import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crossos.hardware.battery import apply_threshold
from crossos.hardware.fans import PROFILES, export_profile, validate_curve
from crossos.hardware.power import PLANS, apply_ppd, list_plans
from crossos.hardware.probe import probe
from crossos.hardware.undervolt import save_offsets
from crossos.hardware.vendors import vendor_map
from crossos.safety import SafetyError


class FanTests(unittest.TestCase):
    def test_builtin_profiles_match_across_os(self):
        self.assertEqual(set(PROFILES), {"silent", "balanced", "performance", "turbo"})
        for name in PROFILES:
            exported = export_profile(name)
            self.assertEqual(exported["linux"]["points"], exported["windows"]["points"])
            self.assertFalse(exported["applied"])
            self.assertGreaterEqual(len(exported["points"]), 2)
            validate_curve(exported["points"])

    def test_curve_validation(self):
        with self.assertRaises(SafetyError):
            validate_curve([{"temp_c": 40, "duty_percent": 101}, {"temp_c": 70, "duty_percent": 100}])
        with self.assertRaises(SafetyError):
            validate_curve([{"temp_c": 70, "duty_percent": 20}, {"temp_c": 40, "duty_percent": 40}])
        with self.assertRaises(SafetyError):
            validate_curve([{"temp_c": 40, "duty_percent": 40}, {"temp_c": 80, "duty_percent": 20}])
        with self.assertRaises(SafetyError):
            validate_curve([{"temp_c": True, "duty_percent": 10}, {"temp_c": 50, "duty_percent": 20}])
        with self.assertRaises(SafetyError):
            validate_curve([{"temp_c": 40, "duty_percent": 10}])


class BatteryTests(unittest.TestCase):
    def test_threshold_requires_node_and_confirm(self):
        root = Path(self.id().replace(".", "_"))
        # isoliert unter tmp über TemporaryDirectory-Muster ohne Abhängigkeit
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            node = root / "BAT0" / "charge_control_end_threshold"
            node.parent.mkdir(parents=True)
            node.write_text("100\n", encoding="utf-8")
            node.chmod(0o644)
            state = root / "state.json"
            held = apply_threshold(80, confirm=False, state_file=state, node=str(node), sysfs_root=root)
            self.assertFalse(held["written"])
            self.assertEqual(node.read_text(encoding="utf-8").strip(), "100")
            written = apply_threshold(80, confirm=True, state_file=state, node=str(node), sysfs_root=root)
            self.assertTrue(written["written"])
            self.assertEqual(node.read_text(encoding="utf-8").strip(), "80")
            node.chmod(0o444)
            blocked = apply_threshold(70, confirm=True, state_file=state, node=str(node), sysfs_root=root)
            self.assertFalse(blocked["written"])
            self.assertEqual(node.read_text(encoding="utf-8").strip(), "80")
            with self.assertRaises(SafetyError):
                apply_threshold(10, confirm=True, state_file=state, sysfs_root=root)
            with self.assertRaises(SafetyError):
                apply_threshold(True, confirm=True, state_file=state, sysfs_root=root)
            with self.assertRaises(SafetyError):
                apply_threshold(101, confirm=True, state_file=state, sysfs_root=root)
            traversal = root / "BAT0" / ".." / ".." / "charge_control_end_threshold"
            with self.assertRaises(SafetyError):
                apply_threshold(80, confirm=True, state_file=state, node=str(traversal), sysfs_root=root)
            missing = apply_threshold(80, confirm=True, state_file=state, sysfs_root=root / "absent")
            self.assertFalse(missing["written"])


class PowerUndervoltProbeTests(unittest.TestCase):
    def test_power_map_and_no_fake_apply(self):
        described = list_plans()
        guids = {item["windows_guid"] for item in described["plans"]}
        self.assertIn("381b4222-f694-41f0-9685-ff5bb260df2e", guids)
        self.assertEqual({item["id"] for item in PLANS}, {"saver", "balanced", "performance", "ultimate"})
        dry = apply_ppd("balanced", confirm=False)
        self.assertFalse(dry["executed"])
        forced = apply_ppd("performance", confirm=True)
        # In dieser VM fehlt powerprofilesctl. Dann bleibt es ein Plan.
        if described["powerprofilesctl"] is None:
            self.assertFalse(forced["executed"])

    def test_undervolt_is_stored_only(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            record = save_offsets(
                {"cpu": {"vendor": "intel", "core_offset_mv": -50, "cache_offset_mv": -40}, "gpu": {"vendor": "nvidia", "offset_mv": -25, "core_clock_mhz": 50, "mem_clock_mhz": 0}},
                path,
            )
            self.assertFalse(record["applied"])
            self.assertFalse(record["voltage_written"])
            self.assertTrue(any("Intel" in note for note in record["notes"]))
            with self.assertRaises(SafetyError):
                save_offsets({"cpu": {"vendor": "intel", "core_offset_mv": -500}, "gpu": {"vendor": "nvidia"}}, path)

    def test_probe_is_honest(self):
        report = probe()
        self.assertEqual(report["os"], "linux")
        self.assertTrue(report["executed_local_read"])
        self.assertIsInstance(report["limitations"], list)
        for vendor in vendor_map()["vendors"]:
            loaded = any(item["loaded"] for item in vendor["modules"])
            present = any(item["exists"] for item in vendor["sysfs"])
            self.assertEqual(vendor["usable"], loaded and present)
            if not loaded:
                self.assertFalse(vendor["usable"])
        # Umgebung darf keine Werte erfinden, wenn Knoten fehlen.
        if not report["readings"]["power_supply"]:
            self.assertTrue(any("power_supply" in item or "Batterie" in item for item in report["limitations"]))


if __name__ == "__main__":
    unittest.main()
