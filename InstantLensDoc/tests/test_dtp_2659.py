"""Scribus-Chrome: Menü, Icon-Leiste, mm-Lineale, Anschnitt/Satzspiegel — 2.6.54."""

from __future__ import annotations

from PySide6.QtGui import QColor

from instantlensdoc.dtp.canvas import DtpPane
from instantlensdoc.dtp.chrome import BLEED_RED, MARGIN_BLUE, MENU_TITLES, PASTEBOARD
from instantlensdoc.dtp.model import DtpDocument
from instantlensdoc.dtp.presets import apply_book_preset


def test_scribus_menu_and_icon_bar(qapp):
    doc = DtpDocument()
    apply_book_preset(doc, "A4")
    doc.grid_visible = False
    pane = DtpPane(doc=doc)
    pane.resize(1100, 800)
    pane.show()
    qapp.processEvents()
    titles = [a.text().replace("&", "") for a in pane.menu_bar.actions() if a.text()]
    assert titles == list(MENU_TITLES)
    assert pane.icon_bar.objectName() == "dtpIconBar"
    assert pane.icon_bar.height() <= 36
    assert pane.status_bar.objectName() == "dtpStatusBar"
    assert "100" in pane._zoom_label.text()
    assert "von" in pane._page_label.text()
    assert not pane.side_panel.isVisible()
    pane.close()


def test_bleed_red_margin_blue_pasteboard(qapp):
    doc = DtpDocument()
    apply_book_preset(doc, "A4")
    doc.grid_visible = False
    pane = DtpPane(doc=doc)
    pane.show()
    qapp.processEvents()
    bleed = pane.scene.bleed_item
    margin = pane.scene.margin_item
    assert bleed.pen().color().name().upper() == QColor(BLEED_RED).name().upper()
    assert margin.pen().color().name().upper() == QColor(MARGIN_BLUE).name().upper()
    bg = pane.view.backgroundBrush().color().name().upper()
    assert bg == QColor(PASTEBOARD).name().upper()
    pane.set_zoom(125)
    assert abs(pane._zoom - 125) < 0.01
    assert "125" in pane._zoom_label.text()
    pane.close()


def test_rulers_are_mm_and_select_then_tool_still_works(qapp):
    from instantlensdoc.dtp.canvas import DtpPane as Pane

    doc = DtpDocument()
    shape = doc.add_shape("rectangle", x=40, y=40, width=60, height=40)
    pane = Pane(doc=doc)
    pane.show()
    qapp.processEvents()
    assert pane.h_ruler.objectName() == "dtpHRuler"
    assert pane.v_ruler.objectName() == "dtpVRuler"
    pane.scene._items[shape.id].setSelected(True)
    pane.apply_fill("#FF0000")
    assert shape.fill.upper().startswith("#FF0000") or shape.fill.lower() == "#ff0000"
    pane.close()
