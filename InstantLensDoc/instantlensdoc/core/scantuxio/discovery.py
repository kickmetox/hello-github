"""
Erweiterte Geräte-Erkennung: Netzwerk-Drucker/-Scanner per mDNS (Avahi/Bonjour),
rohe USB-Scanner ohne passendes SANE-Backend, sowie einfache Treiber-Vorschläge
mit Nachlade-Möglichkeit (Paketinstallation über pkexec).

Das ergänzt scanner.py (welches nur zeigt, was SANE *bereits* erfolgreich
ansprechen kann) um die Fälle "Gerät ist da, wird aber noch nicht erkannt".
"""
from __future__ import annotations

import getpass
import glob
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field


@dataclass
class NetworkDevice:
    name: str
    service_type: str
    host: str
    address: str
    port: str

    @property
    def kind(self) -> str:
        t = self.service_type.lower()
        if "uscan" in t or "scanner" in t or "escl" in t:
            return "Scanner"
        if "ipp" in t or "printer" in t or "pdl-datastream" in t:
            return "Drucker"
        return "Gerät"


@dataclass
class RawUsbDevice:
    vendor_id: str
    product_id: str
    vendor_name: str
    product_name: str
    usb_path: str
    already_supported: bool = False


@dataclass
class DriverSuggestion:
    package: str | None
    hint: str


# Bekannte Scanner-/MFP-Hersteller (USB-Vendor-ID) und ein sinnvoller erster
# Schritt unter Debian/Ubuntu. Erhebt keinen Anspruch auf Vollständigkeit -
# bei unbekannten Herstellern wird auf die SANE-Projektseite verwiesen.
VENDOR_DRIVER_HINTS: dict[str, DriverSuggestion] = {
    "0x03f0": DriverSuggestion(
        "hplip", "HP-Geräte: HPLIP installieren, stellt das SANE-Backend 'hpaio' bereit."
    ),
    "0x04a9": DriverSuggestion(
        "sane-utils",
        "Canon: wird meist vom 'pixma'-Backend in sane-backends abgedeckt (sane-utils reicht i.d.R. aus).",
    ),
    "0x04b8": DriverSuggestion(
        "sane-utils",
        "Epson: wird meist vom 'epson2'-Backend abgedeckt. Für sehr neue Modelle ggf. "
        "'epsonscan2' direkt vom Hersteller nötig.",
    ),
    "0x04f9": DriverSuggestion(
        None,
        "Brother: benötigt meist das herstellereigene Treiberpaket (brscan4/brscan5) "
        "von support.brother.com - kein offizielles Debian-Paket verfügbar.",
    ),
    "0x055f": DriverSuggestion(
        "sane-utils",
        "Mustek: wird meist von 'mustek'/'mustek_usb'/'mustek_usb2' in sane-backends abgedeckt.",
    ),
    "0x0924": DriverSuggestion(
        "sane-utils", "Xerox: oft baugleich mit Samsung/Fuji-Geräten, meist von SANE abgedeckt."
    ),
    "0x04e8": DriverSuggestion(
        None, "Samsung: ältere MFPs benötigen das inoffizielle 'smfp'-Backend, Support ist eingeschränkt."
    ),
}

_NETWORK_SERVICE_TYPES = (
    "_ipp._tcp",
    "_ipps._tcp",
    "_printer._tcp",
    "_pdl-datastream._tcp",
    "_scanner._tcp",
    "_uscan._tcp",
    "_uscans._tcp",
)


def is_avahi_browse_available() -> bool:
    return shutil.which("avahi-browse") is not None


def is_pkexec_available() -> bool:
    return shutil.which("pkexec") is not None


def current_username() -> str:
    return getpass.getuser()


def is_user_in_scanner_group(username: str | None = None) -> bool:
    username = username or current_username()
    try:
        proc = subprocess.run(["groups", username], capture_output=True, text=True, timeout=5)
    except (subprocess.TimeoutExpired, OSError):
        return True  # im Zweifel nicht mit einem Fehlvorschlag stören
    return "scanner" in proc.stdout.split()


def discover_network_devices(timeout: int = 6) -> list[NetworkDevice]:
    """Sucht per mDNS/Bonjour (Avahi) nach Netzwerk-Druckern und -Scannern.

    Findet auch Geräte, die SANE (noch) nicht automatisch aufgelistet hat,
    z.B. weil der eSCL/WSD-Dienst erst nach dem letzten Neustart hinzukam.
    """
    if not is_avahi_browse_available():
        return []

    devices: list[NetworkDevice] = []
    try:
        proc = subprocess.run(
            ["avahi-browse", "-a", "-r", "-t", "-p"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return devices

    for line in proc.stdout.splitlines():
        if not line.startswith("="):
            continue
        parts = line.split(";")
        if len(parts) < 9:
            continue
        service_type = parts[4]
        if not any(t in service_type for t in _NETWORK_SERVICE_TYPES):
            continue
        name, host, address, port = parts[3], parts[6], parts[7], parts[8]
        devices.append(
            NetworkDevice(name=name, service_type=service_type, host=host, address=address, port=port)
        )

    # Doppelte Einträge (mehrere Netzwerk-Interfaces) zusammenfassen.
    seen = set()
    unique = []
    for dev in devices:
        key = (dev.name, dev.service_type, dev.address)
        if key not in seen:
            seen.add(key)
            unique.append(dev)
    return unique


def is_zeroconf_available() -> bool:
    try:
        import zeroconf  # noqa: F401
    except ImportError:
        return False
    return True


def discover_network_devices_zeroconf(timeout: float = 4.0) -> list[NetworkDevice]:
    """Sucht per mDNS nach Netzwerk-Druckern/-Scannern - wie
    discover_network_devices(), aber über das plattformunabhängige
    'zeroconf'-Paket (reines Python) statt des Linux-only
    'avahi-browse'-Kommandozeilenwerkzeugs. Läuft unverändert unter
    Windows, wo es kein Avahi gibt - ERGÄNZT den bestehenden Avahi-Pfad,
    ersetzt ihn nicht (beide können nebeneinander existieren).

    Liefert dieselbe NetworkDevice-Struktur wie discover_network_devices(),
    damit Aufrufer beide Quellen austauschbar behandeln können."""
    try:
        from zeroconf import Zeroconf, ServiceBrowser, ServiceListener
    except ImportError:
        return []

    found: list[tuple[str, object]] = []

    class _CollectingListener(ServiceListener):
        def add_service(self, zc, service_type, name):
            info = zc.get_service_info(service_type, name)
            if info:
                found.append((service_type, info))

        def update_service(self, zc, service_type, name):
            pass

        def remove_service(self, zc, service_type, name):
            pass

    zc = Zeroconf()
    listener = _CollectingListener()
    browsers = []
    try:
        for service_type in _NETWORK_SERVICE_TYPES:
            mdns_type = f"{service_type}.local."
            browsers.append(ServiceBrowser(zc, mdns_type, listener))
        time.sleep(timeout)
    finally:
        zc.close()

    devices: list[NetworkDevice] = []
    for service_type, info in found:
        addresses = info.parsed_addresses() if hasattr(info, "parsed_addresses") else []
        address = addresses[0] if addresses else ""
        host = (info.server or "").rstrip(".") or address
        name = info.name.split(".")[0] if info.name else host
        port = str(info.port) if info.port else ""
        devices.append(
            NetworkDevice(name=name, service_type=service_type.rstrip("."), host=host,
                          address=address, port=port)
        )

    seen = set()
    unique = []
    for dev in devices:
        key = (dev.name, dev.service_type, dev.address)
        if key not in seen:
            seen.add(key)
            unique.append(dev)
    return unique


_USB_SCANNER_LINE = re.compile(
    r"found USB scanner.*?vendor=(0x[0-9a-fA-F]+)(?:\s*\[([^\]]*)\])?.*?"
    r"product=(0x[0-9a-fA-F]+)(?:\s*\[([^\]]*)\])?.*?\bat\s+(\S+)"
)


def discover_usb_raw(known_device_ids: list[str] | None = None, timeout: int = 20) -> list[RawUsbDevice]:
    """Fragt sane-find-scanner nach roh erkannten USB-Scanner-Chips.

    sane-find-scanner erkennt Vendor/Produkt oft schon anhand der USB-IDs,
    auch wenn (noch) kein passendes SANE-Backend das Gerät ansprechen kann.
    """
    if shutil.which("sane-find-scanner") is None:
        return []
    known_device_ids = known_device_ids or []
    try:
        proc = subprocess.run(
            ["sane-find-scanner", "-q"], capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return []

    results: list[RawUsbDevice] = []
    for line in proc.stdout.splitlines():
        m = _USB_SCANNER_LINE.search(line)
        if not m:
            continue
        vendor_id, vendor_name, product_id, product_name, usb_path = m.groups()
        already = any(usb_path in dev_id for dev_id in known_device_ids)
        results.append(
            RawUsbDevice(
                vendor_id=vendor_id,
                product_id=product_id or "",
                vendor_name=vendor_name or "Unbekannt",
                product_name=product_name or "",
                usb_path=usb_path,
                already_supported=already,
            )
        )
    return results


def suggest_driver(vendor_id: str) -> DriverSuggestion:
    return VENDOR_DRIVER_HINTS.get(
        vendor_id.lower(),
        DriverSuggestion(
            None,
            "Kein bekanntes Standardpaket. Bitte Gerätename auf "
            "sane-project.org/sane-mfgs.html nachschlagen.",
        ),
    )


def install_package(package_name: str, timeout: int = 300) -> str:
    """Installiert ein apt-Paket über pkexec (fragt das System-Passwort über den
    normalen PolicyKit-Dialog des Betriebssystems ab - ScanTuxio sieht das
    Passwort nie)."""
    if not is_pkexec_available():
        raise RuntimeError("'pkexec' ist nicht verfügbar. Bitte Paket manuell installieren:\n"
                            f"sudo apt install {package_name}")
    proc = subprocess.run(
        ["pkexec", "apt-get", "install", "-y", package_name],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "Installation fehlgeschlagen.")
    return proc.stdout.strip()


def add_user_to_scanner_group(username: str | None = None, timeout: int = 60) -> str:
    """Fügt den Benutzer der Gruppe 'scanner' hinzu (für direkten USB-Zugriff)."""
    username = username or current_username()
    if not is_pkexec_available():
        raise RuntimeError(
            "'pkexec' ist nicht verfügbar. Bitte manuell ausführen:\n"
            f"sudo usermod -aG scanner {username}"
        )
    proc = subprocess.run(
        ["pkexec", "usermod", "-aG", "scanner", username],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "Gruppenzuweisung fehlgeschlagen.")
    return f"{username} wurde der Gruppe 'scanner' hinzugefügt. Bitte einmal ab- und wieder anmelden."
