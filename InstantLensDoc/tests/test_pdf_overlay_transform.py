"""PDF-Overlays/Formen: Auswahl, Verschieben, 8 Griffe, Stempel-Edit, Gummiband.

DTP-Rahmen bleiben ein eigener Canvas (ResizeHandle an FrameItem) — dieser Test
fasst nur ild_pdf/pdf_view an und prüft, dass der DTP-Pfad unberührt bleibt.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["ILD_SMOKE_QT"] = "1"
os.environ.setdefault("ILD_SKIP_DEPS_CHECK", "1")
os.environ.setdefault("ILD_NO_SESSION", "1")
os.environ.setdefault("ILD_NO_SPLASH", "1")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from menu_smoke_lib import make_n_page_pdf  # noqa: E402


def _pump(app, seconds: float = 0.3, until=None) -> None:
    t0 = time.time()
    while time.time() - t0 < seconds:
        app.processEvents()
        if until is not None and until():
            return
        time.sleep(0.01)


def _canvas_page_to_widget(canvas, vx: float, vy: float) -> tuple[float, float]:
    pw, ph = canvas._pixmap_logical_size()
    cr = canvas.contentsRect()
    lx = float(cr.x()) + (float(cr.width()) - pw) / 2.0
    ly = float(cr.y()) + (float(cr.height()) - ph) / 2.0
    return float(vx) + lx, float(vy) + ly


def _qclick(canvas, x: float, y: float) -> None:
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest

    QTest.mouseClick(
        canvas,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        QPoint(int(round(x)), int(round(y))),
    )


def _qdrag(canvas, x0: float, y0: float, x1: float, y1: float) -> None:
    from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    p0 = QPoint(int(round(x0)), int(round(y0)))
    p1 = QPoint(int(round(x1)), int(round(y1)))
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p0)
    app = QApplication.instance()
    steps = 8
    for i in range(1, steps + 1):
        t = i / float(steps)
        p = QPoint(
            int(round(p0.x() + (p1.x() - p0.x()) * t)),
            int(round(p0.y() + (p1.y() - p0.y()) * t)),
        )
        local = QPointF(float(p.x()), float(p.y()))
        try:
            ev = QMouseEvent(
                QEvent.Type.MouseMove,
                local,
                Qt.MouseButton.NoButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )
        except TypeError:
            ev = QMouseEvent(
                QEvent.Type.MouseMove,
                local,
                local,
                local,
                Qt.MouseButton.NoButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )
        QApplication.sendEvent(canvas, ev)
        if app is not None:
            app.processEvents()
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p1)


def _qdouble(canvas, x: float, y: float) -> None:
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest

    QTest.mouseDClick(
        canvas,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        QPoint(int(round(x)), int(round(y))),
    )


@pytest.fixture
def viewer(qapp, tmp_path: Path):
    from instantlensdoc.ui.pdf_view import PdfViewer

    pdf = tmp_path / "overlay.pdf"
    make_n_page_pdf(pdf, 3)
    v = PdfViewer()
    v.resize(960, 720)
    v.show()
    qapp.processEvents()
    assert v.load(pdf), f"load fehlgeschlagen: {v._last_refresh_error!r}"
    v.set_annotations_locked(False)
    v._suppress_default_zoom = True
    _pump(qapp, 1.5, until=lambda: v._canvas_has_page_image())
    v.set_scale(1.5, immediate=True)
    _pump(qapp, 0.4)
    v.set_tool(None)
    assert v.canvas._select_mode
    yield v
    v.close()


def _add(v, **kwargs):
    from ild_pdf import Annotation
    from PySide6.QtWidgets import QApplication

    ann = Annotation(page=0, **kwargs)
    v.store.add(ann)
    v.refresh()
    app = QApplication.instance()
    if app is not None:
        _pump(app, 0.15)
    return v.store.get(ann.id) or ann


def _center_widget(v, ann) -> tuple[float, float]:
    s = v._view_scale()
    cx = (ann.x + ann.width / 2.0) * s
    cy = (ann.y + ann.height / 2.0) * s
    return _canvas_page_to_widget(v.canvas, cx, cy)


def test_apply_handle_resize_eight_roles(qapp):
    from ild_pdf import Annotation, AnnotationType
    from instantlensdoc.ui.pdf_view import PdfCanvas

    start = (40.0, 50.0, 80.0, 40.0)
    br = PdfCanvas._apply_handle_resize(start, "br", 160.0, 120.0)
    assert br[2] > 80.0 and br[3] > 40.0
    tl = PdfCanvas._apply_handle_resize(start, "tl", 20.0, 30.0)
    assert tl[0] < 40.0 and tl[1] < 50.0
    r = PdfCanvas._apply_handle_resize(start, "r", 200.0, 70.0)
    assert abs(r[3] - 40.0) < 0.01 and r[2] > 80.0
    canvas = PdfCanvas()
    ann = Annotation(
        page=0, type=AnnotationType.RECTANGLE, x=10.0, y=10.0, width=40.0, height=20.0
    )
    rects = canvas._ann_handle_rects(ann)
    assert set(rects) == {"tl", "t", "tr", "r", "br", "b", "bl", "l"}
    dummy_cursors = {
        h: PdfCanvas._cursor_for_ann_handle(h)
        for h in ("tl", "t", "tr", "r", "br", "b", "bl", "l")
    }
    assert len(dummy_cursors) == 8
    from ild_pdf import Annotation, AnnotationType
    from instantlensdoc.ui.pdf_view import PdfCanvas

    start = (40.0, 50.0, 80.0, 40.0)
    br = PdfCanvas._apply_handle_resize(start, "br", 160.0, 120.0)
    assert br[2] > 80.0 and br[3] > 40.0
    tl = PdfCanvas._apply_handle_resize(start, "tl", 20.0, 30.0)
    assert tl[0] < 40.0 and tl[1] < 50.0
    r = PdfCanvas._apply_handle_resize(start, "r", 200.0, 70.0)
    assert abs(r[3] - 40.0) < 0.01 and r[2] > 80.0
    canvas = PdfCanvas()
    ann = Annotation(
        page=0, type=AnnotationType.RECTANGLE, x=10.0, y=10.0, width=40.0, height=20.0
    )
    rects = canvas._ann_handle_rects(ann)
    assert set(rects) == {"tl", "t", "tr", "r", "br", "b", "bl", "l"}
    dummy_cursors = {
        h: PdfCanvas._cursor_for_ann_handle(h)
        for h in ("tl", "t", "tr", "r", "br", "b", "bl", "l")
    }
    assert len(dummy_cursors) == 8


def test_select_overlay_and_shape_shows_eight_handles(qapp, viewer):
    from ild_pdf import AnnotationType
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or qapp
    overlay = _add(
        viewer,
        type=AnnotationType.TEXT_OVERLAY,
        x=70.0,
        y=80.0,
        width=140.0,
        height=36.0,
        text="Hallo Overlay",
        color="#1A5276",
    )
    shape = _add(
        viewer,
        type=AnnotationType.RECTANGLE,
        x=240.0,
        y=160.0,
        width=90.0,
        height=50.0,
        color="#2980B9",
    )
    wx, wy = _center_widget(viewer, overlay)
    _qclick(viewer.canvas, wx, wy)
    _pump(app, 0.12)
    assert overlay.id in viewer.canvas._selected_ids
    handles = viewer.canvas.selected_handle_rects()
    assert len(handles) == 8, handles
    wx, wy = _center_widget(viewer, shape)
    _qclick(viewer.canvas, wx, wy)
    _pump(app, 0.12)
    assert shape.id in viewer.canvas._selected_ids
    assert len(viewer.canvas.selected_handle_rects()) == 8


def test_drag_move_overlay_and_shape(qapp, viewer):
    from ild_pdf import AnnotationType
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or qapp
    overlay = _add(
        viewer,
        type=AnnotationType.TEXT_OVERLAY,
        x=60.0,
        y=70.0,
        width=120.0,
        height=32.0,
        text="Move me",
        color="#1A5276",
    )
    shape = _add(
        viewer,
        type=AnnotationType.ELLIPSE,
        x=220.0,
        y=180.0,
        width=70.0,
        height=40.0,
        color="#8E44AD",
    )
    for ann in (overlay, shape):
        before = (viewer.store.get(ann.id).x, viewer.store.get(ann.id).y)
        wx, wy = _center_widget(viewer, viewer.store.get(ann.id))
        _qdrag(viewer.canvas, wx, wy, wx + 48.0, wy + 24.0)
        _pump(app, 0.2)
        after = (viewer.store.get(ann.id).x, viewer.store.get(ann.id).y)
        assert after[0] > before[0] + 5.0, (ann.type, before, after)
        assert after[1] > before[1] + 2.0, (ann.type, before, after)


def test_resize_handles_change_bounds(qapp, viewer):
    from ild_pdf import AnnotationType
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or qapp
    overlay = _add(
        viewer,
        type=AnnotationType.TEXT_OVERLAY,
        x=80.0,
        y=90.0,
        width=100.0,
        height=40.0,
        text="Resize",
        color="#1A5276",
    )
    wx, wy = _center_widget(viewer, overlay)
    _qclick(viewer.canvas, wx, wy)
    _pump(app, 0.12)
    handles = viewer.canvas.selected_handle_rects()
    assert "br" in handles
    hx, hy, hw, hh = handles["br"]
    x0, y0 = _canvas_page_to_widget(viewer.canvas, hx + hw / 2.0, hy + hh / 2.0)
    before = (viewer.store.get(overlay.id).width, viewer.store.get(overlay.id).height)
    _qdrag(viewer.canvas, x0, y0, x0 + 40.0, y0 + 30.0)
    _pump(app, 0.2)
    after = (viewer.store.get(overlay.id).width, viewer.store.get(overlay.id).height)
    assert after[0] > before[0] + 4.0, (before, after)
    assert after[1] > before[1] + 2.0, (before, after)


def test_rubber_band_on_empty_selects_intersecting(qapp, viewer):
    from ild_pdf import AnnotationType
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or qapp
    a = _add(
        viewer,
        type=AnnotationType.TEXT_OVERLAY,
        x=80.0,
        y=90.0,
        width=110.0,
        height=36.0,
        text="A",
        color="#1A5276",
    )
    b = _add(
        viewer,
        type=AnnotationType.STAMP,
        x=250.0,
        y=200.0,
        width=70.0,
        height=36.0,
        text="OK",
        color="#1E8449",
    )
    s = viewer._view_scale()
    x0, y0 = _canvas_page_to_widget(viewer.canvas, 20.0 * s, 20.0 * s)
    x1, y1 = _canvas_page_to_widget(viewer.canvas, 360.0 * s, 270.0 * s)
    _qdrag(viewer.canvas, x0, y0, x1, y1)
    _pump(app, 0.2)
    assert a.id in viewer.canvas._selected_ids and b.id in viewer.canvas._selected_ids, (
        viewer.canvas._selected_ids
    )
    ex, ey = _canvas_page_to_widget(viewer.canvas, 16.0 * s, 16.0 * s)
    _qclick(viewer.canvas, ex, ey)
    _pump(app, 0.1)
    assert not viewer.canvas._selected_ids


def test_edit_text_stamp_and_overlay_dialog(qapp, viewer, monkeypatch):
    from ild_pdf import AnnotationType
    from instantlensdoc.ui.pdf_view import TextOverlayEditDialog
    from PySide6.QtWidgets import QApplication, QDialog

    app = QApplication.instance() or qapp
    overlay = _add(
        viewer,
        type=AnnotationType.TEXT_OVERLAY,
        x=70.0,
        y=80.0,
        width=130.0,
        height=34.0,
        text="Alt Overlay",
        color="#1A5276",
    )
    stamp = _add(
        viewer,
        type=AnnotationType.STAMP,
        x=230.0,
        y=170.0,
        width=80.0,
        height=36.0,
        text="Alt Stempel",
        color="#1E8449",
    )

    def _accept(self):
        self.text.setPlainText("GEÄNDERT")
        return QDialog.Accepted

    monkeypatch.setattr(TextOverlayEditDialog, "exec", _accept)
    for ann in (overlay, stamp):
        wx, wy = _center_widget(viewer, viewer.store.get(ann.id))
        _qdouble(viewer.canvas, wx, wy)
        _pump(app, 0.2)
        got = viewer.store.get(ann.id)
        assert got is not None and got.text == "GEÄNDERT", (ann.type, getattr(got, "text", None))


def test_dtp_sibling_resize_handles_untouched(qapp):
    """PDF-Canvas-Änderungen dürfen DTP-Rahmengriffe nicht anfassen."""
    from instantlensdoc.dtp.canvas import DtpPane, ResizeHandle
    from instantlensdoc.dtp.model import DtpDocument

    doc = DtpDocument()
    shape = doc.add_shape("rectangle", x=40, y=40, width=80, height=50, fill="#AABBCC")
    pane = DtpPane(doc=doc)
    pane.resize(900, 700)
    pane.show()
    qapp.processEvents()
    item = pane.scene._items[shape.id]
    item.setSelected(True)
    qapp.processEvents()
    handles = [h for h in item.childItems() if isinstance(h, ResizeHandle)]
    assert len(handles) == 8
    roles = {h.role for h in handles}
    assert roles == set(ResizeHandle.ROLES)
    w0, h0 = float(shape.width), float(shape.height)
    geom = (shape.x, shape.y, shape.width, shape.height)
    item.resize_from("br", 20.0, 10.0, geom)
    qapp.processEvents()
    assert shape.width > w0 + 5.0
    assert shape.height > h0 + 3.0
    pane.close()
