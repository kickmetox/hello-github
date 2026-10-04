"""Export/Import: Editor-Inhalt → HTML / DOCX / PDF / TXT / RTF / XLSX / JPG / EPUB — 2.6.27."""

from __future__ import annotations

import html
import re
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

SUPPORTED_EXPORT_FORMATS: tuple[str, ...] = (
    "docx",
    "xlsx",
    "pdf",
    "txt",
    "rtf",
    "html",
    "jpg",
    "jpeg",
    "epub",
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
    "epub",
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
        {"id": "epub", "ext": ".epub", "name": "EPUB (E-Book)"},
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
        {"id": "epub", "ext": ".epub", "name": "EPUB (E-Book Text)"},
    ]

def _inline_md_to_html(fragment: str) -> str:
    """Escape + Markdown-Links → <a>."""
    from instantlensdoc.core.hyperlinks import _MD_LINK_RE, validate_hyperlink

    parts: list[str] = []
    pos = 0
    for m in _MD_LINK_RE.finditer(fragment or ""):
        parts.append(html.escape((fragment or "")[pos : m.start()]))
        label, tgt = m.group(1), m.group(2)
        ok, norm, _k, _e = validate_hyperlink(label, tgt)
        if ok:
            parts.append(
                f'<a href="{html.escape(norm, quote=True)}">{html.escape(label)}</a>'
            )
        else:
            parts.append(html.escape(m.group(0)))
        pos = m.end()
    parts.append(html.escape((fragment or "")[pos:]))
    return "".join(parts)


def _markdownish_body_parts(text: str) -> list[str]:
    """Markdownish → HTML-Fragmente; Markdown-Links → <a> — 2.6.27."""
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
            paras.append(f"<h3>{_inline_md_to_html(joined[4:])}</h3>")
        elif joined.startswith("## "):
            paras.append(f"<h2>{_inline_md_to_html(joined[3:])}</h2>")
        elif joined.startswith("# "):
            paras.append(f"<h1>{_inline_md_to_html(joined[2:])}</h1>")
        elif joined.startswith("- "):
            paras.append(f"<li>{_inline_md_to_html(joined[2:])}</li>")
        else:
            paras.append(f"<p>{_inline_md_to_html(joined)}</p>")

    for line in _lines(text):
        if not line.strip():
            flush()
        else:
            if line.strip().startswith("- ") and buf:
                flush()
            buf.append(line.strip())
    flush()
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
    return out


def export_html(
    text: str,
    path: str | Path,
    *,
    title: str = "InstantLens Doc",
    as_markdownish: bool = True,
) -> Path:
    """
    Schreibt UTF-8-HTML. Bei as_markdownish: #/## Überschriften, leere Zeile = Absatz.
    Markdown-Hyperlinks werden zu <a href> — 2.6.27.
    """
    path = Path(path)
    if as_markdownish:
        body_parts = _markdownish_body_parts(text)
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
a {{ color: #0b5cab; }}
</style>
</head>
<body>
{"".join(body_parts)}
</body>
</html>
"""
    path.write_text(doc, encoding="utf-8")
    return path


def export_epub(
    text: str,
    path: str | Path,
    *,
    title: str = "InstantLens Doc",
    author: str = "InstantLens Doc",
    language: str = "de",
) -> Path:
    """
    EPUB 2.0.1 (ohne externe Abhängigkeit) — Kapitel aus Markdownish-Text — 2.6.27.
    Struktur: mimetype + META-INF/container.xml + OEBPS/{content.opf,toc.ncx,chapter*.xhtml}.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    book_id = f"urn:uuid:{uuid4()}"
    # Kapitel an H1 splitten, sonst ein Kapitel
    raw = (text or "").replace("\r\n", "\n")
    chunks: list[tuple[str, str]] = []
    current_title = title or "Kapitel 1"
    current_lines: list[str] = []
    for line in raw.split("\n"):
        if line.startswith("# ") and not line.startswith("## "):
            if current_lines and any(x.strip() for x in current_lines):
                chunks.append((current_title, "\n".join(current_lines).strip()))
            current_title = line[2:].strip() or f"Kapitel {len(chunks) + 1}"
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines and any(x.strip() for x in current_lines):
        chunks.append((current_title, "\n".join(current_lines).strip()))
    if not chunks:
        chunks = [(title or "Inhalt", raw or "")]

    chapters: list[tuple[str, str, str]] = []  # id, title, xhtml_body
    for i, (ch_title, ch_text) in enumerate(chunks, start=1):
        cid = f"chap{i:02d}"
        body = "".join(_markdownish_body_parts(ch_text if ch_text.strip() else ch_title))
        xhtml = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" '
            '"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="'
            + html.escape(language)
            + '">\n<head><title>'
            + html.escape(ch_title)
            + "</title>"
            "<style type=\"text/css\">body{font-family:serif;line-height:1.5;margin:1em;}"
            "a{color:#0b5cab;}</style></head>\n<body>\n"
            f"<h1 id=\"{cid}\">{html.escape(ch_title)}</h1>\n"
            f"{body}\n</body></html>\n"
        )
        chapters.append((cid, ch_title, xhtml))

    manifest_items = []
    spine_items = []
    nav_points = []
    for i, (cid, ch_title, _x) in enumerate(chapters, start=1):
        href = f"{cid}.xhtml"
        manifest_items.append(
            f'<item id="{cid}" href="{href}" media-type="application/xhtml+xml"/>'
        )
        spine_items.append(f'<itemref idref="{cid}"/>')
        nav_points.append(
            f'<navPoint id="nav{i}" playOrder="{i}">'
            f"<navLabel><text>{html.escape(ch_title)}</text></navLabel>"
            f'<content src="{href}"/>'
            f"</navPoint>"
        )

    opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:title>{html.escape(title)}</dc:title>
    <dc:creator opf:role="aut">{html.escape(author or "InstantLens Doc")}</dc:creator>
    <dc:language>{html.escape(language)}</dc:language>
    <dc:identifier id="BookId">{html.escape(book_id)}</dc:identifier>
    <meta name="generator" content="InstantLens Doc"/>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    {"".join(manifest_items)}
  </manifest>
  <spine toc="ncx">
    {"".join(spine_items)}
  </spine>
</package>
"""
    ncx = f"""<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="{html.escape(book_id)}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>{html.escape(title)}</text></docTitle>
  <navMap>
    {"".join(nav_points)}
  </navMap>
</ncx>
"""
    container = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # mimetype muss unkomprimiert und erstes Entry sein
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml", container, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/content.opf", opf, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/toc.ncx", ncx, compress_type=zipfile.ZIP_DEFLATED)
        for cid, _t, xhtml in chapters:
            zf.writestr(
                f"OEBPS/{cid}.xhtml",
                xhtml.encode("utf-8"),
                compress_type=zipfile.ZIP_DEFLATED,
            )
    path.write_bytes(buf.getvalue())
    return path


def import_epub(path: str | Path) -> str:
    """EPUB → Plaintext (Kapitel-Titel + Body) — 2.6.27."""
    path = Path(path)
    parts: list[str] = []
    with zipfile.ZipFile(path, "r") as zf:
        names = [
            n
            for n in zf.namelist()
            if n.lower().endswith((".xhtml", ".html", ".htm"))
            and "meta-inf" not in n.lower()
        ]
        names.sort()
        for name in names:
            raw = zf.read(name).decode("utf-8", errors="replace")
            # Tags grob entfernen
            t = re.sub(r"(?is)<script[^>]*>.*?</script>", "", raw)
            t = re.sub(r"(?is)<style[^>]*>.*?</style>", "", t)
            t = re.sub(r"(?i)<br\s*/?>", "\n", t)
            t = re.sub(r"(?i)</p>", "\n\n", t)
            t = re.sub(r"(?i)</h[1-6]>", "\n\n", t)
            t = re.sub(r"(?i)<h1[^>]*>", "# ", t)
            t = re.sub(r"(?i)<h2[^>]*>", "## ", t)
            t = re.sub(r"(?i)<h3[^>]*>", "### ", t)
            t = re.sub(r"<[^>]+>", "", t)
            t = html.unescape(t)
            t = re.sub(r"\n{3,}", "\n\n", t).strip()
            if t:
                parts.append(t)
    return "\n\n".join(parts).strip() + ("\n" if parts else "")


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
    author: str = "InstantLens Doc",
) -> Path:
    """Unified Export nach Erweiterung/Format — 2.6.14 / EPUB 2.6.27."""
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
    if f == "epub":
        return export_epub(text, path, title=title, author=author)
    raise ValueError(f"Unbekanntes Export-Format: {f}")


def import_document_text(path: str | Path) -> dict[str, Any]:
    """Unified Import → Plaintext (+ Meta) — 2.6.14."""
    from ild_pdf.tables import import_csv, import_xlsx, table_to_markdown

    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    ext = path.suffix.lower().lstrip(".")
    meta: dict[str, Any] = {"path": str(path), "format": ext}
    if ext == "epub":
        return {"text": import_epub(path), "meta": meta}
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
