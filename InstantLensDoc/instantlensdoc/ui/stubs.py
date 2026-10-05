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
    "ki": (
        f"KI-Assistent — {__version__} produktiv: OpenAI-kompatibler Endpoint "
        "plus Offline-Fallback (Zusammenfassen/Umformulieren/Übersetzen/TOC)"
    ),
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
    "shapes_ai": (
        f"Intelligente Formerkennung — {__version__} produktiv: "
        "Tinte → Rechteck/Ellipse/Linie/Pfeil/Dreieck (DTP + Hook für Annotationen)"
    ),
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
    "varfonts": (
        f"Variable Fonts — {__version__} produktiv: fvar-Achsen + Qt wght/wdth/slnt"
    ),
    "envelope": (
        f"Envelope Distort — {__version__} produktiv: 4-Punkt-Bilinear-Warp auf DTP-Rahmen"
    ),
    "esign": (
        f"E-Signatur PAdES-B — {__version__}: PKCS#12, sichtbares Widget, "
        "Validierung; QES nur mit QTSP-Zertifikat"
    ),
    "textpath": (
        f"Text auf Pfad / Text zu Pfaden — {__version__} produktiv: "
        "Ellipse/Linie auf dem DTP-Canvas, Outlines via QPainterPath"
    ),
    "clipmask": (
        f"Schnittmasken — {__version__} produktiv: Inhalt wird mit Formrahmen geclippt"
    ),
    "livefx": (
        f"Füllungen / Live-Effekte — {__version__} produktiv: "
        "linear/radial Verlauf, Deckkraft, Schlagschatten"
    ),
    "glyphs": (
        f"Glyphen-Palette — {__version__} produktiv: Unicode-Blöcke der Systemschrift"
    ),
}

PLANNED_EN = {
    "ki": f"AI assistant — {__version__} live: OpenAI-compatible endpoint + offline fallback",
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
    "shapes_ai": f"Smart shape recognition — {__version__} live (ink → vector)",
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
    "varfonts": f"Variable fonts — {__version__} live (axes + Qt apply)",
    "envelope": f"Envelope distort — {__version__} live (4-point warp on DTP)",
    "esign": f"PAdES-B signature — {__version__}; QES requires QTSP certificate",
    "textpath": f"Text on path / outlines — {__version__} live on DTP canvas",
    "clipmask": f"Clip masks — {__version__} live (content clipped to shape)",
    "livefx": f"Fills / live effects — {__version__} live (gradient, opacity, shadow)",
    "glyphs": f"Glyph palette — {__version__} live (Unicode blocks)",
}

# Kurzbeschreibungen für Info-Dialog — 1.9.5 / Live 2.6.28
STUB_SHORT = {
    "ki": "KI-Assistent für Zusammenfassen, Umformulieren, Übersetzen, TOC — produktiv, Offline ohne Schlüssel.",
    "cloud": (
        "Gemeinsames Review: Freigabeordner + optionaler Endpoint — produktiv 2.6.23+; "
        "kein gehosteter Cloud-Dienst; lokaler Realtime-Hub (CRDT-lite) verfügbar; "
        "Offline bleibt nutzbar."
    ),
    "stylus": (
        "Drucksensitiver Stylus mit Palm Rejection — produktiv 2.6.28 "
        "(Tablet-Druck → Strichstärke; sonst Freihand)."
    ),
    "shapes_ai": "Intelligente Formerkennung (Tinte → Vektorform) — produktiv 2.6.54.",
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
    "varfonts": "Variable Fonts (Achsen wght/wdth/slnt) — produktiv 2.6.54.",
    "envelope": "Envelope-Distort auf DTP-Rahmen — produktiv 2.6.54.",
    "esign": (
        "PAdES-B mit PKCS#12 und sichtbarem Widget — produktiv 2.6.54; "
        "QES nur mit QTSP-Zertifikat."
    ),
    "textpath": "Text auf Pfad / Text in Pfade — produktiv 2.6.54 (DTP-Canvas).",
    "clipmask": "Schnittmasken — produktiv 2.6.54 (Inhalt clippt an Formrahmen).",
    "livefx": "Verlauf, Deckkraft, Schlagschatten — produktiv 2.6.54.",
    "glyphs": "Glyphen-Palette — produktiv 2.6.54 (Unicode der Systemschrift).",
}

STUB_SHORT_EN = {
    "ki": "AI assistant for summary/rewrite/translate/TOC — live, offline without a key.",
    "cloud": (
        "Shared review: folder sync + optional endpoint — live since 2.6.23; "
        "no hosted cloud service; local realtime hub (CRDT-lite) available; "
        "offline remains usable."
    ),
    "stylus": (
        "Pressure-sensitive stylus with palm rejection — live 2.6.28 "
        "(tablet pressure → stroke width; else freehand)."
    ),
    "shapes_ai": "Smart shape recognition (ink → vector) — live 2.6.54.",
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
    "varfonts": "Variable fonts (wght/wdth/slnt axes) — live 2.6.54.",
    "envelope": "Envelope distort on DTP frames — live 2.6.54.",
    "esign": (
        "PAdES-B with PKCS#12 and visible widget — live 2.6.54; "
        "QES only with a QTSP certificate."
    ),
    "textpath": "Text on path / outlines — live 2.6.54 (DTP canvas).",
    "clipmask": "Clip masks — live 2.6.54 (content clipped to a shape).",
    "livefx": "Gradient, opacity, drop shadow — live 2.6.54.",
    "glyphs": "Glyph palette — live 2.6.54 (system-font Unicode).",
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
    "textpath": "Text auf Pfad",
    "clipmask": "Schnittmaske",
    "livefx": "Füllung / Live-Effekt",
    "glyphs": "Glyphen-Palette",
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
    "textpath": "Text on path",
    "clipmask": "Clip mask",
    "livefx": "Fill / live effect",
    "glyphs": "Glyph palette",
}

# Features die live sind und eigene Dialoge öffnen (nicht Coming-soon)
_LIVE_KEYS = frozenset(
    {
        "cloud",
        "stylus",
        "extrude3d",
        "plugins",
        "telemetry",
        "ki",
        "shapes_ai",
        "varfonts",
        "envelope",
        "esign",
        "textpath",
        "clipmask",
        "livefx",
        "glyphs",
    }
)


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
    """Live-Feature öffnen oder Info-Dialog — 2.6.54."""
    dispatch = {
        "ki": "_show_ki_assistant",
        "shapes_ai": "_run_shape_recognition",
        "varfonts": "_show_variable_fonts",
        "envelope": "_apply_envelope_distort",
        "esign": "_show_pades_dialog",
        "textpath": "_dtp_text_on_path",
        "clipmask": "_dtp_clip_mask",
        "livefx": "_dtp_live_fill",
        "glyphs": "_dtp_glyph_palette",
        "cloud": "_show_shared_review_dialog",
        "extrude3d": "_show_extrude3d_dialog",
        "stylus": "_activate_stylus_tool",
        "plugins": "_show_hooks_info",
        "telemetry": "_show_telemetry_settings",
    }
    meth = dispatch.get(key)
    if meth and parent is not None:
        opener = getattr(parent, meth, None)
        if callable(opener):
            try:
                opener()
                return
            except Exception:
                pass
    if key == "extrude3d":
        try:
            from instantlensdoc.ui.extrude3d_dialog import Extrude3DDialog

            Extrude3DDialog(parent).exec()
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
