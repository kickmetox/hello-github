"""Session: offene Dokument-Tabs wiederherstellen (Reihenfolge = Sidebar-Drag)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

from instantlensdoc.config import config_dir

SESSION_NAME = "session.json"
SESSION_MAX_TABS = 16


@dataclass
class SessionTab:
    path: str
    page: int = 0
    scale: float = 1.5
    kind: str = ""  # optional Hinweis


@dataclass
class SessionState:
    tabs: List[SessionTab] = field(default_factory=list)
    active: int = 0
    restore: bool = True
    # Doc-Split Zweit-Panel (0.6.8): Pfad + Typ pdf|editor — je Session gemerkt
    secondary_path: str = ""
    secondary_kind: str = ""
    # Doc-Split Sync-Scroll (0.6.9): Zustand je Session gemerkt
    sync_scroll: bool = False


def session_path() -> Path:
    return config_dir() / SESSION_NAME


def _normalize_secondary_kind(kind: str | None) -> str:
    k = str(kind or "").strip().lower()
    if k in ("pdf", "editor"):
        return k
    return ""


def load_session() -> SessionState:
    path = session_path()
    if not path.is_file():
        return SessionState()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return SessionState()
    tabs: List[SessionTab] = []
    # Explizite order-Indizes (0.6.1+) oder Listenreihenfolge
    items = list(raw.get("tabs") or [])
    ordered: list[tuple[int, dict]] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        try:
            ord_i = int(item.get("order", i))
        except (TypeError, ValueError):
            ord_i = i
        ordered.append((ord_i, item))
    ordered.sort(key=lambda t: t[0])
    for _ord, item in ordered:
        p = str(item.get("path") or "").strip()
        if not p or not Path(p).is_file():
            continue
        tabs.append(
            SessionTab(
                path=str(Path(p)),
                page=int(item.get("page") or 0),
                scale=float(item.get("scale") or 1.5),
                kind=str(item.get("kind") or ""),
            )
        )
        if len(tabs) >= SESSION_MAX_TABS:
            break
    active = int(raw.get("active") or 0)
    if active < 0 or active >= len(tabs):
        active = max(0, len(tabs) - 1) if tabs else 0
    restore = bool(raw.get("restore", True))
    sec_raw = str(raw.get("secondary_path") or "").strip()
    secondary_path = str(Path(sec_raw)) if sec_raw and Path(sec_raw).is_file() else ""
    secondary_kind = _normalize_secondary_kind(raw.get("secondary_kind"))
    if secondary_path and not secondary_kind:
        secondary_kind = "pdf" if Path(secondary_path).suffix.lower() == ".pdf" else "editor"
    sync_scroll = bool(raw.get("sync_scroll", False))
    return SessionState(
        tabs=tabs,
        active=active,
        restore=restore,
        secondary_path=secondary_path,
        secondary_kind=secondary_kind,
        sync_scroll=sync_scroll,
    )


def save_session(state: SessionState) -> None:
    path = session_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tabs_payload = []
    for i, t in enumerate(state.tabs[:SESSION_MAX_TABS]):
        d = asdict(t)
        d["order"] = i  # Reihenfolge der Session-Tabs (Drag in Sidebar)
        tabs_payload.append(d)
    sec_path = str(state.secondary_path or "").strip()
    if sec_path and not Path(sec_path).is_file():
        sec_path = ""
    payload = {
        "restore": state.restore,
        "active": state.active,
        "tabs": tabs_payload,
        "secondary_path": sec_path,
        "secondary_kind": _normalize_secondary_kind(state.secondary_kind),
        "sync_scroll": bool(state.sync_scroll),
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def clear_session() -> None:
    save_session(SessionState())


def build_session(
    paths: List[str],
    *,
    active_path: Optional[str] = None,
    page: int = 0,
    scale: float = 1.5,
    restore: bool = True,
    secondary_path: Optional[str] = None,
    secondary_kind: Optional[str] = None,
    sync_scroll: bool = False,
) -> SessionState:
    tabs: List[SessionTab] = []
    seen: set[str] = set()
    for p in paths:
        key = str(Path(p))
        if key in seen or not Path(key).is_file():
            continue
        seen.add(key)
        tabs.append(SessionTab(path=key, page=0, scale=1.5))
        if len(tabs) >= SESSION_MAX_TABS:
            break
    active = 0
    if active_path:
        ap = str(Path(active_path))
        for i, t in enumerate(tabs):
            if t.path == ap:
                active = i
                t.page = max(0, int(page))
                t.scale = float(scale)
                break
        else:
            if Path(ap).is_file():
                tabs.append(SessionTab(path=ap, page=max(0, int(page)), scale=float(scale)))
                active = len(tabs) - 1
    sec = str(secondary_path or "").strip()
    if sec and Path(sec).is_file():
        sec = str(Path(sec))
    else:
        sec = ""
    kind = _normalize_secondary_kind(secondary_kind)
    if sec and not kind:
        kind = "pdf" if Path(sec).suffix.lower() == ".pdf" else "editor"
    return SessionState(
        tabs=tabs,
        active=active,
        restore=restore,
        secondary_path=sec,
        secondary_kind=kind,
        sync_scroll=bool(sync_scroll),
    )
