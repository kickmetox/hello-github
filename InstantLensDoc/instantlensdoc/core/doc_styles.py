"""Formatvorlagen für Word-Suite: Katalog, QSettings, DOCX styles.xml.

Builtin: Normal, Titel, Überschrift 1–3, Zitat, Beschriftung.
Benutzerstile: anlegen/ändern/löschen; Persistenz in QSettings und DOCX.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

from PySide6.QtGui import QTextFormat

ILD_STYLE_PROP = int(QTextFormat.UserProperty) + 2659

CHROME_ORG = "Andreas Meyer"
CHROME_APP = "InstantLensDoc"
CUSTOM_STYLES_KEY = "wordSuite/customStyles"


@dataclass
class StyleSpec:
    id: str
    label: str
    word_name: str
    size: float = 11.0
    bold: bool = False
    italic: bool = False
    align: str = "left"
    indent: float = 0.0
    heading: int = 0
    color: str | None = None
    space_before: float = 0.0
    space_after: float = 8.0
    builtin: bool = True
    html_class: str = ""

    def __post_init__(self) -> None:
        if not self.html_class:
            self.html_class = f"ild-{self.id}"


BUILTIN_STYLES: tuple[StyleSpec, ...] = (
    StyleSpec("normal", "Normal", "Normal", size=11.0, space_after=8.0),
    StyleSpec(
        "title",
        "Titel",
        "Title",
        size=26.0,
        bold=True,
        align="center",
        space_after=12.0,
    ),
    StyleSpec(
        "h1",
        "Überschrift 1",
        "Heading 1",
        size=18.0,
        bold=True,
        heading=1,
        space_before=12.0,
        space_after=8.0,
    ),
    StyleSpec(
        "h2",
        "Überschrift 2",
        "Heading 2",
        size=14.0,
        bold=True,
        heading=2,
        space_before=10.0,
        space_after=6.0,
    ),
    StyleSpec(
        "h3",
        "Überschrift 3",
        "Heading 3",
        size=12.0,
        bold=True,
        italic=True,
        heading=3,
        space_before=8.0,
        space_after=4.0,
    ),
    StyleSpec(
        "quote",
        "Zitat",
        "Quote",
        size=11.0,
        italic=True,
        indent=36.0,
        color="#4B5563",
        space_before=6.0,
        space_after=6.0,
    ),
    StyleSpec(
        "caption",
        "Beschriftung",
        "Caption",
        size=9.0,
        italic=True,
        color="#374151",
        space_after=4.0,
    ),
)

_ALIASES = {
    "body": "normal",
    "heading1": "h1",
    "heading2": "h2",
    "heading3": "h3",
    "titel": "title",
    "zitat": "quote",
    "beschriftung": "caption",
    "überschrift 1": "h1",
    "überschrift 2": "h2",
    "überschrift 3": "h3",
}


def normalize_style_id(style_id: str | None) -> str:
    raw = (style_id or "normal").strip()
    key = raw.lower()
    if key in _ALIASES:
        return _ALIASES[key]
    return key or "normal"


def builtin_by_id() -> dict[str, StyleSpec]:
    return {s.id: s for s in BUILTIN_STYLES}


def _qsettings():
    from PySide6.QtCore import QSettings

    return QSettings(CHROME_ORG, CHROME_APP)


def load_custom_styles() -> list[StyleSpec]:
    """Benutzerstile aus QSettings."""
    try:
        raw = _qsettings().value(CUSTOM_STYLES_KEY, "")
    except Exception:
        raw = ""
    if not raw:
        return []
    try:
        data = json.loads(str(raw))
    except Exception:
        return []
    out: list[StyleSpec] = []
    if not isinstance(data, list):
        return out
    for item in data:
        if not isinstance(item, dict):
            continue
        sid = normalize_style_id(str(item.get("id") or item.get("label") or ""))
        if not sid or sid in builtin_by_id():
            continue
        out.append(
            StyleSpec(
                id=sid,
                label=str(item.get("label") or sid),
                word_name=str(item.get("word_name") or item.get("label") or sid),
                size=float(item.get("size") or 11.0),
                bold=bool(item.get("bold")),
                italic=bool(item.get("italic")),
                align=str(item.get("align") or "left"),
                indent=float(item.get("indent") or 0.0),
                heading=int(item.get("heading") or 0),
                color=item.get("color") or None,
                space_before=float(item.get("space_before") or 0.0),
                space_after=float(item.get("space_after") or 8.0),
                builtin=False,
                html_class=str(item.get("html_class") or f"ild-{sid}"),
            )
        )
    return out


def save_custom_styles(styles: Iterable[StyleSpec]) -> None:
    payload = []
    for s in styles:
        if s.builtin:
            continue
        d = asdict(s)
        d["builtin"] = False
        payload.append(d)
    try:
        _qsettings().setValue(CUSTOM_STYLES_KEY, json.dumps(payload, ensure_ascii=False))
    except Exception:
        pass


def all_styles(extra: Iterable[StyleSpec] | None = None) -> list[StyleSpec]:
    seen: set[str] = set()
    out: list[StyleSpec] = []
    for s in list(BUILTIN_STYLES) + list(extra or ()) + load_custom_styles():
        if s.id in seen:
            continue
        seen.add(s.id)
        out.append(s)
    return out


def get_style(style_id: str, extra: Iterable[StyleSpec] | None = None) -> StyleSpec:
    sid = normalize_style_id(style_id)
    for s in all_styles(extra):
        if s.id == sid:
            return s
    return builtin_by_id()["normal"]


def upsert_custom_style(spec: StyleSpec) -> StyleSpec:
    spec.builtin = False
    spec.id = normalize_style_id(spec.id)
    customs = [s for s in load_custom_styles() if s.id != spec.id]
    customs.append(spec)
    save_custom_styles(customs)
    return spec


def delete_custom_style(style_id: str) -> bool:
    sid = normalize_style_id(style_id)
    if sid in builtin_by_id():
        return False
    before = load_custom_styles()
    after = [s for s in before if s.id != sid]
    if len(after) == len(before):
        return False
    save_custom_styles(after)
    return True


def collect_block_style_ids(document) -> list[str]:
    ids: list[str] = []
    block = document.firstBlock()
    while block.isValid():
        raw = block.blockFormat().property(ILD_STYLE_PROP)
        ids.append(normalize_style_id(str(raw) if raw else "normal"))
        block = block.next()
    return ids


def inject_style_classes(html: str, style_ids: list[str]) -> str:
    """Fügt class=\"ild-…\" an Block-Tags in Dokumentreihenfolge an."""
    import re

    if not html or not style_ids:
        return html or ""
    idx = 0
    pattern = re.compile(r"<(p|h[1-6]|li)(\s[^>]*)?>", re.I)

    def _repl(m: re.Match[str]) -> str:
        nonlocal idx
        tag = m.group(1)
        attrs = m.group(2) or ""
        if idx >= len(style_ids):
            return m.group(0)
        sid = style_ids[idx]
        idx += 1
        cls = f"ild-{sid}"
        if "class=" in attrs.lower():
            attrs = re.sub(
                r'class=(["\'])(.*?)\1',
                lambda cm: f'class={cm.group(1)}{cm.group(2)} {cls}{cm.group(1)}',
                attrs,
                count=1,
                flags=re.I,
            )
        else:
            attrs = f' class="{cls}"' + attrs
        return f"<{tag}{attrs}>"

    return pattern.sub(_repl, html)


def word_name_for_id(style_id: str) -> str:
    return get_style(style_id).word_name


def style_id_from_word_name(name: str | None) -> str:
    n = (name or "").strip()
    if not n:
        return "normal"
    low = n.lower()
    for s in BUILTIN_STYLES:
        if s.word_name.lower() == low or s.label.lower() == low:
            return s.id
    m = __import__("re").match(r"(?:heading|überschrift)\s*([1-6])\b", n, __import__("re").I)
    if m:
        return f"h{m.group(1)}"
    return normalize_style_id(n)


def load_styles_from_docx(path: str | Path) -> list[StyleSpec]:
    """Benutzerdefinierte Absatzstile aus einer DOCX-Datei lesen."""
    try:
        from docx import Document as DocxDocument
        from docx.enum.style import WD_STYLE_TYPE
    except ImportError:
        return []
    try:
        d = DocxDocument(str(path))
    except Exception:
        return []
    builtin_words = {s.word_name.lower() for s in BUILTIN_STYLES}
    out: list[StyleSpec] = []
    try:
        styles = list(d.styles)
    except Exception:
        return []
    for st in styles:
        try:
            if getattr(st, "type", None) != WD_STYLE_TYPE.PARAGRAPH:
                continue
            name = str(st.name or "").strip()
            if not name or name.lower() in builtin_words:
                continue
            if getattr(st, "builtin", False):
                continue
            font = getattr(st, "font", None)
            size = 11.0
            try:
                if font is not None and font.size is not None:
                    size = float(font.size.pt)
            except Exception:
                pass
            bold = bool(getattr(font, "bold", False)) if font is not None else False
            italic = bool(getattr(font, "italic", False)) if font is not None else False
            sid = normalize_style_id(name)
            out.append(
                StyleSpec(
                    id=sid,
                    label=name,
                    word_name=name,
                    size=size,
                    bold=bold,
                    italic=italic,
                    builtin=False,
                )
            )
        except Exception:
            continue
    return out


def ensure_docx_styles(document: Any, extras: Iterable[StyleSpec] | None = None) -> None:
    """Stellt Builtin- + Custom-Stile in styles.xml sicher."""
    try:
        from docx.enum.style import WD_STYLE_TYPE
        from docx.shared import Pt, RGBColor
    except ImportError:
        return
    styles = document.styles
    for spec in all_styles(extras):
        try:
            st = styles[spec.word_name]
        except KeyError:
            try:
                st = styles.add_style(spec.word_name, WD_STYLE_TYPE.PARAGRAPH)
            except Exception:
                continue
        try:
            st.font.size = Pt(float(spec.size))
            st.font.bold = bool(spec.bold)
            st.font.italic = bool(spec.italic)
            if spec.color:
                hx = spec.color.lstrip("#")
                if len(hx) == 6:
                    st.font.color.rgb = RGBColor.from_string(hx.upper())
            pf = st.paragraph_format
            pf.space_before = Pt(float(spec.space_before))
            pf.space_after = Pt(float(spec.space_after))
            if spec.indent:
                from docx.shared import Emu, Pt as Pt2

                pf.left_indent = Pt2(float(spec.indent) * 0.75)
        except Exception:
            continue
