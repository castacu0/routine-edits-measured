"""
Content-preserving transformations, i.e. the evasion set.

These reproduce the seven modifications in McKeown & Buchanan (arXiv:2212.08035)
so intra-score results are directly comparable to their Table 5, plus a
`laundering` chain that models what actually happens to an image between
generation and a report: it is posted, recompressed by a platform, screenshotted,
and reposted.

That chain is the one that matters operationally and the one nobody publishes
numbers for. It is the core of research problem RA-4.
"""

from __future__ import annotations

import io
from PIL import Image, ImageDraw


def _jpeg(img: Image.Image, quality: int) -> Image.Image:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def border(img: Image.Image, px: int = 30) -> Image.Image:
    """Extend with a black border rather than overwriting content."""
    out = Image.new("RGB", (img.width + 2 * px, img.height + 2 * px), (0, 0, 0))
    out.paste(img.convert("RGB"), (px, px))
    return out


def compression(img: Image.Image, quality: int = 30) -> Image.Image:
    return _jpeg(img, quality)


def crop(img: Image.Image, frac: float = 0.05) -> Image.Image:
    """Remove `frac` from each edge; at 0.05 the result is 81% of the pixels."""
    dx, dy = int(img.width * frac), int(img.height * frac)
    return img.convert("RGB").crop((dx, dy, img.width - dx, img.height - dy))


def mirror(img: Image.Image) -> Image.Image:
    """
    Horizontal flip.

    One keystroke, and it defeats every non-dihedral perceptual hash: the result
    scores like an unrelated image. This is the single most important row in any
    intra-score table.
    """
    return img.convert("RGB").transpose(Image.Transpose.FLIP_LEFT_RIGHT)


def scale(img: Image.Image, factor: float = 1.5) -> Image.Image:
    return img.convert("RGB").resize(
        (int(img.width * factor), int(img.height * factor)), Image.Resampling.LANCZOS
    )


def thumbnail(img: Image.Image, size: int = 96) -> Image.Image:
    out = img.convert("RGB").copy()
    out.thumbnail((size, size), Image.Resampling.LANCZOS)
    return out


def watermark(img: Image.Image) -> Image.Image:
    """Opaque bar in the lower right, 10% of image height, minimum 40px."""
    out = img.convert("RGB").copy()
    h = max(40, int(out.height * 0.10))
    w = min(out.width, h * 4)
    d = ImageDraw.Draw(out)
    d.rectangle([out.width - w - 8, out.height - h - 8, out.width - 8, out.height - 8],
                fill=(20, 20, 20))
    d.text((out.width - w, out.height - h), "SAMPLE", fill=(255, 255, 255))
    return out


def screenshot(img: Image.Image) -> Image.Image:
    """
    Approximate a phone screenshot: scale to a phone width, then PNG-then-JPEG.

    Screenshotting is how most redistribution actually happens and it destroys
    every provenance signal while mostly preserving the picture.
    """
    target_w = 1080
    ratio = target_w / img.width
    out = img.convert("RGB").resize((target_w, max(1, int(img.height * ratio))),
                                    Image.Resampling.LANCZOS)
    return _jpeg(out, 92)


def laundering(img: Image.Image) -> Image.Image:
    """
    The realistic chain: platform recompress → screenshot → repost recompress.

    A detector or hash evaluated only on pristine output is being evaluated on a
    distribution that does not occur in the wild.
    """
    step = _jpeg(img, 85)          # first platform upload
    step = screenshot(step)        # someone screenshots it
    step = _jpeg(step, 70)         # reposted, compressed again
    return step


TRANSFORMS = {
    "border_30px": border,
    "compression_q30": compression,
    "crop_5pct": crop,
    "mirror_x": mirror,
    "scale_150pct": scale,
    "thumbnail_96": thumbnail,
    "watermark": watermark,
    "screenshot": screenshot,
    "laundering_chain": laundering,
}

# The seven that reproduce McKeown & Buchanan exactly. Use this subset when the
# goal is comparability with published numbers rather than realism.
MCKEOWN_SUBSET = [
    "border_30px", "compression_q30", "crop_5pct", "mirror_x",
    "scale_150pct", "thumbnail_96", "watermark",
]


# ═════════════════════════════════════════════════════════════════════════════
# Routine-transformation set · seven families × four intensities
# ═════════════════════════════════════════════════════════════════════════════
#
# The seven NON-ADVERSARIAL edits an ordinary user applies without any intent to
# evade — recompress, crop, resize, noise, small rotation, brightness, blur —
# each at four intensities. This is the protocol of the JOTS resubmission draft
# (2026-09), reproduced here so its residual-population table regenerates from
# committed code, on Meta's reference PDQ, on a real photographic corpus, with
# paired statistics (research/vdlab/stats.py) rather than a one-off script.
#
# Every family is deterministic. Gaussian noise seeds its generator from the
# image content, so the same image always receives the same noise field and two
# different images never share one.

import hashlib
import math
from typing import Callable

import numpy as np
from PIL import ImageFilter


def jpeg_q(quality: int) -> Callable[[Image.Image], Image.Image]:
    return lambda img: _jpeg(img, quality)


def center_crop_area(frac_area: float) -> Callable[[Image.Image], Image.Image]:
    """Keep the central `frac_area` of the area, then rescale to the original size."""
    def f(img: Image.Image) -> Image.Image:
        img = img.convert("RGB")
        w, h = img.size
        s = math.sqrt(frac_area)
        cw, ch = max(1, int(round(w * s))), max(1, int(round(h * s)))
        x0, y0 = (w - cw) // 2, (h - ch) // 2
        return img.crop((x0, y0, x0 + cw, y0 + ch)).resize((w, h), Image.Resampling.LANCZOS)
    return f


def resize_roundtrip(factor: float) -> Callable[[Image.Image], Image.Image]:
    """Downscale by `factor`, then upscale back to the original size."""
    def f(img: Image.Image) -> Image.Image:
        img = img.convert("RGB")
        w, h = img.size
        small = img.resize((max(1, int(w * factor)), max(1, int(h * factor))),
                           Image.Resampling.LANCZOS)
        return small.resize((w, h), Image.Resampling.LANCZOS)
    return f


def gaussian_noise(sigma: float) -> Callable[[Image.Image], Image.Image]:
    def f(img: Image.Image) -> Image.Image:
        arr = np.asarray(img.convert("RGB"), dtype=np.float32)
        seed = int.from_bytes(hashlib.sha256(arr.tobytes()).digest()[:8], "big")
        rng = np.random.default_rng(seed)
        out = arr + rng.normal(0.0, sigma, size=arr.shape).astype(np.float32)
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")
    return f


def rotation(degrees: float) -> Callable[[Image.Image], Image.Image]:
    """Small-angle rotation about the centre, canvas size kept, corners filled black."""
    return lambda img: img.convert("RGB").rotate(
        degrees, resample=Image.Resampling.BICUBIC, expand=False, fillcolor=(0, 0, 0))


def brightness(delta: int) -> Callable[[Image.Image], Image.Image]:
    def f(img: Image.Image) -> Image.Image:
        arr = np.asarray(img.convert("RGB"), dtype=np.int16) + int(delta)
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    return f


def blur(radius: float) -> Callable[[Image.Image], Image.Image]:
    return lambda img: img.convert("RGB").filter(ImageFilter.GaussianBlur(radius))


ROUTINE_LEVELS: dict[str, tuple[Callable[..., Callable], list]] = {
    "jpeg":             (jpeg_q,           [90, 70, 50, 30]),
    "center_crop":      (center_crop_area, [0.95, 0.85, 0.70, 0.50]),
    "resize_roundtrip": (resize_roundtrip, [0.8, 0.5, 0.3, 0.15]),
    "gaussian_noise":   (gaussian_noise,   [5, 10, 20, 35]),
    "rotation":         (rotation,         [2, 5, 10, 15]),
    "brightness":       (brightness,       [10, -10, 25, -25]),
    "blur":             (blur,             [0.5, 1.0, 2.0, 3.5]),
}

# family -> { "family:level": transform }
ROUTINE_TRANSFORMS: dict[str, dict[str, Callable[[Image.Image], Image.Image]]] = {
    family: {f"{family}:{level}": factory(level) for level in levels}
    for family, (factory, levels) in ROUTINE_LEVELS.items()
}
