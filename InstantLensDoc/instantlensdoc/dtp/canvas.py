"""QGraphicsScene-Canvas für den DTP-Layout-Modus."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QTabletEvent,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from instantlensdoc.dtp.geometry import snap_point
from instantlensdoc.dtp.model import DtpDocument, DtpFrame


PAGE_OFFSET = 40.0  # Rand um die Seite in der Szene


class FrameItem(QGraphicsRectItem):
    def __init__(self, frame: DtpFrame, doc: DtpDocument):
        super().__init__(0, 0, frame.width, frame.height)
        self.frame = frame
        self.doc = doc
        self.setPos(frame.x + PAGE_OFFSET, frame.y + PAGE_OFFSET)
        self.setFlags(
            QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self._refresh_look()

    def _refresh_look(self) -> None:
        if self.frame.kind == "text":
            self.setBrush(QBrush(QColor(255, 255, 255, 40)))
            self.setPen(QPen(QColor("#3B6DB5"), 0.8, Qt.DashLine))
        elif self.frame.kind == "shape":
            self.setBrush(Qt.NoBrush)
            self.setPen(QPen(QColor(self.frame.stroke or "#1A5276"), max(0.6, self.frame.stroke_width)))
        else:
            self.setBrush(QBrush(QColor("#F4F7FB")))
            self.setPen(QPen(QColor("#888"), 0.8))

    def paint(self, painter: QPainter, option, widget=None) -> None:  # type: ignore[override]
        from instantlensdoc.dtp.export import paint_frame_local

        painter.save()
        if self.isSelected():
            painter.setPen(QPen(QColor("#0B3D91"), 1.15, Qt.DashLine))
        else:
            painter.setPen(self.pen())
        painter.setBrush(self.brush() if self.frame.kind == "text" else Qt.NoBrush)
        painter.drawRect(self.rect())
        paint_frame_local(painter, self.doc, self.frame)
        painter.restore()

    def itemChange(self, change, value):  # type: ignore[override]
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            pos: QPointF = value
            x = pos.x() - PAGE_OFFSET
            y = pos.y() - PAGE_OFFSET
            grid = self.doc.grid_pt() if self.doc.grid_snap else 0.0
            guides = self.doc.guides if self.doc.guides_snap else ()
            sx, sy = snap_point(x, y, grid_pt=grid, guides=guides)
            return QPointF(sx + PAGE_OFFSET, sy + PAGE_OFFSET)
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.frame.x = self.pos().x() - PAGE_OFFSET
            self.frame.y = self.pos().y() - PAGE_OFFSET
        return super().itemChange(change, value)


class GuideItem(QGraphicsPathItem):
    def __init__(self, orientation: str, pos: float, page_w: float, page_h: float):
        super().__init__()
        self.orientation = orientation
        self.pos_pt = pos
        path = QPainterPath()
        if orientation in ("v", "vertical"):
            path.moveTo(pos + PAGE_OFFSET, PAGE_OFFSET - 10)
            path.lineTo(pos + PAGE_OFFSET, page_h + PAGE_OFFSET + 10)
            self.setPen(QPen(QColor("#C0392B"), 0.8, Qt.DashLine))
        else:
            path.moveTo(PAGE_OFFSET - 10, pos + PAGE_OFFSET)
            path.lineTo(page_w + PAGE_OFFSET + 10, pos + PAGE_OFFSET)
            self.setPen(QPen(QColor("#C0392B"), 0.8, Qt.DashLine))
        self.setPath(path)
        self.setZValue(50)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

    def itemChange(self, change, value):  # type: ignore[override]
        if change == QGraphicsItem.ItemPositionChange:
            p: QPointF = value
            if self.orientation in ("v", "vertical"):
                return QPointF(p.x(), 0)
            return QPointF(0, p.y())
        return super().itemChange(change, value)


class DtpScene(QGraphicsScene):
    def __init__(self, doc: DtpDocument, parent=None):
        super().__init__(parent)
        self.doc = doc
        self._items: dict[str, FrameItem] = {}
        self.rebuild()

    def rebuild(self) -> None:
        self.clear()
        self._items.clear()
        g = self.doc.geometry
        self.setSceneRect(0, 0, g.width_pt + PAGE_OFFSET * 2, g.height_pt + PAGE_OFFSET * 2)
        # page paper
        paper = QGraphicsRectItem(PAGE_OFFSET, PAGE_OFFSET, g.width_pt, g.height_pt)
        paper.setBrush(QBrush(QColor("#ffffff")))
        paper.setPen(QPen(QColor("#888"), 1.0))
        paper.setZValue(-20)
        paper.setFlag(QGraphicsItem.ItemIsSelectable, False)
        paper.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.addItem(paper)
        # bleed
        if g.bleed_pt:
            bleed = QGraphicsRectItem(
                PAGE_OFFSET - g.bleed_pt,
                PAGE_OFFSET - g.bleed_pt,
                g.width_pt + 2 * g.bleed_pt,
                g.height_pt + 2 * g.bleed_pt,
            )
            bleed.setBrush(Qt.NoBrush)
            bleed.setPen(QPen(QColor("#E67E22"), 0.6, Qt.DotLine))
            bleed.setZValue(-19)
            self.addItem(bleed)
        # margins / satzspiegel
        margin = QGraphicsRectItem(
            PAGE_OFFSET + g.margin_left_pt,
            PAGE_OFFSET + g.margin_top_pt,
            g.width_pt - g.margin_left_pt - g.margin_right_pt,
            g.height_pt - g.margin_top_pt - g.margin_bottom_pt,
        )
        margin.setBrush(Qt.NoBrush)
        margin.setPen(QPen(QColor("#27AE60"), 0.7, Qt.DashLine))
        margin.setZValue(-18)
        self.addItem(margin)
        if self.doc.grid_visible:
            step = self.doc.grid_pt()
            x = 0.0
            while x <= g.width_pt + 0.1:
                line = QGraphicsPathItem()
                p = QPainterPath()
                p.moveTo(PAGE_OFFSET + x, PAGE_OFFSET)
                p.lineTo(PAGE_OFFSET + x, PAGE_OFFSET + g.height_pt)
                line.setPath(p)
                line.setPen(QPen(QColor(74, 144, 217, 60), 0.4))
                line.setZValue(-10)
                self.addItem(line)
                x += step
            y = 0.0
            while y <= g.height_pt + 0.1:
                line = QGraphicsPathItem()
                p = QPainterPath()
                p.moveTo(PAGE_OFFSET, PAGE_OFFSET + y)
                p.lineTo(PAGE_OFFSET + g.width_pt, PAGE_OFFSET + y)
                line.setPath(p)
                line.setPen(QPen(QColor(74, 144, 217, 60), 0.4))
                line.setZValue(-10)
                self.addItem(line)
                y += step
        for gd in self.doc.guides:
            self.addItem(GuideItem(gd.orientation, gd.position_pt, g.width_pt, g.height_pt))
        page = int(self.doc.current_page)
        for fr in self.doc.sorted_frames(page):
            it = FrameItem(fr, self.doc)
            it.setZValue(fr.z)
            self.addItem(it)
            self._items[fr.id] = it
            if fr.kind == "text" and not fr.text:
                label = QGraphicsSimpleTextItem("Textrahmen")
                label.setBrush(QColor("#999"))
                label.setParentItem(it)
                label.setPos(6, 6)

    def selected_frames(self) -> list[DtpFrame]:
        out = []
        for it in self.selectedItems():
            if isinstance(it, FrameItem):
                out.append(it.frame)
        return out


class DtpView(QGraphicsView):
    strokeFinished = Signal(list)  # list of [x,y,pressure] in page coords
    tabletPressure = Signal(float)

    def __init__(self, scene: DtpScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setBackgroundBrush(QBrush(QColor("#C5CCD6")))
        self.ink_mode = False
        self.recognize_on_finish = False
        self._stroke: list[list[float]] = []
        self._base_width = 2.2
        self.setMouseTracking(True)

    def _page_pos(self, view_pos) -> tuple[float, float]:
        sp = self.mapToScene(view_pos)
        return sp.x() - PAGE_OFFSET, sp.y() - PAGE_OFFSET

    def tabletEvent(self, event: QTabletEvent) -> None:  # type: ignore[override]
        if not self.ink_mode:
            event.ignore()
            return
        pressure = float(event.pressure())
        self.tabletPressure.emit(pressure)
        pos = event.position().toPoint()
        x, y = self._page_pos(pos)
        pt = [x, y, pressure]
        t = event.type()
        if t == QTabletEvent.Type.TabletPress:
            self._stroke = [pt]
            event.accept()
            return
        if t == QTabletEvent.Type.TabletMove:
            self._stroke.append(pt)
            event.accept()
            return
        if t == QTabletEvent.Type.TabletRelease:
            self._stroke.append(pt)
            self.strokeFinished.emit(list(self._stroke))
            self._stroke = []
            event.accept()
            return
        event.ignore()

    def mousePressEvent(self, event):  # type: ignore[override]
        if self.ink_mode and event.button() == Qt.LeftButton:
            x, y = self._page_pos(event.pos())
            self._stroke = [[x, y, 0.5]]
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # type: ignore[override]
        if self.ink_mode and self._stroke:
            x, y = self._page_pos(event.pos())
            self._stroke.append([x, y, 0.5])
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):  # type: ignore[override]
        if self.ink_mode and self._stroke:
            x, y = self._page_pos(event.pos())
            self._stroke.append([x, y, 0.5])
            self.strokeFinished.emit(list(self._stroke))
            self._stroke = []
            event.accept()
            return
        super().mouseReleaseEvent(event)


class _Ruler(QWidget):
    guideRequested = Signal(str, float)

    def __init__(self, orientation: str, *, thickness: int = 22):
        super().__init__()
        self.orientation = orientation  # h | v
        self._scale = 1.0
        self._offset = PAGE_OFFSET
        self._length = 595.0
        if orientation == "h":
            self.setFixedHeight(thickness)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        else:
            self.setFixedWidth(thickness)
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

    def set_metrics(self, scale: float, offset: float, length: float) -> None:
        self._scale = max(0.05, float(scale))
        self._offset = float(offset)
        self._length = float(length)
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#EEF2F6"))
        p.setPen(QColor("#333"))
        font = QFont()
        font.setPointSize(7)
        p.setFont(font)
        # ticks every 10 mm ≈ 28.35 pt
        step = 28.346
        i = 0
        while True:
            pt = i * step
            if pt > self._length + 1:
                break
            pos = self._offset * self._scale + pt * self._scale
            mm = int(round(pt / 2.8346))
            if self.orientation == "h":
                h = 12 if i % 5 == 0 else 6
                p.drawLine(int(pos), self.height() - h, int(pos), self.height())
                if i % 5 == 0:
                    p.drawText(int(pos) + 2, 10, str(mm))
            else:
                w = 12 if i % 5 == 0 else 6
                p.drawLine(self.width() - w, int(pos), self.width(), int(pos))
                if i % 5 == 0:
                    p.save()
                    p.translate(10, int(pos) + 10)
                    p.rotate(-90)
                    p.drawText(0, 0, str(mm))
                    p.restore()
            i += 1
        p.end()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if self.orientation == "h":
            pt = (event.position().x() / self._scale) - self._offset
            self.guideRequested.emit("vertical", float(pt))
        else:
            pt = (event.position().y() / self._scale) - self._offset
            self.guideRequested.emit("horizontal", float(pt))


class DtpPane(QWidget):
    """Komplettes DTP-Widget: Toolbar, Lineale, Canvas."""

    statusMessage = Signal(str)

    def __init__(self, parent=None, doc: DtpDocument | None = None):
        super().__init__(parent)
        self.setObjectName("ildDtpPane")
        self.doc = doc or DtpDocument.sample("A5")
        self.scene = DtpScene(self.doc)
        self.view = DtpView(self.scene)
        self.view.strokeFinished.connect(self._on_stroke)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        bar = QHBoxLayout()
        bar.setContentsMargins(4, 2, 4, 2)

        def _btn(label: str, slot, tip: str = "") -> QToolButton:
            b = QToolButton()
            b.setText(label)
            b.setToolTip(tip or label)
            b.clicked.connect(slot)
            bar.addWidget(b)
            return b

        _btn("Textrahmen", self.add_text_frame, "Textrahmen einfügen")
        _btn("Bildrahmen", self.add_image_frame, "Bild-/Platzhalterrahmen")
        _btn("Form", self.add_shape, "Rechteck")
        _btn("Verketten", self.link_selected, "Zwei Textrahmen verketten")
        _btn("Spalten", self.make_columns, "Spaltenkette auf der Seite")
        _btn("Raster", self.toggle_grid, "Raster ein/aus")
        _btn("Ausrichten", lambda: self.align("left"), "Links ausrichten")
        _btn("Verteilen", lambda: self.distribute("h"), "Horizontal verteilen")
        _btn("Envelope", self.apply_envelope, "Envelope Distort auf Auswahl")
        _btn("3D", self.apply_extrude, "Extrusion auf Auswahl")
        _btn("Pfadtext", self.apply_text_on_path, "Text auf Ellipse/Linie")
        _btn("Outlines", self.convert_to_outlines, "Text in Pfade umwandeln")
        _btn("Clip", self.apply_clip_mask, "Auswahl: Inhalt + Maske")
        _btn("Füllung", self.apply_live_fill, "Verlauf + Schatten")
        _btn("Glyphen", self.show_glyph_palette, "Glyphen-Palette")
        self._ink_btn = _btn("Stift", self.toggle_ink, "Drucksensitiver Stift")
        self._ink_btn.setCheckable(True)
        _btn("Erkennen", self.recognize_selected_ink, "Tinte → Form")
        _btn("PDF", self._emit_export, "Layout als PDF (QPdfWriter)")
        bar.addStretch(1)
        self._info = QLabel("")
        bar.addWidget(self._info)
        root.addLayout(bar)

        body = QHBoxLayout()
        body.setSpacing(0)
        col = QVBoxLayout()
        col.setSpacing(0)
        self.h_ruler = _Ruler("h")
        self.v_ruler = _Ruler("v")
        self.h_ruler.guideRequested.connect(self._add_guide)
        self.v_ruler.guideRequested.connect(self._add_guide)
        corner = QWidget()
        corner.setFixedSize(22, 22)
        corner.setStyleSheet("background:#EEF2F6;")
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(0)
        top.addWidget(corner)
        top.addWidget(self.h_ruler, 1)
        col.addLayout(top)
        mid = QHBoxLayout()
        mid.setContentsMargins(0, 0, 0, 0)
        mid.setSpacing(0)
        mid.addWidget(self.v_ruler)
        mid.addWidget(self.view, 1)
        col.addLayout(mid, 1)
        body.addLayout(col, 1)
        root.addLayout(body, 1)
        self._refresh_info()

    def set_document(self, doc: DtpDocument) -> None:
        self.doc = doc
        self.scene.doc = doc
        self.scene.rebuild()
        self._refresh_info()

    def _refresh_info(self) -> None:
        g = self.doc.geometry
        self._info.setText(
            f"{g.name} · {g.width_pt:.0f}×{g.height_pt:.0f} pt · Seite {self.doc.current_page + 1}/{self.doc.page_count}"
        )

    def add_text_frame(self) -> DtpFrame:
        fr = self.doc.add_text_frame("Neuer Text", page=self.doc.current_page)
        self.scene.rebuild()
        self.statusMessage.emit(f"Textrahmen {fr.id}")
        return fr

    def add_image_frame(self) -> DtpFrame:
        fr = self.doc.add_image_frame(page=self.doc.current_page)
        fr.kind = "shape"
        fr.shape = "rectangle"
        fr.fill = "#EEEEEE"
        self.scene.rebuild()
        return fr

    def add_shape(self) -> DtpFrame:
        fr = self.doc.add_shape("rectangle", page=self.doc.current_page)
        self.scene.rebuild()
        return fr

    def link_selected(self) -> None:
        sel = self.scene.selected_frames()
        texts = [f for f in sel if f.kind == "text"]
        if len(texts) >= 2:
            self.doc.link_frames(texts[0].id, texts[1].id)
            if texts[0].text:
                self.doc.flow_text(texts[0].text, texts[0])
            self.scene.rebuild()
            self.statusMessage.emit(f"Verkettet {texts[0].id} → {texts[1].id}")

    def make_columns(self) -> None:
        self.doc.geometry.columns = max(2, self.doc.geometry.columns)
        frames = self.doc.create_column_chain(page=self.doc.current_page, columns=self.doc.geometry.columns)
        sample = ("Spaltenfluss — InstantLens Doc DTP. " * 40)
        self.doc.flow_text(sample, frames[0])
        self.scene.rebuild()

    def toggle_grid(self) -> None:
        self.doc.grid_visible = not self.doc.grid_visible
        self.scene.rebuild()

    def align(self, mode: str) -> None:
        from instantlensdoc.dtp.geometry import align_frames

        align_frames(self.scene.selected_frames(), mode)
        self.scene.rebuild()

    def distribute(self, axis: str) -> None:
        from instantlensdoc.dtp.geometry import distribute_frames

        distribute_frames(self.scene.selected_frames(), axis)
        self.scene.rebuild()

    def apply_envelope(self) -> None:
        from instantlensdoc.dtp.envelope import envelope_corners_default

        for fr in self.scene.selected_frames() or self.doc.frames_on_page(self.doc.current_page)[:1]:
            from instantlensdoc.dtp.model import EnvelopeMesh

            fr.envelope = EnvelopeMesh(corners=envelope_corners_default(fr.width, fr.height))
        self.scene.rebuild()
        self.statusMessage.emit("Envelope Distort angewandt")

    def apply_extrude(self) -> None:
        from instantlensdoc.dtp.model import ExtrudeSpec

        for fr in self.scene.selected_frames() or [f for f in self.doc.frames if f.kind == "shape"][:1]:
            fr.extrude = ExtrudeSpec()
        self.scene.rebuild()
        self.statusMessage.emit("3D-Extrusion angewandt")

    def apply_text_on_path(self, kind: str = "ellipse") -> None:
        frames = [f for f in self.scene.selected_frames() if f.kind == "text"]
        if not frames:
            frames = [f for f in self.doc.frames_on_page(self.doc.current_page) if f.kind == "text"][:1]
        for fr in frames:
            self.doc.apply_text_on_path(fr.id, kind)
        self.scene.rebuild()
        self.statusMessage.emit("Text auf Pfad")

    def convert_to_outlines(self) -> None:
        frames = [f for f in self.scene.selected_frames() if f.kind == "text"]
        if not frames:
            frames = [f for f in self.doc.frames_on_page(self.doc.current_page) if f.kind == "text"][:1]
        for fr in frames:
            self.doc.convert_text_to_outlines(fr.id)
        self.scene.rebuild()
        self.statusMessage.emit("Text in Pfade umgewandelt")

    def apply_clip_mask(self) -> None:
        sel = self.scene.selected_frames()
        if len(sel) >= 2:
            self.doc.apply_clip_mask(sel[0].id, sel[1].id)
            self.statusMessage.emit(f"Schnittmaske {sel[0].id} ← {sel[1].id}")
        else:
            page = self.doc.frames_on_page(self.doc.current_page)
            shapes = [f for f in page if f.kind == "shape"]
            others = [f for f in page if f.kind != "shape"]
            if shapes and others:
                self.doc.apply_clip_mask(others[0].id, shapes[0].id)
                self.statusMessage.emit("Schnittmaske (Seite)")
            else:
                self.statusMessage.emit("Schnittmaske: zwei Rahmen wählen")
                return
        self.scene.rebuild()

    def apply_live_fill(self) -> None:
        targets = [f for f in self.scene.selected_frames() if f.kind in ("shape", "image")]
        if not targets:
            targets = [f for f in self.doc.frames_on_page(self.doc.current_page) if f.kind == "shape"][:1]
        for fr in targets:
            self.doc.apply_live_fill(fr.id, kind="linear", shadow=True)
        self.scene.rebuild()
        self.statusMessage.emit("Live-Füllung / Schatten")

    def show_glyph_palette(self) -> None:
        from instantlensdoc.features.glyph_dialog import GlyphPaletteDialog

        fam = ""
        texts = [f for f in self.scene.selected_frames() if f.kind == "text"]
        if texts:
            fam = texts[0].font_family or ""
        dlg = GlyphPaletteDialog(self, family=fam)
        if dlg.exec() != 1:  # QDialog.Accepted
            return
        glyph = dlg.selected_glyph()
        if not glyph:
            return
        if not texts:
            texts = [f for f in self.doc.frames_on_page(self.doc.current_page) if f.kind == "text"][:1]
        if not texts:
            fr = self.add_text_frame()
            texts = [fr]
        for fr in texts:
            self.doc.insert_glyph(fr.id, glyph)
            if dlg.selected_family() and not fr.font_family:
                fr.font_family = dlg.selected_family()
        self.scene.rebuild()
        self.statusMessage.emit(f"Glyphe eingefügt: {glyph}")

    def toggle_ink(self, checked: bool = False) -> None:
        self.view.ink_mode = bool(self._ink_btn.isChecked() if hasattr(self, "_ink_btn") else checked)
        self.statusMessage.emit("Stift " + ("an" if self.view.ink_mode else "aus"))

    def _on_stroke(self, points: list) -> None:
        if not points:
            return
        fr = self.doc.add_ink_stroke(points, page=self.doc.current_page)
        if self.view.recognize_on_finish:
            self._recognize_frame(fr)
        self.scene.rebuild()

    def recognize_selected_ink(self) -> None:
        from instantlensdoc.features.shape_recognizer import recognize_ink_as_shape

        for fr in list(self.doc.frames_on_page(self.doc.current_page)):
            if fr.kind == "ink" and fr.ink_points:
                self._recognize_frame(fr)
        self.scene.rebuild()

    def _recognize_frame(self, fr: DtpFrame) -> None:
        from instantlensdoc.features.shape_recognizer import recognize_ink_as_shape

        result = recognize_ink_as_shape(fr.ink_points)
        if result.kind in ("ink", ""):
            return
        fr.kind = "shape"
        fr.shape = result.kind
        fr.x, fr.y, fr.width, fr.height = result.rect
        fr.ink_points = []
        self.statusMessage.emit(f"Erkannt: {result.kind} ({result.confidence:.0%})")

    def _add_guide(self, orientation: str, pos: float) -> None:
        self.doc.add_guide(orientation, pos)
        self.scene.rebuild()

    def _emit_export(self) -> None:
        self.statusMessage.emit("DTP-PDF-Export über Menü Datei / Ribbon")

    def export_pdf_to(self, path: str) -> str:
        from instantlensdoc.dtp.export import export_pdf

        return str(export_pdf(self.doc, path))
