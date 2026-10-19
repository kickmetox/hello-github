from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF

from officedisplay.input.pointer import stroke_width


_PIXMAPS: dict[str, QImage] = {}


def qcolor(value: str | None, fallback: str = "#000000") -> QColor:
    color = QColor(value or fallback)
    if not color.isValid():
        color = QColor(fallback)
    return color


def paint_slide(painter: QPainter, presentation, slide, rect: QRectF, selected: set[str] | None = None) -> None:
    selected = selected or set()
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    _background(painter, slide, rect)
    for obj in slide.objects:
        _paint_object(painter, presentation, obj, rect, 0, 0, 1, 1, selected)
    painter.restore()


def render_thumb(presentation, slide, width: int = 220):
    height = max(40, int(width * presentation.height / max(1, presentation.width)))
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor("#FFFFFF"))
    painter = QPainter(image)
    paint_slide(painter, presentation, slide, QRectF(0, 0, width, height))
    painter.end()
    return image


def _background(painter: QPainter, slide, rect: QRectF) -> None:
    bg = slide.background
    opacity = max(0.0, min(float(bg.opacity), 1.0))
    has_image = bool(bg.image) and Path(bg.image).is_file()
    painter.save()
    painter.setOpacity(1.0 if has_image else max(0.05, min(opacity, 1.0)))
    if bg.mode == "gradient":
        angle = math.radians(bg.angle)
        center = rect.center()
        length = max(rect.width(), rect.height())
        start = center + QPointF(math.cos(angle) * length / -2, math.sin(angle) * length / -2)
        end = center + QPointF(math.cos(angle) * length / 2, math.sin(angle) * length / 2)
        gradient = QLinearGradient(start, end)
        gradient.setColorAt(0, qcolor(bg.color, "#0B63E5"))
        gradient.setColorAt(1, qcolor(bg.color2, "#08357A"))
        painter.fillRect(rect, gradient)
    else:
        painter.fillRect(rect, qcolor(bg.color, "#FFFFFF"))
    if has_image:
        image = _image(bg.image)
        if image is not None:
            painter.setOpacity(opacity)
            _draw_fit(painter, image, rect, bg.fit, bg.offset_x, bg.offset_y)
    painter.restore()


def _draw_fit(painter, image: QImage, rect: QRectF, fit: str, ox: float, oy: float) -> None:
    if fit == "contain":
        scale = min(rect.width() / image.width(), rect.height() / image.height())
    elif fit == "tile":
        scale = max(0.2, rect.width() / image.width() / 3)
        painter.drawImage(rect.translated(ox * rect.width(), oy * rect.height()), image)
        return
    else:
        scale = max(rect.width() / image.width(), rect.height() / image.height())
    width, height = image.width() * scale, image.height() * scale
    x = rect.x() + (rect.width() - width) / 2 + ox * rect.width()
    y = rect.y() + (rect.height() - height) / 2 + oy * rect.height()
    painter.drawImage(QRectF(x, y, width, height), image)


def _paint_object(painter, presentation, obj, rect, ox, oy, ow, oh, selected) -> None:
    ax = ox + obj.x * ow
    ay = oy + obj.y * oh
    aw = obj.w * ow
    ah = obj.h * oh
    box = QRectF(rect.x() + ax * rect.width(), rect.y() + ay * rect.height(), aw * rect.width(), ah * rect.height())
    painter.save()
    painter.setOpacity(float(obj.props.get("opacity", 1)))
    if obj.rotation:
        painter.translate(box.center())
        painter.rotate(obj.rotation)
        painter.translate(-box.center())
    if obj.kind == "group":
        for child in obj.children:
            _paint_object(painter, presentation, child, box, 0, 0, 1, 1, selected)
    elif obj.kind == "text":
        _text(painter, obj, box, rect.height() / max(1, presentation.height))
    elif obj.kind == "shape":
        _shape(painter, obj, box)
    elif obj.kind == "image":
        image = _image(obj.props.get("render_path") or obj.props.get("path"))
        if image is not None:
            painter.drawImage(box, image)
        else:
            painter.fillRect(box, QColor("#E8EEF8"))
    elif obj.kind == "path":
        _path(painter, obj, rect, ox, oy, ow, oh, rect.height() / max(1, presentation.height))
    elif obj.kind == "kpi":
        painter.fillRect(box, QColor("#F4F7FB"))
        painter.setPen(qcolor(obj.props.get("color"), "#0B63E5"))
        font = QFont(obj.props.get("font_family") or "Segoe UI")
        font.setPixelSize(max(8, int(box.height() * 0.34)))
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(box.adjusted(8, 8, -8, -8), Qt.AlignmentFlag.AlignCenter, str(obj.props.get("value") or "–"))
        font.setPixelSize(max(7, int(box.height() * 0.16)))
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor("#243044"))
        painter.drawText(box.adjusted(8, int(box.height() * 0.62), -8, -6), Qt.AlignmentFlag.AlignHCenter, str(obj.props.get("label") or ""))
    elif obj.kind == "chart":
        _chart(painter, obj, box)
    elif obj.kind == "video":
        painter.fillRect(box, QColor("#1B1F2A"))
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(box, Qt.AlignmentFlag.AlignCenter, "Video\n" + Path(obj.props.get("path") or "").name)
    elif obj.kind == "model3d":
        image = _image(obj.props.get("path"))
        if image is not None:
            painter.drawImage(box, image)
        else:
            painter.fillRect(box, QColor("#0B63E5"))
    if obj.id in selected:
        pen = QPen(QColor("#F28C28"), 2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(box)
    painter.restore()


def _text(painter: QPainter, obj, box: QRectF, scale: float = 1.0) -> None:
    font = QFont(obj.props.get("font_family") or "Segoe UI")
    font.setPixelSize(max(1, int((obj.props.get("font_size") or 18) * scale)))
    font.setBold(bool(obj.props.get("bold")))
    font.setItalic(bool(obj.props.get("italic")))
    font.setUnderline(bool(obj.props.get("underline")))
    painter.setFont(font)
    painter.setPen(qcolor(obj.props.get("color"), "#1B1F2A"))
    align = {
        "left": Qt.AlignmentFlag.AlignLeft,
        "center": Qt.AlignmentFlag.AlignHCenter,
        "right": Qt.AlignmentFlag.AlignRight,
    }.get(obj.props.get("align") or "left", Qt.AlignmentFlag.AlignLeft)
    text = str(obj.props.get("text") or "")
    valign = obj.props.get("valign") or "top"
    if valign == "top":
        painter.drawText(box, align | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, text)
        return
    measured = painter.boundingRect(QRectF(0, 0, box.width(), 100000), align | Qt.TextFlag.TextWordWrap, text)
    extra = box.height() - measured.height()
    if extra > 0 and valign == "middle":
        box = box.adjusted(0, extra / 2, 0, 0)
    elif extra > 0 and valign == "bottom":
        box = box.adjusted(0, extra, 0, 0)
    painter.drawText(box, align | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, text)


def _shape_clip(kind: str, box: QRectF) -> QPainterPath:
    path = QPainterPath()
    if kind == "ellipse":
        path.addEllipse(box)
    elif kind == "roundrect":
        path.addRoundedRect(box, 16, 16)
    elif kind == "triangle":
        path.addPolygon(QPolygonF([box.center() + QPointF(0, -box.height() / 2), box.bottomRight(), box.bottomLeft()]))
    elif kind == "diamond":
        path.addPolygon(
            QPolygonF(
                [
                    QPointF(box.center().x(), box.top()),
                    QPointF(box.right(), box.center().y()),
                    QPointF(box.center().x(), box.bottom()),
                    QPointF(box.left(), box.center().y()),
                ]
            )
        )
    elif kind == "star":
        path.addPolygon(_star(box))
    else:
        path.addRect(box)
    return path


def _shape(painter: QPainter, obj, box: QRectF) -> None:
    kind = obj.props.get("shape") or "rect"
    image = _image(obj.props.get("image"))
    if image is not None and kind != "line":
        painter.save()
        painter.setClipPath(_shape_clip(kind, box))
        painter.drawImage(box, image)
        painter.restore()
        painter.setBrush(Qt.BrushStyle.NoBrush)
    elif image is not None and kind == "line":
        painter.drawImage(box, image)
        painter.setBrush(Qt.BrushStyle.NoBrush)
    else:
        painter.setBrush(QBrush(qcolor(obj.props.get("fill"), "#0B63E5")))
    stroke = obj.props.get("stroke") or "#00000000"
    width = int(obj.props.get("stroke_width") or 0)
    painter.setPen(QPen(qcolor(stroke), width) if width else Qt.PenStyle.NoPen)
    if kind == "ellipse":
        painter.drawEllipse(box)
    elif kind == "roundrect":
        painter.drawRoundedRect(box, 16, 16)
    elif kind == "triangle":
        painter.drawPolygon(QPolygonF([box.center() + QPointF(0, -box.height() / 2), box.bottomRight(), box.bottomLeft()]))
    elif kind == "diamond":
        painter.drawPolygon(
            QPolygonF(
                [
                    QPointF(box.center().x(), box.top()),
                    QPointF(box.right(), box.center().y()),
                    QPointF(box.center().x(), box.bottom()),
                    QPointF(box.left(), box.center().y()),
                ]
            )
        )
    elif kind == "star":
        painter.drawPolygon(_star(box))
    elif kind == "arrow":
        body = QRectF(box.left(), box.top() + box.height() * 0.25, box.width() * 0.65, box.height() * 0.5)
        painter.drawRect(body)
        painter.drawPolygon(
            QPolygonF(
                [
                    QPointF(box.left() + box.width() * 0.55, box.top()),
                    QPointF(box.right(), box.center().y()),
                    QPointF(box.left() + box.width() * 0.55, box.bottom()),
                ]
            )
        )
    elif kind == "line":
        painter.setPen(QPen(qcolor(obj.props.get("fill"), "#0B63E5"), max(2, width or 3)))
        painter.drawLine(box.topLeft(), box.bottomRight())
    else:
        painter.drawRect(box)


def _star(box: QRectF) -> QPolygonF:
    points = []
    cx, cy = box.center().x(), box.center().y()
    rx, ry = box.width() / 2, box.height() / 2
    for index in range(10):
        angle = -math.pi / 2 + index * math.pi / 5
        radius = 1 if index % 2 == 0 else 0.45
        points.append(QPointF(cx + math.cos(angle) * rx * radius, cy + math.sin(angle) * ry * radius))
    return QPolygonF(points)


def _path(painter, obj, rect, ox, oy, ow, oh, scale: float = 1.0) -> None:
    points = obj.props.get("points") or []
    color = qcolor(obj.props.get("color"), "#0B63E5")
    if obj.props.get("highlighter"):
        color.setAlpha(90)
    base = float(obj.props.get("base_width") or 6)
    curve = float(obj.props.get("curve") or 1)
    kind = obj.props.get("pointer") or "pen"
    local = obj.props.get("coords") != "slide"
    origin_x = ox + obj.x * ow if local else ox
    origin_y = oy + obj.y * oh if local else oy
    span_w = obj.w * ow if local else ow
    span_h = obj.h * oh if local else oh
    for index in range(1, len(points)):
        x1, y1, p1 = points[index - 1]
        x2, y2, p2 = points[index]
        width = max(0.6, stroke_width(base, (p1 + p2) / 2, curve, kind) * scale)
        pen = QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(
            QPointF(rect.x() + (origin_x + x1 * span_w) * rect.width(), rect.y() + (origin_y + y1 * span_h) * rect.height()),
            QPointF(rect.x() + (origin_x + x2 * span_w) * rect.width(), rect.y() + (origin_y + y2 * span_h) * rect.height()),
        )


def _chart(painter: QPainter, obj, box: QRectF) -> None:
    painter.fillRect(box, QColor("#FFFFFF"))
    painter.setPen(QColor("#D5DDEA"))
    painter.drawRect(box)
    series = (obj.props.get("series") or [{}])[0]
    values = [float(item) for item in (series.get("values") or [])]
    if not values:
        painter.setPen(QColor("#243044"))
        painter.drawText(box.adjusted(8, 8, -8, -8), Qt.AlignmentFlag.AlignCenter, "Keine Zahlen in der Quelle")
        return
    categories = obj.props.get("categories") or [str(i + 1) for i in range(len(values))]
    peak = max(values) if values else 1
    peak = peak or 1
    colors = ["#0B63E5", "#F28C28", "#3CB44B", "#E23B3B", "#7C5CFF"]
    if obj.props.get("chart_type") == "pie":
        total = sum(values) or 1
        start = 0
        for index, value in enumerate(values):
            span = int(360 * 16 * value / total)
            painter.setBrush(QColor(colors[index % len(colors)]))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPie(box.adjusted(12, 12, -12, -12), start, span)
            start += span
        return
    left = box.left() + 28
    width = (box.width() - 40) / max(1, len(values))
    for index, value in enumerate(values):
        bar_h = (box.height() - 36) * (value / peak)
        bar = QRectF(left + index * width + 4, box.bottom() - 20 - bar_h, max(4, width - 8), bar_h)
        painter.fillRect(bar, QColor(colors[index % len(colors)]))
        painter.setPen(QColor("#1B1F2A"))
        painter.drawText(QRectF(bar.left(), box.bottom() - 18, width, 16), Qt.AlignmentFlag.AlignLeft, str(categories[index])[:8])
    if obj.props.get("example"):
        painter.setPen(QColor("#B42318"))
        painter.drawText(box.adjusted(8, 4, -8, -4), "Beispielwerte")


def _image(path: str | None) -> QImage | None:
    if not path or not Path(path).is_file():
        return None
    cached = _PIXMAPS.get(path)
    if cached is not None:
        return cached
    from officedisplay.io.media import load_qimage

    image, _hint = load_qimage(path)
    if image is None or image.isNull():
        return None
    _PIXMAPS[path] = image
    return image


def clear_image_cache(path: str | None = None) -> None:
    if path:
        _PIXMAPS.pop(path, None)
    else:
        _PIXMAPS.clear()
