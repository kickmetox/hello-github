import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _texts(presentation) -> str:
    return " ".join(
        str(obj.props.get("text") or "")
        for slide in presentation.slides
        for obj in slide.objects
        if obj.kind == "text"
    )


def _rich(folder: Path) -> Path:
    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
    from pptx.enum.chart import XL_CHART_TYPE
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches

    image = folder / "bild.png"
    Image.new("RGB", (32, 24), (20, 90, 200)).save(image)
    package = Presentation()
    title = package.slides.add_slide(package.slide_layouts[0])
    title.shapes.title.text = "CyberSec Titel"
    title.placeholders[1].text = "Untertitel im Saal"
    body = package.slides.add_slide(package.slide_layouts[1])
    body.shapes.title.text = "Punkte"
    frame = body.placeholders[1].text_frame
    frame.text = "Erster Punkt"
    frame.add_paragraph().text = "Zweiter Punkt"
    field = body.shapes.add_textbox(Inches(0.5), Inches(4.6), Inches(4), Inches(0.4))
    field.text_frame.paragraphs[0].text = "Freies Textfeld"
    body.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(6.2), Inches(1.2), Inches(2), Inches(1))
    table = body.shapes.add_table(2, 2, Inches(0.5), Inches(2.2), Inches(4.2), Inches(1.2)).table
    table.cell(0, 0).text = "SpalteA"
    table.cell(0, 1).text = "SpalteB"
    chart_slide = package.slides.add_slide(package.slide_layouts[5])
    chart_slide.shapes.title.text = "Diagramm Titel"
    data = CategoryChartData()
    data.categories = ["Nord", "Süd"]
    data.add_series("Werte", (4, 7))
    chart_slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(1), Inches(1.6), Inches(6), Inches(4), data
    )
    chart_slide.notes_slide.notes_text_frame.text = "Notiz Saal"
    picture = package.slides.add_slide(package.slide_layouts[6])
    picture.shapes.add_picture(str(image), Inches(0.6), Inches(0.6), Inches(3), Inches(2))
    package.slides.add_slide(package.slide_layouts[6])
    target = folder / "CyberSec ATCEUC.pptx"
    package.save(str(target))
    return target


def _replace_part(path: Path, predicate, payload: bytes) -> None:
    temporary = path.with_suffix(".tmp.pptx")
    with zipfile.ZipFile(path, "r") as source, zipfile.ZipFile(temporary, "w") as target:
        for info in source.infolist():
            blob = payload if predicate(info.filename) else source.read(info.filename)
            target.writestr(info, blob)
    temporary.replace(path)


class PptxOpenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def test_filename_with_spaces_and_unicode(self):
        from officedisplay.io.pptx_io import import_pptx
        from officedisplay.ui import main_window as ui
        from officedisplay.ui.main_window import MainWindow

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            sample = _rich(root)
            loaded = import_pptx(sample)
            blob = _texts(loaded)
            self.assertIn("CyberSec Titel", blob)
            self.assertIn("Erster Punkt", blob)
            self.assertIn("Freies Textfeld", blob)
            self.assertIn("SpalteA", blob)
            self.assertIn("Diagramm Titel", blob)
            self.assertEqual(loaded.slides[2].notes, "Notiz Saal")
            self.assertGreaterEqual(len(loaded.slides), 5)
            unicode_path = root / "Fölie Übersicht.pptx"
            unicode_path.write_bytes(sample.read_bytes())
            again = import_pptx(unicode_path)
            self.assertIn("CyberSec Titel", _texts(again))
            messages = []
            original = ui.show_text
            ui.show_text = lambda _parent, _title, text: messages.append(text)
            guarded = ui.load_odisp

            def refuse_odisp(*_args, **_kwargs):
                raise AssertionError("pptx wurde als odisp gelesen")

            ui.load_odisp = refuse_odisp
            window = MainWindow()
            try:
                window.load_path(unicode_path)
                self.assertIn("CyberSec Titel", _texts(window.presentation))
                self.assertFalse(messages)
            finally:
                ui.show_text = original
                ui.load_odisp = guarded
                window.close()

    def test_table_or_chart_keeps_title(self):
        from officedisplay.io.pptx_io import import_pptx

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            sample = _rich(root)
            broken = root / "chart kaputt.pptx"
            broken.write_bytes(sample.read_bytes())
            _replace_part(broken, lambda name: name.startswith("ppt/charts/") and name.endswith(".xml"), b"<not xml")
            loaded = import_pptx(broken)
            blob = _texts(loaded)
            self.assertIn("Diagramm Titel", blob)
            self.assertIn("SpalteA", blob)
            self.assertIn("CyberSec Titel", blob)

    def test_broken_shape_on_first_slide_keeps_second(self):
        from pptx import Presentation
        from pptx.enum.shapes import MSO_SHAPE
        from pptx.oxml import parse_xml
        from pptx.oxml.ns import nsdecls
        from pptx.util import Inches

        from officedisplay.io import pptx_io
        from officedisplay.io.pptx_io import import_pptx

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            package = Presentation()
            first = package.slides.add_slide(package.slide_layouts[5])
            first.shapes.title.text = "Titel Folie Eins"
            broken = first.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1), Inches(3), Inches(2), Inches(1))
            broken.name = "Kaputt"
            second = package.slides.add_slide(package.slide_layouts[5])
            second.shapes.title.text = "Zweite Folie bleibt"
            target = root / "zwei folien.pptx"
            package.save(str(target))
            graphic = f'''
            <p:graphicFrame {nsdecls("a", "p", "r")}>
              <p:nvGraphicFramePr>
                <p:cNvPr id="80" name="Ohne Graphic"/>
                <p:cNvGraphicFramePr/>
                <p:nvPr/>
              </p:nvGraphicFramePr>
              <p:xfrm>
                <a:off x="914400" y="914400"/>
                <a:ext cx="2000000" cy="1000000"/>
              </p:xfrm>
            </p:graphicFrame>
            '''
            package = Presentation(str(target))
            package.slides[0].shapes._spTree.append(parse_xml(graphic))
            package.save(str(target))
            original = pptx_io._take_shape

            def boom(shape, slide, slide_w, slide_h, media, transforms=()):
                try:
                    name = shape.name
                except Exception:
                    name = ""
                if name == "Kaputt":
                    raise RuntimeError("kaputtes Shape")
                return original(shape, slide, slide_w, slide_h, media, transforms)

            pptx_io._take_shape = boom
            try:
                loaded = import_pptx(target)
            finally:
                pptx_io._take_shape = original
            blob = _texts(loaded)
            self.assertIn("Titel Folie Eins", blob)
            self.assertIn("Zweite Folie bleibt", blob)
            self.assertGreaterEqual(len(loaded.slides), 2)

            destroyed = root / "folie1 kaputt.pptx"
            destroyed.write_bytes(target.read_bytes())
            _replace_part(destroyed, lambda name: name.endswith("ppt/slides/slide1.xml"), b"<p:sld><kaputt")
            survived = import_pptx(destroyed)
            self.assertIn("Zweite Folie bleibt", _texts(survived))

    def test_zip_fallback_reads_title_when_presentation_fails(self):
        from officedisplay.io.pptx_io import PptxReadError, import_pptx
        from officedisplay.ui import main_window as ui
        from officedisplay.ui.main_window import MainWindow

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / "nur zip.pptx"
            slide = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                   xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
              <p:cSld><p:spTree>
                <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
                <p:grpSpPr/>
                <p:sp>
                  <p:nvSpPr>
                    <p:cNvPr id="2" name="Titel"/>
                    <p:cNvSpPr/>
                    <p:nvPr><p:ph type="title"/></p:nvPr>
                  </p:nvSpPr>
                  <p:txBody>
                    <a:bodyPr/>
                    <a:lstStyle/>
                    <a:p><a:r><a:t>Titel aus slide1.xml</a:t></a:r></a:p>
                  </p:txBody>
                </p:sp>
              </p:spTree></p:cSld>
            </p:sld>
            """
            presentation = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                            xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
              <p:sldIdLst><p:sldId id="256" r:id="rId2"/></p:sldIdLst>
              <p:sldSz cx="12192000" cy="6858000"/>
            </p:presentation>
            """
            rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
              <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
            </Relationships>
            """
            with zipfile.ZipFile(target, "w") as archive:
                archive.writestr("[Content_Types].xml", b"<Types>")
                archive.writestr("ppt/presentation.xml", presentation.encode("utf-8"))
                archive.writestr("ppt/_rels/presentation.xml.rels", rels.encode("utf-8"))
                archive.writestr("ppt/slides/slide1.xml", slide.encode("utf-8"))
            loaded = import_pptx(target)
            self.assertIn("Titel aus slide1.xml", _texts(loaded))

            missing = root / "beziehung fehlt.pptx"
            with zipfile.ZipFile(missing, "w") as archive:
                archive.writestr(
                    "[Content_Types].xml",
                    b'<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>',
                )
                archive.writestr("ppt/presentation.xml", presentation.encode("utf-8"))
                archive.writestr(
                    "ppt/_rels/presentation.xml.rels",
                    b'<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>',
                )
            with self.assertRaises(PptxReadError) as caught:
                import_pptx(missing)
            self.assertIn("lässt sich nicht laden", str(caught.exception))
            self.assertIn("leer", str(caught.exception))

            secret = root / "geheim.pptx"
            secret.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1EncryptedPackage EncryptionInfo")
            with self.assertRaises(PptxReadError) as encrypted:
                import_pptx(secret)
            self.assertEqual(str(encrypted.exception), "Die Datei ist verschlüsselt und lässt sich hier nicht öffnen.")

            messages = []
            original = ui.show_text
            ui.show_text = lambda _parent, _title, text: messages.append(text)
            window = MainWindow()
            try:
                window.load_path(secret)
                self.assertEqual(messages[-1], "Die Datei ist verschlüsselt und lässt sich hier nicht öffnen.")
                plain = root / "keine pptx.pptx"
                plain.write_text("keine pptx", encoding="utf-8")
                window.load_path(plain)
                self.assertIn("lässt sich nicht laden", messages[-1])
                self.assertIn("kein ZIP", messages[-1])
            finally:
                ui.show_text = original
                window.close()


if __name__ == "__main__":
    unittest.main()
