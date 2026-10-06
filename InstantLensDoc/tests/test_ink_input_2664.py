"""Stifteingabe / Touch-Handschrift auf der unified View — Offscreen."""

from __future__ import annotations

import os
import sys
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

from PySide6.QtCore import Qt  # noqa: E402

from menu_smoke_lib import create_main_window, install_headless_env, pump  # noqa: E402


_APP = None
_WIN = None


def setup_module() -> None:
    global _APP, _WIN
    install_headless_env()
    _APP, _WIN = create_main_window()


def teardown_module() -> None:
    global _WIN
    try:
        if _WIN is not None:
            _WIN.hide()
    except Exception:
        pass
    _WIN = None


def test_stifteingabe_toggle_exists() -> None:
    act = getattr(_WIN, "_act_ink_input", None)
    assert act is not None
    assert act.objectName() == "actInkInput"
    assert "Stifteingabe" in (act.text() or "")
    assert act.isCheckable()
    rec = getattr(_WIN, "_act_recognize_handwriting", None)
    assert rec is not None
    assert rec.objectName() == "actRecognizeHandwriting"
    rb = _WIN.ribbon_bar
    rb.select_tab("Ansicht")
    pump(_APP, 0.05)
    assert "ink_input" in rb._actions
    assert "recognize_handwriting" in rb._actions
    btn = rb._actions["ink_input"]
    assert "Stifteingabe" in (btn.text() or "")
    canvas = _WIN.pdf_view.canvas
    assert bool(canvas.testAttribute(Qt.WA_AcceptTouchEvents))
    session = getattr(_WIN, "_ink_session", None)
    assert session is not None


def test_synthetic_strokes_ocr_stub_or_skip_tessdata() -> None:
    from instantlensdoc.ui.ink_input import (
        recognize_ink_strokes,
        recognized_text_to_html,
        synthetic_stroke_list,
        tessdata_ready,
    )

    strokes = synthetic_stroke_list()
    assert len(strokes) >= 2
    live = recognize_ink_strokes(strokes)
    if live.get("skipped") or not str(live.get("text") or "").strip():
        if live.get("skipped"):
            assert live.get("reason") in (
                "ocr_unavailable",
                "ocr_error",
                "empty",
            ) or not tessdata_ready()[0]
        result = recognize_ink_strokes(strokes, stub=True)
    else:
        result = live
    text = result.get("text") or ""
    html = result.get("html") or recognized_text_to_html(text)
    assert "\u00b6" not in text
    assert "\x0c" not in text
    assert "\u00b6" not in html
    assert "\x0c" not in html
    assert result.get("stub") or result.get("ok") or text


def test_recognized_text_inserts_rich_not_pilcrow(qapp) -> None:
    from instantlensdoc.ui.editor import TextEditor
    from instantlensdoc.ui.ink_input import recognized_text_to_html

    from PySide6.QtGui import QTextCursor  # noqa: E402

    dirty = "Hallo\x0cWelt\u00b6Test"
    html = recognized_text_to_html(dirty)
    assert "\u00b6" not in html
    assert "\x0c" not in html
    ed = TextEditor()
    ed.setPlainText("Caret ")
    cur = ed.textCursor()
    cur.movePosition(QTextCursor.MoveOperation.End)
    ed.setTextCursor(cur)
    assert ed.insert_recognized_rich_text(html, dirty)
    plain = ed.toPlainText()
    assert "Hallo" in plain
    assert "\u00b6" not in plain
    assert "\x0c" not in plain
    ed.deleteLater()


def test_schreibschutz_grays_out_ink_actions() -> None:
    act = _WIN._act_ink_input
    rec = _WIN._act_recognize_handwriting
    _WIN.editor.setReadOnly(False)
    _WIN._sync_ink_input_actions()
    pump(_APP, 0.02)
    assert act.isEnabled()
    assert rec.isEnabled()
    _WIN.editor.setReadOnly(True)
    _WIN._sync_ink_input_actions()
    pump(_APP, 0.02)
    assert not act.isEnabled()
    assert not rec.isEnabled()
    _WIN.editor.setReadOnly(False)
    _WIN._sync_ink_input_actions()
    pump(_APP, 0.02)
    assert act.isEnabled()


def test_toggle_stifteingabe_enables_session() -> None:
    session = _WIN._ink_session
    _WIN.editor.setReadOnly(False)
    _WIN._sync_ink_input_actions()
    _WIN._act_ink_input.setChecked(False)
    _WIN._toggle_ink_input(True)
    pump(_APP, 0.02)
    assert session.enabled is True
    session.begin(10, 10, 0.5)
    session.move(20, 12, 0.6)
    session.end()
    assert len(session.strokes) == 1
    _WIN._toggle_ink_input(False)
    assert session.enabled is False
    session.clear()
