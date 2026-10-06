"""DTP: Ribbon/Menü-Titel öffnet die Ansicht; Speichern/Nicht speichern/Abbrechen."""

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
from instantlensdoc.ui.menu_click import find_menubar_menu  # noqa: E402
from PySide6.QtWidgets import QDialog, QMessageBox, QWidget  # noqa: E402


_APP = None
_WIN = None
_TD = None
_PDF = None
_REC = None


def setup_module() -> None:
    global _APP, _WIN, _TD, _PDF, _REC
    install_headless_env()
    _TD = tempfile.TemporaryDirectory(prefix="ild-dtp-2661-")
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


def _clear_document_dirty() -> None:
    doc = getattr(_WIN, "doc", None)
    if doc is not None:
        doc.dirty = False
        if getattr(doc, "path", None):
            try:
                _WIN._mark_unsaved(doc.path, False)
            except Exception:
                pass
    pv = getattr(_WIN, "pdf_view", None)
    store = getattr(pv, "store", None) if pv is not None else None
    if store is not None:
        store.dirty = False
    if pv is not None and hasattr(pv, "_sidecar_save_pending"):
        try:
            pv._sidecar_save_pending = False
        except Exception:
            pass
    try:
        _WIN._update_unsaved_status()
    except Exception:
        pass


def _reload_pdf() -> None:
    _WIN.open_path(str(_PDF))
    pump(_APP, 0.2)
    _clear_document_dirty()
    if _WIN._layout_mode_active():
        _WIN.dtp_pane.clear_dirty()
        _WIN._leave_layout_mode()
    pump(_APP, 0.05)
    assert not _WIN._document_is_dirty()


def _checked_ribbon_title() -> str:
    for btn in _WIN.ribbon_bar._cat_buttons:
        if btn.isChecked():
            return (btn.text() or "").strip()
    return ""


def test_ribbon_dtp_tab_opens_pane_for_pdf() -> None:
    _reload_pdf()
    assert _WIN.stack.currentWidget() is _WIN.pdf_view
    _WIN.ribbon_bar.select_tab("Start")
    pump(_APP, 0.05)
    assert _checked_ribbon_title() == "Start"
    _WIN.ribbon_bar.select_tab("DTP")
    pump(_APP, 0.05)
    assert _WIN.stack.currentWidget() is _WIN.pdf_view
    assert _WIN._layout_mode_active()
    assert _WIN.dtp_pane.isVisible()
    assert _WIN._layout_mode_action.isChecked()
    assert _WIN._dtp_view_action.isChecked()
    assert _checked_ribbon_title() == "Start"
    titles = [
        (b.text() or "").strip()
        for b in _WIN.ribbon_bar._cat_buttons
        if b.isVisible()
    ]
    for need in ("Start", "Einfügen", "Layout"):
        assert need in titles, need


def test_menubar_dtp_about_to_show_opens_pane() -> None:
    _reload_pdf()
    assert not _WIN._layout_mode_active()
    menu = find_menubar_menu(_WIN, "DTP")
    assert menu is not None
    texts = [a.text() for a in menu.actions() if not a.isSeparator()]
    assert texts[0] == "DTP-Werkzeuge"
    menu.aboutToShow.emit()
    pump(_APP, 0.05)
    assert _WIN._layout_mode_active()
    assert _WIN.stack.currentWidget() is _WIN.pdf_view
    assert _WIN.dtp_pane.isVisible()


def test_unsaved_prompt_german_buttons() -> None:
    box = _WIN._unsaved_prompt_box(title="Layout-Modus", name="sample.pdf")
    assert box.button(QMessageBox.Save).text() == "Speichern"
    assert box.button(QMessageBox.Discard).text() == "Nicht speichern"
    assert box.button(QMessageBox.Cancel).text() == "Abbrechen"


def test_dirty_document_cancel_aborts_enter(monkeypatch) -> None:
    _reload_pdf()
    monkeypatch.setattr(_WIN, "_document_is_dirty", lambda: True)
    seen: dict[str, str] = {}

    def fake_exec(self, *a, **k):
        seen["title"] = self.windowTitle()
        save_btn = self.button(QMessageBox.Save)
        seen["save"] = save_btn.text() if save_btn is not None else ""
        return QMessageBox.Cancel

    monkeypatch.setattr(QMessageBox, "exec", fake_exec)
    monkeypatch.setattr(QDialog, "exec", fake_exec)
    assert _WIN._enter_layout_mode() is False
    assert not _WIN._layout_mode_active()
    assert not _WIN.dtp_pane.isVisible()
    assert _WIN.stack.currentWidget() is _WIN.pdf_view
    assert seen.get("save") == "Speichern"
    assert seen.get("title") == "Layout-Modus"


def test_ribbon_dtp_cancel_restores_previous_tab(monkeypatch) -> None:
    _reload_pdf()
    _WIN.ribbon_bar.select_tab("Start")
    pump(_APP, 0.05)
    monkeypatch.setattr(_WIN, "_document_is_dirty", lambda: True)
    monkeypatch.setattr(QMessageBox, "exec", lambda self, *a, **k: QMessageBox.Cancel)
    monkeypatch.setattr(QDialog, "exec", lambda self, *a, **k: QMessageBox.Cancel)
    _WIN.ribbon_bar.select_tab("DTP")
    pump(_APP, 0.05)
    assert not _WIN._layout_mode_active()
    assert _checked_ribbon_title() == "Start"


def test_dirty_document_discard_enters_dtp(monkeypatch) -> None:
    _reload_pdf()
    monkeypatch.setattr(_WIN, "_document_is_dirty", lambda: True)
    monkeypatch.setattr(QMessageBox, "exec", lambda self, *a, **k: QMessageBox.Discard)
    monkeypatch.setattr(QDialog, "exec", lambda self, *a, **k: QMessageBox.Discard)
    assert _WIN._enter_layout_mode() is True
    assert _WIN._layout_mode_active()
    assert _WIN.dtp_pane.isVisible()
    assert _WIN.stack.currentWidget() is _WIN.pdf_view


def test_dtp_help_from_menu_and_f1(monkeypatch) -> None:
    from PySide6.QtGui import QAction

    from instantlensdoc.dtp import help_dialog as hd

    _reload_pdf()
    assert _WIN._enter_layout_mode() is True
    seen: list[str] = []

    def fake_exec(self):
        seen.append(self.objectName())
        seen.append(self.windowTitle())
        return 0

    monkeypatch.setattr(hd.DtpHelpDialog, "exec", fake_exec)
    _WIN._show_dtp_help()
    assert "ildDtpHelpDialog" in seen
    assert "DTP-Hilfe" in seen
    seen.clear()
    _WIN._show_help_dialog()
    assert "DTP-Hilfe" in seen
    act = _WIN.findChild(QAction, "actDtpHelp")
    assert act is not None
    seen.clear()
    act.trigger()
    assert "ildDtpHelpDialog" in seen
    from_hilfe = _WIN.findChild(QAction, "actDtpHelpFromHilfe")
    assert from_hilfe is not None
    seen.clear()
    from_hilfe.trigger()
    assert "ildDtpHelpDialog" in seen
    help_btn = _WIN.dtp_pane.props_panel.findChild(QWidget, "dtpPropHelp")
    assert help_btn is not None
    seen.clear()
    help_btn.click()
    pump(_APP, 0.02)
    assert "ildDtpHelpDialog" in seen


def test_dirty_layout_cancel_stays_in_dtp(monkeypatch) -> None:
    _reload_pdf()
    assert _WIN._enter_layout_mode() is True
    _WIN.dtp_pane.mark_dirty()
    monkeypatch.setattr(QMessageBox, "exec", lambda self, *a, **k: QMessageBox.Cancel)
    monkeypatch.setattr(QDialog, "exec", lambda self, *a, **k: QMessageBox.Cancel)
    assert _WIN._leave_layout_mode() is False
    assert _WIN._layout_mode_active()
    assert _WIN.dtp_pane.is_dirty()


def test_dirty_layout_discard_leaves_dtp(monkeypatch) -> None:
    _reload_pdf()
    assert _WIN._enter_layout_mode() is True
    _WIN.dtp_pane.mark_dirty()
    monkeypatch.setattr(QMessageBox, "exec", lambda self, *a, **k: QMessageBox.Discard)
    monkeypatch.setattr(QDialog, "exec", lambda self, *a, **k: QMessageBox.Discard)
    assert _WIN._leave_layout_mode() is True
    assert not _WIN._layout_mode_active()
    assert not _WIN.dtp_pane.is_dirty()
    assert _WIN.stack.currentWidget() is _WIN.pdf_view


def test_dtp_embedded_keeps_word_menus_hides_own_chrome() -> None:
    _reload_pdf()
    assert _WIN._enter_layout_mode() is True
    assert _WIN._layout_mode_active()
    assert _WIN.stack.currentWidget() is _WIN.pdf_view
    assert _WIN.stack.currentWidget() is not _WIN.dtp_pane
    assert _WIN.dtp_pane.isVisible()
    assert getattr(_WIN.dtp_pane, "_word_embedded", False) is True
    assert _WIN.dtp_pane.h_ruler.isVisible()
    assert _WIN.dtp_pane.view.isVisible()
    assert not _WIN.dtp_pane.menu_bar.isVisible()
    assert not _WIN.dtp_pane.icon_bar.isVisible()
    assert not _WIN.dtp_pane.status_bar.isVisible()
    for title in ("Datei", "Bearbeiten", "Ansicht", "DTP"):
        menu = find_menubar_menu(_WIN, title)
        assert menu is not None, title
    assert find_menubar_menu(_WIN, "DTP").objectName() == "menuDtp"
    titles = [
        (a.text() or "").replace("&", "")
        for a in _WIN.menuBar().actions()
        if (a.text() or "").strip()
    ]
    assert "DTP" in titles
    assert "Datei" in titles


def test_dtp_properties_merge_into_one_right_column() -> None:
    _reload_pdf()
    _WIN._toggle_right_toolbox(True)
    pump(_APP, 0.05)
    tools = _WIN.ink_tools_pane
    assert tools is not None
    assert tools.objectName() == "ildRightToolbox"
    assert tools.isVisible()
    assert _WIN._enter_layout_mode() is True
    pump(_APP, 0.05)
    host = tools.dtp_host
    props = _WIN.dtp_pane.props_panel
    layers = _WIN.dtp_pane.side_panel
    assert host is not None
    assert host.isVisible()
    assert host.isAncestorOf(props)
    assert host.isAncestorOf(layers)
    assert props.isVisible()
    assert layers.isVisible()
    assert tools.isAncestorOf(props)
    assert tools.findChild(QWidget, "inkTool_brush") is not None
    assert props.findChild(QWidget, "dtpPropFill") is not None
    assert props.findChild(QWidget, "dtpPropFontColor") is not None
    assert props.findChild(QWidget, "dtpPropTool_select") is not None
    assert props.findChild(QWidget, "dtpPropHelp") is not None
    assert _WIN._doc_host.isAncestorOf(_WIN.dtp_pane)
    _WIN.dtp_pane.clear_dirty()
    assert _WIN._leave_layout_mode() is True
    pump(_APP, 0.05)
    assert not host.isVisible()
