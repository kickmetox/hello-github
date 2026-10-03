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
    TABLE_CSV = "table_csv"  # Tabellen-Heuristik → CSV — 1.9.0


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

# Typische Installationspfade (Windows) — Hinweis wenn Runtime nicht im PATH
TESSERACT_COMMON_PATHS = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
)

_PATH_HINT_DE = (
    "Pfad-Hilfe (falls nicht im PATH):\n"
    + "\n".join(f"  {p}" for p in TESSERACT_COMMON_PATHS)
    + "\n"
    "  → PATH um den Ordner ergänzen oder TESSDATA_PREFIX setzen."
)

INSTALL_HINT_DE = (
    "OCR benötigt die Tesseract-Runtime.\n\n"
    "Windows:\n"
    "  winget install UB-Mannheim.TesseractOCR\n"
    f"  oder Installer: {TESSERACT_WIKI_URL}\n\n"
    f"{_PATH_HINT_DE}\n\n"
    "Danach Python-Paket (falls fehlen):\n"
    "  pip install pytesseract\n\n"
    "Sprachen: deu + eng empfohlen (im Tesseract-Installer anhaken)."
)

INSTALL_HINT_HTML = (
    "<p>OCR benötigt die Tesseract-Runtime.</p>"
    "<p><b>Windows:</b><br>"
    "<code>winget install UB-Mannheim.TesseractOCR</code><br>"
    f'oder <a href="{TESSERACT_WIKI_URL}">UB-Mannheim Tesseract (Wiki)</a></p>'
    "<p><b>Pfad-Hilfe</b> (falls nicht im PATH):<br>"
    + "<br>".join(f"<code>{p}</code>" for p in TESSERACT_COMMON_PATHS)
    + "<br>→ PATH um den Ordner ergänzen oder <code>TESSDATA_PREFIX</code> setzen.</p>"
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


def format_rows_as_csv(
    rows: List[List[str]],
    *,
    delimiter: str = ";",
    dialect: str = "excel",
) -> str:
    """
    Zeilen/Spalten als CSV (Default `;` für DE-Excel) — 1.9.0.
    UTF-8 mit BOM-Präfix im String (für Excel-kompatibles Speichern).
    """
    import csv
    import io

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=delimiter, dialect=dialect, lineterminator="\n")
    for row in rows:
        writer.writerow([str(c) if c is not None else "" for c in row])
    return "\ufeff" + buf.getvalue()


def write_ocr_table_csv(
    path: str | Path,
    rows: List[List[str]],
    *,
    delimiter: str = ";",
) -> Path:
    """Schreibt Tabellen-OCR als CSV (UTF-8 BOM)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = format_rows_as_csv(rows, delimiter=delimiter)
    path.write_text(text, encoding="utf-8")
    return path


def _rows_from_tesseract_data(
    data: dict,
    *,
    gap_threshold: int = 28,
    min_conf: int = 40,
) -> tuple[List[List[str]], bool]:
    """Grobe Tabellenerkennung aus image_to_data → (rows, table_like)."""
    n = len(data.get("text") or [])
    buckets: dict[tuple[int, int], list[tuple[int, str]]] = {}
    for i in range(n):
        word = (data["text"][i] or "").strip()
        if not word:
            continue
        conf_raw = data["conf"][i]
        conf = int(float(conf_raw)) if conf_raw not in ("-1", "") else -1
        if conf >= 0 and conf < min_conf:
            continue
        key = (int(data["block_num"][i]), int(data["line_num"][i]))
        left = int(data["left"][i])
        buckets.setdefault(key, []).append((left, word))

    if not buckets:
        return [], False

    line_rows: List[List[str]] = []
    table_like = False
    for _key in sorted(buckets.keys()):
        words = sorted(buckets[_key], key=lambda t: t[0])
        if len(words) >= 2:
            cols: List[str] = []
            col_words: List[str] = []
            prev_x = words[0][0]
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
    return line_rows, table_like


def ocr_image_table_rows(
    source: Union[str, Path, Image.Image],
    lang: str = "deu+eng",
) -> tuple[List[List[str]], bool]:
    """
    Tabellen-OCR → Roh-Zeilen (heuristisch) — 1.9.0.
    Rückgabe: (rows, table_like).
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
        lines = [ln.split() for ln in plain.splitlines() if ln.strip()]
        return lines, False

    rows, table_like = _rows_from_tesseract_data(data)
    if not rows:
        plain = pytesseract.image_to_string(img, lang=lang)
        lines = [ln.split() for ln in plain.splitlines() if ln.strip()]
        return lines, False
    return rows, table_like


def ocr_image_to_csv(
    source: Union[str, Path, Image.Image],
    lang: str = "deu+eng",
    *,
    delimiter: str = ";",
) -> tuple[str, bool]:
    """OCR → CSV-String (UTF-8 BOM) + table_like-Flag — 1.9.0."""
    rows, table_like = ocr_image_table_rows(source, lang=lang)
    if not rows:
        return "\ufeff", False
    return format_rows_as_csv(rows, delimiter=delimiter), table_like


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

    line_rows, table_like = _rows_from_tesseract_data(data)
    if not line_rows:
        plain = pytesseract.image_to_string(img, lang=lang)
        return plain, False

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


# OCR-Render-DPI (Batch-Dialog): 150 / 300 — 1.1.2
OCR_DPI_CHOICES: tuple[int, ...] = (150, 300)
DEFAULT_OCR_DPI = 150


def dpi_to_scale(dpi: int) -> float:
    """DPI → pypdfium2-Render-Scale (72 DPI = 1.0)."""
    d = int(dpi) if dpi else DEFAULT_OCR_DPI
    if d not in OCR_DPI_CHOICES:
        d = min(OCR_DPI_CHOICES, key=lambda x: abs(x - d))
    return max(d / 72.0, 1.0)


@dataclass
class OcrDocumentResult:
    """Ergebnis einer Batch-OCR über PDF-Seiten (optional Bereich)."""

    text: str
    lang: str
    pages_done: int
    pages_total: int
    cancelled: bool = False
    page_texts: List[str] = field(default_factory=list)
    dpi: int = DEFAULT_OCR_DPI
    page_from: int = 1  # 1-basiert inkl.
    page_to: int = 0  # 1-basiert inkl.; 0 = Ende
    # (Seitennummer 1-basiert, Fehlermeldung) — 1.1.3
    page_errors: List[tuple[int, str]] = field(default_factory=list)


def _format_ocr_errors_section(page_errors: List[tuple[int, str]]) -> str:
    """Abschnitt „OCR-Fehler“ für Ergebnis-TXT — 1.1.3."""
    if not page_errors:
        return ""
    lines = ["--- OCR-Fehler ---"]
    for page_no, err in page_errors:
        msg = (err or "unbekannt").strip().replace("\n", " ")
        if len(msg) > 200:
            msg = msg[:197] + "…"
        lines.append(f"Seite {page_no}: {msg}")
    return "\n".join(lines) + "\n"


def ocr_pdf_document(
    pdf_path: str | Path,
    *,
    lang: str = "deu+eng",
    scale: float | None = None,
    dpi: int | None = None,
    page_from: int | None = None,
    page_to: int | None = None,
    attach_errors: bool = True,
    progress: Optional[Callable[[int, int, str], Optional[bool]]] = None,
) -> OcrDocumentResult:
    """
    OCR über PDF-Seiten (optional von–bis, 1-basiert inkl.).
    dpi 150/300 setzt scale=dpi/72; scale-Argument bleibt kompatibel.
    progress(page_1based, total_in_range, preview) → False zum Abbrechen.
    Seitenfehler werden gesammelt; mit attach_errors=True (Default) als Abschnitt
    angehängt (1.1.3/1.1.4). Abbruch behält Teilergebnis inkl. bisheriger Fehler.
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

    use_dpi = int(dpi) if dpi is not None else DEFAULT_OCR_DPI
    if use_dpi not in OCR_DPI_CHOICES:
        use_dpi = min(OCR_DPI_CHOICES, key=lambda x: abs(x - use_dpi))
    if scale is None:
        scale = dpi_to_scale(use_dpi)
    else:
        scale = max(float(scale), 1.0)

    start = 1 if page_from is None else max(1, int(page_from))
    end = total if page_to is None else min(total, int(page_to))
    if start > total:
        start = total if total else 1
    if end < start:
        end = start
    if total <= 0:
        return OcrDocumentResult(
            text="",
            lang=lang,
            pages_done=0,
            pages_total=0,
            cancelled=False,
            page_texts=[],
            dpi=use_dpi,
            page_from=start,
            page_to=end,
            page_errors=[],
        )

    indices = list(range(start - 1, end))  # 0-basiert
    range_total = len(indices)
    page_texts: List[str] = []
    page_errors: List[tuple[int, str]] = []
    cancelled = False
    for i, page in enumerate(indices):
        if progress is not None:
            cont = progress(
                i + 1,
                range_total,
                f"Seite {page + 1}/{total} ({i + 1}/{range_total})",
            )
            if cont is False:
                cancelled = True
                break
        page_no = page + 1
        try:
            img = render_page(pdf_path, page_index=page, scale=scale)
            page_texts.append(ocr_image(img, lang=lang))
        except OcrUnavailable:
            raise
        except Exception as e:
            page_texts.append("")
            page_errors.append((page_no, f"{type(e).__name__}: {e}"))

    parts: List[str] = []
    for i, t in enumerate(page_texts):
        page_no = indices[i] + 1
        header = f"--- Seite {page_no}/{total} ---"
        body = (t or "").rstrip()
        if not body and any(pe[0] == page_no for pe in page_errors):
            body = (
                "[OCR-Fehler — siehe Abschnitt am Ende]"
                if attach_errors
                else "[OCR-Fehler]"
            )
        parts.append(f"{header}\n{body}" if body else header)
    combined = "\n\n".join(parts).strip()
    err_section = (
        _format_ocr_errors_section(page_errors) if attach_errors else ""
    )
    if err_section:
        combined = (combined + "\n\n" + err_section) if combined else err_section
    elif combined:
        combined += "\n"
    return OcrDocumentResult(
        text=combined,
        lang=lang,
        pages_done=len(page_texts),
        pages_total=range_total,
        cancelled=cancelled,
        page_texts=page_texts,
        dpi=use_dpi,
        page_from=start,
        page_to=end,
        page_errors=page_errors,
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
    label = source_label or (
        str(source) if isinstance(source, (str, Path)) else "Bild"
    )
    if mode == OcrOutputMode.TABLE_CSV:
        csv_text, _used = ocr_image_to_csv(source, lang=lang)
        out_dir_p = Path(out_dir) if out_dir else Path.cwd()
        out_dir_p.mkdir(parents=True, exist_ok=True)
        stem = Path(label).stem if label else "ocr"
        csv_path = out_dir_p / f"{stem}_table.csv"
        csv_path.write_text(csv_text, encoding="utf-8")
        return OcrResult(
            text=csv_text,
            lang=lang,
            mode=mode,
            source_label=label,
            sidecar=csv_path,
        )

    text = ocr_image(source, lang=lang)
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
