"""PDF-Dokumentdruck: Seitenbereich (von–bis) + DPI + Graustufen vor QPrintDialog — 1.0.3."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)

from instantlensdoc.core.app_settings import (
    EXPORT_RASTER_DPI_CHOICES,
    get_export_raster_dpi,
    get_print_grayscale,
)


class PrintRangeDialog(QDialog):
    """Modaler Dialog: Seitenbereich von–bis (1-basiert) + Raster-DPI + Graustufen."""

    def __init__(
        self,
        page_count: int,
        parent=None,
        *,
        default_dpi: int | None = None,
        default_grayscale: bool | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Seitenbereich drucken")
        self.setWindowModality(Qt.WindowModal)
        self.resize(340, 210)
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

        self.dpi_combo = QComboBox()
        self.dpi_combo.setToolTip("Rasterauflösung für den Dokumentdruck (72 / 150 / 300 DPI)")
        for d in EXPORT_RASTER_DPI_CHOICES:
            self.dpi_combo.addItem(f"{d} DPI", int(d))
        try:
            dpi = int(default_dpi) if default_dpi is not None else int(get_export_raster_dpi())
        except Exception:
            dpi = 150
        if dpi not in EXPORT_RASTER_DPI_CHOICES:
            dpi = min(EXPORT_RASTER_DPI_CHOICES, key=lambda x: abs(x - dpi))
        idx = list(EXPORT_RASTER_DPI_CHOICES).index(dpi)
        self.dpi_combo.setCurrentIndex(idx)
        form.addRow("DPI (Raster):", self.dpi_combo)

        if default_grayscale is None:
            gray = bool(get_print_grayscale())
        else:
            gray = bool(default_grayscale)
        self.grayscale_check = QCheckBox("Graustufen")
        self.grayscale_check.setChecked(gray)
        self.grayscale_check.setToolTip(
            "Dokumentdruck monochrom (Graustufen) — Einstellung wird gemerkt — 1.0.3"
        )
        form.addRow("Farbe:", self.grayscale_check)

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

    def dpi(self) -> int:
        """Gewählte Raster-DPI (72 / 150 / 300)."""
        data = self.dpi_combo.currentData()
        try:
            v = int(data)
        except (TypeError, ValueError):
            v = 150
        if v not in EXPORT_RASTER_DPI_CHOICES:
            v = min(EXPORT_RASTER_DPI_CHOICES, key=lambda x: abs(x - v))
        return v

    def grayscale(self) -> bool:
        """Dokumentdruck in Graustufen — 1.0.3."""
        return bool(self.grayscale_check.isChecked())
