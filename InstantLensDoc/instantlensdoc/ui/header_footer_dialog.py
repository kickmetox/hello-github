"""Dialog: Kopf- und Fußzeile des Word-Suite-Dokuments (kein Body-Glyph)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)


class HeaderFooterDialog(QDialog):
    """Kopf-/Fußzeile als Dokument-Meta — nicht als ¶/Form-Feed im Fließtext."""

    def __init__(
        self,
        header: str = "",
        footer: str = "",
        parent=None,
        *,
        focus_band: str | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("headerFooterDialog")
        self.setWindowTitle("Kopf- und Fußzeile")
        self.setModal(True)
        self.resize(460, 180)

        root = QVBoxLayout(self)
        form = QFormLayout()
        self.header_edit = QLineEdit()
        self.header_edit.setObjectName("docHeaderEdit")
        self.header_edit.setText(header or "")
        self.header_edit.setPlaceholderText("Kopfzeile (nicht im Fließtext)")
        self.footer_edit = QLineEdit()
        self.footer_edit.setObjectName("docFooterEdit")
        self.footer_edit.setText(footer or "")
        self.footer_edit.setPlaceholderText("Fußzeile (nicht im Fließtext)")
        form.addRow("Kopfzeile", self.header_edit)
        form.addRow("Fußzeile", self.footer_edit)
        root.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.setObjectName("headerFooterButtons")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        band = str(focus_band or "").strip().lower()
        if band == "footer":
            self.footer_edit.setFocus()
        else:
            self.header_edit.setFocus()

    def result_header_footer(self) -> tuple[str, str]:
        return (self.header_edit.text() or "").strip(), (self.footer_edit.text() or "").strip()
