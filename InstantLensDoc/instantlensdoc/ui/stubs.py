"""UI-Stubs für geplante Features (keine Fake-KI / keine Fake-Cloud)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from instantlensdoc import __version__
from instantlensdoc.core.i18n import get_lang, tr

PLANNED = {
    "ki": f"KI-Assistent — Stub {__version__} (Coming soon)",
    "cloud": f"Cloud-Sync — Stub {__version__} (Coming soon)",
    "stylus": f"Drucksensitiver Stylus / Palm Rejection — Stub {__version__}",
    "shapes_ai": f"Intelligente Formerkennung — Stub {__version__}",
    "extrude3d": f"3D-Extrusion — Stub {__version__}",
    "plugins": (
        f"Plugin-Hooks — Stub {__version__} — nicht produktiv "
        "(interner Event-Bus + no-op Loader; kein Plugin-System)"
    ),
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
    "plugins": (
        f"Plugin hooks — stub {__version__} — not production-ready "
        "(internal event bus + no-op loader; no plugin system)"
    ),
    "varfonts": "Variable fonts (full) — planned",
    "envelope": "Envelope distort (full) — planned",
    "esign": "E-signature (legally binding) — planned",
}

# Kurzbeschreibungen für Info-Dialog — 1.9.5
STUB_SHORT = {
    "ki": "Lokaler KI-Assistent für Zusammenfassen und Vorschläge — Stub / nicht produktiv.",
    "cloud": "Optionale Cloud-Synchronisation — Stub / Coming soon / keine Aktion.",
    "stylus": "Drucksensitiver Stylus mit Palm Rejection — Stub / keine Aktion.",
    "shapes_ai": "Intelligente Formerkennung beim Zeichnen — Stub / geplant.",
    "extrude3d": "3D-Extrusion von Formen — Stub / geplant / keine Aktion.",
    "plugins": (
        "Plugin-Hooks: interner Event-Bus + no-op Loader — Stub / nicht produktiv."
    ),
    "varfonts": "Vollständige Variable-Fonts-Unterstützung — geplant.",
    "envelope": "Envelope-Distort-Transformation — geplant.",
    "esign": "Rechtssichere E-Signatur — geplant.",
}

STUB_SHORT_EN = {
    "ki": "Local AI assistant for summaries and suggestions — stub / not production.",
    "cloud": "Optional cloud sync — stub / Coming soon / no action.",
    "stylus": "Pressure-sensitive stylus with palm rejection — stub / no action.",
    "shapes_ai": "Smart shape recognition while drawing — stub / planned.",
    "extrude3d": "3D extrusion of shapes — stub / planned / no action.",
    "plugins": (
        "Plugin hooks: internal event bus + no-op loader — stub / not production."
    ),
    "varfonts": "Full variable fonts support — planned.",
    "envelope": "Envelope distort transform — planned.",
    "esign": "Legally binding e-signature — planned.",
}

STUB_TITLES = {
    "ki": "KI-Assistent",
    "cloud": "Cloud-Sync",
    "stylus": "Stylus / Palm Rejection",
    "shapes_ai": "Intelligente Formerkennung",
    "extrude3d": "3D-Extrusion",
    "plugins": "Plugin-Hooks",
    "varfonts": "Variable Fonts",
    "envelope": "Envelope Distort",
    "esign": "E-Signatur",
}

STUB_TITLES_EN = {
    "ki": "AI assistant",
    "cloud": "Cloud sync",
    "stylus": "Stylus / palm rejection",
    "shapes_ai": "Smart shape recognition",
    "extrude3d": "3D extrusion",
    "plugins": "Plugin hooks",
    "varfonts": "Variable fonts",
    "envelope": "Envelope distort",
    "esign": "E-signature",
}


class StubInfoDialog(QDialog):
    """Info-Dialog für Stubs: Kurzbeschreibung + Badge „Geplant“; Esc schließt — 1.9.5."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        title: str,
        short: str,
        detail: str,
        badge: str = "Geplant",
    ):
        super().__init__(parent)
        self.setObjectName("stubInfoDialog")
        self.setWindowTitle(title or tr("planned"))
        self.setModal(True)
        self.resize(420, 220)
        layout = QVBoxLayout(self)

        head = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setObjectName("stubInfoTitle")
        title_lbl.setStyleSheet("font-weight:600;font-size:14px;")
        title_lbl.setWordWrap(True)
        head.addWidget(title_lbl, 1)
        self.badge = QLabel(badge)
        self.badge.setObjectName("stubInfoBadge")
        self.badge.setAlignment(Qt.AlignCenter)
        self.badge.setStyleSheet(
            "QLabel#stubInfoBadge {"
            " background:#fff3e0; color:#8a5a00; border:1px solid #e0a060;"
            " border-radius:4px; padding:2px 8px; font-weight:700;"
            "}"
        )
        self.badge.setToolTip("Stub / geplant — keine Aktion — 1.9.5")
        head.addWidget(self.badge, 0)
        layout.addLayout(head)

        short_lbl = QLabel(short)
        short_lbl.setObjectName("stubInfoShort")
        short_lbl.setWordWrap(True)
        short_lbl.setStyleSheet("color:#333;margin-top:6px;")
        layout.addWidget(short_lbl)

        detail_lbl = QLabel(detail)
        detail_lbl.setObjectName("stubInfoDetail")
        detail_lbl.setWordWrap(True)
        detail_lbl.setStyleSheet("color:#666;margin-top:4px;")
        layout.addWidget(detail_lbl)

        note = QLabel("Stub / nicht produktiv — keine Aktion.")
        note.setObjectName("stubInfoNote")
        note.setStyleSheet("color:#8a5a00;font-weight:600;margin-top:8px;")
        note.setWordWrap(True)
        layout.addWidget(note)

        layout.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        close_btn = buttons.button(QDialogButtonBox.Close)
        if close_btn is not None:
            close_btn.setText("Schließen")
            close_btn.setToolTip("Esc schließt ebenfalls — 1.9.5")
        layout.addWidget(buttons)

        # Esc schließt (zusätzlich zu QDialog-Standard) — 1.9.5
        esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        esc.setContext(Qt.WindowShortcut)
        esc.activated.connect(self.reject)


def show_planned(parent: QWidget | None, key: str) -> None:
    """Stub-Info mit Kurzbeschreibung + Badge „Geplant“; Esc schließt — 1.9.5."""
    en = get_lang() == "en"
    titles = STUB_TITLES_EN if en else STUB_TITLES
    shorts = STUB_SHORT_EN if en else STUB_SHORT
    details = PLANNED_EN if en else PLANNED
    title = titles.get(key) or key
    short = shorts.get(key) or (
        "Dieses Feature ist geplant und noch nicht implementiert."
        if not en
        else "This feature is planned and not yet implemented."
    )
    detail = details.get(key) or PLANNED.get(
        key, "Dieses Feature ist geplant und noch nicht implementiert."
    )
    badge = tr("planned")
    dlg = StubInfoDialog(
        parent, title=title, short=short, detail=detail, badge=badge
    )
    dlg.exec()
