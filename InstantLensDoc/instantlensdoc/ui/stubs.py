"""UI-Stubs für geplante Features."""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget

PLANNED = {
    "ki": "KI-Assistent — Stub 0.1.6 (Coming soon)",
    "cloud": "Cloud-Sync — Stub 0.1.6 (Coming soon)",
    "stylus": "Drucksensitiver Stylus / Palm Rejection — Stub 0.1.6",
    "shapes_ai": "Intelligente Formerkennung — Stub 0.1.6",
    "extrude3d": "3D-Extrusion — Stub 0.1.6",
    "varfonts": "Variable Fonts (voll) — geplant",
    "envelope": "Envelope Distort (voll) — geplant",
    "esign": "E-Signatur (rechtssicher) — geplant",
}


def show_planned(parent: QWidget | None, key: str) -> None:
    msg = PLANNED.get(key, "Dieses Feature ist geplant und noch nicht implementiert.")
    QMessageBox.information(parent, "Geplant", msg)
