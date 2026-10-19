"""Auswahl von Dateien und Verzeichnissen, die in beiden Welten gelten."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from cpcm.paths import Identity, World, from_canonical, to_canonical


@dataclass
class SelectionItem:
    id: str
    kind: str
    canonical: str
    label: str
    paths: dict[str, str] = field(default_factory=dict)

    def to_json(self) -> dict:
        return asdict(self)

    @classmethod
    def from_json(cls, raw: dict) -> "SelectionItem":
        return cls(
            id=str(raw["id"]),
            kind=str(raw["kind"]),
            canonical=str(raw["canonical"]),
            label=str(raw.get("label") or raw["canonical"].rstrip("/").split("/")[-1]),
            paths={str(k): str(v) for k, v in dict(raw.get("paths") or {}).items()},
        )


@dataclass
class Selection:
    items: list[SelectionItem] = field(default_factory=list)

    def to_json(self) -> dict:
        return {"version": 1, "items": [item.to_json() for item in self.items]}

    @classmethod
    def from_json(cls, raw: dict) -> "Selection":
        return cls(items=[SelectionItem.from_json(item) for item in raw.get("items") or []])


def selection_path(vault: Path) -> Path:
    return vault / "selection.json"


def load_selection(vault: Path) -> Selection:
    path = selection_path(vault)
    if not path.is_file():
        return Selection()
    return Selection.from_json(json.loads(path.read_text(encoding="utf-8")))


def save_selection(vault: Path, selection: Selection) -> None:
    vault.mkdir(parents=True, exist_ok=True)
    selection_path(vault).write_text(
        json.dumps(selection.to_json(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _kind_for(path: Path, requested: str) -> str:
    if requested in ("file", "dir"):
        return requested
    if path.is_dir():
        return "dir"
    if path.is_file() or path.is_symlink():
        return "file"
    raise FileNotFoundError(f"Pfad existiert nicht: {path}")


def add_path(
    selection: Selection,
    path: Path,
    host: Identity,
    counterpart: Identity,
    *,
    kind: str = "auto",
) -> SelectionItem:
    path = Path(path)
    detected = _kind_for(path, kind)
    canonical = to_canonical(path, host)
    other = from_canonical(canonical, counterpart, allow_external=False)
    label = path.name or canonical.split("/")[-1]
    for item in selection.items:
        if item.canonical == canonical:
            item.kind = detected
            item.label = label
            item.paths[host.world.value] = str(path)
            if other is not None:
                item.paths[counterpart.world.value] = other
            return item
    item = SelectionItem(
        id=uuid.uuid4().hex[:12],
        kind=detected,
        canonical=canonical,
        label=label,
        paths={host.world.value: str(path)},
    )
    if other is not None:
        item.paths[counterpart.world.value] = other
    selection.items.append(item)
    return item


def set_world_path(selection: Selection, item_id: str, world: World, path: str) -> SelectionItem:
    for item in selection.items:
        if item.id == item_id:
            item.paths[world.value] = path
            return item
    raise KeyError(item_id)


def remove_item(selection: Selection, item_id: str) -> None:
    before = len(selection.items)
    selection.items = [item for item in selection.items if item.id != item_id]
    if len(selection.items) == before:
        raise KeyError(item_id)


def local_path_for(item: SelectionItem, host: Identity) -> Path | None:
    stored = item.paths.get(host.world.value)
    if stored:
        return Path(stored)
    mapped = from_canonical(item.canonical, host, allow_external=host.native_external())
    return None if mapped is None else Path(mapped)
