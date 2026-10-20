import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from officedisplay.ui.main_window import MainWindow
from officedisplay.ui.theme import THEMES, stylesheet


class ThemeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_four_themes(self):
        for name in ("hell", "dunkel", "farbe", "graustufen"):
            css = stylesheet(name)
            self.assertIn("QMainWindow", css)
            self.assertIn(THEMES[name]["window"], css)
        gray = THEMES["graustufen"]["accent"]
        self.assertEqual(gray[1], gray[3])
        self.assertNotEqual(stylesheet("hell"), stylesheet("dunkel"))

    def test_window_switches_theme(self):
        window = MainWindow()
        window.apply_theme("dunkel")
        self.assertIn(THEMES["dunkel"]["window"], window.styleSheet())
        window.apply_theme("graustufen")
        self.assertEqual(window.prefs["theme"], "graustufen")
        window.close()


if __name__ == "__main__":
    unittest.main()
