import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crossos.server import create_server


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._previous = os.environ.get("CROSSOS_STATE")
        cls._state = Path(os.environ.get("TMPDIR", "/tmp")) / "crossos-api-state.json"
        if cls._state.exists():
            cls._state.unlink()
        os.environ["CROSSOS_STATE"] = str(cls._state)
        cls.httpd = create_server("127.0.0.1", 0)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.httpd.server_address
        cls.base = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        if cls._previous is None:
            os.environ.pop("CROSSOS_STATE", None)
        else:
            os.environ["CROSSOS_STATE"] = cls._previous

    def _json(self, method, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(self.base + path, data=data, method=method)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def test_pages_and_endpoints(self):
        with urllib.request.urlopen(self.base + "/", timeout=10) as response:
            html = response.read().decode("utf-8")
        self.assertIn("CrossOS", html)
        self.assertIn("Übersicht", html)
        status, health = self._json("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(health["dry_run_default"])
        status, translated = self._json(
            "POST",
            "/api/translate",
            {
                "text": "[core]\neditor = /home/andreas/.local/bin/nvim\nautocrlf = input\n",
                "source_format": "ini",
                "target_format": "reg",
                "target_os": "windows",
                "user": "andreas",
            },
        )
        self.assertEqual(status, 200)
        self.assertIn("AppData\\\\Local\\\\bin\\\\nvim", translated["output"])
        self.assertFalse(translated["executed"])
        status, diagnosis = self._json(
            "POST",
            "/api/diagnose",
            {"text": "Installation failed 0x80070005\nSegmentation fault (core dumped)\n", "shell": "bash"},
        )
        self.assertEqual(status, 200)
        codes = {item["code"] for item in diagnosis["findings"]}
        self.assertIn("0x80070005", codes)
        self.assertIn("segfault", codes)
        status, hardware = self._json("GET", "/api/hardware/probe")
        self.assertEqual(status, 200)
        self.assertEqual(hardware["os"], "linux")
        status, apps = self._json("POST", "/api/apps/plan", {"target_os": "linux", "apps": ["Photoshop", "Git"]})
        self.assertEqual(status, 200)
        self.assertEqual(apps["apps"][0]["equivalence"], "workflow")
        self.assertFalse(apps["executed"])
        status, rejected = self._json("POST", "/api/packages/plan", {"manager": "apt", "packages": ["vim; rm -rf /"]})
        self.assertEqual(status, 400)
        self.assertNotIn("rm -rf", rejected["error"])
        self.assertNotIn("shell", rejected)
        status, fans = self._json("GET", "/api/hardware/fans")
        self.assertEqual(status, 200)
        self.assertEqual(fans["profiles"][0]["linux"]["points"], fans["profiles"][0]["windows"]["points"])
        status, traversal = self._json("GET", "/fonts/%2e%2e/%2e%2e/etc/passwd")
        self.assertIn(traversal.get("code"), {"safety", "not_found"})
        self.assertNotIn("root:", json.dumps(traversal))


if __name__ == "__main__":
    unittest.main()
