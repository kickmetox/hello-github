"""Lokaler ShatuIDE-Server. Bindet nur an 127.0.0.1, Cookie schützt die API."""

from __future__ import annotations

import json
import mimetypes
import subprocess
import os
import re
import secrets
import sys
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from shatuide import __author__, __email__, __version__
from shatuide import ai, analysis, config, database, frameworks, history, http_client, integrations, notebook
from shatuide import refactor, remote, runner, scripting, snippets, testing, tools, vcs
from shatuide.complete import completions
from shatuide.debug_session import DebugSession
from shatuide.edit import replace_project
from shatuide.shell_debug import PowerShellDebugSession, ShellDebugSession
from shatuide.formatter import format_source
from shatuide.icon_util import load_icon_bytes
from shatuide.paths import SKIP_DIRS, STATIC, default_workspace, inside, meta_dir
from shatuide.probe import prepare as prepare_probe
from shatuide import creator, kit, studio

MAX_READ = 2_000_000


class KernelSession:
    def __init__(self, python: str, cwd: str, plot_dir: Path) -> None:
        plot_dir.mkdir(parents=True, exist_ok=True)
        worker = Path(__file__).resolve().parent / "kernel_worker.py"
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["MPLBACKEND"] = "Agg"
        env["SHATU_PLOT_DIR"] = str(plot_dir)
        import subprocess

        self.proc = subprocess.Popen(
            [python, "-u", str(worker)],
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self.lock = threading.Lock()
        self.counter = 0
        self.plot_dir = plot_dir

    def execute(self, code: str, timeout: float = 60) -> dict:
        if self.proc.poll() is not None:
            return {"ok": False, "error": "Kernel ist beendet. Neu starten."}
        with self.lock:
            self.counter += 1
            ident = self.counter
            assert self.proc.stdin is not None and self.proc.stdout is not None
            self.proc.stdin.write(json.dumps({"id": ident, "code": code}) + "\n")
            self.proc.stdin.flush()
            line = self._readline(timeout)
        if not line:
            return {"ok": False, "error": "Kernel antwortet nicht."}
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return {"ok": False, "error": line[:500]}
        data["ok"] = not data.get("error")
        return data

    def _readline(self, timeout: float) -> str:
        result: list[str] = []

        def read() -> None:
            assert self.proc.stdout is not None
            result.append(self.proc.stdout.readline())

        thread = threading.Thread(target=read, daemon=True)
        thread.start()
        thread.join(timeout)
        if thread.is_alive():
            return ""
        return result[0] if result else ""

    def close(self) -> None:
        try:
            if self.proc.poll() is None and self.proc.stdin:
                self.proc.stdin.write(json.dumps({"cmd": "shutdown"}) + "\n")
                self.proc.stdin.flush()
                self.proc.wait(timeout=1)
        except (OSError, subprocess.TimeoutExpired):
            pass
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=1)
        for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    pass


class CollabHub:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.docs: dict[str, dict] = {}
        self.httpd: ThreadingHTTPServer | None = None
        self.port = 0

    def start(self, path: str, text: str) -> dict:
        token = secrets.token_hex(3)
        with self.lock:
            self.docs[token] = {"path": path, "text": text, "version": 1}
        if self.httpd is None:
            hub = self

            class CollabHandler(BaseHTTPRequestHandler):
                def log_message(self, fmt: str, *args) -> None:
                    return

                def _json(self, payload: dict, status: int = 200) -> None:
                    raw = json.dumps(payload).encode("utf-8")
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(raw)))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(raw)

                def do_GET(self) -> None:  # noqa: N802
                    parsed = urlparse(self.path)
                    query = parse_qs(parsed.query)
                    token_q = (query.get("token") or [""])[0]
                    if parsed.path in {"/", "/index.html"}:
                        body = (
                            "<!doctype html><meta charset=utf-8><title>ShatuIDE Live</title>"
                            "<textarea id=t style='width:100%;height:80vh'></textarea>"
                            "<script>const token=new URLSearchParams(location.search).get('token');"
                            "async function pull(){const r=await fetch('/sync?token='+token);const j=await r.json();"
                            "if(document.activeElement!==t)t.value=j.text||'';}setInterval(pull,1000);pull();"
                            "t.oninput=()=>fetch('/sync?token='+token,{method:'POST',headers:{'Content-Type':'application/json'},"
                            "body:JSON.stringify({text:t.value})});</script>"
                        ).encode("utf-8")
                        self.send_response(200)
                        self.send_header("Content-Type", "text/html; charset=utf-8")
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                        return
                    if parsed.path == "/sync":
                        with hub.lock:
                            doc = hub.docs.get(token_q)
                        if not doc:
                            self._json({"ok": False, "error": "Unbekannte Sitzung."}, 404)
                            return
                        self._json({"ok": True, **doc})
                        return
                    self._json({"ok": False, "error": "Nicht gefunden."}, 404)

                def do_POST(self) -> None:  # noqa: N802
                    parsed = urlparse(self.path)
                    query = parse_qs(parsed.query)
                    token_q = (query.get("token") or [""])[0]
                    length = int(self.headers.get("Content-Length", "0") or 0)
                    raw = self.rfile.read(length) if length else b"{}"
                    try:
                        payload = json.loads(raw.decode("utf-8") or "{}")
                    except json.JSONDecodeError:
                        payload = {}
                    with hub.lock:
                        doc = hub.docs.get(token_q)
                        if not doc:
                            self._json({"ok": False, "error": "Unbekannte Sitzung."}, 404)
                            return
                        if "text" in payload:
                            doc["text"] = str(payload["text"])[:2_000_000]
                            doc["version"] += 1
                        snapshot = dict(doc)
                    self._json({"ok": True, **snapshot})

            self.httpd = ThreadingHTTPServer(("0.0.0.0", 0), CollabHandler)
            self.httpd.daemon_threads = True
            self.port = self.httpd.server_address[1]
            threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return {"ok": True, "token": token, "port": self.port}

    def publish(self, token: str, text: str) -> dict:
        with self.lock:
            doc = self.docs.get(token)
            if not doc:
                return {"ok": False, "error": "Unbekannte Sitzung."}
            doc["text"] = text
            doc["version"] += 1
            return {"ok": True, "version": doc["version"]}

    def fetch(self, token: str) -> dict:
        with self.lock:
            doc = self.docs.get(token)
            if not doc:
                return {"ok": False, "error": "Unbekannte Sitzung."}
            return {"ok": True, **doc}


class App:
    def __init__(self, workspace: str | None = None) -> None:
        self.token = secrets.token_hex(16)
        cfg = config.load()
        if workspace:
            self.workspace = str(Path(workspace).expanduser().resolve())
        elif os.environ.get("SHATUIDE_WORKSPACE"):
            self.workspace = str(default_workspace())
        elif cfg.get("workspace"):
            self.workspace = str(Path(str(cfg["workspace"])).expanduser())
        else:
            self.workspace = str(default_workspace())
        Path(self.workspace).mkdir(parents=True, exist_ok=True)
        self.python = str(cfg.get("python") or sys.executable)
        self.sessions: dict[str, runner.ProcessSession] = {}
        self.terminals: dict[str, runner.PtyTerminal] = {}
        self.debug: DebugSession | None = None
        self.kernel: KernelSession | None = None
        self.jobs: dict[str, dict] = {}
        self.collab = CollabHub()
        self._ruff: bool | None = None
        self._syms: list[str] = []
        self._sym_time = 0.0
        self.terminal_tail = ""

    def python_exe(self) -> str:
        if self.python and Path(self.python).is_file():
            return self.python
        return sys.executable

    def resolve_write(self, path: str) -> Path:
        if not path:
            raise PermissionError("Pfad fehlt.")
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = Path(self.workspace) / candidate
        resolved = candidate.resolve()
        root = Path(self.workspace).resolve()
        if resolved == root:
            raise PermissionError("Die Workspace-Wurzel kann nicht überschrieben werden.")
        if not inside(root, resolved):
            raise PermissionError("Schreiben nur im geöffneten Workspace.")
        return resolved

    def resolve_any(self, path: str) -> Path:
        if not path:
            return Path(self.workspace).resolve()
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = Path(self.workspace) / candidate
        return candidate.resolve()

    def rel(self, path: Path) -> str:
        root = Path(self.workspace).resolve()
        try:
            return str(path.resolve().relative_to(root))
        except ValueError:
            return str(path)

    def state(self) -> dict:
        cfg = config.load()
        return {
            "ok": True,
            "version": __version__,
            "author": __author__,
            "email": __email__,
            "workspace": self.workspace,
            "python": self.python_exe(),
            "platform": sys.platform,
            "windows_home": r"D:\AI_Temp\ShatuIDE",
            "model": cfg.get("model", "llama3.1"),
            "base_url": cfg.get("base_url", ""),
            "has_api_key": bool(cfg.get("api_key")),
        }

    def set_workspace(self, path: str) -> dict:
        folder = Path(path).expanduser()
        folder.mkdir(parents=True, exist_ok=True)
        self.workspace = str(folder.resolve())
        cfg = config.load()
        cfg["workspace"] = self.workspace
        config.save(cfg)
        if self.kernel:
            self.kernel.close()
            self.kernel = None
        return {"ok": True, "workspace": self.workspace}

    def list_tree(self, path: str) -> dict:
        folder = self.resolve_any(path) if path else Path(self.workspace).resolve()
        root = Path(self.workspace).resolve()
        if not inside(root, folder) and folder != root:
            return {"ok": False, "error": "Ordner liegt außerhalb des Workspace."}
        if not folder.is_dir():
            return {"ok": False, "error": "Kein Ordner."}
        entries = []
        try:
            children = sorted(folder.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
        except OSError as exc:
            return {"ok": False, "error": str(exc)}
        for child in children:
            if child.name in SKIP_DIRS or child.name.startswith("."):
                continue
            entries.append({"name": child.name, "path": str(child), "dir": child.is_dir()})
        return {"ok": True, "path": str(folder), "entries": entries}

    def browse(self, path: str) -> dict:
        folder = self.resolve_any(path) if path else Path(self.workspace).resolve()
        if not folder.exists():
            return {"ok": False, "error": "Pfad nicht gefunden."}
        if not folder.is_dir():
            return {"ok": False, "error": "Kein Ordner."}
        parent = "" if folder.parent == folder else str(folder.parent)
        entries = []
        try:
            children = sorted(folder.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
        except OSError as exc:
            return {"ok": False, "error": str(exc)}
        for child in children:
            if child.name in SKIP_DIRS:
                continue
            try:
                is_dir = child.is_dir()
            except OSError:
                continue
            entries.append({"name": child.name, "path": str(child), "dir": is_dir})
            if len(entries) >= 800:
                break
        return {
            "ok": True,
            "path": str(folder),
            "parent": parent,
            "workspace": self.workspace,
            "home": str(Path.home()),
            "entries": entries,
        }

    def read_file(self, path: str) -> dict:
        target = self.resolve_any(path)
        if not target.is_file():
            return {"ok": False, "error": "Datei nicht gefunden."}
        if target.stat().st_size > 20_000_000:
            return {"ok": False, "error": "Datei ist größer als 20 MB."}
        writable = inside(Path(self.workspace), target)
        data = target.read_bytes()
        if b"\x00" in data[:1024]:
            return {"ok": True, "path": str(target), "binary": True, "content": "", "writable": writable}
        return {
            "ok": True,
            "path": str(target),
            "binary": False,
            "content": data.decode("utf-8", "replace"),
            "writable": writable,
        }

    def write_file(self, path: str, content: str) -> dict:
        target = self.resolve_write(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        relative = self.rel(target)
        previous = target.read_text(encoding="utf-8", errors="replace") if target.is_file() else ""
        if previous and previous != content:
            history.snapshot(Path(self.workspace), relative, previous)
        target.write_text(content, encoding="utf-8")
        return {"ok": True, "path": str(target)}

    def make_dir(self, path: str) -> dict:
        target = self.resolve_write(path)
        target.mkdir(parents=True, exist_ok=True)
        return {"ok": True, "path": str(target)}

    def delete_path(self, path: str) -> dict:
        target = self.resolve_write(path)
        if target.is_dir():
            if any(target.iterdir()):
                return {"ok": False, "error": "Ordner ist nicht leer."}
            target.rmdir()
        elif target.is_file():
            target.unlink()
        else:
            return {"ok": False, "error": "Nicht gefunden."}
        return {"ok": True}

    def move_path(self, src: str, dst: str) -> dict:
        source = self.resolve_write(src)
        target = self.resolve_write(dst)
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
        return {"ok": True, "path": str(target)}

    def project_sources(self, limit: int = 1500) -> dict[str, str]:
        files: dict[str, str] = {}
        for path in analysis.iter_project_files(self.workspace, limit=limit):
            if path.suffix != ".py" or path.stat().st_size > MAX_READ:
                continue
            try:
                files[str(path)] = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
        return files

    def project_symbols(self) -> list[str]:
        now = time.time()
        if now - self._sym_time < 3:
            return self._syms
        names: list[str] = []
        for path, text in self.project_sources(600).items():
            for item in analysis.outline(text):
                names.append(item["name"])
            if len(names) > 2500:
                break
        self._syms = names
        self._sym_time = now
        return names

    def ruff_problems(self, source: str, filename: str) -> list[dict]:
        if self._ruff is False:
            return []
        import subprocess

        try:
            proc = subprocess.run(
                [self.python_exe(), "-m", "ruff", "check", "--output-format", "json", "--stdin-filename", filename or "datei.py", "-"],
                input=source,
                text=True,
                capture_output=True,
                timeout=8,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            self._ruff = False
            return []
        if "No module named ruff" in (proc.stderr or "") or "No module named" in (proc.stderr or "") and "ruff" in (proc.stderr or ""):
            self._ruff = False
            return []
        if not proc.stdout.strip():
            return []
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return []
        items = data if isinstance(data, list) else data.get("diagnostics", [])
        problems = []
        for item in items:
            if not isinstance(item, dict):
                continue
            loc = item.get("location") or item.get("start") or {}
            row = loc.get("row") or loc.get("line") or 1
            col = loc.get("column") or loc.get("col") or 1
            problems.append(
                {
                    "line": row,
                    "col": max(0, int(col) - 1),
                    "end_line": row,
                    "end_col": 0,
                    "severity": "warning",
                    "message": item.get("message", "Ruff"),
                    "code": item.get("code") or "RUFF",
                }
            )
        self._ruff = True
        return problems

    def analyze(self, source: str, path: str) -> dict:
        lang = scripting.language_of(path or "")
        if lang == "json":
            return {
                "ok": True,
                "problems": scripting.json_problems(source),
                "outline": scripting.json_outline(source),
                "todos": [],
            }
        if lang in {"powershell", "shell", "batch"}:
            return {
                "ok": True,
                "problems": [],
                "outline": scripting.script_outline(source, path or ""),
                "todos": analysis.todos_in_source(source, path),
            }
        problems = analysis.lint_source(source, path or "<memory>")
        problems.extend(self.ruff_problems(source, path or "datei.py"))
        return {
            "ok": True,
            "problems": problems,
            "outline": analysis.outline(source),
            "todos": analysis.todos_in_source(source, path),
        }

    def start_job(self, func) -> str:
        job_id = secrets.token_hex(4)
        job = {"id": job_id, "log": [], "done": False, "result": None}
        self.jobs[job_id] = job

        def wrap() -> None:
            try:
                job["result"] = func(lambda message: job["log"].append(str(message)))
            except Exception as exc:
                job["result"] = {"ok": False, "error": str(exc)}
                job["log"].append(str(exc))
            job["done"] = True

        threading.Thread(target=wrap, daemon=True).start()
        return job_id

    def _agent_path(self, path: str) -> Path:
        return self.resolve_write(path) if path not in {"", "."} else Path(self.workspace).resolve()

    def agent_call(self, tool: str, args: dict) -> str:
        root = Path(self.workspace).resolve()
        try:
            if tool == "list_dir":
                folder = root if args.get("path") in {None, "", "."} else self.resolve_write(str(args.get("path")))
                if folder == root or inside(root, folder):
                    if not folder.exists() and args.get("path") in {None, "", "."}:
                        folder = root
                    if not folder.is_dir():
                        folder = self.resolve_write(str(args.get("path")))
                entries = []
                target = folder if folder.is_dir() else root
                for child in sorted(target.iterdir(), key=lambda item: item.name.lower()):
                    if child.name in SKIP_DIRS or child.name.startswith("."):
                        continue
                    entries.append({"name": child.name, "dir": child.is_dir()})
                return json.dumps(entries[:400], ensure_ascii=False)
            if tool == "read_file":
                target = self.resolve_write(str(args.get("path") or ""))
                if target.is_dir():
                    return "Das ist ein Ordner."
                return target.read_text(encoding="utf-8", errors="replace")[:20000]
            if tool == "write_file":
                target = self.resolve_write(str(args.get("path") or ""))
                content = str(args.get("content") or "")
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.is_file():
                    history.snapshot(root, self.rel(target), target.read_text(encoding="utf-8", errors="replace"))
                target.write_text(content, encoding="utf-8")
                return f"geschrieben: {target} ({len(content)} Zeichen)"
            if tool == "search":
                query = str(args.get("query") or "").lower()
                hits = []
                for path, text in self.project_sources(400).items():
                    for index, line in enumerate(text.splitlines(), start=1):
                        if query and query in line.lower():
                            hits.append(f"{path}:{index}: {line.strip()[:160]}")
                            if len(hits) >= 40:
                                return "\n".join(hits)
                return "\n".join(hits) or "Keine Treffer."
            if tool == "pip_install":
                package = str(args.get("package") or "")
                result = tools.pip_install(self.python_exe(), [package])
                return (result.get("stdout") or "")[-4000] + (result.get("error") or "")
            if tool == "run_python":
                target = self.resolve_write(str(args.get("path") or ""))
                import subprocess

                proc = subprocess.run(
                    [self.python_exe(), "-u", str(target)],
                    cwd=str(target.parent),
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
                return f"Code {proc.returncode}\n{proc.stdout[-6000]}\n{proc.stderr[-3000]}"
            if tool == "run_tests":
                import subprocess

                argv = testing.test_argv(self.python_exe(), self.workspace, self.workspace, "auto")
                proc = subprocess.run(argv, cwd=self.workspace, capture_output=True, text=True, timeout=120, check=False)
                return f"Code {proc.returncode}\n{proc.stdout[-6000]}\n{proc.stderr[-2000]}"
        except Exception as exc:
            return f"Fehler: {exc}"
        return f"Unbekanntes Werkzeug: {tool}"

    def run_agent(self, prompt: str, log) -> dict:
        cfg = config.load()
        messages = [{"role": "user", "content": prompt}]
        steps = []
        for step in range(12):
            log(f"Schritt {step + 1}")
            system = ai.AGENT_SYSTEM
            extra = str(cfg.get("system_prompt") or "").strip()
            if extra:
                system += "\n\nZusätzliche Anweisung:\n" + extra
            reply = ai.chat_completion(
                str(cfg.get("base_url") or ""),
                str(cfg.get("api_key") or ""),
                str(cfg.get("model") or "llama3.1"),
                ai.build_messages(system, messages),
                timeout=120,
            )
            if not reply.get("ok"):
                return {"ok": False, "error": reply.get("error"), "steps": steps}
            parsed = ai.parse_agent_message(reply.get("content") or "")
            if not parsed.get("ok"):
                steps.append({"message": reply.get("content", "")[:2000]})
                return {"ok": False, "error": parsed.get("error"), "steps": steps}
            entry = {"message": parsed.get("message", ""), "tool": parsed.get("tool"), "args": parsed.get("args")}
            if parsed.get("done"):
                steps.append(entry)
                log(entry["message"])
                return {"ok": True, "steps": steps, "message": entry["message"]}
            tool = str(parsed.get("tool") or "")
            args = parsed.get("args") if isinstance(parsed.get("args"), dict) else {}
            log(f"{tool} {json.dumps(args, ensure_ascii=False)[:300]}")
            result = self.agent_call(tool, args)
            entry["result"] = result[:4000]
            steps.append(entry)
            messages.append({"role": "assistant", "content": json.dumps(parsed, ensure_ascii=False)})
            messages.append({"role": "user", "content": f"Werkzeugergebnis {tool}:\n{result[:12000]}"})
        return {"ok": False, "error": "Schrittlimit erreicht.", "steps": steps}

    def context_from(self, text: str, path: str, content: str) -> str:
        parts: list[str] = []
        if any(token in text for token in ("@file", "@datei")) and content:
            parts.append(f"Aktuelle Datei {path}:\n{content[:30000]}")
        if "@terminal" in text and self.terminal_tail:
            parts.append("Terminal:\n" + self.terminal_tail[-8000:])
        if "@git" in text or "@diff" in text:
            diff = vcs.diff(Path(self.workspace))
            parts.append("Git-Diff:\n" + (diff.get("stdout") or diff.get("error") or "")[-8000])
        for match in re.findall(r"@(\S+)", text):
            if match in {"file", "datei", "terminal", "git", "diff"}:
                continue
            try:
                target = self.resolve_any(match)
            except OSError:
                continue
            if target.is_file():
                try:
                    parts.append(f"Datei {target}:\n" + target.read_text(encoding="utf-8", errors="replace")[:20000])
                except OSError:
                    continue
            elif target.is_dir() and (inside(self.workspace, target) or target == Path(self.workspace).resolve()):
                names = [child.name for child in target.iterdir() if child.name not in SKIP_DIRS][:200]
                parts.append(f"Ordner {target}:\n" + "\n".join(names))
        return "\n\n".join(parts)[:60000]

    def bookmarks_path(self) -> Path:
        return meta_dir(Path(self.workspace)) / "bookmarks.json"

    def bookmarks(self, action: str, payload: dict) -> dict:
        path = self.bookmarks_path()
        try:
            items = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
        except json.JSONDecodeError:
            items = []
        if action == "add":
            items.append({"path": payload.get("path", ""), "line": int(payload.get("line") or 1), "note": payload.get("note", "")})
            path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
        elif action == "remove":
            index = int(payload.get("index", -1))
            if 0 <= index < len(items):
                items.pop(index)
                path.write_text(json.dumps(items, indent=2), encoding="utf-8")
        return {"ok": True, "items": items}

    def ensure_kernel(self) -> KernelSession:
        if self.kernel is None or self.kernel.proc.poll() is not None:
            plot = meta_dir(Path(self.workspace)) / "plots"
            self.kernel = KernelSession(self.python_exe(), self.workspace, plot)
        return self.kernel


class Handler(BaseHTTPRequestHandler):
    server: "Server"

    def log_message(self, fmt: str, *args) -> None:
        return

    @property
    def app(self) -> App:
        return self.server.app

    def _authorized(self) -> bool:
        header = self.headers.get("X-Shatu-Token", "")
        if header and secrets.compare_digest(header, self.app.token):
            return True
        cookie = self.headers.get("Cookie", "")
        return f"shatu_session={self.app.token}" in cookie

    def _host_ok(self) -> bool:
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in {"127.0.0.1", "localhost"}

    def _json(self, payload: dict, status: int = 200) -> None:
        raw = json.dumps(payload, default=str, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        if not raw:
            return {}
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}

    def _guard(self) -> bool:
        if not self._host_ok():
            self._json({"ok": False, "error": "Nur localhost."}, 403)
            return False
        if not self._authorized():
            self._json({"ok": False, "error": "Nicht angemeldet."}, 403)
            return False
        return True

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)
        if not self._host_ok():
            self._json({"ok": False, "error": "Nur localhost."}, 403)
            return
        if path in {"/", "/index.html"}:
            self._page()
            return
        if path == "/probe":
            self._html("probe.html")
            return
        if path.startswith("/static/"):
            self._static(path[len("/static/") :])
            return
        if path == "/api/icon":
            data, content_type = load_icon_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return
        if not self._authorized():
            self._json({"ok": False, "error": "Nicht angemeldet."}, 403)
            return
        try:
            self._get(path, query)
        except Exception as exc:
            self._json({"ok": False, "error": str(exc), "trace": traceback.format_exc()[-1500:]}, 500)

    def do_POST(self) -> None:  # noqa: N802
        if not self._guard():
            return
        parsed = urlparse(self.path)
        try:
            payload = self._read_json()
            self._post(unquote(parsed.path), payload)
        except PermissionError as exc:
            self._json({"ok": False, "error": str(exc)}, 403)
        except Exception as exc:
            self._json({"ok": False, "error": str(exc), "trace": traceback.format_exc()[-1500:]}, 500)

    def _page(self) -> None:
        self._html("index.html")

    def _html(self, name: str) -> None:
        page = (STATIC / name).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.send_header("Set-Cookie", f"shatu_session={self.app.token}; Path=/; SameSite=Strict; HttpOnly")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(page)

    def _static(self, name: str) -> None:
        target = (STATIC / name).resolve()
        if not inside(STATIC, target) or not target.is_file():
            self._json({"ok": False, "error": "Nicht gefunden."}, 404)
            return
        data = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _q(self, query: dict, key: str, default: str = "") -> str:
        return (query.get(key) or [default])[0]

    def _get(self, path: str, query: dict) -> None:
        app = self.app
        if path == "/api/state":
            self._json(app.state())
        elif path == "/api/tree":
            self._json(app.list_tree(self._q(query, "path")))
        elif path == "/api/browse":
            self._json(app.browse(self._q(query, "path")))
        elif path == "/api/file":
            self._json(app.read_file(self._q(query, "path")))
        elif path == "/api/snippets":
            self._json({"ok": True, "snippets": snippets.all_snippets()})
        elif path == "/api/session":
            session = app.sessions.get(self._q(query, "id"))
            if not session:
                self._json({"ok": False, "error": "Keine Sitzung."}, 404)
                return
            self._json(session.poll(int(self._q(query, "from", "0") or 0)))
        elif path == "/api/debug":
            if not app.debug:
                self._json({"ok": True, "running": False, "events": [], "output": []})
                return
            self._json(app.debug.snapshot(int(self._q(query, "from", "0") or 0)))
        elif path == "/api/pythons":
            self._json({"ok": True, "interpreters": tools.discover_interpreters(Path(app.workspace)), "current": app.python_exe()})
        elif path == "/api/tools":
            self._json(tools.tool_status(app.python_exe()))
        elif path == "/api/jobs":
            job = app.jobs.get(self._q(query, "id"))
            self._json(job or {"ok": False, "error": "Auftrag unbekannt."})
        elif path == "/api/history":
            relative = self._q(query, "path")
            self._json({"ok": True, "items": history.list_snapshots(Path(app.workspace), relative)})
        elif path == "/api/frameworks":
            self._json({"ok": True, "items": frameworks.detect(Path(app.workspace), app.python_exe())})
        elif path == "/api/ai/config":
            cfg = config.load()
            self._json(
                {
                    "ok": True,
                    **config.public_view(cfg),
                    "python": app.python_exe(),
                    "providers": integrations.PROVIDERS,
                    "extension_catalog": integrations.EXTENSIONS,
                    "editors": integrations.editor_status(cfg),
                }
            )
        elif path == "/api/bookmarks":
            self._json(app.bookmarks("list", {}))
        elif path == "/api/notebook":
            target = app.resolve_any(self._q(query, "path"))
            self._json(notebook.load_notebook(target))
        elif path == "/api/plot":
            name = Path(self._q(query, "name")).name
            image = meta_dir(Path(app.workspace)) / "plots" / name
            if not image.is_file():
                self._json({"ok": False, "error": "Plot nicht gefunden."}, 404)
                return
            data = image.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif path == "/api/collab":
            self._json(app.collab.fetch(self._q(query, "token")))
        elif path == "/api/studio":
            self._json(self._studio_get(query))
        else:
            self._json({"ok": False, "error": "Unbekannter Pfad."}, 404)

    def _post(self, path: str, payload: dict) -> None:
        app = self.app
        if path == "/api/workspace":
            self._json(app.set_workspace(str(payload.get("path") or "")))
        elif path == "/api/file":
            self._json(app.write_file(str(payload.get("path") or ""), str(payload.get("content") or "")))
        elif path == "/api/mkdir":
            self._json(app.make_dir(str(payload.get("path") or "")))
        elif path == "/api/delete":
            self._json(app.delete_path(str(payload.get("path") or "")))
        elif path == "/api/move":
            self._json(app.move_path(str(payload.get("src") or ""), str(payload.get("dst") or "")))
        elif path == "/api/analyze":
            self._json(app.analyze(str(payload.get("content") or ""), str(payload.get("path") or "")))
        elif path == "/api/complete":
            items = completions(
                str(payload.get("content") or ""),
                int(payload.get("line") or 1),
                int(payload.get("col") or 0),
                app.project_symbols(),
            )
            self._json({"ok": True, "items": items})
        elif path == "/api/format":
            content = str(payload.get("content") or "")
            file_path = str(payload.get("path") or "")
            language = scripting.language_of(file_path)
            if language == "json":
                self._json(scripting.format_json(content))
            elif language in {"powershell", "shell", "batch"}:
                self._json(studio.format_script(language, content))
            else:
                self._json(format_source(content, app.python_exe()))
        elif path == "/api/goto":
            project = app.project_sources(400)
            content = str(payload.get("content") or "")
            line_no = int(payload.get("line") or 1)
            col_no = int(payload.get("col") or 0)
            hits = analysis.goto_definition(content, line_no, col_no, project, str(payload.get("path") or ""))
            if not hits:
                ident = analysis.name_at(content, line_no, col_no)
                origin = analysis.external_file(content, ident)
                if origin:
                    hits = [{"name": ident, "line": 1, "col": 0, "kind": "module", "path": origin}]
            self._json({"ok": True, "hits": hits})
        elif path == "/api/search":
            self._json({"ok": True, "hits": self._search(str(payload.get("query") or ""))})
        elif path == "/api/replace":
            self._json(self._replace(payload))
        elif path == "/api/rename":
            self._json(self._rename(payload))
        elif path == "/api/extract":
            self._json(
                refactor.extract_method(
                    str(payload.get("content") or ""),
                    int(payload.get("start") or 1),
                    int(payload.get("end") or 1),
                    str(payload.get("name") or "extracted"),
                )
            )
        elif path == "/api/duplicates":
            self._json({"ok": True, "groups": analysis.duplicates(app.project_sources())})
        elif path == "/api/todos":
            items = []
            for file_path in analysis.iter_project_files(app.workspace):
                if file_path.suffix.lower() not in {".py", ".md", ".txt", ".rst"}:
                    continue
                try:
                    text = file_path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                items.extend(analysis.todos_in_source(text, str(file_path)))
                if len(items) > 300:
                    break
            self._json({"ok": True, "items": items})
        elif path == "/api/probe":
            self._json(self._probe(payload))
        elif path == "/api/run":
            self._json(self._run(payload))
        elif path == "/api/session/stop":
            session = app.sessions.get(str(payload.get("id") or ""))
            if session:
                session.stop()
            self._json({"ok": True})
        elif path == "/api/session/input":
            session = app.sessions.get(str(payload.get("id") or ""))
            if not session:
                self._json({"ok": False, "error": "Keine Sitzung."}, 404)
                return
            session.write(str(payload.get("data") or ""))
            self._json({"ok": True})
        elif path == "/api/debug/start":
            self._json(self._debug_start(payload))
        elif path == "/api/debug":
            self._json(self._debug_cmd(payload))
        elif path == "/api/tests":
            self._json(self._tests(payload))
        elif path == "/api/coverage":
            self._json(testing.read_coverage(app.python_exe(), app.workspace))
        elif path == "/api/interpreter":
            chosen = str(payload.get("path") or "")
            app.python = chosen
            cfg = config.load()
            cfg["python"] = chosen
            config.save(cfg)
            app._ruff = None
            self._json({"ok": True, "python": app.python_exe()})
        elif path == "/api/venv":
            dest = app.resolve_write(str(payload.get("path") or str(Path(app.workspace) / ".venv")))
            self._json(tools.create_venv(app.python_exe(), dest))
        elif path == "/api/pip":
            self._json(self._pip(payload))
        elif path == "/api/conda":
            self._json(tools.conda_create(str(payload.get("name") or "shatu"), str(payload.get("version") or "3.12")))
        elif path == "/api/poetry":
            self._json(tools.poetry_install(Path(app.workspace)))
        elif path == "/api/pipenv":
            self._json(tools.pipenv_install(Path(app.workspace)))
        elif path == "/api/tools/python":
            job_id = app.start_job(lambda log: tools.download_python(Path(app.workspace), log))
            self._json({"ok": True, "job": job_id})
        elif path == "/api/git":
            self._json(self._git(payload))
        elif path == "/api/history":
            relative = str(payload.get("path") or "")
            snap_id = str(payload.get("id") or "")
            current = str(payload.get("current") or "")
            if payload.get("restore"):
                text = history.read_snapshot(Path(app.workspace), relative, snap_id)
                self._json({"ok": True, "content": text})
            else:
                self._json({"ok": True, "diff": history.diff_snapshot(Path(app.workspace), relative, snap_id, current)})
        elif path == "/api/terminal":
            self._json(self._terminal(payload))
        elif path == "/api/repl":
            self._json(self._repl(payload))
        elif path == "/api/notebook":
            self._json(self._notebook(payload))
        elif path == "/api/db":
            self._json(self._db(payload))
        elif path == "/api/http":
            self._json(self._http(payload))
        elif path == "/api/ai/config":
            self._json(self._save_ai(payload))
        elif path == "/api/ai/models":
            self._json(self._list_models(payload))
        elif path == "/api/editors":
            self._json(self._editors(payload))
        elif path == "/api/ai/chat":
            self._json(self._chat(payload))
        elif path == "/api/ai/inline":
            self._json(self._inline(payload))
        elif path == "/api/ai/fix":
            self._json(self._fix(payload))
        elif path == "/api/ai/agent":
            prompt = str(payload.get("prompt") or "")
            job_id = app.start_job(lambda log: app.run_agent(prompt, log))
            self._json({"ok": True, "job": job_id})
        elif path == "/api/remote":
            self._json(self._remote(payload))
        elif path == "/api/collab":
            self._json(self._collab(payload))
        elif path == "/api/bookmarks":
            self._json(app.bookmarks(str(payload.get("action") or "list"), payload))
        elif path == "/api/compile":
            self._json(self._compile(payload))
        elif path == "/api/studio":
            self._json(self._studio(payload))
        else:
            self._json({"ok": False, "error": "Unbekannter Pfad."}, 404)

    def _studio_get(self, query: dict) -> dict:
        action = self._q(query, "action")
        workspace = Path(self.app.workspace)
        if action == "shells":
            return {"ok": True, "shells": studio.local_shells(), "compilers": studio.compiler_status()}
        if action == "recovery":
            return studio.recovery_list(workspace)
        if action == "help":
            return studio.powershell_help(self._q(query, "topic") or "Get-Help")
        if action == "compilers":
            return studio.compiler_status()
        if action == "kit":
            return kit.catalog_view(workspace)
        return {"ok": False, "error": "Unbekannte Studio-Abfrage."}

    def _studio_dir(self, path: str) -> Path:
        workspace = Path(self.app.workspace)
        if not path:
            return workspace
        try:
            target = self.app.resolve_write(path)
        except Exception:
            return workspace
        return target.parent if target.suffix else target

    def _studio(self, payload: dict) -> dict:
        action = str(payload.get("action") or "")
        workspace = Path(self.app.workspace)
        if action == "recovery":
            return studio.recovery_store(workspace, str(payload.get("path") or ""), str(payload.get("content") or ""))
        if action == "recovery-read":
            return studio.recovery_read(workspace, str(payload.get("id") or ""))
        if action == "recovery-drop":
            return studio.recovery_drop(workspace, str(payload.get("id") or ""))
        if action == "function":
            try:
                content = studio.advanced_function(payload)
            except ValueError as exc:
                return {"ok": False, "error": str(exc)}
            return {"ok": True, "content": content, "suffix": ".ps1"}
        if action == "module":
            try:
                built = studio.build_module(
                    str(payload.get("content") or ""),
                    str(payload.get("name") or "Modul"),
                    str(payload.get("version") or "1.0.0"),
                    str(payload.get("author") or "ShatuIDE"),
                    str(payload.get("description") or ""),
                )
            except ValueError as exc:
                return {"ok": False, "error": str(exc)}
            if not built.get("ok"):
                return built
            folder = self._studio_dir(str(payload.get("path") or ""))
            folder.mkdir(parents=True, exist_ok=True)
            psm1 = folder / f"{built['name']}.psm1"
            psd1 = folder / f"{built['name']}.psd1"
            psm1.write_text(built["psm1"], encoding="utf-8")
            psd1.write_text(built["psd1"], encoding="utf-8")
            return {
                "ok": True,
                "psm1": str(psm1),
                "psd1": str(psd1),
                "functions": built["functions"],
                "message": f"Modul {built['name']} mit {len(built['functions'])} Funktionen.",
            }
        if action == "gui":
            built = studio.gui_script(
                str(payload.get("title") or "Werkzeug"),
                payload.get("controls") or [],
                str(payload.get("language") or "powershell"),
            )
            if not built.get("ok"):
                return built
            raw_title = re.sub(r"[^A-Za-z0-9_-]", "", str(payload.get("title") or "Gui")) or "Gui"
            try:
                stem = studio.safe_name(raw_title, "Gui")
            except ValueError:
                stem = "Gui"
            path = studio.output_dir(workspace) / (stem + built["suffix"])
            path.write_text(built["content"], encoding="utf-8")
            return {"ok": True, "path": str(path), "content": built["content"], "message": "GUI-Skript erzeugt."}
        if action == "service":
            try:
                built = studio.service_sources(
                    str(payload.get("name") or "ShatuDienst"),
                    str(payload.get("description") or ""),
                )
            except ValueError as exc:
                return {"ok": False, "error": str(exc)}
            folder = self._studio_dir(str(payload.get("path") or "")) / built["name"]
            folder.mkdir(parents=True, exist_ok=True)
            written = []
            first = ""
            for filename, text in built["files"].items():
                target = folder / filename
                target.write_text(text, encoding="utf-8")
                written.append(str(target))
                if not first:
                    first = str(target)
            return {
                "ok": True,
                "path": first,
                "files": written,
                "message": f"Dienstskripte für {built['name']} liegen im Workspace. Installieren geht unter Windows mit Administratorrechten.",
            }
        if action == "exe":
            source = str(payload.get("content") or "")
            path = str(payload.get("path") or "")
            language = scripting.language_of(path or "a.py")
            if not source and path:
                try:
                    source = self.app.resolve_any(path).read_text(encoding="utf-8")
                except OSError as exc:
                    return {"ok": False, "error": str(exc)}
            result = studio.compile_exe(
                workspace,
                source,
                language,
                str(payload.get("name") or Path(path).stem or "ShatuApp"),
                target=str(payload.get("target") or "auto"),
                windowed=bool(payload.get("windowed")),
                python=self.app.python_exe(),
            )
            if result.get("argv"):
                started = self._session(result["argv"], str(workspace))
                started["message"] = result.get("message", "")
                started["kind"] = result.get("kind", "")
                return started
            return result
        if action == "msi":
            name = str(payload.get("name") or "ShatuApp")
            paths = payload.get("files") or []
            files: list[Path] = []
            if isinstance(paths, list):
                for item in paths:
                    try:
                        files.append(self.app.resolve_write(str(item)))
                    except Exception:
                        return {"ok": False, "error": "Installer-Datei liegt außerhalb des Workspace."}
            if not files:
                raw_path = str(payload.get("path") or "")
                for option in (studio.output_dir(workspace) / f"{name}.exe", studio.output_dir(workspace) / name):
                    if option.is_file():
                        files.append(option)
                        break
                if not files and raw_path:
                    try:
                        files.append(self.app.resolve_write(raw_path))
                    except Exception:
                        return {"ok": False, "error": "Die Datei liegt außerhalb des Workspace."}
            return studio.build_msi(
                workspace,
                name,
                str(payload.get("version") or "1.0.0"),
                str(payload.get("manufacturer") or "ShatuIDE"),
                files,
            )
        if action == "measure":
            path = str(payload.get("path") or "")
            if not path:
                return {"ok": False, "error": "Keine Datei."}
            script = self.app.resolve_any(path)
            if not script.is_file():
                return {"ok": False, "error": "Datei nicht gefunden."}
            plan = studio.measure_invocation(
                scripting.language_of(str(script)),
                str(script),
                self.app.python_exe(),
                meta_dir(workspace) / "tmp",
            )
            if not plan.get("ok"):
                return plan
            started = self._session(plan["argv"], str(script.parent))
            started["message"] = "Messung läuft."
            return started
        if action == "help":
            return studio.powershell_help(str(payload.get("topic") or "Get-Help"))
        if action == "remote":
            plan = studio.remote_powershell(
                str(payload.get("transport") or "local"),
                str(payload.get("host") or ""),
                str(payload.get("command") or payload.get("content") or ""),
                str(payload.get("user") or ""),
            )
            if not plan.get("ok"):
                return plan
            started = self._session(plan["argv"], str(workspace))
            started["message"] = "Remote-Befehl läuft."
            return started
        if action == "trace":
            path = str(payload.get("path") or "")
            content = str(payload.get("content") or "")
            if path and not content:
                try:
                    content = self.app.resolve_any(path).read_text(encoding="utf-8")
                except OSError:
                    content = ""
            plan = studio.remote_trace(
                scripting.language_of(path or "a.py"),
                path or "skript",
                content,
                str(payload.get("transport") or "local"),
                str(payload.get("host") or ""),
                str(payload.get("user") or ""),
                self.app.python_exe(),
            )
            if not plan.get("ok"):
                return plan
            if plan.get("argv"):
                cwd = str(Path(path).parent) if path and Path(path).parent.is_dir() else str(workspace)
                started = self._session(plan["argv"], cwd)
                started["message"] = "Ablaufverfolgung läuft."
                return started
            return plan
        if action == "script":
            return self._create_script(payload)
        if action == "database":
            return creator.create_database(workspace, payload)
        if action == "kit":
            return self._kit(payload)
        return {"ok": False, "error": "Unbekannte Studio-Aktion."}

    def _kit(self, payload: dict) -> dict:
        op = str(payload.get("op") or "build")
        workspace = Path(self.app.workspace)
        if op == "load":
            return kit.load_kit(workspace, str(payload.get("name") or ""))
        if op == "save":
            return kit.save_kit(workspace, payload)
        if op != "build":
            return {"ok": False, "error": "Unbekannte Baukasten-Aktion."}
        built = kit.build_kit(payload)
        if not built.get("ok"):
            return built
        saved = kit.save_kit(workspace, payload)
        if not saved.get("ok"):
            return saved
        target = studio.output_dir(workspace) / f"{built['name']}{built['suffix']}"
        target.write_text(built["content"], encoding="utf-8")
        if built["suffix"] == ".sh":
            target.chmod(target.stat().st_mode | 0o111)
        return {
            "ok": True,
            "path": str(target),
            "kit": saved["path"],
            "content": built["content"],
            "language": built["language"],
            "message": built["message"] + " Datei " + target.name + ".",
        }

    def _create_script(self, payload: dict) -> dict:
        if payload.get("use_model"):
            prepared = creator.model_messages(payload)
            if not prepared.get("ok"):
                return prepared
            cfg = config.load()
            result = ai.chat_completion(
                str(cfg.get("base_url") or ""),
                str(cfg.get("api_key") or ""),
                str(cfg.get("model") or ""),
                prepared["messages"],
            )
            if not result.get("ok"):
                return result
            built = creator.script_from_model(payload, str(result.get("content") or ""))
        else:
            built = creator.build_script(payload)
        if not built.get("ok"):
            return built
        target = studio.output_dir(Path(self.app.workspace)) / f"{built['name']}{built['suffix']}"
        target.write_text(built["content"], encoding="utf-8")
        if built["suffix"] == ".sh":
            target.chmod(target.stat().st_mode | 0o111)
        return {
            "ok": True,
            "path": str(target),
            "content": built["content"],
            "language": built["language"],
            "source": built["source"],
            "message": built["message"] + " Datei " + target.name + ".",
        }

    def _search(self, query: str) -> list[dict]:
        query = query.strip()
        if len(query) < 2:
            return []
        low = query.lower()
        hits: list[dict] = []
        for key, label in {
            "workspace": "Einstellung Workspace",
            "interpreter": "Einstellung Interpreter",
            "modell": "Einstellung Sprachmodell",
            "ollama": "KI Ollama",
        }.items():
            if low in key or low in label.lower():
                hits.append({"kind": "setting", "path": label, "line": 1, "text": label})
        for file_path in analysis.iter_project_files(self.app.workspace, limit=2000):
            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if file_path.suffix == ".py":
                for item in analysis.outline(text):
                    if low in item["name"].lower():
                        hits.append({"kind": "symbol", "path": str(file_path), "line": item["line"], "text": item["name"]})
            for index, line in enumerate(text.splitlines(), start=1):
                if low in line.lower():
                    hits.append({"kind": "text", "path": str(file_path), "line": index, "text": line.strip()[:180]})
                    if len(hits) >= 250:
                        return hits
        return hits

    def _rename(self, payload: dict) -> dict:
        old = str(payload.get("old") or "")
        new = str(payload.get("new") or "")
        if payload.get("project"):
            files = self.app.project_sources()
            if payload.get("preview"):
                return refactor.preview_rename(files, old, new)
            renamed = refactor.rename_project(files, old, new)
            if not renamed.get("ok"):
                return renamed
            for path, content in renamed.get("files", {}).items():
                Path(path).write_text(content, encoding="utf-8")
            return renamed
        return refactor.rename_source(str(payload.get("content") or ""), old, new)

    def _session(self, args: list[str], cwd: str) -> dict:
        session = runner.ProcessSession(args, cwd)
        ident = secrets.token_hex(4)
        self.app.sessions[ident] = session
        return {"ok": True, "id": ident}

    def _replace(self, payload: dict) -> dict:
        return replace_project(
            self.app.workspace,
            str(payload.get("query") or ""),
            str(payload.get("replacement") or ""),
            case=bool(payload.get("case")),
            word=bool(payload.get("word")),
            regex=bool(payload.get("regex")),
            preview=bool(payload.get("preview", True)),
        )

    def _probe(self, payload: dict) -> dict:
        return prepare_probe(
            str(payload.get("content") or ""),
            str(payload.get("path") or ""),
            int(payload.get("start") or 1),
            int(payload.get("end") or payload.get("start") or 1),
            str(payload.get("selected") or ""),
            str(payload.get("scope") or "mark"),
        )

    def _run(self, payload: dict) -> dict:
        mode = str(payload.get("mode") or "file")
        python = self.app.python_exe()
        path = str(payload.get("path") or "")
        if mode == "selection":
            folder = meta_dir(Path(self.app.workspace)) / "tmp"
            folder.mkdir(parents=True, exist_ok=True)
            suffix = scripting.selection_suffix(path)
            script = folder / f"selection{suffix}"
            script.write_text(runner.selection_code(str(payload.get("content") or "")), encoding="utf-8")
            try:
                argv = scripting.run_argv(str(script), python, payload.get("args") or [])
            except RuntimeError as exc:
                return {"ok": False, "error": str(exc)}
            return self._session(argv, self.app.workspace)
        if mode == "framework":
            argv = payload.get("argv") or []
            if not isinstance(argv, list) or not argv:
                return {"ok": False, "error": "Startbefehl fehlt."}
            cwd = str(payload.get("cwd") or self.app.workspace)
            return self._session([str(part) for part in argv], cwd)
        if not path:
            return {"ok": False, "error": "Keine Datei."}
        script = self.app.resolve_any(path)
        cwd = str(script.parent if script.is_file() else Path(self.app.workspace))
        if mode == "pyinstaller":
            if scripting.language_of(str(script)) != "python":
                return {"ok": False, "error": "PyInstaller packt nur Python-Dateien."}
            return self._session(runner.pyinstaller_args(python, str(script)), cwd)
        try:
            argv = scripting.run_argv(str(script), python, payload.get("args") or [])
        except RuntimeError as exc:
            return {"ok": False, "error": str(exc)}
        return self._session(argv, cwd)

    def _compile(self, payload: dict) -> dict:
        mode = str(payload.get("mode") or "file")
        if mode == "project":
            return runner.compile_tree(self.app.workspace)
        path = str(payload.get("path") or "")
        if mode == "check" or (path and scripting.language_of(path) in {"shell", "powershell", "batch", "json"}):
            if mode != "check" and path and scripting.language_of(path) == "python":
                return runner.compile_file(str(self.app.resolve_any(path)))
            content = payload.get("content")
            target = str(self.app.resolve_any(path)) if path and content is None and mode != "check" else (path or "<memory>")
            if path and content is None and mode != "check":
                return scripting.syntax_check(target, None)
            return scripting.syntax_check(path or "<memory>", None if content is None else str(content))
        if not path:
            source = str(payload.get("content") or "")
            try:
                compile(source, path or "<memory>", "exec")
            except SyntaxError as exc:
                return {"ok": False, "error": f"Zeile {exc.lineno}: {exc.msg}"}
            return {"ok": True, "message": "Syntax in Ordnung."}
        return runner.compile_file(str(self.app.resolve_any(path)))

    def _debug_start(self, payload: dict) -> dict:
        if self.app.debug:
            self.app.debug.close()
            self.app.debug = None
        script = self.app.resolve_any(str(payload.get("path") or ""))
        if not script.is_file():
            return {"ok": False, "error": "Datei nicht gefunden."}
        points = payload.get("breakpoints") or []
        bp_file = meta_dir(Path(self.app.workspace)) / "breakpoints.json"
        lang = scripting.language_of(str(script))
        try:
            if lang == "shell":
                session = ShellDebugSession()
                session.start(str(script), str(script.parent), points, bp_file)
            elif lang == "powershell":
                session = PowerShellDebugSession()
                session.start(str(script), str(script.parent), points, bp_file)
            elif lang == "json":
                return {"ok": False, "error": "JSON-Dateien haben keinen Debugger. Syntax prüfen nennt die Fehlerzeile."}
            elif lang == "python":
                session = DebugSession()
                session.start(self.app.python_exe(), str(script), str(script.parent), points, bp_file)
            else:
                return {"ok": False, "error": "Debuggen gibt es für Python, Bash und PowerShell."}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        self.app.debug = session
        return {"ok": True}

    def _debug_cmd(self, payload: dict) -> dict:
        session = self.app.debug
        if not session:
            return {"ok": False, "error": "Kein Debugger."}
        points = payload.get("breakpoints")
        if isinstance(points, list):
            session.update_breakpoints(points)
        cmd = str(payload.get("cmd") or "")
        if cmd:
            message = {"cmd": cmd}
            if payload.get("expr"):
                message["expr"] = payload["expr"]
            if isinstance(points, list):
                message["points"] = points
            session.command(message)
        return session.snapshot()

    def _tests(self, payload: dict) -> dict:
        target = str(payload.get("path") or self.app.workspace)
        framework = str(payload.get("framework") or "auto")
        try:
            argv = testing.test_argv(self.app.python_exe(), self.app.workspace, target, framework)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        if payload.get("coverage"):
            try:
                argv = testing.coverage_argv(self.app.python_exe(), self.app.workspace, target)
            except Exception as exc:
                return {"ok": False, "error": str(exc)}
        return self._session(argv, self.app.workspace)

    def _pip(self, payload: dict) -> dict:
        action = str(payload.get("action") or "list")
        python = self.app.python_exe()
        if action == "list":
            return tools.pip_list(python)
        if action == "search":
            return tools.pip_search_pypi(str(payload.get("query") or payload.get("package") or ""))
        if action == "install":
            packages = payload.get("packages") or [payload.get("package")]
            packages = [str(item) for item in packages if item]
            return tools.pip_install(python, packages)
        if action == "group":
            group = str(payload.get("group") or "")
            packages = tools.TOOL_GROUPS.get(group)
            if not packages:
                return {"ok": False, "error": "Unbekannte Werkzeuggruppe."}
            return tools.pip_install(python, packages)
        return {"ok": False, "error": "Unbekannte pip-Aktion."}

    def _git(self, payload: dict) -> dict:
        cwd = Path(self.app.workspace)
        action = str(payload.get("action") or "status")
        if action == "status":
            return vcs.status(cwd)
        if action == "diff":
            return vcs.diff(cwd, payload.get("path"), bool(payload.get("staged")))
        if action == "log":
            return vcs.log(cwd)
        if action == "branches":
            return vcs.branches(cwd)
        if action == "add":
            paths = payload.get("paths") or ["."]
            return vcs.run_git(cwd, ["add", "--", *[str(item) for item in paths]])
        if action == "commit":
            message = str(payload.get("message") or "").strip()
            if not message:
                return {"ok": False, "error": "Commit-Nachricht fehlt."}
            return vcs.run_git(cwd, ["commit", "-m", message])
        if action == "checkout":
            branch = str(payload.get("branch") or "")
            if not re.match(r"^[\w.\-/]+$", branch):
                return {"ok": False, "error": "Ungültiger Branch."}
            return vcs.run_git(cwd, ["checkout", branch])
        if action == "branch":
            name = str(payload.get("name") or "")
            if not re.match(r"^[\w.\-/]+$", name):
                return {"ok": False, "error": "Ungültiger Branchname."}
            return vcs.run_git(cwd, ["branch", name])
        if action == "push":
            return self._git_remote(cwd, ["push"])
        if action == "pull":
            return self._git_remote(cwd, ["pull"])
        if action == "clone":
            url = str(payload.get("url") or "")
            dest_name = str(payload.get("dest") or "repo")
            if not re.match(r"^[\w.\-]+$", dest_name):
                return {"ok": False, "error": "Ungültiger Zielname."}
            return vcs.clone(url, cwd / dest_name, github_token=self._github_token())
        if action == "conflicts":
            return {"ok": True, "files": vcs.conflicts(cwd)}
        if action == "resolve":
            target = self.app.resolve_write(str(payload.get("path") or ""))
            text = target.read_text(encoding="utf-8", errors="replace")
            target.write_text(vcs.take_side(text, str(payload.get("side") or "ours")), encoding="utf-8")
            return {"ok": True, "path": str(target)}
        return {"ok": False, "error": "Unbekannte Git-Aktion."}

    def _github_token(self) -> str:
        return str(config.load().get("github_token") or "")

    def _git_remote(self, cwd: Path, args: list[str]) -> dict:
        url = vcs.origin_url(cwd)
        return vcs.run_git(cwd, args, timeout=40, github_token=self._github_token(), auth_urls=[url])

    def _terminal(self, payload: dict) -> dict:
        action = str(payload.get("action") or "read")
        ident = str(payload.get("id") or "")
        if action == "start":
            requested = str(payload.get("shell") or "")
            chosen = studio.match_shell(requested)
            if requested and not chosen:
                return {"ok": False, "error": "Diese Shell ist nicht installiert."}
            term = runner.PtyTerminal(self.app.workspace, chosen or None)
            ident = secrets.token_hex(4)
            self.app.terminals[ident] = term
            return {"ok": True, "id": ident}
        term = self.app.terminals.get(ident)
        if not term:
            return {"ok": False, "error": "Kein Terminal."}
        if action == "write":
            data = str(payload.get("data") or "")
            term.write(data)
            return {"ok": True}
        if action == "close":
            term.close()
            self.app.terminals.pop(ident, None)
            return {"ok": True}
        snap = term.read_from(int(payload.get("from") or 0))
        self.app.terminal_tail = snap.get("text", "")[-8000:] or self.app.terminal_tail
        snap["ok"] = True
        snap["id"] = ident
        return snap

    def _repl(self, payload: dict) -> dict:
        if payload.get("restart") and self.app.kernel:
            self.app.kernel.close()
            self.app.kernel = None
        kernel = self.app.ensure_kernel()
        if "code" not in payload:
            return {"ok": True, "restarted": bool(payload.get("restart"))}
        result = kernel.execute(str(payload.get("code") or ""))
        return result

    def _notebook(self, payload: dict) -> dict:
        target = self.app.resolve_write(str(payload.get("path") or "notebook.ipynb"))
        action = str(payload.get("action") or "save")
        cells = payload.get("cells") or []
        if action == "save":
            return notebook.save_notebook(target, cells)
        if action == "run":
            index = int(payload.get("index") or 0)
            source = str(payload.get("source") or "")
            if not source and cells:
                source = str(cells[index].get("source") or "")
            result = self.app.ensure_kernel().execute(source)
            result["index"] = index
            return result
        return {"ok": False, "error": "Unbekannte Notebook-Aktion."}

    def _db(self, payload: dict) -> dict:
        engine = str(payload.get("engine") or "sqlite")
        if payload.get("action") == "schema" and engine == "sqlite":
            path = str(payload.get("path") or "")
            return database.sqlite_schema(str(self.app.resolve_any(path)))
        path = str(payload.get("path") or "")
        if engine == "sqlite" and path and not Path(path).is_absolute():
            path = str((Path(self.app.workspace) / path).resolve())
        mongo_query = payload.get("query") if isinstance(payload.get("query"), dict) else {}
        return database.query(
            engine,
            sql=str(payload.get("sql") or ""),
            path=path,
            dsn=str(payload.get("dsn") or ""),
            database=str(payload.get("database") or ""),
            collection=str(payload.get("collection") or ""),
            mongo_query=mongo_query,
        )

    def _http(self, payload: dict) -> dict:
        if payload.get("text"):
            parsed = http_client.parse_http_file(str(payload.get("text")))
            if not parsed.get("ok"):
                return parsed
            result = http_client.send_request(parsed["method"], parsed["url"], parsed.get("headers"), parsed.get("body", ""))
        else:
            headers = payload.get("headers") if isinstance(payload.get("headers"), dict) else {}
            result = http_client.send_request(
                str(payload.get("method") or "GET"),
                str(payload.get("url") or ""),
                headers,
                str(payload.get("body") or ""),
            )
        if result.get("body"):
            result["body"] = http_client.pretty_body(result["body"])
        return result

    def _ai_key(self, payload: dict, cfg: dict) -> str:
        key = payload.get("api_key")
        if isinstance(key, str) and key and not set(key) <= {"•"}:
            return key
        return str(cfg.get("api_key") or "")

    def _list_models(self, payload: dict) -> dict:
        cfg = config.load()
        base = str(payload.get("base_url") or cfg.get("base_url") or "").strip()
        return ai.list_models(base, self._ai_key(payload, cfg))

    def _editors(self, payload: dict) -> dict:
        cfg = config.load()
        action = str(payload.get("action") or "")
        if action == "github":
            token = self._secret_value(payload.get("github_token"))
            if token is None:
                token = str(cfg.get("github_token") or "")
            if token == "":
                return {"ok": False, "error": "GitHub-Token ist ungültig."}
            return integrations.github_user(token)
        extension_ids = integrations.known_extension_ids(payload.get("extensions") or cfg.get("extensions") or [])
        if action == "write":
            profile = {
                "provider": cfg.get("provider") or "",
                "base_url": cfg.get("base_url") or "",
                "model": cfg.get("model") or "",
                "system_prompt": cfg.get("system_prompt") or "",
                "has_github_token": bool(cfg.get("github_token")),
            }
            written = integrations.write_editor_config(Path(self.app.workspace), extension_ids, profile)
            written["message"] = "VS-Code-Konfiguration geschrieben. Schlüssel bleiben in der Nutzerdatei."
            return written
        if action == "open":
            kind = str(payload.get("kind") or "vscode")
            key = {"vscode": "editor_vscode", "visualstudio": "editor_visualstudio", "windsurf": "editor_windsurf"}.get(kind)
            if not key:
                return {"ok": False, "error": "Unbekannter Editor."}
            return integrations.open_editor(kind, Path(self.app.workspace), str(cfg.get(key) or ""))
        if action == "install":
            binary = integrations.editor_binary("vscode", str(cfg.get("editor_vscode") or ""))
            return integrations.install_extensions(binary, extension_ids)
        return {"ok": False, "error": "Unbekannte Editor-Aktion."}

    def _secret_value(self, value: object) -> str | None:
        if not isinstance(value, str) or not value or set(value) <= {"•"}:
            return None
        if any(char.isspace() for char in value) or len(value) > 400:
            return ""
        return value

    def _save_ai(self, payload: dict) -> dict:
        cfg = config.load()
        provider_id = str(payload.get("provider") or cfg.get("provider") or "")
        preset = integrations.provider_by_id(provider_id) if provider_id else None
        if "provider" in payload:
            if provider_id and preset is None:
                return {"ok": False, "error": "Unbekannter Anbieter."}
            cfg["provider"] = provider_id
        if "base_url" in payload:
            entered = str(payload.get("base_url") or "").strip()
            cfg["base_url"] = entered or (preset["base_url"] if preset else "")
        elif preset and not cfg.get("base_url"):
            cfg["base_url"] = preset["base_url"]
        if "model" in payload:
            entered_model = str(payload.get("model") or "").strip()
            cfg["model"] = entered_model or (preset["model"] if preset and preset.get("model") else "") or "llama3.1"
        elif preset and not cfg.get("model"):
            cfg["model"] = preset["model"] or "llama3.1"
        if "system_prompt" in payload:
            cfg["system_prompt"] = str(payload.get("system_prompt") or "")
        if "extensions" in payload:
            cfg["extensions"] = integrations.known_extension_ids(payload.get("extensions"))
        for source, target in (
            ("editor_vscode", "editor_vscode"),
            ("editor_visualstudio", "editor_visualstudio"),
            ("editor_windsurf", "editor_windsurf"),
        ):
            if source in payload:
                cfg[target] = integrations.safe_editor_path(str(payload.get(source) or ""))
        key = self._secret_value(payload.get("api_key"))
        if key == "":
            return {"ok": False, "error": "API-Schlüssel ist ungültig."}
        if key:
            cfg["api_key"] = key
        github = self._secret_value(payload.get("github_token"))
        if github == "":
            return {"ok": False, "error": "GitHub-Token ist ungültig."}
        if github:
            cfg["github_token"] = github
        config.save(cfg)
        result = {"ok": True, **config.public_view(cfg), "editors": integrations.editor_status(cfg)}
        prompt = str(payload.get("prompt") or "").strip()
        if prompt:
            result["reply"] = self._chat(
                {
                    "messages": [{"role": "user", "content": prompt}],
                    "text": prompt,
                    "path": str(payload.get("path") or ""),
                    "content": str(payload.get("content") or ""),
                }
            )
        return result

    def _chat(self, payload: dict) -> dict:
        cfg = config.load()
        history_items = payload.get("messages") if isinstance(payload.get("messages"), list) else []
        context = self.app.context_from(
            str(payload.get("text") or ""),
            str(payload.get("path") or ""),
            str(payload.get("content") or ""),
        )
        system = ai.resolve_system_prompt(str(cfg.get("system_prompt") or ""))
        messages = ai.build_messages(system, history_items, context)
        return ai.chat_completion(
            str(cfg.get("base_url") or ""),
            str(cfg.get("api_key") or ""),
            str(cfg.get("model") or "llama3.1"),
            messages,
        )

    def _inline(self, payload: dict) -> dict:
        cfg = config.load()
        selection = str(payload.get("selection") or "")
        instruction = str(payload.get("instruction") or "")
        prompt = (
            "Ändere den folgenden Python-Code gemäß der Anweisung. "
            "Gib nur den neuen Code in einem python-Fence zurück.\n\n"
            f"Anweisung: {instruction}\n\nCode:\n```python\n{selection}\n```"
        )
        system = ai.resolve_system_prompt(str(cfg.get("system_prompt") or ""))
        reply = ai.chat_completion(
            str(cfg.get("base_url") or ""),
            str(cfg.get("api_key") or ""),
            str(cfg.get("model") or "llama3.1"),
            ai.build_messages(system, [{"role": "user", "content": prompt}]),
        )
        if not reply.get("ok"):
            return reply
        return {"ok": True, "content": ai.extract_code(reply.get("content") or ""), "raw": reply.get("content")}

    def _fix(self, payload: dict) -> dict:
        cfg = config.load()
        prompt = (
            "Der folgende Python-Lauf ist fehlgeschlagen. Erkläre kurz die Ursache und gib den korrigierten Code "
            "der Datei in einem python-Fence zurück.\n\n"
            f"Traceback:\n{str(payload.get('traceback') or '')[:8000]}\n\n"
            f"Code:\n```python\n{str(payload.get('content') or '')[:20000]}\n```"
        )
        system = ai.resolve_system_prompt(str(cfg.get("system_prompt") or ""))
        reply = ai.chat_completion(
            str(cfg.get("base_url") or ""),
            str(cfg.get("api_key") or ""),
            str(cfg.get("model") or "llama3.1"),
            ai.build_messages(system, [{"role": "user", "content": prompt}]),
        )
        if not reply.get("ok"):
            return reply
        return {"ok": True, "content": ai.extract_code(reply.get("content") or ""), "raw": reply.get("content")}

    def _remote(self, payload: dict) -> dict:
        action = str(payload.get("action") or "")
        if action == "ssh":
            return remote.ssh_run(str(payload.get("target") or ""), str(payload.get("command") or ""))
        if action == "docker-ps":
            return remote.docker_ps()
        if action == "docker-logs":
            return remote.docker_logs(str(payload.get("container") or ""))
        if action == "docker-exec":
            return remote.docker_exec(str(payload.get("container") or ""), str(payload.get("command") or ""))
        if action == "wsl":
            return remote.wsl_run(str(payload.get("command") or ""))
        return {"ok": False, "error": "Unbekannte Remote-Aktion."}

    def _collab(self, payload: dict) -> dict:
        action = str(payload.get("action") or "start")
        if action == "start":
            return self.app.collab.start(str(payload.get("path") or ""), str(payload.get("content") or ""))
        if action == "publish":
            return self.app.collab.publish(str(payload.get("token") or ""), str(payload.get("text") or ""))
        return self.app.collab.fetch(str(payload.get("token") or ""))


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    app: App


def create_server(host: str = "127.0.0.1", port: int = 8765, workspace: str | None = None) -> tuple[Server, App]:
    app = App(workspace)
    httpd = Server((host, port), Handler)
    httpd.app = app
    return httpd, app


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="ShatuIDE")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--workspace", default="")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("ShatuIDE bindet nur an localhost.")
    httpd, _app = create_server(args.host, args.port, args.workspace or None)
    url = f"http://{args.host}:{httpd.server_address[1]}/"
    print(f"ShatuIDE {__version__} – {__author__} <{__email__}>")
    print(f"Workspace: {_app.workspace}")
    print(url)
    if not args.no_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nBeendet.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
