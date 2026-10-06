"""Word-Suite: Absatz- + Seitenlayout-Menü — Mausklick feuert denselben Slot."""

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

from menu_effect_lib import DialogRecorder, pump  # noqa: E402
from menu_smoke_lib import (  # noqa: E402
    create_main_window,
    install_headless_env,
    load_state,
    build_fixtures,
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
_REC = None


def setup_module() -> None:
    global _APP, _WIN, _TD, _FIXTURES, _REC
    install_headless_env()
    _TD = tempfile.TemporaryDirectory(prefix="ild-ws-menu-2661-")
    _FIXTURES = build_fixtures(Path(_TD.name))
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


def _menu(title: str):
    menu = find_menubar_menu(_WIN, title)
    assert menu is not None, f"Menü {title} fehlt"
    return menu


def _leaf(title: str, label: str):
    menu = _menu(title)
    for path, host, act in iter_leaf_actions(menu, title):
        text = (act.text() or "").replace("&", "").strip()
        if text == label:
            return path, host, act
    raise AssertionError(f"{title}: {label} nicht gefunden")


def _seed_editor(text: str = "Hallo Absatz Ausrichtung Listen.") -> None:
    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.15)
    _WIN.editor.setPlainText(text)
    cur = _WIN.editor.textCursor()
    cur.setPosition(0)
    _WIN.editor.setTextCursor(cur)
    try:
        _WIN._sync_menu_enablement()
        _WIN._sync_editor_only_actions()
    except Exception:
        pass


def _click_fires(title: str, label: str) -> int:
    _path, host, act = _leaf(title, label)
    assert act.isEnabled(), f"{title} ▸ {label} disabled"
    hits = {"n": 0}

    def _hit(*_a, **_k):
        hits["n"] += 1

    act.triggered.connect(_hit)
    try:
        ok = mouse_click_menu_action(_APP, host, act)
        pump(_APP, 0.12)
    finally:
        try:
            act.triggered.disconnect(_hit)
        except Exception:
            pass
    assert ok, f"QTest.mouseClick {title} ▸ {label} ohne Geometrie"
    return hits["n"]


def test_absatz_and_seitenlayout_menus_exist() -> None:
    absatz = _menu("Absatz")
    seiten = _menu("Seitenlayout")
    assert absatz.objectName() == "menuAbsatz"
    assert seiten.objectName() == "menuSeitenlayout"
    labels_a = {
        (act.text() or "").replace("&", "").strip()
        for _p, _h, act in iter_leaf_actions(absatz, "Absatz")
    }
    labels_s = {
        (act.text() or "").replace("&", "").strip()
        for _p, _h, act in iter_leaf_actions(seiten, "Seitenlayout")
    }
    for need in (
        "Absatz…",
        "Absatz links",
        "Absatz zentriert",
        "Aufzählungszeichen",
        "Nummerierung",
    ):
        assert need in labels_a, f"Absatz-Menü fehlt {need}: {sorted(labels_a)}"
    for need in ("Seitenlayout…", "Hochformat", "Querformat", "A4"):
        assert need in labels_s, f"Seitenlayout-Menü fehlt {need}: {sorted(labels_s)}"


def test_absatz_menu_one_column() -> None:
    menu = _menu("Absatz")
    prepare_menu_for_clicks(menu)
    menu.popup(menu.parentWidget().mapToGlobal(menu.rect().topLeft()) if menu.parentWidget() else menu.pos())
    menu.show()
    pump(_APP, 0.08)
    rect = menu.rect()
    overflow = []
    for path, _h, act in iter_leaf_actions(menu, "Absatz"):
        geo = menu.actionGeometry(act)
        if geo.isValid() and geo.x() > rect.width():
            overflow.append(f"{path} x={geo.x()} w={rect.width()}")
    menu.hide()
    assert not overflow, "Absatz-Menü zweite Spalte:\n" + "\n".join(overflow[:8])


def test_qtest_mouseclick_alignment_and_bullets() -> None:
    _seed_editor("Hallo Absatz Ausrichtung Listen.")
    n = _click_fires("Absatz", "Absatz zentriert")
    assert n >= 1, f"Absatz zentriert triggered={n}"
    pump(_APP, 0.05)
    assert _WIN.editor.current_block_alignment() == "center"
    n = _click_fires("Absatz", "Aufzählungszeichen")
    assert n >= 1, f"Aufzählungszeichen triggered={n}"
    pump(_APP, 0.05)
    line = _WIN.editor.textCursor().block().text()
    assert "\u2022" in line or "•" in line or line.lstrip().startswith("-"), line


def test_qtest_mouseclick_seitenlayout_dialog_and_a4() -> None:
    _seed_editor()
    _REC.events.clear()
    n = _click_fires("Seitenlayout", "Seitenlayout…")
    assert n >= 1
    pump(_APP, 0.15)
    assert _REC.events, "Seitenlayout… Mausklick ohne Dialog"
    n = _click_fires("Seitenlayout", "A4")
    assert n >= 1
    pump(_APP, 0.08)
    lay = _WIN.editor.page_layout()
    assert lay is not None
    assert str(getattr(lay, "preset", "")).replace(" ", "").lower() in ("a4", "dina4")


def test_disabled_on_pdf_enabled_on_word_suite() -> None:
    load_state(_WIN, _APP, "pdf20", _FIXTURES)
    pump(_APP, 0.25)
    _WIN._sync_menu_enablement()
    _WIN._sync_editor_only_actions()
    disabled = []
    for title, label in (
        ("Absatz", "Absatz zentriert"),
        ("Absatz", "Aufzählungszeichen"),
        ("Seitenlayout", "Seitenlayout…"),
        ("Seitenlayout", "A4"),
    ):
        _p, _h, act = _leaf(title, label)
        if act.isEnabled():
            disabled.append(f"{title} ▸ {label} noch enabled auf PDF")
    assert not disabled, "\n".join(disabled)

    ok = _WIN.open_ocr_result(
        text="EINLEITUNG\n\nFliesstext Absatz zum Ausrichten.\n\n- Listenpunkt",
        title="Word-Suite — Absatz/Liste",
        auto_format=False,
    )
    assert ok
    pump(_APP, 0.2)
    _WIN._sync_menu_enablement()
    _WIN._sync_editor_only_actions()
    for title, label in (
        ("Absatz", "Absatz links"),
        ("Absatz", "Nummerierung"),
        ("Seitenlayout", "Hochformat"),
    ):
        _p, _h, act = _leaf(title, label)
        assert act.isEnabled(), f"{title} ▸ {label} disabled auf Word-Suite"
    n = _click_fires("Absatz", "Absatz rechts")
    assert n >= 1
    pump(_APP, 0.05)
    assert _WIN.editor.current_block_alignment() == "right"
