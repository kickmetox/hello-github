"""Envelope Distort: 4-Punkt-Bilinear-Warp von QPainterPath."""

from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainterPath, QTransform


def envelope_corners_default(width: float, height: float, *, bulge: float = 0.12) -> list[list[float]]:
    """Leicht gewölbte Default-Ecken (TL, TR, BR, BL) in Lokalcoords."""
    w, h, b = float(width), float(height), float(bulge) * min(float(width), float(height))
    return [
        [0.0, b],
        [w, 0.0],
        [w - b * 0.3, h],
        [b, h - b * 0.2],
    ]


def _map_uv(u: float, v: float, corners: Sequence[Sequence[float]]) -> tuple[float, float]:
    tl, tr, br, bl = corners
    x = (
        (1 - u) * (1 - v) * tl[0]
        + u * (1 - v) * tr[0]
        + u * v * br[0]
        + (1 - u) * v * bl[0]
    )
    y = (
        (1 - u) * (1 - v) * tl[1]
        + u * (1 - v) * tr[1]
        + u * v * br[1]
        + (1 - u) * v * bl[1]
    )
    return x, y


def warp_painter_path(
    path: QPainterPath,
    *,
    width: float,
    height: float,
    corners: Sequence[Sequence[float]],
) -> QPainterPath:
    """Bilinearer Envelope: lokale (0..w, 0..h) → 4 Ecken."""
    w = max(1.0, float(width))
    h = max(1.0, float(height))
    if len(corners) != 4:
        return QPainterPath(path)
    out = QPainterPath()
    n = path.elementCount()
    if n == 0:
        return out
    for i in range(n):
        el = path.elementAt(i)
        u = max(0.0, min(1.0, float(el.x) / w))
        v = max(0.0, min(1.0, float(el.y) / h))
        x, y = _map_uv(u, v, corners)
        et = el.type
        # QPainterPath.ElementType: MoveTo=0, LineTo=1, CurveTo=2
        if i == 0 or et == QPainterPath.ElementType.MoveToElement:
            out.moveTo(x, y)
        elif et == QPainterPath.ElementType.CurveToElement:
            out.lineTo(x, y)
        else:
            out.lineTo(x, y)
    return out


def warp_rect_path(
    width: float,
    height: float,
    corners: Sequence[Sequence[float]],
    *,
    steps: int = 12,
) -> QPainterPath:
    """Gitter-Warp eines Rechtecks (für Vorschau/Export)."""
    w, h = float(width), float(height)
    path = QPainterPath()
    # outer boundary via top, right, bottom, left
    def pt(u, v):
        return _map_uv(u, v, corners)

    path.moveTo(*pt(0.0, 0.0))
    for i in range(1, steps + 1):
        path.lineTo(*pt(i / steps, 0.0))
    for i in range(1, steps + 1):
        path.lineTo(*pt(1.0, i / steps))
    for i in range(1, steps + 1):
        path.lineTo(*pt(1.0 - i / steps, 1.0))
    for i in range(1, steps + 1):
        path.lineTo(*pt(0.0, 1.0 - i / steps))
    path.closeSubpath()
    return path


def identity_corners(width: float, height: float) -> list[list[float]]:
    w, h = float(width), float(height)
    return [[0.0, 0.0], [w, 0.0], [w, h], [0.0, h]]


def apply_envelope_transform(
    path: QPainterPath, origin_x: float, origin_y: float
) -> QPainterPath:
    t = QTransform()
    t.translate(origin_x, origin_y)
    return t.map(path)


def path_bounding_rect(path: QPainterPath) -> QRectF:
    return path.controlPointRect()
