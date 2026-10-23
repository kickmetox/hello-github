"""Hilfetext und Tasten, ohne ein Win32-Fenster zu erzeugen."""

from __future__ import annotations

import os
import unittest

from flare.helptext import description, features, help_text, short_description
from flare.window import VK_DOWN, VK_ESCAPE, VK_F1, VK_RETURN, help_text as window_help
from flare.window import shortcut_action


class HelpTextTests(unittest.TestCase):
    def test_help_text_contains_short_description_and_features(self) -> None:
        text = help_text()
        self.assertEqual(window_help(), text)
        self.assertIn("Kurzbeschreibung", text)
        self.assertIn("Beschreibung", text)
        self.assertIn("Feature-Liste", text)
        self.assertIn(short_description(), text)
        self.assertIn(description(), text)
        self.assertGreater(len(description()), len(short_description()))
        self.assertGreaterEqual(len(features()), 3)
        for item in features():
            self.assertIn(item, text)
        self.assertIn("Strg+Alt+Leertaste", short_description())
        self.assertIn("Windows 11", short_description())
        self.assertIn("F1", description())
        joined = "\n".join(features())
        for fact in (
            "nvcuda.dll",
            "node_modules",
            ".git",
            "47731",
            "flare.client.Client",
            "%LOCALAPPDATA%\\Programs\\Flare",
            "%LOCALAPPDATA%\\Flare",
            "2+2*3",
            "85 %",
            "35 %",
            "exclude_drives",
            "index_network",
            "OneDrive",
            "Dropbox",
            "Google Drive",
            "USB-Sticks",
            "Keine Websuche",
            "E-Mail",
            "Kontakte",
            "Chats",
            "Index speichern",
            "Index kopieren",
            "Index vergleichen",
            "index-save",
            "index-load",
            "index-copy",
            "index-compare",
            "Menü Index",
            "Laden",
            "index-create",
            "index-add",
            "--root",
            "--list",
            "query --index",
            "Index anlegen",
            "Dokumentenverwaltung",
            "nur Namen",
        ):
            self.assertIn(fact, joined)


class HelpShortcutTests(unittest.TestCase):
    def test_save_dialog_is_not_built_at_import(self) -> None:
        import inspect

        import flare.window as window

        dialog = inspect.getsource(window._index_file_dialog)
        self.assertIn("GetSaveFileNameW", dialog)
        self.assertIn("GetOpenFileNameW", dialog)
        self.assertNotIn("WINFUNCTYPE", dialog)
        self.assertNotIn("WINFUNCTYPE", inspect.getsource(window.choose_index_save_path))
        self.assertNotIn("WINFUNCTYPE", inspect.getsource(window.choose_index_open_path))
        self.assertIn("flare-index.db", inspect.getsource(window.choose_index_save_path))
        menu = inspect.getsource(window.NativeWindow._install_index_menu)
        self.assertNotIn("WINFUNCTYPE", menu)
        self.assertNotIn("wstring_at", menu)
        self.assertIn("CreateMenu", menu)
        for label in ("Speichern…", "Laden…", "Vergleichen…", "Kopieren…", "Anlegen…", "Index"):
            self.assertIn(label, menu)
        confirm = inspect.getsource(window.confirm_index_replace)
        self.assertIn("MessageBoxW", confirm)
        self.assertIn("Der laufende Index wird durch diese Datei ersetzt. Fortfahren?", confirm)
        self.assertNotIn("WINFUNCTYPE", confirm)
        self.assertNotIn("wstring_at", inspect.getsource(window))
        help_source = inspect.getsource(window.HelpWindow)
        self.assertIn("Index speichern", help_source)
        self.assertIn("Index kopieren", help_source)
        self.assertIn("Index vergleichen", help_source)
        self.assertIn("Index anlegen", help_source)
        self.assertIn("VK_ESCAPE", help_source)
        if os.name != "nt":
            self.assertIsNone(window.choose_index_save_path(0))
            self.assertIsNone(window.choose_index_open_path(0))
            self.assertFalse(window.confirm_index_replace(0))

    def test_list_clears_old_rows_and_status_shows_the_path(self) -> None:
        import inspect

        from flare.window import NativeWindow, list_item_height, replace_list_rows, result_labels, search_status

        previous = [
            "1min ai",
            "7-zip file manager",
            "administrative tools",
            "application verifier (wow)",
            "ashampoo pdf pro",
            "ashampoo winoptimizer pro 29",
        ]
        hits = [{"name": f"hit-{i}", "path": rf"F:\hit-{i}", "via": "prefix"} for i in range(12)]
        hits[0] = {"name": "Xchange", "path": r"F:\Xchange", "via": "prefix"}
        labels = result_labels(hits)
        shown = replace_list_rows(previous, labels)
        self.assertEqual(len(shown), 12)
        self.assertEqual(shown, labels)
        self.assertFalse(set(previous) & set(shown))
        self.assertEqual(shown[0], "Xchange")
        self.assertNotIn("F:\\", shown[0])
        self.assertEqual(
            search_status("Suche", 3.71, 12, r"F:\Xchange"),
            r"Suche · 3.71 ms · 12 Treffer · F:\Xchange",
        )
        self.assertGreaterEqual(list_item_height(18, 0), 22)
        self.assertGreater(list_item_height(18, 2), list_item_height(18, 0))
        source = inspect.getsource(NativeWindow._run_search)
        self.assertIn("LB_RESETCONTENT", source)
        self.assertIn("_erase_list", source)
        self.assertIn("InvalidateRect", inspect.getsource(NativeWindow._erase_list))
        self.assertIn("LB_SETITEMHEIGHT", inspect.getsource(NativeWindow._apply_list_height))
        self.assertIn("Speichern…", inspect.getsource(NativeWindow._install_index_menu))

    def test_f1_opens_help_and_escape_closes_it(self) -> None:
        self.assertEqual(shortcut_action(VK_F1, help_open=False, help_target=False), "help")
        self.assertEqual(shortcut_action(VK_F1, help_open=True, help_target=True), "help")
        self.assertEqual(shortcut_action(VK_ESCAPE, help_open=True, help_target=True), "close-help")
        self.assertEqual(shortcut_action(VK_ESCAPE, help_open=True, help_target=False), "close-help")
        self.assertEqual(shortcut_action(VK_ESCAPE, help_open=False, help_target=False), "hide")
        self.assertIsNone(shortcut_action(VK_DOWN, help_open=True, help_target=True))
        self.assertEqual(shortcut_action(VK_RETURN, help_open=False, help_target=False), "open")
        self.assertIsNone(shortcut_action(VK_RETURN, help_open=True, help_target=True))


if __name__ == "__main__":
    unittest.main()
