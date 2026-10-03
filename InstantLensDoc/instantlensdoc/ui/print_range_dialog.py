"""PDF-Dokumentdruck: Seitenbereich (von–bis) vor QPrintDialog — 1.0.1."""

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


class PrintRangeDialog(QDialog):
    """Modaler Dialog: Seitenbereich von–bis (1-basiert) für Dokumentdruck."""

    def __init__(self, page_count: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seitenbereich drucken")
        self.setWindowModality(Qt.WindowModal)
        self.resize(320, 140)
        n = max(1, int(page_count or 1))
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Seitenbereich wählen (1 … {n}):"))
        form = QFormLayout()
        self.from_spin = QSpinBox()
        self.from_spin.setRange(1, n)
        self.from_spin.setValue(1)
        self.from_spin.setToolTip("Erste Seite (einschließlich)")
        self.to_spin = QSpinBox()
        self.to_spin.setRange(1, n)
        self.to_spin.setValue(n)
        self.to_spin.setToolTip("Letzte Seite (einschließlich)")
        form.addRow("Von Seite:", self.from_spin)
        form.addRow("Bis Seite:", self.to_spin)
        layout.addLayout(form)
        self.from_spin.valueChanged.connect(self._sync_from)
        self.to_spin.valueChanged.connect(self._sync_to)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.from_spin.setFocus()

    def _sync_from(self, value: int) -> None:
        if self.to_spin.value() < value:
            self.to_spin.setValue(value)

    def _sync_to(self, value: int) -> None:
        if self.from_spin.value() > value:
            self.from_spin.setValue(value)

    def page_range(self) -> tuple[int, int]:
        """0-basierte Indizes (start inklusiv, end exklusiv) für range()."""
        a = int(self.from_spin.value()) - 1
        b = int(self.to_spin.value())  # exklusiv nach 0-basiert: to ist inklusiv → end = to
        if a < 0:
            a = 0
        if b <= a:
            b = a + 1
        return a, b
