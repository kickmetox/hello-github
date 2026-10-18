"""Erscheinungsbild zwischen Windows, GNOME, KDE und XFCE."""

from __future__ import annotations

import re

from cpcm.paths import World

_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def theme_artifacts(theme: dict, world: World, desktop: str = "gnome") -> dict:
    mode = str(theme.get("mode") or "dark")
    if mode not in ("dark", "light", "schedule"):
        raise ValueError("Modus muss dark, light oder schedule sein")
    accent = str(theme.get("accent") or "#0078D4")
    if not _COLOR.match(accent):
        raise ValueError("Akzentfarbe muss #RRGGBB sein")
    dark_from = str(theme.get("dark_from") or "19:00")
    light_from = str(theme.get("light_from") or "07:00")
    wallpaper = str(theme.get("wallpaper") or "")
    cursor = str(theme.get("cursor_theme") or "default")
    cursor_size = int(theme.get("cursor_size") or 24)
    prefer = "prefer-light" if mode == "light" else "prefer-dark"
    gtk = "Adwaita" if mode == "light" else "Adwaita-dark"
    gnome = "\n".join([
        f"gsettings set org.gnome.desktop.interface color-scheme {prefer}",
        f"gsettings set org.gnome.desktop.interface gtk-theme {gtk}",
        f"gsettings set org.gnome.desktop.interface cursor-theme {cursor}",
        f"gsettings set org.gnome.desktop.interface cursor-size {cursor_size}",
        f"# Akzent {accent}",
    ])
    if wallpaper:
        gnome += f'\ngsettings set org.gnome.desktop.background picture-uri "file://{wallpaper}"\n'
    if mode == "schedule":
        gnome += f"# Zeitplan: hell ab {light_from}, dunkel ab {dark_from}.\n"
    kde = "\n".join([
        f"kwriteconfig5 --file kdeglobals --group General --key ColorScheme {'BreezeLight' if mode == 'light' else 'BreezeDark'}",
        f"kwriteconfig5 --file kcminputrc --group Mouse --key cursorTheme {cursor}",
        f"# Akzent {accent}",
    ])
    xfce = "\n".join([
        f"xfconf-query -c xsettings -p /Net/ThemeName -s {gtk}",
        f"xfconf-query -c xsettings -p /Gtk/CursorThemeName -s {cursor}",
        f"xfconf-query -c xsettings -p /Gtk/CursorThemeSize -s {cursor_size}",
    ])
    bit = 1 if mode == "light" else 0
    windows = "\n".join([
        "Windows Registry Editor Version 5.00",
        "",
        r"[HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize]",
        f'"AppsUseLightTheme"=dword:{bit:08x}',
        f'"SystemUsesLightTheme"=dword:{bit:08x}',
        f"; Akzent {accent}",
        f"; Cursor {cursor} {cursor_size}px",
        f"; Zeitplan hell {light_from} / dunkel {dark_from}" if mode == "schedule" else f"; Modus {mode}",
    ])
    linux = {"gnome": gnome, "kde": kde, "xfce": xfce}.get(desktop.lower(), gnome)
    return {
        "primary": windows if world == World.WINDOWS else linux,
        "windows": windows,
        "gnome": gnome,
        "kde": kde,
        "xfce": xfce,
        "stored": {
            "mode": mode, "accent": accent, "dark_from": dark_from, "light_from": light_from,
            "wallpaper": wallpaper, "cursor_theme": cursor, "cursor_size": cursor_size,
        },
    }
