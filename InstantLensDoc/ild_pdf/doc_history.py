"""Lokale Dokument-Änderungslog-Datei (ildhist-v1) — Zeitstempel letzter Aktionen."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Sequence

HIST_SCHEMA_ID = "ildhist-v1"
HIST_VERSION = 1
HISTORY_ENTRY_LIMIT = 200


def history_path_for(pdf_path: str | Path) -> Path:
    p = Path(pdf_path)
    return p.with_suffix(p.suffix + ".ildhist.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class HistoryEntry:
    ts: str
    action: str
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "ts": self.ts,
            "action": str(self.action or "").strip(),
            "detail": str(self.detail or ""),
        }

    @classmethod
    def from_dict(cls, data: object) -> "HistoryEntry":
        if not isinstance(data, dict):
            return cls(ts=_now_iso(), action="unknown")
        ts = str(data.get("ts") or "").strip() or _now_iso()
        action = str(data.get("action") or "").strip() or "unknown"
        detail = str(data.get("detail") or "")
        return cls(ts=ts, action=action, detail=detail)


@dataclass
class DocHistory:
    """Änderungslog neben dem PDF: ``*.ildhist.json``."""

    pdf_path: Path
    entries: List[HistoryEntry] = field(default_factory=list)
    dirty: bool = False

    def __post_init__(self) -> None:
        self.pdf_path = Path(self.pdf_path)

    @property
    def path(self) -> Path:
        return history_path_for(self.pdf_path)

    @classmethod
    def for_pdf(cls, pdf_path: str | Path, *, load: bool = True) -> "DocHistory":
        hist = cls(pdf_path=Path(pdf_path))
        if load and hist.path.is_file():
            try:
                hist.load()
            except Exception:
                hist.entries = []
                hist.dirty = False
        return hist

    def append(self, action: str, detail: str = "", *, save: bool = True) -> HistoryEntry:
        entry = HistoryEntry(ts=_now_iso(), action=str(action or "").strip() or "unknown", detail=str(detail or ""))
        self.entries.append(entry)
        if len(self.entries) > HISTORY_ENTRY_LIMIT:
            self.entries = self.entries[-HISTORY_ENTRY_LIMIT:]
        self.dirty = True
        if save:
            try:
                self.save()
            except Exception:
                pass
        return entry

    def last_entries(self, n: int = 20) -> list[HistoryEntry]:
        k = max(0, int(n))
        if k <= 0:
            return []
        return list(self.entries[-k:])

    def last_action_ts(self) -> str:
        if not self.entries:
            return ""
        return str(self.entries[-1].ts or "")

    def _payload(self) -> dict:
        return {
            "version": HIST_VERSION,
            "schema": HIST_SCHEMA_ID,
            "pdf": str(self.pdf_path),
            "saved_at": _now_iso(),
            "count": len(self.entries),
            "entries": [e.to_dict() for e in self.entries],
        }

    def save(self, path: Optional[Path] = None) -> Path:
        target = Path(path) if path else self.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self._payload(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self.dirty = False
        return target

    def load(self, path: Optional[Path] = None) -> None:
        target = Path(path) if path else self.path
        data = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("ildhist: Wurzel muss Objekt sein")
        ver = data.get("version")
        schema = data.get("schema")
        if ver is not None and int(ver) != HIST_VERSION:
            raise ValueError(f"ildhist: inkompatible Version {ver}")
        if schema is not None and str(schema) != HIST_SCHEMA_ID:
            raise ValueError(f"ildhist: inkompatibles Schema {schema!r}")
        raw = data.get("entries") or []
        if not isinstance(raw, list):
            raise ValueError("ildhist: entries muss Liste sein")
        self.entries = [HistoryEntry.from_dict(x) for x in raw]
        if len(self.entries) > HISTORY_ENTRY_LIMIT:
            self.entries = self.entries[-HISTORY_ENTRY_LIMIT:]
        self.dirty = False


def append_doc_history(
    pdf_path: str | Path | None,
    action: str,
    detail: str = "",
) -> Optional[HistoryEntry]:
    """Kurzform: Eintrag anhängen wenn pdf_path gesetzt."""
    if not pdf_path:
        return None
    hist = DocHistory.for_pdf(pdf_path, load=True)
    return hist.append(action, detail, save=True)


def format_history_summary(entries: Sequence[HistoryEntry], *, max_items: int = 10) -> str:
    """Kurzer Anzeigetext für Dialog/Status."""
    items = list(entries)[-max(0, int(max_items)) :]
    if not items:
        return "(keine Einträge)"
    lines: list[str] = []
    for e in items:
        ts = e.ts.replace("T", " ").replace("+00:00", " UTC")
        detail = f" — {e.detail}" if e.detail else ""
        lines.append(f"{ts}  {e.action}{detail}")
    return "\n".join(lines)
