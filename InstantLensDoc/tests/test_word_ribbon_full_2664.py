"""Word-Ribbon vollständig: lokale Befehle mutieren, Online-Features mit Tooltip deaktiviert."""

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

from PySide6.QtGui import QTextCursor  # noqa: E402
from PySide6.QtWidgets import QLabel  # noqa: E402

from menu_smoke_lib import (  # noqa: E402
    build_fixtures,
    create_main_window,
    install_headless_env,
    load_state,
    pump,
)
from instantlensdoc.ui.word_ribbon import DISABLED_REASONS, WORD_TAB_GROUPS  # noqa: E402


_APP = None
_WIN = None
_TD = None
_FIXTURES = None


def setup_module() -> None:
    global _APP, _WIN, _FIXTURES, _TD
    install_headless_env()
    _TD = tempfile.TemporaryDirectory(prefix="ild-word-ribbon-2664-")
    _FIXTURES = build_fixtures(Path(_TD.name))
    _APP, _WIN = create_main_window()


def teardown_module() -> None:
    global _WIN, _TD
    try:
        if _WIN is not None:
            _WIN.hide()
    except Exception:
        pass
    _WIN = None
    if _TD is not None:
        _TD.cleanup()


def test_word_tabs_have_groups_and_disabled_tooltips() -> None:
    rb = _WIN.ribbon_bar
    for tab in ("Start", "Einfügen", "Layout", "Verweise", "Sendungen", "Überprüfen", "Ansicht"):
        rb.select_tab(tab)
        pump(_APP, 0.02)
        wrap = rb._stack.currentWidget()
        titles = [
            lab.text()
            for lab in wrap.findChildren(QLabel)
            if lab.objectName() == "ribbonGroupTitle"
        ]
        assert titles, f"{tab} ohne Gruppen: {titles}"
    for aid, reason in DISABLED_REASONS.items():
        assert aid in rb._actions, aid
        btn = rb._actions[aid]
        assert not btn.isEnabled(), aid
        assert reason in (btn.toolTip() or ""), (aid, btn.toolTip())
    assert WORD_TAB_GROUPS["Start"][0][0] == "Schriftart"


def test_start_clipboard_font_and_format_painter() -> None:
    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.1)
    ed = _WIN.editor
    ed.setPlainText("FormatPainter Probe")
    cur = ed.textCursor()
    cur.select(QTextCursor.Document)
    ed.setTextCursor(cur)
    assert ed.toggle_bold_selection()
    _WIN._format_painter()
    assert _WIN._format_painter_armed
    ed.setPlainText("Zweites Ziel")
    cur = ed.textCursor()
    cur.select(QTextCursor.Document)
    ed.setTextCursor(cur)
    _WIN._format_painter()
    assert ed.selection_font_bold() or int(ed._selection_probe_format(ed.textCursor()).fontWeight()) >= 75
    assert ed.toggle_subscript_selection()
    assert ed.toggle_superscript_selection()
    assert ed.grow_font_selection(2)
    assert ed.shrink_font_selection(1)
    for aid in ("cut", "copy", "paste", "format_painter", "font_color", "grow_font", "subscript"):
        assert aid in _WIN.ribbon_bar._actions, aid


def test_insert_mutations_and_references() -> None:
    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.1)
    ed = _WIN.editor
    ed.setPlainText("Fließtext für Einfügen.")
    assert ed.insert_blank_page()
    assert "Seite" in ed.toPlainText() or ed.document().blockCount() > 1
    assert ed.insert_bookmark("ziel")
    assert "[ziel]" in ed.toPlainText()
    assert ed.insert_date_time("01.01.2024 12:00")
    assert "2024" in ed.toPlainText()
    assert ed.insert_symbol("©")
    assert "©" in ed.toPlainText()
    assert ed.insert_footnote("Hinweis")
    assert "Fußnote" in ed.toPlainText()
    assert ed.insert_endnote("Ende")
    assert "Endnote" in ed.toPlainText()
    assert ed.insert_caption("Foto")
    assert "Abbildung" in ed.toPlainText()
    assert ed.insert_bibliography_block("Literatur\n[1] Test (2024): Werk.")
    assert "Literatur" in ed.toPlainText()
    assert ed.insert_text_box("Kasten")
    assert ed.insert_cover_page("DeckblattTest")
    assert "DeckblattTest" in ed.toPlainText()
    assert ed.insert_cross_ref("ziel")
    assert "siehe [ziel]" in ed.toPlainText()
    assert ed.mark_index_entry("Indexwort")
    assert "{XE:Indexwort}" in ed.toPlainText()
    assert ed.insert_citation("Meier", "2020", "Werk")
    assert "Meier" in ed.toPlainText()
    assert ed.insert_equation("∑")
    assert "∑" in ed.toPlainText()
    assert ed.insert_signature_line()
    assert "Unterschrift" in ed.toPlainText()
    assert ed.insert_address_block()
    assert "{vorname}" in ed.toPlainText()
    assert ed.insert_greeting_line()
    assert "{anrede}" in ed.toPlainText()
    n = ed.highlight_merge_fields()
    assert n >= 1
    stats = ed.word_count_stats()
    assert stats["words"] > 0
    from instantlensdoc.ui.bibliography_dialog import BibliographyDialog

    dlg = BibliographyDialog(_WIN)
    assert dlg.objectName() == "bibliographyDialog"
    dlg.close()


def test_envelopes_labels_and_view_modes() -> None:
    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.1)
    _WIN._apply_envelope_layout()
    lay = _WIN.editor.page_layout()
    assert lay is not None
    from ild_pdf.pages import pt_to_mm

    w, h = lay.page_size_pt()
    assert pt_to_mm(max(w, h)) > 200
    _WIN._apply_label_layout()
    lay = _WIN.editor.page_layout()
    w, h = lay.page_size_pt()
    assert pt_to_mm(min(w, h)) <= 51.0
    assert _WIN.editor.set_word_view_mode("draft") == "draft"
    assert _WIN.editor.set_word_view_mode("print") == "print"


def test_disabled_ribbon_click_sets_status() -> None:
    _WIN._on_ribbon_action("smartart")
    pump(_APP, 0.02)
    msg = ""
    try:
        msg = _WIN.statusBar().currentMessage()
    except Exception:
        msg = ""
    assert "SmartArt" in msg or "nicht lokal" in msg
    for aid in (
        "thesaurus",
        "translate",
        "screenshot",
        "icons",
        "insert_chart",
        "online_pictures",
        "mail_merge_rules",
    ):
        assert aid in _WIN.ribbon_bar._actions
        assert not _WIN.ribbon_bar._actions[aid].isEnabled()
    for aid in (
        "toggle_case",
        "replace",
        "goto",
        "insert_cover_page",
        "insert_cross_ref",
        "insert_citation",
        "mark_index",
        "mail_merge_address",
        "review_accept",
        "view_outline",
        "toggle_minimap",
        "zoom_one_page",
    ):
        assert aid in _WIN.ribbon_bar._actions, aid
        assert _WIN.ribbon_bar._actions[aid].isEnabled(), aid

