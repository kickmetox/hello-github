"""Hilfetext und Tasten, ohne ein Win32-Fenster zu erzeugen."""

from __future__ import annotations

import os
import unittest

from flare.helptext import description, features, help_text, short_description
from flare.launch import (
    editor_command,
    explorer_command_line,
    explorer_select_args,
    list_sendto_entries,
    quote_command_path,
    reveal_in_explorer,
)
from flare.window import VK_APPS, VK_DOWN, VK_ESCAPE, VK_F1, VK_F10, VK_RETURN, help_text as window_help
from flare.window import copy_unicode_text, hit_row, row_path, shortcut_action


class HelpTextTests(unittest.TestCase):
    def test_help_text_contains_short_description_and_features(self) -> None:
        text = help_text()
        self.assertEqual(window_help(), text)
        self.assertIn("Kurzbeschreibung", text)
        self.assertIn("Beschreibung", text)
        self.assertIn("Feature-Liste", text)
        self.assertIn(short_description(), text)
        self.assertIn(description(), text)
        self.assertEqual(
            [line for line in text.splitlines() if line in ("Andreas Meyer", "ame@sellerbach.de")],
            ["Andreas Meyer", "ame@sellerbach.de"],
        )
        self.assertEqual(text.count("@"), 1)
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
            "Sichern",
            "Laden",
            "Vergleichen",
            "flare-index.db",
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
        for label in (
            "Sichern…",
            "Laden…",
            "Vergleichen…",
            "Kopieren…",
            "Anlegen…",
            "Index",
            "Info",
            "Andreas Meyer",
            "ame@sellerbach.de",
        ):
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
        self.assertIn("Sichern…", inspect.getsource(NativeWindow._install_index_menu))

    def test_f1_opens_help_and_escape_closes_it(self) -> None:
        self.assertEqual(shortcut_action(VK_F1, help_open=False, help_target=False), "help")
        self.assertEqual(shortcut_action(VK_F1, help_open=True, help_target=True), "help")
        self.assertEqual(shortcut_action(VK_ESCAPE, help_open=True, help_target=True), "close-help")
        self.assertEqual(shortcut_action(VK_ESCAPE, help_open=True, help_target=False), "close-help")
        self.assertEqual(shortcut_action(VK_ESCAPE, help_open=False, help_target=False), "hide")
        self.assertIsNone(shortcut_action(VK_DOWN, help_open=True, help_target=True))
        self.assertEqual(shortcut_action(VK_RETURN, help_open=False, help_target=False), "open")
        self.assertIsNone(shortcut_action(VK_RETURN, help_open=True, help_target=True))
        self.assertEqual(shortcut_action(VK_APPS, help_open=False, help_target=False), "context")
        self.assertEqual(shortcut_action(VK_F10, help_open=False, help_target=False, shift=True), "context")
        self.assertIsNone(shortcut_action(VK_F10, help_open=False, help_target=False, shift=False))
        self.assertIsNone(shortcut_action(VK_APPS, help_open=True, help_target=True))
        self.assertEqual(shortcut_action(VK_APPS, help_open=True, help_target=False), "context")
        for label in (
            "Öffnen",
            "Speicherort öffnen",
            "Im Editor bearbeiten",
            "Senden an",
            "Pfad kopieren",
            "Als Pfad kopieren",
            "Rechtsklick",
            "Umschalt+F10",
            "notepad.exe",
            "SendTo",
        ):
            self.assertIn(label, help_text())


class IconTests(unittest.TestCase):
    def test_artwork_ico_is_used_by_window_exe_and_installer(self) -> None:
        import importlib.util
        import struct

        from flare.window import apply_flare_icons, flare_icon_path, load_flare_icons

        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        png = os.path.join(root, "packaging", "windows", "flare-icon.png")
        ico = os.path.join(root, "packaging", "windows", "flare.ico")
        self.assertTrue(os.path.isfile(png))
        self.assertTrue(os.path.isfile(ico))
        self.assertTrue(flare_icon_path().endswith("flare.ico"))
        self.assertTrue(os.path.isfile(flare_icon_path()))
        if os.name != "nt":
            self.assertEqual(load_flare_icons(), (0, 0))
            apply_flare_icons(0, 1, 1)

        with open(ico, "rb") as handle:
            data = handle.read()
        _reserved, kind, count = struct.unpack_from("<HHH", data, 0)
        self.assertEqual((_reserved, kind), (0, 1))
        self.assertEqual(count, 4)
        sizes = []
        for index in range(count):
            width, height, _colors, _reserved_b, planes, bitcount, length, offset = struct.unpack_from(
                "<BBBBHHII", data, 6 + 16 * index
            )
            self.assertEqual((planes, bitcount), (1, 32))
            blob = data[offset : offset + length]
            self.assertTrue(blob.startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertEqual(blob[12:16], b"IHDR")
            image_w, image_h = struct.unpack(">II", blob[16:24])
            self.assertEqual(image_w, image_h)
            self.assertEqual(width, 0 if image_w >= 256 else image_w)
            self.assertEqual(height, 0 if image_h >= 256 else image_h)
            sizes.append(image_w)
        self.assertEqual(sizes, [16, 32, 48, 256])

        spec_path = os.path.join(root, "packaging", "windows", "make_icon.py")
        loaded = importlib.util.spec_from_file_location("flare_make_icon", spec_path)
        assert loaded is not None and loaded.loader is not None
        module = importlib.util.module_from_spec(loaded)
        loaded.loader.exec_module(module)
        with open(png, "rb") as handle:
            png_bytes = handle.read()
        _width, _height, rgba = module.decode_png(png_bytes)
        self.assertEqual((_width, _height), (1024, 1024))
        scaled = module.box_resize(_width, _height, rgba, 32)
        self.assertTrue(module.looks_like_artwork(scaled))

        from pathlib import Path

        tree = Path(root)
        window_source = (tree / "flare" / "window.py").read_text(encoding="utf-8")
        spec = (tree / "packaging" / "windows" / "flare.spec").read_text(encoding="utf-8")
        nsi = (tree / "packaging" / "windows" / "flare.nsi").read_text(encoding="utf-8")
        for token in ("WM_SETICON", "ICON_BIG", "ICON_SMALL", "hIcon", "LoadImageW", "GCLP_HICON"):
            self.assertIn(token, window_source)
        self.assertNotIn("wstring_at", window_source)
        self.assertIn("flare.ico", spec)
        self.assertIn("icon=icon", spec)
        self.assertIn('MUI_ICON "${__FILEDIR__}\\flare.ico"', nsi)
        self.assertIn('MUI_UNICON "${__FILEDIR__}\\flare.ico"', nsi)


class ResultMenuTests(unittest.TestCase):
    def test_empty_space_and_missing_path_do_not_qualify(self) -> None:
        self.assertEqual(hit_row(0, 0, 3, 0, 0, 200, 24, 12, 8), 0)
        self.assertIsNone(hit_row(2, 0, 3, 0, 48, 200, 72, 12, 90))
        self.assertIsNone(hit_row(0, 1, 3, 0, 0, 200, 24, 12, 8))
        self.assertIsNone(hit_row(4, 0, 3, 0, 0, 200, 24, 12, 8))
        self.assertEqual(row_path({"path": r"F:\Xchange"}), r"F:\Xchange")
        self.assertEqual(row_path({"kind": "calc", "path": ""}), "")
        self.assertEqual(row_path(None), "")

    def test_context_menu_is_created_only_on_windows(self) -> None:
        import inspect

        import flare.window as window

        popup = inspect.getsource(window.NativeWindow._popup_result_menu)
        self.assertIn('sys.platform != "win32"', popup)
        self.assertIn("CreatePopupMenu", popup)
        labels = (
            "Öffnen",
            "Speicherort öffnen",
            "Im Editor bearbeiten",
            "Senden an",
            "Pfad kopieren",
            "Als Pfad kopieren",
        )
        places = []
        for label in labels:
            token = f'"{label}"'
            self.assertIn(token, popup)
            places.append(popup.index(token))
        self.assertEqual(places, sorted(places))
        self.assertIn("Keine Ziele", popup)
        listing = inspect.getsource(window.NativeWindow._list_wndproc)
        self.assertIn("WM_CONTEXTMENU", listing)
        self.assertIn("WM_RBUTTONUP", listing)
        parent = inspect.getsource(window.NativeWindow._wndproc)
        self.assertIn("WM_CONTEXTMENU", parent)
        self.assertIn("WM_RBUTTONUP", parent)
        self.assertIn("CF_UNICODETEXT", inspect.getsource(window.copy_unicode_text))
        self.assertIn("utf-16-le", inspect.getsource(window.copy_unicode_text))
        self.assertNotIn("wstring_at", inspect.getsource(window))
        self.assertIn("Sichern…", inspect.getsource(window.NativeWindow._install_index_menu))
        self.assertIn("Andreas Meyer", inspect.getsource(window.NativeWindow._install_index_menu))
        if os.name != "nt":
            self.assertFalse(copy_unicode_text(r"D:\notes.txt"))

    def test_explorer_select_quotes_spaces_for_files_and_folders(self) -> None:
        import inspect
        import sys
        from unittest import mock

        file_args = explorer_select_args(r"D:\notes.txt")
        folder_args = explorer_select_args(r"C:\Users\Andreas\Documents")
        spaced = explorer_select_args(r"C:\Program Files\Flare Setup\readme.txt")
        spaced_folder = explorer_select_args(r"C:\Program Files")
        root_args = explorer_select_args(r"F:\\")
        self.assertEqual(file_args, ["explorer.exe", r"/select,D:\notes.txt"])
        self.assertEqual(folder_args, ["explorer.exe", r"/select,C:\Users\Andreas\Documents"])
        self.assertEqual(spaced, ["explorer.exe", '/select,"C:\\Program Files\\Flare Setup\\readme.txt"'])
        self.assertEqual(spaced_folder, ["explorer.exe", '/select,"C:\\Program Files"'])
        self.assertEqual(root_args, ["explorer.exe", "F:\\"])
        self.assertNotIn("/select", root_args[1])
        self.assertEqual(explorer_select_args("E:"), ["explorer.exe", "E:\\"])
        self.assertEqual(
            explorer_select_args(r"F:\Xchange"),
            ["explorer.exe", r"/select,F:\Xchange"],
        )
        self.assertEqual(
            explorer_command_line(spaced),
            'explorer.exe /select,"C:\\Program Files\\Flare Setup\\readme.txt"',
        )
        self.assertEqual(explorer_select_args(""), [])
        built = inspect.getsource(explorer_select_args)
        for banned in ("os.walk", "listdir", "scandir", "exists"):
            self.assertNotIn(banned, built)
        reveal = inspect.getsource(reveal_in_explorer)
        for banned in ("os.walk", "listdir", "scandir", "rglob"):
            self.assertNotIn(banned, reveal)
        self.assertEqual(reveal_in_explorer(""), "Pfad fehlt.")
        self.assertEqual(reveal_in_explorer(r"D:\no\such\notes.txt"), "Datei fehlt.")
        with (
            mock.patch.object(sys, "platform", "win32"),
            mock.patch("flare.launch.os.path.exists", return_value=True),
            mock.patch("flare.launch.subprocess.Popen", side_effect=OSError("missing")),
        ):
            self.assertEqual(reveal_in_explorer(r"D:\notes.txt"), "Explorer startet nicht.")
        with (
            mock.patch.object(sys, "platform", "win32"),
            mock.patch("flare.launch.os.path.exists", return_value=True),
            mock.patch("flare.launch.subprocess.Popen") as popen,
        ):
            self.assertIsNone(reveal_in_explorer(r"C:\Users\Andreas\Documents"))
            self.assertEqual(popen.call_args.args[0], r"explorer.exe /select,C:\Users\Andreas\Documents")
            self.assertIsNone(reveal_in_explorer(r"C:\Program Files\readme.txt"))
            self.assertEqual(
                popen.call_args.args[0],
                'explorer.exe /select,"C:\\Program Files\\readme.txt"',
            )
            self.assertIsNone(reveal_in_explorer(r"E:\\"))
            self.assertEqual(popen.call_args.args[0], "explorer.exe E:\\")
            self.assertFalse(popen.call_args.kwargs.get("shell", False))

    def test_quoted_path_keeps_backslashes_and_quotes_spaces(self) -> None:
        plain = quote_command_path(r"F:\Xchange")
        spaced = quote_command_path(r"C:\Program Files\Flare Setup\readme.txt")
        self.assertEqual(plain, '"F:\\Xchange"')
        self.assertIn("\\", plain)
        self.assertFalse(plain.startswith("F:"))
        self.assertEqual(spaced, '"C:\\Program Files\\Flare Setup\\readme.txt"')
        self.assertTrue(spaced.startswith('"') and spaced.endswith('"'))
        self.assertIn(" ", spaced)
        self.assertNotIn("/", spaced)
        self.assertIn("\\", spaced)

    def test_sendto_listing_skips_desktop_ini(self) -> None:
        import inspect
        import tempfile
        from pathlib import Path

        source = inspect.getsource(list_sendto_entries)
        self.assertNotIn("os.walk", source)
        self.assertNotIn("rglob", source)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "desktop.ini").write_text("[.ShellClassInfo]", encoding="utf-8")
            (root / "Desktop.ini").write_text("doppelt", encoding="utf-8")
            (root / ".hidden.lnk").write_text("hidden", encoding="utf-8")
            (root / "Notepad.lnk").write_text("notepad", encoding="utf-8")
            (root / "Mail Recipient.lnk").write_text("mail", encoding="utf-8")
            entries = list_sendto_entries(root)
            empty = Path(tmp) / "leer"
            empty.mkdir()
            self.assertEqual(list_sendto_entries(empty), [])
        self.assertEqual([item["name"] for item in entries], ["Mail Recipient", "Notepad"])
        self.assertTrue(all("desktop.ini" not in item["path"].casefold() for item in entries))
        self.assertTrue(all(not item["name"].startswith(".") for item in entries))
        self.assertEqual(list_sendto_entries(None), [])
        self.assertEqual(list_sendto_entries(root / "fehlt"), [])

    def test_editor_command_uses_config_then_environment_and_refuses_a_directory(self) -> None:
        argv, status = editor_command(
            r"D:\notes.txt",
            config={"editor": "config-editor"},
            environ={"EDITOR": "env-editor"},
            is_dir=False,
        )
        self.assertEqual(argv, ["config-editor", r"D:\notes.txt"])
        self.assertIsNone(status)
        argv, status = editor_command(
            r"D:\notes.txt",
            config={"editor": "  "},
            environ={"EDITOR": "env-editor"},
            is_dir=False,
        )
        self.assertEqual(argv, ["env-editor", r"D:\notes.txt"])
        self.assertIsNone(status)
        argv, status = editor_command(r"D:\notes.txt", config={}, environ={}, is_dir=False)
        self.assertEqual(argv, ["notepad.exe", r"D:\notes.txt"])
        self.assertIsNone(status)
        argv, status = editor_command(
            r"D:\Ordner",
            config={"editor": "config-editor"},
            environ={"EDITOR": "env-editor"},
            is_dir=True,
        )
        self.assertIsNone(argv)
        self.assertEqual(status, "Ordner lassen sich nicht bearbeiten.")
        argv, status = editor_command(
            r"D:\notes.txt",
            config={"editor": r"C:\kein\editor.exe"},
            environ={"EDITOR": "env-editor"},
            is_dir=False,
        )
        self.assertIsNone(argv)
        self.assertEqual(status, "Editor fehlt.")


if __name__ == "__main__":
    unittest.main()
