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
# Seiten-Favoriten Export/Import (eigenes JSON, unabhängig vom Sidecar)
FAV_SCHEMA_ID = "ildfav-v1"
FAV_VERSION = 1


class FavoritesImportError(ValueError):
    """Ungültiges Favoriten-JSON (Schema/Version/Felder)."""


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
    stroke_width: float = 2.0  # Strichstärke Shapes 1–12 px (0.9.2)
    fill_color: str = ""  # Füllfarbe Shapes (#RRGGBB); leer = aus color abgeleitet (0.9.3)
    rotation: float = 0.0  # Stempel-Drehung in Grad (0/90/180/270)
    tags: List[str] = field(default_factory=list)  # freie Labels, filterbar
    group_id: str = ""  # temporäre Gruppen-ID (Sidecar; leer = ungruppiert)
    locked: bool = False  # Gruppen-/Ann.-Sperre: nicht verschiebbar
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
        # Opacity immer explizit und geklemmt persistieren (Sidecar-Robustheit)
        try:
            op = float(d.get("opacity", 1.0))
        except (TypeError, ValueError):
            op = 1.0
        d["opacity"] = round(max(0.05, min(1.0, op)), 4)
        try:
            sw = float(d.get("stroke_width", 2.0))
        except (TypeError, ValueError):
            sw = 2.0
        d["stroke_width"] = round(max(1.0, min(12.0, sw)), 2)
        fc = str(d.get("fill_color") or "").strip()
        if fc and not fc.startswith("#"):
            fc = "#" + fc
        d["fill_color"] = fc.upper() if fc else ""
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
            sw = float(data.get("stroke_width", 2.0) or 2.0)
        except (TypeError, ValueError):
            sw = 2.0
        data["stroke_width"] = max(1.0, min(12.0, sw))
        fc = str(data.get("fill_color") or "").strip()
        if fc and not fc.startswith("#"):
            fc = "#" + fc
        data["fill_color"] = fc.upper() if fc else ""
        try:
            rot = float(data.get("rotation", 0.0) or 0.0)
        except (TypeError, ValueError):
            rot = 0.0
        # Einfache Stempel-Rotation: auf 0/90/180/270 normalisieren
        data["rotation"] = float(int(round(rot / 90.0)) % 4 * 90)
        data["tags"] = normalize_tags(data.get("tags"))
        gid = data.get("group_id")
        if gid is None:
            data["group_id"] = ""
        else:
            data["group_id"] = str(gid).strip()
        data["locked"] = bool(data.get("locked", False))
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
        self._undo_labels: List[str] = []
        self._redo_labels: List[str] = []
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
        self._undo_labels.clear()
        self._redo_labels.clear()

    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    def peek_undo_label(self) -> str | None:
        """Label der nächsten Undo-Stufe (z. B. „Tag umbenennen“), oder None."""
        if not self._undo:
            return None
        if self._undo_labels:
            return str(self._undo_labels[-1] or "Annotation")
        return "Annotation"

    def undo_history_items(self) -> List[dict]:
        """
        Lesbare Annotation-Undo-Historie (älteste zuerst).
        Jeder Eintrag: stack_index, label, kind=\"annotation\".
        """
        items: List[dict] = []
        n = len(self._undo)
        for i in range(n):
            if i < len(self._undo_labels):
                label = str(self._undo_labels[i] or "Annotation")
            else:
                label = "Annotation"
            items.append(
                {
                    "stack_index": i,
                    "label": label,
                    "kind": "annotation",
                }
            )
        return items

    def _snapshot(self) -> List[dict]:
        return [a.to_dict() for a in self.annotations]

    def _restore(self, snap: List[dict]) -> None:
        self.annotations = [Annotation.from_dict(a) for a in snap]
        self.dirty = True

    def _push_undo(self, label: str = "Annotation") -> None:
        if not self._recording:
            return
        self._undo.append(self._snapshot())
        self._undo_labels.append(str(label or "Annotation"))
        if len(self._undo) > HISTORY_LIMIT:
            self._undo.pop(0)
            if self._undo_labels:
                self._undo_labels.pop(0)
        self._redo.clear()
        self._redo_labels.clear()

    @contextmanager
    def atomic(self, label: str = "Annotation") -> Iterator[None]:
        """Mehrere Mutationen als eine Undo-Stufe (optional benannt)."""
        self._push_undo(label)
        prev = self._recording
        self._recording = False
        try:
            yield
        finally:
            self._recording = prev

    def undo(self) -> bool:
        if not self._undo:
            return False
        label = self._undo_labels.pop() if self._undo_labels else "Annotation"
        self._redo.append(self._snapshot())
        self._redo_labels.append(label)
        self._restore(self._undo.pop())
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        label = self._redo_labels.pop() if self._redo_labels else "Annotation"
        self._undo.append(self._snapshot())
        self._undo_labels.append(label)
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
        targets = [
            a
            for a in self.annotations
            if a.id in ids and not bool(getattr(a, "locked", False))
        ]
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

    def _apply_dx(self, ann: Annotation, dx: float) -> None:
        """Horizontale Verschiebung inkl. Callout-Endpunkt (ohne Undo)."""
        if abs(float(dx)) < 1e-9:
            return
        ann.x = float(ann.x) + float(dx)
        if ann.callout_x or ann.callout_y:
            ann.callout_x = float(ann.callout_x) + float(dx)
        ann.touch()

    def _apply_dy(self, ann: Annotation, dy: float) -> None:
        """Vertikale Verschiebung inkl. Callout-Endpunkt (ohne Undo)."""
        if abs(float(dy)) < 1e-9:
            return
        ann.y = float(ann.y) + float(dy)
        if ann.callout_x or ann.callout_y:
            ann.callout_y = float(ann.callout_y) + float(dy)
        ann.touch()

    def align(
        self,
        ann_ids: Sequence[str],
        *,
        horizontal: str | None = None,
        vertical: str | None = None,
    ) -> int:
        """
        Auswahl ausrichten (eine Undo-Stufe).
        horizontal: left | center | right
        vertical: top | middle | bottom
        Mindestens eine Achse; Standard horizontal=left wenn nichts gesetzt.
        Rückgabe: Anzahl bewegter Annotationen.
        """
        h_mode = None
        v_mode = None
        if horizontal is not None:
            h_mode = str(horizontal or "left").strip().lower()
            if h_mode not in ("left", "center", "right"):
                h_mode = "left"
        if vertical is not None:
            v_mode = str(vertical or "top").strip().lower()
            if v_mode not in ("top", "middle", "bottom"):
                v_mode = "top"
        if h_mode is None and v_mode is None:
            h_mode = "left"
        ids = {str(i) for i in ann_ids if i}
        if len(ids) < 2:
            return 0
        targets = [a for a in self.annotations if a.id in ids]
        if len(targets) < 2:
            return 0
        moves_x: list[tuple[Annotation, float]] = []
        moves_y: list[tuple[Annotation, float]] = []
        if h_mode is not None:
            if h_mode == "left":
                anchor_x = min(float(a.x) for a in targets)
            elif h_mode == "right":
                anchor_x = max(float(a.x) + float(a.width or 0.0) for a in targets)
            else:
                left = min(float(a.x) for a in targets)
                right = max(float(a.x) + float(a.width or 0.0) for a in targets)
                anchor_x = (left + right) / 2.0
            for a in targets:
                w = float(a.width or 0.0)
                if h_mode == "left":
                    dx = anchor_x - float(a.x)
                elif h_mode == "right":
                    dx = anchor_x - (float(a.x) + w)
                else:
                    dx = anchor_x - (float(a.x) + w / 2.0)
                if abs(dx) >= 1e-9:
                    moves_x.append((a, dx))
        if v_mode is not None:
            if v_mode == "top":
                anchor_y = min(float(a.y) for a in targets)
            elif v_mode == "bottom":
                anchor_y = max(float(a.y) + float(a.height or 0.0) for a in targets)
            else:
                top = min(float(a.y) for a in targets)
                bottom = max(float(a.y) + float(a.height or 0.0) for a in targets)
                anchor_y = (top + bottom) / 2.0
            for a in targets:
                h = float(a.height or 0.0)
                if v_mode == "top":
                    dy = anchor_y - float(a.y)
                elif v_mode == "bottom":
                    dy = anchor_y - (float(a.y) + h)
                else:
                    dy = anchor_y - (float(a.y) + h / 2.0)
                if abs(dy) >= 1e-9:
                    moves_y.append((a, dy))
        if not moves_x and not moves_y:
            return 0
        self._push_undo()
        moved_ids: set[str] = set()
        for a, dx in moves_x:
            self._apply_dx(a, dx)
            moved_ids.add(a.id)
        for a, dy in moves_y:
            self._apply_dy(a, dy)
            moved_ids.add(a.id)
        self.dirty = True
        return len(moved_ids)

    def distribute_horizontal(self, ann_ids: Sequence[str]) -> int:
        """
        Auswahl horizontal gleichmäßig verteilen (linke/rechte Kante bleibt).
        Mindestens 3 Annotationen; eine Undo-Stufe. Rückgabe: bewegte Anzahl.
        """
        ids = {str(i) for i in ann_ids if i}
        if len(ids) < 3:
            return 0
        targets = [a for a in self.annotations if a.id in ids]
        if len(targets) < 3:
            return 0
        ordered = sorted(targets, key=lambda a: float(a.x))
        first = ordered[0]
        last = ordered[-1]
        span = float(last.x) - float(first.x)
        if abs(span) < 1e-9:
            return 0
        step = span / float(len(ordered) - 1)
        moves: list[tuple[Annotation, float]] = []
        for i, a in enumerate(ordered):
            if i == 0 or i == len(ordered) - 1:
                continue
            target_x = float(first.x) + step * float(i)
            dx = target_x - float(a.x)
            if abs(dx) >= 1e-9:
                moves.append((a, dx))
        if not moves:
            return 0
        self._push_undo()
        for a, dx in moves:
            self._apply_dx(a, dx)
        self.dirty = True
        return len(moves)

    def distribute_vertical(self, ann_ids: Sequence[str]) -> int:
        """
        Auswahl vertikal gleichmäßig verteilen (obere/untere Kante bleibt).
        Mindestens 3 Annotationen; eine Undo-Stufe. Rückgabe: bewegte Anzahl.
        """
        ids = {str(i) for i in ann_ids if i}
        if len(ids) < 3:
            return 0
        targets = [a for a in self.annotations if a.id in ids]
        if len(targets) < 3:
            return 0
        ordered = sorted(targets, key=lambda a: float(a.y))
        first = ordered[0]
        last = ordered[-1]
        span = float(last.y) - float(first.y)
        if abs(span) < 1e-9:
            return 0
        step = span / float(len(ordered) - 1)
        moves: list[tuple[Annotation, float]] = []
        for i, a in enumerate(ordered):
            if i == 0 or i == len(ordered) - 1:
                continue
            target_y = float(first.y) + step * float(i)
            dy = target_y - float(a.y)
            if abs(dy) >= 1e-9:
                moves.append((a, dy))
        if not moves:
            return 0
        self._push_undo()
        for a, dy in moves:
            self._apply_dy(a, dy)
        self.dirty = True
        return len(moves)

    def group(self, ann_ids: Sequence[str], group_id: str | None = None) -> tuple[int, str]:
        """
        Auswahl gruppieren: gemeinsame temporäre group_id im Sidecar (≥2).
        Eine Undo-Stufe. Rückgabe: (Anzahl, group_id) — (0, \"\") bei Abbruch.
        """
        ids = {str(i) for i in ann_ids if i}
        if len(ids) < 2:
            return 0, ""
        targets = [a for a in self.annotations if a.id in ids]
        if len(targets) < 2:
            return 0, ""
        gid = str(group_id or "").strip() or uuid4().hex[:12]
        self._push_undo()
        for a in targets:
            a.group_id = gid
            a.touch()
        # Meta-Eintrag anlegen, falls noch keiner existiert
        groups = dict(self._meta.get("ann_groups") or {})
        if gid not in groups:
            groups[gid] = {"title": "", "color": ""}
            self._meta["ann_groups"] = groups
        self.dirty = True
        return len(targets), gid

    def ungroup(self, ann_ids: Sequence[str]) -> int:
        """
        Auswahl entgruppieren: group_id leeren.
        Ohne IDs: alle Annotationen mit group_id. Eine Undo-Stufe.
        Rückgabe: Anzahl geänderter Annotationen.
        """
        ids = {str(i) for i in ann_ids if i}
        if ids:
            targets = [
                a for a in self.annotations if a.id in ids and str(a.group_id or "").strip()
            ]
        else:
            targets = [a for a in self.annotations if str(a.group_id or "").strip()]
        if not targets:
            return 0
        affected = {str(a.group_id or "").strip() for a in targets if str(a.group_id or "").strip()}
        self._push_undo()
        for a in targets:
            a.group_id = ""
            a.touch()
        self._prune_ann_groups(keep_check=affected)
        self.dirty = True
        return len(targets)

    def ids_in_group(self, group_id: str) -> list[str]:
        """Alle Annotation-IDs mit der gegebenen group_id (Reihenfolge wie im Store)."""
        gid = str(group_id or "").strip()
        if not gid:
            return []
        return [
            a.id
            for a in self.annotations
            if str(getattr(a, "group_id", "") or "").strip() == gid
        ]

    def expand_group_ids(self, ann_ids: Sequence[str]) -> list[str]:
        """Auswahl um alle Gruppenmitglieder erweitern (ohne Duplikate)."""
        out: list[str] = []
        seen: set[str] = set()
        for raw in ann_ids or []:
            aid = str(raw or "").strip()
            if not aid or aid in seen:
                continue
            ann = self.get(aid)
            gid = str(getattr(ann, "group_id", "") or "").strip() if ann else ""
            if gid:
                for mid in self.ids_in_group(gid):
                    if mid not in seen:
                        seen.add(mid)
                        out.append(mid)
            else:
                seen.add(aid)
                out.append(aid)
        return out

    def set_locked(self, ann_ids: Sequence[str], locked: bool) -> int:
        """locked-Flag für Auswahl setzen. Eine Undo-Stufe. Rückgabe: Anzahl."""
        ids = {str(i) for i in ann_ids if i}
        if not ids:
            return 0
        flag = bool(locked)
        targets = [
            a
            for a in self.annotations
            if a.id in ids and bool(getattr(a, "locked", False)) != flag
        ]
        if not targets:
            return 0
        self._push_undo()
        for a in targets:
            a.locked = flag
            a.touch()
        self.dirty = True
        return len(targets)

    def toggle_group_lock(self, ann_ids: Sequence[str]) -> tuple[int, bool]:
        """
        Gruppen-Sperre umschalten: alle Mitglieder der Gruppen in der Auswahl.
        Ohne group_id: locked nur für die genannten IDs.
        Rückgabe: (Anzahl, neuer locked-Zustand).
        """
        expanded = self.expand_group_ids(ann_ids)
        if not expanded:
            return 0, False
        anns = [self.get(i) for i in expanded]
        anns = [a for a in anns if a is not None]
        if not anns:
            return 0, False
        # Wenn mind. eine entsperrt → alle sperren; sonst alle entsperren
        new_locked = not all(bool(getattr(a, "locked", False)) for a in anns)
        n = self.set_locked(expanded, new_locked)
        return n, new_locked

    @staticmethod
    def _normalize_opacity(value: object) -> float:
        try:
            op = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            op = 1.0
        return round(max(0.05, min(1.0, op)), 4)

    def update(self, ann_id: str, **kwargs) -> Optional[Annotation]:
        for a in self.annotations:
            if a.id == ann_id:
                self._push_undo()
                for k, v in kwargs.items():
                    if hasattr(a, k):
                        if k == "tags":
                            setattr(a, k, normalize_tags(v))
                        elif k == "opacity":
                            setattr(a, k, self._normalize_opacity(v))
                        elif k == "stroke_width":
                            setattr(a, k, self._normalize_stroke_width(v))
                        elif k == "fill_color":
                            setattr(a, k, self._normalize_fill_color(v))
                        else:
                            setattr(a, k, v)
                a.touch()
                self.dirty = True
                return a
        return None

    def update_many(self, ann_ids: Sequence[str], **kwargs) -> int:
        """
        Mehrere Annotationen in einer Undo-Stufe aktualisieren (z. B. Batch-Farbe).
        Rückgabe: Anzahl geänderter Annotationen.
        """
        ids = {str(i) for i in ann_ids if i}
        if not ids or not kwargs:
            return 0
        targets = [a for a in self.annotations if a.id in ids]
        if not targets:
            return 0
        self._push_undo()
        for a in targets:
            for k, v in kwargs.items():
                if hasattr(a, k):
                    if k == "tags":
                        setattr(a, k, normalize_tags(v))
                    elif k == "opacity":
                        setattr(a, k, self._normalize_opacity(v))
                    elif k == "stroke_width":
                        setattr(a, k, self._normalize_stroke_width(v))
                    elif k == "fill_color":
                        setattr(a, k, self._normalize_fill_color(v))
                    else:
                        setattr(a, k, v)
            a.touch()
        self.dirty = True
        return len(targets)

    def count_tag(self, tag: str) -> int:
        """Anzahl Annotationen mit diesem Tag (case-insensitive)."""
        needle = str(tag or "").strip()
        if not needle:
            return 0
        cf = needle.casefold()
        return sum(
            1
            for a in self.annotations
            if any(str(t).casefold() == cf for t in (getattr(a, "tags", None) or []))
        )

    def rename_tag(self, old_tag: str, new_tag: str) -> int:
        """
        Tag global in allen Annotationen umbenennen (case-insensitive Match).
        Eine Undo-Stufe für alle betroffenen Annotationen (Ctrl+Z stellt alles zurück).
        Rückgabe: Anzahl geänderter Annotationen.
        """
        old = str(old_tag or "").strip()
        new_raw = str(new_tag or "").strip()
        if not old or not new_raw:
            return 0
        new_list = normalize_tags(new_raw)
        if not new_list:
            return 0
        new_s = new_list[0]
        old_cf = old.casefold()
        targets = [
            a
            for a in self.annotations
            if any(str(t).casefold() == old_cf for t in (getattr(a, "tags", None) or []))
        ]
        if not targets:
            return 0
        with self.atomic("Tag umbenennen"):
            for a in targets:
                seen: set[str] = set()
                nxt: list[str] = []
                for t in a.tags or []:
                    s = new_s if str(t).casefold() == old_cf else str(t)
                    key = s.casefold()
                    if key in seen:
                        continue
                    seen.add(key)
                    nxt.append(s)
                a.tags = nxt
                a.touch()
            self.dirty = True
        return len(targets)

    def set_colors(self, ann_ids: Sequence[str], color: str) -> int:
        """Batch-Farbe für Auswahl setzen (#RRGGBB)."""
        c = str(color or "").strip()
        if not c:
            return 0
        if not c.startswith("#"):
            c = "#" + c
        c = c.upper()
        return self.update_many(ann_ids, color=c)

    def set_opacities(self, ann_ids: Sequence[str], opacity: float) -> int:
        """Batch-Deckkraft für Auswahl setzen (0.05–1.0); Sidecar-Feld opacity."""
        op = self._normalize_opacity(opacity)
        return self.update_many(ann_ids, opacity=op)

    @staticmethod
    def _normalize_stroke_width(value: object) -> float:
        try:
            w = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            w = 2.0
        return round(max(1.0, min(12.0, w)), 2)

    def set_stroke_widths(self, ann_ids: Sequence[str], width: float) -> int:
        """Batch-Strichstärke für Auswahl setzen (1–12 px) — 0.9.2."""
        w = self._normalize_stroke_width(width)
        return self.update_many(ann_ids, stroke_width=w)

    @staticmethod
    def _normalize_fill_color(value: object) -> str:
        c = str(value or "").strip()
        if not c:
            return ""
        if not c.startswith("#"):
            c = "#" + c
        return c.upper()

    def set_fill_colors(self, ann_ids: Sequence[str], color: str) -> int:
        """Batch-Füllfarbe für Auswahl setzen (#RRGGBB oder leer) — 0.9.3."""
        c = self._normalize_fill_color(color)
        return self.update_many(ann_ids, fill_color=c)

    def save_opacities(self, ann_ids: Sequence[str], opacity: float) -> int:
        """
        Batch-Deckkraft setzen und Sidecar sofort force-schreiben.
        Rückgabe: Anzahl geänderter Annotationen (0 bei Fehler/keine Änderung).
        """
        n = self.set_opacities(ann_ids, opacity)
        if n <= 0:
            return 0
        self.save(force=True)
        return n

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

    @staticmethod
    def bbox_key(
        ann: Annotation,
        *,
        tol: float = 2.0,
        same_type: bool = True,
    ) -> tuple:
        """
        Signatur Seite+BBox (gerundet auf tol Pixel) — optional inkl. Typ.
        Gleiche Keys = Duplikat-Kandidaten.
        """
        t = max(0.5, float(tol))

        def _r(v: float) -> float:
            # Stabil quantisieren (kein Banker's Rounding von round())
            return math.floor(float(v) / t + 0.5) * t

        key = (
            int(ann.page),
            _r(ann.x),
            _r(ann.y),
            _r(ann.width),
            _r(ann.height),
        )
        if same_type:
            key = key + (ann.type.value,)  # type: ignore[assignment]
        return key

    def find_duplicate_groups(
        self,
        *,
        tol: float = 2.0,
        same_type: bool = True,
    ) -> List[List[Annotation]]:
        """
        Gruppen mit gleicher Seite+BBox (mind. 2 Annotationen).
        Paarweise: |Δx|,|Δy|,|Δw|,|Δh| ≤ tol (zuverlässiger als Raster-Buckets).
        """
        t = max(0.0, float(tol))
        anns = list(self.annotations)
        used: set[str] = set()
        groups: List[List[Annotation]] = []
        for i, a in enumerate(anns):
            if a.id in used:
                continue
            group = [a]
            for b in anns[i + 1 :]:
                if b.id in used:
                    continue
                if int(a.page) != int(b.page):
                    continue
                if same_type and a.type != b.type:
                    continue
                if (
                    abs(float(a.x) - float(b.x)) <= t
                    and abs(float(a.y) - float(b.y)) <= t
                    and abs(float(a.width) - float(b.width)) <= t
                    and abs(float(a.height) - float(b.height)) <= t
                ):
                    group.append(b)
            if len(group) >= 2:
                for g in group:
                    used.add(g.id)
                groups.append(group)
        return groups

    def merge_duplicates(
        self,
        *,
        tol: float = 2.0,
        same_type: bool = True,
        keep: str = "oldest",
        merge_text: bool = True,
        merge_tags: bool = True,
        groups: Optional[List[List[Annotation]]] = None,
    ) -> int:
        """
        Duplikate (gleiche Seite+BBox) optional zusammenführen.
        keep: oldest | newest | first — welche Annotation behalten wird.
        groups: optional nur diese Gruppen mergen (sonst alle gefundenen).
        Rückgabe: Anzahl entfernter Annotationen.
        """
        if groups is None:
            groups = self.find_duplicate_groups(tol=tol, same_type=same_type)
        else:
            groups = [list(g) for g in groups if g and len(g) >= 2]
        if not groups:
            return 0
        remove_ids: list[str] = []
        keep_updates: list[tuple[str, dict]] = []
        for group in groups:
            if keep == "newest":
                ordered = sorted(
                    group,
                    key=lambda a: (str(getattr(a, "modified", "") or ""), a.id),
                    reverse=True,
                )
            elif keep == "first":
                ordered = list(group)
            else:  # oldest
                ordered = sorted(
                    group,
                    key=lambda a: (str(getattr(a, "created", "") or ""), a.id),
                )
            keeper = ordered[0]
            drops = ordered[1:]
            updates: dict = {}
            if merge_tags:
                tags: list[str] = list(normalize_tags(getattr(keeper, "tags", None)))
                for d in drops:
                    tags.extend(normalize_tags(getattr(d, "tags", None)))
                merged_tags = normalize_tags(tags)
                if merged_tags != normalize_tags(getattr(keeper, "tags", None)):
                    updates["tags"] = merged_tags
            if merge_text:
                texts: list[str] = []
                for a in [keeper] + drops:
                    t = str(getattr(a, "text", "") or "").strip()
                    if t and t not in texts:
                        texts.append(t)
                if len(texts) > 1:
                    updates["text"] = " | ".join(texts)
                elif texts and texts[0] != str(getattr(keeper, "text", "") or "").strip():
                    updates["text"] = texts[0]
            if updates:
                keep_updates.append((keeper.id, updates))
            remove_ids.extend(d.id for d in drops)
        if not remove_ids and not keep_updates:
            return 0
        self._push_undo("Duplikate zusammenführen")
        recording = self._recording
        self._recording = False
        try:
            for kid, updates in keep_updates:
                a = self.get(kid)
                if a is None:
                    continue
                for k, v in updates.items():
                    if k == "tags":
                        a.tags = normalize_tags(v)
                    else:
                        setattr(a, k, v)
                a.touch()
            if remove_ids:
                drop = set(remove_ids)
                self.annotations = [a for a in self.annotations if a.id not in drop]
            self.dirty = True
        finally:
            self._recording = recording
        return len(remove_ids)

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
        anns_changed = changed or len(planned) != len(self.annotations)
        if anns_changed:
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
        # Seiten-Favoriten mit-remappen (Reihenfolge beibehalten)
        favs = list(self._meta.get("page_favorites") or [])
        if favs:
            remapped: list[int] = []
            seen: set[int] = set()
            for raw in favs:
                try:
                    old_p = int(raw)
                except (TypeError, ValueError):
                    continue
                if old_p not in mapping:
                    continue
                new_p = int(mapping[old_p])
                if new_p not in seen:
                    seen.add(new_p)
                    remapped.append(new_p)
            if remapped:
                self._meta["page_favorites"] = remapped
            else:
                self._meta.pop("page_favorites", None)
        if anns_changed or groups or favs:
            self.dirty = True

    def list_page_favorites(self) -> list[int]:
        """Favoriten-Seitenindizes (0-basiert, Reihenfolge wie gespeichert, dedupliziert)."""
        raw = self._meta.get("page_favorites") or []
        out: list[int] = []
        seen: set[int] = set()
        if not isinstance(raw, (list, tuple)):
            return out
        for item in raw:
            try:
                p = int(item)
            except (TypeError, ValueError):
                continue
            if p < 0 or p in seen:
                continue
            seen.add(p)
            out.append(p)
        return out

    def is_page_favorite(self, page: int) -> bool:
        return int(page) in self.list_page_favorites()

    def set_page_favorites(self, pages: Sequence[int]) -> list[int]:
        """Favoritenliste setzen (Reihenfolge beibehalten, dedupliziert); leere Liste löscht Meta."""
        cleaned: list[int] = []
        seen: set[int] = set()
        for item in pages or []:
            try:
                p = int(item)
            except (TypeError, ValueError):
                continue
            if p < 0 or p in seen:
                continue
            seen.add(p)
            cleaned.append(p)
        if cleaned:
            self._meta["page_favorites"] = cleaned
        else:
            self._meta.pop("page_favorites", None)
        self.dirty = True
        return cleaned

    def reorder_page_favorites(self, pages: Sequence[int]) -> list[int]:
        """Favoriten-Reihenfolge setzen (Drag in Sidebar); nur bekannte Seiten behalten."""
        return self.set_page_favorites(pages)

    def export_page_favorites_dict(self) -> dict:
        """Favoriten als exportierbares Dict (Schema ildfav-v1)."""
        src = ""
        try:
            if self.pdf_path is not None:
                src = Path(self.pdf_path).name
        except Exception:
            src = ""
        return {
            "version": FAV_VERSION,
            "schema": FAV_SCHEMA_ID,
            "page_favorites": self.list_page_favorites(),
            "source": src,
        }

    def export_page_favorites_json(self, path: str | Path) -> Path:
        """Seiten-Favoriten als JSON-Datei schreiben (ildfav-v1)."""
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        data = self.export_page_favorites_dict()
        dest.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return dest

    def import_page_favorites_dict(
        self,
        data: dict,
        *,
        merge: bool = False,
        max_page: int | None = None,
    ) -> list[int]:
        """
        Favoriten aus Dict übernehmen.
        merge=True: bestehende behalten und neue anhängen (Reihenfolge).
        max_page: optional obere Grenze (exklusiv) zum Filtern ungültiger Indizes.
        """
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
        if "page_favorites" not in data:
            raise FavoritesImportError("Feld „page_favorites“ fehlt.")
        raw = data.get("page_favorites")
        if not isinstance(raw, (list, tuple)):
            raise FavoritesImportError("„page_favorites“ muss eine Liste sein.")
        incoming: list[int] = []
        seen: set[int] = set()
        for item in raw:
            try:
                p = int(item)
            except (TypeError, ValueError):
                continue
            if p < 0 or p in seen:
                continue
            if max_page is not None and p >= int(max_page):
                continue
            seen.add(p)
            incoming.append(p)
        if merge:
            combined = self.list_page_favorites()
            for p in incoming:
                if p not in combined:
                    combined.append(p)
            return self.set_page_favorites(combined)
        return self.set_page_favorites(incoming)

    def import_page_favorites_json(
        self,
        path: str | Path,
        *,
        merge: bool = False,
        max_page: int | None = None,
    ) -> list[int]:
        """Favoriten aus JSON-Datei laden (ersetzt oder merge)."""
        src = Path(path)
        try:
            data = json.loads(src.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise FavoritesImportError(f"Ungültiges JSON: {e}") from e
        except OSError as e:
            raise FavoritesImportError(str(e)) from e
        return self.import_page_favorites_dict(data, merge=merge, max_page=max_page)

    def toggle_page_favorite(self, page: int) -> bool:
        """
        Seite als Favorit markieren/entfernen.
        Neue Favoriten werden am Ende angehängt (Drag-Reihenfolge bleibt).
        Rückgabe: True wenn danach Favorit, sonst False.
        """
        p = int(page)
        favs = self.list_page_favorites()
        if p in favs:
            favs = [x for x in favs if x != p]
            self.set_page_favorites(favs)
            return False
        favs.append(p)
        self.set_page_favorites(favs)
        return True

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

    def get_ann_group(self, group_id: str) -> dict:
        """Ann.-Gruppen-Metadaten: {title, color} für temporäre group_id."""
        gid = str(group_id or "").strip()
        if not gid:
            return {"title": "", "color": ""}
        groups = self._meta.get("ann_groups") or {}
        raw = groups.get(gid) or {}
        if not isinstance(raw, dict):
            return {"title": "", "color": ""}
        title = str(raw.get("title") or "").strip()
        color = str(raw.get("color") or "").strip()
        if color and not color.startswith("#"):
            color = "#" + color
        return {"title": title, "color": color.upper() if color else ""}

    def set_ann_group(
        self,
        group_id: str,
        *,
        title: str | None = None,
        color: str | None = None,
    ) -> dict:
        """
        Temporäre Ann.-Gruppe umbenennen und/oder farblich markieren (Sidecar-Meta).
        title/color=None → unverändert; leerer String → zurücksetzen.
        """
        gid = str(group_id or "").strip()
        if not gid:
            return {"title": "", "color": ""}
        groups = dict(self._meta.get("ann_groups") or {})
        cur = dict(self.get_ann_group(gid))
        if title is not None:
            cur["title"] = str(title).strip()
        if color is not None:
            c = str(color).strip()
            if c and not c.startswith("#"):
                c = "#" + c
            cur["color"] = c.upper() if c else ""
        if not cur.get("title") and not cur.get("color"):
            # Eintrag behalten wenn Mitglieder existieren (leere Meta ok)
            if self.ids_in_group(gid):
                groups[gid] = {"title": "", "color": ""}
            else:
                groups.pop(gid, None)
        else:
            groups[gid] = {"title": cur.get("title") or "", "color": cur.get("color") or ""}
        self._meta["ann_groups"] = groups
        self.dirty = True
        return self.get_ann_group(gid)

    def list_ann_groups(self) -> dict[str, dict]:
        """Alle Ann.-Gruppen mit Mitgliedern als {group_id: {title, color}}."""
        out: dict[str, dict] = {}
        # Zuerst Meta
        groups = self._meta.get("ann_groups") or {}
        if isinstance(groups, dict):
            for key, val in groups.items():
                gid = str(key or "").strip()
                if not gid or not isinstance(val, dict):
                    continue
                title = str(val.get("title") or "").strip()
                color = str(val.get("color") or "").strip()
                if color and not color.startswith("#"):
                    color = "#" + color
                out[gid] = {"title": title, "color": color.upper() if color else ""}
        # Gruppen mit Mitgliedern ohne Meta-Eintrag ergänzen
        for a in self.annotations:
            gid = str(getattr(a, "group_id", "") or "").strip()
            if gid and gid not in out:
                out[gid] = {"title": "", "color": ""}
        return out

    def _prune_ann_groups(self, keep_check: set[str] | None = None) -> None:
        """Verwaiste ann_groups-Meta-Einträge entfernen (keine Mitglieder mehr)."""
        groups = dict(self._meta.get("ann_groups") or {})
        if not groups:
            return
        live = {
            str(getattr(a, "group_id", "") or "").strip()
            for a in self.annotations
            if str(getattr(a, "group_id", "") or "").strip()
        }
        check = keep_check if keep_check is not None else set(groups.keys())
        changed = False
        for gid in list(check):
            if gid and gid not in live and gid in groups:
                groups.pop(gid, None)
                changed = True
        if changed:
            if groups:
                self._meta["ann_groups"] = groups
            else:
                self._meta.pop("ann_groups", None)

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

    def export_group_json(self, group_id: str, path: str | Path) -> Path:
        """
        Nur Mitglieder einer temporären Ann.-Gruppe als JSON Schema v4 exportieren.
        Meta enthält die Gruppenmarkierung unter ann_groups.
        """
        gid = str(group_id or "").strip()
        if not gid:
            raise ValueError("Keine Gruppen-ID")
        member_ids = set(self.ids_in_group(gid))
        if not member_ids:
            raise ValueError("Gruppe hat keine Mitglieder")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        full = self._payload(export=True)
        anns = [
            a
            for a in full.get("annotations") or []
            if isinstance(a, dict) and str(a.get("id") or "") in member_ids
        ]
        # Fallback: group_id-Feld falls id-Filter leer (export dicts)
        if not anns:
            anns = [
                a
                for a in full.get("annotations") or []
                if isinstance(a, dict)
                and str(a.get("group_id") or "").strip() == gid
            ]
        meta = dict(full.get("meta") or {})
        gmeta = self.get_ann_group(gid)
        meta["ann_groups"] = {gid: {"title": gmeta.get("title") or "", "color": gmeta.get("color") or ""}}
        payload = {
            "version": full.get("version"),
            "schema": full.get("schema"),
            "pdf": full.get("pdf"),
            "saved_at": full.get("saved_at"),
            "count": len(anns),
            "meta": meta,
            "annotations": anns,
            "export_group_id": gid,
        }
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
        "group_title",
        "group_color",
        "created",
        "modified",
    )

    def export_csv(self, path: str | Path) -> Path:
        """Annotationen als flache CSV inkl. Tags und Seitengruppen."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(self.CSV_FIELDS), extrasaction="ignore")
            writer.writeheader()
            for ann in self.annotations:
                row = ann.to_dict()
                row["tags"] = tags_to_str(row.get("tags"))
                grp = self.get_page_group(int(ann.page))
                row["group_title"] = grp.get("title") or ""
                row["group_color"] = grp.get("color") or ""
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
            grp = self.get_page_group(page)
            grp_title = (grp.get("title") or "").strip()
            grp_color = (grp.get("color") or "").strip()
            if fmt_l == "md":
                if grp_title:
                    lines.append(f"## Seite {page_label} — {grp_title}")
                else:
                    lines.append(f"## Seite {page_label}")
                lines.append("")
                if grp_title or grp_color:
                    gbits = []
                    if grp_title:
                        gbits.append(f"Gruppe: **{grp_title}**")
                    if grp_color:
                        gbits.append(f"Gruppenfarbe: `{grp_color}`")
                    lines.append(" · ".join(gbits))
                    lines.append("")
            else:
                if grp_title:
                    lines.append(f"Seite {page_label} — {grp_title}")
                else:
                    lines.append(f"Seite {page_label}")
                lines.append("-" * (7 + len(str(page_label)) + (3 + len(grp_title) if grp_title else 0)))
                if grp_title or grp_color:
                    gbits_t = []
                    if grp_title:
                        gbits_t.append(f"Gruppe: {grp_title}")
                    if grp_color:
                        gbits_t.append(f"Farbe: {grp_color}")
                    lines.append(" · ".join(gbits_t))
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
