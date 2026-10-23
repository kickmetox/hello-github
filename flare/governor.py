"""Begrenzt die Indexierung auf ein kleines Tastverhältnis und weicht bei Last aus."""

from __future__ import annotations

import sys
import threading
import time


def sleep_budget(work_s: float, duty: float, idle: float) -> float:
    """Wie lange nach `work_s` Arbeit gewartet wird, damit der Anteil `duty` bleibt."""
    if duty >= 1:
        need = 0.0
    else:
        need = work_s * (1.0 - duty) / max(duty, 0.01)
    if idle < 0.20:
        need += 0.30
    return min(max(need, 0.0), 0.50)


def read_cpu_times() -> tuple[int, int] | None:
    """Liefert (idle, total). None, wenn die Plattform keine Quelle hat."""
    if sys.platform == "win32":
        return _windows_times()
    try:
        with open("/proc/stat", encoding="ascii") as handle:
            parts = handle.readline().split()
        if not parts or parts[0] != "cpu":
            return None
        nums = [int(part) for part in parts[1:]]
    except (OSError, ValueError):
        return None
    if len(nums) < 4:
        return None
    idle = nums[3] + (nums[4] if len(nums) > 4 else 0)
    return idle, sum(nums)


def _windows_times() -> tuple[int, int] | None:
    import ctypes

    class FILETIME(ctypes.Structure):
        _fields_ = [("lo", ctypes.c_uint32), ("hi", ctypes.c_uint32)]

    idle, kernel, user = FILETIME(), FILETIME(), FILETIME()
    ok = ctypes.windll.kernel32.GetSystemTimes(
        ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
    )
    if not ok:
        return None

    def value(ft: FILETIME) -> int:
        return (ft.hi << 32) | ft.lo

    # Kernel-Zeit enthält die Idle-Zeit bereits.
    idle_v = value(idle)
    total = value(kernel) + value(user)
    return idle_v, total


def lower_background_thread() -> None:
    """Nur den Index-Thread drosseln. Unter Windows über die Thread-Priorität."""
    if sys.platform != "win32":
        return
    import ctypes

    THREAD_MODE_BACKGROUND_BEGIN = 0x00010000
    try:
        ctypes.windll.kernel32.SetThreadPriority(
            ctypes.windll.kernel32.GetCurrentThread(),
            THREAD_MODE_BACKGROUND_BEGIN,
        )
    except OSError:
        return


class Governor:
    def __init__(self, duty: float = 0.08, fast: bool = False) -> None:
        self.base_duty = min(0.50, max(0.02, duty))
        self.fast = fast
        self.started = time.perf_counter()
        self.boost_seconds = 8.0
        self.last_sample = 0.0
        self.last_idle = 1.0
        self.wake = threading.Event()

    @property
    def duty(self) -> float:
        if (time.perf_counter() - self.started) < self.boost_seconds:
            return max(self.base_duty, 0.40)
        return self.base_duty

    def pause(self, work_s: float, stop: threading.Event | None = None) -> None:
        if self.fast:
            return
        now = time.perf_counter()
        if now - self.last_sample > 0.40:
            self.last_idle = self._sample_idle(0.02)
            self.last_sample = time.perf_counter()
        budget = sleep_budget(work_s, self.duty, self.last_idle)
        deadline = time.perf_counter() + budget
        while time.perf_counter() < deadline:
            if stop is not None and stop.is_set():
                return
            if self.wake.is_set():
                self.wake.clear()
                return
            time.sleep(0.02)

    def _sample_idle(self, sample_s: float) -> float:
        first = read_cpu_times()
        if first is None:
            time.sleep(sample_s)
            return 1.0
        time.sleep(sample_s)
        second = read_cpu_times()
        if second is None:
            return 1.0
        total = second[1] - first[1]
        idle = second[0] - first[0]
        if total <= 0:
            return 1.0
        return max(0.0, min(1.0, idle / total))
