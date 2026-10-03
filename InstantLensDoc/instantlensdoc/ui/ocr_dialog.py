"""OCR-Dialog: Sprach-Preset, DPI, optionaler Seitenbereich, Ausgabe-Modus."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QSpinBox,
    QTextBrowser,
    QVBoxLayout,
)

from instantlensdoc.core.app_settings import (
    get_ocr_attach_errors,
    get_ocr_dpi,
    get_ocr_lang,
)
from instantlensdoc.core.ocr import (
    DEFAULT_OCR_DPI,
    INSTALL_HINT_HTML,
    LANG_PRESETS,
    OCR_DPI_CHOICES,
    OcrOutputMode,
    TESSERACT_WIKI_URL,
    list_installed_languages,
    tesseract_available,
)


class OcrDialog(QDialog):
    """Preset-Sprache, DPI, optional von–bis; liefert lang + mode + dpi + range."""

    def __init__(
        self,
        parent=None,
        *,
        need_file: bool = False,
        default_label: str = "",
        page_count: int | None = None,
        show_page_range: bool = False,
    ):
        super().__init__(parent)
        self.setWindowTitle("OCR")
        self.resize(440, 340)
        self.need_file = need_file
        self.selected_path: str | None = None
        self._page_count = int(page_count) if page_count and page_count > 0 else 0
        self._show_page_range = bool(show_page_range)

        layout = QVBoxLayout(self)
        ok, msg = tesseract_available()
        if ok:
            status = QLabel(msg)
            status.setWordWrap(True)
            layout.addWidget(status)
        else:
            hint = QTextBrowser()
            hint.setOpenExternalLinks(True)
            hint.setMaximumHeight(140)
            hint.setHtml(
                INSTALL_HINT_HTML
                + f"<p><small>{msg.splitlines()[0] if msg else 'Tesseract fehlt'}</small></p>"
            )
            hint.setToolTip(TESSERACT_WIKI_URL)
            layout.addWidget(hint)

        form = QFormLayout()
        self.lang_combo = QComboBox()
        self.lang_combo.setToolTip(
            "Sprach-Preset für Tesseract (deu/eng/…) — Settings-Default vorgewählt — 1.1.6"
        )
        default_lang = get_ocr_lang()
        pick = 0
        for i, (name, code) in enumerate(LANG_PRESETS.items()):
            self.lang_combo.addItem(name, code)
            if code == default_lang:
                pick = i
        self.lang_combo.setCurrentIndex(pick)
        # Installierte Sprachen als Zusatzinfo
        installed = list_installed_languages()
        if installed:
            form.addRow(QLabel(f"Installiert: {', '.join(installed[:12])}"))
        form.addRow("Sprach-Preset", self.lang_combo)

        self.dpi_combo = QComboBox()
        self.dpi_combo.setToolTip(
            "OCR-Render-DPI (150 oder 300) — Settings-Default vorgewählt — 1.1.6"
        )
        for d in OCR_DPI_CHOICES:
            self.dpi_combo.addItem(f"{d} DPI", int(d))
        default_dpi = get_ocr_dpi()
        try:
            idx_dpi = list(OCR_DPI_CHOICES).index(int(default_dpi))
        except ValueError:
            idx_dpi = list(OCR_DPI_CHOICES).index(DEFAULT_OCR_DPI)
        self.dpi_combo.setCurrentIndex(idx_dpi)
        form.addRow("DPI", self.dpi_combo)

        self.range_check = QCheckBox("Seitenbereich von–bis")
        self.range_check.setToolTip(
            "Optional: nur einen Seitenbereich OCR’en (leer = alle Seiten) — 1.1.2"
        )
        self.range_check.setChecked(False)
        self.page_from = QSpinBox()
        self.page_to = QSpinBox()
        max_p = self._page_count if self._page_count > 0 else 99999
        self.page_from.setRange(1, max_p)
        self.page_to.setRange(1, max_p)
        self.page_from.setValue(1)
        self.page_to.setValue(max_p if self._page_count > 0 else 1)
        self.page_from.setEnabled(False)
        self.page_to.setEnabled(False)
        self.range_check.toggled.connect(self._on_range_toggled)
        self.page_from.valueChanged.connect(self._clamp_range)
        range_row = QHBoxLayout()
        range_row.addWidget(QLabel("Von"))
        range_row.addWidget(self.page_from)
        range_row.addWidget(QLabel("Bis"))
        range_row.addWidget(self.page_to)
        if self._show_page_range:
            form.addRow(self.range_check)
            form.addRow("Seiten", range_row)
        else:
            self.range_check.setVisible(False)
            self.page_from.setVisible(False)
            self.page_to.setVisible(False)

        # Batch: Fehlerabschnitt optional anhängen — Settings-persistiert — 1.1.5
        self.attach_errors_check = QCheckBox("Fehler anhängen")
        self.attach_errors_check.setToolTip(
            "Seitenfehler als Abschnitt „OCR-Fehler“ an das Ergebnis-TXT anhängen "
            "(Einstellung wird gemerkt) — 1.1.5"
        )
        self.attach_errors_check.setChecked(get_ocr_attach_errors())
        if self._show_page_range:
            form.addRow(self.attach_errors_check)
        else:
            self.attach_errors_check.setVisible(False)

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

    def _on_range_toggled(self, checked: bool) -> None:
        self.page_from.setEnabled(bool(checked))
        self.page_to.setEnabled(bool(checked))

    def _clamp_range(self, *_args) -> None:
        if self.page_to.value() < self.page_from.value():
            self.page_to.setValue(self.page_from.value())

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
        if self._show_page_range and self.range_check.isChecked():
            self._clamp_range()
        self.accept()

    def lang_code(self) -> str:
        return self.lang_combo.currentData() or "deu+eng"

    def dpi(self) -> int:
        data = self.dpi_combo.currentData()
        try:
            return int(data) if data is not None else DEFAULT_OCR_DPI
        except (TypeError, ValueError):
            return DEFAULT_OCR_DPI

    def page_range(self) -> tuple[int | None, int | None]:
        """(von, bis) 1-basiert inkl., oder (None, None) wenn nicht begrenzt."""
        if not self._show_page_range or not self.range_check.isChecked():
            return None, None
        a = int(self.page_from.value())
        b = int(self.page_to.value())
        if b < a:
            b = a
        return a, b

    def attach_errors(self) -> bool:
        """True = OCR-Fehler-Abschnitt an Ergebnis anhängen (Settings) — 1.1.5."""
        if not self._show_page_range:
            return True
        return bool(self.attach_errors_check.isChecked())

    def output_mode(self) -> OcrOutputMode:
        if self.rb_searchable.isChecked():
            return OcrOutputMode.SEARCHABLE_IMAGE
        return OcrOutputMode.EDITABLE_TEXT
