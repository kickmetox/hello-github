"""Maus- und Touchpad-Gesten als gsettings-, libinput- und Registry-Plan.

Nichts davon wird ausgeführt. Die Windows-DWORD-Werte für Precision Touchpad
sind die von CrossOS verwendete Konvention und können je nach OEM abweichen.
"""

from __future__ import annotations

from crossos.safety import SafetyError, parse_bool_token

_THREE = {
    "workspace": "Arbeitsflächen wechseln",
    "back": "Vor und zurück",
    "overview": "Aktivitätenübersicht",
    "none": "aus",
}
_FOUR = {
    "overview": "Aktivitätenübersicht",
    "workspace": "Arbeitsflächen wechseln",
    "none": "aus",
}


def gesture_bridge(profile: dict) -> dict:
    if not isinstance(profile, dict):
        raise SafetyError("Gestenprofil muss ein Objekt sein.")
    natural = parse_bool_token(profile.get("natural_scroll", True))
    tap = parse_bool_token(profile.get("tap_to_click", True))
    three = str(profile.get("three_finger", "workspace"))
    four = str(profile.get("four_finger", "overview"))
    if three not in _THREE or four not in _FOUR:
        raise SafetyError("three_finger oder four_finger ist kein bekannter Wert.")

    gnome = [
        ["gsettings", "set", "org.gnome.desktop.peripherals.touchpad", "natural-scroll", "true" if natural else "false"],
        ["gsettings", "set", "org.gnome.desktop.peripherals.touchpad", "tap-to-click", "true" if tap else "false"],
        ["gsettings", "set", "org.gnome.desktop.peripherals.touchpad", "click-method", "fingers"],
    ]
    if three == "workspace":
        gnome.append(
            ["gsettings", "set", "org.gnome.desktop.wm.preferences", "focus-mode", "click"]
        )
    libinput = _libinput(natural, tap)
    registry = _registry(natural, tap, three, four)
    return {
        "profile": {
            "natural_scroll": natural,
            "tap_to_click": tap,
            "three_finger": three,
            "three_finger_de": _THREE[three],
            "four_finger": four,
            "four_finger_de": _FOUR[four],
        },
        "gnome_argv": gnome,
        "libinput_quirks": libinput,
        "windows_reg": registry,
        "notes": [
            "3- und 4-Finger-Wischgesten hängt GNOME an die Shell, nicht an einen einzelnen libinput-Schalter.",
            "ScrollDirection=1 bedeutet in dieser Suite natürliche Richtung. OEM-Treiber können das invertieren.",
            "Keine dieser Zeilen wird von CrossOS ausgeführt.",
        ],
        "executed": False,
        "dry_run": True,
    }


def _libinput(natural: bool, tap: bool) -> str:
    scroll = "natural" if natural else "traditional"
    tap_line = "true" if tap else "false"
    return (
        "# /etc/libinput/local-overrides.quirks — Plan, nicht geschrieben\n"
        "[CrossOS Touchpad]\n"
        "MatchUdevType=touchpad\n"
        "MatchName=*\n"
        f"# natural_scroll={scroll}\n"
        f"# tap_to_click={tap_line}\n"
        "AttrScrollMethod=twofinger\n"
    )


def _registry(natural: bool, tap: bool, three: str, four: str) -> str:
    scroll = "00000001" if natural else "00000000"
    tap_dword = "00000001" if tap else "00000000"
    three_dword = "00000000" if three == "none" else "00000001"
    four_dword = "00000000" if four == "none" else "00000001"
    return (
        "Windows Registry Editor Version 5.00\n\n"
        "[HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\PrecisionTouchPad]\n"
        f'"ScrollDirection"=dword:{scroll}\n'
        f'"TwoFingerTapEnabled"=dword:{tap_dword}\n'
        f'"ThreeFingerSlideEnabled"=dword:{three_dword}\n'
        f'"FourFingerSlideEnabled"=dword:{four_dword}\n'
        "; CrossOS-Plan. ThreeFingerSlideEnabled ist je nach Windows-Build nicht vorhanden.\n"
        f"; three_finger={three} four_finger={four}\n"
    )
