"""Pfadübersetzung zwischen Linux, Windows und WSL.

Konventionen (umkehrbar, längster Präfix gewinnt):

- ``~/.config`` ↔ ``AppData/Roaming``
- ``~/.local/share`` ↔ ``AppData/Local``
- ``~/.local/state`` ↔ ``AppData/Local/State``
- ``~/.local/bin`` ↔ ``AppData/Local/bin``
- ``~/.cache`` ↔ ``AppData/Local/Cache``

``AppData/Local/Temp`` bleibt darunter ``~/.local/share/Temp``, damit der
Cache-Pfad eindeutig zurückübersetzt werden kann. Systempfade außerhalb des
Benutzerprofils (``/etc``, ``C:\\Program Files``) werden nicht erfunden:
Richtung Windows/WSL bleiben nicht zuordenbare Linux-Pfade unverändert,
Windows-Systempfade werden für Linux als ``/mnt/<laufwerk>/...`` markiert.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from crossos.safety import SafetyError, validate_user

LINUX_PREFIXES: tuple[tuple[str, str], ...] = (
    (".local/share", "AppData/Local"),
    (".local/state", "AppData/Local/State"),
    (".local/bin", "AppData/Local/bin"),
    (".config", "AppData/Roaming"),
    (".cache", "AppData/Local/Cache"),
)

WINDOWS_PREFIXES: tuple[tuple[str, str], ...] = (
    ("AppData/Local/State", ".local/state"),
    ("AppData/Local/Cache", ".cache"),
    ("AppData/Local/bin", ".local/bin"),
    ("AppData/Roaming", ".config"),
    ("AppData/Local", ".local/share"),
)

_LINUX_HOME = re.compile(r"^/home/([^/]+)(?:/(.*))?$")
_WSL = re.compile(r"^/mnt/([a-z])(?:/(.*))?$")
_WIN = re.compile(r"^([A-Za-z]):[\\/](.*)$", re.DOTALL)
_WIN_USERS = re.compile(r"^Users/([^/]+)(?:/(.*))?$", re.IGNORECASE)

_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_./])("
    r"~(?:[\\/][^\s\"'<>|,;]*)?"
    r"|%(?:USERPROFILE|APPDATA|LOCALAPPDATA)%(?:[\\/][^\s\"'<>|,;]*)?"
    r"|\$\{HOME\}(?:/[^\s\"'<>|,;]*)?"
    r"|\$HOME(?:/[^\s\"'<>|,;]*)?"
    r"|/mnt/[a-z](?:/[^\s\"'<>|,;]*)?"
    r"|/home/[^\s\"'<>|,;]+"
    r"|[A-Za-z]:\\(?:[^:*?\"<>|\r\n\\]+\\)*[^:*?\"<>|\r\n\\]*"
    r")"
)


@dataclass(frozen=True)
class PathChange:
    before: str
    after: str
    unmapped: bool = False

    def as_dict(self) -> dict:
        return {"kind": "path", "before": self.before, "after": self.after, "unmapped": self.unmapped}


def _swap_prefix(rest: str, table: tuple[tuple[str, str], ...]) -> str:
    normalized = rest.replace("\\", "/").strip("/")
    for src, dst in table:
        if normalized == src:
            return dst
        prefix = src + "/"
        if normalized.startswith(prefix):
            tail = normalized[len(prefix) :]
            return f"{dst}/{tail}" if tail else dst
    return normalized


def _classify(path: str) -> str:
    if _WSL.match(path):
        return "wsl"
    if path.startswith("/"):
        return "linux"
    if _WIN.match(path):
        return "windows"
    return "unknown"


def _expand_user_tokens(path: str, user: str) -> str:
    expanded = path
    replacements = {
        "%USERPROFILE%": f"C:/Users/{user}",
        "%APPDATA%": f"C:/Users/{user}/AppData/Roaming",
        "%LOCALAPPDATA%": f"C:/Users/{user}/AppData/Local",
        "${HOME}": f"/home/{user}",
        "$HOME": f"/home/{user}",
    }
    for token, value in replacements.items():
        if expanded.startswith(token):
            expanded = value + expanded[len(token) :].replace("\\", "/")
            break
    if expanded == "~":
        return f"/home/{user}"
    if expanded.startswith("~/") or expanded.startswith("~\\"):
        return f"/home/{user}/" + expanded[2:].replace("\\", "/")
    return expanded


def _linux_home_to_windows(path: str) -> str | None:
    match = _LINUX_HOME.match(path)
    if not match:
        return None
    owner, rest = match.group(1), match.group(2) or ""
    try:
        owner = validate_user(owner)
    except SafetyError:
        return None
    mapped = _swap_prefix(rest, LINUX_PREFIXES) if rest else ""
    joined = f"C:/Users/{owner}/{mapped}" if mapped else f"C:/Users/{owner}"
    return joined.replace("/", "\\")


def _wsl_to_windows(path: str) -> str | None:
    match = _WSL.match(path)
    if not match:
        return None
    letter = match.group(1).upper()
    rest = match.group(2) or ""
    if not rest:
        return f"{letter}:\\"
    return letter + ":\\" + rest.replace("/", "\\")


def _windows_to_wsl(path: str) -> str:
    match = _WIN.match(path.replace("/", "\\"))
    if not match:
        return path
    letter = match.group(1).lower()
    rest = match.group(2).replace("\\", "/").strip("/")
    if not rest:
        return f"/mnt/{letter}"
    return f"/mnt/{letter}/{rest}"


def _windows_to_linux(path: str) -> tuple[str, bool]:
    match = _WIN.match(path.replace("/", "\\"))
    if not match:
        return path, True
    letter = match.group(1).lower()
    rest = match.group(2).replace("\\", "/").strip("/")
    user_match = _WIN_USERS.match(rest)
    if not user_match:
        mount = f"/mnt/{letter}" if not rest else f"/mnt/{letter}/{rest}"
        return mount, True
    owner = user_match.group(1)
    try:
        owner = validate_user(owner)
    except SafetyError:
        mount = f"/mnt/{letter}/{rest}"
        return mount, True
    tail = user_match.group(2) or ""
    mapped = _swap_prefix(tail, WINDOWS_PREFIXES) if tail else ""
    if mapped:
        return f"/home/{owner}/{mapped}", False
    return f"/home/{owner}", False


def _normalize_windows(path: str) -> str:
    match = _WIN.match(path.replace("/", "\\"))
    if not match:
        return path
    letter = match.group(1).upper()
    rest = match.group(2).replace("/", "\\").rstrip("\\")
    if rest == "":
        return f"{letter}:\\"
    return f"{letter}:\\{rest}"


def translate_path(raw: str, target: str, user: str | None = None) -> tuple[str, bool]:
    """Einen einzelnen Pfad übersetzen.

    Rückgabe: ``(pfad, unmapped)``. ``unmapped`` ist wahr, wenn kein
    semantisches Heimatverzeichnis zugeordnet werden konnte.
    """
    if target not in {"linux", "windows", "wsl"}:
        raise SafetyError("Ziel muss linux, windows oder wsl sein.")
    owner = validate_user(user) if user else validate_user(None)
    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        text = text[1:-1]
    trailing = text.endswith("/") or text.endswith("\\")
    expanded = _expand_user_tokens(text, owner)
    kind = _classify(expanded)

    if target == "linux" and kind == "linux":
        result = expanded
        return (result + "/" if trailing and not result.endswith("/") else result), False
    if target == "windows" and kind == "windows":
        result = _normalize_windows(expanded)
        return result, False
    if target == "wsl" and kind == "wsl":
        return expanded, False

    windows_form: str | None
    unmapped = False
    if kind == "wsl":
        windows_form = _wsl_to_windows(expanded)
    elif kind == "linux":
        windows_form = _linux_home_to_windows(expanded)
        if windows_form is None:
            return expanded, True
    elif kind == "windows":
        windows_form = expanded.replace("/", "\\")
    else:
        return raw, True

    if windows_form is None:
        return raw, True

    if target == "windows":
        result = _normalize_windows(windows_form)
    elif target == "wsl":
        result = _windows_to_wsl(windows_form)
    else:
        result, unmapped = _windows_to_linux(windows_form)
    if trailing and target != "windows" and not result.endswith("/"):
        result += "/"
    if trailing and target == "windows" and not result.endswith("\\"):
        result += "\\"
    return result, unmapped


def rewrite_text(text: str, target: str, user: str | None = None) -> tuple[str, list[PathChange]]:
    """Pfad-Tokens in einem Freitext ersetzen. URLs bleiben unverändert."""
    if not isinstance(text, str) or text == "":
        return text, []
    changes: list[PathChange] = []

    def replacer(match: re.Match[str]) -> str:
        token = match.group(1)
        translated, unmapped = translate_path(token, target, user)
        if translated != token:
            changes.append(PathChange(token, translated, unmapped))
        return translated

    rewritten = _TOKEN.sub(replacer, text)
    return rewritten, changes


def rewrite_obj(value, target: str, user: str | None = None):
    """Dict/List/str rekursiv. Gibt ``(wert, änderungen)`` zurück."""
    changes: list[PathChange] = []
    if isinstance(value, str):
        new, found = rewrite_text(value, target, user)
        return new, found
    if isinstance(value, list):
        out = []
        for item in value:
            new, found = rewrite_obj(item, target, user)
            changes.extend(found)
            out.append(new)
        return out, changes
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            new_key, key_changes = rewrite_text(key, target, user) if isinstance(key, str) else (key, [])
            new_val, val_changes = rewrite_obj(item, target, user)
            changes.extend(key_changes)
            changes.extend(val_changes)
            out[new_key] = new_val
        return out, changes
    return value, changes
