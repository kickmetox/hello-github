"""App-Konfiguration und Pfade."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable, List, Optional

APP_NAME = "InstantLensDoc"
DISPLAY_NAME = "InstantLens Doc"
VENDOR = "Andreas Meyer"
CONTACT_EMAIL = "ame@sellerbach.de"

# Repo-Root = InstantLensDoc/ (auch unter PyInstaller _MEIPASS)
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    ROOT = Path(sys._MEIPASS)  # type: ignore[attr-defined]
else:
    ROOT = Path(__file__).resolve().parents[1]

ASSETS = ROOT / "assets"
ICON_ICO = ASSETS / "app.ico"
ICON_PNG = ASSETS / "icon.png"

# Nutzerzielordner (Windows) — Icon ggf. von dort übernehmen
USER_TARGET = Path(r"D:\AI_Temp\InstantLensDoc")

# Bekannte Icon-Dateinamen (Reihenfolge = Priorität)
_ICON_NAMES = (
    "app.ico",
    "icon.ico",
    "app.png",
    "icon.png",
    "lensDoc.jpg",
    "lensDoc.jpeg",
    "lensDoc.png",
    "app.jpg",
    "icon.jpg",
)


def _candidate_dirs() -> List[Path]:
    """Verzeichnisse, in denen Icons liegen können."""
    dirs: List[Path] = []
    # 1) App-Assets (Repo / Bundle)
    dirs.append(ASSETS)
    dirs.append(ROOT)
    # 2) CWD und CWD/assets (wenn aus anderem Ordner gestartet)
    cwd = Path.cwd()
    dirs.append(cwd / "assets")
    dirs.append(cwd)
    # 3) Nutzerzielordner Windows
    dirs.append(USER_TARGET / "assets")
    dirs.append(USER_TARGET)
    # 4) Executable-Verzeichnis (frozen)
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        dirs.append(exe_dir / "assets")
        dirs.append(exe_dir)
    # Deduplizieren, Reihenfolge behalten
    seen: set[str] = set()
    out: List[Path] = []
    for d in dirs:
        key = str(d)
        if key not in seen:
            seen.add(key)
            out.append(d)
    return out


def iter_icon_candidates() -> Iterable[Path]:
    """Alle möglichen Icon-Pfade in Prioritätsreihenfolge."""
    for folder in _candidate_dirs():
        for name in _ICON_NAMES:
            yield folder / name


def icon_path() -> Optional[Path]:
    """Erstes vorhandenes Icon (ICO/PNG/JPG)."""
    for p in iter_icon_candidates():
        try:
            if p.is_file() and p.stat().st_size > 0:
                return p
        except OSError:
            continue
    return None


def icon_paths_for_qt() -> List[Path]:
    """Mehrere Icon-Dateien für QIcon.addFile (Window/Taskleiste/About)."""
    found: List[Path] = []
    seen: set[str] = set()
    for p in iter_icon_candidates():
        try:
            if not p.is_file() or p.stat().st_size <= 0:
                continue
        except OSError:
            continue
        key = str(p.resolve()) if p.exists() else str(p)
        if key in seen:
            continue
        seen.add(key)
        found.append(p)
        # Max. ein paar Varianten (ico + png reichen)
        if len(found) >= 4:
            break
    return found


def config_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    d = base / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d
