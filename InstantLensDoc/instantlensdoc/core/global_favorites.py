"""Globale Dokument-Favoriten (Schema ildfav-v1) — Schnelljump über Docs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from ild_pdf.annotate import FAV_SCHEMA_ID, FAV_VERSION, FavoritesImportError
from instantlensdoc.config import config_dir

GLOBAL_FAV_FILENAME = "global_favorites.ildfav.json"
GLOBAL_FAV_MAX = 24


@dataclass(frozen=True)
class GlobalFavorite:
    """Ein Favorit: PDF-Pfad + 0-basierte Seite + optional Label."""

    path: str
    page: int
    label: str = ""

    def display_label(self) -> str:
        name = Path(self.path).name if self.path else "?"
        base = (self.label or "").strip() or name
        return f"{base} · S{self.page + 1}"


def global_favorites_path() -> Path:
    return config_dir() / GLOBAL_FAV_FILENAME


def _normalize_entry(item: object) -> GlobalFavorite | None:
    if isinstance(item, GlobalFavorite):
        return item
    if isinstance(item, dict):
        path = str(item.get("path") or "").strip()
        if not path:
            return None
        try:
            page = int(item.get("page", 0))
        except (TypeError, ValueError):
            return None
        if page < 0:
            return None
        label = str(item.get("label") or "").strip()[:80]
        return GlobalFavorite(path=str(Path(path)), page=page, label=label)
    return None


def favorites_to_export_dict(
    favorites: Sequence[GlobalFavorite | dict],
    *,
    source: str = "",
) -> dict:
    """Globale Favoriten → ildfav-v1 Dict (scope=global)."""
    out: list[dict] = []
    seen: set[tuple[str, int]] = set()
    for raw in favorites:
        fav = _normalize_entry(raw)
        if fav is None:
            continue
        key = (str(Path(fav.path)), int(fav.page))
        if key in seen:
            continue
        seen.add(key)
        entry: dict = {"path": key[0], "page": key[1]}
        if fav.label:
            entry["label"] = fav.label
        out.append(entry)
        if len(out) >= GLOBAL_FAV_MAX:
            break
    return {
        "version": FAV_VERSION,
        "schema": FAV_SCHEMA_ID,
        "scope": "global",
        "favorites": out,
        "page_favorites": out,  # Alias für ildfav-v1 Interop
        "source": str(source or "InstantLensDoc-global"),
    }


def parse_favorites_dict(data: dict) -> list[GlobalFavorite]:
    """ildfav-v1 Dict → Liste GlobalFavorite (scope global oder gemischt)."""
    if not isinstance(data, dict):
        raise FavoritesImportError("Favoriten-JSON muss ein Objekt sein.")
    ver = data.get("version")
    schema = data.get("schema")
    try:
        ver_i = int(ver)
    except (TypeError, ValueError):
        raise FavoritesImportError(
            f"Ungültige Version {ver!r} — erwartet {FAV_VERSION} ({FAV_SCHEMA_ID})."
        ) from None
    if ver_i != FAV_VERSION:
        raise FavoritesImportError(
            f"Inkompatible Version {ver_i} — erwartet {FAV_VERSION} ({FAV_SCHEMA_ID})."
        )
    if schema is not None and str(schema) != FAV_SCHEMA_ID:
        raise FavoritesImportError(
            f"Inkompatibles Schema „{schema}“ — erwartet „{FAV_SCHEMA_ID}“."
        )
    raw = data.get("favorites")
    if raw is None:
        raw = data.get("page_favorites")
    if raw is None:
        raise FavoritesImportError("Feld „favorites“ / „page_favorites“ fehlt.")
    if not isinstance(raw, (list, tuple)):
        raise FavoritesImportError("„favorites“ muss eine Liste sein.")
    out: list[GlobalFavorite] = []
    seen: set[tuple[str, int]] = set()
    for item in raw:
        # Per-Doc ildfav: reine Seitenzahlen — ohne path überspringen
        if isinstance(item, (int, float)) and not isinstance(item, bool):
            continue
        fav = _normalize_entry(item)
        if fav is None:
            continue
        key = (str(Path(fav.path)), int(fav.page))
        if key in seen:
            continue
        seen.add(key)
        out.append(GlobalFavorite(path=key[0], page=key[1], label=fav.label))
        if len(out) >= GLOBAL_FAV_MAX:
            break
    return out


def load_global_favorites() -> list[GlobalFavorite]:
    path = global_favorites_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    try:
        return parse_favorites_dict(data)
    except FavoritesImportError:
        return []


def save_global_favorites(favorites: Sequence[GlobalFavorite | dict]) -> Path:
    dest = global_favorites_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = favorites_to_export_dict(favorites)
    dest.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return dest


def add_global_favorite(
    path: str | Path,
    page: int,
    *,
    label: str = "",
) -> list[GlobalFavorite]:
    """Favorit vorne einfügen (max GLOBAL_FAV_MAX); Duplikat path+page → nach vorne."""
    p = str(Path(path))
    page_i = max(0, int(page))
    lbl = str(label or "").strip()[:80]
    current = [f for f in load_global_favorites() if not (f.path == p and f.page == page_i)]
    current.insert(0, GlobalFavorite(path=p, page=page_i, label=lbl))
    current = current[:GLOBAL_FAV_MAX]
    save_global_favorites(current)
    return current


def remove_global_favorite(path: str | Path, page: int) -> list[GlobalFavorite]:
    p = str(Path(path))
    page_i = int(page)
    current = [f for f in load_global_favorites() if not (f.path == p and f.page == page_i)]
    save_global_favorites(current)
    return current


def reorder_global_favorites(
    order: Sequence[GlobalFavorite | dict | tuple],
) -> list[GlobalFavorite]:
    """Neue Reihenfolge speichern (Drag-Reorder) — 1.7.1.

    ``order``: GlobalFavorite, Dict, oder ``(path, page)``-Tupel.
    Unbekannte Einträge werden übersprungen; fehlende bestehende Favoriten
    werden ans Ende angehängt.
    """
    current = load_global_favorites()
    by_key = {(f.path, f.page): f for f in current}
    new_list: list[GlobalFavorite] = []
    seen: set[tuple[str, int]] = set()
    for raw in order:
        fav: GlobalFavorite | None = None
        if isinstance(raw, GlobalFavorite):
            fav = raw
        elif isinstance(raw, (tuple, list)) and len(raw) >= 2:
            try:
                key = (str(Path(raw[0])), int(raw[1]))
            except (TypeError, ValueError):
                continue
            fav = by_key.get(key)
        else:
            fav = _normalize_entry(raw)
        if fav is None:
            continue
        key = (str(Path(fav.path)), int(fav.page))
        if key in seen:
            continue
        # Label aus aktuellem Store bevorzugen
        existing = by_key.get(key)
        if existing is not None:
            fav = existing
        else:
            fav = GlobalFavorite(path=key[0], page=key[1], label=fav.label)
        seen.add(key)
        new_list.append(fav)
        if len(new_list) >= GLOBAL_FAV_MAX:
            break
    if len(new_list) < GLOBAL_FAV_MAX:
        for fav in current:
            key = (fav.path, fav.page)
            if key in seen:
                continue
            seen.add(key)
            new_list.append(fav)
            if len(new_list) >= GLOBAL_FAV_MAX:
                break
    save_global_favorites(new_list)
    return load_global_favorites()


def export_global_favorites_json(path: str | Path) -> Path:
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = favorites_to_export_dict(load_global_favorites())
    dest.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return dest


def import_global_favorites_json(
    path: str | Path,
    *,
    merge: bool = True,
) -> list[GlobalFavorite]:
    src = Path(path)
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise FavoritesImportError(f"Ungültiges JSON: {e}") from e
    except OSError as e:
        raise FavoritesImportError(str(e)) from e
    incoming = parse_favorites_dict(data)
    if not merge:
        save_global_favorites(incoming)
        return load_global_favorites()
    # Merge: neue vorne, bestehende behalten
    seen: set[tuple[str, int]] = set()
    merged: list[GlobalFavorite] = []
    for fav in list(incoming) + load_global_favorites():
        key = (fav.path, fav.page)
        if key in seen:
            continue
        seen.add(key)
        merged.append(fav)
        if len(merged) >= GLOBAL_FAV_MAX:
            break
    save_global_favorites(merged)
    return load_global_favorites()
