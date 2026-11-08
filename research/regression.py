#!/usr/bin/env python3
"""
Hash stability regression.

WHAT IT DOES
------------
Generates a small set of images deterministically, hashes them, and compares the
result against fingerprints recorded when we knew they were correct.

WHY IT MATTERS
--------------
Our whole system assumes the same image always produces the same fingerprint.
That assumption can break without anyone touching our code: PDQ is maintained by
Meta, and the image-decoding library underneath it changes too. A routine update
can shift a fingerprint by a bit or two.

That is invisible in ordinary testing, because our unit tests use pre-computed
fingerprints rather than images. If it happened silently, stored fingerprints
would stop matching, published research would stop reproducing, and the system
would appear to work while catching nothing.

    python research/regression.py            # check against the baseline
    python research/regression.py --update   # re-record it (read the warning)

The images are generated from a fixed seed rather than committed, so no image
file ever enters this repository — the same rule that governs everything else
here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageDraw  # noqa: E402

from vdlab import hashes as H  # noqa: E402
from vdlab import transforms as T  # noqa: E402

BASELINE = Path(__file__).resolve().parent / "hash_baseline.json"
N_IMAGES = 12


def make_image(index: int) -> Image.Image:
    """
    Deterministic test image.

    Uses an explicit LCG rather than `random` so the output cannot shift if
    Python changes its RNG. That would be a false alarm, and a regression check
    that cries wolf gets switched off.
    """
    state = (index + 1) * 2654435761 % 2147483647

    def nxt(n: int) -> int:
        nonlocal state
        state = (state * 1103515245 + 12345) % 2147483648
        return state % n

    w, h = 640, 480
    img = Image.new("RGB", (w, h), (nxt(256), nxt(256), nxt(256)))
    d = ImageDraw.Draw(img)
    for _ in range(14):
        x0, y0 = nxt(w), nxt(h)
        x1, y1 = x0 + nxt(220) + 20, y0 + nxt(220) + 20
        colour = (nxt(256), nxt(256), nxt(256))
        if nxt(2):
            d.ellipse([x0, y0, x1, y1], fill=colour)
        else:
            d.rectangle([x0, y0, x1, y1], fill=colour)
    return img


def bits_to_hex(bits) -> str:
    out = 0
    for b in bits:
        out = (out << 1) | int(b)
    return format(out, f"0{len(bits) // 4}x")


def compute() -> dict:
    """Fingerprint every generated image, plus one transform of each."""
    result = {}
    for i in range(N_IMAGES):
        img = make_image(i)
        pdq_bits, quality = H.pdq_with_quality(img)
        entry = {
            "pdq": bits_to_hex(pdq_bits),
            "pdq_quality": quality,
            "phash": bits_to_hex(H.phash(img)),
            "blockhash": bits_to_hex(H.blockhash(img)),
            # A transform is included because a decoder change can affect
            # re-encoded images while leaving originals untouched.
            "pdq_after_q30": bits_to_hex(H.pdq_with_quality(T.compression(img))[0]),
        }
        # Dihedral is checked as a digest; comparing 8 hashes per image would
        # make a failure harder to read, not easier.
        variants = "".join(bits_to_hex(v) for v in H.pdq_dihedral(img))
        entry["dihedral_digest"] = hashlib.sha256(variants.encode()).hexdigest()[:16]
        result[f"image_{i:02d}"] = entry
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--update", action="store_true",
                    help="overwrite the baseline (see the warning printed first)")
    args = ap.parse_args()

    current = compute()

    if args.update or not BASELINE.exists():
        if BASELINE.exists():
            print("⚠  OVERWRITING THE BASELINE.\n")
            print("   Do this only when you know WHY the fingerprints changed.")
            print("   If a library update caused it, every previously computed")
            print("   hash is suspect, including any a researcher has published.")
            print("   Tell them before you do this.\n")
        BASELINE.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n")
        print(f"✔ baseline written: {BASELINE.relative_to(Path.cwd())} ({len(current)} images)")
        return

    baseline = json.loads(BASELINE.read_text())
    drift = []
    for key, expected in baseline.items():
        actual = current.get(key)
        if actual is None:
            drift.append(f"{key}: missing from current run")
            continue
        for field, want in expected.items():
            got = actual.get(field)
            if got != want:
                drift.append(f"{key}.{field}\n      expected {want}\n      got      {got}")

    if drift:
        print("\n✖ PERCEPTUAL HASHES HAVE CHANGED\n")
        for d in drift:
            print(f"    {d}")
        print(f"\n  {len(drift)} field(s) differ from the recorded baseline.\n")
        print("  This is not flakiness. One of these is true:")
        print("    1. The PDQ library changed how it computes fingerprints.")
        print("    2. The image-decoding library changed how it reads pixels.")
        print("    3. Someone changed research/vdlab/hashes.py.")
        print("\n  Work out which before doing anything else. Do not run")
        print("  --update to make this pass until you know why.\n")
        sys.exit(1)

    print(f"✔ all fingerprints stable across {len(baseline)} images "
          f"({sum(len(v) for v in baseline.values())} fields checked)")


if __name__ == "__main__":
    main()
