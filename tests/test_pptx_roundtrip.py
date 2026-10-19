import tempfile
import unittest
from pathlib import Path

from PIL import Image

from officedisplay.io.native_io import load_odisp, save_odisp
from officedisplay.io.odp_io import export_odp, import_odp
from officedisplay.io.pptx_io import export_pptx, import_pptx
from officedisplay.model.presentation import Presentation, Slide, SlideObject, new_id


class RoundtripTest(unittest.TestCase):
    def _deck(self, image_path: Path) -> Presentation:
        presentation = Presentation(title="Runde", width=1280, height=720)
        slide = Slide(id=new_id(), name="Folie 1", notes="Notiz bleibt")
        slide.objects.append(
            SlideObject(
                id=new_id(),
                kind="text",
                x=0.1,
                y=0.1,
                w=0.6,
                h=0.2,
                name="titel",
                props={
                    "text": "Hallo Andreas",
                    "font_size": 28,
                    "bold": True,
                    "color": "#112233",
                    "font_family": "Calibri",
                    "align": "left",
                },
            )
        )
        slide.objects.append(
            SlideObject(
                id=new_id(),
                kind="image",
                x=0.1,
                y=0.4,
                w=0.3,
                h=0.3,
                name="foto",
                props={"path": str(image_path)},
            )
        )
        presentation.slides = [slide]
        return presentation

    def test_pptx_text_and_image(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            image = root / "bild.png"
            Image.new("RGB", (40, 30), (10, 80, 200)).save(image)
            target = root / "deck.pptx"
            export_pptx(self._deck(image), target)
            loaded = import_pptx(target)
            blob = " ".join(obj.props.get("text", "") for obj in loaded.slides[0].objects)
            self.assertIn("Hallo Andreas", blob)
            self.assertEqual(loaded.slides[0].notes, "Notiz bleibt")
            images = [obj for obj in loaded.slides[0].objects if obj.kind == "image"]
            self.assertTrue(images)
            self.assertTrue(Path(images[0].props["path"]).is_file())

    def test_odp_text(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            image = root / "bild.png"
            Image.new("RGB", (8, 8), (0, 0, 0)).save(image)
            target = root / "deck.odp"
            export_odp(self._deck(image), target)
            loaded = import_odp(target)
            blob = " ".join(str(obj.props.get("text") or "") for obj in loaded.slides[0].objects)
            self.assertIn("Hallo Andreas", blob)

    def test_odisp_keeps_objects(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            image = root / "bild.png"
            Image.new("RGB", (8, 8), (1, 2, 3)).save(image)
            target = root / "deck.odisp"
            original = self._deck(image)
            save_odisp(original, target)
            loaded = load_odisp(target)
            self.assertEqual(loaded.slides[0].objects[0].props["text"], "Hallo Andreas")
            self.assertEqual(loaded.title, "Runde")


if __name__ == "__main__":
    unittest.main()
