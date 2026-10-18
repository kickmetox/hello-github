"""Debugger-Prozess. Steuerung über ein lokales Socket, Programmausgabe über stdout."""

from __future__ import annotations

import bdb
import json
import linecache
import os
import socket
import sys
import traceback


class JsonConn:
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.buf = b""

    def send(self, obj: dict) -> None:
        data = (json.dumps(obj, default=str) + "\n").encode("utf-8")
        self.sock.sendall(data)

    def recv(self) -> dict | None:
        while b"\n" not in self.buf:
            chunk = self.sock.recv(65536)
            if not chunk:
                return None
            self.buf += chunk
        line, self.buf = self.buf.split(b"\n", 1)
        if not line.strip():
            return self.recv()
        return json.loads(line.decode("utf-8"))


class ShatuDbg(bdb.Bdb):
    def __init__(self, conn: JsonConn, script: str, bp_file: str):
        super().__init__()
        self.conn = conn
        self.script = os.path.abspath(script)
        self.bp_file = bp_file
        self.mode = "run"
        self._tick = 0
        self._seen_exc = None
        self._skip_files = {self.canonic(__file__), self.canonic(bdb.__file__)}

    def trace_dispatch(self, frame, event, arg):
        if event == "line":
            self._tick += 1
            if self._tick % 40 == 0:
                self.reload_points()
        return super().trace_dispatch(frame, event, arg)

    def set_continue(self) -> None:  # type: ignore[override]
        # Tracing bleibt an, damit neue Haltepunkte während des Laufs greifen.
        self._set_stopinfo(self.botframe, None, -1)

    def apply_points(self, points: list[dict]) -> None:
        self.clear_all_breaks()
        linecache.checkcache(self.script)
        for point in points:
            filename = os.path.abspath(point.get("file") or self.script)
            lineno = int(point.get("line") or 0)
            if lineno < 1:
                continue
            cond = point.get("condition") or None
            self.set_break(filename, lineno, cond=cond)

    def reload_points(self) -> None:
        try:
            with open(self.bp_file, encoding="utf-8") as handle:
                points = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return
        if isinstance(points, list):
            self.apply_points(points)

    def user_line(self, frame) -> None:
        filename = self.canonic(frame.f_code.co_filename)
        if filename in self._skip_files:
            return
        hit = self.break_here(frame)
        in_script = filename == self.canonic(self.script)
        if self.mode == "run" and not hit:
            if in_script:
                self.set_continue()
            return
        self._pause(frame, "breakpoint" if hit else "step")

    def _user_file(self, filename: str) -> bool:
        if filename in self._skip_files:
            return False
        normalized = filename.replace("\\", "/")
        if "/site-packages/" in normalized or normalized.startswith("<"):
            return False
        script = self.canonic(self.script)
        if filename == script:
            return True
        return filename.startswith(os.path.dirname(script) + os.sep)

    def dispatch_exception(self, frame, arg):  # type: ignore[override]
        # Rückgabe ist die Trace-Funktion. Ein erneuter Aufruf mit "exception"
        # würde hier endlos wieder eintreten.
        exc_type, exc_value, _tb = arg
        if exc_type not in (bdb.BdbQuit, KeyboardInterrupt, SystemExit):
            filename = self.canonic(frame.f_code.co_filename)
            if self._user_file(filename) and self._seen_exc is not exc_value:
                self._seen_exc = exc_value
                self.user_exception(frame, arg)
                if self.quitting:
                    raise bdb.BdbQuit
        return self.trace_dispatch

    def user_exception(self, frame, exc_info) -> None:
        if exc_info[0] in (bdb.BdbQuit, KeyboardInterrupt, SystemExit):
            return
        self._pause(frame, "exception", exc_info)

    def _pause(self, frame, reason: str, exc_info=None) -> None:
        locals_view = {}
        for key, value in frame.f_locals.items():
            if key.startswith("__"):
                continue
            try:
                locals_view[key] = repr(value)[:500]
            except Exception:
                locals_view[key] = "<nicht darstellbar>"
        stack = []
        current = frame
        while current is not None and len(stack) < 30:
            stack.append(
                {
                    "file": current.f_code.co_filename,
                    "line": current.f_lineno,
                    "func": current.f_code.co_name,
                }
            )
            current = current.f_back
        message = {
            "event": "stopped",
            "reason": reason,
            "file": frame.f_code.co_filename,
            "line": frame.f_lineno,
            "func": frame.f_code.co_name,
            "locals": locals_view,
            "stack": stack,
        }
        if exc_info is not None:
            message["exception"] = "".join(traceback.format_exception(*exc_info))[:4000]
        self.conn.send(message)
        while True:
            cmd = self.conn.recv()
            if not cmd:
                self.set_quit()
                return
            name = cmd.get("cmd")
            if name == "breakpoints":
                self.apply_points(cmd.get("points") or [])
                self.conn.send({"event": "breakpoints_ok"})
                continue
            if name == "eval":
                self._eval(frame, cmd.get("expr") or "")
                continue
            self.reload_points()
            if name == "continue":
                self.mode = "run"
                self.set_continue()
                return
            if name in {"step", "next"}:
                self.mode = "over"
                self.set_next(frame)
                return
            if name == "step_into":
                self.mode = "into"
                self.set_step()
                return
            if name == "step_out":
                self.mode = "over"
                self.set_return(frame)
                return
            if name == "stop":
                self.set_quit()
                return
            self.conn.send({"event": "unknown", "cmd": name})

    def _eval(self, frame, expr: str) -> None:
        expr = expr.strip()[:500]
        if not expr:
            self.conn.send({"event": "eval", "error": "Ausdruck fehlt."})
            return
        try:
            value = eval(expr, frame.f_globals, frame.f_locals)  # noqa: S307 – Debug-Ausdruck des lokalen Nutzers
            self.conn.send({"event": "eval", "expr": expr, "value": repr(value)[:2000]})
        except Exception as exc:
            self.conn.send({"event": "eval", "expr": expr, "error": str(exc)})


def _hold_syntax(conn: JsonConn, script: str, exc: SyntaxError) -> None:
    line = exc.lineno or 1
    conn.send(
        {
            "event": "stopped",
            "reason": "exception",
            "file": script,
            "line": line,
            "func": "<module>",
            "locals": {},
            "stack": [{"file": script, "line": line, "func": "<module>"}],
            "exception": f"SyntaxError: {exc.msg}",
        }
    )
    while True:
        cmd = conn.recv()
        if not cmd or cmd.get("cmd") in {"stop", "continue", "step", "step_into", "step_out"}:
            break
    conn.send({"event": "terminated", "code": 1})


def main() -> None:
    port = int(sys.argv[1])
    script = os.path.abspath(sys.argv[2])
    bp_file = sys.argv[3]
    cwd = sys.argv[4] if len(sys.argv) > 4 else os.path.dirname(script)
    os.chdir(cwd)
    sys.path.insert(0, os.path.dirname(script))
    sock = socket.create_connection(("127.0.0.1", port), timeout=15)
    sock.settimeout(None)
    conn = JsonConn(sock)
    try:
        init = conn.recv() or {}
        dbg = ShatuDbg(conn, script, bp_file)
        dbg.apply_points(init.get("points") or [])
        with open(script, encoding="utf-8") as handle:
            source = handle.read()
        try:
            code = compile(source, script, "exec")
        except SyntaxError as exc:
            _hold_syntax(conn, script, exc)
            return
        globs = {"__name__": "__main__", "__file__": script, "__package__": None, "__cached__": None}
        sys.argv = [script, *sys.argv[5:]]
        try:
            dbg.run(code, globs, globs)
            conn.send({"event": "terminated", "code": 0})
        except SystemExit as exc:
            code_value = exc.code if isinstance(exc.code, int) else 0
            conn.send({"event": "terminated", "code": code_value})
        except Exception:
            conn.send({"event": "exception", "trace": traceback.format_exc()[-4000:]})
            conn.send({"event": "terminated", "code": 1})
    finally:
        try:
            sock.close()
        except OSError:
            pass


if __name__ == "__main__":
    main()
