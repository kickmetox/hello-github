"""Word-Suite Layout-Marken: Toggles, Persistenz, Konfigurationsdialog — Offscreen."""

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

import pytest  # noqa: E402
from menu_smoke_lib import create_main_window, install_headless_env, pump  # noqa: E402

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402

from instantlensdoc.core.editor_layout_marks import (  # noqa: E402
    EditorLayoutMarks,
    crop_mark_segments_mm,
)


def test_defaults_width_and_hf_on_print_off():
    m = EditorLayoutMarks()
    assert m.show_width_marks is True
    assert m.show_header_footer_marks is True
    assert m.show_print_marks is False
    assert m.include_print_on_print is True
    segs = crop_mark_segments_mm(210.0, 297.0, crop_mm=5.0, gap_mm=1.0)
    assert len(segs) == 8
    loaded = EditorLayoutMarks.from_dict({"show_print_marks": True, "crop_mm": 99})
    assert loaded.show_print_marks is True
    assert loaded.crop_mm == 25.0  # clamp


@pytest.fixture(scope="module")
def main_win():
    td = tempfile.TemporaryDirectory(prefix="ild-layout-marks-")
    install_headless_env(td.name)
    app, win = create_main_window()
    try:
        win.new_doc("empty")
        pump(app, 0.15)
    except Exception:
        try:
            win.stack.setCurrentWidget(win.editor_pane)
            pump(app, 0.05)
        except Exception:
            pass
    yield app, win
    try:
        win.close()
    except Exception:
        pass
    try:
        app.processEvents()
        app.quit()
    except Exception:
        pass
    td.cleanup()


def test_toggles_mutate_view_flags(main_win) -> None:
    app, win = main_win
    ed = win.editor
    assert ed.show_width_marks() is True
    assert ed.show_header_footer_marks() is True
    assert ed.show_print_marks() is False
    win._toggle_width_marks(False)
    pump(app, 0.05)
    assert ed.show_width_marks() is False
    assert win._width_marks_action.isChecked() is False
    win._toggle_editor_print_marks(True)
    pump(app, 0.05)
    assert ed.show_print_marks() is True
    assert win._editor_print_marks_action.isChecked() is True
    win._toggle_header_footer_marks(False)
    pump(app, 0.05)
    assert ed.show_header_footer_marks() is False
    persisted = EditorLayoutMarks.from_settings()
    assert persisted.show_width_marks is False
    assert persisted.show_print_marks is True
    assert persisted.show_header_footer_marks is False
    win._toggle_width_marks(True)
    pump(app, 0.05)
    assert ed.show_width_marks() is True
    assert ed.show_print_marks() is True


def test_layout_marks_dialog_opens_qtimer_close(main_win) -> None:
    app, win = main_win
    opened: list[str] = []

    def _close_modal() -> None:
        w = QApplication.activeModalWidget()
        if isinstance(w, QDialog):
            opened.append(w.objectName())
            w.reject()

    QTimer.singleShot(250, _close_modal)
    win._show_editor_layout_marks_dialog()
    pump(app, 0.15)
    assert "editorLayoutMarksDialog" in opened, opened
    assert "pageMarginsDialog" not in opened


def test_marks_do_not_mutate_page_margins(main_win) -> None:
    """Seitenränder gehören Layout → Seitenränder, nicht den Marken."""
    _app, win = main_win
    lay = win.editor.page_layout()
    assert lay is not None
    before = (
        float(lay.margin_left_mm),
        float(lay.margin_right_mm),
        float(lay.margin_top_mm),
        float(lay.margin_bottom_mm),
        float(lay.header_distance_mm),
        float(lay.footer_distance_mm),
    )
    m = win.editor.layout_marks()
    m.header_height_mm = 20.0
    m.footer_height_mm = 18.0
    win.editor.set_layout_marks(m)
    win._toggle_width_marks(not win.editor.show_width_marks())
    lay2 = win.editor.page_layout()
    after = (
        float(lay2.margin_left_mm),
        float(lay2.margin_right_mm),
        float(lay2.margin_top_mm),
        float(lay2.margin_bottom_mm),
        float(lay2.header_distance_mm),
        float(lay2.footer_distance_mm),
    )
    assert after == before
    from instantlensdoc.ui.page_margins_dialog import PageMarginsDialog
    from instantlensdoc.ui.editor_layout_marks_dialog import EditorLayoutMarksDialog

    assert PageMarginsDialog is not EditorLayoutMarksDialog
    assert PageMarginsDialog().objectName() == "pageMarginsDialog"
    assert EditorLayoutMarksDialog().objectName() == "editorLayoutMarksDialog"


def test_header_footer_dialog_opens_qtimer_close(main_win) -> None:
    app, win = main_win
    opened: list[str] = []

    def _close_modal() -> None:
        w = QApplication.activeModalWidget()
        if isinstance(w, QDialog):
            opened.append(w.objectName())
            w.reject()

    QTimer.singleShot(250, _close_modal)
    win._edit_editor_header_footer("header")
    pump(app, 0.15)
    assert "headerFooterDialog" in opened, opened


def test_menu_and_toolbar_actions_exist(main_win) -> None:
    _app, win = main_win
    names = {
        (a.text() or "").replace("&", "")
        for a in win.findChildren(type(win._width_marks_action))
    }
    assert "Breitenmarken" in names
    assert "Druckmarken" in names
    assert "Kopf-/Fußzeilen-Marken" in names
    assert "Layout-Marken…" in names
    rb = win.ribbon_bar
    for aid in ("width_marks", "print_marks", "header_footer_marks", "layout_marks"):
        assert aid in rb._actions, aid
    pane = win.editor_pane
    for aid in ("width_marks", "print_marks", "header_footer_marks", "layout_marks"):
        assert aid in pane._tool_buttons, aid
    ov = getattr(win.editor, "_marks_overlay", None)
    assert ov is not None
    assert ov.objectName() == "editorLayoutMarksOverlay"
