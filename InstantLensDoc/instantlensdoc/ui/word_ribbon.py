"""Word-Ribbon-Gruppen: lokale Befehle vs. bewusst deaktivierte Cloud/Online-Features."""

from __future__ import annotations

# (aid, label) | (aid, label, "menu", items) | (aid, label, "off", reason)

OFF_3D = "3D-Modelle sind nicht lokal verfügbar."
OFF_SMARTART = "SmartArt ist nicht lokal verfügbar."
OFF_WORDART = "WordArt ist nicht lokal verfügbar."
OFF_VIDEO = "Onlinevideo braucht eine Cloud-Verbindung und ist hier nicht verfügbar."
OFF_ADDINS = "Add-Ins und Office-Store sind nicht lokal verfügbar."
OFF_SHARE = "Freigabe über SharePoint/Cloud ist nicht lokal verfügbar."
OFF_IMMERSIVE = "Immersiver Reader / Fokus ist in dieser Version nicht enthalten."
OFF_RESEARCHER = "Researcher braucht Online-Quellen und ist nicht lokal verfügbar."
OFF_MACROS = "Makros (VBA) sind nicht lokal verfügbar."
OFF_COPILOT = "Copilot ist nicht lokal verfügbar."
OFF_TTS = "Vorlesen ist in dieser Version nicht enthalten (kein TTS)."
OFF_THESAURUS = "Thesaurus ist nicht lokal verfügbar."
OFF_TRANSLATE = "Übersetzung braucht eine Cloud-Verbindung und ist hier nicht verfügbar."
OFF_SCREENSHOT = "Bildschirmfoto ist in dieser Version nicht enthalten."
OFF_ICONS = "Office-Icons sind nicht lokal verfügbar."
OFF_CHART = "Excel-Diagramme sind nicht lokal verfügbar."
OFF_ONLINE_PIC = "Onlinebilder brauchen eine Cloud-Verbindung und sind hier nicht verfügbar."
OFF_RULES = "Seriendruck-Regeln (If/Then) sind in dieser Version nicht enthalten."

DISABLED_REASONS: dict[str, str] = {
    "smartart": OFF_SMARTART,
    "wordart": OFF_WORDART,
    "online_video": OFF_VIDEO,
    "models_3d": OFF_3D,
    "addins": OFF_ADDINS,
    "sharepoint": OFF_SHARE,
    "cloud_share": OFF_SHARE,
    "immersive_reader": OFF_IMMERSIVE,
    "focus_mode": OFF_IMMERSIVE,
    "researcher": OFF_RESEARCHER,
    "macros": OFF_MACROS,
    "copilot": OFF_COPILOT,
    "read_aloud": OFF_TTS,
    "thesaurus": OFF_THESAURUS,
    "translate": OFF_TRANSLATE,
    "screenshot": OFF_SCREENSHOT,
    "icons": OFF_ICONS,
    "insert_chart": OFF_CHART,
    "online_pictures": OFF_ONLINE_PIC,
    "mail_merge_rules": OFF_RULES,
}

WORD_TAB_GROUPS: dict[str, tuple[tuple[str, tuple], ...]] = {
    "Start": (
        (
            "Schriftart",
            (
                ("bold", "Fett"),
                ("italic", "Kursiv"),
                ("underline", "Unterstrichen"),
                ("strike", "Durchgestrichen"),
                ("font", "Schriftart"),
                ("font_size", "Schriftgröße"),
                ("grow_font", "A+"),
                ("shrink_font", "A−"),
                ("subscript", "Tiefgestellt"),
                ("superscript", "Hochgestellt"),
                ("font_color", "Schriftfarbe"),
                ("highlight", "Texthervorhebung"),
                ("highlight_color", "Hintergrundfarbe"),
                ("clear_formatting", "Format löschen"),
                ("toggle_case", "Groß-/Kleinschreibung"),
            ),
        ),
        (
            "Zwischenablage",
            (
                ("paste", "Einfügen"),
                ("cut", "Ausschneiden"),
                ("copy", "Kopieren"),
                ("format_painter", "Format übertragen"),
                ("undo", "↶ Rückgängig"),
                ("redo", "↷ Wiederholen"),
            ),
        ),
        (
            "Absatz",
            (
                ("bullet_list", "Aufzählung"),
                ("numbered_list", "Nummerierung"),
                ("outdent", "Einzug −"),
                ("indent", "Einzug +"),
                ("align_left", "Links"),
                ("align_center", "Zentriert"),
                ("align_right", "Rechts"),
                ("align_justify", "Blocksatz"),
                ("line_spacing_15", "Zeilenabstand"),
                ("paragraph", "Absatz…"),
            ),
        ),
        (
            "Formatvorlagen",
            (("styles_pane", "Formatvorlagen"),),
        ),
        (
            "Bearbeiten",
            (
                ("find_replace", "Suchen"),
                ("replace", "Ersetzen"),
                ("goto", "Gehe zu"),
                ("select_all", "Markieren"),
                ("show_special_chars", "¶"),
                ("spellcheck", "Rechtschreibung"),
            ),
        ),
    ),
    "Einfügen": (
        (
            "Seiten",
            (
                ("insert_cover_page", "Deckblatt"),
                ("insert_blank_page", "Leere Seite"),
                ("insert_break", "Seitenumbruch"),
                ("section_break", "Abschnittsumbruch"),
            ),
        ),
        (
            "Tabellen",
            (("insert_table", "Tabelle"),),
        ),
        (
            "Illustrationen",
            (
                ("insert_picture", "Bilder"),
                ("insert_shape", "Formen"),
                ("online_pictures", "Onlinebilder", "off", OFF_ONLINE_PIC),
                ("models_3d", "3D-Modelle", "off", OFF_3D),
                ("smartart", "SmartArt", "off", OFF_SMARTART),
                ("insert_chart", "Diagramm", "off", OFF_CHART),
                ("screenshot", "Bildschirmfoto", "off", OFF_SCREENSHOT),
                ("icons", "Icons", "off", OFF_ICONS),
                ("online_video", "Onlinevideo", "off", OFF_VIDEO),
            ),
        ),
        (
            "Links",
            (
                ("insert_hyperlink", "Link"),
                ("insert_bookmark", "Textmarke"),
                ("insert_cross_ref", "Querverweis"),
            ),
        ),
        (
            "Kommentare",
            (("doc_comments", "Kommentar"),),
        ),
        (
            "Rahmen",
            (
                ("dtp_text_frame", "Textrahmen"),
                ("dtp_image", "Bild…"),
                ("dtp_graphic", "Grafik"),
            ),
        ),
        (
            "Kopf-/Fußzeile",
            (
                ("insert_header", "Kopfzeile"),
                ("insert_footer", "Fußzeile"),
                ("header_footer", "Kopf-/Fußzeile"),
                ("insert_page_number", "Seitenzahl"),
            ),
        ),
        (
            "Text",
            (
                ("insert_cover_page", "Deckblatt"),
                ("insert_text_box", "Textfeld"),
                ("insert_snippet", "Schnellbausteine"),
                ("insert_date", "Datum/Uhrzeit"),
                ("insert_equation", "Gleichung"),
                ("insert_signature", "Signaturzeile"),
                ("insert_symbol", "Symbol"),
                ("drop_cap", "Initial"),
                ("field_token", "Ersatzzeichen"),
                ("wordart", "WordArt", "off", OFF_WORDART),
                ("addins", "Add-Ins", "off", OFF_ADDINS),
            ),
        ),
    ),
    "Verweise": (
        (
            "Inhaltsverzeichnis",
            (
                ("auto_toc", "Inhaltsverzeichnis"),
                ("auto_toc_update", "Aktualisieren"),
            ),
        ),
        (
            "Fußnoten",
            (
                ("insert_footnote", "Fußnote"),
                ("insert_endnote", "Endnote"),
            ),
        ),
        (
            "Beschriftungen",
            (
                ("insert_caption", "Beschriftung"),
                ("auto_lof", "Abbildungsverzeichnis"),
                ("insert_cross_ref", "Querverweis"),
            ),
        ),
        (
            "Index",
            (("auto_index", "Index"),),
        ),
        (
            "Zitate",
            (
                ("insert_citation", "Zitat"),
                ("bibliography", "Literaturverzeichnis"),
                ("researcher", "Researcher", "off", OFF_RESEARCHER),
            ),
        ),
        (
            "Index markieren",
            (("mark_index", "Eintrag markieren"),),
        ),
    ),
    "Sendungen": (
        (
            "Erstellen",
            (
                ("mail_merge", "Seriendruck…"),
                ("envelopes", "Umschläge"),
                ("labels", "Etiketten"),
            ),
        ),
        (
            "Felder schreiben und einfügen",
            (
                ("mail_merge_data", "Datenquelle…"),
                ("mail_merge_recipients", "Empfängerliste"),
                ("mail_merge_field", "Feld einfügen"),
                ("mail_merge_address", "Adressblock"),
                ("mail_merge_greeting", "Grußzeile"),
                ("mail_merge_highlight", "Felder hervorheben"),
                ("mail_merge_rules", "Regeln", "off", OFF_RULES),
            ),
        ),
        (
            "Vorschau",
            (("mail_merge_preview", "Vorschau"),),
        ),
        (
            "Fertig stellen",
            (
                ("mail_merge_finish", "Zusammenführen"),
                ("cloud_share", "Freigabe", "off", OFF_SHARE),
                ("sharepoint", "SharePoint", "off", OFF_SHARE),
            ),
        ),
    ),
    "Überprüfen": (
        (
            "Dokumentprüfung",
            (
                ("spellcheck", "Rechtschreibung"),
                ("thesaurus", "Thesaurus", "off", OFF_THESAURUS),
                ("word_count", "Wörter zählen"),
                ("translate", "Übersetzen", "off", OFF_TRANSLATE),
                ("read_aloud", "Vorlesen", "off", OFF_TTS),
            ),
        ),
        (
            "Sprache",
            (("hyphenate", "Silbentrennung"),),
        ),
        (
            "Kommentare",
            (("doc_comments", "Kommentare"),),
        ),
        (
            "Nachverfolgung",
            (
                ("review_mode", "Änderungen"),
                ("review_accept", "Annehmen"),
                ("review_reject", "Ablehnen"),
                ("compare_pdfs", "Vergleichen"),
            ),
        ),
        (
            "Schützen",
            (("write_protect", "Schreibschutz"),),
        ),
        (
            "Nicht lokal",
            (
                ("copilot", "Copilot", "off", OFF_COPILOT),
                ("macros", "Makros", "off", OFF_MACROS),
                ("immersive_reader", "Fokus", "off", OFF_IMMERSIVE),
            ),
        ),
    ),
    "Ansicht": (
            (
                "Ansichten",
                (
                    ("chrome_klassisch", "Klassisch"),
                    ("chrome_ribbon", "Ribbon"),
                    ("chrome_kombiniert", "Kombiniert"),
                    ("view_print", "Seitenlayout"),
                    ("view_draft", "Entwurf"),
                    ("view_web", "Weblayout"),
                    ("view_outline", "Gliederung"),
                    ("focus_mode", "Fokus", "off", OFF_IMMERSIVE),
                ),
            ),
        (
            "Anzeigen",
            (
                ("toggle_rulers", "Lineal"),
                ("toggle_grid", "Gitternetzlinien"),
                ("toggle_navigation", "Navigation"),
                ("toggle_minimap", "Minimap"),
                ("show_special_chars", "¶"),
                ("dtp_layout", "DTP-Werkzeuge"),
                ("dtp_grid", "Raster"),
                ("width_marks", "Breitenmarken"),
                ("print_marks", "Druckmarken"),
                ("header_footer_marks", "Kopf-/Fußzeilen-Marken"),
                ("layout_marks", "Layout-Marken…"),
            ),
        ),
        (
            "Zoom",
            (
                ("zoom_100", "100 %"),
                ("zoom_one_page", "Eine Seite"),
                ("zoom_page_width", "Seitenbreite"),
                ("zoom_multi", "Mehrere Seiten"),
            ),
        ),
        (
            "Fenster",
            (
                ("doc_split", "Teilen"),
                ("detach_window", "Neues Fenster"),
            ),
        ),
        (
            "Stift",
            (
                ("ink_input", "Stifteingabe"),
                ("ink_pen_ballpoint", "Kugelschreiber"),
                ("ink_pen_felt", "Filzstift"),
                ("ink_pen_highlighter", "Textmarker"),
                ("ink_brush", "Pinsel"),
                ("ink_color", "Tintenfarbe"),
                ("ink_width", "Tintenstärke"),
                ("ink_fill_none", "Keine Füllung"),
                ("ink_fill_closed", "Strich füllen"),
                ("ink_fill_flood", "Loop-Füllung"),
                ("recognize_handwriting", "Handschrift erkennen"),
                ("right_toolbox", "Rechter Werkzeugkasten"),
                ("stamp_place", "Stempel"),
                ("stamp_frame", "Stempelrahmen"),
                ("stamp_color", "Stempelfarbe"),
                ("stamp_text_only", "Stempel nur Text"),
                ("stamp_shadow", "Stempelschatten"),
                ("stamp_outline", "Stempelkontur"),
                ("stamp_edit", "Stempel bearbeiten"),
            ),
        ),
    ),
}


def disabled_reason(action_id: str) -> str | None:
    return DISABLED_REASONS.get(str(action_id or ""))


# Eine Ansicht: nie ausblenden, nur ausgrauen — deutsche Gründe.
REASON_FONT = (
    "Schriftänderung erst nach OCR (Word-Suite) oder in txt/doc/docx/odt/md/csv/xlsx/DTP-Textrahmen verfügbar"
)
REASON_FONT_PDF = "Schriftänderung erst nach OCR (Word-Suite) verfügbar"
REASON_PAGE = "Seitenränder und Seitenlayout brauchen eine geöffnete Seite"
REASON_PDF = "Nur bei angezeigter PDF-Seite verfügbar"
REASON_MAIL = "Seriendruck nur bei Textdokument (txt, doc, docx, odt, md, csv, xlsx)"
REASON_TABLE = "Tabellenwerkzeuge nur in einer Tabelle"
REASON_ARRANGE = "Anordnen nur bei ausgewähltem DTP-Rahmen"
REASON_RICH = "Nur in txt, doc, docx, odt, md, csv, xlsx, DTP-Textrahmen oder nach OCR verfügbar"
REASON_WRITE_PROTECT = "Dokument ist schreibgeschützt"

FONT_ACTION_IDS = frozenset(
    {
        "bold",
        "italic",
        "underline",
        "strike",
        "font",
        "font_size",
        "grow_font",
        "shrink_font",
        "subscript",
        "superscript",
        "font_color",
        "highlight",
        "highlight_color",
        "clear_formatting",
        "toggle_case",
        "styles_pane",
        "style_normal",
        "style_h1",
        "style_h2",
        "style_h3",
        "style_quote",
        "style_title",
        "style_list",
        "format_painter",
        "dtp_font",
    }
)
PAGE_ACTION_IDS = frozenset(
    {
        "page_layout",
        "page_margins",
        "page_margins_normal",
        "page_margins_narrow",
        "page_margins_wide",
        "page_margins_custom",
        "page_orientation",
        "page_portrait",
        "page_landscape",
        "page_size",
        "page_size_a4",
        "page_size_letter",
        "page_size_legal",
        "page_columns",
        "page_columns_1",
        "page_columns_2",
        "page_columns_3",
        "page_breaks",
        "insert_break",
        "section_break",
        "line_numbers",
        "header_footer",
        "insert_header",
        "insert_footer",
        "insert_page_number",
        "insert_cover_page",
        "insert_blank_page",
        "view_print",
        "zoom_100",
        "zoom_one_page",
        "zoom_page_width",
        "zoom_multi",
    }
)
MAIL_ACTION_IDS = frozenset(
    {
        "mail_merge",
        "mail_merge_data",
        "mail_merge_field",
        "mail_merge_preview",
        "mail_merge_finish",
        "mail_merge_recipients",
        "mail_merge_address",
        "mail_merge_greeting",
        "mail_merge_highlight",
        "envelopes",
        "labels",
    }
)
PDF_ACTION_IDS = frozenset(
    {
        "book_layout",
        "page_by_page",
        "continuous_scroll",
    }
)
PDF_OPEN_ACTION_IDS = frozenset(
    {
        "preflight",
        "apply_bleed",
        "export_pdfx",
    }
)
ALWAYS_ACTION_IDS = frozenset(
    {
        "open",
        "scan_import",
        "devices_discover",
        "devices_printers",
        "devices_refresh",
        "toggle_ribbon",
        "toggle_doc_tabs",
        "settings",
        "chrome_klassisch",
        "chrome_ribbon",
        "chrome_kombiniert",
        "print",
        "dtp_layout",
        "write_protect",
        "doc_info",
        "copy",
        "save",
        "save_as",
    }
)
INK_ACTION_IDS = frozenset(
    {
        "ink_input",
        "ink_pen_ballpoint",
        "ink_pen_felt",
        "ink_pen_highlighter",
        "ink_brush",
        "ink_color",
        "ink_width",
        "ink_fill_none",
        "ink_fill_closed",
        "ink_fill_flood",
        "recognize_handwriting",
        "stamp_place",
        "stamp_frame",
        "stamp_color",
        "stamp_text_only",
        "stamp_shadow",
        "stamp_outline",
        "stamp_edit",
    }
)
VIEW_ACTION_IDS = frozenset(
    {
        "view_print",
        "view_draft",
        "view_web",
        "view_outline",
        "toggle_rulers",
        "toggle_grid",
        "toggle_navigation",
        "toggle_minimap",
        "zoom_100",
        "zoom_one_page",
        "zoom_page_width",
        "zoom_multi",
        "book_layout",
        "page_by_page",
        "continuous_scroll",
        "doc_split",
        "detach_window",
        "width_marks",
        "print_marks",
        "header_footer_marks",
        "layout_marks",
        "dtp_grid",
        "select_all",
        "show_special_chars",
        "word_count",
        "find_replace",
        "right_toolbox",
    }
)
PROTECT_ALLOWED_ACTION_IDS = ALWAYS_ACTION_IDS | VIEW_ACTION_IDS
TABLE_ACTION_IDS = frozenset(
    {
        "table_add_row",
        "table_add_col",
        "table_del_row",
        "table_del_col",
        "table_merge",
        "table_split",
        "table_borders",
        "table_header_row",
        "table_align_left",
        "table_align_center",
        "table_align_right",
    }
)
ARRANGE_ACTION_IDS = frozenset({"bring_forward", "send_backward"})
RICH_TEXT_ACTION_IDS = frozenset(
    {
        "export_epub",
        "export_pptx",
        "insert_hyperlink",
        "insert_shape",
        "insert_snippet",
        "insert_table",
        "find_replace",
        "replace",
        "goto",
        "spellcheck",
        "auto_toc",
        "auto_toc_update",
        "auto_lof",
        "auto_index",
        "field_token",
        "indent",
        "outdent",
        "bullet_list",
        "numbered_list",
        "paragraph",
        "align_left",
        "align_center",
        "align_right",
        "align_justify",
        "line_spacing_15",
        "insert_special_chars",
        "insert_nbsp",
        "insert_shy",
        "hyphenate",
        "drop_cap",
        "insert_footnote",
        "insert_endnote",
        "insert_caption",
        "insert_citation",
        "bibliography",
        "mark_index",
        "insert_bookmark",
        "insert_cross_ref",
        "insert_text_box",
        "insert_date",
        "insert_equation",
        "insert_signature",
        "insert_symbol",
        "select_all",
        "show_special_chars",
        "word_count",
        "review_mode",
        "review_accept",
        "review_reject",
        "doc_comments",
        "autocorrect_toggle",
    }
)
