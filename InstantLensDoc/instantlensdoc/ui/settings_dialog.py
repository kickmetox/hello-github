"""Einstellungen: Theme, OCR, Sprache, Export, Zoom, Autosave, Pfade."""

from __future__ import annotations

from pathlib import Path

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
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from ild_pdf.pages import PAGE_SIZE_PRESETS
from instantlensdoc.core.app_settings import (
    get_autosave_interval_sec,
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
    get_ocr_lang,
    get_page_size_unit,
    get_pdf_continuous_scroll,
    get_pdf_grayscale,
    get_pdf_night_mode,
    get_pdf_thumbnail_scale,
    get_pdf_two_page_spread,
    get_editor_soft_tabs,
    get_editor_tab_width,
    get_page_number_overlay_font_size,
    get_page_number_overlay_opacity,
    get_page_number_overlay_position,
    get_show_page_number_overlay,
    get_restore_session_on_start,
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
    reset_to_defaults,
    save_settings,
    set_recent_files_max,
    set_wizard_completed,
    set_wizard_skip_once,
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
    set_ocr_lang,
    set_page_size_unit,
    set_pdf_continuous_scroll,
    set_pdf_grayscale,
    set_pdf_night_mode,
    set_pdf_thumbnail_scale,
    set_pdf_two_page_spread,
    set_page_number_overlay_font_size,
    set_page_number_overlay_opacity,
    set_page_number_overlay_position,
    set_show_page_number_overlay,
    set_restore_session_on_start,
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
from instantlensdoc.core.ocr import LANG_PRESETS
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
        form.addRow(tr("ocr_lang"), self.lang_combo)

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

        self.autosave_sec = QSpinBox()
        self.autosave_sec.setRange(10, 600)
        self.autosave_sec.setSingleStep(10)
        self.autosave_sec.setSuffix(" s")
        self.autosave_sec.setValue(get_autosave_interval_sec())
        self.autosave_sec.setToolTip("Intervall für Autosave (Editor + Annotationen)")
        form.addRow(tr("autosave_interval"), self.autosave_sec)

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

        self.restore_session = QCheckBox("Beim Start letzte Session wiederherstellen")
        self.restore_session.setChecked(get_restore_session_on_start())
        self.restore_session.setToolTip(
            "Offene Dokumente der letzten Sitzung beim Start laden (optional)"
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
        set_ui_lang(str(self.ui_lang.currentData() or "de"))
        sync_from_settings()
        set_update_check_on_start(self.update_chk.isChecked())
        set_default_zoom_mode(str(self.zoom_mode.currentData() or DEFAULT_ZOOM_MODE_PERCENT))
        set_default_zoom_percent(int(self.zoom_pct.value()))
        set_pdf_thumbnail_scale(float(self.thumb_scale.currentData() or 0.18))
        set_autosave_interval_sec(int(self.autosave_sec.value()))
        set_editor_line_numbers(self.line_numbers.isChecked())
        set_editor_minimap(self.minimap.isChecked())
        set_editor_soft_wrap(self.soft_wrap.isChecked())
        set_editor_tab_width(int(self.tab_width.currentData() or 4))
        set_editor_soft_tabs(self.soft_tabs.isChecked())
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
        set_restore_session_on_start(self.restore_session.isChecked())
        set_page_size_unit(str(self.page_unit.currentData() or "mm"))
        set_pdf_grayscale(self.pdf_grayscale.isChecked())
        set_pdf_night_mode(self.pdf_night.isChecked())
        set_pdf_two_page_spread(self.pdf_spread.isChecked())
        set_pdf_continuous_scroll(self.pdf_continuous.isChecked())
        set_show_page_number_overlay(self.page_num_overlay.isChecked())
        set_page_number_overlay_opacity(float(self.page_num_opacity.value()))
        set_page_number_overlay_font_size(int(self.page_num_font.value()))
        set_page_number_overlay_position(
            str(self.page_num_pos.currentData() or "bottom-center")
        )
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
