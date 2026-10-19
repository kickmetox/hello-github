import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class SurfaceFormatTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def _pptx_bytes(self, folder: Path) -> bytes:
        from pptx import Presentation

        package = Presentation()
        slide = package.slides.add_slide(package.slide_layouts[0])
        slide.shapes.title.text = "Titel aus Paket"
        target = folder / "quelle.pptx"
        package.save(str(target))
        return target.read_bytes()

    def test_potx_or_ppsx_keeps_title(self):
        from officedisplay.io.open_file import load_presentation

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            blob = self._pptx_bytes(root)
            potx = root / "vorlage.potx"
            potx.write_bytes(blob)
            loaded = load_presentation(potx)
            texts = " ".join(obj.props.get("text", "") for slide in loaded.slides for obj in slide.objects)
            self.assertIn("Titel aus Paket", texts)
            ppsx = root / "schau.ppsx"
            ppsx.write_bytes(blob)
            again = load_presentation(ppsx)
            texts = " ".join(obj.props.get("text", "") for slide in again.slides for obj in slide.objects)
            self.assertIn("Titel aus Paket", texts)

    def test_pdrx_zip_imports(self):
        from officedisplay.io.open_file import load_presentation

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / "beispiel.pdrx"
            target.write_bytes(self._pptx_bytes(root))
            self.assertTrue(zipfile.is_zipfile(target))
            loaded = load_presentation(target)
            texts = " ".join(obj.props.get("text", "") for slide in loaded.slides for obj in slide.objects)
            self.assertIn("Titel aus Paket", texts)

    def test_png_becomes_image_object(self):
        from officedisplay.io.incoming import place_on_slide
        from officedisplay.model.presentation import Slide, new_id

        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / "klein.png"
            Image.new("RGB", (12, 8), (20, 40, 60)).save(image)
            slide = Slide(id=new_id(), name="Folie")
            kind = place_on_slide(slide, str(image), 0.1, 0.1)
            self.assertEqual(kind, "image")
            self.assertEqual(slide.objects[-1].kind, "image")
            self.assertTrue(Path(slide.objects[-1].props["path"]).is_file())

    def test_mp4_and_avi_are_video_objects(self):
        from officedisplay.io.incoming import classify, place_on_slide
        from officedisplay.model.presentation import Slide, new_id

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ("clip.mp4", "film.avi"):
                path = root / name
                path.write_bytes(b"not a real stream")
                self.assertEqual(classify(str(path)), "video")
                slide = Slide(id=new_id(), name="Folie")
                place_on_slide(slide, str(path), 0.2, 0.2)
                self.assertEqual(slide.objects[-1].kind, "video")
                self.assertTrue(slide.objects[-1].props["path"].endswith(path.suffix))

    def test_ppt_without_soffice_is_a_message(self):
        import shutil

        from officedisplay.io import open_file
        from officedisplay.io.open_file import FormatReadError, load_presentation

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "alt.ppt"
            path.write_bytes(b"\xd0\xcf\x11\xe0kein powerpoint")
            original = open_file.shutil.which
            open_file.shutil.which = lambda _name: None
            try:
                with self.assertRaises(FormatReadError) as caught:
                    load_presentation(path)
            finally:
                open_file.shutil.which = original
            message = str(caught.exception)
            self.assertIn("soffice", message)
            self.assertNotIn("Traceback", message)
            self.assertIsNone(shutil.which("soffice"))

    def test_menu_layout_and_notes(self):
        from PySide6.QtCore import QSettings

        from officedisplay.model.presentation import Slide, new_id
        from officedisplay.ui.main_window import MainWindow

        settings = QSettings("Sellerbach", "OfficeDisplay")
        settings.setValue("menubar/visible", True)
        window = MainWindow()
        try:
            self.assertTrue(window.menuBar().isVisible())
            self.assertTrue(window.menu_button.isVisible())
            window.hide_menu_bar()
            self.app.processEvents()
            self.assertFalse(window.menuBar().isVisible())
            window.menu_button.click()
            self.app.processEvents()
            self.assertTrue(window.menuBar().isVisible())
            window.presentation.slides.append(Slide(id=new_id(), name="Zweite"))
            window.presentation.slides[0].objects.clear()
            window.presentation.slides[0].objects  # keep the list
            from officedisplay.model.presentation import SlideObject

            window.presentation.slides[1].objects = [
                SlideObject(id=new_id(), kind="text", x=0.1, y=0.1, w=0.4, h=0.2, props={"text": "Bleibt stehen"})
            ]
            window.canvas.set_index(0)
            window.layout_list.setCurrentRow(4)
            window.apply_current_layout()
            self.assertEqual(window.presentation.slides[0].objects, [])
            self.assertIn("Bleibt stehen", window.presentation.slides[1].objects[0].props["text"])
            self.assertEqual(len(window.presentation.slides), 2)
            window.notes_edit.setPlainText("Notiz vom Rand")
            window.commit_notes()
            self.assertEqual(window.current_slide().notes, "Notiz vom Rand")
            window.undo_change()
            self.assertEqual(window.current_slide().notes, "")
            self.assertIn("Folie", window.slide_pos.text())
            self.assertIn("%", window.zoom_label.text())
            headings = [label.text() for label in window.findChildren(type(window.slide_pos)) if label.objectName() == "groupHeading"]
            for name in ("Folie", "Schrift", "Absatz", "Zeichnen", "Objekte"):
                self.assertIn(name, headings)
        finally:
            window.show_menu_bar()
            window.show_all_toolbars()
            window.close()


if __name__ == "__main__":
    unittest.main()
