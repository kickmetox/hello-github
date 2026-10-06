"""QActions für Word-Chrome: Start / Seitenlayout / Einfügen.

Kein zweites Ribbon. Der Chrome-Worker platziert diese IDs auf den
bestehenden Tabs (Ribbon-Tab „Layout“ = Seitenlayout). Pulldown und
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

CHROME_TAB_ACTION_IDS: dict[str, tuple[str, ...]] = {
    "Start": (
        "paragraph",
        "align_left",
        "align_center",
        "align_right",
        "align_justify",
        "bullet_list",
        "numbered_list",
        "line_spacing_10",
        "line_spacing_115",
        "line_spacing_15",
        "line_spacing_20",
        "line_spacing_exact",
        "keep_with_next",
        "widow_orphan",
        "list_glyph",
        "list_restart",
        "list_indent",
        "list_outdent",
        "cell_align_top",
        "cell_align_middle",
        "cell_align_bottom",
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
        "header_footer",
    ),
    "Einfügen": (
        "header_footer",
        "field_token",
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
    "field_token": "actFieldToken",
    "insert_break": "actEditInsertPageBreak",
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
