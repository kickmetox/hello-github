"""PDF-Dokument öffnen/schließen und Metadaten."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pypdfium2 as pdfium


class PdfDocument:
    """Dünne Hülle um pypdfium2.PdfDocument."""

    def __init__(self, path: str | Path | None = None, *, password: str | None = None):
        self.path: Optional[Path] = Path(path) if path else None
        self.password: Optional[str] = password
        self._doc: Optional[pdfium.PdfDocument] = None
        if self.path is not None:
            self.open(self.path, password=password)

    def open(self, path: str | Path, password: str | None = None) -> None:
        self.close()
        self.path = Path(path)
        if not self.path.is_file():
            raise FileNotFoundError(f"PDF nicht gefunden: {self.path}")
        if password is not None:
            self.password = password
        # Fallback-Kette Bytes → Pfad → pikepdf-Reparatur statt nacktem
        # ``PdfDocument(str_path)`` (Windows: „Data format error“) — 2.6.53
        from .pdfium_open import PdfiumOpenError, open_pdfium

        try:
            self._doc = open_pdfium(self.path, password=self.password)
        except MemoryError:
            self._doc = None
            raise
        except PdfiumOpenError as e:
            self._doc = None
            raise RuntimeError(str(e)) from e
        except Exception as e:
            self._doc = None
            raise RuntimeError(f"PDF-Öffnung fehlgeschlagen: {e}") from e

    def close(self) -> None:
        if self._doc is not None:
            self._doc.close()
            self._doc = None

    @property
    def raw(self) -> pdfium.PdfDocument:
        if self._doc is None:
            raise RuntimeError("Kein PDF geöffnet")
        return self._doc

    @property
    def page_count(self) -> int:
        return len(self.raw)

    def page_size(self, index: int) -> tuple[float, float]:
        page = self.raw[index]
        try:
            w, h = page.get_size()
            return float(w), float(h)
        finally:
            page.close()

    def page_label(self, index: int) -> str:
        """PDF-Seitenlabel (römisch/arabisch/Präfix) oder '' wenn keines gesetzt."""
        if index < 0 or index >= self.page_count:
            return ""
        try:
            label = self.raw.get_page_label(index)
        except Exception:
            return ""
        return str(label or "").strip()

    def page_labels(self, *, max_pages: int | None = None) -> list[str]:
        """Seitenlabels (leere Strings wenn keine PageLabels-Dict im PDF).

        max_pages: optionaler Cap — bei großen PDFs teuer (pro Seite PDFium-Call).
        """
        n = self.page_count
        if max_pages is not None:
            n = max(0, min(n, int(max_pages)))
        return [self.page_label(i) for i in range(n)]

    def __enter__(self) -> "PdfDocument":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def __len__(self) -> int:
        return self.page_count


def format_page_status(
    page_index: int,
    page_count: int,
    label: str | None = None,
    *,
    prefix: str = "Seite",
) -> str:
    """Status-/Anzeigetext: 'Seite iii (3/10)' wenn Label, sonst 'Seite 3/10'."""
    n = max(0, int(page_index)) + 1
    total = max(0, int(page_count))
    lab = (label or "").strip()
    if lab:
        return f"{prefix} {lab} ({n}/{total})"
    return f"{prefix} {n}/{total}"
