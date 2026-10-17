"""Prüfungen für Analyse, Refactoring, Debugger und die lokale API."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
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
from shatuide.icon_util import crop_center_square, decode_png, encode_png, generated_icon_png
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


if __name__ == "__main__":
    unittest.main()
