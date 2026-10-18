"""Hilfe und Feature-Liste aus einer Quelle, im Fenster und als Datei."""

from __future__ import annotations

import sys
from pathlib import Path

from spheredrive import __version__
from spheredrive.catalog import COMPARISON, DESCRIPTION, FEATURES, GUIDE
from spheredrive.i18n import LANGUAGES, get_language, set_language, t
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
            "Das Menü Sprache schaltet die Oberfläche um. Die Namen der Sprachen bleiben in der eigenen Sprache.",
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


def _features():
    return [(t(title), [t(item) for item in items]) for title, items in FEATURES]


def _chapters():
    return [(t(title), [t(item) for item in items]) for title, items in CHAPTERS]


def render_feature_text() -> str:
    lines = [t("SphereDrive Feature-Liste"), f"Version {__version__}", "", t(DESCRIPTION), ""]
    for title, items in _features():
        lines.append(title)
        lines.extend(f"- {item}" for item in items)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_help_text() -> str:
    lines = [t("SphereDrive Hilfe"), f"Version {__version__}", "", t(DESCRIPTION), ""]
    for title, items in _chapters():
        lines.append(title)
        lines.extend(f"- {item}" for item in items)
        lines.append("")
    lines.append(t("Feature-Liste"))
    lines.append("")
    for title, items in _features():
        lines.append(title)
        lines.extend(f"- {item}" for item in items)
        lines.append("")
    lines.append(t("Wann welcher Befehl"))
    lines.append("")
    for title, text in GUIDE:
        lines.append(t(title))
        lines.append(t(text))
        lines.append("")
    lines.append(t("Vergleich"))
    lines.append("")
    for row in COMPARISON:
        lines.append(
            t(
                "{befehl}: {ziel}. Erstellt {erstellt}. Neustart: {neustart}. {sphere}.",
                befehl=row["befehl"],
                ziel=t(row["ziel"]),
                erstellt=t(row["erstellt"]),
                neustart=t(row["neustart"]),
                sphere=t(row["spheredrive"]),
            )
        )
    lines.append("")
    lines.append(t("Dateien"))
    lines.append(
        t(
            "{help} und {feature} liegen neben dem Programm. Der Start und der Installer kopieren sie nach {folder}.",
            help=HELP_FILE,
            feature=FEATURE_FILE,
            folder=WORK_DIR,
        )
    )
    lines.append(t("Im Programm öffnet das Menü Hilfe dieselben Texte und die Dateien."))
    return "\n".join(lines).rstrip() + "\n"


def _in_language(code: str, render):
    previous = get_language()
    set_language(code)
    try:
        return render()
    finally:
        set_language(previous)


def _help_body() -> str:
    parts = [
        f"<h1>{_esc(t('SphereDrive Hilfe'))}</h1>",
        f"<p>{_esc(t(DESCRIPTION))}</p>",
    ]
    for title, items in _chapters():
        parts.append(f"<h2>{_esc(title)}</h2><ul>")
        parts.extend(f"<li>{_esc(item)}</li>" for item in items)
        parts.append("</ul>")
    parts.append(f"<h2>{_esc(t('Feature-Liste'))}</h2>")
    for title, items in _features():
        parts.append(f"<h3>{_esc(title)}</h3><ul>")
        parts.extend(f"<li>{_esc(item)}</li>" for item in items)
        parts.append("</ul>")
    parts.append(f"<h2>{_esc(t('Wann welcher Befehl'))}</h2>")
    for title, text in GUIDE:
        parts.append(f"<h3>{_esc(t(title))}</h3><p>{_esc(t(text))}</p>")
    parts.append(f"<h2>{_esc(t('Vergleich'))}</h2>")
    parts.append(
        "<table><thead><tr>"
        f"<th>{_esc(t('Befehl'))}</th><th>{_esc(t('Ziel'))}</th><th>{_esc(t('Erstellt'))}</th>"
        f"<th>{_esc(t('Neustart'))}</th><th>SphereDrive</th>"
        "</tr></thead><tbody>"
    )
    for row in COMPARISON:
        parts.append(
            "<tr>"
            f"<td>{_esc(row['befehl'])}</td>"
            f"<td>{_esc(t(row['ziel']))}</td>"
            f"<td>{_esc(t(row['erstellt']))}</td>"
            f"<td>{_esc(t(row['neustart']))}</td>"
            f"<td>{_esc(t(row['spheredrive']))}</td>"
            "</tr>"
        )
    parts.append("</tbody></table>")
    parts.append(f"<h2>{_esc(t('Dateien'))}</h2>")
    parts.append(
        "<p>"
        + _esc(
            t(
                "{help} und {feature} liegen neben dem Programm. Der Start und der Installer kopieren sie nach {folder}.",
                help=HELP_FILE,
                feature=FEATURE_FILE,
                folder=str(WORK_DIR),
            )
        )
        + " "
        + _esc(t("Im Programm öffnet das Menü Hilfe dieselben Texte und die Dateien."))
        + "</p>"
    )
    return "".join(parts)


def render_help_html() -> str:
    links = " ".join(
        f'<a href="#{code}" onclick="showLang(\'{code}\');return false;">{_esc(name)}</a>'
        for code, name in LANGUAGES
    )
    sections = "".join(
        f'<section id="{code}" lang="{code}"{"" if code == "de" else " hidden"}>'
        + _in_language(code, _help_body)
        + "</section>"
        for code, name in LANGUAGES
    )
    return (
        "<!DOCTYPE html>\n"
        '<html lang="de">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        "<title>SphereDrive Hilfe</title>\n"
        "<style>\n"
        "body{font-family:Segoe UI,Microsoft YaHei,Noto Sans CJK SC,sans-serif;max-width:46rem;margin:2rem auto;padding:0 1.2rem;color:#1b2531;background:#f5f7fa;line-height:1.45}\n"
        "nav a{margin-right:0.8rem} h1{font-size:1.7rem;margin-bottom:0.2rem} h2{font-size:1.15rem;margin:1.6rem 0 0.4rem}\n"
        "p,li{font-size:1rem}\n"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        f"<nav>{links}</nav>\n"
        f"{sections}\n"
        "<script>\n"
        "function showLang(code){document.querySelectorAll('section').forEach(function(node){node.hidden=node.id!==code;});}\n"
        "showLang((location.hash||'#de').slice(1));\n"
        "</script>\n"
        "</body></html>\n"
    )


def render_feature_bundle() -> str:
    parts = []
    for code, name in LANGUAGES:
        parts.append(f"===== {name} =====")
        parts.append(_in_language(code, render_feature_text).rstrip())
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def write_documents(directory: Path) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    html = directory / HELP_FILE
    features = directory / FEATURE_FILE
    _write_if_changed(html, render_help_html())
    _write_if_changed(features, render_feature_bundle())
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
