"""PDF: Gehe zu Seite."""

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


class GotoPageDialog(QDialog):
    """Modaler Dialog: Sprung zu einer Seitennummer im PDF-Viewer."""

    def __init__(self, pdf_view, parent=None):
        super().__init__(parent)
        self.pdf_view = pdf_view
        self.setWindowTitle("Gehe zu Seite")
        self.setWindowModality(Qt.WindowModal)
        self.resize(280, 120)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        max_page = max(1, int(getattr(pdf_view, "page_count", 0) or 0))
        cur = int(getattr(pdf_view, "page_index", 0) or 0) + 1
        self.page_spin = QSpinBox()
        self.page_spin.setRange(1, max_page)
        self.page_spin.setValue(min(max(1, cur), max_page))
        self.page_spin.setToolTip(f"1 … {max_page}")
        form.addRow("Seite:", self.page_spin)
        layout.addLayout(form)
        layout.addWidget(QLabel(f"Maximal: {max_page}"))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._go)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.page_spin.setFocus()
        self.page_spin.selectAll()

    def _go(self) -> None:
        page_count = int(getattr(self.pdf_view, "page_count", 0) or 0)
        if page_count < 1:
            self.reject()
            return
        idx = int(self.page_spin.value()) - 1
        if 0 <= idx < page_count:
            self.pdf_view.goto_page(idx)
            self.accept()
        else:
            self.page_spin.setFocus()
