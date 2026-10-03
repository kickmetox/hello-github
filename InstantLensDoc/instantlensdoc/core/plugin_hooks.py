"""
Plugin-Hooks — STUB (1.9.4)

Kein echtes Plugin-System. Dieser Modul stellt nur einen **internen Event-Bus**
und einen **no-op Loader** bereit, damit spätere Erweiterungen einen klaren
Anknüpfungspunkt haben.

Kennzeichnung:
- ``IS_STUB = True``
- ``load_plugins()`` lädt niemals Code und gibt immer ``[]`` zurück
- Listener können intern registriert werden (Tests/App), externe Plugins nicht
- **nicht produktiv** — About/Menü/Settings-Seite „Stubs“ kennzeichnen klar

Dokumentierte Event-Namen (API-Stabilität später; Liste auch in FEATURES.md / Docs):

| Event | Bedeutung |
|-------|-----------|
| ``app.started`` | nach QApplication / MainWindow |
| ``document.opened`` | Datei geöffnet |
| ``document.saved`` | Datei gespeichert |
| ``annotation.changed`` | Sidecar-Annotation geändert |
| ``ocr.finished`` | OCR-Lauf beendet |
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, DefaultDict, Iterable, List, Optional, Sequence

# Klare Stub-Markierung — kein echtes Plugin-System, nicht produktiv
IS_STUB = True
NOT_PRODUCTION_READY = True
STUB_MESSAGE = (
    "Plugin-Hooks Stub 1.9.4 — nicht produktiv; "
    "interner Event-Bus + no-op Loader; kein Plugin-System (Coming soon)."
)

# Dokumentierte Event-Namen (API-Stabilität später) — Docs/FEATURES spiegeln diese Liste
KNOWN_EVENTS: tuple[str, ...] = (
    "app.started",
    "document.opened",
    "document.saved",
    "annotation.changed",
    "ocr.finished",
)

EVENT_DESCRIPTIONS: dict[str, str] = {
    "app.started": "nach QApplication / MainWindow",
    "document.opened": "Datei geöffnet",
    "document.saved": "Datei gespeichert",
    "annotation.changed": "Sidecar-Annotation geändert",
    "ocr.finished": "OCR-Lauf beendet",
}

Listener = Callable[..., Any]


class EventBus:
    """Minimaler interner Pub/Sub — kein Plugin-Sandboxing."""

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
        """Ruft Listener auf; Fehler werden geschluckt (Stub-robust). Rückgabe: Aufrufe."""
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
        return tuple(self._listeners.get(str(event)) or ())


# Prozessweiter Bus (App kann denselben nutzen)
_bus = EventBus()


def get_event_bus() -> EventBus:
    """Singleton Event-Bus (intern)."""
    return _bus


def subscribe(event: str, callback: Listener) -> None:
    _bus.subscribe(event, callback)


def emit(event: str, *args: Any, **kwargs: Any) -> int:
    return _bus.emit(event, *args, **kwargs)


def load_plugins(directory: str | Path | None = None) -> list:
    """
    No-op Plugin-Loader — **STUB / nicht produktiv**.

    Akzeptiert optional einen Ordnerpfad, lädt aber niemals Module und
    gibt immer eine leere Liste zurück. Externe Plugins werden bewusst
    nicht unterstützt.
    """
    # Pfad nur validieren/anlegen-Hinweis — kein Import, kein exec
    if directory is not None:
        Path(directory)  # noqa: B018 — Existenz absichtlich ignoriert
    return []


def plugin_stub_info() -> dict[str, Any]:
    """Metadaten für About/Smoke/Docs."""
    return {
        "stub": True,
        "is_stub": IS_STUB,
        "not_production_ready": NOT_PRODUCTION_READY,
        "version_marker": "1.9.4",
        "message": STUB_MESSAGE,
        "known_events": list(KNOWN_EVENTS),
        "event_descriptions": dict(EVENT_DESCRIPTIONS),
        "loader": "no-op",
    }
