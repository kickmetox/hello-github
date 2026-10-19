import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class PlayerNavTests(unittest.TestCase):
    def test_next_prev_and_black(self):
        from officedisplay.player_nav import navigate_player

        nxt = navigate_player(0, 4, "", "right")
        self.assertEqual(nxt["index"], 1)
        self.assertEqual(nxt["blank"], "")
        self.assertFalse(nxt["exit"])
        space = navigate_player(1, 4, "", "space")
        self.assertEqual(space["index"], 2)
        prev = navigate_player(2, 4, "", "left")
        self.assertEqual(prev["index"], 1)
        page = navigate_player(1, 4, "", "pageup")
        self.assertEqual(page["index"], 0)
        self.assertEqual(navigate_player(2, 4, "", "home")["index"], 0)
        self.assertEqual(navigate_player(0, 4, "", "end")["index"], 3)
        black = navigate_player(1, 4, "", "b")
        self.assertEqual(black["blank"], "black")
        self.assertEqual(black["index"], 1)
        self.assertEqual(navigate_player(1, 4, "black", "period")["blank"], "")
        white = navigate_player(1, 4, "", "w")
        self.assertEqual(white["blank"], "white")
        covered = navigate_player(0, 4, "black", "click")
        self.assertFalse(covered["run_click"])
        self.assertEqual(covered["index"], 1)
        opened = navigate_player(0, 4, "", "click")
        self.assertTrue(opened["run_click"])
        self.assertEqual(opened["index"], 0)
        self.assertTrue(navigate_player(1, 4, "", "escape")["exit"])
        self.assertTrue(navigate_player(1, 4, "black", "n")["toggle_notes"])


class SlideshowIoTests(unittest.TestCase):
    def test_oshow_roundtrip_keeps_order_and_kinds(self):
        from PIL import Image

        from officedisplay.io.slideshow_io import load_oshow, save_oshow
        from officedisplay.model.slideshow import ShowEntry, Slideshow

        folder = Path(tempfile.mkdtemp())
        image_path = folder / "saal.png"
        Image.new("RGB", (12, 8), (11, 99, 229)).save(image_path)
        show = Slideshow(
            title="Abend",
            entries=[
                ShowEntry(id="bild", kind="image", title="Saal", path=str(image_path)),
                ShowEntry(id="text", kind="text", title="Ansagen", text="Tür auf um acht."),
            ],
        )
        target = folder / "abend.oshow"
        save_oshow(show, target)
        loaded = load_oshow(target)
        self.assertEqual([entry.kind for entry in loaded.entries], ["image", "text"])
        self.assertEqual([entry.title for entry in loaded.entries], ["Saal", "Ansagen"])
        self.assertEqual(loaded.entries[1].text, "Tür auf um acht.")
        self.assertTrue(Path(loaded.entries[0].path).is_file())

    def test_odisp_export_one_slide_per_entry(self):
        from PIL import Image

        from officedisplay.io.native_io import load_odisp
        from officedisplay.io.slideshow_io import export_slideshow_odisp
        from officedisplay.model.slideshow import ShowEntry, Slideshow

        folder = Path(tempfile.mkdtemp())
        image_path = folder / "foto.png"
        Image.new("RGB", (8, 8), (240, 80, 20)).save(image_path)
        show = Slideshow(
            title="Folge",
            entries=[
                ShowEntry(id="1", kind="image", title="Foto", path=str(image_path)),
                ShowEntry(id="2", kind="text", title="Hinweis", text="Bitte Platz nehmen."),
                ShowEntry(id="3", kind="video", title="Clip", path=str(folder / "clip.mp4")),
            ],
        )
        target = folder / "folge.odisp"
        export_slideshow_odisp(show, target)
        loaded = load_odisp(target)
        self.assertEqual(len(loaded.slides), 3)
        self.assertEqual([slide.objects[0].kind for slide in loaded.slides], ["image", "text", "video"])
        self.assertIn("Platz nehmen", loaded.slides[1].objects[0].props["text"])


class ShapeAndBackgroundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def test_shape_fill_slot_keeps_selection(self):
        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtGui import QMouseEvent

        from officedisplay.model.presentation import SlideObject
        from officedisplay.ui.main_window import MainWindow

        window = MainWindow()
        obj = SlideObject(
            id="form",
            kind="shape",
            x=0.2,
            y=0.2,
            w=0.4,
            h=0.4,
            props={"shape": "rect", "fill": "#0B63E5", "stroke": "#00000000", "stroke_width": 0},
        )
        window.current_slide().objects.append(obj)
        window.canvas.selected = ["bleiben"]
        window.shape_fill_color("#C01040", obj)
        self.assertEqual(obj.props["fill"], "#C01040")
        self.assertEqual(window.canvas.selected, ["bleiben"])

        window.canvas.shapeContext.disconnect(window.open_shape_menu)
        seen = {}
        window.canvas.shapeContext.connect(lambda object_id, _pos: seen.__setitem__("id", object_id))
        window.resize(1200, 800)
        window.canvas.resize(800, 600)
        point = window.canvas.n2w(0.4, 0.4)
        event = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(point),
            QPointF(point),
            Qt.MouseButton.RightButton,
            Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier,
        )
        window.canvas.mousePressEvent(event)
        self.assertEqual(window.canvas.selected, ["bleiben"])
        self.assertEqual(seen.get("id"), "form")
        window.close()

    def test_background_image_opacity_on_thumb(self):
        from PIL import Image
        from PySide6.QtGui import QColor

        from officedisplay.model.presentation import Background, Presentation, Slide
        from officedisplay.ui.render import clear_image_cache, render_thumb

        folder = Path(tempfile.mkdtemp())
        image_path = folder / "rot.png"
        Image.new("RGB", (24, 24), (255, 0, 0)).save(image_path)
        clear_image_cache(str(image_path))
        slide = Slide(
            id="s",
            name="Hintergrund",
            background=Background(mode="image", color="#0000FF", image=str(image_path), opacity=0.0, fit="cover"),
        )
        deck = Presentation(width=200, height=100, slides=[slide])
        clear = render_thumb(deck, slide, 80)
        hidden = clear.pixelColor(40, 20)
        self.assertGreater(hidden.blue(), 200)
        self.assertLess(hidden.red(), 40)
        slide.background.opacity = 1
        shown = render_thumb(deck, slide, 80)
        visible = shown.pixelColor(40, 20)
        self.assertGreater(visible.red(), 200)
        self.assertLess(visible.blue(), 40)
        self.assertIsInstance(hidden, QColor)
