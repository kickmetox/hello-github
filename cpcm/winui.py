"""Windows-Fenster. Kein Browser."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from pathlib import Path

from cpcm.desktop import Session

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
comdlg32 = ctypes.WinDLL("comdlg32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, WPARAM, LPARAM)

WM_DESTROY = 0x0002
WM_SIZE = 0x0005
WM_SETFONT = 0x0030
WM_COMMAND = 0x0111
WM_CLOSE = 0x0010
WS_OVERLAPPEDWINDOW = 0x00CF0000
WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_BORDER = 0x00800000
WS_VSCROLL = 0x00200000
WS_TABSTOP = 0x00010000
WS_HSCROLL = 0x00100000
ES_MULTILINE = 0x0004
ES_AUTOVSCROLL = 0x0040
ES_AUTOHSCROLL = 0x0080
ES_READONLY = 0x0800
BS_AUTOCHECKBOX = 0x0003
LBS_NOTIFY = 0x0001
LBS_NOINTEGRALHEIGHT = 0x0100
LB_ADDSTRING = 0x0180
LB_RESETCONTENT = 0x0184
LB_GETCURSEL = 0x0188
CW_USEDEFAULT = 0x80000000
SW_SHOWNORMAL = 1
MF_STRING = 0
MF_POPUP = 0x0010
OFN_FILEMUSTEXIST = 0x00001000
OFN_PATHMUSTEXIST = 0x00000800
OFN_OVERWRITEPROMPT = 0x00000002
COLOR_WINDOW = 5
IDC_ARROW = 32512
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010
ID_EXIT = 1001
ID_HELP = 1100
ID_MANUAL = 1101
ID_FEATURES = 1102
ID_ABOUT = 1103
ID_RESTORE = 1200
ID_WORLDS = 1201
ID_APPS = 1202
ID_CONFIG = 1203
ID_DIAGNOSE = 1204
ID_HARDWARE = 1205

_STATES: dict[int, object] = {}
_CALLBACKS: list = []


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", WPARAM),
        ("lParam", LPARAM),
        ("time", wintypes.DWORD),
        ("pt_x", wintypes.LONG),
        ("pt_y", wintypes.LONG),
    ]


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]


class OPENFILENAMEW(ctypes.Structure):
    _fields_ = [
        ("lStructSize", wintypes.DWORD),
        ("hwndOwner", wintypes.HWND),
        ("hInstance", wintypes.HINSTANCE),
        ("lpstrFilter", wintypes.LPCWSTR),
        ("lpstrCustomFilter", wintypes.LPWSTR),
        ("nMaxCustFilter", wintypes.DWORD),
        ("nFilterIndex", wintypes.DWORD),
        ("lpstrFile", wintypes.LPWSTR),
        ("nMaxFile", wintypes.DWORD),
        ("lpstrFileTitle", wintypes.LPWSTR),
        ("nMaxFileTitle", wintypes.DWORD),
        ("lpstrInitialDir", wintypes.LPCWSTR),
        ("lpstrTitle", wintypes.LPCWSTR),
        ("Flags", wintypes.DWORD),
        ("nFileOffset", wintypes.WORD),
        ("nFileExtension", wintypes.WORD),
        ("lpstrDefExt", wintypes.LPCWSTR),
        ("lCustData", LPARAM),
        ("lpfnHook", ctypes.c_void_p),
        ("lpTemplateName", wintypes.LPCWSTR),
        ("pvReserved", ctypes.c_void_p),
        ("dwReserved", wintypes.DWORD),
        ("FlagsEx", wintypes.DWORD),
    ]


user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, ctypes.c_void_p]
user32.CreateWindowExW.restype = wintypes.HWND
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]
user32.SendMessageW.restype = LRESULT
user32.SetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.MessageBoxW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]
shell32.ShellExecuteW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_int]
shell32.ShellExecuteW.restype = wintypes.HINSTANCE


def _hwnd_key(hwnd) -> int:
    return int(ctypes.cast(hwnd, ctypes.c_void_p).value or 0)


def _text_of(hwnd) -> str:
    size = user32.GetWindowTextLengthW(hwnd) + 1
    buffer = ctypes.create_unicode_buffer(size)
    user32.GetWindowTextW(hwnd, buffer, size)
    return buffer.value


def _set_text(hwnd, text: str) -> None:
    user32.SetWindowTextW(hwnd, text)


def _checked(hwnd) -> bool:
    return user32.SendMessageW(hwnd, 0x00F0, 0, 0) == 1


def _font():
    return gdi32.CreateFontW(-16, 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 5, 0, "Segoe UI")


def _apply_font(hwnd, font) -> None:
    user32.SendMessageW(hwnd, WM_SETFONT, font, 1)


def _child(parent, klass, text, style, x, y, w, h, ident=0):
    return user32.CreateWindowExW(0, klass, text, WS_CHILD | WS_VISIBLE | style, x, y, w, h, parent, ident, None, None)


def _edit(parent, text, x, y, w, h, *, multi=False, readonly=False):
    style = WS_BORDER | WS_TABSTOP | ES_AUTOHSCROLL
    if multi:
        style |= ES_MULTILINE | ES_AUTOVSCROLL | WS_VSCROLL
    if readonly:
        style |= ES_READONLY
    return _child(parent, "EDIT", text, style, x, y, w, h)


def _button(parent, text, x, y, w, h, ident):
    return _child(parent, "BUTTON", text, WS_TABSTOP, x, y, w, h, ident)


def _listbox(parent, x, y, w, h, ident):
    return _child(parent, "LISTBOX", "", WS_BORDER | WS_VSCROLL | LBS_NOTIFY | LBS_NOINTEGRALHEIGHT | WS_TABSTOP, x, y, w, h, ident)


def _fill_list(hwnd, rows: list[str]) -> None:
    user32.SendMessageW(hwnd, LB_RESETCONTENT, 0, 0)
    for row in rows:
        user32.SendMessageW(hwnd, LB_ADDSTRING, 0, ctypes.cast(ctypes.create_unicode_buffer(row), ctypes.c_void_p).value)


def _selection(hwnd) -> int:
    return int(user32.SendMessageW(hwnd, LB_GETCURSEL, 0, 0))


def _report(log, text: str) -> None:
    _set_text(log, text)


def _guard(owner, log, action) -> None:
    try:
        _report(log, action())
    except Exception as exc:
        message = str(exc) or exc.__class__.__name__
        if log:
            _report(log, message)
        else:
            user32.MessageBoxW(owner, message, "CPCM", 0x10)


def _pick_file(owner, title: str, save: bool, filter_text: str) -> str:
    buffer = ctypes.create_unicode_buffer(32768)
    dialog = OPENFILENAMEW()
    dialog.lStructSize = ctypes.sizeof(OPENFILENAMEW)
    dialog.hwndOwner = owner
    dialog.lpstrFilter = filter_text
    dialog.lpstrFile = ctypes.cast(buffer, wintypes.LPWSTR)
    dialog.nMaxFile = 32768
    dialog.lpstrTitle = title
    dialog.Flags = OFN_PATHMUSTEXIST | (OFN_OVERWRITEPROMPT if save else OFN_FILEMUSTEXIST)
    function = comdlg32.GetSaveFileNameW if save else comdlg32.GetOpenFileNameW
    if not function(ctypes.byref(dialog)):
        return ""
    return buffer.value


def _open_document(hwnd, path: Path) -> None:
    if not path.is_file():
        user32.MessageBoxW(hwnd, f"Datei fehlt:\n{path}", "CPCM", 0x10)
        return
    shell32.ShellExecuteW(hwnd, "open", str(path), None, str(path.parent), SW_SHOWNORMAL)


class ToolWindow:
    def __init__(self, owner, session: Session, title: str, width: int, height: int) -> None:
        self.session = session
        self.owner = owner
        self.font = _font()
        self.hwnd = user32.CreateWindowExW(0, "CPCMTool", title, WS_OVERLAPPEDWINDOW, 80, 80, width, height, owner, None, None, None)
        _STATES[_hwnd_key(self.hwnd)] = self
        self.controls: dict[str, wintypes.HWND] = {}
        self.actions: dict[int, object] = {}
        self.next_id = 3000
        self.log = _edit(self.hwnd, "", 12, height - 220, width - 40, 160, multi=True, readonly=True)
        _apply_font(self.log, self.font)
        user32.ShowWindow(self.hwnd, SW_SHOWNORMAL)

    def label(self, text, x, y, w, h=20):
        hwnd = _child(self.hwnd, "STATIC", text, 0, x, y, w, h)
        _apply_font(hwnd, self.font)
        return hwnd

    def edit(self, key, text, x, y, w, h, *, multi=False):
        hwnd = _edit(self.hwnd, text, x, y, w, h, multi=multi)
        _apply_font(hwnd, self.font)
        self.controls[key] = hwnd
        return hwnd

    def check(self, key, text, x, y, w, checked=False):
        hwnd = _child(self.hwnd, "BUTTON", text, BS_AUTOCHECKBOX | WS_TABSTOP, x, y, w, 22)
        _apply_font(hwnd, self.font)
        if checked:
            user32.SendMessageW(hwnd, 0x00F1, 1, 0)
        self.controls[key] = hwnd
        return hwnd

    def button(self, text, x, y, w, action):
        ident = self.next_id
        self.next_id += 1
        hwnd = _button(self.hwnd, text, x, y, w, 28, ident)
        _apply_font(hwnd, self.font)
        self.actions[ident] = action
        return hwnd

    def listbox(self, key, x, y, w, h):
        ident = self.next_id
        self.next_id += 1
        hwnd = _listbox(self.hwnd, x, y, w, h, ident)
        _apply_font(hwnd, self.font)
        self.controls[key] = hwnd
        return hwnd

    def on_command(self, ident) -> None:
        action = self.actions.get(ident)
        if action:
            _guard(self.hwnd, self.log, action)


class MainWindow:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.font = _font()
        self.entries: list[dict] = []
        self.items: list[dict] = []
        self.hwnd = user32.CreateWindowExW(
            0, "CPCMMain", session.title(), WS_OVERLAPPEDWINDOW,
            CW_USEDEFAULT, CW_USEDEFAULT, 980, 680, None, self._menu(), None, None,
        )
        _STATES[_hwnd_key(self.hwnd)] = self
        self.path = _edit(self.hwnd, str(Path.home()), 12, 12, 620, 26)
        self.go = _button(self.hwnd, "Öffnen", 640, 12, 90, 26, 2002)
        self.up = _button(self.hwnd, "Nach oben", 736, 12, 100, 26, 2003)
        self.add_file = _button(self.hwnd, "Datei…", 842, 12, 110, 26, 2004)
        self.browser = _listbox(self.hwnd, 12, 48, 460, 430, 2006)
        self.selection = _listbox(self.hwnd, 484, 48, 468, 360, 2007)
        self.take = _button(self.hwnd, "Aufnehmen", 484, 416, 120, 28, 2011)
        self.remove = _button(self.hwnd, "Entfernen", 612, 416, 110, 28, 2008)
        self.backup = _button(self.hwnd, "Sicherung erstellen", 730, 416, 180, 28, 2009)
        self.log = _edit(self.hwnd, "", 12, 488, 940, 110, multi=True, readonly=True)
        self.status = _child(self.hwnd, "STATIC", session.status_line(), 0, 12, 608, 940, 22)
        for hwnd in (self.path, self.go, self.up, self.add_file, self.browser, self.selection, self.take, self.remove, self.backup, self.log, self.status):
            _apply_font(hwnd, self.font)
        icon_path = session.root / "cpcm.ico"
        if icon_path.is_file():
            icon = user32.LoadImageW(None, str(icon_path), IMAGE_ICON, 0, 0, LR_LOADFROMFILE)
            if icon:
                user32.SendMessageW(self.hwnd, 0x0080, 1, icon)
                user32.SendMessageW(self.hwnd, 0x0080, 0, icon)
        self.refresh_browser(_text_of(self.path))
        self.refresh_selection()
        user32.ShowWindow(self.hwnd, SW_SHOWNORMAL)

    def _menu(self):
        menu = user32.CreateMenu()
        file_menu = user32.CreatePopupMenu()
        user32.AppendMenuW(file_menu, MF_STRING, ID_EXIT, "Beenden")
        user32.AppendMenuW(menu, MF_POPUP, file_menu, "Datei")
        work = user32.CreatePopupMenu()
        user32.AppendMenuW(work, MF_STRING, ID_RESTORE, "Wiederherstellen…")
        user32.AppendMenuW(work, MF_STRING, ID_WORLDS, "Welten…")
        user32.AppendMenuW(work, MF_STRING, ID_APPS, "Programme…")
        user32.AppendMenuW(work, MF_STRING, ID_CONFIG, "Konfiguration…")
        user32.AppendMenuW(work, MF_STRING, ID_DIAGNOSE, "Diagnose…")
        user32.AppendMenuW(work, MF_STRING, ID_HARDWARE, "Hardware…")
        user32.AppendMenuW(menu, MF_POPUP, work, "Bearbeiten")
        help_menu = user32.CreatePopupMenu()
        user32.AppendMenuW(help_menu, MF_STRING, ID_HELP, "Inhalt")
        user32.AppendMenuW(help_menu, MF_STRING, ID_MANUAL, "Bedienungsanleitung")
        user32.AppendMenuW(help_menu, MF_STRING, ID_FEATURES, "Feature-Liste")
        user32.AppendMenuW(help_menu, MF_STRING, ID_ABOUT, "Über CPCM")
        user32.AppendMenuW(menu, MF_POPUP, help_menu, "Hilfe")
        return menu

    def refresh_browser(self, path_text: str) -> None:
        try:
            page = self.session.browse(path_text)
        except Exception as exc:
            _report(self.log, str(exc))
            return
        _set_text(self.path, page["path"])
        self.entries = page["entries"]
        _fill_list(self.browser, [f"{'[Ordner] ' if entry['kind'] == 'dir' else ''}{entry['name']}" for entry in self.entries])

    def refresh_selection(self) -> None:
        self.items = self.session.selection_rows()
        _fill_list(self.selection, [f"{item['label']}    {item['canonical']}" for item in self.items])
        _set_text(self.status, self.session.status_line())

    def current_entry(self) -> dict | None:
        index = _selection(self.browser)
        if index < 0 or index >= len(self.entries):
            return None
        return self.entries[index]

    def on_command(self, ident, notify) -> None:
        if ident == 2002:
            self.refresh_browser(_text_of(self.path))
        elif ident == 2003:
            parent = self.session.browse(_text_of(self.path)).get("parent")
            if parent:
                self.refresh_browser(parent)
        elif ident == 2004:
            chosen = _pick_file(self.hwnd, "Datei aufnehmen", False, "Alle Dateien\0*.*\0\0")
            if chosen:
                _guard(self.hwnd, self.log, lambda: self.session.add(chosen))
                self.refresh_selection()
        elif ident == 2006 and notify == 2:
            entry = self.current_entry()
            if entry and entry["kind"] == "dir":
                self.refresh_browser(entry["path"])
        elif ident == 2011:
            entry = self.current_entry()
            path = entry["path"] if entry else _text_of(self.path)
            _guard(self.hwnd, self.log, lambda: self.session.add(path))
            self.refresh_selection()
        elif ident == 2008:
            index = _selection(self.selection)
            if 0 <= index < len(self.items):
                item_id = self.items[index]["id"]
                _guard(self.hwnd, self.log, lambda: self.session.remove_selected(item_id))
                self.refresh_selection()
        elif ident == 2009:
            def act():
                if not self.session.selection_rows():
                    entry = self.current_entry()
                    self.session.add(entry["path"] if entry else _text_of(self.path))
                    self.refresh_selection()
                return self.session.backup()

            _guard(self.hwnd, self.log, act)
        elif ident == ID_EXIT:
            user32.DestroyWindow(self.hwnd)
        elif ident == ID_HELP:
            self._help()
        elif ident == ID_MANUAL:
            _open_document(self.hwnd, self.session.manual_path())
        elif ident == ID_FEATURES:
            _open_document(self.hwnd, self.session.features_path())
        elif ident == ID_ABOUT:
            user32.MessageBoxW(self.hwnd, f"{self.session.title()}\nAndreas Meyer\name@sellerbach.de\n\nFensterprogramm. Kein Browser.", "CPCM", 0x40)
        elif ident == ID_RESTORE:
            self._restore()
        elif ident == ID_WORLDS:
            self._worlds()
        elif ident == ID_APPS:
            self._apps()
        elif ident == ID_CONFIG:
            self._config()
        elif ident == ID_DIAGNOSE:
            self._diagnose()
        elif ident == ID_HARDWARE:
            self._hardware()

    def _help(self) -> None:
        tool = ToolWindow(self.hwnd, self.session, "Hilfe", 720, 560)
        _set_text(tool.log, self.session.help_text())
        user32.MoveWindow(tool.log, 12, 12, 680, 490, True)

    def _restore(self) -> None:
        tool = ToolWindow(self.hwnd, self.session, "Wiederherstellen", 760, 640)
        tool.rows = []
        tool.listbox("snaps", 12, 12, 720, 180)
        tool.check("overwrite", "Vorhandene Dateien ersetzen", 12, 200, 280, False)
        tool.check("translate", "Pfade in Textdateien umschreiben", 300, 200, 300, True)
        tool.label("Zielordner, leer lassen für die eigenen Ordner", 12, 230, 420)
        tool.edit("dest", "", 12, 252, 500, 24)
        tool.button("Liste", 12, 286, 100, lambda: self._load_snaps(tool))
        tool.button("Wiederherstellen", 120, 286, 150, lambda: self._do_restore(tool))
        tool.button("Export…", 278, 286, 100, lambda: self._do_export(tool))
        tool.button("Import…", 386, 286, 100, lambda: self._do_import(tool))
        tool.button("Löschen", 494, 286, 100, lambda: self._do_delete(tool))
        self._load_snaps(tool)

    def _selected_snapshot(self, tool: ToolWindow) -> str:
        index = _selection(tool.controls["snaps"])
        if index < 0 or index >= len(tool.rows):
            raise ValueError("Keine Sicherung gewählt.")
        return tool.rows[index]["id"]

    def _load_snaps(self, tool: ToolWindow) -> str:
        tool.rows = self.session.snapshots()
        _fill_list(tool.controls["snaps"], [f"{row['id']}    {row.get('created', '')}    {row.get('files', 0)} Dateien" for row in tool.rows])
        return f"{len(tool.rows)} Sicherungen."

    def _do_restore(self, tool: ToolWindow) -> str:
        return self.session.restore(
            self._selected_snapshot(tool),
            overwrite=_checked(tool.controls["overwrite"]),
            translate_paths=_checked(tool.controls["translate"]),
            destination=_text_of(tool.controls["dest"]),
        )

    def _do_export(self, tool: ToolWindow) -> str:
        dest = _pick_file(tool.hwnd, "Sicherung exportieren", True, "CPCM-Archiv\0*.cpcm\0\0")
        if not dest:
            return "Export abgebrochen."
        if not dest.lower().endswith(".cpcm"):
            dest += ".cpcm"
        return self.session.export(self._selected_snapshot(tool), dest)

    def _do_import(self, tool: ToolWindow) -> str:
        source = _pick_file(tool.hwnd, "Sicherung importieren", False, "CPCM-Archiv\0*.cpcm\0\0")
        if not source:
            return "Import abgebrochen."
        result = self.session.import_archive(source)
        self._load_snaps(tool)
        return result

    def _do_delete(self, tool: ToolWindow) -> str:
        result = self.session.delete(self._selected_snapshot(tool))
        self._load_snaps(tool)
        return result

    def _worlds(self) -> None:
        tool = ToolWindow(self.hwnd, self.session, "Welten", 760, 560)
        data = self.session.settings()
        tool.label("Linux-Home", 12, 12, 200)
        tool.edit("linux", data["homes"].get("linux", ""), 12, 34, 700, 24)
        tool.label("Windows-Home", 12, 66, 200)
        tool.edit("windows", data["homes"].get("windows", ""), 12, 88, 700, 24)
        tool.label("Vault", 12, 120, 200)
        tool.edit("vault", str(self.session.vault()), 12, 142, 700, 24)
        tool.button("Speichern", 12, 176, 140, lambda: self.session.save_worlds(_text_of(tool.controls["linux"]), _text_of(tool.controls["windows"]), _text_of(tool.controls["vault"])))
        _set_text(tool.log, self.session.world_lines())

    def _apps(self) -> None:
        tool = ToolWindow(self.hwnd, self.session, "Programme", 760, 620)
        tool.label("Ein Programmname pro Zeile. Befehle werden nur angezeigt.", 12, 12, 500)
        tool.edit("names", "git\nfirefox\nphotoshop", 12, 36, 500, 120, multi=True)
        managers = self.session.managers()
        tool.label("Paketverwaltung: " + ", ".join(managers), 12, 164, 500)
        tool.edit("manager", managers[0], 12, 186, 200, 24)
        tool.button("Dieses System lesen", 12, 220, 180, self.session.detect_apps)
        tool.button("Plan erstellen", 200, 220, 150, lambda: self.session.plan_apps(_text_of(tool.controls["names"]), _text_of(tool.controls["manager"])))

    def _config(self) -> None:
        tool = ToolWindow(self.hwnd, self.session, "Konfiguration", 760, 640)
        tool.edit("source", "linux", 12, 12, 120, 24)
        tool.edit("target", "windows", 140, 12, 120, 24)
        tool.edit("text", "", 12, 44, 720, 140, multi=True)
        tool.edit("shortcut", "Strg+Alt+Super+K", 12, 192, 240, 24)
        tool.button("Übersetzen", 12, 226, 130, lambda: self.session.translate(_text_of(tool.controls["text"]), _text_of(tool.controls["source"]), _text_of(tool.controls["target"])))
        tool.button("Kürzel", 150, 226, 100, lambda: self.session.shortcut(_text_of(tool.controls["shortcut"])))
        tool.button("Gesten", 258, 226, 100, self.session.gestures)
        tool.button("Erscheinungsbild", 366, 226, 160, self.session.theme)

    def _diagnose(self) -> None:
        tool = ToolWindow(self.hwnd, self.session, "Diagnose", 760, 640)
        tool.edit("log", "", 12, 12, 720, 140, multi=True)
        tool.edit("world", "linux", 12, 160, 120, 24)
        tool.edit("fs", "ext4", 140, 160, 120, 24)
        tool.edit("device", "/dev/nvme0n1p3", 268, 160, 220, 24)
        tool.button("Meldung übersetzen", 12, 194, 170, lambda: self.session.diagnose(_text_of(tool.controls["log"])))
        tool.button("Dateisystem-Plan", 190, 194, 160, lambda: self.session.filesystem(_text_of(tool.controls["world"]), _text_of(tool.controls["fs"]), _text_of(tool.controls["device"])))

    def _hardware(self) -> None:
        tool = ToolWindow(self.hwnd, self.session, "Hardware", 760, 560)
        tool.label("Profile bleiben im Vault. Spannung wird nicht geschrieben.", 12, 12, 520)
        tool.edit("profile", "Balanced", 12, 40, 200, 24)
        tool.button("Sonde und Profile", 12, 74, 170, self.session.hardware)
        tool.button("Profil aktivieren", 190, 74, 160, lambda: self.session.activate_profile(_text_of(tool.controls["profile"])))


def _wndproc(hwnd, message, wparam, lparam):
    state = _STATES.get(_hwnd_key(hwnd))
    if message == WM_COMMAND and state is not None:
        ident = int(wparam) & 0xFFFF
        notify = (int(wparam) >> 16) & 0xFFFF
        if isinstance(state, MainWindow):
            state.on_command(ident, notify)
        elif isinstance(state, ToolWindow):
            state.on_command(ident)
        return 0
    if message == WM_DESTROY:
        _STATES.pop(_hwnd_key(hwnd), None)
        if isinstance(state, MainWindow):
            user32.PostQuitMessage(0)
        return 0
    if message == WM_CLOSE:
        user32.DestroyWindow(hwnd)
        return 0
    return user32.DefWindowProcW(hwnd, message, wparam, lparam)


def run(root: Path | None = None) -> int:
    session = Session(root)
    instance = kernel32.GetModuleHandleW(None)
    cursor = user32.LoadCursorW(None, IDC_ARROW)
    callback = WNDPROC(_wndproc)
    _CALLBACKS.append(callback)
    for name in ("CPCMMain", "CPCMTool"):
        klass = WNDCLASSEXW()
        klass.cbSize = ctypes.sizeof(WNDCLASSEXW)
        klass.lpfnWndProc = callback
        klass.hInstance = instance
        klass.hCursor = cursor
        klass.hbrBackground = COLOR_WINDOW + 1
        klass.lpszClassName = name
        if not user32.RegisterClassExW(ctypes.byref(klass)):
            user32.MessageBoxW(None, "Das Fenster konnte nicht registriert werden.", "CPCM", 0x10)
            return 1
    MainWindow(session)
    message = MSG()
    while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
        user32.TranslateMessage(ctypes.byref(message))
        user32.DispatchMessageW(ctypes.byref(message))
    return 0
