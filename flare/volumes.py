"""Laufwerke und lokale Cloud-Ordner.

Die Auswahl ist reine Logik: Tests übergeben Laufwerkslisten und Ordner.
Win32 wird nur auf Windows aufgerufen, und nur um diese Listen zu füllen.
Es gibt keinen Zugriff auf Hersteller-APIs und keinen Download von Dateiinhalten.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, NamedTuple

from flare.paths import is_inside, place_key

# GetDriveTypeW.
DRIVE_UNKNOWN = 0
DRIVE_NO_ROOT_DIR = 1
DRIVE_REMOVABLE = 2
DRIVE_FIXED = 3
DRIVE_REMOTE = 4
DRIVE_CDROM = 5
DRIVE_RAMDISK = 6

# GetFileAttributes: Platzhalter, deren Bytes nicht gelesen werden dürfen.
FILE_ATTRIBUTE_OFFLINE = 0x1000
FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x00400000
_OFFLINE_ATTRIBUTES = FILE_ATTRIBUTE_OFFLINE | FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS

# Externe Platten wie heiße Ordner, Netzfreigaben wie das Benutzerprofil.
TIER_VOLUME = 1
TIER_NETWORK = 2

_ONEDRIVE_ENV = ("OneDrive", "OneDriveConsumer", "OneDriveCommercial")


class DriveInfo(NamedTuple):
    root: str
    drive_type: int
    label: str | None
    readable: bool


def normalize_drive_root(value: str) -> str:
    """`C:\\Windows`, `c:` und `E:/` werden zu `C:\\` bzw. `E:\\`."""
    text = value.strip()
    if len(text) >= 2 and text[1] == ":":
        return text[0].upper() + ":\\"
    slashed = text.replace("/", "\\")
    if len(slashed) >= 2 and slashed[1] == ":":
        return slashed[0].upper() + ":\\"
    return text


def index_network_enabled(config: Mapping[str, Any] | None) -> bool:
    if not isinstance(config, dict):
        return False
    return bool(config.get("index_network", False))


def exclude_drive_list(config: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(config, dict):
        return []
    raw = config.get("exclude_drives", [])
    if not isinstance(raw, list):
        return []
    return [item.strip() for item in raw if isinstance(item, str) and item.strip()]


def is_excluded(root: str, label: str, exclude: Sequence[str]) -> bool:
    """Laufwerksstamm wie `E:\\` oder die Datenträgerbezeichnung."""
    root_key = normalize_drive_root(root).casefold()
    label_key = label.strip().casefold()
    for raw in exclude:
        if not isinstance(raw, str):
            continue
        item = raw.strip()
        if not item:
            continue
        if normalize_drive_root(item).casefold() == root_key:
            return True
        if label_key and item.casefold() == label_key:
            return True
    return False


def tier_for_drive_type(drive_type: int, *, index_network: bool) -> int | None:
    """Tier, oder None wenn das Laufwerk nicht gelesen wird.

    CD-ROM, RAM und unbekannte Typen entfallen. Netzlaufwerke nur auf Wunsch,
    dann Tier 2: Namen ohne Inhalt, dieselbe Kost wie das Benutzerprofil.
    """
    if drive_type == DRIVE_REMOVABLE:
        return TIER_VOLUME
    if drive_type == DRIVE_FIXED:
        return TIER_VOLUME
    if drive_type == DRIVE_REMOTE:
        return TIER_NETWORK if index_network else None
    return None


def tracked_drives(
    drives: Sequence[DriveInfo],
    *,
    system_drive: str,
    index_network: bool = False,
    exclude: Sequence[str] | None = None,
) -> list[tuple[str, int, bool]]:
    """Laufwerksbuchstaben, die im Blick bleiben: `(Stamm, Tier, lesen)`.

    `lesen` ist falsch, wenn GetVolumeInformation fehlschlägt oder der Stamm
    nicht lesbar ist. Der Buchstabe bleibt trotzdem, damit eine kurze Störung
    den Baum nicht löscht. Weg ist er erst, wenn er nicht mehr gemeldet wird,
    ausgeschlossen ist oder der Typ nicht in den Index gehört.
    Das Systemlaufwerk bleibt draußen. Ohne erkannten Systemdatenträger
    entfallen auch feste Platten, damit nicht versehentlich `C:\\` komplett
    gelesen wird.
    """
    skipped = list(exclude or [])
    system = normalize_drive_root(system_drive) if system_drive else ""
    chosen: list[tuple[str, int, bool]] = []
    seen: set[str] = set()
    for drive in drives:
        root = normalize_drive_root(drive.root)
        if not root or root in seen:
            continue
        if system and root.casefold() == system.casefold():
            continue
        if not system and drive.drive_type == DRIVE_FIXED:
            continue
        tier = tier_for_drive_type(drive.drive_type, index_network=index_network)
        if tier is None:
            continue
        label = drive.label or ""
        if is_excluded(root, label, skipped):
            continue
        seen.add(root)
        chosen.append((root, tier, drive.label is not None and drive.readable))
    return chosen


def select_drive_roots(
    drives: Sequence[DriveInfo],
    *,
    system_drive: str,
    index_network: bool = False,
    exclude: Sequence[str] | None = None,
) -> list[tuple[str, int]]:
    """Laufwerke, die jetzt gelesen werden."""
    return [
        (root, tier)
        for root, tier, walk in tracked_drives(
            drives,
            system_drive=system_drive,
            index_network=index_network,
            exclude=exclude,
        )
        if walk
    ]


def is_offline_stat(st: object) -> bool:
    """FILE_ATTRIBUTE_OFFLINE oder RECALL_ON_DATA_ACCESS an einem stat-Objekt."""
    attrs = getattr(st, "st_file_attributes", None)
    if attrs is None:
        return False
    try:
        value = int(attrs)
    except (TypeError, ValueError):
        return False
    return bool(value & _OFFLINE_ATTRIBUTES)


def is_offline_file(path: str, st: object, *, marker_dir: bool = False) -> bool:
    """Platzhalter nicht öffnen. Unter Linux reicht eine Markierung im Test."""
    if is_offline_stat(st):
        return True
    if not marker_dir:
        return False
    marker = os.path.join(os.path.dirname(path), ".flare-offline", os.path.basename(path))
    try:
        return os.path.isfile(marker)
    except OSError:
        return False


def should_sample_content(*, enabled: bool, tier: int, offline: bool) -> bool:
    """Inhalt nur in heißen Bäumen, und nie bei Nur-online-Platzhaltern.

    Tier 2 (Benutzerprofil und optionale Netzlaufwerke) liefert nur Namen.
    """
    return bool(enabled) and tier <= 1 and not offline


def dropbox_paths_from_info(text: str) -> list[str]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, dict):
        return []
    found: list[str] = []
    for value in payload.values():
        if not isinstance(value, dict):
            continue
        path = value.get("path")
        if isinstance(path, str) and path.strip():
            found.append(os.path.expandvars(path.strip()))
    return found


def discover_cloud_roots(
    env: Mapping[str, str],
    *,
    exists: Callable[[str], bool],
    read_text: Callable[[str], str | None],
    registry_folders: Sequence[str] = (),
    listdir: Callable[[str], Sequence[str]] | None = None,
    existing_roots: Sequence[str] = (),
) -> list[str]:
    """Lokale Spiegel von OneDrive, Dropbox und Google Drive.

    Dieselbe Stelle (realpath) nur einmal. Liegt ein Kandidat in einem
    anderen Kandidaten, bleibt der äußere Ordner. Bekannte Ordner, die
    bereits dieselbe Stelle sind, werden nicht erneut eingetragen.
    """
    listing = listdir or (lambda _path: [])
    candidates = _cloud_candidates(env, exists, listing, read_text, registry_folders)
    taken = {place_key(path) for path in existing_roots if path}
    unique: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        expanded = os.path.expandvars(raw).strip()
        if not expanded:
            continue
        try:
            present = exists(expanded)
        except OSError:
            continue
        if not present:
            continue
        key = place_key(expanded)
        if key in seen or key in taken:
            continue
        seen.add(key)
        unique.append(key)
    return sorted(_drop_nested(unique), key=str.casefold)


def _cloud_candidates(
    env: Mapping[str, str],
    exists: Callable[[str], bool],
    listdir: Callable[[str], Sequence[str]],
    read_text: Callable[[str], str | None],
    registry_folders: Sequence[str],
) -> list[str]:
    home = env.get("USERPROFILE") or env.get("HOME") or ""
    found: list[str] = []
    for key in _ONEDRIVE_ENV:
        raw = env.get(key, "")
        if raw.strip():
            found.append(raw.strip())
    found.extend(registry_folders)
    if home:
        found.append(os.path.join(home, "Dropbox"))
        found.append(os.path.join(home, "Google Drive"))
        found.append(os.path.join(home, "Google Drive", "My Drive"))
    for info_path in _dropbox_info_paths(env):
        try:
            text = read_text(info_path)
        except OSError:
            text = None
        if text:
            found.extend(dropbox_paths_from_info(text))
    local = env.get("LOCALAPPDATA", "")
    if local:
        found.extend(_drivefs_my_drive(local, exists, listdir))
    return found


def _dropbox_info_paths(env: Mapping[str, str]) -> list[str]:
    paths: list[str] = []
    appdata = env.get("APPDATA", "")
    local = env.get("LOCALAPPDATA", "")
    if appdata:
        paths.append(os.path.join(appdata, "Dropbox", "info.json"))
    if local:
        paths.append(os.path.join(local, "Dropbox", "info.json"))
    return paths


def _drivefs_my_drive(
    local: str,
    exists: Callable[[str], bool],
    listdir: Callable[[str], Sequence[str]],
) -> list[str]:
    root = os.path.join(local, "Google", "DriveFS")
    try:
        if not exists(root):
            return []
        names = list(listdir(root))
    except OSError:
        return []
    found: list[str] = []
    for name in names:
        child = os.path.join(root, name)
        if name.casefold() == "my drive":
            found.append(child)
            continue
        try:
            if not exists(child):
                continue
            inner = list(listdir(child))
        except OSError:
            continue
        for leaf in inner:
            if leaf.casefold() == "my drive":
                found.append(os.path.join(child, leaf))
    return found


def _drop_nested(paths: Sequence[str]) -> list[str]:
    ordered = sorted(paths, key=lambda path: (len(path), path))
    kept: list[str] = []
    for path in ordered:
        if any(is_inside(path, parent) for parent in kept):
            continue
        kept.append(path)
    return kept


def windows_system_drive() -> str:
    """Systemlaufwerk über GetWindowsDirectoryW, danach die Umgebungsvariablen."""
    if sys.platform != "win32":
        return ""
    import ctypes

    kernel = _kernel32()
    buf = ctypes.create_unicode_buffer(260)
    got = kernel.GetWindowsDirectoryW(buf, len(buf))
    if 0 < got < len(buf):
        root = normalize_drive_root(buf.value)
        if root:
            return root
    for key in ("SystemDrive", "SystemRoot", "WINDIR"):
        raw = os.environ.get(key, "")
        if raw.strip():
            root = normalize_drive_root(raw)
            if root:
                return root
    return ""


def list_windows_drives() -> list[DriveInfo] | None:
    """None, wenn GetLogicalDriveStringsW fehlschlägt. Sonst jedes Laufwerk."""
    if sys.platform != "win32":
        return []
    kernel = _kernel32()
    letters = _logical_drives(kernel)
    if letters is None:
        return None
    found: list[DriveInfo] = []
    for root in letters:
        try:
            drive_type = int(kernel.GetDriveTypeW(root))
        except OSError:
            continue
        label = _volume_label(kernel, root)
        readable = _root_readable(root)
        found.append(DriveInfo(root, drive_type, label, readable))
    return found


def read_onedrive_folders() -> list[str]:
    """UserFolder unter HKCU\\Software\\Microsoft\\OneDrive, wenn lesbar."""
    if sys.platform != "win32":
        return []
    import winreg

    found: list[str] = []

    def take(key: Any) -> None:
        try:
            value, _typ = winreg.QueryValueEx(key, "UserFolder")
        except OSError:
            return
        if isinstance(value, str) and value.strip():
            found.append(os.path.expandvars(value.strip()))

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\OneDrive") as root:
            take(root)
            try:
                with winreg.OpenKey(root, "Accounts") as accounts:
                    index = 0
                    while True:
                        try:
                            name = winreg.EnumKey(accounts, index)
                        except OSError:
                            break
                        index += 1
                        try:
                            with winreg.OpenKey(accounts, name) as account:
                                take(account)
                        except OSError:
                            continue
            except OSError:
                pass
    except OSError:
        return found
    return found


def windows_cloud_roots() -> list[str]:
    if sys.platform != "win32":
        return []
    try:
        registry = read_onedrive_folders()
    except OSError:
        registry = []
    from flare.crawl import _user_dirs, application_roots

    existing = [path for path, _tier in _user_dirs() + application_roots()]
    return discover_cloud_roots(
        os.environ,
        exists=os.path.isdir,
        read_text=_read_text,
        registry_folders=registry,
        listdir=os.listdir,
        existing_roots=existing,
    )


def _windows_drive_view() -> tuple[list[DriveInfo], str] | None:
    """None, wenn die Laufwerksliste selbst fehlschlägt."""
    if sys.platform != "win32":
        return None
    drives = list_windows_drives()
    if drives is None:
        return None
    return drives, windows_system_drive()


def drive_roots_for_config(
    *,
    index_network: bool = False,
    exclude: Sequence[str] | None = None,
) -> list[tuple[str, int]]:
    if sys.platform != "win32":
        return []
    try:
        view = _windows_drive_view()
    except OSError:
        return []
    if view is None:
        return []
    drives, system = view
    return select_drive_roots(
        drives,
        system_drive=system,
        index_network=index_network,
        exclude=list(exclude or []),
    )


def drive_snapshot_for_config(
    *,
    index_network: bool = False,
    exclude: Sequence[str] | None = None,
) -> list[tuple[str, int, bool]]:
    """Für die Nachschau. Wirft OSError, wenn die Liste nicht lesbar ist."""
    if sys.platform != "win32":
        return []
    view = _windows_drive_view()
    if view is None:
        raise OSError("drive list unavailable")
    drives, system = view
    return tracked_drives(
        drives,
        system_drive=system,
        index_network=index_network,
        exclude=list(exclude or []),
    )


def _read_text(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return None


def _root_readable(root: str) -> bool:
    try:
        iterator = os.scandir(root)
    except OSError:
        return False
    with iterator:
        return True


def _volume_label(kernel: Any, root: str) -> str | None:
    """None, wenn GetVolumeInformation fehlschlägt. Leerer Name ist gültig."""
    import ctypes

    name = ctypes.create_unicode_buffer(261)
    filesystem = ctypes.create_unicode_buffer(261)
    try:
        ok = kernel.GetVolumeInformationW(root, name, len(name), None, None, None, filesystem, len(filesystem))
    except OSError:
        return None
    if not ok:
        return None
    return name.value


def _logical_drives(kernel: Any) -> list[str] | None:
    import ctypes

    needed = kernel.GetLogicalDriveStringsW(0, None)
    if not needed:
        return None
    buf = ctypes.create_unicode_buffer(int(needed) + 1)
    got = kernel.GetLogicalDriveStringsW(len(buf), buf)
    if not got:
        return None
    return [part for part in buf[: int(got)].split("\x00") if part]


_KERNEL: Any = None


def _kernel32() -> Any:
    global _KERNEL
    if _KERNEL is not None:
        return _KERNEL
    import ctypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetLogicalDriveStringsW.argtypes = [ctypes.c_uint32, ctypes.c_wchar_p]
    kernel.GetLogicalDriveStringsW.restype = ctypes.c_uint32
    kernel.GetDriveTypeW.argtypes = [ctypes.c_wchar_p]
    kernel.GetDriveTypeW.restype = ctypes.c_uint32
    kernel.GetVolumeInformationW.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_wchar_p,
        ctypes.c_uint32,
    ]
    kernel.GetVolumeInformationW.restype = ctypes.c_int
    kernel.GetWindowsDirectoryW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32]
    kernel.GetWindowsDirectoryW.restype = ctypes.c_uint32
    _KERNEL = kernel
    return kernel
