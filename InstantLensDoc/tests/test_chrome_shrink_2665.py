"""Menü/Ribbon schrumpfen mit dem Fenster; Overflow » löst die QAction."""

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
from PySide6.QtWidgets import QScrollArea  # noqa: E402

from menu_smoke_lib import (  # noqa: E402
    build_fixtures,
    create_main_window,
    install_headless_env,
    pump,
)
from instantlensdoc.ui.menu_click import (  # noqa: E402
    find_menubar_menu,
    show_scrollable_menu,
)
from instantlensdoc.ui.ribbon_bar import _OverflowPanel  # noqa: E402


_APP = None
_WIN = None
_TD = None
_FIXTURES = None


def setup_module() -> None:
    global _APP, _WIN, _TD, _FIXTURES
    install_headless_env()
    _TD = tempfile.TemporaryDirectory(prefix="ild-chrome-shrink-2665-")
    _FIXTURES = build_fixtures(Path(_TD.name))
    _APP, _WIN = create_main_window()


def teardown_module() -> None:
    global _WIN, _TD
    try:
        if _WIN is not None:
            _WIN.close()
    except Exception:
        pass
    if _TD is not None:
        _TD.cleanup()


def _menu_titles() -> list[str]:
    mb = _WIN.menuBar()
    out = []
    for act in mb.actions():
        menu = act.menu() if hasattr(act, "menu") else None
        if menu is None:
            continue
        out.append((menu.title() or act.text() or "").replace("&", "").strip())
    return out


def test_menubar_scroll_host_installed() -> None:
    host = getattr(_WIN, "_ild_menubar_host", None)
    assert host is not None
    assert isinstance(host, QScrollArea)
    assert host.horizontalScrollBarPolicy() == Qt.ScrollBarAsNeeded
    assert _WIN.menuBar() is getattr(_WIN, "_ild_chrome_menubar", None)


def test_narrow_window_keeps_all_menu_titles() -> None:
    _WIN.resize(1280, 800)
    pump(_APP, 0.08)
    wide = _menu_titles()
    assert "Bearbeiten" in wide
    assert "PDF" in wide
    assert "DTP" in wide
    _WIN.resize(360, 640)
    pump(_APP, 0.12)
    _WIN.menuBar().updateGeometry()
    host = _WIN._ild_menubar_host
    host._fit()
    pump(_APP, 0.08)
    narrow = _menu_titles()
    assert wide == narrow, f"Menütitel verloren: {set(wide) - set(narrow)}"
    for title in wide:
        menu = find_menubar_menu(_WIN, title)
        assert menu is not None
        assert menu.isEnabled()
        n = sum(1 for a in menu.actions() if not a.isSeparator())
        assert n >= 1, f"Menü {title} ohne Einträge"


def test_ribbon_shrinks_without_losing_actions() -> None:
    rb = _WIN.ribbon_bar
    rb.setVisible(True)
    rb.select_tab("Start")
    pump(_APP, 0.08)
    ids_wide = set(rb._actions)
    assert "bold" in ids_wide
    _WIN.resize(320, 640)
    rb.resize(300, rb.height())
    pump(_APP, 0.15)
    for panel in rb.findChildren(_OverflowPanel):
        panel._reflow()
    assert set(rb._actions) == ids_wide
    hidden = []
    for panel in rb.findChildren(_OverflowPanel):
        hidden.extend(panel._hidden_specs)
    scrolls = rb.findChildren(QScrollArea)
    names = {s.objectName() for s in scrolls}
    assert "ildRibbonTabScroll" in names
    assert "ildRibbonBodyScroll" in names
    assert hidden or any(
        s.horizontalScrollBar().isVisible()
        or s.horizontalScrollBar().maximum() > 0
        for s in scrolls
    ), "Weder Overflow » noch Scrollbar bei schmalem Ribbon"


def test_overflow_menu_is_one_column_and_triggers_qaction() -> None:
    rb = _WIN.ribbon_bar
    _p_hits = {"n": 0}

    def _hit(*_a, **_k):
        _p_hits["n"] += 1

    act = rb.qaction("bold")
    assert act is not None
    act.setEnabled(True)
    act.triggered.connect(_hit)
    try:
        menu = show_scrollable_menu(
            [("bold", "Fett"), ("italic", "Kursiv")],
            rb,
            on_pick=rb._pick_overflow,
            qactions=getattr(rb, "_qactions", None),
        )
        assert menu is not None
        geos = [menu.actionGeometry(a) for a in menu.actions() if not a.isSeparator()]
        assert geos and all(g.x() < 48 for g in geos)
        bold = next(a for a in menu.actions() if a.property("ribbonActionId") == "bold")
        bold.trigger()
        pump(_APP, 0.08)
    finally:
        try:
            act.triggered.disconnect(_hit)
        except Exception:
            pass
    assert _p_hits["n"] >= 1, f"Overflow ohne QAction.triggered ({_p_hits['n']})"
