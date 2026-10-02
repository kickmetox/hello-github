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


def create_crash_report_zip(dest: Path | str | None = None) -> Path:
    """
    Packt den Logordner (Crash-/App-Logs) als ZIP.
    dest: Zielpfad (.zip); wenn None → Logordner/InstantLensDoc-crash-report-YYYYMMDD-HHMMSS.zip
    """
    import zipfile
    from datetime import datetime

    src = log_dir()
    if dest is None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        dest_path = src / f"InstantLensDoc-crash-report-{stamp}.zip"
    else:
        dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Manifest kurz
        files = sorted(p for p in src.iterdir() if p.is_file() and p.suffix.lower() != ".zip")
        manifest = [
            f"InstantLens Doc crash report",
            f"created: {datetime.now().isoformat(timespec='seconds')}",
            f"log_dir: {src}",
            f"files: {len(files)}",
            "",
        ]
        for p in files:
            try:
                manifest.append(f"- {p.name} ({p.stat().st_size} bytes)")
            except OSError:
                manifest.append(f"- {p.name}")
        zf.writestr("REPORT.txt", "\n".join(manifest) + "\n")
        for p in files:
            try:
                zf.write(p, arcname=p.name)
            except OSError:
                continue
    return dest_path


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
