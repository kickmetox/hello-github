"""Plattform erkennen, ohne Fähigkeiten zu erfinden."""

from __future__ import annotations

import platform
import shutil
from pathlib import Path


def detect_platform() -> dict:
    system = platform.system()
    info = {
        "system": system,
        "machine": platform.machine(),
        "python": platform.python_version(),
        "kernel": platform.release(),
        "wsl": False,
        "os_release": {},
    }
    if system == "Linux":
        version_file = Path("/proc/version")
        try:
            version = version_file.read_text(encoding="utf-8", errors="replace").lower()
        except OSError:
            version = ""
        info["wsl"] = "microsoft" in version or "wsl" in version
        info["os_release"] = _os_release()
    info["tools"] = {
        name: shutil.which(name) is not None
        for name in (
            "apt-get",
            "dpkg",
            "pacman",
            "dnf",
            "flatpak",
            "snap",
            "winget",
            "scoop",
            "systemctl",
            "fwupdmgr",
            "powerprofilesctl",
            "tlp",
            "ntfsfix",
            "ntfsinfo",
            "fsck",
            "gsettings",
            "xfconf-query",
        )
    }
    return info


def _os_release() -> dict[str, str]:
    path = Path("/etc/os-release")
    data: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return data
    for line in text.splitlines():
        if "=" not in line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        data[key] = value.strip().strip('"')
    return data


def default_shell_for_host() -> str:
    if platform.system() == "Windows":
        return "powershell"
    return "bash"
