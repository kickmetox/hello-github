"""Seitenlayout-Hilfen 2.6.12/2.6.13: Buchformate, Lineal/Raster, Satzspiegel, Musterseiten, HF.

Frames/Boxen + Textrahmen-Verkettung + Textumfluss liegen in ``instantlensdoc.core.layout``.
Typografie (Tracking/Kerning/Leading/Silbentrennung/Drop Caps): ``ild_pdf.typography``.
Farbmanagement/Bleed/Preflight/PDF/X: ``ild_pdf.print_prep`` (2.6.18).
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, List, Literal, Optional, Sequence, Tuple

from .pages import PAGE_SIZE_PRESETS, mm_to_pt, pt_to_mm

# Buch- und Zusatzformate (Hochformat, mm) — Spezifikation instantlensdoc-dtp.md
BOOK_FORMAT_MM: dict[str, Tuple[float, float]] = {
    "Taschenbuch": (125.0, 190.0),
    "DINA5": (148.0, 210.0),
    "Roman": (135.0, 215.0),
    "Sachbuch": (170.0, 240.0),
    "DINA4": (210.0, 297.0),
    "Quadrat": (210.0, 210.0),
}

# DIN-A + US + Buch — Anzeige-Namen (Werte in PDF-Punkten)
LAYOUT_PAGE_PRESETS: dict[str, Tuple[float, float]] = {
    "US Letter": PAGE_SIZE_PRESETS["Letter"],
    "US Legal": PAGE_SIZE_PRESETS["Legal"],
    "A3": PAGE_SIZE_PRESETS["A3"],
    "A4": PAGE_SIZE_PRESETS["A4"],
    "A5": PAGE_SIZE_PRESETS["A5"],
    "A6": (mm_to_pt(105.0), mm_to_pt(148.0)),
    "Taschenbuch": (mm_to_pt(125.0), mm_to_pt(190.0)),
    "DINA5": (mm_to_pt(148.0), mm_to_pt(210.0)),
    "Roman": (mm_to_pt(135.0), mm_to_pt(215.0)),
    "Sachbuch": (mm_to_pt(170.0), mm_to_pt(240.0)),
    "DINA4": PAGE_SIZE_PRESETS["A4"],
    "Quadrat": (mm_to_pt(210.0), mm_to_pt(210.0)),
}

AlignName = Literal["left", "center", "right", "justify"]
GuideOrientation = Literal["horizontal", "vertical"]

PARAGRAPH_ALIGNMENTS: tuple[str, ...] = ("left", "center", "right", "justify")
LINE_SPACINGS: tuple[float, ...] = (1.0, 1.15, 1.5, 2.0)

_ALIGN_MARKER_RE = re.compile(
    r"^<!--\s*ild-align:(left|center|right|justify)\s*-->\s*$", re.IGNORECASE
)
_SPACE_MARKER_RE = re.compile(
    r"^<!--\s*ild-spacing:ls=([0-9.]+);sb=([0-9.]+);sa=([0-9.]+)\s*-->\s*$",
    re.IGNORECASE,
)


@dataclass
class Guide:
    """Ausrichtungs-Hilfslinie in PDF-Punkten (Seite, Y von unten wie MediaBox bzw. Anzeige)."""

    orientation: GuideOrientation
    position_pt: float
    id: str = ""
    locked: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Guide":
        ori = str(data.get("orientation") or "horizontal").lower()
        if ori not in ("horizontal", "vertical"):
            ori = "horizontal"
        return cls(
            orientation=ori,  # type: ignore[arg-type]
            position_pt=float(data.get("position_pt") or 0.0),
            id=str(data.get("id") or ""),
            locked=bool(data.get("locked", False)),
        )


@dataclass
class GridSettings:
    """Raster-Einstellungen für Viewer-Overlay."""

    enabled: bool = False
    spacing_mm: float = 5.0
    subdivisions: int = 1
    color: str = "#4A90D9"
    opacity: float = 0.35
    snap: bool = False

    def spacing_pt(self) -> float:
        return mm_to_pt(max(1.0, float(self.spacing_mm)))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RulerSettings:
    """Lineal ein/aus + Einheit."""

    enabled: bool = False
    unit: str = "mm"  # mm | inch
    show_horizontal: bool = True
    show_vertical: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ParagraphFormat:
    """Absatzformat — an Style-Presets (2.6.10) angebunden."""

    alignment: AlignName = "left"
    line_spacing: float = 1.15
    space_before_pt: float = 0.0
    space_after_pt: float = 6.0
    first_line_indent_pt: float = 0.0
    style_id: str = "body"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_style_preset(cls, preset: dict[str, Any], style_id: str = "body") -> "ParagraphFormat":
        align = str(preset.get("alignment") or "left").lower()
        if align not in PARAGRAPH_ALIGNMENTS:
            align = "left"
        ls = float(preset.get("line_spacing") or 1.15)
        if ls not in LINE_SPACINGS:
            ls = min(LINE_SPACINGS, key=lambda x: abs(x - ls))
        return cls(
            alignment=align,  # type: ignore[arg-type]
            line_spacing=ls,
            space_before_pt=float(preset.get("space_before_pt") or 0.0),
            space_after_pt=float(preset.get("space_after_pt") or 6.0),
            first_line_indent_pt=float(preset.get("first_line_indent_pt") or 0.0),
            style_id=style_id or str(preset.get("id") or "body"),
        )


def ensure_layout_presets_in_page_sizes() -> None:
    """Buch-/DIN-Presets in PAGE_SIZE_PRESETS registrieren (idempotent)."""
    for name, (w, h) in LAYOUT_PAGE_PRESETS.items():
        # Kurzalias ohne Leerzeichen für Dialog/CLI
        key = name.replace(" ", "")
        if key not in PAGE_SIZE_PRESETS:
            PAGE_SIZE_PRESETS[key] = (float(w), float(h))
        # Lesbare Namen ebenfalls
        if name not in PAGE_SIZE_PRESETS:
            PAGE_SIZE_PRESETS[name] = (float(w), float(h))
    # Zusätzliche Aliase
    aliases = {
        "Letter": PAGE_SIZE_PRESETS["Letter"],
        "Taschenbuch": LAYOUT_PAGE_PRESETS["Taschenbuch"],
        "Roman": LAYOUT_PAGE_PRESETS["Roman"],
        "Sachbuch": LAYOUT_PAGE_PRESETS["Sachbuch"],
        "Quadrat": LAYOUT_PAGE_PRESETS["Quadrat"],
        "A6": LAYOUT_PAGE_PRESETS["A6"],
    }
    for k, v in aliases.items():
        PAGE_SIZE_PRESETS.setdefault(k, v)


ensure_layout_presets_in_page_sizes()


def list_page_format_presets(*, unit: str = "mm") -> list[dict[str, Any]]:
    """Alle Layout-Presets mit Maßen (mm oder inch)."""
    from .pages import format_size_pair

    out: list[dict[str, Any]] = []
    for name, (w, h) in LAYOUT_PAGE_PRESETS.items():
        out.append(
            {
                "name": name,
                "width_pt": float(w),
                "height_pt": float(h),
                "width_mm": round(pt_to_mm(w), 1),
                "height_mm": round(pt_to_mm(h), 1),
                "label": f"{name} ({format_size_pair(w, h, unit)})",
                "category": (
                    "book"
                    if name
                    in ("Taschenbuch", "DINA5", "Roman", "Sachbuch", "DINA4", "Quadrat")
                    else "standard"
                ),
            }
        )
    return out


def resolve_page_format(name: str) -> Tuple[float, float]:
    """Preset-Name → (width_pt, height_pt)."""
    key = (name or "").strip()
    if not key:
        return PAGE_SIZE_PRESETS["A4"]
    if key in PAGE_SIZE_PRESETS:
        return PAGE_SIZE_PRESETS[key]
    # Fuzzy: ohne Leerzeichen / case
    compact = key.replace(" ", "").lower()
    for k, v in PAGE_SIZE_PRESETS.items():
        if k.replace(" ", "").lower() == compact:
            return v
    for k, v in LAYOUT_PAGE_PRESETS.items():
        if k.replace(" ", "").lower() == compact:
            return v
    raise KeyError(f"Unbekanntes Seitenformat: {name}")


def ruler_ticks(
    length_pt: float,
    *,
    unit: str = "mm",
    major_every: int = 10,
) -> list[dict[str, Any]]:
    """
    Tick-Marken für Lineal entlang einer Kante (0 … length_pt).
    major_every: bei mm alle N mm eine Hauptmarke; bei inch alle 1 inch.
    """
    u = (unit or "mm").lower().strip()
    ticks: list[dict[str, Any]] = []
    if u in ("in", "inch", "inches"):
        step_pt = 72.0 / 8.0  # 1/8 inch
        major_pt = 72.0
        n = 0
        pos = 0.0
        while pos <= length_pt + 0.01:
            is_major = abs(pos % major_pt) < 0.05 or abs(pos) < 0.05
            label = f"{pos / 72.0:.2f}" if is_major else ""
            ticks.append(
                {
                    "pos_pt": pos,
                    "major": is_major,
                    "label": label,
                    "unit": "inch",
                }
            )
            n += 1
            pos = n * step_pt
    else:
        step_mm = 1.0
        major_mm = max(1, int(major_every))
        n = 0
        pos_mm = 0.0
        length_mm = pt_to_mm(length_pt)
        while pos_mm <= length_mm + 0.01:
            is_major = (int(round(pos_mm)) % major_mm) == 0
            ticks.append(
                {
                    "pos_pt": mm_to_pt(pos_mm),
                    "major": is_major,
                    "label": f"{int(round(pos_mm))}" if is_major else "",
                    "unit": "mm",
                }
            )
            n += 1
            pos_mm = n * step_mm
    return ticks


def grid_lines(
    width_pt: float,
    height_pt: float,
    *,
    spacing_mm: float = 5.0,
) -> dict[str, list[float]]:
    """Vertikale/horizontale Rasterlinien in PDF-Punkten (Y von unten)."""
    step = mm_to_pt(max(1.0, float(spacing_mm)))
    xs: list[float] = []
    ys: list[float] = []
    x = 0.0
    while x <= width_pt + 0.01:
        xs.append(x)
        x += step
    y = 0.0
    while y <= height_pt + 0.01:
        ys.append(y)
        y += step
    return {"vertical": xs, "horizontal": ys}


def snap_to_grid(
    x_pt: float,
    y_pt: float,
    *,
    spacing_mm: float = 5.0,
) -> Tuple[float, float]:
    step = mm_to_pt(max(1.0, float(spacing_mm)))
    if step <= 0:
        return float(x_pt), float(y_pt)
    sx = round(float(x_pt) / step) * step
    sy = round(float(y_pt) / step) * step
    return sx, sy


def snap_to_guides(
    x_pt: float,
    y_pt: float,
    guides: Sequence[Guide],
    *,
    threshold_pt: float = 4.0,
) -> Tuple[float, float]:
    sx, sy = float(x_pt), float(y_pt)
    for g in guides:
        if g.orientation == "vertical" and abs(sx - g.position_pt) <= threshold_pt:
            sx = g.position_pt
        if g.orientation == "horizontal" and abs(sy - g.position_pt) <= threshold_pt:
            sy = g.position_pt
    return sx, sy


def normalize_guides(raw: Iterable[Any]) -> list[Guide]:
    out: list[Guide] = []
    for i, item in enumerate(raw or []):
        if isinstance(item, Guide):
            g = item
        elif isinstance(item, dict):
            g = Guide.from_dict(item)
        else:
            continue
        if not g.id:
            g.id = f"g{i+1}"
        out.append(g)
    return out


# --- Absatzformatierung (Marker im Editor-Text) ---


def paragraph_align_marker(alignment: str) -> str:
    align = (alignment or "left").lower().strip()
    if align not in PARAGRAPH_ALIGNMENTS:
        align = "left"
    return f"<!-- ild-align:{align} -->"


def paragraph_spacing_marker(
    *,
    line_spacing: float = 1.15,
    space_before_pt: float = 0.0,
    space_after_pt: float = 6.0,
) -> str:
    ls = float(line_spacing)
    if ls not in LINE_SPACINGS:
        ls = min(LINE_SPACINGS, key=lambda x: abs(x - ls))
    return (
        f"<!-- ild-spacing:ls={ls:g};sb={float(space_before_pt):g};"
        f"sa={float(space_after_pt):g} -->"
    )


def apply_paragraph_format(
    text: str,
    *,
    alignment: str | None = None,
    line_spacing: float | None = None,
    space_before_pt: float | None = None,
    space_after_pt: float | None = None,
    paragraph_index: int | None = None,
) -> str:
    """
    Setzt Absatz-Marker vor Absätze (durch Leerzeilen getrennt).
    paragraph_index=None → alle Absätze; sonst 0-basiert.
    """
    paras = _split_paragraphs(text)
    if not paras:
        return text or ""
    indices = range(len(paras)) if paragraph_index is None else [int(paragraph_index)]
    for idx in indices:
        if idx < 0 or idx >= len(paras):
            continue
        body_lines = _strip_para_markers(paras[idx])
        prefix: list[str] = []
        if alignment is not None:
            prefix.append(paragraph_align_marker(alignment))
        if (
            line_spacing is not None
            or space_before_pt is not None
            or space_after_pt is not None
        ):
            # bestehende Spacing-Werte aus Marker lesen
            cur = parse_paragraph_format("\n".join(paras[idx]))
            prefix.append(
                paragraph_spacing_marker(
                    line_spacing=(
                        float(line_spacing)
                        if line_spacing is not None
                        else cur.line_spacing
                    ),
                    space_before_pt=(
                        float(space_before_pt)
                        if space_before_pt is not None
                        else cur.space_before_pt
                    ),
                    space_after_pt=(
                        float(space_after_pt)
                        if space_after_pt is not None
                        else cur.space_after_pt
                    ),
                )
            )
        paras[idx] = "\n".join(prefix + body_lines) if prefix else "\n".join(body_lines)
    return "\n\n".join(paras)


def parse_paragraph_format(paragraph: str) -> ParagraphFormat:
    align: AlignName = "left"
    ls = 1.15
    sb = 0.0
    sa = 6.0
    for line in (paragraph or "").splitlines():
        m = _ALIGN_MARKER_RE.match(line.strip())
        if m:
            align = m.group(1).lower()  # type: ignore[assignment]
            continue
        m2 = _SPACE_MARKER_RE.match(line.strip())
        if m2:
            ls = float(m2.group(1))
            sb = float(m2.group(2))
            sa = float(m2.group(3))
    return ParagraphFormat(
        alignment=align, line_spacing=ls, space_before_pt=sb, space_after_pt=sa
    )


def list_paragraph_formats_from_styles() -> list[dict[str, Any]]:
    """Style-Presets inkl. Absatzattribute (2.6.10 Styles + 2.6.11 Spacing/Align)."""
    from .auto_format import STYLE_PRESETS, list_style_presets

    # Defaults an Presets anbinden falls noch nicht gesetzt
    defaults = {
        "heading1": {"alignment": "left", "line_spacing": 1.15, "space_before_pt": 14.0, "space_after_pt": 8.0},
        "heading2": {"alignment": "left", "line_spacing": 1.15, "space_before_pt": 12.0, "space_after_pt": 6.0},
        "heading3": {"alignment": "left", "line_spacing": 1.15, "space_before_pt": 10.0, "space_after_pt": 4.0},
        "body": {"alignment": "left", "line_spacing": 1.15, "space_before_pt": 0.0, "space_after_pt": 6.0},
        "quote": {"alignment": "left", "line_spacing": 1.5, "space_before_pt": 8.0, "space_after_pt": 8.0},
    }
    for sid, preset in STYLE_PRESETS.items():
        d = defaults.get(sid, defaults["body"])
        for k, v in d.items():
            preset.setdefault(k, v)
    rows = list_style_presets()
    for row in rows:
        pf = ParagraphFormat.from_style_preset(row, style_id=str(row.get("id") or "body"))
        row["paragraph"] = pf.to_dict()
    return rows


def apply_style_paragraph_defaults(text: str, style_id: str = "body") -> str:
    """Wendet Absatz-Defaults eines Style-Presets auf alle Absätze an."""
    rows = {r["id"]: r for r in list_paragraph_formats_from_styles()}
    preset = rows.get(style_id) or rows.get("body") or {}
    pf = ParagraphFormat.from_style_preset(preset, style_id=style_id)
    return apply_paragraph_format(
        text,
        alignment=pf.alignment,
        line_spacing=pf.line_spacing,
        space_before_pt=pf.space_before_pt,
        space_after_pt=pf.space_after_pt,
    )


def _split_paragraphs(text: str) -> list[str]:
    raw = (text or "").replace("\r\n", "\n").strip("\n")
    if not raw.strip():
        return []
    parts = re.split(r"\n\s*\n", raw)
    return [p.strip("\n") for p in parts if p.strip() or p == ""]


def _strip_para_markers(paragraph: str) -> list[str]:
    lines: list[str] = []
    for line in (paragraph or "").splitlines():
        s = line.strip()
        if _ALIGN_MARKER_RE.match(s) or _SPACE_MARKER_RE.match(s):
            continue
        lines.append(line)
    return lines if lines else [""]


# --- Kopf-/Fußzeile mit Titel / Ersteller ---


def document_hf_fields(pdf_path: str | Path) -> dict[str, str]:
    """Titel/Autor/Creator aus PDF-Metadaten."""
    from .metadata import get_metadata

    meta = get_metadata(pdf_path)
    return {
        "title": (meta.title or "").strip(),
        "author": (meta.author or "").strip(),
        "creator": (meta.creator or meta.author or "").strip(),
        "stem": Path(pdf_path).stem,
    }


def apply_header_footer_with_meta(
    pdf_path: str | Path,
    *,
    out_path: str | Path | None = None,
    header_text: str = "{title}",
    footer_text: str = "{author} — {n} / {total}",
    include_page_numbers: bool = True,
    page_number_template: str = "{n} / {total}",
    title: str | None = None,
    author: str | None = None,
    creator: str | None = None,
    font_size: float = 10.0,
    margin: float = 28.0,
    pages: Optional[Sequence[int]] = None,
) -> Path:
    """
    Kopf-/Fußzeile bakken inkl. {title}/{author}/{creator}/{stem}/{n}/{total}/{date}.
    Metadaten aus PDF wenn nicht explizit übergeben; optional Autor in DocInfo schreiben.
    """
    from .metadata import PdfMetadata, get_metadata, set_metadata
    from .watermark import apply_header_footer

    pdf_path = Path(pdf_path)
    fields = document_hf_fields(pdf_path)
    if title is not None:
        fields["title"] = str(title)
    if author is not None:
        fields["author"] = str(author)
        fields["creator"] = str(creator if creator is not None else author)
    elif creator is not None:
        fields["creator"] = str(creator)

    # Metadaten aktualisieren wenn Titel/Autor gesetzt
    if title is not None or author is not None:
        meta = get_metadata(pdf_path)
        set_metadata(
            pdf_path,
            PdfMetadata(
                title=fields["title"] or meta.title,
                author=fields["author"] or meta.author,
                subject=meta.subject,
                keywords=meta.keywords,
                creator=fields["creator"] or meta.creator,
                producer=meta.producer,
            ),
        )

    return apply_header_footer(
        pdf_path,
        out_path=out_path,
        pages=pages,
        header_text=header_text,
        footer_text=footer_text,
        include_page_numbers=include_page_numbers,
        page_number_template=page_number_template,
        font_size=font_size,
        margin=margin,
        title=fields.get("title") or "",
        author=fields.get("author") or "",
        creator=fields.get("creator") or "",
    )


def format_hf_preview_with_meta(
    *,
    header_text: str = "{title}",
    footer_text: str = "{author}",
    include_page_numbers: bool = True,
    page_number_template: str = "{n} / {total}",
    title: str = "",
    author: str = "",
    creator: str = "",
    stem: str = "dokument",
    total_pages: int = 1,
) -> str:
    from .watermark import format_header_footer_preview

    mapping = {
        "title": title or stem,
        "author": author or creator or "",
        "creator": creator or author or "",
        "stem": stem,
    }

    def _exp(t: str) -> str:
        out = t or ""
        for k, v in mapping.items():
            out = out.replace("{" + k + "}", v)
        return out

    return format_header_footer_preview(
        header_text=_exp(header_text),
        footer_text=_exp(footer_text),
        include_page_numbers=include_page_numbers,
        page_number_template=page_number_template,
        total_pages=total_pages,
        stem=stem,
    )


# --- Satzspiegel (Type Area) — Ränder an Seitenformate gebunden — 2.6.12 ---


@dataclass
class Satzspiegel:
    """Satzspiegel / Type Area: Ränder in mm, gebunden an Seitenformat-Preset."""

    format_name: str = "A4"
    margin_top_mm: float = 20.0
    margin_bottom_mm: float = 25.0
    margin_inside_mm: float = 25.0  # Bund / innen (bei einseitig = links)
    margin_outside_mm: float = 20.0
    columns: int = 1
    gutter_mm: float = 5.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.update(self.rect_pt())
        d["margins_pt"] = self.margins_pt()
        return d

    def margins_pt(self) -> dict[str, float]:
        return {
            "top": mm_to_pt(self.margin_top_mm),
            "bottom": mm_to_pt(self.margin_bottom_mm),
            "left": mm_to_pt(self.margin_inside_mm),
            "right": mm_to_pt(self.margin_outside_mm),
        }

    def page_size_pt(self) -> Tuple[float, float]:
        try:
            return resolve_page_format(self.format_name)
        except KeyError:
            return LAYOUT_PAGE_PRESETS.get("A4", PAGE_SIZE_PRESETS["A4"])

    def rect_pt(self) -> dict[str, float]:
        """Type-Area-Rechteck in PDF-Punkten (Ursprung unten-links)."""
        w, h = self.page_size_pt()
        m = self.margins_pt()
        x = m["left"]
        y = m["bottom"]
        tw = max(1.0, w - m["left"] - m["right"])
        th = max(1.0, h - m["top"] - m["bottom"])
        return {
            "x": x,
            "y": y,
            "width": tw,
            "height": th,
            "page_width": w,
            "page_height": h,
        }

    def column_rects_pt(self) -> list[dict[str, float]]:
        """Spaltenrechtecke innerhalb des Satzspiegels."""
        base = self.rect_pt()
        cols = max(1, int(self.columns))
        gutter = mm_to_pt(max(0.0, float(self.gutter_mm)))
        usable = max(1.0, base["width"] - gutter * (cols - 1))
        col_w = usable / cols
        out: list[dict[str, float]] = []
        for i in range(cols):
            out.append(
                {
                    "x": base["x"] + i * (col_w + gutter),
                    "y": base["y"],
                    "width": col_w,
                    "height": base["height"],
                    "column": i,
                }
            )
        return out


# Empfohlene Ränder (mm) je Formatkategorie — typografische Faustwerte
_SATZSPIEGEL_DEFAULTS_MM: dict[str, Tuple[float, float, float, float]] = {
    # top, bottom, inside, outside
    "Taschenbuch": (15.0, 18.0, 18.0, 14.0),
    "DINA5": (18.0, 22.0, 20.0, 16.0),
    "Roman": (16.0, 20.0, 20.0, 15.0),
    "Sachbuch": (20.0, 24.0, 22.0, 18.0),
    "DINA4": (20.0, 25.0, 25.0, 20.0),
    "A4": (20.0, 25.0, 25.0, 20.0),
    "Quadrat": (18.0, 20.0, 18.0, 18.0),
    "A5": (18.0, 22.0, 20.0, 16.0),
    "A3": (25.0, 30.0, 28.0, 22.0),
    "A6": (12.0, 14.0, 14.0, 12.0),
    "US Letter": (20.0, 25.0, 25.0, 20.0),
    "US Legal": (20.0, 25.0, 25.0, 20.0),
}


def satzspiegel_for_format(
    format_name: str = "A4",
    *,
    columns: int = 1,
    gutter_mm: float = 5.0,
    margin_top_mm: float | None = None,
    margin_bottom_mm: float | None = None,
    margin_inside_mm: float | None = None,
    margin_outside_mm: float | None = None,
) -> Satzspiegel:
    """Satzspiegel-Preset für Seitenformat (Override-Ränder optional)."""
    key = (format_name or "A4").strip()
    # Alias-Normalisierung
    compact = key.replace(" ", "").lower()
    resolved_name = key
    for name in LAYOUT_PAGE_PRESETS:
        if name.replace(" ", "").lower() == compact:
            resolved_name = name
            break
    defaults = _SATZSPIEGEL_DEFAULTS_MM.get(resolved_name)
    if defaults is None:
        # Fuzzy ohne Leerzeichen
        for k, v in _SATZSPIEGEL_DEFAULTS_MM.items():
            if k.replace(" ", "").lower() == compact:
                defaults = v
                resolved_name = k
                break
    if defaults is None:
        defaults = (20.0, 25.0, 25.0, 20.0)
    top, bottom, inside, outside = defaults
    return Satzspiegel(
        format_name=resolved_name,
        margin_top_mm=float(margin_top_mm if margin_top_mm is not None else top),
        margin_bottom_mm=float(margin_bottom_mm if margin_bottom_mm is not None else bottom),
        margin_inside_mm=float(margin_inside_mm if margin_inside_mm is not None else inside),
        margin_outside_mm=float(
            margin_outside_mm if margin_outside_mm is not None else outside
        ),
        columns=max(1, int(columns)),
        gutter_mm=float(gutter_mm),
    )


def list_satzspiegel_presets(*, columns: int = 1) -> list[dict[str, Any]]:
    """Satzspiegel für alle Layout-Seitenformate."""
    return [satzspiegel_for_format(name, columns=columns).to_dict() for name in LAYOUT_PAGE_PRESETS]


# --- Musterseiten (Master Pages) — 2.6.12 ---


@dataclass
class MasterPage:
    """Musterseite: wiederkehrende Kopf-/Fußzeile + Seitenzahlen + Satzspiegel."""

    name: str = "Standard"
    header_text: str = "{title}"
    footer_text: str = "{author} — {n} / {total}"
    include_page_numbers: bool = True
    page_number_template: str = "{n} / {total}"
    font_size: float = 10.0
    # HF-Abstand vom Seitenrand (pt); an Satzspiegel gekoppelt wenn None
    header_margin_pt: float | None = None
    footer_margin_pt: float | None = None
    satzspiegel: Satzspiegel = field(default_factory=lambda: satzspiegel_for_format("A4"))
    start_page: int = 1  # 1-basiert; Seiten davor ohne Muster
    odd_even: bool = False  # bei True: outside/inside spiegeln (einfach)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "header_text": self.header_text,
            "footer_text": self.footer_text,
            "include_page_numbers": self.include_page_numbers,
            "page_number_template": self.page_number_template,
            "font_size": self.font_size,
            "header_margin_pt": self.header_margin_pt,
            "footer_margin_pt": self.footer_margin_pt,
            "satzspiegel": self.satzspiegel.to_dict(),
            "start_page": self.start_page,
            "odd_even": self.odd_even,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MasterPage":
        ss_raw = data.get("satzspiegel") or {}
        if isinstance(ss_raw, Satzspiegel):
            ss = ss_raw
        elif isinstance(ss_raw, dict) and ss_raw:
            ss = Satzspiegel(
                format_name=str(ss_raw.get("format_name") or "A4"),
                margin_top_mm=float(ss_raw.get("margin_top_mm") or 20.0),
                margin_bottom_mm=float(ss_raw.get("margin_bottom_mm") or 25.0),
                margin_inside_mm=float(ss_raw.get("margin_inside_mm") or 25.0),
                margin_outside_mm=float(ss_raw.get("margin_outside_mm") or 20.0),
                columns=int(ss_raw.get("columns") or 1),
                gutter_mm=float(ss_raw.get("gutter_mm") or 5.0),
            )
        else:
            fmt = str(data.get("format_name") or "A4")
            ss = satzspiegel_for_format(fmt)
        return cls(
            name=str(data.get("name") or "Standard"),
            header_text=str(data.get("header_text") or "{title}"),
            footer_text=str(data.get("footer_text") or "{author} — {n} / {total}"),
            include_page_numbers=bool(data.get("include_page_numbers", True)),
            page_number_template=str(data.get("page_number_template") or "{n} / {total}"),
            font_size=float(data.get("font_size") or 10.0),
            header_margin_pt=(
                float(data["header_margin_pt"])
                if data.get("header_margin_pt") is not None
                else None
            ),
            footer_margin_pt=(
                float(data["footer_margin_pt"])
                if data.get("footer_margin_pt") is not None
                else None
            ),
            satzspiegel=ss,
            start_page=max(1, int(data.get("start_page") or 1)),
            odd_even=bool(data.get("odd_even", False)),
        )


MASTER_PRESETS: dict[str, dict[str, Any]] = {
    "Standard": {
        "name": "Standard",
        "header_text": "{title}",
        "footer_text": "{author} — {n} / {total}",
        "format_name": "A4",
    },
    "Buch": {
        "name": "Buch",
        "header_text": "{title}",
        "footer_text": "{n}",
        "format_name": "Taschenbuch",
        "page_number_template": "{n}",
    },
    "Sachbuch": {
        "name": "Sachbuch",
        "header_text": "{author}",
        "footer_text": "{title} · {n} / {total}",
        "format_name": "Sachbuch",
    },
    "Minimal": {
        "name": "Minimal",
        "header_text": "",
        "footer_text": "{n}",
        "format_name": "A4",
        "page_number_template": "{n}",
    },
}


def list_master_presets() -> list[dict[str, Any]]:
    """Eingebaute Musterseiten-Presets inkl. Satzspiegel."""
    out: list[dict[str, Any]] = []
    for key, raw in MASTER_PRESETS.items():
        mp = master_page_from_preset(key)
        d = mp.to_dict()
        d["id"] = key
        out.append(d)
    return out


def master_page_from_preset(name: str = "Standard") -> MasterPage:
    key = (name or "Standard").strip()
    raw = MASTER_PRESETS.get(key)
    if raw is None:
        compact = key.replace(" ", "").lower()
        for k, v in MASTER_PRESETS.items():
            if k.replace(" ", "").lower() == compact:
                raw = v
                key = k
                break
    if raw is None:
        raw = MASTER_PRESETS["Standard"]
        key = "Standard"
    data = dict(raw)
    fmt = str(data.pop("format_name", "A4"))
    ss = satzspiegel_for_format(fmt)
    data["satzspiegel"] = ss
    data.setdefault("name", key)
    return MasterPage.from_dict(data)


def apply_master_page(
    pdf_path: str | Path,
    master: MasterPage | str | dict[str, Any] | None = None,
    *,
    out_path: str | Path | None = None,
    title: str | None = None,
    author: str | None = None,
    creator: str | None = None,
    pages: Optional[Sequence[int]] = None,
) -> Path:
    """
    Musterseite auf PDF anwenden: Kopf-/Fußzeile + Seitenzahlen über Seiten bakken.
    Baut auf ``apply_header_footer_with_meta`` (2.6.11) auf; Ränder aus Satzspiegel.
    """
    if master is None:
        mp = master_page_from_preset("Standard")
    elif isinstance(master, MasterPage):
        mp = master
    elif isinstance(master, str):
        mp = master_page_from_preset(master)
    else:
        mp = MasterPage.from_dict(master)

    margins = mp.satzspiegel.margins_pt()
    header_margin = (
        float(mp.header_margin_pt)
        if mp.header_margin_pt is not None
        else max(12.0, margins["top"] * 0.45)
    )
    # apply_header_footer nutzt einen gemeinsamen margin — Mittelwert / Header
    bake_margin = header_margin

    page_indices: Optional[list[int]] = None
    if pages is not None:
        page_indices = [int(p) for p in pages]
    elif mp.start_page > 1:
        from .document import PdfDocument

        with PdfDocument(pdf_path) as doc:
            total = len(doc)
        page_indices = list(range(mp.start_page - 1, total))

    return apply_header_footer_with_meta(
        pdf_path,
        out_path=out_path,
        header_text=mp.header_text,
        footer_text=mp.footer_text,
        include_page_numbers=mp.include_page_numbers,
        page_number_template=mp.page_number_template,
        title=title,
        author=author,
        creator=creator,
        font_size=mp.font_size,
        margin=bake_margin,
        pages=page_indices,
    )


def type_area_guides(satzspiegel: Satzspiegel) -> list[Guide]:
    """Hilfslinien entlang des Satzspiegel-Rechtecks."""
    r = satzspiegel.rect_pt()
    left = r["x"]
    right = r["x"] + r["width"]
    bottom = r["y"]
    top = r["y"] + r["height"]
    return normalize_guides(
        [
            {"orientation": "vertical", "position_pt": left, "id": "ss-left"},
            {"orientation": "vertical", "position_pt": right, "id": "ss-right"},
            {"orientation": "horizontal", "position_pt": bottom, "id": "ss-bottom"},
            {"orientation": "horizontal", "position_pt": top, "id": "ss-top"},
        ]
    )
