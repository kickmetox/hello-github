"""Zwei Textdateien / Editor-Tabs zeilenweise Side-by-Side oder Unified vergleichen."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from instantlensdoc.core.app_settings import (
    dialog_start_dir,
    get_editor_text_encoding,
    get_text_diff_ignore_whitespace,
    get_text_diff_sync_scroll,
    set_text_diff_ignore_whitespace,
    set_text_diff_sync_scroll,
)
from instantlensdoc.core.documents import normalize_text_encoding
from instantlensdoc.core.text_diff import (
    filter_diff_differences,
    format_diff_txt,
    format_unified_diff,
    line_diff_sides,
    word_diff_spans,
)


def _read_text(path: str | Path, encoding: str | None = None) -> str:
    enc = normalize_text_encoding(encoding or get_editor_text_encoding())
    raw = Path(path).read_bytes()
    try:
        return raw.decode(enc)
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace")


_TAG_COLORS = {
    "equal": None,
    "replace": QColor("#FFF3CD"),
    "delete": QColor("#F8D7DA"),
    "insert": QColor("#D4EDDA"),
}

_WORD_COLORS = {
    "replace": QColor("#FFD666"),
    "delete": QColor("#FF8A80"),
    "insert": QColor("#69F0AE"),
}


def _fill_pane(
    edit: QPlainTextEdit,
    lines: list[str],
    tags: list[str],
    side: str,
    *,
    line_numbers: bool = True,
    word_highlight: bool = True,
    other_lines: list[str] | None = None,
) -> None:
    if line_numbers:
        numbered = [f"{i + 1:>4} │ {line}" for i, line in enumerate(lines)]
        prefix_len = 7  # "NNNN │ "
    else:
        numbered = list(lines)
        prefix_len = 0
    edit.setPlainText("\n".join(numbered))
    selections = []
    doc = edit.document()
    for i, tag in enumerate(tags):
        color = _TAG_COLORS.get(tag)
        if color is None:
            continue
        if side == "left" and tag == "insert":
            continue
        if side == "right" and tag == "delete":
            continue
        block = doc.findBlockByNumber(i)
        if not block.isValid():
            continue
        fmt = QTextCharFormat()
        fmt.setBackground(color)
        cur = QTextCursor(block)
        cur.select(QTextCursor.LineUnderCursor)
        sel = QTextEdit.ExtraSelection()
        sel.cursor = cur
        sel.format = fmt
        selections.append(sel)

        # Einfaches Wort-Highlight innerhalb geänderter Zeilen — 1.2.2
        if word_highlight and tag == "replace" and other_lines is not None:
            this_line = lines[i] if i < len(lines) else ""
            other = other_lines[i] if i < len(other_lines) else ""
            if side == "left":
                spans, _ = word_diff_spans(this_line, other)
            else:
                _, spans = word_diff_spans(other, this_line)
            # Absolute Position im Block: Prefix + Textanteile
            pos = block.position() + prefix_len
            for stag, token in spans:
                tlen = len(token)
                if stag in _WORD_COLORS and tlen > 0:
                    wfmt = QTextCharFormat()
                    wfmt.setBackground(_WORD_COLORS[stag])
                    wcur = QTextCursor(doc)
                    wcur.setPosition(pos)
                    wcur.setPosition(pos + tlen, QTextCursor.KeepAnchor)
                    wsel = QTextEdit.ExtraSelection()
                    wsel.cursor = wcur
                    wsel.format = wfmt
                    selections.append(wsel)
                pos += tlen
    edit.setExtraSelections(selections)


def _fill_unified(
    edit: QPlainTextEdit,
    text: str,
) -> None:
    """Unified-Diff in eine Pane mit Zeilenfarben — 1.2.2."""
    edit.setPlainText(text)
    selections = []
    doc = edit.document()
    block = doc.firstBlock()
    while block.isValid():
        line = block.text()
        color = None
        if line.startswith("- ") or (line.startswith("-") and not line.startswith("---")):
            color = _TAG_COLORS["delete"]
        elif line.startswith("+ ") or (line.startswith("+") and not line.startswith("+++")):
            color = _TAG_COLORS["insert"]
        if color is not None:
            fmt = QTextCharFormat()
            fmt.setBackground(color)
            cur = QTextCursor(block)
            cur.select(QTextCursor.LineUnderCursor)
            sel = QTextEdit.ExtraSelection()
            sel.cursor = cur
            sel.format = fmt
            selections.append(sel)
        block = block.next()
    edit.setExtraSelections(selections)


class TextCompareDialog(QDialog):
    """Zwei Tabs/Dateien Side-by-Side oder Unified (einfacher Zeilen-/Wort-Diff)."""

    def __init__(
        self,
        parent=None,
        *,
        tab_paths: list[str] | None = None,
        left_path: str | None = None,
        right_path: str | None = None,
        left_text: str | None = None,
        right_text: str | None = None,
        left_label: str | None = None,
        right_label: str | None = None,
        panel_mode: bool = False,
    ):
        super().__init__(parent)
        self._panel_mode = bool(panel_mode)
        if self._panel_mode:
            self.setWindowTitle("Text-Diff — offene Tabs (Zeilen-Diff)")
            self.setWindowFlag(Qt.Tool, True)
            self.setAttribute(Qt.WA_DeleteOnClose, True)
        else:
            self.setWindowTitle("Dateien vergleichen (Side-by-Side / Unified)")
        self.resize(1100, 700)
        self._tabs = [str(p) for p in (tab_paths or []) if p]
        self._left_path = left_path or ""
        self._right_path = right_path or ""
        self._left_text = left_text
        self._right_text = right_text
        self._left_label = left_label or ""
        self._right_label = right_label or ""
        self._last_left: list[str] = []
        self._last_right: list[str] = []
        self._last_tags: list[str] = []
        self._last_lname = ""
        self._last_rname = ""
        self._scroll_syncing = False

        root = QVBoxLayout(self)
        if self._panel_mode:
            root.addWidget(
                QLabel(
                    "Zeilen-Diff Panel: zwei offene Text-Tabs wählen — "
                    "Side-by-Side/Unified · Wort-Highlight · Ignore-Whitespace · "
                    "Sync-Scroll (Settings) · TXT-Export — 1.2.4"
                )
            )
        pick = QHBoxLayout()
        self.cmb_left = QComboBox()
        self.cmb_right = QComboBox()
        self.cmb_left.setMinimumWidth(220)
        self.cmb_right.setMinimumWidth(220)
        self._fill_combos()
        btn_l = QPushButton("Datei…")
        btn_r = QPushButton("Datei…")
        btn_l.clicked.connect(lambda: self._pick_file(True))
        btn_r.clicked.connect(lambda: self._pick_file(False))
        self.cmb_left.currentIndexChanged.connect(lambda _: self._on_combo(True))
        self.cmb_right.currentIndexChanged.connect(lambda _: self._on_combo(False))
        pick.addWidget(QLabel("Links"))
        pick.addWidget(self.cmb_left, 1)
        pick.addWidget(btn_l)
        pick.addWidget(QLabel("Rechts"))
        pick.addWidget(self.cmb_right, 1)
        pick.addWidget(btn_r)
        root.addLayout(pick)

        opts = QHBoxLayout()
        self.chk_only_diff = QCheckBox("Nur Unterschiede")
        self.chk_only_diff.setToolTip(
            "Gleiche Zeilen ausblenden — nur Abweichungen anzeigen — 1.2.1"
        )
        self.chk_only_diff.toggled.connect(lambda _: self.refresh())
        self.chk_line_numbers = QCheckBox("Zeilennummern")
        self.chk_line_numbers.setChecked(True)
        self.chk_line_numbers.setToolTip(
            "Zeilennummern in den Diff-Panes ein-/ausblenden — 1.2.1"
        )
        self.chk_line_numbers.toggled.connect(lambda _: self.refresh())
        self.chk_unified = QCheckBox("Unified")
        self.chk_unified.setToolTip(
            "Unified-Ansicht statt Side-by-Side (eine Spalte) — 1.2.2"
        )
        self.chk_unified.toggled.connect(lambda _: self.refresh())
        self.chk_word_hl = QCheckBox("Wort-Highlight")
        self.chk_word_hl.setChecked(True)
        self.chk_word_hl.setToolTip(
            "Geänderte Wörter innerhalb abweichender Zeilen hervorheben — 1.2.2"
        )
        self.chk_word_hl.toggled.connect(lambda _: self.refresh())
        self.chk_ignore_ws = QCheckBox("Ignore-Whitespace")
        self.chk_ignore_ws.setChecked(get_text_diff_ignore_whitespace())
        self.chk_ignore_ws.setToolTip(
            "Whitespace beim Zeilenvergleich ignorieren (Anzeige bleibt original); "
            "Einstellung wird gespeichert — 1.2.4"
        )
        self.chk_ignore_ws.toggled.connect(self._on_ignore_ws_toggled)
        self.chk_sync_scroll = QCheckBox("Sync-Scroll")
        self.chk_sync_scroll.setChecked(get_text_diff_sync_scroll())
        self.chk_sync_scroll.setToolTip(
            "Scrollposition Links/Rechts im Side-by-Side synchron halten; "
            "auch in Einstellungen — 1.2.4"
        )
        self.chk_sync_scroll.toggled.connect(self._on_sync_scroll_toggled)
        opts.addWidget(self.chk_only_diff)
        opts.addWidget(self.chk_line_numbers)
        opts.addWidget(self.chk_unified)
        opts.addWidget(self.chk_word_hl)
        opts.addWidget(self.chk_ignore_ws)
        opts.addWidget(self.chk_sync_scroll)
        opts.addStretch()
        root.addLayout(opts)

        self.lbl_status = QLabel("—")
        root.addWidget(self.lbl_status)

        self._panes_host = QWidget()
        panes = QHBoxLayout(self._panes_host)
        panes.setContentsMargins(0, 0, 0, 0)
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.Monospace)
        self.view_left = QPlainTextEdit()
        self.view_right = QPlainTextEdit()
        self.view_unified = QPlainTextEdit()
        for v in (self.view_left, self.view_right, self.view_unified):
            v.setReadOnly(True)
            v.setFont(font)
            v.setLineWrapMode(QPlainTextEdit.NoWrap)
        panes.addWidget(self.view_left, 1)
        panes.addWidget(self.view_right, 1)
        panes.addWidget(self.view_unified, 1)
        self.view_unified.hide()
        root.addWidget(self._panes_host, 1)

        btn_reload = QPushButton("Vergleichen")
        btn_reload.clicked.connect(self.refresh)
        btn_export = QPushButton("Diff als TXT…")
        btn_export.setToolTip("Aktuellen Diff als Textdatei exportieren — 1.2.1/1.2.2")
        btn_export.clicked.connect(self._export_diff_txt)
        row = QHBoxLayout()
        row.addWidget(btn_reload)
        row.addWidget(btn_export)
        row.addStretch()
        root.addLayout(row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._select_initial()
        self._apply_sync_scroll()
        self.refresh()

    def _fill_combos(self):
        self.cmb_left.blockSignals(True)
        self.cmb_right.blockSignals(True)
        self.cmb_left.clear()
        self.cmb_right.clear()
        self.cmb_left.addItem("— Datei wählen —", "")
        self.cmb_right.addItem("— Datei wählen —", "")
        for p in self._tabs:
            name = Path(p).name
            self.cmb_left.addItem(name, p)
            self.cmb_right.addItem(name, p)
        if self._left_label and self._left_text is not None:
            self.cmb_left.addItem(self._left_label + " (Editor)", "__editor_left__")
        if self._right_label and self._right_text is not None:
            self.cmb_right.addItem(self._right_label + " (Editor)", "__editor_right__")
        self.cmb_left.blockSignals(False)
        self.cmb_right.blockSignals(False)

    def _select_initial(self):
        if self._left_path:
            idx = self.cmb_left.findData(self._left_path)
            if idx >= 0:
                self.cmb_left.setCurrentIndex(idx)
        elif self._left_text is not None and self.cmb_left.findData("__editor_left__") >= 0:
            self.cmb_left.setCurrentIndex(self.cmb_left.findData("__editor_left__"))
        elif self._tabs:
            self.cmb_left.setCurrentIndex(1)
        if self._right_path:
            idx = self.cmb_right.findData(self._right_path)
            if idx >= 0:
                self.cmb_right.setCurrentIndex(idx)
        elif len(self._tabs) >= 2:
            self.cmb_right.setCurrentIndex(2 if self.cmb_right.count() > 2 else 1)
        elif self._right_text is not None and self.cmb_right.findData("__editor_right__") >= 0:
            self.cmb_right.setCurrentIndex(self.cmb_right.findData("__editor_right__"))

    def _on_combo(self, left: bool):
        self.refresh()

    def _pick_file(self, left: bool):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Datei wählen",
            dialog_start_dir(),
            "Text (*.txt *.md *.html *.htm *.csv *.json *.py *.log);;Alle (*.*)",
        )
        if not path:
            return
        cmb = self.cmb_left if left else self.cmb_right
        idx = cmb.findData(path)
        if idx < 0:
            cmb.addItem(Path(path).name, path)
            idx = cmb.count() - 1
        cmb.setCurrentIndex(idx)
        self.refresh()

    def _load_side(self, data: str) -> tuple[str, str]:
        """Returns (label, text)."""
        if data == "__editor_left__":
            return self._left_label or "Editor", self._left_text or ""
        if data == "__editor_right__":
            return self._right_label or "Editor", self._right_text or ""
        if not data:
            return "—", ""
        p = Path(data)
        if not p.is_file():
            return p.name, ""
        try:
            return p.name, _read_text(p)
        except Exception as e:
            QMessageBox.warning(self, "Lesen", f"{p.name}: {e}")
            return p.name, ""

    def _disconnect_sync_scroll(self) -> None:
        left_bar = self.view_left.verticalScrollBar()
        right_bar = self.view_right.verticalScrollBar()
        try:
            left_bar.valueChanged.disconnect(self._on_left_scroll_sync)
        except (TypeError, RuntimeError):
            pass
        try:
            right_bar.valueChanged.disconnect(self._on_right_scroll_sync)
        except (TypeError, RuntimeError):
            pass

    def _on_ignore_ws_toggled(self, checked: bool) -> None:
        """Ignore-Whitespace persistieren — 1.2.4."""
        set_text_diff_ignore_whitespace(bool(checked))
        self.refresh()

    def _on_sync_scroll_toggled(self, checked: bool) -> None:
        """Sync-Scroll persistieren und anwenden — 1.2.4."""
        set_text_diff_sync_scroll(bool(checked))
        self._apply_sync_scroll()

    def _apply_sync_scroll(self) -> None:
        """Sync-Scroll Side-by-Side verbinden — 1.2.3/1.2.4."""
        self._disconnect_sync_scroll()
        if self.chk_unified.isChecked() or not self.chk_sync_scroll.isChecked():
            return
        left_bar = self.view_left.verticalScrollBar()
        right_bar = self.view_right.verticalScrollBar()
        left_bar.valueChanged.connect(self._on_left_scroll_sync)
        right_bar.valueChanged.connect(self._on_right_scroll_sync)

    def _sync_scroll_ratio(self, source, target) -> None:
        if source is None or target is None or source is target:
            return
        s_max = source.maximum()
        t_max = target.maximum()
        if s_max <= 0:
            target.setValue(0)
            return
        if t_max <= 0:
            return
        ratio = source.value() / s_max
        target.setValue(int(round(ratio * t_max)))

    def _on_left_scroll_sync(self, _value: int = 0) -> None:
        if self._scroll_syncing:
            return
        self._scroll_syncing = True
        try:
            self._sync_scroll_ratio(
                self.view_left.verticalScrollBar(),
                self.view_right.verticalScrollBar(),
            )
        finally:
            self._scroll_syncing = False

    def _on_right_scroll_sync(self, _value: int = 0) -> None:
        if self._scroll_syncing:
            return
        self._scroll_syncing = True
        try:
            self._sync_scroll_ratio(
                self.view_right.verticalScrollBar(),
                self.view_left.verticalScrollBar(),
            )
        finally:
            self._scroll_syncing = False

    def refresh(self):
        left_data = self.cmb_left.currentData() or ""
        right_data = self.cmb_right.currentData() or ""
        lname, ltext = self._load_side(str(left_data))
        rname, rtext = self._load_side(str(right_data))
        if not left_data and not right_data:
            self.view_left.setPlainText("")
            self.view_right.setPlainText("")
            self.view_unified.setPlainText("")
            self.lbl_status.setText("Zwei Dateien oder Tabs wählen")
            self._last_left, self._last_right, self._last_tags = [], [], []
            self._apply_sync_scroll()
            return
        ignore_ws = self.chk_ignore_ws.isChecked()
        out_l, out_r, tags = line_diff_sides(
            ltext, rtext, ignore_whitespace=ignore_ws
        )
        self._last_left, self._last_right, self._last_tags = out_l, out_r, tags
        self._last_lname, self._last_rname = lname, rname
        show_l, show_r, show_t = out_l, out_r, tags
        only_diff = self.chk_only_diff.isChecked()
        if only_diff:
            show_l, show_r, show_t = filter_diff_differences(out_l, out_r, tags)
        line_nums = self.chk_line_numbers.isChecked()
        unified = self.chk_unified.isChecked()
        word_hl = self.chk_word_hl.isChecked()
        if unified:
            self.view_left.hide()
            self.view_right.hide()
            self.view_unified.show()
            utxt = format_unified_diff(
                show_l,
                show_r,
                show_t,
                left_label=lname,
                right_label=rname,
                line_numbers=line_nums,
                only_differences=False,  # bereits gefiltert
            )
            _fill_unified(self.view_unified, utxt)
        else:
            self.view_unified.hide()
            self.view_left.show()
            self.view_right.show()
            _fill_pane(
                self.view_left,
                show_l,
                show_t,
                "left",
                line_numbers=line_nums,
                word_highlight=word_hl,
                other_lines=show_r,
            )
            _fill_pane(
                self.view_right,
                show_r,
                show_t,
                "right",
                line_numbers=line_nums,
                word_highlight=word_hl,
                other_lines=show_l,
            )
        n_diff = sum(1 for t in tags if t != "equal")
        mode = " · nur Unterschiede" if only_diff else ""
        view = " · unified" if unified else " · side-by-side"
        ws = " · ignore-ws" if ignore_ws else ""
        sync = (
            " · sync-scroll"
            if (not unified and self.chk_sync_scroll.isChecked())
            else ""
        )
        self.lbl_status.setText(
            f"{lname}  ↔  {rname}  ·  {len(show_t)} Zeilen · "
            f"{n_diff} abweichend{mode}{view}{ws}{sync}"
        )
        self.view_left.setToolTip(lname)
        self.view_right.setToolTip(rname)
        self._apply_sync_scroll()

    def _export_diff_txt(self) -> None:
        """Aktuellen Diff als TXT speichern — 1.2.1/1.2.2."""
        if not self._last_tags and not self._last_left and not self._last_right:
            QMessageBox.information(
                self, "Diff-Export", "Kein Diff vorhanden — zuerst vergleichen."
            )
            return
        from instantlensdoc.core.app_settings import get_last_export_dir, set_last_export_dir

        start = dialog_start_dir(get_last_export_dir())
        default = str(Path(start) / "diff.txt")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Diff als TXT exportieren",
            default,
            "Text (*.txt);;Alle (*.*)",
        )
        if not path:
            return
        if not path.lower().endswith(".txt"):
            path += ".txt"
        try:
            text = format_diff_txt(
                self._last_left,
                self._last_right,
                self._last_tags,
                left_label=self._last_lname or "Links",
                right_label=self._last_rname or "Rechts",
                line_numbers=self.chk_line_numbers.isChecked(),
                only_differences=self.chk_only_diff.isChecked(),
                unified=self.chk_unified.isChecked(),
            )
            Path(path).write_text(text, encoding="utf-8")
            set_last_export_dir(Path(path).parent)
            self.lbl_status.setText(f"Diff exportiert: {Path(path).name}")
            QMessageBox.information(self, "Diff-Export", f"Gespeichert:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Diff-Export", str(e))
