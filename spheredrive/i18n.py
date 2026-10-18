"""Sprachumschaltung. Deutsch ist die Vorgabe, die übrigen Sprachen liegen in translations."""

from __future__ import annotations

import sys

from spheredrive.translations import TABLES

LANGUAGES: list[tuple[str, str]] = [
    ("de", "Deutsch"),
    ("en", "English"),
    ("fr", "Français"),
    ("es", "Español"),
    ("pt", "Português"),
    ("ru", "Русский"),
    ("zh", "中文"),
]

_LANG_IDS = {code for code, _name in LANGUAGES}
_lang = "de"

# Primäre Sprach-ID von GetUserDefaultUILanguage.
_WINDOWS_PRIMARY = {
    0x07: "de",
    0x09: "en",
    0x0C: "fr",
    0x0A: "es",
    0x16: "pt",
    0x19: "ru",
    0x04: "zh",
}


def get_language() -> str:
    return _lang


def set_language(code: str) -> str:
    global _lang
    _lang = code if code in _LANG_IDS else "de"
    return _lang


def t(text: str, **kwargs) -> str:
    """Übersetzt einen deutschen Text. Platzhalter heißen {name}."""
    if text and _lang != "de":
        text = TABLES.get(_lang, {}).get(text, text)
    if not kwargs:
        return text
    try:
        return text.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return text


def detect_windows_language() -> str | None:
    """UI-Sprache von Windows, wenn sie SphereDrive unterstützt."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes

        lang_id = int(ctypes.windll.kernel32.GetUserDefaultUILanguage())
    except (AttributeError, OSError, ValueError):
        return None
    return _WINDOWS_PRIMARY.get(lang_id & 0x3FF)


def choose_initial_language(saved: str | None, explicit: bool) -> str:
    """Gespeicherte Sprache gewinnt. Sonst die Windows-Sprache, sonst Deutsch."""
    if explicit and saved in _LANG_IDS:
        return saved
    detected = detect_windows_language()
    if detected:
        return detected
    return "de"


def apply_font(root) -> str:
    """Wählt eine Schrift, die auch Kyrillisch und Chinesisch zeichnen kann."""
    from spheredrive.ui.widgets import P, load_font, tkfont_families

    load_font(root)
    families = set(tkfont_families(root))
    if _lang == "zh":
        for name in (
            "Microsoft YaHei UI",
            "Microsoft YaHei",
            "Noto Sans CJK SC",
            "Noto Sans SC",
            "Source Han Sans SC",
            "WenQuanYi Micro Hei",
            "Droid Sans Fallback",
        ):
            if name in families:
                P.font = name
                return name
    for name in ("Segoe UI", "Liberation Sans", "DejaVu Sans", "Noto Sans"):
        if name in families:
            P.font = name
            return name
    return P.font


def translated_keys() -> set[str]:
    return set(TABLES["en"])
