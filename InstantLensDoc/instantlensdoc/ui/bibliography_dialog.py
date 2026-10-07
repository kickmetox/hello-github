"""Einfaches lokales Literaturverzeichnis (kein Researcher)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)


class BibliographyDialog(QDialog):
    """Autor / Titel / Jahr — wird als sichtbarer Literaturblock eingefügt."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("bibliographyDialog")
        self.setWindowTitle("Literaturverzeichnis")
        self.setModal(True)
        self.resize(420, 220)
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.author = QLineEdit()
        self.author.setObjectName("bibAuthor")
        self.title = QLineEdit()
        self.title.setObjectName("bibTitle")
        self.year = QLineEdit()
        self.year.setObjectName("bibYear")
        self.author.setText("Mustermann, A.")
        self.title.setText("Titel des Werks")
        self.year.setText("2024")
        form.addRow("Autor", self.author)
        form.addRow("Titel", self.title)
        form.addRow("Jahr", self.year)
        root.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def result_entry(self) -> tuple[str, str, str]:
        return (
            (self.author.text() or "").strip() or "o. A.",
            (self.title.text() or "").strip() or "ohne Titel",
            (self.year.text() or "").strip() or "o. J.",
        )

    def result_block(self) -> str:
        author, title, year = self.result_entry()
        return f"Literatur\n[1] {author} ({year}): {title}."
