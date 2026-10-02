"""Hell/Dunkel-Theme für die Qt-Oberfläche."""

from __future__ import annotations

from typing import Literal

from PySide6.QtWidgets import QApplication, QWidget

from instantlensdoc.core.app_settings import get_theme, set_theme

ThemeMode = Literal["light", "dark"]

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


def load_theme_mode() -> ThemeMode:
    return get_theme()


def save_theme_mode(mode: ThemeMode) -> None:
    set_theme(mode)


def apply_theme(app: QApplication | None = None, *, mode: ThemeMode | None = None) -> ThemeMode:
    """Stylesheet setzen; liefert aktiven Modus."""
    if mode is None:
        mode = load_theme_mode()
    else:
        save_theme_mode(mode)
    qss = DARK_STYLE if mode == "dark" else LIGHT_STYLE
    target = app or QApplication.instance()
    if target is not None:
        target.setStyleSheet(qss)
    return mode


def toggle_theme(parent: QWidget | None = None) -> ThemeMode:
    current = load_theme_mode()
    new_mode: ThemeMode = "dark" if current == "light" else "light"
    apply_theme(mode=new_mode)
    return new_mode
