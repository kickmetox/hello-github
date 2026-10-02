"""Text-/Layout-Editor-Fläche."""

from __future__ import annotations

from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit


class TextEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)
        self.setPlaceholderText("Dokumententext…")

    def find_and_highlight(self, query: str) -> int:
        if not query:
            return 0
        self.moveCursor(QTextCursor.Start)
        count = 0
        # Einfache Suche: erste Treffer markieren
        while self.find(query):
            count += 1
            if count > 200:
                break
        return count


class RichPreview(QTextEdit):
    """Einfache HTML-Vorschau / Layout-Notizfläche."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(False)
        self.setAcceptRichText(True)
