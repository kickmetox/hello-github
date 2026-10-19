import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QLabel, QToolButton

from officedisplay.model.presentation import SlideObject, new_id
from officedisplay.ui.dialogs import MagicDesignDialog, SettingsDialog
from officedisplay.ui.main_window import TOOLBAR_KEYS, MainWindow
from officedisplay.ui.theme import contrast


class AppearanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _window(self, width=1360):
        window = MainWindow()
        window.resize(width, 860)
        window.show()
        self.app.processEvents()
        return window

    def test_toolbar_buttons_stay_on_their_bar(self):
        for width in (1360, 1100):
            window = self._window(width)
            try:
                window.show_all_toolbars()
                self.app.processEvents()
                bars = []
                for key in TOOLBAR_KEYS:
                    bars.extend(window._bars(key))
                self.assertGreaterEqual(len(bars), 5)
                for bar in bars:
                    self.assertTrue(bar.isVisible(), bar.windowTitle())
                    self.assertGreaterEqual(bar.height(), 40, bar.windowTitle())
                    for button in bar.findChildren(QToolButton):
                        if not button.text().strip():
                            continue
                        self.assertTrue(button.isVisible(), button.text())
                        self.assertGreaterEqual(button.height(), 24, button.text())
                        self.assertLessEqual(button.geometry().right(), bar.width() + 1, button.text())
            finally:
                window.show_all_toolbars()
                window.close()
        window = self._window()
        try:
            window._toolbar_actions["grafik"].setChecked(False)
            self.app.processEvents()
            for bar in window._bars("grafik"):
                self.assertFalse(bar.isVisible())
            self.assertTrue(window._toolbars["text"].isVisible())
        finally:
            window.show_all_toolbars()
            window.close()

    def test_farbe_dialog_text_is_readable(self):
        window = self._window()
        window.apply_theme("farbe")
        dialog = MagicDesignDialog(window)
        dialog.show()
        self.app.processEvents()
        try:
            image = dialog.grab().toImage()
            label = next(child for child in dialog.findChildren(QLabel) if "Satz" in child.text())
            origin = label.mapTo(dialog, QPoint(0, 0))
            background = image.pixelColor(4, 4)
            best = 0.0
            for y in range(label.height()):
                for x in range(0, label.width(), 3):
                    ink = image.pixelColor(origin.x() + x, origin.y() + y)
                    best = max(best, contrast(ink.name(), background.name()))
            self.assertGreaterEqual(best, 4.5)
        finally:
            dialog.close()
            window.close()

    def test_spinbox_arrows_are_painted(self):
        window = self._window()
        window.apply_theme("farbe")
        self.app.processEvents()
        image = window.size_box.grab().toImage()
        fill = image.pixelColor(12, image.height() // 2)
        dark = 0
        for y in range(image.height()):
            for x in range(image.width() - 22, image.width() - 2):
                color = image.pixelColor(x, y)
                if color.red() + color.green() + color.blue() + 80 < fill.red() + fill.green() + fill.blue():
                    dark += 1
        self.assertGreater(dark, 8)
        window.close()

    def test_settings_fields_show_the_start(self):
        window = self._window()
        dialog = SettingsDialog(window, {"base_url": "https://api.openai.com/v1"}, {})
        dialog.show()
        self.app.processEvents()
        try:
            field = dialog.base
            self.assertEqual(field.cursorPosition(), 0)
            width = field.fontMetrics().horizontalAdvance(field.text())
            self.assertGreater(field.width(), width + 8)
        finally:
            dialog.close()
            window.close()

    def test_slide_label_fits_the_strip(self):
        window = self._window()
        try:
            item = window.strip.item(0)
            text_width = window.strip.fontMetrics().horizontalAdvance(item.text())
            room = window.strip.viewport().width() - window.strip.iconSize().width() - 16
            self.assertGreaterEqual(room, text_width, item.text())
        finally:
            window.close()

    def test_undo_restores_committed_text(self):
        window = self._window()
        try:
            obj = SlideObject(
                id=new_id(),
                kind="text",
                x=0.2,
                y=0.2,
                w=0.4,
                h=0.2,
                props={"text": "Alt", "font_size": 28, "color": "#111111", "font_family": "Segoe UI"},
            )
            window.current_slide().objects.append(obj)
            window.canvas.begin_text_edit(obj.id)
            window.canvas.editor.setPlainText("Neu")
            window.canvas.commit_text()
            self.app.processEvents()
            self.assertEqual(obj.props["text"], "Neu")
            window.undo_change()
            restored = window.current_slide().objects[0]
            self.assertEqual(restored.props["text"], "Alt")
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
