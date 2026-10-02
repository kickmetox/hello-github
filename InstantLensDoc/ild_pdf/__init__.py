"""
ild_pdf — auskoppelbares PDF-Modul für InstantLens Doc und andere Apps.

Basiert auf pypdfium2 (PDFium, lizenzfreundlich). Kein Poppler/GPL.
"""

from .document import PdfDocument
from .render import render_page, render_pages
from .annotate import Annotation, AnnotationStore, AnnotationType
from .pages import rotate_page, delete_pages, reorder_pages

__all__ = [
    "PdfDocument",
    "render_page",
    "render_pages",
    "Annotation",
    "AnnotationStore",
    "AnnotationType",
    "rotate_page",
    "delete_pages",
    "reorder_pages",
]

__version__ = "0.1.0"
