"""Lokale Dateihistorie, unabhängig von Git."""

from __future__ import annotations

import difflib
import hashlib
import json
import time
from pathlib import Path


def _dir(workspace: Path, relative: str) -> Path:
    digest = hashlib.sha1(relative.encode("utf-8")).hexdigest()[:16]
    path = Path(workspace) / ".shatuide" / "history" / digest
    path.mkdir(parents=True, exist_ok=True)
    return path


def _index(folder: Path) -> list[dict]:
    path = folder / "index.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def snapshot(workspace: Path, relative: str, content: str, keep: int = 40) -> dict | None:
    folder = _dir(workspace, relative)
    items = _index(folder)
    digest = hashlib.sha1(content.encode("utf-8")).hexdigest()
    if items and items[-1].get("hash") == digest:
        return None
    stamp = time.strftime("%Y%m%d-%H%M%S")
    name = f"{stamp}-{digest[:8]}.txt"
    (folder / name).write_text(content, encoding="utf-8")
    entry = {"id": name, "hash": digest, "time": stamp, "bytes": len(content.encode("utf-8")), "path": relative}
    items.append(entry)
    items = items[-keep:]
    (folder / "index.json").write_text(json.dumps(items, indent=2), encoding="utf-8")
    # Alte Dateien entfernen, die nicht mehr im Index stehen.
    keep_names = {item["id"] for item in items}
    for child in folder.glob("*.txt"):
        if child.name not in keep_names:
            child.unlink(missing_ok=True)
    return entry


def list_snapshots(workspace: Path, relative: str) -> list[dict]:
    return list(reversed(_index(_dir(workspace, relative))))


def read_snapshot(workspace: Path, relative: str, snapshot_id: str) -> str:
    folder = _dir(workspace, relative)
    path = folder / snapshot_id
    if path.parent != folder or not path.is_file():
        raise FileNotFoundError(snapshot_id)
    return path.read_text(encoding="utf-8")


def diff_snapshot(workspace: Path, relative: str, snapshot_id: str, current: str) -> str:
    old = read_snapshot(workspace, relative, snapshot_id)
    lines = difflib.unified_diff(
        old.splitlines(),
        current.splitlines(),
        fromfile=snapshot_id,
        tofile=relative,
        lineterm="",
    )
    return "\n".join(lines)
