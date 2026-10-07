"""DTP-Schriftfarbe: QColorDialog auf Textauswahl oder Textrahmen, nicht Füllung."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["ILD_SMOKE_QT"] = "1"

from PySide6.QtGui import QAction, QColor, QTextCursor
from PySide6.QtWidgets import QLabel, QToolButton

from instantlensdoc.dtp.canvas import DtpPane
from instantlensdoc.dtp.model import DtpDocument


def _fg_hex(item) -> str:
    cur = QTextCursor(item.text_item.document())
    cur.select(QTextCursor.Document)
    return cur.charFormat().foreground().color().name().lower()


def test_chrome_has_schriftfarbe_action(qapp) -> None:
    pane = DtpPane(doc=DtpDocument.sample("A5"))
    pane.show()
    qapp.processEvents()
    act = pane.findChild(QAction, "dtpFontColorAction")
    assert act is not None
    assert "Schriftfarbe" in (act.text() or "")
    assert "QColorDialog" in (act.toolTip() or "")
    btn = pane.findChild(QToolButton, "dtpFontColorBtn")
    assert btn is not None
    chip = pane.findChild(QLabel, "dtpGlyphChip")
    assert chip is not None
    pane.close()


def test_font_color_on_selected_frame_not_fill(qapp) -> None:
    doc = DtpDocument()
    fr = doc.add_text_frame("DTP Rahmen Text", x=20, y=20, width=180, height=50)
    fr.fill = "#D0E8FF"
    pane = DtpPane(doc=doc)
    pane.show()
    qapp.processEvents()
    pane.scene.clearSelection()
    pane.scene._items[fr.id].setSelected(True)
    hit = pane.apply_font_color("#cc3300", dialog=False)
    assert hit.scope != "cancelled"
    assert fr.fill == "#D0E8FF"
    item = pane.scene._items[fr.id]
    html = ((fr.rich_html or "") + item.text_item.toHtml()).lower()
    assert "#cc3300" in html or "rgb(204, 51, 0)" in html
    assert _fg_hex(item) == "#cc3300" or "#cc3300" in html
    assert pane.is_dirty()
    pane.close()


def test_font_color_on_caret_selection(qapp) -> None:
    doc = DtpDocument()
    fr = doc.add_text_frame("ABCDEFGH", x=20, y=20, width=180, height=50)
    pane = DtpPane(doc=doc)
    pane.show()
    qapp.processEvents()
    item = pane.scene._items[fr.id]
    item.begin_edit()
    cur = item.text_item.textCursor()
    cur.setPosition(0)
    cur.setPosition(3, QTextCursor.KeepAnchor)
    item.text_item.setTextCursor(cur)
    hit = pane.apply_font_color("#007700", dialog=False)
    assert hit.scope == "caret_selection"
    html = item.text_item.toHtml().lower()
    assert "#007700" in html or "rgb(0, 119, 0)" in html
    assert pane.is_dirty()
    pane.close()


def test_font_color_dialog_smoke_title(qapp, monkeypatch) -> None:
    seen: list[str] = []

    def fake_get_color(initial, parent, title=""):
        seen.append(str(title))
        return QColor()

    from PySide6.QtWidgets import QColorDialog

    monkeypatch.setattr(QColorDialog, "getColor", fake_get_color)
    pane = DtpPane(doc=DtpDocument.sample("A5"))
    pane.show()
    qapp.processEvents()
    fr = pane.doc.text_frames()[0]
    pane.scene._items[fr.id].setSelected(True)
    pane.apply_font_color(dialog=True)
    assert seen and seen[0] == "Schriftfarbe"
    pane.close()
