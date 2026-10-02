"""PDF-Ansicht: Zoom, Annotationen, Formen, Messung, Text-Overlay, Seitenops."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QPointF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QImage,
    QKeySequence,
    QPainter,
    QPen,
    QPixmap,
    QPolygonF,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ild_pdf import (
    DRAG_TYPES,
    Annotation,
    AnnotationStore,
    AnnotationType,
    STAMP_PRESETS,
    bake_text_overlays,
    find_text_rects,
    import_page_text_as_overlays,
    render_page,
)
from ild_pdf.pages import delete_pages, reorder_pages, rotate_page
from instantlensdoc.core.app_settings import (
    get_ann_highlight_color,
    get_ann_pen_color,
    get_default_zoom_scale,
    set_ann_highlight_color,
    set_ann_pen_color,
)


class PageReorderDialog(QDialog):
    """Seitenreihenfolge per Liste ändern (hoch/runter)."""

    def __init__(self, page_count: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seiten neu anordnen")
        self.resize(360, 420)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Reihenfolge (oben = Seite 1):"))
        self.list = QListWidget()
        for i in range(page_count):
            self.list.addItem(QListWidgetItem(f"Seite {i + 1}"))
            self.list.item(i).setData(256, i)
        layout.addWidget(self.list)
        row = QHBoxLayout()
        btn_up = QPushButton("▲ Hoch")
        btn_down = QPushButton("▼ Runter")
        btn_up.clicked.connect(self._up)
        btn_down.clicked.connect(self._down)
        row.addWidget(btn_up)
        row.addWidget(btn_down)
        layout.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _up(self):
        row = self.list.currentRow()
        if row <= 0:
            return
        item = self.list.takeItem(row)
        self.list.insertItem(row - 1, item)
        self.list.setCurrentRow(row - 1)

    def _down(self):
        row = self.list.currentRow()
        if row < 0 or row >= self.list.count() - 1:
            return
        item = self.list.takeItem(row)
        self.list.insertItem(row + 1, item)
        self.list.setCurrentRow(row + 1)

    def new_order(self) -> list[int]:
        order: list[int] = []
        for i in range(self.list.count()):
            order.append(int(self.list.item(i).data(256)))
        return order


class TextOverlayEditDialog(QDialog):
    """Overlay-Textblock bearbeiten (Sidecar, kein natives PDF-Rewrite)."""

    def __init__(self, ann: Annotation, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Text-Overlay bearbeiten")
        self.resize(420, 280)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.text = QPlainTextEdit()
        self.text.setPlainText(ann.text or "")
        self.font_size = QDoubleSpinBox()
        self.font_size.setRange(6, 96)
        self.font_size.setValue(float(ann.font_size or 12))
        self.color = QLineEdit(ann.color or "#1A5276")
        form.addRow("Text:", self.text)
        form.addRow("Schriftgröße (px):", self.font_size)
        form.addRow("Farbe:", self.color)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> dict:
        return {
            "text": self.text.toPlainText(),
            "font_size": float(self.font_size.value()),
            "color": self.color.text().strip() or "#1A5276",
        }


class PdfCanvas(QLabel):
    """Gerenderte PDF-Seite; Klick/Drag setzt Annotationen."""

    annotation_placed = Signal(float, float)
    drag_finished = Signal(float, float, float, float)  # x0,y0,x1,y1
    overlay_edit_requested = Signal(str)  # ann id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(200, 200)
        self._pixmap: Optional[QPixmap] = None
        self._annotations: list[Annotation] = []
        self._drag_tool: AnnotationType | None = None
        self._drag_start: tuple[float, float] | None = None
        self._drag_current: tuple[float, float] | None = None
        self._scale = 1.5
        self._search_rects: list[tuple[float, float, float, float]] = []
        self._search_active: int = -1
        self.setMouseTracking(True)

    def set_drag_tool(self, tool: AnnotationType | None):
        self._drag_tool = tool if tool in DRAG_TYPES else None

    def set_search_highlights(
        self,
        rects: list[tuple[float, float, float, float]] | None,
        active: int = -1,
    ):
        self._search_rects = list(rects or [])
        self._search_active = active if 0 <= active < len(self._search_rects) else -1
        self._repaint_overlay()

    def clear_search_highlights(self):
        if self._search_rects or self._search_active >= 0:
            self._search_rects = []
            self._search_active = -1
            self._repaint_overlay()

    def set_page_image(
        self,
        image,
        annotations: list[Annotation] | None = None,
        scale: float = 1.5,
    ):
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        data = image.tobytes("raw", "RGBA")
        qimg = QImage(data, image.width, image.height, QImage.Format_RGBA8888)
        self._pixmap = QPixmap.fromImage(qimg.copy())
        self._annotations = annotations or []
        self._scale = scale
        self._drag_start = None
        self._drag_current = None
        self._repaint_overlay()

    def _map_to_page(self, event) -> tuple[float, float] | None:
        if self._pixmap is None:
            return None
        pos = event.position()
        pm = self.pixmap()
        if pm is None:
            return None
        lx = (self.width() - pm.width()) / 2
        ly = (self.height() - pm.height()) / 2
        x = pos.x() - lx
        y = pos.y() - ly
        if 0 <= x <= pm.width() and 0 <= y <= pm.height():
            return float(x), float(y)
        return None

    def _hit_overlay(self, x: float, y: float) -> Annotation | None:
        for ann in reversed(self._annotations):
            if ann.type not in (AnnotationType.TEXT_OVERLAY, AnnotationType.TEXT, AnnotationType.STICKY):
                continue
            if ann.x <= x <= ann.x + max(ann.width, 40) and ann.y <= y <= ann.y + max(ann.height, 20):
                return ann
        return None

    def _draw_ann(self, painter: QPainter, ann: Annotation):
        color = QColor(ann.color)
        color.setAlpha(90 if ann.type == AnnotationType.HIGHLIGHT else 200)
        pen = QPen(QColor(ann.color))
        pen.setWidth(2)
        painter.setPen(pen)
        x, y = int(ann.x), int(ann.y)
        w, h = int(ann.width), int(ann.height)

        if ann.type == AnnotationType.HIGHLIGHT:
            painter.fillRect(x, y, w, h, color)
        elif ann.type == AnnotationType.REDACTION:
            rw, rh = max(w, 4), max(h, 4)
            painter.fillRect(x, y, rw, rh, QColor(0, 0, 0, 230))
            # Sichtbarer Hinweisrahmen (besserer UX vor Einbrennen)
            painter.setPen(QPen(QColor(220, 50, 50), 2, Qt.DashLine))
            painter.drawRect(x, y, rw, rh)
            painter.setPen(QColor(255, 220, 220))
            if rw >= 36 and rh >= 14:
                painter.drawText(x + 3, y + min(14, rh - 2), "REDACT")
        elif ann.type == AnnotationType.UNDERLINE:
            painter.drawLine(x, y + h, x + w, y + h)
        elif ann.type == AnnotationType.STICKY:
            painter.fillRect(x, y, max(w, 80), max(h, 60), QColor(255, 255, 150, 200))
            painter.drawText(x + 4, y + 16, (ann.text or "Notiz")[:40])
        elif ann.type == AnnotationType.TEXT:
            painter.drawRect(x, y, w, h)
            painter.drawText(x + 4, y + 16, (ann.text or "")[:60])
        elif ann.type == AnnotationType.TEXT_OVERLAY:
            painter.fillRect(x, y, max(w, 40), max(h, 18), QColor(255, 255, 255, 160))
            painter.setPen(QPen(QColor(ann.color), 1, Qt.DashLine))
            painter.drawRect(x, y, max(w, 40), max(h, 18))
            painter.setPen(QColor(ann.color))
            painter.drawText(x + 2, y + int(max(ann.font_size, 12)), (ann.text or "")[:80])
        elif ann.type in (AnnotationType.STAMP, AnnotationType.SIGNATURE):
            if ann.text.startswith("img:"):
                img_path = Path(ann.text[4:])
                if img_path.is_file():
                    pm = QPixmap(str(img_path))
                    if not pm.isNull():
                        painter.drawPixmap(
                            x,
                            y,
                            max(int(w), 40),
                            max(int(h), 24),
                            pm.scaled(
                                max(int(w), 40),
                                max(int(h), 24),
                                Qt.KeepAspectRatio,
                                Qt.SmoothTransformation,
                            ),
                        )
                        return
            if ann.type == AnnotationType.SIGNATURE:
                painter.setPen(QPen(QColor("#2C3E50"), 2, Qt.DashLine))
                painter.drawRect(x, y, max(w, 80), max(h, 32))
                painter.drawText(x + 4, y + 16, "Signatur")
                return
            stamp_color = QColor(ann.color if ann.color != "#FFFF00" else "#C0392B")
            painter.setPen(QPen(stamp_color, 3))
            painter.drawRect(x, y, max(w, 100), max(h, 36))
            painter.drawText(x + 8, y + max(h, 36) // 2 + 4, (ann.text or "STEMPEL")[:24])
        elif ann.type == AnnotationType.SIGNATURE_FIELD:
            painter.setPen(QPen(QColor(ann.color or "#7F8C8D"), 2, Qt.DashLine))
            painter.setBrush(QColor(255, 255, 255, 30))
            fh = max(int(h), 48)
            fw = max(int(w), 160)
            painter.drawRect(x, y, fw, fh)
            painter.drawLine(x + 8, y + fh - 10, x + fw - 8, y + fh - 10)
            painter.setPen(QColor(ann.color or "#7F8C8D"))
            painter.drawText(x + 8, y + 18, (ann.text or "Unterschrift")[:40])
        elif ann.type == AnnotationType.CALLOUT:
            box_w, box_h = max(w, 100), max(h, 40)
            painter.setBrush(QColor(255, 255, 220, 220))
            painter.drawRect(x, y, box_w, box_h)
            painter.drawText(x + 4, y + 16, (ann.text or "Callout")[:40])
            cx = int(ann.callout_x) if ann.callout_x else x - 40
            cy = int(ann.callout_y) if ann.callout_y else y + box_h + 30
            painter.drawLine(x, y + box_h, cx, cy)
            painter.drawEllipse(cx - 3, cy - 3, 6, 6)
        elif ann.type == AnnotationType.RECTANGLE:
            painter.setBrush(QColor(ann.color))
            c = QColor(ann.color)
            c.setAlpha(40)
            painter.fillRect(x, y, w, h, c)
            painter.drawRect(x, y, w, h)
        elif ann.type in (AnnotationType.LINE, AnnotationType.ARROW, AnnotationType.MEASURE):
            x2, y2 = ann.end_point()
            painter.drawLine(int(ann.x), int(ann.y), int(x2), int(y2))
            if ann.type == AnnotationType.ARROW:
                self._draw_arrow_head(painter, ann.x, ann.y, x2, y2)
            if ann.type == AnnotationType.MEASURE:
                mid_x = (ann.x + x2) / 2
                mid_y = (ann.y + y2) / 2
                label = ann.text or ann.measure_label(self._scale)
                painter.drawText(int(mid_x) + 4, int(mid_y) - 4, label)

    def _draw_arrow_head(self, painter: QPainter, x0: float, y0: float, x1: float, y1: float):
        import math

        angle = math.atan2(y1 - y0, x1 - x0)
        size = 12.0
        p1 = QPointF(x1, y1)
        p2 = QPointF(x1 - size * math.cos(angle - 0.4), y1 - size * math.sin(angle - 0.4))
        p3 = QPointF(x1 - size * math.cos(angle + 0.4), y1 - size * math.sin(angle + 0.4))
        painter.setBrush(QColor(painter.pen().color()))
        painter.drawPolygon(QPolygonF([p1, p2, p3]))

    def _repaint_overlay(self):
        if self._pixmap is None:
            return
        pm = QPixmap(self._pixmap)
        painter = QPainter(pm)
        # Temporäre Textsuche-Highlights (unter Annotationen)
        for i, (sx, sy, sw, sh) in enumerate(self._search_rects):
            if i == self._search_active:
                fill = QColor(255, 140, 0, 140)
                pen = QPen(QColor(230, 90, 0), 2)
            else:
                fill = QColor(255, 230, 80, 110)
                pen = QPen(QColor(200, 160, 0), 1)
            painter.fillRect(int(sx), int(sy), max(int(sw), 2), max(int(sh), 2), fill)
            painter.setPen(pen)
            painter.drawRect(int(sx), int(sy), max(int(sw), 2), max(int(sh), 2))
        for ann in self._annotations:
            self._draw_ann(painter, ann)
        # Drag-Vorschau
        if self._drag_start and self._drag_current and self._drag_tool:
            x0, y0 = self._drag_start
            x1, y1 = self._drag_current
            preview = Annotation(
                page=0,
                type=self._drag_tool,
                x=min(x0, x1),
                y=min(y0, y1),
                width=abs(x1 - x0),
                height=abs(y1 - y0),
                callout_x=x1,
                callout_y=y1,
                color="#2980B9",
            )
            if self._drag_tool in (AnnotationType.LINE, AnnotationType.ARROW, AnnotationType.MEASURE):
                preview.x, preview.y = x0, y0
                preview.callout_x, preview.callout_y = x1, y1
            if self._drag_tool == AnnotationType.MEASURE:
                preview.text = preview.measure_label(self._scale)
            self._draw_ann(painter, preview)
        painter.end()
        self.setPixmap(pm)
        self.adjustSize()

    def mousePressEvent(self, event):
        pt = self._map_to_page(event)
        if pt is None:
            return super().mousePressEvent(event)
        x, y = pt
        if event.button() == Qt.RightButton or (
            event.button() == Qt.LeftButton and event.modifiers() & Qt.ControlModifier
        ):
            hit = self._hit_overlay(x, y)
            if hit:
                self.overlay_edit_requested.emit(hit.id)
                return
        if self._drag_tool and event.button() == Qt.LeftButton:
            self._drag_start = (x, y)
            self._drag_current = (x, y)
            return
        if event.button() == Qt.LeftButton:
            self.annotation_placed.emit(x, y)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start is not None:
            pt = self._map_to_page(event)
            if pt:
                self._drag_current = pt
                self._repaint_overlay()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag_start is not None and event.button() == Qt.LeftButton:
            pt = self._map_to_page(event) or self._drag_current
            if pt:
                x0, y0 = self._drag_start
                x1, y1 = pt
                self._drag_start = None
                self._drag_current = None
                if abs(x1 - x0) > 3 or abs(y1 - y0) > 3:
                    self.drag_finished.emit(x0, y0, x1, y1)
                else:
                    self._repaint_overlay()
            else:
                self._drag_start = None
                self._drag_current = None
                self._repaint_overlay()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        pt = self._map_to_page(event)
        if pt:
            hit = self._hit_overlay(*pt)
            if hit:
                self.overlay_edit_requested.emit(hit.id)
                return
        super().mouseDoubleClickEvent(event)


class PdfViewer(QWidget):
    status = Signal(str)
    annotations_changed = Signal()
    page_changed = Signal(int)  # 0-basiert

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pdf_path: Optional[Path] = None
        self.page_index = 0
        self.page_count = 0
        self.scale = get_default_zoom_scale()
        self.tool: AnnotationType | None = AnnotationType.HIGHLIGHT
        self.store: Optional[AnnotationStore] = None
        self.password: Optional[str] = None
        self._tool_buttons: list[QToolButton] = []
        self._pending_callout_anchor: tuple[float, float] | None = None
        self._zoom_timer = QTimer(self)
        self._zoom_timer.setSingleShot(True)
        self._zoom_timer.setInterval(120)
        self._zoom_timer.timeout.connect(self._apply_pending_zoom)
        self._pending_scale: float | None = None
        self._highlight_color = get_ann_highlight_color()
        self._pen_color = get_ann_pen_color()
        self._search_query = ""
        self._search_rects: list[tuple[float, float, float, float]] = []
        self._search_index = -1

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QHBoxLayout()
        self.lbl_page = QLabel("—")
        self.lbl_zoom = QLabel(f"{int(round(self.scale * 100))}%")
        btn_prev = QPushButton("◀")
        btn_next = QPushButton("▶")
        btn_prev.clicked.connect(self.prev_page)
        btn_next.clicked.connect(self.next_page)
        btn_zoom_in = QPushButton("+")
        btn_zoom_out = QPushButton("−")
        btn_zoom_in.setToolTip("Vergrößern (Ctrl++)")
        btn_zoom_out.setToolTip("Verkleinern (Ctrl+-)")
        btn_zoom_in.clicked.connect(self.zoom_in)
        btn_zoom_out.clicked.connect(self.zoom_out)
        btn_fit = QPushButton("Seite")
        btn_fit.setToolTip("Seite einpassen (Ctrl+0)")
        btn_fit.clicked.connect(self.fit_page)
        btn_fit_w = QPushButton("Breite")
        btn_fit_w.setToolTip("Seitenbreite einpassen (Ctrl+9)")
        btn_fit_w.clicked.connect(self.fit_width)
        btn_undo = QPushButton("↶")
        btn_undo.setToolTip("Annotation rückgängig (Ctrl+Z)")
        btn_undo.clicked.connect(self.undo_annotation)
        btn_redo = QPushButton("↷")
        btn_redo.setToolTip("Annotation wiederholen (Ctrl+Y)")
        btn_redo.clicked.connect(self.redo_annotation)
        btn_rot = QPushButton("90°")
        btn_rot.setToolTip("Aktuelle Seite um 90° drehen")
        btn_rot.clicked.connect(self.rotate_current)
        btn_del = QPushButton("Seite löschen")
        btn_del.clicked.connect(self.delete_current)
        btn_reorder = QPushButton("Neu anordnen…")
        btn_reorder.setToolTip("Seitenreihenfolge ändern")
        btn_reorder.clicked.connect(self.reorder_dialog)
        btn_save_ann = QPushButton("Annot. speichern")
        btn_save_ann.setToolTip("Annotationen in Sidecar *.ildann.json speichern")
        btn_save_ann.clicked.connect(self.save_annotations)
        btn_reload_ann = QPushButton("Annot. laden")
        btn_reload_ann.clicked.connect(self.reload_annotations)
        btn_extract = QPushButton("Seite→Bild")
        btn_extract.setToolTip("Aktuelle Seite als PNG extrahieren")
        btn_extract.clicked.connect(self.extract_page_as_image)
        btn_img_page = QPushButton("Bild→Seite")
        btn_img_page.setToolTip("Bild als neue PDF-Seite anhängen")
        btn_img_page.clicked.connect(self.insert_image_page)
        btn_import_text = QPushButton("Text→Overlay")
        btn_import_text.setToolTip("PDF-Textblöcke als editierbare Overlays (Sidecar)")
        btn_import_text.clicked.connect(self.import_text_overlays)
        btn_bake = QPushButton("Overlay einbrennen")
        btn_bake.setToolTip("TEXT_OVERLAY in PDF-Content schreiben (Helvetica)")
        btn_bake.clicked.connect(self.bake_overlays)

        for t, label in [
            (AnnotationType.HIGHLIGHT, "Highlight"),
            (AnnotationType.REDACTION, "Schwärzen"),
            (AnnotationType.UNDERLINE, "Unterstreichen"),
            (AnnotationType.STICKY, "Notiz"),
            (AnnotationType.TEXT_OVERLAY, "Text-Overlay"),
            (AnnotationType.STAMP, "Stempel"),
            (AnnotationType.CALLOUT, "Callout"),
            (AnnotationType.RECTANGLE, "Rechteck"),
            (AnnotationType.LINE, "Linie"),
            (AnnotationType.ARROW, "Pfeil"),
            (AnnotationType.MEASURE, "Lineal"),
            (AnnotationType.SIGNATURE_FIELD, "Signaturfeld"),
        ]:
            b = QToolButton()
            b.setText(label)
            b.setCheckable(True)
            b.setChecked(t == AnnotationType.HIGHLIGHT)
            b.clicked.connect(lambda checked, tool=t: self._set_tool(tool))
            self._tool_buttons.append(b)
            toolbar.addWidget(b)

        self.btn_hl_color = QPushButton("HL")
        self.btn_hl_color.setToolTip("Highlight-Farbe")
        self.btn_hl_color.setFixedWidth(36)
        self.btn_hl_color.clicked.connect(self._pick_highlight_color)
        self._style_color_btn(self.btn_hl_color, self._highlight_color)
        self.btn_pen_color = QPushButton("Stift")
        self.btn_pen_color.setToolTip("Stift-Farbe (Linie/Pfeil/Rechteck/Unterstreichen)")
        self.btn_pen_color.setFixedWidth(44)
        self.btn_pen_color.clicked.connect(self._pick_pen_color)
        self._style_color_btn(self.btn_pen_color, self._pen_color)
        toolbar.addWidget(self.btn_hl_color)
        toolbar.addWidget(self.btn_pen_color)

        toolbar.addWidget(btn_prev)
        toolbar.addWidget(self.lbl_page)
        toolbar.addWidget(btn_next)
        toolbar.addWidget(btn_undo)
        toolbar.addWidget(btn_redo)
        toolbar.addWidget(btn_zoom_out)
        toolbar.addWidget(self.lbl_zoom)
        toolbar.addWidget(btn_zoom_in)
        toolbar.addWidget(btn_fit)
        toolbar.addWidget(btn_fit_w)
        toolbar.addWidget(btn_rot)
        toolbar.addWidget(btn_del)
        toolbar.addWidget(btn_reorder)
        toolbar.addWidget(btn_save_ann)
        toolbar.addWidget(btn_reload_ann)
        toolbar.addWidget(btn_extract)
        toolbar.addWidget(btn_img_page)
        toolbar.addWidget(btn_import_text)
        toolbar.addWidget(btn_bake)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.canvas = PdfCanvas()
        self.canvas.annotation_placed.connect(self._on_place)
        self.canvas.drag_finished.connect(self._on_drag)
        self.canvas.overlay_edit_requested.connect(self._edit_overlay)
        self.scroll.setWidget(self.canvas)
        layout.addWidget(self.scroll)
        self.canvas.set_drag_tool(AnnotationType.HIGHLIGHT)
        paste_sc = QShortcut(QKeySequence.Paste, self)
        paste_sc.activated.connect(self.paste_clipboard_image)

    @staticmethod
    def _style_color_btn(btn: QPushButton, color: str):
        c = QColor(color)
        if not c.isValid():
            c = QColor("#888888")
        # Kontrasttext
        text = "#111" if c.lightness() > 140 else "#fff"
        btn.setStyleSheet(
            f"QPushButton {{ background:{c.name()}; color:{text}; "
            f"border:1px solid #555; padding:2px 4px; }}"
        )

    def _pick_highlight_color(self):
        initial = QColor(self._highlight_color)
        color = QColorDialog.getColor(initial, self, "Highlight-Farbe")
        if color.isValid():
            self._highlight_color = color.name()
            set_ann_highlight_color(self._highlight_color)
            self._style_color_btn(self.btn_hl_color, self._highlight_color)
            self.status.emit(f"Highlight-Farbe: {self._highlight_color}")

    def _pick_pen_color(self):
        initial = QColor(self._pen_color)
        color = QColorDialog.getColor(initial, self, "Stift-Farbe")
        if color.isValid():
            self._pen_color = color.name()
            set_ann_pen_color(self._pen_color)
            self._style_color_btn(self.btn_pen_color, self._pen_color)
            self.status.emit(f"Stift-Farbe: {self._pen_color}")

    def apply_settings_colors(self):
        self._highlight_color = get_ann_highlight_color()
        self._pen_color = get_ann_pen_color()
        self._style_color_btn(self.btn_hl_color, self._highlight_color)
        self._style_color_btn(self.btn_pen_color, self._pen_color)

    def apply_default_zoom(self):
        self.set_scale(get_default_zoom_scale(), immediate=True)

    def _tool_label(self, tool: AnnotationType) -> str:
        return {
            AnnotationType.HIGHLIGHT: "Highlight",
            AnnotationType.REDACTION: "Schwärzen",
            AnnotationType.UNDERLINE: "Unterstreichen",
            AnnotationType.STICKY: "Notiz",
            AnnotationType.TEXT: "Textfeld",
            AnnotationType.TEXT_OVERLAY: "Text-Overlay",
            AnnotationType.STAMP: "Stempel",
            AnnotationType.CALLOUT: "Callout",
            AnnotationType.RECTANGLE: "Rechteck",
            AnnotationType.LINE: "Linie",
            AnnotationType.ARROW: "Pfeil",
            AnnotationType.MEASURE: "Lineal",
            AnnotationType.SIGNATURE_FIELD: "Signaturfeld",
        }.get(tool, tool.value)

    def _set_tool(self, tool: AnnotationType):
        self.tool = tool
        self._pending_callout_anchor = None
        want = self._tool_label(tool)
        for b in self._tool_buttons:
            b.setChecked(b.text() == want)
        self.canvas.set_drag_tool(tool if tool in DRAG_TYPES else None)
        if tool == AnnotationType.REDACTION:
            n = self.redaction_count()
            self.status.emit(
                f"Werkzeug: Schwärzen — Rechteck ziehen · {n} offen · "
                "PDF → Schwärzung einbrennen"
            )
        else:
            self.status.emit(f"Werkzeug: {tool.value}")

    def load(self, path: str | Path, password: str | None = None) -> bool:
        from PySide6.QtWidgets import QApplication

        from ild_pdf.limits import OPEN_TIMEOUT_HINT, inspect_pdf
        from ild_pdf.render import clear_render_cache
        from ild_pdf.security import needs_password
        from instantlensdoc.ui.password_dialog import ask_pdf_password

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            path = Path(path)
            if not path.is_file():
                QMessageBox.critical(self, "PDF öffnen", f"Datei nicht gefunden:\n{path}")
                return False
            pw = password if password is not None else self.password

            # Passwort nachfragen wenn nötig
            try:
                if pw is None and needs_password(path):
                    pw = ask_pdf_password(self, path)
                    if pw is None:
                        return False
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "PDF öffnen",
                    f"Passwort-Prüfung fehlgeschlagen:\n{e}\n\n{OPEN_TIMEOUT_HINT}",
                )
                return False

            try:
                health = inspect_pdf(path, password=pw)
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "PDF öffnen",
                    f"PDF-Diagnose fehlgeschlagen:\n{e}\n\n{OPEN_TIMEOUT_HINT}",
                )
                return False

            if health.errors:
                # ggf. nochmal Passwort versuchen
                if any("passwort" in e.lower() or "password" in e.lower() for e in health.errors):
                    pw2 = ask_pdf_password(self, path)
                    if pw2 is None:
                        return False
                    pw = pw2
                    try:
                        health = inspect_pdf(path, password=pw)
                    except Exception as e:
                        QMessageBox.critical(
                            self,
                            "PDF öffnen",
                            f"PDF-Diagnose fehlgeschlagen:\n{e}\n\n{OPEN_TIMEOUT_HINT}",
                        )
                        return False
                if health.errors:
                    QMessageBox.critical(
                        self,
                        "PDF öffnen",
                        "PDF kann nicht geöffnet werden:\n\n"
                        + "\n".join(health.errors),
                    )
                    self.pdf_path = None
                    self.store = None
                    self.password = None
                    return False
            if health.warnings:
                r = QMessageBox.warning(
                    self,
                    "Großes PDF",
                    "\n".join(health.warnings) + "\n\nTrotzdem öffnen?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )
                if r != QMessageBox.Yes:
                    return False

            clear_render_cache(path)
            self.pdf_path = path
            self.password = pw
            self.store = AnnotationStore(self.pdf_path)
            self.store.clear_history()
            from ild_pdf import PdfDocument

            with PdfDocument(self.pdf_path, password=self.password) as doc:
                self.page_count = len(doc)
            self.page_index = 0
            self._pending_callout_anchor = None
            self._pending_scale = None
            self._zoom_timer.stop()
            self.scale = get_default_zoom_scale()
            self.clear_search_highlights()
            self.refresh()
            self.annotations_changed.emit()
            self.page_changed.emit(self.page_index)
            return True
        except MemoryError:
            QMessageBox.critical(
                self,
                "PDF öffnen",
                "Nicht genug Speicher für dieses PDF.\n"
                "Tipp: Datei teilen (PDF → zusammenführen/teilen) oder Zoom reduzieren.\n\n"
                + OPEN_TIMEOUT_HINT,
            )
            self.pdf_path = None
            self.store = None
            self.password = None
            return False
        except Exception as e:
            QMessageBox.critical(
                self,
                "PDF öffnen",
                f"PDF konnte nicht geladen werden:\n{e}\n\n{OPEN_TIMEOUT_HINT}",
            )
            self.pdf_path = None
            self.store = None
            self.password = None
            return False
        finally:
            QApplication.restoreOverrideCursor()

    def refresh(self):
        if not self.pdf_path:
            return
        try:
            from ild_pdf.limits import clamp_render_scale
            from ild_pdf import PdfDocument

            with PdfDocument(self.pdf_path, password=self.password) as doc:
                pw, ph = doc.page_size(self.page_index)
            eff, warn = clamp_render_scale(pw, ph, self.scale)
            if warn and abs(eff - self.scale) > 0.01:
                self.scale = eff
                self.status.emit(warn)
            img = render_page(
                self.pdf_path,
                self.page_index,
                scale=self.scale,
                password=self.password,
            )
            anns = self.store.for_page(self.page_index) if self.store else []
            self.canvas.set_page_image(img, anns, scale=self.scale)
            if self._search_rects:
                self.canvas.set_search_highlights(self._search_rects, self._search_index)
            self.lbl_page.setText(f"{self.page_index + 1} / {self.page_count}")
            self.lbl_zoom.setText(f"{int(round(self.scale * 100))}%")
            dirty = " *" if self.store and self.store.dirty else ""
            self.status.emit(f"PDF: {self.pdf_path.name}{dirty}")
        except MemoryError:
            QMessageBox.warning(
                self,
                "PDF-Ansicht",
                "Render fehlgeschlagen (Speicher).\nZoom verringern oder Seite überspringen.",
            )
        except Exception as e:
            QMessageBox.warning(self, "PDF-Ansicht", f"Seite konnte nicht gerendert werden:\n{e}")

    def goto_page(self, page_index: int):
        if 0 <= page_index < self.page_count:
            self.page_index = page_index
            if self._search_query:
                self._rebuild_search_rects(keep_index=False)
            self.refresh()
            self.page_changed.emit(self.page_index)

    def prev_page(self):
        if self.page_index > 0:
            self.page_index -= 1
            if self._search_query:
                self._rebuild_search_rects(keep_index=False)
            self.refresh()
            self.page_changed.emit(self.page_index)

    def next_page(self):
        if self.page_index + 1 < self.page_count:
            self.page_index += 1
            if self._search_query:
                self._rebuild_search_rects(keep_index=False)
            self.refresh()
            self.page_changed.emit(self.page_index)

    def clear_search_highlights(self):
        self._search_query = ""
        self._search_rects = []
        self._search_index = -1
        self.canvas.clear_search_highlights()

    def _rebuild_search_rects(self, *, keep_index: bool = True) -> int:
        """Aktualisiert Treffer-Rechtecke der aktuellen Seite für _search_query."""
        q = self._search_query
        if not q or not self.pdf_path:
            self._search_rects = []
            self._search_index = -1
            return 0
        matches = find_text_rects(
            self.pdf_path,
            self.page_index,
            q,
            scale=self.scale,
            password=self.password,
        )
        self._search_rects = [(m.x, m.y, m.width, m.height) for m in matches]
        if keep_index and self._search_rects:
            self._search_index = max(0, min(self._search_index, len(self._search_rects) - 1))
        else:
            self._search_index = 0 if self._search_rects else -1
        return len(self._search_rects)

    def highlight_search(self, query: str) -> int:
        """Highlightet Query-Treffer auf der aktuellen Seite. Liefert Trefferzahl."""
        q = (query or "").strip()
        if not q or not self.pdf_path:
            self.clear_search_highlights()
            return 0
        self._search_query = q
        n = self._rebuild_search_rects(keep_index=False)
        self.canvas.set_search_highlights(self._search_rects, self._search_index)
        return n

    def search_next(self) -> bool:
        """Nächster Treffer auf aktueller Seite; wrappt. False wenn keine Treffer."""
        if not self._search_query:
            return False
        if not self._search_rects:
            self._rebuild_search_rects(keep_index=False)
        if not self._search_rects:
            return False
        self._search_index = (self._search_index + 1) % len(self._search_rects)
        self.canvas.set_search_highlights(self._search_rects, self._search_index)
        return True

    def search_hit_count(self) -> int:
        return len(self._search_rects)

    def set_scale(self, scale: float, *, immediate: bool = False):
        scale = max(0.25, min(5.0, float(scale)))
        self.lbl_zoom.setText(f"{int(round(scale * 100))}%")
        if immediate:
            self._pending_scale = None
            self._zoom_timer.stop()
            self.scale = scale
            if self._search_query:
                self._rebuild_search_rects(keep_index=True)
            self.refresh()
            return
        # Debounce: schnelle Zoom-Schritte nur Label, Render verzögert
        self._pending_scale = scale
        self._zoom_timer.start()

    def _apply_pending_zoom(self):
        if self._pending_scale is None:
            return
        self.scale = self._pending_scale
        self._pending_scale = None
        if self._search_query:
            self._rebuild_search_rects(keep_index=True)
        self.refresh()

    def zoom_in(self):
        base = self._pending_scale if self._pending_scale is not None else self.scale
        self.set_scale(base + 0.25)

    def zoom_out(self):
        base = self._pending_scale if self._pending_scale is not None else self.scale
        self.set_scale(base - 0.25)

    def zoom_100(self):
        self.set_scale(1.0, immediate=True)

    def paste_clipboard_image(self) -> bool:
        """Bild aus Zwischenablage als Stempel-Annotation oder neue Seite."""
        if not self.pdf_path:
            return False
        clip = QApplication.clipboard()
        if clip is None:
            return False
        md = clip.mimeData()
        qimg = None
        if md and md.hasImage():
            raw = md.imageData()
            if isinstance(raw, QImage) and not raw.isNull():
                qimg = raw
        if qimg is None:
            pm = clip.pixmap()
            if pm is not None and not pm.isNull():
                qimg = pm.toImage()
        if qimg is None or qimg.isNull():
            self.status.emit("Zwischenablage enthält kein Bild")
            return False
        import tempfile

        from ild_pdf import insert_image_as_page, insert_image_stamp_overlay
        from ild_pdf.render import clear_render_cache

        tmp = Path(tempfile.gettempdir()) / "ild_clipboard_paste.png"
        if not qimg.save(str(tmp), "PNG"):
            QMessageBox.warning(self, "Einfügen", "Bild konnte nicht gespeichert werden.")
            return False
        choice, ok = QInputDialog.getItem(
            self,
            "Bild einfügen",
            "Zwischenablage-Bild:",
            ["Als Stempel-Annotation (aktuelle Seite)", "Als neue PDF-Seite"],
            0,
            False,
        )
        if not ok:
            return False
        try:
            if choice.startswith("Als neue"):
                insert_image_as_page(self.pdf_path, tmp)
                from ild_pdf import PdfDocument

                clear_render_cache(self.pdf_path)
                with PdfDocument(self.pdf_path, password=self.password) as doc:
                    self.page_count = len(doc)
                self.page_index = self.page_count - 1
                self.refresh()
                self.status.emit("Zwischenablage-Bild als neue Seite")
            else:
                insert_image_stamp_overlay(
                    self.pdf_path, tmp, page_index=self.page_index
                )
                self.reload_annotations()
                self.status.emit("Zwischenablage-Bild als Stempel")
            return True
        except Exception as e:
            QMessageBox.warning(self, "Einfügen", str(e))
            return False

    def _viewport_size(self) -> tuple[int, int]:
        vp = self.scroll.viewport()
        return max(vp.width() - 16, 80), max(vp.height() - 16, 80)

    def fit_page(self):
        """Aktuelle Seite in die Viewport-Fläche einpassen."""
        if not self.pdf_path:
            return
        try:
            from ild_pdf import PdfDocument

            with PdfDocument(self.pdf_path, password=self.password) as doc:
                pw, ph = doc.page_size(self.page_index)
            vw, vh = self._viewport_size()
            if pw <= 0 or ph <= 0:
                return
            scale = min(vw / pw, vh / ph)
            self.set_scale(scale, immediate=True)
            self.status.emit(f"Seite einpassen ({int(round(scale * 100))}%)")
        except Exception as e:
            QMessageBox.warning(self, "Zoom", str(e))

    def fit_width(self):
        """Seitenbreite an Viewport anpassen."""
        if not self.pdf_path:
            return
        try:
            from ild_pdf import PdfDocument

            with PdfDocument(self.pdf_path, password=self.password) as doc:
                pw, _ph = doc.page_size(self.page_index)
            vw, _vh = self._viewport_size()
            if pw <= 0:
                return
            scale = vw / pw
            self.set_scale(scale, immediate=True)
            self.status.emit(f"Breite einpassen ({int(round(scale * 100))}%)")
        except Exception as e:
            QMessageBox.warning(self, "Zoom", str(e))

    def undo_annotation(self) -> bool:
        if not self.store or not self.store.can_undo():
            self.status.emit("Nichts rückgängig zu machen")
            return False
        try:
            self.store.undo()
            self.store.save(force=True)
            self.refresh()
            self.annotations_changed.emit()
            self.status.emit("Annotation rückgängig")
            return True
        except Exception as e:
            QMessageBox.warning(self, "Rückgängig", str(e))
            return False

    def redo_annotation(self) -> bool:
        if not self.store or not self.store.can_redo():
            self.status.emit("Nichts zu wiederholen")
            return False
        try:
            self.store.redo()
            self.store.save(force=True)
            self.refresh()
            self.annotations_changed.emit()
            self.status.emit("Annotation wiederholt")
            return True
        except Exception as e:
            QMessageBox.warning(self, "Wiederholen", str(e))
            return False

    def print_current_page(self) -> bool:
        """Aktuelle PDF-Seite (mit Annotationen) über Qt PrintDialog drucken."""
        if not self.pdf_path:
            QMessageBox.information(self, "Drucken", "Kein PDF geladen.")
            return False
        try:
            from PySide6.QtGui import QPainter
            from PySide6.QtPrintSupport import QPrintDialog, QPrinter

            # Frisch rendern für Druckqualität
            img = render_page(self.pdf_path, self.page_index, scale=max(self.scale, 2.0))
            anns = self.store.for_page(self.page_index) if self.store else []
            # Temporäres Canvas-Pixmap nutzen
            self.canvas.set_page_image(img, anns, scale=max(self.scale, 2.0))
            pm = self.canvas.pixmap()
            if pm is None or pm.isNull():
                QMessageBox.warning(self, "Drucken", "Keine Seitenvorschau verfügbar.")
                self.refresh()
                return False

            printer = QPrinter(QPrinter.HighResolution)
            printer.setDocName(f"{self.pdf_path.stem} — Seite {self.page_index + 1}")
            dlg = QPrintDialog(printer, self)
            dlg.setWindowTitle("PDF-Seite drucken")
            if dlg.exec() != QPrintDialog.Accepted:
                self.refresh()
                return False
            painter = QPainter(printer)
            try:
                page_rect = printer.pageRect(QPrinter.DevicePixel)
                scaled = pm.scaled(
                    int(page_rect.width()),
                    int(page_rect.height()),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                x = int((page_rect.width() - scaled.width()) / 2)
                y = int((page_rect.height() - scaled.height()) / 2)
                painter.drawPixmap(x, y, scaled)
            finally:
                painter.end()
            self.refresh()
            self.status.emit("PDF-Seite gedruckt")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Drucken", f"Druck fehlgeschlagen:\n{e}")
            try:
                self.refresh()
            except Exception:
                pass
            return False

    def annotation_summaries(self) -> list[tuple[str, Annotation]]:
        if not self.store:
            return []
        out: list[tuple[str, Annotation]] = []
        for a in self.store.annotations:
            label = f"S{a.page + 1}: {a.type.value}"
            if a.text:
                label += f" — {a.text[:40]}"
            elif a.type == AnnotationType.MEASURE:
                label += f" — {a.measure_label(self.scale)}"
            out.append((label, a))
        return out

    def save_annotations(self) -> bool:
        if not self.store or not self.pdf_path:
            QMessageBox.information(self, "Annotationen", "Kein PDF geladen.")
            return False
        try:
            path = self.store.save(force=True)
            self.status.emit(
                f"Sidecar gespeichert: {path.name} ({len(self.store.annotations)})"
            )
            self.annotations_changed.emit()
            return True
        except Exception as e:
            QMessageBox.warning(self, "Annotationen speichern", str(e))
            return False

    def save_annotations_as(self) -> bool:
        """Speichern unter: Sidecar *.ildann.json an gewähltem Pfad (PDF bleibt unverändert)."""
        if not self.store or not self.pdf_path:
            QMessageBox.information(self, "Annotationen", "Kein PDF geladen.")
            return False
        from PySide6.QtWidgets import QFileDialog

        default = str(self.store.sidecar_path)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Annotationen speichern unter (Sidecar)",
            default,
            "Annotation-Sidecar (*.ildann.json);;JSON (*.json);;Alle (*.*)",
        )
        if not path:
            return False
        dest = Path(path)
        if dest.suffix.lower() != ".json" and not dest.name.endswith(".ildann.json"):
            dest = Path(str(dest) + ".ildann.json")
        try:
            saved = self.store.export_backup(dest)
            QMessageBox.information(
                self,
                "Annotationen speichern unter",
                "Sidecar gespeichert (PDF unverändert):\n"
                f"{saved}\n\n"
                f"Standard-Sidecar neben der PDF:\n{self.store.sidecar_path.name}",
            )
            self.status.emit(f"Sidecar gespeichert unter: {saved.name}")
            self.annotations_changed.emit()
            return True
        except Exception as e:
            QMessageBox.warning(self, "Annotationen speichern unter", str(e))
            return False

    def reload_annotations(self) -> bool:
        if not self.store or not self.pdf_path:
            return False
        try:
            if self.store.sidecar_path.exists():
                self.store.load()
                self.refresh()
                self.annotations_changed.emit()
                self.status.emit(f"Annotationen geladen ({len(self.store.annotations)})")
                return True
            QMessageBox.information(
                self,
                "Annotationen",
                f"Keine Sidecar-Datei:\n{self.store.sidecar_path.name}",
            )
            return False
        except Exception as e:
            QMessageBox.warning(self, "Annotationen laden", str(e))
            return False

    def import_text_overlays(self):
        if not self.store or not self.pdf_path:
            return
        try:
            created = import_page_text_as_overlays(
                self.store, self.pdf_path, self.page_index, scale=self.scale
            )
            self.store.save()
            self.refresh()
            self.annotations_changed.emit()
            self.status.emit(f"{len(created)} Text-Overlay(s) aus PDF-Text")
            if not created:
                QMessageBox.information(
                    self,
                    "Text-Overlay",
                    "Kein extrahierbarer Text auf dieser Seite.\n"
                    "Leere Overlays können mit dem Werkzeug „Text-Overlay“ gesetzt werden.",
                )
        except Exception as e:
            QMessageBox.warning(self, "Text→Overlay", str(e))

    def bake_overlays(self):
        if not self.store or not self.pdf_path:
            return
        n = len(self.store.text_overlays())
        if n == 0:
            QMessageBox.information(self, "Einbrennen", "Keine TEXT/TEXT_OVERLAY Annotationen.")
            return
        reply = QMessageBox.question(
            self,
            "Overlay einbrennen",
            f"{n} Text-Overlay(s) als Helvetica-Content in die PDF schreiben?\n"
            "(Native Textblöcke bleiben unverändert; Sidecar bleibt erhalten.)",
        )
        if reply != QMessageBox.Yes:
            return
        try:
            bake_text_overlays(self.pdf_path, self.store, scale=self.scale)
            self.refresh()
            self.status.emit("Overlays in PDF eingebrannt")
        except Exception as e:
            QMessageBox.warning(self, "Einbrennen", str(e))

    def redaction_count(self) -> int:
        if not self.store:
            return 0
        return sum(1 for a in self.store.annotations if a.type == AnnotationType.REDACTION)

    def clear_redactions(self):
        """Entfernt nur REDACTION-Annotationen aus dem Sidecar (PDF unverändert)."""
        if not self.store:
            return
        reds = [a for a in self.store.annotations if a.type == AnnotationType.REDACTION]
        if not reds:
            QMessageBox.information(self, "Schwärzung", "Keine Schwärzungs-Annotationen.")
            return
        by_page: dict[int, int] = {}
        for a in reds:
            by_page[a.page] = by_page.get(a.page, 0) + 1
        pages = ", ".join(f"S.{p + 1}:{n}" for p, n in sorted(by_page.items()))
        reply = QMessageBox.question(
            self,
            "Schwärzungs-Annotationen löschen",
            f"{len(reds)} Schwärzung(en) aus dem Sidecar entfernen?\n({pages})\n"
            "Bereits eingebrannte Flächen bleiben im PDF.",
        )
        if reply != QMessageBox.Yes:
            return
        with self.store.atomic():
            self.store.annotations = [
                a for a in self.store.annotations if a.type != AnnotationType.REDACTION
            ]
            self.store.dirty = True
        try:
            self.store.save(force=True)
        except Exception as e:
            QMessageBox.warning(self, "Schwärzung", str(e))
            return
        self.refresh()
        self.annotations_changed.emit()
        self.status.emit(f"{len(reds)} Schwärzungs-Annotation(en) gelöscht")

    def bake_redactions(self, *, remove_sidecar: bool | None = None):
        if not self.store or not self.pdf_path:
            return
        reds = [a for a in self.store.annotations if a.type == AnnotationType.REDACTION]
        if not reds:
            QMessageBox.information(self, "Schwärzung", "Keine Schwärzungs-Annotationen.")
            return
        by_page: dict[int, int] = {}
        for a in reds:
            by_page[a.page] = by_page.get(a.page, 0) + 1
        pages = ", ".join(f"S.{p + 1}:{n}" for p, n in sorted(by_page.items()))

        from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout

        dlg = QDialog(self)
        dlg.setWindowTitle("Schwärzung einbrennen")
        lay = QVBoxLayout(dlg)
        lay.addWidget(
            QLabel(
                f"{len(reds)} Schwärzung(en) dauerhaft als schwarze Flächen schreiben?\n"
                f"Verteilung: {pages}\n\n"
                "Hinweis: Basis-Redaction — Text unter der Fläche kann in der\n"
                "PDF-Textschicht noch selektierbar sein."
            )
        )
        chk = QCheckBox("Annotationen nach Einbrennen aus Sidecar entfernen")
        chk.setChecked(True if remove_sidecar is None else bool(remove_sidecar))
        lay.addWidget(chk)
        buttons = QDialogButtonBox(QDialogButtonBox.Yes | QDialogButtonBox.No)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        lay.addWidget(buttons)
        if dlg.exec() != QDialog.Accepted:
            return
        remove = chk.isChecked()
        try:
            from ild_pdf.redact import bake_redactions as apply_redactions
            from ild_pdf.render import clear_render_cache

            apply_redactions(
                self.pdf_path,
                self.store,
                scale=self.scale,
                remove_from_store=remove,
            )
            clear_render_cache(self.pdf_path)
            self.refresh()
            self.annotations_changed.emit()
            self.status.emit(f"{len(reds)} Schwärzung(en) eingebrannt")
        except Exception as e:
            QMessageBox.warning(self, "Schwärzung", str(e))

    def render_thumbnails(self, *, max_pages: int = 40, scale: float = 0.18):
        """Kleine Seitenvorschauen (PIL). Begrenzt auf max_pages."""
        if not self.pdf_path or self.page_count <= 0:
            return []
        out = []
        n = min(self.page_count, max_pages)
        for i in range(n):
            try:
                out.append(
                    render_page(
                        self.pdf_path,
                        i,
                        scale=scale,
                        password=self.password,
                        use_cache=True,
                    )
                )
            except Exception:
                from PIL import Image

                out.append(Image.new("RGB", (72, 96), (220, 220, 220)))
        return out

    def _edit_overlay(self, ann_id: str):
        if not self.store:
            return
        ann = self.store.get(ann_id)
        if not ann:
            return
        dlg = TextOverlayEditDialog(ann, self)
        if dlg.exec() != QDialog.Accepted:
            return
        vals = dlg.values()
        self.store.update(ann_id, **vals)
        try:
            self.store.save()
        except Exception as e:
            QMessageBox.warning(self, "Overlay", str(e))
        self.refresh()
        self.annotations_changed.emit()
        self.status.emit("Text-Overlay aktualisiert")

    def extract_page_as_image(self):
        if not self.pdf_path:
            return
        from PySide6.QtWidgets import QFileDialog
        from ild_pdf import extract_page_image

        default = str(self.pdf_path.with_name(f"{self.pdf_path.stem}_p{self.page_index + 1}.png"))
        path, _ = QFileDialog.getSaveFileName(self, "Seite als Bild", default, "PNG (*.png);;JPEG (*.jpg)")
        if not path:
            return
        try:
            fmt = "JPEG" if path.lower().endswith((".jpg", ".jpeg")) else "PNG"
            out = extract_page_image(self.pdf_path, self.page_index, path, scale=self.scale, format=fmt)
            self.status.emit(f"Seite exportiert: {out.name}")
        except Exception as e:
            QMessageBox.warning(self, "Extrahieren", str(e))

    def place_signature_field(self):
        """Signaturfeld-Platzhalter per Klick (Werkzeug Signaturfeld)."""
        self._set_tool(AnnotationType.SIGNATURE_FIELD)
        self.status.emit("Signaturfeld: auf die Seite klicken")

    def insert_signature_image(self):
        """Bild-Signatur auf aktuelle Seite setzen (Datei wählen, dann Klickposition)."""
        if not self.store or not self.pdf_path:
            QMessageBox.information(self, "Signatur", "Kein PDF geladen.")
            return
        from PySide6.QtWidgets import QFileDialog
        from ild_pdf import insert_signature_image

        path, _ = QFileDialog.getOpenFileName(
            self, "Signatur-Bild", "", "Bilder (*.png *.jpg *.jpeg *.bmp)"
        )
        if not path:
            return
        # Mitte-unten der Seite als Default
        try:
            from ild_pdf import PdfDocument

            with PdfDocument(self.pdf_path, password=self.password) as doc:
                pw, ph = doc.page_size(self.page_index)
            x = max(40.0, pw * 0.15)
            y = max(40.0, ph * 0.78)
        except Exception:
            x, y = 80.0, 520.0
        try:
            insert_signature_image(
                self.pdf_path,
                path,
                page_index=self.page_index,
                x=x,
                y=y,
            )
            self.store.load()
            self.refresh()
            self.annotations_changed.emit()
            self.status.emit("Signatur-Bild platziert")
        except Exception as e:
            QMessageBox.warning(self, "Signatur", str(e))

    def insert_image_page(self):
        if not self.pdf_path:
            return
        from PySide6.QtWidgets import QFileDialog
        from ild_pdf import insert_image_as_page

        path, _ = QFileDialog.getOpenFileName(
            self, "Bild als neue Seite", "", "Bilder (*.png *.jpg *.jpeg *.bmp)"
        )
        if not path:
            return
        try:
            insert_image_as_page(self.pdf_path, path)
            from ild_pdf import PdfDocument

            with PdfDocument(self.pdf_path, password=self.password) as doc:
                self.page_count = len(doc)
            self.page_index = self.page_count - 1
            self.refresh()
            self.status.emit("Bildseite angehängt")
        except Exception as e:
            QMessageBox.warning(self, "Bild einfügen", str(e))

    def _on_drag(self, x0: float, y0: float, x1: float, y1: float):
        if not self.store or self.tool is None or self.tool not in DRAG_TYPES:
            return
        if self.tool == AnnotationType.HIGHLIGHT:
            ann = Annotation(
                page=self.page_index,
                type=AnnotationType.HIGHLIGHT,
                x=min(x0, x1),
                y=min(y0, y1),
                width=max(abs(x1 - x0), 8),
                height=max(abs(y1 - y0), 8),
                color=self._highlight_color,
            )
        elif self.tool == AnnotationType.REDACTION:
            ann = Annotation(
                page=self.page_index,
                type=AnnotationType.REDACTION,
                x=min(x0, x1),
                y=min(y0, y1),
                width=max(abs(x1 - x0), 8),
                height=max(abs(y1 - y0), 8),
                color="#000000",
                text="REDACT",
            )
        elif self.tool == AnnotationType.RECTANGLE:
            ann = Annotation(
                page=self.page_index,
                type=AnnotationType.RECTANGLE,
                x=min(x0, x1),
                y=min(y0, y1),
                width=max(abs(x1 - x0), 8),
                height=max(abs(y1 - y0), 8),
                color=self._pen_color,
            )
        elif self.tool in (AnnotationType.LINE, AnnotationType.ARROW, AnnotationType.MEASURE):
            ann = Annotation(
                page=self.page_index,
                type=self.tool,
                x=x0,
                y=y0,
                width=abs(x1 - x0),
                height=abs(y1 - y0),
                callout_x=x1,
                callout_y=y1,
                color=self._pen_color,
            )
            if self.tool == AnnotationType.MEASURE:
                ann.text = ann.measure_label(self.scale)
        else:
            return
        self._commit_ann(ann)

    def _on_place(self, x: float, y: float):
        if not self.store or self.tool is None:
            return
        if self.tool in DRAG_TYPES:
            return  # Drag-Werkzeuge

        if self.tool == AnnotationType.CALLOUT:
            if self._pending_callout_anchor is None:
                self._pending_callout_anchor = (x, y)
                self.status.emit("Callout: zweiten Klick für Textbox setzen")
                return
            ax, ay = self._pending_callout_anchor
            self._pending_callout_anchor = None
            text, ok = QInputDialog.getText(self, "Callout", "Text:")
            if not ok:
                return
            ann = Annotation(
                page=self.page_index,
                type=AnnotationType.CALLOUT,
                x=x,
                y=y,
                width=140,
                height=48,
                text=text,
                color=self._pen_color,
                callout_x=ax,
                callout_y=ay,
            )
            self._commit_ann(ann)
            return

        text = ""
        color = self._pen_color
        width, height = 160.0, 24.0
        font_size = 12.0

        if self.tool == AnnotationType.STAMP:
            stamp, ok = QInputDialog.getItem(
                self, "Stempel", "Text:", list(STAMP_PRESETS), 0, True
            )
            if not ok or not stamp:
                return
            text = stamp
            color = "#C0392B"
            width, height = 140.0, 40.0
        elif self.tool == AnnotationType.STICKY:
            text, ok = QInputDialog.getText(self, "Notiz", "Inhalt:")
            if not ok:
                return
            height = 70.0
            color = "#FF6B6B"
        elif self.tool == AnnotationType.TEXT_OVERLAY:
            text, ok = QInputDialog.getMultiLineText(self, "Text-Overlay", "Text:")
            if not ok:
                return
            color = "#1A5276"
            width, height = 200.0, 36.0
            font_size = 14.0
        elif self.tool == AnnotationType.TEXT:
            text, ok = QInputDialog.getText(self, "Text", "Inhalt:")
            if not ok:
                return
        elif self.tool == AnnotationType.UNDERLINE:
            width = 180.0
            color = self._pen_color
        elif self.tool == AnnotationType.SIGNATURE_FIELD:
            text, ok = QInputDialog.getText(self, "Signaturfeld", "Beschriftung:", text="Unterschrift")
            if not ok:
                return
            color = "#7F8C8D"
            width, height = 220.0, 56.0
        else:
            return

        ann = Annotation(
            page=self.page_index,
            type=self.tool,
            x=x,
            y=y,
            width=width,
            height=height,
            text=text,
            color=color,
            font_size=font_size,
        )
        self._commit_ann(ann)

    def _commit_ann(self, ann: Annotation):
        assert self.store is not None
        self.store.add(ann)
        try:
            self.store.save()
        except Exception as e:
            QMessageBox.warning(self, "Annotationen", f"Speichern fehlgeschlagen: {e}")
        self.refresh()
        self.annotations_changed.emit()
        self.status.emit(f"Annotation gespeichert ({ann.type.value})")

    def rotate_current(self):
        if not self.pdf_path:
            return
        try:
            rotate_page(self.pdf_path, self.page_index, 90)
            self.refresh()
            self.status.emit("Seite gedreht")
        except Exception as e:
            QMessageBox.warning(self, "Drehen", str(e))

    def delete_current(self):
        if not self.pdf_path or self.page_count <= 1:
            QMessageBox.information(self, "Löschen", "Letzte Seite kann nicht gelöscht werden.")
            return
        reply = QMessageBox.question(
            self,
            "Seite löschen",
            f"Seite {self.page_index + 1} wirklich löschen?",
        )
        if reply != QMessageBox.Yes:
            return
        try:
            deleted = self.page_index
            delete_pages(self.pdf_path, [deleted])
            if self.store:
                mapping = {}
                for i in range(self.page_count):
                    if i < deleted:
                        mapping[i] = i
                    elif i > deleted:
                        mapping[i] = i - 1
                self.store.remap_pages(mapping)
                self.store.save(force=True)
            self.page_count -= 1
            self.page_index = min(self.page_index, self.page_count - 1)
            self.refresh()
            self.annotations_changed.emit()
            self.status.emit("Seite gelöscht")
        except Exception as e:
            QMessageBox.warning(self, "Löschen", str(e))

    def reorder_dialog(self):
        if not self.pdf_path or self.page_count < 2:
            QMessageBox.information(self, "Neu anordnen", "Mindestens 2 Seiten nötig.")
            return
        dlg = PageReorderDialog(self.page_count, self)
        if dlg.exec() != QDialog.Accepted:
            return
        order = dlg.new_order()
        if order == list(range(self.page_count)):
            return
        try:
            reorder_pages(self.pdf_path, order)
            if self.store:
                mapping = {old: new for new, old in enumerate(order)}
                self.store.remap_pages(mapping)
                self.store.save(force=True)
            self.page_index = 0
            from ild_pdf import PdfDocument

            with PdfDocument(self.pdf_path, password=self.password) as doc:
                self.page_count = len(doc)
            self.refresh()
            self.annotations_changed.emit()
            self.status.emit("Seiten neu angeordnet")
        except Exception as e:
            QMessageBox.warning(self, "Neu anordnen", str(e))

    def clear(self):
        self.pdf_path = None
        self.store = None
        self.canvas.clear()
        self.lbl_page.setText("—")
        self.annotations_changed.emit()
