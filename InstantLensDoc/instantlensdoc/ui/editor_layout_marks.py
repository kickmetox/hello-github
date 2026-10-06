"""Overlay: Breiten-/Druck-/Kopf-Fuß-Marken im Texteditor (nicht DTP-Canvas)."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from instantlensdoc.core.editor_layout_marks import (
    EditorLayoutMarks,
    color_bar_patches_mm,
    crop_mark_segments_mm,
    footer_band_rect,
    header_band_rect,
    hit_test_band,
    mm_to_px,
    px_to_mm,
    register_marks_mm,
)


def _qcolor(hex_color: str, alpha: int = 255) -> QColor:
    c = QColor(hex_color)
    if not c.isValid():
        c = QColor("#333333")
    c.setAlpha(int(max(0, min(255, alpha))))
    return c


def draw_width_marks(
    painter: QPainter,
    *,
    page: QRectF,
    type_area: QRectF,
    marks: EditorLayoutMarks,
    dpi: float,
    columns: int = 1,
) -> None:
    """Ticks am Satzspiegel-Rand (mm) — Linealstreifen oben + Kanten."""
    color = _qcolor(marks.width_color, 220)
    painter.setPen(QPen(color, 1.2))
    painter.setBrush(Qt.NoBrush)
    x0, x1 = type_area.left(), type_area.right()
    y0, y1 = type_area.top(), type_area.bottom()
    painter.drawLine(QPointF(x0, page.top()), QPointF(x0, page.bottom()))
    painter.drawLine(QPointF(x1, page.top()), QPointF(x1, page.bottom()))
    band = 16.0
    ruler = QRectF(page.left(), page.top(), page.width(), band)
    painter.fillRect(ruler, _qcolor("#F3F3F3", 210))
    painter.setPen(QPen(_qcolor("#B0B0B0"), 1))
    painter.drawLine(ruler.bottomLeft(), ruler.bottomRight())
    font = QFont("Sans Serif", 7)
    painter.setFont(font)
    px_mm = mm_to_px(1.0, dpi)
    if px_mm < 0.4:
        return
    origin = page.left()
    lo = int((type_area.left() - origin) / px_mm) - 2
    hi = int((type_area.right() - origin) / px_mm) + 2
    painter.setPen(QPen(color, 1))
    for mm in range(max(0, lo), hi + 1):
        pos = origin + mm * px_mm
        if pos < page.left() - 1 or pos > page.right() + 1:
            continue
        major = mm % 10 == 0
        tick = 12.0 if major else (8.0 if mm % 5 == 0 else 4.0)
        painter.drawLine(QPointF(pos, page.top() + band - tick), QPointF(pos, page.top() + band))
        if major:
            painter.drawText(QPointF(pos + 2, page.top() + 10), str(mm))
    # Endmarken mit mm-Beschriftung am Satzspiegel
    left_mm = px_to_mm(type_area.left() - page.left(), dpi)
    right_mm = px_to_mm(type_area.right() - page.left(), dpi)
    painter.setPen(QPen(color, 1.6))
    for x, label in ((x0, f"{left_mm:.0f}"), (x1, f"{right_mm:.0f}")):
        painter.drawLine(QPointF(x, y0), QPointF(x, y0 + 10))
        painter.drawText(QPointF(x + 3, y0 + 22), f"{label} mm")
    painter.setPen(QPen(color, 1, Qt.DotLine))
    painter.drawLine(QPointF(x0, y0), QPointF(x1, y0))
    painter.drawLine(QPointF(x0, y1), QPointF(x1, y1))
    cols = max(1, int(columns or 1))
    if cols > 1:
        gap = mm_to_px(4.0, dpi)
        inner = max(1.0, type_area.width() - gap * (cols - 1))
        col_w = inner / float(cols)
        painter.setPen(QPen(color, 1, Qt.DashLine))
        for i in range(1, cols):
            x = type_area.left() + i * (col_w + gap)
            painter.drawLine(QPointF(x, y0), QPointF(x, y1))
            painter.drawLine(QPointF(x, page.top()), QPointF(x, page.top() + band))


def draw_print_marks(
    painter: QPainter,
    *,
    page: QRectF,
    marks: EditorLayoutMarks,
    dpi: float,
) -> None:
    """Crop / Bleed / Register / Farbkeil um die Seite, nicht im Textspiegel."""
    page_w_mm = px_to_mm(page.width(), dpi)
    page_h_mm = px_to_mm(page.height(), dpi)
    ox, oy = page.left(), page.top()

    def to_px(mm_x: float, mm_y: float) -> QPointF:
        return QPointF(ox + mm_to_px(mm_x, dpi), oy + mm_to_px(mm_y, dpi))

    if marks.show_bleed and marks.bleed_mm > 0:
        pad = mm_to_px(marks.bleed_mm, dpi)
        painter.setPen(QPen(_qcolor(marks.bleed_color, 200), 1.0))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRectF(page.x() - pad, page.y() - pad, page.width() + 2 * pad, page.height() + 2 * pad))
    if marks.show_crop:
        painter.setPen(QPen(_qcolor(marks.print_color, 230), 1.2))
        for x1, y1, x2, y2 in crop_mark_segments_mm(
            page_w_mm, page_h_mm, crop_mm=marks.crop_mm, gap_mm=marks.gap_mm
        ):
            painter.drawLine(to_px(x1, y1), to_px(x2, y2))
    if marks.show_register:
        painter.setPen(QPen(_qcolor(marks.print_color, 230), 1.0))
        painter.setBrush(Qt.NoBrush)
        for cx, cy, r_mm in register_marks_mm(
            page_w_mm, page_h_mm, register_mm=marks.register_mm, gap_mm=marks.gap_mm
        ):
            c = to_px(cx, cy)
            r = mm_to_px(r_mm, dpi)
            painter.drawLine(QPointF(c.x() - r, c.y()), QPointF(c.x() + r, c.y()))
            painter.drawLine(QPointF(c.x(), c.y() - r), QPointF(c.x(), c.y() + r))
            painter.drawEllipse(c, r * 0.45, r * 0.45)
    if marks.show_color_bar:
        for x, y, w, h, col in color_bar_patches_mm(
            page_w_mm, page_h_mm, bar_mm=marks.color_bar_mm, gap_mm=marks.gap_mm
        ):
            painter.fillRect(
                QRectF(
                    ox + mm_to_px(x, dpi),
                    oy + mm_to_px(y, dpi),
                    mm_to_px(w, dpi),
                    mm_to_px(h, dpi),
                ),
                _qcolor(col),
            )


def draw_header_footer_marks(
    painter: QPainter,
    *,
    header: QRectF,
    footer: QRectF,
    marks: EditorLayoutMarks,
    header_text: str = "",
    footer_text: str = "",
) -> None:
    color = _qcolor(marks.header_footer_color, 200)
    fill = _qcolor(marks.header_footer_color, 28)
    pen = QPen(color, 1.1, Qt.DotLine)
    painter.setPen(pen)
    painter.setBrush(fill)
    painter.drawRect(header)
    painter.drawRect(footer)
    font = QFont("Sans Serif", 8)
    painter.setFont(font)
    painter.setPen(_qcolor(marks.header_footer_color, 230))
    h_label = header_text.strip() or "Kopfzeile"
    f_label = footer_text.strip() or "Fußzeile"
    painter.drawText(header.adjusted(6, 2, -6, -2), Qt.AlignVCenter | Qt.AlignLeft, h_label)
    painter.drawText(footer.adjusted(6, 2, -6, -2), Qt.AlignVCenter | Qt.AlignLeft, f_label)


class EditorLayoutMarksOverlay(QWidget):
    """Transparente Fläche über dem Editor: Marken zeichnen, Bänder klickbar."""

    headerFooterClicked = Signal(str)

    def __init__(self, editor: QWidget):
        super().__init__(editor)
        self.setObjectName("editorLayoutMarksOverlay")
        self._editor = editor
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self._header = QRectF()
        self._footer = QRectF()

    def hit_test(self, pos) -> str | None:
        return hit_test_band(
            float(pos.x()),
            float(pos.y()),
            (
                self._header.x(),
                self._header.y(),
                self._header.width(),
                self._header.height(),
            ),
            (
                self._footer.x(),
                self._footer.y(),
                self._footer.width(),
                self._footer.height(),
            ),
        )

    def paintEvent(self, event) -> None:  # noqa: N802
        ed = self._editor
        marks = getattr(ed, "layout_marks", lambda: EditorLayoutMarks())()
        if marks is None or not marks.any_screen():
            self._header = QRectF()
            self._footer = QRectF()
            return
        geom = ed.layout_marks_geometry()
        if geom is None:
            self._header = QRectF()
            self._footer = QRectF()
            return
        page = geom["page"]
        type_area = geom["type_area"]
        dpi = float(geom.get("dpi") or 96.0)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        try:
            if marks.screen_print():
                draw_print_marks(painter, page=page, marks=marks, dpi=dpi)
            if marks.screen_width():
                draw_width_marks(
                    painter,
                    page=page,
                    type_area=type_area,
                    marks=marks,
                    dpi=dpi,
                    columns=int(geom.get("columns") or 1),
                )
            if marks.screen_header_footer():
                hh = mm_to_px(marks.header_height_mm, dpi)
                fh = mm_to_px(marks.footer_height_mm, dpi)
                hr = header_band_rect(
                    page.x(), page.y(), page.width(), height=hh
                )
                fr = footer_band_rect(
                    page.x(), page.y(), page.width(), page.height(), height=fh
                )
                self._header = QRectF(*hr)
                self._footer = QRectF(*fr)
                draw_header_footer_marks(
                    painter,
                    header=self._header,
                    footer=self._footer,
                    marks=marks,
                    header_text=str(getattr(ed, "document_header", lambda: "")()),
                    footer_text=str(getattr(ed, "document_footer", lambda: "")()),
                )
            else:
                self._header = QRectF()
                self._footer = QRectF()
        finally:
            painter.end()
