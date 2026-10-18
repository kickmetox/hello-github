"""Startet den Debugger-Prozess und reicht Befehle der Oberfläche durch."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path


class DebugSession:
    def __init__(self) -> None:
        self.proc: subprocess.Popen | None = None
        self.sock: socket.socket | None = None
        self.events: list[dict] = []
        self.output: list[str] = []
        self.paused: dict | None = None
        self.cond = threading.Condition()
        self.bp_file: Path | None = None
        self.returncode: int | None = None

    def start(self, python: str, script: str, cwd: str, breakpoints: list[dict], bp_file: Path) -> None:
        self.bp_file = bp_file
        bp_file.parent.mkdir(parents=True, exist_ok=True)
        bp_file.write_text(json.dumps(breakpoints), encoding="utf-8")
        worker = Path(__file__).resolve().parent / "debug_worker.py"
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        self.proc = subprocess.Popen(
            [python or sys.executable, "-u", str(worker), str(port), script, str(bp_file), cwd],
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        threading.Thread(target=self._read_stdout, daemon=True).start()
        listener.settimeout(15)
        try:
            self.sock, _addr = listener.accept()
        except socket.timeout as exc:
            if self.proc.poll() is None:
                self.proc.kill()
            raise RuntimeError("Debugger hat sich nicht verbunden. " + "".join(self.output)[-800:]) from exc
        finally:
            listener.close()
        self.sock.settimeout(None)
        threading.Thread(target=self._read_socket, daemon=True).start()
        self.command({"cmd": "init", "points": breakpoints})

    def _read_stdout(self) -> None:
        assert self.proc is not None and self.proc.stdout is not None
        for line in self.proc.stdout:
            with self.cond:
                self.output.append(line)
                if len(self.output) > 4000:
                    self.output = self.output[-3000:]
                self.cond.notify_all()
        code = self.proc.wait()
        with self.cond:
            self.returncode = code
            self.events.append({"event": "process_exit", "code": code})
            self.cond.notify_all()

    def _read_socket(self) -> None:
        assert self.sock is not None
        buf = b""
        while True:
            try:
                chunk = self.sock.recv(65536)
            except OSError:
                break
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if not line.strip():
                    continue
                try:
                    message = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    continue
                with self.cond:
                    self.events.append(message)
                    if message.get("event") == "stopped":
                        self.paused = message
                    elif message.get("event") in {"terminated", "exception"}:
                        self.paused = None
                    self.cond.notify_all()

    def command(self, payload: dict) -> None:
        if self.sock is None:
            raise RuntimeError("Keine Debug-Sitzung.")
        self.sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))

    def update_breakpoints(self, points: list[dict]) -> None:
        if self.bp_file is not None:
            self.bp_file.write_text(json.dumps(points), encoding="utf-8")
        if self.paused and self.sock is not None:
            self.command({"cmd": "breakpoints", "points": points})

    def wait_event(self, name: str, timeout: float = 8) -> dict:
        deadline = time.time() + timeout
        with self.cond:
            while time.time() < deadline:
                for event in self.events:
                    if event.get("event") == name:
                        return event
                remaining = deadline - time.time()
                if remaining <= 0:
                    break
                self.cond.wait(timeout=min(0.2, remaining))
        raise TimeoutError(name)

    def snapshot(self, output_from: int = 0) -> dict:
        with self.cond:
            running = self.proc is not None and self.proc.poll() is None
            return {
                "ok": True,
                "running": running,
                "paused": self.paused,
                "events": self.events[-40:],
                "output": self.output[output_from:],
                "output_next": len(self.output),
                "returncode": self.returncode if not running else None,
            }

    def close(self) -> None:
        try:
            if self.paused and self.sock is not None:
                self.command({"cmd": "stop"})
        except OSError:
            pass
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None
        if self.proc is not None:
            for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except OSError:
                        pass
