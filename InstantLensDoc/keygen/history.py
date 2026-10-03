"""Lokale Keygen-History (letzte N Keys) — ohne Secrets in Logs — 1.1.3."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List

HISTORY_MAX = 10
_log = logging.getLogger("instantlensdoc.keygen")


def history_path() -> Path:
    from instantlensdoc.config import config_dir

    return config_dir() / "keygen_history.json"


def load_history(max_items: int = HISTORY_MAX) -> List[dict[str, Any]]:
    """Einträge laden: [{email, days, key, created}, …] neueste zuerst."""
    path = history_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("entries") or []
    except Exception:
        _log.warning("keygen history load failed (file unreadable)")
        return []
    out: List[dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        key = str(raw.get("key") or "").strip()
        if not key:
            continue
        try:
            days = int(raw.get("days") or 0)
        except (TypeError, ValueError):
            days = 0
        out.append(
            {
                "email": str(raw.get("email") or ""),
                "days": days,
                "key": key,
                "created": str(raw.get("created") or ""),
            }
        )
        if len(out) >= max(1, int(max_items)):
            break
    return out


def save_history(entries: List[dict[str, Any]], max_items: int = HISTORY_MAX) -> None:
    """History speichern; Logs enthalten keine Keys."""
    limit = max(1, int(max_items))
    cleaned: List[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in entries:
        if not isinstance(raw, dict):
            continue
        key = str(raw.get("key") or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        try:
            days = int(raw.get("days") or 0)
        except (TypeError, ValueError):
            days = 0
        cleaned.append(
            {
                "email": str(raw.get("email") or ""),
                "days": days,
                "key": key,
                "created": str(raw.get("created") or ""),
            }
        )
        if len(cleaned) >= limit:
            break
    path = history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"entries": cleaned, "version": 1}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    # Keine Keys/Secrets in Logs
    _log.info("keygen history saved (%d entries)", len(cleaned))


def add_history(
    *,
    email: str,
    key: str,
    days: int,
    max_items: int = HISTORY_MAX,
) -> List[dict[str, Any]]:
    """Key vorne einfügen (max HISTORY_MAX); Rückgabe aktuelle Liste."""
    key = (key or "").strip()
    if not key:
        return load_history(max_items=max_items)
    entry = {
        "email": (email or "").strip(),
        "days": int(days),
        "key": key,
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    existing = [e for e in load_history(max_items=max_items * 2) if e.get("key") != key]
    entries = [entry] + existing
    save_history(entries, max_items=max_items)
    return load_history(max_items=max_items)


def clear_history() -> None:
    """History leeren."""
    path = history_path()
    if path.exists():
        try:
            path.unlink()
        except Exception:
            save_history([])
    _log.info("keygen history cleared")
