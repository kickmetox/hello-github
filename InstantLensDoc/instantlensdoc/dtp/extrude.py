"""Einfache 3D-Extrusion von QPainterPath (kein OpenGL)."""

from __future__ import annotations

import math
from typing import Any

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPainterPath, QPolygonF


def _offset(angle_deg: float, depth: float) -> tuple[float, float]:
    a = math.radians(float(angle_deg))
    d = float(depth)
    return math.cos(a) * d, -math.sin(a) * d


def _poly_from_path(path: QPainterPath) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    for i in range(path.elementCount()):
        el = path.elementAt(i)
        pts.append((float(el.x), float(el.y)))
    return pts


def extrude_path(
    path: QPainterPath,
    *,
    depth: float = 18.0,
    angle_deg: float = 32.0,
    shading: float = 0.35,
    fill: str = "#4A90D9",
) -> dict[str, Any]:
    """
    Liefert Seitenflächen (hinten zuerst) + Front für QPainter.

    Jede Fläche: {\"poly\": QPolygonF, \"color\": QColor}
    """
    ox, oy = _offset(angle_deg, depth)
    pts = _poly_from_path(path)
    if len(pts) < 2:
        return {"faces": [], "front": path, "ox": ox, "oy": oy}

    base = QColor(fill or "#4A90D9")
    shade = max(0.0, min(1.0, float(shading)))
    faces: list[dict[str, Any]] = []
    n = len(pts)
    # close
    if pts[0] != pts[-1]:
        pts = pts + [pts[0]]
        n = len(pts)
    for i in range(n - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        poly = QPolygonF(
            [
                QPointF(x0 + ox, y0 + oy),
                QPointF(x1 + ox, y1 + oy),
                QPointF(x1, y1),
                QPointF(x0, y0),
            ]
        )
        # shade by edge direction
        dx, dy = x1 - x0, y1 - y0
        nx, ny = -dy, dx
        ln = math.hypot(nx, ny) or 1.0
        nx, ny = nx / ln, ny / ln
        light = max(0.25, min(1.0, 0.55 + 0.45 * (nx * 0.4 + ny * 0.7)))
        k = 1.0 - shade * (1.0 - light)
        c = QColor(
            max(0, min(255, int(base.red() * k))),
            max(0, min(255, int(base.green() * k))),
            max(0, min(255, int(base.blue() * k))),
        )
        faces.append({"poly": poly, "color": c})

    front = QPainterPath(path)
    return {"faces": faces, "front": front, "ox": ox, "oy": oy, "base": base}


def path_for_shape(kind: str, w: float, h: float) -> QPainterPath:
    p = QPainterPath()
    k = (kind or "rectangle").lower()
    if k == "ellipse":
        p.addEllipse(0.0, 0.0, float(w), float(h))
    elif k == "triangle":
        p.moveTo(float(w) / 2.0, 0.0)
        p.lineTo(float(w), float(h))
        p.lineTo(0.0, float(h))
        p.closeSubpath()
    elif k == "line":
        p.moveTo(0.0, float(h) / 2.0)
        p.lineTo(float(w), float(h) / 2.0)
    elif k == "arrow":
        p.moveTo(0.0, float(h) * 0.35)
        p.lineTo(float(w) * 0.65, float(h) * 0.35)
        p.lineTo(float(w) * 0.65, 0.0)
        p.lineTo(float(w), float(h) / 2.0)
        p.lineTo(float(w) * 0.65, float(h))
        p.lineTo(float(w) * 0.65, float(h) * 0.65)
        p.lineTo(0.0, float(h) * 0.65)
        p.closeSubpath()
    else:
        p.addRect(0.0, 0.0, float(w), float(h))
    return p
