"""QGraphicsScene-Canvas für den DTP-Layout-Modus."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QTabletEvent,
    QTextCursor,
    QTransform,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from instantlensdoc.dtp.geometry import snap_point, snap_value
from instantlensdoc.dtp.model import DtpDocument, DtpFrame, DtpGuide
from instantlensdoc.dtp.presets import list_book_presets


PAGE_OFFSET = 40.0  # Rand um die Seite in der Szene


class ResizeHandle(QGraphicsRectItem):
    """Ecken-/Kantengriff zum Skalieren des Eltern-Rahmens."""

    ROLES = ("tl", "tm", "tr", "ml", "mr", "bl", "bm", "br")

    def __init__(self, role: str, parent: "FrameItem"):
        super().__init__(-3.5, -3.5, 7.0, 7.0, parent)
        self.role = role
        self.setBrush(QBrush(QColor("#FFFFFF")))
        self.setPen(QPen(QColor("#0B3D91"), 1.0))
        self.setZValue(80)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        cursors = {
            "tl": Qt.SizeFDiagCursor,
            "br": Qt.SizeFDiagCursor,
            "tr": Qt.SizeBDiagCursor,
            "bl": Qt.SizeBDiagCursor,
            "tm": Qt.SizeVerCursor,
            "bm": Qt.SizeVerCursor,
            "ml": Qt.SizeHorCursor,
            "mr": Qt.SizeHorCursor,
        }
        self.setCursor(QCursor(cursors.get(role, Qt.SizeAllCursor)))
        self._origin: QPointF | None = None
        self._geom: tuple[float, float, float, float] | None = None

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        parent = self.parentItem()
        if isinstance(parent, FrameItem) and parent.is_locked():
            event.ignore()
            return
        self._origin = event.scenePos()
        fr = parent.frame  # type: ignore[union-attr]
        self._geom = (fr.x, fr.y, fr.width, fr.height)
        event.accept()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._origin is None or self._geom is None:
            return
        parent = self.parentItem()
        if not isinstance(parent, FrameItem):
            return
        dx = event.scenePos().x() - self._origin.x()
        dy = event.scenePos().y() - self._origin.y()
        parent.resize_from(self.role, dx, dy, self._geom)
        event.accept()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        parent = self.parentItem()
        if isinstance(parent, FrameItem) and parent.frame.kind == "text":
            parent.reflow_after_edit()
        self._origin = None
        self._geom = None
        event.accept()


class FrameTextItem(QGraphicsTextItem):
    """Caret im Textrahmen; Doppelklick startet die Bearbeitung."""

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[override]
        parent = self.parentItem()
        if isinstance(parent, FrameItem) and not parent._editing:
            parent.begin_edit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def focusOutEvent(self, event) -> None:  # type: ignore[override]
        parent = self.parentItem()
        super().focusOutEvent(event)
        if isinstance(parent, FrameItem) and parent._editing:
            parent.end_edit()


class FrameItem(QGraphicsRectItem):
    def __init__(self, frame: DtpFrame, doc: DtpDocument):
        super().__init__(0, 0, frame.width, frame.height)
        self.frame = frame
        self.doc = doc
        self.text_item: QGraphicsTextItem | None = None
        self._handles: list[ResizeHandle] = []
        self._editing = False
        self.setPos(frame.x + PAGE_OFFSET, frame.y + PAGE_OFFSET)
        flags = QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges
        if not self.is_locked():
            flags |= QGraphicsItem.ItemIsMovable
        self.setFlags(flags)
        self.setAcceptHoverEvents(True)
        self._refresh_look()
        self._install_text()
        for role in ResizeHandle.ROLES:
            h = ResizeHandle(role, self)
            h.setVisible(False)
            self._handles.append(h)
        self._place_handles()

    def is_locked(self) -> bool:
        if self.frame.locked:
            return True
        for ly in self.doc.layers:
            if ly.id == self.frame.layer_id:
                return bool(ly.locked)
        return False

    def _install_text(self) -> None:
        if self.frame.kind != "text" or self.frame.path_kind or self.frame.as_outlines:
            return
        item = FrameTextItem(self)
        item.setPos(3, 2)
        item.setTextWidth(max(12.0, self.frame.width - 6))
        item.setPlainText(self.frame.text or "")
        item.setDefaultTextColor(QColor("#111111"))
        from instantlensdoc.dtp.export import _qfont_for_frame

        item.setFont(_qfont_for_frame(self.doc, self.frame))
        item.setTextInteractionFlags(Qt.NoTextInteraction)
        item.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.text_item = item

    def _refresh_look(self) -> None:
        if self.frame.kind == "text":
            self.setBrush(QBrush(QColor(255, 255, 255, 30)))
            self.setPen(QPen(QColor("#3B6DB5"), 0.8, Qt.DashLine))
        elif self.frame.kind == "shape":
            self.setBrush(Qt.NoBrush)
            self.setPen(QPen(QColor(self.frame.stroke or "#1A5276"), max(0.6, self.frame.stroke_width)))
        elif self.frame.kind == "image":
            self.setBrush(QBrush(QColor("#EEF3F8")))
            self.setPen(QPen(QColor("#5D6D7E"), 0.8))
        else:
            self.setBrush(QBrush(QColor("#F4F7FB")))
            self.setPen(QPen(QColor("#888"), 0.8))

    def _place_handles(self) -> None:
        w, h = self.frame.width, self.frame.height
        pos = {
            "tl": (0, 0),
            "tm": (w / 2, 0),
            "tr": (w, 0),
            "ml": (0, h / 2),
            "mr": (w, h / 2),
            "bl": (0, h),
            "bm": (w / 2, h),
            "br": (w, h),
        }
        for hdl in self._handles:
            x, y = pos[hdl.role]
            hdl.setPos(x, y)

    def set_handles_visible(self, visible: bool) -> None:
        for hdl in self._handles:
            hdl.setVisible(bool(visible) and not self.is_locked())

    def paint(self, painter: QPainter, option, widget=None) -> None:  # type: ignore[override]
        from instantlensdoc.dtp.export import paint_frame_local

        painter.save()
        if self.isSelected():
            painter.setPen(QPen(QColor("#0B3D91"), 1.15, Qt.DashLine))
        else:
            painter.setPen(self.pen())
        painter.setBrush(self.brush() if self.frame.kind == "text" else Qt.NoBrush)
        painter.drawRect(self.rect())
        if self.frame.kind == "text" and self.text_item is not None and not self.frame.path_kind:
            # Live-Text zeichnet QGraphicsTextItem; nur Overflow-Hint
            if self.frame.next_id:
                painter.setPen(QPen(QColor("#1A5276"), 1.0))
                painter.drawText(QRectF(self.frame.width - 14, self.frame.height - 12, 12, 10), Qt.AlignCenter, "↪")
        else:
            paint_frame_local(painter, self.doc, self.frame)
            if self.frame.kind == "image" and not self.frame.image_path:
                painter.setPen(QColor("#888"))
                painter.drawText(self.rect().adjusted(6, 6, -6, -6), Qt.AlignCenter, "Bild ersetzen…")
        painter.restore()

    def begin_edit(self) -> None:
        if self.text_item is None or self.is_locked():
            return
        self._editing = True
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.text_item.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.text_item.setFocus()
        cur = self.text_item.textCursor()
        cur.movePosition(QTextCursor.End)
        self.text_item.setTextCursor(cur)

    def end_edit(self) -> None:
        if self.text_item is None:
            self._editing = False
            return
        self.text_item.setTextInteractionFlags(Qt.NoTextInteraction)
        self.frame.text = self.text_item.toPlainText()
        self._editing = False
        if not self.is_locked():
            self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.reflow_after_edit()

    def set_plain_text(self, text: str) -> None:
        self.frame.text = text
        if self.text_item is not None:
            self.text_item.setPlainText(text)

    def reflow_after_edit(self) -> None:
        if self.frame.kind != "text":
            return
        self.doc.reflow_chain(self.frame, auto_extend=True)
        scene = self.scene()
        if isinstance(scene, DtpScene):
            scene.sync_text_items()

    def apply_style_font(self) -> None:
        if self.text_item is None:
            return
        from instantlensdoc.dtp.export import _qfont_for_frame

        self.text_item.setFont(_qfont_for_frame(self.doc, self.frame))

    def resize_from(self, role: str, dx: float, dy: float, orig: tuple[float, float, float, float]) -> None:
        x, y, w, h = orig
        if "r" in role:
            w = max(24.0, w + dx)
        if "l" in role:
            w = max(24.0, w - dx)
            x = x + dx if w > 24 else x
        if "b" in role:
            h = max(18.0, h + dy)
        if "t" in role:
            h = max(18.0, h - dy)
            y = y + dy if h > 18 else y
        grid = self.doc.grid_pt() if self.doc.grid_snap else 0.0
        if grid:
            x = snap_value(x, grid)
            y = snap_value(y, grid)
            w = max(24.0, snap_value(w, grid))
            h = max(18.0, snap_value(h, grid))
        self.prepareGeometryChange()
        self.frame.x, self.frame.y = x, y
        self.frame.resize(w, h)
        self.setRect(0, 0, w, h)
        self.setPos(x + PAGE_OFFSET, y + PAGE_OFFSET)
        if self.text_item is not None:
            self.text_item.setTextWidth(max(12.0, w - 6))
        self._place_handles()

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[override]
        if self.frame.kind == "text":
            self.begin_edit()
            event.accept()
            return
        if self.frame.kind == "image":
            scene = self.scene()
            pane = scene.parent() if scene is not None else None
            # DtpPane ruft replace_image
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def itemChange(self, change, value):  # type: ignore[override]
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self.set_handles_visible(bool(value))
        if change == QGraphicsItem.ItemPositionChange and self.scene() and not self._editing:
            if self.is_locked():
                return self.pos()
            pos: QPointF = value
            x = pos.x() - PAGE_OFFSET
            y = pos.y() - PAGE_OFFSET
            grid = self.doc.grid_pt() if self.doc.grid_snap else 0.0
            guides = self.doc.guides if self.doc.guides_snap else ()
            sx, sy = snap_point(x, y, grid_pt=grid, guides=guides)
            return QPointF(sx + PAGE_OFFSET, sy + PAGE_OFFSET)
        if change == QGraphicsItem.ItemPositionHasChanged and not self._editing:
            self.frame.x = self.pos().x() - PAGE_OFFSET
            self.frame.y = self.pos().y() - PAGE_OFFSET
        return super().itemChange(change, value)

    def focusOutEvent(self, event) -> None:  # type: ignore[override]
        if self._editing:
            self.end_edit()
        super().focusOutEvent(event)


class GuideItem(QGraphicsPathItem):
    def __init__(self, guide: DtpGuide, page_w: float, page_h: float):
        super().__init__()
        self.guide = guide
        self.orientation = guide.orientation
        self.page_w = page_w
        self.page_h = page_h
        self.setPen(QPen(QColor("#C0392B"), 0.9, Qt.DashLine))
        self.setZValue(50)
        self.setFlag(QGraphicsItem.ItemIsMovable, not guide.locked)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setCursor(QCursor(Qt.SplitHCursor if guide.orientation in ("v", "vertical") else Qt.SplitVCursor))
        self._rebuild_path()

    def _rebuild_path(self) -> None:
        path = QPainterPath()
        if self.orientation in ("v", "vertical"):
            path.moveTo(0, PAGE_OFFSET - 12)
            path.lineTo(0, self.page_h + PAGE_OFFSET + 12)
            self.setPos(self.guide.position_pt + PAGE_OFFSET, 0)
        else:
            path.moveTo(PAGE_OFFSET - 12, 0)
            path.lineTo(self.page_w + PAGE_OFFSET + 12, 0)
            self.setPos(0, self.guide.position_pt + PAGE_OFFSET)
        self.setPath(path)

    def itemChange(self, change, value):  # type: ignore[override]
        if change == QGraphicsItem.ItemPositionChange:
            p: QPointF = value
            if self.orientation in ("v", "vertical"):
                return QPointF(p.x(), 0)
            return QPointF(0, p.y())
        if change == QGraphicsItem.ItemPositionHasChanged:
            if self.orientation in ("v", "vertical"):
                self.guide.position_pt = self.pos().x() - PAGE_OFFSET
            else:
                self.guide.position_pt = self.pos().y() - PAGE_OFFSET
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
            self.addItem(GuideItem(gd, g.width_pt, g.height_pt))
        page = int(self.doc.current_page)
        for fr in self.doc.sorted_frames(page):
            it = FrameItem(fr, self.doc)
            it.setZValue(fr.z)
            self.addItem(it)
            self._items[fr.id] = it
        for fr in self.doc.frames:
            if fr.master and fr.id not in self._items:
                it = FrameItem(fr, self.doc)
                it.setZValue(fr.z)
                self.addItem(it)
                self._items[fr.id] = it

    def sync_text_items(self) -> None:
        for fid, it in self._items.items():
            fr = self.doc.frame_by_id(fid)
            if fr is None or it.text_item is None:
                continue
            if it._editing:
                continue
            if it.text_item.toPlainText() != (fr.text or ""):
                it.text_item.setPlainText(fr.text or "")
            it.text_item.setTextWidth(max(12.0, fr.width - 6))
            it.apply_style_font()
            it.setRect(0, 0, fr.width, fr.height)
            it.setPos(fr.x + PAGE_OFFSET, fr.y + PAGE_OFFSET)
            it._place_handles()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        xform = self.views()[0].transform() if self.views() else QTransform()
        hit = self.itemAt(event.scenePos(), xform)
        editing = [it for it in self._items.values() if it._editing]
        for it in editing:
            if hit is it or (it.text_item is not None and (hit is it.text_item or (hit and hit.parentItem() is it))):
                break
            else:
                it.end_edit()
        super().mousePressEvent(event)

    def selected_frames(self) -> list[DtpFrame]:
        out = []
        for it in self.selectedItems():
            if isinstance(it, FrameItem):
                out.append(it.frame)
            elif isinstance(it, (QGraphicsTextItem, FrameTextItem)) and isinstance(it.parentItem(), FrameItem):
                out.append(it.parentItem().frame)
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
        self._block_preset = False
        self._block_master = False
        self._block_style = False
        self._block_layer = False
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

        self.preset_combo = QComboBox()
        self.preset_combo.setObjectName("dtpPreset")
        self.preset_combo.setToolTip("Buchformat / Satzspiegel")
        for rec in list_book_presets():
            self.preset_combo.addItem(rec["name"], rec["name"])
        idx = self.preset_combo.findData(self.doc.geometry.name)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)
        self.preset_combo.currentIndexChanged.connect(self._on_preset)
        bar.addWidget(self.preset_combo)
        _btn("◀", self.prev_page, "Vorherige Seite")
        _btn("▶", self.next_page, "Nächste Seite")
        _btn("+Seite", self.add_page, "Seite hinzufügen")
        _btn("Textrahmen", self.add_text_frame, "Textrahmen einfügen (Doppelklick = Caret)")
        _btn("Bildrahmen", self.add_image_frame, "Bildrahmen; Doppelklick ersetzt")
        _btn("Form", self.add_shape, "Rechteck")
        _btn("Verketten", self.link_selected, "Zwei Textrahmen verketten und umbrechen")
        _btn("Import", self.import_text, "TXT/MD/DOCX/OCR in Rahmen")
        _btn("Bild…", self.replace_image, "Bild in ausgewählten Rahmen")
        _btn("Spalten", self.make_columns, "Spaltenkette auf der Seite")
        _btn("Raster", self.toggle_grid, "Raster ein/aus")
        _btn("Links", lambda: self.align("left"), "Links ausrichten")
        _btn("Mitte", lambda: self.align("center"), "Horizontal zentrieren")
        _btn("Verteilen", lambda: self.distribute("h"), "Horizontal verteilen")
        self.style_combo = QComboBox()
        self.style_combo.setObjectName("dtpStyle")
        self.style_combo.setToolTip("Absatz-/Zeichenformat")
        for sid, st in self.doc.styles.items():
            self.style_combo.addItem(f"{st.id} ({st.kind})", sid)
        self.style_combo.currentIndexChanged.connect(self._on_style)
        bar.addWidget(self.style_combo)
        self.master_combo = QComboBox()
        self.master_combo.setObjectName("dtpMaster")
        self.master_combo.setToolTip("Musterseite auf aktuelle Seite anwenden")
        self._reload_masters()
        self.master_combo.currentIndexChanged.connect(self._on_master)
        bar.addWidget(self.master_combo)
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
        _btn("PDF", self.export_pdf_dialog, "Layout als PDF (QPdfWriter)")
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
        side = QVBoxLayout()
        side.setContentsMargins(4, 4, 4, 4)
        side.addWidget(QLabel("Ebenen"))
        self.layer_list = QListWidget()
        self.layer_list.setObjectName("dtpLayerList")
        self.layer_list.setMaximumWidth(168)
        self.layer_list.itemChanged.connect(self._on_layer_item)
        self.layer_list.itemClicked.connect(self._on_layer_select)
        side.addWidget(self.layer_list, 1)
        _ly_btns = QHBoxLayout()
        up = QToolButton()
        up.setText("▲")
        up.setToolTip("Auswahl nach vorn")
        up.clicked.connect(self.bring_forward)
        dn = QToolButton()
        dn.setText("▼")
        dn.setToolTip("Auswahl nach hinten")
        dn.clicked.connect(self.send_backward)
        _ly_btns.addWidget(up)
        _ly_btns.addWidget(dn)
        side.addLayout(_ly_btns)
        body.addLayout(side)
        root.addLayout(body, 1)
        self._refresh_info()
        self._reload_layers()

    def set_document(self, doc: DtpDocument) -> None:
        self.doc = doc
        self.scene.doc = doc
        self.scene.rebuild()
        self._refresh_info()
        self._reload_layers()
        self._reload_masters()
        self._block_preset = True
        idx = self.preset_combo.findData(doc.geometry.name)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)
        self._block_preset = False

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
        self.scene.rebuild()
        self.statusMessage.emit(f"Bildrahmen {fr.id}")
        return fr

    def add_shape(self) -> DtpFrame:
        fr = self.doc.add_shape("rectangle", page=self.doc.current_page)
        self.scene.rebuild()
        return fr

    def prev_page(self) -> None:
        self.doc.current_page = max(0, self.doc.current_page - 1)
        self.scene.rebuild()
        self._refresh_info()

    def next_page(self) -> None:
        if self.doc.current_page + 1 >= self.doc.page_count:
            self.doc.add_page()
        self.doc.current_page += 1
        self.scene.rebuild()
        self._refresh_info()

    def add_page(self) -> None:
        self.doc.add_page()
        self.doc.current_page = self.doc.page_count - 1
        if self.doc.masters:
            self.doc.apply_master(self.doc.masters[0].id, pages=[self.doc.current_page])
        self.scene.rebuild()
        self._refresh_info()
        self.statusMessage.emit(f"Seite {self.doc.current_page + 1}")

    def import_text(self, path: str | None = None) -> None:
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Text in Rahmen importieren",
                "",
                "Text/OCR/Office (*.txt *.md *.html *.docx *.ildocr.txt *.hocr *.tsv);;Alle (*.*)",
            )
        if not path:
            return
        sel = [f for f in self.scene.selected_frames() if f.kind == "text"]
        fr = sel[0] if sel else self.doc.add_text_frame("", page=self.doc.current_page)
        self.doc.import_into_frame(fr.id, path, auto_extend=True)
        self.scene.rebuild()
        self.statusMessage.emit(f"Import: {path}")

    def replace_image(self, path: str | None = None) -> None:
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self, "Bild ersetzen", "", "Bilder (*.png *.jpg *.jpeg *.webp *.tif *.tiff);;Alle (*.*)"
            )
        if not path:
            return
        sel = self.scene.selected_frames()
        images = [f for f in sel if f.kind in ("image", "shape")]
        if images:
            self.doc.set_image(images[0].id, path)
        else:
            self.doc.add_image_frame(path, page=self.doc.current_page)
        self.scene.rebuild()
        self.statusMessage.emit("Bildrahmen aktualisiert")

    def _on_preset(self, _index: int = 0) -> None:
        if self._block_preset:
            return
        name = str(self.preset_combo.currentData() or self.preset_combo.currentText() or "")
        if not name:
            return
        self.doc.apply_preset(name)
        self.scene.rebuild()
        self._refresh_info()
        self.statusMessage.emit(f"Buchformat {name}")

    def _on_style(self, _index: int = 0) -> None:
        if self._block_style:
            return
        sid = str(self.style_combo.currentData() or "")
        if not sid:
            return
        for fr in self.scene.selected_frames() or [f for f in self.doc.frames_on_page(self.doc.current_page) if f.kind == "text"][:1]:
            try:
                self.doc.apply_style(fr.id, sid)
            except KeyError:
                pass
        self.scene.rebuild()
        self.statusMessage.emit(f"Stil {sid}")

    def _reload_masters(self) -> None:
        self._block_master = True
        self.master_combo.blockSignals(True)
        self.master_combo.clear()
        for m in self.doc.masters:
            self.master_combo.addItem(m.name, m.id)
        cur = ""
        if 0 <= self.doc.current_page < len(self.doc.page_master):
            cur = self.doc.page_master[self.doc.current_page]
        idx = self.master_combo.findData(cur)
        if idx >= 0:
            self.master_combo.setCurrentIndex(idx)
        self.master_combo.blockSignals(False)
        self._block_master = False

    def _on_master(self, _index: int = 0) -> None:
        if self._block_master:
            return
        mid = str(self.master_combo.currentData() or "")
        if not mid:
            return
        self.doc.apply_master(mid, pages=[self.doc.current_page])
        self.scene.rebuild()
        self.statusMessage.emit("Musterseite angewandt")

    def _reload_layers(self) -> None:
        self._block_layer = True
        self.layer_list.blockSignals(True)
        self.layer_list.clear()
        for ly in sorted(self.doc.layers, key=lambda x: x.z):
            item = QListWidgetItem(ly.name)
            item.setData(Qt.UserRole, ly.id)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if ly.visible else Qt.Unchecked)
            item.setToolTip("Sperren: " + ("ja" if ly.locked else "nein") + " — Klick wählt Rahmen")
            self.layer_list.addItem(item)
        self.layer_list.blockSignals(False)
        self._block_layer = False

    def _on_layer_item(self, item: QListWidgetItem) -> None:
        if self._block_layer or item is None:
            return
        lid = str(item.data(Qt.UserRole) or "")
        self.doc.set_layer_visible(lid, item.checkState() == Qt.Checked)
        self.scene.rebuild()

    def _on_layer_select(self, item: QListWidgetItem) -> None:
        if item is None:
            return
        lid = str(item.data(Qt.UserRole) or "")
        for it in self.scene._items.values():
            it.setSelected(it.frame.layer_id == lid)

    def bring_forward(self) -> None:
        for fr in self.scene.selected_frames():
            self.doc.bring_to_front(fr.id)
        self.scene.rebuild()

    def send_backward(self) -> None:
        for fr in self.scene.selected_frames():
            self.doc.send_to_back(fr.id)
        self.scene.rebuild()

    def link_selected(self) -> None:
        sel = self.scene.selected_frames()
        texts = [f for f in sel if f.kind == "text"]
        if len(texts) >= 2:
            self.doc.link_frames(texts[0].id, texts[1].id)
            self.doc.reflow_chain(texts[0], auto_extend=True)
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
        self.export_pdf_dialog()

    def export_pdf_dialog(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "DTP als PDF", "layout.pdf", "PDF (*.pdf)")
        if not path:
            return
        out = self.export_pdf_to(path)
        self.statusMessage.emit(f"DTP-PDF: {out}")

    def export_pdf_to(self, path: str) -> str:
        from instantlensdoc.dtp.export import export_pdf

        dest = export_pdf(self.doc, path)
        data = dest.read_bytes()[:8]
        if not data.startswith(b"%PDF"):
            raise RuntimeError("Export lieferte kein gültiges PDF")
        return str(dest)
