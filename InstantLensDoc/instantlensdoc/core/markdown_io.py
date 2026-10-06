"""Markdown ↔ HTML für den Word-Suite-Editor (kein sichtbares ¶).

Round-Trip: Überschriften, Listen, Fett/Kursiv, Links, Tabellen, Code.
Qt ``QTextDocument.toMarkdown`` wird bevorzugt, wenn verfügbar.
"""

from __future__ import annotations

import html as html_mod
import re
from html.parser import HTMLParser

_PILCROW_RE = re.compile(r"[\u00b6\u00a7\x0c\u2028]+")
_FENCE_RE = re.compile(r"^```(\w*)\s*$")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_UL_RE = re.compile(r"^(\s*)([-*+])\s+(.*)$")
_OL_RE = re.compile(r"^(\s*)(\d{1,3})[.)]\s+(.*)$")
_HR_RE = re.compile(r"^(-{3,}|\*{3,}|_{3,})\s*$")
_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BOLD_ITALIC_RE = re.compile(r"\*\*\*(.+?)\*\*\*|___(.+?)___")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)|(?<!_)_(?!_)(.+?)(?<!_)_(?!_)")


def strip_pilcrow(text: str) -> str:
    """Absatzmarken/Form-Feed entfernen — Speichern ohne sichtbares ¶."""
    s = _PILCROW_RE.sub("", text or "")
    s = s.replace("\u2029", "\n")
    return s


def markdown_to_html(src: str) -> str:
    """Markdown → HTML-Fragment für ``QTextDocument.setHtml``."""
    text = strip_pilcrow(src or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    body: list[str] = []
    i = 0
    in_code = False
    code_lang = ""
    code_buf: list[str] = []
    para: list[str] = []
    list_kind = ""  # ul|ol
    list_buf: list[str] = []

    def flush_para() -> None:
        nonlocal para
        if not para:
            return
        joined = " ".join(para).strip()
        para = []
        if joined:
            body.append(f"<p>{_inline_md(joined)}</p>")

    def flush_list() -> None:
        nonlocal list_kind, list_buf
        if not list_buf:
            list_kind = ""
            return
        tag = list_kind or "ul"
        items = "".join(f"<li>{_inline_md(x)}</li>" for x in list_buf)
        body.append(f"<{tag}>{items}</{tag}>")
        list_buf = []
        list_kind = ""

    def flush_code() -> None:
        nonlocal code_buf, code_lang
        lang = html_mod.escape(code_lang or "")
        cls = f' class="language-{lang}"' if lang else ""
        inner = html_mod.escape("\n".join(code_buf))
        body.append(f"<pre><code{cls}>{inner}</code></pre>")
        code_buf = []
        code_lang = ""

    while i < len(lines):
        line = lines[i]
        if in_code:
            if _FENCE_RE.match(line.strip()):
                in_code = False
                flush_code()
            else:
                code_buf.append(line)
            i += 1
            continue
        stripped = line.strip()
        fence = _FENCE_RE.match(stripped)
        if fence:
            flush_para()
            flush_list()
            in_code = True
            code_lang = fence.group(1) or ""
            i += 1
            continue
        if not stripped:
            flush_para()
            flush_list()
            i += 1
            continue
        if _HR_RE.match(stripped):
            flush_para()
            flush_list()
            body.append("<hr/>")
            i += 1
            continue
        hm = _HEADING_RE.match(stripped)
        if hm:
            flush_para()
            flush_list()
            level = min(6, len(hm.group(1)))
            body.append(f"<h{level}>{_inline_md(hm.group(2).strip())}</h{level}>")
            i += 1
            continue
        table_block = _take_table(lines, i)
        if table_block is not None:
            flush_para()
            flush_list()
            html_table, consumed = table_block
            body.append(html_table)
            i += consumed
            continue
        um = _UL_RE.match(line)
        om = _OL_RE.match(line)
        if um or om:
            flush_para()
            kind = "ul" if um else "ol"
            item = um.group(3) if um else om.group(3)
            if list_kind and list_kind != kind:
                flush_list()
            list_kind = kind
            list_buf.append(item)
            i += 1
            continue
        flush_list()
        para.append(stripped)
        i += 1
    if in_code:
        flush_code()
    flush_para()
    flush_list()
    inner = "".join(body) or "<p></p>"
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'/></head>"
        f"<body>{inner}</body></html>"
    )


def _inline_md(fragment: str) -> str:
    """Inline-Markdown: Code, Links, Fett/Kursiv — rest escapen."""
    s = fragment or ""
    parts: list[str] = []
    pos = 0
    # Placeholders for spans we already converted
    slots: dict[str, str] = {}

    def stash(html: str) -> str:
        key = f"\x00MD{len(slots)}\x00"
        slots[key] = html
        return key

    def repl_code(m: re.Match) -> str:
        return stash(f"<code>{html_mod.escape(m.group(1))}</code>")

    def repl_link(m: re.Match) -> str:
        label, href = m.group(1), m.group(2)
        return stash(
            f'<a href="{html_mod.escape(href, quote=True)}">{html_mod.escape(label)}</a>'
        )

    s = _INLINE_CODE_RE.sub(repl_code, s)
    s = _LINK_RE.sub(repl_link, s)

    def repl_bi(m: re.Match) -> str:
        inner = m.group(1) or m.group(2) or ""
        return stash(f"<strong><em>{html_mod.escape(inner)}</em></strong>")

    def repl_b(m: re.Match) -> str:
        inner = m.group(1) or m.group(2) or ""
        return stash(f"<strong>{html_mod.escape(inner)}</strong>")

    def repl_i(m: re.Match) -> str:
        inner = m.group(1) or m.group(2) or ""
        return stash(f"<em>{html_mod.escape(inner)}</em>")

    s = _BOLD_ITALIC_RE.sub(repl_bi, s)
    s = _BOLD_RE.sub(repl_b, s)
    s = _ITALIC_RE.sub(repl_i, s)
    s = html_mod.escape(s)
    for key, val in slots.items():
        s = s.replace(html_mod.escape(key), val)
        s = s.replace(key, val)
    return s


def _take_table(lines: list[str], start: int) -> tuple[str, int] | None:
    if start >= len(lines) or not _TABLE_ROW_RE.match(lines[start]):
        return None
    rows: list[str] = []
    i = start
    while i < len(lines) and _TABLE_ROW_RE.match(lines[i]):
        rows.append(lines[i])
        i += 1
    if len(rows) < 2:
        return None
    parsed: list[list[str]] = []
    sep_idx = None
    for ri, raw in enumerate(rows):
        if _TABLE_SEP_RE.match(raw.strip()):
            sep_idx = ri
            continue
        cells = _split_pipe_row(raw)
        parsed.append(cells)
    if not parsed:
        return None
    # Header = first row if separator present
    header = sep_idx == 1 or (sep_idx is None and len(parsed) >= 1)
    try:
        from ild_pdf.tables import DocumentTable, TableFormat, table_to_html

        table = DocumentTable(
            cells=parsed,
            format=TableFormat(header=bool(header), border=True),
            table_id="md1",
        )
        return table_to_html(table), i - start
    except Exception:
        bits = ['<table border="1">']
        for ri, cells in enumerate(parsed):
            bits.append("<tr>")
            tag = "th" if ri == 0 and header else "td"
            for c in cells:
                bits.append(f"<{tag}>{html_mod.escape(c)}</{tag}>")
            bits.append("</tr>")
        bits.append("</table>")
        return "".join(bits), i - start


def _split_pipe_row(raw: str) -> list[str]:
    s = raw.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.replace("\\|", "|").strip() for c in re.split(r"(?<!\\)\|", s)]


class _HtmlToMd(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self._stack: list[str] = []
        self._li_buf: list[str] = []
        self._ol_index: list[int] = []
        self._skip = False
        self._table_rows: list[list[str]] = []
        self._table_row: list[str] = []
        self._cell: list[str] = []
        self._in_pre = False
        self._pre: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        t = tag.lower()
        self._stack.append(t)
        if t in ("style", "script"):
            self._skip = True
        elif t in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.out.append("\n" + "#" * int(t[1]) + " ")
        elif t == "p":
            self.out.append("\n\n")
        elif t == "br":
            self.out.append("\n")
        elif t == "hr":
            self.out.append("\n\n---\n\n")
        elif t == "blockquote":
            self.out.append("\n\n> ")
        elif t == "pre":
            self._in_pre = True
            self._pre = []
        elif t == "code" and not self._in_pre:
            self.out.append("`")
        elif t in ("strong", "b"):
            self.out.append("**")
        elif t in ("em", "i"):
            self.out.append("*")
        elif t == "a":
            href = ""
            for k, v in attrs:
                if k.lower() == "href":
                    href = v or ""
            self._stack[-1] = f"a:{href}"
            self.out.append("[")
        elif t == "ul":
            self.out.append("\n")
        elif t == "ol":
            self._ol_index.append(1)
            self.out.append("\n")
        elif t == "li":
            if "ol" in self._stack:
                n = self._ol_index[-1] if self._ol_index else 1
                if self._ol_index:
                    self._ol_index[-1] = n + 1
                self.out.append(f"{n}. ")
            else:
                self.out.append("- ")
        elif t == "table":
            self._table_rows = []
        elif t == "tr":
            self._table_row = []
        elif t in ("td", "th"):
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in ("style", "script"):
            self._skip = False
        elif t in ("h1", "h2", "h3", "h4", "h5", "h6", "p"):
            self.out.append("\n")
        elif t == "pre":
            self._in_pre = False
            self.out.append("\n```\n" + "".join(self._pre).rstrip("\n") + "\n```\n")
            self._pre = []
        elif t == "code" and not self._in_pre:
            self.out.append("`")
        elif t in ("strong", "b"):
            self.out.append("**")
        elif t in ("em", "i"):
            self.out.append("*")
        elif t == "a" or (self._stack and str(self._stack[-1]).startswith("a:")):
            href = ""
            for item in reversed(self._stack):
                if str(item).startswith("a:"):
                    href = str(item)[2:]
                    break
            self.out.append(f"]({href})")
        elif t == "li":
            self.out.append("\n")
        elif t == "ol":
            if self._ol_index:
                self._ol_index.pop()
        elif t in ("td", "th"):
            self._table_row.append("".join(self._cell).replace("|", "\\|").strip())
            self._cell = []
        elif t == "tr":
            if self._table_row:
                self._table_rows.append(self._table_row)
            self._table_row = []
        elif t == "table":
            self.out.append(_rows_to_pipe_md(self._table_rows))
            self._table_rows = []
        while self._stack:
            top = self._stack.pop()
            if top == t or str(top).startswith(f"{t}:") or (
                t == "a" and str(top).startswith("a:")
            ):
                break

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        text = strip_pilcrow(data)
        if not text:
            return
        if self._in_pre:
            self._pre.append(text)
            return
        if self._cell is not None and self._stack and self._stack[-1] in ("td", "th"):
            self._cell.append(text)
            return
        self.out.append(text)


def _rows_to_pipe_md(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    cols = max(len(r) for r in rows)
    norm = [r + [""] * (cols - len(r)) for r in rows]
    lines = ["", "| " + " | ".join(norm[0]) + " |", "| " + " | ".join(["---"] * cols) + " |"]
    for row in norm[1:]:
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    return "\n".join(lines)


def html_to_markdown(html: str) -> str:
    """HTML (Editor/Qt) → Markdown ohne ¶."""
    src = strip_pilcrow(html or "")
    if not src.strip():
        return ""
    # Qt-Markdown nur mit laufender QApplication (sonst segfault offscreen)
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QTextDocument

        if QApplication.instance() is not None:
            doc = QTextDocument()
            doc.setHtml(src)
            md = doc.toMarkdown()
            if md and md.strip():
                return strip_pilcrow(md).strip() + "\n"
    except Exception:
        pass
    parser = _HtmlToMd()
    try:
        parser.feed(src)
        parser.close()
    except Exception:
        return strip_pilcrow(re.sub(r"<[^>]+>", "", src))
    text = "".join(parser.out)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return strip_pilcrow(text).strip() + "\n"


def qtextdocument_to_markdown(document) -> str:
    """``QTextDocument.toMarkdown`` ohne Absatzmarken."""
    if document is None:
        return ""
    try:
        md = document.toMarkdown()
    except Exception:
        try:
            md = html_to_markdown(document.toHtml())
        except Exception:
            md = str(document.toPlainText() or "")
    return strip_pilcrow(md or "")
