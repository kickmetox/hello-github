"""Word/SoftMaker-Oberfläche: Klassisch / Ribbon / Kombiniert.

Default: Kombiniert (Pull-down-Menüs + Ribbon). Umschalten verwirft
kein offenes Dokument — nur Sichtbarkeit von Menüleiste und Ribbon.
"""

from __future__ import annotations

from typing import Literal

ChromeMode = Literal["klassisch", "ribbon", "kombiniert"]

CHROME_KLASSISCH: ChromeMode = "klassisch"
CHROME_RIBBON: ChromeMode = "ribbon"
CHROME_KOMBINIERT: ChromeMode = "kombiniert"

CHROME_MODES: tuple[ChromeMode, ...] = (
    CHROME_KLASSISCH,
    CHROME_RIBBON,
    CHROME_KOMBINIERT,
)

CHROME_LABELS: dict[str, str] = {
    CHROME_KLASSISCH: "Klassisch (Pull-down)",
    CHROME_RIBBON: "Ribbon",
    CHROME_KOMBINIERT: "Kombiniert",
}

DEFAULT_CHROME_MODE: ChromeMode = CHROME_KOMBINIERT


def normalize_chrome_mode(value: object) -> ChromeMode:
    raw = str(value or "").strip().lower()
    aliases = {
        "classic": CHROME_KLASSISCH,
        "klassisch": CHROME_KLASSISCH,
        "pulldown": CHROME_KLASSISCH,
        "pull-down": CHROME_KLASSISCH,
        "menu": CHROME_KLASSISCH,
        "menus": CHROME_KLASSISCH,
        "ribbon": CHROME_RIBBON,
        "office": CHROME_RIBBON,
        "kombiniert": CHROME_KOMBINIERT,
        "combined": CHROME_KOMBINIERT,
        "both": CHROME_KOMBINIERT,
    }
    return aliases.get(raw, DEFAULT_CHROME_MODE)  # type: ignore[return-value]


def get_chrome_mode() -> ChromeMode:
    from instantlensdoc.core.app_settings import load_settings

    return normalize_chrome_mode(load_settings().get("chrome_mode", DEFAULT_CHROME_MODE))


def set_chrome_mode(mode: str) -> ChromeMode:
    from instantlensdoc.core.app_settings import save_settings

    resolved = normalize_chrome_mode(mode)
    save_settings(
        {
            "chrome_mode": resolved,
            "ribbon_visible": resolved != CHROME_KLASSISCH,
        }
    )
    return resolved


def apply_chrome(window, mode: str | None = None) -> ChromeMode:
    """Menüleiste/Ribbon laut Modus — Dokument bleibt unangetastet."""
    resolved = normalize_chrome_mode(mode if mode is not None else get_chrome_mode())
    presentation = bool(getattr(window, "_presentation_active", False))
    menubar = window.menuBar() if hasattr(window, "menuBar") else None
    ribbon = getattr(window, "ribbon_bar", None)
    show_menu = (not presentation) and resolved in (CHROME_KLASSISCH, CHROME_KOMBINIERT)
    show_ribbon = (not presentation) and resolved in (CHROME_RIBBON, CHROME_KOMBINIERT)
    if menubar is not None:
        menubar.setVisible(bool(show_menu))
    if ribbon is not None:
        ribbon.setVisible(bool(show_ribbon))
    act = getattr(window, "_ribbon_action", None)
    if act is not None:
        try:
            act.blockSignals(True)
            act.setChecked(bool(show_ribbon))
            act.blockSignals(False)
        except Exception:
            pass
    group = getattr(window, "_chrome_mode_actions", None) or {}
    for key, action in group.items():
        try:
            action.blockSignals(True)
            action.setChecked(str(key) == resolved)
            action.blockSignals(False)
        except Exception:
            pass
    return resolved
