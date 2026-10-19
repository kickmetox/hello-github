import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class ModelTests(unittest.TestCase):
    def test_group_move_ungroup(self):
        from officedisplay.model.presentation import Slide, SlideObject, group_objects, move_object_to_slide, new_id, ungroup

        source = Slide(id=new_id(), name="A")
        target = Slide(id=new_id(), name="B")
        a = SlideObject(id="a", kind="shape", x=0.1, y=0.1, w=0.2, h=0.2)
        b = SlideObject(id="b", kind="text", x=0.4, y=0.2, w=0.2, h=0.1, props={"text": "Hallo"})
        source.objects += [a, b]
        group = group_objects(source, ["a", "b"])
        self.assertEqual(len(source.objects), 1)
        self.assertTrue(move_object_to_slide(source, target, group.id))
        self.assertEqual(len(source.objects), 0)
        released = ungroup(target, group.id)
        self.assertEqual(len(released), 2)
        self.assertIn("Hallo", released[1].props["text"])


class PointerTests(unittest.TestCase):
    def test_pen_pressure_and_touch(self):
        from officedisplay.input.pointer import StrokeBuilder, interpret_pointer, stroke_width

        self.assertEqual(interpret_pointer("pen", "pen", "pan"), "draw")
        self.assertEqual(interpret_pointer("select", "eraser", "pan"), "erase")
        self.assertEqual(interpret_pointer("pen", "touch", "pan"), "pan")
        self.assertEqual(interpret_pointer("pen", "touch", "draw"), "draw")
        self.assertEqual(interpret_pointer("select", "mouse", "pan"), "select")
        thin = stroke_width(10, 0.1, 1, "pen")
        thick = stroke_width(10, 1.0, 1, "pen")
        self.assertLess(thin, thick)
        builder = StrokeBuilder(base_width=8, curve=1, smooth_passes=1, pointer_kind="pen")
        builder.add(0.1, 0.1, 0.2)
        builder.add(0.2, 0.2, 0.9)
        builder.add(0.3, 0.15, 0.4)
        finished = builder.finish()
        self.assertGreaterEqual(len(finished), 3)
        self.assertGreater(builder.widths()[-1], 0)


class DesignTests(unittest.TestCase):
    def test_prompt_and_resize(self):
        from officedisplay.ai.offline_design import generate_deck, predict_layout
        from officedisplay.design.resize import magic_resize

        self.assertEqual(predict_layout("Umsatz Diagramm 12 Prozent Kennzahl"), "chart")
        from officedisplay.ai.layout_model import predict

        label, source = predict("Umsatz Diagramm 12 Prozent Kennzahl")
        self.assertEqual(label, "chart")
        self.assertEqual(source, "onnxruntime")
        deck = generate_deck("Produktlaunch Nordlicht im Mai, Zielgruppe Werkstätten und Händler")
        self.assertGreaterEqual(len(deck.slides), 3)
        self.assertIn("Nordlicht", deck.slides[0].objects[1].props["text"])
        magic_resize(deck, 1080, 1920)
        self.assertEqual((deck.width, deck.height), (1080, 1920))

    def test_document_keeps_source(self):
        from officedisplay.ai.doc_transform import slides_from_text

        text = "# Befund\nDer Prototyp hält die Last.\n\n# Empfehlung\nDie Serie startet im Mai."
        deck = slides_from_text(text, "Bericht")
        blob = " ".join(obj.props.get("text", "") for slide in deck.slides for obj in slide.objects)
        self.assertIn("Prototyp hält die Last", blob)
        self.assertIn("Quelle", deck.slides[0].notes)

    def test_command_and_speech(self):
        from officedisplay.ai.commands import apply_command
        from officedisplay.ai.speech_coach import analyze_speech
        from officedisplay.model.presentation import Slide, new_id

        slide = Slide(id=new_id(), name="X")
        from officedisplay.model.presentation import SlideObject

        slide.objects.append(SlideObject(id="t", kind="text", x=0, y=0, w=1, h=0.2, name="inhalt", props={"text": "Eins\nZwei\nDrei"}))
        from officedisplay.model.presentation import Presentation

        presentation = Presentation(slides=[slide])
        message = apply_command(presentation, slide, "zwei spalten")
        self.assertIn("Spalten", message)
        report = analyze_speech("Äh also der Test ist kurz. Äh wir machen weiter. Äh danke.")
        self.assertGreaterEqual(report["filler_count"], 3)


class IoTests(unittest.TestCase):
    def test_roundtrip_and_pptx(self):
        from PIL import Image

        from officedisplay.ai.offline_design import generate_deck
        from officedisplay.io.native_io import load_odisp, save_odisp
        from officedisplay.io.odp_io import export_odp, import_odp
        from officedisplay.io.pptx_io import export_pptx, import_pptx
        from officedisplay.model.presentation import SlideObject, new_id

        deck = generate_deck("Quartalsbericht Vertrieb")
        folder = Path(tempfile.mkdtemp())
        image_path = folder / "bild.png"
        Image.new("RGB", (40, 30), (11, 99, 229)).save(image_path)
        deck.slides[1].objects.append(
            SlideObject(id=new_id(), kind="image", x=0.1, y=0.1, w=0.2, h=0.2, props={"path": str(image_path)})
        )
        native = folder / "deck.odisp"
        save_odisp(deck, native)
        loaded = load_odisp(native)
        self.assertEqual(loaded.title, deck.title)
        pptx = folder / "deck.pptx"
        export_pptx(deck, pptx)
        imported = import_pptx(pptx)
        texts = [obj.props.get("text", "") for slide in imported.slides for obj in slide.objects]
        self.assertTrue(any("Quartalsbericht" in text for text in texts))
        odp = folder / "deck.odp"
        export_odp(deck, odp)
        odp_loaded = import_odp(odp)
        odp_text = " ".join(obj.props.get("text", "") for slide in odp_loaded.slides for obj in slide.objects)
        self.assertIn("Quartalsbericht", odp_text)

    def test_csv_binding(self):
        from officedisplay.io.data_bind import read_table
        from officedisplay.model.presentation import SlideObject

        folder = Path(tempfile.mkdtemp())
        path = folder / "daten.csv"
        path.write_text("Region;Umsatz\nNord;10\nSüd;12\n", encoding="utf-8")
        categories, series = read_table(str(path))
        self.assertEqual(categories[0], "Nord")
        self.assertEqual(series[0]["values"][1], 12)


class ApiTests(unittest.TestCase):
    def test_online_guard_and_request(self):
        from officedisplay.ai.online_ai import OnlineAIError, chat_completion, validate_endpoint

        called = {"n": 0}

        def opener(*_args, **_kwargs):
            called["n"] += 1
            raise AssertionError("Netzwerk darf nicht geöffnet werden")

        with self.assertRaises(OnlineAIError):
            validate_endpoint("https://api.openai.com/v1/chat/completions")
        with self.assertRaises(OnlineAIError):
            chat_completion(None, [{"role": "user", "content": "Hallo"}], opener=opener)
        self.assertEqual(called["n"], 0)

    def test_canva_request_shape(self):
        from officedisplay.ai.canva_api import CanvaAPIError, CanvaClient, authorize_url

        with self.assertRaises(CanvaAPIError):
            authorize_url("cid", "https://local/callback", "state", "challenge")
        with self.assertRaises(CanvaAPIError):
            CanvaClient("token")


class NativeTests(unittest.TestCase):
    def test_adjust_and_palette(self):
        from officedisplay.design.palette import palette_from_seed
        from officedisplay.native.cpp_bridge import adjust_rgb

        data = bytearray([10, 20, 30])
        adjust_rgb(data, 1, 0.1, 1.2, True)
        self.assertEqual(data[0], data[1])
        colors = palette_from_seed("#0B63E5")
        self.assertEqual(len(colors), 5)

    def test_macro_and_brand(self):
        from officedisplay.design.palette import constrain_color, constrain_font
        from officedisplay.macros_runner import run_macro
        from officedisplay.model.presentation import blank_presentation

        brand = {"locked": True, "body_font": "Arial", "colors": ["#112233"]}
        self.assertEqual(constrain_font(brand, "Comic Sans"), "Arial")
        self.assertEqual(constrain_color(brand, "#FFFFFF"), "#112233")
        presentation = blank_presentation()
        root = Path(__file__).resolve().parents[1]
        message = run_macro(root / "macros" / "beispiel.py", presentation)
        self.assertIn("Makrofolie", message)
        self.assertGreaterEqual(len(presentation.slides), 2)


class AppTests(unittest.TestCase):
    def test_window_stroke_and_export(self):
        from PySide6.QtWidgets import QApplication

        from officedisplay.ui.main_window import MainWindow

        app = QApplication.instance() or QApplication([])
        window = MainWindow()
        window.canvas.tool = "pen"
        window.canvas.add_stroke_points([(0.2, 0.2, 0.2), (0.3, 0.35, 0.8), (0.4, 0.25, 0.5)], "pen")
        self.assertTrue(any(obj.kind == "path" for obj in window.current_slide().objects))
        window.resize(1200, 800)
        window.canvas.resize(800, 600)
        window.canvas.update()
        app.processEvents()
        folder = Path(tempfile.mkdtemp())
        target = folder / "ui.pptx"
        from officedisplay.io.pptx_io import export_pptx

        export_pptx(window.presentation, target)
        self.assertTrue(target.is_file())
        window.close()


if __name__ == "__main__":
    unittest.main()
