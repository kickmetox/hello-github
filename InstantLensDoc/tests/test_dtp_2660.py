"""DTP: nutzbare Lineale, Werkzeuge, Farbe, Systemschriften — 2.6.54."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtTest import QTest

from instantlensdoc.dtp.geometry import format_unit, normalize_unit, snap_to_unit, unit_from_pt
from instantlensdoc.dtp.model import DtpDocument
from instantlensdoc.dtp.presets import apply_book_preset
from instantlensdoc.dtp.type_extras import list_system_fonts


def test_ruler_units_and_drag_guide(qapp):
    from instantlensdoc.dtp.canvas import DtpPane, GuideItem

    doc = DtpDocument()
    apply_book_preset(doc, "A4")
    doc.grid_visible = False
    pane = DtpPane(doc=doc)
    pane.resize(1100, 800)
    pane.show()
    qapp.processEvents()
    assert pane.h_ruler.unit() == "mm"
    assert pane.cycle_ruler_unit() == "pt"
    assert pane.h_ruler.unit() == "pt" and pane.v_ruler.unit() == "pt"
    assert pane.doc.ruler_unit == "pt"
    assert pane.cycle_ruler_unit() == "in"
    pane.set_ruler_unit("mm")
    assert pane._unit_corner.text() == "mm"
    n0 = len(doc.guides)
    # Klick/Release aufs Lineal erzeugt Hilfslinie (ziehen)
    QTest.mouseClick(pane.h_ruler, Qt.LeftButton, Qt.NoModifier, QPoint(pane.h_ruler.width() // 2, 8))
    qapp.processEvents()
    assert len(doc.guides) == n0 + 1
    g = doc.guides[-1]
    assert g.orientation in ("v", "vertical")
    gi = next(it for it in pane.scene.items() if isinstance(it, GuideItem) and it.guide is g)
    gi.setPos(snap_to_unit(90.0, "mm") + 40.0, 0)
    qapp.processEvents()
    assert abs(g.position_pt - snap_to_unit(90.0, "mm")) < 1.5
    pane.close()


def test_toolbar_tools_apply_to_selection(qapp):
    from instantlensdoc.dtp.canvas import DtpPane

    doc = DtpDocument()
    shape = doc.add_shape("rectangle", x=40, y=40, width=80, height=50, fill="#AABBCC")
    pane = DtpPane(doc=doc)
    pane.show()
    qapp.processEvents()
    assert pane._tool == "select"
    pane.scene._items[shape.id].setSelected(True)
    pane.set_tool("text")
    assert shape.kind == "text"
    assert abs(shape.width - 80) < 0.01 and abs(shape.x - 40) < 0.01
    assert pane._tool == "select"
    pane.scene._items[shape.id].setSelected(True)
    pane.set_tool("image")
    assert shape.kind == "image"
    pane.scene._items[shape.id].setSelected(True)
    pane.set_tool("shape")
    assert shape.kind == "shape"
    n = len(doc.frames)
    pane.scene.clearSelection()
    pane.set_tool("text")
    assert pane._tool == "text"
    assert len(doc.frames) == n  # ohne Auswahl: Aufzieh-Modus, kein Sofort-Rahmen
    pane.finish_create_frame((30, 30), (130, 90))
    assert len(doc.frames) == n + 1
    assert doc.frames[-1].kind == "text"
    assert pane._tool == "select"
    pane.close()


def test_fill_stroke_picker_on_selected_frames(qapp):
    from instantlensdoc.dtp.canvas import DtpPane

    doc = DtpDocument()
    a = doc.add_shape("rectangle", x=20, y=20, width=60, height=40)
    b = doc.add_shape("ellipse", x=100, y=20, width=50, height=40)
    pane = DtpPane(doc=doc)
    pane.show()
    qapp.processEvents()
    pane.scene._items[a.id].setSelected(True)
    hit = pane.apply_fill("#FF3300", kind="solid")
    assert hit.scope == "frames"
    assert a.fill.upper().startswith("#FF3300") or a.fill.lower() == "#ff3300"
    assert (b.fill or "") != a.fill
    pane.apply_stroke("#00AA55", width=2.0)
    assert a.stroke.upper() in ("#00AA55", "#0A5")
    assert a.stroke_width == 2.0
    pane.close()


def test_qfontdatabase_on_text_frame_and_caret(qapp):
    from PySide6.QtGui import QTextCursor

    from instantlensdoc.dtp.canvas import DtpPane

    fams = list_system_fonts()
    assert fams
    db = list(QFontDatabase.families())
    assert db
    family = db[0]
    doc = DtpDocument()
    fr = doc.add_text_frame("Hello Font", x=30, y=30, width=200, height=60)
    extra = doc.add_text_frame("Andere Story", x=30, y=120, width=200, height=40)
    pane = DtpPane(doc=doc)
    pane.show()
    qapp.processEvents()
    pane.scene._items[fr.id].setSelected(True)
    hit = pane.apply_font(family=family, size=16)
    assert hit.scope == "frames"
    assert fr.font_family == family
    assert fr.font_size == 16
    assert extra.font_family != family or extra.font_size != 16
    item = pane.scene._items[fr.id]
    item.begin_edit()
    cur = item.text_item.textCursor()
    cur.setPosition(0)
    cur.setPosition(5, QTextCursor.KeepAnchor)
    item.text_item.setTextCursor(cur)
    hit2 = pane.apply_font(family=family, bold=True, toggle=False)
    assert hit2.is_caret
    item.end_edit()
    pane.close()


def test_unit_helpers():
    assert normalize_unit("inch") == "in"
    assert "mm" in format_unit(72.0, "mm")
    assert "pt" in format_unit(72.0, "pt")
    assert abs(unit_from_pt(72.0, "in") - 1.0) < 0.001
