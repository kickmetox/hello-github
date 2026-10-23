"""Änderungen an heißen Ordnern unter Windows 11.

Eine Meldung pro Wurzel (Unterbaum). Der Katalog prüft danach nur Ordner,
deren mtime sich geändert hat.
"""

from __future__ import annotations

import ctypes
import logging
import os
import select
import struct
import sys
import threading
from collections.abc import Callable
from ctypes import c_char_p, c_int, c_uint32

log = logging.getLogger("flare")

ChangeFn = Callable[[str, bool], None]

IN_MODIFY = 0x00000002
IN_ATTRIB = 0x00000004
IN_CLOSE_WRITE = 0x00000008
IN_MOVED_FROM = 0x00000040
IN_MOVED_TO = 0x00000080
IN_CREATE = 0x00000100
IN_DELETE = 0x00000200
IN_DELETE_SELF = 0x00000400
IN_MOVE_SELF = 0x00000800
IN_Q_OVERFLOW = 0x00004000
IN_IGNORED = 0x00008000
IN_MASK = (
    IN_MODIFY | IN_ATTRIB | IN_CLOSE_WRITE | IN_MOVED_FROM | IN_MOVED_TO
    | IN_CREATE | IN_DELETE | IN_DELETE_SELF | IN_MOVE_SELF
)
IN_NONBLOCK = 0x800
IN_CLOEXEC = 0x80000


class NullWatcher:
    def watch(self, path: str) -> None:
        return

    def close(self) -> None:
        return


class LinuxWatcher:
    def __init__(self, on_change: ChangeFn, stop: threading.Event) -> None:
        self.on_change = on_change
        self.stop = stop
        self._lock = threading.Lock()
        self._wd_to_path: dict[int, str] = {}
        self._paths: set[str] = set()
        self.fd = -1
        self._libc = ctypes.CDLL("libc.so.6", use_errno=True)
        self._libc.inotify_init1.argtypes = [c_int]
        self._libc.inotify_init1.restype = c_int
        self._libc.inotify_add_watch.argtypes = [c_int, c_char_p, c_uint32]
        self._libc.inotify_add_watch.restype = c_int
        self.fd = self._libc.inotify_init1(IN_NONBLOCK | IN_CLOEXEC)
        if self.fd < 0:
            raise OSError("inotify_init1")
        self.limit = _watch_limit()
        self._thread = threading.Thread(target=self._loop, name="flare-watch", daemon=True)
        self._thread.start()

    def watch(self, path: str) -> None:
        with self._lock:
            if path in self._paths or len(self._paths) >= self.limit or self.fd < 0:
                return
            wd = self._libc.inotify_add_watch(self.fd, path.encode("utf-8", "surrogateescape"), IN_MASK)
            if wd < 0:
                return
            self._wd_to_path[wd] = path
            self._paths.add(path)

    def close(self) -> None:
        fd = self.fd
        self.fd = -1
        if fd >= 0:
            os.close(fd)
        if self._thread.is_alive():
            self._thread.join(timeout=1.5)

    def _loop(self) -> None:
        while not self.stop.is_set() and self.fd >= 0:
            try:
                readable, _, _ = select.select([self.fd], [], [], 0.4)
            except (OSError, ValueError):
                return
            if not readable:
                continue
            try:
                blob = os.read(self.fd, 65536)
            except BlockingIOError:
                continue
            except OSError:
                return
            self._parse(blob)

    def _parse(self, blob: bytes) -> None:
        offset = 0
        header = 16
        while offset + header <= len(blob):
            wd, mask, _cookie, name_len = _unpack_event(blob, offset)
            if name_len < 0 or offset + header + name_len > len(blob):
                return
            offset += header + name_len
            if mask & IN_Q_OVERFLOW:
                with self._lock:
                    paths = list(self._paths)
                for path in paths:
                    self.on_change(path, False)
                continue
            if mask & IN_IGNORED:
                with self._lock:
                    path = self._wd_to_path.pop(wd, None)
                    if path:
                        self._paths.discard(path)
                continue
            with self._lock:
                path = self._wd_to_path.get(wd)
            if path:
                self.on_change(path, False)


def _unpack_event(blob: bytes, offset: int) -> tuple[int, int, int, int]:
    wd, mask, cookie, name_len = struct.unpack_from("iIII", blob, offset)
    return wd, mask, cookie, name_len


def _watch_limit() -> int:
    try:
        raw = int(Path_read("/proc/sys/fs/inotify/max_user_watches"))
    except (OSError, ValueError):
        raw = 8192
    return max(128, min(2000, raw // 4))


def Path_read(path: str) -> str:
    with open(path, encoding="ascii") as handle:
        return handle.read().strip()


class WindowsWatcher:
    def __init__(self, on_change: ChangeFn, stop: threading.Event, roots: list[str]) -> None:
        self.on_change = on_change
        self.stop = stop
        self.roots = roots[:60]
        self._thread = threading.Thread(target=self._loop, name="flare-watch", daemon=True)
        self._thread.start()

    def watch(self, path: str) -> None:
        return

    def close(self) -> None:
        if self._thread.is_alive():
            self._thread.join(timeout=1.5)

    def _loop(self) -> None:
        kernel = ctypes.windll.kernel32
        kernel.FindFirstChangeNotificationW.argtypes = [ctypes.c_wchar_p, ctypes.c_int, ctypes.c_uint32]
        kernel.FindFirstChangeNotificationW.restype = ctypes.c_void_p
        kernel.FindNextChangeNotification.argtypes = [ctypes.c_void_p]
        kernel.FindNextChangeNotification.restype = ctypes.c_int
        kernel.FindCloseChangeNotification.argtypes = [ctypes.c_void_p]
        kernel.WaitForMultipleObjects.argtypes = [
            ctypes.c_uint32, ctypes.c_void_p, ctypes.c_int, ctypes.c_uint32
        ]
        kernel.WaitForMultipleObjects.restype = ctypes.c_uint32
        flags = 0x1 | 0x2 | 0x8 | 0x10
        invalid = ctypes.c_void_p(-1).value
        owned: list[tuple[int, str]] = []
        for root in self.roots:
            handle = kernel.FindFirstChangeNotificationW(root, 1, flags)
            if not handle or handle == invalid:
                continue
            owned.append((handle, root))
        if not owned:
            return
        array_type = ctypes.c_void_p * len(owned)
        arr = array_type(*(handle for handle, _root in owned))
        try:
            while not self.stop.is_set():
                rc = kernel.WaitForMultipleObjects(len(owned), arr, 0, 400)
                if rc >= len(owned):
                    continue
                _handle, root = owned[rc]
                self.on_change(root, True)
                kernel.FindNextChangeNotification(owned[rc][0])
        finally:
            for handle, _root in owned:
                kernel.FindCloseChangeNotification(handle)


def start_watcher(
    on_change: ChangeFn,
    stop: threading.Event,
    roots: list[str],
) -> NullWatcher | LinuxWatcher | WindowsWatcher:
    if sys.platform == "win32":
        try:
            return WindowsWatcher(on_change, stop, roots)
        except OSError:
            log.exception("windows watcher unavailable")
            return NullWatcher()
    if sys.platform.startswith("linux"):
        try:
            return LinuxWatcher(on_change, stop)
        except OSError:
            log.exception("inotify unavailable")
            return NullWatcher()
    return NullWatcher()
