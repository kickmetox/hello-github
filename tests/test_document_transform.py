import tempfile
import unittest
from pathlib import Path

from officedisplay.ai.doc_transform import outline_from_text, slides_from_text


def _pdf_bytes(sentence: str) -> bytes:
    stream = f"BT /F1 18 Tf 72 720 Td ({sentence}) Tj ET\n".encode("latin-1")
    chunks = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n",
        b"4 0 obj\n<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"endstream\nendobj\n",
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]
    blob = b"%PDF-1.4\n"
    offsets = []
    for chunk in chunks:
        offsets.append(len(blob))
        blob += chunk
    xref = len(blob)
    blob += f"xref\n0 {len(chunks) + 1}\n".encode()
    blob += b"0000000000 65535 f \n"
    for offset in offsets:
        blob += f"{offset:010d} 00000 n \n".encode()
    blob += f"trailer\n<< /Size {len(chunks) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return blob


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
            path.write_bytes(_pdf_bytes("Der Umsatz blieb stabil."))
            from officedisplay.ai.doc_transform import read_text_file

            raw = read_text_file(str(path))
            self.assertIn("Umsatz", raw)
            deck = slides_from_text(raw, "PDF")
            joined = " ".join(str(obj.props.get("text") or "") for slide in deck.slides for obj in slide.objects)
            self.assertIn("Umsatz", joined)
            self.assertNotIn("Quartalsrekord", joined)


if __name__ == "__main__":
    unittest.main()
