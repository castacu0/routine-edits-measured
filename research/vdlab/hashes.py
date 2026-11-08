"""
Perceptual hash implementations for the research harness.

PDQ comes from Meta's reference implementation via the `pdqhash` bindings, so
results are comparable to production. pHash and Blockhash are implemented here
in ~30 lines each rather than pulled from `imagehash`, because the harness needs
to control the exact variant and because the algorithms are small enough that a
dependency would obscure more than it saves.

All three return a numpy bool array so Hamming distance is one XOR and a sum.

NOTHING IN THIS MODULE TOUCHES ABUSE MATERIAL. It operates on ordinary images.
See research/README.md on corpus requirements.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

try:
    import pdqhash
except ImportError:  # pragma: no cover
    pdqhash = None


# ── DCT-II, built once and reused ────────────────────────────────────────────

_DCT_CACHE: dict[int, np.ndarray] = {}


def dct_matrix(n: int) -> np.ndarray:
    """Orthonormal DCT-II basis. Cached; these are small and reused constantly."""
    if n not in _DCT_CACHE:
        k = np.arange(n).reshape(-1, 1)
        i = np.arange(n).reshape(1, -1)
        m = np.cos(np.pi * (2 * i + 1) * k / (2 * n))
        m[0] /= np.sqrt(2)
        _DCT_CACHE[n] = m * np.sqrt(2 / n)
    return _DCT_CACHE[n]


def dct2(a: np.ndarray) -> np.ndarray:
    m = dct_matrix(a.shape[0])
    return m @ a @ m.T


# ── the hashes ───────────────────────────────────────────────────────────────

def pdq(img: Image.Image) -> np.ndarray:
    """Meta PDQ, 256 bits. Returns bits only; use pdq_with_quality for both."""
    return pdq_with_quality(img)[0]


def pdq_with_quality(img: Image.Image) -> tuple[np.ndarray, int]:
    """
    PDQ bits plus the quality score.

    Quality <= 49 is Meta's documented discard threshold: below it the image has
    too little structure for the hash to discriminate, and including such hashes
    is a well-known way to manufacture false positives.
    """
    if pdqhash is None:
        raise RuntimeError("pdqhash not installed — see research/requirements.txt")
    arr = np.asarray(img.convert("RGB"))
    vector, quality = pdqhash.compute(arr)
    return np.asarray(vector, dtype=bool), int(quality)


def pdq_dihedral(img: Image.Image) -> list[np.ndarray]:
    """
    All 8 PDQ hashes covering the dihedral group D4.

    This is the mitigation for the one-keystroke flip evasion, and measuring what
    it costs is research problem RA-3.
    """
    if pdqhash is None:
        raise RuntimeError("pdqhash not installed")
    arr = np.asarray(img.convert("RGB"))
    vectors, _quality = pdqhash.compute_dihedral(arr)
    return [np.asarray(v, dtype=bool) for v in vectors]


def phash(img: Image.Image, hash_size: int = 8, factor: int = 4) -> np.ndarray:
    """
    Classic DCT perceptual hash, 64 bits.

    Resize to 32x32 greyscale, DCT, keep the top-left 8x8 low-frequency block,
    drop the DC term, threshold at the median of the rest.
    """
    n = hash_size * factor
    g = np.asarray(img.convert("L").resize((n, n), Image.Resampling.LANCZOS), dtype=float)
    low = dct2(g)[:hash_size, :hash_size]
    flat = low.flatten()
    # Excluding DC (index 0) from the median makes the hash invariant to overall
    # brightness; leaving it in skews the threshold toward the image's mean.
    med = np.median(flat[1:])
    return (flat > med).astype(bool)


def blockhash(img: Image.Image, bits: int = 16) -> np.ndarray:
    """
    Block-mean hash, 256 bits at bits=16.

    Included because it is NOT a DCT descendant, which makes it the useful
    control when measuring error correlation across the stack (RA-2).
    """
    g = np.asarray(img.convert("L").resize((bits, bits), Image.Resampling.LANCZOS), dtype=float)
    return (g > np.median(g)).flatten().astype(bool)


ALGORITHMS = {
    "pdq": (pdq, 256),
    "phash": (phash, 64),
    "blockhash": (blockhash, 256),
}

# Meta's documented recommendation for PDQ. The others have no comparable
# published default, so their thresholds are scaled to the same normalised
# distance and should be treated as provisional, not authoritative.
PDQ_THRESHOLD_BITS = 31
PDQ_QUALITY_FLOOR = 49


def hamming(a: np.ndarray, b: np.ndarray) -> int:
    return int(np.count_nonzero(a ^ b))


def normalised(a: np.ndarray, b: np.ndarray) -> float:
    return hamming(a, b) / a.size
