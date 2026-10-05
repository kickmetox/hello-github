"""Text auf Pfad und Glyphen-Positionen — ohne Qt (für Tests)."""

from __future__ import annotations

import math
from typing import Iterable, Sequence


def ellipse_polyline(
    width: float,
    height: float,
    *,
    samples: int = 96,
    inset: float = 8.0,
) -> list[tuple[float, float]]:
    """Ellipse im Rahmen (lokal 0..w / 0..h), Start rechts, Gegenuhrzeigersinn."""
    rx = max(4.0, float(width) / 2.0 - float(inset))
    ry = max(4.0, float(height) / 2.0 - float(inset))
    cx, cy = float(width) / 2.0, float(height) / 2.0
    n = max(8, int(samples))
    pts: list[tuple[float, float]] = []
    for i in range(n + 1):
        t = 2.0 * math.pi * i / n
        pts.append((cx + rx * math.cos(t), cy + ry * math.sin(t)))
    return pts


def line_polyline(width: float, height: float) -> list[tuple[float, float]]:
    """Basislinie unten im Rahmen."""
    y = max(4.0, float(height) * 0.62)
    return [(4.0, y), (max(8.0, float(width) - 4.0), y)]


def polyline_for_kind(kind: str, width: float, height: float) -> list[tuple[float, float]]:
    k = (kind or "").lower().strip()
    if k in ("line", "baseline"):
        return line_polyline(width, height)
    return ellipse_polyline(width, height)


def _seg_len(a: Sequence[float], b: Sequence[float]) -> float:
    return math.hypot(float(b[0]) - float(a[0]), float(b[1]) - float(a[1]))


def path_length(points: Sequence[Sequence[float]]) -> float:
    total = 0.0
    for i in range(1, len(points)):
        total += _seg_len(points[i - 1], points[i])
    return total


def point_and_angle_at(
    points: Sequence[Sequence[float]], distance: float
) -> tuple[float, float, float]:
    """Punkt und Tangentenwinkel (Grad, Qt-Y nach unten) bei Bogenlänge."""
    if len(points) < 2:
        p = points[0] if points else (0.0, 0.0)
        return float(p[0]), float(p[1]), 0.0
    remain = max(0.0, float(distance))
    for i in range(1, len(points)):
        a, b = points[i - 1], points[i]
        sl = _seg_len(a, b)
        if sl < 1e-9:
            continue
        if remain <= sl or i == len(points) - 1:
            t = 0.0 if sl < 1e-9 else min(1.0, remain / sl)
            x = float(a[0]) + t * (float(b[0]) - float(a[0]))
            y = float(a[1]) + t * (float(b[1]) - float(a[1]))
            ang = math.degrees(math.atan2(float(b[1]) - float(a[1]), float(b[0]) - float(a[0])))
            return x, y, ang
        remain -= sl
    last = points[-1]
    prev = points[-2]
    ang = math.degrees(math.atan2(float(last[1]) - float(prev[1]), float(last[0]) - float(prev[0])))
    return float(last[0]), float(last[1]), ang


def estimate_glyph_width(ch: str, font_size: float, tracking: float = 0.0) -> float:
    """Näherung ohne Font-Metrics (Tests/Export-Fallback)."""
    if ch == " ":
        w = 0.33
    elif ch in "iIl1j.,':;!|":
        w = 0.32
    elif ch in "mwWM@":
        w = 0.92
    else:
        w = 0.58
    return max(1.0, float(font_size) * w + float(tracking))


def place_text_on_path(
    text: str,
    points: Sequence[Sequence[float]],
    *,
    font_size: float = 12.0,
    tracking: float = 0.0,
    start_offset: float = 0.0,
) -> list[dict]:
    """Glyphen entlang einer Polylinie. Jeder Eintrag: char, x, y, angle."""
    glyphs: list[dict] = []
    if not text or len(points) < 2:
        return glyphs
    total = path_length(points)
    if total < 2.0:
        return glyphs
    cursor = max(0.0, float(start_offset))
    for ch in text:
        if ch in "\n\r":
            continue
        w = estimate_glyph_width(ch, font_size, tracking)
        if cursor + w * 0.5 > total:
            break
        x, y, ang = point_and_angle_at(points, cursor + w * 0.35)
        glyphs.append({"char": ch, "x": x, "y": y, "angle": ang, "width": w})
        cursor += w
    return glyphs


def text_to_outline_records(
    text: str,
    *,
    font_size: float = 12.0,
    x: float = 2.0,
    y: float | None = None,
    tracking: float = 0.0,
) -> list[dict]:
    """Flacher Text als Outline-Platzhalter (ohne Qt); Export nutzt QPainterPath.addText."""
    baseline = float(y if y is not None else font_size + 2.0)
    out: list[dict] = []
    cx = float(x)
    for ch in (text or "").replace("\r", ""):
        if ch == "\n":
            baseline += float(font_size) * 1.25
            cx = float(x)
            continue
        w = estimate_glyph_width(ch, font_size, tracking)
        out.append({"char": ch, "x": cx, "y": baseline, "angle": 0.0, "width": w})
        cx += w
    return out
