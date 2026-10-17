"""Ausführen, Kompilieren und allgemeine Prozess-Sitzungen."""

from __future__ import annotations

import compileall
import os
import py_compile
import subprocess
import sys
import textwrap
import threading
from pathlib import Path


class ProcessSession:
    def __init__(self, args: list[str], cwd: str, env: dict | None = None) -> None:
        merged = os.environ.copy()
        if env:
            merged.update(env)
        merged["PYTHONUNBUFFERED"] = "1"
        self.proc = subprocess.Popen(
            args,
            cwd=cwd,
            env=merged,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self.output: list[str] = []
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _read(self) -> None:
        assert self.proc.stdout is not None
        for line in self.proc.stdout:
            with self.lock:
                self.output.append(line)
                if len(self.output) > 6000:
                    self.output = self.output[-5000:]

    def write(self, data: str) -> None:
        if self.proc.stdin is None:
            return
        self.proc.stdin.write(data)
        self.proc.stdin.flush()

    def poll(self, start: int = 0) -> dict:
        with self.lock:
            chunk = self.output[start:]
            code = self.proc.poll()
            return {
                "ok": True,
                "lines": chunk,
                "next": start + len(chunk),
                "running": code is None,
                "code": code,
            }

    def stop(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()


def compile_file(path: str) -> dict:
    try:
        py_compile.compile(path, doraise=True)
    except py_compile.PyCompileError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "message": f"Bytecode erzeugt für {path}"}


def compile_tree(workspace: str) -> dict:
    import re

    skip = re.compile(r"[/\\](\.venv|venv|env|__pycache__|\.shatuide|\.git|node_modules)[/\\]")
    success = compileall.compile_dir(str(Path(workspace)), quiet=1, rx=skip, workers=1)
    return {"ok": bool(success), "message": "Projekt kompiliert." if success else "Kompilieren mit Fehlern beendet."}


def pyinstaller_args(python: str, script: str) -> list[str]:
    return [python, "-m", "PyInstaller", "--noconfirm", "--onefile", script]


def selection_code(source: str) -> str:
    return textwrap.dedent(source)


def run_args(python: str, script: str, args: list[str] | None = None) -> list[str]:
    return [python or sys.executable, "-u", script, *(args or [])]


class PtyTerminal:
    """Interaktives Terminal. Unter Windows eine einfache Pipe-Sitzung."""

    def __init__(self, cwd: str, shell: str | None = None) -> None:
        self.output = ""
        self.lock = threading.Lock()
        self.master = None
        self.proc: subprocess.Popen
        if os.name != "nt":
            import pty

            shell = shell or os.environ.get("SHELL", "/bin/bash")
            master, slave = pty.openpty()
            self.master = master
            self.proc = subprocess.Popen(
                [shell, "-i"],
                stdin=slave,
                stdout=slave,
                stderr=slave,
                cwd=cwd,
                start_new_session=True,
            )
            os.close(slave)
            threading.Thread(target=self._read_pty, daemon=True).start()
        else:
            self.proc = subprocess.Popen(
                ["cmd.exe"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=cwd,
                text=True,
                bufsize=1,
            )
            threading.Thread(target=self._read_pipe, daemon=True).start()

    def _append(self, text: str) -> None:
        with self.lock:
            self.output += text
            if len(self.output) > 200_000:
                self.output = self.output[-150_000:]

    def _read_pty(self) -> None:
        assert self.master is not None
        while True:
            try:
                data = os.read(self.master, 4096)
            except OSError:
                break
            if not data:
                break
            self._append(data.decode("utf-8", "replace"))

    def _read_pipe(self) -> None:
        assert self.proc.stdout is not None
        for line in self.proc.stdout:
            self._append(line)

    def write(self, data: str) -> None:
        if self.master is not None:
            os.write(self.master, data.encode("utf-8"))
            return
        if self.proc.stdin is not None:
            self.proc.stdin.write(data)
            self.proc.stdin.flush()

    def read_from(self, pos: int) -> dict:
        with self.lock:
            return {
                "text": self.output[pos:],
                "next": len(self.output),
                "running": self.proc.poll() is None,
            }

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()
        if self.master is not None:
            try:
                os.close(self.master)
            except OSError:
                pass
