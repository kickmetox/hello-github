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
