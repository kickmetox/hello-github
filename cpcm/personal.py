"""Persönliche Bereiche, die Windows und Linux gemeinsam führen."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from cpcm.paths import Identity, World, join_root

AREAS: tuple[tuple[str, str], ...] = (
    ("documents", "Dokumente"),
    ("pictures", "Bilder"),
    ("desktop", "Desktop"),
    ("downloads", "Downloads"),
    ("music", "Musik"),
    ("videos", "Videos"),
    ("mail", "Mail"),
    ("calendar", "Termine"),
    ("wallpaper", "Hintergrund"),
    ("settings", "Einstellungen"),
)

_FOLDER = {
    "documents": ("Documents", "Dokumente"),
    "pictures": ("Pictures", "Bilder"),
    "desktop": ("Desktop",),
    "downloads": ("Downloads",),
    "music": ("Music", "Musik"),
    "videos": ("Videos",),
}


def is_reparse(path: Path) -> bool:
    from cpcm.backup import is_reparse_point
    return is_reparse_point(path)


def _existing_dir(path: Path) -> Path | None:
    try:
        return path if path.is_dir() else None
    except OSError:
        return None


def _existing_file(path: Path) -> Path | None:
    try:
        return path if path.is_file() else None
    except OSError:
        return None


def known_dir(identity: Identity, key: str) -> Path:
    names = _FOLDER[key]
    home = str(identity.home)
    for name in names:
        candidate = Path(join_root(home, name))
        if _existing_dir(candidate):
            return candidate
    return Path(join_root(home, names[0]))


def thunderbird_dir(identity: Identity) -> Path:
    if identity.world == World.WINDOWS:
        return Path(join_root(str(identity.appdata), "Thunderbird"))
    return identity.home / ".thunderbird"


def discover(identity: Identity, keys: list[str]) -> tuple[list[Path], list[str]]:
    """Vorhandene Pfade und die Namen fehlender Bereiche."""
    found: list[Path] = []
    missing: list[str] = []
    labels = dict(AREAS)
    for key in keys:
        paths = _paths_for(identity, key)
        existing = [path for path in paths if path.exists()]
        if existing:
            found.extend(existing)
        else:
            missing.append(labels.get(key, key))
    unique: list[Path] = []
    seen: set[str] = set()
    for path in found:
        marker = os.path.normcase(str(path))
        if marker not in seen:
            seen.add(marker)
            unique.append(path)
    return unique, missing


def _paths_for(identity: Identity, key: str) -> list[Path]:
    if key in _FOLDER:
        folder = known_dir(identity, key)
        return [folder] if folder.exists() else []
    if key == "mail":
        paths = [thunderbird_dir(identity)]
        if identity.world == World.WINDOWS:
            outlook = Path(join_root(str(identity.localappdata), "Microsoft", "Outlook"))
            if outlook.is_dir():
                paths.extend(outlook.glob("*.pst"))
        return [path for path in paths if path.exists()]
    if key == "calendar":
        paths: list[Path] = []
        documents = known_dir(identity, "documents")
        if documents.is_dir():
            paths.extend(documents.glob("*.ics"))
            calendar_dir = documents / "Kalender"
            if calendar_dir.is_dir() and not is_reparse(calendar_dir):
                paths.extend(calendar_dir.glob("*.ics"))
        if identity.world == World.LINUX:
            evolution = identity.home / ".local" / "share" / "evolution" / "calendar"
            if evolution.is_dir():
                paths.append(evolution)
        return [path for path in paths if path.exists()]
    if key == "wallpaper":
        image = wallpaper_source(identity)
        return [image] if image else []
    if key == "settings":
        return [path for path in settings_files(identity) if path.exists()]
    return []


def settings_files(identity: Identity) -> list[Path]:
    home = identity.home
    files = [home / ".bashrc", home / ".gitconfig", home / ".profile"]
    if identity.world == World.WINDOWS:
        files.extend([
            Path(join_root(str(identity.appdata), "Code", "User", "settings.json")),
            Path(join_root(str(identity.appdata), "Code", "User", "keybindings.json")),
            Path(join_root(str(identity.localappdata), "Packages", "Microsoft.WindowsTerminal_8wekyb3d8bbwe", "LocalState", "settings.json")),
        ])
    else:
        files.extend([
            home / ".config" / "Code" / "User" / "settings.json",
            home / ".config" / "Code" / "User" / "keybindings.json",
            home / ".config" / "gtk-3.0" / "settings.ini",
            home / ".config" / "kdeglobals",
        ])
    return files


def wallpaper_source(identity: Identity) -> Path | None:
    if identity.world == World.WINDOWS and os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop") as key:
                value, _kind = winreg.QueryValueEx(key, "WallPaper")
            candidate = _existing_file(Path(value))
            if candidate:
                return candidate
        except OSError:
            pass
        transcoded = Path(join_root(str(identity.appdata), "Microsoft", "Windows", "Themes", "TranscodedWallpaper"))
        return _existing_file(transcoded)
    picture = identity.home / ".local" / "share" / "cpcm" / "wallpaper.jpg"
    if picture.is_file():
        return picture
    return None


def appearance_note(identity: Identity) -> dict:
    return {
        "world": identity.world.value,
        "wallpaper": str(wallpaper_source(identity) or ""),
        "mode": "dark",
        "accent": "#0078D4",
    }


def apply_wallpaper(image: Path) -> str:
    """Setzt den Desktop-Hintergrund. Unter Windows direkt, unter Linux über gsettings, wenn vorhanden."""
    if not image.is_file():
        raise FileNotFoundError(str(image))
    if os.name == "nt":
        destination = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Themes" / "CPCM-Wallpaper.jpg"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(image, destination)
        system = ctypes_wallpaper(destination)
        return system
    destination = Path.home() / ".local" / "share" / "cpcm" / "wallpaper.jpg"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(image, destination)
    gsettings = shutil.which("gsettings")
    if not gsettings:
        return f"Hintergrund liegt in {destination}. gsettings ist nicht installiert, der Desktop wurde nicht umgestellt."
    uri = destination.resolve().as_uri()
    subprocess.run([gsettings, "set", "org.gnome.desktop.background", "picture-uri", uri], check=False)
    subprocess.run([gsettings, "set", "org.gnome.desktop.background", "picture-uri-dark", uri], check=False)
    return f"Hintergrund gesetzt: {destination}"


def ctypes_wallpaper(destination: Path) -> str:
    import ctypes
    ok = ctypes.windll.user32.SystemParametersInfoW(20, 0, str(destination), 3)
    if not ok:
        return f"Datei liegt in {destination}. Windows hat den Hintergrund nicht übernommen."
    return f"Hintergrund übernommen: {destination}"


def note_text(identity: Identity) -> str:
    return json.dumps(appearance_note(identity), indent=2, ensure_ascii=False) + "\n"
