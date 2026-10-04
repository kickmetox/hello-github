"""Persistente App-Einstellungen (Theme, OCR, Pfade, Export, Zoom, Autosave)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

from instantlensdoc.config import config_dir

SETTINGS_NAME = "ui_settings.json"

ThemeMode = Literal["light", "dark", "system"]
UiLang = Literal["de", "en", "fr", "ru", "es", "zh", "pt", "ar", "it"]

DEFAULTS: dict[str, Any] = {
    "theme": "system",  # System folgen; manuell light/dark Override — 1.4.0
    "high_contrast": False,  # High-Contrast Theme Toggle — 2.0.0 (Persistenz 2.0.1)
    "ui_font_pt": 10,  # UI-Schriftgröße pt (9–20) — 2.0.0
    "ui_font_scale_percent": 100,  # UI-Schrift Skala 100|125|150 % — 2.0.1
    "ocr_lang": "deu+eng",
    "ocr_dpi": 150,  # OCR-Batch Default-DPI 150|300 — 1.1.6
    "ocr_attach_errors": True,  # OCR-Batch: Fehlerabschnitt anhängen — 1.1.5
    "ocr_defaults_toast_sec": 2,  # OCR-Defaults-Toast Dauer 1|2|3 s — 1.1.9
    "merge_close_preview_on_edit": False,  # Vorschau-Tab bei „Zum Bearbeiten“ schließen — 1.1.6
    "keygen_reveal_auto_hide_sec": 10,  # Reveal Auto-Hide 5|10|30 — 1.1.6
    "batch_output_dir": "",
    "default_open_dir": "",
    "ui_lang": "de",
    "export_jpeg_quality": 85,
    "export_pdf_page": "A4",
    "export_image_max_edge": 2000,
    "update_check_on_start": False,
    "update_dismissed_version": "",  # Update-Hinweis verworfen bis nächste Version — 1.7.1
    "presentation_hide_annotations": True,  # Ann.-Overlay in Präsentation aus — 1.7.0
    "presentation_auto_advance_sec": 0,  # 0=aus, sonst 3|5|10|30 s — 1.7.2
    "presentation_black_background": True,  # schwarzer Präsentations-Hintergrund — 1.7.1
    "presentation_show_page_number": True,  # Seitennummer-Overlay in Präsentation — 1.7.1
    "presentation_countdown_position": "bottom-right",  # unten-rechts | center — 1.7.3
    "presentation_countdown_color": "dark",  # hell | dunkel — 1.7.3
    "favorites_bar_visible": True,  # globale Lesezeichen-Leiste — 1.7.0
    "text_pdf_font_size": 11.0,  # Text→PDF Schriftgröße pt — 1.7.1
    "text_pdf_margin": 50.0,  # Text→PDF Rand pt — 1.7.1
    "last_text_pdf_dir": "",  # letzter Zielordner Text→PDF — 1.7.2
    "text_pdf_open_after": False,  # nach Text→PDF optional öffnen — 1.7.2
    "last_update_check_at": "",  # ISO-Zeitstempel letzter Update-Check — 1.7.3
    "last_export_dir": "",
    "last_ann_export_dir": "",  # letzter Zielordner Ann.-Export JSON — 1.2.1
    "ann_export_filename_template": "{stem}_ann.json",  # Dateiname-Template — 1.2.1
    "split_open_tabs": False,  # PDF-Split: erzeugte Dateien in Tabs öffnen — 1.2.3
    "text_diff_sync_scroll": True,  # Text-Diff Sync-Scroll Default — 1.2.4
    "text_diff_ignore_whitespace": False,  # Text-Diff Ignore-Whitespace — 1.2.4
    "text_diff_wrap_around": True,  # Text-Diff F7 Wrap-around — 1.2.6
    "text_diff_wrap_blink_duration": "kurz",  # Wrap-Blink Dauer kurz|mittel|lang — 1.2.9
    "text_diff_wrap_blink_sound": True,  # Wrap-Blink System-Beep vs. stumm — 1.2.9
    "pdf_compare_diff_threshold": 18,  # Raster-Diff Pixel-Schwellwert 0–255 — 1.4.1
    "pdf_compare_page_sync": True,  # Seitenwahl Sync (True) / Entkoppelt (False) — 1.4.1
    "last_pdf_diff_png_dir": "",  # letzter Zielordner Diff-PNG-Export — 1.4.2
    "last_page_image_export_dir": "",  # letzter Zielordner Seiten→Bilder — 1.5.1
    "last_export_format": "PNG",  # letztes Export-Format PNG|JPEG — 2.5.0
    "default_ann_color_theme": "",  # Default Farben-Theme Name — 2.5.1
    "custom_ann_color_themes": [],  # benutzerdefinierte Farben-Themes — 2.5.3
    "welcome_recent_filter": "",  # Welcome Recent-Filter Persistenz — 2.5.1
    "welcome_tag_filter_sort": "az",  # Quick-Tag Sort A–Z|freq — 2.5.6
    "page_image_filename_template": "{stem}_p{page}",  # Dateiname-Template — 1.5.1
    "last_signature_image": "",  # zuletzt verwendetes Signatur-Bild — 1.5.1
    "last_signature_width": 180.0,  # Signatur-Breite Default — 1.5.1
    "last_signature_height": 64.0,  # Signatur-Höhe Default — 1.5.1
    "last_signature_opacity": 1.0,  # Signatur-Deckkraft Default — 1.5.1
    "signature_aspect_lock": True,  # Aspect-Ratio Lock Signatur — 1.5.2
    "meta_backup_on_save": True,  # .ildbak vor Metadaten-Speichern — 1.5.2
    "last_rename_undo_log": "",  # letzter Batch-Rename Undo-Log (TXT) — 1.4.2
    "default_zoom_percent": 150,
    "default_zoom_mode": "percent",  # percent | fit_width | fit_page
    "autosave_interval_sec": 60,  # 15 | 30 | 60 | 120 — 0.9.7
    "autosave_enabled": True,
    "autosave_backup_enabled": False,  # .ildbak vor Autosave-Überschreiben — 0.9.9
    "autosave_backup_max": 3,  # 1–10 Rotations-Backups — 0.9.9
    "ann_highlight_color": "#FFE066",
    "ann_pen_color": "#2C3E50",
    "ann_note_color": "#FFEB3B",
    "ann_default_fill_color": "#FFE066",  # Standard-Füllfarbe Shapes — 0.9.9
    "editor_line_numbers": False,
    "editor_minimap": False,
    "ann_palette_index": 0,
    "pdf_grayscale": False,
    "pdf_night_mode": False,
    "pdf_two_page_spread": False,
    "pdf_continuous_scroll": False,
    "editor_bracket_match": True,
    "editor_bracket_auto_close": True,
    "ann_filter_presets": [],
    "workspace_layouts": [],  # benannte Sidebar-Layouts Name+Panels+Splitter — 1.6.0
    "default_workspace_layout": "",  # Name des Default-Layouts — 1.6.1
    "watermark_output_template": "{stem}_wm",  # Bake-Ausgabe-Template — 1.6.2
    "crypto_reload_prefill_password": False,  # PW vorausfüllen (unsicher) — 1.6.2
    "last_stats_export_dir": "",  # letzter Zielordner Stats-JSON — 1.6.3
    "stats_filename_template": "{stem}_stats.json",  # Stats-JSON Dateiname — 1.6.4
    "last_watermark_text": "VERTRAULICH",  # zuletzt WM-Text — 1.6.1
    "last_watermark_image": "",  # zuletzt WM-Bild — 1.6.1
    "last_watermark_opacity": 0.25,  # WM Deckkraft Settings — 1.6.1
    "last_watermark_angle": 45.0,  # WM Winkel Settings — 1.6.1
    "last_watermark_font_size": 48.0,  # WM Schriftgröße Settings — 1.6.1
    "last_watermark_img_scale": 0.45,  # WM Bild-Skalierung Settings — 1.6.1
    "last_watermark_placement": "diagonal",  # diagonal|center — 1.6.1
    "last_watermark_mode": "text",  # text|image — 1.6.1
    "ann_default_opacity": 1.0,
    "ann_default_stroke_width": 2.0,
    "recent_files_max": 12,
    "tag_cloud_sort": "freq",
    "recent_dirs": [],
    "project_workspaces": [],
    "active_project_workspace": "",
    "editor_markdown_preview": False,
    "editor_doc_split": False,
    "editor_doc_split_sync_scroll": False,
    "editor_doc_split_vertical": False,
    "tag_rename_confirm_threshold": 20,
    "wizard_completed": False,
    "wizard_skip_once": False,
    "selection_note_with_highlight": False,
    "editor_soft_wrap": True,
    "editor_tab_width": 4,
    "editor_soft_tabs": True,
    "editor_indent_guides": True,
    "editor_current_line_highlight": True,
    "editor_show_special_chars": False,
    "annotations_visible": True,
    # Annotation-Layer Typ-Toggles global (Highlight/Note/Shape/Redaction) — 1.8.0
    "ann_layer_types_visible": {
        "highlight": True,
        "note": True,
        "shape": True,
        "redaction": True,
    },
    "crash_recovery_enabled": True,  # Autosave-Snapshots für Crash-Recovery — 1.8.0
    "crash_recovery_max_age_hours": 72.0,  # Orphans älter verwerfen — 1.8.0
    "last_header_text": "",  # Kopfzeile Bake — 1.8.0
    "last_footer_text": "",  # Fußzeile Bake — 1.8.0
    "last_hf_include_page_numbers": True,
    "last_hf_page_template": "{n} / {total}",
    "last_hf_page_range": "",  # Seitenbereich z. B. 1-3,5 — 1.8.1
    "last_hf_header_position": "top-center",
    "last_hf_footer_position": "bottom-center",
    "last_hf_page_position": "bottom-right",
    "last_hf_font_size": 10.0,
    "last_hf_margin": 28.0,
    "minimize_to_tray": False,
    "page_size_unit": "mm",
    "measure_unit": "mm",  # Messanzeige mm|px — 2.1.0
    "measure_snap_to_annotation": False,  # Endpunkte an Ann.-Ecken snappen — 2.1.1
    "measure_labels_persistent": True,  # Mess-Labels in Sidecar/Overlay halten — 2.1.1
    "measure_csv_utf8_bom": True,  # Messwerte-CSV UTF-8 BOM — 2.1.2
    "last_measure_csv_dir": "",  # Zielordner Messwerte-CSV merken — 2.1.2
    "measure_csv_filename_template": "{stem}_measures.csv",  # Live-Template — 2.1.3
    "page_labels_txt_utf8_bom": True,  # PageLabels-TXT UTF-8 BOM — 2.2.4
    "last_page_labels_txt_dir": "",  # Zielordner PageLabels-TXT merken — 2.2.4
    "page_labels_txt_filename_template": "{stem}_labels.txt",  # Template — 2.2.4
    "telemetry_opt_in": False,  # anonym Diagnostik lokal — Opt-in Default aus — 2.6.26
    "stylus_pressure_enabled": True,  # Stylus-Druck → Strichstärke — 2.6.26
    "stylus_palm_rejection": True,  # Palm-Rejection Heuristik — 2.6.26
    "command_palette_recent": [],  # letzte Command-Palette-Befehle (IDs) — 2.3.1
    "command_palette_recent_max": 10,  # Recent-Anzahl 5/10/20 — 2.3.2
    "command_palette_pinned": [],  # angeheftete Palette-Befehle (IDs) — 2.3.2
    "command_palette_pin_max": 5,  # max Pins 3/5/10 — 2.3.3
    "compress_open_after": False,  # nach Kompression neues File öffnen — Settings Toggle — 2.3.2/2.3.3
    "links_txt_utf8_bom": True,  # Links-TXT UTF-8 BOM — 2.3.3
    "last_links_txt_dir": "",  # Zielordner Links-TXT merken — 2.3.3
    "links_txt_filename_template": "{stem}_links.txt",  # Template — 2.3.3
    "native_ann_import_save_sidecar": True,  # nach Kommentar-Import Sidecar speichern — 2.1.2
    "textlayer_diff_side_by_side": False,  # Textlayer Diff TXT/Panel Side-by-Side — 2.1.2
    "textlayer_diff_txt_template": "{stemA}_vs_{stemB}_{mode}.txt",  # 2.1.3
    "backup_on_save": False,
    "export_raster_dpi": 150,
    "print_grayscale": False,
    "export_profiles": [],
    "active_export_profile": "",
    "window_geometry": "",
    "window_state": "",
    "ann_color_presets": [
        "#FFE066",
        "#FF6B6B",
        "#4ECDC4",
        "#5B8DEF",
        "#F5A623",
        "#9B59B6",
    ],
    "restore_session_on_start": True,
    "restore_window_geometry_on_start": True,
    "pdf_thumbnail_scale": 0.18,
    "thumb_lazy_threshold": 50,
    "thumb_cache_max_mb": 100,  # Thumbnail Disk-Cache max Größe MB — 2.4.1
    "thumb_cache_debug_hits": False,  # Hit/Miss optional in Status — 2.4.1
    "thumb_cache_prune_mode": "on_write",  # on_write | interval — Auto-Prune — 2.4.3
    "thumb_cache_prune_interval_min": 15,  # Intervall-Minuten wenn mode=interval — 2.4.3
    "thumb_cache_prune_toast": True,  # Auto-Prune Status-Toast optional — 2.4.4
    "sync_scroll_status_indicator": True,  # Sync-Scroll Statusleisten-Indikator — 2.4.1
    "last_ann_template_id": "",  # zuletzt angewandte Annotation-Vorlage — 2.4.2
    "last_shortcuts_txt_dir": "",  # Zielordner F1 Shortcuts-TXT merken — 2.4.2
    "shortcuts_txt_filename_template": "{date}_shortcuts.txt",  # F1 TXT Template — 2.4.2
    "thumb_prefetch_radius": 2,
    "thumb_prefetch_cancel_ms": 90,
    "forms_csv_visible_only": False,  # CSV-Export Default „nur sichtbare“ — 1.3.5
    "default_stamp_image": "",  # Standard-Stempel Dateiname in config/stamps/ — 1.9.1
    "last_used_stamp_kind": "",  # text | image — Quick-Stempel 1.9.2
    "last_used_stamp_text": "",  # zuletzt verwendeter Textstempel — 1.9.2
    "last_used_stamp_color": "#C0392B",  # Farbe zuletzt verwendeter Textstempel — 1.9.2
    "last_used_stamp_image": "",  # zuletzt verwendetes Stempelbild (Basename) — 1.9.2
    "ocr_table_csv_delimiter": ";",  # Tabellen-OCR CSV: ; / , / Tab — 1.9.1
    "ocr_table_csv_utf8_bom": True,  # Tabellen-OCR CSV UTF-8 BOM — 1.9.1
    "last_ocr_table_csv_dir": "",  # Zielordner Tabellen-OCR CSV merken — 1.9.1
    "last_portfolio_extract_dir": "",  # Zielordner Portfolio-Extrakt merken — 2.0.2
    "last_multi_doc_csv_dir": "",  # Zielordner Multi-Doc-Suche CSV merken — 2.0.3
    "multi_doc_csv_filename_template": "{date}_multisearch.csv",  # Live-Template — 2.0.3
    "redaction_bake_continue_on_sidecar_skip": True,  # Bake fortsetzen merken — 1.3.6
    "redaction_preview_opacity": 0.90,
    "true_redact_strip_metadata": True,  # Echtes Schwärzen: Meta strippen — 2.6.0
    "true_redact_dpi": 150,  # Raster-DPI für echtes Schwärzen — 2.6.0
    "editor_text_encoding": "auto",
    "skip_splash": False,
    "spellcheck_dict_path": "",
    "spellcheck_use_builtin": True,  # Builtin-Wortliste der UI-Sprache — 2.6.20
    "spellcheck_grammar_hints": True,  # leichte Grammatik-Hinweise — 2.6.20
    "autocorrect_enabled": True,  # Autokorrektur beim Tippen — 2.6.20
    "autocorrect_expand_snippets": True,  # Kürzel→Bausteine — 2.6.20
    "autocorrect_user_rules": {},  # {trigger: replacement} — 2.6.20
    "show_page_boxes": False,
    "show_page_number_overlay": False,
    "page_number_overlay_opacity": 0.59,
    "page_number_overlay_font_size": 11,
    "page_number_overlay_position": "bottom-center",
    "page_number_overlay_format": "{page} / {pages}",
    "page_number_overlay_start": 1,
    "page_number_overlay_skip_edges": False,
    "show_printer_marks": False,
    "show_rulers": False,
    "show_alignment_grid": False,
    "alignment_grid_spacing_mm": 5.0,
    "alignment_grid_snap": False,
    "show_satzspiegel": False,  # Type-Area-Overlay — 2.6.12
    "satzspiegel_format": "A4",
    "satzspiegel_columns": 1,
    "alignment_guides": [],
    "ruler_unit": "mm",
    "annotations_locked": False,
    "editor_snippets": [
        "Sehr geehrte Damen und Herren,\n\n",
        "Mit freundlichen Grüßen\n",
        "— Notiz —\n",
        "Best regards,\n",
        "Vielen Dank im Voraus.\n",
        "Anbei das Dokument zur Prüfung.\n",
        "Bitte um kurze Rückmeldung.\n",
        "Freundliche Grüße\n",
        "— Textbaustein —\n",
    ],
    "user_doc_templates": [],
    "sidecar_save_debounce_ms": 400,
    "search_snippet_context_chars": 40,
    "search_snippet_ellipsis_style": "guillemets",
    "status_blink_mode": "kurz",
    "merge_diff_max_side": 28,
    "editor_trim_trailing_whitespace": False,
    "editor_trim_whitespace_on_paste": False,
    "pdf_toolbar_groups": {
        "tools": True,
        "colors": True,
        "view": True,
        "nav": True,
        "history": True,
        "zoom": True,
        "pages": True,
        "io": True,
    },
}

PDF_TOOLBAR_GROUP_LABELS: dict[str, str] = {
    "tools": "Werkzeuge",
    "colors": "Farben & Deckkraft",
    "view": "Ansicht (Grau/Nacht/Ann./Rahmen)",
    "nav": "Seitenblättern",
    "history": "Undo & Annotation",
    "zoom": "Zoom & Einpassen",
    "pages": "Seitenoperationen",
    "io": "Export / Import / Bake",
}


def settings_path() -> Path:
    return config_dir() / SETTINGS_NAME


def load_settings() -> dict[str, Any]:
    path = settings_path()
    data = dict(DEFAULTS)
    if not path.is_file():
        return data
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            for key in DEFAULTS:
                if key in raw:
                    data[key] = raw[key]
            for key, val in raw.items():
                if key not in data:
                    data[key] = val
    except Exception:
        pass
    return data


def save_settings(updates: dict[str, Any]) -> dict[str, Any]:
    data = load_settings()
    data.update(updates)
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def reset_to_defaults() -> dict[str, Any]:
    """Alle UI-Einstellungen auf Werkseinstellungen (DEFAULTS) zurücksetzen."""
    data = dict(DEFAULTS)
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def get_theme() -> ThemeMode:
    mode = str(load_settings().get("theme", DEFAULTS["theme"]) or "system").strip().lower()
    if mode == "dark":
        return "dark"
    if mode == "light":
        return "light"
    return "system"


def set_theme(mode: ThemeMode | str) -> None:
    m = str(mode or "system").strip().lower()
    if m not in ("light", "dark", "system"):
        m = "system"
    save_settings({"theme": m})


def get_high_contrast() -> bool:
    """High-Contrast Theme aktiv — 2.0.0."""
    return bool(load_settings().get("high_contrast", DEFAULTS["high_contrast"]))


def set_high_contrast(enabled: bool) -> None:
    """High-Contrast Theme speichern — 2.0.0."""
    save_settings({"high_contrast": bool(enabled)})


UI_FONT_PT_MIN = 9
UI_FONT_PT_MAX = 20
UI_FONT_PT_DEFAULT = 10


def get_ui_font_pt() -> int:
    """UI-Schriftgröße in pt (9–20) — 2.0.0."""
    raw = load_settings().get("ui_font_pt", DEFAULTS["ui_font_pt"])
    try:
        val = int(raw)
    except (TypeError, ValueError):
        val = int(DEFAULTS["ui_font_pt"])
    return max(UI_FONT_PT_MIN, min(UI_FONT_PT_MAX, val))


def set_ui_font_pt(pt: int) -> int:
    """UI-Schriftgröße speichern; Rückgabe normalisierter Wert — 2.0.0."""
    try:
        val = int(pt)
    except (TypeError, ValueError):
        val = int(DEFAULTS["ui_font_pt"])
    val = max(UI_FONT_PT_MIN, min(UI_FONT_PT_MAX, val))
    save_settings({"ui_font_pt": val})
    return val


UI_FONT_SCALE_CHOICES: tuple[int, ...] = (100, 125, 150)
UI_FONT_SCALE_DEFAULT = 100


def get_ui_font_scale_percent() -> int:
    """UI-Schrift Skala in Prozent (100|125|150) — 2.0.1."""
    raw = load_settings().get(
        "ui_font_scale_percent", DEFAULTS["ui_font_scale_percent"]
    )
    try:
        val = int(raw)
    except (TypeError, ValueError):
        val = int(DEFAULTS["ui_font_scale_percent"])
    if val not in UI_FONT_SCALE_CHOICES:
        # Nächsten erlaubten Wert wählen
        val = min(UI_FONT_SCALE_CHOICES, key=lambda c: abs(c - val))
    return int(val)


def set_ui_font_scale_percent(percent: int) -> int:
    """UI-Schrift Skala speichern; Rückgabe normalisierter Wert — 2.0.1."""
    try:
        val = int(percent)
    except (TypeError, ValueError):
        val = UI_FONT_SCALE_DEFAULT
    if val not in UI_FONT_SCALE_CHOICES:
        val = min(UI_FONT_SCALE_CHOICES, key=lambda c: abs(c - val))
    save_settings({"ui_font_scale_percent": int(val)})
    return int(val)


def effective_ui_font_pt(
    *, pt: int | None = None, scale_percent: int | None = None
) -> int:
    """Effektive UI-pt aus Basis-pt × Skala% — 2.0.1."""
    base = int(pt) if pt is not None else get_ui_font_pt()
    scale = (
        int(scale_percent)
        if scale_percent is not None
        else get_ui_font_scale_percent()
    )
    if scale not in UI_FONT_SCALE_CHOICES:
        scale = UI_FONT_SCALE_DEFAULT
    eff = int(round(base * scale / 100.0))
    return max(UI_FONT_PT_MIN, min(28, eff))


def get_ocr_lang() -> str:
    lang = load_settings().get("ocr_lang", DEFAULTS["ocr_lang"])
    return str(lang) if lang else DEFAULTS["ocr_lang"]


def set_ocr_lang(code: str) -> None:
    save_settings({"ocr_lang": code or DEFAULTS["ocr_lang"]})


OCR_DPI_CHOICES_SETTINGS: tuple[int, ...] = (150, 300)


def get_ocr_dpi() -> int:
    """OCR-Batch Default-DPI (150 oder 300) — 1.1.6."""
    raw = load_settings().get("ocr_dpi", DEFAULTS["ocr_dpi"])
    try:
        val = int(raw)
    except (TypeError, ValueError):
        val = int(DEFAULTS["ocr_dpi"])
    if val not in OCR_DPI_CHOICES_SETTINGS:
        val = min(OCR_DPI_CHOICES_SETTINGS, key=lambda x: abs(x - val))
    return val


def set_ocr_dpi(dpi: int) -> int:
    """OCR-Default-DPI speichern; Rückgabe normalisierter Wert — 1.1.6."""
    try:
        val = int(dpi)
    except (TypeError, ValueError):
        val = int(DEFAULTS["ocr_dpi"])
    if val not in OCR_DPI_CHOICES_SETTINGS:
        val = min(OCR_DPI_CHOICES_SETTINGS, key=lambda x: abs(x - val))
    save_settings({"ocr_dpi": val})
    return val


def get_ocr_attach_errors() -> bool:
    """OCR-Batch: Seitenfehler als Abschnitt anhängen (Default an) — 1.1.5."""
    return bool(load_settings().get("ocr_attach_errors", DEFAULTS["ocr_attach_errors"]))


def set_ocr_attach_errors(enabled: bool) -> None:
    save_settings({"ocr_attach_errors": bool(enabled)})


OCR_DEFAULTS_TOAST_CHOICES: tuple[int, ...] = (1, 2, 3)

# Gemeinsamer Tooltip Settings + Merge-Dialog (Readonly schließen) — 1.1.9
MERGE_CLOSE_PREVIEW_TOOLTIP = (
    "Einstellung wird sofort in den App-Settings persistiert und bleibt über "
    "Neustarts erhalten. Identisch mit Einstellungen → „Zusammenführen: "
    "Readonly-Vorschau … schließen“ (beidseitiger Sync) — 1.1.9"
)


def get_ocr_defaults_toast_sec() -> int:
    """OCR-Defaults-Toast Dauer in Sekunden (1/2/3) — 1.1.9."""
    raw = load_settings().get(
        "ocr_defaults_toast_sec", DEFAULTS["ocr_defaults_toast_sec"]
    )
    try:
        val = int(raw)
    except (TypeError, ValueError):
        val = int(DEFAULTS["ocr_defaults_toast_sec"])
    if val not in OCR_DEFAULTS_TOAST_CHOICES:
        val = min(OCR_DEFAULTS_TOAST_CHOICES, key=lambda x: abs(x - val))
    return val


def set_ocr_defaults_toast_sec(seconds: int) -> int:
    """OCR-Defaults-Toast Dauer speichern; Rückgabe normalisierter Wert — 1.1.9."""
    try:
        val = int(seconds)
    except (TypeError, ValueError):
        val = int(DEFAULTS["ocr_defaults_toast_sec"])
    if val not in OCR_DEFAULTS_TOAST_CHOICES:
        val = min(OCR_DEFAULTS_TOAST_CHOICES, key=lambda x: abs(x - val))
    save_settings({"ocr_defaults_toast_sec": val})
    return val


def get_merge_close_preview_on_edit() -> bool:
    """Readonly-Vorschau-Tab bei „Zum Bearbeiten öffnen“ schließen — 1.1.6."""
    return bool(
        load_settings().get(
            "merge_close_preview_on_edit",
            DEFAULTS["merge_close_preview_on_edit"],
        )
    )


def set_merge_close_preview_on_edit(enabled: bool) -> None:
    save_settings({"merge_close_preview_on_edit": bool(enabled)})


KEYGEN_REVEAL_AUTO_HIDE_CHOICES: tuple[int, ...] = (5, 10, 30)


def get_keygen_reveal_auto_hide_sec() -> int:
    """Keygen Reveal Auto-Hide Intervall in Sekunden (5/10/30) — 1.1.6."""
    raw = load_settings().get(
        "keygen_reveal_auto_hide_sec", DEFAULTS["keygen_reveal_auto_hide_sec"]
    )
    try:
        val = int(raw)
    except (TypeError, ValueError):
        val = int(DEFAULTS["keygen_reveal_auto_hide_sec"])
    if val not in KEYGEN_REVEAL_AUTO_HIDE_CHOICES:
        val = min(KEYGEN_REVEAL_AUTO_HIDE_CHOICES, key=lambda x: abs(x - val))
    return val


def set_keygen_reveal_auto_hide_sec(seconds: int) -> int:
    """Keygen Reveal Auto-Hide speichern; Rückgabe normalisierter Wert — 1.1.6."""
    try:
        val = int(seconds)
    except (TypeError, ValueError):
        val = int(DEFAULTS["keygen_reveal_auto_hide_sec"])
    if val not in KEYGEN_REVEAL_AUTO_HIDE_CHOICES:
        val = min(KEYGEN_REVEAL_AUTO_HIDE_CHOICES, key=lambda x: abs(x - val))
    save_settings({"keygen_reveal_auto_hide_sec": val})
    return val


def get_batch_output_dir() -> Path | None:
    raw = str(load_settings().get("batch_output_dir") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_dir() else None


def set_batch_output_dir(path: str | Path) -> None:
    save_settings({"batch_output_dir": str(path)})


def get_default_open_dir() -> Path | None:
    raw = str(load_settings().get("default_open_dir") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_dir() else None


def set_default_open_dir(path: str | Path) -> None:
    save_settings({"default_open_dir": str(path)})


def get_ui_lang() -> UiLang:
    """UI-Sprache DE/EN/FR/RU/ES/ZH/PT/AR/IT — persistiert — 2.6.19."""
    from instantlensdoc.core.i18n import normalize_lang

    lang = str(load_settings().get("ui_lang", "de") or "de")
    return normalize_lang(lang)  # type: ignore[return-value]


def set_ui_lang(lang: str) -> None:
    """UI-Sprache speichern (9 Sprachen) — 2.6.19."""
    from instantlensdoc.core.i18n import normalize_lang

    save_settings({"ui_lang": normalize_lang(lang)})


def get_export_jpeg_quality() -> int:
    try:
        q = int(load_settings().get("export_jpeg_quality", 85))
    except (TypeError, ValueError):
        q = 85
    return max(10, min(100, q))


def set_export_jpeg_quality(quality: int) -> int:
    """JPEG-Qualität für Seiten→Bilder / Export speichern (10–100) — 1.5.2."""
    try:
        q = int(quality)
    except (TypeError, ValueError):
        q = 85
    q = max(10, min(100, q))
    save_settings({"export_jpeg_quality": q})
    return q


def get_export_pdf_page() -> str:
    name = str(load_settings().get("export_pdf_page", "A4") or "A4")
    return name


def get_export_image_max_edge() -> int:
    try:
        v = int(load_settings().get("export_image_max_edge", 2000))
    except (TypeError, ValueError):
        v = 2000
    return max(200, min(8000, v))


def get_update_check_on_start() -> bool:
    return bool(load_settings().get("update_check_on_start", False))


def set_update_check_on_start(enabled: bool) -> None:
    save_settings({"update_check_on_start": bool(enabled)})


def get_telemetry_opt_in() -> bool:
    """Opt-in „anonym Diagnostik (lokal)“ — Default False — 2.6.26."""
    return bool(load_settings().get("telemetry_opt_in", False))


def set_telemetry_opt_in(enabled: bool) -> None:
    """Opt-in speichern; bei Aktivierung lokales Diagnostik-Log (kein Netzwerk)."""
    save_settings({"telemetry_opt_in": bool(enabled)})
    try:
        from instantlensdoc.core.telemetry import report_anonymous_usage

        report_anonymous_usage(
            "settings.telemetry_opt_in",
            enabled=bool(enabled),
            requested=bool(enabled),
        )
    except Exception:
        pass


def get_stylus_pressure_enabled() -> bool:
    return bool(load_settings().get("stylus_pressure_enabled", True))


def set_stylus_pressure_enabled(enabled: bool) -> None:
    save_settings({"stylus_pressure_enabled": bool(enabled)})


def get_stylus_palm_rejection() -> bool:
    return bool(load_settings().get("stylus_palm_rejection", True))


def set_stylus_palm_rejection(enabled: bool) -> None:
    save_settings({"stylus_palm_rejection": bool(enabled)})


COMMAND_PALETTE_RECENT_MAX = 10  # Default; Settings 5/10/20 — 2.3.2
COMMAND_PALETTE_RECENT_CHOICES = (5, 10, 20)
COMMAND_PALETTE_PIN_MAX = 5  # Default; Settings 3/5/10 — 2.3.3
COMMAND_PALETTE_PIN_CHOICES = (3, 5, 10)


def get_command_palette_recent_max() -> int:
    """Anzahl Recent-Einträge in der Command Palette (5/10/20) — 2.3.2."""
    raw = load_settings().get("command_palette_recent_max", COMMAND_PALETTE_RECENT_MAX)
    try:
        n = int(raw)
    except (TypeError, ValueError):
        n = COMMAND_PALETTE_RECENT_MAX
    if n not in COMMAND_PALETTE_RECENT_CHOICES:
        # nächste erlaubte Stufe
        n = min(COMMAND_PALETTE_RECENT_CHOICES, key=lambda x: abs(x - n))
    return n


def set_command_palette_recent_max(n: int) -> int:
    """Recent-Anzahl setzen (5/10/20) und Liste trimmen — 2.3.2."""
    try:
        val = int(n)
    except (TypeError, ValueError):
        val = COMMAND_PALETTE_RECENT_MAX
    if val not in COMMAND_PALETTE_RECENT_CHOICES:
        val = min(COMMAND_PALETTE_RECENT_CHOICES, key=lambda x: abs(x - val))
    save_settings({"command_palette_recent_max": val})
    # Liste auf neues Max trimmen
    cur = get_command_palette_recent(max_items=val)
    save_settings({"command_palette_recent": cur})
    return val


def get_command_palette_pin_max() -> int:
    """Max. Anzahl angehefteter Palette-Befehle (3/5/10) — 2.3.3."""
    raw = load_settings().get("command_palette_pin_max", COMMAND_PALETTE_PIN_MAX)
    try:
        n = int(raw)
    except (TypeError, ValueError):
        n = COMMAND_PALETTE_PIN_MAX
    if n not in COMMAND_PALETTE_PIN_CHOICES:
        n = min(COMMAND_PALETTE_PIN_CHOICES, key=lambda x: abs(x - n))
    return n


def set_command_palette_pin_max(n: int) -> int:
    """Pin-Max setzen (3/5/10) und Liste trimmen — 2.3.3."""
    try:
        val = int(n)
    except (TypeError, ValueError):
        val = COMMAND_PALETTE_PIN_MAX
    if val not in COMMAND_PALETTE_PIN_CHOICES:
        val = min(COMMAND_PALETTE_PIN_CHOICES, key=lambda x: abs(x - val))
    save_settings({"command_palette_pin_max": val})
    cur = get_command_palette_pinned()
    if len(cur) > val:
        set_command_palette_pinned(cur[:val])
    return val


def get_command_palette_pinned() -> list[str]:
    """Angeheftete Command-Palette-Befehls-IDs (persistiert, max Pins) — 2.3.2/2.3.3."""
    raw = load_settings().get("command_palette_pinned") or []
    limit = get_command_palette_pin_max()
    out: list[str] = []
    if isinstance(raw, list):
        for x in raw:
            s = str(x or "").strip()
            if s and s not in out:
                out.append(s)
            if len(out) >= limit:
                break
    return out


def set_command_palette_pinned(ids: list[str] | tuple[str, ...]) -> list[str]:
    """Pinned-Liste setzen (Reihenfolge behalten, max Pins) — 2.3.2/2.3.3."""
    limit = get_command_palette_pin_max()
    out: list[str] = []
    for x in ids or []:
        s = str(x or "").strip()
        if s and s not in out:
            out.append(s)
        if len(out) >= limit:
            break
    save_settings({"command_palette_pinned": out})
    return out


def toggle_command_palette_pin(
    cmd_id: str, *, replace_oldest: bool = False
) -> bool | None:
    """
    Pin umschalten (Unpin wenn gesetzt).

    Returns:
      True  — jetzt angeheftet
      False — jetzt unpinned / leer
      None  — Pin-Limit erreicht und ``replace_oldest=False`` (nichts geändert)

    Bei Limit + ``replace_oldest=True``: ältesten Pin (Ende) ersetzen — 2.3.4.
    """
    cid = str(cmd_id or "").strip()
    if not cid:
        return False
    pinned = get_command_palette_pinned()
    if cid in pinned:
        pinned = [x for x in pinned if x != cid]
        set_command_palette_pinned(pinned)
        return False
    limit = get_command_palette_pin_max()
    others = [x for x in pinned if x != cid]
    if len(others) >= limit and not replace_oldest:
        return None
    # Neu anheften am Anfang; bei Max ältesten (Ende) verdrängen — 2.3.4
    pinned = [cid] + others
    pinned = pinned[:limit]
    set_command_palette_pinned(pinned)
    return True


def command_palette_pins_at_limit() -> bool:
    """True wenn aktuelle Pin-Anzahl das Max erreicht hat — 2.3.4."""
    return len(get_command_palette_pinned()) >= get_command_palette_pin_max()


def get_command_palette_recent(
    max_items: int | None = None,
) -> list[str]:
    """Letzte Command-Palette-Befehls-IDs (neueste zuerst) — 2.3.1/2.3.2."""
    limit = get_command_palette_recent_max() if max_items is None else max(1, int(max_items))
    raw = load_settings().get("command_palette_recent") or []
    out: list[str] = []
    if isinstance(raw, list):
        for x in raw:
            s = str(x or "").strip()
            if s and s not in out:
                out.append(s)
            if len(out) >= limit:
                break
    return out


def push_command_palette_recent(
    cmd_id: str, *, max_items: int | None = None
) -> list[str]:
    """Befehl in Recent-Liste nach vorne schieben — 2.3.1/2.3.2."""
    limit = get_command_palette_recent_max() if max_items is None else max(1, int(max_items))
    cid = str(cmd_id or "").strip()
    if not cid:
        return get_command_palette_recent(max_items=limit)
    prev = [x for x in get_command_palette_recent(max_items=limit * 2) if x != cid]
    nxt = [cid] + prev
    nxt = nxt[:limit]
    save_settings({"command_palette_recent": nxt})
    return nxt


def get_compress_open_after() -> bool:
    """Nach erfolgreicher PDF-Kompression neues File öffnen — Settings Toggle — 2.3.2/2.3.3."""
    return bool(load_settings().get("compress_open_after", False))


def set_compress_open_after(enabled: bool) -> None:
    """Toggle merken (Dialog + Einstellungen) — 2.3.3."""
    save_settings({"compress_open_after": bool(enabled)})


DEFAULT_LINKS_TXT_FILENAME_TEMPLATE = "{stem}_links.txt"
LINKS_TXT_KNOWN_PLACEHOLDERS = frozenset({"stem", "date"})
_LINKS_TXT_ANY_PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")


def get_links_txt_utf8_bom() -> bool:
    """Links-TXT mit UTF-8-BOM schreiben — 2.3.3."""
    return bool(load_settings().get("links_txt_utf8_bom", True))


def set_links_txt_utf8_bom(enabled: bool) -> bool:
    v = bool(enabled)
    save_settings({"links_txt_utf8_bom": v})
    return v


def get_last_links_txt_dir() -> Path | None:
    """Zuletzt genutzter Zielordner für Links-TXT — 2.3.3."""
    raw = str(load_settings().get("last_links_txt_dir", "") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_dir() else (p.parent if p.parent.is_dir() else None)


def set_last_links_txt_dir(path: str | Path) -> None:
    p = Path(path)
    if p.is_file():
        p = p.parent
    save_settings({"last_links_txt_dir": str(p)})


def get_links_txt_filename_template() -> str:
    """Dateiname-Template Links-TXT, Default ``{stem}_links.txt`` — 2.3.3."""
    raw = str(
        load_settings().get(
            "links_txt_filename_template",
            DEFAULTS.get(
                "links_txt_filename_template",
                DEFAULT_LINKS_TXT_FILENAME_TEMPLATE,
            ),
        )
        or ""
    ).strip()
    if not raw:
        return DEFAULT_LINKS_TXT_FILENAME_TEMPLATE
    raw = raw.replace("/", "_").replace("\\", "_")
    if not raw.lower().endswith(".txt"):
        raw = raw + ".txt"
    return raw


def set_links_txt_filename_template(template: str) -> str:
    """Links-TXT-Template speichern — 2.3.3."""
    raw = str(template or "").strip() or DEFAULT_LINKS_TXT_FILENAME_TEMPLATE
    raw = raw.replace("/", "_").replace("\\", "_")
    if not raw.lower().endswith(".txt"):
        raw = raw + ".txt"
    save_settings({"links_txt_filename_template": raw})
    return raw


def find_invalid_links_txt_placeholders(template: str) -> list[str]:
    """Unbekannte Platzhalter im Links-TXT-Template — 2.3.4."""
    seen: set[str] = set()
    out: list[str] = []
    for name in _LINKS_TXT_ANY_PLACEHOLDER_RE.findall(str(template or "")):
        key = name.strip()
        if not key or key in LINKS_TXT_KNOWN_PLACEHOLDERS or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def highlight_links_txt_template_html(template: str) -> str:
    """Template als HTML; ungültige Platzhalter rot — 2.3.4."""
    import html as _html

    raw = str(template or "")
    parts: list[str] = []
    last = 0
    for m in _LINKS_TXT_ANY_PLACEHOLDER_RE.finditer(raw):
        parts.append(_html.escape(raw[last : m.start()]))
        name = m.group(1).strip()
        token = _html.escape(m.group(0))
        if name and name not in LINKS_TXT_KNOWN_PLACEHOLDERS:
            parts.append(
                f'<span style="color:#c62828;font-weight:600">{token}</span>'
            )
        else:
            parts.append(token)
        last = m.end()
    parts.append(_html.escape(raw[last:]))
    return "".join(parts) or _html.escape(raw)


def format_links_txt_filename(
    stem: str,
    *,
    template: str | None = None,
    date: str | None = None,
) -> str:
    """
    Links-TXT-Dateiname aus Template.
    Platzhalter: ``{stem}``, ``{date}`` (YYYY-MM-DD).
    Default ``{stem}_links.txt`` — 2.3.3/2.3.4.
    """
    from datetime import date as _date

    tpl = template if template is not None else get_links_txt_filename_template()
    stem_s = (stem or "links").strip() or "links"
    date_s = (date if date is not None else _date.today().isoformat()).strip()
    name = str(tpl or DEFAULT_LINKS_TXT_FILENAME_TEMPLATE).replace(
        "{stem}", stem_s
    ).replace("{date}", date_s)
    name = name.replace("/", "_").replace("\\", "_")
    if not name.lower().endswith(".txt"):
        name = name + ".txt"
    return name or f"{stem_s}_links.txt"


def get_update_dismissed_version() -> str:
    """Version, für die der Update-Hinweis verworfen wurde (bis nächste) — 1.7.1."""
    return str(load_settings().get("update_dismissed_version") or "").strip()


def set_update_dismissed_version(version: str) -> None:
    save_settings({"update_dismissed_version": str(version or "").strip()})


def clear_update_dismissed_version() -> None:
    save_settings({"update_dismissed_version": ""})


def get_presentation_hide_annotations() -> bool:
    """Präsentationsmodus: Annotation-Overlay optional ausblenden — 1.7.0."""
    return bool(load_settings().get("presentation_hide_annotations", True))


def set_presentation_hide_annotations(enabled: bool) -> None:
    save_settings({"presentation_hide_annotations": bool(enabled)})


# Präsentation Auto-Advance: aus oder 3/5/10/30 s — 1.7.2
PRESENTATION_AUTO_ADVANCE_CHOICES = (0, 3, 5, 10, 30)
PRESENTATION_AUTO_ADVANCE_DEFAULT = 0


def normalize_presentation_auto_advance_sec(seconds: int | float | str | None) -> int:
    """Intervall auf 0|3|5|10|30 snappen (0 bleibt aus; sonst nächster erlaubter Wert)."""
    try:
        v = int(seconds)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return PRESENTATION_AUTO_ADVANCE_DEFAULT
    if v <= 0:
        return 0
    if v in PRESENTATION_AUTO_ADVANCE_CHOICES:
        return v
    best = 3
    best_dist = abs(best - v)
    for choice in PRESENTATION_AUTO_ADVANCE_CHOICES:
        if choice == 0:
            continue
        d = abs(choice - v)
        if d < best_dist or (d == best_dist and choice > best):
            best = choice
            best_dist = d
    return best


def get_presentation_auto_advance_sec() -> int:
    """Auto-Advance-Intervall in Sekunden (0 = aus; 3/5/10/30) — 1.7.2."""
    try:
        v = int(load_settings().get("presentation_auto_advance_sec", 0))
    except (TypeError, ValueError):
        v = 0
    return normalize_presentation_auto_advance_sec(v)


def set_presentation_auto_advance_sec(sec: int) -> int:
    """Auto-Advance setzen (0|3|5|10|30). Rückgabe: gespeicherter Wert — 1.7.2."""
    v = normalize_presentation_auto_advance_sec(sec)
    save_settings({"presentation_auto_advance_sec": v})
    return v


def get_presentation_black_background() -> bool:
    """Präsentation: schwarzer Hintergrund — 1.7.1."""
    return bool(load_settings().get("presentation_black_background", True))


def set_presentation_black_background(enabled: bool) -> None:
    save_settings({"presentation_black_background": bool(enabled)})


def get_presentation_show_page_number() -> bool:
    """Präsentation: Seitennummer-Overlay anzeigen — 1.7.1."""
    return bool(load_settings().get("presentation_show_page_number", True))


def set_presentation_show_page_number(enabled: bool) -> None:
    save_settings({"presentation_show_page_number": bool(enabled)})


# Countdown-Overlay Position: unten-rechts | mitte — 1.7.3
PRESENTATION_COUNTDOWN_POSITION_CHOICES = ("bottom-right", "center")
PRESENTATION_COUNTDOWN_POSITION_DEFAULT = "bottom-right"


def normalize_presentation_countdown_position(position: str | None) -> str:
    raw = str(position or "").strip().lower()
    if raw in ("center", "mitte", "middle", "centre"):
        return "center"
    if raw in ("bottom-right", "bottom_right", "unten-rechts", "unten_rechts", "br"):
        return "bottom-right"
    return PRESENTATION_COUNTDOWN_POSITION_DEFAULT


def get_presentation_countdown_position() -> str:
    """Countdown-Overlay Position: bottom-right | center — 1.7.3."""
    return normalize_presentation_countdown_position(
        load_settings().get("presentation_countdown_position")
    )


def set_presentation_countdown_position(position: str) -> str:
    key = normalize_presentation_countdown_position(position)
    save_settings({"presentation_countdown_position": key})
    return key


# Countdown-Overlay Farbe: hell | dunkel — 1.7.3
PRESENTATION_COUNTDOWN_COLOR_CHOICES = ("dark", "light")
PRESENTATION_COUNTDOWN_COLOR_DEFAULT = "dark"


def normalize_presentation_countdown_color(color: str | None) -> str:
    raw = str(color or "").strip().lower()
    if raw in ("light", "hell", "white", "weiss", "weiß"):
        return "light"
    if raw in ("dark", "dunkel", "black", "schwarz"):
        return "dark"
    return PRESENTATION_COUNTDOWN_COLOR_DEFAULT


def get_presentation_countdown_color() -> str:
    """Countdown-Overlay Farbe: dark | light — 1.7.3."""
    return normalize_presentation_countdown_color(
        load_settings().get("presentation_countdown_color")
    )


def set_presentation_countdown_color(color: str) -> str:
    key = normalize_presentation_countdown_color(color)
    save_settings({"presentation_countdown_color": key})
    return key


def reset_presentation_countdown_defaults() -> tuple[str, str]:
    """Countdown Position+Farbe auf Defaults; (pos, color) — 1.7.4."""
    pos = set_presentation_countdown_position(PRESENTATION_COUNTDOWN_POSITION_DEFAULT)
    color = set_presentation_countdown_color(PRESENTATION_COUNTDOWN_COLOR_DEFAULT)
    return pos, color


def get_last_update_check_at() -> str:
    """ISO-Zeitstempel des letzten Update-Checks (leer = nie) — 1.7.3."""
    return str(load_settings().get("last_update_check_at") or "").strip()


def set_last_update_check_at(iso_ts: str) -> None:
    save_settings({"last_update_check_at": str(iso_ts or "").strip()})


def get_favorites_bar_visible() -> bool:
    """Globale Favoriten-/Lesezeichen-Leiste sichtbar — 1.7.0."""
    return bool(load_settings().get("favorites_bar_visible", True))


def set_favorites_bar_visible(visible: bool) -> None:
    save_settings({"favorites_bar_visible": bool(visible)})


def get_text_pdf_font_size() -> float:
    """Text→PDF Schriftgröße in pt — 1.7.1."""
    try:
        v = float(load_settings().get("text_pdf_font_size", 11.0))
    except (TypeError, ValueError):
        v = 11.0
    return max(6.0, min(36.0, v))


def set_text_pdf_font_size(size: float) -> None:
    try:
        v = float(size)
    except (TypeError, ValueError):
        v = 11.0
    save_settings({"text_pdf_font_size": max(6.0, min(36.0, v))})


def get_text_pdf_margin() -> float:
    """Text→PDF Rand in pt — 1.7.1."""
    try:
        v = float(load_settings().get("text_pdf_margin", 50.0))
    except (TypeError, ValueError):
        v = 50.0
    return max(10.0, min(120.0, v))


def set_text_pdf_margin(margin: float) -> None:
    try:
        v = float(margin)
    except (TypeError, ValueError):
        v = 50.0
    save_settings({"text_pdf_margin": max(10.0, min(120.0, v))})


def get_last_text_pdf_dir() -> Path | None:
    """Letzter Zielordner für Text → PDF — 1.7.2."""
    raw = str(load_settings().get("last_text_pdf_dir") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_dir() else None


def set_last_text_pdf_dir(path: str | Path) -> None:
    """Text→PDF Zielordner merken — 1.7.2."""
    p = Path(path)
    if p.is_file():
        p = p.parent
    save_settings({"last_text_pdf_dir": str(p)})


def get_text_pdf_open_after() -> bool:
    """Nach Text→PDF Export optional öffnen — 1.7.2."""
    return bool(load_settings().get("text_pdf_open_after", False))


def set_text_pdf_open_after(enabled: bool) -> None:
    save_settings({"text_pdf_open_after": bool(enabled)})


def get_last_export_dir() -> Path | None:
    raw = str(load_settings().get("last_export_dir") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_dir() else None


def set_last_export_dir(path: str | Path) -> None:
    p = Path(path)
    if p.is_file():
        p = p.parent
    save_settings({"last_export_dir": str(p)})


DEFAULT_ANN_EXPORT_FILENAME_TEMPLATE = "{stem}_ann.json"


def get_last_ann_export_dir() -> Path | None:
    """Letzter Zielordner für Annotation-JSON-Export — 1.2.1."""
    raw = str(load_settings().get("last_ann_export_dir") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_dir() else None


def set_last_ann_export_dir(path: str | Path) -> None:
    """Zielordner für Ann.-Export merken — 1.2.1."""
    p = Path(path)
    if p.is_file():
        p = p.parent
    save_settings({"last_ann_export_dir": str(p)})


ANN_EXPORT_KNOWN_PLACEHOLDERS = frozenset({"stem", "page", "date"})


def find_invalid_ann_export_placeholders(template: str) -> list[str]:
    """
    Unbekannte ``{…}``-Platzhalter im Ann.-Export-Template (Reihenfolge, unique).
    Bekannt: stem, page, date. — 1.2.3
    """
    import re

    seen: set[str] = set()
    out: list[str] = []
    for name in re.findall(r"\{([^{}]+)\}", str(template or "")):
        key = name.strip()
        if not key or key in ANN_EXPORT_KNOWN_PLACEHOLDERS or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def highlight_ann_export_template_html(template: str) -> str:
    """
    Template als HTML; ungültige Platzhalter rot markiert. — 1.2.3
    """
    import html as _html
    import re

    raw = str(template or "")
    parts: list[str] = []
    last = 0
    for m in re.finditer(r"\{([^{}]+)\}", raw):
        parts.append(_html.escape(raw[last : m.start()]))
        name = m.group(1).strip()
        token = _html.escape(m.group(0))
        if name and name not in ANN_EXPORT_KNOWN_PLACEHOLDERS:
            parts.append(f'<span style="color:#c62828;font-weight:600">{token}</span>')
        else:
            parts.append(token)
        last = m.end()
    parts.append(_html.escape(raw[last:]))
    return "".join(parts) or _html.escape(raw)


def get_split_open_tabs() -> bool:
    """PDF-Split: erzeugte Dateien in Tabs öffnen — 1.2.3."""
    return bool(load_settings().get("split_open_tabs", DEFAULTS["split_open_tabs"]))


def set_split_open_tabs(enabled: bool) -> None:
    """Persistenz Checkbox „in Tabs öffnen“ — 1.2.3."""
    save_settings({"split_open_tabs": bool(enabled)})


def get_text_diff_sync_scroll() -> bool:
    """Text-Diff: Sync-Scroll Side-by-Side Default — 1.2.4."""
    return bool(
        load_settings().get("text_diff_sync_scroll", DEFAULTS["text_diff_sync_scroll"])
    )


def set_text_diff_sync_scroll(enabled: bool) -> None:
    """Persistenz Text-Diff Sync-Scroll — 1.2.4."""
    save_settings({"text_diff_sync_scroll": bool(enabled)})


def get_text_diff_ignore_whitespace() -> bool:
    """Text-Diff: Ignore-Whitespace Default — 1.2.4."""
    return bool(
        load_settings().get(
            "text_diff_ignore_whitespace", DEFAULTS["text_diff_ignore_whitespace"]
        )
    )


def set_text_diff_ignore_whitespace(enabled: bool) -> None:
    """Persistenz Text-Diff Ignore-Whitespace — 1.2.4."""
    save_settings({"text_diff_ignore_whitespace": bool(enabled)})


def get_text_diff_wrap_around() -> bool:
    """Text-Diff: Wrap-around bei F7/Shift+F7 — 1.2.6."""
    return bool(
        load_settings().get(
            "text_diff_wrap_around", DEFAULTS["text_diff_wrap_around"]
        )
    )


def set_text_diff_wrap_around(enabled: bool) -> None:
    """Persistenz Text-Diff Wrap-around — 1.2.6."""
    save_settings({"text_diff_wrap_around": bool(enabled)})


WRAP_BLINK_KURZ = "kurz"
WRAP_BLINK_MITTEL = "mittel"
WRAP_BLINK_LANG = "lang"
WRAP_BLINK_DURATION_DEFAULT = WRAP_BLINK_KURZ
WRAP_BLINK_DURATION_CHOICES = (
    (WRAP_BLINK_KURZ, "Kurz"),
    (WRAP_BLINK_MITTEL, "Mittel"),
    (WRAP_BLINK_LANG, "Lang"),
)
WRAP_BLINK_MS = {
    WRAP_BLINK_KURZ: 350,
    WRAP_BLINK_MITTEL: 700,
    WRAP_BLINK_LANG: 1200,
}


def get_text_diff_wrap_blink_duration() -> str:
    """Wrap-Blink Dauer: kurz|mittel|lang — 1.2.9."""
    raw = str(
        load_settings().get(
            "text_diff_wrap_blink_duration",
            DEFAULTS["text_diff_wrap_blink_duration"],
        )
        or WRAP_BLINK_DURATION_DEFAULT
    ).strip().lower()
    if raw in ("lang", "long", "lng"):
        return WRAP_BLINK_LANG
    if raw in ("mittel", "medium", "med"):
        return WRAP_BLINK_MITTEL
    return WRAP_BLINK_KURZ


def set_text_diff_wrap_blink_duration(mode: str) -> str:
    """Persistenz Wrap-Blink Dauer — 1.2.9."""
    raw = str(mode or "").strip().lower()
    if raw in ("lang", "long", "lng"):
        val = WRAP_BLINK_LANG
    elif raw in ("mittel", "medium", "med"):
        val = WRAP_BLINK_MITTEL
    else:
        val = WRAP_BLINK_KURZ
    save_settings({"text_diff_wrap_blink_duration": val})
    return val


def get_text_diff_wrap_blink_ms() -> int:
    """Wrap-Blink Dauer in ms (350 kurz / 700 mittel / 1200 lang) — 1.2.9."""
    return int(WRAP_BLINK_MS.get(get_text_diff_wrap_blink_duration(), 350))


def get_text_diff_wrap_blink_sound() -> bool:
    """Wrap-Blink System-Beep (True) vs. stumm (False) — 1.2.9."""
    return bool(
        load_settings().get(
            "text_diff_wrap_blink_sound",
            DEFAULTS["text_diff_wrap_blink_sound"],
        )
    )


def set_text_diff_wrap_blink_sound(enabled: bool) -> None:
    """Persistenz Wrap-Blink Sound (System-Beep vs. stumm) — 1.2.9."""
    save_settings({"text_diff_wrap_blink_sound": bool(enabled)})


PDF_COMPARE_DIFF_THRESHOLD_DEFAULT = 18
PDF_COMPARE_DIFF_THRESHOLD_MIN = 0
PDF_COMPARE_DIFF_THRESHOLD_MAX = 255


def get_pdf_compare_diff_threshold() -> int:
    """Raster-Diff Pixel-Schwellwert (0–255) — 1.4.1."""
    raw = load_settings().get(
        "pdf_compare_diff_threshold", DEFAULTS["pdf_compare_diff_threshold"]
    )
    try:
        val = int(raw)
    except (TypeError, ValueError):
        val = PDF_COMPARE_DIFF_THRESHOLD_DEFAULT
    return max(
        PDF_COMPARE_DIFF_THRESHOLD_MIN,
        min(val, PDF_COMPARE_DIFF_THRESHOLD_MAX),
    )


def set_pdf_compare_diff_threshold(value: int) -> int:
    """Persistenz Raster-Diff-Schwelle — 1.4.1."""
    try:
        val = int(value)
    except (TypeError, ValueError):
        val = PDF_COMPARE_DIFF_THRESHOLD_DEFAULT
    val = max(
        PDF_COMPARE_DIFF_THRESHOLD_MIN,
        min(val, PDF_COMPARE_DIFF_THRESHOLD_MAX),
    )
    save_settings({"pdf_compare_diff_threshold": val})
    return val


def get_pdf_compare_page_sync() -> bool:
    """Seitenwahl Sync (True) vs. Entkoppelt (False) — 1.4.1."""
    return bool(
        load_settings().get(
            "pdf_compare_page_sync", DEFAULTS["pdf_compare_page_sync"]
        )
    )


def set_pdf_compare_page_sync(enabled: bool) -> None:
    """Persistenz Seitenwahl Sync/Entkoppelt — 1.4.1."""
    save_settings({"pdf_compare_page_sync": bool(enabled)})


def get_last_pdf_diff_png_dir() -> Path | None:
    """Letzter Zielordner für Diff-PNG-Export — 1.4.2."""
    raw = str(load_settings().get("last_pdf_diff_png_dir") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_dir() else None


def set_last_pdf_diff_png_dir(path: str | Path) -> None:
    """Zielordner Diff-PNG merken — 1.4.2."""
    p = Path(path)
    if p.is_file():
        p = p.parent
    save_settings({"last_pdf_diff_png_dir": str(p)})


DEFAULT_PAGE_IMAGE_FILENAME_TEMPLATE = "{stem}_p{page}"


def get_last_page_image_export_dir() -> Path | None:
    """Letzter Zielordner für Seiten→Bilder-Export — 1.5.1."""
    raw = str(load_settings().get("last_page_image_export_dir") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_dir() else None


def set_last_page_image_export_dir(path: str | Path) -> None:
    """Zielordner Seiten→Bilder merken — 1.5.1."""
    p = Path(path)
    if p.is_file():
        p = p.parent
    save_settings({"last_page_image_export_dir": str(p)})


def get_page_image_filename_template() -> str:
    """Dateiname-Template Seiten→Bilder, Default ``{stem}_p{page}`` — 1.5.1."""
    raw = str(
        load_settings().get(
            "page_image_filename_template",
            DEFAULTS["page_image_filename_template"],
        )
        or ""
    ).strip()
    if not raw:
        return DEFAULT_PAGE_IMAGE_FILENAME_TEMPLATE
    if "{stem}" not in raw:
        raw = "{stem}_" + raw.lstrip("_")
    if "{page}" not in raw:
        raw = raw.rstrip("_") + "_p{page}"
    raw = raw.replace("/", "_").replace("\\", "_")
    return raw


def set_page_image_filename_template(template: str) -> str:
    """Template Seiten→Bilder speichern — 1.5.1."""
    raw = str(template or "").strip() or DEFAULT_PAGE_IMAGE_FILENAME_TEMPLATE
    if "{stem}" not in raw:
        raw = "{stem}_" + raw.lstrip("_")
    if "{page}" not in raw:
        raw = raw.rstrip("_") + "_p{page}"
    raw = raw.replace("/", "_").replace("\\", "_")
    # Extension weglassen — wird je Format gesetzt
    for suf in (".png", ".jpg", ".jpeg"):
        if raw.lower().endswith(suf):
            raw = raw[: -len(suf)]
            break
    save_settings({"page_image_filename_template": raw})
    return raw


def get_last_signature_image() -> Path | None:
    """Zuletzt verwendetes Signatur-Bild — 1.5.1."""
    raw = str(load_settings().get("last_signature_image") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_file() else None


def set_last_signature_image(path: str | Path) -> None:
    """Signatur-Bild-Pfad merken — 1.5.1."""
    p = Path(path)
    if p.is_file():
        save_settings({"last_signature_image": str(p)})


def get_last_signature_size() -> tuple[float, float]:
    """Zuletzt verwendete Signatur-Größe (width, height) — 1.5.1."""
    try:
        w = float(load_settings().get("last_signature_width", 180.0) or 180.0)
    except (TypeError, ValueError):
        w = 180.0
    try:
        h = float(load_settings().get("last_signature_height", 64.0) or 64.0)
    except (TypeError, ValueError):
        h = 64.0
    return max(40.0, min(600.0, w)), max(20.0, min(400.0, h))


def set_last_signature_size(width: float, height: float) -> None:
    """Signatur-Größe merken — 1.5.1."""
    w = max(40.0, min(600.0, float(width)))
    h = max(20.0, min(400.0, float(height)))
    save_settings({"last_signature_width": w, "last_signature_height": h})


def get_last_signature_opacity() -> float:
    """Zuletzt verwendete Signatur-Deckkraft — 1.5.1."""
    try:
        op = float(load_settings().get("last_signature_opacity", 1.0) or 1.0)
    except (TypeError, ValueError):
        op = 1.0
    return max(0.05, min(1.0, op))


def set_last_signature_opacity(opacity: float) -> None:
    """Signatur-Deckkraft merken — 1.5.1."""
    try:
        op = float(opacity)
    except (TypeError, ValueError):
        op = 1.0
    save_settings({"last_signature_opacity": max(0.05, min(1.0, op))})


def get_signature_aspect_lock() -> bool:
    """Aspect-Ratio Lock für Signatur-Bild — 1.5.2."""
    return bool(load_settings().get("signature_aspect_lock", True))


def set_signature_aspect_lock(enabled: bool) -> None:
    """Aspect-Ratio Lock Signatur merken — 1.5.2."""
    save_settings({"signature_aspect_lock": bool(enabled)})


def get_last_signature_preview_zoom() -> float:
    """Zuletzt verwendeter Signatur-Vorschau-Zoom (0.5–3.0), Settings — 1.5.5."""
    try:
        z = float(load_settings().get("last_signature_preview_zoom", 1.0) or 1.0)
    except (TypeError, ValueError):
        z = 1.0
    return max(0.5, min(3.0, z))


def set_last_signature_preview_zoom(zoom: float) -> None:
    """Signatur-Vorschau-Zoom in Settings persistieren — 1.5.5."""
    try:
        z = float(zoom)
    except (TypeError, ValueError):
        z = 1.0
    save_settings({"last_signature_preview_zoom": max(0.5, min(3.0, z))})


def get_meta_backup_on_save() -> bool:
    """Toggle: .ildbak vor Metadaten-Speichern — 1.5.2."""
    return bool(load_settings().get("meta_backup_on_save", True))


def set_meta_backup_on_save(enabled: bool) -> None:
    """Toggle Metadaten-Backup .ildbak speichern — 1.5.2."""
    save_settings({"meta_backup_on_save": bool(enabled)})


def get_last_rename_undo_log() -> Path | None:
    """Pfad des letzten Batch-Rename Undo-Logs (TXT) — 1.4.2/1.4.4."""
    raw = str(load_settings().get("last_rename_undo_log") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    if not p.is_file():
        return None
    try:
        from instantlensdoc.core.batch_rename import is_undo_log_invalidated

        if is_undo_log_invalidated(p):
            return None
    except Exception:
        pass
    return p


def set_last_rename_undo_log(path: str | Path) -> None:
    """Letztes Batch-Rename Undo-Log merken — 1.4.2."""
    save_settings({"last_rename_undo_log": str(Path(path))})


def clear_last_rename_undo_log() -> None:
    """Letztes Batch-Rename Undo-Log aus Settings entfernen — 1.4.4."""
    save_settings({"last_rename_undo_log": ""})


def get_ann_export_filename_template() -> str:
    """Dateiname-Template für Ann.-JSON-Export, z. B. ``{stem}_ann.json`` — 1.2.1."""
    raw = str(
        load_settings().get(
            "ann_export_filename_template",
            DEFAULTS["ann_export_filename_template"],
        )
        or ""
    ).strip()
    if not raw:
        return DEFAULT_ANN_EXPORT_FILENAME_TEMPLATE
    # Pflicht: {stem} und .json-Suffix
    if "{stem}" not in raw:
        raw = "{stem}_" + raw.lstrip("_")
    if not raw.lower().endswith(".json"):
        raw = raw + ".json"
    return raw


def set_ann_export_filename_template(template: str) -> str:
    """Template speichern und normalisieren — 1.2.1."""
    raw = str(template or "").strip() or DEFAULT_ANN_EXPORT_FILENAME_TEMPLATE
    if "{stem}" not in raw:
        raw = "{stem}_" + raw.lstrip("_")
    if not raw.lower().endswith(".json"):
        raw = raw + ".json"
    # Unsichere Pfadzeichen entfernen (nur Dateiname)
    raw = raw.replace("/", "_").replace("\\", "_")
    save_settings({"ann_export_filename_template": raw})
    return raw


def format_ann_export_filename(
    stem: str,
    *,
    page: int | None = None,
    template: str | None = None,
    date: str | None = None,
) -> str:
    """
    Dateiname aus Template bauen.
    Platzhalter: ``{stem}``, optional ``{page}`` (1-basiert),
    ``{date}`` (YYYY-MM-DD). — 1.2.1/1.2.2
    """
    from datetime import date as _date

    tpl = template if template is not None else get_ann_export_filename_template()
    name = str(tpl)
    safe_stem = str(stem or "document").strip() or "document"
    name = name.replace("{stem}", safe_stem)
    date_s = (date if date is not None else _date.today().isoformat()).strip()
    name = name.replace("{date}", date_s)
    if page is not None:
        name = name.replace("{page}", str(int(page)))
    else:
        name = name.replace("{page}", "")
        name = name.replace("__", "_").replace("_.", ".")
    # Leere Doppel-Unterstriche nach fehlendem {page} bereinigen
    while "__" in name:
        name = name.replace("__", "_")
    name = name.replace("_.", ".")
    if not name.lower().endswith(".json"):
        name += ".json"
    return name


DEFAULT_ZOOM_MODE_PERCENT = "percent"
DEFAULT_ZOOM_MODE_FIT_WIDTH = "fit_width"
DEFAULT_ZOOM_MODE_FIT_PAGE = "fit_page"
DEFAULT_ZOOM_MODES = (
    DEFAULT_ZOOM_MODE_PERCENT,
    DEFAULT_ZOOM_MODE_FIT_WIDTH,
    DEFAULT_ZOOM_MODE_FIT_PAGE,
)


def get_default_zoom_percent() -> int:
    try:
        v = int(load_settings().get("default_zoom_percent", 150))
    except (TypeError, ValueError):
        v = 150
    return max(25, min(500, v))


def set_default_zoom_percent(percent: int) -> None:
    save_settings({"default_zoom_percent": max(25, min(500, int(percent)))})


def get_default_zoom_mode() -> str:
    """Standard-Zoom-Modus beim Öffnen: percent | fit_width | fit_page."""
    raw = str(load_settings().get("default_zoom_mode", DEFAULT_ZOOM_MODE_PERCENT) or "")
    raw = raw.strip().lower()
    if raw in DEFAULT_ZOOM_MODES:
        return raw
    return DEFAULT_ZOOM_MODE_PERCENT


def set_default_zoom_mode(mode: str) -> str:
    m = str(mode or DEFAULT_ZOOM_MODE_PERCENT).strip().lower()
    if m not in DEFAULT_ZOOM_MODES:
        m = DEFAULT_ZOOM_MODE_PERCENT
    save_settings({"default_zoom_mode": m})
    return m


def get_default_zoom_scale() -> float:
    return get_default_zoom_percent() / 100.0


# Feste Autosave-Intervalle in Einstellungen — 0.9.7
AUTOSAVE_INTERVAL_CHOICES = (15, 30, 60, 120)
AUTOSAVE_INTERVAL_DEFAULT = 60


def normalize_autosave_interval_sec(seconds: int | float | str | None) -> int:
    """Intervall auf erlaubte Werte 15/30/60/120 s snappen (nächster; bei Gleichstand größer)."""
    try:
        v = int(seconds)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return AUTOSAVE_INTERVAL_DEFAULT
    if v in AUTOSAVE_INTERVAL_CHOICES:
        return v
    best = AUTOSAVE_INTERVAL_DEFAULT
    best_dist = abs(best - v)
    for choice in AUTOSAVE_INTERVAL_CHOICES:
        d = abs(choice - v)
        if d < best_dist or (d == best_dist and choice > best):
            best = choice
            best_dist = d
    return best


def get_autosave_interval_sec() -> int:
    try:
        v = int(load_settings().get("autosave_interval_sec", AUTOSAVE_INTERVAL_DEFAULT))
    except (TypeError, ValueError):
        v = AUTOSAVE_INTERVAL_DEFAULT
    return normalize_autosave_interval_sec(v)


def set_autosave_interval_sec(seconds: int) -> int:
    """Autosave-Intervall setzen (15/30/60/120). Rückgabe: gespeicherter Wert — 0.9.7."""
    v = normalize_autosave_interval_sec(seconds)
    save_settings({"autosave_interval_sec": v})
    return v


def get_autosave_enabled() -> bool:
    """Autosave Ein/Aus (Toggle in Einstellungen) — 0.9.6."""
    return bool(load_settings().get("autosave_enabled", True))


def set_autosave_enabled(enabled: bool) -> None:
    save_settings({"autosave_enabled": bool(enabled)})


AUTOSAVE_BACKUP_MAX_MIN = 1
AUTOSAVE_BACKUP_MAX_MAX = 10
AUTOSAVE_BACKUP_MAX_DEFAULT = 3


def get_autosave_backup_enabled() -> bool:
    """Autosave legt vor Überschreiben eine .ildbak-Kopie an — 0.9.9."""
    return bool(load_settings().get("autosave_backup_enabled", False))


def set_autosave_backup_enabled(enabled: bool) -> None:
    save_settings({"autosave_backup_enabled": bool(enabled)})


def get_autosave_backup_max() -> int:
    """Max. Anzahl rotierender .ildbak-Backups (1–10) — 0.9.9."""
    try:
        v = int(load_settings().get("autosave_backup_max", AUTOSAVE_BACKUP_MAX_DEFAULT))
    except (TypeError, ValueError):
        v = AUTOSAVE_BACKUP_MAX_DEFAULT
    return max(AUTOSAVE_BACKUP_MAX_MIN, min(AUTOSAVE_BACKUP_MAX_MAX, v))


def set_autosave_backup_max(count: int) -> int:
    try:
        v = int(count)
    except (TypeError, ValueError):
        v = AUTOSAVE_BACKUP_MAX_DEFAULT
    v = max(AUTOSAVE_BACKUP_MAX_MIN, min(AUTOSAVE_BACKUP_MAX_MAX, v))
    save_settings({"autosave_backup_max": v})
    return v


def get_ann_highlight_color() -> str:
    c = str(load_settings().get("ann_highlight_color") or DEFAULTS["ann_highlight_color"]).strip()
    return c if c.startswith("#") and len(c) >= 4 else DEFAULTS["ann_highlight_color"]


def set_ann_highlight_color(color: str) -> None:
    c = (color or "").strip() or DEFAULTS["ann_highlight_color"]
    if not c.startswith("#"):
        c = "#" + c
    save_settings({"ann_highlight_color": c})


def get_ann_pen_color() -> str:
    c = str(load_settings().get("ann_pen_color") or DEFAULTS["ann_pen_color"]).strip()
    return c if c.startswith("#") and len(c) >= 4 else DEFAULTS["ann_pen_color"]


def set_ann_pen_color(color: str) -> None:
    c = (color or "").strip() or DEFAULTS["ann_pen_color"]
    if not c.startswith("#"):
        c = "#" + c
    save_settings({"ann_pen_color": c})


def get_ann_note_color() -> str:
    c = str(load_settings().get("ann_note_color") or DEFAULTS["ann_note_color"]).strip()
    return c if c.startswith("#") and len(c) >= 4 else DEFAULTS["ann_note_color"]


def set_ann_note_color(color: str) -> None:
    c = (color or "").strip() or DEFAULTS["ann_note_color"]
    if not c.startswith("#"):
        c = "#" + c
    save_settings({"ann_note_color": c})


def get_pdf_two_page_spread() -> bool:
    return bool(load_settings().get("pdf_two_page_spread", False))


def set_pdf_two_page_spread(enabled: bool) -> None:
    save_settings({"pdf_two_page_spread": bool(enabled)})


def get_pdf_book_layout() -> bool:
    """Buch-Layout: Spread + Cover-Seite allein — 2.6.19."""
    return bool(load_settings().get("pdf_book_layout", False))


def set_pdf_book_layout(enabled: bool) -> None:
    save_settings({"pdf_book_layout": bool(enabled)})


def get_pdf_page_by_page() -> bool:
    """Seite-für-Seite-Scroll: Mausrad blättert Seiten — 2.6.19."""
    return bool(load_settings().get("pdf_page_by_page", False))


def set_pdf_page_by_page(enabled: bool) -> None:
    save_settings({"pdf_page_by_page": bool(enabled)})


def get_doc_tabs_visible() -> bool:
    """Horizontale Dokument-Tabs sichtbar — 2.6.19."""
    return bool(load_settings().get("doc_tabs_visible", True))


def set_doc_tabs_visible(enabled: bool) -> None:
    save_settings({"doc_tabs_visible": bool(enabled)})


def get_ribbon_visible() -> bool:
    """Ribbon-Chrome sichtbar (partiell) — 2.6.19."""
    return bool(load_settings().get("ribbon_visible", True))


def set_ribbon_visible(enabled: bool) -> None:
    save_settings({"ribbon_visible": bool(enabled)})


def get_pdf_continuous_scroll() -> bool:
    return bool(load_settings().get("pdf_continuous_scroll", False))


def set_pdf_continuous_scroll(enabled: bool) -> None:
    save_settings({"pdf_continuous_scroll": bool(enabled)})


def get_editor_bracket_match() -> bool:
    return bool(load_settings().get("editor_bracket_match", True))


def set_editor_bracket_match(enabled: bool) -> None:
    save_settings({"editor_bracket_match": bool(enabled)})


def get_editor_bracket_auto_close() -> bool:
    """Klammern/Anführungszeichen beim Tippen automatisch schließen."""
    return bool(load_settings().get("editor_bracket_auto_close", True))


def set_editor_bracket_auto_close(enabled: bool) -> None:
    save_settings({"editor_bracket_auto_close": bool(enabled)})


RECENT_FILES_MAX_DEFAULT = 12
RECENT_FILES_MAX_MIN = 3
RECENT_FILES_MAX_MAX = 50


def get_recent_files_max() -> int:
    """Max. Anzahl zuletzt geöffneter Dateien (3–50, Standard 12)."""
    try:
        n = int(load_settings().get("recent_files_max", RECENT_FILES_MAX_DEFAULT))
    except (TypeError, ValueError):
        n = RECENT_FILES_MAX_DEFAULT
    return max(RECENT_FILES_MAX_MIN, min(RECENT_FILES_MAX_MAX, n))


def set_recent_files_max(count: int) -> int:
    """Max. Anzahl setzen und Recent-Liste ggf. kürzen. Rückgabe: gespeicherter Wert."""
    try:
        n = int(count)
    except (TypeError, ValueError):
        n = RECENT_FILES_MAX_DEFAULT
    n = max(RECENT_FILES_MAX_MIN, min(RECENT_FILES_MAX_MAX, n))
    save_settings({"recent_files_max": n})
    try:
        from instantlensdoc.core import recent as recent_mod

        recent_mod.trim_recent_to_max(n)
    except Exception:
        pass
    return n


TagCloudSort = Literal["freq", "az"]
TAG_CLOUD_SORT_FREQ = "freq"
TAG_CLOUD_SORT_AZ = "az"


def get_tag_cloud_sort() -> TagCloudSort:
    """Tag-Cloud-Sortierung: Häufigkeit (freq) oder A–Z (az)."""
    raw = str(load_settings().get("tag_cloud_sort", TAG_CLOUD_SORT_FREQ) or "").strip().lower()
    if raw in ("az", "a-z", "alpha", "name"):
        return TAG_CLOUD_SORT_AZ
    return TAG_CLOUD_SORT_FREQ


def set_tag_cloud_sort(mode: str) -> TagCloudSort:
    """Tag-Cloud-Sortierung speichern. Rückgabe: normalisierter Modus."""
    raw = str(mode or "").strip().lower()
    value: TagCloudSort = (
        TAG_CLOUD_SORT_AZ if raw in ("az", "a-z", "alpha", "name") else TAG_CLOUD_SORT_FREQ
    )
    save_settings({"tag_cloud_sort": value})
    return value


ANN_FILTER_PRESETS_MAX = 20


def _normalize_ann_filter_preset(raw: object) -> dict | None:
    """Filter-Preset: name + Typ/Farbe/Tags/Seite/Suche/Regex."""
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or "").strip()
    if not name:
        return None
    tags_raw = raw.get("tags") or []
    tags: list[str] = []
    if isinstance(tags_raw, str):
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
    elif isinstance(tags_raw, (list, tuple)):
        for t in tags_raw:
            s = str(t or "").strip()
            if s and s not in tags:
                tags.append(s)
    color = str(raw.get("color") or "").strip()
    if color and not color.startswith("#"):
        color = "#" + color
    return {
        "name": name,
        "type": str(raw.get("type") or "").strip(),
        "color": color,
        "tags": tags,
        "current_page": bool(raw.get("current_page", False)),
        "search": str(raw.get("search") or ""),
        "regex": bool(raw.get("regex", False)),
    }


def get_ann_filter_presets() -> list[dict]:
    """Gespeicherte Annotations-Filter-Presets."""
    raw = load_settings().get("ann_filter_presets") or []
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    seen: set[str] = set()
    for item in raw:
        p = _normalize_ann_filter_preset(item)
        if not p:
            continue
        key = str(p["name"]).casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
        if len(out) >= ANN_FILTER_PRESETS_MAX:
            break
    return out


def get_ann_filter_preset(name: str) -> dict | None:
    want = (name or "").strip().casefold()
    if not want:
        return None
    for p in get_ann_filter_presets():
        if str(p["name"]).casefold() == want:
            return dict(p)
    return None


def save_ann_filter_preset(
    name: str,
    *,
    type: str = "",
    color: str = "",
    tags: list[str] | None = None,
    current_page: bool = False,
    search: str = "",
    regex: bool = False,
    state: dict | None = None,
) -> dict:
    """
    Filter-Preset speichern/überschreiben (gleicher Name → Update).
    state: optional vollständiges Dict (überschreibt Einzelparameter).
    """
    if isinstance(state, dict):
        type = str(state.get("type") if state.get("type") is not None else type)
        color = str(state.get("color") if state.get("color") is not None else color)
        tags = state.get("tags") if state.get("tags") is not None else tags
        current_page = bool(
            state.get("current_page")
            if state.get("current_page") is not None
            else current_page
        )
        search = str(state.get("search") if state.get("search") is not None else search)
        regex = bool(state.get("regex") if state.get("regex") is not None else regex)
        if not name:
            name = str(state.get("name") or "")
    preset = _normalize_ann_filter_preset(
        {
            "name": name,
            "type": type,
            "color": color,
            "tags": tags or [],
            "current_page": current_page,
            "search": search,
            "regex": regex,
        }
    )
    if preset is None:
        raise ValueError("Preset-Name fehlt")
    presets = [
        p
        for p in get_ann_filter_presets()
        if str(p["name"]).casefold() != str(preset["name"]).casefold()
    ]
    presets.insert(0, preset)
    presets = presets[:ANN_FILTER_PRESETS_MAX]
    save_settings({"ann_filter_presets": presets})
    return dict(preset)


def delete_ann_filter_preset(name: str) -> bool:
    want = (name or "").strip().casefold()
    if not want:
        return False
    presets = get_ann_filter_presets()
    kept = [p for p in presets if str(p["name"]).casefold() != want]
    if len(kept) == len(presets):
        return False
    save_settings({"ann_filter_presets": kept})
    return True


WORKSPACE_LAYOUTS_MAX = 20  # max. 20 Layouts — 1.6.1
LAYOUTS_SCHEMA_ID = "ildlayouts-v1"
LAYOUTS_VERSION = 1
DEFAULT_WATERMARK_OUTPUT_TEMPLATE = "{stem}_wm"
DEFAULT_STATS_FILENAME_TEMPLATE = "{stem}_stats.json"


def get_stats_filename_template() -> str:
    """Stats-JSON Dateiname-Template, Default ``{stem}_stats.json`` — 1.6.4."""
    raw = str(
        load_settings().get(
            "stats_filename_template",
            DEFAULTS.get("stats_filename_template", DEFAULT_STATS_FILENAME_TEMPLATE),
        )
        or ""
    ).strip()
    if not raw:
        return DEFAULT_STATS_FILENAME_TEMPLATE
    raw = raw.replace("/", "_").replace("\\", "_")
    return raw or DEFAULT_STATS_FILENAME_TEMPLATE


def set_stats_filename_template(template: str) -> str:
    """Stats-JSON Dateiname-Template speichern — 1.6.4."""
    raw = str(template or "").strip() or DEFAULT_STATS_FILENAME_TEMPLATE
    raw = raw.replace("/", "_").replace("\\", "_")
    save_settings({"stats_filename_template": raw})
    return raw


def get_watermark_output_template() -> str:
    """Bake-Ausgabe-Pfad-Template, Default ``{stem}_wm`` — 1.6.2."""
    raw = str(
        load_settings().get(
            "watermark_output_template",
            DEFAULTS["watermark_output_template"],
        )
        or ""
    ).strip()
    if not raw:
        return DEFAULT_WATERMARK_OUTPUT_TEMPLATE
    raw = raw.replace("/", "_").replace("\\", "_")
    for suf in (".pdf", ".PDF"):
        if raw.endswith(suf):
            raw = raw[: -len(suf)]
            break
    if "{stem}" not in raw and "{name}" not in raw:
        raw = "{stem}_" + raw.lstrip("_")
    return raw or DEFAULT_WATERMARK_OUTPUT_TEMPLATE


def set_watermark_output_template(template: str) -> str:
    """Bake-Ausgabe-Template speichern — 1.6.2."""
    raw = str(template or "").strip() or DEFAULT_WATERMARK_OUTPUT_TEMPLATE
    raw = raw.replace("/", "_").replace("\\", "_")
    for suf in (".pdf", ".PDF"):
        if raw.endswith(suf):
            raw = raw[: -len(suf)]
            break
    if "{stem}" not in raw and "{name}" not in raw:
        raw = "{stem}_" + raw.lstrip("_")
    save_settings({"watermark_output_template": raw})
    return raw


def get_crypto_reload_prefill_password() -> bool:
    """Passwort beim Crypto-Reload vorausfüllen (unsicher, default aus) — 1.6.2/1.6.3."""
    return bool(load_settings().get("crypto_reload_prefill_password", False))


def set_crypto_reload_prefill_password(enabled: bool) -> bool:
    """Toggle Crypto-Reload-Prefill speichern — 1.6.2/1.6.3. Passwort nie in Settings/Logs."""
    val = bool(enabled)
    save_settings({"crypto_reload_prefill_password": val})
    return val


def get_last_stats_export_dir() -> Path | None:
    """Letzter Zielordner für Dokument-Statistik JSON — 1.6.3."""
    raw = str(load_settings().get("last_stats_export_dir") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_dir() else None


def set_last_stats_export_dir(path: str | Path) -> None:
    """Zielordner Stats-JSON merken — 1.6.3."""
    p = Path(path)
    if p.is_file():
        p = p.parent
    save_settings({"last_stats_export_dir": str(p)})


def _normalize_workspace_layout(raw: object) -> dict | None:
    """Layout: name + Panel-Sichtbarkeit + Splitter-Größen — 1.6.0/1.6.1."""
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or "").strip()
    if not name:
        return None
    panels_raw = raw.get("panels") or {}
    if not isinstance(panels_raw, dict):
        panels_raw = {}
    panels = {
        "thumbs": bool(panels_raw.get("thumbs", True)),
        "ann": bool(panels_raw.get("ann", True)),
        "bookmark": bool(panels_raw.get("bookmark", True)),
    }
    sizes_raw = raw.get("splitter_sizes") or raw.get("splitter") or []
    sizes: list[int] = []
    if isinstance(sizes_raw, (list, tuple)):
        for v in sizes_raw:
            try:
                iv = int(v)
            except (TypeError, ValueError):
                continue
            if iv > 0:
                sizes.append(iv)
    return {
        "name": name,
        "panels": panels,
        "splitter_sizes": sizes,
    }


def get_workspace_layouts() -> list[dict]:
    """Gespeicherte Sidebar-Workspace-Layouts (Name + Panels + Splitter)."""
    raw = load_settings().get("workspace_layouts") or []
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    seen: set[str] = set()
    for item in raw:
        p = _normalize_workspace_layout(item)
        if not p:
            continue
        key = str(p["name"]).casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
        if len(out) >= WORKSPACE_LAYOUTS_MAX:
            break
    return out


def get_workspace_layout(name: str) -> dict | None:
    want = (name or "").strip().casefold()
    if not want:
        return None
    for p in get_workspace_layouts():
        if str(p["name"]).casefold() == want:
            return dict(p)
    return None


def get_default_workspace_layout_name() -> str:
    """Name des markierten Default-Layouts — 1.6.1."""
    return str(load_settings().get("default_workspace_layout") or "").strip()


def set_default_workspace_layout(name: str | None) -> str:
    """Default-Layout setzen (leer = keines) — 1.6.1."""
    want = (name or "").strip()
    if want and get_workspace_layout(want) is None:
        raise ValueError(f"Layout nicht gefunden: {want}")
    save_settings({"default_workspace_layout": want})
    return want


def save_workspace_layout(
    name: str,
    *,
    panels: dict | None = None,
    splitter_sizes: list[int] | None = None,
    state: dict | None = None,
    overwrite: bool = False,
) -> dict:
    """
    Layout speichern — 1.6.0/1.6.2.
    Duplikat-Namen werden abgelehnt (overwrite=False, Default) — 1.6.2.
    overwrite=True: bestehenden Namen aktualisieren.
    """
    if isinstance(state, dict):
        if not name:
            name = str(state.get("name") or "")
        panels = state.get("panels") if state.get("panels") is not None else panels
        splitter_sizes = (
            state.get("splitter_sizes")
            if state.get("splitter_sizes") is not None
            else splitter_sizes
        )
    layout = _normalize_workspace_layout(
        {
            "name": name,
            "panels": panels or {"thumbs": True, "ann": True, "bookmark": True},
            "splitter_sizes": splitter_sizes or [],
        }
    )
    if not layout:
        raise ValueError("Layout-Name fehlt")
    layouts = get_workspace_layouts()
    key = str(layout["name"]).casefold()
    existing_idx = None
    for i, existing in enumerate(layouts):
        if str(existing["name"]).casefold() == key:
            existing_idx = i
            break
    if existing_idx is not None:
        if not overwrite:
            raise ValueError(f"Name bereits vergeben: {layout['name']}")
        layouts[existing_idx] = layout
    else:
        if len(layouts) >= WORKSPACE_LAYOUTS_MAX:
            raise ValueError(
                f"Maximal {WORKSPACE_LAYOUTS_MAX} Layouts — bitte eines löschen."
            )
        layouts.insert(0, layout)
    layouts = layouts[:WORKSPACE_LAYOUTS_MAX]
    save_settings({"workspace_layouts": layouts})
    return dict(layout)


def rename_workspace_layout(old_name: str, new_name: str) -> dict:
    """Layout umbenennen — 1.6.1."""
    old = (old_name or "").strip()
    new = (new_name or "").strip()
    if not old:
        raise ValueError("Alter Name fehlt")
    if not new:
        raise ValueError("Neuer Name darf nicht leer sein")
    layouts = get_workspace_layouts()
    old_key = old.casefold()
    new_key = new.casefold()
    target = None
    for p in layouts:
        if str(p["name"]).casefold() == old_key:
            target = p
            break
    if target is None:
        raise ValueError(f"Layout nicht gefunden: {old}")
    if old_key != new_key:
        for p in layouts:
            if str(p["name"]).casefold() == new_key:
                raise ValueError(f"Name bereits vergeben: {new}")
    renamed = {
        "name": new,
        "panels": dict(target.get("panels") or {}),
        "splitter_sizes": list(target.get("splitter_sizes") or []),
    }
    out: list[dict] = []
    for p in layouts:
        if str(p["name"]).casefold() == old_key:
            out.append(renamed)
        else:
            out.append(p)
    patch: dict = {"workspace_layouts": out}
    default = get_default_workspace_layout_name()
    if default and default.casefold() == old_key:
        patch["default_workspace_layout"] = new
    save_settings(patch)
    return dict(renamed)


def delete_workspace_layout(name: str) -> bool:
    want = (name or "").strip().casefold()
    if not want:
        return False
    layouts = get_workspace_layouts()
    kept = [p for p in layouts if str(p["name"]).casefold() != want]
    if len(kept) == len(layouts):
        return False
    patch: dict = {"workspace_layouts": kept}
    default = get_default_workspace_layout_name()
    if default and default.casefold() == want:
        patch["default_workspace_layout"] = ""
    save_settings(patch)
    return True


class LayoutsImportError(ValueError):
    """Ungültiges oder konfliktbehaftetes ildlayouts-v1 JSON — 1.6.2/1.6.3."""


class LayoutsImportResult:
    """Import-Ergebnis inkl. Log + Zusammenfassung — 1.6.4/1.6.5."""

    def __init__(self, layouts: list[dict], log: list[str] | None = None):
        self.layouts = list(layouts or [])
        self.log = list(log or [])

    def __iter__(self):
        return iter(self.layouts)

    def __len__(self) -> int:
        return len(self.layouts)

    def __bool__(self) -> bool:
        return bool(self.layouts)

    def summary_counts(self) -> dict[str, int]:
        """Zähler importiert / übersprungen / umbenannt — 1.6.5."""
        imported = skipped = renamed = 0
        for line in self.log:
            s = str(line or "")
            if s.startswith("übersprungen:"):
                skipped += 1
            elif s.startswith("umbenannt:"):
                renamed += 1
            elif s.startswith("importiert:") or s.startswith("ersetzt/importiert:"):
                imported += 1
        return {
            "imported": imported,
            "skipped": skipped,
            "renamed": renamed,
        }

    def summary_text(self) -> str:
        """Eine Zeile Zusammenfassung DE — 1.6.5."""
        c = self.summary_counts()
        return (
            f"importiert: {c['imported']}, "
            f"übersprungen: {c['skipped']}, "
            f"umbenannt: {c['renamed']}"
        )

    def log_text(self, *, include_summary: bool = True) -> str:
        """Vollständiges Import-Log als Text (optional mit Zusammenfassung) — 1.6.5."""
        lines: list[str] = []
        if include_summary:
            lines.append(f"Zusammenfassung: {self.summary_text()}")
            lines.append("")
        if self.log:
            lines.extend(str(x) for x in self.log)
        else:
            lines.append("(keine Einträge)")
        return "\n".join(lines) + "\n"


def export_layouts_import_log_txt(
    path: str | Path,
    result: LayoutsImportResult,
    *,
    utf8_bom: bool = True,
) -> Path:
    """Import-Log als TXT speichern (Zusammenfassung + Zeilen) — 1.6.5."""
    path = Path(path)
    body = (
        "# InstantLens Doc Workspace-Layouts Import-Log\n"
        "# schema: ildlayouts-import-log-v1\n"
        f"# {result.summary_text()}\n"
        "\n"
        f"{result.log_text(include_summary=True)}"
    )
    data = body.encode("utf-8-sig" if utf8_bom else "utf-8")
    path.write_bytes(data)
    return path


def _unique_layout_name(base: str, used: set[str]) -> str:
    """Nächsten freien Namen ``base``, ``base_2``, ``base_3``, … wählen — 1.6.4."""
    name = (base or "Layout").strip() or "Layout"
    if name.casefold() not in used:
        return name
    n = 2
    while True:
        candidate = f"{name}_{n}"
        if candidate.casefold() not in used:
            return candidate
        n += 1


def export_workspace_layouts_dict() -> dict:
    """Workspace-Layouts als exportierbares Dict (ildlayouts-v1) — 1.6.2."""
    return {
        "version": LAYOUTS_VERSION,
        "schema": LAYOUTS_SCHEMA_ID,
        "default": get_default_workspace_layout_name(),
        "layouts": get_workspace_layouts(),
    }


def export_workspace_layouts_json(path: str | Path) -> Path:
    """Workspace-Layouts als JSON schreiben (ildlayouts-v1) — 1.6.2."""
    import json

    path = Path(path)
    path.write_text(
        json.dumps(export_workspace_layouts_dict(), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return path


def import_workspace_layouts_dict(
    data: dict,
    *,
    merge: bool = True,
    on_collision: str = "reject",
) -> LayoutsImportResult:
    """
    Layouts aus Dict übernehmen (ildlayouts-v1) — 1.6.2–1.6.4.
    merge=True: anhängen; merge=False: ersetzen.
    on_collision (nur Merge): ``reject`` (Default, 1.6.2), ``skip``, ``rename`` (_2) — 1.6.4.
    Rückgabe: LayoutsImportResult (layouts + Import-Log).
    Ungültiges Schema: klare DE-Meldung.
    """
    if not isinstance(data, dict):
        raise LayoutsImportError(
            "Ungültiges Layout-JSON: erwartet ein Objekt mit Schema "
            f"„{LAYOUTS_SCHEMA_ID}“."
        )
    schema = data.get("schema")
    if schema is None or str(schema).strip() == "":
        raise LayoutsImportError(
            f"Ungültiges Schema — Feld „schema“ fehlt. "
            f"Erwartet wird „{LAYOUTS_SCHEMA_ID}“."
        )
    if str(schema) != LAYOUTS_SCHEMA_ID:
        raise LayoutsImportError(
            f"Ungültiges Schema — erwartet „{LAYOUTS_SCHEMA_ID}“, "
            f"erhalten „{schema}“."
        )
    ver = data.get("version", LAYOUTS_VERSION)
    try:
        ver_i = int(ver)
    except (TypeError, ValueError) as e:
        raise LayoutsImportError(
            f"Ungültige Version {ver!r} — erwartet {LAYOUTS_VERSION}."
        ) from e
    if ver_i != LAYOUTS_VERSION:
        raise LayoutsImportError(
            f"Inkompatible Version {ver_i} — erwartet {LAYOUTS_VERSION} "
            f"(Schema „{LAYOUTS_SCHEMA_ID}“)."
        )
    raw_list = data.get("layouts")
    if not isinstance(raw_list, list):
        raise LayoutsImportError(
            "Ungültiges Schema/Inhalt: Feld „layouts“ fehlt oder ist keine Liste."
        )
    incoming: list[dict] = []
    seen: set[str] = set()
    for item in raw_list:
        layout = _normalize_workspace_layout(item)
        if not layout:
            continue
        key = str(layout["name"]).casefold()
        if key in seen:
            raise LayoutsImportError(
                f"Name bereits vergeben (im Import): {layout['name']}"
            )
        seen.add(key)
        incoming.append(layout)
    if not incoming:
        raise LayoutsImportError("Keine gültigen Layouts im Import.")

    mode = str(on_collision or "reject").strip().lower()
    if mode not in ("reject", "skip", "rename"):
        mode = "reject"

    log: list[str] = []
    existing = get_workspace_layouts()
    if merge:
        existing_keys = {str(p["name"]).casefold() for p in existing}
        accepted: list[dict] = []
        for layout in incoming:
            key = str(layout["name"]).casefold()
            orig = str(layout["name"])
            if key in existing_keys:
                if mode == "reject":
                    raise LayoutsImportError(f"Name bereits vergeben: {orig}")
                if mode == "skip":
                    log.append(f"übersprungen: {orig}")
                    continue
                # rename → Name_2, Name_3, …
                new_name = _unique_layout_name(orig, existing_keys)
                layout = dict(layout)
                layout["name"] = new_name
                log.append(f"umbenannt: {orig} → {new_name}")
                existing_keys.add(new_name.casefold())
                accepted.append(layout)
            else:
                log.append(f"importiert: {orig}")
                existing_keys.add(key)
                accepted.append(layout)
        combined = accepted + existing
        if not accepted and not existing:
            raise LayoutsImportError("Keine gültigen Layouts im Import.")
    else:
        # Ersetzen: bestehende Layouts verwerfen — 1.6.3
        combined = list(incoming)
        for layout in incoming:
            log.append(f"ersetzt/importiert: {layout['name']}")
    if len(combined) > WORKSPACE_LAYOUTS_MAX:
        raise LayoutsImportError(
            f"Maximal {WORKSPACE_LAYOUTS_MAX} Layouts — Import würde Limit überschreiten."
        )
    patch: dict = {"workspace_layouts": combined[:WORKSPACE_LAYOUTS_MAX]}
    default = str(data.get("default") or "").strip()
    if default:
        if any(str(p["name"]).casefold() == default.casefold() for p in combined):
            patch["default_workspace_layout"] = default
        elif merge and mode == "rename":
            # Default-Name ggf. mitumbenannt — im Log nachsehen
            for line in log:
                if line.startswith(f"umbenannt: {default} → "):
                    new_def = line.split(" → ", 1)[1].strip()
                    if any(
                        str(p["name"]).casefold() == new_def.casefold()
                        for p in combined
                    ):
                        patch["default_workspace_layout"] = new_def
                    break
    elif not merge:
        patch["default_workspace_layout"] = ""
    save_settings(patch)
    return LayoutsImportResult(get_workspace_layouts(), log)


def import_workspace_layouts_json(
    path: str | Path,
    *,
    merge: bool = True,
    on_collision: str = "reject",
) -> LayoutsImportResult:
    """Workspace-Layouts aus JSON laden (ildlayouts-v1) — 1.6.2–1.6.4."""
    import json

    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise LayoutsImportError(f"JSON lesen fehlgeschlagen: {e}") from e
    if not isinstance(data, dict):
        raise LayoutsImportError(
            "Ungültiges Layout-JSON: erwartet ein Objekt mit Schema "
            f"„{LAYOUTS_SCHEMA_ID}“."
        )
    return import_workspace_layouts_dict(
        data, merge=merge, on_collision=on_collision
    )


def get_last_watermark_settings() -> dict:
    """Zuletzt verwendete Wasserzeichen-Settings — 1.6.1."""
    s = load_settings()
    try:
        opacity = float(s.get("last_watermark_opacity", 0.25) or 0.25)
    except (TypeError, ValueError):
        opacity = 0.25
    try:
        angle = float(s.get("last_watermark_angle", 45.0) or 45.0)
    except (TypeError, ValueError):
        angle = 45.0
    try:
        font_size = float(s.get("last_watermark_font_size", 48.0) or 48.0)
    except (TypeError, ValueError):
        font_size = 48.0
    try:
        img_scale = float(s.get("last_watermark_img_scale", 0.45) or 0.45)
    except (TypeError, ValueError):
        img_scale = 0.45
    placement = str(s.get("last_watermark_placement") or "diagonal").strip().lower()
    if placement not in ("diagonal", "center"):
        placement = "diagonal"
    mode = str(s.get("last_watermark_mode") or "text").strip().lower()
    if mode not in ("text", "image"):
        mode = "text"
    text = str(s.get("last_watermark_text") or "VERTRAULICH")
    image = str(s.get("last_watermark_image") or "").strip()
    return {
        "text": text,
        "image": image,
        "opacity": max(0.05, min(1.0, opacity)),
        "angle": max(-90.0, min(90.0, angle)),
        "font_size": max(8.0, min(120.0, font_size)),
        "img_scale": max(0.1, min(1.0, img_scale)),
        "placement": placement,
        "mode": mode,
    }


def set_last_watermark_settings(
    *,
    text: str | None = None,
    image: str | None = None,
    opacity: float | None = None,
    angle: float | None = None,
    font_size: float | None = None,
    img_scale: float | None = None,
    placement: str | None = None,
    mode: str | None = None,
) -> None:
    """Wasserzeichen-Settings (Opacity/Größe/Winkel + Text/Bild) merken — 1.6.1."""
    patch: dict = {}
    if text is not None:
        patch["last_watermark_text"] = str(text)
    if image is not None:
        patch["last_watermark_image"] = str(image or "")
    if opacity is not None:
        try:
            patch["last_watermark_opacity"] = max(0.05, min(1.0, float(opacity)))
        except (TypeError, ValueError):
            pass
    if angle is not None:
        try:
            patch["last_watermark_angle"] = max(-90.0, min(90.0, float(angle)))
        except (TypeError, ValueError):
            pass
    if font_size is not None:
        try:
            patch["last_watermark_font_size"] = max(8.0, min(120.0, float(font_size)))
        except (TypeError, ValueError):
            pass
    if img_scale is not None:
        try:
            patch["last_watermark_img_scale"] = max(0.1, min(1.0, float(img_scale)))
        except (TypeError, ValueError):
            pass
    if placement is not None:
        p = str(placement).strip().lower()
        if p in ("diagonal", "center"):
            patch["last_watermark_placement"] = p
    if mode is not None:
        m = str(mode).strip().lower()
        if m in ("text", "image"):
            patch["last_watermark_mode"] = m
    if patch:
        save_settings(patch)


def get_editor_line_numbers() -> bool:
    return bool(load_settings().get("editor_line_numbers", False))


def set_editor_line_numbers(enabled: bool) -> None:
    save_settings({"editor_line_numbers": bool(enabled)})


def get_editor_minimap() -> bool:
    """Optionale Editor-Minimap (Linien-Übersicht + dickere Scrollbar)."""
    return bool(load_settings().get("editor_minimap", False))


def set_editor_minimap(enabled: bool) -> None:
    save_settings({"editor_minimap": bool(enabled)})


# Feste Annotation-Palette für Zyklus/Randomizer (Highlight/Stift/Notiz)
ANN_COLOR_PALETTE: tuple[str, ...] = (
    "#FFE066",
    "#FF6B6B",
    "#4ECDC4",
    "#95E1D3",
    "#F38181",
    "#AA96DA",
    "#FCBAD3",
    "#A8D8EA",
    "#FF9F43",
    "#2ECC71",
    "#3498DB",
    "#9B59B6",
)


def get_ann_color_palette() -> list[str]:
    return list(ANN_COLOR_PALETTE)


def get_ann_palette_index() -> int:
    try:
        idx = int(load_settings().get("ann_palette_index", 0))
    except (TypeError, ValueError):
        idx = 0
    n = len(ANN_COLOR_PALETTE)
    if n <= 0:
        return 0
    return idx % n


def set_ann_palette_index(index: int) -> int:
    n = len(ANN_COLOR_PALETTE)
    if n <= 0:
        save_settings({"ann_palette_index": 0})
        return 0
    idx = int(index) % n
    save_settings({"ann_palette_index": idx})
    return idx


def cycle_ann_palette_color() -> str:
    """Nächste Palette-Farbe (Zyklus); Index persistieren."""
    n = len(ANN_COLOR_PALETTE)
    if n <= 0:
        return get_ann_highlight_color()
    nxt = (get_ann_palette_index() + 1) % n
    set_ann_palette_index(nxt)
    return ANN_COLOR_PALETTE[nxt]


def random_ann_palette_color() -> str:
    """Zufällige Palette-Farbe; Index auf Treffer setzen."""
    import random

    n = len(ANN_COLOR_PALETTE)
    if n <= 0:
        return get_ann_highlight_color()
    idx = random.randrange(n)
    set_ann_palette_index(idx)
    return ANN_COLOR_PALETTE[idx]


def get_pdf_grayscale() -> bool:
    return bool(load_settings().get("pdf_grayscale", False))


def set_pdf_grayscale(enabled: bool) -> None:
    save_settings({"pdf_grayscale": bool(enabled)})


def get_pdf_night_mode() -> bool:
    """Nachtmodus (Invert-Ansicht) — nur Darstellung, nicht Export/Speichern."""
    return bool(load_settings().get("pdf_night_mode", False))


def set_pdf_night_mode(enabled: bool) -> None:
    save_settings({"pdf_night_mode": bool(enabled)})


def get_ann_default_opacity() -> float:
    try:
        v = float(load_settings().get("ann_default_opacity", 1.0))
    except (TypeError, ValueError):
        v = 1.0
    return max(0.05, min(1.0, v))


def set_ann_default_opacity(opacity: float) -> None:
    try:
        v = float(opacity)
    except (TypeError, ValueError):
        v = 1.0
    save_settings({"ann_default_opacity": max(0.05, min(1.0, v))})


def get_ann_default_stroke_width() -> float:
    """Standard-Strichstärke für neue Shapes (1–12 px) — 0.9.2."""
    try:
        v = float(load_settings().get("ann_default_stroke_width", 2.0))
    except (TypeError, ValueError):
        v = 2.0
    return max(1.0, min(12.0, v))


def set_ann_default_stroke_width(width: float) -> None:
    try:
        v = float(width)
    except (TypeError, ValueError):
        v = 2.0
    save_settings({"ann_default_stroke_width": max(1.0, min(12.0, v))})


def get_ann_default_fill_color() -> str:
    """Standard-Füllfarbe für neue Shapes (#RRGGBB) — 0.9.9."""
    fallback = str(DEFAULTS.get("ann_default_fill_color") or "#FFE066")
    c = str(load_settings().get("ann_default_fill_color") or fallback).strip()
    if not c.startswith("#"):
        c = "#" + c if c else fallback
    return c.upper() if len(c) >= 4 else fallback.upper()


def set_ann_default_fill_color(color: str) -> str:
    fallback = str(DEFAULTS.get("ann_default_fill_color") or "#FFE066")
    c = (color or "").strip() or fallback
    if not c.startswith("#"):
        c = "#" + c
    c = c.upper()
    save_settings({"ann_default_fill_color": c})
    return c


RECENT_DIRS_MAX = 8
PROJECT_WORKSPACES_MAX = 5


def get_recent_dirs(max_items: int = RECENT_DIRS_MAX) -> list[Path]:
    """Zuletzt verwendete Ordner (nur existierende)."""
    raw = load_settings().get("recent_dirs") or []
    if not isinstance(raw, list):
        return []
    out: list[Path] = []
    seen: set[str] = set()
    for item in raw:
        p = Path(str(item)).expanduser()
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        if p.is_dir():
            out.append(p)
        if len(out) >= max_items:
            break
    return out


def remember_recent_dir(path: str | Path | None, max_items: int = RECENT_DIRS_MAX) -> list[Path]:
    """Ordner (oder Elternordner einer Datei) als zuletzt verwendet merken."""
    if path is None or str(path).strip() == "":
        return get_recent_dirs(max_items=max_items)
    p = Path(path).expanduser()
    if p.is_dir():
        pass
    elif p.is_file():
        p = p.parent
    elif p.parent.is_dir():
        # Speichern-unter-Pfad o. ä. — Parent nutzen
        p = p.parent
    else:
        return get_recent_dirs(max_items=max_items)
    key = str(p)
    prev = [str(x) for x in get_recent_dirs(max_items=max_items * 2)]
    cleaned = [key] + [x for x in prev if x != key]
    cleaned = cleaned[:max_items]
    save_settings({"recent_dirs": cleaned})
    return get_recent_dirs(max_items=max_items)


def get_project_workspaces(max_items: int = PROJECT_WORKSPACES_MAX) -> list[Path]:
    """Letzte Projekt-Ordner / Workspaces (nur existierende), max. 5."""
    raw = load_settings().get("project_workspaces") or []
    if not isinstance(raw, list):
        return []
    out: list[Path] = []
    seen: set[str] = set()
    for item in raw:
        p = Path(str(item)).expanduser()
        key = str(p.resolve()) if p.exists() else str(p)
        if key in seen:
            continue
        seen.add(key)
        if p.is_dir():
            out.append(p)
        if len(out) >= max_items:
            break
    return out


def remember_project_workspace(
    path: str | Path | None,
    max_items: int = PROJECT_WORKSPACES_MAX,
    *,
    activate: bool = True,
) -> list[Path]:
    """Projekt-Ordner als Workspace merken (letzte 5) und optional aktiv setzen."""
    if path is None or str(path).strip() == "":
        return get_project_workspaces(max_items=max_items)
    p = Path(path).expanduser()
    if not p.is_dir():
        return get_project_workspaces(max_items=max_items)
    key = str(p.resolve() if p.exists() else p)
    prev = [str(x) for x in get_project_workspaces(max_items=max_items * 2)]
    cleaned = [key] + [x for x in prev if x != key]
    cleaned = cleaned[:max_items]
    payload: dict[str, Any] = {"project_workspaces": cleaned}
    if activate:
        payload["active_project_workspace"] = key
        payload["default_open_dir"] = key
    save_settings(payload)
    remember_recent_dir(p)
    return get_project_workspaces(max_items=max_items)


def get_active_project_workspace() -> Path | None:
    """Aktiver Projekt-Ordner, falls vorhanden und existent."""
    raw = str(load_settings().get("active_project_workspace") or "").strip()
    if raw:
        p = Path(raw).expanduser()
        if p.is_dir():
            return p
    for d in get_project_workspaces():
        return d
    return None


def clear_active_project_workspace() -> None:
    save_settings({"active_project_workspace": ""})


def dialog_start_dir(*fallbacks: str | Path | None) -> str:
    """Startpfad für QFileDialog: aktiver Workspace, zuletzt verwendeter Ordner, sonst Fallbacks."""
    active = get_active_project_workspace()
    if active is not None and active.is_dir():
        return str(active)
    for d in get_recent_dirs():
        if d.is_dir():
            return str(d)
    for fb in fallbacks:
        if fb is None:
            continue
        p = Path(fb)
        if p.is_file():
            p = p.parent
        if p.is_dir():
            return str(p)
        # default_open / last_export als String ohne Existenzcheck schon in get_*
    d = get_default_open_dir()
    if d:
        return str(d)
    d = get_last_export_dir()
    if d:
        return str(d)
    return ""


def get_editor_markdown_preview() -> bool:
    return bool(load_settings().get("editor_markdown_preview", False))


def set_editor_markdown_preview(enabled: bool) -> None:
    save_settings({"editor_markdown_preview": bool(enabled)})


def get_editor_doc_split() -> bool:
    return bool(load_settings().get("editor_doc_split", False))


def set_editor_doc_split(enabled: bool) -> None:
    save_settings({"editor_doc_split": bool(enabled)})


def get_editor_doc_split_sync_scroll() -> bool:
    return bool(load_settings().get("editor_doc_split_sync_scroll", False))


def set_editor_doc_split_sync_scroll(enabled: bool) -> None:
    save_settings({"editor_doc_split_sync_scroll": bool(enabled)})


def get_editor_doc_split_vertical() -> bool:
    """True = Doc-Split vertikal (übereinander), False = horizontal (nebeneinander)."""
    return bool(load_settings().get("editor_doc_split_vertical", False))


def set_editor_doc_split_vertical(enabled: bool) -> None:
    save_settings({"editor_doc_split_vertical": bool(enabled)})


def get_tag_rename_confirm_threshold() -> int:
    """Bestätigung beim Tag-Rename wenn Treffer > Schwelle (Default 20)."""
    try:
        n = int(load_settings().get("tag_rename_confirm_threshold", 20))
    except (TypeError, ValueError):
        n = 20
    return max(0, min(n, 99999))


def set_tag_rename_confirm_threshold(n: int) -> None:
    try:
        val = int(n)
    except (TypeError, ValueError):
        val = 20
    save_settings({"tag_rename_confirm_threshold": max(0, min(val, 99999))})


def get_wizard_completed() -> bool:
    """True = Erste-Schritte-Wizard dauerhaft abgeschlossen."""
    return bool(load_settings().get("wizard_completed", False))


def set_wizard_completed(done: bool) -> None:
    save_settings({"wizard_completed": bool(done)})


def get_wizard_skip_once() -> bool:
    """True = Wizard beim nächsten Start einmal überspringen."""
    return bool(load_settings().get("wizard_skip_once", False))


def set_wizard_skip_once(skip: bool) -> None:
    save_settings({"wizard_skip_once": bool(skip)})


def consume_wizard_skip_once() -> bool:
    """
    Einmaliges Überspringen abfragen und Flag zurücksetzen.
    Rückgabe: True wenn dieser Start übersprungen werden soll.
    """
    if not get_wizard_skip_once():
        return False
    set_wizard_skip_once(False)
    return True


def get_selection_note_with_highlight() -> bool:
    return bool(load_settings().get("selection_note_with_highlight", False))


def set_selection_note_with_highlight(enabled: bool) -> None:
    save_settings({"selection_note_with_highlight": bool(enabled)})


def get_editor_soft_wrap() -> bool:
    return bool(load_settings().get("editor_soft_wrap", True))


def set_editor_soft_wrap(enabled: bool) -> None:
    save_settings({"editor_soft_wrap": bool(enabled)})


def get_editor_show_special_chars() -> bool:
    return bool(load_settings().get("editor_show_special_chars", False))


def set_editor_show_special_chars(enabled: bool) -> None:
    save_settings({"editor_show_special_chars": bool(enabled)})


def get_annotations_visible() -> bool:
    return bool(load_settings().get("annotations_visible", True))


def set_annotations_visible(visible: bool) -> None:
    save_settings({"annotations_visible": bool(visible)})


ANN_LAYER_TYPE_KEYS = ("highlight", "note", "shape", "redaction")


def get_ann_layer_types_visible() -> dict[str, bool]:
    """Globale Typ-Sichtbarkeit für Annotation-Layer — 1.8.0."""
    raw = load_settings().get("ann_layer_types_visible") or {}
    out: dict[str, bool] = {}
    for key in ANN_LAYER_TYPE_KEYS:
        if isinstance(raw, dict) and key in raw:
            out[key] = bool(raw[key])
        else:
            out[key] = True
    return out


def set_ann_layer_types_visible(visible: dict[str, bool] | None) -> dict[str, bool]:
    """Typ-Toggles speichern; fehlende Keys bleiben True — 1.8.0."""
    cur = get_ann_layer_types_visible()
    if visible:
        for key in ANN_LAYER_TYPE_KEYS:
            if key in visible:
                cur[key] = bool(visible[key])
    save_settings({"ann_layer_types_visible": cur})
    return cur


def set_ann_layer_type_visible(group: str, visible: bool) -> dict[str, bool]:
    key = str(group or "").strip().lower()
    if key not in ANN_LAYER_TYPE_KEYS:
        return get_ann_layer_types_visible()
    cur = get_ann_layer_types_visible()
    cur[key] = bool(visible)
    save_settings({"ann_layer_types_visible": cur})
    return cur


def get_crash_recovery_enabled() -> bool:
    return bool(load_settings().get("crash_recovery_enabled", True))


def set_crash_recovery_enabled(enabled: bool) -> None:
    save_settings({"crash_recovery_enabled": bool(enabled)})


def get_crash_recovery_max_age_hours() -> float:
    try:
        v = float(load_settings().get("crash_recovery_max_age_hours", 72.0))
    except (TypeError, ValueError):
        v = 72.0
    return max(1.0, min(720.0, v))


def set_crash_recovery_max_age_hours(hours: float) -> None:
    try:
        v = float(hours)
    except (TypeError, ValueError):
        v = 72.0
    save_settings({"crash_recovery_max_age_hours": max(1.0, min(720.0, v))})


def get_last_header_footer_settings() -> dict[str, Any]:
    s = load_settings()
    return {
        "header_text": str(s.get("last_header_text") or ""),
        "footer_text": str(s.get("last_footer_text") or ""),
        "include_page_numbers": bool(s.get("last_hf_include_page_numbers", True)),
        "page_template": str(s.get("last_hf_page_template") or "{n} / {total}"),
        "header_position": str(s.get("last_hf_header_position") or "top-center"),
        "footer_position": str(s.get("last_hf_footer_position") or "bottom-center"),
        "page_position": str(s.get("last_hf_page_position") or "bottom-right"),
        "font_size": float(s.get("last_hf_font_size") or 10.0),
        "margin": float(s.get("last_hf_margin") or 28.0),
        "page_range": str(s.get("last_hf_page_range") or ""),
    }


def set_last_header_footer_settings(
    *,
    header_text: str = "",
    footer_text: str = "",
    include_page_numbers: bool = True,
    page_template: str = "{n} / {total}",
    header_position: str = "top-center",
    footer_position: str = "bottom-center",
    page_position: str = "bottom-right",
    font_size: float = 10.0,
    margin: float = 28.0,
    page_range: str = "",
) -> None:
    save_settings(
        {
            "last_header_text": str(header_text or ""),
            "last_footer_text": str(footer_text or ""),
            "last_hf_include_page_numbers": bool(include_page_numbers),
            "last_hf_page_template": str(page_template or "{n} / {total}"),
            "last_hf_header_position": str(header_position or "top-center"),
            "last_hf_footer_position": str(footer_position or "bottom-center"),
            "last_hf_page_position": str(page_position or "bottom-right"),
            "last_hf_font_size": float(font_size),
            "last_hf_margin": float(margin),
            "last_hf_page_range": str(page_range or ""),
        }
    )


def get_show_page_boxes() -> bool:
    """Optional: MediaBox/CropBox-Rahmen als Overlay auf der PDF-Seite."""
    return bool(load_settings().get("show_page_boxes", False))


def set_show_page_boxes(enabled: bool) -> None:
    save_settings({"show_page_boxes": bool(enabled)})


def get_show_page_number_overlay() -> bool:
    """Optional: Seitennummer als Overlay auf der PDF-Seite."""
    return bool(load_settings().get("show_page_number_overlay", False))


def set_show_page_number_overlay(enabled: bool) -> None:
    save_settings({"show_page_number_overlay": bool(enabled)})


def get_page_number_overlay_opacity() -> float:
    """Deckkraft des Seitennummer-Overlays (0.05–1.0)."""
    try:
        op = float(load_settings().get("page_number_overlay_opacity", 0.59))
    except (TypeError, ValueError):
        op = 0.59
    return round(max(0.05, min(1.0, op)), 4)


def set_page_number_overlay_opacity(opacity: float) -> None:
    try:
        op = float(opacity)
    except (TypeError, ValueError):
        op = 0.59
    save_settings({"page_number_overlay_opacity": round(max(0.05, min(1.0, op)), 4)})


def get_page_number_overlay_font_size() -> int:
    """Schriftgröße (pt) des Seitennummer-Overlays (8–36)."""
    try:
        sz = int(load_settings().get("page_number_overlay_font_size", 11))
    except (TypeError, ValueError):
        sz = 11
    return max(8, min(36, sz))


def set_page_number_overlay_font_size(size: int) -> None:
    try:
        sz = int(size)
    except (TypeError, ValueError):
        sz = 11
    save_settings({"page_number_overlay_font_size": max(8, min(36, sz))})


def get_page_number_overlay_position() -> str:
    """Position des Seitennummer-Overlays: bottom-center | top-center."""
    raw = str(load_settings().get("page_number_overlay_position", "bottom-center") or "")
    key = raw.strip().lower().replace("_", "-")
    if key in ("top-center", "top", "oben", "oben-mitte"):
        return "top-center"
    return "bottom-center"


def set_page_number_overlay_position(position: str) -> None:
    raw = str(position or "bottom-center").strip().lower().replace("_", "-")
    if raw in ("top-center", "top", "oben", "oben-mitte"):
        key = "top-center"
    else:
        key = "bottom-center"
    save_settings({"page_number_overlay_position": key})


def get_page_number_overlay_format() -> str:
    """Format-String für Seitennummer-Overlay; Platzhalter {page}/{pages} bzw. {n}/{total}."""
    raw = str(
        load_settings().get("page_number_overlay_format", "{page} / {pages}") or ""
    ).strip()
    return raw or "{page} / {pages}"


def set_page_number_overlay_format(fmt: str) -> None:
    text = str(fmt or "").strip() or "{page} / {pages}"
    if len(text) > 80:
        text = text[:80]
    save_settings({"page_number_overlay_format": text})


def get_page_number_overlay_start() -> int:
    """Startnummer für Seitennummer-Overlay (erste Seite ≠ 1 möglich)."""
    try:
        n = int(load_settings().get("page_number_overlay_start", 1))
    except (TypeError, ValueError):
        n = 1
    return max(0, min(9999, n))


def set_page_number_overlay_start(start: int) -> None:
    try:
        n = int(start)
    except (TypeError, ValueError):
        n = 1
    save_settings({"page_number_overlay_start": max(0, min(9999, n))})


def get_page_number_overlay_skip_edges() -> bool:
    """True = Seitennummer-Overlay auf erster und letzter Seite ausblenden."""
    return bool(load_settings().get("page_number_overlay_skip_edges", False))


def set_page_number_overlay_skip_edges(enabled: bool) -> None:
    save_settings({"page_number_overlay_skip_edges": bool(enabled)})


def get_editor_tab_width() -> int:
    """Editor-Tab-Breite in Zeichen (2 / 4 / 8)."""
    try:
        w = int(load_settings().get("editor_tab_width", 4))
    except (TypeError, ValueError):
        w = 4
    if w not in (2, 4, 8):
        w = 4
    return w


def set_editor_tab_width(width: int) -> None:
    try:
        w = int(width)
    except (TypeError, ValueError):
        w = 4
    if w not in (2, 4, 8):
        w = 4
    save_settings({"editor_tab_width": w})


def get_editor_soft_tabs() -> bool:
    """True = Tab als Leerzeichen (Soft-Tabs); False = echte Tabulatorzeichen."""
    return bool(load_settings().get("editor_soft_tabs", True))


def set_editor_soft_tabs(enabled: bool) -> None:
    save_settings({"editor_soft_tabs": bool(enabled)})


def get_editor_indent_guides() -> bool:
    """True = vertikale Einrückungs-Guides (Tab-Stops) im Editor."""
    return bool(load_settings().get("editor_indent_guides", True))


def set_editor_indent_guides(enabled: bool) -> None:
    save_settings({"editor_indent_guides": bool(enabled)})


def get_editor_current_line_highlight() -> bool:
    """True = aktuelle Editorzeile hervorheben."""
    return bool(load_settings().get("editor_current_line_highlight", True))


def set_editor_current_line_highlight(enabled: bool) -> None:
    save_settings({"editor_current_line_highlight": bool(enabled)})


def get_show_printer_marks() -> bool:
    """Optional: Seitenrand-Druckermarken (Crop/Registration) als Overlay."""
    return bool(load_settings().get("show_printer_marks", False))


def set_show_printer_marks(enabled: bool) -> None:
    save_settings({"show_printer_marks": bool(enabled)})


def get_show_rulers() -> bool:
    """Horizontales/vertikales Lineal im PDF-Viewer — 2.6.11."""
    return bool(load_settings().get("show_rulers", False))


def set_show_rulers(enabled: bool) -> None:
    save_settings({"show_rulers": bool(enabled)})


def get_show_alignment_grid() -> bool:
    """Ausrichtungsraster einblenden — 2.6.11."""
    return bool(load_settings().get("show_alignment_grid", False))


def set_show_alignment_grid(enabled: bool) -> None:
    save_settings({"show_alignment_grid": bool(enabled)})


def get_alignment_grid_spacing_mm() -> float:
    raw = load_settings().get("alignment_grid_spacing_mm", DEFAULTS["alignment_grid_spacing_mm"])
    try:
        val = float(raw)
    except (TypeError, ValueError):
        val = float(DEFAULTS["alignment_grid_spacing_mm"])
    return max(1.0, min(50.0, val))


def set_alignment_grid_spacing_mm(mm: float) -> float:
    try:
        val = float(mm)
    except (TypeError, ValueError):
        val = float(DEFAULTS["alignment_grid_spacing_mm"])
    val = max(1.0, min(50.0, val))
    save_settings({"alignment_grid_spacing_mm": val})
    return val


def get_alignment_grid_snap() -> bool:
    return bool(load_settings().get("alignment_grid_snap", False))


def set_alignment_grid_snap(enabled: bool) -> None:
    save_settings({"alignment_grid_snap": bool(enabled)})


def get_show_satzspiegel() -> bool:
    """Satzspiegel-Overlay — 2.6.12."""
    return bool(load_settings().get("show_satzspiegel", False))


def set_show_satzspiegel(enabled: bool) -> None:
    save_settings({"show_satzspiegel": bool(enabled)})


def get_satzspiegel_format() -> str:
    raw = load_settings().get("satzspiegel_format", DEFAULTS["satzspiegel_format"])
    return str(raw or "A4")


def set_satzspiegel_format(name: str) -> str:
    val = str(name or "A4").strip() or "A4"
    save_settings({"satzspiegel_format": val})
    return val


def get_satzspiegel_columns() -> int:
    try:
        n = int(load_settings().get("satzspiegel_columns", 1))
    except (TypeError, ValueError):
        n = 1
    return max(1, min(6, n))


def set_satzspiegel_columns(n: int) -> int:
    try:
        val = max(1, min(6, int(n)))
    except (TypeError, ValueError):
        val = 1
    save_settings({"satzspiegel_columns": val})
    return val


def get_ruler_unit() -> str:
    u = str(load_settings().get("ruler_unit", DEFAULTS["ruler_unit"]) or "mm").lower()
    return "inch" if u in ("in", "inch", "inches") else "mm"


def set_ruler_unit(unit: str) -> str:
    u = "inch" if str(unit or "").lower() in ("in", "inch", "inches") else "mm"
    save_settings({"ruler_unit": u})
    return u


def get_alignment_guides() -> list[dict]:
    raw = load_settings().get("alignment_guides", [])
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(dict(item))
    return out


def set_alignment_guides(guides: list[dict] | None) -> list[dict]:
    data = list(guides or [])
    save_settings({"alignment_guides": data})
    return data


def get_annotations_locked() -> bool:
    """Annotationen gesperrt (nicht per Drag verschiebbar)."""
    return bool(load_settings().get("annotations_locked", False))


def set_annotations_locked(locked: bool) -> None:
    save_settings({"annotations_locked": bool(locked)})


EDITOR_SNIPPET_COUNT = 9  # erweitert 3→9 — 2.6.20
_DEFAULT_EDITOR_SNIPPETS = [
    "Sehr geehrte Damen und Herren,\n\n",
    "Mit freundlichen Grüßen\n",
    "— Notiz —\n",
    "Best regards,\n",
    "Vielen Dank im Voraus.\n",
    "Anbei das Dokument zur Prüfung.\n",
    "Bitte um kurze Rückmeldung.\n",
    "Freundliche Grüße\n",
    "— Textbaustein —\n",
]


def get_editor_snippets() -> list[str]:
    """Neun gespeicherte Textbausteine für den Editor — 2.6.20."""
    raw = load_settings().get("editor_snippets")
    defaults = list(_DEFAULT_EDITOR_SNIPPETS)
    if not isinstance(raw, list):
        return defaults
    out: list[str] = []
    for i in range(EDITOR_SNIPPET_COUNT):
        if i < len(raw):
            out.append(str(raw[i] if raw[i] is not None else defaults[i]))
        else:
            out.append(defaults[i])
    return out


def set_editor_snippets(snippets: list[str]) -> list[str]:
    defaults = list(_DEFAULT_EDITOR_SNIPPETS)
    cleaned: list[str] = []
    for i in range(EDITOR_SNIPPET_COUNT):
        if i < len(snippets) and snippets[i] is not None:
            cleaned.append(str(snippets[i]))
        else:
            cleaned.append(defaults[i] if i < len(defaults) else "")
    save_settings({"editor_snippets": cleaned})
    return cleaned


def set_editor_snippet(index: int, text: str) -> list[str]:
    """Einzelnen Textbaustein-Slot (0..8) setzen — 2.6.20."""
    snippets = get_editor_snippets()
    i = max(0, min(EDITOR_SNIPPET_COUNT - 1, int(index)))
    snippets[i] = str(text if text is not None else "")
    return set_editor_snippets(snippets)


def get_spellcheck_use_builtin() -> bool:
    return bool(load_settings().get("spellcheck_use_builtin", True))


def set_spellcheck_use_builtin(enabled: bool) -> None:
    save_settings({"spellcheck_use_builtin": bool(enabled)})


def get_spellcheck_grammar_hints() -> bool:
    return bool(load_settings().get("spellcheck_grammar_hints", True))


def set_spellcheck_grammar_hints(enabled: bool) -> None:
    save_settings({"spellcheck_grammar_hints": bool(enabled)})


def get_autocorrect_enabled() -> bool:
    return bool(load_settings().get("autocorrect_enabled", True))


def set_autocorrect_enabled(enabled: bool) -> None:
    save_settings({"autocorrect_enabled": bool(enabled)})


def get_autocorrect_expand_snippets() -> bool:
    return bool(load_settings().get("autocorrect_expand_snippets", True))


def set_autocorrect_expand_snippets(enabled: bool) -> None:
    save_settings({"autocorrect_expand_snippets": bool(enabled)})


def get_autocorrect_user_rules() -> dict[str, str]:
    raw = load_settings().get("autocorrect_user_rules")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in raw.items():
        key = str(k or "").strip().casefold()
        if key and v is not None:
            out[key] = str(v)
    return out


def set_autocorrect_user_rules(rules: dict[str, str] | None) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for k, v in (rules or {}).items():
        key = str(k or "").strip().casefold()
        if key and v is not None and str(v) != "":
            cleaned[key] = str(v)
    save_settings({"autocorrect_user_rules": cleaned})
    return cleaned


def set_autocorrect_user_rule(trigger: str, replacement: str) -> dict[str, str]:
    rules = get_autocorrect_user_rules()
    key = str(trigger or "").strip().casefold()
    if key:
        if replacement is None or str(replacement) == "":
            rules.pop(key, None)
        else:
            rules[key] = str(replacement)
    return set_autocorrect_user_rules(rules)


USER_DOC_TEMPLATE_LIMIT = 20


def get_user_doc_templates() -> list[dict]:
    """Gespeicherte Nutzer-Dokumentvorlagen: [{id, title, body}, …]."""
    raw = load_settings().get("user_doc_templates")
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        tid = str(item.get("id") or "").strip()
        title = str(item.get("title") or "").strip()
        body = str(item.get("body") if item.get("body") is not None else "")
        if not tid or not title:
            continue
        out.append({"id": tid, "title": title, "body": body})
        if len(out) >= USER_DOC_TEMPLATE_LIMIT:
            break
    return out


def get_user_doc_template(template_id: str) -> dict | None:
    needle = str(template_id or "").strip()
    if not needle:
        return None
    # Prefixe user: optional
    if needle.lower().startswith("user:"):
        needle = needle[5:]
    for t in get_user_doc_templates():
        if t["id"] == needle or t["id"].casefold() == needle.casefold():
            return t
        if t["title"].casefold() == needle.casefold():
            return t
    return None


def save_user_doc_template(
    title: str,
    body: str,
    *,
    template_id: str | None = None,
) -> dict:
    """
    Nutzer-Vorlage speichern / überschreiben (gleicher Titel → Update).
    Rückgabe: gespeicherter Eintrag {id, title, body}.
    """
    from uuid import uuid4

    title_s = str(title or "").strip() or "Vorlage"
    body_s = str(body if body is not None else "")
    items = get_user_doc_templates()
    tid = str(template_id or "").strip()
    if tid and tid.lower().startswith("user:"):
        tid = tid[5:]
    # Update by id or same title
    updated = False
    for item in items:
        if tid and item["id"] == tid:
            item["title"] = title_s
            item["body"] = body_s
            updated = True
            tid = item["id"]
            break
        if not tid and item["title"].casefold() == title_s.casefold():
            item["body"] = body_s
            tid = item["id"]
            updated = True
            break
    if not updated:
        if len(items) >= USER_DOC_TEMPLATE_LIMIT:
            items.pop(0)
        tid = tid or uuid4().hex[:12]
        items.append({"id": tid, "title": title_s, "body": body_s})
    save_settings({"user_doc_templates": items})
    return {"id": tid, "title": title_s, "body": body_s}


def delete_user_doc_template(template_id: str) -> bool:
    needle = str(template_id or "").strip()
    if not needle:
        return False
    if needle.lower().startswith("user:"):
        needle = needle[5:]
    items = get_user_doc_templates()
    new_items = [t for t in items if t["id"] != needle]
    if len(new_items) == len(items):
        return False
    save_settings({"user_doc_templates": new_items})
    return True


def rename_user_doc_template(template_id: str, new_title: str) -> dict | None:
    """Nutzer-Vorlage umbenennen. Rückgabe: aktualisierter Eintrag oder None."""
    needle = str(template_id or "").strip()
    if not needle:
        return None
    if needle.lower().startswith("user:"):
        needle = needle[5:]
    title_s = str(new_title or "").strip()
    if not title_s:
        return None
    items = get_user_doc_templates()
    for item in items:
        if item["id"] == needle:
            item["title"] = title_s
            save_settings({"user_doc_templates": items})
            return dict(item)
    return None


def reorder_user_doc_templates(template_ids: list[str]) -> list[dict]:
    """
    Nutzer-Vorlagen in angegebene ID-Reihenfolge bringen (Drag-Persistenz).
    Unbekannte IDs werden ignoriert; fehlende IDs am Ende angehängt.
    Rückgabe: neue Liste.
    """
    items = get_user_doc_templates()
    if not items:
        return []
    by_id = {t["id"]: t for t in items}
    seen: set[str] = set()
    ordered: list[dict] = []
    for raw in template_ids or []:
        tid = str(raw or "").strip()
        if tid.lower().startswith("user:"):
            tid = tid[5:]
        if not tid or tid in seen or tid not in by_id:
            continue
        ordered.append(by_id[tid])
        seen.add(tid)
    for t in items:
        if t["id"] not in seen:
            ordered.append(t)
    save_settings({"user_doc_templates": ordered})
    return [dict(t) for t in ordered]


def user_templates_dir() -> Path:
    """Ordner für gespiegelte Nutzer-Vorlagen (Explorer)."""
    d = config_dir() / "templates"
    d.mkdir(parents=True, exist_ok=True)
    return d


def sync_user_templates_folder() -> Path:
    """
    Nutzer-Vorlagen als .md-Dateien nach config/templates spiegeln.
    Rückgabe: Ordnerpfad (immer existierend).
    """
    import re

    folder = user_templates_dir()
    # Alte Spiegel-Dateien entfernen (nur *.md mit unserer Marker-Endung)
    for old in folder.glob("*.ildtpl.md"):
        try:
            old.unlink()
        except OSError:
            pass
    for t in get_user_doc_templates():
        tid = t["id"]
        title = t["title"]
        safe = re.sub(r"[^\w\-]+", "_", title, flags=re.UNICODE).strip("_") or "vorlage"
        safe = safe[:48]
        name = f"{safe}.{tid[:8]}.ildtpl.md"
        (folder / name).write_text(t["body"], encoding="utf-8")
    readme = folder / "README.txt"
    readme.write_text(
        "InstantLens Doc — Nutzer-Vorlagen (Spiegel).\n"
        "Dateien *.ildtpl.md werden aus den gespeicherten Vorlagen erzeugt.\n"
        "Bearbeiten hier ändert die App-Vorlagen nicht; bitte in der App speichern.\n"
        "Export/Import: Datei → Neu → Meine Vorlagen → als Zip.\n",
        encoding="utf-8",
    )
    return folder


def export_user_templates_zip(dest: Path | str) -> Path:
    """
    Nutzer-Vorlagen-Ordner als Zip exportieren (templates.json + *.ildtpl.md).
    Rückgabe: Zielpfad.
    """
    import json
    import zipfile

    dest_path = Path(dest)
    folder = sync_user_templates_folder()
    templates = get_user_doc_templates()
    manifest = {"format": "ildtpl-v1", "templates": templates}
    with zipfile.ZipFile(dest_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "templates.json",
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        )
        for f in sorted(folder.glob("*.ildtpl.md")):
            zf.write(f, arcname=f.name)
        readme = folder / "README.txt"
        if readme.is_file():
            zf.write(readme, arcname="README.txt")
    return dest_path


def parse_user_templates_zip(src: Path | str) -> list[dict]:
    """Vorlagen-Einträge aus Zip lesen (ohne Speichern)."""
    import json
    import zipfile

    src_path = Path(src)
    if not src_path.is_file():
        raise FileNotFoundError(str(src_path))
    items: list[dict] = []
    with zipfile.ZipFile(src_path, "r") as zf:
        names = zf.namelist()
        if "templates.json" in names:
            raw = json.loads(zf.read("templates.json").decode("utf-8"))
            payload = raw.get("templates") if isinstance(raw, dict) else raw
            if isinstance(payload, list):
                for entry in payload:
                    if not isinstance(entry, dict):
                        continue
                    title = str(entry.get("title") or "").strip()
                    body = str(entry.get("body") if entry.get("body") is not None else "")
                    tid = str(entry.get("id") or "").strip() or None
                    if not title:
                        continue
                    items.append({"id": tid, "title": title, "body": body})
        if not items:
            for name in names:
                base = Path(name).name
                if not base.endswith(".ildtpl.md"):
                    continue
                try:
                    body = zf.read(name).decode("utf-8")
                except Exception:
                    continue
                # safe.title.tid.ildtpl.md oder title.ildtpl.md
                stem = base[: -len(".ildtpl.md")]
                parts = stem.rsplit(".", 1)
                title = parts[0].replace("_", " ").strip() or stem
                tid = parts[1] if len(parts) == 2 and len(parts[1]) >= 4 else None
                items.append({"id": tid, "title": title, "body": body})
    return items


def find_user_template_import_conflicts(items: list[dict]) -> list[dict]:
    """
    Einträge aus Zip, deren Titel (casefold) schon lokal existieren.
    Rückgabe: [{incoming, existing}, …].
    """
    by_title = {t["title"].casefold(): t for t in get_user_doc_templates()}
    conflicts: list[dict] = []
    seen: set[str] = set()
    for entry in items:
        title = str(entry.get("title") or "").strip()
        key = title.casefold()
        if not key or key in seen:
            continue
        existing = by_title.get(key)
        if existing is None:
            continue
        seen.add(key)
        conflicts.append({"incoming": entry, "existing": existing})
    return conflicts


def dry_run_user_templates_zip_import(src: Path | str) -> list[dict]:
    """
    Dry-Run: Liste was beim Zip-Import überschrieben würde (ohne Schreiben).
    Rückgabe: [{title, action, incoming, existing?}, …]
      action: 'overwrite' | 'add'
    """
    items = parse_user_templates_zip(src)
    by_title = {t["title"].casefold(): t for t in get_user_doc_templates()}
    out: list[dict] = []
    seen: set[str] = set()
    for entry in items:
        title = str(entry.get("title") or "").strip()
        key = title.casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        existing = by_title.get(key)
        if existing is not None:
            out.append(
                {
                    "title": title,
                    "action": "overwrite",
                    "incoming": entry,
                    "existing": existing,
                }
            )
        else:
            out.append(
                {
                    "title": title,
                    "action": "add",
                    "incoming": entry,
                    "existing": None,
                }
            )
    return out


def format_dry_run_conflict_list_txt(
    dry_run_rows: list[dict] | None = None,
    *,
    conflict_titles: list[str] | None = None,
) -> str:
    """
    Konflikt-/Dry-Run-Liste als Klartext (TXT-Export).
    Zeilen: # Header, dann OVERWRITE/ADD + Titel.
    """
    rows = list(dry_run_rows or [])
    overwrite: list[str] = []
    add: list[str] = []
    for row in rows:
        t = str(row.get("title") or "").strip()
        if not t:
            continue
        if str(row.get("action") or "") == "overwrite":
            overwrite.append(t)
        else:
            add.append(t)
    if not overwrite and conflict_titles:
        overwrite = [str(t).strip() for t in conflict_titles if str(t).strip()]
    lines = [
        "InstantLens Doc — Vorlagen-Zip Dry-Run / Konflikte",
        f"Überschreiben: {len(overwrite)}",
        f"Neu: {len(add)}",
        "",
    ]
    for t in overwrite:
        lines.append(f"OVERWRITE\t{t}")
    for t in add:
        lines.append(f"ADD\t{t}")
    if not overwrite and not add:
        lines.append("(keine Einträge)")
    lines.append("")
    return "\n".join(lines)


def export_dry_run_conflict_list_txt(
    dest: Path | str,
    dry_run_rows: list[dict] | None = None,
    *,
    conflict_titles: list[str] | None = None,
) -> Path:
    """Dry-Run-/Konfliktliste nach TXT schreiben. Rückgabe: Zielpfad."""
    path = Path(dest)
    if path.suffix.lower() != ".txt":
        path = path.with_suffix(".txt")
    path.parent.mkdir(parents=True, exist_ok=True)
    text = format_dry_run_conflict_list_txt(
        dry_run_rows, conflict_titles=conflict_titles
    )
    path.write_text(text, encoding="utf-8")
    return path


def import_user_templates_zip(
    src: Path | str,
    *,
    merge: bool = True,
    conflict_mode: str = "overwrite",
) -> list[dict]:
    """
    Vorlagen aus Zip importieren.
    merge=True: hinzufügen/überschreiben (Titel); False: bestehende ersetzen.
    conflict_mode: 'overwrite' (Default) | 'skip' — bei Titel-Konflikt.
    Rückgabe: importierte Einträge.
    """
    items = parse_user_templates_zip(src)
    mode = str(conflict_mode or "overwrite").strip().casefold()
    if mode not in ("overwrite", "skip"):
        mode = "overwrite"
    if not merge:
        for old in list(get_user_doc_templates()):
            delete_user_doc_template(old["id"])
        mode = "overwrite"
    skip_titles: set[str] = set()
    if mode == "skip":
        skip_titles = {
            c["existing"]["title"].casefold()
            for c in find_user_template_import_conflicts(items)
        }
    imported: list[dict] = []
    for entry in items:
        title = str(entry.get("title") or "").strip()
        if title.casefold() in skip_titles:
            continue
        tid = entry.get("id")
        if mode == "overwrite" and title:
            existing = get_user_doc_template(title)
            if existing and existing["title"].casefold() == title.casefold():
                tid = existing["id"]
        saved = save_user_doc_template(
            title=entry["title"],
            body=entry["body"],
            template_id=tid,
        )
        imported.append(saved)
    sync_user_templates_folder()
    return imported


SEARCH_SNIPPET_CONTEXT_MIN = 20
SEARCH_SNIPPET_CONTEXT_MAX = 80
SEARCH_SNIPPET_CONTEXT_DEFAULT = 40

SEARCH_SNIPPET_ELLIPSIS_GUILLEMETS = "guillemets"
SEARCH_SNIPPET_ELLIPSIS_DOTS = "ellipsis"
SEARCH_SNIPPET_ELLIPSIS_DEFAULT = SEARCH_SNIPPET_ELLIPSIS_GUILLEMETS
SEARCH_SNIPPET_ELLIPSIS_CHOICES = (
    (SEARCH_SNIPPET_ELLIPSIS_GUILLEMETS, "«…» Guillemets"),
    (SEARCH_SNIPPET_ELLIPSIS_DOTS, "… Ellipsis"),
)

STATUS_BLINK_KURZ = "kurz"
STATUS_BLINK_AUS = "aus"
STATUS_BLINK_DEFAULT = STATUS_BLINK_KURZ
STATUS_BLINK_CHOICES = (
    (STATUS_BLINK_KURZ, "Kurz (Blink)"),
    (STATUS_BLINK_AUS, "Aus (einmaliger Hinweis)"),
)

MERGE_DIFF_MAX_SIDE_MIN = 12
MERGE_DIFF_MAX_SIDE_MAX = 64
MERGE_DIFF_MAX_SIDE_DEFAULT = 28

SIDECAR_SAVE_DEBOUNCE_MIN_MS = 200
SIDECAR_SAVE_DEBOUNCE_MAX_MS = 1000
SIDECAR_SAVE_DEBOUNCE_DEFAULT_MS = 400


def get_search_snippet_context_chars() -> int:
    """Kontext-Zeichen links/rechts vom Treffer-Match (20–80, Default 40)."""
    try:
        v = int(
            load_settings().get(
                "search_snippet_context_chars", SEARCH_SNIPPET_CONTEXT_DEFAULT
            )
        )
    except (TypeError, ValueError):
        v = SEARCH_SNIPPET_CONTEXT_DEFAULT
    return max(SEARCH_SNIPPET_CONTEXT_MIN, min(SEARCH_SNIPPET_CONTEXT_MAX, v))


def set_search_snippet_context_chars(chars: int) -> int:
    val = max(
        SEARCH_SNIPPET_CONTEXT_MIN,
        min(SEARCH_SNIPPET_CONTEXT_MAX, int(chars)),
    )
    save_settings({"search_snippet_context_chars": val})
    return val


def get_search_snippet_ellipsis_style() -> str:
    """Treffer-Markierung: guillemets («») oder ellipsis (…)."""
    raw = str(
        load_settings().get(
            "search_snippet_ellipsis_style", SEARCH_SNIPPET_ELLIPSIS_DEFAULT
        )
        or SEARCH_SNIPPET_ELLIPSIS_DEFAULT
    ).strip().casefold()
    if raw in ("ellipsis", "…", "...", "dots", "dot"):
        return SEARCH_SNIPPET_ELLIPSIS_DOTS
    return SEARCH_SNIPPET_ELLIPSIS_GUILLEMETS


def set_search_snippet_ellipsis_style(style: str) -> str:
    raw = str(style or "").strip().casefold()
    if raw in ("ellipsis", "…", "...", "dots", "dot"):
        val = SEARCH_SNIPPET_ELLIPSIS_DOTS
    else:
        val = SEARCH_SNIPPET_ELLIPSIS_GUILLEMETS
    save_settings({"search_snippet_ellipsis_style": val})
    return val


def get_status_blink_mode() -> str:
    """Statusleisten-Blink bei pending Debounce: 'kurz' | 'aus'."""
    raw = str(
        load_settings().get("status_blink_mode", STATUS_BLINK_DEFAULT)
        or STATUS_BLINK_DEFAULT
    ).strip().casefold()
    if raw in ("aus", "off", "none", "0", "false", "no"):
        return STATUS_BLINK_AUS
    return STATUS_BLINK_KURZ


def set_status_blink_mode(mode: str) -> str:
    raw = str(mode or "").strip().casefold()
    if raw in ("aus", "off", "none", "0", "false", "no"):
        val = STATUS_BLINK_AUS
    else:
        val = STATUS_BLINK_KURZ
    save_settings({"status_blink_mode": val})
    return val


def get_merge_diff_max_side() -> int:
    """Max. Zeichen je Seite im Ann.-Merge-Diff-Kurztext (12–64, Default 28)."""
    try:
        v = int(
            load_settings().get(
                "merge_diff_max_side", MERGE_DIFF_MAX_SIDE_DEFAULT
            )
        )
    except (TypeError, ValueError):
        v = MERGE_DIFF_MAX_SIDE_DEFAULT
    return max(MERGE_DIFF_MAX_SIDE_MIN, min(MERGE_DIFF_MAX_SIDE_MAX, v))


def set_merge_diff_max_side(chars: int) -> int:
    val = max(
        MERGE_DIFF_MAX_SIDE_MIN,
        min(MERGE_DIFF_MAX_SIDE_MAX, int(chars)),
    )
    save_settings({"merge_diff_max_side": val})
    return val


def get_sidecar_save_debounce_ms() -> int:
    """Sidecar-Save Debounce in ms (200–1000, Default 400)."""
    try:
        v = int(load_settings().get("sidecar_save_debounce_ms", SIDECAR_SAVE_DEBOUNCE_DEFAULT_MS))
    except (TypeError, ValueError):
        v = SIDECAR_SAVE_DEBOUNCE_DEFAULT_MS
    return max(SIDECAR_SAVE_DEBOUNCE_MIN_MS, min(SIDECAR_SAVE_DEBOUNCE_MAX_MS, v))


def set_sidecar_save_debounce_ms(ms: int) -> int:
    val = max(
        SIDECAR_SAVE_DEBOUNCE_MIN_MS,
        min(SIDECAR_SAVE_DEBOUNCE_MAX_MS, int(ms)),
    )
    save_settings({"sidecar_save_debounce_ms": val})
    return val


def get_minimize_to_tray() -> bool:
    return bool(load_settings().get("minimize_to_tray", False))


def set_minimize_to_tray(enabled: bool) -> None:
    save_settings({"minimize_to_tray": bool(enabled)})


def get_page_size_unit() -> str:
    """'mm' oder 'inch' für Seitengrößenanzeige."""
    raw = str(load_settings().get("page_size_unit", "mm") or "mm").lower().strip()
    if raw in ("in", "inch", "inches", '"'):
        return "inch"
    return "mm"


def set_page_size_unit(unit: str) -> str:
    u = "inch" if str(unit or "").lower().strip() in ("in", "inch", "inches", '"') else "mm"
    save_settings({"page_size_unit": u})
    return u


def toggle_page_size_unit() -> str:
    """Wechselt mm ↔ inch und speichert; Rückgabe: neue Einheit."""
    return set_page_size_unit("inch" if get_page_size_unit() == "mm" else "mm")


def get_measure_unit() -> str:
    """Messanzeige-Einheit: 'mm' oder 'px' — 2.1.0."""
    raw = str(load_settings().get("measure_unit", "mm") or "mm").lower().strip()
    if raw in ("px", "pixel", "pixels"):
        return "px"
    return "mm"


def set_measure_unit(unit: str) -> str:
    u = "px" if str(unit or "").lower().strip() in ("px", "pixel", "pixels") else "mm"
    save_settings({"measure_unit": u})
    return u


def toggle_measure_unit() -> str:
    """Wechselt mm ↔ px und speichert; Rückgabe: neue Einheit — 2.1.0."""
    return set_measure_unit("px" if get_measure_unit() == "mm" else "mm")


def get_measure_snap_to_annotation() -> bool:
    """Snap-to-Annotation für Messwerkzeuge — 2.1.1."""
    return bool(load_settings().get("measure_snap_to_annotation", False))


def set_measure_snap_to_annotation(enabled: bool) -> bool:
    v = bool(enabled)
    save_settings({"measure_snap_to_annotation": v})
    return v


def toggle_measure_snap_to_annotation() -> bool:
    """Snap-to-Annotation umschalten — 2.1.1."""
    return set_measure_snap_to_annotation(not get_measure_snap_to_annotation())


def get_ink_smooth() -> bool:
    """Freihand leichte Glättung optional — 2.2.1."""
    return bool(load_settings().get("ink_smooth", False))


def set_ink_smooth(enabled: bool) -> bool:
    v = bool(enabled)
    save_settings({"ink_smooth": v})
    return v


def toggle_ink_smooth() -> bool:
    """Freihand-Glättung umschalten — 2.2.1."""
    return set_ink_smooth(not get_ink_smooth())


INK_SMOOTH_LEICHT = "leicht"
INK_SMOOTH_MITTEL = "mittel"
INK_SMOOTH_STARK = "stark"
INK_SMOOTH_STRENGTH_DEFAULT = INK_SMOOTH_LEICHT
INK_SMOOTH_STRENGTH_CHOICES = (
    (INK_SMOOTH_LEICHT, "Leicht"),
    (INK_SMOOTH_MITTEL, "Mittel"),
    (INK_SMOOTH_STARK, "Stark"),
)
INK_SMOOTH_PASSES = {
    INK_SMOOTH_LEICHT: 1,
    INK_SMOOTH_MITTEL: 2,
    INK_SMOOTH_STARK: 3,
}


def get_ink_smooth_strength() -> str:
    """Glättungsstärke leicht|mittel|stark — 2.2.3."""
    raw = str(
        load_settings().get("ink_smooth_strength", INK_SMOOTH_STRENGTH_DEFAULT)
        or INK_SMOOTH_STRENGTH_DEFAULT
    ).strip().lower()
    if raw in ("stark", "strong", "high", "3"):
        return INK_SMOOTH_STARK
    if raw in ("mittel", "medium", "med", "2"):
        return INK_SMOOTH_MITTEL
    return INK_SMOOTH_LEICHT


def set_ink_smooth_strength(strength: str) -> str:
    """Persistenz Glättungsstärke — 2.2.3."""
    raw = str(strength or "").strip().lower()
    if raw in ("stark", "strong", "high", "3"):
        val = INK_SMOOTH_STARK
    elif raw in ("mittel", "medium", "med", "2"):
        val = INK_SMOOTH_MITTEL
    else:
        val = INK_SMOOTH_LEICHT
    save_settings({"ink_smooth_strength": val})
    return val


def get_ink_smooth_passes() -> int:
    """Passes für aktuelle Glättungsstärke (1–3) — 2.2.3."""
    return int(INK_SMOOTH_PASSES.get(get_ink_smooth_strength(), 1))


def get_measure_labels_persistent() -> bool:
    """Mess-Labels persistent in Sidecar/Overlay halten — 2.1.1."""
    return bool(load_settings().get("measure_labels_persistent", True))


def set_measure_labels_persistent(enabled: bool) -> bool:
    v = bool(enabled)
    save_settings({"measure_labels_persistent": v})
    return v


def get_measure_csv_utf8_bom() -> bool:
    """Messwerte-CSV mit UTF-8-BOM schreiben — 2.1.2."""
    return bool(load_settings().get("measure_csv_utf8_bom", True))


def set_measure_csv_utf8_bom(enabled: bool) -> bool:
    v = bool(enabled)
    save_settings({"measure_csv_utf8_bom": v})
    return v


def get_last_measure_csv_dir() -> Path | None:
    """Zuletzt genutzter Zielordner für Messwerte-CSV — 2.1.2."""
    raw = str(load_settings().get("last_measure_csv_dir", "") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_dir() else (p.parent if p.parent.is_dir() else None)


def set_last_measure_csv_dir(path: str | Path) -> None:
    p = Path(path)
    if p.is_file():
        p = p.parent
    save_settings({"last_measure_csv_dir": str(p)})


DEFAULT_MEASURE_CSV_FILENAME_TEMPLATE = "{stem}_measures.csv"
MEASURE_CSV_KNOWN_PLACEHOLDERS = frozenset({"stem", "date"})
_MEASURE_CSV_ANY_PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")


def get_measure_csv_filename_template() -> str:
    """Dateiname-Template Messwerte-CSV, Default ``{stem}_measures.csv`` — 2.1.3."""
    raw = str(
        load_settings().get(
            "measure_csv_filename_template",
            DEFAULTS.get(
                "measure_csv_filename_template", DEFAULT_MEASURE_CSV_FILENAME_TEMPLATE
            ),
        )
        or ""
    ).strip()
    if not raw:
        return DEFAULT_MEASURE_CSV_FILENAME_TEMPLATE
    raw = raw.replace("/", "_").replace("\\", "_")
    if not raw.lower().endswith(".csv"):
        raw = raw + ".csv"
    return raw


def set_measure_csv_filename_template(template: str) -> str:
    """Messwerte-CSV-Template speichern — 2.1.3."""
    raw = str(template or "").strip() or DEFAULT_MEASURE_CSV_FILENAME_TEMPLATE
    raw = raw.replace("/", "_").replace("\\", "_")
    if not raw.lower().endswith(".csv"):
        raw = raw + ".csv"
    save_settings({"measure_csv_filename_template": raw})
    return raw


def find_invalid_measure_csv_placeholders(template: str) -> list[str]:
    """Unbekannte Platzhalter im Mess-CSV-Template — 2.1.3."""
    seen: set[str] = set()
    out: list[str] = []
    for name in _MEASURE_CSV_ANY_PLACEHOLDER_RE.findall(str(template or "")):
        key = name.strip()
        if not key or key in MEASURE_CSV_KNOWN_PLACEHOLDERS or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def highlight_measure_csv_template_html(template: str) -> str:
    """Template als HTML; ungültige Platzhalter rot — 2.1.3."""
    import html as _html

    raw = str(template or "")
    parts: list[str] = []
    last = 0
    for m in _MEASURE_CSV_ANY_PLACEHOLDER_RE.finditer(raw):
        parts.append(_html.escape(raw[last : m.start()]))
        name = m.group(1).strip()
        token = _html.escape(m.group(0))
        if name and name not in MEASURE_CSV_KNOWN_PLACEHOLDERS:
            parts.append(
                f'<span style="color:#c62828;font-weight:600">{token}</span>'
            )
        else:
            parts.append(token)
        last = m.end()
    parts.append(_html.escape(raw[last:]))
    return "".join(parts) or _html.escape(raw)


def format_measure_csv_filename(
    stem: str,
    *,
    template: str | None = None,
    date: str | None = None,
) -> str:
    """
    Messwerte-CSV-Dateiname aus Template.
    Platzhalter: ``{stem}``, ``{date}`` (YYYY-MM-DD).
    Default ``{stem}_measures.csv`` — 2.1.3.
    """
    from datetime import date as _date

    tpl = (
        template
        if template is not None
        else get_measure_csv_filename_template()
    )
    stem_s = (stem or "dokument").strip() or "dokument"
    date_s = (date if date is not None else _date.today().isoformat()).strip()
    name = str(tpl or DEFAULT_MEASURE_CSV_FILENAME_TEMPLATE).replace(
        "{stem}", stem_s
    ).replace("{date}", date_s)
    name = name.replace("/", "_").replace("\\", "_")
    if not name.lower().endswith(".csv"):
        name = name + ".csv"
    return name or f"{stem_s}_measures.csv"


def get_page_labels_txt_utf8_bom() -> bool:
    """PageLabels-TXT mit UTF-8-BOM schreiben — 2.2.4."""
    return bool(load_settings().get("page_labels_txt_utf8_bom", True))


def set_page_labels_txt_utf8_bom(enabled: bool) -> bool:
    v = bool(enabled)
    save_settings({"page_labels_txt_utf8_bom": v})
    return v


def get_last_page_labels_txt_dir() -> Path | None:
    """Zuletzt genutzter Zielordner für PageLabels-TXT — 2.2.4."""
    raw = str(load_settings().get("last_page_labels_txt_dir", "") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_dir() else (p.parent if p.parent.is_dir() else None)


def set_last_page_labels_txt_dir(path: str | Path) -> None:
    p = Path(path)
    if p.is_file():
        p = p.parent
    save_settings({"last_page_labels_txt_dir": str(p)})


DEFAULT_PAGE_LABELS_TXT_FILENAME_TEMPLATE = "{stem}_labels.txt"
PAGE_LABELS_TXT_KNOWN_PLACEHOLDERS = frozenset({"stem", "date"})
_PAGE_LABELS_TXT_ANY_PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")


def get_page_labels_txt_filename_template() -> str:
    """Dateiname-Template PageLabels-TXT, Default ``{stem}_labels.txt`` — 2.2.4."""
    raw = str(
        load_settings().get(
            "page_labels_txt_filename_template",
            DEFAULTS.get(
                "page_labels_txt_filename_template",
                DEFAULT_PAGE_LABELS_TXT_FILENAME_TEMPLATE,
            ),
        )
        or ""
    ).strip()
    if not raw:
        return DEFAULT_PAGE_LABELS_TXT_FILENAME_TEMPLATE
    raw = raw.replace("/", "_").replace("\\", "_")
    if not raw.lower().endswith(".txt"):
        raw = raw + ".txt"
    return raw


def set_page_labels_txt_filename_template(template: str) -> str:
    """PageLabels-TXT-Template speichern — 2.2.4."""
    raw = str(template or "").strip() or DEFAULT_PAGE_LABELS_TXT_FILENAME_TEMPLATE
    raw = raw.replace("/", "_").replace("\\", "_")
    if not raw.lower().endswith(".txt"):
        raw = raw + ".txt"
    save_settings({"page_labels_txt_filename_template": raw})
    return raw


def find_invalid_page_labels_txt_placeholders(template: str) -> list[str]:
    """Unbekannte Platzhalter im PageLabels-TXT-Template — 2.2.5."""
    seen: set[str] = set()
    out: list[str] = []
    for name in _PAGE_LABELS_TXT_ANY_PLACEHOLDER_RE.findall(str(template or "")):
        key = name.strip()
        if not key or key in PAGE_LABELS_TXT_KNOWN_PLACEHOLDERS or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def highlight_page_labels_txt_template_html(template: str) -> str:
    """Template als HTML; ungültige Platzhalter rot — 2.2.5."""
    import html as _html

    raw = str(template or "")
    parts: list[str] = []
    last = 0
    for m in _PAGE_LABELS_TXT_ANY_PLACEHOLDER_RE.finditer(raw):
        parts.append(_html.escape(raw[last : m.start()]))
        name = m.group(1).strip()
        token = _html.escape(m.group(0))
        if name and name not in PAGE_LABELS_TXT_KNOWN_PLACEHOLDERS:
            parts.append(
                f'<span style="color:#c62828;font-weight:600">{token}</span>'
            )
        else:
            parts.append(token)
        last = m.end()
    parts.append(_html.escape(raw[last:]))
    return "".join(parts) or _html.escape(raw)


def format_page_labels_txt_filename(
    stem: str,
    *,
    template: str | None = None,
    date: str | None = None,
) -> str:
    """
    PageLabels-TXT-Dateiname aus Template.
    Platzhalter: ``{stem}``, ``{date}`` (YYYY-MM-DD).
    Default ``{stem}_labels.txt`` — 2.2.4/2.2.5.
    """
    from datetime import date as _date

    tpl = (
        template
        if template is not None
        else get_page_labels_txt_filename_template()
    )
    stem_s = (stem or "dokument").strip() or "dokument"
    date_s = (date if date is not None else _date.today().isoformat()).strip()
    name = str(tpl or DEFAULT_PAGE_LABELS_TXT_FILENAME_TEMPLATE).replace(
        "{stem}", stem_s
    ).replace("{date}", date_s)
    name = name.replace("/", "_").replace("\\", "_")
    if not name.lower().endswith(".txt"):
        name = name + ".txt"
    return name or f"{stem_s}_labels.txt"


def get_native_ann_import_save_sidecar() -> bool:
    """Nach PDF-Kommentar-Import Sidecar speichern — 2.1.2."""
    return bool(load_settings().get("native_ann_import_save_sidecar", True))


def set_native_ann_import_save_sidecar(enabled: bool) -> bool:
    v = bool(enabled)
    save_settings({"native_ann_import_save_sidecar": v})
    return v


DEFAULT_TEXTLAYER_DIFF_TXT_TEMPLATE = "{stemA}_vs_{stemB}_{mode}.txt"
TEXTLAYER_DIFF_TXT_KNOWN_PLACEHOLDERS = frozenset(
    {"stemA", "stemB", "page", "date", "mode"}
)
_TEXTLAYER_DIFF_TXT_PLACEHOLDER_RE = re.compile(
    r"\{(stemA|stemB|page|date|mode)\}"
)
_TEXTLAYER_DIFF_TXT_ANY_PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")


def get_textlayer_diff_side_by_side() -> bool:
    """Textlayer-Diff Side-by-Side statt Unified — 2.1.2."""
    return bool(load_settings().get("textlayer_diff_side_by_side", False))


def set_textlayer_diff_side_by_side(enabled: bool) -> bool:
    v = bool(enabled)
    save_settings({"textlayer_diff_side_by_side": v})
    return v


def get_textlayer_diff_txt_template() -> str:
    """Dateiname-Template für Textlayer-Diff-TXT — 2.1.2/2.1.3."""
    raw = str(
        load_settings().get(
            "textlayer_diff_txt_template",
            DEFAULTS.get(
                "textlayer_diff_txt_template", DEFAULT_TEXTLAYER_DIFF_TXT_TEMPLATE
            ),
        )
        or DEFAULT_TEXTLAYER_DIFF_TXT_TEMPLATE
    ).strip()
    return raw or DEFAULT_TEXTLAYER_DIFF_TXT_TEMPLATE


def set_textlayer_diff_txt_template(template: str) -> str:
    tpl = str(template or "").strip() or DEFAULT_TEXTLAYER_DIFF_TXT_TEMPLATE
    save_settings({"textlayer_diff_txt_template": tpl})
    return tpl


def find_invalid_textlayer_diff_txt_placeholders(template: str) -> list[str]:
    """Unbekannte Platzhalter im Diff-TXT-Template — 2.1.3."""
    seen: set[str] = set()
    out: list[str] = []
    for name in _TEXTLAYER_DIFF_TXT_ANY_PLACEHOLDER_RE.findall(str(template or "")):
        key = name.strip()
        if not key or key in TEXTLAYER_DIFF_TXT_KNOWN_PLACEHOLDERS or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def highlight_textlayer_diff_txt_template_html(template: str) -> str:
    """Diff-TXT-Template als HTML; ungültige Platzhalter rot — 2.1.3."""
    import html as _html

    raw = str(template or "")
    parts: list[str] = []
    last = 0
    for m in _TEXTLAYER_DIFF_TXT_ANY_PLACEHOLDER_RE.finditer(raw):
        parts.append(_html.escape(raw[last : m.start()]))
        name = m.group(1).strip()
        token = _html.escape(m.group(0))
        if name and name not in TEXTLAYER_DIFF_TXT_KNOWN_PLACEHOLDERS:
            parts.append(
                f'<span style="color:#c62828;font-weight:600">{token}</span>'
            )
        else:
            parts.append(token)
        last = m.end()
    parts.append(_html.escape(raw[last:]))
    return "".join(parts) or _html.escape(raw)


def format_textlayer_diff_txt_filename(
    stem_a: str,
    stem_b: str,
    *,
    template: str | None = None,
    page: int = 1,
    mode: str = "unified",
    date: str | None = None,
) -> str:
    """
    Diff-TXT-Dateiname aus Template ``{stemA}_vs_{stemB}_{mode}.txt``.
    Platzhalter: stemA, stemB, page, date, mode (unified|sidebyside) — 2.1.3.
    """
    from datetime import date as _date

    a = (stem_a or "a").strip() or "a"
    b = (stem_b or "b").strip() or "b"
    p = max(1, int(page))
    d = (date or "").strip() or _date.today().isoformat()
    m = (mode or "unified").strip().lower() or "unified"
    if m in ("side_by_side", "side-by-side", "sbs"):
        m = "sidebyside"
    tpl = (
        (template or DEFAULT_TEXTLAYER_DIFF_TXT_TEMPLATE).strip()
        or DEFAULT_TEXTLAYER_DIFF_TXT_TEMPLATE
    )
    mapping = {
        "stemA": a,
        "stemB": b,
        "page": str(p),
        "date": d,
        "mode": m,
    }

    def _sub(mm: re.Match) -> str:
        return mapping.get(mm.group(1), mm.group(0))

    name = _TEXTLAYER_DIFF_TXT_PLACEHOLDER_RE.sub(_sub, tpl)
    name = name.replace("/", "_").replace("\\", "_")
    if not name.lower().endswith(".txt"):
        name = name + ".txt"
    return name


def get_backup_on_save() -> bool:
    return bool(load_settings().get("backup_on_save", False))


def set_backup_on_save(enabled: bool) -> None:
    save_settings({"backup_on_save": bool(enabled)})


EXPORT_RASTER_DPI_CHOICES = (72, 150, 300)


def get_export_raster_dpi() -> int:
    try:
        v = int(load_settings().get("export_raster_dpi", 150))
    except (TypeError, ValueError):
        v = 150
    if v not in EXPORT_RASTER_DPI_CHOICES:
        # nächster bekannter Wert
        return min(EXPORT_RASTER_DPI_CHOICES, key=lambda x: abs(x - v))
    return v


def set_export_raster_dpi(dpi: int) -> int:
    try:
        v = int(dpi)
    except (TypeError, ValueError):
        v = 150
    if v not in EXPORT_RASTER_DPI_CHOICES:
        v = min(EXPORT_RASTER_DPI_CHOICES, key=lambda x: abs(x - v))
    save_settings({"export_raster_dpi": v})
    return v


def get_print_grayscale() -> bool:
    """Dokumentdruck in Graustufen — 1.0.3."""
    return bool(load_settings().get("print_grayscale", False))


def set_print_grayscale(enabled: bool) -> None:
    save_settings({"print_grayscale": bool(enabled)})


def get_print_preview() -> bool:
    """Druckvorschau (erste Seite) vor Dokumentdruck — 1.0.6. Standard: an."""
    return bool(load_settings().get("print_preview", True))


def set_print_preview(enabled: bool) -> None:
    save_settings({"print_preview": bool(enabled)})


EXPORT_PROFILE_FORMATS = ("PNG", "JPEG")
EXPORT_PROFILES_MAX = 10  # benannte Export-Presets max. 10 — 2.5.1
LAST_EXPORT_PRESET_NAME = "Zuletzt"


def _normalize_export_profile(raw: object) -> dict[str, object] | None:
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or "").strip()
    if not name:
        return None
    try:
        dpi = int(raw.get("dpi", 150))
    except (TypeError, ValueError):
        dpi = 150
    if dpi not in EXPORT_RASTER_DPI_CHOICES:
        dpi = min(EXPORT_RASTER_DPI_CHOICES, key=lambda x: abs(x - dpi))
    fmt = str(raw.get("format") or "PNG").strip().upper()
    if fmt in ("JPG", "JPEG"):
        fmt = "JPEG"
    if fmt not in EXPORT_PROFILE_FORMATS:
        fmt = "PNG"
    target = str(raw.get("target") or "").strip()
    return {"name": name, "dpi": dpi, "format": fmt, "target": target}


def get_export_profiles() -> list[dict[str, object]]:
    """Gespeicherte Export-Profile (Name, DPI, Format, Zielordner)."""
    raw = load_settings().get("export_profiles") or []
    if not isinstance(raw, list):
        return []
    out: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in raw:
        p = _normalize_export_profile(item)
        if not p:
            continue
        key = str(p["name"]).casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
        if len(out) >= EXPORT_PROFILES_MAX:
            break
    return out


def get_export_profile(name: str) -> dict[str, object] | None:
    want = (name or "").strip().casefold()
    if not want:
        return None
    for p in get_export_profiles():
        if str(p["name"]).casefold() == want:
            return p
    return None


def save_export_profile(
    name: str,
    *,
    dpi: int | None = None,
    format: str | None = None,
    target: str | Path | None = None,
    allow_replace: bool = False,
) -> dict[str, object]:
    """
    Profil speichern (DPI/Format/Ziel).

    Duplikat-Namen werden abgelehnt (außer ``allow_replace`` oder Preset „Zuletzt“) — 2.5.2.
    """
    clean_name = (name or "").strip()
    if not clean_name:
        raise ValueError("Profilname fehlt")
    is_last = clean_name.casefold() == LAST_EXPORT_PRESET_NAME.casefold()
    existing = get_export_profile(clean_name)
    if existing is not None and not allow_replace and not is_last:
        raise ValueError(
            f"Preset-Name „{clean_name}“ existiert bereits. "
            "Bitte anderen Namen wählen oder das bestehende Preset löschen."
        )
    if dpi is None:
        dpi = get_export_raster_dpi()
    if format is None:
        format = "PNG"
    fmt = str(format).strip().upper()
    if fmt in ("JPG", "JPEG"):
        fmt = "JPEG"
    if fmt not in EXPORT_PROFILE_FORMATS:
        fmt = "PNG"
    target_s = ""
    if target is not None and str(target).strip():
        t = Path(target).expanduser()
        if t.is_file():
            t = t.parent
        target_s = str(t)
    profile = _normalize_export_profile(
        {"name": clean_name, "dpi": dpi, "format": fmt, "target": target_s}
    )
    assert profile is not None
    profiles = [
        p
        for p in get_export_profiles()
        if str(p["name"]).casefold() != clean_name.casefold()
    ]
    profiles.insert(0, profile)
    profiles = profiles[:EXPORT_PROFILES_MAX]
    save_settings({"export_profiles": profiles, "active_export_profile": clean_name})
    return profile


# Export-Presets JSON Export/Import — 2.5.2
EXPORT_PRESETS_SCHEMA_ID = "ildexportpresets-v1"
EXPORT_PRESETS_VERSION = 1


class ExportPresetsImportError(ValueError):
    """Ungültiges ildexportpresets-v1 JSON."""


class ExportPresetsImportResult:
    """Import-Ergebnis inkl. übersprungener ungültiger Einträge — 2.5.3."""

    def __init__(
        self,
        presets: list[dict[str, object]],
        *,
        skipped_invalid: int = 0,
        skipped_duplicate: int = 0,
    ):
        self.presets = list(presets or [])
        self.skipped_invalid = int(skipped_invalid or 0)
        self.skipped_duplicate = int(skipped_duplicate or 0)

    def __iter__(self):
        return iter(self.presets)

    def __len__(self) -> int:
        return len(self.presets)

    def __bool__(self) -> bool:
        return bool(self.presets)

    def summary_text(self) -> str:
        parts = [f"importiert: {len(self.presets)}"]
        if self.skipped_invalid:
            parts.append(f"ungültig übersprungen: {self.skipped_invalid}")
        if self.skipped_duplicate:
            parts.append(f"Duplikate übersprungen: {self.skipped_duplicate}")
        return ", ".join(parts)


def export_export_presets_dict() -> dict[str, Any]:
    """Alle Export-Presets als Dict (Schema ildexportpresets-v1) — 2.5.2."""
    return {
        "version": EXPORT_PRESETS_VERSION,
        "schema": EXPORT_PRESETS_SCHEMA_ID,
        "presets": get_export_profiles(),
        "active": get_active_export_profile_name(),
    }


def export_export_presets_json(path: str | Path) -> Path:
    """Alle Export-Presets als JSON schreiben — 2.5.2."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(export_export_presets_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return dest


def import_export_presets_dict(
    data: dict,
    *,
    merge: bool = False,
) -> ExportPresetsImportResult:
    """
    Export-Presets aus Dict übernehmen (ildexportpresets-v1) — 2.5.2/2.5.3.

    merge=True: bestehende behalten, neue Namen anhängen (Duplikate überspringen).
    merge=False: alle Presets ersetzen.
    Ungültige Einträge werden übersprungen und gezählt — 2.5.3.
    """
    if not isinstance(data, dict):
        raise ExportPresetsImportError(
            "Export-Presets-JSON muss ein Objekt sein "
            f"(Schema „{EXPORT_PRESETS_SCHEMA_ID}“)."
        )
    ver = data.get("version")
    schema = data.get("schema")
    try:
        ver_i = int(ver)
    except (TypeError, ValueError):
        raise ExportPresetsImportError(
            f"Ungültige Version {ver!r} — erwartet {EXPORT_PRESETS_VERSION} "
            f"(„{EXPORT_PRESETS_SCHEMA_ID}“)."
        ) from None
    if ver_i != EXPORT_PRESETS_VERSION:
        raise ExportPresetsImportError(
            f"Inkompatible Version {ver_i} — erwartet {EXPORT_PRESETS_VERSION} "
            f"(„{EXPORT_PRESETS_SCHEMA_ID}“)."
        )
    if schema is None or str(schema) != EXPORT_PRESETS_SCHEMA_ID:
        raise ExportPresetsImportError(
            f"Ungültiges oder fehlendes Schema „{schema}“ — "
            f"erwartet „{EXPORT_PRESETS_SCHEMA_ID}“."
        )
    raw = data.get("presets", data.get("profiles"))
    if not isinstance(raw, (list, tuple)):
        raise ExportPresetsImportError("Feld „presets“ muss eine Liste sein.")
    incoming: list[dict[str, object]] = []
    seen: set[str] = set()
    skipped_invalid = 0
    skipped_duplicate = 0
    for item in raw:
        p = _normalize_export_profile(item)
        if not p:
            skipped_invalid += 1
            continue
        key = str(p["name"]).casefold()
        if key in seen:
            skipped_duplicate += 1
            continue
        seen.add(key)
        incoming.append(p)
    if merge:
        existing = get_export_profiles()
        existing_keys = {str(p["name"]).casefold() for p in existing}
        merged = list(existing)
        for p in incoming:
            if str(p["name"]).casefold() in existing_keys:
                skipped_duplicate += 1
                continue  # Duplikat-Namen überspringen
            merged.append(p)
            existing_keys.add(str(p["name"]).casefold())
            if len(merged) >= EXPORT_PROFILES_MAX:
                break
        out = merged[:EXPORT_PROFILES_MAX]
    else:
        out = incoming[:EXPORT_PROFILES_MAX]
    active = str(data.get("active") or "").strip()
    if active and not any(str(p["name"]).casefold() == active.casefold() for p in out):
        active = str(out[0]["name"]) if out else ""
    elif not active:
        active = str(out[0]["name"]) if out else ""
    save_settings({"export_profiles": out, "active_export_profile": active})
    return ExportPresetsImportResult(
        out,
        skipped_invalid=skipped_invalid,
        skipped_duplicate=skipped_duplicate,
    )


def import_export_presets_json(
    path: str | Path,
    *,
    merge: bool = False,
) -> ExportPresetsImportResult:
    """Export-Presets aus JSON-Datei laden — 2.5.2/2.5.3."""
    src = Path(path)
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ExportPresetsImportError(
            f"Ungültiges JSON — Datei ist kein gültiges "
            f"„{EXPORT_PRESETS_SCHEMA_ID}“: {e}"
        ) from e
    except OSError as e:
        raise ExportPresetsImportError(str(e)) from e
    return import_export_presets_dict(data, merge=merge)


def delete_export_profile(name: str) -> bool:
    want = (name or "").strip().casefold()
    if not want:
        return False
    profiles = get_export_profiles()
    kept = [p for p in profiles if str(p["name"]).casefold() != want]
    if len(kept) == len(profiles):
        return False
    active = str(load_settings().get("active_export_profile") or "").strip()
    payload: dict[str, Any] = {"export_profiles": kept}
    if active.casefold() == want:
        payload["active_export_profile"] = str(kept[0]["name"]) if kept else ""
    save_settings(payload)
    return True


def move_export_profile(name: str, delta: int) -> bool:
    """Export-Preset in der Liste um ``delta`` Positionen verschieben — 2.5.13."""
    want = (name or "").strip().casefold()
    if not want or not delta:
        return False
    profiles = get_export_profiles()
    idx = next(
        (i for i, p in enumerate(profiles) if str(p["name"]).casefold() == want),
        -1,
    )
    if idx < 0:
        return False
    new_idx = idx + int(delta)
    if new_idx < 0 or new_idx >= len(profiles):
        return False
    item = profiles.pop(idx)
    profiles.insert(new_idx, item)
    save_settings({"export_profiles": profiles})
    return True


def rename_export_profile(old_name: str, new_name: str) -> dict[str, object]:
    """Export-Preset umbenennen (Duplikat ablehnen) — 2.5.4."""
    old = (old_name or "").strip()
    new = (new_name or "").strip()
    if not old:
        raise ValueError("Alter Preset-Name fehlt")
    if not new:
        raise ValueError("Neuer Preset-Name fehlt")
    existing = get_export_profile(old)
    if existing is None:
        raise ValueError(f"Preset „{old}“ nicht gefunden")
    if old.casefold() == new.casefold():
        # Nur Groß/Klein geändert → Namen aktualisieren, Rest behalten
        if str(existing["name"]) == new:
            return dict(existing)
    else:
        clash = get_export_profile(new)
        if clash is not None:
            raise ValueError(
                f"Preset-Name „{new}“ existiert bereits. "
                "Bitte anderen Namen wählen."
            )
    was_active = get_active_export_profile_name().casefold() == old.casefold()
    profiles = get_export_profiles()
    updated: list[dict[str, object]] = []
    for p in profiles:
        if str(p["name"]).casefold() == old.casefold():
            renamed = _normalize_export_profile(
                {
                    "name": new,
                    "dpi": p.get("dpi"),
                    "format": p.get("format"),
                    "target": p.get("target"),
                }
            )
            assert renamed is not None
            updated.append(renamed)
        else:
            updated.append(p)
    payload: dict[str, Any] = {"export_profiles": updated}
    if was_active:
        payload["active_export_profile"] = new
    save_settings(payload)
    out = get_export_profile(new)
    if out is None:
        raise ValueError(f"Umbenennen fehlgeschlagen: „{new}“")
    return out


def duplicate_export_profile(
    name: str, new_name: str | None = None
) -> dict[str, object]:
    """Export-Preset duplizieren (neuer Name, max. Limit) — 2.5.5."""
    src = get_export_profile(name)
    if src is None:
        raise ValueError(f"Preset „{(name or '').strip()}“ nicht gefunden")
    base = (new_name or "").strip() or f"{src['name']} Kopie"
    # Freien Namen finden wenn Kollision
    candidate = base
    n = 2
    while get_export_profile(candidate) is not None:
        candidate = f"{base}_{n}"
        n += 1
        if n > 100:
            raise ValueError("Kein freier Preset-Name für Duplikat gefunden")
    return save_export_profile(
        candidate,
        dpi=int(src.get("dpi") or 150),
        format=str(src.get("format") or "PNG"),
        target=str(src.get("target") or ""),
    )


def get_active_export_profile_name() -> str:
    return str(load_settings().get("active_export_profile") or "").strip()


def export_profile_summary(profile: dict[str, object] | None) -> str:
    """Live-Zusammenfassung DPI · Format · Ziel — 2.5.1."""
    if not profile:
        return "(kein Preset)"
    tip = f"{profile.get('dpi', '?')} DPI · {profile.get('format', '?')}"
    target = str(profile.get("target") or "").strip()
    if target:
        tip += f" · {target}"
    else:
        tip += " · (kein Zielordner)"
    return tip


def export_profile_path_preview(profile: dict[str, object] | None) -> str:
    """Live-Pfad-Vorschau Zielordner eines Export-Presets — 2.5.3."""
    if not profile:
        return "(kein Preset)"
    target = str(profile.get("target") or "").strip()
    if not target:
        return "(kein Zielordner)"
    return target


def apply_export_profile(name: str) -> dict[str, object] | None:
    """Profil anwenden: DPI/Format setzen, Zielordner merken — 2.5.0 Format."""
    profile = get_export_profile(name)
    if not profile:
        return None
    set_export_raster_dpi(int(profile["dpi"]))
    fmt = str(profile.get("format") or "PNG").strip().upper()
    if fmt in ("JPG", "JPEG"):
        fmt = "JPEG"
    if fmt not in EXPORT_PROFILE_FORMATS:
        fmt = "PNG"
    set_last_export_format(fmt)
    target = str(profile.get("target") or "").strip()
    if target and Path(target).is_dir():
        set_last_export_dir(target)
        set_last_page_image_export_dir(target)
    save_settings({"active_export_profile": str(profile["name"])})
    return profile


def get_last_export_format() -> str:
    """Letztes Bild-Export-Format PNG|JPEG — 2.5.0."""
    raw = str(load_settings().get("last_export_format") or "PNG").strip().upper()
    if raw in ("JPG", "JPEG"):
        return "JPEG"
    return "PNG" if raw not in EXPORT_PROFILE_FORMATS else raw


def set_last_export_format(fmt: str) -> str:
    """Export-Format merken (PNG|JPEG) — 2.5.0."""
    f = str(fmt or "PNG").strip().upper()
    if f in ("JPG", "JPEG"):
        f = "JPEG"
    if f not in EXPORT_PROFILE_FORMATS:
        f = "PNG"
    save_settings({"last_export_format": f})
    return f


def remember_last_export_preset(
    *,
    dpi: int | None = None,
    format: str | None = None,
    target: str | Path | None = None,
) -> dict[str, object]:
    """
    Letzte Export-Einstellungen als Preset „Zuletzt“ speichern — 2.5.0.

    Speichert DPI/Format/Pfad und setzt das Profil aktiv.
    """
    if dpi is None:
        dpi = get_export_raster_dpi()
    if format is None:
        format = get_last_export_format()
    profile = save_export_profile(
        LAST_EXPORT_PRESET_NAME,
        dpi=int(dpi),
        format=format,
        target=target,
    )
    set_last_export_format(str(profile["format"]))
    t = str(profile.get("target") or "").strip()
    if t:
        set_last_export_dir(t)
        set_last_page_image_export_dir(t)
    return profile


def get_window_geometry_b64() -> str:
    return str(load_settings().get("window_geometry", "") or "")


def set_window_geometry_b64(data: str) -> None:
    save_settings({"window_geometry": str(data or "")})


def get_window_state_b64() -> str:
    return str(load_settings().get("window_state", "") or "")


def set_window_state_b64(data: str) -> None:
    save_settings({"window_state": str(data or "")})


ANN_COLOR_PRESET_COUNT = 6
_DEFAULT_ANN_PRESETS = [
    "#FFE066",
    "#FF6B6B",
    "#4ECDC4",
    "#5B8DEF",
    "#F5A623",
    "#9B59B6",
]
# Werksfarben (unveränderliche Factory-Defaults) — 0.9.8
ANN_COLOR_PRESET_FACTORY = tuple(_DEFAULT_ANN_PRESETS)

# Vordefinierte Annotation-Farben-Themes (laden → 6 Presets) — 2.5.0
ANN_COLOR_THEMES: dict[str, tuple[str, ...]] = {
    "Markieren": (
        "#FFE066",
        "#FF9F1C",
        "#FF6B6B",
        "#FF85A1",
        "#C3F584",
        "#7BDFF2",
    ),
    "Corporate": (
        "#1B4F72",
        "#2E86C1",
        "#148F77",
        "#5D6D7E",
        "#B7950B",
        "#922B21",
    ),
}
CUSTOM_ANN_COLOR_THEMES_MAX = 20  # benutzerdefinierte Themes max. — 2.5.3


def factory_ann_color_presets() -> list[str]:
    """Werksstandard der 6 Color-Presets (Kopie) — 0.9.8."""
    return list(ANN_COLOR_PRESET_FACTORY)


def _normalize_custom_ann_color_theme(raw: object) -> dict[str, Any] | None:
    """Ein Custom-Theme {name, colors[6]} normalisieren — 2.5.3."""
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or raw.get("theme") or "").strip()
    if not name:
        return None
    colors_raw = raw.get("colors", raw.get("presets"))
    if not isinstance(colors_raw, (list, tuple)):
        return None
    defaults = list(_DEFAULT_ANN_PRESETS)
    colors: list[str] = []
    for i in range(ANN_COLOR_PRESET_COUNT):
        if i < len(colors_raw) and str(colors_raw[i] or "").strip():
            colors.append(_normalize_hex_color(str(colors_raw[i]), defaults[i]))
        else:
            colors.append(defaults[i])
    return {"name": name, "colors": colors}


def get_custom_ann_color_themes() -> list[dict[str, Any]]:
    """Benutzerdefinierte Farben-Themes — 2.5.3."""
    raw = load_settings().get("custom_ann_color_themes") or []
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw:
        theme = _normalize_custom_ann_color_theme(item)
        if not theme:
            continue
        key = str(theme["name"]).casefold()
        if key in seen or key in {k.casefold() for k in ANN_COLOR_THEMES}:
            continue
        seen.add(key)
        out.append(theme)
        if len(out) >= CUSTOM_ANN_COLOR_THEMES_MAX:
            break
    return out


def _save_custom_ann_color_themes(themes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Custom-Themes speichern (max. Limit) — 2.5.3."""
    clean: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in themes:
        theme = _normalize_custom_ann_color_theme(item)
        if not theme:
            continue
        key = str(theme["name"]).casefold()
        if key in seen or key in {k.casefold() for k in ANN_COLOR_THEMES}:
            continue
        seen.add(key)
        clean.append(theme)
        if len(clean) >= CUSTOM_ANN_COLOR_THEMES_MAX:
            break
    save_settings({"custom_ann_color_themes": clean})
    return clean


def _unique_ann_theme_name(base: str, used: set[str]) -> str:
    """Nächsten freien Theme-Namen ``base``, ``base_2``, … — 2.5.3."""
    name = (base or "Theme").strip() or "Theme"
    if name.casefold() not in used:
        return name
    n = 2
    while True:
        candidate = f"{name}_{n}"
        if candidate.casefold() not in used:
            return candidate
        n += 1


def list_ann_color_themes() -> list[str]:
    """Namen vordefinierter + Custom Farben-Themes — 2.5.0/2.5.3."""
    names = list(ANN_COLOR_THEMES.keys())
    for t in get_custom_ann_color_themes():
        names.append(str(t["name"]))
    return names


def is_builtin_ann_color_theme(name: str) -> bool:
    """True wenn Theme fest eingebaut (Markieren/Corporate) — 2.5.4."""
    clean = (name or "").strip()
    return clean in ANN_COLOR_THEMES


def delete_custom_ann_color_theme(name: str) -> bool:
    """Benutzerdefiniertes Farben-Theme löschen (Builtins geschützt) — 2.5.4."""
    clean = (name or "").strip()
    if not clean:
        return False
    if clean in ANN_COLOR_THEMES:
        raise ValueError(
            f"Eingebautes Theme „{clean}“ kann nicht gelöscht werden."
        )
    themes = get_custom_ann_color_themes()
    kept = [t for t in themes if str(t["name"]).casefold() != clean.casefold()]
    if len(kept) == len(themes):
        return False
    _save_custom_ann_color_themes(kept)
    try:
        if get_default_ann_color_theme().casefold() == clean.casefold():
            set_default_ann_color_theme("")
    except Exception:
        pass
    return True


def rename_custom_ann_color_theme(old_name: str, new_name: str) -> dict[str, Any]:
    """Benutzerdefiniertes Farben-Theme umbenennen (Builtins geschützt) — 2.5.5."""
    old = (old_name or "").strip()
    new = (new_name or "").strip()
    if not old:
        raise ValueError("Alter Theme-Name fehlt")
    if not new:
        raise ValueError("Neuer Theme-Name fehlt")
    if old in ANN_COLOR_THEMES:
        raise ValueError(
            f"Eingebautes Theme „{old}“ kann nicht umbenannt werden."
        )
    if new in ANN_COLOR_THEMES:
        raise ValueError(
            f"Name „{new}“ ist für ein eingebautes Theme reserviert."
        )
    themes = get_custom_ann_color_themes()
    existing: dict[str, Any] | None = None
    for t in themes:
        if str(t["name"]).casefold() == old.casefold():
            existing = t
            break
    if existing is None:
        raise ValueError(f"Custom-Theme „{old}“ nicht gefunden")
    if old.casefold() != new.casefold():
        for t in themes:
            if str(t["name"]).casefold() == new.casefold():
                raise ValueError(
                    f"Theme-Name „{new}“ existiert bereits. "
                    "Bitte anderen Namen wählen."
                )
    updated: list[dict[str, Any]] = []
    renamed: dict[str, Any] | None = None
    for t in themes:
        if str(t["name"]).casefold() == old.casefold():
            colors = list(t.get("colors") or [])
            renamed = _normalize_custom_ann_color_theme(
                {"name": new, "colors": colors}
            )
            if renamed is None:
                raise ValueError(f"Umbenennen fehlgeschlagen: „{new}“")
            updated.append(renamed)
        else:
            updated.append(t)
    # Default vor Speichern lesen (get_default braucht existierendes Theme) — 2.5.5
    raw_default = str(load_settings().get("default_ann_color_theme") or "").strip()
    was_default = raw_default.casefold() == old.casefold()
    _save_custom_ann_color_themes(updated)
    if was_default and renamed is not None:
        set_default_ann_color_theme(str(renamed["name"]))
    if renamed is None:
        raise ValueError(f"Umbenennen fehlgeschlagen: „{new}“")
    return renamed


def duplicate_custom_ann_color_theme(
    name: str, new_name: str | None = None
) -> dict[str, Any]:
    """Benutzerdefiniertes Farben-Theme duplizieren (Builtins geschützt) — 2.5.6."""
    src_name = (name or "").strip()
    if not src_name:
        raise ValueError("Theme-Name fehlt")
    if src_name in ANN_COLOR_THEMES:
        raise ValueError(
            f"Eingebautes Theme „{src_name}“ kann nicht dupliziert werden."
        )
    themes = get_custom_ann_color_themes()
    src: dict[str, Any] | None = None
    for t in themes:
        if str(t["name"]).casefold() == src_name.casefold():
            src = t
            break
    if src is None:
        raise ValueError(f"Custom-Theme „{src_name}“ nicht gefunden")
    if len(themes) >= CUSTOM_ANN_COLOR_THEMES_MAX:
        raise ValueError(
            f"Maximal {CUSTOM_ANN_COLOR_THEMES_MAX} Custom-Themes erlaubt."
        )
    used = {str(t["name"]).casefold() for t in themes}
    used.update(k.casefold() for k in ANN_COLOR_THEMES)
    base = (new_name or "").strip() or f"{src['name']} Kopie"
    candidate = _unique_ann_theme_name(base, used)
    dup = _normalize_custom_ann_color_theme(
        {"name": candidate, "colors": list(src.get("colors") or [])}
    )
    if dup is None:
        raise ValueError(f"Duplizieren fehlgeschlagen: „{candidate}“")
    updated = list(themes) + [dup]
    _save_custom_ann_color_themes(updated)
    return dup


def get_ann_color_theme(name: str) -> list[str] | None:
    """Theme-Farben (6) oder None — 2.5.0/2.5.3."""
    clean = (name or "").strip()
    colors = ANN_COLOR_THEMES.get(clean)
    if colors:
        return list(colors)
    for t in get_custom_ann_color_themes():
        if str(t["name"]).casefold() == clean.casefold():
            return list(t["colors"])
    return None


def apply_ann_color_theme(name: str) -> list[str]:
    """Theme laden und als Color-Presets speichern (ildcolors-v1) — 2.5.0."""
    colors = get_ann_color_theme(name)
    if not colors:
        raise ValueError(f"Unbekanntes Farben-Theme: {name!r}")
    set_ann_color_presets(colors)
    return list(get_ann_color_presets())


def get_default_ann_color_theme() -> str:
    """Gespeichertes Default-Farben-Theme (Name) — 2.5.1."""
    raw = str(load_settings().get("default_ann_color_theme") or "").strip()
    if raw and get_ann_color_theme(raw) is not None:
        return raw
    return ""


def set_default_ann_color_theme(name: str) -> str:
    """Farben-Theme als Default speichern (leer = kein Default) — 2.5.1."""
    clean = (name or "").strip()
    if clean and get_ann_color_theme(clean) is None:
        raise ValueError(f"Unbekanntes Farben-Theme: {clean!r}")
    save_settings({"default_ann_color_theme": clean})
    return clean


# Farben-Theme JSON (eigenes Schema, getrennt von Color-Presets) — 2.5.2
ANN_COLORS_THEME_SCHEMA_ID = "ildcolors-theme-v1"
ANN_COLORS_THEME_VERSION = 1


class AnnColorsThemeImportResult:
    """Theme-Import inkl. Log + Zusammenfassung — 2.5.3."""

    def __init__(
        self,
        colors: list[str],
        themes: list[dict[str, Any]] | None = None,
        log: list[str] | None = None,
    ):
        self.colors = list(colors or [])
        self.themes = list(themes or [])
        self.log = list(log or [])

    def __iter__(self):
        return iter(self.colors)

    def __len__(self) -> int:
        return len(self.colors)

    def __bool__(self) -> bool:
        return bool(self.colors)

    def summary_counts(self) -> dict[str, int]:
        imported = skipped = renamed = 0
        for line in self.log:
            s = str(line or "")
            if s.startswith("übersprungen:"):
                skipped += 1
            elif s.startswith("umbenannt:"):
                renamed += 1
            elif s.startswith("importiert:") or s.startswith("ersetzt/importiert:"):
                imported += 1
        return {
            "imported": imported,
            "skipped": skipped,
            "renamed": renamed,
        }

    def summary_text(self) -> str:
        c = self.summary_counts()
        return (
            f"importiert: {c['imported']}, "
            f"übersprungen: {c['skipped']}, "
            f"umbenannt: {c['renamed']}"
        )

    def log_text(self, *, include_summary: bool = True) -> str:
        lines: list[str] = []
        if include_summary:
            lines.append(f"Zusammenfassung: {self.summary_text()}")
            lines.append("")
        if self.log:
            lines.extend(str(x) for x in self.log)
        else:
            lines.append("(keine Einträge)")
        return "\n".join(lines) + "\n"


def export_ann_colors_theme_import_log_txt(
    path: str | Path,
    result: AnnColorsThemeImportResult,
    *,
    utf8_bom: bool = True,
) -> Path:
    """Theme Import-Log als TXT speichern — 2.5.3."""
    path = Path(path)
    body = (
        "# InstantLens Doc Farben-Themes Import-Log\n"
        f"# schema: {ANN_COLORS_THEME_SCHEMA_ID}-import-log\n"
        f"# {result.summary_text()}\n"
        "\n"
        f"{result.log_text(include_summary=True)}"
    )
    path.write_bytes(body.encode("utf-8-sig" if utf8_bom else "utf-8"))
    return path


def export_ann_color_theme_dict(name: str | None = None) -> dict[str, Any]:
    """Theme oder aktuelle Presets als ildcolors-theme-v1 Dict — 2.5.2."""
    theme_name = (name or "").strip()
    if theme_name:
        colors = get_ann_color_theme(theme_name)
        if not colors:
            raise ValueError(f"Unbekanntes Farben-Theme: {theme_name!r}")
    else:
        colors = get_ann_color_presets()
        theme_name = get_default_ann_color_theme()
    payload: dict[str, Any] = {
        "version": ANN_COLORS_THEME_VERSION,
        "schema": ANN_COLORS_THEME_SCHEMA_ID,
        "colors": list(colors),
    }
    if theme_name:
        payload["theme"] = theme_name
    return payload


def export_ann_color_theme_json(
    path: str | Path, name: str | None = None
) -> Path:
    """Farben-Theme als JSON exportieren (ildcolors-theme-v1) — 2.5.2."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(export_ann_color_theme_dict(name), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return dest


def _validate_ann_color_theme_dict(data: dict) -> None:
    """Schema ildcolors-theme-v1 prüfen — klare DE-Fehler — 2.5.2/2.5.3."""
    if not isinstance(data, dict):
        raise AnnColorsImportError(
            "Farben-Theme-JSON muss ein Objekt sein "
            f"(Schema „{ANN_COLORS_THEME_SCHEMA_ID}“)."
        )
    ver = data.get("version")
    schema = data.get("schema")
    try:
        ver_i = int(ver)
    except (TypeError, ValueError):
        raise AnnColorsImportError(
            f"Ungültige Version {ver!r} — erwartet {ANN_COLORS_THEME_VERSION} "
            f"(„{ANN_COLORS_THEME_SCHEMA_ID}“)."
        ) from None
    if ver_i != ANN_COLORS_THEME_VERSION:
        raise AnnColorsImportError(
            f"Inkompatible Version {ver_i} — erwartet {ANN_COLORS_THEME_VERSION} "
            f"(„{ANN_COLORS_THEME_SCHEMA_ID}“)."
        )
    if schema is None or str(schema) != ANN_COLORS_THEME_SCHEMA_ID:
        raise AnnColorsImportError(
            f"Ungültiges oder fehlendes Schema „{schema}“ — "
            f"erwartet „{ANN_COLORS_THEME_SCHEMA_ID}“. "
            f"(Color-Presets nutzen „{ANN_COLORS_SCHEMA_ID}“.)"
        )
    themes_raw = data.get("themes")
    if themes_raw is not None:
        if not isinstance(themes_raw, (list, tuple)):
            raise AnnColorsImportError(
                "Feld „themes“ muss eine Liste sein "
                f"(Schema „{ANN_COLORS_THEME_SCHEMA_ID}“)."
            )
        return
    raw = data.get("colors", data.get("presets"))
    if not isinstance(raw, (list, tuple)):
        raise AnnColorsImportError(
            "Feld „colors“ fehlt oder ist ungültig — erwartet eine Liste mit 6 Farben "
            "oder Feld „themes“."
        )


def _extract_incoming_ann_themes(data: dict) -> list[dict[str, Any]]:
    """Einzel- oder Mehrfach-Themes aus Import-Dict — 2.5.3."""
    themes_raw = data.get("themes")
    incoming: list[dict[str, Any]] = []
    if isinstance(themes_raw, (list, tuple)):
        for item in themes_raw:
            theme = _normalize_custom_ann_color_theme(item)
            if theme:
                incoming.append(theme)
        return incoming
    # Einzeltheme: colors + optional theme-Name
    raw = data.get("colors", data.get("presets"))
    name = str(data.get("theme") or data.get("name") or "Import").strip() or "Import"
    theme = _normalize_custom_ann_color_theme({"name": name, "colors": raw})
    if theme:
        incoming.append(theme)
    return incoming


def _apply_theme_colors_to_presets(
    colors_raw: list[str], *, merge: bool
) -> list[str]:
    """6 Farben in Color-Presets übernehmen (Merge-Slots oder Ersetzen) — 2.5.2."""
    current = get_ann_color_presets()
    defaults = list(_DEFAULT_ANN_PRESETS)
    out: list[str] = list(current if merge else defaults)
    for i in range(ANN_COLOR_PRESET_COUNT):
        if i >= len(colors_raw):
            if not merge:
                out[i] = defaults[i]
            continue
        c = str(colors_raw[i] or "").strip()
        if not c:
            if not merge:
                out[i] = defaults[i]
            continue
        out[i] = _normalize_hex_color(c, defaults[i])
    return set_ann_color_presets(out)


def import_ann_color_theme_dict(
    data: dict,
    *,
    merge: bool = False,
    set_default: bool = False,
    on_collision: str = "skip",
) -> AnnColorsThemeImportResult:
    """
    Farben-Theme(s) aus Dict importieren (ildcolors-theme-v1) — 2.5.2/2.5.3.

    merge=True: Custom-Themes anhängen; bei Namenskollision skip/rename (_2);
    merge=False: Custom-Themes ersetzen.
    Color-Presets: erster akzeptierter Theme wird angewandt (Slots Merge/Ersetzen).
    Rückgabe: AnnColorsThemeImportResult (Farben + Import-Log).
    """
    _validate_ann_color_theme_dict(data)
    incoming = _extract_incoming_ann_themes(data)
    if not incoming:
        raise AnnColorsImportError(
            "Keine gültigen Farben-Themes im Import "
            f"(Schema „{ANN_COLORS_THEME_SCHEMA_ID}“)."
        )

    mode = str(on_collision or "skip").strip().lower()
    if mode not in ("reject", "skip", "rename"):
        mode = "skip"

    log: list[str] = []
    builtin_keys = {k.casefold() for k in ANN_COLOR_THEMES}
    existing = get_custom_ann_color_themes()
    apply_colors: list[str] | None = None

    if merge:
        existing_keys = {str(t["name"]).casefold() for t in existing} | builtin_keys
        accepted: list[dict[str, Any]] = []
        for theme in incoming:
            orig = str(theme["name"])
            key = orig.casefold()
            if key in existing_keys:
                if mode == "reject":
                    raise AnnColorsImportError(f"Name bereits vergeben: {orig}")
                if mode == "skip":
                    log.append(f"übersprungen: {orig}")
                    # Bei Skip trotzdem Presets aus erstem Theme anwenden wenn noch keins
                    if apply_colors is None and key in builtin_keys:
                        apply_colors = list(theme["colors"])
                    continue
                new_name = _unique_ann_theme_name(orig, existing_keys)
                theme = dict(theme)
                theme["name"] = new_name
                log.append(f"umbenannt: {orig} → {new_name}")
                existing_keys.add(new_name.casefold())
                accepted.append(theme)
                if apply_colors is None:
                    apply_colors = list(theme["colors"])
            else:
                log.append(f"importiert: {orig}")
                existing_keys.add(key)
                accepted.append(theme)
                if apply_colors is None:
                    apply_colors = list(theme["colors"])
        combined = existing + accepted
        if len(combined) > CUSTOM_ANN_COLOR_THEMES_MAX:
            combined = combined[:CUSTOM_ANN_COLOR_THEMES_MAX]
        themes = _save_custom_ann_color_themes(combined)
    else:
        # Ersetzen: Custom-Themes verwerfen, Builtins bleiben
        accepted = []
        used: set[str] = set(builtin_keys)
        for theme in incoming:
            orig = str(theme["name"])
            key = orig.casefold()
            if key in used:
                if mode == "skip":
                    log.append(f"übersprungen: {orig}")
                    if apply_colors is None and key in builtin_keys:
                        apply_colors = list(theme["colors"])
                    continue
                if mode == "rename":
                    new_name = _unique_ann_theme_name(orig, used)
                    theme = dict(theme)
                    theme["name"] = new_name
                    log.append(f"umbenannt: {orig} → {new_name}")
                    used.add(new_name.casefold())
                    accepted.append(theme)
                    if apply_colors is None:
                        apply_colors = list(theme["colors"])
                    continue
                # reject → Builtin-Namen als Custom überspringen, Farben trotzdem anwenden
                log.append(f"übersprungen: {orig}")
                if apply_colors is None:
                    apply_colors = list(theme["colors"])
                continue
            log.append(f"ersetzt/importiert: {orig}")
            used.add(key)
            accepted.append(theme)
            if apply_colors is None:
                apply_colors = list(theme["colors"])
        themes = _save_custom_ann_color_themes(accepted)

    if apply_colors is None and incoming:
        apply_colors = list(incoming[0]["colors"])
    colors = _apply_theme_colors_to_presets(apply_colors or [], merge=merge)

    theme_name = str(data.get("theme") or data.get("name") or "").strip()
    if set_default and theme_name and get_ann_color_theme(theme_name) is not None:
        set_default_ann_color_theme(theme_name)
    return AnnColorsThemeImportResult(list(colors), themes, log)


def import_ann_color_theme_json(
    path: str | Path,
    *,
    merge: bool = False,
    set_default: bool = False,
    on_collision: str = "skip",
) -> AnnColorsThemeImportResult:
    """Farben-Theme aus JSON-Datei importieren — 2.5.2/2.5.3."""
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as e:
        raise AnnColorsImportError(
            f"Farben-Theme-Datei konnte nicht gelesen werden: {e}"
        ) from e
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise AnnColorsImportError(
            f"Ungültiges JSON — Datei ist kein gültiges "
            f"„{ANN_COLORS_THEME_SCHEMA_ID}“: {e}"
        ) from e
    if not isinstance(data, dict):
        raise AnnColorsImportError(
            "Farben-Theme-JSON muss ein Objekt sein "
            f"(Schema „{ANN_COLORS_THEME_SCHEMA_ID}“)."
        )
    return import_ann_color_theme_dict(
        data, merge=merge, set_default=set_default, on_collision=on_collision
    )


def get_welcome_recent_filter() -> str:
    """Persistierter Welcome-Recent-Filtertext — 2.5.1."""
    return str(load_settings().get("welcome_recent_filter") or "")


def set_welcome_recent_filter(text: str) -> str:
    """Welcome-Recent-Filter persistieren — 2.5.1."""
    val = str(text or "")
    save_settings({"welcome_recent_filter": val})
    return val


WELCOME_TAG_FILTER_SORT_CHOICES: tuple[str, ...] = ("az", "freq")


def get_welcome_tag_filter_sort() -> str:
    """Quick-Tag Sortierung: az | freq — 2.5.6."""
    raw = str(load_settings().get("welcome_tag_filter_sort") or "az").strip().casefold()
    return raw if raw in WELCOME_TAG_FILTER_SORT_CHOICES else "az"


def set_welcome_tag_filter_sort(mode: str) -> str:
    """Quick-Tag Sortierung speichern (az|freq) — 2.5.6."""
    val = str(mode or "az").strip().casefold()
    if val not in WELCOME_TAG_FILTER_SORT_CHOICES:
        val = "az"
    save_settings({"welcome_tag_filter_sort": val})
    return val


def _normalize_hex_color(color: str, fallback: str = "#888888") -> str:
    c = (color or "").strip()
    if not c:
        return fallback
    if not c.startswith("#"):
        c = "#" + c
    if len(c) < 4:
        return fallback
    return c.upper() if len(c) >= 7 else c


def get_ann_color_presets() -> list[str]:
    """Sechs Favoriten-Farben für Annotationen (Stroke/Fill Quick-Bar) — 0.9.5."""
    raw = load_settings().get("ann_color_presets")
    defaults = list(_DEFAULT_ANN_PRESETS)
    if not isinstance(raw, list):
        return defaults
    out: list[str] = []
    for i in range(ANN_COLOR_PRESET_COUNT):
        if i < len(raw):
            out.append(_normalize_hex_color(str(raw[i]), defaults[i]))
        else:
            out.append(defaults[i])
    return out


def set_ann_color_presets(colors: list[str]) -> list[str]:
    defaults = list(_DEFAULT_ANN_PRESETS)
    cleaned: list[str] = []
    for i in range(ANN_COLOR_PRESET_COUNT):
        if i < len(colors):
            cleaned.append(_normalize_hex_color(str(colors[i]), defaults[i]))
        else:
            cleaned.append(defaults[i])
    save_settings({"ann_color_presets": cleaned})
    return cleaned


def set_ann_color_preset(index: int, color: str) -> list[str]:
    """Einzelnen Favoriten-Slot (0..5) setzen — 0.9.5: 6 Farben."""
    presets = get_ann_color_presets()
    i = max(0, min(ANN_COLOR_PRESET_COUNT - 1, int(index)))
    presets[i] = _normalize_hex_color(color, presets[i])
    return set_ann_color_presets(presets)


def reset_ann_color_preset(index: int) -> list[str]:
    """Einzelnen Favoriten-Slot auf Werkstandard zurücksetzen — 0.9.6."""
    defaults = list(_DEFAULT_ANN_PRESETS)
    i = max(0, min(ANN_COLOR_PRESET_COUNT - 1, int(index)))
    return set_ann_color_preset(i, defaults[i])


def reset_ann_color_presets() -> list[str]:
    """Alle 6 Color-Presets auf Werkstandard (Factory) — 0.9.6/0.9.8."""
    return set_ann_color_presets(factory_ann_color_presets())


# Color-Presets JSON Export/Import — 0.9.7
ANN_COLORS_SCHEMA_ID = "ildcolors-v1"
ANN_COLORS_VERSION = 1


class AnnColorsImportError(ValueError):
    """Ungültiges ildcolors-v1 Preset-JSON."""


def export_ann_color_presets_dict() -> dict[str, Any]:
    """Color-Presets als exportierbares Dict (Schema ildcolors-v1) — 0.9.7."""
    return {
        "version": ANN_COLORS_VERSION,
        "schema": ANN_COLORS_SCHEMA_ID,
        "colors": get_ann_color_presets(),
    }


def export_ann_color_presets_json(path: str | Path) -> Path:
    """Color-Presets als JSON-Datei schreiben (ildcolors-v1)."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(export_ann_color_presets_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return dest


def import_ann_color_presets_dict(
    data: dict,
    *,
    merge: bool = False,
) -> list[str]:
    """
    Color-Presets aus Dict übernehmen (ildcolors-v1).
    merge=True: nur nicht-leere Einträge der Datei überschreiben.
    """
    if not isinstance(data, dict):
        raise AnnColorsImportError("Color-Presets-JSON muss ein Objekt sein.")
    ver = data.get("version")
    schema = data.get("schema")
    try:
        ver_i = int(ver)
    except (TypeError, ValueError):
        raise AnnColorsImportError(
            f"Ungültige Version {ver!r} — erwartet {ANN_COLORS_VERSION} ({ANN_COLORS_SCHEMA_ID})."
        ) from None
    if ver_i != ANN_COLORS_VERSION:
        raise AnnColorsImportError(
            f"Inkompatible Version {ver_i} — erwartet {ANN_COLORS_VERSION} ({ANN_COLORS_SCHEMA_ID})."
        )
    if schema is not None and str(schema) != ANN_COLORS_SCHEMA_ID:
        raise AnnColorsImportError(
            f"Inkompatibles Schema „{schema}“ — erwartet „{ANN_COLORS_SCHEMA_ID}“."
        )
    raw = data.get("colors", data.get("presets"))
    if not isinstance(raw, (list, tuple)):
        raise AnnColorsImportError("Feld „colors“ muss eine Liste sein.")
    current = get_ann_color_presets()
    defaults = list(_DEFAULT_ANN_PRESETS)
    out: list[str] = list(current if merge else defaults)
    for i in range(ANN_COLOR_PRESET_COUNT):
        if i >= len(raw):
            if not merge:
                out[i] = defaults[i]
            continue
        c = str(raw[i] or "").strip()
        if not c:
            if not merge:
                out[i] = defaults[i]
            continue
        out[i] = _normalize_hex_color(c, defaults[i])
    return set_ann_color_presets(out)


def import_ann_color_presets_json(
    path: str | Path,
    *,
    merge: bool = False,
) -> list[str]:
    """Color-Presets aus JSON-Datei laden (ildcolors-v1)."""
    src = Path(path)
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise AnnColorsImportError(f"Ungültiges JSON: {e}") from e
    except OSError as e:
        raise AnnColorsImportError(str(e)) from e
    return import_ann_color_presets_dict(data, merge=merge)


def get_restore_session_on_start() -> bool:
    return bool(load_settings().get("restore_session_on_start", True))


def set_restore_session_on_start(enabled: bool) -> None:
    save_settings({"restore_session_on_start": bool(enabled)})


def get_restore_window_geometry_on_start() -> bool:
    """Fenstergeometrie/-state beim Start wiederherstellen (Toggle)."""
    return bool(load_settings().get("restore_window_geometry_on_start", True))


def set_restore_window_geometry_on_start(enabled: bool) -> None:
    save_settings({"restore_window_geometry_on_start": bool(enabled)})



THUMB_LAZY_THRESHOLD_CHOICES = (25, 50, 100)
THUMB_PREFETCH_RADIUS_CHOICES = (1, 2, 3)
THUMB_PREFETCH_CANCEL_MS_CHOICES = (50, 90, 150, 250)
THUMB_PREFETCH_RADIUS_DEFAULT = 2
THUMB_PREFETCH_CANCEL_MS_DEFAULT = 90
THUMB_CACHE_MAX_MB_CHOICES = (25, 50, 100, 200, 500)
THUMB_CACHE_MAX_MB_DEFAULT = 100
THUMB_CACHE_PRUNE_MODE_ON_WRITE = "on_write"
THUMB_CACHE_PRUNE_MODE_INTERVAL = "interval"
THUMB_CACHE_PRUNE_MODE_CHOICES = (
    THUMB_CACHE_PRUNE_MODE_ON_WRITE,
    THUMB_CACHE_PRUNE_MODE_INTERVAL,
)
THUMB_CACHE_PRUNE_INTERVAL_MIN_CHOICES = (5, 15, 30, 60)
THUMB_CACHE_PRUNE_INTERVAL_MIN_DEFAULT = 15


def get_thumb_cache_max_mb() -> int:
    """Max. Thumbnail-Disk-Cache Größe in MB (25/50/100/200/500) — 2.4.1."""
    try:
        v = int(
            load_settings().get(
                "thumb_cache_max_mb", THUMB_CACHE_MAX_MB_DEFAULT
            )
        )
    except (TypeError, ValueError):
        v = THUMB_CACHE_MAX_MB_DEFAULT
    if v not in THUMB_CACHE_MAX_MB_CHOICES:
        return min(THUMB_CACHE_MAX_MB_CHOICES, key=lambda x: abs(x - v))
    return v


def set_thumb_cache_max_mb(mb: int) -> int:
    try:
        v = int(mb)
    except (TypeError, ValueError):
        v = THUMB_CACHE_MAX_MB_DEFAULT
    if v not in THUMB_CACHE_MAX_MB_CHOICES:
        v = min(THUMB_CACHE_MAX_MB_CHOICES, key=lambda x: abs(x - v))
    save_settings({"thumb_cache_max_mb": v})
    # Auto-Prune bei neuem Limit + Status/Log — 2.4.3
    try:
        from instantlensdoc.core.thumb_cache import auto_prune_thumb_cache

        auto_prune_thumb_cache(announce=True)
    except Exception:
        pass
    return v


def get_thumb_cache_debug_hits() -> bool:
    """Hit/Miss optional in Statusleiste anzeigen — 2.4.1."""
    return bool(load_settings().get("thumb_cache_debug_hits", False))


def set_thumb_cache_debug_hits(enabled: bool) -> None:
    save_settings({"thumb_cache_debug_hits": bool(enabled)})


def get_thumb_cache_prune_mode() -> str:
    """Auto-Prune: ``on_write`` (Default) oder ``interval`` — 2.4.3."""
    raw = str(
        load_settings().get(
            "thumb_cache_prune_mode", THUMB_CACHE_PRUNE_MODE_ON_WRITE
        )
        or THUMB_CACHE_PRUNE_MODE_ON_WRITE
    ).strip().lower()
    if raw not in THUMB_CACHE_PRUNE_MODE_CHOICES:
        return THUMB_CACHE_PRUNE_MODE_ON_WRITE
    return raw


def set_thumb_cache_prune_mode(mode: str) -> str:
    """Auto-Prune-Modus speichern — 2.4.3."""
    raw = str(mode or THUMB_CACHE_PRUNE_MODE_ON_WRITE).strip().lower()
    if raw not in THUMB_CACHE_PRUNE_MODE_CHOICES:
        raw = THUMB_CACHE_PRUNE_MODE_ON_WRITE
    save_settings({"thumb_cache_prune_mode": raw})
    return raw


def get_thumb_cache_prune_interval_min() -> int:
    """Auto-Prune Intervall in Minuten (5/15/30/60) — 2.4.3."""
    try:
        v = int(
            load_settings().get(
                "thumb_cache_prune_interval_min",
                THUMB_CACHE_PRUNE_INTERVAL_MIN_DEFAULT,
            )
        )
    except (TypeError, ValueError):
        v = THUMB_CACHE_PRUNE_INTERVAL_MIN_DEFAULT
    if v not in THUMB_CACHE_PRUNE_INTERVAL_MIN_CHOICES:
        return min(
            THUMB_CACHE_PRUNE_INTERVAL_MIN_CHOICES, key=lambda x: abs(x - v)
        )
    return v


def set_thumb_cache_prune_interval_min(minutes: int) -> int:
    """Auto-Prune Intervall speichern — 2.4.3."""
    try:
        v = int(minutes)
    except (TypeError, ValueError):
        v = THUMB_CACHE_PRUNE_INTERVAL_MIN_DEFAULT
    if v not in THUMB_CACHE_PRUNE_INTERVAL_MIN_CHOICES:
        v = min(
            THUMB_CACHE_PRUNE_INTERVAL_MIN_CHOICES, key=lambda x: abs(x - v)
        )
    save_settings({"thumb_cache_prune_interval_min": v})
    return v


def get_thumb_cache_prune_toast() -> bool:
    """Auto-Prune Status-Toast optional (Default an) — 2.4.4."""
    return bool(load_settings().get("thumb_cache_prune_toast", True))


def set_thumb_cache_prune_toast(enabled: bool) -> None:
    """Auto-Prune Toast an/aus speichern — 2.4.4."""
    save_settings({"thumb_cache_prune_toast": bool(enabled)})


def get_sync_scroll_status_indicator() -> bool:
    """Sync-Scroll an/aus in Statusleiste anzeigen — 2.4.1."""
    return bool(load_settings().get("sync_scroll_status_indicator", True))


def set_sync_scroll_status_indicator(enabled: bool) -> None:
    save_settings({"sync_scroll_status_indicator": bool(enabled)})


def get_last_ann_template_id() -> str:
    """Zuletzt angewandte Annotation-Vorlage (id) — 2.4.2."""
    return str(load_settings().get("last_ann_template_id", "") or "").strip()


def set_last_ann_template_id(template_id: str | None) -> str:
    """Merkt zuletzt angewandte Annotation-Vorlage — 2.4.2."""
    tid = str(template_id or "").strip()
    save_settings({"last_ann_template_id": tid})
    return tid


DEFAULT_SHORTCUTS_TXT_FILENAME_TEMPLATE = "{date}_shortcuts.txt"
SHORTCUTS_TXT_KNOWN_PLACEHOLDERS = frozenset({"date"})
_SHORTCUTS_TXT_ANY_PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")


def get_last_shortcuts_txt_dir() -> Path | None:
    """Zuletzt genutzter Zielordner für F1 Shortcuts-TXT — 2.4.2."""
    raw = str(load_settings().get("last_shortcuts_txt_dir", "") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_dir() else (p.parent if p.parent.is_dir() else None)


def set_last_shortcuts_txt_dir(path: str | Path) -> None:
    """F1 Shortcuts-TXT-Zielordner merken — 2.4.2."""
    p = Path(path)
    if p.is_file():
        p = p.parent
    save_settings({"last_shortcuts_txt_dir": str(p)})


def get_shortcuts_txt_filename_template() -> str:
    """Dateiname-Template F1 Shortcuts-TXT, Default ``{date}_shortcuts.txt`` — 2.4.2."""
    raw = str(
        load_settings().get(
            "shortcuts_txt_filename_template",
            DEFAULTS.get(
                "shortcuts_txt_filename_template",
                DEFAULT_SHORTCUTS_TXT_FILENAME_TEMPLATE,
            ),
        )
        or ""
    ).strip()
    if not raw:
        return DEFAULT_SHORTCUTS_TXT_FILENAME_TEMPLATE
    raw = raw.replace("/", "_").replace("\\", "_")
    if not raw.lower().endswith(".txt"):
        raw = raw + ".txt"
    return raw


def set_shortcuts_txt_filename_template(template: str) -> str:
    """F1 Shortcuts-TXT-Template speichern — 2.4.2."""
    raw = str(template or "").strip() or DEFAULT_SHORTCUTS_TXT_FILENAME_TEMPLATE
    raw = raw.replace("/", "_").replace("\\", "_")
    if not raw.lower().endswith(".txt"):
        raw = raw + ".txt"
    save_settings({"shortcuts_txt_filename_template": raw})
    return raw


def format_shortcuts_txt_filename(
    *,
    template: str | None = None,
    date: str | None = None,
) -> str:
    """
    F1 Shortcuts-TXT-Dateiname aus Template.
    Platzhalter: ``{date}`` (YYYY-MM-DD).
    Default ``{date}_shortcuts.txt`` — 2.4.2/2.4.3.
    """
    from datetime import date as _date

    tpl = (
        template
        if template is not None
        else get_shortcuts_txt_filename_template()
    )
    date_s = (date if date is not None else _date.today().isoformat()).strip()
    name = str(tpl or DEFAULT_SHORTCUTS_TXT_FILENAME_TEMPLATE).replace(
        "{date}", date_s
    )
    name = name.replace("/", "_").replace("\\", "_")
    if not name.lower().endswith(".txt"):
        name = name + ".txt"
    return name or f"{date_s}_shortcuts.txt"


def find_invalid_shortcuts_txt_placeholders(template: str) -> list[str]:
    """Unbekannte Platzhalter im F1-Shortcuts-TXT-Template — 2.4.3."""
    seen: set[str] = set()
    out: list[str] = []
    for name in _SHORTCUTS_TXT_ANY_PLACEHOLDER_RE.findall(str(template or "")):
        key = name.strip()
        if not key or key in SHORTCUTS_TXT_KNOWN_PLACEHOLDERS or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def highlight_shortcuts_txt_template_html(template: str) -> str:
    """Template als HTML; ungültige Platzhalter rot — 2.4.3."""
    import html as _html

    raw = str(template or "")
    parts: list[str] = []
    last = 0
    for m in _SHORTCUTS_TXT_ANY_PLACEHOLDER_RE.finditer(raw):
        parts.append(_html.escape(raw[last : m.start()]))
        name = m.group(1).strip()
        token = _html.escape(m.group(0))
        if name and name not in SHORTCUTS_TXT_KNOWN_PLACEHOLDERS:
            parts.append(
                f'<span style="color:#c62828;font-weight:600">{token}</span>'
            )
        else:
            parts.append(token)
        last = m.end()
    parts.append(_html.escape(raw[last:]))
    return "".join(parts) or _html.escape(raw)


def get_thumb_lazy_threshold() -> int:
    """Seiten-Schwellwert für Thumbnail-Lazy-Load (25/50/100, Default 50)."""
    try:
        v = int(load_settings().get("thumb_lazy_threshold", 50))
    except (TypeError, ValueError):
        v = 50
    if v not in THUMB_LAZY_THRESHOLD_CHOICES:
        return min(THUMB_LAZY_THRESHOLD_CHOICES, key=lambda x: abs(x - v))
    return v


def set_thumb_lazy_threshold(threshold: int) -> int:
    try:
        v = int(threshold)
    except (TypeError, ValueError):
        v = 50
    if v not in THUMB_LAZY_THRESHOLD_CHOICES:
        v = min(THUMB_LAZY_THRESHOLD_CHOICES, key=lambda x: abs(x - v))
    save_settings({"thumb_lazy_threshold": v})
    return v


def get_thumb_prefetch_radius() -> int:
    """Prefetch-Radius um Viewport (±1/2/3, Default 2) — 1.3.3."""
    try:
        v = int(
            load_settings().get(
                "thumb_prefetch_radius", THUMB_PREFETCH_RADIUS_DEFAULT
            )
        )
    except (TypeError, ValueError):
        v = THUMB_PREFETCH_RADIUS_DEFAULT
    if v not in THUMB_PREFETCH_RADIUS_CHOICES:
        return min(THUMB_PREFETCH_RADIUS_CHOICES, key=lambda x: abs(x - v))
    return v


def set_thumb_prefetch_radius(radius: int) -> int:
    try:
        v = int(radius)
    except (TypeError, ValueError):
        v = THUMB_PREFETCH_RADIUS_DEFAULT
    if v not in THUMB_PREFETCH_RADIUS_CHOICES:
        v = min(THUMB_PREFETCH_RADIUS_CHOICES, key=lambda x: abs(x - v))
    save_settings({"thumb_prefetch_radius": v})
    return v


def get_thumb_prefetch_cancel_ms() -> int:
    """Cancel-Debounce bei schnellem Thumb-Scroll (ms) — 1.3.3."""
    try:
        v = int(
            load_settings().get(
                "thumb_prefetch_cancel_ms", THUMB_PREFETCH_CANCEL_MS_DEFAULT
            )
        )
    except (TypeError, ValueError):
        v = THUMB_PREFETCH_CANCEL_MS_DEFAULT
    if v not in THUMB_PREFETCH_CANCEL_MS_CHOICES:
        return min(THUMB_PREFETCH_CANCEL_MS_CHOICES, key=lambda x: abs(x - v))
    return v


def set_thumb_prefetch_cancel_ms(ms: int) -> int:
    try:
        v = int(ms)
    except (TypeError, ValueError):
        v = THUMB_PREFETCH_CANCEL_MS_DEFAULT
    if v not in THUMB_PREFETCH_CANCEL_MS_CHOICES:
        v = min(THUMB_PREFETCH_CANCEL_MS_CHOICES, key=lambda x: abs(x - v))
    save_settings({"thumb_prefetch_cancel_ms": v})
    return v


def get_forms_csv_visible_only() -> bool:
    """Default für Forms-CSV „nur sichtbare/gefilterte Zeilen“ — 1.3.5."""
    return bool(load_settings().get("forms_csv_visible_only", False))


def set_forms_csv_visible_only(enabled: bool) -> bool:
    val = bool(enabled)
    save_settings({"forms_csv_visible_only": val})
    return val


# Tabellen-OCR CSV / Stempel-Standard — 1.9.1
OCR_TABLE_CSV_DELIMITERS: tuple[str, ...] = (";", ",", "\t")
OCR_TABLE_CSV_DELIMITER_LABELS: dict[str, str] = {
    ";": "Semikolon (;)",
    ",": "Komma (,)",
    "\t": "Tab",
}


def get_default_stamp_image() -> str:
    """Dateiname des Standard-Stempelbilds (leer = keiner) — 1.9.1."""
    return str(load_settings().get("default_stamp_image", "") or "").strip()


def set_default_stamp_image(name: str | None) -> str:
    """Standard-Stempel setzen (nur Basename) — 1.9.1."""
    val = Path(str(name or "")).name.strip() if name else ""
    save_settings({"default_stamp_image": val})
    return val


def get_last_used_stamp() -> dict:
    """Zuletzt verwendeter Stempel (kind/text/color/image) — 1.9.2."""
    s = load_settings()
    kind = str(s.get("last_used_stamp_kind", "") or "").strip().lower()
    if kind not in ("text", "image"):
        kind = ""
    return {
        "kind": kind,
        "text": str(s.get("last_used_stamp_text", "") or ""),
        "color": str(s.get("last_used_stamp_color", "#C0392B") or "#C0392B"),
        "image": str(s.get("last_used_stamp_image", "") or "").strip(),
    }


def set_last_used_stamp(
    *,
    kind: str,
    text: str = "",
    color: str = "#C0392B",
    image: str = "",
) -> dict:
    """Merkt zuletzt verwendeten Stempel für Quick-Stempel — 1.9.2."""
    k = str(kind or "").strip().lower()
    if k not in ("text", "image"):
        k = "text" if text else ("image" if image else "")
    payload = {
        "last_used_stamp_kind": k,
        "last_used_stamp_text": str(text or ""),
        "last_used_stamp_color": str(color or "#C0392B"),
        "last_used_stamp_image": Path(str(image or "")).name.strip() if image else "",
    }
    save_settings(payload)
    return get_last_used_stamp()


def get_last_quick_stamp_opacity() -> float | None:
    """Zuletzt gemerkte Quick-Stempel-Deckkraft (wie Signatur), oder None — 1.9.4."""
    raw = load_settings().get("last_quick_stamp_opacity", None)
    if raw is None or raw == "":
        return None
    try:
        op = float(raw)
    except (TypeError, ValueError):
        return None
    return max(0.05, min(1.0, op))


def set_last_quick_stamp_opacity(opacity: float) -> float:
    """Quick-Stempel-Deckkraft merken (wie Signatur) — 1.9.4."""
    try:
        op = float(opacity)
    except (TypeError, ValueError):
        op = 1.0
    op = max(0.05, min(1.0, op))
    save_settings({"last_quick_stamp_opacity": op})
    return op


def get_last_quick_stamp_zoom() -> float | None:
    """Zuletzt gemerkter Quick-Stempel-Seitenzoom (wie Signatur-Vorschau), oder None — 1.9.4."""
    raw = load_settings().get("last_quick_stamp_zoom", None)
    if raw is None or raw == "":
        return None
    try:
        z = float(raw)
    except (TypeError, ValueError):
        return None
    return max(0.1, min(8.0, z))


def set_last_quick_stamp_zoom(zoom: float) -> float:
    """Quick-Stempel-Seitenzoom merken (wie Signatur) — 1.9.4."""
    try:
        z = float(zoom)
    except (TypeError, ValueError):
        z = 1.0
    z = max(0.1, min(8.0, z))
    save_settings({"last_quick_stamp_zoom": z})
    return z


def get_ocr_table_csv_delimiter() -> str:
    """Trennzeichen für Tabellen-OCR→CSV (;/,/Tab) — 1.9.1."""
    raw = str(load_settings().get("ocr_table_csv_delimiter", ";") or ";")
    if raw in ("\\t", "tab", "TAB"):
        raw = "\t"
    if raw not in OCR_TABLE_CSV_DELIMITERS:
        return ";"
    return raw


def set_ocr_table_csv_delimiter(delimiter: str) -> str:
    raw = str(delimiter or ";")
    if raw in ("\\t", "tab", "TAB"):
        raw = "\t"
    if raw not in OCR_TABLE_CSV_DELIMITERS:
        raw = ";"
    save_settings({"ocr_table_csv_delimiter": raw})
    return raw


def get_ocr_table_csv_utf8_bom() -> bool:
    """UTF-8 BOM für Tabellen-OCR→CSV (Default an) — 1.9.1."""
    return bool(load_settings().get("ocr_table_csv_utf8_bom", True))


def set_ocr_table_csv_utf8_bom(enabled: bool) -> bool:
    val = bool(enabled)
    save_settings({"ocr_table_csv_utf8_bom": val})
    return val


def get_last_ocr_table_csv_dir() -> Path | None:
    """Zuletzt genutzter Zielordner für Tabellen-OCR CSV — 1.9.1."""
    raw = str(load_settings().get("last_ocr_table_csv_dir", "") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_dir() else None


def set_last_ocr_table_csv_dir(path: str | Path) -> None:
    p = Path(path)
    if p.is_file():
        p = p.parent
    save_settings({"last_ocr_table_csv_dir": str(p)})


def get_last_portfolio_extract_dir() -> Path | None:
    """Zuletzt genutzter Zielordner für Portfolio-Extrakt — 2.0.2."""
    raw = str(load_settings().get("last_portfolio_extract_dir", "") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_dir() else None


def set_last_portfolio_extract_dir(path: str | Path) -> None:
    """Portfolio-Extrakt-Zielordner merken — 2.0.2."""
    p = Path(path)
    if p.is_file():
        p = p.parent
    save_settings({"last_portfolio_extract_dir": str(p)})


DEFAULT_MULTI_DOC_CSV_FILENAME_TEMPLATE = "{date}_multisearch.csv"
MULTI_DOC_CSV_KNOWN_PLACEHOLDERS = frozenset({"date", "query"})
_MULTI_DOC_CSV_ANY_PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")


def get_last_multi_doc_csv_dir() -> Path | None:
    """Zuletzt genutzter Zielordner für Multi-Doc-Suche CSV — 2.0.3."""
    raw = str(load_settings().get("last_multi_doc_csv_dir", "") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_dir() else None


def set_last_multi_doc_csv_dir(path: str | Path) -> None:
    """Multi-Doc-CSV-Zielordner merken — 2.0.3."""
    p = Path(path)
    if p.is_file():
        p = p.parent
    save_settings({"last_multi_doc_csv_dir": str(p)})


def get_multi_doc_csv_filename_template() -> str:
    """Dateiname-Template Multi-Doc-CSV, Default ``{date}_multisearch.csv`` — 2.0.3/2.0.4."""
    raw = str(
        load_settings().get(
            "multi_doc_csv_filename_template",
            DEFAULTS["multi_doc_csv_filename_template"],
        )
        or ""
    ).strip()
    if not raw:
        return DEFAULT_MULTI_DOC_CSV_FILENAME_TEMPLATE
    raw = raw.replace("/", "_").replace("\\", "_")
    if not raw.lower().endswith(".csv"):
        raw = raw + ".csv"
    return raw


def set_multi_doc_csv_filename_template(template: str) -> str:
    """Multi-Doc-CSV-Template speichern — 2.0.3/2.0.4."""
    raw = str(template or "").strip() or DEFAULT_MULTI_DOC_CSV_FILENAME_TEMPLATE
    raw = raw.replace("/", "_").replace("\\", "_")
    if not raw.lower().endswith(".csv"):
        raw = raw + ".csv"
    save_settings({"multi_doc_csv_filename_template": raw})
    return raw


def sanitize_multi_doc_csv_query(query: str | None) -> str:
    """Suchbegriff für Dateiname sichern (max. 40 Zeichen) — 2.0.4."""
    raw = str(query or "").strip() or "search"
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in raw)
    safe = safe.strip("._") or "search"
    return safe[:40]


def find_invalid_multi_doc_csv_placeholders(template: str) -> list[str]:
    """Unbekannte Platzhalter im Multi-Doc-CSV-Template — 2.0.4."""
    seen: set[str] = set()
    out: list[str] = []
    for name in _MULTI_DOC_CSV_ANY_PLACEHOLDER_RE.findall(str(template or "")):
        key = name.strip()
        if not key or key in MULTI_DOC_CSV_KNOWN_PLACEHOLDERS or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def highlight_multi_doc_csv_template_html(template: str) -> str:
    """Template als HTML; ungültige Platzhalter rot — 2.0.4."""
    import html as _html

    raw = str(template or "")
    parts: list[str] = []
    last = 0
    for m in _MULTI_DOC_CSV_ANY_PLACEHOLDER_RE.finditer(raw):
        parts.append(_html.escape(raw[last : m.start()]))
        name = m.group(1).strip()
        token = _html.escape(m.group(0))
        if name and name not in MULTI_DOC_CSV_KNOWN_PLACEHOLDERS:
            parts.append(
                f'<span style="color:#c62828;font-weight:600">{token}</span>'
            )
        else:
            parts.append(token)
        last = m.end()
    parts.append(_html.escape(raw[last:]))
    return "".join(parts) or _html.escape(raw)


def format_multi_doc_csv_filename(
    *,
    template: str | None = None,
    date: str | None = None,
    query: str | None = None,
) -> str:
    """
    Multi-Doc-CSV-Dateiname aus Template.
    Platzhalter: ``{date}`` (YYYY-MM-DD), ``{query}`` (sanitized).
    Default ``{date}_multisearch.csv`` — 2.0.3/2.0.4.
    """
    from datetime import date as _date

    tpl = (
        template
        if template is not None
        else get_multi_doc_csv_filename_template()
    )
    date_s = (date if date is not None else _date.today().isoformat()).strip()
    query_s = sanitize_multi_doc_csv_query(query)
    name = str(tpl or DEFAULT_MULTI_DOC_CSV_FILENAME_TEMPLATE).replace(
        "{date}", date_s
    ).replace("{query}", query_s)
    name = name.replace("/", "_").replace("\\", "_")
    if not name.lower().endswith(".csv"):
        name = name + ".csv"
    return name or DEFAULT_MULTI_DOC_CSV_FILENAME_TEMPLATE.replace(
        "{date}", date_s
    )


def get_redaction_bake_continue_on_sidecar_skip() -> bool:
    """Default: PDF-Bake bei Sidecar-Fehler fortsetzen — 1.3.6."""
    return bool(load_settings().get("redaction_bake_continue_on_sidecar_skip", True))


def set_redaction_bake_continue_on_sidecar_skip(enabled: bool) -> bool:
    val = bool(enabled)
    save_settings({"redaction_bake_continue_on_sidecar_skip": val})
    return val


def get_redaction_preview_opacity() -> float:
    """Deckkraft der Schwärzungs-Vorschau (0.05–1.0, Default 0.90)."""
    try:
        v = float(load_settings().get("redaction_preview_opacity", 0.90))
    except (TypeError, ValueError):
        v = 0.90
    return max(0.05, min(1.0, v))


def get_true_redact_strip_metadata() -> bool:
    """Metadaten beim echten Schwärzen entfernen — Default an — 2.6.0."""
    return bool(load_settings().get("true_redact_strip_metadata", True))


def set_true_redact_strip_metadata(enabled: bool) -> bool:
    """Persistiert true_redact_strip_metadata — 2.6.0."""
    val = bool(enabled)
    save_settings({"true_redact_strip_metadata": val})
    return val


def get_true_redact_dpi() -> int:
    """Raster-DPI für echtes Schwärzen (72–600, Default 150) — 2.6.0."""
    try:
        v = int(load_settings().get("true_redact_dpi", 150))
    except (TypeError, ValueError):
        v = 150
    return max(72, min(600, v))


def set_true_redact_dpi(dpi: int) -> int:
    """Persistiert true_redact_dpi — 2.6.0."""
    try:
        v = int(dpi)
    except (TypeError, ValueError):
        v = 150
    v = max(72, min(600, v))
    save_settings({"true_redact_dpi": v})
    return v


def set_redaction_preview_opacity(opacity: float) -> float:
    try:
        v = float(opacity)
    except (TypeError, ValueError):
        v = 0.90
    v = max(0.05, min(1.0, v))
    save_settings({"redaction_preview_opacity": round(v, 4)})
    return v


PDF_THUMBNAIL_SCALE_CHOICES = (0.12, 0.18, 0.24)


def get_pdf_thumbnail_scale() -> float:
    """Render-Scale für Sidebar-Thumbnails (Default 0.18)."""
    try:
        v = float(load_settings().get("pdf_thumbnail_scale", 0.18))
    except (TypeError, ValueError):
        v = 0.18
    if v not in PDF_THUMBNAIL_SCALE_CHOICES:
        return min(PDF_THUMBNAIL_SCALE_CHOICES, key=lambda x: abs(x - v))
    return v


def set_pdf_thumbnail_scale(scale: float) -> float:
    try:
        v = float(scale)
    except (TypeError, ValueError):
        v = 0.18
    if v not in PDF_THUMBNAIL_SCALE_CHOICES:
        v = min(PDF_THUMBNAIL_SCALE_CHOICES, key=lambda x: abs(x - v))
    save_settings({"pdf_thumbnail_scale": v})
    return v


def pdf_thumbnail_icon_size(scale: float | None = None) -> tuple[int, int]:
    """Icon-Breite/-Höhe aus Thumbnail-Scale (Basis 72×96 bei 0.18)."""
    s = float(scale if scale is not None else get_pdf_thumbnail_scale())
    factor = s / 0.18
    w = max(48, min(160, int(round(72 * factor))))
    h = max(64, min(214, int(round(96 * factor))))
    return w, h


TEXT_ENCODING_CHOICES = ("auto", "utf-8", "latin-1")


def get_editor_text_encoding() -> str:
    """Standard-Encoding für Editor-Öffnen/Speichern (auto | utf-8 | latin-1)."""
    from instantlensdoc.core.documents import normalize_text_encoding

    raw = str(load_settings().get("editor_text_encoding", "auto") or "auto")
    return normalize_text_encoding(raw)


def set_editor_text_encoding(encoding: str) -> str:
    from instantlensdoc.core.documents import normalize_text_encoding

    enc = normalize_text_encoding(encoding)
    save_settings({"editor_text_encoding": enc})
    return enc


def get_skip_splash() -> bool:
    """Quiet startup: Splash-Screen überspringen."""
    return bool(load_settings().get("skip_splash", False))


def set_skip_splash(enabled: bool) -> None:
    save_settings({"skip_splash": bool(enabled)})


def get_spellcheck_dict_path() -> str:
    """Pfad zur lokalen Rechtschreib-Wortliste (eine Zeile = ein Wort)."""
    return str(load_settings().get("spellcheck_dict_path", "") or "").strip()


def set_spellcheck_dict_path(path: str | Path | None) -> str:
    raw = str(path or "").strip()
    save_settings({"spellcheck_dict_path": raw})
    try:
        from instantlensdoc.core.spellcheck import clear_wordlist_cache

        clear_wordlist_cache()
    except Exception:
        pass
    return raw


def get_editor_trim_trailing_whitespace() -> bool:
    return bool(load_settings().get("editor_trim_trailing_whitespace", False))


def set_editor_trim_trailing_whitespace(enabled: bool) -> None:
    save_settings({"editor_trim_trailing_whitespace": bool(enabled)})


def get_editor_trim_whitespace_on_paste() -> bool:
    return bool(load_settings().get("editor_trim_whitespace_on_paste", False))


def set_editor_trim_whitespace_on_paste(enabled: bool) -> None:
    save_settings({"editor_trim_whitespace_on_paste": bool(enabled)})


def _default_toolbar_groups() -> dict[str, bool]:
    raw = DEFAULTS.get("pdf_toolbar_groups") or {}
    return {k: bool(raw.get(k, True)) for k in PDF_TOOLBAR_GROUP_LABELS}


def get_pdf_toolbar_groups() -> dict[str, bool]:
    raw = load_settings().get("pdf_toolbar_groups")
    out = _default_toolbar_groups()
    if isinstance(raw, dict):
        for key in out:
            if key in raw:
                out[key] = bool(raw[key])
    return out


def set_pdf_toolbar_groups(groups: dict[str, bool]) -> dict[str, bool]:
    base = _default_toolbar_groups()
    if isinstance(groups, dict):
        for key in base:
            if key in groups:
                base[key] = bool(groups[key])
    save_settings({"pdf_toolbar_groups": base})
    return base
