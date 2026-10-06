"""Eine Ansicht: Menüs/Ribbon immer sichtbar, ausgegraut wenn nicht anwendbar."""

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
    load_state,
    pump,
)
from instantlensdoc.ui.menu_click import find_menubar_menu, iter_leaf_actions  # noqa: E402
from instantlensdoc.ui.word_ribbon import (  # noqa: E402
    REASON_FONT,
    REASON_FONT_PDF,
    REASON_MAIL,
    REASON_PAGE,
)


_APP = None
_WIN = None
_TD = None
_FIXTURES = None


def setup_module() -> None:
    global _APP, _WIN, _FIXTURES, _TD
    install_headless_env()
    _TD = tempfile.TemporaryDirectory(prefix="ild-view-caps-2665-")
    _FIXTURES = build_fixtures(Path(_TD.name))
    _APP, _WIN = create_main_window()


def teardown_module() -> None:
    global _WIN, _TD
    try:
        if _WIN is not None:
            _WIN.hide()
    except Exception:
        pass
    _WIN = None
    if _TD is not None:
        _TD.cleanup()


def _leaf(title: str, label: str):
    menu = find_menubar_menu(_WIN, title)
    assert menu is not None, f"Menü {title} fehlt"
    for path, host, act in iter_leaf_actions(menu, title):
        text = (act.text() or "").replace("&", "").strip()
        if text == label:
            return path, host, act
    raise AssertionError(f"{title}: {label} nicht gefunden")


def _select_dtp_kind(kind: str) -> bool:
    pane = _WIN.dtp_pane
    scene = pane.scene
    try:
        editing = pane.editing_item() if hasattr(pane, "editing_item") else None
        if editing is not None and hasattr(editing, "end_edit"):
            editing.end_edit()
    except Exception:
        pass
    scene.clearSelection()
    for it in list(scene.items()):
        try:
            it.setSelected(False)
        except Exception:
            pass
    found = None
    for it in scene._items.values():
        if getattr(it.frame, "kind", "") == kind:
            found = it
            break
    if found is None:
        return False
    found.setSelected(True)
    pump(_APP, 0.05)
    _WIN._on_dtp_selection_enablement()
    kinds = [getattr(fr, "kind", "") for fr in _WIN._dtp_selected_frames()]
    return kind in kinds and "text" in kinds if kind == "text" else (kind in kinds and "text" not in kinds)


def test_font_enabled_on_txt_and_docx() -> None:
    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.1)
    _WIN._sync_menu_enablement()
    caps = _WIN._view_capability_state()
    assert caps["font"] is True
    assert caps["mail_merge"] is True
    assert caps["page"] is True
    _p, _h, fett = _leaf("Bearbeiten", "Fett")
    assert fett.isEnabled()
    assert _WIN.ribbon_bar.is_enabled("font")
    assert _WIN.ribbon_bar.is_enabled("font_color")
    assert _WIN.ribbon_bar.is_enabled("scan_import")
    load_state(_WIN, _APP, "docx", _FIXTURES)
    pump(_APP, 0.15)
    _WIN._sync_menu_enablement()
    assert _WIN._view_capability_state()["font"] is True
    assert _WIN.ribbon_bar.is_enabled("bold")


def test_font_gray_on_image_pdf_tooltip_ocr() -> None:
    load_state(_WIN, _APP, "pdf20", _FIXTURES)
    pump(_APP, 0.25)
    _WIN._sync_menu_enablement()
    caps = _WIN._view_capability_state()
    assert caps["font"] is False
    assert caps["pdf"] is True
    assert caps["page"] is True
    assert caps["mail_merge"] is False
    _p, _h, fett = _leaf("Bearbeiten", "Fett")
    assert not fett.isEnabled()
    tip = fett.toolTip() or ""
    assert REASON_FONT_PDF in tip or "OCR" in tip
    assert not _WIN.ribbon_bar.is_enabled("font")
    assert not _WIN.ribbon_bar.is_enabled("font_color")
    assert not _WIN.ribbon_bar.is_enabled("bold")
    rtip = _WIN.ribbon_bar._actions["font"].toolTip() or ""
    assert "OCR" in rtip
    assert _WIN.ribbon_bar.is_enabled("page_layout")
    assert _WIN.ribbon_bar.is_enabled("page_margins")
    assert not _WIN.ribbon_bar.is_enabled("mail_merge")
    mtip = _WIN.ribbon_bar._actions["mail_merge"].toolTip() or ""
    assert REASON_MAIL.split("(")[0].strip() in mtip or "Seriendruck" in mtip
    assert _WIN.ribbon_bar.is_enabled("scan_import")
    assert _WIN.ribbon_bar.is_enabled("dtp_layout")


def test_dtp_text_frame_enables_font_on_pdf() -> None:
    from instantlensdoc.dtp.model import DtpDocument

    load_state(_WIN, _APP, "pdf20", _FIXTURES)
    pump(_APP, 0.2)
    try:
        if getattr(_WIN, "doc", None) is not None:
            _WIN.doc.dirty = False
        if hasattr(_WIN.dtp_pane, "clear_dirty"):
            _WIN.dtp_pane.clear_dirty()
    except Exception:
        pass
    _WIN.dtp_pane.set_document(DtpDocument.sample("A5"))
    try:
        _WIN.dtp_pane.clear_dirty()
    except Exception:
        pass
    _WIN._dtp_tools_on = True
    _WIN.dtp_pane.show()
    _WIN.dtp_pane.raise_()
    pump(_APP, 0.1)
    _WIN._sync_menu_enablement()
    assert _WIN._layout_mode_active()
    assert _select_dtp_kind("image") or _select_dtp_kind("shape")
    caps = _WIN._view_capability_state()
    assert caps["font"] is False, caps
    assert not _WIN.ribbon_bar.is_enabled("font")
    assert _select_dtp_kind("text")
    caps = _WIN._view_capability_state()
    assert caps["font"] is True
    assert _WIN.ribbon_bar.is_enabled("bold")
    assert _WIN.ribbon_bar.is_enabled("font")
    assert _select_dtp_kind("image") or _select_dtp_kind("shape")
    assert _WIN._view_capability_state()["font"] is False
    try:
        _WIN.dtp_pane.clear_dirty()
    except Exception:
        pass
    _WIN.dtp_pane.hide()
    _WIN._dtp_tools_on = False
    _WIN._sync_menu_enablement()


def test_font_after_ocr_word_suite() -> None:
    load_state(_WIN, _APP, "pdf20", _FIXTURES)
    pump(_APP, 0.2)
    assert not _WIN._view_capability_state()["font"]
    ok = _WIN.open_ocr_result(
        text="OCR-Text nach Word-Suite für Schrift.",
        title="Word-Suite — Enablement",
        auto_format=False,
    )
    assert ok
    pump(_APP, 0.2)
    caps = _WIN._view_capability_state()
    assert caps["font"] is True
    assert caps["mail_merge"] is True
    assert _WIN.ribbon_bar.is_enabled("font")
    assert _WIN.ribbon_bar.is_enabled("font_color")
    _p, _h, fett = _leaf("Bearbeiten", "Fett")
    assert fett.isEnabled()


def test_never_hide_menus_or_ribbon_groups() -> None:
    load_state(_WIN, _APP, "pdf20", _FIXTURES)
    pump(_APP, 0.2)
    _WIN._sync_menu_enablement()
    for title in ("Bearbeiten", "Absatz", "Seitenlayout", "Einfügen", "Ansicht"):
        menu = find_menubar_menu(_WIN, title)
        assert menu is not None, title
        assert menu.isEnabled(), f"{title} darf nicht deaktiviert/versteckt sein"
    rb = _WIN.ribbon_bar
    rb.select_tab("Layout")
    pump(_APP, 0.05)
    arr = getattr(rb, "_arrange_group", None)
    assert arr is not None
    assert not arr.isHidden()
    dtp = getattr(rb, "_dtp_tools_group", None)
    assert dtp is not None
    assert not dtp.isHidden()
    if rb._table_tab_index >= 0:
        assert rb._cat_buttons[rb._table_tab_index].isVisible()
    for aid in ("bold", "font", "font_color", "mail_merge", "page_layout", "scan_import"):
        assert aid in rb._actions
        btn = rb._actions[aid]
        assert btn is not None


def test_welcome_page_no_font_no_page() -> None:
    try:
        _WIN._leave_layout_mode()
    except Exception:
        pass
    _WIN.stack.setCurrentWidget(_WIN.welcome_page)
    pump(_APP, 0.05)
    _WIN._sync_menu_enablement()
    caps = _WIN._view_capability_state()
    assert caps["font"] is False
    assert caps["pdf"] is False
    assert caps["page"] is False
    assert caps["scan"] is True
    assert not _WIN.ribbon_bar.is_enabled("font")
    assert not _WIN.ribbon_bar.is_enabled("page_layout")
    assert _WIN.ribbon_bar.is_enabled("scan_import")
    tip = _WIN.ribbon_bar._actions["page_layout"].toolTip() or ""
    assert REASON_PAGE in tip or "Seite" in tip
    tipf = _WIN.ribbon_bar._actions["font"].toolTip() or ""
    assert REASON_FONT in tipf or "OCR" in tipf or "txt" in tipf
