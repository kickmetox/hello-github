"""Raster-Diff zweier PDF-Seiten (PIL) + grobe Ähnlichkeit in Prozent — 1.4.0/1.4.1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from PIL import Image, ImageChops, ImageEnhance, ImageOps


@dataclass(frozen=True)
class RasterDiffResult:
    """Ergebnis eines Seiten-Raster-Vergleichs."""

    similarity_percent: float  # 0–100, grob
    different_pixels: int
    total_pixels: int
    overlay: Image.Image  # RGB: Basis + magentafarbene Diff-Maske


def _as_rgb(img: Image.Image) -> Image.Image:
    if img.mode == "RGB":
        return img
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        return bg
    return img.convert("RGB")


def align_images(
    left: Image.Image, right: Image.Image
) -> Tuple[Image.Image, Image.Image]:
    """Beide Bilder auf gemeinsame Größe (min width/height) bringen."""
    a = _as_rgb(left)
    b = _as_rgb(right)
    w = min(a.width, b.width)
    h = min(a.height, b.height)
    if w < 1 or h < 1:
        return a, b
    if a.size != (w, h):
        a = a.resize((w, h), Image.Resampling.BILINEAR)
    if b.size != (w, h):
        b = b.resize((w, h), Image.Resampling.BILINEAR)
    return a, b


def raster_diff(
    left: Image.Image,
    right: Image.Image,
    *,
    threshold: int = 18,
) -> RasterDiffResult:
    """
    Pixel-Diff zweier gerenderter Seiten.
    similarity_percent ≈ Anteil ähnlicher Pixel (nach Schwellwert), grob.
    overlay: linkes Bild + magentafarbene Markierung der Unterschiede.
    """
    a, b = align_images(left, right)
    w, h = a.size
    total = max(1, w * h)
    # Absolutedifferenz pro Kanal
    diff = ImageChops.difference(a, b)
    # Grau + Schwellwert → Maske
    gray = ImageOps.grayscale(diff)
    # Punktweise: Pixel > threshold gelten als unterschiedlich
    mask = gray.point(lambda p: 255 if p > max(0, min(255, int(threshold))) else 0)
    different = sum(1 for p in mask.getdata() if p)
    similar = max(0, total - different)
    pct = round(100.0 * similar / total, 1)

    # Overlay: Basis abdunkeln + Magenta auf Diff
    base = ImageEnhance.Brightness(a).enhance(0.85)
    overlay = base.copy()
    magenta = Image.new("RGB", (w, h), (220, 40, 180))
    overlay.paste(magenta, mask=mask)

    return RasterDiffResult(
        similarity_percent=pct,
        different_pixels=int(different),
        total_pixels=int(total),
        overlay=overlay,
    )
