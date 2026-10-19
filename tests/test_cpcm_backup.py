import json
import tempfile
import unittest
from pathlib import Path

from cpcm.backup import create_snapshot, export_snapshot, import_snapshot, restore_snapshot
from cpcm.paths import World, identity_for_home
from cpcm.selection import Selection, add_path


class BackupTests(unittest.TestCase):
    def test_backup_and_restore_across_worlds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            linux_home, windows_home, vault = root / "linux", root / "windows", root / "vault"
            notes = linux_home / "Documents" / "notes"
            notes.mkdir(parents=True)
            (notes / "a.txt").write_text("hallo", encoding="utf-8")
            (notes / "leer").mkdir()
            config = linux_home / ".config" / "app"
            config.mkdir(parents=True)
            source_path = str(linux_home / "Documents" / "notes")
            (config / "cfg.json").write_text(json.dumps({"p": source_path}), encoding="utf-8")
            (notes / "link.txt").symlink_to("a.txt")
            linux = identity_for_home(World.LINUX, linux_home, "ada")
            windows = identity_for_home(World.WINDOWS, windows_home, "ada")
            selection = Selection()
            add_path(selection, notes, linux, windows)
            add_path(selection, config, linux, windows)
            snapshot = create_snapshot(vault, selection, linux)
            report = restore_snapshot(vault, snapshot.id, windows, source=linux, translate_paths=True, allow_external=False)
            self.assertEqual((windows_home / "Documents" / "notes" / "a.txt").read_text(encoding="utf-8"), "hallo")
            self.assertTrue((windows_home / "Documents" / "notes" / "leer").is_dir())
            self.assertTrue((windows_home / "Documents" / "notes" / "link.txt").is_symlink())
            payload = json.loads((windows_home / "AppData" / "Roaming" / "app" / "cfg.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["p"], str(windows_home / "Documents" / "notes"))
            self.assertTrue(report.rewritten)

    def test_overwrite_keeps_previous_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            linux_home, windows_home, vault = root / "linux", root / "windows", root / "vault"
            notes = linux_home / "Documents"
            notes.mkdir(parents=True)
            (notes / "a.txt").write_text("neu", encoding="utf-8")
            target = windows_home / "Documents"
            target.mkdir(parents=True)
            (target / "a.txt").write_text("alt", encoding="utf-8")
            linux = identity_for_home(World.LINUX, linux_home, "ada")
            windows = identity_for_home(World.WINDOWS, windows_home, "ada")
            selection = Selection()
            add_path(selection, notes / "a.txt", linux, windows)
            snapshot = create_snapshot(vault, selection, linux)
            blocked = restore_snapshot(vault, snapshot.id, windows, allow_external=False)
            self.assertEqual((target / "a.txt").read_text(encoding="utf-8"), "alt")
            self.assertIn(str(target / "a.txt"), blocked.conflicts)
            report = restore_snapshot(vault, snapshot.id, windows, overwrite=True, allow_external=False)
            self.assertEqual((target / "a.txt").read_text(encoding="utf-8"), "neu")
            saved = list((vault / "pre-restore").rglob("a.txt"))
            self.assertEqual(saved[0].read_text(encoding="utf-8"), "alt")
            self.assertTrue(report.pre_restore)

    def test_zip_roundtrip_and_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home, vault, other = root / "home", root / "vault", root / "vault2"
            file = home / ".bashrc"
            file.parent.mkdir()
            file.write_text("export A=1\n", encoding="utf-8")
            linux = identity_for_home(World.LINUX, home, "ada")
            windows = identity_for_home(World.WINDOWS, Path(r"C:\Users\ada"), "ada")
            selection = Selection()
            add_path(selection, file, linux, windows)
            self.assertEqual(selection.items[0].paths["windows"], r"C:\Users\ada\.bashrc")
            snapshot = create_snapshot(vault, selection, linux)
            archive = root / "move.cpcm"
            export_snapshot(vault, snapshot.id, archive)
            imported = import_snapshot(other, archive)
            hostile = other / "snapshots" / imported / "manifest.json"
            raw = json.loads(hostile.read_text(encoding="utf-8"))
            raw["entries"].append({"canonical": "../outside.txt", "kind": "file", "source_path": "x", "payload": "../outside.txt", "sha256": "", "size": 0, "mode": 420, "mtime": 0, "link_target": ""})
            hostile.write_text(json.dumps(raw), encoding="utf-8")
            report = restore_snapshot(other, imported, linux, destination=root / "out", allow_external=False)
            self.assertIn("Unsicherer Speicherpfad", " ".join(item["reason"] for item in report.skipped))
            self.assertFalse((root / "outside.txt").exists())

    def test_symlink_loop_and_cache_do_not_grow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "docs"
            folder.mkdir()
            (folder / "a.txt").write_text("a", encoding="utf-8")
            (folder / "loop").symlink_to(folder, target_is_directory=True)
            cache = folder / "node_modules"
            cache.mkdir()
            (cache / "pkg.js").write_text("no", encoding="utf-8")
            linux = identity_for_home(World.LINUX, root, "ada")
            windows = identity_for_home(World.WINDOWS, Path(r"C:\Users\ada"), "ada")
            selection = Selection()
            add_path(selection, folder, linux, windows)
            snapshot = create_snapshot(root / "vault", selection, linux)
            files = [entry.canonical for entry in snapshot.entries if entry.kind == "file"]
            self.assertEqual(files, ["home/docs/a.txt"])

    def test_refuses_empty_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                create_snapshot(Path(tmp) / "vault", Selection(), identity_for_home(World.LINUX, Path(tmp), "ada"))
