"""Datei-Logging unter %APPDATA%/InstantLensDoc (bzw. XDG_CONFIG_HOME) — 1.6.3."""

from __future__ import annotations

import logging
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

_CONFIGURED = False

# Passwort/Geheimnisse nie in Logs — 1.6.3
_SECRET_PATTERNS = (
    re.compile(r"(?i)(password|passwd|passwort|prefill)\s*[=:]\s*\S+"),
    re.compile(r"(?i)(user_password|owner_password)\s*[=:]\s*\S+"),
    re.compile(r"(?i)(_crypto_reload_prefill)\s*[=:]\s*\S+"),
)


def redact_secrets(text: str) -> str:
    """Entfernt Passwort-/Geheimnis-Werte aus Logtext — 1.6.3."""
    if not text:
        return text
    out = str(text)
    for pat in _SECRET_PATTERNS:
        out = pat.sub(lambda m: f"{m.group(1)}=***", out)
    return out


class _SecretRedactFilter(logging.Filter):
    """Filter: Passwörter nie in Logs schreiben — 1.6.3."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = redact_secrets(record.msg)
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {
                        k: redact_secrets(str(v)) if isinstance(v, str) else v
                        for k, v in record.args.items()
                    }
                elif isinstance(record.args, tuple):
                    record.args = tuple(
                        redact_secrets(a) if isinstance(a, str) else a
                        for a in record.args
                    )
        except Exception:
            pass
        return True


def log_dir() -> Path:
    from instantlensdoc.config import config_dir

    d = config_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_file() -> Path:
    return log_dir() / "instantlensdoc.log"


def create_crash_report_zip(
    dest: Path | str | None = None,
    *,
    screenshot_path: Path | str | None = None,
) -> Path:
    """
    Packt den Logordner (Crash-/App-Logs) als ZIP.
    dest: Zielpfad (.zip); wenn None → Logordner/InstantLensDoc-crash-report-YYYYMMDD-HHMMSS.zip
    screenshot_path: optionaler Hinweis/Pfad zu einem Screenshot — wird in REPORT.txt
      vermerkt und, falls die Datei existiert, ins ZIP unter screenshots/ kopiert.
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

    shot: Path | None = None
    shot_hint = ""
    if screenshot_path is not None:
        raw = str(screenshot_path).strip()
        if raw:
            shot_hint = raw
            cand = Path(raw)
            if cand.is_file():
                shot = cand

    with zipfile.ZipFile(dest_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Manifest kurz
        files = sorted(p for p in src.iterdir() if p.is_file() and p.suffix.lower() != ".zip")
        manifest = [
            "InstantLens Doc crash report",
            f"created: {datetime.now().isoformat(timespec='seconds')}",
            f"log_dir: {src}",
            f"files: {len(files)}",
            "",
        ]
        if shot_hint:
            manifest.append(f"screenshot_path_hint: {shot_hint}")
            if shot is not None:
                manifest.append(f"screenshot_included: screenshots/{shot.name}")
            else:
                manifest.append(
                    "screenshot_included: no (Pfad nur als Hinweis — Datei nicht gefunden "
                    "oder nicht angegeben)"
                )
            manifest.append("")
        else:
            manifest.append("screenshot_path_hint: (none)")
            manifest.append("")
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
        if shot is not None:
            try:
                zf.write(shot, arcname=f"screenshots/{shot.name}")
            except OSError:
                pass
    return dest_path


def setup_logging(*, level: int = logging.INFO, force: bool = False) -> Path:
    """
    Konfiguriert Root-Logger einmalig:
    - Rotierende Datei in config_dir()/logs/instantlensdoc.log
    - Kurz auf stderr (Warnungen+)
    - Passwort-Redaction-Filter (nie Passwort in Logs) — 1.6.3
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
    redact = _SecretRedactFilter()
    fh = RotatingFileHandler(
        path,
        maxBytes=1_500_000,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setLevel(level)
    fh.setFormatter(fmt)
    fh.addFilter(redact)
    root.addHandler(fh)

    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(logging.WARNING)
    sh.setFormatter(fmt)
    sh.addFilter(redact)
    root.addHandler(sh)

    # Auch am Logger selbst, falls Handler später hinzukommen
    root.addFilter(redact)

    _CONFIGURED = True
    logging.getLogger("instantlensdoc").info("Logging gestartet → %s", path)
    return path


def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name or "instantlensdoc")
