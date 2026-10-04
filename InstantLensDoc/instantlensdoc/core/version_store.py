"""Lokaler Versionsverlauf (Snapshots) — ildversions-v1 — 2.6.23.

Speichert/restored Dokumentstände neben der Datei unter ``*.ildversions/``.
"""

from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

VERSIONS_SCHEMA_ID = "ildversions-v1"
VERSIONS_VERSION = 1
VERSION_LIMIT = 50


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def versions_dir_for(doc_path: str | Path) -> Path:
    p = Path(doc_path)
    return p.parent / f"{p.name}.ildversions"


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class VersionEntry:
    id: str
    label: str
    ts: str
    kind: str  # text | binary
    size: int
    filename: str
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "ts": self.ts,
            "kind": self.kind,
            "size": int(self.size),
            "filename": self.filename,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: object) -> "VersionEntry":
        if not isinstance(data, dict):
            return cls(
                id=_new_id(),
                label="",
                ts=_now_iso(),
                kind="text",
                size=0,
                filename="",
            )
        try:
            size = int(data.get("size") or 0)
        except (TypeError, ValueError):
            size = 0
        return cls(
            id=str(data.get("id") or _new_id()),
            label=str(data.get("label") or ""),
            ts=str(data.get("ts") or "").strip() or _now_iso(),
            kind=str(data.get("kind") or "text").strip() or "text",
            size=max(0, size),
            filename=str(data.get("filename") or ""),
            note=str(data.get("note") or ""),
        )


@dataclass
class VersionStore:
    """Versionsindex + Snapshot-Dateien unter ``{doc}.ildversions/``."""

    doc_path: Path
    entries: List[VersionEntry] = field(default_factory=list)
    dirty: bool = False

    def __post_init__(self) -> None:
        self.doc_path = Path(self.doc_path)

    @property
    def root(self) -> Path:
        return versions_dir_for(self.doc_path)

    @property
    def index_path(self) -> Path:
        return self.root / "index.json"

    @classmethod
    def for_doc(cls, doc_path: str | Path, *, load: bool = True) -> "VersionStore":
        store = cls(doc_path=Path(doc_path))
        if load and store.index_path.is_file():
            try:
                store.load()
            except Exception:
                store.entries = []
                store.dirty = False
        return store

    def _ensure_root(self) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        return self.root

    def save_version(
        self,
        *,
        label: str = "",
        note: str = "",
        text: str | None = None,
        source: str | Path | None = None,
    ) -> VersionEntry:
        """
        Snapshot speichern.

        - ``text`` gesetzt → Text-Snapshot (``.txt``)
        - sonst ``source`` oder ``doc_path`` als Binärkopie
        """
        self._ensure_root()
        vid = _new_id()
        ts = _now_iso()
        lbl = str(label or "").strip() or f"Version {len(self.entries) + 1}"
        if text is not None:
            kind = "text"
            filename = f"{vid}.txt"
            payload = self.root / filename
            data = text if isinstance(text, str) else str(text)
            payload.write_text(data, encoding="utf-8")
            size = len(data.encode("utf-8"))
        else:
            kind = "binary"
            src = Path(source) if source is not None else self.doc_path
            if not src.is_file():
                raise FileNotFoundError(str(src))
            suffix = src.suffix or ".bin"
            filename = f"{vid}{suffix}"
            payload = self.root / filename
            shutil.copy2(src, payload)
            size = int(payload.stat().st_size)
        entry = VersionEntry(
            id=vid,
            label=lbl,
            ts=ts,
            kind=kind,
            size=size,
            filename=filename,
            note=str(note or ""),
        )
        self.entries.append(entry)
        while len(self.entries) > VERSION_LIMIT:
            old = self.entries.pop(0)
            old_path = self.root / old.filename
            if old_path.is_file():
                try:
                    old_path.unlink()
                except Exception:
                    pass
        self.dirty = True
        self.save_index()
        return entry

    def list_versions(self, *, limit: int = 50) -> list[VersionEntry]:
        k = max(0, int(limit))
        if k <= 0:
            return []
        return list(self.entries[-k:])

    def get(self, version_id: str) -> Optional[VersionEntry]:
        vid = str(version_id or "").strip()
        for e in self.entries:
            if e.id == vid:
                return e
        return None

    def payload_path(self, version_id: str) -> Optional[Path]:
        e = self.get(version_id)
        if e is None or not e.filename:
            return None
        p = self.root / e.filename
        return p if p.is_file() else None

    def read_text(self, version_id: str) -> str:
        e = self.get(version_id)
        if e is None:
            raise KeyError(version_id)
        path = self.payload_path(version_id)
        if path is None:
            raise FileNotFoundError(version_id)
        if e.kind == "text":
            return path.read_text(encoding="utf-8")
        # Binary: best-effort UTF-8 decode for restore into editor
        raw = path.read_bytes()
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("utf-8", errors="replace")

    def restore(
        self,
        version_id: str,
        *,
        dest: str | Path | None = None,
    ) -> Path:
        """Snapshot nach ``dest`` (Default: Dokumentpfad) zurückschreiben."""
        e = self.get(version_id)
        if e is None:
            raise KeyError(version_id)
        src = self.payload_path(version_id)
        if src is None:
            raise FileNotFoundError(version_id)
        target = Path(dest) if dest is not None else self.doc_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if e.kind == "text":
            target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            shutil.copy2(src, target)
        return target

    def delete(self, version_id: str) -> bool:
        e = self.get(version_id)
        if e is None:
            return False
        path = self.root / e.filename
        if path.is_file():
            try:
                path.unlink()
            except Exception:
                pass
        self.entries = [x for x in self.entries if x.id != e.id]
        self.dirty = True
        self.save_index()
        return True

    def summary(self) -> dict[str, Any]:
        return {
            "total": len(self.entries),
            "limit": VERSION_LIMIT,
            "root": str(self.root),
            "doc": str(self.doc_path),
            "latest": self.entries[-1].to_dict() if self.entries else None,
        }

    def _payload(self) -> dict[str, Any]:
        return {
            "version": VERSIONS_VERSION,
            "schema": VERSIONS_SCHEMA_ID,
            "doc": str(self.doc_path),
            "saved_at": _now_iso(),
            "count": len(self.entries),
            "entries": [e.to_dict() for e in self.entries],
        }

    def save_index(self) -> Path:
        self._ensure_root()
        self.index_path.write_text(
            json.dumps(self._payload(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self.dirty = False
        return self.index_path

    def load(self) -> None:
        data = json.loads(self.index_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("ildversions: Wurzel muss Objekt sein")
        ver = data.get("version")
        schema = data.get("schema")
        if ver is not None and int(ver) != VERSIONS_VERSION:
            raise ValueError(f"ildversions: inkompatible Version {ver}")
        if schema is not None and str(schema) != VERSIONS_SCHEMA_ID:
            raise ValueError(f"ildversions: inkompatibles Schema {schema!r}")
        raw = data.get("entries") or []
        if not isinstance(raw, list):
            raise ValueError("ildversions: entries muss Liste sein")
        self.entries = [VersionEntry.from_dict(x) for x in raw]
        if len(self.entries) > VERSION_LIMIT:
            self.entries = self.entries[-VERSION_LIMIT:]
        self.dirty = False
