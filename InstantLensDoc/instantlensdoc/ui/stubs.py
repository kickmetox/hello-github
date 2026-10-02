"""UI-Stubs für geplante Features (keine Fake-KI / keine Fake-Cloud)."""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget

from instantlensdoc.core.i18n import get_lang, tr

PLANNED = {
    "ki": "KI-Assistent — Stub 0.2.5 (Coming soon)",
    "cloud": "Cloud-Sync — Stub 0.2.5 (Coming soon)",
    "stylus": "Drucksensitiver Stylus / Palm Rejection — Stub 0.2.5",
    "shapes_ai": "Intelligente Formerkennung — Stub 0.2.5",
    "extrude3d": "3D-Extrusion — Stub 0.2.5",
    "varfonts": "Variable Fonts (voll) — geplant",
    "envelope": "Envelope Distort (voll) — geplant",
    "esign": "E-Signatur (rechtssicher) — geplant",
}

PLANNED_EN = {
    "ki": "AI assistant — stub 0.2.5 (Coming soon)",
    "cloud": "Cloud sync — stub 0.2.5 (Coming soon)",
    "stylus": "Pressure-sensitive stylus / palm rejection — stub 0.2.5",
    "shapes_ai": "Smart shape recognition — stub 0.2.5",
    "extrude3d": "3D extrusion — stub 0.2.5",
    "varfonts": "Variable fonts (full) — planned",
    "envelope": "Envelope distort (full) — planned",
    "esign": "E-signature (legally binding) — planned",
}


def show_planned(parent: QWidget | None, key: str) -> None:
    table = PLANNED_EN if get_lang() == "en" else PLANNED
    msg = table.get(key) or PLANNED.get(key, "Dieses Feature ist geplant und noch nicht implementiert.")
    QMessageBox.information(parent, tr("planned"), msg)
