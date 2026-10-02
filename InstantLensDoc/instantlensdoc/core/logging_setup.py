"""Datei-Logging unter %APPDATA%/InstantLensDoc (bzw. XDG_CONFIG_HOME)."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

_CONFIGURED = False


def log_dir() -> Path:
    from instantlensdoc.config import config_dir

    d = config_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_file() -> Path:
    return log_dir() / "instantlensdoc.log"


def setup_logging(*, level: int = logging.INFO, force: bool = False) -> Path:
    """
    Konfiguriert Root-Logger einmalig:
    - Rotierende Datei in config_dir()/logs/instantlensdoc.log
    - Kurz auf stderr (Warnungen+)
    """
    global _CONFIGURED
    path = log_file()
    if _CONFIGURED and not force:
        return path

    root = logging.getLogger()
    root.setLevel(level)
    # Doppelte Handler vermeiden
    for h in list(root.handlers):
        root.removeHandler(h)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = RotatingFileHandler(
        path,
        maxBytes=1_500_000,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setLevel(level)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(logging.WARNING)
    sh.setFormatter(fmt)
    root.addHandler(sh)

    _CONFIGURED = True
    logging.getLogger("instantlensdoc").info("Logging gestartet → %s", path)
    return path


def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name or "instantlensdoc")
