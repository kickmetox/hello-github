"""Glyphen-Palette: Klick fügt Zeichen in den gewählten DTP-Textrahmen ein."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from instantlensdoc.features.glyph_palette import DEFAULT_BLOCKS, list_glyph_blocks, list_glyphs


class GlyphPaletteDialog(QDialog):
    glyphChosen = Signal(str)

    def __init__(self, parent=None, *, family: str = ""):
        super().__init__(parent)
        self.setObjectName("glyphPaletteDialog")
        self.setWindowTitle("Glyphen-Palette")
        self.resize(560, 480)
        self._chosen = ""
        root = QVBoxLayout(self)
        row = QHBoxLayout()
        self.family = QComboBox()
        self.family.setObjectName("glyphFamily")
        try:
            fams = list(QFontDatabase.families())
        except Exception:
            fams = ["serif", "sans-serif"]
        for f in fams:
            self.family.addItem(f)
        if family:
            idx = self.family.findText(family)
            if idx >= 0:
                self.family.setCurrentIndex(idx)
        self.block = QComboBox()
        self.block.setObjectName("glyphBlock")
        self.block.addItem("Standard", list(DEFAULT_BLOCKS))
        for name in list_glyph_blocks():
            self.block.addItem(name, [name])
        self.family.currentIndexChanged.connect(self._rebuild)
        self.block.currentIndexChanged.connect(self._rebuild)
        row.addWidget(QLabel("Schrift"))
        row.addWidget(self.family, 1)
        row.addWidget(QLabel("Block"))
        row.addWidget(self.block, 1)
        root.addLayout(row)
        self.preview = QLabel(" ")
        self.preview.setObjectName("glyphPreview")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet("font-size:36px;padding:8px;min-height:56px;")
        self.meta = QLabel("Zeichen wählen")
        self.meta.setWordWrap(True)
        root.addWidget(self.preview)
        root.addWidget(self.meta)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        self._grid.setSpacing(2)
        self.scroll.setWidget(self._grid_host)
        root.addWidget(self.scroll, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        insert = QPushButton("Einfügen")
        insert.setObjectName("glyphInsert")
        insert.clicked.connect(self._emit_insert)
        buttons.addButton(insert, QDialogButtonBox.ActionRole)
        root.addWidget(buttons)
        self._rebuild()

    def selected_glyph(self) -> str:
        return self._chosen

    def selected_family(self) -> str:
        return str(self.family.currentText() or "")

    def _rebuild(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        fam = self.selected_family()
        blocks = self.block.currentData() or list(DEFAULT_BLOCKS)
        glyphs = list_glyphs(fam, blocks=blocks, limit=420)
        font = QFont(fam)
        font.setPointSize(14)
        cols = 12
        for i, rec in enumerate(glyphs):
            btn = QToolButton()
            btn.setText(rec["char"])
            btn.setFont(font)
            btn.setToolTip(f"{rec['hex']}  {rec['name']}")
            btn.setFixedSize(36, 32)
            btn.clicked.connect(lambda _=False, r=rec: self._pick(r))
            self._grid.addWidget(btn, i // cols, i % cols)

    def _pick(self, rec: dict) -> None:
        self._chosen = rec["char"]
        self.preview.setText(rec["char"])
        font = QFont(self.selected_family())
        font.setPointSize(32)
        self.preview.setFont(font)
        self.meta.setText(f"{rec['hex']}  {rec['name']}  ({rec['block']})")

    def _emit_insert(self) -> None:
        if self._chosen:
            self.glyphChosen.emit(self._chosen)
            self.accept()
