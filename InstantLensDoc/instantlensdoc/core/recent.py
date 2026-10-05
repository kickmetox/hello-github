"""Zuletzt geöffnete Dateien (persistiert unter Config-Dir)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple

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


def load_recent_entries(max_items: int | None = None) -> List[Tuple[str, bool]]:
    """
    Recent-Einträge als [(pfad, existiert), …].
    Fehlende Dateien bleiben in der Liste (für graue Anzeige + Entfernen).
    """
    limit = _clamp_max(max_items)
    path = recent_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = [str(p) for p in data.get("files", []) if p]
    except Exception:
        return []
    out: List[Tuple[str, bool]] = []
    seen: set[str] = set()
    for p in items:
        key = str(Path(p))
        if key in seen:
            continue
        seen.add(key)
        exists = Path(p).is_file()
        out.append((key, exists))
        if len(out) >= limit:
            break
    return out


def load_recent(max_items: int | None = None, *, existing_only: bool = False) -> List[str]:
    """
    Recent-Pfade laden.
    Standard: inkl. fehlender Dateien. existing_only=True filtert wie früher.
    """
    entries = load_recent_entries(max_items=max_items)
    if existing_only:
        return [p for p, ok in entries if ok]
    return [p for p, _ok in entries]


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
    # Bestehende Liste inkl. fehlender behalten; neue Datei nach vorne
    files = [path] + [p for p in load_recent(max_items=limit * 2) if p != path]
    save_recent(files, max_items=limit)
    return load_recent(max_items=limit)


def remove_recent(path: str | Path, max_items: int | None = None) -> List[str]:
    """Einzelnen Pfad aus der Recent-Liste entfernen."""
    limit = _clamp_max(max_items)
    target = str(Path(path))
    files = [p for p in load_recent(max_items=limit * 2) if p != target]
    save_recent(files, max_items=limit)
    return load_recent(max_items=limit)


def prune_missing_recent(max_items: int | None = None) -> List[str]:
    """Einträge ohne Datei aus der persistierten Liste entfernen — 2.6.54."""
    limit = _clamp_max(max_items)
    kept = [p for p in load_recent(max_items=limit * 2) if Path(p).is_file()]
    save_recent(kept, max_items=limit)
    return load_recent(max_items=limit)


def clear_recent() -> None:
    save_recent([])


def trim_recent_to_max(max_items: int | None = None) -> List[str]:
    """Liste auf aktuelle Max-Anzahl kürzen und speichern."""
    files = load_recent(max_items=max_items)
    save_recent(files, max_items=max_items)
    return files
