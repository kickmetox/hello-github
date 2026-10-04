"""Lokale Dokument-Änderungslog-Datei (ildhist-v1) — Zeitstempel letzter Aktionen."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Sequence

HIST_SCHEMA_ID = "ildhist-v1"
HIST_VERSION = 1
HISTORY_ENTRY_LIMIT = 200

_PAGE_RE = re.compile(r"(?:^|[;\s,])page\s*=\s*(\d+)", re.IGNORECASE)


def history_path_for(pdf_path: str | Path) -> Path:
    p = Path(pdf_path)
    return p.with_suffix(p.suffix + ".ildhist.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_page_from_detail(detail: str) -> Optional[int]:
    """Seitenindex (0-basiert) aus Detail-Text ``page=N`` lesen — 2.2.2."""
    m = _PAGE_RE.search(str(detail or ""))
    if not m:
        return None
    try:
        return int(m.group(1))
    except (TypeError, ValueError):
        return None


@dataclass
class HistoryEntry:
    ts: str
    action: str
    detail: str = ""
    page: Optional[int] = None  # optional 0-basiert — 2.2.2

    def resolved_page(self) -> Optional[int]:
        """Explizites ``page``-Feld oder aus Detail geparst."""
        if self.page is not None:
            try:
                return int(self.page)
            except (TypeError, ValueError):
                pass
        return parse_page_from_detail(self.detail)

    def to_dict(self) -> dict:
        d = {
            "ts": self.ts,
            "action": str(self.action or "").strip(),
            "detail": str(self.detail or ""),
        }
        if self.page is not None:
            try:
                d["page"] = int(self.page)
            except (TypeError, ValueError):
                pass
        return d

    @classmethod
    def from_dict(cls, data: object) -> "HistoryEntry":
        if not isinstance(data, dict):
            return cls(ts=_now_iso(), action="unknown")
        ts = str(data.get("ts") or "").strip() or _now_iso()
        action = str(data.get("action") or "").strip() or "unknown"
        detail = str(data.get("detail") or "")
        page: Optional[int] = None
        if "page" in data and data.get("page") is not None:
            try:
                page = int(data["page"])
            except (TypeError, ValueError):
                page = None
        if page is None:
            page = parse_page_from_detail(detail)
        return cls(ts=ts, action=action, detail=detail, page=page)


@dataclass
class DocHistory:
    """Änderungslog neben dem PDF: ``*.ildhist.json``."""

    pdf_path: Path
    entries: List[HistoryEntry] = field(default_factory=list)
    dirty: bool = False
    # Session-Snapshot vor letztem Clear für Undo — 2.2.4
    _clear_undo: Optional[List[HistoryEntry]] = field(
        default=None, repr=False, compare=False
    )
    # Session-Snapshot nach Undo Clear für Redo — 2.2.5
    _clear_redo: Optional[List[HistoryEntry]] = field(
        default=None, repr=False, compare=False
    )

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

    def append(
        self,
        action: str,
        detail: str = "",
        *,
        page: int | None = None,
        save: bool = True,
    ) -> HistoryEntry:
        detail_s = str(detail or "")
        page_i: Optional[int] = None
        if page is not None:
            try:
                page_i = int(page)
            except (TypeError, ValueError):
                page_i = None
        if page_i is None:
            page_i = parse_page_from_detail(detail_s)
        entry = HistoryEntry(
            ts=_now_iso(),
            action=str(action or "").strip() or "unknown",
            detail=detail_s,
            page=page_i,
        )
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

    def clear(self, *, save: bool = True, action: str | None = None) -> int:
        """
        Einträge löschen — Rückgabe: Anzahl entfernt.

        Ohne ``action``: alles. Mit ``action``: nur Einträge dieses Typs — 2.2.3.
        Speichert Session-Snapshot für ``undo_clear`` — 2.2.4.
        Neues Clear invalidiert Redo — 2.2.5.
        """
        # Snapshot vor Clear (tiefe Kopie) — Undo Clear — 2.2.4
        self._clear_undo = [
            HistoryEntry.from_dict(e.to_dict()) for e in self.entries
        ]
        self._clear_redo = None  # neues Clear → Redo verwerfen — 2.2.5
        act = str(action or "").strip()
        if act and act not in ("*", "alle", "all", ""):
            before = len(self.entries)
            self.entries = [e for e in self.entries if e.action != act]
            n = before - len(self.entries)
        else:
            n = len(self.entries)
            self.entries = []
        self.dirty = True
        if save:
            try:
                self.save()
            except Exception:
                pass
        return n

    def clear_filtered(self, action: str | None, *, save: bool = True) -> int:
        """Nur aktuellen Filter (Aktionstyp) löschen — 2.2.3."""
        return self.clear(save=save, action=action)

    def can_undo_clear(self) -> bool:
        """True wenn Session-Snapshot nach Clear verfügbar — 2.2.4."""
        return self._clear_undo is not None

    def can_redo_clear(self) -> bool:
        """True wenn Session-Snapshot nach Undo Clear verfügbar — 2.2.5."""
        return self._clear_redo is not None

    def undo_clear(self, *, save: bool = True) -> bool:
        """
        Letztes Clear rückgängig machen (Session-Snapshot) — 2.2.4.
        Speichert aktuellen Stand für ``redo_clear`` — 2.2.5.

        Rückgabe: True wenn wiederhergestellt, sonst False.
        """
        if self._clear_undo is None:
            return False
        # Aktueller (geleerter) Stand → Redo — 2.2.5
        self._clear_redo = [
            HistoryEntry.from_dict(e.to_dict()) for e in self.entries
        ]
        self.entries = [
            HistoryEntry.from_dict(e.to_dict()) for e in self._clear_undo
        ]
        self._clear_undo = None
        self.dirty = True
        if save:
            try:
                self.save()
            except Exception:
                pass
        return True

    def redo_clear(self, *, save: bool = True) -> bool:
        """
        Clear nach Undo erneut anwenden (Session-Snapshot) — 2.2.5.

        Rückgabe: True wenn angewendet, sonst False.
        """
        if self._clear_redo is None:
            return False
        # Aktueller Stand → Undo wieder möglich
        self._clear_undo = [
            HistoryEntry.from_dict(e.to_dict()) for e in self.entries
        ]
        self.entries = [
            HistoryEntry.from_dict(e.to_dict()) for e in self._clear_redo
        ]
        self._clear_redo = None
        self.dirty = True
        if save:
            try:
                self.save()
            except Exception:
                pass
        return True

    def last_entries(self, n: int = 20) -> list[HistoryEntry]:
        k = max(0, int(n))
        if k <= 0:
            return []
        return list(self.entries[-k:])

    def action_types(self) -> list[str]:
        """Sortierte eindeutige Aktionstypen (für Filter)."""
        return sorted({str(e.action or "").strip() for e in self.entries if e.action})

    def filter_entries(
        self,
        action: str | None = None,
        *,
        limit: int = 50,
    ) -> list[HistoryEntry]:
        """Letzte ``limit`` Einträge, optional gefiltert nach Aktionstyp — 2.2.1."""
        items = list(self.entries)
        act = str(action or "").strip()
        if act and act not in ("*", "alle", "all", ""):
            items = [e for e in items if e.action == act]
        k = max(0, int(limit))
        if k <= 0:
            return []
        return items[-k:]

    def export_json(
        self,
        path: str | Path,
        *,
        action: str | None = None,
        limit: int | None = None,
        filtered: bool = False,
    ) -> Path:
        """
        Stand als JSON exportieren (ildhist-v1 Payload).

        ``filtered=True`` oder ``action`` gesetzt: nur gefilterte Sicht — 2.2.3.
        """
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        use_filter = bool(filtered) or (
            action is not None
            and str(action).strip()
            and str(action).strip() not in ("*", "alle", "all", "")
        )
        if use_filter:
            lim = int(limit) if limit is not None else HISTORY_ENTRY_LIMIT
            entries = self.filter_entries(action, limit=lim)
            payload = self._payload_for_entries(entries, filter_action=action)
        else:
            payload = self._payload()
        target.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return target

    def export_filtered_json(
        self,
        path: str | Path,
        action: str | None = None,
        *,
        limit: int = 50,
    ) -> Path:
        """Gefilterte Sicht als JSON exportieren — 2.2.3."""
        return self.export_json(path, action=action, limit=limit, filtered=True)

    def last_action_ts(self) -> str:
        if not self.entries:
            return ""
        return str(self.entries[-1].ts or "")

    def _payload(self) -> dict:
        return self._payload_for_entries(self.entries)

    def _payload_for_entries(
        self,
        entries: Sequence[HistoryEntry],
        *,
        filter_action: str | None = None,
    ) -> dict:
        items = list(entries)
        payload: dict = {
            "version": HIST_VERSION,
            "schema": HIST_SCHEMA_ID,
            "pdf": str(self.pdf_path),
            "saved_at": _now_iso(),
            "count": len(items),
            "entries": [e.to_dict() for e in items],
        }
        act = str(filter_action or "").strip()
        if act and act not in ("*", "alle", "all", ""):
            payload["filter_action"] = act
            payload["filtered"] = True
        return payload

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
    *,
    page: int | None = None,
) -> Optional[HistoryEntry]:
    """Kurzform: Eintrag anhängen wenn pdf_path gesetzt."""
    if not pdf_path:
        return None
    hist = DocHistory.for_pdf(pdf_path, load=True)
    return hist.append(action, detail, page=page, save=True)


def format_history_summary(entries: Sequence[HistoryEntry], *, max_items: int = 10) -> str:
    """Kurzer Anzeigetext für Dialog/Status."""
    items = list(entries)[-max(0, int(max_items)) :]
    if not items:
        return "(keine Einträge)"
    lines: list[str] = []
    for e in items:
        ts = e.ts.replace("T", " ").replace("+00:00", " UTC")
        pg = e.resolved_page()
        page_bit = f" [S.{pg + 1}]" if pg is not None else ""
        detail = f" — {e.detail}" if e.detail else ""
        lines.append(f"{ts}  {e.action}{page_bit}{detail}")
    return "\n".join(lines)
