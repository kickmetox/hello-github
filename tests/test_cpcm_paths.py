import tempfile
import unittest
from pathlib import Path

from cpcm.paths import World, from_canonical, identity_for_home, rewrite_text, to_canonical


class PathTests(unittest.TestCase):
    def test_roundtrip_known_folders_and_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            linux_home, windows_home = root / "linux", root / "windows"
            linux_home.mkdir()
            windows_home.mkdir()
            linux = identity_for_home(World.LINUX, linux_home, "ada")
            windows = identity_for_home(World.WINDOWS, windows_home, "ada")
            samples = {
                linux_home / "Documents" / "notes" / "a.txt": "documents/notes/a.txt",
                linux_home / ".config" / "app" / "cfg.json": "config/app/cfg.json",
                linux_home / ".local" / "share" / "app" / "state": "local/app/state",
                linux_home / ".bashrc": "home/.bashrc",
                linux_home / "Bilder" / "x.png": "pictures/x.png",
            }
            for path, canonical in samples.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("x", encoding="utf-8")
                self.assertEqual(to_canonical(path, linux), canonical)
                self.assertEqual(from_canonical(canonical, windows, allow_external=False), str(self._windows_target(windows_home, canonical)))

    def test_counterpart_windows_string_uses_backslashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes = Path(tmp) / "linux" / "Documents" / "notes" / "a.txt"
            notes.parent.mkdir(parents=True)
            notes.write_text("a", encoding="utf-8")
            linux = identity_for_home(World.LINUX, Path(tmp) / "linux", "ada")
            windows = identity_for_home(World.WINDOWS, Path(r"C:\Users\ada"), "ada")
            mapped = from_canonical(to_canonical(notes, linux), windows, allow_external=False)
            self.assertEqual(mapped, r"C:\Users\ada\Documents\notes\a.txt")

    def test_external_does_not_cross_worlds(self):
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp) / "outside" / "a.txt"
            outside.parent.mkdir()
            outside.write_text("a", encoding="utf-8")
            linux = identity_for_home(World.LINUX, Path(tmp) / "linux", "ada")
            windows = identity_for_home(World.WINDOWS, Path(tmp) / "windows", "ada")
            canonical = to_canonical(outside, linux)
            self.assertTrue(canonical.startswith("external/"))
            self.assertIsNone(from_canonical(canonical, windows, allow_external=False))

    def test_rejects_parent_segments(self):
        linux = identity_for_home(World.LINUX, Path("/home/ada"), "ada")
        self.assertIsNone(from_canonical("home/../../etc/passwd", linux, allow_external=False))

    def test_rewrite_text_swaps_home_and_documents(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = identity_for_home(World.LINUX, Path(tmp) / "linux", "ada")
            target = identity_for_home(World.WINDOWS, Path(tmp) / "windows", "ada")
            rewritten = rewrite_text(f"notes={source.home / 'Documents' / 'notes'}", source, target)
            self.assertIn(str(target.home / "Documents" / "notes"), rewritten)
            self.assertNotIn(str(source.home), rewritten)

    def _windows_target(self, home: Path, canonical: str) -> Path:
        head, _, rest = canonical.partition("/")
        mapping = {
            "documents": home / "Documents",
            "pictures": home / "Pictures",
            "config": home / "AppData" / "Roaming",
            "local": home / "AppData" / "Local",
            "home": home,
        }
        base = mapping[head]
        return base.joinpath(*rest.split("/")) if rest else base
