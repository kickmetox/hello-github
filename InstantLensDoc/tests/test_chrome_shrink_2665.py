"""Menü/Ribbon schrumpfen mit dem Fenster; zu schmal: Scrollbar, keine verlorenen Tools."""

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
    assert "font" in ids_wide
    _WIN.resize(320, 640)
    rb.resize(300, rb.height())
    pump(_APP, 0.15)
    for panel in rb.findChildren(_OverflowPanel):
        panel._reflow()
    assert set(rb._actions) == ids_wide
    hidden = []
    for panel in rb.findChildren(_OverflowPanel):
        hidden.extend(panel._hidden_specs)
    assert hidden == [], f"Ribbon hat Tools versteckt: {hidden[:8]}"
    wrap = rb._stack.currentWidget()
    for aid in ("bold", "font", "italic"):
        btn = rb._actions.get(aid)
        assert btn is not None
        assert btn.isVisibleTo(wrap), aid
    scrolls = rb.findChildren(QScrollArea)
    names = {s.objectName() for s in scrolls}
    assert "ildRibbonTabScroll" in names
    assert "ildRibbonBodyScroll" in names
    body = next(s for s in scrolls if s.objectName() == "ildRibbonBodyScroll")
    body._fit()
    pump(_APP, 0.05)
    assert (
        body.horizontalScrollBar().maximum() > 0
        or body.horizontalScrollBar().isVisible()
        or int(rb._stack.sizeHint().width()) > 300
    ), "Keine horizontale Ribbon-Scrollbar bei schmaler Leiste"


def test_narrow_ribbon_keeps_ink_font_dtp_reachable() -> None:
    rb = _WIN.ribbon_bar
    rb.setVisible(True)
    _WIN.resize(280, 640)
    rb.resize(260, rb.height())
    pump(_APP, 0.12)
    for tab, aids in (
        ("Start", ("font", "bold", "font_color")),
        ("Layout", ("dtp_layout", "group_frames", "dtp_text_frame")),
        ("Ansicht", ("ink_input", "ink_pen_ballpoint", "stamp_place")),
    ):
        rb.select_tab(tab)
        pump(_APP, 0.05)
        wrap = rb._stack.currentWidget()
        for aid in aids:
            assert aid in rb._actions, aid
            btns = list(rb._action_buttons.get(aid) or ())
            if not btns and rb._actions.get(aid) is not None:
                btns = [rb._actions[aid]]
            vis = [b for b in btns if b is not None and b.isVisibleTo(wrap)]
            assert vis, f"{tab}:{aid} unsichtbar ({len(btns)} Instanzen)"
            assert not any(
                aid in (spec[0], spec[1])
                for p in wrap.findChildren(_OverflowPanel)
                for spec in p._hidden_specs
            )
    host = getattr(_WIN, "_ild_menubar_host", None)
    assert host is not None
    host._fit()
    sp = getattr(_WIN, "main_splitter", None)
    if sp is not None and sp.count() >= 2:
        total = max(400, sum(sp.sizes()) or 800)
        sp.setSizes([220, max(180, total - 220)] + list(sp.sizes()[2:]))
        pump(_APP, 0.08)
        _WIN._fit_chrome_hscroll()
        pump(_APP, 0.05)
        rb.select_tab("Ansicht")
        wrap = rb._stack.currentWidget()
        ink = list(rb._action_buttons.get("ink_input") or [rb._actions["ink_input"]])
        assert any(b is not None and b.isVisibleTo(wrap) for b in ink)


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
