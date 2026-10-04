"""
Stabiles Scripting-API für InstantLens Doc (2.6.17).

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
    ild.apply_typography(text="Absatz", tracking=50, leading=1.5)
    ild.hyphenate("Silbentrennung", lang="de")
    ild.apply_drop_cap("Einleitungstext …")
    ild.create_table(3, 3)
    ild.import_table_csv("daten.csv")
    ild.save_document("Hallo", "out.docx")
    ild.ocr_to_word_suite("scan.png")
    ild.import_ildocr("scan.ildocr.txt")
    ild.list_ki_wizards()
    ild.generate_ki_document("anschreiben", fields={"betreff": "Anfrage"})

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
    apply_drop_cap,
    apply_header_footer,
    apply_master_page,
    apply_paragraph_format,
    apply_redactions,
    apply_typography,
    auto_format_pdf,
    auto_format_text,
    create_table,
    encrypt_pdf,
    export_document_fmt,
    export_page,
    export_table,
    find_replace,
    format_table,
    generate_key,
    generate_toc,
    get_encryption_info,
    grid_lines,
    highlight_paragraphs,
    hyphenate,
    import_document,
    import_table_csv,
    import_table_xlsx,
    layout_add_image_frame,
    layout_add_text_frame,
    layout_flow_text,
    layout_flow_text_wrap,
    layout_link_frames,
    layout_list_frames,
    layout_move_frame,
    layout_resize_frame,
    layout_set_text_wrap,
    license_status,
    list_character_styles,
    list_hyphenation_languages,
    list_io_formats,
    list_master_pages,
    list_page_formats,
    list_paragraph_styles,
    list_satzspiegel,
    list_stamps,
    list_style_presets,
    list_system_fonts,
    list_table_styles,
    list_typography_styles,
    merge_pdfs,
    new_layout,
    ocr_image,
    ocr_pdf_page,
    ocr_to_word_suite,
    handoff_ocr_to_word_suite,
    import_ildocr,
    list_ki_wizards,
    generate_ki_document,
    run_ki_wizard,
    list_ui_langs,
    get_ui_lang,
    set_ui_lang,
    tr,
    ocr_handwriting,
    open_info,
    outline_summary,
    page_count,
    remove_password,
    resolve_page_format,
    rotate_page,
    ruler_ticks,
    satzspiegel,
    save_document,
    set_page_format,
    sort_table,
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
    "ocr_to_word_suite",
    "handoff_ocr_to_word_suite",
    "import_ildocr",
    "list_ki_wizards",
    "generate_ki_document",
    "run_ki_wizard",
    "list_ui_langs",
    "get_ui_lang",
    "set_ui_lang",
    "tr",
    "ocr_handwriting",
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
    "apply_typography",
    "apply_drop_cap",
    "list_character_styles",
    "list_typography_styles",
    "hyphenate",
    "list_hyphenation_languages",
    "layout_set_text_wrap",
    "layout_flow_text_wrap",
    "create_table",
    "format_table",
    "sort_table",
    "import_table_csv",
    "import_table_xlsx",
    "export_table",
    "list_table_styles",
    "save_document",
    "export_document_fmt",
    "import_document",
    "list_io_formats",
    "generate_key",
    "verify_key",
    "license_status",
    "activate_license",
    "encrypt_pdf",
    "remove_password",
    "get_encryption_info",
]
