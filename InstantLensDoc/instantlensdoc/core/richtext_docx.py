"""DOCX ↔ HTML Rich-Text (Bold/Italic/Underline/Absätze) — 2.6.49.

Lädt DOCX via python-docx mit echten Zeichenformaten in HTML für QTextDocument.
Exportiert HTML (inkl. Qt-``toHtml()``-Spans) zurück nach DOCX/RTF ohne Markdown-Marker.
"""

from __future__ import annotations

import html as html_lib
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Optional


def _escape(text: str) -> str:
    return html_lib.escape(text or "", quote=False).replace("\n", "<br/>")


def _run_to_html(run: Any) -> str:
    text = run.text or ""
    if not text:
        return ""
    piece = _escape(text)
    # Unterstrich zuerst innen, dann Kursiv/Fett — wie typische Writer
    if bool(getattr(run, "underline", False)):
        piece = f"<u>{piece}</u>"
    if bool(getattr(run, "italic", False)):
        piece = f"<i>{piece}</i>"
    if bool(getattr(run, "bold", False)):
        piece = f"<b>{piece}</b>"
    return piece


def _heading_tag(style_name: str | None) -> str:
    name = (style_name or "").strip()
    m = re.match(r"Heading\s*([1-6])\b", name, re.I)
    if m:
        return f"h{m.group(1)}"
    if name.lower() in {"title", "subtitle"}:
        return "h1" if name.lower() == "title" else "h2"
    return "p"


def docx_to_html(path: str | Path) -> str:
    """DOCX → HTML mit <b>/<i>/<u> und Absätzen/Überschriften."""
    try:
        from docx import Document as DocxDocument
    except ImportError as e:
        raise RuntimeError("python-docx fehlt zum DOCX-Import") from e

    d = DocxDocument(str(path))
    parts: list[str] = [
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\"/></head><body>"
    ]
    for para in d.paragraphs:
        style_name = ""
        try:
            style_name = para.style.name if para.style is not None else ""
        except Exception:
            style_name = ""
        tag = _heading_tag(style_name)
        runs_html = [_run_to_html(r) for r in para.runs]
        inner = "".join(runs_html)
        if not inner and (para.text or ""):
            # Fallback wenn Runs leer, Text aber vorhanden
            inner = _escape(para.text)
        if not inner:
            inner = "<br/>"
        align = ""
        try:
            from docx.enum.text import WD_ALIGN_PARAGRAPH

            a = para.alignment
            if a == WD_ALIGN_PARAGRAPH.CENTER:
                align = ' style="text-align:center;"'
            elif a == WD_ALIGN_PARAGRAPH.RIGHT:
                align = ' style="text-align:right;"'
            elif a == WD_ALIGN_PARAGRAPH.JUSTIFY:
                align = ' style="text-align:justify;"'
        except Exception:
            pass
        parts.append(f"<{tag}{align}>{inner}</{tag}>")

    # Tabellen grob als HTML (ohne Zellformate reicht für Lesbarkeit)
    try:
        for tbl in d.tables:
            parts.append("<table border=\"1\" cellpadding=\"4\" cellspacing=\"0\">")
            for row in tbl.rows:
                parts.append("<tr>")
                for cell in row.cells:
                    cell_bits: list[str] = []
                    for p in cell.paragraphs:
                        cell_bits.append("".join(_run_to_html(r) for r in p.runs) or _escape(p.text))
                    parts.append(f"<td>{'<br/>'.join(cell_bits)}</td>")
                parts.append("</tr>")
            parts.append("</table>")
    except Exception:
        pass

    parts.append("</body></html>")
    return "".join(parts)


def docx_plain_and_html(path: str | Path) -> tuple[str, str]:
    """Liefert (Plaintext, HTML) aus einer DOCX-Datei."""
    html = docx_to_html(path)
    # Plain: einfache Tag-Entfernung
    plain = re.sub(r"(?i)<br\s*/?>", "\n", html)
    plain = re.sub(r"(?i)</p\s*>", "\n", plain)
    plain = re.sub(r"(?i)</h[1-6]\s*>", "\n", plain)
    plain = re.sub(r"(?i)</tr\s*>", "\n", plain)
    plain = re.sub(r"(?i)</td\s*>", "\t", plain)
    plain = re.sub(r"<[^>]+>", "", plain)
    plain = html_lib.unescape(plain)
    plain = re.sub(r"\n{3,}", "\n\n", plain).strip() + ("\n" if plain.strip() else "")
    return plain, html


class _HtmlToDocxParser(HTMLParser):
    """Minimaler HTML→DOCX-Parser für Qt-toHtml und docx_to_html-Ausgabe."""

    def __init__(self, document: Any) -> None:
        super().__init__(convert_charrefs=True)
        self.doc = document
        self._para: Any | None = None
        self._bold = 0
        self._italic = 0
        self._underline = 0
        self._skip = 0
        self._pending_align: str | None = None
        self._heading_level: int | None = None
        self._span_stack: list[tuple[bool, bool, bool]] = []

    def _ensure_para(self) -> Any:
        if self._para is None:
            if self._heading_level:
                self._para = self.doc.add_heading("", level=self._heading_level)
            else:
                self._para = self.doc.add_paragraph("")
            if self._pending_align:
                try:
                    from docx.enum.text import WD_ALIGN_PARAGRAPH

                    mapping = {
                        "center": WD_ALIGN_PARAGRAPH.CENTER,
                        "right": WD_ALIGN_PARAGRAPH.RIGHT,
                        "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
                        "left": WD_ALIGN_PARAGRAPH.LEFT,
                    }
                    al = mapping.get(self._pending_align)
                    if al is not None:
                        self._para.alignment = al
                except Exception:
                    pass
        return self._para

    def _add_text(self, text: str) -> None:
        if not text:
            return
        para = self._ensure_para()
        run = para.add_run(text)
        run.bold = self._bold > 0
        run.italic = self._italic > 0
        run.underline = self._underline > 0

    def _style_flags(self, style: str) -> tuple[bool, bool, bool]:
        s = (style or "").lower().replace(" ", "")
        bold = "font-weight:600" in s or "font-weight:700" in s or "font-weight:bold" in s
        italic = "font-style:italic" in s
        underline = "text-decoration:underline" in s or "text-decoration-line:underline" in s
        return bold, italic, underline

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        ad = {k.lower(): (v or "") for k, v in attrs}
        if t in {"script", "style", "head", "meta", "title"}:
            self._skip += 1
            return
        if self._skip:
            return
        if t in {"b", "strong"}:
            self._bold += 1
        elif t in {"i", "em"}:
            self._italic += 1
        elif t == "u":
            self._underline += 1
        elif t == "span":
            b, i, u = self._style_flags(ad.get("style", ""))
            if b:
                self._bold += 1
            if i:
                self._italic += 1
            if u:
                self._underline += 1
            self._span_stack.append((b, i, u))
        elif t in {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._para = None
            self._pending_align = None
            style = ad.get("style", "")
            if "text-align:center" in style.replace(" ", "").lower():
                self._pending_align = "center"
            elif "text-align:right" in style.replace(" ", "").lower():
                self._pending_align = "right"
            elif "text-align:justify" in style.replace(" ", "").lower():
                self._pending_align = "justify"
            if t.startswith("h") and t[1:].isdigit():
                self._heading_level = int(t[1])
            else:
                self._heading_level = None
        elif t == "br":
            self._add_text("\n")
        elif t == "li":
            self._para = None
            self._heading_level = None
            self._pending_align = None

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in {"script", "style", "head", "meta", "title"}:
            if self._skip:
                self._skip -= 1
            return
        if self._skip:
            return
        if t in {"b", "strong"}:
            self._bold = max(0, self._bold - 1)
        elif t in {"i", "em"}:
            self._italic = max(0, self._italic - 1)
        elif t == "u":
            self._underline = max(0, self._underline - 1)
        elif t == "span":
            stack = self._span_stack
            if stack:
                b, i, u = stack.pop()
                if b:
                    self._bold = max(0, self._bold - 1)
                if i:
                    self._italic = max(0, self._italic - 1)
                if u:
                    self._underline = max(0, self._underline - 1)
        elif t in {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li"}:
            if self._para is None:
                # leerer Absatz
                self._ensure_para()
            self._para = None
            self._heading_level = None
            self._pending_align = None

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        if not data:
            return
        # Qt liefert oft Newlines zwischen Tags — nur echte Textstücke schreiben
        if data.strip() == "" and "\n" in data and data.replace("\n", "").strip() == "":
            return
        self._add_text(data)


def html_to_docx(html: str, path: str | Path, *, title: Optional[str] = None) -> Path:
    """HTML (inkl. Qt-Spans) → DOCX mit Bold/Italic/Underline."""
    try:
        from docx import Document as DocxDocument
        from docx.shared import Pt
    except ImportError as e:
        raise RuntimeError("python-docx fehlt zum DOCX-Export") from e

    path = Path(path)
    d = DocxDocument()
    if title:
        try:
            d.core_properties.title = title
        except Exception:
            pass
    try:
        style = d.styles["Normal"]
        style.font.name = "Calibri"
        style.font.size = Pt(11)
    except Exception:
        pass

    parser = _HtmlToDocxParser(d)
    parser.feed(html or "")
    parser.close()
    if parser._para is None and not d.paragraphs:
        d.add_paragraph("")
    d.save(str(path))
    return path


def html_to_rtf(html: str, path: str | Path, *, title: Optional[str] = None) -> Path:
    """HTML → einfaches RTF mit \\b/\\i/\\ul."""

    class _Rtf(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.parts: list[str] = []
            self.bold = 0
            self.italic = 0
            self.underline = 0
            self.skip = 0
            self._span_stack: list[tuple[bool, bool, bool]] = []

        def _esc(self, s: str) -> str:
            out: list[str] = []
            for ch in s:
                o = ord(ch)
                if ch in {"\\", "{", "}"}:
                    out.append("\\" + ch)
                elif ch == "\n":
                    out.append("\\par\n")
                elif o < 128:
                    out.append(ch)
                else:
                    out.append(f"\\u{o}?")
            return "".join(out)

        def _style_flags(self, style: str) -> tuple[bool, bool, bool]:
            s = (style or "").lower().replace(" ", "")
            bold = "font-weight:600" in s or "font-weight:700" in s or "font-weight:bold" in s
            italic = "font-style:italic" in s
            underline = "text-decoration:underline" in s
            return bold, italic, underline

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            t = tag.lower()
            ad = {k.lower(): (v or "") for k, v in attrs}
            if t in {"script", "style", "head"}:
                self.skip += 1
                return
            if self.skip:
                return
            if t in {"b", "strong"}:
                self.bold += 1
                self.parts.append("\\b ")
            elif t in {"i", "em"}:
                self.italic += 1
                self.parts.append("\\i ")
            elif t == "u":
                self.underline += 1
                self.parts.append("\\ul ")
            elif t == "span":
                b, i, u = self._style_flags(ad.get("style", ""))
                self._span_stack.append((b, i, u))
                if b:
                    self.bold += 1
                    self.parts.append("\\b ")
                if i:
                    self.italic += 1
                    self.parts.append("\\i ")
                if u:
                    self.underline += 1
                    self.parts.append("\\ul ")
            elif t == "br":
                self.parts.append("\\par\n")
            elif t in {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li"}:
                if self.parts and not self.parts[-1].endswith("\\par\n"):
                    pass

        def handle_endtag(self, tag: str) -> None:
            t = tag.lower()
            if t in {"script", "style", "head"}:
                if self.skip:
                    self.skip -= 1
                return
            if self.skip:
                return
            if t in {"b", "strong"}:
                self.bold = max(0, self.bold - 1)
                self.parts.append("\\b0 ")
            elif t in {"i", "em"}:
                self.italic = max(0, self.italic - 1)
                self.parts.append("\\i0 ")
            elif t == "u":
                self.underline = max(0, self.underline - 1)
                self.parts.append("\\ul0 ")
            elif t == "span":
                if self._span_stack:
                    b, i, u = self._span_stack.pop()
                    if u:
                        self.underline = max(0, self.underline - 1)
                        self.parts.append("\\ul0 ")
                    if i:
                        self.italic = max(0, self.italic - 1)
                        self.parts.append("\\i0 ")
                    if b:
                        self.bold = max(0, self.bold - 1)
                        self.parts.append("\\b0 ")
            elif t in {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"}:
                self.parts.append("\\par\n")

        def handle_data(self, data: str) -> None:
            if self.skip or not data:
                return
            if data.strip() == "" and data.replace("\n", "").strip() == "":
                return
            self.parts.append(self._esc(data))

    path = Path(path)
    header = [
        r"{\rtf1\ansi\deff0",
        r"{\fonttbl{\f0 Times New Roman;}{\f1 Segoe UI;}}",
    ]
    if title:
        from instantlensdoc.core.export import _rtf_escape

        header.append(r"{\info{\title " + _rtf_escape(title) + "}}")
    header.append(r"\f0\fs22 ")
    parser = _Rtf()
    parser.feed(html or "")
    parser.close()
    path.write_text("".join(header) + "".join(parser.parts) + "}", encoding="utf-8", errors="replace")
    return path


def html_has_char_formats(html: str) -> bool:
    """True wenn HTML Bold/Italic/Underline-Marker enthält."""
    h = html or ""
    if re.search(r"(?i)</?(b|strong|i|em|u)\b", h):
        return True
    if re.search(r"(?i)font-weight\s*:\s*(bold|[6-9]00)", h):
        return True
    if re.search(r"(?i)font-style\s*:\s*italic", h):
        return True
    if re.search(r"(?i)text-decoration[^;]*underline", h):
        return True
    return False
