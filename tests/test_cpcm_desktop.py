import tempfile
import unittest
from pathlib import Path

from cpcm.cli import main
from cpcm.desktop import Session


class DesktopTests(unittest.TestCase):
    def test_backup_restore_and_documents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            for name in ("HILFE.txt", "BEDIENUNGSANLEITUNG.rtf", "FEATURE-LISTE.rtf"):
                (root / "docs" / name).write_text(Path("/workspace/docs", name).read_text(encoding="utf-8"), encoding="utf-8")
            inbox = root / "inbox"
            inbox.mkdir()
            (inbox / "note.txt").write_text("fenster", encoding="utf-8")
            session = Session(root)
            session.add(str(inbox / "note.txt"))
            self.assertIn("Dateien: 1", session.backup())
            snapshot = session.snapshots()[0]["id"]
            report = session.restore(snapshot, overwrite=True, translate_paths=False, destination=str(root / "out"))
            self.assertIn("note.txt", report)
            restored = list((root / "out").rglob("note.txt"))
            self.assertEqual(restored[0].read_text(encoding="utf-8"), "fenster")
            self.assertIn("Andreas Meyer", session.help_text())
            self.assertIn("Bedienungsanleitung", session.manual_path().read_text(encoding="ascii"))
            self.assertIn("Feature-Liste", session.features_path().read_text(encoding="ascii"))
            self.assertTrue((Path("/workspace/docs/LINUX-BUILD.md")).is_file())

    def test_window_command_on_linux_stays_closed(self):
        self.assertEqual(main(["window"]), 0)
