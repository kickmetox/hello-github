"""Editor-Zeilen-Lesezeichen Export/Import (Schema ildbm-v1) + Sidecar-Persistenz."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

BM_SCHEMA_ID = "ildbm-v1"
BM_VERSION = 1


class BookmarksImportError(ValueError):
    """Ungültiges oder inkompatibles Zeilen-Lesezeichen-JSON."""


def sidecar_path_for(doc_path: str | Path) -> Path:
    """Sidecar neben der Textdatei: datei.txt.ildbm.json."""
    p = Path(doc_path)
    return p.with_suffix(p.suffix + ".ildbm.json")


def bookmarks_to_export_dict(
    bookmarks: Sequence[tuple[int, str]] | Sequence[int],
    *,
    source: str = "",
) -> dict:
    """[(line, label)|line, …] → Export-Dict (ildbm-v1); Reihenfolge bleibt erhalten."""
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
    Reihenfolge der Liste bleibt erhalten (Drag-Reorder).
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


def save_bookmarks_sidecar(
    doc_path: str | Path,
    bookmarks: Sequence[tuple[int, str]] | Sequence[int],
) -> Path:
    """Lesezeichen neben der Textdatei persistieren (*.ildbm.json)."""
    dest = sidecar_path_for(doc_path)
    return export_bookmarks_json(
        dest, bookmarks, source=Path(doc_path).name
    )


def load_bookmarks_sidecar(
    doc_path: str | Path,
    *,
    max_line: int | None = None,
) -> list[tuple[int, str]] | None:
    """
    Sidecar laden falls vorhanden.
    Rückgabe None wenn keine Datei; [] wenn leer/gültig ohne Einträge.
    """
    src = sidecar_path_for(doc_path)
    if not src.is_file():
        return None
    return load_bookmarks_json(src, max_line=max_line)


def delete_bookmarks_sidecar(doc_path: str | Path) -> bool:
    """Sidecar löschen wenn vorhanden. True wenn gelöscht."""
    src = sidecar_path_for(doc_path)
    if not src.is_file():
        return False
    try:
        src.unlink()
        return True
    except OSError:
        return False
