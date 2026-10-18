"""Firmware nur lesen. Es wird nie geflasht."""

from __future__ import annotations

import shutil
import subprocess


def firmware_status() -> dict:
    tool = shutil.which("fwupdmgr")
    base = {
        "flashed": False,
        "update_invoked": False,
        "forbidden": ["fwupdmgr update", "fwupdmgr install", "Windows-Update Treiberinstallation automatisch"],
    }
    if tool:
        try:
            completed = subprocess.run(
                [tool, "get-devices"],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return base | {
                "mode": "read-only",
                "tool": tool,
                "executed_read": False,
                "reason_de": "fwupdmgr get-devices hat nicht rechtzeitig geantwortet.",
            }
        return base | {
            "mode": "read-only",
            "tool": tool,
            "executed_read": True,
            "returncode": completed.returncode,
            "stdout": (completed.stdout or "")[:8000],
            "stderr": (completed.stderr or "")[:2000],
            "plan_de": "LVFS wird über fwupdmgr gelesen. Ein Update wird nicht angestoßen.",
        }
    return base | {
        "mode": "plan",
        "tool": None,
        "executed_read": False,
        "plan_de": (
            "fwupdmgr ist nicht installiert. Unter Linux kommt Firmware über LVFS "
            "(Paket fwupd, Befehl nur zum Lesen: fwupdmgr get-devices). Unter Windows "
            "kommt dasselbe Gerät über Windows Update, optionale Updates und den "
            "Hersteller-Katalog. CrossOS schreibt keine Firmware."
        ),
        "linux_steps": [
            "Paket fwupd nur als Plan: apt-get install fwupd",
            "Lesen: fwupdmgr get-devices",
            "Lesen: fwupdmgr get-updates",
            "Nicht ausführen: fwupdmgr update",
        ],
        "windows_steps": [
            "Einstellungen → Windows Update → Erweiterte Optionen → Optionale Updates",
            "Hersteller-Support nur lesen, kein automatisches BIOS-Flash",
            "Kein powercfg und kein Firmware-Write aus dieser Suite",
        ],
    }
