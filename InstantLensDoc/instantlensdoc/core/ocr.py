"""OCR-Bridge über pytesseract / Tesseract."""

from __future__ import annotations

from pathlib import Path
from typing import Union

from PIL import Image


class OcrUnavailable(RuntimeError):
    """Tesseract oder pytesseract nicht verfügbar."""


INSTALL_HINT_DE = (
    "OCR benötigt die Tesseract-Runtime.\n\n"
    "Windows:\n"
    "  winget install UB-Mannheim.TesseractOCR\n"
    "  oder Installer von https://github.com/UB-Mannheim/tesseract/wiki\n\n"
    "Danach Python-Paket (falls fehlen):\n"
    "  pip install pytesseract\n\n"
    "Sprachen: deu + eng empfohlen (im Tesseract-Installer anhaken)."
)


def tesseract_available() -> tuple[bool, str]:
    try:
        import pytesseract
    except ImportError:
        return False, "pytesseract nicht installiert (pip install pytesseract).\n\n" + INSTALL_HINT_DE
    try:
        ver = pytesseract.get_tesseract_version()
        return True, f"Tesseract {ver}"
    except Exception as e:
        return False, (
            "Tesseract-Runtime fehlt oder ist nicht im PATH.\n\n"
            + INSTALL_HINT_DE
            + f"\n\nTechnik-Detail: {e}"
        )


def ocr_image(
    source: Union[str, Path, Image.Image],
    lang: str = "deu+eng",
) -> str:
    ok, msg = tesseract_available()
    if not ok:
        raise OcrUnavailable(msg)

    import pytesseract

    if isinstance(source, (str, Path)):
        img = Image.open(source)
    else:
        img = source
    try:
        return pytesseract.image_to_string(img, lang=lang)
    except Exception:
        # Fallback ohne Sprachpaket
        return pytesseract.image_to_string(img, lang="eng")


def ocr_pdf_page(pdf_path: str | Path, page_index: int = 0, lang: str = "deu+eng") -> str:
    from ild_pdf import render_page

    img = render_page(pdf_path, page_index=page_index, scale=2.0)
    return ocr_image(img, lang=lang)


def status_message() -> str:
    ok, msg = tesseract_available()
    return msg if ok else f"OCR nicht verfügbar:\n{msg}"
