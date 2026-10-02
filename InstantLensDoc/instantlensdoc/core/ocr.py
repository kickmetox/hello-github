"""OCR-Bridge über pytesseract / Tesseract — Presets + Ausgabe-Modi."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

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


TESSERACT_WIKI_URL = "https://github.com/UB-Mannheim/tesseract/wiki"

INSTALL_HINT_DE = (
    "OCR benötigt die Tesseract-Runtime.\n\n"
    "Windows:\n"
    "  winget install UB-Mannheim.TesseractOCR\n"
    f"  oder Installer: {TESSERACT_WIKI_URL}\n\n"
    "Danach Python-Paket (falls fehlen):\n"
    "  pip install pytesseract\n\n"
    "Sprachen: deu + eng empfohlen (im Tesseract-Installer anhaken)."
)

INSTALL_HINT_HTML = (
    "<p>OCR benötigt die Tesseract-Runtime.</p>"
    "<p><b>Windows:</b><br>"
    "<code>winget install UB-Mannheim.TesseractOCR</code><br>"
    f'oder <a href="{TESSERACT_WIKI_URL}">UB-Mannheim Tesseract (Wiki)</a></p>'
    "<p>Python: <code>pip install pytesseract</code></p>"
    "<p>Sprachen <code>deu</code> + <code>eng</code> im Installer anhaken.</p>"
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


def _load_image(source: Union[str, Path, Image.Image]) -> Image.Image:
    if isinstance(source, (str, Path)):
        return Image.open(source)
    return source


def format_text_as_table(lines: List[List[str]]) -> str:
    """Zeilen/Spalten als Markdown-Tabelle formatieren (einfach)."""
    if not lines:
        return ""
    col_count = max(len(r) for r in lines)
    if col_count < 2:
        return "\n".join(" ".join(r) for r in lines)
    widths = [0] * col_count
    padded: List[List[str]] = []
    for row in lines:
        cells = row + [""] * (col_count - len(row))
        padded.append(cells)
        for i, c in enumerate(cells):
            widths[i] = max(widths[i], len(c))
    header = padded[0]
    sep = "| " + " | ".join("-" * max(1, w) for w in widths) + " |"
    out = ["| " + " | ".join(c.ljust(widths[i]) for i, c in enumerate(header)) + " |", sep]
    for row in padded[1:]:
        out.append("| " + " | ".join(row[i].ljust(widths[i]) for i in range(col_count)) + " |")
    return "\n".join(out)


def ocr_image_structured(
    source: Union[str, Path, Image.Image],
    lang: str = "deu+eng",
) -> tuple[str, bool]:
    """
    OCR mit Tabellen-Heuristik über Tesseract image_to_data.
    Liefert (Text, used_table_layout).
    """
    ok, msg = tesseract_available()
    if not ok:
        raise OcrUnavailable(msg)

    import pytesseract

    img = _load_image(source)
    try:
        data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
    except Exception:
        plain = pytesseract.image_to_string(img, lang="eng")
        return plain, False

    n = len(data["text"])
    rows: dict[tuple[int, int], list[tuple[int, str]]] = {}
    for i in range(n):
        word = (data["text"][i] or "").strip()
        if not word:
            continue
        conf = int(float(data["conf"][i])) if data["conf"][i] not in ("-1", "") else -1
        if conf >= 0 and conf < 40:
            continue
        key = (int(data["block_num"][i]), int(data["line_num"][i]))
        left = int(data["left"][i])
        rows.setdefault(key, []).append((left, word))

    if not rows:
        plain = pytesseract.image_to_string(img, lang=lang)
        return plain, False

    line_rows: List[List[str]] = []
    table_like = False
    for _key in sorted(rows.keys()):
        words = sorted(rows[_key], key=lambda t: t[0])
        if len(words) >= 2:
            # Spalten anhand horizontaler Lücken gruppieren
            cols: List[str] = []
            col_words: List[str] = []
            prev_x = words[0][0]
            gap_threshold = 28
            for left, w in words:
                if col_words and left - prev_x > gap_threshold:
                    cols.append(" ".join(col_words))
                    col_words = [w]
                else:
                    col_words.append(w)
                prev_x = left + len(w) * 8
            if col_words:
                cols.append(" ".join(col_words))
            if len(cols) >= 2:
                table_like = True
                line_rows.append(cols)
            else:
                line_rows.append([" ".join(w for _, w in words)])
        else:
            line_rows.append([words[0][1]])

    if table_like and len(line_rows) >= 2:
        return format_text_as_table(line_rows), True
    plain_lines = [" ".join(r) for r in line_rows]
    return "\n".join(plain_lines), table_like


def ocr_image(
    source: Union[str, Path, Image.Image],
    lang: str = "deu+eng",
    *,
    table_layout: bool = True,
) -> str:
    ok, msg = tesseract_available()
    if not ok:
        raise OcrUnavailable(msg)

    import pytesseract

    img = _load_image(source)
    if table_layout:
        try:
            text, used = ocr_image_structured(img, lang=lang)
            if used or text.strip():
                return text
        except Exception:
            pass
    try:
        return pytesseract.image_to_string(img, lang=lang)
    except Exception:
        return pytesseract.image_to_string(img, lang="eng")


def ocr_pdf_page(pdf_path: str | Path, page_index: int = 0, lang: str = "deu+eng") -> str:
    from ild_pdf import render_page

    img = render_page(pdf_path, page_index=page_index, scale=2.0)
    return ocr_image(img, lang=lang)


@dataclass
class OcrDocumentResult:
    """Ergebnis einer Batch-OCR über alle PDF-Seiten."""

    text: str
    lang: str
    pages_done: int
    pages_total: int
    cancelled: bool = False
    page_texts: List[str] = field(default_factory=list)


def ocr_pdf_document(
    pdf_path: str | Path,
    *,
    lang: str = "deu+eng",
    scale: float = 2.0,
    progress: Optional[Callable[[int, int, str], Optional[bool]]] = None,
) -> OcrDocumentResult:
    """
    OCR über alle Seiten eines PDFs.
    progress(page_1based, total, preview) → False zum Abbrechen, sonst True/None.
    """
    from ild_pdf import render_page

    ok, msg = tesseract_available()
    if not ok:
        raise OcrUnavailable(msg)

    pdf_path = Path(pdf_path)
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        total = len(doc)
    finally:
        doc.close()

    page_texts: List[str] = []
    cancelled = False
    for page in range(total):
        if progress is not None:
            cont = progress(page + 1, total, f"Seite {page + 1}/{total}")
            if cont is False:
                cancelled = True
                break
        img = render_page(pdf_path, page_index=page, scale=scale)
        page_texts.append(ocr_image(img, lang=lang))

    parts: List[str] = []
    for i, t in enumerate(page_texts):
        header = f"--- Seite {i + 1}/{total} ---"
        body = (t or "").rstrip()
        parts.append(f"{header}\n{body}" if body else header)
    combined = "\n\n".join(parts).strip() + ("\n" if parts else "")
    return OcrDocumentResult(
        text=combined,
        lang=lang,
        pages_done=len(page_texts),
        pages_total=total,
        cancelled=cancelled,
        page_texts=page_texts,
    )


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
