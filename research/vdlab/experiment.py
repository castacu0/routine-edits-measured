"""
Experiment runners for RA-1 (tail), RA-2 (correlation) and RA-3 (dihedral cost).

Each returns plain dicts so results serialise to JSON without a schema layer,
and so a researcher can drop them into pandas or R without fighting an object
model.

Every runner is deterministic given a seed. Reproducibility is not optional in
this project: a number that cannot be regenerated cannot be defended.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

from . import hashes as H
from . import transforms as T


@dataclass
class Corpus:
    """A directory of ordinary images. See research/README.md on requirements."""

    paths: list[Path]
    seed: int = 1

    @classmethod
    def load(cls, directory: Path, limit: int | None = None, seed: int = 1) -> "Corpus":
        exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        found = sorted(p for p in Path(directory).rglob("*") if p.suffix.lower() in exts)
        if not found:
            raise SystemExit(f"No images found under {directory}")
        rng = random.Random(seed)
        rng.shuffle(found)
        return cls(paths=found[:limit] if limit else found, seed=seed)

    def __len__(self) -> int:
        return len(self.paths)


def _open(path: Path) -> Image.Image | None:
    try:
        img = Image.open(path)
        img.load()
        return img
    except Exception:
        return None


# ── RA-1 · inter-image distribution and its tail ─────────────────────────────

def inter_image(corpus: Corpus, algorithms: list[str], comparisons_per_image: int = 50,
                progress=None) -> dict:
    """
    Hamming distance between UNRELATED images.

    Reproduces the McKeown & Buchanan method: each image against K random others.
    Unrelated pairs should centre on 0.5. What we actually care about is the
    LEFT TAIL, because every false positive lives there and because the
    published range gives only its minimum.
    """
    rng = random.Random(corpus.seed)
    fns = {a: H.ALGORITHMS[a][0] for a in algorithms}
    bits = {a: H.ALGORITHMS[a][1] for a in algorithms}

    computed: dict[str, list[np.ndarray]] = {a: [] for a in algorithms}
    qualities: list[int] = []
    kept: list[Path] = []

    for i, path in enumerate(corpus.paths):
        img = _open(path)
        if img is None:
            continue
        try:
            if "pdq" in algorithms:
                vec, q = H.pdq_with_quality(img)
                # Meta discards these; including them inflates the collision rate
                # and is a known way to make a hash look worse than it is.
                if q <= H.PDQ_QUALITY_FLOOR:
                    continue
                qualities.append(q)
                computed["pdq"].append(vec)
            for a in algorithms:
                if a != "pdq":
                    computed[a].append(fns[a](img))
        except Exception:
            for a in algorithms:
                if len(computed[a]) > len(kept):
                    computed[a].pop()
            continue
        kept.append(path)
        if progress and i % 200 == 0:
            progress(i, len(corpus.paths))

    n = len(kept)
    if n < 2:
        raise SystemExit("Fewer than two usable images; nothing to compare.")

    # Sample pairs once and score every algorithm on the SAME pairs, which is
    # what makes the correlation analysis in RA-2 valid.
    pairs: list[tuple[int, int]] = []
    for i in range(n):
        for _ in range(comparisons_per_image):
            j = rng.randrange(n)
            if j != i:
                pairs.append((i, j))

    dists = {a: np.empty(len(pairs), dtype=np.int32) for a in algorithms}
    for k, (i, j) in enumerate(pairs):
        for a in algorithms:
            dists[a][k] = H.hamming(computed[a][i], computed[a][j])

    out = {
        "method": "inter_image",
        "images_used": n,
        "images_skipped_low_quality": len(corpus.paths) - n,
        "pairs": len(pairs),
        "seed": corpus.seed,
        "algorithms": {},
    }
    if qualities:
        out["pdq_quality"] = {"mean": float(np.mean(qualities)),
                              "min": int(np.min(qualities))}

    for a in algorithms:
        d = dists[a]
        nb = bits[a]
        norm = d / nb
        thr = H.PDQ_THRESHOLD_BITS if a == "pdq" else round(nb * H.PDQ_THRESHOLD_BITS / 256)
        below = int(np.count_nonzero(d <= thr))
        # The empirical floor: if zero pairs landed below threshold we can only
        # say the rate is under 1/N, never that it is zero.
        rate = below / len(d) if below else None
        out["algorithms"][a] = {
            "bits": nb,
            "threshold_bits": thr,
            "mean": float(norm.mean()),
            "median": float(np.median(norm)),
            "stdev": float(norm.std()),
            "min": float(norm.min()),
            "max": float(norm.max()),
            "min_bits": int(d.min()),
            "pairs_below_threshold": below,
            "empirical_fpr": rate,
            "empirical_fpr_upper_bound_if_zero": None if below else 1 / len(d),
            # The tail, which is the actual deliverable of RA-1.
            "tail_cdf_bits": {str(b): int(np.count_nonzero(d <= b)) for b in range(0, 65, 5)},
            "histogram_bits": dict(sorted(Counter(d.tolist()).items())),
        }
    out["_pair_distances"] = {a: dists[a] for a in algorithms}  # for RA-2, not serialised
    return out


# ── RA-2 · error correlation across the stack ────────────────────────────────

def error_correlation(inter_result: dict, algorithms: list[str]) -> dict:
    """
    Do the algorithms produce their near-collisions on the SAME pairs?

    Our fusion model assumes correlated errors (rho ~ 0.7) but that figure is a
    placeholder. This measures it on identical pairs, which is the only way the
    comparison is meaningful.
    """
    dists = inter_result["_pair_distances"]
    bits = {a: H.ALGORITHMS[a][1] for a in algorithms}
    norm = {a: dists[a] / bits[a] for a in algorithms}

    out = {"method": "error_correlation", "pearson": {}, "joint_low_tail": {}}
    for i, a in enumerate(algorithms):
        for b in algorithms[i + 1:]:
            r = float(np.corrcoef(norm[a], norm[b])[0, 1])
            out["pearson"][f"{a}~{b}"] = r

    # Beyond linear correlation: when one algorithm scores a pair in its lowest
    # percentile, how often do the others? That is what fusion actually depends
    # on, and it is not the same question as Pearson r.
    pct = 1.0
    for a in algorithms:
        cut_a = np.percentile(norm[a], pct)
        low_a = norm[a] <= cut_a
        for b in algorithms:
            if a == b:
                continue
            cut_b = np.percentile(norm[b], pct)
            low_b = norm[b] <= cut_b
            joint = int(np.count_nonzero(low_a & low_b))
            expected = len(norm[a]) * (pct / 100) ** 2
            out["joint_low_tail"][f"{a}|{b}"] = {
                "observed": joint,
                "expected_if_independent": round(expected, 1),
                "lift": round(joint / expected, 2) if expected else None,
            }
    return out


# ── RA-3 · what dihedral robustness costs ────────────────────────────────────

def dihedral_cost(corpus: Corpus, sample: int = 300, comparisons: int = 50) -> dict:
    """
    Measure both sides of the dihedral trade in one pass.

    Benefit: recall against mirrored images, which plain PDQ misses entirely.
    Cost:    the false-positive multiplier from indexing 8 variants instead of 1.

    The naive assumption is that 8 variants means 8x the false positives. They
    are derived from the same image and are therefore not independent, so the
    real multiplier is somewhere between 1 and 8. Nobody has published it.
    """
    rng = random.Random(corpus.seed)
    entries = []
    for path in corpus.paths[:sample]:
        img = _open(path)
        if img is None:
            continue
        try:
            base, q = H.pdq_with_quality(img)
            if q <= H.PDQ_QUALITY_FLOOR:
                continue
            variants = H.pdq_dihedral(img)
            mirrored, _ = H.pdq_with_quality(T.mirror(img))
        except Exception:
            continue
        entries.append({"base": base, "variants": variants, "mirrored": mirrored})

    if len(entries) < 2:
        raise SystemExit("Not enough usable images for the dihedral experiment.")

    thr = H.PDQ_THRESHOLD_BITS
    plain_hits = sum(1 for e in entries if H.hamming(e["base"], e["mirrored"]) <= thr)
    dihedral_hits = sum(
        1 for e in entries
        if min(H.hamming(v, e["mirrored"]) for v in e["variants"]) <= thr
    )

    single_fp = dihedral_fp = trials = 0
    n = len(entries)
    for i in range(n):
        for _ in range(comparisons):
            j = rng.randrange(n)
            if j == i:
                continue
            trials += 1
            if H.hamming(entries[i]["base"], entries[j]["base"]) <= thr:
                single_fp += 1
            if min(H.hamming(v, entries[j]["base"]) for v in entries[i]["variants"]) <= thr:
                dihedral_fp += 1

    return {
        "method": "dihedral_cost",
        "images": n,
        "threshold_bits": thr,
        "recall_vs_mirror": {
            "plain_pdq": plain_hits / n,
            "dihedral_pdq": dihedral_hits / n,
            "note": "plain PDQ is expected to be ~0.0; a mirror scores like an unrelated image",
        },
        "false_positives": {
            "trials": trials,
            "single_hash": single_fp,
            "dihedral_8": dihedral_fp,
            "multiplier": (dihedral_fp / single_fp) if single_fp else None,
            "naive_assumption": 8.0,
            "note": "multiplier is None when no false positives occurred at this "
                    "sample size; rerun with a larger corpus to resolve it",
        },
    }


# ── intra-score · robustness to each transformation ──────────────────────────

def intra_image(corpus: Corpus, algorithms: list[str], transform_names: list[str],
                sample: int = 400, progress=None) -> dict:
    """Distance between an image and a transformed version of itself."""
    fns = {a: H.ALGORITHMS[a][0] for a in algorithms}
    bits = {a: H.ALGORITHMS[a][1] for a in algorithms}
    acc: dict[str, dict[str, list[int]]] = {
        t: {a: [] for a in algorithms} for t in transform_names
    }

    used = 0
    for idx, path in enumerate(corpus.paths[:sample]):
        img = _open(path)
        if img is None:
            continue
        try:
            base = {a: fns[a](img) for a in algorithms}
        except Exception:
            continue
        used += 1
        for tname in transform_names:
            try:
                variant = T.TRANSFORMS[tname](img)
                for a in algorithms:
                    acc[tname][a].append(H.hamming(base[a], fns[a](variant)))
            except Exception:
                continue
        if progress and idx % 100 == 0:
            progress(idx, min(sample, len(corpus.paths)))

    out = {"method": "intra_image", "images_used": used, "transforms": {}}
    for tname in transform_names:
        out["transforms"][tname] = {}
        for a in algorithms:
            d = np.array(acc[tname][a]) if acc[tname][a] else np.array([0])
            nb = bits[a]
            thr = H.PDQ_THRESHOLD_BITS if a == "pdq" else round(nb * H.PDQ_THRESHOLD_BITS / 256)
            out["transforms"][tname][a] = {
                "mean_norm": float((d / nb).mean()),
                "median_norm": float(np.median(d / nb)),
                "exact_match_pct": float(100 * np.count_nonzero(d == 0) / len(d)),
                # This is the number that matters: would we still catch it?
                "recall_at_threshold": float(np.count_nonzero(d <= thr) / len(d)),
            }
    return out


# ── residual population under routine transformations · paired ──────────────

def residual_paired(corpus: Corpus, algorithms: list[str],
                    families: dict[str, dict[str, "T.Callable"]] | None = None,
                    sample: int | None = None, n_boot: int = 2000, progress=None) -> dict:
    """
    Residual population = share of transformed images a method FAILS to match
    against its own original, per transformation family, pooled over the
    family's intensity levels — plus the statistics that make a comparison
    between methods defensible:

      - Wilson interval on every rate;
      - McNemar on identical image–transformation pairs for every pair of
        algorithms;
      - bootstrap CI for the residual difference, resampled by image;
      - the two-proportion sample size needed to detect a given improvement on
        the first algorithm's residual rate.

    Every algorithm is scored on the SAME transformed image. That is what makes
    the paired tests valid, and it is why this runner hashes each transformed
    image once and fans the result out to all algorithms.

    No PDQ-quality filter is applied: a robustness question asks whether the
    same image survives an edit, so every image is kept. The count of images
    Meta would discard is reported so the reader can judge.
    """
    from . import stats as S

    families = families or T.ROUTINE_TRANSFORMS
    fns = {a: H.ALGORITHMS[a][0] for a in algorithms}
    bits = {a: H.ALGORITHMS[a][1] for a in algorithms}
    thr = {a: (H.PDQ_THRESHOLD_BITS if a == "pdq"
               else round(bits[a] * H.PDQ_THRESHOLD_BITS / 256)) for a in algorithms}

    det: dict[str, dict[str, list[list[bool]]]] = {
        fam: {a: [] for a in algorithms} for fam in families
    }
    used = low_quality = 0
    paths = corpus.paths[:sample] if sample else corpus.paths

    for idx, path in enumerate(paths):
        img = _open(path)
        if img is None:
            continue
        try:
            base = {a: fns[a](img) for a in algorithms}
            if "pdq" in algorithms and H.pdq_with_quality(img)[1] <= H.PDQ_QUALITY_FLOOR:
                low_quality += 1
        except Exception:
            continue
        used += 1
        for fam, levels in families.items():
            rows = {a: [] for a in algorithms}
            for _name, fn in levels.items():
                variant = fn(img)
                for a in algorithms:
                    rows[a].append(H.hamming(base[a], fns[a](variant)) <= thr[a])
            for a in algorithms:
                det[fam][a].append(rows[a])
        if progress and idx % 50 == 0:
            progress(idx, len(paths))

    if used < 2:
        raise SystemExit("Fewer than two usable images; nothing to measure.")

    out = {
        "method": "residual_paired",
        "images_used": used,
        "images_below_pdq_quality_floor": low_quality,
        "threshold_bits": thr,
        "n_boot": n_boot,
        "families": {},
        "sample_size": {},
    }

    for fam, levels in families.items():
        mats = {a: np.asarray(det[fam][a], dtype=bool) for a in algorithms}
        level_names = list(levels.keys())
        entry = {"levels": level_names, "n_images": used,
                 "n_pairs": int(mats[algorithms[0]].size), "per_algorithm": {}, "pairwise": {}}
        for a in algorithms:
            rr = S.residual_rate(mats[a])
            rr["per_level"] = {lv: float(1 - mats[a][:, i].mean()) for i, lv in enumerate(level_names)}
            entry["per_algorithm"][a] = rr
        for i, a in enumerate(algorithms):
            for b in algorithms[i + 1:]:
                entry["pairwise"][f"{a}~{b}"] = {
                    "mcnemar": S.mcnemar(mats[a], mats[b]),
                    "bootstrap": S.bootstrap_diff(mats[a], mats[b], n_boot=n_boot, seed=corpus.seed),
                }
        out["families"][fam] = entry

        base_r = entry["per_algorithm"][algorithms[0]]["residual"]
        if 0.0 < base_r < 1.0:
            effects = [e for e in (0.05, 0.10, 0.15, 0.20, 0.30) if base_r - e > 0]
            if effects:
                out["sample_size"][fam] = {
                    "baseline_algorithm": algorithms[0],
                    "baseline_residual": base_r,
                    "table": S.sample_size_table(base_r, effects),
                }
    return out
