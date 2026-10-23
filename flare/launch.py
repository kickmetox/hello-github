"""Programme, Verknüpfungen und das Öffnen eines Treffers."""

from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any

from flare.paths import norm, parent_of

_SECRET_NAMES = {
    ".env",
    ".netrc",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "credentials",
    "secrets.json",
}
_SECRET_EXTS = {".pem", ".key", ".p12", ".pfx", ".kdbx"}


def is_secret_name(name: str) -> bool:
    lowered = name.casefold()
    if lowered in _SECRET_NAMES:
        return True
    suffix = Path(lowered).suffix
    return suffix in _SECRET_EXTS


def _cstring(buf: bytes, offset: int) -> str | None:
    if offset < 0 or offset >= len(buf):
        return None
    end = buf.find(b"\x00", offset)
    if end < 0:
        return None
    try:
        return buf[offset:end].decode("mbcs" if sys.platform == "win32" else "utf-8", "replace")
    except LookupError:
        return buf[offset:end].decode("latin-1", "replace")


def parse_lnk(path: str) -> dict[str, Any] | None:
    """Lokalen Zielpfad aus einer .lnk-Datei lesen. Reicht für Startmenü-Einträge."""
    try:
        blob = Path(path).read_bytes()
    except OSError:
        return None
    if len(blob) < 76 or struct.unpack_from("<I", blob, 0)[0] < 76:
        return None
    flags = struct.unpack_from("<I", blob, 0x14)[0]
    cursor = struct.unpack_from("<I", blob, 0)[0]
    if flags & 0x1:  # HasLinkTargetIDList
        if cursor + 2 > len(blob):
            return None
        id_size = struct.unpack_from("<H", blob, cursor)[0]
        cursor += 2 + id_size
    target = ""
    if flags & 0x2 and cursor + 28 <= len(blob):  # HasLinkInfo
        info = blob[cursor:]
        info_size, header_size, info_flags = struct.unpack_from("<III", info, 0)
        if header_size >= 28 and info_flags & 0x1:
            local_off = struct.unpack_from("<I", info, 16)[0]
            target = _cstring(info[:info_size], local_off) or ""
            if header_size >= 36 and not target:
                uni_off = struct.unpack_from("<I", info, 28)[0]
                if 0 < uni_off < info_size - 2:
                    raw = info[uni_off:info_size]
                    zero = raw.find(b"\x00\x00")
                    if zero >= 0 and zero % 2 == 1:
                        zero += 1
                    chunk = raw if zero < 0 else raw[:zero]
                    try:
                        target = chunk.decode("utf-16le", "ignore").rstrip("\x00")
                    except UnicodeDecodeError:
                        target = ""
    display = Path(path).stem
    full = norm(path)
    launch = target or full
    suffix = Path(target).suffix.casefold() if target else ""
    kind = "app" if suffix in {".exe", ".bat", ".cmd", ".com"} or not target else "file"
    return {
        "kind": kind,
        "name": display,
        "path": full,
        "dir": parent_of(full),
        "ext": ".lnk",
        "launch": launch,
        "mtime_ns": 0,
        "size": 0,
    }


def launch_target(item: dict[str, Any]) -> None:
    sink = os.environ.get("FLARE_OPEN_SINK")
    launch = item.get("launch") or ""
    argv: list[str] | None = None
    if isinstance(launch, str) and launch.startswith("["):
        try:
            parsed = json.loads(launch)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list) and all(isinstance(part, str) for part in parsed):
            argv = parsed
    target = argv[0] if argv else (launch or item["path"])
    if sink:
        with open(sink, "a", encoding="utf-8") as handle:
            handle.write(target + "\n")
        return
    if item.get("kind") == "calc":
        return
    if argv:
        subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return
    path = launch or item["path"]
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]


def _drive_root_text(text: str) -> bool:
    """C: oder C:\\ haben keinen Elternordner. Andere Pfade schon."""
    bare = text.rstrip("\\")
    return len(bare) == 2 and bare[0].isalpha() and bare[1] == ":"


def windows_path(path: str) -> str:
    """Voller Windows-Pfad mit Backslash. Ein Laufwerksstamm endet auf \\."""
    text = str(path or "").replace("/", "\\").strip("\x00").strip()
    if _drive_root_text(text):
        return text.rstrip("\\")[0] + ":\\"
    return text.rstrip("\\")


def is_drive_root(path: str) -> bool:
    return _drive_root_text(str(path or "").replace("/", "\\").strip("\x00").strip())


def quote_explorer_path(path: str) -> str:
    """Pfad für explorer /select,. Leerzeichen stehen in Anführungszeichen."""
    text = windows_path(path)
    if any(ch.isspace() for ch in text) or '"' in text:
        return '"' + text.replace('"', "") + '"'
    return text


def explorer_select_args(path: str) -> list[str]:
    """Argumente für explorer.exe.

    Datei und Ordner: explorer.exe /select, mit dem vollen Pfad.
    Ein Laufwerksstamm ohne Elternordner wird selbst geöffnet, ohne /select.
    """
    full = windows_path(path)
    if not full:
        return []
    if is_drive_root(full):
        return ["explorer.exe", full]
    return ["explorer.exe", "/select," + quote_explorer_path(full)]


def explorer_command_line(args: list[str]) -> str:
    """Kommandozeile, die explorer so erwartet. Die Quotes stecken schon im Argument."""
    return " ".join(args)


def reveal_in_explorer(path: str) -> str | None:
    """Explorer mit dem Eintrag öffnen. Kein Walk und kein Index.

    None bei Erfolg. Sonst ein kurzer deutscher Status.
    """
    args = explorer_select_args(path)
    if len(args) < 2:
        return "Pfad fehlt."
    probe = windows_path(path)
    try:
        found = os.path.exists(probe)
    except OSError:
        found = False
    if not found:
        return "Datei fehlt."
    if sys.platform != "win32":
        return "Explorer startet nicht."
    command = explorer_command_line(args)
    try:
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        return "Explorer startet nicht."
    return None
