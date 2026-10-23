"""Verhalten von Katalog, Suche, Dienst und Autostart."""

from __future__ import annotations

import os
import struct
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path

os.environ.setdefault("FLARE_FORCE_CPU", "1")

from flare.autostart import install_autostart, launch_command, remove_autostart
from flare.calc import try_calc
from flare.client import Client
from flare.crawl import Crawler, should_skip_dir
from flare.governor import Governor, read_cpu_times, sleep_budget
from flare.hotkey import hotkey_label, parse_hotkey
from flare.launch import parse_desktop, parse_lnk
from flare.rank import Ranker, overlap_scores, trigrams
from flare.search import lexical_score, search
from flare.service import Service
from flare.store import Index


def _build_lnk(target: str) -> bytes:
    raw = target.encode("ascii") + b"\x00"
    header = bytearray(76)
    struct.pack_into("<I", header, 0, 76)
    struct.pack_into("<I", header, 0x14, 0x2)
    volume = struct.pack("<III", 17, 3, 0) + struct.pack("<I", 16) + b"\x00"
    header_size = 28
    volume_off = header_size
    local_off = volume_off + len(volume)
    suffix_off = local_off + len(raw)
    info_size = suffix_off + 1
    info = struct.pack("<III", info_size, header_size, 1)
    info += struct.pack("<IIII", volume_off, local_off, 0, suffix_off)
    info += volume + raw + b"\x00"
    return bytes(header) + info


class RankingTests(unittest.TestCase):
    def test_lexical_order(self) -> None:
        exact = lexical_score("bericht", "bericht", "/a/bericht", kind="file", tier=1, use_count=0, via="prefix")
        prefix = lexical_score("bericht", "bericht-2026.pdf", "/a/x", kind="file", tier=1, use_count=0, via="prefix")
        token = lexical_score("bericht", "alt-bericht.txt", "/a/x", kind="file", tier=1, use_count=0, via="trigram")
        self.assertGreater(exact, prefix)
        self.assertGreater(prefix, token)

    def test_typo_overlap(self) -> None:
        good = overlap_scores(trigrams("dokumnet"), [trigrams("Dokumentation")])[0]
        bad = overlap_scores(trigrams("dokumnet"), [trigrams("Netzteil")])[0]
        self.assertGreaterEqual(good, 0.5)
        self.assertLess(bad, 0.5)

    def test_calc(self) -> None:
        self.assertEqual(try_calc("2+2*3"), "8")
        self.assertEqual(try_calc("(2+2)*3"), "12")
        self.assertIsNone(try_calc("2+2; os.system('x')"))
        self.assertIsNone(try_calc("hallo"))

    def test_budget_caps_when_busy(self) -> None:
        calm = sleep_budget(0.02, 0.40, 0.9)
        busy = sleep_budget(0.02, 0.40, 0.05)
        self.assertLess(calm, busy)
        self.assertLessEqual(busy, 0.5)
        self.assertIsNotNone(read_cpu_times())

    def test_hotkey_label(self) -> None:
        mods, key = parse_hotkey("Strg+Alt+Leertaste")
        self.assertEqual(mods, {"ctrl", "alt"})
        self.assertEqual(key, "space")
        self.assertEqual(hotkey_label("ctrl+alt+space"), "Strg+Alt+Leertaste")


class IndexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "home"
        self.root.mkdir()
        (self.root / "Rechnung-2026.txt").write_text("Sonderzahlung im März\n", encoding="utf-8")
        (self.root / "Büro.txt").write_text("notizen", encoding="utf-8")
        (self.root / "Dokumentation.txt").write_text("handbuch", encoding="utf-8")
        nested = self.root / "projekte"
        nested.mkdir()
        (nested / "alpha.py").write_text("print('ok')\n", encoding="utf-8")
        hidden = self.root / ".hidden"
        hidden.mkdir()
        (hidden / "geheim.txt").write_text("nein", encoding="utf-8")
        modules = self.root / "node_modules"
        modules.mkdir()
        (modules / "pkg.js").write_text("nope", encoding="utf-8")
        (self.root / "id_rsa").write_text("secret", encoding="utf-8")
        (self.root / ".env").write_text("TOKEN=1", encoding="utf-8")
        desktop = self.root / "demo.desktop"
        desktop.write_text(
            "[Desktop Entry]\nType=Application\nName=Demo App\nName[de]=Demo Programm\nExec=demo --flag\n",
            encoding="utf-8",
        )
        (self.root / "hidden.desktop").write_text(
            "[Desktop Entry]\nType=Application\nName=Versteckt\nNoDisplay=true\nExec=hidden\n",
            encoding="utf-8",
        )
        lnk = self.root / "Werkzeug.lnk"
        lnk.write_bytes(_build_lnk(r"C:\Tools\Demo.exe"))
        self.db = Path(self.tmp.name) / "index.db"
        self.index = Index(self.db)
        self.crawler = Crawler(
            self.index,
            Governor(fast=True),
            [(str(self.root), 1)],
            threading.Event(),
            content=True,
            index_path=False,
        )

    def tearDown(self) -> None:
        self.index.close()
        self.tmp.cleanup()

    def _fill(self) -> None:
        self.crawler.prime()
        self.crawler.drain()

    def test_skip_rules(self) -> None:
        self.assertTrue(should_skip_dir("node_modules"))
        self.assertTrue(should_skip_dir(".git"))
        self.assertFalse(should_skip_dir("Dokumente"))

    def test_index_search_and_incremental(self) -> None:
        self._fill()
        self.assertGreater(self.crawler.readdirs, 0)
        names = {hit["name"] for hit in search(self.index, Ranker(allow_cuda=False), "rechnung")["results"]}
        self.assertIn("Rechnung-2026.txt", names)
        buro = search(self.index, Ranker(allow_cuda=False), "büro")["results"]
        self.assertTrue(any(hit["name"] == "Büro.txt" for hit in buro))
        content = search(self.index, Ranker(allow_cuda=False), "sonderzahlung")["results"]
        self.assertTrue(content and content[0]["via"] == "content")
        fuzzy = search(self.index, Ranker(allow_cuda=False), "dokumnet")["results"]
        self.assertTrue(any(hit["name"] == "Dokumentation.txt" for hit in fuzzy), fuzzy)
        apps = search(self.index, Ranker(allow_cuda=False), "demo programm")["results"]
        self.assertTrue(any(hit["kind"] == "app" and hit["name"] == "Demo Programm" for hit in apps), apps)
        self.assertFalse(any(hit["name"] == "Versteckt" for hit in search(self.index, Ranker(allow_cuda=False), "versteckt")["results"]))
        self.assertFalse(any("geheim" in hit["name"] for hit in search(self.index, Ranker(allow_cuda=False), "geheim")["results"]))
        self.assertFalse(any(hit["name"] == "pkg.js" for hit in search(self.index, Ranker(allow_cuda=False), "pkg")["results"]))
        self.assertFalse(any(hit["name"] == "id_rsa" for hit in search(self.index, Ranker(allow_cuda=False), "id_rsa")["results"]))
        folder = search(self.index, Ranker(allow_cuda=False), "projekte")["results"]
        self.assertTrue(any(hit["kind"] == "dir" for hit in folder))
        lnk_hits = search(self.index, Ranker(allow_cuda=False), "werkzeug")["results"]
        self.assertTrue(lnk_hits and lnk_hits[0]["kind"] == "app")
        self.assertTrue(lnk_hits[0]["path"].endswith("werkzeug.lnk") or lnk_hits[0]["name"] == "Werkzeug")

        target = next(hit for hit in search(self.index, Ranker(allow_cuda=False), "alpha.py")["results"] if hit["name"] == "alpha.py")
        self.index.record_use(target["id"], int(time.time()))
        self.crawler.readdirs = 0
        self.crawler.enqueue_all()
        self.crawler.drain()
        self.assertEqual(self.crawler.readdirs, 0)
        again = self.index.get(target["id"])
        self.assertIsNotNone(again)
        assert again is not None
        self.assertEqual(again["use_count"], 1)

        (self.root / "neu.txt").write_text("frisch", encoding="utf-8")
        self.crawler.enqueue_all()
        self.crawler.drain()
        self.assertTrue(any(hit["name"] == "neu.txt" for hit in search(self.index, Ranker(allow_cuda=False), "neu")["results"]))
        (self.root / "neu.txt").unlink()
        self.crawler.enqueue_all()
        self.crawler.drain()
        self.assertFalse(any(hit["name"] == "neu.txt" for hit in search(self.index, Ranker(allow_cuda=False), "neu.txt")["results"]))

    def test_many_files_stay_fast(self) -> None:
        bulk = self.root / "stapel"
        bulk.mkdir()
        for index in range(1500):
            (bulk / f"datei-{index:04d}.txt").write_text("x", encoding="utf-8")
        started = time.perf_counter()
        self._fill()
        elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 20.0, elapsed)
        ranker = Ranker(allow_cuda=False)
        search(self.index, ranker, "datei-1499")
        samples = []
        for _ in range(8):
            t0 = time.perf_counter()
            payload = search(self.index, ranker, "datei-1499")
            samples.append((time.perf_counter() - t0) * 1000)
        self.assertTrue(any(hit["name"] == "datei-1499.txt" for hit in payload["results"]))
        self.assertLess(sorted(samples)[len(samples) // 2], 40.0, samples)

    def test_lnk_and_desktop_parsers(self) -> None:
        parsed = parse_lnk(str(self.root / "Werkzeug.lnk"))
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["kind"], "app")
        self.assertIn("Demo.exe", parsed["launch"])
        desktop = parse_desktop(str(self.root / "demo.desktop"))
        self.assertIsNotNone(desktop)
        assert desktop is not None
        self.assertEqual(desktop["name"], "Demo Programm")
        self.assertIsNone(parse_desktop(str(self.root / "hidden.desktop")))


class ServiceTests(unittest.TestCase):
    def test_http_and_client(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        try:
            root = Path(tmp.name) / "docs"
            root.mkdir()
            (root / "Vertrag.txt").write_text("klausel", encoding="utf-8")
            data = Path(tmp.name) / "data"
            sink = Path(tmp.name) / "opened.txt"
            os.environ["FLARE_OPEN_SINK"] = str(sink)
            service = Service(
                data_dir=data,
                roots=[(str(root), 1)],
                open_immediately=False,
                allow_ui=False,
                hotkey=False,
                watch=False,
                index_path=False,
                fast=True,
                port=0,
            )
            service.start()
            found = False
            payload: dict = {}
            for _ in range(50):
                payload = service.search("vertrag")
                if any(hit["name"] == "Vertrag.txt" for hit in payload["results"]):
                    found = True
                    break
                time.sleep(0.05)
            self.assertTrue(found, payload)
            with urllib.request.urlopen(service.url + "api/health", timeout=2) as response:
                self.assertEqual(response.status, 200)
            client = Client(data)
            remote = client.search("vertrag")
            self.assertTrue(any(hit["name"] == "Vertrag.txt" for hit in remote["results"]))
            item_id = next(hit["id"] for hit in remote["results"] if hit["name"] == "Vertrag.txt")
            self.assertTrue(client.open_id(item_id))
            self.assertIn("Vertrag.txt", sink.read_text(encoding="utf-8"))
            self.assertTrue(client.status()["running"])
            service.shutdown()
            local = Client(data).search("vertrag")
            self.assertTrue(any(hit["name"] == "Vertrag.txt" for hit in local["results"]))
        finally:
            os.environ.pop("FLARE_OPEN_SINK", None)
            tmp.cleanup()


class AutostartTests(unittest.TestCase):
    def test_desktop_file_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            path = install_autostart(home)
            text = Path(path).read_text(encoding="utf-8")
            self.assertIn("--background", text)
            self.assertIn("flare.py", text)
            self.assertIn("X-GNOME-Autostart-enabled=true", text)
            command = launch_command(True)
            self.assertIn("--background", command)
            remove_autostart(home)
            self.assertFalse(Path(path).exists())


if __name__ == "__main__":
    unittest.main()
