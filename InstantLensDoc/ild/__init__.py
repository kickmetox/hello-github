"""
Stabiles Scripting-API für InstantLens Doc (2.6.8).

Headless, ohne GUI. Nutzt ``ild_pdf`` + Lizenz/OCR der App.

    import ild
    ild.page_count("dok.pdf")
    ild.export_page("dok.pdf", 1, "seite.png")
    key = ild.generate_key("kunde@example.com")

CLI: ``python -m ild --help`` · PowerShell: ``scripts\\ild.ps1``.
"""

from __future__ import annotations

from instantlensdoc import __version__ as version

from ild.api import (
    activate_license,
    add_redaction,
    apply_redactions,
    encrypt_pdf,
    export_page,
    generate_key,
    get_encryption_info,
    license_status,
    merge_pdfs,
    ocr_image,
    ocr_pdf_page,
    open_info,
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
    "generate_key",
    "verify_key",
    "license_status",
    "activate_license",
    "encrypt_pdf",
    "remove_password",
    "get_encryption_info",
]
