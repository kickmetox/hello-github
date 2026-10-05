"""Plugin-/Script-Hooks: Aliase on_open/on_save/on_scan + Menü-Plugins.

Erweitert ``instantlensdoc.core.plugin_hooks`` um die in der Doku genannten
Hook-Punkte, ohne das bestehende Event-Schema zu brechen.
"""

from __future__ import annotations

from typing import Any, Callable

from instantlensdoc.core import plugin_hooks as _ph

MenuCallback = Callable[[], None]


def ensure_extended_events() -> None:
    """Idempotent: on_scan / Aliase in plugin_hooks registrieren."""
    extra = (
        "document.scanned",
        "on_open",
        "on_save",
        "on_scan",
    )
    known = list(_ph.KNOWN_EVENTS)
    for ev in extra:
        if ev not in known:
            known.append(ev)
    _ph.KNOWN_EVENTS = tuple(known)  # type: ignore[misc]
    _ph.EVENT_DESCRIPTIONS.update(
        {
            "document.scanned": "Scan importiert / Gerätelauf fertig (Hook-Punkt)",
            "on_open": "Alias für document.opened (Skript-Doku)",
            "on_save": "Alias für document.saved (Skript-Doku)",
            "on_scan": "Alias für document.scanned (Skript-Doku)",
        }
    )


def notify_open(path: str, **payload: Any) -> int:
    ensure_extended_events()
    data = {"path": path, **payload}
    n = _ph.emit("document.opened", data)
    n += _ph.emit("on_open", data)
    return n


def notify_save(path: str, **payload: Any) -> int:
    ensure_extended_events()
    data = {"path": path, **payload}
    n = _ph.emit("document.saved", data)
    n += _ph.emit("on_save", data)
    return n


def notify_scan(path: str = "", **payload: Any) -> int:
    """Vom Scan-Worker aufrufbar — scan/devices werden hier nicht geändert."""
    ensure_extended_events()
    data = {"path": path, **payload}
    n = _ph.emit("document.scanned", data)
    n += _ph.emit("on_scan", data)
    return n


def register_menu_plugin(
    title: str,
    callback: MenuCallback,
    *,
    menu: str = "Extras",
    shortcut: str = "",
) -> dict[str, Any]:
    ensure_extended_events()
    rec = {
        "title": title,
        "callback": callback,
        "menu": menu,
        "shortcut": shortcut,
    }
    _ph._menu_plugins.append(rec)  # type: ignore[attr-defined]
    return {"ok": True, "title": title, "menu": menu}


def iter_menu_plugins() -> list[dict[str, Any]]:
    ensure_extended_events()
    return list(getattr(_ph, "_menu_plugins", []) or [])


def install_sample_plugin(directory: str | None = None) -> str:
    """Beispiel-Plugin in den Hooks-Ordner schreiben."""
    from pathlib import Path

    root = _ph.hooks_dir(directory)
    dest = Path(root) / "ild_dtp_sample_plugin.py"
    dest.write_text(_SAMPLE, encoding="utf-8")
    _ph.load_plugins(root)
    return str(dest)


_SAMPLE = '''\
"""Beispiel-Plugin InstantLens Doc — on_open / on_save / on_scan + Menü."""

from instantlensdoc.features.plugins import register_menu_plugin


def on_open(**payload):
    return True


def on_save(**payload):
    return True


def on_scan(**payload):
    return True


def on_document_opened(**payload):
    on_open(**payload)


def register(api=None):
    def _ping():
        pass

    register_menu_plugin("Beispiel-Plugin: Ping", _ping, menu="Extras")
'''
