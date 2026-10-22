import zipfile
from io import BytesIO
from pathlib import Path

import pytest

from app.extract import extract_text, safe_original_name
from app.ocr import engine_status, tesseract_binary


def test_text_and_hostile_filename():
    text, status = extract_text(r"..\..\Notizen.txt", "Mietvertrag Berlin".encode("utf-8"))
    assert status == "extracted"
    assert "Mietvertrag" in text
    assert safe_original_name(r"..\..\Notizen.txt") == "Notizen.txt"


def test_rejects_executable_extension():
    text, status = extract_text("payload.exe", b"MZ")
    assert text == ""
    assert status == "rejected"


def test_docx_paragraphs():
    payload = _docx("Hausrat Police Nordlicht")
    text, status = extract_text("police.docx", payload)
    assert status == "extracted"
    assert "Hausrat" in text
    assert "Nordlicht" in text


def test_pdf_text_layer(monkeypatch):
    def forbidden(_image):
        raise AssertionError("Digitale Textebene darf nicht durch OCR laufen.")

    monkeypatch.setattr("app.ocr.recognize", forbidden)
    payload = _pdf("Mietvertrag Berlin")
    text, status = extract_text("vertrag.pdf", payload)
    assert status == "extracted"
    assert "Mietvertrag" in text


def test_image_without_tesseract_stays_unreadable(monkeypatch):
    monkeypatch.setattr("app.ocr.tesseract_binary", lambda: None)
    text, status = extract_text("scan.png", _png("QUARZSCAN"))
    assert text == ""
    assert status == "no_ocr"


def test_image_and_scanned_pdf_are_read():
    if not engine_status()["available"] or _font() is None:
        pytest.skip("Tesseract oder Schrift fehlt")
    image = _png("QUARZSCAN")
    text, status = extract_text("scan.png", image)
    assert status == "ocr"
    assert "QUARZSCAN" in text.replace(" ", "")
    pdf_text, pdf_status = extract_text("scan.pdf", _image_pdf(image))
    assert pdf_status == "ocr"
    assert "QUARZSCAN" in pdf_text.replace(" ", "")
    assert tesseract_binary()


def _font() -> str | None:
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ):
        if Path(candidate).is_file():
            return candidate
    return None


def _png(text: str) -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (1600, 320), "white")
    draw = ImageDraw.Draw(image)
    font_path = _font()
    font = ImageFont.truetype(font_path, 72) if font_path else ImageFont.load_default()
    draw.text((48, 100), text, fill="black", font=font)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _image_pdf(png: bytes) -> bytes:
    from PIL import Image

    buffer = BytesIO()
    with Image.open(BytesIO(png)) as image:
        image.convert("RGB").save(buffer, format="PDF", resolution=150)
    return buffer.getvalue()


def _docx(text: str) -> bytes:
    document = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>"
    )
    types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        "</Relationships>"
    )
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document)
    return buffer.getvalue()


def _pdf(text: str) -> bytes:
    safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({safe}) Tj ET\n".encode("ascii")
    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n",
        b"4 0 obj\n<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"endstream\nendobj\n",
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]
    header = b"%PDF-1.4\n"
    chunks = [header]
    offsets = [0]
    position = len(header)
    for obj in objects:
        offsets.append(position)
        chunks.append(obj)
        position += len(obj)
    xref = [b"xref\n0 6\n", b"0000000000 65535 f \n"]
    for offset in offsets[1:]:
        xref.append(f"{offset:010d} 00000 n \n".encode("ascii"))
    trailer = f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{position}\n%%EOF\n".encode("ascii")
    return b"".join(chunks + xref + [trailer])
