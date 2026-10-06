"""Unit tests: Scan-Übertragung (NAPS2/WIA/eSCL/extern) — 2.6.54.

Mockt subprocess/WIA; prüft Ausgabedatei-Suche, Quoting, Fehlerfälle, Backend-Plan.
Ohne echte Hardware. Aufruf:

    python3 scripts/test_scan_transfer.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image

from instantlensdoc.core.devices import DeviceInfo, DeviceKind, DeviceScope, scanner_choices
from instantlensdoc.core.scan_transfer import (
    BACKEND_AUTO,
    BACKEND_ESCL,
    BACKEND_EXTERNAL,
    BACKEND_NAPS2,
    BACKEND_TWAIN,
    BACKEND_WIA,
    ScanAttempt,
    ScanJob,
    build_external_command,
    build_naps2_command,
    build_wia_command,
    classify_device_id,
    format_command,
    looks_like_cli_option_error,
    new_files_since,
    plan_steps,
    read_result_file,
    run_scan,
    snapshot_dir,
    validate_and_normalize,
    wait_for_output,
    write_wia_script,
)


def _png(path: Path, size: tuple[int, int] = (8, 8)) -> Path:
    Image.new("RGB", size, (240, 240, 240)).save(path, "PNG")
    return path


class TestQuotingAndCommands(unittest.TestCase):
    def test_naps2_command_quotes_spaces_in_output_path(self) -> None:
        out = Path(r"C:\Users\Max Mustermann\AppData\Local\Temp\scan out.png")
        cmd = build_naps2_command(
            r"C:\Program Files\NAPS2\NAPS2.Console.exe",
            out,
            driver="wia",
            device="HP ScanJet",
            dpi=300,
            color_mode="Color",
            source="Flatbed",
        )
        self.assertEqual(cmd[0], r"C:\Program Files\NAPS2\NAPS2.Console.exe")
        self.assertEqual(cmd[1], "-o")
        self.assertEqual(cmd[2], str(out))
        self.assertIn("--driver", cmd)
        self.assertIn("wia", cmd)
        self.assertIn("--device", cmd)
        self.assertIn("HP ScanJet", cmd)
        line = format_command(cmd)
        # Windows list2cmdline quotes paths with spaces
        if os.name == "nt" or True:
            self.assertIn("scan out.png", line)
            self.assertTrue(
                '"C:\\Program Files\\NAPS2\\NAPS2.Console.exe"' in line
                or "Program Files" in line
            )

    def test_wia_command_uses_file_sta_and_quoted_paths(self) -> None:
        script = Path(r"C:\Users\Müller\Local\Temp\ild_wia_scan.ps1")
        out_dir = Path(r"C:\Users\Müller\Local\Temp\ild-scan")
        result = out_dir / "wia_result.txt"
        cmd = build_wia_command(
            r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
            script,
            out_dir=out_dir,
            result_file=result,
            device_id="{6BDD1FC6-810F-11D0-BEC7-08002BE2092F}\\0000",
            device_name="Canon",
            dpi=300,
            color_mode="Color",
            source="Flatbed",
            use_dialog=False,
        )
        self.assertIn("-STA", cmd)
        self.assertIn("-File", cmd)
        self.assertIn(str(script), cmd)
        self.assertIn("-OutDir", cmd)
        self.assertIn(str(out_dir), cmd)
        self.assertNotIn("-UseDialog", cmd)
        dlg = build_wia_command(
            "powershell.exe",
            script,
            out_dir=out_dir,
            result_file=result,
            device_id="",
            device_name="",
            dpi=200,
            color_mode="Gray",
            source="ADF",
            use_dialog=True,
        )
        self.assertIn("-UseDialog", dlg)

    def test_external_template_placeholders(self) -> None:
        cmd = build_external_command(
            r'"C:\Program Files\NAPS2\NAPS2.Console.exe" -o "{output}" --dpi {dpi} --device "{device}" --bitdepth {color}',
            output=Path(r"C:\Temp\scan me.png"),
            outdir=Path(r"C:\Temp"),
            dpi=300,
            device="HP LaserJet",
            color="Color",
            source="Flatbed",
        )
        self.assertEqual(cmd[0], r"C:\Program Files\NAPS2\NAPS2.Console.exe")
        self.assertEqual(cmd[2], r"C:\Temp\scan me.png")
        self.assertIn("300", cmd)
        self.assertIn("HP LaserJet", cmd)
        self.assertIn("Color", cmd)

    def test_cli_option_error_detection(self) -> None:
        self.assertTrue(looks_like_cli_option_error("ERROR(S):\nUnknown option: --bitdepth"))
        self.assertTrue(looks_like_cli_option_error("Unrecognized option '--verbose'"))
        self.assertFalse(looks_like_cli_option_error("Device busy"))


class TestFileDiscovery(unittest.TestCase):
    def test_wait_for_output_finds_expected_and_naps2_numbered(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ild-scan-test-") as raw:
            d = Path(raw)
            before = snapshot_dir(d)
            expected = d / "scan_naps2_1.png"
            # NAPS2 appends 1 before the extension when the name already exists
            numbered = d / "scan_naps2_11.png"
            _png(numbered)
            found = wait_for_output(
                d, before, expected=[expected], stem="scan_naps2_1", timeout=0.0, poll=0.0
            )
            names = {p.name for p in found}
            self.assertIn("scan_naps2_11.png", names)

    def test_wait_for_output_ignores_tiny_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ild-scan-test-") as raw:
            d = Path(raw)
            before = snapshot_dir(d)
            tiny = d / "scan_wia_x.png"
            tiny.write_bytes(b"nope")
            found = wait_for_output(d, before, stem="scan_wia_", timeout=0.0)
            self.assertEqual(found, [])

    def test_new_files_since_detects_growth(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ild-scan-test-") as raw:
            d = Path(raw)
            p = _png(d / "a.png")
            before = snapshot_dir(d)
            Image.new("RGB", (16, 16), (1, 2, 3)).save(p, "PNG")
            grew = new_files_since(d, before)
            self.assertEqual([x.name for x in grew], ["a.png"])

    def test_validate_converts_bmp_and_skips_corrupt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ild-scan-test-") as raw:
            d = Path(raw)
            bmp = d / "scan.bmp"
            Image.new("RGB", (4, 4), (9, 9, 9)).save(bmp, "BMP")
            bad = d / "bad.png"
            bad.write_bytes(b"not-an-image")
            ok = d / "ok.png"
            _png(ok)
            out = validate_and_normalize([bmp, bad, ok], out_dir=d)
            names = [p.suffix.lower() for p in out]
            self.assertIn(".png", names)
            self.assertTrue(any(p.stem.startswith("scan") and p.suffix == ".png" for p in out))
            self.assertFalse(any(p.name == "bad.png" for p in out))

    def test_read_result_file_utf8_and_umlaut_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ild-scan-test-") as raw:
            d = Path(raw)
            umlaut = d / "Müller-scan.png"
            _png(umlaut)
            rf = d / "wia_result.txt"
            rf.write_text(str(umlaut) + "\nCANCELLED\n", encoding="utf-8")
            paths = read_result_file(rf)
            self.assertEqual(paths, [umlaut])


class TestPlanAndRun(unittest.TestCase):
    def test_classify_device_ids(self) -> None:
        self.assertEqual(classify_device_id("{ABC}\\0000", "WIA"), "wia")
        self.assertEqual(classify_device_id("naps2:wia:HP Scan", "ScanTuxio/NAPS2/WIA"), "naps2")
        self.assertEqual(classify_device_id("naps2:twain:HP", ""), "naps2")
        self.assertEqual(classify_device_id("native-escl:http://1.2.3.4:8080", ""), "escl")
        self.assertEqual(classify_device_id("mdns:1.2.3.4:8080", "ScanTuxio/mDNS"), "escl")
        self.assertEqual(classify_device_id("TWAIN:HP", "TWAIN"), "twain")
        self.assertEqual(classify_device_id("wia:dialog", ""), "dialog")

    def test_plan_auto_wia_then_naps2(self) -> None:
        job = ScanJob(
            device_id="{6BDD}\\0000",
            device_name="Canon CanoScan",
            device_backend="WIA",
            backend=BACKEND_AUTO,
        )
        with patch("instantlensdoc.core.scan_transfer.is_windows", return_value=True), patch(
            "instantlensdoc.core.scan_transfer.naps2_console_path",
            return_value=r"C:\Program Files\NAPS2\NAPS2.Console.exe",
        ):
            steps = plan_steps(job)
        kinds = [s.kind for s in steps]
        self.assertEqual(kinds[0], "wia")
        self.assertIn("naps2", kinds)
        self.assertEqual(kinds[-1], "wia-dialog")

    def test_plan_forced_naps2(self) -> None:
        job = ScanJob(
            device_id="naps2:wia:HP ScanJet",
            device_name="HP ScanJet (WIA)",
            backend=BACKEND_NAPS2,
        )
        steps = plan_steps(job)
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].kind, "naps2")
        self.assertEqual(steps[0].driver, "wia")
        self.assertEqual(steps[0].device_name, "HP ScanJet")

    def test_plan_twain_uses_naps2_driver(self) -> None:
        job = ScanJob(device_id="TWAIN:Epson", device_name="Epson", backend=BACKEND_TWAIN)
        steps = plan_steps(job)
        self.assertEqual(steps[0].kind, "naps2")
        self.assertEqual(steps[0].driver, "twain")

    def test_plan_escl(self) -> None:
        job = ScanJob(
            device_id="native-escl:http://192.168.1.9:8080",
            device_name="Kyocera",
            backend=BACKEND_ESCL,
        )
        steps = plan_steps(job)
        self.assertEqual(steps[0].kind, "escl")

    def test_plan_auto_network_uses_escl_not_wia(self) -> None:
        job = ScanJob(
            device_id="{6BDD}\\net",
            device_name="Kyocera (Netzwerk)",
            device_backend="WIA",
            backend=BACKEND_AUTO,
            fallback_devices=[
                ("native-escl:http://192.168.1.9:80", "Kyocera", "ScanTuxio/eSCL"),
            ],
        )
        with patch("instantlensdoc.core.scan_transfer.is_windows", return_value=True), patch(
            "instantlensdoc.core.scan_transfer.naps2_console_path",
            return_value=r"C:\Program Files\NAPS2\NAPS2.Console.exe",
        ):
            steps = plan_steps(job)
        kinds = [s.kind for s in steps]
        self.assertEqual(kinds[0], "escl")
        self.assertNotIn("wia", kinds)
        self.assertNotIn("wia-dialog", kinds)

    def test_plan_auto_ecosys_skips_wia_dialog(self) -> None:
        job = ScanJob(
            device_id="{6BDD1FC6-810F-11D0-BEC7-08002BE2092F}\\0002",
            device_name="ECOSYS M5521cdn",
            device_backend="WIA",
            backend=BACKEND_AUTO,
        )
        with patch("instantlensdoc.core.scan_transfer.is_windows", return_value=True), patch(
            "instantlensdoc.core.scan_transfer.naps2_console_path",
            return_value=r"C:\Program Files\NAPS2\NAPS2.Console.exe",
        ):
            steps = plan_steps(job)
        kinds = [s.kind for s in steps]
        self.assertNotIn("wia", kinds)
        self.assertNotIn("wia-dialog", kinds)

    def test_run_scan_naps2_writes_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ild-scan-test-") as raw:
            d = Path(raw)

            def fake_run(cmd, *, timeout, cwd=None, env=None, hide_window=True):
                out = Path(cmd[cmd.index("-o") + 1])
                _png(out)
                return 0, f"Saved {out}\n", "", False

            job = ScanJob(
                device_id="naps2:wia:HP",
                device_name="HP",
                backend=BACKEND_NAPS2,
                out_dir=d,
                naps2_path=str(d / "NAPS2.Console.exe"),
            )
            (d / "NAPS2.Console.exe").write_text("fake")
            with patch("instantlensdoc.core.scan_transfer.naps2_console_path", return_value=str(d / "NAPS2.Console.exe")), patch(
                "instantlensdoc.core.scan_transfer.run_process", side_effect=fake_run
            ):
                result = run_scan(job)
            self.assertTrue(result.ok, result.error)
            self.assertEqual(len(result.paths), 1)
            self.assertTrue(result.paths[0].is_file())
            self.assertGreater(result.paths[0].stat().st_size, 32)

    def test_run_scan_naps2_missing_file_is_error_with_stderr(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ild-scan-test-") as raw:
            d = Path(raw)

            def fake_run(cmd, *, timeout, cwd=None, env=None, hide_window=True):
                return 1, "", "Unknown option: --bitdepth\nDevice not found", False

            job = ScanJob(
                device_id="naps2:wia:HP",
                device_name="HP",
                backend=BACKEND_NAPS2,
                out_dir=d,
            )
            with patch(
                "instantlensdoc.core.scan_transfer.naps2_console_path",
                return_value="/usr/bin/true",
            ), patch("instantlensdoc.core.scan_transfer.run_process", side_effect=fake_run):
                result = run_scan(job)
            self.assertFalse(result.ok)
            text = result.detail_text_de()
            self.assertIn("NAPS2", text)
            self.assertIn("stderr", text.lower())
            self.assertTrue(result.attempts)

    def test_run_scan_wia_reads_result_file_not_stdout(self) -> None:
        """Pfad mit Umlaut kommt aus Result-Datei, nicht aus kaputtem UTF-8-stdout."""
        with tempfile.TemporaryDirectory(prefix="ild-scan-test-") as raw:
            d = Path(raw)
            target = d / "Müller-wia.png"

            def fake_run(cmd, *, timeout, cwd=None, env=None, hide_window=True):
                rf = Path(cmd[cmd.index("-ResultFile") + 1])
                _png(target)
                rf.write_text(str(target) + "\n", encoding="utf-8")
                return 0, "M\x00ller-wia.png\n", "", False  # kaputtes stdout

            job = ScanJob(
                device_id="{6BDD1FC6-810F-11D0-BEC7-08002BE2092F}\\0000",
                device_name="Canon",
                device_backend="WIA",
                backend=BACKEND_WIA,
                out_dir=d,
            )
            with patch("instantlensdoc.core.scan_transfer.is_windows", return_value=True), patch(
                "instantlensdoc.core.scan_transfer.powershell_exe", return_value="powershell"
            ), patch("instantlensdoc.core.scan_transfer.run_process", side_effect=fake_run):
                result = run_scan(job)
            self.assertTrue(result.ok, result.error)
            self.assertEqual(result.paths[0].name, "Müller-wia.png")

    def test_run_scan_wia_busy_message(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ild-scan-test-") as raw:
            d = Path(raw)

            def fake_run(cmd, *, timeout, cwd=None, env=None, hide_window=True):
                return 1, "", "WIA-Fehler: The device is busy [0x80210006]", False

            job = ScanJob(
                device_id="{6BDD1FC6-810F-11D0-BEC7-08002BE2092F}\\0000",
                device_name="Canon",
                device_backend="WIA",
                backend=BACKEND_WIA,
                out_dir=d,
            )
            with patch("instantlensdoc.core.scan_transfer.is_windows", return_value=True), patch(
                "instantlensdoc.core.scan_transfer.powershell_exe", return_value="powershell"
            ), patch("instantlensdoc.core.scan_transfer.run_process", side_effect=fake_run):
                result = run_scan(job)
            self.assertFalse(result.ok)
            self.assertTrue(result.busy)
            self.assertIn("ausgelastet", result.error.lower())

    def test_run_scan_external_picks_new_file_in_outdir(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ild-scan-test-") as raw:
            d = Path(raw)
            ext = d / "ext-out"
            ext.mkdir()

            def fake_run(cmd, *, timeout, cwd=None, env=None, hide_window=True):
                _png(ext / "from-tool.jpg")
                return 0, "", "", False

            job = ScanJob(
                backend=BACKEND_EXTERNAL,
                out_dir=d,
                external_cmd='echo "{output}"',
                external_outdir=str(ext),
            )
            with patch("instantlensdoc.core.scan_transfer.run_process", side_effect=fake_run):
                result = run_scan(job)
            self.assertTrue(result.ok, result.error)
            self.assertEqual(result.paths[0].name, "from-tool.jpg")

    def test_run_scan_cancelled_dialog(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ild-scan-test-") as raw:
            d = Path(raw)

            def fake_run(cmd, *, timeout, cwd=None, env=None, hide_window=True):
                return 3, "CANCELLED\n", "", False

            job = ScanJob(backend=BACKEND_WIA, out_dir=d)
            with patch("instantlensdoc.core.scan_transfer.is_windows", return_value=True), patch(
                "instantlensdoc.core.scan_transfer.powershell_exe", return_value="powershell"
            ), patch("instantlensdoc.core.scan_transfer.run_process", side_effect=fake_run):
                result = run_scan(job)
            self.assertTrue(result.cancelled)
            self.assertFalse(result.ok)

    def test_wia_script_written_utf8_bom_and_items_item(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ild-scan-test-") as raw:
            d = Path(raw)
            script = write_wia_script(d)
            data = script.read_bytes()
            self.assertTrue(data.startswith(b"\xef\xbb\xbf"))
            text = script.read_text(encoding="utf-8-sig")
            self.assertIn("$item = $dev.Items.Item(1)", text)
            self.assertNotIn("$dev.Items(1)", text)
            self.assertIn("ShowAcquireImage", text)
            self.assertIn("SaveFile", text)
            self.assertIn("if ($UseDialog)", text)
            self.assertIn("kein CommonDialog-Fallback", text)
            self.assertNotIn("Windows-Scannerdialog wird verwendet", text)
            self.assertGreater(text.find("ShowAcquireImage"), text.find("if ($UseDialog)"))


class TestScannerChoices(unittest.TestCase):
    def test_groups_wia_and_naps2_same_name(self) -> None:
        wia = DeviceInfo(
            kind=DeviceKind.SCANNER,
            name="Canon CanoScan",
            device_id="{6BDD1FC6-810F-11D0-BEC7-08002BE2092F}\\0000",
            scope=DeviceScope.LOCAL,
            backend="WIA",
        )
        naps = DeviceInfo(
            kind=DeviceKind.SCANNER,
            name="Canon CanoScan (WIA)",
            device_id="naps2:wia:Canon CanoScan",
            scope=DeviceScope.LOCAL,
            backend="ScanTuxio/NAPS2/WIA",
        )
        choices = scanner_choices([wia, naps], backend="auto", include_wia_dialog=False)
        self.assertEqual(len(choices), 1)
        self.assertEqual(choices[0].primary.backend, "WIA")
        self.assertEqual(len(choices[0].alternates), 1)

    def test_escl_filter(self) -> None:
        wia = DeviceInfo(kind=DeviceKind.SCANNER, name="USB", device_id="{A}", backend="WIA")
        escl = DeviceInfo(
            kind=DeviceKind.SCANNER,
            name="Kyocera",
            device_id="native-escl:http://1.2.3.4:80",
            backend="ScanTuxio/eSCL",
            scope=DeviceScope.NETWORK,
        )
        choices = scanner_choices([wia, escl], backend="escl", include_wia_dialog=False)
        self.assertEqual(len(choices), 1)
        self.assertEqual(choices[0].primary.name, "Kyocera")

    def test_network_prefers_escl_over_wia(self) -> None:
        wia = DeviceInfo(
            kind=DeviceKind.SCANNER,
            name="Kyocera ECOSYS",
            device_id="{6BDD1FC6-810F-11D0-BEC7-08002BE2092F}\\0001",
            scope=DeviceScope.NETWORK,
            backend="WIA",
        )
        escl = DeviceInfo(
            kind=DeviceKind.SCANNER,
            name="Kyocera ECOSYS",
            device_id="native-escl:http://192.168.1.9:80",
            scope=DeviceScope.NETWORK,
            backend="ScanTuxio/eSCL",
        )
        choices = scanner_choices([wia, escl], backend="auto", include_wia_dialog=False)
        self.assertEqual(len(choices), 1)
        self.assertTrue(choices[0].primary.device_id.startswith("native-escl:"))


class TestAcquireBridge(unittest.TestCase):
    def test_acquire_from_scanner_uses_transfer(self) -> None:
        from instantlensdoc.core import scan as scan_mod

        with tempfile.TemporaryDirectory(prefix="ild-scan-test-") as raw:
            d = Path(raw)
            png = _png(Path(d) / "x.png")
            fake = ScanAttempt(backend=BACKEND_NAPS2, paths=[png])
            fake_result_ok = type("R", (), {})()

            class Res:
                ok = True
                cancelled = False
                busy = False
                paths = [png]
                error = ""
                attempts = [fake]
                backend = "NAPS2"

                def detail_text_de(self):
                    return "ok"

            with patch("instantlensdoc.core.scan_transfer.run_scan", return_value=Res()):
                paths = scan_mod.acquire_from_scanner(
                    DeviceInfo(kind=DeviceKind.SCANNER, name="HP", device_id="naps2:wia:HP"),
                    out_dir=d,
                    backend=BACKEND_NAPS2,
                )
            self.assertEqual(paths, [png])
            self.assertEqual(scan_mod.last_acquire_error(), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
