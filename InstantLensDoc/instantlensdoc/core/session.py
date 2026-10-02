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


def session_path() -> Path:
    return config_dir() / SESSION_NAME


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
    return SessionState(tabs=tabs, active=active, restore=restore)


def save_session(state: SessionState) -> None:
    path = session_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tabs_payload = []
    for i, t in enumerate(state.tabs[:SESSION_MAX_TABS]):
        d = asdict(t)
        d["order"] = i  # Reihenfolge der Session-Tabs (Drag in Sidebar)
        tabs_payload.append(d)
    payload = {
        "restore": state.restore,
        "active": state.active,
        "tabs": tabs_payload,
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
    return SessionState(tabs=tabs, active=active, restore=restore)
