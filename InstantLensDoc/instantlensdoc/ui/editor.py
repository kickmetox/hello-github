"""Text-/Layout-Editor-Fläche mit Suche, Markieren und optionalen Zeilennummern."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QTextCharFormat, QTextCursor, QTextDocument
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QTextEdit, QWidget

from instantlensdoc.core.app_settings import get_editor_line_numbers


class _LineNumberArea(QWidget):
    def __init__(self, editor: "TextEditor"):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event):  # noqa: N802
        self._editor.paint_line_number_area(event)


class TextEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)
        self.setPlaceholderText("Dokumententext…")
        self._last_query = ""
        self._paste_image_dir: Path | None = None
        self._last_case_sensitive = False
        self._line_numbers = bool(get_editor_line_numbers())
        self._line_number_area = _LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self._update_line_number_area_width(0)
        self.set_line_numbers_visible(self._line_numbers)

    def line_number_area_width(self) -> int:
        if not self._line_numbers:
            return 0
        digits = max(2, len(str(max(1, self.blockCount()))))
        return 8 + self.fontMetrics().horizontalAdvance("9") * digits

    def set_line_numbers_visible(self, visible: bool) -> None:
        self._line_numbers = bool(visible)
        self._line_number_area.setVisible(self._line_numbers)
        self._update_line_number_area_width(0)
        self.viewport().update()

    def line_numbers_visible(self) -> bool:
        return self._line_numbers

    def _update_line_number_area_width(self, _new_block_count: int = 0) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def paint_line_number_area(self, event) -> None:
        if not self._line_numbers:
            return
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QColor("#E8ECF0"))
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#5A6A7A"))
                painter.drawText(
                    0,
                    top,
                    self._line_number_area.width() - 4,
                    self.fontMetrics().height(),
                    Qt.AlignRight,
                    str(block_number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

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

    @staticmethod
    def _find_flags(*, case_sensitive: bool = False) -> QTextDocument.FindFlag:
        flags = QTextDocument.FindFlag(0)
        if case_sensitive:
            flags |= QTextDocument.FindCaseSensitively
        return flags

    def find_and_highlight(self, query: str, *, case_sensitive: bool = False) -> int:
        """Alle Vorkommen suchen und gelb markieren; Cursor auf ersten Treffer."""
        self.clear_extra_selections()
        self._last_query = query or ""
        self._last_case_sensitive = case_sensitive
        if not query:
            return 0

        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#FFE066"))
        selections: list[QTextEdit.ExtraSelection] = []
        doc = self.document()
        cursor = QTextCursor(doc)
        count = 0
        first: QTextCursor | None = None
        flags = self._find_flags(case_sensitive=case_sensitive)

        while True:
            cursor = doc.find(query, cursor, flags)
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

    def find_next(self, query: str | None = None, *, case_sensitive: bool | None = None) -> bool:
        q = query if query is not None else self._last_query
        if not q:
            return False
        if case_sensitive is None:
            case_sensitive = self._last_case_sensitive
        self._last_query = q
        self._last_case_sensitive = case_sensitive
        flags = self._find_flags(case_sensitive=case_sensitive)
        found = self.find(q, flags)
        if not found:
            # von vorn
            cur = self.textCursor()
            cur.movePosition(QTextCursor.Start)
            self.setTextCursor(cur)
            found = self.find(q, flags)
        return found

    def replace_one(
        self,
        find: str,
        replace: str,
        *,
        case_sensitive: bool = False,
    ) -> int:
        """Aktuelle Auswahl ersetzen, wenn sie dem Suchbegriff entspricht; sonst nächsten Treffer suchen."""
        if not find:
            return 0
        cur = self.textCursor()
        selected = cur.selectedText().replace("\u2029", "\n")
        match = selected == find if case_sensitive else selected.casefold() == find.casefold()
        if cur.hasSelection() and match:
            cur.insertText(replace)
            self.setTextCursor(cur)
            self._last_query = find
            self._last_case_sensitive = case_sensitive
            return 1
        if self.find_next(find, case_sensitive=case_sensitive):
            cur = self.textCursor()
            if cur.hasSelection():
                cur.insertText(replace)
                self.setTextCursor(cur)
                return 1
        return 0

    def replace_all(
        self,
        find: str,
        replace: str,
        *,
        case_sensitive: bool = False,
    ) -> int:
        """Alle Vorkommen ersetzen. Rückgabe: Anzahl."""
        if not find:
            return 0
        self._last_query = find
        self._last_case_sensitive = case_sensitive
        flags = self._find_flags(case_sensitive=case_sensitive)
        doc = self.document()
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()
        count = 0
        search = QTextCursor(doc)
        while True:
            search = doc.find(find, search, flags)
            if search.isNull():
                break
            search.insertText(replace)
            count += 1
            if count > 50_000:
                break
        cursor.endEditBlock()
        return count

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

    def toggle_case_selection(self) -> bool:
        """
        Groß-/Kleinschreibung der Auswahl umschalten.
        Zyklus: GROSS → klein → Titel → GROSS.
        """
        cur = self.textCursor()
        if not cur.hasSelection():
            return False
        text = cur.selectedText().replace("\u2029", "\n")
        if not text:
            return False
        letters = [c for c in text if c.isalpha()]
        if letters and all(c.isupper() for c in letters):
            new = text.lower()
        elif letters and all(c.islower() for c in letters):
            new = text.title()
        else:
            new = text.upper()
        start = cur.selectionStart()
        cur.insertText(new)
        # Auswahl wiederherstellen
        cur.setPosition(start)
        cur.setPosition(start + len(new), QTextCursor.KeepAnchor)
        self.setTextCursor(cur)
        return True

    def indent_selection(self, spaces: int = 4) -> bool:
        """Einrückung der ausgewählten Zeilen erhöhen (Leerzeichen voranstellen)."""
        return self._adjust_indent(+max(1, int(spaces)))

    def outdent_selection(self, spaces: int = 4) -> bool:
        """Einrückung der ausgewählten Zeilen verringern."""
        return self._adjust_indent(-max(1, int(spaces)))

    def _adjust_indent(self, delta: int) -> bool:
        """delta > 0: einrücken; delta < 0: ausrücken. Wirkt auf alle Zeilen der Auswahl."""
        cur = self.textCursor()
        doc = self.document()
        if cur.hasSelection():
            start = cur.selectionStart()
            end = cur.selectionEnd()
        else:
            start = end = cur.position()
        start_block = doc.findBlock(start)
        end_block = doc.findBlock(end if end > start else start)
        # Wenn Auswahl am Zeilenanfang endet, letzte Zeile nicht mitnehmen
        if cur.hasSelection() and end > start and doc.findBlock(end).position() == end:
            end_block = end_block.previous()
            if not end_block.isValid():
                end_block = start_block

        pad = " " * abs(delta)
        cur.beginEditBlock()
        block = start_block
        first_pos = start_block.position()
        last_pos = end_block.position() + end_block.length() - 1
        while block.isValid() and block.position() <= end_block.position():
            bcur = QTextCursor(block)
            bcur.movePosition(QTextCursor.StartOfBlock)
            text = block.text()
            if delta > 0:
                bcur.insertText(pad)
            else:
                remove = 0
                for ch in text[: abs(delta)]:
                    if ch == " ":
                        remove += 1
                    elif ch == "\t":
                        remove += 1
                        break
                    else:
                        break
                if remove:
                    bcur.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, remove)
                    bcur.removeSelectedText()
            block = block.next()
        cur.endEditBlock()
        # Auswahl über die betroffenen Zeilen wiederherstellen
        new_cur = self.textCursor()
        new_cur.setPosition(first_pos)
        end_blk = doc.findBlock(last_pos)
        if not end_blk.isValid():
            end_blk = doc.lastBlock()
        new_cur.setPosition(
            end_blk.position() + max(0, end_blk.length() - 1),
            QTextCursor.KeepAnchor,
        )
        self.setTextCursor(new_cur)
        return True

    def keyPressEvent(self, event):  # noqa: N802
        if event.key() == Qt.Key_Tab and not (event.modifiers() & Qt.ControlModifier):
            if event.modifiers() & Qt.ShiftModifier:
                self.outdent_selection()
            elif self.textCursor().hasSelection():
                self.indent_selection()
            else:
                super().keyPressEvent(event)
            return
        super().keyPressEvent(event)

    def word_stats(self) -> tuple[int, int]:
        """(Wörter, Zeichen inkl. Whitespace) des aktuellen Texts."""
        text = self.toPlainText()
        words = len(text.split()) if text.strip() else 0
        return words, len(text)


class RichPreview(QTextEdit):
    """Einfache HTML-Vorschau / Layout-Notizfläche."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(False)
        self.setAcceptRichText(True)
