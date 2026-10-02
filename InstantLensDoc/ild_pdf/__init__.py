"""
ild_pdf — auskoppelbares PDF-Modul für InstantLens Doc und andere Apps.

Basiert auf pypdfium2 (PDFium, lizenzfreundlich). Kein Poppler/GPL.
"""

from .document import PdfDocument
from .render import render_page, render_pages
from .annotate import Annotation, AnnotationStore, AnnotationType, STAMP_PRESETS
from .pages import rotate_page, delete_pages, reorder_pages
from .images import (
    extract_page_image,
    extract_embedded_images,
    insert_image_as_page,
    insert_image_stamp_overlay,
)

__all__ = [
    "PdfDocument",
    "render_page",
    "render_pages",
    "Annotation",
    "AnnotationStore",
    "AnnotationType",
    "STAMP_PRESETS",
    "rotate_page",
    "delete_pages",
    "reorder_pages",
    "extract_page_image",
    "extract_embedded_images",
    "insert_image_as_page",
    "insert_image_stamp_overlay",
]

__version__ = "0.1.2"
