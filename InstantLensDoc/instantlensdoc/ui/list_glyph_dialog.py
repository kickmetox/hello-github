"""Dialog: Aufzählungszeichen wählen."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QVBoxLayout,
)

from instantlensdoc.ui.rich_lists import BULLET_GLYPHS, DEFAULT_BULLET


class ListGlyphDialog(QDialog):
    """Wählbares Bullet-Zeichen für die aktuelle Liste/Auswahl."""

    def __init__(self, current: str = DEFAULT_BULLET, parent=None):
        super().__init__(parent)
        self.setObjectName("listGlyphDialog")
        self.setWindowTitle("Aufzählungszeichen")
        self.setModal(True)
        self.resize(320, 140)

        root = QVBoxLayout(self)
        form = QFormLayout()
        self.glyph_combo = QComboBox()
        self.glyph_combo.setObjectName("listGlyphCombo")
        for g in BULLET_GLYPHS:
            self.glyph_combo.addItem(f"{g}  Aufzählung", g)
        cur = (current or DEFAULT_BULLET).strip() or DEFAULT_BULLET
        idx = self.glyph_combo.findData(cur)
        self.glyph_combo.setCurrentIndex(idx if idx >= 0 else 0)
        form.addRow("Zeichen", self.glyph_combo)
        root.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def result_glyph(self) -> str:
        data = self.glyph_combo.currentData()
        return str(data or DEFAULT_BULLET)
