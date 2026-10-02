"""PDF-Seiten als Bilder rendern (pypdfium2)."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Union

from PIL import Image
import pypdfium2 as pdfium

from .document import PdfDocument


def render_page(
    source: Union[str, Path, PdfDocument, pdfium.PdfDocument],
    page_index: int = 0,
    scale: float = 2.0,
) -> Image.Image:
    """Eine Seite als PIL-Image rendern."""
    own = False
    if isinstance(source, (str, Path)):
        doc = pdfium.PdfDocument(str(source))
        own = True
    elif isinstance(source, PdfDocument):
        doc = source.raw
    else:
        doc = source

    try:
        page = doc[page_index]
        try:
            bitmap = page.render(scale=scale)
            return bitmap.to_pil()
        finally:
            page.close()
    finally:
        if own:
            doc.close()


def render_pages(
    source: Union[str, Path, PdfDocument],
    indices: Iterable[int] | None = None,
    scale: float = 2.0,
) -> List[Image.Image]:
    """Mehrere Seiten rendern. Ohne indices: alle Seiten."""
    own = False
    if isinstance(source, (str, Path)):
        doc = PdfDocument(source)
        own = True
    elif isinstance(source, PdfDocument):
        doc = source
    else:
        raise TypeError("source muss Pfad oder PdfDocument sein")

    try:
        pages = list(indices) if indices is not None else list(range(len(doc)))
        return [render_page(doc, i, scale=scale) for i in pages]
    finally:
        if own:
            doc.close()


def convert_from_path(path: str | Path, dpi: int = 150) -> List[Image.Image]:
    """pdf2image-ähnliche API für Drop-in-Ersatz."""
    scale = dpi / 72.0
    return render_pages(path, scale=scale)
