"""Slideshow neben der Präsentation: Bild, Video, Text in fester Reihenfolge."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from officedisplay.model.presentation import AUTHOR, EMAIL, new_id


KINDS = ("image", "video", "text")


@dataclass
class ShowEntry:
    id: str
    kind: str
    title: str = ""
    text: str = ""
    path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind if self.kind in KINDS else "text",
            "title": self.title,
            "text": self.text,
            "path": self.path,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ShowEntry:
        kind = data.get("kind") or "text"
        if kind not in KINDS:
            kind = "text"
        return ShowEntry(
            id=data.get("id") or new_id(),
            kind=kind,
            title=data.get("title") or "",
            text=data.get("text") or "",
            path=data.get("path") or None,
        )


@dataclass
class Slideshow:
    title: str = "Slideshow"
    entries: list[ShowEntry] = field(default_factory=list)
    author: str = AUTHOR
    email: str = EMAIL

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "officedisplay-slideshow",
            "version": 1,
            "title": self.title,
            "author": self.author,
            "email": self.email,
            "entries": [entry.to_dict() for entry in self.entries],
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Slideshow:
        return Slideshow(
            title=data.get("title") or "Slideshow",
            entries=[ShowEntry.from_dict(item) for item in data.get("entries") or []],
            author=data.get("author") or AUTHOR,
            email=data.get("email") or EMAIL,
        )

    def clone(self) -> Slideshow:
        return Slideshow.from_dict(copy.deepcopy(self.to_dict()))
