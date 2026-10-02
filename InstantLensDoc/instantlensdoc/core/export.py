"""Export: Editor-Inhalt → HTML / verbessertes DOCX / einfaches PDF."""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Optional


def _lines(text: str) -> list[str]:
    return (text or "").replace("\r\n", "\n").split("\n")


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


def export_pdf(
    text: str,
    path: str | Path,
    *,
    title: str = "InstantLens Doc",
    page_size: tuple[float, float] = (595.0, 842.0),  # A4
) -> Path:
    """
    Einfaches Mehrseiten-PDF aus Plaintext (Helvetica via pikepdf).
    Kein Layout-Engine — Zeilenumbruch nach Zeichenzahl.
    """
    import pikepdf
    from pikepdf import Dictionary, Name, Stream

    path = Path(path)
    page_w, page_h = page_size
    margin = 50.0
    font_size = 11.0
    line_h = font_size * 1.35
    usable_w = page_w - 2 * margin
    chars_per_line = max(int(usable_w / (font_size * 0.5)), 40)

    def wrap(paragraph: str) -> list[str]:
        if not paragraph:
            return [""]
        words = paragraph.split()
        if not words:
            return [""]
        lines: list[str] = []
        cur = words[0]
        for w in words[1:]:
            if len(cur) + 1 + len(w) <= chars_per_line:
                cur = f"{cur} {w}"
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        return lines

    all_lines: list[str] = []
    for para in _lines(text):
        all_lines.extend(wrap(para))

    lines_per_page = max(int((page_h - 2 * margin) / line_h), 1)
    pages_lines = [
        all_lines[i : i + lines_per_page] for i in range(0, max(len(all_lines), 1), lines_per_page)
    ]
    if not pages_lines:
        pages_lines = [[""]]

    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    pdf = pikepdf.Pdf.new()
    font = Dictionary(
        Type=Name.Font,
        Subtype=Name.Type1,
        BaseFont=Name.Helvetica,
    )
    for plines in pages_lines:
        parts = ["BT", f"/F1 {font_size:.1f} Tf", f"1 0 0 1 {margin:.1f} {page_h - margin:.1f} Tm"]
        first = True
        for line in plines:
            if first:
                parts.append(f"({esc(line)}) Tj")
                first = False
            else:
                parts.append(f"0 {-line_h:.2f} Td ({esc(line)}) Tj")
        parts.append("ET")
        content = "\n".join(parts).encode("latin-1", errors="replace")
        page = pdf.add_blank_page(page_size=(page_w, page_h))
        page[Name.Resources] = Dictionary(Font=Dictionary(F1=font))
        page[Name.Contents] = Stream(pdf, content)

    if title:
        with pdf.open_metadata() as meta:
            meta["dc:title"] = title
    pdf.save(path)
    return path
