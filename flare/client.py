"""Zugriff für andere Programme: HTTP, wenn Flare läuft, sonst die Datenbank direkt."""

from __future__ import annotations

import json
import socket
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from flare.paths import data_dir as default_data_dir
from flare.rank import Ranker
from flare.search import search
from flare.store import Index


class Client:
    def __init__(self, data_dir: str | Path | None = None, timeout: float = 2.0) -> None:
        self.data_dir = Path(data_dir) if data_dir else default_data_dir()
        self.timeout = timeout

    def port(self) -> int | None:
        file = self.data_dir / "port"
        try:
            port = int(file.read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            return None
        try:
            with socket.create_connection(("127.0.0.1", port), 0.3):
                return port
        except OSError:
            return None

    def search(self, text: str, limit: int = 8, similar: bool = False) -> dict[str, Any]:
        port = self.port()
        if port is not None:
            params = {"q": text, "limit": str(limit)}
            if similar:
                params["similar"] = "1"
            query = urllib.parse.urlencode(params)
            return self._json("GET", port, f"/api/search?{query}")
        return self._local_search(text, limit, similar)

    def status(self) -> dict[str, Any]:
        port = self.port()
        if port is not None:
            payload = self._json("GET", port, "/api/status")
            payload["running"] = True
            return payload
        db = self.data_dir / "index.db"
        counts = {"items": 0, "dirs": 0}
        if db.exists():
            index = Index(db, readonly=True)
            try:
                counts = index.counts()
            finally:
                index.close()
        return {"running": False, **counts}

    def open_id(self, item_id: int) -> bool:
        port = self.port()
        if port is None:
            return False
        payload = self._json("POST", port, "/api/open", {"id": item_id})
        return bool(payload.get("ok"))

    def activate(self) -> bool:
        port = self.port()
        if port is None:
            return False
        payload = self._json("POST", port, "/api/activate", {})
        return bool(payload.get("ok"))

    def reindex(self) -> bool:
        port = self.port()
        if port is None:
            return False
        payload = self._json("POST", port, "/api/reindex", {})
        return bool(payload.get("ok"))

    def _local_search(self, text: str, limit: int, similar: bool = False) -> dict[str, Any]:
        db = self.data_dir / "index.db"
        if not db.exists():
            return {"query": text, "backend": "cpu", "took_ms": 0, "similar": similar, "results": []}
        index = Index(db, readonly=True)
        ranker = Ranker(allow_cuda=False)
        try:
            return search(index, ranker, text, limit, similar)
        finally:
            ranker.close()
            index.close()

    def _json(self, method: str, port: int, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"} if data is not None else {},
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))
