"""Programm-Äquivalente. Paketnamen kommen nur aus diesem Katalog."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass

from cpcm.paths import World

_PACKAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
_WINGET = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*(\.[A-Za-z0-9][A-Za-z0-9._+-]*)+$")
MANAGERS = {World.WINDOWS: ("winget", "scoop"), World.LINUX: ("apt", "pacman", "dnf", "flatpak", "snap")}


@dataclass(frozen=True)
class App:
    id: str
    names: tuple[str, ...]
    kind: str
    note: str
    binaries: tuple[str, ...]
    packages: dict[str, str]


def _app(app_id, names, kind, note, binaries, **packages) -> App:
    return App(app_id, names, kind, note, binaries, packages)


CATALOG = (
    _app("git", ("git",), "equivalent", "Dieselbe Versionsverwaltung.", ("git",), winget="Git.Git", scoop="git", apt="git", pacman="git", dnf="git"),
    _app("vscode", ("visual studio code", "vscode", "code"), "equivalent", "Dieselbe Anwendung.", ("code",), winget="Microsoft.VisualStudioCode", scoop="vscode", apt="code", flatpak="com.visualstudio.code"),
    _app("firefox", ("firefox",), "equivalent", "Dieselbe Anwendung.", ("firefox",), winget="Mozilla.Firefox", scoop="firefox", apt="firefox", pacman="firefox", dnf="firefox", flatpak="org.mozilla.firefox", snap="firefox"),
    _app("chrome", ("google chrome", "chrome"), "equivalent", "Dieselbe Anwendung.", ("google-chrome", "google-chrome-stable"), winget="Google.Chrome", scoop="googlechrome", apt="google-chrome-stable", flatpak="com.google.Chrome"),
    _app("notepadpp", ("notepad++", "notepadpp"), "workflow", "Notepad-Next ist die plattformübergreifende Fortsetzung, kein eingebautes Windows-Notepad.", ("notepad++", "notepad-next"), winget="Notepad++.Notepad++", scoop="notepadplusplus", apt="notepad-next", flatpak="com.github.dail8859.NotepadNext"),
    _app("gimp", ("gimp", "photoshop"), "workflow", "Photoshop hat kein freies Gegenstück. GIMP übernimmt Bildbearbeitung, Krita eher Illustration.", ("gimp",), winget="GIMP.GIMP", scoop="gimp", apt="gimp", pacman="gimp", dnf="gimp", flatpak="org.gimp.GIMP"),
    _app("krita", ("krita",), "workflow", "Zeichen- und Illustrationsprogramm.", ("krita",), winget="KDE.Krita", scoop="krita", apt="krita", flatpak="org.kde.krita"),
    _app("sevenzip", ("7-zip", "7zip"), "equivalent", "Archivprogramm.", ("7z",), winget="7zip.7zip", scoop="7zip", apt="7zip", pacman="7zip", dnf="p7zip"),
    _app("vlc", ("vlc",), "equivalent", "Dieselbe Anwendung.", ("vlc",), winget="VideoLAN.VLC", scoop="vlc", apt="vlc", flatpak="org.videolan.VLC"),
    _app("keepassxc", ("keepassxc", "keepass"), "equivalent", "KeePassXC liest KeePass-Dateien.", ("keepassxc",), winget="KeePassXCTeam.KeePassXC", apt="keepassxc", flatpak="org.keepassxc.KeePassXC"),
    _app("thunderbird", ("thunderbird", "outlook"), "workflow", "Outlook hat kein freies Gegenstück. Thunderbird übernimmt Mail.", ("thunderbird",), winget="Mozilla.Thunderbird", apt="thunderbird", flatpak="org.mozilla.Thunderbird"),
    _app("libreoffice", ("libreoffice", "word", "excel"), "workflow", "Office-Dokumente bearbeiten, ohne Microsoft Office zu ersetzen.", ("libreoffice",), winget="TheDocumentFoundation.LibreOffice", apt="libreoffice", flatpak="org.libreoffice.LibreOffice"),
    _app("docker", ("docker", "docker desktop"), "workflow", "Docker Engine ist gemeinsam. Docker Desktop ist die grafische Hülle.", ("docker",), winget="Docker.DockerDesktop", apt="docker.io", pacman="docker", dnf="docker"),
    _app("nodejs", ("node", "nodejs"), "equivalent", "Dieselbe Laufzeit.", ("node",), winget="OpenJS.NodeJS", scoop="nodejs", apt="nodejs", pacman="nodejs", dnf="nodejs"),
    _app("python", ("python", "python3"), "equivalent", "Dieselbe Sprache.", ("python3", "python"), winget="Python.Python.3.12", scoop="python", apt="python3", pacman="python", dnf="python3"),
    _app("ssh", ("openssh", "putty", "ssh"), "workflow", "OpenSSH ist auf beiden Systemen vorhanden.", ("ssh",), winget="Microsoft.OpenSSH.Beta", apt="openssh-client", pacman="openssh", dnf="openssh-clients"),
    _app("filezilla", ("filezilla", "winscp"), "workflow", "WinSCP bleibt Windows. FileZilla läuft auf beiden Systemen.", ("filezilla",), winget="FileZilla.FileZilla", apt="filezilla", flatpak="org.filezillaproject.Filezilla"),
    _app("steam", ("steam",), "equivalent", "Dieselbe Anwendung.", ("steam",), winget="Valve.Steam", apt="steam", flatpak="com.valvesoftware.Steam"),
)


def validate_package(manager: str, name: str) -> str:
    if manager == "winget":
        if not _WINGET.match(name):
            raise ValueError(f"Ungültige winget-ID: {name}")
        return name
    if manager not in ("scoop", "apt", "pacman", "dnf", "flatpak", "snap"):
        raise ValueError(f"Unbekannter Paketmanager: {manager}")
    if not _PACKAGE.match(name):
        raise ValueError(f"Ungültiger Paketname: {name}")
    return name


def _find(token: str) -> App | None:
    folded = token.strip().casefold()
    if not folded:
        return None
    for app in CATALOG:
        if folded == app.id or folded in app.names:
            return app
    for app in CATALOG:
        if any(folded in name or name in folded for name in app.names):
            return app
    return None


def detect_installed() -> list[str]:
    return [app.id for app in CATALOG if any(shutil.which(binary) for binary in app.binaries)]


def _command(manager: str, package: str) -> str:
    package = validate_package(manager, package)
    return {
        "winget": f"winget install --id {package} -e",
        "scoop": f"scoop install {package}",
        "apt": f"sudo apt-get install -y {package}",
        "pacman": f"sudo pacman -S --needed {package}",
        "dnf": f"sudo dnf install -y {package}",
        "flatpak": f"flatpak install -y flathub {package}",
        "snap": f"sudo snap install {package}",
    }[manager]


def plan(names: list[str], target: World, manager: str) -> dict:
    if manager not in MANAGERS[target]:
        raise ValueError(f"{manager} gibt es in der Welt {target.value} nicht")
    items, unknown = [], []
    for name in names:
        app = _find(name)
        if app is None:
            unknown.append(name)
            continue
        package = app.packages.get(manager)
        if not package:
            items.append({"id": app.id, "kind": app.kind, "note": app.note, "package": None, "command": None, "status": "kein Paket für diesen Manager"})
            continue
        items.append({"id": app.id, "kind": app.kind, "note": app.note, "package": package, "command": _command(manager, package), "status": "bereit"})
    return {"manager": manager, "target": target.value, "items": items, "unknown": unknown}
