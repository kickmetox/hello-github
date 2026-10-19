import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from officedisplay.input.pointer import StrokeBuilder, interpret_pointer, smooth_points, stroke_width
from officedisplay.model.presentation import blank_presentation
from officedisplay.native.cpp_bridge import adjust_rgb, smooth_stroke_inplace, using_native
from officedisplay.ui.canvas import SlideCanvas


class StrokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_pressure_changes_width(self):
        light = stroke_width(10, 0.15, 1.2, "pen")
        heavy = stroke_width(10, 1.0, 1.2, "pen")
        self.assertGreater(heavy, light)

    def test_pointer_actions(self):
        self.assertEqual(interpret_pointer("pen", "eraser", "pan"), "erase")
        self.assertEqual(interpret_pointer("select", "pen", "pan"), "select")
        self.assertEqual(interpret_pointer("pen", "pen", "pan"), "draw")
        self.assertEqual(interpret_pointer("pen", "touch", "draw"), "draw")
        self.assertEqual(interpret_pointer("select", "touch", "pan"), "pan")
        self.assertEqual(interpret_pointer("pen", "mouse", "pan"), "draw")

    def test_smoothing_reduces_jitter(self):
        raw = [(0, 0, 1), (1, 10, 1), (2, 0, 1), (3, 10, 1), (4, 0, 1)]
        smoothed = smooth_points(raw, 2)
        raw_span = max(point[1] for point in raw[1:-1]) - min(point[1] for point in raw[1:-1])
        smooth_span = max(point[1] for point in smoothed[1:-1]) - min(point[1] for point in smoothed[1:-1])
        self.assertLess(smooth_span, raw_span)
        native = smooth_stroke_inplace([0, 0, 1, 10, 2, 0, 3, 10, 4, 0], 2)
        self.assertEqual(len(native), 10)
        self.assertTrue(using_native())

    def test_canvas_accepts_synthetic_pen(self):
        canvas = SlideCanvas()
        canvas.resize(900, 700)
        canvas.show()
        canvas.set_presentation(blank_presentation(), 0)
        canvas.tool = "pen"
        canvas.pointer_event("pen", "press", 180, 160, 0.2, False)
        canvas.pointer_event("pen", "move", 240, 220, 0.95, False)
        canvas.pointer_event("pen", "release", 300, 180, 0.4, False)
        paths = [obj for obj in canvas.slide().objects if obj.kind == "path" and obj.id != "__preview__"]
        self.assertEqual(len(paths), 1)
        pressures = [point[2] for point in paths[0].props["points"]]
        self.assertGreater(max(pressures), min(pressures))
        builder = StrokeBuilder(8, 1.0, 1, "pen")
        builder.add(0, 0, 0.2)
        builder.add(0.2, 0.2, 1)
        self.assertGreater(builder.widths()[-1], builder.widths()[0])

    def test_native_grayscale(self):
        data = bytearray([10, 20, 30] * 4)
        adjust_rgb(data, 4, 0.0, 1.0, True)
        self.assertEqual(data[0], data[1])
        self.assertEqual(data[1], data[2])


if __name__ == "__main__":
    unittest.main()
