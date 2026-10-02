"""OCR-Bridge über pytesseract / Tesseract — Presets + Ausgabe-Modi."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Tuple, Union

from PIL import Image, ImageDraw, ImageFont


class OcrUnavailable(RuntimeError):
    """Tesseract oder pytesseract nicht verfügbar."""


class OcrOutputMode(str, Enum):
    """Ausgabe-Modus nach OCR."""

    EDITABLE_TEXT = "editable_text"  # reiner Text → Editor
    SEARCHABLE_IMAGE = "searchable_image"  # Bildseite + Textlayer-Sidecar


# UI-Presets: Anzeigename → Tesseract-lang
LANG_PRESETS: Dict[str, str] = {
    "Deutsch + Englisch": "deu+eng",
    "Deutsch": "deu",
    "Englisch": "eng",
    "Französisch": "fra",
    "Spanisch": "spa",
    "Italienisch": "ita",
    "Niederländisch": "nld",
    "Polnisch": "pol",
    "Portugiesisch": "por",
    "Mehrsprachig (deu+eng+fra)": "deu+eng+fra",
}


INSTALL_HINT_DE = (
    "OCR benötigt die Tesseract-Runtime.\n\n"
    "Windows:\n"
    "  winget install UB-Mannheim.TesseractOCR\n"
    "  oder Installer von https://github.com/UB-Mannheim/tesseract/wiki\n\n"
    "Danach Python-Paket (falls fehlen):\n"
    "  pip install pytesseract\n\n"
    "Sprachen: deu + eng empfohlen (im Tesseract-Installer anhaken)."
)


@dataclass
class OcrResult:
    text: str
    lang: str
    mode: OcrOutputMode
    source_label: str = ""
    searchable_pdf: Path | None = None
    sidecar: Path | None = None


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


def list_installed_languages() -> List[str]:
    ok, _ = tesseract_available()
    if not ok:
        return []
    try:
        import pytesseract

        langs = pytesseract.get_languages(config="")
        return sorted(langs)
    except Exception:
        return []


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


def make_searchable_image_pdf(
    source: Union[str, Path, Image.Image],
    text: str,
    out_path: str | Path,
    *,
    lang: str = "deu+eng",
) -> Tuple[Path, Path]:
    """
    „Durchsuchbares Bild“: speichert Bild als PDF-Seite + Text-Sidecar
    (`*.ildocr.txt`) daneben. Kein vollständiges unsichtbares Textlayer-PDF
    (dafür bräuchte man reportlab/hocr) — aber real nutzbar für Suche/Archiv.
    """
    out_path = Path(out_path)
    if isinstance(source, (str, Path)):
        img = Image.open(source)
    else:
        img = source.copy()
    if img.mode == "RGBA":
        img = img.convert("RGB")

    # Titelzeile mit Hinweis auf Sidecar
    canvas = img
    try:
        draw = ImageDraw.Draw(canvas)
        # dezenter Hinweis unten
        note = "InstantLens Doc — durchsuchbares Bild (Text in Sidecar)"
        draw.rectangle([0, canvas.height - 18, canvas.width, canvas.height], fill=(240, 240, 240))
        draw.text((4, canvas.height - 16), note, fill=(80, 80, 80))
    except Exception:
        pass

    canvas.save(out_path, "PDF", resolution=150.0)
    sidecar = out_path.with_suffix(out_path.suffix + ".ildocr.txt")
    header = f"# InstantLens Doc OCR\n# lang={lang}\n# mode=searchable_image\n\n"
    sidecar.write_text(header + text, encoding="utf-8")
    return out_path, sidecar


def run_ocr(
    source: Union[str, Path, Image.Image],
    *,
    lang: str = "deu+eng",
    mode: OcrOutputMode = OcrOutputMode.EDITABLE_TEXT,
    out_dir: str | Path | None = None,
    source_label: str = "",
) -> OcrResult:
    """Einheitlicher OCR-Einstieg inkl. Ausgabe-Modus."""
    text = ocr_image(source, lang=lang)
    label = source_label or (
        str(source) if isinstance(source, (str, Path)) else "Bild"
    )
    if mode == OcrOutputMode.EDITABLE_TEXT:
        return OcrResult(text=text, lang=lang, mode=mode, source_label=label)

    out_dir_p = Path(out_dir) if out_dir else Path.cwd()
    out_dir_p.mkdir(parents=True, exist_ok=True)
    stem = Path(label).stem if label else "ocr"
    out_pdf = out_dir_p / f"{stem}_searchable.pdf"
    pdf_path, sidecar = make_searchable_image_pdf(source, text, out_pdf, lang=lang)
    return OcrResult(
        text=text,
        lang=lang,
        mode=mode,
        source_label=label,
        searchable_pdf=pdf_path,
        sidecar=sidecar,
    )


def status_message() -> str:
    ok, msg = tesseract_available()
    return msg if ok else f"OCR nicht verfügbar:\n{msg}"
