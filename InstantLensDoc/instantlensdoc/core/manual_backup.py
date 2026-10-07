"""Manuelles Backup aktueller Dokumente in den App-Backup-Ordner — 1.0.9."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from instantlensdoc.config import config_dir

# Letzte N Backup-Vorgänge in Settings anzeigen — 1.0.4
BACKUP_LOG_MAX = 20
# UTF-8 BOM für Excel-Kompatibilität beim TXT-Export — 1.0.8
_UTF8_BOM = "\ufeff"


def backup_dir() -> Path:
    """Persistenter Backup-Ordner unter dem App-Config-Verzeichnis."""
    d = config_dir() / "backups"
    d.mkdir(parents=True, exist_ok=True)
    return d


def backup_log_path() -> Path:
    """JSON-Log der letzten manuellen Backup-Vorgänge — 1.0.4."""
    return config_dir() / "backup_log.json"


def load_backup_log() -> list[dict[str, Any]]:
    """Letzte Backup-Log-Einträge (neueste zuerst), max. BACKUP_LOG_MAX."""
    path = backup_log_path()
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(raw, dict):
        items = raw.get("entries") or raw.get("log") or []
    elif isinstance(raw, list):
        items = raw
    else:
        return []
    out: list[dict[str, Any]] = []
    for it in items:
        if isinstance(it, dict):
            out.append(it)
    return out[:BACKUP_LOG_MAX]


def append_backup_log(
    *,
    dest: str | Path | None = None,
    source: str | Path | None = None,
    ok: bool = True,
    message: str = "",
) -> list[dict[str, Any]]:
    """
    Backup-Vorgang protokollieren (max. BACKUP_LOG_MAX, neueste zuerst) — 1.0.4.
    Rückgabe: aktualisierte Liste.
    """
    entry: dict[str, Any] = {
        "ts": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": bool(ok),
        "dest": str(dest) if dest else "",
        "source": str(source) if source else "",
        "message": (message or "").strip(),
    }
    items = [entry] + [e for e in load_backup_log() if isinstance(e, dict)]
    items = items[:BACKUP_LOG_MAX]
    path = backup_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "entries": items}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return items


def clear_backup_log() -> None:
    """Backup-Log leeren (Datei zurücksetzen) — 1.0.5."""
    path = backup_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "entries": []}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def format_backup_log_line(entry: dict[str, Any]) -> str:
    """Eine lesbare Zeile für Settings-Liste — 1.0.4."""
    ts = str(entry.get("ts") or "?")
    ok = bool(entry.get("ok", True))
    status = "OK" if ok else "FEHLER"
    dest = str(entry.get("dest") or "").strip()
    source = str(entry.get("source") or "").strip()
    msg = str(entry.get("message") or "").strip()
    target = dest or source or msg or "—"
    if dest and source and source not in dest:
        target = f"{Path(source).name} → {dest}"
    elif dest:
        target = dest
    if msg and not ok:
        return f"[{ts}] {status}: {msg}"
    return f"[{ts}] {status}: {target}"


def filter_backup_log(
    entries: list[dict[str, Any]] | None = None,
    *,
    mode: str = "all",
) -> list[dict[str, Any]]:
    """
    Backup-Log nach Erfolg/Fehler filtern — 1.0.7.

    ``mode``: ``all`` | ``ok`` / ``success`` | ``error`` / ``fail`` / ``fehler``
    """
    items = list(entries) if entries is not None else load_backup_log()
    key = (mode or "all").strip().lower()
    if key in ("ok", "success", "erfolg"):
        return [e for e in items if isinstance(e, dict) and bool(e.get("ok", True))]
    if key in ("error", "fail", "fehler", "err"):
        return [e for e in items if isinstance(e, dict) and not bool(e.get("ok", True))]
    return [e for e in items if isinstance(e, dict)]


def sort_backup_log(
    entries: list[dict[str, Any]] | None = None,
    *,
    newest_first: bool = True,
) -> list[dict[str, Any]]:
    """
    Backup-Log sortieren (neueste zuerst / älteste zuerst) — 1.0.9.

    Sortierschlüssel: ``ts``-String (YYYY-MM-DD HH:MM:SS), Fallback Listenposition.
    """
    items = [e for e in (entries if entries is not None else load_backup_log()) if isinstance(e, dict)]

    def _key(pair: tuple[int, dict[str, Any]]) -> tuple[str, int]:
        i, e = pair
        ts = str(e.get("ts") or "")
        return (ts, i)

    indexed = list(enumerate(items))
    indexed.sort(key=_key, reverse=bool(newest_first))
    return [e for _i, e in indexed]


def default_backup_log_export_name(*, when: datetime | None = None) -> str:
    """Standard-Dateiname mit Zeitstempel für Backup-Log-TXT — 1.0.8."""
    ts = (when or datetime.now()).strftime("%Y%m%d-%H%M%S")
    return f"backup-log-{ts}.txt"


def export_backup_log_txt(
    path: str | Path,
    entries: list[dict[str, Any]] | None = None,
    *,
    utf8_bom: bool = True,
) -> Path:
    """
    Backup-Log als TXT exportieren (eine Zeile pro Eintrag) — 1.0.8.

    Schreibt UTF-8 mit BOM (``utf8_bom=True``, Standard) für Excel.
    """
    items = list(entries) if entries is not None else load_backup_log()
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [format_backup_log_line(e) for e in items if isinstance(e, dict)]
    header = (
        f"# InstantLens Doc Backup-Log\n"
        f"# Einträge: {len(lines)}\n"
        f"# Export: {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')}\n"
    )
    body = "\n".join(lines)
    text = header + (body + "\n" if body else "(leer)\n")
    if utf8_bom:
        out.write_text(_UTF8_BOM + text, encoding="utf-8")
    else:
        out.write_text(text, encoding="utf-8")
    return out


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
