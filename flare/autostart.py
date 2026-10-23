"""Start mit der Anmeldung. Windows: Run-Schlüssel. Linux: XDG-Autostart."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path


def launch_command(background: bool = True) -> str:
    exe = Path(sys.executable)
    if sys.platform == "win32":
        pythonw = exe.with_name("pythonw.exe")
        if pythonw.exists():
            exe = pythonw
    launcher = Path(__file__).resolve().parent.parent / "flare.py"
    args = [str(exe)]
    if launcher.exists():
        args.append(str(launcher))
    else:
        args.extend(["-m", "flare"])
    if background:
        args.append("--background")
    if sys.platform == "win32":
        return subprocess.list2cmdline(args)
    return shlex.join(args)


def autostart_path(config_home: Path | None = None) -> Path:
    if config_home is None:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        config_home = Path(xdg) if xdg else Path.home() / ".config"
    return config_home / "autostart" / "flare.desktop"


def install_autostart(config_home: Path | None = None) -> str:
    command = launch_command(True)
    if sys.platform == "win32":
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        try:
            winreg.SetValueEx(key, "Flare", 0, winreg.REG_SZ, command)
        finally:
            key.Close()
        return r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run\Flare"
    path = autostart_path(config_home)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "[Desktop Entry]",
                "Type=Application",
                "Version=1.0",
                "Name=Flare",
                "Comment=Spotlight-ähnliche Suche",
                f"Exec={command}",
                "Terminal=false",
                "X-GNOME-Autostart-enabled=true",
                "Categories=Utility;",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return str(path)


def remove_autostart(config_home: Path | None = None) -> str:
    if sys.platform == "win32":
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        try:
            winreg.DeleteValue(key, "Flare")
        except FileNotFoundError:
            pass
        finally:
            key.Close()
        return r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run\Flare"
    path = autostart_path(config_home)
    if path.exists():
        path.unlink()
    return str(path)
