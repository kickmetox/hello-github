"""DTP teilt Druckermarken mit PDF; kein Word-Editor-Overlay."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu

from instantlensdoc.core.app_settings import (
    get_show_printer_marks,
    get_show_satzspiegel,
    set_show_printer_marks,
    set_show_satzspiegel,
)
from instantlensdoc.dtp.model import DtpDocument
from instantlensdoc.dtp.print_marks import (
    WORD_EDITOR_OVERLAY_TAGS,
    crop_and_registration_marks,
    printer_mark_size,
)


def test_crop_geometry_has_l_marks_and_registration() -> None:
    mark, gap = printer_mark_size(200.0, 300.0)
    assert 8.0 <= mark <= 18.0
    assert gap == 2.0
    lines, circle = crop_and_registration_marks(40.0, 40.0, 200.0, 300.0)
    assert len(lines) == 10  # 4 Ecken × 2 + Kreuz
    assert circle is not None
    assert circle.x == 40.0 + 100.0
    assert circle.y < 40.0


def test_dtp_printer_marks_follow_shared_setting(qapp) -> None:
    prev_m = get_show_printer_marks()
    prev_s = get_show_satzspiegel()
    try:
        set_show_printer_marks(False)
        set_show_satzspiegel(False)
        from instantlensdoc.dtp.canvas import DtpPane

        pane = DtpPane(doc=DtpDocument.sample("A5"))
        pane.show()
        qapp.processEvents()
        assert pane.scene.printer_mark_items() == []
        act = pane.findChild(QAction, "dtpPrinterMarksAction")
        assert act is not None
        assert act.isCheckable()
        assert not act.isChecked()
        menu = pane.findChild(QMenu, "dtpViewMenu")
        assert menu is not None
        labels = [(a.text() or "").replace("&", "") for a in menu.actions()]
        assert "Druckermarken" in labels
        assert "Satzspiegel" in labels

        set_show_printer_marks(True)
        pane.apply_shared_print_overlays()
        qapp.processEvents()
        items = pane.scene.printer_mark_items()
        assert len(items) >= 8
        assert act.isChecked()
        tags = {it.data(0) for it in pane.scene.items() if it.data(0)}
        assert tags & WORD_EDITOR_OVERLAY_TAGS == set()
        assert pane.scene.bleed_item is not None
        assert pane.scene.margin_item is not None

        act.setChecked(False)
        qapp.processEvents()
        assert get_show_printer_marks() is False
        assert pane.scene.printer_mark_items() == []
        pane.close()
    finally:
        set_show_printer_marks(prev_m)
        set_show_satzspiegel(prev_s)


def test_dtp_satzspiegel_stays_geometry_not_word_overlay(qapp) -> None:
    prev_s = get_show_satzspiegel()
    try:
        set_show_satzspiegel(False)
        from instantlensdoc.dtp.canvas import DtpPane

        pane = DtpPane(doc=DtpDocument.sample("A5"))
        pane.show()
        qapp.processEvents()
        ss = pane.findChild(QAction, "dtpSatzspiegelAction")
        assert ss is not None
        assert not ss.isChecked()
        assert pane.scene.margin_item is not None
        assert pane.scene.margin_item.data(0) == "margin"
        ss.setChecked(True)
        qapp.processEvents()
        assert get_show_satzspiegel() is True
        assert pane.scene.margin_item is not None
        tags = {it.data(0) for it in pane.scene.items() if it.data(0)}
        assert "header_mark" not in tags
        assert "footer_mark" not in tags
        assert "width_mark" not in tags
        assert tags & WORD_EDITOR_OVERLAY_TAGS == set()
        ss.setChecked(False)
        qapp.processEvents()
        assert get_show_satzspiegel() is False
        assert pane.scene.margin_item is not None
        pane.close()
    finally:
        set_show_satzspiegel(prev_s)


def test_mainwindow_toggle_exposes_shared_setting_on_dtp(qapp) -> None:
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "tests"))
    os.environ["ILD_SMOKE_QT"] = "1"
    os.environ.setdefault("ILD_SKIP_DEPS_CHECK", "1")
    os.environ.setdefault("ILD_NO_SESSION", "1")
    os.environ.setdefault("ILD_NO_SPLASH", "1")
    from menu_smoke_lib import create_main_window, install_headless_env, pump

    install_headless_env()
    prev_m = get_show_printer_marks()
    prev_s = get_show_satzspiegel()
    app, win = create_main_window()
    try:
        win._toggle_printer_marks(True)
        pump(app, 0.05)
        pane = win.dtp_pane
        assert pane._printer_marks_action.isChecked()
        assert pane.scene.printer_mark_items()
        assert get_show_printer_marks() is True
        win._toggle_printer_marks(False)
        pump(app, 0.05)
        assert pane.scene.printer_mark_items() == []
        win._toggle_satzspiegel(False)
        pump(app, 0.05)
        assert pane.scene.margin_item is not None
        tags = {it.data(0) for it in pane.scene.items() if it.data(0)}
        assert tags & WORD_EDITOR_OVERLAY_TAGS == set()
        win.hide()
    finally:
        set_show_printer_marks(prev_m)
        set_show_satzspiegel(prev_s)
