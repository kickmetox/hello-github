"""Gestufter Katalog.

Heiße Ordner (Programme, Schreibtisch, Dokumente) werden klein gehalten und bei
Änderungen gezielt nachgelesen. Kalte Ordner laufen im Leerlauf. Unveränderte
Ordner werden über die gespeicherte Kindliste übersprungen, ohne readdir.
"""

from __future__ import annotations

import heapq
import logging
import os
import stat
import sys
import threading
import time
from collections.abc import Callable
from contextlib import nullcontext
from pathlib import Path
from typing import Any

from flare.governor import Governor
from flare.launch import is_secret_name, parse_lnk
from flare.paths import is_inside, norm, parent_of, place_key
from flare.store import Index
from flare.volumes import DRIVE_PROBE_S, is_offline_file, run_within, should_sample_content

log = logging.getLogger("flare")

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".cache",
    ".npm",
    ".cargo",
    ".rustup",
    ".tox",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "site-packages",
    "target",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "$recycle.bin",
    "system volume information",
    "windows",
    "proc",
    "sys",
    "dev",
}

TEXT_EXT = {
    ".txt",
    ".md",
    ".rst",
    ".org",
    ".py",
    ".json",
    ".csv",
    ".log",
    ".toml",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
    ".xml",
    ".html",
    ".css",
    ".js",
    ".ts",
}

RESCHEDULE = {0: 90.0, 1: 300.0, 2: 1200.0}


def roots_worth_watching(
    roots: list[tuple[str, int]],
    quiet: list[str],
) -> list[str]:
    """Heiße Ordner beobachten. Platte, USB, Cloud und Netz bleiben beim Takt."""
    skip = {norm(path) for path in quiet}
    return [path for path, tier in roots if tier <= 1 and norm(path) not in skip]
# GetLogicalDriveStringsW / GetDriveTypeW, kein enger Takt.
DRIVE_POLL_S = 12.0
# Eine Namensebene auf einem gemappten Laufwerk. Hängt die Freigabe, weitergehen.
SHALLOW_LIST_S = DRIVE_PROBE_S
# Gleiche mtime im selben Zeitquant verdeckt ein schnelles Löschen. Spätestens
# nach diesem Alter wird der Ordner trotzdem neu gelesen.
READDIR_MAX_AGE_NS = 15 * 60 * 1_000_000_000
_PATH_DIR = ":path"


def should_skip_dir(name: str) -> bool:
    lowered = name.casefold()
    if lowered in SKIP_DIRS:
        return True
    if name.startswith(".") and name not in {".", ".."}:
        return True
    return False


def should_skip_file(name: str) -> bool:
    if is_secret_name(name):
        return True
    lowered = name.casefold()
    if lowered in {"thumbs.db", "desktop.ini", ".ds_store"}:
        return True
    return lowered.endswith("~") or lowered.endswith(".tmp")


def collect_root_names(root: str | Path) -> list[dict[str, Any]]:
    """Datei- und Ordnernamen unter einem Ordner. Kein Dateiinhalt.

    Dieselben Stellen (realpath) zählen einmal. Versteckte Ordner, node_modules
    und Geheimnisdateien entfallen, der angegebene Ordner selbst nicht.
    """
    folder = os.fspath(root)
    if not os.path.isdir(folder):
        raise ValueError(f"Ordner fehlt: {folder}")
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    root_key = place_key(folder)
    _consider_name(folder, True, seen, items, keep_skipped=root_key)
    stack = [folder]
    while stack:
        current = stack.pop()
        try:
            iterator = os.scandir(current)
        except OSError:
            continue
        with iterator:
            for entry in iterator:
                try:
                    is_dir = entry.is_dir(follow_symlinks=False)
                    is_file = entry.is_file(follow_symlinks=False)
                except OSError:
                    continue
                if is_dir:
                    if should_skip_dir(entry.name):
                        continue
                    if _consider_name(entry.path, True, seen, items):
                        stack.append(entry.path)
                    continue
                if is_file:
                    _consider_name(entry.path, False, seen, items)
                    continue
                try:
                    linked_file = entry.is_file(follow_symlinks=True)
                except OSError:
                    linked_file = False
                if not linked_file:
                    continue
                # Dieselbe Stelle im Ordner nicht doppelt. Ein Verweis nach
                # außen bleibt als Name erhalten.
                target = place_key(entry.path)
                if target == root_key or is_inside(target, folder):
                    continue
                _consider_name(entry.path, False, seen, items)
    return items


def collect_list_names(list_path: str | Path) -> list[dict[str, Any]]:
    """Eine UTF-8-Liste, ein Pfad pro Zeile. Leerzeilen und #-Kommentare entfallen.

    Nur vorhandene Pfade werden Namen. Ordner werden nicht rekursiv gelesen.
    """
    file = Path(list_path)
    if not file.is_file():
        raise ValueError(f"Liste fehlt: {file}")
    try:
        text = file.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise ValueError(f"Liste ist kein UTF-8: {file}") from exc
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if not os.path.exists(line):
            continue
        is_dir = os.path.isdir(line)
        name = os.path.basename(norm(line).rstrip("\\/")) or line
        if is_dir:
            if should_skip_dir(name):
                continue
        elif should_skip_file(name):
            continue
        _consider_name(line, is_dir, seen, items)
    return items


def _consider_name(
    path: str,
    is_dir: bool,
    seen: set[str],
    items: list[dict[str, Any]],
    keep_skipped: str | None = None,
) -> bool:
    key = place_key(path)
    if key in seen:
        return False
    name = os.path.basename(norm(path).rstrip("\\/")) or path
    if keep_skipped != key:
        if is_dir and should_skip_dir(name):
            return False
        if not is_dir and should_skip_file(name):
            return False
    try:
        st = os.stat(path, follow_symlinks=False)
    except OSError:
        return False
    seen.add(key)
    stored = norm(path)
    items.append(
        {
            "kind": "dir" if is_dir else "file",
            "name": name,
            "path": stored,
            "dir": parent_of(stored),
            "ext": "" if is_dir else Path(name).suffix.casefold(),
            "launch": None,
            "mtime_ns": getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)),
            "size": 0 if is_dir else int(st.st_size),
            "tier": 1,
        }
    )
    return True


class _Listed:
    """Eintrag einer beendeten, zeitlich begrenzten Verzeichnisliste."""

    def __init__(self, name: str, path: str, is_dir: bool, is_file: bool) -> None:
        self.name = name
        self.path = path
        self._is_dir = is_dir
        self._is_file = is_file

    def is_dir(self, follow_symlinks: bool = False) -> bool:
        return self._is_dir

    def is_file(self, follow_symlinks: bool = False) -> bool:
        return self._is_file

    def stat(self, follow_symlinks: bool = False) -> os.stat_result:
        return os.stat(self.path, follow_symlinks=follow_symlinks)


def list_dir_quick(path: str, timeout: float = SHALLOW_LIST_S) -> list[_Listed] | None:
    """Namen einer Ebene, oder None wenn das Laufwerk nicht rechtzeitig antwortet."""

    def read() -> list[_Listed]:
        found: list[_Listed] = []
        with os.scandir(path) as iterator:
            for entry in iterator:
                try:
                    is_dir = entry.is_dir(follow_symlinks=False)
                    is_file = entry.is_file(follow_symlinks=False)
                except OSError:
                    continue
                found.append(_Listed(entry.name, entry.path, is_dir, is_file))
        return found

    rows = run_within(f"list:{path}", read, timeout)
    if not isinstance(rows, list):
        return None
    return rows


def stat_quick(path: str, timeout: float = SHALLOW_LIST_S) -> os.stat_result | None:
    st = run_within(f"stat:{path}", lambda: os.stat(path, follow_symlinks=False), timeout)
    if st is None:
        return None
    return st


def read_text_sample(path: str, size: int) -> str | None:
    if size <= 0 or size > 65536:
        return None
    if Path(path).suffix.casefold() not in TEXT_EXT:
        return None
    try:
        with open(path, "rb") as handle:
            blob = handle.read(4096)
    except OSError:
        return None
    if b"\x00" in blob:
        return None
    return blob.decode("utf-8", "replace")


# Known Folder IDs: Desktop, Documents, Downloads, Pictures, Music, Videos, Profile.
_KNOWN_FOLDERS = (
    (0, "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}"),
    (1, "{FDD39AD0-476A-45D4-8CDE-E9A6B0C1F19E}"),
    (1, "{374DE290-123F-4565-9164-39C4925E467B}"),
    (1, "{33E28130-4E1C-4673-AEFE-9B033B0F0A3A}"),
    (1, "{4BD8D571-6D19-48D3-BE97-422220080E43}"),
    (1, "{18989B1D-99B5-455B-841C-AB7C74E4DDFC}"),
    (2, "{5E6C858F-0E22-4760-9AFE-EA3317B67173}"),
)


def _known_folder(guid: str) -> str | None:
    import ctypes
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    folder = GUID()
    ole32 = ctypes.WinDLL("ole32", use_last_error=True)
    if ole32.CLSIDFromString(guid, ctypes.byref(folder)) != 0:
        return None
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    shell32.SHGetKnownFolderPath.argtypes = [
        ctypes.POINTER(GUID),
        wintypes.DWORD,
        wintypes.HANDLE,
        ctypes.POINTER(ctypes.c_wchar_p),
    ]
    shell32.SHGetKnownFolderPath.restype = ctypes.HRESULT
    ptr = ctypes.c_wchar_p()
    if shell32.SHGetKnownFolderPath(ctypes.byref(folder), 0, None, ctypes.byref(ptr)) != 0:
        return None
    path = ptr.value
    ole32.CoTaskMemFree(ptr)
    return path or None


def _user_dirs() -> list[tuple[str, int]]:
    if sys.platform != "win32":
        return []
    found: list[tuple[str, int]] = []
    for tier, guid in _KNOWN_FOLDERS:
        try:
            path = _known_folder(guid)
        except OSError:
            path = None
        if path:
            found.append((path, tier))
    if found:
        return found
    profile = Path(os.environ.get("USERPROFILE", str(Path.home())))
    for tier, name in (
        (0, "Desktop"),
        (1, "Documents"),
        (1, "Downloads"),
        (1, "Pictures"),
        (1, "Music"),
        (1, "Videos"),
    ):
        found.append((str(profile / name), tier))
    found.append((str(profile), 2))
    return found


def application_roots() -> list[tuple[str, int]]:
    if sys.platform != "win32":
        return []
    appdata = os.environ.get("APPDATA", "")
    programdata = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    candidates = [
        Path(appdata) / "Microsoft" / "Windows" / "Start Menu" if appdata else None,
        Path(programdata) / "Microsoft" / "Windows" / "Start Menu",
    ]
    return [(str(candidate), 0) for candidate in candidates if candidate is not None]


def dedupe_roots(pairs: list[tuple[str, int]]) -> list[tuple[str, int]]:
    ordered = sorted(pairs, key=lambda item: (item[1], item[0]))
    kept: list[tuple[str, int]] = []
    seen: set[str] = set()
    for raw, tier in ordered:
        if not raw:
            continue
        if not os.path.isdir(raw):
            continue
        path = norm(raw)
        key = place_key(raw)
        if key in seen:
            continue
        seen.add(key)
        kept.append((path, tier))
    return kept


def merge_volume_roots(
    base: list[tuple[str, int]],
    drives: list[tuple[str, int]] | None = None,
    cloud: list[str] | None = None,
) -> tuple[list[tuple[str, int]], list[str]]:
    """Wurzeln plus die Laufwerke, die beim Abziehen wieder entfernt werden."""
    drive_pairs = list(drives or [])
    cloud_pairs = [(path, 1) for path in (cloud or []) if path]
    merged = dedupe_roots(list(base) + cloud_pairs + drive_pairs)
    drive_keys = {place_key(path) for path, _tier in drive_pairs}
    dynamic = [path for path, _tier in merged if place_key(path) in drive_keys]
    return merged, dynamic


def default_roots(extra: list[tuple[str, int]] | None = None) -> list[tuple[str, int]]:
    pairs = _user_dirs() + application_roots()
    if extra:
        pairs.extend(extra)
    return dedupe_roots(pairs)


class Crawler:
    def __init__(
        self,
        index: Index,
        governor: Governor,
        roots: list[tuple[str, int]],
        stop: threading.Event,
        *,
        content: bool = True,
        index_path: bool = True,
        data_dir: str | None = None,
        watcher: Any | None = None,
        drive_poll: Callable[[], list[tuple[str, int]]] | None = None,
        dynamic_roots: list[str] | None = None,
        names_only: list[str] | None = None,
        shallow_roots: list[str] | None = None,
    ) -> None:
        self.index = index
        self.governor = governor
        self.roots = [(norm(path), tier) for path, tier in roots]
        self.stop = stop
        self.content = content
        self.index_path = index_path
        self.data_dir = norm(data_dir) if data_dir else ""
        self.watcher = watcher
        self.phase = "idle"
        self.readdirs = 0
        self._lock = threading.Lock()
        self._heap: list[tuple[int, int, str]] = []
        self._desired: dict[str, tuple[int, int, int, bool]] = {}
        self._seq = 0
        self._next_full = {0: 0.0, 1: 0.0, 2: 0.0}
        self._claimed = list(self.roots)
        self.readdir_max_age_ns = READDIR_MAX_AGE_NS
        self._drive_poll = drive_poll
        self._next_drive_poll = 0.0
        dynamic_norm = {norm(path) for path in (dynamic_roots or [])}
        self._static_roots = {path for path, _tier in self.roots if path not in dynamic_norm}
        self._dynamic = {path: tier for path, tier in self.roots if path in dynamic_norm}
        # Laufwerke und Cloud-Spiegel: nur Namen, Nachschau höchstens im Tier-1-Takt.
        self._names_only = {norm(path) for path in (names_only or [])}
        self._names_only.update(self._dynamic)
        # Gemappte Buchstaben ohne index_network: nur die Namen direkt am Stamm.
        self._shallow = {norm(path) for path in (shallow_roots or [])}
        self._names_only.update(self._shallow)
        self._write_gate = threading.Lock()

    def pause_writes(self) -> None:
        """Scans anhalten, solange der laufende Index ausgetauscht wird."""
        self._write_gate.acquire()

    def resume_writes(self) -> None:
        self._write_gate.release()

    def add(self, path: str, tier: int, *, descend: bool, priority: int | None = None) -> None:
        path = norm(path) if not path.startswith(":") else path
        pr = tier if priority is None else priority
        with self._lock:
            current = self._desired.get(path)
            seq = self._seq
            self._seq += 1
            if current is not None:
                pr = min(pr, current[0])
                descend = descend or current[3]
                tier = min(tier, current[2])
            self._desired[path] = (pr, seq, tier, descend)
            heapq.heappush(self._heap, (pr, seq, path))

    def _pop(self) -> tuple[str, int, bool] | None:
        with self._lock:
            while self._heap:
                pr, seq, path = heapq.heappop(self._heap)
                current = self._desired.get(path)
                if current is None or current[0] != pr or current[1] != seq:
                    continue
                del self._desired[path]
                return path, current[2], current[3]
        return None

    def queued(self) -> int:
        with self._lock:
            return len(self._desired)

    def prime(self) -> None:
        now = time.monotonic()
        for tier, delay in RESCHEDULE.items():
            self._next_full[tier] = now + delay
        for path, tier in self.roots:
            self.add(path, tier, descend=self._root_descend(path), priority=tier)
        if self.index_path:
            self.ingest_path()

    def enqueue_all(self) -> None:
        for path, tier in self.roots:
            self.add(path, tier, descend=self._root_descend(path), priority=tier)
        if self.index_path:
            self.ingest_path()

    def _root_descend(self, path: str) -> bool:
        return path not in self._shallow

    def poke(self, path: str, descend: bool = False) -> None:
        try:
            self.index.mark_dirty(path)
        except Exception:
            log.debug("dirty failed", exc_info=True)
        tier = 2
        for root, root_tier in self._claimed:
            if path == root or is_inside(path, root):
                tier = min(tier, root_tier)
        self.add(path, tier, descend=descend, priority=-1)
        self.governor.wake.set()

    def blocked(self, path: str, tier: int) -> bool:
        for root, root_tier in self._claimed:
            if root_tier < tier and (path == root or is_inside(path, root)):
                return True
        return False

    def run(self) -> None:
        self.prime()
        while not self.stop.is_set():
            with self._write_gate:
                self.poll_drives()
                item = self._pop()
                if item is not None:
                    path, tier, descend = item
                    self.phase = "scan"
                    started = time.perf_counter()
                    try:
                        if path == _PATH_DIR:
                            self.ingest_path()
                        else:
                            self.scan_dir(path, tier, descend)
                    except Exception:
                        log.exception("scan failed: %s", path)
                    if self.queued() == 0:
                        self.phase = "idle"
            if item is None:
                self.phase = "idle"
                self._maybe_schedule()
                if self.stop.wait(0.4):
                    return
                continue
            self.governor.pause(time.perf_counter() - started, self.stop)
            if self.readdirs and self.readdirs % 400 == 0:
                self.index.checkpoint()
            self._maybe_schedule()

    def drain(self, limit: int = 100000) -> int:
        """Synchron bis die Warteschlange leer ist. Für Tests und den Erstlauf."""
        count = 0
        while count < limit:
            with self._write_gate:
                item = self._pop()
                if item is None:
                    break
                path, tier, descend = item
                if path == _PATH_DIR:
                    self.ingest_path()
                else:
                    self.scan_dir(path, tier, descend)
            count += 1
        return count

    def poll_drives(self, *, force: bool = False) -> None:
        """Angehängte und abgehängte Laufwerke. Win32 höchstens alle 12 Sekunden."""
        if self._drive_poll is None:
            return
        now = time.monotonic()
        if not force and now < self._next_drive_poll:
            return
        self._next_drive_poll = now + DRIVE_POLL_S
        try:
            found = list(self._drive_poll())
        except OSError:
            log.debug("drive poll failed", exc_info=True)
            return
        self.apply_drives(found)

    def apply_drives(self, found: list[tuple[Any, ...]]) -> None:
        current: dict[str, tuple[int, bool, bool]] = {}
        for item in found:
            if len(item) >= 3:
                raw, tier, walk = item[0], int(item[1]), bool(item[2])
            else:
                raw, tier = item[0], int(item[1])
                walk = True
            shallow = bool(item[3]) if len(item) >= 4 else False
            if not raw:
                continue
            path = norm(raw)
            previous = current.get(path)
            if previous is None or int(tier) < previous[0]:
                current[path] = (int(tier), walk, shallow)
            elif int(tier) == previous[0] and previous[2] and not shallow:
                current[path] = (int(tier), walk, False)
        for path in list(self._dynamic):
            if path not in current:
                self._drop_drive(path)
        for path, (tier, walk, shallow) in current.items():
            if path in self._dynamic or not walk:
                continue
            self._adopt_drive(path, tier, shallow=shallow)

    def _adopt_drive(self, path: str, tier: int, *, shallow: bool = False) -> None:
        if path in self._static_roots:
            return
        try:
            present = os.path.isdir(path)
        except OSError:
            return
        if not present:
            return
        self._dynamic[path] = tier
        self._names_only.add(path)
        if shallow:
            self._shallow.add(path)
        if not any(existing == path for existing, _tier in self.roots):
            self.roots.append((path, tier))
        if not any(existing == path for existing, _tier in self._claimed):
            self._claimed.append((path, tier))
        self.add(path, tier, descend=not shallow, priority=tier)
        log.info("drive added: %s", path)

    def _drop_drive(self, path: str) -> None:
        self._dynamic.pop(path, None)
        self._shallow.discard(path)
        if path in self._static_roots:
            return
        self._names_only.discard(path)
        self.roots = [(existing, tier) for existing, tier in self.roots if existing != path]
        self._claimed = [(existing, tier) for existing, tier in self._claimed if existing != path]
        self._discard_queued(path)
        self.index.drop_tree(path)
        log.info("drive removed: %s", path)

    def hides_content(self, path: str) -> bool:
        """Externe Platte, USB, Cloud oder Netz: keine Dateibytes lesen."""
        for root in self._names_only:
            if is_inside(path, root):
                return True
        return False

    def _watch_dir(self, path: str, tier: int) -> None:
        # Wechseldatenträger nicht öfter als der Tier-1-Takt (300 s) nachlesen.
        if tier > 1 or self.watcher is None or self.hides_content(path):
            return
        self.watcher.watch(path)

    def _discard_queued(self, root: str) -> None:
        with self._lock:
            drop = [
                queued
                for queued in self._desired
                if not queued.startswith(":") and is_inside(queued, root)
            ]
            for queued in drop:
                del self._desired[queued]

    def _maybe_schedule(self) -> None:
        now = time.monotonic()
        due = {tier for tier, when in self._next_full.items() if now >= when}
        if not due:
            return
        if 0 in due and self.index_path:
            self.add(_PATH_DIR, 0, descend=False, priority=0)
        for path, tier in self.roots:
            if tier in due:
                self.add(path, tier, descend=self._root_descend(path), priority=tier)
        for tier in due:
            self._next_full[tier] = now + RESCHEDULE[tier]

    def ingest_path(self) -> None:
        rows: list[dict[str, Any]] = []
        seen_dirs: set[str] = set()
        for raw in os.environ.get("PATH", "").split(os.pathsep):
            if not raw or raw in seen_dirs:
                continue
            seen_dirs.add(raw)
            try:
                entries = list(os.scandir(raw))
            except OSError:
                continue
            for entry in entries:
                try:
                    is_file = entry.is_file(follow_symlinks=True)
                except OSError:
                    continue
                if not is_file or should_skip_file(entry.name):
                    continue
                if sys.platform == "win32":
                    if entry.name.casefold().rsplit(".", 1)[-1] not in {"exe", "bat", "cmd", "com"}:
                        continue
                elif not os.access(entry.path, os.X_OK):
                    continue
                try:
                    full = norm(os.path.realpath(entry.path))
                except OSError:
                    full = norm(entry.path)
                try:
                    st = entry.stat(follow_symlinks=True)
                except OSError:
                    continue
                rows.append(
                    {
                        "kind": "app",
                        "name": Path(entry.name).stem if sys.platform == "win32" else entry.name,
                        "path": full,
                        "dir": _PATH_DIR,
                        "ext": Path(entry.name).suffix.casefold(),
                        "launch": None,
                        "mtime_ns": getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)),
                        "size": st.st_size,
                        "tier": 0,
                    }
                )
        self.index.reconcile_dir(_PATH_DIR, ":meta", 0, 0, rows, [])

    def scan_dir(self, path: str, tier: int, descend: bool) -> None:
        if path.startswith(":"):
            return
        if self.data_dir and is_inside(path, self.data_dir):
            return
        if self.blocked(path, tier):
            return
        shallow = path in self._shallow
        if shallow:
            descend = False
            st = stat_quick(path, SHALLOW_LIST_S)
            if st is None:
                return
        else:
            try:
                st = os.stat(path, follow_symlinks=False)
            except OSError:
                return
        if not stat.S_ISDIR(st.st_mode):
            return
        known, dirty, readdir_ns = self.index.dir_info(path)
        current_mtime = getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))
        stale = (time.time_ns() - readdir_ns) >= self.readdir_max_age_ns
        if known is not None and known == current_mtime and not dirty and not stale:
            if descend:
                for child in self.index.child_dirs(path):
                    self.add(child, tier, descend=True, priority=tier)
            self._watch_dir(path, tier)
            return
        self.readdirs += 1
        files: list[os.DirEntry[str]] = []
        subdirs: list[str] = []
        markers = sys.platform != "win32" and os.path.isdir(os.path.join(path, ".flare-offline"))
        if shallow:
            listed = list_dir_quick(path, SHALLOW_LIST_S)
            if listed is None:
                return
            source: Any = nullcontext(listed)
        else:
            try:
                source = os.scandir(path)
            except OSError:
                return
        with source as entries:
            for entry in entries:
                name = entry.name
                if name in {".", ".."}:
                    continue
                try:
                    is_dir = entry.is_dir(follow_symlinks=False)
                    is_file = entry.is_file(follow_symlinks=False)
                except OSError:
                    continue
                if is_dir:
                    if should_skip_dir(name):
                        continue
                    child = norm(entry.path)
                    if self.blocked(child, tier):
                        continue
                    if self.data_dir and is_inside(child, self.data_dir):
                        continue
                    subdirs.append(child)
                elif is_file:
                    if should_skip_file(name):
                        continue
                    files.append(entry)
        items: list[dict[str, Any]] = []
        samples: list[tuple[str, str]] = []
        for child in subdirs:
            try:
                dst = os.stat(child, follow_symlinks=False)
            except OSError:
                continue
            items.append(
                {
                    "kind": "dir",
                    "name": os.path.basename(child),
                    "path": child,
                    "dir": path,
                    "ext": "",
                    "launch": None,
                    "mtime_ns": getattr(dst, "st_mtime_ns", int(dst.st_mtime * 1e9)),
                    "size": 0,
                    "tier": tier,
                }
            )
        for entry in files:
            full = norm(entry.path)
            lowered = entry.name.casefold()
            try:
                st_file = entry.stat(follow_symlinks=False)
            except OSError:
                continue
            mtime_ns = getattr(st_file, "st_mtime_ns", int(st_file.st_mtime * 1e9))
            if lowered.endswith(".lnk") and not self.hides_content(full):
                parsed = parse_lnk(full)
                if parsed is None:
                    continue
                parsed["mtime_ns"] = mtime_ns
                parsed["size"] = st_file.st_size
                parsed["tier"] = tier
                items.append(parsed)
                continue
            items.append(
                {
                    "kind": "file",
                    "name": entry.name,
                    "path": full,
                    "dir": path,
                    "ext": Path(entry.name).suffix.casefold(),
                    "launch": None,
                    "mtime_ns": mtime_ns,
                    "size": st_file.st_size,
                    "tier": tier,
                }
            )
            offline = is_offline_file(full, st_file, marker_dir=markers)
            if should_sample_content(
                enabled=self.content,
                tier=tier,
                offline=offline,
                names_only=self.hides_content(full),
            ):
                sample = read_text_sample(full, st_file.st_size)
                if sample:
                    samples.append((full, sample))
        try:
            after = os.stat(path, follow_symlinks=False)
            saved_mtime = getattr(after, "st_mtime_ns", current_mtime)
        except OSError:
            saved_mtime = current_mtime
        self.index.reconcile_dir(path, parent_of(path), saved_mtime, tier, items, subdirs)
        for full, sample in samples:
            self.index.set_content(full, sample)
        if saved_mtime != current_mtime:
            self.index.mark_dirty(path)
            self.add(path, tier, descend=descend, priority=tier)
        self._watch_dir(path, tier)
        if shallow:
            return
        for child in subdirs:
            if descend or not self.index.knows_dir(child):
                self.add(child, tier, descend=True, priority=tier)
            elif self.index.dir_info(child)[1]:
                self.add(child, tier, descend=False, priority=tier)
