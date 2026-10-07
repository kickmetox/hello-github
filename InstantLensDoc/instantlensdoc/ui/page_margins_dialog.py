"""Dialog: Seitenränder in Millimeter (Word: Benutzerdefiniert)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
)

from instantlensdoc.core.editor_page_layout import (
    MARGIN_PRESETS,
    EditorPageLayout,
)


class PageMarginsDialog(QDialog):
    """Vier mm-Felder plus Normal/Schmal/Breit — kein Stub."""

    def __init__(self, layout: EditorPageLayout | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("pageMarginsDialog")
        self.setWindowTitle("Seitenränder")
        self.setModal(True)
        self.resize(360, 280)
        self._layout = EditorPageLayout.from_dict((layout or EditorPageLayout()).to_dict())

        root = QVBoxLayout(self)
        preset_row = QHBoxLayout()
        for key, label in (("normal", "Normal"), ("schmal", "Schmal"), ("breit", "Breit")):
            btn = QPushButton(label)
            btn.setObjectName(f"pageMarginsPreset_{key}")
            btn.clicked.connect(lambda _=False, k=key: self._apply_preset(k))
            preset_row.addWidget(btn)
        root.addLayout(preset_row)

        form = QFormLayout()
        self.m_top = QDoubleSpinBox()
        self.m_bottom = QDoubleSpinBox()
        self.m_left = QDoubleSpinBox()
        self.m_right = QDoubleSpinBox()
        for spin, key, name, val in (
            (self.m_top, "top", "Oben (mm)", self._layout.margin_top_mm),
            (self.m_bottom, "bottom", "Unten (mm)", self._layout.margin_bottom_mm),
            (self.m_left, "left", "Links (mm)", self._layout.margin_left_mm),
            (self.m_right, "right", "Rechts (mm)", self._layout.margin_right_mm),
        ):
            spin.setObjectName(f"pageMargins_{key}")
            spin.setRange(0.0, 100.0)
            spin.setDecimals(1)
            spin.setSuffix(" mm")
            spin.setValue(float(val))
            form.addRow(name, spin)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _apply_preset(self, name: str) -> None:
        vals = MARGIN_PRESETS.get(name)
        if not vals:
            return
        top, bottom, left, right = vals
        self.m_top.setValue(top)
        self.m_bottom.setValue(bottom)
        self.m_left.setValue(left)
        self.m_right.setValue(right)

    def result_margins_mm(self) -> tuple[float, float, float, float]:
        return (
            float(self.m_top.value()),
            float(self.m_bottom.value()),
            float(self.m_left.value()),
            float(self.m_right.value()),
        )

    def result_layout(self) -> EditorPageLayout:
        top, bottom, left, right = self.result_margins_mm()
        return EditorPageLayout.from_dict(self._layout.to_dict()).set_margins(
            top, bottom, left, right
        )
