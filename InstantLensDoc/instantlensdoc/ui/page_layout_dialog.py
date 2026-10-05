"""Dialog: Seitenlayout für den Texteditor (DTP-Presets, Ränder, Ausrichtung) — 2.6.53."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from ild_pdf.pages import convert_pt, format_size_pair, pt_to_mm, to_pt
from instantlensdoc.core.app_settings import get_page_size_unit, set_page_size_unit
from instantlensdoc.core.editor_page_layout import (
    CUSTOM_PRESET,
    EditorPageLayout,
    page_presets,
    preset_size,
)


class PageLayoutDialog(QDialog):
    """Seitenformat/Ausrichtung/Ränder — wirkt auf Textumbruch und ``QTextDocument.pageSize``."""

    def __init__(
        self,
        layout: EditorPageLayout | None = None,
        parent=None,
        *,
        rich_document: bool = False,
    ):
        super().__init__(parent)
        self.setObjectName("pageLayoutDialog")
        self.setWindowTitle("Seitenlayout")
        self.setModal(True)
        self.resize(460, 520)
        self._layout = EditorPageLayout.from_dict((layout or EditorPageLayout()).to_dict())
        self._unit = get_page_size_unit()
        self._rich_document = bool(rich_document)
        self._updating = False

        root = QVBoxLayout(self)

        unit_row = QHBoxLayout()
        unit_row.addWidget(QLabel("Einheit:"))
        self.unit_combo = QComboBox()
        self.unit_combo.setObjectName("pageLayoutUnit")
        self.unit_combo.addItem("mm", "mm")
        self.unit_combo.addItem("inch", "inch")
        self.unit_combo.setCurrentIndex(1 if self._unit == "inch" else 0)
        self.unit_combo.currentIndexChanged.connect(self._on_unit_changed)
        unit_row.addWidget(self.unit_combo)
        unit_row.addStretch(1)
        root.addLayout(unit_row)

        # --- Seitenformat ----------------------------------------------------
        size_box = QGroupBox("Seitenformat (DTP-Presets)")
        size_form = QFormLayout(size_box)
        self.preset = QComboBox()
        self.preset.setObjectName("pageLayoutPreset")
        self._fill_presets()
        self.preset.currentIndexChanged.connect(self._on_preset)
        size_form.addRow("Preset", self.preset)
        self.w_spin = QDoubleSpinBox()
        self.w_spin.setObjectName("pageLayoutWidth")
        self.h_spin = QDoubleSpinBox()
        self.h_spin.setObjectName("pageLayoutHeight")
        for s in (self.w_spin, self.h_spin):
            s.setRange(1.0, 2000.0)
            s.setDecimals(2)
            s.valueChanged.connect(self._on_custom_size)
        self._w_label = QLabel()
        self._h_label = QLabel()
        size_form.addRow(self._w_label, self.w_spin)
        size_form.addRow(self._h_label, self.h_spin)

        ori_row = QHBoxLayout()
        self.rb_portrait = QRadioButton("Hochformat")
        self.rb_portrait.setObjectName("pageLayoutPortrait")
        self.rb_landscape = QRadioButton("Querformat")
        self.rb_landscape.setObjectName("pageLayoutLandscape")
        grp = QButtonGroup(self)
        grp.addButton(self.rb_portrait)
        grp.addButton(self.rb_landscape)
        self.rb_portrait.toggled.connect(self._refresh_info)
        ori_row.addWidget(self.rb_portrait)
        ori_row.addWidget(self.rb_landscape)
        ori_row.addStretch(1)
        size_form.addRow("Ausrichtung", ori_row)
        root.addWidget(size_box)

        # --- Ränder ----------------------------------------------------------
        margin_box = QGroupBox("Ränder")
        margin_form = QFormLayout(margin_box)
        self.m_top = QDoubleSpinBox()
        self.m_bottom = QDoubleSpinBox()
        self.m_left = QDoubleSpinBox()
        self.m_right = QDoubleSpinBox()
        self._margin_labels: dict[str, QLabel] = {}
        for key, spin, name in (
            ("top", self.m_top, "Oben"),
            ("bottom", self.m_bottom, "Unten"),
            ("left", self.m_left, "Links / innen"),
            ("right", self.m_right, "Rechts / außen"),
        ):
            spin.setObjectName(f"pageLayoutMargin_{key}")
            spin.setRange(0.0, 200.0)
            spin.setDecimals(2)
            spin.valueChanged.connect(self._refresh_info)
            lab = QLabel(name)
            self._margin_labels[key] = lab
            margin_form.addRow(lab, spin)
        btn_sp = QPushButton("Satzspiegel-Vorschlag (DTP)")
        btn_sp.setObjectName("pageLayoutSatzspiegel")
        btn_sp.setToolTip(
            "Ränder aus dem Satzspiegel-Preset des gewählten Formats übernehmen "
            "(ild_pdf.page_layout.satzspiegel_for_format)"
        )
        btn_sp.clicked.connect(self._apply_satzspiegel)
        margin_form.addRow(btn_sp)
        root.addWidget(margin_box)

        # --- Geltung ---------------------------------------------------------
        scope_box = QGroupBox("Anwenden auf")
        scope_form = QFormLayout(scope_box)
        self.scope = QComboBox()
        self.scope.setObjectName("pageLayoutScope")
        self.scope.addItem("Word-/DOCX-/HTML-Dokumente (empfohlen)", "rich")
        self.scope.addItem("Alle Textdokumente (auch TXT/Markdown)", "all")
        self.scope.addItem("Aus — Umbruch am Fensterrand", "off")
        self.scope.currentIndexChanged.connect(self._refresh_info)
        scope_form.addRow("Geltung", self.scope)
        root.addWidget(scope_box)

        self.info_label = QLabel()
        self.info_label.setObjectName("pageLayoutInfo")
        self.info_label.setWordWrap(True)
        self.info_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        root.addWidget(self.info_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._load_from_layout()

    # ---- Hilfen -----------------------------------------------------------
    def _unit_suffix(self) -> str:
        return "in" if self._unit == "inch" else "mm"

    def _fill_presets(self) -> None:
        cur = self.preset.currentData() if self.preset.count() else None
        self.preset.blockSignals(True)
        self.preset.clear()
        for name, w, h in page_presets():
            self.preset.addItem(f"{name} ({format_size_pair(w, h, self._unit)})", name)
        self.preset.addItem(f"— {CUSTOM_PRESET} —", CUSTOM_PRESET)
        if cur is not None:
            idx = self.preset.findData(cur)
            self.preset.setCurrentIndex(idx if idx >= 0 else self.preset.count() - 1)
        self.preset.blockSignals(False)

    def _load_from_layout(self) -> None:
        lay = self._layout
        self._updating = True
        try:
            idx = self.preset.findData(lay.preset)
            if idx < 0:
                idx = self.preset.findData(CUSTOM_PRESET)
            self.preset.setCurrentIndex(max(0, idx))
            self.w_spin.setValue(convert_pt(lay.width_pt, self._unit))
            self.h_spin.setValue(convert_pt(lay.height_pt, self._unit))
            (self.rb_landscape if lay.orientation == "landscape" else self.rb_portrait).setChecked(True)
            for spin, mm in (
                (self.m_top, lay.margin_top_mm),
                (self.m_bottom, lay.margin_bottom_mm),
                (self.m_left, lay.margin_left_mm),
                (self.m_right, lay.margin_right_mm),
            ):
                spin.setValue(convert_pt(to_pt(mm, "mm"), self._unit))
            sidx = self.scope.findData(lay.scope if lay.enabled else "off")
            self.scope.setCurrentIndex(max(0, sidx))
            u = self._unit_suffix()
            self._w_label.setText(f"Breite ({u})")
            self._h_label.setText(f"Höhe ({u})")
            for key, lab in self._margin_labels.items():
                base = {"top": "Oben", "bottom": "Unten", "left": "Links / innen", "right": "Rechts / außen"}[key]
                lab.setText(f"{base} ({u})")
        finally:
            self._updating = False
        self._refresh_info()

    def _collect(self) -> EditorPageLayout:
        lay = EditorPageLayout.from_dict(self._layout.to_dict())
        name = self.preset.currentData() or CUSTOM_PRESET
        if name != CUSTOM_PRESET and preset_size(str(name)) is not None:
            lay.with_preset(str(name))
        else:
            lay.preset = CUSTOM_PRESET
            lay.width_pt = to_pt(self.w_spin.value(), self._unit)
            lay.height_pt = to_pt(self.h_spin.value(), self._unit)
        lay.orientation = "landscape" if self.rb_landscape.isChecked() else "portrait"
        lay.margin_top_mm = pt_to_mm(to_pt(self.m_top.value(), self._unit))
        lay.margin_bottom_mm = pt_to_mm(to_pt(self.m_bottom.value(), self._unit))
        lay.margin_left_mm = pt_to_mm(to_pt(self.m_left.value(), self._unit))
        lay.margin_right_mm = pt_to_mm(to_pt(self.m_right.value(), self._unit))
        scope = str(self.scope.currentData() or "rich")
        lay.enabled = scope != "off"
        lay.scope = scope
        lay._clamp()
        return lay

    # ---- Slots ------------------------------------------------------------
    def _on_unit_changed(self) -> None:
        self._layout = self._collect()
        data = self.unit_combo.currentData() or "mm"
        self._unit = "inch" if data == "inch" else "mm"
        set_page_size_unit(self._unit)
        self._fill_presets()
        self._load_from_layout()

    def _on_preset(self) -> None:
        if self._updating:
            return
        name = self.preset.currentData()
        size = preset_size(str(name)) if name and name != CUSTOM_PRESET else None
        if size is not None:
            self._updating = True
            try:
                self.w_spin.setValue(convert_pt(size[0], self._unit))
                self.h_spin.setValue(convert_pt(size[1], self._unit))
            finally:
                self._updating = False
        self._refresh_info()

    def _on_custom_size(self) -> None:
        if self._updating:
            return
        # Manuelle Maße → Preset auf Benutzerdefiniert, außer sie treffen ein Preset
        w_pt = to_pt(self.w_spin.value(), self._unit)
        h_pt = to_pt(self.h_spin.value(), self._unit)
        hit = None
        for name, w, h in page_presets():
            if abs(w - w_pt) < 0.6 and abs(h - h_pt) < 0.6:
                hit = name
                break
        self._updating = True
        try:
            idx = self.preset.findData(hit or CUSTOM_PRESET)
            if idx >= 0:
                self.preset.setCurrentIndex(idx)
        finally:
            self._updating = False
        self._refresh_info()

    def _apply_satzspiegel(self) -> None:
        lay = self._collect().apply_satzspiegel()
        self._updating = True
        try:
            self.m_top.setValue(convert_pt(to_pt(lay.margin_top_mm, "mm"), self._unit))
            self.m_bottom.setValue(convert_pt(to_pt(lay.margin_bottom_mm, "mm"), self._unit))
            self.m_left.setValue(convert_pt(to_pt(lay.margin_left_mm, "mm"), self._unit))
            self.m_right.setValue(convert_pt(to_pt(lay.margin_right_mm, "mm"), self._unit))
        finally:
            self._updating = False
        self._refresh_info()

    def _refresh_info(self, *_args) -> None:
        if self._updating:
            return
        try:
            lay = self._collect()
        except Exception as e:  # pragma: no cover - defensive
            self.info_label.setText(str(e))
            return
        w, h = lay.page_size_pt()
        px = int(round(lay.text_width_px(96.0)))
        applies = lay.applies_to(self._rich_document)
        hint = (
            "Gilt für das aktuelle Dokument."
            if applies
            else (
                "Gilt nicht für das aktuelle Dokument (Plaintext) — Geltung „Alle“ wählen."
                if lay.enabled and lay.scope != "off"
                else "Seitenlayout aus: Umbruch am Fensterrand."
            )
        )
        self.info_label.setText(
            f"Seite {format_size_pair(w, h, self._unit)} · Textspalte "
            f"{format_size_pair(lay.text_width_pt(), lay.text_height_pt(), self._unit)} "
            f"(≈ {px} px bei 96 dpi)\n{hint}"
        )

    # ---- Ergebnis ---------------------------------------------------------
    def result_layout(self) -> EditorPageLayout:
        return self._collect()
