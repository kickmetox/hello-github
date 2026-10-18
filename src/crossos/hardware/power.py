"""Windows-Energiesparpläne ↔ power-profiles-daemon und TLP.

Anwenden auf Linux nur über powerprofilesctl, nur mit confirm=true,
und nur wenn das Programm existiert. TLP-Konfiguration bleibt Text.
"""

from __future__ import annotations

import shutil
import subprocess

from crossos.safety import SafetyError, require_confirm

PLANS: list[dict] = [
    {
        "id": "saver",
        "windows_name": "Energiesparmodus",
        "windows_guid": "a1841308-3541-4fab-bc81-f71556f20b4a",
        "ppd": "power-saver",
        "tlp_governor_ac": "powersave",
        "tlp_governor_bat": "powersave",
    },
    {
        "id": "balanced",
        "windows_name": "Ausbalanciert",
        "windows_guid": "381b4222-f694-41f0-9685-ff5bb260df2e",
        "ppd": "balanced",
        "tlp_governor_ac": "schedutil",
        "tlp_governor_bat": "powersave",
    },
    {
        "id": "performance",
        "windows_name": "Höchstleistung",
        "windows_guid": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
        "ppd": "performance",
        "tlp_governor_ac": "performance",
        "tlp_governor_bat": "performance",
    },
    {
        "id": "ultimate",
        "windows_name": "Ultimative Leistung",
        "windows_guid": "e9a42b02-d5df-448d-aa00-03f14749eb61",
        "ppd": "performance",
        "ppd_note": "power-profiles-daemon hat keine Stufe über performance. Ultimative Leistung fällt darauf zurück.",
        "tlp_governor_ac": "performance",
        "tlp_governor_bat": "performance",
    },
]


def list_plans() -> dict:
    rows = []
    for plan in PLANS:
        rows.append(
            {
                **plan,
                "windows_argv": ["powercfg", "/setactive", plan["windows_guid"]],
                "ppd_argv": ["powerprofilesctl", "set", plan["ppd"]],
                "tlp_snippet": (
                    f"# /etc/tlp.conf — Plan, wird nicht geschrieben\n"
                    f"CPU_SCALING_GOVERNOR_ON_AC={plan['tlp_governor_ac']}\n"
                    f"CPU_SCALING_GOVERNOR_ON_BAT={plan['tlp_governor_bat']}\n"
                ),
            }
        )
    return {
        "plans": rows,
        "powerprofilesctl": shutil.which("powerprofilesctl"),
        "tlp": shutil.which("tlp"),
        "executed": False,
    }


def apply_ppd(plan_id: str, *, confirm: object) -> dict:
    plan = next((item for item in PLANS if item["id"] == plan_id), None)
    if plan is None:
        raise SafetyError("Unbekannter Energiesparplan.")
    described = list_plans()
    selected = next(item for item in described["plans"] if item["id"] == plan_id)
    if confirm is not True:
        return selected | {"executed": False, "dry_run": True, "reason_de": "Ohne confirm=true bleibt es beim Plan."}
    require_confirm(confirm)
    binary = shutil.which("powerprofilesctl")
    if binary is None:
        return selected | {
            "executed": False,
            "dry_run": True,
            "reason_de": "powerprofilesctl ist nicht installiert. Der TLP-Schnipsel wird nicht geschrieben.",
        }
    profile = plan["ppd"]
    if profile not in {"power-saver", "balanced", "performance"}:
        raise SafetyError("ppd-Profil abgelehnt.")
    completed = subprocess.run([binary, "set", profile], capture_output=True, text=True, timeout=15, check=False)
    return selected | {
        "executed": True,
        "dry_run": False,
        "returncode": completed.returncode,
        "stdout": (completed.stdout or "")[-2000:],
        "stderr": (completed.stderr or "")[-2000:],
    }
