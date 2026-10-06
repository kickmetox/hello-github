"""Seitenlayout für den Texteditor (Word-Suite/DOCX) — 2.6.53.

Nutzt die DTP-Presets aus ``ild_pdf.page_layout`` (A4/Letter/Buchformate) und den
Satzspiegel-Vorschlag. Der Editor (``QPlainTextEdit``) rendert damit eine
Textspalte in Seitenbreite: ``QTextDocument.setPageSize`` (Druck/Export) plus
Viewport-Ränder, sodass Text wie auf einer Seite umbricht statt am Fensterrand.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from ild_pdf.page_layout import LAYOUT_PAGE_PRESETS, satzspiegel_for_format
from ild_pdf.pages import PAGE_SIZE_PRESETS, mm_to_pt, pt_to_mm

SCOPES: tuple[str, ...] = ("rich", "all", "off")
ORIENTATIONS: tuple[str, ...] = ("portrait", "landscape")
CUSTOM_PRESET = "Benutzerdefiniert"


def page_presets() -> list[tuple[str, float, float]]:
    """(Name, Breite pt, Höhe pt) — DTP-Reihenfolge, Duplikate (gleiche Maße) entfernt."""
    seen: set[tuple[int, int]] = set()
    out: list[tuple[str, float, float]] = []
    for name, (w, h) in list(LAYOUT_PAGE_PRESETS.items()) + list(PAGE_SIZE_PRESETS.items()):
        key = (int(round(w)), int(round(h)))
        if key in seen:
            continue
        seen.add(key)
        out.append((name, float(w), float(h)))
    return out


def preset_size(name: str) -> tuple[float, float] | None:
    for n, w, h in page_presets():
        if n.replace(" ", "").lower() == (name or "").replace(" ", "").lower():
            return w, h
    return None


@dataclass
class EditorPageLayout:
    enabled: bool = True
    scope: str = "rich"
    preset: str = "A4"
    width_pt: float = 595.28
    height_pt: float = 841.89
    orientation: str = "portrait"
    margin_top_mm: float = 25.0
    margin_bottom_mm: float = 20.0
    margin_left_mm: float = 25.0
    margin_right_mm: float = 20.0
    columns: int = 1
    header_distance_mm: float = 12.5
    footer_distance_mm: float = 12.5
    extra: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    # ---- Konstruktion ----------------------------------------------------
    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EditorPageLayout":
        d = dict(data or {})
        lay = cls()
        lay.enabled = bool(d.get("enabled", True))
        scope = str(d.get("scope", "rich") or "rich").lower()
        lay.scope = scope if scope in SCOPES else "rich"
        lay.preset = str(d.get("preset", "A4") or "A4")
        size = preset_size(lay.preset) if lay.preset != CUSTOM_PRESET else None
        try:
            lay.width_pt = float(d.get("width_pt", size[0] if size else 595.28))
            lay.height_pt = float(d.get("height_pt", size[1] if size else 841.89))
        except (TypeError, ValueError):
            lay.width_pt, lay.height_pt = (595.28, 841.89)
        if size and (abs(lay.width_pt - size[0]) > 0.5 or abs(lay.height_pt - size[1]) > 0.5):
            # Preset-Name gewinnt über abweichende Maße (alte/kaputte Settings)
            lay.width_pt, lay.height_pt = size
        ori = str(d.get("orientation", "portrait") or "portrait").lower()
        lay.orientation = ori if ori in ORIENTATIONS else "portrait"
        for key in (
            "margin_top_mm",
            "margin_bottom_mm",
            "margin_left_mm",
            "margin_right_mm",
            "header_distance_mm",
            "footer_distance_mm",
        ):
            try:
                val = float(d.get(key, getattr(lay, key)))
            except (TypeError, ValueError):
                val = float(getattr(lay, key))
            setattr(lay, key, max(0.0, min(val, 100.0)))
        try:
            cols = int(d.get("columns", 1) or 1)
        except (TypeError, ValueError):
            cols = 1
        lay.columns = cols if cols in (1, 2, 3) else 1
        lay._clamp()
        return lay

    @classmethod
    def from_settings(cls) -> "EditorPageLayout":
        from instantlensdoc.core.app_settings import get_editor_page_layout

        return cls.from_dict(get_editor_page_layout())

    def save(self) -> None:
        from instantlensdoc.core.app_settings import set_editor_page_layout

        set_editor_page_layout(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("extra", None)
        return d

    def _clamp(self) -> None:
        self.width_pt = max(mm_to_pt(50.0), min(self.width_pt, mm_to_pt(1200.0)))
        self.height_pt = max(mm_to_pt(50.0), min(self.height_pt, mm_to_pt(1200.0)))
        # Ränder dürfen die Seite nicht aufzehren (mind. 40 mm Textspalte)
        w_mm, h_mm = pt_to_mm(self.width_pt), pt_to_mm(self.height_pt)
        if self.orientation == "landscape":
            w_mm, h_mm = h_mm, w_mm
        if self.margin_left_mm + self.margin_right_mm > w_mm - 40.0:
            keep = max(0.0, (w_mm - 40.0) / 2.0)
            self.margin_left_mm = self.margin_right_mm = keep
        if self.margin_top_mm + self.margin_bottom_mm > h_mm - 40.0:
            keep = max(0.0, (h_mm - 40.0) / 2.0)
            self.margin_top_mm = self.margin_bottom_mm = keep

    # ---- Geometrie -------------------------------------------------------
    def page_size_pt(self) -> tuple[float, float]:
        """(Breite, Höhe) in pt inkl. Ausrichtung."""
        w, h = float(self.width_pt), float(self.height_pt)
        if self.orientation == "landscape":
            w, h = max(w, h), min(w, h)
        else:
            w, h = min(w, h), max(w, h)
        return w, h

    def text_width_pt(self) -> float:
        w, _h = self.page_size_pt()
        full = max(mm_to_pt(40.0), w - mm_to_pt(self.margin_left_mm) - mm_to_pt(self.margin_right_mm))
        cols = max(1, int(self.columns or 1))
        if cols <= 1:
            return full
        gap = mm_to_pt(4.0) * (cols - 1)
        return max(mm_to_pt(20.0), (full - gap) / float(cols))

    def text_height_pt(self) -> float:
        _w, h = self.page_size_pt()
        header = mm_to_pt(float(self.header_distance_mm or 0.0))
        footer = mm_to_pt(float(self.footer_distance_mm or 0.0))
        return max(
            mm_to_pt(40.0),
            h - mm_to_pt(self.margin_top_mm) - mm_to_pt(self.margin_bottom_mm) - header - footer,
        )

    def page_size_px(self, dpi: float = 96.0) -> tuple[float, float]:
        w, h = self.page_size_pt()
        f = float(dpi) / 72.0
        return w * f, h * f

    def text_width_px(self, dpi: float = 96.0) -> float:
        return self.text_width_pt() * float(dpi) / 72.0

    def margins_px(self, dpi: float = 96.0) -> tuple[float, float, float, float]:
        """(oben, unten, links, rechts) in Pixel."""
        f = float(dpi) / 72.0
        return (
            mm_to_pt(self.margin_top_mm) * f,
            mm_to_pt(self.margin_bottom_mm) * f,
            mm_to_pt(self.margin_left_mm) * f,
            mm_to_pt(self.margin_right_mm) * f,
        )

    def applies_to(self, rich_document: bool) -> bool:
        """Gilt das Layout für dieses Dokument? (scope rich/all/off + enabled)."""
        if not self.enabled or self.scope == "off":
            return False
        if self.scope == "all":
            return True
        return bool(rich_document)

    def describe(self) -> str:
        w, h = self.page_size_pt()
        ori = "Querformat" if self.orientation == "landscape" else "Hochformat"
        cols = max(1, int(self.columns or 1))
        return (
            f"{self.preset} {pt_to_mm(w):.0f}×{pt_to_mm(h):.0f} mm, {ori}, "
            f"{cols} Spalte(n), "
            f"Ränder o/u/l/r {self.margin_top_mm:.0f}/{self.margin_bottom_mm:.0f}/"
            f"{self.margin_left_mm:.0f}/{self.margin_right_mm:.0f} mm, "
            f"Kopf/Fuß {self.header_distance_mm:.0f}/{self.footer_distance_mm:.0f} mm, "
            f"Textbreite {pt_to_mm(self.text_width_pt()):.0f} mm"
        )

    # ---- DTP-Satzspiegel ------------------------------------------------
    def apply_satzspiegel(self) -> "EditorPageLayout":
        """Ränder aus dem DTP-Satzspiegel des Presets übernehmen (innen → links)."""
        sp = satzspiegel_for_format(self.preset if self.preset != CUSTOM_PRESET else "A4")
        self.margin_top_mm = float(sp.margin_top_mm)
        self.margin_bottom_mm = float(sp.margin_bottom_mm)
        self.margin_left_mm = float(sp.margin_inside_mm)
        self.margin_right_mm = float(sp.margin_outside_mm)
        self._clamp()
        return self

    def with_preset(self, name: str) -> "EditorPageLayout":
        size = preset_size(name)
        if size is not None:
            self.preset = name
            self.width_pt, self.height_pt = size
        else:
            self.preset = CUSTOM_PRESET
        self._clamp()
        return self


def preset_names(extra: Iterable[str] = ()) -> list[str]:
    names = [n for n, _w, _h in page_presets()]
    for e in extra:
        if e not in names:
            names.append(e)
    return names
