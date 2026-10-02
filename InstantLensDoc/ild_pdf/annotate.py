"""Basis-Annotationen (Highlight, Underline, Sticky Note, Textfeld)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional
from uuid import uuid4


class AnnotationType(str, Enum):
    HIGHLIGHT = "highlight"
    UNDERLINE = "underline"
    STICKY = "sticky"
    TEXT = "text"


@dataclass
class Annotation:
    page: int
    type: AnnotationType
    x: float
    y: float
    width: float = 120.0
    height: float = 24.0
    text: str = ""
    color: str = "#FFFF00"
    id: str = field(default_factory=lambda: uuid4().hex)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["type"] = self.type.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Annotation":
        data = dict(data)
        data["type"] = AnnotationType(data["type"])
        return cls(**data)


class AnnotationStore:
    """Annotationen neben dem PDF als JSON speichern."""

    def __init__(self, pdf_path: str | Path | None = None):
        self.pdf_path = Path(pdf_path) if pdf_path else None
        self.annotations: List[Annotation] = []
        if self.pdf_path and self.sidecar_path.exists():
            self.load()

    @property
    def sidecar_path(self) -> Path:
        if self.pdf_path is None:
            raise RuntimeError("Kein PDF-Pfad gesetzt")
        return self.pdf_path.with_suffix(self.pdf_path.suffix + ".ildann.json")

    def add(self, ann: Annotation) -> Annotation:
        self.annotations.append(ann)
        return ann

    def remove(self, ann_id: str) -> bool:
        before = len(self.annotations)
        self.annotations = [a for a in self.annotations if a.id != ann_id]
        return len(self.annotations) < before

    def for_page(self, page: int) -> List[Annotation]:
        return [a for a in self.annotations if a.page == page]

    def save(self, path: Optional[Path] = None) -> Path:
        target = path or self.sidecar_path
        payload = {
            "version": 1,
            "pdf": str(self.pdf_path) if self.pdf_path else None,
            "annotations": [a.to_dict() for a in self.annotations],
        }
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return target

    def load(self, path: Optional[Path] = None) -> None:
        target = path or self.sidecar_path
        data = json.loads(target.read_text(encoding="utf-8"))
        self.annotations = [Annotation.from_dict(a) for a in data.get("annotations", [])]
