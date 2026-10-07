"""DTP 2.6.55: Menü/Toolbar auf Auswahl, Story oder Caret."""

from __future__ import annotations

from instantlensdoc.dtp.model import DtpDocument


def test_typography_and_hyphenate_respect_selection(qapp):
    from instantlensdoc.dtp.canvas import DtpPane

    doc = DtpDocument()
    a = doc.add_text_frame("Hallo Welt", x=20, y=20, width=160, height=40)
    b = doc.add_text_frame("Unangetastet", x=20, y=80, width=160, height=40)
    pane = DtpPane(doc=doc)
    pane.show()
    qapp.processEvents()
    pane.scene._items[a.id].setSelected(True)
    hit = pane.apply_typography(tracking=25.0, leading=1.5)
    assert hit.scope == "frames"
    assert a.id in hit.ids and b.id not in hit.ids
    assert "ild-typo" in (a.text or "")
    assert "ild-typo" not in (b.text or "")
    pane.scene.clearSelection()
    pane.scene._items[a.id].setSelected(True)
    pane.hyphenate("de")
    # Auswahl bleibt Ziel; der andere Rahmen unverändert
    assert "ild-typo" not in (b.text or "")
    pane.close()


def test_drop_cap_on_caret_paragraph(qapp):
    from PySide6.QtGui import QTextCursor

    from instantlensdoc.dtp.canvas import DtpPane

    doc = DtpDocument()
    fr = doc.add_text_frame("Absatz eins.\nAbsatz zwei.", x=20, y=20, width=200, height=80)
    pane = DtpPane(doc=doc)
    pane.show()
    qapp.processEvents()
    item = pane.scene._items[fr.id]
    item.begin_edit()
    cur = item.text_item.textCursor()
    cur.setPosition(0)
    item.text_item.setTextCursor(cur)
    hit = pane.apply_drop_cap(lines=3, chars=1)
    assert hit.is_caret
    blob = (fr.rich_html or "") + (fr.text or "") + item.text_item.toPlainText()
    assert "dropcap" in blob.lower() or "ild-dropcap" in blob
    item.end_edit()
    pane.close()


def test_scale_only_selected_object(qapp):
    from instantlensdoc.dtp.canvas import DtpPane

    doc = DtpDocument()
    s = doc.add_shape("rectangle", x=10, y=10, width=40, height=20)
    t = doc.add_shape("ellipse", x=80, y=10, width=40, height=20)
    pane = DtpPane(doc=doc)
    pane.show()
    qapp.processEvents()
    pane.scene._items[s.id].setSelected(True)
    orig_t = t.width
    pane.scale_selected(2.0)
    assert abs(s.width - 80) < 0.5
    assert abs(t.width - orig_t) < 0.5
    pane.close()


def test_no_selection_font_hits_all_text(qapp):
    from instantlensdoc.dtp.canvas import DtpPane

    doc = DtpDocument()
    a = doc.add_text_frame("A", x=10, y=10, width=80, height=30)
    b = doc.add_text_frame("B", x=10, y=50, width=80, height=30)
    pane = DtpPane(doc=doc)
    pane.show()
    qapp.processEvents()
    pane.scene.clearSelection()
    doc.active_story_id = ""
    hit = pane.apply_font(size=15)
    assert hit.scope == "all_text"
    assert a.font_size == 15 and b.font_size == 15
    pane.close()
