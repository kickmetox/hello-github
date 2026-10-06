"""QTimer-Watchdog um einen Geräte-Worker — GUI bleibt bedienbar — 2.6.57."""

from __future__ import annotations

import time
from typing import Any, Callable, Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget

from instantlensdoc.core.device_io import submit_device_io


def watch_worker(
    parent: Optional[QWidget],
    fn: Callable[..., Any],
    *,
    timeout: float,
    on_done: Callable[[Any], None],
    on_timeout: Callable[[], None],
    on_error: Optional[Callable[[BaseException], None]] = None,
    args: tuple = (),
    kwargs: Optional[dict] = None,
    interval_ms: int = 40,
) -> QTimer:
    """``fn`` im Geräte-Pool starten; GUI-Thread nur per Timer pollen.

    Nach ``timeout`` wird ``on_timeout`` aufgerufen und ein späteres
    Future-Ergebnis ignoriert. Der Timer ist Kind von ``parent`` (wird mit
    dem Dialog entsorgt).
    """
    fut = submit_device_io(fn, *args, **(kwargs or {}))
    state = {"finished": False}
    t0 = time.monotonic()
    timer = QTimer(parent)
    timer.setInterval(max(10, int(interval_ms)))

    def tick() -> None:
        if state["finished"]:
            timer.stop()
            return
        if fut.done():
            state["finished"] = True
            timer.stop()
            try:
                on_done(fut.result())
            except Exception as e:
                if on_error is not None:
                    on_error(e)
                else:
                    try:
                        on_done(e)
                    except Exception:
                        pass
            return
        if (time.monotonic() - t0) >= max(0.05, float(timeout)):
            state["finished"] = True
            timer.stop()
            try:
                from instantlensdoc.core.scan_procs import kill_tracked_scan_children

                kill_tracked_scan_children(wia_orphans=True)
            except Exception:
                pass
            try:
                on_timeout()
            except Exception:
                pass

    timer.timeout.connect(tick)
    timer.start()
    return timer
