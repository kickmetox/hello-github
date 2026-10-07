"""Text-bearbeiten-Dialog: ein Klick schließt (OK/Abbrechen/Esc), deutsche Buttons."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["ILD_SMOKE_QT"] = "1"
os.environ.setdefault("ILD_SKIP_DEPS_CHECK", "1")
os.environ.setdefault("ILD_NO_SPLASH", "1")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QDialog, QDialogButtonBox  # noqa: E402

from ild_pdf.text_edit import (  # noqa: E402
    TextStyle,
    sanitize_font_family_label,
    sanitize_pdf_edit_text,
)
from instantlensdoc.ui.pdf_view import InlineTextEditDialog, PdfCanvas  # noqa: E402


def test_sanitize_pdf_edit_text_strips_controls_and_mojibake() -> None:
    assert "\x00" not in sanitize_pdf_edit_text("A\x00B")
    assert sanitize_pdf_edit_text("CafÃ©") == "Café"
    assert sanitize_font_family_label("Calibri-0-400") == "Calibri"
    assert sanitize_font_family_label("ABCDEF+Calibri") == "Calibri"


def test_inline_text_edit_dialog_buttons_german_and_close(qapp) -> None:
    style = TextStyle(font_family="Calibri-0-400", font_size=11, color="#000000")
    dlg = InlineTextEditDialog("A\x00B CafÃ©", style, None, title="Text bearbeiten")
    dlg.show()
    qapp.processEvents()
    box = dlg.findChild(QDialogButtonBox, "inlineTextEditButtons")
    assert box is not None
    ok = box.button(QDialogButtonBox.Ok)
    cancel = box.button(QDialogButtonBox.Cancel)
    assert ok is not None and ok.text() == "OK"
    assert cancel is not None and cancel.text() == "Abbrechen"
    assert "\x00" not in dlg.text.toPlainText()
    assert "Café" in dlg.text.toPlainText()
    cancel.click()
    qapp.processEvents()
    assert dlg.result() == QDialog.Rejected
    dlg.deleteLater()


def test_inline_text_edit_esc_and_ok(qapp) -> None:
    dlg = InlineTextEditDialog("Hallo", TextStyle(), None)
    dlg.show()
    qapp.processEvents()
    QTest.keyClick(dlg, Qt.Key_Escape)
    qapp.processEvents()
    assert dlg.result() == QDialog.Rejected

    dlg2 = InlineTextEditDialog("Hallo", TextStyle(), None)
    dlg2.show()
    qapp.processEvents()
    box = dlg2.findChild(QDialogButtonBox, "inlineTextEditButtons")
    box.button(QDialogButtonBox.Ok).click()
    qapp.processEvents()
    assert dlg2.result() == QDialog.Accepted
    dlg2.deleteLater()


def test_inline_dialog_closes_while_canvas_grabbed(qapp) -> None:
    canvas = PdfCanvas()
    canvas.resize(400, 300)
    canvas.show()
    qapp.processEvents()
    canvas.grabMouse()
    dlg = InlineTextEditDialog("x", TextStyle(), canvas, title="Text bearbeiten")
    canvas.release_pointer_grab()
    dlg.show()
    qapp.processEvents()
    box = dlg.findChild(QDialogButtonBox, "inlineTextEditButtons")
    box.button(QDialogButtonBox.Cancel).click()
    qapp.processEvents()
    assert dlg.result() == QDialog.Rejected
    canvas.close()
    dlg.deleteLater()
