"""
Stabiles Scripting-API für InstantLens Doc (2.6.12).

Headless, ohne GUI. Nutzt ``ild_pdf`` + Lizenz/OCR der App.

    import ild
    ild.page_count("dok.pdf")
    ild.export_page("dok.pdf", 1, "seite.png")
    key = ild.generate_key("kunde@example.com")
    ild.auto_format_pdf("dok.pdf")
    ild.generate_toc(path="dok.pdf")
    ild.list_system_fonts()
    ild.list_page_formats()
    ild.apply_header_footer("dok.pdf", author="Max", title="Bericht")
    ild.apply_master_page("dok.pdf", "Buch", title="Roman")
    ild.satzspiegel("Taschenbuch")
    ild.layout_flow_text("Langer Text…", columns=2)

CLI: ``python -m ild --help`` · PowerShell: ``scripts\\ild.ps1``.
"""

from __future__ import annotations

from instantlensdoc import __version__ as version

from ild.api import (
    activate_license,
    add_custom_stamp_def,
    add_ink,
    add_redaction,
    add_shape,
    add_stamp,
    apply_header_footer,
    apply_master_page,
    apply_paragraph_format,
    apply_redactions,
    auto_format_pdf,
    auto_format_text,
    encrypt_pdf,
    export_page,
    find_replace,
    generate_key,
    generate_toc,
    get_encryption_info,
    grid_lines,
    highlight_paragraphs,
    layout_add_image_frame,
    layout_add_text_frame,
    layout_flow_text,
    layout_link_frames,
    layout_list_frames,
    layout_move_frame,
    layout_resize_frame,
    license_status,
    list_master_pages,
    list_page_formats,
    list_paragraph_styles,
    list_satzspiegel,
    list_stamps,
    list_style_presets,
    list_system_fonts,
    merge_pdfs,
    new_layout,
    ocr_image,
    ocr_pdf_page,
    open_info,
    outline_summary,
    page_count,
    remove_password,
    resolve_page_format,
    rotate_page,
    ruler_ticks,
    satzspiegel,
    set_page_format,
    split_pdf,
    verify_key,
)

__all__ = [
    "version",
    "open_info",
    "page_count",
    "export_page",
    "merge_pdfs",
    "split_pdf",
    "rotate_page",
    "ocr_image",
    "ocr_pdf_page",
    "add_redaction",
    "apply_redactions",
    "add_shape",
    "add_stamp",
    "add_ink",
    "highlight_paragraphs",
    "list_stamps",
    "add_custom_stamp_def",
    "auto_format_text",
    "auto_format_pdf",
    "generate_toc",
    "list_style_presets",
    "list_system_fonts",
    "find_replace",
    "outline_summary",
    "list_page_formats",
    "resolve_page_format",
    "set_page_format",
    "apply_header_footer",
    "apply_paragraph_format",
    "list_paragraph_styles",
    "ruler_ticks",
    "grid_lines",
    "satzspiegel",
    "list_satzspiegel",
    "list_master_pages",
    "apply_master_page",
    "new_layout",
    "layout_add_text_frame",
    "layout_add_image_frame",
    "layout_move_frame",
    "layout_resize_frame",
    "layout_link_frames",
    "layout_flow_text",
    "layout_list_frames",
    "generate_key",
    "verify_key",
    "license_status",
    "activate_license",
    "encrypt_pdf",
    "remove_password",
    "get_encryption_info",
]
