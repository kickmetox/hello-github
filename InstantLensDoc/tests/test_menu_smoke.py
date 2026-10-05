"""Smoke: jede Menü-/Ribbon-/Leisten-Aktion in allen Dokumentzuständen — 2.6.54."""

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
from menu_smoke_lib import (  # noqa: E402
    DIALOG_ALLOWLIST_IDS,
    build_fixtures,
    create_main_window,
    current_state_tag,
    install_headless_env,
    install_qt_hooks,
    inventory_window,
    load_state,
    missing_ribbon_handlers,
    pump,
    should_skip_trigger,
    trigger_row,
)

_APP = None
_WIN = None
_FIXTURES = None
_TD = None
_RESTORE = None
_HOOKS: list = []


def setup_module() -> None:
    global _APP, _WIN, _FIXTURES, _TD, _RESTORE
    install_headless_env()
    _TD = tempfile.TemporaryDirectory(prefix="ild-pytest-menu-")
    _FIXTURES = build_fixtures(Path(_TD.name))
    _RESTORE = install_qt_hooks(_HOOKS)
    _APP, _WIN = create_main_window()


def teardown_module() -> None:
    global _WIN, _TD, _RESTORE
    try:
        if _WIN is not None:
            _WIN.close()
    except Exception:
        pass
    if _RESTORE:
        _RESTORE()
    if _TD is not None:
        _TD.cleanup()


def test_inventory_not_empty() -> None:
    rows = inventory_window(_WIN)
    menus = [r for r in rows if r["kind"] == "menu"]
    assert len(menus) >= 80, f"zu wenige Menüeinträge: {len(menus)}"
    kinds = {r["kind"] for r in rows}
    for need in ("menu", "ribbon", "editor-toolbar", "pdf-toolbar"):
        assert need in kinds, f"Inventar ohne {need}"


def test_ribbon_handlers_wired() -> None:
    missing = missing_ribbon_handlers(_WIN)
    assert missing == [], f"Ribbon ohne Slot: {missing}"


def test_no_menu_stubs() -> None:
    rows = inventory_window(_WIN)
    stubs = [r["path"] for r in rows if r.get("stub") and r["kind"] in ("menu", "ribbon")]
    assert stubs == [], "Stub-Menüeinträge: " + "; ".join(stubs)


def test_no_unwired_menu_slots() -> None:
    rows = inventory_window(_WIN)
    empty = [
        r["path"]
        for r in rows
        if r["kind"] == "menu" and int(r.get("receivers") or 0) == 0
    ]
    assert empty == [], "Menü ohne Slot: " + "; ".join(empty)


def _trigger_state(state: str) -> None:
    load_state(_WIN, _APP, state, _FIXTURES)
    pump(_APP, 0.15)
    rows = inventory_window(_WIN)
    errors = []
    stubs = []
    for row in rows:
        if row.get("kind") not in {
            "menu",
            "ribbon",
            "editor-toolbar",
            "pdf-toolbar",
            "palette",
        }:
            continue
        if should_skip_trigger(row, state):
            continue
        out = trigger_row(_APP, _WIN, row, state)
        if out.get("skipped"):
            continue
        if out.get("exc"):
            errors.append(f"{row.get('path')}: {out['exc'][:400]}")
        if out.get("stub") and row.get("kind") in ("menu", "ribbon"):
            stubs.append(row.get("path"))
        if out.get("hang"):
            errors.append(f"{row.get('path')}: Dialog hing")
        if out.get("no_slot"):
            errors.append(f"{row.get('path')}: kein Slot")
        if current_state_tag(_WIN, _FIXTURES) != state:
            try:
                load_state(_WIN, _APP, state, _FIXTURES)
            except Exception:
                pass
        aid = row.get("ribbon_id") or row.get("palette_id") or ""
        if aid in DIALOG_ALLOWLIST_IDS:
            pass
    assert not stubs, "Stubs: " + "; ".join(stubs[:20])
    assert not errors, "Ausnahmen:\n" + "\n---\n".join(errors[:25])


EDITOR_ONLY_LABELS = (
    "Zeilenabstand 1,5",
    "Zeilenabstand 1,15 (Standard)",
    "Absatz links",
    "Absatz zentriert",
    "Absatz rechts",
    "Absatz Blocksatz",
    "Fett",
    "Kursiv",
    "Unterstrichen",
    "Einrückung erhöhen",
    "Einrückung verringern",
    "Seitenlayout…",
    "Laufweite +50 (Tracking)",
    "Durchschuss 1,5 (Leading)",
    "Automatische Formatierung",
)


def _find_actions_by_text(win, text: str):
    from PySide6.QtGui import QAction

    want = (text or "").replace("&", "")
    return [
        a
        for a in win.findChildren(QAction)
        if (a.text() or "").replace("&", "") == want
    ]


def test_editor_only_disabled_on_pdf() -> None:
    load_state(_WIN, _APP, "pdf20", _FIXTURES)
    pump(_APP, 0.2)
    _WIN._sync_menu_enablement()
    missing = []
    still_on = []
    for label in EDITOR_ONLY_LABELS:
        found = _find_actions_by_text(_WIN, label)
        if not found:
            missing.append(label)
            continue
        if any(a.isEnabled() for a in found):
            still_on.append(label)
    assert not missing, "Menüeinträge fehlen: " + ", ".join(missing)
    assert not still_on, "Editor-only bleibt bei PDF aktiv: " + ", ".join(still_on)
    rows = inventory_window(_WIN)
    eo_on = [
        r["path"]
        for r in rows
        if r.get("editor_only") and r.get("enabled") and r.get("kind") in ("menu", "ribbon", "editor-toolbar")
    ]
    assert not eo_on, "Inventar markiert Editor-only nicht als PDF-disabled: " + "; ".join(eo_on[:12])


def test_line_spacing_does_not_switch_pdf_tab() -> None:
    """Slot selbst wechselt den Stack nicht — Tab-Guard bleibt bei C."""
    load_state(_WIN, _APP, "pdf20", _FIXTURES)
    pump(_APP, 0.2)
    assert _WIN.stack.currentWidget() is _WIN.pdf_view
    _WIN._set_paragraph_line_spacing(1.5)
    pump(_APP, 0.1)
    assert _WIN.stack.currentWidget() is _WIN.pdf_view


def test_editor_only_enabled_on_docx() -> None:
    from PySide6.QtGui import QAction

    load_state(_WIN, _APP, "docx", _FIXTURES)
    pump(_APP, 0.2)
    _WIN._sync_menu_enablement()
    found = None
    for act in _WIN.findChildren(QAction):
        if (act.text() or "").replace("&", "") == "Zeilenabstand 1,5":
            found = act
            break
    assert found is not None
    assert found.isEnabled()
    _trigger_state("none")


def test_trigger_empty() -> None:
    _trigger_state("empty")


def test_trigger_docx() -> None:
    _trigger_state("docx")


def test_trigger_pdf20() -> None:
    _trigger_state("pdf20")


def test_trigger_pdf500() -> None:
    _trigger_state("pdf500")
