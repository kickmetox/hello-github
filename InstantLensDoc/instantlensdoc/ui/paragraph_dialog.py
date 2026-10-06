"""Word-ähnlicher Absatz-Dialog (Abstand, Einzug, Zeilenabstand, Umbruch)."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QVBoxLayout,
)


LINE_SPACING_PRESETS: tuple[tuple[str, str, float], ...] = (
    ("1,0", "multiple", 1.0),
    ("1,15", "multiple", 1.15),
    ("1,5", "multiple", 1.5),
    ("2,0", "multiple", 2.0),
    ("Genau", "exact", 12.0),
)


@dataclass
class ParagraphFormatSpec:
    space_before_pt: float = 0.0
    space_after_pt: float = 8.0
    first_line_indent_mm: float = 0.0
    left_indent_mm: float = 0.0
    right_indent_mm: float = 0.0
    line_spacing: float = 1.15
    line_spacing_mode: str = "multiple"  # multiple | exact
    keep_with_next: bool = False
    widow_orphan: bool = True


class ParagraphDialog(QDialog):
    """Absatzformat: gilt für die aktuelle Auswahl, sonst das ganze Dokument."""

    def __init__(self, spec: ParagraphFormatSpec | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("paragraphFormatDialog")
        self.setWindowTitle("Absatz")
        self.setModal(True)
        self.resize(420, 460)
        self._spec = spec or ParagraphFormatSpec()

        root = QVBoxLayout(self)

        space_box = QGroupBox("Abstand")
        space_form = QFormLayout(space_box)
        self.before_spin = QDoubleSpinBox()
        self.before_spin.setObjectName("paraSpaceBefore")
        self.after_spin = QDoubleSpinBox()
        self.after_spin.setObjectName("paraSpaceAfter")
        for spin, val in ((self.before_spin, self._spec.space_before_pt), (self.after_spin, self._spec.space_after_pt)):
            spin.setRange(0.0, 200.0)
            spin.setDecimals(1)
            spin.setSuffix(" pt")
            spin.setValue(float(val))
        space_form.addRow("Abstand davor", self.before_spin)
        space_form.addRow("Abstand danach", self.after_spin)
        root.addWidget(space_box)

        ind_box = QGroupBox("Einzug")
        ind_form = QFormLayout(ind_box)
        self.first_spin = QDoubleSpinBox()
        self.first_spin.setObjectName("paraFirstLineIndent")
        self.left_spin = QDoubleSpinBox()
        self.left_spin.setObjectName("paraLeftIndent")
        self.right_spin = QDoubleSpinBox()
        self.right_spin.setObjectName("paraRightIndent")
        for spin, val in (
            (self.first_spin, self._spec.first_line_indent_mm),
            (self.left_spin, self._spec.left_indent_mm),
            (self.right_spin, self._spec.right_indent_mm),
        ):
            spin.setRange(-50.0, 80.0)
            spin.setDecimals(1)
            spin.setSuffix(" mm")
            spin.setValue(float(val))
        ind_form.addRow("Erste Zeile", self.first_spin)
        ind_form.addRow("Links", self.left_spin)
        ind_form.addRow("Rechts", self.right_spin)
        root.addWidget(ind_box)

        ls_box = QGroupBox("Zeilenabstand")
        ls_form = QFormLayout(ls_box)
        self.spacing_combo = QComboBox()
        self.spacing_combo.setObjectName("paraLineSpacing")
        for label, _mode, _val in LINE_SPACING_PRESETS:
            self.spacing_combo.addItem(label)
        self.exact_spin = QDoubleSpinBox()
        self.exact_spin.setObjectName("paraLineSpacingExact")
        self.exact_spin.setRange(4.0, 72.0)
        self.exact_spin.setDecimals(1)
        self.exact_spin.setSuffix(" pt")
        self.exact_spin.setValue(12.0)
        self.spacing_combo.currentIndexChanged.connect(self._sync_exact)
        ls_form.addRow("Abstand", self.spacing_combo)
        ls_row = QHBoxLayout()
        ls_row.addWidget(self.exact_spin)
        ls_form.addRow("Genau", ls_row)
        root.addWidget(ls_box)

        flow_box = QGroupBox("Textfluss")
        flow_form = QFormLayout(flow_box)
        self.keep_cb = QCheckBox("Absätze nicht trennen (mit nächstem zusammenhalten)")
        self.keep_cb.setObjectName("paraKeepWithNext")
        self.keep_cb.setChecked(bool(self._spec.keep_with_next))
        self.widow_cb = QCheckBox("Absatzkontrolle (Witwen/Waisen)")
        self.widow_cb.setObjectName("paraWidowOrphan")
        self.widow_cb.setChecked(bool(self._spec.widow_orphan))
        flow_form.addRow(self.keep_cb)
        flow_form.addRow(self.widow_cb)
        root.addWidget(flow_box)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.setObjectName("paraDialogButtons")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._load_spacing()
        self._sync_exact()

    def _load_spacing(self) -> None:
        mode = (self._spec.line_spacing_mode or "multiple").lower()
        val = float(self._spec.line_spacing or 1.15)
        if mode == "exact":
            self.spacing_combo.setCurrentIndex(4)
            self.exact_spin.setValue(val if val >= 4.0 else 12.0)
            return
        best = 1
        best_d = 99.0
        for i, (_label, m, v) in enumerate(LINE_SPACING_PRESETS):
            if m != "multiple":
                continue
            d = abs(v - val)
            if d < best_d:
                best_d = d
                best = i
        self.spacing_combo.setCurrentIndex(best)

    def _sync_exact(self, *_args) -> None:
        exact = self.spacing_combo.currentIndex() == 4
        self.exact_spin.setEnabled(exact)

    def result_spec(self) -> ParagraphFormatSpec:
        idx = self.spacing_combo.currentIndex()
        if idx < 0:
            idx = 1
        _label, mode, val = LINE_SPACING_PRESETS[min(idx, len(LINE_SPACING_PRESETS) - 1)]
        if mode == "exact":
            val = float(self.exact_spin.value())
        return ParagraphFormatSpec(
            space_before_pt=float(self.before_spin.value()),
            space_after_pt=float(self.after_spin.value()),
            first_line_indent_mm=float(self.first_spin.value()),
            left_indent_mm=float(self.left_spin.value()),
            right_indent_mm=float(self.right_spin.value()),
            line_spacing=float(val),
            line_spacing_mode=mode,
            keep_with_next=bool(self.keep_cb.isChecked()),
            widow_orphan=bool(self.widow_cb.isChecked()),
        )
