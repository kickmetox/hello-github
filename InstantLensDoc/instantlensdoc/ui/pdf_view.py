"""PDF-Ansicht: Zoom, Annotationen, Formen, Messung, Text-Overlay, Seitenops."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QDoubleSpinBox,
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
    import_page_text_as_overlays,
    render_page,
)
from ild_pdf.pages import delete_pages, reorder_pages, rotate_page


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
        self.setMouseTracking(True)

    def set_drag_tool(self, tool: AnnotationType | None):
        self._drag_tool = tool if tool in DRAG_TYPES else None

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
        elif ann.type == AnnotationType.STAMP:
            stamp_color = QColor(ann.color if ann.color != "#FFFF00" else "#C0392B")
            painter.setPen(QPen(stamp_color, 3))
            painter.drawRect(x, y, max(w, 100), max(h, 36))
            painter.drawText(x + 8, y + max(h, 36) // 2 + 4, (ann.text or "STEMPEL")[:24])
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pdf_path: Optional[Path] = None
        self.page_index = 0
        self.page_count = 0
        self.scale = 1.5
        self.tool: AnnotationType | None = AnnotationType.HIGHLIGHT
        self.store: Optional[AnnotationStore] = None
        self._tool_buttons: list[QToolButton] = []
        self._pending_callout_anchor: tuple[float, float] | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QHBoxLayout()
        self.lbl_page = QLabel("—")
        btn_prev = QPushButton("◀")
        btn_next = QPushButton("▶")
        btn_prev.clicked.connect(self.prev_page)
        btn_next.clicked.connect(self.next_page)
        btn_zoom_in = QPushButton("+")
        btn_zoom_out = QPushButton("−")
        btn_zoom_in.clicked.connect(lambda: self.set_scale(self.scale + 0.25))
        btn_zoom_out.clicked.connect(lambda: self.set_scale(max(0.5, self.scale - 0.25)))
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
            (AnnotationType.UNDERLINE, "Unterstreichen"),
            (AnnotationType.STICKY, "Notiz"),
            (AnnotationType.TEXT_OVERLAY, "Text-Overlay"),
            (AnnotationType.STAMP, "Stempel"),
            (AnnotationType.CALLOUT, "Callout"),
            (AnnotationType.RECTANGLE, "Rechteck"),
            (AnnotationType.LINE, "Linie"),
            (AnnotationType.ARROW, "Pfeil"),
            (AnnotationType.MEASURE, "Lineal"),
        ]:
            b = QToolButton()
            b.setText(label)
            b.setCheckable(True)
            b.setChecked(t == AnnotationType.HIGHLIGHT)
            b.clicked.connect(lambda checked, tool=t: self._set_tool(tool))
            self._tool_buttons.append(b)
            toolbar.addWidget(b)

        toolbar.addWidget(btn_prev)
        toolbar.addWidget(self.lbl_page)
        toolbar.addWidget(btn_next)
        toolbar.addWidget(btn_zoom_out)
        toolbar.addWidget(btn_zoom_in)
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

    def _tool_label(self, tool: AnnotationType) -> str:
        return {
            AnnotationType.HIGHLIGHT: "Highlight",
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
        }.get(tool, tool.value)

    def _set_tool(self, tool: AnnotationType):
        self.tool = tool
        self._pending_callout_anchor = None
        want = self._tool_label(tool)
        for b in self._tool_buttons:
            b.setChecked(b.text() == want)
        self.canvas.set_drag_tool(tool if tool in DRAG_TYPES else None)
        self.status.emit(f"Werkzeug: {tool.value}")

    def load(self, path: str | Path):
        self.pdf_path = Path(path)
        self.store = AnnotationStore(self.pdf_path)
        from ild_pdf import PdfDocument

        with PdfDocument(self.pdf_path) as doc:
            self.page_count = len(doc)
        self.page_index = 0
        self._pending_callout_anchor = None
        self.refresh()
        self.annotations_changed.emit()

    def refresh(self):
        if not self.pdf_path:
            return
        img = render_page(self.pdf_path, self.page_index, scale=self.scale)
        anns = self.store.for_page(self.page_index) if self.store else []
        self.canvas.set_page_image(img, anns, scale=self.scale)
        self.lbl_page.setText(f"Seite {self.page_index + 1} / {self.page_count}")
        dirty = " *" if self.store and self.store.dirty else ""
        self.status.emit(f"PDF: {self.pdf_path.name}{dirty}")

    def goto_page(self, page_index: int):
        if 0 <= page_index < self.page_count:
            self.page_index = page_index
            self.refresh()

    def prev_page(self):
        if self.page_index > 0:
            self.page_index -= 1
            self.refresh()

    def next_page(self):
        if self.page_index + 1 < self.page_count:
            self.page_index += 1
            self.refresh()

    def set_scale(self, scale: float):
        self.scale = scale
        self.refresh()

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
            self.status.emit(f"Annotationen gespeichert: {path.name} ({len(self.store.annotations)})")
            self.annotations_changed.emit()
            return True
        except Exception as e:
            QMessageBox.warning(self, "Annotationen speichern", str(e))
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

            with PdfDocument(self.pdf_path) as doc:
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
                color="#FFE066",
            )
        elif self.tool == AnnotationType.RECTANGLE:
            ann = Annotation(
                page=self.page_index,
                type=AnnotationType.RECTANGLE,
                x=min(x0, x1),
                y=min(y0, y1),
                width=max(abs(x1 - x0), 8),
                height=max(abs(y1 - y0), 8),
                color="#27AE60",
            )
        elif self.tool in (AnnotationType.LINE, AnnotationType.ARROW, AnnotationType.MEASURE):
            color = {
                AnnotationType.LINE: "#2C3E50",
                AnnotationType.ARROW: "#8E44AD",
                AnnotationType.MEASURE: "#E67E22",
            }[self.tool]
            ann = Annotation(
                page=self.page_index,
                type=self.tool,
                x=x0,
                y=y0,
                width=abs(x1 - x0),
                height=abs(y1 - y0),
                callout_x=x1,
                callout_y=y1,
                color=color,
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
                color="#2980B9",
                callout_x=ax,
                callout_y=ay,
            )
            self._commit_ann(ann)
            return

        text = ""
        color = "#FF6B6B"
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

            with PdfDocument(self.pdf_path) as doc:
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
