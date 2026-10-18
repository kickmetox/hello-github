"""Prüfungen für Analyse, Refactoring, Debugger und die lokale API."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shatuide import analysis, ai, history, http_client, integrations, notebook, refactor, tools
from shatuide.debug_session import DebugSession
from shatuide.formatter import fallback_format
from shatuide.icon_util import crop_center_square, decode_png, encode_png, generated_icon_png, icon_priority, load_icon_bytes
from shatuide.paths import ASSETS
from shatuide.kernel_worker import main as kernel_main  # noqa: F401  (Importpfad)
from shatuide.runner import compile_file
from shatuide.server import KernelSession, create_server


class AnalysisTests(unittest.TestCase):
    def test_syntax_error(self) -> None:
        problems = analysis.lint_source("def f(\n")
        self.assertTrue(any(item["severity"] == "error" for item in problems))

    def test_unused_import_and_types(self) -> None:
        source = "import sys\nimport os\n\ndef add(x: int) -> int:\n    return 'nein'\n\nn: int = 'abc'\nprint(os.name)\n"
        problems = analysis.lint_source(source)
        codes = {item["code"] for item in problems}
        self.assertIn("F401", codes)
        self.assertIn("TYPE", codes)
        self.assertTrue(any("sys" in item["message"] for item in problems))

    def test_undefined_name(self) -> None:
        problems = analysis.lint_source("def f():\n    return fehlt\n")
        self.assertTrue(any(item["code"] == "F821" for item in problems))

    def test_defined_name_is_clean(self) -> None:
        source = "def f(wert: int) -> int:\n    return wert\n"
        codes = {item["code"] for item in analysis.lint_source(source)}
        self.assertNotIn("F821", codes)
        self.assertNotIn("TYPE", codes)

    def test_outline_and_todo(self) -> None:
        source = "class Kiste:\n    def offen(self):\n        pass\n\n# TODO: Deckel\n"
        items = analysis.outline(source)
        self.assertEqual([item["name"] for item in items], ["Kiste", "offen"])
        todos = analysis.todos_in_source(source, "a.py")
        self.assertEqual(todos[0]["tag"], "TODO")

    def test_goto_and_external(self) -> None:
        source = "import pathlib\n\ndef f():\n    return pathlib.Path\n"
        hits = analysis.goto_definition(source, 1, 8, {}, "a.py")
        self.assertTrue(hits)
        origin = analysis.external_file(source, "pathlib")
        self.assertTrue(origin and origin.endswith(".py"))

    def test_duplicates(self) -> None:
        block = "\n".join(f"wert_{i} = {i} * 2 + 3" for i in range(8))
        groups = analysis.duplicates({"a.py": block, "b.py": block})
        self.assertTrue(groups)
        self.assertGreaterEqual(groups[0]["count"], 2)


class RefactorTests(unittest.TestCase):
    def test_rename_skips_strings(self) -> None:
        source = 'def add(x):\n    return x\nprint("add")\n'
        result = refactor.rename_source(source, "add", "plus")
        self.assertTrue(result["ok"])
        self.assertIn("def plus", result["content"])
        self.assertIn('"add"', result["content"])
        self.assertEqual(result["count"], 1)

    def test_extract(self) -> None:
        source = "x = 1\ny = x + 2\nprint(y)\n"
        result = refactor.extract_method(source, 1, 2, "rechnen")
        self.assertTrue(result["ok"], result)
        self.assertIn("def rechnen", result["content"])

    def test_format_fallback(self) -> None:
        self.assertEqual(fallback_format("a = 1   \n"), "a = 1\n")


class ToolTests(unittest.TestCase):
    def test_pick_asset(self) -> None:
        names = [
            "cpython-3.11.0+20260101-x86_64-unknown-linux-gnu-install_only.tar.gz",
            "cpython-3.12.1+20260101-x86_64_v3-unknown-linux-gnu-install_only.tar.gz",
            "cpython-3.12.8+20260101-x86_64-unknown-linux-gnu-install_only.tar.gz",
            "cpython-3.16.0a1+20260101-x86_64-unknown-linux-gnu-install_only.tar.gz",
            "cpython-3.13.1+20260101-x86_64-pc-windows-msvc-install_only.tar.gz",
        ]
        assets = [{"name": name, "browser_download_url": "https://example.invalid/" + name} for name in names]
        picked = tools.pick_asset(assets, "x86_64-unknown-linux-gnu")
        self.assertIsNotNone(picked)
        assert picked is not None
        self.assertIn("3.12.8", picked["name"])

    def test_package_validation(self) -> None:
        self.assertEqual(tools.validate_package("pandas>=2"), "pandas>=2")
        self.assertIsNone(tools.validate_package("pandas; rm -rf /"))

    def test_icon_center_crop(self) -> None:
        width, height = 30, 10
        rows = []
        for y in range(height):
            row = bytearray()
            for x in range(width):
                color = (255, 0, 0, 255) if x == 15 and y == 5 else (0, 0, 255, 255)
                row.extend(color)
            rows.append(bytes(row))
        decoded = decode_png(encode_png(width, height, rows))
        self.assertIsNotNone(decoded)
        assert decoded is not None
        cropped = decode_png(crop_center_square(*decoded, out_size=8))
        self.assertIsNotNone(cropped)
        assert cropped is not None
        side_w, side_h, rgba = cropped
        self.assertEqual((side_w, side_h), (8, 8))
        center = ((4 * side_w) + 4) * 4
        self.assertGreater(rgba[center], 200)
        self.assertLess(rgba[center + 2], 40)
        self.assertTrue(generated_icon_png().startswith(b"\x89PNG"))
        shatu = icon_priority(Path("shatuide.jpg"))
        graphic = icon_priority(Path("grafik.png"))
        self.assertIsNotNone(shatu)
        self.assertIsNotNone(graphic)
        assert shatu is not None and graphic is not None
        self.assertLess(shatu, graphic)
        self.assertIsNone(icon_priority(Path("readme.md")))
        graphic = ROOT / "shatuide.png"
        self.assertTrue(graphic.is_file())
        decoded_icon = decode_png(graphic.read_bytes())
        self.assertIsNotNone(decoded_icon)
        assert decoded_icon is not None
        expected = crop_center_square(*decoded_icon)
        served, content_type = load_icon_bytes()
        self.assertEqual(content_type, "image/png")
        self.assertEqual(served, expected)
        self.assertEqual((ASSETS / "icon.png").read_bytes(), expected)


class HistoryHttpNotebookTests(unittest.TestCase):
    def test_history_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            history.snapshot(root, "a.py", "eins\n")
            history.snapshot(root, "a.py", "zwei\n")
            items = history.list_snapshots(root, "a.py")
            self.assertEqual(len(items), 2)
            self.assertIn("eins", history.read_snapshot(root, "a.py", items[1]["id"]))

    def test_http_file(self) -> None:
        parsed = http_client.parse_http_file("POST https://example.test/graphql\nContent-Type: application/json\n\n{\"query\": \"{ a }\"}\n")
        self.assertTrue(parsed["ok"])
        self.assertEqual(parsed["method"], "POST")
        self.assertIn("query", parsed["body"])

    def test_notebook(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "n.ipynb"
            notebook.save_notebook(path, [{"type": "code", "source": "print(1)\n"}])
            loaded = notebook.load_notebook(path)
            self.assertEqual(loaded["cells"][0]["source"], "print(1)\n")

    def test_agent_parser(self) -> None:
        parsed = ai.parse_agent_message('```json\n{"done": true, "message": "fertig"}\n```')
        self.assertTrue(parsed["ok"])
        self.assertTrue(parsed["done"])
        self.assertTrue(ai.extract_code("```python\nprint(1)\n```").startswith("print(1)"))
        self.assertEqual(ai.resolve_system_prompt("  Hallo  "), "Hallo")
        self.assertEqual(ai.resolve_system_prompt("   "), ai.CHAT_SYSTEM)
        self.assertEqual(ai.parse_models({"data": [{"id": "llama3.1"}, {"id": "llama3.1"}, "mistral"]}), ["llama3.1", "mistral"])
        self.assertEqual(ai.parse_models({"models": [{"name": "phi"}]}), ["phi"])


class RuntimeTests(unittest.TestCase):
    def test_fault_stops_on_syntax_and_exception(self) -> None:
        from shatuide.faults import locate_fault

        trace = (
            'Traceback (most recent call last):\n'
            '  File "/tmp/app.py", line 4, in <module>\n'
            '  File "/tmp/lib.py", line 2, in f\n'
            'ZeroDivisionError: division by zero\n'
        )
        found = locate_fault(trace, "/tmp/app.py")
        self.assertIsNotNone(found)
        assert found is not None
        self.assertEqual(found["line"], 4)
        self.assertEqual(found["file"], "/tmp/app.py")
        self.assertIn("ZeroDivisionError", found["message"])
        self.assertEqual(locate_fault("tool.sh: line 3: foo: command not found\n", "/tmp/tool.sh")["line"], 3)
        self.assertEqual(locate_fault("At C:\\a.ps1:5 char:1\n+ nope\n", "C:\\a.ps1")["line"], 5)
        modern = locate_fault("RuntimeException: C:\\a.ps1:5\nLine |\n   5 |  1 / 0\n", "C:\\a.ps1")
        self.assertEqual(modern["line"], 5)
        self.assertEqual(modern["file"], "C:\\a.ps1")
        colored = locate_fault(
            "\x1b[31;1mRuntimeException: \x1b[0m/tmp/app.ps1:2\x1b[0m\n",
            "/tmp/app.ps1",
        )
        self.assertEqual(colored["line"], 2)
        self.assertEqual(colored["file"], "/tmp/app.ps1")

        with tempfile.TemporaryDirectory() as tmp:
            broken = Path(tmp) / "kaputt.py"
            broken.write_text("def\n", encoding="utf-8")
            session = DebugSession()
            try:
                session.start(sys.executable, str(broken), tmp, [], Path(tmp) / "bp.json")
                event = session.wait_event("stopped", timeout=8)
                self.assertEqual(event["line"], 1)
                self.assertEqual(event["reason"], "exception")
                session.command({"cmd": "continue"})
                session.wait_event("terminated", timeout=8)
            finally:
                session.close()
            crash = Path(tmp) / "rechnung.py"
            crash.write_text("print(1)\nvalue = 1 / 0\n", encoding="utf-8")
            session = DebugSession()
            try:
                session.start(sys.executable, str(crash), tmp, [], Path(tmp) / "crash.json")
                event = session.wait_event("stopped", timeout=8)
                self.assertEqual(event["line"], 2)
                self.assertEqual(event["reason"], "exception")
                self.assertIn("ZeroDivision", event.get("exception") or "")
                session.command({"cmd": "continue"})
                session.wait_event("terminated", timeout=8)
            finally:
                session.close()

        from shatuide.shell_debug import PowerShellDebugSession, ShellDebugSession

        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "fehl.sh"
            script.write_text("echo start\nnosuchcommand\necho after\n", encoding="utf-8")
            session = ShellDebugSession()
            try:
                session.start(str(script), tmp, [], Path(tmp) / "sh-bp.json")
                stopped = session.wait_event("stopped", timeout=8)
                self.assertEqual(stopped["line"], 2, session.snapshot())
                self.assertEqual(stopped["reason"], "exception")
                session.command({"cmd": "continue"})
                session.wait_event("terminated", timeout=8)
            finally:
                session.close()
            from shatuide.scripting import powershell_binary

            if powershell_binary():
                ps_script = Path(tmp) / "fehl.ps1"
                ps_script.write_text('Write-Output "start"\n1 / 0\nWrite-Output "after"\n', encoding="utf-8")
                ps = PowerShellDebugSession()
                try:
                    ps.start(str(ps_script), tmp, [], Path(tmp) / "ps-bp.json")
                    stopped = ps.wait_event("stopped", timeout=12)
                    self.assertEqual(stopped["line"], 2, ps.snapshot())
                    self.assertEqual(stopped["reason"], "exception")
                    self.assertIn("zero", (stopped.get("exception") or "").lower())
                    ps.command({"cmd": "continue"})
                    ps.wait_event("terminated", timeout=12)
                finally:
                    ps.close()

    def test_compile_and_debug(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "t.py"
            script.write_text("x = 1\ny = x + 41\nprint(y)\n", encoding="utf-8")
            compiled = compile_file(str(script))
            self.assertTrue(compiled["ok"], compiled)
            session = DebugSession()
            try:
                session.start(
                    sys.executable,
                    str(script),
                    tmp,
                    [{"file": str(script.resolve()), "line": 2}],
                    Path(tmp) / "bp.json",
                )
                event = session.wait_event("stopped", timeout=8)
                self.assertEqual(event["line"], 2)
                self.assertIn("x", event["locals"])
                session.command({"cmd": "continue"})
                session.wait_event("terminated", timeout=8)
            finally:
                session.close()

    def test_kernel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kernel = KernelSession(sys.executable, tmp, Path(tmp) / "plots")
            try:
                result = kernel.execute("1 + 41")
                self.assertEqual(result.get("result"), "42", result)
                assigned = kernel.execute("wert = [1, 2, 3]\nwert")
                self.assertFalse(assigned.get("error"))
                names = {item["name"] for item in assigned.get("variables", [])}
                self.assertIn("wert", names)
            finally:
                kernel.close()


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.httpd, self.app = create_server("127.0.0.1", 0, self.tmp.name)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.httpd.server_address[:2]
        self.base = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.tmp.cleanup()

    def request(self, path: str, payload: dict | None = None, method: str | None = None) -> dict:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.base + path, data=data, method=method or ("POST" if payload is not None else "GET"))
        req.add_header("X-Shatu-Token", self.app.token)
        req.add_header("Host", "127.0.0.1")
        if payload is not None:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read()
            content_type = response.headers.get("Content-Type", "")
        if "json" not in content_type:
            return {"raw": body}
        return json.loads(body.decode("utf-8"))

    def test_browse_existing_files(self) -> None:
        folder = Path(self.tmp.name)
        (folder / "skript.py").write_text("print(1)\n", encoding="utf-8")
        (folder / "tool.sh").write_text("echo hi\n", encoding="utf-8")
        (folder / "daten.txt").write_text("hallo\n", encoding="utf-8")
        listed = self.request("/api/browse?path=" + urllib.parse.quote(str(folder)))
        names = {entry["name"] for entry in listed["entries"]}
        self.assertTrue({"skript.py", "tool.sh", "daten.txt"} <= names)
        self.assertEqual(listed["parent"], str(folder.resolve().parent))
        inside = self.request("/api/file?path=" + urllib.parse.quote(str(folder / "skript.py")))
        self.assertTrue(inside["writable"])
        other = Path(tempfile.mkdtemp())
        try:
            script = other / "fremd.py"
            script.write_text("wert = 7\n", encoding="utf-8")
            read = self.request("/api/file?path=" + urllib.parse.quote(str(script)))
            self.assertFalse(read["writable"])
            self.assertIn("wert = 7", read["content"])
        finally:
            script = other / "fremd.py"
            if script.exists():
                script.unlink()
            other.rmdir()

    def test_page_icon_and_run(self) -> None:
        page = urllib.request.urlopen(self.base + "/", timeout=10)
        html = page.read().decode("utf-8")
        self.assertIn("ShatuIDE", html)
        self.assertIn("shatu_session=", page.headers.get("Set-Cookie", ""))
        icon = self.request("/api/icon")
        self.assertTrue(icon["raw"].startswith(b"\x89PNG"))
        script = Path(self.tmp.name) / "hallo.py"
        written = self.request("/api/file", {"path": str(script), "content": "print(12345)\n"})
        self.assertTrue(written["ok"])
        read = self.request("/api/file?path=" + urllib.parse.quote(str(script)))
        self.assertIn("12345", read["content"])
        outside = Path(self.tmp.name).parent / ("shatu-ausserhalb-" + os.path.basename(self.tmp.name))
        outside_req = self._raw_post("/api/file", {"path": str(outside), "content": "nein"})
        self.assertEqual(outside_req.status, 403)
        started = self.request("/api/run", {"mode": "file", "path": str(script)})
        seen = ""
        code = None
        for _ in range(40):
            state = self.request(f"/api/session?id={started['id']}&from=0")
            seen = "".join(state["lines"])
            if not state["running"]:
                code = state["code"]
                break
            import time
            time.sleep(0.1)
        self.assertEqual(code, 0)
        self.assertIn("12345", seen)
        analyzed = self.request("/api/analyze", {"path": str(script), "content": "import sys\nprint(sys.version)\n"})
        self.assertTrue(analyzed["ok"])
        renamed = self.request("/api/rename", {"content": "def add(x):\n    return add(x)\n", "old": "add", "new": "plus"})
        self.assertIn("def plus", renamed["content"])

    def _raw_post(self, path: str, payload: dict):
        req = urllib.request.Request(
            self.base + path,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
        )
        req.add_header("X-Shatu-Token", self.app.token)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return response
        except urllib.error.HTTPError as exc:
            return exc

    def test_ai_connect_prompt(self) -> None:
        cfg_path = Path.home() / ".shatuide" / "config.json"
        backup = cfg_path.read_bytes() if cfg_path.is_file() else None
        seen: dict = {}

        class ModelHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                seen["auth"] = self.headers.get("Authorization")
                self._write({"data": [{"id": "demo"}, {"id": "anderes"}]})

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", "0") or 0)
                seen["body"] = json.loads(self.rfile.read(length).decode("utf-8"))
                self._write({"choices": [{"message": {"content": "pong"}}]})

            def _write(self, payload: dict) -> None:
                raw = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def log_message(self, format: str, *args) -> None:  # noqa: A003
                return

        model = ThreadingHTTPServer(("127.0.0.1", 0), ModelHandler)
        thread = threading.Thread(target=model.serve_forever, daemon=True)
        thread.start()
        port = model.server_address[1]
        try:
            saved = self.request(
                "/api/ai/config",
                {
                    "base_url": f"http://127.0.0.1:{port}/v1",
                    "model": "demo",
                    "system_prompt": "Systemtext speziell",
                    "prompt": "Hallo Modell",
                    "api_key": "geheim",
                },
            )
            self.assertTrue(saved["ok"])
            self.assertEqual(saved["system_prompt"], "Systemtext speziell")
            self.assertEqual(saved["api_key"], "••••••••")
            self.assertTrue(saved["reply"]["ok"])
            self.assertEqual(saved["reply"]["content"], "pong")
            messages = seen["body"]["messages"]
            self.assertEqual(messages[0]["content"], "Systemtext speziell")
            self.assertEqual(messages[-1]["content"], "Hallo Modell")
            self.assertEqual(seen["body"]["model"], "demo")
            self.assertEqual(seen["body"].get("model"), "demo")
            loaded = self.request("/api/ai/config")
            self.assertEqual(loaded["system_prompt"], "Systemtext speziell")
            self.assertNotIn("geheim", json.dumps(loaded))
            listed = self.request("/api/ai/models", {"base_url": f"http://127.0.0.1:{port}/v1", "api_key": "••••••••"})
            self.assertEqual(listed["models"], ["demo", "anderes"])
            self.assertEqual(seen.get("auth"), "Bearer geheim")
            agent = self.app.run_agent("mach etwas", lambda _message: None)
            self.assertFalse(agent["ok"])
            system = seen["body"]["messages"][0]["content"]
            self.assertIn("Zusätzliche Anweisung", system)
            self.assertIn("Systemtext speziell", system)
            self.assertIn("JSON", system)
            refused = self.request(
                "/api/ai/config",
                {"base_url": "http://127.0.0.1:9/v1", "model": "keins", "system_prompt": "", "prompt": "Hallo Modell"},
            )
            self.assertTrue(refused["ok"])
            self.assertFalse(refused["reply"]["ok"])
            self.assertTrue(refused["reply"]["error"])
        finally:
            model.shutdown()
            model.server_close()
            if backup is None:
                cfg_path.unlink(missing_ok=True)
            else:
                cfg_path.write_bytes(backup)
                os.chmod(cfg_path, 0o600)

    def test_github_editor_profile(self) -> None:
        self.assertEqual(integrations.provider_by_id("kimi")["base_url"], "https://api.moonshot.ai/v1")
        names = [item["name"] for item in integrations.EXTENSIONS]
        for expected in (
            "Kimi Code",
            "GitHub Copilot",
            "Tabnine",
            "Bito AI",
            "Mintlify Doc Writer",
            "Code GPT",
            "Windsurf (Codeium)",
            "Qodo Gen",
            "Google Gemini Code Assist",
        ):
            self.assertIn(expected, names)
        self.assertIn("moonshot-ai.kimi-code", integrations.marketplace_ids(["kimi", "copilot"]))
        self.assertTrue(integrations.github_host("https://github.com/kickmetox/hello-github.git"))
        self.assertFalse(integrations.github_host("https://gitlab.com/gruppe/projekt.git"))
        env = integrations.with_github_auth({"A": "1"}, "ghp_testtoken", ["https://github.com/a/b.git"])
        self.assertIn("AUTHORIZATION: bearer ghp_testtoken", env["GIT_CONFIG_VALUE_0"])
        untouched = integrations.with_github_auth({}, "ghp_testtoken", ["https://gitlab.com/a/b.git"])
        self.assertNotIn("GIT_CONFIG_VALUE_0", untouched)
        cfg_path = Path.home() / ".shatuide" / "config.json"
        backup = cfg_path.read_bytes() if cfg_path.is_file() else None
        try:
            rejected = self.request("/api/ai/config", {"github_token": "nicht gültig"})
            self.assertFalse(rejected["ok"])
            saved = self.request(
                "/api/ai/config",
                {
                    "provider": "kimi",
                    "base_url": "",
                    "model": "",
                    "system_prompt": "Antworte knapp.",
                    "github_token": "ghp_testtoken",
                    "extensions": ["kimi", "copilot", "unbekannt"],
                    "editor_visualstudio": r"C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\devenv.exe",
                },
            )
            self.assertTrue(saved["ok"], saved)
            self.assertEqual(saved["base_url"], "https://api.moonshot.ai/v1")
            self.assertEqual(saved["model"], "kimi-k3")
            self.assertEqual(saved["github_token"], "••••••••")
            self.assertEqual(saved["extensions"], ["kimi", "copilot"])
            self.assertNotIn("ghp_testtoken", json.dumps(saved))
            written = self.request("/api/editors", {"action": "write", "extensions": ["kimi", "copilot"]})
            self.assertTrue(written["ok"], written)
            folder = Path(self.tmp.name) / ".vscode"
            text = (folder / "extensions.json").read_text(encoding="utf-8")
            profile = (folder / "shatuide.ai.json").read_text(encoding="utf-8")
            self.assertIn("moonshot-ai.kimi-code", text)
            self.assertIn("GitHub.copilot-chat", text)
            self.assertIn("Antworte knapp.", profile)
            self.assertNotIn("ghp_testtoken", text + profile)
            loaded = self.request("/api/ai/config")
            self.assertEqual(loaded["extension_catalog"][0]["id"], "kimi")
            self.assertTrue(loaded["editors"]["visualstudio"]["configured"].endswith("devenv.exe"))
        finally:
            if backup is None:
                cfg_path.unlink(missing_ok=True)
            else:
                cfg_path.write_bytes(backup)
                os.chmod(cfg_path, 0o600)


class ScriptEditTests(unittest.TestCase):
    def test_replace_keeps_files_outside_the_workspace(self) -> None:
        from shatuide.edit import replace_project

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "probe.py").write_text("wert = 1\nwertig = 2\n", encoding="utf-8")
            (root / "tool.sh").write_text("echo wert\n", encoding="utf-8")
            other = Path(tempfile.mkdtemp())
            try:
                outside = other / "fremd.py"
                outside.write_text("wert = 1\n", encoding="utf-8")
                preview = replace_project(root, "wert", "zahl", word=True, preview=True)
                self.assertTrue(preview["ok"], preview)
                self.assertEqual(preview["replacements"], 2)
                self.assertEqual(outside.read_text(encoding="utf-8"), "wert = 1\n")
                applied = replace_project(root, "wert", "zahl", word=True, preview=False)
                self.assertEqual(applied["replacements"], 2)
                self.assertEqual((root / "probe.py").read_text(encoding="utf-8"), "zahl = 1\nwertig = 2\n")
                self.assertEqual((root / "tool.sh").read_text(encoding="utf-8"), "echo zahl\n")
                self.assertEqual(outside.read_text(encoding="utf-8"), "wert = 1\n")
                broken = replace_project(root, "(", "x", regex=True)
                self.assertFalse(broken["ok"])
            finally:
                outside.unlink(missing_ok=True)
                other.rmdir()

    def test_shell_syntax_run_and_debug(self) -> None:
        from shatuide.scripting import syntax_check
        from shatuide.shell_debug import ShellDebugSession

        self.assertTrue(syntax_check("a.sh", "echo ok\n")["ok"])
        broken = syntax_check("a.sh", "if\n")
        self.assertFalse(broken["ok"])
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "tool.sh"
            script.write_text("echo start\nx=7\necho mid\necho end\n", encoding="utf-8")
            httpd, app = create_server("127.0.0.1", 0, tmp)
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            host, port = httpd.server_address[:2]
            base = f"http://{host}:{port}"
            try:
                payload = json.dumps({"mode": "file", "path": str(script)}).encode("utf-8")
                req = urllib.request.Request(base + "/api/run", data=payload, method="POST")
                req.add_header("X-Shatu-Token", app.token)
                req.add_header("Host", "127.0.0.1")
                req.add_header("Content-Type", "application/json")
                with urllib.request.urlopen(req, timeout=20) as response:
                    started = json.loads(response.read().decode("utf-8"))
                self.assertTrue(started["ok"], started)
                text = ""
                idle = 0
                body = {}
                for _ in range(40):
                    poll = urllib.request.Request(base + f"/api/session?id={started['id']}&from=0")
                    poll.add_header("X-Shatu-Token", app.token)
                    poll.add_header("Host", "127.0.0.1")
                    with urllib.request.urlopen(poll, timeout=20) as response:
                        body = json.loads(response.read().decode("utf-8"))
                    text = "".join(body.get("lines") or [])
                    if body.get("running"):
                        idle = 0
                    else:
                        idle += 1
                        if text and idle >= 2:
                            break
                    time.sleep(0.05)
                self.assertIn("start", text, body)
                self.assertIn("mid", text)
                session = ShellDebugSession()
                try:
                    session.start(str(script), tmp, [{"file": str(script), "line": 3}], Path(tmp) / "bp.json")
                    stopped = session.wait_event("stopped", timeout=8)
                    self.assertEqual(stopped["line"], 3)
                    self.assertEqual(stopped["locals"].get("x"), "7")
                    session.command({"cmd": "eval", "expr": "printf %s \"$x\""})
                    evaluated = self._wait_eval(session)
                    self.assertIn("7", evaluated.get("value", ""))
                    session.command({"cmd": "step"})
                    stepped = self._wait_line(session, 4)
                    self.assertEqual(stepped["line"], 4)
                    session.command({"cmd": "continue"})
                    session.wait_event("terminated", timeout=8)
                finally:
                    session.close()
            finally:
                httpd.shutdown()
                httpd.server_close()

    def test_powershell_syntax_and_debug(self) -> None:
        import shutil
        from unittest.mock import patch

        from shatuide.scripting import syntax_check
        from shatuide.shell_debug import PowerShellDebugSession

        with patch("shatuide.scripting.powershell_binary", return_value=None):
            missing = syntax_check("a.ps1", "Write-Output 1\n")
        self.assertFalse(missing["ok"])
        self.assertIn("PowerShell", missing["error"])
        portable = Path.home() / "pwsh" / "pwsh"
        if not shutil.which("pwsh") and not shutil.which("powershell") and portable.is_file():
            os.environ["PATH"] = str(portable.parent) + os.pathsep + os.environ.get("PATH", "")
        if not shutil.which("pwsh") and not shutil.which("powershell"):
            return
        checked = syntax_check("a.ps1", "Write-Output 1\n")
        self.assertTrue(checked["ok"], checked)
        broken = syntax_check("a.ps1", "function {\n")
        self.assertFalse(broken["ok"])
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "tool.ps1"
            script.write_text('$x = 7\nWrite-Output "start"\nWrite-Output "end"\n', encoding="utf-8")
            session = PowerShellDebugSession()
            try:
                session.start(str(script), tmp, [{"file": str(script), "line": 2}], Path(tmp) / "bp.json")
                stopped = session.wait_event("stopped", timeout=8)
                self.assertEqual(stopped["line"], 2, session.snapshot())
                self.assertEqual(stopped["locals"].get("x"), "7")
                session.command({"cmd": "step"})
                stepped = self._wait_line(session, 3)
                self.assertEqual(stepped["line"], 3)
                session.command({"cmd": "continue"})
                session.wait_event("terminated", timeout=8)
                output = "".join(session.snapshot()["output"])
                self.assertIn("start", output)
                self.assertIn("end", output)
            finally:
                session.close()

    def test_probe_symbol_and_section(self) -> None:
        import subprocess

        from shatuide.probe import prepare

        source = "\n".join(
            [
                "def wert():",
                "    return 41 + 1",
                "",
                "def add(a, b=1):",
                '    """',
                "    >>> add(2)",
                "    3",
                '    """',
                "    return a + b",
                "",
                "def test_add():",
                "    assert add(2) == 3",
                "",
                "import unittest",
                "class Suite(unittest.TestCase):",
                "    def test_one(self):",
                "        self.assertEqual(add(2, 2), 4)",
                "",
            ]
        )

        def line_of(snippet: str) -> int:
            return source.splitlines().index(snippet) + 1

        def execute(code: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)

        wert = prepare(source, "t.py", line_of("    return 41 + 1"), line_of("    return 41 + 1"), "", "function")
        self.assertEqual(wert["title"], "Funktion wert")
        self.assertIn("42", execute(wert["code"]).stdout)
        documented = prepare(source, "t.py", line_of("    return a + b"), line_of("    return a + b"), "", "function")
        self.assertIn("Doctest", documented["detail"])
        self.assertEqual(execute(documented["code"]).returncode, 0)
        tested = prepare(source, "t.py", line_of("    assert add(2) == 3"), line_of("    assert add(2) == 3"), "", "function")
        self.assertIn("test_add", tested["code"])
        self.assertEqual(execute(tested["code"]).returncode, 0)
        method = prepare(source, "t.py", line_of("        self.assertEqual(add(2, 2), 4)"), 1, "", "function")
        self.assertEqual(method["title"], "Methode Suite.test_one")
        self.assertEqual(execute(method["code"]).returncode, 0)
        marked = prepare("print(1)\n", "t.py", 1, 1, "print('zeile-ok')\n", "mark")
        self.assertEqual(marked["kind"], "line")
        self.assertIn("zeile-ok", execute(marked["code"]).stdout)
        shell = prepare("greet() {\n  echo hi\n}\n", "a.sh", 2, 2, "", "function")
        self.assertEqual(shell["title"], "Funktion greet")
        shell_run = subprocess.run(["bash", "-c", shell["code"]], capture_output=True, text=True)
        self.assertIn("hi", shell_run.stdout)
        broken = prepare('{"a": 1,}\n', "a.json", 1, 1, "", "mark")
        self.assertEqual(broken["mode"], "check")
        with tempfile.TemporaryDirectory() as tmp:
            httpd, app = create_server("127.0.0.1", 0, tmp)
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            host, port = httpd.server_address[:2]
            base = f"http://{host}:{port}"
            try:
                page = urllib.request.Request(base + "/probe")
                page.add_header("Host", "127.0.0.1")
                with urllib.request.urlopen(page, timeout=10) as response:
                    html = response.read().decode("utf-8")
                self.assertIn("Testfenster", html)
                payload = json.dumps(
                    {"content": source, "path": "t.py", "start": line_of("    return 41 + 1"), "end": 2, "selected": "", "scope": "function"}
                ).encode("utf-8")
                req = urllib.request.Request(base + "/api/probe", data=payload, method="POST")
                req.add_header("X-Shatu-Token", app.token)
                req.add_header("Host", "127.0.0.1")
                req.add_header("Content-Type", "application/json")
                with urllib.request.urlopen(req, timeout=10) as response:
                    body = json.loads(response.read().decode("utf-8"))
                self.assertTrue(body["ok"], body)
                self.assertEqual(body["title"], "Funktion wert")
            finally:
                httpd.shutdown()
                httpd.server_close()

    def test_json_check_format_and_outline(self) -> None:
        from shatuide.scripting import format_json, json_outline, json_problems, language_of, run_argv, syntax_check
        from shatuide.server import App

        self.assertEqual(language_of("daten.json"), "json")
        self.assertTrue(syntax_check("daten.json", '{"name": "Shatu", "ok": true}\n')["ok"])
        broken = syntax_check("daten.json", '{\n  "name":\n}\n')
        self.assertFalse(broken["ok"])
        self.assertIn("Zeile", broken["error"])
        self.assertEqual(json_problems('{"a": 1}\n'), [])
        problems = json_problems("{")
        self.assertEqual(problems[0]["code"], "JSON")
        self.assertGreaterEqual(problems[0]["line"], 1)
        outline = json_outline('{\n  "titel": 1,\n  "werte": [1]\n}\n')
        self.assertEqual([item["name"] for item in outline], ["titel", "werte"])
        self.assertEqual(outline[0]["line"], 2)
        pretty = format_json('{"b":1,"a":[true,null]}')
        self.assertEqual(pretty["tool"], "json")
        self.assertIn('"a": [\n    true,\n    null\n  ]', pretty["content"])
        self.assertTrue(pretty["content"].endswith("\n"))
        with self.assertRaises(RuntimeError):
            run_argv("daten.json", sys.executable)
        with tempfile.TemporaryDirectory() as tmp:
            app = App(tmp)
            analyzed = app.analyze("{", str(Path(tmp) / "daten.json"))
            self.assertEqual(analyzed["problems"][0]["code"], "JSON")
            self.assertEqual(analyzed["outline"], [])

    def test_script_outline_not_python_lint(self) -> None:
        from shatuide.scripting import script_outline
        from shatuide.server import App

        source = "function Get-Wert {\n    param($Name)\n    return $Name\n}\nfunction Set-Wert {\n    $global:x = 1\n}\n"
        items = script_outline(source, "tool.ps1")
        self.assertEqual([item["name"] for item in items], ["Get-Wert", "Set-Wert"])
        self.assertEqual(items[0]["line"], 1)
        self.assertEqual(items[0]["end_line"], 4)
        self.assertEqual(items[0]["kind"], "function")
        self.assertIn("Name", items[0]["params"])
        shell = script_outline("hallo() {\n  echo hi\n}\n", "a.sh")
        self.assertEqual(shell[0]["name"], "hallo")
        self.assertEqual(shell[0]["end_line"], 3)
        labels = script_outline("@echo off\n:start\necho hi\n", "a.bat")
        self.assertEqual(labels[0]["name"], "start")
        self.assertEqual(labels[0]["kind"], "label")
        with tempfile.TemporaryDirectory() as tmp:
            app = App(tmp)
            analyzed = app.analyze("function Get-Wert {\n  1 +\n}\n", str(Path(tmp) / "a.ps1"))
            self.assertEqual(analyzed["outline"][0]["name"], "Get-Wert")
            self.assertEqual(analyzed["outline"][0]["line"], 1)
            self.assertFalse(any(item.get("code") == "E999" for item in analyzed["problems"]))

    def test_html_outline_format_and_check(self) -> None:
        from shatuide.probe import prepare
        from shatuide.scripting import format_html, html_fragment, html_outline, html_problems, language_of, run_argv, syntax_check
        from shatuide.server import App

        self.assertEqual(language_of("seite.html"), "html")
        self.assertEqual(language_of("seite.htm"), "html")
        source = "<html><body><h1 id=\"titel\">Hallo</h1><div id=\"haupt\"><script>\nfunction hallo() {\n  return 1;\n}\n</script></div></body></html>\n"
        names = [item["name"] for item in html_outline(source)]
        self.assertEqual(names, ["h1#titel Hallo", "div#haupt", "hallo"])
        self.assertEqual(html_outline(source)[2]["kind"], "function")
        self.assertEqual(html_outline(source)[2]["line"], 2)
        self.assertEqual(html_problems("<div><p>x</div>\n"), [])
        broken = html_problems("<div><span></div>\n")
        self.assertEqual(broken[0]["code"], "HTML")
        self.assertEqual(broken[0]["line"], 1)
        self.assertIn("span", broken[0]["message"])
        unclosed = html_problems("<div>\n<p>x</p>\n")
        self.assertEqual(unclosed[0]["line"], 1)
        self.assertIn("div", unclosed[0]["message"])
        self.assertTrue(syntax_check("seite.html", "<div></div>\n")["ok"])
        failed = syntax_check("seite.html", "<div>")
        self.assertFalse(failed["ok"])
        self.assertIn("Zeile 1", failed["error"])
        pretty = format_html("<html><body><h1>Titel</h1></body></html>")
        self.assertTrue(pretty["ok"], pretty)
        self.assertIn("\n    <h1>\n      Titel\n    </h1>\n", pretty["content"])
        self.assertTrue(pretty["content"].endswith("\n"))
        kept = format_html("<script>\nfunction hallo() {\n  return 1;\n}\n</script>\n")
        self.assertIn("function hallo() {\n  return 1;\n}", kept["content"])
        refused = format_html("<div></span>")
        self.assertFalse(refused["ok"])
        self.assertIn("Zeile", refused["error"])
        with self.assertRaises(RuntimeError):
            run_argv("seite.html", sys.executable)
        fragment = html_fragment(source, 2)
        self.assertTrue(fragment.startswith("<script>"), fragment)
        self.assertIn("function hallo", fragment)
        self.assertTrue(fragment.strip().endswith("</script>"))
        probed = prepare(source, "seite.html", 2, 2, "", "function")
        self.assertEqual(probed["mode"], "check")
        self.assertEqual(probed["language"], "html")
        with tempfile.TemporaryDirectory() as tmp:
            app = App(tmp)
            analyzed = app.analyze(source, str(Path(tmp) / "seite.html"))
            self.assertEqual([item["name"] for item in analyzed["outline"]], names)
            self.assertFalse(any(item.get("code") == "E999" for item in analyzed["problems"]))

    def _wait_line(self, session, line: int, timeout: float = 8):
        import time as time_mod

        deadline = time_mod.time() + timeout
        while time_mod.time() < deadline:
            paused = session.snapshot().get("paused")
            if paused and paused.get("line") == line:
                return paused
            time_mod.sleep(0.05)
        self.fail(session.snapshot())

    def _wait_eval(self, session, timeout: float = 8):
        import time as time_mod

        deadline = time_mod.time() + timeout
        while time_mod.time() < deadline:
            for event in session.snapshot()["events"]:
                if event.get("event") == "eval":
                    return event
            time_mod.sleep(0.05)
        self.fail(session.snapshot())


class StudioTests(unittest.TestCase):
    def test_format_function_module_gui_and_service(self) -> None:
        from shatuide.studio import advanced_function, build_module, format_script, gui_script, service_sources

        formatted = format_script("powershell", "function A {\nif ($true) {\nWrite-Output 1\n}\n}\n")
        self.assertIn("    Write-Output 1", formatted["content"])
        self.assertEqual(formatted["tool"], "shatu")
        shell = format_script("shell", "if true; then\necho hi\nfi\n")
        self.assertIn("    echo hi", shell["content"])
        function = advanced_function({
            "name": "Get-Wert",
            "synopsis": "Liefert eine Zahl",
            "parameters": [{"name": "Wert", "type": "int", "mandatory": True, "help": "Die Zahl"}],
            "output": "int",
        })
        self.assertIn("[CmdletBinding()]", function)
        self.assertIn("[int]$Wert", function)
        self.assertIn(".PARAMETER Wert", function)
        module = build_module(function, "Werkzeug", "1.2.0")
        self.assertTrue(module["ok"], module)
        self.assertEqual(module["functions"], ["Get-Wert"])
        self.assertIn("FunctionsToExport = @('Get-Wert')", module["psd1"])
        help_only = "<#\n.NAME\nGet-Hinweis\n.SYNOPSIS\nKurz\n#>\n"
        from_help = build_module(help_only, "Hinweis")
        self.assertEqual(from_help["functions"], ["Get-Hinweis"])
        gui = gui_script("Werkzeug", [{"kind": "button", "name": "btnOk", "text": "OK", "x": 10, "y": 12, "w": 80, "h": 24}], "powershell")
        self.assertIn("System.Windows.Forms.Button", gui["content"])
        self.assertIn("$btnOk", gui["content"])
        python_gui = gui_script("Werkzeug", [{"kind": "label", "name": "lbl", "text": "Hallo", "x": 1, "y": 2, "w": 40, "h": 20}], "python")
        self.assertIn("tk.Label", python_gui["content"])
        service = service_sources("LagerDienst", "Nachtlauf")
        install = "\n".join(service["files"].values())
        self.assertIn("New-Service", install)
        self.assertIn("LagerDienst", install)
        self.assertIn("stop.flag", install)

    def test_exe_msi_measure_recovery_and_remote(self) -> None:
        import shutil
        import subprocess

        from shatuide.studio import (
            build_msi,
            compile_exe,
            measure_invocation,
            recovery_read,
            recovery_store,
            remote_powershell,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            native = compile_exe(root, "echo shatu-exe-ok\n", "shell", "Hallo", target="native")
            self.assertTrue(native["ok"], native)
            proc = subprocess.run([native["path"]], capture_output=True, text=True, timeout=20)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("shatu-exe-ok", proc.stdout)
            if shutil.which("x86_64-w64-mingw32-gcc"):
                windows = compile_exe(root, "Write-Output shatu-win\n", "powershell", "Fenster", target="windows")
                self.assertTrue(windows["ok"], windows)
                self.assertTrue(Path(windows["path"]).read_bytes().startswith(b"MZ"))
            payload = root / "liesmich.txt"
            payload.write_text("installer-ok", encoding="utf-8")
            nested = root / "static"
            nested.mkdir()
            (nested / "app.js").write_text("js-ok", encoding="utf-8")
            package = build_msi(root, "Paket", "1.0.0", "ShatuIDE", [payload, nested / "app.js"])
            if shutil.which("msibuild") and shutil.which("gcab"):
                self.assertTrue(package["ok"], package)
                self.assertTrue(Path(package["wxs"]).is_file())
                out = root / "entpackt"
                out.mkdir()
                extracted = subprocess.run(["msiextract", "-C", str(out), package["path"]], capture_output=True, text=True)
                self.assertEqual(extracted.returncode, 0, extracted.stderr)
                self.assertEqual(next(out.rglob("liesmich.txt")).read_text(encoding="utf-8"), "installer-ok")
                script = next(out.rglob("app.js"))
                self.assertEqual(script.read_text(encoding="utf-8"), "js-ok")
                self.assertEqual(script.parent.name, "static")
                if shutil.which("msiinfo"):
                    ui = subprocess.run(["msiinfo", "export", package["path"], "InstallUISequence"], capture_output=True, text=True)
                    self.assertEqual(ui.returncode, 0, ui.stderr)
                    order = {}
                    for line in ui.stdout.splitlines()[3:]:
                        if not line.strip():
                            continue
                        cols = line.split("\t")
                        order[cols[0]] = int(cols[2])
                    self.assertLess(order["WelcomeDlg"], order["ExecuteAction"])
                    self.assertLess(order["ExecuteAction"], order["ExitOk"])
                    self.assertIn("MaintainDlg", order)
                    controls = subprocess.run(["msiinfo", "export", package["path"], "Control"], capture_output=True, text=True)
                    self.assertIn("Installieren", controls.stdout)
                    self.assertIn("Abbrechen", controls.stdout)
                    self.assertIn("Fertig", controls.stdout)
                    self.assertNotIn("Desktop", controls.stdout)
                    upgrade = subprocess.run(["msiinfo", "export", package["path"], "Upgrade"], capture_output=True, text=True)
                    self.assertIn("OLDERFOUND", upgrade.stdout)
                    execute = subprocess.run(["msiinfo", "export", package["path"], "InstallExecuteSequence"], capture_output=True, text=True)
                    self.assertIn("RemoveExistingProducts", execute.stdout)
            else:
                self.assertFalse(package["ok"])
                self.assertIn("wxs", package)
            script = root / "mess.py"
            script.write_text("print('mess-ok')\n", encoding="utf-8")
            plan = measure_invocation("python", str(script), sys.executable, root / "tmp")
            measured = subprocess.run(plan["argv"], capture_output=True, text=True, timeout=20)
            self.assertIn("SHATU_MEASURE", measured.stdout)
            self.assertIn("mess-ok", measured.stdout)
            stored = recovery_store(root, str(script), "print('neu')\n")
            self.assertEqual(recovery_read(root, stored["id"])["content"], "print('neu')\n")
            bad = remote_powershell("ssh", "bad host", "Write-Output 1", "user")
            self.assertFalse(bad["ok"])
            local = remote_powershell("local", "", "Write-Output shatu-remote-ok", "")
            if local.get("ok"):
                remote = subprocess.run(local["argv"], capture_output=True, text=True, timeout=30)
                self.assertIn("shatu-remote-ok", remote.stdout)

    def test_release_exe_and_installer(self) -> None:
        import shutil
        import subprocess

        from shatuide.release import build_release

        with tempfile.TemporaryDirectory() as tmp:
            built = build_release(Path(__file__).resolve().parent.parent, Path(tmp), bundle_python=False)
            self.assertTrue(built["ok"], built)
            exe = Path(built["exe"])
            exe_bytes = exe.read_bytes()
            self.assertTrue(exe_bytes.startswith(b"MZ"))
            self.assertIn(b"\x89PNG", exe_bytes)
            msi = Path(built["msi"])
            self.assertTrue(msi.is_file())
            self.assertGreater(msi.stat().st_size, 1000)
            if shutil.which("msiextract"):
                out = Path(tmp) / "entpackt"
                out.mkdir()
                extracted = subprocess.run(["msiextract", "-C", str(out), str(msi)], capture_output=True, text=True)
                self.assertEqual(extracted.returncode, 0, extracted.stderr)
                self.assertTrue(any(path.name == "shatuide.py" for path in out.rglob("shatuide.py")))
                page = next(path for path in out.rglob("app.js") if path.parent.name == "static")
                self.assertIn("ShatuIDE", page.read_text(encoding="utf-8"))
                self.assertTrue(any(path.name == "ShatuIDE.exe" for path in out.rglob("ShatuIDE.exe")))
            if shutil.which("msiinfo"):
                exported = subprocess.run(["msiinfo", "export", str(msi), "File"], capture_output=True, text=True)
                self.assertEqual(exported.returncode, 0, exported.stderr)
                rows = [line.split("\t") for line in exported.stdout.splitlines()[3:] if line.strip()]
                self.assertTrue(rows)
                self.assertTrue(all(row[6] == "16896" for row in rows), rows[0])
                components = subprocess.run(["msiinfo", "export", str(msi), "Component"], capture_output=True, text=True)
                self.assertEqual(components.returncode, 0, components.stderr)
                component_rows = [line.split("\t") for line in components.stdout.splitlines()[3:] if line.strip()]
                self.assertTrue(all(row[3] == "256" for row in component_rows))
                shortcuts = subprocess.run(["msiinfo", "export", str(msi), "Shortcut"], capture_output=True, text=True)
                self.assertEqual(shortcuts.returncode, 0, shortcuts.stderr)
                self.assertIn("DesktopFolder", shortcuts.stdout)
                self.assertIn("ProgramMenuFolder", shortcuts.stdout)
                self.assertIn("[#fil", shortcuts.stdout)
                controls = subprocess.run(["msiinfo", "export", str(msi), "Control"], capture_output=True, text=True)
                self.assertEqual(controls.returncode, 0, controls.stderr)
                self.assertIn("Installieren", controls.stdout)
                self.assertIn("Desktop", controls.stdout)
                self.assertIn("blauer Balken", controls.stdout)
                ui = subprocess.run(["msiinfo", "export", str(msi), "InstallUISequence"], capture_output=True, text=True)
                self.assertIn("WelcomeDlg", ui.stdout)
                self.assertIn("ExitOk", ui.stdout)

    def test_debug_other_file(self) -> None:
        from shatuide.shell_debug import ShellDebugSession

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            lib = folder / "lib.sh"
            lib.write_text("echo lib\nx=9\necho libend\n", encoding="utf-8")
            script = folder / "tool.sh"
            script.write_text(
                'echo start\nsource "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"\necho end\n',
                encoding="utf-8",
            )
            session = ShellDebugSession()
            try:
                session.start(str(script), tmp, [{"file": str(lib), "line": 2}], folder / "bp.json")
                stopped = session.wait_event("stopped", timeout=8)
                self.assertEqual(stopped["line"], 2)
                self.assertTrue(str(stopped["file"]).endswith("lib.sh"), stopped)
                session.command({"cmd": "step"})
                deadline = time.time() + 8
                stepped = None
                while time.time() < deadline:
                    paused = session.snapshot().get("paused")
                    if paused and paused.get("line") == 3:
                        stepped = paused
                        break
                    time.sleep(0.05)
                self.assertIsNotNone(stepped, session.snapshot())
                session.command({"cmd": "continue"})
                session.wait_event("terminated", timeout=8)
            finally:
                session.close()
            module = folder / "lib.ps1"
            module.write_text("$x = 9\nWrite-Output $x\n", encoding="utf-8")
            entry = folder / "main.ps1"
            entry.write_text('. "$PSScriptRoot/lib.ps1"\n', encoding="utf-8")
            from shatuide.scripting import powershell_binary
            from shatuide.shell_debug import PowerShellDebugSession

            if not powershell_binary():
                return
            ps = PowerShellDebugSession()
            try:
                ps.start(str(entry), tmp, [{"file": str(module), "line": 1}], folder / "ps-bp.json")
                stopped = ps.wait_event("stopped", timeout=12)
                self.assertEqual(stopped["line"], 1)
                self.assertTrue(str(stopped["file"]).endswith("lib.ps1"), stopped)
                ps.command({"cmd": "continue"})
                ps.wait_event("terminated", timeout=12)
            finally:
                ps.close()


class CreatorTests(unittest.TestCase):
    def test_script_from_questions_and_prompt(self) -> None:
        import subprocess

        from shatuide.creator import build_script, extract_script, infer_action, model_messages, script_from_model

        self.assertEqual(infer_action("Bitte addiere zwei Zahlen"), "sum")
        self.assertEqual(infer_action("Zeige den Ordner"), "list")
        self.assertEqual(infer_action("Beschreibung der Lage"), "print")
        greeted = build_script({
            "language": "python",
            "name": "Gruss",
            "action": "print",
            "purpose": "Begrüßt eine Person",
            "questions": "Name: Wie heißt du",
        })
        self.assertTrue(greeted["ok"], greeted)
        proc = subprocess.run([sys.executable, "-c", greeted["content"]], input="Ada\n", text=True, capture_output=True, timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Ada", proc.stdout)
        summed = build_script({"language": "python", "name": "Plus", "purpose": "Addiere zwei Zahlen"})
        self.assertEqual(summed["action"], "sum")
        proc = subprocess.run([sys.executable, "-c", summed["content"]], input="2\n3\n", text=True, capture_output=True, timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("5", proc.stdout)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "a.txt").write_text("x", encoding="utf-8")
            listed = build_script({"language": "python", "name": "Ordner", "action": "list", "questions": "Pfad: Ordner"})
            proc = subprocess.run([sys.executable, "-c", listed["content"]], input=tmp + "\n", text=True, capture_output=True, timeout=10)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("a.txt", proc.stdout)
            shell = build_script({"prompt": "Sprache: shell\nName: Liste\nAktion: list\nFrage: Pfad: Welcher Ordner?\nZeige den Ordner"})
            self.assertEqual(shell["language"], "shell")
            self.assertIn("read -r", shell["content"])
            script = Path(tmp) / "liste.sh"
            script.write_text(shell["content"], encoding="utf-8")
            proc = subprocess.run(["bash", str(script)], input=tmp + "\n", text=True, capture_output=True, timeout=10)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("a.txt", proc.stdout)
        for language in ("python", "powershell", "shell", "batch"):
            for action in ("print", "sum", "list", "fetch", "csv", "json", "write"):
                item = build_script({"language": language, "name": "Werk", "action": action, "purpose": "Test"})
                self.assertTrue(item["ok"], (language, action, item))
                if language == "python":
                    compile(item["content"], "werk.py", "exec")
                if language == "shell":
                    checked = subprocess.run(["bash", "-n"], input=item["content"], text=True, capture_output=True, timeout=10)
                    self.assertEqual(checked.returncode, 0, (action, checked.stderr, item["content"]))
        self.assertFalse(build_script({"language": "python", "name": "../geheim", "action": "print"})["ok"])
        messages = model_messages({
            "language": "powershell",
            "name": "Hinweis",
            "purpose": "Zeige den Text",
            "questions": "Text: Was",
        })
        self.assertTrue(messages["ok"], messages)
        self.assertEqual(messages["messages"][0]["role"], "system")
        self.assertIn("Text", messages["messages"][1]["content"])
        taken = script_from_model(
            {"language": "python", "name": "AusModell", "action": "print"},
            "```python\nprint('modell')\n```",
        )
        self.assertEqual(extract_script("```python\nprint(1)\n```").strip(), "print(1)")
        self.assertIn("print('modell')", taken["content"])
        self.assertEqual(taken["source"], "model")
        self.assertFalse(script_from_model({"language": "python", "name": "Leer", "action": "print"}, "   ")["ok"])

    def test_database_files_stay_in_workspace(self) -> None:
        import sqlite3

        from shatuide.creator import create_database, parse_schema

        parsed = parse_schema("person: id int pk, name text pflicht")
        self.assertTrue(parsed[0]["columns"][0]["primary"])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = create_database(root, {"engine": "sqlite", "name": "Lager", "schema": "name text"})
            self.assertFalse(missing["ok"])
            outside = create_database(root, {
                "engine": "sqlite",
                "name": "Lager",
                "path": "../ausserhalb.sqlite",
                "schema": "person\n  id int pk\n  name text\n",
            })
            self.assertFalse(outside["ok"])
            self.assertIn("Workspace", outside["error"])
            created = create_database(root, {
                "engine": "sqlite",
                "name": "Lager",
                "schema": "person\n  id int pk\n  name text pflicht\n  email text unique\n",
            })
            self.assertTrue(created["ok"], created)
            database = Path(created["database"])
            self.assertTrue(database.is_file())
            self.assertTrue(str(database).startswith(str(root.resolve())))
            sql = Path(created["path"]).read_text(encoding="utf-8")
            self.assertIn("CREATE TABLE person", sql)
            self.assertIn("email TEXT UNIQUE", sql)
            with sqlite3.connect(database) as con:
                con.execute("INSERT INTO person (name, email) VALUES ('Ada', 'a@b.c')")
                con.commit()
                row = con.execute("SELECT name FROM person").fetchone()
            self.assertEqual(row[0], "Ada")
            again = create_database(root, {"engine": "sqlite", "name": "Lager", "schema": "person\n  id int pk\n  name text\n"})
            self.assertFalse(again["ok"])
            self.assertIn("existiert", again["error"])
            postgres = create_database(root, {
                "engine": "postgresql",
                "name": "Lager",
                "schema": "artikel\n  id int pk\n  preis real pflicht\n",
                "apply": True,
            })
            self.assertTrue(postgres["ok"], postgres)
            self.assertFalse(postgres["applied"])
            self.assertIn("Verbindungszeichenkette fehlt", postgres["message"])
            self.assertIn("DOUBLE PRECISION", Path(postgres["path"]).read_text(encoding="utf-8"))
            mongo = create_database(root, {"engine": "mongodb", "name": "Lager", "schema": "person\n  name text pflicht\n"})
            self.assertTrue(mongo["ok"], mongo)
            self.assertIn("collections", Path(mongo["path"]).read_text(encoding="utf-8"))
            compile(Path(mongo["script"]).read_text(encoding="utf-8"), "mongo.py", "exec")
            injected = create_database(root, {"engine": "sqlite", "name": "Boese", "schema": "person\n  name);drop text\n"})
            self.assertFalse(injected["ok"])
            from shatuide.database import sqlite_query

            queried = sqlite_query(
                str(database),
                "INSERT INTO person (name, email) VALUES ('Bea', 'a;b');\nSELECT name FROM person WHERE email = 'a;b';",
            )
            self.assertTrue(queried["ok"], queried)
            self.assertEqual(queried["rows"][0]["name"], "Bea")

    def test_api_script_and_database(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        httpd, app = create_server("127.0.0.1", 0, tmp.name)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        host, port = httpd.server_address[:2]
        base = f"http://{host}:{port}"

        def request(payload: dict) -> dict:
            req = urllib.request.Request(base + "/api/studio", data=json.dumps(payload).encode("utf-8"), method="POST")
            req.add_header("X-Shatu-Token", app.token)
            req.add_header("Host", "127.0.0.1")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))

        try:
            script = request({
                "action": "script",
                "language": "python",
                "name": "Gruss",
                "action_name": "print",
                "purpose": "Begrüßt",
                "questions": "Name: Wie heißt du",
            })
            self.assertTrue(script["ok"], script)
            self.assertIn("input(", Path(script["path"]).read_text(encoding="utf-8"))
            self.assertTrue(str(Path(script["path"]).resolve()).startswith(str(Path(tmp.name).resolve())))
            database = request({
                "action": "database",
                "engine": "sqlite",
                "name": "Lager",
                "schema": "person\n  id int pk\n  name text pflicht\n",
            })
            self.assertTrue(database["ok"], database)
            self.assertTrue(Path(database["database"]).is_file())
            self.assertIn("CREATE TABLE person", Path(database["path"]).read_text(encoding="utf-8"))
        finally:
            httpd.shutdown()
            httpd.server_close()
            tmp.cleanup()


class KitTests(unittest.TestCase):
    def test_modules_build_a_running_script(self) -> None:
        import sqlite3
        import subprocess

        from shatuide.kit import build_kit, load_kit, save_kit

        greeted = build_kit({
            "language": "python",
            "name": "Gruss",
            "blocks": [
                {"id": "eingabe", "ziel": "Name", "frage": "Wie heißt du", "art": "text"},
                {"id": "ausgabe", "text": "Hallo {Name}"},
                {"id": "rechnen", "ziel": "Summe", "links": "2", "operator": "+", "rechts": "3"},
                {"id": "ausgabe", "text": "{Summe}"},
            ],
        })
        self.assertTrue(greeted["ok"], greeted)
        proc = subprocess.run([sys.executable, "-c", greeted["content"]], input="Ada\n", text=True, capture_output=True, timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Hallo Ada", proc.stdout)
        self.assertIn("5", proc.stdout)
        self.assertFalse(build_kit({"language": "python", "name": "Leer", "blocks": [{"id": "ausgabe", "text": "{Fehlt}"}]})["ok"])
        self.assertFalse(build_kit({"language": "batch", "name": "Netz", "blocks": [{"id": "web", "adresse": "https://example.com", "ziel": "Seite"}]})["ok"])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            note = root / "notiz.txt"
            note.write_text("zeile\n", encoding="utf-8")
            (root / "a.txt").write_text("x", encoding="utf-8")
            data = root / "daten.json"
            data.write_text('{"name": "Ada"}', encoding="utf-8")
            base = root / "app.sqlite"
            with sqlite3.connect(base) as con:
                con.execute("CREATE TABLE person (name TEXT)")
                con.execute("INSERT INTO person (name) VALUES ('Ada')")
            built = build_kit({
                "language": "python",
                "name": "Werk",
                "blocks": [
                    {"id": "datei_lesen", "quelle": str(note), "ziel": "Inhalt"},
                    {"id": "ausgabe", "text": "{Inhalt}"},
                    {"id": "datei_schreiben", "datei": str(root / "raus.txt"), "inhalt": "hallo-kit"},
                    {"id": "ordner", "pfad": str(root)},
                    {"id": "csv_zeile", "datei": str(root / "daten.csv"), "werte": "Ada;1"},
                    {"id": "json_lesen", "datei": str(data), "schluessel": "name", "ziel": "Daten"},
                    {"id": "ausgabe", "text": "{Daten}"},
                    {"id": "sqlite", "datei": str(base), "sql": "SELECT name FROM person"},
                    {"id": "text_bauen", "ziel": "Text", "teile": "A;B", "trenner": "-"},
                    {"id": "bedingung", "variable": "Daten", "vergleich": "gleich", "wert": "Ada", "text": "bekannt"},
                    {"id": "pause", "sekunden": "0"},
                ],
            })
            self.assertTrue(built["ok"], built)
            proc = subprocess.run([sys.executable, "-c", built["content"]], text=True, capture_output=True, timeout=10)
            self.assertEqual(proc.returncode, 0, proc.stderr + built["content"])
            self.assertIn("zeile", proc.stdout)
            self.assertIn("a.txt", proc.stdout)
            self.assertIn("Ada", proc.stdout)
            self.assertIn("bekannt", proc.stdout)
            self.assertEqual((root / "raus.txt").read_text(encoding="utf-8"), "hallo-kit\n")
            self.assertIn("Ada,1", (root / "daten.csv").read_text(encoding="utf-8"))
            for language in ("python", "powershell", "shell", "batch"):
                item = build_kit({
                    "language": language,
                    "name": "Mini",
                    "blocks": [
                        {"id": "eingabe", "ziel": "Name", "frage": "Name", "art": "text"},
                        {"id": "ausgabe", "text": "Hallo {Name}"},
                    ],
                })
                self.assertTrue(item["ok"], (language, item))
                if language == "python":
                    compile(item["content"], "mini.py", "exec")
                if language == "shell":
                    checked = subprocess.run(["bash", "-n"], input=item["content"], text=True, capture_output=True, timeout=10)
                    self.assertEqual(checked.returncode, 0, checked.stderr + item["content"])
            shell = build_kit({
                "language": "shell",
                "name": "Liste",
                "blocks": [{"id": "ordner", "pfad": str(root)}],
            })
            checked = subprocess.run(["bash", "-n"], input=shell["content"], text=True, capture_output=True, timeout=10)
            self.assertEqual(checked.returncode, 0, checked.stderr + shell["content"])
            proc = subprocess.run(["bash", "-c", shell["content"]], text=True, capture_output=True, timeout=10)
            self.assertIn("a.txt", proc.stdout, proc.stderr)
            saved = save_kit(root, {"name": "Gruss", "language": "python", "blocks": greeted["blocks"]})
            self.assertTrue(saved["ok"], saved)
            loaded = load_kit(root, "Gruss")
            self.assertEqual(loaded["blocks"][0]["ziel"], "Name")
            outside = save_kit(root, {"name": "../fremd", "language": "python", "blocks": greeted["blocks"]})
            self.assertFalse(outside["ok"])

    def test_api_kit_stays_in_workspace(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        httpd, app = create_server("127.0.0.1", 0, tmp.name)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        host, port = httpd.server_address[:2]
        base = f"http://{host}:{port}"

        def request(path: str, payload: dict | None = None) -> dict:
            data = None if payload is None else json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(base + path, data=data, method="POST" if payload is not None else "GET")
            req.add_header("X-Shatu-Token", app.token)
            req.add_header("Host", "127.0.0.1")
            if payload is not None:
                req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))

        try:
            catalog = request("/api/studio?action=kit")
            self.assertTrue(catalog["ok"], catalog)
            self.assertIn("eingabe", {item["id"] for item in catalog["modules"]})
            built = request("/api/studio", {
                "action": "kit",
                "op": "build",
                "name": "Gruss",
                "language": "python",
                "blocks": [
                    {"id": "eingabe", "ziel": "Name", "frage": "Wie heißt du", "art": "text"},
                    {"id": "ausgabe", "text": "Hallo {Name}"},
                ],
            })
            self.assertTrue(built["ok"], built)
            self.assertIn("Hallo ", Path(built["path"]).read_text(encoding="utf-8"))
            self.assertTrue((Path(tmp.name) / "baukasten" / "Gruss.json").is_file())
            loaded = request("/api/studio", {"action": "kit", "op": "load", "name": "Gruss"})
            self.assertEqual(loaded["blocks"][1]["text"], "Hallo {Name}")
        finally:
            httpd.shutdown()
            httpd.server_close()
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
