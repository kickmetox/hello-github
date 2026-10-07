"""Tab-X / Öffnen: keine Extra-Menüs; Dokument erscheint in der zentralen Ansicht."""

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

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QMenu  # noqa: E402

from menu_effect_lib import DialogRecorder, pump  # noqa: E402
from menu_smoke_lib import (  # noqa: E402
    create_main_window,
    install_headless_env,
    make_docx,
    make_n_page_pdf,
)
from instantlensdoc.core.documents import DocKind  # noqa: E402
from instantlensdoc.ui.menu_click import close_other_menus  # noqa: E402


_APP = None
_WIN = None
_TD = None
_REC = None
_PDF = None
_DOCX = None
_PDF2 = None


def setup_module() -> None:
    global _APP, _WIN, _TD, _REC, _PDF, _DOCX, _PDF2
    install_headless_env()
    _TD = tempfile.TemporaryDirectory(prefix="ild-tab-host-2667-")
    td = Path(_TD.name)
    _PDF = td / "one.pdf"
    _PDF2 = td / "two.pdf"
    _DOCX = td / "doc.docx"
    make_n_page_pdf(_PDF, 2)
    make_n_page_pdf(_PDF2, 2)
    make_docx(_DOCX)
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


def _visible_menus() -> list[str]:
    out = []
    mb = _WIN.menuBar()
    for act in mb.actions():
        menu = act.menu() if hasattr(act, "menu") else None
        if menu is not None and menu.isVisible():
            out.append((menu.title() or act.text() or "").replace("&", "").strip())
    return out


def _close_all() -> None:
    try:
        _WIN.close_all_tabs()
    except Exception:
        pass
    pump(_APP, 0.1)
    close_other_menus(None, menubar=_WIN.menuBar())


def test_open_pdf_shows_in_document_host() -> None:
    _close_all()
    _WIN.open_path(str(_PDF))
    pump(_APP, 0.25)
    assert _WIN.doc is not None
    assert _WIN.doc.kind == DocKind.PDF
    assert _WIN.stack.currentWidget() is _WIN.pdf_view
    assert _WIN.pdf_view.isVisibleTo(_WIN._doc_host)
    if not _WIN._layout_mode_active():
        assert not _WIN.dtp_pane.isVisible()
    assert not _visible_menus()


def test_open_docx_shows_in_document_host() -> None:
    _close_all()
    _WIN.open_path(str(_DOCX))
    pump(_APP, 0.25)
    assert _WIN.doc is not None
    assert _WIN.doc.kind == DocKind.DOCX
    assert _WIN.stack.currentWidget() is _WIN.editor_pane
    assert _WIN.editor_pane.isVisibleTo(_WIN._doc_host)
    if not _WIN._layout_mode_active():
        assert not _WIN.dtp_pane.isVisible()
    assert not _visible_menus()


def test_tab_close_does_not_open_extra_menus_and_shows_remaining() -> None:
    _close_all()
    _WIN.open_path(str(_PDF))
    pump(_APP, 0.15)
    _WIN.open_path(str(_DOCX))
    pump(_APP, 0.2)
    _REC.events.clear()
    close_other_menus(None, menubar=_WIN.menuBar())
    bar = _WIN.doc_tab_bar
    assert bar.tabs.count() >= 2
    idx = None
    for i in range(bar.tabs.count()):
        data = str(bar.tabs.tabData(i) or "")
        if Path(data).name == _DOCX.name:
            idx = i
            break
    assert idx is not None
    close_btn = bar.tabs.tabButton(idx, bar.tabs.ButtonPosition.RightSide)
    if close_btn is not None:
        QTest.mouseClick(close_btn, Qt.MouseButton.LeftButton)
    else:
        bar._on_close(idx)
    pump(_APP, 0.25)
    extras = _visible_menus()
    assert not extras, f"Tab-X öffnete Menüs: {extras}"
    leftover = [
        e
        for e in _REC.events
        if e.get("kind") in ("dialog", "file", "message")
        and "Speichern" not in str(e.get("title") or "")
    ]
    assert not leftover, f"Tab-X öffnete Dialoge: {leftover[:6]}"
    assert _WIN.doc is not None
    assert _WIN.stack.currentWidget() in (_WIN.pdf_view, _WIN.editor_pane)
    assert _WIN.stack.currentWidget() is not _WIN.welcome_page


def test_open_path_then_tab_activate_keeps_host() -> None:
    _close_all()
    _WIN.open_path(str(_PDF))
    pump(_APP, 0.12)
    _WIN.open_path(str(_PDF2))
    pump(_APP, 0.12)
    _WIN._on_doc_tab_activated(str(_PDF))
    pump(_APP, 0.2)
    assert _WIN.stack.currentWidget() is _WIN.pdf_view
    assert Path(_WIN.doc.path).name == _PDF.name
    assert not _visible_menus()
