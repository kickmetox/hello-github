"""Einstellungen: Theme, OCR-Sprache, Standardpfade."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from instantlensdoc.core.app_settings import (
    get_batch_output_dir,
    get_default_open_dir,
    get_ocr_lang,
    get_theme,
    save_settings,
    set_batch_output_dir,
    set_default_open_dir,
    set_ocr_lang,
    set_theme,
)
from instantlensdoc.core.ocr import LANG_PRESETS
from instantlensdoc.ui.theme import apply_theme


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Einstellungen")
        self.resize(480, 260)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("InstantLens Doc — Anwendungseinstellungen"))

        form = QFormLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Hell", "light")
        self.theme_combo.addItem("Dunkel", "dark")
        cur_theme = get_theme()
        self.theme_combo.setCurrentIndex(1 if cur_theme == "dark" else 0)
        form.addRow("Design", self.theme_combo)

        self.lang_combo = QComboBox()
        cur_lang = get_ocr_lang()
        pick = 0
        for i, (name, code) in enumerate(LANG_PRESETS.items()):
            self.lang_combo.addItem(name, code)
            if code == cur_lang:
                pick = i
        self.lang_combo.setCurrentIndex(pick)
        form.addRow("OCR-Sprache (Standard)", self.lang_combo)

        self.batch_dir = QLineEdit()
        bd = get_batch_output_dir()
        self.batch_dir.setText(str(bd) if bd else "")
        batch_row = QHBoxLayout()
        batch_row.addWidget(self.batch_dir)
        btn_b = QPushButton("…")
        btn_b.clicked.connect(lambda: self._pick_dir(self.batch_dir))
        batch_row.addWidget(btn_b)
        form.addRow("Batch-Ausgabeordner", batch_row)

        self.open_dir = QLineEdit()
        od = get_default_open_dir()
        self.open_dir.setText(str(od) if od else "")
        open_row = QHBoxLayout()
        open_row.addWidget(self.open_dir)
        btn_o = QPushButton("…")
        btn_o.clicked.connect(lambda: self._pick_dir(self.open_dir))
        open_row.addWidget(btn_o)
        form.addRow("Standard-Ordner (Öffnen)", open_row)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _pick_dir(self, field: QLineEdit):
        start = field.text().strip() or str(Path.home())
        path = QFileDialog.getExistingDirectory(self, "Ordner wählen", start)
        if path:
            field.setText(path)

    def _save(self):
        theme = self.theme_combo.currentData() or "light"
        lang = self.lang_combo.currentData() or "deu+eng"
        set_theme("dark" if theme == "dark" else "light")
        set_ocr_lang(str(lang))
        batch = self.batch_dir.text().strip()
        if batch:
            set_batch_output_dir(batch)
        else:
            save_settings({"batch_output_dir": ""})
        op = self.open_dir.text().strip()
        if op:
            set_default_open_dir(op)
        else:
            save_settings({"default_open_dir": ""})
        apply_theme(mode=get_theme())
        self.accept()
