"""Asset-Bibliothek und Symbole (verknüpfte Klone des Masters)."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4


def _nid() -> str:
    return uuid4().hex[:10]


@dataclass
class AssetItem:
    id: str = field(default_factory=_nid)
    name: str = ""
    kind: str = "image"  # image | svg | symbol | render
    path: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DtpSymbol:
    id: str = field(default_factory=_nid)
    name: str = "Symbol"
    proto: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "proto": dict(self.proto)}


class AssetLibrary:
    def __init__(self) -> None:
        self.items: list[AssetItem] = []
        self.symbols: list[DtpSymbol] = []

    def add_file(self, path: str | Path, *, kind: str = "") -> AssetItem:
        p = Path(path)
        k = (kind or "").lower()
        if not k:
            suf = p.suffix.lower()
            k = {
                ".svg": "svg",
                ".pdf": "render",
                ".ai": "render",
                ".eps": "render",
            }.get(suf, "image")
        item = AssetItem(name=p.stem, kind=k, path=str(p))
        self.items.append(item)
        return item

    def get(self, asset_id: str) -> Optional[AssetItem]:
        for it in self.items:
            if it.id == asset_id:
                return it
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [i.to_dict() for i in self.items],
            "symbols": [s.to_dict() for s in self.symbols],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "AssetLibrary":
        lib = cls()
        raw = data or {}
        for it in raw.get("items") or []:
            if not isinstance(it, dict):
                continue
            known = {f.name for f in AssetItem.__dataclass_fields__.values()}  # type: ignore[attr-defined]
            lib.items.append(AssetItem(**{k: it[k] for k in it if k in known}))
        for s in raw.get("symbols") or []:
            if not isinstance(s, dict):
                continue
            lib.symbols.append(
                DtpSymbol(
                    id=str(s.get("id") or _nid()),
                    name=str(s.get("name") or "Symbol"),
                    proto=dict(s.get("proto") or {}),
                )
            )
        return lib


def frame_to_proto(fr: Any) -> dict[str, Any]:
    if hasattr(fr, "to_dict"):
        d = dict(fr.to_dict())
    else:
        d = dict(fr)
    d.pop("id", None)
    d.pop("x", None)
    d.pop("y", None)
    return d


def register_symbol(library: AssetLibrary, fr: Any, name: str = "") -> DtpSymbol:
    sym = DtpSymbol(name=name or getattr(fr, "id", "Symbol"), proto=frame_to_proto(fr))
    library.symbols.append(sym)
    try:
        fr.symbol_id = sym.id
        fr.linked = True
    except Exception:
        pass
    return sym


def place_symbol(doc: Any, symbol_id: str, *, x: float, y: float, page: int = 0) -> Any:
    from instantlensdoc.dtp.model import DtpFrame

    library = getattr(doc, "library", None)
    if library is None:
        raise KeyError("Keine Bibliothek")
    sym = next((s for s in library.symbols if s.id == symbol_id), None)
    if sym is None:
        raise KeyError(symbol_id)
    proto = dict(sym.proto)
    proto["x"] = float(x)
    proto["y"] = float(y)
    proto["page"] = int(page)
    proto["symbol_id"] = sym.id
    proto["linked"] = True
    fr = DtpFrame.from_dict(proto)
    doc.frames.append(fr)
    return fr


def sync_linked_clones(doc: Any, symbol_id: str) -> int:
    library = getattr(doc, "library", None)
    if library is None:
        return 0
    sym = next((s for s in library.symbols if s.id == symbol_id), None)
    if sym is None:
        return 0
    n = 0
    skip = {"id", "x", "y", "page", "symbol_id", "linked"}
    for fr in doc.frames:
        if getattr(fr, "symbol_id", "") != symbol_id:
            continue
        for k, v in sym.proto.items():
            if k in skip:
                continue
            if hasattr(fr, k):
                setattr(fr, k, deepcopy(v) if not isinstance(v, (int, float, str, bool)) else v)
        n += 1
    return n
