"""Absatz / Seitenlayout — Word-Suite, bestehende menuAbsatz/menuSeitenlayout."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["ILD_SMOKE_QT"] = "1"
os.environ.setdefault("ILD_SKIP_DEPS_CHECK", "1")
os.environ.setdefault("ILD_NO_SESSION", "1")
os.environ.setdefault("ILD_NO_SPLASH", "1")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

sys.path.insert(0, str(ROOT / "tests"))
from menu_smoke_lib import (  # noqa: E402
    build_fixtures,
    create_main_window,
    install_headless_env,
    install_qt_hooks,
    inventory_window,
    load_state,
    pump,
)

from PySide6.QtGui import QTextCursor  # noqa: E402
from PySide6.QtWidgets import QDialog  # noqa: E402

_APP = None
_WIN = None
_FIXTURES = None
_TD = None
_RESTORE = None
_HOOKS: list = []


REQUIRED_TOP_MENUS = ("Absatz", "Seitenlayout")
FORBIDDEN_TOP_MENUS = ("Ausrichtung", "Aufzählungszeichen")
REQUIRED_ABSATZ = (
    "Absatz…",
    "Absatz links",
    "Absatz zentriert",
    "Absatz rechts",
    "Absatz Blocksatz",
    "Aufzählungszeichen",
    "Nummerierung",
    "Zeilenabstand 1,0",
    "Zeilenabstand 1,15 (Standard)",
    "Zeilenabstand 1,5",
    "Zeilenabstand 2,0",
    "Mit nächstem Absatz zusammenhalten",
    "Absatzkontrolle (Witwen/Waisen)",
    "Aufzählungszeichen ändern…",
    "Nummerierung neu beginnen",
    "Listenebene erhöhen",
    "Listenebene verringern",
    "Zelle oben",
    "Zelle mittig",
    "Zelle unten",
    "Ersatzzeichen…",
)
REQUIRED_SEITEN = (
    "Seitenlayout…",
    "A4",
    "Legal",
    "Hochformat",
    "Querformat",
    "1 Spalte",
    "2 Spalten",
    "3 Spalten",
    "Abschnittsumbruch einfügen",
    "Kopf-/Fußzeile…",
)


def setup_module() -> None:
    global _APP, _WIN, _FIXTURES, _TD, _RESTORE
    install_headless_env()
    _TD = tempfile.TemporaryDirectory(prefix="ild-para-2659-")
    _FIXTURES = build_fixtures(Path(_TD.name))
    _RESTORE = install_qt_hooks(_HOOKS)
    _APP, _WIN = create_main_window()


def teardown_module() -> None:
    global _WIN, _TD, _RESTORE
    try:
        if _WIN is not None:
            _WIN.close()
    except Exception:
        pass
    if _RESTORE:
        _RESTORE()
    if _TD is not None:
        _TD.cleanup()


def _menu_paths(win) -> set[str]:
    rows = inventory_window(win)
    return {str(r.get("path") or "") for r in rows if r.get("kind") == "menu"}


def _menu_texts(win) -> set[str]:
    rows = inventory_window(win)
    return {str(r.get("text") or "").replace("&", "") for r in rows if r.get("kind") == "menu"}


def _top_titles(paths: set[str]) -> set[str]:
    out = set()
    for p in paths:
        out.add(p.split("▸")[0].strip() if "▸" in p else p)
    return out


def test_word_suite_menus_present() -> None:
    paths = _menu_paths(_WIN)
    texts = _menu_texts(_WIN)
    tops = _top_titles(paths)
    missing_top = [m for m in REQUIRED_TOP_MENUS if m not in tops]
    assert missing_top == [], f"Top-Menüs fehlen: {missing_top}"
    extra = [m for m in FORBIDDEN_TOP_MENUS if m in tops]
    assert extra == [], f"Doppelte Top-Menüs: {extra}"
    absatz = _WIN._absatz_menu
    seiten = _WIN._seitenlayout_menu
    assert absatz.objectName() == "menuAbsatz"
    assert seiten.objectName() == "menuSeitenlayout"
    missing_a = [lab for lab in REQUIRED_ABSATZ if lab not in texts]
    missing_s = [lab for lab in REQUIRED_SEITEN if lab not in texts]
    assert missing_a == [], f"Absatz-Einträge fehlen: {missing_a}"
    assert missing_s == [], f"Seitenlayout-Einträge fehlen: {missing_s}"


def test_paragraph_dialog_opens_and_mutates() -> None:
    from instantlensdoc.ui.paragraph_dialog import ParagraphDialog, ParagraphFormatSpec

    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.1)
    ed = _WIN.editor
    ed.setPlainText("Eins.\n\nZwei.")
    cur = ed.textCursor()
    cur.setPosition(0)
    ed.setTextCursor(cur)
    spec = ParagraphFormatSpec(
        space_before_pt=12.0,
        space_after_pt=18.0,
        first_line_indent_mm=10.0,
        left_indent_mm=8.0,
        right_indent_mm=6.0,
        line_spacing=1.5,
        line_spacing_mode="multiple",
        keep_with_next=True,
        widow_orphan=True,
    )
    dlg = ParagraphDialog(spec, _WIN)
    assert dlg.objectName() == "paragraphFormatDialog"
    assert dlg.windowTitle() == "Absatz"
    got = dlg.result_spec()
    assert got.space_before_pt == 12.0
    assert got.keep_with_next is True
    dlg.close()
    assert ed.apply_paragraph_spec(spec)
    fmt = ed.textCursor().blockFormat()
    assert fmt.topMargin() >= 11.0
    assert fmt.bottomMargin() >= 17.0
    assert fmt.leftMargin() > 0
    assert fmt.textIndent() > 0
    keep = ed.current_paragraph_spec()
    assert keep.keep_with_next is True
    assert keep.space_before_pt >= 11.0


def test_no_selection_paragraph_applies_whole_document() -> None:
    from instantlensdoc.ui.editor import TextEditor

    ed = TextEditor()
    ed.setPlainText("Alpha-Absatz.\n\nBeta-Absatz.")
    cur = ed.textCursor()
    cur.setPosition(0)
    ed.setTextCursor(cur)
    assert not ed.textCursor().hasSelection()
    assert ed.set_paragraph_alignment("center")
    block = ed.document().firstBlock()
    aligns = []
    while block.isValid():
        if (block.text() or "").strip():
            al = int(block.blockFormat().alignment())
            aligns.append(al)
        block = block.next()
    from PySide6.QtCore import Qt

    assert aligns and all(a & int(Qt.AlignHCenter) for a in aligns)
    ed.deleteLater()


def test_alignment_and_table_cell() -> None:
    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.1)
    ed = _WIN.editor
    ed.setPlainText("Zelle-Test")
    assert ed.set_paragraph_alignment("justify")
    assert ed.current_block_alignment() == "justify"
    ok = ed.insert_rich_table(2, 2)
    table = ed.current_table()
    if ok and table is not None:
        assert ed.set_table_cell_vertical_alignment("middle")
        assert ed.current_cell_vertical_alignment() == "middle"
    else:
        # QPlainTextDocumentLayout trägt keine QTextTable — Slot bleibt no-op.
        assert ed.set_table_cell_vertical_alignment("middle") is False


def test_lists_nested_glyph_restart() -> None:
    from instantlensdoc.ui.editor import TextEditor
    from instantlensdoc.ui.rich_lists import parse_list_prefix

    ed = TextEditor()
    ed.setPlainText("Punkt A\nPunkt B")
    cur = ed.textCursor()
    cur.select(QTextCursor.Document)
    ed.setTextCursor(cur)
    assert ed.toggle_list(ordered=False)
    plain = ed.toPlainText()
    assert "• " in plain
    assert "\x0c" not in plain
    assert "¶" not in plain
    ed.toggle_list(ordered=True)
    assert "1. " in ed.toPlainText()
    ed.restart_list_numbering()
    assert ed.toPlainText().lstrip().startswith("1. ")
    ed.toggle_list(ordered=False)
    assert ed.set_list_glyph("◆")
    assert "◆ " in ed.toPlainText()
    cur = ed.textCursor()
    cur.setPosition(0)
    ed.setTextCursor(cur)
    ed.adjust_list_indent(+1)
    info = parse_list_prefix(ed.textCursor().block().text())
    assert info is not None
    ed.deleteLater()


def test_ocr_html_bullets_without_control_glyphs() -> None:
    from instantlensdoc.ui.editor import TextEditor
    from instantlensdoc.core.ocr_word_suite import WordSuiteBlock, blocks_to_word_suite_html

    html = blocks_to_word_suite_html(
        [
            WordSuiteBlock(reading_order=0, text="\x0c Erster Punkt"),
            WordSuiteBlock(reading_order=1, text="¶ Zweiter Punkt"),
            WordSuiteBlock(reading_order=2, text="- Dritter Punkt"),
        ],
        title="OCR",
    )
    assert "\x0c" not in html
    ed = TextEditor()
    ed.set_rich_html(html)
    plain = ed.toPlainText()
    assert "\x0c" not in plain
    assert "¶" not in plain
    assert "• " in plain
    assert "Erster Punkt" in plain
    ed.deleteLater()


def test_page_layout_picker_and_section_break() -> None:
    load_state(_WIN, _APP, "docx", _FIXTURES)
    pump(_APP, 0.15)
    assert _WIN._editor_document_active()
    _WIN._apply_page_size_preset("Letter")
    lay = _WIN.editor.page_layout()
    assert lay is not None
    assert "Letter" in lay.preset or abs(lay.width_pt - 612.0) < 1.0
    _WIN._apply_page_orientation("landscape")
    assert _WIN.editor.page_layout().orientation == "landscape"
    _WIN._apply_page_columns(2)
    assert int(_WIN.editor.page_layout().columns) == 2
    before = _WIN.editor.document().blockCount()
    _WIN._insert_section_break()
    assert _WIN.editor.document().blockCount() >= before
    from instantlensdoc.ui.page_layout_dialog import PageLayoutDialog

    dlg = PageLayoutDialog(_WIN.editor.page_layout(), _WIN, rich_document=True)
    assert dlg.objectName() == "pageLayoutDialog"
    assert dlg.columns_spin.maximum() == 3
    assert dlg.header_spin.objectName() == "pageLayoutHeaderDistance"
    assert dlg.footer_spin.objectName() == "pageLayoutFooterDistance"
    dlg.close()
    pane = _WIN.editor_pane
    assert "align_justify" in pane._tool_buttons
    assert "bullet_list" in pane._tool_buttons
    assert getattr(pane, "layout_picker", None) is not None


def test_header_footer_and_field_token_dialogs() -> None:
    from instantlensdoc.ui.field_token_dialog import FieldTokenDialog
    from instantlensdoc.ui.header_footer_dialog import HeaderFooterDialog
    from instantlensdoc.ui.list_glyph_dialog import ListGlyphDialog

    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.1)
    hf = HeaderFooterDialog("Kopf", "Fuß", _WIN)
    assert hf.objectName() == "headerFooterDialog"
    assert hf.result_header_footer() == ("Kopf", "Fuß")
    hf.close()
    _WIN.editor.set_document_header_footer("Kopfzeile", "Fußzeile")
    assert _WIN.editor.document_header() == "Kopfzeile"
    assert "¶" not in _WIN.editor.toPlainText()
    ft = FieldTokenDialog(_WIN)
    assert ft.objectName() == "fieldTokenDialog"
    ident, display = ft.result_field()
    assert ident
    assert "\x0c" not in display and "¶" not in display
    assert ft.table.objectName() == "fieldTokenTable"
    assert ft.format_combo.objectName() == "fieldTokenFormat"
    assert ft.target_combo.objectName() == "fieldTokenTarget"
    assert ft.add_btn.objectName() == "fieldTokenAdd"
    names = {ft.field_combo.itemData(i) for i in range(ft.field_combo.count())}
    for need in ("date", "time", "page", "total", "filename", "author"):
        assert need in names, need
    ft.close()
    glyph = ListGlyphDialog("•", _WIN)
    assert glyph.objectName() == "listGlyphDialog"
    assert glyph.result_glyph() == "•"
    glyph.close()
    assert isinstance(QDialog, type)


def test_field_tokens_insert_header_footer_and_resolve() -> None:
    from instantlensdoc.core.documents import Document, DocKind, save_document, open_document
    from instantlensdoc.core.field_tokens import (
        make_resolve_context,
        read_docx_custom_field_tokens,
        resolve_field_tokens_in_text,
        load_field_tokens_sidecar,
    )

    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.1)
    ed = _WIN.editor
    ed.setPlainText("")
    assert ed.insert_field_token("") is True
    assert "{date}" in ed.toPlainText()
    assert ed.insert_field_token("filename", target="body") is True
    assert "{filename}" in ed.toPlainText()
    assert ed.insert_field_token("author", target="header") is True
    assert "{author}" in ed.document_header()
    before_footer = ed.document_footer()
    assert ed.insert_field_token("total", target="footer") is True
    assert "{total}" in ed.document_footer()
    assert ed.document_footer() != before_footer or "{total}" in ed.document_footer()
    ed.set_field_token_ersatz("kunde", "ACME")
    ed.insert_field_token("kunde", display="{kunde}")
    _WIN._sync_editor_rich_meta()
    specs = ed.field_token_specs()
    assert "kunde" in specs
    ctx = make_resolve_context(
        page=3,
        page_count=9,
        filename="vertrag.docx",
        author="Andreas",
        specs=specs,
    )
    resolved = resolve_field_tokens_in_text(
        "{date} {time} {page} {total} {filename} {author} {kunde}",
        ctx,
    )
    assert "3" in resolved and "9" in resolved
    assert "vertrag.docx" in resolved
    assert "Andreas" in resolved
    assert "ACME" in resolved
    assert "{date}" not in resolved
    html = ed.resolved_field_preview_html(ctx)
    assert "vertrag.docx" in html or "Andreas" in html or "ACME" in html
    tmp = Path(_TD.name) / "felder.docx"
    _WIN.doc.kind = DocKind.DOCX
    _WIN.doc.path = tmp
    _WIN._sync_editor_rich_meta()
    save_document(_WIN.doc, tmp)
    side = load_field_tokens_sidecar(tmp)
    assert "kunde" in side
    custom = read_docx_custom_field_tokens(tmp)
    assert "kunde" in custom
    opened = open_document(tmp)
    ft = (opened.meta or {}).get("field_tokens") or {}
    assert "kunde" in ft
    assert "{author}" in str((opened.meta or {}).get("header") or "")


def test_editor_only_new_menus_disabled_on_pdf() -> None:
    load_state(_WIN, _APP, "pdf20", _FIXTURES)
    pump(_APP, 0.2)
    _WIN._sync_menu_enablement()
    _WIN._sync_editor_only_actions()
    rows = inventory_window(_WIN)
    still_on = [
        r["path"]
        for r in rows
        if r.get("kind") == "menu"
        and r.get("enabled")
        and str(r.get("path") or "").startswith(("Absatz ▸", "Seitenlayout ▸"))
    ]
    assert not still_on, "Word-Suite-Menüs bei PDF aktiv: " + "; ".join(still_on[:8])


def test_rich_lists_stdlib_no_control_glyphs() -> None:
    from instantlensdoc.ui.rich_lists import (
        normalize_ocr_line,
        parse_list_prefix,
        prefix_for,
        sanitize_rich_html,
    )

    assert "¶" not in normalize_ocr_line("¶ Punkt")
    assert "\x0c" not in normalize_ocr_line("\x0c Punkt")
    assert normalize_ocr_line("\x0c Punkt").startswith("• ")
    html = sanitize_rich_html("<ul><li>A</li></ul>")
    assert "• " in html
    assert "\x0c" not in html
    info = parse_list_prefix(prefix_for(ordered=False) + "Text")
    assert info is not None and not info.ordered


def test_chrome_can_place_start_layout_insert_qactions() -> None:
    from instantlensdoc.ui.chrome_actions import CHROME_ACTION_OBJECT_NAMES, CHROME_TABS

    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.1)
    tabs = _WIN.chrome_tab_qactions()
    assert set(tabs) == set(CHROME_TABS)
    para = tabs["Start"]["paragraph"]
    assert para.objectName() == "actEditParagraph"
    assert _WIN.ribbon_bar.qaction("paragraph") is para
    hf = tabs["Seitenlayout"]["header_footer"]
    assert hf.objectName() == "actHeaderFooter"
    assert tabs["Einfügen"]["header_footer"] is hf
    ft = tabs["Einfügen"]["field_token"]
    assert ft.objectName() == "actFieldToken"
    assert _WIN.ribbon_bar.qaction("field_token") is ft
    layout_alias = _WIN.chrome_tab_qactions("Layout")
    assert layout_alias["page_layout"] is tabs["Seitenlayout"]["page_layout"]
    assert _WIN.ribbon_bar._tab_index.get("Seitenlayout") == _WIN.ribbon_bar._tab_index.get(
        "Layout"
    )
    for aid in (
        "page_columns_2",
        "section_break",
        "line_spacing_115",
        "keep_with_next",
        "page_size_legal",
    ):
        act = _WIN.chrome_qactions().get(aid)
        assert act is not None, aid
        assert act.objectName() == CHROME_ACTION_OBJECT_NAMES[aid]
    ribbons = [
        w
        for w in _WIN.findChildren(type(_WIN.ribbon_bar))
        if w.objectName() == "ildRibbonBar"
    ]
    assert len(ribbons) == 1


def test_chrome_feature_qactions_absatz_align_lists() -> None:
    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.1)
    absatz = _WIN.chrome_feature_qactions("Absatz")
    align = _WIN.chrome_feature_qactions("Ausrichtung")
    listen = _WIN.chrome_feature_qactions("Listen")
    assert absatz["paragraph"].objectName() == "actEditParagraph"
    assert align["align_justify"].objectName() == "actEditAlignJustify"
    assert listen["bullet_list"].objectName() == "actEditBulletList"
    assert _WIN.chrome_feature_qactions("Kopf/Fuß")["header_footer"] is _WIN.chrome_qactions()[
        "header_footer"
    ]
    assert _WIN.chrome_feature_qactions("Ersatzzeichen")["field_token"] is _WIN.chrome_qactions()[
        "field_token"
    ]
    layout = _WIN.chrome_tab_qactions("Seitenlayout")
    assert "align_left" in layout
    assert "bullet_list" in layout
    assert "header_footer" in layout
