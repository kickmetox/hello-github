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


def _channel(value: int) -> float:
    amount = value / 255
    if amount <= 0.04045:
        return amount / 12.92
    return ((amount + 0.055) / 1.055) ** 2.4


def contrast(hex_a: str, hex_b: str) -> float:
    """Kontrast zweier #RRGGBB-Farben. Unter 4.5 ist Fließtext schlecht lesbar."""

    def lum(color: str) -> float:
        color = color.lstrip("#")
        red, green, blue = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
        return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)

    lighter, darker = lum(hex_a), lum(hex_b)
    if lighter < darker:
        lighter, darker = darker, lighter
    return (lighter + 0.05) / (darker + 0.05)


def stylesheet(name: str) -> str:
    theme = THEMES.get(name, THEMES["farbe"])
    # Farbe nutzt ein dunkles Fenster und dunkle Schrift. Dialoge liegen dann
    # auf dem hellen Paneel, sonst verschwindet der Text.
    dialog_bg = theme["window"]
    if contrast(theme["window"], theme["ink"]) < 4.5:
        dialog_bg = theme["panel"]
    dialog_buttons = ""
    if dialog_bg == theme["panel"]:
        dialog_buttons = f"QDialog QPushButton {{ border: 1px solid {theme['accent']}; }}"
    return f"""
    QMainWindow {{ background: {theme['window']}; color: {theme['ink']}; }}
    QDialog {{ background: {dialog_bg}; color: {theme['ink']}; }}
    QWidget {{ color: {theme['ink']}; font-family: "Segoe UI", "Noto Sans", sans-serif; font-size: 13px; }}
    QMenuBar, QMenu {{ background: {theme['panel']}; color: {theme['ink']}; }}
    QMenu::item:selected {{ background: {theme['accent']}; color: {theme['accent_ink']}; }}
    QToolBar {{ background: {theme['panel']}; border: 0; border-bottom: 1px solid {theme['line']}; spacing: 4px; padding: 4px; min-height: 40px; }}
    QToolBar QToolButton {{ min-height: 24px; padding: 4px 8px; background: {theme['panel']}; color: {theme['ink']}; border: 1px solid {theme['line']}; border-radius: 6px; }}
    QToolBar QToolButton:checked {{ background: {theme['accent']}; color: {theme['accent_ink']}; }}
    QDockWidget {{ color: {theme['ink']}; titlebar-close-icon: none; }}
    QDockWidget::title {{ background: {theme['panel']}; padding: 6px; border: 1px solid {theme['line']}; }}
    QListWidget, QPlainTextEdit, QTextBrowser {{
        background: {theme['panel']}; color: {theme['ink']}; border: 1px solid {theme['line']}; border-radius: 8px; padding: 4px;
    }}
    QLineEdit, QComboBox {{
        background: {theme['panel']}; color: {theme['ink']}; border: 1px solid {theme['line']};
        border-radius: 6px; padding: 2px 8px; min-height: 26px;
    }}
    QComboBox QLineEdit {{ padding: 0 4px; min-height: 22px; background: transparent; }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus {{ border: 2px solid {theme['accent']}; }}
    QSpinBox {{
        background: {theme['panel']}; color: {theme['ink']}; border: 1px solid {theme['line']};
        border-radius: 6px; padding: 2px 4px 2px 8px; min-height: 26px; min-width: 72px;
    }}
    QPushButton {{
        background: {theme['panel']}; color: {theme['ink']}; border: 1px solid {theme['line']};
        border-radius: 8px; padding: 6px 10px;
    }}
    QPushButton:checked, QPushButton:hover {{ background: {theme['accent']}; color: {theme['accent_ink']}; }}
    {dialog_buttons}
    QStatusBar {{ background: {theme['panel']}; color: {theme['muted']}; }}
    QLabel#muted {{ color: {theme['muted']}; }}
    """
