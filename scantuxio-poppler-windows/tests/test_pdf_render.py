#!/usr/bin/env python3
"""Tests für pdf_render (ohne echte PDF-Datei / optional ohne pypdfium2)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from pdf_render import ensure_pdf_backend, probe_pdfium, warn_if_poppler_only_stack  # noqa: E402


class PdfRenderTest(unittest.TestCase):
    def test_probe_returns_info(self):
        info = probe_pdfium()
        self.assertIsInstance(info.ok, bool)
        self.assertTrue(info.message)

    def test_ensure_required_raises_without_module(self):
        with mock.patch("pdf_render._has_module", return_value=False):
            with self.assertRaises(ModuleNotFoundError):
                ensure_pdf_backend(required=True)
            info = ensure_pdf_backend(required=False)
            self.assertFalse(info.ok)

    def test_poppler_warning_when_pdf2image_only(self):
        def fake_has(name: str) -> bool:
            return name == "pdf2image"

        with mock.patch("pdf_render._has_module", side_effect=fake_has):
            with mock.patch("pdf_render.probe_pdfium") as probe:
                from pdf_render import PdfBackendInfo

                probe.return_value = PdfBackendInfo(False, "none", "missing")
                msg = warn_if_poppler_only_stack()
                self.assertIsNotNone(msg)
                self.assertIn("Poppler", msg or "")


if __name__ == "__main__":
    unittest.main()
