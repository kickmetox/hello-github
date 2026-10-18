import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crossos.migrator.paths import translate_path
from crossos.safety import SafetyError


class PathTests(unittest.TestCase):
    def test_linux_config_to_windows(self):
        translated, unmapped = translate_path("/home/andreas/.config/Code/User/settings.json", "windows")
        self.assertFalse(unmapped)
        self.assertEqual(translated, r"C:\Users\andreas\AppData\Roaming\Code\User\settings.json")

    def test_windows_roaming_to_linux(self):
        translated, unmapped = translate_path(r"C:\Users\andreas\AppData\Roaming\Code\User\settings.json", "linux")
        self.assertFalse(unmapped)
        self.assertEqual(translated, "/home/andreas/.config/Code/User/settings.json")

    def test_local_share_and_cache(self):
        share, _ = translate_path("/home/ada/.local/share/fonts/a.ttf", "windows")
        cache, _ = translate_path("/home/ada/.cache/thumbnails/x", "windows")
        state, _ = translate_path("/home/ada/.local/state/app", "windows")
        binary, _ = translate_path("/home/ada/.local/bin/nvim", "windows")
        self.assertEqual(share, r"C:\Users\ada\AppData\Local\fonts\a.ttf")
        self.assertEqual(cache, r"C:\Users\ada\AppData\Local\Cache\thumbnails\x")
        self.assertEqual(state, r"C:\Users\ada\AppData\Local\State\app")
        self.assertEqual(binary, r"C:\Users\ada\AppData\Local\bin\nvim")

    def test_wsl_mount_and_program_files(self):
        win, _ = translate_path("/mnt/c/Users/andreas/Documents/a.txt", "windows")
        self.assertEqual(win, r"C:\Users\andreas\Documents\a.txt")
        wsl, unmapped = translate_path(r"C:\Program Files\Git\bin\git.exe", "wsl")
        self.assertEqual(wsl, "/mnt/c/Program Files/Git/bin/git.exe")
        self.assertFalse(unmapped)
        linux, unmapped = translate_path(r"C:\Program Files\Git\bin\git.exe", "linux")
        self.assertTrue(unmapped)
        self.assertEqual(linux, "/mnt/c/Program Files/Git/bin/git.exe")

    def test_tilde_and_appdata_env(self):
        translated, _ = translate_path("~/.config/foo", "windows", "andreas")
        self.assertEqual(translated, r"C:\Users\andreas\AppData\Roaming\foo")
        back, _ = translate_path(r"%APPDATA%\Code\settings.json", "linux", "andreas")
        self.assertEqual(back, "/home/andreas/.config/Code/settings.json")

    def test_preserves_path_user(self):
        translated, _ = translate_path("/home/ada/.config/x", "windows", "andreas")
        self.assertTrue(translated.startswith("C:\\Users\\ada\\"))

    def test_rejects_bad_user_token(self):
        with self.assertRaises(SafetyError):
            translate_path("~/.config/x", "windows", "ada;rm")

    def test_roundtrip_home(self):
        forward, _ = translate_path("/home/andreas/.config/git/ignore", "windows")
        backward, _ = translate_path(forward, "linux")
        self.assertEqual(backward, "/home/andreas/.config/git/ignore")


if __name__ == "__main__":
    unittest.main()
