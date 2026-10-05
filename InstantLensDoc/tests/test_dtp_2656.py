"""DTP Select-then-tool: Rahmen, Story, Caret/Absatz — 2.6.54."""

from __future__ import annotations

from instantlensdoc.dtp.model import DtpDocument
from instantlensdoc.dtp.targeting import story_or_all_text


def test_selected_frame_gets_fill_stroke_wrap_style(qapp):
    from instantlensdoc.dtp.canvas import DtpPane

    doc = DtpDocument()
    shape = doc.add_shape("rectangle", x=20, y=20, width=80, height=40)
    other = doc.add_shape("ellipse", x=120, y=20, width=50, height=40)
    text = doc.add_text_frame("Hallo Welt", x=20, y=80, width=160, height=40)
    pane = DtpPane(doc=doc)
    pane.resize(900, 700)
    pane.show()
    qapp.processEvents()
    pane.scene._items[shape.id].setSelected(True)
    hit = pane.apply_fill("#FF0000", kind="solid")
    assert hit.scope == "frames"
    assert shape.id in hit.ids
    assert other.id not in hit.ids
    assert shape.fill.upper().startswith("#FF0000") or shape.fill.lower() == "#ff0000"
    assert (other.fill or "") != shape.fill
    pane.scene.clearSelection()
    pane.scene._items[shape.id].setSelected(True)
    pane.apply_stroke("#00AA00", width=2.5)
    assert shape.stroke.upper() in ("#00AA00", "#0A0")
    assert shape.stroke_width == 2.5
    pane.scene.clearSelection()
    pane.scene._items[shape.id].setSelected(True)
    pane.apply_wrap_mode("bounding_box")
    assert shape.wrap == "bounding_box"
    pane.scene.clearSelection()
    pane.scene._items[text.id].setSelected(True)
    pane.apply_style_tool("h1")
    assert text.style_id == "h1"
    assert text.font_size >= 14
    pane.close()


def test_no_selection_applies_font_to_story_or_all_text(qapp):
    from instantlensdoc.dtp.canvas import DtpPane

    doc = DtpDocument()
    a = doc.add_text_frame("Eins", x=20, y=20, width=100, height=40)
    b = doc.add_text_frame("Zwei", x=20, y=80, width=100, height=40)
    doc.link_frames(a.id, b.id)
    extra = doc.add_text_frame("Ausserhalb", x=20, y=140, width=100, height=40)
    doc.set_active_story(a)
    pane = DtpPane(doc=doc)
    pane.show()
    qapp.processEvents()
    pane.scene.clearSelection()
    hit = pane.apply_font(family="serif", size=17)
    assert hit.scope in ("story", "all_text")
    assert a.font_size == 17
    assert b.font_size == 17
    if hit.scope == "story":
        assert extra.id not in hit.ids
        assert extra.font_size != 17
    pane.scene.clearSelection()
    doc.active_story_id = ""
    hit2 = pane.apply_font(family="serif", size=13)
    assert extra.font_size == 13
    assert hit2.scope == "all_text"
    pane.close()


def test_caret_selection_and_paragraph_char_format(qapp):
    from PySide6.QtGui import QTextCursor

    from instantlensdoc.dtp.canvas import DtpPane

    doc = DtpDocument()
    fr = doc.add_text_frame("Alpha Beta\nGamma Delta", x=30, y=30, width=220, height=90)
    pane = DtpPane(doc=doc)
    pane.show()
    qapp.processEvents()
    item = pane.scene._items[fr.id]
    item.begin_edit()
    cur = item.text_item.textCursor()
    cur.setPosition(0)
    cur.setPosition(5, QTextCursor.KeepAnchor)  # "Alpha"
    item.text_item.setTextCursor(cur)
    hit = pane.apply_font(bold=True, toggle=False)
    assert hit.is_caret
    assert hit.scope == "caret_selection"
    html = fr.rich_html or item.text_item.toHtml()
    assert "Alpha" in (item.text_item.toPlainText())
    assert "font-weight" in html.lower() or "bold" in html.lower()
    # kein Selection → aktueller Absatz
    cur2 = item.text_item.textCursor()
    cur2.clearSelection()
    cur2.setPosition(len("Alpha Beta\nG"))
    item.text_item.setTextCursor(cur2)
    hit2 = pane.apply_font(italic=True, toggle=False)
    assert hit2.scope == "caret_paragraph"
    item.end_edit()
    pane.close()


def test_story_or_all_text_helper():
    doc = DtpDocument()
    a = doc.add_text_frame("A")
    b = doc.add_text_frame("B")
    doc.link_frames(a.id, b.id)
    extra = doc.add_text_frame("C")
    doc.set_active_story(a)
    story = story_or_all_text(doc)
    ids = {f.id for f in story}
    assert a.id in ids and b.id in ids
    assert extra.id not in ids
    doc.active_story_id = ""
    all_t = story_or_all_text(doc)
    assert {f.id for f in all_t} >= {a.id, b.id, extra.id}
