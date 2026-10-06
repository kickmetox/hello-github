"""2.6.57: Geräte-I/O Timeout, Cache-Menü, Netzwerk-eSCL — ohne echte Hardware.

    python3 scripts/test_scan_timeout_2657.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from instantlensdoc.core.device_io import run_with_timeout
from instantlensdoc.core.devices import (
    DeviceDiscoveryResult,
    DeviceInfo,
    DeviceKind,
    DeviceScope,
    devices_menu_entries,
    load_cached_discovery,
    save_cached_discovery,
    scanner_choices,
)


def _hang(seconds: float = 8.0) -> str:
    time.sleep(seconds)
    return "should-not-return"


class TestRunWithTimeout(unittest.TestCase):
    def test_mocked_hang_does_not_block(self) -> None:
        from concurrent.futures import ThreadPoolExecutor

        ex = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ild-to-test")
        self.addCleanup(lambda: ex.shutdown(wait=False, cancel_futures=False))
        t0 = time.monotonic()
        res = run_with_timeout(_hang, 0.25, 8.0, executor=ex)
        elapsed = time.monotonic() - t0
        self.assertTrue(res.timed_out)
        self.assertIn("Zeitüberschreitung", res.error)
        self.assertLess(elapsed, 1.5, f"run_with_timeout blocked {elapsed:.2f}s")

    def test_success_returns_value(self) -> None:
        res = run_with_timeout(lambda: 42, 1.0)
        self.assertTrue(res.ok)
        self.assertEqual(res.value, 42)


class TestDeviceCacheMenu(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory(prefix="ild-devcache-")
        self._path = Path(self._td.name) / "device_cache.json"
        self._patch = patch(
            "instantlensdoc.core.devices.device_cache_path", return_value=self._path
        )
        self._patch.start()

    def tearDown(self) -> None:
        self._patch.stop()
        self._td.cleanup()

    def test_menu_populate_uses_cache_not_live_discover(self) -> None:
        fake = DeviceDiscoveryResult(
            scanners=[
                DeviceInfo(
                    kind=DeviceKind.SCANNER,
                    name="Canon",
                    device_id="{AA}\\1",
                    backend="WIA",
                )
            ]
        )
        save_cached_discovery(fake)

        def hang_discover(**_k):
            time.sleep(20)
            return DeviceDiscoveryResult()

        t0 = time.monotonic()
        with patch("instantlensdoc.core.devices.discover_devices", side_effect=hang_discover):
            cached = load_cached_discovery()
            entries = devices_menu_entries(cached)
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 0.8, f"cache populate blocked {elapsed:.2f}s")
        self.assertEqual(len(entries), 1)
        self.assertIn("Canon", entries[0][0])
        self.assertIs(entries[0][1].kind, DeviceKind.SCANNER)


class TestNetworkEsclDefault(unittest.TestCase):
    def test_dropdown_picks_escl_for_network_mfp(self) -> None:
        wia = DeviceInfo(
            kind=DeviceKind.SCANNER,
            name="Brother MFC",
            device_id="{6BDD}\\002",
            scope=DeviceScope.NETWORK,
            backend="WIA",
        )
        escl = DeviceInfo(
            kind=DeviceKind.SCANNER,
            name="Brother MFC",
            device_id="native-escl:http://10.0.0.9:80",
            scope=DeviceScope.NETWORK,
            backend="ScanTuxio/eSCL",
        )
        choices = scanner_choices([wia, escl], backend="auto", include_wia_dialog=False)
        self.assertEqual(len(choices), 1)
        self.assertTrue(choices[0].primary.device_id.startswith("native-escl:"))


class TestScanDialogTimeoutUi(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        cls.app = app

    def test_dialog_opens_from_cache_when_discover_hangs(self) -> None:
        from PySide6.QtWidgets import QWidget

        from instantlensdoc.ui.scan_dialog import ScanDialog

        class DummyPdf(QWidget):
            pdf_path = None
            password = ""
            page_index = 0
            page_count = 0

        fake = DeviceDiscoveryResult(
            scanners=[
                DeviceInfo(
                    kind=DeviceKind.SCANNER,
                    name="HP ScanJet",
                    device_id="{BB}\\2",
                    backend="WIA",
                )
            ]
        )
        with patch(
            "instantlensdoc.ui.scan_dialog.load_cached_discovery", return_value=fake
        ), patch(
            "instantlensdoc.ui.scan_dialog.discover_devices",
            side_effect=lambda **_k: _hang(20),
        ):
            t0 = time.monotonic()
            dlg = ScanDialog(DummyPdf(), None, auto_launch_scantuxio=False)
            elapsed = time.monotonic() - t0
            self.addCleanup(dlg.close)
            self.assertLess(elapsed, 1.5, f"ScanDialog blocked {elapsed:.2f}s")
            labels = [dlg.device_combo.itemText(i) for i in range(dlg.device_combo.count())]
            self.assertTrue(any("HP" in t or "ScanJet" in t for t in labels))

    def test_acquire_timeout_reenable_dialog(self) -> None:
        from PySide6.QtWidgets import QWidget

        from instantlensdoc.ui.scan_dialog import ScanDialog

        class DummyPdf(QWidget):
            pdf_path = None
            password = ""
            page_index = 0
            page_count = 0

        fake = DeviceDiscoveryResult(
            scanners=[
                DeviceInfo(
                    kind=DeviceKind.SCANNER,
                    name="Sleepy WIA",
                    device_id="{CC}\\3",
                    backend="WIA",
                )
            ]
        )
        os.environ["ILD_DEVICE_IO_TIMEOUT"] = "0.35"
        self.addCleanup(lambda: os.environ.pop("ILD_DEVICE_IO_TIMEOUT", None))
        with patch(
            "instantlensdoc.ui.scan_dialog.load_cached_discovery", return_value=fake
        ), patch(
            "instantlensdoc.ui.scan_dialog.discover_devices", return_value=fake
        ), patch(
            "instantlensdoc.ui.scan_dialog.acquire_from_scanner",
            side_effect=lambda *a, **k: _hang(20),
        ):
            dlg = ScanDialog(DummyPdf(), None, auto_launch_scantuxio=False)
            self.addCleanup(dlg.close)
            dlg.device_combo.setCurrentIndex(0)
            t0 = time.monotonic()
            dlg._start_acquire(insert=False)
            while time.monotonic() - t0 < 2.5:
                self.app.processEvents()
                if not dlg._io_busy:
                    break
                time.sleep(0.03)
            elapsed = time.monotonic() - t0
            self.assertLess(elapsed, 2.0, f"timeout watchdog blocked {elapsed:.2f}s")
            self.assertFalse(dlg._io_busy)
            self.assertTrue(dlg.device_combo.isEnabled())
            self.assertTrue(dlg.btn_scan.isEnabled())
            self.assertIn("Zeitüberschreitung", dlg.device_status.text())
            self.assertIn("anderes Gerät", dlg.device_status.text())

    def test_devices_menu_fill_from_cache_instant(self) -> None:
        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QMenu, QWidget

        fake = DeviceDiscoveryResult(
            scanners=[
                DeviceInfo(
                    kind=DeviceKind.SCANNER,
                    name="Netzwerk-Kyocera",
                    device_id="native-escl:http://1.2.3.4:80",
                    scope=DeviceScope.NETWORK,
                    backend="ScanTuxio/eSCL",
                )
            ]
        )
        parent = QWidget()
        menu = QMenu("Geräte", parent)
        menu.addAction(QAction("Scannen…", parent))
        t0 = time.monotonic()
        with patch(
            "instantlensdoc.core.devices.discover_devices",
            side_effect=lambda **_k: _hang(20),
        ):
            entries = devices_menu_entries(fake)
            for i, (label, _dev) in enumerate(entries):
                act = QAction(label, parent)
                act.setObjectName(f"actCachedDevice{i}")
                menu.addAction(act)
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 0.5)
        names = [a.text() for a in menu.actions()]
        self.assertTrue(any("Kyocera" in n for n in names))


class TestScanProcTree(unittest.TestCase):
    def test_kill_process_tree_reaps_child(self) -> None:
        import subprocess

        from instantlensdoc.core.scan_procs import kill_process_tree, register_pid, unregister_pid

        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        register_pid(proc.pid)
        try:
            killed = kill_process_tree(proc.pid)
            t0 = time.monotonic()
            while proc.poll() is None and time.monotonic() - t0 < 2.0:
                time.sleep(0.05)
            self.assertIsNotNone(proc.poll(), "child still running after kill_process_tree")
            self.assertTrue(killed)
        finally:
            unregister_pid(proc.pid)
            try:
                proc.kill()
            except Exception:
                pass

    def test_run_process_timeout_does_not_leave_child(self) -> None:
        from instantlensdoc.core.scan_transfer import run_process

        t0 = time.monotonic()
        rc, _out, _err, timed_out = run_process(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            timeout=0.35,
            hide_window=False,
        )
        elapsed = time.monotonic() - t0
        self.assertTrue(timed_out)
        self.assertLess(elapsed, 2.0, f"run_process hang {elapsed:.2f}s")
        self.assertEqual(len(__import__("instantlensdoc.core.scan_procs", fromlist=["tracked_pids"]).tracked_pids()), 0)

    def test_kill_new_since_only_new_pids(self) -> None:
        from instantlensdoc.core.scan_procs import kill_new_since

        calls = []

        def fake_list(names=None):
            return [111, 222]

        def fake_tree(pid):
            calls.append(pid)
            return [pid]

        with patch("instantlensdoc.core.scan_procs.list_named_pids", side_effect=fake_list), patch(
            "instantlensdoc.core.scan_procs.kill_process_tree", side_effect=fake_tree
        ):
            killed = kill_new_since({111})
        self.assertEqual(killed, [222])
        self.assertEqual(calls, [222])

    def test_ecosys_name_is_network_mfp(self) -> None:
        from instantlensdoc.core.devices import device_is_network
        from instantlensdoc.core.scan_procs import name_looks_network_mfp

        self.assertTrue(name_looks_network_mfp("ECOSYS M5521cdn"))
        d = DeviceInfo(
            kind=DeviceKind.SCANNER,
            name="ECOSYS M5521cdn",
            device_id="{6BDD}\\eco",
            scope=DeviceScope.LOCAL,
            backend="WIA",
        )
        self.assertTrue(device_is_network(d))

    def test_wia_script_dialog_only_with_flag(self) -> None:
        from instantlensdoc.core.scan_transfer import WIA_SCRIPT

        self.assertIn("if ($UseDialog)", WIA_SCRIPT)
        self.assertGreater(WIA_SCRIPT.find("ShowAcquireImage"), WIA_SCRIPT.find("if ($UseDialog)"))
        self.assertIn("kein CommonDialog-Fallback", WIA_SCRIPT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
