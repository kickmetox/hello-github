"""Lokale HTTP-Schnittstelle. Nur 127.0.0.1, gedacht für die Oberfläche und andere Programme."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

HTML = (Path(__file__).with_name("ui.html")).read_text(encoding="utf-8").encode("utf-8")


class EventBus:
    def __init__(self) -> None:
        self._cv = threading.Condition()
        self.seq = 0
        self.payload: dict[str, Any] | None = None

    def push(self, payload: dict[str, Any]) -> None:
        with self._cv:
            self.seq += 1
            self.payload = payload
            self._cv.notify_all()

    def wait(self, since: int, timeout: float = 25.0) -> tuple[int, dict[str, Any] | None]:
        with self._cv:
            if self.seq <= since:
                self._cv.wait(timeout)
            if self.seq <= since:
                return self.seq, None
            return self.seq, self.payload


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "Flare/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    @property
    def app(self) -> Any:
        return self.server.app  # type: ignore[attr-defined]

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._bytes(200, HTML, "text/html; charset=utf-8")
            return
        if parsed.path == "/favicon.ico":
            self._bytes(204, b"", "image/x-icon")
            return
        query = parse_qs(parsed.query)
        if parsed.path == "/api/search":
            text = query.get("q", [""])[0]
            limit = _limit(query.get("limit", ["8"])[0])
            self._json(200, self.app.search(text, limit))
            return
        if parsed.path == "/api/status":
            self._json(200, self.app.status())
            return
        if parsed.path == "/api/health":
            self._json(200, {"ok": True})
            return
        if parsed.path == "/api/events":
            try:
                since = int(query.get("since", ["0"])[0])
            except ValueError:
                since = 0
            seq, event = self.app.bus.wait(since, 25.0)
            self._json(200, {"seq": seq, "event": event})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > 1_000_000:
            self._json(413, {"error": "too large"})
            return
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "bad json"})
            return
        if not isinstance(body, dict):
            body = {}
        if parsed.path == "/api/open":
            opened = self.app.open_result(body)
            self._json(200 if opened else 404, {"ok": opened})
            return
        if parsed.path == "/api/activate":
            self.app.activate()
            self._json(200, {"ok": True})
            return
        if parsed.path == "/api/reindex":
            self.app.reindex()
            self._json(200, {"ok": True})
            return
        self._json(404, {"error": "not found"})

    def _json(self, code: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._bytes(code, data, "application/json; charset=utf-8")

    def _bytes(self, code: int, data: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if data:
            self.wfile.write(data)


def _limit(raw: str) -> int:
    try:
        return max(1, min(int(raw), 50))
    except ValueError:
        return 8


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, host: str, port: int, app: Any) -> None:
        self.app = app
        super().__init__((host, port), Handler)
