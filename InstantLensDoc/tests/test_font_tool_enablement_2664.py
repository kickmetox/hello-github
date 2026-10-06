"""Menüs bleiben sichtbar; Schriftwerkzeuge grauen mit Tooltip (Chrome-Policy)."""

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
    build_fixtures,
    create_main_window,
    install_headless_env,
    pump,
)
from instantlensdoc.ui.chrome_actions import (  # noqa: E402
    FONT_TOOL_DISABLE_REASON,
    font_tools_allowed,
    is_font_tool_label,
)
from instantlensdoc.ui.menu_click import find_menubar_menu  # noqa: E402


_APP = None
_WIN = None
_TD = None
_FIXTURES = None


def setup_module() -> None:
    global _APP, _WIN, _TD, _FIXTURES
    install_headless_env()
    _TD = tempfile.TemporaryDirectory(prefix="ild-font-enable-2664-")
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


def test_font_tools_policy_table() -> None:
    assert is_font_tool_label("Schriftfarbe…")
    assert is_font_tool_label("Fett")
    assert is_font_tool_label("&Schriftart…")
    ok, reason = font_tools_allowed(
        is_editor=False, is_dtp=False, is_pdf=True, has_ocr=False
    )
    assert not ok
    assert "OCR" in reason
    ok, _r = font_tools_allowed(
        is_editor=False, is_dtp=False, is_pdf=True, has_ocr=True
    )
    assert ok
    ok, _r = font_tools_allowed(
        is_editor=True, is_dtp=False, is_pdf=False, has_ocr=False
    )
    assert ok
    ok, _r = font_tools_allowed(
        is_editor=False, is_dtp=True, is_pdf=False, has_ocr=False
    )
    assert ok


def _font_act(label: str):
    menu = find_menubar_menu(_WIN, "Bearbeiten")
    assert menu is not None
    for a in menu.actions():
        if (a.text() or "").replace("&", "").strip().startswith(label):
            return a
    raise AssertionError(f"fehlt: {label}")


def _assert_menus_visible() -> None:
    mb = _WIN.menuBar()
    titles = []
    for top in mb.actions():
        menu = top.menu() if hasattr(top, "menu") else None
        assert top.isVisible(), f"Menü unsichtbar: {top.text()}"
        assert top.isEnabled(), f"Menü-Titel disabled: {top.text()}"
        if menu is not None:
            # Titel = QAction; QMenu.isVisible() wäre das Popup.
            assert menu.isEnabled()
            titles.append((menu.title() or top.text() or "").replace("&", ""))
    for need in ("Bearbeiten", "Absatz", "Seitenlayout", "PDF", "DTP"):
        assert need in titles, f"Top-Level fehlt/versteckt: {need} in {titles}"


def _open_pdf() -> None:
    _WIN.open_path(str(_FIXTURES["pdf20"]))
    pump(_APP, 0.35)
    _WIN._sync_menu_enablement()


def _open_empty() -> None:
    _WIN.new_doc("empty")
    pump(_APP, 0.12)
    doc = getattr(_WIN, "doc", None)
    if doc is not None:
        try:
            doc.text = _WIN.editor.toPlainText()
        except Exception:
            pass
        doc.dirty = False
    _WIN._sync_menu_enablement()


def _open_docx() -> None:
    _WIN.open_path(str(_FIXTURES["docx"]))
    pump(_APP, 0.35)
    _WIN._sync_menu_enablement()


def test_menus_stay_visible_on_pdf_font_tools_gray() -> None:
    _open_pdf()
    _assert_menus_visible()
    fett = _font_act("Fett")
    farbe = _font_act("Schriftfarbe")
    assert not fett.isEnabled()
    assert not farbe.isEnabled()
    tip = (farbe.toolTip() or "") + (fett.toolTip() or "")
    assert FONT_TOOL_DISABLE_REASON in tip or "OCR" in tip


def test_font_tools_enabled_on_txt_and_after_ocr() -> None:
    _open_empty()
    _WIN.editor.setPlainText("Klartext für Schrift.")
    _WIN._sync_menu_enablement()
    assert _WIN._editor_document_active()
    assert _font_act("Fett").isEnabled()
    assert _font_act("Schriftfarbe").isEnabled()

    _open_docx()
    assert _WIN._editor_document_active()
    assert _font_act("Fett").isEnabled()
    assert _font_act("Schriftart").isEnabled()

    _open_pdf()
    assert not _WIN._editor_document_active()
    assert not _font_act("Fett").isEnabled(), "Fett auf PDF ohne OCR muss disabled sein"

    pdf = Path(_FIXTURES["pdf20"])
    sidecar = pdf.parent / f"{pdf.stem}.ildocr.txt"
    sidecar.write_text("OCR Sidecar", encoding="utf-8")
    try:
        _WIN._sync_menu_enablement()
        assert _WIN._current_has_ocr()
        assert _font_act("Fett").isEnabled(), "Fett nach OCR-Sidecar noch disabled"
        assert _font_act("Schriftfarbe").isEnabled()
        tip = _font_act("Fett").toolTip() or ""
        assert FONT_TOOL_DISABLE_REASON not in tip
    finally:
        sidecar.unlink(missing_ok=True)
    _WIN._last_ocr_pdf_path = None
    _WIN._sync_menu_enablement()
    assert not _font_act("Fett").isEnabled()

    ok = _WIN.open_ocr_result(
        text="OCR Absatz zum Formatieren.",
        title="Word-Suite — OCR Farbe",
        auto_format=False,
    )
    assert ok
    pump(_APP, 0.2)
    _WIN._sync_menu_enablement()
    assert _WIN._editor_document_active()
    assert _font_act("Fett").isEnabled(), "Fett nach OCR noch disabled"
    assert _font_act("Schriftart").isEnabled()
    assert _font_act("Schriftfarbe").isEnabled()


def test_font_tools_enabled_in_dtp() -> None:
    _open_empty()
    pane = getattr(_WIN, "dtp_pane", None)
    if pane is not None:
        try:
            pane.clear_dirty()
        except Exception:
            pass
    assert _WIN._enter_layout_mode()
    pump(_APP, 0.1)
    _WIN._sync_menu_enablement()
    assert _WIN._layout_mode_active()
    _assert_menus_visible()
    assert _font_act("Fett").isEnabled()
    assert _font_act("Schriftfarbe").isEnabled()
