"""PDF-Ansicht mit Zoom und Basis-Annotationen."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ild_pdf import Annotation, AnnotationStore, AnnotationType, render_page
from ild_pdf.pages import delete_pages, rotate_page


class PdfCanvas(QLabel):
    """Zeigt eine gerenderte PDF-Seite; Klick setzt Annotation je nach Werkzeug."""

    annotation_placed = Signal(float, float)  # relative 0..1 Koordinaten

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(200, 200)
        self._pixmap: Optional[QPixmap] = None
        self._annotations: list[Annotation] = []
        self.setMouseTracking(True)

    def set_page_image(self, image, annotations: list[Annotation] | None = None):
        # PIL → QImage
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
        painter.end()
        self.setPixmap(pm)
        self.adjustSize()

    def mousePressEvent(self, event):
        if self._pixmap is None:
            return
        pos = event.position()
        # Koordinaten relativ zum Pixmap (zentriert in Label)
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pdf_path: Optional[Path] = None
        self.page_index = 0
        self.page_count = 0
        self.scale = 1.5
        self.tool: AnnotationType | None = AnnotationType.HIGHLIGHT
        self.store: Optional[AnnotationStore] = None

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
        btn_rot.clicked.connect(self.rotate_current)
        btn_del = QPushButton("Seite löschen")
        btn_del.clicked.connect(self.delete_current)

        for t, label in [
            (AnnotationType.HIGHLIGHT, "Highlight"),
            (AnnotationType.UNDERLINE, "Unterstreichen"),
            (AnnotationType.STICKY, "Notiz"),
            (AnnotationType.TEXT, "Textfeld"),
        ]:
            b = QToolButton()
            b.setText(label)
            b.setCheckable(True)
            b.setChecked(t == AnnotationType.HIGHLIGHT)
            b.clicked.connect(lambda checked, tool=t: self._set_tool(tool))
            toolbar.addWidget(b)

        toolbar.addWidget(btn_prev)
        toolbar.addWidget(self.lbl_page)
        toolbar.addWidget(btn_next)
        toolbar.addWidget(btn_zoom_out)
        toolbar.addWidget(btn_zoom_in)
        toolbar.addWidget(btn_rot)
        toolbar.addWidget(btn_del)
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
        self.status.emit(f"Werkzeug: {tool.value}")

    def load(self, path: str | Path):
        self.pdf_path = Path(path)
        self.store = AnnotationStore(self.pdf_path)
        from ild_pdf import PdfDocument

        with PdfDocument(self.pdf_path) as doc:
            self.page_count = len(doc)
        self.page_index = 0
        self.refresh()

    def refresh(self):
        if not self.pdf_path:
            return
        img = render_page(self.pdf_path, self.page_index, scale=self.scale)
        anns = self.store.for_page(self.page_index) if self.store else []
        # Annotation-Koordinaten sind in Render-Pixeln bei scale — Sidecar speichert absolute Werte
        self.canvas.set_page_image(img, anns)
        self.lbl_page.setText(f"Seite {self.page_index + 1} / {self.page_count}")
        self.status.emit(f"PDF: {self.pdf_path.name}")

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

    def _on_place(self, x: float, y: float):
        if not self.store or self.tool is None:
            return
        text = ""
        if self.tool in (AnnotationType.STICKY, AnnotationType.TEXT):
            from PySide6.QtWidgets import QInputDialog

            text, ok = QInputDialog.getText(self, "Text", "Inhalt:")
            if not ok:
                return
        ann = Annotation(
            page=self.page_index,
            type=self.tool,
            x=x,
            y=y,
            width=160 if self.tool != AnnotationType.UNDERLINE else 180,
            height=24 if self.tool != AnnotationType.STICKY else 70,
            text=text,
            color="#FFE066" if self.tool == AnnotationType.HIGHLIGHT else "#FF6B6B",
        )
        self.store.add(ann)
        self.store.save()
        self.refresh()
        self.status.emit("Annotation gespeichert")

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
        try:
            delete_pages(self.pdf_path, [self.page_index])
            self.page_count -= 1
            self.page_index = min(self.page_index, self.page_count - 1)
            self.refresh()
            self.status.emit("Seite gelöscht")
        except Exception as e:
            QMessageBox.warning(self, "Löschen", str(e))

    def clear(self):
        self.pdf_path = None
        self.store = None
        self.canvas.clear()
        self.lbl_page.setText("—")
