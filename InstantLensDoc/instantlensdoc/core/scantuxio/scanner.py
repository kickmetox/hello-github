"""
Scanner-Anbindung über SANE (scanimage-Kommandozeilenwerkzeug).

SANE ist die Standard-Scanner-Schicht unter Linux und bringt bereits
Backends für hunderte Geräte mit - von sehr alten USB/Parallel-Scannern
(z.B. genesys, plustek, mustek, canon, epson2 ...) bis zu modernen
Netzwerk-Scannern per eSCL/WSD (sane-airscan) und HP-Multifunktionsgeräten
(hpaio). Dadurch muss ScanTuxio keine Geräte-Treiber selbst mitbringen -
alles was `scanimage -L` findet, kann direkt benutzt werden.
"""
from __future__ import annotations

import re
import shutil
import ssl
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Optional


class ScannerError(RuntimeError):
    """Wird bei Problemen mit scanimage/SANE ausgelöst."""


@dataclass
class ScannerDevice:
    device_id: str
    description: str

    def __str__(self) -> str:
        return self.description


@dataclass
class DeviceOption:
    name: str
    kind: str  # "choice" | "range" | "bool"
    choices: list = field(default_factory=list)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    unit: str = ""
    default: Optional[str] = None


# Meldungen, die scanimage im Batch-Modus ausgibt, wenn der automatische
# Einzug (ADF) leer ist - das ist das erwartete Ende eines Stapel-Scans,
# kein echter Fehler.
_ADF_EMPTY_PATTERNS = (
    "document feeder out of documents",
    "out of paper",
    "no documents",
    "feeder empty",
)


def is_scanimage_available() -> bool:
    return shutil.which("scanimage") is not None


def list_devices(timeout: int = 20) -> list[ScannerDevice]:
    """Fragt SANE nach allen aktuell erreichbaren Scannern (USB & Netzwerk)."""
    if not is_scanimage_available():
        raise ScannerError(
            "Das Kommandozeilenwerkzeug 'scanimage' wurde nicht gefunden. "
            "Bitte 'sane-utils' installieren."
        )
    try:
        proc = subprocess.run(
            ["scanimage", "-L"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise ScannerError("Zeitüberschreitung beim Suchen nach Scannern.") from exc

    devices: list[ScannerDevice] = []
    # Beispielzeile:
    # device `escl:https://192.168.1.5:9096' is a ESCL Kyocera ECOSYS M5521cdn platen,adf scanner
    pattern = re.compile(r"device `([^']+)' is a (.+)$")
    for line in proc.stdout.splitlines():
        m = pattern.search(line)
        if m:
            devices.append(ScannerDevice(device_id=m.group(1), description=m.group(2).strip()))
    return devices


_OPTION_LINE = re.compile(r"^\s{2,}--([A-Za-z0-9][A-Za-z0-9\-]*)\s+(.*)$")
_DEFAULT_SUFFIX = re.compile(r"\[([^\]]*)\]\s*$")
_UNIT_SUFFIX = re.compile(r"(dpi|mm|pel|bit)\b")


def get_device_options(device_id: str, timeout: int = 20) -> dict[str, DeviceOption]:
    """Liest die von einem konkreten Gerät unterstützten Optionen aus.

    Die Ausgabe von `scanimage --help -d <device>` unterscheidet sich stark
    zwischen den SANE-Backends, daher wird hier bewusst tolerant geparst:
    was nicht verstanden wird, wird einfach ignoriert und es bleiben die
    eingebauten Vorgaben aktiv.
    """
    options: dict[str, DeviceOption] = {}
    try:
        proc = subprocess.run(
            ["scanimage", "--help", "-d", device_id],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return options

    text = proc.stdout + "\n" + proc.stderr
    for raw_line in text.splitlines():
        m = _OPTION_LINE.match(raw_line)
        if not m:
            continue
        name, rest = m.group(1), m.group(2)

        default = None
        dm = _DEFAULT_SUFFIX.search(rest)
        if dm:
            default = dm.group(1).strip()
            rest = rest[: dm.start()].strip()

        if rest.startswith("[=(yes|no)]") or rest.lower().startswith("(yes|no)"):
            options[name] = DeviceOption(name=name, kind="bool", default=default)
            continue

        unit = ""
        um = _UNIT_SUFFIX.search(rest)
        if um:
            unit = um.group(1)

        if ".." in rest:
            range_part = rest.split()[0] if rest.split() else rest
            range_part = _UNIT_SUFFIX.sub("", range_part)
            bounds = range_part.split("..")
            try:
                lo = float(re.sub(r"[^0-9.\-]", "", bounds[0]))
                hi = float(re.sub(r"[^0-9.\-]", "", bounds[1]))
                options[name] = DeviceOption(
                    name=name, kind="range", min_value=lo, max_value=hi, unit=unit, default=default
                )
            except (ValueError, IndexError):
                pass
            continue

        if "|" in rest:
            value_part = rest.split()[0] if rest.split() else rest
            value_part = _UNIT_SUFFIX.sub("", value_part)
            choices = [c for c in value_part.split("|") if c]
            if choices:
                options[name] = DeviceOption(
                    name=name, kind="choice", choices=choices, unit=unit, default=default
                )
            continue

    return options


def _build_common_args(
    device_id: str,
    mode: Optional[str],
    resolution: Optional[str],
    source: Optional[str],
    available_options: Optional[dict[str, DeviceOption]] = None,
) -> list[str]:
    args = ["-d", device_id]
    available = set(available_options.keys()) if available_options else None

    def supported(opt: str) -> bool:
        return available is None or opt in available

    if mode and supported("mode"):
        args += ["--mode", mode]
    if resolution and supported("resolution"):
        res_value = str(resolution).replace("dpi", "")
        args += ["--resolution", res_value]
    if source and supported("source"):
        args += ["--source", source]
    return args


def scan_single_page(
    device_id: str,
    out_path: str,
    mode: str = "Color",
    resolution: str = "300",
    source: Optional[str] = None,
    available_options: Optional[dict[str, DeviceOption]] = None,
    timeout: int = 180,
) -> str:
    """Scannt eine einzelne Seite (Flachbett oder ein ADF-Blatt) nach out_path (PNG)."""
    if not is_scanimage_available():
        raise ScannerError("'scanimage' wurde nicht gefunden. Bitte 'sane-utils' installieren.")

    args = ["scanimage", "--format=png"]
    args += _build_common_args(device_id, mode, resolution, source, available_options)
    args += ["-o", out_path]

    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise ScannerError("Zeitüberschreitung beim Scannen. Ist der Scanner bereit?") from exc

    if proc.returncode != 0:
        raise ScannerError(_friendly_error(proc.stderr))
    return out_path


def scan_batch_adf(
    device_id: str,
    out_dir: str,
    mode: str = "Color",
    resolution: str = "300",
    source: Optional[str] = None,
    available_options: Optional[dict[str, DeviceOption]] = None,
    timeout: int = 600,
) -> list[str]:
    """Scannt so lange Seiten aus dem automatischen Einzug (ADF), bis dieser leer ist."""
    if not is_scanimage_available():
        raise ScannerError("'scanimage' wurde nicht gefunden. Bitte 'sane-utils' installieren.")

    pattern = out_dir.rstrip("/") + "/page-%03d.png"
    args = ["scanimage", "--format=png", f"--batch={pattern}", "--batch-count=-1"]
    args += _build_common_args(device_id, mode, resolution, source, available_options)

    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise ScannerError("Zeitüberschreitung beim Stapel-Scan.") from exc

    import glob

    produced = sorted(glob.glob(out_dir.rstrip("/") + "/page-*.png"))

    if proc.returncode != 0 and not produced:
        stderr_lower = proc.stderr.lower()
        if not any(p in stderr_lower for p in _ADF_EMPTY_PATTERNS):
            raise ScannerError(_friendly_error(proc.stderr))
    return produced


def _friendly_error(stderr: str) -> str:
    text = stderr.strip() or "Unbekannter Scanner-Fehler."
    lower = text.lower()
    if "access denied" in lower or "permission" in lower:
        return (
            "Zugriff auf den Scanner verweigert. Unter Linux muss der Benutzer meist "
            "Mitglied der Gruppe 'scanner' sein (sudo usermod -aG scanner $USER, danach "
            "neu anmelden).\n\nDetails: " + text
        )
    if "no such file or directory" in lower or "invalid argument" in lower and "device" in lower:
        return "Scanner nicht gefunden oder nicht erreichbar.\n\nDetails: " + text
    return text


# ---------------------------------------------------------------------------
# Manuelle Netzwerk-Scanner (für gemeinsame Bürorechner)
#
# mDNS/Bonjour-Auto-Erkennung funktioniert oft nicht zuverlässig in größeren
# Firmennetzwerken (kein Multicast über Subnetz-/VLAN-Grenzen hinweg). Für
# diesen Fall lässt sich ein eSCL-Netzwerk-Scanner auch direkt per
# IP/Hostname konfigurieren - die daraus gebaute Geräte-ID versteht
# `scanimage` genauso wie eine automatisch gefundene.
# ---------------------------------------------------------------------------

def build_escl_device_id(host: str, port: str, use_https: bool = True) -> str:
    scheme = "https" if use_https else "http"
    return f"escl:{scheme}://{host}:{port}"


def escl_ssl_context() -> ssl.SSLContext:
    """TLS-Kontext für eSCL-Geräte: Verifikation bewusst deaktiviert, da
    Multifunktionsgeräte fast immer ein selbstsigniertes Zertifikat
    mitbringen. Gemeinsam genutzt von test_escl_connection() (hier) und
    dem nativen eSCL-Scan-Client (scanner_escl.py)."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def escl_auth_header(username: str | None, password: str | None) -> dict:
    """Baut den HTTP-Basic-Auth-Header, falls ein Benutzername angegeben
    ist - sonst ein leeres dict (keine Authentifizierung)."""
    if not username:
        return {}
    import base64
    token = base64.b64encode(f"{username}:{password or ''}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def test_escl_connection(
    host: str,
    port: str,
    use_https: bool = True,
    timeout: int = 6,
    username: str | None = None,
    password: str | None = None,
) -> tuple[bool, str]:
    """Prüft per HTTP(S)-Anfrage, ob unter der angegebenen Adresse ein
    eSCL-Scanner antwortet - unabhängig von SANE/mDNS, daher auch über
    Subnetz-Grenzen hinweg nutzbar, solange die Adresse erreichbar ist.

    Mit username/password wird HTTP-Basic-Auth mitgeschickt - nützlich, um
    zu prüfen, ob hinterlegte Zugangsdaten stimmen. Das sagt aber nichts
    darüber aus, ob `scanimage` selbst eSCL-Authentifizierung unterstützt -
    das tut der Standard-eSCL-Backend derzeit i.d.R. nicht."""
    scheme = "https" if use_https else "http"
    url = f"{scheme}://{host}:{port}/eSCL/ScannerCapabilities"
    ctx = escl_ssl_context()
    request = urllib.request.Request(url)
    for key, value in escl_auth_header(username, password).items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=ctx if use_https else None) as resp:
            body = resp.read(2000).decode("utf-8", errors="replace")
            if resp.status == 200 and "ScannerCapabilities" in body:
                model = re.search(r"<pwg:MakeAndModel>([^<]*)</pwg:MakeAndModel>", body)
                name = model.group(1) if model else "Gerät"
                return True, f"Verbunden: {name}"
            return False, f"Unerwartete Antwort (HTTP {resp.status})."
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            return False, "Anmeldung erforderlich - Benutzername/Passwort falsch oder fehlend."
        return False, f"HTTP-Fehler {exc.code} - ist das ein eSCL-Scanner auf diesem Port?"
    except urllib.error.URLError as exc:
        return False, f"Nicht erreichbar: {exc.reason}"
    except (TimeoutError, OSError) as exc:
        return False, f"Zeitüberschreitung/Fehler: {exc}"


# ---------------------------------------------------------------------------
# Dispatcher: leitet je nach device_id-Präfix an das passende Backend weiter.
#
# Bestehende SANE-device_id-Strings (kein bekannter Präfix, z.B. "escl:...",
# "pixma:...") laufen unverändert über die Funktionen oben in dieser Datei.
# Neue Präfixe für zusätzliche Backends:
#   "native-escl:" -> scanner_escl.py (reines Python, Linux + Windows)
#   "naps2:"       -> scanner_naps2.py (Windows, WIA/TWAIN über NAPS2.Console.exe)
# Fehlt ein optionales Backend-Modul/Paket (z.B. unter Linux kein NAPS2),
# wird das defensiv abgefangen statt die ganze Geräteliste crashen zu lassen.
# ---------------------------------------------------------------------------

from . import scanner_escl as _escl  # noqa: E402
from . import platform_utils as _platform_utils  # noqa: E402


def _discover_native_escl_devices() -> list[ScannerDevice]:
    """Windows-Ersatz für die automatische Netzwerk-Scanner-Erkennung, die
    unter Linux SANE selbst übernimmt (sane-airscan macht dort intern schon
    eigenes mDNS-Browsing - deshalb findet die Linux-Version Netzwerk-
    Scanner automatisch, "mit Bravour"). Unter Windows gibt es kein SANE,
    also übernimmt hier dieselbe zeroconf-Suche, die schon der
    Treiber-Assistent für die Anzeige nutzt (discovery.py) - bisher wurde
    ihr Ergebnis dort aber nur als Info-Text angezeigt, nie tatsächlich als
    nutzbares Gerät in die Scanner-Liste übernommen. Nur unter Windows
    aktiv: unter Linux würde dasselbe Gerät sonst doppelt erscheinen (einmal
    über SANE mit `escl:`-Präfix, einmal hierüber mit `native-escl:`)."""
    if not _platform_utils.IS_WINDOWS:
        return []
    try:
        from . import discovery as _discovery
    except ImportError:
        return []

    # Geräte, die sowohl _uscan._tcp (http) als auch _uscans._tcp (https)
    # melden (wie der Kyocera des Testrechners), sollen nur EINMAL in der
    # Liste erscheinen, nicht als zwei optisch identische Einträge -
    # bevorzugt die verschlüsselte Variante, falls beide gefunden werden.
    by_address: dict[str, tuple[bool, ScannerDevice]] = {}
    for net_dev in _discovery.discover_network_devices_zeroconf():
        if net_dev.kind != "Scanner":
            continue
        host = net_dev.address or net_dev.host
        if not host or not net_dev.port:
            continue
        use_https = "uscans" in net_dev.service_type.lower()
        device_id = _escl.build_device_id(host, net_dev.port, use_https=use_https)
        device = ScannerDevice(device_id=device_id, description=f"{net_dev.name} (Netzwerk, eSCL)")
        existing = by_address.get(host)
        if existing is None or (use_https and not existing[0]):
            by_address[host] = (use_https, device)
    return [device for _, device in by_address.values()]


def list_devices_all(timeout: int = 20) -> list[ScannerDevice]:
    """Aggregiert Geräte aus allen verfügbaren Backends. Ein fehlendes/
    nicht anwendbares Backend (z.B. kein `scanimage` unter Windows) liefert
    einfach keine Geräte, statt die Suche für die anderen Backends zu
    verhindern."""
    devices: list[ScannerDevice] = []
    try:
        devices.extend(list_devices(timeout=timeout))
    except ScannerError:
        pass

    try:
        from . import scanner_naps2 as _naps2
        devices.extend(_naps2.list_devices(timeout=timeout))
    except ImportError:
        pass
    except ScannerError:
        pass

    try:
        devices.extend(_discover_native_escl_devices())
    except Exception:
        pass

    return devices


def get_device_options_dispatch(
    device_id: str,
    timeout: int = 20,
    username: str | None = None,
    password: str | None = None,
) -> dict[str, DeviceOption]:
    if device_id.startswith(_escl.DEVICE_PREFIX):
        return _escl.get_device_options(device_id, username, password, timeout=timeout)
    if device_id.startswith("naps2:"):
        try:
            from . import scanner_naps2 as _naps2
        except ImportError:
            return {}
        return _naps2.get_device_options(device_id, timeout=timeout)
    return get_device_options(device_id, timeout=timeout)


def scan_single_page_dispatch(
    device_id: str,
    out_path: str,
    mode: str = "Color",
    resolution: str = "300",
    source: Optional[str] = None,
    available_options: Optional[dict[str, DeviceOption]] = None,
    timeout: Optional[int] = None,
    username: str | None = None,
    password: str | None = None,
) -> str:
    """timeout=None lässt jedes Backend seinen eigenen, dafür passenden
    Vorgabewert verwenden (SANE: 180s: eSCL: ebenfalls 180s, siehe
    scanner_escl.py - reale Geräte können bei höherer Auflösung durchaus
    30-90s pro Seite brauchen)."""
    kwargs = {} if timeout is None else {"timeout": timeout}
    if device_id.startswith(_escl.DEVICE_PREFIX):
        return _escl.scan_single_page(
            device_id, out_path, mode, resolution, source, available_options,
            username=username, password=password, **kwargs,
        )
    if device_id.startswith("naps2:"):
        from . import scanner_naps2 as _naps2
        return _naps2.scan_single_page(device_id, out_path, mode, resolution, source, **kwargs)
    return scan_single_page(device_id, out_path, mode, resolution, source, available_options, **kwargs)


def scan_batch_adf_dispatch(
    device_id: str,
    out_dir: str,
    mode: str = "Color",
    resolution: str = "300",
    source: Optional[str] = None,
    available_options: Optional[dict[str, DeviceOption]] = None,
    timeout: Optional[int] = None,
    username: str | None = None,
    password: str | None = None,
) -> list[str]:
    """timeout=None lässt jedes Backend seinen eigenen Vorgabewert
    verwenden (SANE: 600s für den GANZEN Stapel; eSCL: 90s PRO Seite,
    siehe scanner_escl.py - unterschiedliche Semantik, deshalb kein
    gemeinsamer Default hier)."""
    kwargs = {} if timeout is None else {"timeout": timeout}
    if device_id.startswith(_escl.DEVICE_PREFIX):
        return _escl.scan_batch_adf(
            device_id, out_dir, mode, resolution, source, available_options,
            username=username, password=password, **kwargs,
        )
    if device_id.startswith("naps2:"):
        from . import scanner_naps2 as _naps2
        return _naps2.scan_batch_adf(device_id, out_dir, mode, resolution, source, **kwargs)
    return scan_batch_adf(device_id, out_dir, mode, resolution, source, available_options, **kwargs)
