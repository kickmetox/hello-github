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
from .pages import (
    PAGE_SIZE_PRESETS,
    extract_page_range,
    merge_pdfs,
    split_pdf,
    rotate_page,
    flip_page,
    insert_blank_page,
    duplicate_page,
    delete_pages,
    reorder_pages,
    get_page_boxes,
    set_page_size,
    set_crop_box,
)
from .outline import OutlineItem, add_outline_item, delete_outline_item, extract_outline
from .images import (
    compress_image_for_pdf,
    compress_pdf_as_images,
    extract_page_image,
    extract_pages_as_images,
    extract_embedded_images,
    insert_image_as_page,
    insert_image_stamp_overlay,
    insert_signature_field,
    insert_signature_image,
)
from .overlay import (
    TextBlock,
    TextMatchRect,
    bake_text_overlays,
    extract_text_blocks,
    find_text_rects,
    import_page_text_as_overlays,
)
from .watermark import apply_page_numbers, apply_watermark
from .limits import PdfHealth, clamp_render_scale, inspect_pdf
from .render import clear_render_cache
from .security import needs_password, remove_password, set_password, try_open_password
from .redact import bake_redactions
from .metadata import PdfMetadata, get_metadata, set_metadata

__all__ = [
    "PdfDocument",
    "render_page",
    "render_pages",
    "clear_render_cache",
    "Annotation",
    "AnnotationStore",
    "AnnotationType",
    "DRAG_TYPES",
    "STAMP_PRESETS",
    "PAGE_SIZE_PRESETS",
    "extract_page_range",
    "merge_pdfs",
    "split_pdf",
    "rotate_page",
    "flip_page",
    "insert_blank_page",
    "duplicate_page",
    "delete_pages",
    "reorder_pages",
    "get_page_boxes",
    "set_page_size",
    "set_crop_box",
    "OutlineItem",
    "extract_outline",
    "add_outline_item",
    "delete_outline_item",
    "compress_image_for_pdf",
    "compress_pdf_as_images",
    "extract_page_image",
    "extract_pages_as_images",
    "extract_embedded_images",
    "insert_image_as_page",
    "insert_image_stamp_overlay",
    "insert_signature_field",
    "insert_signature_image",
    "TextBlock",
    "TextMatchRect",
    "extract_text_blocks",
    "find_text_rects",
    "import_page_text_as_overlays",
    "bake_text_overlays",
    "apply_watermark",
    "apply_page_numbers",
    "PdfHealth",
    "inspect_pdf",
    "clamp_render_scale",
    "needs_password",
    "try_open_password",
    "set_password",
    "remove_password",
    "bake_redactions",
    "PdfMetadata",
    "get_metadata",
    "set_metadata",
]

__version__ = "0.3.0"
