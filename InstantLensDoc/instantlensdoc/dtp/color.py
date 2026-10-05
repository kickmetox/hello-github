"""RGB / CMYK / Lab / Spot + ICC-Anzeige/Konvertierung für DTP."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from ild_pdf.print_prep import PANTONE_BASIC, rgb_to_cmyk


@dataclass
class ColorSpec:
    space: str = "rgb"  # rgb | cmyk | lab | spot
    rgb: tuple[float, float, float] = (0.0, 0.0, 0.0)  # 0..1
    cmyk: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    lab: tuple[float, float, float] = (0.0, 0.0, 0.0)
    spot_name: str = ""
    hex: str = "#000000"

    def to_dict(self) -> dict[str, Any]:
        return {
            "space": self.space,
            "rgb": list(self.rgb),
            "cmyk": list(self.cmyk),
            "lab": list(self.lab),
            "spot_name": self.spot_name,
            "hex": self.hex,
        }


def _hex(r: float, g: float, b: float) -> str:
    def ch(v: float) -> int:
        return max(0, min(255, int(round(v * 255))))

    return f"#{ch(r):02X}{ch(g):02X}{ch(b):02X}"


def rgb_to_lab(r: float, g: float, b: float) -> tuple[float, float, float]:
    """sRGB D65 → Lab (kleine Matrix, ohne ICC)."""
    def lin(c: float) -> float:
        return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92

    rl, gl, bl = lin(r), lin(g), lin(b)
    x = rl * 0.4124 + gl * 0.3576 + bl * 0.1805
    y = rl * 0.2126 + gl * 0.7152 + bl * 0.0722
    z = rl * 0.0193 + gl * 0.1192 + bl * 0.9505
    xn, yn, zn = 0.95047, 1.0, 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else (7.787 * t + 16 / 116)

    fx, fy, fz = f(x / xn), f(y / yn), f(z / zn)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def from_rgb(r: float, g: float, b: float) -> ColorSpec:
    r, g, b = float(r), float(g), float(b)
    cmyk = rgb_to_cmyk(r, g, b)
    return ColorSpec(
        space="rgb",
        rgb=(r, g, b),
        cmyk=cmyk,
        lab=rgb_to_lab(r, g, b),
        hex=_hex(r, g, b),
    )


def from_cmyk(c: float, m: float, y: float, k: float) -> ColorSpec:
    r = (1 - c) * (1 - k)
    g = (1 - m) * (1 - k)
    b = (1 - y) * (1 - k)
    spec = from_rgb(r, g, b)
    spec.space = "cmyk"
    spec.cmyk = (float(c), float(m), float(y), float(k))
    return spec


def from_lab(L: float, a: float, b: float) -> ColorSpec:
    """Lab D65 → sRGB (inverse of rgb_to_lab, clamped)."""
    fy = (L + 16) / 116
    fx = a / 500 + fy
    fz = fy - b / 200

    def finv(t: float) -> float:
        return t ** 3 if t ** 3 > 0.008856 else (t - 16 / 116) / 7.787

    x = 0.95047 * finv(fx)
    y = 1.0 * finv(fy)
    z = 1.08883 * finv(fz)
    rl = x * 3.2406 + y * -1.5372 + z * -0.4986
    gl = x * -0.9689 + y * 1.8758 + z * 0.0415
    bl = x * 0.0557 + y * -0.2040 + z * 1.0570

    def gamma(c: float) -> float:
        c = max(0.0, min(1.0, c))
        return 1.055 * (c ** (1 / 2.4)) - 0.055 if c > 0.0031308 else 12.92 * c

    spec = from_rgb(gamma(rl), gamma(gl), gamma(bl))
    spec.space = "lab"
    spec.lab = (float(L), float(a), float(b))
    return spec


def from_spot(name: str) -> ColorSpec:
    key = (name or "").strip().lower().replace(" ", "")
    hit = None
    for k, rec in PANTONE_BASIC.items():
        if key in k.lower() or key in str(rec.get("name") or "").lower().replace(" ", ""):
            hit = rec
            break
    if hit:
        c, m, y, k = hit["cmyk"]
        spec = from_cmyk(c, m, y, k)
    else:
        spec = from_cmyk(0, 1, 1, 0)
    spec.space = "spot"
    spec.spot_name = str(hit["name"] if hit else name)
    return spec


def convert(spec: ColorSpec, space: str) -> ColorSpec:
    space = (space or "rgb").lower()
    if space == spec.space:
        return spec
    if space == "cmyk":
        out = from_cmyk(*spec.cmyk)
        out.space = "cmyk"
        return out
    if space == "lab":
        out = from_lab(*spec.lab)
        out.space = "lab"
        return out
    if space == "spot":
        return from_spot(spec.spot_name or spec.hex)
    return from_rgb(*spec.rgb)


def icc_convert_rgb(
    rgb: tuple[float, float, float],
    *,
    src_icc: str | Path | None = None,
    dst_icc: str | Path | None = None,
) -> tuple[float, float, float]:
    """ICC-Konvertierung via Pillow ImageCms wenn Profile da sind, sonst Identity."""
    if not src_icc or not dst_icc:
        return rgb
    try:
        from PIL import Image, ImageCms

        im = Image.new("RGB", (1, 1), tuple(int(round(c * 255)) for c in rgb))
        conv = ImageCms.buildTransform(
            str(src_icc), str(dst_icc), "RGB", "RGB", renderingIntent=0
        )
        out = ImageCms.applyTransform(im, conv)
        px = out.getpixel((0, 0))
        return (px[0] / 255.0, px[1] / 255.0, px[2] / 255.0)
    except Exception:
        return rgb


BLEND_MODES = (
    "normal",
    "multiply",
    "screen",
    "overlay",
    "darken",
    "lighten",
    "color_dodge",
    "color_burn",
)
