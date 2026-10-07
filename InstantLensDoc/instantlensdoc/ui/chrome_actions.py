"""QActions für Word-Chrome: Start / Seitenlayout / Einfügen.

Kein zweites Ribbon. Der Chrome-Worker (Klassisch/Ribbon/Kombiniert,
Formatvorlagen, Tabellen, Serienbrief) platziert diese IDs auf den
bestehenden Tabs. Ribbon-Tab „Layout“ = Seitenlayout. Pulldown und
Ribbon klicken dieselbe QAction (objectName).
"""

from __future__ import annotations

from typing import Mapping

CHROME_TABS = ("Start", "Seitenlayout", "Einfügen")

CHROME_TAB_ALIASES = {
    "start": "Start",
    "home": "Start",
    "seitenlayout": "Seitenlayout",
    "layout": "Seitenlayout",
    "page_layout": "Seitenlayout",
    "page layout": "Seitenlayout",
    "einfügen": "Einfügen",
    "einfuegen": "Einfügen",
    "insert": "Einfügen",
}

CHROME_FEATURE_ALIASES = {
    "absatz": "Absatz",
    "paragraph": "Absatz",
    "ausrichtung": "Ausrichtung",
    "align": "Ausrichtung",
    "alignment": "Ausrichtung",
    "listen": "Listen",
    "lists": "Listen",
    "aufzählung": "Listen",
    "aufzaehlung": "Listen",
    "seitenlayout": "Seitenlayout",
    "layout": "Seitenlayout",
    "kopf": "Kopf/Fuß",
    "fuß": "Kopf/Fuß",
    "fuss": "Kopf/Fuß",
    "header": "Kopf/Fuß",
    "footer": "Kopf/Fuß",
    "kopf/fuß": "Kopf/Fuß",
    "kopf/fuss": "Kopf/Fuß",
    "ersatzzeichen": "Ersatzzeichen",
    "felder": "Ersatzzeichen",
    "fields": "Ersatzzeichen",
}

# Feature-Gruppen, die dieser Worker liefert — Chrome platziert sie.
CHROME_FEATURE_ACTION_IDS: dict[str, tuple[str, ...]] = {
    "Absatz": (
        "paragraph",
        "line_spacing_10",
        "line_spacing_115",
        "line_spacing_15",
        "line_spacing_20",
        "line_spacing_exact",
        "keep_with_next",
        "widow_orphan",
    ),
    "Ausrichtung": (
        "align_left",
        "align_center",
        "align_right",
        "align_justify",
        "cell_align_top",
        "cell_align_middle",
        "cell_align_bottom",
    ),
    "Listen": (
        "bullet_list",
        "numbered_list",
        "list_glyph",
        "list_restart",
        "list_indent",
        "list_outdent",
    ),
    "Seitenlayout": (
        "page_layout",
        "page_portrait",
        "page_landscape",
        "page_size_a4",
        "page_size_letter",
        "page_size_legal",
        "page_columns_1",
        "page_columns_2",
        "page_columns_3",
        "section_break",
        "page_margins_normal",
        "page_margins_narrow",
        "page_margins_wide",
        "page_margins_custom",
        "line_numbers",
        "hyphenate",
        "bring_forward",
        "send_backward",
        "group_frames",
        "ungroup_frames",
    ),
    "Kopf/Fuß": ("header_footer",),
    "Ersatzzeichen": ("field_token",),
}

CHROME_TAB_ACTION_IDS: dict[str, tuple[str, ...]] = {
    "Start": (
        *CHROME_FEATURE_ACTION_IDS["Absatz"],
        *CHROME_FEATURE_ACTION_IDS["Ausrichtung"],
        *CHROME_FEATURE_ACTION_IDS["Listen"],
    ),
    "Seitenlayout": (
        *CHROME_FEATURE_ACTION_IDS["Seitenlayout"],
        *CHROME_FEATURE_ACTION_IDS["Ausrichtung"][:4],
        *CHROME_FEATURE_ACTION_IDS["Listen"][:2],
        *CHROME_FEATURE_ACTION_IDS["Kopf/Fuß"],
        "paragraph",
        "indent",
        "outdent",
        "insert_break",
    ),
    "Einfügen": (
        *CHROME_FEATURE_ACTION_IDS["Kopf/Fuß"],
        *CHROME_FEATURE_ACTION_IDS["Ersatzzeichen"],
        "insert_break",
        "section_break",
    ),
}

CHROME_ACTION_OBJECT_NAMES: dict[str, str] = {
    "paragraph": "actEditParagraph",
    "align_left": "actEditAlignLeft",
    "align_center": "actEditAlignCenter",
    "align_right": "actEditAlignRight",
    "align_justify": "actEditAlignJustify",
    "bullet_list": "actEditBulletList",
    "numbered_list": "actEditNumberedList",
    "line_spacing_10": "actLineSpacing10",
    "line_spacing_115": "actLineSpacing115",
    "line_spacing_15": "actLineSpacing15",
    "line_spacing_20": "actLineSpacing20",
    "line_spacing_exact": "actLineSpacingExact",
    "keep_with_next": "actKeepWithNext",
    "widow_orphan": "actWidowOrphan",
    "list_glyph": "actListGlyph",
    "list_restart": "actListRestart",
    "list_indent": "actListIndent",
    "list_outdent": "actListOutdent",
    "cell_align_top": "actCellAlignTop",
    "cell_align_middle": "actCellAlignMiddle",
    "cell_align_bottom": "actCellAlignBottom",
    "page_layout": "actPageLayout",
    "page_portrait": "actPageLayoutPortrait",
    "page_landscape": "actPageLayoutLandscape",
    "page_size_a4": "actPageLayoutA4",
    "page_size_letter": "actPageLayoutLetter",
    "page_size_legal": "actPageLayoutLegal",
    "page_columns_1": "actPageLayoutColumns1",
    "page_columns_2": "actPageLayoutColumns2",
    "page_columns_3": "actPageLayoutColumns3",
    "section_break": "actInsertSectionBreak",
    "header_footer": "actHeaderFooter",
    "width_marks": "actEditorWidthMarks",
    "print_marks": "actEditorPrintMarks",
    "header_footer_marks": "actEditorHeaderFooterMarks",
    "layout_marks": "actEditorLayoutMarks",
    "field_token": "actFieldToken",
    "insert_break": "actEditInsertPageBreak",
    "page_margins_normal": "actPageMarginsNormal",
    "page_margins_narrow": "actPageMarginsNarrow",
    "page_margins_wide": "actPageMarginsWide",
    "page_margins_custom": "actPageMarginsCustom",
    "line_numbers": "actLineNumbers",
    "hyphenate": "actHyphenate",
    "indent": "actEditIndent",
    "outdent": "actEditOutdent",
    "bring_forward": "actArrangeBringForward",
    "send_backward": "actArrangeSendBackward",
    "group_frames": "actAnnGroup",
    "ungroup_frames": "actAnnUngroup",
}

CHROME_ACTION_ATTRS: tuple[tuple[str, str], ...] = (
    ("paragraph", "_act_paragraph_dialog"),
    ("align_left", "_act_align_left"),
    ("align_center", "_act_align_center"),
    ("align_right", "_act_align_right"),
    ("align_justify", "_act_align_justify"),
    ("bullet_list", "_act_bullet_list"),
    ("numbered_list", "_act_numbered_list"),
    ("line_spacing_115", "_act_spacing_115"),
    ("line_spacing_15", "_act_spacing_15"),
    ("page_layout", "_page_layout_action"),
    ("field_token", "_field_token_action"),
    ("line_numbers", "_line_numbers_action"),
    ("hyphenate", "_hyphenate_action"),
    ("width_marks", "_width_marks_action"),
    ("print_marks", "_editor_print_marks_action"),
    ("header_footer_marks", "_header_footer_marks_action"),
    ("layout_marks", "_layout_marks_action"),
    ("indent", "_act_indent"),
    ("outdent", "_act_outdent"),
    ("group_frames", "_act_ann_group"),
    ("ungroup_frames", "_act_ann_ungroup"),
)


def normalize_chrome_tab(name: str | None) -> str:
    raw = str(name or "").replace("&", "").strip()
    if not raw:
        return ""
    if raw in CHROME_TAB_ACTION_IDS:
        return raw
    return CHROME_TAB_ALIASES.get(raw.lower(), raw)


def tab_action_ids(tab: str | None) -> tuple[str, ...]:
    name = normalize_chrome_tab(tab)
    return CHROME_TAB_ACTION_IDS.get(name, ())


def pick_tab_qactions(
    mapping: Mapping[str, object] | None,
    tab: str | None,
) -> dict[str, object]:
    src = mapping or {}
    return {aid: src[aid] for aid in tab_action_ids(tab) if aid in src}


def all_tab_qactions(mapping: Mapping[str, object] | None) -> dict[str, dict[str, object]]:
    src = mapping or {}
    return {tab: pick_tab_qactions(src, tab) for tab in CHROME_TABS}


FONT_TOOL_ACTION_IDS: frozenset[str] = frozenset(
    {
        "bold",
        "italic",
        "underline",
        "strike",
        "font",
        "font_color",
        "highlight",
        "highlight_color",
        "clear_formatting",
    }
)

FONT_TOOL_OBJECT_NAMES: frozenset[str] = frozenset(
    {
        "actEditBold",
        "actEditItalic",
        "actEditUnderline",
        "actEditStrike",
        "actEditFont",
        "actEditFontSize",
        "actEditFontColor",
        "actEditHighlight",
        "actEditBackgroundColor",
        "actEditClearFormatting",
    }
)

FONT_TOOL_LABEL_NEEDLES: tuple[str, ...] = (
    "fett",
    "kursiv",
    "unterstrichen",
    "durchgestrichen",
    "schriftart",
    "schriftgröße",
    "schriftfarbe",
    "texthervorhebung",
    "hintergrundfarbe",
    "textmarker",
    "formatierungen löschen",
)

FONT_TOOL_DISABLE_REASON = (
    "Schriftwerkzeuge nach OCR oder in txt/doc/docx/odt/md/csv/xlsx/DTP"
)

EDITOR_ACTION_DISABLE_REASON = "Nur im Text- oder DOCX-Editor verfügbar"


def is_font_tool_id(action_id: str | None) -> bool:
    return str(action_id or "") in FONT_TOOL_ACTION_IDS


def is_font_tool_object_name(name: str | None) -> bool:
    return str(name or "") in FONT_TOOL_OBJECT_NAMES


def is_font_tool_label(label: str | None) -> bool:
    t = (label or "").replace("&", "").strip().lower()
    return bool(t) and any(n in t for n in FONT_TOOL_LABEL_NEEDLES)


def font_tools_allowed(
    *,
    is_editor: bool,
    is_dtp: bool,
    is_pdf: bool,
    has_ocr: bool,
) -> tuple[bool, str]:
    """Schriftwerkzeuge: grauen + Tooltip, nie Menü ausblenden.

    Enabled: txt/doc/docx/odt/md/csv/xlsx-Editor, DTP, oder PDF nach OCR.
    Disabled: PDF ohne OCR (und sonstige Nicht-Text-Tabs).
    """
    if is_dtp or is_editor:
        return True, ""
    if is_pdf and has_ocr:
        return True, ""
    return False, FONT_TOOL_DISABLE_REASON


def normalize_chrome_feature(name: str | None) -> str:
    raw = str(name or "").replace("&", "").strip()
    if not raw:
        return ""
    if raw in CHROME_FEATURE_ACTION_IDS:
        return raw
    return CHROME_FEATURE_ALIASES.get(raw.lower(), raw)


def feature_action_ids(feature: str | None) -> tuple[str, ...]:
    return CHROME_FEATURE_ACTION_IDS.get(normalize_chrome_feature(feature), ())


def pick_feature_qactions(
    mapping: Mapping[str, object] | None,
    feature: str | None,
) -> dict[str, object]:
    src = mapping or {}
    return {aid: src[aid] for aid in feature_action_ids(feature) if aid in src}
