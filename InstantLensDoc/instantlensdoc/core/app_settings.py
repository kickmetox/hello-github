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
    "editor_line_numbers": False,
    "pdf_grayscale": False,
    "pdf_night_mode": False,
    "ann_default_opacity": 1.0,
    "recent_dirs": [],
    "editor_markdown_preview": False,
    "editor_soft_wrap": True,
    "editor_show_special_chars": False,
    "annotations_visible": True,
    "minimize_to_tray": False,
    "page_size_unit": "mm",
    "backup_on_save": False,
    "export_raster_dpi": 150,
    "window_geometry": "",
    "window_state": "",
    "ann_color_presets": ["#FFE066", "#FF6B6B", "#4ECDC4"],
    "restore_session_on_start": True,
    "pdf_thumbnail_scale": 0.18,
    "editor_text_encoding": "utf-8",
    "show_page_boxes": False,
    "show_printer_marks": False,
    "annotations_locked": False,
    "editor_snippets": [
        "Sehr geehrte Damen und Herren,\n\n",
        "Mit freundlichen Grüßen\n",
        "— Notiz —\n",
    ],
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


def get_editor_line_numbers() -> bool:
    return bool(load_settings().get("editor_line_numbers", False))


def set_editor_line_numbers(enabled: bool) -> None:
    save_settings({"editor_line_numbers": bool(enabled)})


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


def dialog_start_dir(*fallbacks: str | Path | None) -> str:
    """Startpfad für QFileDialog: zuletzt verwendeter existierender Ordner, sonst Fallbacks."""
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


TEXT_ENCODING_CHOICES = ("utf-8", "latin-1")


def get_editor_text_encoding() -> str:
    """Standard-Encoding für Editor-Öffnen/Speichern (utf-8 | latin-1)."""
    from instantlensdoc.core.documents import normalize_text_encoding

    raw = str(load_settings().get("editor_text_encoding", "utf-8") or "utf-8")
    return normalize_text_encoding(raw)


def set_editor_text_encoding(encoding: str) -> str:
    from instantlensdoc.core.documents import normalize_text_encoding

    enc = normalize_text_encoding(encoding)
    save_settings({"editor_text_encoding": enc})
    return enc
