"""Crop-/Registration-Marken — geteilte Geometrie für DTP und PDF.

Kein Word-Editor-Overlay (keine Breiten-, Kopf- oder Fußzeilen-Marken).
Satzspiegel bleibt im DTP Seitengeometrie (blaues Margin-Rechteck).
"""

from __future__ import annotations

from typing import NamedTuple

# Tags, die der Texteditor (Geschwister) für Overlays nutzt — DTP zeichnet sie nicht.
WORD_EDITOR_OVERLAY_TAGS = frozenset(
    {
        "header_mark",
        "footer_mark",
        "width_mark",
        "column_width_mark",
        "editor_print_mark",
        "breitenmarke",
        "kopfmarke",
        "fussmarke",
    }
)


class LineSeg(NamedTuple):
    x1: float
    y1: float
    x2: float
    y2: float


class CircleMark(NamedTuple):
    x: float
    y: float
    r: float


def printer_mark_size(width: float, height: float) -> tuple[float, float]:
    """Markenlänge und Abstand zum Seitenrand (gleiche Formel wie PDF-Overlay)."""
    mark = max(8.0, min(18.0, min(float(width), float(height)) * 0.04))
    gap = 2.0
    return mark, gap


def crop_and_registration_marks(
    x: float, y: float, w: float, h: float
) -> tuple[list[LineSeg], CircleMark | None]:
    """L-förmige Crop-Marks an den Ecken plus Registrierkreuz oben-mitte."""
    mark, gap = printer_mark_size(w, h)
    lines: list[LineSeg] = []
    corners = (
        (x, y, -1, -1),
        (x + w, y, 1, -1),
        (x, y + h, -1, 1),
        (x + w, y + h, 1, 1),
    )
    for cx, cy, sx, sy in corners:
        hx0 = cx + sx * gap
        hx1 = cx + sx * (gap + mark)
        hy = cy + sy * gap
        lines.append(LineSeg(hx0, hy, hx1, hy))
        vx = cx + sx * gap
        vy0 = cy + sy * gap
        vy1 = cy + sy * (gap + mark)
        lines.append(LineSeg(vx, vy0, vx, vy1))
    mx = x + w / 2.0
    my = y - gap - mark * 0.6
    circle: CircleMark | None = None
    if my > 2:
        r = mark * 0.35
        lines.append(LineSeg(mx - r, my, mx + r, my))
        lines.append(LineSeg(mx, my - r, mx, my + r))
        circle = CircleMark(mx, my, r * 0.45)
    return lines, circle
