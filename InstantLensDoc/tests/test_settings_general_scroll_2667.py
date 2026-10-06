"""Einstellungen → Allgemein: scrollbar, OK/Abbrechen bleiben sichtbar."""

from __future__ import annotations

import os
import sys
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
from PySide6.QtWidgets import (  # noqa: E402
    QApplication,
    QDialogButtonBox,
    QScrollArea,
)

from menu_smoke_lib import install_headless_env, pump  # noqa: E402
from instantlensdoc.ui.settings_dialog import SettingsDialog  # noqa: E402


def test_general_tab_is_scroll_area_buttons_outside() -> None:
    install_headless_env()
    app = QApplication.instance() or QApplication([])
    dlg = SettingsDialog()
    dlg.show()
    pump(app, 0.08)
    scroll = dlg.findChild(QScrollArea, "settingsGeneralScroll")
    assert scroll is not None
    assert scroll.verticalScrollBarPolicy() == Qt.ScrollBarAsNeeded
    page = scroll.widget()
    assert page is not None
    assert page.objectName() == "settingsGeneralPage"
    buttons = dlg.findChild(QDialogButtonBox, "settingsDialogButtons")
    assert buttons is not None
    assert buttons.parent() is dlg or buttons.parentWidget() is dlg
    inner = scroll.widget()
    assert buttons is not inner and not inner.isAncestorOf(buttons)
    screen = app.primaryScreen()
    if screen is not None:
        cap = max(420, int(screen.availableGeometry().height() * 0.82))
        assert dlg.maximumHeight() <= cap or dlg.height() <= cap
    assert dlg.height() >= 400
    dlg.close()
