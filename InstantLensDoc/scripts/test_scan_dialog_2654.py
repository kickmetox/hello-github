"""Offscreen-Smoke: vereinfachter Scan-Dialog + Einstellungen → Scannen — 2.6.54."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QWidget

from instantlensdoc.core.devices import DeviceDiscoveryResult, DeviceInfo, DeviceKind
from instantlensdoc.core.scan_transfer import BACKEND_ORDER
from instantlensdoc.ui.scan_dialog import ScanDialog
from instantlensdoc.ui.settings_dialog import SettingsDialog


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


class DummyPdf(QWidget):
    pdf_path = None
    password = ""
    page_index = 0
    page_count = 0


class TestScanDialog2654(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _app()

    def test_dialog_has_one_scan_button_and_backend_combo(self) -> None:
        fake = DeviceDiscoveryResult(
            scanners=[
                DeviceInfo(kind=DeviceKind.SCANNER, name="Canon", device_id="{AA}\\1", backend="WIA")
            ]
        )
        with patch("instantlensdoc.ui.scan_dialog.discover_devices", return_value=fake):
            dlg = ScanDialog(DummyPdf(), None, auto_launch_scantuxio=False)
        self.addCleanup(dlg.close)
        self.assertEqual(dlg.objectName(), "scanDialog")
        self.assertEqual(dlg.btn_scan.text(), "Scannen")
        self.assertEqual(dlg.btn_scantuxio.text(), "ScanTuxio öffnen")
        self.assertTrue(dlg.adv_panel.isHidden())
        dlg.adv_toggle.setChecked(True)
        self.assertFalse(dlg.adv_panel.isHidden())
        keys = [dlg.backend_widget.backend_combo.itemData(i) for i in range(dlg.backend_widget.backend_combo.count())]
        self.assertEqual(tuple(keys), BACKEND_ORDER)
        self.assertGreaterEqual(dlg.device_combo.count(), 1)
        self.assertTrue(hasattr(dlg, "btn_acquire") and hasattr(dlg, "btn_import"))
        self.assertEqual(dlg.layout_hocr.objectName(), "scanOcrHocr")

    def test_settings_has_scan_tab(self) -> None:
        dlg = SettingsDialog(None)
        self.addCleanup(dlg.close)
        titles = [dlg.tabs.tabText(i) for i in range(dlg.tabs.count())]
        self.assertIn("Scannen", titles)
        self.assertTrue(hasattr(dlg, "scan_backend_widget"))
        self.assertEqual(dlg.scan_backend_widget.backend_combo.count(), 7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
