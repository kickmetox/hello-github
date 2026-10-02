"""Zuletzt geöffnete Dateien (persistiert unter Config-Dir)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from instantlensdoc.config import config_dir

RECENT_MAX = 12


def recent_path() -> Path:
    return config_dir() / "recent.json"


def load_recent(max_items: int = RECENT_MAX) -> List[str]:
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
        if len(out) >= max_items:
            break
    return out


def save_recent(files: List[str], max_items: int = RECENT_MAX) -> None:
    path = recent_path()
    cleaned: List[str] = []
    seen: set[str] = set()
    for p in files:
        key = str(Path(p))
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(key)
        if len(cleaned) >= max_items:
            break
    path.write_text(
        json.dumps({"files": cleaned}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def add_recent(path: str | Path, max_items: int = RECENT_MAX) -> List[str]:
    path = str(Path(path))
    files = [path] + [p for p in load_recent(max_items=max_items * 2) if p != path]
    save_recent(files, max_items=max_items)
    return load_recent(max_items=max_items)


def clear_recent() -> None:
    save_recent([])
