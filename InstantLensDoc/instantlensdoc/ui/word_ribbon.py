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
OFF_INK = "Stifteingabe/Ink ist in dieser Word-Leiste nicht verfügbar."
OFF_COPILOT = "Copilot ist nicht lokal verfügbar."
OFF_TTS = "Vorlesen ist in dieser Version nicht enthalten (kein TTS)."

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
    "ink_tools": OFF_INK,
    "copilot": OFF_COPILOT,
    "read_aloud": OFF_TTS,
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
                ("spellcheck", "Rechtschreibung"),
            ),
        ),
    ),
    "Einfügen": (
        (
            "Seiten",
            (
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
                ("models_3d", "3D-Modelle", "off", OFF_3D),
                ("smartart", "SmartArt", "off", OFF_SMARTART),
                ("online_video", "Onlinevideo", "off", OFF_VIDEO),
            ),
        ),
        (
            "Links",
            (
                ("insert_hyperlink", "Link"),
                ("insert_bookmark", "Textmarke"),
            ),
        ),
        (
            "Kommentare",
            (("doc_comments", "Kommentar"),),
        ),
        (
            "Kopf-/Fußzeile",
            (
                ("header_footer", "Kopf-/Fußzeile"),
                ("insert_page_number", "Seitenzahl"),
            ),
        ),
        (
            "Text",
            (
                ("insert_text_box", "Textfeld"),
                ("insert_date", "Datum/Uhrzeit"),
                ("insert_symbol", "Symbol"),
                ("drop_cap", "Initial"),
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
            ),
        ),
        (
            "Index",
            (("auto_index", "Index"),),
        ),
        (
            "Zitate",
            (
                ("bibliography", "Literaturverzeichnis"),
                ("researcher", "Researcher", "off", OFF_RESEARCHER),
            ),
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
                ("mail_merge_field", "Feld einfügen"),
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
                ("word_count", "Wörter zählen"),
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
                ("compare_pdfs", "Vergleichen"),
            ),
        ),
        (
            "Nicht lokal",
            (
                ("ink_tools", "Stifteingabe", "off", OFF_INK),
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
                ("view_print", "Seitenlayout"),
                ("view_draft", "Entwurf"),
                ("view_web", "Weblayout"),
                ("chrome_klassisch", "Klassisch"),
                ("chrome_ribbon", "Ribbon"),
                ("chrome_kombiniert", "Kombiniert"),
                ("focus_mode", "Fokus", "off", OFF_IMMERSIVE),
            ),
        ),
        (
            "Anzeigen",
            (
                ("toggle_rulers", "Lineal"),
                ("toggle_grid", "Gitternetzlinien"),
                ("toggle_navigation", "Navigation"),
            ),
        ),
        (
            "Zoom",
            (
                ("zoom_100", "100 %"),
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
    ),
}


def disabled_reason(action_id: str) -> str | None:
    return DISABLED_REASONS.get(str(action_id or ""))
