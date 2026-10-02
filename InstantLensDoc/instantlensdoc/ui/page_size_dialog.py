"""Dialog: Seitengröße setzen / CropBox zuschneiden."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ild_pdf.pages import (
    PAGE_SIZE_PRESETS,
    get_page_boxes,
    set_crop_box,
    set_page_size,
)
from instantlensdoc.core.i18n import tr


class PageSizeDialog(QDialog):
    def __init__(self, pdf_path: str | Path, page_index: int = 0, parent=None):
        super().__init__(parent)
        self.pdf_path = Path(pdf_path)
        self.page_index = page_index
        self.setWindowTitle(tr("page_size_title"))
        self.resize(420, 420)
        layout = QVBoxLayout(self)

        boxes = get_page_boxes(self.pdf_path, page_index)
        mb = boxes["mediabox"]
        cb = boxes["cropbox"]
        layout.addWidget(
            QLabel(
                f"Seite {page_index + 1}\n"
                f"MediaBox: {mb[2] - mb[0]:.1f} × {mb[3] - mb[1]:.1f} pt\n"
                f"CropBox:  ({cb[0]:.1f}, {cb[1]:.1f}) – ({cb[2]:.1f}, {cb[3]:.1f})"
            )
        )

        size_box = QGroupBox(tr("apply_media"))
        size_form = QFormLayout(size_box)
        self.preset = QComboBox()
        self.preset.addItem("— Custom —", None)
        for name, (w, h) in PAGE_SIZE_PRESETS.items():
            self.preset.addItem(f"{name} ({w:.0f}×{h:.0f})", name)
        self.preset.currentIndexChanged.connect(self._on_preset)
        size_form.addRow("Preset", self.preset)
        self.w_spin = QDoubleSpinBox()
        self.w_spin.setRange(10, 5000)
        self.w_spin.setDecimals(2)
        self.w_spin.setValue(mb[2] - mb[0])
        self.h_spin = QDoubleSpinBox()
        self.h_spin.setRange(10, 5000)
        self.h_spin.setDecimals(2)
        self.h_spin.setValue(mb[3] - mb[1])
        size_form.addRow("Breite (pt)", self.w_spin)
        size_form.addRow("Höhe (pt)", self.h_spin)
        self.all_pages = QCheckBox("Alle Seiten")
        size_form.addRow(self.all_pages)
        btn_size = QPushButton(tr("apply_media"))
        btn_size.clicked.connect(self._apply_size)
        size_form.addRow(btn_size)
        layout.addWidget(size_box)

        crop_box = QGroupBox(tr("apply_crop"))
        crop_form = QFormLayout(crop_box)
        self.left = self._spin(cb[0])
        self.bottom = self._spin(cb[1])
        self.right = self._spin(cb[2])
        self.top = self._spin(cb[3])
        crop_form.addRow("Links", self.left)
        crop_form.addRow("Unten", self.bottom)
        crop_form.addRow("Rechts", self.right)
        crop_form.addRow("Oben", self.top)
        btn_crop = QPushButton(tr("apply_crop"))
        btn_crop.clicked.connect(self._apply_crop)
        crop_form.addRow(btn_crop)
        layout.addWidget(crop_box)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.clicked.connect(self.accept)
        layout.addWidget(buttons)

        # A4 vorauswählen wenn nahe
        for i in range(self.preset.count()):
            name = self.preset.itemData(i)
            if name and name in PAGE_SIZE_PRESETS:
                pw, ph = PAGE_SIZE_PRESETS[name]
                if abs(pw - (mb[2] - mb[0])) < 1 and abs(ph - (mb[3] - mb[1])) < 1:
                    self.preset.setCurrentIndex(i)
                    break

    def _spin(self, value: float) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(-1000, 5000)
        s.setDecimals(2)
        s.setValue(value)
        return s

    def _on_preset(self):
        name = self.preset.currentData()
        if name and name in PAGE_SIZE_PRESETS:
            w, h = PAGE_SIZE_PRESETS[name]
            self.w_spin.setValue(w)
            self.h_spin.setValue(h)

    def _apply_size(self):
        try:
            set_page_size(
                self.pdf_path,
                self.page_index,
                self.w_spin.value(),
                self.h_spin.value(),
                all_pages=self.all_pages.isChecked(),
            )
            QMessageBox.information(self, tr("page_size_title"), "MediaBox gesetzt.")
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, tr("page_size_title"), str(e))

    def _apply_crop(self):
        try:
            set_crop_box(
                self.pdf_path,
                self.page_index,
                self.left.value(),
                self.bottom.value(),
                self.right.value(),
                self.top.value(),
            )
            QMessageBox.information(self, tr("page_size_title"), "CropBox gesetzt.")
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, tr("page_size_title"), str(e))
