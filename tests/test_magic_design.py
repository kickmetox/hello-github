import json
import re
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QPushButton

from officedisplay.ai.canva_api import CanvaAPIError, request_canva_magic
from officedisplay.ai.offline_design import deck_has_content, magic_deck
from officedisplay.model.presentation import SlideObject, blank_presentation, new_id
from officedisplay.ui.dialogs import MagicDesignDialog


class _Response:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class MagicDesignTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_quartalszahlen_words_and_slides(self):
        deck = magic_deck("Quartalszahlen Nord Süd")
        self.assertGreaterEqual(len(deck.slides), 2)
        texts = " ".join(
            str(obj.props.get("text") or "")
            for slide in deck.slides
            for obj in slide.objects
            if obj.kind == "text"
        )
        for word in ("Quartalszahlen", "Nord", "Süd"):
            self.assertIn(word, texts)
        self.assertIsNone(re.search(r"\d", texts))
        cover = deck.slides[0]
        self.assertEqual(cover.background.mode, "gradient")
        self.assertEqual(cover.background.opacity, 1.0)
        self.assertIn(
            deck.analytics.get("vorlage"),
            {"Pitch", "Vergleich", "Kennzahlen", "Zitat", "Unterricht", "Titel mit Fläche"},
        )
        blank = blank_presentation()
        self.assertFalse(deck_has_content(blank))
        blank.slides[0].objects.append(
            SlideObject(id=new_id(), kind="text", x=0, y=0, w=0.2, h=0.1, props={"text": "da"})
        )
        self.assertTrue(deck_has_content(blank))

    def test_dialog_and_missing_token_do_not_open_urllib(self):
        calls = []

        def opened(*args, **kwargs):
            calls.append(args)
            raise AssertionError("urllib")

        with patch("urllib.request.urlopen", opened):
            dialog = MagicDesignDialog()
            labels = [button.text() for button in dialog.findChildren(QPushButton)]
            self.assertIn("Lokal erzeugen", labels)
            self.assertIn("Über Canva erzeugen", labels)
            self.assertEqual(dialog.action, "")
            with self.assertRaises(CanvaAPIError) as caught:
                request_canva_magic("", "https://api.canva.com/rest/v1", "Quartalszahlen Nord Süd")
            self.assertIn("nichts gesendet", str(caught.exception))
            with self.assertRaises(CanvaAPIError):
                request_canva_magic("token", "http://example.com/v1", "Quartalszahlen Nord Süd")
        self.assertEqual(calls, [])

    def test_canva_generation_shows_design_id(self):
        seen = []

        def opener(request, timeout=0):
            seen.append(request)
            if request.full_url.endswith("/generations"):
                return _Response({"job": {"id": "job1", "status": "in_progress"}})
            return _Response(
                {"job": {"id": "job1", "status": "success", "result": {"design": {"id": "DAF123"}}}}
            )

        def opened(*args, **kwargs):
            raise AssertionError("urllib")

        with patch("urllib.request.urlopen", opened):
            text = request_canva_magic(
                "geheim",
                "https://api.canva.com/rest/v1",
                "Quartalszahlen Nord Süd",
                opener=opener,
                pause=0,
            )
        self.assertIn("DAF123", text)
        self.assertIn("PPTX", text)
        self.assertTrue(seen[0].full_url.startswith("https://"))
        self.assertTrue(seen[0].full_url.endswith("/generations"))
        self.assertTrue(seen[1].full_url.endswith("/generations/job1"))
        self.assertIn("Bearer geheim", seen[0].get_header("Authorization"))
        body = json.loads(seen[0].data.decode("utf-8"))
        self.assertEqual(body["brief"], "Quartalszahlen Nord Süd")
        self.assertEqual(body["design_type"], {"type": "preset", "name": "presentation"})
        self.assertIsNone(re.search(r"\d", body["brief"]))
