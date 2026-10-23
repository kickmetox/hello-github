"""Eigenes Windows-Fenster. Die Suche läuft im Prozess, ohne Browser."""

from __future__ import annotations

import ctypes
import sys
import threading
from ctypes import wintypes
from typing import Any, Callable

from flare.helptext import help_text

WM_DESTROY = 0x0002
WM_SIZE = 0x0005
WM_CLOSE = 0x0010
WM_QUIT = 0x0012
WM_KEYDOWN = 0x0100
WM_COMMAND = 0x0111
WM_TIMER = 0x0113
WM_CTLCOLOREDIT = 0x0133
WM_CTLCOLORLISTBOX = 0x0134
WM_CTLCOLORSTATIC = 0x0138
WM_SETFONT = 0x0030
WM_FLARE_SHOW = 0x8001

EN_CHANGE = 0x0300
BN_CLICKED = 0
LBN_DBLCLK = 2
LB_RESETCONTENT = 0x0184
LB_ADDSTRING = 0x0180
LB_SETCURSEL = 0x0186
LB_GETCURSEL = 0x0188
BM_GETCHECK = 0x00F0
BST_CHECKED = 1

WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_TABSTOP = 0x00010000
WS_VSCROLL = 0x00200000
WS_BORDER = 0x00800000
WS_CAPTION = 0x00C00000
WS_SYSMENU = 0x00080000
WS_THICKFRAME = 0x00040000
WS_CLIPCHILDREN = 0x02000000
ES_AUTOHSCROLL = 0x0080
ES_MULTILINE = 0x0004
ES_AUTOVSCROLL = 0x0040
ES_READONLY = 0x0800
EM_SETSEL = 0x00B1
BS_AUTOCHECKBOX = 0x0003
BS_PUSHBUTTON = 0x0000
LBS_NOTIFY = 0x0001
LBS_NOINTEGRALHEIGHT = 0x0100

SW_HIDE = 0
SW_SHOW = 5
PM_REMOVE = 1
VK_RETURN = 0x0D
VK_ESCAPE = 0x1B
VK_UP = 0x26
VK_DOWN = 0x28
VK_F1 = 0x70
IDC_HELP = 104
SM_CXSCREEN = 0
SM_CYSCREEN = 1

SearchFn = Callable[[str, bool], dict[str, Any]]
OpenFn = Callable[[dict[str, Any]], None]
StatusFn = Callable[[], str]

LRESULT = ctypes.c_ssize_t

_WINDOWS: dict[int, "NativeWindow"] = {}
_USER32_READY = False


def _prepare_user32():
    """DefWindowProcW muss LPARAM als Zeigerweite nehmen, sonst gehen Rahmennachrichten verloren."""
    global _USER32_READY
    user32 = ctypes.windll.user32
    if not _USER32_READY:
        user32.DefWindowProcW.argtypes = [
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        user32.DefWindowProcW.restype = LRESULT
        _USER32_READY = True
    return user32


def supported() -> bool:
    return sys.platform == "win32"


def shortcut_action(key: int, *, help_open: bool, help_target: bool) -> str | None:
    """Tasten im Suchfenster, ohne ein HWND zu erzeugen.

    „help“ öffnet die Hilfe. „close-help“ schließt sie und kehrt zur Suche
    zurück. None gibt die Taste an das Hilfe-Fenster weiter.
    """
    if key == VK_F1:
        return "help"
    if help_open and key == VK_ESCAPE:
        return "close-help"
    if help_target:
        return None
    if key == VK_RETURN:
        return "open"
    if key == VK_ESCAPE:
        return "hide"
    if key == VK_DOWN:
        return "down"
    if key == VK_UP:
        return "up"
    return None


class HelpWindow:
    """Zweites Win32-Fenster mit Kurzbeschreibung, Beschreibung und Feature-Liste."""

    def __init__(self, owner: "NativeWindow") -> None:
        self.owner = owner
        self.hwnd = 0
        self.body = 0
        self._proc: Any = None
        self._wndproc_type: Any = None
        self._brush = 0
        self._field_brush = 0
        self._return_focus = True
        self._class_ready = False

    def targets(self, hwnd: int) -> bool:
        if not hwnd or not self.hwnd:
            return False
        if hwnd == self.hwnd or hwnd == self.body:
            return True
        try:
            return bool(ctypes.windll.user32.IsChild(self.hwnd, hwnd))
        except (AttributeError, OSError):
            return False

    def open(self) -> None:
        user32 = ctypes.windll.user32
        if self.hwnd:
            user32.ShowWindow(self.hwnd, SW_SHOW)
            user32.SetForegroundWindow(self.hwnd)
            if self.body:
                user32.SetFocus(self.body)
                user32.SendMessageW(self.body, EM_SETSEL, 0, 0)
            return
        self._create()

    def close(self, focus: bool = True) -> None:
        self._return_focus = focus
        hwnd = self.hwnd
        if hwnd:
            ctypes.windll.user32.DestroyWindow(hwnd)
            return
        if focus:
            self._focus_search()

    def _focus_search(self) -> None:
        if not self._return_focus:
            return
        user32 = ctypes.windll.user32
        hwnd = self.owner.hwnd
        if not hwnd:
            return
        try:
            if not user32.IsWindow(hwnd) or not user32.IsWindowVisible(hwnd):
                return
        except (AttributeError, OSError):
            return
        user32.SetForegroundWindow(hwnd)
        if self.owner.edit:
            user32.SetFocus(self.owner.edit)

    def _create(self) -> bool:
        if not self._ensure_class():
            return False
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        user32.SetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
        user32.SetWindowTextW.restype = wintypes.BOOL
        if not self._field_brush:
            self._field_brush = gdi32.CreateSolidBrush(0x00222226)
        width, height = 640, 480
        x, y = self._origin(width, height)
        hwnd = user32.CreateWindowExW(
            0,
            "FlareHelp",
            "Hilfe",
            WS_CAPTION | WS_SYSMENU | WS_THICKFRAME | WS_CLIPCHILDREN,
            x,
            y,
            width,
            height,
            self.owner.hwnd or None,
            None,
            ctypes.windll.kernel32.GetModuleHandleW(None),
            None,
        )
        if not hwnd:
            return False
        self.hwnd = int(hwnd)
        style = (
            WS_CHILD
            | WS_VISIBLE
            | WS_VSCROLL
            | WS_BORDER
            | ES_MULTILINE
            | ES_AUTOVSCROLL
            | ES_READONLY
        )
        body = user32.CreateWindowExW(
            0,
            "EDIT",
            "",
            style,
            0,
            0,
            10,
            10,
            self.hwnd,
            wintypes.HMENU(200),
            ctypes.windll.kernel32.GetModuleHandleW(None),
            None,
        )
        self.body = int(body) if body else 0
        if self.owner._font and self.body:
            user32.SendMessageW(self.body, WM_SETFONT, self.owner._font, 1)
        if self.body:
            user32.SetWindowTextW(self.body, help_text())
        self._layout()
        user32.ShowWindow(self.hwnd, SW_SHOW)
        user32.SetForegroundWindow(self.hwnd)
        if self.body:
            user32.SetFocus(self.body)
            user32.SendMessageW(self.body, EM_SETSEL, 0, 0)
        return True

    def _origin(self, width: int, height: int) -> tuple[int, int]:
        user32 = ctypes.windll.user32
        rect = wintypes.RECT()
        if self.owner.hwnd and user32.GetWindowRect(self.owner.hwnd, ctypes.byref(rect)):
            owner_w = rect.right - rect.left
            owner_h = rect.bottom - rect.top
            return (
                max(0, rect.left + (owner_w - width) // 2),
                max(0, rect.top + (owner_h - height) // 2),
            )
        return (
            max(0, (user32.GetSystemMetrics(SM_CXSCREEN) - width) // 2),
            max(0, (user32.GetSystemMetrics(SM_CYSCREEN) - height) // 3),
        )

    def _ensure_class(self) -> bool:
        if self._class_ready:
            return True
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        wndproc_type = ctypes.WINFUNCTYPE(
            LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
        )
        self._wndproc_type = wndproc_type
        self._proc = wndproc_type(self._wndproc)
        if not self._brush:
            self._brush = gdi32.CreateSolidBrush(0x00121212)

        class WNDCLASSW(ctypes.Structure):
            _fields_ = [
                ("style", wintypes.UINT),
                ("lpfnWndProc", wndproc_type),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HANDLE),
                ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR),
            ]

        wc = WNDCLASSW()
        wc.lpfnWndProc = self._proc
        wc.hInstance = ctypes.windll.kernel32.GetModuleHandleW(None)
        wc.hCursor = user32.LoadCursorW(None, 32512)
        wc.hbrBackground = self._brush
        wc.lpszClassName = "FlareHelp"
        atom = user32.RegisterClassW(ctypes.byref(wc))
        if not atom and ctypes.windll.kernel32.GetLastError() not in (0, 1410):
            return False
        self._class_ready = True
        return True

    def _layout(self) -> None:
        if not self.hwnd or not self.body:
            return
        user32 = ctypes.windll.user32
        rect = wintypes.RECT()
        user32.GetClientRect(self.hwnd, ctypes.byref(rect))
        width = max(40, (rect.right - rect.left) - 24)
        height = max(40, (rect.bottom - rect.top) - 24)
        user32.MoveWindow(self.body, 12, 12, width, height, True)

    def _wndproc(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        user32 = _prepare_user32()
        if msg == WM_SIZE:
            self._layout()
            return 0
        if msg == WM_CLOSE or (msg == WM_KEYDOWN and int(wparam) == VK_ESCAPE):
            self.close(focus=True)
            return 0
        if msg == WM_DESTROY:
            self.hwnd = 0
            self.body = 0
            self._focus_search()
            return 0
        if msg in {WM_CTLCOLOREDIT, WM_CTLCOLORSTATIC}:
            gdi32 = ctypes.windll.gdi32
            gdi32.SetTextColor(wparam, 0x00F2F2F2)
            gdi32.SetBkColor(wparam, 0x00222226)
            return self._field_brush or self._brush
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


class NativeWindow:
    def __init__(self, search: SearchFn, open_hit: OpenFn, status: StatusFn) -> None:
        self._search = search
        self._open_hit = open_hit
        self._status = status
        self.hwnd = 0
        self.edit = 0
        self.check = 0
        self.list = 0
        self.label = 0
        self.similar = False
        self.results: list[dict[str, Any]] = []
        self.selected = 0
        self._pending_show = False
        self._proc: Any = None
        self._wndproc_type: Any = None
        self._brush = 0
        self._field_brush = 0
        self._font = 0
        self.help_btn = 0
        self._help = HelpWindow(self)

    def show(self) -> None:
        if not self.hwnd:
            self._pending_show = True
            return
        ctypes.windll.user32.PostMessageW(self.hwnd, WM_FLARE_SHOW, 0, 0)

    def run(self, stop: threading.Event, visible: bool) -> None:
        if not supported():
            while not stop.wait(3600):
                pass
            return
        if not self._create():
            while not stop.wait(3600):
                pass
            return
        if visible or self._pending_show:
            self._reveal()
        user32 = ctypes.windll.user32
        msg = wintypes.MSG()
        try:
            while not stop.is_set():
                while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
                    if msg.message == WM_QUIT:
                        stop.set()
                        return
                    if msg.message == WM_KEYDOWN and self._shortcut(int(msg.wParam), int(msg.hwnd or 0)):
                        continue
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                stop.wait(0.02)
        finally:
            self._help.close(focus=False)
            if self.hwnd:
                user32.DestroyWindow(self.hwnd)

    def _shortcut(self, key: int, hwnd: int = 0) -> bool:
        action = shortcut_action(
            key,
            help_open=bool(self._help.hwnd),
            help_target=self._help.targets(hwnd),
        )
        if action == "help":
            self._open_help()
            return True
        if action == "close-help":
            self._help.close(focus=True)
            return True
        if action == "open":
            self._open_selected()
            return True
        if action == "hide":
            self._hide()
            return True
        if action == "down":
            self._move(1)
            return True
        if action == "up":
            self._move(-1)
            return True
        return False

    def _open_help(self) -> None:
        if self.hwnd and not ctypes.windll.user32.IsWindowVisible(self.hwnd):
            self._reveal()
        self._help.open()

    def _create(self) -> bool:
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        user32.CreateWindowExW.argtypes = [
            ctypes.c_uint,
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            ctypes.c_uint,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.HWND,
            wintypes.HMENU,
            wintypes.HINSTANCE,
            ctypes.c_void_p,
        ]
        user32.CreateWindowExW.restype = wintypes.HWND
        user32.SetProcessDPIAware()
        wndproc_type = ctypes.WINFUNCTYPE(
            LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
        )
        self._wndproc_type = wndproc_type
        self._proc = wndproc_type(self._wndproc)
        class_name = "FlareWindow"

        class WNDCLASSW(ctypes.Structure):
            _fields_ = [
                ("style", wintypes.UINT),
                ("lpfnWndProc", wndproc_type),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HANDLE),
                ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR),
            ]

        instance = ctypes.windll.kernel32.GetModuleHandleW(None)
        self._brush = gdi32.CreateSolidBrush(0x00121212)
        self._field_brush = gdi32.CreateSolidBrush(0x00222226)
        wc = WNDCLASSW()
        wc.lpfnWndProc = self._proc
        wc.hInstance = instance
        wc.hCursor = user32.LoadCursorW(None, 32512)
        wc.hbrBackground = self._brush
        wc.lpszClassName = class_name
        user32.RegisterClassW(ctypes.byref(wc))
        width, height = 680, 520
        x = max(0, (user32.GetSystemMetrics(SM_CXSCREEN) - width) // 2)
        y = max(0, (user32.GetSystemMetrics(SM_CYSCREEN) - height) // 3)
        hwnd = user32.CreateWindowExW(
            0,
            class_name,
            "Flare",
            WS_CAPTION | WS_SYSMENU | WS_THICKFRAME | WS_CLIPCHILDREN,
            x,
            y,
            width,
            height,
            None,
            None,
            instance,
            None,
        )
        if not hwnd:
            return False
        self.hwnd = hwnd
        _WINDOWS[int(hwnd)] = self
        self._font = gdi32.CreateFontW(-18, 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 5, 0, "Segoe UI")
        self.edit = self._child("EDIT", "", 100, ES_AUTOHSCROLL | WS_BORDER)
        self.check = self._child("BUTTON", "Ähnliche Namen", 101, BS_AUTOCHECKBOX)
        self.list = self._child("LISTBOX", "", 102, LBS_NOTIFY | LBS_NOINTEGRALHEIGHT | WS_VSCROLL | WS_BORDER)
        self.label = self._child("STATIC", "Index wird aufgebaut", 103, 0)
        self.help_btn = self._child("BUTTON", "Hilfe", IDC_HELP, BS_PUSHBUTTON)
        self._layout()
        user32.SetTimer(hwnd, 2, 1000, None)
        return True

    def _child(self, klass: str, title: str, ident: int, style: int) -> int:
        user32 = ctypes.windll.user32
        hwnd = user32.CreateWindowExW(
            0,
            klass,
            title,
            WS_CHILD | WS_VISIBLE | WS_TABSTOP | style,
            0,
            0,
            10,
            10,
            self.hwnd,
            wintypes.HMENU(ident),
            ctypes.windll.kernel32.GetModuleHandleW(None),
            None,
        )
        if self._font:
            user32.SendMessageW(hwnd, WM_SETFONT, self._font, 1)
        return hwnd

    def _layout(self) -> None:
        if not self.hwnd:
            return
        user32 = ctypes.windll.user32
        rect = wintypes.RECT()
        user32.GetClientRect(self.hwnd, ctypes.byref(rect))
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        help_w = 96
        user32.MoveWindow(self.edit, 16, 16, max(40, width - 32), 36, True)
        user32.MoveWindow(self.check, 16, 60, max(40, width - 32 - help_w - 12), 24, True)
        if self.help_btn:
            user32.MoveWindow(self.help_btn, max(16, width - 16 - help_w), 56, help_w, 28, True)
        user32.MoveWindow(self.list, 16, 92, max(40, width - 32), max(40, height - 132), True)
        user32.MoveWindow(self.label, 16, height - 28, max(40, width - 32), 20, True)

    def _wndproc(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        user32 = _prepare_user32()
        if msg == WM_FLARE_SHOW:
            self._reveal()
            return 0
        if msg == WM_SIZE:
            self._layout()
            return 0
        if msg == WM_COMMAND:
            code = (wparam >> 16) & 0xFFFF
            ident = wparam & 0xFFFF
            if ident == 100 and code == EN_CHANGE:
                user32.SetTimer(hwnd, 1, 30, None)
            elif ident == 101 and code == BN_CLICKED:
                self.similar = user32.SendMessageW(self.check, BM_GETCHECK, 0, 0) == BST_CHECKED
                self._run_search()
            elif ident == 102 and code == LBN_DBLCLK:
                self._open_selected()
            elif ident == IDC_HELP and code == BN_CLICKED:
                self._open_help()
            return 0
        if msg == WM_TIMER:
            if wparam == 1:
                user32.KillTimer(hwnd, 1)
                self._run_search()
            elif wparam == 2:
                self._paint_status()
            return 0
        if msg in {WM_CTLCOLOREDIT, WM_CTLCOLORLISTBOX, WM_CTLCOLORSTATIC}:
            gdi32 = ctypes.windll.gdi32
            gdi32.SetTextColor(wparam, 0x00F2F2F2)
            gdi32.SetBkColor(wparam, 0x00222226 if msg != WM_CTLCOLORSTATIC else 0x00121212)
            return self._field_brush if msg != WM_CTLCOLORSTATIC else self._brush
        if msg == WM_CLOSE:
            self._hide()
            return 0
        if msg == WM_DESTROY:
            _WINDOWS.pop(int(hwnd), None)
            self.hwnd = 0
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _reveal(self) -> None:
        if not self.hwnd:
            self._pending_show = True
            return
        user32 = ctypes.windll.user32
        user32.ShowWindow(self.hwnd, SW_SHOW)
        user32.SetForegroundWindow(self.hwnd)
        user32.SetFocus(self.edit)
        self._pending_show = False
        self._run_search()

    def _hide(self) -> None:
        if self._help.hwnd:
            self._help.close(focus=False)
        if self.hwnd:
            ctypes.windll.user32.ShowWindow(self.hwnd, SW_HIDE)

    def _query(self) -> str:
        buf = ctypes.create_unicode_buffer(512)
        ctypes.windll.user32.GetWindowTextW(self.edit, buf, 512)
        return buf.value

    def _run_search(self) -> None:
        try:
            payload = self._search(self._query(), self.similar)
        except Exception:
            return
        self.results = list(payload.get("results") or [])
        self.selected = 0
        user32 = ctypes.windll.user32
        user32.SendMessageW(self.list, LB_RESETCONTENT, 0, 0)
        for hit in self.results:
            label = hit["name"]
            if hit.get("via") == "similar" and hit.get("similarity") is not None:
                label = f"{label}   ähnlich {int(round(float(hit['similarity']) * 100))} %"
            user32.SendMessageW(self.list, LB_ADDSTRING, 0, label)
        if self.results:
            user32.SendMessageW(self.list, LB_SETCURSEL, 0, 0)
        took = payload.get("took_ms")
        if took is not None:
            mode = "Ähnlichkeit" if self.similar else "Suche"
            ctypes.windll.user32.SetWindowTextW(self.label, f"{mode} · {took} ms · {len(self.results)} Treffer")

    def _paint_status(self) -> None:
        if self._query():
            return
        try:
            text = self._status()
        except Exception:
            return
        ctypes.windll.user32.SetWindowTextW(self.label, text)

    def _move(self, delta: int) -> None:
        if not self.results:
            return
        self.selected = max(0, min(len(self.results) - 1, self.selected + delta))
        ctypes.windll.user32.SendMessageW(self.list, LB_SETCURSEL, self.selected, 0)

    def _open_selected(self) -> None:
        choice = int(ctypes.windll.user32.SendMessageW(self.list, LB_GETCURSEL, 0, 0))
        if choice >= 0:
            self.selected = choice
        if not self.results:
            return
        hit = self.results[self.selected]
        self._open_hit(hit)
        if hit.get("kind") == "calc":
            ctypes.windll.user32.SetWindowTextW(self.label, "Ergebnis kopiert")
