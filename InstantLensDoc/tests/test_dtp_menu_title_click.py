"""DTP-Menütitel / Ribbon-Tab: Klick öffnet Layout-Modus (sibling-Slot)."""

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

from menu_effect_lib import pump  # noqa: E402
from menu_smoke_lib import (  # noqa: E402
    build_fixtures,
    create_main_window,
    install_headless_env,
    load_state,
)
from instantlensdoc.ui.menu_click import (  # noqa: E402
    find_menubar_menu,
    iter_leaf_actions,
    prepare_menu_for_clicks,
)


_APP = None
_WIN = None
_TD = None
_FIXTURES = None


def setup_module() -> None:
    global _APP, _WIN, _TD, _FIXTURES
    install_headless_env()
    _TD = tempfile.TemporaryDirectory(prefix="ild-dtp-menu-click-")
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


def _leave_dtp() -> None:
    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.1)
    pane = getattr(_WIN, "dtp_pane", None)
    if pane is not None:
        try:
            pane.clear_dirty()
        except Exception:
            pass
    doc = getattr(_WIN, "doc", None)
    if doc is not None:
        doc.dirty = False
    try:
        _WIN._leave_layout_mode()
    except Exception:
        try:
            _WIN.stack.setCurrentWidget(_WIN.editor_pane)
        except Exception:
            pass
    pump(_APP, 0.05)
    assert not _WIN._layout_mode_active()


def test_dtp_menu_exists_one_column() -> None:
    menu = find_menubar_menu(_WIN, "DTP")
    assert menu is not None, "Top-Level-Menü DTP fehlt"
    assert menu.objectName() == "menuDtp"
    prepare_menu_for_clicks(menu)
    menu.popup(
        menu.parentWidget().mapToGlobal(menu.rect().topLeft())
        if menu.parentWidget()
        else menu.pos()
    )
    menu.show()
    pump(_APP, 0.08)
    rect = menu.rect()
    overflow = []
    for path, _h, act in iter_leaf_actions(menu, "DTP"):
        geo = menu.actionGeometry(act)
        if geo.isValid() and geo.x() > rect.width():
            overflow.append(f"{path} x={geo.x()}")
    menu.hide()
    assert not overflow, "DTP-Menü zweite Spalte:\n" + "\n".join(overflow[:8])
    labels = [
        (act.text() or "").replace("&", "").strip()
        for _p, _h, act in iter_leaf_actions(menu, "DTP")
    ]
    assert "Layout-Modus" in labels


def test_qtest_mouseclick_dtp_menubar_title_enters_layout() -> None:
    _leave_dtp()
    menu = find_menubar_menu(_WIN, "DTP")
    assert menu is not None
    mb = _WIN.menuBar()
    mb.setVisible(True)
    pump(_APP, 0.05)
    dtp_act = None
    for act in mb.actions():
        if act.menu() is menu:
            dtp_act = act
            break
    assert dtp_act is not None
    geo = mb.actionGeometry(dtp_act)
    assert geo.isValid()
    QTest.mouseClick(mb, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, geo.center())
    pump(_APP, 0.15)
    if not _WIN._layout_mode_active():
        menu.popup(mb.mapToGlobal(geo.bottomLeft()))
        pump(_APP, 0.1)
    assert _WIN._layout_mode_active(), "DTP-Menütitel ohne Layout-Modus"
    assert _WIN.stack.currentWidget() is _WIN.dtp_pane


def test_qtest_mouseclick_ribbon_dtp_tab_enters_layout() -> None:
    _leave_dtp()
    rb = _WIN.ribbon_bar
    assert rb is not None
    rb.setVisible(True)
    pump(_APP, 0.05)
    btn = None
    for b in rb._cat_buttons:
        if (b.text() or "").replace("&", "").strip() == "DTP":
            btn = b
            break
    assert btn is not None, "Ribbon-Tab DTP fehlt"
    QTest.mouseClick(btn, Qt.MouseButton.LeftButton)
    pump(_APP, 0.15)
    assert _WIN._layout_mode_active(), "Ribbon-Tab DTP ohne Layout-Modus"
    assert _WIN.stack.currentWidget() is _WIN.dtp_pane
