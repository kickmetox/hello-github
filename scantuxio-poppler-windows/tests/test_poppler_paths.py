#!/usr/bin/env python3
"""Smoke-Test für poppler_paths (ohne echte Poppler-Binaries)."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from poppler_paths import ensure_poppler, find_poppler, apply_poppler_env  # noqa: E402


class PopplerPathsTest(unittest.TestCase):
    def test_missing_is_not_ok(self):
        # Env leeren
        for k in ("SCANTUXIO_POPPLER", "POPPLER_PATH", "PDF2IMAGE_POPPLER_PATH"):
            os.environ.pop(k, None)
        info = find_poppler()
        # Auf Linux-CI kann system-poppler installiert sein — dann ok=True
        self.assertIsInstance(info.ok, bool)
        self.assertTrue(info.message)

    def test_bundle_layout(self):
        with tempfile.TemporaryDirectory() as td:
            bin_dir = Path(td) / "vendor" / "poppler" / "Library" / "bin"
            bin_dir.mkdir(parents=True)
            for name in ("pdftoppm", "pdfinfo"):
                exe = bin_dir / (name + (".exe" if os.name == "nt" else ""))
                exe.write_text("", encoding="utf-8")
                if os.name != "nt":
                    exe.chmod(0o755)
            os.environ["SCANTUXIO_POPPLER"] = str(bin_dir)
            info = ensure_poppler(required=False)
            self.assertTrue(info.ok, info.message)
            self.assertEqual(Path(info.poppler_path), bin_dir)
            apply_poppler_env(info)
            self.assertIn(str(bin_dir), os.environ.get("PATH", ""))


if __name__ == "__main__":
    unittest.main()
