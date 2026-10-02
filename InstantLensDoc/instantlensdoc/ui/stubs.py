"""UI-Stubs für geplante Features."""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget

PLANNED = {
    "ki": "KI-Assistent — geplant (Coming soon)",
    "cloud": "Cloud-Sync — geplant (Coming soon)",
    "stylus": "Drucksensitiver Stylus / Palm Rejection — geplant",
    "shapes_ai": "Intelligente Formerkennung — geplant",
    "extrude3d": "3D-Extrusion — geplant",
    "varfonts": "Variable Fonts (voll) — geplant",
    "envelope": "Envelope Distort (voll) — geplant",
    "esign": "E-Signatur (rechtssicher) — geplant",
}


def show_planned(parent: QWidget | None, key: str) -> None:
    msg = PLANNED.get(key, "Dieses Feature ist geplant und noch nicht implementiert.")
    QMessageBox.information(parent, "Geplant", msg)
