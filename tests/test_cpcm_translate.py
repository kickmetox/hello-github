import json
import unittest
from pathlib import Path

from cpcm.catalog import plan, validate_package
from cpcm.paths import World, identity_for_home
from cpcm.shortcuts import translate_shortcut
from cpcm.themes import theme_artifacts
from cpcm.translate import translate_config


class TranslateTests(unittest.TestCase):
    def test_shell_becomes_powershell_and_registry(self):
        source = identity_for_home(World.LINUX, Path("/home/ada"), "ada")
        target = identity_for_home(World.WINDOWS, Path(r"C:\Users\ada"), "ada")
        text = "export EDITOR=nvim\nexport NOTES=\"/home/ada/Documents/notes\"\nalias ll='ls -al'\n"
        result = translate_config(text, source, target)
        self.assertIn("SetEnvironmentVariable('EDITOR'", result["text"])
        self.assertIn("Get-ChildItem -Force", result["text"])
        self.assertIn('"EDITOR"="nvim"', result["reg"])
        self.assertIn(r"C:\Users\ada\Documents\notes", result["text"])

    def test_json_paths_and_shortcut(self):
        source = identity_for_home(World.LINUX, Path("/home/ada"), "ada")
        target = identity_for_home(World.WINDOWS, Path(r"C:\Users\ada"), "ada")
        result = translate_config('{\n  "notes": "/home/ada/Documents/notes",\n  "key": "ctrl+alt+super+k"\n}\n', source, target)
        parsed = json.loads(result["text"])
        self.assertEqual(parsed["notes"], r"C:\Users\ada\Documents\notes")
        self.assertEqual(parsed["key"], "Ctrl+Alt+Win+K")

    def test_shortcut_order(self):
        self.assertEqual(translate_shortcut("Strg+Alt+Super+K", World.WINDOWS), "Ctrl+Alt+Win+K")
        self.assertEqual(translate_shortcut("Win+Shift+P", World.LINUX), "Shift+Super+P")

    def test_theme_rejects_bad_color(self):
        with self.assertRaises(ValueError):
            theme_artifacts({"accent": "blue"}, World.LINUX)

    def test_package_plan_rejects_injection(self):
        planned = plan(["Notepad++", "Photoshop"], World.LINUX, "apt")
        commands = " ".join(item["command"] or "" for item in planned["items"])
        self.assertIn("notepad-next", commands)
        self.assertIn("gimp", commands)
        self.assertNotIn(";", commands)
        with self.assertRaises(ValueError):
            validate_package("apt", "vim;rm -rf /")
        with self.assertRaises(ValueError):
            plan(["git"], World.LINUX, "winget")
