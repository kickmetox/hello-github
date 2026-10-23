"""Speicherorte. Übersteuerbar, damit Tests nicht ins echte Home schreiben."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def norm(path: str | os.PathLike[str]) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def place_key(path: str) -> str:
    """Dieselbe Stelle, Symlinks eingeschlossen."""
    try:
        return norm(os.path.realpath(path))
    except OSError:
        return norm(path)


def prefix_with_sep(path: str, sep: str) -> str:
    """Kinder-Präfix. Ein Stamm, der schon auf den Trenner endet, wird nicht verdoppelt."""
    if path.endswith(sep):
        return path
    return path + sep


def child_prefix(path: str) -> str:
    return prefix_with_sep(norm(path), os.sep)


def parent_of(path: str) -> str:
    parent = os.path.dirname(path)
    return parent if parent else path


def is_inside(child: str, parent: str) -> bool:
    child_n = norm(child)
    parent_n = norm(parent)
    if child_n == parent_n:
        return True
    return child_n.startswith(child_prefix(parent))


def data_dir() -> Path:
    override = os.environ.get("FLARE_DATA_DIR")
    if override:
        return Path(override)
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Local"
        return root / "Flare"
    xdg = os.environ.get("XDG_DATA_HOME")
    root = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return root / "flare"


def config_dir() -> Path:
    override = os.environ.get("FLARE_CONFIG_DIR")
    if override:
        return Path(override)
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Roaming"
        return root / "Flare"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    root = Path(xdg) if xdg else Path.home() / ".config"
    return root / "flare"


def sqlite_uri(path: Path, mode: str) -> str:
    return Path(path).resolve().as_uri() + f"?mode={mode}"
