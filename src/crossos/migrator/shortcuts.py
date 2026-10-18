"""Tastaturkürzel zwischen Windows und Linux, inklusive VS-Code-Grammatik.

Kanonische Modifier: ctrl, shift, alt, meta.
Deutsche Beschriftung: Strg, Umschalt, Alt, Win bzw. Super.
VS Code: ``win`` auf Windows, ``meta`` auf Linux. Akkorde mit Leerzeichen.
"""

from __future__ import annotations

import json
import re

from crossos.safety import SafetyError

_MODIFIERS = {
    "ctrl": "ctrl",
    "control": "ctrl",
    "strg": "ctrl",
    "steuerung": "ctrl",
    "shift": "shift",
    "umschalt": "shift",
    "alt": "alt",
    "altgr": "altgr",
    "super": "meta",
    "win": "meta",
    "windows": "meta",
    "meta": "meta",
    "cmd": "ctrl",
    "command": "ctrl",
}

_KEYS = {
    "entf": "delete",
    "delete": "delete",
    "del": "delete",
    "einf": "insert",
    "einfug": "insert",
    "einfg": "insert",
    "insert": "insert",
    "ins": "insert",
    "pos1": "home",
    "home": "home",
    "ende": "end",
    "end": "end",
    "bildauf": "pageup",
    "pageup": "pageup",
    "bildab": "pagedown",
    "pagedown": "pagedown",
    "drucken": "print",
    "print": "print",
    "printscreen": "print",
    "esc": "escape",
    "escape": "escape",
    "eingabe": "enter",
    "enter": "enter",
    "return": "enter",
    "leer": "space",
    "leerzeichen": "space",
    "space": "space",
    "tab": "tab",
    "left": "left",
    "right": "right",
    "up": "up",
    "down": "down",
    "links": "left",
    "rechts": "right",
    "hoch": "up",
    "runter": "down",
    "backspace": "backspace",
    "rueck": "backspace",
    "minus": "minus",
    "-": "minus",
    "plus": "plus",
    "+": "plus",
    ",": "comma",
    "comma": "comma",
    ".": "period",
    "period": "period",
}

_ORDER = ("ctrl", "shift", "alt", "altgr", "meta")
_KEY_RE = re.compile(r"^(?:[a-z0-9]|f(?:[1-9]|1[0-9]|2[0-4]))$")

_LABELS = {
    "windows": {"ctrl": "Strg", "shift": "Umschalt", "alt": "Alt", "altgr": "AltGr", "meta": "Win"},
    "linux": {"ctrl": "Strg", "shift": "Umschalt", "alt": "Alt", "altgr": "AltGr", "meta": "Super"},
}

_VSCODE = {
    "windows": {"ctrl": "ctrl", "shift": "shift", "alt": "alt", "altgr": "alt", "meta": "win"},
    "linux": {"ctrl": "ctrl", "shift": "shift", "alt": "alt", "altgr": "alt", "meta": "meta"},
}


def translate_shortcut(shortcut: str, *, source_os: str = "linux", target_os: str = "windows") -> dict:
    del source_os  # Die Grammatik ist absichtlich quellunabhängig; OS steckt in den Tokens.
    if target_os not in {"linux", "windows"}:
        raise SafetyError("Ziel für Kürzel muss linux oder windows sein.")
    chords = _parse(shortcut)
    return _pack(chords, target_os, source=shortcut)


def translate_vscode_keybindings(payload: object, *, target_os: str) -> dict:
    if target_os not in {"linux", "windows"}:
        raise SafetyError("Ziel für Kürzel muss linux oder windows sein.")
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise SafetyError(f"Keybindings-JSON ungültig: {exc.msg}") from exc
    if not isinstance(payload, list):
        raise SafetyError("VS-Code-Keybindings müssen eine Liste sein.")
    translated = []
    for item in payload:
        if not isinstance(item, dict) or "key" not in item:
            raise SafetyError("Jeder Eintrag braucht ein key-Feld.")
        chords = _parse(str(item["key"]))
        packed = _pack(chords, target_os, source=str(item["key"]))
        clone = dict(item)
        clone["key"] = packed["vscode_windows"] if target_os == "windows" else packed["vscode_linux"]
        clone["crossos"] = packed
        translated.append(clone)
    return {"target_os": target_os, "bindings": translated, "executed": False, "dry_run": True}


def _parse(shortcut: str) -> list[list[str]]:
    if not isinstance(shortcut, str) or not shortcut.strip():
        raise SafetyError("Kürzel fehlt.")
    text = re.sub(r"\s*\+\s*", "+", shortcut.strip().lower())
    text = text.replace("strg", "ctrl")
    chords = []
    for chord_src in text.split():
        parts = [part.strip() for part in chord_src.split("+") if part.strip()]
        if len(parts) < 2 and not (len(parts) == 1 and parts[0] in _KEYS or _KEY_RE.fullmatch(parts[0] if parts else "")):
            # Einzelne Funktionstaste oder Buchstabe ist erlaubt, leere Akkorde nicht.
            if len(parts) != 1:
                raise SafetyError("Kürzel ist unvollständig.")
        modifiers: list[str] = []
        key: str | None = None
        for part in parts:
            if part in _MODIFIERS and key is None:
                canonical = _MODIFIERS[part]
                if canonical not in modifiers:
                    modifiers.append(canonical)
                continue
            if key is not None:
                raise SafetyError("Pro Akkord ist nur eine Taste erlaubt.")
            key = _canonical_key(part)
        if key is None:
            raise SafetyError("Kürzel ohne Taste.")
        ordered = [name for name in _ORDER if name in modifiers]
        chords.append(ordered + [key])
    if not chords:
        raise SafetyError("Kürzel fehlt.")
    return chords


def _canonical_key(part: str) -> str:
    if part in _KEYS:
        return _KEYS[part]
    if _KEY_RE.fullmatch(part):
        return part
    raise SafetyError("Taste oder Modifier abgelehnt.")


def _pack(chords: list[list[str]], target_os: str, *, source: str = "") -> dict:
    notes = []
    flat = [token for chord in chords for token in chord]
    if "altgr" in flat:
        notes.append("AltGr wird in der VS-Code-Grammatik als alt ausgegeben. Auf einer deutschen Tastatur ist AltGr nicht dasselbe wie Alt.")
    if "meta" in flat:
        notes.append("Super, Win und Meta sind dieselbe Taste. VS Code schreibt auf Windows win und auf Linux meta.")
    if "cmd" in source.lower() or "command" in source.lower():
        notes.append("cmd/command wird auf Windows und Linux zu ctrl, analog zur VS-Code-Konvention. Super/Win bleibt meta.")

    def vscode(os_name: str) -> str:
        rendered = []
        for chord in chords:
            mods = [_VSCODE[os_name][token] for token in chord[:-1]]
            key = chord[-1]
            rendered.append("+".join([*mods, key]))
        return " ".join(rendered)

    def label(os_name: str) -> str:
        rendered = []
        for chord in chords:
            mods = [_LABELS[os_name][token] for token in chord[:-1]]
            key = _label_key(chord[-1])
            rendered.append("+".join([*mods, key]))
        return " ".join(rendered)

    canonical = " ".join("+".join(chord) for chord in chords)
    return {
        "canonical": canonical,
        "windows_label": label("windows"),
        "linux_label": label("linux"),
        "vscode_windows": vscode("windows"),
        "vscode_linux": vscode("linux"),
        "target_os": target_os,
        "target_vscode": vscode(target_os),
        "target_label": label(target_os),
        "notes": notes,
        "executed": False,
    }


def _label_key(key: str) -> str:
    special = {
        "delete": "Entf",
        "insert": "Einfg",
        "home": "Pos1",
        "end": "Ende",
        "pageup": "BildAuf",
        "pagedown": "BildAb",
        "print": "Druck",
        "escape": "Esc",
        "enter": "Eingabe",
        "space": "Leer",
        "minus": "-",
        "plus": "+",
        "comma": ",",
        "period": ".",
        "left": "Links",
        "right": "Rechts",
        "up": "Hoch",
        "down": "Runter",
        "backspace": "Rück",
    }
    if key in special:
        return special[key]
    if re.fullmatch(r"f\d{1,2}", key):
        return key.upper()
    return key.upper()
