"""Lokale und Netzwerk-Drucker-/Scanner-Erkennung — 2.6.2 / Haertung 2.6.38.

Windows: Systemdrucker (Qt / Winspool / Get-Printer / win32print),
Scanner via WIA / PnP / TWAIN-Quellen wo verfuegbar.
Linux/macOS: Qt-Drucker; Scanner ueber SANE (`scanimage -L`) falls vorhanden.
Netzwerk: Qt ``isRemote`` / UNC-Freigaben / erkannte Netzwerk-PnP-Geraete.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, List, Optional, Sequence, Tuple


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
    "  • Tesseract: winget install UB-Mannheim.TesseractOCR (deu+eng anhaken)\n"
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
    "  • PowerShell: Get-PnpDevice -Class Image\n"
    "  • Ohne Hardware: im Scan-Dialog „Bilder importieren…“ nutzen"
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


def _run_powershell(script: str, *, timeout: float = 30.0) -> tuple[str, str, int]:
    """PowerShell ausführen; (stdout, stderr, returncode)."""
    if platform.system() != "Windows":
        return "", "not-windows", -1
    ps = shutil.which("powershell") or shutil.which("pwsh")
    if not ps:
        return "", "PowerShell nicht gefunden", -1
    try:
        proc = subprocess.run(
            [
                ps,
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            **_subprocess_kwargs(),
        )
    except subprocess.TimeoutExpired:
        return "", "PowerShell Timeout", -1
    except Exception as e:
        return "", str(e), -1
    return (proc.stdout or ""), (proc.stderr or ""), int(proc.returncode)


def _powershell_json(script: str, *, timeout: float = 30.0) -> tuple[Optional[object], Optional[str]]:
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


def _list_scanners_windows() -> tuple[List[DeviceInfo], List[str], List[str]]:
    """Windows-Scanner: WIA-Geräte + PnP Image-Klasse + TWAIN-Quellen."""
    warnings: List[str] = []
    notes: List[str] = ["Windows: WIA/PnP/TWAIN-Scannererkennung"]
    out: List[DeviceInfo] = []

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
    data3, err3 = _powershell_json(twain_script, timeout=20.0)
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
            timeout=20,
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
        return _list_scanners_sane()
    except Exception as e:
        return [], [f"Scanner-Erkennung fehlgeschlagen: {e}"], ["error"]


def list_printers() -> tuple[List[DeviceInfo], List[str]]:
    printers: List[DeviceInfo] = []
    warnings: List[str] = []
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
    msg = f"{n_s} Scanner · {n_p} Drucker"
    if result.warnings:
        # Erste Warnung kompakt (ohne mehrzeiligen Hint voll)
        first = result.warnings[0].splitlines()[0]
        msg += f" — {first}"
    return msg
