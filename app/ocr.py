"""Lokale Texterkennung über das Programm Tesseract.

Die Originaldatei bleibt unverändert. Der erkannte Text landet im Suchindex.
Ohne installiertes Tesseract bleiben Bilder Bilder; PDF, Word und Text mit
vorhandener Textebene brauchen diese Komponente nicht.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from io import BytesIO
from pathlib import Path

logger = logging.getLogger("docman")

_languages: list[str] | None = None
_language_binary: str | None = None


class OcrUnavailable(Exception):
    """Tesseract ist nicht installiert oder nicht auffindbar."""


def tesseract_binary() -> str | None:
    found = shutil.which("tesseract")
    if found:
        return found
    if os.name == "nt":
        candidate = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if candidate.is_file():
            return str(candidate)
    return None


def languages() -> list[str]:
    global _languages, _language_binary
    binary = tesseract_binary()
    if not binary:
        return []
    if _languages is not None and _language_binary == binary:
        return _languages
    try:
        result = subprocess.run(
            [binary, "--list-langs"],
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    text = (result.stdout or b"").decode("utf-8", errors="replace")
    text += "\n" + (result.stderr or b"").decode("utf-8", errors="replace")
    found = []
    for line in text.splitlines():
        code = line.strip().lower()
        if code.isalpha() and 2 <= len(code) <= 8 and code != "osd":
            found.append(code)
    _languages = found
    _language_binary = binary
    return found


def engine_status() -> dict:
    present = languages()
    return {"available": bool(tesseract_binary()) and bool(present), "languages": present}


def recognize(image: bytes) -> str:
    binary = tesseract_binary()
    if not binary or not languages():
        raise OcrUnavailable()
    png = _png(image)
    result = subprocess.run(
        [binary, "stdin", "stdout", "-l", _language_argument(), "--psm", "3"],
        input=png,
        capture_output=True,
        timeout=25,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or b"").decode("utf-8", errors="replace")[:300]
        logger.warning("Tesseract %s: %s", result.returncode, detail)
        raise RuntimeError("Tesseract konnte das Bild nicht lesen.")
    return (result.stdout or b"").decode("utf-8", errors="replace").replace("\x00", "").strip()


def _language_argument() -> str:
    present = set(languages())
    if "deu" in present and "eng" in present:
        return "deu+eng"
    if "deu" in present:
        return "deu"
    if "eng" in present:
        return "eng"
    return languages()[0]


def _png(image: bytes) -> bytes:
    from PIL import Image

    with Image.open(BytesIO(image)) as opened:
        frame = opened.convert("RGB")
        frame.thumbnail((4000, 4000))
        buffer = BytesIO()
        frame.save(buffer, format="PNG")
        return buffer.getvalue()
