"""Volltextsuche über mehrere geöffnete Dokumente / PDFs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

_TEXT_SUFFIXES = {".txt", ".md", ".html", ".htm", ".json", ".ildocr.txt"}
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


@dataclass
class SearchHit:
    path: str
    page: int | None  # 0-based PDF page; None for text files
    line: int | None
    snippet: str
    kind: str  # text | pdf | sidecar


def _read_text_file(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except Exception:
            continue
    return ""


def _snippet_around(line: str, query: str, *, width: int = 120) -> str:
    """Kompaktes Snippet um den Treffer herum (casefold-Match)."""
    snippet = (line or "").strip()
    if not snippet:
        return ""
    ql = (query or "").casefold()
    ll = snippet.casefold()
    pos = ll.find(ql) if ql else -1
    if pos < 0:
        return snippet[:width]
    if len(snippet) <= width:
        return snippet
    start = max(0, pos - max(20, (width - len(query)) // 3))
    end = min(len(snippet), start + width)
    if end - start < width:
        start = max(0, end - width)
    out = snippet[start:end].strip()
    if start > 0:
        out = "…" + out
    if end < len(snippet):
        out = out + "…"
    return out


def _pdf_pages_text(pdf_path: Path) -> List[tuple[int, str]]:
    """Alle PDF-Seiten in einem Document-Open extrahieren (Performance)."""
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        parts: List[tuple[int, str]] = []
        for i in range(len(doc)):
            page = doc[i]
            try:
                tp = page.get_textpage()
                try:
                    parts.append((i, tp.get_text_bounded() or ""))
                finally:
                    tp.close()
            finally:
                page.close()
        return parts
    finally:
        doc.close()


def extract_document_text(path: str | Path) -> List[tuple[int | None, str]]:
    """(page_index, text) pro Abschnitt — page_index None bei Fließtext."""
    path = Path(path)
    if not path.is_file():
        return []
    suf = path.suffix.lower()
    if suf in _TEXT_SUFFIXES or suf == ".docx":
        if suf == ".docx":
            try:
                from docx import Document as DocxDocument

                doc = DocxDocument(str(path))
                return [(None, "\n".join(p.text for p in doc.paragraphs))]
            except Exception:
                return []
        return [(None, _read_text_file(path))]
    if suf == ".pdf":
        parts: List[tuple[int | None, str]] = []
        sidecar = path.with_suffix(path.suffix + ".ildocr.txt")
        if sidecar.is_file():
            parts.append((None, _read_text_file(sidecar)))
        try:
            for i, blob in _pdf_pages_text(path):
                parts.append((i, blob))
        except Exception:
            pass
        return parts
    sidecar = path.with_suffix(path.suffix + ".ildocr.txt")
    if sidecar.is_file():
        return [(None, _read_text_file(sidecar))]
    return []


def filter_pdf_paths(paths: Sequence[str]) -> List[str]:
    """Nur existierende PDF-Pfade (Reihenfolge erhalten, dedupe)."""
    out: List[str] = []
    seen: set[str] = set()
    for raw in paths:
        p = Path(raw)
        if not p.is_file() or p.suffix.lower() != ".pdf":
            continue
        key = str(p.resolve()) if p.exists() else str(p)
        if key in seen:
            continue
        seen.add(key)
        out.append(str(p))
    return out


def search_paths(
    paths: Sequence[str],
    query: str,
    *,
    max_hits: int = 200,
    pdf_only: bool = False,
) -> List[SearchHit]:
    """
    Volltextsuche über Pfade.
    pdf_only=True: nur PDFs (+ optional OCR-Sidecar am PDF).
    """
    q = (query or "").strip()
    if not q:
        return []
    ql = q.casefold()
    hits: List[SearchHit] = []
    iter_paths = filter_pdf_paths(paths) if pdf_only else list(paths)
    for raw in iter_paths:
        p = Path(raw)
        if not p.is_file():
            continue
        if pdf_only and p.suffix.lower() != ".pdf":
            continue
        kind = "pdf" if p.suffix.lower() == ".pdf" else "text"
        try:
            sections = extract_document_text(p)
        except Exception:
            continue
        for page_idx, blob in sections:
            if not blob or ql not in blob.casefold():
                continue
            for line_no, line in enumerate(blob.splitlines(), start=1):
                if ql not in line.casefold():
                    continue
                snippet = _snippet_around(line, q)
                hit_kind = kind
                if page_idx is None and p.suffix.lower() == ".pdf":
                    hit_kind = "sidecar"
                hits.append(
                    SearchHit(
                        path=str(p),
                        page=page_idx,
                        line=line_no if page_idx is None else line_no,
                        snippet=snippet,
                        kind=hit_kind,
                    )
                )
                if len(hits) >= max_hits:
                    return hits
    return hits


def search_open_pdfs(
    paths: Sequence[str],
    query: str,
    *,
    max_hits: int = 200,
) -> List[SearchHit]:
    """Schnellsuche nur über geöffnete / gelistete PDFs."""
    return search_paths(paths, query, max_hits=max_hits, pdf_only=True)


def sidebar_document_paths(files_widget) -> List[str]:
    """Pfade aus Sidebar-Dokumentenliste."""
    out: List[str] = []
    for i in range(files_widget.count()):
        item = files_widget.item(i)
        if item is None:
            continue
        data = item.data(256)
        if data:
            out.append(str(data))
    return out
