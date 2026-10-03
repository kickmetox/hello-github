"""PDF-Ansicht: Zoom, Annotationen, Formen, Messung, Text-Overlay, Seitenops."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

from PySide6.QtCore import QPointF, Qt, QTimer, Signal, QUrl
from PySide6.QtGui import (
    QColor,
    QCursor,
    QDesktopServices,
    QFont,
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
    QComboBox,
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
    QMenu,
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
    extract_pages,
    flip_page,
    insert_blank_page,
    insert_page_from_bytes,
    reorder_pages,
    rotate_page,
)
from instantlensdoc.core.app_settings import (
    cycle_ann_palette_color,
    get_ann_color_presets,
    reset_ann_color_preset,
    get_ann_default_fill_color,
    get_ann_default_opacity,
    get_ann_highlight_color,
    get_ann_note_color,
    get_ann_pen_color,
    get_ann_layer_types_visible,
    get_annotations_locked,
    get_annotations_visible,
    get_default_zoom_mode,
    get_default_zoom_scale,
    get_pdf_continuous_scroll,
    get_pdf_grayscale,
    get_pdf_night_mode,
    get_pdf_two_page_spread,
    get_page_number_overlay_font_size,
    get_page_number_overlay_format,
    get_page_number_overlay_opacity,
    get_redaction_preview_opacity,
    get_page_number_overlay_position,
    get_page_number_overlay_skip_edges,
    get_page_number_overlay_start,
    get_ink_smooth,
    get_ink_smooth_passes,
    get_ink_smooth_strength,
    get_measure_labels_persistent,
    get_measure_snap_to_annotation,
    get_measure_unit,
    set_ink_smooth,
    set_ink_smooth_strength,
    INK_SMOOTH_STRENGTH_CHOICES,
    get_show_page_boxes,
    get_show_page_number_overlay,
    get_show_printer_marks,
    set_measure_unit,
    toggle_measure_snap_to_annotation,
    toggle_measure_unit,
    random_ann_palette_color,
    set_ann_color_preset,
    set_ann_default_fill_color,
    set_ann_default_opacity,
    set_ann_highlight_color,
    set_ann_note_color,
    set_ann_pen_color,
    set_ann_layer_type_visible,
    set_ann_layer_types_visible,
    set_annotations_locked,
    set_annotations_visible,
    set_page_number_overlay_font_size,
    set_page_number_overlay_format,
    set_page_number_overlay_opacity,
    set_redaction_preview_opacity,
    set_page_number_overlay_position,
    set_page_number_overlay_skip_edges,
    set_page_number_overlay_start,
    set_pdf_continuous_scroll,
    set_pdf_grayscale,
    set_pdf_night_mode,
    set_pdf_two_page_spread,
    set_show_page_boxes,
    set_show_page_number_overlay,
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
    """Stempel-Bibliothek: Text-Presets (+ Datum) und Link zur Bild-Bibliothek — 1.9.0."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Stempel")
        self.resize(400, 360)
        from PySide6.QtWidgets import QCheckBox, QListWidget, QPushButton

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
        self.btn_images = QPushButton("Eigene Stempel-Bilder…")
        self.btn_images.setToolTip(
            "Stempel-Bildbibliothek verwalten (Ordner) und als Sidecar-Stempel setzen — 1.9.0"
        )
        self.btn_images.clicked.connect(self._open_image_library)
        layout.addWidget(self.btn_images)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._items: list[tuple[str, str]] = []  # display, (text, color) encoded
        self._image_placed = False
        self._rebuild()

    def _open_image_library(self) -> None:
        from instantlensdoc.ui.stamp_library_dialog import StampLibraryDialog

        parent = self.parent()
        pdf_path = None
        page_index = 0
        if parent is not None and hasattr(parent, "pdf_path"):
            pdf_path = getattr(parent, "pdf_path", None)
            page_index = int(getattr(parent, "page_index", 0) or 0)
        dlg = StampLibraryDialog(
            self,
            pdf_path=pdf_path,
            page_index=page_index,
            allow_place=bool(pdf_path),
        )
        if dlg.exec() == QDialog.Accepted and dlg.placed_path:
            self._image_placed = True
            self.accept()

    def image_placed(self) -> bool:
        return bool(getattr(self, "_image_placed", False))

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
        if getattr(self, "_image_placed", False):
            return None
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
    ink_finished = Signal(object)  # list[(x,y)] Freihand-Polyline — 2.2.0
    text_selection_finished = Signal(float, float, float, float)  # Text-Marquee (Auswahl-Modus)
    overlay_edit_requested = Signal(str)  # ann id
    annotation_selected = Signal(str)  # ann id (leer = Auswahl aufheben)
    uri_link_clicked = Signal(str)  # externe http(s)-URL
    annotations_moved = Signal(list, float, float)  # ids, dx, dy
    escape_pressed = Signal()  # Esc → z. B. Quick-Stempel abbrechen — 1.9.3

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
        self._ink_points: list[tuple[float, float]] | None = None  # Freihand — 2.2.0
        self._ink_preview_color: str = "#2980B9"  # Strichfarbe Vorschau — 2.2.1
        self._ink_preview_stroke: float = 2.0  # Strichstärke Vorschau — 2.2.1
        self._text_sel_start: tuple[float, float] | None = None
        self._text_sel_current: tuple[float, float] | None = None
        self._scale = 1.5
        self._search_rects: list[tuple[float, float, float, float]] = []
        self._search_active: int = -1
        self._selected_id: str | None = None
        self._selected_ids: set[str] = set()
        self._annotations_visible = True
        self._ann_type_visible: dict[str, bool] = {
            "highlight": True,
            "note": True,
            "shape": True,
            "redaction": True,
        }
        self._annotations_locked = False
        self._show_page_boxes = False
        self._show_page_number_overlay = False
        self._page_number_text = ""
        self._page_number_overlay_opacity = 0.59
        self._page_number_overlay_font_size = 11
        self._page_number_overlay_position = "bottom-center"
        self._page_number_overlay_format = "{page} / {pages}"
        self._redaction_preview_opacity = 0.90
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

    def set_redaction_preview_opacity(self, opacity: float):
        try:
            op = float(opacity)
        except (TypeError, ValueError):
            op = 0.90
        self._redaction_preview_opacity = max(0.05, min(1.0, op))
        self.update()

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

    def set_ann_type_visible(self, visible: dict[str, bool] | None):
        """Typ-Gruppen-Sichtbarkeit (highlight/note/shape/redaction) — 1.8.0."""
        base = {
            "highlight": True,
            "note": True,
            "shape": True,
            "redaction": True,
        }
        if visible:
            for k, v in visible.items():
                if k in base:
                    base[k] = bool(v)
        self._ann_type_visible = base
        self._repaint_overlay()

    def ann_type_visible(self) -> dict[str, bool]:
        return dict(self._ann_type_visible)

    @staticmethod
    def ann_type_group(ann_type) -> str:
        """AnnotationType → Layer-Gruppe — 1.8.0."""
        try:
            t = ann_type if isinstance(ann_type, AnnotationType) else AnnotationType(str(ann_type))
        except Exception:
            return "shape"
        if t in (AnnotationType.HIGHLIGHT, AnnotationType.UNDERLINE):
            return "highlight"
        if t in (
            AnnotationType.STICKY,
            AnnotationType.TEXT,
            AnnotationType.CALLOUT,
            AnnotationType.TEXT_OVERLAY,
        ):
            return "note"
        if t == AnnotationType.REDACTION:
            return "redaction"
        return "shape"

    def _ann_type_is_visible(self, ann: Annotation) -> bool:
        if not self._annotations_visible:
            return False
        group = self.ann_type_group(ann.type)
        return bool(self._ann_type_visible.get(group, True))

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

    def set_show_page_number_overlay(self, enabled: bool):
        self._show_page_number_overlay = bool(enabled)
        self._repaint_overlay()

    def show_page_number_overlay(self) -> bool:
        return bool(self._show_page_number_overlay)

    def set_page_number_text(self, text: str | None):
        self._page_number_text = str(text or "").strip()
        if self._show_page_number_overlay:
            self._repaint_overlay()

    def set_page_number_overlay_opacity(self, opacity: float):
        try:
            op = float(opacity)
        except (TypeError, ValueError):
            op = 0.59
        self._page_number_overlay_opacity = max(0.05, min(1.0, op))
        if self._show_page_number_overlay:
            self._repaint_overlay()

    def page_number_overlay_opacity(self) -> float:
        return float(self._page_number_overlay_opacity)

    def set_page_number_overlay_font_size(self, size: int):
        try:
            sz = int(size)
        except (TypeError, ValueError):
            sz = 11
        self._page_number_overlay_font_size = max(8, min(36, sz))
        if self._show_page_number_overlay:
            self._repaint_overlay()

    def page_number_overlay_font_size(self) -> int:
        return int(self._page_number_overlay_font_size)

    def set_page_number_overlay_position(self, position: str):
        raw = str(position or "bottom-center").strip().lower().replace("_", "-")
        self._page_number_overlay_position = (
            "top-center" if raw in ("top-center", "top", "oben", "oben-mitte") else "bottom-center"
        )
        if self._show_page_number_overlay:
            self._repaint_overlay()

    def page_number_overlay_position(self) -> str:
        return str(self._page_number_overlay_position or "bottom-center")

    def set_page_number_overlay_format(self, fmt: str):
        text = str(fmt or "").strip() or "{page} / {pages}"
        if len(text) > 80:
            text = text[:80]
        self._page_number_overlay_format = text
        if self._show_page_number_overlay:
            self._repaint_overlay()

    def page_number_overlay_format(self) -> str:
        return str(self._page_number_overlay_format or "{page} / {pages}")

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
            self._ink_points = None
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
            if not self._ann_type_is_visible(ann):
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
            AnnotationType.MEASURE_ANGLE,
            AnnotationType.CALLOUT,
        ):
            x2, y2 = ann.end_point()
            xs = [ann.x, x2]
            ys = [ann.y, y2]
            if ann.type == AnnotationType.MEASURE_ANGLE:
                x3 = float(ann.p3_x) if (ann.p3_x or ann.p3_y) else float(ann.x + ann.width)
                y3 = float(ann.p3_y) if (ann.p3_x or ann.p3_y) else float(ann.y)
                xs.append(x3)
                ys.append(y3)
            if ann.type == AnnotationType.CALLOUT:
                xs.extend([ann.x + max(ann.width, 100), ann.x])
                ys.extend([ann.y + max(ann.height, 40), ann.y])
            pad = 6.0
            return min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad
        if ann.type == AnnotationType.INK:
            pts = getattr(ann, "ink_points", lambda: [])()
            if pts:
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
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
            if not self._ann_type_is_visible(ann):
                continue
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
        try:
            stroke_w = float(getattr(ann, "stroke_width", 2.0) or 2.0)
        except (TypeError, ValueError):
            stroke_w = 2.0
        stroke_w = max(1.0, min(12.0, stroke_w))
        pen_c = QColor(ann.color)
        pen_c.setAlpha(_a(255))
        pen = QPen(pen_c)
        pen.setWidthF(stroke_w)
        painter.setPen(pen)
        x, y = int(ann.x + dx), int(ann.y + dy)
        w, h = int(ann.width), int(ann.height)

        if ann.type == AnnotationType.HIGHLIGHT:
            painter.fillRect(x, y, w, h, color)
        elif ann.type == AnnotationType.REDACTION:
            rw, rh = max(w, 4), max(h, 4)
            try:
                preview_op = float(
                    getattr(self, "_redaction_preview_opacity", 0.90) or 0.90
                )
            except (TypeError, ValueError):
                preview_op = 0.90
            preview_op = max(0.05, min(1.0, preview_op))
            base_a = int(round(255 * preview_op))
            painter.fillRect(x, y, rw, rh, QColor(0, 0, 0, _a(base_a)))
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
                        # Signatur-Deckkraft über painter.setOpacity — 1.5.1
                        painter.setOpacity(opacity)
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
        elif ann.type in (AnnotationType.RECTANGLE, AnnotationType.MEASURE_AREA):
            fill_src = str(getattr(ann, "fill_color", "") or "").strip() or ann.color
            painter.setBrush(QColor(fill_src if fill_src else ann.color))
            c = QColor(fill_src if fill_src else ann.color)
            c.setAlpha(_a(40 if not str(getattr(ann, "fill_color", "") or "").strip() else 90))
            painter.fillRect(x, y, w, h, c)
            painter.drawRect(x, y, w, h)
            if ann.type == AnnotationType.MEASURE_AREA:
                try:
                    from instantlensdoc.core.app_settings import get_measure_unit as _gmu

                    unit = _gmu()
                except Exception:
                    unit = "mm"
                label = ann.text or ann.measure_label(self._scale, unit=unit)
                painter.drawText(x + 4, y + 14, label)
        elif ann.type == AnnotationType.MEASURE_ANGLE:
            x2, y2 = ann.end_point()
            x2, y2 = x2 + dx, y2 + dy
            x3 = (float(ann.p3_x) if (ann.p3_x or ann.p3_y) else float(ann.x + ann.width)) + dx
            y3 = (float(ann.p3_y) if (ann.p3_x or ann.p3_y) else float(ann.y)) + dy
            painter.drawLine(x, y, int(x2), int(y2))
            painter.drawLine(int(x2), int(y2), int(x3), int(y3))
            label = ann.text or ann.measure_label(self._scale)
            painter.drawText(int(x2) + 4, int(y2) - 4, label)
        elif ann.type in (AnnotationType.LINE, AnnotationType.ARROW, AnnotationType.MEASURE):
            x2, y2 = ann.end_point()
            x2, y2 = x2 + dx, y2 + dy
            painter.drawLine(x, y, int(x2), int(y2))
            if ann.type == AnnotationType.ARROW:
                self._draw_arrow_head(painter, float(x), float(y), x2, y2)
            if ann.type == AnnotationType.MEASURE:
                mid_x = (x + x2) / 2
                mid_y = (y + y2) / 2
                try:
                    from instantlensdoc.core.app_settings import get_measure_unit as _gmu2

                    unit = _gmu2()
                except Exception:
                    unit = "mm"
                label = ann.text or ann.measure_label(self._scale, unit=unit)
                painter.drawText(int(mid_x) + 4, int(mid_y) - 4, label)
        elif ann.type == AnnotationType.INK:
            # Freihand-Polyline (Maus) — 2.2.0
            pts = [
                QPointF(float(pt[0]) + dx, float(pt[1]) + dy)
                for pt in (getattr(ann, "points", None) or [])
                if isinstance(pt, (list, tuple)) and len(pt) >= 2
            ]
            if len(pts) >= 2:
                painter.drawPolyline(QPolygonF(pts))
            elif len(pts) == 1:
                painter.drawPoint(pts[0])
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
        # Optional: Seitennummer-Overlay (HUD unten-/oben-mitte)
        if self._show_page_number_overlay and self._page_number_text:
            label = self._page_number_text
            font = QFont()
            try:
                pt = int(self._page_number_overlay_font_size)
            except (TypeError, ValueError, AttributeError):
                pt = 11
            font.setPointSize(max(8, min(36, pt)))
            font.setBold(True)
            painter.setFont(font)
            metrics = painter.fontMetrics()
            tw = metrics.horizontalAdvance(label) + 16
            th = metrics.height() + 10
            px = max(8, (pm.width() - tw) // 2)
            pos = str(
                getattr(self, "_page_number_overlay_position", "bottom-center") or "bottom-center"
            ).lower()
            if pos in ("top-center", "top", "oben", "oben-mitte"):
                py = 12
            else:
                py = max(8, pm.height() - th - 12)
            try:
                op = float(self._page_number_overlay_opacity)
            except (TypeError, ValueError, AttributeError):
                op = 0.59
            op = max(0.05, min(1.0, op))
            bg_a = max(20, min(255, int(round(255 * op))))
            fg_a = max(80, min(255, int(round(255 * min(1.0, op + 0.25)))))
            painter.fillRect(px, py, tw, th, QColor(20, 20, 20, bg_a))
            painter.setPen(QPen(QColor(255, 255, 255, fg_a)))
            painter.drawText(px + 8, py + th - 8, label)
        move_dx, move_dy = self._move_delta if self._move_origin is not None else (0.0, 0.0)
        if self._annotations_visible:
            for ann in self._annotations:
                if not self._ann_type_is_visible(ann):
                    continue
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
        if self._ink_points and len(self._ink_points) >= 1 and self._drag_tool == AnnotationType.INK:
            preview = Annotation(
                page=0,
                type=AnnotationType.INK,
                x=0,
                y=0,
                points=[[p[0], p[1]] for p in self._ink_points],
                color=str(getattr(self, "_ink_preview_color", None) or "#2980B9"),
                stroke_width=float(getattr(self, "_ink_preview_stroke", 2.0) or 2.0),
            )
            preview.sync_bounds_from_points()
            self._draw_ann(painter, preview)
        elif self._drag_start and self._drag_current and self._drag_tool:
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
                try:
                    from instantlensdoc.core.app_settings import get_measure_unit as _gmu3

                    unit = _gmu3()
                except Exception:
                    unit = "mm"
                preview.text = preview.measure_label(self._scale, unit=unit)
            if self._drag_tool == AnnotationType.MEASURE_AREA:
                try:
                    from instantlensdoc.core.app_settings import get_measure_unit as _gmu4

                    unit = _gmu4()
                except Exception:
                    unit = "mm"
                preview.text = preview.measure_label(self._scale, unit=unit)
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
                shift = bool(event.modifiers() & Qt.ShiftModifier)
                if shift:
                    # Mehrfachauswahl umschalten — kein Verschieben
                    self.annotation_selected.emit(hit_any.id)
                    return
                # Bereits ausgewählt → Mehrfachauswahl behalten und gemeinsam verschieben
                if hit_any.id in self._selected_ids:
                    ids = set(self._selected_ids)
                else:
                    self.annotation_selected.emit(hit_any.id)
                    ids = set(self._selected_ids) if self._selected_ids else {hit_any.id}
                if not self._annotations_locked:
                    # Gesperrte Gruppenmitglieder nicht mitverschieben
                    by_id = {a.id: a for a in self._annotations}
                    movable = {
                        i
                        for i in ids
                        if not bool(getattr(by_id.get(i), "locked", False))
                    }
                    if movable:
                        self._move_ids = movable
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
            if self._drag_tool == AnnotationType.INK:
                # Freihand: Punkte sammeln — 2.2.0
                self._ink_points = [(x, y)]
                self._drag_start = (x, y)
                self._drag_current = (x, y)
                return
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
        if self._ink_points is not None:
            pt = self._map_to_page(event)
            if pt:
                lx, ly = self._ink_points[-1]
                if abs(pt[0] - lx) >= 1.5 or abs(pt[1] - ly) >= 1.5:
                    self._ink_points.append(pt)
                    self._drag_current = pt
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
            ):
                hit = self._hit_annotation(*pt)
                if hit and not bool(getattr(hit, "locked", False)):
                    self.setCursor(QCursor(Qt.OpenHandCursor))
                else:
                    self.unsetCursor()
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
        if self._ink_points is not None and event.button() == Qt.LeftButton:
            pt = self._map_to_page(event)
            if pt:
                lx, ly = self._ink_points[-1]
                if abs(pt[0] - lx) >= 0.5 or abs(pt[1] - ly) >= 0.5:
                    self._ink_points.append(pt)
            pts = list(self._ink_points)
            self._ink_points = None
            self._drag_start = None
            self._drag_current = None
            if len(pts) >= 2:
                self.ink_finished.emit(pts)
            else:
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

    def keyPressEvent(self, event):  # noqa: N802
        """Esc bricht Quick-Stempel-Platzieren ab — 1.9.3."""
        if event.key() == Qt.Key_Escape:
            viewer = self.parent()
            while viewer is not None and not hasattr(viewer, "cancel_quick_stamp"):
                viewer = viewer.parent()
            if viewer is not None and getattr(viewer, "_quick_stamp_armed", False):
                viewer.cancel_quick_stamp()
                event.accept()
                return
            self.escape_pressed.emit()
        super().keyPressEvent(event)


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
    page_number_overlay_changed = Signal(bool)
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
        # Winkel: nach erstem Drag (Strahl 1) zweiter Klick setzt p3 — 2.1.0
        self._pending_angle: tuple[float, float, float, float, int] | None = None
        self._quick_stamp_armed: bool = False  # Quick-Stempel ohne Dialog — 1.9.2
        self._quick_stamp_payload: dict | None = None
        self._zoom_timer = QTimer(self)
        self._zoom_timer.setSingleShot(True)
        self._zoom_timer.setInterval(120)
        self._zoom_timer.timeout.connect(self._apply_pending_zoom)
        self._pending_scale: float | None = None
        # Sidecar-Save Debounce: schnelle Ann.-Edits bündeln (Intervall in Settings)
        from instantlensdoc.core.app_settings import get_sidecar_save_debounce_ms

        self._sidecar_save_timer = QTimer(self)
        self._sidecar_save_timer.setSingleShot(True)
        self._sidecar_save_timer.setInterval(get_sidecar_save_debounce_ms())
        self._sidecar_save_timer.timeout.connect(self._flush_sidecar_save)
        self._sidecar_save_pending = False
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
        try:
            from instantlensdoc.core.app_settings import get_ann_default_stroke_width

            self._default_stroke_width = float(get_ann_default_stroke_width())
        except Exception:
            self._default_stroke_width = 2.0
        try:
            self._default_fill_color = get_ann_default_fill_color()
        except Exception:
            self._default_fill_color = "#FFE066"
        self._suppress_default_zoom = False  # Session Zoom pro Tab (0.9.2)
        self._search_case_sensitive = False
        self._search_whole_word = False
        self._search_regex = False
        self._annotations_visible = get_annotations_visible()
        self._annotations_locked = get_annotations_locked()
        self._show_page_boxes = get_show_page_boxes()
        self._show_page_number_overlay = get_show_page_number_overlay()
        self._page_number_overlay_opacity = get_page_number_overlay_opacity()
        self._page_number_overlay_font_size = get_page_number_overlay_font_size()
        self._page_number_overlay_position = get_page_number_overlay_position()
        self._page_number_overlay_format = get_page_number_overlay_format()
        self._page_number_overlay_start = get_page_number_overlay_start()
        self._page_number_overlay_skip_edges = get_page_number_overlay_skip_edges()
        self._redaction_preview_opacity = get_redaction_preview_opacity()
        self._show_printer_marks = get_show_printer_marks()
        self._search_query = ""
        self._search_rects: list[tuple[float, float, float, float]] = []
        self._search_index = -1
        self._selected_ann_id: str | None = None
        self._selected_ann_ids: set[str] = set()
        self._ann_clipboard: list[dict] = []
        self._page_ops_undo: list[dict] = []  # Seiten-Löschen/Drehen/Duplizieren rückgängig
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
        btn_fit.setToolTip("Seite einpassen / Fit-Page (Ctrl+0)")
        btn_fit.clicked.connect(self.fit_page)
        btn_fit_w = QPushButton("Breite")
        btn_fit_w.setToolTip("Seitenbreite einpassen / Fit-Width (Ctrl+9)")
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
        btn_hist.setToolTip(
            "PDF-Undo-Stack: Seiten-Ops + Annotationen (z. B. Tag umbenennen) wiederherstellen"
        )
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
        self.btn_ann_stroke = QPushButton("Strich…")
        self.btn_ann_stroke.setToolTip(
            "Strichfarbe des ausgewählten Shapes ändern (getrennt von Füllung; "
            "Commit + Undo) — 0.9.4"
        )
        self.btn_ann_stroke.clicked.connect(self.recolor_stroke_selected_annotations)
        # Alias: ältere Menü-/Shortcut-Pfade nutzen weiterhin Farbe…
        btn_ann_color = self.btn_ann_stroke
        self.btn_ann_fill = QPushButton("Füllung…")
        self.btn_ann_fill.setToolTip(
            "Füllfarbe des ausgewählten Shapes ändern (Commit + Undo) — 0.9.3"
        )
        self.btn_ann_fill.clicked.connect(self.recolor_fill_selected_annotations)
        btn_ann_opacity = QPushButton("α…")
        btn_ann_opacity.setToolTip(
            "Deckkraft der ausgewählten Annotation(en) ändern (Batch, Ctrl+Alt+Shift+O)"
        )
        btn_ann_opacity.clicked.connect(self.set_opacity_selected_annotations)
        btn_align_l = QPushButton("⫷")
        btn_align_l.setFixedWidth(28)
        btn_align_l.setToolTip("Auswahl links ausrichten (≥2 Annotationen)")
        btn_align_l.clicked.connect(lambda: self.align_selected_annotations("left"))
        btn_align_c = QPushButton("⫸⫷")
        btn_align_c.setFixedWidth(36)
        btn_align_c.setToolTip("Auswahl horizontal zentrieren (≥2 Annotationen)")
        btn_align_c.clicked.connect(lambda: self.align_selected_annotations("center"))
        btn_align_r = QPushButton("⫸")
        btn_align_r.setFixedWidth(28)
        btn_align_r.setToolTip("Auswahl rechts ausrichten (≥2 Annotationen)")
        btn_align_r.clicked.connect(lambda: self.align_selected_annotations("right"))
        btn_align_t = QPushButton("⬆")
        btn_align_t.setFixedWidth(28)
        btn_align_t.setToolTip("Auswahl oben ausrichten (≥2 Annotationen)")
        btn_align_t.clicked.connect(lambda: self.align_selected_annotations("top"))
        btn_align_m = QPushButton("⬍")
        btn_align_m.setFixedWidth(28)
        btn_align_m.setToolTip("Auswahl vertikal mittig ausrichten (≥2 Annotationen)")
        btn_align_m.clicked.connect(lambda: self.align_selected_annotations("middle"))
        btn_align_b = QPushButton("⬇")
        btn_align_b.setFixedWidth(28)
        btn_align_b.setToolTip("Auswahl unten ausrichten (≥2 Annotationen)")
        btn_align_b.clicked.connect(lambda: self.align_selected_annotations("bottom"))
        btn_dist_h = QPushButton("⇔")
        btn_dist_h.setFixedWidth(28)
        btn_dist_h.setToolTip(
            "Auswahl horizontal verteilen (≥3 Annotationen; Ränder bleiben)"
        )
        btn_dist_h.clicked.connect(self.distribute_selected_annotations_horizontal)
        btn_dist_v = QPushButton("⇕")
        btn_dist_v.setFixedWidth(28)
        btn_dist_v.setToolTip(
            "Auswahl vertikal verteilen (≥3 Annotationen; Ränder bleiben)"
        )
        btn_dist_v.clicked.connect(self.distribute_selected_annotations_vertical)
        btn_group = QPushButton("Grp")
        btn_group.setFixedWidth(28)
        btn_group.setToolTip(
            "Auswahl gruppieren (≥2) — temporäre Gruppen-ID im Sidecar"
        )
        btn_group.clicked.connect(self.group_selected_annotations)
        btn_ungroup = QPushButton("⧉")
        btn_ungroup.setFixedWidth(28)
        btn_ungroup.setToolTip("Auswahl entgruppieren (group_id leeren)")
        btn_ungroup.clicked.connect(self.ungroup_selected_annotations)
        btn_group_lock = QPushButton("🔒")
        btn_group_lock.setFixedWidth(28)
        btn_group_lock.setToolTip(
            "Gruppen-Sperre umschalten — Mitglieder der Auswahl nicht verschiebbar"
        )
        btn_group_lock.clicked.connect(self.toggle_selected_group_lock)
        btn_group_edit = QPushButton("🏷")
        btn_group_edit.setFixedWidth(28)
        btn_group_edit.setToolTip(
            "Ann.-Gruppe umbenennen / Farbe (Sidecar-Markierung)"
        )
        btn_group_edit.clicked.connect(self.edit_selected_ann_group)
        btn_stamp_rot = QPushButton("Stempel ↻")
        btn_stamp_rot.setToolTip("Ausgewählten Stempel um 90° drehen")
        btn_stamp_rot.clicked.connect(lambda: self.rotate_selected_stamp(90))
        self.btn_quick_stamp = QPushButton("Quick-Stempel")
        self.btn_quick_stamp.setObjectName("btnQuickStamp")
        self.btn_quick_stamp.setToolTip(
            "Links: zuletzt/Standard platzieren · Rechtsklick: Bibliothek wählen · "
            "Esc → Abbruch + Fokus Toolbar · Ctrl+Shift+S = Standard-Stempel ★ — 1.9.5"
        )
        self.btn_quick_stamp.setContextMenuPolicy(Qt.CustomContextMenu)
        self.btn_quick_stamp.clicked.connect(lambda: self.arm_quick_stamp())
        self.btn_quick_stamp.customContextMenuRequested.connect(
            self._quick_stamp_context_menu
        )
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
            (AnnotationType.MEASURE_AREA, "Fläche"),
            (AnnotationType.MEASURE_ANGLE, "Winkel"),
            (AnnotationType.INK, "Freihand"),
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
            elif t == AnnotationType.MEASURE_AREA:
                b.setToolTip("Fläche: Rechteck aufziehen — Anzeige mm²/px² (Toggle mm/px) — 2.1.0")
            elif t == AnnotationType.MEASURE_ANGLE:
                b.setToolTip(
                    "Winkel: ersten Strahl ziehen, dann zweiten Endpunkt klicken — 2.1.0"
                )
            elif t == AnnotationType.MEASURE:
                b.setToolTip("Lineal: Distanz ziehen — Anzeige mm/px (Toggle) — 2.1.0")
            elif t == AnnotationType.INK:
                b.setToolTip(
                    "Freihand: Maus-Polyline; Strichstärke/Farbe (Stift+Slider); "
                    "optional Glätten — 2.2.1 (kein Stylus/Druck)"
                )
            b.clicked.connect(lambda checked, tool=t: self._set_tool(tool))
            self._tool_buttons.append(b)
            toolbar.addWidget(b)

        self.btn_ink_smooth = QToolButton()
        self.btn_ink_smooth.setText("Glätten")
        self.btn_ink_smooth.setCheckable(True)
        self.btn_ink_smooth.setChecked(get_ink_smooth())
        self.btn_ink_smooth.setToolTip(
            "Freihand: Glättung optional; Stärke daneben — 2.2.3 (kein Stylus)"
        )
        self.btn_ink_smooth.clicked.connect(self._toggle_ink_smooth)
        toolbar.addWidget(self.btn_ink_smooth)

        self.cmb_ink_smooth_strength = QComboBox()
        self.cmb_ink_smooth_strength.setObjectName("inkSmoothStrength")
        self.cmb_ink_smooth_strength.setMaximumWidth(90)
        cur_str = get_ink_smooth_strength()
        pick_str = 0
        for i, (key, label) in enumerate(INK_SMOOTH_STRENGTH_CHOICES):
            self.cmb_ink_smooth_strength.addItem(label, key)
            if key == cur_str:
                pick_str = i
        self.cmb_ink_smooth_strength.setCurrentIndex(pick_str)
        self.cmb_ink_smooth_strength.setToolTip(
            "Glättungsstärke: Leicht / Mittel / Stark (passes 1–3) — 2.2.3"
        )
        self.cmb_ink_smooth_strength.currentIndexChanged.connect(
            self._on_ink_smooth_strength_changed
        )
        toolbar.addWidget(self.cmb_ink_smooth_strength)

        self.btn_ink_undo_stroke = QToolButton()
        self.btn_ink_undo_stroke.setText("Ink−")
        self.btn_ink_undo_stroke.setToolTip(
            "Letzten Freihand-Strich löschen (Undo-fähig) — 2.2.1"
        )
        self.btn_ink_undo_stroke.clicked.connect(self.delete_last_ink_stroke)
        toolbar.addWidget(self.btn_ink_undo_stroke)

        self.btn_measure_unit = QToolButton()
        self.btn_measure_unit.setText(f"Maß:{get_measure_unit()}")
        self.btn_measure_unit.setToolTip(
            "Messanzeige-Einheit umschalten (mm ↔ px); Labels werden aktualisiert — 2.1.1"
        )
        self.btn_measure_unit.clicked.connect(self._toggle_measure_unit)
        toolbar.addWidget(self.btn_measure_unit)

        self.btn_measure_snap = QToolButton()
        self.btn_measure_snap.setText("Snap")
        self.btn_measure_snap.setCheckable(True)
        self.btn_measure_snap.setChecked(get_measure_snap_to_annotation())
        self.btn_measure_snap.setToolTip(
            "Mess-Endpunkte optional an Annotation-Ecken snappen — 2.1.1"
        )
        self.btn_measure_snap.clicked.connect(self._toggle_measure_snap)
        toolbar.addWidget(self.btn_measure_snap)

        self.btn_hl_color = QPushButton("HL")
        self.btn_hl_color.setToolTip("Highlight-Farbe")
        self.btn_hl_color.setFixedWidth(36)
        self.btn_hl_color.clicked.connect(self._pick_highlight_color)
        self._style_color_btn(self.btn_hl_color, self._highlight_color)
        self.btn_pen_color = QPushButton("Stift")
        self.btn_pen_color.setToolTip(
            "Stift-Farbe (Linie/Pfeil/Rechteck/Unterstreichen/Freihand) — 2.2.1"
        )
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
            "Deckkraft: bei Auswahl → ausgewähltes Objekt; sonst Standard für neue Ann."
        )
        self.spin_opacity.valueChanged.connect(self._on_default_opacity_changed)
        # Toolbar-Slider (0.05–1.0 als 5–100 %) — ausgewähltes Objekt oder Standard
        # Undo erst bei Loslassen (Commit on release) — 0.9.1
        self.slider_opacity = QSlider(Qt.Horizontal)
        self.slider_opacity.setRange(5, 100)
        self.slider_opacity.setSingleStep(5)
        self.slider_opacity.setPageStep(10)
        self.slider_opacity.setFixedWidth(88)
        self.slider_opacity.setValue(int(round(self._default_opacity * 100)))
        self.slider_opacity.setToolTip(
            "Opacity-Slider: Deckkraft des ausgewählten Objekts; ohne Auswahl → Standard "
            "(Undo beim Loslassen)"
        )
        self._opacity_slider_dragging = False
        self._opacity_slider_undo_pushed = False
        self._opacity_slider_prev_recording = True
        self.slider_opacity.sliderPressed.connect(self._on_opacity_slider_pressed)
        self.slider_opacity.sliderReleased.connect(self._on_opacity_slider_released)
        self.slider_opacity.valueChanged.connect(self._on_opacity_slider_changed)
        # Stroke-Width Slider für ausgewähltes Shape — Commit on release + Undo (0.9.2)
        self.slider_stroke = QSlider(Qt.Horizontal)
        self.slider_stroke.setRange(1, 12)
        self.slider_stroke.setSingleStep(1)
        self.slider_stroke.setPageStep(2)
        self.slider_stroke.setFixedWidth(72)
        self.slider_stroke.setValue(int(round(self._default_stroke_width)))
        self.slider_stroke.setToolTip(
            "Strichstärke (px) des ausgewählten Shapes; ohne Auswahl → Standard "
            "(Undo beim Loslassen)"
        )
        self._stroke_slider_dragging = False
        self._stroke_slider_undo_pushed = False
        self._stroke_slider_prev_recording = True
        self.slider_stroke.sliderPressed.connect(self._on_stroke_slider_pressed)
        self.slider_stroke.sliderReleased.connect(self._on_stroke_slider_released)
        self.slider_stroke.valueChanged.connect(self._on_stroke_slider_changed)
        self.lbl_stroke = QLabel(f"Strich {int(round(self._default_stroke_width))}")
        self.lbl_stroke.setFixedWidth(52)
        self.lbl_stroke.setToolTip("Aktuelle Strichstärke in Pixel")
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
        self.btn_page_num = QToolButton()
        self.btn_page_num.setText("Nr.")
        self.btn_page_num.setCheckable(True)
        self.btn_page_num.setChecked(self._show_page_number_overlay)
        self.btn_page_num.setToolTip(
            "Seitennummer als Overlay auf der PDF-Seite anzeigen (Einstellungen)"
        )
        self.btn_page_num.toggled.connect(self.set_show_page_number_overlay)
        self.spin_page_num_opacity = QDoubleSpinBox()
        self.spin_page_num_opacity.setRange(0.05, 1.0)
        self.spin_page_num_opacity.setSingleStep(0.05)
        self.spin_page_num_opacity.setDecimals(2)
        self.spin_page_num_opacity.setValue(self._page_number_overlay_opacity)
        self.spin_page_num_opacity.setPrefix("Nr α ")
        self.spin_page_num_opacity.setFixedWidth(88)
        self.spin_page_num_opacity.setToolTip(
            "Deckkraft des Seitennummer-Overlays (Einstellungen)"
        )
        self.spin_page_num_opacity.valueChanged.connect(
            self.set_page_number_overlay_opacity
        )
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
        # Color-Presets Quick-Bar: 6 Farben Stroke/Fill + Undo (0.9.5)
        from instantlensdoc.core.app_settings import ANN_COLOR_PRESET_COUNT

        self._preset_btns: list[QPushButton] = []
        for i in range(ANN_COLOR_PRESET_COUNT):
            pb = QPushButton(str(i + 1))
            pb.setFixedWidth(22)
            pb.setToolTip(
                f"Preset {i + 1}: Auswahl → Strich · Shift → Füllung (Undo); "
                "ohne Auswahl → Highlight · Shift=Stift · Ctrl=Notiz; "
                "Rechtsklick: speichern / zurücksetzen — 0.9.6"
            )
            pb.clicked.connect(lambda checked=False, idx=i: self._apply_color_preset(idx))
            pb.setContextMenuPolicy(Qt.CustomContextMenu)
            pb.customContextMenuRequested.connect(
                lambda pos, idx=i, btn=pb: self._color_preset_context_menu(btn, idx, pos)
            )
            self._preset_btns.append(pb)
            toolbar.addWidget(pb)
        self._refresh_preset_btns()
        toolbar.addWidget(self.spin_opacity)
        toolbar.addWidget(self.slider_opacity)
        toolbar.addWidget(self.lbl_stroke)
        toolbar.addWidget(self.slider_stroke)
        toolbar.addWidget(self.btn_grayscale)
        toolbar.addWidget(self.btn_night)
        toolbar.addWidget(self.btn_spread)
        toolbar.addWidget(self.btn_continuous)
        toolbar.addWidget(self.btn_ann_layer)
        toolbar.addWidget(self.btn_ann_lock)
        toolbar.addWidget(self.btn_page_boxes)
        toolbar.addWidget(self.btn_page_num)
        toolbar.addWidget(self.spin_page_num_opacity)
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
        toolbar.addWidget(self.btn_ann_stroke)
        toolbar.addWidget(self.btn_ann_fill)
        toolbar.addWidget(btn_ann_opacity)
        toolbar.addWidget(btn_align_l)
        toolbar.addWidget(btn_align_c)
        toolbar.addWidget(btn_align_r)
        toolbar.addWidget(btn_align_t)
        toolbar.addWidget(btn_align_m)
        toolbar.addWidget(btn_align_b)
        toolbar.addWidget(btn_dist_h)
        toolbar.addWidget(btn_dist_v)
        toolbar.addWidget(btn_group)
        toolbar.addWidget(btn_ungroup)
        toolbar.addWidget(btn_group_lock)
        toolbar.addWidget(btn_group_edit)
        toolbar.addWidget(btn_stamp_rot)
        toolbar.addWidget(self.btn_quick_stamp)
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
                self.lbl_stroke,
                self.slider_stroke,
            ],
            "view": [
                self.btn_grayscale,
                self.btn_night,
                self.btn_spread,
                self.btn_continuous,
                self.btn_ann_layer,
                self.btn_ann_lock,
                self.btn_page_boxes,
                self.btn_page_num,
                self.spin_page_num_opacity,
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
                self.btn_ann_fill,
                btn_ann_opacity,
                btn_align_l,
                btn_align_c,
                btn_align_r,
                btn_align_t,
                btn_align_m,
                btn_align_b,
                btn_dist_h,
                btn_dist_v,
                btn_group,
                btn_ungroup,
                btn_group_lock,
                btn_group_edit,
                btn_stamp_rot,
                self.btn_quick_stamp,
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
        self.canvas.set_ann_type_visible(get_ann_layer_types_visible())
        self.canvas.set_annotations_locked(self._annotations_locked)
        self.canvas.set_show_page_boxes(self._show_page_boxes)
        self.canvas.set_show_page_number_overlay(self._show_page_number_overlay)
        self.canvas.set_page_number_overlay_opacity(self._page_number_overlay_opacity)
        self.canvas.set_page_number_overlay_font_size(self._page_number_overlay_font_size)
        self.canvas.set_page_number_overlay_position(self._page_number_overlay_position)
        self.canvas.set_page_number_overlay_format(self._page_number_overlay_format)
        self.canvas.set_redaction_preview_opacity(self._redaction_preview_opacity)
        self.canvas.set_show_printer_marks(self._show_printer_marks)
        self.canvas.annotation_placed.connect(self._on_place)
        self.canvas.drag_finished.connect(self._on_drag)
        self.canvas.ink_finished.connect(self._on_ink)
        self._sync_ink_preview_style()
        self.canvas.text_selection_finished.connect(self._on_text_selection)
        self.canvas.overlay_edit_requested.connect(self._edit_overlay)
        self.canvas.annotation_selected.connect(self._on_annotation_selected)
        self.canvas.uri_link_clicked.connect(self._open_uri_link)
        self.canvas.annotations_moved.connect(self._on_annotations_moved)
        self.canvas.escape_pressed.connect(self._on_canvas_escape)
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
        # Standard-Stempel ★ — Ctrl+Shift+S (Speichern unter → Ctrl+Alt+S) — 1.9.5
        std_stamp_sc = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        std_stamp_sc.setContext(Qt.WidgetWithChildrenShortcut)
        std_stamp_sc.activated.connect(self.arm_standard_stamp)

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

    def _sync_ink_preview_style(self) -> None:
        """Freihand-Vorschau: aktuelle Stiftfarbe + Strichstärke — 2.2.1."""
        if not hasattr(self, "canvas") or self.canvas is None:
            return
        self.canvas._ink_preview_color = str(self._pen_color or "#2980B9")
        self.canvas._ink_preview_stroke = float(
            getattr(self, "_default_stroke_width", 2.0) or 2.0
        )
        self.canvas.update()

    def _toggle_ink_smooth(self) -> None:
        """Optionale Freihand-Glättung — 2.2.1/2.2.3."""
        on = bool(self.btn_ink_smooth.isChecked())
        set_ink_smooth(on)
        strength = get_ink_smooth_strength()
        self.status.emit(
            f"Freihand-Glättung {'an' if on else 'aus'}"
            + (f" ({strength})" if on else "")
        )

    def _on_ink_smooth_strength_changed(self, _index: int = 0) -> None:
        """Glättungsstärke persistieren — 2.2.3."""
        data = self.cmb_ink_smooth_strength.currentData()
        val = set_ink_smooth_strength(str(data or "leicht"))
        if self.btn_ink_smooth.isChecked():
            self.status.emit(f"Freihand-Glättung Stärke: {val}")

    def _pick_pen_color(self):
        initial = QColor(self._pen_color)
        color = QColorDialog.getColor(initial, self, "Stift-Farbe")
        if color.isValid():
            self._pen_color = color.name()
            set_ann_pen_color(self._pen_color)
            self._style_color_btn(self.btn_pen_color, self._pen_color)
            self._sync_ink_preview_style()
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
                f"Preset {i + 1}: {c} — Auswahl: Klick=Strich · Shift=Füllung (Undo); "
                "ohne Auswahl: Highlight · Shift=Stift · Ctrl=Notiz; "
                "Rechtsklick: speichern / zurücksetzen — 0.9.6"
            )

    def _selected_annotation_ids(self) -> list[str]:
        ids = list(self._selected_ann_ids) if self._selected_ann_ids else (
            [self._selected_ann_id] if self._selected_ann_id else []
        )
        return [i for i in ids if i]

    def apply_preset_stroke_color(self, color: str) -> int:
        """Strichfarbe für Auswahl setzen (Commit + Undo) — Quick-Bar 0.9.5."""
        if not self.store:
            self.status.emit("Kein PDF geladen")
            return 0
        ids = self._selected_annotation_ids()
        if not ids:
            self.status.emit("Keine Annotation ausgewählt")
            return 0
        c = str(color or "").strip()
        if not c:
            return 0
        if not c.startswith("#"):
            c = "#" + c
        c = c.upper()
        n = self.store.set_stroke_colors(ids, c)
        if n <= 0:
            self.status.emit("Strichfarbe nicht geändert")
            return 0
        try:
            self.schedule_sidecar_save(force=True)
        except Exception as e:
            QMessageBox.warning(self, "Strichfarbe", str(e))
            return 0
        self.refresh()
        self.annotations_changed.emit()
        self.status.emit(f"Strichfarbe {c} für {n} Annotation(en)")
        return n

    def apply_preset_fill_color(self, color: str) -> int:
        """Füllfarbe für Auswahl setzen (Commit + Undo) — Quick-Bar 0.9.5."""
        if not self.store:
            self.status.emit("Kein PDF geladen")
            return 0
        ids = self._selected_annotation_ids()
        if not ids:
            self.status.emit("Keine Annotation ausgewählt")
            return 0
        c = str(color or "").strip()
        if not c:
            return 0
        if not c.startswith("#"):
            c = "#" + c
        c = c.upper()
        n = self.store.set_fill_colors(ids, c)
        if n <= 0:
            self.status.emit("Füllfarbe nicht geändert")
            return 0
        self._default_fill_color = c
        try:
            set_ann_default_fill_color(c)
        except Exception:
            pass
        try:
            self.schedule_sidecar_save(force=True)
        except Exception as e:
            QMessageBox.warning(self, "Füllfarbe", str(e))
            return 0
        self.refresh()
        self.annotations_changed.emit()
        self.status.emit(f"Füllfarbe {c} für {n} Annotation(en)")
        return n

    def _apply_color_preset(self, index: int):
        presets = get_ann_color_presets()
        if index < 0 or index >= len(presets):
            return
        color = presets[index]
        mods = QApplication.keyboardModifiers()
        # Mit Auswahl: Stroke/Fill Quick-Bar (0.9.5)
        if self._selected_annotation_ids() and self.store is not None:
            if mods & Qt.ShiftModifier:
                self.apply_preset_fill_color(color)
            else:
                self.apply_preset_stroke_color(color)
            return
        if mods & Qt.ControlModifier:
            self._note_color = color
            set_ann_note_color(color)
            self._style_color_btn(self.btn_note_color, color)
            self.status.emit(f"Notizfarbe (Preset {index + 1}): {color}")
        elif mods & Qt.ShiftModifier:
            self._pen_color = color
            set_ann_pen_color(color)
            self._style_color_btn(self.btn_pen_color, color)
            self.status.emit(f"Stift-Farbe (Preset {index + 1}): {color}")
        else:
            self._highlight_color = color
            set_ann_highlight_color(color)
            self._style_color_btn(self.btn_hl_color, color)
            self.status.emit(f"Highlight-Farbe (Preset {index + 1}): {color}")

    def _color_preset_context_menu(self, btn: QPushButton, index: int, pos) -> None:
        """Rechtsklick: Preset speichern / auf Standard zurücksetzen — 0.9.6."""
        menu = QMenu(self)
        act_save = menu.addAction("Preset speichern…")
        act_reset = menu.addAction("Preset zurücksetzen")
        chosen = menu.exec(btn.mapToGlobal(pos))
        if chosen == act_save:
            self._save_color_preset(index)
        elif chosen == act_reset:
            self._reset_color_preset(index)

    def _save_color_preset(self, index: int):
        # Bei Auswahl: aktuelle Strichfarbe speichern, sonst Highlight (Settings)
        color = self._highlight_color
        ids = self._selected_annotation_ids()
        if ids and self.store is not None:
            first = self.store.get(ids[0])
            if first and first.color:
                color = first.color
        set_ann_color_preset(index, color)
        self._refresh_preset_btns()
        self.status.emit(f"Preset {index + 1} gespeichert = {color}")

    def _reset_color_preset(self, index: int):
        presets = reset_ann_color_preset(index)
        self._refresh_preset_btns()
        color = presets[index] if 0 <= index < len(presets) else ""
        self.status.emit(f"Preset {index + 1} zurückgesetzt = {color}")

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

    def _selected_opacity_ids(self) -> list[str]:
        ids = list(self._selected_ann_ids) if self._selected_ann_ids else (
            [self._selected_ann_id] if self._selected_ann_id else []
        )
        return [i for i in ids if i]

    def _apply_toolbar_opacity(self, value: float, *, commit: bool = True) -> None:
        """
        Opacity-Slider/Spin: bei Auswahl nur ausgewählte Objekte;
        ohne Auswahl → Standard-Deckkraft für neue Annotationen.
        commit=False: Live-Vorschau ohne Undo/Sidecar-Force (Slider-Drag).
        """
        op = max(0.05, min(1.0, float(value)))
        ids = self._selected_opacity_ids()
        if self.store and ids:
            n = self.store.set_opacities(ids, op)
            if n > 0:
                if commit:
                    try:
                        self.schedule_sidecar_save(force=True)
                    except Exception:
                        pass
                self.refresh()
                self.annotations_changed.emit()
                self.status.emit(f"Deckkraft {op:.2f} für {n} ausgewählte Annotation(en)")
            return
        self._default_opacity = op
        if commit:
            set_ann_default_opacity(self._default_opacity)
        self.status.emit(f"Standard-Deckkraft {self._default_opacity:.2f}")

    def _on_opacity_slider_pressed(self) -> None:
        """Undo-Stufe einmalig beim Drag-Start (Commit on release)."""
        self._opacity_slider_dragging = True
        self._opacity_slider_undo_pushed = False
        ids = self._selected_opacity_ids()
        if self.store and ids:
            try:
                self.store._push_undo("Deckkraft")  # noqa: SLF001 — eine Stufe für Drag
                self._opacity_slider_prev_recording = bool(self.store._recording)
                self.store._recording = False
                self._opacity_slider_undo_pushed = True
            except Exception:
                self._opacity_slider_undo_pushed = False

    def _on_opacity_slider_released(self) -> None:
        """Slider loslassen → Sidecar speichern, Undo-Aufnahme wieder an."""
        was_dragging = bool(self._opacity_slider_dragging)
        self._opacity_slider_dragging = False
        if self.store and self._opacity_slider_undo_pushed:
            try:
                self.store._recording = bool(
                    getattr(self, "_opacity_slider_prev_recording", True)
                )
            except Exception:
                self.store._recording = True
        self._opacity_slider_undo_pushed = False
        if was_dragging:
            # Finalen Wert committen (Sidecar + Default persistieren)
            percent = int(self.slider_opacity.value()) if hasattr(self, "slider_opacity") else 100
            value = max(0.05, min(1.0, float(percent) / 100.0))
            ids = self._selected_opacity_ids()
            if self.store and ids:
                try:
                    self.schedule_sidecar_save(force=True)
                except Exception:
                    pass
                self.refresh()
                self.annotations_changed.emit()
            else:
                self._default_opacity = value
                set_ann_default_opacity(self._default_opacity)

    def _on_default_opacity_changed(self, value: float):
        self._sync_opacity_controls(value, from_slider=False)
        self._apply_toolbar_opacity(value, commit=True)

    def _on_opacity_slider_changed(self, percent: int):
        value = max(0.05, min(1.0, float(percent) / 100.0))
        self._sync_opacity_controls(value, from_slider=True)
        # Während Drag: Live ohne Undo-Spam; ohne Drag (API/Wheel): sofort committen
        if getattr(self, "_opacity_slider_dragging", False):
            self._apply_toolbar_opacity(value, commit=False)
        else:
            self._apply_toolbar_opacity(value, commit=True)

    def _sync_stroke_controls(self, value: float) -> None:
        w = max(1.0, min(12.0, float(value)))
        iw = int(round(w))
        if hasattr(self, "slider_stroke"):
            self.slider_stroke.blockSignals(True)
            self.slider_stroke.setValue(iw)
            self.slider_stroke.blockSignals(False)
        if hasattr(self, "lbl_stroke"):
            self.lbl_stroke.setText(f"Strich {iw}")

    def _selected_stroke_ids(self) -> list[str]:
        return self._selected_opacity_ids()

    def _apply_toolbar_stroke(self, value: float, *, commit: bool = True) -> None:
        """
        Stroke-Slider: bei Auswahl nur ausgewählte Shapes;
        ohne Auswahl → Standard-Strichstärke. commit=False: Live ohne Undo/Sidecar.
        """
        w = max(1.0, min(12.0, float(value)))
        ids = self._selected_stroke_ids()
        if self.store and ids:
            n = self.store.set_stroke_widths(ids, w)
            if n > 0:
                if commit:
                    try:
                        self.schedule_sidecar_save(force=True)
                    except Exception:
                        pass
                self.refresh()
                self.annotations_changed.emit()
                self.status.emit(f"Strichstärke {w:.0f}px für {n} ausgewählte Annotation(en)")
            return
        self._default_stroke_width = w
        if commit:
            try:
                from instantlensdoc.core.app_settings import set_ann_default_stroke_width

                set_ann_default_stroke_width(self._default_stroke_width)
            except Exception:
                pass
        self._sync_ink_preview_style()
        self.status.emit(f"Standard-Strichstärke {self._default_stroke_width:.0f}px")

    def _on_stroke_slider_pressed(self) -> None:
        """Undo-Stufe einmalig beim Drag-Start (Commit on release) — 0.9.2."""
        self._stroke_slider_dragging = True
        self._stroke_slider_undo_pushed = False
        ids = self._selected_stroke_ids()
        if self.store and ids:
            try:
                self.store._push_undo("Strichstärke")  # noqa: SLF001
                self._stroke_slider_prev_recording = bool(self.store._recording)
                self.store._recording = False
                self._stroke_slider_undo_pushed = True
            except Exception:
                self._stroke_slider_undo_pushed = False

    def _on_stroke_slider_released(self) -> None:
        was_dragging = bool(self._stroke_slider_dragging)
        self._stroke_slider_dragging = False
        if self.store and self._stroke_slider_undo_pushed:
            try:
                self.store._recording = bool(
                    getattr(self, "_stroke_slider_prev_recording", True)
                )
            except Exception:
                self.store._recording = True
        self._stroke_slider_undo_pushed = False
        if was_dragging:
            px = int(self.slider_stroke.value()) if hasattr(self, "slider_stroke") else 2
            value = max(1.0, min(12.0, float(px)))
            ids = self._selected_stroke_ids()
            if self.store and ids:
                try:
                    self.schedule_sidecar_save(force=True)
                except Exception:
                    pass
                self.refresh()
                self.annotations_changed.emit()
            else:
                self._default_stroke_width = value
                try:
                    from instantlensdoc.core.app_settings import set_ann_default_stroke_width

                    set_ann_default_stroke_width(self._default_stroke_width)
                except Exception:
                    pass

    def _on_stroke_slider_changed(self, px: int) -> None:
        value = max(1.0, min(12.0, float(px)))
        self._sync_stroke_controls(value)
        if getattr(self, "_stroke_slider_dragging", False):
            self._apply_toolbar_stroke(value, commit=False)
        else:
            self._apply_toolbar_stroke(value, commit=True)

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
        """PageLabels aus PDF + Sidecar-Custom laden (Custom überschreibt) — 2.2.0."""
        self._page_labels = []
        if not self.pdf_path or self.page_count <= 0:
            return
        n = int(self.page_count or 0)
        try:
            from ild_pdf import PdfDocument

            with PdfDocument(self.pdf_path, password=self.password) as doc:
                native = list(doc.page_labels())
        except Exception:
            native = [""] * n
        custom: list[str] = []
        if self.store is not None:
            try:
                custom = self.store.list_custom_page_labels(page_count=n)
            except Exception:
                custom = []
        from ild_pdf.page_labels import merge_labels

        self._page_labels = merge_labels(native, custom)

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

    def annotation_types_visible(self) -> dict[str, bool]:
        """Globale Typ-Toggles Highlight/Note/Shape/Redaction — 1.8.0."""
        return get_ann_layer_types_visible()

    def set_annotation_type_visible(self, group: str, visible: bool) -> None:
        """Einen Annotation-Typ global ein-/ausblenden — 1.8.0; Zähler 1.8.1."""
        types = set_ann_layer_type_visible(group, visible)
        self.canvas.set_ann_type_visible(types)
        vis_n, total_n = self.count_visible_annotations()
        self.status.emit(
            f"Annotation-Typ „{group}“ "
            + ("sichtbar" if visible else "ausgeblendet")
            + f" — {vis_n} von {total_n} sichtbar"
        )
        self.annotations_layer_changed.emit(self._annotations_visible)

    def set_annotation_types_visible(self, visible: dict[str, bool]) -> None:
        types = set_ann_layer_types_visible(visible)
        self.canvas.set_ann_type_visible(types)
        self.annotations_layer_changed.emit(self._annotations_visible)

    def count_visible_annotations(self) -> tuple[int, int]:
        """(sichtbar nach Typ-Layer, gesamt) — 1.8.1."""
        if not self.store:
            return 0, 0
        total = len(self.store.annotations)
        if not self._annotations_visible:
            return 0, total
        n = sum(
            1
            for a in self.store.annotations
            if self.canvas._ann_type_is_visible(a)
        )
        return n, total

    def count_annotations_by_layer_group(self) -> dict[str, int]:
        """Anzahl Annotationen je Layer-Gruppe — 1.8.2."""
        out = {"highlight": 0, "note": 0, "shape": 0, "redaction": 0}
        if not self.store:
            return out
        for a in self.store.annotations:
            g = self.canvas.ann_type_group(a.type)
            out[g] = out.get(g, 0) + 1
        return out

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

    def set_show_page_number_overlay(self, enabled: bool):
        """Seitennummer als Overlay ein-/ausblenden (persistiert)."""
        on = bool(enabled)
        changed = self._show_page_number_overlay != on
        self._show_page_number_overlay = on
        set_show_page_number_overlay(on)
        if hasattr(self, "btn_page_num"):
            self.btn_page_num.blockSignals(True)
            self.btn_page_num.setChecked(on)
            self.btn_page_num.blockSignals(False)
        self.canvas.set_show_page_number_overlay(on)
        self._update_page_number_overlay()
        if changed:
            self.page_number_overlay_changed.emit(on)
            self.status.emit(
                "Seitennummer-Overlay an" if on else "Seitennummer-Overlay aus"
            )

    def show_page_number_overlay(self) -> bool:
        return bool(self._show_page_number_overlay)

    def set_page_number_overlay_opacity(self, opacity: float):
        """Deckkraft des Seitennummer-Overlays setzen (persistiert)."""
        try:
            op = float(opacity)
        except (TypeError, ValueError):
            op = 0.59
        op = max(0.05, min(1.0, op))
        changed = abs(float(self._page_number_overlay_opacity) - op) >= 0.001
        self._page_number_overlay_opacity = op
        set_page_number_overlay_opacity(op)
        if hasattr(self, "spin_page_num_opacity"):
            self.spin_page_num_opacity.blockSignals(True)
            self.spin_page_num_opacity.setValue(op)
            self.spin_page_num_opacity.blockSignals(False)
        if getattr(self, "canvas", None):
            self.canvas.set_page_number_overlay_opacity(op)
        if changed:
            self.status.emit(f"Seitennummer-Overlay Deckkraft {op:.0%}")

    def page_number_overlay_opacity(self) -> float:
        return float(self._page_number_overlay_opacity)

    def set_redaction_preview_opacity(self, opacity: float):
        """Deckkraft der Schwärzungs-Vorschau setzen (persistiert) — 1.3.1."""
        try:
            op = float(opacity)
        except (TypeError, ValueError):
            op = 0.90
        op = max(0.05, min(1.0, op))
        self._redaction_preview_opacity = op
        set_redaction_preview_opacity(op)
        if getattr(self, "canvas", None):
            self.canvas.set_redaction_preview_opacity(op)
        if self.pdf_path:
            self.refresh()
        self.status.emit(f"Schwärzung Preview-Deckkraft {op:.0%}")

    def redaction_preview_opacity(self) -> float:
        return float(getattr(self, "_redaction_preview_opacity", 0.90) or 0.90)

    def set_page_number_overlay_font_size(self, size: int):
        """Schriftgröße (pt) des Seitennummer-Overlays setzen (persistiert)."""
        try:
            sz = int(size)
        except (TypeError, ValueError):
            sz = 11
        sz = max(8, min(36, sz))
        changed = int(self._page_number_overlay_font_size) != sz
        self._page_number_overlay_font_size = sz
        set_page_number_overlay_font_size(sz)
        if getattr(self, "canvas", None):
            self.canvas.set_page_number_overlay_font_size(sz)
        if changed:
            self.status.emit(f"Seitennummer-Overlay Schriftgröße {sz} pt")

    def page_number_overlay_font_size(self) -> int:
        return int(self._page_number_overlay_font_size)

    def set_page_number_overlay_position(self, position: str):
        """Position des Seitennummer-Overlays: bottom-center | top-center (persistiert)."""
        raw = str(position or "bottom-center").strip().lower().replace("_", "-")
        key = (
            "top-center"
            if raw in ("top-center", "top", "oben", "oben-mitte")
            else "bottom-center"
        )
        changed = str(self._page_number_overlay_position) != key
        self._page_number_overlay_position = key
        set_page_number_overlay_position(key)
        if getattr(self, "canvas", None):
            self.canvas.set_page_number_overlay_position(key)
        if changed:
            label = "oben-mitte" if key == "top-center" else "unten-mitte"
            self.status.emit(f"Seitennummer-Overlay Position {label}")

    def page_number_overlay_position(self) -> str:
        return str(self._page_number_overlay_position or "bottom-center")

    def set_page_number_overlay_format(self, fmt: str):
        """Format-String für Seitennummer-Overlay (persistiert); {page}/{pages}."""
        text = str(fmt or "").strip() or "{page} / {pages}"
        if len(text) > 80:
            text = text[:80]
        changed = str(self._page_number_overlay_format) != text
        self._page_number_overlay_format = text
        set_page_number_overlay_format(text)
        if getattr(self, "canvas", None):
            self.canvas.set_page_number_overlay_format(text)
        self._update_page_number_overlay()
        if changed:
            self.status.emit(f"Seitennummer-Overlay Format: {text}")

    def page_number_overlay_format(self) -> str:
        return str(self._page_number_overlay_format or "{page} / {pages}")

    def set_page_number_overlay_start(self, start: int):
        """Startnummer der ersten Seite im Overlay (persistiert)."""
        try:
            n = int(start)
        except (TypeError, ValueError):
            n = 1
        n = max(0, min(9999, n))
        changed = int(getattr(self, "_page_number_overlay_start", 1)) != n
        self._page_number_overlay_start = n
        set_page_number_overlay_start(n)
        self._update_page_number_overlay()
        if changed:
            self.status.emit(f"Seitennummer-Overlay Start: {n}")

    def page_number_overlay_start(self) -> int:
        return int(getattr(self, "_page_number_overlay_start", 1) or 1)

    def set_page_number_overlay_skip_edges(self, enabled: bool):
        """Erste und letzte Seite vom Seitennummer-Overlay ausschließen (persistiert)."""
        on = bool(enabled)
        changed = bool(getattr(self, "_page_number_overlay_skip_edges", False)) != on
        self._page_number_overlay_skip_edges = on
        set_page_number_overlay_skip_edges(on)
        self._update_page_number_overlay()
        if changed:
            self.status.emit(
                "Seitennummer-Overlay: erste/letzte Seite aus"
                if on
                else "Seitennummer-Overlay: alle Seiten"
            )

    def page_number_overlay_skip_edges(self) -> bool:
        return bool(getattr(self, "_page_number_overlay_skip_edges", False))

    def format_page_number_overlay_text(self) -> str:
        """Overlay-Text aus Format-String ({page}/{pages}, Aliase {n}/{total}, {label})."""
        if self._page_number_overlay_should_skip():
            return ""
        start = int(getattr(self, "_page_number_overlay_start", 1) or 1)
        page = int(self.page_index) + start
        count = int(self.page_count or 0)
        pages = count + start - 1 if count > 0 else 0
        lab = self.page_label(self.page_index) or ""
        fmt = str(self._page_number_overlay_format or "{page} / {pages}")
        try:
            return fmt.format(
                page=page,
                pages=pages,
                n=page,
                total=pages,
                label=lab,
            )
        except Exception:
            return f"{page} / {pages}"

    def _page_number_overlay_should_skip(self) -> bool:
        """True wenn Overlay auf aktueller Seite wegen Edge-Ausschluss ausgeblendet wird."""
        if not bool(getattr(self, "_page_number_overlay_skip_edges", False)):
            return False
        count = int(self.page_count or 0)
        if count <= 0:
            return False
        idx = int(self.page_index)
        if idx <= 0:
            return True
        if count >= 2 and idx >= count - 1:
            return True
        # Einzelseite: erste = letzte → ausschließen
        if count == 1:
            return True
        return False

    def _update_page_number_overlay(self) -> None:
        """Aktuelle Seitennummer/Label an Canvas-Overlay übergeben."""
        if not getattr(self, "canvas", None):
            return
        if not self._show_page_number_overlay or not self.pdf_path:
            self.canvas.set_page_number_text("")
            return
        text = self.format_page_number_overlay_text()
        self.canvas.set_page_number_text(text)

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
                self.schedule_sidecar_save(force=True)
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
        try:
            self._default_fill_color = get_ann_default_fill_color()
        except Exception:
            self._default_fill_color = getattr(self, "_default_fill_color", "#FFE066")
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
        self.canvas.set_ann_type_visible(get_ann_layer_types_visible())
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
        self._show_page_number_overlay = get_show_page_number_overlay()
        self._page_number_overlay_opacity = get_page_number_overlay_opacity()
        self._page_number_overlay_font_size = get_page_number_overlay_font_size()
        self._page_number_overlay_position = get_page_number_overlay_position()
        self._page_number_overlay_format = get_page_number_overlay_format()
        self._page_number_overlay_start = get_page_number_overlay_start()
        self._page_number_overlay_skip_edges = get_page_number_overlay_skip_edges()
        if hasattr(self, "btn_page_num"):
            self.btn_page_num.blockSignals(True)
            self.btn_page_num.setChecked(self._show_page_number_overlay)
            self.btn_page_num.blockSignals(False)
        if hasattr(self, "spin_page_num_opacity"):
            self.spin_page_num_opacity.blockSignals(True)
            self.spin_page_num_opacity.setValue(self._page_number_overlay_opacity)
            self.spin_page_num_opacity.blockSignals(False)
        self.canvas.set_show_page_number_overlay(self._show_page_number_overlay)
        self.canvas.set_page_number_overlay_opacity(self._page_number_overlay_opacity)
        self.canvas.set_page_number_overlay_font_size(self._page_number_overlay_font_size)
        self.canvas.set_page_number_overlay_position(self._page_number_overlay_position)
        self.canvas.set_page_number_overlay_format(self._page_number_overlay_format)
        self._redaction_preview_opacity = get_redaction_preview_opacity()
        self.canvas.set_redaction_preview_opacity(self._redaction_preview_opacity)
        self._update_page_number_overlay()
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
        """Standard-Zoom aus Einstellungen: Prozent / Fit-Width / Fit-Page."""
        # Session-Zoom pro Tab hat Vorrang (0.9.2)
        if getattr(self, "_suppress_default_zoom", False):
            return
        mode = get_default_zoom_mode()
        if mode == "fit_width":
            self.fit_width()
            return
        if mode == "fit_page":
            self.fit_page()
            return
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
            AnnotationType.MEASURE_AREA: "Fläche",
            AnnotationType.MEASURE_ANGLE: "Winkel",
            AnnotationType.INK: "Freihand",
            AnnotationType.SIGNATURE_FIELD: "Signaturfeld",
        }.get(tool, tool.value)

    def _toggle_measure_unit(self) -> None:
        """Messanzeige mm ↔ px; Labels persistent aktualisieren — 2.1.0/2.1.1."""
        unit = toggle_measure_unit()
        if hasattr(self, "btn_measure_unit"):
            self.btn_measure_unit.setText(f"Maß:{unit}")
        if self.store and get_measure_labels_persistent():
            n = self.store.refresh_measure_labels(scale=self.scale, unit=unit)
            if n:
                self.schedule_sidecar_save(force=False)
                self.annotations_changed.emit()
        self.refresh()
        self.status.emit(f"Messanzeige: {unit}")

    def _toggle_measure_snap(self) -> None:
        """Snap-to-Annotation für Messung umschalten — 2.1.1."""
        enabled = toggle_measure_snap_to_annotation()
        if hasattr(self, "btn_measure_snap"):
            self.btn_measure_snap.setChecked(enabled)
        self.status.emit(
            "Mess-Snap an Annotationen: an"
            if enabled
            else "Mess-Snap an Annotationen: aus"
        )

    def _measure_unit(self) -> str:
        try:
            return get_measure_unit()
        except Exception:
            return "mm"

    def _snap_measure_point(
        self, x: float, y: float, *, page: int, tol: float = 8.0
    ) -> tuple[float, float]:
        """Punkt optional an nächste Ann.-Ecke/Endpunkt snappen — 2.1.1."""
        if not get_measure_snap_to_annotation() or not self.store:
            return x, y
        best = None
        best_d = float(tol)
        for ann in self.store.annotations:
            if int(ann.page) != int(page):
                continue
            pts = [
                (float(ann.x), float(ann.y)),
                (float(ann.x + ann.width), float(ann.y)),
                (float(ann.x), float(ann.y + ann.height)),
                (float(ann.x + ann.width), float(ann.y + ann.height)),
            ]
            if ann.type in (
                AnnotationType.LINE,
                AnnotationType.ARROW,
                AnnotationType.MEASURE,
                AnnotationType.MEASURE_ANGLE,
                AnnotationType.CALLOUT,
            ):
                pts.append((float(ann.callout_x), float(ann.callout_y)))
            if ann.type == AnnotationType.MEASURE_ANGLE:
                pts.append((float(ann.p3_x), float(ann.p3_y)))
            for px, py in pts:
                d = ((px - x) ** 2 + (py - y) ** 2) ** 0.5
                if d <= best_d:
                    best_d = d
                    best = (px, py)
        return best if best is not None else (x, y)

    def _set_tool(self, tool: AnnotationType | None):
        self.tool = tool
        self._pending_callout_anchor = None
        self._pending_callout_page = self.page_index
        self._pending_angle = None
        # Quick-Stempel nur über arm_quick_stamp(); Werkzeugwechsel löscht — 1.9.2
        self._quick_stamp_armed = False
        self._quick_stamp_payload = None
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
                "PDF → Redactions anwenden"
            )
        elif tool == AnnotationType.MEASURE_ANGLE:
            self.status.emit(
                "Werkzeug: Winkel — ersten Strahl ziehen, dann zweiten Endpunkt klicken"
            )
        elif tool == AnnotationType.MEASURE_AREA:
            self.status.emit(
                f"Werkzeug: Fläche — Rechteck ziehen (Anzeige {self._measure_unit()}²)"
            )
        elif tool == AnnotationType.MEASURE:
            self.status.emit(
                f"Werkzeug: Lineal — Distanz ziehen (Anzeige {self._measure_unit()})"
            )
        elif tool == AnnotationType.INK:
            self.status.emit(
                "Werkzeug: Freihand — Maus ziehen (Polyline); Ctrl+Z = Undo — 2.2.0"
            )
        else:
            self.status.emit(f"Werkzeug: {tool.value}")

    def current_tool_id(self) -> str:
        """Session-ID des aktuellen Ann.-Werkzeugs ("" = Auswahl) — 0.9.7."""
        if self.tool is None:
            return ""
        try:
            return str(self.tool.value)
        except Exception:
            return ""

    def set_tool_from_id(self, tool_id: str | None) -> None:
        """Ann.-Werkzeug aus Session-ID wiederherstellen — 0.9.7."""
        tid = str(tool_id or "").strip().lower()
        if tid in ("", "select", "none", "auswahl"):
            self._set_tool(None)
            return
        try:
            tool = AnnotationType(tid)
        except ValueError:
            return
        self._set_tool(tool)

    def restore_default_opacity(self, opacity: float) -> None:
        """Standard-Deckkraft aus Session wiederherstellen — 0.9.8."""
        try:
            op = max(0.05, min(1.0, float(opacity)))
        except (TypeError, ValueError):
            return
        self._default_opacity = op
        try:
            set_ann_default_opacity(op)
        except Exception:
            pass
        self._sync_opacity_controls(op)

    def restore_default_stroke_width(self, width: float) -> None:
        """Standard-Strichstärke aus Session wiederherstellen — 0.9.8."""
        try:
            w = max(1.0, min(12.0, float(width)))
        except (TypeError, ValueError):
            return
        self._default_stroke_width = w
        try:
            from instantlensdoc.core.app_settings import set_ann_default_stroke_width

            set_ann_default_stroke_width(w)
        except Exception:
            pass
        self._sync_stroke_controls(w)

    def restore_default_fill_color(self, color: str) -> None:
        """Standard-Füllfarbe aus Session wiederherstellen — 0.9.9."""
        c = str(color or "").strip()
        if not c:
            return
        if not c.startswith("#"):
            c = "#" + c
        c = c.upper()
        if len(c) < 4:
            return
        self._default_fill_color = c
        try:
            set_ann_default_fill_color(c)
        except Exception:
            pass

    def restore_default_stroke_color(self, color: str) -> None:
        """Standard-Strichfarbe (Stift) aus Session wiederherstellen — 0.9.9."""
        c = str(color or "").strip()
        if not c:
            return
        if not c.startswith("#"):
            c = "#" + c
        c = c.upper()
        if len(c) < 4:
            return
        self._pen_color = c
        try:
            set_ann_pen_color(c)
        except Exception:
            pass
        try:
            self._style_color_btn(self.btn_pen_color, c)
        except Exception:
            pass

    def _on_annotation_selected(self, ann_id: str):
        """Auswahl setzen; Gruppe → alle Mitglieder; Shift+Klick Mehrfachauswahl umschalten."""
        shift = bool(QApplication.keyboardModifiers() & Qt.ShiftModifier)
        aid = ann_id or None
        if shift and aid:
            group_ids = set()
            if self.store:
                group_ids = set(self.store.expand_group_ids([aid]))
            if not group_ids:
                group_ids = {aid}
            ids = set(self._selected_ann_ids)
            if aid in ids:
                ids -= group_ids
            else:
                ids |= group_ids
            self._selected_ann_ids = ids
            self._selected_ann_id = aid if aid in ids else (next(iter(ids), None))
            self.canvas.set_selected_ids(self._selected_ann_ids)
            n = len(self._selected_ann_ids)
            if n == 0:
                self.status.emit("Auswahl aufgehoben")
            elif n == 1 and self.store:
                ann = self.store.get(self._selected_ann_id) if self._selected_ann_id else None
                if ann:
                    try:
                        op = float(
                            getattr(ann, "opacity", self._default_opacity) or self._default_opacity
                        )
                    except (TypeError, ValueError):
                        op = self._default_opacity
                    self._sync_opacity_controls(op)
                    try:
                        sw = float(
                            getattr(ann, "stroke_width", self._default_stroke_width)
                            or self._default_stroke_width
                        )
                    except (TypeError, ValueError):
                        sw = self._default_stroke_width
                    self._sync_stroke_controls(sw)
                    self.status.emit(f"Auswahl: {ann.type.value} (S. {ann.page + 1})")
                else:
                    self.status.emit("1 Annotation ausgewählt")
            else:
                self.status.emit(f"{n} Annotationen ausgewählt (Shift+Klick)")
            return
        if aid and self.store:
            expanded = self.store.expand_group_ids([aid])
            self._selected_ann_ids = set(expanded) if expanded else {aid}
            self._selected_ann_id = aid
            self.canvas.set_selected_ids(self._selected_ann_ids)
            ann = self.store.get(aid)
            if ann:
                try:
                    op = float(getattr(ann, "opacity", self._default_opacity) or self._default_opacity)
                except (TypeError, ValueError):
                    op = self._default_opacity
                self._sync_opacity_controls(op)
                try:
                    sw = float(
                        getattr(ann, "stroke_width", self._default_stroke_width)
                        or self._default_stroke_width
                    )
                except (TypeError, ValueError):
                    sw = self._default_stroke_width
                self._sync_stroke_controls(sw)
                n = len(self._selected_ann_ids)
                gid = str(getattr(ann, "group_id", "") or "").strip()
                if n > 1 and gid:
                    lock_txt = " · gesperrt" if bool(getattr(ann, "locked", False)) else ""
                    gmeta = self.store.get_ann_group(gid) if self.store else {}
                    gtitle = str((gmeta or {}).get("title") or "").strip()
                    gname = gtitle or gid[:8]
                    self.status.emit(
                        f"Gruppe „{gname}“: {n} Annotationen ausgewählt{lock_txt}"
                    )
                else:
                    self.status.emit(f"Auswahl: {ann.type.value} (S. {ann.page + 1})")
            else:
                self.status.emit("Auswahl aufgehoben")
            return
        self._selected_ann_id = aid
        self._selected_ann_ids = {self._selected_ann_id} if self._selected_ann_id else set()
        self.canvas.set_selected_id(self._selected_ann_id)
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
            self.schedule_sidecar_save(force=True)
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

    def apply_sidecar_debounce_ms(self, ms: int | None = None) -> int:
        """Debounce-Intervall aus Settings übernehmen (200–1000 ms)."""
        from instantlensdoc.core.app_settings import get_sidecar_save_debounce_ms

        val = int(ms) if ms is not None else get_sidecar_save_debounce_ms()
        val = max(200, min(1000, val))
        self._sidecar_save_timer.setInterval(val)
        return val

    def schedule_sidecar_save(self, *, force: bool = False) -> None:
        """
        Sidecar speichern — ohne force verzögert (Debounce laut Settings, 200–1000 ms).
        force=True: ausstehendes Debounce abbrechen und sofort schreiben.
        """
        if not self.store:
            return
        if force:
            self._sidecar_save_timer.stop()
            self._sidecar_save_pending = False
            try:
                self.store.save(force=True)
            except Exception as e:
                QMessageBox.warning(self, "Annotationen", f"Speichern fehlgeschlagen: {e}")
            return
        was_pending = bool(getattr(self, "_sidecar_save_pending", False))
        self._sidecar_save_pending = True
        self._sidecar_save_timer.start()
        # Dirty-Indikator (Tab) auch bei pending Debounce aktualisieren
        if not was_pending:
            self.annotations_changed.emit()

    def sidecar_save_pending(self) -> bool:
        """True wenn Sidecar-Debounce noch aussteht (Timer aktiv oder Flag)."""
        return bool(
            getattr(self, "_sidecar_save_pending", False)
            or (
                hasattr(self, "_sidecar_save_timer")
                and self._sidecar_save_timer.isActive()
            )
        )

    def _flush_sidecar_save(self) -> None:
        if not self.store or not self._sidecar_save_pending:
            self._sidecar_save_pending = False
            return
        self._sidecar_save_pending = False
        try:
            self.store.save()
        except Exception as e:
            QMessageBox.warning(self, "Annotationen", f"Speichern fehlgeschlagen: {e}")
        self.annotations_changed.emit()

    def flush_sidecar_save(self) -> None:
        """Ausstehendes Debounce sofort ausführen (PDF-Wechsel / Close / Ctrl+S)."""
        if self._sidecar_save_timer.isActive() or self._sidecar_save_pending:
            self._sidecar_save_timer.stop()
            pending = self._sidecar_save_pending
            self._sidecar_save_pending = False
            if pending and self.store:
                try:
                    self.store.save(force=True)
                except Exception as e:
                    QMessageBox.warning(
                        self, "Annotationen", f"Speichern fehlgeschlagen: {e}"
                    )
                self.annotations_changed.emit()

    def load(self, path: str | Path, password: str | None = None) -> bool:
        from PySide6.QtWidgets import QApplication

        from ild_pdf.limits import OPEN_TIMEOUT_HINT, inspect_pdf
        from ild_pdf.render import clear_render_cache
        from ild_pdf.security import needs_password
        from instantlensdoc.ui.password_dialog import ask_pdf_password

        # Vorheriges Sidecar flushen bevor Store gewechselt wird
        self.flush_sidecar_save()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            path = Path(path)
            if not path.is_file():
                QMessageBox.critical(self, "PDF öffnen", f"Datei nicht gefunden:\n{path}")
                return False
            pw = password if password is not None else self.password

            # Prefill aus Crypto-Reload (nur wenn Toggle an) — 1.6.2
            prefill = ""
            try:
                win = self.window()
                raw_pf = getattr(win, "_crypto_reload_prefill", None)
                if raw_pf:
                    from instantlensdoc.core.app_settings import (
                        get_crypto_reload_prefill_password,
                    )

                    if get_crypto_reload_prefill_password():
                        prefill = str(raw_pf)
            except Exception:
                prefill = ""

            # Passwort nachfragen wenn nötig
            try:
                if pw is None and needs_password(path):
                    pw = ask_pdf_password(self, path, prefill=prefill)
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
                # ggf. nochmal Passwort versuchen — klarer DE-Fehler — 1.6.2
                from ild_pdf.security import (
                    WRONG_PASSWORD_MSG_DE,
                    is_wrong_password_error,
                )

                pw_err = any(is_wrong_password_error(e) for e in health.errors)
                if pw_err:
                    pw2 = ask_pdf_password(
                        self,
                        path,
                        prefill=prefill if prefill else "",
                        wrong_password=True,
                    )
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
                    # Nochmals Passwort? Sonst klare DE-Meldung — 1.6.2
                    if any(is_wrong_password_error(e) for e in health.errors):
                        QMessageBox.critical(
                            self,
                            "PDF öffnen",
                            WRONG_PASSWORD_MSG_DE,
                        )
                    else:
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
            # Fit-Modi brauchen Viewport-Größe → nach Show/Layout
            mode = get_default_zoom_mode()
            if mode in ("fit_width", "fit_page"):
                QTimer.singleShot(0, self.apply_default_zoom)
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
            self._update_page_number_overlay()
            if self._search_rects:
                self.canvas.set_search_highlights(self._search_rects, self._search_index)
            self.lbl_zoom.setText(f"{int(round(self.scale * 100))}%")
            pending = bool(getattr(self, "_sidecar_save_pending", False))
            dirty = (
                " *"
                if self.store and (self.store.dirty or pending)
                else ""
            )
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

    def set_search_options(
        self,
        *,
        case_sensitive: bool | None = None,
        whole_word: bool | None = None,
        regex: bool | None = None,
    ) -> None:
        """Case-sensitive / Whole-word (0.9.2) / Regex (0.9.3) Toggles für PDF-Suche."""
        if case_sensitive is not None:
            self._search_case_sensitive = bool(case_sensitive)
        if whole_word is not None:
            self._search_whole_word = bool(whole_word)
        if regex is not None:
            self._search_regex = bool(regex)

    def _search_kw(self) -> dict:
        return {
            "case_sensitive": bool(getattr(self, "_search_case_sensitive", False)),
            "whole_word": bool(getattr(self, "_search_whole_word", False)),
            "regex": bool(getattr(self, "_search_regex", False)),
        }

    def _rebuild_search_rects(self, *, keep_index: bool = True) -> int:
        """Aktualisiert Treffer-Rechtecke der aktuellen Seite für _search_query."""
        from ild_pdf.overlay import SearchPatternError

        q = self._search_query
        if not q or not self.pdf_path:
            self._search_rects = []
            self._search_index = -1
            return 0
        try:
            matches = find_text_rects(
                self.pdf_path,
                self.page_index,
                q,
                scale=self.scale,
                password=self.password,
                **self._search_kw(),
            )
        except SearchPatternError as e:
            self._search_rects = []
            self._search_index = -1
            self.status.emit(f"Regex-Fehler: {e}")
            raise
        self._search_rects = [(m.x, m.y, m.width, m.height) for m in matches]
        if keep_index and self._search_rects:
            self._search_index = max(0, min(self._search_index, len(self._search_rects) - 1))
        else:
            self._search_index = 0 if self._search_rects else -1
        return len(self._search_rects)

    def highlight_search(
        self,
        query: str,
        *,
        case_sensitive: bool | None = None,
        whole_word: bool | None = None,
        regex: bool | None = None,
    ) -> int:
        """Highlightet Query-Treffer auf der aktuellen Seite. Liefert Trefferzahl."""
        from ild_pdf.overlay import SearchPatternError

        q = (query or "").strip()
        if not q or not self.pdf_path:
            self.clear_search_highlights()
            return 0
        if (
            case_sensitive is not None
            or whole_word is not None
            or regex is not None
        ):
            self.set_search_options(
                case_sensitive=case_sensitive,
                whole_word=whole_word,
                regex=regex,
            )
        self._search_query = q
        try:
            n = self._rebuild_search_rects(keep_index=False)
        except SearchPatternError:
            self.clear_search_highlights()
            self._search_query = q  # Query behalten für Status
            raise
        self.canvas.set_search_highlights(self._search_rects, self._search_index)
        return n

    def _goto_search_page(self, page_index: int, *, hit_index: int = 0) -> bool:
        """Seite wechseln und Treffer-Highlight setzen. False wenn keine Treffer."""
        if not self.pdf_path or not self._search_query:
            return False
        if page_index < 0 or page_index >= self.page_count:
            return False
        if page_index != self.page_index:
            self.goto_page(page_index)
        else:
            self._rebuild_search_rects(keep_index=False)
        if not self._search_rects:
            return False
        self._search_index = max(0, min(int(hit_index), len(self._search_rects) - 1))
        self.canvas.set_search_highlights(self._search_rects, self._search_index)
        return True

    def _find_search_on_pages(
        self,
        *,
        start: int,
        direction: int,
        stop_exclusive: int | None = None,
    ) -> bool:
        """Nächste Seite mit Query-Treffern ab start (direction ±1)."""
        from ild_pdf.overlay import SearchPatternError

        if not self.pdf_path or not self._search_query or self.page_count <= 0:
            return False
        step = 1 if direction >= 0 else -1
        i = int(start)
        while 0 <= i < self.page_count:
            if stop_exclusive is not None and i == stop_exclusive:
                break
            try:
                matches = find_text_rects(
                    self.pdf_path,
                    i,
                    self._search_query,
                    scale=self.scale,
                    password=self.password,
                    **self._search_kw(),
                )
            except SearchPatternError as e:
                self.status.emit(f"Regex-Fehler: {e}")
                return False
            if matches:
                hit = 0 if step > 0 else len(matches) - 1
                return self._goto_search_page(i, hit_index=hit)
            i += step
        return False

    def search_next(self) -> bool:
        """Nächster Treffer: Seite → weitere Seiten → Wrap. False wenn keine Treffer."""
        if not self._search_query:
            return False
        if not self._search_rects:
            self._rebuild_search_rects(keep_index=False)
        if self._search_rects:
            if self._search_index < len(self._search_rects) - 1:
                self._search_index += 1
                self.canvas.set_search_highlights(self._search_rects, self._search_index)
                return True
            # Letzter Treffer der Seite → folgende Seiten, sonst Wrap ab Anfang
            if self._find_search_on_pages(start=self.page_index + 1, direction=1):
                return True
            if self._find_search_on_pages(
                start=0, direction=1, stop_exclusive=self.page_index + 1
            ):
                return True
            self._search_index = 0
            self.canvas.set_search_highlights(self._search_rects, self._search_index)
            return True
        if self._find_search_on_pages(start=self.page_index + 1, direction=1):
            return True
        if self._find_search_on_pages(
            start=0, direction=1, stop_exclusive=self.page_index + 1
        ):
            return True
        return False

    def search_prev(self) -> bool:
        """Vorheriger Treffer: Seite → vorherige Seiten → Wrap. False wenn keine Treffer."""
        if not self._search_query:
            return False
        if not self._search_rects:
            self._rebuild_search_rects(keep_index=False)
        if self._search_rects:
            if self._search_index > 0:
                self._search_index -= 1
                self.canvas.set_search_highlights(self._search_rects, self._search_index)
                return True
            if self._find_search_on_pages(start=self.page_index - 1, direction=-1):
                return True
            if self._find_search_on_pages(
                start=self.page_count - 1,
                direction=-1,
                stop_exclusive=self.page_index - 1,
            ):
                return True
            n = len(self._search_rects)
            self._search_index = n - 1
            self.canvas.set_search_highlights(self._search_rects, self._search_index)
            return True
        if self._find_search_on_pages(start=self.page_index - 1, direction=-1):
            return True
        if self._find_search_on_pages(
            start=self.page_count - 1,
            direction=-1,
            stop_exclusive=self.page_index - 1,
        ):
            return True
        return False

    def search_hit_count(self) -> int:
        return len(self._search_rects)

    def search_active_index(self) -> int:
        """0-basierter Index des aktiven Treffer-Highlights (−1 wenn keiner)."""
        return int(self._search_index)

    def annotate_search_hits_current_page(
        self,
        query: str | None = None,
        *,
        case_sensitive: bool | None = None,
        whole_word: bool | None = None,
        regex: bool | None = None,
        tag: str | None = None,
    ) -> int:
        """Suchtreffer der aktuellen Seite als Highlight-Annotationen — 0.9.6."""
        return self.annotate_search_hits(
            query,
            all_pages=False,
            case_sensitive=case_sensitive,
            whole_word=whole_word,
            regex=regex,
            tag=tag,
        )

    def annotate_search_hits_all_pages(
        self,
        query: str | None = None,
        *,
        case_sensitive: bool | None = None,
        whole_word: bool | None = None,
        regex: bool | None = None,
        tag: str | None = None,
    ) -> int:
        """Suchtreffer aller Seiten als Highlight-Annotationen (ein Undo) — 0.9.7."""
        return self.annotate_search_hits(
            query,
            all_pages=True,
            case_sensitive=case_sensitive,
            whole_word=whole_word,
            regex=regex,
            tag=tag,
        )

    def annotate_search_hits(
        self,
        query: str | None = None,
        *,
        all_pages: bool = False,
        case_sensitive: bool | None = None,
        whole_word: bool | None = None,
        regex: bool | None = None,
        tag: str | None = None,
    ) -> int:
        """
        Suchtreffer als Highlight-Annotationen anlegen (Batch).
        all_pages=False: aktuelle Seite (0.9.6); True: alle Seiten (0.9.7).
        tag: optionaler Tag an neue Highlights (0.9.8).
        Immer ein Undo-Schritt via store.atomic().
        """
        from ild_pdf.overlay import SearchPatternError, find_text_rects

        if not self.store or not self.pdf_path:
            self.status.emit("Kein PDF geladen")
            return 0
        q = (query if query is not None else self._search_query) or ""
        q = q.strip()
        if not q:
            self.status.emit("Keine Suche aktiv")
            return 0
        if (
            case_sensitive is not None
            or whole_word is not None
            or regex is not None
        ):
            self.set_search_options(
                case_sensitive=case_sensitive,
                whole_word=whole_word,
                regex=regex,
            )
        self._search_query = q
        color = self._highlight_color or "#FFE066"
        opacity = float(getattr(self, "_default_opacity", 1.0) or 1.0)
        tag_clean = (tag or "").strip()
        tags = [tag_clean] if tag_clean else []
        pages: list[int]
        if all_pages:
            pages = list(range(max(0, int(self.page_count))))
        else:
            pages = [int(self.page_index)]
        # Treffer je Seite sammeln (vor Commit), dann ein atomic
        page_hits: list[tuple[int, list]] = []
        try:
            for page in pages:
                if all_pages:
                    matches = find_text_rects(
                        self.pdf_path,
                        page,
                        q,
                        scale=self.scale,
                        password=self.password,
                        **self._search_kw(),
                    )
                    rects = [
                        (float(m.x), float(m.y), float(m.width), float(m.height))
                        for m in matches
                    ]
                else:
                    n = self._rebuild_search_rects(keep_index=True)
                    if n <= 0 or not self._search_rects:
                        self.status.emit("Keine Treffer auf dieser Seite")
                        return 0
                    rects = list(self._search_rects)
                if rects:
                    page_hits.append((page, rects))
        except SearchPatternError as e:
            self.status.emit(f"Regex-Fehler: {e}")
            raise
        if not page_hits:
            self.status.emit(
                "Keine Treffer im Dokument"
                if all_pages
                else "Keine Treffer auf dieser Seite"
            )
            return 0
        created = 0
        label = "Suche → Highlight (alle Seiten)" if all_pages else "Suche → Highlight"
        with self.store.atomic(label=label):
            for page, rects in page_hits:
                for i, (rx, ry, rw, rh) in enumerate(rects):
                    snippet = q if created == 0 and i == 0 else ""
                    self.store.add(
                        Annotation(
                            page=page,
                            type=AnnotationType.HIGHLIGHT,
                            x=float(rx),
                            y=float(ry),
                            width=max(float(rw), 4.0),
                            height=max(float(rh), 6.0),
                            color=color,
                            text=snippet,
                            opacity=opacity,
                            tags=list(tags),
                        )
                    )
                    created += 1
        try:
            self.schedule_sidecar_save(force=True)
        except Exception as e:
            QMessageBox.warning(self, "Treffer markieren", str(e))
        # Aktuelle Seite-Highlights aktualisieren
        try:
            self._rebuild_search_rects(keep_index=True)
        except Exception:
            pass
        self.canvas.set_search_highlights(self._search_rects, self._search_index)
        self.refresh()
        self.annotations_changed.emit()
        tag_note = f", Tag „{tag_clean}“" if tag_clean else ""
        if all_pages:
            self.status.emit(
                f"{created} Highlight(s) aus Suche (alle Seiten, {len(page_hits)} Seite(n){tag_note})"
            )
        else:
            self.status.emit(
                f"{created} Highlight(s) aus Suche (Seite {pages[0] + 1}{tag_note})"
            )
        return created

    def collect_search_hits(
        self,
        query: str,
        *,
        max_hits: int = 100,
        snippet_chars: int = 48,
        case_sensitive: bool | None = None,
        whole_word: bool | None = None,
        regex: bool | None = None,
    ) -> list[tuple[int, int, str]]:
        """
        Alle PDF-Texttreffer für die Trefferliste.
        Rückgabe: (Seite, Zeichen-Offset, Snippet) — Offset ab 0.9.4.
        """
        from ild_pdf.overlay import SearchPatternError

        q = (query or "").strip()
        if not q or not self.pdf_path or self.page_count <= 0:
            return []
        if (
            case_sensitive is not None
            or whole_word is not None
            or regex is not None
        ):
            self.set_search_options(
                case_sensitive=case_sensitive,
                whole_word=whole_word,
                regex=regex,
            )
        out: list[tuple[int, int, str]] = []
        ctx = max(12, int(snippet_chars))
        for page_idx in range(int(self.page_count)):
            if len(out) >= max_hits:
                break
            try:
                matches = find_text_rects(
                    self.pdf_path,
                    page_idx,
                    q,
                    scale=1.0,
                    password=self.password,
                    max_hits=max(1, max_hits - len(out)),
                    **self._search_kw(),
                )
            except SearchPatternError:
                raise
            for hit_i, m in enumerate(matches):
                if len(out) >= max_hits:
                    break
                raw = (getattr(m, "text", None) or q).replace("\n", " ").strip()
                # Kurzes Snippet um Match
                try:
                    from instantlensdoc.core.fulltext import _snippet_around

                    snip = _snippet_around(raw, q, context_chars=ctx, width=max(40, ctx * 2))
                except Exception:
                    snip = raw[: max(20, ctx)] + ("…" if len(raw) > ctx else "")
                try:
                    off = int(getattr(m, "offset", hit_i))
                except (TypeError, ValueError):
                    off = hit_i
                if off < 0:
                    off = hit_i
                out.append((page_idx, off, snip or q))
        return out

    def recolor_stroke_selected_annotations(self) -> int:
        """Strichfarbe für ausgewähltes Shape setzen (getrennt von Füllung; Commit + Undo) — 0.9.4."""
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
        initial = QColor(self._highlight_color or "#FFE066")
        first = self.store.get(ids[0])
        if first and first.color:
            c0 = QColor(first.color)
            if c0.isValid():
                initial = c0
        chosen = QColorDialog.getColor(
            initial,
            self,
            f"Strichfarbe für {len(ids)} Annotation(en)",
        )
        if not chosen.isValid():
            return 0
        color = chosen.name().upper()
        n = self.store.set_colors(ids, color)
        if n <= 0:
            self.status.emit("Strichfarbe nicht geändert")
            return 0
        try:
            self.schedule_sidecar_save(force=True)
        except Exception as e:
            QMessageBox.warning(self, "Strichfarbe", str(e))
            return 0
        self.refresh()
        self.annotations_changed.emit()
        self.status.emit(f"Strichfarbe {color} für {n} Annotation(en)")
        return n

    def recolor_fill_selected_annotations(self) -> int:
        """Füllfarbe für ausgewähltes Shape setzen (Commit + Undo) — 0.9.3."""
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
        initial = QColor("#FFE066")
        first = self.store.get(ids[0])
        if first:
            src = str(getattr(first, "fill_color", "") or "").strip() or (
                first.color or ""
            )
            c0 = QColor(src) if src else QColor()
            if c0.isValid():
                initial = c0
        chosen = QColorDialog.getColor(
            initial,
            self,
            f"Füllfarbe für {len(ids)} Annotation(en)",
        )
        if not chosen.isValid():
            return 0
        color = chosen.name().upper()
        n = self.store.set_fill_colors(ids, color)
        if n <= 0:
            self.status.emit("Füllfarbe nicht geändert")
            return 0
        self._default_fill_color = color
        try:
            set_ann_default_fill_color(color)
        except Exception:
            pass
        try:
            self.schedule_sidecar_save(force=True)
        except Exception as e:
            QMessageBox.warning(self, "Füllfarbe", str(e))
            return 0
        self.refresh()
        self.annotations_changed.emit()
        self.status.emit(f"Füllfarbe {color} für {n} Annotation(en)")
        return n

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
            label = self.store.peek_undo_label() or "Annotation"
            self.store.undo()
            self.schedule_sidecar_save(force=True)
            self.refresh()
            self.annotations_changed.emit()
            self.status.emit(f"{label} rückgängig")
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
            elif kind == "duplicate":
                label = f"Seite {page_h} dupliziert — rückgängig"
            elif kind == "rotate":
                deg = int(entry.get("degrees", 90))
                label = f"Seite {page_h} gedreht ({deg:+d}°) — rückgängig"
            elif kind == "flip":
                parts = []
                if entry.get("horizontal"):
                    parts.append("H")
                if entry.get("vertical"):
                    parts.append("V")
                axis = "/".join(parts) or "?"
                label = f"Seite {page_h} gespiegelt ({axis}) — rückgängig"
            elif kind == "reorder":
                n = int(entry.get("page_count") or len(entry.get("inverse") or []) or 0)
                label = f"Seitenreihenfolge geändert ({n} Seiten) — rückgängig"
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

    def annotation_undo_history_items(self) -> list[dict]:
        """Annotation-Undo-Stack mit sichtbaren Labels (älteste zuerst)."""
        if not self.store:
            return []
        try:
            return list(self.store.undo_history_items())
        except Exception:
            return []

    def restore_annotation_undo_at(self, stack_index: int) -> bool:
        """Annotation-Undo vom neuesten Eintrag bis einschließlich stack_index."""
        if not self.store or not self.store.can_undo():
            self.status.emit("Annotation-Undo-Stack leer")
            return False
        n = len(getattr(self.store, "_undo", []) or [])
        if n <= 0:
            return False
        target = max(0, min(int(stack_index), n - 1))
        times = n - target
        last_label = "Annotation"
        ok_any = False
        try:
            for _ in range(times):
                if not self.store.can_undo():
                    break
                last_label = self.store.peek_undo_label() or "Annotation"
                self.store.undo()
                ok_any = True
            if ok_any:
                self.schedule_sidecar_save(force=True)
                self.refresh()
                self.annotations_changed.emit()
                self.status.emit(f"{last_label} rückgängig (Undo-Stack)")
            return ok_any
        except Exception as e:
            QMessageBox.warning(self, "Rückgängig", str(e))
            return False

    def show_page_ops_history(self) -> bool:
        """Dialog: PDF-Undo-Stack (Seiten-Ops + benannte Annotation-Undos)."""
        from PySide6.QtWidgets import (
            QDialog,
            QHBoxLayout,
            QLabel,
            QListWidget,
            QListWidgetItem,
            QPushButton,
            QVBoxLayout,
        )

        page_items = self.page_ops_history_items()
        ann_items = self.annotation_undo_history_items()
        dlg = QDialog(self)
        dlg.setWindowTitle("PDF-Undo-Stack")
        dlg.resize(460, 380)
        layout = QVBoxLayout(dlg)
        layout.addWidget(
            QLabel(
                "Seiten-Ops und Annotation-Undos (sichtbar benannt, z. B. „Tag umbenennen“).\n"
                "Neueste Einträge unten — „Wiederherstellen“ macht bis zum gewählten Eintrag rückgängig."
            )
        )
        lst = QListWidget()

        def _refill() -> None:
            lst.clear()
            for it in self.page_ops_history_items():
                row = QListWidgetItem(f"[Seite] {it['label']}")
                row.setData(Qt.UserRole, ("page", int(it["stack_index"])))
                lst.addItem(row)
            for it in self.annotation_undo_history_items():
                row = QListWidgetItem(f"[Ann.] {it['label']}")
                row.setData(Qt.UserRole, ("annotation", int(it["stack_index"])))
                lst.addItem(row)
            if lst.count() > 0:
                lst.setCurrentRow(lst.count() - 1)

        _refill()
        layout.addWidget(lst)
        if lst.count() == 0:
            layout.addWidget(QLabel("Keine Einträge im PDF-Undo-Stack."))

        btns = QHBoxLayout()
        btn_restore = QPushButton("Wiederherstellen")
        btn_restore.setEnabled(lst.count() > 0)
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
            data = cur.data(Qt.UserRole)
            if not data:
                return
            source, idx = data
            ok = False
            if source == "page":
                ok = self.restore_page_op_at(int(idx))
            elif source == "annotation":
                ok = self.restore_annotation_undo_at(int(idx))
            if ok:
                restored["ok"] = True
                _refill()
                btn_restore.setEnabled(lst.count() > 0)
                if lst.count() == 0:
                    dlg.accept()

        btn_restore.clicked.connect(_do_restore)
        lst.itemDoubleClicked.connect(lambda _item: _do_restore())
        btn_close.clicked.connect(dlg.reject)
        # page_items/ann_items nur für Initial-Enable — Liste via _refill
        _ = (page_items, ann_items)
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
            self.schedule_sidecar_save(force=True)
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
                self.schedule_sidecar_save(force=True)
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
        """Batch-Strichfarbe (Alias) — nutzt Stroke-Color Picker 0.9.4."""
        return self.recolor_stroke_selected_annotations()

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
            self.schedule_sidecar_save(force=True)
        except Exception as e:
            QMessageBox.warning(self, "Annotation-Deckkraft", str(e))
            return 0
        self.refresh()
        self.annotations_changed.emit()
        self.status.emit(f"Deckkraft {float(value):.2f} für {n} Annotation(en)")
        return n

    def _selected_annotation_ids(self) -> list[str]:
        ids = list(self._selected_ann_ids) if self._selected_ann_ids else (
            [self._selected_ann_id] if self._selected_ann_id else []
        )
        return [i for i in ids if i]

    def align_selected_annotations(self, mode: str = "left") -> int:
        """Auswahl ausrichten: left|center|right|top|middle|bottom (≥2)."""
        if not self.store:
            self.status.emit("Kein PDF geladen")
            return 0
        ids = self._selected_annotation_ids()
        if len(ids) < 2:
            self.status.emit("Ausrichten: mindestens 2 Annotationen auswählen")
            return 0
        key = str(mode or "left").strip().lower()
        v_modes = {"top", "middle", "bottom"}
        h_modes = {"left", "center", "right"}
        if key in v_modes:
            n = self.store.align(ids, vertical=key)
        else:
            if key not in h_modes:
                key = "left"
            n = self.store.align(ids, horizontal=key)
        if n <= 0:
            self.status.emit("Ausrichten: keine Änderung")
            return 0
        try:
            self.schedule_sidecar_save(force=True)
        except Exception as e:
            QMessageBox.warning(self, "Ausrichten", str(e))
            return 0
        self.refresh()
        self.annotations_changed.emit()
        labels = {
            "left": "links",
            "center": "mittig",
            "right": "rechts",
            "top": "oben",
            "middle": "vertikal mittig",
            "bottom": "unten",
        }
        label = labels.get(key, key)
        self.status.emit(f"{n} Annotation(en) {label} ausgerichtet")
        return n

    def distribute_selected_annotations_horizontal(self) -> int:
        """Auswahl horizontal gleichmäßig verteilen (≥3)."""
        if not self.store:
            self.status.emit("Kein PDF geladen")
            return 0
        ids = self._selected_annotation_ids()
        if len(ids) < 3:
            self.status.emit("Verteilen: mindestens 3 Annotationen auswählen")
            return 0
        n = self.store.distribute_horizontal(ids)
        if n <= 0:
            self.status.emit("Verteilen: keine Änderung")
            return 0
        try:
            self.schedule_sidecar_save(force=True)
        except Exception as e:
            QMessageBox.warning(self, "Verteilen", str(e))
            return 0
        self.refresh()
        self.annotations_changed.emit()
        self.status.emit(f"{n} Annotation(en) horizontal verteilt")
        return n

    def distribute_selected_annotations_vertical(self) -> int:
        """Auswahl vertikal gleichmäßig verteilen (≥3)."""
        if not self.store:
            self.status.emit("Kein PDF geladen")
            return 0
        ids = self._selected_annotation_ids()
        if len(ids) < 3:
            self.status.emit("Verteilen: mindestens 3 Annotationen auswählen")
            return 0
        n = self.store.distribute_vertical(ids)
        if n <= 0:
            self.status.emit("Verteilen: keine Änderung")
            return 0
        try:
            self.schedule_sidecar_save(force=True)
        except Exception as e:
            QMessageBox.warning(self, "Verteilen", str(e))
            return 0
        self.refresh()
        self.annotations_changed.emit()
        self.status.emit(f"{n} Annotation(en) vertikal verteilt")
        return n

    def group_selected_annotations(self) -> int:
        """Auswahl gruppieren: gemeinsame temporäre group_id im Sidecar (≥2)."""
        if not self.store:
            self.status.emit("Kein PDF geladen")
            return 0
        ids = self._selected_annotation_ids()
        if len(ids) < 2:
            self.status.emit("Gruppieren: mindestens 2 Annotationen auswählen")
            return 0
        n, gid = self.store.group(ids)
        if n <= 0 or not gid:
            self.status.emit("Gruppieren: keine Änderung")
            return 0
        try:
            self.schedule_sidecar_save(force=True)
        except Exception as e:
            QMessageBox.warning(self, "Gruppieren", str(e))
            return 0
        self.refresh()
        self.annotations_changed.emit()
        self.status.emit(f"{n} Annotation(en) gruppiert ({gid})")
        return n

    def ungroup_selected_annotations(self) -> int:
        """Auswahl entgruppieren (group_id leeren)."""
        if not self.store:
            self.status.emit("Kein PDF geladen")
            return 0
        ids = self._selected_annotation_ids()
        if not ids:
            self.status.emit("Entgruppieren: keine Auswahl")
            return 0
        n = self.store.ungroup(ids)
        if n <= 0:
            self.status.emit("Entgruppieren: keine Gruppe in der Auswahl")
            return 0
        try:
            self.schedule_sidecar_save(force=True)
        except Exception as e:
            QMessageBox.warning(self, "Entgruppieren", str(e))
            return 0
        self.refresh()
        self.annotations_changed.emit()
        self.status.emit(f"{n} Annotation(en) entgruppiert")
        return n

    def toggle_selected_group_lock(self) -> int:
        """Gruppen-Sperre der Auswahl umschalten (Mitglieder nicht verschiebbar)."""
        if not self.store:
            self.status.emit("Kein PDF geladen")
            return 0
        ids = self._selected_annotation_ids()
        if not ids:
            self.status.emit("Gruppen-Sperre: keine Auswahl")
            return 0
        n, locked = self.store.toggle_group_lock(ids)
        if n <= 0:
            self.status.emit("Gruppen-Sperre: keine Änderung")
            return 0
        # Auswahl auf alle Gruppenmitglieder erweitern
        expanded = self.store.expand_group_ids(ids)
        if expanded:
            self._selected_ann_ids = set(expanded)
            self._selected_ann_id = expanded[0]
            self.canvas.set_selected_ids(self._selected_ann_ids)
        try:
            self.schedule_sidecar_save(force=True)
        except Exception as e:
            QMessageBox.warning(self, "Gruppen-Sperre", str(e))
            return 0
        self.refresh()
        self.annotations_changed.emit()
        state = "gesperrt" if locked else "entsperrt"
        self.status.emit(f"{n} Annotation(en) {state}")
        return n

    def edit_selected_ann_group(self) -> bool:
        """Temporäre Ann.-Gruppe umbenennen und farblich markieren (Sidecar)."""
        if not self.store:
            QMessageBox.information(self, "Gruppe", "Kein PDF mit Annotationen geladen.")
            return False
        ids = self._selected_annotation_ids()
        if not ids:
            self.status.emit("Ann.-Gruppe: keine Auswahl")
            return False
        expanded = self.store.expand_group_ids(ids)
        gid = ""
        for aid in expanded:
            ann = self.store.get(aid)
            if ann and str(getattr(ann, "group_id", "") or "").strip():
                gid = str(ann.group_id).strip()
                break
        if not gid:
            self.status.emit("Ann.-Gruppe: Auswahl ist nicht gruppiert")
            return False
        cur = self.store.get_ann_group(gid)
        title, ok = QInputDialog.getText(
            self,
            "Ann.-Gruppe",
            f"Name für Gruppe ({len(self.store.ids_in_group(gid))} Mitglieder):",
            text=cur.get("title") or "",
        )
        if not ok:
            return False
        color = cur.get("color") or ""
        pick = QMessageBox.question(
            self,
            "Gruppenfarbe",
            "Farbe für die Gruppenmarkierung wählen?",
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
        self.store.set_ann_group(gid, title=title, color=color)
        try:
            self.schedule_sidecar_save(force=True)
        except Exception as e:
            QMessageBox.warning(self, "Ann.-Gruppe", str(e))
            return False
        self.annotations_changed.emit()
        label = title.strip() or gid[:8]
        self.status.emit(f"Ann.-Gruppe „{label}“ aktualisiert")
        return True

    def extract_selected_pages_as_pdf(
        self, page_indices: list[int] | Sequence[int] | None = None
    ) -> Path | None:
        """Ausgewählte Seiten (Thumbnail-Batch) als neues PDF speichern. Rückgabe: Zielpfad."""
        if not self.pdf_path:
            QMessageBox.information(self, "Extrahieren", "Kein PDF geladen.")
            return None
        idxs = [int(p) for p in (page_indices or [])]
        if not idxs:
            self.status.emit("Extrahieren: keine Seiten ausgewählt")
            return None
        # Duplikate entfernen, Reihenfolge behalten
        seen: set[int] = set()
        clean: list[int] = []
        for i in idxs:
            if i in seen:
                continue
            seen.add(i)
            clean.append(i)
        from PySide6.QtWidgets import QFileDialog

        default_name = f"{self.pdf_path.stem}_extract.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Seiten als PDF extrahieren",
            str(self.pdf_path.with_name(default_name)),
            "PDF (*.pdf)",
        )
        if not path:
            return None
        dest = Path(path)
        if dest.suffix.lower() != ".pdf":
            dest = dest.with_suffix(".pdf")
        try:
            extract_pages(self.pdf_path, dest, clean)
        except Exception as e:
            QMessageBox.warning(self, "Extrahieren", str(e))
            return None
        self.status.emit(f"{len(clean)} Seite(n) → {dest.name}")
        return dest

    def open_selected_pages_as_document(
        self, page_indices: list[int] | Sequence[int] | None = None
    ) -> Path | None:
        """
        Ausgewählte Seiten als neues PDF speichern und Pfad für Tab-Öffnen liefern.
        Speichern-Dialog wie beim Extrahieren; Rückgabe None bei Abbruch.
        """
        dest = self.extract_selected_pages_as_pdf(page_indices)
        if dest is None:
            return None
        self.status.emit(f"{dest.name} — bereit zum Öffnen in neuem Tab")
        return dest

    def export_selected_ann_group_json(self, group_id: str | None = None) -> bool:
        """Temporäre Ann.-Gruppe als JSON exportieren (Mitglieder + Meta)."""
        if not self.store:
            QMessageBox.information(self, "Gruppe exportieren", "Kein PDF mit Annotationen geladen.")
            return False
        gid = str(group_id or "").strip()
        if not gid:
            ids = self._selected_annotation_ids()
            expanded = self.store.expand_group_ids(ids) if ids else []
            for aid in expanded:
                ann = self.store.get(aid)
                if ann and str(getattr(ann, "group_id", "") or "").strip():
                    gid = str(ann.group_id).strip()
                    break
        if not gid:
            self.status.emit("Gruppe exportieren: keine Gruppe gewählt")
            return False
        members = self.store.ids_in_group(gid)
        if not members:
            QMessageBox.information(self, "Gruppe exportieren", "Gruppe hat keine Mitglieder.")
            return False
        from PySide6.QtWidgets import QFileDialog

        meta = self.store.get_ann_group(gid)
        label = str(meta.get("title") or "").strip() or gid[:8]
        default_name = f"{(self.pdf_path.stem if self.pdf_path else 'ann')}_group_{label}.json"
        # Dateiname säubern
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in default_name)
        start_dir = str(self.pdf_path.with_name(safe)) if self.pdf_path else safe
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Ann.-Gruppe als JSON exportieren",
            start_dir,
            "JSON (*.json)",
        )
        if not path:
            return False
        dest = Path(path)
        if dest.suffix.lower() != ".json":
            dest = dest.with_suffix(".json")
        try:
            self.store.export_group_json(gid, dest)
        except Exception as e:
            QMessageBox.warning(self, "Gruppe exportieren", str(e))
            return False
        self.status.emit(f"Gruppe „{label}“ → {dest.name} ({len(members)} Ann.)")
        return True

    def reorder_page_favorites(self, pages: list[int]) -> list[int]:
        """PDF-Favoriten-Reihenfolge aus Sidebar-Drag speichern."""
        if not self.store or not self.pdf_path:
            return []
        cleaned = self.store.reorder_page_favorites(pages)
        try:
            self.schedule_sidecar_save(force=True)
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
            self.schedule_sidecar_save(force=True)
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
        """Letzte Seiten-Operation (Löschen, Duplizieren, Drehen, Neuordnen) rückgängig."""
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
                        self.schedule_sidecar_save(force=True)
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
            if kind == "duplicate":
                idx = int(entry["index"])
                if self.page_count <= 1:
                    self.status.emit("Duplikat-Undo: letzte Seite bleibt")
                    return False
                delete_pages(self.pdf_path, [idx])
                if self.store is not None:
                    if entry.get("ann_remapped") and self.store.can_undo():
                        self.store.undo()
                    if "page_groups" in entry:
                        self.store._meta["page_groups"] = dict(entry["page_groups"] or {})
                    if "page_favorites" in entry:
                        favs = list(entry["page_favorites"] or [])
                        if favs:
                            self.store._meta["page_favorites"] = favs
                        else:
                            self.store._meta.pop("page_favorites", None)
                    self.store.dirty = True
                    try:
                        self.schedule_sidecar_save(force=True)
                    except Exception:
                        pass
                from ild_pdf import PdfDocument

                with PdfDocument(self.pdf_path, password=self.password) as doc:
                    self.page_count = len(doc)
                    self._reload_page_labels()
                self.page_index = min(max(0, idx - 1 if idx > 0 else 0), max(0, self.page_count - 1))
                self._selected_ann_id = None
                self._selected_ann_ids = set()
                self.canvas.set_selected_id(None)
                clear_render_cache(self.pdf_path)
                self.refresh()
                self.annotations_changed.emit()
                self.page_changed.emit(self.page_index)
                self.document_changed.emit()
                self.status.emit(f"Seiten-Duplikat rückgängig (S. {idx + 1})")
                return True
            if kind == "rotate":
                idx = int(entry["index"])
                deg = int(entry.get("degrees", 90))
                rotate_page(self.pdf_path, idx, -int(deg))
                if self.store is not None and entry.get("ann_remapped") and self.store.can_undo():
                    self.store.undo()
                    try:
                        self.schedule_sidecar_save(force=True)
                    except Exception:
                        pass
                clear_render_cache(self.pdf_path)
                if idx != self.page_index:
                    self.page_index = idx
                self.refresh()
                self.annotations_changed.emit()
                self.document_changed.emit()
                self.status.emit(f"Seitendrehung rückgängig (S. {idx + 1})")
                return True
            if kind == "flip":
                idx = int(entry["index"])
                horizontal = bool(entry.get("horizontal"))
                vertical = bool(entry.get("vertical"))
                # Spiegeln ist involutorisch: gleiche Achse erneut = Undo
                flip_page(
                    self.pdf_path,
                    idx,
                    horizontal=horizontal,
                    vertical=vertical,
                )
                if self.store is not None and entry.get("ann_remapped") and self.store.can_undo():
                    self.store.undo()
                    try:
                        self.schedule_sidecar_save(force=True)
                    except Exception:
                        pass
                clear_render_cache(self.pdf_path)
                if idx != self.page_index:
                    self.page_index = idx
                self.refresh()
                self.annotations_changed.emit()
                self.document_changed.emit()
                self.status.emit(f"Drehen/Spiegeln rückgängig (S. {idx + 1})")
                return True
            if kind == "reorder":
                inverse = [int(i) for i in (entry.get("inverse") or [])]
                if not inverse or len(inverse) != self.page_count:
                    self.status.emit("Seiten-Undo: ungültige Reihenfolge")
                    return False
                if sorted(inverse) != list(range(self.page_count)):
                    self.status.emit("Seiten-Undo: ungültige Reihenfolge")
                    return False
                # Nur PDF zurücksetzen; Ann.-Remap über Store-Undo, Meta aus Snapshot
                reorder_pages(self.pdf_path, inverse)
                if self.store is not None:
                    if entry.get("ann_remapped") and self.store.can_undo():
                        self.store.undo()
                    if "page_groups" in entry:
                        self.store._meta["page_groups"] = dict(entry["page_groups"] or {})
                    if "page_favorites" in entry:
                        favs = list(entry["page_favorites"] or [])
                        if favs:
                            self.store._meta["page_favorites"] = favs
                        else:
                            self.store._meta.pop("page_favorites", None)
                    self.store.dirty = True
                    try:
                        self.schedule_sidecar_save(force=True)
                    except Exception:
                        pass
                from ild_pdf import PdfDocument

                with PdfDocument(self.pdf_path, password=self.password) as doc:
                    self.page_count = len(doc)
                    self._reload_page_labels()
                self.page_index = min(max(0, self.page_index), max(0, self.page_count - 1))
                self._selected_ann_id = None
                self._selected_ann_ids = set()
                self.canvas.set_selected_id(None)
                clear_render_cache(self.pdf_path)
                self.refresh()
                self.annotations_changed.emit()
                self.page_changed.emit(self.page_index)
                self.document_changed.emit()
                self.status.emit("Seitenreihenfolge rückgängig (Undo)")
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
            label = None
            try:
                label = self.store.peek_redo_label()
            except Exception:
                label = None
            self.store.redo()
            self.schedule_sidecar_save(force=True)
            self.refresh()
            self.annotations_changed.emit()
            # Nach Redo von Glätten denselben Toast wie beim Anwenden — 2.2.4
            if label == "Freihand glätten":
                self._show_smooth_status_toast("Glättung angewandt")
            else:
                self.status.emit("Annotation wiederholt")
            return True
        except Exception as e:
            QMessageBox.warning(self, "Wiederholen", str(e))
            return False

    def _pixmap_from_rendered_page(
        self, page_index: int, scale: float, *, grayscale: bool | None = None
    ):
        """Seite via pypdfium2 rendern und als QPixmap (mit Ann.) zurückgeben."""
        from PySide6.QtGui import QImage, QPixmap

        gray = bool(self._grayscale if grayscale is None else grayscale)
        img = render_page(self.pdf_path, page_index, scale=scale, grayscale=gray)
        anns = self.store.for_page(page_index) if self.store else []
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        data = img.tobytes("raw", "RGBA")
        qimg = QImage(data, img.width, img.height, QImage.Format_RGBA8888)
        pm = QPixmap.fromImage(qimg.copy())
        # Annotationen auf temporärem Canvas zeichnen
        self.canvas.set_page_image(img, anns, scale=scale)
        drawn = self.canvas.pixmap()
        if drawn is not None and not drawn.isNull():
            return drawn
        return pm

    def print_current_page(self) -> bool:
        """Aktuelle PDF-Seite (mit Annotationen) über Qt PrintDialog drucken."""
        if not self.pdf_path:
            QMessageBox.information(self, "Drucken", "Kein PDF geladen.")
            return False
        try:
            from PySide6.QtGui import QPainter
            from PySide6.QtPrintSupport import QPrintDialog, QPrinter

            scale = max(float(self.scale or 1.5), 2.0)
            pm = self._pixmap_from_rendered_page(self.page_index, scale)
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

    def print_document(self) -> bool:
        """PDF-Dokument (Bereich + DPI + Graustufen + Vorschau Zoom/Seiten) — 1.0.7."""
        if not self.pdf_path:
            QMessageBox.information(self, "Drucken", "Kein PDF geladen.")
            return False
        try:
            from PySide6.QtGui import QPainter
            from PySide6.QtPrintSupport import QPrintDialog, QPrinter
            from PySide6.QtWidgets import QApplication, QProgressDialog

            from instantlensdoc.core.app_settings import (
                set_export_raster_dpi,
                set_print_grayscale,
                set_print_preview,
            )
            from instantlensdoc.ui.print_preview_dialog import PrintPreviewDialog
            from instantlensdoc.ui.print_range_dialog import PrintRangeDialog

            n = int(self.page_count or 0)
            if n <= 0:
                QMessageBox.warning(self, "Drucken", "PDF hat keine Seiten.")
                return False

            # Seitenbereich + DPI + Graustufen + Vorschau-Toggle — 1.0.6
            range_dlg = PrintRangeDialog(n, self)
            if range_dlg.exec() != PrintRangeDialog.Accepted:
                return False
            start, end = range_dlg.page_range()
            start = max(0, min(start, n - 1))
            end = max(start + 1, min(end, n))
            pages = list(range(start, end))
            if not pages:
                return False
            dpi = int(range_dlg.dpi())
            gray = bool(range_dlg.grayscale())
            show_preview = bool(range_dlg.preview())
            try:
                set_export_raster_dpi(dpi)
                set_print_grayscale(gray)
                set_print_preview(show_preview)
            except Exception:
                pass
            scale = max(dpi / 72.0, 1.0)

            # Optionale Vorschau: Zoom +/- + Seitenwahl bei Mehrseiten — 1.0.7
            if show_preview:
                thumb_scale = min(scale, 2.0)

                def _preview_pm(pidx: int, _ts=thumb_scale, _g=gray):
                    return self._pixmap_from_rendered_page(
                        pidx, _ts, grayscale=_g
                    )

                preview_pm = _preview_pm(pages[0])
                preview_dlg = PrintPreviewDialog(
                    preview_pm,
                    page_label=f"Seite {pages[0] + 1}",
                    page_count=len(pages),
                    dpi=dpi,
                    grayscale=gray,
                    parent=self,
                    default_preview=True,
                    pages=list(pages),
                    pixmap_provider=_preview_pm,
                )
                if preview_dlg.exec() != PrintPreviewDialog.Accepted:
                    try:
                        self.refresh()
                    except Exception:
                        pass
                    return False
                try:
                    set_print_preview(preview_dlg.preview_enabled())
                except Exception:
                    pass
                if not preview_dlg.preview_enabled():
                    # Toggle abgewählt: weiterdrucken ohne künftige Vorschau
                    pass

            printer = QPrinter(QPrinter.HighResolution)
            printer.setDocName(str(self.pdf_path.stem))
            dlg = QPrintDialog(printer, self)
            dlg.setWindowTitle("PDF-Dokument drucken")
            if dlg.exec() != QPrintDialog.Accepted:
                return False

            total = len(pages)
            # Fortschrittsdialog nur bei Mehrseiten-Druck, abbrechenbar — 1.0.4/1.0.5
            progress: QProgressDialog | None = None
            if total > 1:
                progress = QProgressDialog(
                    "Drucke PDF…", "Abbrechen", 0, total, self
                )
                progress.setWindowTitle("Dokumentdruck")
                progress.setWindowModality(Qt.WindowModal)
                progress.setMinimumDuration(0)
                progress.setValue(0)
                QApplication.processEvents()
            painter = QPainter(printer)
            printed = 0
            canceled = False
            gray_lbl = ", Graustufen" if gray else ""
            try:
                for idx, i in enumerate(pages):
                    if progress is not None:
                        QApplication.processEvents()
                        if progress.wasCanceled():
                            canceled = True
                            break
                        progress.setValue(idx)
                        progress.setLabelText(
                            f"Drucke Seite {i + 1} / {n} "
                            f"({idx + 1}/{total}, {dpi} DPI{gray_lbl})…"
                        )
                        QApplication.processEvents()
                        if progress.wasCanceled():
                            canceled = True
                            break
                    if canceled:
                        break
                    pm = self._pixmap_from_rendered_page(i, scale, grayscale=gray)
                    if pm is None or pm.isNull():
                        continue
                    if printed > 0:
                        printer.newPage()
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
                    printed += 1
                if progress is not None and not canceled:
                    progress.setValue(total)
            finally:
                # Abbruch: Job verwerfen (kein halber Druckauftrag) — 1.0.5
                if canceled:
                    try:
                        if painter.isActive():
                            painter.end()
                    except Exception:
                        pass
                    try:
                        printer.abort()
                    except Exception:
                        pass
                else:
                    try:
                        if painter.isActive():
                            painter.end()
                    except Exception:
                        pass
                if progress is not None:
                    try:
                        progress.close()
                    except Exception:
                        pass
            try:
                self.refresh()
            except Exception:
                pass
            if canceled:
                self.status.emit("Druck abgebrochen")
                return False
            self.status.emit(
                f"PDF-Dokument gedruckt (Seiten {start + 1}–{end}, "
                f"{printed} Seite(n), {dpi} DPI{gray_lbl})"
            )
            return True
        except Exception as e:
            QMessageBox.critical(self, "Drucken", f"Dokumentdruck fehlgeschlagen:\n{e}")
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

        from instantlensdoc.core.fulltext import truncate_display_text

        out: list[tuple[str, Annotation]] = []
        for a in self.store.annotations:
            kind = ANN_TYPE_LABELS.get(a.type.value, a.type.value)
            label = f"S{a.page + 1}: {kind}"
            if a.text:
                label += f" — {truncate_display_text(a.text, 40)}"
            elif a.type in (
                AnnotationType.MEASURE,
                AnnotationType.MEASURE_AREA,
                AnnotationType.MEASURE_ANGLE,
            ):
                label += f" — {a.measure_label(self.scale, unit=self._measure_unit())}"
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
            self._sidecar_save_timer.stop()
            self._sidecar_save_pending = False
            path = self.store.save(force=True)
            self.status.emit(
                f"Sidecar gespeichert: {path.name} ({len(self.store.annotations)})"
            )
            self.annotations_changed.emit()
            return True
        except Exception as e:
            QMessageBox.warning(self, "Annotationen speichern", str(e))
            return False

    def merge_duplicate_annotations(self) -> int:
        """Duplikate (gleiche Seite+BBox) finden; Vorschau-Dialog, dann optional Apply."""
        if not self.store or not self.pdf_path:
            QMessageBox.information(self, "Duplikate", "Kein PDF geladen.")
            return 0
        groups = self.store.find_duplicate_groups(tol=2.0, same_type=True)
        if not groups:
            QMessageBox.information(
                self,
                "Duplikate",
                "Keine Annotation-Duplikate (gleiche Seite + BBox) gefunden.",
            )
            self.status.emit("Keine Annotation-Duplikate")
            return 0
        n_groups = len(groups)
        from instantlensdoc.ui.merge_duplicates_dialog import (
            MergeDuplicatesPreviewDialog,
        )

        dlg = MergeDuplicatesPreviewDialog(groups, parent=self)
        if dlg.exec() != QDialog.Accepted:
            self.status.emit(f"{n_groups} Duplikat-Gruppe(n) — nicht zusammengeführt")
            return 0
        selected = dlg.groups_to_merge()
        if not selected:
            kept = len(dlg.groups_to_keep())
            self.status.emit(
                f"Keine Gruppe zum Mergen gewählt — {kept} Gruppe(n) behalten"
            )
            return 0
        removed = self.store.merge_duplicates(
            tol=2.0,
            same_type=True,
            keep="oldest",
            merge_text=True,
            merge_tags=True,
            groups=selected,
        )
        if removed:
            self.schedule_sidecar_save(force=True)
            self.refresh()
            self.annotations_changed.emit()
            undo_label = (
                self.store.peek_undo_label()
                if hasattr(self.store, "peek_undo_label")
                else None
            ) or "Duplikate zusammenführen"
            self.status.emit(
                f"{removed} Duplikat(e) zusammengeführt — Ctrl+Z: {undo_label}"
            )
        else:
            self.status.emit("Keine Duplikate entfernt")
        return removed

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

    def export_annotations_json_flatten(self) -> bool:
        """
        Annotation-Export Dialog: aktuelle Seite / Dokument als JSON (ildann-v4)
        + optional Flatten-PDF — 1.2.0/1.2.1 (Zielordner merken, Dateiname-Template).
        """
        if not self.store or not self.pdf_path:
            QMessageBox.information(self, "Annotationen", "Kein PDF geladen.")
            return False
        from instantlensdoc.ui.annotation_export_dialog import AnnotationExportDialog
        from instantlensdoc.ui.file_dialogs import confirm_overwrite_export

        page = int(self.page_index)
        page_ann = sum(1 for a in self.store.annotations if int(a.page) == page)
        dlg = AnnotationExportDialog(
            self,
            pdf_path=self.pdf_path,
            current_page=page,
            page_count=max(1, int(self.page_count or 1)),
            ann_count=len(self.store.annotations),
            page_ann_count=page_ann,
        )
        if dlg.exec() != AnnotationExportDialog.Accepted or not dlg.result_options:
            return False
        opts = dlg.result_options
        pages = [page] if opts.scope == "page" else None
        if not confirm_overwrite_export(opts.json_path, self):
            return False
        if opts.flatten and opts.flatten_path is not None:
            if not confirm_overwrite_export(opts.flatten_path, self):
                return False
        try:
            from instantlensdoc.core.app_settings import (
                remember_recent_dir,
                set_last_ann_export_dir,
                set_last_export_dir,
            )

            if self.store.dirty:
                self.schedule_sidecar_save(force=True)
            saved = self.store.export_json(opts.json_path, pages=pages)
            set_last_ann_export_dir(opts.json_path.parent)
            set_last_export_dir(opts.json_path.parent)
            remember_recent_dir(opts.json_path.parent)
            scope_lbl = f"Seite {page + 1}" if opts.scope == "page" else "Dokument"
            msg = f"JSON {scope_lbl}: {saved.name}"
            if opts.flatten and opts.flatten_path is not None:
                from ild_pdf import flatten_annotations_to_pdf

                bake_scale = max(float(self.scale), 1.5)
                flat_pages = [page] if opts.scope == "page" else None
                out_flat = flatten_annotations_to_pdf(
                    self.pdf_path,
                    self.store,
                    scale=bake_scale,
                    out_path=opts.flatten_path,
                    password=self.password,
                    grayscale=self._grayscale,
                    page_indices=flat_pages,
                )
                set_last_ann_export_dir(out_flat.parent)
                set_last_export_dir(out_flat.parent)
                remember_recent_dir(out_flat.parent)
                msg += f" + Flatten {out_flat.name}"
            self.status.emit(msg)
            QMessageBox.information(self, "Annotationen exportieren", msg)
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

    def export_measures_csv(self) -> bool:
        """Messwerte CSV · Live-Template · Quick-Insert · Reset·Esc — 2.1.5."""
        if not self.store or not self.pdf_path:
            QMessageBox.information(self, "Messwerte", "Kein PDF geladen.")
            return False
        measures = self.store.list_measure_annotations()
        if not measures:
            QMessageBox.information(self, "Messwerte", "Keine Mess-Annotationen vorhanden.")
            return False
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtWidgets import (
            QCheckBox,
            QDialog,
            QDialogButtonBox,
            QFileDialog,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QPushButton,
            QVBoxLayout,
        )

        from instantlensdoc.core.app_settings import (
            DEFAULT_MEASURE_CSV_FILENAME_TEMPLATE,
            dialog_start_dir,
            find_invalid_measure_csv_placeholders,
            format_measure_csv_filename,
            get_last_measure_csv_dir,
            get_measure_csv_filename_template,
            get_measure_csv_utf8_bom,
            highlight_measure_csv_template_html,
            set_last_measure_csv_dir,
            set_measure_csv_filename_template,
            set_measure_csv_utf8_bom,
        )
        from instantlensdoc.ui.file_dialogs import confirm_overwrite_export
        from instantlensdoc.ui.template_reset import (
            EscapeDiscardEditFilter,
            focus_line_edit_select_all,
            reset_line_edit_template,
        )

        opts = QDialog(self)
        opts.setWindowTitle("Messwerte als CSV")
        ol = QVBoxLayout(opts)
        ol.addWidget(
            QLabel(
                f"{len(measures)} Messwert(e) · Spalten Typ,Seite,Wert,Einheit · "
                f"Template {DEFAULT_MEASURE_CSV_FILENAME_TEMPLATE} — 2.1.5"
            )
        )
        chk_bom = QCheckBox("UTF-8 BOM (Excel)")
        chk_bom.setChecked(get_measure_csv_utf8_bom())
        chk_bom.setToolTip("CSV mit UTF-8-BOM schreiben (Excel-freundlich) — 2.1.2")
        ol.addWidget(chk_bom)

        tpl_row = QHBoxLayout()
        tpl_row.addWidget(QLabel("Dateiname:"))
        tpl_edit = QLineEdit(get_measure_csv_filename_template())
        tpl_edit.setPlaceholderText(DEFAULT_MEASURE_CSV_FILENAME_TEMPLATE)
        tpl_edit.setToolTip(
            "Live-Dateiname-Template; Platzhalter {stem}/{date}; "
            "Quick-Insert; Reset Default (Bestätigung nur bei Abweichung · "
            "Fokus+Selektion); Esc im Feld verwirft Edit (nicht speichern) — 2.1.5"
        )
        tpl_row.addWidget(tpl_edit, 1)
        preview = QLabel("")
        preview.setTextFormat(Qt.RichText)
        preview.setWordWrap(True)
        preview.setToolTip(
            "Live-Vorschau Mess-CSV-Dateiname; ungültige Platzhalter rot — 2.1.5"
        )

        def _update_preview() -> None:
            import html as _html

            tpl = tpl_edit.text().strip() or DEFAULT_MEASURE_CSV_FILENAME_TEMPLATE
            stem = self.pdf_path.stem if self.pdf_path else "dokument"
            name = format_measure_csv_filename(stem, template=tpl)
            html = highlight_measure_csv_template_html(tpl)
            invalid = find_invalid_measure_csv_placeholders(tpl)
            note = f" → <code>{_html.escape(name)}</code>"
            if invalid:
                note += f" · ungültig: {', '.join(invalid)}"
            preview.setText(f"CSV: {html}{note}")

        tpl_esc = EscapeDiscardEditFilter(
            tpl_edit, on_discard=_update_preview, parent=opts
        )

        for token in ("{stem}", "{date}"):
            btn = QPushButton(token)
            btn.setAutoDefault(False)
            btn.setDefault(False)
            btn.setFocusPolicy(Qt.TabFocus)
            btn.setToolTip(f"Platzhalter {token} an Cursor einfügen — 2.1.5")

            def _insert(t=token) -> None:
                tpl_edit.insert(t)
                tpl_edit.setFocus()
                _update_preview()
                tpl_esc.commit()

            btn.clicked.connect(_insert)
            tpl_row.addWidget(btn)
        btn_reset_tpl = QPushButton("Reset Default")
        btn_reset_tpl.setAutoDefault(False)
        btn_reset_tpl.setDefault(False)
        btn_reset_tpl.setFocusPolicy(Qt.TabFocus)
        btn_reset_tpl.setToolTip(
            f"Reset Default ({DEFAULT_MEASURE_CSV_FILENAME_TEMPLATE}) "
            "Bestätigung nur bei Abweichung; danach Fokus+Selektion; "
            "gemeinsamer Helper mit Diff-Reset — 2.1.5"
        )

        def _focus_tpl_select_all() -> None:
            """Fokus + Selektion (gemeinsamer Helper) — 2.1.5."""
            focus_line_edit_select_all(tpl_edit)

        def _reset_tpl() -> None:
            """Mess-CSV Reset Default — gemeinsamer Helper mit Diff — 2.1.5."""
            default = DEFAULT_MEASURE_CSV_FILENAME_TEMPLATE

            def _after() -> None:
                _update_preview()
                tpl_esc.commit(default)

            reset_line_edit_template(
                opts,
                tpl_edit,
                default,
                title="Reset Default",
                body_prefix="Mess-CSV-Template auf Default zurücksetzen?",
                on_updated=_after,
                after_focus=False,
            )
            QTimer.singleShot(0, _focus_tpl_select_all)

        btn_reset_tpl.clicked.connect(_reset_tpl)
        tpl_row.addWidget(btn_reset_tpl)
        ol.addLayout(tpl_row)
        ol.addWidget(preview)
        tpl_edit.textChanged.connect(lambda _t: _update_preview())
        _update_preview()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Speichern…")
        buttons.accepted.connect(opts.accept)
        buttons.rejected.connect(opts.reject)
        ol.addWidget(buttons)
        if opts.exec() != QDialog.Accepted:
            return False
        utf8_bom = bool(chk_bom.isChecked())
        set_measure_csv_utf8_bom(utf8_bom)
        tpl = tpl_edit.text().strip() or DEFAULT_MEASURE_CSV_FILENAME_TEMPLATE
        set_measure_csv_filename_template(tpl)

        start = dialog_start_dir(get_last_measure_csv_dir())
        fname = format_measure_csv_filename(self.pdf_path.stem, template=tpl)
        default = str(Path(start) / fname)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Messwerte als CSV exportieren",
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
            unit = self._measure_unit()
            saved = self.store.export_measures_csv(
                dest, scale=self.scale, unit=unit, utf8_bom=utf8_bom
            )
            set_last_measure_csv_dir(saved.parent)
            bom_s = "BOM" if utf8_bom else "ohne BOM"
            self.status.emit(
                f"Messwerte CSV: {saved.name} ({len(measures)} · {unit} · {bom_s})"
            )
            return True
        except Exception as e:
            QMessageBox.warning(self, "Messwerte CSV exportieren", str(e))
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
                self.schedule_sidecar_save(force=True)
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
            self.schedule_sidecar_save(force=True)
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

    def import_native_pdf_comments(self) -> bool:
        """Native PDF-Markup → Sidecar; Status ersetzt/übersprungen/neu·kopierbar — 2.1.3."""
        if not self.store or not self.pdf_path:
            QMessageBox.information(self, "PDF-Kommentare", "Kein PDF geladen.")
            return False
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QApplication,
            QCheckBox,
            QDialog,
            QDialogButtonBox,
            QLabel,
            QProgressDialog,
            QVBoxLayout,
        )

        from ild_pdf.pdf_ann_import import import_native_into_store
        from instantlensdoc.core.app_settings import (
            get_native_ann_import_save_sidecar,
            set_native_ann_import_save_sidecar,
        )

        # 1) Dry-Run: Zähler ohne Schreiben — 2.1.1
        try:
            dry = import_native_into_store(
                self.store,
                self.pdf_path,
                replace=False,
                scale=1.0,
                password=self.password,
                duplicate_strategy="skip",
                dry_run=True,
            )
        except Exception as e:
            QMessageBox.warning(self, "PDF-Kommentare importieren", str(e))
            return False

        dry_dlg = QDialog(self)
        dry_dlg.setWindowTitle("PDF-Kommentare importieren — Dry-Run")
        dry_lay = QVBoxLayout(dry_dlg)
        dry_status = dry.copyable_status_text()
        dry_lbl = QLabel(
            f"Dry-Run: {dry.status_counts_de()}\n"
            f"Kandidaten={dry.candidates}, Duplikate={dry.duplicates_found}, "
            f"Typen-Skip={dry.skipped}, Seiten={dry.pages_scanned}.\n\n"
            "Anhängen = Sidecar erweitern · Ersetzen = Sidecar neu.\n"
            "Hinweis: grobe Übernahme (QuadPoints→Box); Link/Widget übersprungen."
        )
        dry_lbl.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        dry_lbl.setToolTip(
            "Status ersetzt/übersprungen/neu — Text selektierbar/kopierbar — 2.1.3"
        )
        dry_lay.addWidget(dry_lbl)
        from PySide6.QtWidgets import QPushButton as _QPushButton

        btn_copy_dry = _QPushButton("Status kopieren")
        btn_copy_dry.setToolTip(
            "Detail-Status (ersetzt/übersprungen/neu) in Zwischenablage · "
            "Toast + A11y Announcement — 2.1.4"
        )

        def _copy_dry_status() -> None:
            self._copy_import_status_to_clipboard(
                dry_status, toast="Import-Status kopiert (Dry-Run)"
            )

        btn_copy_dry.clicked.connect(_copy_dry_status)
        dry_lay.addWidget(btn_copy_dry)
        chk_save_sidecar = QCheckBox("Nach Import Sidecar speichern")
        chk_save_sidecar.setChecked(get_native_ann_import_save_sidecar())
        chk_save_sidecar.setToolTip(
            "Wenn an: Sidecar nach erfolgreichem Import sofort speichern — 2.1.2"
        )
        dry_lay.addWidget(chk_save_sidecar)
        dry_btns = QDialogButtonBox()
        btn_append = dry_btns.addButton("Anhängen", QDialogButtonBox.AcceptRole)
        btn_replace = dry_btns.addButton("Ersetzen", QDialogButtonBox.ActionRole)
        btn_cancel = dry_btns.addButton(QDialogButtonBox.Cancel)
        dry_lay.addWidget(dry_btns)
        choice = {"v": "cancel"}

        def _append() -> None:
            choice["v"] = "append"
            dry_dlg.accept()

        def _replace() -> None:
            choice["v"] = "replace"
            dry_dlg.accept()

        btn_append.clicked.connect(_append)
        btn_replace.clicked.connect(_replace)
        btn_cancel.clicked.connect(dry_dlg.reject)
        if dry_dlg.exec() != QDialog.Accepted or choice["v"] == "cancel":
            self.status.emit("PDF-Import abgebrochen (Dry-Run)")
            return False
        replace = choice["v"] == "replace"
        save_sidecar = bool(chk_save_sidecar.isChecked())
        set_native_ann_import_save_sidecar(save_sidecar)

        # Duplikat-Strategie nur beim Anhängen — 2.1.1
        dup_strategy = "keep"
        if not replace and dry.duplicates_found > 0:
            dup_box = QMessageBox(self)
            dup_box.setWindowTitle("Duplikat-Strategie")
            dup_box.setText(
                f"{dry.duplicates_found} mögliche Duplikate zur bestehenden Sidecar.\n"
                "Wie verfahren?"
            )
            btn_keep = dup_box.addButton("Beide behalten", QMessageBox.AcceptRole)
            btn_skip = dup_box.addButton("Duplikate überspringen", QMessageBox.ActionRole)
            btn_repl = dup_box.addButton("Duplikate ersetzen", QMessageBox.ActionRole)
            dup_box.addButton(QMessageBox.Cancel)
            dup_box.exec()
            clicked = dup_box.clickedButton()
            if clicked is None or clicked == dup_box.button(QMessageBox.Cancel):
                self.status.emit("PDF-Import abgebrochen")
                return False
            if clicked == btn_skip:
                dup_strategy = "skip"
            elif clicked == btn_repl:
                dup_strategy = "replace"
            else:
                dup_strategy = "keep"
            _ = btn_keep  # Role-Marker

        # 2) Import mit Fortschritt + Abbruch — 2.1.1
        prog = QProgressDialog(
            "PDF-Kommentare importieren…", "Abbrechen", 0, max(1, dry.pages_scanned), self
        )
        prog.setWindowTitle("PDF-Kommentar-Import")
        prog.setWindowModality(Qt.WindowModal)
        prog.setMinimumDuration(0)
        prog.setValue(0)
        cancelled = {"v": False}

        def on_progress(cur: int, tot: int, label: str) -> None:
            prog.setMaximum(max(1, tot))
            prog.setValue(max(0, cur - 1))
            prog.setLabelText(f"{label} ({cur}/{tot})")
            QApplication.processEvents()
            if prog.wasCanceled():
                cancelled["v"] = True

        def should_cancel() -> bool:
            QApplication.processEvents()
            if prog.wasCanceled():
                cancelled["v"] = True
            return bool(cancelled["v"])

        try:
            result = import_native_into_store(
                self.store,
                self.pdf_path,
                replace=replace,
                scale=1.0,
                password=self.password,
                duplicate_strategy=dup_strategy,
                dry_run=False,
                on_progress=on_progress,
                should_cancel=should_cancel,
            )
            if not result.cancelled:
                prog.setValue(prog.maximum())
            prog.close()
            status_line = result.status_counts_de()
            copy_text = result.copyable_status_text()
            if result.cancelled:
                self.status.emit(f"PDF-Import abgebrochen — {status_line}")
                self._show_import_status_copyable(
                    "PDF-Kommentare — Abbruch",
                    f"Import abgebrochen.\n{status_line}\n{result.summary_de()}",
                    copy_text,
                )
                return False
            if save_sidecar:
                self.schedule_sidecar_save(force=True)
            self.refresh()
            self.annotations_changed.emit()
            mode = "ersetzt" if replace else "angehängt"
            side_s = " · Sidecar gespeichert" if save_sidecar else " · Sidecar nicht gespeichert"
            self.status.emit(f"PDF-Import ({mode}): {status_line}{side_s}")
            # Ergebnis-Status immer kopierbar anbieten — 2.1.3
            self._show_import_status_copyable(
                "PDF-Kommentare — Status",
                (
                    f"PDF-Import ({mode}): {status_line}{side_s}\n"
                    f"{result.summary_de()}"
                    if result.imported > 0
                    else f"Keine Annotationen übernommen.\n{status_line}"
                ),
                copy_text,
            )
            return True
        except Exception as e:
            prog.close()
            QMessageBox.warning(self, "PDF-Kommentare importieren", str(e))
            return False

    def _announce_import_status_toast(self, msg: str) -> None:
        """
        Accessibility-Announcement für Import-Status-Toast —
        gleiche Pipeline wie OCR/HC (AccessibleName/Description +
        AnnouncementEvent, Fallback NameChanged) — 2.1.4/2.1.5.
        """
        target = self
        win = self.window()
        if win is not None and hasattr(win, "statusBar"):
            try:
                sb = win.statusBar()
                if sb is not None:
                    target = sb
            except Exception:
                pass
        try:
            target.setAccessibleName(msg)
            if hasattr(target, "setAccessibleDescription"):
                target.setAccessibleDescription(msg)
        except Exception:
            pass
        try:
            from PySide6.QtGui import QAccessible, QAccessibleAnnouncementEvent

            ev = QAccessibleAnnouncementEvent(target, msg)
            QAccessible.updateAccessibility(ev)
        except Exception:
            try:
                from PySide6.QtGui import QAccessible, QAccessibleEvent

                ev = QAccessibleEvent(target, QAccessible.Event.NameChanged)
                QAccessible.updateAccessibility(ev)
            except Exception:
                pass

    def _show_import_status_toast(self, msg: str) -> None:
        """
        Import-Status Toast: Dauer aus OCR-Defaults-Toast-Settings;
        Klick fokussiert Statusleiste/Log falls vorhanden; A11y — 2.1.5.
        """
        from PySide6.QtCore import QTimer
        from PySide6.QtCore import Qt as _Qt

        try:
            from instantlensdoc.core.app_settings import get_ocr_defaults_toast_sec

            ms = max(1, int(get_ocr_defaults_toast_sec())) * 1000
        except Exception:
            ms = 2000
        self._import_status_toast_token = (
            int(getattr(self, "_import_status_toast_token", 0)) + 1
        )
        token = self._import_status_toast_token
        self._announce_import_status_toast(msg)
        self.status.emit(msg)
        win = self.window()
        if win is not None:
            try:
                win._import_status_toast_active = True
                win._import_status_toast_msg = msg
            except Exception:
                pass
        if win is not None and hasattr(win, "statusBar"):
            try:
                sb = win.statusBar()
                sb.showMessage(msg, ms)
                sb.setToolTip(
                    "Klick fokussiert Statusleiste/Log falls vorhanden — 2.1.5"
                )
                sb.setCursor(_Qt.PointingHandCursor)
            except Exception:
                pass

        def _clear() -> None:
            if token != getattr(self, "_import_status_toast_token", 0):
                return
            target = self
            if win is not None and hasattr(win, "statusBar"):
                try:
                    sb = win.statusBar()
                    if sb is not None:
                        target = sb
                        cur = sb.currentMessage() or ""
                        if msg in cur or "Import-Status" in cur:
                            tip = sb.toolTip() or ""
                            if tip.startswith("Klick fokussiert Statusleiste"):
                                sb.setToolTip("")
                                sb.unsetCursor()
                        if getattr(win, "_import_status_toast_active", False):
                            win._import_status_toast_active = False
                except Exception:
                    pass
            try:
                if (getattr(target, "accessibleName", lambda: "")() or "") == msg or (
                    hasattr(target, "accessibleName")
                    and (target.accessibleName() or "") == msg
                ):
                    target.setAccessibleName("")
                    if hasattr(target, "setAccessibleDescription"):
                        target.setAccessibleDescription("")
            except Exception:
                pass

        QTimer.singleShot(ms, _clear)

    def _copy_import_status_to_clipboard(
        self, copy_text: str, *, toast: str = "Import-Status kopiert"
    ) -> None:
        """Clipboard + Toast (OCR-Dauer) + A11y · Klick→Status/Log — 2.1.5."""
        from PySide6.QtWidgets import QApplication

        clip = QApplication.clipboard()
        if clip is not None:
            clip.setText((copy_text or "").rstrip() + "\n")
        self._show_import_status_toast(toast)

    def _show_import_status_copyable(
        self, title: str, text: str, copy_text: str
    ) -> None:
        """Import-Status Dialog: selektierbarer Text + Kopieren·Toast·A11y — 2.1.4."""
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QLabel, QMessageBox

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Information)
        box.setWindowTitle(title)
        box.setText(text)
        box.setStandardButtons(QMessageBox.Ok)
        copy_btn = box.addButton("Status kopieren", QMessageBox.ActionRole)
        for lbl in box.findChildren(QLabel):
            lbl.setTextInteractionFlags(
                Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
            )
        box.exec()
        if box.clickedButton() is copy_btn:
            self._copy_import_status_to_clipboard(
                copy_text or text, toast="Import-Status kopiert"
            )

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
                self.schedule_sidecar_save(force=True)
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
            self.schedule_sidecar_save()
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

    def clear_annotations_on_page(
        self,
        page_index: int | None = None,
        *,
        filtered_ids: list[str] | None = None,
    ) -> int:
        """
        Annotationen einer Seite löschen — Bestätigung + Zähler + Undo.
        Option: nur sichtbare/gefilterte (filtered_ids) — 1.1.2.
        """
        from PySide6.QtWidgets import QCheckBox

        if not self.store:
            self.status.emit("Keine Annotationen")
            return 0
        page = self.page_index if page_index is None else int(page_index)
        anns = self.store.for_page(page)
        if not anns:
            QMessageBox.information(
                self,
                "Alle Annotationen auf Seite löschen",
                f"Keine Annotationen auf Seite {page + 1}.",
            )
            return 0
        n_all = len(anns)
        filt_set = {str(x) for x in (filtered_ids or [])}
        n_filt = (
            sum(1 for a in anns if str(a.id) in filt_set) if filtered_ids is not None else n_all
        )
        # Filter aktiv = gefilterte Menge echt kleiner als alle auf der Seite
        filter_active = filtered_ids is not None and n_filt < n_all
        zero_filtered = filtered_ids is not None and n_filt <= 0

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle("Alle Annotationen auf Seite löschen")
        ann_word = "Annotation" if n_all == 1 else "Annotationen"
        box.setText(
            f"{n_all} {ann_word} auf Seite {page + 1} löschen?\n"
            "Rückgängig mit Ctrl+Z (ein Undo-Schritt)."
        )
        cb = QCheckBox("Nur sichtbare/gefilterte Annotationen")
        cb.setToolTip(
            "Nur die aktuell in der Sidebar sichtbaren/gefilterten "
            "Annotationen dieser Seite löschen — 1.1.2/1.1.4"
        )
        # Bei 0 Treffern: Option sichtbar, aber nicht vorausgewählt — 1.1.4
        from instantlensdoc.core.i18n import tr_ann_zero_filtered

        zero_status = tr_ann_zero_filtered(page + 1)
        cb.setChecked(bool(filter_active and n_filt > 0))
        cb.setEnabled(filtered_ids is not None)
        if zero_filtered:
            box.setInformativeText(zero_status)
            self.status.emit(zero_status)
        elif filter_active:
            box.setInformativeText(
                f"Mit Filter: {n_filt} von {n_all} sichtbar/gefiltert."
            )
        box.setCheckBox(cb)
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)
        yes_btn = box.button(QMessageBox.Yes)

        def _sync_filtered_yes(checked: bool = False) -> None:
            if cb.isChecked() and n_filt <= 0:
                if yes_btn is not None:
                    yes_btn.setEnabled(False)
                box.setInformativeText(zero_status)
            else:
                if yes_btn is not None:
                    yes_btn.setEnabled(True)
                if zero_filtered and not cb.isChecked():
                    box.setInformativeText(zero_status)
                elif filter_active and n_filt > 0:
                    box.setInformativeText(
                        f"Mit Filter: {n_filt} von {n_all} sichtbar/gefiltert."
                    )

        cb.toggled.connect(_sync_filtered_yes)
        _sync_filtered_yes(cb.isChecked())
        if box.exec() != QMessageBox.Yes:
            return 0

        only_ids = None
        if cb.isChecked() and filtered_ids is not None:
            only_ids = list(filt_set)
            if n_filt <= 0:
                self.status.emit(zero_status)
                return 0

        n = self.store.clear_page(page, only_ids=only_ids)
        if n <= 0:
            return 0
        self._selected_ann_id = None
        self._selected_ann_ids = set()
        self.canvas.set_selected_id(None)
        try:
            self.schedule_sidecar_save(force=True)
        except Exception as e:
            QMessageBox.warning(self, "Alle Annotationen auf Seite löschen", str(e))
            return 0
        self.refresh()
        self.annotations_changed.emit()
        if only_ids is not None:
            ann_word = "Annotation" if n == 1 else "Annotationen"
            self.status.emit(
                f"{n} {ann_word} (gefiltert) auf Seite {page + 1} gelöscht"
            )
        else:
            self.status.emit(f"{n} Annotation(en) auf Seite {page + 1} gelöscht")
        return n

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
            self.schedule_sidecar_save(force=True)
        except Exception as e:
            QMessageBox.warning(self, "Schwärzung", str(e))
            return
        self.refresh()
        self.annotations_changed.emit()
        self.status.emit(f"{len(reds)} Schwärzungs-Annotation(en) gelöscht")

    def bake_redactions(self, *, remove_sidecar: bool | None = None):
        """Redactions anwenden → neues PDF mit schwarzen Flächen (Bake) — 1.3.0."""
        if not self.store or not self.pdf_path:
            return
        reds = [a for a in self.store.annotations if a.type == AnnotationType.REDACTION]
        if not reds:
            QMessageBox.information(self, "Redactions", "Keine Schwärzungs-Annotationen.")
            return
        by_page: dict[int, int] = {}
        for a in reds:
            by_page[a.page] = by_page.get(a.page, 0) + 1
        pages = ", ".join(f"S.{p + 1}:{n}" for p, n in sorted(by_page.items()))

        from PySide6.QtWidgets import (
            QCheckBox,
            QDialog,
            QDialogButtonBox,
            QFileDialog,
            QLabel,
            QVBoxLayout,
        )

        from instantlensdoc.ui.file_dialogs import confirm_overwrite_export

        dlg = QDialog(self)
        dlg.setWindowTitle("Redactions anwenden")
        lay = QVBoxLayout(dlg)
        lay.addWidget(
            QLabel(
                f"{len(reds)} Schwärzung(en) als schwarze Flächen in ein neues PDF schreiben?\n"
                f"Verteilung: {pages}\n\n"
                "Hinweis: Basis-Redaction — Text unter der Fläche kann in der\n"
                "PDF-Textschicht noch selektierbar sein."
            )
        )
        chk = QCheckBox("Annotationen nach Anwenden aus Sidecar entfernen")
        chk.setChecked(True if remove_sidecar is None else bool(remove_sidecar))
        lay.addWidget(chk)
        # Auch Sidecar speichern — Default an — 1.3.4
        chk_sidecar = QCheckBox("Auch Sidecar speichern")
        chk_sidecar.setChecked(True)
        chk_sidecar.setToolTip(
            "Sidecar nach Anwenden speichern; bei Schreibfehler Warnung "
            "mit Option PDF-Bake fortzusetzen — 1.3.5"
        )
        lay.addWidget(chk_sidecar)
        buttons = QDialogButtonBox(QDialogButtonBox.Yes | QDialogButtonBox.No)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        lay.addWidget(buttons)
        if dlg.exec() != QDialog.Accepted:
            return
        remove = chk.isChecked()
        save_sidecar = chk_sidecar.isChecked()
        src = Path(self.pdf_path)
        default_name = f"{src.stem}_redacted.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Redactions anwenden — neues PDF",
            str(src.with_name(default_name)),
            "PDF (*.pdf)",
        )
        if not path:
            return
        dest = Path(path)
        if dest.suffix.lower() != ".pdf":
            dest = dest.with_suffix(".pdf")
        if not confirm_overwrite_export(dest, self):
            return
        try:
            from ild_pdf.redact import bake_redactions as apply_redactions
            from ild_pdf.render import clear_render_cache

            apply_redactions(
                self.pdf_path,
                self.store,
                scale=self.scale,
                out_path=dest,
                remove_from_store=remove,
            )
            sidecar_ok = True
            sidecar_err: Exception | None = None
            if save_sidecar:
                # Quell-Sidecar flushen (falls remove nicht schon gespeichert hat)
                try:
                    self.schedule_sidecar_save(force=True)
                except Exception as e:
                    sidecar_ok = False
                    sidecar_err = e
                # Sidecar neben neues PDF schreiben — 1.3.4/1.3.5
                try:
                    if dest.resolve() != src.resolve():
                        side_dest = dest.with_name(dest.stem + ".ildann.json")
                        self.store.save(path=side_dest, force=True)
                except Exception as e:
                    sidecar_ok = False
                    sidecar_err = e
                if not sidecar_ok:
                    # Sidecar-Fehler: Warnung, Fortsetzen-Option Settings merken — 1.3.6
                    from instantlensdoc.core.app_settings import (
                        get_redaction_bake_continue_on_sidecar_skip,
                        set_redaction_bake_continue_on_sidecar_skip,
                    )

                    prefer_continue = bool(
                        get_redaction_bake_continue_on_sidecar_skip()
                    )
                    warn = QMessageBox(self)
                    warn.setIcon(QMessageBox.Warning)
                    warn.setWindowTitle("Redactions — Sidecar")
                    warn.setText("Sidecar konnte nicht geschrieben werden")
                    warn.setInformativeText(
                        f"{sidecar_err}\n\n"
                        f"Das geschwärzte PDF wurde bereits geschrieben:\n{dest}\n\n"
                        "PDF-Bake trotzdem fortsetzen?"
                    )
                    warn.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                    warn.setDefaultButton(
                        QMessageBox.Yes if prefer_continue else QMessageBox.No
                    )
                    cont = warn.exec() == QMessageBox.Yes
                    set_redaction_bake_continue_on_sidecar_skip(cont)
                    if not cont:
                        self.status.emit(
                            f"Redaction PDF geschrieben, Sidecar-Abbruch → {dest.name}"
                        )
                        clear_render_cache(self.pdf_path)
                        self.refresh()
                        self.annotations_changed.emit()
                        return
                    # Fortsetzung: Sidecar übersprungen — Status — 1.3.6
                    sidecar_skipped = True
                else:
                    sidecar_skipped = False
            else:
                sidecar_skipped = False
            clear_render_cache(self.pdf_path)
            self.refresh()
            self.annotations_changed.emit()
            if sidecar_skipped:
                self.status.emit(
                    f"Sidecar übersprungen · {len(reds)} Redaction(s) → {dest.name}"
                )
            elif save_sidecar and sidecar_ok:
                self.status.emit(
                    f"{len(reds)} Redaction(s) → {dest.name} + Sidecar"
                )
            elif save_sidecar:
                self.status.emit(
                    f"{len(reds)} Redaction(s) → {dest.name} (Sidecar-Warnung)"
                )
            else:
                self.status.emit(f"{len(reds)} Redaction(s) → {dest.name}")
        except Exception as e:
            QMessageBox.warning(self, "Redactions", str(e))

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
            self.schedule_sidecar_save()
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
            self.schedule_sidecar_save()
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
            self.schedule_sidecar_save()
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
            self.schedule_sidecar_save()
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

    def _remember_quick_stamp_zoom_opacity(self) -> None:
        """Zoom/Opacity wie Signatur merken, falls vorhanden — 1.9.4."""
        from instantlensdoc.core.app_settings import (
            set_last_quick_stamp_opacity,
            set_last_quick_stamp_zoom,
        )

        try:
            if hasattr(self, "scale") and self.scale is not None:
                set_last_quick_stamp_zoom(float(self.scale))
        except Exception:
            pass
        try:
            op = getattr(self, "_default_opacity", None)
            if op is not None:
                set_last_quick_stamp_opacity(float(op))
        except Exception:
            pass

    def _restore_quick_stamp_zoom_opacity(self) -> None:
        """Gemerkte Quick-Stempel Zoom/Opacity wiederherstellen falls vorhanden — 1.9.4."""
        from instantlensdoc.core.app_settings import (
            get_last_quick_stamp_opacity,
            get_last_quick_stamp_zoom,
        )

        try:
            z = get_last_quick_stamp_zoom()
            if z is not None and hasattr(self, "set_scale"):
                self.set_scale(float(z), immediate=True)
        except Exception:
            pass
        try:
            op = get_last_quick_stamp_opacity()
            if op is not None and hasattr(self, "restore_default_opacity"):
                self.restore_default_opacity(float(op))
        except Exception:
            pass

    def arm_quick_stamp(self, payload: dict | None = None) -> None:
        """Toolbar Quick-Stempel: Standard/zuletzt/Bibliothek; Esc bricht ab — 1.9.5."""
        from instantlensdoc.core.stamp_library import resolve_quick_stamp

        if not self.pdf_path:
            self.status.emit("Kein PDF für Quick-Stempel")
            return
        if not isinstance(payload, dict):
            payload = resolve_quick_stamp()
        if not payload:
            QMessageBox.information(
                self,
                "Quick-Stempel",
                "Kein Stempel verfügbar. Rechtsklick → Bibliothek wählen "
                "oder Standard-Stempel ★ setzen (Ctrl+Shift+S).",
            )
            return
        # Zoom/Opacity wie Signatur wiederherstellen falls vorhanden — 1.9.4
        self._restore_quick_stamp_zoom_opacity()
        self._quick_stamp_payload = payload
        self._quick_stamp_armed = True
        self._set_tool(AnnotationType.STAMP)
        # _set_tool würde Quick nicht löschen (tool==STAMP); Payload bleibt
        self._quick_stamp_payload = payload
        self._quick_stamp_armed = True
        label = payload.get("image") or (payload.get("text") or "Stempel").split("\n")[0]
        self.status.emit(
            f"Quick-Stempel bereit: {label} — Klick auf Seite · Esc = Abbruch"
        )
        try:
            self.canvas.setFocus(Qt.OtherFocusReason)
        except Exception:
            pass

    def arm_standard_stamp(self) -> None:
        """Ctrl+Shift+S: Standard-Stempel ★ platzieren (nicht zuletzt verwendet) — 1.9.5."""
        from instantlensdoc.core.stamp_library import resolve_standard_stamp

        payload = resolve_standard_stamp()
        self.arm_quick_stamp(payload)

    def _on_canvas_escape(self) -> None:
        """Esc: Quick-Stempel / Callout / Winkel-Pending abbrechen — 2.1.0."""
        if self.cancel_pending_angle():
            return
        if self._pending_callout_anchor is not None:
            self._pending_callout_anchor = None
            self.status.emit("Platzieren abgebrochen")
            return
        self.cancel_quick_stamp()

    def cancel_pending_angle(self) -> bool:
        """Esc: Winkel-Zweitklick abbrechen — 2.1.0."""
        if self._pending_angle is None:
            return False
        self._pending_angle = None
        if self.tool == AnnotationType.MEASURE_ANGLE:
            self.canvas.set_drag_tool(AnnotationType.MEASURE_ANGLE, select_mode=False)
        self.status.emit("Winkel abgebrochen")
        return True

    def cancel_quick_stamp(self) -> bool:
        """Esc: Quick-Stempel abbrechen; Status + Zoom/Opacity; Fokus Toolbar — 1.9.5."""
        if not self._quick_stamp_armed and not self._quick_stamp_payload:
            return False
        # Wie Signatur: Zoom/Opacity auch bei Abbruch merken falls vorhanden — 1.9.4
        self._remember_quick_stamp_zoom_opacity()
        self._quick_stamp_armed = False
        self._quick_stamp_payload = None
        self.status.emit("Platzieren abgebrochen")
        # Fokus zurück auf Toolbar-Button — 1.9.5
        try:
            if hasattr(self, "btn_quick_stamp") and self.btn_quick_stamp is not None:
                self.btn_quick_stamp.setFocus(Qt.OtherFocusReason)
        except Exception:
            pass
        return True

    def _quick_stamp_context_menu(self, pos) -> None:
        """Rechtsklick Quick-Stempel: Bibliothek / Text-Presets wählen — 1.9.3."""
        from instantlensdoc.core.stamp_library import list_stamp_images

        menu = QMenu(self)
        act_last = menu.addAction("Zuletzt / Standard (wie Linksklick)")
        act_last.triggered.connect(lambda: self.arm_quick_stamp())
        images = list_stamp_images()
        if images:
            img_menu = menu.addMenu("Bildbibliothek")
            for info in images:
                label = f"★ {info.name}" if info.is_default else info.name
                act = img_menu.addAction(label)

                def _arm_img(checked=False, entry=info):
                    self.arm_quick_stamp(
                        {
                            "kind": "image",
                            "text": "",
                            "color": "#CCCCCC",
                            "image": entry.name,
                            "path": entry.path,
                        }
                    )

                act.triggered.connect(_arm_img)
        else:
            empty = menu.addAction("(Bildbibliothek leer)")
            empty.setEnabled(False)
        text_menu = menu.addMenu("Text-Presets")
        for display, text, color in stamp_library_items(include_date=True):
            act = text_menu.addAction(display.replace("\n", " · "))

            def _arm_txt(checked=False, t=text, c=color):
                self.arm_quick_stamp(
                    {"kind": "text", "text": t, "color": c, "image": "", "path": None}
                )

            act.triggered.connect(_arm_txt)
        if self._quick_stamp_armed:
            menu.addSeparator()
            act_cancel = menu.addAction("Platzieren abbrechen (Esc)")
            act_cancel.triggered.connect(self.cancel_quick_stamp)
        menu.exec(self.btn_quick_stamp.mapToGlobal(pos))

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
            self.schedule_sidecar_save()
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
        return self.rotate_at(self.page_index, degrees)

    def rotate_at(self, page_index: int, degrees: int = 90) -> bool:
        """Seite an Index drehen (−90/90/180/270), speichern, Undo-fähig; Ann.-Remap 1.8.1."""
        if not self.pdf_path:
            return False
        try:
            idx = int(page_index)
            if idx < 0 or idx >= int(self.page_count or 0):
                self.status.emit("Drehen: ungültige Seite")
                return False
            deg = int(degrees)
            # Anzeigegröße vor Drehung für Ann.-Koordinaten-Remap — 1.8.1
            page_w = page_h = 0.0
            try:
                from ild_pdf import PdfDocument

                with PdfDocument(self.pdf_path, password=self.password) as doc:
                    page_w, page_h = doc.page_size(idx)
            except Exception:
                page_w = page_h = 0.0
            ann_remapped = False
            if self.store is not None and page_w > 0 and page_h > 0:
                undo_before = len(getattr(self.store, "_undo", []) or [])
                n_ann = self.store.remap_coords_for_rotation(
                    idx, deg, page_w=page_w, page_h=page_h, label="Ann. nach Drehung"
                )
                undo_after = len(getattr(self.store, "_undo", []) or [])
                ann_remapped = bool(n_ann) and undo_after > undo_before
                if n_ann:
                    try:
                        self.schedule_sidecar_save(force=True)
                    except Exception:
                        pass
            self._page_ops_undo.append(
                {
                    "kind": "rotate",
                    "index": idx,
                    "degrees": deg,
                    "ann_remapped": ann_remapped,
                    "page_w": page_w,
                    "page_h": page_h,
                }
            )
            if len(self._page_ops_undo) > 20:
                self._page_ops_undo.pop(0)
            rotate_page(self.pdf_path, idx, deg)
            from ild_pdf.render import clear_render_cache

            clear_render_cache(self.pdf_path)
            if idx != self.page_index:
                self.page_index = idx
            self.refresh()
            self.document_changed.emit()
            if ann_remapped:
                self.annotations_changed.emit()
            shown = deg % 360
            self.status.emit(
                f"Seite {idx + 1} gedreht ({shown}°) — Ctrl+Z rückgängig"
            )
            return True
        except Exception as e:
            if self._page_ops_undo and self._page_ops_undo[-1].get("kind") == "rotate":
                if int(self._page_ops_undo[-1].get("index", -1)) == int(page_index):
                    self._page_ops_undo.pop()
            QMessageBox.warning(self, "Drehen", str(e))
            return False

    def rotate_many(self, page_indices: list[int] | Sequence[int], degrees: int = 90) -> int:
        """Mehrere Seiten drehen (±90/180); Undo; Status „N Seiten gedreht“ — 1.8.3."""
        if not self.pdf_path:
            return 0
        pages = sorted({int(i) for i in page_indices})
        if not pages:
            return 0
        deg = int(degrees)
        n = 0
        for idx in pages:
            if self.rotate_at(idx, deg):
                n += 1
        if n:
            label = "1 Seite" if n == 1 else f"{n} Seiten"
            self.status.emit(
                f"{label} gedreht ({deg:+d}°) — Ctrl+Z rückgängig"
            )
        return n

    def flip_current(self, *, horizontal: bool = False, vertical: bool = False):
        """Aktuelle Seite spiegeln (horizontal und/oder vertikal) und speichern."""
        return self.flip_at(self.page_index, horizontal=horizontal, vertical=vertical)

    def flip_at(
        self,
        page_index: int,
        *,
        horizontal: bool = False,
        vertical: bool = False,
    ) -> bool:
        """Seite spiegeln (H/V), speichern, Undo-fähig; Ann.-Remap — 1.8.2."""
        if not self.pdf_path:
            return False
        if not horizontal and not vertical:
            return False
        try:
            idx = int(page_index)
            if idx < 0 or idx >= int(self.page_count or 0):
                self.status.emit("Spiegeln: ungültige Seite")
                return False
            page_w = page_h = 0.0
            try:
                from ild_pdf import PdfDocument

                with PdfDocument(self.pdf_path, password=self.password) as doc:
                    page_w, page_h = doc.page_size(idx)
            except Exception:
                page_w = page_h = 0.0
            ann_remapped = False
            if self.store is not None and page_w > 0 and page_h > 0:
                undo_before = len(getattr(self.store, "_undo", []) or [])
                n_ann = self.store.remap_coords_for_flip(
                    idx,
                    horizontal=bool(horizontal),
                    vertical=bool(vertical),
                    page_w=page_w,
                    page_h=page_h,
                    label="Ann. nach Spiegeln",
                )
                undo_after = len(getattr(self.store, "_undo", []) or [])
                ann_remapped = bool(n_ann) and undo_after > undo_before
                if n_ann:
                    try:
                        self.schedule_sidecar_save(force=True)
                    except Exception:
                        pass
            self._page_ops_undo.append(
                {
                    "kind": "flip",
                    "index": idx,
                    "horizontal": bool(horizontal),
                    "vertical": bool(vertical),
                    "ann_remapped": ann_remapped,
                    "page_w": page_w,
                    "page_h": page_h,
                }
            )
            if len(self._page_ops_undo) > 20:
                self._page_ops_undo.pop(0)
            flip_page(
                self.pdf_path,
                idx,
                horizontal=bool(horizontal),
                vertical=bool(vertical),
            )
            from ild_pdf.render import clear_render_cache

            clear_render_cache(self.pdf_path)
            if idx != self.page_index:
                self.page_index = idx
            self.refresh()
            self.document_changed.emit()
            if ann_remapped:
                self.annotations_changed.emit()
            parts = []
            if horizontal:
                parts.append("horizontal")
            if vertical:
                parts.append("vertikal")
            self.status.emit(
                f"Seite {idx + 1} gespiegelt ({'/'.join(parts)}) — Ctrl+Z rückgängig"
            )
            return True
        except Exception as e:
            if self._page_ops_undo and self._page_ops_undo[-1].get("kind") == "flip":
                if int(self._page_ops_undo[-1].get("index", -1)) == int(page_index):
                    self._page_ops_undo.pop()
            QMessageBox.warning(self, "Spiegeln", str(e))
            return False

    def flip_many(
        self,
        page_indices: list[int] | Sequence[int],
        *,
        horizontal: bool = False,
        vertical: bool = False,
    ) -> int:
        """Mehrere Seiten spiegeln (H/V); Undo; Status „N Seiten gespiegelt“ — 1.8.3."""
        if not self.pdf_path:
            return 0
        if not horizontal and not vertical:
            return 0
        pages = sorted({int(i) for i in page_indices})
        if not pages:
            return 0
        n = 0
        for idx in pages:
            if self.flip_at(idx, horizontal=horizontal, vertical=vertical):
                n += 1
        if n:
            parts = []
            if horizontal:
                parts.append("H")
            if vertical:
                parts.append("V")
            label = "1 Seite" if n == 1 else f"{n} Seiten"
            self.status.emit(
                f"{label} gespiegelt ({'/'.join(parts)}) — Ctrl+Z rückgängig"
            )
        return n

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
        """Seiten→Bilder; Footer-Filter + Badge „Filter: übersprungen“ — 1.5.5."""
        if not self.pdf_path:
            QMessageBox.information(self, "Export", "Kein PDF geladen.")
            return
        from PySide6.QtWidgets import (
            QApplication,
            QDialog,
            QDialogButtonBox,
            QFileDialog,
            QHBoxLayout,
            QInputDialog,
            QLabel,
            QPlainTextEdit,
            QProgressDialog,
            QPushButton,
            QVBoxLayout,
        )
        from ild_pdf import extract_pages_as_images
        from instantlensdoc.core.app_settings import (
            EXPORT_RASTER_DPI_CHOICES,
            apply_export_profile,
            dialog_start_dir,
            get_active_export_profile_name,
            get_export_jpeg_quality,
            get_export_profile,
            get_export_profiles,
            get_export_raster_dpi,
            get_last_page_image_export_dir,
            get_page_image_filename_template,
            remember_recent_dir,
            set_export_jpeg_quality,
            set_export_raster_dpi,
            set_last_export_dir,
            set_last_page_image_export_dir,
            set_page_image_filename_template,
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
            ["Aktuelle Seite", "Seitenbereich…", "Alle Seiten"],
            0,
            False,
        )
        if not ok:
            return
        pages: list[int] | None
        if scope.startswith("Aktuelle"):
            pages = [self.page_index]
        elif scope.startswith("Seitenbereich"):
            from ild_pdf import PdfDocument, flatten_page_indices, parse_page_ranges

            try:
                with PdfDocument(self.pdf_path, password=self.password) as doc:
                    n_pages = len(doc)
            except Exception:
                n_pages = 1
            default_spec = (
                f"{self.page_index + 1}"
                if n_pages <= 1
                else f"1-{min(n_pages, max(1, self.page_index + 1))}"
            )
            spec, ok = QInputDialog.getText(
                self,
                "Seitenbereich",
                f"Seitenbereich (1…{n_pages}), z. B. 1-3,5,8-10:",
                text=default_spec,
            )
            if not ok:
                return
            try:
                ranges = parse_page_ranges(spec, n_pages, one_based=True)
                pages = flatten_page_indices(ranges)
            except ValueError as e:
                QMessageBox.warning(self, "Seitenbereich", str(e))
                return
            if not pages:
                QMessageBox.information(self, "Seitenbereich", "Keine Seiten ausgewählt.")
                return
        else:
            pages = None
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
        # JPEG-Qualität aus Settings (bei JPEG wählbar) — 1.5.2
        jpeg_q = get_export_jpeg_quality()
        if str(fmt).upper() in ("JPEG", "JPG"):
            jpeg_q, ok = QInputDialog.getInt(
                self,
                "Seiten als Bilder",
                "JPEG-Qualität (Settings, 10–100):",
                jpeg_q,
                10,
                100,
                1,
            )
            if not ok:
                return
            jpeg_q = set_export_jpeg_quality(jpeg_q)
        # Dateiname-Template {stem}_p{page} — 1.5.1
        tpl_default = get_page_image_filename_template()
        tpl, ok = QInputDialog.getText(
            self,
            "Seiten als Bilder",
            "Dateiname-Template ({stem}, {page}):",
            text=tpl_default,
        )
        if not ok:
            return
        tpl = set_page_image_filename_template(tpl or tpl_default)
        last_img_dir = get_last_page_image_export_dir()
        start_dir = dialog_start_dir(
            last_img_dir,
            str(profile["target"]) if profile and profile.get("target") else None,
            self.pdf_path.parent,
        )
        out_dir = QFileDialog.getExistingDirectory(self, "Zielordner für Bilder", start_dir)
        if not out_dir:
            return
        try:
            from ild_pdf import PdfDocument as _PdProg

            if pages is None:
                try:
                    with _PdProg(self.pdf_path, password=self.password) as doc:
                        total_export = len(doc)
                except Exception:
                    total_export = 1
            else:
                total_export = len(pages)
            progress: QProgressDialog | None = None
            cancelled = {"v": False}
            # Fortschritt bei Bereich/Mehrseiten; Abbruch behält geschriebene Dateien — 1.5.2
            if total_export > 1:
                progress = QProgressDialog(
                    "Seiten als Bilder…", "Abbrechen", 0, total_export, self
                )
                progress.setWindowTitle("Export")
                progress.setMinimumDuration(0)
                progress.setValue(0)
                progress.setAutoClose(False)
                progress.setAutoReset(False)

                def _on_prog(cur: int, total: int) -> bool:
                    if progress is None:
                        return True
                    progress.setMaximum(total)
                    progress.setValue(cur - 1)
                    progress.setLabelText(f"Seite {cur} von {total}…")
                    QApplication.processEvents()
                    if progress.wasCanceled():
                        cancelled["v"] = True
                        return False
                    return True
            else:
                _on_prog = None  # type: ignore[assignment]

            # Geplante Seitenindizes für Skip-Log — 1.5.4
            if pages is None:
                planned = list(range(int(total_export)))
            else:
                planned = list(pages)
            written = extract_pages_as_images(
                self.pdf_path,
                out_dir,
                pages=pages,
                dpi=dpi,
                format=fmt,
                jpeg_quality=jpeg_q,
                password=self.password,
                grayscale=self._grayscale,
                filename_template=tpl,
                on_progress=_on_prog,
            )
            if progress is not None:
                # Geschriebene Dateien bleiben bei Abbruch erhalten — 1.5.2
                if not cancelled["v"]:
                    progress.setValue(total_export)
                progress.close()
            set_last_export_dir(out_dir)
            set_last_page_image_export_dir(out_dir)
            remember_recent_dir(out_dir)
            n_ok = len(written)
            skipped_pages = planned[n_ok:]  # Rest bei Abbruch = übersprungen
            n_skip = len(skipped_pages)
            footer = f"geschrieben {n_ok}, übersprungen {n_skip}"
            q_note = f", Q={jpeg_q}" if str(fmt).upper() in ("JPEG", "JPG") else ""
            log_lines: list[str] = []
            for i, wpath in enumerate(written):
                pg = planned[i] + 1 if i < len(planned) else i + 1
                log_lines.append(f"[ok] Seite {pg} → {wpath}")
            for pi in skipped_pages:
                log_lines.append(f"[skip] Seite {pi + 1} übersprungen")
            header = (
                f"Abgebrochen — behalten {n_ok}/{total_export}"
                if cancelled["v"]
                else f"Export {n_ok}/{total_export} @ {dpi} DPI{q_note}"
            )
            full_log = header + "\n" + "\n".join(log_lines) if log_lines else header
            if cancelled["v"]:
                status_msg = (
                    f"Export abgebrochen — {footer} → {Path(out_dir).name}"
                )
            else:
                status_msg = (
                    f"{n_ok}/{total_export} Bild(er) @ {dpi} DPI{q_note} → "
                    f"{Path(out_dir).name} · {footer}"
                )
            self.status.emit(status_msg)
            # Ergebnisdialog: Log + Footer-Toggle + Badge Filter übersprungen — 1.5.5
            dlg = QDialog(self)
            dlg.setWindowTitle("Export — Seiten als Bilder")
            dlg.resize(560, 420)
            lay = QVBoxLayout(dlg)
            summary = QLabel(
                f"{out_dir}\n{footer}"
                + ("\n(Abbruch — geschriebene Dateien behalten)" if cancelled["v"] else "")
            )
            summary.setWordWrap(True)
            lay.addWidget(summary)
            log_edit = QPlainTextEdit()
            log_edit.setReadOnly(True)
            log_edit.setPlainText(full_log)
            lay.addWidget(log_edit, 1)
            state = {
                "filter_skipped": False,
                "full_log": full_log,
                "skipped_pages": list(skipped_pages),
            }
            footer_row = QHBoxLayout()
            footer_lbl = QLabel(footer)
            footer_lbl.setCursor(Qt.PointingHandCursor)
            footer_lbl.setStyleSheet("color: #555; text-decoration: underline;")
            footer_lbl.setToolTip(
                "Klick: Log auf übersprungene Einträge filtern (Toggle), "
                "analog Split-Log — 1.5.5"
            )
            filter_badge = QLabel("Filter: übersprungen")
            filter_badge.setObjectName("pagesExportFilterBadge")
            filter_badge.setVisible(False)
            filter_badge.setStyleSheet(
                "color: #0d47a1; background: #E3F2FD; font-weight: bold; "
                "padding: 2px 8px; border-radius: 3px;"
            )
            filter_badge.setToolTip("Filter aktiv: nur übersprungene Einträge — 1.5.5")

            def _update_footer_style() -> None:
                if state["filter_skipped"]:
                    footer_lbl.setStyleSheet(
                        "color: #0d47a1; font-weight: bold; text-decoration: underline;"
                    )
                    footer_lbl.setToolTip(
                        "Filter aktiv: nur übersprungene. Klick hebt auf — 1.5.5"
                    )
                    filter_badge.setText("Filter: übersprungen")
                    filter_badge.setVisible(True)
                else:
                    footer_lbl.setStyleSheet(
                        "color: #555; text-decoration: underline;"
                    )
                    footer_lbl.setToolTip(
                        "Klick: Log auf übersprungene Einträge filtern (Toggle), "
                        "analog Split-Log — 1.5.5"
                    )
                    filter_badge.setVisible(False)

            def _apply_filter() -> None:
                if not state["filter_skipped"]:
                    log_edit.setPlainText(state["full_log"])
                    _update_footer_style()
                    return
                skip_lines = [
                    ln
                    for ln in state["full_log"].splitlines()
                    if ln.startswith("[skip]")
                ]
                log_edit.setPlainText(
                    f"Filter: übersprungen ({len(skip_lines)})"
                    + ("\n" + "\n".join(skip_lines) if skip_lines else "")
                )
                _update_footer_style()

            def _footer_clicked(event) -> None:
                from PySide6.QtCore import Qt as _Qt

                if (
                    event is not None
                    and getattr(event, "button", lambda: _Qt.LeftButton)()
                    != _Qt.LeftButton
                ):
                    return
                if not state["filter_skipped"] and not state["skipped_pages"]:
                    return
                state["filter_skipped"] = not state["filter_skipped"]
                _apply_filter()

            footer_lbl.mousePressEvent = (  # type: ignore[method-assign]
                lambda event: _footer_clicked(event)
            )
            footer_row.addWidget(footer_lbl)
            footer_row.addWidget(filter_badge)
            footer_row.addStretch(1)
            lay.addLayout(footer_row)
            btn_row = QHBoxLayout()
            btn_folder = QPushButton("Ordner öffnen")
            btn_folder.clicked.connect(
                lambda: QDesktopServices.openUrl(
                    QUrl.fromLocalFile(str(out_dir))
                )
            )
            btn_row.addWidget(btn_folder)
            btn_row.addStretch(1)
            btns = QDialogButtonBox(QDialogButtonBox.Ok)
            btns.accepted.connect(dlg.accept)
            btn_row.addWidget(btns)
            lay.addLayout(btn_row)
            dlg.exec()
        except Exception as e:
            QMessageBox.warning(self, "Export", str(e))

    def place_signature_field(self):
        """Signaturfeld-Platzhalter per Klick (Werkzeug Signaturfeld)."""
        self._set_tool(AnnotationType.SIGNATURE_FIELD)
        self.status.emit("Signaturfeld: auf die Seite klicken")

    def insert_signature_image(self):
        """Bildstempel-Signatur; Zoom Settings·Reset; Esc-Status — 1.5.5."""
        if not self.store or not self.pdf_path:
            QMessageBox.information(self, "Signatur", "Kein PDF geladen.")
            return
        from PySide6.QtWidgets import (
            QCheckBox,
            QDialog,
            QDialogButtonBox,
            QFileDialog,
            QFormLayout,
            QHBoxLayout,
            QLabel,
            QPushButton,
            QSlider,
            QVBoxLayout,
        )
        from PySide6.QtCore import QEvent, Qt as _Qt
        from PySide6.QtGui import QKeyEvent, QPixmap, QWheelEvent
        from ild_pdf import insert_signature_image
        from instantlensdoc.core.app_settings import (
            dialog_start_dir,
            get_last_signature_image,
            get_last_signature_opacity,
            get_last_signature_preview_zoom,
            get_last_signature_size,
            get_signature_aspect_lock,
            remember_recent_dir,
            set_last_signature_image,
            set_last_signature_opacity,
            set_last_signature_preview_zoom,
            set_last_signature_size,
            set_signature_aspect_lock,
        )
        from instantlensdoc.ui.file_dialogs import confirm_overwrite_export

        last_sig = get_last_signature_image()
        start = dialog_start_dir(
            last_sig.parent if last_sig else None,
            self.pdf_path.parent if self.pdf_path else None,
        )
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Signatur-Bild",
            start,
            "Bilder (*.png *.jpg *.jpeg *.bmp)",
        )
        if not path and last_sig is not None:
            # Abbruch im Dialog: bei bekanntem letztem Bild nachfragen — 1.5.1
            from PySide6.QtWidgets import QMessageBox as _MB

            use = _MB.question(
                self,
                "Signatur",
                f"Zuletzt verwendet:\n{last_sig.name}\n\nDieses Bild erneut verwenden?",
                _MB.Yes | _MB.No,
                _MB.Yes,
            )
            if use == _MB.Yes:
                path = str(last_sig)
        if not path:
            return
        remember_recent_dir(path)
        set_last_signature_image(path)
        # Bild-Seitenverhältnis für Aspect-Lock — 1.5.2
        img_aspect = 180.0 / 64.0
        try:
            from PIL import Image as _PILImg

            with _PILImg.open(path) as im:
                iw, ih = im.size
            if iw > 0 and ih > 0:
                img_aspect = float(iw) / float(ih)
        except Exception:
            pass
        # Option: Größe/Opacity/Aspect-Lock + Vorschau Zoom Settings·Reset — 1.5.5
        zoom_state = {"factor": float(get_last_signature_preview_zoom())}
        preview_holder: dict[str, object] = {}

        class _SigPreviewDialog(QDialog):
            """Esc → Status „Platzieren abgebrochen“; Zoom Settings — 1.5.5."""

            def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
                if event.key() == _Qt.Key_Escape:
                    set_last_signature_preview_zoom(zoom_state["factor"])
                    self.reject()
                    event.accept()
                    return
                super().keyPressEvent(event)

            def eventFilter(self, obj, event):  # noqa: N802
                lbl = preview_holder.get("lbl")
                if obj is lbl and event.type() == QEvent.Type.Wheel:
                    assert isinstance(event, QWheelEvent)
                    delta = event.angleDelta().y()
                    if delta == 0:
                        delta = event.pixelDelta().y()
                    if delta > 0:
                        zoom_state["factor"] = min(3.0, zoom_state["factor"] * 1.15)
                    elif delta < 0:
                        zoom_state["factor"] = max(0.5, zoom_state["factor"] / 1.15)
                    set_last_signature_preview_zoom(zoom_state["factor"])
                    updater = preview_holder.get("update")
                    if callable(updater):
                        updater()
                    event.accept()
                    return True
                return super().eventFilter(obj, event)

        opt = _SigPreviewDialog(self)
        opt.setWindowTitle("Signatur platzieren — Vorschau")
        ol = QVBoxLayout(opt)
        ol.addWidget(QLabel(f"Bild: {Path(path).name}"))
        hint_lbl = QLabel(
            "Vorschau: Mausrad zoomt (Zoom in Settings persistiert) · "
            "Reset-Zoom · Esc → Platzieren abgebrochen · Bildstempel als Sidecar."
        )
        hint_lbl.setWordWrap(True)
        hint_lbl.setStyleSheet("color:#555;")
        ol.addWidget(hint_lbl)
        preview_lbl = QLabel()
        preview_lbl.setAlignment(_Qt.AlignCenter)
        preview_lbl.setMinimumHeight(120)
        preview_lbl.setStyleSheet(
            "QLabel { background:#F4F6F8; border:1px solid #CCD5DD; }"
        )
        preview_lbl.setToolTip("Mausrad: Vorschau zoomen (Settings) — 1.5.5")
        ol.addWidget(preview_lbl)
        zoom_btn_row = QHBoxLayout()
        btn_reset_zoom = QPushButton("Reset-Zoom")
        btn_reset_zoom.setObjectName("sigPreviewResetZoom")
        btn_reset_zoom.setToolTip(
            "Vorschau-Zoom auf 100 % zurücksetzen und in Settings speichern — 1.5.5"
        )

        def _reset_preview_zoom() -> None:
            zoom_state["factor"] = 1.0
            set_last_signature_preview_zoom(1.0)
            updater = preview_holder.get("update")
            if callable(updater):
                updater()

        btn_reset_zoom.clicked.connect(_reset_preview_zoom)
        zoom_btn_row.addWidget(btn_reset_zoom)
        zoom_btn_row.addStretch(1)
        ol.addLayout(zoom_btn_row)
        preview_holder["lbl"] = preview_lbl
        form = QFormLayout()
        last_w, last_h = get_last_signature_size()
        last_op = get_last_signature_opacity()
        # Größe als Prozent der Default-Breite 180 — Slider 40–300 %
        size_slider = QSlider(_Qt.Horizontal)
        size_slider.setRange(40, 300)
        size_pct = int(round((last_w / 180.0) * 100))
        size_slider.setValue(max(40, min(300, size_pct)))
        size_lbl = QLabel(f"{size_slider.value()} %")
        size_row = QVBoxLayout()
        size_row.addWidget(size_slider)
        size_row.addWidget(size_lbl)
        form.addRow("Größe", size_row)
        op_slider = QSlider(_Qt.Horizontal)
        op_slider.setRange(5, 100)
        op_slider.setValue(int(round(last_op * 100)))
        op_lbl = QLabel(f"{op_slider.value()} %")
        op_row = QVBoxLayout()
        op_row.addWidget(op_slider)
        op_row.addWidget(op_lbl)
        form.addRow("Deckkraft", op_row)
        ol.addLayout(form)
        chk_aspect = QCheckBox("Seitenverhältnis sperren (Aspect-Ratio Lock)")
        chk_aspect.setChecked(bool(get_signature_aspect_lock()))
        chk_aspect.setToolTip(
            "An: Höhe folgt der Bild-Proportion zur Breite. Aus: freies 180×64-Skalieren — 1.5.2"
        )
        ol.addWidget(chk_aspect)
        dims_lbl = QLabel("")
        dims_lbl.setStyleSheet("color:#555;")
        ol.addWidget(dims_lbl)

        def _calc_size() -> tuple[float, float]:
            scale = size_slider.value() / 100.0
            width = max(40.0, 180.0 * scale)
            if chk_aspect.isChecked():
                height = max(12.0, width / max(0.05, img_aspect))
            else:
                height = max(20.0, 64.0 * scale)
            return width, height

        def _update_preview(*_args) -> None:
            from PySide6.QtGui import QPainter as _QP

            size_lbl.setText(f"{size_slider.value()} %")
            op_lbl.setText(f"{op_slider.value()} %")
            w, h = _calc_size()
            z = zoom_state["factor"]
            dims_lbl.setText(
                f"Platzierung: {w:.0f} × {h:.0f} pt · Vorschau-Zoom {z:.0%}"
            )
            pm = QPixmap(path)
            if pm.isNull():
                preview_lbl.setText("(Vorschau nicht verfügbar)")
                return
            op = max(0.05, min(1.0, op_slider.value() / 100.0))
            # Basis 280×100, Mausrad-Zoom 50–300 % — 1.5.3
            base_w = max(40, int(round(280 * z)))
            base_h = max(24, int(round(100 * z)))
            scaled = pm.scaled(
                base_w, base_h, _Qt.KeepAspectRatio, _Qt.SmoothTransformation
            )
            if op < 0.999:
                canvas = QPixmap(scaled.size())
                canvas.fill(_Qt.transparent)
                painter = _QP(canvas)
                painter.setOpacity(op)
                painter.drawPixmap(0, 0, scaled)
                painter.end()
                scaled = canvas
            preview_lbl.setPixmap(scaled)

        preview_holder["update"] = _update_preview
        preview_lbl.installEventFilter(opt)
        size_slider.valueChanged.connect(_update_preview)
        op_slider.valueChanged.connect(_update_preview)
        chk_aspect.toggled.connect(_update_preview)
        _update_preview()
        chk_flat = QCheckBox("Zusätzlich Flatten-PDF erzeugen (Signatur einbrennen)")
        chk_flat.setChecked(False)
        chk_flat.setToolTip(
            "Schreibt die aktuelle Seite inkl. Signatur in ein neues PDF; Sidecar bleibt."
        )
        ol.addWidget(chk_flat)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_btn = btns.button(QDialogButtonBox.Ok)
        if ok_btn is not None:
            ok_btn.setText("Platzieren")
        btns.accepted.connect(opt.accept)
        btns.rejected.connect(opt.reject)
        ol.addWidget(btns)
        if opt.exec() != QDialog.Accepted:
            # Esc/Abbrechen: Zoom merken + Status — 1.5.4
            set_last_signature_preview_zoom(zoom_state["factor"])
            self.status.emit("Platzieren abgebrochen")
            return
        set_last_signature_preview_zoom(zoom_state["factor"])
        width, height = _calc_size()
        opacity = max(0.05, min(1.0, op_slider.value() / 100.0))
        set_last_signature_size(width, height)
        set_last_signature_opacity(opacity)
        set_signature_aspect_lock(chk_aspect.isChecked())
        do_flatten = chk_flat.isChecked()
        flatten_out = None
        if do_flatten:
            default_flat = str(
                self.pdf_path.with_name(
                    f"{self.pdf_path.stem}_sig_p{self.page_index + 1}_flattened.pdf"
                )
            )
            flatten_out, _ = QFileDialog.getSaveFileName(
                self,
                "Flatten-PDF speichern",
                default_flat,
                "PDF (*.pdf)",
            )
            if not flatten_out:
                return
            if not flatten_out.lower().endswith(".pdf"):
                flatten_out = flatten_out + ".pdf"
            if not confirm_overwrite_export(flatten_out, self):
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
            result = insert_signature_image(
                self.pdf_path,
                path,
                page_index=self.page_index,
                x=x,
                y=y,
                width=width,
                height=height,
                opacity=opacity,
                flatten=do_flatten,
                flatten_path=flatten_out,
                password=self.password,
            )
            self.store.load()
            self.refresh()
            self.annotations_changed.emit()
            if do_flatten and isinstance(result, tuple):
                _img, flat = result
                remember_recent_dir(flat)
                self.status.emit(f"Signatur platziert + Flatten: {Path(flat).name}")
            else:
                lock_note = " · Aspect-Lock" if chk_aspect.isChecked() else ""
                self.status.emit(
                    f"Signatur platziert ({int(width)}×{int(height)} pt, "
                    f"{int(opacity * 100)} %{lock_note})"
                )
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
            self.schedule_sidecar_save()
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

    def sticky_from_text_selection(
        self,
        *,
        edit: bool = True,
        with_highlight: bool | None = None,
    ) -> bool:
        """Auswahl → Sticky/Notiz; optional zusätzlich Highlight (Checkbox / Setting)."""
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
        from instantlensdoc.core.app_settings import (
            get_selection_note_with_highlight,
            set_selection_note_with_highlight,
        )

        also_hl = (
            bool(with_highlight)
            if with_highlight is not None
            else bool(get_selection_note_with_highlight())
        )
        if edit:
            from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QVBoxLayout

            dlg = QDialog(self)
            dlg.setWindowTitle("Notiz aus Auswahl")
            lay = QVBoxLayout(dlg)
            lay.addWidget(QLabel("Inhalt (vorausgefüllt aus Textauswahl):"))
            edit_box = QPlainTextEdit()
            edit_box.setPlainText(text)
            edit_box.setMinimumHeight(120)
            lay.addWidget(edit_box)
            chk = QCheckBox("Zusätzlich Highlight aus Auswahl anlegen")
            chk.setChecked(also_hl)
            chk.setToolTip(
                "In einem Schritt Sticky/Notiz und Text-Highlight speichern (Einstellung bleibt erhalten)"
            )
            lay.addWidget(chk)
            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            buttons.accepted.connect(dlg.accept)
            buttons.rejected.connect(dlg.reject)
            lay.addWidget(buttons)
            if dlg.exec() != QDialog.Accepted:
                return False
            text = (edit_box.toPlainText() or "").strip()
            also_hl = bool(chk.isChecked())
            set_selection_note_with_highlight(also_hl)
            if not text:
                self.status.emit("Notiz abgebrochen — leerer Text")
                return False
        elif with_highlight is None:
            also_hl = bool(get_selection_note_with_highlight())

        hl_created = False
        if also_hl and self._text_selection_rects:
            # Highlight aus gespeicherten Auswahl-Rechtecken
            with self.store.atomic():
                for i, (rx, ry, rw, rh) in enumerate(self._text_selection_rects):
                    snippet = text if i == 0 else ""
                    self.store.add(
                        Annotation(
                            page=page,
                            type=AnnotationType.HIGHLIGHT,
                            x=float(rx),
                            y=float(ry),
                            width=max(float(rw), 4.0),
                            height=max(float(rh), 6.0),
                            color=self._highlight_color,
                            text=snippet,
                            opacity=self._default_opacity,
                        )
                    )
            hl_created = True

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
        if hl_created:
            self.status.emit(f"Highlight + Notiz aus Auswahl: {preview}")
        else:
            self.status.emit(f"Notiz aus Auswahl: {preview}")
        return True

    def _on_ink(self, points: object) -> None:
        """Freihand-Polyline committen; Glätten als eigener Undo-Eintrag — 2.2.3."""
        if not self.store:
            return
        # Werkzeug sollte INK sein; programmatische Tests dürfen Punkte ohne Tool setzen
        if self.tool is not None and self.tool != AnnotationType.INK:
            return
        raw = list(points or [])
        if len(raw) < 2:
            return
        # Punkte auf Startseite mappen (Spread)
        page0, lx0, ly0 = self._spread_resolve(float(raw[0][0]), float(raw[0][1]))
        mapped: list[list[float]] = [[lx0, ly0]]
        ox, oy = float(raw[0][0]), float(raw[0][1])
        for pt in raw[1:]:
            try:
                x, y = float(pt[0]), float(pt[1])
            except (TypeError, ValueError, IndexError):
                continue
            mapped.append([lx0 + (x - ox), ly0 + (y - oy)])
        if len(mapped) < 2:
            return
        do_smooth = False
        try:
            do_smooth = bool(
                getattr(self, "btn_ink_smooth", None)
                and self.btn_ink_smooth.isChecked()
            )
            if not do_smooth:
                do_smooth = bool(get_ink_smooth())
        except Exception:
            do_smooth = bool(get_ink_smooth())
        strength = get_ink_smooth_strength()
        passes = get_ink_smooth_passes()
        # Rohstrich zuerst (ohne Glättung) — eigener Undo-Eintrag
        ann = Annotation.from_ink_points(
            page0,
            mapped,
            color=self._pen_color,
            stroke_width=float(getattr(self, "_default_stroke_width", 2.0) or 2.0),
            smooth=False,
        )
        # Historie: spezifischer Action-Name vor generischem commit
        try:
            from ild_pdf.doc_history import append_doc_history

            append_doc_history(
                self.pdf_path,
                "annotation.ink",
                f"page={page0} points={len(ann.ink_points())} smooth={int(do_smooth)} "
                f"strength={strength} stroke={ann.stroke_width:.0f} color={ann.color}",
                page=page0,
            )
        except Exception:
            pass
        # _commit_ann loggt zusätzlich annotation.add — OK für Audit
        self._commit_ann(ann)
        # Glättung als separater Undo-Stack-Eintrag; Redo ok; Status — 2.2.3
        if do_smooth and self.store is not None:
            try:
                smoothed = self.store.smooth_ink(
                    ann.id, passes=passes, strength=strength
                )
                if smoothed is not None:
                    try:
                        from ild_pdf.doc_history import append_doc_history

                        append_doc_history(
                            self.pdf_path,
                            "annotation.ink_smooth",
                            f"page={page0} id={ann.id[:8]} strength={strength} "
                            f"passes={passes}",
                            page=page0,
                        )
                    except Exception:
                        pass
                    try:
                        self.schedule_sidecar_save(force=True)
                    except Exception:
                        pass
                    self.refresh()
                    self.annotations_changed.emit()
                    # Toast Dauer Settings + A11y — 2.2.4
                    self._show_smooth_status_toast("Glättung angewandt")
            except Exception:
                pass

    def _announce_smooth_status_toast(self, msg: str) -> None:
        """
        Accessibility-Announcement für Ink-Glättungs-Status —
        gleicher Announcement-Pfad wie OCR
        (MainWindow._announce_status_toast bzw. AccessibleName +
        AnnouncementEvent, Fallback NameChanged) — 2.2.5.
        """
        win = self.window()
        if win is not None and hasattr(win, "_announce_status_toast"):
            try:
                win._announce_status_toast(msg)
                return
            except Exception:
                pass
        target = self
        if win is not None and hasattr(win, "statusBar"):
            try:
                sb = win.statusBar()
                if sb is not None:
                    target = sb
            except Exception:
                pass
        try:
            target.setAccessibleName(msg)
            if hasattr(target, "setAccessibleDescription"):
                target.setAccessibleDescription(msg)
        except Exception:
            pass
        try:
            from PySide6.QtGui import QAccessible, QAccessibleAnnouncementEvent

            ev = QAccessibleAnnouncementEvent(target, msg)
            QAccessible.updateAccessibility(ev)
        except Exception:
            try:
                from PySide6.QtGui import QAccessible, QAccessibleEvent

                ev = QAccessibleEvent(target, QAccessible.Event.NameChanged)
                QAccessible.updateAccessibility(ev)
            except Exception:
                pass

    def _focus_ink_tool_from_toast(self) -> bool:
        """Ink-Toast-Klick: Freihand-Werkzeug aktivieren + Fokus — 2.2.5."""
        from PySide6.QtCore import Qt as _Qt

        try:
            self._set_tool(AnnotationType.INK)
        except Exception:
            return False
        focused = False
        for b in getattr(self, "_tool_buttons", []) or []:
            try:
                if b.text() == "Freihand":
                    b.setFocus(_Qt.OtherFocusReason)
                    focused = True
                    break
            except Exception:
                pass
        try:
            self.canvas.setFocus(_Qt.OtherFocusReason)
            focused = True
        except Exception:
            pass
        win = self.window()
        if win is not None and hasattr(win, "_announce_status_toast"):
            try:
                win._announce_status_toast("Werkzeug: Freihand")
            except Exception:
                pass
        return focused or self.tool == AnnotationType.INK

    def _show_smooth_status_toast(self, msg: str = "Glättung angewandt") -> None:
        """
        Ink-Glättungs-Status: Dauer aus OCR-Defaults-Toast-Settings;
        Klick fokussiert Ink-Tool; A11y wie OCR — 2.2.5.
        """
        from PySide6.QtCore import QTimer
        from PySide6.QtCore import Qt as _Qt

        try:
            from instantlensdoc.core.app_settings import get_ocr_defaults_toast_sec

            ms = max(1, int(get_ocr_defaults_toast_sec())) * 1000
        except Exception:
            ms = 2000
        self._smooth_status_toast_token = (
            int(getattr(self, "_smooth_status_toast_token", 0)) + 1
        )
        token = self._smooth_status_toast_token
        self._announce_smooth_status_toast(msg)
        self.status.emit(msg)
        win = self.window()
        if win is not None:
            try:
                win._smooth_status_toast_active = True
                win._smooth_status_toast_msg = msg
            except Exception:
                pass
        if win is not None and hasattr(win, "statusBar"):
            try:
                sb = win.statusBar()
                sb.showMessage(msg, ms)
                sb.setToolTip(
                    "Klick fokussiert Ink-/Freihand-Werkzeug — 2.2.5"
                )
                sb.setCursor(_Qt.PointingHandCursor)
            except Exception:
                pass

        def _clear() -> None:
            if token != getattr(self, "_smooth_status_toast_token", 0):
                return
            target = self
            if win is not None and hasattr(win, "statusBar"):
                try:
                    sb = win.statusBar()
                    if sb is not None:
                        target = sb
                        tip = sb.toolTip() or ""
                        if tip.startswith("Klick fokussiert Ink"):
                            sb.setToolTip("")
                            sb.unsetCursor()
                        if getattr(win, "_smooth_status_toast_active", False):
                            win._smooth_status_toast_active = False
                except Exception:
                    pass
            try:
                if hasattr(target, "accessibleName") and (
                    target.accessibleName() or ""
                ) == msg:
                    target.setAccessibleName("")
                    if hasattr(target, "setAccessibleDescription"):
                        target.setAccessibleDescription("")
            except Exception:
                pass

        QTimer.singleShot(ms, _clear)

    def delete_last_ink_stroke(self) -> bool:
        """Letzten Freihand-Strich löschen (Undo-fähig) — 2.2.1."""
        if not self.store:
            self.status.emit("Kein PDF geöffnet")
            return False
        target = self.store.remove_last_ink(page=self.page_index)
        if target is None:
            target = self.store.remove_last_ink(page=None)
        if target is None:
            self.status.emit("Kein Freihand-Strich zum Löschen")
            return False
        try:
            self.schedule_sidecar_save(force=True)
        except Exception:
            pass
        try:
            from ild_pdf.doc_history import append_doc_history

            append_doc_history(
                self.pdf_path,
                "annotation.ink_delete",
                f"page={target.page} id={target.id[:8]}",
            )
        except Exception:
            pass
        self.refresh()
        self.annotations_changed.emit()
        self.document_changed.emit()
        self.status.emit("Letzter Freihand-Strich gelöscht")
        return True

    def apply_custom_page_labels(
        self,
        labels: Sequence[str],
        *,
        write_pdf: bool = False,
    ) -> None:
        """Custom-Seitenlabels in Sidecar speichern; optional PDF PageLabels — 2.2.0."""
        if not self.store or not self.pdf_path:
            raise RuntimeError("Kein PDF geöffnet")
        cleaned = self.store.set_custom_page_labels(list(labels))
        self.store.save(force=True)
        if write_pdf:
            from ild_pdf.page_labels import write_pdf_page_labels

            n = int(self.page_count or 0)
            full = list(cleaned) + [""] * max(0, n - len(cleaned))
            write_pdf_page_labels(self.pdf_path, full[:n], password=self.password)
        self._reload_page_labels()
        self.refresh()
        self.document_changed.emit()
        try:
            from ild_pdf.doc_history import append_doc_history

            n_set = sum(1 for x in cleaned if x)
            append_doc_history(
                self.pdf_path,
                "page_labels.set",
                f"labels={n_set} write_pdf={bool(write_pdf)}",
            )
        except Exception:
            pass
        self.status.emit(
            f"Seitenbeschriftungen gespeichert ({sum(1 for x in cleaned if x)} Labels)"
            + (" · PDF PageLabels geschrieben" if write_pdf else "")
        )

    def edit_page_labels(self) -> None:
        """Dialog Seitenbeschriftungen — 2.2.0."""
        if not self.pdf_path or not self.store:
            self.status.emit("Kein PDF geöffnet")
            return
        from instantlensdoc.ui.page_labels_dialog import PageLabelsDialog

        dlg = PageLabelsDialog(self, parent=self)
        dlg.exec()

    def show_doc_history(self) -> None:
        """Dokument-Historie-Panel (50/Filter/Export/Doppelklick/Clear) — 2.2.3."""
        if not self.pdf_path:
            self.status.emit("Kein PDF geöffnet")
            return
        from instantlensdoc.ui.doc_history_dialog import DocHistoryDialog

        def _goto(page: int) -> None:
            self.goto_page(int(page))
            self.status.emit(f"Historie → Seite {int(page) + 1}")

        dlg = DocHistoryDialog(
            self.pdf_path,
            parent=self,
            on_goto_page=_goto,
            page_count=int(getattr(self, "page_count", 0) or 0) or None,
        )
        dlg.exec()

    def _on_drag(self, x0: float, y0: float, x1: float, y1: float):
        if not self.store or self.tool is None or self.tool not in DRAG_TYPES:
            return
        if self.tool == AnnotationType.INK:
            return  # über ink_finished
        page0, lx0, ly0 = self._spread_resolve(x0, y0)
        _page1, lx1, ly1 = self._spread_resolve(x1, y1)
        page = page0
        # Endpunkt relativ zum Start halten (kein Seitenwechsel mitten im Drag)
        lx1 = lx0 + (x1 - x0)
        ly1 = ly0 + (y1 - y0)
        x0, y0, x1, y1 = lx0, ly0, lx1, ly1
        # Optional Snap-to-Annotation für Messwerkzeuge — 2.1.1
        if self.tool in (
            AnnotationType.MEASURE,
            AnnotationType.MEASURE_AREA,
            AnnotationType.MEASURE_ANGLE,
        ):
            x0, y0 = self._snap_measure_point(x0, y0, page=page)
            x1, y1 = self._snap_measure_point(x1, y1, page=page)
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
                fill_color=str(getattr(self, "_default_fill_color", "") or "").strip(),
            )
        elif self.tool == AnnotationType.MEASURE_AREA:
            ann = Annotation(
                page=page,
                type=AnnotationType.MEASURE_AREA,
                x=min(x0, x1),
                y=min(y0, y1),
                width=max(abs(x1 - x0), 8),
                height=max(abs(y1 - y0), 8),
                color=self._pen_color,
            )
            ann.text = ann.measure_label(self.scale, unit=self._measure_unit())
        elif self.tool == AnnotationType.MEASURE_ANGLE:
            # Erster Strahl: Start → Vertex (callout); zweiter Klick setzt p3
            self._pending_angle = (x0, y0, x1, y1, page)
            # Drag-Tool aus, damit nächster Klick als Place ankommt — 2.1.0
            self.canvas.set_drag_tool(None, select_mode=False)
            self.status.emit("Winkel: zweiten Endpunkt klicken (Esc bricht ab)")
            return
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
                ann.text = ann.measure_label(self.scale, unit=self._measure_unit())
        else:
            return
        self._commit_ann(ann)

    def _on_place(self, x: float, y: float):
        if not self.store or self.tool is None:
            return
        # Winkel: zweiter Klick nach erstem Drag — 2.1.0/2.1.1
        if self.tool == AnnotationType.MEASURE_ANGLE and self._pending_angle is not None:
            page, x, y = self._spread_resolve(x, y)
            x, y = self._snap_measure_point(x, y, page=page)
            ax, ay, vx, vy, apage = self._pending_angle
            self._pending_angle = None
            ann = Annotation(
                page=apage,
                type=AnnotationType.MEASURE_ANGLE,
                x=ax,
                y=ay,
                width=abs(vx - ax),
                height=abs(vy - ay),
                callout_x=vx,
                callout_y=vy,
                p3_x=x,
                p3_y=y,
                color=self._pen_color,
            )
            ann.text = ann.measure_label(self.scale, unit=self._measure_unit())
            self._commit_ann(ann)
            # Drag wieder aktiv für nächsten Winkel
            self.canvas.set_drag_tool(AnnotationType.MEASURE_ANGLE, select_mode=False)
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
            # Quick-Stempel: zuletzt verwendet / Standard ★ ohne Dialog — 1.9.2
            if self._quick_stamp_armed and self._quick_stamp_payload:
                payload = self._quick_stamp_payload
                self._quick_stamp_armed = False
                self._quick_stamp_payload = None
                # Zoom/Opacity wie Signatur merken — 1.9.4
                self._remember_quick_stamp_zoom_opacity()
                if payload.get("kind") == "image" and payload.get("path"):
                    from instantlensdoc.core.stamp_library import (
                        place_library_stamp,
                        remember_stamp_usage,
                    )

                    try:
                        place_library_stamp(
                            self.pdf_path,
                            payload["path"],
                            page_index=page,
                            x=float(x),
                            y=float(y),
                        )
                        remember_stamp_usage(
                            kind="image", image=str(payload.get("image") or "")
                        )
                        if self.store:
                            self.store.load()
                        self._render()
                        self.annotations_changed.emit()
                        self.status.emit(
                            f"Quick-Stempel: {payload.get('image') or 'Bild'}"
                        )
                    except Exception as e:
                        QMessageBox.warning(self, "Quick-Stempel", str(e))
                    return
                text = str(payload.get("text") or "GENEHMIGT")
                color = str(payload.get("color") or "#1E8449")
                width, height = 150.0, 52.0 if "\n" in text else 40.0
                from instantlensdoc.core.stamp_library import remember_stamp_usage

                remember_stamp_usage(kind="text", text=text, color=color)
            else:
                dlg = StampPickDialog(self)
                if dlg.exec() != QDialog.Accepted:
                    return
                picked = dlg.result_stamp()
                if not picked:
                    return
                text, color = picked
                width, height = 150.0, 52.0 if "\n" in text else 40.0
                from instantlensdoc.core.stamp_library import remember_stamp_usage

                remember_stamp_usage(kind="text", text=text, color=color)
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
        try:
            ann.stroke_width = max(
                1.0, min(12.0, float(getattr(self, "_default_stroke_width", 2.0)))
            )
        except (TypeError, ValueError):
            ann.stroke_width = 2.0
        # Fill-Default für Shapes ohne explizite Füllung — 0.9.9
        try:
            if ann.type == AnnotationType.RECTANGLE and not str(
                getattr(ann, "fill_color", "") or ""
            ).strip():
                fc = str(getattr(self, "_default_fill_color", "") or "").strip()
                if fc:
                    ann.fill_color = fc
        except Exception:
            pass
        self.store.add(ann)
        try:
            self.schedule_sidecar_save()
        except Exception as e:
            QMessageBox.warning(self, "Annotationen", f"Speichern fehlgeschlagen: {e}")
        try:
            from ild_pdf.doc_history import append_doc_history

            append_doc_history(
                self.pdf_path,
                "annotation.add",
                f"type={ann.type.value} page={ann.page}",
            )
        except Exception:
            pass
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
        self.schedule_sidecar_save(force=True)

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
        """Aktuelle Seite duplizieren (Kopie danach) und speichern; Undo Ctrl+Z."""
        return self.duplicate_at(self.page_index)

    def duplicate_many(self, page_indices: list[int] | Sequence[int]) -> int:
        """Mehrere Seiten duplizieren (hohe Indizes zuerst); Undo je Seite Ctrl+Z."""
        if not self.pdf_path:
            return 0
        pages = sorted({int(i) for i in page_indices}, reverse=True)
        if not pages:
            return 0
        n = 0
        for idx in pages:
            if self.duplicate_at(idx):
                n += 1
        if n:
            self.status.emit(f"{n} Seite(n) dupliziert (Ctrl+Z rückgängig)")
        return n

    def delete_many(self, page_indices: list[int] | Sequence[int], *, confirm: bool = True) -> int:
        """Mehrere Seiten löschen (hohe Indizes zuerst); eine Bestätigung; Undo je Seite."""
        if not self.pdf_path:
            return 0
        pages = sorted({int(i) for i in page_indices})
        if not pages:
            return 0
        remaining = int(self.page_count or 0) - len(pages)
        if remaining < 1:
            QMessageBox.information(
                self, "Löschen", "Es muss mindestens eine Seite übrig bleiben."
            )
            return 0
        if confirm:
            labels = ", ".join(str(p + 1) for p in pages[:12])
            if len(pages) > 12:
                labels += "…"
            reply = QMessageBox.question(
                self,
                "Seiten löschen",
                f"{len(pages)} Seite(n) wirklich löschen?\n({labels})\n(Rückgängig: Ctrl+Z)",
            )
            if reply != QMessageBox.Yes:
                return 0
        n = 0
        for idx in sorted(pages, reverse=True):
            if self.delete_at(idx, confirm=False):
                n += 1
        if n:
            self.status.emit(f"{n} Seite(n) gelöscht (Ctrl+Z rückgängig)")
        return n

    def duplicate_at(self, page_index: int) -> bool:
        """Seite an Index duplizieren (Kopie danach); Undo Ctrl+Z."""
        if not self.pdf_path:
            return False
        try:
            src = int(page_index)
        except (TypeError, ValueError):
            self.status.emit("Duplizieren: ungültige Seite")
            return False
        if src < 0 or src >= int(self.page_count or 0):
            self.status.emit("Duplizieren: ungültige Seite")
            return False
        try:
            groups_before: dict = {}
            favs_before: list = []
            if self.store is not None:
                groups_before = dict(self.store._meta.get("page_groups") or {})
                favs_before = list(self.store._meta.get("page_favorites") or [])
            undo_before = len(getattr(self.store, "_undo", []) or []) if self.store else 0
            new_idx = duplicate_page(self.pdf_path, src, after=True)
            self._remap_insert(new_idx)
            undo_after = len(getattr(self.store, "_undo", []) or []) if self.store else 0
            ann_remapped = undo_after > undo_before
            self._page_ops_undo.append(
                {
                    "kind": "duplicate",
                    "index": new_idx,
                    "source": src,
                    "page_groups": groups_before,
                    "page_favorites": favs_before,
                    "ann_remapped": ann_remapped,
                }
            )
            if len(self._page_ops_undo) > 20:
                self._page_ops_undo.pop(0)
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
            self.status.emit(
                f"Seite {src + 1} dupliziert → S. {new_idx + 1} (Ctrl+Z rückgängig)"
            )
            return True
        except Exception as e:
            if self._page_ops_undo and self._page_ops_undo[-1].get("kind") == "duplicate":
                self._page_ops_undo.pop()
            QMessageBox.warning(self, "Duplizieren", str(e))
            return False

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
        """Aktuelle Seite löschen (Bestätigung + Undo Ctrl+Z)."""
        return self.delete_at(self.page_index, confirm=True)

    def delete_at(self, page_index: int, *, confirm: bool = True) -> bool:
        """Seite an Index löschen (optional Bestätigung; Undo Ctrl+Z)."""
        if not self.pdf_path or self.page_count <= 1:
            QMessageBox.information(self, "Löschen", "Letzte Seite kann nicht gelöscht werden.")
            return False
        try:
            deleted = int(page_index)
        except (TypeError, ValueError):
            self.status.emit("Löschen: ungültige Seite")
            return False
        if deleted < 0 or deleted >= int(self.page_count or 0):
            self.status.emit("Löschen: ungültige Seite")
            return False
        if confirm:
            reply = QMessageBox.question(
                self,
                "Seite löschen",
                f"Seite {deleted + 1} wirklich löschen?\n(Rückgängig: Ctrl+Z)",
            )
            if reply != QMessageBox.Yes:
                return False
        try:
            if deleted != self.page_index:
                self.page_index = deleted
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
                self.schedule_sidecar_save(force=True)
            self.page_count -= 1
            self.page_index = min(self.page_index, self.page_count - 1)
            from ild_pdf.render import clear_render_cache

            clear_render_cache(self.pdf_path)
            self.refresh()
            self.annotations_changed.emit()
            self.page_changed.emit(self.page_index)
            self.document_changed.emit()
            self.status.emit("Seite gelöscht — Ctrl+Z stellt sie wieder her")
            return True
        except Exception as e:
            if self._page_ops_undo and self._page_ops_undo[-1].get("kind") == "delete":
                self._page_ops_undo.pop()
            QMessageBox.warning(self, "Löschen", str(e))
            return False

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
            self.schedule_sidecar_save(force=True)
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

    def apply_page_order(self, order: list[int], *, record_undo: bool = True) -> bool:
        """Wendet neue Seitenreihenfolge an (Dialog oder Thumbnail-Drag); Undo via Ctrl+Z."""
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
            # Inverse: order[new]=old → inverse[old]=new
            inverse = [0] * len(order)
            for new_i, old_i in enumerate(order):
                inverse[int(old_i)] = int(new_i)
            groups_before: dict = {}
            favs_before: list = []
            if self.store is not None:
                groups_before = dict(self.store._meta.get("page_groups") or {})
                favs_before = list(self.store._meta.get("page_favorites") or [])
            reorder_pages(self.pdf_path, order)
            ann_remapped = False
            if self.store:
                mapping = {old: new for new, old in enumerate(order)}
                undo_before = len(getattr(self.store, "_undo", []) or [])
                self.store.remap_pages(mapping)
                undo_after = len(getattr(self.store, "_undo", []) or [])
                ann_remapped = undo_after > undo_before
                self.schedule_sidecar_save(force=True)
            if record_undo:
                self._page_ops_undo.append(
                    {
                        "kind": "reorder",
                        "inverse": inverse,
                        "page_count": len(order),
                        "page_groups": groups_before,
                        "page_favorites": favs_before,
                        "ann_remapped": ann_remapped,
                    }
                )
                if len(self._page_ops_undo) > 20:
                    self._page_ops_undo.pop(0)
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
            msg = "Seiten neu angeordnet"
            if record_undo:
                msg += " (Ctrl+Z rückgängig)"
            self.status.emit(msg)
            return True
        except Exception as e:
            QMessageBox.warning(self, "Neu anordnen", str(e))
            return False

    def clear(self):
        self.flush_sidecar_save()
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