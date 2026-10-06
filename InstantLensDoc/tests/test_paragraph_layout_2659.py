"""Absatz / Seitenlayout / Ausrichtung / Aufzählungszeichen — Word-Suite 2.6.59."""

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


REQUIRED_TOP_MENUS = ("Absatz", "Seitenlayout", "Ausrichtung", "Aufzählungszeichen")
REQUIRED_LABELS = (
    "Absatz…",
    "Zeilenabstand 1,0",
    "Zeilenabstand 1,15 (Standard)",
    "Zeilenabstand 1,5",
    "Zeilenabstand 2,0",
    "Mit nächstem Absatz zusammenhalten",
    "Absatzkontrolle (Witwen/Waisen)",
    "Seitenlayout…",
    "A4",
    "Letter",
    "Legal",
    "Hochformat",
    "Querformat",
    "1 Spalte",
    "2 Spalten",
    "3 Spalten",
    "Abschnittsumbruch einfügen",
    "Absatz links",
    "Absatz zentriert",
    "Absatz rechts",
    "Absatz Blocksatz",
    "Zelle oben",
    "Zelle mittig",
    "Zelle unten",
    "Aufzählungszeichen",
    "Nummerierung",
    "Aufzählungszeichen ändern…",
    "Nummerierung neu beginnen",
    "Listenebene erhöhen",
    "Listenebene verringern",
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


def test_word_suite_menus_present() -> None:
    paths = _menu_paths(_WIN)
    texts = _menu_texts(_WIN)
    missing_top = [m for m in REQUIRED_TOP_MENUS if not any(p.split("▸")[0].strip() == m or p == m for p in paths)]
    # Top-level titles appear as path prefix "Absatz ▸ …"
    missing_top = [m for m in REQUIRED_TOP_MENUS if not any(p == m or p.startswith(m + " ▸") for p in paths)]
    assert missing_top == [], f"Top-Menüs fehlen: {missing_top}"
    missing = [lab for lab in REQUIRED_LABELS if lab not in texts]
    assert missing == [], f"Einträge fehlen: {missing}"


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
    assert ed.insert_rich_table(2, 2)
    assert ed.current_table() is not None
    assert ed.set_table_cell_vertical_alignment("middle")
    assert ed.current_cell_vertical_alignment() == "middle"


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
    from instantlensdoc.core.ocr_word_suite import blocks_to_word_suite_html, WordSuiteBlock

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
    dlg.close()
    pane = _WIN.editor_pane
    assert "align_justify" in pane._tool_buttons
    assert "bullet_list" in pane._tool_buttons
    assert getattr(pane, "layout_picker", None) is not None


def test_list_glyph_dialog_opens() -> None:
    from instantlensdoc.ui.list_glyph_dialog import ListGlyphDialog

    dlg = ListGlyphDialog("•", _WIN)
    assert dlg.objectName() == "listGlyphDialog"
    assert dlg.result_glyph() == "•"
    dlg.close()


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
        and str(r.get("path") or "").startswith(("Absatz ▸", "Aufzählungszeichen ▸", "Ausrichtung ▸", "Seitenlayout ▸"))
    ]
    assert not still_on, "Word-Suite-Menüs bei PDF aktiv: " + "; ".join(still_on[:8])
