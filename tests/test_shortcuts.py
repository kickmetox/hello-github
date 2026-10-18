import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crossos.migrator.gestures import gesture_bridge
from crossos.migrator.shortcuts import translate_shortcut, translate_vscode_keybindings
from crossos.migrator.theme import theme_bridge
from crossos.safety import SafetyError

ROOT = Path(__file__).resolve().parents[1]


class ShortcutTests(unittest.TestCase):
    def test_german_labels_and_vscode(self):
        result = translate_shortcut("Strg+Alt+Entf", target_os="windows")
        self.assertEqual(result["vscode_windows"], "ctrl+alt+delete")
        self.assertEqual(result["vscode_linux"], "ctrl+alt+delete")
        self.assertEqual(result["windows_label"], "Strg+Alt+Entf")
        self.assertFalse(result["executed"])

    def test_super_win_meta(self):
        result = translate_shortcut("Super+T", target_os="windows")
        self.assertEqual(result["vscode_windows"], "win+t")
        self.assertEqual(result["vscode_linux"], "meta+t")
        self.assertEqual(result["windows_label"], "Win+T")
        self.assertEqual(result["linux_label"], "Super+T")

    def test_chord_and_spaces(self):
        result = translate_shortcut("ctrl + k ctrl + s", target_os="linux")
        self.assertEqual(result["vscode_linux"], "ctrl+k ctrl+s")
        self.assertEqual(result["linux_label"], "Strg+K Strg+S")

    def test_cmd_becomes_ctrl(self):
        result = translate_shortcut("cmd+c", target_os="linux")
        self.assertEqual(result["vscode_linux"], "ctrl+c")
        self.assertTrue(any("cmd" in note for note in result["notes"]))

    def test_rejects_injection_key(self):
        with self.assertRaises(SafetyError):
            translate_shortcut("ctrl+;rm", target_os="windows")

    def test_vscode_file(self):
        payload = json.loads((ROOT / "examples" / "vscode-keybindings.json").read_text(encoding="utf-8"))
        result = translate_vscode_keybindings(payload, target_os="windows")
        keys = [item["key"] for item in result["bindings"]]
        self.assertEqual(keys[0], "ctrl+shift+p")
        self.assertEqual(keys[1], "ctrl+k ctrl+s")
        self.assertEqual(keys[2], "win+t")
        self.assertFalse(result["executed"])


class GestureThemeTests(unittest.TestCase):
    def test_gestures_are_plans(self):
        profile = json.loads((ROOT / "examples" / "gestures.json").read_text(encoding="utf-8"))
        result = gesture_bridge(profile)
        self.assertFalse(result["executed"])
        self.assertIn("natural-scroll", result["gnome_argv"][0])
        self.assertIn("ScrollDirection", result["windows_reg"])
        self.assertIn("dword:00000001", result["windows_reg"])
        self.assertIn("MatchUdevType=touchpad", result["libinput_quirks"])

    def test_theme_schedule_and_accent(self):
        profile = json.loads((ROOT / "examples" / "theme.json").read_text(encoding="utf-8"))
        result = theme_bridge(profile, user="andreas")
        self.assertFalse(result["executed"])
        self.assertIn("prefer-dark", " ".join(" ".join(cmd) for cmd in result["gnome"]))
        self.assertIn(r"C:\Users\andreas\AppData\Local\backgrounds\graphite.png", result["wallpaper_windows"])
        self.assertTrue(result["schedule"]["active"])
        self.assertIn("nicht als Timer", result["schedule"]["bash"])
        with self.assertRaises(SafetyError):
            theme_bridge({"accent": "red;rm"})


if __name__ == "__main__":
    unittest.main()
