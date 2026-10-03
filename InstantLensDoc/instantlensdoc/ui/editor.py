"""Text-/Layout-Editor-Fläche mit Suche, Markieren und optionalen Zeilennummern."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QTextCharFormat, QTextCursor, QTextDocument, QTextOption
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QTextEdit, QWidget

from instantlensdoc.core.app_settings import (
    get_editor_bracket_auto_close,
    get_editor_bracket_match,
    get_editor_line_numbers,
    get_editor_minimap,
    get_editor_soft_wrap,
    get_editor_show_special_chars,
    get_editor_trim_whitespace_on_paste,
)
from instantlensdoc.core.bookmarks import (
    BM_SCHEMA_ID,
    BM_VERSION,
    BookmarksImportError,
    bookmarks_to_export_dict,
    export_bookmarks_json,
    parse_bookmarks_dict,
)

CLIPBOARD_HISTORY_MAX = 3
MINIMAP_WIDTH = 56
MINIMAP_SCROLLBAR_WIDTH = 14


class _LineNumberArea(QWidget):
    def __init__(self, editor: "TextEditor"):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event):  # noqa: N802
        self._editor.paint_line_number_area(event)

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._editor.toggle_bookmark_at_y(event.position().y())
        super().mousePressEvent(event)


class _MinimapArea(QWidget):
    """Einfache Linien-Übersicht (Minimap) rechts neben dem Editor."""

    def __init__(self, editor: "TextEditor"):
        super().__init__(editor)
        self._editor = editor
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Minimap — Klick springt zur Position")

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self._editor.minimap_width(), 0)

    def paintEvent(self, event):  # noqa: N802
        self._editor.paint_minimap_area(event)

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._editor.minimap_goto_y(event.position().y())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # noqa: N802
        if event.buttons() & Qt.LeftButton:
            self._editor.minimap_goto_y(event.position().y())
        super().mouseMoveEvent(event)


class TextEditor(QPlainTextEdit):
    line_bookmarks_changed = Signal()  # Zeilenfavoriten geändert → Sidebar-Liste

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
        self._minimap = bool(get_editor_minimap())
        self._soft_wrap = bool(get_editor_soft_wrap())
        self._show_special = bool(get_editor_show_special_chars())
        self._bracket_match = bool(get_editor_bracket_match())
        self._bracket_auto_close = bool(get_editor_bracket_auto_close())
        self._clipboard_history: list[str] = []
        self._find_selections: list = []
        self._mark_selections: list = []
        self._bracket_selections: list = []
        self._spell_selections: list = []
        self._line_bookmarks: set[int] = set()  # 0-basierte Blocknummern
        self._line_bookmark_order: list[int] = []  # Anzeige-/Persistenz-Reihenfolge (Blocks)
        self._line_bookmark_labels: dict[int, str] = {}  # Block → editierbares Label
        self._line_number_area = _LineNumberArea(self)
        self._minimap_area = _MinimapArea(self)
        self.blockCountChanged.connect(self._update_side_areas)
        self.updateRequest.connect(self._update_line_number_area)
        self.updateRequest.connect(self._update_minimap_area)
        self.cursorPositionChanged.connect(self._update_bracket_match)
        self.verticalScrollBar().valueChanged.connect(lambda _v: self._minimap_area.update())
        self._update_side_areas()
        self.set_line_numbers_visible(self._line_numbers)
        self.set_minimap_visible(self._minimap)
        self.set_soft_wrap(self._soft_wrap)
        self.set_special_chars_visible(self._show_special)

    def line_number_area_width(self) -> int:
        if not self._line_numbers:
            return 0
        digits = max(2, len(str(max(1, self.blockCount()))))
        # Extra Platz für Lesezeichen-Marker links
        return 14 + self.fontMetrics().horizontalAdvance("9") * digits

    def list_line_bookmarks(self) -> list[int]:
        """1-basierte Zeilennummern der Lesezeichen (Drag-Reihenfolge, sonst Einfügereihenfolge)."""
        n = self.blockCount()
        ordered: list[int] = []
        seen: set[int] = set()
        for b in self._line_bookmark_order:
            if b in self._line_bookmarks and 0 <= b < n and b not in seen:
                ordered.append(b + 1)
                seen.add(b)
        for b in sorted(self._line_bookmarks):
            if 0 <= b < n and b not in seen:
                ordered.append(b + 1)
                seen.add(b)
        return ordered

    def list_line_bookmarks_with_labels(self) -> list[tuple[int, str]]:
        """[(1-basierte Zeile, Label), …] in Anzeige-Reihenfolge; Label kann leer sein."""
        out: list[tuple[int, str]] = []
        for line in self.list_line_bookmarks():
            out.append((line, self.get_line_bookmark_label(line)))
        return out

    def reorder_line_bookmarks(self, lines: list[int]) -> list[int]:
        """
        Anzeige-Reihenfolge der Lesezeichen setzen (1-basierte Zeilen).
        Unbekannte/ungültige Zeilen werden ignoriert; fehlende Favoriten angehängt.
        """
        n = self.blockCount()
        new_order: list[int] = []
        seen: set[int] = set()
        for ln in lines:
            try:
                block_no = int(ln) - 1
            except (TypeError, ValueError):
                continue
            if block_no not in self._line_bookmarks or not (0 <= block_no < n):
                continue
            if block_no in seen:
                continue
            new_order.append(block_no)
            seen.add(block_no)
        for b in self._line_bookmark_order:
            if b in self._line_bookmarks and b not in seen and 0 <= b < n:
                new_order.append(b)
                seen.add(b)
        for b in sorted(self._line_bookmarks):
            if b not in seen and 0 <= b < n:
                new_order.append(b)
                seen.add(b)
        self._line_bookmark_order = new_order
        self.line_bookmarks_changed.emit()
        return self.list_line_bookmarks()

    def clear_line_bookmarks(self) -> None:
        self._line_bookmarks.clear()
        self._line_bookmark_order.clear()
        self._line_bookmark_labels.clear()
        self._line_number_area.update()
        self.line_bookmarks_changed.emit()

    def is_line_bookmarked(self, line: int) -> bool:
        """line: 1-basiert."""
        return int(line) - 1 in self._line_bookmarks

    def get_line_bookmark_label(self, line: int) -> str:
        """Editierbares Label für Zeilenfavorit (1-basiert); leer wenn keines."""
        return str(self._line_bookmark_labels.get(int(line) - 1, "") or "")

    def set_line_bookmark_label(self, line: int, label: str) -> bool:
        """
        Label für vorhandenen Zeilenfavorit setzen (1-basiert).
        Leeres Label entfernt den Text. Rückgabe False wenn Zeile kein Favorit.
        """
        block_no = int(line) - 1
        if block_no not in self._line_bookmarks:
            return False
        text = str(label or "").strip()
        if text:
            self._line_bookmark_labels[block_no] = text[:80]
        else:
            self._line_bookmark_labels.pop(block_no, None)
        self.line_bookmarks_changed.emit()
        return True

    def toggle_line_bookmark(self, line: int | None = None) -> bool:
        """
        Zeile als Favorit/Lesezeichen umschalten.
        line: 1-basiert; None = Cursor-Zeile.
        Rückgabe: True wenn danach Lesezeichen.
        """
        if line is None:
            block_no = self.textCursor().blockNumber()
        else:
            block_no = int(line) - 1
        if block_no < 0 or block_no >= self.blockCount():
            return False
        if block_no in self._line_bookmarks:
            self._line_bookmarks.discard(block_no)
            if block_no in self._line_bookmark_order:
                self._line_bookmark_order = [b for b in self._line_bookmark_order if b != block_no]
            self._line_bookmark_labels.pop(block_no, None)
            now = False
        else:
            self._line_bookmarks.add(block_no)
            if block_no not in self._line_bookmark_order:
                self._line_bookmark_order.append(block_no)
            now = True
        self._line_number_area.update()
        self.line_bookmarks_changed.emit()
        return now

    def goto_next_line_bookmark(self) -> int:
        """Nächstes Lesezeichen ab Cursor (nach Zeilennummer); Rückgabe 1-basierte Zeile oder 0."""
        marks = sorted(self.list_line_bookmarks())
        if not marks:
            return 0
        cur = self.textCursor().blockNumber() + 1
        for m in marks:
            if m > cur:
                self.goto_line(m)
                return m
        self.goto_line(marks[0])
        return marks[0]

    def goto_prev_line_bookmark(self) -> int:
        """Vorheriges Lesezeichen (nach Zeilennummer); Rückgabe 1-basierte Zeile oder 0."""
        marks = sorted(self.list_line_bookmarks())
        if not marks:
            return 0
        cur = self.textCursor().blockNumber() + 1
        for m in reversed(marks):
            if m < cur:
                self.goto_line(m)
                return m
        self.goto_line(marks[-1])
        return marks[-1]

    def current_line_number(self) -> int:
        """1-basierte Cursor-Zeile."""
        return self.textCursor().blockNumber() + 1

    def line_count(self) -> int:
        """Anzahl Textzeilen (Blöcke)."""
        return max(1, self.blockCount())

    def export_line_bookmarks_dict(self, *, source: str = "") -> dict:
        """Zeilen-Lesezeichen als exportierbares Dict (Schema ildbm-v1)."""
        return bookmarks_to_export_dict(
            self.list_line_bookmarks_with_labels(), source=source
        )

    def export_line_bookmarks_json(
        self, path: str | Path, *, source: str = ""
    ) -> Path:
        """Zeilen-Lesezeichen als JSON-Datei schreiben (ildbm-v1)."""
        return export_bookmarks_json(
            path, self.list_line_bookmarks_with_labels(), source=source
        )

    def import_line_bookmarks_dict(
        self,
        data: dict,
        *,
        merge: bool = False,
        max_line: int | None = None,
    ) -> list[tuple[int, str]]:
        """
        Lesezeichen aus Dict übernehmen.
        merge=True: bestehende behalten und neue anhängen/Label aktualisieren.
        max_line: optional obere Grenze (inkl.) zum Filtern ungültiger Zeilen.
        """
        limit = int(max_line) if max_line is not None else self.blockCount()
        if limit < 1:
            limit = self.blockCount()
        incoming = parse_bookmarks_dict(data, max_line=limit)
        if not merge:
            self.clear_line_bookmarks()
        for line, label in incoming:
            block_no = line - 1
            self._line_bookmarks.add(block_no)
            if block_no not in self._line_bookmark_order:
                self._line_bookmark_order.append(block_no)
            if label:
                self._line_bookmark_labels[block_no] = label
            elif not merge:
                self._line_bookmark_labels.pop(block_no, None)
        self._line_number_area.update()
        self.line_bookmarks_changed.emit()
        return self.list_line_bookmarks_with_labels()

    def import_line_bookmarks_json(
        self,
        path: str | Path,
        *,
        merge: bool = False,
        max_line: int | None = None,
    ) -> list[tuple[int, str]]:
        """Lesezeichen aus JSON-Datei laden (ersetzt oder merge)."""
        import json as _json

        limit = int(max_line) if max_line is not None else self.blockCount()
        if limit < 1:
            limit = self.blockCount()
        try:
            data = _json.loads(Path(path).read_text(encoding="utf-8"))
        except _json.JSONDecodeError as e:
            raise BookmarksImportError(f"Ungültiges JSON: {e}") from e
        except OSError as e:
            raise BookmarksImportError(str(e)) from e
        return self.import_line_bookmarks_dict(data, merge=merge, max_line=limit)

    def toggle_bookmark_at_y(self, y: float) -> bool:
        """Klick in Zeilennummernleiste → Lesezeichen der sichtbaren Zeile."""
        if not self._line_numbers:
            return False
        block = self.firstVisibleBlock()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        while block.isValid():
            bottom = top + int(self.blockBoundingRect(block).height())
            if top <= y < bottom:
                return self.toggle_line_bookmark(block.blockNumber() + 1)
            block = block.next()
            top = bottom
        return False

    def minimap_width(self) -> int:
        return MINIMAP_WIDTH if self._minimap else 0

    def set_line_numbers_visible(self, visible: bool) -> None:
        self._line_numbers = bool(visible)
        self._line_number_area.setVisible(self._line_numbers)
        self._update_side_areas()
        self.viewport().update()

    def line_numbers_visible(self) -> bool:
        return self._line_numbers

    def set_minimap_visible(self, visible: bool) -> None:
        """Optionale Minimap (Linien-Übersicht) + dickere Scrollbar."""
        self._minimap = bool(visible)
        self._minimap_area.setVisible(self._minimap)
        sb = self.verticalScrollBar()
        if self._minimap:
            sb.setStyleSheet(
                f"QScrollBar:vertical {{ width: {MINIMAP_SCROLLBAR_WIDTH}px; min-width: {MINIMAP_SCROLLBAR_WIDTH}px; }}"
            )
        else:
            sb.setStyleSheet("")
        self._update_side_areas()
        self._minimap_area.update()
        self.viewport().update()

    def minimap_visible(self) -> bool:
        return bool(self._minimap)

    def set_soft_wrap(self, enabled: bool) -> None:
        """Zeilenumbruch am Fensterrand (Soft-Wrap) ein/aus."""
        self._soft_wrap = bool(enabled)
        if self._soft_wrap:
            self.setLineWrapMode(QPlainTextEdit.WidgetWidth)
            self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        else:
            self.setLineWrapMode(QPlainTextEdit.NoWrap)

    def soft_wrap_enabled(self) -> bool:
        return bool(self._soft_wrap)

    def set_special_chars_visible(self, visible: bool) -> None:
        """Tabs/Leerzeichen/Absatzenden als sichtbare Sonderzeichen (ShowTabsAndSpaces)."""
        self._show_special = bool(visible)
        option = self.document().defaultTextOption()
        flags = option.flags()
        flag = QTextOption.ShowTabsAndSpaces
        # Paragraph-Marken zusätzlich, falls verfügbar
        para = getattr(QTextOption, "ShowLineAndParagraphSeparators", None)
        if self._show_special:
            flags |= flag
            if para is not None:
                flags |= para
        else:
            flags &= ~flag
            if para is not None:
                flags &= ~para
        option.setFlags(flags)
        self.document().setDefaultTextOption(option)
        self.viewport().update()

    def special_chars_visible(self) -> bool:
        return bool(self._show_special)

    def insert_soft_hyphen(self) -> bool:
        """Weiches Trennzeichen U+00AD an der Cursor-Position einfügen."""
        cur = self.textCursor()
        cur.insertText("\u00ad")
        self.setTextCursor(cur)
        return True

    def insert_nbsp(self) -> bool:
        """
        Geschütztes Leerzeichen einfügen.
        Qt/QTextDocument normalisiert U+00A0 → U+0020; daher U+202F (Narrow NBSP).
        """
        cur = self.textCursor()
        # U+202F Narrow No-Break Space — bricht nicht, bleibt in QPlainTextEdit erhalten
        cur.insertText("\u202f")
        self.setTextCursor(cur)
        return True

    # Alias / Konstante für Tests und Doku
    NBSP_CHAR = "\u202f"
    SOFT_HYPHEN_CHAR = "\u00ad"

    def set_bracket_match_enabled(self, enabled: bool) -> None:
        """Bracket-Match Highlight ein/aus."""
        self._bracket_match = bool(enabled)
        if not self._bracket_match:
            self._bracket_selections = []
            self._apply_extra_selections()
        else:
            self._update_bracket_match()

    def bracket_match_enabled(self) -> bool:
        return bool(self._bracket_match)

    def set_bracket_auto_close_enabled(self, enabled: bool) -> None:
        """Beim Tippen schließende Klammern/Anführungszeichen einfügen."""
        self._bracket_auto_close = bool(enabled)

    def bracket_auto_close_enabled(self) -> bool:
        return bool(self._bracket_auto_close)

    def _apply_extra_selections(self) -> None:
        merged = (
            list(self._find_selections)
            + list(self._mark_selections)
            + list(self._bracket_selections)
            + list(getattr(self, "_spell_selections", []) or [])
        )
        self.setExtraSelections(merged)

    _BRACKET_PAIRS = {"(": ")", "[": "]", "{": "}", ")": "(", "]": "[", "}": "{"}
    _BRACKET_OPEN = frozenset("([{")
    _BRACKET_CLOSE = frozenset(")]}")

    def _update_bracket_match(self) -> None:
        self._bracket_selections = []
        if not self._bracket_match:
            self._apply_extra_selections()
            return
        cur = self.textCursor()
        if cur.hasSelection():
            self._apply_extra_selections()
            return
        pos = cur.position()
        text = self.toPlainText()
        if not text:
            self._apply_extra_selections()
            return
        # Klammer links vom Cursor oder unter dem Cursor
        ch_left = text[pos - 1] if pos > 0 else ""
        ch_at = text[pos] if pos < len(text) else ""
        match_pos = -1
        origin = -1
        if ch_left in self._BRACKET_PAIRS:
            origin = pos - 1
            match_pos = self._find_matching_bracket(text, origin)
        elif ch_at in self._BRACKET_PAIRS:
            origin = pos
            match_pos = self._find_matching_bracket(text, origin)
        if origin < 0 or match_pos < 0:
            self._apply_extra_selections()
            return
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#B4D7FF"))
        for p in (origin, match_pos):
            sel = QTextEdit.ExtraSelection()
            c = QTextCursor(self.document())
            c.setPosition(p)
            c.setPosition(p + 1, QTextCursor.KeepAnchor)
            sel.cursor = c
            sel.format = fmt
            self._bracket_selections.append(sel)
        self._apply_extra_selections()

    def _find_matching_bracket(self, text: str, pos: int) -> int:
        """Index der passenden Klammer oder -1."""
        if pos < 0 or pos >= len(text):
            return -1
        ch = text[pos]
        other = self._BRACKET_PAIRS.get(ch)
        if other is None:
            return -1
        if ch in self._BRACKET_OPEN:
            depth = 0
            for i in range(pos, len(text)):
                c = text[i]
                if c == ch:
                    depth += 1
                elif c == other:
                    depth -= 1
                    if depth == 0:
                        return i
            return -1
        # closing → rückwärts
        depth = 0
        for i in range(pos, -1, -1):
            c = text[i]
            if c == ch:
                depth += 1
            elif c == other:
                depth -= 1
                if depth == 0:
                    return i
        return -1

    def goto_line(self, line: int) -> bool:
        """Cursor auf 1-basierte Zeilennummer setzen; True bei Erfolg."""
        n = int(line)
        if n < 1 or n > self.blockCount():
            return False
        block = self.document().findBlockByNumber(n - 1)
        if not block.isValid():
            return False
        cursor = QTextCursor(block)
        cursor.movePosition(QTextCursor.StartOfBlock)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        self.setFocus()
        return True

    def duplicate_line(self) -> bool:
        """Aktuelle Zeile (bzw. ausgewählte Zeilen) direkt darunter duplizieren."""
        cur = self.textCursor()
        doc = self.document()
        if cur.hasSelection():
            start = cur.selectionStart()
            end = cur.selectionEnd()
            start_block = doc.findBlock(start)
            end_block = doc.findBlock(end if end > start else start)
            if end > start and doc.findBlock(end).position() == end:
                end_block = end_block.previous()
                if not end_block.isValid():
                    end_block = start_block
        else:
            start_block = end_block = cur.block()

        lines: list[str] = []
        block = start_block
        while block.isValid() and block.blockNumber() <= end_block.blockNumber():
            lines.append(block.text())
            block = block.next()
        if not lines:
            return False

        insert_at = end_block.position() + len(end_block.text())
        text = "\n" + "\n".join(lines)
        cur.beginEditBlock()
        cur.setPosition(insert_at)
        cur.insertText(text)
        # Neue Duplikat-Zeilen auswählen
        sel_start = insert_at + 1
        sel_end = insert_at + len(text)
        cur.setPosition(sel_start)
        cur.setPosition(sel_end, QTextCursor.KeepAnchor)
        cur.endEditBlock()
        self.setTextCursor(cur)
        self.ensureCursorVisible()
        return True

    def move_line(self, delta: int) -> bool:
        """Aktuelle Zeile(n) um delta (−1 hoch / +1 runter) verschieben."""
        if delta not in (-1, 1):
            return False
        cur = self.textCursor()
        doc = self.document()
        if cur.hasSelection():
            start = cur.selectionStart()
            end = cur.selectionEnd()
            start_block = doc.findBlock(start)
            end_block = doc.findBlock(end if end > start else start)
            if end > start and doc.findBlock(end).position() == end:
                end_block = end_block.previous()
                if not end_block.isValid():
                    end_block = start_block
        else:
            start_block = end_block = cur.block()

        if not start_block.isValid() or not end_block.isValid():
            return False

        first = start_block.blockNumber()
        last = end_block.blockNumber()
        if first > last:
            first, last = last, first

        lines = self.toPlainText().split("\n")
        n = len(lines)
        if delta < 0:
            if first <= 0:
                return False
            block = lines[first : last + 1]
            neighbor = lines[first - 1]
            lines[first - 1 : last + 1] = block + [neighbor]
            new_first = first - 1
            new_last = last - 1
        else:
            if last >= n - 1:
                return False
            block = lines[first : last + 1]
            neighbor = lines[last + 1]
            lines[first : last + 2] = [neighbor] + block
            new_first = first + 1
            new_last = last + 1

        new_text = "\n".join(lines)
        # Absolute Zeichenpositionen der neuen Auswahl
        pos = 0
        sel_start = 0
        sel_end = 0
        for i, line in enumerate(lines):
            if i == new_first:
                sel_start = pos
            if i == new_last:
                sel_end = pos + len(line)
                break
            pos += len(line) + 1

        cur.beginEditBlock()
        cur.select(QTextCursor.Document)
        cur.insertText(new_text)
        cur.setPosition(sel_start)
        cur.setPosition(sel_end, QTextCursor.KeepAnchor)
        cur.endEditBlock()
        self.setTextCursor(cur)
        self.ensureCursorVisible()
        return True

    def move_line_up(self) -> bool:
        return self.move_line(-1)

    def move_line_down(self) -> bool:
        return self.move_line(1)

    def trim_trailing_whitespace(self) -> bool:
        """Trailing Whitespace pro Zeile entfernen; True wenn Text geändert wurde."""
        text = self.toPlainText()
        if not text:
            return False
        lines = text.split("\n")
        trimmed = [line.rstrip(" \t") for line in lines]
        if trimmed == lines:
            return False
        new_text = "\n".join(trimmed)
        cur = self.textCursor()
        pos = cur.position()
        anchor = cur.anchor()
        cur.beginEditBlock()
        cur.select(QTextCursor.Document)
        cur.insertText(new_text)
        cur.endEditBlock()
        cur.setPosition(min(pos, len(new_text)))
        if anchor != pos:
            cur.setPosition(min(anchor, len(new_text)), QTextCursor.KeepAnchor)
        self.setTextCursor(cur)
        return True

    def insert_pdf_page_image_reference(self, image_path: Path | str, *, page_label: str) -> None:
        """Verweis auf gerenderte PDF-Seite als Bilddatei einfügen."""
        path = Path(image_path)
        line = f"\n[PDF-Seitenbild {page_label}: {path}]\n"
        cur = self.textCursor()
        if cur.hasSelection():
            cur.removeSelectedText()
        cur.insertText(line)
        self.setTextCursor(cur)
        self.ensureCursorVisible()

    def sort_lines_az(self) -> bool:
        """Ausgewählte Zeilen alphabetisch (A–Z, case-insensitive) sortieren."""
        cur = self.textCursor()
        doc = self.document()
        if cur.hasSelection():
            start = cur.selectionStart()
            end = cur.selectionEnd()
            start_block = doc.findBlock(start)
            end_block = doc.findBlock(end if end > start else start)
            if end > start and doc.findBlock(end).position() == end:
                end_block = end_block.previous()
                if not end_block.isValid():
                    end_block = start_block
        else:
            # Keine Auswahl: gesamte Datei sortieren
            start_block = doc.firstBlock()
            end_block = doc.lastBlock()

        if not start_block.isValid() or not end_block.isValid():
            return False

        first = start_block.blockNumber()
        last = end_block.blockNumber()
        if first > last:
            first, last = last, first

        lines = self.toPlainText().split("\n")
        block = lines[first : last + 1]
        if len(block) < 2:
            return False
        sorted_block = sorted(block, key=lambda s: s.casefold())
        if sorted_block == block:
            return True  # bereits sortiert
        lines[first : last + 1] = sorted_block
        new_text = "\n".join(lines)

        pos = 0
        sel_start = 0
        sel_end = 0
        for i, line in enumerate(lines):
            if i == first:
                sel_start = pos
            if i == last:
                sel_end = pos + len(line)
                break
            pos += len(line) + 1

        cur.beginEditBlock()
        cur.select(QTextCursor.Document)
        cur.insertText(new_text)
        cur.setPosition(sel_start)
        cur.setPosition(sel_end, QTextCursor.KeepAnchor)
        cur.endEditBlock()
        self.setTextCursor(cur)
        self.ensureCursorVisible()
        return True

    def comment_prefix_for_path(self, path: Path | str | None = None) -> str:
        """Kommentarpräfix für einfache Sprachen: # oder //."""
        ext = ""
        if path is not None:
            ext = Path(path).suffix.lower()
        hash_ext = {
            ".py", ".pyw", ".rb", ".pl", ".pm", ".sh", ".bash", ".zsh",
            ".ps1", ".psm1", ".r", ".yaml", ".yml", ".toml", ".ini", ".cfg",
            ".conf", ".properties", ".gitignore", ".dockerfile", ".cmake",
            ".mak", ".mk", ".am", ".m4",
        }
        slash_ext = {
            ".js", ".jsx", ".ts", ".tsx", ".mjs", ".c", ".h", ".cpp", ".cc",
            ".cxx", ".hpp", ".hh", ".cs", ".java", ".kt", ".kts", ".go",
            ".rs", ".swift", ".scala", ".php", ".sql", ".jsonc", ".scss",
            ".less", ".dart",
        }
        if ext in hash_ext:
            return "#"
        if ext in slash_ext:
            return "//"
        # Heuristik am Dokumentanfang
        text = self.toPlainText()
        for line in text.splitlines()[:40]:
            s = line.lstrip()
            if s.startswith("//"):
                return "//"
            if s.startswith("#") and not s.startswith("#!"):
                return "#"
        return "#"

    def toggle_line_comment(self, prefix: str | None = None) -> bool:
        """Zeilen kommentieren/auskommentieren (# oder //)."""
        marker = (prefix or "#").strip() or "#"
        if marker not in ("#", "//"):
            marker = "#"
        cur = self.textCursor()
        doc = self.document()
        if cur.hasSelection():
            start = cur.selectionStart()
            end = cur.selectionEnd()
            start_block = doc.findBlock(start)
            end_block = doc.findBlock(end if end > start else start)
            if end > start and doc.findBlock(end).position() == end:
                end_block = end_block.previous()
                if not end_block.isValid():
                    end_block = start_block
        else:
            start_block = end_block = cur.block()

        blocks: list = []
        block = start_block
        while block.isValid() and block.blockNumber() <= end_block.blockNumber():
            blocks.append(block)
            block = block.next()
        if not blocks:
            return False

        def _is_commented(text: str) -> bool:
            s = text.lstrip()
            if not s:
                return True  # leere Zeilen zählen als „schon kommentiert“ für Uncomment-Entscheidung
            return s.startswith(marker)

        nonempty = [b.text() for b in blocks if b.text().strip()]
        all_commented = bool(nonempty) and all(_is_commented(t) for t in nonempty)

        start_bn = start_block.blockNumber()
        end_bn = end_block.blockNumber()
        cur.beginEditBlock()
        block = start_block
        while block.isValid() and block.blockNumber() <= end_bn:
            text = block.text()
            bcur = QTextCursor(block)
            bcur.movePosition(QTextCursor.StartOfBlock)
            if all_commented:
                # Präfix nach Einrückung entfernen
                lead = len(text) - len(text.lstrip()) if text.strip() else 0
                rest = text[lead:]
                if rest.startswith(marker):
                    remove = len(marker)
                    if rest[remove:].startswith(" "):
                        remove += 1
                    bcur.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, lead)
                    bcur.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, remove)
                    bcur.removeSelectedText()
            else:
                if text.strip():
                    lead = len(text) - len(text.lstrip())
                    bcur.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, lead)
                    bcur.insertText(marker + " ")
            block = block.next()
        cur.endEditBlock()

        new_cur = self.textCursor()
        start_blk = doc.findBlockByNumber(start_bn)
        end_blk = doc.findBlockByNumber(end_bn)
        if not start_blk.isValid():
            start_blk = doc.firstBlock()
        if not end_blk.isValid():
            end_blk = doc.lastBlock()
        new_cur.setPosition(start_blk.position())
        new_cur.setPosition(
            end_blk.position() + max(0, end_blk.length() - 1),
            QTextCursor.KeepAnchor,
        )
        self.setTextCursor(new_cur)
        return True

    def _update_line_number_area_width(self, _new_block_count: int = 0) -> None:
        self._update_side_areas()

    def _update_side_areas(self, _new_block_count: int = 0) -> None:
        left = self.line_number_area_width()
        right = self.minimap_width()
        self.setViewportMargins(left, 0, right, 0)
        self._layout_side_areas()

    def _update_line_number_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_side_areas()

    def _update_minimap_area(self, rect: QRect, dy: int) -> None:
        if not self._minimap:
            return
        if dy:
            self._minimap_area.scroll(0, dy)
        else:
            self._minimap_area.update()
        if rect.contains(self.viewport().rect()):
            self._update_side_areas()

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._layout_side_areas()

    def _layout_side_areas(self) -> None:
        cr = self.contentsRect()
        ln_w = self.line_number_area_width()
        mm_w = self.minimap_width()
        self._line_number_area.setGeometry(QRect(cr.left(), cr.top(), ln_w, cr.height()))
        self._minimap_area.setGeometry(
            QRect(cr.right() - mm_w + 1, cr.top(), mm_w, cr.height())
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
        mark_color = QColor("#C45C26")
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                if block_number in self._line_bookmarks:
                    fh = self.fontMetrics().height()
                    cy = top + fh // 2
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(mark_color)
                    painter.drawEllipse(3, cy - 4, 8, 8)
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

    def paint_minimap_area(self, event) -> None:
        if not self._minimap:
            return
        painter = QPainter(self._minimap_area)
        painter.fillRect(event.rect(), QColor("#F0F3F6"))
        h = max(1, self._minimap_area.height())
        w = max(1, self._minimap_area.width())
        doc = self.document()
        n = max(1, doc.blockCount())
        # Sichtbarer Bereich
        sb = self.verticalScrollBar()
        vmax = max(1, sb.maximum())
        vval = sb.value()
        vpage = max(1, sb.pageStep())
        vis_top = int(h * (vval / (vmax + vpage)))
        vis_h = max(4, int(h * (vpage / (vmax + vpage))))
        painter.fillRect(0, vis_top, w, vis_h, QColor(70, 130, 180, 55))
        painter.setPen(QColor(70, 130, 180, 120))
        painter.drawRect(0, vis_top, w - 1, vis_h)
        # Linien-Übersicht: Inhalt → Strichbreite
        painter.setPen(Qt.NoPen)
        block = doc.firstBlock()
        i = 0
        while block.isValid():
            text = block.text().rstrip()
            if text:
                dens = min(1.0, len(text) / 80.0)
                bar_w = max(2, int((w - 6) * dens))
                y = int(i * h / n)
                yh = max(1, int(h / n))
                painter.fillRect(3, y, bar_w, yh, QColor("#6A7A8A"))
            block = block.next()
            i += 1

    def minimap_goto_y(self, y: float) -> None:
        """Minimap-Klick → relative Dokumentposition."""
        if not self._minimap:
            return
        h = max(1, self._minimap_area.height())
        ratio = max(0.0, min(1.0, float(y) / float(h)))
        n = max(1, self.blockCount())
        line = int(ratio * (n - 1))
        block = self.document().findBlockByNumber(line)
        if not block.isValid():
            return
        cur = self.textCursor()
        cur.setPosition(block.position())
        self.setTextCursor(cur)
        self.centerCursor()
        self._minimap_area.update()

    def clipboard_history(self) -> list[str]:
        """Letzte eingefügte Textschnipsel (max. 3, neueste zuerst)."""
        return list(self._clipboard_history)

    def push_clipboard_history(self, text: str) -> list[str]:
        """Text in den Clipboard-Verlauf aufnehmen (Deduplizierung, max. 3)."""
        raw = text if text is not None else ""
        if not str(raw):
            return self.clipboard_history()
        entry = str(raw)
        hist = [entry] + [t for t in self._clipboard_history if t != entry]
        self._clipboard_history = hist[:CLIPBOARD_HISTORY_MAX]
        return self.clipboard_history()

    def paste_clipboard_history(self, index: int) -> bool:
        """Eintrag aus dem Verlauf an der Cursor-Position einfügen."""
        hist = self.clipboard_history()
        i = int(index)
        if i < 0 or i >= len(hist):
            return False
        text = hist[i]
        # erneut an den Anfang (zuletzt genutzt)
        self.push_clipboard_history(text)
        cur = self.textCursor()
        cur.insertText(text)
        self.setTextCursor(cur)
        return True

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
        if source is not None and source.hasText():
            text = source.text()
            if (
                get_editor_trim_whitespace_on_paste()
            ):
                # Trailing Whitespace pro Zeile entfernen (nicht führend)
                lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
                trimmed = "\n".join(line.rstrip(" \t") for line in lines)
                if trimmed != text:
                    from PySide6.QtCore import QMimeData

                    md = QMimeData()
                    md.setText(trimmed)
                    self.push_clipboard_history(trimmed)
                    super().insertFromMimeData(md)
                    return
            self.push_clipboard_history(text)
        super().insertFromMimeData(source)

    def clear_extra_selections(self) -> None:
        self._find_selections = []
        self._mark_selections = []
        self._spell_selections = []
        self.setExtraSelections(list(self._bracket_selections))

    def clear_spelling(self) -> None:
        """Nur Rechtschreibmarkierungen entfernen."""
        self._spell_selections = []
        self._apply_extra_selections()

    def check_spelling(self, dict_path: str | None = None) -> int:
        """
        Lokale Wortliste laden und unbekannte Wörter wellig markieren.
        Ohne Spell-Lib — reine Wortlisten-Prüfung. Rückgabe: Anzahl Markierungen.
        """
        from pathlib import Path

        from instantlensdoc.core.app_settings import get_spellcheck_dict_path
        from instantlensdoc.core.spellcheck import spellcheck_text

        path = (dict_path or get_spellcheck_dict_path() or "").strip()
        if not path:
            self.clear_spelling()
            raise FileNotFoundError("Kein Wörterbuch-Pfad gesetzt")
        if not Path(path).is_file():
            self.clear_spelling()
            raise FileNotFoundError(f"Wörterbuch nicht gefunden: {path}")
        text = self.toPlainText()
        spans = spellcheck_text(text, path)
        fmt = QTextCharFormat()
        fmt.setUnderlineColor(QColor("#C0392B"))
        fmt.setUnderlineStyle(QTextCharFormat.WaveUnderline)
        fmt.setToolTip("Unbekanntes Wort (lokale Wortliste)")
        selections: list = []
        for start, end, _word in spans:
            sel = QTextEdit.ExtraSelection()
            c = QTextCursor(self.document())
            c.setPosition(start)
            c.setPosition(end, QTextCursor.KeepAnchor)
            sel.cursor = c
            sel.format = fmt
            selections.append(sel)
        self._spell_selections = selections
        self._apply_extra_selections()
        return len(selections)

    @staticmethod
    def _find_flags(*, case_sensitive: bool = False) -> QTextDocument.FindFlag:
        flags = QTextDocument.FindFlag(0)
        if case_sensitive:
            flags |= QTextDocument.FindCaseSensitively
        return flags

    def find_and_highlight(self, query: str, *, case_sensitive: bool = False) -> int:
        """Alle Vorkommen suchen und gelb markieren; Cursor auf ersten Treffer."""
        self._find_selections = []
        self._last_query = query or ""
        self._last_case_sensitive = case_sensitive
        if not query:
            self._apply_extra_selections()
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

        self._find_selections = selections
        self._apply_extra_selections()
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

    def find_prev(self, query: str | None = None, *, case_sensitive: bool | None = None) -> bool:
        q = query if query is not None else self._last_query
        if not q:
            return False
        if case_sensitive is None:
            case_sensitive = self._last_case_sensitive
        self._last_query = q
        self._last_case_sensitive = case_sensitive
        flags = self._find_flags(case_sensitive=case_sensitive) | QTextDocument.FindBackward
        found = self.find(q, flags)
        if not found:
            cur = self.textCursor()
            cur.movePosition(QTextCursor.End)
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
        self._mark_selections.append(sel)
        self._apply_extra_selections()
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

    def transform_document_case(self, mode: str) -> bool:
        """
        Gesamten Dokumenttext umwandeln.
        mode: 'upper' | 'lower'
        """
        mode = (mode or "").strip().lower()
        if mode not in ("upper", "lower"):
            return False
        text = self.toPlainText()
        if not text:
            return False
        new = text.upper() if mode == "upper" else text.lower()
        if new == text:
            return False
        cur = self.textCursor()
        pos = cur.position()
        cur.beginEditBlock()
        cur.select(QTextCursor.Document)
        cur.insertText(new)
        cur.endEditBlock()
        # Cursor-Position soweit möglich erhalten
        new_cur = self.textCursor()
        new_cur.setPosition(min(pos, len(new)))
        self.setTextCursor(new_cur)
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
        start_bn = start_block.blockNumber()
        end_bn = end_block.blockNumber()
        block = start_block
        while block.isValid() and block.blockNumber() <= end_bn:
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
        # Auswahl über die betroffenen Zeilen wiederherstellen (Blocknummern, nicht stale Pos)
        new_cur = self.textCursor()
        start_blk = doc.findBlockByNumber(start_bn)
        end_blk = doc.findBlockByNumber(end_bn)
        if not start_blk.isValid():
            start_blk = doc.firstBlock()
        if not end_blk.isValid():
            end_blk = doc.lastBlock()
        new_cur.setPosition(start_blk.position())
        new_cur.setPosition(
            end_blk.position() + max(0, end_blk.length() - 1),
            QTextCursor.KeepAnchor,
        )
        self.setTextCursor(new_cur)
        return True

    def keyPressEvent(self, event):  # noqa: N802
        # Block ein-/ausrücken: Tab / Shift+Tab (aktuelle Zeile oder Auswahl)
        if event.key() == Qt.Key_Tab and not (event.modifiers() & Qt.ControlModifier):
            if event.modifiers() & Qt.ShiftModifier:
                self.outdent_selection()
            else:
                self.indent_selection()
            return
        if event.key() == Qt.Key_Backtab:
            self.outdent_selection()
            return
        # Bracket / Quote Auto-Close (Einstellung)
        if self._bracket_auto_close and not (
            event.modifiers()
            & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)
        ):
            ch = event.text()
            pairs = {"(": ")", "[": "]", "{": "}", '"': '"', "'": "'"}
            if ch in pairs:
                close = pairs[ch]
                cur = self.textCursor()
                if cur.hasSelection():
                    selected = cur.selectedText().replace("\u2029", "\n")
                    cur.insertText(ch + selected + close)
                    return
                doc = self.document()
                pos = cur.position()
                next_ch = ""
                if pos < doc.characterCount() - 1:
                    next_ch = doc.characterAt(pos)
                # Schließendes Zeichen schon da → nur tippen
                if next_ch == close and ch in "([{":
                    super().keyPressEvent(event)
                    return
                # Quotes: nur auto-schließen am Wortanfang / Whitespace
                if ch in ('"', "'"):
                    prev_ch = doc.characterAt(pos - 1) if pos > 0 else ""
                    if next_ch == ch:
                        # über vorhandenes Quote springen
                        cur.movePosition(QTextCursor.Right)
                        self.setTextCursor(cur)
                        return
                    if prev_ch and not prev_ch.isspace() and prev_ch not in "([{:=":
                        super().keyPressEvent(event)
                        return
                cur.insertText(ch + close)
                cur.movePosition(QTextCursor.Left)
                self.setTextCursor(cur)
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


class EditorPane(QWidget):
    """Texteditor mit optionaler Markdown-Vorschau (Split)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QSplitter, QTextBrowser, QVBoxLayout

        from instantlensdoc.core.app_settings import get_editor_markdown_preview

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(Qt.Horizontal)
        self.editor = TextEditor()
        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(True)
        self.preview.setPlaceholderText("Markdown-Vorschau…")
        font = QFont("Georgia", 11)
        font.setStyleHint(QFont.Serif)
        self.preview.setFont(font)
        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.preview)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        layout.addWidget(self.splitter)
        self._preview_visible = bool(get_editor_markdown_preview())
        self.preview.setVisible(self._preview_visible)
        self.editor.textChanged.connect(self._sync_preview)
        self._sync_preview()

    def set_preview_visible(self, visible: bool) -> None:
        from instantlensdoc.core.app_settings import set_editor_markdown_preview

        self._preview_visible = bool(visible)
        self.preview.setVisible(self._preview_visible)
        set_editor_markdown_preview(self._preview_visible)
        if self._preview_visible:
            self._sync_preview()

    def preview_visible(self) -> bool:
        return bool(self._preview_visible)

    def _sync_preview(self) -> None:
        if not self._preview_visible:
            return
        text = self.editor.toPlainText()
        try:
            # Qt Markdown (CommonMark-ähnlich)
            self.preview.setMarkdown(text)
        except Exception:
            self.preview.setPlainText(text)
