import json
import socket
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from cpcm.server import DEFAULT_PORT, App, bind_server, effective_port, make_handler


class ApiTests(unittest.TestCase):
    def test_port_stays_away_from_shatuide(self):
        self.assertEqual(effective_port(8765), DEFAULT_PORT)
        self.assertEqual(effective_port(8864), DEFAULT_PORT)
        self.assertEqual(effective_port(None), DEFAULT_PORT)
        self.assertEqual(DEFAULT_PORT, 8910)
        busy = socket.socket()
        busy.bind(("127.0.0.1", DEFAULT_PORT))
        server = None
        try:
            server = bind_server("127.0.0.1", 8765, make_handler(App(Path(tempfile.gettempdir()))))
            self.assertEqual(server.server_address[1], DEFAULT_PORT + 1)
            self.assertNotIn(server.server_address[1], range(8765, 8865))
        finally:
            if server is not None:
                server.server_close()
            busy.close()

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
                self.assertEqual(status["author"], "Andreas Meyer")
                self.assertEqual(status["author_email"], "ame@sellerbach.de")
                self.assertEqual(status["install_dir_linux"], "~/AI_Temp/CPCM")
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
