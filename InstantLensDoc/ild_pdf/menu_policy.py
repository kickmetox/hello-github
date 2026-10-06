"""PDF-Menü: Enablement-Klassen — kein No-Op, Dialog oder Dateiänderung.

always  — Dateidialoge, unabhängig vom aktuellen Tab (Merge, Vergleich, Scan, …)
pdf     — braucht aktuellen PDF-Tab (sonst disabled, auch bei offenem Geschwister-PDF)
selection — braucht aktiven PDF-Tab plus Auswahl (Stempel, Bookmark, Textauswahl, …)
"""

from __future__ import annotations

ALWAYS_ON_NEEDLES: tuple[str, ...] = (
    "zusammenführen",
    "vergleichen",
    "scannen",
    "scan",
    "drucker",
    "gerät",
    "portfolio",
    "stempel-bibliothek",
    "annotation-vorlagen",
    "annotation-suche",
)

SELECTION_NEEDLES: tuple[str, ...] = (
    "stempel 90",
    "lesezeichen löschen",
    "auswahl → text",
    "auswahl → schwärzung",
    "messwerte",
)

SELECTION_REASONS: tuple[tuple[str, str], ...] = (
    ("stempel 90", "Kein Stempel ausgewählt"),
    ("lesezeichen löschen", "Kein Lesezeichen ausgewählt"),
    ("auswahl → text", "Keine Textauswahl"),
    ("auswahl → schwärzung", "Keine Textauswahl"),
    ("messwerte", "Keine Mess-Annotationen"),
)


def normalize_menu_label(label: str) -> str:
    return (label or "").replace("&", "").strip().lower()


def pdf_menu_need(label: str) -> str:
    """always | pdf | selection."""
    t = normalize_menu_label(label)
    if any(n in t for n in ALWAYS_ON_NEEDLES):
        return "always"
    if any(n in t for n in SELECTION_NEEDLES):
        return "selection"
    return "pdf"


def pdf_menu_disable_reason(label: str, *, has_open_pdf: bool, is_pdf_tab: bool) -> str:
    """Tooltip-Grund wenn der Eintrag disabled ist."""
    need = pdf_menu_need(label)
    t = normalize_menu_label(label)
    if need == "always":
        return ""
    if need == "selection":
        if not is_pdf_tab:
            return "Aktiver Tab ist kein PDF"
        for needle, reason in SELECTION_REASONS:
            if needle in t:
                return reason
        return "Keine Auswahl"
    if not has_open_pdf:
        return "Nur bei geöffnetem PDF verfügbar"
    if not is_pdf_tab:
        return "Aktiver Tab ist kein PDF"
    return "Nur bei geöffnetem PDF verfügbar"
