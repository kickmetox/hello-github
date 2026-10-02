"""Text-/Layout-Editor-Fläche mit Suche und Markieren."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtGui import QColor, QFont, QImage, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QTextEdit


class TextEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)
        self.setPlaceholderText("Dokumententext…")
        self._last_query = ""
        self._paste_image_dir: Path | None = None

    def set_paste_image_dir(self, path: Path | None) -> None:
        self._paste_image_dir = Path(path) if path else None

    def paste_clipboard_image(self) -> bool:
        """Bild aus Zwischenablage speichern und Pfad einfügen."""
        clip = QApplication.clipboard()
        if clip is None:
            return False
        md = clip.mimeData()
        img: QImage | None = None
        if md and md.hasImage():
            raw = md.imageData()
            if isinstance(raw, QImage) and not raw.isNull():
                img = raw
        if img is None:
            pm = clip.pixmap()
            if pm is not None and not pm.isNull():
                img = pm.toImage()
        if img is None or img.isNull():
            return False
        out_dir = self._paste_image_dir
        if out_dir is None or not out_dir.is_dir():
            out_dir = Path(tempfile.gettempdir()) / "InstantLensDoc_paste"
            out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"clipboard_{Path(tempfile.mktemp()).name}.png"
        if not img.save(str(out), "PNG"):
            return False
        cur = self.textCursor()
        cur.insertText(f"\n[Bild aus Zwischenablage: {out}]\n")
        self.setTextCursor(cur)
        return True

    def insertFromMimeData(self, source) -> None:  # noqa: N802
        if source is not None and source.hasImage():
            clip = QApplication.clipboard()
            if clip is not None:
                # Zwischenablage kann schon das Image halten — paste_clipboard_image
                if self.paste_clipboard_image():
                    return
        super().insertFromMimeData(source)

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
