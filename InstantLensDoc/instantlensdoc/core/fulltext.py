"""Volltextsuche über mehrere geöffnete Dokumente."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

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


def _pdf_page_text(pdf_path: Path, page_index: int) -> str:
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        if page_index < 0 or page_index >= len(doc):
            return ""
        page = doc[page_index]
        try:
            tp = page.get_textpage()
            try:
                return tp.get_text_bounded() or ""
            finally:
                tp.close()
        finally:
            page.close()
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
        import pypdfium2 as pdfium

        doc = pdfium.PdfDocument(str(path))
        try:
            parts: List[tuple[int | None, str]] = []
            sidecar = path.with_suffix(path.suffix + ".ildocr.txt")
            if sidecar.is_file():
                parts.append((None, _read_text_file(sidecar)))
            for i in range(len(doc)):
                parts.append((i, _pdf_page_text(path, i)))
            return parts
        finally:
            doc.close()
    sidecar = path.with_suffix(path.suffix + ".ildocr.txt")
    if sidecar.is_file():
        return [(None, _read_text_file(sidecar))]
    return []


def search_paths(
    paths: Sequence[str],
    query: str,
    *,
    max_hits: int = 200,
) -> List[SearchHit]:
    q = (query or "").strip()
    if not q:
        return []
    ql = q.lower()
    hits: List[SearchHit] = []
    for raw in paths:
        p = Path(raw)
        if not p.is_file():
            continue
        kind = "pdf" if p.suffix.lower() == ".pdf" else "text"
        for page_idx, blob in extract_document_text(p):
            if ql not in blob.lower():
                continue
            # Zeilen mit Treffer
            for line_no, line in enumerate(blob.splitlines(), start=1):
                if ql not in line.lower():
                    continue
                snippet = line.strip()
                if len(snippet) > 120:
                    pos = line.lower().find(ql)
                    start = max(0, pos - 40)
                    snippet = line[start : start + 120].strip()
                hits.append(
                    SearchHit(
                        path=str(p),
                        page=page_idx,
                        line=line_no if page_idx is None else line_no,
                        snippet=snippet,
                        kind=kind if page_idx is not None else "sidecar" if ".ildocr" in p.name else kind,
                    )
                )
                if len(hits) >= max_hits:
                    return hits
    return hits


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
