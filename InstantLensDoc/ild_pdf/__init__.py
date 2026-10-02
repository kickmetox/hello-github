"""
ild_pdf — auskoppelbares PDF-Modul für InstantLens Doc und andere Apps.

Basiert auf pypdfium2 (PDFium, lizenzfreundlich). Kein Poppler/GPL.
"""

from .document import PdfDocument
from .render import render_page, render_pages
from .annotate import (
    Annotation,
    AnnotationStore,
    AnnotationType,
    DRAG_TYPES,
    STAMP_PRESETS,
)
from .pages import merge_pdfs, split_pdf, rotate_page, delete_pages, reorder_pages
from .outline import OutlineItem, extract_outline
from .images import (
    extract_page_image,
    extract_embedded_images,
    insert_image_as_page,
    insert_image_stamp_overlay,
    insert_signature_field,
    insert_signature_image,
)
from .overlay import (
    TextBlock,
    bake_text_overlays,
    extract_text_blocks,
    import_page_text_as_overlays,
)

__all__ = [
    "PdfDocument",
    "render_page",
    "render_pages",
    "Annotation",
    "AnnotationStore",
    "AnnotationType",
    "DRAG_TYPES",
    "STAMP_PRESETS",
    "merge_pdfs",
    "split_pdf",
    "rotate_page",
    "delete_pages",
    "reorder_pages",
    "OutlineItem",
    "extract_outline",
    "extract_page_image",
    "extract_embedded_images",
    "insert_image_as_page",
    "insert_image_stamp_overlay",
    "insert_signature_field",
    "insert_signature_image",
    "TextBlock",
    "extract_text_blocks",
    "import_page_text_as_overlays",
    "bake_text_overlays",
]

__version__ = "0.1.6"
