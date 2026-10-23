"""Eigenes Windows-Fenster. Die Suche läuft im Prozess, ohne Browser."""

from __future__ import annotations

import ctypes
import sys
import threading
import time
from ctypes import wintypes
from pathlib import Path
from typing import Any, Callable

from flare.helptext import help_text
from flare.launch import (
    launch_sendto,
    list_sendto_entries,
    open_with_editor,
    quote_command_path,
    reveal_in_explorer,
    sendto_folder,
)
from flare.store import compare_indexes, copy_index, create_index, format_index_compare

WM_DESTROY = 0x0002
WM_SIZE = 0x0005
WM_CLOSE = 0x0010
WM_QUIT = 0x0012
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_CHAR = 0x0102
WM_COMMAND = 0x0111
WM_TIMER = 0x0113
WM_CTLCOLOREDIT = 0x0133
WM_CTLCOLORLISTBOX = 0x0134
WM_CTLCOLORSTATIC = 0x0138
WM_SETFONT = 0x0030
WM_CONTEXTMENU = 0x007B
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_GETDLGCODE = 0x0087
DLGC_WANTALLKEYS = 0x0004
WM_RBUTTONUP = 0x0205
WM_FLARE_SHOW = 0x8001

EN_CHANGE = 0x0300
BN_CLICKED = 0
LBN_DBLCLK = 2
LB_RESETCONTENT = 0x0184
LB_ADDSTRING = 0x0180
LB_SETCURSEL = 0x0186
LB_GETCURSEL = 0x0188
LB_GETCOUNT = 0x018B
LB_GETITEMRECT = 0x0198
LB_SETITEMHEIGHT = 0x01A0
LB_GETITEMHEIGHT = 0x01A1
LB_ITEMFROMPOINT = 0x01A9
LB_ERR = -1
WM_SETREDRAW = 0x000B
LBN_SELCHANGE = 1
RDW_INVALIDATE = 0x0001
RDW_ERASE = 0x0004
RDW_UPDATENOW = 0x0100
OPAQUE = 2
# CreateFontW(-18). Die Zeile muss diese Höhe plus Luft haben.
LIST_FONT_PX = 18
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
VK_SHIFT = 0x10
VK_UP = 0x26
VK_DOWN = 0x28
VK_APPS = 0x5D
VK_F1 = 0x70
VK_F10 = 0x79
IDC_HELP = 104
IDC_SAVE_INDEX = 201
IDC_COPY_INDEX = 203
IDC_COMPARE_INDEX = 204
IDC_CREATE_INDEX = 205
IDC_MENU_SAVE = 301
IDC_MENU_LOAD = 302
IDC_MENU_COMPARE = 303
IDC_MENU_COPY = 304
IDC_MENU_CREATE = 305
IDC_MENU_RESET = 306
IDC_CTX_OPEN = 311
IDC_CTX_REVEAL = 312
IDC_CTX_COPY = 313
IDC_CTX_EDIT = 314
IDC_CTX_COPY_QUOTED = 315
IDC_CTX_SEND_BASE = 400
IDC_CTX_SEND_LIMIT = 80
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
TPM_RETURNCMD = 0x0100
TPM_RIGHTBUTTON = 0x0002
TPM_NONOTIFY = 0x0080
GWLP_WNDPROC = -4
MB_YESNO = 0x0004
IDYES = 6
MF_STRING = 0x0000
MF_POPUP = 0x0010
MF_GRAYED = 0x0001
MF_DISABLED = 0x0002
WM_SETICON = 0x0080
ICON_SMALL = 0
ICON_BIG = 1
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010
GCLP_HICON = -14
GCLP_HICONSM = -34
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


def flare_icon_path() -> str:
    """flare.ico neben der eingefrorenen exe, im PyInstaller-Ordner oder im Quellbaum."""
    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "flare.ico")
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir / "flare.ico")
        candidates.append(exe_dir / "_internal" / "flare.ico")
    candidates.append(Path(__file__).resolve().parents[1] / "packaging" / "windows" / "flare.ico")
    for path in candidates:
        if path.is_file():
            return str(path)
    return ""


def load_flare_icons() -> tuple[int, int]:
    """Großes und kleines HICON. Unter Linux und ohne Datei (0, 0)."""
    if sys.platform != "win32":
        return 0, 0
    path = flare_icon_path()
    if not path:
        return 0, 0
    user32 = ctypes.windll.user32
    try:
        user32.LoadImageW.argtypes = [
            wintypes.HINSTANCE,
            wintypes.LPCWSTR,
            wintypes.UINT,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        ]
        user32.LoadImageW.restype = wintypes.HANDLE
        big = int(user32.LoadImageW(None, path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE) or 0)
        small = int(user32.LoadImageW(None, path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE) or 0)
    except (AttributeError, OSError):
        return 0, 0
    return big, small


def apply_flare_icons(hwnd: int, big: int, small: int) -> None:
    """Titelleiste, Taskleiste und Alt-Tab: WM_SETICON groß und klein, dazu das Klassenicon."""
    if sys.platform != "win32" or not hwnd or not (big or small):
        return
    user32 = ctypes.windll.user32
    try:
        if big:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, big)
        if small:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, small)
        set_class = getattr(user32, "SetClassLongPtrW", None)
        if set_class is None:
            return
        set_class.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
        set_class.restype = ctypes.c_size_t
        if big:
            set_class(hwnd, GCLP_HICON, big)
        if small:
            set_class(hwnd, GCLP_HICONSM, small)
    except (AttributeError, OSError):
        return


def choose_index_save_path(owner: int = 0, title: str = "Index speichern") -> str | None:
    """Speichern-Dialog. Nur unter Windows, und erst beim Klick, nicht beim Import."""
    return _index_file_dialog(owner, save=True, title=title, suggested="flare-index.db")


def choose_index_open_path(owner: int = 0, title: str = "Index öffnen") -> str | None:
    """Öffnen-Dialog. Nur unter Windows, und erst beim Klick, nicht beim Import."""
    return _index_file_dialog(owner, save=False, title=title, suggested="")


def confirm_index_replace(owner: int = 0) -> bool:
    """Ja/Nein, bevor der laufende Index ersetzt wird. Nur unter Windows."""
    if sys.platform != "win32":
        return False
    user32 = ctypes.windll.user32
    user32.MessageBoxW.argtypes = [
        wintypes.HWND,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.UINT,
    ]
    user32.MessageBoxW.restype = ctypes.c_int
    answer = user32.MessageBoxW(
        owner or None,
        "Der laufende Index wird durch diese Datei ersetzt. Fortfahren?",
        "Index laden",
        MB_YESNO,
    )
    return int(answer) == IDYES


def _save_index_as(
    owner: int,
    save: Callable[[str], str] | None,
    set_status: Callable[[str], None],
) -> None:
    path = choose_index_save_path(owner)
    if not path:
        return
    if save is None:
        set_status("Speichern fehlgeschlagen.")
        return
    try:
        save(path)
    except Exception:
        set_status("Speichern fehlgeschlagen.")
        return
    set_status("Index gespeichert.")


def _load_index_from(
    owner: int,
    load: Callable[[str], str] | None,
    set_status: Callable[[str], None],
    refreshed: Callable[[], None],
) -> None:
    path = choose_index_open_path(owner, "Index laden")
    if not path:
        return
    if not confirm_index_replace(owner):
        return
    if load is None:
        set_status("Laden fehlgeschlagen.")
        return
    try:
        load(path)
    except ValueError as exc:
        text = str(exc)
        if "ohne Tabelle" in text or "lässt sich nicht öffnen" in text or "Index fehlt" in text:
            set_status("Datei ist kein Flare-Index.")
        else:
            set_status("Laden fehlgeschlagen.")
        return
    except Exception:
        set_status("Laden fehlgeschlagen.")
        return
    refreshed()


def _create_index_as(owner: int, set_status: Callable[[str], None]) -> None:
    path = choose_index_save_path(owner, "Index anlegen")
    if not path:
        return
    try:
        create_index(path)
    except Exception:
        set_status("Anlegen fehlgeschlagen.")
        return
    set_status("Index angelegt.")


def _copy_index_as(owner: int, set_status: Callable[[str], None]) -> None:
    source = choose_index_open_path(owner, "Index kopieren")
    if not source:
        return
    dest = choose_index_save_path(owner, "Index kopieren")
    if not dest:
        return
    try:
        copy_index(source, dest)
    except Exception:
        set_status("Kopieren fehlgeschlagen.")
        return
    set_status("Index kopiert.")


def _compare_indexes_as(
    owner: int,
    set_status: Callable[[str], None],
    show_report: Callable[[str], None],
) -> None:
    left = choose_index_open_path(owner, "Erster Index")
    if not left:
        return
    right = choose_index_open_path(owner, "Zweiter Index")
    if not right:
        return
    try:
        report = format_index_compare(compare_indexes(left, right))
    except Exception:
        set_status("Vergleich fehlgeschlagen.")
        return
    set_status("Vergleich fertig.")
    show_report(report)


def _index_file_dialog(owner: int, *, save: bool, title: str, suggested: str) -> str | None:
    if sys.platform != "win32":
        return None
    comdlg32 = ctypes.WinDLL("comdlg32", use_last_error=True)

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
            ("lCustData", wintypes.LPARAM),
            ("lpfnHook", ctypes.c_void_p),
            ("lpTemplateName", wintypes.LPCWSTR),
            ("pvReserved", ctypes.c_void_p),
            ("dwReserved", wintypes.DWORD),
            ("FlagsEx", wintypes.DWORD),
        ]

    file_buf = ctypes.create_unicode_buffer(32768)
    file_buf.value = suggested
    filt = "SQLite-Datenbank\0*.db\0Alle Dateien\0*.*\0"
    ofn = OPENFILENAMEW()
    ofn.lStructSize = ctypes.sizeof(OPENFILENAMEW)
    ofn.hwndOwner = owner or None
    ofn.lpstrFilter = filt
    ofn.nFilterIndex = 1
    ofn.lpstrFile = ctypes.cast(file_buf, wintypes.LPWSTR)
    ofn.nMaxFile = len(file_buf)
    ofn.lpstrTitle = title
    ofn.lpstrDefExt = "db"
    if save:
        comdlg32.GetSaveFileNameW.argtypes = [ctypes.POINTER(OPENFILENAMEW)]
        comdlg32.GetSaveFileNameW.restype = wintypes.BOOL
        ofn.Flags = 0x00080000 | 0x00000800 | 0x00000002
        accepted = comdlg32.GetSaveFileNameW(ctypes.byref(ofn))
    else:
        comdlg32.GetOpenFileNameW.argtypes = [ctypes.POINTER(OPENFILENAMEW)]
        comdlg32.GetOpenFileNameW.restype = wintypes.BOOL
        ofn.Flags = 0x00080000 | 0x00000800 | 0x00001000
        accepted = comdlg32.GetOpenFileNameW(ctypes.byref(ofn))
    if not accepted:
        return None
    chosen = file_buf.value.strip()
    return chosen or None


def list_item_height(font_px: int, external_leading: int = 0) -> int:
    """Zeilenhöhe in Pixeln. Mindestens die Schrift, plus Luft gegen Überlappung."""
    cell = max(1, int(font_px)) + max(0, int(external_leading))
    return cell + 4


def item_height_covers_list(item_height: int, client_height: int, count: int) -> bool:
    """True, wenn die erste markierte Zeile so hoch ist, dass sie den Rest verdeckt."""
    return int(count) > 1 and int(client_height) > 0 and int(item_height) >= int(client_height)


def row_height_for_list(font_px: int, external_leading: int = 0, client_height: int = 0) -> int:
    """Eine Textzeile. Niemals die ganze Listenhöhe, sonst bleibt nur der erste Treffer sichtbar."""
    height = list_item_height(font_px, external_leading)
    if item_height_covers_list(height, client_height, 2):
        return max(8, int(client_height) // 8)
    return height


def rows_shown_for_count(stored: int, list_count: int) -> int:
    """LB_GETCOUNT muss die Trefferzahl sein. Jede dieser Zeilen wird gemalt."""
    if int(list_count) != int(stored):
        return 0
    return int(stored)


def result_labels(results: list[dict[str, Any]]) -> list[str]:
    """Sichtbarer Text einer Trefferliste. Nur der Name, nicht der Pfad."""
    labels: list[str] = []
    for hit in results:
        label = str(hit.get("name") or "")
        if hit.get("via") == "similar" and hit.get("similarity") is not None:
            label = f"{label}   ähnlich {int(round(float(hit['similarity']) * 100))} %"
        labels.append(label)
    return labels


def replace_list_rows(previous: list[str], labels: list[str]) -> list[str]:
    """Alte Zeilen verwerfen, dann nur die neuen Treffer. Nichts bleibt darunter."""
    return list(labels)


def search_status(mode: str, took_ms: float, count: int, path: str = "") -> str:
    """Statuszeile: Modus, Dauer, Trefferzahl und der Pfad der Auswahl."""
    text = f"{mode} · {took_ms} ms · {count} Treffer"
    cleaned = str(path or "").strip()
    if cleaned:
        return f"{text} · {cleaned}"
    return text


def selectable_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Jeder zurückgegebene Treffer ist eine Zeile. Gleicher Name, anderer Pfad bleibt."""
    return [dict(hit) for hit in results]


def path_for_selection(results: list[dict[str, Any]], index: int) -> str:
    """Pfad der Zeile `index`. Daneben oder außerhalb gibt es keinen Pfad."""
    if index < 0 or index >= len(results):
        return ""
    return row_path(results[index])


def rows_after_reset(labels: list[str]) -> list[str]:
    """Nach LB_RESETCONTENT genau diese Zeilen. Sichtbar ist die Trefferzahl."""
    return list(labels)


def enter_action(query: str, list_query: str | None, *, selected: int, count: int) -> str:
    """Enter öffnet nur einen Treffer der aktuellen Anfrage.

    Leere Liste oder eine Liste zu einem anderen Text: „search“. Nichts öffnen
    und das Fenster nicht abgeben. „open“ nur, wenn ein Treffer dieser Anfrage
    ausgewählt ist und gerade geöffnet wird.
    """
    if list_query != query or count <= 0:
        return "search"
    if selected < 0 or selected >= count:
        return "none"
    return "open"


def enter_activates_other_window(action: str) -> bool:
    """Nur das Öffnen eines echten Treffers darf den Vordergrund verlassen."""
    return action == "open"


def swallow_enter(message: int, wparam: int) -> bool:
    """Enter nicht an Windows durchreichen. Sonst aktiviert das System ein anderes Fenster."""
    if int(wparam) == VK_RETURN and message in (WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP):
        return True
    if message == WM_CHAR and int(wparam) in (10, 13):
        return True
    return False


def escape_action(query: str, hit_count: int) -> str:
    """Erstes Escape leert Anfrage oder Treffer. Das nächste blendet aus."""
    if str(query or "") or int(hit_count) > 0:
        return "reset"
    return "hide"


def split_lparam(value: int) -> tuple[int, int]:
    """X und Y aus einem Win32-LPARAM, jeweils vorzeichenbehaftet 16 Bit."""
    raw = int(value) & 0xFFFFFFFF
    x = raw & 0xFFFF
    y = (raw >> 16) & 0xFFFF
    if x >= 0x8000:
        x -= 0x10000
    if y >= 0x8000:
        y -= 0x10000
    return x, y


def make_lparam(x: int, y: int) -> int:
    return ((int(y) & 0xFFFF) << 16) | (int(x) & 0xFFFF)


_SEND_PTR: Any = None
_SEND_MSG: Any = None


def _send_msg(hwnd: int, message: int, wparam: int = 0, lparam: int = 0) -> int:
    """SendMessageW mit zeigerbreitem WPARAM. LB_SETCURSEL -1 löscht die Auswahl."""
    global _SEND_MSG
    if _SEND_MSG is None:
        kind = ctypes.WINFUNCTYPE(
            LRESULT,
            wintypes.HWND,
            wintypes.UINT,
            ctypes.c_size_t,
            ctypes.c_ssize_t,
        )
        _SEND_MSG = kind(("SendMessageW", ctypes.windll.user32))
    mask = (1 << (8 * ctypes.sizeof(ctypes.c_void_p))) - 1
    return int(_SEND_MSG(int(hwnd), int(message), int(wparam) & mask, int(lparam)))


def _send_ptr(hwnd: int, message: int, wparam: int, lparam: Any) -> int:
    """SendMessageW mit Zeigerbreite. Ein nacktes int würde auf 64 Bit abgeschnitten."""
    global _SEND_PTR
    if _SEND_PTR is None:
        kind = ctypes.WINFUNCTYPE(
            LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, ctypes.c_void_p
        )
        _SEND_PTR = kind(("SendMessageW", ctypes.windll.user32))
    if isinstance(lparam, int):
        return int(_SEND_PTR(hwnd, message, wparam, lparam))
    return int(_SEND_PTR(hwnd, message, wparam, ctypes.cast(lparam, ctypes.c_void_p)))


def hit_row(
    index: int,
    outside: int,
    count: int,
    left: int,
    top: int,
    right: int,
    bottom: int,
    x: int,
    y: int,
) -> int | None:
    """Zeile unter dem Zeiger. Leerfläche und außerhalb ergeben kein Menü."""
    if outside or count <= 0:
        return None
    if index < 0 or index >= count:
        return None
    if right <= left or bottom <= top:
        return None
    if x < left or x >= right or y < top or y >= bottom:
        return None
    return index


def row_path(item: dict[str, Any] | None) -> str:
    """Voller Pfad einer Zeile. Leer heißt: kein Kontextmenü."""
    if not item:
        return ""
    return str(item.get("path") or "").strip()


def copy_unicode_text(text: str, owner: int = 0) -> bool:
    """CF_UNICODETEXT in die Zwischenablage. Unter Linux immer False."""
    if sys.platform != "win32":
        return False
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    try:
        user32.OpenClipboard.argtypes = [wintypes.HWND]
        user32.OpenClipboard.restype = wintypes.BOOL
        user32.EmptyClipboard.restype = wintypes.BOOL
        user32.CloseClipboard.restype = wintypes.BOOL
        user32.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]
        user32.SetClipboardData.restype = ctypes.c_void_p
        kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        kernel32.GlobalAlloc.restype = ctypes.c_void_p
        kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalUnlock.restype = wintypes.BOOL
        kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
        kernel32.GlobalFree.restype = ctypes.c_void_p
    except (AttributeError, OSError):
        return False
    payload = str(text).encode("utf-16-le") + b"\x00\x00"
    if not user32.OpenClipboard(owner or None):
        return False
    handle = None
    locked = False
    try:
        if not user32.EmptyClipboard():
            return False
        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(payload))
        if not handle:
            return False
        dest = kernel32.GlobalLock(handle)
        if not dest:
            return False
        locked = True
        ctypes.memmove(dest, payload, len(payload))
        kernel32.GlobalUnlock(handle)
        locked = False
        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            return False
        handle = None
        return True
    except (AttributeError, OSError):
        return False
    finally:
        if locked and handle:
            kernel32.GlobalUnlock(handle)
        if handle:
            kernel32.GlobalFree(handle)
        user32.CloseClipboard()


def shortcut_action(key: int, *, help_open: bool, help_target: bool, shift: bool = False) -> str | None:
    """Tasten im Suchfenster, ohne ein HWND zu erzeugen.

    „help“ öffnet die Hilfe. „close-help“ schließt sie und kehrt zur Suche
    zurück. „context“ öffnet das Treffer-Menü. None gibt die Taste weiter.
    """
    if key == VK_F1:
        return "help"
    if help_open and key == VK_ESCAPE:
        return "close-help"
    if help_target:
        return None
    if key == VK_RETURN:
        return "open"
    if key == VK_APPS or (key == VK_F10 and shift):
        return "context"
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
        self.save_btn = 0
        self.copy_btn = 0
        self.compare_btn = 0
        self.create_btn = 0
        self.save_status = 0
        self._proc: Any = None
        self._wndproc_type: Any = None
        self._brush = 0
        self._field_brush = 0
        self._return_focus = True
        self._class_ready = False
        self._icon_big = 0
        self._icon_small = 0

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
        width, height = 860, 520
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
        apply_flare_icons(self.hwnd, self._icon_big, self._icon_small)
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
        self.create_btn = self._child("BUTTON", "Index anlegen", IDC_CREATE_INDEX, BS_PUSHBUTTON)
        self.save_btn = self._child("BUTTON", "Index speichern", IDC_SAVE_INDEX, BS_PUSHBUTTON)
        self.copy_btn = self._child("BUTTON", "Index kopieren", IDC_COPY_INDEX, BS_PUSHBUTTON)
        self.compare_btn = self._child("BUTTON", "Index vergleichen", IDC_COMPARE_INDEX, BS_PUSHBUTTON)
        self.save_status = self._child("STATIC", "", 202, 0)
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

        self._icon_big, self._icon_small = load_flare_icons()
        wc = WNDCLASSW()
        wc.lpfnWndProc = self._proc
        wc.hInstance = ctypes.windll.kernel32.GetModuleHandleW(None)
        wc.hIcon = self._icon_big
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
        buttons = [
            hwnd
            for hwnd in (self.create_btn, self.save_btn, self.copy_btn, self.compare_btn)
            if hwnd
        ]
        reserve = 76 if buttons else 0
        body_h = max(40, height - reserve)
        user32.MoveWindow(self.body, 12, 12, width, body_h, True)
        if buttons:
            gap = 8
            btn_w = max(80, (width - gap * (len(buttons) - 1)) // len(buttons))
            y = 16 + body_h
            for index, hwnd in enumerate(buttons):
                user32.MoveWindow(hwnd, 12 + index * (btn_w + gap), y, btn_w, 28, True)
        if self.save_status:
            user32.MoveWindow(self.save_status, 12, 48 + body_h, width, 22, True)

    def _wndproc(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        user32 = _prepare_user32()
        if msg == WM_SIZE:
            self._layout()
            return 0
        if msg == WM_COMMAND:
            ident = int(wparam) & 0xFFFF
            code = (int(wparam) >> 16) & 0xFFFF
            if code == BN_CLICKED:
                if ident == IDC_CREATE_INDEX:
                    self._create_index()
                elif ident == IDC_SAVE_INDEX:
                    self._save_index()
                elif ident == IDC_COPY_INDEX:
                    self._copy_index()
                elif ident == IDC_COMPARE_INDEX:
                    self._compare_indexes()
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
        font = self.owner._font
        if font and hwnd:
            user32.SendMessageW(hwnd, WM_SETFONT, font, 1)
        return int(hwnd) if hwnd else 0

    def _set_status(self, text: str) -> None:
        if self.save_status:
            ctypes.windll.user32.SetWindowTextW(self.save_status, text)

    def show_report(self, report: str) -> None:
        if not self.body:
            return
        user32 = ctypes.windll.user32
        user32.SetWindowTextW(self.body, report)
        user32.SetFocus(self.body)
        user32.SendMessageW(self.body, EM_SETSEL, 0, 0)

    def _save_index(self) -> None:
        _save_index_as(self.hwnd, getattr(self.owner, "save_index", None), self._set_status)

    def _create_index(self) -> None:
        _create_index_as(self.hwnd, self._set_status)

    def _copy_index(self) -> None:
        _copy_index_as(self.hwnd, self._set_status)

    def _compare_indexes(self) -> None:
        _compare_indexes_as(self.hwnd, self._set_status, self.show_report)


class NativeWindow:
    def __init__(
        self,
        search: SearchFn,
        open_hit: OpenFn,
        status: StatusFn,
        save_index: Callable[[str], str] | None = None,
        load_index: Callable[[str], str] | None = None,
        editor: str | None = None,
    ) -> None:
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
        self._rows: list[str] = []
        self._result_status: tuple[str, float, int] | None = None
        self.selected = -1
        # Anfrage, für die die Liste gefüllt wurde. None heißt: noch nicht, oder der Text hat sich geändert.
        self._list_query: str | None = None
        self._suspend_query = False
        self._pending_show = False
        self._proc: Any = None
        self._wndproc_type: Any = None
        self._brush = 0
        self._field_brush = 0
        self._font = 0
        self.help_btn = 0
        self._menu = 0
        self._icon_big = 0
        self._icon_small = 0
        self._list_proc_cb: Any = None
        self._old_list_proc: Any = None
        self._edit_proc_cb: Any = None
        self._old_edit_proc: Any = None
        self._enter_busy = False
        self._result_menu_open = False
        self._ignore_context_until = 0.0
        self._point_api = False
        self.save_index = save_index
        self.load_index = load_index
        self.editor = str(editor or "").strip()
        self._sendto_targets: list[dict[str, str]] = []
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
                    # wintypes.MSG heißt hWnd. hwnd gibt es nicht und wirft beim ersten Tastendruck.
                    hwnd = getattr(msg, "hWnd", None)
                    if hwnd is None:
                        hwnd = getattr(msg, "hwnd", 0)
                    if self._consume_key(int(msg.message), int(msg.wParam), int(hwnd or 0)):
                        continue
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                stop.wait(0.02)
        finally:
            self._help.close(focus=False)
            if self.hwnd:
                user32.DestroyWindow(self.hwnd)

    def _consume_key(self, message: int, wparam: int, hwnd: int) -> bool:
        """True: Taste verbraucht. Enter erreicht weder Translate noch Dispatch."""
        if swallow_enter(message, wparam) and message not in (WM_KEYDOWN, WM_SYSKEYDOWN):
            return True
        if message in (WM_KEYDOWN, WM_SYSKEYDOWN):
            handled = self._shortcut(int(wparam), hwnd)
            if swallow_enter(message, wparam):
                return True
            return handled
        return False

    def _shortcut(self, key: int, hwnd: int = 0) -> bool:
        shift = False
        if key in (VK_F10, VK_APPS) and sys.platform == "win32":
            try:
                user32 = ctypes.windll.user32
                user32.GetKeyState.argtypes = [ctypes.c_int]
                user32.GetKeyState.restype = ctypes.c_short
                shift = bool(int(user32.GetKeyState(VK_SHIFT)) & 0x8000)
            except (AttributeError, OSError):
                shift = False
        action = shortcut_action(
            key,
            help_open=bool(self._help.hwnd),
            help_target=self._help.targets(hwnd),
            shift=shift,
        )
        if action == "help":
            self._open_help()
            return True
        if action == "close-help":
            self._help.close(focus=True)
            return True
        if action == "open":
            self._on_enter()
            return True
        if action == "context":
            self._open_menu_for_current_selection(force=True)
            return True
        if action == "hide":
            query = self._query() if sys.platform == "win32" else ""
            if escape_action(query, len(self.results)) == "reset":
                self._reset_search()
            else:
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
        self._icon_big, self._icon_small = load_flare_icons()
        wc = WNDCLASSW()
        wc.lpfnWndProc = self._proc
        wc.hInstance = instance
        wc.hIcon = self._icon_big
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
        apply_flare_icons(int(hwnd), self._icon_big, self._icon_small)
        _WINDOWS[int(hwnd)] = self
        self._font = gdi32.CreateFontW(-LIST_FONT_PX, 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 5, 0, "Segoe UI")
        self.edit = self._child("EDIT", "", 100, ES_AUTOHSCROLL | WS_BORDER)
        self._subclass_search_edit()
        self.check = self._child("BUTTON", "Ähnliche Namen", 101, BS_AUTOCHECKBOX)
        self.list = self._child("LISTBOX", "", 102, LBS_NOTIFY | LBS_NOINTEGRALHEIGHT | WS_VSCROLL | WS_BORDER)
        self._apply_list_height()
        self.label = self._child("STATIC", "Index wird aufgebaut", 103, 0)
        self.help_btn = self._child("BUTTON", "Hilfe", IDC_HELP, BS_PUSHBUTTON)
        self._install_index_menu()
        self._subclass_result_list()
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

    def _apply_list_height(self) -> None:
        """Die Zeile muss die Schrift fassen, sonst malen sich die Treffer übereinander."""
        if not self.list:
            return
        client_h = self._list_client_height()
        height = row_height_for_list(LIST_FONT_PX, 0, client_h)
        measured = self._font_cell()
        if measured is not None:
            height = max(height, row_height_for_list(measured[0], measured[1], client_h))
        if item_height_covers_list(height, client_h, 2):
            height = row_height_for_list(LIST_FONT_PX, 0, client_h)
        _send_msg(self.list, LB_SETITEMHEIGHT, 0, height)

    def _list_client_height(self) -> int:
        if sys.platform != "win32" or not self.list:
            return 0
        rect = wintypes.RECT()
        try:
            if not ctypes.windll.user32.GetClientRect(self.list, ctypes.byref(rect)):
                return 0
        except (AttributeError, OSError):
            return 0
        return max(0, int(rect.bottom) - int(rect.top))

    def _font_cell(self) -> tuple[int, int] | None:
        if not self.list or not self._font or sys.platform != "win32":
            return None
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        class TEXTMETRICW(ctypes.Structure):
            _fields_ = [
                ("tmHeight", ctypes.c_long),
                ("tmAscent", ctypes.c_long),
                ("tmDescent", ctypes.c_long),
                ("tmInternalLeading", ctypes.c_long),
                ("tmExternalLeading", ctypes.c_long),
                ("tmAveCharWidth", ctypes.c_long),
                ("tmMaxCharWidth", ctypes.c_long),
                ("tmWeight", ctypes.c_long),
                ("tmOverhang", ctypes.c_long),
                ("tmDigitizedAspectX", ctypes.c_long),
                ("tmDigitizedAspectY", ctypes.c_long),
                ("tmFirstChar", ctypes.c_wchar),
                ("tmLastChar", ctypes.c_wchar),
                ("tmDefaultChar", ctypes.c_wchar),
                ("tmBreakChar", ctypes.c_wchar),
                ("tmItalic", ctypes.c_byte),
                ("tmUnderlined", ctypes.c_byte),
                ("tmStruckOut", ctypes.c_byte),
                ("tmPitchAndFamily", ctypes.c_byte),
                ("tmCharSet", ctypes.c_byte),
            ]

        hdc = user32.GetDC(self.list)
        if not hdc:
            return None
        try:
            old = gdi32.SelectObject(hdc, self._font)
            metrics = TEXTMETRICW()
            ok = gdi32.GetTextMetricsW(hdc, ctypes.byref(metrics))
            if old:
                gdi32.SelectObject(hdc, old)
            if not ok:
                return None
            text_h = int(metrics.tmHeight)
            try:
                class SIZE(ctypes.Structure):
                    _fields_ = [("cx", ctypes.c_long), ("cy", ctypes.c_long)]

                gdi32.GetTextExtentPoint32W.argtypes = [
                    wintypes.HDC,
                    wintypes.LPCWSTR,
                    ctypes.c_int,
                    ctypes.POINTER(SIZE),
                ]
                gdi32.GetTextExtentPoint32W.restype = wintypes.BOOL
                size = SIZE()
                if gdi32.GetTextExtentPoint32W(hdc, "AgÄyj", 5, ctypes.byref(size)):
                    text_h = max(text_h, int(size.cy))
            except (AttributeError, OSError):
                pass
            return text_h, int(metrics.tmExternalLeading)
        except (AttributeError, OSError):
            return None
        finally:
            user32.ReleaseDC(self.list, hdc)

    def _erase_list(self) -> None:
        """Redraw ist wieder an. Jede Zeile malen, ohne die Liste mit einem Vollflächen-Fill zu überdecken.

        InvalidateRect mit Löschen, dann UpdateWindow, damit die Zeilen ohne Klick erscheinen.
        """
        hwnd = self.list
        if not hwnd:
            return
        user32 = ctypes.windll.user32
        try:
            user32.InvalidateRect.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.BOOL]
            user32.InvalidateRect.restype = wintypes.BOOL
            user32.UpdateWindow.argtypes = [wintypes.HWND]
            user32.UpdateWindow.restype = wintypes.BOOL
            user32.InvalidateRect(hwnd, None, True)
            user32.UpdateWindow(hwnd)
        except (AttributeError, OSError):
            return

    def _install_index_menu(self) -> None:
        """Menüleiste nur unter Windows und erst beim Erzeugen des Fensters."""
        if sys.platform != "win32" or not self.hwnd:
            return
        user32 = ctypes.windll.user32
        user32.CreateMenu.argtypes = []
        user32.CreateMenu.restype = wintypes.HMENU
        user32.CreatePopupMenu.argtypes = []
        user32.CreatePopupMenu.restype = wintypes.HMENU
        user32.AppendMenuW.argtypes = [
            wintypes.HMENU,
            wintypes.UINT,
            ctypes.c_size_t,
            wintypes.LPCWSTR,
        ]
        user32.AppendMenuW.restype = wintypes.BOOL
        user32.SetMenu.argtypes = [wintypes.HWND, wintypes.HMENU]
        user32.SetMenu.restype = wintypes.BOOL
        user32.DrawMenuBar.argtypes = [wintypes.HWND]
        user32.DrawMenuBar.restype = wintypes.BOOL
        bar = user32.CreateMenu()
        popup = user32.CreatePopupMenu()
        if not bar or not popup:
            return
        user32.AppendMenuW(popup, MF_STRING, IDC_MENU_SAVE, "Sichern…")
        user32.AppendMenuW(popup, MF_STRING, IDC_MENU_LOAD, "Laden…")
        user32.AppendMenuW(popup, MF_STRING, IDC_MENU_COMPARE, "Vergleichen…")
        user32.AppendMenuW(popup, MF_STRING, IDC_MENU_COPY, "Kopieren…")
        user32.AppendMenuW(popup, MF_STRING, IDC_MENU_CREATE, "Anlegen…")
        user32.AppendMenuW(bar, MF_POPUP, int(popup), "Index")
        user32.AppendMenuW(bar, MF_STRING, IDC_MENU_RESET, "Suche zurücksetzen")
        info = user32.CreatePopupMenu()
        if info:
            user32.AppendMenuW(info, MF_STRING | MF_GRAYED | MF_DISABLED, 0, "Andreas Meyer")
            user32.AppendMenuW(info, MF_STRING | MF_GRAYED | MF_DISABLED, 0, "ame@sellerbach.de")
            user32.AppendMenuW(bar, MF_POPUP, int(info), "Info")
        if not user32.SetMenu(self.hwnd, bar):
            return
        self._menu = bar
        user32.DrawMenuBar(self.hwnd)

    def _subclass_search_edit(self) -> None:
        """Enter im Suchfeld schlucken. Das einzeilige Edit würde ihn sonst durchreichen."""
        if sys.platform != "win32" or not self.edit or self._wndproc_type is None:
            return
        user32 = ctypes.windll.user32
        setter = getattr(user32, "SetWindowLongPtrW", None)
        if setter is None:
            return
        try:
            setter.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
            setter.restype = ctypes.c_void_p
            user32.CallWindowProcW.argtypes = [
                ctypes.c_void_p,
                wintypes.HWND,
                wintypes.UINT,
                wintypes.WPARAM,
                wintypes.LPARAM,
            ]
            user32.CallWindowProcW.restype = LRESULT
            callback = self._wndproc_type(self._edit_wndproc)
            self._edit_proc_cb = callback
            previous = setter(self.edit, GWLP_WNDPROC, ctypes.cast(callback, ctypes.c_void_p))
        except (AttributeError, OSError):
            self._edit_proc_cb = None
            return
        if not previous:
            self._edit_proc_cb = None
            return
        self._old_edit_proc = previous

    def _call_old_proc(self, old: Any, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        if not old:
            return int(_prepare_user32().DefWindowProcW(hwnd, msg, wparam, lparam))
        return int(ctypes.windll.user32.CallWindowProcW(old, hwnd, msg, wparam, lparam))

    def _edit_wndproc(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        if msg == WM_GETDLGCODE:
            base = self._call_old_proc(self._old_edit_proc, hwnd, msg, wparam, lparam)
            return int(base) | DLGC_WANTALLKEYS
        if swallow_enter(msg, int(wparam)):
            if msg in (WM_KEYDOWN, WM_SYSKEYDOWN) and not self._enter_busy:
                self._on_enter()
            return 0
        return self._call_old_proc(self._old_edit_proc, hwnd, msg, wparam, lparam)

    def _subclass_result_list(self) -> None:
        """Rechtsklick erreicht die Liste, nicht das Hauptfenster. Nur unter Windows."""
        if sys.platform != "win32" or not self.list or self._wndproc_type is None:
            return
        user32 = ctypes.windll.user32
        setter = getattr(user32, "SetWindowLongPtrW", None)
        if setter is None:
            return
        try:
            setter.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
            setter.restype = ctypes.c_void_p
            user32.CallWindowProcW.argtypes = [
                ctypes.c_void_p,
                wintypes.HWND,
                wintypes.UINT,
                wintypes.WPARAM,
                wintypes.LPARAM,
            ]
            user32.CallWindowProcW.restype = LRESULT
            callback = self._wndproc_type(self._list_wndproc)
            self._list_proc_cb = callback
            previous = setter(self.list, GWLP_WNDPROC, ctypes.cast(callback, ctypes.c_void_p))
        except (AttributeError, OSError):
            self._list_proc_cb = None
            return
        if not previous:
            self._list_proc_cb = None
            return
        self._old_list_proc = previous

    def _list_wndproc(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        if msg in (WM_RBUTTONUP, WM_CONTEXTMENU):
            try:
                self._on_list_context(msg, int(lparam))
            except Exception:
                self._set_status("Aktion fehlgeschlagen.")
            return 0
        old = self._old_list_proc
        if not old:
            return int(_prepare_user32().DefWindowProcW(hwnd, msg, wparam, lparam))
        return int(ctypes.windll.user32.CallWindowProcW(old, hwnd, msg, wparam, lparam))

    def _bind_point_calls(self) -> None:
        if self._point_api or sys.platform != "win32":
            return
        user32 = ctypes.windll.user32
        user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
        user32.ClientToScreen.restype = wintypes.BOOL
        user32.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
        user32.ScreenToClient.restype = wintypes.BOOL
        self._point_api = True

    def _list_client_to_screen(self, x: int, y: int) -> tuple[int, int]:
        if sys.platform != "win32" or not self.list:
            return int(x), int(y)
        self._bind_point_calls()
        pt = wintypes.POINT(int(x), int(y))
        try:
            if ctypes.windll.user32.ClientToScreen(self.list, ctypes.byref(pt)):
                return int(pt.x), int(pt.y)
        except (AttributeError, OSError):
            return int(x), int(y)
        return int(x), int(y)

    def _screen_to_list(self, x: int, y: int) -> tuple[int, int] | None:
        if sys.platform != "win32" or not self.list:
            return None
        self._bind_point_calls()
        pt = wintypes.POINT(int(x), int(y))
        try:
            if not ctypes.windll.user32.ScreenToClient(self.list, ctypes.byref(pt)):
                return None
        except (AttributeError, OSError):
            return None
        return int(pt.x), int(pt.y)

    def _parent_client_to_list(self, x: int, y: int) -> tuple[int, int] | None:
        if sys.platform != "win32" or not self.hwnd or not self.list:
            return None
        self._bind_point_calls()
        pt = wintypes.POINT(int(x), int(y))
        user32 = ctypes.windll.user32
        try:
            if not user32.ClientToScreen(self.hwnd, ctypes.byref(pt)):
                return None
            if not user32.ScreenToClient(self.list, ctypes.byref(pt)):
                return None
        except (AttributeError, OSError):
            return None
        return int(pt.x), int(pt.y)

    def _list_client_contains(self, x: int, y: int) -> bool:
        if sys.platform != "win32" or not self.list:
            return False
        rect = wintypes.RECT()
        try:
            if not ctypes.windll.user32.GetClientRect(self.list, ctypes.byref(rect)):
                return False
        except (AttributeError, OSError):
            return False
        return rect.left <= x < rect.right and rect.top <= y < rect.bottom

    def _row_at_client(self, x: int, y: int) -> int | None:
        """Trefferzeile unter Listenkoordinaten. Leerfläche bleibt None."""
        if sys.platform != "win32" or not self.list or not self.results:
            return None
        user32 = ctypes.windll.user32
        try:
            raw = int(user32.SendMessageW(self.list, LB_ITEMFROMPOINT, 0, make_lparam(x, y)))
        except (AttributeError, OSError):
            return None
        raw &= 0xFFFFFFFF
        index = raw & 0xFFFF
        outside = (raw >> 16) & 0xFFFF
        rect = wintypes.RECT()
        try:
            got = _send_ptr(self.list, LB_GETITEMRECT, index, ctypes.byref(rect))
        except (AttributeError, OSError):
            return None
        if (got & 0xFFFFFFFF) == 0xFFFFFFFF:
            return None
        return hit_row(index, outside, len(self.results), rect.left, rect.top, rect.right, rect.bottom, x, y)

    def _select_result(self, index: int) -> bool:
        if index < 0 or index >= len(self.results):
            return False
        if not row_path(self.results[index]):
            return False
        self.selected = index
        if self.list and sys.platform == "win32":
            try:
                ctypes.windll.user32.SendMessageW(self.list, LB_SETCURSEL, index, 0)
            except (AttributeError, OSError):
                return False
        if self._query():
            self._apply_result_status()
        return True

    def _open_list_menu_at_client(self, x: int, y: int, screen: tuple[int, int], *, force: bool = False) -> bool:
        index = self._row_at_client(x, y)
        if index is None or not self._select_result(index):
            return False
        self._popup_result_menu(screen[0], screen[1], force=force)
        return True

    def _row_screen_point(self, index: int) -> tuple[int, int]:
        if sys.platform != "win32" or not self.list:
            return 0, 0
        rect = wintypes.RECT()
        user32 = ctypes.windll.user32
        try:
            got = _send_ptr(self.list, LB_GETITEMRECT, index, ctypes.byref(rect))
        except (AttributeError, OSError):
            got = LB_ERR
        if (got & 0xFFFFFFFF) != 0xFFFFFFFF and rect.bottom > rect.top:
            return self._list_client_to_screen(rect.left + 8, rect.bottom)
        return self._list_client_to_screen(8, 8)

    def _open_menu_for_current_selection(self, *, force: bool = False) -> None:
        if sys.platform != "win32" or not self.list:
            return
        index = self.selected
        try:
            choice = int(ctypes.windll.user32.SendMessageW(self.list, LB_GETCURSEL, 0, 0))
        except (AttributeError, OSError):
            choice = LB_ERR
        if choice >= 0:
            index = choice
        if not self._select_result(index):
            return
        x, y = self._row_screen_point(index)
        self._popup_result_menu(x, y, force=force)

    def _on_list_context(self, msg: int, lparam: int) -> None:
        if sys.platform != "win32":
            return
        if msg == WM_RBUTTONUP:
            x, y = split_lparam(lparam)
            self._open_list_menu_at_client(x, y, self._list_client_to_screen(x, y))
            return
        if msg == WM_CONTEXTMENU:
            x, y = split_lparam(lparam)
            if x == -1 and y == -1:
                self._open_menu_for_current_selection()
                return
            local = self._screen_to_list(x, y)
            if local is None:
                return
            self._open_list_menu_at_client(local[0], local[1], (x, y))

    def _on_parent_context(self, msg: int, wparam: int, lparam: int) -> bool:
        """True, wenn die Nachricht zur Trefferliste gehört und hier endet."""
        if sys.platform != "win32" or not self.list:
            return False
        if msg == WM_RBUTTONUP:
            local = self._parent_client_to_list(*split_lparam(lparam))
            if local is None or not self._list_client_contains(*local):
                return False
            self._open_list_menu_at_client(local[0], local[1], self._list_client_to_screen(*local))
            return True
        if msg != WM_CONTEXTMENU:
            return False
        x, y = split_lparam(lparam)
        if x == -1 and y == -1:
            self._open_menu_for_current_selection()
            return True
        target = int(wparam) if wparam else 0
        list_hwnd = int(self.list)
        if target not in (0, int(self.hwnd or 0), list_hwnd):
            return False
        local = self._screen_to_list(x, y)
        if local is None or not self._list_client_contains(*local):
            return target == list_hwnd
        self._open_list_menu_at_client(local[0], local[1], (x, y))
        return True

    def _popup_result_menu(self, x: int, y: int, *, force: bool = False) -> None:
        """Kontextmenü nur unter Windows und nur für eine Zeile mit Pfad."""
        if sys.platform != "win32" or not self.hwnd:
            return
        if self._result_menu_open:
            return
        now = time.monotonic()
        if not force and now < self._ignore_context_until:
            return
        user32 = ctypes.windll.user32
        try:
            user32.CreatePopupMenu.argtypes = []
            user32.CreatePopupMenu.restype = wintypes.HMENU
            user32.AppendMenuW.argtypes = [
                wintypes.HMENU,
                wintypes.UINT,
                ctypes.c_size_t,
                wintypes.LPCWSTR,
            ]
            user32.AppendMenuW.restype = wintypes.BOOL
            user32.TrackPopupMenu.argtypes = [
                wintypes.HMENU,
                wintypes.UINT,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                wintypes.HWND,
                ctypes.c_void_p,
            ]
            user32.TrackPopupMenu.restype = ctypes.c_int
            user32.DestroyMenu.argtypes = [wintypes.HMENU]
            user32.DestroyMenu.restype = wintypes.BOOL
        except (AttributeError, OSError):
            self._set_status("Aktion fehlgeschlagen.")
            return
        menu = user32.CreatePopupMenu()
        if not menu:
            return
        self._result_menu_open = True
        command = 0
        submenu = 0
        submenu_attached = False
        try:
            user32.AppendMenuW(menu, MF_STRING, IDC_CTX_OPEN, "Öffnen")
            user32.AppendMenuW(menu, MF_STRING, IDC_CTX_REVEAL, "Speicherort öffnen")
            user32.AppendMenuW(menu, MF_STRING, IDC_CTX_EDIT, "Im Editor bearbeiten")
            submenu = int(user32.CreatePopupMenu() or 0)
            self._sendto_targets = list_sendto_entries(sendto_folder())[:IDC_CTX_SEND_LIMIT]
            if submenu:
                if not self._sendto_targets:
                    user32.AppendMenuW(submenu, MF_STRING | MF_GRAYED | MF_DISABLED, 0, "Keine Ziele")
                else:
                    for offset, entry in enumerate(self._sendto_targets):
                        user32.AppendMenuW(
                            submenu,
                            MF_STRING,
                            IDC_CTX_SEND_BASE + offset,
                            entry["name"],
                        )
                submenu_attached = bool(user32.AppendMenuW(menu, MF_POPUP, submenu, "Senden an"))
            user32.AppendMenuW(menu, MF_STRING, IDC_CTX_COPY, "Pfad kopieren")
            user32.AppendMenuW(menu, MF_STRING, IDC_CTX_COPY_QUOTED, "Als Pfad kopieren")
            user32.SetForegroundWindow(self.hwnd)
            command = int(
                user32.TrackPopupMenu(
                    menu,
                    TPM_RETURNCMD | TPM_RIGHTBUTTON | TPM_NONOTIFY,
                    int(x),
                    int(y),
                    0,
                    self.hwnd,
                    None,
                )
            )
        except (AttributeError, OSError):
            self._set_status("Aktion fehlgeschlagen.")
            command = 0
        finally:
            try:
                if submenu and not submenu_attached:
                    user32.DestroyMenu(submenu)
                user32.DestroyMenu(menu)
            except (AttributeError, OSError):
                pass
            self._result_menu_open = False
            self._ignore_context_until = time.monotonic() + 0.3
            try:
                user32.PostMessageW(self.hwnd, 0, 0, 0)
            except (AttributeError, OSError):
                pass
        if command == IDC_CTX_OPEN:
            self._open_selected()
        elif command == IDC_CTX_REVEAL:
            self._reveal_selected()
        elif command == IDC_CTX_EDIT:
            self._edit_selected()
        elif command == IDC_CTX_COPY:
            self._copy_selected_path()
        elif command == IDC_CTX_COPY_QUOTED:
            self._copy_selected_path_quoted()
        elif IDC_CTX_SEND_BASE <= command < IDC_CTX_SEND_BASE + len(self._sendto_targets):
            self._send_selected(command - IDC_CTX_SEND_BASE)

    def _reveal_selected(self) -> None:
        path = self._selected_path()
        if not path:
            return
        try:
            status = reveal_in_explorer(path)
        except Exception:
            self._set_status("Explorer startet nicht.")
            return
        if status:
            self._set_status(status)

    def _copy_selected_path(self) -> None:
        self._copy_text(self._selected_path())

    def _copy_selected_path_quoted(self) -> None:
        path = self._selected_path()
        if not path:
            return
        self._copy_text(quote_command_path(path))

    def _copy_text(self, text: str) -> None:
        if not text:
            return
        try:
            copied = copy_unicode_text(text, int(self.hwnd or 0))
        except Exception:
            copied = False
        self._set_status("Pfad kopiert" if copied else "Pfad nicht kopiert.")

    def _edit_selected(self) -> None:
        path = self._selected_path()
        if not path:
            return
        hit = {}
        if 0 <= self.selected < len(self.results):
            hit = self.results[self.selected]
        try:
            status = open_with_editor(path, editor=self.editor, kind=str(hit.get("kind") or ""))
        except Exception:
            self._set_status("Editor fehlt.")
            return
        if status:
            self._set_status(status)

    def _send_selected(self, index: int) -> None:
        if index < 0 or index >= len(self._sendto_targets):
            return
        target = str(self._sendto_targets[index].get("path") or "")
        path = self._selected_path()
        if not target or not path:
            return
        try:
            status = launch_sendto(target, path)
        except Exception:
            self._set_status("Senden fehlgeschlagen.")
            return
        if status:
            self._set_status(status)

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
        if swallow_enter(msg, int(wparam)):
            if msg in (WM_KEYDOWN, WM_SYSKEYDOWN):
                self._on_enter()
            return 0
        if msg == WM_SIZE:
            self._layout()
            return 0
        if msg == WM_COMMAND:
            code = (int(wparam) >> 16) & 0xFFFF
            ident = int(wparam) & 0xFFFF
            if ident == IDC_MENU_SAVE:
                self._index_save()
            elif ident == IDC_MENU_LOAD:
                self._index_load()
            elif ident == IDC_MENU_COMPARE:
                self._index_compare()
            elif ident == IDC_MENU_COPY:
                self._index_copy()
            elif ident == IDC_MENU_CREATE:
                self._index_create()
            elif ident == IDC_MENU_RESET:
                self._reset_search()
            elif ident == 100 and code == EN_CHANGE:
                if not self._suspend_query:
                    self._on_query_edited()
                    user32.SetTimer(hwnd, 1, 30, None)
            elif ident == 101 and code == BN_CLICKED:
                self.similar = user32.SendMessageW(self.check, BM_GETCHECK, 0, 0) == BST_CHECKED
                self._run_search()
            elif ident == 102 and code == LBN_SELCHANGE:
                self._sync_selection()
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
        if msg in (WM_CONTEXTMENU, WM_RBUTTONUP):
            try:
                handled = self._on_parent_context(msg, int(wparam), int(lparam))
            except Exception:
                self._set_status("Aktion fehlgeschlagen.")
                return 0
            if handled:
                return 0
        if msg in {WM_CTLCOLOREDIT, WM_CTLCOLORLISTBOX, WM_CTLCOLORSTATIC}:
            gdi32 = ctypes.windll.gdi32
            gdi32.SetTextColor(wparam, 0x00F2F2F2)
            gdi32.SetBkColor(wparam, 0x00222226 if msg != WM_CTLCOLORSTATIC else 0x00121212)
            if msg == WM_CTLCOLORLISTBOX:
                gdi32.SetBkMode(wparam, OPAQUE)
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
        if not self.edit or sys.platform != "win32":
            return ""
        buf = ctypes.create_unicode_buffer(512)
        ctypes.windll.user32.GetWindowTextW(self.edit, buf, 512)
        return buf.value

    def _read_similar(self) -> None:
        if not self.check or sys.platform != "win32":
            return
        try:
            checked = _send_msg(self.check, BM_GETCHECK, 0, 0) == BST_CHECKED
        except (AttributeError, OSError):
            return
        self.similar = bool(checked)

    def _on_query_edited(self) -> None:
        """EN_CHANGE: Auswahl weg, bevor Öffnen den alten Index sehen kann."""
        self._clear_list_state(stamp=None)

    def _reset_search(self) -> None:
        """Anfrage, Liste und Auswahl leer. Das Fenster bleibt offen."""
        self._suspend_query = True
        try:
            if sys.platform == "win32" and self.hwnd:
                try:
                    ctypes.windll.user32.KillTimer(self.hwnd, 1)
                except (AttributeError, OSError):
                    pass
            if sys.platform == "win32" and self.edit:
                ctypes.windll.user32.SetWindowTextW(self.edit, "")
            self._clear_list_state(stamp="")
            if sys.platform == "win32" and self.edit:
                ctypes.windll.user32.SetFocus(self.edit)
            self._paint_status()
        finally:
            self._suspend_query = False
            if sys.platform == "win32" and self.hwnd:
                try:
                    ctypes.windll.user32.KillTimer(self.hwnd, 1)
                except (AttributeError, OSError):
                    pass

    def _clear_list_state(self, stamp: str | None) -> None:
        self.results = []
        self._rows = []
        self.selected = -1
        self._list_query = stamp
        self._result_status = None
        if sys.platform == "win32" and self.list:
            _send_msg(self.list, LB_SETCURSEL, -1, 0)
            _send_msg(self.list, WM_SETREDRAW, 0, 0)
            try:
                _send_msg(self.list, LB_RESETCONTENT, 0, 0)
            finally:
                _send_msg(self.list, WM_SETREDRAW, 1, 0)
                self._erase_list()
        if stamp is None:
            self._set_status("")

    def _run_search(self) -> None:
        if sys.platform == "win32" and self.hwnd:
            try:
                ctypes.windll.user32.KillTimer(self.hwnd, 1)
            except (AttributeError, OSError):
                pass
        self._read_similar()
        query = self._query() if sys.platform == "win32" else ""
        try:
            payload = self._search(query, self.similar)
        except Exception:
            return
        if sys.platform == "win32" and self._query() != query:
            return
        self.results = selectable_rows(list(payload.get("results") or []))
        labels = result_labels(self.results)
        self._rows = rows_after_reset(replace_list_rows(self._rows, labels))
        took = payload.get("took_ms")
        if took is not None:
            mode = "Ähnlichkeit" if self.similar else "Suche"
            self._result_status = (mode, float(took), len(self.results))
        select = 0 if self.results else -1
        self._list_query = query
        self.selected = select
        suspended = self._suspend_query
        self._suspend_query = True
        try:
            self._fill_listbox(select)
        finally:
            self._suspend_query = suspended
        if took is not None:
            self._apply_result_status()

    def _fill_listbox(self, select: int) -> None:
        """LB_RESETCONTENT, dann genau eine Zeile pro Treffer. Nichts daneben."""
        if sys.platform != "win32" or not self.list:
            return
        self._apply_list_height()
        _send_msg(self.list, LB_SETCURSEL, -1, 0)
        _send_msg(self.list, WM_SETREDRAW, 0, 0)
        count = 0
        try:
            _send_msg(self.list, LB_RESETCONTENT, 0, 0)
            held = [ctypes.create_unicode_buffer(label) for label in self._rows]
            for buf in held:
                _send_ptr(self.list, LB_ADDSTRING, 0, buf)
            count = _send_msg(self.list, LB_GETCOUNT, 0, 0)
            if count != len(self._rows):
                _send_msg(self.list, LB_RESETCONTENT, 0, 0)
                for buf in held:
                    _send_ptr(self.list, LB_ADDSTRING, 0, buf)
                count = _send_msg(self.list, LB_GETCOUNT, 0, 0)
        finally:
            # War das Zeichnen aus, wieder an. Sonst bleibt nur die Auswahl sichtbar.
            _send_msg(self.list, WM_SETREDRAW, 1, 0)
        self._keep_rows_uncovered(count)
        if 0 <= select < len(self._rows):
            _send_msg(self.list, LB_SETCURSEL, select, 0)
        else:
            _send_msg(self.list, LB_SETCURSEL, -1, 0)
        self._erase_list()

    def _keep_rows_uncovered(self, count: int) -> None:
        """Die erste Zeile bleibt eine Textzeile. Sie darf die übrigen nicht übermalen."""
        if not self.list or count <= 1:
            return
        client_h = self._list_client_height()
        current = _send_msg(self.list, LB_GETITEMHEIGHT, 0, 0)
        if current < 0 or not item_height_covers_list(current, client_h, count):
            return
        _send_msg(
            self.list,
            LB_SETITEMHEIGHT,
            0,
            row_height_for_list(LIST_FONT_PX, 0, client_h),
        )

    def _paint_status(self) -> None:
        if self._query():
            return
        try:
            text = self._status()
        except Exception:
            return
        ctypes.windll.user32.SetWindowTextW(self.label, text)

    def _set_status(self, text: str) -> None:
        if self.label:
            ctypes.windll.user32.SetWindowTextW(self.label, text)

    def _index_save(self) -> None:
        _save_index_as(self.hwnd, self.save_index, self._set_status)

    def _index_load(self) -> None:
        _load_index_from(self.hwnd, self.load_index, self._set_status, self._refresh_after_load)

    def _index_compare(self) -> None:
        _compare_indexes_as(self.hwnd, self._set_status, self._show_report)

    def _index_copy(self) -> None:
        _copy_index_as(self.hwnd, self._set_status)

    def _index_create(self) -> None:
        _create_index_as(self.hwnd, self._set_status)

    def _show_report(self, report: str) -> None:
        self._help.open()
        self._help.show_report(report)

    def _refresh_after_load(self) -> None:
        self._run_search()
        if not self._query():
            self._paint_status()

    def _selected_path(self) -> str:
        return path_for_selection(self.results, self.selected)

    def _apply_result_status(self) -> None:
        if self._result_status is None:
            return
        mode, took, count = self._result_status
        self._set_status(search_status(mode, took, count, self._selected_path()))

    def _live_selection(self) -> int:
        """Auswahl nur, wenn die Liste zur Anfrage im Suchfeld gehört."""
        query = self._query() if sys.platform == "win32" else ""
        if self._list_query != query:
            return -1
        choice = self.selected
        if sys.platform == "win32" and self.list:
            try:
                current = _send_msg(self.list, LB_GETCURSEL, 0, 0)
            except (AttributeError, OSError):
                current = -1
            if current >= 0:
                choice = current
        if choice < 0 or choice >= len(self.results):
            return -1
        return choice

    def _sync_selection(self) -> None:
        if not self.list or self._suspend_query:
            return
        choice = self._live_selection()
        self.selected = choice
        if self._list_query == self._query():
            self._apply_result_status()

    def _move(self, delta: int) -> None:
        if not self.results or self._list_query != self._query():
            return
        self.selected = max(0, min(len(self.results) - 1, self.selected + delta))
        _send_msg(self.list, LB_SETCURSEL, self.selected, 0)
        if self._query():
            self._apply_result_status()

    def _on_enter(self) -> None:
        """Ein Enter. Die Schleife und das Suchfeld dürfen ihn nicht doppelt ausführen."""
        if self._enter_busy:
            return
        self._enter_busy = True
        try:
            self._open_selected()
        finally:
            self._enter_busy = False

    def _hold_flare_focus(self) -> None:
        """Tastatur und Vordergrund bleiben in Flare. Kein anderes Fenster aktivieren."""
        if sys.platform != "win32" or not self.hwnd:
            return
        user32 = ctypes.windll.user32
        try:
            user32.SetForegroundWindow(self.hwnd)
            if self.edit:
                user32.SetFocus(self.edit)
        except (AttributeError, OSError):
            return

    def _open_selected(self) -> None:
        if sys.platform == "win32" and not self.list:
            self._hold_flare_focus()
            return
        query = self._query() if sys.platform == "win32" else ""
        selected = self.selected
        if self._list_query == query:
            selected = self._live_selection()
        action = enter_action(query, self._list_query, selected=selected, count=len(self.results))
        if enter_activates_other_window(action):
            if self._query() != query or self._list_query != query:
                self._hold_flare_focus()
                return
            if selected < 0 or selected >= len(self.results):
                self._hold_flare_focus()
                return
            self.selected = selected
            hit = self.results[self.selected]
            try:
                self._open_hit(hit)
            except OSError as exc:
                missing = isinstance(exc, FileNotFoundError)
                missing = missing or getattr(exc, "errno", None) in (2, 3)
                missing = missing or getattr(exc, "winerror", None) in (2, 3)
                self._set_status("Datei fehlt." if missing else "Öffnen fehlgeschlagen.")
                self._hold_flare_focus()
                return
            except Exception:
                self._set_status("Öffnen fehlgeschlagen.")
                self._hold_flare_focus()
                return
        else:
            if action == "search":
                self._run_search()
            self._hold_flare_focus()
            return
        if hit.get("kind") == "calc":
            try:
                ctypes.windll.user32.SetWindowTextW(self.label, "Ergebnis kopiert")
            except (AttributeError, OSError):
                return
