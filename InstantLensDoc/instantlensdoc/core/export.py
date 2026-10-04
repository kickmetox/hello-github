"""Export/Import: Editor-Inhalt → HTML / DOCX / PDF / TXT / RTF / XLSX / JPG — 2.6.14."""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any, Optional

SUPPORTED_EXPORT_FORMATS: tuple[str, ...] = (
    "docx",
    "xlsx",
    "pdf",
    "txt",
    "rtf",
    "html",
    "jpg",
    "jpeg",
)
SUPPORTED_IMPORT_FORMATS: tuple[str, ...] = (
    "docx",
    "xlsx",
    "pdf",
    "txt",
    "rtf",
    "html",
    "htm",
    "csv",
    "md",
    "markdown",
    "jpg",
    "jpeg",
    "png",
)


def _lines(text: str) -> list[str]:
    return (text or "").replace("\r\n", "\n").split("\n")


def list_export_formats() -> list[dict[str, str]]:
    return [
        {"id": "docx", "ext": ".docx", "name": "Microsoft Word"},
        {"id": "xlsx", "ext": ".xlsx", "name": "Microsoft Excel (Tabellen)"},
        {"id": "pdf", "ext": ".pdf", "name": "PDF"},
        {"id": "txt", "ext": ".txt", "name": "Plain Text"},
        {"id": "rtf", "ext": ".rtf", "name": "Rich Text Format"},
        {"id": "html", "ext": ".html", "name": "HTML"},
        {"id": "jpg", "ext": ".jpg", "name": "JPEG-Bild"},
    ]


def list_import_formats() -> list[dict[str, str]]:
    return [
        {"id": "docx", "ext": ".docx", "name": "Microsoft Word"},
        {"id": "xlsx", "ext": ".xlsx", "name": "Microsoft Excel"},
        {"id": "csv", "ext": ".csv", "name": "CSV (Tabellen)"},
        {"id": "pdf", "ext": ".pdf", "name": "PDF"},
        {"id": "txt", "ext": ".txt", "name": "Plain Text"},
        {"id": "rtf", "ext": ".rtf", "name": "Rich Text Format"},
        {"id": "html", "ext": ".html", "name": "HTML"},
        {"id": "md", "ext": ".md", "name": "Markdown"},
        {"id": "jpg", "ext": ".jpg", "name": "JPEG/PNG Bild"},
    ]

def export_html(
    text: str,
    path: str | Path,
    *,
    title: str = "InstantLens Doc",
    as_markdownish: bool = True,
) -> Path:
    """
    Schreibt UTF-8-HTML. Bei as_markdownish: #/## Überschriften, leere Zeile = Absatz.
    """
    path = Path(path)
    body_parts: list[str] = []
    if as_markdownish:
        paras: list[str] = []
        buf: list[str] = []

        def flush():
            nonlocal buf
            if not buf:
                return
            joined = " ".join(buf).strip()
            buf = []
            if not joined:
                return
            if joined.startswith("### "):
                paras.append(f"<h3>{html.escape(joined[4:])}</h3>")
            elif joined.startswith("## "):
                paras.append(f"<h2>{html.escape(joined[3:])}</h2>")
            elif joined.startswith("# "):
                paras.append(f"<h1>{html.escape(joined[2:])}</h1>")
            elif joined.startswith("- "):
                paras.append(f"<li>{html.escape(joined[2:])}</li>")
            else:
                paras.append(f"<p>{html.escape(joined)}</p>")

        for line in _lines(text):
            if not line.strip():
                flush()
            else:
                # Listenzeilen einzeln flushen
                if line.strip().startswith("- ") and buf:
                    flush()
                buf.append(line.strip())
        flush()
        # li ohne ul wrappen
        out: list[str] = []
        in_ul = False
        for p in paras:
            if p.startswith("<li>"):
                if not in_ul:
                    out.append("<ul>")
                    in_ul = True
                out.append(p)
            else:
                if in_ul:
                    out.append("</ul>")
                    in_ul = False
                out.append(p)
        if in_ul:
            out.append("</ul>")
        body_parts = out
    else:
        body_parts = [f"<pre>{html.escape(text)}</pre>"]

    doc = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8"/>
<meta name="generator" content="InstantLens Doc"/>
<title>{html.escape(title)}</title>
<style>
body {{ font-family: Georgia, 'Times New Roman', serif; max-width: 42rem;
       margin: 2rem auto; padding: 0 1rem; line-height: 1.55; color: #1a1a1a; }}
h1,h2,h3 {{ font-family: 'Segoe UI', system-ui, sans-serif; }}
pre {{ white-space: pre-wrap; font-family: Consolas, monospace; }}
</style>
</head>
<body>
{"".join(body_parts)}
</body>
</html>
"""
    path.write_text(doc, encoding="utf-8")
    return path


def export_docx(text: str, path: str | Path, *, title: Optional[str] = None) -> Path:
    """DOCX mit Absätzen; Zeilen mit # werden Heading-Styles."""
    try:
        from docx import Document as DocxDocument
        from docx.shared import Pt
    except ImportError as e:
        raise RuntimeError("python-docx fehlt zum DOCX-Export") from e

    path = Path(path)
    d = DocxDocument()
    if title:
        d.core_properties.title = title
    style = d.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    for line in _lines(text):
        raw = line.rstrip()
        if not raw:
            d.add_paragraph("")
            continue
        if raw.startswith("### "):
            d.add_heading(raw[4:], level=3)
        elif raw.startswith("## "):
            d.add_heading(raw[3:], level=2)
        elif raw.startswith("# "):
            d.add_heading(raw[2:], level=1)
        elif re.match(r"^[-*]\s+", raw):
            d.add_paragraph(re.sub(r"^[-*]\s+", "", raw), style="List Bullet")
        else:
            d.add_paragraph(raw)
    d.save(str(path))
    return path


def resolve_page_size(name_or_size: str | tuple[float, float] | None = None) -> tuple[float, float]:
    """Seitenformat aus Preset-Name oder Tupel; Default aus Einstellungen."""
    if isinstance(name_or_size, tuple) and len(name_or_size) == 2:
        return float(name_or_size[0]), float(name_or_size[1])
    from ild_pdf.pages import PAGE_SIZE_PRESETS

    name = name_or_size
    if not name:
        try:
            from instantlensdoc.core.app_settings import get_export_pdf_page

            name = get_export_pdf_page()
        except Exception:
            name = "A4"
    return PAGE_SIZE_PRESETS.get(str(name), PAGE_SIZE_PRESETS["A4"])


def export_pdf(
    text: str,
    path: str | Path,
    *,
    title: str = "InstantLens Doc",
    page_size: tuple[float, float] | str | None = None,
) -> Path:
    """
    Einfaches Mehrseiten-PDF aus Plaintext (Helvetica via pikepdf Seiten).
    Delegiert an ild_pdf.text_pdf.text_to_pdf — 1.7.0.
    page_size: Tupel, Preset-Name oder None (= Einstellung/A4).
    """
    from ild_pdf.text_pdf import text_to_pdf

    return text_to_pdf(
        text,
        path,
        title=title,
        page_size=resolve_page_size(page_size),
    )


def export_txt(text: str, path: str | Path, *, encoding: str = "utf-8") -> Path:
    """Plaintext speichern — 2.6.14."""
    path = Path(path)
    path.write_text(text or "", encoding=encoding, errors="replace")
    return path


def _rtf_escape(s: str) -> str:
    out: list[str] = []
    for ch in s or "":
        o = ord(ch)
        if ch in {"\\", "{", "}"}:
            out.append("\\" + ch)
        elif ch == "\n":
            out.append("\\par\n")
        elif ch == "\t":
            out.append("\\tab ")
        elif o < 128:
            out.append(ch)
        else:
            out.append(f"\\u{o}?")
    return "".join(out)


def export_rtf(text: str, path: str | Path, *, title: Optional[str] = None) -> Path:
    """Einfaches RTF (Absätze, Überschriften #/##) — 2.6.14."""
    path = Path(path)
    parts = [
        r"{\rtf1\ansi\deff0",
        r"{\fonttbl{\f0 Times New Roman;}{\f1 Segoe UI;}}",
    ]
    if title:
        parts.append(r"{\info{\title " + _rtf_escape(title) + "}}")
    parts.append(r"\f0\fs22 ")
    for line in _lines(text):
        raw = line.rstrip()
        if not raw:
            parts.append(r"\par")
            continue
        if raw.startswith("### "):
            parts.append(r"\f1\fs24\b " + _rtf_escape(raw[4:]) + r"\b0\f0\fs22\par")
        elif raw.startswith("## "):
            parts.append(r"\f1\fs28\b " + _rtf_escape(raw[3:]) + r"\b0\f0\fs22\par")
        elif raw.startswith("# "):
            parts.append(r"\f1\fs32\b " + _rtf_escape(raw[2:]) + r"\b0\f0\fs22\par")
        else:
            parts.append(_rtf_escape(raw) + r"\par")
    parts.append("}")
    path.write_text("".join(parts), encoding="utf-8", errors="replace")
    return path


def import_rtf(path: str | Path) -> str:
    """Grober RTF→Text-Import (Steuerworte entfernen) — 2.6.14."""
    raw = Path(path).read_text(encoding="utf-8", errors="replace")
    # Unicode escapes \uN?
    def _u_repl(m: re.Match[str]) -> str:
        try:
            return chr(int(m.group(1)))
        except ValueError:
            return ""

    raw = re.sub(r"\\u(-?\d+)\??", _u_repl, raw)
    raw = raw.replace("\\par", "\n").replace("\\tab", "\t").replace("\\line", "\n")
    # Drop groups like {\*\…} roughly
    raw = re.sub(r"\{\\\*[^}]*\}", "", raw)
    raw = re.sub(r"\\[a-zA-Z]+\d* ?", "", raw)
    raw = raw.replace("{", "").replace("}", "").replace("\\\\", "\\")
    return raw.strip() + ("\n" if raw.strip() else "")


def export_xlsx_from_text(
    text: str,
    path: str | Path,
    *,
    sheet_name: str = "Tabelle1",
) -> Path:
    """Tabellen aus Text (Markdown/ild-table) oder Zeilen→XLSX — 2.6.14."""
    from ild_pdf.tables import (
        create_table,
        export_table_xlsx,
        find_tables_in_text,
        parse_table,
    )

    path = Path(path)
    found = find_tables_in_text(text or "")
    if found:
        return export_table_xlsx(found[0][2], path, sheet_name=sheet_name)
    # Fallback: Zeilen als einspaltige Tabelle / TSV
    rows: list[list[str]] = []
    for line in _lines(text):
        if "\t" in line:
            rows.append(line.split("\t"))
        elif ";" in line and line.count(";") >= 1:
            rows.append([c.strip() for c in line.split(";")])
        else:
            rows.append([line])
    if not rows:
        rows = [[""]]
    return export_table_xlsx(create_table(data=rows, header=False), path, sheet_name=sheet_name)


def export_jpg(
    text: str,
    path: str | Path,
    *,
    title: str = "InstantLens Doc",
    width: int = 1200,
    margin: int = 40,
    bg: str = "#FFFFFF",
    fg: str = "#1A1A1A",
) -> Path:
    """Text als JPEG-Bild (Pillow) — 2.6.14."""
    from PIL import Image, ImageDraw, ImageFont

    path = Path(path)
    lines = _lines(text)
    if not lines:
        lines = [title or " "]
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 18)
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
        title_font = font
    line_h = 24
    height = margin * 2 + line_h * (len(lines) + 2)
    height = max(height, 200)
    img = Image.new("RGB", (int(width), int(height)), bg)
    draw = ImageDraw.Draw(img)
    y = margin
    if title:
        draw.text((margin, y), title, fill=fg, font=title_font)
        y += line_h + 8
    for line in lines[:200]:
        draw.text((margin, y), line[:200], fill=fg, font=font)
        y += line_h
        if y > height - margin:
            break
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(path), format="JPEG", quality=90)
    return path


def export_document(
    text: str,
    path: str | Path,
    *,
    fmt: str | None = None,
    title: str = "InstantLens Doc",
    page_size: tuple[float, float] | str | None = None,
) -> Path:
    """Unified Export nach Erweiterung/Format — 2.6.14."""
    path = Path(path)
    f = (fmt or path.suffix.lstrip(".")).lower().lstrip(".")
    if f == "jpeg":
        f = "jpg"
    if f == "htm":
        f = "html"
    if f == "html":
        return export_html(text, path, title=title)
    if f == "docx":
        return export_docx(text, path, title=title)
    if f == "pdf":
        return export_pdf(text, path, title=title, page_size=page_size)
    if f == "txt":
        return export_txt(text, path)
    if f == "rtf":
        return export_rtf(text, path, title=title)
    if f == "xlsx":
        return export_xlsx_from_text(text, path)
    if f == "jpg":
        return export_jpg(text, path, title=title)
    raise ValueError(f"Unbekanntes Export-Format: {f}")


def import_document_text(path: str | Path) -> dict[str, Any]:
    """Unified Import → Plaintext (+ Meta) — 2.6.14."""
    from ild_pdf.tables import import_csv, import_xlsx, table_to_markdown

    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    ext = path.suffix.lower().lstrip(".")
    meta: dict[str, Any] = {"path": str(path), "format": ext}
    if ext in ("txt", "log", "md", "markdown", "html", "htm", "csv"):
        if ext == "csv":
            table = import_csv(path)
            return {"text": table_to_markdown(table), "meta": {**meta, "table": table.to_dict()}}
        text = path.read_text(encoding="utf-8", errors="replace")
        return {"text": text, "meta": meta}
    if ext == "rtf":
        return {"text": import_rtf(path), "meta": meta}
    if ext == "docx":
        try:
            from docx import Document as DocxDocument

            from ild_pdf.tables import create_table, table_to_markdown

            d = DocxDocument(str(path))
            parts: list[str] = [p.text for p in d.paragraphs]
            for ti, tbl in enumerate(d.tables):
                cells = [[(c.text or "") for c in row.cells] for row in tbl.rows]
                parts.append(
                    table_to_markdown(create_table(data=cells, table_id=f"docx{ti + 1}"))
                )
            return {"text": "\n".join(parts), "meta": meta}
        except ImportError as e:
            raise RuntimeError("python-docx fehlt zum DOCX-Import") from e
    if ext == "xlsx":
        table = import_xlsx(path)
        return {"text": table_to_markdown(table), "meta": {**meta, "table": table.to_dict()}}
    if ext == "pdf":
        try:
            import pypdfium2 as pdfium

            doc = pdfium.PdfDocument(str(path))
            try:
                chunks: list[str] = []
                for i in range(len(doc)):
                    page = doc[i]
                    try:
                        textpage = page.get_textpage()
                        try:
                            chunks.append(textpage.get_text_bounded() or "")
                        finally:
                            textpage.close()
                    except Exception:
                        chunks.append("")
                return {
                    "text": "\n\n".join(chunks).strip() + ("\n" if chunks else ""),
                    "meta": {**meta, "pages": len(doc)},
                }
            finally:
                doc.close()
        except Exception:
            return {"text": "", "meta": {**meta, "note": "PDF ohne Textlayer"}}
    if ext in ("jpg", "jpeg", "png", "bmp", "gif", "webp"):
        return {"text": f"[Bild: {path.name}]\n", "meta": {**meta, "image": str(path)}}
    # Fallback plaintext
    return {"text": path.read_text(encoding="utf-8", errors="replace"), "meta": meta}
