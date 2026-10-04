"""UI-Stubs / Live-Umleitungen für geplante bzw. ausgelieferte Features."""

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
        "Stempel/Kommentare austauschbar (kein gehosteter Cloud-Dienst); "
        "lokaler Realtime-Hub (TCP JSON-Lines CRDT-lite) via realtime_collab / "
        "realtime_start_hub verfügbar"
    ),
    "stylus": (
        f"Stylus / Palm Rejection — {__version__} produktiv: "
        "Tablet-Stift mit Druck→Strichstärke; Palm-Rejection-Heuristik; "
        "ohne Druck = verbesserte Freihand-Integration"
    ),
    "shapes_ai": f"Intelligente Formerkennung — Stub {__version__}",
    "extrude3d": (
        f"3D-Extrusion — {__version__} Limited Viewer: isometrische Extrusion "
        "einfacher Formen (kein Mesh-Import, kein OpenGL)"
    ),
    "plugins": (
        f"Plugin-Hooks — {__version__} produktiv: Event-Bus + User-Skripte "
        "(open/save/export/ocr) via Python/PowerShell ild; kein Marketplace"
    ),
    "outline_read": (
        f"Document Outline Vorlesen — Stub {__version__} "
        "(TTS/Screenreader-Anbindung geplant; Pane selbst produktiv)"
    ),
    "telemetry": (
        f"Telemetrie — {__version__} optional lokal: Opt-in Default aus "
        "(Toggle default disabled), kein Netzwerk, kein PII, keine Datenübertragung "
        "— nur diagnostics.jsonl; Stubs öffnen · Esc · Fokus · warum lokal"
    ),
    "varfonts": "Variable Fonts (voll) — geplant",
    "envelope": "Envelope Distort (voll) — geplant",
    "esign": (
        f"E-Signatur QES/QTSP-Trust — {__version__}: "
        "AES/SES produktiv; Trust-Pfad (verify_trust_path / eidas_trust_info) "
        "ohne bezahlte TSA; volle QES/Zeitstempel bleibt QTSP"
    ),
}

PLANNED_EN = {
    "ki": f"AI assistant — stub {__version__} (Coming soon)",
    "cloud": (
        f"Shared review / cloud folder — {__version__} live: "
        "shared-folder sync + optional HTTP endpoint; notes/highlights/"
        "stamps/comments exchangeable (no hosted cloud service); "
        "local realtime hub (TCP JSON-lines CRDT-lite) available via "
        "realtime_collab / realtime_start_hub"
    ),
    "stylus": (
        f"Stylus / palm rejection — {__version__} live: "
        "tablet pen with pressure→stroke width; palm-rejection heuristic; "
        "without pressure = improved freehand integration"
    ),
    "shapes_ai": f"Smart shape recognition — stub {__version__}",
    "extrude3d": (
        f"3D extrusion — {__version__} limited viewer: isometric extrusion "
        "of simple shapes (no mesh import, no OpenGL)"
    ),
    "plugins": (
        f"Plugin hooks — {__version__} live: event bus + user scripts "
        "(open/save/export/ocr) via Python/PowerShell ild; no marketplace"
    ),
    "outline_read": (
        f"Document outline read-aloud — stub {__version__} "
        "(TTS/screen reader planned; outline pane itself is live)"
    ),
    "telemetry": (
        f"Telemetry — {__version__} optional local: opt-in default off "
        "(toggle default disabled), no network, no PII, no data transfer "
        "— diagnostics.jsonl only; open Stubs · Esc · focus · why local"
    ),
    "varfonts": "Variable fonts (full) — planned",
    "envelope": "Envelope distort (full) — planned",
    "esign": (
        f"E-signature QES/QTSP trust — {__version__}: "
        "AES/SES live; trust path (verify_trust_path / eidas_trust_info) "
        "without paid TSA; full QES/timestamp remains QTSP"
    ),
}

# Kurzbeschreibungen für Info-Dialog — 1.9.5 / Live 2.6.28
STUB_SHORT = {
    "ki": "Lokaler KI-Assistent für Zusammenfassen und Vorschläge — Stub / nicht produktiv.",
    "cloud": (
        "Gemeinsames Review: Freigabeordner + optionaler Endpoint — produktiv 2.6.23+; "
        "kein gehosteter Cloud-Dienst; lokaler Realtime-Hub (CRDT-lite) verfügbar; "
        "Offline bleibt nutzbar."
    ),
    "stylus": (
        "Drucksensitiver Stylus mit Palm Rejection — produktiv 2.6.28 "
        "(Tablet-Druck → Strichstärke; sonst Freihand)."
    ),
    "shapes_ai": "Intelligente Formerkennung beim Zeichnen — Stub / geplant.",
    "extrude3d": (
        "3D-Extrusion Limited Viewer — produktiv 2.6.28 "
        "(isometrisch, einfache Formen; kein Mesh/OpenGL)."
    ),
    "plugins": (
        "User-/Script-Hooks (open/save/export/ocr) — produktiv 2.6.28; "
        "Python/PowerShell ild; kein Marketplace-Plugin-System."
    ),
    "outline_read": (
        "Document Outline Vorlesen (TTS) — Stub / geplant; "
        "Struktur-Pane (Überschriften/Lesezeichen) produktiv 2.6.28."
    ),
    "telemetry": (
        "Optionale lokale Diagnostik — produktiv 2.6.28: Opt-in Default aus, "
        "kein Netzwerk, kein PII, keine Datenübertragung (diagnostics.jsonl)."
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
        "Shared review: folder sync + optional endpoint — live since 2.6.23; "
        "no hosted cloud service; local realtime hub (CRDT-lite) available; "
        "offline remains usable."
    ),
    "stylus": (
        "Pressure-sensitive stylus with palm rejection — live 2.6.28 "
        "(tablet pressure → stroke width; else freehand)."
    ),
    "shapes_ai": "Smart shape recognition while drawing — stub / planned.",
    "extrude3d": (
        "3D extrusion limited viewer — live 2.6.28 "
        "(isometric, simple shapes; no mesh/OpenGL)."
    ),
    "plugins": (
        "User/script hooks (open/save/export/ocr) — live 2.6.28; "
        "Python/PowerShell ild; no marketplace plugin system."
    ),
    "outline_read": (
        "Document outline read-aloud (TTS) — stub / planned; "
        "structure pane (headings/bookmarks) live 2.6.28."
    ),
    "telemetry": (
        "Optional local diagnostics — live 2.6.28: opt-in default off, "
        "no network, no PII, no data transfer (diagnostics.jsonl)."
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

# Features die live sind und eigene Dialoge öffnen (nicht Coming-soon)
_LIVE_KEYS = frozenset({"cloud", "stylus", "extrude3d", "plugins", "telemetry"})


class StubInfoDialog(QDialog):
    """Info-Dialog für Stubs/Live-Hinweise: Kurzbeschreibung + Badge „Geplant“/Live; Esc schließt."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        title: str,
        short: str,
        detail: str,
        badge: str = "Geplant",
        note: str | None = None,
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
        live = badge.lower() in ("live", "2.6.28", "produktiv") or "2.6.28" in badge
        if live:
            self.badge.setStyleSheet(
                "QLabel#stubInfoBadge {"
                " background:#e8f5e9; color:#1b5e20; border:1px solid #66bb6a;"
                " border-radius:4px; padding:2px 8px; font-weight:700;"
                "}"
            )
            self.badge.setToolTip("Produktiv / live — 2.6.28")
        else:
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

        note_txt = note
        if note_txt is None:
            note_txt = (
                "Produktiv / live."
                if live
                else "Stub / nicht produktiv — keine Aktion."
            )
        note_lbl = QLabel(note_txt)
        note_lbl.setObjectName("stubInfoNote")
        note_lbl.setStyleSheet(
            "color:#1b5e20;font-weight:600;margin-top:8px;"
            if live
            else "color:#8a5a00;font-weight:600;margin-top:8px;"
        )
        note_lbl.setWordWrap(True)
        layout.addWidget(note_lbl)

        layout.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        close_btn = buttons.button(QDialogButtonBox.Close)
        if close_btn is not None:
            close_btn.setText("Schließen")
            close_btn.setToolTip("Esc schließt ebenfalls — 1.9.5")
        layout.addWidget(buttons)

        esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        esc.setContext(Qt.WindowShortcut)
        esc.activated.connect(self.reject)


def show_planned(parent: QWidget | None, key: str) -> None:
    """Stub-Info oder Live-Feature öffnen — 2.6.28."""
    if key == "cloud":
        opener = getattr(parent, "_show_shared_review_dialog", None)
        if callable(opener):
            try:
                opener()
                return
            except Exception:
                pass
    if key == "extrude3d":
        opener = getattr(parent, "_show_extrude3d_dialog", None)
        if callable(opener):
            try:
                opener()
                return
            except Exception:
                pass
        try:
            from instantlensdoc.ui.extrude3d_dialog import Extrude3DDialog

            Extrude3DDialog(parent).exec()
            return
        except Exception:
            pass
    if key == "stylus":
        opener = getattr(parent, "_activate_stylus_tool", None)
        if callable(opener):
            try:
                opener()
                return
            except Exception:
                pass
    if key == "plugins":
        opener = getattr(parent, "_show_hooks_info", None)
        if callable(opener):
            try:
                opener()
                return
            except Exception:
                pass
    if key == "telemetry":
        opener = getattr(parent, "_show_telemetry_settings", None)
        if callable(opener):
            try:
                opener()
                return
            except Exception:
                pass

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
    if key in _LIVE_KEYS:
        badge = "2.6.28" if not en else "Live"
        note = "Produktiv / live." if not en else "Live / production."
    else:
        badge = tr("planned")
        note = None
    dlg = StubInfoDialog(
        parent, title=title, short=short, detail=detail, badge=badge, note=note
    )
    dlg.exec()
