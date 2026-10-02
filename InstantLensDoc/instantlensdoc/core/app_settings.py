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
