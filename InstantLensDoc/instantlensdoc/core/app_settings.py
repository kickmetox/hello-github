"""Persistente App-Einstellungen (Theme, OCR, Pfade, Export, Zoom, Autosave)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from instantlensdoc.config import config_dir

SETTINGS_NAME = "ui_settings.json"

ThemeMode = Literal["light", "dark", "system"]
UiLang = Literal["de", "en"]

DEFAULTS: dict[str, Any] = {
    "theme": "system",  # System folgen; manuell light/dark Override — 1.4.0
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
    "minimize_to_tray": False,
    "page_size_unit": "mm",
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
    "thumb_prefetch_radius": 2,
    "thumb_prefetch_cancel_ms": 90,
    "forms_csv_visible_only": False,  # CSV-Export Default „nur sichtbare“ — 1.3.5
    "redaction_bake_continue_on_sidecar_skip": True,  # Bake fortsetzen merken — 1.3.6
    "redaction_preview_opacity": 0.90,
    "editor_text_encoding": "auto",
    "skip_splash": False,
    "spellcheck_dict_path": "",
    "show_page_boxes": False,
    "show_page_number_overlay": False,
    "page_number_overlay_opacity": 0.59,
    "page_number_overlay_font_size": 11,
    "page_number_overlay_position": "bottom-center",
    "page_number_overlay_format": "{page} / {pages}",
    "page_number_overlay_start": 1,
    "page_number_overlay_skip_edges": False,
    "show_printer_marks": False,
    "annotations_locked": False,
    "editor_snippets": [
        "Sehr geehrte Damen und Herren,\n\n",
        "Mit freundlichen Grüßen\n",
        "— Notiz —\n",
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
    lang = str(load_settings().get("ui_lang", "de")).lower()
    return "en" if lang.startswith("en") else "de"


def set_ui_lang(lang: str) -> None:
    save_settings({"ui_lang": "en" if str(lang).lower().startswith("en") else "de"})


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


def get_annotations_locked() -> bool:
    """Annotationen gesperrt (nicht per Drag verschiebbar)."""
    return bool(load_settings().get("annotations_locked", False))


def set_annotations_locked(locked: bool) -> None:
    save_settings({"annotations_locked": bool(locked)})


EDITOR_SNIPPET_COUNT = 3
_DEFAULT_EDITOR_SNIPPETS = [
    "Sehr geehrte Damen und Herren,\n\n",
    "Mit freundlichen Grüßen\n",
    "— Notiz —\n",
]


def get_editor_snippets() -> list[str]:
    """Drei gespeicherte Textbausteine für den Editor."""
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
            cleaned.append(defaults[i])
    save_settings({"editor_snippets": cleaned})
    return cleaned


def set_editor_snippet(index: int, text: str) -> list[str]:
    """Einzelnen Textbaustein-Slot (0..2) setzen."""
    snippets = get_editor_snippets()
    i = max(0, min(EDITOR_SNIPPET_COUNT - 1, int(index)))
    snippets[i] = str(text if text is not None else "")
    return set_editor_snippets(snippets)


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
EXPORT_PROFILES_MAX = 12


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
) -> dict[str, object]:
    """Profil speichern/überschreiben (DPI/Format/Ziel)."""
    clean_name = (name or "").strip()
    if not clean_name:
        raise ValueError("Profilname fehlt")
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
    profiles = [p for p in get_export_profiles() if str(p["name"]).casefold() != clean_name.casefold()]
    profiles.insert(0, profile)
    profiles = profiles[:EXPORT_PROFILES_MAX]
    save_settings({"export_profiles": profiles, "active_export_profile": clean_name})
    return profile


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


def get_active_export_profile_name() -> str:
    return str(load_settings().get("active_export_profile") or "").strip()


def apply_export_profile(name: str) -> dict[str, object] | None:
    """Profil anwenden: DPI setzen, Zielordner als last_export_dir merken."""
    profile = get_export_profile(name)
    if not profile:
        return None
    set_export_raster_dpi(int(profile["dpi"]))
    target = str(profile.get("target") or "").strip()
    if target and Path(target).is_dir():
        set_last_export_dir(target)
    save_settings({"active_export_profile": str(profile["name"])})
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


def factory_ann_color_presets() -> list[str]:
    """Werksstandard der 6 Color-Presets (Kopie) — 0.9.8."""
    return list(ANN_COLOR_PRESET_FACTORY)


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
