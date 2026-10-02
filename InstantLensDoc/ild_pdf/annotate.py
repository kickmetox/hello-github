"""Basis-Annotationen inkl. Stempel/Callout/Formen/Messung/Text-Overlay; Sidecar-Persistenz."""

from __future__ import annotations

import json
import math
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterator, List, Optional
from uuid import uuid4

SIDECAR_VERSION = 3
HISTORY_LIMIT = 40


class AnnotationType(str, Enum):
    HIGHLIGHT = "highlight"
    UNDERLINE = "underline"
    STICKY = "sticky"
    TEXT = "text"
    STAMP = "stamp"
    CALLOUT = "callout"
    RECTANGLE = "rectangle"
    LINE = "line"
    ARROW = "arrow"
    MEASURE = "measure"
    TEXT_OVERLAY = "text_overlay"
    SIGNATURE_FIELD = "signature_field"  # Platzhalter-Rahmen
    SIGNATURE = "signature"  # Bild-Unterschrift (text: img:…)
    REDACTION = "redaction"  # Schwärzung (opakes Rechteck)


# Vordefinierte Stempel-Texte (UI kann erweitern)
STAMP_PRESETS = (
    "GEPRÜFT",
    "FREIGEGEBEN",
    "ENTWURF",
    "VERTRAULICH",
    "KOPIE",
    "ERLEDIGT",
)

# Werkzeuge die per Drag (Press→Release) gezeichnet werden
DRAG_TYPES = frozenset(
    {
        AnnotationType.RECTANGLE,
        AnnotationType.LINE,
        AnnotationType.ARROW,
        AnnotationType.MEASURE,
        AnnotationType.HIGHLIGHT,
        AnnotationType.REDACTION,
    }
)


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
    # Callout / Linie / Pfeil / Messung: zweiter Punkt
    callout_x: float = 0.0
    callout_y: float = 0.0
    font_size: float = 12.0
    opacity: float = 1.0  # Deckkraft 0.05–1.0
    id: str = field(default_factory=lambda: uuid4().hex)
    created: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    modified: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def touch(self) -> None:
        self.modified = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def end_point(self) -> tuple[float, float]:
        """Endpunkt für Linien-artige Annotationen."""
        if self.callout_x or self.callout_y:
            return float(self.callout_x), float(self.callout_y)
        return float(self.x + self.width), float(self.y + self.height)

    def length_px(self) -> float:
        x2, y2 = self.end_point()
        return math.hypot(x2 - self.x, y2 - self.y)

    def measure_label(self, scale: float = 1.0, unit: str = "pt") -> str:
        """Distanzlabel: Pixel → PDF-Punkte (bei bekanntem Render-Scale)."""
        px = self.length_px()
        pts = px / max(scale, 0.01)
        if unit == "mm":
            return f"{pts * 25.4 / 72:.1f} mm"
        if unit == "px":
            return f"{px:.0f} px"
        return f"{pts:.1f} pt"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["type"] = self.type.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Annotation":
        data = dict(data)
        data["type"] = AnnotationType(data["type"])
        data.setdefault("callout_x", 0.0)
        data.setdefault("callout_y", 0.0)
        data.setdefault("font_size", 12.0)
        try:
            op = float(data.get("opacity", 1.0))
        except (TypeError, ValueError):
            op = 1.0
        data["opacity"] = max(0.05, min(1.0, op))
        data.setdefault("created", datetime.now(timezone.utc).isoformat(timespec="seconds"))
        data.setdefault("modified", data["created"])
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        data = {k: v for k, v in data.items() if k in known}
        return cls(**data)


class AnnotationStore:
    """Annotationen neben dem PDF als JSON speichern (*.ildann.json)."""

    def __init__(self, pdf_path: str | Path | None = None):
        self.pdf_path = Path(pdf_path) if pdf_path else None
        self.annotations: List[Annotation] = []
        self.dirty = False
        self._meta: dict = {}
        self._undo: List[List[dict]] = []
        self._redo: List[List[dict]] = []
        self._recording = True
        if self.pdf_path and self.sidecar_path.exists():
            try:
                self.load()
            except Exception:
                # Kaputte Sidecar darf Öffnen nicht crashen
                self.annotations = []
                self.dirty = False
                self._meta = {}
                self.clear_history()

    @property
    def sidecar_path(self) -> Path:
        if self.pdf_path is None:
            raise RuntimeError("Kein PDF-Pfad gesetzt")
        return self.pdf_path.with_suffix(self.pdf_path.suffix + ".ildann.json")

    def clear_history(self) -> None:
        self._undo.clear()
        self._redo.clear()

    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    def _snapshot(self) -> List[dict]:
        return [a.to_dict() for a in self.annotations]

    def _restore(self, snap: List[dict]) -> None:
        self.annotations = [Annotation.from_dict(a) for a in snap]
        self.dirty = True

    def _push_undo(self) -> None:
        if not self._recording:
            return
        self._undo.append(self._snapshot())
        if len(self._undo) > HISTORY_LIMIT:
            self._undo.pop(0)
        self._redo.clear()

    @contextmanager
    def atomic(self) -> Iterator[None]:
        """Mehrere Mutationen als eine Undo-Stufe."""
        self._push_undo()
        prev = self._recording
        self._recording = False
        try:
            yield
        finally:
            self._recording = prev

    def undo(self) -> bool:
        if not self._undo:
            return False
        self._redo.append(self._snapshot())
        self._restore(self._undo.pop())
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        self._undo.append(self._snapshot())
        self._restore(self._redo.pop())
        return True

    def add(self, ann: Annotation) -> Annotation:
        self._push_undo()
        self.annotations.append(ann)
        self.dirty = True
        return ann

    def get(self, ann_id: str) -> Optional[Annotation]:
        for a in self.annotations:
            if a.id == ann_id:
                return a
        return None

    def update(self, ann_id: str, **kwargs) -> Optional[Annotation]:
        for a in self.annotations:
            if a.id == ann_id:
                self._push_undo()
                for k, v in kwargs.items():
                    if hasattr(a, k):
                        setattr(a, k, v)
                a.touch()
                self.dirty = True
                return a
        return None

    def remove(self, ann_id: str) -> bool:
        before = len(self.annotations)
        if not any(a.id == ann_id for a in self.annotations):
            return False
        self._push_undo()
        self.annotations = [a for a in self.annotations if a.id != ann_id]
        changed = len(self.annotations) < before
        if changed:
            self.dirty = True
        return changed

    def remove_last(self, page: int | None = None) -> Optional[Annotation]:
        """Löscht die letzte Annotation (optional nur auf page). Undo-fähig."""
        candidates = self.annotations if page is None else self.for_page(page)
        if not candidates:
            return None
        target = candidates[-1]
        if self.remove(target.id):
            return target
        return None

    def for_page(self, page: int) -> List[Annotation]:
        return [a for a in self.annotations if a.page == page]

    def text_overlays(self, page: int | None = None) -> List[Annotation]:
        items = [
            a
            for a in self.annotations
            if a.type in (AnnotationType.TEXT_OVERLAY, AnnotationType.TEXT)
        ]
        if page is not None:
            items = [a for a in items if a.page == page]
        return items

    def remap_pages(self, mapping: dict[int, int]) -> None:
        """Seitenindizes nach reorder/delete anpassen; fehlende Keys = Seite entfernt."""
        planned: List[tuple[Annotation, int]] = []
        changed = False
        for ann in self.annotations:
            if ann.page in mapping:
                new_page = mapping[ann.page]
                if new_page != ann.page:
                    changed = True
                planned.append((ann, new_page))
            else:
                changed = True
        if not changed and len(planned) == len(self.annotations):
            return
        self._push_undo()
        kept: List[Annotation] = []
        for ann, new_page in planned:
            if ann.page != new_page:
                ann.page = new_page
                ann.touch()
            kept.append(ann)
        self.annotations = kept
        self.dirty = True

    def save(self, path: Optional[Path] = None, force: bool = False) -> Path:
        target = path or self.sidecar_path
        if not force and not self.dirty and target.exists() and path is None:
            return target
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        payload = {
            "version": SIDECAR_VERSION,
            "pdf": str(self.pdf_path) if self.pdf_path else None,
            "saved_at": now,
            "count": len(self.annotations),
            "meta": self._meta,
            "annotations": [a.to_dict() for a in self.annotations],
        }
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        self.dirty = False
        return target

    def load(self, path: Optional[Path] = None) -> None:
        target = path or self.sidecar_path
        data = json.loads(target.read_text(encoding="utf-8"))
        self._meta = dict(data.get("meta") or {})
        self.annotations = [Annotation.from_dict(a) for a in data.get("annotations", [])]
        self.dirty = False
        self.clear_history()

    def export_backup(self, path: str | Path) -> Path:
        """Kopie der Sidecar unter anderem Namen (Backup)."""
        path = Path(path)
        return self.save(path, force=True)

    def export_json(self, path: str | Path) -> Path:
        """Annotationen als JSON exportieren (gleiche Sidecar-Struktur)."""
        return self.export_backup(path)

    def import_json(self, path: str | Path, *, replace: bool = True) -> int:
        """
        Annotationen aus JSON importieren.
        replace=True: ersetzen; False: anhängen (neue IDs behalten, Duplikate möglich).
        Rückgabe: Anzahl importierter Annotationen.
        """
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        imported = [Annotation.from_dict(a) for a in data.get("annotations", [])]
        self._push_undo()
        if replace:
            self.annotations = imported
            if "meta" in data and isinstance(data["meta"], dict):
                self._meta = dict(data["meta"])
        else:
            self.annotations.extend(imported)
        self.dirty = True
        return len(imported)
