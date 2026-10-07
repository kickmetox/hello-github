"""Abschnittsumbrüche — 2.6.28.

Abschnittsumbrüche mit gemischter Orientierung — Sidecar ``*.ildsections.json``.

Schema ``ildsections-v1``. Abschnitte steuern Seitenformat, Orientierung und Spalten
ab einer Startseite (0-basiert); Anwendung über ``set_page_size`` / Layout-Presets.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional, Sequence
from uuid import uuid4

from .page_layout import resolve_page_format
from .pages import PAGE_SIZE_PRESETS, page_count, set_page_size

SECTIONS_SCHEMA_ID = "ildsections-v1"
SECTIONS_VERSION = 1
SIDECAR_SUFFIX = ".ildsections.json"

Orientation = Literal["portrait", "landscape"]


class SectionError(ValueError):
    """Ungültiges Abschnitts-/Sidecar-JSON."""


@dataclass
class SectionBreak:
    """Abschnittsumbruch ab ``start_page`` (0-basiert)."""

    id: str = field(default_factory=lambda: uuid4().hex[:10])
    start_page: int = 0
    page_size: Optional[tuple[float, float]] = None  # (w, h) pt
    preset: Optional[str] = None  # z.B. "A4", "Letter"
    orientation: Orientation = "portrait"
    columns: int = 1

    def resolved_size(self) -> tuple[float, float]:
        """Effektive Seitengröße in pt (Orientierung angewendet)."""
        if self.page_size and len(self.page_size) == 2:
            w, h = float(self.page_size[0]), float(self.page_size[1])
        elif self.preset:
            w, h = resolve_page_format(self.preset)
        else:
            w, h = PAGE_SIZE_PRESETS.get("A4", (595.28, 841.89))
        if self.orientation == "landscape" and h > w:
            w, h = h, w
        elif self.orientation == "portrait" and w > h:
            w, h = h, w
        return float(w), float(h)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "start_page": int(self.start_page),
            "orientation": self.orientation,
            "columns": int(self.columns),
        }
        if self.preset:
            d["preset"] = self.preset
        if self.page_size:
            d["page_size"] = [float(self.page_size[0]), float(self.page_size[1])]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SectionBreak":
        if not isinstance(data, dict):
            raise SectionError("SectionBreak muss ein Objekt sein.")
        ori = str(data.get("orientation") or "portrait").lower()
        if ori not in ("portrait", "landscape"):
            ori = "portrait"
        ps = data.get("page_size")
        page_size: Optional[tuple[float, float]] = None
        if isinstance(ps, (list, tuple)) and len(ps) == 2:
            page_size = (float(ps[0]), float(ps[1]))
        cols = int(data.get("columns") or 1)
        if cols < 1:
            cols = 1
        if cols > 6:
            cols = 6
        return cls(
            id=str(data.get("id") or uuid4().hex[:10]),
            start_page=max(0, int(data.get("start_page") or 0)),
            page_size=page_size,
            preset=str(data["preset"]) if data.get("preset") else None,
            orientation=ori,  # type: ignore[arg-type]
            columns=cols,
        )


@dataclass
class SectionModel:
    """Sammlung von Abschnittsumbrüchen für ein Dokument."""

    sections: list[SectionBreak] = field(default_factory=list)
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": SECTIONS_VERSION,
            "schema": SECTIONS_SCHEMA_ID,
            "sections": [s.to_dict() for s in self.sections],
            "source": str(self.source or ""),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SectionModel":
        if not isinstance(data, dict):
            raise SectionError("Abschnitts-JSON muss ein Objekt sein.")
        ver = data.get("version")
        schema = data.get("schema")
        try:
            ver_i = int(ver)
        except (TypeError, ValueError):
            raise SectionError(
                f"Ungültige Version {ver!r} — erwartet {SECTIONS_VERSION} ({SECTIONS_SCHEMA_ID})."
            ) from None
        if ver_i != SECTIONS_VERSION:
            raise SectionError(
                f"Inkompatible Version {ver_i} — erwartet {SECTIONS_VERSION} ({SECTIONS_SCHEMA_ID})."
            )
        if schema is not None and str(schema) != SECTIONS_SCHEMA_ID:
            raise SectionError(
                f"Inkompatibles Schema „{schema}“ — erwartet „{SECTIONS_SCHEMA_ID}“."
            )
        secs = data.get("sections") or []
        if not isinstance(secs, list):
            raise SectionError("Feld „sections“ muss eine Liste sein.")
        return cls(
            sections=[SectionBreak.from_dict(s) for s in secs if isinstance(s, dict)],
            source=str(data.get("source") or ""),
        )

    def sorted_sections(self) -> list[SectionBreak]:
        return sorted(self.sections, key=lambda s: (s.start_page, s.id))


def sidecar_path_for(doc_path: str | Path) -> Path:
    """Sidecar neben dem Dokument: ``datei.pdf.ildsections.json``."""
    p = Path(doc_path)
    return p.with_suffix(p.suffix + ".ildsections.json")


def save_sections_sidecar(doc_path: str | Path, model: SectionModel) -> Path:
    path = sidecar_path_for(doc_path)
    model.source = str(Path(doc_path).name)
    path.write_text(
        json.dumps(model.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def load_sections_sidecar(doc_path: str | Path) -> SectionModel:
    path = sidecar_path_for(doc_path)
    if not path.is_file():
        return SectionModel(source=str(Path(doc_path).name))
    data = json.loads(path.read_text(encoding="utf-8"))
    return SectionModel.from_dict(data)


def add_section_break(
    model: SectionModel | None = None,
    *,
    start_page: int = 0,
    page_size: tuple[float, float] | None = None,
    preset: str | None = None,
    orientation: Orientation = "portrait",
    columns: int = 1,
    section_id: str | None = None,
) -> SectionModel:
    """Neuen Abschnittsumbruch anhängen (mutiert/erzeugt Model)."""
    m = model or SectionModel()
    ori: Orientation = orientation if orientation in ("portrait", "landscape") else "portrait"
    br = SectionBreak(
        id=section_id or uuid4().hex[:10],
        start_page=max(0, int(start_page)),
        page_size=page_size,
        preset=preset,
        orientation=ori,
        columns=max(1, min(6, int(columns))),
    )
    # Gleiche Startseite ersetzen
    m.sections = [s for s in m.sections if s.start_page != br.start_page]
    m.sections.append(br)
    m.sections = m.sorted_sections()
    return m


def list_sections(model: SectionModel | Sequence[SectionBreak] | None) -> list[dict[str, Any]]:
    """Abschnitte als Dict-Liste (sortiert)."""
    if model is None:
        return []
    if isinstance(model, SectionModel):
        secs = model.sorted_sections()
    else:
        secs = sorted(list(model), key=lambda s: (s.start_page, s.id))
    out: list[dict[str, Any]] = []
    for s in secs:
        d = s.to_dict()
        w, h = s.resolved_size()
        d["resolved_width_pt"] = w
        d["resolved_height_pt"] = h
        out.append(d)
    return out


def apply_section_page_sizes(
    pdf_path: str | Path,
    model: SectionModel | Sequence[SectionBreak],
    *,
    out_path: str | Path | None = None,
) -> Path:
    """
    Seitengrößen aus Abschnitten auf PDF anwenden.

    Jeder Break gilt ab ``start_page`` bis zum nächsten Break (exklusiv)
    bzw. bis Dokumentende. Nutzt ``set_page_size`` / Presets.
    """
    pdf_path = Path(pdf_path)
    dest = Path(out_path) if out_path else pdf_path
    if isinstance(model, SectionModel):
        secs = model.sorted_sections()
    else:
        secs = sorted(list(model), key=lambda s: s.start_page)
    if not secs:
        if dest.resolve() != pdf_path.resolve():
            dest.write_bytes(pdf_path.read_bytes())
        return dest

    n = page_count(pdf_path)
    # Kopie einmal, dann in-place auf dest
    if dest.resolve() != pdf_path.resolve():
        dest.write_bytes(pdf_path.read_bytes())
        work = dest
    else:
        work = pdf_path

    for i, sec in enumerate(secs):
        start = max(0, int(sec.start_page))
        if start >= n:
            continue
        end = n
        if i + 1 < len(secs):
            end = min(n, max(start + 1, int(secs[i + 1].start_page)))
        w, h = sec.resolved_size()
        for pi in range(start, end):
            set_page_size(work, pi, w, h, out_path=work)
    return work


def paginate_text_columns(
    text: str,
    *,
    columns: int = 2,
    page_height_chars: int = 40,
) -> list[list[str]]:
    """
    Einfache Word-ähnliche Spalten-/Seitenzählung für Plaintext.

    Zeilen werden zeilenweise auf ``columns`` Spalten verteilt; nach
    ``page_height_chars`` Zeilen pro Spalte beginnt eine neue Seite.
    Rückgabe: Liste von Seiten, jede Seite = Liste von Spaltentexten.
    """
    cols = max(1, min(6, int(columns)))
    height = max(1, int(page_height_chars))
    lines = (text or "").replace("\r\n", "\n").split("\n")
    if not lines:
        lines = [""]

    # Zeilen in Spalten-Buckets (round-robin über volle Spaltenhöhen)
    # Word-ähnlich: zuerst Spalte 1 füllen, dann Spalte 2, … dann neue Seite
    pages: list[list[str]] = []
    i = 0
    while i < len(lines):
        page_cols: list[list[str]] = [[] for _ in range(cols)]
        for c in range(cols):
            chunk = lines[i : i + height]
            i += len(chunk)
            page_cols[c] = chunk
            if i >= len(lines):
                break
        pages.append(["\n".join(col) for col in page_cols])
        if i >= len(lines):
            break
    return pages


def section_for_page(model: SectionModel, page_index: int) -> Optional[SectionBreak]:
    """Aktiven Abschnittsumbruch für 0-basierte Seite finden."""
    active: Optional[SectionBreak] = None
    for s in model.sorted_sections():
        if s.start_page <= page_index:
            active = s
        else:
            break
    return active
