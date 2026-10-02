"""PDF-Ansicht: Zoom, Annotationen, Formen, Messung, Text-Overlay, Seitenops."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QPointF, Qt, QTimer, Signal, QUrl
from PySide6.QtGui import (
    QColor,
    QCursor,
    QDesktopServices,
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
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ild_pdf import (
    DRAG_TYPES,
    Annotation,
    AnnotationStore,
    AnnotationType,
    STAMP_LIBRARY,
    STAMP_PRESETS,
    stamp_library_items,
    stamp_with_date,
    bake_text_overlays,
    find_text_rects,
    selection_to_highlight_rects,
    selection_to_plain_text,
    import_page_text_as_overlays,
    list_page_uri_links,
    render_page,
    uri_link_at,
)
from ild_pdf.pages import (
    delete_pages,
    duplicate_page,
    extract_page_bytes,
    flip_page,
    insert_blank_page,
    insert_page_from_bytes,
    reorder_pages,
    rotate_page,
)
from instantlensdoc.core.app_settings import (
    cycle_ann_palette_color,
    get_ann_color_presets,
    get_ann_default_opacity,
    get_ann_highlight_color,
    get_ann_note_color,
    get_ann_pen_color,
    get_annotations_locked,
    get_annotations_visible,
    get_default_zoom_scale,
    get_pdf_continuous_scroll,
    get_pdf_grayscale,
    get_pdf_night_mode,
    get_pdf_two_page_spread,
    get_show_page_boxes,
    get_show_printer_marks,
    random_ann_palette_color,
    set_ann_color_preset,
    set_ann_default_opacity,
    set_ann_highlight_color,
    set_ann_note_color,
    set_ann_pen_color,
    set_annotations_locked,
    set_annotations_visible,
    set_pdf_continuous_scroll,
    set_pdf_grayscale,
    set_pdf_night_mode,
    set_pdf_two_page_spread,
    set_show_page_boxes,
    set_show_printer_marks,
)

# Continuous-Scroll: max. gerenderte Seiten (Speicher)
CONTINUOUS_MAX_PAGES = 40
CONTINUOUS_PAGE_GAP = 12


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


class StampPickDialog(QDialog):
    """Stempel-Bibliothek: Genehmigt/Entwurf/Vertraulich (+ Datum) und weitere Presets."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Stempel")
        self.resize(380, 320)
        from PySide6.QtWidgets import QCheckBox, QListWidget

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Bibliothek / Preset wählen:"))
        self.with_date = QCheckBox("Datum anhängen")
        self.with_date.setChecked(True)
        self.with_date.toggled.connect(self._rebuild)
        layout.addWidget(self.with_date)
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda _i: self.accept())
        layout.addWidget(self.list)
        self.custom = QLineEdit()
        self.custom.setPlaceholderText("Oder eigenen Text…")
        layout.addWidget(self.custom)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._items: list[tuple[str, str]] = []  # display, (text, color) encoded
        self._rebuild()

    def _rebuild(self):
        include = self.with_date.isChecked()
        self.list.clear()
        self._items = []
        for display, text, color in stamp_library_items(include_date=include):
            self._items.append((text, color))
            self.list.addItem(display)
        # weitere Presets ohne Duplikat der Library-Labels
        lib_labels = {lab for lab, _ in STAMP_LIBRARY}
        for preset in STAMP_PRESETS:
            if preset in lib_labels:
                continue
            text = stamp_with_date(preset, include_date=include)
            self._items.append((text, "#C0392B"))
            self.list.addItem(text.replace("\n", " · "))
        if self.list.count():
            self.list.setCurrentRow(0)

    def result_stamp(self) -> tuple[str, str] | None:
        """(text, color) oder None."""
        custom = self.custom.text().strip()
        if custom:
            text = stamp_with_date(custom, include_date=self.with_date.isChecked())
            return text, "#C0392B"
        row = self.list.currentRow()
        if 0 <= row < len(self._items):
            return self._items[row]
        return None


class TextOverlayEditDialog(QDialog):
    """Annotation-Text bearbeiten (Notiz/Kommentar/Overlay; Sidecar)."""

    def __init__(self, ann: Annotation, parent=None):
        super().__init__(parent)
        kind = {
            AnnotationType.STICKY: "Notiz",
            AnnotationType.TEXT: "Text",
            AnnotationType.TEXT_OVERLAY: "Text-Overlay",
            AnnotationType.CALLOUT: "Callout",
            AnnotationType.STAMP: "Stempel",
            AnnotationType.SIGNATURE_FIELD: "Signaturfeld",
        }.get(ann.type, "Annotation")
        self.setWindowTitle(f"{kind} bearbeiten")
        self.resize(420, 280)
        self._show_style = ann.type == AnnotationType.TEXT_OVERLAY
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.text = QPlainTextEdit()
        self.text.setPlainText(ann.text or "")
        form.addRow("Text:", self.text)
        self.font_size = QDoubleSpinBox()
        self.font_size.setRange(6, 96)
        self.font_size.setValue(float(ann.font_size or 12))
        self.color = QLineEdit(ann.color or "#1A5276")
        self.opacity = QDoubleSpinBox()
        self.opacity.setRange(0.05, 1.0)
        self.opacity.setSingleStep(0.05)
        self.opacity.setDecimals(2)
        try:
            op = float(getattr(ann, "opacity", 1.0) or 1.0)
        except (TypeError, ValueError):
            op = 1.0
        self.opacity.setValue(max(0.05, min(1.0, op)))
        self.opacity.setToolTip("Deckkraft der Annotation (0.05–1.0)")
        if self._show_style:
            form.addRow("Schriftgröße (px):", self.font_size)
            form.addRow("Farbe:", self.color)
        form.addRow("Deckkraft:", self.opacity)
        from ild_pdf.annotate import tags_to_str

        self.tags_edit = QLineEdit(tags_to_str(getattr(ann, "tags", None)))
        self.tags_edit.setPlaceholderText("Tags, komma-getrennt…")
        self.tags_edit.setToolTip("Freie Labels (z. B. Review, TODO) — filterbar in der Sidebar")
        form.addRow("Tags:", self.tags_edit)
        self.rotation = None
        if ann.type == AnnotationType.STAMP:
            self.rotation = QDoubleSpinBox()
            self.rotation.setRange(0, 270)
            self.rotation.setSingleStep(90)
            self.rotation.setDecimals(0)
            try:
                rot = float(getattr(ann, "rotation", 0.0) or 0.0)
            except (TypeError, ValueError):
                rot = 0.0
            self.rotation.setValue(float(int(round(rot / 90.0)) % 4 * 90))
            self.rotation.setToolTip("Stempel-Drehung in 90°-Schritten")
            form.addRow("Drehung (°):", self.rotation)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> dict:
        from ild_pdf.annotate import normalize_tags

        out = {
            "text": self.text.toPlainText(),
            "opacity": float(self.opacity.value()),
            "tags": normalize_tags(self.tags_edit.text()),
        }
        if self._show_style:
            out["font_size"] = float(self.font_size.value())
            out["color"] = self.color.text().strip() or "#1A5276"
        if self.rotation is not None:
            rot = float(self.rotation.value())
            out["rotation"] = float(int(round(rot / 90.0)) % 4 * 90)
        return out


class PdfCanvas(QLabel):
    """Gerenderte PDF-Seite; Klick/Drag setzt Annotationen."""

    annotation_placed = Signal(float, float)
    drag_finished = Signal(float, float, float, float)  # x0,y0,x1,y1
    text_selection_finished = Signal(float, float, float, float)  # Text-Marquee (Auswahl-Modus)
    overlay_edit_requested = Signal(str)  # ann id
    annotation_selected = Signal(str)  # ann id (leer = Auswahl aufheben)
    uri_link_clicked = Signal(str)  # externe http(s)-URL
    annotations_moved = Signal(list, float, float)  # ids, dx, dy

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(200, 200)
        self._pixmap: Optional[QPixmap] = None
        self._annotations: list[Annotation] = []
        self._uri_links: list = []
        self._drag_tool: AnnotationType | None = None
        self._select_mode = False
        self._drag_start: tuple[float, float] | None = None
        self._drag_current: tuple[float, float] | None = None
        self._text_sel_start: tuple[float, float] | None = None
        self._text_sel_current: tuple[float, float] | None = None
        self._scale = 1.5
        self._search_rects: list[tuple[float, float, float, float]] = []
        self._search_active: int = -1
        self._selected_id: str | None = None
        self._selected_ids: set[str] = set()
        self._annotations_visible = True
        self._annotations_locked = False
        self._show_page_boxes = False
        self._show_printer_marks = False
        # Pixel-Rects (x,y,w,h) für MediaBox / CropBox / Druckermarken
        self._mediabox_rect: tuple[float, float, float, float] | None = None
        self._cropbox_rect: tuple[float, float, float, float] | None = None
        self._printer_marks_rect: tuple[float, float, float, float] | None = None
        self._move_ids: set[str] = set()
        self._move_origin: tuple[float, float] | None = None
        self._move_delta: tuple[float, float] = (0.0, 0.0)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    def set_uri_links(self, links: list | None):
        self._uri_links = list(links or [])

    def _hit_uri_link(self, x: float, y: float):
        for link in reversed(self._uri_links):
            if link.contains(x, y):
                return link
        return None

    def set_annotations_visible(self, visible: bool):
        self._annotations_visible = bool(visible)
        self._repaint_overlay()

    def annotations_visible(self) -> bool:
        return bool(self._annotations_visible)

    def set_annotations_locked(self, locked: bool):
        self._annotations_locked = bool(locked)
        if self._annotations_locked and self._move_origin is not None:
            self._move_ids = set()
            self._move_origin = None
            self._move_delta = (0.0, 0.0)
            self._repaint_overlay()

    def annotations_locked(self) -> bool:
        return bool(self._annotations_locked)

    def set_show_page_boxes(self, enabled: bool):
        self._show_page_boxes = bool(enabled)
        self._repaint_overlay()

    def show_page_boxes(self) -> bool:
        return bool(self._show_page_boxes)

    def set_show_printer_marks(self, enabled: bool):
        self._show_printer_marks = bool(enabled)
        self._repaint_overlay()

    def show_printer_marks(self) -> bool:
        return bool(self._show_printer_marks)

    def set_page_box_rects(
        self,
        mediabox: tuple[float, float, float, float] | None = None,
        cropbox: tuple[float, float, float, float] | None = None,
    ):
        """Pixel-Rechtecke (x, y, w, h) für Seitenrahmen-Overlay."""
        self._mediabox_rect = mediabox
        self._cropbox_rect = cropbox
        self._repaint_overlay()

    def clear_page_box_rects(self):
        self._mediabox_rect = None
        self._cropbox_rect = None
        self._repaint_overlay()

    def set_printer_marks_rect(
        self, rect: tuple[float, float, float, float] | None = None
    ):
        """Pixel-Rechteck (x, y, w, h) für Seitenrand-Druckermarken."""
        self._printer_marks_rect = rect
        self._repaint_overlay()

    def clear_printer_marks_rect(self):
        self._printer_marks_rect = None
        self._repaint_overlay()

    def _draw_printer_marks(
        self, painter: QPainter, rect: tuple[float, float, float, float]
    ):
        """Crop-/Registration-Marken an den Ecken des Rechtecks."""
        x, y, w, h = rect
        mark = max(8.0, min(18.0, min(w, h) * 0.04))
        gap = 2.0
        pen = QPen(QColor(20, 20, 20, 220), 1.5, Qt.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        # Vier Ecken: L-förmige Crop-Marks etwas außerhalb
        corners = [
            (x, y, -1, -1),  # TL
            (x + w, y, 1, -1),  # TR
            (x, y + h, -1, 1),  # BL
            (x + w, y + h, 1, 1),  # BR
        ]
        for cx, cy, sx, sy in corners:
            # horizontal
            hx0 = cx + sx * gap
            hx1 = cx + sx * (gap + mark)
            hy = cy + sy * gap
            painter.drawLine(QPointF(hx0, hy), QPointF(hx1, hy))
            # vertikal
            vx = cx + sx * gap
            vy0 = cy + sy * gap
            vy1 = cy + sy * (gap + mark)
            painter.drawLine(QPointF(vx, vy0), QPointF(vx, vy1))
        # Registrierkreuz in der Mitte der oberen Kante
        mx = x + w / 2.0
        my = y - gap - mark * 0.6
        if my > 2:
            r = mark * 0.35
            painter.drawLine(QPointF(mx - r, my), QPointF(mx + r, my))
            painter.drawLine(QPointF(mx, my - r), QPointF(mx, my + r))
            painter.drawEllipse(QPointF(mx, my), r * 0.45, r * 0.45)

    def set_drag_tool(self, tool: AnnotationType | None, *, select_mode: bool = False):
        self._select_mode = bool(select_mode)
        self._drag_tool = tool if (tool in DRAG_TYPES and not select_mode) else None
        if not self._select_mode and self._move_origin is not None:
            self._move_ids = set()
            self._move_origin = None
            self._move_delta = (0.0, 0.0)
        if not self._select_mode:
            self._text_sel_start = None
            self._text_sel_current = None
            self._repaint_overlay()

    def set_selected_id(self, ann_id: str | None):
        self._selected_id = ann_id
        self._selected_ids = {ann_id} if ann_id else set()
        self._repaint_overlay()

    def set_selected_ids(self, ann_ids: list[str] | set[str] | None):
        ids = {str(i) for i in (ann_ids or []) if i}
        self._selected_ids = ids
        self._selected_id = next(iter(ids), None)
        self._repaint_overlay()

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
        if not self._annotations_visible:
            return None
        editable = (
            AnnotationType.TEXT_OVERLAY,
            AnnotationType.TEXT,
            AnnotationType.STICKY,
            AnnotationType.CALLOUT,
            AnnotationType.STAMP,
            AnnotationType.SIGNATURE_FIELD,
        )
        for ann in reversed(self._annotations):
            if ann.type not in editable:
                continue
            x0, y0, x1, y1 = self._ann_bounds(ann)
            if x0 <= x <= x1 and y0 <= y <= y1:
                return ann
        return None

    @staticmethod
    def _ann_bounds(ann: Annotation) -> tuple[float, float, float, float]:
        """x0,y0,x1,y1 in Seitenpixeln."""
        if ann.type in (
            AnnotationType.LINE,
            AnnotationType.ARROW,
            AnnotationType.MEASURE,
            AnnotationType.CALLOUT,
        ):
            x2, y2 = ann.end_point()
            xs = [ann.x, x2]
            ys = [ann.y, y2]
            if ann.type == AnnotationType.CALLOUT:
                xs.extend([ann.x + max(ann.width, 100), ann.x])
                ys.extend([ann.y + max(ann.height, 40), ann.y])
            pad = 6.0
            return min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad
        w = max(ann.width, 8)
        h = max(ann.height, 8)
        if ann.type in (AnnotationType.STICKY, AnnotationType.STAMP, AnnotationType.SIGNATURE_FIELD):
            w = max(w, 80)
            h = max(h, 36)
        return ann.x, ann.y, ann.x + w, ann.y + h

    def _hit_annotation(self, x: float, y: float) -> Annotation | None:
        for ann in reversed(self._annotations):
            x0, y0, x1, y1 = self._ann_bounds(ann)
            if x0 <= x <= x1 and y0 <= y <= y1:
                return ann
        return None

    def _draw_ann(self, painter: QPainter, ann: Annotation, *, dx: float = 0.0, dy: float = 0.0):
        try:
            opacity = float(getattr(ann, "opacity", 1.0) or 1.0)
        except (TypeError, ValueError):
            opacity = 1.0
        opacity = max(0.05, min(1.0, opacity))

        def _a(base: int) -> int:
            return max(0, min(255, int(round(base * opacity))))

        color = QColor(ann.color)
        color.setAlpha(_a(90 if ann.type == AnnotationType.HIGHLIGHT else 200))
        # Deckkraft nur über α der Farben — kein zusätzliches painter.setOpacity
        # (sonst doppelte Multiplikation bei Fills mit _a(...)).
        pen_c = QColor(ann.color)
        pen_c.setAlpha(_a(255))
        pen = QPen(pen_c)
        pen.setWidth(2)
        painter.setPen(pen)
        x, y = int(ann.x + dx), int(ann.y + dy)
        w, h = int(ann.width), int(ann.height)

        if ann.type == AnnotationType.HIGHLIGHT:
            painter.fillRect(x, y, w, h, color)
        elif ann.type == AnnotationType.REDACTION:
            rw, rh = max(w, 4), max(h, 4)
            painter.fillRect(x, y, rw, rh, QColor(0, 0, 0, _a(230)))
            # Sichtbarer Hinweisrahmen (besserer UX vor Einbrennen)
            painter.setPen(QPen(QColor(220, 50, 50), 2, Qt.DashLine))
            painter.drawRect(x, y, rw, rh)
            painter.setPen(QColor(255, 220, 220))
            if rw >= 36 and rh >= 14:
                painter.drawText(x + 3, y + min(14, rh - 2), "REDACT")
        elif ann.type == AnnotationType.UNDERLINE:
            painter.drawLine(x, y + h, x + w, y + h)
        elif ann.type == AnnotationType.STICKY:
            fill = QColor(ann.color if ann.color else "#FFEB3B")
            fill.setAlpha(_a(200))
            painter.fillRect(x, y, max(w, 80), max(h, 60), fill)
            # Textkontrast je nach Helligkeit der Notizfarbe
            painter.setPen(QColor("#111111" if fill.lightness() > 140 else "#FFFFFF"))
            painter.drawText(x + 4, y + 16, (ann.text or "Notiz")[:40])
        elif ann.type == AnnotationType.TEXT:
            painter.drawRect(x, y, w, h)
            painter.drawText(x + 4, y + 16, (ann.text or "")[:60])
        elif ann.type == AnnotationType.TEXT_OVERLAY:
            painter.fillRect(x, y, max(w, 40), max(h, 18), QColor(255, 255, 255, _a(160)))
            painter.setPen(QPen(QColor(ann.color), 1, Qt.DashLine))
            painter.drawRect(x, y, max(w, 40), max(h, 18))
            painter.setPen(QColor(ann.color))
            painter.drawText(x + 2, y + int(max(ann.font_size, 12)), (ann.text or "")[:80])
        elif ann.type in (AnnotationType.STAMP, AnnotationType.SIGNATURE):
            try:
                rot = float(getattr(ann, "rotation", 0.0) or 0.0)
            except (TypeError, ValueError):
                rot = 0.0
            rot = float(int(round(rot / 90.0)) % 4 * 90)
            box_h = max(h, 48 if "\n" in (ann.text or "") else 36)
            box_w = max(w, 120)
            if ann.type == AnnotationType.SIGNATURE and not (ann.text or "").startswith("img:"):
                box_w, box_h = max(w, 80), max(h, 32)
            cx = x + box_w / 2.0
            cy = y + box_h / 2.0
            painter.save()
            if rot:
                painter.translate(cx, cy)
                painter.rotate(rot)
                painter.translate(-cx, -cy)
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
                        painter.restore()
                        painter.setOpacity(1.0)
                        return
            if ann.type == AnnotationType.SIGNATURE:
                painter.setPen(QPen(QColor("#2C3E50"), 2, Qt.DashLine))
                painter.drawRect(x, y, max(w, 80), max(h, 32))
                painter.drawText(x + 4, y + 16, "Signatur")
                painter.restore()
                painter.setOpacity(1.0)
                return
            stamp_color = QColor(ann.color if ann.color != "#FFFF00" else "#C0392B")
            painter.setPen(QPen(stamp_color, 3))
            painter.drawRect(x, y, box_w, box_h)
            painter.setPen(stamp_color)
            lines = (ann.text or "STEMPEL").splitlines()[:3]
            ty = y + 16
            for line in lines:
                painter.drawText(x + 8, ty, line[:28])
                ty += 16
            painter.restore()
        elif ann.type == AnnotationType.SIGNATURE_FIELD:
            painter.setPen(QPen(QColor(ann.color or "#7F8C8D"), 2, Qt.DashLine))
            painter.setBrush(QColor(255, 255, 255, _a(30)))
            fh = max(int(h), 48)
            fw = max(int(w), 160)
            painter.drawRect(x, y, fw, fh)
            painter.drawLine(x + 8, y + fh - 10, x + fw - 8, y + fh - 10)
            painter.setPen(QColor(ann.color or "#7F8C8D"))
            painter.drawText(x + 8, y + 18, (ann.text or "Unterschrift")[:40])
        elif ann.type == AnnotationType.CALLOUT:
            box_w, box_h = max(w, 100), max(h, 40)
            painter.setBrush(QColor(255, 255, 220, _a(220)))
            painter.drawRect(x, y, box_w, box_h)
            painter.drawText(x + 4, y + 16, (ann.text or "Callout")[:40])
            cx = int(ann.callout_x + dx) if ann.callout_x else x - 40
            cy = int(ann.callout_y + dy) if ann.callout_y else y + box_h + 30
            painter.drawLine(x, y + box_h, cx, cy)
            painter.drawEllipse(cx - 3, cy - 3, 6, 6)
        elif ann.type == AnnotationType.RECTANGLE:
            painter.setBrush(QColor(ann.color))
            c = QColor(ann.color)
            c.setAlpha(_a(40))
            painter.fillRect(x, y, w, h, c)
            painter.drawRect(x, y, w, h)
        elif ann.type in (AnnotationType.LINE, AnnotationType.ARROW, AnnotationType.MEASURE):
            x2, y2 = ann.end_point()
            x2, y2 = x2 + dx, y2 + dy
            painter.drawLine(x, y, int(x2), int(y2))
            if ann.type == AnnotationType.ARROW:
                self._draw_arrow_head(painter, float(x), float(y), x2, y2)
            if ann.type == AnnotationType.MEASURE:
                mid_x = (x + x2) / 2
                mid_y = (y + y2) / 2
                label = ann.text or ann.measure_label(self._scale)
                painter.drawText(int(mid_x) + 4, int(mid_y) - 4, label)
        painter.setOpacity(1.0)

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
        # Optional: MediaBox / CropBox Rahmen
        if self._show_page_boxes:
            if self._mediabox_rect:
                mx, my, mw, mh = self._mediabox_rect
                painter.setPen(QPen(QColor(40, 110, 220, 180), 2, Qt.SolidLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(int(mx), int(my), max(int(mw) - 1, 1), max(int(mh) - 1, 1))
            if self._cropbox_rect:
                cx, cy, cw, ch = self._cropbox_rect
                painter.setPen(QPen(QColor(220, 60, 40, 200), 2, Qt.DashLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(int(cx), int(cy), max(int(cw) - 1, 1), max(int(ch) - 1, 1))
        # Optional: Seitenrand-Druckermarken (Crop/Registration)
        if self._show_printer_marks and self._printer_marks_rect:
            self._draw_printer_marks(painter, self._printer_marks_rect)
        move_dx, move_dy = self._move_delta if self._move_origin is not None else (0.0, 0.0)
        if self._annotations_visible:
            for ann in self._annotations:
                dx = move_dx if ann.id in self._move_ids else 0.0
                dy = move_dy if ann.id in self._move_ids else 0.0
                self._draw_ann(painter, ann, dx=dx, dy=dy)
                if ann.id in self._selected_ids or (
                    self._selected_id and ann.id == self._selected_id
                ):
                    x0, y0, x1, y1 = self._ann_bounds(ann)
                    x0, y0, x1, y1 = x0 + dx, y0 + dy, x1 + dx, y1 + dy
                    sel = QPen(QColor(30, 144, 255), 2, Qt.DashLine)
                    painter.setPen(sel)
                    painter.setBrush(Qt.NoBrush)
                    painter.drawRect(int(x0) - 2, int(y0) - 2, int(x1 - x0) + 4, int(y1 - y0) + 4)
        # Drag-Vorschau (auch bei ausgeblendetem Layer sichtbar)
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
        # Text-Auswahl-Marquee (Auswahl-Modus → Zwischenablage)
        if self._text_sel_start and self._text_sel_current:
            tx0, ty0 = self._text_sel_start
            tx1, ty1 = self._text_sel_current
            rx, ry = min(tx0, tx1), min(ty0, ty1)
            rw, rh = abs(tx1 - tx0), abs(ty1 - ty0)
            painter.fillRect(
                int(rx), int(ry), max(int(rw), 2), max(int(rh), 2), QColor(70, 130, 230, 70)
            )
            painter.setPen(QPen(QColor(40, 90, 200), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(int(rx), int(ry), max(int(rw), 2), max(int(rh), 2))
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
            # Ctrl+Klick: URI-Link öffnen wenn getroffen, sonst Overlay-Edit
            if event.button() == Qt.LeftButton and event.modifiers() & Qt.ControlModifier:
                link = self._hit_uri_link(x, y)
                if link:
                    self.uri_link_clicked.emit(link.uri)
                    return
            hit = self._hit_overlay(x, y)
            if hit:
                self.overlay_edit_requested.emit(hit.id)
                return
            # Rechtsklick: Annotation auswählen (für Löschen)
            if event.button() == Qt.RightButton:
                hit_any = self._hit_annotation(x, y)
                self.annotation_selected.emit(hit_any.id if hit_any else "")
                return
        if self._select_mode and event.button() == Qt.LeftButton:
            link = self._hit_uri_link(x, y)
            if link and not (event.modifiers() & Qt.ShiftModifier):
                self.uri_link_clicked.emit(link.uri)
                return
            hit_any = self._hit_annotation(x, y)
            if hit_any:
                self.annotation_selected.emit(hit_any.id if hit_any else "")
                # Verschieben starten wenn nicht gesperrt
                if (
                    hit_any
                    and not self._annotations_locked
                    and not (event.modifiers() & Qt.ShiftModifier)
                ):
                    ids = set(self._selected_ids) if self._selected_ids else set()
                    if hit_any.id not in ids:
                        ids = {hit_any.id}
                    self._move_ids = ids
                    self._move_origin = (x, y)
                    self._move_delta = (0.0, 0.0)
                    self.setCursor(QCursor(Qt.ClosedHandCursor))
                return
            # Leere Fläche → Text-Auswahl-Marquee (Kopieren in Zwischenablage)
            if not (event.modifiers() & Qt.ShiftModifier):
                self.annotation_selected.emit("")
                self._text_sel_start = (x, y)
                self._text_sel_current = (x, y)
                self._repaint_overlay()
            return
        if event.button() == Qt.LeftButton and event.modifiers() & Qt.ShiftModifier:
            hit_any = self._hit_annotation(x, y)
            if hit_any:
                self.annotation_selected.emit(hit_any.id)
                return
        if self._drag_tool and event.button() == Qt.LeftButton:
            self._drag_start = (x, y)
            self._drag_current = (x, y)
            return
        if event.button() == Qt.LeftButton:
            self.annotation_placed.emit(x, y)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._move_origin is not None:
            pt = self._map_to_page(event)
            if pt:
                ox, oy = self._move_origin
                self._move_delta = (pt[0] - ox, pt[1] - oy)
                self._repaint_overlay()
            return
        if self._text_sel_start is not None:
            pt = self._map_to_page(event)
            if pt:
                self._text_sel_current = pt
                self._repaint_overlay()
            return
        if self._drag_start is not None:
            pt = self._map_to_page(event)
            if pt:
                self._drag_current = pt
                self._repaint_overlay()
        else:
            pt = self._map_to_page(event)
            if pt and self._hit_uri_link(*pt):
                self.setCursor(QCursor(Qt.PointingHandCursor))
            elif (
                pt
                and self._select_mode
                and not self._annotations_locked
                and self._hit_annotation(*pt)
            ):
                self.setCursor(QCursor(Qt.OpenHandCursor))
            else:
                self.unsetCursor()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._move_origin is not None and event.button() == Qt.LeftButton:
            dx, dy = self._move_delta
            ids = list(self._move_ids)
            self._move_ids = set()
            self._move_origin = None
            self._move_delta = (0.0, 0.0)
            self.unsetCursor()
            if ids and (abs(dx) > 2 or abs(dy) > 2):
                self.annotations_moved.emit(ids, float(dx), float(dy))
            else:
                self._repaint_overlay()
            return
        if self._text_sel_start is not None and event.button() == Qt.LeftButton:
            pt = self._map_to_page(event) or self._text_sel_current
            if pt:
                x0, y0 = self._text_sel_start
                x1, y1 = pt
                self._text_sel_start = None
                self._text_sel_current = None
                if abs(x1 - x0) > 3 or abs(y1 - y0) > 3:
                    self.text_selection_finished.emit(x0, y0, x1, y1)
                else:
                    self._repaint_overlay()
            else:
                self._text_sel_start = None
                self._text_sel_current = None
                self._repaint_overlay()
            return
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
    page_favorites_changed = Signal()
    page_changed = Signal(int)  # 0-basiert
    zoom_changed = Signal(float)  # scale (1.0 = 100%)
    document_changed = Signal()  # Pfad/Seiten geändert (Statusleiste)
    grayscale_changed = Signal(bool)  # Toolbar ↔ Menü sync
    night_mode_changed = Signal(bool)
    annotations_layer_changed = Signal(bool)
    annotations_lock_changed = Signal(bool)
    page_boxes_changed = Signal(bool)
    printer_marks_changed = Signal(bool)
    two_page_spread_changed = Signal(bool)
    continuous_scroll_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pdf_path: Optional[Path] = None
        self.page_index = 0
        self.page_count = 0
        self._page_labels: list[str] = []
        self.scale = get_default_zoom_scale()
        self.tool: AnnotationType | None = AnnotationType.HIGHLIGHT
        self.store: Optional[AnnotationStore] = None
        self.password: Optional[str] = None
        self._tool_buttons: list[QToolButton] = []
        self._pending_callout_anchor: tuple[float, float] | None = None
        self._pending_callout_page: int = 0
        self._zoom_timer = QTimer(self)
        self._zoom_timer.setSingleShot(True)
        self._zoom_timer.setInterval(120)
        self._zoom_timer.timeout.connect(self._apply_pending_zoom)
        self._pending_scale: float | None = None
        self._highlight_color = get_ann_highlight_color()
        self._pen_color = get_ann_pen_color()
        self._note_color = get_ann_note_color()
        self._grayscale = get_pdf_grayscale()
        self._night_mode = get_pdf_night_mode()
        self._two_page_spread = get_pdf_two_page_spread()
        self._continuous_scroll = get_pdf_continuous_scroll()
        if self._continuous_scroll and self._two_page_spread:
            # Mutual exclusive: Continuous bevorzugt wenn beide gesetzt
            self._two_page_spread = False
            set_pdf_two_page_spread(False)
        self._spread_left_width = 0.0
        self._spread_gap = 12
        self._continuous_offsets: list[tuple[int, float, float]] = []  # page, y0, height
        self._continuous_gap = CONTINUOUS_PAGE_GAP
        self._continuous_scroll_syncing = False
        self._default_opacity = get_ann_default_opacity()
        self._annotations_visible = get_annotations_visible()
        self._annotations_locked = get_annotations_locked()
        self._show_page_boxes = get_show_page_boxes()
        self._show_printer_marks = get_show_printer_marks()
        self._search_query = ""
        self._search_rects: list[tuple[float, float, float, float]] = []
        self._search_index = -1
        self._selected_ann_id: str | None = None
        self._selected_ann_ids: set[str] = set()
        self._ann_clipboard: list[dict] = []
        self._page_ops_undo: list[dict] = []  # Seiten-Löschen/Drehen rückgängig
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
        btn_fit_h = QPushButton("Höhe")
        btn_fit_h.setToolTip("Seitenhöhe einpassen (Ctrl+8)")
        btn_fit_h.clicked.connect(self.fit_height)
        btn_undo = QPushButton("↶")
        btn_undo.setToolTip("Annotation / Seite rückgängig (Ctrl+Z)")
        btn_undo.clicked.connect(self.undo_annotation)
        btn_redo = QPushButton("↷")
        btn_redo.setToolTip("Annotation wiederholen (Ctrl+Y)")
        btn_redo.clicked.connect(self.redo_annotation)
        btn_hist = QPushButton("Historie…")
        btn_hist.setToolTip("Seiten-Undo-Historie: gelöschte/gedrehte Seiten wiederherstellen")
        btn_hist.clicked.connect(self.show_page_ops_history)
        self.btn_fav = QPushButton("★")
        self.btn_fav.setFixedWidth(28)
        self.btn_fav.setCheckable(True)
        self.btn_fav.setToolTip(
            "Aktuelle Seite als Favorit markieren/entfernen (Ctrl+Shift+F) — schnell springen"
        )
        self.btn_fav.clicked.connect(self.toggle_page_favorite)
        self.btn_fav_jump = QPushButton("★…")
        self.btn_fav_jump.setFixedWidth(36)
        self.btn_fav_jump.setToolTip("Zu Favoriten-Seite springen (Ctrl+Alt+F)")
        self.btn_fav_jump.clicked.connect(self.show_page_favorites)
        btn_del_ann = QPushButton("Ann. löschen")
        btn_del_ann.setToolTip("Ausgewählte Annotation löschen, sonst die letzte (Entf)")
        btn_del_ann.clicked.connect(self.delete_annotation)
        btn_ann_color = QPushButton("Farbe…")
        btn_ann_color.setToolTip(
            "Farbe der ausgewählten Annotation(en) ändern (Batch, Ctrl+Alt+Shift+F)"
        )
        btn_ann_color.clicked.connect(self.recolor_selected_annotations)
        btn_ann_opacity = QPushButton("α…")
        btn_ann_opacity.setToolTip(
            "Deckkraft der ausgewählten Annotation(en) ändern (Batch, Ctrl+Alt+Shift+O)"
        )
        btn_ann_opacity.clicked.connect(self.set_opacity_selected_annotations)
        btn_stamp_rot = QPushButton("Stempel ↻")
        btn_stamp_rot.setToolTip("Ausgewählten Stempel um 90° drehen")
        btn_stamp_rot.clicked.connect(lambda: self.rotate_selected_stamp(90))
        btn_rot_ccw = QPushButton("⟲")
        btn_rot_ccw.setToolTip("Aktuelle Seite 90° gegen den Uhrzeigersinn drehen (−90°) und speichern")
        btn_rot_ccw.clicked.connect(lambda: self.rotate_current(-90))
        btn_rot = QPushButton("⟳")
        btn_rot.setToolTip("Aktuelle Seite 90° im Uhrzeigersinn drehen und speichern")
        btn_rot.clicked.connect(lambda: self.rotate_current(90))
        btn_flip_h = QPushButton("↔")
        btn_flip_h.setToolTip("Aktuelle Seite horizontal spiegeln (links↔rechts) und speichern")
        btn_flip_h.clicked.connect(lambda: self.flip_current(horizontal=True))
        btn_flip_v = QPushButton("↕")
        btn_flip_v.setToolTip("Aktuelle Seite vertikal spiegeln (oben↔unten) und speichern")
        btn_flip_v.clicked.connect(lambda: self.flip_current(vertical=True))
        btn_blank = QPushButton("Leere Seite")
        btn_blank.setToolTip("Leere Seite nach der aktuellen einfügen und speichern")
        btn_blank.clicked.connect(self.insert_blank_after_current)
        btn_dup = QPushButton("Duplizieren")
        btn_dup.setToolTip("Aktuelle Seite duplizieren und speichern")
        btn_dup.clicked.connect(self.duplicate_current)
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
        btn_extract.setToolTip("Aktuelle Seite als PNG/JPEG exportieren")
        btn_extract.clicked.connect(self.extract_page_as_image)
        btn_extract_all = QPushButton("Seiten→Bilder")
        btn_extract_all.setToolTip("Alle Seiten als PNG/JPEG exportieren")
        btn_extract_all.clicked.connect(self.export_pages_as_images)
        btn_img_page = QPushButton("Bild→Seite")
        btn_img_page.setToolTip("Bild als neue PDF-Seite anhängen")
        btn_img_page.clicked.connect(self.insert_image_page)
        btn_import_text = QPushButton("Text→Overlay")
        btn_import_text.setToolTip("PDF-Textblöcke als editierbare Overlays (Sidecar)")
        btn_import_text.clicked.connect(self.import_text_overlays)
        btn_bake = QPushButton("Overlay einbrennen")
        btn_bake.setToolTip("TEXT_OVERLAY in PDF-Content schreiben (Helvetica)")
        btn_bake.clicked.connect(self.bake_overlays)

        # Auswahl-Werkzeug (tool=None)
        btn_select = QToolButton()
        btn_select.setText("Auswahl")
        btn_select.setCheckable(True)
        btn_select.setToolTip(
            "Annotation anklicken zum Auswählen; Entf löscht; "
            "PDF-Links (http/https) öffnen; Ctrl+Klick öffnet Link auch mit anderem Werkzeug"
        )
        btn_select.clicked.connect(lambda checked: self._set_tool(None))
        self._tool_buttons.append(btn_select)
        toolbar.addWidget(btn_select)

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
            if t == AnnotationType.HIGHLIGHT:
                b.setToolTip(
                    "Highlight: Text aufziehen (Selection→Highlight) oder freies Rechteck — speichert Annotation"
                )
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
        self.btn_note_color = QPushButton("Notiz")
        self.btn_note_color.setToolTip("Notizfarbe (Sticky) — unabhängig von Highlight")
        self.btn_note_color.setFixedWidth(48)
        self.btn_note_color.clicked.connect(self._pick_note_color)
        self._style_color_btn(self.btn_note_color, self._note_color)
        self.spin_opacity = QDoubleSpinBox()
        self.spin_opacity.setRange(0.05, 1.0)
        self.spin_opacity.setSingleStep(0.05)
        self.spin_opacity.setDecimals(2)
        self.spin_opacity.setValue(self._default_opacity)
        self.spin_opacity.setPrefix("α ")
        self.spin_opacity.setFixedWidth(78)
        self.spin_opacity.setToolTip(
            "Deckkraft: Standard für neue Annotationen; bei Auswahl → ausgewählte Ann."
        )
        self.spin_opacity.valueChanged.connect(self._on_default_opacity_changed)
        # Toolbar-Slider (0.05–1.0 als 5–100 %) — nicht nur Dialog α…
        self.slider_opacity = QSlider(Qt.Horizontal)
        self.slider_opacity.setRange(5, 100)
        self.slider_opacity.setSingleStep(5)
        self.slider_opacity.setPageStep(10)
        self.slider_opacity.setFixedWidth(88)
        self.slider_opacity.setValue(int(round(self._default_opacity * 100)))
        self.slider_opacity.setToolTip(
            "Annotation-Deckkraft per Slider (Auswahl oder Standard) — ohne Dialog"
        )
        self.slider_opacity.valueChanged.connect(self._on_opacity_slider_changed)
        self.btn_grayscale = QToolButton()
        self.btn_grayscale.setText("Grau")
        self.btn_grayscale.setCheckable(True)
        self.btn_grayscale.setChecked(self._grayscale)
        self.btn_grayscale.setToolTip("PDF-Seiten in Graustufen rendern/exportieren")
        self.btn_grayscale.toggled.connect(self.set_grayscale)
        self.btn_night = QToolButton()
        self.btn_night.setText("Nacht")
        self.btn_night.setCheckable(True)
        self.btn_night.setChecked(self._night_mode)
        self.btn_night.setToolTip(
            "Nachtmodus: dunkle Invert-Ansicht (nur Darstellung, nicht speichern/exportieren)"
        )
        self.btn_night.toggled.connect(self.set_night_mode)
        self.btn_spread = QToolButton()
        self.btn_spread.setText("2S")
        self.btn_spread.setCheckable(True)
        self.btn_spread.setChecked(self._two_page_spread)
        self.btn_spread.setToolTip(
            "Zwei-Seiten-Ansicht (Spread): aktuelle + nächste Seite nebeneinander"
        )
        self.btn_spread.toggled.connect(self.set_two_page_spread)
        self.btn_continuous = QToolButton()
        self.btn_continuous.setText("CS")
        self.btn_continuous.setCheckable(True)
        self.btn_continuous.setChecked(self._continuous_scroll)
        self.btn_continuous.setToolTip(
            "Continuous Scroll: Seiten untereinander (statt Einzelseite; schließt Spread aus)"
        )
        self.btn_continuous.toggled.connect(self.set_continuous_scroll)
        self.btn_ann_layer = QToolButton()
        self.btn_ann_layer.setText("Ann.")
        self.btn_ann_layer.setCheckable(True)
        self.btn_ann_layer.setChecked(self._annotations_visible)
        self.btn_ann_layer.setToolTip("Annotation-Layer ein-/ausblenden")
        self.btn_ann_layer.toggled.connect(self.set_annotations_visible)
        self.btn_ann_lock = QToolButton()
        self.btn_ann_lock.setText("Sperre")
        self.btn_ann_lock.setCheckable(True)
        self.btn_ann_lock.setChecked(self._annotations_locked)
        self.btn_ann_lock.setToolTip(
            "Annotationen sperren (nicht verschiebbar) — Auswahl-Werkzeug + Ziehen"
        )
        self.btn_ann_lock.toggled.connect(self.set_annotations_locked)
        self.btn_page_boxes = QToolButton()
        self.btn_page_boxes.setText("Rahmen")
        self.btn_page_boxes.setCheckable(True)
        self.btn_page_boxes.setChecked(self._show_page_boxes)
        self.btn_page_boxes.setToolTip("MediaBox/CropBox-Seitenrahmen als Overlay anzeigen")
        self.btn_page_boxes.toggled.connect(self.set_show_page_boxes)
        self.btn_printer_marks = QToolButton()
        self.btn_printer_marks.setText("Marken")
        self.btn_printer_marks.setCheckable(True)
        self.btn_printer_marks.setChecked(self._show_printer_marks)
        self.btn_printer_marks.setToolTip(
            "Seitenrand-Druckermarken (Crop/Registration) als Overlay anzeigen"
        )
        self.btn_printer_marks.toggled.connect(self.set_show_printer_marks)
        toolbar.addWidget(self.btn_hl_color)
        toolbar.addWidget(self.btn_pen_color)
        toolbar.addWidget(self.btn_note_color)
        self._preset_btns: list[QPushButton] = []
        for i in range(3):
            pb = QPushButton(str(i + 1))
            pb.setFixedWidth(22)
            pb.setToolTip(
                f"Favorit {i + 1}: Klick = Highlight-Farbe · Shift+Klick = Stift · "
                "Rechtsklick = aktuellen HL speichern"
            )
            pb.clicked.connect(lambda checked=False, idx=i: self._apply_color_preset(idx))
            pb.setContextMenuPolicy(Qt.CustomContextMenu)
            pb.customContextMenuRequested.connect(
                lambda pos, idx=i, btn=pb: self._save_color_preset(idx)
            )
            self._preset_btns.append(pb)
            toolbar.addWidget(pb)
        self._refresh_preset_btns()
        toolbar.addWidget(self.spin_opacity)
        toolbar.addWidget(self.slider_opacity)
        toolbar.addWidget(self.btn_grayscale)
        toolbar.addWidget(self.btn_night)
        toolbar.addWidget(self.btn_spread)
        toolbar.addWidget(self.btn_continuous)
        toolbar.addWidget(self.btn_ann_layer)
        toolbar.addWidget(self.btn_ann_lock)
        toolbar.addWidget(self.btn_page_boxes)
        toolbar.addWidget(self.btn_printer_marks)

        toolbar.addWidget(btn_prev)
        toolbar.addWidget(self.lbl_page)
        toolbar.addWidget(btn_next)
        toolbar.addWidget(btn_undo)
        toolbar.addWidget(btn_redo)
        toolbar.addWidget(btn_hist)
        toolbar.addWidget(self.btn_fav)
        toolbar.addWidget(self.btn_fav_jump)
        toolbar.addWidget(btn_del_ann)
        toolbar.addWidget(btn_ann_color)
        toolbar.addWidget(btn_ann_opacity)
        toolbar.addWidget(btn_stamp_rot)
        toolbar.addWidget(btn_zoom_out)
        toolbar.addWidget(self.lbl_zoom)
        toolbar.addWidget(btn_zoom_in)
        toolbar.addWidget(btn_fit)
        toolbar.addWidget(btn_fit_w)
        toolbar.addWidget(btn_fit_h)
        toolbar.addWidget(btn_rot_ccw)
        toolbar.addWidget(btn_rot)
        toolbar.addWidget(btn_flip_h)
        toolbar.addWidget(btn_flip_v)
        toolbar.addWidget(btn_blank)
        toolbar.addWidget(btn_dup)
        toolbar.addWidget(btn_del)
        toolbar.addWidget(btn_reorder)
        toolbar.addWidget(btn_save_ann)
        toolbar.addWidget(btn_reload_ann)
        toolbar.addWidget(btn_extract)
        toolbar.addWidget(btn_extract_all)
        toolbar.addWidget(btn_img_page)
        toolbar.addWidget(btn_import_text)
        toolbar.addWidget(btn_bake)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        self._toolbar_group_widgets: dict[str, list] = {
            "tools": list(self._tool_buttons),
            "colors": [
                self.btn_hl_color,
                self.btn_pen_color,
                self.btn_note_color,
                *self._preset_btns,
                self.spin_opacity,
                self.slider_opacity,
            ],
            "view": [
                self.btn_grayscale,
                self.btn_night,
                self.btn_spread,
                self.btn_continuous,
                self.btn_ann_layer,
                self.btn_ann_lock,
                self.btn_page_boxes,
                self.btn_printer_marks,
            ],
            "nav": [btn_prev, self.lbl_page, btn_next],
            "history": [
                btn_undo,
                btn_redo,
                btn_hist,
                self.btn_fav,
                self.btn_fav_jump,
                btn_del_ann,
                btn_ann_color,
                btn_ann_opacity,
                btn_stamp_rot,
            ],
            "zoom": [
                btn_zoom_out,
                self.lbl_zoom,
                btn_zoom_in,
                btn_fit,
                btn_fit_w,
                btn_fit_h,
            ],
            "pages": [
                btn_rot_ccw,
                btn_rot,
                btn_flip_h,
                btn_flip_v,
                btn_blank,
                btn_dup,
                btn_del,
                btn_reorder,
            ],
            "io": [
                btn_save_ann,
                btn_reload_ann,
                btn_extract,
                btn_extract_all,
                btn_img_page,
                btn_import_text,
                btn_bake,
            ],
        }
        self.apply_toolbar_groups()

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.canvas = PdfCanvas()
        self.canvas.set_annotations_visible(self._annotations_visible)
        self.canvas.set_annotations_locked(self._annotations_locked)
        self.canvas.set_show_page_boxes(self._show_page_boxes)
        self.canvas.set_show_printer_marks(self._show_printer_marks)
        self.canvas.annotation_placed.connect(self._on_place)
        self.canvas.drag_finished.connect(self._on_drag)
        self.canvas.text_selection_finished.connect(self._on_text_selection)
        self.canvas.overlay_edit_requested.connect(self._edit_overlay)
        self.canvas.annotation_selected.connect(self._on_annotation_selected)
        self.canvas.uri_link_clicked.connect(self._open_uri_link)
        self.canvas.annotations_moved.connect(self._on_annotations_moved)
        self.scroll.setWidget(self.canvas)
        self.scroll.verticalScrollBar().valueChanged.connect(self._on_continuous_scroll)
        layout.addWidget(self.scroll)
        self.canvas.set_drag_tool(AnnotationType.HIGHLIGHT, select_mode=False)
        self._text_selection_text = ""
        self._text_selection_rects: list[tuple[float, float, float, float]] = []
        paste_sc = QShortcut(QKeySequence.Paste, self)
        paste_sc.activated.connect(self.paste_clipboard_image)
        copy_sc = QShortcut(QKeySequence.Copy, self)
        copy_sc.setContext(Qt.WidgetWithChildrenShortcut)
        copy_sc.activated.connect(self.copy_text_selection)
        del_sc = QShortcut(QKeySequence.Delete, self)
        del_sc.activated.connect(self.delete_annotation)
        back_sc = QShortcut(QKeySequence(Qt.Key_Backspace), self)
        back_sc.activated.connect(self.delete_annotation)
        cycle_sc = QShortcut(QKeySequence("Ctrl+Shift+C"), self)
        cycle_sc.setContext(Qt.WidgetWithChildrenShortcut)
        cycle_sc.activated.connect(self.cycle_annotation_color)
        rand_sc = QShortcut(QKeySequence("Ctrl+Alt+Shift+C"), self)
        rand_sc.setContext(Qt.WidgetWithChildrenShortcut)
        rand_sc.activated.connect(self.randomize_annotation_color)
        fav_sc = QShortcut(QKeySequence("Ctrl+Shift+F"), self)
        fav_sc.setContext(Qt.WidgetWithChildrenShortcut)
        fav_sc.activated.connect(self.toggle_page_favorite)
        fav_jump_sc = QShortcut(QKeySequence("Ctrl+Alt+F"), self)
        fav_jump_sc.setContext(Qt.WidgetWithChildrenShortcut)
        fav_jump_sc.activated.connect(self.show_page_favorites)
        recolor_sc = QShortcut(QKeySequence("Ctrl+Alt+Shift+F"), self)
        recolor_sc.setContext(Qt.WidgetWithChildrenShortcut)
        recolor_sc.activated.connect(self.recolor_selected_annotations)
        opacity_sc = QShortcut(QKeySequence("Ctrl+Alt+Shift+O"), self)
        opacity_sc.setContext(Qt.WidgetWithChildrenShortcut)
        opacity_sc.activated.connect(self.set_opacity_selected_annotations)

    def apply_toolbar_groups(self) -> None:
        """Sichtbarkeit der PDF-Toolbar-Gruppen aus den Einstellungen anwenden."""
        from instantlensdoc.core.app_settings import get_pdf_toolbar_groups

        groups = get_pdf_toolbar_groups()
        mapping = getattr(self, "_toolbar_group_widgets", None)
        if not isinstance(mapping, dict):
            return
        for name, widgets in mapping.items():
            visible = bool(groups.get(name, True))
            for w in widgets:
                w.setVisible(visible)

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

    def _pick_note_color(self):
        initial = QColor(self._note_color)
        color = QColorDialog.getColor(initial, self, "Notizfarbe")
        if color.isValid():
            self._note_color = color.name()
            set_ann_note_color(self._note_color)
            self._style_color_btn(self.btn_note_color, self._note_color)
            self.status.emit(f"Notizfarbe: {self._note_color}")

    def _refresh_preset_btns(self):
        presets = get_ann_color_presets()
        for i, btn in enumerate(getattr(self, "_preset_btns", []) or []):
            c = presets[i] if i < len(presets) else "#888888"
            self._style_color_btn(btn, c)
            btn.setToolTip(
                f"Favorit {i + 1}: {c} — Klick = Highlight · Shift+Klick = Stift · "
                "Ctrl+Klick = Notiz · Rechtsklick = HL speichern"
            )

    def _apply_color_preset(self, index: int):
        presets = get_ann_color_presets()
        if index < 0 or index >= len(presets):
            return
        color = presets[index]
        mods = QApplication.keyboardModifiers()
        if mods & Qt.ControlModifier:
            self._note_color = color
            set_ann_note_color(color)
            self._style_color_btn(self.btn_note_color, color)
            self.status.emit(f"Notizfarbe (Favorit {index + 1}): {color}")
        elif mods & Qt.ShiftModifier:
            self._pen_color = color
            set_ann_pen_color(color)
            self._style_color_btn(self.btn_pen_color, color)
            self.status.emit(f"Stift-Farbe (Favorit {index + 1}): {color}")
        else:
            self._highlight_color = color
            set_ann_highlight_color(color)
            self._style_color_btn(self.btn_hl_color, color)
            self.status.emit(f"Highlight-Farbe (Favorit {index + 1}): {color}")

    def _save_color_preset(self, index: int):
        set_ann_color_preset(index, self._highlight_color)
        self._refresh_preset_btns()
        self.status.emit(f"Favorit {index + 1} = {self._highlight_color}")

    def _apply_active_color(self, color: str, *, label: str) -> None:
        """Aktive Farbe setzen (Highlight; Shift=Stift; Ctrl=Notiz)."""
        color = (color or "").strip()
        if not color:
            return
        mods = QApplication.keyboardModifiers()
        if mods & Qt.ControlModifier:
            self._note_color = color
            set_ann_note_color(color)
            self._style_color_btn(self.btn_note_color, color)
            self.status.emit(f"Notizfarbe ({label}): {color}")
        elif mods & Qt.ShiftModifier:
            self._pen_color = color
            set_ann_pen_color(color)
            self._style_color_btn(self.btn_pen_color, color)
            self.status.emit(f"Stift-Farbe ({label}): {color}")
        else:
            self._highlight_color = color
            set_ann_highlight_color(color)
            self._style_color_btn(self.btn_hl_color, color)
            self.status.emit(f"Highlight-Farbe ({label}): {color}")

    def cycle_annotation_color(self) -> str:
        """Nächste Farbe aus der festen Palette (Ctrl+Shift+C)."""
        color = cycle_ann_palette_color()
        # Modifier beim Shortcut oft schon Shift/Ctrl — hier nur Highlight setzen
        self._highlight_color = color
        set_ann_highlight_color(color)
        self._style_color_btn(self.btn_hl_color, color)
        self.status.emit(f"Palette-Zyklus: {color}")
        return color

    def randomize_annotation_color(self) -> str:
        """Zufällige Palette-Farbe (Ctrl+Alt+Shift+C)."""
        color = random_ann_palette_color()
        self._highlight_color = color
        set_ann_highlight_color(color)
        self._style_color_btn(self.btn_hl_color, color)
        self.status.emit(f"Farbe random: {color}")
        return color

    def _sync_opacity_controls(self, value: float, *, from_slider: bool = False):
        """Spin und Slider ohne Feedback-Schleife synchronisieren."""
        op = max(0.05, min(1.0, float(value)))
        if hasattr(self, "spin_opacity") and not from_slider:
            self.spin_opacity.blockSignals(True)
            self.spin_opacity.setValue(op)
            self.spin_opacity.blockSignals(False)
        if hasattr(self, "slider_opacity"):
            self.slider_opacity.blockSignals(True)
            self.slider_opacity.setValue(int(round(op * 100)))
            self.slider_opacity.blockSignals(False)
        if from_slider and hasattr(self, "spin_opacity"):
            self.spin_opacity.blockSignals(True)
            self.spin_opacity.setValue(op)
            self.spin_opacity.blockSignals(False)

    def _apply_toolbar_opacity(self, value: float) -> None:
        """Standard-Deckkraft setzen; bei Auswahl alle ausgewählten Ann. aktualisieren."""
        self._default_opacity = max(0.05, min(1.0, float(value)))
        set_ann_default_opacity(self._default_opacity)
        ids = list(self._selected_ann_ids) if self._selected_ann_ids else (
            [self._selected_ann_id] if self._selected_ann_id else []
        )
        ids = [i for i in ids if i]
        if self.store and ids:
            n = self.store.set_opacities(ids, self._default_opacity)
            if n > 0:
                try:
                    self.store.save(force=True)
                except Exception:
                    pass
                self.refresh()
                self.annotations_changed.emit()
                self.status.emit(
                    f"Deckkraft {self._default_opacity:.2f} für {n} Annotation(en)"
                )

    def _on_default_opacity_changed(self, value: float):
        self._sync_opacity_controls(value, from_slider=False)
        self._apply_toolbar_opacity(value)

    def _on_opacity_slider_changed(self, percent: int):
        value = max(0.05, min(1.0, float(percent) / 100.0))
        self._sync_opacity_controls(value, from_slider=True)
        self._apply_toolbar_opacity(value)

    def set_grayscale(self, enabled: bool):
        enabled = bool(enabled)
        changed = self._grayscale != enabled
        self._grayscale = enabled
        set_pdf_grayscale(enabled)
        if hasattr(self, "btn_grayscale"):
            self.btn_grayscale.blockSignals(True)
            self.btn_grayscale.setChecked(enabled)
            self.btn_grayscale.blockSignals(False)
        if changed and self.pdf_path:
            from ild_pdf.render import clear_render_cache

            clear_render_cache(self.pdf_path)
            self.refresh()
        if changed:
            self.grayscale_changed.emit(enabled)
            self.status.emit("Graustufen an" if enabled else "Graustufen aus")

    def grayscale_enabled(self) -> bool:
        return bool(self._grayscale)

    def set_night_mode(self, enabled: bool):
        """Dunkle Invert-Ansicht — nur Viewer/Thumbs, nie Export/Speichern."""
        enabled = bool(enabled)
        changed = self._night_mode != enabled
        self._night_mode = enabled
        set_pdf_night_mode(enabled)
        if hasattr(self, "btn_night"):
            self.btn_night.blockSignals(True)
            self.btn_night.setChecked(enabled)
            self.btn_night.blockSignals(False)
        if changed and self.pdf_path:
            from ild_pdf.render import clear_render_cache

            clear_render_cache(self.pdf_path)
            self.refresh()
        if changed:
            self.night_mode_changed.emit(enabled)
            self.status.emit("Nachtmodus an" if enabled else "Nachtmodus aus")

    def night_mode_enabled(self) -> bool:
        return bool(self._night_mode)

    def set_two_page_spread(self, enabled: bool):
        """Zwei-Seiten-Ansicht (Spread): aktuelle + nächste Seite nebeneinander."""
        enabled = bool(enabled)
        if enabled and self._continuous_scroll:
            self.set_continuous_scroll(False)
        changed = self._two_page_spread != enabled
        self._two_page_spread = enabled
        set_pdf_two_page_spread(enabled)
        if hasattr(self, "btn_spread"):
            self.btn_spread.blockSignals(True)
            self.btn_spread.setChecked(enabled)
            self.btn_spread.blockSignals(False)
        if not enabled:
            self._spread_left_width = 0.0
        if changed and self.pdf_path:
            self.refresh()
        if changed:
            self.two_page_spread_changed.emit(enabled)
            self.status.emit(
                "Zwei-Seiten-Ansicht an" if enabled else "Zwei-Seiten-Ansicht aus"
            )

    def two_page_spread_enabled(self) -> bool:
        return bool(self._two_page_spread)

    def set_continuous_scroll(self, enabled: bool):
        """Continuous Scroll: Seiten untereinander statt Einzelseite."""
        enabled = bool(enabled)
        if enabled and self._two_page_spread:
            self.set_two_page_spread(False)
        changed = self._continuous_scroll != enabled
        self._continuous_scroll = enabled
        set_pdf_continuous_scroll(enabled)
        if hasattr(self, "btn_continuous"):
            self.btn_continuous.blockSignals(True)
            self.btn_continuous.setChecked(enabled)
            self.btn_continuous.blockSignals(False)
        if not enabled:
            self._continuous_offsets = []
        if changed and self.pdf_path:
            self.refresh()
            if enabled:
                self._scroll_to_continuous_page(self.page_index)
        if changed:
            self.continuous_scroll_changed.emit(enabled)
            self.status.emit(
                "Continuous Scroll an" if enabled else "Continuous Scroll aus"
            )

    def continuous_scroll_enabled(self) -> bool:
        return bool(self._continuous_scroll)

    def page_label(self, page_index: int | None = None) -> str:
        """Seitenlabel der Seite ('' wenn keines / Index ungültig)."""
        idx = self.page_index if page_index is None else int(page_index)
        labels = getattr(self, "_page_labels", None) or []
        if 0 <= idx < len(labels):
            return str(labels[idx] or "")
        return ""

    def has_page_labels(self) -> bool:
        """True wenn mindestens ein nicht-leeres PDF-Seitenlabel vorhanden."""
        return any(bool(x) for x in (getattr(self, "_page_labels", None) or []))

    def _reload_page_labels(self) -> None:
        """PageLabels aus dem geöffneten PDF laden (Cache)."""
        self._page_labels = []
        if not self.pdf_path or self.page_count <= 0:
            return
        try:
            from ild_pdf import PdfDocument

            with PdfDocument(self.pdf_path, password=self.password) as doc:
                self._page_labels = list(doc.page_labels())
        except Exception:
            self._page_labels = [""] * int(self.page_count or 0)

    def format_page_label_text(
        self,
        page_index: int | None = None,
        *,
        suffix: str = "",
        range_end: int | None = None,
    ) -> str:
        """Anzeigetext für Toolbar-Seitenzeile inkl. optionalem Label."""
        idx = self.page_index if page_index is None else int(page_index)
        total = int(self.page_count or 0)
        if range_end is not None and int(range_end) != idx:
            left = self.page_label(idx)
            right = self.page_label(int(range_end))
            n0, n1 = idx + 1, int(range_end) + 1
            if left or right:
                lpart = left or str(n0)
                rpart = right or str(n1)
                base = f"{lpart}–{rpart} ({n0}–{n1}/{total})"
            else:
                base = f"{n0}–{n1} / {total}"
        else:
            lab = self.page_label(idx)
            n = idx + 1
            if lab:
                base = f"{lab} ({n}/{total})"
            else:
                base = f"{n} / {total}"
        if suffix:
            return f"{base}{suffix}"
        return base

    def _continuous_page_range(self) -> tuple[int, int]:
        """(start, end) exklusiv end — Fenster um aktuelle Seite."""
        n = int(self.page_count or 0)
        if n <= 0:
            return 0, 0
        if n <= CONTINUOUS_MAX_PAGES:
            return 0, n
        half = CONTINUOUS_MAX_PAGES // 2
        start = max(0, int(self.page_index) - half // 2)
        end = min(n, start + CONTINUOUS_MAX_PAGES)
        start = max(0, end - CONTINUOUS_MAX_PAGES)
        return start, end

    def _spread_resolve(self, x: float, y: float) -> tuple[int, float, float]:
        """Display-Koordinaten → (page_index, lokale_x, lokale_y)."""
        if self._continuous_scroll and self._continuous_offsets:
            gap = float(self._continuous_gap)
            for page, y0, h in self._continuous_offsets:
                if y < y0 + h + gap:
                    return page, x, max(0.0, y - y0)
            page, y0, h = self._continuous_offsets[-1]
            return page, x, max(0.0, y - y0)
        if (
            self._two_page_spread
            and self._spread_left_width > 0
            and self.page_index + 1 < self.page_count
            and x >= self._spread_left_width + self._spread_gap
        ):
            return (
                self.page_index + 1,
                x - self._spread_left_width - self._spread_gap,
                y,
            )
        return self.page_index, x, y

    def _on_continuous_scroll(self, value: int):
        """Aktuelle Seite aus Viewport-Mitte ableiten (ohne re-render)."""
        if (
            self._continuous_scroll_syncing
            or not self._continuous_scroll
            or not self._continuous_offsets
        ):
            return
        vp = self.scroll.viewport()
        center_y = float(value) + float(vp.height()) * 0.35
        new_page = self.page_index
        for page, y0, h in self._continuous_offsets:
            if y0 <= center_y < y0 + h + self._continuous_gap:
                new_page = page
                break
        else:
            if self._continuous_offsets:
                new_page = self._continuous_offsets[-1][0]
        if new_page != self.page_index:
            self.page_index = new_page
            self.lbl_page.setText(
                self.format_page_label_text(suffix=" (Scroll)")
            )
            self.page_changed.emit(self.page_index)

    def _scroll_to_continuous_page(self, page_index: int):
        """Viewport auf Seite in Continuous-Ansicht setzen."""
        if not self._continuous_offsets:
            return
        target = None
        for page, y0, _h in self._continuous_offsets:
            if page == page_index:
                target = y0
                break
        if target is None:
            return
        self._continuous_scroll_syncing = True
        try:
            bar = self.scroll.verticalScrollBar()
            bar.setValue(int(max(0, target - 8)))
        finally:
            self._continuous_scroll_syncing = False

    def set_annotations_visible(self, visible: bool):
        """Annotation-Layer ein-/ausblenden (nur Darstellung)."""
        enabled = bool(visible)
        changed = self._annotations_visible != enabled
        self._annotations_visible = enabled
        set_annotations_visible(enabled)
        if hasattr(self, "btn_ann_layer"):
            self.btn_ann_layer.blockSignals(True)
            self.btn_ann_layer.setChecked(enabled)
            self.btn_ann_layer.blockSignals(False)
        self.canvas.set_annotations_visible(enabled)
        if changed:
            self.annotations_layer_changed.emit(enabled)
            self.status.emit(
                "Annotationen sichtbar" if enabled else "Annotation-Layer ausgeblendet"
            )

    def annotations_visible(self) -> bool:
        return bool(self._annotations_visible)

    def set_annotations_locked(self, locked: bool):
        """Annotationen sperren — nicht per Drag verschiebbar."""
        enabled = bool(locked)
        changed = self._annotations_locked != enabled
        self._annotations_locked = enabled
        set_annotations_locked(enabled)
        if hasattr(self, "btn_ann_lock"):
            self.btn_ann_lock.blockSignals(True)
            self.btn_ann_lock.setChecked(enabled)
            self.btn_ann_lock.blockSignals(False)
        self.canvas.set_annotations_locked(enabled)
        if changed:
            self.annotations_lock_changed.emit(enabled)
            self.status.emit(
                "Annotationen gesperrt (nicht verschiebbar)"
                if enabled
                else "Annotationen entsperrt — Auswahl + Ziehen verschiebt"
            )

    def annotations_locked(self) -> bool:
        return bool(self._annotations_locked)

    def set_show_page_boxes(self, enabled: bool):
        """MediaBox/CropBox-Rahmen als Overlay ein-/ausblenden."""
        on = bool(enabled)
        changed = self._show_page_boxes != on
        self._show_page_boxes = on
        set_show_page_boxes(on)
        if hasattr(self, "btn_page_boxes"):
            self.btn_page_boxes.blockSignals(True)
            self.btn_page_boxes.setChecked(on)
            self.btn_page_boxes.blockSignals(False)
        self.canvas.set_show_page_boxes(on)
        if on:
            self._update_page_box_overlay()
        else:
            self.canvas.clear_page_box_rects()
        if changed:
            self.page_boxes_changed.emit(on)
            self.status.emit(
                "Seitenrahmen/CropBox-Overlay an" if on else "Seitenrahmen-Overlay aus"
            )

    def show_page_boxes(self) -> bool:
        return bool(self._show_page_boxes)

    def set_show_printer_marks(self, enabled: bool):
        """Seitenrand-Druckermarken als Overlay ein-/ausblenden."""
        on = bool(enabled)
        changed = self._show_printer_marks != on
        self._show_printer_marks = on
        set_show_printer_marks(on)
        if hasattr(self, "btn_printer_marks"):
            self.btn_printer_marks.blockSignals(True)
            self.btn_printer_marks.setChecked(on)
            self.btn_printer_marks.blockSignals(False)
        self.canvas.set_show_printer_marks(on)
        if on:
            self._update_printer_marks_overlay()
        else:
            self.canvas.clear_printer_marks_rect()
        if changed:
            self.printer_marks_changed.emit(on)
            self.status.emit(
                "Druckermarken-Overlay an" if on else "Druckermarken-Overlay aus"
            )

    def show_printer_marks(self) -> bool:
        return bool(self._show_printer_marks)

    @staticmethod
    def _pdf_box_to_pixel_rect(
        box: tuple[float, float, float, float],
        page_h_pt: float,
        scale: float,
    ) -> tuple[float, float, float, float]:
        """PDF-Box (l,b,r,t) → Pixel-Rect (x,y,w,h), Y von oben."""
        left, bottom, right, top = box
        s = max(float(scale), 0.01)
        x0 = float(left) * s
        x1 = float(right) * s
        y0 = (float(page_h_pt) - float(top)) * s
        y1 = (float(page_h_pt) - float(bottom)) * s
        return x0, y0, max(x1 - x0, 1.0), max(y1 - y0, 1.0)

    def _update_page_box_overlay(self):
        if not self.pdf_path or not self._show_page_boxes:
            self.canvas.clear_page_box_rects()
            return
        try:
            from ild_pdf.pages import get_page_boxes

            boxes = get_page_boxes(self.pdf_path, self.page_index)
            mb = boxes["mediabox"]
            cb = boxes["cropbox"]
            page_h = float(mb[3] - mb[1]) if mb[3] > mb[1] else float(mb[3])
            media_r = self._pdf_box_to_pixel_rect(mb, page_h, self.scale)
            crop_r = self._pdf_box_to_pixel_rect(cb, page_h, self.scale)
            # Crop nur zeichnen wenn abweichend
            same = all(abs(a - b) < 0.5 for a, b in zip(media_r, crop_r))
            self.canvas.set_page_box_rects(media_r, None if same else crop_r)
        except Exception:
            self.canvas.clear_page_box_rects()

    def _update_printer_marks_overlay(self):
        if not self.pdf_path or not self._show_printer_marks:
            self.canvas.clear_printer_marks_rect()
            return
        try:
            from ild_pdf.pages import get_page_boxes

            boxes = get_page_boxes(self.pdf_path, self.page_index)
            mb = boxes["mediabox"]
            cb = boxes["cropbox"]
            page_h = float(mb[3] - mb[1]) if mb[3] > mb[1] else float(mb[3])
            # Marken am CropBox (sonst MediaBox)
            target = cb if cb else mb
            rect = self._pdf_box_to_pixel_rect(target, page_h, self.scale)
            self.canvas.set_printer_marks_rect(rect)
        except Exception:
            self.canvas.clear_printer_marks_rect()

    def _on_annotations_moved(self, ids: list, dx: float, dy: float):
        if not self.store or self._annotations_locked:
            self.refresh()
            return
        n = self.store.move_by(ids, dx, dy)
        if n:
            try:
                self.store.save(force=True)
            except Exception as e:
                QMessageBox.warning(self, "Annotation verschieben", str(e))
            self.refresh()
            self.annotations_changed.emit()
            self.status.emit(f"{n} Annotation(en) verschoben")
        else:
            self.refresh()

    def apply_settings_colors(self):
        self._highlight_color = get_ann_highlight_color()
        self._pen_color = get_ann_pen_color()
        self._note_color = get_ann_note_color()
        self._style_color_btn(self.btn_hl_color, self._highlight_color)
        self._style_color_btn(self.btn_pen_color, self._pen_color)
        if hasattr(self, "btn_note_color"):
            self._style_color_btn(self.btn_note_color, self._note_color)
        self._refresh_preset_btns()
        self._default_opacity = get_ann_default_opacity()
        self._sync_opacity_controls(self._default_opacity)
        self._grayscale = get_pdf_grayscale()
        if hasattr(self, "btn_grayscale"):
            self.btn_grayscale.blockSignals(True)
            self.btn_grayscale.setChecked(self._grayscale)
            self.btn_grayscale.blockSignals(False)
        self._night_mode = get_pdf_night_mode()
        if hasattr(self, "btn_night"):
            self.btn_night.blockSignals(True)
            self.btn_night.setChecked(self._night_mode)
            self.btn_night.blockSignals(False)
        self._two_page_spread = get_pdf_two_page_spread()
        self._continuous_scroll = get_pdf_continuous_scroll()
        if self._continuous_scroll and self._two_page_spread:
            self._two_page_spread = False
            set_pdf_two_page_spread(False)
        if hasattr(self, "btn_spread"):
            self.btn_spread.blockSignals(True)
            self.btn_spread.setChecked(self._two_page_spread)
            self.btn_spread.blockSignals(False)
        if hasattr(self, "btn_continuous"):
            self.btn_continuous.blockSignals(True)
            self.btn_continuous.setChecked(self._continuous_scroll)
            self.btn_continuous.blockSignals(False)
        self._annotations_visible = get_annotations_visible()
        if hasattr(self, "btn_ann_layer"):
            self.btn_ann_layer.blockSignals(True)
            self.btn_ann_layer.setChecked(self._annotations_visible)
            self.btn_ann_layer.blockSignals(False)
        self.canvas.set_annotations_visible(self._annotations_visible)
        self._annotations_locked = get_annotations_locked()
        if hasattr(self, "btn_ann_lock"):
            self.btn_ann_lock.blockSignals(True)
            self.btn_ann_lock.setChecked(self._annotations_locked)
            self.btn_ann_lock.blockSignals(False)
        self.canvas.set_annotations_locked(self._annotations_locked)
        self._show_page_boxes = get_show_page_boxes()
        if hasattr(self, "btn_page_boxes"):
            self.btn_page_boxes.blockSignals(True)
            self.btn_page_boxes.setChecked(self._show_page_boxes)
            self.btn_page_boxes.blockSignals(False)
        self.canvas.set_show_page_boxes(self._show_page_boxes)
        if self._show_page_boxes:
            self._update_page_box_overlay()
        else:
            self.canvas.clear_page_box_rects()
        self._show_printer_marks = get_show_printer_marks()
        if hasattr(self, "btn_printer_marks"):
            self.btn_printer_marks.blockSignals(True)
            self.btn_printer_marks.setChecked(self._show_printer_marks)
            self.btn_printer_marks.blockSignals(False)
        self.canvas.set_show_printer_marks(self._show_printer_marks)
        if self._show_printer_marks:
            self._update_printer_marks_overlay()
        else:
            self.canvas.clear_printer_marks_rect()
        if self.pdf_path:
            self.refresh()

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

    def _set_tool(self, tool: AnnotationType | None):
        self.tool = tool
        self._pending_callout_anchor = None
        self._pending_callout_page = self.page_index
        if tool is None:
            want = "Auswahl"
            for b in self._tool_buttons:
                b.setChecked(b.text() == want)
            self.canvas.set_drag_tool(None, select_mode=True)
            self.status.emit("Werkzeug: Auswahl — Text aufziehen + Ctrl+C kopieren; Annotation anklicken")
            return
        want = self._tool_label(tool)
        for b in self._tool_buttons:
            b.setChecked(b.text() == want)
        self.canvas.set_drag_tool(
            tool if tool in DRAG_TYPES else None, select_mode=False
        )
        if tool == AnnotationType.REDACTION:
            n = self.redaction_count()
            self.status.emit(
                f"Werkzeug: Schwärzen — Rechteck ziehen · {n} offen · "
                "PDF → Schwärzung einbrennen"
            )
        else:
            self.status.emit(f"Werkzeug: {tool.value}")

    def _on_annotation_selected(self, ann_id: str):
        self._selected_ann_id = ann_id or None
        self._selected_ann_ids = {self._selected_ann_id} if self._selected_ann_id else set()
        self.canvas.set_selected_id(self._selected_ann_id)
        if self._selected_ann_id and self.store:
            ann = self.store.get(self._selected_ann_id)
            if ann:
                try:
                    op = float(getattr(ann, "opacity", self._default_opacity) or self._default_opacity)
                except (TypeError, ValueError):
                    op = self._default_opacity
                self._sync_opacity_controls(op)
                self.status.emit(f"Auswahl: {ann.type.value} (S. {ann.page + 1})")
            else:
                self.status.emit("Auswahl aufgehoben")
        else:
            self.status.emit("Auswahl aufgehoben")

    def select_all_annotations_on_page(self) -> int:
        """Alle Annotationen der aktuellen Seite auswählen. Rückgabe: Anzahl."""
        if not self.store:
            self.status.emit("Keine Annotationen")
            return 0
        ids = [a.id for a in self.store.for_page(self.page_index)]
        self._selected_ann_ids = set(ids)
        self._selected_ann_id = ids[0] if ids else None
        self.canvas.set_selected_ids(ids)
        n = len(ids)
        if n:
            self.status.emit(f"{n} Annotation(en) auf Seite {self.page_index + 1} ausgewählt")
        else:
            self.status.emit(f"Keine Annotationen auf Seite {self.page_index + 1}")
        return n

    def delete_annotation(self) -> bool:
        """Löscht ausgewählte Annotation(en), sonst die letzte auf der aktuellen Seite (bzw. global)."""
        if not self.store:
            self.status.emit("Keine Annotationen")
            return False
        removed: list[str] = []
        targets = list(self._selected_ann_ids) if self._selected_ann_ids else (
            [self._selected_ann_id] if self._selected_ann_id else []
        )
        for aid in targets:
            if aid and self.store.get(aid) and self.store.remove(aid):
                removed.append(aid)
        if not removed:
            target = self.store.remove_last(page=self.page_index)
            if target is None:
                target = self.store.remove_last(page=None)
            if target is not None:
                removed.append(target.id)
        if not removed:
            self.status.emit("Keine Annotation zum Löschen")
            return False
        self._selected_ann_id = None
        self._selected_ann_ids = set()
        self.canvas.set_selected_id(None)
        try:
            self.store.save(force=True)
        except Exception as e:
            QMessageBox.warning(self, "Annotation löschen", str(e))
            return False
        self.refresh()
        self.annotations_changed.emit()
        if len(removed) > 1:
            self.status.emit(f"{len(removed)} Annotationen gelöscht")
        else:
            self.status.emit("Annotation gelöscht")
        return True

    def clear_annotation_selection(self):
        self._selected_ann_id = None
        self._selected_ann_ids = set()
        self.canvas.set_selected_id(None)

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
            self.clear_page_ops_undo()
            from ild_pdf import PdfDocument

            with PdfDocument(self.pdf_path, password=self.password) as doc:
                self.page_count = len(doc)
            self._reload_page_labels()
            self.page_index = 0
            self._pending_callout_anchor = None
            self._pending_scale = None
            self._zoom_timer.stop()
            self.scale = get_default_zoom_scale()
            self.clear_search_highlights()
            self.refresh()
            self.annotations_changed.emit()
            self.page_changed.emit(self.page_index)
            self.zoom_changed.emit(self.scale)
            self.document_changed.emit()
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
            from copy import copy

            from PIL import Image

            from ild_pdf.limits import clamp_render_scale
            from ild_pdf import PdfDocument
            from ild_pdf.links import UriLink

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
                grayscale=self._grayscale,
                invert=self._night_mode,
            )
            anns = list(self.store.for_page(self.page_index) if self.store else [])
            links: list = []
            try:
                links = list(
                    list_page_uri_links(
                        self.pdf_path,
                        self.page_index,
                        scale=self.scale,
                        password=self.password,
                    )
                )
            except Exception:
                links = []

            self._spread_left_width = 0.0
            self._continuous_offsets = []
            facing = self.page_index + 1
            use_continuous = bool(self._continuous_scroll)
            use_spread = (
                (not use_continuous)
                and self._two_page_spread
                and facing < self.page_count
            )
            if use_continuous:
                from ild_pdf.limits import MAX_RENDER_PIXELS

                gap = int(self._continuous_gap)
                start, end = self._continuous_page_range()
                pages_imgs: list[tuple[int, object]] = []
                for pi in range(start, end):
                    if pi == self.page_index:
                        pages_imgs.append((pi, img))
                    else:
                        try:
                            pi_img = render_page(
                                self.pdf_path,
                                pi,
                                scale=self.scale,
                                password=self.password,
                                grayscale=self._grayscale,
                                invert=self._night_mode,
                            )
                        except Exception:
                            continue
                        pages_imgs.append((pi, pi_img))
                if not pages_imgs:
                    pages_imgs = [(self.page_index, img)]
                max_w = max(im.size[0] for _, im in pages_imgs)
                total_h = sum(im.size[1] for _, im in pages_imgs) + gap * max(
                    0, len(pages_imgs) - 1
                )
                if max_w * total_h > MAX_RENDER_PIXELS:
                    self.status.emit(
                        "Continuous Scroll: zu groß — Zoom verringern oder weniger Seiten"
                    )
                    self.lbl_page.setText(self.format_page_label_text())
                    self._continuous_offsets = []
                else:
                    combined = Image.new(
                        "RGBA", (max_w, total_h), (240, 240, 240, 255)
                    )
                    y_off = 0.0
                    all_anns: list = []
                    all_links: list = []
                    for pi, pimg in pages_imgs:
                        if pimg.mode != "RGBA":
                            pimg = pimg.convert("RGBA")
                        combined.paste(pimg, (0, int(y_off)))
                        ph = float(pimg.size[1])
                        self._continuous_offsets.append((pi, y_off, ph))
                        if self.store:
                            for ann in self.store.for_page(pi):
                                disp = copy(ann)
                                disp.y = float(ann.y) + y_off
                                if ann.callout_x or ann.callout_y:
                                    disp.callout_y = float(ann.callout_y) + y_off
                                all_anns.append(disp)
                        try:
                            page_links = list_page_uri_links(
                                self.pdf_path,
                                pi,
                                scale=self.scale,
                                password=self.password,
                            )
                            for link in page_links:
                                all_links.append(
                                    UriLink(
                                        page=link.page,
                                        x=link.x,
                                        y=link.y + y_off,
                                        width=link.width,
                                        height=link.height,
                                        uri=link.uri,
                                    )
                                )
                        except Exception:
                            pass
                        y_off += ph + gap
                    img = combined
                    anns = all_anns
                    links = all_links
                    trunc = ""
                    if end - start < self.page_count:
                        trunc = f" · {start + 1}–{end}"
                    self.lbl_page.setText(
                        self.format_page_label_text(suffix=f" (Scroll{trunc})")
                    )
            elif use_spread:
                gap = int(self._spread_gap)
                img2 = render_page(
                    self.pdf_path,
                    facing,
                    scale=self.scale,
                    password=self.password,
                    grayscale=self._grayscale,
                    invert=self._night_mode,
                )
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
                if img2.mode != "RGBA":
                    img2 = img2.convert("RGBA")
                left_w, left_h = img.size
                right_w, right_h = img2.size
                self._spread_left_width = float(left_w)
                combo_w = left_w + gap + right_w
                combo_h = max(left_h, right_h)
                combined = Image.new("RGBA", (combo_w, combo_h), (240, 240, 240, 255))
                combined.paste(img, (0, 0))
                combined.paste(img2, (left_w + gap, 0))
                img = combined
                ox = float(left_w + gap)
                if self.store:
                    for ann in self.store.for_page(facing):
                        disp = copy(ann)
                        disp.x = float(ann.x) + ox
                        if ann.callout_x or ann.callout_y:
                            disp.callout_x = float(ann.callout_x) + ox
                        anns.append(disp)
                try:
                    right_links = list_page_uri_links(
                        self.pdf_path,
                        facing,
                        scale=self.scale,
                        password=self.password,
                    )
                    for link in right_links:
                        links.append(
                            UriLink(
                                page=link.page,
                                x=link.x + ox,
                                y=link.y,
                                width=link.width,
                                height=link.height,
                                uri=link.uri,
                            )
                        )
                except Exception:
                    pass
                self.lbl_page.setText(
                    self.format_page_label_text(range_end=facing)
                )
            else:
                self.lbl_page.setText(self.format_page_label_text())

            self.canvas.set_page_image(img, anns, scale=self.scale)
            self.canvas.set_uri_links(links)
            self._update_page_box_overlay()
            self._update_printer_marks_overlay()
            if self._search_rects:
                self.canvas.set_search_highlights(self._search_rects, self._search_index)
            self.lbl_zoom.setText(f"{int(round(self.scale * 100))}%")
            dirty = " *" if self.store and self.store.dirty else ""
            self.status.emit(f"PDF: {self.pdf_path.name}{dirty}")
            self._refresh_fav_btn()
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
            old = self.page_index
            self.page_index = page_index
            if self._search_query:
                self._rebuild_search_rects(keep_index=False)
            need_refresh = True
            if self._continuous_scroll and self._continuous_offsets:
                in_window = any(p == page_index for p, _, _ in self._continuous_offsets)
                # Fenster neu, wenn Seite außerhalb oder Range sich ändern würde
                start, end = self._continuous_page_range()
                if in_window and start <= old < end and start <= page_index < end:
                    # Nur scrollen, wenn Range gleich bleibt
                    old_start, old_end = self._continuous_offsets[0][0], self._continuous_offsets[-1][0] + 1
                    if old_start == start and old_end == end:
                        need_refresh = False
                        self.lbl_page.setText(
                            self.format_page_label_text(suffix=" (Scroll)")
                        )
                        self._scroll_to_continuous_page(page_index)
            if need_refresh:
                self.refresh()
                if self._continuous_scroll:
                    self._scroll_to_continuous_page(page_index)
            self.page_changed.emit(self.page_index)

    def prev_page(self):
        if self.page_index <= 0:
            return
        if self._continuous_scroll:
            self.goto_page(self.page_index - 1)
            return
        step = 2 if self._two_page_spread else 1
        self.page_index = max(0, self.page_index - step)
        if self._search_query:
            self._rebuild_search_rects(keep_index=False)
        self.refresh()
        self.page_changed.emit(self.page_index)

    def next_page(self):
        if self.page_index + 1 >= self.page_count:
            return
        if self._continuous_scroll:
            self.goto_page(self.page_index + 1)
            return
        step = 2 if self._two_page_spread else 1
        target = self.page_index + step
        if target >= self.page_count:
            target = self.page_index + 1
        if target >= self.page_count:
            return
        self.page_index = target
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
        self.zoom_changed.emit(scale if immediate else scale)
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
        self.zoom_changed.emit(self.scale)
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
                    self._reload_page_labels()
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

    def fit_height(self):
        """Seitenhöhe an Viewport anpassen."""
        if not self.pdf_path:
            return
        try:
            from ild_pdf import PdfDocument

            with PdfDocument(self.pdf_path, password=self.password) as doc:
                _pw, ph = doc.page_size(self.page_index)
            _vw, vh = self._viewport_size()
            if ph <= 0:
                return
            scale = vh / ph
            self.set_scale(scale, immediate=True)
            self.status.emit(f"Höhe einpassen ({int(round(scale * 100))}%)")
        except Exception as e:
            QMessageBox.warning(self, "Zoom", str(e))

    def undo_annotation(self) -> bool:
        # Zuerst Seiten-Ops (Löschen/Drehen), danach Annotation-History
        if self.can_undo_page_op():
            return self.undo_page_op()
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

    def can_undo_page_op(self) -> bool:
        return bool(getattr(self, "_page_ops_undo", None))

    def clear_page_ops_undo(self) -> None:
        self._page_ops_undo = []

    def page_ops_history_items(self) -> list[dict]:
        """
        Lesbare Historie des Seiten-Undo-Stacks (älteste zuerst).
        Jeder Eintrag: stack_index, kind, page (0-basiert), label.
        """
        stack = list(getattr(self, "_page_ops_undo", None) or [])
        items: list[dict] = []
        for i, entry in enumerate(stack):
            kind = entry.get("kind") or "?"
            idx = int(entry.get("index", 0))
            page_h = idx + 1
            if kind == "delete":
                label = f"Seite {page_h} gelöscht — wiederherstellbar"
            elif kind == "rotate":
                deg = int(entry.get("degrees", 90))
                label = f"Seite {page_h} gedreht ({deg:+d}°) — rückgängig"
            else:
                label = f"Aktion „{kind}“ (S. {page_h})"
            items.append(
                {
                    "stack_index": i,
                    "kind": kind,
                    "page": idx,
                    "label": label,
                    "entry": entry,
                }
            )
        return items

    def restore_page_op_at(self, stack_index: int) -> bool:
        """
        Ausgewählten Historie-Eintrag wiederherstellen:
        Undo vom neuesten Eintrag bis einschließlich dem gewählten.
        """
        stack = getattr(self, "_page_ops_undo", None) or []
        if not stack:
            self.status.emit("Seiten-Historie leer")
            return False
        target = max(0, min(int(stack_index), len(stack) - 1))
        times = len(stack) - target
        ok_any = False
        for _ in range(times):
            if not self.undo_page_op():
                break
            ok_any = True
        if ok_any:
            self.status.emit("Seiten-Historie: Eintrag wiederhergestellt")
        return ok_any

    def show_page_ops_history(self) -> bool:
        """Dialog: Seiten-Undo-Historie mit Wiederherstellen."""
        from PySide6.QtWidgets import (
            QDialog,
            QHBoxLayout,
            QLabel,
            QListWidget,
            QListWidgetItem,
            QPushButton,
            QVBoxLayout,
        )

        items = self.page_ops_history_items()
        dlg = QDialog(self)
        dlg.setWindowTitle("Seiten-Historie (Undo)")
        dlg.resize(420, 320)
        layout = QVBoxLayout(dlg)
        layout.addWidget(
            QLabel(
                "Gelöschte oder gedrehte Seiten aus dem Undo-Stack.\n"
                "Neueste Einträge unten — „Wiederherstellen“ macht bis zum gewählten Eintrag rückgängig."
            )
        )
        lst = QListWidget()
        for it in items:
            row = QListWidgetItem(it["label"])
            row.setData(Qt.UserRole, int(it["stack_index"]))
            lst.addItem(row)
        if items:
            lst.setCurrentRow(len(items) - 1)
        layout.addWidget(lst)
        if not items:
            layout.addWidget(QLabel("Keine Seiten-Aktionen zum Rückgängigmachen."))

        btns = QHBoxLayout()
        btn_restore = QPushButton("Wiederherstellen")
        btn_restore.setEnabled(bool(items))
        btn_restore.setDefault(True)
        btn_close = QPushButton("Schließen")
        btns.addWidget(btn_restore)
        btns.addStretch()
        btns.addWidget(btn_close)
        layout.addLayout(btns)

        restored = {"ok": False}

        def _do_restore():
            cur = lst.currentItem()
            if cur is None:
                return
            idx = cur.data(Qt.UserRole)
            if idx is None:
                return
            if self.restore_page_op_at(int(idx)):
                restored["ok"] = True
                lst.clear()
                fresh = self.page_ops_history_items()
                for it2 in fresh:
                    row2 = QListWidgetItem(it2["label"])
                    row2.setData(Qt.UserRole, int(it2["stack_index"]))
                    lst.addItem(row2)
                btn_restore.setEnabled(bool(fresh))
                if not fresh:
                    dlg.accept()

        btn_restore.clicked.connect(_do_restore)
        lst.itemDoubleClicked.connect(lambda _item: _do_restore())
        btn_close.clicked.connect(dlg.reject)
        dlg.exec()
        return bool(restored["ok"])

    def _refresh_fav_btn(self) -> None:
        """Toolbar-Stern: Zustand der aktuellen Seite."""
        btn = getattr(self, "btn_fav", None)
        if btn is None:
            return
        is_fav = False
        if self.store is not None and self.pdf_path:
            try:
                is_fav = self.store.is_page_favorite(self.page_index)
            except Exception:
                is_fav = False
        btn.blockSignals(True)
        btn.setChecked(is_fav)
        btn.blockSignals(False)
        n = 0
        if self.store is not None:
            try:
                n = len(self.store.list_page_favorites())
            except Exception:
                n = 0
        btn.setToolTip(
            f"{'Favorit entfernen' if is_fav else 'Seite als Favorit markieren'} "
            f"(Ctrl+Shift+F) — {n} Favorit(en)"
        )

    def list_page_favorites(self) -> list[int]:
        if not self.store:
            return []
        return [
            p
            for p in self.store.list_page_favorites()
            if 0 <= int(p) < int(self.page_count or 0)
        ]

    def toggle_page_favorite(self) -> bool:
        """Aktuelle PDF-Seite als Favorit markieren/entfernen (Sidecar-Meta)."""
        if not self.store or not self.pdf_path:
            self.status.emit("Kein PDF geladen")
            return False
        now_fav = self.store.toggle_page_favorite(self.page_index)
        try:
            self.store.save(force=True)
        except Exception as e:
            QMessageBox.warning(self, "Seiten-Favorit", str(e))
            return False
        self._refresh_fav_btn()
        page_h = self.page_index + 1
        self.status.emit(
            f"Seite {page_h} als Favorit markiert"
            if now_fav
            else f"Seite {page_h} aus Favoriten entfernt"
        )
        self.page_favorites_changed.emit()
        return now_fav

    def show_page_favorites(self) -> bool:
        """Dialog: Favoriten-Seiten auflisten und springen."""
        from PySide6.QtWidgets import (
            QDialog,
            QHBoxLayout,
            QLabel,
            QListWidget,
            QListWidgetItem,
            QPushButton,
            QVBoxLayout,
        )

        if not self.store or not self.pdf_path:
            QMessageBox.information(self, "Favoriten", "Kein PDF geladen.")
            return False
        favs = self.list_page_favorites()
        dlg = QDialog(self)
        dlg.setWindowTitle("Seiten-Favoriten")
        dlg.resize(360, 280)
        layout = QVBoxLayout(dlg)
        layout.addWidget(
            QLabel(
                "Favoriten-Seiten dieses PDFs (schnell springen).\n"
                "★ in der Toolbar markiert die aktuelle Seite."
            )
        )
        lst = QListWidget()
        for i, p in enumerate(favs):
            label = self.page_label(p) if self.has_page_labels() else ""
            text = f"{i + 1}. Seite {p + 1}" + (f" ({label})" if label else "")
            row = QListWidgetItem(text)
            row.setData(Qt.UserRole, int(p))
            lst.addItem(row)
        if favs and 0 <= self.page_index:
            # aktuelle Favoriten-Seite vorselektieren falls vorhanden
            for i, p in enumerate(favs):
                if p == self.page_index:
                    lst.setCurrentRow(i)
                    break
            else:
                lst.setCurrentRow(0)
        layout.addWidget(lst)
        if not favs:
            layout.addWidget(QLabel("Keine Favoriten — aktuelle Seite mit ★ markieren."))

        btns = QHBoxLayout()
        btn_goto = QPushButton("Springen")
        btn_goto.setEnabled(bool(favs))
        btn_goto.setDefault(True)
        btn_toggle = QPushButton("Aktuelle ★ umschalten")
        btn_remove = QPushButton("Entfernen")
        btn_remove.setEnabled(bool(favs))
        btn_close = QPushButton("Schließen")
        btns.addWidget(btn_goto)
        btns.addWidget(btn_toggle)
        btns.addWidget(btn_remove)
        btns.addStretch()
        btns.addWidget(btn_close)
        layout.addLayout(btns)

        jumped = {"ok": False}

        def _refresh_list():
            lst.clear()
            fresh = self.list_page_favorites()
            for i2, p2 in enumerate(fresh):
                label2 = self.page_label(p2) if self.has_page_labels() else ""
                text2 = f"{i2 + 1}. Seite {p2 + 1}" + (f" ({label2})" if label2 else "")
                row2 = QListWidgetItem(text2)
                row2.setData(Qt.UserRole, int(p2))
                lst.addItem(row2)
            btn_goto.setEnabled(bool(fresh))
            btn_remove.setEnabled(bool(fresh))
            self._refresh_fav_btn()
            self.page_favorites_changed.emit()

        def _do_goto():
            cur = lst.currentItem()
            if cur is None:
                return
            idx = cur.data(Qt.UserRole)
            if idx is None:
                return
            self.goto_page(int(idx))
            jumped["ok"] = True
            dlg.accept()

        def _do_toggle():
            self.toggle_page_favorite()
            _refresh_list()

        def _do_remove():
            cur = lst.currentItem()
            if cur is None or not self.store:
                return
            idx = cur.data(Qt.UserRole)
            if idx is None:
                return
            favs_now = [p for p in self.store.list_page_favorites() if p != int(idx)]
            self.store.set_page_favorites(favs_now)
            try:
                self.store.save(force=True)
            except Exception as e:
                QMessageBox.warning(self, "Favoriten", str(e))
                return
            _refresh_list()
            self.status.emit(f"Seite {int(idx) + 1} aus Favoriten entfernt")
            self.page_favorites_changed.emit()

        btn_goto.clicked.connect(_do_goto)
        lst.itemDoubleClicked.connect(lambda _item: _do_goto())
        btn_toggle.clicked.connect(_do_toggle)
        btn_remove.clicked.connect(_do_remove)
        btn_close.clicked.connect(dlg.reject)
        dlg.exec()
        return bool(jumped["ok"])

    def recolor_selected_annotations(self) -> int:
        """Batch-Farbe für ausgewählte Annotation(en) ändern."""
        if not self.store:
            self.status.emit("Kein PDF geladen")
            return 0
        ids = list(self._selected_ann_ids) if self._selected_ann_ids else (
            [self._selected_ann_id] if self._selected_ann_id else []
        )
        ids = [i for i in ids if i]
        if not ids:
            self.status.emit("Keine Annotation ausgewählt")
            return 0
        # Startfarbe: erste Auswahl oder aktuelle Highlight-Farbe
        initial = QColor(self._highlight_color or "#FFE066")
        first = self.store.get(ids[0])
        if first and first.color:
            c0 = QColor(first.color)
            if c0.isValid():
                initial = c0
        chosen = QColorDialog.getColor(
            initial,
            self,
            f"Farbe für {len(ids)} Annotation(en)",
        )
        if not chosen.isValid():
            return 0
        color = chosen.name().upper()
        n = self.store.set_colors(ids, color)
        if n <= 0:
            self.status.emit("Farbe nicht geändert")
            return 0
        try:
            self.store.save()
        except Exception as e:
            QMessageBox.warning(self, "Annotation-Farbe", str(e))
            return 0
        self.refresh()
        self.annotations_changed.emit()
        self.status.emit(f"Farbe {color} für {n} Annotation(en)")
        return n

    def set_opacity_selected_annotations(self) -> int:
        """Batch-Deckkraft für ausgewählte Annotation(en) ändern."""
        from PySide6.QtWidgets import QInputDialog

        if not self.store:
            self.status.emit("Kein PDF geladen")
            return 0
        ids = list(self._selected_ann_ids) if self._selected_ann_ids else (
            [self._selected_ann_id] if self._selected_ann_id else []
        )
        ids = [i for i in ids if i]
        if not ids:
            self.status.emit("Keine Annotation ausgewählt")
            return 0
        initial = float(self._default_opacity)
        first = self.store.get(ids[0])
        if first is not None:
            try:
                initial = float(getattr(first, "opacity", initial) or initial)
            except (TypeError, ValueError):
                pass
        initial = max(0.05, min(1.0, initial))
        value, ok = QInputDialog.getDouble(
            self,
            "Deckkraft (Batch)",
            f"Deckkraft für {len(ids)} Annotation(en) (0.05–1.0):",
            initial,
            0.05,
            1.0,
            2,
            step=0.05,
        )
        if not ok:
            return 0
        n = self.store.set_opacities(ids, float(value))
        if n <= 0:
            self.status.emit("Deckkraft nicht geändert")
            return 0
        try:
            # Force-Schreiben: Opacity muss im Sidecar zuverlässig landen
            self.store.save(force=True)
        except Exception as e:
            QMessageBox.warning(self, "Annotation-Deckkraft", str(e))
            return 0
        self.refresh()
        self.annotations_changed.emit()
        self.status.emit(f"Deckkraft {float(value):.2f} für {n} Annotation(en)")
        return n

    def reorder_page_favorites(self, pages: list[int]) -> list[int]:
        """PDF-Favoriten-Reihenfolge aus Sidebar-Drag speichern."""
        if not self.store or not self.pdf_path:
            return []
        cleaned = self.store.reorder_page_favorites(pages)
        try:
            self.store.save(force=True)
        except Exception as e:
            QMessageBox.warning(self, "Favoriten", str(e))
            return []
        self._refresh_fav_btn()
        self.page_favorites_changed.emit()
        self.status.emit(f"Favoriten umsortiert ({len(cleaned)})")
        return cleaned

    def export_page_favorites_json(self) -> bool:
        """Seiten-Favoriten als JSON (ildfav-v1) exportieren."""
        if not self.store or not self.pdf_path:
            QMessageBox.information(self, "Favoriten", "Kein PDF geladen.")
            return False
        from PySide6.QtWidgets import QFileDialog
        from instantlensdoc.ui.file_dialogs import confirm_overwrite_export

        default = str(self.pdf_path.with_suffix(self.pdf_path.suffix + ".favorites.json"))
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Seiten-Favoriten als JSON exportieren",
            default,
            "Favoriten JSON (*.favorites.json *.json);;Alle (*.*)",
        )
        if not path:
            return False
        dest = Path(path)
        if dest.suffix.lower() != ".json":
            dest = dest.with_suffix(".json")
        if not confirm_overwrite_export(dest, self):
            return False
        try:
            saved = self.store.export_page_favorites_json(dest)
            n = len(self.store.list_page_favorites())
            self.status.emit(f"Favoriten exportiert: {saved.name} ({n})")
            return True
        except Exception as e:
            QMessageBox.warning(self, "Favoriten exportieren", str(e))
            return False

    def import_page_favorites_json(self) -> bool:
        """Seiten-Favoriten aus JSON importieren (ersetzen oder zusammenführen)."""
        if not self.store or not self.pdf_path:
            QMessageBox.information(self, "Favoriten", "Kein PDF geladen.")
            return False
        from PySide6.QtWidgets import QFileDialog
        from ild_pdf import FavoritesImportError

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seiten-Favoriten aus JSON importieren",
            str(self.pdf_path.parent),
            "Favoriten JSON (*.favorites.json *.json);;Alle (*.*)",
        )
        if not path:
            return False
        merge = False
        reply = QMessageBox.question(
            self,
            "Favoriten importieren",
            "Bestehende Favoriten behalten und neue anhängen?\n\n"
            "Ja = zusammenführen · Nein = ersetzen · Abbrechen = abbrechen",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Cancel:
            return False
        merge = reply == QMessageBox.Yes
        try:
            favs = self.store.import_page_favorites_json(
                path,
                merge=merge,
                max_page=int(self.page_count or 0) or None,
            )
            self.store.save(force=True)
        except FavoritesImportError as e:
            QMessageBox.warning(self, "Favoriten importieren", str(e))
            return False
        except Exception as e:
            QMessageBox.warning(self, "Favoriten importieren", str(e))
            return False
        self._refresh_fav_btn()
        self.page_favorites_changed.emit()
        mode = "zusammengeführt" if merge else "ersetzt"
        self.status.emit(f"Favoriten {mode}: {len(favs)} Seite(n)")
        return True

    def undo_page_op(self) -> bool:
        """Letzte Seiten-Operation (Löschen oder Drehen) rückgängig."""
        stack = getattr(self, "_page_ops_undo", None)
        if not stack or not self.pdf_path:
            return False
        entry = stack.pop()
        kind = entry.get("kind")
        try:
            from ild_pdf.render import clear_render_cache

            if kind == "delete":
                idx = int(entry["index"])
                insert_page_from_bytes(self.pdf_path, idx, entry["page_bytes"])
                if self.store and self.store.can_undo():
                    self.store.undo()
                if self.store is not None and "page_groups" in entry:
                    self.store._meta["page_groups"] = dict(entry["page_groups"] or {})
                    self.store.dirty = True
                    try:
                        self.store.save(force=True)
                    except Exception:
                        pass
                from ild_pdf import PdfDocument

                with PdfDocument(self.pdf_path, password=self.password) as doc:
                    self.page_count = len(doc)
                self.page_index = min(max(0, idx), max(0, self.page_count - 1))
                clear_render_cache(self.pdf_path)
                self.refresh()
                self.annotations_changed.emit()
                self.page_changed.emit(self.page_index)
                self.document_changed.emit()
                self.status.emit(f"Seite {idx + 1} wiederhergestellt (Undo)")
                return True
            if kind == "rotate":
                idx = int(entry["index"])
                deg = int(entry.get("degrees", 90))
                rotate_page(self.pdf_path, idx, -int(deg))
                clear_render_cache(self.pdf_path)
                if idx != self.page_index:
                    self.page_index = idx
                self.refresh()
                self.document_changed.emit()
                self.status.emit(f"Seitendrehung rückgängig (S. {idx + 1})")
                return True
            self.status.emit("Unbekannte Seiten-Undo-Aktion")
            return False
        except Exception as e:
            QMessageBox.warning(self, "Seiten-Undo", str(e))
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
        from datetime import datetime

        from instantlensdoc.ui.sidebar import ANN_TYPE_LABELS

        def _fmt_ts(iso: str) -> str:
            raw = (iso or "").strip()
            if not raw:
                return ""
            try:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                return dt.astimezone().strftime("%d.%m. %H:%M")
            except Exception:
                return raw[:16]

        out: list[tuple[str, Annotation]] = []
        for a in self.store.annotations:
            kind = ANN_TYPE_LABELS.get(a.type.value, a.type.value)
            label = f"S{a.page + 1}: {kind}"
            if a.text:
                label += f" — {a.text[:40]}"
            elif a.type == AnnotationType.MEASURE:
                label += f" — {a.measure_label(self.scale)}"
            tags = getattr(a, "tags", None) or []
            if tags:
                from ild_pdf.annotate import tags_to_str

                label += f" [{tags_to_str(tags)}]"
            ts = _fmt_ts(getattr(a, "modified", "") or getattr(a, "created", ""))
            if ts:
                label += f" · {ts}"
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
        from instantlensdoc.ui.file_dialogs import confirm_overwrite_export

        if not confirm_overwrite_export(dest, self):
            return False
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

    def export_annotations_json(self) -> bool:
        """Annotationen als JSON-Datei exportieren (Dialog)."""
        if not self.store or not self.pdf_path:
            QMessageBox.information(self, "Annotationen", "Kein PDF geladen.")
            return False
        from PySide6.QtWidgets import QFileDialog

        default = str(self.pdf_path.with_suffix(self.pdf_path.suffix + ".annotations.json"))
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Annotationen als JSON exportieren",
            default,
            "JSON (*.json);;Annotation-Sidecar (*.ildann.json);;Alle (*.*)",
        )
        if not path:
            return False
        dest = Path(path)
        if dest.suffix.lower() != ".json":
            dest = dest.with_suffix(dest.suffix + ".json") if dest.suffix else Path(str(dest) + ".json")
        from instantlensdoc.ui.file_dialogs import confirm_overwrite_export

        if not confirm_overwrite_export(dest, self):
            return False
        try:
            saved = self.store.export_json(dest)
            self.status.emit(f"Annotationen exportiert: {saved.name} ({len(self.store.annotations)})")
            return True
        except Exception as e:
            QMessageBox.warning(self, "Annotationen exportieren", str(e))
            return False

    def export_annotations_csv(self) -> bool:
        """Annotationen als CSV-Datei exportieren (Dialog)."""
        if not self.store or not self.pdf_path:
            QMessageBox.information(self, "Annotationen", "Kein PDF geladen.")
            return False
        from PySide6.QtWidgets import QFileDialog
        from instantlensdoc.ui.file_dialogs import confirm_overwrite_export

        default = str(self.pdf_path.with_suffix(self.pdf_path.suffix + ".annotations.csv"))
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Annotationen als CSV exportieren",
            default,
            "CSV (*.csv);;Alle (*.*)",
        )
        if not path:
            return False
        dest = Path(path)
        if dest.suffix.lower() != ".csv":
            dest = dest.with_suffix(".csv")
        if not confirm_overwrite_export(dest, self):
            return False
        try:
            saved = self.store.export_csv(dest)
            self.status.emit(f"Annotationen CSV: {saved.name} ({len(self.store.annotations)})")
            return True
        except Exception as e:
            QMessageBox.warning(self, "Annotationen CSV exportieren", str(e))
            return False

    def export_annotations_report(self, *, default_fmt: str = "md") -> bool:
        """PDF-Kommentare als zusammenhängenden TXT/MD-Bericht exportieren."""
        if not self.store or not self.pdf_path:
            QMessageBox.information(self, "Kommentar-Bericht", "Kein PDF geladen.")
            return False
        from PySide6.QtWidgets import QFileDialog
        from instantlensdoc.ui.file_dialogs import confirm_overwrite_export

        fmt = (default_fmt or "md").strip().lower()
        if fmt not in ("md", "txt"):
            fmt = "md"
        suffix = ".md" if fmt == "md" else ".txt"
        default = str(self.pdf_path.with_suffix(self.pdf_path.suffix + f".kommentare{suffix}"))
        filt = (
            "Markdown (*.md);;Text (*.txt);;Alle (*.*)"
            if fmt == "md"
            else "Text (*.txt);;Markdown (*.md);;Alle (*.*)"
        )
        path, selected = QFileDialog.getSaveFileName(
            self,
            "Kommentar-Bericht exportieren",
            default,
            filt,
        )
        if not path:
            return False
        dest = Path(path)
        sel = (selected or "").lower()
        if "txt" in sel and "markdown" not in sel:
            use_fmt = "txt"
            if dest.suffix.lower() != ".txt":
                dest = dest.with_suffix(".txt")
        elif "markdown" in sel or dest.suffix.lower() in (".md", ".markdown"):
            use_fmt = "md"
            if dest.suffix.lower() not in (".md", ".markdown"):
                dest = dest.with_suffix(".md")
        elif dest.suffix.lower() == ".txt":
            use_fmt = "txt"
        else:
            use_fmt = "md"
            if dest.suffix.lower() not in (".md", ".markdown"):
                dest = dest.with_suffix(".md")
        if not confirm_overwrite_export(dest, self):
            return False
        try:
            saved = self.store.export_report(
                dest,
                fmt=use_fmt,
                source=self.pdf_path,
            )
            self.status.emit(
                f"Kommentar-Bericht: {saved.name} ({len(self.store.annotations)} Einträge)"
            )
            return True
        except Exception as e:
            QMessageBox.warning(self, "Kommentar-Bericht", str(e))
            return False

    def export_annotations_flattened(self) -> bool:
        """
        Alle Annotationen flatten/bake: Seiten rendern + Annotationen einzeichnen → neues PDF.
        Original und Sidecar bleiben unverändert.
        """
        if not self.store or not self.pdf_path:
            QMessageBox.information(self, "Flatten/Bake", "Kein PDF geladen.")
            return False
        n = len(self.store.annotations)
        if n == 0:
            reply = QMessageBox.question(
                self,
                "Flatten/Bake",
                "Keine Annotationen vorhanden.\nTrotzdem Seiten als PDF exportieren (ohne Overlay)?",
            )
            if reply != QMessageBox.Yes:
                return False
        from PySide6.QtWidgets import QFileDialog
        from ild_pdf import flatten_annotations_to_pdf
        from instantlensdoc.core.app_settings import (
            dialog_start_dir,
            remember_recent_dir,
            set_last_export_dir,
        )

        default = str(
            Path(dialog_start_dir(self.pdf_path.parent))
            / f"{self.pdf_path.stem}_flattened.pdf"
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Annotationen flatten/bake exportieren",
            default,
            "PDF (*.pdf);;Alle (*.*)",
        )
        if not path:
            return False
        dest = Path(path)
        if dest.suffix.lower() != ".pdf":
            dest = dest.with_suffix(".pdf")
        if dest.resolve() == self.pdf_path.resolve():
            QMessageBox.warning(
                self,
                "Flatten/Bake",
                "Ziel darf nicht die aktuelle Datei sein.\nBitte anderen Namen wählen.",
            )
            return False
        from instantlensdoc.ui.file_dialogs import confirm_overwrite_export

        if not confirm_overwrite_export(dest, self):
            return False
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication, QProgressDialog

        try:
            if self.store.dirty:
                self.store.save(force=True)
            bake_scale = max(float(self.scale), 1.5)
            total_pages = max(1, int(self.page_count or 1))
            prog = QProgressDialog("Flatten/Bake…", "Abbrechen", 0, total_pages + 1, self)
            prog.setWindowTitle("Flatten/Bake")
            prog.setWindowModality(Qt.WindowModal)
            prog.setMinimumDuration(0)
            prog.setValue(0)
            prog.setAutoClose(False)
            prog.setAutoReset(False)
            prog.show()
            QApplication.processEvents()

            def _on_prog(msg: str, current: int = 0, total: int = 0) -> None:
                if total and total > 0:
                    prog.setMaximum(total)
                    prog.setValue(min(max(0, current), total))
                prog.setLabelText(msg or "…")
                QApplication.processEvents()

            out = flatten_annotations_to_pdf(
                self.pdf_path,
                self.store,
                scale=bake_scale,
                out_path=dest,
                password=self.password,
                grayscale=self._grayscale,
                progress=_on_prog,
                should_cancel=prog.wasCanceled,
            )
            prog.setValue(prog.maximum())
            prog.close()
            set_last_export_dir(out.parent)
            remember_recent_dir(out.parent)
            self.status.emit(f"Flatten/Bake: {out.name} ({n} Ann., {self.page_count} Seite(n))")
            QMessageBox.information(
                self,
                "Flatten/Bake",
                f"Annotationen eingebrannt (alle Seiten):\n{out}\n\n"
                f"{n} Annotation(en) · Original unverändert.",
            )
            return True
        except InterruptedError:
            try:
                prog.close()
            except Exception:
                pass
            self.status.emit("Flatten/Bake abgebrochen")
            return False
        except Exception as e:
            try:
                prog.close()
            except Exception:
                pass
            QMessageBox.warning(self, "Flatten/Bake", str(e))
            return False

    def import_annotations_json(self) -> bool:
        """Annotationen aus JSON importieren (ersetzen oder anhängen)."""
        if not self.store or not self.pdf_path:
            QMessageBox.information(self, "Annotationen", "Kein PDF geladen.")
            return False
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Annotationen aus JSON importieren",
            str(self.pdf_path.parent),
            "JSON (*.json *.ildann.json);;Alle (*.*)",
        )
        if not path:
            return False
        reply = QMessageBox.question(
            self,
            "Annotationen importieren",
            "Bestehende Annotationen ersetzen?\n\n"
            "Ja = ersetzen · Nein = anhängen · Abbrechen = nichts",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Cancel:
            return False
        replace = reply == QMessageBox.Yes
        try:
            n = self.store.import_json(path, replace=replace)
            self.store.save(force=True)
            self.refresh()
            self.annotations_changed.emit()
            mode = "ersetzt" if replace else "angehängt"
            self.status.emit(f"{n} Annotation(en) {mode} aus {Path(path).name}")
            return True
        except Exception as e:
            from ild_pdf.annotate import AnnotationImportError

            title = "Annotationen importieren"
            if isinstance(e, AnnotationImportError):
                QMessageBox.warning(self, title, f"Schema v4 / Struktur ungültig:\n\n{e}")
            else:
                QMessageBox.warning(self, title, str(e))
            return False

    def save_pdf_as_copy(self) -> bool:
        """PDF (und Sidecar falls vorhanden) als Kopie speichern; aktuelles Dokument bleibt geöffnet."""
        if not self.pdf_path:
            QMessageBox.information(self, "Als Kopie speichern", "Kein PDF geladen.")
            return False
        from PySide6.QtWidgets import QFileDialog
        import shutil

        default = str(
            self.pdf_path.with_name(f"{self.pdf_path.stem}_Kopie{self.pdf_path.suffix}")
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            "PDF als Kopie speichern",
            default,
            "PDF (*.pdf);;Alle (*.*)",
        )
        if not path:
            return False
        dest = Path(path)
        if dest.suffix.lower() != ".pdf":
            dest = dest.with_suffix(".pdf")
        if dest.resolve() == self.pdf_path.resolve():
            QMessageBox.warning(
                self,
                "Als Kopie speichern",
                "Ziel darf nicht die aktuelle Datei sein.\nBitte anderen Namen wählen.",
            )
            return False
        from instantlensdoc.ui.file_dialogs import confirm_overwrite_export

        if not confirm_overwrite_export(dest, self):
            return False
        try:
            # Offene Annotationen zuerst in Sidecar schreiben
            if self.store and self.store.dirty:
                self.store.save(force=True)
            shutil.copy2(self.pdf_path, dest)
            side_src = self.pdf_path.with_suffix(self.pdf_path.suffix + ".ildann.json")
            side_dst = dest.with_suffix(dest.suffix + ".ildann.json")
            if side_src.is_file():
                shutil.copy2(side_src, side_dst)
            msg = f"Kopie gespeichert: {dest.name}"
            if side_src.is_file():
                msg += f" (+ {side_dst.name})"
            self.status.emit(msg)
            QMessageBox.information(
                self,
                "Als Kopie speichern",
                f"PDF-Kopie geschrieben (aktuelles Dokument bleibt geöffnet):\n{dest}",
            )
            return True
        except Exception as e:
            QMessageBox.warning(self, "Als Kopie speichern", str(e))
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

    def render_thumbnails(self, *, max_pages: int = 40, scale: float | None = None):
        """Kleine Seitenvorschauen (PIL). Begrenzt auf max_pages — bevorzugt lazy via render_thumbnail."""
        if not self.pdf_path or self.page_count <= 0:
            return []
        if scale is None:
            from instantlensdoc.core.app_settings import get_pdf_thumbnail_scale

            scale = get_pdf_thumbnail_scale()
        out = []
        n = min(self.page_count, max_pages)
        for i in range(n):
            out.append(self.render_thumbnail(i, scale=scale))
        return out

    def render_thumbnail(self, page_index: int, *, scale: float | None = None):
        """Eine Thumbnail-Seite rendern (für Lazy-Load)."""
        from PIL import Image
        from instantlensdoc.core.app_settings import get_pdf_thumbnail_scale, pdf_thumbnail_icon_size

        if scale is None:
            scale = get_pdf_thumbnail_scale()
        iw, ih = pdf_thumbnail_icon_size(scale)
        if not self.pdf_path or page_index < 0 or page_index >= self.page_count:
            return Image.new("RGB", (iw, ih), (220, 220, 220))
        try:
            return render_page(
                self.pdf_path,
                page_index,
                scale=scale,
                password=self.password,
                use_cache=True,
                grayscale=self._grayscale,
                invert=self._night_mode,
            )
        except Exception:
            return Image.new("RGB", (iw, ih), (220, 220, 220))

    def _edit_overlay(self, ann_id: str):
        """Notiz-/Kommentar-/Overlay-Text nachträglich bearbeiten."""
        if not self.store:
            return
        ann = self.store.get(ann_id)
        if not ann:
            return
        editable = {
            AnnotationType.TEXT_OVERLAY,
            AnnotationType.TEXT,
            AnnotationType.STICKY,
            AnnotationType.CALLOUT,
            AnnotationType.STAMP,
            AnnotationType.SIGNATURE_FIELD,
        }
        if ann.type not in editable:
            return
        dlg = TextOverlayEditDialog(ann, self)
        if dlg.exec() != QDialog.Accepted:
            return
        vals = dlg.values()
        self.store.update(ann_id, **vals)
        try:
            self.store.save()
        except Exception as e:
            QMessageBox.warning(self, "Annotation", str(e))
        self.refresh()
        self.annotations_changed.emit()
        self.status.emit(f"{ann.type.value} aktualisiert")

    def edit_selected_annotation_text(self) -> bool:
        """Ausgewählte Annotation (Notiz/Text/…) bearbeiten."""
        if not self.store or not self._selected_ann_id:
            return False
        ann = self.store.get(self._selected_ann_id)
        if not ann:
            return False
        self._edit_overlay(ann.id)
        return True

    def edit_selected_annotation_tags(self) -> bool:
        """Freie Tags/Labels der Auswahl bearbeiten (alle Annotationstypen)."""
        if not self.store or not self._selected_ann_id:
            self.status.emit("Keine Annotation ausgewählt")
            return False
        ann = self.store.get(self._selected_ann_id)
        if not ann:
            return False
        from ild_pdf.annotate import normalize_tags, tags_to_str
        from PySide6.QtWidgets import QInputDialog

        current = tags_to_str(getattr(ann, "tags", None))
        text, ok = QInputDialog.getText(
            self,
            "Annotation-Tags",
            "Tags (komma-getrennt):",
            text=current,
        )
        if not ok:
            return False
        tags = normalize_tags(text)
        self.store.update(ann.id, tags=tags)
        try:
            self.store.save()
        except Exception as e:
            QMessageBox.warning(self, "Annotation-Tags", str(e))
            return False
        self.refresh()
        self.annotations_changed.emit()
        self.status.emit(
            f"Tags: {tags_to_str(tags)}" if tags else "Tags entfernt"
        )
        return True

    def duplicate_selected_annotation(self) -> bool:
        """Ausgewählte Annotation duplizieren (neue ID, leicht versetzt)."""
        if not self.store or not self._selected_ann_id:
            self.status.emit("Keine Annotation ausgewählt")
            return False
        dup = self.store.duplicate(self._selected_ann_id)
        if dup is None:
            self.status.emit("Duplizieren fehlgeschlagen")
            return False
        try:
            self.store.save()
        except Exception as e:
            QMessageBox.warning(self, "Annotation duplizieren", str(e))
            return False
        self._selected_ann_id = dup.id
        self._selected_ann_ids = {dup.id}
        self.canvas.set_selected_id(dup.id)
        self.refresh()
        self.annotations_changed.emit()
        self.status.emit(f"Annotation dupliziert ({dup.type.value})")
        return True

    def copy_selected_annotations(self) -> int:
        """
        Ausgewählte Annotation(en) in internes Clipboard kopieren
        (Einfügen auf anderer Seite möglich).
        """
        if not self.store:
            self.status.emit("Kein PDF geladen")
            return 0
        ids = list(self._selected_ann_ids) if self._selected_ann_ids else (
            [self._selected_ann_id] if self._selected_ann_id else []
        )
        payloads: list[dict] = []
        for aid in ids:
            ann = self.store.get(aid)
            if ann is not None:
                payloads.append(ann.to_dict())
        if not payloads:
            self.status.emit("Keine Annotation ausgewählt")
            return 0
        self._ann_clipboard = payloads
        self.status.emit(f"{len(payloads)} Annotation(en) kopiert")
        return len(payloads)

    def paste_annotations_on_page(self, page_index: int | None = None) -> int:
        """Kopierte Annotationen auf Zielseite einfügen (Default: aktuelle Seite)."""
        if not self.store or not self.pdf_path:
            self.status.emit("Kein PDF geladen")
            return 0
        if not self._ann_clipboard:
            self.status.emit("Zwischenablage leer (Annotationen zuerst kopieren)")
            return 0
        target = self.page_index if page_index is None else int(page_index)
        if target < 0 or target >= max(1, int(self.page_count or 0)):
            self.status.emit("Ungültige Zielseite")
            return 0
        created = self.store.paste_dicts(self._ann_clipboard, page=target)
        if not created:
            self.status.emit("Einfügen fehlgeschlagen")
            return 0
        try:
            self.store.save()
        except Exception as e:
            QMessageBox.warning(self, "Annotationen einfügen", str(e))
            return 0
        self._selected_ann_ids = {a.id for a in created}
        self._selected_ann_id = created[0].id
        self.canvas.set_selected_id(self._selected_ann_id)
        if target != self.page_index:
            self.goto_page(target)
        else:
            self.refresh()
        self.annotations_changed.emit()
        self.status.emit(f"{len(created)} Annotation(en) auf Seite {target + 1} eingefügt")
        return len(created)

    def rotate_selected_stamp(self, degrees: int = 90) -> bool:
        """Ausgewählten Stempel um 90°-Schritte drehen (Sidecar)."""
        if not self.store or not self._selected_ann_id:
            self.status.emit("Kein Stempel ausgewählt")
            return False
        ann = self.store.get(self._selected_ann_id)
        if not ann or ann.type != AnnotationType.STAMP:
            self.status.emit("Auswahl ist kein Stempel")
            return False
        try:
            cur = float(getattr(ann, "rotation", 0.0) or 0.0)
        except (TypeError, ValueError):
            cur = 0.0
        new_rot = float(int(round((cur + float(degrees)) / 90.0)) % 4 * 90)
        self.store.update(ann.id, rotation=new_rot)
        try:
            self.store.save()
        except Exception as e:
            QMessageBox.warning(self, "Stempel drehen", str(e))
            return False
        self.refresh()
        self.annotations_changed.emit()
        self.status.emit(f"Stempel gedreht ({int(new_rot)}°)")
        return True

    def _open_uri_link(self, uri: str) -> None:
        """Externe http(s)-URL im Systembrowser öffnen."""
        from ild_pdf import is_external_http_uri

        raw = (uri or "").strip()
        if not is_external_http_uri(raw):
            self.status.emit("Kein gültiger externer Link")
            return
        ok = QDesktopServices.openUrl(QUrl(raw))
        if ok:
            self.status.emit(f"Link geöffnet: {raw[:80]}")
        else:
            QMessageBox.warning(self, "Link", f"URL konnte nicht geöffnet werden:\n{raw}")

    def rotate_current(self, degrees: int = 90):
        """Aktuelle Seite drehen (−90/90/180/270) und PDF speichern (Undo-fähig)."""
        if not self.pdf_path:
            return
        try:
            deg = int(degrees)
            self._page_ops_undo.append(
                {"kind": "rotate", "index": int(self.page_index), "degrees": deg}
            )
            if len(self._page_ops_undo) > 20:
                self._page_ops_undo.pop(0)
            rotate_page(self.pdf_path, self.page_index, deg)
            from ild_pdf.render import clear_render_cache

            clear_render_cache(self.pdf_path)
            self.refresh()
            self.document_changed.emit()
            shown = deg % 360
            self.status.emit(
                f"Seite {self.page_index + 1} gedreht ({shown}°) — Ctrl+Z rückgängig"
            )
        except Exception as e:
            if self._page_ops_undo and self._page_ops_undo[-1].get("kind") == "rotate":
                self._page_ops_undo.pop()
            QMessageBox.warning(self, "Drehen", str(e))

    def flip_current(self, *, horizontal: bool = False, vertical: bool = False):
        """Aktuelle Seite spiegeln (horizontal und/oder vertikal) und speichern."""
        if not self.pdf_path:
            return
        if not horizontal and not vertical:
            return
        try:
            flip_page(
                self.pdf_path,
                self.page_index,
                horizontal=horizontal,
                vertical=vertical,
            )
            from ild_pdf.render import clear_render_cache

            clear_render_cache(self.pdf_path)
            self.refresh()
            self.document_changed.emit()
            parts = []
            if horizontal:
                parts.append("horizontal")
            if vertical:
                parts.append("vertikal")
            self.status.emit(
                f"Seite {self.page_index + 1} gespiegelt ({'/'.join(parts)}) und gespeichert"
            )
        except Exception as e:
            QMessageBox.warning(self, "Spiegeln", str(e))

    def extract_page_as_image(self):
        if not self.pdf_path:
            return
        from PySide6.QtWidgets import QFileDialog, QInputDialog
        from ild_pdf import extract_page_image
        from instantlensdoc.core.app_settings import (
            EXPORT_RASTER_DPI_CHOICES,
            apply_export_profile,
            dialog_start_dir,
            get_active_export_profile_name,
            get_export_profile,
            get_export_profiles,
            get_export_raster_dpi,
            remember_recent_dir,
            set_export_raster_dpi,
            set_last_export_dir,
        )

        profiles = get_export_profiles()
        active_name = get_active_export_profile_name()
        profile = get_export_profile(active_name) if active_name else None
        if profiles:
            names = ["(kein Profil)"] + [str(p["name"]) for p in profiles]
            default_idx = 0
            if profile:
                try:
                    default_idx = names.index(str(profile["name"]))
                except ValueError:
                    default_idx = 0
            chosen, ok = QInputDialog.getItem(
                self,
                "Seite als Bild",
                "Export-Profil (DPI/Format/Ziel):",
                names,
                default_idx,
                False,
            )
            if not ok:
                return
            if chosen and chosen != "(kein Profil)":
                profile = apply_export_profile(chosen)
            else:
                profile = None

        dpi_items = [str(d) for d in EXPORT_RASTER_DPI_CHOICES]
        default_dpi = str(int(profile["dpi"]) if profile else get_export_raster_dpi())
        dpi_idx = dpi_items.index(default_dpi) if default_dpi in dpi_items else 1
        dpi_str, ok = QInputDialog.getItem(
            self,
            "Seite als Bild",
            "Auflösung (DPI):",
            dpi_items,
            dpi_idx,
            False,
        )
        if not ok:
            return
        dpi = int(dpi_str)
        set_export_raster_dpi(dpi)

        prefer_jpeg = bool(profile and str(profile.get("format")) == "JPEG")
        start_dir = dialog_start_dir(
            str(profile["target"]) if profile and profile.get("target") else None,
            self.pdf_path.parent,
        )
        ext = "jpg" if prefer_jpeg else "png"
        default = str(Path(start_dir) / f"{self.pdf_path.stem}_p{self.page_index + 1}.{ext}")
        filters = (
            "JPEG (*.jpg *.jpeg);;PNG (*.png)" if prefer_jpeg else "PNG (*.png);;JPEG (*.jpg *.jpeg)"
        )
        path, selected = QFileDialog.getSaveFileName(
            self, "Seite als Bild", default, filters
        )
        if not path:
            return
        from instantlensdoc.ui.file_dialogs import confirm_overwrite_export

        if not confirm_overwrite_export(path, self):
            return
        try:
            fmt = "JPEG" if path.lower().endswith((".jpg", ".jpeg")) or "JPEG" in selected else "PNG"
            if fmt == "JPEG" and not path.lower().endswith((".jpg", ".jpeg")):
                path = path + ".jpg"
                if not confirm_overwrite_export(path, self):
                    return
            out = extract_page_image(
                self.pdf_path,
                self.page_index,
                path,
                dpi=dpi,
                format=fmt,
                password=self.password,
                grayscale=self._grayscale,
            )
            set_last_export_dir(Path(out).parent)
            remember_recent_dir(Path(out).parent)
            self.status.emit(f"Seite exportiert ({dpi} DPI): {out.name}")
        except Exception as e:
            QMessageBox.warning(self, "Extrahieren", str(e))

    def export_pages_as_images(self):
        """Alle (oder aktuelle) PDF-Seiten als PNG/JPEG in einen Ordner exportieren."""
        if not self.pdf_path:
            QMessageBox.information(self, "Export", "Kein PDF geladen.")
            return
        from PySide6.QtWidgets import QFileDialog, QInputDialog
        from ild_pdf import extract_pages_as_images
        from instantlensdoc.core.app_settings import (
            EXPORT_RASTER_DPI_CHOICES,
            apply_export_profile,
            dialog_start_dir,
            get_active_export_profile_name,
            get_export_profile,
            get_export_profiles,
            get_export_raster_dpi,
            remember_recent_dir,
            set_export_raster_dpi,
            set_last_export_dir,
        )

        profiles = get_export_profiles()
        active_name = get_active_export_profile_name()
        profile = get_export_profile(active_name) if active_name else None
        if profiles:
            names = ["(kein Profil)"] + [str(p["name"]) for p in profiles]
            default_idx = 0
            if profile:
                try:
                    default_idx = names.index(str(profile["name"]))
                except ValueError:
                    default_idx = 0
            chosen, ok = QInputDialog.getItem(
                self,
                "Seiten als Bilder",
                "Export-Profil (DPI/Format/Ziel):",
                names,
                default_idx,
                False,
            )
            if not ok:
                return
            if chosen and chosen != "(kein Profil)":
                profile = apply_export_profile(chosen)
            else:
                profile = None

        scope, ok = QInputDialog.getItem(
            self,
            "Seiten als Bilder",
            "Welche Seiten?",
            ["Aktuelle Seite", "Alle Seiten"],
            1,
            False,
        )
        if not ok:
            return
        fmt_items = ["PNG", "JPEG"]
        fmt_idx = 1 if profile and str(profile.get("format")) == "JPEG" else 0
        fmt, ok = QInputDialog.getItem(
            self,
            "Seiten als Bilder",
            "Format:",
            fmt_items,
            fmt_idx,
            False,
        )
        if not ok:
            return
        dpi_items = [str(d) for d in EXPORT_RASTER_DPI_CHOICES]
        default_dpi = str(int(profile["dpi"]) if profile else get_export_raster_dpi())
        dpi_idx = dpi_items.index(default_dpi) if default_dpi in dpi_items else 1
        dpi_str, ok = QInputDialog.getItem(
            self,
            "Seiten als Bilder",
            "Auflösung (DPI):",
            dpi_items,
            dpi_idx,
            False,
        )
        if not ok:
            return
        dpi = int(dpi_str)
        set_export_raster_dpi(dpi)
        start_dir = dialog_start_dir(
            str(profile["target"]) if profile and profile.get("target") else None,
            self.pdf_path.parent,
        )
        out_dir = QFileDialog.getExistingDirectory(self, "Zielordner für Bilder", start_dir)
        if not out_dir:
            return
        pages = [self.page_index] if scope.startswith("Aktuelle") else None
        try:
            written = extract_pages_as_images(
                self.pdf_path,
                out_dir,
                pages=pages,
                dpi=dpi,
                format=fmt,
                password=self.password,
                grayscale=self._grayscale,
            )
            set_last_export_dir(out_dir)
            remember_recent_dir(out_dir)
            self.status.emit(f"{len(written)} Bild(er) @ {dpi} DPI → {Path(out_dir).name}")
            QMessageBox.information(
                self,
                "Export",
                f"{len(written)} Seite(n) als {fmt} ({dpi} DPI) exportiert nach:\n{out_dir}",
            )
        except Exception as e:
            QMessageBox.warning(self, "Export", str(e))

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
        from instantlensdoc.core.app_settings import dialog_start_dir, remember_recent_dir

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Signatur-Bild",
            dialog_start_dir(self.pdf_path.parent if self.pdf_path else None),
            "Bilder (*.png *.jpg *.jpeg *.bmp)",
        )
        if not path:
            return
        remember_recent_dir(path)
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
        from instantlensdoc.core.app_settings import dialog_start_dir, remember_recent_dir

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Bild als neue Seite",
            dialog_start_dir(self.pdf_path.parent if self.pdf_path else None),
            "Bilder (*.png *.jpg *.jpeg *.bmp)",
        )
        if not path:
            return
        remember_recent_dir(path)
        try:
            insert_image_as_page(self.pdf_path, path)
            from ild_pdf import PdfDocument

            with PdfDocument(self.pdf_path, password=self.password) as doc:
                self.page_count = len(doc)
                self._reload_page_labels()
            self.page_index = self.page_count - 1
            self.refresh()
            self.status.emit("Bildseite angehängt")
        except Exception as e:
            QMessageBox.warning(self, "Bild einfügen", str(e))

    def _highlight_from_text_selection(
        self,
        page: int,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
    ) -> bool:
        """Selection→Highlight: Text unter Drag als Highlight-Annotation(en) speichern."""
        if not self.store or not self.pdf_path:
            return False
        try:
            rects, text = selection_to_highlight_rects(
                self.pdf_path,
                page,
                x0,
                y0,
                x1,
                y1,
                scale=self.scale,
                password=self.password,
            )
        except Exception:
            return False
        if not rects:
            return False
        created: list[Annotation] = []
        with self.store.atomic():
            for i, r in enumerate(rects):
                snippet = (r.text or "").strip() or (text if i == 0 else "")
                ann = Annotation(
                    page=page,
                    type=AnnotationType.HIGHLIGHT,
                    x=r.x,
                    y=r.y,
                    width=max(r.width, 4.0),
                    height=max(r.height, 6.0),
                    color=self._highlight_color,
                    text=snippet,
                    opacity=self._default_opacity,
                )
                self.store.add(ann)
                created.append(ann)
        if not created:
            return False
        try:
            self.store.save()
        except Exception as e:
            QMessageBox.warning(self, "Annotationen", f"Speichern fehlgeschlagen: {e}")
        self._selected_ann_id = created[0].id
        self._selected_ann_ids = {a.id for a in created}
        self.canvas.set_selected_ids(self._selected_ann_ids)
        self.refresh()
        self.annotations_changed.emit()
        preview = (text or created[0].text or "").replace("\n", " ")
        if len(preview) > 48:
            preview = preview[:45] + "…"
        n = len(created)
        self.status.emit(
            f"Text-Highlight ({n}): {preview}" if preview else f"Text-Highlight ({n})"
        )
        return True

    def _on_text_selection(self, x0: float, y0: float, x1: float, y1: float):
        """Auswahl-Modus: Text unter Marquee extrahieren (ohne Annotation)."""
        if not self.pdf_path:
            self._text_selection_text = ""
            self._text_selection_rects = []
            return
        page0, lx0, ly0 = self._spread_resolve(x0, y0)
        lx1 = lx0 + (x1 - x0)
        ly1 = ly0 + (y1 - y0)
        try:
            rects, text = selection_to_highlight_rects(
                self.pdf_path,
                page0,
                lx0,
                ly0,
                lx1,
                ly1,
                scale=self.scale,
                password=self.password,
            )
        except Exception:
            rects, text = [], ""
        if not text:
            # Fallback nur Plaintext-API
            try:
                text = selection_to_plain_text(
                    self.pdf_path,
                    page0,
                    lx0,
                    ly0,
                    lx1,
                    ly1,
                    scale=self.scale,
                    password=self.password,
                )
            except Exception:
                text = ""
        self._text_selection_text = text or ""
        self._text_selection_rects = [
            (float(r.x), float(r.y), float(r.width), float(r.height)) for r in (rects or [])
        ]
        if self._text_selection_rects:
            self.canvas.set_search_highlights(self._text_selection_rects, active=0)
        else:
            # gesamtes Marquee als Vorschau
            self.canvas.set_search_highlights(
                [(min(lx0, lx1), min(ly0, ly1), abs(lx1 - lx0), abs(ly1 - ly0))],
                active=0,
            )
        if self._text_selection_text:
            preview = self._text_selection_text.replace("\n", " ")
            if len(preview) > 56:
                preview = preview[:53] + "…"
            self.status.emit(f"Text ausgewählt — Ctrl+C kopiert: {preview}")
        else:
            self.status.emit("Kein Text in der Auswahl — erneut aufziehen")

    def selection_text(self) -> str:
        """Zuletzt ausgewählter PDF-Text (Marquee) oder Text der ausgewählten Annotationen."""
        if (self._text_selection_text or "").strip():
            return self._text_selection_text
        if not self.store:
            return ""
        parts: list[str] = []
        ids = list(self._selected_ann_ids) if self._selected_ann_ids else []
        if not ids and self._selected_ann_id:
            ids = [self._selected_ann_id]
        for aid in ids:
            ann = self.store.get(aid)
            if ann is None:
                continue
            t = (getattr(ann, "text", None) or "").strip()
            if t:
                parts.append(t)
        return "\n".join(parts)

    def copy_text_selection(self) -> bool:
        """Ausgewählten PDF-Text in die System-Zwischenablage kopieren (nicht nur Highlight)."""
        text = self.selection_text()
        if not text:
            self.status.emit("Nichts zu kopieren — Text im Auswahl-Modus aufziehen")
            return False
        clip = QApplication.clipboard()
        if clip is None:
            return False
        clip.setText(text)
        preview = text.replace("\n", " ")
        if len(preview) > 48:
            preview = preview[:45] + "…"
        self.status.emit(f"Kopiert ({len(text)} Z.): {preview}")
        return True

    def sticky_from_text_selection(self, *, edit: bool = True) -> bool:
        """Auswahl → Sticky/Notiz mit vorausgefülltem Text (optional Dialog zum Anpassen)."""
        if not self.store or not self.pdf_path:
            self.status.emit("Notiz aus Auswahl nur bei geöffnetem PDF")
            return False
        text = (self.selection_text() or "").strip()
        if not text:
            self.status.emit("Kein Text ausgewählt — Auswahl-Werkzeug: Text aufziehen")
            return False
        page = int(self.page_index)
        x, y = 40.0, 40.0
        if self._text_selection_rects:
            rx, ry, rw, rh = self._text_selection_rects[0]
            x = float(rx)
            y = float(ry) + max(float(rh), 8.0) + 4.0
        if edit:
            text, ok = QInputDialog.getMultiLineText(
                self,
                "Notiz aus Auswahl",
                "Inhalt (vorausgefüllt aus Textauswahl):",
                text,
            )
            if not ok:
                return False
            text = (text or "").strip()
            if not text:
                self.status.emit("Notiz abgebrochen — leerer Text")
                return False
        height = 70.0 if "\n" not in text else min(160.0, 24.0 + 18.0 * (text.count("\n") + 1))
        ann = Annotation(
            page=page,
            type=AnnotationType.STICKY,
            x=x,
            y=y,
            width=160.0,
            height=height,
            text=text,
            color=self._note_color,
            opacity=self._default_opacity,
        )
        self._commit_ann(ann)
        self._selected_ann_id = ann.id
        self._selected_ann_ids = {ann.id}
        self.canvas.set_selected_ids(self._selected_ann_ids)
        preview = text.replace("\n", " ")
        if len(preview) > 48:
            preview = preview[:45] + "…"
        self.status.emit(f"Notiz aus Auswahl: {preview}")
        return True

    def _on_drag(self, x0: float, y0: float, x1: float, y1: float):
        if not self.store or self.tool is None or self.tool not in DRAG_TYPES:
            return
        page0, lx0, ly0 = self._spread_resolve(x0, y0)
        _page1, lx1, ly1 = self._spread_resolve(x1, y1)
        page = page0
        # Endpunkt relativ zum Start halten (kein Seitenwechsel mitten im Drag)
        lx1 = lx0 + (x1 - x0)
        ly1 = ly0 + (y1 - y0)
        x0, y0, x1, y1 = lx0, ly0, lx1, ly1
        if self.tool == AnnotationType.HIGHLIGHT:
            # Selection→Highlight: Text unter dem Drag-Rechteck als Annotation(en)
            if self.pdf_path and self._highlight_from_text_selection(page, x0, y0, x1, y1):
                return
            ann = Annotation(
                page=page,
                type=AnnotationType.HIGHLIGHT,
                x=min(x0, x1),
                y=min(y0, y1),
                width=max(abs(x1 - x0), 8),
                height=max(abs(y1 - y0), 8),
                color=self._highlight_color,
            )
        elif self.tool == AnnotationType.REDACTION:
            ann = Annotation(
                page=page,
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
                page=page,
                type=AnnotationType.RECTANGLE,
                x=min(x0, x1),
                y=min(y0, y1),
                width=max(abs(x1 - x0), 8),
                height=max(abs(y1 - y0), 8),
                color=self._pen_color,
            )
        elif self.tool in (AnnotationType.LINE, AnnotationType.ARROW, AnnotationType.MEASURE):
            ann = Annotation(
                page=page,
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

        page, x, y = self._spread_resolve(x, y)

        if self.tool == AnnotationType.CALLOUT:
            if self._pending_callout_anchor is None:
                self._pending_callout_anchor = (x, y)
                self._pending_callout_page = page
                self.status.emit("Callout: zweiten Klick für Textbox setzen")
                return
            ax, ay = self._pending_callout_anchor
            self._pending_callout_anchor = None
            page = getattr(self, "_pending_callout_page", page)
            text, ok = QInputDialog.getText(self, "Callout", "Text:")
            if not ok:
                return
            ann = Annotation(
                page=page,
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
            dlg = StampPickDialog(self)
            if dlg.exec() != QDialog.Accepted:
                return
            picked = dlg.result_stamp()
            if not picked:
                return
            text, color = picked
            width, height = 150.0, 52.0 if "\n" in text else 40.0
        elif self.tool == AnnotationType.STICKY:
            prefill = (self.selection_text() or "").strip()
            text, ok = QInputDialog.getMultiLineText(
                self,
                "Notiz",
                "Inhalt:" + (" (aus Textauswahl)" if prefill else ""),
                prefill,
            )
            if not ok:
                return
            height = 70.0 if "\n" not in (text or "") else min(160.0, 24.0 + 18.0 * (text.count("\n") + 1))
            color = self._note_color
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
            page=page,
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
        try:
            ann.opacity = max(0.05, min(1.0, float(self._default_opacity)))
        except (TypeError, ValueError):
            ann.opacity = 1.0
        self.store.add(ann)
        try:
            self.store.save()
        except Exception as e:
            QMessageBox.warning(self, "Annotationen", f"Speichern fehlgeschlagen: {e}")
        self.refresh()
        self.annotations_changed.emit()
        self.status.emit(f"Annotation gespeichert ({ann.type.value})")

    def _remap_insert(self, insert_at: int) -> None:
        """Annotation-Seitenindizes nach Einfügen einer Seite bei insert_at anpassen."""
        if not self.store:
            return
        mapping = {}
        for i in range(self.page_count):
            mapping[i] = i if i < insert_at else i + 1
        self.store.remap_pages(mapping)
        self.store.save(force=True)

    def insert_blank_after_current(self):
        """Leere Seite nach der aktuellen einfügen und speichern."""
        if not self.pdf_path:
            return
        try:
            at = self.page_index + 1
            new_idx = insert_blank_page(self.pdf_path, at)
            self._remap_insert(new_idx)
            from ild_pdf import PdfDocument
            from ild_pdf.render import clear_render_cache

            clear_render_cache(self.pdf_path)
            with PdfDocument(self.pdf_path, password=self.password) as doc:
                self.page_count = len(doc)
                self._reload_page_labels()
            self.page_index = new_idx
            self._selected_ann_id = None
            self._selected_ann_ids = set()
            self.canvas.set_selected_id(None)
            self.refresh()
            self.annotations_changed.emit()
            self.page_changed.emit(self.page_index)
            self.document_changed.emit()
            self.status.emit(f"Leere Seite {new_idx + 1} eingefügt und gespeichert")
        except Exception as e:
            QMessageBox.warning(self, "Leere Seite", str(e))

    def duplicate_current(self):
        """Aktuelle Seite duplizieren (Kopie danach) und speichern."""
        if not self.pdf_path:
            return
        try:
            new_idx = duplicate_page(self.pdf_path, self.page_index, after=True)
            self._remap_insert(new_idx)
            from ild_pdf import PdfDocument
            from ild_pdf.render import clear_render_cache

            clear_render_cache(self.pdf_path)
            with PdfDocument(self.pdf_path, password=self.password) as doc:
                self.page_count = len(doc)
                self._reload_page_labels()
            self.page_index = new_idx
            self._selected_ann_id = None
            self._selected_ann_ids = set()
            self.canvas.set_selected_id(None)
            self.refresh()
            self.annotations_changed.emit()
            self.page_changed.emit(self.page_index)
            self.document_changed.emit()
            self.status.emit(f"Seite {new_idx} dupliziert → S. {new_idx + 1} gespeichert")
        except Exception as e:
            QMessageBox.warning(self, "Duplizieren", str(e))

    def focus_annotation(self, ann) -> bool:
        """Zur Annotation springen und auswählen (Sidebar-Klick)."""
        if ann is None or not self.store:
            return False
        aid = getattr(ann, "id", None) or (ann if isinstance(ann, str) else None)
        target = self.store.get(aid) if aid else None
        if target is None and hasattr(ann, "page"):
            target = ann
            aid = getattr(ann, "id", None)
        if target is None:
            return False
        page = int(target.page)
        if page != self.page_index:
            self.goto_page(page)
        self._selected_ann_id = aid
        self._selected_ann_ids = {aid} if aid else set()
        self.canvas.set_selected_id(aid)
        self.refresh()
        self.status.emit(f"Annotation: {target.type.value} (S. {page + 1})")
        return True

    def delete_current(self):
        if not self.pdf_path or self.page_count <= 1:
            QMessageBox.information(self, "Löschen", "Letzte Seite kann nicht gelöscht werden.")
            return
        reply = QMessageBox.question(
            self,
            "Seite löschen",
            f"Seite {self.page_index + 1} wirklich löschen?\n(Rückgängig: Ctrl+Z)",
        )
        if reply != QMessageBox.Yes:
            return
        try:
            deleted = self.page_index
            page_bytes = extract_page_bytes(self.pdf_path, deleted)
            groups_before = {}
            if self.store is not None:
                groups_before = dict(self.store._meta.get("page_groups") or {})
            self._page_ops_undo.append(
                {
                    "kind": "delete",
                    "index": deleted,
                    "page_bytes": page_bytes,
                    "page_groups": groups_before,
                }
            )
            if len(self._page_ops_undo) > 20:
                self._page_ops_undo.pop(0)
            delete_pages(self.pdf_path, [deleted])
            if self.store:
                mapping = {}
                for i in range(self.page_count):
                    if i < deleted:
                        mapping[i] = i
                    elif i > deleted:
                        mapping[i] = i - 1
                # Eine Undo-Stufe für Annotation-Remap (wird bei Seiten-Undo mit restored)
                with self.store.atomic():
                    planned = []
                    changed = False
                    for ann in list(self.store.annotations):
                        if ann.page in mapping:
                            new_page = mapping[ann.page]
                            if new_page != ann.page:
                                changed = True
                            planned.append((ann, new_page))
                        else:
                            changed = True
                    if changed or len(planned) != len(self.store.annotations):
                        kept = []
                        for ann, new_page in planned:
                            if ann.page != new_page:
                                ann.page = new_page
                                ann.touch()
                            kept.append(ann)
                        self.store.annotations = kept
                        groups = dict(self.store._meta.get("page_groups") or {})
                        if groups:
                            new_groups = {}
                            for key, val in groups.items():
                                try:
                                    old_p = int(key)
                                except (TypeError, ValueError):
                                    continue
                                if old_p in mapping:
                                    new_groups[str(mapping[old_p])] = val
                            self.store._meta["page_groups"] = new_groups
                        favs = list(self.store._meta.get("page_favorites") or [])
                        if favs:
                            remapped = []
                            seen = set()
                            for raw in favs:
                                try:
                                    old_p = int(raw)
                                except (TypeError, ValueError):
                                    continue
                                if old_p not in mapping:
                                    continue
                                new_p = int(mapping[old_p])
                                if new_p not in seen:
                                    seen.add(new_p)
                                    remapped.append(new_p)
                            remapped.sort()
                            if remapped:
                                self.store._meta["page_favorites"] = remapped
                            else:
                                self.store._meta.pop("page_favorites", None)
                        self.store.dirty = True
                self.store.save(force=True)
            self.page_count -= 1
            self.page_index = min(self.page_index, self.page_count - 1)
            from ild_pdf.render import clear_render_cache

            clear_render_cache(self.pdf_path)
            self.refresh()
            self.annotations_changed.emit()
            self.page_changed.emit(self.page_index)
            self.document_changed.emit()
            self.status.emit("Seite gelöscht — Ctrl+Z stellt sie wieder her")
        except Exception as e:
            if self._page_ops_undo and self._page_ops_undo[-1].get("kind") == "delete":
                self._page_ops_undo.pop()
            QMessageBox.warning(self, "Löschen", str(e))

    def edit_page_annotation_group(self, page: int | None = None) -> bool:
        """Seiten-Annotationsgruppe umbenennen und farblich markieren."""
        if not self.store:
            QMessageBox.information(self, "Gruppe", "Kein PDF mit Annotationen geladen.")
            return False
        idx = self.page_index if page is None else int(page)
        cur = self.store.get_page_group(idx)
        title, ok = QInputDialog.getText(
            self,
            "Annotationsgruppe",
            f"Name für Gruppe Seite {idx + 1}:",
            text=cur.get("title") or "",
        )
        if not ok:
            return False
        color = cur.get("color") or ""
        pick = QMessageBox.question(
            self,
            "Gruppenfarbe",
            "Farbe für die Gruppe wählen?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        if pick == QMessageBox.Cancel:
            return False
        if pick == QMessageBox.Yes:
            initial = QColor(color) if color else QColor("#90CAF9")
            chosen = QColorDialog.getColor(initial, self, "Gruppenfarbe")
            if chosen.isValid():
                color = chosen.name().upper()
            elif not color:
                color = ""
        self.store.set_page_group(idx, title=title, color=color)
        try:
            self.store.save(force=True)
        except Exception as e:
            QMessageBox.warning(self, "Gruppe", str(e))
            return False
        self.annotations_changed.emit()
        label = title.strip() or f"Seite {idx + 1}"
        self.status.emit(f"Gruppe „{label}“ aktualisiert")
        return True

    def reorder_dialog(self):
        if not self.pdf_path or self.page_count < 2:
            QMessageBox.information(self, "Neu anordnen", "Mindestens 2 Seiten nötig.")
            return
        dlg = PageReorderDialog(self.page_count, self)
        if dlg.exec() != QDialog.Accepted:
            return
        order = dlg.new_order()
        self.apply_page_order(order)

    def apply_page_order(self, order: list[int]) -> bool:
        """Wendet neue Seitenreihenfolge an (Dialog oder Thumbnail-Drag)."""
        if not self.pdf_path or self.page_count < 2:
            return False
        if not order or len(order) != self.page_count:
            return False
        if order == list(range(self.page_count)):
            return False
        if sorted(order) != list(range(self.page_count)):
            QMessageBox.warning(self, "Neu anordnen", "Ungültige Seitenreihenfolge.")
            return False
        try:
            reorder_pages(self.pdf_path, order)
            if self.store:
                mapping = {old: new for new, old in enumerate(order)}
                self.store.remap_pages(mapping)
                self.store.save(force=True)
            self.page_index = 0
            self._selected_ann_id = None
            self._selected_ann_ids = set()
            self.canvas.set_selected_id(None)
            from ild_pdf import PdfDocument

            with PdfDocument(self.pdf_path, password=self.password) as doc:
                self.page_count = len(doc)
                self._reload_page_labels()
            self.refresh()
            self.annotations_changed.emit()
            self.page_changed.emit(self.page_index)
            self.document_changed.emit()
            self.status.emit("Seiten neu angeordnet")
            return True
        except Exception as e:
            QMessageBox.warning(self, "Neu anordnen", str(e))
            return False

    def clear(self):
        self.pdf_path = None
        self.store = None
        self.page_count = 0
        self.page_index = 0
        self._page_labels = []
        self._selected_ann_id = None
        self._selected_ann_ids = set()
        self.canvas.set_selected_id(None)
        self.canvas.clear()
        self.lbl_page.setText("—")
        self.annotations_changed.emit()
        self.document_changed.emit()
        self.zoom_changed.emit(self.scale)