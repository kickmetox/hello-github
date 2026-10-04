"""OCR-Dialog: Sprach-Preset, DPI, optionaler Seitenbereich, Ausgabe-Modus."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
)

from instantlensdoc.core.app_settings import (
    OCR_TABLE_CSV_DELIMITER_LABELS,
    OCR_TABLE_CSV_DELIMITERS,
    get_ocr_attach_errors,
    get_ocr_defaults_toast_sec,
    get_ocr_dpi,
    get_ocr_lang,
    get_ocr_table_csv_delimiter,
    get_ocr_table_csv_utf8_bom,
    set_ocr_attach_errors,
    set_ocr_dpi,
    set_ocr_lang,
    set_ocr_table_csv_delimiter,
    set_ocr_table_csv_utf8_bom,
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
            "Sprach-Preset für Tesseract (deu/eng/…) — Settings-Default vorgewählt — 1.1.6–1.1.8"
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

        # Sprach-Preset + „Als Defaults speichern“ nebeneinander — 1.1.7/1.1.8
        lang_row = QHBoxLayout()
        lang_row.addWidget(self.lang_combo, 1)
        self.btn_save_defaults = QPushButton("Als Defaults speichern")
        self.btn_save_defaults.setToolTip(
            "Aktuelles Sprach-Preset und DPI als Settings-Defaults speichern "
            "(ohne Dialog zu schließen); Toast (Dauer Settings 1/2/3 s) + "
            "Feld-Highlight + Accessibility-Announcement — 1.1.9"
        )
        self.btn_save_defaults.clicked.connect(self._save_as_defaults)
        lang_row.addWidget(self.btn_save_defaults)
        form.addRow("Sprach-Preset", lang_row)

        self.dpi_combo = QComboBox()
        self.dpi_combo.setToolTip(
            "OCR-Render-DPI (150 oder 300) — Settings-Default vorgewählt — 1.1.6–1.1.9"
        )
        for d in OCR_DPI_CHOICES:
            self.dpi_combo.addItem(f"{d} DPI", int(d))
        default_dpi = get_ocr_dpi()
        try:
            idx_dpi = list(OCR_DPI_CHOICES).index(int(default_dpi))
        except ValueError:
            idx_dpi = list(OCR_DPI_CHOICES).index(DEFAULT_OCR_DPI)
        self.dpi_combo.setCurrentIndex(idx_dpi)
        dpi_row = QHBoxLayout()
        dpi_row.addWidget(self.dpi_combo, 1)
        self.defaults_feedback = QLabel("")
        self.defaults_feedback.setStyleSheet("color: #2a7; font-size: 11px;")
        self.defaults_feedback.setToolTip(
            "Toast/Status nach „Als Defaults speichern“ — Dauer in Settings "
            "(1/2/3 s); Screenreader-Announcement — 1.1.9"
        )
        self.defaults_feedback.setAccessibleName("")
        self.defaults_feedback.setAccessibleDescription(
            "OCR-Defaults-Toast — Accessibility-Announcement — 1.1.9"
        )
        dpi_row.addWidget(self.defaults_feedback)
        form.addRow("DPI", dpi_row)
        self._defaults_hl_token = 0
        self._defaults_toast_token = 0
        self._defaults_hl_style = (
            "QComboBox { background-color: #d8f5e3; border: 1px solid #2a7; }"
        )

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
        self.rb_layout = QRadioButton("Text mit Layout-Erhalt (Blöcke / Lesereihenfolge)")
        self.rb_layout.setObjectName("ocrModeLayoutPreserve")
        self.rb_layout.setToolTip(
            "Tesseract-Blöcke in Lesereihenfolge; Sidecar *.ildocr.txt + optional hOCR/TSV — 2.6.5"
        )
        self.rb_searchable = QRadioButton("Durchsuchbares Bild (PDF + Text-Sidecar)")
        self.rb_table_csv = QRadioButton("Tabelle als CSV (heuristisch)")
        self.rb_table_csv.setToolTip(
            "Grobe Tabellenerkennung aus OCR → CSV; Trennzeichen/BOM in Optionen — 1.9.1"
        )
        self.rb_layout.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self.rb_editable)
        group.addButton(self.rb_layout)
        group.addButton(self.rb_searchable)
        group.addButton(self.rb_table_csv)
        mode_box = QVBoxLayout()
        mode_box.addWidget(self.rb_editable)
        mode_box.addWidget(self.rb_layout)
        mode_box.addWidget(self.rb_searchable)
        mode_box.addWidget(self.rb_table_csv)
        form.addRow("Ausgabe", mode_box)

        # Layout-Sidecars — 2.6.5
        self.layout_hocr_check = QCheckBox("hOCR Sidecar (*.ildocr.hocr)")
        self.layout_hocr_check.setObjectName("ocrLayoutHocr")
        self.layout_hocr_check.setChecked(True)
        self.layout_hocr_check.setToolTip(
            "Tesseract hOCR mit Bounding-Boxes neben dem Text speichern — 2.6.5"
        )
        self.layout_tsv_check = QCheckBox("TSV Sidecar (*.ildocr.tsv)")
        self.layout_tsv_check.setObjectName("ocrLayoutTsv")
        self.layout_tsv_check.setChecked(True)
        self.layout_tsv_check.setToolTip(
            "Tesseract TSV (Wörter + Koordinaten) speichern — 2.6.5"
        )
        self._layout_opts_label = QLabel("Layout-Sidecars")
        form.addRow(self._layout_opts_label, self.layout_hocr_check)
        form.addRow("", self.layout_tsv_check)

        # Tabellen-CSV Optionen — 1.9.1
        self.csv_delim_combo = QComboBox()
        cur_delim = get_ocr_table_csv_delimiter()
        delim_pick = 0
        for i, d in enumerate(OCR_TABLE_CSV_DELIMITERS):
            self.csv_delim_combo.addItem(
                OCR_TABLE_CSV_DELIMITER_LABELS.get(d, d), d
            )
            if d == cur_delim:
                delim_pick = i
        self.csv_delim_combo.setCurrentIndex(delim_pick)
        self.csv_delim_combo.setToolTip(
            "CSV-Trennzeichen: Semikolon, Komma oder Tab — 1.9.1"
        )
        self.csv_bom_check = QCheckBox("UTF-8 BOM (Excel)")
        self.csv_bom_check.setChecked(get_ocr_table_csv_utf8_bom())
        self.csv_bom_check.setToolTip(
            "UTF-8 mit BOM für Excel-Kompatibilität (abschaltbar) — 1.9.1"
        )
        self._csv_opts_label = QLabel("CSV-Optionen")
        form.addRow(self._csv_opts_label, self.csv_delim_combo)
        form.addRow("", self.csv_bom_check)
        self.rb_editable.toggled.connect(self._sync_mode_opts_visible)
        self.rb_layout.toggled.connect(self._sync_mode_opts_visible)
        self.rb_searchable.toggled.connect(self._sync_mode_opts_visible)
        self.rb_table_csv.toggled.connect(self._sync_mode_opts_visible)
        self._sync_mode_opts_visible()

        # OCR → Word-Suite Handoff — 2.6.15
        self.word_suite_check = QCheckBox("In Word-Suite öffnen/übernehmen")
        self.word_suite_check.setObjectName("ocrWordSuiteHandoff")
        self.word_suite_check.setChecked(True)
        self.word_suite_check.setToolTip(
            "Erkannten Text (Blöcke/Lesereihenfolge) als editierbares Word-Suite-Dokument "
            "öffnen — nicht nur Sidecar-Anzeige; weiterformatieren/exportieren — 2.6.15"
        )
        self.word_suite_auto_format = QCheckBox("Auto-Format nach Übernahme")
        self.word_suite_auto_format.setObjectName("ocrWordSuiteAutoFormat")
        self.word_suite_auto_format.setChecked(True)
        self.word_suite_auto_format.setToolTip(
            "Style-Heuristik (Überschriften/Fließtext) aus 2.6.10 anwenden — 2.6.15"
        )
        form.addRow(self.word_suite_check)
        form.addRow("", self.word_suite_auto_format)

        # Handschriftenerkennung (Basis-Hook Tesseract PSM) — 2.6.18
        from instantlensdoc.core.i18n import tr as _tr_hw
        from instantlensdoc.core.ocr import HANDWRITING_PSM_PRESETS, DEFAULT_HANDWRITING_PSM

        self.handwriting_check = QCheckBox(_tr_hw("handwriting_title"))
        self.handwriting_check.setObjectName("ocrHandwritingMode")
        self.handwriting_check.setChecked(False)
        self.handwriting_check.setToolTip(_tr_hw("handwriting_hint"))
        self.handwriting_psm = QComboBox()
        self.handwriting_psm.setObjectName("ocrHandwritingPsm")
        for name, code in HANDWRITING_PSM_PRESETS.items():
            self.handwriting_psm.addItem(f"{name} (PSM {code})", int(code))
        self.handwriting_psm.setCurrentIndex(0)
        self.handwriting_psm.setEnabled(False)
        self.handwriting_check.toggled.connect(self.handwriting_psm.setEnabled)
        form.addRow(self.handwriting_check)
        form.addRow(_tr_hw("handwriting_mode"), self.handwriting_psm)
        _ = DEFAULT_HANDWRITING_PSM

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

    def _flash_defaults_fields(self) -> None:
        """Kurz-Highlight für Sprach-/DPI-Felder nach Defaults-Speichern — 1.1.8."""
        self._defaults_hl_token = int(getattr(self, "_defaults_hl_token", 0)) + 1
        token = self._defaults_hl_token
        widgets = [self.lang_combo, self.dpi_combo]
        if self._show_page_range and self.attach_errors_check.isVisible():
            widgets.append(self.attach_errors_check)
        for w in widgets:
            w.setStyleSheet(self._defaults_hl_style)

        def _clear() -> None:
            if token != getattr(self, "_defaults_hl_token", 0):
                return
            for w in widgets:
                w.setStyleSheet("")

        QTimer.singleShot(900, _clear)

    def _announce_defaults_toast(self, msg: str) -> None:
        """Accessibility-Announcement für OCR-Defaults-Toast — 1.1.9."""
        self.defaults_feedback.setAccessibleName(msg)
        self.defaults_feedback.setAccessibleDescription(msg)
        try:
            from PySide6.QtGui import QAccessible, QAccessibleAnnouncementEvent

            ev = QAccessibleAnnouncementEvent(self.defaults_feedback, msg)
            QAccessible.updateAccessibility(ev)
        except Exception:
            try:
                from PySide6.QtGui import QAccessible, QAccessibleEvent

                ev = QAccessibleEvent(
                    self.defaults_feedback, QAccessible.Event.NameChanged
                )
                QAccessible.updateAccessibility(ev)
            except Exception:
                pass

    def _show_defaults_toast(self, msg: str) -> None:
        """Toast anzeigen, nach Settings-Dauer (1/2/3 s) ausblenden + announce — 1.1.9."""
        sec = get_ocr_defaults_toast_sec()
        ms = max(1, int(sec)) * 1000
        self._defaults_toast_token = (
            int(getattr(self, "_defaults_toast_token", 0)) + 1
        )
        token = self._defaults_toast_token
        self.defaults_feedback.setText(msg)
        self._announce_defaults_toast(msg)

        def _clear() -> None:
            if token != getattr(self, "_defaults_toast_token", 0):
                return
            if (self.defaults_feedback.text() or "") == msg:
                self.defaults_feedback.setText("")
                self.defaults_feedback.setAccessibleName("")

        QTimer.singleShot(ms, _clear)
        parent = self.parent()
        if parent is not None and hasattr(parent, "statusBar"):
            try:
                parent.statusBar().showMessage(msg, ms)
            except Exception:
                pass
        elif parent is not None and hasattr(parent, "_set_status"):
            try:
                parent._set_status(msg)
            except Exception:
                pass

    def _save_as_defaults(self) -> None:
        """Sprach-Preset + DPI (+ Fehler-Toggle) sofort speichern; Toast + Highlight — 1.1.9."""
        try:
            set_ocr_lang(self.lang_code())
            set_ocr_dpi(self.dpi())
            if self._show_page_range:
                set_ocr_attach_errors(self.attach_errors())
            msg = "OCR-Defaults gespeichert"
            self._show_defaults_toast(msg)
            self._flash_defaults_fields()
        except Exception:
            self.defaults_feedback.setText("Speichern fehlgeschlagen")

    def _pick(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Bild für OCR", "", "Bilder (*.png *.jpg *.jpeg *.tif *.tiff *.bmp)"
        )
        if path:
            self.selected_path = path

    def _sync_csv_opts_visible(self, *_args) -> None:
        """Kompatibel: leitet auf Mode-Opts um — 2.6.5."""
        self._sync_mode_opts_visible()

    def _sync_mode_opts_visible(self, *_args) -> None:
        csv_on = bool(self.rb_table_csv.isChecked())
        self.csv_delim_combo.setVisible(csv_on)
        self.csv_bom_check.setVisible(csv_on)
        self._csv_opts_label.setVisible(csv_on)
        layout_on = bool(
            self.rb_layout.isChecked() or self.rb_searchable.isChecked()
        )
        self.layout_hocr_check.setVisible(layout_on)
        self.layout_tsv_check.setVisible(layout_on)
        self._layout_opts_label.setVisible(layout_on)

    def _accept(self):
        if self.need_file and not self.selected_path:
            self._pick()
            if not self.selected_path:
                return
        if self._show_page_range and self.range_check.isChecked():
            self._clamp_range()
        # CSV-Optionen persistieren wenn Tabellen-Modus — 1.9.1
        if self.rb_table_csv.isChecked():
            try:
                set_ocr_table_csv_delimiter(str(self.csv_delimiter()))
                set_ocr_table_csv_utf8_bom(self.csv_utf8_bom())
            except Exception:
                pass
        self.accept()

    def csv_delimiter(self) -> str:
        data = self.csv_delim_combo.currentData()
        return str(data) if data is not None else ";"

    def csv_utf8_bom(self) -> bool:
        return bool(self.csv_bom_check.isChecked())

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
        if self.rb_table_csv.isChecked():
            return OcrOutputMode.TABLE_CSV
        if self.rb_searchable.isChecked():
            return OcrOutputMode.SEARCHABLE_IMAGE
        if self.rb_layout.isChecked():
            return OcrOutputMode.LAYOUT_PRESERVE
        return OcrOutputMode.EDITABLE_TEXT

    def write_hocr(self) -> bool:
        return bool(self.layout_hocr_check.isChecked())

    def write_tsv(self) -> bool:
        return bool(self.layout_tsv_check.isChecked())

    def open_in_word_suite(self) -> bool:
        """True = OCR-Ergebnis in Word-Suite übernehmen — 2.6.15."""
        return bool(self.word_suite_check.isChecked())

    def word_suite_auto_format_enabled(self) -> bool:
        return bool(self.word_suite_auto_format.isChecked())

    def handwriting_enabled(self) -> bool:
        """True = Handschrift-PSM-Hook — 2.6.18."""
        return bool(getattr(self, "handwriting_check", None) and self.handwriting_check.isChecked())

    def handwriting_psm_value(self) -> int:
        from instantlensdoc.core.ocr import DEFAULT_HANDWRITING_PSM, normalize_handwriting_psm

        if not hasattr(self, "handwriting_psm"):
            return DEFAULT_HANDWRITING_PSM
        data = self.handwriting_psm.currentData()
        return normalize_handwriting_psm(data)


class CsvPreviewDialog(QDialog):
    """Vorschau erste N Zeilen; Trennzeichen live; Persistenz erst Speichern — 1.9.5."""

    def __init__(
        self,
        rows: list[list[str]] | None,
        parent=None,
        *,
        max_rows: int = 5,
        delimiter: str = ";",
        target_hint: str = "",
    ):
        super().__init__(parent)
        self.setWindowTitle("Tabellen-CSV — Vorschau")
        self.resize(680, 420)
        self._accepted_save = False
        self._all_rows = [list(r) for r in (rows or [])]
        self._max_rows = max(1, int(max_rows))
        self._delimiter = delimiter if delimiter in OCR_TABLE_CSV_DELIMITERS else ";"
        # Ausgangswert für Abbruch-Reset — Persistenz erst bei Speichern — 1.9.4/1.9.5
        self._initial_delimiter = self._delimiter
        layout = QVBoxLayout(self)

        self.head = QLabel()
        self.head.setWordWrap(True)
        layout.addWidget(self.head)

        # Zähler + Trennzeichen live (ohne Settings-Schreiben) — 1.9.5
        opts = QHBoxLayout()
        self.count_label = QLabel()
        self.count_label.setObjectName("csvPreviewCounts")
        self.count_label.setStyleSheet("font-weight:600;")
        opts.addWidget(self.count_label)
        opts.addStretch(1)
        opts.addWidget(QLabel("Trennzeichen:"))
        self.delim_combo = QComboBox()
        self.delim_combo.setObjectName("csvPreviewDelim")
        pick = 0
        for i, d in enumerate(OCR_TABLE_CSV_DELIMITERS):
            self.delim_combo.addItem(OCR_TABLE_CSV_DELIMITER_LABELS.get(d, d), d)
            if d == self._delimiter:
                pick = i
        self.delim_combo.setCurrentIndex(pick)
        self.delim_combo.setToolTip(
            "Trennzeichen live in der Vorschau umschalten; "
            "Persistenz erst beim Speichern · Abbruch setzt Combobox synchron zurück — 1.9.5"
        )
        self.delim_combo.currentIndexChanged.connect(self._on_delim_changed)
        opts.addWidget(self.delim_combo)
        layout.addLayout(opts)

        if target_hint:
            hint = QLabel(f"Ziel: {target_hint}")
            hint.setStyleSheet("color:#555;")
            hint.setWordWrap(True)
            layout.addWidget(hint)

        self.table = QTableWidget(0, 1)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        self.raw_preview = QLabel()
        self.raw_preview.setObjectName("csvPreviewRaw")
        self.raw_preview.setWordWrap(True)
        self.raw_preview.setStyleSheet(
            "color:#444;font-family:monospace;background:#f7f7f7;padding:6px;"
        )
        self.raw_preview.setToolTip(
            "Roh-CSV der Vorschauzeilen (folgt dem Trennzeichen, ohne Persistenz) — 1.9.5"
        )
        layout.addWidget(self.raw_preview)

        # A11y-Feedback bei Speichern — 1.9.5
        self.save_a11y = QLabel("")
        self.save_a11y.setObjectName("csvPreviewSaveA11y")
        self.save_a11y.setWordWrap(True)
        self.save_a11y.setStyleSheet("color:#1b5e20;font-weight:600;")
        self.save_a11y.setAccessibleName("")
        layout.addWidget(self.save_a11y)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        self._save_btn = buttons.button(QDialogButtonBox.Save)
        self._save_btn.setText("Speichern")
        self._save_btn.setToolTip(
            "Trennzeichen persistieren und speichern (Screenreader-Announcement) — 1.9.5"
        )
        buttons.button(QDialogButtonBox.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self._cancel_reset)
        layout.addWidget(buttons)

        self._rebuild()

    def _on_delim_changed(self, _idx: int = 0) -> None:
        """Nur Vorschau — keine Settings-Persistenz — 1.9.5."""
        data = self.delim_combo.currentData()
        self._delimiter = str(data if data is not None else ";")
        if self._delimiter not in OCR_TABLE_CSV_DELIMITERS:
            self._delimiter = ";"
        self._rebuild()

    def _sync_delim_combo(self) -> None:
        """Combobox-Index exakt auf ``_delimiter`` setzen — 1.9.5."""
        pick = 0
        for i in range(self.delim_combo.count()):
            if self.delim_combo.itemData(i) == self._delimiter:
                pick = i
                break
        self.delim_combo.blockSignals(True)
        self.delim_combo.setCurrentIndex(pick)
        self.delim_combo.blockSignals(False)

    def _rebuild(self) -> None:
        from instantlensdoc.core.ocr import format_rows_as_csv

        total_rows = len(self._all_rows)
        preview_rows = self._all_rows[: self._max_rows]
        shown = len(preview_rows)
        cols = max((len(r) for r in self._all_rows), default=0)
        preview_cols = max((len(r) for r in preview_rows), default=0) or max(cols, 1)
        delim_label = OCR_TABLE_CSV_DELIMITER_LABELS.get(
            self._delimiter,
            "Tab" if self._delimiter == "\t" else repr(self._delimiter)[1:-1],
        )
        self.head.setText(
            f"Vorschau der ersten {shown} von {total_rows} Zeile(n) "
            f"(Trennzeichen: {delim_label}). Speichern persistiert · Abbruch setzt "
            f"Combobox synchron zurück — 1.9.5"
        )
        self.count_label.setText(
            f"Zeilen: {total_rows} · Spalten: {cols} · Vorschau: {shown}×{preview_cols}"
        )

        self.table.clear()
        if not preview_rows:
            self.table.setRowCount(1)
            self.table.setColumnCount(1)
            self.table.setHorizontalHeaderLabels(["Spalte 1"])
            self.table.setItem(0, 0, QTableWidgetItem("(keine Zeilen erkannt)"))
            self.raw_preview.setText("(leer)")
            return
        self.table.setRowCount(shown)
        self.table.setColumnCount(preview_cols)
        self.table.setHorizontalHeaderLabels([f"Spalte {i + 1}" for i in range(preview_cols)])
        for r_i, row in enumerate(preview_rows):
            for c_i in range(preview_cols):
                val = row[c_i] if c_i < len(row) else ""
                self.table.setItem(r_i, c_i, QTableWidgetItem(str(val)))
        raw = format_rows_as_csv(preview_rows, delimiter=self._delimiter, utf8_bom=False)
        # kurze Rohvorschau (max. 5 Zeilen bereits begrenzt)
        self.raw_preview.setText(raw.rstrip("\n") if raw else "(leer)")

    def _reset_preview_to_initial(self) -> None:
        """Vorschau-Trennzeichen + Combobox synchron zurück — 1.9.5."""
        self._delimiter = self._initial_delimiter
        if self._delimiter not in OCR_TABLE_CSV_DELIMITERS:
            self._delimiter = ";"
            self._initial_delimiter = ";"
        self._sync_delim_combo()
        self._rebuild()

    def _cancel_reset(self) -> None:
        """Abbruch: Vorschau + Combobox zurücksetzen, keine Persistenz — 1.9.5."""
        self._accepted_save = False
        self._reset_preview_to_initial()
        self.reject()

    def reject(self) -> None:
        """Esc/Schließen: Combobox synchron zurück ohne Persistenz — 1.9.5."""
        if not self._accepted_save:
            # Immer Combobox synchronisieren (auch wenn Wert schon initial) — 1.9.5
            self._reset_preview_to_initial()
        super().reject()

    def _announce_save_a11y(self, msg: str) -> None:
        """Screenreader-Announcement beim Speichern — 1.9.5."""
        self.save_a11y.setText(msg)
        self.save_a11y.setAccessibleName(msg)
        self.save_a11y.setAccessibleDescription(msg)
        if hasattr(self, "_save_btn") and self._save_btn is not None:
            self._save_btn.setAccessibleName(msg)
        try:
            from PySide6.QtGui import QAccessible, QAccessibleAnnouncementEvent

            ev = QAccessibleAnnouncementEvent(self.save_a11y, msg)
            QAccessible.updateAccessibility(ev)
        except Exception:
            try:
                from PySide6.QtGui import QAccessible, QAccessibleEvent

                ev = QAccessibleEvent(self.save_a11y, QAccessible.Event.NameChanged)
                QAccessible.updateAccessibility(ev)
            except Exception:
                pass

    def _save(self) -> None:
        """Erst hier Persistenz des Trennzeichens + A11y — 1.9.5."""
        self._accepted_save = True
        try:
            set_ocr_table_csv_delimiter(self._delimiter)
        except Exception:
            pass
        delim_label = OCR_TABLE_CSV_DELIMITER_LABELS.get(
            self._delimiter,
            "Tab" if self._delimiter == "\t" else repr(self._delimiter)[1:-1],
        )
        self._announce_save_a11y(f"Trennzeichen gespeichert: {delim_label}")
        self.accept()

    @property
    def save_confirmed(self) -> bool:
        return bool(self._accepted_save)

    @property
    def selected_delimiter(self) -> str:
        """Aktuell gewähltes Trennzeichen (live umschaltbar) — 1.9.5."""
        return self._delimiter

    @property
    def initial_delimiter(self) -> str:
        """Ausgangswert beim Dialog-Start (für Abbruch-Reset) — 1.9.5."""
        return self._initial_delimiter

    @property
    def row_count(self) -> int:
        return len(self._all_rows)

    @property
    def column_count(self) -> int:
        return max((len(r) for r in self._all_rows), default=0)

