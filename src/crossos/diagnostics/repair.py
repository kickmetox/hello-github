"""Reparaturskripte erzeugen und nur freigegebene Leseaktionen ausführen.

Dateisystemreparatur, Firmware und Spannung sind nicht auf der Liste.
Es gibt kein shell=True.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from crossos.safety import SafetyError, ensure_within, require_confirm, validate_package_name, validate_unit_name

# Nur lesende oder prüfende Aktionen. argv ist fest oder aus geprüften Teilen gebaut.
ALLOWLIST: dict[str, dict] = {
    "disk-free": {
        "argv": ["df", "-hT"],
        "summary_de": "Zeigt die Belegung der Dateisysteme. Ändert nichts.",
        "mutates": False,
    },
    "failed-units": {
        "argv": ["systemctl", "--failed", "--no-pager", "--plain"],
        "summary_de": "Listet fehlgeschlagene systemd-Units. Startet nichts neu.",
        "mutates": False,
    },
    "apt-check": {
        "argv": ["apt-get", "check"],
        "summary_de": "Prüft den dpkg/apt-Zustand ohne Installation und ohne -f.",
        "mutates": False,
    },
    "uname": {
        "argv": ["uname", "-a"],
        "summary_de": "Zeigt Kernel und Architektur.",
        "mutates": False,
    },
    "locale-show": {
        "argv": ["locale"],
        "summary_de": "Zeigt die Locale-Variablen.",
        "mutates": False,
    },
}


def allowlist_public() -> list[dict]:
    return [
        {"id": key, "summary_de": value["summary_de"], "mutates": value["mutates"], "argv": value["argv"]}
        for key, value in ALLOWLIST.items()
    ]


def link_apply(code: str, *, unit: str | None = None) -> dict:
    mapping = {
        "apt-broken": "apt-check",
        "systemd-failed": "failed-units",
        "0x80070070": "disk-free",
        "oom": "uname",
        "segfault": "uname",
    }
    action = mapping.get(code)
    if action is None:
        return {
            "eligible": False,
            "action_id": None,
            "requires_confirm": True,
            "mutates": False,
            "reason_de": "Für diesen Befund gibt es keine freigegebene Ein-Klick-Aktion. Das Skript bleibt ein Plan.",
        }
    spec = ALLOWLIST[action]
    return {
        "eligible": True,
        "action_id": action,
        "requires_confirm": True,
        "mutates": spec["mutates"],
        "reason_de": spec["summary_de"],
        "unit": unit,
    }


def render_scripts(finding: dict) -> dict:
    code = finding["code"]
    bash = _bash(finding)
    powershell = _powershell(finding)
    return {"bash": bash, "powershell": powershell, "code": code, "executable": False}


def _bash(finding: dict) -> str:
    code = finding["code"]
    lines = [
        "#!/usr/bin/env bash",
        "# CrossOS-Plan. Wird nicht automatisch ausgeführt.",
        "set -euo pipefail",
        f"# Befund: {finding['title']} ({code})",
    ]
    if code == "apt-broken":
        lines += [
            "apt-get check",
            "# Änderung wäre erst dieser Plan, und auch der ist nicht freigegeben:",
            "# apt-get -s -f install",
            "# dpkg --configure -a",
        ]
    elif code == "systemd-failed":
        unit = finding.get("unit") or "UNIT.service"
        lines += [
            f"systemctl status --no-pager --full {unit}",
            f"journalctl -u {unit} -n 80 --no-pager",
            "# systemctl restart ist nicht freigegeben.",
        ]
    elif code == "missing-so":
        lines += [
            "# Bibliothek aus der Meldung suchen, nicht raten:",
            "# apt-file search <name>.so",
            "ldconfig -p | head",
        ]
    elif code == "segfault":
        lines += [
            "uname -a",
            "command -v coredumpctl >/dev/null && coredumpctl list --no-pager | head || true",
            "# ldd am betroffenen Programm zeigt fehlende Bibliotheken. Pfad nicht von CrossOS eingesetzt.",
        ]
    elif code in {"ext4-error", "io-error", "readonly-fs"}:
        lines += [
            "lsblk -f",
            "# fsck nur am nicht gemounteten Gerät und nur als Plan:",
            "# fsck -n /dev/GERAET",
            "# Kein fsck -y, kein ntfsfix ohne --no-action.",
        ]
    elif code == "oom":
        lines += ["free -h", "uname -a"]
    elif code == "0x80070070":
        lines += ["df -hT"]
    else:
        lines += ["echo 'Kein Schreibschritt in diesem Plan.'"]
    return "\n".join(lines) + "\n"


def _powershell(finding: dict) -> str:
    code = finding["code"]
    lines = [
        "# CrossOS-Plan. Wird nicht automatisch ausgeführt.",
        f"# Befund: {finding['title']} ({code})",
        "$ErrorActionPreference = 'Continue'",
    ]
    if code == "0x80070005":
        lines += [
            "Get-Acl -Path $env:USERPROFILE | Format-List",
            "# icacls.exe wird nicht aufgerufen.",
        ]
    elif code == "0x80070002":
        lines += [
            "Get-ChildItem -Path $env:USERPROFILE -ErrorAction SilentlyContinue | Select-Object -First 5",
            "# Fehlende Update-Payload nicht mit Clear-WindowsUpdateCache ersetzen, solange die Quelle unklar ist.",
        ]
    elif code == "missing-dll":
        lines += [
            "Get-Item -ErrorAction SilentlyContinue ($env:windir + '\\System32\\vcruntime140.dll')",
            "# winget install Microsoft.VCRedist.2015+.x64   # Plan, nicht gestartet",
        ]
    elif code == "0x80070070":
        lines += ["Get-PSDrive -PSProvider FileSystem"]
    elif code in {"0x80070422", "event-7031"}:
        lines += [
            "Get-Service | Where-Object { $_.Status -eq 'Stopped' -and $_.StartType -eq 'Disabled' } | Select-Object -First 20",
            "# Set-Service -StartupType wird nicht ausgeführt.",
        ]
    elif code in {"0xc0000005", "event-1000"}:
        lines += [
            "Get-WinEvent -FilterHashtable @{LogName='Application'; Id=1000} -MaxEvents 5 -ErrorAction SilentlyContinue",
        ]
    else:
        lines += ["Write-Output 'Kein Schreibschritt in diesem Plan.'"]
    return "\n".join(lines) + "\n"


def apply_allowlisted(
    action_id: str,
    *,
    confirm: object,
    package: str | None = None,
    path: str | None = None,
    unit: str | None = None,
    roots: list[Path] | None = None,
) -> dict:
    """Führt nur eine freigegebene Aktion aus. Alles andere wirft SafetyError."""
    if action_id not in ALLOWLIST:
        raise SafetyError("Aktion ist nicht auf der Freigabeliste. Dateisystem, Firmware und Spannung bleiben Plan.")
    require_confirm(confirm)
    if package is not None:
        # Auch wenn die Aktion den Namen nicht anhängt: erst prüfen, dann nichts einsetzen.
        validate_package_name(package)
        raise SafetyError("Diese freigegebene Aktion nimmt keinen Paketnamen entgegen.")
    if unit is not None:
        validate_unit_name(unit)
    if path is not None:
        if not roots:
            raise SafetyError("Für Pfade ist keine Wurzel freigegeben.")
        # list-dir ist absichtlich nicht auf der Allowlist. Ein Pfad an einer
        # Leseaktion wird geprüft und dann abgelehnt, damit Traversal auffällt.
        for root in roots:
            ensure_within(Path(path), root)
        raise SafetyError("Freigegebene Aktionen nehmen keinen Pfad entgegen.")

    spec = ALLOWLIST[action_id]
    argv = list(spec["argv"])
    binary = shutil.which(argv[0])
    if binary is None:
        return {
            "action_id": action_id,
            "executed": False,
            "reason_de": f"Werkzeug {argv[0]} ist auf diesem System nicht vorhanden.",
            "argv": argv,
        }
    argv[0] = binary
    completed = subprocess.run(argv, capture_output=True, text=True, timeout=30, check=False)
    return {
        "action_id": action_id,
        "executed": True,
        "mutates": False,
        "argv": argv,
        "returncode": completed.returncode,
        "stdout": (completed.stdout or "")[-8000:],
        "stderr": (completed.stderr or "")[-4000:],
    }
