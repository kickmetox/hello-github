"""Hell/Dunkel/System-Theme + High-Contrast / UI-Schrift — 2.0.1 (Basis 2.0.0)."""

from __future__ import annotations

from typing import Callable, Literal

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QWidget

from instantlensdoc.core.app_settings import (
    effective_ui_font_pt,
    get_high_contrast,
    get_theme,
    get_ui_font_pt,
    get_ui_font_scale_percent,
    set_high_contrast,
    set_theme,
)

ThemeMode = Literal["light", "dark", "system"]
ResolvedTheme = Literal["light", "dark"]

# Zyklische Reihenfolge: System → Hell → Dunkel → System — 1.4.4
THEME_CYCLE_ORDER: tuple[ThemeMode, ...] = ("system", "light", "dark")

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

# High-Contrast Theme — 2.0.0 (WCAG-orientiert, schwarz/weiß + Gelb-Fokus)
HIGH_CONTRAST_STYLE = """
QMainWindow, QWidget { background: #000000; color: #FFFFFF; }
QPlainTextEdit, QTextEdit, QTextBrowser {
    background: #000000; color: #FFFFFF;
    selection-background-color: #FFFF00; selection-color: #000000;
    border: 1px solid #FFFFFF;
}
QMenuBar, QMenu { background: #000000; color: #FFFFFF; border: 1px solid #FFFFFF; }
QMenuBar::item:selected, QMenu::item:selected {
    background: #FFFF00; color: #000000;
}
QStatusBar { background: #000000; color: #FFFF00; border-top: 1px solid #FFFFFF; }
QToolButton { color: #FFFFFF; background: #000000; border: 1px solid #FFFFFF; }
QToolButton:checked { background: #FFFF00; color: #000000; border: 2px solid #FFFFFF; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QListWidget, QTreeWidget, QTableWidget {
    background: #000000; color: #FFFFFF; border: 1px solid #FFFFFF;
}
QPushButton {
    background: #000000; color: #FFFFFF; border: 2px solid #FFFFFF; padding: 4px 10px;
}
QPushButton:hover, QPushButton:focus { background: #FFFF00; color: #000000; }
QSplitter::handle { background: #FFFFFF; }
QLabel { color: #FFFFFF; }
QCheckBox, QRadioButton { color: #FFFFFF; }
QTabBar::tab { background: #000000; color: #FFFFFF; border: 1px solid #FFFFFF; padding: 4px 8px; }
QTabBar::tab:selected { background: #FFFF00; color: #000000; }
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
    Statusleisten-Indicator: System / Manuell dunkel / Manuell hell — 1.4.2/1.4.3.
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


def apply_ui_font(
    app: QApplication | None = None,
    *,
    pt: int | None = None,
    scale_percent: int | None = None,
    persist: bool = True,
) -> int:
    """
    UI-Schriftgröße setzen (effektiv = pt × Skala%).
    persist=True speichert übergebene pt/scale — 2.0.1.
    """
    try:
        from instantlensdoc.core.app_settings import (
            set_ui_font_pt,
            set_ui_font_scale_percent,
        )

        if pt is not None and persist:
            set_ui_font_pt(int(pt))
        if scale_percent is not None and persist:
            set_ui_font_scale_percent(int(scale_percent))
        size = int(
            effective_ui_font_pt(
                pt=pt if pt is not None else get_ui_font_pt(),
                scale_percent=(
                    scale_percent
                    if scale_percent is not None
                    else get_ui_font_scale_percent()
                ),
            )
        )
    except Exception:
        try:
            size = int(get_ui_font_pt())
        except Exception:
            size = 10
        size = max(9, min(28, size))
    target = app or QApplication.instance()
    if target is not None:
        font = QFont(target.font())
        font.setPointSize(size)
        target.setFont(font)
    return size


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
    hc = False
    try:
        hc = bool(get_high_contrast())
    except Exception:
        hc = False
    if hc:
        qss = HIGH_CONTRAST_STYLE
    else:
        qss = DARK_STYLE if resolved == "dark" else LIGHT_STYLE
    target = app or QApplication.instance()
    if target is not None:
        target.setStyleSheet(qss)
        try:
            apply_ui_font(target)
        except Exception:
            pass
    return resolved


def toggle_high_contrast(parent: QWidget | None = None) -> bool:
    """High-Contrast Theme ein/aus; liefert neuen Zustand — 2.0.0."""
    try:
        cur = bool(get_high_contrast())
    except Exception:
        cur = False
    new = not cur
    try:
        set_high_contrast(new)
    except Exception:
        pass
    apply_theme()
    return new


def toggle_theme(parent: QWidget | None = None) -> ResolvedTheme:
    """Manueller Override: light ↔ dark (verlässt System-Modus)."""
    current = resolve_theme()
    new_mode: ThemeMode = "dark" if current == "light" else "light"
    return apply_theme(mode=new_mode)


def next_theme_mode(mode: ThemeMode | None = None) -> ThemeMode:
    """Nächster Modus im Zyklus System → Hell → Dunkel → System — 1.4.4."""
    cur: ThemeMode = mode if mode in THEME_CYCLE_ORDER else load_theme_mode()
    if cur not in THEME_CYCLE_ORDER:
        cur = "system"
    idx = THEME_CYCLE_ORDER.index(cur)
    return THEME_CYCLE_ORDER[(idx + 1) % len(THEME_CYCLE_ORDER)]


def cycle_theme_mode(parent: QWidget | None = None) -> ThemeMode:
    """
    Theme zyklisch umschalten: System → Hell → Dunkel → System.
    Speichert und wendet an; liefert den neuen Preference-Modus — 1.4.4.
    """
    nxt = next_theme_mode()
    apply_theme(mode=nxt)
    return nxt


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
