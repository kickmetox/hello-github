"""ACPI- und Hersteller-Module als Fähigkeitskarte.

Ein Modul, das nicht geladen ist, gilt nicht als Erfolg.
"""

from __future__ import annotations

from pathlib import Path

VENDORS: dict[str, dict] = {
    "asus": {
        "modules": ["asus_nb_wmi", "asus_wmi"],
        "sysfs": ["/sys/devices/platform/asus-nb-wmi"],
        "capabilities": ["keyboard_backlight", "charge_limit_if_node_exists", "fan_read_if_hwmon"],
        "note_de": "asus_nb_wmi muss geladen sein. Ohne den Plattformknoten gibt es keine ASUS-Lüfterkurve.",
    },
    "lenovo": {
        "modules": ["thinkpad_acpi", "ideapad_laptop"],
        "sysfs": ["/sys/devices/platform/thinkpad_acpi"],
        "capabilities": ["fan_rpm_read", "charge_control_end_threshold", "conservation_mode"],
        "note_de": "ThinkPad-Schwellen liegen an thinkpad_acpi. ideapad_laptop setzt conservation_mode, keine freie Kurve.",
    },
    "hp": {
        "modules": ["hp_wmi"],
        "sysfs": ["/sys/devices/platform/hp-wmi"],
        "capabilities": ["wireless_killswitch", "omen_fan_not_exposed"],
        "note_de": "hp-wmi legt Omen-Lüfter meist nicht als beschreibbares pwm aus. Kein Erfolg ohne Knoten.",
    },
    "dell": {
        "modules": ["dell_smm_hwmon", "dell_wmi"],
        "sysfs": ["/sys/devices/platform/dell-wmi"],
        "capabilities": ["fan_rpm_read", "thermal_read"],
        "note_de": "dell_smm_hwmon liest Drehzahl oft nur. Schreiben wird nicht versucht.",
    },
}


def _module_loaded(name: str) -> bool:
    sysfs = Path("/sys/module") / name
    if sysfs.is_dir():
        return True
    modules = Path("/proc/modules")
    try:
        text = modules.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    token = name.replace("-", "_")
    return any(line.split()[0] == token for line in text.splitlines() if line.strip())


def vendor_map() -> dict:
    entries = []
    for vendor, spec in VENDORS.items():
        modules = [{"name": name, "loaded": _module_loaded(name)} for name in spec["modules"]]
        sysfs_present = []
        for raw in spec["sysfs"]:
            path = Path(raw)
            sysfs_present.append({"path": raw, "exists": path.exists()})
        loaded = any(item["loaded"] for item in modules)
        present = any(item["exists"] for item in sysfs_present)
        entries.append(
            {
                "vendor": vendor,
                "modules": modules,
                "sysfs": sysfs_present,
                "capabilities": spec["capabilities"],
                "note_de": spec["note_de"],
                "usable": loaded and present,
            }
        )
    return {"vendors": entries, "applied": False}
