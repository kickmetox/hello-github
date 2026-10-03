"""Crash-Recovery: Autosave-Snapshots und Orphan-Wiederherstellung — 1.8.0."""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from instantlensdoc.config import config_dir

RECOVERY_SCHEMA = "ildrecovery-v1"
RECOVERY_DIR_NAME = "recovery"
Kind = Literal["text", "sidecar", "pdf"]


def recovery_dir() -> Path:
    d = config_dir() / RECOVERY_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_key(path: str | Path) -> str:
    """Stabiler Dateiname aus Absolutpfad (keine Pfadtrenner)."""
    raw = str(Path(path).resolve())
    out = []
    for ch in raw:
        if ch.isalnum() or ch in ("-", "_", "."):
            out.append(ch)
        else:
            out.append("_")
    key = "".join(out)
    if len(key) > 180:
        key = key[-180:]
    return key or "orphan"


@dataclass
class RecoveryOrphan:
    meta_path: Path
    source_path: str
    kind: str
    saved_at: float
    payload_path: Path
    label: str

    def age_seconds(self) -> float:
        return max(0.0, time.time() - float(self.saved_at or 0.0))


def write_recovery_snapshot(
    source_path: str | Path,
    *,
    kind: Kind,
    text: str | None = None,
    copy_from: str | Path | None = None,
    dirty: bool = True,
) -> Path | None:
    """
    Snapshot unter config/recovery schreiben (Meta-JSON + Payload).
    Nur bei dirty=True; Rückgabe: Meta-Pfad oder None.
    """
    if not dirty:
        return None
    src = Path(source_path)
    if not src:
        return None
    key = _safe_key(src)
    rdir = recovery_dir()
    meta_path = rdir / f"{key}.json"
    if kind == "text":
        payload = rdir / f"{key}.txt"
        payload.write_text(text if text is not None else "", encoding="utf-8")
    else:
        payload = rdir / f"{key}.bin"
        src_copy = Path(copy_from) if copy_from else src
        if not src_copy.is_file():
            return None
        shutil.copy2(src_copy, payload)
    meta: dict[str, Any] = {
        "schema": RECOVERY_SCHEMA,
        "version": 1,
        "source_path": str(src.resolve()) if src.exists() or src.parent.exists() else str(src),
        "kind": kind,
        "saved_at": time.time(),
        "dirty": True,
        "payload": payload.name,
        "label": src.name,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta_path


def clear_recovery_for(source_path: str | Path) -> None:
    """Orphan-Marker für Pfad entfernen (nach Speichern / Verwerfen)."""
    key = _safe_key(source_path)
    rdir = recovery_dir()
    meta_path = rdir / f"{key}.json"
    payload_names: list[str] = []
    if meta_path.is_file():
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            name = data.get("payload")
            if name:
                payload_names.append(str(name))
        except Exception:
            pass
        try:
            meta_path.unlink()
        except OSError:
            pass
    for name in payload_names or [f"{key}.txt", f"{key}.bin"]:
        p = rdir / name
        if p.is_file():
            try:
                p.unlink()
            except OSError:
                pass


def list_orphans(*, max_age_hours: float = 72.0) -> list[RecoveryOrphan]:
    """Dirty Orphans im Recovery-Ordner (älteste zuerst) — 1.8.4."""
    rdir = recovery_dir()
    out: list[RecoveryOrphan] = []
    cutoff = time.time() - max(1.0, float(max_age_hours)) * 3600.0
    for meta_path in rdir.glob("*.json"):
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("schema") != RECOVERY_SCHEMA:
            continue
        if not data.get("dirty", True):
            continue
        saved_at = float(data.get("saved_at") or 0.0)
        if saved_at and saved_at < cutoff:
            continue
        payload_name = str(data.get("payload") or "")
        payload = rdir / payload_name if payload_name else Path()
        if not payload.is_file():
            continue
        src = str(data.get("source_path") or "")
        if not src:
            continue
        out.append(
            RecoveryOrphan(
                meta_path=meta_path,
                source_path=src,
                kind=str(data.get("kind") or "text"),
                saved_at=saved_at,
                payload_path=payload,
                label=str(data.get("label") or Path(src).name),
            )
        )
    # Älteste zuerst (saved_at, Fallback mtime) — 1.8.4
    out.sort(
        key=lambda o: (
            float(o.saved_at or 0.0),
            o.meta_path.stat().st_mtime if o.meta_path.is_file() else 0.0,
        )
    )
    return out


def restore_orphan(orphan: RecoveryOrphan, *, dest: str | Path | None = None) -> Path:
    """
    Snapshot zurückschreiben.
    text → Zieldatei mit Payload-Inhalt; sidecar/pdf → Payload kopieren.
    """
    target = Path(dest) if dest else Path(orphan.source_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if orphan.kind == "text":
        text = orphan.payload_path.read_text(encoding="utf-8")
        target.write_text(text, encoding="utf-8")
    else:
        shutil.copy2(orphan.payload_path, target)
    clear_recovery_for(orphan.source_path)
    return target


def format_orphan_age(age_seconds: float) -> str:
    """Lesbares Snapshot-Alter — 1.8.2."""
    secs = max(0.0, float(age_seconds or 0.0))
    if secs < 60:
        return "gerade eben"
    mins = int(secs // 60)
    if mins < 60:
        return f"vor {mins} Min."
    hours = mins // 60
    rem_m = mins % 60
    if hours < 48:
        if rem_m:
            return f"vor {hours} Std. {rem_m} Min."
        return f"vor {hours} Std."
    days = hours // 24
    rem_h = hours % 24
    if rem_h:
        return f"vor {days} Tag{'en' if days != 1 else ''} {rem_h} Std."
    return f"vor {days} Tag{'en' if days != 1 else ''}"


def orphan_meta_preview(orphan: RecoveryOrphan) -> str:
    """
    Lesbare Snapshot-Metadaten für Dialog-Vorschau — 1.8.1; Alter 1.8.2.
    Pfad, Kind, Zeit, Alter, Größe, optional Text-Snippet.
    """
    from datetime import datetime

    try:
        ts = datetime.fromtimestamp(float(orphan.saved_at or 0.0)).strftime(
            "%d.%m.%Y %H:%M"
        )
    except Exception:
        ts = "—"
    size_b = 0
    try:
        if orphan.payload_path.is_file():
            size_b = int(orphan.payload_path.stat().st_size)
    except OSError:
        size_b = 0
    if size_b >= 1024 * 1024:
        size_s = f"{size_b / (1024 * 1024):.1f} MB"
    elif size_b >= 1024:
        size_s = f"{size_b / 1024:.1f} KB"
    else:
        size_s = f"{size_b} B"
    age_s = format_orphan_age(orphan.age_seconds())
    lines = [
        f"{orphan.label}",
        f"  Alter: {age_s}",
        f"  Art: {orphan.kind} · {size_s} · {ts}",
        f"  Pfad: {orphan.source_path}",
    ]
    if orphan.kind == "text" and orphan.payload_path.is_file():
        try:
            text = orphan.payload_path.read_text(encoding="utf-8", errors="replace")
            snippet = " ".join(text.strip().split())
            if len(snippet) > 80:
                snippet = snippet[:77] + "…"
            if snippet:
                lines.append(f"  Vorschau: {snippet}")
        except Exception:
            pass
    return "\n".join(lines)


def restore_orphan_as_copy(
    orphan: RecoveryOrphan, *, dest: str | Path | None = None
) -> Path:
    """
    Snapshot als Kopie öffnen (Originalpfad unberührt) — 1.8.3.
    Ohne dest: neben Quelle als ``{stem}_recovered{suffix}``.
    Original-Orphan bleibt bis explizitem Verwerfen.
    """
    if dest is not None:
        target = Path(dest)
    else:
        src = Path(orphan.source_path)
        target = src.with_name(f"{src.stem}_recovered{src.suffix or '.bin'}")
        if target.exists():
            n = 2
            while True:
                cand = src.with_name(f"{src.stem}_recovered{n}{src.suffix or '.bin'}")
                if not cand.exists():
                    target = cand
                    break
                n += 1
    target.parent.mkdir(parents=True, exist_ok=True)
    if orphan.kind == "text":
        text = orphan.payload_path.read_text(encoding="utf-8")
        target.write_text(text, encoding="utf-8")
    else:
        shutil.copy2(orphan.payload_path, target)
    # Orphan bewusst behalten — erst „Verwerfen“ räumt auf — 1.8.3
    return target


def discard_orphan(orphan: RecoveryOrphan) -> None:
    """Verwerfen: Meta + Payload orphan-sauber löschen — 1.8.1."""
    for p in (orphan.meta_path, orphan.payload_path):
        if p is None:
            continue
        try:
            if Path(p).is_file():
                Path(p).unlink()
        except OSError:
            pass
    # Alias-/Key-Varianten ebenfalls entfernen
    clear_recovery_for(orphan.source_path)
    # Falls Meta-Dateiname vom Key abweicht: leere Payload-Reste am Meta-Stem
    try:
        stem = orphan.meta_path.stem if orphan.meta_path else ""
        if stem:
            rdir = recovery_dir()
            for ext in (".txt", ".bin", ".json"):
                leftover = rdir / f"{stem}{ext}"
                if leftover.is_file():
                    try:
                        leftover.unlink()
                    except OSError:
                        pass
    except Exception:
        pass


def purge_stale_orphans(*, max_age_hours: float = 72.0) -> int:
    """Orphans älter als max_age_hours inkl. Payload löschen — 1.8.1."""
    rdir = recovery_dir()
    cutoff = time.time() - max(1.0, float(max_age_hours)) * 3600.0
    removed = 0
    for meta_path in list(rdir.glob("*.json")):
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("schema") != RECOVERY_SCHEMA:
            continue
        saved_at = float(data.get("saved_at") or 0.0)
        if saved_at and saved_at >= cutoff:
            continue
        payload_name = str(data.get("payload") or "")
        for p in (meta_path, rdir / payload_name if payload_name else None):
            if p is None:
                continue
            try:
                if Path(p).is_file():
                    Path(p).unlink()
                    removed += 1
            except OSError:
                pass
    return removed
