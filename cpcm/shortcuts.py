"""Tastaturkürzel und Touchpad-Gesten zwischen Windows und Linux."""

from __future__ import annotations

import re

from cpcm.paths import World

_ALIASES = {
    "ctrl": "ctrl", "control": "ctrl", "strg": "ctrl", "steuerung": "ctrl",
    "alt": "alt", "option": "alt", "opt": "alt", "mod1": "alt",
    "shift": "shift", "umschalt": "shift",
    "super": "super", "meta": "super", "win": "super", "windows": "super",
    "cmd": "super", "command": "super", "mod4": "super",
}
_ORDER = ("ctrl", "alt", "shift", "super")
_EMIT = {
    World.WINDOWS: {"ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "super": "Win"},
    World.LINUX: {"ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "super": "Super"},
}
_VSCODE = {"ctrl": "ctrl", "alt": "alt", "shift": "shift", "super": "meta"}
GESTURE_DEFAULTS = {
    "natural_scroll": True,
    "tap_to_click": True,
    "speed": 0.6,
    "three_finger_swipe": "workspace-switch",
    "four_finger_swipe": "overview",
}


def parse_shortcut(text: str) -> tuple[list[str], str]:
    parts = re.split(r"\s*\+\s*", text.strip())
    mods: list[str] = []
    key = ""
    for part in parts:
        token = part.strip()
        canonical = _ALIASES.get(token.casefold())
        if canonical:
            if canonical not in mods:
                mods.append(canonical)
        else:
            if key:
                raise ValueError(f"Mehr als eine Taste: {text}")
            key = token
    if not key:
        raise ValueError(f"Keine Taste in: {text}")
    mods.sort(key=lambda item: _ORDER.index(item))
    return mods, key


def translate_shortcut(text: str, world: World, *, vscode: bool = False) -> str:
    mods, key = parse_shortcut(text)
    table = _VSCODE if vscode else _EMIT[world]
    rendered = [table[mod] for mod in mods]
    rendered.append(key.lower() if vscode else (key.upper() if len(key) == 1 else key))
    return "+".join(rendered)


def gesture_artifacts(settings: dict, world: World) -> dict:
    natural = bool(settings.get("natural_scroll", True))
    tap = bool(settings.get("tap_to_click", True))
    speed = float(settings.get("speed", 0.6))
    three = str(settings.get("three_finger_swipe") or "workspace-switch")
    four = str(settings.get("four_finger_swipe") or "overview")
    linux = "\n".join([
        "gsettings set org.gnome.desktop.peripherals.touchpad natural-scroll " + ("true" if natural else "false"),
        "gsettings set org.gnome.desktop.peripherals.touchpad tap-to-click " + ("true" if tap else "false"),
        f"gsettings set org.gnome.desktop.peripherals.touchpad speed {speed}",
        f"# 3-Finger: {three}",
        f"# 4-Finger: {four}",
    ])
    windows = "\n".join([
        "Windows Registry Editor Version 5.00",
        "",
        r"[HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\PrecisionTouchPad]",
        f'"ScrollDirection"=dword:{1 if natural else 0:08x}',
        f'"TapsEnabled"=dword:{1 if tap else 0:08x}',
        f"; 3-Finger={three} 4-Finger={four}",
    ])
    return {"primary": windows if world == World.WINDOWS else linux, "linux": linux, "windows": windows}
