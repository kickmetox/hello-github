"""Persistente App-Einstellungen (Theme, OCR, Pfade, Export, Zoom, Autosave)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from instantlensdoc.config import config_dir

SETTINGS_NAME = "ui_settings.json"

ThemeMode = Literal["light", "dark"]
UiLang = Literal["de", "en"]

DEFAULTS: dict[str, Any] = {
    "theme": "light",
    "ocr_lang": "deu+eng",
    "batch_output_dir": "",
    "default_open_dir": "",
    "ui_lang": "de",
    "export_jpeg_quality": 85,
    "export_pdf_page": "A4",
    "export_image_max_edge": 2000,
    "update_check_on_start": False,
    "last_export_dir": "",
    "default_zoom_percent": 150,
    "autosave_interval_sec": 60,
    "ann_highlight_color": "#FFE066",
    "ann_pen_color": "#2C3E50",
    "ann_note_color": "#FFEB3B",
    "editor_line_numbers": False,
    "editor_minimap": False,
    "ann_palette_index": 0,
    "pdf_grayscale": False,
    "pdf_night_mode": False,
    "pdf_two_page_spread": False,
    "pdf_continuous_scroll": False,
    "editor_bracket_match": True,
    "ann_default_opacity": 1.0,
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
    "editor_show_special_chars": False,
    "annotations_visible": True,
    "minimize_to_tray": False,
    "page_size_unit": "mm",
    "backup_on_save": False,
    "export_raster_dpi": 150,
    "export_profiles": [],
    "active_export_profile": "",
    "window_geometry": "",
    "window_state": "",
    "ann_color_presets": ["#FFE066", "#FF6B6B", "#4ECDC4"],
    "restore_session_on_start": True,
    "pdf_thumbnail_scale": 0.18,
    "editor_text_encoding": "auto",
    "skip_splash": False,
    "spellcheck_dict_path": "",
    "show_page_boxes": False,
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
    mode = load_settings().get("theme", "light")
    return "dark" if mode == "dark" else "light"


def set_theme(mode: ThemeMode) -> None:
    save_settings({"theme": mode})


def get_ocr_lang() -> str:
    lang = load_settings().get("ocr_lang", DEFAULTS["ocr_lang"])
    return str(lang) if lang else DEFAULTS["ocr_lang"]


def set_ocr_lang(code: str) -> None:
    save_settings({"ocr_lang": code or DEFAULTS["ocr_lang"]})


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


def get_default_zoom_percent() -> int:
    try:
        v = int(load_settings().get("default_zoom_percent", 150))
    except (TypeError, ValueError):
        v = 150
    return max(25, min(500, v))


def set_default_zoom_percent(percent: int) -> None:
    save_settings({"default_zoom_percent": max(25, min(500, int(percent)))})


def get_default_zoom_scale() -> float:
    return get_default_zoom_percent() / 100.0


def get_autosave_interval_sec() -> int:
    try:
        v = int(load_settings().get("autosave_interval_sec", 60))
    except (TypeError, ValueError):
        v = 60
    return max(10, min(600, v))


def set_autosave_interval_sec(seconds: int) -> None:
    save_settings({"autosave_interval_sec": max(10, min(600, int(seconds)))})


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


def import_user_templates_zip(
    src: Path | str,
    *,
    merge: bool = True,
) -> list[dict]:
    """
    Vorlagen aus Zip importieren.
    merge=True: hinzufügen/überschreiben (Titel); False: bestehende ersetzen.
    Rückgabe: importierte Einträge.
    """
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
    if not merge:
        for old in list(get_user_doc_templates()):
            delete_user_doc_template(old["id"])
    imported: list[dict] = []
    for entry in items:
        saved = save_user_doc_template(
            title=entry["title"],
            body=entry["body"],
            template_id=entry.get("id"),
        )
        imported.append(saved)
    sync_user_templates_folder()
    return imported


SEARCH_SNIPPET_CONTEXT_MIN = 20
SEARCH_SNIPPET_CONTEXT_MAX = 80
SEARCH_SNIPPET_CONTEXT_DEFAULT = 40

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


ANN_COLOR_PRESET_COUNT = 3
_DEFAULT_ANN_PRESETS = ["#FFE066", "#FF6B6B", "#4ECDC4"]


def _normalize_hex_color(color: str, fallback: str = "#888888") -> str:
    c = (color or "").strip()
    if not c:
        return fallback
    if not c.startswith("#"):
        c = "#" + c
    if len(c) < 4:
        return fallback
    return c


def get_ann_color_presets() -> list[str]:
    """Drei Favoriten-Farben für Annotationen (Highlight/Stift)."""
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
    """Einzelnen Favoriten-Slot (0..2) setzen."""
    presets = get_ann_color_presets()
    i = max(0, min(ANN_COLOR_PRESET_COUNT - 1, int(index)))
    presets[i] = _normalize_hex_color(color, presets[i])
    return set_ann_color_presets(presets)


def get_restore_session_on_start() -> bool:
    return bool(load_settings().get("restore_session_on_start", True))


def set_restore_session_on_start(enabled: bool) -> None:
    save_settings({"restore_session_on_start": bool(enabled)})


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
