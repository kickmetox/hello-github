"""Native filesystem paths for copy/display (Windows ``\\``, POSIX ``/``).

QFileDialog and ``QUrl.toLocalFile()`` often yield POSIX slashes on Windows
(``D:/AI_Temp/file.pdf``). Explorer, cmd and many tools need backslashes
(``D:\\AI_Temp\\file.pdf``). Incoming open/save paths may use either separator;
both are accepted. Linux/macOS keep POSIX slashes.
"""

from __future__ import annotations

import ntpath
import os
import posixpath
from pathlib import Path
from typing import Iterable

PathLike = str | Path


def native_fs_path(path: PathLike | None, *, os_name: str | None = None) -> str:
    """Normalize a filesystem path using the OS path module.

    ``os_name`` defaults to ``os.name`` (``nt`` / ``posix``) so tests can
    exercise Windows separators on Linux without touching real paths.
    """
    if path is None:
        return ""
    text = str(path).strip()
    if not text:
        return ""
    name = os.name if os_name is None else os_name
    if name == "nt":
        return ntpath.normpath(text)
    return posixpath.normpath(text)


def native_fs_paths(
    paths: Iterable[PathLike | None], *, os_name: str | None = None
) -> list[str]:
    """Normalize several filesystem paths; empty entries are dropped."""
    out: list[str] = []
    for item in paths:
        text = native_fs_path(item, os_name=os_name)
        if text:
            out.append(text)
    return out


def as_native_path(path: PathLike, *, os_name: str | None = None) -> Path:
    """``Path`` built from a native-separator string (open/save accept both)."""
    text = native_fs_path(path, os_name=os_name)
    return Path(text) if text else Path(str(path))
