"""Vault-Ort und die Home-Pfade beider Welten."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

from cpcm import WINDOWS_INSTALL_DIR
from cpcm.paths import Identity, World, host_identity, identity_for_home, looks_like_foreign_path


def _package_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resource_root() -> Path:
    """Quellbaum, oder bei PyInstaller das entpackte Bundle."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return _package_root()


def install_root() -> Path:
    """Beschreibbarer Programmordner. Neben der Binary, sonst der Quellbaum."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return _package_root()


def bundled_path(install: Path, relative: str) -> Path:
    """Datei im Installationsordner, im Bundle nur wenn die Binary keine Kopie daneben hat."""
    local = install / relative
    if local.exists() or not getattr(sys, "frozen", False):
        return local
    return resource_root() / relative


ROOT = install_root()


def settings_file(root: Path | None = None) -> Path:
    return (root or ROOT) / "cpcm-settings.json"


def default_settings(host: Identity | None = None) -> dict:
    host = host or host_identity()
    return {
        "vault": None,
        "homes": {
            "linux": str(host.home) if host.world == World.LINUX else f"/home/{host.user}",
            "windows": str(host.home) if host.world == World.WINDOWS else rf"C:\Users\{host.user}",
        },
        "port": 8910,
        "install_dir_windows": WINDOWS_INSTALL_DIR,
    }


def load_settings(root: Path | None = None) -> dict:
    path = settings_file(root)
    data = default_settings()
    if path.is_file():
        stored = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(stored, dict):
            for key in ("vault", "port", "install_dir_windows"):
                if key in stored:
                    data[key] = stored[key]
            port = data.get("port")
            if isinstance(port, int) and 8765 <= port < 8865:
                data["port"] = 8910
            homes = stored.get("homes")
            if isinstance(homes, dict):
                for key in ("linux", "windows"):
                    if homes.get(key):
                        data["homes"][key] = str(homes[key])
    return data


def save_settings(data: dict, root: Path | None = None) -> None:
    settings_file(root).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def vault_dir(data: dict | None = None, root: Path | None = None) -> Path:
    root = root or ROOT
    data = data or load_settings(root)
    raw = data.get("vault")
    if raw:
        text = str(raw)
        if looks_like_foreign_path(text) and not Path(text).exists():
            return root / "vault"
        return Path(text)
    return root / "vault"


def counterpart_identity(data: dict, host: Identity) -> Identity:
    other = World.WINDOWS if host.world == World.LINUX else World.LINUX
    home = data.get("homes", {}).get(other.value) or default_settings(host)["homes"][other.value]
    return identity_for_home(other, Path(home), host.user)


def host_home_identity(data: dict, host: Identity | None = None) -> Identity:
    host = host or host_identity()
    configured = str(data.get("homes", {}).get(host.world.value) or "")
    if configured and not looks_like_foreign_path(configured) and Path(configured).is_dir():
        return identity_for_home(host.world, Path(configured), host.user)
    return host


def ensure_windows_install(source: Path | None = None) -> Path | None:
    if os.name != "nt":
        return None
    target = Path(WINDOWS_INSTALL_DIR)
    source = (source or ROOT).resolve()
    target.mkdir(parents=True, exist_ok=True)
    if source == target.resolve() or (target / "cpcm.py").is_file():
        return target
    for name in ("cpcm.py", "cpcm", "web", "icon.png", "cpcm.ico", "CPCM.bat", "cpcm.sh", "Install-CPCM.ps1", "Create-Shortcut.ps1", "README.md", "examples"):
        src, dst = source / name, target / name
        if not src.exists():
            continue
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
    return target
