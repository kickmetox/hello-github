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
        if password is not None:
            self.password = password
        self._doc = pdfium.PdfDocument(str(self.path), password=self.password)

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

    def __enter__(self) -> "PdfDocument":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def __len__(self) -> int:
        return self.page_count
