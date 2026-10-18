"""Hardware lesen: Linux über sysfs, Windows als Kommandoplan.

Temperaturen in sysfs stehen in Milligrad Celsius, cpufreq in Kilohertz.
Fehlende Knoten bleiben leer, statt einen Wert zu erfinden.
"""

from __future__ import annotations

import platform
from pathlib import Path

from crossos.hardware.vendors import vendor_map


def probe() -> dict:
    system = platform.system()
    if system == "Windows":
        return {
            "os": "windows",
            "executed_local_read": False,
            "readings": None,
            "commands": [
                ["powercfg", "/getactivescheme"],
                ["powercfg", "/list"],
                ["powercfg", "/query"],
                ["powershell", "-NoProfile", "-Command", "Get-CimInstance -ClassName Win32_Battery"],
                ["powershell", "-NoProfile", "-Command", "Get-CimInstance -ClassName Win32_Fan"],
                ["powershell", "-NoProfile", "-Command", "Get-CimInstance -Namespace root\\wmi -ClassName MSAcpi_ThermalZoneTemperature"],
            ],
            "note_de": "Auf Windows werden die Befehle nur erzeugt. Diese Instanz führt sie nicht aus, solange sie nicht selbst unter Windows läuft.",
            "vendors": vendor_map(),
        }
    readings = {
        "thermal": _thermal(),
        "hwmon": _hwmon(),
        "cpufreq": _cpufreq(),
        "power_supply": _power_supply(),
    }
    limitations = []
    if not readings["thermal"]:
        limitations.append("Kein lesbarer thermal_zone-Knoten.")
    if not readings["hwmon"]:
        limitations.append("Kein lesbarer hwmon-Knoten.")
    if not readings["cpufreq"]:
        limitations.append("Kein cpufreq-Knoten. In dieser Umgebung oft eine virtuelle CPU ohne Governor-Sysfs.")
    if not readings["power_supply"]:
        limitations.append("Kein power_supply-Knoten. Diese VM hat keine Batterie im sysfs.")
    return {
        "os": "linux",
        "executed_local_read": True,
        "readings": readings,
        "limitations": limitations,
        "vendors": vendor_map(),
        "commands_if_windows": [
            ["powercfg", "/getactivescheme"],
            ["powercfg", "/list"],
        ],
    }


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None


def _thermal() -> list[dict]:
    root = Path("/sys/class/thermal")
    zones = []
    if not root.is_dir():
        return zones
    for zone in sorted(root.glob("thermal_zone*")):
        raw = _read(zone / "temp")
        if raw is None or not raw.lstrip("-").isdigit():
            continue
        milli = int(raw)
        zones.append(
            {
                "name": zone.name,
                "type": _read(zone / "type"),
                "temp_c": round(milli / 1000, 1),
            }
        )
    return zones


def _hwmon() -> list[dict]:
    root = Path("/sys/class/hwmon")
    chips = []
    if not root.is_dir():
        return chips
    for chip in sorted(root.glob("hwmon*")):
        temps = []
        for temp in sorted(chip.glob("temp*_input")):
            raw = _read(temp)
            if raw is None or not raw.lstrip("-").isdigit():
                continue
            label = _read(chip / temp.name.replace("_input", "_label"))
            temps.append({"input": temp.name, "label": label, "temp_c": round(int(raw) / 1000, 1)})
        fans = []
        for fan in sorted(chip.glob("fan*_input")):
            raw = _read(fan)
            if raw is None or not raw.isdigit():
                continue
            fans.append({"input": fan.name, "rpm": int(raw)})
        pwms = [entry.name for entry in sorted(chip.glob("pwm[0-9]*")) if entry.is_file() and "_" not in entry.name]
        chips.append({"name": _read(chip / "name"), "path": str(chip), "temps": temps, "fans": fans, "pwm": pwms})
    return chips


def _cpufreq() -> list[dict]:
    root = Path("/sys/devices/system/cpu")
    cpus = []
    if not root.is_dir():
        return cpus
    for cpu in sorted(root.glob("cpu[0-9]*")):
        freq = cpu / "cpufreq"
        if not freq.is_dir():
            continue
        current = _read(freq / "scaling_cur_freq")
        cpus.append(
            {
                "cpu": cpu.name,
                "governor": _read(freq / "scaling_governor"),
                "cur_khz": int(current) if current and current.isdigit() else None,
            }
        )
    return cpus


def _power_supply() -> list[dict]:
    root = Path("/sys/class/power_supply")
    supplies = []
    if not root.is_dir():
        return supplies
    interesting = (
        "type",
        "status",
        "capacity",
        "charge_control_end_threshold",
        "charge_stop_threshold",
        "energy_full",
        "energy_now",
    )
    for supply in sorted(root.iterdir()):
        if not supply.is_dir():
            continue
        fields = {}
        for name in interesting:
            value = _read(supply / name)
            if value is not None:
                fields[name] = value
        if fields:
            supplies.append({"name": supply.name, "fields": fields})
    return supplies
