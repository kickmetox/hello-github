"""Audit-Bar 2655: Dialog oder sichtbare Änderung — kein Trigger-Pass."""

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

from menu_effect_lib import (  # noqa: E402
    DialogRecorder,
    build_effect_fixtures,
    classify_events,
    create_main_window,
    install_headless_env,
    inventory_window,
    load_effect_state,
    pump,
    snapshot_state,
    state_changed,
    walk_state,
)


_APP = None
_WIN = None
_FX = None
_TD = None
_REC = None


def setup_module() -> None:
    global _APP, _WIN, _FX, _TD, _REC
    install_headless_env()
    _TD = tempfile.TemporaryDirectory(prefix="ild-pytest-2655-audit-")
    _FX = build_effect_fixtures(Path(_TD.name))
    _REC = DialogRecorder(shot_dir=None)
    _REC.install()
    _APP, _WIN = create_main_window()


def teardown_module() -> None:
    global _WIN, _TD, _REC
    try:
        if _WIN is not None:
            _WIN.close()
    except Exception:
        pass
    if _REC is not None:
        _REC.restore()
    if _TD is not None:
        _TD.cleanup()


def _top_menus(win) -> set[str]:
    titles = set()
    for act in win.menuBar().actions():
        menu = act.menu()
        t = (menu.title() if menu is not None else act.text() or "").replace("&", "")
        if t:
            titles.add(t)
    return titles


def test_format_and_fenster_menus_exist() -> None:
    titles = _top_menus(_WIN)
    assert "Format" in titles, titles
    assert "Fenster" in titles, titles
    assert "Geräte" in titles, titles
    assert "PDF" in titles, titles


def test_bold_is_effect_on_docx() -> None:
    load_effect_state(_WIN, _APP, "docx", _FX)
    pump(_APP, 0.15)
    _REC.reset()
    before = snapshot_state(_WIN)
    _WIN._toggle_bold()
    pump(_APP, 0.05)
    after = snapshot_state(_WIN)
    ch = state_changed(before, after)
    verd, det = classify_events(list(_REC.events), ch)
    assert verd == "effect", (verd, det, ch)
    assert "html" in ch or "plain" in ch


def test_settings_opens_dialog() -> None:
    load_effect_state(_WIN, _APP, "docx", _FX)
    _REC.reset()
    _WIN._settings()
    pump(_APP, 0.1)
    verd, det = classify_events(list(_REC.events), [])
    assert verd == "open", (verd, det, _REC.events)


def test_hooks_opens_feature_dialog_not_infobox() -> None:
    _REC.reset()
    _WIN._show_hooks_info()
    pump(_APP, 0.1)
    events = list(_REC.events)
    verd, det = classify_events(events, [])
    assert verd == "open", (verd, det, events)
    assert not any(e.get("box") == "information" for e in events)


def test_docx_format_menu_no_fail() -> None:
    load_effect_state(_WIN, _APP, "docx", _FX)
    rows = walk_state(_APP, _WIN, "docx", _REC, _FX)
    fmt = [r for r in rows if str(r.get("path") or "").startswith("Format ▸")]
    fails = [r for r in fmt if r.get("verdict") == "fail"]
    assert fmt, "Format-Menü leer"
    assert not fails, fails[:8]


def test_enabled_edit_actions_pass_on_ocr() -> None:
    load_effect_state(_WIN, _APP, "ocr", _FX)
    rows = walk_state(_APP, _WIN, "ocr", _REC, _FX)
    core = {
        "Fett",
        "Kopieren",
        "Suchen und Ersetzen…",
        "Schriftart…",
        "Durchgestrichen",
        "Formatierungen löschen",
    }
    fails = [
        r
        for r in rows
        if r.get("text") in core
        and r.get("verdict") == "fail"
        and str(r.get("path") or "").startswith("Bearbeiten")
    ]
    assert not fails, fails


def test_question_dialog_is_open() -> None:
    verd, det = classify_events(
        [{"kind": "messagebox", "box": "question", "cls": "QMessageBox", "title": "x"}],
        [],
    )
    assert verd == "open", (verd, det)


def test_infobox_is_fail() -> None:
    verd, det = classify_events(
        [{"kind": "messagebox", "box": "information", "cls": "QMessageBox", "title": "x"}],
        [],
    )
    assert verd == "fail", (verd, det)


def test_encoding_opens_dialog_on_docx() -> None:
    load_effect_state(_WIN, _APP, "docx", _FX)
    _REC.reset()
    _WIN.save_doc_with_encoding()
    pump(_APP, 0.1)
    verd, det = classify_events(list(_REC.events), [])
    assert verd == "open", (verd, det, _REC.events)


def test_detach_opens_dialog_on_docx() -> None:
    load_effect_state(_WIN, _APP, "docx", _FX)
    _REC.reset()
    _WIN._detach_current_document()
    pump(_APP, 0.1)
    verd, det = classify_events(list(_REC.events), [])
    assert verd == "open", (verd, det, _REC.events)


def test_pdf_measures_empty_opens_dialog() -> None:
    load_effect_state(_WIN, _APP, "pdf", _FX)
    _REC.reset()
    _WIN._pdf_menu_call("Messwerte als CSV exportieren…", lambda: None)
    pump(_APP, 0.1)
    verd, det = classify_events(list(_REC.events), [])
    assert verd == "open", (verd, det, _REC.events)


def test_pdf_search_prev_opens_dialog() -> None:
    load_effect_state(_WIN, _APP, "pdf", _FX)
    _REC.reset()
    _WIN._on_search_prev()
    pump(_APP, 0.1)
    verd, det = classify_events(list(_REC.events), [])
    assert verd == "open", (verd, det, _REC.events)


def test_pdf_highlight_all_empty_query_opens_dialog() -> None:
    load_effect_state(_WIN, _APP, "pdf", _FX)
    _REC.reset()
    _WIN._on_search_annotate_hits(True)
    pump(_APP, 0.1)
    verd, det = classify_events(list(_REC.events), [])
    assert verd == "open", (verd, det, _REC.events)


def test_pdf_save_all_opens_dialog() -> None:
    load_effect_state(_WIN, _APP, "pdf", _FX)
    _REC.reset()
    _WIN.save_all_docs()
    pump(_APP, 0.1)
    verd, det = classify_events(list(_REC.events), [])
    assert verd == "open", (verd, det, _REC.events)


def test_pdf_align_empty_opens_dialog() -> None:
    load_effect_state(_WIN, _APP, "pdf", _FX)
    _REC.reset()
    _WIN._align_selected_annotations("center")
    pump(_APP, 0.1)
    verd, det = classify_events(list(_REC.events), [])
    assert verd == "open", (verd, det, _REC.events)


def test_pdf_extract_text_opens_dialog() -> None:
    load_effect_state(_WIN, _APP, "pdf", _FX)
    _REC.reset()
    _WIN._extract_all_text_to_editor()
    pump(_APP, 0.15)
    verd, det = classify_events(list(_REC.events), [])
    assert verd == "open", (verd, det, _REC.events)