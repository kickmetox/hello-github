"""Pfade, Workspace und Verzeichnisse, die beim Scannen ausgelassen werden."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = Path(__file__).resolve().parent
STATIC = ROOT / "static"
ASSETS = ROOT / "assets"

# Windows-Zielverzeichnis laut Auftrag. Die IDE hat darauf vollen lokalen Zugriff.
WINDOWS_HOME = Path(r"D:\AI_Temp\ShatuIDE")

SKIP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "env",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "dist",
    "build",
    ".shatuide",
    "site-packages",
    ".tox",
    ".idea",
    ".vscode",
}

TEXT_SUFFIXES = {
    ".py",
    ".pyi",
    ".pyw",
    ".txt",
    ".md",
    ".rst",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".cfg",
    ".html",
    ".css",
    ".js",
    ".ts",
    ".sql",
    ".http",
    ".ipynb",
    ".csv",
    ".xml",
    ".env",
    ".gitignore",
    ".bat",
    ".ps1",
    ".sh",
}


def app_root() -> Path:
    """Verzeichnis, in dem shatuide.py liegt."""
    return ROOT


def default_workspace() -> Path:
    """Workspace: Umgebungsvariable, sonst D:\\AI_Temp\\ShatuIDE unter Windows, sonst App-Root."""
    env = os.environ.get("SHATUIDE_WORKSPACE")
    if env:
        return Path(env).expanduser().resolve()
    if os.name == "nt":
        WINDOWS_HOME.mkdir(parents=True, exist_ok=True)
        return WINDOWS_HOME
    return ROOT


def meta_dir(workspace: Path) -> Path:
    path = Path(workspace) / ".shatuide"
    path.mkdir(parents=True, exist_ok=True)
    return path


def inside(root: Path, path: Path) -> bool:
    root_r = Path(root).resolve()
    try:
        Path(path).resolve().relative_to(root_r)
        return True
    except ValueError:
        return False


def python_executable() -> str:
    return sys.executable
