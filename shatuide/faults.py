"""Fehlerstellen aus Tracebacks und Shell-Meldungen."""

from __future__ import annotations

import re
from pathlib import Path

_PY_FRAME = re.compile(r'^\s*File "([^"]+)", line (\d+)', re.MULTILINE)
_PS_PATH = re.compile(r"(?im)^(?:At|In)\s+(.+?):(\d+)\s+char:")
_PS_LINE = re.compile(r"(?im)^(?:At|In)\s+line:(\d+)\s+char:")
_PS_MODERN = re.compile(r"(?m)^[A-Za-z_][\w.]*:\s+(.+?):(\d+)\s*$")
_SH_LINE = re.compile(r"(?m)^(.*?): (?:line|Zeile) (\d+):")
_ZEILE = re.compile(r"(?i)\bZeile\s+(\d+)")
_EXC = re.compile(r"^[A-Za-z_][\w.]*(?:Error|Exception|Interrupt)\b.*|^SyntaxError:.*", re.MULTILINE)
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def same_file(left: str, right: str) -> bool:
    if not left or not right:
        return False
    a = Path(left)
    b = Path(right)
    if a.name != b.name:
        return False
    try:
        return a.resolve() == b.resolve() or not a.is_absolute() or not b.is_absolute()
    except OSError:
        return True


def locate_fault(text: str, preferred: str = "") -> dict | None:
    """Letzte Fehlerstelle. Bevorzugt die Datei, die gerade läuft."""
    source = _ANSI.sub("", text or "")
    frames = [(path, int(line)) for path, line in _PY_FRAME.findall(source)]
    if frames:
        chosen = frames[-1]
        if preferred:
            own = [item for item in frames if same_file(item[0], preferred)]
            if own:
                chosen = own[-1]
        return {"file": _prefer(chosen[0], preferred), "line": chosen[1], "message": _message(source)}
    match = _PS_PATH.search(source)
    if match:
        return {"file": _prefer(match.group(1).strip(), preferred), "line": int(match.group(2)), "message": _message(source)}
    match = _PS_LINE.search(source)
    if match:
        return {"file": preferred, "line": int(match.group(1)), "message": _message(source)}
    match = None
    for item in _PS_MODERN.finditer(source):
        match = item
    if match:
        return {"file": _prefer(match.group(1).strip(), preferred), "line": int(match.group(2)), "message": _message(source)}
    match = None
    for item in _SH_LINE.finditer(source):
        match = item
    if match:
        return {"file": _prefer(match.group(1).strip(), preferred), "line": int(match.group(2)), "message": _message(source)}
    match = _ZEILE.search(source)
    if match:
        return {"file": preferred, "line": int(match.group(1)), "message": _message(source)}
    return None


def _prefer(found: str, preferred: str) -> str:
    if preferred and same_file(found, preferred):
        return preferred
    return found or preferred


def _message(text: str) -> str:
    found = list(_EXC.finditer(text))
    if found:
        return found[-1].group(0).strip()[:500]
    for line in reversed(text.splitlines()):
        stripped = line.strip()
        if stripped and not stripped.startswith("File ") and stripped != "^":
            return stripped[:500]
    return "Fehler"
