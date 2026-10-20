import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image


class OdpImportTest(unittest.TestCase):
    def test_page_keeps_text_and_picture(self):
        from officedisplay.io.odp_io import import_odp

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            image = root / "bild.png"
            Image.new("RGB", (12, 8), (10, 40, 180)).save(image)
            target = root / "folien.odp"
            content = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:presentation="urn:oasis:names:tc:opendocument:xmlns:presentation:1.0">
 <office:body><office:presentation>
  <draw:page draw:name="Seite Eins" draw:style-name="dp1" draw:master-page-name="Standard">
   <draw:frame svg:x="2cm" svg:y="3cm" svg:width="10cm" svg:height="2cm">
    <draw:text-box><text:p text:style-name="P1">Foliensatz</text:p></draw:text-box>
   </draw:frame>
   <draw:frame svg:x="1cm" svg:y="8cm" svg:width="6cm" svg:height="4cm">
    <draw:image xlink:href="Pictures/bild.png" xlink:type="simple" xlink:show="embed"/>
   </draw:frame>
   <presentation:notes>
    <draw:frame svg:x="1cm" svg:y="1cm" svg:width="10cm" svg:height="2cm">
     <draw:text-box><text:p text:style-name="P1">Nur eine Notiz</text:p></draw:text-box>
    </draw:frame>
   </presentation:notes>
  </draw:page>
  <draw:page draw:name="Leer"/>
 </office:presentation></office:body>
</office:document-content>
"""
            styles = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" xmlns:xlink="http://www.w3.org/1999/xlink">
 <office:styles>
  <draw:fill-image draw:name="Hintergrund" xlink:href="Pictures/bild.png"/>
  <style:style style:name="dp1" style:family="drawing-page">
   <style:drawing-page-properties draw:fill="solid" draw:fill-color="#112233"/>
  </style:style>
 </office:styles>
 <office:automatic-styles>
  <style:page-layout style:name="PM1">
   <style:page-layout-properties fo:page-width="28cm" fo:page-height="15.75cm"/>
  </style:page-layout>
 </office:automatic-styles>
 <office:master-styles>
  <style:master-page style:name="Standard" style:page-layout-name="PM1" draw:style-name="dp1"/>
 </office:master-styles>
</office:document-styles>
"""
            with zipfile.ZipFile(target, "w") as archive:
                archive.writestr("mimetype", "application/vnd.oasis.opendocument.presentation", compress_type=zipfile.ZIP_STORED)
                archive.writestr("content.xml", content.encode("utf-8"))
                archive.writestr("styles.xml", styles.encode("utf-8"))
                archive.writestr("Pictures/bild.png", image.read_bytes())
            loaded = import_odp(target)
            self.assertEqual(len(loaded.slides), 2)
            first, second = loaded.slides
            self.assertEqual(second.objects, [])
            self.assertTrue(first.objects)
            text = next(obj for obj in first.objects if obj.kind == "text")
            self.assertIn("Foliensatz", text.props["text"])
            self.assertAlmostEqual(text.x, 2 / 28, delta=0.02)
            self.assertAlmostEqual(text.y, 3 / 15.75, delta=0.02)
            self.assertGreater(text.w, 0.2)
            picture = next(obj for obj in first.objects if obj.kind == "image")
            self.assertTrue(Path(picture.props["path"]).is_file())
            self.assertAlmostEqual(picture.x, 1 / 28, delta=0.02)
            self.assertGreater(picture.y, 0.4)
            self.assertLess(picture.y, 0.7)
            blob = " ".join(str(obj.props.get("text") or "") for obj in first.objects)
            self.assertNotIn("Nur eine Notiz", blob)
            self.assertEqual(first.background.color.upper(), "#112233")


if __name__ == "__main__":
    unittest.main()
