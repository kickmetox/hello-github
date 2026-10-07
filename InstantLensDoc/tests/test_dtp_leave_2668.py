"""2.6.62: Textverarbeitung verlässt DTP; Tab zeigt Dokument; Fenster min; 8 Griffe."""

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

from menu_effect_lib import DialogRecorder  # noqa: E402
from menu_smoke_lib import (  # noqa: E402
    create_main_window,
    install_headless_env,
    make_n_page_pdf,
    pump,
)
from instantlensdoc.dtp.canvas import ResizeHandle  # noqa: E402
from instantlensdoc.ui.chrome import CHROME_LABELS  # noqa: E402
from instantlensdoc.ui.menu_click import find_menubar_menu  # noqa: E402


_APP = None
_WIN = None
_TD = None
_PDF = None
_REC = None


def setup_module() -> None:
    global _APP, _WIN, _TD, _PDF, _REC
    install_headless_env()
    _TD = tempfile.TemporaryDirectory(prefix="ild-dtp-leave-2668-")
    _PDF = Path(_TD.name) / "sample.pdf"
    make_n_page_pdf(_PDF, 2)
    _REC = DialogRecorder(shot_dir=None)
    _REC.install()
    _APP, _WIN = create_main_window()


def teardown_module() -> None:
    global _WIN, _TD, _REC
    try:
        if _WIN is not None:
            _WIN.hide()
    except Exception:
        pass
    _WIN = None
    if _REC is not None:
        try:
            _REC.restore()
        except Exception:
            pass
        _REC = None
    if _TD is not None:
        try:
            _TD.cleanup()
        except Exception:
            pass
        _TD = None


def _clear_dirty() -> None:
    doc = getattr(_WIN, "doc", None)
    if doc is not None:
        doc.dirty = False
    pane = getattr(_WIN, "dtp_pane", None)
    if pane is not None:
        try:
            pane.clear_dirty()
        except Exception:
            pass


def test_ansicht_and_dtp_menu_named_textverarbeitung() -> None:
    view = find_menubar_menu(_WIN, "Ansicht")
    dtp = find_menubar_menu(_WIN, "DTP")
    assert view is not None and dtp is not None
    view_texts = [a.text() for a in view.actions() if not a.isSeparator()]
    dtp_texts = [a.text() for a in dtp.actions() if not a.isSeparator()]
    assert "Textverarbeitung" in view_texts
    assert dtp_texts[0] == "Textverarbeitung"
    act = _WIN._text_view_action
    assert act.objectName() == "actTextverarbeitung"
    assert act.text() == "Textverarbeitung"


def test_textverarbeitung_leaves_dtp_without_keine_fuellung() -> None:
    _WIN.open_path(str(_PDF))
    pump(_APP, 0.2)
    _clear_dirty()
    assert _WIN._enter_layout_mode()
    pump(_APP, 0.05)
    assert _WIN.dtp_pane.isVisible()
    _clear_dirty()
    assert _WIN._leave_dtp_to_document()
    pump(_APP, 0.05)
    assert not _WIN.dtp_pane.isVisible()
    assert not _WIN._layout_mode_active()
    assert _WIN.stack.currentWidget() is _WIN.pdf_view
    assert _WIN.stack.isVisible()


def test_tab_click_leaves_dtp_overlay() -> None:
    _WIN.open_path(str(_PDF))
    pump(_APP, 0.2)
    _clear_dirty()
    assert _WIN._enter_layout_mode()
    pump(_APP, 0.05)
    assert _WIN.dtp_pane.isVisible()
    _clear_dirty()
    _WIN._on_doc_tab_activated(str(_PDF))
    pump(_APP, 0.15)
    assert not _WIN.dtp_pane.isVisible()
    assert _WIN.stack.currentWidget() is _WIN.pdf_view
    assert not _WIN._layout_mode_active()


def test_window_min_not_full_monitor() -> None:
    hint = _WIN.minimumSizeHint()
    assert hint.width() <= 1024
    assert hint.height() <= 640
    assert _WIN.minimumWidth() <= 1024
    assert _WIN.minimumHeight() <= 640


def test_chrome_labels_klassisch_ribbon_kombiniert() -> None:
    assert CHROME_LABELS["klassisch"] == "Klassisch (Pull-down)"
    assert CHROME_LABELS["ribbon"] == "Ribbon"
    assert CHROME_LABELS["kombiniert"] == "Kombiniert"
    menu = find_menubar_menu(_WIN, "Ansicht")
    titles = []
    for act in menu.actions():
        sub = act.menu()
        if sub is not None:
            titles.append((sub.title() or "").replace("&", "").strip())
    assert any("Klassisch" in t and "Ribbon" in t for t in titles)


def test_dtp_selection_shows_eight_handles() -> None:
    pane = _WIN.dtp_pane
    _WIN._enter_layout_mode()
    pump(_APP, 0.05)
    items = list(pane.scene._items.values())
    assert items
    item = items[0]
    item.setSelected(True)
    pump(_APP, 0.05)
    handles = [h for h in item.childItems() if isinstance(h, ResizeHandle)]
    assert len(handles) == 8
    assert any(h.isVisible() for h in handles)
    item.setSelected(False)
    _clear_dirty()
    _WIN._leave_dtp_to_document()
