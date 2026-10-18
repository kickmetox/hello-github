"""Einstieg: Oberfläche oder stille Wiederherstellung mit --restore."""

from __future__ import annotations

import ctypes
import logging
import sys

from spheredrive.paths import default_log_path, ensure_work_dir
from spheredrive.service import SphereService


def enable_dpi() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            return


def setup_logging() -> None:
    logger = logging.getLogger("spheredrive")
    if logger.handlers:
        return
    path = default_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    setup_logging()
    logger = logging.getLogger("spheredrive")
    folder_problem = ensure_work_dir()
    if folder_problem:
        logger.warning(folder_problem)
    if "--restore" in args:
        service = SphereService()
        results = service.restore_persistent()
        failed = False
        for result in results:
            line = ("OK " if result.ok else "FEHLER ") + result.text()
            logger.info(line)
            print(line)
            failed = failed or not result.ok
        return 1 if failed else 0
    enable_dpi()
    from spheredrive.ui.app import SphereApp

    app = SphereApp(SphereService())
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
