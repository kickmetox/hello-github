"""Lokale Dokument-Kommentare an Textstellen — ildcomments-v1 Sidecar — 2.6.22.

Feedback ohne Änderung des Fließtexts. Keine Cloud-Echtzeit-Kollaboration.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Sequence

COMMENTS_SCHEMA_ID = "ildcomments-v1"
COMMENTS_VERSION = 1
COMMENT_LIMIT = 2000


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def comments_path_for(doc_path: str | Path) -> Path:
    p = Path(doc_path)
    return p.with_suffix(p.suffix + ".ildcomments.json")


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class DocComment:
    id: str
    author: str
    ts: str
    start: int
    end: int
    anchor_text: str
    body: str
    resolved: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "author": self.author,
            "ts": self.ts,
            "start": int(self.start),
            "end": int(self.end),
            "anchor_text": self.anchor_text,
            "body": self.body,
            "resolved": bool(self.resolved),
        }

    @classmethod
    def from_dict(cls, data: object) -> "DocComment":
        if not isinstance(data, dict):
            return cls(
                id=_new_id(),
                author="unknown",
                ts=_now_iso(),
                start=0,
                end=0,
                anchor_text="",
                body="",
            )
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
            author=str(data.get("author") or "unknown").strip() or "unknown",
            ts=str(data.get("ts") or "").strip() or _now_iso(),
            start=max(0, start),
            end=max(0, end),
            anchor_text=str(data.get("anchor_text") or ""),
            body=str(data.get("body") or ""),
            resolved=bool(data.get("resolved")),
        )


@dataclass
class CommentStore:
    """Kommentare neben dem Dokument: ``*.ildcomments.json``."""

    doc_path: Path
    author: str = "local"
    comments: List[DocComment] = field(default_factory=list)
    dirty: bool = False

    def __post_init__(self) -> None:
        self.doc_path = Path(self.doc_path)
        self.author = str(self.author or "local").strip() or "local"

    @property
    def path(self) -> Path:
        return comments_path_for(self.doc_path)

    @classmethod
    def for_doc(cls, doc_path: str | Path, *, load: bool = True) -> "CommentStore":
        store = cls(doc_path=Path(doc_path))
        if load and store.path.is_file():
            try:
                store.load()
            except Exception:
                store.comments = []
                store.dirty = False
        return store

    def set_author(self, author: str, *, save: bool = True) -> str:
        self.author = str(author or "").strip() or "local"
        self.dirty = True
        if save:
            try:
                self.save()
            except Exception:
                pass
        return self.author

    def add(
        self,
        body: str,
        *,
        start: int = 0,
        end: int | None = None,
        anchor_text: str = "",
        author: str | None = None,
        save: bool = True,
    ) -> DocComment:
        s = max(0, int(start))
        e = int(end) if end is not None else s + len(anchor_text or "")
        if e < s:
            e = s
        entry = DocComment(
            id=_new_id(),
            author=str(author or self.author or "local").strip() or "local",
            ts=_now_iso(),
            start=s,
            end=e,
            anchor_text=str(anchor_text or ""),
            body=str(body or "").strip(),
            resolved=False,
        )
        self.comments.append(entry)
        if len(self.comments) > COMMENT_LIMIT:
            self.comments = self.comments[-COMMENT_LIMIT:]
        self.dirty = True
        if save:
            try:
                self.save()
            except Exception:
                pass
        return entry

    def list_comments(
        self,
        *,
        author: str | None = None,
        unresolved_only: bool = False,
        limit: int = 200,
    ) -> list[DocComment]:
        items = list(self.comments)
        act = str(author or "").strip()
        if act:
            items = [c for c in items if c.author == act]
        if unresolved_only:
            items = [c for c in items if not c.resolved]
        k = max(0, int(limit))
        if k <= 0:
            return []
        return items[-k:]

    def get(self, comment_id: str) -> Optional[DocComment]:
        cid = str(comment_id or "").strip()
        for c in self.comments:
            if c.id == cid:
                return c
        return None

    def resolve(self, comment_id: str, *, resolved: bool = True, save: bool = True) -> bool:
        c = self.get(comment_id)
        if c is None:
            return False
        c.resolved = bool(resolved)
        self.dirty = True
        if save:
            try:
                self.save()
            except Exception:
                pass
        return True

    def update_body(self, comment_id: str, body: str, *, save: bool = True) -> bool:
        c = self.get(comment_id)
        if c is None:
            return False
        c.body = str(body or "").strip()
        self.dirty = True
        if save:
            try:
                self.save()
            except Exception:
                pass
        return True

    def delete(self, comment_id: str, *, save: bool = True) -> bool:
        cid = str(comment_id or "").strip()
        before = len(self.comments)
        self.comments = [c for c in self.comments if c.id != cid]
        if len(self.comments) == before:
            return False
        self.dirty = True
        if save:
            try:
                self.save()
            except Exception:
                pass
        return True

    def clear(self, *, save: bool = True) -> int:
        n = len(self.comments)
        self.comments = []
        self.dirty = True
        if save:
            try:
                self.save()
            except Exception:
                pass
        return n

    def summary(self) -> dict[str, Any]:
        open_n = sum(1 for c in self.comments if not c.resolved)
        authors = sorted({c.author for c in self.comments if c.author})
        return {
            "author": self.author,
            "total": len(self.comments),
            "open": open_n,
            "resolved": len(self.comments) - open_n,
            "authors": authors,
            "path": str(self.path),
        }

    def _payload(self) -> dict[str, Any]:
        return {
            "version": COMMENTS_VERSION,
            "schema": COMMENTS_SCHEMA_ID,
            "doc": str(self.doc_path),
            "author": self.author,
            "saved_at": _now_iso(),
            "count": len(self.comments),
            "comments": [c.to_dict() for c in self.comments],
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
            raise ValueError("ildcomments: Wurzel muss Objekt sein")
        ver = data.get("version")
        schema = data.get("schema")
        if ver is not None and int(ver) != COMMENTS_VERSION:
            raise ValueError(f"ildcomments: inkompatible Version {ver}")
        if schema is not None and str(schema) != COMMENTS_SCHEMA_ID:
            raise ValueError(f"ildcomments: inkompatibles Schema {schema!r}")
        self.author = str(data.get("author") or "local").strip() or "local"
        raw = data.get("comments") or []
        if not isinstance(raw, list):
            raise ValueError("ildcomments: comments muss Liste sein")
        self.comments = [DocComment.from_dict(x) for x in raw]
        if len(self.comments) > COMMENT_LIMIT:
            self.comments = self.comments[-COMMENT_LIMIT:]
        self.dirty = False


def format_comments_summary(
    comments: Sequence[DocComment], *, max_items: int = 20
) -> str:
    items = list(comments)[-max(0, int(max_items)) :]
    if not items:
        return "(keine Kommentare)"
    lines: list[str] = []
    for c in items:
        ts = c.ts.replace("T", " ").replace("+00:00", " UTC")
        status = "resolved" if c.resolved else "open"
        body = (c.body or "").replace("\n", " ")
        if len(body) > 48:
            body = body[:47] + "…"
        anchor = (c.anchor_text or "").replace("\n", " ")
        if len(anchor) > 24:
            anchor = anchor[:23] + "…"
        lines.append(
            f"{ts}  @{c.author}  [{status}]  {c.start}:{c.end}  "
            f"„{anchor}“ — {body}"
        )
    return "\n".join(lines)
