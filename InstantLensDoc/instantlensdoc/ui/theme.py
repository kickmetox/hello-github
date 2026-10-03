"""Hell/Dunkel/System-Theme für die Qt-Oberfläche — 1.4.2 Status-Indicator."""

from __future__ import annotations

from typing import Callable, Literal

from PySide6.QtWidgets import QApplication, QWidget

from instantlensdoc.core.app_settings import get_theme, set_theme

ThemeMode = Literal["light", "dark", "system"]
ResolvedTheme = Literal["light", "dark"]

LIGHT_STYLE = """
QMainWindow, QWidget { background: #f5f5f5; color: #1a1a1a; }
QPlainTextEdit, QTextEdit, QTextBrowser {
    background: #ffffff; color: #1a1a1a;
    selection-background-color: #3399ff;
}
QMenuBar, QMenu { background: #ececec; color: #1a1a1a; }
QStatusBar { background: #ececec; color: #333; }
QToolButton:checked { background: #d0e8ff; border: 1px solid #2980b9; }
QSplitter::handle { background: #ccc; }
"""

DARK_STYLE = """
QMainWindow, QWidget { background: #2b2b2b; color: #e8e8e8; }
QPlainTextEdit, QTextEdit, QTextBrowser {
    background: #1e1e1e; color: #e8e8e8;
    selection-background-color: #264f78;
}
QMenuBar, QMenu { background: #333; color: #e8e8e8; }
QStatusBar { background: #333; color: #ccc; }
QToolButton { color: #e8e8e8; }
QToolButton:checked { background: #3d5a80; border: 1px solid #5dade2; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #1e1e1e; color: #e8e8e8; border: 1px solid #555;
}
QSplitter::handle { background: #444; }
QLabel { color: #e8e8e8; }
"""

# Callback nach Live-Apply (z. B. Menü sync) — 1.4.1
_on_system_theme_changed: Callable[[ResolvedTheme], None] | None = None
_system_watch_installed = False


def detect_system_theme() -> ResolvedTheme:
    """OS-Farbschema (Qt ColorScheme) → light|dark."""
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QGuiApplication

        app = QGuiApplication.instance()
        hints = app.styleHints() if app is not None else None
        if hints is not None and hasattr(hints, "colorScheme"):
            scheme = hints.colorScheme()
            dark = getattr(Qt, "ColorScheme", None)
            if dark is not None and scheme == dark.Dark:
                return "dark"
            if dark is not None and scheme == dark.Light:
                return "light"
    except Exception:
        pass
    # Fallback: dunkle Palette wenn App dunklen Window-Text hat
    try:
        app = QApplication.instance()
        if app is not None:
            pal = app.palette()
            window = pal.color(pal.ColorRole.Window)
            if window.lightness() < 128:
                return "dark"
    except Exception:
        pass
    return "light"


def load_theme_mode() -> ThemeMode:
    mode = get_theme()
    if mode in ("dark", "light", "system"):
        return mode  # type: ignore[return-value]
    return "light"


def save_theme_mode(mode: ThemeMode) -> None:
    set_theme(mode)


def theme_status_text(mode: ThemeMode | None = None) -> str:
    """
    Statusleisten-Indicator: System / Manuell dunkel / Manuell hell — 1.4.2.
    """
    pref = mode if mode is not None else load_theme_mode()
    if pref == "system":
        return "Theme: System"
    if pref == "dark":
        return "Theme: Manuell dunkel"
    return "Theme: Manuell hell"


def resolve_theme(mode: ThemeMode | None = None) -> ResolvedTheme:
    """Gespeicherter Modus → tatsächlich anzuwendendes light|dark."""
    m = mode if mode is not None else load_theme_mode()
    if m == "system":
        return detect_system_theme()
    return "dark" if m == "dark" else "light"


def apply_theme(
    app: QApplication | None = None, *, mode: ThemeMode | None = None
) -> ResolvedTheme:
    """Stylesheet setzen; speichert mode wenn übergeben; liefert resolved light|dark."""
    if mode is not None:
        save_theme_mode(mode)
        pref = mode
    else:
        pref = load_theme_mode()
    resolved = resolve_theme(pref)
    qss = DARK_STYLE if resolved == "dark" else LIGHT_STYLE
    target = app or QApplication.instance()
    if target is not None:
        target.setStyleSheet(qss)
    return resolved


def toggle_theme(parent: QWidget | None = None) -> ResolvedTheme:
    """Manueller Override: light ↔ dark (verlässt System-Modus)."""
    current = resolve_theme()
    new_mode: ThemeMode = "dark" if current == "light" else "light"
    return apply_theme(mode=new_mode)


def set_follow_system(follow: bool) -> ResolvedTheme:
    """Toggle: System-Theme folgen; sonst manueller Override auf aktuelles Resolved."""
    if follow:
        return apply_theme(mode="system")
    return apply_theme(mode=resolve_theme())


def _on_color_scheme_changed(*_args) -> None:
    """OS-Theme gewechselt → bei „folgen“ live nachziehen — 1.4.1."""
    if load_theme_mode() != "system":
        return
    resolved = apply_theme()  # ohne mode: nicht speichern, nur neu resolven
    cb = _on_system_theme_changed
    if cb is not None:
        try:
            cb(resolved)
        except Exception:
            pass


def install_system_theme_watch(
    on_changed: Callable[[ResolvedTheme], None] | None = None,
) -> bool:
    """
    QStyleHints.colorSchemeChanged → Theme live nachziehen wenn System folgen.
    Idempotent. Liefert True wenn Signal verbunden — 1.4.1.
    """
    global _system_watch_installed, _on_system_theme_changed
    if on_changed is not None:
        _on_system_theme_changed = on_changed
    if _system_watch_installed:
        return True
    try:
        from PySide6.QtGui import QGuiApplication

        app = QGuiApplication.instance()
        if app is None:
            return False
        hints = app.styleHints()
        if hints is None or not hasattr(hints, "colorSchemeChanged"):
            return False
        hints.colorSchemeChanged.connect(_on_color_scheme_changed)
        _system_watch_installed = True
        return True
    except Exception:
        return False
