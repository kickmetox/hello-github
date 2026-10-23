"""Verhalten von Katalog, Suche, Dienst und Autostart."""

from __future__ import annotations

import json
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
from flare.crawl import Crawler, DRIVE_POLL_S, RESCHEDULE, application_roots, dedupe_roots, merge_volume_roots, roots_worth_watching, should_skip_dir, _user_dirs
from flare.paths import is_inside, norm, place_key, prefix_with_sep
from flare.volumes import (
    DRIVE_CDROM,
    DRIVE_FIXED,
    DRIVE_RAMDISK,
    DRIVE_REMOTE,
    DRIVE_REMOVABLE,
    FILE_ATTRIBUTE_OFFLINE,
    FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS,
    DriveInfo,
    discover_cloud_roots,
    drive_roots_for_config,
    exclude_drive_list,
    index_network_enabled,
    is_offline_stat,
    list_windows_drives,
    normalize_drive_root,
    read_onedrive_folders,
    answers_quickly,
    select_drive_roots,
    shallow_remote_roots,
    should_sample_content,
    tracked_drives,
    windows_cloud_roots,
    windows_system_drive,
)
from flare.governor import Governor, read_cpu_times, sleep_budget
from flare.hotkey import hotkey_label, parse_hotkey
from flare.launch import parse_lnk
from flare.ngram import NameIndex
from flare.rank import Ranker, dice_scores, overlap_scores, trigrams
from flare.search import lexical_score, search
from flare.service import Service
from flare.store import Index, compare_indexes, copy_index


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

    def test_gdf_word_outranks_hash_infix(self) -> None:
        zurich = lexical_score(
            "gdf", "Zürich GDF", r"D:\Zürich GDF", kind="dir", tier=1, use_count=0, via="trigram"
        )
        schriften = lexical_score(
            "GDF", "Schriften GdF", r"D:\Schriften GdF", kind="dir", tier=1, use_count=0, via="trigram"
        )
        hashed = lexical_score(
            "gdf",
            "e_DRHCGYGDFOfQEGETH2FVEEEZCDGECYAF.R",
            r"C:\Users\a\AppData\Local\Microsoft\Office\16.0\OfficeFileCache\e_DRHCGYGDFOfQEGETH2FVEEEZCDGECYAF.R",
            kind="file",
            tier=0,
            use_count=30,
            via="trigram",
        )
        self.assertGreater(zurich, hashed)
        self.assertGreater(schriften, hashed)
        self.assertGreater(zurich - hashed, 1000)

    def test_gdf_short_query_hits_words_without_similar(self) -> None:
        names = [
            "GDF Formulare",
            "Zürich GDF",
            "1 GDF Formulare",
            "Schriften GdF",
        ]
        hashes = [
            "e_DRHCGYGDFOfQEGETH2FVEEEZCDGECYAF.R",
            "e_CJAPDRHGGDF5CUFADXDOA7GVCHF5EOGN.R",
            "bookmarks-2026-08-17_24_lq1gdfSw1my1fFgvOsvin-wgJlh8KVKjchfNug4lzq",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            index = Index(Path(tmp) / "index.db")
            ranker = Ranker(allow_cuda=False)
            try:
                items: list[dict] = []
                for number in range(158):
                    name = names[number] if number < len(names) else f"GDF Ordner {number:03d}"
                    items.append(
                        {
                            "kind": "dir",
                            "name": name,
                            "path": rf"D:\Dokumente\{number:03d}\{name}",
                            "dir": rf"D:\Dokumente\{number:03d}",
                            "ext": "",
                            "launch": None,
                            "mtime_ns": 1,
                            "size": 0,
                            "tier": 1,
                        }
                    )
                for name in hashes:
                    items.append(
                        {
                            "kind": "file",
                            "name": name,
                            "path": rf"C:\Users\a\AppData\Local\Microsoft\Office\16.0\OfficeFileCache\{name}",
                            "dir": r"C:\Users\a\AppData\Local\Microsoft\Office\16.0\OfficeFileCache",
                            "ext": Path(name).suffix.casefold(),
                            "launch": None,
                            "mtime_ns": 1,
                            "size": 1,
                            "tier": 0,
                        }
                    )
                index.reconcile_dir(r"D:\Dokumente", r"D:\\", 1, 1, items, [])
                from flare.search import ui_result_limit

                found = search(index, ranker, "gdf", limit=ui_result_limit(False), similar=False)
                got = [hit["name"] for hit in found["results"]]
                for name in names:
                    self.assertIn(name, got, got[:12])
                for name in hashes:
                    self.assertNotIn(name, got)
                self.assertGreaterEqual(len(got), 158)
                self.assertLessEqual(len(got), ui_result_limit(False))
                wide = search(index, ranker, "GDF", limit=ui_result_limit(True), similar=True)
                wide_names = [hit["name"] for hit in wide["results"]]
                for name in names:
                    self.assertIn(name, wide_names)
                for name in hashes:
                    self.assertNotIn(name, wide_names)
            finally:
                index.close()
                ranker.close()

    def test_exact_xchange_outranks_infix_and_is_not_dropped(self) -> None:
        exact = lexical_score(
            "Xchange", "Xchange", r"F:\Xchange", kind="dir", tier=2, use_count=0, via="prefix"
        )
        prefix = lexical_score(
            "Xchange",
            "Xchange-backup",
            r"F:\Xchange-backup",
            kind="dir",
            tier=1,
            use_count=30,
            via="prefix",
        )
        infix = lexical_score(
            "Xchange",
            "DataExchangeHost",
            r"C:\Windows\System32\DataExchangeHost.exe",
            kind="app",
            tier=0,
            use_count=30,
            via="trigram",
        )
        self.assertGreater(exact, prefix)
        self.assertGreater(prefix, infix)
        with tempfile.TemporaryDirectory() as tmp:
            items: list[dict] = [
                {
                    "kind": "dir",
                    "name": "Xchange",
                    "path": r"F:\Xchange",
                    "dir": r"F:\\",
                    "ext": "",
                    "launch": None,
                    "mtime_ns": 1,
                    "size": 0,
                    "tier": 2,
                },
                {
                    "kind": "app",
                    "name": "DataExchangeHost",
                    "path": r"C:\Windows\System32\DataExchangeHost.exe",
                    "dir": ":path",
                    "ext": ".exe",
                    "launch": None,
                    "mtime_ns": 1,
                    "size": 10,
                    "tier": 0,
                },
                {
                    "kind": "file",
                    "name": "Xchang.txt",
                    "path": r"F:\Xchang.txt",
                    "dir": r"F:\\",
                    "ext": ".txt",
                    "launch": None,
                    "mtime_ns": 1,
                    "size": 1,
                    "tier": 1,
                },
            ]
            for number in range(45):
                items.append(
                    {
                        "kind": "file",
                        "name": f"Xchange-{number:02d}.txt",
                        "path": rf"F:\pref\Xchange-{number:02d}.txt",
                        "dir": r"F:\pref",
                        "ext": ".txt",
                        "launch": None,
                        "mtime_ns": 1,
                        "size": 1,
                        "tier": 1,
                    }
                )
            for number in range(40):
                items.append(
                    {
                        "kind": "file",
                        "name": f"DataXchange{number:02d}.dat",
                        "path": rf"C:\infix\DataXchange{number:02d}.dat",
                        "dir": r"C:\infix",
                        "ext": ".dat",
                        "launch": None,
                        "mtime_ns": 1,
                        "size": 1,
                        "tier": 0,
                    }
                )
            index = Index(Path(tmp) / "index.db")
            ranker = Ranker(allow_cuda=False)
            try:
                index.reconcile_dir(r"F:\\", "", 1, 2, items, [])
                with index.lock:
                    index.con.execute("UPDATE items SET use_count=30 WHERE name != ?", ("Xchange",))
                    index.con.commit()
                wide = search(index, ranker, "Xchange", limit=50, similar=False)
                names = [hit["name"] for hit in wide["results"]]
                self.assertIn("Xchange", names)
                self.assertIn("DataExchangeHost", names)
                self.assertLess(names.index("Xchange"), names.index("DataExchangeHost"))
                self.assertEqual(names[0], "Xchange")
                self.assertNotIn("Xchang.txt", names)
                tight = search(index, ranker, "Xchange", limit=3, similar=False)["results"]
                self.assertEqual(tight[0]["name"], "Xchange")
                self.assertLessEqual(len(tight), 3)
                self.assertNotIn("DataExchangeHost", [hit["name"] for hit in tight])
                self.assertNotIn("Xchang.txt", [hit["name"] for hit in tight])
            finally:
                index.close()
                ranker.close()

    def test_typo_overlap(self) -> None:
        good = overlap_scores(trigrams("dokumnet"), [trigrams("Dokumentation")])[0]
        bad = overlap_scores(trigrams("dokumnet"), [trigrams("Netzteil")])[0]
        self.assertGreaterEqual(good, 0.5)
        self.assertLess(bad, 0.5)
        ranker = Ranker(allow_cuda=False)
        near = ranker.similarity_scores("bericht", ["Berricht"])[0]
        far = ranker.similarity_scores("bericht", ["Netzteil"])[0]
        self.assertGreaterEqual(near, 0.5)
        self.assertLess(far, 0.5)
        self.assertGreater(dice_scores(trigrams("bericht"), [trigrams("Berricht")])[0], 0.4)

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
        self.assertTrue(
            should_skip_dir(r"C:\Users\a\AppData\Local\Microsoft\Office\16.0\OfficeFileCache")
        )
        self.assertTrue(should_skip_dir("OfficeFileCache"))
        self.assertTrue(should_skip_dir(r"C:\Users\a\AppData\Local\Microsoft\Windows\INetCache"))
        self.assertTrue(should_skip_dir(r"C:\Users\a\AppData\Local\Google\Chrome\User Data\Default\GPUCache"))
        self.assertTrue(should_skip_dir(r"C:\Users\a\AppData\Local\Google\Chrome\User Data\Default\Code Cache"))
        self.assertTrue(should_skip_dir(r"C:\Users\a\AppData\Local\Google\Chrome\User Data\Default\Cache"))
        self.assertTrue(should_skip_dir(r"C:\Users\a\AppData\Local\Temp"))
        self.assertFalse(should_skip_dir(r"D:\GDF\Temp"))
        self.assertFalse(should_skip_dir("Temp"))
        self.assertFalse(should_skip_dir(r"D:\Projekte\Cache"))

    def test_office_file_cache_is_not_indexed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "profile"
            cache = root / "AppData" / "Local" / "Microsoft" / "Office" / "16.0" / "OfficeFileCache"
            cache.mkdir(parents=True)
            (cache / "e_DRHCGYGDFOfQEGETH2FVEEEZCDGECYAF.R").write_bytes(b"x")
            temp = root / "AppData" / "Local" / "Temp"
            temp.mkdir(parents=True)
            (temp / "gdf-temp.txt").write_text("x", encoding="utf-8")
            kept = root / "Temp"
            kept.mkdir()
            (kept / "behalten.txt").write_text("x", encoding="utf-8")
            (root / "GDF Formulare").mkdir()
            index = Index(Path(tmp) / "index.db")
            try:
                crawler = Crawler(
                    index,
                    Governor(fast=True),
                    [(str(root), 1)],
                    threading.Event(),
                    content=False,
                    index_path=False,
                )
                crawler.prime()
                crawler.drain()
                stored = {row[0] for row in index.con.execute("SELECT name FROM items")}
                self.assertIn("GDF Formulare", stored)
                self.assertIn("behalten.txt", stored)
                self.assertNotIn("e_DRHCGYGDFOfQEGETH2FVEEEZCDGECYAF.R", stored)
                self.assertNotIn("OfficeFileCache", stored)
                self.assertNotIn("gdf-temp.txt", stored)
            finally:
                index.close()

    def test_index_search_and_incremental(self) -> None:
        self._fill()
        self.assertGreater(self.crawler.readdirs, 0)
        empty = search(self.index, Ranker(allow_cuda=False), "")["results"]
        self.assertTrue(any(hit["name"] == "Werkzeug" for hit in empty), empty)
        self.assertFalse(any(hit["name"] == "[" for hit in empty))
        names = {hit["name"] for hit in search(self.index, Ranker(allow_cuda=False), "rechnung")["results"]}
        self.assertIn("Rechnung-2026.txt", names)
        buro = search(self.index, Ranker(allow_cuda=False), "büro")["results"]
        self.assertTrue(any(hit["name"] == "Büro.txt" for hit in buro))
        content = search(self.index, Ranker(allow_cuda=False), "sonderzahlung")["results"]
        self.assertTrue(content and content[0]["via"] == "content")
        fuzzy = search(self.index, Ranker(allow_cuda=False), "dokumnet")["results"]
        self.assertTrue(any(hit["name"] == "Dokumentation.txt" for hit in fuzzy), fuzzy)
        apps = search(self.index, Ranker(allow_cuda=False), "werkzeug")["results"]
        self.assertTrue(any(hit["kind"] == "app" and hit["name"] == "Werkzeug" for hit in apps), apps)
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
        time.sleep(0.05)
        self.crawler.enqueue_all()
        self.crawler.drain()
        self.assertTrue(any(hit["name"] == "neu.txt" for hit in search(self.index, Ranker(allow_cuda=False), "neu")["results"]))
        time.sleep(0.05)
        (self.root / "neu.txt").unlink()
        time.sleep(0.05)
        self.crawler.enqueue_all()
        self.crawler.drain()
        self.assertFalse(any(hit["name"] == "neu.txt" for hit in search(self.index, Ranker(allow_cuda=False), "neu.txt")["results"]))
        self.crawler.readdir_max_age_ns = 0
        self.crawler.readdirs = 0
        self.crawler.enqueue_all()
        self.crawler.drain()
        self.assertGreater(self.crawler.readdirs, 0)

    def test_dirty_flag_sees_delete_without_mtime_change(self) -> None:
        self._fill()
        (self.root / "Rechnung-2026.txt").unlink()
        directory = norm(self.root)
        mtime, _dirty, _read = self.index.dir_info(directory)
        assert mtime is not None
        os.utime(self.root, ns=(mtime, mtime))
        self.index.mark_dirty(directory)
        self.crawler.enqueue_all()
        self.crawler.drain()
        hits = search(self.index, Ranker(allow_cuda=False), "rechnung")["results"]
        self.assertFalse(any(hit["name"] == "Rechnung-2026.txt" for hit in hits))

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

    def test_lnk_parser(self) -> None:
        parsed = parse_lnk(str(self.root / "Werkzeug.lnk"))
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["kind"], "app")
        self.assertIn("Demo.exe", parsed["launch"])


class SimilarityTests(unittest.TestCase):
    def test_similar_mode_keeps_near_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "docs"
            root.mkdir()
            for index in range(8):
                (root / f"bericht-{index}.txt").write_text("x", encoding="utf-8")
            (root / "Berricht-extra.txt").write_text("x", encoding="utf-8")
            (root / "Netzteil.txt").write_text("x", encoding="utf-8")
            index = Index(Path(tmp) / "index.db")
            try:
                crawler = Crawler(
                    index,
                    Governor(fast=True),
                    [(str(root), 1)],
                    threading.Event(),
                    content=False,
                    index_path=False,
                )
                crawler.prime()
                crawler.drain()
                ranker = Ranker(allow_cuda=False)
                plain = search(index, ranker, "bericht", limit=8)
                self.assertFalse(any(hit["name"] == "Berricht-extra.txt" for hit in plain["results"]), plain)
                sim = search(index, ranker, "bericht", limit=8, similar=True)
                near = [hit for hit in sim["results"] if hit["name"] == "Berricht-extra.txt"]
                self.assertTrue(near and near[0]["via"] == "similar", sim)
                self.assertGreaterEqual(near[0]["similarity"], 0.5)
                self.assertLessEqual(near[0]["similarity"], 1)
                self.assertFalse(any(hit["name"] == "Netzteil.txt" for hit in sim["results"]))
                lexical = [hit for hit in sim["results"] if hit["via"] != "similar"]
                self.assertGreaterEqual(len(lexical), len(sim["results"]) // 2)
                self.assertTrue(any(hit["name"].startswith("bericht-") for hit in lexical))
                index.counts = lambda: {"items": 3001, "dirs": 1}
                via_fts = search(index, ranker, "bericht", limit=8, similar=True)
                fts_near = [hit for hit in via_fts["results"] if hit["name"] == "Berricht-extra.txt"]
                self.assertTrue(fts_near and fts_near[0]["via"] == "similar", via_fts)
                self.assertFalse(any(hit["name"] == "Netzteil.txt" for hit in via_fts["results"]))
            finally:
                index.close()

    def test_johnson_similar_hits_are_selectable_rows(self) -> None:
        from flare.search import _FUZZY_MIN, ui_result_limit
        from flare.window import path_for_selection, rows_after_reset, search_status, selectable_rows

        self.assertGreaterEqual(_FUZZY_MIN, 0.5)
        self.assertEqual(ui_result_limit(False), 200)
        self.assertEqual(ui_result_limit(True), 200)
        self.assertGreaterEqual(ui_result_limit(False), 30)
        with tempfile.TemporaryDirectory() as tmp:
            index = Index(Path(tmp) / "index.db")
            try:
                rows: list[tuple[str, str]] = [
                    (f"personal-song-{number:03d}", rf"C:\noise\personal-song-{number:03d}.txt")
                    for number in range(400)
                ]
                rows.append(("Chris Johnson notes", r"C:\docs\Chris Johnson notes"))
                for number in range(20):
                    rows.append((f"Johnston {number:02d}", rf"C:\people\Johnston {number:02d}.txt"))
                rows.append(("Johnston notes", r"D:\a\Johnston notes"))
                rows.append(("Johnston notes", r"E:\b\Johnston notes"))
                for name, path in rows:
                    index.con.execute(
                        """
                        INSERT INTO items(kind, name, name_fold, path, dir, ext, mtime_ns, size, tier)
                        VALUES ('file', ?, ?, ?, ?, '.txt', 1, 1, 1)
                        """,
                        (name, name.casefold(), path, str(Path(path).parent)),
                    )
                index.con.commit()
                index._load_names()
                ranker = Ranker(allow_cuda=False)
                try:
                    plain = search(index, ranker, "johnson", limit=ui_result_limit(False), similar=False)
                    self.assertTrue(all(hit.get("via") != "similar" for hit in plain["results"]), plain)
                    self._assert_johnson_rows(
                        search(index, ranker, "johnson", limit=ui_result_limit(True), similar=True)
                    )
                    narrow = search(index, ranker, "johnson", limit=12, similar=True)
                    self.assertGreater(len(narrow["results"]), 1)
                    self.assertLess(len(narrow["results"]), 23)
                    index.counts = lambda: {"items": 3001, "dirs": 1}
                    wide = search(index, ranker, "johnson", limit=ui_result_limit(True), similar=True)
                    shown = self._assert_johnson_rows(wide)
                    self.assertEqual(rows_after_reset([hit["name"] for hit in shown]), [hit["name"] for hit in shown])
                    self.assertEqual(len(shown), len(rows_after_reset([hit["name"] for hit in shown])))
                finally:
                    ranker.close()
            finally:
                index.close()

    def _assert_johnson_rows(self, payload: dict) -> list[dict]:
        from flare.window import path_for_selection, search_status, selectable_rows

        rows = selectable_rows(payload["results"])
        self.assertEqual(len(rows), len(payload["results"]))
        self.assertGreater(len(rows), 1)
        names = [row["name"] for row in rows]
        self.assertIn("Chris Johnson notes", names)
        self.assertGreater(names.count("Johnston notes"), 1)
        johnston = [row for row in rows if str(row["name"]).startswith("Johnston")]
        self.assertGreaterEqual(len(johnston), 22, names)
        self.assertTrue(all(float(row["similarity"]) >= 0.5 for row in johnston), johnston)
        self.assertTrue(all(row["via"] == "similar" for row in johnston), johnston)
        lexical = [row for row in rows if row["name"] == "Chris Johnson notes"]
        self.assertTrue(lexical and lexical[0]["via"] != "similar", lexical)
        paths = [path_for_selection(rows, index) for index in range(len(rows))]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertIn(r"D:\a\Johnston notes", paths)
        self.assertIn(r"E:\b\Johnston notes", paths)
        first = paths.index(r"D:\a\Johnston notes")
        second = paths.index(r"E:\b\Johnston notes")
        self.assertNotEqual(
            search_status("Ähnlichkeit", payload["took_ms"], len(rows), path_for_selection(rows, first)),
            search_status("Ähnlichkeit", payload["took_ms"], len(rows), path_for_selection(rows, second)),
        )
        return rows

    def test_johnson_infix_names_are_returned_with_and_without_similar(self) -> None:
        from flare.search import ui_result_limit

        examples = [
            "Letter Chris Johnson",
            "Reisekosten Johnson Nov18.pdf",
            "Meeting Professor Christopher Johnson_GdF.docx",
            "Failure in Safety-Critical Systems, by Chris Johnson",
        ]
        self.assertGreaterEqual(ui_result_limit(False), 30)
        self.assertGreaterEqual(ui_result_limit(True), 30)
        self.assertTrue(
            all(
                "johnson" in name.casefold() and not name.casefold().startswith("johnson")
                for name in examples
            )
        )
        with tempfile.TemporaryDirectory() as tmp:
            index = Index(Path(tmp) / "index.db")
            try:
                stored: list[tuple[str, str, str]] = [
                    (name, rf"C:\docs\{name}", "file") for name in examples
                ]
                stored.append(("Ablage Johnson", r"C:\docs\Ablage Johnson", "dir"))
                stored.append(("Johnson Start.txt", r"C:\docs\Johnson Start.txt", "file"))
                for number in range(25):
                    name = f"Akte {number:02d} Johnson"
                    stored.append((name, rf"C:\akten\{name}", "file"))
                stored.append(("Johnston nur ähnlich", r"C:\people\Johnston nur ähnlich.txt", "file"))
                for number in range(40):
                    name = f"personal-song-{number:03d}"
                    stored.append((name, rf"C:\noise\{name}.txt", "file"))
                for name, path, kind in stored:
                    index.con.execute(
                        """
                        INSERT INTO items(kind, name, name_fold, path, dir, ext, mtime_ns, size, tier)
                        VALUES (?, ?, ?, ?, ?, ?, 1, 1, 1)
                        """,
                        (kind, name, name.casefold(), path, str(Path(path).parent), Path(name).suffix.casefold()),
                    )
                index.con.commit()
                index._load_names()
                ranker = Ranker(allow_cuda=False)
                try:
                    for similar in (False, True):
                        payload = search(
                            index,
                            ranker,
                            "johnson",
                            limit=ui_result_limit(similar),
                            similar=similar,
                        )
                        names = [hit["name"] for hit in payload["results"]]
                        for example in examples:
                            self.assertIn(example, names, names)
                            hit = next(row for row in payload["results"] if row["name"] == example)
                            self.assertNotEqual(hit["via"], "similar", hit)
                        self.assertIn("Ablage Johnson", names)
                        folder = next(row for row in payload["results"] if row["name"] == "Ablage Johnson")
                        self.assertEqual(folder["kind"], "dir")
                        infix = [name for name in names if "johnson" in name.casefold()]
                        self.assertGreaterEqual(len(infix), 30, names)
                        self.assertLessEqual(len(payload["results"]), ui_result_limit(similar))
                    plain = search(index, ranker, "johnson", limit=ui_result_limit(False), similar=False)
                    plain_names = [hit["name"] for hit in plain["results"]]
                    self.assertIn("Johnson Start.txt", plain_names)
                    self.assertNotIn("Johnston nur ähnlich", plain_names)
                    wide = search(index, ranker, "johnson", limit=ui_result_limit(True), similar=True)
                    self.assertIn("Johnston nur ähnlich", [hit["name"] for hit in wide["results"]])
                finally:
                    ranker.close()
            finally:
                index.close()

    def test_name_index_only_returns_sharing_trigrams(self) -> None:
        names = NameIndex()
        names.load(
            [
                {"id": 1, "name": "Berricht-extra.txt", "path": "/a", "dir": "/"},
                {"id": 2, "name": "Netzteil.txt", "path": "/b", "dir": "/"},
            ]
        )
        found = {row["name"] for row in names.candidates("bericht")}
        self.assertIn("Berricht-extra.txt", found)
        self.assertNotIn("Netzteil.txt", found)

    def test_window_is_not_a_browser(self) -> None:
        import flare.service as service
        import flare.window as window

        self.assertFalse(hasattr(service, "spawn_ui"))
        self.assertFalse(hasattr(service, "find_browser"))
        if os.name != "nt":
            self.assertFalse(window.supported())


class ScheduleTests(unittest.TestCase):
    def test_path_rescan_is_spaced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "docs"
            root.mkdir()
            (root / "notiz.txt").write_text("x", encoding="utf-8")
            index = Index(Path(tmp) / "index.db")
            try:
                crawler = Crawler(
                    index,
                    Governor(fast=True),
                    [(str(root), 1)],
                    threading.Event(),
                    content=False,
                    index_path=True,
                )
                crawler.prime()
                crawler.drain()
                for _ in range(4):
                    crawler._maybe_schedule()
                self.assertEqual(crawler.queued(), 0)
                crawler._next_full[0] = 0
                crawler._maybe_schedule()
                self.assertEqual(crawler.queued(), 1)
                crawler._maybe_schedule()
                self.assertEqual(crawler.queued(), 1)
                self.assertGreater(crawler._next_full[0], time.monotonic())
            finally:
                index.close()


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
    def test_run_key_roundtrip(self) -> None:
        import sys
        from unittest import mock

        fake = mock.MagicMock()
        with mock.patch.object(sys, "platform", "win32"), mock.patch.dict(sys.modules, {"winreg": fake}):
            where = install_autostart()
            self.assertEqual(where, r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run\Flare")
            value = fake.SetValueEx.call_args[0][4]
            self.assertIn("--background", value)
            self.assertIn("flare.py", value)
            remove_autostart()
        fake.DeleteValue.assert_called_once()

    def test_autostart_requires_windows(self) -> None:
        import sys

        if sys.platform == "win32":
            return
        with self.assertRaises(RuntimeError):
            install_autostart()

    def test_cli_requires_windows(self) -> None:
        import sys

        from flare.cli import main

        if sys.platform == "win32":
            return
        self.assertEqual(main(["status"]), 2)

    def test_windowed_stdio_uses_devnull(self) -> None:
        import inspect
        import sys

        from flare.cli import _ensure_stdio

        source = inspect.getsource(_ensure_stdio)
        for banned in ("wstring_at", "GetCommandLineW", "ReadConsole", "AllocConsole", "ctypes"):
            self.assertNotIn(banned, source)
        saved = (sys.stdin, sys.stdout, sys.stderr)
        try:
            sys.stdin = None
            sys.stdout = None
            sys.stderr = None
            _ensure_stdio()
            self.assertIsNotNone(sys.stdin)
            self.assertIsNotNone(sys.stdout)
            self.assertIsNotNone(sys.stderr)
            for stream in (sys.stdin, sys.stdout, sys.stderr):
                self.assertEqual(os.path.basename(stream.name), os.path.basename(os.devnull))
            sys.stdout.write("ok")
            sys.stderr.write("ok")
            sys.stdout.flush()
            sys.stderr.flush()
        finally:
            for stream in (sys.stdin, sys.stdout, sys.stderr):
                if stream is not None and stream not in saved:
                    stream.close()
            sys.stdin, sys.stdout, sys.stderr = saved

    def test_frozen_windows_exe_reaches_service(self) -> None:
        import sys
        from unittest import mock

        from flare.cli import main

        with tempfile.TemporaryDirectory() as tmp:
            with (
                mock.patch.object(sys, "platform", "win32"),
                mock.patch.object(sys, "frozen", True, create=True),
                mock.patch.object(sys, "executable", r"C:\Users\a\AppData\Local\Programs\Flare\Flare.exe"),
                mock.patch("flare.cli.Service") as service_cls,
            ):
                code = main(["--data-dir", tmp, "--no-hotkey", "--no-watch"])
        self.assertEqual(code, 0)
        service_cls.assert_called_once()
        service_cls.return_value.run_forever.assert_called_once()

    def test_default_roots_are_windows_only(self) -> None:
        import sys

        if sys.platform == "win32":
            return
        self.assertEqual(_user_dirs(), [])
        self.assertEqual(application_roots(), [])

    def test_frozen_windows_command_uses_the_exe(self) -> None:
        import sys
        from unittest import mock

        exe = r"C:\Users\a\AppData\Local\Programs\Flare\Flare.exe"
        with (
            mock.patch.object(sys, "frozen", True, create=True),
            mock.patch.object(sys, "platform", "win32"),
            mock.patch.object(sys, "executable", exe),
        ):
            command = launch_command(True)
        self.assertIn("Flare.exe", command)
        self.assertIn("--background", command)
        self.assertNotIn("flare.py", command)
        self.assertNotIn("-m", command)


def _names(index: Index, text: str) -> set[str]:
    return {hit["name"] for hit in search(index, Ranker(allow_cuda=False), text)["results"]}


class VolumeTests(unittest.TestCase):
    def _sample_drives(self) -> list[DriveInfo]:
        return [
            DriveInfo("E:\\", DRIVE_REMOVABLE, "STICK", True),
            DriveInfo("D:\\", DRIVE_FIXED, "DATA", True),
            DriveInfo("C:\\", DRIVE_FIXED, "Windows", True),
            DriveInfo("F:\\", DRIVE_CDROM, "DVD", True),
            DriveInfo("Z:\\", DRIVE_REMOTE, "NAS", True),
            DriveInfo("G:\\", DRIVE_REMOVABLE, None, True),
            DriveInfo("H:\\", DRIVE_FIXED, "LOCKED", False),
            DriveInfo("R:\\", DRIVE_RAMDISK, "RAM", True),
            DriveInfo("Y:\\", DRIVE_REMOTE, None, False),
        ]

    def test_removable_and_nonsystem_fixed_drives_are_included(self) -> None:
        chosen = dict(
            select_drive_roots(
                self._sample_drives(),
                system_drive=r"C:\Windows",
                index_network=False,
                exclude=[],
            )
        )
        self.assertEqual(chosen["E:\\"], 1)
        self.assertEqual(chosen["D:\\"], 1)
        self.assertNotIn("C:\\", chosen)
        self.assertNotIn("F:\\", chosen)
        self.assertNotIn("Z:\\", chosen)
        self.assertNotIn("G:\\", chosen)
        self.assertNotIn("H:\\", chosen)
        self.assertNotIn("R:\\", chosen)

    def test_system_drive_is_not_a_full_disk_root(self) -> None:
        self.assertEqual(normalize_drive_root(r"C:\Windows"), "C:\\")
        self.assertEqual(normalize_drive_root("c:"), "C:\\")
        self.assertEqual(normalize_drive_root("E:/"), "E:\\")
        chosen = select_drive_roots(
            [DriveInfo("C:\\", DRIVE_FIXED, "OS", True), DriveInfo("E:\\", DRIVE_REMOVABLE, "STICK", True)],
            system_drive="C:",
        )
        self.assertEqual([root for root, _tier in chosen], ["E:\\"])
        without_system = select_drive_roots(
            [DriveInfo("C:\\", DRIVE_FIXED, "OS", True), DriveInfo("E:\\", DRIVE_REMOVABLE, "STICK", True)],
            system_drive="",
        )
        self.assertEqual([root for root, _tier in without_system], ["E:\\"])

    def test_cdrom_is_skipped(self) -> None:
        chosen = select_drive_roots(
            [DriveInfo("F:\\", DRIVE_CDROM, "DVD", True)],
            system_drive="C:\\",
            index_network=True,
        )
        self.assertEqual(chosen, [])

    def test_exclude_drives_honored(self) -> None:
        chosen = {
            root
            for root, _tier in select_drive_roots(
                self._sample_drives(),
                system_drive=r"C:\Windows",
                index_network=False,
                exclude=["e:/", "DATA"],
            )
        }
        self.assertNotIn("E:\\", chosen)
        self.assertNotIn("D:\\", chosen)
        self.assertEqual(exclude_drive_list({}), [])
        self.assertEqual(exclude_drive_list({"exclude_drives": [" E:\\ ", 3, ""]}), ["E:\\"])

    def test_drive_f_fixed_removable_and_mapped_root(self) -> None:
        fixed = dict(
            select_drive_roots(
                [
                    DriveInfo("C:\\", DRIVE_FIXED, "OS", True),
                    DriveInfo("F:\\", DRIVE_FIXED, "DATA", True),
                ],
                system_drive="C:\\",
                index_network=False,
            )
        )
        self.assertEqual(fixed.get("F:\\"), 1)
        self.assertNotIn("C:\\", fixed)
        removable = dict(
            select_drive_roots(
                [DriveInfo("F:\\", DRIVE_REMOVABLE, "STICK", True)],
                system_drive="C:\\",
                index_network=False,
            )
        )
        self.assertEqual(removable.get("F:\\"), 1)
        mapped = [DriveInfo("F:\\", DRIVE_REMOTE, "SHARE", True)]
        self.assertEqual(select_drive_roots(mapped, system_drive="C:\\", index_network=False), [])
        self.assertEqual(
            shallow_remote_roots(mapped, system_drive="C:\\", index_network=False),
            [("F:\\", 2)],
        )
        self.assertEqual(
            shallow_remote_roots(mapped, system_drive="C:\\", index_network=False, exclude=["F:\\"]),
            [],
        )
        self.assertEqual(shallow_remote_roots(mapped, system_drive="C:\\", index_network=True), [])
        self.assertEqual(
            select_drive_roots(mapped, system_drive="C:\\", index_network=True),
            [("F:\\", 2)],
        )
        self.assertEqual(
            shallow_remote_roots(
                [DriveInfo("Y:\\", DRIVE_REMOTE, None, False)],
                system_drive="C:\\",
                index_network=False,
            ),
            [],
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "F"
            folder = root / "Xchange"
            folder.mkdir(parents=True)
            (folder / "deep.txt").write_text("zweiteebene\n", encoding="utf-8")
            (root / "readme.txt").write_text("nurwurzel\n", encoding="utf-8")
            index = Index(Path(tmp) / "index.db")
            try:
                crawler = Crawler(
                    index,
                    Governor(fast=True),
                    [(str(root), 2)],
                    threading.Event(),
                    content=True,
                    index_path=False,
                    shallow_roots=[str(root)],
                )
                crawler.prime()
                crawler.drain()
                self.assertIn("Xchange", _names(index, "Xchange"))
                self.assertNotIn("deep.txt", _names(index, "deep"))
                self.assertFalse(_names(index, "zweiteebene"))
                self.assertIn("readme.txt", _names(index, "readme"))
                self.assertFalse(_names(index, "nurwurzel"))
                self.assertEqual(crawler.readdirs, 1)
            finally:
                index.close()

    def test_fixed_nonsystem_drive_is_recursive_mapped_stays_one_level(self) -> None:
        drives = [
            DriveInfo("C:\\", DRIVE_FIXED, "Windows", True),
            DriveInfo("D:\\", DRIVE_FIXED, "DATA", True),
            DriveInfo("Z:\\", DRIVE_REMOTE, "NAS", True),
        ]
        full = dict(select_drive_roots(drives, system_drive="C:\\", index_network=False))
        shallow = dict(shallow_remote_roots(drives, system_drive="C:\\", index_network=False))
        self.assertEqual(full.get("D:\\"), 1)
        self.assertNotIn("C:\\", full)
        self.assertNotIn("Z:\\", full)
        self.assertNotIn("D:\\", shallow)
        self.assertEqual(shallow.get("Z:\\"), 2)
        self.assertFalse(
            should_sample_content(enabled=True, tier=1, offline=False, names_only=True)
        )
        with tempfile.TemporaryDirectory() as tmp:
            fixed = Path(tmp) / "D"
            nested = fixed / "Ebene1" / "Ebene2"
            nested.mkdir(parents=True)
            (nested / "Budget-Johnson.txt").write_text("xqcontenttoken festplatte\n", encoding="utf-8")
            mapped = Path(tmp) / "Z"
            (mapped / "Ordner").mkdir(parents=True)
            (mapped / "Sichtbar.txt").write_text("xqcontenttoken netz\n", encoding="utf-8")
            (mapped / "Ordner" / "Versteckt.txt").write_text("xqcontenttoken tief\n", encoding="utf-8")
            index = Index(Path(tmp) / "index.db")
            try:
                crawler = Crawler(
                    index,
                    Governor(fast=True),
                    [(str(fixed), 1), (str(mapped), 2)],
                    threading.Event(),
                    content=True,
                    index_path=False,
                    names_only=[str(fixed), str(mapped)],
                    shallow_roots=[str(mapped)],
                )
                crawler.prime()
                crawler.drain()
                stored = {row[0] for row in index.con.execute("SELECT name FROM items")}
                self.assertIn("Budget-Johnson.txt", stored)
                self.assertIn("Ebene2", stored)
                self.assertIn("Ebene1", stored)
                self.assertIn("Sichtbar.txt", stored)
                self.assertIn("Ordner", stored)
                self.assertNotIn("Versteckt.txt", stored)
                self.assertIn("Budget-Johnson.txt", _names(index, "Budget-Johnson"))
                self.assertIn("Ebene2", _names(index, "Ebene2"))
                self.assertNotIn("Versteckt", _names(index, "Versteckt"))
                self.assertFalse(_names(index, "xqcontenttoken"))
                self.assertEqual(index.con.execute("SELECT COUNT(*) FROM content").fetchone()[0], 0)
                self.assertTrue(index.knows_dir(norm(nested)))
                self.assertTrue(index.knows_dir(norm(fixed / "Ebene1")))
                self.assertEqual(crawler.readdirs, 4)
            finally:
                index.close()

    def test_slow_drive_probe_is_skipped(self) -> None:
        started = time.perf_counter()

        def hang(_path: str) -> bool:
            time.sleep(1)
            return True

        self.assertFalse(answers_quickly(r"F:\slow-probe", timeout=0.05, probe=hang))
        self.assertLess(time.perf_counter() - started, 0.4)
        again = time.perf_counter()
        self.assertFalse(answers_quickly(r"F:\slow-probe", timeout=0.05, probe=lambda _path: True))
        self.assertLess(time.perf_counter() - again, 0.2)

    def test_index_network_defaults_to_skip_remote(self) -> None:
        self.assertFalse(index_network_enabled({}))
        self.assertFalse(index_network_enabled({"index_network": False}))
        quiet = {
            root: tier
            for root, tier in select_drive_roots(
                self._sample_drives(),
                system_drive="C:\\",
            )
        }
        self.assertNotIn("Z:\\", quiet)
        self.assertNotIn("Y:\\", quiet)
        enabled = {
            root: tier
            for root, tier in select_drive_roots(
                self._sample_drives(),
                system_drive="C:\\",
                index_network=True,
            )
        }
        self.assertEqual(enabled["Z:\\"], 2)
        self.assertNotIn("Y:\\", enabled)
        tracked = {
            root: (tier, walk)
            for root, tier, walk in tracked_drives(
                self._sample_drives(),
                system_drive=r"C:\Windows",
                index_network=True,
            )
        }
        self.assertEqual(tracked["H:\\"], (1, False))
        self.assertEqual(tracked["G:\\"], (1, False))
        self.assertEqual(tracked["Y:\\"], (2, False))
        self.assertNotIn("F:\\", tracked)
        self.assertNotIn("C:\\", tracked)
        self.assertFalse(should_sample_content(enabled=True, tier=2, offline=False))
        self.assertTrue(should_sample_content(enabled=True, tier=1, offline=False))
        self.assertTrue(index_network_enabled({"index_network": True}))

    def test_cloud_roots_added_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            one = home / "OneDrive"
            desktop = one / "Desktop"
            desktop.mkdir(parents=True)
            drop = home / "Dropbox"
            drop.mkdir()
            biz = home / "DropboxBiz"
            biz.mkdir()
            gdrive = home / "Google Drive"
            my_drive = gdrive / "My Drive"
            my_drive.mkdir(parents=True)
            appdata = home / "Roaming"
            local = home / "Local"
            (appdata / "Dropbox").mkdir(parents=True)
            (local / "Dropbox").mkdir(parents=True)
            info = {
                "personal": {"path": str(drop)},
                "business": {"path": str(biz)},
            }
            (appdata / "Dropbox" / "info.json").write_text(json.dumps(info), encoding="utf-8")
            (local / "Dropbox" / "info.json").write_text(
                json.dumps({"personal": {"path": str(drop)}}),
                encoding="utf-8",
            )
            drivefs = local / "Google" / "DriveFS" / "99" / "My Drive"
            drivefs.mkdir(parents=True)
            env = {
                "USERPROFILE": str(home),
                "APPDATA": str(appdata),
                "LOCALAPPDATA": str(local),
                "OneDrive": str(one),
                "OneDriveConsumer": str(one),
                "OneDriveCommercial": str(home / "fehlt"),
            }

            def read_text(path: str) -> str | None:
                if not os.path.isfile(path):
                    return None
                return Path(path).read_text(encoding="utf-8")

            found = discover_cloud_roots(
                env,
                exists=os.path.isdir,
                read_text=read_text,
                registry_folders=[str(one), str(one)],
                listdir=os.listdir,
                existing_roots=[str(desktop)],
            )
            keys = set(found)
            self.assertEqual(len(found), len(keys))
            self.assertIn(place_key(one), keys)
            self.assertEqual(found.count(place_key(one)), 1)
            self.assertIn(place_key(drop), keys)
            self.assertEqual(found.count(place_key(drop)), 1)
            self.assertIn(place_key(biz), keys)
            self.assertIn(place_key(gdrive), keys)
            self.assertNotIn(place_key(my_drive), keys)
            self.assertIn(place_key(drivefs), keys)
            self.assertNotIn(place_key(desktop), keys)
            self.assertTrue(all("fehlt" not in path for path in found))
            again = discover_cloud_roots(
                env,
                exists=os.path.isdir,
                read_text=read_text,
                registry_folders=[str(one)],
                listdir=os.listdir,
                existing_roots=[str(one)],
            )
            self.assertNotIn(place_key(one), again)

            link = home / "link"
            link.symlink_to(one, target_is_directory=True)
            merged = dedupe_roots([(str(link), 1), (str(one), 0)])
            self.assertEqual(len(merged), 1)
            self.assertEqual(merged[0][1], 0)
            roots, dynamic = merge_volume_roots([], [(str(one), 1)], [str(link)])
            self.assertEqual(len(roots), 1)
            self.assertEqual(dynamic, [roots[0][0]])

    def test_offline_attribute_skips_content(self) -> None:
        class Stat:
            def __init__(self, attrs: int) -> None:
                self.st_file_attributes = attrs

        self.assertTrue(is_offline_stat(Stat(FILE_ATTRIBUTE_OFFLINE)))
        self.assertTrue(is_offline_stat(Stat(FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS)))
        self.assertTrue(is_offline_stat(Stat(FILE_ATTRIBUTE_OFFLINE | 0x20)))
        self.assertFalse(is_offline_stat(Stat(0x20)))
        self.assertFalse(is_offline_stat(Stat(0)))
        self.assertFalse(should_sample_content(enabled=True, tier=1, offline=True))

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cloud"
            root.mkdir()
            (root / "wolke.txt").write_text("einzigartigerplatzhalter\n", encoding="utf-8")
            (root / "sichtbar.txt").write_text("sichtbarerinhalt\n", encoding="utf-8")
            marker = root / ".flare-offline"
            marker.mkdir()
            (marker / "wolke.txt").write_text("", encoding="utf-8")
            index = Index(Path(tmp) / "index.db")
            try:
                crawler = Crawler(
                    index,
                    Governor(fast=True),
                    [(str(root), 1)],
                    threading.Event(),
                    content=True,
                    index_path=False,
                )
                crawler.prime()
                crawler.drain()
                self.assertIn("wolke.txt", _names(index, "wolke"))
                self.assertFalse(_names(index, "einzigartigerplatzhalter"))
                self.assertTrue(_names(index, "sichtbarerinhalt"))
            finally:
                index.close()

    def test_network_tier_indexes_names_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "nas"
            root.mkdir()
            (root / "freigabe.txt").write_text("netzinhaltgeheim\n", encoding="utf-8")
            index = Index(Path(tmp) / "index.db")
            try:
                crawler = Crawler(
                    index,
                    Governor(fast=True),
                    [(str(root), 2)],
                    threading.Event(),
                    content=True,
                    index_path=False,
                )
                crawler.prime()
                crawler.drain()
                self.assertIn("freigabe.txt", _names(index, "freigabe"))
                self.assertFalse(_names(index, "netzinhaltgeheim"))
            finally:
                index.close()

    def test_removing_a_drive_drops_its_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stick = Path(tmp) / "E"
            nested = stick / "nested"
            nested.mkdir(parents=True)
            (stick / "foto.txt").write_text("bildwort\n", encoding="utf-8")
            (nested / "deep.txt").write_text("tief\n", encoding="utf-8")
            (stick / ".env").write_text("TOKEN=1\n", encoding="utf-8")
            modules = stick / "node_modules"
            modules.mkdir()
            (modules / "pkg.js").write_text("nope\n", encoding="utf-8")
            docs = Path(tmp) / "docs"
            docs.mkdir()
            (docs / "bleib.txt").write_text("aktenzeichen\n", encoding="utf-8")
            state = {"drives": [(str(stick), 1)]}

            def poll() -> list[tuple[str, int]]:
                return list(state["drives"])

            index = Index(Path(tmp) / "index.db")
            try:
                crawler = Crawler(
                    index,
                    Governor(fast=True),
                    [(str(docs), 1), (str(stick), 1)],
                    threading.Event(),
                    content=True,
                    index_path=False,
                    drive_poll=poll,
                    dynamic_roots=[str(stick)],
                )
                crawler.prime()
                crawler.drain()
                self.assertIn("foto.txt", _names(index, "foto"))
                self.assertIn("deep.txt", _names(index, "deep"))
                self.assertTrue(crawler.hides_content(norm(stick)))
                self.assertFalse(crawler.hides_content(norm(docs)))
                bild = search(index, Ranker(allow_cuda=False), "bildwort")["results"]
                self.assertFalse(any(hit.get("via") == "content" for hit in bild), bild)
                bleib = search(index, Ranker(allow_cuda=False), "aktenzeichen")["results"]
                self.assertTrue(
                    any(hit["name"] == "bleib.txt" and hit["via"] == "content" for hit in bleib),
                    bleib,
                )
                self.assertIn("bleib.txt", _names(index, "bleib"))
                self.assertFalse(_names(index, ".env"))
                self.assertFalse(_names(index, "pkg.js"))
                index.drop_tree(os.sep)
                self.assertIn("foto.txt", _names(index, "foto"))
                self.assertIn("bleib.txt", _names(index, "bleib"))
                state["drives"] = [(str(stick), 1, False)]
                crawler.poll_drives(force=True)
                self.assertIn("foto.txt", _names(index, "foto"))
                self.assertIn("deep.txt", _names(index, "deep"))
                state["drives"] = []
                crawler.poll_drives(force=True)
                self.assertFalse(_names(index, "foto"))
                self.assertFalse(_names(index, "deep"))
                self.assertFalse(_names(index, "bildwort"))
                self.assertIsNone(index.dir_info(norm(stick))[0])
                self.assertIsNone(index.dir_info(norm(nested))[0])
                self.assertIn("bleib.txt", _names(index, "bleib"))
                state["drives"] = [(str(stick), 1)]
                crawler.poll_drives(force=True)
                crawler.drain()
                self.assertIn("foto.txt", _names(index, "foto"))
                self.assertIn("deep.txt", _names(index, "deep"))
            finally:
                index.close()

    def test_drive_poll_is_spaced(self) -> None:
        self.assertGreaterEqual(DRIVE_POLL_S, 10)
        self.assertLessEqual(DRIVE_POLL_S, 15)
        calls = {"n": 0}

        def poll() -> list[tuple[str, int]]:
            calls["n"] += 1
            return []

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "docs"
            root.mkdir()
            index = Index(Path(tmp) / "index.db")
            try:
                crawler = Crawler(
                    index,
                    Governor(fast=True),
                    [(str(root), 1)],
                    threading.Event(),
                    index_path=False,
                    drive_poll=poll,
                )
                crawler.poll_drives()
                crawler.poll_drives()
                self.assertEqual(calls["n"], 1)
                crawler.poll_drives(force=True)
                self.assertEqual(calls["n"], 2)

                def boom() -> list[tuple[str, int]]:
                    raise OSError("laufwerk")

                crawler._drive_poll = boom
                crawler.poll_drives(force=True)
                self.assertEqual(calls["n"], 2)
            finally:
                index.close()

    def test_child_prefix_does_not_double_a_drive_root(self) -> None:
        self.assertEqual(prefix_with_sep("E:\\", "\\"), "E:\\")
        self.assertTrue("E:\\foto".startswith(prefix_with_sep("E:\\", "\\")))
        self.assertEqual(prefix_with_sep("C:\\Users\\me", "\\"), "C:\\Users\\me\\")
        self.assertFalse("C:\\Users\\meter".startswith(prefix_with_sep("C:\\Users\\me", "\\")))
        self.assertTrue(is_inside(os.path.join(tempfile.gettempdir(), "a", "b"), os.path.join(tempfile.gettempdir(), "a")))

    def test_win32_helpers_stay_quiet_off_windows(self) -> None:
        import sys

        if sys.platform == "win32":
            return
        self.assertEqual(list_windows_drives(), [])
        self.assertEqual(windows_cloud_roots(), [])
        self.assertEqual(drive_roots_for_config(), [])
        self.assertEqual(read_onedrive_folders(), [])
        self.assertEqual(windows_system_drive(), "")

    def test_external_and_cloud_roots_are_names_only(self) -> None:
        self.assertFalse(should_sample_content(enabled=True, tier=1, offline=False, names_only=True))
        self.assertTrue(should_sample_content(enabled=True, tier=1, offline=False))
        self.assertFalse(index_network_enabled({}))
        self.assertFalse(index_network_enabled(None))
        self.assertEqual(RESCHEDULE[1], 300.0)
        watched = roots_worth_watching(
            [("/home/me/Dokumente", 1), ("/mnt/usb", 1), ("/home/me/OneDrive", 1)],
            ["/mnt/usb", "/home/me/OneDrive"],
        )
        self.assertEqual(watched, ["/home/me/Dokumente"])
        with tempfile.TemporaryDirectory() as tmp:
            external = Path(tmp) / "usb"
            cloud = Path(tmp) / "OneDrive"
            known = Path(tmp) / "Dokumente"
            for folder in (external, cloud, known):
                folder.mkdir()
            (external / "stick.txt").write_text("usbinhaltgeheim\n", encoding="utf-8")
            (cloud / "wolke.txt").write_text("cloudinhaltgeheim\n", encoding="utf-8")
            (known / "notiz.txt").write_text("sonderakte\n", encoding="utf-8")
            index = Index(Path(tmp) / "index.db")
            try:
                crawler = Crawler(
                    index,
                    Governor(fast=True),
                    [(str(external), 1), (str(cloud), 1), (str(known), 1)],
                    threading.Event(),
                    content=True,
                    index_path=False,
                    dynamic_roots=[str(external)],
                    names_only=[str(cloud)],
                )
                self.assertEqual(dict(crawler.roots)[norm(external)], 1)
                self.assertTrue(crawler.hides_content(norm(external / "stick.txt")))
                self.assertTrue(crawler.hides_content(norm(cloud)))
                self.assertFalse(crawler.hides_content(norm(known)))
                crawler.prime()
                crawler.drain()
                self.assertIn("stick.txt", _names(index, "stick"))
                self.assertIn("wolke.txt", _names(index, "wolke"))
                self.assertIn("notiz.txt", _names(index, "notiz"))
                usb = search(index, Ranker(allow_cuda=False), "usbinhaltgeheim")["results"]
                cloud_hits = search(index, Ranker(allow_cuda=False), "cloudinhaltgeheim")["results"]
                known_hits = search(index, Ranker(allow_cuda=False), "sonderakte")["results"]
                self.assertFalse(any(hit.get("via") == "content" for hit in usb), usb)
                self.assertFalse(any(hit.get("via") == "content" for hit in cloud_hits), cloud_hits)
                self.assertTrue(
                    any(hit["name"] == "notiz.txt" and hit["via"] == "content" for hit in known_hits),
                    known_hits,
                )
            finally:
                index.close()

    def test_governor_duty_stays_light(self) -> None:
        import inspect

        import flare.crawl as crawl
        import flare.service as service
        import flare.volumes as volumes

        gov = Governor(duty=0.35)
        self.assertEqual(gov.base_duty, 0.35)
        self.assertEqual(gov.boost_seconds, 20.0)
        self.assertEqual(gov.duty, 0.85)
        gov.started = time.perf_counter() - 21
        self.assertEqual(gov.duty, 0.35)
        self.assertEqual(RESCHEDULE[1], 300.0)
        for module in (crawl, service, volumes):
            self.assertNotIn("lower_background_thread(", inspect.getsource(module))

    def test_backup_roundtrip_keeps_the_live_index(self) -> None:
        import io
        from contextlib import redirect_stdout

        from flare.cli import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "docs"
            root.mkdir()
            (root / "merkname.txt").write_text("merklich\n", encoding="utf-8")
            data = Path(tmp) / "data"
            data.mkdir()
            db = data / "index.db"
            index = Index(db)
            dest = Path(tmp) / "kopie" / "flare-index.db"
            try:
                crawler = Crawler(
                    index,
                    Governor(fast=True),
                    [(str(root), 1)],
                    threading.Event(),
                    content=True,
                    index_path=False,
                )
                crawler.prime()
                crawler.drain()
                self.assertIn("merkname.txt", _names(index, "merkname"))
                with self.assertRaises(ValueError):
                    index.backup(db)
                saved = index.backup(dest)
                self.assertEqual(Path(saved), dest)
                self.assertTrue(db.exists())
                self.assertTrue(dest.exists())
            finally:
                index.close()
            live = Index(db)
            copy = Index(dest, readonly=True)
            try:
                self.assertIn("merkname.txt", _names(live, "merkname"))
                self.assertIn("merkname.txt", _names(copy, "merkname"))
            finally:
                live.close()
                copy.close()
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["--data-dir", str(data), "index-save", str(Path(tmp) / "cli.db")])
            self.assertEqual(code, 0)
            self.assertIn("cli.db", out.getvalue())
            via_cli = Index(Path(tmp) / "cli.db", readonly=True)
            try:
                self.assertIn("merkname.txt", _names(via_cli, "merkname"))
            finally:
                via_cli.close()
            self.assertTrue(db.exists())
            missing = main(
                ["--data-dir", str(Path(tmp) / "leer"), "index-save", str(Path(tmp) / "kein.db")]
            )
            self.assertEqual(missing, 1)

    def test_indexer_does_not_lower_the_thread_or_read_wstring(self) -> None:
        import inspect

        import flare.crawl as crawl
        import flare.service as service
        import flare.volumes as volumes

        import flare.window as window

        for module in (crawl, service, volumes, window):
            source = inspect.getsource(module)
            self.assertNotIn("wstring_at", source)
            self.assertNotIn("lower_background_thread", source)


def _seed_index(path: Path, rows: list[tuple[str, int, int]]) -> None:
    index = Index(path)
    try:
        for item_path, size, mtime in rows:
            name = Path(item_path).name
            index.con.execute(
                """
                INSERT INTO items(kind, name, name_fold, path, dir, ext, mtime_ns, size, tier)
                VALUES ('file', ?, ?, ?, ?, '.txt', ?, ?, 1)
                """,
                (name, name.casefold(), item_path, str(Path(item_path).parent), mtime, size),
            )
        index.con.commit()
    finally:
        index.close()


class IndexCopyCompareTests(unittest.TestCase):
    def test_copy_roundtrip_keeps_the_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "quelle.db"
            dest = Path(tmp) / "kopie" / "ziel.db"
            _seed_index(source, [("/docs/merkname.txt", 12, 40)])
            saved = copy_index(source, dest)
            self.assertEqual(Path(saved), dest)
            self.assertTrue(source.is_file())
            self.assertTrue(dest.is_file())
            live = Index(source, readonly=True)
            copy = Index(dest, readonly=True)
            try:
                self.assertIn("merkname.txt", _names(live, "merkname"))
                self.assertIn("merkname.txt", _names(copy, "merkname"))
            finally:
                live.close()
                copy.close()

    def test_copy_onto_the_same_path_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "quelle.db"
            _seed_index(source, [("/docs/bleibt.txt", 4, 8)])
            before = source.read_bytes()
            with self.assertRaises(ValueError):
                copy_index(source, source)
            self.assertEqual(source.read_bytes(), before)
            live = Index(source, readonly=True)
            try:
                self.assertIn("bleibt.txt", _names(live, "bleibt"))
            finally:
                live.close()

    def test_compare_identical_indexes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            left = Path(tmp) / "a.db"
            right = Path(tmp) / "b.db"
            rows = [("/docs/gleich.txt", 3, 9), ("/docs/auch.txt", 5, 11)]
            _seed_index(left, rows)
            saved = copy_index(left, right)
            report = compare_indexes(left, saved)
            self.assertEqual(report["count_a"], 2)
            self.assertEqual(report["count_b"], 2)
            self.assertEqual(report["only_a"], 0)
            self.assertEqual(report["only_b"], 0)
            self.assertEqual(report["changed"], 0)
            self.assertEqual(report["only_a_paths"], [])
            self.assertEqual(report["only_b_paths"], [])
            self.assertEqual(report["changed_paths"], [])

    def test_compare_counts_added_removed_and_changed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            left = Path(tmp) / "a.db"
            right = Path(tmp) / "b.db"
            only_a = [(f"/nur-a/{index:02d}.txt", 1, 1) for index in range(21)]
            only_b = [(f"/nur-b/{index:02d}.txt", 1, 1) for index in range(21)]
            changed_a = [(f"/anders/{index:02d}.txt", 1, 10) for index in range(21)]
            changed_b = [(f"/anders/{index:02d}.txt", 9, 10) for index in range(21)]
            same = [("/gleich/bleibt.txt", 4, 4)]
            _seed_index(left, only_a + changed_a + same)
            _seed_index(right, only_b + changed_b + same)
            report = compare_indexes(left, right)
            self.assertEqual(report["count_a"], 43)
            self.assertEqual(report["count_b"], 43)
            self.assertEqual(report["only_a"], 21)
            self.assertEqual(report["only_b"], 21)
            self.assertEqual(report["changed"], 21)
            self.assertEqual(len(report["only_a_paths"]), 20)
            self.assertEqual(len(report["only_b_paths"]), 20)
            self.assertEqual(len(report["changed_paths"]), 20)
            self.assertNotIn("/nur-a/20.txt", report["only_a_paths"])
            self.assertIn("/nur-a/00.txt", report["only_a_paths"])
            self.assertIn("/anders/00.txt", report["changed_paths"])
            self.assertNotIn("/gleich/bleibt.txt", report["changed_paths"])

    def test_cli_copy_and_compare(self) -> None:
        import io
        from contextlib import redirect_stderr, redirect_stdout

        from flare.cli import main

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "quelle.db"
            dest = Path(tmp) / "ziel.db"
            _seed_index(source, [("/docs/merkname.txt", 12, 40)])
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["index-copy", str(source), str(dest)])
            self.assertEqual(code, 0)
            self.assertIn(str(dest), out.getvalue())
            self.assertTrue(source.is_file())
            report_out = io.StringIO()
            with redirect_stdout(report_out):
                compared = main(["index-compare", str(source), str(dest)])
            self.assertEqual(compared, 0)
            text = report_out.getvalue()
            self.assertIn("Nur in A: 0", text)
            self.assertIn("Nur in B: 0", text)
            self.assertIn("Geändert: 0", text)
            err = io.StringIO()
            with redirect_stderr(err):
                missing = main(["index-compare", str(Path(tmp) / "fehlt.db"), str(dest)])
            self.assertEqual(missing, 1)
            self.assertIn("Index fehlt", err.getvalue())
            self.assertNotIn("Traceback", err.getvalue())
            empty = Path(tmp) / "leer.db"
            import sqlite3

            sqlite3.connect(empty).close()
            err_empty = io.StringIO()
            with redirect_stderr(err_empty):
                bare = main(["index-compare", str(empty), str(dest)])
            self.assertEqual(bare, 1)
            self.assertIn("ohne Tabelle", err_empty.getvalue())
            self.assertNotIn("Traceback", err_empty.getvalue())


class IndexLoadTests(unittest.TestCase):
    def test_load_replaces_live_items_and_keeps_the_snapshot(self) -> None:
        import io
        from contextlib import redirect_stderr, redirect_stdout

        from flare.cli import main
        from flare.store import replace_live_index

        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            data.mkdir()
            live = data / "index.db"
            snap = Path(tmp) / "kopie" / "flare-index.db"
            _seed_index(live, [("/docs/altname.txt", 3, 5), ("/docs/weg.txt", 4, 6)])
            _seed_index(snap, [("/docs/geladen.txt", 9, 11)])
            snap_bytes = snap.read_bytes()
            index = Index(live)
            try:
                self.assertEqual(
                    {row["name"] for row in index.names._rows.values()},
                    {"altname.txt", "weg.txt"},
                )
                index.con.execute(
                    """
                    INSERT INTO items(kind, name, name_fold, path, dir, ext, mtime_ns, size, tier)
                    VALUES ('file', 'nurwal.txt', 'nurwal.txt', '/docs/nurwal.txt', '/docs', '.txt', 1, 1, 1)
                    """
                )
                index.con.commit()
                wal = live.with_name(live.name + "-wal")
                self.assertTrue(wal.is_file())
                self.assertGreater(wal.stat().st_size, 0)
                replaced = replace_live_index(index, snap)
                self.assertEqual(Path(replaced), live)
                names = {row["name"] for row in index.names._rows.values()}
                self.assertEqual(names, {"geladen.txt"})
                self.assertEqual(index.counts()["items"], 1)
                self.assertIn("geladen.txt", _names(index, "geladen"))
                self.assertNotIn("altname.txt", _names(index, "altname"))
                self.assertNotIn("nurwal.txt", _names(index, "nurwal"))
            finally:
                index.close()
            self.assertTrue(snap.is_file())
            self.assertEqual(snap.read_bytes(), snap_bytes)
            again = Index(live, readonly=True)
            copy = Index(snap, readonly=True)
            try:
                self.assertEqual(again.counts()["items"], 1)
                self.assertIn("geladen.txt", _names(again, "geladen"))
                self.assertNotIn("altname.txt", _names(again, "altname"))
                self.assertIn("geladen.txt", _names(copy, "geladen"))
                self.assertNotIn("altname.txt", _names(copy, "altname"))
            finally:
                again.close()
                copy.close()
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["--data-dir", str(data), "index-load", str(snap)])
            self.assertEqual(code, 0)
            self.assertIn(str(live), out.getvalue())
            self.assertEqual(snap.read_bytes(), snap_bytes)
            via_cli = Index(live, readonly=True)
            try:
                self.assertIn("geladen.txt", _names(via_cli, "geladen"))
                self.assertEqual(via_cli.counts()["items"], 1)
            finally:
                via_cli.close()

    def test_load_rejects_a_non_index_without_changing_the_live_database(self) -> None:
        import io
        import sqlite3
        from contextlib import redirect_stderr

        from flare.cli import main
        from flare.store import replace_live_index

        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            data.mkdir()
            live = data / "index.db"
            _seed_index(live, [("/docs/bleibt.txt", 2, 7)])
            before = live.read_bytes()
            wal = live.with_name(live.name + "-wal")
            shm = live.with_name(live.name + "-shm")
            wal_before = wal.read_bytes() if wal.is_file() else None
            shm_before = shm.read_bytes() if shm.is_file() else None
            fake = Path(tmp) / "kein.db"
            fake.write_text("das ist kein index\n", encoding="utf-8")
            empty = Path(tmp) / "leer.db"
            sqlite3.connect(empty).close()
            err = io.StringIO()
            with redirect_stderr(err):
                code = main(["--data-dir", str(data), "index-load", str(fake)])
            self.assertNotEqual(code, 0)
            self.assertIn("Laden fehlgeschlagen", err.getvalue())
            self.assertNotIn("Traceback", err.getvalue())
            self.assertEqual(live.read_bytes(), before)
            self.assertEqual(wal.read_bytes() if wal.is_file() else None, wal_before)
            self.assertEqual(shm.read_bytes() if shm.is_file() else None, shm_before)
            err_empty = io.StringIO()
            with redirect_stderr(err_empty):
                bare = main(["--data-dir", str(data), "index-load", str(empty)])
            self.assertNotEqual(bare, 0)
            self.assertIn("ohne Tabelle", err_empty.getvalue())
            self.assertNotIn("Traceback", err_empty.getvalue())
            self.assertEqual(live.read_bytes(), before)
            index = Index(live)
            try:
                remembered = {row["name"] for row in index.names._rows.values()}
                main_bytes = live.read_bytes()
                with self.assertRaises(ValueError):
                    replace_live_index(index, fake)
                self.assertEqual({row["name"] for row in index.names._rows.values()}, remembered)
                self.assertEqual(live.read_bytes(), main_bytes)
                self.assertIn("bleibt.txt", _names(index, "bleibt"))
            finally:
                index.close()
            self.assertTrue(fake.is_file())
            self.assertEqual(fake.read_text(encoding="utf-8"), "das ist kein index\n")

    def test_service_load_uses_the_open_index(self) -> None:
        from flare.store import replace_live_index

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "leer"
            root.mkdir()
            data = Path(tmp) / "data"
            snap = Path(tmp) / "snap.db"
            _seed_index(snap, [("/virtual/geladen.txt", 8, 8)])
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
            try:
                service.index.con.execute(
                    """
                    INSERT INTO items(kind, name, name_fold, path, dir, ext, mtime_ns, size, tier)
                    VALUES ('file', 'weg.txt', 'weg.txt', '/virtual/weg.txt', '/virtual', '.txt', 1, 1, 1)
                    """
                )
                service.index.con.commit()
                service.index._load_names()
                service.start()
                loaded = service.load_index_copy(str(snap))
                self.assertEqual(loaded, str(service.index.path))
                names = {row["name"] for row in service.index.names._rows.values()}
                self.assertEqual(names, {"geladen.txt"})
                self.assertTrue(snap.is_file())
                self.assertIn("geladen.txt", _names(service.index, "geladen"))
                self.assertNotIn("weg.txt", _names(service.index, "weg"))
            finally:
                service.shutdown()
            import inspect

            import flare.cli as cli
            import flare.service as service_mod

            self.assertIn("replace_live_index", inspect.getsource(service_mod.Service.load_index_copy))
            self.assertIn("load_index_at", inspect.getsource(cli._index_load))
            self.assertIn("replace_live_index", inspect.getsource(replace_live_index))
            self.assertNotIn("shutil", inspect.getsource(replace_live_index))


class CustomIndexTests(unittest.TestCase):
    def test_index_create_opens_as_an_empty_index(self) -> None:
        from flare.store import create_index

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "neu" / "ZIEL.db"
            live = Path(tmp) / "live.db"
            live.write_bytes(b"live-unveraendert")
            saved = create_index(dest)
            self.assertEqual(saved, dest)
            self.assertEqual(live.read_bytes(), b"live-unveraendert")
            index = Index(dest, readonly=True)
            try:
                self.assertEqual(index.counts(), {"items": 0, "dirs": 0})
            finally:
                index.close()

    def test_root_add_stores_names_not_content(self) -> None:
        from flare.crawl import collect_root_names
        from flare.store import add_names, create_index

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "akten"
            nested = root / "nest"
            hidden = root / ".geheim"
            modules = root / "node_modules"
            nested.mkdir(parents=True)
            hidden.mkdir()
            modules.mkdir()
            (root / "akte.txt").write_text("sonderakteinhalt\n", encoding="utf-8")
            (nested / "tief.txt").write_text("tief\n", encoding="utf-8")
            (root / ".env").write_text("TOKEN=1\n", encoding="utf-8")
            (hidden / "weg.txt").write_text("nein\n", encoding="utf-8")
            (modules / "pkg.js").write_text("nein\n", encoding="utf-8")
            alias = root / "alias.txt"
            os.symlink(root / "akte.txt", alias)
            dest = Path(tmp) / "ZIEL.db"
            create_index(dest)
            items = collect_root_names(root)
            self.assertTrue(all("text" not in item for item in items))
            add_names(dest, items)
            index = Index(dest, readonly=True)
            try:
                names = {row["name"] for row in index.con.execute("SELECT name FROM items")}
                self.assertIn("akte.txt", names)
                self.assertIn("tief.txt", names)
                self.assertNotIn(".env", names)
                self.assertNotIn("weg.txt", names)
                self.assertNotIn("pkg.js", names)
                linked = [
                    row[0]
                    for row in index.con.execute("SELECT path FROM items")
                    if row[0].endswith("akte.txt") or row[0].endswith("alias.txt")
                ]
                self.assertEqual(len(linked), 1)
                content = index.con.execute("SELECT COUNT(*) FROM content").fetchone()[0]
                self.assertEqual(content, 0)
            finally:
                index.close()
            self.assertNotIn(b"sonderakteinhalt", dest.read_bytes())

    def test_list_add_ignores_comments_and_missing_paths(self) -> None:
        from flare.crawl import collect_list_names
        from flare.store import add_names, create_index

        with tempfile.TemporaryDirectory() as tmp:
            present = Path(tmp) / "da.txt"
            present.write_text("nur-name\n", encoding="utf-8")
            missing = Path(tmp) / "fehlt.txt"
            listing = Path(tmp) / "LISTE.txt"
            listing.write_text(
                "\n# kommentar\n"
                f"{present}\n"
                f"{missing}\n"
                "   # auch ein kommentar\n",
                encoding="utf-8",
            )
            dest = Path(tmp) / "ZIEL.db"
            create_index(dest)
            items = collect_list_names(listing)
            self.assertEqual([item["name"] for item in items], ["da.txt"])
            add_names(dest, items)
            index = Index(dest, readonly=True)
            try:
                names = {row["name"] for row in index.con.execute("SELECT name FROM items")}
                self.assertEqual(names, {"da.txt"})
                self.assertEqual(index.con.execute("SELECT COUNT(*) FROM content").fetchone()[0], 0)
            finally:
                index.close()

    def test_second_add_keeps_paths_outside_the_root(self) -> None:
        from flare.crawl import collect_root_names
        from flare.paths import norm
        from flare.store import add_names, create_index

        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "eins"
            second = Path(tmp) / "zwei"
            first.mkdir()
            second.mkdir()
            (first / "bleib.txt").write_text("a\n", encoding="utf-8")
            (second / "neu.txt").write_text("b\n", encoding="utf-8")
            dest = Path(tmp) / "ZIEL.db"
            create_index(dest)
            add_names(dest, collect_root_names(first))
            add_names(dest, collect_root_names(second))
            index = Index(dest, readonly=True)
            try:
                names = {row["name"] for row in index.con.execute("SELECT name FROM items")}
                self.assertIn("bleib.txt", names)
                self.assertIn("neu.txt", names)
            finally:
                index.close()
            (second / "neu.txt").unlink()
            (second / "anders.txt").write_text("c\n", encoding="utf-8")
            add_names(dest, collect_root_names(second), prune_root=str(second))
            index = Index(dest, readonly=True)
            try:
                names = {row["name"] for row in index.con.execute("SELECT name FROM items")}
                self.assertIn("bleib.txt", names)
                self.assertIn("anders.txt", names)
                self.assertNotIn("neu.txt", names)
                bleib = index.con.execute(
                    "SELECT path FROM items WHERE name='bleib.txt'"
                ).fetchone()[0]
                self.assertTrue(bleib.startswith(norm(str(first))))
            finally:
                index.close()

    def test_query_index_does_not_need_the_live_directory(self) -> None:
        import io
        from contextlib import redirect_stderr, redirect_stdout

        from flare.cli import main
        from flare.client import Client

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "akten"
            root.mkdir()
            (root / "akte.txt").write_text("sonderakteinhalt\n", encoding="utf-8")
            dest = Path(tmp) / "ZIEL.db"
            out = io.StringIO()
            with redirect_stdout(out):
                created = main(["index-create", str(dest)])
                added = main(["index-add", str(dest), "--root", str(root)])
            self.assertEqual(created, 0, out.getvalue())
            self.assertEqual(added, 0, out.getvalue())
            self.assertFalse((Path(tmp) / "index.db").exists())
            found = io.StringIO()
            with redirect_stdout(found):
                code = main(["query", "--index", str(dest), "--similar", "akte"])
            self.assertEqual(code, 0)
            self.assertIn("akte.txt", found.getvalue())
            self.assertNotIn("sonderakteinhalt", found.getvalue())
            local = Client(Path(tmp) / "leer").search("akte", index=dest, similar=True)
            self.assertTrue(any(hit["name"] == "akte.txt" for hit in local["results"]), local)
            err = io.StringIO()
            with redirect_stderr(err):
                bad = main(["query", "--index", str(Path(tmp) / "fehlt.db"), "akte"])
            self.assertEqual(bad, 1)
            self.assertNotIn("Traceback", err.getvalue())
            self.assertIn("Index", err.getvalue())

    def test_query_index_rejects_a_non_index_file(self) -> None:
        import io
        from contextlib import redirect_stderr

        from flare.cli import main

        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "kein.db"
            fake.write_text("das ist kein index\n", encoding="utf-8")
            err = io.StringIO()
            with redirect_stderr(err):
                code = main(["query", "--index", str(fake), "akte"])
            self.assertNotEqual(code, 0)
            self.assertNotIn("Traceback", err.getvalue())
            self.assertIn("fehlgeschlagen", err.getvalue())

    def test_http_search_accepts_an_index_path(self) -> None:
        import json
        import urllib.error
        import urllib.parse
        import urllib.request

        from flare.cli import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "akten"
            root.mkdir()
            (root / "akte.txt").write_text("sonderakteinhalt\n", encoding="utf-8")
            dest = Path(tmp) / "ZIEL.db"
            import io
            from contextlib import redirect_stdout

            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(["index-create", str(dest)]), 0)
                self.assertEqual(main(["index-add", str(dest), "--root", str(root)]), 0)
            empty = Path(tmp) / "leer"
            empty.mkdir()
            service = Service(
                data_dir=Path(tmp) / "data",
                roots=[(str(empty), 1)],
                open_immediately=False,
                allow_ui=False,
                hotkey=False,
                watch=False,
                index_path=False,
                fast=True,
                port=0,
            )
            service.start()
            try:
                query = urllib.parse.urlencode({"q": "akte", "index": str(dest), "similar": "1"})
                with urllib.request.urlopen(service.url + "api/search?" + query, timeout=2) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                self.assertTrue(any(hit["name"] == "akte.txt" for hit in payload["results"]), payload)
                live = service.url + "api/search?" + urllib.parse.urlencode({"q": "2+2"})
                with urllib.request.urlopen(live, timeout=2) as response:
                    calc = json.loads(response.read().decode("utf-8"))
                self.assertEqual(calc["results"][0]["kind"], "calc")
                missing = service.url + "api/search?" + urllib.parse.urlencode(
                    {"q": "akte", "index": str(Path(tmp) / "fehlt.db")}
                )
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(missing, timeout=2)
                body = json.loads(caught.exception.read().decode("utf-8"))
                self.assertIn("error", body)
                fake = Path(tmp) / "kein.db"
                fake.write_text("kein index\n", encoding="utf-8")
                bad = service.url + "api/search?" + urllib.parse.urlencode(
                    {"q": "akte", "index": str(fake)}
                )
                with self.assertRaises(urllib.error.HTTPError):
                    urllib.request.urlopen(bad, timeout=2)
                with urllib.request.urlopen(service.url + "api/health", timeout=2) as response:
                    self.assertEqual(response.status, 200)
            finally:
                service.shutdown()


if __name__ == "__main__":
    unittest.main()
