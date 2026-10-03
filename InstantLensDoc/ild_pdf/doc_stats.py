"""Dokument-Statistik: Seiten, Wörter, Annotationen, Dateigröße — 1.6.3."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


STATS_SCHEMA_ID = "ildstats-v1"
STATS_VERSION = 1


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

    def to_export_dict(self) -> dict[str, Any]:
        """Export-Dict Schema ildstats-v1 — 1.6.2."""
        return {
            "version": STATS_VERSION,
            "schema": STATS_SCHEMA_ID,
            "stats": {
                "path": self.path,
                "pages": int(self.pages),
                "words": int(self.words) if self.has_text else None,
                "has_text": bool(self.has_text),
                "annotations": int(self.annotations),
                "file_size": int(self.file_size),
                "file_size_label": self.format_size(),
            },
        }

    def format_text(self) -> str:
        """Copy-as-Text — 1.6.2."""
        words = str(self.words) if self.has_text else "—"
        return (
            "Dokument-Statistik\n"
            f"Datei: {Path(self.path).name}\n"
            f"Pfad: {self.path}\n"
            f"Seiten: {self.pages}\n"
            f"Wörter: {words}\n"
            f"Annotationen: {self.annotations}\n"
            f"Dateigröße: {self.format_size()} ({self.file_size} B)\n"
        )


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


def export_document_stats_json(
    stats: DocumentStats,
    path: str | Path,
) -> Path:
    """
    Dokument-Statistik als ildstats-v1 JSON schreiben — 1.6.2/1.6.3.
    Encoding: UTF-8 ohne BOM (BOM nicht nötig für JSON).
    """
    path = Path(path)
    path.write_text(
        json.dumps(stats.to_export_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",  # kein utf-8-sig — BOM nicht nötig
    )
    return path


def format_document_stats_text(stats: DocumentStats) -> str:
    """Alias Copy-as-Text — 1.6.2."""
    return stats.format_text()
