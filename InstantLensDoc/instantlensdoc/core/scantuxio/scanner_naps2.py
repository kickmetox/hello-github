"""Windows-USB-/Lokal-Scanner über WIA und TWAIN - durch Shellen von
NAPS2.Console.exe (aktiv gepflegtes Open-Source-Tool), statt eigener
COM/WIA- bzw. TWAIN-DSM-Bindungen. Deckt beide Treiberarten über ein
einziges, bewährtes Werkzeug ab - passt zum bestehenden ScanTuxio-Muster,
externe Tools zu shellen (scanimage/lp), statt Treiber-Protokolle selbst
zu implementieren.

***WICHTIG - UNGETESTET***: Kein Zugriff auf eine echte Windows-Maschine
mit angeschlossenem WIA-/TWAIN-Scanner. Geschrieben nach der öffentlich
dokumentierten NAPS2.Console-Kommandozeile, bewusst konservativ (nur die
Flags verwendet, die in der NAPS2-Dokumentation eindeutig belegt sind:
-o, --driver, --device, --dpi, --source, --listdevices). Vor dem
produktiven Einsatz UNBEDINGT gegen die tatsächlich installierte
NAPS2-Version prüfen (`NAPS2.Console.exe --help`), da sich CLI-Flags
zwischen Versionen ändern können - siehe docs/windows-port-status.md für
die konkrete Test-Checkliste.

Farbmodus (SANE-Vokabular Color/Gray/Lineart) wird bewusst NICHT an NAPS2
durchgereicht, da keine verlässlich dokumentierte CLI-Option dafür
gefunden wurde - NAPS2 nutzt in diesem Fall seine eigene Profil-/
Geräte-Vorgabe. Das müsste bei Bedarf nach einem Blick in die reale
--help-Ausgabe nachgerüstet werden.

Distribution: NAPS2 muss auf dem Zielrechner installiert sein (oder die
portable Variante mitverteilt werden) - siehe docs/windows-port-status.md.
"""
from __future__ import annotations

import os
import subprocess

from .scanner import ScannerError, ScannerDevice, DeviceOption
from . import platform_utils

DEVICE_PREFIX = "naps2:"

_ADF_SOURCE_VALUES = {"ADF", "ADF Duplex"}


def _naps2_console_path() -> str | None:
    """Sucht NAPS2.Console.exe im PATH oder unter Program Files\\NAPS2\\."""
    return platform_utils.find_executable(
        "NAPS2.Console.exe", "NAPS2.Console",
        extra_dirs=platform_utils.windows_program_files_dirs(),
    )


def is_available() -> bool:
    return _naps2_console_path() is not None


def build_device_id(driver: str, name: str) -> str:
    return f"{DEVICE_PREFIX}{driver}:{name}"


def _parse_device_id(device_id: str) -> tuple[str, str]:
    rest = device_id[len(DEVICE_PREFIX):]
    driver, _, name = rest.partition(":")
    return driver, name


def _source_arg(source: str | None) -> str:
    if source == "ADF Duplex":
        return "Duplex"
    if source == "ADF":
        return "Feeder"
    return "Glass"


def list_devices(timeout: int = 20) -> list[ScannerDevice]:
    """Listet WIA- UND TWAIN-Geräte über 'NAPS2.Console --listdevices'.
    Gibt eine leere Liste zurück, falls NAPS2 nicht installiert ist -
    kein Fehler, damit die Aggregation in scanner.list_devices_all()
    nicht daran scheitert."""
    exe = _naps2_console_path()
    if not exe:
        return []
    devices: list[ScannerDevice] = []
    for driver in ("wia", "twain"):
        try:
            proc = subprocess.run(
                [exe, "--listdevices", "--driver", driver],
                capture_output=True, text=True, timeout=timeout,
                **platform_utils.hidden_console_kwargs(),
            )
        except subprocess.TimeoutExpired:
            continue
        for line in proc.stdout.splitlines():
            name = line.strip()
            if not name:
                continue
            device_id = build_device_id(driver, name)
            devices.append(ScannerDevice(device_id=device_id, description=f"{name} ({driver.upper()})"))
    return devices


def get_device_options(device_id: str, timeout: int = 10) -> dict[str, DeviceOption]:
    """NAPS2 --listdevices liefert keine unterstützten Auflösungen/Modi -
    die UI fällt auf ihre eingebauten Vorgaben zurück (siehe
    FALLBACK_RESOLUTIONS/FALLBACK_SOURCE_ITEMS in main_window.py)."""
    return {}


def scan_single_page(
    device_id: str,
    out_path: str,
    mode: str = "Color",
    resolution: str = "300",
    source: str | None = None,
    timeout: int = 180,
) -> str:
    exe = _naps2_console_path()
    if not exe:
        raise ScannerError("NAPS2.Console.exe wurde nicht gefunden. Bitte NAPS2 installieren.")
    driver, name = _parse_device_id(device_id)
    res_value = str(resolution).replace("dpi", "")
    args = [
        exe, "-o", out_path,
        "--driver", driver, "--device", name,
        "--dpi", res_value,
        "--source", _source_arg(source),
    ]
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            **platform_utils.hidden_console_kwargs(),
        )
    except subprocess.TimeoutExpired as exc:
        raise ScannerError("Zeitüberschreitung beim Scannen (NAPS2).") from exc
    if proc.returncode != 0 or not os.path.exists(out_path):
        raise ScannerError(proc.stderr.strip() or "NAPS2-Scan fehlgeschlagen.")
    return out_path


def scan_batch_adf(
    device_id: str,
    out_dir: str,
    mode: str = "Color",
    resolution: str = "300",
    source: str | None = None,
    timeout: int = 600,
) -> list[str]:
    """Scannt den kompletten ADF-Stapel als EINE mehrseitige TIFF-Datei -
    NAPS2 übernimmt dabei selbst die Erkennung von 'Einzug leer' (Details
    dazu nicht verifizierbar ohne echte Hardware). Die TIFF-Datei wird
    danach mit PIL (bereits Abhängigkeit, keine neue nötig) in einzelne
    Seitenbilder zerlegt, da der Rest von ScanTuxio - wie beim SANE-
    Batch-Scan - eine Liste einzelner Seitendateien erwartet."""
    exe = _naps2_console_path()
    if not exe:
        raise ScannerError("NAPS2.Console.exe wurde nicht gefunden. Bitte NAPS2 installieren.")
    driver, name = _parse_device_id(device_id)
    res_value = str(resolution).replace("dpi", "")

    combined_path = os.path.join(out_dir, "_naps2_batch.tiff")
    args = [
        exe, "-o", combined_path,
        "--driver", driver, "--device", name,
        "--dpi", res_value,
        "--source", "Duplex" if source == "ADF Duplex" else "Feeder",
    ]
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            **platform_utils.hidden_console_kwargs(),
        )
    except subprocess.TimeoutExpired as exc:
        raise ScannerError("Zeitüberschreitung beim Stapel-Scan (NAPS2).") from exc
    if proc.returncode != 0 or not os.path.exists(combined_path):
        # Leerer Einzug wird von NAPS2 vermutlich als Fehler/leere Ausgabe
        # gemeldet (nicht verifiziert) - als leerer Stapel behandelt statt
        # als harter Fehler, analog zum SANE-Pfad (_ADF_EMPTY_PATTERNS).
        return []

    from PIL import Image
    produced: list[str] = []
    with Image.open(combined_path) as img:
        page_num = 0
        while True:
            try:
                img.seek(page_num)
            except EOFError:
                break
            page_path = os.path.join(out_dir, f"page-{page_num + 1:03d}.png")
            img.convert("RGB").save(page_path)
            produced.append(page_path)
            page_num += 1
    try:
        os.remove(combined_path)
    except OSError:
        pass
    return produced
