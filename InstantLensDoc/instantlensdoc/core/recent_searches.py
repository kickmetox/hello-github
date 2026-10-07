"""Letzte Suchbegriffe (persistiert unter Config-Dir)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from instantlensdoc.config import config_dir

SEARCH_MAX = 12
SEARCH_FILE = "recent_searches.json"


def recent_searches_path() -> Path:
    return config_dir() / SEARCH_FILE


def load_recent_searches(max_items: int = SEARCH_MAX) -> List[str]:
    path = recent_searches_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = [str(q).strip() for q in data.get("queries", []) if str(q).strip()]
    except Exception:
        return []
    out: List[str] = []
    seen: set[str] = set()
    for q in items:
        key = q.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(q)
        if len(out) >= max_items:
            break
    return out


def save_recent_searches(queries: List[str], max_items: int = SEARCH_MAX) -> None:
    cleaned: List[str] = []
    seen: set[str] = set()
    for q in queries:
        q = str(q).strip()
        if not q:
            continue
        key = q.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(q)
        if len(cleaned) >= max_items:
            break
    path = recent_searches_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"queries": cleaned}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def add_recent_search(query: str, max_items: int = SEARCH_MAX) -> List[str]:
    q = str(query).strip()
    if not q:
        return load_recent_searches(max_items=max_items)
    files = [q] + [p for p in load_recent_searches(max_items=max_items * 2) if p.casefold() != q.casefold()]
    save_recent_searches(files, max_items=max_items)
    return load_recent_searches(max_items=max_items)


def clear_recent_searches() -> None:
    save_recent_searches([])
