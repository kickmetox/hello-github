"""Variable-Fonts-Dialog: Achsen-Slider, Anwendung auf DTP-Textrahmen."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from instantlensdoc.features.variable_fonts import (
    apply_axes_to_qfont,
    list_font_axes,
    list_variable_fonts,
)


class VariableFontsDialog(QDialog):
    def __init__(self, parent=None, *, current_family: str = ""):
        super().__init__(parent)
        self.setObjectName("variableFontsDialog")
        self.setWindowTitle("Variable Fonts")
        self.resize(460, 360)
        self.axes_values: dict[str, float] = {}
        self._sliders: dict[str, QSlider] = {}
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Systemfonts inkl. Windows-Fonts; fvar-Achsen sofern fontTools sie liest."))
        self.family = QComboBox()
        self.family.setObjectName("varFontFamily")
        self._fonts = list_variable_fonts()
        for rec in self._fonts:
            mark = " [var]" if rec.get("variable") else ""
            self.family.addItem(rec["family"] + mark, rec["family"])
        if current_family:
            idx = self.family.findData(current_family)
            if idx >= 0:
                self.family.setCurrentIndex(idx)
        self.family.currentIndexChanged.connect(self._rebuild_axes)
        layout.addWidget(self.family)
        self.form = QFormLayout()
        layout.addLayout(self.form)
        self.preview = QLabel("Beispieltext — Variable Fonts")
        self.preview.setObjectName("varFontPreview")
        self.preview.setStyleSheet("font-size: 22px; padding: 8px;")
        layout.addWidget(self.preview)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._rebuild_axes()

    def selected_family(self) -> str:
        return str(self.family.currentData() or self.family.currentText() or "")

    def _rebuild_axes(self) -> None:
        while self.form.rowCount():
            self.form.removeRow(0)
        self._sliders.clear()
        fam = self.selected_family().replace(" [var]", "")
        axes = list_font_axes(fam)
        self.axes_values = {a["tag"]: float(a["default"]) for a in axes}
        for a in axes:
            sl = QSlider(Qt.Horizontal)
            sl.setMinimum(int(a["min"]))
            sl.setMaximum(int(max(a["max"], a["min"] + 1)))
            sl.setValue(int(a["default"]))
            sl.setObjectName(f"axis_{a['tag']}")
            sl.valueChanged.connect(lambda v, tag=a["tag"]: self._on_axis(tag, v))
            self._sliders[a["tag"]] = sl
            self.form.addRow(a["tag"], sl)
        self._update_preview()

    def _on_axis(self, tag: str, value: int) -> None:
        self.axes_values[tag] = float(value)
        self._update_preview()

    def _update_preview(self) -> None:
        font = QFont(self.selected_family().split(" [")[0])
        font.setPointSize(18)
        font = apply_axes_to_qfont(font, self.axes_values)
        self.preview.setFont(font)
