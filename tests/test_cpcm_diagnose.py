import unittest

from cpcm.diagnose import analyze, lint_user_script, script_is_allowed
from cpcm.filesystems import repair_plan


class DiagnoseTests(unittest.TestCase):
    def test_windows_and_linux_signatures(self):
        windows = analyze("Installation stoppte mit Unbekannter Fehler 0x80070002")
        self.assertEqual(windows[0]["id"], "win-file-not-found")
        self.assertIn("fehlt", windows[0]["explanation"])
        self.assertEqual(analyze("bash: line 1: 4242 Segmentation fault (core dumped) ./tool")[0]["id"], "segfault")
        library = analyze("error while loading shared libraries: libssl.so.3: cannot open shared object file")
        self.assertEqual(library[0]["id"], "missing-so")
        self.assertIn("libssl.so.3", library[0]["linux_script"])

    def test_allowlist_blocks_destructive_lines(self):
        self.assertFalse(script_is_allowed("rm -rf /"))
        self.assertFalse(script_is_allowed("sudo dpkg --configure -a; sudo rm -rf /"))
        self.assertTrue(script_is_allowed("sudo dpkg --configure -a\nsudo apt-get -f install\n"))
        with self.assertRaises(ValueError):
            lint_user_script("chmod 777 /\n")

    def test_filesystem_plan_does_not_claim_native_windows_fsck(self):
        plan = repair_plan("windows", "ext4", "/dev/sda2")
        text = " ".join(plan["commands"])
        self.assertIn("wsl", text)
        self.assertIn("-n", text)
        self.assertFalse(plan["writes"])
        with self.assertRaises(ValueError):
            repair_plan("linux", "ntfs", "/dev/sda2; rm -rf /")
