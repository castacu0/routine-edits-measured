#!/usr/bin/env python3
"""
Hash a corpus ONCE. Publish the hashes. Everyone works from those.

    python research/hash_corpus.py \\
        --corpus ~/datasets/mirflickr1m \\
        --out    ~/datasets/mirflickr1m-hashes \\
        --i-confirm-benign-corpus [--workers 8] [--chunk 5000] [--resume] [--limit N]

This is the "streaming hash-once script" research/COMPUTE.md asked for. It:

  1. walks the corpus in sorted order (deterministic), never materialising it;
  2. hashes every image with PDQ (Meta reference bindings), pHash and Blockhash
     in one pass, recording PDQ quality;
  3. writes one compressed part file per chunk, so an interrupted run resumes
     with --resume instead of starting over;
  4. merges the parts into hashes.npz and writes MANIFEST.json recording corpus
     path, counts, library versions, the harness commit and a checksum.

The output is ~90 bytes per image: a million images fit in ~90 MB, contain no
pixels, and can be shared among researchers. It does NOT belong in this
repository; publish it as a release asset or on Zenodo (COMPUTE.md, "Security
note on the hash file"). The script refuses to write inside the repo.

Corpus rule, as everywhere in this harness: ordinary images only, outside the
repository, with --i-confirm-benign-corpus stated explicitly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from importlib.metadata import version as pkg_version
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vdlab import hashes as H  # noqa: E402
from vdlab.guard import REPO, guard_corpus, guard_output  # noqa: E402

EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def list_images(corpus: Path, limit: int | None) -> list[str]:
    found = sorted(str(p.relative_to(corpus)) for p in corpus.rglob("*")
                   if p.is_file() and p.suffix.lower() in EXTS)
    return found[:limit] if limit else found


def _hash_one(args: tuple[str, str]) -> tuple[str, bytes | None, int, bytes | None, bytes | None]:
    """Worker: one image → packed PDQ, quality, packed pHash, packed Blockhash."""
    corpus, rel = args
    try:
        img = Image.open(Path(corpus) / rel)
        img.load()
        pdq_bits, q = H.pdq_with_quality(img)
        return (rel, np.packbits(pdq_bits).tobytes(), int(q),
                np.packbits(H.phash(img)).tobytes(), np.packbits(H.blockhash(img)).tobytes())
    except Exception:
        return (rel, None, -1, None, None)


def hash_chunk(corpus: Path, rels: list[str], workers: int) -> tuple[dict, list[str]]:
    ids, pdq, qual, ph, bh, failed = [], [], [], [], [], []
    jobs = [(str(corpus), r) for r in rels]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for rel, p, q, a, b in pool.map(_hash_one, jobs, chunksize=32):
            if p is None:
                failed.append(rel)
                continue
            ids.append(rel)
            pdq.append(np.frombuffer(p, dtype=np.uint8))
            qual.append(q)
            ph.append(np.frombuffer(a, dtype=np.uint8))
            bh.append(np.frombuffer(b, dtype=np.uint8))
    arrays = {
        "ids": np.array(ids, dtype=str),
        "pdq": np.stack(pdq) if pdq else np.zeros((0, 32), np.uint8),
        "pdq_quality": np.array(qual, dtype=np.int16),
        "phash": np.stack(ph) if ph else np.zeros((0, 8), np.uint8),
        "blockhash": np.stack(bh) if bh else np.zeros((0, 32), np.uint8),
    }
    return arrays, failed


def harness_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                                       text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", required=True, type=Path, help="image directory, OUTSIDE this repository")
    ap.add_argument("--out", required=True, type=Path, help="output directory, OUTSIDE this repository")
    ap.add_argument("--i-confirm-benign-corpus", action="store_true",
                    help="affirm the corpus contains no abuse material and no case data")
    ap.add_argument("--workers", type=int, default=None, help="processes (default: all cores minus one)")
    ap.add_argument("--chunk", type=int, default=5000, help="images per part file")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--resume", action="store_true", help="skip part files that already exist")
    args = ap.parse_args()

    guard_corpus(args.corpus, args.i_confirm_benign_corpus)
    guard_output(args.out)
    args.out.mkdir(parents=True, exist_ok=True)
    workers = args.workers or max(1, (__import__("os").cpu_count() or 2) - 1)

    started = time.time()
    rels = list_images(args.corpus, args.limit)
    if not rels:
        raise SystemExit(f"✖ no images found under {args.corpus}")
    chunks = [rels[i:i + args.chunk] for i in range(0, len(rels), args.chunk)]
    print(f"{len(rels):,} images in {len(chunks)} part(s) · {workers} workers · out: {args.out}")

    failed_all: list[str] = []
    skipped = 0
    for k, chunk in enumerate(chunks):
        part = args.out / f"part-{k:05d}.npz"
        if args.resume and part.exists():
            skipped += 1
            continue
        t0 = time.time()
        arrays, failed = hash_chunk(args.corpus, chunk, workers)
        failed_all.extend(failed)
        np.savez_compressed(part, **arrays)
        rate = len(chunk) / max(1e-6, time.time() - t0)
        print(f"  part {k + 1}/{len(chunks)}: {len(arrays['ids']):,} hashed, "
              f"{len(failed)} unreadable, {rate:,.0f} img/s")
    if skipped:
        print(f"  resumed: {skipped} existing part(s) skipped")

    # Merge, in order, so the id list is deterministic across runs.
    parts = [np.load(args.out / f"part-{k:05d}.npz") for k in range(len(chunks))]
    merged = {key: np.concatenate([p[key] for p in parts]) for key in parts[0].files}
    hashes_path = args.out / "hashes.npz"
    np.savez_compressed(hashes_path, **merged)

    n = int(merged["ids"].shape[0])
    manifest = {
        "generator": "research/hash_corpus.py",
        "corpus": str(args.corpus.resolve()),
        "images_listed": len(rels),
        "images_hashed": n,
        "unreadable": len(failed_all) if not skipped else None,
        "unreadable_files_sample": failed_all[:100],
        "parts": len(chunks),
        "chunk": args.chunk,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "elapsed_seconds": round(time.time() - started, 1),
        "versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pillow": pkg_version("pillow"),
            "pdqhash": pkg_version("pdqhash"),
        },
        "harness_commit": harness_commit(),
        "arrays": {
            "ids": "relative path within the corpus, sorted",
            "pdq": "uint8 (n, 32): 256 PDQ bits packed MSB-first (numpy.packbits)",
            "pdq_quality": "int16 (n,): Meta quality score; <= 49 is Meta's discard floor",
            "phash": "uint8 (n, 8): 64-bit DCT pHash, packed",
            "blockhash": "uint8 (n, 32): 256-bit block-mean hash, packed",
        },
        "pdq_threshold_bits": H.PDQ_THRESHOLD_BITS,
        "pdq_quality_floor": H.PDQ_QUALITY_FLOOR,
        "hashes_sha256": sha256_of(hashes_path),
        "warning": ("perceptual hashes of ordinary images only; no pixels, no case data. "
                    "Do not add to the repository: publish as a release asset or on Zenodo."),
    }
    (args.out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    mb = hashes_path.stat().st_size / 1e6
    print(f"✔ {n:,} hashes → {hashes_path} ({mb:.1f} MB) · manifest written · "
          f"{time.time() - started:.1f}s total")


if __name__ == "__main__":
    main()
