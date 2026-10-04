"""Lokale und Netzwerk-Drucker-/Scanner-Erkennung — 2.6.2.

Windows: Systemdrucker (Qt / Winspool), Scanner via WIA/PnP wo verfügbar.
Linux/macOS: Qt-Drucker; Scanner über SANE (`scanimage -L`) falls vorhanden.
Netzwerk: Qt ``isRemote`` / UNC-Freigaben / erkannte Netzwerk-PnP-Geräte.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, List, Optional, Sequence


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
    return DeviceScope.UNKNOWN


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

    class PRINTER_INFO_4(ctypes.Structure):
        _fields_ = [
            ("pPrinterName", wintypes.LPWSTR),
            ("pServerName", wintypes.LPWSTR),
            ("Attributes", wintypes.DWORD),
        ]

    level = 4
    flags = PRINTER_ENUM_LOCAL | PRINTER_ENUM_CONNECTIONS
    needed = wintypes.DWORD(0)
    returned = wintypes.DWORD(0)
    winspool.EnumPrintersW(
        flags, None, level, None, 0, ctypes.byref(needed), ctypes.byref(returned)
    )
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
        warnings.append("Winspool EnumPrinters fehlgeschlagen.")
        return [], warnings

    count = int(returned.value)
    arr_t = PRINTER_INFO_4 * count
    arr = arr_t.from_buffer(buf)
    out: List[DeviceInfo] = []
    for i in range(count):
        name = str(arr[i].pPrinterName or "").strip()
        if not name:
            continue
        server = str(arr[i].pServerName or "").strip()
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


def _powershell_json(script: str, *, timeout: float = 25.0) -> tuple[Optional[object], Optional[str]]:
    """PowerShell → JSON (Windows)."""
    if platform.system() != "Windows":
        return None, None
    ps = shutil.which("powershell") or shutil.which("pwsh")
    if not ps:
        return None, "PowerShell nicht gefunden"
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
        )
    except Exception as e:
        return None, str(e)
    raw = (proc.stdout or "").strip()
    if proc.returncode != 0 and not raw:
        err = (proc.stderr or "").strip() or f"exit {proc.returncode}"
        return None, err
    if not raw:
        return [], None
    import json

    try:
        data = json.loads(raw)
    except Exception as e:
        return None, f"JSON-Parse: {e}"
    return data, None


def _list_scanners_windows() -> tuple[List[DeviceInfo], List[str], List[str]]:
    """Windows-Scanner: WIA-Geräte + PnP Image-Klasse."""
    warnings: List[str] = []
    notes: List[str] = ["Windows: WIA/PnP-Scannererkennung"]
    out: List[DeviceInfo] = []

    # 1) WIA DeviceManager (COM via PowerShell)
    wia_script = r"""
$ErrorActionPreference = 'Stop'
try {
  $dm = New-Object -ComObject WIA.DeviceManager
  $items = @()
  foreach ($d in @($dm.DeviceInfos)) {
    $name = [string]$d.Properties['Name'].Value
    $id = [string]$d.DeviceID
    $type = [int]$d.Type
    if ($type -eq 1 -or $type -eq 65537) {  # Scanner / mixed
      $items += [pscustomobject]@{ Name = $name; DeviceID = $id; Backend = 'WIA' }
    }
  }
  if (-not $items) { '[]' } else { $items | ConvertTo-Json -Compress -Depth 3 }
} catch {
  Write-Output ('ERR:' + $_.Exception.Message)
}
"""
    data, err = _powershell_json(wia_script)
    if err:
        warnings.append(f"WIA: {err}")
    elif isinstance(data, str) and data.startswith("ERR:"):
        warnings.append(data)
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
                if "network" in did.lower() or did.lower().startswith("\\\\")
                else DeviceScope.LOCAL
            )
            out.append(
                DeviceInfo(
                    kind=DeviceKind.SCANNER,
                    name=name,
                    device_id=did,
                    scope=scope,
                    backend="WIA",
                )
            )

    # 2) PnP Image / Scanner class (ergänzt Netzwerk-USB-über-IP etc.)
    pnp_script = r"""
$ErrorActionPreference = 'SilentlyContinue'
$items = @(Get-PnpDevice -Class Image,Camera -Status OK,Unknown,Error -ErrorAction SilentlyContinue |
  Where-Object { $_.FriendlyName -match 'scan|wia|twain|epson|canon|brother|hp |fujitsu|kodak|xerox|ricoh' -or $_.Class -eq 'Image' } |
  Select-Object -Property FriendlyName, InstanceId, Class)
if (-not $items) {
  $items = @(Get-CimInstance Win32_PnPEntity -ErrorAction SilentlyContinue |
    Where-Object { $_.PNPClass -eq 'Image' -or $_.Name -match 'Scanner|Scan' } |
    Select-Object @{N='FriendlyName';E={$_.Name}}, @{N='InstanceId';E={$_.PNPDeviceID}}, @{N='Class';E={$_.PNPClass}})
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
            scope = DeviceScope.NETWORK if "SWD\\PRINTENUM" in did.upper() or "USBPRINT" in did.upper() and "IP" in name.upper() else DeviceScope.LOCAL
            if re.search(r"network|netzwerk|\\\\|ipp|http", name, re.I):
                scope = DeviceScope.NETWORK
            out.append(
                DeviceInfo(
                    kind=DeviceKind.SCANNER,
                    name=name,
                    device_id=did,
                    scope=scope,
                    backend="PnP",
                    details=str(row.get("Class") or ""),
                )
            )

    # 3) Optional: python WIA via win32com
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
                name = str(d.Properties("Name").Value)
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
        warnings.append(
            "Keine Scanner erkannt. WIA/TWAIN-Treiber prüfen oder Bilder importieren."
        )
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
    # device `name' is a … scanner
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
    if system == "Windows":
        return _list_scanners_windows()
    return _list_scanners_sane()


def list_printers() -> tuple[List[DeviceInfo], List[str]]:
    printers, warnings = list_printers_qt()
    extra, w2 = _list_printers_winspool()
    warnings.extend(w2)
    return _dedupe(list(printers) + list(extra)), warnings


def discover_devices(
    *,
    include_printers: bool = True,
    include_scanners: bool = True,
    on_progress: Optional[Callable[[str], None]] = None,
) -> DeviceDiscoveryResult:
    """Geräte neu suchen (Refresh/Rescan)."""
    result = DeviceDiscoveryResult()
    if include_printers:
        if on_progress:
            on_progress("Drucker werden gesucht…")
        printers, warnings = list_printers()
        result.printers = printers
        result.warnings.extend(warnings)
        result.backend_notes.append(f"Drucker: {len(printers)}")
    if include_scanners:
        if on_progress:
            on_progress("Scanner werden gesucht…")
        scanners, warnings, notes = list_scanners()
        result.scanners = scanners
        result.warnings.extend(warnings)
        result.backend_notes.extend(notes)
        result.backend_notes.append(f"Scanner: {len(scanners)}")
    return result


def printer_names_for_print() -> List[str]:
    """Kurze Namensliste für Druckziel-Auswahl."""
    printers, _ = list_printers()
    return [p.name for p in printers]


# Umgebungs-Hinweis für Docs / UI
WINDOWS_SCAN_DEPS_HINT = (
    "Windows Scan/OCR:\n"
    "  • Tesseract: winget install UB-Mannheim.TesseractOCR (deu+eng anhaken)\n"
    "  • Python: pip install pytesseract\n"
    "  • Scanner: WIA-Treiber des Herstellers (TWAIN optional)\n"
    "  • Ohne Scanner-Hardware: Bilder/Fotos im Scan-Dialog importieren"
)
