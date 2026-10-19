from __future__ import annotations

from PySide6.QtCore import QEvent, QMimeData, QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QPainter, QPen
from PySide6.QtWidgets import QPlainTextEdit, QWidget

from officedisplay.input.pointer import StrokeBuilder, device_kind_from_name, interpret_pointer
from officedisplay.model.presentation import SlideObject, clamp_object, new_id
from officedisplay.ui.render import paint_slide


def _segment_distance(px: float, py: float, start, end) -> float:
    x1, y1 = start[0], start[1]
    x2, y2 = end[0], end[1]
    dx, dy = x2 - x1, y2 - y1
    length = dx * dx + dy * dy
    if length <= 1e-12:
        return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length))
    return ((px - (x1 + t * dx)) ** 2 + (py - (y1 + t * dy)) ** 2) ** 0.5


class SlideCanvas(QWidget):
    changed = Signal()
    gestureStarted = Signal()
    pointerKindChanged = Signal(str)
    selectionChanged = Signal(list)
    statusMessage = Signal(str)
    filesDropped = Signal(list, float, float)
    textDropped = Signal(str, float, float)
    shapeContext = Signal(str, QPoint)

    def __init__(self) -> None:
        super().__init__()
        self.presentation = None
        self.slide_index = 0
        self.tool = "select"
        self.touch_mode = "pan"
        self.pen_width = 6.0
        self.pen_curve = 1.0
        self.pen_smooth = 1
        self.highlighter = False
        self.snap = True
        self.view_scale = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.selected: list[str] = []
        self._drag = None
        self._stroke: StrokeBuilder | None = None
        self._tablet = False
        self._pinch_distance = None
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TabletTracking, True)
        self.setMouseTracking(True)
        self.grabGesture(Qt.GestureType.PinchGesture)
        self.setAcceptDrops(True)
        self.editor = QPlainTextEdit(self)
        self.editor.hide()
        self.editor.setFrameStyle(0)
        self.editor.focusOutEvent = self._editor_focus_out  # type: ignore[method-assign]
        self._editing_id = None

    def set_presentation(self, presentation, index: int = 0) -> None:
        self.presentation = presentation
        self.slide_index = index
        self.selected = []
        self.editor.hide()
        self.update()

    def set_index(self, index: int) -> None:
        if not self.presentation:
            return
        self.slide_index = max(0, min(index, len(self.presentation.slides) - 1))
        self.selected = []
        self.editor.hide()
        self.selectionChanged.emit([])
        self.update()

    def slide(self):
        if not self.presentation:
            return None
        return self.presentation.slides[self.slide_index]

    def slide_rect(self) -> QRectF:
        if not self.presentation:
            return QRectF(20, 20, 200, 100)
        margin = 28
        avail_w = max(10, self.width() - margin * 2)
        avail_h = max(10, self.height() - margin * 2)
        scale = min(avail_w / self.presentation.width, avail_h / self.presentation.height) * self.view_scale
        width = self.presentation.width * scale
        height = self.presentation.height * scale
        return QRectF((self.width() - width) / 2 + self.pan_x, (self.height() - height) / 2 + self.pan_y, width, height)

    def n2w(self, x: float, y: float) -> QPointF:
        rect = self.slide_rect()
        return QPointF(rect.x() + x * rect.width(), rect.y() + y * rect.height())

    def w2n(self, x: float, y: float) -> tuple[float, float]:
        rect = self.slide_rect()
        if rect.width() <= 0 or rect.height() <= 0:
            return 0, 0
        return (x - rect.x()) / rect.width(), (y - rect.y()) / rect.height()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#00000000"))
        slide = self.slide()
        if slide is None:
            painter.end()
            return
        rect = self.slide_rect()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 40))
        painter.drawRoundedRect(rect.translated(8, 10), 8, 8)
        painter.setClipRect(rect)
        paint_slide(painter, self.presentation, slide, rect, set(self.selected))
        painter.setClipping(False)
        if len(self.selected) == 1:
            obj = self._find(self.selected[0])
            if obj is not None:
                self._handles(painter, obj)
        if self._drag and self._drag.get("mode") == "create":
            box = self._norm_rect(self._drag["x0"], self._drag["y0"], self._drag["x1"], self._drag["y1"])
            painter.setPen(QPen(QColor("#0B63E5"), 1, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            a = self.n2w(box[0], box[1])
            b = self.n2w(box[0] + box[2], box[1] + box[3])
            painter.drawRect(QRectF(a, b))
        painter.end()

    def _handles(self, painter: QPainter, obj) -> None:
        painter.setBrush(QColor("#FFFFFF"))
        painter.setPen(QPen(QColor("#0B63E5"), 1))
        for _name, point in self._handle_points(obj):
            painter.drawRect(QRectF(point.x() - 5, point.y() - 5, 10, 10))

    def _handle_points(self, obj) -> list[tuple[str, QPointF]]:
        x, y, w, h = obj.x, obj.y, obj.w, obj.h
        pairs = {
            "nw": (x, y),
            "n": (x + w / 2, y),
            "ne": (x + w, y),
            "e": (x + w, y + h / 2),
            "se": (x + w, y + h),
            "s": (x + w / 2, y + h),
            "sw": (x, y + h),
            "w": (x, y + h / 2),
        }
        return [(name, self.n2w(px, py)) for name, (px, py) in pairs.items()]

    def _find(self, object_id: str):
        slide = self.slide()
        if slide is None:
            return None
        for obj in slide.objects:
            if obj.id == object_id:
                return obj
        return None

    def _hit(self, nx: float, ny: float):
        slide = self.slide()
        if slide is None:
            return None
        for obj in reversed(slide.objects):
            if obj.id == "__preview__":
                continue
            if obj.kind == "path":
                if self._near_slide_path(obj, nx, ny):
                    return obj
                continue
            if obj.x <= nx <= obj.x + obj.w and obj.y <= ny <= obj.y + obj.h:
                return obj
        return None

    def _near_slide_path(self, obj, nx: float, ny: float) -> bool:
        points = obj.props.get("points") or []
        if obj.props.get("coords") != "slide":
            points = [[obj.x + point[0] * obj.w, obj.y + point[1] * obj.h, point[2]] for point in points]
        tolerance = 0.03
        for index in range(1, len(points)):
            if _segment_distance(nx, ny, points[index - 1], points[index]) <= tolerance:
                return True
        return False

    def _handle_at(self, pos) -> str | None:
        if len(self.selected) != 1:
            return None
        obj = self._find(self.selected[0])
        if obj is None:
            return None
        for name, point in self._handle_points(obj):
            if abs(point.x() - pos.x()) <= 8 and abs(point.y() - pos.y()) <= 8:
                return name
        return None

    def _snap(self, value: float) -> float:
        if not self.snap:
            return value
        return round(value / 0.02) * 0.02

    def pointer_event(self, kind: str, phase: str, x: float, y: float, pressure: float, shift: bool) -> None:
        if self.slide() is None:
            return
        self.pointerKindChanged.emit({"pen": "Stift", "eraser": "Radierer", "touch": "Touch", "mouse": "Maus"}.get(kind, kind))
        action = interpret_pointer(self.tool, kind, self.touch_mode)
        nx, ny = self.w2n(x, y)
        if phase == "press":
            self.gestureStarted.emit()
            if action == "draw":
                self._stroke = StrokeBuilder(self.pen_width, self.pen_curve, self.pen_smooth, kind)
                self._stroke.add(nx, ny, pressure)
                self._drag = {"mode": "draw"}
            elif action == "erase":
                self._erase(nx, ny)
                self._drag = {"mode": "erase"}
            elif action == "pan":
                self._drag = {"mode": "pan", "x": x, "y": y}
            else:
                handle = self._handle_at(QPointF(x, y))
                if handle:
                    obj = self._find(self.selected[0])
                    self._drag = {"mode": "resize", "handle": handle, "origin": (obj.x, obj.y, obj.w, obj.h)}
                else:
                    hit = self._hit(nx, ny)
                    if hit is None and self.tool == "select":
                        self.selected = []
                        self.selectionChanged.emit([])
                        self._drag = {"mode": "pan", "x": x, "y": y}
                    elif hit is None and self.tool not in {"select", "pen", "eraser", "highlighter", "pan"}:
                        self._drag = {"mode": "create", "x0": nx, "y0": ny, "x1": nx, "y1": ny}
                    elif hit is not None:
                        if shift and self.tool == "select":
                            drag = QDrag(self)
                            mime = QMimeData()
                            mime.setData("application/x-officedisplay-object", hit.id.encode("utf-8"))
                            drag.setMimeData(mime)
                            drag.exec(Qt.DropAction.MoveAction)
                            self._drag = None
                            return
                        self.selected = [hit.id]
                        self.selectionChanged.emit(self.selected)
                        self._drag = {"mode": "move", "id": hit.id, "nx": nx, "ny": ny, "ox": hit.x, "oy": hit.y}
                        if self.tool == "text":
                            self.begin_text_edit(hit.id)
        elif phase == "move" and self._drag:
            if self._drag["mode"] == "draw" and self._stroke:
                self._stroke.add(nx, ny, pressure)
                self._preview_stroke()
            elif self._drag["mode"] == "erase":
                self._erase(nx, ny)
            elif self._drag["mode"] == "pan":
                self.pan_x += x - self._drag["x"]
                self.pan_y += y - self._drag["y"]
                self._drag["x"], self._drag["y"] = x, y
            elif self._drag["mode"] == "move":
                if not self.rect().contains(int(x), int(y)):
                    object_id = self._drag["id"]
                    self._drag = None
                    self._start_object_drag(object_id)
                    return
                obj = self._find(self._drag["id"])
                if obj:
                    obj.x = self._snap(self._drag["ox"] + (nx - self._drag["nx"]))
                    obj.y = self._snap(self._drag["oy"] + (ny - self._drag["ny"]))
                    clamp_object(obj)
            elif self._drag["mode"] == "resize":
                self._resize(nx, ny)
            elif self._drag["mode"] == "create":
                self._drag["x1"], self._drag["y1"] = nx, ny
            self.update()
        elif phase == "release":
            if self._drag and self._drag.get("mode") == "draw":
                self._commit_stroke()
            elif self._drag and self._drag.get("mode") == "create":
                self._commit_shape()
            elif self._drag and self._drag.get("mode") == "move" and self.tool == "text" and not self._editing_id:
                pass
            self._drag = None
            self._stroke = None
            self.changed.emit()
            self.update()

    def _preview_stroke(self) -> None:
        if not self._stroke:
            return
        slide = self.slide()
        points = self._stroke.points
        existing = self._find("__preview__")
        if existing is None:
            slide.objects.append(
                SlideObject(
                    id="__preview__",
                    kind="path",
                    x=0,
                    y=0,
                    w=1,
                    h=1,
                    props=self._stroke_props(points),
                )
            )
        else:
            existing.props = self._stroke_props(points)

    def _stroke_props(self, points) -> dict:
        return {
            "points": [[x, y, p] for x, y, p in points],
            "coords": "slide",
            "color": "#F2D15C" if self.highlighter or self.tool == "highlighter" else "#0B63E5",
            "base_width": self.pen_width,
            "curve": self.pen_curve,
            "pointer": self._stroke.pointer_kind if self._stroke else "pen",
            "highlighter": self.highlighter or self.tool == "highlighter",
        }

    def _commit_stroke(self) -> None:
        slide = self.slide()
        preview = self._find("__preview__")
        if preview is not None:
            slide.objects.remove(preview)
        if not self._stroke or len(self._stroke.points) < 2:
            return
        finished = self._stroke.finish()
        obj = self._stroke_object(finished, self._stroke.pointer_kind)
        if obj is not None:
            slide.objects.append(obj)

    def add_stroke_points(self, points: list[tuple[float, float, float]], pointer: str = "pen") -> str:
        """Test- und Skriptzugang ohne echtes Tablett."""
        builder = StrokeBuilder(self.pen_width, self.pen_curve, self.pen_smooth, pointer)
        for x, y, pressure in points:
            builder.add(x, y, pressure)
        finished = builder.finish()
        obj = self._stroke_object(finished, pointer)
        if obj is None:
            return ""
        self.slide().objects.append(obj)
        self.changed.emit()
        self.update()
        return obj.id

    def _commit_shape(self) -> None:
        x, y, w, h = self._norm_rect(self._drag["x0"], self._drag["y0"], self._drag["x1"], self._drag["y1"])
        if w < 0.02 or h < 0.02:
            w, h = 0.28, 0.16
        kind = self.tool
        if kind == "text":
            obj = SlideObject(
                id=new_id(),
                kind="text",
                x=x,
                y=y,
                w=max(w, 0.3),
                h=max(h, 0.12),
                name="text",
                props={
                    "text": "Text",
                    "font_family": "Segoe UI",
                    "font_size": 28,
                    "bold": False,
                    "italic": False,
                    "underline": False,
                    "color": "#1B1F2A",
                    "align": "left",
                },
            )
            self.slide().objects.append(obj)
            self.selected = [obj.id]
            self.begin_text_edit(obj.id)
        elif kind == "chart":
            self.slide().objects.append(
                SlideObject(
                    id=new_id(),
                    kind="chart",
                    x=x,
                    y=y,
                    w=max(w, 0.4),
                    h=max(h, 0.3),
                    name="diagramm",
                    props={
                        "chart_type": "bar",
                        "categories": ["A", "B", "C"],
                        "series": [{"name": "Beispielwerte – ersetzen", "values": [3, 5, 4]}],
                        "example": True,
                    },
                )
            )
        else:
            created_id = new_id()
            shape = {
                "rect": "rect",
                "ellipse": "ellipse",
                "roundrect": "roundrect",
                "triangle": "triangle",
                "diamond": "diamond",
                "star": "star",
                "arrow": "arrow",
                "line": "line",
            }.get(kind, "rect")
            self.slide().objects.append(
                SlideObject(
                    id=created_id,
                    kind="shape",
                    x=x,
                    y=y,
                    w=w,
                    h=h,
                    name=shape,
                    props={"shape": shape, "fill": "#0B63E5", "stroke": "#00000000", "stroke_width": 0},
                )
            )
            self.selected = [created_id]
        self.selectionChanged.emit(self.selected)

    def _stroke_object(self, points, pointer: str) -> SlideObject | None:
        if len(points) < 2:
            return None
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        width = max(max_x - min_x, 0.01)
        height = max(max_y - min_y, 0.01)
        local = [[(x - min_x) / width, (y - min_y) / height, pressure] for x, y, pressure in points]
        return SlideObject(
            id=new_id(),
            kind="path",
            x=min_x,
            y=min_y,
            w=width,
            h=height,
            name="strich",
            props={
                "points": local,
                "coords": "local",
                "color": "#F2D15C" if self.highlighter or self.tool == "highlighter" else "#0B63E5",
                "base_width": self.pen_width,
                "curve": self.pen_curve,
                "pointer": pointer,
                "highlighter": self.highlighter or self.tool == "highlighter",
            },
        )

    def _norm_rect(self, x0, y0, x1, y1):
        return min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0)

    def _resize(self, nx, ny) -> None:
        obj = self._find(self.selected[0]) if self.selected else None
        if obj is None:
            return
        x, y, w, h = self._drag["origin"]
        handle = self._drag["handle"]
        right, bottom = x + w, y + h
        if "w" in handle:
            x = min(nx, right - 0.02)
            w = right - x
        if "e" in handle:
            w = max(0.02, nx - x)
        if "n" in handle:
            y = min(ny, bottom - 0.02)
            h = bottom - y
        if "s" in handle:
            h = max(0.02, ny - y)
        obj.x, obj.y, obj.w, obj.h = x, y, w, h
        clamp_object(obj)

    def _erase(self, nx, ny) -> None:
        slide = self.slide()
        hit = self._hit(nx, ny)
        if hit is not None and hit.kind == "path":
            slide.objects.remove(hit)
            self.selected = [item for item in self.selected if item != hit.id]

    def begin_text_edit(self, object_id: str) -> None:
        obj = self._find(object_id)
        if obj is None or obj.kind != "text":
            return
        self._editing_id = object_id
        point = self.n2w(obj.x, obj.y)
        end = self.n2w(obj.x + obj.w, obj.y + obj.h)
        self.editor.setGeometry(int(point.x()), int(point.y()), max(80, int(end.x() - point.x())), max(40, int(end.y() - point.y())))
        self.editor.setPlainText(str(obj.props.get("text") or ""))
        self.editor.show()
        self.editor.setFocus()

    def _editor_focus_out(self, event) -> None:
        self.commit_text()
        QPlainTextEdit.focusOutEvent(self.editor, event)

    def commit_text(self) -> None:
        if not self._editing_id:
            return
        obj = self._find(self._editing_id)
        if obj is not None:
            from officedisplay.ai.offline_design import estimate_font

            obj.props["text"] = self.editor.toPlainText()
            obj.props["font_size"] = estimate_font(
                obj.props["text"], obj.w, obj.h, self.presentation.height, int(obj.props.get("font_size") or 24)
            )
        self._editing_id = None
        self.editor.hide()
        self.changed.emit()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self._right_click(event)
            return
        if self._tablet:
            return
        kind = self._kind_from_device(event)
        if kind == "pen":
            return
        self.pointer_event(kind, "press", event.position().x(), event.position().y(), self._pressure(event), bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier))

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.RightButton and not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if self._tablet:
            return
        kind = self._kind_from_device(event)
        if kind == "pen":
            return
        phase = "move" if event.buttons() else "hover"
        if phase == "hover":
            self.pointerKindChanged.emit("Maus")
            return
        self.pointer_event(kind, "move", event.position().x(), event.position().y(), self._pressure(event), bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier))

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            return
        if self._tablet:
            self._tablet = False
            return
        kind = self._kind_from_device(event)
        self.pointer_event(kind, "release", event.position().x(), event.position().y(), self._pressure(event), False)

    def _right_click(self, event) -> None:
        """Kontext der Form unter dem Zeiger. Die Auswahl bleibt unverändert."""
        kept = list(self.selected)
        nx, ny = self.w2n(event.position().x(), event.position().y())
        hit = self._hit(nx, ny)
        self.selected = kept
        if hit is None or hit.kind != "shape":
            return
        pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
        self.shapeContext.emit(hit.id, pos)

    def contextMenuEvent(self, event) -> None:
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        nx, ny = self.w2n(event.position().x(), event.position().y())
        hit = self._hit(nx, ny)
        if hit and hit.kind == "text":
            self.begin_text_edit(hit.id)
        elif hit and hit.kind == "video":
            self.statusMessage.emit("video:" + str(hit.props.get("path") or ""))

    def tabletEvent(self, event) -> None:
        pointer = ""
        try:
            pointer = event.pointerType().name
        except Exception:
            pointer = str(event.pointerType())
        kind = device_kind_from_name("stylus", pointer)
        phase = {
            QEvent.Type.TabletPress: "press",
            QEvent.Type.TabletMove: "move",
            QEvent.Type.TabletRelease: "release",
        }.get(event.type(), "move")
        self._tablet = phase != "release"
        pos = event.position()
        self.pointer_event(kind, phase, pos.x(), pos.y(), float(event.pressure()), False)
        event.accept()

    def event(self, event):
        if event.type() in {QEvent.Type.TabletPress, QEvent.Type.TabletMove, QEvent.Type.TabletRelease}:
            self.tabletEvent(event)
            return True
        if event.type() in {QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate, QEvent.Type.TouchEnd}:
            self._touch(event)
            return True
        if event.type() == QEvent.Type.Gesture:
            pinch = event.gesture(Qt.GestureType.PinchGesture)
            if pinch is not None and pinch.changeFlags() & pinch.ChangeFlag.ScaleFactorChanged:
                self.view_scale = max(0.3, min(4.0, self.view_scale * pinch.scaleFactor()))
                self.pointerKindChanged.emit("Touch")
                self.update()
                return True
        return super().event(event)

    def _touch(self, event) -> None:
        points = list(event.points())
        self.pointerKindChanged.emit("Touch")
        if len(points) >= 2:
            a, b = points[0].position(), points[1].position()
            distance = ((a.x() - b.x()) ** 2 + (a.y() - b.y()) ** 2) ** 0.5
            if self._pinch_distance:
                factor = distance / self._pinch_distance if self._pinch_distance else 1
                self.view_scale = max(0.3, min(4.0, self.view_scale * factor))
            self._pinch_distance = distance
            if event.type() == QEvent.Type.TouchEnd:
                self._pinch_distance = None
            self.update()
            event.accept()
            return
        if not points:
            return
        point = points[0]
        diameters = point.ellipseDiameters() if hasattr(point, "ellipseDiameters") else None
        if diameters is not None and (diameters.width() > 80 or diameters.height() > 80):
            event.accept()
            return
        phase = {QEvent.Type.TouchBegin: "press", QEvent.Type.TouchUpdate: "move", QEvent.Type.TouchEnd: "release"}[event.type()]
        pressure = float(point.pressure() or 0.55)
        self.pointer_event("touch", phase, point.position().x(), point.position().y(), pressure, False)
        event.accept()

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            self.view_scale = max(0.3, min(4.0, self.view_scale * (1.1 if delta > 0 else 0.9)))
            self.update()
        else:
            super().wheelEvent(event)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        nx, ny = self.w2n(event.position().x(), event.position().y())
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls() if url.toLocalFile()]
            self.filesDropped.emit(paths, nx, ny)
        elif event.mimeData().hasText():
            self.textDropped.emit(event.mimeData().text(), nx, ny)
        event.acceptProposedAction()

    def _start_object_drag(self, object_id: str) -> None:
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData("application/x-officedisplay-object", object_id.encode("utf-8"))
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)

    def _kind_from_device(self, event) -> str:
        device = event.device() if hasattr(event, "device") else None
        if device is None:
            return "mouse"
        return device_kind_from_name(str(device.type()), "")

    def _pressure(self, event) -> float:
        try:
            return float(event.pressure())
        except Exception:
            return 1.0
