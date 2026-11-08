"""
Paired statistics for method comparisons.

Three things, and only three, because these are the three a reviewer asks for
when two hash functions are compared on the same images:

  1. residual_rate   — the share of transformed images a method FAILS to match,
                        with a Wilson interval, never a bare point estimate.
  2. mcnemar         — paired test on identical image–transformation pairs.
                        Independent-samples tests are wrong here: both methods
                        saw the same inputs, so the discordant cells carry the
                        whole comparison.
  3. bootstrap_diff  — non-parametric CI for the difference in residual rate,
                        resampled BY IMAGE so the pairing (and the correlation
                        between intensity levels of one image) is preserved.
  4. required_n      — two-proportion sample size for a minimum detectable
                        effect at a given power; the number that says whether
                        an evaluation could have seen the effect it claims.

Pure numpy and the standard library. No scipy, so the harness stays
installable from three packages and every number here is reproducible from a
formula you can read.

NOTHING IN THIS MODULE TOUCHES IMAGES. It consumes boolean detection matrices.
"""

from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np

_Z = NormalDist()


def _z(p: float) -> float:
    return _Z.inv_cdf(p)


# ── 1. residual rate with interval ───────────────────────────────────────────

def residual_rate(detected: np.ndarray, confidence: float = 0.95) -> dict:
    """
    Share of pairs NOT detected, i.e. the residual (evasion) rate.

    `detected` is a boolean array; shape does not matter, every element is one
    image–transformation pair. Wilson score interval rather than the normal
    approximation, because rates near 0% or 100% are exactly where the normal
    interval lies and exactly where these results land.
    """
    d = np.asarray(detected, dtype=bool).ravel()
    n = d.size
    if n == 0:
        raise ValueError("residual_rate: no observations")
    misses = int(n - np.count_nonzero(d))
    p = misses / n
    z = _z(1 - (1 - confidence) / 2)
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return {
        "n": n,
        "misses": misses,
        "residual": p,
        "ci_low": max(0.0, centre - half),
        "ci_high": min(1.0, centre + half),
        "interval": "wilson",
        "confidence": confidence,
    }


# ── 2. McNemar ───────────────────────────────────────────────────────────────

def mcnemar(detected_a: np.ndarray, detected_b: np.ndarray, correction: bool = True) -> dict:
    """
    McNemar's test on paired detections.

    Cells: `a_only` = A detected, B missed; `b_only` = B detected, A missed.
    The concordant cells do not enter the statistic; that is the point of a
    paired test. Continuity-corrected chi-square with one degree of freedom;
    when fewer than 25 discordant pairs exist the chi-square approximation is
    poor and the exact binomial two-sided p-value is reported instead.

    A significant result says the methods differ. It does not say by how much
    or whether the difference matters; report the residual difference and its
    bootstrap interval alongside, never the p-value alone.
    """
    a = np.asarray(detected_a, dtype=bool).ravel()
    b = np.asarray(detected_b, dtype=bool).ravel()
    if a.shape != b.shape:
        raise ValueError("mcnemar: inputs must be paired (same shape)")
    a_only = int(np.count_nonzero(a & ~b))
    b_only = int(np.count_nonzero(~a & b))
    n_disc = a_only + b_only

    out = {
        "n_pairs": int(a.size),
        "a_only": a_only,
        "b_only": b_only,
        "discordant": n_disc,
        "residual_a": float(1 - a.mean()),
        "residual_b": float(1 - b.mean()),
        "residual_diff_b_minus_a": float(a.mean() - b.mean()),
    }

    if n_disc == 0:
        out.update({"method": "none", "chi2": 0.0, "p_value": 1.0,
                    "note": "no discordant pairs; the methods agree on every pair"})
        return out

    if n_disc < 25:
        k = min(a_only, b_only)
        p = 2 * sum(math.comb(n_disc, i) for i in range(0, k + 1)) / (2 ** n_disc)
        out.update({"method": "exact_binomial", "chi2": None, "p_value": min(1.0, p)})
        return out

    diff = abs(a_only - b_only) - (1 if correction else 0)
    chi2 = max(0.0, diff) ** 2 / n_disc
    # Survival function of chi-square with df=1: P(X > chi2) = erfc(sqrt(chi2/2)).
    p = math.erfc(math.sqrt(chi2 / 2))
    out.update({"method": "chi2_continuity" if correction else "chi2", "chi2": chi2, "p_value": p})
    return out


# ── 3. bootstrap by image ────────────────────────────────────────────────────

def bootstrap_diff(detected_a: np.ndarray, detected_b: np.ndarray, n_boot: int = 5000,
                   seed: int = 1, confidence: float = 0.95) -> dict:
    """
    Bootstrap CI for residual(B) − residual(A), resampling IMAGES.

    Inputs are (n_images, n_levels) boolean matrices: one row per image, one
    column per intensity level of the transformation. Resampling rows keeps
    every level of one image together, which is what makes the interval honest
    when the same image contributes four observations.

    Positive difference = B misses more than A. Chunked so 5,000 replicates over
    a million-image corpus fit in memory.
    """
    a = np.atleast_2d(np.asarray(detected_a, dtype=bool))
    b = np.atleast_2d(np.asarray(detected_b, dtype=bool))
    if a.shape != b.shape:
        raise ValueError("bootstrap_diff: inputs must be paired (same shape)")
    n_img, n_lvl = a.shape
    # Per-image miss counts. The bootstrap only needs these, not the matrices.
    per_img = (n_lvl - b.sum(axis=1)) - (n_lvl - a.sum(axis=1))  # misses_B - misses_A
    per_img = per_img.astype(np.int64)
    point = float(per_img.sum() / (n_img * n_lvl))

    rng = np.random.default_rng(seed)
    reps = np.empty(n_boot, dtype=np.float64)
    chunk = max(1, min(n_boot, 200_000_000 // max(1, n_img)))
    done = 0
    while done < n_boot:
        m = min(chunk, n_boot - done)
        idx = rng.integers(0, n_img, size=(m, n_img))
        reps[done:done + m] = per_img[idx].sum(axis=1) / (n_img * n_lvl)
        done += m

    alpha = 1 - confidence
    lo, hi = np.percentile(reps, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return {
        "n_images": int(n_img),
        "levels_per_image": int(n_lvl),
        "n_boot": int(n_boot),
        "seed": seed,
        "diff_b_minus_a": point,
        "ci_low": float(lo),
        "ci_high": float(hi),
        "excludes_zero": bool(lo > 0 or hi < 0),
        "resampled_by": "image",
    }


# ── 4. sample size ───────────────────────────────────────────────────────────

def required_n(baseline_rate: float, min_detectable_effect: float, alpha: float = 0.05,
               power: float = 0.80) -> int:
    """
    Images per condition to detect a reduction of `min_detectable_effect`
    (absolute, e.g. 0.05 for five percentage points) from `baseline_rate`.

    Two-proportion z-test, normal approximation, two-sided alpha, equal group
    sizes. This is the textbook formula and deliberately so: the reader should
    be able to recompute it by hand. It assumes independent groups, which makes
    it CONSERVATIVE for a paired design (a paired test needs fewer), so it is
    safe to quote as a floor.
    """
    p1 = float(baseline_rate)
    p2 = p1 - float(min_detectable_effect)
    if not (0 < p1 < 1) or not (0 < p2 < 1):
        raise ValueError("rates must lie strictly inside (0, 1)")
    z_a = _z(1 - alpha / 2)
    z_b = _z(power)
    pbar = (p1 + p2) / 2
    num = (z_a * math.sqrt(2 * pbar * (1 - pbar)) + z_b * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    return int(math.ceil(num / (p1 - p2) ** 2))


def sample_size_table(baseline_rate: float, effects=(0.05, 0.10, 0.15, 0.20, 0.30),
                      alpha: float = 0.05, power: float = 0.80) -> list[dict]:
    return [{"min_detectable_effect": e, "required_n_per_condition": required_n(baseline_rate, e, alpha, power)}
            for e in effects]


# ── self-test ────────────────────────────────────────────────────────────────

def _selftest() -> None:
    # Sample-size formula against a published-style table: baseline 72.2%,
    # 80% power, alpha 0.05 → 1325 / 345 / 159 / 92 / 42 (±1 for rounding).
    expect = {0.05: 1325, 0.10: 345, 0.15: 159, 0.20: 92, 0.30: 42}
    for e, want in expect.items():
        got = required_n(0.722, e)
        assert abs(got - want) <= 1, (e, got, want)

    # McNemar cell counts b=30, c=15 (45 discordant → chi-square branch) with
    # continuity correction → chi2 = (|30-15|-1)^2 / 45 = 4.3556, p ≈ 0.0369.
    a = np.array([True] * 30 + [False] * 15 + [True] * 100)
    b = np.array([False] * 30 + [True] * 15 + [True] * 100)
    r = mcnemar(a, b)
    assert r["a_only"] == 30 and r["b_only"] == 15, r
    assert abs(r["chi2"] - 196 / 45) < 1e-9, r
    assert abs(r["p_value"] - 0.03689) < 1e-4, r

    # Exact branch when discordant < 25 in total: b=3, c=0 → p = 2 * 1/8 = 0.25.
    a = np.array([True, True, True, True])
    b = np.array([False, False, False, True])
    r = mcnemar(a, b)
    assert r["method"] == "exact_binomial" and abs(r["p_value"] - 0.25) < 1e-12, r

    # Residual rate and Wilson interval: 0 misses of 1000 → upper bound ≈ 0.38%.
    rr = residual_rate(np.ones(1000, dtype=bool))
    assert rr["residual"] == 0.0 and 0.003 < rr["ci_high"] < 0.004, rr

    # Bootstrap recovers a known difference and its interval contains it.
    rng = np.random.default_rng(7)
    n, lvl = 2000, 4
    det_a = rng.random((n, lvl)) < 0.9   # A misses 10%
    det_b = rng.random((n, lvl)) < 0.7   # B misses 30%
    bs = bootstrap_diff(det_a, det_b, n_boot=2000, seed=3)
    assert 0.15 < bs["diff_b_minus_a"] < 0.25, bs
    assert bs["ci_low"] < bs["diff_b_minus_a"] < bs["ci_high"] and bs["excludes_zero"], bs

    print("✔ stats self-test passed: required_n, mcnemar (chi2 + exact), residual_rate, bootstrap_diff")


if __name__ == "__main__":
    _selftest()
