"""Lokale Klartext-Analyse. Ausführung nur für Zeilen auf der Allowlist."""

from __future__ import annotations

import re
from dataclasses import dataclass

from cpcm.paths import World


@dataclass(frozen=True)
class Pattern:
    id: str
    regex: str
    title: str
    explanation: str
    cause: str
    severity: str
    risk: str
    worlds: tuple[str, ...]
    linux_script: str = ""
    windows_script: str = ""


PATTERNS = (
    Pattern("win-file-not-found", r"0x80070002", "Datei oder Ordner fehlt", "Windows meldet ERROR_FILE_NOT_FOUND (0x80070002). Eine Datei oder ein Ordner fehlt.", "Verschobene Datei, falscher Konfigurationspfad oder ein Update, das eine Komponente nicht mitinstalliert hat.", "hoch", "niedrig", ("windows",), windows_script="Get-ChildItem -Force $env:USERPROFILE | Out-Null\n# Gezielten Pfad aus der Meldung prüfen, nichts pauschal neu anlegen."),
    Pattern("win-access-denied", r"0x80070005", "Zugriff verweigert", "0x80070005 ist ERROR_ACCESS_DENIED. Der Prozess darf das Ziel nicht ändern.", "Fehlende Benutzerrechte oder eine gesperrte Datei.", "hoch", "mittel", ("windows",), windows_script="# icacls \"<PFAD>\" /grant \"${env:USERNAME}:(M)\""),
    Pattern("win-fail", r"0x80004005", "Allgemeiner Fehler", "0x80004005 (E_FAIL) sagt nur, dass der Vorgang gescheitert ist. Die Zeile davor nennt die Ursache.", "Folgefehler von Netz, Sperre oder Dienst.", "mittel", "niedrig", ("windows",)),
    Pattern("win-invalidarg", r"0x80070057", "Ungültiges Argument", "0x80070057 bedeutet einen falschen Parameter, oft einen Pfad der anderen Welt.", "Leerer oder fremder Pfad.", "mittel", "niedrig", ("windows",)),
    Pattern("win-corrupt", r"0x80070570", "Datei beschädigt", "0x80070570: Windows konnte die Datei nicht lesen.", "Abgebrochener Schreibvorgang oder ein fehlerhafter Datenträger.", "hoch", "hoch", ("windows",), windows_script="# Nur prüfen:\nchkdsk <LAUFWERK>: /scan"),
    Pattern("access-violation", r"0x[Cc]0000005", "Speicherzugriff verletzt", "0xC0000005 ist eine Zugriffsverletzung im Programm, kein Registry-Schalter.", "Fehler in der Anwendung oder einem Plugin.", "hoch", "hoch", ("windows",)),
    Pattern("segfault", r"segmentation fault(?: \(core dumped\))?", "Speicherzugriff verletzt", "Segmentation fault bedeutet, dass ein Programm auf ungültigen Speicher zugegriffen hat.", "Fehler im Programm oder eine Bibliothek in der falschen Version.", "hoch", "hoch", ("linux",)),
    Pattern("missing-so", r"error while loading shared libraries: ([\w.+-]+\.so(?:\.[\d]+)*)", "Gemeinsame Bibliothek fehlt", "Der Loader findet eine .so-Datei nicht.", "Unvollständige Installation.", "hoch", "mittel", ("linux",), linux_script="apt-file search {lib} || true"),
    Pattern("missing-dll", r"(?i)((?:[\w.+-]+)\.dll).{0,40}(?:was not found|nicht gefunden|could not be found)", "DLL fehlt", "Windows startet das Programm nicht, weil eine DLL fehlt.", "Laufzeitbibliothek oder unvollständiges Programmverzeichnis.", "hoch", "mittel", ("windows",)),
    Pattern("permission", r"permission denied", "Zugriff verweigert", "Der Benutzer darf die Datei nicht lesen oder schreiben.", "Dateirechte oder eine fehlende Gruppe.", "hoch", "mittel", ("linux", "windows"), linux_script="ls -ld \"<PFAD>\""),
    Pattern("no-such-file", r"no such file or directory", "Datei oder Ordner fehlt", "Ein genannter Pfad existiert nicht.", "Tippfehler oder ein Pfad aus der anderen Welt.", "mittel", "niedrig", ("linux",)),
    Pattern("broken-dpkg", r"unmet dependencies|dpkg: error processing package|you have held broken packages", "Paketabhängigkeiten sind gebrochen", "dpkg kann ein Paket nicht einrichten.", "Abgebrochene Installation.", "hoch", "mittel", ("linux",), linux_script="sudo dpkg --configure -a\nsudo apt-get -f install"),
    Pattern("systemd-failed", r"(?:Failed to start|Unit )([\w.@+-]+\.service)", "Dienst ist fehlgeschlagen", "Eine systemd-Unit ist nicht gestartet.", "Konfigurationsfehler oder eine fehlende Abhängigkeit.", "hoch", "mittel", ("linux",), linux_script="systemctl --user status {unit} --no-pager || systemctl status {unit} --no-pager"),
    Pattern("io-error", r"I/O error|Buffer I/O error", "Datenträger-Lesefehler", "Der Kernel konnte einen Block nicht lesen.", "Fehlerhafter Datenträger oder unsauberes Aushängen.", "hoch", "hoch", ("linux",), linux_script="# sudo fsck -n <GERAET>"),
    Pattern("ntfs-dirty", r"ntfs.*unclean|Volume is dirty|unclean file system", "NTFS wurde nicht sauber ausgehängt", "Linux sollte das Laufwerk nicht nebenbei reparieren, solange Windows-Schnellstart aktiv ist.", "Schnellstart oder ein harter Reset.", "hoch", "hoch", ("linux",), linux_script="# sudo ntfsfix -n <GERAET>"),
    Pattern("oom", r"out of memory|Killed process", "Arbeitsspeicher erschöpft", "Der Kernel hat einen Prozess wegen Speichermangels beendet.", "Zu wenig RAM oder ein Leck.", "hoch", "niedrig", ("linux",)),
)

_COMPILED = tuple((pattern, re.compile(pattern.regex, re.I)) for pattern in PATTERNS)
_ALLOWED_LINE = re.compile(
    r"^(?:ls -ld \"[^\"$;|&`]+\"|sudo dpkg --configure -a|sudo apt-get -f install|"
    r"systemctl --user status [\w.@+-]+\.service --no-pager|systemctl status [\w.@+-]+\.service --no-pager|"
    r"apt-file search [\w.+-]+ \|\| true|Get-ChildItem -Force \$env:USERPROFILE \| Out-Null)$"
)


def analyze(text: str) -> list[dict]:
    findings, seen = [], set()
    for pattern, compiled in _COMPILED:
        match = compiled.search(text)
        if not match or pattern.id in seen:
            continue
        seen.add(pattern.id)
        groups = match.groups()
        linux_script, windows_script = pattern.linux_script, pattern.windows_script
        if pattern.id == "missing-so" and groups:
            linux_script = linux_script.replace("{lib}", groups[0])
        if pattern.id == "systemd-failed" and groups and groups[0]:
            linux_script = linux_script.replace("{unit}", groups[0])
        findings.append({
            "id": pattern.id, "title": pattern.title, "explanation": pattern.explanation,
            "cause": pattern.cause, "severity": pattern.severity, "risk": pattern.risk,
            "worlds": list(pattern.worlds), "match": match.group(0),
            "linux_script": linux_script, "windows_script": windows_script,
            "auto_apply": script_is_allowed(linux_script) if linux_script else False,
        })
    if not findings:
        findings.append({
            "id": "unknown", "title": "Keine bekannte Signatur",
            "explanation": "In diesem Text steckt keines der hinterlegten Muster.",
            "cause": "Zu wenig Kontext oder ein seltenes Ereignis.",
            "severity": "niedrig", "risk": "niedrig", "worlds": [], "match": "",
            "linux_script": "", "windows_script": "", "auto_apply": False,
        })
    return findings


def script_for(finding: dict, world: World) -> str:
    return str(finding.get("windows_script") if world == World.WINDOWS else finding.get("linux_script") or "")


def script_is_allowed(script: str) -> bool:
    lines = [line.strip() for line in script.splitlines() if line.strip() and not line.strip().startswith("#")]
    return bool(lines) and all(_ALLOWED_LINE.match(line) for line in lines)


def lint_user_script(script: str) -> None:
    if not script_is_allowed(script):
        raise ValueError("Skript enthält Zeilen außerhalb der Allowlist und wird nicht ausgeführt")
