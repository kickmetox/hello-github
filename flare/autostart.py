"""Start mit der Windows-Anmeldung über den Run-Schlüssel."""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path


def launch_command(background: bool = True) -> str:
    # PyInstaller setzt sys.frozen. Dann ist sys.executable bereits Flare.exe.
    if getattr(sys, "frozen", False):
        args = [sys.executable]
        if background:
            args.append("--background")
        if sys.platform == "win32":
            return subprocess.list2cmdline(args)
        return shlex.join(args)
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


_RUN_KEY = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run\Flare"
_RUN_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _require_windows() -> None:
    if sys.platform != "win32":
        raise RuntimeError("Autostart gibt es nur unter Windows 11.")


def install_autostart() -> str:
    _require_windows()
    import winreg

    command = launch_command(True)
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_PATH, 0, winreg.KEY_SET_VALUE)
    try:
        winreg.SetValueEx(key, "Flare", 0, winreg.REG_SZ, command)
    finally:
        key.Close()
    return _RUN_KEY


def remove_autostart() -> str:
    _require_windows()
    import winreg

    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_PATH, 0, winreg.KEY_SET_VALUE)
    try:
        winreg.DeleteValue(key, "Flare")
    except FileNotFoundError:
        pass
    finally:
        key.Close()
    return _RUN_KEY
