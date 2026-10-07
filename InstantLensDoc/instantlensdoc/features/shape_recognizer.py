"""Intelligente Formerkennung: Tintenstrich → Vektorform.

Geometrischer Erkenner (Ecken + $1-ähnlich). Ersetzt den Strich durch
rectangle / ellipse / line / arrow / triangle.

Hook für die Annotationsschicht (nicht in diesem Lauf geändert)::

    from instantlensdoc.features.shape_recognizer import recognize_ink_as_shape

    result = recognize_ink_as_shape(points)  # points: [[x,y], ...] oder [[x,y,pressure], ...]
    if result.kind != \"ink\":
        # Ink-Annotation entfernen, Shape-Annotation mit result.rect / result.kind setzen
        ...

``recognize_ink_as_shape`` ist die stabile Funktion, die der Annotation-Worker
aufrufen kann — pdf_view wird hier nicht angefasst.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

Point = Sequence[float]


@dataclass
class ShapeResult:
    kind: str  # rectangle|ellipse|line|arrow|triangle|ink
    confidence: float
    rect: tuple[float, float, float, float]  # x, y, w, h
    points_resampled: list[tuple[float, float]] = field(default_factory=list)
    corners: int = 0
    closed: bool = False
    message: str = ""


def _xy(pts: Sequence[Point]) -> list[tuple[float, float]]:
    out = []
    for p in pts:
        if len(p) >= 2:
            out.append((float(p[0]), float(p[1])))
    return out


def _resample(pts: list[tuple[float, float]], n: int = 64) -> list[tuple[float, float]]:
    if len(pts) < 2:
        return pts[:]
    dist = [0.0]
    for i in range(1, len(pts)):
        d = math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
        dist.append(dist[-1] + d)
    total = dist[-1] or 1.0
    step = total / (n - 1)
    out = [pts[0]]
    target = step
    i = 1
    while len(out) < n and i < len(pts):
        while i < len(dist) and dist[i] < target:
            i += 1
        if i >= len(pts):
            break
        d0, d1 = dist[i - 1], dist[i]
        t = 0.0 if d1 == d0 else (target - d0) / (d1 - d0)
        x = pts[i - 1][0] + t * (pts[i][0] - pts[i - 1][0])
        y = pts[i - 1][1] + t * (pts[i][1] - pts[i - 1][1])
        out.append((x, y))
        target += step
    while len(out) < n:
        out.append(pts[-1])
    return out[:n]


def _bbox(pts: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, y0 = min(xs), min(ys)
    return x0, y0, max(xs) - x0, max(ys) - y0


def _path_len(pts: list[tuple[float, float]]) -> float:
    return sum(
        math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
        for i in range(1, len(pts))
    )


def _area(pts: list[tuple[float, float]]) -> float:
    if len(pts) < 3:
        return 0.0
    a = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def _corner_count(pts: list[tuple[float, float]], *, thresh_deg: float = 38.0) -> int:
    if len(pts) < 5:
        return 0
    n = len(pts)
    idxs = []
    rad = math.radians(thresh_deg)
    for i in range(1, n - 1):
        ax, ay = pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]
        bx, by = pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]
        la, lb = math.hypot(ax, ay), math.hypot(bx, by)
        if la < 1e-6 or lb < 1e-6:
            continue
        cos = max(-1.0, min(1.0, (ax * bx + ay * by) / (la * lb)))
        ang = math.acos(cos)
        if ang >= rad:
            if idxs and (i - idxs[-1]) < 3:
                continue
            idxs.append(i)
    return len(idxs)


def _linearity(pts: list[tuple[float, float]]) -> float:
    if len(pts) < 2:
        return 0.0
    x0, y0 = pts[0]
    x1, y1 = pts[-1]
    chord = math.hypot(x1 - x0, y1 - y0) or 1.0
    return min(1.0, chord / max(_path_len(pts), 1e-6))


def recognize_stroke(points: Sequence[Point]) -> ShapeResult:
    pts = _xy(points)
    if len(pts) < 2:
        return ShapeResult(kind="ink", confidence=0.0, rect=(0, 0, 1, 1), message="zu wenig Punkte")
    rs = _resample(pts, 64)
    x, y, w, h = _bbox(rs)
    w, h = max(w, 4.0), max(h, 4.0)
    closed = math.hypot(rs[0][0] - rs[-1][0], rs[0][1] - rs[-1][1]) < 0.22 * math.hypot(w, h)
    corners = _corner_count(rs)
    lin = _linearity(rs)
    circ = 0.0
    per = _path_len(rs + [rs[0]] if closed else rs)
    ar = _area(rs)
    if per > 0:
        circ = min(1.2, (4.0 * math.pi * ar) / (per * per + 1e-6))
    aspect = w / h if h else 1.0

    kind = "ink"
    conf = 0.35
    # line / arrow
    if lin > 0.86 and not closed:
        # arrow head: last 15% of path has a direction change
        mid = rs[len(rs) * 3 // 4]
        head_lin = _linearity(rs[len(rs) * 3 // 4 :])
        if head_lin < 0.7 and corners >= 1:
            kind, conf = "arrow", 0.78
        else:
            kind, conf = "line", 0.9
    elif closed and circ >= 0.72 and corners <= 2:
        kind, conf = "ellipse", min(0.95, 0.7 + circ * 0.25)
    elif closed and corners >= 3:
        if 3 <= corners <= 4 and circ < 0.7:
            kind, conf = ("triangle" if corners == 3 else "rectangle"), 0.82
        elif corners >= 4:
            kind, conf = "rectangle", 0.8 if 0.55 <= aspect <= 1.8 else 0.7
        else:
            kind, conf = "triangle", 0.75
    elif corners >= 4 and 0.6 <= aspect <= 1.7:
        kind, conf = "rectangle", 0.62
    elif corners == 3:
        kind, conf = "triangle", 0.6
    elif circ >= 0.55:
        kind, conf = "ellipse", 0.55

    # $1-like template distances as tie-break
    templates = {
        "rectangle": _rect_template(),
        "ellipse": _ellipse_template(),
        "triangle": _tri_template(),
        "line": _line_template(),
        "arrow": _arrow_template(),
    }
    best_t, best_d = kind, 1e9
    cand = _normalize_for_dollar(rs)
    for name, tmpl in templates.items():
        d = sum(math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(cand, tmpl)) / len(cand)
        if d < best_d:
            best_d, best_t = d, name
    if best_d < 0.55 and kind == "ink":
        kind, conf = best_t, 0.7
    elif best_d < 0.35:
        kind = best_t
        conf = max(conf, 0.85)

    return ShapeResult(
        kind=kind,
        confidence=float(conf),
        rect=(x, y, w, h),
        points_resampled=rs,
        corners=corners,
        closed=closed,
        message=f"{kind} corners={corners} circ={circ:.2f} lin={lin:.2f}",
    )


def recognize_ink_as_shape(points: Sequence[Point]) -> ShapeResult:
    """Hook für die PDF-Annotationsschicht und den DTP-Canvas."""
    return recognize_stroke(points)


def _normalize_for_dollar(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    rs = _resample(pts, 64)
    cx = sum(p[0] for p in rs) / len(rs)
    cy = sum(p[1] for p in rs) / len(rs)
    trans = [(p[0] - cx, p[1] - cy) for p in rs]
    m = max(max(abs(x), abs(y)) for x, y in trans) or 1.0
    return [(x / m, y / m) for x, y in trans]


def _rect_template() -> list[tuple[float, float]]:
    pts = []
    for i in range(16):
        pts.append((-1 + i / 8, -1))
    for i in range(16):
        pts.append((1, -1 + i / 8))
    for i in range(16):
        pts.append((1 - i / 8, 1))
    for i in range(16):
        pts.append((-1, 1 - i / 8))
    return _normalize_for_dollar(pts)


def _ellipse_template() -> list[tuple[float, float]]:
    pts = [
        (math.cos(2 * math.pi * i / 64), math.sin(2 * math.pi * i / 64))
        for i in range(64)
    ]
    return _normalize_for_dollar(pts)


def _tri_template() -> list[tuple[float, float]]:
    a, b, c = (0.0, -1.0), (1.0, 1.0), (-1.0, 1.0)
    pts = []
    for start, end in ((a, b), (b, c), (c, a)):
        for i in range(21):
            t = i / 21
            pts.append((start[0] + t * (end[0] - start[0]), start[1] + t * (end[1] - start[1])))
    return _normalize_for_dollar(pts)


def _line_template() -> list[tuple[float, float]]:
    return _normalize_for_dollar([(-1.0, 0.0), (1.0, 0.0)])


def _arrow_template() -> list[tuple[float, float]]:
    shaft = [(-1.0, 0.0), (0.4, 0.0)]
    head = [(0.4, 0.0), (0.4, -0.35), (1.0, 0.0), (0.4, 0.35), (0.4, 0.0)]
    return _normalize_for_dollar(shaft + head)
