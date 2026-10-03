"""Zwei Textdateien / Editor-Tabs zeilenweise Side-by-Side vergleichen."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
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
)

from instantlensdoc.core.app_settings import dialog_start_dir, get_editor_text_encoding
from instantlensdoc.core.documents import normalize_text_encoding
from instantlensdoc.core.text_diff import line_diff_sides


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


def _fill_pane(edit: QPlainTextEdit, lines: list[str], tags: list[str], side: str) -> None:
    numbered = [f"{i + 1:>4} │ {line}" for i, line in enumerate(lines)]
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
    edit.setExtraSelections(selections)


class TextCompareDialog(QDialog):
    """Zwei Tabs/Dateien Side-by-Side (einfacher Zeilen-Diff)."""

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
            self.setWindowTitle("Dateien vergleichen (Side-by-Side)")
        self.resize(1100, 700)
        self._tabs = [str(p) for p in (tab_paths or []) if p]
        self._left_path = left_path or ""
        self._right_path = right_path or ""
        self._left_text = left_text
        self._right_text = right_text
        self._left_label = left_label or ""
        self._right_label = right_label or ""

        root = QVBoxLayout(self)
        if self._panel_mode:
            root.addWidget(
                QLabel("Einfaches Zeilen-Diff Panel: zwei offene Text-Tabs wählen — 1.2.0")
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

        self.lbl_status = QLabel("—")
        root.addWidget(self.lbl_status)

        panes = QHBoxLayout()
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.Monospace)
        self.view_left = QPlainTextEdit()
        self.view_right = QPlainTextEdit()
        for v in (self.view_left, self.view_right):
            v.setReadOnly(True)
            v.setFont(font)
            v.setLineWrapMode(QPlainTextEdit.NoWrap)
        panes.addWidget(self.view_left, 1)
        panes.addWidget(self.view_right, 1)
        root.addLayout(panes, 1)

        btn_reload = QPushButton("Vergleichen")
        btn_reload.clicked.connect(self.refresh)
        row = QHBoxLayout()
        row.addWidget(btn_reload)
        row.addStretch()
        root.addLayout(row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._select_initial()
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

    def refresh(self):
        left_data = self.cmb_left.currentData() or ""
        right_data = self.cmb_right.currentData() or ""
        lname, ltext = self._load_side(str(left_data))
        rname, rtext = self._load_side(str(right_data))
        if not left_data and not right_data:
            self.view_left.setPlainText("")
            self.view_right.setPlainText("")
            self.lbl_status.setText("Zwei Dateien oder Tabs wählen")
            return
        out_l, out_r, tags = line_diff_sides(ltext, rtext)
        _fill_pane(self.view_left, out_l, tags, "left")
        _fill_pane(self.view_right, out_r, tags, "right")
        n_diff = sum(1 for t in tags if t != "equal")
        self.lbl_status.setText(
            f"{lname}  ↔  {rname}  ·  {len(tags)} Zeilen · {n_diff} abweichend"
        )
        self.view_left.setToolTip(lname)
        self.view_right.setToolTip(rname)
