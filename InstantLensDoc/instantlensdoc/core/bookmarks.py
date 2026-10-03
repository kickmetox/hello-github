"""Editor-Zeilen-Lesezeichen Export/Import (Schema ildbm-v1)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

BM_SCHEMA_ID = "ildbm-v1"
BM_VERSION = 1


class BookmarksImportError(ValueError):
    """Ungültiges oder inkompatibles Zeilen-Lesezeichen-JSON."""


def bookmarks_to_export_dict(
    bookmarks: Sequence[tuple[int, str]] | Sequence[int],
    *,
    source: str = "",
) -> dict:
    """[(line, label)|line, …] → Export-Dict (ildbm-v1)."""
    out: list[dict] = []
    seen: set[int] = set()
    for item in bookmarks:
        if isinstance(item, (list, tuple)) and len(item) >= 1:
            line = int(item[0])
            label = str(item[1]).strip()[:80] if len(item) > 1 else ""
        else:
            line = int(item)
            label = ""
        if line < 1 or line in seen:
            continue
        seen.add(line)
        entry: dict = {"line": line}
        if label:
            entry["label"] = label
        out.append(entry)
    out.sort(key=lambda e: int(e["line"]))
    return {
        "version": BM_VERSION,
        "schema": BM_SCHEMA_ID,
        "bookmarks": out,
        "source": str(source or ""),
    }


def export_bookmarks_json(
    path: str | Path,
    bookmarks: Sequence[tuple[int, str]] | Sequence[int],
    *,
    source: str = "",
) -> Path:
    """Lesezeichen als JSON-Datei schreiben (ildbm-v1)."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = bookmarks_to_export_dict(bookmarks, source=source)
    dest.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return dest


def parse_bookmarks_dict(
    data: dict,
    *,
    max_line: int | None = None,
) -> list[tuple[int, str]]:
    """
    Lesezeichen aus Dict parsen (ohne Editor-Zustand).
    max_line: optional obere Grenze (inkl.).
    """
    if not isinstance(data, dict):
        raise BookmarksImportError("Lesezeichen-JSON muss ein Objekt sein.")
    ver = data.get("version")
    schema = data.get("schema")
    try:
        ver_i = int(ver)
    except (TypeError, ValueError):
        raise BookmarksImportError(
            f"Ungültige Version {ver!r} — erwartet {BM_VERSION} ({BM_SCHEMA_ID})."
        ) from None
    if ver_i != BM_VERSION:
        raise BookmarksImportError(
            f"Inkompatible Version {ver_i} — erwartet {BM_VERSION} ({BM_SCHEMA_ID})."
        )
    if schema is not None and str(schema) != BM_SCHEMA_ID:
        raise BookmarksImportError(
            f"Inkompatibles Schema „{schema}“ — erwartet „{BM_SCHEMA_ID}“."
        )
    if "bookmarks" not in data:
        raise BookmarksImportError("Feld „bookmarks“ fehlt.")
    raw = data.get("bookmarks")
    if not isinstance(raw, (list, tuple)):
        raise BookmarksImportError("„bookmarks“ muss eine Liste sein.")
    incoming: list[tuple[int, str]] = []
    seen: set[int] = set()
    for item in raw:
        line: int | None = None
        label = ""
        if isinstance(item, dict):
            try:
                line = int(item.get("line"))
            except (TypeError, ValueError):
                continue
            label = str(item.get("label") or "").strip()[:80]
        else:
            try:
                line = int(item)
            except (TypeError, ValueError):
                continue
        if line is None or line < 1 or line in seen:
            continue
        if max_line is not None and line > int(max_line):
            continue
        seen.add(line)
        incoming.append((line, label))
    incoming.sort(key=lambda t: t[0])
    return incoming


def load_bookmarks_json(
    path: str | Path,
    *,
    max_line: int | None = None,
) -> list[tuple[int, str]]:
    """Lesezeichen aus JSON-Datei laden."""
    src = Path(path)
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise BookmarksImportError(f"Ungültiges JSON: {e}") from e
    except OSError as e:
        raise BookmarksImportError(str(e)) from e
    return parse_bookmarks_dict(data, max_line=max_line)
