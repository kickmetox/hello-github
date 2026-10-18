"""Ladegrenzen. Schreiben nur, wenn der sysfs-Knoten existiert, beschreibbar ist und confirm=true."""

from __future__ import annotations

import json
import os
from pathlib import Path

from crossos.safety import SafetyError, ensure_within, require_confirm

_FILENAMES = {"charge_control_end_threshold", "charge_stop_threshold"}


def validate_threshold(value: object) -> int:
    if type(value) is not int:
        raise SafetyError("Ladeschwelle muss eine ganze Zahl sein.")
    if not 20 <= value <= 100:
        raise SafetyError("Ladeschwelle muss zwischen 20 und 100 Prozent liegen.")
    return value


def candidate_nodes(sysfs_root: Path) -> list[Path]:
    if not sysfs_root.is_dir():
        return []
    found = []
    for name in sorted(_FILENAMES):
        found.extend(sorted(sysfs_root.glob(f"*/{name}")))
    return found


def apply_threshold(
    percent: object,
    *,
    confirm: object,
    state_file: Path,
    node: str | None = None,
    sysfs_root: Path | None = None,
) -> dict:
    value = validate_threshold(percent)
    root = sysfs_root or Path("/sys/class/power_supply")
    chosen = _select_node(root, node)
    state = _load(state_file)
    profiles = state.setdefault("charge_profiles", [])
    profile = {"stop_percent": value, "node": str(chosen) if chosen else None}
    profiles.append(profile)
    state["charge_profiles"] = profiles[-20:]
    _store(state_file, state)

    result = {
        "stop_percent": value,
        "stored": True,
        "node": str(chosen) if chosen else None,
        "written": False,
        "confirmed": confirm is True,
    }
    if chosen is None:
        result["reason_de"] = "Kein charge_control_end_threshold oder charge_stop_threshold unter dem sysfs-Wurzelpfad. Profil ist nur gespeichert."
        return result
    if not chosen.exists():
        result["reason_de"] = "Der Knoten existiert nicht."
        return result
    if not os.access(chosen, os.W_OK):
        result["reason_de"] = "Der Knoten ist nicht beschreibbar. Nichts geschrieben."
        return result
    if confirm is not True:
        result["reason_de"] = "Knoten wäre beschreibbar. Ohne confirm=true wird nicht geschrieben."
        return result
    require_confirm(confirm)
    chosen.write_text(f"{value}\n", encoding="utf-8")
    result["written"] = True
    result["readback"] = chosen.read_text(encoding="utf-8").strip()
    return result


def _select_node(root: Path, node: str | None) -> Path | None:
    if node is None:
        found = candidate_nodes(root)
        return found[0] if found else None
    raw = Path(node)
    if raw.name not in _FILENAMES:
        raise SafetyError("Nur charge_control_end_threshold oder charge_stop_threshold sind beschreibbar.")
    # Relativer Knoten wird unter der Wurzel aufgelöst. Absolute Pfade müssen
    # trotzdem innerhalb der Wurzel liegen.
    resolved = ensure_within(raw, root)
    return resolved


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _store(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
