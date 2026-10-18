import json
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from cpcm.server import App, make_handler


class ApiTests(unittest.TestCase):
    def test_backup_restore_over_http(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox = root / "inbox"
            inbox.mkdir()
            (inbox / "note.txt").write_text("gemeinsam", encoding="utf-8")
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(App(root)))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_address[1]}"
            try:
                self._post(base + "/api/selection", {"path": str(inbox / "note.txt"), "kind": "file"})
                snapshot = self._post(base + "/api/backup", {})
                report = self._post(base + "/api/restore", {"id": snapshot["id"], "destination": str(root / "out"), "overwrite": True})
                restored = list((root / "out").rglob("note.txt"))
                self.assertEqual(restored[0].read_text(encoding="utf-8"), "gemeinsam")
                self.assertTrue(report["restored"])
                status = self._get(base + "/api/status")
                self.assertEqual(status["install_dir_windows"], r"D:\AI_Temp\CPCM")
                page = urllib.request.urlopen(base + "/").read()
                self.assertIn(b"Cross Platform Config Manager", page)
            finally:
                server.shutdown()
                server.server_close()

    def _post(self, url, payload):
        request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))

    def _get(self, url):
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read().decode("utf-8"))
