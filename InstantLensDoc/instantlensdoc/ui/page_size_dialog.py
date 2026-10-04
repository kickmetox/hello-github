"""Dialog: Seitengröße setzen / CropBox zuschneiden — Anzeige mm/inch."""

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
    convert_pt,
    format_size_pair,
    get_page_boxes,
    set_crop_box,
    set_page_size,
    to_pt,
)
from instantlensdoc.core.app_settings import get_page_size_unit, set_page_size_unit
from instantlensdoc.core.i18n import tr


class PageSizeDialog(QDialog):
    def __init__(self, pdf_path: str | Path, page_index: int = 0, parent=None):
        super().__init__(parent)
        self.pdf_path = Path(pdf_path)
        self.page_index = page_index
        self._unit = get_page_size_unit()
        self.setWindowTitle(tr("page_size_title"))
        self.resize(440, 460)
        layout = QVBoxLayout(self)

        boxes = get_page_boxes(self.pdf_path, page_index)
        self._mb = boxes["mediabox"]
        self._cb = boxes["cropbox"]
        mb_w = self._mb[2] - self._mb[0]
        mb_h = self._mb[3] - self._mb[1]

        unit_row = QHBoxLayout()
        unit_row.addWidget(QLabel("Einheit:"))
        self.unit_combo = QComboBox()
        self.unit_combo.addItem("mm", "mm")
        self.unit_combo.addItem("inch", "inch")
        self.unit_combo.setCurrentIndex(1 if self._unit == "inch" else 0)
        self.unit_combo.currentIndexChanged.connect(self._on_unit_changed)
        unit_row.addWidget(self.unit_combo)
        unit_row.addStretch(1)
        layout.addLayout(unit_row)

        self.info_label = QLabel()
        layout.addWidget(self.info_label)

        size_box = QGroupBox(tr("apply_media"))
        size_form = QFormLayout(size_box)
        self.preset = QComboBox()
        self.preset.addItem("— Custom —", None)
        for name, (w, h) in PAGE_SIZE_PRESETS.items():
            self.preset.addItem(f"{name} ({format_size_pair(w, h, self._unit)})", name)
        self.preset.currentIndexChanged.connect(self._on_preset)
        size_form.addRow("Preset", self.preset)
        self.w_spin = QDoubleSpinBox()
        self.w_spin.setRange(1, 5000)
        self.w_spin.setDecimals(2)
        self.h_spin = QDoubleSpinBox()
        self.h_spin.setRange(1, 5000)
        self.h_spin.setDecimals(2)
        self._w_label = QLabel()
        self._h_label = QLabel()
        size_form.addRow(self._w_label, self.w_spin)
        size_form.addRow(self._h_label, self.h_spin)
        self.all_pages = QCheckBox("Alle Seiten")
        size_form.addRow(self.all_pages)
        btn_size = QPushButton(tr("apply_media"))
        btn_size.clicked.connect(self._apply_size)
        size_form.addRow(btn_size)
        layout.addWidget(size_box)

        crop_box = QGroupBox(tr("apply_crop"))
        crop_form = QFormLayout(crop_box)
        self.left = QDoubleSpinBox()
        self.bottom = QDoubleSpinBox()
        self.right = QDoubleSpinBox()
        self.top = QDoubleSpinBox()
        for s in (self.left, self.bottom, self.right, self.top):
            s.setRange(-1000, 5000)
            s.setDecimals(2)
        self._crop_labels = {
            "left": QLabel("Links"),
            "bottom": QLabel("Unten"),
            "right": QLabel("Rechts"),
            "top": QLabel("Oben"),
        }
        crop_form.addRow(self._crop_labels["left"], self.left)
        crop_form.addRow(self._crop_labels["bottom"], self.bottom)
        crop_form.addRow(self._crop_labels["right"], self.right)
        crop_form.addRow(self._crop_labels["top"], self.top)
        btn_crop = QPushButton(tr("apply_crop"))
        btn_crop.clicked.connect(self._apply_crop)
        crop_form.addRow(btn_crop)
        layout.addWidget(crop_box)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.clicked.connect(self.accept)
        layout.addWidget(buttons)

        self._apply_unit_to_spins(mb_w, mb_h, refresh_presets=False)
        self._refresh_labels(mb_w, mb_h)

        # A4 vorauswählen wenn nahe
        for i in range(self.preset.count()):
            name = self.preset.itemData(i)
            if name and name in PAGE_SIZE_PRESETS:
                pw, ph = PAGE_SIZE_PRESETS[name]
                if abs(pw - mb_w) < 1 and abs(ph - mb_h) < 1:
                    self.preset.setCurrentIndex(i)
                    break

    def _unit_suffix(self) -> str:
        return "in" if self._unit == "inch" else "mm"

    def _refresh_labels(self, mb_w: float, mb_h: float):
        u = self._unit_suffix()
        self.info_label.setText(
            f"Seite {self.page_index + 1}\n"
            f"MediaBox: {format_size_pair(mb_w, mb_h, self._unit)} "
            f"({mb_w:.1f} × {mb_h:.1f} pt)\n"
            f"CropBox:  ({convert_pt(self._cb[0], self._unit):.2f}, "
            f"{convert_pt(self._cb[1], self._unit):.2f}) – "
            f"({convert_pt(self._cb[2], self._unit):.2f}, "
            f"{convert_pt(self._cb[3], self._unit):.2f}) {u}"
        )
        self._w_label.setText(f"Breite ({u})")
        self._h_label.setText(f"Höhe ({u})")
        for key, lab in self._crop_labels.items():
            base = {"left": "Links", "bottom": "Unten", "right": "Rechts", "top": "Oben"}[key]
            lab.setText(f"{base} ({u})")

    def _apply_unit_to_spins(self, mb_w: float, mb_h: float, *, refresh_presets: bool):
        self.w_spin.setValue(convert_pt(mb_w, self._unit))
        self.h_spin.setValue(convert_pt(mb_h, self._unit))
        self.left.setValue(convert_pt(self._cb[0], self._unit))
        self.bottom.setValue(convert_pt(self._cb[1], self._unit))
        self.right.setValue(convert_pt(self._cb[2], self._unit))
        self.top.setValue(convert_pt(self._cb[3], self._unit))
        if refresh_presets:
            cur = self.preset.currentData()
            self.preset.blockSignals(True)
            self.preset.clear()
            self.preset.addItem("— Custom —", None)
            for name, (w, h) in PAGE_SIZE_PRESETS.items():
                self.preset.addItem(f"{name} ({format_size_pair(w, h, self._unit)})", name)
            idx = self.preset.findData(cur)
            self.preset.setCurrentIndex(idx if idx >= 0 else 0)
            self.preset.blockSignals(False)

    def _on_unit_changed(self):
        data = self.unit_combo.currentData() or "mm"
        self._unit = "inch" if data == "inch" else "mm"
        set_page_size_unit(self._unit)
        mb_w = self._mb[2] - self._mb[0]
        mb_h = self._mb[3] - self._mb[1]
        self._apply_unit_to_spins(mb_w, mb_h, refresh_presets=True)
        self._refresh_labels(mb_w, mb_h)

    def _on_preset(self):
        name = self.preset.currentData()
        if name and name in PAGE_SIZE_PRESETS:
            w, h = PAGE_SIZE_PRESETS[name]
            self.w_spin.setValue(convert_pt(w, self._unit))
            self.h_spin.setValue(convert_pt(h, self._unit))

    def _apply_size(self):
        try:
            set_page_size(
                self.pdf_path,
                self.page_index,
                to_pt(self.w_spin.value(), self._unit),
                to_pt(self.h_spin.value(), self._unit),
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
                to_pt(self.left.value(), self._unit),
                to_pt(self.bottom.value(), self._unit),
                to_pt(self.right.value(), self._unit),
                to_pt(self.top.value(), self._unit),
            )
            QMessageBox.information(self, tr("page_size_title"), "CropBox gesetzt.")
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, tr("page_size_title"), str(e))
