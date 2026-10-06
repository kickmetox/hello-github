"""Overlays/Formen/Stempel: wählen, verschieben, Größe, editieren; Schreibschutz; Undo."""

from __future__ import annotations

import os
import sys
from pathlib import Path

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
from test_pdf_overlay_transform import (  # noqa: E402
    _add,
    _center_widget,
    _pump,
    _qclick,
    _qdrag,
)


def test_stamp_style_persist_and_undo():
    from ild_pdf import (
        Annotation,
        AnnotationStore,
        AnnotationType,
        stamp_style_fields,
        toggle_stamp_style,
    )

    store = AnnotationStore()
    ann = Annotation(
        page=0,
        type=AnnotationType.STAMP,
        x=12.0,
        y=18.0,
        width=90.0,
        height=36.0,
        text="GENEHMIGT",
        color="#1E8449",
        stroke_width=3.0,
    )
    store.add(ann)
    clone = Annotation.from_dict(ann.to_dict())
    toggle_stamp_style(clone, "frame")
    assert clone.stamp_frame is False
    assert clone.stroke_width == 0.0
    store.update(ann.id, **stamp_style_fields(clone))
    got = store.get(ann.id)
    assert got is not None
    assert got.stroke_width == 0.0
    assert got.stamp_frame is False
    roundtrip = Annotation.from_dict(got.to_dict())
    assert roundtrip.stroke_width == 0.0
    assert roundtrip.stamp_frame is False
    toggle_stamp_style(clone, "text_only")
    assert clone.stamp_text_only is True
    toggle_stamp_style(clone, "shadow")
    assert clone.stamp_shadow is True
    assert "ild-stamp-shadow" in (clone.tags or [])
    toggle_stamp_style(clone, "outline")
    assert clone.stamp_outline is True
    store.update(ann.id, **stamp_style_fields(clone))
    assert store.undo()
    mid = store.get(ann.id)
    assert mid is not None
    assert mid.stamp_frame is False
    assert store.undo()
    restored = store.get(ann.id)
    assert restored is not None
    assert restored.stamp_frame is True
    assert restored.stroke_width >= 1.0


def test_fillable_shapes_select_and_handles(qapp, tmp_path: Path):
    from ild_pdf import AnnotationType
    from instantlensdoc.ui.pdf_view import PdfViewer
    from PySide6.QtWidgets import QApplication

    pdf = tmp_path / "shapes.pdf"
    make_n_page_pdf(pdf, 1)
    v = PdfViewer()
    v.resize(960, 720)
    v.show()
    qapp.processEvents()
    assert v.load(pdf)
    v.set_annotations_locked(False)
    v._suppress_default_zoom = True
    _pump(qapp, 1.2, until=lambda: v._canvas_has_page_image())
    v.set_scale(1.5, immediate=True)
    _pump(qapp, 0.3)
    v.set_tool(None)
    app = QApplication.instance() or qapp
    kinds = (
        AnnotationType.ELLIPSE,
        AnnotationType.TRIANGLE,
        AnnotationType.ROUNDED_RECT,
        AnnotationType.STAMP,
        AnnotationType.TEXT_OVERLAY,
    )
    y = 50.0
    for kind in kinds:
        ann = _add(
            v,
            type=kind,
            x=80.0,
            y=y,
            width=110.0,
            height=48.0,
            text="OK" if kind in (AnnotationType.STAMP, AnnotationType.TEXT_OVERLAY) else "",
            color="#2980B9",
        )
        wx, wy = _center_widget(v, v.store.get(ann.id) or ann)
        _qclick(v.canvas, wx, wy)
        _pump(app, 0.12)
        assert ann.id in v.canvas._selected_ids, (kind, v.canvas._selected_ids)
        assert len(v.canvas.selected_handle_rects()) == 8, kind
        y += 70.0
    v.close()


def test_schreibschutz_blocks_overlay_move(qapp, tmp_path: Path):
    from ild_pdf import AnnotationType
    from instantlensdoc.ui.pdf_view import PdfViewer
    from PySide6.QtWidgets import QApplication

    pdf = tmp_path / "lock.pdf"
    make_n_page_pdf(pdf, 1)
    v = PdfViewer()
    v.resize(800, 600)
    v.show()
    qapp.processEvents()
    assert v.load(pdf)
    v.set_annotations_locked(False)
    v._suppress_default_zoom = True
    _pump(qapp, 1.2, until=lambda: v._canvas_has_page_image())
    v.set_scale(1.5, immediate=True)
    _pump(qapp, 0.3)
    v.set_tool(None)
    app = QApplication.instance() or qapp
    shape = _add(
        v,
        type=AnnotationType.RECTANGLE,
        x=80.0,
        y=90.0,
        width=80.0,
        height=44.0,
        color="#1A5276",
    )
    v.set_annotations_locked(True)
    before = (v.store.get(shape.id).x, v.store.get(shape.id).y)
    wx, wy = _center_widget(v, v.store.get(shape.id))
    _qdrag(v.canvas, wx, wy, wx + 50.0, wy + 30.0)
    _pump(app, 0.2)
    after = (v.store.get(shape.id).x, v.store.get(shape.id).y)
    assert after == before
    v.close()


def test_dtp_stamp_shape_move_resize_undo_lock(qapp):
    from instantlensdoc.dtp.canvas import DtpPane, ResizeHandle
    from instantlensdoc.dtp.model import DtpDocument
    from PySide6.QtWidgets import QGraphicsItem, QGraphicsView

    doc = DtpDocument()
    doc.grid_snap = False
    doc.grid_visible = False
    stamp = doc.add_stamp("GENEHMIGT", x=50, y=60, width=120, height=40)
    shape = doc.add_shape("ellipse", x=200, y=80, width=90, height=50, fill="#AABBCC")
    text = doc.add_text_frame("Hallo", x=40, y=160, width=160, height=48)
    image = doc.add_image_frame(x=220, y=170, width=100, height=70)
    pane = DtpPane(doc=doc)
    pane.resize(1000, 760)
    pane.show()
    qapp.processEvents()
    assert pane.view.dragMode() == QGraphicsView.RubberBandDrag

    for fr in (stamp, shape, text, image):
        item = pane.scene._items[fr.id]
        item.setSelected(True)
        qapp.processEvents()
        handles = [h for h in item.childItems() if isinstance(h, ResizeHandle)]
        assert len(handles) == 8, fr.kind
        item.setSelected(False)

    item = pane.scene._items[stamp.id]
    item.setSelected(True)
    w0, h0 = float(stamp.width), float(stamp.height)
    geom = (stamp.x, stamp.y, stamp.width, stamp.height)
    item.resize_from("br", 24.0, 12.0, geom)
    pane.end_gesture()
    qapp.processEvents()
    assert stamp.width > w0 + 8.0
    assert stamp.height > h0 + 4.0
    assert pane.can_undo()
    assert pane.undo()
    restored = pane.doc.frame_by_id(stamp.id)
    assert restored is not None
    assert abs(restored.width - w0) < 0.2
    assert pane.can_redo()
    assert pane.redo()
    grown = pane.doc.frame_by_id(stamp.id)
    assert grown is not None and grown.width > w0 + 8.0

    item = pane.scene._items[stamp.id]
    item.setSelected(True)
    qapp.processEvents()
    assert pane.apply_stamp_style("frame")
    fr = pane.doc.frame_by_id(stamp.id)
    assert fr is not None and fr.stroke_width == 0.0
    pane.apply_stamp_style("shadow")
    fr = pane.doc.frame_by_id(stamp.id)
    assert fr is not None and fr.shadow is True
    pane.apply_stamp_style("outline")
    fr = pane.doc.frame_by_id(stamp.id)
    assert fr is not None and fr.stamp_outline is True

    pane.set_schreibschutz(True)
    assert pane.view.dragMode() == QGraphicsView.NoDrag
    item = pane.scene._items[stamp.id]
    assert item.is_locked()
    assert not bool(item.flags() & QGraphicsItem.ItemIsMovable)
    w_lock = float(item.frame.width)
    item.resize_from("br", 40.0, 20.0, (item.frame.x, item.frame.y, item.frame.width, item.frame.height))
    assert abs(item.frame.width - w_lock) < 0.01
    item.begin_edit()
    assert item._editing is False
    pane.set_schreibschutz(False)
    assert pane.view.dragMode() == QGraphicsView.RubberBandDrag
    pane.close()


def test_dtp_group_ctrl_click_and_ungroup(qapp):
    from instantlensdoc.dtp.canvas import DtpPane
    from instantlensdoc.dtp.model import DtpDocument
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QGraphicsView

    doc = DtpDocument()
    doc.grid_snap = False
    a = doc.add_shape("rectangle", x=40, y=40, width=70, height=40, fill="#AABBCC")
    b = doc.add_shape("ellipse", x=180, y=90, width=60, height=45, fill="#88AACC")
    c = doc.add_text_frame("C", x=40, y=160, width=90, height=36)
    pane = DtpPane(doc=doc)
    pane.resize(900, 700)
    pane.show()
    qapp.processEvents()
    pane.set_tool("select", apply=False)
    assert pane.view.dragMode() == QGraphicsView.RubberBandDrag

    msgs: list[str] = []
    pane.statusMessage.connect(msgs.append)
    assert pane.group_selected() == 0
    assert any("Mindestens zwei Objekte markieren (Strg+Klick)" in m for m in msgs)

    def _click(item, mods=Qt.KeyboardModifier.NoModifier):
        center = item.sceneBoundingRect().center()
        vp = pane.view.mapFromScene(center)
        QTest.mouseClick(pane.view.viewport(), Qt.MouseButton.LeftButton, mods, vp)
        qapp.processEvents()

    _click(pane.scene._items[a.id])
    sel = {f.id for f in pane.scene.selected_frames()}
    assert a.id in sel
    _click(pane.scene._items[b.id], Qt.KeyboardModifier.ControlModifier)
    sel = {f.id for f in pane.scene.selected_frames()}
    assert a.id in sel and b.id in sel, sel
    n = pane.group_selected()
    assert n >= 2
    ga = doc.frame_by_id(a.id).group_id
    gb = doc.frame_by_id(b.id).group_id
    assert ga and ga == gb
    assert DtpDocument.from_dict(doc.to_dict()).frame_by_id(a.id).group_id == ga

    pane.scene.clearSelection()
    qapp.processEvents()
    pane.scene._items[a.id].setSelected(True)
    pane.scene.apply_group_selection(a, additive=False)
    sel = {f.id for f in pane.scene.selected_frames()}
    assert a.id in sel and b.id in sel
    assert c.id not in sel

    n_ug = pane.ungroup_selected()
    assert n_ug >= 2
    assert doc.frame_by_id(a.id).group_id == ""
    assert doc.frame_by_id(b.id).group_id == ""
    pane.close()


def test_dtp_group_model_and_main_window_routing():
    from instantlensdoc.dtp.model import DtpDocument

    doc = DtpDocument()
    a = doc.add_shape("rectangle", x=10, y=10, width=20, height=10)
    b = doc.add_shape("ellipse", x=40, y=10, width=20, height=10)
    n, gid = doc.group_frames([a.id])
    assert n == 0 and gid == ""
    n, gid = doc.group_frames([a.id, b.id])
    assert n == 2 and gid
    assert a.group_id == b.group_id == gid
    assert doc.expand_group_ids([a.id]) == [a.id, b.id] or set(doc.expand_group_ids([a.id])) == {a.id, b.id}
    assert doc.ungroup_frames([a.id]) == 2
    assert a.group_id == "" and b.group_id == ""

    mw = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
    cv = (ROOT / "instantlensdoc" / "dtp" / "canvas.py").read_text(encoding="utf-8")
    pv = (ROOT / "instantlensdoc" / "ui" / "pdf_view.py").read_text(encoding="utf-8")
    tip = "Mindestens zwei Objekte markieren (Strg+Klick)"
    assert tip in mw and tip in cv and tip in pv
    fn = mw.split("def _group_selected_annotations", 1)[1][:1800]
    assert "_ensure_pdf_target" not in fn
    assert "group_selected()" in fn
    assert "_layout_mode_active" in fn


def test_dtp_stamp_paint_frameless(qapp):
    from instantlensdoc.dtp.export import paint_frame_local
    from instantlensdoc.dtp.model import DtpDocument
    from PySide6.QtGui import QImage, QPainter

    doc = DtpDocument()
    fr = doc.add_stamp("OK", x=0, y=0, width=80, height=30)
    fr.stamp_text_only = True
    fr.stroke_width = 0.0
    img = QImage(120, 60, QImage.Format_ARGB32)
    img.fill(0)
    p = QPainter(img)
    paint_frame_local(p, doc, fr)
    p.end()
    assert not img.isNull()
