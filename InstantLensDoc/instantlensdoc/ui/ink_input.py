"""Touch-/Stylus-Stifteingabe auf der einheitlichen Text/PDF/DTP-Ansicht.

Finger oder Stift schreiben Tinte; Erkennung läuft über die vorhandene
Tesseract-/ScanTuxio-OCR (gleiche Sprachen). Ergebnis wird als Rich-Text
an den Caret oder als Textrahmen eingefügt — keine Steuerzeichen (¶/FF).
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from PySide6.QtCore import QEvent, QObject, QPointF, QTimer, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from instantlensdoc.core.ocr_word_suite import sanitize_ocr_html, sanitize_ocr_visible_text

INK_WIDTHS: tuple[float, ...] = (1.0, 1.5, 2.5, 3.5, 5.0, 8.0, 12.0)
DEFAULT_INK_COLOR = "#1A1A1A"
DEFAULT_INK_WIDTH = 2.5
DEFAULT_INK_TOOL = "ballpoint"
LONG_PRESS_MS = 550
TAP_SLOP_PX = 8.0
PINCH_MIN_FACTOR = 0.85
PINCH_MAX_FACTOR = 1.18
PT_PER_MM = 72.0 / 25.4
RECENT_COLOR_MAX = 8

TOOL_BALLPOINT = "ballpoint"
TOOL_FELT = "felt"
TOOL_HIGHLIGHTER = "highlighter"
TOOL_BRUSH = "brush"
INK_TOOLS: tuple[str, ...] = (TOOL_BALLPOINT, TOOL_FELT, TOOL_HIGHLIGHTER, TOOL_BRUSH)
INK_TOOL_LABELS = {
    TOOL_BALLPOINT: "Kugelschreiber",
    TOOL_FELT: "Filzstift",
    TOOL_HIGHLIGHTER: "Textmarker",
    TOOL_BRUSH: "Pinsel",
}
FILL_NONE = "none"
FILL_CLOSED = "closed"
FILL_FLOOD = "flood"
INK_FILLS: tuple[str, ...] = (FILL_NONE, FILL_CLOSED, FILL_FLOOD)
INK_FILL_LABELS = {
    FILL_NONE: "Keine Füllung",
    FILL_CLOSED: "Geschlossenen Strich füllen",
    FILL_FLOOD: "Loop-Füllung",
}


def pt_to_mm(pt: float) -> float:
    return float(pt) / PT_PER_MM


def mm_to_pt(mm: float) -> float:
    return float(mm) * PT_PER_MM


def normalize_ink_tool(name: str | None) -> str:
    key = str(name or DEFAULT_INK_TOOL).strip().lower()
    return key if key in INK_TOOL_LABELS else DEFAULT_INK_TOOL


def normalize_ink_fill(name: str | None) -> str:
    key = str(name or FILL_NONE).strip().lower()
    return key if key in INK_FILL_LABELS else FILL_NONE


def _qcolor(value: str | None, fallback: str = DEFAULT_INK_COLOR) -> QColor:
    color = QColor(value or fallback)
    if not color.isValid():
        color = QColor(fallback)
    return color


@dataclass
class InkStroke:
    points: list[tuple[float, float, float]] = field(default_factory=list)
    color: str = DEFAULT_INK_COLOR
    width: float = DEFAULT_INK_WIDTH
    tool: str = DEFAULT_INK_TOOL
    fill: str = FILL_NONE
    fill_color: str = ""
    filled: bool = False
    flood_origin: tuple[float, float] | None = None
    flood_image: object | None = None

    def add(self, x: float, y: float, pressure: float = 0.5) -> None:
        self.points.append((float(x), float(y), max(0.0, min(1.0, float(pressure)))))

    def bbox(self) -> tuple[float, float, float, float] | None:
        if not self.points:
            return None
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        pad = max(4.0, float(self.width) * 2.0)
        return min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad

    def is_closed(self, slop: float | None = None) -> bool:
        if len(self.points) < 5:
            return False
        a, b = self.points[0], self.points[-1]
        limit = float(slop if slop is not None else max(12.0, float(self.width) * 4.0))
        return math.hypot(a[0] - b[0], a[1] - b[1]) <= limit


class InkSession(QObject):
    """Gesammelte Handschrift-Striche der aktuellen Ansicht."""

    changed = Signal()
    toolChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.enabled = False
        self.color = DEFAULT_INK_COLOR
        self.width = DEFAULT_INK_WIDTH
        self.tool = DEFAULT_INK_TOOL
        self.fill_mode = FILL_NONE
        self.fill_color = ""
        self.width_unit = "pt"
        self.recent_colors: list[str] = [DEFAULT_INK_COLOR, "#C0392B", "#1A5276", "#F1C40F"]
        self.strokes: list[InkStroke] = []
        self.current: InkStroke | None = None
        self.selected: set[int] = set()
        self.fills: list[InkStroke] = []

    def set_enabled(self, on: bool) -> None:
        self.enabled = bool(on)
        if not self.enabled:
            self.current = None
        self.changed.emit()

    def set_tool(self, tool: str) -> None:
        self.tool = normalize_ink_tool(tool)
        self.toolChanged.emit()
        self.changed.emit()

    def set_fill_mode(self, mode: str) -> None:
        self.fill_mode = normalize_ink_fill(mode)
        self.toolChanged.emit()

    def set_color(self, color: str) -> None:
        q = _qcolor(color)
        self.color = q.name()
        if self.color not in self.recent_colors:
            self.recent_colors.insert(0, self.color)
            self.recent_colors = self.recent_colors[:RECENT_COLOR_MAX]
        else:
            self.recent_colors.remove(self.color)
            self.recent_colors.insert(0, self.color)
        self.changed.emit()

    def begin(self, x: float, y: float, pressure: float = 0.5) -> None:
        self.current = InkStroke(
            color=self.color,
            width=self.width,
            tool=self.tool,
            fill=self.fill_mode,
            fill_color=self.fill_color or self.color,
        )
        self.current.add(x, y, pressure)
        self.changed.emit()

    def move(self, x: float, y: float, pressure: float = 0.5) -> None:
        if self.current is None:
            return
        last = self.current.points[-1]
        if abs(x - last[0]) < 0.6 and abs(y - last[1]) < 0.6:
            return
        self.current.add(x, y, pressure)
        self.changed.emit()

    def end(self) -> InkStroke | None:
        st = self.current
        self.current = None
        if st is None:
            return None
        if len(st.points) < 2:
            self.changed.emit()
            return None
        if st.fill == FILL_CLOSED and st.is_closed():
            st.filled = True
            st.fill_color = st.fill_color or st.color
        elif st.fill == FILL_FLOOD:
            apply_loop_flood_fill(st)
        self.strokes.append(st)
        self.changed.emit()
        return st

    def cancel(self) -> None:
        self.current = None
        self.changed.emit()

    def clear(self) -> None:
        self.strokes.clear()
        self.fills.clear()
        self.current = None
        self.selected.clear()
        self.changed.emit()

    def all_for_paint(self) -> list[InkStroke]:
        out = list(self.strokes)
        if self.current is not None and self.current.points:
            out.append(self.current)
        return out

    def selected_or_last(self) -> list[InkStroke]:
        if self.selected:
            picked = [self.strokes[i] for i in sorted(self.selected) if 0 <= i < len(self.strokes)]
            if picked:
                return picked
        if self.strokes:
            return [self.strokes[-1]]
        if self.current is not None and len(self.current.points) >= 2:
            return [self.current]
        return []

    def bbox(self, strokes: Sequence[InkStroke] | None = None) -> tuple[float, float, float, float] | None:
        items = list(strokes if strokes is not None else self.selected_or_last())
        boxes = [s.bbox() for s in items if s.bbox()]
        if not boxes:
            return None
        x0 = min(b[0] for b in boxes)
        y0 = min(b[1] for b in boxes)
        x1 = max(b[2] for b in boxes)
        y1 = max(b[3] for b in boxes)
        return x0, y0, x1, y1


def synthetic_stroke_list() -> list[InkStroke]:
    """Offscreen-Testdaten: zwei Striche (kein echtes Tablet nötig)."""
    return [
        InkStroke(
            points=[
                (20.0, 40.0, 0.6),
                (28.0, 22.0, 0.7),
                (36.0, 40.0, 0.6),
                (32.0, 32.0, 0.5),
                (24.0, 32.0, 0.5),
            ],
            color=DEFAULT_INK_COLOR,
            width=3.0,
        ),
        InkStroke(
            points=[
                (48.0, 22.0, 0.5),
                (48.0, 40.0, 0.6),
                (48.0, 31.0, 0.5),
                (60.0, 31.0, 0.5),
                (60.0, 22.0, 0.5),
                (60.0, 40.0, 0.5),
            ],
            color=DEFAULT_INK_COLOR,
            width=3.0,
        ),
    ]


def accept_touch_events(widget: QWidget | None) -> None:
    if widget is None:
        return
    try:
        widget.setAttribute(Qt.WA_AcceptTouchEvents, True)
    except Exception:
        try:
            widget.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        except Exception:
            pass


def apply_loop_flood_fill(st: InkStroke) -> bool:
    """Bucket-Fill im Inneren eines Tinten-Loops (auch fast-geschlossen)."""
    from PIL import Image, ImageDraw

    if len(st.points) < 5:
        return False
    box = st.bbox()
    if box is None:
        return False
    x0, y0, x1, y1 = box
    pad = max(8.0, float(st.width) * 3.0)
    scale = 2.0
    w = max(12, int((x1 - x0 + 2 * pad) * scale))
    h = max(12, int((y1 - y0 + 2 * pad) * scale))
    img = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(img)
    pts = [
        ((p[0] - x0 + pad) * scale, (p[1] - y0 + pad) * scale) for p in st.points
    ]
    wall = max(2, int(float(st.width or DEFAULT_INK_WIDTH) * scale))
    if len(pts) == 1:
        return False
    draw.line(pts, fill=255, width=wall, joint="curve")
    if not st.is_closed(slop=max(36.0, float(st.width) * 10.0)):
        a, b = pts[0], pts[-1]
        if math.hypot(a[0] - b[0], a[1] - b[1]) <= max(48.0, wall * 6):
            draw.line([b, a], fill=255, width=wall)
        else:
            if st.is_closed():
                st.filled = True
                st.fill_color = st.fill_color or st.color
            return st.filled
    else:
        draw.line([pts[-1], pts[0]], fill=255, width=wall)
    cx = int(sum(p[0] for p in pts) / len(pts))
    cy = int(sum(p[1] for p in pts) / len(pts))
    seed = _flood_seed(img, cx, cy)
    if seed is None:
        if st.is_closed():
            st.filled = True
            st.fill_color = st.fill_color or st.color
        return st.filled
    ImageDraw.floodfill(img, seed, 128)
    n_fill = 0
    try:
        n_fill = img.histogram()[128]
    except Exception:
        n_fill = 0
    if n_fill < 8 or n_fill > (w * h) * 0.45:
        if st.is_closed():
            st.filled = True
            st.fill_color = st.fill_color or st.color
        return st.filled
    fill = _qcolor(st.fill_color or st.color)
    if normalize_ink_tool(st.tool) == TOOL_HIGHLIGHTER:
        fill.setAlpha(70)
    else:
        fill.setAlpha(140)
    rgba = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pix = rgba.load()
    src = img.load()
    r, g, b, a = fill.red(), fill.green(), fill.blue(), fill.alpha()
    for yy in range(h):
        for xx in range(w):
            if src[xx, yy] == 128:
                pix[xx, yy] = (r, g, b, a)
    from PySide6.QtGui import QImage

    qimg = QImage(rgba.tobytes("raw", "RGBA"), w, h, QImage.Format.Format_RGBA8888).copy()
    st.flood_image = qimg
    st.flood_origin = (x0 - pad, y0 - pad)
    st.filled = True
    st.fill_color = st.fill_color or st.color
    return True


def _flood_seed(img, cx: int, cy: int) -> tuple[int, int] | None:
    w, h = img.size
    cx = max(0, min(w - 1, int(cx)))
    cy = max(0, min(h - 1, int(cy)))
    pix = img.load()
    if pix[cx, cy] == 0:
        return (cx, cy)
    for rad in range(1, 24):
        for dx, dy in ((rad, 0), (-rad, 0), (0, rad), (0, -rad), (rad, rad), (-rad, rad)):
            x, y = cx + dx, cy + dy
            if 0 <= x < w and 0 <= y < h and pix[x, y] == 0:
                return (x, y)
    return None


def _stroke_pen(st: InkStroke, pressure: float = 0.55) -> QPen:
    color = _qcolor(st.color)
    tool = normalize_ink_tool(st.tool)
    width = max(0.6, float(st.width or DEFAULT_INK_WIDTH))
    if tool == TOOL_HIGHLIGHTER:
        color.setAlpha(88)
        width *= 2.4
    elif tool == TOOL_FELT:
        color.setAlpha(210)
        width *= 1.25
    elif tool == TOOL_BRUSH:
        width *= 0.35 + 1.45 * max(0.08, min(1.0, pressure))
        color.setAlpha(230)
    pen = QPen(color)
    pen.setWidthF(width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def paint_strokes(painter: QPainter, strokes: Iterable[InkStroke]) -> None:
    painter.setRenderHint(QPainter.Antialiasing, True)
    for st in strokes:
        if len(st.points) < 1:
            continue
        pts = st.points
        flood = getattr(st, "flood_image", None)
        origin = getattr(st, "flood_origin", None)
        if flood is not None and origin is not None:
            painter.drawImage(QPointF(origin[0], origin[1]), flood)
        elif st.filled and len(pts) >= 3:
            poly = QPolygonF([QPointF(p[0], p[1]) for p in pts])
            fill = _qcolor(st.fill_color or st.color)
            if normalize_ink_tool(st.tool) == TOOL_HIGHLIGHTER:
                fill.setAlpha(70)
            else:
                fill.setAlpha(140)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(fill))
            painter.drawPolygon(poly)
        painter.setBrush(Qt.NoBrush)
        if len(pts) == 1:
            painter.setPen(_stroke_pen(st, pts[0][2]))
            painter.drawPoint(QPointF(pts[0][0], pts[0][1]))
            continue
        if normalize_ink_tool(st.tool) == TOOL_BRUSH:
            for i in range(1, len(pts)):
                p0, p1 = pts[i - 1], pts[i]
                painter.setPen(_stroke_pen(st, (p0[2] + p1[2]) * 0.5))
                painter.drawLine(QPointF(p0[0], p0[1]), QPointF(p1[0], p1[1]))
            continue
        path = QPainterPath(QPointF(pts[0][0], pts[0][1]))
        for p in pts[1:]:
            path.lineTo(QPointF(p[0], p[1]))
        painter.setPen(_stroke_pen(st, 0.55))
        painter.drawPath(path)


def strokes_to_pil(strokes: Sequence[InkStroke], *, scale: int = 3):
    """Tinte auf Weiß → PIL-Bild für Tesseract. None wenn leer."""
    from PIL import Image, ImageDraw

    items = [s for s in strokes if s.points]
    if not items:
        return None
    xs = [p[0] for s in items for p in s.points]
    ys = [p[1] for s in items for p in s.points]
    pad = 24.0
    x0, y0 = min(xs) - pad, min(ys) - pad
    x1, y1 = max(xs) + pad, max(ys) + pad
    w = max(32, int((x1 - x0) * scale))
    h = max(32, int((y1 - y0) * scale))
    img = Image.new("L", (w, h), 255)
    draw = ImageDraw.Draw(img)
    for st in items:
        pts = [
            ((p[0] - x0) * scale, (p[1] - y0) * scale)
            for p in st.points
        ]
        width = max(2, int(float(st.width or DEFAULT_INK_WIDTH) * scale))
        if len(pts) == 1:
            x, y = pts[0]
            draw.ellipse((x - width, y - width, x + width, y + width), fill=0)
        else:
            draw.line(pts, fill=0, width=width, joint="curve")
    return img


def tessdata_ready() -> tuple[bool, str]:
    from instantlensdoc.core.ocr import tesseract_available

    return tesseract_available()


def ocr_lang_for_ink() -> str:
    try:
        from instantlensdoc.core.app_settings import get_ocr_lang

        return str(get_ocr_lang() or "deu+eng")
    except Exception:
        return "deu+eng"


def recognize_ink_strokes(
    strokes: Sequence[InkStroke] | Sequence[Sequence[float]],
    *,
    lang: str | None = None,
    stub: bool = False,
) -> dict:
    """OCR auf Tintenstrichen. Ohne tessdata: skipped. Nie Steuerzeichen im Text."""
    normalized: list[InkStroke] = []
    for item in strokes or []:
        if isinstance(item, InkStroke):
            if item.points:
                normalized.append(item)
            continue
        pts = []
        for p in item:
            if isinstance(p, (list, tuple)) and len(p) >= 2:
                pr = float(p[2]) if len(p) >= 3 else 0.5
                pts.append((float(p[0]), float(p[1]), pr))
        if pts:
            normalized.append(InkStroke(points=pts))
    if stub:
        return {
            "ok": True,
            "skipped": False,
            "stub": True,
            "text": "Handschrift",
            "html": recognized_text_to_html("Handschrift"),
            "lang": lang or ocr_lang_for_ink(),
        }
    if not normalized:
        return {"ok": False, "skipped": True, "reason": "empty", "text": "", "html": ""}
    ok, msg = tessdata_ready()
    if not ok:
        return {
            "ok": False,
            "skipped": True,
            "reason": "ocr_unavailable",
            "message": msg,
            "text": "",
            "html": "",
        }
    img = strokes_to_pil(normalized)
    if img is None:
        return {"ok": False, "skipped": True, "reason": "empty", "text": "", "html": ""}
    code = lang or ocr_lang_for_ink()
    try:
        from instantlensdoc.core.ocr import OcrOutputMode, OcrResult
        from instantlensdoc.core.ocr_word_suite import (
            ocr_stroke_image_to_word_suite,
            open_ocr_stroke_image,
        )

        ws = ocr_stroke_image_to_word_suite(
            img, lang=code, auto_format=False, handwriting=True
        )
        raw = getattr(ws, "text", "") or ""
        html = sanitize_ocr_html(getattr(ws, "html", "") or "")
        reused = OcrResult(
            text=str(raw or ""),
            lang=code,
            mode=OcrOutputMode.EDITABLE_TEXT,
            source_label="Handschrift-Strokes",
        )
        doc = open_ocr_stroke_image(
            img,
            lang=code,
            auto_format=False,
            handwriting=True,
            result=reused,
        )
        if not str(raw or "").strip():
            raw = getattr(doc, "text", "") or raw
            html = sanitize_ocr_html(getattr(doc, "html", "") or html)
    except Exception as exc:
        try:
            from instantlensdoc.core.ocr import ocr_image_handwriting

            raw = ocr_image_handwriting(img, lang=code)
            html = ""
        except Exception:
            return {
                "ok": False,
                "skipped": True,
                "reason": "ocr_error",
                "message": str(exc),
                "text": "",
                "html": "",
            }
    text = sanitize_ocr_visible_text(raw or "").strip()
    if not html:
        html = recognized_text_to_html(text)
    else:
        html = sanitize_ocr_html(html)
    return {
        "ok": bool(text),
        "skipped": False,
        "stub": False,
        "text": text,
        "html": html,
        "lang": code,
    }


def recognized_text_to_html(text: str) -> str:
    """Sichtbarer Rich-Text ohne ¶ / Form-Feed."""
    from html import escape as html_escape

    clean = sanitize_ocr_visible_text(text or "").strip()
    if not clean:
        return ""
    paras = [p.strip() for p in clean.split("\n\n") if p.strip()]
    if not paras:
        paras = [ln.strip() for ln in clean.split("\n") if ln.strip()] or [clean]
    chunks: list[str] = []
    for para in paras:
        inner = html_escape(para, quote=False).replace("\n", "<br/>")
        chunks.append(
            '<p style="margin:0 0 8pt 0; font-family:Calibri,Calibri; font-size:11pt;">'
            f"{inner}</p>"
        )
    return sanitize_ocr_html("".join(chunks))


def is_schreibschutz(window) -> bool:
    """Schreibschutz: Editor read-only oder PDF-Annotationen gesperrt (Sibling-Policy)."""
    try:
        ed = getattr(window, "editor", None)
        if ed is not None and bool(ed.isReadOnly()):
            return True
    except Exception:
        pass
    try:
        if callable(getattr(window, "_pdf_tab_active", None)) and window._pdf_tab_active():
            pdf = getattr(window, "pdf_view", None)
            if pdf is not None and bool(getattr(pdf, "annotations_locked", lambda: False)()):
                return True
    except Exception:
        pass
    return False


def _pointer_xy(event) -> tuple[float, float] | None:
    try:
        if hasattr(event, "position"):
            p = event.position()
            return float(p.x()), float(p.y())
    except Exception:
        pass
    try:
        p = event.pos()
        return float(p.x()), float(p.y())
    except Exception:
        return None


def _touch_points(event) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    seq = None
    for name in ("points", "touchPoints"):
        getter = getattr(event, name, None)
        if callable(getter):
            try:
                seq = getter()
                break
            except Exception:
                seq = None
    if not seq:
        return pts
    for tp in seq:
        try:
            pos = tp.position() if hasattr(tp, "position") else tp.pos()
            pts.append((float(pos.x()), float(pos.y())))
        except Exception:
            continue
    return pts


class InkGlass(QWidget):
    """Transparente Tinten-Glasplatte über Editor/PDF/DTP — fängt keine Maus."""

    def __init__(self, host: QWidget, session: InkSession):
        super().__init__(host)
        self._session = session
        self.setObjectName("ildInkGlass")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.NoFocus)
        self.setAttribute(Qt.WA_AcceptTouchEvents, False)
        self.resize(host.size())
        self.show()
        self.raise_()
        session.changed.connect(self.update)
        host.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is self.parent() and event.type() == QEvent.Type.Resize:
            self.resize(obj.size())
            self.raise_()
        return False

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        if painter.isActive():
            paint_strokes(painter, self._session.all_for_paint())
            painter.end()


class TouchInkFilter(QObject):
    """Maus, Touch und Tablet zeichnen dieselben Tintenwerkzeuge.

    Linksziehen (Maus) = Finger/Stift: begin/move/end auf derselben Session.
    Bei ausgeschalteter Stifteingabe: Events durchreichen (Auswahl/Caret bleiben).
    Zwei Finger: Pinch-Zoom (auch ohne Stiftmodus).
    """

    def __init__(self, session: InkSession, window, parent=None):
        super().__init__(parent)
        self.session = session
        self.window = window
        self._press = None  # (x, y)
        self._moved = False
        self._pinching = False
        self._pinch_dist = 0.0
        self._long_timer = QTimer(self)
        self._long_timer.setSingleShot(True)
        self._long_timer.timeout.connect(self._fire_long_press)
        self._long_pos: tuple[float, float] | None = None
        self._long_widget: QWidget | None = None
        self._tablet_active = False
        self._last_ptr: tuple[float, float, float] | None = None
        self._mouse_draw = False
        self._hosts: list[QWidget] = []

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if not isinstance(obj, QWidget):
            return False
        et = event.type()
        try:
            if et in (
                QEvent.Type.TouchBegin,
                QEvent.Type.TouchUpdate,
                QEvent.Type.TouchEnd,
                QEvent.Type.TouchCancel,
            ):
                return self._on_touch(obj, event)
            if et in (
                QEvent.Type.TabletPress,
                QEvent.Type.TabletMove,
                QEvent.Type.TabletRelease,
            ):
                return self._on_tablet(obj, event)
            if et == QEvent.Type.MouseButtonPress:
                return self._on_mouse_press(obj, event)
            if et == QEvent.Type.MouseMove:
                return self._on_mouse_move(obj, event)
            if et == QEvent.Type.MouseButtonRelease:
                return self._on_mouse_release(obj, event)
        except Exception:
            return False
        return False

    def _blocked(self) -> bool:
        return is_schreibschutz(self.window)

    def _ink_on(self) -> bool:
        return bool(self.session.enabled) and not self._blocked()

    def _dynamic_pressure(self, x: float, y: float, event=None) -> float:
        """Tablet-Druck, sonst Breite aus Zeigergeschwindigkeit (Maus = Stift)."""
        if event is not None:
            try:
                if event.type() in (
                    QEvent.Type.TabletPress,
                    QEvent.Type.TabletMove,
                    QEvent.Type.TabletRelease,
                ):
                    p = float(event.pressure())
                    if p > 0.02:
                        self._last_ptr = (time.monotonic(), x, y)
                        return max(0.08, min(1.0, p))
            except Exception:
                pass
        now = time.monotonic()
        last = self._last_ptr
        self._last_ptr = (now, x, y)
        if last is None:
            return 0.55
        dt = max(1e-3, now - last[0])
        speed = math.hypot(x - last[1], y - last[2]) / dt
        t = max(0.0, min(1.0, speed / 900.0))
        return max(0.15, min(1.0, 1.0 - 0.7 * t))

    def _on_touch(self, obj: QWidget, event) -> bool:
        pts = _touch_points(event)
        et = event.type()
        if len(pts) >= 2:
            self._long_timer.stop()
            if self.session.current is not None:
                self.session.cancel()
            self._handle_pinch(obj, pts, begin=(et == QEvent.Type.TouchBegin))
            event.accept()
            return True
        if not self._ink_on():
            if et == QEvent.Type.TouchBegin and pts:
                self._arm_long_press(obj, pts[0][0], pts[0][1])
            elif et == QEvent.Type.TouchEnd and pts and not self._moved:
                self._long_timer.stop()
                self._place_caret(obj, pts[0][0], pts[0][1])
            elif et in (QEvent.Type.TouchEnd, QEvent.Type.TouchCancel):
                self._long_timer.stop()
            return False
        if not pts:
            if et in (QEvent.Type.TouchEnd, QEvent.Type.TouchCancel):
                self.session.end()
                self._long_timer.stop()
            event.accept()
            return True
        x, y = pts[0]
        if et == QEvent.Type.TouchBegin:
            self._press = (x, y)
            self._moved = False
            self._last_ptr = None
            self._arm_long_press(obj, x, y)
            self.session.begin(x, y, self._dynamic_pressure(x, y, event))
            event.accept()
            return True
        if et == QEvent.Type.TouchUpdate:
            if self._press and (
                abs(x - self._press[0]) > TAP_SLOP_PX or abs(y - self._press[1]) > TAP_SLOP_PX
            ):
                self._moved = True
                self._long_timer.stop()
            self.session.move(x, y, self._dynamic_pressure(x, y, event))
            event.accept()
            return True
        if et in (QEvent.Type.TouchEnd, QEvent.Type.TouchCancel):
            self._long_timer.stop()
            if not self._moved:
                self.session.cancel()
                self._place_caret(obj, x, y)
            else:
                self.session.end()
            self._press = None
            self._moved = False
            event.accept()
            return True
        return False

    def _on_tablet(self, obj: QWidget, event) -> bool:
        if not self._ink_on():
            return False
        xy = _pointer_xy(event)
        if xy is None:
            return False
        x, y = xy
        pressure = self._dynamic_pressure(x, y, event)
        t = event.type()
        if t == QEvent.Type.TabletPress:
            self._tablet_active = True
            self._press = (x, y)
            self._moved = False
            self.session.begin(x, y, pressure)
            event.accept()
            return True
        if t == QEvent.Type.TabletMove and self._tablet_active:
            if self._press and (
                abs(x - self._press[0]) > TAP_SLOP_PX or abs(y - self._press[1]) > TAP_SLOP_PX
            ):
                self._moved = True
            self.session.move(x, y, pressure)
            event.accept()
            return True
        if t == QEvent.Type.TabletRelease and self._tablet_active:
            if not self._moved:
                self.session.cancel()
                self._place_caret(obj, x, y)
            else:
                self.session.end()
            self._tablet_active = False
            self._press = None
            self._moved = False
            event.accept()
            return True
        return False

    def _on_mouse_press(self, obj: QWidget, event) -> bool:
        # Synthetisierte Maus vom aktiven Stift nicht verdoppeln; echte Maus bleibt vollwertig.
        if self._tablet_active:
            event.accept()
            return True
        if not self._ink_on():
            if event.button() == Qt.RightButton:
                return False
            xy = _pointer_xy(event)
            if xy:
                self._arm_long_press(obj, xy[0], xy[1])
            return False
        if event.button() != Qt.LeftButton:
            return False
        xy = _pointer_xy(event)
        if xy is None:
            return False
        x, y = xy
        self._press = (x, y)
        self._moved = False
        self._mouse_draw = True
        self._last_ptr = None
        self._arm_long_press(obj, x, y)
        self.session.begin(x, y, self._dynamic_pressure(x, y, event))
        event.accept()
        return True

    def _on_mouse_move(self, obj: QWidget, event) -> bool:
        xy = _pointer_xy(event)
        if xy and self._press:
            if abs(xy[0] - self._press[0]) > TAP_SLOP_PX or abs(xy[1] - self._press[1]) > TAP_SLOP_PX:
                self._moved = True
                self._long_timer.stop()
        drawing = self._ink_on() and (self._mouse_draw or self.session.current is not None)
        if not drawing:
            return False
        if xy is None:
            return False
        self.session.move(xy[0], xy[1], self._dynamic_pressure(xy[0], xy[1], event))
        event.accept()
        return True

    def _on_mouse_release(self, obj: QWidget, event) -> bool:
        self._long_timer.stop()
        drawing = self._mouse_draw or (self._ink_on() and self.session.current is not None)
        if not drawing:
            xy = _pointer_xy(event)
            if xy and not self._moved and event.button() == Qt.LeftButton:
                self._place_caret(obj, xy[0], xy[1])
            self._press = None
            self._moved = False
            self._mouse_draw = False
            return False
        if event.button() != Qt.LeftButton:
            return False
        xy = _pointer_xy(event) or self._press or (0.0, 0.0)
        if not self._moved:
            self.session.cancel()
            self._place_caret(obj, xy[0], xy[1])
        else:
            self.session.end()
        self._press = None
        self._moved = False
        self._mouse_draw = False
        event.accept()
        return True

    def _arm_long_press(self, widget: QWidget, x: float, y: float) -> None:
        self._long_widget = widget
        self._long_pos = (x, y)
        self._long_timer.start(LONG_PRESS_MS)

    def _fire_long_press(self) -> None:
        w = self._long_widget
        pos = self._long_pos
        self._long_widget = None
        self._long_pos = None
        if w is None or pos is None or self._moved:
            return
        if self.session.current is not None:
            self.session.cancel()
        try:
            from PySide6.QtCore import QPoint
            from PySide6.QtGui import QContextMenuEvent

            gp = w.mapToGlobal(QPoint(int(pos[0]), int(pos[1])))
            ev = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(int(pos[0]), int(pos[1])), gp)
            from PySide6.QtWidgets import QApplication

            QApplication.sendEvent(w, ev)
        except Exception:
            try:
                w.customContextMenuRequested.emit(
                    w.mapFromGlobal(w.mapToGlobal(w.rect().center()))
                )
            except Exception:
                pass

    def _place_caret(self, widget: QWidget, x: float, y: float) -> None:
        win = self.window
        try:
            from PySide6.QtCore import QPoint
            from PySide6.QtGui import QTextCursor

            ed = getattr(win, "editor", None)
            vp = ed.viewport() if ed is not None else None
            if ed is not None and (widget is ed or widget is vp):
                cur = ed.cursorForPosition(QPoint(int(x), int(y)))
                ed.setTextCursor(cur)
                ed.setFocus(Qt.OtherFocusReason)
                return
        except Exception:
            pass
        try:
            pane = getattr(win, "dtp_pane", None)
            view = getattr(pane, "view", None) if pane is not None else None
            if pane is not None and view is not None and (
                widget is view or widget is getattr(view, "viewport", lambda: None)()
            ):
                item = pane.editing_item() if hasattr(pane, "editing_item") else None
                if item is not None and getattr(item, "text_item", None) is not None:
                    from PySide6.QtCore import QPoint

                    sp = view.mapToScene(QPoint(int(x), int(y)))
                    lp = item.text_item.mapFromScene(sp)
                    cur = item.text_item.cursorForPosition(lp.toPoint())
                    item.text_item.setTextCursor(cur)
                    item.text_item.setFocus(Qt.OtherFocusReason)
        except Exception:
            pass

    def _handle_pinch(self, widget: QWidget, pts: list[tuple[float, float]], *, begin: bool) -> None:
        if len(pts) < 2:
            self._pinching = False
            return
        dx = pts[0][0] - pts[1][0]
        dy = pts[0][1] - pts[1][1]
        dist = max(1.0, (dx * dx + dy * dy) ** 0.5)
        if begin or not self._pinching or self._pinch_dist <= 1.0:
            self._pinching = True
            self._pinch_dist = dist
            return
        factor = dist / self._pinch_dist
        if factor < PINCH_MIN_FACTOR or factor > PINCH_MAX_FACTOR:
            apply_pinch_zoom(self.window, widget, factor)
            self._pinch_dist = dist


def apply_pinch_zoom(window, widget: QWidget, factor: float) -> None:
    fac = max(0.7, min(1.4, float(factor)))
    try:
        pdf = getattr(window, "pdf_view", None)
        canvas = getattr(pdf, "canvas", None) if pdf is not None else None
        if pdf is not None and (
            widget is canvas or widget is pdf or (canvas is not None and widget.parent() is canvas)
        ):
            if hasattr(pdf, "set_scale"):
                base = float(getattr(pdf, "_pending_scale", None) or getattr(pdf, "scale", 1.0) or 1.0)
                pdf.set_scale(max(0.25, min(6.0, base * fac)), immediate=True)
            return
    except Exception:
        pass
    try:
        pane = getattr(window, "dtp_pane", None)
        view = getattr(pane, "view", None) if pane is not None else None
        if pane is not None and view is not None and (
            widget is view or widget is view.viewport()
        ):
            pane.set_zoom(max(25.0, min(400.0, float(getattr(pane, "_zoom", 100.0)) * fac)))
            return
    except Exception:
        pass
    try:
        ed = getattr(window, "editor", None)
        if ed is not None and (widget is ed or widget is ed.viewport()):
            f = ed.font()
            size = float(f.pointSizeF() or f.pointSize() or 11.0)
            size = max(7.0, min(36.0, size * fac))
            f.setPointSizeF(size)
            ed.setFont(f)
    except Exception:
        pass


def install_ink_input(window) -> InkSession:
    """Maus, Touch und Tablet auf Editor-, PDF- und DTP-Fläche; Glasplatte für Tinte."""
    session = InkSession(window)
    filt = TouchInkFilter(session, window, window)
    glasses: list[InkGlass] = []
    hosts: list[QWidget] = []
    ed = getattr(window, "editor", None)
    if ed is not None:
        hosts.append(ed.viewport())
        accept_touch_events(ed)
        accept_touch_events(ed.viewport())
    pdf = getattr(window, "pdf_view", None)
    canvas = getattr(pdf, "canvas", None) if pdf is not None else None
    if canvas is not None:
        hosts.append(canvas)
        accept_touch_events(canvas)
    pane = getattr(window, "dtp_pane", None)
    view = getattr(pane, "view", None) if pane is not None else None
    if view is not None:
        hosts.append(view.viewport() if hasattr(view, "viewport") else view)
        accept_touch_events(view)
        try:
            accept_touch_events(view.viewport())
        except Exception:
            pass
    filt._hosts = [h for h in hosts if h is not None]
    for host in filt._hosts:
        host.installEventFilter(filt)
        try:
            host.setMouseTracking(True)
        except Exception:
            pass
        glasses.append(InkGlass(host, session))
    window._ink_session = session
    window._ink_filter = filt
    window._ink_glasses = glasses
    window._ink_hosts = list(filt._hosts)
    return session


def insert_recognized_text(window, html: str, plain: str, bbox=None) -> str:
    """Caret-Rich-Text (Editor) oder Textrahmen (DTP/PDF). Rückgabe: Zielname."""
    html = sanitize_ocr_html(html or "")
    plain = sanitize_ocr_visible_text(plain or "").strip()
    if not html and plain:
        html = recognized_text_to_html(plain)
    if not plain and not html:
        return ""
    try:
        if callable(getattr(window, "_layout_mode_active", None)) and window._layout_mode_active():
            return _insert_dtp_frame(window, plain, html, bbox)
    except Exception:
        pass
    try:
        if callable(getattr(window, "_pdf_tab_active", None)) and window._pdf_tab_active():
            return _insert_pdf_overlay(window, plain, bbox)
    except Exception:
        pass
    ed = getattr(window, "editor", None)
    if ed is None:
        return ""
    try:
        ed._ensure_rich_mode()
    except Exception:
        pass
    from PySide6.QtGui import QTextCursor

    cur = ed.textCursor()
    cur.beginEditBlock()
    try:
        if html:
            cur.insertHtml(html)
        else:
            cur.insertText(plain)
    finally:
        cur.endEditBlock()
    ed.setTextCursor(cur)
    try:
        if callable(getattr(window, "_sync_editor_rich_meta", None)):
            window._sync_editor_rich_meta()
        if callable(getattr(window, "_sync_editor_only_actions", None)):
            window._sync_editor_only_actions()
    except Exception:
        pass
    return "caret"


def _insert_dtp_frame(window, plain: str, html: str, bbox) -> str:
    pane = getattr(window, "dtp_pane", None)
    if pane is None or getattr(pane, "doc", None) is None:
        return ""
    x = y = 40.0
    w, h = 220.0, 64.0
    if bbox and len(bbox) == 4:
        x, y = float(bbox[0]), float(bbox[1])
        w = max(80.0, float(bbox[2] - bbox[0]))
        h = max(36.0, float(bbox[3] - bbox[1]))
    editing = pane.editing_item() if hasattr(pane, "editing_item") else None
    if editing is not None and getattr(editing, "text_item", None) is not None:
        cur = editing.text_item.textCursor()
        if html:
            cur.insertHtml(html)
        else:
            cur.insertText(plain)
        editing.text_item.setTextCursor(cur)
        if hasattr(editing, "commit_rich"):
            editing.commit_rich()
        return "caret"
    fr = pane.doc.add_text_frame(plain, x=x, y=y, width=w, height=h, page=pane.doc.current_page)
    if html:
        try:
            fr.rich_html = html
            fr.text = plain
        except Exception:
            pass
    pane.scene.rebuild()
    try:
        if callable(getattr(window, "_sync_editor_only_actions", None)):
            window._sync_editor_only_actions()
    except Exception:
        pass
    return "frame"


def _insert_pdf_overlay(window, plain: str, bbox) -> str:
    from ild_pdf.annotate import Annotation, AnnotationType

    pdf = getattr(window, "pdf_view", None)
    if pdf is None or getattr(pdf, "store", None) is None:
        return ""
    x = y = 36.0
    w, h = 200.0, 36.0
    if bbox and len(bbox) == 4:
        x, y = float(bbox[0]), float(bbox[1])
        w = max(40.0, float(bbox[2] - bbox[0]))
        h = max(18.0, float(bbox[3] - bbox[1]))
    page = int(getattr(pdf, "current_page", 0) or 0)
    ann = Annotation(
        page=page,
        type=AnnotationType.TEXT_OVERLAY,
        x=x,
        y=y,
        width=w,
        height=h,
        text=plain,
        color="#1A5276",
        font_size=14.0,
    )
    if hasattr(pdf, "_commit_ann"):
        pdf._commit_ann(ann)
    else:
        pdf.store.add(ann)
        if hasattr(pdf, "refresh"):
            pdf.refresh()
    try:
        if callable(getattr(window, "_sync_editor_only_actions", None)):
            window._sync_editor_only_actions()
    except Exception:
        pass
    return "frame"


STAMP_TAG_NO_FRAME = "ild-stamp-no-frame"
STAMP_TAG_TEXT_ONLY = "ild-stamp-text-only"
STAMP_TAG_SHADOW = "ild-stamp-shadow"
STAMP_TAG_OUTLINE = "ild-stamp-outline"
STAMP_TOOL_LABELS = {
    "place": "Stempel setzen",
    "frame": "Rahmen ein/aus",
    "color": "Stempelfarbe",
    "text_only": "Nur Text",
    "shadow": "Schatten",
    "outline": "Kontur",
    "edit": "Stempel bearbeiten",
}
STAMP_TOOLS: tuple[str, ...] = tuple(STAMP_TOOL_LABELS)


def _stamp_tag_list(ann) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in getattr(ann, "tags", None) or []:
        tag = str(raw).strip()
        if not tag:
            continue
        key = tag.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(tag)
    return out


def _stamp_has_tag(tags: Sequence[str], tag: str) -> bool:
    needle = str(tag).casefold()
    return any(str(item).casefold() == needle for item in tags)


def _stamp_set_tag(tags: Sequence[str], tag: str, on: bool) -> list[str]:
    needle = str(tag).casefold()
    out = [item for item in tags if str(item).casefold() != needle]
    if on:
        out.append(str(tag))
    return out


def stamp_paint_flags(ann) -> dict:
    """Rahmen/Farbe/Nur-Text/Schatten/Kontur aus Tags, bool-Feldern und Strichstärke."""
    tags = _stamp_tag_list(ann)
    text_only = _stamp_has_tag(tags, STAMP_TAG_TEXT_ONLY) or bool(
        getattr(ann, "stamp_text_only", False)
    )
    no_frame = (
        _stamp_has_tag(tags, STAMP_TAG_NO_FRAME)
        or text_only
        or (hasattr(ann, "stamp_frame") and not bool(getattr(ann, "stamp_frame", True)))
    )
    try:
        if float(getattr(ann, "stroke_width", 1.0) or 0.0) < 0.5:
            no_frame = True
    except (TypeError, ValueError):
        pass
    shadow = _stamp_has_tag(tags, STAMP_TAG_SHADOW) or bool(getattr(ann, "stamp_shadow", False))
    outline = (
        _stamp_has_tag(tags, STAMP_TAG_OUTLINE) or bool(getattr(ann, "stamp_outline", False))
    ) and not text_only
    frame = (not no_frame) or outline
    if text_only:
        frame = False
        outline = False
    color = str(getattr(ann, "color", "") or "").strip() or "#C0392B"
    if color.upper() == "#FFFF00":
        color = "#C0392B"
    try:
        sw = float(getattr(ann, "stroke_width", 0) or 0)
    except (TypeError, ValueError):
        sw = 0.0
    if frame or outline:
        sw = max(2.0, sw if sw >= 0.5 else (5.0 if outline else 3.0))
    return {
        "frame": bool(frame),
        "text_only": bool(text_only),
        "shadow": bool(shadow),
        "outline": bool(outline),
        "color": color,
        "pen_width": sw if (frame or outline) else 0.0,
    }


def _sync_optional_stamp_attrs(ann, flags: dict) -> None:
    mapping = {
        "stamp_frame": flags.get("frame"),
        "stamp_text_only": flags.get("text_only"),
        "stamp_shadow": flags.get("shadow"),
        "stamp_outline": flags.get("outline"),
    }
    for name, value in mapping.items():
        if hasattr(ann, name):
            try:
                setattr(ann, name, bool(value))
            except Exception:
                pass


def apply_stamp_style_to_annotation(ann, kind: str, *, color: str | None = None) -> dict:
    """Stempelstil über vorhandene Felder (color/tags/fill_color). Kein neues Stempel-Objekt."""
    key = str(kind or "").strip().lower()
    tags = _stamp_tag_list(ann)
    flags = stamp_paint_flags(ann)
    if key == "color":
        hexc = str(color or "").strip()
        if hexc:
            if not hexc.startswith("#"):
                hexc = "#" + hexc
            ann.color = hexc.upper()
    elif key == "frame":
        on = not flags["frame"]
        tags = _stamp_set_tag(tags, STAMP_TAG_NO_FRAME, not on)
        if on:
            tags = _stamp_set_tag(tags, STAMP_TAG_TEXT_ONLY, False)
            if hasattr(ann, "stamp_text_only"):
                ann.stamp_text_only = False
        else:
            tags = _stamp_set_tag(tags, STAMP_TAG_OUTLINE, False)
            if hasattr(ann, "stamp_outline"):
                ann.stamp_outline = False
        if hasattr(ann, "stamp_frame"):
            ann.stamp_frame = on
        if hasattr(ann, "stroke_width"):
            ann.stroke_width = 3.0 if on else 0.0
    elif key == "text_only":
        on = not flags["text_only"]
        tags = _stamp_set_tag(tags, STAMP_TAG_TEXT_ONLY, on)
        tags = _stamp_set_tag(tags, STAMP_TAG_NO_FRAME, on)
        if hasattr(ann, "stamp_text_only"):
            ann.stamp_text_only = on
        if hasattr(ann, "stamp_frame"):
            ann.stamp_frame = not on
        if hasattr(ann, "stroke_width"):
            ann.stroke_width = 0.0 if on else 3.0
        if on:
            tags = _stamp_set_tag(tags, STAMP_TAG_OUTLINE, False)
            try:
                ann.fill_color = ""
            except Exception:
                pass
    elif key == "shadow":
        on = not flags["shadow"]
        tags = _stamp_set_tag(tags, STAMP_TAG_SHADOW, on)
        if hasattr(ann, "stamp_shadow"):
            ann.stamp_shadow = on
    elif key == "outline":
        on = not flags["outline"]
        tags = _stamp_set_tag(tags, STAMP_TAG_OUTLINE, on)
        if hasattr(ann, "stamp_outline"):
            ann.stamp_outline = on
        if on:
            tags = _stamp_set_tag(tags, STAMP_TAG_NO_FRAME, False)
            tags = _stamp_set_tag(tags, STAMP_TAG_TEXT_ONLY, False)
            if hasattr(ann, "stamp_text_only"):
                ann.stamp_text_only = False
            if hasattr(ann, "stamp_frame"):
                ann.stamp_frame = True
            if hasattr(ann, "stroke_width"):
                try:
                    cur = float(getattr(ann, "stroke_width", 0) or 0)
                except (TypeError, ValueError):
                    cur = 0.0
                ann.stroke_width = max(2.0, cur or 2.0)
    try:
        ann.tags = tags
    except Exception:
        pass
    flags = stamp_paint_flags(ann)
    _sync_optional_stamp_attrs(ann, flags)
    sw = 0.0 if flags["text_only"] or not flags["frame"] else float(flags["pen_width"] or 3.0)
    if flags["outline"] and sw < 2.0:
        sw = 2.0
    if hasattr(ann, "stroke_width"):
        try:
            ann.stroke_width = sw
        except Exception:
            pass
    if hasattr(ann, "touch"):
        try:
            ann.touch()
        except Exception:
            pass
    return {
        "color": getattr(ann, "color", None),
        "fill_color": getattr(ann, "fill_color", ""),
        "tags": list(getattr(ann, "tags", None) or []),
        "stroke_width": sw,
        "stamp_frame": bool(flags["frame"]),
        "stamp_text_only": bool(flags["text_only"]),
        "stamp_shadow": bool(flags["shadow"]),
        "stamp_outline": bool(flags["outline"]),
    }
