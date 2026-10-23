"""Globales Kürzel. Greift, während ein anderes Programm den Fokus hat."""

from __future__ import annotations

import logging
import os
import select
import sys
import threading
from collections.abc import Callable

log = logging.getLogger("flare")

_MOD_NAMES = {
    "ctrl": "ctrl",
    "control": "ctrl",
    "strg": "ctrl",
    "alt": "alt",
    "shift": "shift",
    "umschalt": "shift",
    "super": "super",
    "win": "super",
    "meta": "super",
}
_KEY_NAMES = {
    "space": "space",
    "leertaste": "space",
}


def parse_hotkey(spec: str) -> tuple[set[str], str]:
    parts = [part.strip().casefold() for part in spec.replace(" ", "").split("+") if part.strip()]
    if not parts:
        raise ValueError("empty hotkey")
    key = _KEY_NAMES.get(parts[-1], parts[-1])
    mods = set()
    for part in parts[:-1]:
        name = _MOD_NAMES.get(part)
        if name is None:
            raise ValueError(f"unknown modifier {part}")
        mods.add(name)
    if key != "space":
        raise ValueError("only the space key is supported")
    if not mods:
        raise ValueError("hotkey needs a modifier")
    return mods, key


def hotkey_label(spec: str) -> str:
    mods, key = parse_hotkey(spec)
    names = []
    for mod in ("ctrl", "alt", "shift", "super"):
        if mod in mods:
            names.append({"ctrl": "Strg", "alt": "Alt", "shift": "Umschalt", "super": "Win"}[mod])
    names.append("Leertaste" if key == "space" else key)
    return "+".join(names)


class HotkeyThread:
    def __init__(self, spec: str, on_press: Callable[[], None], stop: threading.Event) -> None:
        self.spec = spec
        self.on_press = on_press
        self.stop = stop
        self.active = False
        self.error = ""
        self._thread = threading.Thread(target=self._run, name="flare-hotkey", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def close(self) -> None:
        if self._thread.is_alive():
            self._thread.join(timeout=1.5)

    def _run(self) -> None:
        try:
            mods, _key = parse_hotkey(self.spec)
            if sys.platform == "win32":
                self._win(mods)
            elif sys.platform.startswith("linux") and os.environ.get("DISPLAY"):
                self._x11(mods)
            else:
                self.error = "kein globales Kürzel auf dieser Sitzung"
        except Exception as exc:  # noqa: BLE001 - Hotkey darf den Dienst nicht beenden
            self.error = str(exc)
            log.warning("hotkey unavailable: %s", exc)

    def _win(self, mods: set[str]) -> None:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        modifiers = 0x4000  # MOD_NOREPEAT
        if "alt" in mods:
            modifiers |= 0x0001
        if "ctrl" in mods:
            modifiers |= 0x0002
        if "shift" in mods:
            modifiers |= 0x0004
        if "super" in mods:
            modifiers |= 0x0008
        hotkey_id = 1
        if not user32.RegisterHotKey(None, hotkey_id, modifiers, 0x20):
            self.error = "RegisterHotKey fehlgeschlagen"
            return
        self.active = True
        msg = wintypes.MSG()
        try:
            while not self.stop.is_set():
                rc = user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1)
                if rc and msg.message == 0x0312:  # WM_HOTKEY
                    self.on_press()
                self.stop.wait(0.05)
        finally:
            user32.UnregisterHotKey(None, hotkey_id)
            self.active = False

    def _x11(self, mods: set[str]) -> None:
        import ctypes

        lib = ctypes.CDLL("libX11.so.6")
        lib.XOpenDisplay.restype = ctypes.c_void_p
        lib.XOpenDisplay.argtypes = [ctypes.c_char_p]
        display = lib.XOpenDisplay(None)
        if not display:
            self.error = "XOpenDisplay fehlgeschlagen"
            return
        error_handler = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)(lambda *_a: 0)
        lib.XSetErrorHandler.argtypes = [ctypes.c_void_p]
        lib.XSetErrorHandler(error_handler)
        self._x11_error_handler = error_handler
        lib.XDefaultRootWindow.restype = ctypes.c_ulong
        lib.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        root = lib.XDefaultRootWindow(display)
        lib.XKeysymToKeycode.restype = ctypes.c_ubyte
        lib.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        keycode = lib.XKeysymToKeycode(display, 0x0020)
        base = 0
        if "shift" in mods:
            base |= 1
        if "ctrl" in mods:
            base |= 4
        if "alt" in mods:
            base |= 8
        if "super" in mods:
            base |= 64
        masks = [base, base | 2, base | 16, base | 2 | 16]  # Caps, Num
        lib.XGrabKey.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_uint, ctypes.c_ulong,
            ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ]
        for mask in masks:
            lib.XGrabKey(display, keycode, mask, root, False, 1, 1)
        lib.XSelectInput.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_long]
        lib.XFlush.argtypes = [ctypes.c_void_p]
        lib.XFlush(display)
        lib.XConnectionNumber.restype = ctypes.c_int
        lib.XConnectionNumber.argtypes = [ctypes.c_void_p]
        lib.XPending.restype = ctypes.c_int
        lib.XPending.argtypes = [ctypes.c_void_p]
        fd = lib.XConnectionNumber(display)
        self.active = True

        event = ctypes.create_string_buffer(256)
        lib.XNextEvent.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        try:
            while not self.stop.is_set():
                while lib.XPending(display):
                    lib.XNextEvent(display, event)
                    event_type = ctypes.cast(event, ctypes.POINTER(ctypes.c_int))[0]
                    if event_type == 2:  # KeyPress
                        self.on_press()
                try:
                    select.select([fd], [], [], 0.3)
                except OSError:
                    return
        finally:
            lib.XUngrabKey.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_uint, ctypes.c_ulong]
            for mask in masks:
                lib.XUngrabKey(display, keycode, mask, root)
            lib.XCloseDisplay.argtypes = [ctypes.c_void_p]
            lib.XCloseDisplay(display)
            self.active = False
