"""Hilfetext für das Flare-Fenster.

Die Texte stehen hier, damit Tests sie ohne Win32-Fenster lesen können.
"""

from __future__ import annotations


def short_description() -> str:
    """Kurzbeschreibung, ein oder zwei Sätze."""
    return (
        "Flare sucht auf Windows 11 Programme, Ordner und Dateien "
        "und öffnet sie aus einem eigenen Fenster. "
        "Strg+Alt+Leertaste holt die Suche nach vorn."
    )


def description() -> str:
    """Etwas längerer Beschreibungstext, immer noch ohne Werbesprache."""
    return (
        "Das Fenster ist ein normales Win32-Fenster in diesem Prozess. "
        "Es startet weder Chrome noch Edge. Schließen oder Escape blendet das Fenster "
        "nur aus; der Index läuft im Hintergrund weiter. Enter öffnet den markierten Treffer. "
        "Eine Rechnung wie 2+2*3 erscheint als Treffer, Enter kopiert das Ergebnis. "
        "Das Kontrollkästchen „Ähnliche Namen“ sucht auch nahe Dateinamen. "
        "Dieselbe Suche gibt es als --similar und als similar=1. "
        "Andere Programme fragen über 127.0.0.1, Port 47731, nach. "
        "Der Knopf Hilfe und die Taste F1 öffnen diesen Text. "
        "Escape schließt die Hilfe und kehrt zur Suche zurück."
    )


def features() -> list[str]:
    """Feature-Liste, ein Punkt pro Zeile."""
    return [
        "Spotlight-Suche im eigenen Win32-Fenster, Kürzel Strg+Alt+Leertaste.",
        "Schließen blendet das Fenster aus, der Index läuft weiter.",
        "Ähnliche Namen über das Kontrollkästchen, --similar und similar=1; umgekehrter Trigramm-Index, CUDA über nvcuda.dll ab 32 Kandidaten, sonst die CPU.",
        "Index aus Startmenü-Verknüpfungen (.lnk), PATH-Programmen (.exe, .bat, .cmd, .com) und den Ordnern Desktop, Dokumente, Downloads, Bilder, Musik, Videos und dem Benutzerprofil.",
        "Übersprungen werden node_modules, .git, versteckte Ordner und Geheimnisdateien.",
        "Index-Last etwa 85 % in den ersten 20 Sekunden, danach etwa 35 %. Ist die CPU beschäftigt, wartet Flare zusätzlich.",
        "Andere Programme: HTTP auf 127.0.0.1 Port 47731, flare.py query und flare.client.Client.",
        "Einrichtung pro Benutzer unter %LOCALAPPDATA%\\Programs\\Flare. Katalog und Index bleiben unter %LOCALAPPDATA%\\Flare und werden beim Entfernen nicht gelöscht. Das Setup beendet ein laufendes Flare.exe, bevor es DLLs kopiert.",
        "Rechnung wie 2+2*3. Enter öffnet einen Treffer, Escape blendet die Suche aus.",
        "Hilfe über den Knopf Hilfe oder F1. Escape schließt die Hilfe und kehrt zur Suche zurück.",
    ]


def help_text() -> str:
    """Kurzbeschreibung, Beschreibung und Feature-Liste als ein Text."""
    lines = [
        "Kurzbeschreibung",
        "",
        short_description(),
        "",
        "Beschreibung",
        "",
        description(),
        "",
        "Feature-Liste",
        "",
    ]
    lines.extend(f"• {item}" for item in features())
    return "\n".join(lines)
