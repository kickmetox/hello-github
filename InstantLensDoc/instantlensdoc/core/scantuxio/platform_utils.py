"""Plattform-Erkennung und Hilfsfunktionen, die von den Linux- und
Windows-Implementierungen gemeinsam genutzt werden."""
from __future__ import annotations

import hashlib
import os
import platform
import shutil
import subprocess
import sys
import uuid

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"


def get_machine_id() -> str:
    """Liefert eine stabile, halbwegs eindeutige Kennung für diesen Rechner
    (für die Lizenzaktivierung - kein Tracking, verlässt nie diesen Rechner
    außer wenn der Nutzer sie selbst zur Aktivierung weitergibt)."""
    raw = None
    if IS_LINUX:
        for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        raw = content
                        break
            except OSError:
                continue
    elif IS_WINDOWS:
        try:
            result = subprocess.run(
                ["reg", "query", r"HKLM\SOFTWARE\Microsoft\Cryptography", "/v", "MachineGuid"],
                capture_output=True, text=True, timeout=5, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            for line in result.stdout.splitlines():
                if "MachineGuid" in line:
                    raw = line.strip().split()[-1]
                    break
        except (OSError, subprocess.SubprocessError):
            raw = None
    if not raw:
        raw = str(uuid.getnode())
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()
    return digest[:20]


def find_executable(*names: str, extra_dirs: list[str] | None = None, max_depth: int = 3) -> str | None:
    r"""Sucht eine ausführbare Datei: zuerst im PATH (mehrere Namen probieren,
    z.B. 'gs' und 'gswin64c'), danach in zusätzlich angegebenen Verzeichnissen
    (z.B. typische Windows-Installationspfade außerhalb des PATH).

    Steigt dabei bis zu `max_depth` Unterordner-Ebenen ab, da reale Windows-
    Installationen die eigentliche .exe oft mehrere Ebenen tief unter
    "Program Files" ablegen, mit versionsabhängigem Zwischenordner, der
    sich nicht fest verdrahten lässt - z.B. `Tesseract-OCR\tesseract.exe`
    (1 Ebene), `LibreOffice\program\soffice.exe` (2 Ebenen),
    `gs\gs10.03.1\bin\gswin64c.exe` (3 Ebenen, Versionsnummer im Pfad)."""
    for name in names:
        found = shutil.which(name)
        if found:
            return found

    candidate_names = list(names)
    if IS_WINDOWS:
        candidate_names += [n + ".exe" for n in names if not n.lower().endswith(".exe")]

    for directory in extra_dirs or []:
        if not os.path.isdir(directory):
            continue
        base_depth = directory.rstrip(os.sep).count(os.sep)
        for root, dirs, files in os.walk(directory):
            depth = root.rstrip(os.sep).count(os.sep) - base_depth
            for name in candidate_names:
                if name in files:
                    return os.path.join(root, name)
            if depth >= max_depth:
                dirs[:] = []  # nicht tiefer absteigen - vermeidet lange Suchen
    return None


def windows_program_files_dirs() -> list[str]:
    """Typische Windows-Installationsordner, in denen Ghostscript, Tesseract,
    LibreOffice & Co. landen, falls sie nicht im PATH eingetragen wurden."""
    if not IS_WINDOWS:
        return []
    dirs = []
    for env_var in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
        base = os.environ.get(env_var)
        if base:
            dirs.append(base)
    return dirs


def install_hint(linux_package: str, windows_hint: str) -> str:
    """Baut einen plattformgerechten Installationshinweis für eine fehlende
    externe Abhängigkeit (Tesseract/Ghostscript/poppler/LibreOffice/...).
    Unter Linux reicht der apt-Paketname ("Bitte 'X' installieren."); unter
    Windows gibt es kein apt - "Bitte poppler-utils installieren" wäre dort
    schlicht falsch/irreführend. Stattdessen ein Hinweis auf den offiziellen
    Windows-Installer (siehe README, Abschnitt "Setup auf einer frischen
    Windows-Maschine")."""
    if IS_WINDOWS:
        return windows_hint
    return f"Bitte '{linux_package}' installieren."


def bundled_tool_dir(name: str) -> str | None:
    """Ordner einer vom Installer mitgelieferten Fremd-Laufzeit (z.B.
    'tesseract'): bei der eingefrorenen .exe neben ScanTuxio.exe, im
    Quellcode-Betrieb unter <Projekt>/vendor/<name>. None, wenn nicht
    vorhanden - dann greift die normale Suche im PATH/Program Files."""
    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(os.path.join(os.path.dirname(os.path.abspath(sys.executable)), name))
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates.append(os.path.join(project_root, "vendor", name))
    for path in candidates:
        if os.path.isdir(path):
            return path
    return None


def hidden_console_kwargs() -> dict:
    """subprocess-Argumente, damit die fensterlose GUI-App unter Windows beim
    Starten von Kommandozeilenwerkzeugen (tesseract, ghostscript, ...) keine
    kurz aufblitzenden Konsolenfenster oeffnet."""
    if IS_WINDOWS:
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    return {}
