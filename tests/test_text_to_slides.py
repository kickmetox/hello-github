import json
import unittest

from officedisplay.ai.commands import apply_command
from officedisplay.ai.offline_design import generate_deck
from officedisplay.design.animate import apply_entrance, morph_slide
from officedisplay.design.resize import magic_resize
from officedisplay.model.presentation import SlideObject


class TextToSlidesTest(unittest.TestCase):
    def test_deck_uses_only_prompt_wording(self):
        prompt = "Quartalsbericht mit Vergleich Kosten versus Nutzen. Zitat: Wir bleiben beim Plan."
        deck = generate_deck(prompt)
        self.assertGreaterEqual(len(deck.slides), 4)
        names = [slide.name for slide in deck.slides]
        self.assertIn("Titel", names)
        self.assertIn("Agenda", names)
        self.assertIn("Abschluss", names)
        blob = json.dumps(deck.to_dict(), ensure_ascii=False)
        self.assertIn("Kosten", blob)
        self.assertIn("Plan", blob)
        self.assertNotIn("Worum es geht", blob)
        self.assertNotIn("Beispielwerte", blob)
        self.assertNotIn("Nächster Schritt", blob)

    def test_fluid_resize_is_not_locked_to_16_9(self):
        deck = generate_deck("Zwei Spalten Vergleich Kosten versus Nutzen")
        magic_resize(deck, 1080, 1920)
        self.assertEqual((deck.width, deck.height), (1080, 1920))
        self.assertNotEqual(deck.width / deck.height, 16 / 9)

    def test_command_and_morph(self):
        deck = generate_deck("Umsatz 12 und Kosten 9")
        message = apply_command(deck, deck.slides[1], "dunkler hintergrund")
        self.assertIn("abgedunkelt", message)
        self.assertEqual(deck.slides[1].background.mode, "gradient")
        chart_message = apply_command(deck, deck.slides[2], "diagramm")
        self.assertIn("Diagramm", chart_message)
        left = deck.slides[0]
        right = left.clone()
        right.objects[1].x = 0.4
        mid = morph_slide(left, right, 0.5)
        self.assertNotEqual(mid.objects[1].x, left.objects[1].x)
        marked = left.clone()
        marked.objects[0].props["entrance"] = "fade"
        hidden = apply_entrance(marked, 0)
        self.assertEqual(hidden.objects[0].props["opacity"], 0)


if __name__ == "__main__":
    unittest.main()
