"""Gemeinsames Review / Shared Collaboration — ildshare-v1 — 2.6.23.

Praktische Kollaboration ohne Pflicht-Cloud:
- Lokaler Freigabeordner (NAS / OneDrive / SMB / USB) mit Bundle ``session.ildshare.json``
- Optionaler einfacher HTTP-Endpoint (GET/PUT JSON-Bundle)
- Tauscht Kommentare (2.6.21), Review-Änderungen (2.6.21) und Annotationen/Stempel/Notizen
  (2.6.9 / ildann) zwischen Teilnehmern
- Offline bleibt voll nutzbar; Sync ist best-effort

Kein Ersatz für Echtzeit-CRDT; Polling/manuelles Sync. Kein freier KI-Chat.
"""

from __future__ import annotations

import json
import shutil
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, List, Literal, Optional, Sequence

SHARE_SCHEMA_ID = "ildshare-v1"
SHARE_VERSION = 1
SESSION_FILENAME = "session.ildshare.json"
ITEM_LIMIT = 5000
POLL_DEFAULT_SEC = 8

ShareKind = Literal[
    "comment",
    "note",
    "highlight",
    "stamp",
    "review_change",
    "annotation",
]

LIMITATIONS_DE = (
    "Lokaler Freigabeordner und optionaler HTTP-Endpoint — kein gehosteter "
    "InstantLens-Cloud-Dienst. Kein simultanes Bearbeiten desselben Textes "
    "(kein CRDT); Konfliktlösung: letzte Änderung gewinnt (updated_at). "
    "Polling ≈ alle 8 s wenn Auto-Sync aktiv. Offline: lokale Sidecars bleiben "
    "nutzbar; Sync später. Freier KI-Chat bleibt Stub."
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def session_path_for(share_dir: str | Path) -> Path:
    d = Path(share_dir)
    if d.is_file() and d.name.endswith(".ildshare.json"):
        return d
    return d / SESSION_FILENAME


def resolve_share_dir(share: str | Path) -> Path:
    """Ordner oder Bundle-Pfad → Session-Verzeichnis."""
    p = Path(share)
    if p.is_file():
        return p.parent
    return p


@dataclass
class ShareParticipant:
    id: str
    name: str
    joined_at: str
    last_seen: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "joined_at": self.joined_at,
            "last_seen": self.last_seen or self.joined_at,
        }

    @classmethod
    def from_dict(cls, data: object) -> "ShareParticipant":
        if not isinstance(data, dict):
            return cls(id=_new_id(), name="unknown", joined_at=_now_iso())
        return cls(
            id=str(data.get("id") or _new_id()),
            name=str(data.get("name") or "unknown").strip() or "unknown",
            joined_at=str(data.get("joined_at") or "").strip() or _now_iso(),
            last_seen=str(data.get("last_seen") or data.get("joined_at") or "").strip()
            or _now_iso(),
        )


@dataclass
class ShareItem:
    id: str
    kind: ShareKind
    author: str
    ts: str
    updated_at: str
    payload: dict[str, Any] = field(default_factory=dict)
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "author": self.author,
            "ts": self.ts,
            "updated_at": self.updated_at,
            "payload": dict(self.payload or {}),
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: object) -> "ShareItem":
        if not isinstance(data, dict):
            return cls(
                id=_new_id(),
                kind="annotation",
                author="unknown",
                ts=_now_iso(),
                updated_at=_now_iso(),
            )
        kind_raw = str(data.get("kind") or "annotation").strip().lower()
        allowed: set[str] = {
            "comment",
            "note",
            "highlight",
            "stamp",
            "review_change",
            "annotation",
        }
        kind: ShareKind = kind_raw if kind_raw in allowed else "annotation"  # type: ignore[assignment]
        payload = data.get("payload")
        if not isinstance(payload, dict):
            payload = {}
        ts = str(data.get("ts") or "").strip() or _now_iso()
        return cls(
            id=str(data.get("id") or payload.get("id") or _new_id()),
            kind=kind,
            author=str(data.get("author") or payload.get("author") or "unknown").strip()
            or "unknown",
            ts=ts,
            updated_at=str(data.get("updated_at") or ts).strip() or ts,
            payload=dict(payload),
            source=str(data.get("source") or ""),
        )


def _kind_for_annotation(ann: dict[str, Any]) -> ShareKind:
    t = str(ann.get("type") or "").strip().lower()
    if t in ("sticky", "note", "text"):
        return "note"
    if t in ("highlight", "underline", "strikeout", "squiggly"):
        return "highlight"
    if t in ("stamp", "custom_stamp"):
        return "stamp"
    return "annotation"


def _ts_key(value: str) -> str:
    return str(value or "").strip()


def _merge_items(existing: Sequence[ShareItem], incoming: Sequence[ShareItem]) -> list[ShareItem]:
    by_id: dict[str, ShareItem] = {i.id: i for i in existing}
    for item in incoming:
        prev = by_id.get(item.id)
        if prev is None or _ts_key(item.updated_at) >= _ts_key(prev.updated_at):
            by_id[item.id] = item
    items = list(by_id.values())
    items.sort(key=lambda x: (_ts_key(x.updated_at), x.id))
    if len(items) > ITEM_LIMIT:
        items = items[-ITEM_LIMIT:]
    return items


@dataclass
class SharedReviewSession:
    """Eine Review-Session im Freigabeordner (oder via Endpoint)."""

    share_dir: Path
    session_id: str = ""
    title: str = ""
    created_at: str = ""
    updated_at: str = ""
    host: str = "local"
    doc_name: str = ""
    doc_path_hint: str = ""
    endpoint: str = ""
    participants: List[ShareParticipant] = field(default_factory=list)
    items: List[ShareItem] = field(default_factory=list)
    dirty: bool = False

    def __post_init__(self) -> None:
        self.share_dir = Path(self.share_dir)
        if not self.session_id:
            self.session_id = _new_id()
        if not self.created_at:
            self.created_at = _now_iso()
        if not self.updated_at:
            self.updated_at = self.created_at

    @property
    def path(self) -> Path:
        return session_path_for(self.share_dir)

    def summary(self) -> dict[str, Any]:
        kinds: dict[str, int] = {}
        for it in self.items:
            kinds[it.kind] = kinds.get(it.kind, 0) + 1
        return {
            "session_id": self.session_id,
            "title": self.title,
            "host": self.host,
            "doc_name": self.doc_name,
            "share_dir": str(self.share_dir),
            "path": str(self.path),
            "endpoint": self.endpoint or None,
            "participants": [p.to_dict() for p in self.participants],
            "participant_count": len(self.participants),
            "item_count": len(self.items),
            "kinds": kinds,
            "updated_at": self.updated_at,
            "limitations": LIMITATIONS_DE,
            "schema": SHARE_SCHEMA_ID,
        }

    def to_payload(self) -> dict[str, Any]:
        return {
            "version": SHARE_VERSION,
            "schema": SHARE_SCHEMA_ID,
            "session_id": self.session_id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "host": self.host,
            "doc_name": self.doc_name,
            "doc_path_hint": self.doc_path_hint,
            "endpoint": self.endpoint or None,
            "participants": [p.to_dict() for p in self.participants],
            "items": [i.to_dict() for i in self.items],
            "limitations": LIMITATIONS_DE,
            "count": len(self.items),
        }

    def save(self, path: Optional[Path] = None) -> Path:
        target = Path(path) if path else self.path
        target.parent.mkdir(parents=True, exist_ok=True)
        self.updated_at = _now_iso()
        payload = self.to_payload()
        # atomar schreiben
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(target)
        self.dirty = False
        return target

    @classmethod
    def from_payload(cls, share_dir: str | Path, data: dict[str, Any]) -> "SharedReviewSession":
        sess = cls(share_dir=Path(share_dir))
        ver = data.get("version")
        schema = data.get("schema")
        if ver is not None and int(ver) != SHARE_VERSION:
            raise ValueError(f"ildshare: inkompatible Version {ver}")
        if schema is not None and str(schema) != SHARE_SCHEMA_ID:
            raise ValueError(f"ildshare: inkompatibles Schema {schema!r}")
        sess.session_id = str(data.get("session_id") or _new_id())
        sess.title = str(data.get("title") or "")
        sess.created_at = str(data.get("created_at") or "").strip() or _now_iso()
        sess.updated_at = str(data.get("updated_at") or sess.created_at)
        sess.host = str(data.get("host") or "local").strip() or "local"
        sess.doc_name = str(data.get("doc_name") or "")
        sess.doc_path_hint = str(data.get("doc_path_hint") or "")
        ep = data.get("endpoint")
        sess.endpoint = str(ep or "").strip()
        parts = data.get("participants") or []
        sess.participants = [
            ShareParticipant.from_dict(p) for p in parts if isinstance(p, (dict,))
        ]
        raw_items = data.get("items") or []
        sess.items = [
            ShareItem.from_dict(i) for i in raw_items if isinstance(i, (dict,))
        ]
        if len(sess.items) > ITEM_LIMIT:
            sess.items = sess.items[-ITEM_LIMIT:]
        return sess

    @classmethod
    def load(cls, share: str | Path) -> "SharedReviewSession":
        share_dir = resolve_share_dir(share)
        path = session_path_for(share)
        if not path.is_file():
            raise FileNotFoundError(str(path))
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("ildshare: Wurzel muss Objekt sein")
        return cls.from_payload(share_dir, data)

    def upsert_participant(self, name: str) -> ShareParticipant:
        n = str(name or "").strip() or "local"
        now = _now_iso()
        for p in self.participants:
            if p.name.casefold() == n.casefold():
                p.last_seen = now
                self.dirty = True
                return p
        part = ShareParticipant(id=_new_id(), name=n, joined_at=now, last_seen=now)
        self.participants.append(part)
        self.dirty = True
        return part

    def set_endpoint(self, endpoint: str | None) -> str:
        self.endpoint = str(endpoint or "").strip()
        self.dirty = True
        return self.endpoint


def collect_local_items(doc_path: str | Path, *, author: str = "local") -> list[ShareItem]:
    """Lokale Sidecars → ShareItems (Kommentare, Review, Annotationen/Stempel)."""
    path = Path(doc_path)
    items: list[ShareItem] = []
    now = _now_iso()

    # Kommentare — 2.6.21
    try:
        from instantlensdoc.core.doc_comments import CommentStore

        cstore = CommentStore.for_doc(path, load=True)
        for c in cstore.comments:
            items.append(
                ShareItem(
                    id=c.id,
                    kind="comment",
                    author=c.author or author,
                    ts=c.ts or now,
                    updated_at=c.ts or now,
                    payload=c.to_dict(),
                    source="ildcomments",
                )
            )
    except Exception:
        pass

    # Review-Änderungen — 2.6.21
    try:
        from instantlensdoc.core.review import ReviewStore

        rstore = ReviewStore.for_doc(path, load=True)
        for ch in rstore.changes:
            items.append(
                ShareItem(
                    id=ch.id,
                    kind="review_change",
                    author=ch.author or author,
                    ts=ch.ts or now,
                    updated_at=ch.ts or now,
                    payload=ch.to_dict(),
                    source="ildreview",
                )
            )
    except Exception:
        pass

    # Annotationen / Notizen / Highlights / Stempel — 2.6.9
    try:
        from ild_pdf.annotate import AnnotationStore

        astore = AnnotationStore(path)
        for ann in astore.annotations:
            d = ann.to_dict()
            aid = str(d.get("id") or _new_id())
            kind = _kind_for_annotation(d)
            ts = str(d.get("modified") or d.get("created") or now)
            items.append(
                ShareItem(
                    id=aid,
                    kind=kind,
                    author=str(d.get("author") or author),
                    ts=ts,
                    updated_at=ts,
                    payload=d,
                    source="ildann",
                )
            )
    except Exception:
        pass

    return items


def apply_items_to_local(
    doc_path: str | Path,
    items: Sequence[ShareItem],
    *,
    author: str = "local",
) -> dict[str, int]:
    """ShareItems in lokale Sidecars mergen (last-write-wins)."""
    path = Path(doc_path)
    stats = {"comments": 0, "review": 0, "annotations": 0}

    comments = [i for i in items if i.kind == "comment"]
    reviews = [i for i in items if i.kind == "review_change"]
    anns = [
        i
        for i in items
        if i.kind in ("note", "highlight", "stamp", "annotation")
    ]

    if comments:
        try:
            from instantlensdoc.core.doc_comments import CommentStore, DocComment

            store = CommentStore.for_doc(path, load=True)
            by_id = {c.id: c for c in store.comments}
            for it in comments:
                payload = dict(it.payload or {})
                payload.setdefault("id", it.id)
                payload.setdefault("author", it.author)
                payload.setdefault("ts", it.ts)
                incoming = DocComment.from_dict(payload)
                prev = by_id.get(incoming.id)
                if prev is None or _ts_key(incoming.ts) >= _ts_key(prev.ts):
                    by_id[incoming.id] = incoming
                    stats["comments"] += 1
            store.comments = list(by_id.values())
            store.author = str(author or store.author or "local")
            store.save()
        except Exception:
            pass

    if reviews:
        try:
            from instantlensdoc.core.review import ReviewStore, TrackedChange

            store = ReviewStore.for_doc(path, load=True)
            by_id = {c.id: c for c in store.changes}
            for it in reviews:
                payload = dict(it.payload or {})
                payload.setdefault("id", it.id)
                payload.setdefault("author", it.author)
                payload.setdefault("ts", it.ts)
                incoming = TrackedChange.from_dict(payload)
                prev = by_id.get(incoming.id)
                if prev is None or _ts_key(incoming.ts) >= _ts_key(prev.ts):
                    by_id[incoming.id] = incoming
                    stats["review"] += 1
            store.changes = list(by_id.values())
            store.author = str(author or store.author or "local")
            store.save()
        except Exception:
            pass

    if anns:
        try:
            from ild_pdf.annotate import Annotation, AnnotationStore

            store = AnnotationStore(path)
            by_id = {str(a.id): a for a in store.annotations}
            for it in anns:
                payload = dict(it.payload or {})
                payload.setdefault("id", it.id)
                try:
                    incoming = Annotation.from_dict(payload)
                except Exception:
                    continue
                aid = str(incoming.id)
                prev = by_id.get(aid)
                prev_ts = ""
                if prev is not None:
                    prev_ts = str(
                        getattr(prev, "modified", None)
                        or getattr(prev, "created", None)
                        or ""
                    )
                new_ts = str(
                    getattr(incoming, "modified", None)
                    or getattr(incoming, "created", None)
                    or it.updated_at
                )
                if prev is None or _ts_key(new_ts) >= _ts_key(prev_ts):
                    by_id[aid] = incoming
                    stats["annotations"] += 1
            store.annotations = list(by_id.values())
            store.dirty = True
            store.save(force=True)
        except Exception:
            pass

    return stats


def fetch_endpoint_bundle(endpoint: str, *, timeout: float = 8.0) -> dict[str, Any] | None:
    """Optional: Bundle von einfachem HTTP-Endpoint laden (GET JSON)."""
    url = str(endpoint or "").strip()
    if not url:
        return None
    req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        data = json.loads(raw.decode("utf-8"))
        if isinstance(data, dict):
            return data
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, OSError):
        return None
    return None


def push_endpoint_bundle(
    endpoint: str,
    payload: dict[str, Any],
    *,
    timeout: float = 8.0,
) -> bool:
    """Optional: Bundle an Endpoint senden (PUT JSON; Fallback POST)."""
    url = str(endpoint or "").strip()
    if not url:
        return False
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    for method in ("PUT", "POST"):
        req = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                _ = resp.read()
            return True
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
            continue
    return False


def start_shared_review(
    doc_path: str | Path,
    share_dir: str | Path,
    *,
    author: str = "local",
    title: str = "",
    endpoint: str | None = None,
) -> dict[str, Any]:
    """Neue Session im Freigabeordner starten und lokale Items publishen."""
    doc = Path(doc_path)
    folder = resolve_share_dir(share_dir)
    folder.mkdir(parents=True, exist_ok=True)
    path = session_path_for(folder)
    if path.is_file():
        # bestehende Session erweitern statt überschreiben
        sess = SharedReviewSession.load(folder)
    else:
        sess = SharedReviewSession(
            share_dir=folder,
            title=str(title or doc.stem or "Review"),
            host=str(author or "local").strip() or "local",
            doc_name=doc.name,
            doc_path_hint=str(doc),
            endpoint=str(endpoint or "").strip(),
        )
    if title:
        sess.title = str(title)
    if endpoint is not None:
        sess.set_endpoint(endpoint)
    sess.doc_name = sess.doc_name or doc.name
    sess.doc_path_hint = str(doc)
    sess.upsert_participant(author)
    local_items = collect_local_items(doc, author=author)
    sess.items = _merge_items(sess.items, local_items)
    sess.save()
    if sess.endpoint:
        push_endpoint_bundle(sess.endpoint, sess.to_payload())
    data = sess.summary()
    data["ok"] = True
    data["published"] = len(local_items)
    data["action"] = "start"
    return data


def join_shared_review(
    share: str | Path,
    doc_path: str | Path,
    *,
    author: str = "local",
    apply: bool = True,
) -> dict[str, Any]:
    """Bestehende Session betreten; optional Items lokal anwenden."""
    folder = resolve_share_dir(share)
    sess = SharedReviewSession.load(folder)
    # optional Endpoint-Pull vor Join
    if sess.endpoint:
        remote = fetch_endpoint_bundle(sess.endpoint)
        if remote:
            try:
                remote_sess = SharedReviewSession.from_payload(folder, remote)
                sess.items = _merge_items(sess.items, remote_sess.items)
                for p in remote_sess.participants:
                    sess.upsert_participant(p.name)
            except Exception:
                pass
    sess.upsert_participant(author)
    sess.save()
    applied = {"comments": 0, "review": 0, "annotations": 0}
    if apply:
        applied = apply_items_to_local(doc_path, sess.items, author=author)
    data = sess.summary()
    data["ok"] = True
    data["applied"] = applied
    data["action"] = "join"
    return data


def sync_shared_review(
    share: str | Path,
    doc_path: str | Path,
    *,
    author: str = "local",
) -> dict[str, Any]:
    """Publish lokal → Share, Pull Share → lokal; optional Endpoint round-trip."""
    folder = resolve_share_dir(share)
    path = session_path_for(folder)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    sess = SharedReviewSession.load(folder)

    # Endpoint zuerst pullen
    endpoint_ok = None
    if sess.endpoint:
        remote = fetch_endpoint_bundle(sess.endpoint)
        if remote:
            try:
                remote_sess = SharedReviewSession.from_payload(folder, remote)
                sess.items = _merge_items(sess.items, remote_sess.items)
                endpoint_ok = True
            except Exception:
                endpoint_ok = False
        else:
            endpoint_ok = False

    before = len(sess.items)
    local_items = collect_local_items(doc_path, author=author)
    sess.items = _merge_items(sess.items, local_items)
    sess.upsert_participant(author)
    sess.save()

    applied = apply_items_to_local(doc_path, sess.items, author=author)

    pushed = None
    if sess.endpoint:
        pushed = push_endpoint_bundle(sess.endpoint, sess.to_payload())
        if endpoint_ok is None:
            endpoint_ok = pushed

    data = sess.summary()
    data["ok"] = True
    data["action"] = "sync"
    data["published"] = len(local_items)
    data["merged_total"] = len(sess.items)
    data["grew"] = max(0, len(sess.items) - before)
    data["applied"] = applied
    data["endpoint_ok"] = endpoint_ok
    data["endpoint_pushed"] = pushed
    return data


def shared_review_status(share: str | Path) -> dict[str, Any]:
    sess = SharedReviewSession.load(share)
    data = sess.summary()
    data["ok"] = True
    data["action"] = "status"
    data["exists"] = True
    return data


def shared_review_limitations() -> dict[str, Any]:
    return {
        "ok": True,
        "schema": SHARE_SCHEMA_ID,
        "limitations": LIMITATIONS_DE,
        "modes": ["folder", "endpoint"],
        "realtime": "polling",
        "poll_default_sec": POLL_DEFAULT_SEC,
        "offline": True,
        "integrates": ["ildcomments", "ildreview", "ildann"],
    }


def copy_session_bundle(share: str | Path, dest: str | Path) -> Path:
    """Session-Bundle kopieren (Backup / Weitergabe)."""
    src = session_path_for(share)
    if not src.is_file():
        raise FileNotFoundError(str(src))
    out = Path(dest)
    if out.is_dir():
        out = out / SESSION_FILENAME
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, out)
    return out
