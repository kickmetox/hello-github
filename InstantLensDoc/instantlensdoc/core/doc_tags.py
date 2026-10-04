"""Dokument-Tags global — Schema ildtags-v1 — 2.5.0.

Sidecar neben der Datei: ``datei.pdf.ildtags.json``.
Globaler Index unter ``config/doc_tags_index.json`` für Welcome/Recent-Filter.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Sequence

from instantlensdoc.config import config_dir

TAGS_SCHEMA_ID = "ildtags-v1"
TAGS_VERSION = 1
INDEX_FILENAME = "doc_tags_index.json"


class DocTagsError(ValueError):
    """Ungültiges oder inkompatibles Dokument-Tags-JSON."""


def sidecar_path_for(doc_path: str | Path) -> Path:
    """Sidecar neben dem Dokument: ``datei.pdf.ildtags.json``."""
    p = Path(doc_path)
    return p.with_suffix(p.suffix + ".ildtags.json")


def index_path() -> Path:
    return config_dir() / INDEX_FILENAME


def normalize_doc_tags(value: object) -> list[str]:
    """Tags normalisieren (wie Ann.-Tags, dedupliziert, max. 40 Zeichen)."""
    try:
        from ild_pdf.annotate import normalize_tags

        return normalize_tags(value)
    except Exception:
        if value is None:
            return []
        if isinstance(value, str):
            parts = [p.strip() for p in value.replace(";", ",").split(",")]
        elif isinstance(value, (list, tuple)):
            parts = [str(p).strip() for p in value]
        else:
            return []
        out: list[str] = []
        seen: set[str] = set()
        for p in parts:
            if not p:
                continue
            key = p.casefold()
            if key in seen:
                continue
            seen.add(key)
            out.append(p[:40])
        return out


def tags_to_export_dict(
    tags: Sequence[str] | object,
    *,
    source: str = "",
) -> dict:
    """Tags → Export-Dict (ildtags-v1)."""
    return {
        "version": TAGS_VERSION,
        "schema": TAGS_SCHEMA_ID,
        "tags": normalize_doc_tags(tags),
        "source": str(source or ""),
    }


def parse_tags_dict(data: dict) -> list[str]:
    """Tags aus Dict parsen (Schema-Validierung)."""
    if not isinstance(data, dict):
        raise DocTagsError("Dokument-Tags-JSON muss ein Objekt sein.")
    ver = data.get("version")
    schema = data.get("schema")
    try:
        ver_i = int(ver)
    except (TypeError, ValueError):
        raise DocTagsError(
            f"Ungültige Version {ver!r} — erwartet {TAGS_VERSION} ({TAGS_SCHEMA_ID})."
        ) from None
    if ver_i != TAGS_VERSION:
        raise DocTagsError(
            f"Inkompatible Version {ver_i} — erwartet {TAGS_VERSION} ({TAGS_SCHEMA_ID})."
        )
    if schema is not None and str(schema) != TAGS_SCHEMA_ID:
        raise DocTagsError(
            f"Inkompatibles Schema „{schema}“ — erwartet „{TAGS_SCHEMA_ID}“."
        )
    if "tags" not in data:
        raise DocTagsError("Feld „tags“ fehlt.")
    return normalize_doc_tags(data.get("tags"))


def load_tags_sidecar(doc_path: str | Path) -> list[str]:
    """Sidecar laden; fehlend → leere Liste."""
    path = sidecar_path_for(doc_path)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    try:
        return parse_tags_dict(data)
    except DocTagsError:
        return []


def save_tags_sidecar(
    doc_path: str | Path,
    tags: Sequence[str] | object,
) -> Path:
    """Sidecar schreiben und Index aktualisieren."""
    dest = sidecar_path_for(doc_path)
    payload = tags_to_export_dict(tags, source=str(Path(doc_path).name))
    dest.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    update_index_entry(doc_path, payload["tags"])
    return dest


def load_index() -> dict[str, list[str]]:
    """Globalen Pfad→Tags-Index laden."""
    path = index_path()
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    entries = raw.get("entries")
    if not isinstance(entries, dict):
        # Flaches Mapping erlauben
        entries = raw
    out: dict[str, list[str]] = {}
    for k, v in entries.items():
        key = str(k).strip()
        if not key:
            continue
        out[key] = normalize_doc_tags(v)
    return out


def save_index(entries: dict[str, list[str]]) -> Path:
    path = index_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = {str(k): normalize_doc_tags(v) for k, v in entries.items() if str(k).strip()}
    payload = {
        "version": TAGS_VERSION,
        "schema": TAGS_SCHEMA_ID,
        "entries": clean,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def update_index_entry(doc_path: str | Path, tags: Sequence[str] | object) -> None:
    """Einen Pfad im Index setzen (leere Tags entfernen den Eintrag)."""
    key = str(Path(doc_path))
    try:
        key = str(Path(doc_path).resolve())
    except OSError:
        pass
    entries = load_index()
    norm = normalize_doc_tags(tags)
    if norm:
        entries[key] = norm
        # auch Rohpfad merken (Recent speichert oft nicht-resolved)
        entries[str(Path(doc_path))] = norm
    else:
        entries.pop(key, None)
        entries.pop(str(Path(doc_path)), None)
    save_index(entries)


def tags_for_path(doc_path: str | Path) -> list[str]:
    """Tags für Pfad: Index, sonst Sidecar (lädt Index nach)."""
    key = str(Path(doc_path))
    try:
        key_res = str(Path(doc_path).resolve())
    except OSError:
        key_res = key
    index = load_index()
    if key_res in index:
        return list(index[key_res])
    if key in index:
        return list(index[key])
    tags = load_tags_sidecar(doc_path)
    if tags:
        update_index_entry(doc_path, tags)
    return tags


def tags_match_filter(tags: Iterable[str], needle: str) -> bool:
    """True wenn needle (casefold) in einem Tag vorkommt."""
    n = (needle or "").strip().casefold()
    if not n:
        return True
    for t in tags:
        if n in str(t).casefold():
            return True
    return False


def collect_known_tags(max_items: int = 48) -> list[str]:
    """Bekannte Dokument-Tags aus Index (dedup, sortiert) — 2.5.4."""
    return [t for t, _n in collect_known_tags_with_counts(max_items=max_items)]


def collect_known_tags_with_counts(
    max_items: int = 48,
    *,
    sort: str = "az",
) -> list[tuple[str, int]]:
    """Bekannte Tags mit Doc-Anzahl, dedupliziert — 2.5.5/2.5.6.

    Zählt eindeutige Dokument-Pfade pro Tag (resolved + Rohpfad werden
    zusammengeführt, damit dieselbe Datei nicht doppelt zählt).
    ``sort``: ``az`` (A–Z, Default) oder ``freq`` (Häufigkeit absteigend) — 2.5.6.
    """
    # tag_key → (display_name, set of path keys)
    buckets: dict[str, tuple[str, set[str]]] = {}
    for path_key, tags in load_index().items():
        if not isinstance(tags, (list, tuple)):
            continue
        # Pfad-Normalisierung für Dedup (resolved vs. roh)
        try:
            path_norm = str(Path(path_key).resolve())
        except OSError:
            path_norm = str(path_key)
        for raw in tags:
            t = str(raw).strip()
            if not t:
                continue
            key = t.casefold()
            if key not in buckets:
                buckets[key] = (t, {path_norm})
            else:
                buckets[key][1].add(path_norm)
    items = [(name, len(paths)) for name, paths in buckets.values()]
    mode = (sort or "az").strip().casefold()
    if mode == "freq":
        # Häufigkeit absteigend, bei Gleichstand A–Z — 2.5.6
        items.sort(key=lambda pair: (-int(pair[1]), pair[0].casefold()))
    else:
        items.sort(key=lambda pair: pair[0].casefold())
    limit = max(1, int(max_items or 48))
    return items[:limit]


def refresh_index_for_paths(paths: Sequence[str | Path]) -> dict[str, list[str]]:
    """Sidecars für Recent-Pfade einlesen und Index aktualisieren."""
    entries = load_index()
    for p in paths:
        tags = load_tags_sidecar(p)
        key = str(Path(p))
        try:
            key_res = str(Path(p).resolve())
        except OSError:
            key_res = key
        if tags:
            entries[key] = tags
            entries[key_res] = tags
    save_index(entries)
    return entries
