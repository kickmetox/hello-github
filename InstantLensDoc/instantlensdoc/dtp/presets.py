"""Buch- und Seitenformate für den DTP-Modus (Maße in mm)."""

from __future__ import annotations

from typing import Any

PT_PER_MM = 72.0 / 25.4

# Quelle: docs/instantlensdoc-dtp.md — Hochformat
BOOK_PRESETS_MM: dict[str, tuple[float, float]] = {
    "Taschenbuch": (125.0, 190.0),
    "DINA5": (148.0, 210.0),
    "A5": (148.0, 210.0),
    "Roman": (135.0, 215.0),
    "Sachbuch": (170.0, 240.0),
    "DINA4": (210.0, 297.0),
    "A4": (210.0, 297.0),
    "Quadrat": (210.0, 210.0),
    "Letter": (215.9, 279.4),
    "A3": (297.0, 420.0),
    "A6": (105.0, 148.0),
}

# Van-de-Graaf-ähnlich: innen/oben etwas enger als außen/unten
_SATZSPIEGEL_MM: dict[str, tuple[float, float, float, float, int, float]] = {
    # top, bottom, inside, outside, columns, gutter
    "Taschenbuch": (16.0, 20.0, 16.0, 14.0, 1, 5.0),
    "DINA5": (18.0, 22.0, 18.0, 16.0, 1, 5.0),
    "A5": (18.0, 22.0, 18.0, 16.0, 1, 5.0),
    "Roman": (18.0, 22.0, 18.0, 16.0, 1, 5.0),
    "Sachbuch": (20.0, 24.0, 22.0, 18.0, 1, 6.0),
    "DINA4": (20.0, 25.0, 25.0, 20.0, 1, 6.0),
    "A4": (20.0, 25.0, 25.0, 20.0, 1, 6.0),
    "Quadrat": (18.0, 18.0, 18.0, 18.0, 1, 5.0),
    "Letter": (20.0, 25.0, 25.0, 20.0, 1, 6.0),
    "A3": (22.0, 28.0, 28.0, 22.0, 2, 8.0),
    "A6": (12.0, 16.0, 12.0, 12.0, 1, 4.0),
}


def mm_to_pt(mm: float) -> float:
    return float(mm) * PT_PER_MM


def pt_to_mm(pt: float) -> float:
    return float(pt) / PT_PER_MM


def list_book_presets() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    for name, (w, h) in BOOK_PRESETS_MM.items():
        key = (int(round(w * 10)), int(round(h * 10)))
        if key in seen and name in ("A5", "A4"):
            continue
        seen.add(key)
        out.append(
            {
                "name": name,
                "width_mm": w,
                "height_mm": h,
                "width_pt": mm_to_pt(w),
                "height_pt": mm_to_pt(h),
            }
        )
    return out


def apply_book_preset(doc: Any, name: str) -> Any:
    """PageGeometry eines DtpDocument aus Preset setzen (inkl. Satzspiegel)."""
    from .model import PageGeometry

    key = (name or "A4").strip()
    if key not in BOOK_PRESETS_MM:
        compact = key.replace(" ", "").lower()
        for k in BOOK_PRESETS_MM:
            if k.replace(" ", "").lower() == compact:
                key = k
                break
        else:
            key = "A4"
    w_mm, h_mm = BOOK_PRESETS_MM[key]
    top, bottom, inside, outside, cols, gutter = _SATZSPIEGEL_MM.get(
        key, (20.0, 25.0, 25.0, 20.0, 1, 6.0)
    )
    geo = PageGeometry(
        name=key,
        width_pt=mm_to_pt(w_mm),
        height_pt=mm_to_pt(h_mm),
        margin_top_pt=mm_to_pt(top),
        margin_bottom_pt=mm_to_pt(bottom),
        margin_left_pt=mm_to_pt(inside),
        margin_right_pt=mm_to_pt(outside),
        bleed_pt=mm_to_pt(3.0),
        columns=int(cols),
        gutter_pt=mm_to_pt(gutter),
    )
    doc.geometry = geo
    if getattr(doc, "masters", None):
        doc.masters[0].header_text = "{title}"
        doc.masters[0].footer_text = "{n} / {total}"
    return doc
