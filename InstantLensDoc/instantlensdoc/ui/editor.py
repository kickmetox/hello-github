"""Text-/Layout-Editor-Fläche mit Suche und Markieren."""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit


class TextEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)
        self.setPlaceholderText("Dokumententext…")
        self._last_query = ""

    def clear_extra_selections(self) -> None:
        self.setExtraSelections([])

    def find_and_highlight(self, query: str) -> int:
        """Alle Vorkommen suchen und gelb markieren; Cursor auf ersten Treffer."""
        self.clear_extra_selections()
        self._last_query = query or ""
        if not query:
            return 0

        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#FFE066"))
        selections: list[QTextEdit.ExtraSelection] = []
        doc = self.document()
        cursor = QTextCursor(doc)
        count = 0
        first: QTextCursor | None = None

        while True:
            cursor = doc.find(query, cursor)
            if cursor.isNull():
                break
            sel = QTextEdit.ExtraSelection()
            sel.cursor = QTextCursor(cursor)
            sel.format = fmt
            selections.append(sel)
            if first is None:
                first = QTextCursor(cursor)
            count += 1
            if count > 500:
                break

        self.setExtraSelections(selections)
        if first is not None:
            self.setTextCursor(first)
            self.ensureCursorVisible()
        return count

    def find_next(self, query: str | None = None) -> bool:
        q = query if query is not None else self._last_query
        if not q:
            return False
        found = self.find(q)
        if not found:
            # von vorn
            cur = self.textCursor()
            cur.movePosition(QTextCursor.Start)
            self.setTextCursor(cur)
            found = self.find(q)
        return found

    def highlight_selection(self, color: str = "#FFE066") -> bool:
        """Aktuelle Auswahl dauerhaft (als ExtraSelection) markieren."""
        cur = self.textCursor()
        if not cur.hasSelection():
            return False
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(color))
        sel = QTextEdit.ExtraSelection()
        sel.cursor = QTextCursor(cur)
        sel.format = fmt
        existing = list(self.extraSelections())
        existing.append(sel)
        self.setExtraSelections(existing)
        return True

    def selected_snippet(self, max_len: int = 80) -> str:
        cur = self.textCursor()
        if not cur.hasSelection():
            return ""
        text = cur.selectedText().replace("\u2029", " ")
        return text[:max_len]


class RichPreview(QTextEdit):
    """Einfache HTML-Vorschau / Layout-Notizfläche."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(False)
        self.setAcceptRichText(True)
