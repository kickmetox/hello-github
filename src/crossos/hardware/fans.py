"""Lüfterprofile mit denselben Schwellen auf beiden Systemen.

Die Kurve ist Daten. Sie wird nicht in pwm-Dateien geschrieben: ein falscher
Duty kann die Kühlung abschalten. Export nach Linux und Windows enthält
dieselben Punkte und einen Hinweis, welches Treiberinterface fehlt.
"""

from __future__ import annotations

from crossos.safety import SafetyError

# (Temperatur °C, Duty %). Auf beiden Systemen identisch.
PROFILES: dict[str, tuple[tuple[int, int], ...]] = {
    "silent": ((40, 20), (55, 30), (70, 45), (85, 70), (95, 100)),
    "balanced": ((40, 30), (55, 45), (70, 65), (80, 80), (90, 100)),
    "performance": ((35, 40), (50, 60), (65, 80), (75, 95), (85, 100)),
    "turbo": ((30, 55), (45, 75), (60, 90), (70, 100)),
}


def validate_curve(points: object) -> list[dict]:
    if not isinstance(points, list):
        raise SafetyError("Lüfterkurve muss eine Liste sein.")
    if not 2 <= len(points) <= 12:
        raise SafetyError("Lüfterkurve braucht 2 bis 12 Punkte.")
    cleaned: list[dict] = []
    previous_temp: int | None = None
    previous_duty: int | None = None
    for item in points:
        if isinstance(item, dict):
            temp = item.get("temp_c")
            duty = item.get("duty_percent")
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            temp, duty = item
        else:
            raise SafetyError("Kurvenpunkt muss temp_c und duty_percent enthalten.")
        if type(temp) is not int or type(duty) is not int:
            raise SafetyError("Temperatur und Duty müssen ganze Zahlen sein.")
        if not 0 <= temp <= 110:
            raise SafetyError("Temperatur muss zwischen 0 und 110 °C liegen.")
        if not 0 <= duty <= 100:
            raise SafetyError("Duty muss zwischen 0 und 100 Prozent liegen.")
        if previous_temp is not None and temp <= previous_temp:
            raise SafetyError("Temperaturen müssen streng steigen.")
        if previous_duty is not None and duty < previous_duty:
            raise SafetyError("Duty darf mit steigender Temperatur nicht sinken.")
        previous_temp = temp
        previous_duty = duty
        cleaned.append({"temp_c": temp, "duty_percent": duty})
    return cleaned


def profile_names() -> list[str]:
    return list(PROFILES)


def export_profile(name: str) -> dict:
    key = name.lower().strip()
    if key not in PROFILES:
        raise SafetyError("Profil muss Silent, Balanced, Performance oder Turbo sein.")
    points = validate_curve([{"temp_c": temp, "duty_percent": duty} for temp, duty in PROFILES[key]])
    note_linux = (
        "Dieselbe Kurve. Schreiben nach /sys/class/hwmon/*/pwmN unterbleibt: "
        "ohne bestätigten Vendor-Treiber wäre der Duty eine Vermutung."
    )
    note_windows = (
        "Dieselbe Kurve. powercfg setzt keinen Lüfter-Duty. Herstellerwerkzeuge "
        "werden nicht ferngesteuert."
    )
    return {
        "name": key,
        "points": points,
        "linux": {"points": points, "note_de": note_linux, "applied": False},
        "windows": {"points": points, "note_de": note_windows, "applied": False},
        "applied": False,
        "dry_run": True,
    }


def export_custom(points: object) -> dict:
    cleaned = validate_curve(points)
    return {
        "name": "custom",
        "points": cleaned,
        "linux": {"points": cleaned, "applied": False},
        "windows": {"points": cleaned, "applied": False},
        "applied": False,
        "dry_run": True,
    }
