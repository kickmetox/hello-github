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
    scroll_y: int = 0  # Vertikale Scroll-Position (PDF/Editor) — 0.9.1
    # scale (oben): Zoom-Level pro Tab — Restore mit Vorrang vor Fit/Default (0.9.2)
    label: str = ""  # Anzeige-Label (≠ Dateiname) — 0.9.4


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
    # Haupt-Splitter Sidebar/Viewer Größen (Pixel) — 0.9.3
    splitter_sizes: List[int] = field(default_factory=list)
    # Theme dark|light je Session — 0.9.4
    theme: str = ""


def session_path() -> Path:
    return config_dir() / SESSION_NAME


def _normalize_secondary_kind(kind: str | None) -> str:
    k = str(kind or "").strip().lower()
    if k in ("pdf", "editor"):
        return k
    return ""


def _normalize_splitter_sizes(raw) -> List[int]:
    """Zwei positive Ints [sidebar, viewer]; sonst leer."""
    if not isinstance(raw, (list, tuple)) or len(raw) < 2:
        return []
    out: List[int] = []
    for v in raw[:2]:
        try:
            n = int(v)
        except (TypeError, ValueError):
            return []
        if n <= 0:
            return []
        out.append(n)
    return out


def _normalize_theme(raw) -> str:
    t = str(raw or "").strip().lower()
    if t in ("dark", "light"):
        return t
    return ""


def _normalize_label(raw) -> str:
    return str(raw or "").strip()


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
        try:
            scroll_y = int(item.get("scroll_y") or 0)
        except (TypeError, ValueError):
            scroll_y = 0
        tabs.append(
            SessionTab(
                path=str(Path(p)),
                page=int(item.get("page") or 0),
                scale=float(item.get("scale") or 1.5),
                kind=str(item.get("kind") or ""),
                scroll_y=max(0, scroll_y),
                label=_normalize_label(item.get("label")),
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
    splitter_sizes = _normalize_splitter_sizes(raw.get("splitter_sizes"))
    theme = _normalize_theme(raw.get("theme"))
    return SessionState(
        tabs=tabs,
        active=active,
        restore=restore,
        secondary_path=secondary_path,
        secondary_kind=secondary_kind,
        sync_scroll=sync_scroll,
        splitter_sizes=splitter_sizes,
        theme=theme,
    )


def save_session(state: SessionState) -> None:
    path = session_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tabs_payload = []
    for i, t in enumerate(state.tabs[:SESSION_MAX_TABS]):
        d = asdict(t)
        d["order"] = i  # Reihenfolge der Session-Tabs (Drag in Sidebar)
        d["label"] = _normalize_label(d.get("label"))
        tabs_payload.append(d)
    sec_path = str(state.secondary_path or "").strip()
    if sec_path and not Path(sec_path).is_file():
        sec_path = ""
    sizes = _normalize_splitter_sizes(getattr(state, "splitter_sizes", None))
    payload = {
        "restore": state.restore,
        "active": int(state.active),
        "tabs": tabs_payload,
        "secondary_path": sec_path,
        "secondary_kind": _normalize_secondary_kind(state.secondary_kind),
        "sync_scroll": bool(state.sync_scroll),
        "splitter_sizes": sizes,
        "theme": _normalize_theme(getattr(state, "theme", "")),
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
    scroll_y: int = 0,
    tab_states: Optional[dict] = None,
    restore: bool = True,
    secondary_path: Optional[str] = None,
    secondary_kind: Optional[str] = None,
    sync_scroll: bool = False,
    splitter_sizes: Optional[List[int]] = None,
    theme: Optional[str] = None,
    tab_labels: Optional[dict] = None,
) -> SessionState:
    """
    tab_states: optional {path: {page, scale, scroll_y}} für Last-Page/Zoom/Scroll je Tab (0.9.1/0.9.2).
    splitter_sizes: optional [sidebar_px, viewer_px] — Haupt-Splitter (0.9.3).
    theme: optional dark|light — Session-Theme (0.9.4).
    tab_labels: optional {path: Anzeige-Label} — Tab-Titel ≠ Dateiname (0.9.4).
    """
    tabs: List[SessionTab] = []
    seen: set[str] = set()
    states = tab_states if isinstance(tab_states, dict) else {}
    labels = tab_labels if isinstance(tab_labels, dict) else {}

    def _state_for(key: str) -> dict:
        if key in states and isinstance(states[key], dict):
            return states[key]
        # path_key-Varianten (normiert / roh)
        for k, v in states.items():
            try:
                if str(Path(str(k))) == key and isinstance(v, dict):
                    return v
            except Exception:
                continue
        return {}

    def _label_for(key: str) -> str:
        if key in labels:
            return _normalize_label(labels.get(key))
        for k, v in labels.items():
            try:
                if str(Path(str(k))) == key:
                    return _normalize_label(v)
            except Exception:
                continue
        st = _state_for(key)
        return _normalize_label(st.get("label"))

    for p in paths:
        key = str(Path(p))
        if key in seen or not Path(key).is_file():
            continue
        seen.add(key)
        st = _state_for(key)
        try:
            t_page = max(0, int(st.get("page", 0) or 0))
        except (TypeError, ValueError):
            t_page = 0
        try:
            t_scale = float(st.get("scale", 1.5) or 1.5)
        except (TypeError, ValueError):
            t_scale = 1.5
        try:
            t_scroll = max(0, int(st.get("scroll_y", 0) or 0))
        except (TypeError, ValueError):
            t_scroll = 0
        tabs.append(
            SessionTab(
                path=key,
                page=t_page,
                scale=t_scale,
                scroll_y=t_scroll,
                label=_label_for(key),
            )
        )
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
                t.scroll_y = max(0, int(scroll_y))
                break
        else:
            if Path(ap).is_file():
                tabs.append(
                    SessionTab(
                        path=ap,
                        page=max(0, int(page)),
                        scale=float(scale),
                        scroll_y=max(0, int(scroll_y)),
                        label=_label_for(ap),
                    )
                )
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
        splitter_sizes=_normalize_splitter_sizes(splitter_sizes),
        theme=_normalize_theme(theme),
    )
