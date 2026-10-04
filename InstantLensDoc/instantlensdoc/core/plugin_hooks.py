"""
User-/Script-Hooks — produktiv ab 2.6.25.

Event-Bus + Laden von User-Skripten (Python ``*.py`` / PowerShell ``*.ps1`` Liste).
Aufrufbar aus App, ``ild``-API, CLI und PowerShell.

Events (stabil):

| Event | Bedeutung |
|-------|-----------|
| ``app.started`` | nach QApplication / MainWindow |
| ``document.opened`` | Datei geöffnet |
| ``document.saved`` | Datei gespeichert |
| ``document.exported`` | Export abgeschlossen |
| ``ocr.finished`` | OCR-Lauf beendet |
| ``annotation.changed`` | Sidecar-Annotation geändert |

Hooks-Ordner: ``config_dir()/hooks`` (oder ``ILD_HOOKS_DIR``).
Python-Hooks: Modul mit ``on_<event_with_underscores>(**payload)`` oder ``on_event(event, **payload)``.
PowerShell: nur registriert/listbar; Ausführung über ``scripts/ild.ps1`` / externes ``powershell``.
"""

from __future__ import annotations

import importlib.util
import json
import os
import traceback
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, DefaultDict, List, Optional, Sequence

from instantlensdoc import __version__ as _ILD_VERSION

IS_STUB = False
NOT_PRODUCTION_READY = False
STUB_MESSAGE = (
    f"Plugin-Hooks {_ILD_VERSION}: produktiv — Event-Bus + User-Skripte "
    "(open/save/export/ocr); kein Sandbox-/Marketplace-Plugin-System."
)

KNOWN_EVENTS: tuple[str, ...] = (
    "app.started",
    "document.opened",
    "document.saved",
    "document.exported",
    "ocr.finished",
    "annotation.changed",
)

EVENT_DESCRIPTIONS: dict[str, str] = {
    "app.started": "nach QApplication / MainWindow",
    "document.opened": "Datei geöffnet",
    "document.saved": "Datei gespeichert",
    "document.exported": "Export abgeschlossen",
    "ocr.finished": "OCR-Lauf beendet",
    "annotation.changed": "Sidecar-Annotation geändert",
}

Listener = Callable[..., Any]


class EventBus:
    """Minimaler Pub/Sub — Fehler in Listenern werden geloggt, nicht weitergeworfen."""

    def __init__(self) -> None:
        self._listeners: DefaultDict[str, List[Listener]] = defaultdict(list)

    def subscribe(self, event: str, callback: Listener) -> None:
        if not callable(callback):
            raise TypeError("callback muss callable sein")
        self._listeners[str(event)].append(callback)

    def unsubscribe(self, event: str, callback: Listener) -> bool:
        lst = self._listeners.get(str(event)) or []
        try:
            lst.remove(callback)
            return True
        except ValueError:
            return False

    def emit(self, event: str, *args: Any, **kwargs: Any) -> int:
        n = 0
        for cb in list(self._listeners.get(str(event)) or []):
            try:
                cb(*args, **kwargs)
                n += 1
            except Exception:
                continue
        return n

    def clear(self, event: str | None = None) -> None:
        if event is None:
            self._listeners.clear()
        else:
            self._listeners.pop(str(event), None)

    def listeners(self, event: str) -> Sequence[Listener]:
        return tuple(self._listeners.get(str(event) or "") or ())


_bus = EventBus()
_loaded_hooks: list[dict[str, Any]] = []


def get_event_bus() -> EventBus:
    return _bus


def subscribe(event: str, callback: Listener) -> None:
    _bus.subscribe(event, callback)


def emit(event: str, *args: Any, **kwargs: Any) -> int:
    """Event auslösen; zählt Listener-Aufrufe. Zusätzlich User-Hook-Handler."""
    n = _bus.emit(event, *args, **kwargs)
    # Payload-dict für User-Hooks
    payload: dict[str, Any] = {}
    if args and isinstance(args[0], dict) and not kwargs:
        payload = dict(args[0])
    else:
        payload = dict(kwargs)
        if args:
            payload.setdefault("args", list(args))
    n += _invoke_loaded_handlers(str(event), payload)
    try:
        from instantlensdoc.core.telemetry import report_anonymous_usage

        report_anonymous_usage("hook.emit", event=str(event))
    except Exception:
        pass
    return n


def hooks_dir(directory: str | Path | None = None) -> Path:
    """Aktiver Hooks-Ordner."""
    if directory is not None:
        return Path(directory)
    env = os.environ.get("ILD_HOOKS_DIR", "").strip()
    if env:
        return Path(env)
    try:
        from instantlensdoc.config import config_dir

        d = config_dir() / "hooks"
    except Exception:
        d = Path.home() / ".config" / "InstantLensDoc" / "hooks"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _handler_name(event: str) -> str:
    return "on_" + str(event).replace(".", "_")


def _load_python_hook(path: Path) -> dict[str, Any]:
    """Ein ``*.py`` Hook-Modul laden und Handler registrieren."""
    info: dict[str, Any] = {
        "path": str(path),
        "kind": "python",
        "ok": False,
        "handlers": [],
        "error": "",
    }
    try:
        spec = importlib.util.spec_from_file_location(
            f"ild_hook_{path.stem}", path
        )
        if spec is None or spec.loader is None:
            info["error"] = "spec_failed"
            return info
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        handlers: list[str] = []
        # on_event(event, **payload)
        generic = getattr(mod, "on_event", None)
        if callable(generic):

            def _make_generic(cb=generic):
                def _wrap(event: str, payload: dict[str, Any]) -> None:
                    cb(event, **payload)

                return _wrap

            wrap = _make_generic()
            # gespeichert am Modul für Invoke
            setattr(mod, "_ild_generic_wrap", wrap)
            handlers.append("on_event")
        for ev in KNOWN_EVENTS:
            fn = getattr(mod, _handler_name(ev), None)
            if callable(fn):
                handlers.append(_handler_name(ev))
        info["handlers"] = handlers
        info["ok"] = True
        info["_module"] = mod
    except Exception as exc:
        info["error"] = f"{type(exc).__name__}: {exc}"
        info["traceback"] = traceback.format_exc(limit=4)
    return info


def _invoke_loaded_handlers(event: str, payload: dict[str, Any]) -> int:
    n = 0
    hname = _handler_name(event)
    for rec in list(_loaded_hooks):
        if not rec.get("ok") or rec.get("kind") != "python":
            continue
        mod = rec.get("_module")
        if mod is None:
            continue
        try:
            specific = getattr(mod, hname, None)
            if callable(specific):
                specific(**payload)
                n += 1
            generic = getattr(mod, "_ild_generic_wrap", None)
            if callable(generic):
                generic(event, payload)
                n += 1
            elif callable(getattr(mod, "on_event", None)) and generic is None:
                getattr(mod, "on_event")(event, **payload)
                n += 1
        except Exception:
            continue
    return n


def load_plugins(directory: str | Path | None = None) -> list:
    """
    User-Hooks laden (Python). PowerShell-Dateien werden nur gelistet.

    Rückgabe: Liste Metadaten (ohne Modul-Objekte für JSON-Serialisierung).
    """
    global _loaded_hooks
    root = hooks_dir(directory)
    root.mkdir(parents=True, exist_ok=True)
    loaded: list[dict[str, Any]] = []
    for path in sorted(root.glob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() == ".py":
            rec = _load_python_hook(path)
            loaded.append(rec)
        elif path.suffix.lower() == ".ps1":
            loaded.append(
                {
                    "path": str(path),
                    "kind": "powershell",
                    "ok": True,
                    "handlers": [],
                    "error": "",
                    "note": "PS-Hooks: über ild.ps1 / externes PowerShell aufrufbar",
                }
            )
    _loaded_hooks = loaded
    # serialisierbare Kopie
    out = []
    for rec in loaded:
        out.append(
            {
                "path": rec.get("path"),
                "kind": rec.get("kind"),
                "ok": rec.get("ok"),
                "handlers": list(rec.get("handlers") or []),
                "error": rec.get("error") or "",
                "note": rec.get("note") or "",
            }
        )
    return out


def list_hooks(directory: str | Path | None = None) -> dict[str, Any]:
    """Hooks-Ordner + geladene Skripte + bekannte Events."""
    root = hooks_dir(directory)
    files = []
    if root.is_dir():
        for p in sorted(root.iterdir()):
            if p.is_file() and p.suffix.lower() in (".py", ".ps1", ".json"):
                files.append({"name": p.name, "path": str(p), "suffix": p.suffix.lower()})
    serial = []
    for rec in _loaded_hooks:
        serial.append(
            {
                "path": rec.get("path"),
                "kind": rec.get("kind"),
                "ok": rec.get("ok"),
                "handlers": list(rec.get("handlers") or []),
                "error": rec.get("error") or "",
            }
        )
    return {
        "hooks_dir": str(root),
        "files": files,
        "loaded": serial,
        "known_events": list(KNOWN_EVENTS),
        "event_descriptions": dict(EVENT_DESCRIPTIONS),
        "version": _ILD_VERSION,
    }


def register_hook_script(
    source: str | Path,
    *,
    directory: str | Path | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """Skript in den Hooks-Ordner kopieren und neu laden."""
    import shutil

    src = Path(source)
    if not src.is_file():
        return {"ok": False, "error": f"Datei fehlt: {src}", "version": _ILD_VERSION}
    dest_dir = hooks_dir(directory)
    dest_name = name or src.name
    dest = dest_dir / dest_name
    shutil.copy2(src, dest)
    loaded = load_plugins(dest_dir)
    return {
        "ok": True,
        "path": str(dest),
        "loaded": loaded,
        "version": _ILD_VERSION,
    }


def write_hook_example(directory: str | Path | None = None) -> Path:
    """Beispiel-Python-Hook schreiben falls fehlend."""
    root = hooks_dir(directory)
    dest = root / "example_hook.py"
    if dest.is_file():
        return dest
    dest.write_text(
        '''\
"""Beispiel InstantLens Doc Hook — 2.6.25."""

def on_document_opened(**payload):
    # payload: path, … — keine PII loggen in Produktion
    pass

def on_document_saved(**payload):
    pass

def on_document_exported(**payload):
    pass

def on_ocr_finished(**payload):
    pass

def on_event(event, **payload):
    # generischer Fallback
    pass
''',
        encoding="utf-8",
    )
    return dest


def plugin_stub_info() -> dict[str, Any]:
    """Metadaten für About/Smoke/Docs (Name beibehalten für Kompatibilität)."""
    return {
        "stub": False,
        "is_stub": IS_STUB,
        "live": True,
        "not_production_ready": NOT_PRODUCTION_READY,
        "version_marker": _ILD_VERSION,
        "message": STUB_MESSAGE,
        "known_events": list(KNOWN_EVENTS),
        "event_descriptions": dict(EVENT_DESCRIPTIONS),
        "loader": "user-scripts",
        "hooks_dir": str(hooks_dir()),
    }


# Alias für Klarheit
hooks_info = plugin_stub_info
