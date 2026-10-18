import tempfile
import unittest
from pathlib import Path

from cpcm.hardware import validate_profile, write_charge_threshold


class HardwareTests(unittest.TestCase):
    def test_curve_must_rise(self):
        with self.assertRaises(ValueError):
            validate_profile({"name": "Kaputt", "curve": [[70, 10], [40, 20]], "cpu_max_pct": 80, "charge_start": 40, "charge_stop": 80, "undervolt_mv": 0, "linux_power": "balanced"})

    def test_charge_threshold_writes_only_existing_node(self):
        with tempfile.TemporaryDirectory() as tmp:
            node = Path(tmp) / "charge_control_end_threshold"
            node.write_text("100", encoding="utf-8")
            self.assertEqual(write_charge_threshold("BAT0", "end", 80, node=node), str(node))
            self.assertEqual(node.read_text(encoding="utf-8"), "80")
        with self.assertRaises(ValueError):
            write_charge_threshold("BAT0", "end", 10, node=Path("fehlt"))
