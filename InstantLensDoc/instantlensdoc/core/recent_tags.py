"""Zuletzt genutzte Annotation-Tags (persistiert unter Config-Dir) — 0.9.9."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from instantlensdoc.config import config_dir

TAG_MAX = 16
TAG_FILE = "recent_tags.json"


def recent_tags_path() -> Path:
    return config_dir() / TAG_FILE


def load_recent_tags(max_items: int = TAG_MAX) -> List[str]:
    path = recent_tags_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = [str(t).strip() for t in data.get("tags", []) if str(t).strip()]
    except Exception:
        return []
    out: List[str] = []
    seen: set[str] = set()
    for t in items:
        key = t.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
        if len(out) >= max_items:
            break
    return out


def save_recent_tags(tags: List[str], max_items: int = TAG_MAX) -> None:
    cleaned: List[str] = []
    seen: set[str] = set()
    for t in tags:
        t = str(t).strip()
        if not t:
            continue
        key = t.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(t)
        if len(cleaned) >= max_items:
            break
    path = recent_tags_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"tags": cleaned}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def add_recent_tag(tag: str, max_items: int = TAG_MAX) -> List[str]:
    t = str(tag).strip()
    if not t:
        return load_recent_tags(max_items=max_items)
    files = [t] + [
        p for p in load_recent_tags(max_items=max_items * 2) if p.casefold() != t.casefold()
    ]
    save_recent_tags(files, max_items=max_items)
    return load_recent_tags(max_items=max_items)


def clear_recent_tags() -> None:
    save_recent_tags([])
