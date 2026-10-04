"""Echtzeit-Kollaboration — lokaler WebSocket-/TCP-Hub (stdlib) — CRDT-lite.
Lokal / CRDT-lite — 2.6.28.

Praktischer Pfad ohne Cloud-Credentials:
- ``RealtimeHub``: TCP JSON-Lines Server auf ``127.0.0.1:port``
- Op-Log mit Lamport-Clock (LWW-Element-Set) für Kommentare/Cursor/Text-Patches
- ``start_local_hub``, ``connect_client``, ``broadcast_op``, ``apply_ops``

Gehostete Cloud-Kollaboration braucht Deployment/Credentials — der lokale Hub
ist der unterstützte Offline-/LAN-Pfad. Ordner-Polling (shared_review) bleibt
als Fallback.
"""

from __future__ import annotations

import json
import socket
import socketserver
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
PROTOCOL = "ild-realtime-v1"

LIMITATIONS_DE = (
    "Lokaler TCP-JSON-Lines-Hub auf 127.0.0.1 — kein gehosteter Cloud-Dienst. "
    "CRDT-lite (Op-Log + Lamport/LWW) für Kommentare, Cursor und Text-Patches. "
    "Echte Multi-User-Cloud benötigt Credentials/Deployment; dieser Hub ist der "
    "praktische lokale Pfad. Ordner-Polling (shared_review) bleibt parallel nutzbar."
)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class CollabOp:
    """Einzelne Kollaborations-Operation (Op-Log Eintrag)."""

    id: str
    op_type: str  # comment | cursor | text_patch | presence | ping
    actor: str
    lamport: int
    ts_ms: int
    payload: dict[str, Any] = field(default_factory=dict)
    tombstone: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "op_type": self.op_type,
            "actor": self.actor,
            "lamport": self.lamport,
            "ts_ms": self.ts_ms,
            "payload": dict(self.payload or {}),
            "tombstone": bool(self.tombstone),
        }

    @classmethod
    def from_dict(cls, data: object) -> "CollabOp":
        if not isinstance(data, dict):
            return cls(
                id=_new_id(),
                op_type="ping",
                actor="unknown",
                lamport=0,
                ts_ms=_now_ms(),
            )
        return cls(
            id=str(data.get("id") or _new_id()),
            op_type=str(data.get("op_type") or "ping"),
            actor=str(data.get("actor") or "unknown"),
            lamport=int(data.get("lamport") or 0),
            ts_ms=int(data.get("ts_ms") or _now_ms()),
            payload=dict(data.get("payload") or {})
            if isinstance(data.get("payload"), dict)
            else {},
            tombstone=bool(data.get("tombstone", False)),
        )


@dataclass
class LWWElementSet:
    """CRDT-lite: Last-Writer-Wins Element-Set (nach Lamport, dann ts_ms)."""

    elements: dict[str, CollabOp] = field(default_factory=dict)
    clock: int = 0

    def tick(self, remote: int = 0) -> int:
        self.clock = max(self.clock, int(remote)) + 1
        return self.clock

    def apply(self, op: CollabOp) -> bool:
        """Op anwenden; True wenn übernommen."""
        self.clock = max(self.clock, int(op.lamport))
        key = op.id
        # Element-Key: für LWW oft payload.element_id, sonst op.id
        elem_key = str((op.payload or {}).get("element_id") or op.id)
        key = elem_key
        existing = self.elements.get(key)
        if existing is None:
            self.elements[key] = op
            return True
        if int(op.lamport) > int(existing.lamport):
            self.elements[key] = op
            return True
        if int(op.lamport) == int(existing.lamport) and int(op.ts_ms) >= int(
            existing.ts_ms
        ):
            self.elements[key] = op
            return True
        return False

    def visible(self) -> list[CollabOp]:
        return [op for op in self.elements.values() if not op.tombstone]

    def snapshot(self) -> dict[str, Any]:
        return {
            "clock": self.clock,
            "ops": [op.to_dict() for op in self.elements.values()],
            "visible_count": len(self.visible()),
        }


def apply_ops(
    state: LWWElementSet | dict[str, Any] | None,
    ops: list[CollabOp | dict[str, Any]],
) -> dict[str, Any]:
    """Ops auf State anwenden (LWW). Rückgabe: neuer Snapshot + applied count."""
    if isinstance(state, LWWElementSet):
        store = state
    else:
        store = LWWElementSet()
        if isinstance(state, dict):
            store.clock = int(state.get("clock") or 0)
            for raw in state.get("ops") or []:
                store.apply(CollabOp.from_dict(raw))
    applied = 0
    for raw in ops or []:
        op = raw if isinstance(raw, CollabOp) else CollabOp.from_dict(raw)
        if store.apply(op):
            applied += 1
    snap = store.snapshot()
    snap["applied"] = applied
    snap["ok"] = True
    return snap


class _ThreadJSONHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        hub: RealtimeHub = self.server.hub  # type: ignore[attr-defined]
        peer = f"{self.client_address[0]}:{self.client_address[1]}"
        hub._register(self)
        try:
            # Begrüßung
            self._send(
                {
                    "type": "hello",
                    "protocol": PROTOCOL,
                    "peer": peer,
                    "snapshot": hub.state.snapshot(),
                }
            )
            while True:
                line = self.rfile.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line.decode("utf-8"))
                except Exception:
                    self._send({"type": "error", "message": "invalid json"})
                    continue
                hub._on_message(self, msg if isinstance(msg, dict) else {})
        finally:
            hub._unregister(self)

    def _send(self, obj: dict[str, Any]) -> None:
        try:
            data = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
            self.wfile.write(data)
            self.wfile.flush()
        except Exception:
            pass


class RealtimeHub:
    """Lokaler TCP JSON-Lines Relay auf 127.0.0.1."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host or DEFAULT_HOST
        self.port = int(port)
        self.state = LWWElementSet()
        self._clients: list[_ThreadJSONHandler] = []
        self._lock = threading.RLock()
        self._server: socketserver.ThreadingTCPServer | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> dict[str, Any]:
        if self._running:
            return self.status()

        class _Srv(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True

        self._server = _Srv((self.host, self.port), _ThreadJSONHandler)
        self._server.hub = self  # type: ignore[attr-defined]
        # Actual port if 0 was requested
        self.port = int(self._server.server_address[1])
        self._running = True
        self._thread = threading.Thread(
            target=self._server.serve_forever, name="ild-realtime-hub", daemon=True
        )
        self._thread.start()
        return self.status()

    def stop(self) -> None:
        self._running = False
        if self._server is not None:
            try:
                self._server.shutdown()
            except Exception:
                pass
            try:
                self._server.server_close()
            except Exception:
                pass
        self._server = None
        self._thread = None
        with self._lock:
            self._clients.clear()

    def status(self) -> dict[str, Any]:
        with self._lock:
            n = len(self._clients)
        return {
            "ok": True,
            "running": self._running,
            "host": self.host,
            "port": self.port,
            "protocol": PROTOCOL,
            "clients": n,
            "clock": self.state.clock,
            "ops": len(self.state.elements),
            "limitations": LIMITATIONS_DE,
            "cloud_note": (
                "Gehostete Cloud-Kollaboration benötigt Credentials/Deployment; "
                "lokaler Hub ist der praktische Pfad."
            ),
        }

    def _register(self, handler: _ThreadJSONHandler) -> None:
        with self._lock:
            self._clients.append(handler)

    def _unregister(self, handler: _ThreadJSONHandler) -> None:
        with self._lock:
            try:
                self._clients.remove(handler)
            except ValueError:
                pass

    def _broadcast(self, obj: dict[str, Any], *, exclude: Any = None) -> int:
        data = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
        sent = 0
        with self._lock:
            clients = list(self._clients)
        for c in clients:
            if c is exclude:
                continue
            try:
                c.wfile.write(data)
                c.wfile.flush()
                sent += 1
            except Exception:
                pass
        return sent

    def _on_message(self, handler: _ThreadJSONHandler, msg: dict[str, Any]) -> None:
        mtype = str(msg.get("type") or "")
        if mtype == "ping":
            handler._send({"type": "pong", "ts_ms": _now_ms()})
            return
        if mtype == "sync":
            handler._send({"type": "snapshot", "snapshot": self.state.snapshot()})
            return
        if mtype in ("op", "broadcast_op"):
            op = CollabOp.from_dict(msg.get("op") or msg)
            with self._lock:
                # Lamport tick if client omitted
                if op.lamport <= 0:
                    op.lamport = self.state.tick()
                else:
                    self.state.tick(op.lamport)
                changed = self.state.apply(op)
            if changed:
                self._broadcast({"type": "op", "op": op.to_dict()}, exclude=handler)
            handler._send({"type": "ack", "id": op.id, "applied": changed})
            return
        handler._send({"type": "error", "message": f"unknown type {mtype}"})

    def broadcast_op(self, op: CollabOp | dict[str, Any]) -> dict[str, Any]:
        """Op lokal anwenden und an alle Clients senden."""
        collab_op = op if isinstance(op, CollabOp) else CollabOp.from_dict(op)
        with self._lock:
            if collab_op.lamport <= 0:
                collab_op.lamport = self.state.tick()
            else:
                self.state.tick(collab_op.lamport)
            applied = self.state.apply(collab_op)
        n = self._broadcast({"type": "op", "op": collab_op.to_dict()})
        return {
            "ok": True,
            "applied": applied,
            "sent": n,
            "op": collab_op.to_dict(),
            "clock": self.state.clock,
        }


# Prozessweiter Default-Hub
_HUB: RealtimeHub | None = None
_HUB_LOCK = threading.Lock()


def start_local_hub(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    restart: bool = False,
) -> dict[str, Any]:
    """Lokalen Realtime-Hub starten (stdlib TCP JSON-Lines)."""
    global _HUB
    with _HUB_LOCK:
        if _HUB is not None and _HUB._running and not restart:
            return _HUB.status()
        if _HUB is not None:
            try:
                _HUB.stop()
            except Exception:
                pass
        _HUB = RealtimeHub(host=host, port=port)
        return _HUB.start()


def stop_local_hub() -> dict[str, Any]:
    global _HUB
    with _HUB_LOCK:
        if _HUB is None:
            return {"ok": True, "running": False}
        _HUB.stop()
        _HUB = None
    return {"ok": True, "running": False}


def realtime_status() -> dict[str, Any]:
    with _HUB_LOCK:
        if _HUB is None:
            return {
                "ok": True,
                "running": False,
                "host": DEFAULT_HOST,
                "port": DEFAULT_PORT,
                "protocol": PROTOCOL,
                "clients": 0,
                "limitations": LIMITATIONS_DE,
                "cloud_note": (
                    "Gehostete Cloud-Kollaboration benötigt Credentials/Deployment; "
                    "lokaler Hub ist der praktische Pfad."
                ),
            }
        return _HUB.status()


def get_hub() -> RealtimeHub | None:
    return _HUB


def broadcast_op(op: CollabOp | dict[str, Any]) -> dict[str, Any]:
    """Op über den laufenden Hub broadcasten (oder Fehler wenn kein Hub)."""
    hub = _HUB
    if hub is None or not hub._running:
        return {"ok": False, "error": "hub not running", "hint": "start_local_hub()"}
    return hub.broadcast_op(op)


def connect_client(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    timeout: float = 5.0,
) -> "RealtimeClient":
    """TCP-Client zum lokalen Hub verbinden."""
    client = RealtimeClient(host=host, port=port)
    client.connect(timeout=timeout)
    return client


class RealtimeClient:
    """Einfacher JSON-Lines Client für den lokalen Hub."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = int(port)
        self._sock: socket.socket | None = None
        self._rfile = None
        self._wfile = None
        self.state = LWWElementSet()
        self._on_op: Callable[[CollabOp], None] | None = None
        self._recv_thread: threading.Thread | None = None
        self._alive = False

    def connect(self, *, timeout: float = 5.0) -> dict[str, Any]:
        s = socket.create_connection((self.host, self.port), timeout=timeout)
        s.settimeout(None)
        self._sock = s
        self._rfile = s.makefile("rb")
        self._wfile = s.makefile("wb")
        self._alive = True
        hello = self._readline(timeout=timeout)
        if isinstance(hello, dict) and isinstance(hello.get("snapshot"), dict):
            apply_ops(self.state, hello["snapshot"].get("ops") or [])
        self._recv_thread = threading.Thread(
            target=self._recv_loop, name="ild-realtime-client", daemon=True
        )
        self._recv_thread.start()
        return hello if isinstance(hello, dict) else {"type": "hello"}

    def close(self) -> None:
        self._alive = False
        try:
            if self._sock:
                self._sock.close()
        except Exception:
            pass
        self._sock = None

    def on_op(self, callback: Callable[[CollabOp], None]) -> None:
        self._on_op = callback

    def send_op(
        self,
        op_type: str,
        payload: dict[str, Any] | None = None,
        *,
        actor: str = "local",
        element_id: str | None = None,
        tombstone: bool = False,
    ) -> CollabOp:
        lamport = self.state.tick()
        pl = dict(payload or {})
        if element_id:
            pl["element_id"] = element_id
        op = CollabOp(
            id=_new_id(),
            op_type=op_type,
            actor=actor,
            lamport=lamport,
            ts_ms=_now_ms(),
            payload=pl,
            tombstone=tombstone,
        )
        self.state.apply(op)
        self._send({"type": "op", "op": op.to_dict()})
        return op

    def sync(self) -> None:
        self._send({"type": "sync"})

    def _send(self, obj: dict[str, Any]) -> None:
        if self._wfile is None:
            raise ConnectionError("not connected")
        data = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
        self._wfile.write(data)
        self._wfile.flush()

    def _readline(self, timeout: float | None = None) -> dict[str, Any] | None:
        if self._rfile is None:
            return None
        if timeout is not None and self._sock is not None:
            self._sock.settimeout(timeout)
        try:
            line = self._rfile.readline()
        except Exception:
            return None
        finally:
            if self._sock is not None:
                try:
                    self._sock.settimeout(None)
                except Exception:
                    pass
        if not line:
            return None
        try:
            return json.loads(line.decode("utf-8"))
        except Exception:
            return None

    def _recv_loop(self) -> None:
        while self._alive:
            msg = self._readline()
            if msg is None:
                self._alive = False
                break
            mtype = str(msg.get("type") or "")
            if mtype == "op":
                op = CollabOp.from_dict(msg.get("op") or {})
                self.state.apply(op)
                if self._on_op:
                    try:
                        self._on_op(op)
                    except Exception:
                        pass
            elif mtype == "snapshot":
                snap = msg.get("snapshot") or {}
                apply_ops(self.state, snap.get("ops") or [])
