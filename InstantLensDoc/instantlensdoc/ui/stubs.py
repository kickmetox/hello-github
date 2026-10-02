"""UI-Stubs für geplante Features (keine Fake-KI / keine Fake-Cloud)."""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget

from instantlensdoc import __version__
from instantlensdoc.core.i18n import get_lang, tr

PLANNED = {
    "ki": f"KI-Assistent — Stub {__version__} (Coming soon)",
    "cloud": f"Cloud-Sync — Stub {__version__} (Coming soon)",
    "stylus": f"Drucksensitiver Stylus / Palm Rejection — Stub {__version__}",
    "shapes_ai": f"Intelligente Formerkennung — Stub {__version__}",
    "extrude3d": f"3D-Extrusion — Stub {__version__}",
    "varfonts": "Variable Fonts (voll) — geplant",
    "envelope": "Envelope Distort (voll) — geplant",
    "esign": "E-Signatur (rechtssicher) — geplant",
}

PLANNED_EN = {
    "ki": f"AI assistant — stub {__version__} (Coming soon)",
    "cloud": f"Cloud sync — stub {__version__} (Coming soon)",
    "stylus": f"Pressure-sensitive stylus / palm rejection — stub {__version__}",
    "shapes_ai": f"Smart shape recognition — stub {__version__}",
    "extrude3d": f"3D extrusion — stub {__version__}",
    "varfonts": "Variable fonts (full) — planned",
    "envelope": "Envelope distort (full) — planned",
    "esign": "E-signature (legally binding) — planned",
}


def show_planned(parent: QWidget | None, key: str) -> None:
    table = PLANNED_EN if get_lang() == "en" else PLANNED
    msg = table.get(key) or PLANNED.get(key, "Dieses Feature ist geplant und noch nicht implementiert.")
    QMessageBox.information(parent, tr("planned"), msg)
