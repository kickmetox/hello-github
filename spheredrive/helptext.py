"""Hilfe und Feature-Liste aus einer Quelle, im Fenster und als Datei."""

from __future__ import annotations

import sys
from pathlib import Path

from spheredrive import __version__
from spheredrive.catalog import COMPARISON, DESCRIPTION, FEATURES, GUIDE
from spheredrive.paths import WORK_DIR, install_root, package_root

HELP_FILE = "SphereDrive-Hilfe.html"
FEATURE_FILE = "SphereDrive-Feature-Liste.txt"

CHAPTERS: list[tuple[str, list[str]]] = [
    (
        "Menüleiste",
        [
            "Datei aktualisiert die Anzeige oder beendet das Programm.",
            "Subst, net use, Verknüpfungen, PowerShell und Bereitstellung sind gleich aufgebaut: Seite öffnen, neu anlegen und trennen.",
            "Das Menü net use enthält Seite öffnen, Freigabe verbinden, Ordner freigeben und Trennen.",
            "Hilfe öffnet diesen Text, die Feature-Liste und die Dateien neben dem Programm.",
        ],
    ),
    (
        "Kachelmenü",
        [
            "Die drei Punkte an einer Kachel öffnen Alle Möglichkeiten, net use, Im Explorer öffnen und, wenn erlaubt, Trennen.",
            "net use auf einem echten Datenträger wie C: legt sich nicht über diesen Buchstaben. Es öffnet die Verbindung mit einem freien Buchstaben.",
        ],
    ),
    (
        "net use",
        [
            "Der Befehl lautet net use X: \\\\Computer\\Freigabe.",
            "Dauerhaft setzt /persistent:yes. Ohne diese Option gilt die Verbindung nur bis zum Abmelden.",
            "Ein Kennwort wird nur für den Aufruf verwendet und nicht in der Konfiguration gespeichert.",
            "Ein lokaler Ordner muss zuerst freigegeben sein. Danach verbindet net use \\\\Computer\\Freigabename.",
            "Freigabe verbinden öffnet den Dialog mit der Möglichkeit net use. Ordner freigeben wechselt auf die Seite Netzlaufwerke und zeigt dort das Freigeben eines Ordners.",
        ],
    ),
    (
        "Subst, Verknüpfungen, PowerShell und Bereitstellung",
        [
            "Subst hängt einen lokalen Ordner, auch einen Unterordner, als Laufwerksbuchstaben ein.",
            "Verknüpfungen legen Junctions, symbolische Links und Hardlinks an. Entfernen löscht nur die Verknüpfung.",
            "PowerShell legt ein New-PSDrive an, auf Wunsch im Profil. -Persist gilt nur für UNC-Pfade.",
            "Bereitstellung hängt eine Partition oder eine VHD an einen Buchstaben oder einen leeren NTFS-Ordner. Die Datenträgerverwaltung öffnet diskmgmt.msc.",
        ],
    ),
]


def render_feature_text() -> str:
    lines = ["SphereDrive Feature-Liste", f"Version {__version__}", "", DESCRIPTION, ""]
    for title, items in FEATURES:
        lines.append(title)
        lines.extend(f"- {item}" for item in items)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_help_text() -> str:
    lines = ["SphereDrive Hilfe", f"Version {__version__}", "", DESCRIPTION, ""]
    for title, items in CHAPTERS:
        lines.append(title)
        lines.extend(f"- {item}" for item in items)
        lines.append("")
    lines.append("Feature-Liste")
    lines.append("")
    for title, items in FEATURES:
        lines.append(title)
        lines.extend(f"- {item}" for item in items)
        lines.append("")
    lines.append("Wann welcher Befehl")
    lines.append("")
    for title, text in GUIDE:
        lines.append(title)
        lines.append(text)
        lines.append("")
    lines.append("Vergleich")
    lines.append("")
    for row in COMPARISON:
        lines.append(
            f"{row['befehl']}: {row['ziel']}. Erstellt {row['erstellt']}. "
            f"Neustart: {row['neustart']}. {row['spheredrive']}."
        )
    lines.append("")
    lines.append("Dateien")
    lines.append(
        f"{HELP_FILE} und {FEATURE_FILE} liegen neben dem Programm. "
        f"Der Start und der Installer kopieren sie nach {WORK_DIR}."
    )
    lines.append("Im Programm öffnet das Menü Hilfe dieselben Texte und die Dateien.")
    return "\n".join(lines).rstrip() + "\n"


def render_help_html() -> str:
    parts = [
        "<!DOCTYPE html>",
        '<html lang="de">',
        "<head>",
        '<meta charset="utf-8">',
        "<title>SphereDrive Hilfe</title>",
        "<style>",
        "body{font-family:Segoe UI,sans-serif;max-width:46rem;margin:2rem auto;padding:0 1.2rem;color:#1b2531;background:#f5f7fa;line-height:1.45}",
        "h1{font-size:1.7rem;margin-bottom:0.2rem} h2{font-size:1.15rem;margin:1.6rem 0 0.4rem}",
        "p,li{font-size:1rem} .version{color:#5c6b7a;margin-top:0}",
        "table{border-collapse:collapse;width:100%;background:#fff} th,td{border:1px solid #d5dde6;padding:0.4rem 0.55rem;text-align:left;vertical-align:top}",
        "th{background:#e8eef5}",
        "</style>",
        "</head>",
        "<body>",
        "<h1>SphereDrive Hilfe</h1>",
        f'<p class="version">Version {_esc(__version__)}</p>',
        f"<p>{_esc(DESCRIPTION)}</p>",
    ]
    for title, items in CHAPTERS:
        parts.append(f"<h2>{_esc(title)}</h2>")
        parts.append("<ul>")
        parts.extend(f"<li>{_esc(item)}</li>" for item in items)
        parts.append("</ul>")
    parts.append("<h2>Feature-Liste</h2>")
    for title, items in FEATURES:
        parts.append(f"<h3>{_esc(title)}</h3><ul>")
        parts.extend(f"<li>{_esc(item)}</li>" for item in items)
        parts.append("</ul>")
    parts.append("<h2>Wann welcher Befehl</h2>")
    for title, text in GUIDE:
        parts.append(f"<h3>{_esc(title)}</h3><p>{_esc(text)}</p>")
    parts.append("<h2>Vergleich</h2>")
    parts.append("<table><thead><tr><th>Befehl</th><th>Ziel</th><th>Erstellt</th><th>Neustart</th><th>SphereDrive</th></tr></thead><tbody>")
    for row in COMPARISON:
        parts.append(
            "<tr>"
            f"<td>{_esc(row['befehl'])}</td>"
            f"<td>{_esc(row['ziel'])}</td>"
            f"<td>{_esc(row['erstellt'])}</td>"
            f"<td>{_esc(row['neustart'])}</td>"
            f"<td>{_esc(row['spheredrive'])}</td>"
            "</tr>"
        )
    parts.append("</tbody></table>")
    parts.append("<h2>Dateien</h2>")
    parts.append(
        f"<p>{_esc(HELP_FILE)} und {_esc(FEATURE_FILE)} liegen neben dem Programm. "
        f"Der Start und der Installer kopieren sie nach {_esc(str(WORK_DIR))}. "
        "Im Programm öffnet das Menü Hilfe dieselben Texte und die Dateien.</p>"
    )
    parts.append("</body></html>\n")
    return "\n".join(parts)


def write_documents(directory: Path) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    html = directory / HELP_FILE
    features = directory / FEATURE_FILE
    _write_if_changed(html, render_help_html())
    _write_if_changed(features, render_feature_text())
    return html, features


def locate_document(name: str) -> Path | None:
    for directory in _document_directories():
        path = directory / name
        if path.is_file():
            return path
    return None


def ensure_documents() -> tuple[Path | None, Path | None]:
    for directory in _document_directories():
        try:
            write_documents(directory)
        except OSError:
            continue
    return locate_document(HELP_FILE), locate_document(FEATURE_FILE)


def _document_directories() -> list[Path]:
    directories: list[Path] = []
    if sys.platform == "win32":
        directories.append(WORK_DIR)
    installed = install_root()
    if installed is not None:
        directories.append(installed)
    directories.append(package_root())
    return directories


def _write_if_changed(path: Path, text: str) -> None:
    if path.is_file():
        try:
            if path.read_text(encoding="utf-8") == text:
                return
        except OSError:
            pass
    path.write_text(text, encoding="utf-8")


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
