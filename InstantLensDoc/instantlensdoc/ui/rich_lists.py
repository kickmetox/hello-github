"""Aufzählungen/Nummerierung für den QPlainTextEdit-Word-Editor.

QPlainTextDocumentLayout zeichnet keine QTextList-Marker. Sichtbare Listen
sind deshalb Unicode-Präfixe (• / 1.), nie Steuerzeichen wie ``¶`` oder ``\\x0c``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from typing import Iterable

# Steuer-/Form-Feed-Glyphen, die OCR oder Qt-Listen als „Bullet“ einschleusen.
CONTROL_GLYPHS = frozenset("\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f"
                           "\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b"
                           "\x1c\x1d\x1e\x1f\u00b6")
BULLET_GLYPHS = ("•", "◦", "▪", "◆", "►", "○", "■")
DEFAULT_BULLET = "•"
NESTED_BULLETS = ("•", "◦", "▪")
NESTED_ORDERED = ("1.", "a.", "i.")

_BULLET_CLASS = "".join(
    re.escape(g) for g in (*BULLET_GLYPHS, "-", "*", "·", "●", "○", "■", "□", "‣")
)
_CTRL_CLASS = "".join(re.escape(c) for c in CONTROL_GLYPHS)

LIST_PREFIX_RE = re.compile(
    rf"^(?P<ws>[ \t]*)(?P<mark>(?:[{_BULLET_CLASS}{_CTRL_CLASS}]|[0-9]+[.)]|[a-zA-Z][.)]|"
    r"[ivxlcdmIVXLCDM]+[.)])[ \t]+)"
)

_UL_RE = re.compile(r"<ul\b[^>]*>", re.I)
_OL_RE = re.compile(r"<ol\b[^>]*>", re.I)
_LI_RE = re.compile(r"<li\b[^>]*>", re.I)
_CTRL_HTML_RE = re.compile(
    r"(?:&#(?:1[2-9]|2[0-9]|3[01]|12|182);|&#x(?:[0-8BbCcEeF]|1[0-9A-Fa-f]|b6);|"
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\u00b6])"
)


@dataclass(frozen=True)
class ListPrefix:
    ws: str
    mark: str
    ordered: bool
    glyph: str
    number: int | None = None
    level: int = 0

    @property
    def full(self) -> str:
        return f"{self.ws}{self.mark}"


def strip_control_glyphs(text: str) -> str:
    """Entfernt Form-Feed/¶/C0-Steuerzeichen, lässt Newline/Tab."""
    if not text:
        return ""
    return "".join(ch for ch in text if ch in "\n\t\r" or ch not in CONTROL_GLYPHS)


def parse_list_prefix(text: str) -> ListPrefix | None:
    raw = text or ""
    m = LIST_PREFIX_RE.match(raw)
    if not m:
        return None
    ws = m.group("ws") or ""
    mark = m.group("mark")
    core = mark.strip()
    ordered = bool(re.match(r"^(?:\d+[.)]|[a-zA-Z][.)]|[ivxlcdmIVXLCDM]+[.)])$", core))
    glyph = core[:1] if not ordered else core
    number = None
    if ordered:
        nm = re.match(r"^(\d+)", core)
        if nm:
            number = int(nm.group(1))
    level = 0
    if ws:
        level = ws.count("\t") + max(0, (len(ws.replace("\t", "")) // 4))
    return ListPrefix(ws=ws, mark=mark, ordered=ordered, glyph=glyph, number=number, level=level)


def prefix_for(*, ordered: bool, index: int = 1, level: int = 0, glyph: str | None = None) -> str:
    lvl = max(0, int(level))
    if ordered:
        styles = NESTED_ORDERED
        token = styles[min(lvl, len(styles) - 1)]
        if lvl == 0:
            token = f"{max(1, int(index))}."
        elif token == "a.":
            token = f"{chr(ord('a') + (max(1, int(index)) - 1) % 26)}."
        return f"{token} "
    g = (glyph or "").strip() or NESTED_BULLETS[min(lvl, len(NESTED_BULLETS) - 1)]
    if g in CONTROL_GLYPHS or g in ("¶", "\x0c"):
        g = DEFAULT_BULLET
    return f"{g} "


def replace_prefix(text: str, new_prefix: str | None) -> str:
    info = parse_list_prefix(text)
    body = text[len(info.full) :] if info else (text or "")
    body = strip_control_glyphs(body)
    if new_prefix is None:
        return body
    return f"{new_prefix}{body}"


def looks_like_bullet_line(text: str) -> bool:
    t = (text or "").lstrip()
    if not t:
        return False
    if t[0] in CONTROL_GLYPHS or t[0] == "¶":
        return True
    return parse_list_prefix(text) is not None


def sanitize_rich_html(html: str) -> str:
    """OCR/DOCX-HTML: Listen als <p>• …</p>, keine Steuerzeichen-Bullets."""
    src = unescape(html or "")
    src = _CTRL_HTML_RE.sub("", src)
    src = src.replace("\x0c", "").replace("\u00b6", "")
    # Qt-Listen / HTML-Listen → Absätze mit sichtbarem Unicode-Bullet
    src = re.sub(r"</li\s*>", "</p>", src, flags=re.I)
    src = _LI_RE.sub("<p>• ", src)
    src = re.sub(r"</ul\s*>", "", src, flags=re.I)
    src = re.sub(r"</ol\s*>", "", src, flags=re.I)
    src = _UL_RE.sub("", src)
    src = _OL_RE.sub("", src)
    # -qt-list-mask / list-style Glyphs, die Qt als Steuerzeichen einbettet
    src = re.sub(r"-qt-list-indent:\s*\d+;?", "", src, flags=re.I)
    src = re.sub(r"list-style-type:\s*[^;\"']+;?", "", src, flags=re.I)

    def _fix_para(m: re.Match[str]) -> str:
        open_tag, body, close = m.group(1), m.group(2), m.group(3)
        plain = re.sub(r"<[^>]+>", "", body)
        plain = strip_control_glyphs(unescape(plain))
        info = parse_list_prefix(plain)
        if info and (info.glyph in CONTROL_GLYPHS or info.glyph in ("¶",)):
            rest = replace_prefix(plain, prefix_for(ordered=info.ordered, index=info.number or 1))
            return f"{open_tag}{rest}{close}"
        if plain[:1] in CONTROL_GLYPHS:
            rest = prefix_for(ordered=False) + plain.lstrip()
            rest = replace_prefix(rest, prefix_for(ordered=False)) if not parse_list_prefix(rest) else rest
            return f"{open_tag}{strip_control_glyphs(rest)}{close}"
        return f"{open_tag}{body}{close}"

    src = re.sub(r"(<(?:p|h[1-6]|li)\b[^>]*>)(.*?)(</(?:p|h[1-6]|li)\s*>)", _fix_para, src, flags=re.I | re.S)
    return src


def html_escape_ocr_text(text: str) -> str:
    from html import escape as html_escape

    clean = normalize_ocr_line(text or "")
    return html_escape(clean, quote=False).replace("\n", "<br/>")


def normalize_ocr_line(text: str) -> str:
    raw = text or ""
    lead = raw.lstrip(" \t")
    if lead[:1] in CONTROL_GLYPHS or lead[:1] == "¶":
        rest = strip_control_glyphs(lead[1:]).lstrip()
        return prefix_for(ordered=False) + rest
    clean = strip_control_glyphs(raw)
    info = parse_list_prefix(clean)
    if info and not info.ordered and info.glyph in ("-", "*", "·", "●"):
        return replace_prefix(clean, prefix_for(ordered=False, level=info.level))
    if info and (info.glyph in CONTROL_GLYPHS or info.glyph in ("¶",)):
        return replace_prefix(
            clean, prefix_for(ordered=info.ordered, index=info.number or 1, level=info.level)
        )
    return clean


def iter_valid_glyphs() -> Iterable[str]:
    return BULLET_GLYPHS
