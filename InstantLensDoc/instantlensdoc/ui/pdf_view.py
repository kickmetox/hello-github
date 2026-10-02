"""PDF-Ansicht mit Zoom, Annotationen (inkl. Stempel/Callout) und Seitenoperationen."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ild_pdf import Annotation, AnnotationStore, AnnotationType, STAMP_PRESETS, render_page
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


class PdfCanvas(QLabel):
    """Zeigt eine gerenderte PDF-Seite; Klick setzt Annotation je nach Werkzeug."""

    annotation_placed = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(200, 200)
        self._pixmap: Optional[QPixmap] = None
        self._annotations: list[Annotation] = []
        self.setMouseTracking(True)

    def set_page_image(self, image, annotations: list[Annotation] | None = None):
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        data = image.tobytes("raw", "RGBA")
        qimg = QImage(data, image.width, image.height, QImage.Format_RGBA8888)
        self._pixmap = QPixmap.fromImage(qimg.copy())
        self._annotations = annotations or []
        self._repaint_overlay()

    def _repaint_overlay(self):
        if self._pixmap is None:
            return
        pm = QPixmap(self._pixmap)
        painter = QPainter(pm)
        for ann in self._annotations:
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
        painter.end()
        self.setPixmap(pm)
        self.adjustSize()

    def mousePressEvent(self, event):
        if self._pixmap is None:
            return
        pos = event.position()
        pm = self.pixmap()
        if pm is None:
            return
        lx = (self.width() - pm.width()) / 2
        ly = (self.height() - pm.height()) / 2
        x = pos.x() - lx
        y = pos.y() - ly
        if 0 <= x <= pm.width() and 0 <= y <= pm.height():
            self.annotation_placed.emit(float(x), float(y))
        super().mousePressEvent(event)


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

        for t, label in [
            (AnnotationType.HIGHLIGHT, "Highlight"),
            (AnnotationType.UNDERLINE, "Unterstreichen"),
            (AnnotationType.STICKY, "Notiz"),
            (AnnotationType.TEXT, "Textfeld"),
            (AnnotationType.STAMP, "Stempel"),
            (AnnotationType.CALLOUT, "Callout"),
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
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.canvas = PdfCanvas()
        self.canvas.annotation_placed.connect(self._on_place)
        self.scroll.setWidget(self.canvas)
        layout.addWidget(self.scroll)

    def _set_tool(self, tool: AnnotationType):
        self.tool = tool
        self._pending_callout_anchor = None
        mapping = {
            AnnotationType.HIGHLIGHT: "Highlight",
            AnnotationType.UNDERLINE: "Unterstreichen",
            AnnotationType.STICKY: "Notiz",
            AnnotationType.TEXT: "Textfeld",
            AnnotationType.STAMP: "Stempel",
            AnnotationType.CALLOUT: "Callout",
        }
        want = mapping[tool]
        for b in self._tool_buttons:
            b.setChecked(b.text() == want)
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
        self.canvas.set_page_image(img, anns)
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

    def _on_place(self, x: float, y: float):
        if not self.store or self.tool is None:
            return

        # Callout: 1. Klick = Anker, 2. Klick = Box
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

        if self.tool == AnnotationType.STAMP:
            stamp, ok = QInputDialog.getItem(
                self, "Stempel", "Text:", list(STAMP_PRESETS), 0, True
            )
            if not ok or not stamp:
                return
            text = stamp
            color = "#C0392B"
            width, height = 140.0, 40.0
        elif self.tool in (AnnotationType.STICKY, AnnotationType.TEXT):
            text, ok = QInputDialog.getText(self, "Text", "Inhalt:")
            if not ok:
                return
            height = 70.0 if self.tool == AnnotationType.STICKY else 24.0
        elif self.tool == AnnotationType.HIGHLIGHT:
            color = "#FFE066"
            width = 160.0
        elif self.tool == AnnotationType.UNDERLINE:
            width = 180.0

        ann = Annotation(
            page=self.page_index,
            type=self.tool,
            x=x,
            y=y,
            width=width,
            height=height,
            text=text,
            color=color,
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
                # Seiten > deleted um 1 nach unten
                mapping = {}
                for i in range(self.page_count):
                    if i < deleted:
                        mapping[i] = i
                    elif i > deleted:
                        mapping[i] = i - 1
                    # i == deleted: weggelassen
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
