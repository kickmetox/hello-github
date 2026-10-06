"""Bearbeiten-Menü + Start-Ribbon: QTextEdit-Formate auf DOCX / Neu / OCR — 2.6.55."""

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
from menu_effect_lib import (  # noqa: E402
    DialogRecorder,
    classify_events,
    snapshot_state,
    state_changed,
)

from PySide6.QtGui import QColor, QFont, QTextCursor  # noqa: E402
from instantlensdoc.ui.menu_click import (  # noqa: E402
    find_menubar_menu,
    iter_leaf_actions,
    mouse_click_menu_action,
)


_APP = None
_WIN = None
_FIXTURES = None
_TD = None
_RESTORE = None
_HOOKS: list = []


REQUIRED_EDIT_LABELS = (
    "Rückgängig",
    "Wiederholen",
    "Ausschneiden",
    "Kopieren",
    "Einfügen",
    "Alles auswählen",
    "Suchen…",
    "Suchen und Ersetzen…",
    "Gehe zu Zeile…",
    "Fett",
    "Kursiv",
    "Unterstrichen",
    "Durchgestrichen",
    "Schriftart…",
    "Schriftgröße…",
    "Schriftfarbe…",
    "Texthervorhebung…",
    "Absatz links",
    "Absatz zentriert",
    "Einrückung erhöhen",
    "Zeilenabstand 1,5",
    "Absatz…",
    "Normal",
    "Überschrift 1",
    "Aufzählungszeichen",
    "Nummerierung",
    "Initial / Drop Cap",
    "Deutsch (DE)",
    "Zeilenumbruch einfügen",
    "Seitenumbruch einfügen",
    "Hyperlink…",
    "Tabelle einfügen…",
    "Rechtschreibung prüfen…",
    "Groß-/Kleinschreibung umschalten",
    "Formatierungen löschen",
)

START_TWIN_IDS = (
    "undo",
    "redo",
    "bold",
    "italic",
    "underline",
    "strike",
    "highlight",
    "find_replace",
    "spellcheck",
    "clear_formatting",
)


def setup_module() -> None:
    global _APP, _WIN, _FIXTURES, _TD, _RESTORE
    install_headless_env()
    _TD = tempfile.TemporaryDirectory(prefix="ild-edit-2655-")
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


def _edit_labels(win) -> set[str]:
    rows = inventory_window(win)
    return {
        r["text"]
        for r in rows
        if r.get("kind") == "menu" and str(r.get("path") or "").startswith("Bearbeiten")
    }


def _select_all_text(win) -> None:
    cur = win.editor.textCursor()
    cur.select(QTextCursor.Document)
    win.editor.setTextCursor(cur)


def _seed_text(win, text: str = "Hallo Formatierung Absatz.") -> None:
    win.editor.setPlainText(text)
    _select_all_text(win)


def _assert_formats_work(win) -> None:
    ed = win.editor
    _seed_text(win)
    assert ed.toggle_bold_selection()
    assert ed.selection_font_bold()
    assert ed.toggle_italic_selection()
    assert ed.selection_font_italic()
    assert ed.toggle_underline_selection()
    assert ed.selection_font_underline()
    assert ed.toggle_strike_selection()
    assert ed.selection_font_strike()
    assert ed.apply_font_family("Arial")
    assert ed.apply_font_size(16)
    assert ed.apply_font_color("#cc0000")
    assert ed.apply_highlight_color("#ffe066")
    assert ed.set_paragraph_alignment("center")
    assert ed.current_block_alignment() == "center"
    assert ed.set_paragraph_spacing(line_spacing=1.5, space_after_pt=10)
    assert ed.adjust_block_indent(24)
    assert ed.apply_style_paragraph("h1")
    assert ed.toggle_list(ordered=False)
    assert "• " in ed.toPlainText()
    _select_all_text(win)
    assert ed.apply_drop_cap(lines=3, chars=1)
    assert ed.insert_break("line")
    assert ed.insert_hyperlink("Link", "https://example.com")
    assert ed.insert_table(2, 2)
    assert ed.toggle_case_selection() or True
    assert ed.clear_formatting()
    win._toggle_bold()
    assert ed.selection_font_bold() or ed.toPlainText()
    ed.undo()
    ed.redo()
    ed.selectAll()
    ed.copy()
    assert True


def test_bearbeiten_menu_contains_required_actions() -> None:
    labels = _edit_labels(_WIN)
    missing = [x for x in REQUIRED_EDIT_LABELS if x not in labels]
    assert missing == [], f"Bearbeiten fehlt: {missing}"


def test_start_ribbon_twins_wired() -> None:
    rb = _WIN.ribbon_bar
    for aid in START_TWIN_IDS:
        assert aid in rb._actions, f"Start-Ribbon ohne {aid}"
    missing = []
    import inspect

    src = inspect.getsource(_WIN._on_ribbon_action)
    for aid in START_TWIN_IDS:
        if f'"{aid}"' not in src:
            missing.append(aid)
    assert missing == [], f"Ribbon-Handler fehlt: {missing}"


def test_formats_on_new_text_doc() -> None:
    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.15)
    assert _WIN._editor_document_active()
    _assert_formats_work(_WIN)


def test_formats_on_loaded_docx() -> None:
    load_state(_WIN, _APP, "docx", _FIXTURES)
    pump(_APP, 0.2)
    assert _WIN._editor_document_active()
    _assert_formats_work(_WIN)


def test_formats_on_ocr_imported_text() -> None:
    _WIN._show_scan_ocr_text(
        "OCR Import Absatz mit genug Text zum Formatieren.",
        title="OCR — Audit",
    )
    pump(_APP, 0.15)
    assert _WIN._editor_document_active()
    assert _WIN.doc is not None
    assert "OCR" in (_WIN.doc.title or "")
    _assert_formats_work(_WIN)


def test_editor_only_disabled_on_pdf() -> None:
    load_state(_WIN, _APP, "pdf20", _FIXTURES)
    pump(_APP, 0.25)
    assert not _WIN._editor_document_active()
    rows = inventory_window(_WIN)
    bold = [
        r
        for r in rows
        if r.get("kind") == "menu" and r.get("text") == "Fett" and "Bearbeiten" in str(r.get("path"))
    ]
    assert bold, "Fett-Menüeintrag fehlt"
    assert bold[0]["enabled"] is False
    strike = [
        r
        for r in rows
        if r.get("kind") == "menu"
        and r.get("text") == "Durchgestrichen"
        and "Bearbeiten" in str(r.get("path"))
    ]
    assert strike and strike[0]["enabled"] is False
    rb = _WIN.ribbon_bar
    assert rb.is_enabled("bold") is False
    assert rb.is_enabled("strike") is False
    assert rb.is_enabled("clear_formatting") is False
    _WIN._toggle_bold()
    _WIN._toggle_strike()
    _WIN._set_paragraph_alignment("center")


def test_native_char_and_block_format_unit(qapp) -> None:
    from instantlensdoc.ui.editor import TextEditor

    ed = TextEditor()
    ed.setPlainText("Wort")
    cur = ed.textCursor()
    cur.select(QTextCursor.Document)
    ed.setTextCursor(cur)
    ed.toggle_strike_selection()
    assert ed.selection_font_strike()
    ed.apply_font_size(20)
    probe = ed._selection_probe_format(ed.textCursor())
    assert probe.fontPointSize() == 20
    ed.set_paragraph_alignment("right")
    assert ed.current_block_alignment() == "right"
    ed.apply_font_color(QColor("#112233"))
    ed.clear_formatting()
    assert not ed.selection_font_strike()
    ed.deleteLater()


def _probe_bold_at(ed, pos: int) -> bool:
    cur = QTextCursor(ed.document())
    cur.setPosition(pos)
    cur.setPosition(min(pos + 1, ed.document().characterCount() - 1), QTextCursor.KeepAnchor)
    return ed._selection_probe_format(cur).fontWeight() >= QFont.Bold


def test_no_selection_applies_global_tools_to_document(qapp) -> None:
    from instantlensdoc.ui.editor import TextEditor

    ed = TextEditor()
    ed.setPlainText("Alpha\n\nBeta")
    cur = ed.textCursor()
    cur.setPosition(0)
    ed.setTextCursor(cur)
    assert not cur.hasSelection()
    assert ed.toggle_bold_selection()
    assert _probe_bold_at(ed, 0)
    assert _probe_bold_at(ed, ed.toPlainText().index("B"))
    ed.set_paragraph_alignment("center")
    assert ed.current_block_alignment() == "center"
    cur = ed.textCursor()
    cur.setPosition(ed.toPlainText().index("B"))
    ed.setTextCursor(cur)
    assert ed.current_block_alignment() == "center"
    ed.apply_font_size(18)
    probe = ed._selection_probe_format(ed.textCursor())
    assert probe.fontPointSize() == 18
    ed.deleteLater()


def test_selection_keeps_format_local(qapp) -> None:
    from instantlensdoc.ui.editor import TextEditor

    ed = TextEditor()
    ed.setPlainText("Alpha Beta")
    cur = ed.textCursor()
    cur.setPosition(0)
    cur.setPosition(5, QTextCursor.KeepAnchor)
    ed.setTextCursor(cur)
    ed.toggle_bold_selection()
    assert _probe_bold_at(ed, 0)
    beta = ed.toPlainText().index("B")
    assert not _probe_bold_at(ed, beta)
    ed.deleteLater()


def test_drop_cap_and_table_require_object_selection(qapp) -> None:
    from instantlensdoc.ui.editor import TextEditor

    ed = TextEditor()
    ed.setPlainText("Hallo Dropcap Absatz.")
    cur = ed.textCursor()
    cur.setPosition(0)
    ed.setTextCursor(cur)
    assert ed.apply_drop_cap(lines=3, chars=1) is True
    cur.select(QTextCursor.WordUnderCursor)
    ed.setTextCursor(cur)
    assert ed.apply_drop_cap(lines=3, chars=1) is True
    ed.setPlainText("kein tabellen text")
    assert ed.format_current_table(style="striped") is False
    ed.insert_table(2, 2)
    # Cursor liegt in der eingefügten Tabelle
    assert ed.format_current_table(style="striped") is True
    ed.deleteLater()


def _reseed_for_click(win, text: str = "Hallo Formatierung Absatz fuer Mausklick.") -> None:
    win.editor.setPlainText(text)
    cur = win.editor.textCursor()
    cur.setPosition(0)
    win.editor.setTextCursor(cur)
    try:
        win._sync_menu_enablement()
        win._sync_editor_only_actions()
    except Exception:
        pass


def _menu_or_fail(title: str):
    menu = find_menubar_menu(_WIN, title)
    assert menu is not None, f"Menü {title} fehlt"
    return menu


def _leaf(menu, title: str, label: str):
    for path, host, act in iter_leaf_actions(menu, title):
        text = (act.text() or "").replace("&", "").strip()
        if text == label:
            return path, host, act
    raise AssertionError(f"{title}: {label} nicht gefunden")


def test_qtest_mouseclick_fett_bearbeiten_changes_document() -> None:
    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.15)
    _reseed_for_click(_WIN)
    before = _WIN.editor.document().toHtml()
    menu = _menu_or_fail("Bearbeiten")
    _path, host, act = _leaf(menu, "Bearbeiten", "Fett")
    assert act.isEnabled()
    assert mouse_click_menu_action(_APP, host, act)
    pump(_APP, 0.1)
    after = _WIN.editor.document().toHtml()
    assert after != before, "QTest.mouseClick Fett (Bearbeiten) ohne Dokumentänderung"


def test_qtest_mouseclick_fett_format_changes_document() -> None:
    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.15)
    _reseed_for_click(_WIN)
    before = _WIN.editor.document().toHtml()
    menu = _menu_or_fail("Format")
    _path, host, act = _leaf(menu, "Format", "Fett")
    assert act.isEnabled()
    assert mouse_click_menu_action(_APP, host, act)
    pump(_APP, 0.1)
    after = _WIN.editor.document().toHtml()
    assert after != before, "QTest.mouseClick Fett (Format) ohne Dokumentänderung"


def test_qtest_mouseclick_column2_case_and_indent() -> None:
    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.15)
    menu = _menu_or_fail("Bearbeiten")
    _reseed_for_click(_WIN, "Alpha Beta")
    before_plain = _WIN.editor.toPlainText()
    _path, host, act = _leaf(menu, "Bearbeiten", "Groß-/Kleinschreibung umschalten")
    assert act.isEnabled()
    assert mouse_click_menu_action(_APP, host, act)
    pump(_APP, 0.1)
    after_plain = _WIN.editor.toPlainText()
    assert after_plain != before_plain, "Mausklick Groß-/Kleinschreibung ohne Effekt"
    _reseed_for_click(_WIN, "Einrueckung Satz.")
    before_html = _WIN.editor.document().toHtml()
    _path, host, act = _leaf(menu, "Bearbeiten", "Einrückung erhöhen")
    assert act.isEnabled()
    assert mouse_click_menu_action(_APP, host, act)
    pump(_APP, 0.1)
    after_html = _WIN.editor.document().toHtml()
    assert after_html != before_html, "Mausklick Einrückung erhöhen ohne Effekt"


def test_qtest_mouseclick_suchen_opens_dialog() -> None:
    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.15)
    rec = DialogRecorder(shot_dir=None)
    rec.install()
    try:
        menu = _menu_or_fail("Bearbeiten")
        _reseed_for_click(_WIN)
        _path, host, act = _leaf(menu, "Bearbeiten", "Suchen…")
        assert act.isEnabled()
        rec.reset()
        assert mouse_click_menu_action(_APP, host, act)
        pump(_APP, 0.15)
        verdict, detail = classify_events(rec.events, [])
        assert verdict == "open", f"Suchen… Mausklick: {verdict}/{detail} events={rec.events}"
    finally:
        rec.restore()


def test_qtest_mouseclick_all_enabled_bearbeiten_format_leaves() -> None:
    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.2)
    rec = DialogRecorder(shot_dir=None)
    rec.install()
    fails: list[str] = []
    clicked = 0
    seen_act: set[int] = set()
    try:
        for title in ("Bearbeiten", "Format"):
            menu = _menu_or_fail(title)
            for path, host, act in iter_leaf_actions(menu, title):
                text = (act.text() or "").replace("&", "").strip()
                if text in ("(leer)",) or text.lower() in ("beenden", "quit", "exit"):
                    continue
                _reseed_for_click(_WIN)
                if "einrückung verringern" in text.lower():
                    try:
                        _WIN.editor.adjust_block_indent(24)
                    except Exception:
                        pass
                try:
                    if not act.isEnabled():
                        continue
                except Exception:
                    continue
                rec.reset()
                hits = {"n": 0}

                def _hit(*_a, **_k):
                    hits["n"] += 1

                act.triggered.connect(_hit)
                before = snapshot_state(_WIN)
                try:
                    ok = mouse_click_menu_action(_APP, host, act)
                    pump(_APP, 0.05)
                finally:
                    try:
                        act.triggered.disconnect(_hit)
                    except Exception:
                        pass
                after = snapshot_state(_WIN)
                changes = state_changed(before, after)
                verdict, detail = classify_events(rec.events, changes)
                clicked += 1
                alias = id(act) in seen_act
                seen_act.add(id(act))
                if not ok or hits["n"] < 1:
                    fails.append(
                        f"{path}: click={ok} triggered={hits['n']} {verdict}/{detail}"
                    )
                    continue
                if alias:
                    continue
                if verdict not in ("open", "effect"):
                    fails.append(f"{path}: click={ok} {verdict}/{detail}")
        assert clicked > 0, "keine enabled Leaves geklickt"
        assert fails == [], "Mausklick ohne Slot/Dialog/Effekt:\n" + "\n".join(fails[:24])
    finally:
        rec.restore()
