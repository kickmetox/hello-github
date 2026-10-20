import os
import re
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QAction, QKeyEvent
from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QApplication

from officedisplay.input.pointer import interpret_pointer
from officedisplay.model.presentation import SlideObject, new_id


class TextEditingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _window(self):
        from officedisplay.ui.main_window import MainWindow

        window = MainWindow()
        window.resize(1360, 860)
        window.canvas.resize(900, 600)
        self.app.processEvents()
        return window

    def _text(self, window, size=28):
        obj = SlideObject(
            id=new_id(),
            kind="text",
            x=0.1,
            y=0.2,
            w=0.3,
            h=0.12,
            name="text",
            props={
                "text": "Ein ziemlich langer Satz der nicht in die kleine Box passt und noch weiter geht",
                "font_size": size,
                "font_family": "Segoe UI",
                "color": "#1B1F2A",
            },
        )
        window.current_slide().objects.append(obj)
        window.canvas.selected = [obj.id]
        window.canvas.selectionChanged.emit(window.canvas.selected)
        self.app.processEvents()
        return obj

    def test_text_tool_creates_text(self):
        self.assertEqual(interpret_pointer("text", "mouse", "pan"), "create")
        self.assertEqual(interpret_pointer("text", "touch", "pan"), "create")
        window = self._window()
        window.set_tool("text")
        rect = window.canvas.slide_rect()
        x, y = rect.center().x(), rect.center().y()
        window.canvas.pointer_event("mouse", "press", x, y, 1.0, False)
        window.canvas.pointer_event("mouse", "release", x, y, 1.0, False)
        texts = [obj for obj in window.current_slide().objects if obj.kind == "text"]
        self.assertEqual(len(texts), 1)
        self.assertEqual(texts[0].kind, "text")
        self.assertEqual(window.canvas._editing_id, texts[0].id)
        self.assertTrue(window.canvas.editor.isVisible())
        window.close()

    def test_insert_menu_starts_editing(self):
        window = self._window()
        action = self._menu_action(window, "Einfügen", "Text")
        self.assertIsNotNone(action)
        self.assertGreater(action.receivers("2triggered(bool)"), 0)
        action.trigger()
        self.app.processEvents()
        texts = [obj for obj in window.current_slide().objects if obj.kind == "text"]
        self.assertEqual(len(texts), 1)
        self.assertEqual(window.canvas._editing_id, texts[0].id)
        self.assertTrue(window.canvas.editor.isVisible())
        window.close()

    def test_size_slot_sets_font_and_keeps_it(self):
        window = self._window()
        obj = self._text(window, 28)
        self.assertEqual(window.size_box.value(), 28)
        window.canvas.begin_text_edit(obj.id)
        window.size_box.setValue(40)
        self.app.processEvents()
        self.assertEqual(obj.props["font_size"], 40)
        css = window.canvas.editor.styleSheet()
        match = re.search(r"font-size:\s*(\d+)px", css)
        self.assertIsNotNone(match)
        self.assertGreater(int(match.group(1)), 13)
        window.canvas.commit_text()
        self.assertEqual(obj.props["font_size"], 40)
        window.canvas.selected = []
        window.apply_size(36)
        self.assertIn("Text", window.statusBar().currentMessage())
        window.close()

    def test_size_arrows_and_keys_step_the_selection(self):
        window = self._window()
        obj = self._text(window, 28)
        window.size_box.stepBy(12)
        self.app.processEvents()
        self.assertEqual(obj.props["font_size"], 40)
        window.size_box.setFocus()
        self.app.processEvents()
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(window.size_box, event)
        self.app.processEvents()
        self.assertEqual(obj.props["font_size"], 39)
        window.close()

    def test_every_command_action_has_a_receiver(self):
        window = self._window()
        dead = []
        for action in window.findChildren(QAction):
            if action.isSeparator() or action.menu() is not None or not action.text().strip():
                continue
            if action.receivers("2triggered(bool)") <= 0:
                dead.append(action.text())
        self.assertEqual(dead, [])
        window.group_selected()
        self.assertIn("zwei", window.statusBar().currentMessage())
        window.filter_image("gray")
        self.assertIn("Bild", window.statusBar().currentMessage())
        window.close()

    def _menu_action(self, window, menu_title, item_title):
        for action in window.menuBar().actions():
            menu = action.menu()
            if menu is None or action.text().replace("&", "") != menu_title:
                continue
            for item in menu.actions():
                if item.text().replace("&", "") == item_title:
                    return item
        return None


if __name__ == "__main__":
    unittest.main()
