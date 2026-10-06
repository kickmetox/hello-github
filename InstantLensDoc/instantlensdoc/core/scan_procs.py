"""Scan-Kindprozesse (WIA/NAPS2/wiaacmgr/ScanTuxio) tracken und den Baum töten.

WIA.CommonDialog startet ``wiaacmgr.exe`` außerhalb unseres PowerShell-Prozesses.
``Popen.kill()`` trifft nur die Shell — der Dialog „Was soll gescannt werden?“
überlebt Force-Close und Timeout. Deshalb: PIDs merken, Prozessbaum
(``taskkill /T`` bzw. Prozessgruppe) plus neu erschienene ``wiaacmgr`` beenden.
Windows-Job mit KILL_ON_JOB_CLOSE: Kinder sterben mit InstantLens Doc.
"""

from __future__ import annotations

import atexit
import json
import os
import signal
import subprocess
import sys
import threading
from typing import Iterable, List, Optional, Sequence, Set

_LOCK = threading.Lock()
_TRACKED: Set[int] = set()
_JOB_HANDLE = None  # Windows Job-Object
_ATEXIT_DONE = False

# Prozesse, die WIA-Dialoge / Scan-Backends tragen (Namen lowercase)
ORPHAN_NAMES = (
    "wiaacmgr.exe",
    "wiaacmgr",
    "naps2.console.exe",
    "naps2.exe",
    "scantuxio.exe",
    "scantuxio",
)

# ECOSYS / Kyocera & Co. sind typische Netzwerk-MFPs (WIA im Sleep hängt).
NETWORK_MFP_MARKERS = (
    "ecosys",
    "kyocera",
    "taskalfa",
    "m5521",
    "m5526",
    "m2040",
    "m2135",
    "e-studio",
    "workcentre",
    "airprint",
    "airscan",
)


def name_looks_network_mfp(name: str) -> bool:
    n = (name or "").lower()
    return any(m in n for m in NETWORK_MFP_MARKERS)


def _pid_file_path():
    try:
        from instantlensdoc.config import config_dir

        return config_dir() / "scan_child_pids.json"
    except Exception:
        from pathlib import Path

        return Path.home() / ".config" / "InstantLensDoc" / "scan_child_pids.json"


def _persist() -> None:
    try:
        path = _pid_file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with _LOCK:
            pids = sorted(_TRACKED)
        path.write_text(json.dumps({"pids": pids}), encoding="utf-8")
    except Exception:
        pass


def _load_persisted() -> List[int]:
    try:
        path = _pid_file_path()
        if not path.is_file():
            return []
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [int(p) for p in (raw.get("pids") or []) if int(p) > 1]
    except Exception:
        return []


def register_pid(pid: Optional[int]) -> None:
    try:
        p = int(pid or 0)
    except (TypeError, ValueError):
        return
    if p <= 1:
        return
    with _LOCK:
        _TRACKED.add(p)
    _persist()
    _assign_to_job(p)


def unregister_pid(pid: Optional[int]) -> None:
    try:
        p = int(pid or 0)
    except (TypeError, ValueError):
        return
    with _LOCK:
        _TRACKED.discard(p)
    _persist()


def tracked_pids() -> List[int]:
    with _LOCK:
        return sorted(_TRACKED)


def _is_windows() -> bool:
    return sys.platform == "win32"


def list_named_pids(names: Sequence[str] = ORPHAN_NAMES) -> List[int]:
    """PIDs zu Prozessnamen (wiaacmgr, NAPS2, ScanTuxio)."""
    want = {n.lower() for n in names if n}
    extra = {n[:-4] for n in list(want) if n.endswith(".exe")}
    want |= extra
    found: List[int] = []
    if _is_windows():
        try:
            proc = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=8,
                creationflags=int(getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) or 0),
            )
            for line in (proc.stdout or "").splitlines():
                parts = [c.strip().strip('"') for c in line.split(",")]
                if len(parts) < 2:
                    continue
                if parts[0].lower() not in want:
                    continue
                try:
                    found.append(int(parts[1]))
                except ValueError:
                    continue
        except Exception:
            return found
        return found
    try:
        proc = subprocess.run(
            ["ps", "-eo", "pid,comm"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        for line in (proc.stdout or "").splitlines()[1:]:
            bits = line.split()
            if len(bits) < 2:
                continue
            comm = bits[1].lower()
            base = comm.rsplit("/", 1)[-1]
            if comm in want or base in want:
                try:
                    found.append(int(bits[0]))
                except ValueError:
                    continue
    except Exception:
        pass
    return found


def snapshot_scan_pids(names: Sequence[str] = ORPHAN_NAMES) -> Set[int]:
    return set(list_named_pids(names))


def kill_pid(pid: int) -> bool:
    """Einen Prozess beenden. Wirft nie."""
    try:
        p = int(pid)
    except (TypeError, ValueError):
        return False
    if p <= 1 or p == os.getpid():
        return False
    if _is_windows():
        try:
            subprocess.run(
                ["taskkill", "/F", "/PID", str(p)],
                capture_output=True,
                timeout=8,
                creationflags=int(getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) or 0),
            )
            return True
        except Exception:
            return False
    try:
        os.kill(p, signal.SIGKILL)
        return True
    except Exception:
        return False


def kill_process_tree(pid: int) -> List[int]:
    """Prozess und Kinder beenden (Windows ``taskkill /T``, POSIX Prozessgruppe)."""
    killed: List[int] = []
    try:
        p = int(pid)
    except (TypeError, ValueError):
        return killed
    if p <= 1 or p == os.getpid():
        return killed
    if _is_windows():
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(p)],
                capture_output=True,
                timeout=8,
                creationflags=int(getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) or 0),
            )
            killed.append(p)
        except Exception:
            if kill_pid(p):
                killed.append(p)
        return killed
    # POSIX: erst Prozessgruppe, dann PID
    try:
        os.killpg(p, signal.SIGKILL)
        killed.append(p)
    except Exception:
        pass
    if kill_pid(p) and p not in killed:
        killed.append(p)
    return killed


def kill_named(names: Sequence[str] = ("wiaacmgr.exe", "wiaacmgr")) -> List[int]:
    """Alle Prozesse mit diesen Namen beenden (verwaiste WIA-Dialoge)."""
    killed: List[int] = []
    for pid in list_named_pids(names):
        if pid in killed:
            continue
        if kill_process_tree(pid):
            killed.append(pid)
        unregister_pid(pid)
    return killed


def kill_new_since(before: Iterable[int], names: Sequence[str] = ORPHAN_NAMES) -> List[int]:
    """Seit Snapshot neu erschienene Scan-Helfer (typisch wiaacmgr) beenden."""
    prev = {int(p) for p in before}
    killed: List[int] = []
    for pid in list_named_pids(names):
        if pid in prev:
            continue
        if kill_process_tree(pid):
            killed.append(pid)
        unregister_pid(pid)
    return killed


def kill_tracked_scan_children(*, wia_orphans: bool = True) -> List[int]:
    """Alle gemerkten Scan-Kinder + optional wiaacmgr. Für Timeout/Cancel/Quit."""
    killed: List[int] = []
    for pid in tracked_pids() + _load_persisted():
        if pid in killed:
            continue
        killed.extend(kill_process_tree(pid))
        unregister_pid(pid)
    if wia_orphans:
        killed.extend(kill_named(("wiaacmgr.exe", "wiaacmgr")))
    _persist()
    return killed


def reap_orphan_scan_children() -> List[int]:
    """Nach Force-Close: PIDs aus der Datei + hängengebliebenes wiaacmgr."""
    persisted = _load_persisted()
    if not persisted:
        return []
    return kill_tracked_scan_children(wia_orphans=True)


def _init_job() -> None:
    """Ein Job-Object, KILL_ON_JOB_CLOSE: Force-Close tötet die Kinder mit."""
    global _JOB_HANDLE
    if not _is_windows() or _JOB_HANDLE is not None:
        return
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        handle = kernel32.CreateJobObjectW(None, None)
        if not handle:
            return
        # JOBOBJECT_EXTENDED_LIMIT_INFORMATION / JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
        JobObjectExtendedLimitInformation = 9

        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_uint64),
                ("WriteOperationCount", ctypes.c_uint64),
                ("OtherOperationCount", ctypes.c_uint64),
                ("ReadTransferCount", ctypes.c_uint64),
                ("WriteTransferCount", ctypes.c_uint64),
                ("OtherTransferCount", ctypes.c_uint64),
            ]

        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        kernel32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            wintypes.LPVOID,
            wintypes.DWORD,
        ]
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        ok = kernel32.SetInformationJobObject(
            handle,
            JobObjectExtendedLimitInformation,
            ctypes.byref(info),
            ctypes.sizeof(info),
        )
        if not ok:
            kernel32.CloseHandle(handle)
            return
        _JOB_HANDLE = handle
    except Exception:
        _JOB_HANDLE = None


def _assign_to_job(pid: int) -> None:
    if not _is_windows():
        return
    _init_job()
    if _JOB_HANDLE is None:
        return
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        PROCESS_SET_QUOTA = 0x0100
        PROCESS_TERMINATE = 0x0001
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        proc = kernel32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE, False, int(pid))
        if not proc:
            return
        try:
            kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
            kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
            kernel32.AssignProcessToJobObject(_JOB_HANDLE, proc)
        finally:
            kernel32.CloseHandle(proc)
    except Exception:
        pass


def _atexit_kill() -> None:
    global _ATEXIT_DONE
    if _ATEXIT_DONE:
        return
    _ATEXIT_DONE = True
    try:
        kill_tracked_scan_children(wia_orphans=True)
    except Exception:
        pass


atexit.register(_atexit_kill)


__all__ = [
    "NETWORK_MFP_MARKERS",
    "ORPHAN_NAMES",
    "kill_named",
    "kill_new_since",
    "kill_pid",
    "kill_process_tree",
    "kill_tracked_scan_children",
    "list_named_pids",
    "name_looks_network_mfp",
    "reap_orphan_scan_children",
    "register_pid",
    "snapshot_scan_pids",
    "tracked_pids",
    "unregister_pid",
]
