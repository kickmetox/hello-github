"""OCR → Word-Suite Handoff — 2.6.15 / Rich-QTextDocument 2.6.54.

Nimmt Tesseract-/Layout-OCR-Ergebnisse und ``*.ildocr.*``-Sidecars und
überführt sie in ein editierbares Word-Suite-Dokument: Absätze in
Lesereihenfolge, HTML für ``QTextDocument`` (gleiche Dokumentart wie ein
getipptes oder geöffnetes DOCX). Die Scan-/PDF-Quelle bleibt als Sidecar
oder Kommentar verknüpft; das Arbeitsdokument ist editierbarer Text.
"""

from __future__ import annotations

import html as html_lib
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence, Union

from instantlensdoc.core.ocr import (
    OcrLayoutBlock,
    OcrLayoutPage,
    OcrOutputMode,
    OcrResult,
    format_layout_text,
    ocr_image_layout,
    run_ocr,
)


PathLike = Union[str, Path]

DEFAULT_BODY_FONT = "Calibri"
DEFAULT_BODY_PT = 11.0
DEFAULT_HEADING_PT = 16.0
# Kein page-break-before: Qt speichert das als Form-Feed (\x0c) → Ersatzkasten.
PAGE_BREAK_HTML = (
    '<p style="margin-top:22pt;margin-bottom:0pt;-qt-paragraph-type:empty;">'
    "<br/></p>"
)
# Sichtbares Listenzeichen für QPlainTextEdit (kein ¶ / Form-Feed).
LIST_UL_PREFIX = "\u2022 "
_OCR_UL_RE = re.compile(
    r"^(?:[\x0c\u00b6\u00b7\u2022\u2023\u2043\u2219\u25aa\u25ab\u25cf\u25e6"
    r"\u25a0\u25a1●○▪▫–—]|[-*+])\s+"
)
_OCR_OL_RE = re.compile(r"^(\d{1,3})[.)]\s+")
_PAGE_MARK_RE = re.compile(r"^---\s*Seite\s+\d+\b[^\n]*---\s*$")
_ILD_HF_COMMENT_RE = re.compile(
    r"<!--\s*ild-(header|footer)\s+(.*?)\s*-->", re.I | re.S
)
_BUILTIN_FIELD_TOKENS = frozenset({"date", "time", "page", "n", "total"})
_FIELD_TOKEN_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
_FIELD_TOKEN_DBL_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")
_FIELD_TOKEN_PAD_RE = re.compile(r"\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}")
_FIELD_TOKEN_GUILLEMET_RE = re.compile(r"«\s*([A-Za-z_][A-Za-z0-9_]*)\s*»")
_FIELD_SPAN_ATTR_RE = re.compile(
    r"data-ild-field\s*=\s*['\"]([^'\"]+)['\"]", re.I
)

# Steuer-/Bidi-/Formatsteuerzeichen, die in QTextDocument als ¶ · Kästchen landen.
_OCR_CONTROL_RE = re.compile(
    "["
    "\x00-\x08\x0b\x0c\x0e-\x1f\x7f"
    "\u200b-\u200f"
    "\u2028-\u202e"
    "\u2060-\u2064"
    "\u2066-\u2069"
    "\ufeff"
    "\ufff9-\ufffb"
    "\ufffd"
    "]"
)
_HOCR_TITLE_ATTR_RE = re.compile(r"\btitle=(['\"])(.*?)\1", re.I | re.S)
_HOCR_BBOX_RE = re.compile(r"bbox\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)")
_HOCR_XFONT_RE = re.compile(r"x_font\s+([^;]+)")
_HOCR_XFSIZE_RE = re.compile(r"x_fsize\s+([\d.]+)")
_HOCR_PAR_OPEN_RE = re.compile(
    r"<(?:p|div)\b[^>]*class=['\"][^'\"]*\bocr_par\b[^'\"]*['\"][^>]*>",
    re.I,
)
_HOCR_WORD_RE = re.compile(
    r"<span\b([^>]*ocrx_word[^>]*)>(.*?)</span>",
    re.I | re.S,
)
_HOCR_PAGE_OPEN_RE = re.compile(
    r"<(?:div|body)\b[^>]*class=['\"][^'\"]*\bocr_page\b[^'\"]*['\"][^>]*>",
    re.I,
)

_BLOCK_META_RE = re.compile(
    r"^#\s*block#(?P<order>\d+)\s+id=(?P<id>\d+)\s+"
    r"bbox=(?P<l>-?\d+),(?P<t>-?\d+),(?P<w>-?\d+),(?P<h>-?\d+)\s+"
    r"conf=(?P<conf>-?[\d.]+)\s+lines=(?P<lines>\d+)\s*$"
)
_HEADER_KV_RE = re.compile(r"^#\s*([A-Za-z0-9_]+)=(.*)\s*$")


@dataclass
class WordSuiteBlock:
    """Ein Absatz/Block im Word-Suite-Dokument (Lesereihenfolge)."""

    reading_order: int
    text: str
    block_num: int = 0
    left: int = 0
    top: int = 0
    width: int = 0
    height: int = 0
    conf: float = -1.0
    lines: List[str] = field(default_factory=list)
    font_name: str = ""
    font_size_pt: float = 0.0
    bold: bool = False
    italic: bool = False
    page: int = 0
    is_heading: bool = False
    align: str = ""
    list_kind: str = ""  # "" | "ul" | "ol"
    table_cells: List[List[str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WordSuiteDocument:
    """Editierbares Word-Suite-Dokument aus OCR/Sidecar."""

    title: str
    text: str
    blocks: List[WordSuiteBlock] = field(default_factory=list)
    source: str = ""
    lang: str = "deu+eng"
    mode: str = "editable_text"
    sidecar: Optional[str] = None
    auto_formatted: bool = False
    meta: dict[str, Any] = field(default_factory=dict)
    html: str = ""
    source_path: Optional[str] = None
    source_page: Optional[int] = None
    source_comment: str = ""

    @property
    def block_count(self) -> int:
        return len(self.blocks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "text": self.text,
            "html": self.html,
            "blocks": [b.to_dict() for b in self.blocks],
            "block_count": self.block_count,
            "source": self.source,
            "source_path": self.source_path,
            "source_page": self.source_page,
            "source_comment": self.source_comment,
            "lang": self.lang,
            "mode": self.mode,
            "sidecar": self.sidecar,
            "auto_formatted": self.auto_formatted,
            "meta": dict(self.meta),
        }


def strip_ildocr_header(raw: str) -> tuple[dict[str, Any], str, List[WordSuiteBlock]]:
    """
    Sidecar-Header (``# …``) und Body trennen.

    Rückgabe: (meta, body_text, blocks_from_header).
    Leerzeilen im Header-Bereich bleiben Header (kein Body-Start).
    """
    meta: dict[str, Any] = {}
    blocks: List[WordSuiteBlock] = []
    body_lines: List[str] = []
    in_header = True
    for line in (raw or "").splitlines():
        stripped = line.strip()
        if in_header:
            if not stripped:
                # Leerzeile im Header — weiter im Header bleiben
                continue
            if stripped.startswith("#"):
                m = _BLOCK_META_RE.match(stripped)
                if m:
                    blocks.append(
                        WordSuiteBlock(
                            reading_order=int(m.group("order")),
                            block_num=int(m.group("id")),
                            left=int(m.group("l")),
                            top=int(m.group("t")),
                            width=int(m.group("w")),
                            height=int(m.group("h")),
                            conf=float(m.group("conf")),
                            text="",
                            lines=[],
                        )
                    )
                    continue
                kv = _HEADER_KV_RE.match(stripped)
                if kv:
                    key = kv.group(1).strip().lower()
                    val = kv.group(2).strip()
                    meta[key] = val
                    continue
                # andere Kommentarzeilen (Titel, Trenner) ignorieren
                continue
            # erste Nicht-Kommentar-Zeile = Body-Start
            in_header = False
        body_lines.append(line)
    body = "\n".join(body_lines).strip()
    # Wenn Header-Blöcke ohne Text: Body-Absätze zuordnen
    if blocks and body:
        paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
        for i, b in enumerate(blocks):
            if i < len(paras):
                b.text = paras[i]
                b.lines = paras[i].splitlines()
    return meta, body, blocks


def blocks_to_word_suite_text(
    blocks: Sequence[Union[OcrLayoutBlock, WordSuiteBlock, dict[str, Any]]],
    *,
    block_gap: str = "\n\n",
) -> str:
    """Blöcke in Lesereihenfolge als Absätze (editierbar)."""
    ordered: List[tuple[int, str]] = []
    for i, b in enumerate(blocks):
        if isinstance(b, dict):
            order = int(b.get("reading_order", i))
            text = str(b.get("text") or "").strip()
            cells = b.get("table_cells") or []
        else:
            order = int(getattr(b, "reading_order", i))
            text = str(getattr(b, "text", "") or "").strip()
            cells = getattr(b, "table_cells", None) or []
        if not text and cells:
            text = _table_plain(cells)
        if text:
            ordered.append((order, text))
    ordered.sort(key=lambda t: t[0])
    return block_gap.join(t for _, t in ordered).strip()


def _ws_blocks_from_ocr(
    blocks: Sequence[OcrLayoutBlock] | None,
) -> List[WordSuiteBlock]:
    out: List[WordSuiteBlock] = []
    if not blocks:
        return out
    for b in blocks:
        out.append(
            WordSuiteBlock(
                reading_order=int(b.reading_order),
                text=sanitize_ocr_visible_text((b.text or "").strip()),
                block_num=int(b.block_num),
                left=int(b.left),
                top=int(b.top),
                width=int(b.width),
                height=int(b.height),
                conf=float(b.conf),
                lines=list(b.lines or []),
                font_name=str(getattr(b, "font_name", "") or ""),
                font_size_pt=float(getattr(b, "font_size_pt", 0.0) or 0.0),
                bold=bool(getattr(b, "bold", False)),
                italic=bool(getattr(b, "italic", False)),
                page=int(getattr(b, "page", 0) or 0),
                is_heading=bool(getattr(b, "is_heading", False)),
                align=str(getattr(b, "align", "") or ""),
                list_kind=str(getattr(b, "list_kind", "") or ""),
                table_cells=[
                    [str(c) for c in row]
                    for row in (getattr(b, "table_cells", None) or [])
                ],
            )
        )
    out.sort(key=lambda x: (x.reading_order, x.top, x.left))
    for i, b in enumerate(out):
        b.reading_order = i
    return out


def _paragraphs_as_blocks(text: str) -> List[WordSuiteBlock]:
    return _blocks_from_text(text)


def _blocks_from_text(text: str) -> List[WordSuiteBlock]:
    """Absätze aus Text; ``--- Seite N ---``-Header werden Seitenumbrüche."""
    raw = text or ""
    chunks = re.split(r"(?m)^--- Seite\s+(\d+)[^\n]*---\s*$", raw)
    if len(chunks) > 1:
        blocks: List[WordSuiteBlock] = []
        order = 0
        pre = chunks[0].strip()
        if pre:
            for para in _split_paras(pre):
                blocks.append(
                    WordSuiteBlock(
                        reading_order=order,
                        text=para,
                        lines=para.splitlines(),
                    )
                )
                order += 1
        for j in range(1, len(chunks), 2):
            try:
                page_no = int(chunks[j])
            except (TypeError, ValueError):
                page_no = 0
            body = chunks[j + 1] if j + 1 < len(chunks) else ""
            paras = _split_paras(body)
            if not paras and page_no:
                # leere Seite: trotzdem Umbruch halten
                continue
            for para in paras:
                blocks.append(
                    WordSuiteBlock(
                        reading_order=order,
                        text=para,
                        page=page_no,
                        lines=para.splitlines(),
                    )
                )
                order += 1
        return blocks
    paras = _split_paras(raw)
    return [
        WordSuiteBlock(
            reading_order=i,
            text=p,
            lines=p.splitlines(),
        )
        for i, p in enumerate(paras)
    ]


def _split_paras(text: str) -> List[str]:
    cleaned = sanitize_ocr_visible_text(text or "")
    paras = [p.strip() for p in re.split(r"\n\s*\n", cleaned) if p.strip()]
    if not paras and cleaned.strip():
        paras = [cleaned.strip()]
    return paras


def _maybe_auto_format(text: str, *, enabled: bool) -> tuple[str, bool]:
    if not enabled or not (text or "").strip():
        return text or "", False
    try:
        from ild_pdf.auto_format import auto_format_text

        result = auto_format_text(text)
        if isinstance(result, dict):
            out = str(result.get("text") or result.get("formatted") or text)
        else:
            out = str(getattr(result, "text", None) or result)
        return out, out != text
    except Exception:
        return text, False


def sanitize_ocr_visible_text(text: str) -> str:
    """Form-Feed, Bidi-Marken, Ersatzzeichen aus OCR/PDF-Text entfernen — kein ¶/Kasten."""
    if not text:
        return ""
    lines = str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cleaned_lines: List[str] = []
    for line in lines:
        stripped = line.lstrip(" \t")
        # Pipe/TSV-Zeilen: Steuerzeichen sind Zellenmüll, kein Absatz-/Seitenumbruch.
        if stripped.startswith("|") or stripped.count("|") >= 2 or "\t" in line:
            line = (
                line.replace("\x0c", " ")
                .replace("\u00b6", " ")
                .replace("\u2028", " ")
                .replace("\u2029", " ")
            )
        cleaned_lines.append(line)
    s = "\n".join(cleaned_lines)
    s = (
        s.replace("\x0c", "\n\n")
        .replace("\u00b6", "\n\n")  # Pilcrow = Absatzende, kein Listenzeichen
        .replace("\u2028", "\n")
        .replace("\u2029", "\n\n")
    )
    s = _OCR_CONTROL_RE.sub("", s)
    return normalize_field_tokens(s)


def canonical_field_name(name: str) -> str:
    ident = re.sub(r"[^A-Za-z0-9_]", "", str(name or "").strip())
    if not ident:
        return ""
    if ident.lower() in _BUILTIN_FIELD_TOKENS:
        return ident.lower()
    return ident


def canonical_field_token(name: str) -> str:
    ident = canonical_field_name(name)
    return f"{{{ident}}}" if ident else ""


def safe_field_display(name: str, ersatz: str | None = None) -> str:
    """Sichtbares Feld-Token — nie ¶ / Form-Feed / Replacement-Kasten."""
    token = canonical_field_token(name)
    if not token:
        return ""
    if ersatz is None:
        return token
    cleaned = (
        str(ersatz)
        .replace("\x0c", "")
        .replace("\u00b6", "")
        .replace("\ufffd", "")
        .replace("\u2028", "")
        .replace("\u2029", "")
    )
    cleaned = _OCR_CONTROL_RE.sub("", cleaned).strip()
    if not cleaned:
        return token
    return cleaned


def normalize_field_tokens(text: str) -> str:
    """``{{date}}`` / ``{ DATE }`` / ``«page»`` → ``{date}`` / ``{page}``; Custom bleibt."""
    if not text:
        return ""

    def _canon(raw: str) -> str:
        return canonical_field_token(raw) or ("{" + raw + "}" if raw else "")

    s = _FIELD_TOKEN_DBL_RE.sub(lambda m: _canon(m.group(1)), str(text))
    s = _FIELD_TOKEN_GUILLEMET_RE.sub(lambda m: _canon(m.group(1)), s)
    s = _FIELD_TOKEN_PAD_RE.sub(lambda m: _canon(m.group(1)), s)
    return s


def field_token_html_span(name: str, display: str | None = None) -> str:
    ident = canonical_field_name(name)
    if not ident:
        return html_lib.escape(display or "", quote=False)
    vis = html_lib.escape(safe_field_display(ident, display), quote=False)
    return f'<span data-ild-field="{html_lib.escape(ident, quote=True)}">{vis}</span>'


def wrap_field_tokens_in_html(inner: str) -> str:
    """Bereits geescapten Fließtext: ``{date}`` als Span, kein Steuerzeichen."""
    if not inner or "{" not in inner:
        return inner or ""

    def _wrap(m: re.Match[str]) -> str:
        return field_token_html_span(m.group(1))

    return _FIELD_TOKEN_RE.sub(_wrap, inner)


def extract_field_tokens(text_or_html: str) -> dict[str, str]:
    """Feldnamen aus Fließtext/HTML (data-ild-field + ``{name}``)."""
    blob = text_or_html or ""
    out: dict[str, str] = {}
    for m in _FIELD_SPAN_ATTR_RE.finditer(blob):
        ident = canonical_field_name(m.group(1))
        if ident:
            out[ident] = canonical_field_token(ident)
    for m in _FIELD_TOKEN_RE.finditer(blob):
        ident = canonical_field_name(m.group(1))
        if ident:
            out.setdefault(ident, canonical_field_token(ident))
    return out


def sanitize_ocr_html(html: str) -> str:
    """Steuerzeichen aus generiertem Word-Suite-HTML strippen (Tags/Kommentare bleiben)."""
    if not html:
        return ""
    s = (
        str(html)
        .replace("\x0c", "")
        .replace("\u00b6", "")
        .replace("\u2028", " ")
        .replace("\u2029", " ")
    )
    return _OCR_CONTROL_RE.sub("", s)


def extract_ild_header_footer(html: str) -> tuple[str, str]:
    """``<!-- ild-header/footer … -->`` aus HTML — nicht Teil des Fließtexts."""
    header = ""
    footer = ""
    for m in _ILD_HF_COMMENT_RE.finditer(html or ""):
        kind = (m.group(1) or "").lower()
        text = sanitize_ocr_visible_text(html_lib.unescape(m.group(2) or "")).strip()
        if not text:
            continue
        if kind == "header":
            header = text
        elif kind == "footer":
            footer = text
    return header, footer


def header_footer_html_comments(header: str = "", footer: str = "") -> str:
    """Kopf-/Fußzeile als HTML-Kommentar (kein ¶/Form-Feed im Body)."""
    parts: List[str] = []
    h = sanitize_ocr_visible_text(header or "").strip()
    f = sanitize_ocr_visible_text(footer or "").strip()
    if h:
        parts.append(f"<!-- ild-header {html_lib.escape(h, quote=True)} -->")
    if f:
        parts.append(f"<!-- ild-footer {html_lib.escape(f, quote=True)} -->")
    return "".join(parts)


def _norm_hf_line(text: str) -> str:
    t = sanitize_ocr_visible_text(text or "")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _is_plausible_running_hf(text: str) -> bool:
    t = _norm_hf_line(text)
    if not t or len(t) > 80:
        return False
    if _PAGE_MARK_RE.match(t):
        return False
    if t.count(" ") > 12:
        return False
    return True


def lift_running_header_footer(
    blocks: Sequence[WordSuiteBlock] | None,
) -> tuple[List[WordSuiteBlock], str, str]:
    """Wiederholte erste/letzte Zeile je Seite → Kopf/Fuß, nicht Body."""
    items = list(blocks or [])
    pages: dict[int, List[WordSuiteBlock]] = {}
    for b in items:
        pages.setdefault(int(b.page or 0), []).append(b)
    numbered = [p for p in pages if p > 0]
    if len(numbered) < 2:
        return items, "", ""
    from collections import Counter

    def _lines_of(b: WordSuiteBlock) -> List[str]:
        if getattr(b, "table_cells", None):
            return []
        raw = list(b.lines or []) or (b.text or "").splitlines() or [b.text or ""]
        return [_norm_hf_line(x) for x in raw if _norm_hf_line(x)]

    firsts: List[str] = []
    lasts: List[str] = []
    for p in sorted(numbered):
        page_lines: List[str] = []
        for b in pages[p]:
            page_lines.extend(_lines_of(b))
        if not page_lines:
            continue
        firsts.append(page_lines[0])
        lasts.append(page_lines[-1])

    def _majority(values: List[str]) -> str:
        plausible = [v for v in values if _is_plausible_running_hf(v)]
        if len(plausible) < 2:
            return ""
        line, n = Counter(plausible).most_common(1)[0]
        if n >= 2 and n * 2 >= len(values):
            return line
        return ""

    header = _majority(firsts)
    footer = _majority(lasts)
    if header and header == footer:
        footer = ""
    if not header and not footer:
        return items, "", ""

    out: List[WordSuiteBlock] = []
    order = 0
    for b in items:
        if getattr(b, "table_cells", None):
            b.reading_order = order
            out.append(b)
            order += 1
            continue
        lines = _lines_of(b)
        if not lines:
            continue
        if header and lines and lines[0] == header:
            lines = lines[1:]
        if footer and lines and lines[-1] == footer:
            lines = lines[:-1]
        text = "\n".join(lines).strip()
        if not text:
            continue
        b.text = text
        b.lines = text.splitlines() or [text]
        b.reading_order = order
        out.append(b)
        order += 1
    return out, header, footer


def _html_escape(text: str) -> str:
    return html_lib.escape(sanitize_ocr_visible_text(text), quote=False).replace(
        "\n", "<br/>"
    )


def classify_ocr_list_line(line: str) -> tuple[str, str]:
    """OCR-Zeile → (list_kind, Text ohne Marker). ``¶``/``\\x0c`` zählen als ul, nicht als Glyph."""
    s = (line or "").strip(" \t\r\n")
    if not s:
        return "", ""
    s = re.sub(r"^[\x0c\u00b6]+", LIST_UL_PREFIX, s).strip(" \t\r\n")
    if s in ("\u2022", LIST_UL_PREFIX.strip()):
        return "", ""
    ol = _OCR_OL_RE.match(s)
    if ol:
        rest = s[ol.end() :].strip()
        if rest:
            return "ol", rest
    ul = _OCR_UL_RE.match(s)
    if ul:
        rest = s[ul.end() :].strip()
        if rest:
            return "ul", rest
    return "", s


def _table_plain(cells: Sequence[Sequence[str]]) -> str:
    """Tabellen-Fließtext ohne Markdown-Separator / Steuerzeichen."""
    rows: List[str] = []
    for row in cells or []:
        parts = [sanitize_ocr_visible_text(str(c or "")).strip() for c in row]
        if any(parts):
            rows.append(" | ".join(parts))
    return "\n".join(rows)


def _sanitize_table_cells(cells: Sequence[Sequence[Any]] | None) -> List[List[str]]:
    out: List[List[str]] = []
    for row in cells or []:
        cleaned = [sanitize_ocr_visible_text(str(c or "")).strip() for c in row]
        if any(cleaned):
            out.append(cleaned)
    if not out:
        return []
    ncols = max(len(r) for r in out)
    if ncols < 2:
        return []
    return [r + [""] * (ncols - len(r)) for r in out]


def _is_ocr_table_sep(line: str) -> bool:
    s = (line or "").strip().strip("|").strip()
    if not s:
        return False
    parts = [p.strip() for p in s.split("|")]
    return bool(parts) and all(
        re.fullmatch(r":?-+:?", (p or "").replace(" ", "") or "-") for p in parts
    )


def _plausible_table_cells(cells: Sequence[str]) -> bool:
    nonempty = [c for c in cells if str(c or "").strip()]
    if len(nonempty) < 2:
        return False
    if len(cells) >= 3:
        return True
    return not any(len(str(c or "")) > 48 for c in cells)


def split_ocr_table_row(line: str) -> List[str] | None:
    """Pipe-/TSV-/Spalten-Zeile → Zellen; Separatorzeilen und Steuerzeichen raus."""
    s = (line or "").strip(" \t\r\n")
    if not s or _is_ocr_table_sep(s):
        return None
    if s.startswith("|") or s.count("|") >= 2:
        inner = s.strip("|")
        cells = [
            sanitize_ocr_visible_text(c.replace("\\|", "|")).strip()
            for c in re.split(r"(?<!\\)\|", inner)
        ]
        if len(cells) >= 2 and any(cells):
            return cells
    if "\t" in s:
        cells = [sanitize_ocr_visible_text(c).strip() for c in s.split("\t")]
        if _plausible_table_cells(cells):
            return cells
    if re.search(r"\S\s{2,}\S", s):
        cells = [
            sanitize_ocr_visible_text(c).strip()
            for c in re.split(r"\s{2,}", s)
            if sanitize_ocr_visible_text(c).strip()
        ]
        if _plausible_table_cells(cells):
            return cells
    return None


def ocr_table_html(cells: Sequence[Sequence[str]], *, table_id: str = "ocr1") -> str:
    """OCR-Tabelle als HTML für QTextDocument — keine ¶/Form-Feed/Pipe-Dump."""
    cleaned = _sanitize_table_cells(cells)
    if not cleaned:
        return ""
    try:
        from ild_pdf.tables import DocumentTable, TableFormat, table_to_html

        table = DocumentTable(
            cells=cleaned,
            format=TableFormat(header=True, border=True, style="default"),
            table_id=table_id or "ocr1",
        )
        return sanitize_ocr_html(table_to_html(table))
    except Exception:
        bits = ['<table border="1" cellpadding="4" cellspacing="0">']
        for i, row in enumerate(cleaned):
            bits.append("<tr>")
            tag = "th" if i == 0 else "td"
            for c in row:
                bits.append(f"<{tag}>{_html_escape(c)}</{tag}>")
            bits.append("</tr>")
        bits.append("</table>")
        return sanitize_ocr_html("".join(bits))


def _clone_ws_block(
    src: WordSuiteBlock,
    text: str,
    list_kind: str,
    order: int,
    *,
    table_cells: Sequence[Sequence[str]] | None = None,
) -> WordSuiteBlock:
    cells = _sanitize_table_cells(table_cells)
    body = text if not cells else _table_plain(cells)
    return WordSuiteBlock(
        reading_order=order,
        text=body,
        block_num=int(src.block_num or 0),
        left=int(src.left or 0),
        top=int(src.top or 0),
        width=int(src.width or 0),
        height=int(src.height or 0),
        conf=float(src.conf if src.conf is not None else -1.0),
        lines=body.splitlines() or ([body] if body else []),
        font_name=src.font_name,
        font_size_pt=float(src.font_size_pt or 0.0),
        bold=bool(src.bold) and not cells,
        italic=bool(src.italic) and not cells,
        page=int(src.page or 0),
        is_heading=bool(src.is_heading) and not list_kind and not cells,
        align=src.align or "",
        list_kind="" if cells else list_kind,
        table_cells=cells,
    )


def expand_blocks_with_tables(blocks: Sequence[WordSuiteBlock] | None) -> List[WordSuiteBlock]:
    """Pipe-/TSV-/Spaltenzeilen → Tabellenblöcke (HTML), nicht als ¶/Form-Feed-Liste."""
    out: List[WordSuiteBlock] = []
    order = 0
    pending: List[tuple[WordSuiteBlock, List[str]]] = []

    def _flush_pending() -> None:
        nonlocal order
        if not pending:
            return
        if len(pending) < 2:
            src, cells = pending[0]
            text = " | ".join(cells) if cells else (src.text or "")
            kind, rest = classify_ocr_list_line(text)
            out.append(
                _clone_ws_block(src, rest or text, kind or src.list_kind or "", order)
            )
            order += 1
            pending.clear()
            return
        src0 = pending[0][0]
        cells = _sanitize_table_cells([row for _s, row in pending])
        if cells:
            out.append(_clone_ws_block(src0, _table_plain(cells), "", order, table_cells=cells))
            order += 1
        else:
            for src, row in pending:
                out.append(_clone_ws_block(src, " | ".join(row), "", order))
                order += 1
        pending.clear()

    for src in blocks or []:
        existing = _sanitize_table_cells(getattr(src, "table_cells", None))
        if existing:
            _flush_pending()
            out.append(_clone_ws_block(src, _table_plain(existing), "", order, table_cells=existing))
            order += 1
            continue
        raw_lines = list(src.lines or [])
        blob = src.text or ""
        if not raw_lines:
            raw_lines = blob.splitlines() or ([blob] if blob.strip() else [])
        emitted_line = False
        for ln in raw_lines:
            if _is_ocr_table_sep(ln):
                continue
            cells = split_ocr_table_row(ln)
            kind, rest = classify_ocr_list_line(ln)
            if kind and (not cells or len(cells) < 3):
                cells = None
            if cells:
                pending.append((src, cells))
                emitted_line = True
                continue
            _flush_pending()
            body = rest if kind else sanitize_ocr_visible_text(ln or "").strip()
            if not body:
                continue
            out.append(_clone_ws_block(src, body, kind or src.list_kind or "", order))
            order += 1
            emitted_line = True
        if not emitted_line and blob.strip() and not pending:
            kind, rest = classify_ocr_list_line(blob)
            if rest:
                out.append(
                    _clone_ws_block(src, rest, kind or src.list_kind or "", order)
                )
                order += 1
    _flush_pending()
    return out


def expand_blocks_with_lists(blocks: Sequence[WordSuiteBlock] | None) -> List[WordSuiteBlock]:
    """Mehrzeilige Blöcke mit Aufzählung/Nummerierung in eigene Absätze splitten."""
    out: List[WordSuiteBlock] = []
    order = 0
    for src in blocks or []:
        if getattr(src, "table_cells", None):
            cells = _sanitize_table_cells(src.table_cells)
            out.append(
                _clone_ws_block(src, src.text or _table_plain(cells), "", order, table_cells=cells)
            )
            order += 1
            continue
        raw_lines = list(src.lines or [])
        blob = src.text or ""
        if not raw_lines:
            raw_lines = blob.splitlines() or ([blob] if blob.strip() else [])
        classified: List[tuple[str, str]] = []
        for ln in raw_lines:
            kind, text = classify_ocr_list_line(ln)
            if text:
                classified.append((kind, text))
        if not classified and blob.strip():
            kind, text = classify_ocr_list_line(blob)
            if text:
                classified.append((kind, text))
        if not classified:
            continue
        any_list = any(k for k, _t in classified)
        if not any_list and len(classified) == 1:
            out.append(
                _clone_ws_block(
                    src, classified[0][1], src.list_kind or classified[0][0], order
                )
            )
            order += 1
            continue
        if not any_list:
            joined = "\n".join(t for _k, t in classified)
            out.append(_clone_ws_block(src, joined, src.list_kind or "", order))
            order += 1
            continue
        for kind, text in classified:
            out.append(_clone_ws_block(src, text, kind or (src.list_kind or ""), order))
            order += 1
    return out


def infer_align(left: float, width: float, page_width: float) -> str:
    """Aus Block-BBox vs. Seitenbreite: left/center/right."""
    if page_width <= 0 or width <= 0:
        return "left"
    left_gap = max(0.0, float(left))
    right_gap = max(0.0, float(page_width) - (float(left) + float(width)))
    if abs(left_gap - right_gap) < page_width * 0.12 and left_gap > page_width * 0.10:
        return "center"
    if left_gap > page_width * 0.38 and right_gap < page_width * 0.20:
        return "right"
    return "left"


def _font_style_from_name(name: str) -> tuple[bool, bool, str]:
    """``(bold, italic, family)`` aus Tesseract/pdfium-Fontnamen."""
    raw = (name or "").replace("_", " ").replace("-", " ").strip()
    if not raw:
        return False, False, ""
    low = raw.lower()
    bold = any(t in low for t in ("bold", "black", "heavy", "semibold"))
    italic = any(t in low for t in ("italic", "oblique"))
    family = re.sub(
        r"(?i)\b(bold|italic|oblique|regular|medium|light|black|heavy|roman|mt)\b",
        " ",
        raw,
    )
    family = re.sub(r"\s+", " ", family).strip(" ,")
    return bold, italic, family or raw


def _normalize_font_size_pt(size: float) -> float:
    """hOCR ``x_fsize`` oft in Pixel; auf Punkt begrenzen."""
    try:
        val = float(size)
    except (TypeError, ValueError):
        return 0.0
    if val <= 0:
        return 0.0
    if val > 48.0:
        val = val * 0.75
    return max(7.0, min(48.0, round(val, 1)))


def _hocr_title_from_tag(tag: str) -> str:
    m = _HOCR_TITLE_ATTR_RE.search(tag or "")
    return m.group(2) if m else ""


def _parse_hocr_title(title: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    m = _HOCR_BBOX_RE.search(title or "")
    if m:
        l, t, r, b = (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))
        out["left"] = l
        out["top"] = t
        out["width"] = max(0, r - l)
        out["height"] = max(0, b - t)
    fm = _HOCR_XFONT_RE.search(title or "")
    if fm:
        out["font"] = fm.group(1).strip().strip("'\"")
    sm = _HOCR_XFSIZE_RE.search(title or "")
    if sm:
        try:
            out["size"] = float(sm.group(1))
        except ValueError:
            pass
    return out


def parse_hocr_to_blocks(hocr: str, *, page: int = 0) -> List[WordSuiteBlock]:
    """Tesseract-hOCR → Absätze mit Font/Größe/Fett/Kursiv/Ausrichtung."""
    html = hocr or ""
    if "ocr" not in html.lower():
        return []
    page_w = 0
    for pm in _HOCR_PAGE_OPEN_RE.finditer(html):
        info = _parse_hocr_title(_hocr_title_from_tag(pm.group(0)))
        page_w = max(page_w, int(info.get("width", 0) or 0) + int(info.get("left", 0) or 0))
    opens = list(_HOCR_PAR_OPEN_RE.finditer(html))
    blocks: List[WordSuiteBlock] = []
    for i, m in enumerate(opens):
        start = m.end()
        end = opens[i + 1].start() if i + 1 < len(opens) else len(html)
        chunk = html[start:end]
        chunk = re.split(
            r"(?i)<(?:div|p)\b[^>]*class=['\"][^'\"]*ocr_(?:carea|page|par)\b",
            chunk,
            maxsplit=1,
        )[0]
        par_info = _parse_hocr_title(_hocr_title_from_tag(m.group(0)))
        words: List[str] = []
        fonts: List[str] = []
        sizes: List[float] = []
        n_bold = 0
        n_italic = 0
        for wm in _HOCR_WORD_RE.finditer(chunk):
            attrs, inner = wm.group(1), wm.group(2)
            info = _parse_hocr_title(_hocr_title_from_tag(attrs))
            text = re.sub(r"<[^>]+>", "", inner)
            text = html_lib.unescape(text)
            text = sanitize_ocr_visible_text(text).strip()
            if not text:
                continue
            words.append(text)
            if info.get("font"):
                fonts.append(str(info["font"]))
            if info.get("size"):
                sizes.append(float(info["size"]))
            inner_l = inner.lower()
            attrs_l = (attrs or "").lower()
            fb, fi, _fam = _font_style_from_name(str(info.get("font") or ""))
            if fb or "<strong" in inner_l or "<b>" in inner_l or "ocr-bold" in attrs_l:
                n_bold += 1
            if fi or "<em" in inner_l or "<i>" in inner_l or "ocr-italic" in attrs_l:
                n_italic += 1
        if not words:
            plain = re.sub(r"<br\s*/?>", "\n", chunk, flags=re.I)
            plain = re.sub(r"<[^>]+>", " ", plain)
            plain = sanitize_ocr_visible_text(html_lib.unescape(plain))
            plain = re.sub(r"[ \t]+", " ", plain).strip()
            if not plain:
                continue
            words = [plain]
        body = sanitize_ocr_visible_text(" ".join(words))
        body = re.sub(r" +", " ", body).strip()
        if not body:
            continue
        font_name = fonts[0] if fonts else ""
        _fb, _fi, family = _font_style_from_name(font_name)
        if family:
            font_name = family
        n = max(1, len(words))
        left = int(par_info.get("left", 0) or 0)
        width = int(par_info.get("width", 0) or 0)
        blocks.append(
            WordSuiteBlock(
                reading_order=len(blocks),
                text=body,
                left=left,
                top=int(par_info.get("top", 0) or 0),
                width=width,
                height=int(par_info.get("height", 0) or 0),
                font_name=font_name,
                font_size_pt=_normalize_font_size_pt(_median_positive(sizes)),
                bold=n_bold * 2 >= n,
                italic=n_italic * 2 >= n,
                page=int(page or 0),
                align=infer_align(left, width, page_w),
                lines=body.splitlines(),
            )
        )
    return blocks


def looks_like_heading(
    text: str,
    *,
    font_size_pt: float = 0.0,
    median_size: float = 0.0,
    height: int = 0,
    lines: int = 1,
) -> bool:
    """Überschriften-Heuristik: kurz, ohne Satzende, GROSS oder größer als Median."""
    t = (text or "").strip()
    if not t or len(t) > 80:
        return False
    if t.endswith((".", "!", "?", "。", "…")):
        return False
    if t.startswith("#"):
        return True
    letters = [c for c in t if c.isalpha()]
    if letters:
        upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
        if upper_ratio >= 0.8 and len(t) <= 60:
            return True
    if font_size_pt and median_size and font_size_pt >= max(median_size * 1.25, median_size + 1.5):
        return True
    if height and lines == 1 and median_size <= 0 and height >= 28 and len(t) <= 60:
        return True
    return False


def _median_positive(values: Sequence[float]) -> float:
    nums = sorted(float(v) for v in values if v and v > 0)
    if not nums:
        return 0.0
    mid = len(nums) // 2
    if len(nums) % 2:
        return nums[mid]
    return (nums[mid - 1] + nums[mid]) / 2.0


def infer_block_styles(blocks: Sequence[WordSuiteBlock]) -> None:
    """Font/Überschrift/Ausrichtung an Blöcken setzen, wo Tesseract keine Fonts liefert."""
    sizes: List[float] = []
    page_w = 0.0
    for b in blocks:
        page_w = max(page_w, float(b.left or 0) + float(b.width or 0))
        if b.font_name:
            fb, fi, fam = _font_style_from_name(b.font_name)
            if fam:
                b.font_name = fam
            if fb:
                b.bold = True
            if fi:
                b.italic = True
        if b.font_size_pt and b.font_size_pt > 0:
            b.font_size_pt = _normalize_font_size_pt(b.font_size_pt)
            sizes.append(float(b.font_size_pt))
            continue
        n_lines = max(1, len(b.lines) if b.lines else (1 if b.text else 1))
        if b.height and n_lines:
            est = float(b.height) / float(n_lines) * 0.55
            if 7.0 <= est <= 36.0:
                b.font_size_pt = round(est, 1)
                sizes.append(b.font_size_pt)
    median = _median_positive(sizes) or DEFAULT_BODY_PT
    for b in blocks:
        if getattr(b, "table_cells", None):
            b.table_cells = _sanitize_table_cells(b.table_cells)
            b.text = _table_plain(b.table_cells)
            b.lines = b.text.splitlines() or [b.text]
            b.is_heading = False
            b.list_kind = ""
            if not (b.align or "").strip():
                b.align = "left"
            if not b.font_name:
                b.font_name = DEFAULT_BODY_FONT
            if not b.font_size_pt:
                b.font_size_pt = DEFAULT_BODY_PT
            continue
        b.text = sanitize_ocr_visible_text(b.text)
        if not b.font_name:
            b.font_name = DEFAULT_BODY_FONT
        n_lines = max(1, len(b.lines) if b.lines else 1)
        if not b.is_heading:
            b.is_heading = looks_like_heading(
                b.text,
                font_size_pt=float(b.font_size_pt or 0.0),
                median_size=median,
                height=int(b.height or 0),
                lines=n_lines,
            )
        if b.is_heading:
            b.bold = True
            if not b.font_size_pt or b.font_size_pt < DEFAULT_HEADING_PT:
                b.font_size_pt = DEFAULT_HEADING_PT
        elif not b.font_size_pt:
            b.font_size_pt = DEFAULT_BODY_PT
        if not (b.list_kind or "").strip():
            kind, rest = classify_ocr_list_line(b.text)
            if kind:
                b.list_kind = kind
                b.text = rest
                b.lines = rest.splitlines() or [rest]
                b.is_heading = False
        if b.list_kind:
            b.is_heading = False
            if not (b.align or "").strip():
                b.align = "left"
        if not (b.align or "").strip():
            b.align = infer_align(b.left, b.width, page_w)


def source_link_comment(
    *,
    source: str = "",
    source_path: str | Path | None = None,
    source_page: int | None = None,
    sidecar: str | Path | None = None,
) -> str:
    """Menschenlesbarer Quell-Kommentar (Scan/PDF-Seite), nicht Teil des Fließtexts."""
    parts: List[str] = []
    path = source_path or source
    if path:
        parts.append(f"Quelle: {path}")
    if source_page and int(source_page) > 0:
        parts.append(f"Seite {int(source_page)}")
    if sidecar:
        parts.append(f"Sidecar {Path(str(sidecar)).name}")
    if not parts:
        return ""
    return "OCR-Quelle — " + " · ".join(parts)


def blocks_to_word_suite_html(
    blocks: Sequence[WordSuiteBlock] | None,
    *,
    text: str = "",
    title: str = "",
    source_path: str | None = None,
    source_page: int | None = None,
    sidecar: str | None = None,
    font_family: str = DEFAULT_BODY_FONT,
    font_size_pt: float = DEFAULT_BODY_PT,
    header: str = "",
    footer: str = "",
) -> str:
    """Absätze + optionale Fonts/Seitenumbrüche als HTML für ``QTextDocument``."""
    items = list(blocks or [])
    if not items and (text or "").strip():
        items = _paragraphs_as_blocks(text)
        infer_block_styles(items)
    comment = source_link_comment(
        source_path=source_path,
        source_page=source_page,
        sidecar=sidecar,
    )
    head = (
        "<!DOCTYPE HTML><html><head><meta charset=\"utf-8\"/>"
        f"<title>{html_lib.escape(title or 'Word-Suite')}</title></head>"
        f'<body style="font-family:{html_lib.escape(font_family)};'
        f'font-size:{float(font_size_pt):g}pt;">'
    )
    if comment:
        head += f"<!-- ild-source {html_lib.escape(comment, quote=True)} -->"
    head += header_footer_html_comments(header, footer)
    parts: List[str] = [head]
    last_page: int | None = None
    wrote = False
    ol_index = 0
    for b in items:
        cells = _sanitize_table_cells(getattr(b, "table_cells", None))
        body = (b.text or "").strip()
        if not body and not cells:
            continue
        if _PAGE_MARK_RE.match(body):
            continue
        page = int(b.page or 0)
        if last_page is not None and page and page != last_page:
            parts.append(PAGE_BREAK_HTML)
            ol_index = 0
        if page:
            last_page = page
        if cells:
            parts.append(ocr_table_html(cells, table_id=f"ocr{int(b.reading_order)}"))
            wrote = True
            ol_index = 0
            continue
        fam = html_lib.escape(b.font_name or font_family)
        size = float(b.font_size_pt or font_size_pt or DEFAULT_BODY_PT)
        inner = wrap_field_tokens_in_html(_html_escape(body))
        kind = (b.list_kind or "").strip().lower()
        if kind == "ol":
            ol_index += 1
            inner = f"{ol_index}. {inner}"
        elif kind == "ul":
            ol_index = 0
            inner = LIST_UL_PREFIX + inner
        else:
            ol_index = 0
            if b.italic:
                inner = f"<i>{inner}</i>"
            if b.bold or b.is_heading:
                inner = f"<b>{inner}</b>"
        tag = "h1" if b.is_heading and kind not in ("ul", "ol") else "p"
        align = (b.align or "left").lower().strip()
        if align not in ("left", "center", "right", "justify"):
            align = "left"
        if kind in ("ul", "ol"):
            align = "left"
        margin_left = "24px" if kind in ("ul", "ol") else "0"
        margin_top = "0" if kind in ("ul", "ol") else ("6pt" if tag == "h1" else "0")
        margin_bottom = "4pt" if kind in ("ul", "ol") else ("10pt" if tag == "h1" else "8pt")
        parts.append(
            f'<{tag} align="{align}" style="font-family:{fam};font-size:{size:g}pt;'
            f'text-align:{align};margin-left:{margin_left};margin-top:{margin_top};'
            f'margin-bottom:{margin_bottom};line-height:115%;">{inner}</{tag}>'
        )
        wrote = True
    if not wrote and (text or "").strip():
        for para in _paragraphs_as_blocks(text):
            parts.append(
                f'<p align="left">{wrap_field_tokens_in_html(_html_escape(para.text))}</p>'
            )
    parts.append("</body></html>")
    return sanitize_ocr_html("".join(parts))


def _int_meta(meta: dict[str, Any], key: str) -> int | None:
    raw = meta.get(key)
    if raw is None or raw == "":
        return None
    try:
        val = int(float(str(raw).strip()))
    except (TypeError, ValueError):
        return None
    return val if val > 0 else None


def _finalize_word_suite_document(doc: WordSuiteDocument) -> WordSuiteDocument:
    """HTML, Überschriften und Quell-Link an ein Word-Suite-Dokument anhängen."""
    doc.blocks = expand_blocks_with_tables(doc.blocks)
    if not any(getattr(b, "table_cells", None) for b in doc.blocks):
        extra = _sanitize_table_cells(doc.meta.get("table_rows"))
        if extra:
            src = doc.blocks[-1] if doc.blocks else WordSuiteBlock(reading_order=0, text="")
            doc.blocks.append(
                _clone_ws_block(
                    src,
                    _table_plain(extra),
                    "",
                    len(doc.blocks),
                    table_cells=extra,
                )
            )
    doc.blocks = expand_blocks_with_lists(doc.blocks)
    infer_block_styles(doc.blocks)
    lifted_h, lifted_f = "", ""
    doc.blocks, lifted_h, lifted_f = lift_running_header_footer(doc.blocks)
    header = str(doc.meta.get("header") or lifted_h or "").strip()
    footer = str(doc.meta.get("footer") or lifted_f or "").strip()
    header = sanitize_ocr_visible_text(header).strip()
    footer = sanitize_ocr_visible_text(footer).strip()
    if header:
        doc.meta["header"] = header
    if footer:
        doc.meta["footer"] = footer
    if doc.blocks and not doc.auto_formatted:
        rebuilt = blocks_to_word_suite_text(doc.blocks)
        if rebuilt:
            doc.text = rebuilt
    if not doc.source_path:
        src = (doc.source or "").strip()
        if src and src not in ("OCR", "OCR-Text"):
            doc.source_path = src
    if doc.source_page is None:
        doc.source_page = _int_meta(doc.meta, "page")
    if not doc.source_comment:
        doc.source_comment = source_link_comment(
            source=doc.source,
            source_path=doc.source_path,
            source_page=doc.source_page,
            sidecar=doc.sidecar,
        )
    doc.meta.setdefault("rich_text", True)
    doc.meta.setdefault("font_family", DEFAULT_BODY_FONT)
    doc.meta.setdefault("font_size_pt", DEFAULT_BODY_PT)
    if doc.source_path:
        doc.meta["source_path"] = doc.source_path
    if doc.source_page:
        doc.meta["source_page"] = int(doc.source_page)
    if doc.sidecar:
        doc.meta["sidecar"] = doc.sidecar
    if doc.source_comment:
        doc.meta["source_comment"] = doc.source_comment
        comments = list(doc.meta.get("comments") or [])
        if not any(
            isinstance(c, dict) and "OCR-Quelle" in str(c.get("body") or "")
            for c in comments
        ):
            comments.append(
                {
                    "author": "InstantLens Doc",
                    "body": doc.source_comment,
                    "start": 0,
                    "end": 0,
                    "anchor_text": "",
                    "resolved": False,
                }
            )
            doc.meta["comments"] = comments
    doc.html = blocks_to_word_suite_html(
        doc.blocks,
        text=doc.text,
        title=doc.title,
        source_path=doc.source_path,
        source_page=doc.source_page,
        sidecar=doc.sidecar,
        font_family=str(doc.meta.get("font_family") or DEFAULT_BODY_FONT),
        font_size_pt=float(doc.meta.get("font_size_pt") or DEFAULT_BODY_PT),
        header=str(doc.meta.get("header") or ""),
        footer=str(doc.meta.get("footer") or ""),
    )
    tokens = extract_field_tokens((doc.text or "") + "\n" + (doc.html or ""))
    if tokens:
        existing = dict(doc.meta.get("field_tokens") or {})
        existing.update(tokens)
        doc.meta["field_tokens"] = existing
    return doc


def build_word_suite_document(
    *,
    text: str = "",
    blocks: Sequence[Union[OcrLayoutBlock, WordSuiteBlock]] | None = None,
    title: str = "OCR → Word-Suite",
    source: str = "",
    lang: str = "deu+eng",
    mode: str = "editable_text",
    sidecar: str | Path | None = None,
    auto_format: bool = True,
    meta: dict[str, Any] | None = None,
) -> WordSuiteDocument:
    """Baut ein Word-Suite-Dokument aus Text und/oder Layout-Blöcken."""
    ws_blocks = _ws_blocks_from_ocr(
        [b for b in (blocks or []) if isinstance(b, OcrLayoutBlock)]
    )
    if not ws_blocks and blocks:
        for i, b in enumerate(blocks):
            if isinstance(b, WordSuiteBlock):
                ws_blocks.append(b)
            elif isinstance(b, dict):
                ws_blocks.append(
                    WordSuiteBlock(
                        reading_order=int(b.get("reading_order", i)),
                        text=str(b.get("text") or "").strip(),
                        block_num=int(b.get("block_num", 0) or 0),
                        left=int(b.get("left", 0) or 0),
                        top=int(b.get("top", 0) or 0),
                        width=int(b.get("width", 0) or 0),
                        height=int(b.get("height", 0) or 0),
                        conf=float(b.get("conf", -1) or -1),
                        lines=list(b.get("lines") or []),
                        font_name=str(b.get("font_name") or ""),
                        font_size_pt=float(b.get("font_size_pt") or 0.0),
                        bold=bool(b.get("bold")),
                        italic=bool(b.get("italic")),
                        page=int(b.get("page") or 0),
                        is_heading=bool(b.get("is_heading")),
                        align=str(b.get("align") or ""),
                        list_kind=str(b.get("list_kind") or ""),
                        table_cells=_sanitize_table_cells(b.get("table_cells")),
                    )
                )
    body = ""
    if ws_blocks:
        body = blocks_to_word_suite_text(ws_blocks)
    if not body.strip():
        body = sanitize_ocr_visible_text(text or "").strip()
        if body:
            ws_blocks = _paragraphs_as_blocks(body)
    formatted, did_fmt = _maybe_auto_format(body, enabled=auto_format)
    formatted = sanitize_ocr_visible_text(formatted)
    src_path = None
    src_page = _int_meta(dict(meta or {}), "page")
    if source:
        src_path = str(source)
    doc = WordSuiteDocument(
        title=title or "OCR → Word-Suite",
        text=formatted,
        blocks=ws_blocks,
        source=source or "",
        lang=lang or "deu+eng",
        mode=mode or "editable_text",
        sidecar=str(sidecar) if sidecar else None,
        auto_formatted=did_fmt,
        meta=dict(meta or {}),
        source_path=src_path,
        source_page=src_page,
    )
    return _finalize_word_suite_document(doc)


def import_ildocr_sidecar(
    path: PathLike,
    *,
    auto_format: bool = True,
    title: str | None = None,
) -> WordSuiteDocument:
    """``*.ildocr.txt`` (oder verwandte Sidecars) als Word-Suite-Dokument laden."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(str(p))
    suffix = p.name.lower()
    raw = p.read_text(encoding="utf-8", errors="replace")

    # hOCR: Fonts/Ausrichtung aus Tesseract, nicht als Monospace-Dump
    if suffix.endswith(".ildocr.hocr") or suffix.endswith(".hocr"):
        hocr_blocks = parse_hocr_to_blocks(raw)
        if hocr_blocks:
            return build_word_suite_document(
                text=blocks_to_word_suite_text(hocr_blocks),
                blocks=hocr_blocks,
                title=title or f"Word-Suite — {p.stem}",
                source=str(p),
                mode="hocr",
                sidecar=str(p),
                auto_format=auto_format,
                meta={"format": "hocr"},
            )
        plain = re.sub(r"<script[\s\S]*?</script>", " ", raw, flags=re.I)
        plain = re.sub(r"<style[\s\S]*?</style>", " ", plain, flags=re.I)
        plain = re.sub(r"<br\s*/?>", "\n", plain, flags=re.I)
        plain = re.sub(r"</p\s*>", "\n\n", plain, flags=re.I)
        plain = re.sub(r"<[^>]+>", " ", plain)
        plain = re.sub(r"[ \t]+", " ", plain)
        plain = re.sub(r"\n{3,}", "\n\n", sanitize_ocr_visible_text(plain)).strip()
        return build_word_suite_document(
            text=plain,
            title=title or f"Word-Suite — {p.stem}",
            source=str(p),
            mode="hocr",
            sidecar=str(p),
            auto_format=auto_format,
            meta={"format": "hocr"},
        )

    # TSV: Tesseract-Wortzeilen oder Dokumenttabelle
    if suffix.endswith(".ildocr.tsv") or suffix.endswith(".tsv"):
        lines = raw.splitlines()
        first = (lines[0] if lines else "").lower()
        looks_tess = first.startswith("level") or (
            len(lines) > 1 and len(lines[1].split("\t")) >= 12
        )
        if not looks_tess:
            cells: List[List[str]] = []
            for row in lines:
                if not row.strip():
                    continue
                cells.append(
                    [sanitize_ocr_visible_text(c).strip() for c in row.split("\t")]
                )
            cleaned = _sanitize_table_cells(cells)
            if cleaned:
                return build_word_suite_document(
                    text=_table_plain(cleaned),
                    blocks=[
                        WordSuiteBlock(
                            reading_order=0,
                            text=_table_plain(cleaned),
                            lines=_table_plain(cleaned).splitlines(),
                            table_cells=cleaned,
                        )
                    ],
                    title=title or f"Word-Suite — {p.stem}",
                    source=str(p),
                    mode="tsv",
                    sidecar=str(p),
                    auto_format=False,
                    meta={"format": "tsv", "table_rows": cleaned},
                )
        lines_out: List[str] = []
        cur_key: tuple[int, int, int] | None = None
        words: List[str] = []
        for i, row in enumerate(raw.splitlines()):
            if i == 0 and row.lower().startswith("level"):
                continue
            parts = row.split("\t")
            if len(parts) < 12:
                continue
            try:
                level = int(parts[0])
            except Exception:
                continue
            if level != 5:
                continue
            word = (parts[11] or "").strip()
            if not word:
                continue
            try:
                key = (int(parts[2]), int(parts[3]), int(parts[4]))
            except Exception:
                key = (0, 0, i)
            if cur_key is None:
                cur_key = key
            if key != cur_key:
                if words:
                    lines_out.append(" ".join(words))
                words = [word]
                cur_key = key
            else:
                words.append(word)
        if words:
            lines_out.append(" ".join(words))
        body = "\n".join(lines_out).strip()
        return build_word_suite_document(
            text=body,
            title=title or f"Word-Suite — {p.stem}",
            source=str(p),
            mode="tsv",
            sidecar=str(p),
            auto_format=auto_format,
            meta={"format": "tsv", "lines": len(lines_out)},
        )

    meta, body, header_blocks = strip_ildocr_header(raw)
    mode = str(meta.get("mode") or "ildocr")
    lang = str(meta.get("lang") or "deu+eng")
    return build_word_suite_document(
        text=body,
        blocks=header_blocks,
        title=title or f"Word-Suite — {p.stem}",
        source=str(p),
        lang=lang,
        mode=mode,
        sidecar=str(p),
        auto_format=auto_format,
        meta=meta,
    )


def ocr_result_to_word_suite(
    result: OcrResult,
    *,
    auto_format: bool = True,
    title: str | None = None,
) -> WordSuiteDocument:
    """``OcrResult`` → Word-Suite-Dokument (Blöcke / Lesereihenfolge)."""
    hocr = ""
    layout = getattr(result, "layout", None)
    if layout is not None:
        hocr = str(getattr(layout, "hocr", "") or "")
    if not hocr and getattr(result, "hocr_path", None):
        try:
            hocr = Path(str(result.hocr_path)).read_text(encoding="utf-8", errors="replace")
        except Exception:
            hocr = ""
    hocr_blocks = parse_hocr_to_blocks(hocr) if hocr else []
    if hocr_blocks:
        return build_word_suite_document(
            text=blocks_to_word_suite_text(hocr_blocks),
            blocks=hocr_blocks,
            title=title or f"Word-Suite — {result.source_label or 'OCR'}",
            source=result.source_label or "",
            lang=result.lang,
            mode="hocr",
            sidecar=str(result.sidecar) if result.sidecar else None,
            auto_format=auto_format,
            meta={
                "format": "hocr",
                "searchable_pdf": str(result.searchable_pdf) if result.searchable_pdf else "",
                "hocr": str(result.hocr_path) if result.hocr_path else "",
                "table_rows": list(result.table_rows or []),
            },
        )
    blocks = list(result.blocks or [])
    if not blocks and result.layout is not None:
        blocks = list(result.layout.blocks or [])
    text = (result.text or "").strip()
    if not text and blocks:
        text = format_layout_text(blocks)
    # Sidecar-Header entfernen falls Text aus Sidecar stammt
    if text.lstrip().startswith("# InstantLens Doc OCR"):
        _meta, body, hdr_blocks = strip_ildocr_header(text)
        text = body
        if not blocks and hdr_blocks:
            _meta = dict(_meta)
            if result.table_rows:
                _meta.setdefault("table_rows", list(result.table_rows))
            return build_word_suite_document(
                text=text,
                blocks=hdr_blocks,
                title=title or f"Word-Suite — {result.source_label or 'OCR'}",
                source=result.source_label or "",
                lang=result.lang,
                mode=result.mode.value if hasattr(result.mode, "value") else str(result.mode),
                sidecar=str(result.sidecar) if result.sidecar else None,
                auto_format=auto_format,
                meta=_meta,
            )
    return build_word_suite_document(
        text=text,
        blocks=blocks,
        title=title or f"Word-Suite — {result.source_label or 'OCR'}",
        source=result.source_label or "",
        lang=result.lang,
        mode=result.mode.value if hasattr(result.mode, "value") else str(result.mode),
        sidecar=str(result.sidecar) if result.sidecar else None,
        auto_format=auto_format,
        meta={
            "searchable_pdf": str(result.searchable_pdf) if result.searchable_pdf else "",
            "hocr": str(result.hocr_path) if result.hocr_path else "",
            "tsv": str(result.tsv_path) if result.tsv_path else "",
            "table_rows": list(result.table_rows or []),
        },
    )


def handoff_ocr_to_word_suite(
    source: PathLike | None = None,
    *,
    text: str | None = None,
    page: int = 1,
    lang: str = "deu+eng",
    auto_format: bool = True,
    title: str | None = None,
    prefer_layout: bool = True,
    out: PathLike | None = None,
) -> WordSuiteDocument:
    """
    Einheitlicher Handoff: Sidecar / Bild / PDF-Seite / Rohtext → Word-Suite.

    - ``*.ildocr.txt`` / ``.hocr`` / ``.tsv`` → ``import_ildocr_sidecar``
    - Bild → Layout-OCR (Default) bzw. editable OCR
    - PDF → Seite rendern + Layout-OCR
    - ``text=`` → Absätze übernehmen
    """
    doc: WordSuiteDocument
    if text is not None and source is None:
        doc = build_word_suite_document(
            text=text,
            title=title or "Word-Suite — OCR-Text",
            lang=lang,
            mode="text",
            auto_format=auto_format,
        )
    elif source is None:
        raise ValueError("source oder text erforderlich")
    else:
        p = Path(source)
        name_l = p.name.lower()
        if (
            ".ildocr." in name_l
            or name_l.endswith(".ildocr.txt")
            or name_l.endswith(".hocr")
            or name_l.endswith(".tsv")
            or name_l.endswith(".ildocr")
        ):
            doc = import_ildocr_sidecar(p, auto_format=auto_format, title=title)
        elif p.suffix.lower() == ".pdf":
            from ild_pdf import render_page

            idx = max(0, int(page) - 1)
            img = render_page(p, page_index=idx, scale=2.0)
            if prefer_layout:
                layout = ocr_image_layout(
                    img, lang=lang, include_hocr=False, include_tsv=False
                )
                doc = build_word_suite_document(
                    text=layout.text,
                    blocks=layout.blocks,
                    title=title or f"Word-Suite — {p.name} S.{idx + 1}",
                    source=str(p),
                    lang=lang,
                    mode=OcrOutputMode.LAYOUT_PRESERVE.value,
                    auto_format=auto_format,
                    meta={"page": idx + 1, "width": layout.width, "height": layout.height},
                )
            else:
                result = run_ocr(
                    img,
                    lang=lang,
                    mode=OcrOutputMode.EDITABLE_TEXT,
                    source_label=f"{p.name} S.{idx + 1}",
                )
                doc = ocr_result_to_word_suite(result, auto_format=auto_format, title=title)
        else:
            # Bild / sonstige Datei
            if prefer_layout:
                layout = ocr_image_layout(
                    p, lang=lang, include_hocr=False, include_tsv=False
                )
                doc = build_word_suite_document(
                    text=layout.text,
                    blocks=layout.blocks,
                    title=title or f"Word-Suite — {p.name}",
                    source=str(p),
                    lang=lang,
                    mode=OcrOutputMode.LAYOUT_PRESERVE.value,
                    auto_format=auto_format,
                    meta={"width": layout.width, "height": layout.height},
                )
            else:
                result = run_ocr(
                    p,
                    lang=lang,
                    mode=OcrOutputMode.EDITABLE_TEXT,
                    source_label=p.name,
                )
                doc = ocr_result_to_word_suite(result, auto_format=auto_format, title=title)

    if out is not None:
        dest = Path(out)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(doc.text or "", encoding="utf-8")
        doc.meta["out"] = str(dest)
    return doc


# Alias für Scripting / CLI
ocr_to_word_suite = handoff_ocr_to_word_suite


def word_suite_to_document(ws: WordSuiteDocument):
    """Word-Suite → ``Document`` (DocKind.DOCX, rich HTML) wie ein geöffnetes DOCX."""
    from instantlensdoc.core.documents import DocKind, Document

    if not (ws.html or "").strip():
        _finalize_word_suite_document(ws)
    meta = dict(ws.meta or {})
    meta["html"] = ws.html or ""
    meta["rich_text"] = True
    meta.setdefault("font_family", DEFAULT_BODY_FONT)
    meta.setdefault("font_size_pt", DEFAULT_BODY_PT)
    meta["word_suite"] = True
    meta["ocr_mode"] = ws.mode
    meta["block_count"] = ws.block_count
    if ws.sidecar:
        meta["sidecar"] = ws.sidecar
    if ws.source_path:
        meta["source_path"] = ws.source_path
    if ws.source_page:
        meta["source_page"] = int(ws.source_page)
    if ws.source_comment:
        meta["source_comment"] = ws.source_comment
    if ws.meta.get("header"):
        meta["header"] = str(ws.meta.get("header") or "")
    if ws.meta.get("footer"):
        meta["footer"] = str(ws.meta.get("footer") or "")
    return Document(
        kind=DocKind.DOCX,
        title=ws.title or "Word-Suite — OCR",
        text=ws.text or "",
        dirty=False,
        meta=meta,
    )


def ocr_document_result_to_word_suite(
    result: Any,
    *,
    auto_format: bool = True,
    title: str | None = None,
    source_path: PathLike | None = None,
) -> WordSuiteDocument:
    """Batch-OCR (``OcrDocumentResult``) → Word-Suite mit Seitenumbrüchen."""
    page_texts = list(getattr(result, "page_texts", None) or [])
    text = str(getattr(result, "text", "") or "")
    page_from = int(getattr(result, "page_from", 1) or 1)
    blocks: List[WordSuiteBlock] = []
    order = 0
    for i, raw in enumerate(page_texts):
        page_no = page_from + i
        body = (raw or "").strip()
        if not body:
            continue
        for para in _paragraphs_as_blocks(body):
            para.reading_order = order
            para.page = page_no
            blocks.append(para)
            order += 1
    if not blocks and text.strip():
        # Fallback: --- Seite N --- Header aus Batch-TXT
        chunks = re.split(r"(?m)^--- Seite\s+(\d+)[^\n]*---\s*$", text)
        if len(chunks) > 1:
            # split keeps delimiters: [pre, n1, body1, n2, body2, ...]
            pre = chunks[0].strip()
            if pre:
                for para in _paragraphs_as_blocks(pre):
                    para.reading_order = order
                    blocks.append(para)
                    order += 1
            for j in range(1, len(chunks), 2):
                try:
                    page_no = int(chunks[j])
                except (TypeError, ValueError):
                    page_no = 0
                body = chunks[j + 1] if j + 1 < len(chunks) else ""
                for para in _paragraphs_as_blocks(body):
                    para.reading_order = order
                    para.page = page_no
                    blocks.append(para)
                    order += 1
        else:
            blocks = _paragraphs_as_blocks(text)
    src = str(source_path or "")
    lang = str(getattr(result, "lang", None) or "deu+eng")
    return build_word_suite_document(
        text=text,
        blocks=blocks,
        title=title or "Word-Suite — OCR gesamtes PDF",
        source=src,
        lang=lang,
        mode="ocr_pdf",
        auto_format=auto_format,
        meta={
            "page_from": getattr(result, "page_from", 1),
            "page_to": getattr(result, "page_to", 0),
            "pages_done": getattr(result, "pages_done", 0),
            "dpi": getattr(result, "dpi", 0),
        },
    )


def pdf_extracted_to_word_suite(
    pdf_path: PathLike,
    *,
    page_index: int | None = None,
    password: str | None = None,
    all_pages: bool = False,
    title: str | None = None,
    auto_format: bool = False,
) -> WordSuiteDocument:
    """PDF-eingebetteter Text → Word-Suite (Absätze, Fontgröße, Seitenumbrüche)."""
    from ild_pdf.overlay import (
        extract_all_plain_text,
        extract_page_plain_text,
        extract_text_paragraphs,
    )

    p = Path(pdf_path)
    blocks: List[WordSuiteBlock] = []
    order = 0
    pages: List[int]
    if all_pages:
        try:
            from ild_pdf.pdfium_open import open_pdfium

            kwargs = {}
            if password:
                kwargs["password"] = password
            doc_pdf = open_pdfium(p, **kwargs)
            try:
                n = len(doc_pdf)
            finally:
                doc_pdf.close()
        except Exception:
            n = 1
        pages = list(range(max(1, n)))
    else:
        pages = [max(0, int(page_index or 0))]

    for idx in pages:
        paras = []
        try:
            paras = extract_text_paragraphs(p, idx)
        except Exception:
            paras = []
        if paras:
            for para in paras:
                txt = sanitize_ocr_visible_text((getattr(para, "text", "") or "")).strip()
                if not txt:
                    continue
                fs = float(getattr(para, "font_size", 0.0) or 0.0)
                left = int(getattr(para, "x", 0) or 0)
                width = int(getattr(para, "width", 0) or 0)
                font_name = str(getattr(para, "font_name", "") or "")
                fb, fi, fam = _font_style_from_name(font_name)
                blocks.append(
                    WordSuiteBlock(
                        reading_order=order,
                        text=txt,
                        left=left,
                        top=int(getattr(para, "y", 0) or 0),
                        width=width,
                        height=int(getattr(para, "height", 0) or 0),
                        font_size_pt=fs if fs > 0 else 0.0,
                        font_name=fam or font_name,
                        bold=fb,
                        italic=fi,
                        page=idx + 1,
                        lines=txt.splitlines(),
                    )
                )
                order += 1
            continue
        try:
            raw = extract_page_plain_text(p, idx, password=password)
        except Exception:
            raw = ""
        if not (raw or "").strip():
            continue
        for para in _paragraphs_as_blocks(raw):
            para.reading_order = order
            para.page = idx + 1
            blocks.append(para)
            order += 1

    if all_pages:
        try:
            fallback_text = extract_all_plain_text(
                p, password=password, page_headers=True
            )
        except Exception:
            fallback_text = ""
    else:
        try:
            fallback_text = extract_page_plain_text(
                p, pages[0], password=password
            )
        except Exception:
            fallback_text = ""

    page_meta = None if all_pages else (pages[0] + 1)
    label = p.name if all_pages else f"{p.name} S.{page_meta}"
    return build_word_suite_document(
        text=fallback_text,
        blocks=blocks,
        title=title or f"Word-Suite — {label}",
        source=str(p),
        mode="pdf_extract",
        auto_format=auto_format,
        meta={"page": page_meta or "", "all_pages": bool(all_pages)},
    )


def scan_session_to_word_suite(
    session: Any,
    *,
    auto_format: bool = True,
    title: str | None = None,
) -> WordSuiteDocument:
    """Scan-OCR-Ergebnis (``ScanSessionResult``) → Word-Suite mit Seitenumbrüchen."""
    pages = list(getattr(session, "pages", None) or [])
    pdf_path = getattr(session, "pdf_path", None)
    blocks: List[WordSuiteBlock] = []
    order = 0
    sidecar = None
    lang = "deu+eng"
    for i, page in enumerate(pages, 1):
        ocr = getattr(page, "ocr", None)
        page_index = getattr(page, "page_index", None)
        page_no = (int(page_index) + 1) if page_index is not None else i
        side = getattr(page, "sidecar", None)
        if side and sidecar is None:
            sidecar = str(side)
        if ocr is None:
            continue
        lang = getattr(ocr, "lang", None) or lang
        ocr_blocks = list(getattr(ocr, "blocks", None) or [])
        if not ocr_blocks and getattr(ocr, "layout", None) is not None:
            ocr_blocks = list(getattr(ocr.layout, "blocks", None) or [])
        if ocr_blocks:
            for b in _ws_blocks_from_ocr(ocr_blocks):
                b.reading_order = order
                b.page = page_no
                blocks.append(b)
                order += 1
            continue
        raw = str(getattr(ocr, "text", "") or "").strip()
        if raw.lstrip().startswith("# InstantLens"):
            _meta, body, hdr = strip_ildocr_header(raw)
            raw = body or raw
            if hdr:
                for b in hdr:
                    b.reading_order = order
                    b.page = page_no
                    blocks.append(b)
                    order += 1
                continue
        for para in _paragraphs_as_blocks(raw):
            para.reading_order = order
            para.page = page_no
            blocks.append(para)
            order += 1
    combined = ""
    try:
        combined = str(getattr(session, "combined_text", "") or "")
    except Exception:
        combined = ""
    stem = Path(str(pdf_path)).stem if pdf_path else "Scan"
    return build_word_suite_document(
        text=combined,
        blocks=blocks,
        title=title or f"Word-Suite — Scan {stem}",
        source=str(pdf_path) if pdf_path else "",
        lang=lang,
        mode="scan_ocr",
        sidecar=sidecar,
        auto_format=auto_format,
        meta={"pages": len(pages)},
    )


def open_ocr_result(
    source: PathLike | None = None,
    *,
    text: str | None = None,
    result: Any = None,
    scan: Any = None,
    pdf_extract: PathLike | None = None,
    pdf_extract_all: bool = False,
    page: int = 1,
    page_index: int | None = None,
    password: str | None = None,
    lang: str = "deu+eng",
    auto_format: bool = True,
    title: str | None = None,
    prefer_layout: bool = True,
    source_path: PathLike | None = None,
    source_page: int | None = None,
    out: PathLike | None = None,
):
    """
    Einheitlicher Einstieg: OCR / Sidecar / Scan / PDF-Text → ``Document`` (DOCX).

    Das Arbeitsdokument ist ein rich ``QTextDocument`` (gleiche Art wie ein
    geöffnetes DOCX). Scan-/PDF-Quelle bleibt in ``meta.sidecar`` / Kommentar.
    """
    ws: WordSuiteDocument
    if scan is not None:
        ws = scan_session_to_word_suite(scan, auto_format=auto_format, title=title)
    elif result is not None and hasattr(result, "page_texts"):
        ws = ocr_document_result_to_word_suite(
            result,
            auto_format=auto_format,
            title=title,
            source_path=source_path or source,
        )
    elif result is not None:
        ws = ocr_result_to_word_suite(result, auto_format=auto_format, title=title)
    elif pdf_extract is not None:
        idx = page_index
        if idx is None and page:
            idx = max(0, int(page) - 1)
        ws = pdf_extracted_to_word_suite(
            pdf_extract,
            page_index=idx,
            password=password,
            all_pages=bool(pdf_extract_all),
            title=title,
            auto_format=auto_format,
        )
    else:
        ws = handoff_ocr_to_word_suite(
            source,
            text=text,
            page=page,
            lang=lang,
            auto_format=auto_format,
            title=title,
            prefer_layout=prefer_layout,
            out=out,
        )
    if source_path and not ws.source_path:
        ws.source_path = str(source_path)
    if source_page and not ws.source_page:
        ws.source_page = int(source_page)
        ws.meta["page"] = int(source_page)
    _finalize_word_suite_document(ws)
    if out is not None and not ws.meta.get("out"):
        dest = Path(out)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(ws.text or "", encoding="utf-8")
        ws.meta["out"] = str(dest)
    return word_suite_to_document(ws)

