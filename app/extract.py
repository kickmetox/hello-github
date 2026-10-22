"""Text aus hochgeladenen Dateien. Bilder bleiben ohne OCR im Archiv."""

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
            text = _pdf_text(data)
            status = "extracted" if text.strip() else "empty"
        elif ext == ".docx":
            text = _docx_text(data)
            status = "extracted" if text.strip() else "empty"
        else:
            return "", "binary"
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


def _pdf_text(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def _docx_text(data: bytes) -> str:
    with zipfile.ZipFile(BytesIO(data)) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    chunks = [node.text or "" for node in root.findall(".//w:t", WORD_NS)]
    return "\n".join(part for part in chunks if part)
