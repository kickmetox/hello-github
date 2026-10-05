"""Live-Füllungen, Schatten, Schnittmasken — Qt nur beim Paint."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QRadialGradient,
)


def parse_color(value: str, default: str = "#333333") -> QColor:
    c = QColor(value or default)
    if not c.isValid():
        c = QColor(default)
    return c


def fill_brush(fr: Any, width: float, height: float) -> QBrush:
    """Solid / linear / radial aus Rahmenfeldern."""
    kind = (getattr(fr, "fill_kind", None) or "solid").lower()
    c0 = parse_color(getattr(fr, "fill", None) or "#D0E8FF", "#D0E8FF")
    c1 = parse_color(getattr(fr, "fill_to", None) or "", c0.name())
    if getattr(fr, "fill_to", None):
        c1 = parse_color(fr.fill_to, c0.name())
    w, h = max(1.0, float(width)), max(1.0, float(height))
    if kind == "radial":
        g = QRadialGradient(QPointF(w / 2.0, h / 2.0), min(w, h) / 2.0)
        g.setColorAt(0.0, c0)
        g.setColorAt(1.0, c1)
        return QBrush(g)
    if kind == "linear":
        ang = float(getattr(fr, "fill_angle", 90.0) or 90.0)
        import math

        rad = math.radians(ang)
        x1 = w / 2.0 - math.cos(rad) * w / 2.0
        y1 = h / 2.0 - math.sin(rad) * h / 2.0
        x2 = w / 2.0 + math.cos(rad) * w / 2.0
        y2 = h / 2.0 + math.sin(rad) * h / 2.0
        g = QLinearGradient(x1, y1, x2, y2)
        g.setColorAt(0.0, c0)
        g.setColorAt(1.0, c1)
        return QBrush(g)
    return QBrush(c0)


def clip_path_local(doc: Any, fr: Any) -> QPainterPath | None:
    """Maskenpfad relativ zum Inhaltsrahmen (lokal)."""
    cid = getattr(fr, "clip_id", None) or ""
    if not cid:
        return None
    mask = doc.frame_by_id(cid) if hasattr(doc, "frame_by_id") else None
    if mask is None or mask.id == fr.id:
        return None
    from .extrude import path_for_shape

    shape = mask.shape if mask.kind in ("shape", "image") else "rectangle"
    path = path_for_shape(shape or "rectangle", mask.width, mask.height)
    path.translate(mask.x - fr.x, mask.y - fr.y)
    return path


def apply_clip(painter: QPainter, doc: Any, fr: Any) -> None:
    path = clip_path_local(doc, fr)
    if path is not None and path.elementCount() > 0:
        painter.setClipPath(path, Qt.IntersectClip)


def apply_opacity(painter: QPainter, fr: Any) -> None:
    op = getattr(fr, "opacity", 1.0)
    try:
        painter.setOpacity(max(0.05, min(1.0, float(op if op is not None else 1.0))))
    except Exception:
        painter.setOpacity(1.0)


def paint_drop_shadow(painter: QPainter, path: QPainterPath, fr: Any) -> None:
    if not getattr(fr, "shadow", False):
        return
    if path is None or path.elementCount() == 0:
        path = QPainterPath()
        path.addRect(QRectF(0, 0, fr.width, fr.height))
    painter.save()
    dx = float(getattr(fr, "shadow_dx", 3.0) or 3.0)
    dy = float(getattr(fr, "shadow_dy", 3.0) or 3.0)
    painter.translate(dx, dy)
    painter.fillPath(path, parse_color(getattr(fr, "shadow_color", None) or "#00000066", "#00000066"))
    painter.restore()
