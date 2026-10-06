"""Datei ▸ Informationen: Textersteller / Autor wie Word File ▸ Info."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class DocInfoDialog(QDialog):
    """Autor/Ersteller anzeigen und bearbeiten (core.xml dc:creator / PDF /Author)."""

    def __init__(
        self,
        parent=None,
        *,
        author: str = "",
        filename: str = "",
        writable: bool = True,
    ):
        super().__init__(parent)
        self.setObjectName("ildDocInfoDialog")
        self.setWindowTitle("Informationen")
        self.resize(420, 180)
        layout = QVBoxLayout(self)
        hint = QLabel("Textersteller wie in Word unter Datei ▸ Informationen.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#555;")
        layout.addWidget(hint)
        if filename:
            layout.addWidget(QLabel(filename))
        form = QFormLayout()
        self.author_edit = QLineEdit(author or "")
        self.author_edit.setObjectName("docInfoAuthor")
        self.author_edit.setClearButtonEnabled(True)
        self.author_edit.setReadOnly(not writable)
        if not writable:
            self.author_edit.setToolTip("Dokument ist schreibgeschützt")
        form.addRow("Textersteller / Autor:", self.author_edit)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            if writable
            else QDialogButtonBox.Close
        )
        if writable:
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
        else:
            buttons.rejected.connect(self.reject)
            try:
                buttons.button(QDialogButtonBox.Close).clicked.connect(self.reject)
            except Exception:
                pass
        layout.addWidget(buttons)

    def author(self) -> str:
        return (self.author_edit.text() or "").strip()
