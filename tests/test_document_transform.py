import tempfile
import unittest
from pathlib import Path

from officedisplay.ai.doc_transform import outline_from_text, slides_from_text


PDF = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 88 >> stream
BT /F1 18 Tf 72 720 Td (Einleitung) Tj ET
BT /F1 14 Tf 72 680 Td (Der Umsatz blieb stabil.) Tj ET
endstream
endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
trailer << /Root 1 0 R >>
%%EOF
"""


class DocumentTransformTest(unittest.TestCase):
    def test_markdown_keeps_source_and_citation(self):
        text = "# Einleitung\nDer Umsatz blieb stabil.\n\n# Ausblick\nWir bleiben beim Plan.\n"
        deck = slides_from_text(text, "Protokoll")
        blob = []
        for slide in deck.slides:
            blob.append(slide.notes)
            for obj in slide.objects:
                blob.append(str(obj.props.get("text") or ""))
        joined = "\n".join(blob)
        self.assertIn("stabil", joined)
        self.assertIn("Plan", joined)
        self.assertIn("Quelle", joined)
        self.assertNotIn("erfunden", joined.lower())
        outline = outline_from_text(text)
        self.assertEqual(outline[0]["title"], "Einleitung")

    def test_pdf_uses_only_extracted_text(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "quelle.pdf"
            path.write_bytes(PDF)
            from officedisplay.ai.doc_transform import read_text_file

            raw = read_text_file(str(path))
            self.assertIn("Umsatz", raw)
            deck = slides_from_text(raw, "PDF")
            joined = " ".join(str(obj.props.get("text") or "") for slide in deck.slides for obj in slide.objects)
            self.assertIn("Umsatz", joined)
            self.assertNotIn("Quartalsrekord", joined)


if __name__ == "__main__":
    unittest.main()
