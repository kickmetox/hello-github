"""Ein Menütitel-Klick: nur dieses Menü, keine Geschwister (PDF/Format/Absatz/Seitenlayout/Fenster)."""

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
    build_fixtures,
    create_main_window,
    install_headless_env,
    load_state,
)
from instantlensdoc.ui.menu_click import find_menubar_menu  # noqa: E402


_APP = None
_WIN = None
_TD = None
_FIXTURES = None
_REC = None

REPRO_TITLES = (
    "Datei",
    "Bearbeiten",
    "Ansicht",
    "Format",
    "Absatz",
    "Seitenlayout",
    "PDF",
    "DTP",
    "Extras",
    "Fenster",
    "Hilfe",
)


def setup_module() -> None:
    global _APP, _WIN, _TD, _FIXTURES, _REC
    install_headless_env()
    _TD = tempfile.TemporaryDirectory(prefix="ild-menu-excl-2667-")
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


def _hide_all_menus() -> None:
    from instantlensdoc.ui.menu_click import close_other_menus

    close_other_menus(None, menubar=_WIN.menuBar())
    pump(_APP, 0.05)


def _visible_menubar_titles() -> list[str]:
    out = []
    mb = _WIN.menuBar()
    for act in mb.actions():
        menu = act.menu() if hasattr(act, "menu") else None
        if menu is None:
            continue
        try:
            if menu.isVisible():
                title = (menu.title() or act.text() or "").replace("&", "").strip()
                out.append(title)
        except Exception:
            continue
    return out


def _click_title(title: str) -> QMenu:
    menu = find_menubar_menu(_WIN, title)
    assert menu is not None, f"Menü {title} fehlt"
    mb = _WIN.menuBar()
    mb.setVisible(True)
    hit = None
    for act in mb.actions():
        if act.menu() is menu:
            hit = act
            break
    assert hit is not None
    geo = mb.actionGeometry(hit)
    assert geo.isValid()
    QTest.mouseClick(mb, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, geo.center())
    pump(_APP, 0.12)
    return menu


def test_format_does_not_share_qaction_with_bearbeiten() -> None:
    fmt = find_menubar_menu(_WIN, "Format")
    edit = find_menubar_menu(_WIN, "Bearbeiten")
    assert fmt is not None and edit is not None
    fmt_fett = next(
        a
        for a in fmt.actions()
        if (a.text() or "").replace("&", "").strip() == "Fett"
    )
    edit_fett = next(
        a
        for a in edit.actions()
        if (a.text() or "").replace("&", "").strip() == "Fett"
    )
    assert fmt_fett is not edit_fett
    assert fmt_fett.property("ildMirrorOf") is edit_fett


def test_repro_titles_open_only_that_menu() -> None:
    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.08)
    _WIN.resize(1400, 900)
    pump(_APP, 0.08)
    failed = []
    for title in REPRO_TITLES:
        _hide_all_menus()
        _REC.events.clear()
        _click_title(title)
        vis = _visible_menubar_titles()
        extras = [t for t in vis if t != title]
        if extras:
            failed.append(f"{title} öffnete zusätzlich: {extras}")
        dlg = [e for e in _REC.events if e.get("kind") in ("dialog", "file", "message")]
        if dlg:
            failed.append(f"{title} öffnete Dialoge: {dlg[:4]}")
        _hide_all_menus()
    assert not failed, "\n".join(failed)


def test_stacked_popups_collapse_to_clicked_title() -> None:
    """Alle QMenus offen (Screenshot-Fall) → Klick Datei lässt nur Datei stehen."""
    mb = _WIN.menuBar()
    mb.setVisible(True)
    pump(_APP, 0.05)
    origin = mb.mapToGlobal(mb.rect().bottomLeft())
    for act in mb.actions():
        menu = act.menu() if hasattr(act, "menu") else None
        if menu is None:
            continue
        menu.popup(origin)
        menu.show()
    pump(_APP, 0.08)
    vis_after = _visible_menubar_titles()
    assert len(vis_after) <= 1, f"Stapel blieb stehen: {vis_after}"
    _click_title("Datei")
    vis = _visible_menubar_titles()
    extras = [t for t in vis if t != "Datei"]
    assert not extras, extras
    _hide_all_menus()


def test_sync_enablement_does_not_popup_menus() -> None:
    """Tab-Wechsel / Enablement darf keine Pulldowns aufklappen (Screenshot)."""
    _hide_all_menus()
    _WIN._sync_editor_only_actions()
    _WIN._sync_menu_enablement()
    pump(_APP, 0.08)
    vis = _visible_menubar_titles()
    assert not vis, f"Enablement öffnete Menüs: {vis}"
    _WIN.stack.currentChanged.emit(_WIN.stack.currentIndex())
    pump(_APP, 0.08)
    vis = _visible_menubar_titles()
    assert not vis, f"stack.currentChanged öffnete Menüs: {vis}"
    _hide_all_menus()


def test_menubar_action_geometries_do_not_overlap() -> None:
    _WIN.resize(1100, 800)
    host = getattr(_WIN, "_ild_menubar_host", None)
    if host is not None and hasattr(host, "_fit"):
        host._fit()
    pump(_APP, 0.08)
    mb = _WIN.menuBar()
    geos = []
    for act in mb.actions():
        g = mb.actionGeometry(act)
        if g.isValid() and g.width() > 0:
            geos.append(( (act.text() or "").replace("&", "").strip(), g ))
    overlap = []
    for i, (a, ga) in enumerate(geos):
        for b, gb in geos[i + 1 :]:
            if ga.intersects(gb):
                overlap.append(f"{a} ∩ {b}")
    assert not overlap, "Menütitel überlappen:\n" + "\n".join(overlap)
