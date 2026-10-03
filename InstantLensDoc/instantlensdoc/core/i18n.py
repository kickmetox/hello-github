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
    "theme_system": {"de": "System folgen", "en": "Follow system"},
    "ui_lang": {"de": "Oberflächensprache", "en": "UI language"},
    "ocr_lang": {"de": "OCR-Sprache (Standard)", "en": "OCR language (default)"},
    "batch_dir": {"de": "Batch-Ausgabeordner", "en": "Batch output folder"},
    "open_dir": {"de": "Standard-Ordner (Öffnen)", "en": "Default folder (Open)"},
    "export_jpeg_q": {"de": "Export JPEG-Qualität", "en": "Export JPEG quality"},
    "export_page": {"de": "Export PDF-Seitenformat", "en": "Export PDF page size"},
    "default_zoom": {"de": "Standard-Zoom % (PDF)", "en": "Default zoom % (PDF)"},
    "default_zoom_mode": {"de": "Standard-Zoom-Modus (PDF)", "en": "Default zoom mode (PDF)"},
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
    "field_subject": {"de": "Betreff", "en": "Subject"},
    "field_keywords": {"de": "Keywords", "en": "Keywords"},
    "field_creator": {"de": "Ersteller", "en": "Creator"},
    "field_producer": {"de": "Produzent", "en": "Producer"},
    "meta_save": {"de": "Speichern", "en": "Save"},
    "meta_hint": {
        "de": "Titel, Autor, Betreff und Keywords (DocInfo + XMP) — Speichern schreibt in die PDF-Datei. Dirty · Reset · Backup .ildbak · Erfolgs-Toast — 1.5.2.",
        "en": "Title, author, subject and keywords (DocInfo + XMP) — Save writes into the PDF. Dirty · Reset · .ildbak backup · success toast — 1.5.2.",
    },
    "meta_reset": {"de": "Zurücksetzen", "en": "Reset"},
    "meta_reset_tip": {
        "de": "Alle Felder auf die geladenen Originalwerte zurücksetzen — 1.5.1",
        "en": "Reset all fields to the loaded original values — 1.5.1",
    },
    "meta_dirty": {
        "de": "Ungespeicherte Änderungen (*)",
        "en": "Unsaved changes (*)",
    },
    "meta_delete_empty": {
        "de": "Leere Felder beim Speichern löschen",
        "en": "Delete empty fields on save",
    },
    "meta_delete_empty_tip": {
        "de": "An: leere Metadaten-Felder aus DocInfo/XMP entfernen. Aus: leere Strings belassen — 1.5.1",
        "en": "On: remove empty metadata fields from DocInfo/XMP. Off: keep empty strings — 1.5.1",
    },
    "meta_backup": {
        "de": "Backup (.ildbak) vor Speichern",
        "en": "Backup (.ildbak) before save",
    },
    "meta_backup_tip": {
        "de": "Vor dem Schreiben eine rotierende Backup-Kopie dateiname.pdf.ildbak anlegen — 1.5.2",
        "en": "Create a rotating backup copy filename.pdf.ildbak before writing — 1.5.2",
    },
    "meta_toast_ok": {
        "de": "Metadaten gespeichert",
        "en": "Metadata saved",
    },
    "meta_toast_empty": {
        "de": "(keine Felder gesetzt)",
        "en": "(no fields set)",
    },
    # Lizenz-Banner — 1.0.9
    "expiry_warn_banner": {
        "de": "Hinweis: Lizenz/Trial läuft in {rest} ab{until} — Enter/Klick: Info/Aktivierung · Esc / Dismiss / × bis morgen",
        "en": "Notice: license/trial expires in {rest}{until} — Enter/Click: About/Activate · Esc / Dismiss / × until tomorrow",
    },
    "expiry_expired_banner": {
        "de": "Lizenz abgelaufen{until} — Enter/Klick: Info/Aktivierung · Esc / Dismiss / × bis morgen",
        "en": "License expired{until} — Enter/Click: About/Activate · Esc / Dismiss / × until tomorrow",
    },
    "expiry_warn_tooltip": {
        "de": "Enter/Klick öffnet Info / Lizenz aktivieren; Esc schließt; Fokus-Ring — 1.0.9",
        "en": "Enter/Click opens About / activate license; Esc dismisses; focus ring — 1.0.9",
    },
    "expiry_dismiss_label": {
        "de": "Dismiss",
        "en": "Dismiss",
    },
    "expiry_dismiss_tooltip": {
        "de": "Hinweis schließen — dismiss_date bis morgen — 1.0.9",
        "en": "Dismiss notice — dismiss_date until tomorrow — 1.0.9",
    },
    "expiry_close_tooltip": {
        "de": "Schließen (×) — Hinweis bis morgen ausblenden — 1.0.9",
        "en": "Close (×) — hide notice until tomorrow — 1.0.9",
    },
    "expiry_dismiss_status": {
        "de": "Ablauf-Hinweis bis morgen ausgeblendet",
        "en": "Expiry notice hidden until tomorrow",
    },
    "expiry_banner_accessible": {
        "de": "Lizenz-Ablaufhinweis",
        "en": "License expiry notice",
    },
    "expiry_banner_expired_accessible": {
        "de": "Lizenz abgelaufen — Hinweisbanner",
        "en": "License expired — notice banner",
    },
    "expiry_banner_icon_accessible": {
        "de": "Warnsymbol Lizenzablauf",
        "en": "License expiry warning icon",
    },
    "expiry_dismiss_accessible": {
        "de": "Ablaufhinweis schließen (Dismiss)",
        "en": "Dismiss expiry notice",
    },
    "expiry_close_accessible": {
        "de": "Ablaufhinweis schließen",
        "en": "Close expiry notice",
    },
    # Annotationen 0 gefilterte Treffer — einheitlicher Status — 1.1.6
    "ann_zero_filtered": {
        "de": "Keine gefilterten Treffer auf Seite {page}",
        "en": "No filtered matches on page {page}",
    },
}


def tr_ann_zero_filtered(page: int, *, lang: UiLang | None = None) -> str:
    """Einheitlicher Status-String bei 0 gefilterten Ann.-Treffern — 1.1.6."""
    template = tr("ann_zero_filtered", lang=lang)
    try:
        return template.format(page=int(page))
    except Exception:
        return f"Keine gefilterten Treffer auf Seite {page}"

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
