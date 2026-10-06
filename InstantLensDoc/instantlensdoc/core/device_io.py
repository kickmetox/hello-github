"""Geräte-I/O ohne GUI-Blockade — Probe/Open/Acquire mit Timeout — 2.6.57.

WIA-Connect an einem Gerät im Energiesparmodus hängt oft endlos im GUI-Thread.
Alle Gerätezugriffe laufen deshalb in einem Worker; nach ``DEVICE_IO_TIMEOUT_S``
(8–12 s) gilt der Versuch als fehlgeschlagen, die Oberfläche wird wieder
freigegeben. Der Worker-Thread kann nicht hart abgebrochen werden — das
zugehörige Subprozess-Backend (PowerShell/NAPS2) schon (siehe scan_transfer).
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from dataclasses import dataclass
from typing import Any, Callable, Optional

# 8–12 s: Gerät im Sleep / Netz-WIA ohne Antwort. Erfolgreiche NAPS2/eSCL-Scans
# nutzen in der UI einen längeren Watchdog (siehe ACQUIRE_OK_TIMEOUT_S).
DEVICE_IO_TIMEOUT_S = 10.0
WIA_HANG_TIMEOUT_S = 12.0
ACQUIRE_OK_TIMEOUT_S = 90.0
DISCOVERY_STEP_TIMEOUT_S = 8.0
MENU_REFRESH_TIMEOUT_S = 45.0

DEVICE_TIMEOUT_DE = (
    "Gerät hat nicht geantwortet (Zeitüberschreitung {seconds} s). "
    "Netzwerk-Scanner im Energiesparmodus reagieren oft nicht "
    "(WIA-Vorschau / Netzwerk). "
    "Bitte eSCL/ScanTuxio oder ein anderes Gerät bzw. Backend wählen."
)

_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ild-devio")


def io_timeout_s(default: float = DEVICE_IO_TIMEOUT_S) -> float:
    """Test-Override über ``ILD_DEVICE_IO_TIMEOUT`` (Sekunden)."""
    raw = os.environ.get("ILD_DEVICE_IO_TIMEOUT", "").strip()
    if raw:
        try:
            return max(0.05, float(raw))
        except ValueError:
            pass
    return float(default)


@dataclass
class TimeoutRun:
    """Ergebnis von ``run_with_timeout`` — wirft nie."""

    value: Any = None
    timed_out: bool = False
    error: str = ""

    @property
    def ok(self) -> bool:
        return (not self.timed_out) and (not self.error)


def run_with_timeout(
    fn: Callable[..., Any],
    timeout: float,
    *args: Any,
    executor: Optional[ThreadPoolExecutor] = None,
    **kwargs: Any,
) -> TimeoutRun:
    """``fn`` im Worker ausführen. Nach ``timeout`` sofort zurückkehren.

    Blockiert den Aufrufer höchstens ``timeout`` (+ kleiner Future-Overhead),
    auch wenn ``fn`` endlos hängt. Der hängende Thread bleibt im Pool.
    """
    pool = executor or _POOL
    t0 = time.monotonic()
    fut = pool.submit(fn, *args, **kwargs)
    try:
        val = fut.result(timeout=max(0.05, float(timeout)))
        return TimeoutRun(value=val)
    except FuturesTimeout:
        seconds = max(1, int(round(float(timeout))))
        return TimeoutRun(
            timed_out=True,
            error=DEVICE_TIMEOUT_DE.format(seconds=seconds),
        )
    except Exception as e:
        return TimeoutRun(error=f"{type(e).__name__}: {e}")
    finally:
        # Hang-Nachweis für Tests: der Wait selbst darf timeout nicht sprengen.
        _ = time.monotonic() - t0


def submit_device_io(fn: Callable[..., Any], *args: Any, **kwargs: Any):
    """Future auf dem Geräte-Pool (GUI pollt, blockiert nie)."""
    return _POOL.submit(fn, *args, **kwargs)


__all__ = [
    "ACQUIRE_OK_TIMEOUT_S",
    "DEVICE_IO_TIMEOUT_S",
    "DEVICE_TIMEOUT_DE",
    "DISCOVERY_STEP_TIMEOUT_S",
    "MENU_REFRESH_TIMEOUT_S",
    "TimeoutRun",
    "WIA_HANG_TIMEOUT_S",
    "io_timeout_s",
    "run_with_timeout",
    "submit_device_io",
]
