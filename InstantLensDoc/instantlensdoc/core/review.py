"""Lokales Review / Track Changes — ildreview-v1 Sidecar — 2.6.26.

Protokolliert Einfügungen und Löschungen je Autor, ohne Cloud-Kollaboration.
"""

from __future__ import annotations

import difflib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Literal, Optional, Sequence

REVIEW_SCHEMA_ID = "ildreview-v1"
REVIEW_VERSION = 1
CHANGE_LIMIT = 2000

ChangeKind = Literal["insert", "delete"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def review_path_for(doc_path: str | Path) -> Path:
    p = Path(doc_path)
    return p.with_suffix(p.suffix + ".ildreview.json")


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class TrackedChange:
    id: str
    kind: ChangeKind
    author: str
    ts: str
    start: int
    end: int
    text: str
    accepted: Optional[bool] = None  # None=pending, True=accepted, False=rejected

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "kind": self.kind,
            "author": self.author,
            "ts": self.ts,
            "start": int(self.start),
            "end": int(self.end),
            "text": self.text,
        }
        if self.accepted is not None:
            d["accepted"] = bool(self.accepted)
        return d

    @classmethod
    def from_dict(cls, data: object) -> "TrackedChange":
        if not isinstance(data, dict):
            return cls(
                id=_new_id(),
                kind="insert",
                author="unknown",
                ts=_now_iso(),
                start=0,
                end=0,
                text="",
            )
        kind_raw = str(data.get("kind") or "insert").strip().lower()
        kind: ChangeKind = "delete" if kind_raw == "delete" else "insert"
        acc = data.get("accepted")
        accepted: Optional[bool]
        if acc is None:
            accepted = None
        else:
            accepted = bool(acc)
        try:
            start = int(data.get("start") or 0)
        except (TypeError, ValueError):
            start = 0
        try:
            end = int(data.get("end") or start)
        except (TypeError, ValueError):
            end = start
        return cls(
            id=str(data.get("id") or _new_id()),
            kind=kind,
            author=str(data.get("author") or "unknown").strip() or "unknown",
            ts=str(data.get("ts") or "").strip() or _now_iso(),
            start=max(0, start),
            end=max(0, end),
            text=str(data.get("text") or ""),
            accepted=accepted,
        )


@dataclass
class ReviewStore:
    """Änderungen nachverfolgen neben dem Dokument: ``*.ildreview.json``."""

    doc_path: Path
    enabled: bool = False
    author: str = "local"
    changes: List[TrackedChange] = field(default_factory=list)
    dirty: bool = False

    def __post_init__(self) -> None:
        self.doc_path = Path(self.doc_path)
        self.author = str(self.author or "local").strip() or "local"

    @property
    def path(self) -> Path:
        return review_path_for(self.doc_path)

    @classmethod
    def for_doc(cls, doc_path: str | Path, *, load: bool = True) -> "ReviewStore":
        store = cls(doc_path=Path(doc_path))
        if load and store.path.is_file():
            try:
                store.load()
            except Exception:
                store.changes = []
                store.enabled = False
                store.dirty = False
        return store

    def set_enabled(self, enabled: bool, *, save: bool = True) -> bool:
        self.enabled = bool(enabled)
        self.dirty = True
        if save:
            try:
                self.save()
            except Exception:
                pass
        return self.enabled

    def set_author(self, author: str, *, save: bool = True) -> str:
        self.author = str(author or "").strip() or "local"
        self.dirty = True
        if save:
            try:
                self.save()
            except Exception:
                pass
        return self.author

    def record(
        self,
        kind: ChangeKind,
        text: str,
        *,
        start: int = 0,
        end: int | None = None,
        author: str | None = None,
        save: bool = True,
    ) -> TrackedChange:
        s = max(0, int(start))
        e = int(end) if end is not None else s + len(text or "")
        if e < s:
            e = s
        entry = TrackedChange(
            id=_new_id(),
            kind="delete" if kind == "delete" else "insert",
            author=str(author or self.author or "local").strip() or "local",
            ts=_now_iso(),
            start=s,
            end=e,
            text=str(text or ""),
            accepted=None,
        )
        self.changes.append(entry)
        if len(self.changes) > CHANGE_LIMIT:
            self.changes = self.changes[-CHANGE_LIMIT:]
        self.dirty = True
        if save:
            try:
                self.save()
            except Exception:
                pass
        return entry

    def record_insert(
        self,
        text: str,
        *,
        start: int = 0,
        author: str | None = None,
        save: bool = True,
    ) -> TrackedChange:
        return self.record(
            "insert", text, start=start, author=author, save=save
        )

    def record_delete(
        self,
        text: str,
        *,
        start: int = 0,
        author: str | None = None,
        save: bool = True,
    ) -> TrackedChange:
        return self.record(
            "delete",
            text,
            start=start,
            end=start + len(text or ""),
            author=author,
            save=save,
        )

    def record_diff(
        self,
        before: str,
        after: str,
        *,
        author: str | None = None,
        save: bool = True,
    ) -> list[TrackedChange]:
        """Einfüge-/Lösch-Blöcke aus Text-Diff erzeugen (Review aktiv empfohlen)."""
        a = before or ""
        b = after or ""
        if a == b:
            return []
        sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
        created: list[TrackedChange] = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            if tag in ("delete", "replace") and i1 != i2:
                created.append(
                    self.record(
                        "delete",
                        a[i1:i2],
                        start=i1,
                        end=i2,
                        author=author,
                        save=False,
                    )
                )
            if tag in ("insert", "replace") and j1 != j2:
                created.append(
                    self.record(
                        "insert",
                        b[j1:j2],
                        start=j1,
                        end=j2,
                        author=author,
                        save=False,
                    )
                )
        self.dirty = True
        if save:
            try:
                self.save()
            except Exception:
                pass
        return created

    def pending(self) -> list[TrackedChange]:
        return [c for c in self.changes if c.accepted is None]

    def list_changes(
        self,
        *,
        author: str | None = None,
        pending_only: bool = False,
        limit: int = 200,
    ) -> list[TrackedChange]:
        items = list(self.changes)
        act = str(author or "").strip()
        if act:
            items = [c for c in items if c.author == act]
        if pending_only:
            items = [c for c in items if c.accepted is None]
        k = max(0, int(limit))
        if k <= 0:
            return []
        return items[-k:]

    def get(self, change_id: str) -> Optional[TrackedChange]:
        cid = str(change_id or "").strip()
        for c in self.changes:
            if c.id == cid:
                return c
        return None

    def accept(self, change_id: str, *, save: bool = True) -> bool:
        c = self.get(change_id)
        if c is None:
            return False
        c.accepted = True
        self.dirty = True
        if save:
            try:
                self.save()
            except Exception:
                pass
        return True

    def reject(self, change_id: str, *, save: bool = True) -> bool:
        c = self.get(change_id)
        if c is None:
            return False
        c.accepted = False
        self.dirty = True
        if save:
            try:
                self.save()
            except Exception:
                pass
        return True

    def accept_all(self, *, save: bool = True) -> int:
        n = 0
        for c in self.changes:
            if c.accepted is None:
                c.accepted = True
                n += 1
        if n:
            self.dirty = True
            if save:
                try:
                    self.save()
                except Exception:
                    pass
        return n

    def reject_all(self, *, save: bool = True) -> int:
        n = 0
        for c in self.changes:
            if c.accepted is None:
                c.accepted = False
                n += 1
        if n:
            self.dirty = True
            if save:
                try:
                    self.save()
                except Exception:
                    pass
        return n

    def clear(self, *, save: bool = True) -> int:
        n = len(self.changes)
        self.changes = []
        self.dirty = True
        if save:
            try:
                self.save()
            except Exception:
                pass
        return n

    def summary(self) -> dict[str, Any]:
        pending = self.pending()
        inserts = sum(1 for c in pending if c.kind == "insert")
        deletes = sum(1 for c in pending if c.kind == "delete")
        authors = sorted({c.author for c in self.changes if c.author})
        return {
            "enabled": self.enabled,
            "author": self.author,
            "total": len(self.changes),
            "pending": len(pending),
            "pending_inserts": inserts,
            "pending_deletes": deletes,
            "authors": authors,
            "path": str(self.path),
        }

    def _payload(self) -> dict[str, Any]:
        return {
            "version": REVIEW_VERSION,
            "schema": REVIEW_SCHEMA_ID,
            "doc": str(self.doc_path),
            "enabled": bool(self.enabled),
            "author": self.author,
            "saved_at": _now_iso(),
            "count": len(self.changes),
            "changes": [c.to_dict() for c in self.changes],
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
            raise ValueError("ildreview: Wurzel muss Objekt sein")
        ver = data.get("version")
        schema = data.get("schema")
        if ver is not None and int(ver) != REVIEW_VERSION:
            raise ValueError(f"ildreview: inkompatible Version {ver}")
        if schema is not None and str(schema) != REVIEW_SCHEMA_ID:
            raise ValueError(f"ildreview: inkompatibles Schema {schema!r}")
        self.enabled = bool(data.get("enabled"))
        self.author = str(data.get("author") or "local").strip() or "local"
        raw = data.get("changes") or []
        if not isinstance(raw, list):
            raise ValueError("ildreview: changes muss Liste sein")
        self.changes = [TrackedChange.from_dict(x) for x in raw]
        if len(self.changes) > CHANGE_LIMIT:
            self.changes = self.changes[-CHANGE_LIMIT:]
        self.dirty = False


def format_review_summary(changes: Sequence[TrackedChange], *, max_items: int = 20) -> str:
    items = list(changes)[-max(0, int(max_items)) :]
    if not items:
        return "(keine Änderungen)"
    lines: list[str] = []
    for c in items:
        ts = c.ts.replace("T", " ").replace("+00:00", " UTC")
        status = (
            "pending"
            if c.accepted is None
            else ("accepted" if c.accepted else "rejected")
        )
        sample = (c.text or "").replace("\n", " ")
        if len(sample) > 40:
            sample = sample[:39] + "…"
        lines.append(
            f"{ts}  {c.kind}  @{c.author}  [{status}]  "
            f"{c.start}:{c.end}  „{sample}“"
        )
    return "\n".join(lines)
