"""DTP-Hilfe: schließbarer Dialog, kein Status-No-Op / kein Stub."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QDialogButtonBox, QMenu, QTextBrowser, QToolButton

from instantlensdoc.dtp.help_dialog import DTP_HELP_HTML, DtpHelpDialog
from instantlensdoc.dtp.model import DtpDocument


def test_dtp_help_html_covers_required_topics() -> None:
    blob = DTP_HELP_HTML.lower()
    assert "noch nicht implementiert" not in blob
    assert "(geplant)" not in blob
    assert "stub" not in blob
    for needle in (
        "werkzeuge",
        "rahmen",
        "speichern",
        "nicht speichern",
        "abbrechen",
        "f1",
        "ctrl+alt+l",
        "textrahmen",
        "schriftfarbe",
    ):
        assert needle in blob, needle


def test_dtp_help_dialog_closable(qapp) -> None:
    dlg = DtpHelpDialog()
    assert dlg.objectName() == "ildDtpHelpDialog"
    assert dlg.windowTitle() == "DTP-Hilfe"
    body = dlg.findChild(QTextBrowser, "ildDtpHelpBody")
    assert body is not None
    html = body.toHtml()
    assert "Speichern" in html
    assert "Werkzeuge" in html
    box = dlg.findChild(QDialogButtonBox)
    assert box is not None
    close_btn = box.button(QDialogButtonBox.Close)
    assert close_btn is not None
    assert close_btn.text() == "Schließen"
    close_btn.click()
    qapp.processEvents()
    dlg.close()


def test_chrome_help_opens_dialog(qapp, monkeypatch) -> None:
    from instantlensdoc.dtp.canvas import DtpPane
    from instantlensdoc.dtp import help_dialog as hd

    seen: list[str] = []

    def fake_exec(self):
        seen.append(self.objectName())
        seen.append(self.windowTitle())
        return 0

    monkeypatch.setattr(hd.DtpHelpDialog, "exec", fake_exec)
    pane = DtpPane(doc=DtpDocument.sample("A5"))
    pane.show()
    qapp.processEvents()
    menu = pane.findChild(QMenu, "dtpHelpMenu")
    assert menu is not None
    labels = [(a.text() or "") for a in menu.actions() if not a.isSeparator()]
    assert any("Hilfe" in t for t in labels)
    assert not any("geplant" in t.lower() for t in labels)
    pane._chrome_help()
    assert "ildDtpHelpDialog" in seen
    assert "DTP-Hilfe" in seen
    btn = pane.findChild(QToolButton, "dtpHelpBtn")
    assert btn is not None
    assert "F1" in (btn.toolTip() or "")
    seen.clear()
    btn.click()
    qapp.processEvents()
    assert "ildDtpHelpDialog" in seen
    pane.close()
