"""Gemeinsame Lüfter-, Leistungs- und Ladeprofile. Spannung wird nur gespeichert."""

from __future__ import annotations

import json
import os
from pathlib import Path

PROFILES = {
    "Silent": {"curve": [[40, 15], [55, 25], [70, 40], [85, 70]], "cpu_max_pct": 50, "charge_start": 40, "charge_stop": 80, "undervolt_mv": 0, "linux_power": "power-saver", "windows_plan": "Power saver"},
    "Balanced": {"curve": [[40, 25], [60, 40], [75, 60], [90, 85]], "cpu_max_pct": 80, "charge_start": 50, "charge_stop": 90, "undervolt_mv": 0, "linux_power": "balanced", "windows_plan": "Balanced"},
    "Performance": {"curve": [[40, 40], [60, 60], [75, 80], [85, 100]], "cpu_max_pct": 100, "charge_start": 70, "charge_stop": 100, "undervolt_mv": 0, "linux_power": "performance", "windows_plan": "High performance"},
    "Turbo": {"curve": [[35, 50], [50, 70], [65, 90], [75, 100]], "cpu_max_pct": 100, "charge_start": 80, "charge_stop": 100, "undervolt_mv": 0, "linux_power": "performance", "windows_plan": "Ultimate Performance"},
}
LINUX_POWER = {"power-saver", "balanced", "performance"}


def validate_profile(profile: dict) -> dict:
    name = str(profile.get("name") or "")
    if not name or any(ch in name for ch in "/\\"):
        raise ValueError("Profilname fehlt")
    curve = profile.get("curve") or []
    if len(curve) < 2:
        raise ValueError("Eine Lüfterkurve braucht mindestens zwei Punkte")
    cleaned, last = [], -1
    for point in curve:
        temp, duty = int(point[0]), int(point[1])
        if not 0 <= temp <= 110 or not 0 <= duty <= 100:
            raise ValueError("Temperatur 0–110 °C, Duty 0–100 %")
        if temp <= last:
            raise ValueError("Temperaturen müssen streng steigen")
        last = temp
        cleaned.append([temp, duty])
    cpu, start, stop = int(profile.get("cpu_max_pct", 100)), int(profile.get("charge_start", 40)), int(profile.get("charge_stop", 80))
    offset = int(profile.get("undervolt_mv", 0))
    if not 5 <= cpu <= 100:
        raise ValueError("CPU-Limit muss zwischen 5 und 100 liegen")
    if not 20 <= start < stop <= 100:
        raise ValueError("Ladestart muss unter Ladestopp liegen (20–100)")
    if not -200 <= offset <= 0:
        raise ValueError("Undervolt nur als Absenkung bis -200 mV, 0 heißt aus")
    linux_power = str(profile.get("linux_power") or "balanced")
    if linux_power not in LINUX_POWER:
        raise ValueError("Linux-Leistungsprofil unbekannt")
    return {
        "name": name, "curve": cleaned, "cpu_max_pct": cpu, "charge_start": start, "charge_stop": stop,
        "undervolt_mv": offset, "linux_power": linux_power, "windows_plan": str(profile.get("windows_plan") or "Balanced"),
        "note": "Der Spannungs-Offset wird gespeichert und nicht angewendet." if offset else "Kein Spannungs-Offset.",
    }


def default_profiles() -> dict:
    return {name: validate_profile({"name": name, **raw}) for name, raw in PROFILES.items()}


def profiles_path(vault: Path) -> Path:
    return vault / "hardware-profiles.json"


def load_profiles(vault: Path) -> dict:
    path = profiles_path(vault)
    if not path.is_file():
        data = {"active": "Balanced", "profiles": default_profiles()}
        save_profiles(vault, data)
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def save_profiles(vault: Path, data: dict) -> None:
    vault.mkdir(parents=True, exist_ok=True)
    profiles_path(vault).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def set_active(vault: Path, name: str) -> dict:
    data = load_profiles(vault)
    if name not in data["profiles"]:
        raise KeyError(name)
    data["active"] = name
    save_profiles(vault, data)
    return data


def upsert_profile(vault: Path, profile: dict) -> dict:
    cleaned = validate_profile(profile)
    data = load_profiles(vault)
    data["profiles"][cleaned["name"]] = cleaned
    data["active"] = cleaned["name"]
    save_profiles(vault, data)
    return data


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def probe() -> dict:
    info = {"world": "windows" if os.name == "nt" else "linux", "batteries": [], "thermal": [], "cpufreq": None, "power_profile": None}
    if os.name == "nt":
        info["note"] = "Unter Windows liegen die Profile im Vault. powercfg wird nicht mit freien Befehlen aufgerufen."
        return info
    supply = Path("/sys/class/power_supply")
    if supply.is_dir():
        for node in sorted(supply.iterdir()):
            if _read_text(node / "type") != "Battery":
                continue
            info["batteries"].append({
                "name": node.name,
                "capacity": _read_text(node / "capacity"),
                "status": _read_text(node / "status"),
                "charge_stop": _read_text(node / "charge_control_end_threshold"),
                "charge_start": _read_text(node / "charge_control_start_threshold"),
            })
    thermal = Path("/sys/class/thermal")
    if thermal.is_dir():
        for node in sorted(thermal.glob("thermal_zone*")):
            temp = _read_text(node / "temp")
            info["thermal"].append({"name": node.name, "type": _read_text(node / "type"), "celsius": None if temp is None else round(int(temp) / 1000, 1)})
    freq = _read_text(Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"))
    if freq and freq.isdigit():
        info["cpufreq"] = round(int(freq) / 1000)
    info["power_profile"] = _read_text(Path("/sys/firmware/acpi/platform_profile"))
    info["note"] = "Sichtbar ist, was das System unter /sys bereits anbietet. Spannung wird nicht geschrieben."
    return info


def charge_threshold_node(battery: str, which: str) -> Path:
    if which not in ("start", "end") or not battery or any(ch in battery for ch in "/.\\"):
        raise ValueError("Ladeschwelle oder Akkuname ungültig")
    filename = "charge_control_start_threshold" if which == "start" else "charge_control_end_threshold"
    return Path("/sys/class/power_supply") / battery / filename


def write_charge_threshold(battery: str, which: str, value: int, *, node: Path | None = None) -> str:
    if not 20 <= int(value) <= 100:
        raise ValueError("Schwelle muss zwischen 20 und 100 liegen")
    target = node or charge_threshold_node(battery, which)
    if not target.is_file():
        raise FileNotFoundError(f"Keine Ladeschwelle unter {target}")
    if not os.access(target, os.W_OK):
        raise PermissionError(f"Ladeschwelle ist nicht beschreibbar: {target}")
    target.write_text(str(int(value)), encoding="utf-8")
    return str(target)
