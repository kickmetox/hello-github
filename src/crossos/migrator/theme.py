"""Designbrücke: Windows-Personalisierung, GNOME, KDE Plasma, XFCE.

Wallpaper-Pfade werden übersetzt, nicht kopiert. Zeitpläne werden als
Skripttext ausgegeben und nicht angelegt.
"""

from __future__ import annotations

from crossos.migrator.paths import translate_path
from crossos.safety import SafetyError, validate_accent, validate_theme_token

_GNOME_ACCENTS = {
    "blue": (53, 132, 228),
    "teal": (33, 144, 141),
    "green": (58, 148, 74),
    "yellow": (200, 146, 41),
    "orange": (237, 91, 0),
    "red": (230, 45, 66),
    "pink": (213, 97, 153),
    "purple": (145, 65, 172),
    "slate": (111, 120, 133),
}


def theme_bridge(profile: dict, *, user: str | None = None) -> dict:
    if not isinstance(profile, dict):
        raise SafetyError("Designprofil muss ein Objekt sein.")
    mode = str(profile.get("mode", "dark"))
    if mode not in {"dark", "light", "schedule"}:
        raise SafetyError("mode muss dark, light oder schedule sein.")
    accent = validate_accent(str(profile.get("accent", "#dff24a")))
    cursor = validate_theme_token(str(profile.get("cursor", "Adwaita")), field="cursor")
    wallpaper = str(profile.get("wallpaper", ""))
    dark_from = _hour(str(profile.get("dark_from", "19:00")))
    light_from = _hour(str(profile.get("light_from", "07:00")))
    wall_win, _ = translate_path(wallpaper, "windows", user) if wallpaper else ("", False)
    wall_linux, _ = translate_path(wallpaper, "linux", user) if wallpaper else ("", False)
    rgb = _hex_rgb(accent)
    gnome_accent = _nearest_gnome(rgb)
    colorization = _windows_colorization(rgb)
    light = 1 if mode == "light" else 0
    return {
        "mode": mode,
        "accent": accent,
        "cursor": cursor,
        "wallpaper_windows": wall_win,
        "wallpaper_linux": wall_linux,
        "windows_reg": _windows_reg(light, colorization, wall_win, cursor, mode),
        "gnome": _gnome(mode, gnome_accent, wall_linux, cursor),
        "kde": _kde(mode, rgb, wall_linux, cursor),
        "xfce": _xfce(mode, wall_linux, cursor),
        "schedule": _schedule(mode, dark_from, light_from),
        "gnome_accent_name": gnome_accent,
        "notes": [
            "GNOME 47 kennt Akzente nur als Namen. Die Hex-Farbe wird auf den nächsten Namen abgebildet.",
            "KDE- und XFCE-Schnipsel sind Datei- bzw. xfconf-Pläne und werden nicht geschrieben.",
            "Ein Zeitplan startet keinen Timer und keinen Task Scheduler-Job.",
        ],
        "executed": False,
        "dry_run": True,
    }


def _hour(value: str) -> str:
    parts = value.split(":")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise SafetyError("Uhrzeit muss HH:MM sein.")
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise SafetyError("Uhrzeit außerhalb des Bereichs.")
    return f"{hour:02d}:{minute:02d}"


def _hex_rgb(value: str) -> tuple[int, int, int]:
    return int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)


def _nearest_gnome(rgb: tuple[int, int, int]) -> str:
    def dist(other: tuple[int, int, int]) -> int:
        return sum((a - b) ** 2 for a, b in zip(rgb, other))

    return min(_GNOME_ACCENTS, key=lambda name: dist(_GNOME_ACCENTS[name]))


def _windows_colorization(rgb: tuple[int, int, int]) -> str:
    red, green, blue = rgb
    # AABBGGRR, Alpha 0xFF.
    dword = (0xFF << 24) | (blue << 16) | (green << 8) | red
    return f"{dword:08x}"


def _windows_reg(light: int, colorization: str, wallpaper: str, cursor: str, mode: str) -> str:
    wall = wallpaper.replace("\\", "\\\\")
    return (
        "Windows Registry Editor Version 5.00\n\n"
        "[HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize]\n"
        f'"AppsUseLightTheme"=dword:{light:08d}\n'
        f'"SystemUsesLightTheme"=dword:{light:08d}\n'
        f'"ColorizationColor"=dword:{colorization}\n'
        f"; mode={mode}\n\n"
        "[HKEY_CURRENT_USER\\Control Panel\\Desktop]\n"
        f'"Wallpaper"="{wall}"\n\n'
        "[HKEY_CURRENT_USER\\Control Panel\\Cursors]\n"
        f'""="{cursor}"\n'
    )


def _gnome(mode: str, accent: str, wallpaper: str, cursor: str) -> list[list[str]]:
    scheme = "prefer-light" if mode == "light" else "prefer-dark"
    theme = "Adwaita" if mode == "light" else "Adwaita-dark"
    commands = [
        ["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", scheme],
        ["gsettings", "set", "org.gnome.desktop.interface", "gtk-theme", theme],
        ["gsettings", "set", "org.gnome.desktop.interface", "accent-color", accent],
        ["gsettings", "set", "org.gnome.desktop.interface", "cursor-theme", cursor],
    ]
    if wallpaper:
        commands.append(["gsettings", "set", "org.gnome.desktop.background", "picture-uri", "file://" + wallpaper])
        commands.append(["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", "file://" + wallpaper])
    return commands


def _kde(mode: str, rgb: tuple[int, int, int], wallpaper: str, cursor: str) -> str:
    scheme = "BreezeLight" if mode == "light" else "BreezeDark"
    red, green, blue = rgb
    return (
        "# ~/.config/kdeglobals — Plan, nicht geschrieben\n"
        "[General]\n"
        f"ColorScheme={scheme}\n"
        f"AccentColor={red},{green},{blue}\n"
        "[Icons]\n"
        "Theme=breeze\n"
        "[KDE]\n"
        f"cursorTheme={cursor}\n"
        f"# wallpaper={wallpaper or '-'}\n"
    )


def _xfce(mode: str, wallpaper: str, cursor: str) -> list[list[str]]:
    theme = "Adwaita" if mode == "light" else "Adwaita-dark"
    commands = [
        ["xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName", "-s", theme],
        ["xfconf-query", "-c", "xfwm4", "-p", "/general/theme", "-s", "Default"],
        ["xfconf-query", "-c", "xsettings", "-p", "/Gtk/CursorThemeName", "-s", cursor],
    ]
    if wallpaper:
        commands.append(
            [
                "xfconf-query",
                "-c",
                "xfce4-desktop",
                "-p",
                "/backdrop/screen0/monitoreDP-1/workspace0/last-image",
                "-s",
                wallpaper,
            ]
        )
    return commands


def _schedule(mode: str, dark_from: str, light_from: str) -> dict:
    if mode != "schedule":
        return {"active": False, "dark_from": dark_from, "light_from": light_from, "bash": "", "powershell": ""}
    bash = (
        "#!/usr/bin/env bash\n"
        "# Plan: nicht als Timer installiert.\n"
        f"# dunkel ab {dark_from}, hell ab {light_from}\n"
        "hour=$(date +%H:%M)\n"
        f"if [[ $hour > {dark_from} || $hour < {light_from} ]]; then\n"
        "  gsettings set org.gnome.desktop.interface color-scheme prefer-dark\n"
        "else\n"
        "  gsettings set org.gnome.desktop.interface color-scheme prefer-light\n"
        "fi\n"
    )
    powershell = (
        "# Plan: kein geplanter Task wird registriert.\n"
        f"# dunkel ab {dark_from}, hell ab {light_from}\n"
        "$now = Get-Date -Format 'HH:mm'\n"
        f"if ($now -ge '{dark_from}' -or $now -lt '{light_from}') {{ $light = 0 }} else {{ $light = 1 }}\n"
        "Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize' -Name AppsUseLightTheme -Value $light\n"
    )
    return {
        "active": True,
        "dark_from": dark_from,
        "light_from": light_from,
        "bash": bash,
        "powershell": powershell,
        "installed": False,
    }
