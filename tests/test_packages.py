import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crossos.migrator.apps import CATALOG, plan_apps
from crossos.migrator.packages import MANAGERS, PackageBridge
from crossos.safety import SafetyError, validate_package_name


class PackageTests(unittest.TestCase):
    def setUp(self):
        self._env = os.environ.pop("CROSSOS_ALLOW_PACKAGE_INSTALL", None)

    def tearDown(self):
        if self._env is not None:
            os.environ["CROSSOS_ALLOW_PACKAGE_INSTALL"] = self._env

    def test_injection_does_not_produce_a_command(self):
        bridge = PackageBridge()
        samples = [
            "vim; rm -rf /",
            "foo && bar",
            "$(reboot)",
            "`id`",
            "ok\nrm",
            "a|b",
            "../../../bin/sh",
            "foo > /tmp/x",
            "pkg\x00name",
            "-rf",
            "name with space",
        ]
        for sample in samples:
            with self.subTest(sample=sample):
                with self.assertRaises(SafetyError) as caught:
                    bridge.plan("apt", [sample])
                self.assertNotIn(";", str(caught.exception))
                self.assertNotIn("rm", str(caught.exception))
                self.assertNotIn(sample, str(caught.exception))

    def test_valid_plan_is_dry_run(self):
        planned = PackageBridge().plan("apt", ["git", "vim"])
        self.assertEqual(planned["argv"], ["apt-get", "install", "--yes", "git", "vim"])
        self.assertNotIn(";", planned["shell"])
        self.assertTrue(planned["dry_run"])
        self.assertFalse(planned["executed"])

    def test_drive_blocked_without_env(self):
        result = PackageBridge().drive("apt", ["git"], confirm=True, dry_run=False)
        self.assertFalse(result["executed"])
        self.assertIn("CROSSOS_ALLOW_PACKAGE_INSTALL", result["blocked"])

    def test_all_managers_and_catalog_names(self):
        self.assertEqual(set(MANAGERS), {"winget", "scoop", "apt", "pacman", "dnf", "flatpak", "snap"})
        detected = PackageBridge().detect()
        self.assertIn("apt", detected["managers"])
        bridge = PackageBridge()
        keys = {"apt", "dnf", "pacman", "flatpak", "snap", "winget", "scoop"}
        for app in CATALOG:
            for side_name in ("windows", "linux"):
                side = app.get(side_name) or {}
                for key, value in side.items():
                    if key in keys and isinstance(value, str):
                        validate_package_name(value)
                        bridge.plan(key if key != "apt" else "apt", [value])
            for option in app.get("linux_options", []):
                for key, value in option.items():
                    if key in keys and isinstance(value, str):
                        validate_package_name(value)

    def test_photoshop_is_workflow_not_fake_port(self):
        plan = plan_apps(["Photoshop", "Notepad++"], target_os="linux")
        by_id = {item["id"]: item for item in plan["apps"]}
        photo = by_id["photoshop"]
        self.assertEqual(photo["equivalence"], "workflow")
        shells = [item["shell"] for alt in photo["alternatives"] for item in alt["plans"]]
        self.assertTrue(any("gimp" in shell for shell in shells))
        self.assertTrue(any("krita" in shell for shell in shells))
        self.assertNotIn("photoshop", " ".join(shells).lower())
        note = by_id["notepadpp"]
        self.assertEqual(note["equivalence"], "port")
        self.assertTrue(any("notepadnext" in plan_item["shell"] for plan_item in note["target_plans"]))
        self.assertFalse(plan["executed"])
        self.assertGreaterEqual(len(CATALOG), 40)


if __name__ == "__main__":
    unittest.main()
