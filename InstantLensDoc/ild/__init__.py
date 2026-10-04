"""
Stabiles Scripting-API für InstantLens Doc (2.6.10).

Headless, ohne GUI. Nutzt ``ild_pdf`` + Lizenz/OCR der App.

    import ild
    ild.page_count("dok.pdf")
    ild.export_page("dok.pdf", 1, "seite.png")
    key = ild.generate_key("kunde@example.com")
    ild.auto_format_pdf("dok.pdf")
    ild.generate_toc(path="dok.pdf")
    ild.list_system_fonts()

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
    apply_redactions,
    auto_format_pdf,
    auto_format_text,
    encrypt_pdf,
    export_page,
    find_replace,
    generate_key,
    generate_toc,
    get_encryption_info,
    highlight_paragraphs,
    license_status,
    list_stamps,
    list_style_presets,
    list_system_fonts,
    merge_pdfs,
    ocr_image,
    ocr_pdf_page,
    open_info,
    outline_summary,
    page_count,
    remove_password,
    rotate_page,
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
    "generate_key",
    "verify_key",
    "license_status",
    "activate_license",
    "encrypt_pdf",
    "remove_password",
    "get_encryption_info",
]
