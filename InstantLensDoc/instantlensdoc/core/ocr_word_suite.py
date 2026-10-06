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
PAGE_BREAK_HTML = (
    '<p style="page-break-before:always;-qt-paragraph-type:empty;'
    'margin-top:0px;margin-bottom:0px;"><br/></p>'
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
        else:
            order = int(getattr(b, "reading_order", i))
            text = str(getattr(b, "text", "") or "").strip()
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
                text=(b.text or "").strip(),
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
    paras = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    if not paras and (text or "").strip():
        paras = [(text or "").strip()]
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


def _html_escape(text: str) -> str:
    from instantlensdoc.ui.rich_lists import html_escape_ocr_text

    return html_escape_ocr_text(text)


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
    """Font/Überschrift an Blöcken setzen, wo Tesseract keine Fonts liefert."""
    sizes: List[float] = []
    for b in blocks:
        if b.font_size_pt and b.font_size_pt > 0:
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
    parts: List[str] = [head]
    last_page: int | None = None
    wrote = False
    for b in items:
        body = (b.text or "").strip()
        if not body:
            continue
        page = int(b.page or 0)
        if last_page is not None and page and page != last_page:
            parts.append(PAGE_BREAK_HTML)
        if page:
            last_page = page
        fam = html_lib.escape(b.font_name or font_family)
        size = float(b.font_size_pt or font_size_pt or DEFAULT_BODY_PT)
        inner = _html_escape(body)
        if b.italic:
            inner = f"<i>{inner}</i>"
        if b.bold or b.is_heading:
            inner = f"<b>{inner}</b>"
        tag = "h1" if b.is_heading else "p"
        parts.append(
            f'<{tag} style="font-family:{fam};font-size:{size:g}pt;">{inner}</{tag}>'
        )
        wrote = True
    if not wrote and (text or "").strip():
        for para in _paragraphs_as_blocks(text):
            parts.append(f"<p>{_html_escape(para.text)}</p>")
    parts.append("</body></html>")
    html = "".join(parts)
    try:
        from instantlensdoc.ui.rich_lists import sanitize_rich_html

        return sanitize_rich_html(html)
    except Exception:
        return html


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
    infer_block_styles(doc.blocks)
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
    )
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
                    )
                )
    body = ""
    if ws_blocks:
        body = blocks_to_word_suite_text(ws_blocks)
    if not body.strip():
        body = (text or "").strip()
        if body:
            ws_blocks = _paragraphs_as_blocks(body)
    formatted, did_fmt = _maybe_auto_format(body, enabled=auto_format)
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

    # hOCR: grob Text extrahieren
    if suffix.endswith(".ildocr.hocr") or suffix.endswith(".hocr"):
        plain = re.sub(r"<script[\s\S]*?</script>", " ", raw, flags=re.I)
        plain = re.sub(r"<style[\s\S]*?</style>", " ", plain, flags=re.I)
        plain = re.sub(r"<br\s*/?>", "\n", plain, flags=re.I)
        plain = re.sub(r"</p\s*>", "\n\n", plain, flags=re.I)
        plain = re.sub(r"<[^>]+>", " ", plain)
        plain = re.sub(r"[ \t]+", " ", plain)
        plain = re.sub(r"\n{3,}", "\n\n", plain).strip()
        return build_word_suite_document(
            text=plain,
            title=title or f"Word-Suite — {p.stem}",
            source=str(p),
            mode="hocr",
            sidecar=str(p),
            auto_format=auto_format,
            meta={"format": "hocr"},
        )

    # TSV: Wörter zu Zeilen zusammenfassen
    if suffix.endswith(".ildocr.tsv") or suffix.endswith(".tsv"):
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
                txt = (getattr(para, "text", "") or "").strip()
                if not txt:
                    continue
                fs = float(getattr(para, "font_size", 0.0) or 0.0)
                blocks.append(
                    WordSuiteBlock(
                        reading_order=order,
                        text=txt,
                        left=int(getattr(para, "x", 0) or 0),
                        top=int(getattr(para, "y", 0) or 0),
                        width=int(getattr(para, "width", 0) or 0),
                        height=int(getattr(para, "height", 0) or 0),
                        font_size_pt=fs if fs > 0 else 0.0,
                        font_name=str(getattr(para, "font_name", "") or ""),
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

