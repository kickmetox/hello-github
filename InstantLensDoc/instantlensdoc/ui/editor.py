"""Text-/Layout-Editor-Fläche mit Suche, Markieren und optionalen Zeilennummern."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QPainter,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
    QTextOption,
)
from PySide6.QtWidgets import QAbstractScrollArea, QApplication, QPlainTextEdit, QTextEdit, QWidget

from instantlensdoc.core.app_settings import (
    get_editor_bracket_auto_close,
    get_editor_bracket_match,
    get_editor_current_line_highlight,
    get_editor_indent_guides,
    get_editor_line_numbers,
    get_editor_minimap,
    get_editor_soft_tabs,
    get_editor_soft_wrap,
    get_editor_show_special_chars,
    get_editor_tab_width,
    get_editor_trim_whitespace_on_paste,
)


def apply_wheel_scroll(area: QAbstractScrollArea, event) -> bool:
    """Robustes Mausrad-/Trackpad-Scrollen für Text-/Dokument-Views — 2.6.27.

    - ``pixelDelta`` (Präzisions-Trackpad) bevorzugt
    - ``angleDelta`` Fallback (klassisches Mausrad, 120 ≈ 1 Notch)
    - Shift oder dominante X-Achse → horizontal
    - funktioniert auch ohne Fokus auf dem Widget (Hover reicht)

    Returns:
        True wenn der Event verarbeitet wurde.
    """
    if area is None or event is None:
        return False
    try:
        pixel = event.pixelDelta()
        angle = event.angleDelta()
        px_x = int(pixel.x())
        px_y = int(pixel.y())
        ang_x = int(angle.x())
        ang_y = int(angle.y())
    except Exception:
        return False

    mods = event.modifiers()
    shift = bool(mods & Qt.ShiftModifier)
    # Horizontales Scrollen: Shift+Rad oder klare X-Dominanz
    horizontal = shift or (abs(ang_x) > abs(ang_y) and ang_x != 0) or (
        abs(px_x) > abs(px_y) and px_x != 0 and px_y == 0
    )

    bar = area.horizontalScrollBar() if horizontal else area.verticalScrollBar()
    if bar is None or not bar.isEnabled():
        return False

    if horizontal:
        if px_x != 0:
            delta = px_x
        elif ang_x != 0:
            steps = ang_x / 120.0
            delta = int(steps * max(1, bar.singleStep()) * 3)
        elif shift and (px_y != 0 or ang_y != 0):
            # Shift+vertikales Rad → horizontal (Windows/Word-üblich)
            if px_y != 0:
                delta = px_y
            else:
                steps = ang_y / 120.0
                delta = int(steps * max(1, bar.singleStep()) * 3)
        else:
            return False
    else:
        if px_y != 0:
            delta = px_y
        elif ang_y != 0:
            steps = ang_y / 120.0
            delta = int(steps * max(1, bar.singleStep()) * 3)
        else:
            return False

    if delta == 0:
        return False

    # Qt: positives wheel-up → Inhalt nach unten → Scrollbar-Wert verringern
    new_val = bar.value() - delta
    new_val = max(bar.minimum(), min(bar.maximum(), new_val))
    if new_val == bar.value() and bar.maximum() <= bar.minimum():
        return False
    bar.setValue(new_val)
    try:
        event.accept()
    except Exception:
        pass
    return True
from instantlensdoc.core.bookmarks import (
    BM_SCHEMA_ID,
    BM_VERSION,
    BookmarksImportError,
    bookmarks_to_export_dict,
    export_bookmarks_json,
    parse_bookmarks_dict,
)

CLIPBOARD_HISTORY_MAX = 3
# Minimap (nur Plaintext/Code, Standard aus): schmaler und dezenter als bis 2.6.53
# (56 px, kräftige Balken, dicke Scrollbar) — Feldrückmeldung „graue Balken, nutzlos“
MINIMAP_WIDTH = 36
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

    def wheelEvent(self, event):  # noqa: N802
        # Mausrad über Zeilennummern → Editor scrollen — 2.6.27
        if self._editor is not None and apply_wheel_scroll(self._editor, event):
            return
        super().wheelEvent(event)


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

    def wheelEvent(self, event):  # noqa: N802
        # Mausrad über Minimap → Editor scrollen — 2.6.27
        if self._editor is not None and apply_wheel_scroll(self._editor, event):
            return
        super().wheelEvent(event)


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
        self._tab_width = int(get_editor_tab_width())
        self._soft_tabs = bool(get_editor_soft_tabs())
        self._indent_guides = bool(get_editor_indent_guides())
        self._current_line_highlight = bool(get_editor_current_line_highlight())
        self._show_special = bool(get_editor_show_special_chars())
        self._bracket_match = bool(get_editor_bracket_match())
        self._bracket_auto_close = bool(get_editor_bracket_auto_close())
        self._clipboard_history: list[str] = []
        self._find_selections: list = []
        self._mark_selections: list = []
        self._char_hl_selections: list = []
        self._bracket_selections: list = []
        self._spell_selections: list = []
        self._current_line_selections: list = []
        self._line_bookmarks: set[int] = set()  # 0-basierte Blocknummern
        self._line_bookmark_order: list[int] = []  # Anzeige-/Persistenz-Reihenfolge (Blocks)
        self._line_bookmark_labels: dict[int, str] = {}  # Block → editierbares Label
        # Rich-Dokument (DOCX/HTML/Word-Suite) → erzwungener Umbruch + proportionale
        # Schrift; Seitenlayout (DTP-Preset) → Textspalte in Seitenbreite — 2.6.53
        self._rich_mode = False
        self._rich_base_font: QFont | None = None
        self._page_layout = None
        self._page_extra_px = 0
        self._page_top_px = 0
        self._page_bg_active = False
        self._base_autofill = bool(self.autoFillBackground())
        self._in_margin_update = False
        try:
            from instantlensdoc.core.editor_page_layout import EditorPageLayout

            self._page_layout = EditorPageLayout.from_settings()
        except Exception:
            self._page_layout = None
        self._line_number_area = _LineNumberArea(self)
        self._minimap_area = _MinimapArea(self)
        self.blockCountChanged.connect(self._update_side_areas)
        self.updateRequest.connect(self._update_line_number_area)
        self.updateRequest.connect(self._update_minimap_area)
        self.cursorPositionChanged.connect(self._update_bracket_match)
        self.cursorPositionChanged.connect(self._update_current_line_highlight)
        self.verticalScrollBar().valueChanged.connect(lambda _v: self._minimap_area.update())
        self._update_side_areas()
        self.set_line_numbers_visible(self._line_numbers)
        self.set_minimap_visible(self._minimap)
        self.set_soft_wrap(self._soft_wrap)
        self.set_tab_width(self._tab_width)
        self.set_indent_guides_visible(self._indent_guides)
        self.set_current_line_highlight(self._current_line_highlight)
        self.set_special_chars_visible(self._show_special)
        self._apply_page_layout()
        # Unbegrenzter Editor-Undo-Stack — 2.6.20
        try:
            self.document().setUndoLimit(0)
        except Exception:
            pass
        self._autocorrect_busy = False
        # Lokales Review / Track Changes — 2.6.21
        self._review_enabled = False
        self._review_path: str | None = None
        self._review_author = "local"
        self._review_prev_text: str | None = None
        self._review_busy = False
        self.textChanged.connect(self._on_review_text_changed)
        # Robustes Mausrad: Viewport-Filter + ScrollPerPixel-Feeling — 2.6.27
        try:
            self.viewport().installEventFilter(self)
        except Exception:
            pass
        try:
            self.setFocusPolicy(Qt.StrongFocus)
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        except Exception:
            pass

    def changeEvent(self, event):  # noqa: N802
        """Widget-Font-Wechsel (Ctrl+Rad-Zoom) darf im Rich-Modus nicht auf Monospace zurückfallen — 2.6.53."""
        super().changeEvent(event)
        try:
            from PySide6.QtCore import QEvent

            if event.type() == QEvent.Type.FontChange and bool(getattr(self, "_rich_mode", False)):
                base = getattr(self, "_rich_base_font", None)
                if base is not None:
                    f = QFont(base)
                    size = float(self.font().pointSizeF() or 0.0)
                    if size > 0:
                        f.setPointSizeF(size)
                    self.document().setDefaultFont(f)
        except Exception:
            pass

    def eventFilter(self, obj, event):  # noqa: N802
        """Viewport-Wheel abfangen (auch ohne Fokus) — 2.6.27."""
        try:
            from PySide6.QtCore import QEvent

            if obj is self.viewport() and event.type() == QEvent.Type.Wheel:
                # Ctrl+Wheel: Standard (Zoom/Font) an Qt durchreichen
                if event.modifiers() & Qt.ControlModifier:
                    return super().eventFilter(obj, event)
                if apply_wheel_scroll(self, event):
                    return True
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def wheelEvent(self, event):  # noqa: N802
        """Mausrad-/Trackpad-Scroll für Text- und Word-Suite-Dokumente — 2.6.27."""
        if event.modifiers() & Qt.ControlModifier:
            # Ctrl+Wheel: Qt-Default (falls Font-Zoom / System)
            super().wheelEvent(event)
            return
        if apply_wheel_scroll(self, event):
            return
        super().wheelEvent(event)

    def set_review_tracking(
        self,
        enabled: bool,
        *,
        path: str | None = None,
        author: str | None = None,
    ) -> None:
        """Review-Modus: Textänderungen als Sidecar protokollieren — 2.6.21."""
        self._review_enabled = bool(enabled)
        if path is not None:
            self._review_path = str(path)
        if author is not None:
            self._review_author = str(author or "local").strip() or "local"
        self._review_prev_text = self.toPlainText() if self._review_enabled else None

    def review_tracking_enabled(self) -> bool:
        return bool(self._review_enabled)

    def _on_review_text_changed(self) -> None:
        if not self._review_enabled or self._review_busy or not self._review_path:
            return
        after = self.toPlainText()
        before = self._review_prev_text
        if before is None:
            self._review_prev_text = after
            return
        if before == after:
            return
        self._review_busy = True
        try:
            from instantlensdoc.core.review import ReviewStore

            store = ReviewStore.for_doc(self._review_path, load=True)
            if store.enabled:
                store.record_diff(
                    before, after, author=self._review_author, save=True
                )
            self._review_prev_text = after
        except Exception:
            self._review_prev_text = after
        finally:
            self._review_busy = False

    def keyPressEvent(self, event):  # noqa: N802
        """Autokorrektur / Baustein-Kürzel nach Space/Satzzeichen — 2.6.20."""
        key = event.key()
        text = event.text()
        trigger = key in (
            Qt.Key_Space,
            Qt.Key_Return,
            Qt.Key_Enter,
            Qt.Key_Tab,
        ) or (text and text in ".,;:!?")
        super().keyPressEvent(event)
        if not trigger or self._autocorrect_busy:
            return
        try:
            from instantlensdoc.core.app_settings import (
                get_autocorrect_enabled,
                get_autocorrect_expand_snippets,
            )
            from instantlensdoc.core.autocorrect import (
                apply_autocorrect_at_cursor,
                effective_autocorrect_rules,
            )

            if not get_autocorrect_enabled():
                return
            rules = effective_autocorrect_rules()
            pos = self.textCursor().position()
            look = max(0, pos - 1)
            result = apply_autocorrect_at_cursor(
                self.toPlainText(),
                look,
                rules,
                expand_snippets=bool(get_autocorrect_expand_snippets()),
            )
            if not result:
                return
            self._autocorrect_busy = True
            try:
                c = self.textCursor()
                c.setPosition(int(result["start"]))
                c.setPosition(int(result["end"]), QTextCursor.KeepAnchor)
                c.insertText(str(result["new"]))
            finally:
                self._autocorrect_busy = False
        except Exception:
            self._autocorrect_busy = False

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
        """Breite der Minimap-Spalte; 0 wenn aus **oder** im Rich-Modus (DOCX/HTML).

        Eine Code-Minimap (Zeilen → Striche) ist für Fließtext unlesbar und stahl neben
        der DOCX-Spalte Platz — Rich-Dokumente zeigen sie nie — 2.6.54.
        """
        if not self._minimap or bool(getattr(self, "_rich_mode", False)):
            return 0
        return MINIMAP_WIDTH

    def minimap_effective(self) -> bool:
        """Minimap tatsächlich sichtbar (Einstellung an **und** Plaintext-Modus)."""
        return self.minimap_width() > 0

    def _sync_minimap_visibility(self) -> None:
        eff = self.minimap_effective()
        self._minimap_area.setVisible(eff)
        sb = self.verticalScrollBar()
        if eff:
            sb.setStyleSheet(
                f"QScrollBar:vertical {{ width: {MINIMAP_SCROLLBAR_WIDTH}px; min-width: {MINIMAP_SCROLLBAR_WIDTH}px; }}"
            )
        else:
            sb.setStyleSheet("")

    def set_line_numbers_visible(self, visible: bool) -> None:
        self._line_numbers = bool(visible)
        self._line_number_area.setVisible(self._line_numbers)
        self._update_side_areas()
        self.viewport().update()

    def line_numbers_visible(self) -> bool:
        return self._line_numbers

    def set_minimap_visible(self, visible: bool) -> None:
        """Optionale Minimap (Linien-Übersicht, nur Plaintext) + dickere Scrollbar."""
        self._minimap = bool(visible)
        self._sync_minimap_visibility()
        self._update_side_areas()
        self._minimap_area.update()
        self.viewport().update()

    def minimap_visible(self) -> bool:
        return bool(self._minimap)

    def set_soft_wrap(self, enabled: bool) -> None:
        """Zeilenumbruch am Fensterrand (Soft-Wrap) ein/aus.

        Rich-Dokumente (DOCX/HTML) brechen **immer** um — ein Absatz als eine
        kilometerlange Zeile mit horizontalem Scroll ist nie gewollt — 2.6.53.
        """
        self._soft_wrap = bool(enabled)
        if self._soft_wrap or bool(getattr(self, "_rich_mode", False)):
            self.setLineWrapMode(QPlainTextEdit.WidgetWidth)
            self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        else:
            self.setLineWrapMode(QPlainTextEdit.NoWrap)

    # ---- Rich-Modus / Seitenlayout — 2.6.53 --------------------------------
    def rich_mode(self) -> bool:
        return bool(getattr(self, "_rich_mode", False))

    def _default_rich_font(self) -> QFont:
        """Proportionale Standardschrift für Word-/DOCX-Dokumente (Calibri 11 → Fallback Sans)."""
        f = QFont("Calibri", 11)
        f.setStyleHint(QFont.SansSerif)
        return f

    def set_page_layout(self, layout) -> None:
        """Seitenlayout (``core.editor_page_layout.EditorPageLayout``) setzen + anwenden."""
        self._page_layout = layout
        self._apply_page_layout()

    def page_layout(self):
        return getattr(self, "_page_layout", None)

    def page_layout_active(self) -> bool:
        lay = getattr(self, "_page_layout", None)
        if lay is None:
            return False
        try:
            return bool(lay.applies_to(self.rich_mode()))
        except Exception:
            return False

    def page_column_width_px(self) -> int:
        """Aktuelle Textspaltenbreite (Viewport) in Pixel."""
        try:
            return int(self.viewport().width())
        except Exception:
            return 0

    def _apply_page_layout(self) -> None:
        from PySide6.QtCore import QSizeF
        from PySide6.QtGui import QPalette

        doc = self.document()
        active = self.page_layout_active()
        lay = getattr(self, "_page_layout", None)
        if active and lay is not None:
            dpi = float(self.logicalDpiX() or 96.0)
            w_px, h_px = lay.page_size_px(dpi)
            doc.setPageSize(QSizeF(w_px, h_px))
            if not self._page_bg_active:
                pal = QPalette(self.palette())
                pal.setColor(QPalette.Window, QColor("#D7DBE1"))
                self.setPalette(pal)
                self.setAutoFillBackground(True)
                self._page_bg_active = True
        else:
            doc.setPageSize(QSizeF(-1.0, -1.0))
            if self._page_bg_active:
                self.setPalette(QPalette())
                self.setAutoFillBackground(self._base_autofill)
                self._page_bg_active = False
        # Rich ↔ Plain gewechselt: Minimap folgt dem Modus (nie neben DOCX) — 2.6.54
        try:
            self._sync_minimap_visibility()
        except Exception:
            pass
        self._update_side_areas()
        self.viewport().update()

    def soft_wrap_enabled(self) -> bool:
        return bool(self._soft_wrap)

    def set_tab_width(self, width: int) -> None:
        """Tabulatorbreite in Zeichen (2 / 4 / 8)."""
        try:
            w = int(width)
        except (TypeError, ValueError):
            w = 4
        if w not in (2, 4, 8):
            w = 4
        self._tab_width = w
        space_w = max(1, self.fontMetrics().horizontalAdvance(" "))
        self.setTabStopDistance(float(space_w * w))

    def tab_width(self) -> int:
        return int(self._tab_width)

    def set_soft_tabs(self, enabled: bool) -> None:
        """Soft-Tabs (Leerzeichen) vs. echte Tabulatorzeichen."""
        self._soft_tabs = bool(enabled)

    def soft_tabs_enabled(self) -> bool:
        return bool(self._soft_tabs)

    def set_indent_guides_visible(self, visible: bool) -> None:
        """Vertikale Einrückungs-Guides an Tab-Stops ein-/ausblenden."""
        self._indent_guides = bool(visible)
        self.viewport().update()

    def indent_guides_visible(self) -> bool:
        return bool(self._indent_guides)

    def set_current_line_highlight(self, enabled: bool) -> None:
        """Aktuelle Zeile farblich hervorheben ein-/ausschalten."""
        self._current_line_highlight = bool(enabled)
        self._update_current_line_highlight()

    def current_line_highlight_enabled(self) -> bool:
        return bool(self._current_line_highlight)

    def _update_current_line_highlight(self) -> None:
        self._current_line_selections = []
        if self._current_line_highlight:
            sel = QTextEdit.ExtraSelection()
            fmt = QTextCharFormat()
            bg = QColor("#FFF3B0")
            bg.setAlpha(110)
            fmt.setBackground(bg)
            fmt.setProperty(QTextCharFormat.FullWidthSelection, True)
            sel.format = fmt
            sel.cursor = self.textCursor()
            sel.cursor.clearSelection()
            self._current_line_selections = [sel]
        self._apply_extra_selections()

    def paintEvent(self, event):  # noqa: N802
        super().paintEvent(event)
        if self._indent_guides:
            self._paint_indent_guides(event)

    def _paint_indent_guides(self, event) -> None:
        """Vertikale Linien bei Tab-Stops für führende Einrückung."""
        painter = QPainter(self.viewport())
        try:
            color = QColor("#B0B8C0")
            color.setAlpha(110)
            from PySide6.QtGui import QPen

            pen = QPen(color, 1, Qt.DotLine)
            painter.setPen(pen)
            space_w = max(1, self.fontMetrics().horizontalAdvance(" "))
            tab_w = max(1, int(self._tab_width)) * space_w
            if tab_w <= 0:
                return
            offset = self.contentOffset()
            block = self.firstVisibleBlock()
            viewport_bottom = self.viewport().height()
            while block.isValid():
                geom = self.blockBoundingGeometry(block).translated(offset)
                top = int(geom.top())
                if top > viewport_bottom:
                    break
                bottom = int(geom.bottom())
                if bottom >= 0:
                    text = block.text()
                    # Führende Einrückung in Spalten (Tabs + Spaces)
                    col = 0
                    for ch in text:
                        if ch == "\t":
                            col = ((col // max(1, int(self._tab_width))) + 1) * max(
                                1, int(self._tab_width)
                            )
                        elif ch == " ":
                            col += 1
                        else:
                            break
                    levels = col // max(1, int(self._tab_width))
                    for lvl in range(1, levels + 1):
                        x = int(lvl * tab_w) + int(offset.x())
                        if 0 <= x < self.viewport().width():
                            painter.drawLine(x, max(0, top), x, min(viewport_bottom, bottom))
                block = block.next()
        finally:
            painter.end()

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
            list(getattr(self, "_current_line_selections", []) or [])
            + list(getattr(self, "_char_hl_selections", []) or [])
            + list(self._find_selections)
            + list(self._mark_selections)
            + list(self._bracket_selections)
            + list(getattr(self, "_spell_selections", []) or [])
        )
        self.setExtraSelections(merged)

    def _sync_char_background_extras(self) -> None:
        """QPlainTextEdit zeichnet Char-Background nicht — ExtraSelections spiegeln setBackground."""
        sels: list = []
        doc = self.document()
        block = doc.begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                frag = it.fragment()
                if frag.isValid() and frag.length() > 0:
                    f = frag.charFormat()
                    brush = f.background()
                    if brush.style() != Qt.NoBrush:
                        sel = QTextEdit.ExtraSelection()
                        c = QTextCursor(doc)
                        c.setPosition(frag.position())
                        c.setPosition(
                            frag.position() + frag.length(), QTextCursor.KeepAnchor
                        )
                        fmt = QTextCharFormat()
                        fmt.setBackground(brush)
                        sel.cursor = c
                        sel.format = fmt
                        sels.append(sel)
                it += 1
            block = block.next()
        self._char_hl_selections = sels
        self._apply_extra_selections()

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
            return False
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
        if getattr(self, "_in_margin_update", False):
            return
        self._in_margin_update = True
        try:
            left = self.line_number_area_width()
            right = self.minimap_width()
            extra = 0
            top = 0
            # Seitenlayout: Textspalte in Seitenbreite zentrieren — 2.6.53
            lay = getattr(self, "_page_layout", None)
            if lay is not None and self.page_layout_active():
                dpi = float(self.logicalDpiX() or 96.0)
                col = int(round(lay.text_width_px(dpi)))
                avail = int(self.contentsRect().width()) - left - right
                if avail > 0 and col < avail:
                    extra = max(0, (avail - col) // 2)
                m_top = lay.margins_px(dpi)[0]
                top = int(min(max(0.0, m_top), 48.0))
            self._page_extra_px = int(extra)
            self._page_top_px = int(top)
            before_w = int(self.viewport().width())
            self.setViewportMargins(left + extra, top, right + extra, 0)
            after_w = int(self.viewport().width())
            if after_w != before_w and after_w > 0:
                # Qt liefert beim Rand-Wechsel während show()/resizeEvent keinen
                # Resize mit neuer Breite → QPlainTextDocumentLayout behält die alte
                # Textbreite (DOCX überbreit, horizontaler Scroll). Explizit nachziehen.
                self._relayout_document_width(after_w, before_w)
            self._layout_side_areas()
        finally:
            self._in_margin_update = False

    def _relayout_document_width(self, width_px: int, old_width_px: int = -1) -> None:
        """``QPlainTextEdit::resizeEvent`` mit geänderter Breite erzwingen.

        PySide6 exportiert ``QPlainTextDocumentLayout::setTextWidth`` nicht; ein
        synthetischer Resize mit abweichender alter Breite löst Qt-intern
        ``relayoutDocument()`` aus (Textbreite = Viewport).
        """
        try:
            from PySide6.QtCore import QSize
            from PySide6.QtGui import QResizeEvent

            vp = self.viewport()
            h = max(1, int(vp.height()))
            old_w = int(old_width_px) if int(old_width_px) >= 0 and int(old_width_px) != int(width_px) else -1
            QApplication.sendEvent(vp, QResizeEvent(QSize(int(width_px), h), QSize(old_w, h)))
        except Exception:
            pass

    def _update_line_number_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_side_areas()

    def _update_minimap_area(self, rect: QRect, dy: int) -> None:
        if not self.minimap_effective():
            return
        if dy:
            self._minimap_area.scroll(0, dy)
        else:
            self._minimap_area.update()
        if rect.contains(self.viewport().rect()):
            self._update_side_areas()

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        if getattr(self, "_page_layout", None) is not None and self.page_layout_active():
            # Spaltenbreite hängt von der Fensterbreite ab → Ränder neu berechnen
            self._update_side_areas()
        else:
            self._layout_side_areas()

    def _layout_side_areas(self) -> None:
        cr = self.contentsRect()
        ln_w = self.line_number_area_width()
        mm_w = self.minimap_width()
        extra = int(getattr(self, "_page_extra_px", 0) or 0)
        top = int(getattr(self, "_page_top_px", 0) or 0)
        self._line_number_area.setGeometry(
            QRect(cr.left() + extra, cr.top() + top, ln_w, cr.height() - top)
        )
        self._minimap_area.setGeometry(
            QRect(cr.right() - mm_w - extra + 1, cr.top() + top, mm_w, cr.height() - top)
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
        if not self.minimap_effective():
            return
        painter = QPainter(self._minimap_area)
        # Dezenter als bis 2.6.53: Hintergrund wie Viewport, Striche hell, sichtbarer
        # Bereich nur als zarter Rahmen — Übersicht ohne „graue Balken“-Wand
        painter.fillRect(event.rect(), self.palette().base().color())
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
        painter.fillRect(0, vis_top, w, vis_h, QColor(70, 130, 180, 28))
        painter.setPen(QColor(70, 130, 180, 90))
        painter.drawRect(0, vis_top, w - 1, vis_h)
        # Linien-Übersicht: Inhalt → Strichbreite (max. 1 px hoch, hellgrau)
        painter.setPen(Qt.NoPen)
        bar_color = QColor("#B4BEC8")
        block = doc.firstBlock()
        i = 0
        while block.isValid():
            text = block.text().rstrip()
            if text:
                dens = min(1.0, len(text) / 80.0)
                bar_w = max(2, int((w - 8) * dens))
                y = int(i * h / n)
                yh = max(1, min(2, int(h / n)))
                painter.fillRect(4, y, bar_w, yh, bar_color)
            block = block.next()
            i += 1

    def minimap_goto_y(self, y: float) -> None:
        """Minimap-Klick → relative Dokumentposition."""
        if not self.minimap_effective():
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
        self._apply_extra_selections()

    def setPlainText(self, text: str) -> None:  # noqa: N802
        """Plaintext laden ohne Zeichenformat-Erbe aus dem vorherigen Dokument.

        ``QWidgetTextControl.setContent`` wendet das zuletzt aktive Cursor-
        Zeichenformat auf den gesamten neuen Text an — nach einem fetten/
        unterstrichenen DOCX wäre die nächste TXT-Datei komplett fett — 2.6.52.
        """
        try:
            self.setCurrentCharFormat(QTextCharFormat())
        except Exception:
            pass
        # Zurück in den Plaintext-Modus: Monospace-Standardschrift, Soft-Wrap
        # wieder laut Einstellung, Seitenlayout nur falls scope == all — 2.6.53
        was_rich = bool(getattr(self, "_rich_mode", False))
        self._rich_mode = False
        self._rich_base_font = None
        if was_rich:
            try:
                self.document().setDefaultFont(self.font())
            except Exception:
                pass
        super().setPlainText(text)
        self._char_hl_selections = []
        try:
            self.setCurrentCharFormat(QTextCharFormat())
        except Exception:
            pass
        self._apply_extra_selections()
        if was_rich:
            self.set_soft_wrap(self._soft_wrap)
            try:
                from instantlensdoc.core.app_settings import get_editor_show_special_chars

                self.set_special_chars_visible(bool(get_editor_show_special_chars()))
            except Exception:
                pass
            try:
                self.document().setDocumentMargin(4.0)
            except Exception:
                pass
            self._apply_page_layout()

    def clear_spelling(self) -> None:
        """Nur Rechtschreibmarkierungen entfernen."""
        self._spell_selections = []
        self._apply_extra_selections()

    def check_spelling(self, dict_path: str | None = None) -> int:
        """
        Wortliste + Builtin der UI-Sprache; unbekannte Wörter wellig markieren.
        Tooltip zeigt Korrekturvorschläge. Rückgabe: Anzahl Markierungen — 2.6.20.
        """
        from pathlib import Path

        from instantlensdoc.core.app_settings import (
            get_spellcheck_dict_path,
            get_spellcheck_grammar_hints,
            get_spellcheck_use_builtin,
        )
        from instantlensdoc.core.spellcheck import spellcheck_with_suggestions

        path = (dict_path or get_spellcheck_dict_path() or "").strip()
        use_builtin = bool(get_spellcheck_use_builtin())
        if path and not Path(path).is_file():
            self.clear_spelling()
            raise FileNotFoundError(f"Wörterbuch nicht gefunden: {path}")
        if not path and not use_builtin:
            self.clear_spelling()
            raise FileNotFoundError(
                "Kein Wörterbuch-Pfad gesetzt und Builtin-Wörterbuch deaktiviert"
            )
        text = self.toPlainText()
        result = spellcheck_with_suggestions(
            text,
            path or None,
            include_builtin=use_builtin,
            include_grammar=bool(get_spellcheck_grammar_hints()),
        )
        self._last_spell_result = result
        sel_cur = self.textCursor()
        sel_start = sel_end = None
        if sel_cur.hasSelection():
            sel_start = min(sel_cur.selectionStart(), sel_cur.selectionEnd())
            sel_end = max(sel_cur.selectionStart(), sel_cur.selectionEnd())

        def _in_scope(start: int, end: int) -> bool:
            if sel_start is None or sel_end is None:
                return True
            return not (end <= sel_start or start >= sel_end)

        selections: list = []
        applied_unknown = 0
        for item in result.get("unknown") or []:
            start = int(item["start"])
            end = int(item["end"])
            if not _in_scope(start, end):
                continue
            word = str(item.get("word") or "")
            sugg = item.get("suggestions") or []
            tip = f"Unbekannt: {word}"
            if sugg:
                tip += " → " + ", ".join(str(s) for s in sugg[:5])
            fmt = QTextCharFormat()
            fmt.setUnderlineColor(QColor("#C0392B"))
            fmt.setUnderlineStyle(QTextCharFormat.WaveUnderline)
            fmt.setToolTip(tip)
            sel = QTextEdit.ExtraSelection()
            c = QTextCursor(self.document())
            c.setPosition(start)
            c.setPosition(end, QTextCursor.KeepAnchor)
            sel.cursor = c
            sel.format = fmt
            selections.append(sel)
            applied_unknown += 1
        # Grammar: gestrichelte blaue Unterstreichung
        for gh in result.get("grammar") or []:
            start = int(gh.get("start", 0))
            end = int(gh.get("end", start))
            if end <= start or not _in_scope(start, end):
                continue
            fmt = QTextCharFormat()
            fmt.setUnderlineColor(QColor("#2471A3"))
            fmt.setUnderlineStyle(QTextCharFormat.DashUnderline)
            tip = str(gh.get("message") or "Grammatik")
            if gh.get("suggestion"):
                tip += f" → {gh['suggestion']}"
            fmt.setToolTip(tip)
            sel = QTextEdit.ExtraSelection()
            c = QTextCursor(self.document())
            c.setPosition(start)
            c.setPosition(end, QTextCursor.KeepAnchor)
            sel.cursor = c
            sel.format = fmt
            selections.append(sel)
        self._spell_selections = selections
        self._apply_extra_selections()
        if sel_start is not None:
            return applied_unknown
        return int(result.get("count") or 0)

    def last_spell_result(self) -> dict:
        """Letztes spellcheck_with_suggestions-Ergebnis — 2.6.20."""
        return dict(getattr(self, "_last_spell_result", None) or {})

    def apply_spell_suggestion(self, start: int, end: int, replacement: str) -> bool:
        """Ersetzt Span durch Vorschlag (ein Undo-Schritt)."""
        if start < 0 or end <= start:
            return False
        c = self.textCursor()
        c.setPosition(int(start))
        c.setPosition(int(end), c.KeepAnchor)
        c.insertText(str(replacement))
        return True

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

    def wrap_selection_markers(self, left: str, right: str | None = None) -> bool:
        """Auswahl mit Markern umschließen (Markdown **/*/_ ) — optional, nicht Toolbar."""
        right = left if right is None else right
        cur = self.textCursor()
        if not cur.hasSelection():
            # Wort unter Cursor
            cur.select(QTextCursor.WordUnderCursor)
        if not cur.hasSelection():
            cur.insertText(f"{left}{right}")
            cur.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, len(right))
            self.setTextCursor(cur)
            return True
        selected = cur.selectedText().replace("\u2029", "\n")
        # Toggle: bereits umschlossen → Marker entfernen
        if (
            selected.startswith(left)
            and selected.endswith(right)
            and len(selected) >= len(left) + len(right)
        ):
            inner = selected[len(left) : len(selected) - len(right)]
            cur.insertText(inner)
        else:
            cur.insertText(f"{left}{selected}{right}")
        self.setTextCursor(cur)
        return True

    def set_rich_html(self, html: str, base_font: QFont | None = None) -> None:
        """HTML mit Zeichenformaten in das Dokument laden (DOCX/Word-Suite) — 2.6.49.

        2.6.53: Rich-Dokumente brechen immer am Spaltenrand um (``WidgetWidth``),
        bekommen eine proportionale Standardschrift (DOCX-Normal-Stil bzw. Calibri 11
        statt Editor-Monospace) und — wenn aktiv — das Seitenlayout (Textspalte in
        Seitenbreite, ``QTextDocument.pageSize``).
        """
        self._rich_mode = True
        self.set_soft_wrap(self._soft_wrap)  # erzwingt WidgetWidth im Rich-Modus
        try:
            # Word-Suite/DOCX: keine ¶ · Tabs als sichtbare Steuerzeichen
            self.set_special_chars_visible(False)
        except Exception:
            pass
        try:
            self.setCurrentCharFormat(QTextCharFormat())
        except Exception:
            pass
        doc = self.document()
        font = QFont(base_font) if base_font is not None else self._default_rich_font()
        if font.pointSizeF() <= 0 and font.pixelSize() <= 0:
            font.setPointSize(11)
        self._rich_base_font = QFont(font)
        # Vor setHtml: Importer leitet Standardgrößen vom Dokument-Default ab
        doc.setDefaultFont(font)
        try:
            from instantlensdoc.core.ocr_word_suite import sanitize_ocr_html

            html = sanitize_ocr_html(html or "")
        except Exception:
            html = html or ""
        doc.setHtml(html or "")
        doc.setDefaultFont(font)
        try:
            doc.setDocumentMargin(8.0)
        except Exception:
            pass
        try:
            self.setCurrentCharFormat(QTextCharFormat())
        except Exception:
            pass
        self._apply_page_layout()
        self._sync_char_background_extras()

    def to_rich_html(self) -> str:
        """Aktuelles Dokument als HTML (Bold/Italic/Underline erhalten)."""
        return self.document().toHtml()

    def _selection_or_word_cursor(self) -> QTextCursor:
        """Nur noch intern: Wort unter Cursor, wenn nichts markiert ist."""
        cur = self.textCursor()
        if not cur.hasSelection():
            cur.select(QTextCursor.WordUnderCursor)
        return cur

    def selection_or_document_cursor(self) -> QTextCursor:
        """Auswahl, sonst gesamtes Dokument — Word-Suite/OCR: Tool ohne Selektion = global."""
        cur = QTextCursor(self.textCursor())
        if cur.hasSelection():
            return cur
        wrap = QTextCursor(self.document())
        wrap.select(QTextCursor.Document)
        return wrap

    def _selected_or_document_plain(self) -> tuple[QTextCursor, str, bool]:
        """``(cursor, plain, whole_document)`` — Selektion oder gesamter Editortext."""
        cur = self.textCursor()
        if cur.hasSelection():
            text = cur.selectedText().replace("\u2029", "\n")
            return cur, text, False
        wrap = QTextCursor(self.document())
        wrap.select(QTextCursor.Document)
        return wrap, self.toPlainText(), True

    def _replace_selection_or_document_text(self, new_text: str) -> bool:
        """Auswahl ersetzen, ohne Auswahl den gesamten Dokumenttext — ein Undo-Schritt."""
        _cur, old, whole = self._selected_or_document_plain()
        if new_text == old:
            return False
        if whole:
            self._replace_all_text_undoable(new_text)
            return True
        start = _cur.selectionStart()
        _cur.beginEditBlock()
        try:
            _cur.insertText(new_text)
        finally:
            _cur.endEditBlock()
        restored = QTextCursor(self.document())
        restored.setPosition(start)
        restored.setPosition(start + len(new_text), QTextCursor.KeepAnchor)
        self.setTextCursor(restored)
        return True

    def _global_format_cursor(self) -> tuple[QTextCursor, QTextCursor, bool]:
        """Auswahl, sonst ganzes Dokument. Caret bleibt erhalten (expanded=True)."""
        restore = QTextCursor(self.textCursor())
        work = QTextCursor(restore)
        expanded = False
        if not work.hasSelection():
            work.select(QTextCursor.Document)
            expanded = True
        return work, restore, expanded

    def _restore_format_cursor(
        self, work: QTextCursor, restore: QTextCursor, expanded: bool
    ) -> None:
        if expanded:
            self.setTextCursor(restore)
        else:
            self.setTextCursor(work)

    def _selection_probe_format(self, cur: QTextCursor) -> QTextCharFormat:
        """Zeichenformat am Anfang der Auswahl (oder CurrentFormat ohne Auswahl)."""
        if not cur.hasSelection():
            return QTextCharFormat(self.currentCharFormat())
        start = min(cur.selectionStart(), cur.selectionEnd())
        end = max(cur.selectionStart(), cur.selectionEnd())
        probe = QTextCursor(self.document())
        probe.setPosition(start)
        if end > start:
            probe.setPosition(min(start + 1, end), QTextCursor.KeepAnchor)
            return QTextCharFormat(probe.charFormat())
        return QTextCharFormat(self.currentCharFormat())

    def _ensure_rich_mode(self) -> None:
        """Zeichen-/Absatzformate sichtbar halten (auch nach Neu/OCR-Text) — 2.6.55."""
        if bool(getattr(self, "_rich_mode", False)):
            return
        self._rich_mode = True
        try:
            if getattr(self, "_rich_base_font", None) is None:
                self._rich_base_font = self._default_rich_font()
            self.document().setDefaultFont(self._rich_base_font)
            self.set_soft_wrap(self._soft_wrap)
        except Exception:
            pass

    def _iter_selected_blocks(self, *, empty_means_document: bool = True, all_blocks: bool = False):
        """Blöcke der Auswahl; ohne Auswahl das ganze Dokument (außer empty_means_document=False)."""
        cur = self.textCursor()
        doc = self.document()
        if all_blocks or (empty_means_document and not cur.hasSelection()):
            block = doc.firstBlock()
            while block.isValid():
                yield block
                block = block.next()
            return
        if cur.hasSelection():
            start = min(cur.selectionStart(), cur.selectionEnd())
            end = max(cur.selectionStart(), cur.selectionEnd())
            if end > start:
                end_block = doc.findBlock(end - 1)
            else:
                end_block = doc.findBlock(end)
        else:
            start = cur.position()
            end_block = doc.findBlock(start)
        block = doc.findBlock(start)
        while block.isValid() and block.blockNumber() <= end_block.blockNumber():
            yield block
            block = block.next()

    def _apply_to_selected_blocks(
        self, mutator, *, empty_means_document: bool = True, all_blocks: bool = False
    ) -> int:
        """``mutator(QTextBlockFormat)`` auf Auswahl-Blöcke bzw. das ganze Dokument."""
        self._ensure_rich_mode()
        n = 0
        cur = self.textCursor()
        cur.beginEditBlock()
        try:
            for block in self._iter_selected_blocks(
                empty_means_document=empty_means_document, all_blocks=all_blocks
            ):
                bcur = QTextCursor(block)
                fmt = QTextBlockFormat(block.blockFormat())
                mutator(fmt)
                bcur.setBlockFormat(fmt)
                n += 1
        finally:
            cur.endEditBlock()
        return n

    def toggle_char_format(
        self,
        *,
        bold: bool | None = None,
        italic: bool | None = None,
        underline: bool | None = None,
        strike: bool | None = None,
    ) -> bool:
        """QTextCharFormat auf Auswahl toggeln, ohne Auswahl auf das ganze Dokument."""
        self._ensure_rich_mode()
        work, restore, expanded = self._global_format_cursor()
        probe_src = restore if expanded else work
        probe = self._selection_probe_format(probe_src)
        fmt = QTextCharFormat()
        if bold is not None:
            make_on = bold
            if bold is True:
                # Toggle: wenn bereits fett → aus
                make_on = probe.fontWeight() < QFont.Bold
            fmt.setFontWeight(QFont.Bold if make_on else QFont.Normal)
        if italic is not None:
            make_on = italic
            if italic is True:
                make_on = not bool(probe.fontItalic())
            fmt.setFontItalic(bool(make_on))
        if underline is not None:
            make_on = underline
            if underline is True:
                make_on = not bool(probe.fontUnderline())
            # Unterstreicht Buchstaben inkl. Selection — nicht nur Whitespace
            fmt.setFontUnderline(bool(make_on))
        if strike is not None:
            make_on = strike
            if strike is True:
                make_on = not bool(probe.fontStrikeOut())
            fmt.setFontStrikeOut(bool(make_on))
        work.beginEditBlock()
        try:
            work.mergeCharFormat(fmt)
            if expanded:
                self.mergeCurrentCharFormat(fmt)
            else:
                self.setTextCursor(work)
                self.mergeCurrentCharFormat(fmt)
        finally:
            work.endEditBlock()
        self._restore_format_cursor(work, restore, expanded)
        return True

    def toggle_bold_selection(self) -> bool:
        """Fett via QTextCharFormat (kein ``**``) — 2.6.49."""
        return self.toggle_char_format(bold=True)

    def toggle_italic_selection(self) -> bool:
        """Kursiv via QTextCharFormat (kein ``*``) — 2.6.49."""
        return self.toggle_char_format(italic=True)

    def toggle_underline_selection(self) -> bool:
        """Unterstrichen via QTextCharFormat (kein ``__``) — 2.6.49."""
        return self.toggle_char_format(underline=True)

    def toggle_strike_selection(self) -> bool:
        """Durchgestrichen via QTextCharFormat — 2.6.55."""
        return self.toggle_char_format(strike=True)

    def selection_font_bold(self) -> bool:
        return self._selection_probe_format(self.textCursor()).fontWeight() >= QFont.Bold

    def selection_font_italic(self) -> bool:
        return bool(self._selection_probe_format(self.textCursor()).fontItalic())

    def selection_font_underline(self) -> bool:
        return bool(self._selection_probe_format(self.textCursor()).fontUnderline())

    def selection_font_strike(self) -> bool:
        return bool(self._selection_probe_format(self.textCursor()).fontStrikeOut())

    def apply_font_family(self, family: str) -> bool:
        """Schriftart auf Auswahl bzw. ganzes Dokument."""
        name = (family or "").strip()
        if not name:
            return False
        self._ensure_rich_mode()
        fmt = QTextCharFormat()
        try:
            fmt.setFontFamilies([name])
        except Exception:
            fmt.setFontFamily(name)
        return self._merge_char_format(fmt)

    def apply_qfont(self, font: QFont) -> bool:
        """QFont (QFontDialog/QFontDatabase) auf Auswahl oder ganzes Dokument mergen."""
        if font is None or not font.family():
            return False
        self._ensure_rich_mode()
        fmt = QTextCharFormat()
        fmt.setFont(font)
        return self._merge_char_format(fmt)

    def apply_font_size(self, point_size: float) -> bool:
        """Schriftgröße in Punkt auf Auswahl bzw. Cursor — 2.6.55."""
        size = float(point_size)
        if size <= 0:
            return False
        self._ensure_rich_mode()
        fmt = QTextCharFormat()
        fmt.setFontPointSize(size)
        return self._merge_char_format(fmt)

    def apply_font_color(self, color: str | QColor) -> bool:
        """Schriftfarbe auf Auswahl bzw. Cursor — 2.6.55."""
        qcolor = color if isinstance(color, QColor) else QColor(str(color or ""))
        if not qcolor.isValid():
            return False
        self._ensure_rich_mode()
        fmt = QTextCharFormat()
        fmt.setForeground(QBrush(qcolor))
        return self._merge_char_format(fmt)

    def apply_highlight_color(self, color: str | QColor = "#FFE066") -> bool:
        """Textmarker-Hintergrund setzen (kein Toggle) — 2.6.55."""
        qcolor = color if isinstance(color, QColor) else QColor(str(color or self.HIGHLIGHT_COLOR))
        if not qcolor.isValid():
            qcolor = QColor(self.HIGHLIGHT_COLOR)
        self._ensure_rich_mode()
        fmt = QTextCharFormat()
        fmt.setBackground(QBrush(qcolor))
        ok = self._merge_char_format(fmt)
        self._sync_char_background_extras()
        return ok

    def _merge_char_format(self, fmt: QTextCharFormat) -> bool:
        work, restore, expanded = self._global_format_cursor()
        work.beginEditBlock()
        try:
            work.mergeCharFormat(fmt)
            if expanded:
                self.mergeCurrentCharFormat(fmt)
            else:
                self.setTextCursor(work)
                self.mergeCurrentCharFormat(fmt)
        finally:
            work.endEditBlock()
        self._restore_format_cursor(work, restore, expanded)
        return True

    def clear_formatting(self) -> bool:
        """Zeichen- und Absatzformat: Auswahl, sonst ganzes Dokument."""
        self._ensure_rich_mode()
        work, restore, expanded = self._global_format_cursor()
        base = QFont(self.document().defaultFont())
        char = QTextCharFormat()
        char.setFont(base)
        char.setFontWeight(QFont.Normal)
        char.setFontItalic(False)
        char.setFontUnderline(False)
        char.setFontStrikeOut(False)
        char.setAnchor(False)
        char.setAnchorHref("")
        char.setForeground(QBrush())
        char.setBackground(QBrush(Qt.NoBrush))
        work.beginEditBlock()
        try:
            work.setCharFormat(char)
            if not expanded:
                self.setTextCursor(work)
            self.setCurrentCharFormat(char)

            def _reset(fmt: QTextBlockFormat) -> None:
                fmt.setAlignment(Qt.AlignLeft | Qt.AlignAbsolute)
                fmt.setLeftMargin(0.0)
                fmt.setRightMargin(0.0)
                fmt.setTextIndent(0.0)
                fmt.setTopMargin(0.0)
                fmt.setBottomMargin(0.0)
                self._set_block_line_height(fmt, 1.0)

            self._apply_to_selected_blocks(_reset)
        finally:
            work.endEditBlock()
        self._restore_format_cursor(work, restore, expanded)
        self._sync_char_background_extras()
        return True

    @staticmethod
    def _set_block_line_height(fmt: QTextBlockFormat, factor: float) -> None:
        pct = max(50.0, float(factor) * 100.0)
        try:
            fmt.setLineHeight(pct, QTextBlockFormat.ProportionalHeight)
        except Exception:
            try:
                kind = int(QTextBlockFormat.LineHeightTypes.ProportionalHeight)
                fmt.setLineHeight(pct, kind)
            except Exception:
                fmt.setBottomMargin(max(0.0, (float(factor) - 1.0) * 12.0))

    def current_block_alignment(self) -> str:
        align = int(self.textCursor().blockFormat().alignment())
        if align & int(Qt.AlignJustify):
            return "justify"
        if align & int(Qt.AlignHCenter):
            return "center"
        if align & int(Qt.AlignRight):
            return "right"
        return "left"

    def _replace_all_text_undoable(self, new_text: str) -> None:
        """Gesamten Text ersetzen als **ein** Undo-Schritt — ohne den Verlauf zu löschen.

        ``setPlainText``/``setHtml`` setzen den Undo/Redo-Stack von ``QTextDocument``
        zurück — nach „Absatz zentrieren“ oder „Tabelle einfügen“ war Ctrl+Z tot.
        Hier: Alles auswählen + ``insertText`` in einem Edit-Block; Cursorposition und
        Scroll bleiben soweit möglich erhalten — 2.6.54.
        """
        text = str(new_text if new_text is not None else "")
        if text == self.toPlainText():
            return
        old_pos = self.textCursor().position()
        vbar = self.verticalScrollBar()
        old_scroll = vbar.value()
        cur = self.textCursor()
        cur.beginEditBlock()
        try:
            cur.select(QTextCursor.Document)
            cur.insertText(text)
        finally:
            cur.endEditBlock()
        cur.setPosition(max(0, min(old_pos, len(text))))
        self.setTextCursor(cur)
        try:
            vbar.setValue(min(old_scroll, vbar.maximum()))
        except Exception:
            pass

    def apply_auto_format(self) -> int:
        """Automatische Formatierung (Heading/Body/Quote) — Auswahl oder gesamtes Dokument."""
        from ild_pdf.auto_format import auto_format_text

        _cur, text, _whole = self._selected_or_document_plain()
        result = auto_format_text(text)
        if result.text != text:
            self._replace_selection_or_document_text(result.text)
        return int(result.changed_lines)

    def current_paragraph_index(self) -> int:
        """0-basierter Blockindex unter dem Cursor."""
        return max(0, int(self.textCursor().blockNumber()))

    def set_paragraph_alignment(self, alignment: str, *, all_paragraphs: bool = False) -> bool:
        """Absatzausrichtung visuell via QTextBlockFormat — 2.6.55."""
        mapping = {
            "left": Qt.AlignLeft | Qt.AlignAbsolute,
            "center": Qt.AlignHCenter,
            "right": Qt.AlignRight | Qt.AlignAbsolute,
            "justify": Qt.AlignJustify,
        }
        align = mapping.get((alignment or "left").lower().strip())
        if align is None:
            return False

        def _mut(fmt: QTextBlockFormat) -> None:
            fmt.setAlignment(align)

        return self._apply_to_selected_blocks(_mut, all_blocks=bool(all_paragraphs)) > 0

    def set_paragraph_spacing(
        self,
        *,
        line_spacing: float | None = None,
        space_before_pt: float | None = None,
        space_after_pt: float | None = None,
        all_paragraphs: bool = False,
    ) -> bool:
        """Zeilen-/Absatzabstand via QTextBlockFormat — 2.6.55."""
        def _mut(fmt: QTextBlockFormat) -> None:
            if line_spacing is not None:
                self._set_block_line_height(fmt, float(line_spacing))
            if space_before_pt is not None:
                fmt.setTopMargin(max(0.0, float(space_before_pt)))
            if space_after_pt is not None:
                fmt.setBottomMargin(max(0.0, float(space_after_pt)))

        if line_spacing is None and space_before_pt is None and space_after_pt is None:
            return False
        return self._apply_to_selected_blocks(_mut, all_blocks=bool(all_paragraphs)) > 0

    def apply_style_paragraph(self, style_id: str = "body") -> bool:
        """Absatzstil (Normal/Überschrift/Zitat) als QText-Formate — 2.6.55."""
        sid = (style_id or "body").strip().lower()
        presets = {
            "body": {"size": 11.0, "bold": False, "italic": False, "align": "left", "indent": 0.0},
            "normal": {"size": 11.0, "bold": False, "italic": False, "align": "left", "indent": 0.0},
            "h1": {"size": 18.0, "bold": True, "italic": False, "align": "left", "indent": 0.0},
            "heading1": {"size": 18.0, "bold": True, "italic": False, "align": "left", "indent": 0.0},
            "h2": {"size": 14.0, "bold": True, "italic": False, "align": "left", "indent": 0.0},
            "heading2": {"size": 14.0, "bold": True, "italic": False, "align": "left", "indent": 0.0},
            "h3": {"size": 12.0, "bold": True, "italic": True, "align": "left", "indent": 0.0},
            "heading3": {"size": 12.0, "bold": True, "italic": True, "align": "left", "indent": 0.0},
            "quote": {"size": 11.0, "bold": False, "italic": True, "align": "left", "indent": 36.0},
            "zitat": {"size": 11.0, "bold": False, "italic": True, "align": "left", "indent": 36.0},
        }
        spec = presets.get(sid, presets["body"])
        self._ensure_rich_mode()
        char = QTextCharFormat()
        char.setFontPointSize(float(spec["size"]))
        char.setFontWeight(QFont.Bold if spec["bold"] else QFont.Normal)
        char.setFontItalic(bool(spec["italic"]))
        if sid in ("quote", "zitat"):
            char.setForeground(QBrush(QColor("#4B5563")))
        align_name = str(spec["align"])
        indent = float(spec["indent"])
        work, restore, expanded = self._global_format_cursor()
        work.beginEditBlock()
        try:
            work.mergeCharFormat(char)
            if not expanded:
                self.setTextCursor(work)

            def _mut(fmt: QTextBlockFormat) -> None:
                mapping = {
                    "left": Qt.AlignLeft | Qt.AlignAbsolute,
                    "center": Qt.AlignHCenter,
                    "right": Qt.AlignRight | Qt.AlignAbsolute,
                    "justify": Qt.AlignJustify,
                }
                fmt.setAlignment(mapping.get(align_name, Qt.AlignLeft))
                fmt.setLeftMargin(indent)

            self._apply_to_selected_blocks(_mut)
        finally:
            work.endEditBlock()
        self._restore_format_cursor(work, restore, expanded)
        return True

    def apply_typography(
        self,
        *,
        tracking: float | None = None,
        kerning: float | None = None,
        leading: float | None = None,
        drop_cap_lines: int | None = None,
        drop_cap_chars: int | None = None,
        char_style_id: str | None = None,
        all_paragraphs: bool = False,
    ) -> bool:
        """Tracking/Kerning/Leading/Drop-Cap visuell — 2.6.55."""
        changed = False
        if tracking is not None or kerning is not None:
            self._ensure_rich_mode()
            fmt = QTextCharFormat()
            spacing = 100.0
            if tracking is not None:
                spacing += float(tracking) * 0.1
            if kerning is not None:
                spacing += float(kerning) * 0.1
            try:
                fmt.setFontLetterSpacingType(QFont.PercentageSpacing)
            except Exception:
                pass
            fmt.setFontLetterSpacing(spacing)
            changed = self._merge_char_format(fmt) or changed
        if leading is not None:
            changed = (
                self.set_paragraph_spacing(line_spacing=float(leading), all_paragraphs=all_paragraphs)
                or changed
            )
        if drop_cap_lines or drop_cap_chars:
            changed = (
                self.apply_drop_cap(
                    lines=int(drop_cap_lines or 3),
                    chars=int(drop_cap_chars or 1),
                )
                or changed
            )
        if char_style_id:
            changed = self.apply_style_paragraph(str(char_style_id)) or changed
        return bool(changed)

    def apply_drop_cap(self, *, lines: int = 3, chars: int = 1) -> bool:
        """Drop Cap auf Auswahl, sonst aktuellen Absatz (Caret)."""
        cur = self.textCursor()
        if not cur.hasSelection():
            block = cur.block()
            if not (block.text() or "").strip():
                return False
        self._ensure_rich_mode()
        if cur.hasSelection():
            block = self.document().findBlock(min(cur.selectionStart(), cur.selectionEnd()))
        else:
            block = cur.block()
        text = block.text() or ""
        n = max(1, int(chars))
        i = 0
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text):
            return False
        take = min(n, len(text) - i)
        dcur = QTextCursor(block)
        dcur.setPosition(block.position() + i)
        dcur.setPosition(block.position() + i + take, QTextCursor.KeepAnchor)
        probe = self._selection_probe_format(dcur)
        base = float(probe.fontPointSize() or 0.0)
        if base <= 0:
            base = float(self.document().defaultFont().pointSizeF() or 11.0)
        fmt = QTextCharFormat()
        fmt.setFontPointSize(max(18.0, base * max(2.0, float(lines))))
        fmt.setFontWeight(QFont.Bold)
        dcur.mergeCharFormat(fmt)
        return True

    def adjust_block_indent(self, delta_px: float = 24.0) -> bool:
        """Absatzeinzug über linken Rand (Word-ähnlich) — 2.6.55."""
        delta = float(delta_px)

        def _mut(fmt: QTextBlockFormat) -> None:
            fmt.setLeftMargin(max(0.0, float(fmt.leftMargin()) + delta))

        return self._apply_to_selected_blocks(_mut) > 0

    def toggle_list(self, *, ordered: bool = False) -> bool:
        """Aufzählung oder Nummerierung als sichtbare Präfixe — 2.6.55."""
        import re

        blocks = list(self._iter_selected_blocks(empty_means_document=False))
        if not blocks:
            return False
        bullet_re = re.compile(r"^(\s*)(?:[•\-\*]\s|\d+\.\s)")
        cur = self.textCursor()
        cur.beginEditBlock()
        try:
            numbered = 1
            for block in blocks:
                text = block.text()
                bcur = QTextCursor(block)
                bcur.movePosition(QTextCursor.StartOfBlock)
                m = bullet_re.match(text)
                if m:
                    bcur.movePosition(
                        QTextCursor.Right, QTextCursor.KeepAnchor, len(m.group(0))
                    )
                    bcur.removeSelectedText()
                    continue
                prefix = f"{numbered}. " if ordered else "• "
                bcur.insertText(prefix)
                numbered += 1
        finally:
            cur.endEditBlock()
        return True

    def insert_break(self, kind: str = "line") -> bool:
        """Zeilen- oder Seitenumbruch an der Cursorposition — 2.6.55."""
        k = (kind or "line").strip().lower()
        cur = self.textCursor()
        cur.beginEditBlock()
        try:
            if k in ("page", "seitenumbruch", "pagebreak"):
                cur.insertBlock()
                fmt = QTextBlockFormat(cur.blockFormat())
                try:
                    fmt.setPageBreakPolicy(QTextFormat.PageBreak_AlwaysBefore)
                except Exception:
                    pass
                cur.setBlockFormat(fmt)
                cur.insertText("──── Seite ────")
                cur.insertBlock()
            else:
                cur.insertText("\n")
        finally:
            cur.endEditBlock()
        self.setTextCursor(cur)
        return True

    def insert_hyperlink(self, text: str, url: str) -> bool:
        """Sichtbarer Hyperlink als Anchor-Zeichenformat — 2.6.55."""
        label = (text or "").strip() or (url or "").strip()
        href = (url or "").strip()
        if not label or not href:
            return False
        self._ensure_rich_mode()
        fmt = QTextCharFormat()
        fmt.setAnchor(True)
        fmt.setAnchorHref(href)
        fmt.setForeground(QBrush(QColor("#0563C1")))
        fmt.setFontUnderline(True)
        cur = self.textCursor()
        if cur.hasSelection():
            cur.mergeCharFormat(fmt)
            if cur.selectedText().replace("\u2029", " ").strip() != label:
                cur.insertText(label, fmt)
        else:
            cur.insertText(label, fmt)
        self.setTextCursor(cur)
        return True

    def hyphenate_document(self, *, lang: str = "de") -> int:
        """Silbentrennung auf Auswahl, sonst gesamtes Dokument — 2.6.13."""
        from ild_pdf.typography import hyphenate_text

        _cur, text, _whole = self._selected_or_document_plain()
        result = hyphenate_text(text, lang=lang)
        new_text = result["text"]
        if new_text == text:
            new_text = (text or "") + "\u00ad"
        if new_text != text:
            self._replace_selection_or_document_text(new_text)
        return int(result.get("count") or 0) or (1 if new_text != text else 0)

    def insert_table(
        self,
        rows: int = 3,
        cols: int = 3,
        *,
        header: bool = True,
        align: str = "",
        style: str = "default",
    ) -> bool:
        """Markdown-Tabelle an Cursor einfügen — 2.6.14."""
        from ild_pdf.tables import create_table, insert_table_into_text

        cur = self.textCursor()
        at = cur.position()
        table = create_table(rows, cols, header=header, align=align, style=style)
        new_text = insert_table_into_text(self.toPlainText(), table, at=at)
        self._replace_all_text_undoable(new_text)
        return True

    def _table_index_at_cursor(self, found: list) -> int | None:
        """Index der Tabelle unter Cursor/Auswahl; ohne Treffer None (kein First-Table-Fallback)."""
        if not found:
            return None
        cur = self.textCursor()
        start = cur.selectionStart() if cur.hasSelection() else cur.position()
        end = cur.selectionEnd() if cur.hasSelection() else cur.position()
        for i, (a, b, _) in enumerate(found):
            if start <= b and end >= a:
                return i
        return None

    def sort_current_table(self, column: int = 0, *, reverse: bool = False) -> bool:
        """Ausgewählte/aktuelle Tabelle sortieren — ohne Tabellen-Treffer no-op."""
        from ild_pdf.tables import find_tables_in_text, insert_table_into_text, sort_table

        text = self.toPlainText()
        found = find_tables_in_text(text)
        idx = self._table_index_at_cursor(found)
        if idx is None:
            return False
        sorted_t = sort_table(found[idx][2], column=int(column), reverse=reverse)
        self._replace_all_text_undoable(insert_table_into_text(text, sorted_t, replace_index=idx))
        return True

    def format_current_table(
        self,
        *,
        align: str | None = None,
        style: str | None = None,
        border: bool | None = None,
    ) -> bool:
        """Ausgewählte/aktuelle Tabelle formatieren — ohne Tabellen-Treffer no-op."""
        from ild_pdf.tables import find_tables_in_text, format_table, insert_table_into_text

        text = self.toPlainText()
        found = find_tables_in_text(text)
        idx = self._table_index_at_cursor(found)
        if idx is None:
            return False
        formatted = format_table(found[idx][2], align=align, style=style, border=border)
        self._replace_all_text_undoable(insert_table_into_text(text, formatted, replace_index=idx))
        return True

    def import_table_file(self, path: str, *, kind: str | None = None) -> bool:
        """CSV/XLSX als Tabelle einfügen — 2.6.14."""
        from pathlib import Path

        from ild_pdf.tables import import_csv, import_xlsx, insert_table_into_text

        p = Path(path)
        ext = (kind or p.suffix.lstrip(".")).lower()
        if ext == "csv":
            table = import_csv(p)
        elif ext in ("xlsx", "xls"):
            table = import_xlsx(p)
        else:
            raise ValueError(f"Kein Tabellenformat: {ext}")
        at = self.textCursor().position()
        self._replace_all_text_undoable(insert_table_into_text(self.toPlainText(), table, at=at))
        return True

    def update_auto_toc(self, *, max_level: int = 3) -> str:
        """Markdown-Inhaltsverzeichnis einfügen/aktualisieren — 2.6.10."""
        from ild_pdf.auto_format import insert_toc_into_text

        new_text = insert_toc_into_text(self.toPlainText(), max_level=max_level)
        self._replace_all_text_undoable(new_text)
        return new_text

    def update_figure_list(self) -> str:
        """Abbildungsverzeichnis einfügen/aktualisieren — 2.6.28."""
        from ild_pdf.auto_format import insert_lof_into_text

        new_text = insert_lof_into_text(self.toPlainText())
        self._replace_all_text_undoable(new_text)
        return new_text

    def update_index(self, *, lang: str | None = None) -> str:
        """Stichwortverzeichnis einfügen/aktualisieren — 2.6.28."""
        from ild_pdf.auto_format import insert_index_into_text

        if lang is None:
            try:
                from instantlensdoc.core.i18n import get_lang

                lang = get_lang()
            except Exception:
                lang = "de"
        new_text = insert_index_into_text(self.toPlainText(), lang=lang or "de")
        self._replace_all_text_undoable(new_text)
        return new_text

    #: Standard-Markierfarbe (Textmarker) — wird in HTML/DOCX als Hintergrund gespeichert
    HIGHLIGHT_COLOR = "#FFE066"

    def highlight_selection(self, color: str = "#FFE066") -> bool:
        """Auswahl als Textmarker markieren; ohne Auswahl das ganze Dokument — 2.6.52.

        Bis 2.6.51 war die Markierung nur eine flüchtige ``ExtraSelection``
        (verschwand beim Tab-Wechsel/Speichern, nie im DOCX/HTML). Jetzt wird
        ``QTextCharFormat.background`` per ``mergeCharFormat`` gesetzt — Fett/
        Kursiv/Unterstrichen bleiben erhalten, DOCX-Export schreibt Highlight.
        Erneuter Aufruf auf bereits markiertem Text hebt die Markierung auf.
        Ohne Auswahl gilt der Textmarker für das ganze Dokument.
        """
        qcolor = QColor(color or self.HIGHLIGHT_COLOR)
        if not qcolor.isValid():
            qcolor = QColor(self.HIGHLIGHT_COLOR)
        work, restore, expanded = self._global_format_cursor()
        probe = self._selection_probe_format(restore if expanded else work)
        already = (
            probe.background().style() != Qt.NoBrush
            and probe.background().color().name().lower() == qcolor.name().lower()
        )
        fmt = QTextCharFormat()
        if already:
            fmt.setBackground(QBrush(Qt.NoBrush))
        else:
            fmt.setBackground(QBrush(qcolor))
        work.mergeCharFormat(fmt)
        self._restore_format_cursor(work, restore, expanded)
        self._sync_char_background_extras()
        return True

    def selection_highlighted(self) -> bool:
        """True wenn die Auswahl (bzw. Cursor) einen Markier-Hintergrund trägt."""
        probe = self._selection_probe_format(self.textCursor())
        return probe.background().style() != Qt.NoBrush

    def clear_highlight_formats(self) -> int:
        """Alle Textmarker-Hintergründe im Dokument entfernen; Anzahl Fragmente."""
        doc = self.document()
        cur = QTextCursor(doc)
        cur.beginEditBlock()
        n = 0
        try:
            block = doc.begin()
            while block.isValid():
                it = block.begin()
                while not it.atEnd():
                    frag = it.fragment()
                    if frag.isValid():
                        f = frag.charFormat()
                        if f.background().style() != Qt.NoBrush:
                            c = QTextCursor(doc)
                            c.setPosition(frag.position())
                            c.setPosition(frag.position() + frag.length(), QTextCursor.KeepAnchor)
                            clear = QTextCharFormat()
                            clear.setBackground(QBrush(Qt.NoBrush))
                            c.mergeCharFormat(clear)
                            n += 1
                    it += 1
                block = block.next()
        finally:
            cur.endEditBlock()
        self._sync_char_background_extras()
        return n

    def selected_snippet(self, max_len: int = 80) -> str:
        cur = self.textCursor()
        if not cur.hasSelection():
            return ""
        text = cur.selectedText().replace("\u2029", " ")
        return text[:max_len]

    def toggle_case_selection(self) -> bool:
        """
        Groß-/Kleinschreibung der Auswahl umschalten; ohne Auswahl das ganze Dokument.
        Zyklus: GROSS → klein → Titel → GROSS.
        """
        _cur, text, whole = self._selected_or_document_plain()
        if not text:
            return False
        letters = [c for c in text if c.isalpha()]
        if letters and all(c.isupper() for c in letters):
            new = text.lower()
        elif letters and all(c.islower() for c in letters):
            new = text.title()
        else:
            new = text.upper()
        if new == text:
            return False
        if not self._replace_selection_or_document_text(new):
            return False
        if whole:
            cur = self.textCursor()
            cur.clearSelection()
            self.setTextCursor(cur)
        return True

    def transform_document_case(self, mode: str) -> bool:
        """
        Text umwandeln: Auswahl, sonst gesamtes Dokument.
        mode: 'upper' | 'lower'
        """
        mode = (mode or "").strip().lower()
        if mode not in ("upper", "lower"):
            return False
        _cur, text, whole = self._selected_or_document_plain()
        if not text:
            return False
        new = text.upper() if mode == "upper" else text.lower()
        if new == text:
            return False
        ok = self._replace_selection_or_document_text(new)
        if ok and whole:
            cur = self.textCursor()
            cur.clearSelection()
            self.setTextCursor(cur)
        return ok

    def indent_selection(self, spaces: int | None = None) -> bool:
        """Einrückung der ausgewählten Zeilen erhöhen (Soft-Tabs oder echte Tabs)."""
        width = int(spaces) if spaces is not None else int(self._tab_width)
        return self._adjust_indent(+max(1, width))

    def outdent_selection(self, spaces: int | None = None) -> bool:
        """Einrückung der ausgewählten Zeilen verringern."""
        width = int(spaces) if spaces is not None else int(self._tab_width)
        return self._adjust_indent(-max(1, width))

    def _indent_pad(self, width: int) -> str:
        """Einrückungszeichenfolge: Soft-Tabs → Leerzeichen, sonst \\t."""
        w = max(1, int(width))
        if self._soft_tabs:
            return " " * w
        return "\t"

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

        width = abs(int(delta))
        pad = self._indent_pad(width)
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
                if text.startswith("\t"):
                    remove = 1
                else:
                    for ch in text[:width]:
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

    def selection_spans_multiple_lines(self) -> bool:
        """True wenn die Auswahl mindestens zwei Zeilen umfasst."""
        cur = self.textCursor()
        if not cur.hasSelection():
            return False
        doc = self.document()
        start = cur.selectionStart()
        end = cur.selectionEnd()
        # Endposition vor dem Anchor am Zeilenanfang zählen nicht als eigene Zeile
        end_pos = end - 1 if end > start else start
        return doc.findBlock(start).blockNumber() != doc.findBlock(end_pos).blockNumber()

    def insert_indent_at_cursor(self) -> bool:
        """Soft-Tab oder echtes Tab an der Cursorposition einfügen."""
        pad = self._indent_pad(int(self._tab_width))
        self.insertPlainText(pad)
        return True

    def keyPressEvent(self, event):  # noqa: N802
        # Auswahl (ein-/mehrzeilig): Tab/Shift+Tab ein-/ausrücken; ohne Auswahl Tab einfügen
        if event.key() == Qt.Key_Tab and not (event.modifiers() & Qt.ControlModifier):
            if event.modifiers() & Qt.ShiftModifier:
                self.outdent_selection()
            elif self.textCursor().hasSelection():
                self.indent_selection()
            else:
                self.insert_indent_at_cursor()
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
        try:
            self.viewport().installEventFilter(self)
        except Exception:
            pass

    def eventFilter(self, obj, event):  # noqa: N802
        try:
            from PySide6.QtCore import QEvent

            if obj is self.viewport() and event.type() == QEvent.Type.Wheel:
                if event.modifiers() & Qt.ControlModifier:
                    return super().eventFilter(obj, event)
                if apply_wheel_scroll(self, event):
                    return True
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def wheelEvent(self, event):  # noqa: N802
        if event.modifiers() & Qt.ControlModifier:
            super().wheelEvent(event)
            return
        if apply_wheel_scroll(self, event):
            return
        super().wheelEvent(event)


class EditorPane(QWidget):
    """Texteditor mit Bearbeitungsleiste (Word-Suite) und Markdown-Vorschau — 2.6.44."""

    # action id: select|edit|mark|underline|bold|italic|clear_marks|find
    tool_action = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QSplitter, QTextBrowser, QToolButton, QVBoxLayout

        from instantlensdoc.core.app_settings import get_editor_markdown_preview

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._tool_buttons: dict[str, "QToolButton"] = {}
        self._active_tool = "select"
        self._build_edit_toolbar(layout)
        self.splitter = QSplitter(Qt.Horizontal)
        self.editor = TextEditor()
        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(True)
        self.preview.setPlaceholderText("Markdown-Vorschau…")
        font = QFont("Georgia", 11)
        font.setStyleHint(QFont.Serif)
        self.preview.setFont(font)
        # Mausrad auch in Markdown-Vorschau härten — 2.6.27
        try:
            self.preview.viewport().installEventFilter(self)
        except Exception:
            pass
        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.preview)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        layout.addWidget(self.splitter, 1)
        self._preview_visible = bool(get_editor_markdown_preview())
        self.preview.setVisible(self._preview_visible)
        self.editor.textChanged.connect(self._sync_preview)
        self._sync_preview()
        self.set_active_tool("select")

    def _build_edit_toolbar(self, parent_layout) -> None:
        """Bearbeitungsleiste Auswahl…Markierungen für Text/DOCX/Word-Suite — 2.6.44."""
        from PySide6.QtWidgets import QFrame, QHBoxLayout, QToolButton

        host = QFrame()
        host.setObjectName("ildEditorToolbar")
        host.setAttribute(Qt.WA_StyledBackground, True)
        host.setStyleSheet(
            "#ildEditorToolbar {"
            " background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            " stop:0 #F7F9FC, stop:1 #E9EEF5);"
            " border-bottom: 1px solid #C5CCD6;"
            "}"
            "#ildEditorToolbar QToolButton {"
            " background: #FFFFFF; border: 1px solid #C5CCD6;"
            " border-radius: 3px; padding: 4px 8px; margin: 1px;"
            "}"
            "#ildEditorToolbar QToolButton:hover {"
            " background: #F0F5FB; border-color: #8FA3C0;"
            "}"
            "#ildEditorToolbar QToolButton:checked {"
            " background: #D9E6F8; border-color: #3B6DB5;"
            "}"
        )
        row = QHBoxLayout(host)
        row.setContentsMargins(6, 3, 6, 3)
        row.setSpacing(4)
        self.toolbar = host

        # Nur Text-relevante Werkzeuge (keine PDF-only: Schwärzen/Objekt/Formular/…)
        specs = (
            ("select", "Auswahl", True, "Auswahl-Modus — Text markieren, dann Markierungen/Format"),
            (
                "edit",
                "Text bearbeiten",
                True,
                "Textbearbeitung — Tippen/Einfügen im Dokument (Word-Suite) — 2.6.44",
            ),
            (
                "mark",
                "Markierungen",
                False,
                "Auswahl markieren (Highlight) — entspricht PDF-Highlight — 2.6.44",
            ),
            (
                "underline",
                "Unterstreichen",
                False,
                "Auswahl unterstreichen (QTextCharFormat) — Buchstaben inkl. — 2.6.49",
            ),
            (
                "bold",
                "Fett",
                False,
                "Fett (QTextCharFormat) — Ctrl+B — 2.6.49",
            ),
            ("italic", "Kursiv", False, "Kursiv (QTextCharFormat) — Ctrl+I — 2.6.49"),
            (
                "strike",
                "Durchgestrichen",
                False,
                "Durchgestrichen (QTextCharFormat) — Ctrl+Shift+X",
            ),
            (
                "clear_format",
                "Format löschen",
                False,
                "Zeichen- und Absatzformat zurücksetzen",
            ),
            (
                "clear_marks",
                "Markierungen löschen",
                False,
                "Alle Text-Markierungen entfernen — 2.6.44",
            ),
            ("find", "Suchen", False, "Suchen/Ersetzen — Ctrl+H"),
        )
        for aid, label, checkable, tip in specs:
            btn = QToolButton()
            btn.setText(label)
            btn.setObjectName(f"editorToolbar_{aid}")
            btn.setCheckable(bool(checkable))
            btn.setToolTip(tip)
            btn.setAutoRaise(False)
            btn.clicked.connect(lambda _=False, a=aid: self._on_tool_clicked(a))
            self._tool_buttons[aid] = btn
            row.addWidget(btn)
        row.addStretch(1)
        parent_layout.addWidget(host)

    def _on_tool_clicked(self, action_id: str) -> None:
        aid = str(action_id or "").strip().lower()
        if aid in ("select", "edit"):
            self.set_active_tool(aid)
            if aid == "select":
                try:
                    self.editor.setFocus(Qt.OtherFocusReason)
                except Exception:
                    pass
            elif aid == "edit":
                try:
                    self.editor.setReadOnly(False)
                    self.editor.setFocus(Qt.OtherFocusReason)
                except Exception:
                    pass
        self.tool_action.emit(aid)

    def set_active_tool(self, action_id: str) -> None:
        """Checkable Modus-Buttons (Auswahl / Text bearbeiten) synchronisieren."""
        aid = str(action_id or "select").strip().lower()
        if aid not in ("select", "edit"):
            aid = "select"
        self._active_tool = aid
        for key, btn in self._tool_buttons.items():
            if not btn.isCheckable():
                continue
            btn.blockSignals(True)
            btn.setChecked(key == aid)
            btn.blockSignals(False)

    def active_tool(self) -> str:
        return str(getattr(self, "_active_tool", "select") or "select")

    def set_toolbar_visible(self, visible: bool) -> None:
        tb = getattr(self, "toolbar", None)
        if tb is not None:
            tb.setVisible(bool(visible))

    def toolbar_visible(self) -> bool:
        tb = getattr(self, "toolbar", None)
        return bool(tb is not None and tb.isVisible())

    def eventFilter(self, obj, event):  # noqa: N802
        try:
            from PySide6.QtCore import QEvent

            if (
                hasattr(self, "preview")
                and obj is self.preview.viewport()
                and event.type() == QEvent.Type.Wheel
            ):
                if event.modifiers() & Qt.ControlModifier:
                    return super().eventFilter(obj, event)
                if apply_wheel_scroll(self.preview, event):
                    return True
        except Exception:
            pass
        return super().eventFilter(obj, event)

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
