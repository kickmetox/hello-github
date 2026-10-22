"""Text aus hochgeladenen Dateien. Scans liest ein lokales Tesseract, wenn es da ist."""

from __future__ import annotations

import zipfile
from io import BytesIO
from xml.etree import ElementTree

from app.config import ALLOWED_EXTENSIONS


WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".log"}
MAX_TEXT = 1_500_000


def extension_of(filename: str) -> str:
    name = (filename or "").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    dot = name.rfind(".")
    if dot < 0:
        return ""
    return name[dot:].lower()


def safe_original_name(filename: str) -> str:
    name = (filename or "datei").replace("\\", "/").split("/")[-1].strip()
    name = name.replace("\x00", "")
    if not name or name in {".", ".."}:
        return "datei"
    return name[:300]


def extract_text(filename: str, data: bytes) -> tuple[str, str]:
    ext = extension_of(filename)
    if ext not in ALLOWED_EXTENSIONS:
        return "", "rejected"
    try:
        if ext in TEXT_EXTENSIONS:
            text = _decode_text(data)
            status = "extracted" if text.strip() else "empty"
        elif ext == ".pdf":
            text, status = _pdf_document(data)
        elif ext == ".docx":
            text = _docx_text(data)
            status = "extracted" if text.strip() else "empty"
        else:
            text, status = _ocr_image(data)
    except Exception:
        return "", "failed"
    text = text.replace("\x00", "").strip()
    if len(text) > MAX_TEXT:
        text = text[:MAX_TEXT]
        status = "truncated"
    return text, status


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _enough_text(value: str) -> bool:
    return sum(1 for char in value if char.isalnum()) >= 8


def _pdf_pages(data: bytes) -> list[str]:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(data))
    return [(page.extract_text() or "") for page in reader.pages]


def _pdf_document(data: bytes) -> tuple[str, str]:
    from app.ocr import OcrUnavailable, recognize, tesseract_binary

    pages = _pdf_pages(data)
    if not pages:
        return "", "empty"
    weak = [index for index, text in enumerate(pages) if not _enough_text(text)]
    if not weak:
        return "\n".join(pages), "extracted"
    joined = "\n".join(pages)
    if not tesseract_binary():
        if _enough_text(joined):
            return joined, "extracted"
        return "", "no_ocr"
    try:
        rendered = _render_pdf_pages(data, weak[:8])
    except Exception:
        if _enough_text(joined):
            return joined, "extracted"
        return "", "failed"
    parts: list[str] = []
    used_ocr = False
    for index, text in enumerate(pages):
        image = rendered.get(index)
        if image is None:
            parts.append(text)
            continue
        try:
            recognized = recognize(image)
        except OcrUnavailable:
            if _enough_text(joined):
                return joined, "extracted"
            return "", "no_ocr"
        if recognized.strip():
            parts.append(recognized)
            used_ocr = True
        else:
            parts.append(text)
    combined = "\n".join(parts)
    if not combined.strip():
        return "", "empty"
    return combined, "ocr" if used_ocr else "extracted"


def _render_pdf_pages(data: bytes, indexes: list[int]) -> dict[int, bytes]:
    import pypdfium2 as pdfium

    rendered: dict[int, bytes] = {}
    pdf = pdfium.PdfDocument(data)
    try:
        for index in indexes:
            if index >= len(pdf):
                continue
            page = pdf[index]
            bitmap = page.render(scale=2)
            image = bitmap.to_pil()
            image.thumbnail((4000, 4000))
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            rendered[index] = buffer.getvalue()
            bitmap.close()
    finally:
        pdf.close()
    return rendered


def _ocr_image(data: bytes) -> tuple[str, str]:
    from app.ocr import OcrUnavailable, recognize

    try:
        text = recognize(data)
    except OcrUnavailable:
        return "", "no_ocr"
    if not text.strip():
        return "", "empty"
    return text, "ocr"


def _docx_text(data: bytes) -> str:
    with zipfile.ZipFile(BytesIO(data)) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    chunks = [node.text or "" for node in root.findall(".//w:t", WORD_NS)]
    return "\n".join(part for part in chunks if part)
