"""Pfade für Konfiguration, Symbol und Arbeitsordner."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Vom Benutzer genannter Arbeitsordner. Liegt dort ein Symbol, hat es Vorrang.
WORK_DIR = Path(r"D:\AI_Temp\SphereDrive")
PREFERRED_ICON_NAMES = ("spheredrive.ico", "app.ico", "icon.ico", "logo.ico")


def package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_store_path() -> Path:
    override = os.environ.get("SPHEREDRIVE_CONFIG")
    if override:
        return Path(override)
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "SphereDrive" / "config.json"
    return Path.home() / ".config" / "SphereDrive" / "config.json"


def default_log_path() -> Path:
    return default_store_path().with_name("spheredrive.log")


def choose_icon(files: list[Path]) -> Path | None:
    """Wählt ein Symbol. Eine fremde .ico-Datei gewinnt vor der mitgelieferten SphereDrive.ico."""
    existing = [path for path in files if path.is_file() and path.suffix.lower() == ".ico"]
    if not existing:
        return None
    custom = [path for path in existing if path.name.lower() != "spheredrive.ico"]
    pool = custom or existing

    def rank(path: Path) -> tuple[int, str]:
        name = path.name.lower()
        if "sphere" in name:
            return (0, name)
        if name in PREFERRED_ICON_NAMES:
            return (1, name)
        return (2, name)

    return sorted(pool, key=rank)[0]


def _icons_in(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return [path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".ico"]


def find_icon() -> Path | None:
    env = os.environ.get("SPHEREDRIVE_ICON")
    if env and Path(env).is_file():
        return Path(env)
    for directory in (WORK_DIR, package_root(), package_root() / "assets"):
        chosen = choose_icon(_icons_in(directory))
        if chosen is not None:
            return chosen
    return None


def find_window_png() -> Path | None:
    icon = find_icon()
    if icon is not None:
        sibling = icon.with_suffix(".png")
        if sibling.is_file():
            return sibling
    bundled = package_root() / "assets" / "SphereDrive.png"
    return bundled if bundled.is_file() else None


def entry_script() -> Path:
    root = package_root()
    pyw = root / "SphereDrive.pyw"
    if pyw.is_file():
        return pyw
    return Path(__file__).resolve()


def pythonw_executable() -> str:
    executable = Path(sys.executable)
    candidate = executable.with_name("pythonw.exe")
    if candidate.is_file():
        return str(candidate)
    return str(executable)
