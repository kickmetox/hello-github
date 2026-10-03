"""Manuelles Backup aktueller Dokumente in den App-Backup-Ordner — 1.0.0."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from instantlensdoc.config import config_dir


def backup_dir() -> Path:
    """Persistenter Backup-Ordner unter dem App-Config-Verzeichnis."""
    d = config_dir() / "backups"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def manual_backup_file(path: str | Path, *, dest_dir: Path | None = None) -> Optional[Path]:
    """
    Datei (und ggf. Sidecar ``*.ildann.json``) mit Zeitstempel nach ``backups/`` kopieren.
    Rückgabe: Pfad der Hauptkopie, oder None wenn Quelle fehlt.
    """
    src = Path(path)
    if not src.is_file():
        return None
    out_dir = Path(dest_dir) if dest_dir is not None else backup_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = _stamp()
    dest = out_dir / f"{src.stem}.{stamp}{src.suffix}"
    # Kollision vermeiden
    n = 1
    while dest.exists():
        dest = out_dir / f"{src.stem}.{stamp}_{n}{src.suffix}"
        n += 1
    shutil.copy2(src, dest)
    sidecar = Path(str(src) + ".ildann.json")
    if not sidecar.is_file():
        # alternativ: path.with_suffix(path.suffix + ".ildann.json")
        alt = src.with_suffix(src.suffix + ".ildann.json")
        if alt.is_file():
            sidecar = alt
    if sidecar.is_file():
        side_dest = out_dir / f"{sidecar.name}.{stamp}"
        # lesbarer: stem.stamp.suffix.ildann.json
        side_dest = out_dir / f"{src.stem}.{stamp}{src.suffix}.ildann.json"
        try:
            shutil.copy2(sidecar, side_dest)
        except OSError:
            pass
    return dest


def manual_backup_text(
    text: str,
    *,
    title: str = "unbenannt",
    dest_dir: Path | None = None,
    suffix: str = ".txt",
) -> Path:
    """Ungespeicherten Editor-Text als Backup-Datei ablegen."""
    out_dir = Path(dest_dir) if dest_dir is not None else backup_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (title or "unbenannt"))[:48]
    if not safe:
        safe = "unbenannt"
    stamp = _stamp()
    dest = out_dir / f"{safe}.{stamp}{suffix if suffix.startswith('.') else '.' + suffix}"
    dest.write_text(text or "", encoding="utf-8")
    return dest
