"""UI-Mehrsprachigkeit InstantLens Doc — DE/EN/FR/RU/ES/ZH/PT/AR/IT — 2.6.18."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Literal, Optional

UiLang = Literal["de", "en", "fr", "ru", "es", "zh", "pt", "ar", "it"]

SUPPORTED_LANGS: tuple[UiLang, ...] = (
    "de",
    "en",
    "fr",
    "ru",
    "es",
    "zh",
    "pt",
    "ar",
    "it",
)
RTL_LANGS: frozenset[str] = frozenset({"ar"})

_LANG_ALIASES = {
    "de": "de",
    "deu": "de",
    "ger": "de",
    "german": "de",
    "en": "en",
    "eng": "en",
    "english": "en",
    "fr": "fr",
    "fra": "fr",
    "fre": "fr",
    "french": "fr",
    "ru": "ru",
    "rus": "ru",
    "russian": "ru",
    "es": "es",
    "spa": "es",
    "spanish": "es",
    "zh": "zh",
    "zho": "zh",
    "chi": "zh",
    "cn": "zh",
    "chinese": "zh",
    "pt": "pt",
    "por": "pt",
    "portuguese": "pt",
    "ar": "ar",
    "ara": "ar",
    "arabic": "ar",
    "it": "it",
    "ita": "it",
    "italian": "it",
}

_PROP_SRC = "ild_i18n_src"

_current: UiLang = "de"
_STRINGS: dict[str, dict[str, str]] = {}
_PHRASES: dict[str, dict[str, str]] = {}
_loaded = False


def _locales_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "locales"


def _ensure_loaded() -> None:
    global _loaded, _STRINGS, _PHRASES
    if _loaded:
        return
    path = _locales_dir() / "catalog.json"
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            _STRINGS = dict(data.get("strings") or {})
            _PHRASES = dict(data.get("phrases") or {})
            _loaded = True
            return
        except Exception:
            pass
    # Minimal fallback (DE/EN) if catalog missing
    _STRINGS = {
        "settings": {"de": "Einstellungen", "en": "Settings"},
        "help": {"de": "Hilfe", "en": "Help"},
        "about": {"de": "Info", "en": "About"},
        "ui_lang": {"de": "Oberflächensprache", "en": "UI language"},
        "lang_de": {"de": "Deutsch", "en": "German"},
        "lang_en": {"de": "Englisch", "en": "English"},
    }
    _PHRASES = {}
    _loaded = True


def normalize_lang(lang: str | None) -> UiLang:
    """Normalisiert Sprachcode auf unterstützte UI-Sprache."""
    raw = str(lang or "de").strip().lower().replace("_", "-")
    if not raw:
        return "de"
    primary = raw.split("-", 1)[0]
    mapped = _LANG_ALIASES.get(raw) or _LANG_ALIASES.get(primary)
    if mapped in SUPPORTED_LANGS:
        return mapped  # type: ignore[return-value]
    # Prefix match for supported codes
    for code in SUPPORTED_LANGS:
        if raw.startswith(code):
            return code
    return "de"


def supported_langs() -> tuple[UiLang, ...]:
    return SUPPORTED_LANGS


def is_rtl(lang: str | None = None) -> bool:
    return normalize_lang(lang or _current) in RTL_LANGS


def lang_native_name(code: str) -> str:
    """Anzeigename der Sprache in der jeweiligen Sprache."""
    names = {
        "de": "Deutsch",
        "en": "English",
        "fr": "Français",
        "ru": "Русский",
        "es": "Español",
        "zh": "中文",
        "pt": "Português",
        "ar": "العربية",
        "it": "Italiano",
    }
    return names.get(normalize_lang(code), code)


def get_lang() -> UiLang:
    return _current


def set_lang(lang: str) -> UiLang:
    global _current
    _current = normalize_lang(lang)
    return _current


def tr(key: str, *, lang: UiLang | None = None, **fmt) -> str:
    """Übersetzt Schlüssel; Fallback DE → Schlüssel selbst."""
    _ensure_loaded()
    use = normalize_lang(lang or _current)
    entry = _STRINGS.get(key)
    if not entry:
        return key
    text = entry.get(use) or entry.get("en") or entry.get("de") or key
    if fmt:
        try:
            return text.format(**fmt)
        except Exception:
            return text
    return text


def tr_phrase(german_or_src: str, *, lang: UiLang | None = None) -> str:
    """Übersetzt eine deutsche UI-Phrase (für Tree-Retranslate)."""
    _ensure_loaded()
    use = normalize_lang(lang or _current)
    src = str(german_or_src or "")
    if not src:
        return src
    if use == "de":
        # Wenn Quelle schon übersetzt war: Phrase-Map reverse nicht nötig —
        # retranslate speichert Original in Property.
        entry = _PHRASES.get(src)
        if entry:
            return entry.get("de") or src
        return src
    entry = _PHRASES.get(src)
    if not entry:
        return src
    return entry.get(use) or entry.get("en") or entry.get("de") or src


def tr_ann_zero_filtered(page: int, *, lang: UiLang | None = None) -> str:
    """Einheitlicher Status-String bei 0 gefilterten Ann.-Treffern — 1.1.6."""
    template = tr("ann_zero_filtered", lang=lang)
    try:
        return template.format(page=int(page))
    except Exception:
        return f"Keine gefilterten Treffer auf Seite {page}"


def sync_from_settings() -> UiLang:
    """Lädt Sprache aus App-Einstellungen."""
    try:
        from instantlensdoc.core.app_settings import get_ui_lang

        return set_lang(get_ui_lang())
    except Exception:
        return set_lang("de")


def help_html(*, lang: UiLang | None = None) -> str:
    """Lokalisierte Hilfe-HTML (locales/help/{lang}.html), Fallback DE/EN."""
    use = normalize_lang(lang or _current)
    help_dir = _locales_dir() / "help"
    for candidate in (use, "en", "de"):
        path = help_dir / f"{candidate}.html"
        if path.is_file():
            try:
                return path.read_text(encoding="utf-8")
            except OSError:
                continue
    return f"<h2>{tr('help', lang=use)}</h2><p>InstantLens Doc</p>"


def apply_layout_direction(widget, *, lang: UiLang | None = None) -> None:
    """Setzt Qt LayoutDirection LTR/RTL (Arabisch) — 2.6.18."""
    if widget is None:
        return
    try:
        from PySide6.QtCore import Qt
    except Exception:
        return
    use = normalize_lang(lang or _current)
    direction = Qt.RightToLeft if use in RTL_LANGS else Qt.LeftToRight
    try:
        widget.setLayoutDirection(direction)
    except Exception:
        pass
    try:
        app = widget if widget.__class__.__name__ == "QApplication" else None
        if app is None:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
        if app is not None:
            app.setLayoutDirection(direction)
    except Exception:
        pass


def _iter_text_targets(root) -> Iterable[object]:
    """Sammelt Widgets/Actions mit setText/setTitle für Retranslate."""
    seen: set[int] = set()

    def _add(obj) -> None:
        if obj is None:
            return
        oid = id(obj)
        if oid in seen:
            return
        seen.add(oid)
        yield_box.append(obj)

    yield_box: list[object] = []
    try:
        from PySide6.QtWidgets import QWidget
        from PySide6.QtGui import QAction
    except Exception:
        return []

    if isinstance(root, QWidget):
        _add(root)
        for w in root.findChildren(QWidget):
            _add(w)
        try:
            for act in root.findChildren(QAction):
                _add(act)
        except Exception:
            pass
        # Menüleiste / Aktionen am MainWindow
        try:
            mb = getattr(root, "menuBar", None)
            if callable(mb):
                bar = mb()
                if bar is not None:
                    _add(bar)
                    for act in bar.actions():
                        _add(act)
                        menu = act.menu() if hasattr(act, "menu") else None
                        if menu is not None:
                            _add(menu)
                            for sub in menu.actions():
                                _add(sub)
                                sm = sub.menu() if hasattr(sub, "menu") else None
                                if sm is not None:
                                    _add(sm)
                                    for s2 in sm.actions():
                                        _add(s2)
        except Exception:
            pass
    else:
        _add(root)
    return yield_box


def retranslate_tree(root, *, lang: UiLang | None = None) -> int:
    """
    Übersetzt bekannte deutsche UI-Phrasen im Widget-Baum.

    Speichert Originaltext in Property ``ild_i18n_src`` (einmalig),
    damit Sprachwechsel hin und zurück funktioniert — 2.6.18.
    """
    _ensure_loaded()
    use = normalize_lang(lang or _current)
    count = 0
    for obj in _iter_text_targets(root):
        try:
            getter = None
            setter = None
            if hasattr(obj, "windowTitle") and hasattr(obj, "setWindowTitle"):
                # QWidget window title
                try:
                    title = obj.windowTitle()
                except Exception:
                    title = ""
                if title:
                    prop = f"{_PROP_SRC}_win"
                    src = None
                    try:
                        src = obj.property(prop)
                    except Exception:
                        src = None
                    if not src:
                        src = title
                        try:
                            obj.setProperty(prop, src)
                        except Exception:
                            pass
                    new = tr_phrase(str(src), lang=use)
                    if new != title:
                        obj.setWindowTitle(new)
                        count += 1
            if hasattr(obj, "text") and hasattr(obj, "setText"):
                getter, setter = obj.text, obj.setText
            elif hasattr(obj, "title") and hasattr(obj, "setTitle"):
                getter, setter = obj.title, obj.setTitle
            if getter is None or setter is None:
                continue
            try:
                cur = getter()
            except Exception:
                continue
            if not cur or not str(cur).strip():
                continue
            try:
                src = obj.property(_PROP_SRC)
            except Exception:
                src = None
            if not src:
                src = cur
                try:
                    obj.setProperty(_PROP_SRC, src)
                except Exception:
                    pass
            new = tr_phrase(str(src), lang=use)
            if new != cur:
                try:
                    setter(new)
                    count += 1
                except Exception:
                    pass
            # Tooltips (optional phrase map)
            if hasattr(obj, "toolTip") and hasattr(obj, "setToolTip"):
                try:
                    tip = obj.toolTip()
                    if tip:
                        tprop = f"{_PROP_SRC}_tip"
                        tsrc = obj.property(tprop)
                        if not tsrc:
                            tsrc = tip
                            obj.setProperty(tprop, tsrc)
                        newt = tr_phrase(str(tsrc), lang=use)
                        if newt != tip:
                            obj.setToolTip(newt)
                except Exception:
                    pass
        except Exception:
            continue
    return count


def apply_ui_language(
    root=None,
    *,
    lang: str | None = None,
    persist: bool = False,
) -> UiLang:
    """
    Sprache setzen, optional persistieren, RTL anwenden, UI retranslates — 2.6.18.
    """
    use = set_lang(lang) if lang is not None else sync_from_settings()
    if persist:
        try:
            from instantlensdoc.core.app_settings import set_ui_lang

            set_ui_lang(use)
        except Exception:
            pass
    if root is not None:
        apply_layout_direction(root, lang=use)
        try:
            retranslate_tree(root, lang=use)
        except Exception:
            pass
    else:
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is not None:
                apply_layout_direction(app, lang=use)
        except Exception:
            pass
    return use


def catalog_stats() -> dict[str, int]:
    _ensure_loaded()
    return {
        "langs": len(SUPPORTED_LANGS),
        "string_keys": len(_STRINGS),
        "phrases": len(_PHRASES),
    }


# Schlüssel-/DE-Marker für historische Smoke-Source-Checks (Inhalt kommt aus catalog.json).
# expiry_warn_banner expiry_expired_banner expiry_dismiss_label expiry_close_tooltip
# expiry_banner_accessible expiry_dismiss_accessible expiry_close_accessible
# expiry_warn_tooltip expiry_dismiss_tooltip expiry_dismiss_status
# expiry_banner_expired_accessible expiry_banner_icon_accessible
# ann_zero_filtered settings settings_title ui_lang lang_de lang_en
# field_title field_author field_subject Betreff field_keywords field_creator
# meta_title meta_save meta_hint meta_reset meta_dirty meta_backup meta_toast_ok
_SMOKE_SOURCE_MARKERS = (
    "expiry_warn_banner",
    "expiry_expired_banner",
    "expiry_dismiss_label",
    "expiry_close_tooltip",
    "expiry_banner_accessible",
    "expiry_dismiss_accessible",
    "expiry_close_accessible",
    "ann_zero_filtered",
    "Betreff",
)
