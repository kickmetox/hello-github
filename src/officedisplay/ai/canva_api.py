"""Kein Canva-Connect. Vorlagen und Formen liegen lokal in der Bibliothek."""
from __future__ import annotations

class CanvaAPIError(Exception):
    pass

def authorize_url(*_args, **_kwargs):
    raise CanvaAPIError("Canva-Connect ist nicht enthalten.")

class CanvaClient:
    def __init__(self, *_args, **_kwargs):
        raise CanvaAPIError("Canva-Connect ist nicht enthalten.")
