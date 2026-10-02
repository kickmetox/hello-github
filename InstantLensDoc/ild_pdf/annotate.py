"""Basis-Annotationen inkl. Stempel/Callout/Formen/Messung/Text-Overlay; Sidecar-Persistenz."""

from __future__ import annotations

import csv
import json
import math
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterator, List, Optional, Sequence
from uuid import uuid4

SIDECAR_VERSION = 4
SCHEMA_ID = "ildann-v4"
# v4: PDF-Highlight-kompatibel (rects/quadPoints + colorRGB/opacity für Interop)
HISTORY_LIMIT = 40


def normalize_tags(value: object) -> list[str]:
    """Freie Tags normalisieren: Liste oder Komma-/Semikolon-String → unique, getrimmt."""
    raw: list[str] = []
    if value is None:
        return []
    if isinstance(value, str):
        parts = value.replace(";", ",").split(",")
        raw = [p.strip() for p in parts]
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            if item is None:
                continue
            s = str(item).strip()
            if "," in s or ";" in s:
                raw.extend(normalize_tags(s))
            else:
                raw.append(s)
    else:
        s = str(value).strip()
        if s:
            raw.append(s)
    out: list[str] = []
    seen: set[str] = set()
    for t in raw:
        if not t:
            continue
        key = t.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


def tags_to_str(tags: object) -> str:
    return ", ".join(normalize_tags(tags))


class AnnotationImportError(ValueError):
    """Annotation-JSON-Import abgebrochen (Schema/Struktur ungültig)."""


def validate_annotation_import_data(data: object) -> dict:
    """
    Import-Payload prüfen (Schema v4). Wirft AnnotationImportError mit lesbarer Meldung.
    Sidecar ohne version/schema bleibt importierbar (Abwärtskompatibilität).
    """
    if not isinstance(data, dict):
        raise AnnotationImportError("Ungültige Datei: Wurzel muss ein JSON-Objekt sein.")
    anns = data.get("annotations")
    if anns is None:
        raise AnnotationImportError("Feld „annotations“ fehlt.")
    if not isinstance(anns, list):
        raise AnnotationImportError("Feld „annotations“ muss eine Liste sein.")

    ver = data.get("version")
    schema = data.get("schema")
    if ver is not None:
        try:
            ver_i = int(ver)
        except (TypeError, ValueError) as e:
            raise AnnotationImportError(f"Feld „version“ ist keine Zahl: {ver!r}") from e
        if ver_i != SIDECAR_VERSION:
            raise AnnotationImportError(
                f"Inkompatible Version {ver_i} — erwartet Schema v{SIDECAR_VERSION} ({SCHEMA_ID})."
            )
    if schema is not None and str(schema) != SCHEMA_ID:
        raise AnnotationImportError(
            f"Inkompatibles Schema „{schema}“ — erwartet „{SCHEMA_ID}“ (Version {SIDECAR_VERSION})."
        )
    if ver is not None and schema is None:
        raise AnnotationImportError(
            f"Schema v{SIDECAR_VERSION} erfordert Feld „schema“: „{SCHEMA_ID}“."
        )
    if schema is not None and ver is None:
        raise AnnotationImportError(
            f"Feld „schema“ „{schema}“ erfordert „version“: {SIDECAR_VERSION}."
        )

    for idx, raw in enumerate(anns):
        if not isinstance(raw, dict):
            raise AnnotationImportError(
                f"Annotation [{idx}]: Eintrag muss ein Objekt sein (ist {type(raw).__name__})."
            )
        if "type" not in raw and not isinstance(raw.get("pdf_highlight"), dict):
            raise AnnotationImportError(f"Annotation [{idx}]: Feld „type“ fehlt.")
        try:
            t_raw = raw.get("type")
            if t_raw is None and isinstance(raw.get("pdf_highlight"), dict):
                ph = raw["pdf_highlight"]
                subtype = str(ph.get("subtype") or "Highlight").lower()
                t_raw = "highlight" if "under" not in subtype else "underline"
            AnnotationType(str(t_raw))
        except (ValueError, KeyError) as e:
            raise AnnotationImportError(
                f"Annotation [{idx}]: unbekannter Typ „{raw.get('type')}“."
            ) from e
        if "page" not in raw:
            raise AnnotationImportError(f"Annotation [{idx}]: Feld „page“ fehlt.")
        try:
            page_i = int(raw["page"])
        except (TypeError, ValueError) as e:
            raise AnnotationImportError(f"Annotation [{idx}]: „page“ muss eine Ganzzahl sein.") from e
        if page_i < 0:
            raise AnnotationImportError(f"Annotation [{idx}]: „page“ darf nicht negativ sein ({page_i}).")
        has_xy = "x" in raw and "y" in raw
        has_rects = isinstance(raw.get("rects"), list) and raw["rects"]
        ph = raw.get("pdf_highlight")
        has_ph_rects = isinstance(ph, dict) and isinstance(ph.get("rects"), list) and ph["rects"]
        if not has_xy and not has_rects and not has_ph_rects:
            raise AnnotationImportError(
                f"Annotation [{idx}]: Position fehlt (x/y oder rects/pdf_highlight.rects)."
            )
    return data


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
    "GENEHMIGT",
    "ENTWURF",
    "VERTRAULICH",
    "GEPRÜFT",
    "FREIGEGEBEN",
    "KOPIE",
    "ERLEDIGT",
)

# Kern-Bibliothek: Genehmigt / Entwurf / Vertraulich (+ optionales Datum)
STAMP_LIBRARY = (
    ("GENEHMIGT", "#1E8449"),
    ("ENTWURF", "#D68910"),
    ("VERTRAULICH", "#C0392B"),
)


def stamp_with_date(
    label: str,
    *,
    include_date: bool = True,
    when: datetime | None = None,
    date_fmt: str = "%d.%m.%Y",
) -> str:
    """Stempeltext, optional mit Datum (lokal, Default heute)."""
    base = (label or "STEMPEL").strip() or "STEMPEL"
    if not include_date:
        return base
    dt = when or datetime.now()
    # naive lokal ok für Stempelanzeige
    return f"{base}\n{dt.strftime(date_fmt)}"


def stamp_library_items(*, include_date: bool = True) -> list[tuple[str, str, str]]:
    """
    Stempel-Bibliothek als (anzeige, text, farbe).
    Anzeige enthält Datum wenn include_date; text = Annotationstext.
    """
    items: list[tuple[str, str, str]] = []
    for label, color in STAMP_LIBRARY:
        text = stamp_with_date(label, include_date=include_date)
        items.append((text.replace("\n", " · "), text, color))
    return items

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

# Deutsche Typ-Labels für Kommentar-Berichte (TXT/MD)
REPORT_TYPE_LABELS: dict[str, str] = {
    "highlight": "Markierung",
    "underline": "Unterstreichung",
    "sticky": "Notiz",
    "text": "Text",
    "stamp": "Stempel",
    "callout": "Callout",
    "rectangle": "Rechteck",
    "line": "Linie",
    "arrow": "Pfeil",
    "measure": "Messung",
    "text_overlay": "Text-Overlay",
    "signature_field": "Signaturfeld",
    "signature": "Signatur",
    "redaction": "Schwärzung",
}


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
    rotation: float = 0.0  # Stempel-Drehung in Grad (0/90/180/270)
    tags: List[str] = field(default_factory=list)  # freie Labels, filterbar
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
        d["tags"] = normalize_tags(d.get("tags"))
        return d

    def color_rgb(self) -> list[float]:
        """Farbe als RGB 0..1 (PDF-Highlight / PDF.js kompatibel)."""
        c = (self.color or "#FFFF00").strip().lstrip("#")
        if len(c) == 3:
            c = "".join(ch * 2 for ch in c)
        try:
            r = int(c[0:2], 16) / 255.0
            g = int(c[2:4], 16) / 255.0
            b = int(c[4:6], 16) / 255.0
            return [round(r, 4), round(g, 4), round(b, 4)]
        except Exception:
            return [1.0, 1.0, 0.0]

    def highlight_rects(self) -> list[list[float]]:
        """Ein Rechteck [x, y, width, height] im Sidecar-Koordinatensystem."""
        return [
            [
                float(self.x),
                float(self.y),
                float(self.width),
                float(self.height),
            ]
        ]

    def highlight_quad_points(self) -> list[float]:
        """
        PDF-ähnliche QuadPoints (8 Zahlen): TL, TR, BL, BR in Sidecar-Pixeln.
        Y wächst nach unten (UI); für PDF-Y-Spiegelung siehe Export-Meta `y_origin`.
        """
        x0, y0 = float(self.x), float(self.y)
        x1, y1 = x0 + float(self.width), y0 + float(self.height)
        # TL, TR, BL, BR
        return [x0, y0, x1, y0, x0, y1, x1, y1]

    def to_export_dict(self) -> dict:
        """Sidecar-Feld + PDF-Highlight-Interop (Schema v4)."""
        d = self.to_dict()
        if self.type in (AnnotationType.HIGHLIGHT, AnnotationType.UNDERLINE):
            d["rects"] = self.highlight_rects()
            d["quadPoints"] = self.highlight_quad_points()
            d["colorRGB"] = self.color_rgb()
            d["pdf_highlight"] = {
                "subtype": "Highlight" if self.type == AnnotationType.HIGHLIGHT else "Underline",
                "rects": self.highlight_rects(),
                "quadPoints": self.highlight_quad_points(),
                "colorRGB": self.color_rgb(),
                "opacity": float(self.opacity),
                "contents": self.text or "",
            }
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Annotation":
        data = dict(data)
        # v4 Interop: rects/quadPoints → x,y,width,height falls fehlend
        if "type" not in data and isinstance(data.get("pdf_highlight"), dict):
            ph = data["pdf_highlight"]
            subtype = str(ph.get("subtype") or "Highlight").lower()
            data["type"] = "highlight" if "under" not in subtype else "underline"
            if "text" not in data and "contents" in ph:
                data["text"] = ph.get("contents") or ""
            if "color" not in data and ph.get("colorRGB"):
                rgb = ph["colorRGB"]
                try:
                    data["color"] = "#{:02X}{:02X}{:02X}".format(
                        int(float(rgb[0]) * 255),
                        int(float(rgb[1]) * 255),
                        int(float(rgb[2]) * 255),
                    )
                except Exception:
                    pass
            if "opacity" not in data and "opacity" in ph:
                data["opacity"] = ph["opacity"]
            rects = ph.get("rects") or data.get("rects")
            if rects and isinstance(rects, list) and rects and "x" not in data:
                r0 = rects[0]
                if isinstance(r0, (list, tuple)) and len(r0) >= 4:
                    data["x"], data["y"], data["width"], data["height"] = (
                        float(r0[0]),
                        float(r0[1]),
                        float(r0[2]),
                        float(r0[3]),
                    )
        if "x" not in data and isinstance(data.get("rects"), list) and data["rects"]:
            r0 = data["rects"][0]
            if isinstance(r0, (list, tuple)) and len(r0) >= 4:
                data["x"], data["y"], data["width"], data["height"] = (
                    float(r0[0]),
                    float(r0[1]),
                    float(r0[2]),
                    float(r0[3]),
                )
        data["type"] = AnnotationType(data["type"])
        data.setdefault("callout_x", 0.0)
        data.setdefault("callout_y", 0.0)
        data.setdefault("font_size", 12.0)
        try:
            op = float(data.get("opacity", 1.0))
        except (TypeError, ValueError):
            op = 1.0
        data["opacity"] = max(0.05, min(1.0, op))
        try:
            rot = float(data.get("rotation", 0.0) or 0.0)
        except (TypeError, ValueError):
            rot = 0.0
        # Einfache Stempel-Rotation: auf 0/90/180/270 normalisieren
        data["rotation"] = float(int(round(rot / 90.0)) % 4 * 90)
        data["tags"] = normalize_tags(data.get("tags"))
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

    def duplicate(
        self,
        ann_id: str,
        *,
        dx: float = 12.0,
        dy: float = 12.0,
        page: int | None = None,
    ) -> Optional[Annotation]:
        """
        Auswahl duplizieren: Kopie mit neuer ID, leicht versetzt (inkl. Callout-Endpunkt).
        page: Zielseite (None = gleiche Seite wie Quelle).
        """
        src = self.get(ann_id)
        if src is None:
            return None
        data = src.to_dict()
        data.pop("id", None)
        data.pop("created", None)
        data.pop("modified", None)
        if page is not None:
            data["page"] = int(page)
        data["x"] = float(data.get("x", 0.0)) + float(dx)
        data["y"] = float(data.get("y", 0.0)) + float(dy)
        cx = float(data.get("callout_x", 0.0) or 0.0)
        cy = float(data.get("callout_y", 0.0) or 0.0)
        if cx or cy:
            data["callout_x"] = cx + float(dx)
            data["callout_y"] = cy + float(dy)
        return self.add(Annotation.from_dict(data))

    def paste_dicts(
        self,
        payloads: Sequence[dict],
        *,
        page: int,
        dx: float = 8.0,
        dy: float = 8.0,
    ) -> List[Annotation]:
        """
        Annotation-Dicts (Clipboard) auf Zielseite einfügen — neue IDs, optional versetzt.
        """
        created: List[Annotation] = []
        if not payloads:
            return created
        self._push_undo()
        recording = self._recording
        self._recording = False
        try:
            for raw in payloads:
                data = dict(raw)
                data.pop("id", None)
                data.pop("created", None)
                data.pop("modified", None)
                data["page"] = int(page)
                data["x"] = float(data.get("x", 0.0)) + float(dx)
                data["y"] = float(data.get("y", 0.0)) + float(dy)
                cx = float(data.get("callout_x", 0.0) or 0.0)
                cy = float(data.get("callout_y", 0.0) or 0.0)
                if cx or cy:
                    data["callout_x"] = cx + float(dx)
                    data["callout_y"] = cy + float(dy)
                ann = Annotation.from_dict(data)
                self.annotations.append(ann)
                created.append(ann)
            if created:
                self.dirty = True
        finally:
            self._recording = recording
        return created

    def get(self, ann_id: str) -> Optional[Annotation]:
        for a in self.annotations:
            if a.id == ann_id:
                return a
        return None

    def move_by(self, ann_ids: Sequence[str], dx: float, dy: float) -> int:
        """
        Annotationen um dx/dy verschieben (eine Undo-Stufe).
        Callout-/Linien-Endpunkte wandern mit. Rückgabe: Anzahl bewegter Ann.
        """
        ids = {str(i) for i in ann_ids if i}
        if not ids or (abs(float(dx)) < 1e-9 and abs(float(dy)) < 1e-9):
            return 0
        targets = [a for a in self.annotations if a.id in ids]
        if not targets:
            return 0
        self._push_undo()
        for a in targets:
            a.x = float(a.x) + float(dx)
            a.y = float(a.y) + float(dy)
            if a.callout_x or a.callout_y:
                a.callout_x = float(a.callout_x) + float(dx)
                a.callout_y = float(a.callout_y) + float(dy)
            a.touch()
        self.dirty = True
        return len(targets)

    def update(self, ann_id: str, **kwargs) -> Optional[Annotation]:
        for a in self.annotations:
            if a.id == ann_id:
                self._push_undo()
                for k, v in kwargs.items():
                    if hasattr(a, k):
                        if k == "tags":
                            setattr(a, k, normalize_tags(v))
                        else:
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
        # Seitengruppen-Meta mit-remappen
        groups = dict(self._meta.get("page_groups") or {})
        if groups:
            new_groups: dict = {}
            for key, val in groups.items():
                try:
                    old_p = int(key)
                except (TypeError, ValueError):
                    continue
                if old_p in mapping:
                    new_groups[str(mapping[old_p])] = val
            self._meta["page_groups"] = new_groups
        self.dirty = True

    def get_page_group(self, page: int) -> dict:
        """Gruppen-Metadaten für eine Seite: {title, color} (fehlende Keys leer)."""
        groups = self._meta.get("page_groups") or {}
        raw = groups.get(str(int(page))) or groups.get(int(page)) or {}
        if not isinstance(raw, dict):
            return {"title": "", "color": ""}
        title = str(raw.get("title") or "").strip()
        color = str(raw.get("color") or "").strip()
        if color and not color.startswith("#"):
            color = "#" + color
        return {"title": title, "color": color.upper() if color else ""}

    def set_page_group(
        self,
        page: int,
        *,
        title: str | None = None,
        color: str | None = None,
    ) -> dict:
        """
        Annotation-Seitengruppe umbenennen und/oder farblich markieren.
        title/color=None → unverändert; leerer String → zurücksetzen.
        """
        groups = dict(self._meta.get("page_groups") or {})
        cur = dict(self.get_page_group(page))
        if title is not None:
            cur["title"] = str(title).strip()
        if color is not None:
            c = str(color).strip()
            if c and not c.startswith("#"):
                c = "#" + c
            cur["color"] = c.upper() if c else ""
        key = str(int(page))
        if not cur.get("title") and not cur.get("color"):
            groups.pop(key, None)
        else:
            groups[key] = {"title": cur.get("title") or "", "color": cur.get("color") or ""}
        self._meta["page_groups"] = groups
        self.dirty = True
        return self.get_page_group(page)

    def list_page_groups(self) -> dict[int, dict]:
        """Alle Seitengruppen als {page_index: {title, color}}."""
        groups = self._meta.get("page_groups") or {}
        out: dict[int, dict] = {}
        for key, val in groups.items():
            try:
                p = int(key)
            except (TypeError, ValueError):
                continue
            if isinstance(val, dict):
                title = str(val.get("title") or "").strip()
                color = str(val.get("color") or "").strip()
                if color and not color.startswith("#"):
                    color = "#" + color
                if title or color:
                    out[p] = {"title": title, "color": color.upper() if color else ""}
        return out

    def _payload(self, *, export: bool = False) -> dict:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        meta = dict(self._meta)
        meta.setdefault("y_origin", "top")  # Sidecar-Y: oben; PDF-Y: unten
        meta.setdefault("coord_space", "render_pixels")
        anns = [
            (a.to_export_dict() if export else a.to_dict()) for a in self.annotations
        ]
        return {
            "version": SIDECAR_VERSION,
            "schema": SCHEMA_ID,
            "pdf": str(self.pdf_path) if self.pdf_path else None,
            "saved_at": now,
            "count": len(self.annotations),
            "meta": meta,
            "annotations": anns,
        }

    def save(self, path: Optional[Path] = None, force: bool = False) -> Path:
        target = path or self.sidecar_path
        if not force and not self.dirty and target.exists() and path is None:
            return target
        # Sidecar speichert Kernfelder; Export ergänzt Highlight-Interop
        payload = self._payload(export=False)
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
        """
        Annotationen als JSON Schema v4 exportieren (PDF-Highlight-kompatibel).
        Highlights/Underlines enthalten rects, quadPoints, colorRGB, pdf_highlight.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = self._payload(export=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    CSV_FIELDS = (
        "id",
        "page",
        "type",
        "x",
        "y",
        "width",
        "height",
        "text",
        "color",
        "callout_x",
        "callout_y",
        "font_size",
        "opacity",
        "tags",
        "created",
        "modified",
    )

    def export_csv(self, path: str | Path) -> Path:
        """Annotationen als flache CSV (eine Zeile pro Annotation)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(self.CSV_FIELDS), extrasaction="ignore")
            writer.writeheader()
            for ann in self.annotations:
                row = ann.to_dict()
                row["tags"] = tags_to_str(row.get("tags"))
                writer.writerow({k: row.get(k, "") for k in self.CSV_FIELDS})
        return path

    def build_report(
        self,
        *,
        fmt: str = "md",
        title: str | None = None,
        source: str | Path | None = None,
    ) -> str:
        """
        Zusammenhängender Kommentar-/Annotationsbericht (TXT oder Markdown).
        Gruppiert nach Seite, nummeriert, mit Typ/Text/Tags/Zeit.
        """
        fmt_l = (fmt or "md").strip().lower()
        if fmt_l in ("markdown", "mdown", "mkd"):
            fmt_l = "md"
        if fmt_l not in ("md", "txt"):
            fmt_l = "md"
        src_name = ""
        if source is not None:
            src_name = Path(source).name
        elif self.pdf_path is not None:
            src_name = Path(self.pdf_path).name
        heading = (title or "").strip() or (
            f"Annotationsbericht — {src_name}" if src_name else "Annotationsbericht"
        )
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        anns = sorted(
            list(self.annotations),
            key=lambda a: (int(a.page), float(a.y), float(a.x), a.created or "", a.id),
        )
        lines: list[str] = []
        if fmt_l == "md":
            lines.append(f"# {heading}")
            lines.append("")
            meta_bits = [f"**Erstellt:** {now}", f"**Anzahl:** {len(anns)}"]
            if src_name:
                meta_bits.insert(0, f"**Quelle:** `{src_name}`")
            lines.append(" · ".join(meta_bits))
            lines.append("")
        else:
            lines.append(heading)
            lines.append("=" * max(8, len(heading)))
            if src_name:
                lines.append(f"Quelle: {src_name}")
            lines.append(f"Erstellt: {now}")
            lines.append(f"Anzahl: {len(anns)}")
            lines.append("")

        if not anns:
            lines.append("Keine Annotationen vorhanden." if fmt_l == "txt" else "*Keine Annotationen vorhanden.*")
            lines.append("")
            return "\n".join(lines).rstrip() + "\n"

        by_page: dict[int, list[Annotation]] = {}
        for ann in anns:
            by_page.setdefault(int(ann.page), []).append(ann)

        global_idx = 0
        for page in sorted(by_page.keys()):
            page_anns = by_page[page]
            page_label = page + 1  # 1-basiert für Menschen
            if fmt_l == "md":
                lines.append(f"## Seite {page_label}")
                lines.append("")
            else:
                lines.append(f"Seite {page_label}")
                lines.append("-" * (7 + len(str(page_label))))
            for ann in page_anns:
                global_idx += 1
                t = ann.type.value if isinstance(ann.type, AnnotationType) else str(ann.type)
                type_de = REPORT_TYPE_LABELS.get(t, t)
                text = (ann.text or "").strip()
                tags = tags_to_str(ann.tags)
                created = (ann.created or "").strip()
                if fmt_l == "md":
                    head = f"{global_idx}. **{type_de}**"
                    if text:
                        # Einzeiler oder Block
                        if "\n" in text:
                            lines.append(f"{head}")
                            lines.append("")
                            for tl in text.splitlines():
                                lines.append(f"   > {tl}")
                            lines.append("")
                        else:
                            lines.append(f"{head} — {text}")
                    else:
                        lines.append(f"{head}")
                    extras: list[str] = []
                    if tags:
                        extras.append(f"Tags: `{tags}`")
                    if created:
                        extras.append(f"Zeit: {created}")
                    if ann.color:
                        extras.append(f"Farbe: `{ann.color}`")
                    if extras:
                        lines.append(f"   - {' · '.join(extras)}")
                    lines.append("")
                else:
                    head = f"{global_idx}. [{type_de}]"
                    if text:
                        if "\n" in text:
                            lines.append(head)
                            for tl in text.splitlines():
                                lines.append(f"   | {tl}")
                        else:
                            lines.append(f"{head} {text}")
                    else:
                        lines.append(head)
                    extras_t: list[str] = []
                    if tags:
                        extras_t.append(f"Tags: {tags}")
                    if created:
                        extras_t.append(f"Zeit: {created}")
                    if ann.color:
                        extras_t.append(f"Farbe: {ann.color}")
                    if extras_t:
                        lines.append(f"   ({' · '.join(extras_t)})")
                    lines.append("")
            if fmt_l == "txt":
                lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def export_report(
        self,
        path: str | Path,
        *,
        fmt: str | None = None,
        title: str | None = None,
        source: str | Path | None = None,
    ) -> Path:
        """Kommentar-Bericht als TXT oder Markdown speichern."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        suffix = path.suffix.lower()
        use_fmt = (fmt or "").strip().lower()
        if not use_fmt:
            use_fmt = "txt" if suffix == ".txt" else "md"
        if use_fmt in ("markdown", "mdown", "mkd"):
            use_fmt = "md"
        if use_fmt not in ("md", "txt"):
            use_fmt = "md"
        if use_fmt == "txt" and suffix != ".txt":
            path = path.with_suffix(".txt")
        elif use_fmt == "md" and suffix not in (".md", ".markdown"):
            path = path.with_suffix(".md")
        text = self.build_report(fmt=use_fmt, title=title, source=source)
        path.write_text(text, encoding="utf-8")
        return path

    def import_json(self, path: str | Path, *, replace: bool = True) -> int:
        """
        Annotationen aus JSON importieren.
        replace=True: ersetzen; False: anhängen (neue IDs behalten, Duplikate möglich).
        Rückgabe: Anzahl importierter Annotationen.
        """
        path = Path(path)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise AnnotationImportError(f"Kein gültiges JSON: {e}") from e
        data = validate_annotation_import_data(raw)
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
