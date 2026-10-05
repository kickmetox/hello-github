"""Variable Fonts: Achsen listen (QFontDatabase + fontTools), Qt-Anwendung."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable

from PySide6.QtGui import QFont, QFontDatabase


COMMON_AXES = ("wght", "wdth", "slnt", "ital", "opsz")

_WIN_FONT_DIRS = (
    Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts",
)
_UNIX_FONT_DIRS = (
    Path("/usr/share/fonts"),
    Path("/usr/local/share/fonts"),
    Path.home() / ".fonts",
    Path.home() / ".local/share/fonts",
)


def _font_dirs() -> list[Path]:
    dirs = []
    if os.name == "nt":
        dirs.extend(_WIN_FONT_DIRS)
    else:
        dirs.extend(_UNIX_FONT_DIRS)
    return [d for d in dirs if d and d.is_dir()]


def _iter_font_files() -> Iterable[Path]:
    for root in _font_dirs():
        for p in root.rglob("*"):
            if p.suffix.lower() in {".ttf", ".otf", ".ttc", ".otc"}:
                yield p


def _fvar_axes(path: Path) -> list[dict[str, Any]]:
    try:
        from fontTools.ttLib import TTFont
    except Exception:
        return []
    try:
        font = TTFont(str(path), fontNumber=0, lazy=True)
    except Exception:
        return []
    try:
        if "fvar" not in font:
            return []
        axes = []
        for a in font["fvar"].axes:
            axes.append(
                {
                    "tag": str(a.axisTag),
                    "min": float(a.minValue),
                    "default": float(a.defaultValue),
                    "max": float(a.maxValue),
                }
            )
        return axes
    finally:
        try:
            font.close()
        except Exception:
            pass


def list_variable_fonts(*, include_static: bool = True) -> list[dict[str, Any]]:
    """
    Variable Fonts (fvar) plus Systemfamilien.

    Ohne fontTools oder ohne Variable-Dateien: Familien aus QFontDatabase
    mit synthetischen Achsen wght/wdth/slnt (Qt-unterstützt).
    """
    families = list(QFontDatabase.families())
    by_file: list[dict[str, Any]] = []
    seen_tags: set[str] = set()
    for path in _iter_font_files():
        axes = _fvar_axes(path)
        if not axes:
            continue
        rec = {
            "family": path.stem,
            "path": str(path),
            "variable": True,
            "axes": axes,
            "source": "fontfile",
        }
        by_file.append(rec)
        seen_tags.add(path.stem.lower())

    out = list(by_file)
    if include_static:
        for fam in families:
            key = fam.lower()
            if key in seen_tags:
                continue
            rec = {
                "family": fam,
                "path": "",
                "variable": False,
                "axes": [
                    {"tag": "wght", "min": 100.0, "default": 400.0, "max": 900.0},
                    {"tag": "wdth", "min": 50.0, "default": 100.0, "max": 200.0},
                    {"tag": "slnt", "min": -10.0, "default": 0.0, "max": 0.0},
                ],
                "source": "qfontdatabase",
            }
            # mark as variable-capable via Qt even if the file has no fvar
            styles = QFontDatabase.styles(fam)
            rec["styles"] = list(styles)[:12]
            out.append(rec)
    out.sort(key=lambda r: (0 if r["variable"] else 1, r["family"].lower()))
    return out


def list_font_axes(family_or_path: str) -> list[dict[str, Any]]:
    raw = (family_or_path or "").strip()
    p = Path(raw)
    if p.is_file():
        axes = _fvar_axes(p)
        if axes:
            return axes
    for rec in list_variable_fonts():
        if rec["family"].lower() == raw.lower() or rec.get("path") == raw:
            return list(rec.get("axes") or [])
    return [
        {"tag": "wght", "min": 100.0, "default": 400.0, "max": 900.0},
        {"tag": "wdth", "min": 50.0, "default": 100.0, "max": 200.0},
        {"tag": "slnt", "min": -10.0, "default": 0.0, "max": 0.0},
    ]


def apply_axes_to_qfont(font: QFont, axes: dict[str, float]) -> QFont:
    """Qt-unterstützte Achsen: wght → weight, wdth → stretch, slnt/ital → italic."""
    out = QFont(font)
    if "wght" in axes:
        w = int(max(1, min(1000, float(axes["wght"]))))
        try:
            out.setWeight(QFont.Weight(w) if w in (100, 200, 300, 400, 500, 600, 700, 800, 900) else QFont.Weight.Normal)
        except Exception:
            out.setBold(w >= 600)
        if w >= 600:
            out.setBold(True)
        elif w <= 400:
            out.setBold(False)
    if "wdth" in axes:
        out.setStretch(int(max(50, min(200, float(axes["wdth"])))))
    if float(axes.get("slnt") or 0) != 0.0 or float(axes.get("ital") or 0) >= 0.5:
        out.setItalic(True)
    if "opsz" in axes and out.pointSizeF() <= 0:
        out.setPointSizeF(float(axes["opsz"]))
    return out


def apply_axes_to_frame(frame: Any, axes: dict[str, float]) -> None:
    """DTP-Textrahmen: Achsen speichern + Qt-Felder setzen."""
    frame.font_axes = dict(axes)
    if "wght" in axes:
        frame.font_weight = int(axes["wght"])
    if "wdth" in axes:
        frame.font_stretch = int(axes["wdth"])
