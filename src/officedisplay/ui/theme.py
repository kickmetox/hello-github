from __future__ import annotations

THEMES = {
    "hell": {
        "window": "#F4F6FB",
        "panel": "#FFFFFF",
        "ink": "#1B2433",
        "muted": "#5C6B80",
        "line": "#D5DDEA",
        "accent": "#0B63E5",
        "accent_ink": "#FFFFFF",
        "canvas": "#D9E0EC",
        "danger": "#B42318",
    },
    "dunkel": {
        "window": "#12151C",
        "panel": "#1C2230",
        "ink": "#E8EEF8",
        "muted": "#9AA8BD",
        "line": "#2C3548",
        "accent": "#3B82F6",
        "accent_ink": "#FFFFFF",
        "canvas": "#0C0E14",
        "danger": "#F97066",
    },
    "farbe": {
        "window": "#0A3E9A",
        "panel": "#F7F9FF",
        "ink": "#142033",
        "muted": "#3E5680",
        "line": "#D5E2FF",
        "accent": "#F28C28",
        "accent_ink": "#1B1F2A",
        "canvas": "#08357A",
        "danger": "#E23B3B",
    },
    "grau": {
        "window": "#E6E6E6",
        "panel": "#F5F5F5",
        "ink": "#222222",
        "muted": "#666666",
        "line": "#CCCCCC",
        "accent": "#444444",
        "accent_ink": "#FFFFFF",
        "canvas": "#CFCFCF",
        "danger": "#333333",
    },
}

THEMES["graustufen"] = THEMES["grau"]


def stylesheet(name: str) -> str:
    theme = THEMES.get(name, THEMES["farbe"])
    return f"""
    QMainWindow, QDialog {{ background: {theme['window']}; color: {theme['ink']}; }}
    QWidget {{ color: {theme['ink']}; font-family: "Segoe UI", "Noto Sans", sans-serif; font-size: 13px; }}
    QMenuBar, QMenu {{ background: {theme['panel']}; color: {theme['ink']}; }}
    QMenu::item:selected {{ background: {theme['accent']}; color: {theme['accent_ink']}; }}
    QToolBar {{ background: {theme['panel']}; border: 0; border-bottom: 1px solid {theme['line']}; spacing: 4px; padding: 4px; }}
    QDockWidget {{ color: {theme['ink']}; titlebar-close-icon: none; }}
    QDockWidget::title {{ background: {theme['panel']}; padding: 6px; border: 1px solid {theme['line']}; }}
    QListWidget, QPlainTextEdit, QLineEdit, QComboBox, QSpinBox, QTextBrowser {{
        background: {theme['panel']}; color: {theme['ink']}; border: 1px solid {theme['line']}; border-radius: 8px; padding: 4px;
    }}
    QPushButton {{
        background: {theme['panel']}; color: {theme['ink']}; border: 1px solid {theme['line']};
        border-radius: 8px; padding: 6px 10px;
    }}
    QPushButton:checked, QPushButton:hover {{ background: {theme['accent']}; color: {theme['accent_ink']}; }}
    QStatusBar {{ background: {theme['panel']}; color: {theme['muted']}; }}
    QLabel#muted {{ color: {theme['muted']}; }}
    """
