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
    "cloud": (
        f"Gemeinsames Review / Cloud-Ordner — {__version__} produktiv: "
        "Freigabeordner-Sync + optionaler HTTP-Endpoint; Notizen/Markierungen/"
        "Stempel/Kommentare austauschbar (kein gehosteter Cloud-Dienst)"
    ),
    "stylus": f"Drucksensitiver Stylus / Palm Rejection — Stub {__version__}",
    "shapes_ai": f"Intelligente Formerkennung — Stub {__version__}",
    "extrude3d": f"3D-Extrusion — Stub {__version__}",
    "plugins": (
        f"Plugin-Hooks — Stub {__version__} — nicht produktiv "
        "(interner Event-Bus + no-op Loader; kein Plugin-System)"
    ),
    "outline_read": (
        f"Document Outline Vorlesen — Stub {__version__} "
        "(TTS/Screenreader-Anbindung geplant; keine Aktion)"
    ),
    "telemetry": (
        f"Telemetrie — Stub {__version__} — Toggle disabled (bleibt aus), "
        "immer no-op — keine Datenübertragung — Esc schließt Info · "
        "„Stubs öffnen“ Fokus erste Zeile — 2.3.5"
    ),
    "varfonts": "Variable Fonts (voll) — geplant",
    "envelope": "Envelope Distort (voll) — geplant",
    "esign": (
        f"E-Signatur QES/QTSP-Trust — Hinweis {__version__}: "
        "AES/SES-Pfad produktiv (PKCS#12); volle QES-Validierung bleibt QTSP"
    ),
}

PLANNED_EN = {
    "ki": f"AI assistant — stub {__version__} (Coming soon)",
    "cloud": (
        f"Shared review / cloud folder — {__version__} live: "
        "shared-folder sync + optional HTTP endpoint; notes/highlights/"
        "stamps/comments exchangeable (no hosted cloud service)"
    ),
    "stylus": f"Pressure-sensitive stylus / palm rejection — stub {__version__}",
    "shapes_ai": f"Smart shape recognition — stub {__version__}",
    "extrude3d": f"3D extrusion — stub {__version__}",
    "plugins": (
        f"Plugin hooks — stub {__version__} — not production-ready "
        "(internal event bus + no-op loader; no plugin system)"
    ),
    "outline_read": (
        f"Document outline read-aloud — stub {__version__} "
        "(TTS/screen reader planned; no action)"
    ),
    "telemetry": (
        f"Telemetry — stub {__version__} — toggle disabled (stays off), "
        "always no-op — no data transfer — Esc closes info · "
        "Open Stubs focus first row — 2.3.5"
    ),
    "varfonts": "Variable fonts (full) — planned",
    "envelope": "Envelope distort (full) — planned",
    "esign": (
        f"E-signature QES/QTSP trust — note {__version__}: "
        "AES/SES path live (PKCS#12); full QES validation stays with QTSP"
    ),
}

# Kurzbeschreibungen für Info-Dialog — 1.9.5
STUB_SHORT = {
    "ki": "Lokaler KI-Assistent für Zusammenfassen und Vorschläge — Stub / nicht produktiv.",
    "cloud": (
        "Gemeinsames Review: Freigabeordner + optionaler Endpoint — produktiv 2.6.23; "
        "kein gehosteter Cloud-Dienst; Offline bleibt nutzbar."
    ),
    "stylus": "Drucksensitiver Stylus mit Palm Rejection — Stub / keine Aktion.",
    "shapes_ai": "Intelligente Formerkennung beim Zeichnen — Stub / geplant.",
    "extrude3d": "3D-Extrusion von Formen — Stub / geplant / keine Aktion.",
    "plugins": (
        "Plugin-Hooks: interner Event-Bus + no-op Loader — Stub / nicht produktiv."
    ),
    "outline_read": (
        "Document Outline Vorlesen (TTS) — Stub / geplant / keine Aktion — 2.0.0."
    ),
    "telemetry": (
        "Anonyme Nutzung melden — Stub / Toggle disabled bleibt aus / immer no-op — "
        "keine Datenübertragung. Warum Stub: kein Backend, Privacy lokal. "
        "Info: Esc schließt · „Stubs öffnen“ Fokus erste Stub-Zeile — 2.3.5."
    ),
    "varfonts": "Vollständige Variable-Fonts-Unterstützung — geplant.",
    "envelope": "Envelope-Distort-Transformation — geplant.",
    "esign": (
        "AES/SES-Pfad produktiv (PKCS#12, Sidecar); volle QES-/QTSP-Trust-Validierung "
        "extern — Extras/PDF → Digitale Signatur."
    ),
}

STUB_SHORT_EN = {
    "ki": "Local AI assistant for summaries and suggestions — stub / not production.",
    "cloud": (
        "Shared review: folder sync + optional endpoint — live in 2.6.23; "
        "no hosted cloud service; offline remains usable."
    ),
    "stylus": "Pressure-sensitive stylus with palm rejection — stub / no action.",
    "shapes_ai": "Smart shape recognition while drawing — stub / planned.",
    "extrude3d": "3D extrusion of shapes — stub / planned / no action.",
    "plugins": (
        "Plugin hooks: internal event bus + no-op loader — stub / not production."
    ),
    "outline_read": (
        "Document outline read-aloud (TTS) — stub / planned / no action — 2.0.0."
    ),
    "telemetry": (
        "Report anonymous usage — stub / toggle disabled stays off / always no-op — "
        "no data transfer. Why stub: no backend, local privacy. "
        "Info: Esc closes · Open Stubs · focus first row — 2.3.5."
    ),
    "varfonts": "Full variable fonts support — planned.",
    "envelope": "Envelope distort transform — planned.",
    "esign": (
        "AES/SES path live (PKCS#12, sidecar); full QES/QTSP trust validation "
        "external — Extras/PDF → Digital signature."
    ),
}

STUB_TITLES = {
    "ki": "KI-Assistent",
    "cloud": "Gemeinsames Review / Cloud-Ordner",
    "stylus": "Stylus / Palm Rejection",
    "shapes_ai": "Intelligente Formerkennung",
    "extrude3d": "3D-Extrusion",
    "plugins": "Plugin-Hooks",
    "outline_read": "Document Outline Vorlesen",
    "telemetry": "Telemetrie",
    "varfonts": "Variable Fonts",
    "envelope": "Envelope Distort",
    "esign": "E-Signatur",
}

STUB_TITLES_EN = {
    "ki": "AI assistant",
    "cloud": "Shared review / cloud folder",
    "stylus": "Stylus / palm rejection",
    "shapes_ai": "Smart shape recognition",
    "extrude3d": "3D extrusion",
    "plugins": "Plugin hooks",
    "outline_read": "Document outline read-aloud",
    "telemetry": "Telemetry",
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
    """Stub-Info; Cloud öffnet Shared-Review-Dialog (2.6.23) statt Coming-soon."""
    if key == "cloud":
        opener = getattr(parent, "_show_shared_review_dialog", None)
        if callable(opener):
            try:
                opener()
                return
            except Exception:
                pass
        # Fallback: Info mit produktivem Hinweis (kein Coming soon)
        en = get_lang() == "en"
        dlg = StubInfoDialog(
            parent,
            title=(STUB_TITLES_EN if en else STUB_TITLES).get("cloud", "Cloud"),
            short=(STUB_SHORT_EN if en else STUB_SHORT).get("cloud", ""),
            detail=(PLANNED_EN if en else PLANNED).get("cloud", ""),
            badge="2.6.23" if not en else "Live",
        )
        dlg.exec()
        return
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
