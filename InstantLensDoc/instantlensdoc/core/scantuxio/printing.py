"""Drucken über CUPS (lp/lpstat/lpadmin) unter Linux, über Qts
QtPrintSupport (printing_windows.py) unter Windows - passend zur
restlichen Architektur, die durchgängig auf plattformübliche Werkzeuge
setzt statt eigene Treiber/Backends mitzubringen."""
from __future__ import annotations

import os
import shutil
import subprocess
import webbrowser
from dataclasses import dataclass

from . import platform_utils


class PrintError(RuntimeError):
    pass


@dataclass
class PrinterInfo:
    name: str
    state: str
    is_default: bool = False

    def __str__(self) -> str:
        marker = " (Standard)" if self.is_default else ""
        return f"{self.name}{marker} - {self.state}"


def is_cups_available() -> bool:
    return shutil.which("lpstat") is not None


def is_printing_available() -> bool:
    """True, wenn irgendein Drucker-Backend nutzbar ist - CUPS unter
    Linux, QtPrintSupport unter Windows."""
    if platform_utils.IS_WINDOWS:
        from . import printing_windows
        return printing_windows.is_available()
    return is_cups_available()


def list_printers(timeout: int = 10) -> list[PrinterInfo]:
    if platform_utils.IS_WINDOWS:
        from . import printing_windows
        return printing_windows.list_printers()
    if not is_cups_available():
        return []
    try:
        # LC_ALL=C erzwingt englische lpstat-Ausgabe unabhängig von der
        # Systemsprache - das Parsen unten sucht nach den englischen
        # Text-Mustern ("printer ", "system default destination:") und
        # würde sonst auf lokalisierten Systemen (z.B. deutsch: "Drucker
        # X ist im Leerlauf") stillschweigend keine Drucker finden.
        env = {**os.environ, "LC_ALL": "C"}
        proc = subprocess.run(
            ["lpstat", "-p", "-d"], capture_output=True, text=True, timeout=timeout, env=env
        )
    except subprocess.TimeoutExpired:
        return []

    default_name = None
    printers: list[PrinterInfo] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.startswith("system default destination:"):
            default_name = line.split(":", 1)[1].strip()
        elif line.startswith("printer "):
            parts = line.split()
            name = parts[1] if len(parts) > 1 else "?"
            state = "bereit" if " is idle" in line else ("druckt" if " now printing" in line else "unbekannt")
            printers.append(PrinterInfo(name=name, state=state))

    for p in printers:
        if p.name == default_name:
            p.is_default = True
    return printers


def print_files(
    printer_name: str,
    file_paths: list[str],
    copies: int = 1,
    duplex: bool = False,
    timeout: int = 120,
) -> None:
    if platform_utils.IS_WINDOWS:
        from . import printing_windows
        printing_windows.print_files(printer_name, file_paths, copies, duplex, timeout)
        return
    if not is_cups_available():
        raise PrintError("CUPS ('lp') wurde nicht gefunden. Bitte 'cups-client' installieren.")
    if not file_paths:
        raise PrintError("Keine Datei zum Drucken übergeben.")

    sides = "two-sided-long-edge" if duplex else "one-sided"
    args = ["lp", "-d", printer_name, "-n", str(max(1, copies)), "-o", f"sides={sides}"]
    args += file_paths

    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise PrintError("Zeitüberschreitung beim Drucken.") from exc
    if proc.returncode != 0:
        raise PrintError(proc.stderr.strip() or proc.stdout.strip() or "Drucken fehlgeschlagen.")


def add_network_printer(name: str, device_uri: str, timeout: int = 60) -> str:
    """Richtet einen im Netzwerk gefundenen IPP-Drucker treiberlos in CUPS ein
    (IPP-Everywhere, benötigt keinen herstellerspezifischen Treiber)."""
    if shutil.which("pkexec") is None:
        raise PrintError(
            "'pkexec' ist nicht verfügbar. Bitte manuell einrichten:\n"
            f"sudo lpadmin -p {name} -E -v {device_uri} -m everywhere"
        )
    safe_name = "".join(c if c.isalnum() else "_" for c in name) or "Netzwerkdrucker"
    proc = subprocess.run(
        ["pkexec", "lpadmin", "-p", safe_name, "-E", "-v", device_uri, "-m", "everywhere"],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise PrintError(proc.stderr.strip() or "Drucker-Einrichtung fehlgeschlagen.")
    return f"Drucker '{safe_name}' wurde eingerichtet."


def open_cups_admin() -> None:
    webbrowser.open("http://localhost:631")
