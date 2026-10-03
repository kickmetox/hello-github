"""Dokument-Statistik: Seiten, Wörter, Annotationen, Dateigröße — 1.6.0."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DocumentStats:
    path: str
    pages: int
    words: int
    annotations: int
    file_size: int
    has_text: bool

    def format_size(self) -> str:
        n = int(self.file_size)
        if n < 1024:
            return f"{n} B"
        if n < 1024 * 1024:
            return f"{n / 1024:.1f} KB"
        return f"{n / (1024 * 1024):.2f} MB"


_WORD_RE = re.compile(r"\w+", re.UNICODE)


def count_words(text: str) -> int:
    if not text:
        return 0
    return len(_WORD_RE.findall(text))


def collect_document_stats(
    pdf_path: str | Path,
    *,
    annotation_count: int | None = None,
) -> DocumentStats:
    """
    Seiten + Wörter (sichtbarer Text), Ann.-Anzahl, Dateigröße.
    annotation_count: optional von Sidecar/Store; sonst Sidecar laden.
    """
    from .overlay import extract_all_plain_text

    pdf_path = Path(pdf_path)
    size = int(pdf_path.stat().st_size) if pdf_path.is_file() else 0
    pages = 0
    try:
        import pypdfium2 as pdfium

        doc = pdfium.PdfDocument(str(pdf_path))
        try:
            pages = len(doc)
        finally:
            doc.close()
    except Exception:
        pages = 0

    text = ""
    try:
        text = extract_all_plain_text(pdf_path) or ""
    except Exception:
        text = ""
    words = count_words(text)
    has_text = bool(text.strip())

    ann = annotation_count
    if ann is None:
        try:
            from .annotate import AnnotationStore

            store = AnnotationStore(pdf_path)
            ann = len(store.annotations)
        except Exception:
            ann = 0

    return DocumentStats(
        path=str(pdf_path),
        pages=int(pages),
        words=int(words),
        annotations=int(ann or 0),
        file_size=size,
        has_text=has_text,
    )
