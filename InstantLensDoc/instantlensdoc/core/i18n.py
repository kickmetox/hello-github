"""Minimale UI-Mehrsprachigkeit DE/EN."""

from __future__ import annotations

from typing import Literal

UiLang = Literal["de", "en"]

_STRINGS: dict[str, dict[UiLang, str]] = {
    "settings": {"de": "Einstellungen", "en": "Settings"},
    "settings_title": {"de": "InstantLens Doc — Anwendungseinstellungen", "en": "InstantLens Doc — Application settings"},
    "theme": {"de": "Design", "en": "Theme"},
    "theme_light": {"de": "Hell", "en": "Light"},
    "theme_dark": {"de": "Dunkel", "en": "Dark"},
    "ui_lang": {"de": "Oberflächensprache", "en": "UI language"},
    "ocr_lang": {"de": "OCR-Sprache (Standard)", "en": "OCR language (default)"},
    "batch_dir": {"de": "Batch-Ausgabeordner", "en": "Batch output folder"},
    "open_dir": {"de": "Standard-Ordner (Öffnen)", "en": "Default folder (Open)"},
    "export_jpeg_q": {"de": "Export JPEG-Qualität", "en": "Export JPEG quality"},
    "export_page": {"de": "Export PDF-Seitenformat", "en": "Export PDF page size"},
    "default_zoom": {"de": "Standard-Zoom (PDF)", "en": "Default zoom (PDF)"},
    "autosave_interval": {"de": "Autosave-Intervall", "en": "Autosave interval"},
    "update_check": {"de": "Update-Hinweis beim Start", "en": "Update notice on start"},
    "pick_dir": {"de": "Ordner wählen", "en": "Choose folder"},
    "meta_title": {"de": "PDF-Metadaten", "en": "PDF metadata"},
    "page_size_title": {"de": "Seitengröße / Zuschneiden", "en": "Page size / Crop"},
    "redact_bake": {"de": "Schwärzung einbrennen", "en": "Bake redactions"},
    "redact_none": {"de": "Keine Schwärzungs-Annotationen.", "en": "No redaction annotations."},
    "redact_clear": {"de": "Schwärzungs-Annotationen löschen", "en": "Clear redaction annotations"},
    "update_title": {"de": "Update-Check", "en": "Update check"},
    "help": {"de": "Hilfe", "en": "Help"},
    "about": {"de": "Info", "en": "About"},
    "keyboard": {"de": "Tastaturhilfe", "en": "Keyboard shortcuts"},
    "planned": {"de": "Geplant", "en": "Planned"},
    "lang_de": {"de": "Deutsch", "en": "German"},
    "lang_en": {"de": "Englisch", "en": "English"},
    "apply_media": {"de": "Seitengröße setzen", "en": "Set page size"},
    "apply_crop": {"de": "Zuschneiden (CropBox)", "en": "Crop (CropBox)"},
    "field_title": {"de": "Titel", "en": "Title"},
    "field_author": {"de": "Autor", "en": "Author"},
    "field_subject": {"de": "Thema", "en": "Subject"},
    "field_keywords": {"de": "Stichwörter", "en": "Keywords"},
    "field_creator": {"de": "Ersteller", "en": "Creator"},
    "field_producer": {"de": "Produzent", "en": "Producer"},
}

_current: UiLang = "de"


def get_lang() -> UiLang:
    return _current


def set_lang(lang: str) -> UiLang:
    global _current
    _current = "en" if str(lang).lower().startswith("en") else "de"
    return _current


def tr(key: str, *, lang: UiLang | None = None) -> str:
    """Übersetzt Schlüssel; Fallback = Schlüssel selbst."""
    use = lang or _current
    entry = _STRINGS.get(key)
    if not entry:
        return key
    return entry.get(use) or entry.get("de") or key


def sync_from_settings() -> UiLang:
    """Lädt Sprache aus App-Einstellungen."""
    try:
        from instantlensdoc.core.app_settings import get_ui_lang

        return set_lang(get_ui_lang())
    except Exception:
        return set_lang("de")
