"""Dialog: Layout-Marken im Texteditor konfigurieren (mm, Farbe, Crop/Bleed/Register, Druck)."""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from instantlensdoc.core.editor_layout_marks import EditorLayoutMarks


class EditorLayoutMarksDialog(QDialog):
    """Ein/aus persistiert die Ansicht-Toggles; hier Maße, Farben, Druck/PDF."""

    def __init__(self, marks: EditorLayoutMarks | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("editorLayoutMarksDialog")
        self.setWindowTitle("Layout-Marken")
        self.setModal(True)
        self.resize(480, 560)
        self._marks = EditorLayoutMarks.from_dict((marks or EditorLayoutMarks()).to_dict())

        root = QVBoxLayout(self)
        hint = QLabel(
            "Breitenmarken, Druckmarken und Kopf-/Fußzeilen-Marken lassen sich "
            "unabhängig über Ansicht und die Editor-Leiste ein- und ausschalten. "
            "Hier nur Marken: Größen (mm), Farbe, Crop/Bleed/Register, Bildschirm "
            "vs. Druck/PDF. Satzspiegel und Seitenränder bleiben unter "
            "Layout → Seitenränder — kein zweites Ränder-Dialog."
        )
        hint.setWordWrap(True)
        root.addWidget(hint)

        vis = QGroupBox("Sichtbarkeit")
        vis_form = QFormLayout(vis)
        self.chk_width = QCheckBox("Breitenmarken (Bildschirm)")
        self.chk_width.setObjectName("marksShowWidth")
        self.chk_width.setChecked(self._marks.show_width_marks)
        self.chk_print = QCheckBox("Druckmarken (Bildschirm)")
        self.chk_print.setObjectName("marksShowPrint")
        self.chk_print.setChecked(self._marks.show_print_marks)
        self.chk_hf = QCheckBox("Kopf-/Fußzeilen-Marken (Bildschirm)")
        self.chk_hf.setObjectName("marksShowHeaderFooter")
        self.chk_hf.setChecked(self._marks.show_header_footer_marks)
        vis_form.addRow(self.chk_width)
        vis_form.addRow(self.chk_print)
        vis_form.addRow(self.chk_hf)
        self.chk_screen = QCheckBox("Auf dem Bildschirm zeichnen")
        self.chk_screen.setObjectName("marksShowOnScreen")
        self.chk_screen.setChecked(self._marks.show_on_screen)
        vis_form.addRow(self.chk_screen)
        root.addWidget(vis)

        prn = QGroupBox("Drucken / PDF")
        prn_form = QFormLayout(prn)
        self.chk_w_print = QCheckBox("Breitenmarken auf Druck/PDF")
        self.chk_w_print.setChecked(self._marks.include_width_on_print)
        self.chk_p_print = QCheckBox("Druckmarken auf Druck/PDF")
        self.chk_p_print.setObjectName("marksIncludePrintOnPrint")
        self.chk_p_print.setChecked(self._marks.include_print_on_print)
        self.chk_p_print.setToolTip(
            "Wenn aktiv, erscheinen Crop/Bleed/Register/Farbkeil beim Drucken "
            "und PDF-Export auch dann, wenn die Bildschirm-Druckmarken aus sind."
        )
        self.chk_hf_print = QCheckBox("Kopf-/Fußzeilen auf Druck/PDF")
        self.chk_hf_print.setChecked(self._marks.include_hf_on_print)
        prn_form.addRow(self.chk_w_print)
        prn_form.addRow(self.chk_p_print)
        prn_form.addRow(self.chk_hf_print)
        root.addWidget(prn)

        pre = QGroupBox("Druckmarken (Prepress)")
        pre_form = QFormLayout(pre)
        self.spin_crop = self._mm_spin(self._marks.crop_mm, 1.0, 25.0)
        self.spin_crop.setObjectName("marksCropMm")
        self.spin_bleed = self._mm_spin(self._marks.bleed_mm, 0.0, 20.0)
        self.spin_bleed.setObjectName("marksBleedMm")
        self.spin_reg = self._mm_spin(self._marks.register_mm, 1.0, 20.0)
        self.spin_bar = self._mm_spin(self._marks.color_bar_mm, 1.0, 12.0)
        pre_form.addRow("Schnittmarken (mm)", self.spin_crop)
        pre_form.addRow("Anschnitt / Bleed (mm)", self.spin_bleed)
        pre_form.addRow("Passkreuze (mm)", self.spin_reg)
        pre_form.addRow("Farbkeil (mm)", self.spin_bar)
        self.chk_crop = QCheckBox("Crop")
        self.chk_crop.setChecked(self._marks.show_crop)
        self.chk_bleed = QCheckBox("Bleed")
        self.chk_bleed.setChecked(self._marks.show_bleed)
        self.chk_reg = QCheckBox("Register")
        self.chk_reg.setChecked(self._marks.show_register)
        self.chk_bar = QCheckBox("Farbkeil")
        self.chk_bar.setChecked(self._marks.show_color_bar)
        kinds = QHBoxLayout()
        for cb in (self.chk_crop, self.chk_bleed, self.chk_reg, self.chk_bar):
            kinds.addWidget(cb)
        kinds.addStretch(1)
        pre_form.addRow("Arten", kinds)
        root.addWidget(pre)

        hf = QGroupBox("Kopf- / Fußzeilen-Marken (Bänder)")
        hf_form = QFormLayout(hf)
        self.spin_header = self._mm_spin(self._marks.header_height_mm, 4.0, 40.0)
        self.spin_header.setObjectName("marksHeaderMm")
        self.spin_footer = self._mm_spin(self._marks.footer_height_mm, 4.0, 40.0)
        self.spin_footer.setObjectName("marksFooterMm")
        hf_form.addRow("Bandhöhe Kopf (mm)", self.spin_header)
        hf_form.addRow("Bandhöhe Fuß (mm)", self.spin_footer)
        root.addWidget(hf)

        col = QGroupBox("Farben")
        col_form = QFormLayout(col)
        self.btn_width_c = self._color_btn(self._marks.width_color)
        self.btn_print_c = self._color_btn(self._marks.print_color)
        self.btn_bleed_c = self._color_btn(self._marks.bleed_color)
        self.btn_hf_c = self._color_btn(self._marks.header_footer_color)
        col_form.addRow("Breitenmarken", self.btn_width_c)
        col_form.addRow("Druckmarken", self.btn_print_c)
        col_form.addRow("Bleed", self.btn_bleed_c)
        col_form.addRow("Kopf/Fuß", self.btn_hf_c)
        root.addWidget(col)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    @staticmethod
    def _mm_spin(value: float, lo: float, hi: float) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setDecimals(1)
        s.setSuffix(" mm")
        s.setValue(float(value))
        return s

    def _color_btn(self, hex_color: str) -> QPushButton:
        btn = QPushButton(hex_color)
        btn.setProperty("hex", hex_color)
        btn.setStyleSheet(f"background:{hex_color}; text-align:left; padding:4px;")
        btn.clicked.connect(lambda _=False, b=btn: self._pick_color(b))
        return btn

    def _pick_color(self, btn: QPushButton) -> None:
        cur = QColor(str(btn.property("hex") or "#333333"))
        col = QColorDialog.getColor(cur, self, "Farbe")
        if not col.isValid():
            return
        hex_c = col.name().upper()
        btn.setProperty("hex", hex_c)
        btn.setText(hex_c)
        btn.setStyleSheet(f"background:{hex_c}; text-align:left; padding:4px;")

    def result_marks(self) -> EditorLayoutMarks:
        m = EditorLayoutMarks.from_dict(self._marks.to_dict())
        m.show_width_marks = self.chk_width.isChecked()
        m.show_print_marks = self.chk_print.isChecked()
        m.show_header_footer_marks = self.chk_hf.isChecked()
        m.show_on_screen = self.chk_screen.isChecked()
        m.include_width_on_print = self.chk_w_print.isChecked()
        m.include_print_on_print = self.chk_p_print.isChecked()
        m.include_hf_on_print = self.chk_hf_print.isChecked()
        m.crop_mm = float(self.spin_crop.value())
        m.bleed_mm = float(self.spin_bleed.value())
        m.register_mm = float(self.spin_reg.value())
        m.color_bar_mm = float(self.spin_bar.value())
        m.show_crop = self.chk_crop.isChecked()
        m.show_bleed = self.chk_bleed.isChecked()
        m.show_register = self.chk_reg.isChecked()
        m.show_color_bar = self.chk_bar.isChecked()
        m.header_height_mm = float(self.spin_header.value())
        m.footer_height_mm = float(self.spin_footer.value())
        m.width_color = str(self.btn_width_c.property("hex") or m.width_color)
        m.print_color = str(self.btn_print_c.property("hex") or m.print_color)
        m.bleed_color = str(self.btn_bleed_c.property("hex") or m.bleed_color)
        m.header_footer_color = str(self.btn_hf_c.property("hex") or m.header_footer_color)
        return EditorLayoutMarks.from_dict(m.to_dict())
