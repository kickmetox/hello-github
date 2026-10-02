"""Editor: Gehe zu Zeile."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)

from instantlensdoc.ui.editor import TextEditor


class GotoLineDialog(QDialog):
    """Modaler Dialog: Sprung zu einer Zeilennummer im Texteditor."""

    def __init__(self, editor: TextEditor, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.setWindowTitle("Gehe zu Zeile")
        self.setWindowModality(Qt.WindowModal)
        self.resize(280, 120)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        max_line = max(1, editor.blockCount())
        cur = editor.textCursor().blockNumber() + 1
        self.line_spin = QSpinBox()
        self.line_spin.setRange(1, max_line)
        self.line_spin.setValue(min(max(1, cur), max_line))
        self.line_spin.setToolTip(f"1 … {max_line}")
        form.addRow("Zeile:", self.line_spin)
        layout.addLayout(form)
        layout.addWidget(QLabel(f"Maximal: {max_line}"))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._go)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.line_spin.setFocus()
        self.line_spin.selectAll()

    def _go(self) -> None:
        ok = self.editor.goto_line(int(self.line_spin.value()))
        if ok:
            self.accept()
        else:
            self.line_spin.setFocus()
