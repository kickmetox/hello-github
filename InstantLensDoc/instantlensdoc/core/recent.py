"""Zuletzt geöffnete Dateien (persistiert unter Config-Dir)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from instantlensdoc.config import config_dir

RECENT_MAX = 12
RECENT_MAX_MIN = 3
RECENT_MAX_MAX = 50


def recent_path() -> Path:
    return config_dir() / "recent.json"


def _clamp_max(max_items: int | None) -> int:
    if max_items is None:
        try:
            from instantlensdoc.core.app_settings import get_recent_files_max

            max_items = get_recent_files_max()
        except Exception:
            max_items = RECENT_MAX
    try:
        n = int(max_items)
    except (TypeError, ValueError):
        n = RECENT_MAX
    return max(RECENT_MAX_MIN, min(RECENT_MAX_MAX, n))


def load_recent(max_items: int | None = None) -> List[str]:
    limit = _clamp_max(max_items)
    path = recent_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = [str(p) for p in data.get("files", []) if p]
    except Exception:
        return []
    # Nur existierende Pfade behalten
    out: List[str] = []
    seen: set[str] = set()
    for p in items:
        key = str(Path(p))
        if key in seen:
            continue
        seen.add(key)
        if Path(p).is_file():
            out.append(str(Path(p)))
        if len(out) >= limit:
            break
    return out


def save_recent(files: List[str], max_items: int | None = None) -> None:
    limit = _clamp_max(max_items)
    path = recent_path()
    cleaned: List[str] = []
    seen: set[str] = set()
    for p in files:
        key = str(Path(p))
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(key)
        if len(cleaned) >= limit:
            break
    path.write_text(
        json.dumps({"files": cleaned}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def add_recent(path: str | Path, max_items: int | None = None) -> List[str]:
    limit = _clamp_max(max_items)
    path = str(Path(path))
    files = [path] + [p for p in load_recent(max_items=limit * 2) if p != path]
    save_recent(files, max_items=limit)
    return load_recent(max_items=limit)


def clear_recent() -> None:
    save_recent([])


def trim_recent_to_max(max_items: int | None = None) -> List[str]:
    """Liste auf aktuelle Max-Anzahl kürzen und speichern."""
    files = load_recent(max_items=max_items)
    save_recent(files, max_items=max_items)
    return files
