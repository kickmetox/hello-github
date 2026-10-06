"""Chrome: Pulldown-Menü und Ribbon klicken dieselbe QAction."""

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

from menu_smoke_lib import (  # noqa: E402
    build_fixtures,
    create_main_window,
    install_headless_env,
    load_state,
    pump,
)
from instantlensdoc.ui.menu_click import (  # noqa: E402
    find_menubar_menu,
    iter_leaf_actions,
    mouse_click_menu_action,
    prepare_menu_for_clicks,
)


_APP = None
_WIN = None
_TD = None
_FIXTURES = None

_SHARED = (
    ("bold", "Bearbeiten", "Fett"),
    ("align_left", "Bearbeiten", "Absatz links"),
    ("bullet_list", "Bearbeiten", "Aufzählungszeichen"),
    ("page_layout", "Ansicht", "Seitenlayout…"),
    ("strike", "Bearbeiten", "Durchgestrichen"),
)


def setup_module() -> None:
    global _APP, _WIN, _TD, _FIXTURES
    install_headless_env()
    _TD = tempfile.TemporaryDirectory(prefix="ild-chrome-2662-")
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


def _menu_action(title: str, label: str):
    menu = find_menubar_menu(_WIN, title)
    assert menu is not None, f"Menü {title} fehlt"
    for path, host, act in iter_leaf_actions(menu, title):
        text = (act.text() or "").replace("&", "").strip()
        if text == label:
            return path, host, act
    raise AssertionError(f"{title}: {label} nicht gefunden")


def _seed() -> None:
    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.12)
    _WIN.editor.setPlainText("Hallo Chrome Absatz Listen.")
    cur = _WIN.editor.textCursor()
    cur.setPosition(0)
    _WIN.editor.setTextCursor(cur)
    try:
        _WIN._sync_menu_enablement()
        _WIN._sync_editor_only_actions()
    except Exception:
        pass
    if getattr(_WIN, "ribbon_bar", None) is not None:
        _WIN.ribbon_bar.setVisible(True)
        _WIN.ribbon_bar.select_category(0)
        pump(_APP, 0.05)


def test_ribbon_buttons_are_same_qaction_as_menu() -> None:
    _seed()
    missing = []
    for aid, title, label in _SHARED:
        _p, _h, act = _menu_action(title, label)
        bound = (_WIN._ribbon_qactions or {}).get(aid)
        if bound is not act:
            missing.append(f"{aid}: map={bound!r} menu={act!r}")
            continue
        btns = _WIN.ribbon_bar.buttons(aid)
        assert btns, f"kein Ribbon-Button {aid}"
        da = btns[0].defaultAction()
        if da is not act:
            missing.append(f"{aid}: defaultAction={da!r} menu={act!r}")
    assert not missing, "Ribbon ≠ Pulldown-QAction:\n" + "\n".join(missing)


def test_qtest_mouseclick_ribbon_and_menu_fire_same_action() -> None:
    _seed()
    _p, host, act = _menu_action("Bearbeiten", "Fett")
    btns = _WIN.ribbon_bar.buttons("bold")
    assert btns
    tb = btns[0]
    assert act.isEnabled()
    hits = {"n": 0}

    def _hit(*_a, **_k):
        hits["n"] += 1

    act.triggered.connect(_hit)
    try:
        QTest.mouseClick(tb, Qt.MouseButton.LeftButton)
        pump(_APP, 0.1)
        assert hits["n"] >= 1, f"Ribbon-Klick Fett ohne QAction.triggered ({hits['n']})"
        hits["n"] = 0
        assert mouse_click_menu_action(_APP, host, act)
        pump(_APP, 0.1)
        assert hits["n"] >= 1, f"Pulldown-Klick Fett ohne QAction.triggered ({hits['n']})"
    finally:
        try:
            act.triggered.disconnect(_hit)
        except Exception:
            pass
    html = _WIN.editor.document().toHtml().lower()
    assert "bold" in html or "font-weight" in html or _WIN.editor.selection_font_bold()


def test_classic_menu_one_column_still_applies() -> None:
    _seed()
    menu = find_menubar_menu(_WIN, "Bearbeiten")
    assert menu is not None
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
    for path, _h, act in iter_leaf_actions(menu, "Bearbeiten"):
        geo = menu.actionGeometry(act)
        if geo.isValid() and geo.x() > rect.width():
            overflow.append(f"{path} x={geo.x()} w={rect.width()}")
    menu.hide()
    assert not overflow, "Classic-Menü zweite Spalte:\n" + "\n".join(overflow[:8])


def test_combined_chrome_both_visible_by_default() -> None:
    assert _WIN.menuBar().isVisible()
    assert _WIN.ribbon_bar.isVisible()
    _p, _h, act = _menu_action("Bearbeiten", "Aufzählungszeichen")
    assert _WIN.ribbon_bar.qaction("bullet_list") is act
