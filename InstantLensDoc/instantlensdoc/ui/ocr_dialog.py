"""OCR-Dialog: Sprach-Preset + Ausgabe-Modus."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QRadioButton,
    QVBoxLayout,
)

from instantlensdoc.core.ocr import LANG_PRESETS, OcrOutputMode, list_installed_languages, tesseract_available


class OcrDialog(QDialog):
    """Preset-Sprache und Modus wählen; liefert lang + mode + optional Bildpfad."""

    def __init__(self, parent=None, *, need_file: bool = False, default_label: str = ""):
        super().__init__(parent)
        self.setWindowTitle("OCR")
        self.resize(420, 280)
        self.need_file = need_file
        self.selected_path: str | None = None

        layout = QVBoxLayout(self)
        ok, msg = tesseract_available()
        status = QLabel(msg if ok else f"Hinweis: {msg.splitlines()[0]}")
        status.setWordWrap(True)
        layout.addWidget(status)

        form = QFormLayout()
        self.lang_combo = QComboBox()
        for name, code in LANG_PRESETS.items():
            self.lang_combo.addItem(name, code)
        # Installierte Sprachen als Zusatzinfo
        installed = list_installed_languages()
        if installed:
            form.addRow(QLabel(f"Installiert: {', '.join(installed[:12])}"))
        form.addRow("Sprache", self.lang_combo)

        self.rb_editable = QRadioButton("Editierbarer Text (Editor)")
        self.rb_searchable = QRadioButton("Durchsuchbares Bild (PDF + Text-Sidecar)")
        self.rb_editable.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self.rb_editable)
        group.addButton(self.rb_searchable)
        mode_box = QVBoxLayout()
        mode_box.addWidget(self.rb_editable)
        mode_box.addWidget(self.rb_searchable)
        form.addRow("Ausgabe", mode_box)

        if default_label:
            form.addRow("Quelle", QLabel(default_label))
        layout.addLayout(form)

        if need_file:
            btn = QDialogButtonBox()
            pick = btn.addButton("Bild wählen…", QDialogButtonBox.ActionRole)
            pick.clicked.connect(self._pick)
            layout.addWidget(btn)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _pick(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Bild für OCR", "", "Bilder (*.png *.jpg *.jpeg *.tif *.tiff *.bmp)"
        )
        if path:
            self.selected_path = path

    def _accept(self):
        if self.need_file and not self.selected_path:
            self._pick()
            if not self.selected_path:
                return
        self.accept()

    def lang_code(self) -> str:
        return self.lang_combo.currentData() or "deu+eng"

    def output_mode(self) -> OcrOutputMode:
        if self.rb_searchable.isChecked():
            return OcrOutputMode.SEARCHABLE_IMAGE
        return OcrOutputMode.EDITABLE_TEXT
