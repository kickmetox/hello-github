import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crossos.diagnostics import diagnose, firmware_status, rescue_plan
from crossos.diagnostics.repair import ALLOWLIST, apply_allowlisted
from crossos.safety import SafetyError

ROOT = Path(__file__).resolve().parents[1]


class DiagnosticTests(unittest.TestCase):
    def test_windows_codes_in_german(self):
        text = (ROOT / "examples" / "event-viewer-sample.log").read_text(encoding="utf-8")
        result = diagnose(text, shell="powershell")
        by_code = {item["code"]: item for item in result["findings"]}
        self.assertIn("zugriff verweigert", by_code["0x80070005"]["title"].lower())
        self.assertIn("datei nicht gefunden", by_code["0x80070002"]["title"].lower())
        self.assertIn("0x80004005", by_code)
        self.assertIn("0x80070057", by_code)
        self.assertIn("0xc0000005", by_code)
        self.assertIn("Zugriffsverletzung", by_code["0xc0000005"]["title"])
        self.assertIn("event-1000", by_code)
        self.assertIn("event-41", by_code)
        dll = by_code["missing-dll"]["libraries"]
        self.assertTrue(any(item["name"].lower() == "vcruntime140.dll" for item in dll))
        self.assertTrue(any(plan["packages"] == ["Microsoft.VCRedist.2015+.x64"] for item in dll for plan in item["plans"]))
        for finding in result["findings"]:
            self.assertFalse(finding["scripts"]["powershell"].startswith("rm "))
            self.assertIn("nicht automatisch", finding["script"].lower())

    def test_linux_journal_and_dmesg(self):
        journal = diagnose((ROOT / "examples" / "journal-sample.log").read_text(encoding="utf-8"), shell="bash")
        codes = {item["code"] for item in journal["findings"]}
        self.assertIn("segfault", codes)
        self.assertIn("systemd-failed", codes)
        self.assertIn("apt-broken", codes)
        unit = next(item for item in journal["findings"] if item["code"] == "systemd-failed")
        self.assertEqual(unit["unit"], "nginx.service")
        self.assertIn("systemctl restart ist nicht freigegeben", unit["scripts"]["bash"])
        dmesg = diagnose((ROOT / "examples" / "dmesg-sample.log").read_text(encoding="utf-8"))
        dmesg_codes = {item["code"] for item in dmesg["findings"]}
        self.assertIn("ext4-error", dmesg_codes)
        self.assertIn("io-error", dmesg_codes)
        self.assertIn("oom", dmesg_codes)
        self.assertIn("missing-so", dmesg_codes)
        libraries = next(item for item in dmesg["findings"] if item["code"] == "missing-so")["libraries"]
        apt = [plan for item in libraries for plan in item["plans"] if plan["manager"] == "apt"]
        self.assertEqual(apt[0]["packages"], ["libssl3"])
        self.assertFalse(apt[0]["executed"])

    def test_allowlist_blocks_destructive_and_injection(self):
        for forbidden in ("ntfsfix", "fsck", "fwupdmgr", "undervolt", "mkfs", "apt-get", "dd"):
            with self.subTest(action=forbidden):
                with self.assertRaises(SafetyError):
                    apply_allowlisted(forbidden, confirm=True)
        self.assertNotIn("fsck", ALLOWLIST)
        self.assertNotIn("ntfsfix", ALLOWLIST)
        with self.assertRaises(SafetyError):
            apply_allowlisted("apt-check", confirm=False)
        with self.assertRaises(SafetyError):
            apply_allowlisted("apt-check", confirm="true")
        with self.assertRaises(SafetyError):
            apply_allowlisted("uname", confirm=True, package="vim; rm -rf /")
        with self.assertRaises(SafetyError):
            apply_allowlisted("disk-free", confirm=True, path="../etc/passwd", roots=[ROOT / "examples"])
        done = apply_allowlisted("uname", confirm=True)
        self.assertTrue(done["executed"])
        self.assertEqual(done["argv"][1:], ["-a"])
        self.assertNotIn(";", " ".join(done["argv"]))

    def test_firmware_does_not_flash(self):
        status = firmware_status()
        self.assertFalse(status["flashed"])
        self.assertFalse(status["update_invoked"])
        self.assertIn("fwupdmgr update", status["forbidden"])

    def test_rescue_plans_are_not_executed(self):
        ntfs = rescue_plan(host_os="linux", filesystem="ntfs", device="/dev/sdb1")
        self.assertFalse(ntfs["executed"])
        self.assertIn(["ntfsfix", "--no-action", "/dev/sdb1"], [step["argv"] for step in ntfs["steps"]])
        self.assertIn(["ntfsfix", "/dev/sdb1"], ntfs["do_not_run"])
        ext4 = rescue_plan(host_os="windows", filesystem="ext4", device="E:")
        self.assertFalse(ext4["native_fsck"])
        self.assertIn("nicht nativ", ext4["plan_de"])
        self.assertIn("fsck", ext4["wsl_plan"]["argv"])
        self.assertIn("-n", ext4["wsl_plan"]["argv"])
        with self.assertRaises(SafetyError):
            rescue_plan(host_os="linux", filesystem="ext4", device="/dev/sda1; rm -rf /")
        with self.assertRaises(SafetyError):
            rescue_plan(host_os="windows", filesystem="btrfs", device="/dev/sdb1")


if __name__ == "__main__":
    unittest.main()
