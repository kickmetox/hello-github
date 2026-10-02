"""App-Konfiguration und Pfade."""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "InstantLensDoc"
DISPLAY_NAME = "InstantLens Doc"
VENDOR = "Andreas Meyer"
CONTACT_EMAIL = "ame@sellerbach.de"

# Repo-Root = InstantLensDoc/
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ICON_ICO = ASSETS / "app.ico"
ICON_PNG = ASSETS / "icon.png"

# Nutzerzielordner (Windows) — Icon ggf. von dort übernehmen
USER_TARGET = Path(r"D:\AI_Temp\InstantLensDoc")


def icon_path() -> Path | None:
    for p in (ICON_ICO, ICON_PNG):
        if p.exists():
            return p
    return None


def config_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    d = base / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d
