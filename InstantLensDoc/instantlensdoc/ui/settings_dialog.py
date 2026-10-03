"""Einstellungen: Theme, OCR, Sprache, Export, Zoom, Autosave, Pfade."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)


class AnnExportTemplateEdit(QLineEdit):
    """Ann.-Export-Template: Cursor-Position merken + lokales Undo — 1.2.5/1.2.6."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_cursor = 0
        self._saved_sel_start = -1
        self._saved_sel_len = 0
        # QLineEdit: Undo/Redo lokal (Ctrl+Z/Y via keyPressEvent) — 1.2.6

    def focusOutEvent(self, event):
        self._saved_cursor = self.cursorPosition()
        self._saved_sel_start = self.selectionStart()
        self._saved_sel_len = self.selectionLength()
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        """Ctrl+Z / Ctrl+Y nur lokal im Feld (kein App-Undo) — 1.2.6."""
        from PySide6.QtGui import QKeySequence

        if event.matches(QKeySequence.Undo):
            if self.isUndoAvailable():
                self.undo()
            event.accept()
            return
        if event.matches(QKeySequence.Redo):
            if self.isRedoAvailable():
                self.redo()
            event.accept()
            return
        super().keyPressEvent(event)

    def restore_insert_position(self) -> None:
        """Cursor/Selektion vor Quick-Insert wiederherstellen — 1.2.5."""
        if self.hasFocus():
            return
        if self._saved_sel_start >= 0 and self._saved_sel_len > 0:
            self.setSelection(self._saved_sel_start, self._saved_sel_len)
        else:
            pos = max(0, min(self._saved_cursor, len(self.text())))
            self.setCursorPosition(pos)

from ild_pdf.pages import PAGE_SIZE_PRESETS
from instantlensdoc.core.app_settings import (
    ANN_COLOR_PRESET_COUNT,
    ANN_COLORS_SCHEMA_ID,
    AUTOSAVE_INTERVAL_CHOICES,
    AnnColorsImportError,
    export_ann_color_presets_json,
    factory_ann_color_presets,
    get_ann_color_presets,
    get_autosave_backup_enabled,
    get_autosave_backup_max,
    get_autosave_enabled,
    get_autosave_interval_sec,
    import_ann_color_presets_json,
    AUTOSAVE_BACKUP_MAX_MAX,
    AUTOSAVE_BACKUP_MAX_MIN,
    get_backup_on_save,
    get_batch_output_dir,
    get_default_open_dir,
    DEFAULT_ZOOM_MODE_FIT_PAGE,
    DEFAULT_ZOOM_MODE_FIT_WIDTH,
    DEFAULT_ZOOM_MODE_PERCENT,
    get_default_zoom_mode,
    get_default_zoom_percent,
    PDF_TOOLBAR_GROUP_LABELS,
    get_editor_doc_split_vertical,
    get_editor_text_encoding,
    get_editor_bracket_auto_close,
    get_editor_bracket_match,
    get_editor_trim_trailing_whitespace,
    get_editor_trim_whitespace_on_paste,
    get_skip_splash,
    get_spellcheck_dict_path,
    get_export_image_max_edge,
    get_pdf_toolbar_groups,
    get_export_jpeg_quality,
    get_export_pdf_page,
    get_minimize_to_tray,
    get_ocr_attach_errors,
    get_ocr_defaults_toast_sec,
    get_ocr_dpi,
    get_ocr_lang,
    get_merge_close_preview_on_edit,
    MERGE_CLOSE_PREVIEW_TOOLTIP,
    OCR_DEFAULTS_TOAST_CHOICES,
    get_page_size_unit,
    get_pdf_continuous_scroll,
    get_pdf_grayscale,
    get_pdf_night_mode,
    get_print_grayscale,
    get_print_preview,
    get_pdf_thumbnail_scale,
    get_redaction_preview_opacity,
    get_thumb_lazy_threshold,
    get_thumb_prefetch_cancel_ms,
    get_thumb_prefetch_radius,
    get_pdf_two_page_spread,
    get_editor_current_line_highlight,
    get_editor_indent_guides,
    get_editor_soft_tabs,
    get_editor_tab_width,
    get_page_number_overlay_font_size,
    get_page_number_overlay_format,
    get_page_number_overlay_opacity,
    get_page_number_overlay_position,
    get_page_number_overlay_skip_edges,
    get_page_number_overlay_start,
    get_show_page_number_overlay,
    get_restore_session_on_start,
    get_restore_window_geometry_on_start,
    get_merge_diff_max_side,
    get_recent_files_max,
    get_search_snippet_context_chars,
    get_search_snippet_ellipsis_style,
    get_sidecar_save_debounce_ms,
    get_status_blink_mode,
    get_tag_rename_confirm_threshold,
    get_theme,
    get_ui_lang,
    get_update_check_on_start,
    get_wizard_completed,
    MERGE_DIFF_MAX_SIDE_MAX,
    MERGE_DIFF_MAX_SIDE_MIN,
    RECENT_FILES_MAX_MAX,
    RECENT_FILES_MAX_MIN,
    SEARCH_SNIPPET_CONTEXT_MAX,
    SEARCH_SNIPPET_CONTEXT_MIN,
    SEARCH_SNIPPET_ELLIPSIS_CHOICES,
    SIDECAR_SAVE_DEBOUNCE_MAX_MS,
    SIDECAR_SAVE_DEBOUNCE_MIN_MS,
    STATUS_BLINK_CHOICES,
    PDF_THUMBNAIL_SCALE_CHOICES,
    THUMB_LAZY_THRESHOLD_CHOICES,
    THUMB_PREFETCH_CANCEL_MS_CHOICES,
    THUMB_PREFETCH_RADIUS_CHOICES,
    reset_ann_color_presets,
    reset_to_defaults,
    save_settings,
    set_ann_color_presets,
    set_recent_files_max,
    set_wizard_completed,
    set_wizard_skip_once,
    set_autosave_backup_enabled,
    set_autosave_backup_max,
    set_autosave_enabled,
    set_autosave_interval_sec,
    set_backup_on_save,
    set_batch_output_dir,
    set_default_open_dir,
    set_default_zoom_mode,
    set_default_zoom_percent,
    set_editor_bracket_auto_close,
    set_editor_bracket_match,
    set_editor_doc_split_vertical,
    set_editor_line_numbers,
    set_editor_minimap,
    set_editor_current_line_highlight,
    set_editor_indent_guides,
    set_editor_show_special_chars,
    set_editor_soft_tabs,
    set_editor_soft_wrap,
    set_editor_tab_width,
    set_editor_text_encoding,
    set_editor_trim_trailing_whitespace,
    set_editor_trim_whitespace_on_paste,
    set_skip_splash,
    set_spellcheck_dict_path,
    set_minimize_to_tray,
    set_pdf_toolbar_groups,
    set_ocr_attach_errors,
    set_ocr_defaults_toast_sec,
    set_ocr_dpi,
    set_ocr_lang,
    set_merge_close_preview_on_edit,
    set_page_size_unit,
    set_pdf_continuous_scroll,
    set_pdf_grayscale,
    set_pdf_night_mode,
    set_print_grayscale,
    set_print_preview,
    set_pdf_thumbnail_scale,
    set_redaction_preview_opacity,
    set_thumb_lazy_threshold,
    set_thumb_prefetch_cancel_ms,
    set_thumb_prefetch_radius,
    set_pdf_two_page_spread,
    set_page_number_overlay_font_size,
    set_page_number_overlay_format,
    set_page_number_overlay_opacity,
    set_page_number_overlay_position,
    set_page_number_overlay_skip_edges,
    set_page_number_overlay_start,
    set_show_page_number_overlay,
    set_restore_session_on_start,
    set_restore_window_geometry_on_start,
    set_merge_diff_max_side,
    set_search_snippet_context_chars,
    set_search_snippet_ellipsis_style,
    set_sidecar_save_debounce_ms,
    set_status_blink_mode,
    set_tag_rename_confirm_threshold,
    set_theme,
    set_ui_lang,
    set_update_check_on_start,
)
from instantlensdoc.core.i18n import sync_from_settings, tr
from instantlensdoc.core.ocr import LANG_PRESETS, OCR_DPI_CHOICES
from instantlensdoc.ui.theme import apply_theme


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        sync_from_settings()
        self.setWindowTitle(tr("settings"))
        self.resize(560, 520)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr("settings_title")))

        form = QFormLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(tr("theme_light"), "light")
        self.theme_combo.addItem(tr("theme_dark"), "dark")
        cur_theme = get_theme()
        self.theme_combo.setCurrentIndex(1 if cur_theme == "dark" else 0)
        form.addRow(tr("theme"), self.theme_combo)

        self.ui_lang = QComboBox()
        self.ui_lang.addItem(tr("lang_de"), "de")
        self.ui_lang.addItem(tr("lang_en"), "en")
        self.ui_lang.setCurrentIndex(1 if get_ui_lang() == "en" else 0)
        form.addRow(tr("ui_lang"), self.ui_lang)

        self.lang_combo = QComboBox()
        cur_lang = get_ocr_lang()
        pick = 0
        for i, (name, code) in enumerate(LANG_PRESETS.items()):
            self.lang_combo.addItem(name, code)
            if code == cur_lang:
                pick = i
        self.lang_combo.setCurrentIndex(pick)
        self.lang_combo.setToolTip(
            "OCR-Sprach-Preset als Dialog-Default speichern — 1.1.6"
        )
        form.addRow(tr("ocr_lang"), self.lang_combo)

        self.ocr_dpi_combo = QComboBox()
        cur_dpi = get_ocr_dpi()
        dpi_pick = 0
        for i, d in enumerate(OCR_DPI_CHOICES):
            self.ocr_dpi_combo.addItem(f"{d} DPI", int(d))
            if int(d) == int(cur_dpi):
                dpi_pick = i
        self.ocr_dpi_combo.setCurrentIndex(dpi_pick)
        self.ocr_dpi_combo.setToolTip(
            "OCR-DPI (150/300) als Dialog-Default speichern — 1.1.6"
        )
        form.addRow("OCR-DPI (Standard)", self.ocr_dpi_combo)

        self.ocr_attach_errors = QCheckBox("OCR: Fehler anhängen")
        self.ocr_attach_errors.setChecked(get_ocr_attach_errors())
        self.ocr_attach_errors.setToolTip(
            "Beim Batch-OCR Seitenfehler als Abschnitt „OCR-Fehler“ anhängen "
            "(auch im OCR-Dialog) — 1.1.5"
        )
        form.addRow(self.ocr_attach_errors)

        self.ocr_toast_sec = QComboBox()
        cur_toast = get_ocr_defaults_toast_sec()
        toast_pick = 0
        for i, sec in enumerate(OCR_DEFAULTS_TOAST_CHOICES):
            self.ocr_toast_sec.addItem(f"{sec} s", int(sec))
            if int(sec) == int(cur_toast):
                toast_pick = i
        self.ocr_toast_sec.setCurrentIndex(toast_pick)
        self.ocr_toast_sec.setToolTip(
            "Dauer des Toasts „OCR-Defaults gespeichert“ (1/2/3 s) "
            "inkl. Accessibility-Announcement — 1.1.9"
        )
        form.addRow("OCR-Defaults-Toast", self.ocr_toast_sec)

        self.merge_close_preview = QCheckBox(
            "Zusammenführen: Readonly-Vorschau bei „Zum Bearbeiten öffnen“ schließen"
        )
        self.merge_close_preview.setChecked(get_merge_close_preview_on_edit())
        self.merge_close_preview.setToolTip(MERGE_CLOSE_PREVIEW_TOOLTIP)
        form.addRow(self.merge_close_preview)

        self.zoom_mode = QComboBox()
        self.zoom_mode.addItem("Prozent", DEFAULT_ZOOM_MODE_PERCENT)
        self.zoom_mode.addItem("Seitenbreite (Fit-Width)", DEFAULT_ZOOM_MODE_FIT_WIDTH)
        self.zoom_mode.addItem("Seite einpassen (Fit-Page)", DEFAULT_ZOOM_MODE_FIT_PAGE)
        cur_zoom_mode = get_default_zoom_mode()
        zoom_mode_pick = 0
        for i in range(self.zoom_mode.count()):
            if self.zoom_mode.itemData(i) == cur_zoom_mode:
                zoom_mode_pick = i
                break
        self.zoom_mode.setCurrentIndex(zoom_mode_pick)
        self.zoom_mode.setToolTip(
            "Beim Öffnen: fester Zoom-% oder Fit-Width / Fit-Page (Shortcuts Ctrl+9 / Ctrl+0)"
        )
        self.zoom_mode.currentIndexChanged.connect(self._sync_zoom_pct_enabled)
        form.addRow(tr("default_zoom_mode"), self.zoom_mode)

        zoom_row = QHBoxLayout()
        self.zoom_pct = QSpinBox()
        self.zoom_pct.setRange(25, 500)
        self.zoom_pct.setSingleStep(10)
        self.zoom_pct.setSuffix(" %")
        self.zoom_pct.setValue(get_default_zoom_percent())
        self.zoom_pct.setToolTip("Standard-Zoom-% beim Öffnen (nur Modus Prozent)")
        zoom_row.addWidget(self.zoom_pct)
        self.btn_zoom_from_pdf = QPushButton("Aktuell speichern")
        self.btn_zoom_from_pdf.setToolTip(
            "Aktuellen PDF-Zoom als Standard-% speichern (Modus → Prozent)"
        )
        self.btn_zoom_from_pdf.clicked.connect(self._capture_current_pdf_zoom)
        zoom_row.addWidget(self.btn_zoom_from_pdf)
        form.addRow(tr("default_zoom"), zoom_row)
        self._sync_zoom_pct_enabled()

        self.thumb_scale = QComboBox()
        cur_thumb = get_pdf_thumbnail_scale()
        thumb_pick = 0
        labels = {0.12: "Klein (0.12)", 0.18: "Normal (0.18)", 0.24: "Groß (0.24)"}
        for i, s in enumerate(PDF_THUMBNAIL_SCALE_CHOICES):
            self.thumb_scale.addItem(labels.get(s, f"{s}"), s)
            if abs(s - cur_thumb) < 1e-9:
                thumb_pick = i
        self.thumb_scale.setCurrentIndex(thumb_pick)
        self.thumb_scale.setToolTip("Größe der PDF-Seitenvorschau in der Sidebar")
        form.addRow("PDF-Thumbnail-Größe", self.thumb_scale)

        self.thumb_lazy = QComboBox()
        cur_lazy = get_thumb_lazy_threshold()
        lazy_pick = 0
        for i, n in enumerate(THUMB_LAZY_THRESHOLD_CHOICES):
            self.thumb_lazy.addItem(f">{n} Seiten", n)
            if n == cur_lazy:
                lazy_pick = i
        self.thumb_lazy.setCurrentIndex(lazy_pick)
        self.thumb_lazy.setToolTip(
            "Ab dieser Seitenanzahl Lazy-Load mit Platzhaltern (25 / 50 / 100) — 1.3.1"
        )
        form.addRow("Thumbnail-Lazy ab", self.thumb_lazy)

        self.thumb_prefetch = QComboBox()
        cur_pref = get_thumb_prefetch_radius()
        pref_pick = 0
        for i, n in enumerate(THUMB_PREFETCH_RADIUS_CHOICES):
            self.thumb_prefetch.addItem(f"±{n}", n)
            if n == cur_pref:
                pref_pick = i
        self.thumb_prefetch.setCurrentIndex(pref_pick)
        self.thumb_prefetch.setToolTip(
            "Thumbnail Prefetch um Viewport (±1 / ±2 / ±3) — 1.3.3"
        )
        form.addRow("Thumbnail-Prefetch", self.thumb_prefetch)

        self.thumb_cancel_ms = QComboBox()
        cur_cancel = get_thumb_prefetch_cancel_ms()
        cancel_pick = 0
        for i, ms in enumerate(THUMB_PREFETCH_CANCEL_MS_CHOICES):
            self.thumb_cancel_ms.addItem(f"{ms} ms", ms)
            if ms == cur_cancel:
                cancel_pick = i
        self.thumb_cancel_ms.setCurrentIndex(cancel_pick)
        self.thumb_cancel_ms.setToolTip(
            "Cancel-Debounce bei schnellem Thumbnail-Scroll (ms) — 1.3.3"
        )
        form.addRow("Prefetch-Cancel-Debounce", self.thumb_cancel_ms)

        # Live-Label „aktuell N ms / ±N“ — 1.3.4
        self.lbl_prefetch_live = QLabel()
        self.lbl_prefetch_live.setStyleSheet("color: #555; font-style: italic;")
        self.lbl_prefetch_live.setToolTip(
            "Live-Anzeige der gewählten Prefetch-Cancel-Debounce / Radius — 1.3.4"
        )
        self.thumb_prefetch.currentIndexChanged.connect(
            self._update_prefetch_live_label
        )
        self.thumb_cancel_ms.currentIndexChanged.connect(
            self._update_prefetch_live_label
        )
        self._update_prefetch_live_label()
        form.addRow("Prefetch aktuell", self.lbl_prefetch_live)

        self.redact_opacity = QDoubleSpinBox()
        self.redact_opacity.setRange(0.05, 1.0)
        self.redact_opacity.setSingleStep(0.05)
        self.redact_opacity.setDecimals(2)
        self.redact_opacity.setValue(get_redaction_preview_opacity())
        self.redact_opacity.setToolTip(
            "Deckkraft der Schwärzungs-Vorschau (vor Einbrennen) — 1.3.1"
        )
        form.addRow("Schwärzung Preview-Deckkraft", self.redact_opacity)

        self.autosave_enabled = QCheckBox("Autosave aktiv")
        self.autosave_enabled.setChecked(get_autosave_enabled())
        self.autosave_enabled.setToolTip(
            "Automatisches Speichern von Editor und Annotationen (Intervall unten) — 0.9.6"
        )
        form.addRow(self.autosave_enabled)

        self.autosave_sec = QComboBox()
        cur_as = get_autosave_interval_sec()
        as_pick = 0
        for i, sec in enumerate(AUTOSAVE_INTERVAL_CHOICES):
            self.autosave_sec.addItem(f"{sec} s", sec)
            if sec == cur_as:
                as_pick = i
        self.autosave_sec.setCurrentIndex(as_pick)
        self.autosave_sec.setToolTip(
            "Autosave-Intervall: 15 / 30 / 60 / 120 Sekunden — 0.9.7"
        )
        self.autosave_sec.setEnabled(self.autosave_enabled.isChecked())
        self.autosave_enabled.toggled.connect(self.autosave_sec.setEnabled)
        form.addRow(tr("autosave_interval"), self.autosave_sec)

        self.autosave_backup = QCheckBox("Autosave-Backup (.ildbak) vor Überschreiben")
        self.autosave_backup.setChecked(get_autosave_backup_enabled())
        self.autosave_backup.setToolTip(
            "Vor Autosave eine rotierende Backup-Kopie dateiname.ext.ildbak anlegen — 0.9.9"
        )
        form.addRow(self.autosave_backup)

        self.autosave_backup_max = QSpinBox()
        self.autosave_backup_max.setRange(AUTOSAVE_BACKUP_MAX_MIN, AUTOSAVE_BACKUP_MAX_MAX)
        self.autosave_backup_max.setValue(get_autosave_backup_max())
        self.autosave_backup_max.setToolTip(
            "Max. Anzahl .ildbak-Backups (1–10, Rotation) — 0.9.9"
        )
        self.autosave_backup_max.setEnabled(self.autosave_backup.isChecked())
        self.autosave_backup.toggled.connect(self.autosave_backup_max.setEnabled)
        form.addRow("Autosave-Backups max.", self.autosave_backup_max)

        # Color-Presets (User) — speichern/zurücksetzen auch per Rechtsklick in PDF-Toolbar
        preset_row = QHBoxLayout()
        self._preset_edits: list[QLineEdit] = []
        self._preset_undo: list[str] | None = None
        presets = get_ann_color_presets()
        for i in range(ANN_COLOR_PRESET_COUNT):
            ed = QLineEdit(presets[i] if i < len(presets) else "#888888")
            ed.setMaxLength(7)
            ed.setFixedWidth(72)
            ed.setToolTip(f"Color-Preset {i + 1} (#RRGGBB) — User-Preset in Settings 0.9.6")
            self._preset_edits.append(ed)
            preset_row.addWidget(ed)
        btn_reset_presets = QPushButton("Alle zurücksetzen…")
        btn_reset_presets.setToolTip(
            "Alle 6 Color-Presets auf Werksstandard zurücksetzen (mit Bestätigung) — 0.9.8"
        )
        btn_reset_presets.clicked.connect(self._reset_color_presets_ui)
        preset_row.addWidget(btn_reset_presets)
        btn_factory_presets = QPushButton("Werksstandard")
        btn_factory_presets.setToolTip(
            "Factory-Defaults in die Felder laden (Bestätigung; Undo möglich) — 0.9.9"
        )
        btn_factory_presets.clicked.connect(self._load_factory_color_presets_ui)
        preset_row.addWidget(btn_factory_presets)
        self.btn_undo_factory_presets = QPushButton("Rückgängig")
        self.btn_undo_factory_presets.setToolTip(
            "Letzte Factory-Preset-Änderung in den Feldern rückgängig — 0.9.9"
        )
        self.btn_undo_factory_presets.setEnabled(False)
        self.btn_undo_factory_presets.clicked.connect(self._undo_factory_color_presets_ui)
        preset_row.addWidget(self.btn_undo_factory_presets)
        btn_export_presets = QPushButton("Export…")
        btn_export_presets.setToolTip(
            f"Color-Presets als JSON exportieren ({ANN_COLORS_SCHEMA_ID}) — 0.9.7"
        )
        btn_export_presets.clicked.connect(self._export_color_presets_ui)
        preset_row.addWidget(btn_export_presets)
        btn_import_presets = QPushButton("Import…")
        btn_import_presets.setToolTip(
            f"Color-Presets aus JSON importieren ({ANN_COLORS_SCHEMA_ID}) — 0.9.7"
        )
        btn_import_presets.clicked.connect(self._import_color_presets_ui)
        preset_row.addWidget(btn_import_presets)
        form.addRow("Ann.-Color-Presets", preset_row)

        self.line_numbers = QCheckBox("Zeilennummern im Editor")
        from instantlensdoc.core.app_settings import (
            get_editor_line_numbers,
            get_editor_minimap,
            get_editor_soft_wrap,
        )

        self.line_numbers.setChecked(get_editor_line_numbers())
        self.line_numbers.setToolTip("Optionale Zeilennummern im Texteditor")
        form.addRow(self.line_numbers)

        self.minimap = QCheckBox("Editor-Minimap (Linien-Übersicht)")
        self.minimap.setChecked(get_editor_minimap())
        self.minimap.setToolTip(
            "Einfache Minimap rechts + dickere Scrollbar (optional)"
        )
        form.addRow(self.minimap)

        self.soft_wrap = QCheckBox("Wortumbruch (Soft-Wrap) im Editor")
        self.soft_wrap.setChecked(get_editor_soft_wrap())
        self.soft_wrap.setToolTip(
            "Lange Zeilen am Fensterrand umbrechen — Ansicht-Toggle persistiert (Ctrl+Shift+W)"
        )
        form.addRow(self.soft_wrap)

        self.tab_width = QComboBox()
        self.tab_width.addItem("2 Zeichen", 2)
        self.tab_width.addItem("4 Zeichen", 4)
        self.tab_width.addItem("8 Zeichen", 8)
        cur_tab = get_editor_tab_width()
        tab_idx = {2: 0, 4: 1, 8: 2}.get(cur_tab, 1)
        self.tab_width.setCurrentIndex(tab_idx)
        self.tab_width.setToolTip("Tabulatorbreite im Texteditor (2 / 4 / 8 Zeichen)")
        form.addRow("Editor Tab-Breite", self.tab_width)

        self.soft_tabs = QCheckBox("Soft-Tabs (Tab als Leerzeichen)")
        self.soft_tabs.setChecked(get_editor_soft_tabs())
        self.soft_tabs.setToolTip(
            "An: Tab/Einrücken mit Leerzeichen (Tab-Breite); Aus: echte Tabulatorzeichen"
        )
        form.addRow(self.soft_tabs)

        self.indent_guides = QCheckBox("Einrückungs-Guides (vertikale Linien)")
        self.indent_guides.setChecked(get_editor_indent_guides())
        self.indent_guides.setToolTip(
            "Vertikale Linien an Tab-Stops für führende Einrückung im Editor"
        )
        form.addRow(self.indent_guides)

        self.current_line_hl = QCheckBox("Aktuelle Zeile hervorheben")
        self.current_line_hl.setChecked(get_editor_current_line_highlight())
        self.current_line_hl.setToolTip(
            "Die Zeile mit dem Cursor im Editor farblich markieren (Ansicht ↔ Settings)"
        )
        form.addRow(self.current_line_hl)

        from instantlensdoc.core.app_settings import get_editor_show_special_chars

        self.special_chars = QCheckBox("Sonderzeichen anzeigen (Tabs/Leerzeichen)")
        self.special_chars.setChecked(get_editor_show_special_chars())
        self.special_chars.setToolTip("Tabs, Leerzeichen und Absatzenden im Editor sichtbar")
        form.addRow(self.special_chars)

        self.enc_combo = QComboBox()
        self.enc_combo.addItem("Automatisch (BOM / chardet)", "auto")
        self.enc_combo.addItem("UTF-8", "utf-8")
        self.enc_combo.addItem("Latin-1 (ISO-8859-1)", "latin-1")
        cur_enc = get_editor_text_encoding()
        enc_idx = {"auto": 0, "utf-8": 1, "latin-1": 2}.get(cur_enc, 0)
        self.enc_combo.setCurrentIndex(enc_idx)
        self.enc_combo.setToolTip(
            "Encoding beim Öffnen: Automatisch erkennt BOM und optional chardet; "
            "sonst UTF-8 oder Latin-1"
        )
        form.addRow("Editor-Encoding", self.enc_combo)

        self.skip_splash = QCheckBox("Splash beim Start überspringen (Quiet Startup)")
        self.skip_splash.setChecked(get_skip_splash())
        self.skip_splash.setToolTip(
            "Kein Splash-Screen beim App-Start — schneller/ruhiger Start"
        )
        form.addRow(self.skip_splash)

        self.spell_dict = QLineEdit()
        self.spell_dict.setText(get_spellcheck_dict_path())
        self.spell_dict.setPlaceholderText("Pfad zur Wortliste (.txt, eine Zeile = ein Wort)")
        self.spell_dict.setToolTip(
            "Lokales Rechtschreibwörterbuch ohne externe Lib — "
            "UTF-8-Wortliste; Bearbeiten → Rechtschreibung prüfen (F7)"
        )
        spell_row = QHBoxLayout()
        spell_row.addWidget(self.spell_dict)
        btn_spell = QPushButton("…")
        btn_spell.setToolTip("Wortliste auswählen")
        btn_spell.clicked.connect(self._pick_spell_dict)
        spell_row.addWidget(btn_spell)
        form.addRow("Rechtschreibwörterbuch", spell_row)

        self.trim_trailing = QCheckBox("Trailing Whitespace beim Speichern entfernen")
        self.trim_trailing.setChecked(get_editor_trim_trailing_whitespace())
        self.trim_trailing.setToolTip(
            "Leerzeichen und Tabs am Zeilenende vor Speichern/Autosave entfernen (optional)"
        )
        form.addRow(self.trim_trailing)

        self.trim_paste = QCheckBox("Whitespace trim on paste")
        self.trim_paste.setChecked(get_editor_trim_whitespace_on_paste())
        self.trim_paste.setToolTip(
            "Beim Einfügen aus der Zwischenablage Trailing Whitespace pro Zeile entfernen (optional)"
        )
        form.addRow(self.trim_paste)

        self.bracket_match = QCheckBox("Bracket-Match Highlight")
        self.bracket_match.setChecked(get_editor_bracket_match())
        self.bracket_match.setToolTip(
            "Passende Klammern ()[]{} im Editor hervorheben (Cursor-Position)"
        )
        form.addRow(self.bracket_match)

        self.bracket_auto_close = QCheckBox("Bracket-Auto-Close")
        self.bracket_auto_close.setChecked(get_editor_bracket_auto_close())
        self.bracket_auto_close.setToolTip(
            "Beim Tippen schließende Klammern ()[]{} und Anführungszeichen automatisch einfügen"
        )
        form.addRow(self.bracket_auto_close)

        self.minimize_tray = QCheckBox("Beim Minimieren in den System-Tray")
        self.minimize_tray.setChecked(get_minimize_to_tray())
        self.minimize_tray.setToolTip(
            "Fenster in den Infobereich legen statt Taskleisten-Minimierung (optional)"
        )
        form.addRow(self.minimize_tray)

        self.backup_on_save = QCheckBox("Backup-Kopie (.bak) beim Speichern")
        self.backup_on_save.setChecked(get_backup_on_save())
        self.backup_on_save.setToolTip(
            "Vor dem Überschreiben eine Kopie dateiname.ext.bak anlegen (optional)"
        )
        form.addRow(self.backup_on_save)

        # Letzte 20: Filter Erfolg/Fehler + Export TXT + Doppelklick — 1.0.7
        from PySide6.QtCore import Qt as _Qt

        from instantlensdoc.core.manual_backup import (
            BACKUP_LOG_MAX,
            load_backup_log,
        )

        self.backup_log_list = QListWidget()
        self.backup_log_list.setMinimumHeight(120)
        self.backup_log_list.setMaximumHeight(180)
        self.backup_log_list.setToolTip(
            f"Letzte {BACKUP_LOG_MAX} manuellen Backup-Vorgänge; "
            "Sortierung neueste zuerst (Toggle); Filter Erfolg/Fehler; Export als TXT; "
            "Doppelklick öffnet Backup-Datei bzw. Ordner — 1.0.9"
        )
        self.backup_log_list.setAlternatingRowColors(True)
        self.backup_log_list.itemDoubleClicked.connect(self._open_backup_log_entry)
        self._backup_log_entries: list = list(load_backup_log())
        self._backup_log_filter_mode = "all"
        self._backup_log_newest_first = True
        bak_log_col = QVBoxLayout()
        bak_log_col.setContentsMargins(0, 0, 0, 0)
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filter:"))
        self.backup_log_filter = QComboBox()
        self.backup_log_filter.addItem("Alle", "all")
        self.backup_log_filter.addItem("Nur Erfolg", "ok")
        self.backup_log_filter.addItem("Nur Fehler", "error")
        self.backup_log_filter.setToolTip(
            "Backup-Log nach Erfolg oder Fehler filtern — 1.0.7"
        )
        self.backup_log_filter.currentIndexChanged.connect(self._on_backup_log_filter)
        filter_row.addWidget(self.backup_log_filter, 1)
        self.backup_log_newest_first = QCheckBox("Neueste zuerst")
        self.backup_log_newest_first.setChecked(True)
        self.backup_log_newest_first.setToolTip(
            "Sortierung: neueste zuerst (an) oder älteste zuerst (aus) — 1.0.9"
        )
        self.backup_log_newest_first.toggled.connect(self._on_backup_log_sort)
        filter_row.addWidget(self.backup_log_newest_first)
        bak_log_col.addLayout(filter_row)
        self.backup_log_empty_hint = QLabel(
            "Noch keine Backup-Vorgänge protokolliert."
        )
        self.backup_log_empty_hint.setWordWrap(True)
        self.backup_log_empty_hint.setStyleSheet("color: #666; font-style: italic;")
        self.backup_log_empty_hint.setToolTip(
            "Hinweis wenn das Backup-Log leer ist — 1.0.9"
        )
        bak_log_col.addWidget(self.backup_log_empty_hint)
        bak_log_col.addWidget(self.backup_log_list)
        bak_log_btns = QHBoxLayout()
        self.btn_backup_log_copy = QPushButton("Eintrag kopieren")
        self.btn_backup_log_copy.setToolTip(
            "Ausgewählten Backup-Log-Eintrag in die Zwischenablage kopieren — 1.0.5"
        )
        self.btn_backup_log_copy.clicked.connect(self._copy_backup_log_entry)
        bak_log_btns.addWidget(self.btn_backup_log_copy)
        self.btn_backup_log_export = QPushButton("Log exportieren…")
        self.btn_backup_log_export.setToolTip(
            "Gefiltertes Backup-Log als TXT speichern — 1.0.7"
        )
        self.btn_backup_log_export.clicked.connect(self._export_backup_log)
        bak_log_btns.addWidget(self.btn_backup_log_export)
        self.btn_backup_log_clear = QPushButton("Log leeren")
        self.btn_backup_log_clear.setToolTip(
            "Backup-Log zurücksetzen (alle Einträge löschen) — 1.0.5"
        )
        self.btn_backup_log_clear.clicked.connect(self._clear_backup_log)
        bak_log_btns.addWidget(self.btn_backup_log_clear)
        bak_log_btns.addStretch(1)
        bak_log_col.addLayout(bak_log_btns)
        self._reload_backup_log_list()
        form.addRow(f"Backup-Log (letzte {BACKUP_LOG_MAX})", bak_log_col)

        self.restore_geometry = QCheckBox("Fenstergeometrie wiederherstellen")
        self.restore_geometry.setChecked(get_restore_window_geometry_on_start())
        self.restore_geometry.setToolTip(
            "Größe, Position und Fensterzustand der letzten Sitzung beim Start laden"
        )
        form.addRow(self.restore_geometry)

        self.restore_session = QCheckBox("Offene Tabs wiederherstellen")
        self.restore_session.setChecked(get_restore_session_on_start())
        self.restore_session.setToolTip(
            "Offene Dokument-Tabs der letzten Sitzung beim Start laden (Session)"
        )
        form.addRow(self.restore_session)

        self.page_unit = QComboBox()
        self.page_unit.addItem("mm", "mm")
        self.page_unit.addItem("inch", "inch")
        self.page_unit.setCurrentIndex(1 if get_page_size_unit() == "inch" else 0)
        self.page_unit.setToolTip("Einheit für PDF-Seitengröße in Statusleiste und Dialog")
        form.addRow("Seitengröße Einheit", self.page_unit)

        self.pdf_grayscale = QCheckBox("PDF in Graustufen rendern/exportieren")
        self.pdf_grayscale.setChecked(get_pdf_grayscale())
        self.pdf_grayscale.setToolTip("Seitenansicht und Bild-Export monochrom")
        form.addRow(self.pdf_grayscale)

        self.print_grayscale = QCheckBox("Dokumentdruck in Graustufen")
        self.print_grayscale.setChecked(get_print_grayscale())
        self.print_grayscale.setToolTip(
            "PDF → Dokument drucken… standardmäßig monochrom (auch im Druckdialog) — 1.0.3"
        )
        form.addRow(self.print_grayscale)

        self.print_preview = QCheckBox("Druckvorschau vor Dokumentdruck")
        self.print_preview.setChecked(get_print_preview())
        self.print_preview.setToolTip(
            "Vor dem Druckjob Thumbnail der ersten Seite anzeigen (optional) — 1.0.6"
        )
        form.addRow(self.print_preview)

        self.pdf_night = QCheckBox("PDF Nachtmodus (Invert-Ansicht)")
        self.pdf_night.setChecked(get_pdf_night_mode())
        self.pdf_night.setToolTip("Dunkle Invert-Ansicht — nur Darstellung, nicht speichern/exportieren")
        form.addRow(self.pdf_night)

        self.pdf_spread = QCheckBox("PDF Zwei-Seiten-Ansicht (Spread)")
        self.pdf_spread.setChecked(get_pdf_two_page_spread())
        self.pdf_spread.setToolTip(
            "Aktuelle und nächste Seite nebeneinander (Ansicht/Toolbar „2S“, Ctrl+2)"
        )
        form.addRow(self.pdf_spread)

        self.pdf_continuous = QCheckBox("PDF Continuous Scroll")
        self.pdf_continuous.setChecked(get_pdf_continuous_scroll())
        self.pdf_continuous.setToolTip(
            "Seiten untereinander scrollen statt Einzelseite (Ansicht/Toolbar „CS“, Ctrl+3); "
            "schließt Zwei-Seiten-Ansicht aus"
        )
        form.addRow(self.pdf_continuous)

        self.page_num_overlay = QCheckBox("PDF Seitennummer-Overlay")
        self.page_num_overlay.setChecked(get_show_page_number_overlay())
        self.page_num_overlay.setToolTip(
            "Aktuelle Seitennummer als Overlay auf der PDF-Seite anzeigen "
            "(Ansicht → Seitennummer-Overlay / Toolbar „Nr.“)"
        )
        form.addRow(self.page_num_overlay)

        self.page_num_opacity = QDoubleSpinBox()
        self.page_num_opacity.setRange(0.05, 1.0)
        self.page_num_opacity.setSingleStep(0.05)
        self.page_num_opacity.setDecimals(2)
        self.page_num_opacity.setValue(get_page_number_overlay_opacity())
        self.page_num_opacity.setToolTip(
            "Deckkraft des Seitennummer-Overlays (Toolbar „Nr α“, Standard 0.59)"
        )
        form.addRow("Seitennummer-Overlay Deckkraft", self.page_num_opacity)

        self.page_num_font = QSpinBox()
        self.page_num_font.setRange(8, 36)
        self.page_num_font.setSuffix(" pt")
        self.page_num_font.setValue(get_page_number_overlay_font_size())
        self.page_num_font.setToolTip(
            "Schriftgröße des Seitennummer-Overlays (Standard 11 pt)"
        )
        form.addRow("Seitennummer-Overlay Schriftgröße", self.page_num_font)

        self.page_num_pos = QComboBox()
        self.page_num_pos.addItem("Unten mitte", "bottom-center")
        self.page_num_pos.addItem("Oben mitte", "top-center")
        cur_pos = get_page_number_overlay_position()
        pos_idx = 1 if cur_pos == "top-center" else 0
        self.page_num_pos.setCurrentIndex(pos_idx)
        self.page_num_pos.setToolTip(
            "Position des Seitennummer-Overlays: unten-mitte oder oben-mitte"
        )
        form.addRow("Seitennummer-Overlay Position", self.page_num_pos)

        self.page_num_format = QLineEdit()
        self.page_num_format.setText(get_page_number_overlay_format())
        self.page_num_format.setMaxLength(80)
        self.page_num_format.setPlaceholderText("{page} / {pages}")
        self.page_num_format.setToolTip(
            "Format-String für das Seitennummer-Overlay. "
            "Platzhalter: {page}, {pages} (Aliase {n}, {total}; optional {label})"
        )
        form.addRow("Seitennummer-Overlay Format", self.page_num_format)

        self.page_num_start = QSpinBox()
        self.page_num_start.setRange(0, 9999)
        self.page_num_start.setValue(get_page_number_overlay_start())
        self.page_num_start.setToolTip(
            "Startnummer der ersten Seite im Overlay (z. B. 5 → erste Seite zeigt 5)"
        )
        form.addRow("Seitennummer-Overlay Start", self.page_num_start)

        self.page_num_skip_edges = QCheckBox("Erste/letzte Seite ohne Overlay")
        self.page_num_skip_edges.setChecked(get_page_number_overlay_skip_edges())
        self.page_num_skip_edges.setToolTip(
            "Seitennummer-Overlay auf der ersten und letzten PDF-Seite ausblenden"
        )
        form.addRow(self.page_num_skip_edges)

        self.doc_split_orient = QComboBox()
        self.doc_split_orient.addItem("Horizontal (nebeneinander)", False)
        self.doc_split_orient.addItem("Vertikal (übereinander)", True)
        self.doc_split_orient.setCurrentIndex(1 if get_editor_doc_split_vertical() else 0)
        self.doc_split_orient.setToolTip(
            "Layout für Fenster teilen (zwei Docs): horizontal oder vertikal — wird gemerkt "
            "(gleicher Schalter wie Ansicht → Vertikaler Split / Ctrl+Shift+\\)"
        )
        form.addRow("Doc-Split Layout", self.doc_split_orient)

        self.tag_rename_confirm = QSpinBox()
        self.tag_rename_confirm.setRange(0, 99999)
        self.tag_rename_confirm.setValue(get_tag_rename_confirm_threshold())
        self.tag_rename_confirm.setToolTip(
            "Tag umbenennen: Bestätigung wenn mehr Treffer als dieser Wert "
            "(0 = immer nachfragen; Standard 20)"
        )
        form.addRow("Tag-Rename Bestätigung ab", self.tag_rename_confirm)

        self.sidecar_debounce = QSpinBox()
        self.sidecar_debounce.setRange(
            SIDECAR_SAVE_DEBOUNCE_MIN_MS, SIDECAR_SAVE_DEBOUNCE_MAX_MS
        )
        self.sidecar_debounce.setSingleStep(50)
        self.sidecar_debounce.setSuffix(" ms")
        self.sidecar_debounce.setValue(get_sidecar_save_debounce_ms())
        self.sidecar_debounce.setToolTip(
            "Sidecar-Save Debounce: Annotation-Speichern bündeln "
            f"({SIDECAR_SAVE_DEBOUNCE_MIN_MS}–{SIDECAR_SAVE_DEBOUNCE_MAX_MS} ms, Standard 400)"
        )
        form.addRow("Sidecar-Debounce", self.sidecar_debounce)

        self.snippet_context = QSpinBox()
        self.snippet_context.setRange(
            SEARCH_SNIPPET_CONTEXT_MIN, SEARCH_SNIPPET_CONTEXT_MAX
        )
        self.snippet_context.setSingleStep(5)
        self.snippet_context.setSuffix(" Zeichen")
        self.snippet_context.setValue(get_search_snippet_context_chars())
        self.snippet_context.setToolTip(
            "Treffer-Snippet: Zeichen links/rechts vom Match "
            f"({SEARCH_SNIPPET_CONTEXT_MIN}–{SEARCH_SNIPPET_CONTEXT_MAX}, Standard 40)"
        )
        form.addRow("Treffer-Snippet-Länge", self.snippet_context)

        self.snippet_ellipsis = QComboBox()
        cur_ell = get_search_snippet_ellipsis_style()
        ell_pick = 0
        for i, (key, label) in enumerate(SEARCH_SNIPPET_ELLIPSIS_CHOICES):
            self.snippet_ellipsis.addItem(label, key)
            if key == cur_ell:
                ell_pick = i
        self.snippet_ellipsis.setCurrentIndex(ell_pick)
        self.snippet_ellipsis.setToolTip(
            "Treffer-Markierung im Snippet und gekürzter Ann.-Listen-Text: "
            "«…» (Guillemets) oder … (Ellipsis)"
        )
        form.addRow("Snippet-Ellipsis-Style", self.snippet_ellipsis)

        self.status_blink = QComboBox()
        cur_blink = get_status_blink_mode()
        blink_pick = 0
        for i, (key, label) in enumerate(STATUS_BLINK_CHOICES):
            self.status_blink.addItem(label, key)
            if key == cur_blink:
                blink_pick = i
        self.status_blink.setCurrentIndex(blink_pick)
        self.status_blink.setToolTip(
            "Statusleisten-Hinweis bei pending Sidecar-Debounce: "
            "Kurz (Blink) oder Aus (einmaliger Hinweis ohne Blink)"
        )
        form.addRow("Status-Blink", self.status_blink)

        self.merge_diff_max = QSpinBox()
        self.merge_diff_max.setRange(
            MERGE_DIFF_MAX_SIDE_MIN, MERGE_DIFF_MAX_SIDE_MAX
        )
        self.merge_diff_max.setSingleStep(2)
        self.merge_diff_max.setSuffix(" Zeichen")
        self.merge_diff_max.setValue(get_merge_diff_max_side())
        self.merge_diff_max.setToolTip(
            "Ann.-Merge-Diff: max. Zeichen je Textseite im Kurzvergleich "
            f"({MERGE_DIFF_MAX_SIDE_MIN}–{MERGE_DIFF_MAX_SIDE_MAX}, Standard 28)"
        )
        form.addRow("Merge-Diff max. Länge", self.merge_diff_max)

        self.recent_files_max = QSpinBox()
        self.recent_files_max.setRange(RECENT_FILES_MAX_MIN, RECENT_FILES_MAX_MAX)
        self.recent_files_max.setValue(get_recent_files_max())
        self.recent_files_max.setToolTip(
            "Max. Anzahl „Zuletzt geöffnet“ in Menü/Sidebar "
            f"({RECENT_FILES_MAX_MIN}–{RECENT_FILES_MAX_MAX}, Standard 12)"
        )
        recent_row = QHBoxLayout()
        recent_row.addWidget(self.recent_files_max)
        self.btn_clear_recent = QPushButton("Liste leeren")
        self.btn_clear_recent.setToolTip("Zuletzt geöffnete Dateien leeren")
        self.btn_clear_recent.clicked.connect(self._clear_recent_files)
        recent_row.addWidget(self.btn_clear_recent)
        form.addRow("Zuletzt geöffnet (max.)", recent_row)

        from instantlensdoc.core.app_settings import (
            DEFAULT_ANN_EXPORT_FILENAME_TEMPLATE,
            get_ann_export_filename_template,
            get_last_ann_export_dir,
        )

        self.ann_export_tpl = AnnExportTemplateEdit(get_ann_export_filename_template())
        self.ann_export_tpl.setPlaceholderText(DEFAULT_ANN_EXPORT_FILENAME_TEMPLATE)
        self.ann_export_tpl.setToolTip(
            "Dateiname-Template für Annotation-JSON-Export. "
            "Platzhalter: {stem}, {page} (1-basiert), {date} (YYYY-MM-DD). "
            "Quick-Insert an Cursor-Position; lokales Undo (Ctrl+Z); "
            "Reset-Template auf Default — 1.2.6"
        )
        self.ann_export_tpl.textChanged.connect(self._update_ann_export_preview)
        tpl_row = QHBoxLayout()
        tpl_row.addWidget(self.ann_export_tpl, 1)
        for token in ("{stem}", "{page}", "{date}"):
            btn = QPushButton(token)
            btn.setAutoDefault(False)
            btn.setDefault(False)
            btn.setFocusPolicy(Qt.TabFocus)
            btn.setToolTip(
                f"Platzhalter {token} an Cursor-Position einfügen "
                "(lokales Undo: Ctrl+Z) — 1.2.6"
            )
            btn.clicked.connect(
                lambda _checked=False, t=token: self._insert_ann_export_placeholder(t)
            )
            tpl_row.addWidget(btn)
        self.btn_reset_ann_tpl = QPushButton("Reset-Template")
        self.btn_reset_ann_tpl.setAutoDefault(False)
        self.btn_reset_ann_tpl.setDefault(False)
        self.btn_reset_ann_tpl.setFocusPolicy(Qt.TabFocus)
        self.btn_reset_ann_tpl.setToolTip(
            f"Template auf Default zurücksetzen "
            f"({DEFAULT_ANN_EXPORT_FILENAME_TEMPLATE}); "
            "Bestätigung nur wenn Feld vom Default abweicht; "
            "danach Live-Vorschau + Fokus mit Selektion des Default-Texts — 1.2.9"
        )
        self.btn_reset_ann_tpl.clicked.connect(self._reset_ann_export_template)
        tpl_row.addWidget(self.btn_reset_ann_tpl)
        form.addRow("Ann.-Export Dateiname", tpl_row)
        self.ann_export_preview = QLabel("")
        self.ann_export_preview.setWordWrap(True)
        self.ann_export_preview.setTextFormat(Qt.RichText)
        self.ann_export_preview.setToolTip(
            "Live-Vorschau des Dateinamens (Beispiel stem=dokument, page=2); "
            "ungültige Platzhalter rot — 1.2.3"
        )
        form.addRow("Vorschau Dateiname", self.ann_export_preview)
        self._update_ann_export_preview()
        last_ann = get_last_ann_export_dir()
        self.ann_export_dir_lbl = QLabel(
            f"Ann.-Export Ordner: {last_ann}" if last_ann else "Ann.-Export Ordner: (noch keiner)"
        )
        self.ann_export_dir_lbl.setToolTip(
            "Zuletzt genutzter Zielordner für Annotation-JSON-Export — 1.2.1"
        )
        form.addRow(self.ann_export_dir_lbl)

        from instantlensdoc.core.app_settings import (
            WRAP_BLINK_DURATION_CHOICES,
            get_text_diff_ignore_whitespace,
            get_text_diff_sync_scroll,
            get_text_diff_wrap_around,
            get_text_diff_wrap_blink_duration,
            get_text_diff_wrap_blink_sound,
        )

        self.text_diff_sync_scroll = QCheckBox("Text-Diff Sync-Scroll (Side-by-Side)")
        self.text_diff_sync_scroll.setChecked(get_text_diff_sync_scroll())
        self.text_diff_sync_scroll.setToolTip(
            "Standard für Sync-Scroll im Text-Diff-Panel; "
            "wird mit dem Dialog-Toggle synchron persistiert — 1.2.4"
        )
        form.addRow(self.text_diff_sync_scroll)
        self.text_diff_ignore_ws = QCheckBox("Text-Diff Ignore-Whitespace")
        self.text_diff_ignore_ws.setChecked(get_text_diff_ignore_whitespace())
        self.text_diff_ignore_ws.setToolTip(
            "Whitespace beim Text-Diff-Vergleich ignorieren (persistiert) — 1.2.4"
        )
        form.addRow(self.text_diff_ignore_ws)
        self.text_diff_wrap_around = QCheckBox("Text-Diff Wrap-around (F7)")
        self.text_diff_wrap_around.setChecked(get_text_diff_wrap_around())
        self.text_diff_wrap_around.setToolTip(
            "Bei Nächste/Vorherige Änderung (F7/Shift+F7) am Ende "
            "wieder von vorn / vom Ende; bei Wrap Blink (Dauer/Sound unten) — 1.2.9"
        )
        form.addRow(self.text_diff_wrap_around)
        self.text_diff_wrap_blink = QComboBox()
        cur_wrap_blink = get_text_diff_wrap_blink_duration()
        wrap_blink_pick = 0
        for i, (key, label) in enumerate(WRAP_BLINK_DURATION_CHOICES):
            self.text_diff_wrap_blink.addItem(label, key)
            if key == cur_wrap_blink:
                wrap_blink_pick = i
        self.text_diff_wrap_blink.setCurrentIndex(wrap_blink_pick)
        self.text_diff_wrap_blink.setToolTip(
            "Dauer des Status-Blinks bei Wrap-around Anfang↔Ende "
            "(kurz ≈350 ms, mittel ≈700 ms, lang ≈1200 ms) — 1.2.9"
        )
        form.addRow("Wrap-Blink Dauer", self.text_diff_wrap_blink)
        self.text_diff_wrap_blink_sound = QCheckBox("Wrap-Blink System-Beep")
        self.text_diff_wrap_blink_sound.setChecked(get_text_diff_wrap_blink_sound())
        self.text_diff_wrap_blink_sound.setToolTip(
            "Akustisches Feedback: System-Beep bei Wrap-Blink; "
            "aus = stumm — 1.2.9"
        )
        form.addRow(self.text_diff_wrap_blink_sound)

        self.jpeg_q = QSpinBox()
        self.jpeg_q.setRange(10, 100)
        self.jpeg_q.setValue(get_export_jpeg_quality())
        form.addRow(tr("export_jpeg_q"), self.jpeg_q)

        self.page_combo = QComboBox()
        cur_page = get_export_pdf_page()
        page_pick = 0
        for i, name in enumerate(PAGE_SIZE_PRESETS.keys()):
            self.page_combo.addItem(name, name)
            if name == cur_page:
                page_pick = i
        self.page_combo.setCurrentIndex(page_pick)
        form.addRow(tr("export_page"), self.page_combo)

        self.max_edge = QSpinBox()
        self.max_edge.setRange(200, 8000)
        self.max_edge.setSingleStep(100)
        self.max_edge.setValue(get_export_image_max_edge())
        form.addRow("Export Max-Kante (px)", self.max_edge)

        self.update_chk = QCheckBox(tr("update_check"))
        self.update_chk.setChecked(get_update_check_on_start())
        form.addRow(self.update_chk)

        self.batch_dir = QLineEdit()
        bd = get_batch_output_dir()
        self.batch_dir.setText(str(bd) if bd else "")
        batch_row = QHBoxLayout()
        batch_row.addWidget(self.batch_dir)
        btn_b = QPushButton("…")
        btn_b.clicked.connect(lambda: self._pick_dir(self.batch_dir))
        batch_row.addWidget(btn_b)
        form.addRow(tr("batch_dir"), batch_row)

        self.open_dir = QLineEdit()
        od = get_default_open_dir()
        self.open_dir.setText(str(od) if od else "")
        open_row = QHBoxLayout()
        open_row.addWidget(self.open_dir)
        btn_o = QPushButton("…")
        btn_o.clicked.connect(lambda: self._pick_dir(self.open_dir))
        open_row.addWidget(btn_o)
        form.addRow(tr("open_dir"), open_row)

        layout.addLayout(form)

        tb_group = QGroupBox("PDF-Toolbar — Gruppen ein-/ausblenden")
        tb_layout = QVBoxLayout(tb_group)
        self._toolbar_group_checks: dict[str, QCheckBox] = {}
        cur_tb = get_pdf_toolbar_groups()
        for key, label in PDF_TOOLBAR_GROUP_LABELS.items():
            cb = QCheckBox(label)
            cb.setChecked(bool(cur_tb.get(key, True)))
            self._toolbar_group_checks[key] = cb
            tb_layout.addWidget(cb)
        layout.addWidget(tb_group)

        wiz_row = QHBoxLayout()
        self.wizard_status = QLabel()
        self._refresh_wizard_status()
        wiz_row.addWidget(self.wizard_status, 1)
        self.btn_wizard_reset = QPushButton("Wizard zurücksetzen")
        self.btn_wizard_reset.setToolTip(
            "Erste-Schritte-Wizard wieder beim Start zeigen "
            "(hebt „Nicht mehr zeigen“ / wizard_completed auf)"
        )
        self.btn_wizard_reset.clicked.connect(self._reset_wizard)
        wiz_row.addWidget(self.btn_wizard_reset)
        layout.addLayout(wiz_row)

        reset_row = QHBoxLayout()
        self.btn_reset = QPushButton("Auf Standard zurücksetzen…")
        self.btn_reset.setToolTip("Alle Einstellungen auf Werkseinstellungen zurücksetzen")
        self.btn_reset.clicked.connect(self._reset_defaults)
        reset_row.addWidget(self.btn_reset)
        reset_row.addStretch()
        layout.addLayout(reset_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _insert_ann_export_placeholder(self, token: str) -> None:
        """Quick-Insert {stem}/{page}/{date} an gespeicherter Cursor-Pos — 1.2.5."""
        if not hasattr(self, "ann_export_tpl"):
            return
        edit = self.ann_export_tpl
        if isinstance(edit, AnnExportTemplateEdit):
            edit.restore_insert_position()
        edit.insert(str(token or ""))  # undo-fähig (Ctrl+Z lokal)
        edit.setFocus()
        if isinstance(edit, AnnExportTemplateEdit):
            edit._saved_cursor = edit.cursorPosition()
            edit._saved_sel_start = -1
            edit._saved_sel_len = 0
        self._update_ann_export_preview()

    def _focus_ann_export_tpl_select_all(self) -> None:
        """Fokus + Selektion ganzer Default-Text zum schnellen Überschreiben — 1.2.9."""
        if not hasattr(self, "ann_export_tpl"):
            return
        edit = self.ann_export_tpl
        edit.setFocus()
        edit.selectAll()
        if isinstance(edit, AnnExportTemplateEdit):
            edit._saved_cursor = 0
            edit._saved_sel_start = 0
            edit._saved_sel_len = len(edit.text() or "")

    def _reset_ann_export_template(self) -> None:
        """Template auf Default; Live-Vorschau + Fokus mit Selektion — 1.2.9."""
        from instantlensdoc.core.app_settings import DEFAULT_ANN_EXPORT_FILENAME_TEMPLATE

        if not hasattr(self, "ann_export_tpl"):
            return
        edit = self.ann_export_tpl
        default = DEFAULT_ANN_EXPORT_FILENAME_TEMPLATE
        current = edit.text() or ""
        if current == default:
            # Bereits Default — keine Bestätigung; Vorschau + Fokus + Selektion
            self._update_ann_export_preview()
            QTimer.singleShot(0, self._focus_ann_export_tpl_select_all)
            return
        reply = QMessageBox.question(
            self,
            "Reset-Template",
            f"Ann.-Export-Template auf Default zurücksetzen?\n\n"
            f"Aktuell: {current}\n"
            f"Default: {default}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            QTimer.singleShot(0, self._focus_ann_export_tpl_select_all)
            return
        # selectAll + insert → ein Undo-Schritt (Ctrl+Z stellt vorherigen Text wieder her)
        edit.selectAll()
        edit.insert(default)
        if isinstance(edit, AnnExportTemplateEdit):
            edit._saved_cursor = edit.cursorPosition()
            edit._saved_sel_start = -1
            edit._saved_sel_len = 0
        # Live-Vorschau sofort; Fokus + Selektion ganzer Default-Text — 1.2.9
        self._update_ann_export_preview()
        QTimer.singleShot(0, self._focus_ann_export_tpl_select_all)

    def _update_ann_export_preview(self, *_args) -> None:
        """Live-Vorschau Ann.-Export-Dateiname; ungültige Platzhalter rot — 1.2.3."""
        if not hasattr(self, "ann_export_preview") or not hasattr(self, "ann_export_tpl"):
            return
        import html as _html

        from instantlensdoc.core.app_settings import (
            find_invalid_ann_export_placeholders,
            format_ann_export_filename,
            highlight_ann_export_template_html,
        )

        tpl = self.ann_export_tpl.text().strip() or "{stem}_ann.json"
        sample = format_ann_export_filename(
            "dokument", page=2, template=tpl
        )
        html_tpl = highlight_ann_export_template_html(tpl)
        invalid = find_invalid_ann_export_placeholders(tpl)
        parts = [html_tpl, f"→ {_html.escape(sample)}"]
        if invalid:
            listed = ", ".join(_html.escape("{" + n + "}") for n in invalid)
            parts.append(
                f'<span style="color:#c62828">Ungültige Platzhalter: {listed}</span>'
            )
        self.ann_export_preview.setText("<br>".join(parts))

    def _clear_recent_files(self) -> None:
        from instantlensdoc.core import recent as recent_mod

        reply = QMessageBox.question(
            self,
            "Zuletzt geöffnet",
            "Liste der zuletzt geöffneten Dateien wirklich leeren?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        recent_mod.clear_recent()
        parent = self.parent()
        if parent is not None and hasattr(parent, "_refresh_recent"):
            try:
                parent._refresh_recent()
            except Exception:
                pass
        if parent is not None and hasattr(parent, "_set_status"):
            try:
                parent._set_status("Zuletzt geöffnet geleert")
            except Exception:
                pass
        QMessageBox.information(self, "Zuletzt geöffnet", "Liste geleert.")

    def _sync_backup_log_buttons(self) -> None:
        """Buttons kopieren / exportieren / leeren je nach Inhalt — 1.0.7."""
        entries = getattr(self, "_backup_log_entries", None) or []
        visible = getattr(self, "_backup_log_visible", None) or []
        has_all = bool(entries)
        has_vis = bool(visible)
        if hasattr(self, "btn_backup_log_copy"):
            self.btn_backup_log_copy.setEnabled(has_vis)
        if hasattr(self, "btn_backup_log_export"):
            self.btn_backup_log_export.setEnabled(has_vis)
        if hasattr(self, "btn_backup_log_clear"):
            self.btn_backup_log_clear.setEnabled(has_all)

    def _on_backup_log_filter(self, _idx: int = 0) -> None:
        """Filter Erfolg/Fehler anwenden — 1.0.7."""
        mode = "all"
        if hasattr(self, "backup_log_filter"):
            data = self.backup_log_filter.currentData()
            mode = str(data or "all")
        self._backup_log_filter_mode = mode
        self._populate_backup_log_list()

    def _on_backup_log_sort(self, checked: bool = True) -> None:
        """Sortierung neueste zuerst umschalten — 1.0.9."""
        self._backup_log_newest_first = bool(checked)
        self._populate_backup_log_list()

    def _populate_backup_log_list(self) -> None:
        from PySide6.QtCore import Qt as _Qt

        from instantlensdoc.core.manual_backup import (
            filter_backup_log,
            format_backup_log_line,
            sort_backup_log,
        )

        mode = getattr(self, "_backup_log_filter_mode", "all") or "all"
        newest_first = bool(getattr(self, "_backup_log_newest_first", True))
        entries = getattr(self, "_backup_log_entries", None) or []
        visible = filter_backup_log(entries, mode=mode)
        visible = sort_backup_log(visible, newest_first=newest_first)
        self._backup_log_visible = visible
        self.backup_log_list.clear()
        for entry in visible:
            item = QListWidgetItem(format_backup_log_line(entry))
            item.setData(_Qt.UserRole, entry)
            self.backup_log_list.addItem(item)
        # Leere-Liste-Hinweistext (Label + Listenplatzhalter) — 1.0.9
        empty_all = not entries
        empty_filter = bool(entries) and not visible
        if hasattr(self, "backup_log_empty_hint"):
            if empty_all:
                self.backup_log_empty_hint.setText(
                    "Noch keine Backup-Vorgänge protokolliert."
                )
                self.backup_log_empty_hint.setVisible(True)
            elif empty_filter:
                self.backup_log_empty_hint.setText(
                    "Keine Einträge für diesen Filter."
                )
                self.backup_log_empty_hint.setVisible(True)
            else:
                self.backup_log_empty_hint.setVisible(False)
        if self.backup_log_list.count() == 0:
            if empty_all:
                empty = QListWidgetItem("(noch keine Backup-Vorgänge protokolliert)")
            else:
                empty = QListWidgetItem("(keine Einträge für diesen Filter)")
            empty.setFlags(_Qt.NoItemFlags)
            self.backup_log_list.addItem(empty)
        self._sync_backup_log_buttons()

    def _reload_backup_log_list(self) -> None:
        from instantlensdoc.core.manual_backup import load_backup_log

        self._backup_log_entries = list(load_backup_log())
        self._populate_backup_log_list()

    def _backup_log_entry_from_item(self, item) -> dict | None:
        """Eintrag aus Listeneintrag (Filter-sicher via UserRole) — 1.0.7."""
        from PySide6.QtCore import Qt as _Qt

        if item is None or item.flags() == 0:
            return None
        data = item.data(_Qt.UserRole)
        if isinstance(data, dict):
            return data
        return None

    def _open_backup_log_entry(self, item=None) -> None:
        """Doppelklick: Backup-Datei öffnen, sonst Ordner — 1.0.6/1.0.7."""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        if item is None:
            item = self.backup_log_list.currentItem()
        entry = self._backup_log_entry_from_item(item)
        if entry is None:
            return
        dest = str(entry.get("dest") or "").strip()
        source = str(entry.get("source") or "").strip()
        target = Path(dest) if dest else (Path(source) if source else None)
        if target is None:
            QMessageBox.information(
                self, "Backup-Log", "Kein Dateipfad in diesem Eintrag."
            )
            return
        if target.is_file():
            opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
            status = f"Backup geöffnet: {target}"
        else:
            folder = target if target.is_dir() else target.parent
            if not folder.is_dir():
                # Fallback: Backup-Stammordner
                try:
                    from instantlensdoc.core.manual_backup import backup_dir

                    folder = backup_dir()
                except Exception:
                    folder = None
            if folder is None or not Path(folder).is_dir():
                QMessageBox.warning(
                    self,
                    "Backup-Log",
                    f"Datei fehlt und Ordner nicht gefunden:\n{target}",
                )
                return
            opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
            status = f"Backup-Ordner geöffnet (Datei fehlt): {folder}"
        parent = self.parent()
        if parent is not None and hasattr(parent, "_set_status") and opened:
            try:
                parent._set_status(status)
            except Exception:
                pass

    def _copy_backup_log_entry(self) -> None:
        """Ausgewählten Backup-Log-Eintrag in die Zwischenablage — 1.0.5/1.0.7."""
        from PySide6.QtWidgets import QApplication

        from instantlensdoc.core.manual_backup import format_backup_log_line

        item = self.backup_log_list.currentItem()
        entry = self._backup_log_entry_from_item(item)
        visible = getattr(self, "_backup_log_visible", None) or []
        text = ""
        if entry is not None:
            text = format_backup_log_line(entry)
        elif visible:
            text = format_backup_log_line(visible[0])
            self.backup_log_list.setCurrentRow(0)
        if not text or text.startswith("(noch keine") or text.startswith("(keine Einträge"):
            QMessageBox.information(
                self, "Backup-Log", "Kein Eintrag zum Kopieren vorhanden."
            )
            return
        QApplication.clipboard().setText(text)
        parent = self.parent()
        if parent is not None and hasattr(parent, "_set_status"):
            try:
                parent._set_status("Backup-Log-Eintrag kopiert")
            except Exception:
                pass

    def _export_backup_log(self) -> None:
        """Gefiltertes Backup-Log als TXT (Zeitstempel-Name, UTF-8 BOM) — 1.0.8."""
        from instantlensdoc.core.manual_backup import (
            default_backup_log_export_name,
            export_backup_log_txt,
        )

        visible = getattr(self, "_backup_log_visible", None) or []
        if not visible:
            QMessageBox.information(
                self, "Backup-Log", "Keine Einträge zum Exportieren."
            )
            return
        suggested = Path.home() / default_backup_log_export_name()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Backup-Log exportieren",
            str(suggested),
            "Textdatei (*.txt);;Alle Dateien (*)",
        )
        if not path:
            return
        try:
            out = export_backup_log_txt(path, visible, utf8_bom=True)
        except Exception as e:
            QMessageBox.critical(
                self, "Backup-Log", f"Export fehlgeschlagen:\n{e}"
            )
            return
        parent = self.parent()
        if parent is not None and hasattr(parent, "_set_status"):
            try:
                parent._set_status(f"Backup-Log exportiert: {out}")
            except Exception:
                pass
        QMessageBox.information(
            self, "Backup-Log", f"Log exportiert:\n{out}"
        )

    def _clear_backup_log(self) -> None:
        """Backup-Log leeren — 1.0.5."""
        from instantlensdoc.core.manual_backup import clear_backup_log

        reply = QMessageBox.question(
            self,
            "Backup-Log",
            "Backup-Log wirklich leeren? Alle protokollierten Einträge werden gelöscht.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        clear_backup_log()
        self._reload_backup_log_list()
        parent = self.parent()
        if parent is not None and hasattr(parent, "_set_status"):
            try:
                parent._set_status("Backup-Log geleert")
            except Exception:
                pass

    def _pick_dir(self, field: QLineEdit):
        start = field.text().strip() or str(Path.home())
        path = QFileDialog.getExistingDirectory(self, tr("pick_dir"), start)
        if path:
            field.setText(path)

    def _pick_spell_dict(self):
        start = self.spell_dict.text().strip() or str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Rechtschreibwörterbuch (Wortliste)",
            start,
            "Text / Wortliste (*.txt *.dic *.wordlist *);;Alle Dateien (*)",
        )
        if path:
            self.spell_dict.setText(path)

    def _update_prefetch_live_label(self, *_args) -> None:
        """Live-Anzeige „aktuell N ms / ±N“ — 1.3.4."""
        try:
            ms = int(self.thumb_cancel_ms.currentData() or 90)
        except (TypeError, ValueError):
            ms = 90
        try:
            radius = int(self.thumb_prefetch.currentData() or 2)
        except (TypeError, ValueError):
            radius = 2
        self.lbl_prefetch_live.setText(f"aktuell {ms} ms / ±{radius}")

    def _sync_zoom_pct_enabled(self) -> None:
        mode = str(self.zoom_mode.currentData() or DEFAULT_ZOOM_MODE_PERCENT)
        self.zoom_pct.setEnabled(mode == DEFAULT_ZOOM_MODE_PERCENT)

    def _capture_current_pdf_zoom(self) -> None:
        parent = self.parent()
        pdf_view = getattr(parent, "pdf_view", None) if parent is not None else None
        if pdf_view is None or not getattr(pdf_view, "pdf_path", None):
            QMessageBox.information(
                self,
                "Standard-Zoom",
                "Kein PDF geöffnet — bitte zuerst ein PDF laden und zoomen.",
            )
            return
        pct = max(25, min(500, int(round(float(pdf_view.scale) * 100))))
        self.zoom_pct.setValue(pct)
        for i in range(self.zoom_mode.count()):
            if self.zoom_mode.itemData(i) == DEFAULT_ZOOM_MODE_PERCENT:
                self.zoom_mode.setCurrentIndex(i)
                break
        self._sync_zoom_pct_enabled()
        QMessageBox.information(
            self,
            "Standard-Zoom",
            f"Aktueller Zoom {pct}% übernommen (nach OK speichern).",
        )

    def _refresh_wizard_status(self) -> None:
        if get_wizard_completed():
            self.wizard_status.setText("Erste-Schritte-Wizard: dauerhaft aus")
            self.wizard_status.setStyleSheet("color: #666;")
        else:
            self.wizard_status.setText("Erste-Schritte-Wizard: beim Start aktiv")
            self.wizard_status.setStyleSheet("color: #444;")

    def _reset_color_presets_ui(self) -> None:
        """Alle Color-Presets sofort auf Werksstandard speichern — 0.9.6/0.9.8."""
        reply = QMessageBox.question(
            self,
            "Color-Presets",
            "Alle 6 Color-Presets auf Werksstandard zurücksetzen?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        presets = reset_ann_color_presets()
        self._sync_preset_edits(presets)

    def _load_factory_color_presets_ui(self) -> None:
        """Factory-Defaults in Felder laden (Bestätigung + Undo) — 0.9.8/0.9.9."""
        reply = QMessageBox.question(
            self,
            "Werksstandard",
            "Factory-Defaults in die Color-Preset-Felder laden?\n"
            "(Wird nach OK gespeichert; Rückgängig möglich.)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        prev = [ed.text().strip() for ed in (getattr(self, "_preset_edits", []) or [])]
        presets = factory_ann_color_presets()
        self._sync_preset_edits(presets)
        self._preset_undo = prev
        if hasattr(self, "btn_undo_factory_presets"):
            self.btn_undo_factory_presets.setEnabled(bool(prev))

    def _undo_factory_color_presets_ui(self) -> None:
        """Letzte Factory-Änderung in den Preset-Feldern rückgängig — 0.9.9."""
        prev = getattr(self, "_preset_undo", None)
        if not prev:
            return
        self._sync_preset_edits(list(prev))
        self._preset_undo = None
        if hasattr(self, "btn_undo_factory_presets"):
            self.btn_undo_factory_presets.setEnabled(False)

    def _sync_preset_edits(self, presets: list[str]) -> None:
        for i, ed in enumerate(getattr(self, "_preset_edits", []) or []):
            ed.setText(presets[i] if i < len(presets) else "#888888")

    def _export_color_presets_ui(self) -> None:
        """Color-Presets als ildcolors-v1 JSON speichern — 0.9.7."""
        from instantlensdoc.core.app_settings import (
            dialog_start_dir,
            get_last_export_dir,
            set_ann_color_presets,
            set_last_export_dir,
        )

        # Aktuelle Dialogfelder zuerst übernehmen
        if getattr(self, "_preset_edits", None):
            set_ann_color_presets([ed.text().strip() for ed in self._preset_edits])
        start = dialog_start_dir(get_last_export_dir())
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Color-Presets exportieren",
            str(Path(start) / "ild-colors.json"),
            f"Color-Presets JSON (*{ANN_COLORS_SCHEMA_ID}*.json *.json);;JSON (*.json)",
        )
        if not path:
            return
        try:
            dest = export_ann_color_presets_json(path)
        except Exception as e:
            QMessageBox.warning(self, "Color-Presets Export", str(e))
            return
        set_last_export_dir(dest.parent)
        QMessageBox.information(
            self,
            "Color-Presets",
            f"Exportiert ({ANN_COLORS_SCHEMA_ID}):\n{dest}",
        )

    def _import_color_presets_ui(self) -> None:
        """Color-Presets aus ildcolors-v1 JSON laden — 0.9.7."""
        from instantlensdoc.core.app_settings import (
            dialog_start_dir,
            get_last_export_dir,
            set_last_export_dir,
        )

        start = dialog_start_dir(get_last_export_dir())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Color-Presets importieren",
            str(start),
            "JSON (*.json);;Alle Dateien (*)",
        )
        if not path:
            return
        reply = QMessageBox.question(
            self,
            "Color-Presets importieren",
            "Vorhandene Presets ersetzen?\n"
            "„Nein“ = nur gefüllte Slots aus der Datei übernehmen (Merge).",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Cancel:
            return
        merge = reply == QMessageBox.No
        try:
            presets = import_ann_color_presets_json(path, merge=merge)
        except AnnColorsImportError as e:
            QMessageBox.warning(self, "Color-Presets Import", str(e))
            return
        except Exception as e:
            QMessageBox.warning(self, "Color-Presets Import", str(e))
            return
        self._sync_preset_edits(presets)
        set_last_export_dir(Path(path).parent)
        QMessageBox.information(
            self,
            "Color-Presets",
            f"Importiert ({ANN_COLORS_SCHEMA_ID}, {'Merge' if merge else 'Ersetzen'}):\n"
            + ", ".join(presets),
        )

    def _reset_wizard(self) -> None:
        """„Nicht mehr zeigen“ aufheben — Wizard erscheint wieder beim Start."""
        if not get_wizard_completed():
            set_wizard_skip_once(False)
            self._refresh_wizard_status()
            QMessageBox.information(
                self,
                "Wizard",
                "Wizard ist bereits aktiv (wird beim nächsten Start gezeigt).",
            )
            return
        reply = QMessageBox.question(
            self,
            "Wizard zurücksetzen",
            "Erste-Schritte-Wizard wieder beim App-Start zeigen?\n"
            "(„Nicht mehr zeigen“ wird aufgehoben)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            return
        set_wizard_completed(False)
        set_wizard_skip_once(False)
        self._refresh_wizard_status()
        QMessageBox.information(
            self,
            "Wizard",
            "Wizard zurückgesetzt — erscheint beim nächsten App-Start erneut.",
        )

    def _reset_defaults(self):
        reply = QMessageBox.question(
            self,
            "Einstellungen zurücksetzen",
            "Alle Einstellungen auf Werkseinstellungen zurücksetzen?\n"
            "(Theme, Zoom, Pfade, Editor-Optionen, Annotation-Farben, …)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        reset_to_defaults()
        sync_from_settings()
        apply_theme(mode=get_theme())
        parent = self.parent()
        if parent is not None and hasattr(parent, "apply_tray_setting"):
            try:
                parent.apply_tray_setting()
            except Exception:
                pass
        if parent is not None and hasattr(parent, "_update_doc_status"):
            try:
                parent._update_doc_status()
            except Exception:
                pass
        if parent is not None and hasattr(parent, "pdf_view"):
            try:
                parent.pdf_view.apply_settings_colors()
                parent.pdf_view.apply_toolbar_groups()
            except Exception:
                pass
        QMessageBox.information(
            self,
            "Einstellungen",
            "Werkseinstellungen wiederhergestellt.\nDialog wird geschlossen — Werte sind gespeichert.",
        )
        self.accept()

    def _save(self):
        theme = self.theme_combo.currentData() or "light"
        lang = self.lang_combo.currentData() or "deu+eng"
        set_theme("dark" if theme == "dark" else "light")
        set_ocr_lang(str(lang))
        try:
            dpi_val = int(self.ocr_dpi_combo.currentData() or 150)
        except (TypeError, ValueError):
            dpi_val = 150
        set_ocr_dpi(dpi_val)
        set_ocr_attach_errors(self.ocr_attach_errors.isChecked())
        try:
            toast_sec = int(self.ocr_toast_sec.currentData() or 2)
        except (TypeError, ValueError):
            toast_sec = 2
        set_ocr_defaults_toast_sec(toast_sec)
        set_merge_close_preview_on_edit(self.merge_close_preview.isChecked())
        set_ui_lang(str(self.ui_lang.currentData() or "de"))
        sync_from_settings()
        set_update_check_on_start(self.update_chk.isChecked())
        set_default_zoom_mode(str(self.zoom_mode.currentData() or DEFAULT_ZOOM_MODE_PERCENT))
        set_default_zoom_percent(int(self.zoom_pct.value()))
        set_pdf_thumbnail_scale(float(self.thumb_scale.currentData() or 0.18))
        try:
            lazy_th = int(self.thumb_lazy.currentData() or 50)
        except (TypeError, ValueError):
            lazy_th = 50
        set_thumb_lazy_threshold(lazy_th)
        try:
            pref_r = int(self.thumb_prefetch.currentData() or 2)
        except (TypeError, ValueError):
            pref_r = 2
        set_thumb_prefetch_radius(pref_r)
        try:
            cancel_ms = int(self.thumb_cancel_ms.currentData() or 90)
        except (TypeError, ValueError):
            cancel_ms = 90
        set_thumb_prefetch_cancel_ms(cancel_ms)
        set_redaction_preview_opacity(float(self.redact_opacity.value()))
        set_autosave_enabled(self.autosave_enabled.isChecked())
        try:
            as_sec = int(self.autosave_sec.currentData() or 60)
        except (TypeError, ValueError):
            as_sec = 60
        set_autosave_interval_sec(as_sec)
        set_autosave_backup_enabled(self.autosave_backup.isChecked())
        set_autosave_backup_max(int(self.autosave_backup_max.value()))
        if getattr(self, "_preset_edits", None):
            set_ann_color_presets([ed.text().strip() for ed in self._preset_edits])
        self._preset_undo = None
        if hasattr(self, "btn_undo_factory_presets"):
            self.btn_undo_factory_presets.setEnabled(False)
        set_editor_line_numbers(self.line_numbers.isChecked())
        set_editor_minimap(self.minimap.isChecked())
        set_editor_soft_wrap(self.soft_wrap.isChecked())
        set_editor_tab_width(int(self.tab_width.currentData() or 4))
        set_editor_soft_tabs(self.soft_tabs.isChecked())
        set_editor_indent_guides(self.indent_guides.isChecked())
        set_editor_current_line_highlight(self.current_line_hl.isChecked())
        set_editor_show_special_chars(self.special_chars.isChecked())
        set_editor_text_encoding(str(self.enc_combo.currentData() or "auto"))
        set_skip_splash(self.skip_splash.isChecked())
        set_spellcheck_dict_path(self.spell_dict.text().strip())
        set_editor_trim_trailing_whitespace(self.trim_trailing.isChecked())
        set_editor_trim_whitespace_on_paste(self.trim_paste.isChecked())
        set_editor_bracket_match(self.bracket_match.isChecked())
        set_editor_bracket_auto_close(self.bracket_auto_close.isChecked())
        set_pdf_toolbar_groups(
            {k: cb.isChecked() for k, cb in self._toolbar_group_checks.items()}
        )
        set_minimize_to_tray(self.minimize_tray.isChecked())
        set_backup_on_save(self.backup_on_save.isChecked())
        set_restore_window_geometry_on_start(self.restore_geometry.isChecked())
        set_restore_session_on_start(self.restore_session.isChecked())
        set_page_size_unit(str(self.page_unit.currentData() or "mm"))
        set_pdf_grayscale(self.pdf_grayscale.isChecked())
        set_print_grayscale(self.print_grayscale.isChecked())
        set_print_preview(self.print_preview.isChecked())
        set_pdf_night_mode(self.pdf_night.isChecked())
        set_pdf_two_page_spread(self.pdf_spread.isChecked())
        set_pdf_continuous_scroll(self.pdf_continuous.isChecked())
        set_show_page_number_overlay(self.page_num_overlay.isChecked())
        set_page_number_overlay_opacity(float(self.page_num_opacity.value()))
        set_page_number_overlay_font_size(int(self.page_num_font.value()))
        set_page_number_overlay_position(
            str(self.page_num_pos.currentData() or "bottom-center")
        )
        set_page_number_overlay_format(self.page_num_format.text().strip())
        set_page_number_overlay_start(int(self.page_num_start.value()))
        set_page_number_overlay_skip_edges(self.page_num_skip_edges.isChecked())
        set_editor_doc_split_vertical(bool(self.doc_split_orient.currentData()))
        set_tag_rename_confirm_threshold(int(self.tag_rename_confirm.value()))
        set_sidecar_save_debounce_ms(int(self.sidecar_debounce.value()))
        set_search_snippet_context_chars(int(self.snippet_context.value()))
        set_search_snippet_ellipsis_style(
            str(self.snippet_ellipsis.currentData() or "guillemets")
        )
        set_status_blink_mode(str(self.status_blink.currentData() or "kurz"))
        set_merge_diff_max_side(int(self.merge_diff_max.value()))
        set_recent_files_max(int(self.recent_files_max.value()))
        from instantlensdoc.core.app_settings import (
            set_ann_export_filename_template,
            set_text_diff_ignore_whitespace,
            set_text_diff_sync_scroll,
            set_text_diff_wrap_around,
            set_text_diff_wrap_blink_duration,
            set_text_diff_wrap_blink_sound,
        )

        if hasattr(self, "ann_export_tpl"):
            set_ann_export_filename_template(self.ann_export_tpl.text().strip())
        if hasattr(self, "text_diff_sync_scroll"):
            set_text_diff_sync_scroll(self.text_diff_sync_scroll.isChecked())
        if hasattr(self, "text_diff_ignore_ws"):
            set_text_diff_ignore_whitespace(self.text_diff_ignore_ws.isChecked())
        if hasattr(self, "text_diff_wrap_around"):
            set_text_diff_wrap_around(self.text_diff_wrap_around.isChecked())
        if hasattr(self, "text_diff_wrap_blink"):
            set_text_diff_wrap_blink_duration(
                str(self.text_diff_wrap_blink.currentData() or "kurz")
            )
        if hasattr(self, "text_diff_wrap_blink_sound"):
            set_text_diff_wrap_blink_sound(
                self.text_diff_wrap_blink_sound.isChecked()
            )
        parent = self.parent()
        if parent is not None and hasattr(parent, "_refresh_recent"):
            try:
                parent._refresh_recent()
            except Exception:
                pass
        save_settings(
            {
                "export_jpeg_quality": int(self.jpeg_q.value()),
                "export_pdf_page": str(self.page_combo.currentData() or "A4"),
                "export_image_max_edge": int(self.max_edge.value()),
            }
        )
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
        parent = self.parent()
        if parent is not None and hasattr(parent, "apply_tray_setting"):
            try:
                parent.apply_tray_setting()
            except Exception:
                pass
        if parent is not None and hasattr(parent, "_update_doc_status"):
            try:
                parent._update_doc_status()
            except Exception:
                pass
        if parent is not None and hasattr(parent, "editor") and hasattr(
            parent.editor, "set_bracket_match_enabled"
        ):
            try:
                parent.editor.set_bracket_match_enabled(self.bracket_match.isChecked())
            except Exception:
                pass
        if parent is not None and hasattr(parent, "editor") and hasattr(
            parent.editor, "set_bracket_auto_close_enabled"
        ):
            try:
                parent.editor.set_bracket_auto_close_enabled(
                    self.bracket_auto_close.isChecked()
                )
            except Exception:
                pass
        if parent is not None and hasattr(parent, "editor"):
            try:
                if hasattr(parent.editor, "set_line_numbers_visible"):
                    parent.editor.set_line_numbers_visible(self.line_numbers.isChecked())
                if hasattr(parent.editor, "set_minimap_visible"):
                    parent.editor.set_minimap_visible(self.minimap.isChecked())
                if hasattr(parent.editor, "set_soft_wrap"):
                    parent.editor.set_soft_wrap(self.soft_wrap.isChecked())
                if hasattr(parent.editor, "set_tab_width"):
                    parent.editor.set_tab_width(int(self.tab_width.currentData() or 4))
                if hasattr(parent.editor, "set_soft_tabs"):
                    parent.editor.set_soft_tabs(self.soft_tabs.isChecked())
                if hasattr(parent.editor, "set_indent_guides_visible"):
                    parent.editor.set_indent_guides_visible(self.indent_guides.isChecked())
                if hasattr(parent.editor, "set_current_line_highlight"):
                    parent.editor.set_current_line_highlight(self.current_line_hl.isChecked())
                if hasattr(parent.editor, "set_special_chars_visible"):
                    parent.editor.set_special_chars_visible(self.special_chars.isChecked())
            except Exception:
                pass
        if parent is not None and hasattr(parent, "_minimap_action"):
            try:
                parent._minimap_action.blockSignals(True)
                parent._minimap_action.setChecked(self.minimap.isChecked())
                parent._minimap_action.blockSignals(False)
            except Exception:
                pass
        if parent is not None and hasattr(parent, "_line_numbers_action"):
            try:
                parent._line_numbers_action.blockSignals(True)
                parent._line_numbers_action.setChecked(self.line_numbers.isChecked())
                parent._line_numbers_action.blockSignals(False)
            except Exception:
                pass
        if parent is not None and hasattr(parent, "_soft_wrap_action"):
            try:
                parent._soft_wrap_action.blockSignals(True)
                parent._soft_wrap_action.setChecked(self.soft_wrap.isChecked())
                parent._soft_wrap_action.blockSignals(False)
            except Exception:
                pass
        if parent is not None and hasattr(parent, "pdf_view"):
            try:
                parent.pdf_view.apply_settings_colors()
                parent.pdf_view.apply_toolbar_groups()
                if hasattr(parent.pdf_view, "set_show_page_number_overlay"):
                    parent.pdf_view.set_show_page_number_overlay(
                        self.page_num_overlay.isChecked()
                    )
                if hasattr(parent.pdf_view, "set_page_number_overlay_opacity"):
                    parent.pdf_view.set_page_number_overlay_opacity(
                        float(self.page_num_opacity.value())
                    )
                if hasattr(parent.pdf_view, "set_page_number_overlay_font_size"):
                    parent.pdf_view.set_page_number_overlay_font_size(
                        int(self.page_num_font.value())
                    )
                if hasattr(parent.pdf_view, "set_page_number_overlay_position"):
                    parent.pdf_view.set_page_number_overlay_position(
                        str(self.page_num_pos.currentData() or "bottom-center")
                    )
                if hasattr(parent.pdf_view, "set_page_number_overlay_format"):
                    parent.pdf_view.set_page_number_overlay_format(
                        self.page_num_format.text().strip()
                    )
                if hasattr(parent.pdf_view, "set_page_number_overlay_start"):
                    parent.pdf_view.set_page_number_overlay_start(
                        int(self.page_num_start.value())
                    )
                if hasattr(parent.pdf_view, "set_page_number_overlay_skip_edges"):
                    parent.pdf_view.set_page_number_overlay_skip_edges(
                        self.page_num_skip_edges.isChecked()
                    )
                if hasattr(parent.pdf_view, "set_redaction_preview_opacity"):
                    parent.pdf_view.set_redaction_preview_opacity(
                        float(self.redact_opacity.value())
                    )
                if hasattr(parent, "_refresh_thumbs"):
                    parent._refresh_thumbs()
            except Exception:
                pass
        if parent is not None and hasattr(parent, "_indent_guides_action"):
            try:
                parent._indent_guides_action.blockSignals(True)
                parent._indent_guides_action.setChecked(self.indent_guides.isChecked())
                parent._indent_guides_action.blockSignals(False)
            except Exception:
                pass
        if parent is not None and hasattr(parent, "_current_line_hl_action"):
            try:
                parent._current_line_hl_action.blockSignals(True)
                parent._current_line_hl_action.setChecked(self.current_line_hl.isChecked())
                parent._current_line_hl_action.blockSignals(False)
            except Exception:
                pass
        if parent is not None and hasattr(parent, "_sync_page_number_overlay_action"):
            try:
                parent._sync_page_number_overlay_action(
                    self.page_num_overlay.isChecked()
                )
            except Exception:
                pass
        if parent is not None and hasattr(parent, "_sync_spread_action"):
            try:
                parent._sync_spread_action()
            except Exception:
                pass
        if parent is not None and hasattr(parent, "_sync_continuous_action"):
            try:
                parent._sync_continuous_action()
            except Exception:
                pass
        if parent is not None and hasattr(parent, "_sync_doc_split_orientation"):
            try:
                parent._sync_doc_split_orientation()
            except Exception:
                pass
        self.accept()
