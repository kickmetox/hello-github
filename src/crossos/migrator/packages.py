"""Eine API für winget, scoop, apt, pacman, dnf, flatpak und snap.

Namen werden geprüft, bevor ein argv oder ein Shell-String existiert.
Installation läuft nur mit confirm=true, dry_run=false und der
Umgebungsvariable CROSSOS_ALLOW_PACKAGE_INSTALL=1.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass

from crossos.safety import SafetyError, validate_package_name

MANAGERS: dict[str, dict] = {
    "winget": {
        "binary": "winget",
        "platforms": ["windows"],
        "install": ["winget", "install", "--exact", "--id"],
        "remove": ["winget", "uninstall", "--exact", "--id"],
        "search": ["winget", "search", "--exact", "--id"],
    },
    "scoop": {
        "binary": "scoop",
        "platforms": ["windows"],
        "install": ["scoop", "install"],
        "remove": ["scoop", "uninstall"],
        "search": ["scoop", "search"],
    },
    "apt": {
        "binary": "apt-get",
        "platforms": ["linux"],
        "install": ["apt-get", "install", "--yes"],
        "remove": ["apt-get", "remove", "--yes"],
        "search": ["apt-cache", "search", "--names-only"],
    },
    "pacman": {
        "binary": "pacman",
        "platforms": ["linux"],
        "install": ["pacman", "-S", "--noconfirm"],
        "remove": ["pacman", "-R", "--noconfirm"],
        "search": ["pacman", "-Ss"],
    },
    "dnf": {
        "binary": "dnf",
        "platforms": ["linux"],
        "install": ["dnf", "install", "-y"],
        "remove": ["dnf", "remove", "-y"],
        "search": ["dnf", "search"],
    },
    "flatpak": {
        "binary": "flatpak",
        "platforms": ["linux"],
        "install": ["flatpak", "install", "-y"],
        "remove": ["flatpak", "uninstall", "-y"],
        "search": ["flatpak", "search"],
    },
    "snap": {
        "binary": "snap",
        "platforms": ["linux"],
        "install": ["snap", "install"],
        "remove": ["snap", "remove"],
        "search": ["snap", "find"],
    },
}


@dataclass
class PackageBridge:
    """Plant und — nur unter harten Bedingungen — startet Paketmanager."""

    def detect(self) -> dict:
        found = {}
        for name, spec in MANAGERS.items():
            binary = spec["binary"]
            path = shutil.which(binary)
            entry = {
                "present": path is not None,
                "path": path,
                "platforms": spec["platforms"],
                "version_line": None,
            }
            if path and name == "apt":
                entry["version_line"] = _version_line(path)
            found[name] = entry
        return {"managers": found, "present": [name for name, item in found.items() if item["present"]]}

    def plan(self, manager: str, packages: list[str], action: str = "install") -> dict:
        argv = self._argv(manager, packages, action)
        spec = MANAGERS[manager]
        present = shutil.which(spec["binary"]) is not None
        return {
            "manager": manager,
            "action": action,
            "packages": [validate_package_name(name) for name in packages],
            "argv": argv,
            "shell": shlex.join(argv),
            "manager_present": present,
            "executed": False,
            "dry_run": True,
        }

    def drive(
        self,
        manager: str,
        packages: list[str],
        action: str = "install",
        *,
        confirm: bool = False,
        dry_run: bool = True,
    ) -> dict:
        planned = self.plan(manager, packages, action)
        if dry_run or confirm is not True:
            planned["blocked"] = "Dry-Run ist der Standard. Ausführung braucht confirm=true und dry_run=false."
            return planned
        if os.environ.get("CROSSOS_ALLOW_PACKAGE_INSTALL") != "1":
            planned["blocked"] = "CROSSOS_ALLOW_PACKAGE_INSTALL ist nicht gesetzt. Es wurde nichts installiert oder entfernt."
            return planned
        if action not in {"install", "remove"}:
            planned["blocked"] = "Nur install und remove können überhaupt gestartet werden."
            return planned
        if not planned["manager_present"]:
            planned["blocked"] = "Paketmanager ist auf diesem System nicht vorhanden."
            return planned
        completed = subprocess.run(planned["argv"], capture_output=True, text=True, timeout=120, check=False)
        planned["executed"] = True
        planned["dry_run"] = False
        planned["returncode"] = completed.returncode
        planned["stdout"] = completed.stdout[-4000:]
        planned["stderr"] = completed.stderr[-4000:]
        return planned

    def _argv(self, manager: str, packages: list[str], action: str) -> list[str]:
        if manager not in MANAGERS:
            raise SafetyError("Unbekannter Paketmanager.")
        if action not in {"install", "remove", "search"}:
            raise SafetyError("Aktion muss install, remove oder search sein.")
        # Validierung zuerst: bei einem ungültigen Namen gibt es kein argv.
        clean = [validate_package_name(name) for name in packages]
        if not clean:
            raise SafetyError("Mindestens ein Paketname ist erforderlich.")
        prefix = list(MANAGERS[manager][action])
        if manager == "apt" and action == "search":
            # apt-cache search nimmt einen Begriff, keine Paketliste mit Flags davor.
            return prefix + clean
        return prefix + clean


def _version_line(binary: str) -> str | None:
    try:
        completed = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (completed.stdout or completed.stderr or "").strip()
    return text.splitlines()[0] if text else None
