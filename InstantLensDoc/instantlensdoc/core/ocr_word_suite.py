"""OCR → Word-Suite Handoff — 2.6.15.

Nimmt Tesseract-/Layout-OCR-Ergebnisse und ``*.ildocr.*``-Sidecars und
überführt sie in editierbaren Word-Suite-Dokumenttext (Absätze in
Lesereihenfolge), der mit den Tools aus 2.6.10–2.6.14 weiterformatiert
und exportiert werden kann.
"""

from __future__ import annotations

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

    @property
    def block_count(self) -> int:
        return len(self.blocks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "text": self.text,
            "blocks": [b.to_dict() for b in self.blocks],
            "block_count": self.block_count,
            "source": self.source,
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
            )
        )
    out.sort(key=lambda x: (x.reading_order, x.top, x.left))
    for i, b in enumerate(out):
        b.reading_order = i
    return out


def _paragraphs_as_blocks(text: str) -> List[WordSuiteBlock]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    if not paras and (text or "").strip():
        paras = [(text or "").strip()]
    return [
        WordSuiteBlock(
            reading_order=i,
            text=p,
            lines=p.splitlines(),
        )
        for i, p in enumerate(paras)
    ]


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
    return WordSuiteDocument(
        title=title or "OCR → Word-Suite",
        text=formatted,
        blocks=ws_blocks,
        source=source or "",
        lang=lang or "deu+eng",
        mode=mode or "editable_text",
        sidecar=str(sidecar) if sidecar else None,
        auto_formatted=did_fmt,
        meta=dict(meta or {}),
    )


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
