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
from pathlib import Path
from typing import Any

from flare.governor import Governor
from flare.launch import is_secret_name, parse_lnk
from flare.paths import is_inside, norm, parent_of
from flare.store import Index

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
        if path in seen:
            continue
        seen.add(path)
        kept.append((path, tier))
    return kept


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
            self.add(path, tier, descend=True, priority=tier)
        if self.index_path:
            self.ingest_path()

    def enqueue_all(self) -> None:
        for path, tier in self.roots:
            self.add(path, tier, descend=True, priority=tier)
        if self.index_path:
            self.ingest_path()

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
            item = self._pop()
            if item is None:
                self.phase = "idle"
                self._maybe_schedule()
                if self.stop.wait(0.4):
                    return
                continue
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
            self.governor.pause(time.perf_counter() - started, self.stop)
            if self.readdirs and self.readdirs % 400 == 0:
                self.index.checkpoint()
            self._maybe_schedule()

    def drain(self, limit: int = 100000) -> int:
        """Synchron bis die Warteschlange leer ist. Für Tests und den Erstlauf."""
        count = 0
        while count < limit:
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

    def _maybe_schedule(self) -> None:
        now = time.monotonic()
        due = {tier for tier, when in self._next_full.items() if now >= when}
        if not due:
            return
        if 0 in due and self.index_path:
            self.add(_PATH_DIR, 0, descend=False, priority=0)
        for path, tier in self.roots:
            if tier in due:
                self.add(path, tier, descend=True, priority=tier)
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
            if tier <= 1 and self.watcher is not None:
                self.watcher.watch(path)
            return
        self.readdirs += 1
        files: list[os.DirEntry[str]] = []
        subdirs: list[str] = []
        try:
            iterator = os.scandir(path)
        except OSError:
            return
        with iterator:
            for entry in iterator:
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
            if lowered.endswith(".lnk"):
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
            if self.content and tier <= 1:
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
        if tier <= 1 and self.watcher is not None:
            self.watcher.watch(path)
        for child in subdirs:
            if descend or not self.index.knows_dir(child):
                self.add(child, tier, descend=True, priority=tier)
            elif self.index.dir_info(child)[1]:
                self.add(child, tier, descend=False, priority=tier)
