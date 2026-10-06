"""Lokale und Netzwerk-Drucker-/Scanner-Erkennung — 2.6.2 / 2.6.38 / 2.6.41.

Windows: Systemdrucker (Qt / Winspool / Get-Printer / win32print / ScanTuxio-Qt),
Scanner via **ScanTuxio**-Backends (NAPS2 WIA/TWAIN, native-eSCL/zeroconf)
plus WIA/PnP/TWAIN-Registry-Fallback.
Linux/macOS: Qt-Drucker; Scanner ueber SANE (`scanimage -L`) + ScanTuxio-SANE.
Netzwerk: mDNS/zeroconf (ScanTuxio discovery) · Qt ``isRemote`` · UNC/PnP.

Primaerquelle: vendored ``instantlensdoc.core.scantuxio`` (Upload
``docs/ScanTuxio-Win``).
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, List, Optional, Sequence, Tuple

from instantlensdoc.core.device_io import DISCOVERY_STEP_TIMEOUT_S


class DeviceKind(str, Enum):
    PRINTER = "printer"
    SCANNER = "scanner"


class DeviceScope(str, Enum):
    LOCAL = "local"
    NETWORK = "network"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DeviceInfo:
    """Ein erkanntes Druck- oder Scangerät."""

    kind: DeviceKind
    name: str
    device_id: str = ""
    scope: DeviceScope = DeviceScope.UNKNOWN
    backend: str = ""
    details: str = ""

    def label(self) -> str:
        scope = {
            DeviceScope.LOCAL: "lokal",
            DeviceScope.NETWORK: "Netzwerk",
            DeviceScope.UNKNOWN: "?",
        }.get(self.scope, "?")
        kind = "Drucker" if self.kind == DeviceKind.PRINTER else "Scanner"
        base = f"{self.name} [{kind} · {scope}]"
        if self.backend:
            return f"{base} · {self.backend}"
        return base


@dataclass
class DeviceDiscoveryResult:
    printers: List[DeviceInfo] = field(default_factory=list)
    scanners: List[DeviceInfo] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    backend_notes: List[str] = field(default_factory=list)

    @property
    def all_devices(self) -> List[DeviceInfo]:
        return list(self.printers) + list(self.scanners)


# Klare DE-Hinweise wenn Treiber / Backends fehlen
WINDOWS_SCAN_DEPS_HINT = (
    "Windows Scan/OCR:\n"
    "  • Tesseract: ScanTuxio-Runtime (vendor\\tesseract oder "
    "D:\\AI_Temp\\ScanTuxio Win\\tesseract\\tesseract.exe)\n"
    "  • Fallback: winget install UB-Mannheim.TesseractOCR (deu+eng)\n"
    "  • Python: pip install pytesseract\n"
    "  • Scanner: WIA-Treiber des Herstellers (TWAIN optional)\n"
    "  • Drucker: Windows-Druckerwarteschlange / Get-Printer\n"
    "  • Ohne Scanner-Hardware: Bilder/Fotos im Scan-Dialog importieren"
)

WINDOWS_PRINTER_DRIVER_HINT_DE = (
    "Keine Drucker erkannt. Bitte pruefen:\n"
    "  • Windows-Einstellungen → Bluetooth und Geraete → Drucker und Scanner\n"
    "  • Netzwerkdrucker verbinden (\\\\Server\\Freigabe oder IPP)\n"
    "  • PowerShell: Get-Printer\n"
    "  • Treiber des Herstellers installieren"
)

WINDOWS_SCANNER_DRIVER_HINT_DE = (
    "Keine Scanner erkannt. Bitte pruefen:\n"
    "  • WIA-Treiber des Scanners (Windows-Geraetemanager → Bildverarbeitungsgeraete)\n"
    "  • Optional: TWAIN-Datenquelle des Herstellers\n"
    "  • Optional: NAPS2 installieren (NAPS2.Console --listdevices)\n"
    "  • PowerShell: Get-PnpDevice -Class Image\n"
    "  • Ohne Hardware: im Scan-Dialog „Bilder importieren…“ nutzen"
)

# Offensichtliche UI-Einstiege (DE) — Statusleiste / Dialog / Hilfe — 2.6.41 / 2.6.54 / 2.6.57
SCAN_START_HINT_DE = (
    "Scannen: Menü Geräte → Scannen… (Ctrl+Shift+S) "
    "· Toolbar „Scan…“ · Startseite „Scannen…“ "
    "— Gerät wählen, „Scannen“ klicken; Backend unter Erweitert / Einstellungen → Scannen. "
    "Geräteliste aus Cache (sofort), Suche im Hintergrund. "
    "Netzwerkscanner: eSCL/AirScan. Gerät antwortet nicht: anderes Gerät wählen."
)

NO_DEVICE_STATUS_DE = (
    "0 Scanner · 0 Drucker — Kein Gerät erkannt. "
    "Treiber prüfen oder „Bilder importieren…“ nutzen. "
    + SCAN_START_HINT_DE
)


def _dedupe(devices: Sequence[DeviceInfo]) -> List[DeviceInfo]:
    seen: set[tuple[str, str]] = set()
    out: List[DeviceInfo] = []
    for d in devices:
        key = (d.kind.value, (d.device_id or d.name).strip().lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(d)
    return out


def _scope_from_name(name: str, *, is_remote: Optional[bool] = None) -> DeviceScope:
    if is_remote is True:
        return DeviceScope.NETWORK
    if is_remote is False:
        return DeviceScope.LOCAL
    n = (name or "").strip()
    if n.startswith("\\\\") or n.startswith("//"):
        return DeviceScope.NETWORK
    lower = n.lower()
    if any(x in lower for x in ("http://", "https://", "ipp://", "socket://", "smb://")):
        return DeviceScope.NETWORK
    if re.search(r"\b(network|netzwerk|shared|freigabe)\b", lower):
        return DeviceScope.NETWORK
    return DeviceScope.UNKNOWN


def _subprocess_kwargs() -> dict:
    """Windows: kein Konsolenfenster bei GUI/EXE; UTF-8-freundlich."""
    kwargs: dict = {}
    if platform.system() == "Windows":
        # CREATE_NO_WINDOW = 0x08000000
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        try:
            kwargs["encoding"] = "utf-8"
            kwargs["errors"] = "replace"
        except Exception:
            pass
    return kwargs


def list_printers_qt() -> tuple[List[DeviceInfo], List[str]]:
    """Drucker über Qt PrintSupport (lokal + remote-Flag)."""
    warnings: List[str] = []
    try:
        from PySide6.QtPrintSupport import QPrinterInfo
    except Exception as e:
        return [], [f"Qt PrintSupport nicht verfügbar: {e}"]

    out: List[DeviceInfo] = []
    try:
        infos = list(QPrinterInfo.availablePrinters())
    except Exception as e:
        return [], [f"Druckerliste (Qt) fehlgeschlagen: {e}"]

    for info in infos:
        try:
            name = str(info.printerName() or "").strip()
        except Exception:
            name = ""
        if not name:
            continue
        is_remote = None
        try:
            if hasattr(info, "isRemote"):
                is_remote = bool(info.isRemote())
        except Exception:
            is_remote = None
        details_parts: List[str] = []
        try:
            if hasattr(info, "description") and info.description():
                details_parts.append(str(info.description()))
        except Exception:
            pass
        try:
            if hasattr(info, "location") and info.location():
                details_parts.append(str(info.location()))
        except Exception:
            pass
        out.append(
            DeviceInfo(
                kind=DeviceKind.PRINTER,
                name=name,
                device_id=name,
                scope=_scope_from_name(name, is_remote=is_remote),
                backend="Qt",
                details=" · ".join(details_parts),
            )
        )
    if not out:
        warnings.append("Keine Systemdrucker gefunden (Qt).")
    return out, warnings


def _list_printers_winspool() -> tuple[List[DeviceInfo], List[str]]:
    """Windows: zusätzliche Drucker via Winspool (ctypes), inkl. Netzwerkfreigaben."""
    if platform.system() != "Windows":
        return [], []
    warnings: List[str] = []
    try:
        import ctypes
        from ctypes import wintypes
    except Exception as e:
        return [], [f"ctypes/Winspool nicht verfügbar: {e}"]

    try:
        winspool = ctypes.WinDLL("winspool.drv")
    except Exception as e:
        return [], [f"winspool.drv nicht ladbar: {e}"]

    PRINTER_ENUM_LOCAL = 0x00000002
    PRINTER_ENUM_CONNECTIONS = 0x00000004
    PRINTER_ENUM_NETWORK = 0x00000040

    class PRINTER_INFO_4(ctypes.Structure):
        _fields_ = [
            ("pPrinterName", wintypes.LPWSTR),
            ("pServerName", wintypes.LPWSTR),
            ("Attributes", wintypes.DWORD),
        ]

    level = 4
    flags = PRINTER_ENUM_LOCAL | PRINTER_ENUM_CONNECTIONS | PRINTER_ENUM_NETWORK
    needed = wintypes.DWORD(0)
    returned = wintypes.DWORD(0)
    try:
        winspool.EnumPrintersW(
            flags, None, level, None, 0, ctypes.byref(needed), ctypes.byref(returned)
        )
    except Exception as e:
        return [], [f"Winspool EnumPrinters (Probe) fehlgeschlagen: {e}"]
    if needed.value == 0:
        return [], []
    buf = (ctypes.c_byte * needed.value)()
    ok = winspool.EnumPrintersW(
        flags,
        None,
        level,
        ctypes.byref(buf),
        needed,
        ctypes.byref(needed),
        ctypes.byref(returned),
    )
    if not ok:
        warnings.append(
            "Winspool EnumPrinters fehlgeschlagen "
            "(Druckerwarteschlange / Treiber pruefen)."
        )
        return [], warnings

    count = int(returned.value)
    if count <= 0:
        return [], warnings
    try:
        arr_t = PRINTER_INFO_4 * count
        arr = arr_t.from_buffer(buf)
    except Exception as e:
        warnings.append(f"Winspool Puffer-Parse: {e}")
        return [], warnings
    out: List[DeviceInfo] = []
    for i in range(count):
        try:
            name = str(arr[i].pPrinterName or "").strip()
        except Exception:
            continue
        if not name:
            continue
        try:
            server = str(arr[i].pServerName or "").strip()
        except Exception:
            server = ""
        scope = DeviceScope.NETWORK if server or name.startswith("\\\\") else DeviceScope.LOCAL
        out.append(
            DeviceInfo(
                kind=DeviceKind.PRINTER,
                name=name,
                device_id=name,
                scope=scope,
                backend="Winspool",
                details=server,
            )
        )
    return out, warnings


def _list_printers_win32print() -> tuple[List[DeviceInfo], List[str]]:
    """Optional: pywin32 win32print.EnumPrinters."""
    if platform.system() != "Windows":
        return [], []
    try:
        import win32print  # type: ignore
    except Exception:
        return [], []
    warnings: List[str] = []
    out: List[DeviceInfo] = []
    flags = (
        getattr(win32print, "PRINTER_ENUM_LOCAL", 2)
        | getattr(win32print, "PRINTER_ENUM_CONNECTIONS", 4)
    )
    try:
        # level 2: richer; fallback level 1
        try:
            rows = win32print.EnumPrinters(flags, None, 2)
        except Exception:
            rows = win32print.EnumPrinters(flags, None, 1)
    except Exception as e:
        return [], [f"win32print EnumPrinters: {e}"]
    for row in rows or []:
        try:
            if isinstance(row, (tuple, list)):
                # level 1: (flags, desc, name, comment) or level 2 dict-like
                if len(row) >= 3 and isinstance(row[2], str):
                    name = row[2].strip()
                    details = str(row[1] if len(row) > 1 else "")
                    server = ""
                else:
                    continue
            elif isinstance(row, dict):
                name = str(row.get("pPrinterName") or row.get("PrinterName") or "").strip()
                details = str(row.get("pDriverName") or row.get("pLocation") or "")
                server = str(row.get("pServerName") or "")
            else:
                # PyWIN32 often returns tuple of strings for level 2 differently
                name = str(getattr(row, "pPrinterName", "") or "").strip()
                if not name and hasattr(row, "__getitem__"):
                    try:
                        name = str(row["pPrinterName"]).strip()
                    except Exception:
                        name = ""
                details = ""
                server = ""
            if not name:
                continue
            scope = (
                DeviceScope.NETWORK
                if server or name.startswith("\\\\")
                else _scope_from_name(name)
            )
            out.append(
                DeviceInfo(
                    kind=DeviceKind.PRINTER,
                    name=name,
                    device_id=name,
                    scope=scope if scope != DeviceScope.UNKNOWN else (
                        DeviceScope.NETWORK if server else DeviceScope.LOCAL
                    ),
                    backend="win32print",
                    details=details or server,
                )
            )
        except Exception:
            continue
    return out, warnings


def _run_powershell(script: str, *, timeout: float = DISCOVERY_STEP_TIMEOUT_S) -> tuple[str, str, int]:
    """PowerShell ausführen; (stdout, stderr, returncode). Kill nach Timeout inkl. Baum."""
    if platform.system() != "Windows":
        return "", "not-windows", -1
    ps = shutil.which("powershell") or shutil.which("pwsh")
    if not ps:
        return "", "PowerShell nicht gefunden", -1
    from instantlensdoc.core.scan_procs import (
        kill_new_since,
        kill_process_tree,
        register_pid,
        snapshot_scan_pids,
        unregister_pid,
    )

    kwargs = dict(_subprocess_kwargs())
    flags = int(kwargs.get("creationflags") or 0)
    flags |= int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200) or 0)
    kwargs["creationflags"] = flags
    before = snapshot_scan_pids()
    try:
        proc = subprocess.Popen(
            [
                ps,
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            **kwargs,
        )
    except Exception as e:
        return "", str(e), -1
    register_pid(proc.pid)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            kill_process_tree(proc.pid)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        try:
            kill_new_since(before)
        except Exception:
            pass
        try:
            proc.communicate(timeout=2)
        except Exception:
            pass
        return "", "PowerShell Timeout", -1
    except Exception as e:
        return "", str(e), -1
    finally:
        unregister_pid(proc.pid)
    return (out or ""), (err or ""), int(proc.returncode or 0)


def _powershell_json(script: str, *, timeout: float = DISCOVERY_STEP_TIMEOUT_S) -> tuple[Optional[object], Optional[str]]:
    """PowerShell → JSON (Windows). Toleriert ERR:-Prefix und BOM."""
    if platform.system() != "Windows":
        return None, None
    raw_out, raw_err, code = _run_powershell(script, timeout=timeout)
    raw = (raw_out or "").strip()
    if raw.startswith("\ufeff"):
        raw = raw.lstrip("\ufeff").strip()
    if not raw:
        err = (raw_err or "").strip() or (f"exit {code}" if code else "leer")
        return None, err
    # Explizite Fehlerzeile vom Skript
    for line in raw.splitlines():
        if line.startswith("ERR:"):
            return None, line[4:].strip() or line
    # JSON ggf. aus gemischtem Output extrahieren
    candidate = raw
    if not (candidate.startswith("{") or candidate.startswith("[")):
        m = re.search(r"(\[.*\]|\{.*\})\s*$", raw, re.S)
        if m:
            candidate = m.group(1)
        elif raw.startswith("ERR:"):
            return None, raw[4:].strip()
        else:
            return None, f"Kein JSON (exit {code}): {raw[:160]}"
    import json

    try:
        data = json.loads(candidate)
    except Exception as e:
        return None, f"JSON-Parse: {e}"
    return data, None


def _list_printers_powershell() -> tuple[List[DeviceInfo], List[str]]:
    """Windows: Get-Printer (lokal + Netzwerkverbindungen)."""
    if platform.system() != "Windows":
        return [], []
    script = r"""
$ErrorActionPreference = 'SilentlyContinue'
try {
  $items = @(Get-Printer -ErrorAction Stop | Select-Object Name, ComputerName, Type, PortName, DriverName, Shared, Published)
  if (-not $items) { '[]' } else { $items | ConvertTo-Json -Compress -Depth 3 }
} catch {
  Write-Output ('ERR:' + $_.Exception.Message)
}
"""
    data, err = _powershell_json(script)
    if err:
        return [], [f"Get-Printer: {err}"]
    rows = data if isinstance(data, list) else ([data] if data else [])
    out: List[DeviceInfo] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("Name") or "").strip()
        if not name:
            continue
        computer = str(row.get("ComputerName") or "").strip()
        port = str(row.get("PortName") or "").strip()
        driver = str(row.get("DriverName") or "").strip()
        ptype = str(row.get("Type") or "").strip()
        is_net = bool(computer) or name.startswith("\\\\")
        if port.lower().startswith(("wsd", "ipp", "http", "smb", "tcp")):
            is_net = True
        if "connection" in ptype.lower() or "network" in ptype.lower():
            is_net = True
        details = " · ".join(x for x in (driver, port, computer) if x)
        out.append(
            DeviceInfo(
                kind=DeviceKind.PRINTER,
                name=name,
                device_id=name,
                scope=DeviceScope.NETWORK if is_net else DeviceScope.LOCAL,
                backend="Get-Printer",
                details=details,
            )
        )
    return out, []


def find_naps2_console() -> Optional[str]:
    """Pfad zu NAPS2.Console.exe — Einstellungen → ScanTuxio ``scanner_naps2`` → PATH — 2.6.54."""
    try:
        from instantlensdoc.core.scan_transfer import naps2_console_path

        return naps2_console_path()
    except Exception:
        pass
    if platform.system() != "Windows":
        return shutil.which("naps2.console") or shutil.which("naps2-console")
    which = shutil.which("NAPS2.Console") or shutil.which("naps2.console")
    return which


# --- Scanner-Auswahl für den Scan-Dialog (gruppiert, je Backend gefiltert) — 2.6.54 ---


@dataclass
class ScannerChoice:
    """Ein Eintrag im Geräte-Dropdown: physisches Gerät + alternative Backend-Einträge."""

    label: str
    primary: DeviceInfo
    alternates: List[DeviceInfo] = field(default_factory=list)

    @property
    def device_id(self) -> str:
        return self.primary.device_id or self.primary.name

    def all_devices(self) -> List[DeviceInfo]:
        return [self.primary] + list(self.alternates)


def _device_group_key(d: DeviceInfo) -> str:
    try:
        from instantlensdoc.core.scan_transfer import clean_device_name
    except Exception:  # pragma: no cover
        def clean_device_name(n: str) -> str:  # type: ignore
            return n

    name = clean_device_name(d.name or "")
    did = (d.device_id or "").lower()
    if did.startswith("naps2:"):
        rest = did[len("naps2:"):]
        _drv, _, nm = rest.partition(":")
        name = clean_device_name(nm) or name
    key = re.sub(r"\s+", " ", name.strip().lower())
    return key or did


def device_is_network(d: DeviceInfo) -> bool:
    """Netzwerk-/eSCL-Gerät? WIA-Connect hängt hier oft im Energiesparmodus."""
    if d.scope == DeviceScope.NETWORK:
        return True
    did = (d.device_id or "").lower()
    be = (d.backend or "").lower()
    name = (d.name or "").lower()
    if did.startswith(("native-escl:", "escl:", "mdns:", "airscan:", "http://", "https://")):
        return True
    if any(x in be for x in ("escl", "mdns", "airscan", "netzwerk")):
        return True
    if any(x in name for x in ("netzwerk", "network", "escl", "airscan")):
        return True
    try:
        from instantlensdoc.core.scan_procs import name_looks_network_mfp

        if name_looks_network_mfp(name) or name_looks_network_mfp(did):
            return True
    except Exception:
        pass
    return False


def _device_backend_rank(d: DeviceInfo) -> int:
    """Niedriger = besser. Netzwerk: eSCL vor WIA (ScanTuxio-Netzmodus)."""
    did = (d.device_id or "").lower()
    be = (d.backend or "").lower()
    if device_is_network(d):
        if did.startswith(("native-escl:", "escl:")) or "escl" in be:
            return 0
        if did.startswith("mdns:") or "mdns" in be:
            return 1
        if did.startswith("naps2:"):
            return 2
        if "sane" in be or did.startswith(("airscan:", "net:")):
            return 3
        if "wia" in be or (did.startswith("{") and "}" in did):
            return 20
        return 8
    if did.startswith("{") and "}" in did:
        return 0  # lokales WIA-DeviceID
    if did.startswith("naps2:wia:"):
        return 1
    if did.startswith(("native-escl:", "escl:")):
        return 2
    if did.startswith("naps2:twain:"):
        return 3
    if "wia" in be:
        return 4
    if did.startswith("mdns:"):
        return 5
    if "twain" in be:
        return 6
    if "sane" in be:
        return 2
    if "pnp" in be:
        return 7
    if "cim" in be:
        return 8
    return 9


def _device_matches_backend(d: DeviceInfo, backend: str) -> bool:
    """Passt der Geräteeintrag zum gewählten Scan-Backend?"""
    try:
        from instantlensdoc.core.scan_transfer import classify_device_id
    except Exception:  # pragma: no cover
        return True
    cls = classify_device_id(d.device_id, d.backend)
    b = (backend or "auto").lower()
    if b in ("auto", "external"):
        return True
    if b == "scantuxio":
        return cls in ("naps2", "escl", "sane", "wia", "twain", "pnp", "unknown")
    if b == "wia":
        return cls in ("wia", "naps2", "pnp", "twain", "unknown", "dialog")
    if b == "naps2":
        return cls in ("naps2", "wia", "pnp", "twain", "unknown")
    if b == "escl":
        return cls == "escl"
    if b == "twain":
        return cls in ("twain", "naps2", "wia", "pnp", "unknown")
    return True


def scanner_choices(
    scanners: Sequence[DeviceInfo],
    *,
    backend: str = "auto",
    include_wia_dialog: Optional[bool] = None,
) -> List[ScannerChoice]:
    """Scanner für das Dropdown: pro physischem Gerät ein Eintrag (bestes Backend zuerst,
    Alternativen als Fallback), gefiltert nach Backend; unter Windows zusätzlich der
    WIA-Dialog-Eintrag — 2.6.54."""
    groups: dict[str, List[DeviceInfo]] = {}
    order: List[str] = []
    for d in scanners:
        if d is None or d.kind != DeviceKind.SCANNER:
            continue
        if not _device_matches_backend(d, backend):
            continue
        key = _device_group_key(d)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(d)
    out: List[ScannerChoice] = []
    for key in order:
        devs = sorted(groups[key], key=_device_backend_rank)
        primary = devs[0]
        try:
            from instantlensdoc.core.scan_transfer import clean_device_name

            base = clean_device_name(primary.name) or primary.name or primary.device_id
        except Exception:  # pragma: no cover
            base = primary.name or primary.device_id
        tags: List[str] = []
        for d in devs:
            tag = (d.backend or "").replace("ScanTuxio/", "")
            if tag and tag not in tags:
                tags.append(tag)
        scope = "Netzwerk" if primary.scope == DeviceScope.NETWORK else ""
        suffix = " · ".join(x for x in ([scope] if scope else []) + tags[:3])
        label = f"{base} ({suffix})" if suffix else base
        out.append(ScannerChoice(label=label, primary=primary, alternates=devs[1:]))
    out.sort(
        key=lambda ch: (
            0 if device_is_network(ch.primary) else 1,
            _device_backend_rank(ch.primary),
        )
    )
    if include_wia_dialog is None:
        include_wia_dialog = platform.system() == "Windows" and (backend or "auto") in (
            "auto",
            "wia",
        )
    if include_wia_dialog:
        try:
            from instantlensdoc.core.scan_transfer import WIA_DIALOG_DEVICE_ID, WIA_DIALOG_LABEL_DE
        except Exception:  # pragma: no cover
            WIA_DIALOG_DEVICE_ID, WIA_DIALOG_LABEL_DE = "wia:dialog", "Windows-Scannerauswahl (WIA-Dialog)"
        out.append(
            ScannerChoice(
                label=WIA_DIALOG_LABEL_DE,
                primary=DeviceInfo(
                    kind=DeviceKind.SCANNER,
                    name=WIA_DIALOG_LABEL_DE,
                    device_id=WIA_DIALOG_DEVICE_ID,
                    scope=DeviceScope.LOCAL,
                    backend="WIA",
                ),
            )
        )
    return out


def _list_scanners_scantuxio() -> tuple[List[DeviceInfo], List[str], List[str]]:
    """ScanTuxio ``list_devices_all``: SANE + NAPS2(WIA/TWAIN) + native-eSCL."""
    warnings: List[str] = []
    notes: List[str] = ["ScanTuxio: list_devices_all"]
    out: List[DeviceInfo] = []
    try:
        from instantlensdoc.core.scantuxio import scanner as st_scanner
    except Exception as e:
        return [], [f"ScanTuxio scanner: {e}"], notes
    try:
        devices = st_scanner.list_devices_all(timeout=int(DISCOVERY_STEP_TIMEOUT_S))
    except Exception as e:
        return [], [f"ScanTuxio list_devices_all: {e}"], notes
    for d in devices or []:
        try:
            did = str(getattr(d, "device_id", "") or "").strip()
            name = str(getattr(d, "description", "") or did).strip()
        except Exception:
            continue
        if not did and not name:
            continue
        backend = "ScanTuxio"
        scope = DeviceScope.LOCAL
        low = did.lower()
        if low.startswith("naps2:"):
            backend = "ScanTuxio/NAPS2"
            # naps2:wia:Name → Anzeigename kürzen
            rest = did[len("naps2:") :]
            if ":" in rest:
                drv, nm = rest.split(":", 1)
                backend = f"ScanTuxio/NAPS2/{drv.upper()}"
                if nm:
                    name = f"{nm} ({drv.upper()})"
        elif low.startswith("native-escl:") or low.startswith("escl:"):
            backend = "ScanTuxio/eSCL"
            scope = DeviceScope.NETWORK
        elif any(x in low for x in ("net:", "airscan:", "http:", "escl:")):
            scope = DeviceScope.NETWORK
            backend = "ScanTuxio/SANE"
        else:
            backend = "ScanTuxio/SANE"
        out.append(
            DeviceInfo(
                kind=DeviceKind.SCANNER,
                name=name or did,
                device_id=did or name,
                scope=scope,
                backend=backend,
            )
        )
    if out:
        notes.append(f"ScanTuxio-Scanner: {len(out)}")
    else:
        notes.append("ScanTuxio: 0 Scanner (NAPS2/SANE/eSCL)")
    return _dedupe(out), warnings, notes


def _list_network_scantuxio() -> tuple[List[DeviceInfo], List[str], List[str]]:
    """ScanTuxio mDNS/zeroconf Netzwerk-Drucker/Scanner (Anzeige + eSCL-IDs)."""
    warnings: List[str] = []
    notes: List[str] = []
    out: List[DeviceInfo] = []
    try:
        from instantlensdoc.core.scantuxio import discovery as st_discovery
        from instantlensdoc.core.scantuxio import scanner_escl as st_escl
    except Exception as e:
        return [], [f"ScanTuxio discovery: {e}"], []
    net_devs = []
    try:
        if hasattr(st_discovery, "discover_network_devices"):
            net_devs.extend(st_discovery.discover_network_devices(timeout=3) or [])
    except Exception as e:
        notes.append(f"avahi: {e}")
    try:
        if hasattr(st_discovery, "discover_network_devices_zeroconf"):
            net_devs.extend(st_discovery.discover_network_devices_zeroconf(timeout=2.5) or [])
    except Exception as e:
        notes.append(f"zeroconf: {e}")
    seen: set[tuple[str, str]] = set()
    for nd in net_devs:
        try:
            name = str(getattr(nd, "name", "") or "").strip()
            kind = str(getattr(nd, "kind", "") or "").strip()
            host = str(getattr(nd, "address", "") or getattr(nd, "host", "") or "").strip()
            port = str(getattr(nd, "port", "") or "").strip()
            stype = str(getattr(nd, "service_type", "") or "")
        except Exception:
            continue
        key = (name, host)
        if key in seen or not name:
            continue
        seen.add(key)
        if kind == "Scanner" or re.search(r"uscan|scanner|escl", stype, re.I):
            did = ""
            if host and port:
                use_https = "uscans" in stype.lower()
                try:
                    did = st_escl.build_device_id(host, port, use_https=use_https)
                except Exception:
                    did = f"native-escl:http://{host}:{port}"
            out.append(
                DeviceInfo(
                    kind=DeviceKind.SCANNER,
                    name=f"{name} (Netzwerk, eSCL)",
                    device_id=did or f"mdns:{host}:{port}",
                    scope=DeviceScope.NETWORK,
                    backend="ScanTuxio/mDNS",
                    details=f"{stype} {host}:{port}".strip(),
                )
            )
        elif kind == "Drucker" or re.search(r"ipp|printer|pdl", stype, re.I):
            out.append(
                DeviceInfo(
                    kind=DeviceKind.PRINTER,
                    name=name,
                    device_id=f"ipp://{host}:{port}" if host else name,
                    scope=DeviceScope.NETWORK,
                    backend="ScanTuxio/mDNS",
                    details=f"{stype} {host}:{port}".strip(),
                )
            )
    if out:
        notes.append(f"ScanTuxio-mDNS: {len(out)}")
    return out, warnings, notes


def _list_printers_scantuxio() -> tuple[List[DeviceInfo], List[str]]:
    """ScanTuxio printing (Qt unter Windows / CUPS unter Linux)."""
    try:
        from instantlensdoc.core.scantuxio import printing as st_print
    except Exception as e:
        return [], [f"ScanTuxio printing: {e}"]
    try:
        printers = st_print.list_printers(timeout=10)
    except TypeError:
        try:
            printers = st_print.list_printers()
        except Exception as e:
            return [], [f"ScanTuxio list_printers: {e}"]
    except Exception as e:
        return [], [f"ScanTuxio list_printers: {e}"]
    out: List[DeviceInfo] = []
    for p in printers or []:
        try:
            name = str(getattr(p, "name", "") or "").strip()
            state = str(getattr(p, "state", "") or "")
            is_def = bool(getattr(p, "is_default", False))
        except Exception:
            continue
        if not name:
            continue
        out.append(
            DeviceInfo(
                kind=DeviceKind.PRINTER,
                name=name + (" (Standard)" if is_def else ""),
                device_id=name,
                scope=_scope_from_name(name),
                backend="ScanTuxio",
                details=state,
            )
        )
    return out, []


def _list_scanners_windows() -> tuple[List[DeviceInfo], List[str], List[str]]:
    """Windows-Scanner: ScanTuxio (NAPS2/eSCL) zuerst, dann WIA/PnP/TWAIN."""
    warnings: List[str] = []
    notes: List[str] = ["Windows: ScanTuxio + WIA/PnP/TWAIN"]
    out: List[DeviceInfo] = []

    # 0) ScanTuxio-Backends (NAPS2 WIA/TWAIN + native-eSCL)
    try:
        st_devs, st_warn, st_notes = _list_scanners_scantuxio()
        out.extend(st_devs)
        warnings.extend(st_warn)
        notes.extend(st_notes)
    except Exception as e:
        warnings.append(f"ScanTuxio: {e}")
    try:
        net_devs, net_warn, net_notes = _list_network_scantuxio()
        for d in net_devs:
            if d.kind == DeviceKind.SCANNER:
                out.append(d)
        warnings.extend(net_warn)
        notes.extend(net_notes)
    except Exception as e:
        notes.append(f"ScanTuxio-mDNS: {e}")

    # 1) WIA DeviceManager (COM via PowerShell) — alle Scanner-Typen
    wia_script = r"""
$ErrorActionPreference = 'Stop'
try {
  $dm = New-Object -ComObject WIA.DeviceManager
  $items = @()
  foreach ($d in @($dm.DeviceInfos)) {
    $name = ''
    $id = ''
    $type = 0
    try { $name = [string]$d.Properties.Item('Name').Value } catch {
      try { $name = [string]$d.Properties('Name').Value } catch { $name = [string]$d.DeviceID }
    }
    try { $id = [string]$d.DeviceID } catch { $id = $name }
    try { $type = [int]$d.Type } catch { $type = 0 }
    # 1 = Scanner, 65537 = mixed; Cameras (2) auslassen sofern Name nicht Scan
    $isScan = ($type -eq 1 -or $type -eq 65537 -or $name -match 'scan|wia|twain')
    if ($isScan) {
      $items += [pscustomobject]@{ Name = $name; DeviceID = $id; Backend = 'WIA'; Type = $type }
    }
  }
  if (-not $items) { '[]' } else { $items | ConvertTo-Json -Compress -Depth 3 }
} catch {
  Write-Output ('ERR:' + $_.Exception.Message)
}
"""
    data, err = _powershell_json(wia_script)
    if err:
        # COM fehlt oft ohne WIA — klare DE-Meldung
        msg = err
        if re.search(r"80040154|class not registered|nicht registriert|WIA", err, re.I):
            msg = (
                "WIA.DeviceManager nicht verfuegbar "
                "(WIA-Komponente / Scanner-Treiber fehlt)."
            )
        warnings.append(f"WIA: {msg}")
    else:
        rows = data if isinstance(data, list) else ([data] if data else [])
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = str(row.get("Name") or "").strip()
            did = str(row.get("DeviceID") or name).strip()
            if not name:
                continue
            scope = (
                DeviceScope.NETWORK
                if "network" in did.lower()
                or did.lower().startswith("\\\\")
                or re.search(r"network|netzwerk|\\\\|ipp|http", name, re.I)
                else DeviceScope.LOCAL
            )
            out.append(
                DeviceInfo(
                    kind=DeviceKind.SCANNER,
                    name=name,
                    device_id=did,
                    scope=scope,
                    backend="WIA",
                    details=f"Type={row.get('Type', '')}",
                )
            )

    # 2) PnP Image / Scanner class
    pnp_script = r"""
$ErrorActionPreference = 'SilentlyContinue'
$items = @(Get-PnpDevice -Class Image,Camera -Status OK,Unknown,Error -ErrorAction SilentlyContinue |
  Where-Object {
    $_.FriendlyName -match 'scan|wia|twain|epson|canon|brother|hp |fujitsu|kodak|xerox|ricoh|lexmark|samsung|panasonic' `
      -or $_.Class -eq 'Image'
  } |
  Select-Object -Property FriendlyName, InstanceId, Class, Status)
if (-not $items) {
  $items = @(Get-CimInstance Win32_PnPEntity -ErrorAction SilentlyContinue |
    Where-Object { $_.PNPClass -eq 'Image' -or $_.Name -match 'Scanner|Scan|WIA' } |
    Select-Object @{N='FriendlyName';E={$_.Name}}, @{N='InstanceId';E={$_.PNPDeviceID}}, @{N='Class';E={$_.PNPClass}}, @{N='Status';E={$_.Status}})
}
if (-not $items) { '[]' } else { $items | ConvertTo-Json -Compress -Depth 3 }
"""
    data2, err2 = _powershell_json(pnp_script)
    if err2:
        warnings.append(f"PnP-Scanner: {err2}")
    else:
        rows2 = data2 if isinstance(data2, list) else ([data2] if data2 else [])
        for row in rows2:
            if not isinstance(row, dict):
                continue
            name = str(row.get("FriendlyName") or "").strip()
            did = str(row.get("InstanceId") or name).strip()
            if not name:
                continue
            # Webcams ohne Scan-Hinweis ueberspringen
            if re.search(r"\b(webcam|camera|integrated)\b", name, re.I) and not re.search(
                r"scan|wia|twain", name, re.I
            ):
                continue
            scope = DeviceScope.LOCAL
            if (
                "SWD\\PRINTENUM" in did.upper()
                or ("USBPRINT" in did.upper() and "IP" in name.upper())
                or re.search(r"network|netzwerk|\\\\|ipp|http", name, re.I)
            ):
                scope = DeviceScope.NETWORK
            status = str(row.get("Status") or "")
            out.append(
                DeviceInfo(
                    kind=DeviceKind.SCANNER,
                    name=name,
                    device_id=did,
                    scope=scope,
                    backend="PnP",
                    details=" · ".join(
                        x for x in (str(row.get("Class") or ""), status) if x
                    ),
                )
            )

    # 3) TWAIN Datenquellen (Registry)
    twain_script = r"""
$ErrorActionPreference = 'SilentlyContinue'
$paths = @(
  'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Twain',
  'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows NT\CurrentVersion\Twain',
  'HKLM:\SOFTWARE\Twain',
  'HKLM:\SOFTWARE\WOW6432Node\Twain'
)
$items = @()
foreach ($p in $paths) {
  if (-not (Test-Path $p)) { continue }
  Get-ChildItem $p -ErrorAction SilentlyContinue | ForEach-Object {
    $name = $_.PSChildName
    if ($name) {
      $items += [pscustomobject]@{ Name = $name; DeviceID = ("TWAIN:" + $name); Backend = 'TWAIN' }
    }
  }
}
# DS-Dateien unter Windows\twain_32
$tw = Join-Path $env:WINDIR 'twain_32'
if (Test-Path $tw) {
  Get-ChildItem -Path $tw -Recurse -Filter *.ds -ErrorAction SilentlyContinue | ForEach-Object {
    $n = $_.BaseName
    $items += [pscustomobject]@{ Name = $n; DeviceID = ("TWAIN-DS:" + $_.FullName); Backend = 'TWAIN' }
  }
}
if (-not $items) { '[]' } else { $items | Select-Object -Unique Name, DeviceID, Backend | ConvertTo-Json -Compress -Depth 3 }
"""
    data3, err3 = _powershell_json(twain_script, timeout=DISCOVERY_STEP_TIMEOUT_S)
    if err3:
        notes.append(f"TWAIN-Hinweis: {err3}")
    else:
        rows3 = data3 if isinstance(data3, list) else ([data3] if data3 else [])
        for row in rows3:
            if not isinstance(row, dict):
                continue
            name = str(row.get("Name") or "").strip()
            did = str(row.get("DeviceID") or name).strip()
            if not name:
                continue
            out.append(
                DeviceInfo(
                    kind=DeviceKind.SCANNER,
                    name=name,
                    device_id=did,
                    scope=DeviceScope.LOCAL,
                    backend="TWAIN",
                )
            )
        if rows3:
            notes.append("TWAIN-Quellen aus Registry/DS")

    # 4) Optional: python WIA via win32com
    if not out:
        try:
            import win32com.client  # type: ignore

            dm = win32com.client.Dispatch("WIA.DeviceManager")
            for d in dm.DeviceInfos:
                try:
                    dtype = int(d.Type)
                except Exception:
                    dtype = 0
                if dtype not in (1, 65537):
                    continue
                try:
                    name = str(d.Properties("Name").Value)
                except Exception:
                    try:
                        name = str(d.Properties.Item("Name").Value)
                    except Exception:
                        name = str(d.DeviceID)
                did = str(d.DeviceID)
                out.append(
                    DeviceInfo(
                        kind=DeviceKind.SCANNER,
                        name=name,
                        device_id=did,
                        scope=DeviceScope.LOCAL,
                        backend="WIA-COM",
                    )
                )
            notes.append("win32com WIA Fallback")
        except Exception:
            pass

    # 5) Win32_ImageDevice / Scanner CIM (zusaetzlich zu PnP)
    cim_script = r"""
$ErrorActionPreference = 'SilentlyContinue'
$items = @()
try {
  $items += @(Get-CimInstance -ClassName Win32_ImageDevice -ErrorAction SilentlyContinue |
    Select-Object @{N='Name';E={$_.Name}}, @{N='DeviceID';E={$_.DeviceID}}, @{N='Status';E={$_.Status}})
} catch {}
try {
  $items += @(Get-CimInstance -ClassName Win32_PnPEntity -ErrorAction SilentlyContinue |
    Where-Object { $_.PNPClass -eq 'Image' -or $_.Name -match 'Scanner|Scan|WIA|TWAIN' } |
    Select-Object @{N='Name';E={$_.Name}}, @{N='DeviceID';E={$_.PNPDeviceID}}, @{N='Status';E={$_.Status}})
} catch {}
$items = $items | Where-Object { $_.Name } | Select-Object -Unique Name, DeviceID, Status
if (-not $items) { '[]' } else { $items | ConvertTo-Json -Compress -Depth 3 }
"""
    data_cim, err_cim = _powershell_json(cim_script, timeout=DISCOVERY_STEP_TIMEOUT_S)
    if err_cim:
        notes.append(f"CIM-Image: {err_cim}")
    else:
        rows_cim = data_cim if isinstance(data_cim, list) else ([data_cim] if data_cim else [])
        for row in rows_cim:
            if not isinstance(row, dict):
                continue
            name = str(row.get("Name") or "").strip()
            did = str(row.get("DeviceID") or name).strip()
            if not name:
                continue
            if re.search(r"\b(webcam|camera|integrated)\b", name, re.I) and not re.search(
                r"scan|wia|twain", name, re.I
            ):
                continue
            out.append(
                DeviceInfo(
                    kind=DeviceKind.SCANNER,
                    name=name,
                    device_id=did or f"CIM:{name}",
                    scope=DeviceScope.LOCAL,
                    backend="CIM",
                    details=str(row.get("Status") or ""),
                )
            )
        if rows_cim:
            notes.append("Win32_ImageDevice/CIM")

    if not out:
        warnings.append(WINDOWS_SCANNER_DRIVER_HINT_DE)
    return _dedupe(out), warnings, notes


def _list_scanners_sane() -> tuple[List[DeviceInfo], List[str], List[str]]:
    """Linux/macOS: SANE scanimage -L."""
    warnings: List[str] = []
    notes: List[str] = ["SANE scanimage"]
    exe = shutil.which("scanimage")
    if not exe:
        return [], ["scanimage (SANE) nicht im PATH — optional für Scannerliste."], notes
    try:
        proc = subprocess.run(
            [exe, "-L"],
            capture_output=True,
            text=True,
            timeout=DISCOVERY_STEP_TIMEOUT_S,
            check=False,
        )
    except Exception as e:
        return [], [f"scanimage fehlgeschlagen: {e}"], notes
    out: List[DeviceInfo] = []
    for line in (proc.stdout or "").splitlines():
        m = re.match(r"device `([^']+)'\s+is a\s+(.+)$", line.strip())
        if not m:
            continue
        did, desc = m.group(1), m.group(2).strip()
        scope = (
            DeviceScope.NETWORK
            if any(x in did for x in ("net:", "airscan:", "http:", "escl:"))
            else DeviceScope.LOCAL
        )
        out.append(
            DeviceInfo(
                kind=DeviceKind.SCANNER,
                name=desc or did,
                device_id=did,
                scope=scope,
                backend="SANE",
            )
        )
    if not out and proc.returncode != 0:
        warnings.append((proc.stderr or "scanimage: keine Geräte").strip())
    return out, warnings, notes


def list_scanners() -> tuple[List[DeviceInfo], List[str], List[str]]:
    system = platform.system()
    try:
        if system == "Windows":
            return _list_scanners_windows()
        # Linux: ScanTuxio (SANE + eSCL) + klassisches scanimage
        out: List[DeviceInfo] = []
        warnings: List[str] = []
        notes: List[str] = []
        try:
            st_devs, st_warn, st_notes = _list_scanners_scantuxio()
            out.extend(st_devs)
            warnings.extend(st_warn)
            notes.extend(st_notes)
        except Exception as e:
            warnings.append(f"ScanTuxio: {e}")
        try:
            sane_devs, sane_warn, sane_notes = _list_scanners_sane()
            out.extend(sane_devs)
            warnings.extend(sane_warn)
            notes.extend(sane_notes)
        except Exception as e:
            warnings.append(f"SANE: {e}")
        try:
            net_devs, net_warn, net_notes = _list_network_scantuxio()
            for d in net_devs:
                if d.kind == DeviceKind.SCANNER:
                    out.append(d)
            warnings.extend(net_warn)
            notes.extend(net_notes)
        except Exception as e:
            notes.append(f"mDNS: {e}")
        out = _dedupe(out)
        if not out:
            warnings.append(
                "Keine Scanner erkannt (SANE/scanimage bzw. eSCL). "
                "Optional: sane-utils / NAPS2."
            )
        return out, warnings, notes
    except Exception as e:
        return [], [f"Scanner-Erkennung fehlgeschlagen: {e}"], ["error"]


def list_printers() -> tuple[List[DeviceInfo], List[str]]:
    printers: List[DeviceInfo] = []
    warnings: List[str] = []
    try:
        p_st, w_st = _list_printers_scantuxio()
        printers.extend(p_st)
        warnings.extend(w_st)
    except Exception as e:
        warnings.append(f"ScanTuxio-Drucker: {e}")
    try:
        p_qt, w_qt = list_printers_qt()
        printers.extend(p_qt)
        warnings.extend(w_qt)
    except Exception as e:
        warnings.append(f"Qt-Drucker: {e}")
    try:
        p_ws, w_ws = _list_printers_winspool()
        printers.extend(p_ws)
        warnings.extend(w_ws)
    except Exception as e:
        warnings.append(f"Winspool: {e}")
    try:
        p_ps, w_ps = _list_printers_powershell()
        printers.extend(p_ps)
        warnings.extend(w_ps)
    except Exception as e:
        warnings.append(f"Get-Printer: {e}")
    try:
        p_w32, w_w32 = _list_printers_win32print()
        printers.extend(p_w32)
        warnings.extend(w_w32)
    except Exception as e:
        warnings.append(f"win32print: {e}")
    try:
        net_devs, net_warn, _net_notes = _list_network_scantuxio()
        for d in net_devs:
            if d.kind == DeviceKind.PRINTER:
                printers.append(d)
        warnings.extend(net_warn)
    except Exception as e:
        warnings.append(f"mDNS-Drucker: {e}")
    printers = _dedupe(printers)
    if not printers and platform.system() == "Windows":
        warnings.append(WINDOWS_PRINTER_DRIVER_HINT_DE)
    return printers, warnings


def discover_devices(
    *,
    include_printers: bool = True,
    include_scanners: bool = True,
    on_progress: Optional[Callable[[str], None]] = None,
) -> DeviceDiscoveryResult:
    """Geräte neu suchen (Refresh/Rescan). Nie werfen — Warnings statt Crash."""
    result = DeviceDiscoveryResult()
    try:
        if include_printers:
            if on_progress:
                on_progress("Drucker werden gesucht…")
            try:
                printers, warnings = list_printers()
            except Exception as e:
                printers, warnings = [], [f"Drucker-Erkennung: {e}"]
            result.printers = printers
            result.warnings.extend(warnings)
            result.backend_notes.append(f"Drucker: {len(printers)}")
        if include_scanners:
            if on_progress:
                on_progress("Scanner werden gesucht…")
            try:
                scanners, warnings, notes = list_scanners()
            except Exception as e:
                scanners, warnings, notes = [], [f"Scanner-Erkennung: {e}"], []
            result.scanners = scanners
            result.warnings.extend(warnings)
            result.backend_notes.extend(notes)
            result.backend_notes.append(f"Scanner: {len(scanners)}")
    except Exception as e:
        result.warnings.append(f"Geräteerkennung fehlgeschlagen: {e}")
    try:
        save_cached_discovery(result)
    except Exception:
        pass
    return result


def printer_names_for_print() -> List[str]:
    """Kurze Namensliste für Druckziel-Auswahl."""
    try:
        printers, _ = list_printers()
    except Exception:
        return []
    return [p.name for p in printers]


def format_discovery_status(result: DeviceDiscoveryResult) -> str:
    """Kurzer DE-Status fuer UI."""
    n_p = len(result.printers)
    n_s = len(result.scanners)
    if n_p == 0 and n_s == 0:
        return NO_DEVICE_STATUS_DE
    msg = f"{n_s} Scanner · {n_p} Drucker"
    if n_s == 0:
        msg += " — Kein Scanner · Bilder importieren oder Treiber prüfen"
    if result.warnings:
        # Erste Warnung kompakt (ohne mehrzeiligen Hint voll)
        first = result.warnings[0].splitlines()[0]
        if first and first not in msg:
            msg += f" — {first}"
    return msg


DEVICE_CACHE_NAME = "device_cache.json"


def device_cache_path():
    """JSON-Cache der letzten Geräteliste (Menü öffnet daraus sofort)."""
    try:
        from instantlensdoc.config import config_dir

        return config_dir() / DEVICE_CACHE_NAME
    except Exception:
        from pathlib import Path

        return Path.home() / ".config" / "InstantLensDoc" / DEVICE_CACHE_NAME


def _device_to_dict(d: DeviceInfo) -> dict:
    return {
        "kind": d.kind.value,
        "name": d.name,
        "device_id": d.device_id,
        "scope": d.scope.value,
        "backend": d.backend,
        "details": d.details,
    }


def _device_from_dict(raw: object) -> Optional[DeviceInfo]:
    if not isinstance(raw, dict):
        return None
    kind_s = str(raw.get("kind") or "scanner")
    try:
        kind = DeviceKind(kind_s)
    except ValueError:
        kind = DeviceKind.SCANNER
    scope_s = str(raw.get("scope") or "unknown")
    try:
        scope = DeviceScope(scope_s)
    except ValueError:
        scope = DeviceScope.UNKNOWN
    name = str(raw.get("name") or "").strip()
    if not name:
        return None
    return DeviceInfo(
        kind=kind,
        name=name,
        device_id=str(raw.get("device_id") or ""),
        scope=scope,
        backend=str(raw.get("backend") or ""),
        details=str(raw.get("details") or ""),
    )


def save_cached_discovery(result: DeviceDiscoveryResult) -> None:
    """Letzte Erkennung persistieren. Wirft nie."""
    try:
        payload = {
            "version": 1,
            "printers": [_device_to_dict(d) for d in result.printers],
            "scanners": [_device_to_dict(d) for d in result.scanners],
            "warnings": list(result.warnings[:12]),
            "backend_notes": list(result.backend_notes[:12]),
        }
        path = device_cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        pass


def load_cached_discovery() -> DeviceDiscoveryResult:
    """Letzte Geräteliste (sofort, ohne Hardware). Leer wenn kein Cache."""
    result = DeviceDiscoveryResult()
    try:
        path = device_cache_path()
        if not path.is_file():
            return result
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return result
        for row in raw.get("scanners") or []:
            d = _device_from_dict(row)
            if d is not None and d.kind == DeviceKind.SCANNER:
                result.scanners.append(d)
        for row in raw.get("printers") or []:
            d = _device_from_dict(row)
            if d is not None and d.kind == DeviceKind.PRINTER:
                result.printers.append(d)
        for w in raw.get("warnings") or []:
            result.warnings.append(str(w))
        result.backend_notes.append("aus Cache")
    except Exception:
        return DeviceDiscoveryResult()
    return result


def devices_menu_entries(
    result: Optional[DeviceDiscoveryResult] = None,
    *,
    limit: int = 16,
) -> List[Tuple[str, DeviceInfo]]:
    """Einträge für Menü Geräte — nur Cache/übergebene Liste, nie Hardware."""
    src = result if result is not None else load_cached_discovery()
    out: List[Tuple[str, DeviceInfo]] = []
    for d in list(src.scanners) + list(src.printers):
        if d is None:
            continue
        out.append((d.label(), d))
        if len(out) >= max(1, int(limit)):
            break
    return out
