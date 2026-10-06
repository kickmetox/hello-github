"""Layout-Marken für den Word-Suite-Texteditor (Breite / Druck / Kopf-Fuß).

Metriken (mm, Farben) sind analog zu ``dtp.chrome`` / ``dtp.geometry`` gehalten.
DTP-Crop/Register bleibt in ``dtp.print_marks`` (nicht umschreiben) — gemeinsame
mm-Helfer hier, falls der Canvas sie später importiert.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

# Gleicher Satz wie instantlensdoc.dtp.chrome (nicht importieren — kein DTP-Rewrite).
MARGIN_BLUE = "#1A4DB3"
BLEED_RED = "#E30613"
PRINT_INK = "#1A1A1A"
HEADER_FOOTER_INK = "#5A6570"

BandHit = Literal["header", "footer"]


@dataclass
class EditorLayoutMarks:
    """Sichtbarkeit + Maße der Editor-Layout-Marken (persistiert in Settings)."""

    show_width_marks: bool = True
    show_print_marks: bool = False
    show_header_footer_marks: bool = True
    # Bildschirm vs. Druck/PDF — unabhängig von den Ansichts-Toggles.
    show_on_screen: bool = True
    include_width_on_print: bool = False
    include_print_on_print: bool = True
    include_hf_on_print: bool = True
    # Prepress-Maße
    crop_mm: float = 5.0
    bleed_mm: float = 3.0
    register_mm: float = 4.0
    color_bar_mm: float = 4.0
    gap_mm: float = 1.0
    header_height_mm: float = 12.5
    footer_height_mm: float = 12.5
    show_crop: bool = True
    show_bleed: bool = True
    show_register: bool = True
    show_color_bar: bool = True
    width_color: str = MARGIN_BLUE
    print_color: str = PRINT_INK
    bleed_color: str = BLEED_RED
    header_footer_color: str = HEADER_FOOTER_INK
    extra: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def defaults_dict(cls) -> dict[str, Any]:
        return cls().to_dict()

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EditorLayoutMarks":
        d = dict(data or {})
        m = cls()
        for key in (
            "show_width_marks",
            "show_print_marks",
            "show_header_footer_marks",
            "show_on_screen",
            "include_width_on_print",
            "include_print_on_print",
            "include_hf_on_print",
            "show_crop",
            "show_bleed",
            "show_register",
            "show_color_bar",
        ):
            if key in d:
                setattr(m, key, bool(d.get(key)))
        for key, lo, hi in (
            ("crop_mm", 1.0, 25.0),
            ("bleed_mm", 0.0, 20.0),
            ("register_mm", 1.0, 20.0),
            ("color_bar_mm", 1.0, 12.0),
            ("gap_mm", 0.2, 5.0),
            ("header_height_mm", 4.0, 40.0),
            ("footer_height_mm", 4.0, 40.0),
        ):
            try:
                val = float(d.get(key, getattr(m, key)))
            except (TypeError, ValueError):
                val = float(getattr(m, key))
            setattr(m, key, max(lo, min(hi, val)))
        for key in ("width_color", "print_color", "bleed_color", "header_footer_color"):
            raw = str(d.get(key, getattr(m, key)) or "").strip()
            if raw.startswith("#") and len(raw) in (4, 7, 9):
                setattr(m, key, raw)
        return m

    @classmethod
    def from_settings(cls) -> "EditorLayoutMarks":
        from instantlensdoc.core.app_settings import get_editor_layout_marks

        return cls.from_dict(get_editor_layout_marks())

    def save(self) -> None:
        from instantlensdoc.core.app_settings import set_editor_layout_marks

        set_editor_layout_marks(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("extra", None)
        return d

    def screen_width(self) -> bool:
        return bool(self.show_on_screen and self.show_width_marks)

    def screen_print(self) -> bool:
        return bool(self.show_on_screen and self.show_print_marks)

    def screen_header_footer(self) -> bool:
        return bool(self.show_on_screen and self.show_header_footer_marks)

    def any_screen(self) -> bool:
        return self.screen_width() or self.screen_print() or self.screen_header_footer()

    def print_print_marks_enabled(self) -> bool:
        """Druckmarken auf Druck/PDF — Default an, unabhängig vom Bildschirm-Toggle."""
        return bool(self.include_print_on_print)


def mm_to_px(mm: float, dpi: float = 96.0) -> float:
    return float(mm) * float(dpi) / 25.4


def px_to_mm(px: float, dpi: float = 96.0) -> float:
    d = float(dpi) or 96.0
    return float(px) * 25.4 / d


def type_area_from_page(
    page_x: float,
    page_y: float,
    page_w: float,
    page_h: float,
    *,
    margin_left: float,
    margin_top: float,
    margin_right: float,
    margin_bottom: float,
) -> tuple[float, float, float, float]:
    """(x, y, w, h) des Satzspiegels in denselben Einheiten wie die Seite."""
    x = page_x + max(0.0, float(margin_left))
    y = page_y + max(0.0, float(margin_top))
    w = max(1.0, float(page_w) - float(margin_left) - float(margin_right))
    h = max(1.0, float(page_h) - float(margin_top) - float(margin_bottom))
    return x, y, w, h


def header_band_rect(
    page_x: float,
    page_y: float,
    page_w: float,
    *,
    height: float,
    margin_left: float = 0.0,
    margin_right: float = 0.0,
) -> tuple[float, float, float, float]:
    h = max(1.0, float(height))
    return (
        page_x + max(0.0, float(margin_left)),
        page_y,
        max(1.0, float(page_w) - float(margin_left) - float(margin_right)),
        h,
    )


def footer_band_rect(
    page_x: float,
    page_y: float,
    page_w: float,
    page_h: float,
    *,
    height: float,
    margin_left: float = 0.0,
    margin_right: float = 0.0,
) -> tuple[float, float, float, float]:
    h = max(1.0, float(height))
    return (
        page_x + max(0.0, float(margin_left)),
        page_y + float(page_h) - h,
        max(1.0, float(page_w) - float(margin_left) - float(margin_right)),
        h,
    )


def crop_mark_segments_mm(
    page_w_mm: float,
    page_h_mm: float,
    *,
    crop_mm: float = 5.0,
    gap_mm: float = 1.0,
) -> list[tuple[float, float, float, float]]:
    """Crop-Marken (L-Form) außerhalb der Seite, Ursprung oben-links, mm.

    Sharing-Punkt für DTP: dieselben Segmente in pt via ``mm * 72/25.4``.
    """
    c = max(1.0, float(crop_mm))
    g = max(0.2, float(gap_mm))
    w, h = float(page_w_mm), float(page_h_mm)
    segs: list[tuple[float, float, float, float]] = []
    corners = (
        (0.0, 0.0, -1.0, -1.0),
        (w, 0.0, 1.0, -1.0),
        (0.0, h, -1.0, 1.0),
        (w, h, 1.0, 1.0),
    )
    for cx, cy, sx, sy in corners:
        segs.append((cx + sx * g, cy + sy * g, cx + sx * (g + c), cy + sy * g))
        segs.append((cx + sx * g, cy + sy * g, cx + sx * g, cy + sy * (g + c)))
    return segs


def register_marks_mm(
    page_w_mm: float,
    page_h_mm: float,
    *,
    register_mm: float = 4.0,
    gap_mm: float = 1.0,
) -> list[tuple[float, float, float]]:
    """Registrierkreuze: (cx, cy, radius_mm) oben/unten/links/rechts Mitte."""
    r = max(0.8, float(register_mm) * 0.35)
    g = max(0.2, float(gap_mm))
    w, h = float(page_w_mm), float(page_h_mm)
    off = g + float(register_mm) * 0.6
    return [
        (w / 2.0, -off, r),
        (w / 2.0, h + off, r),
        (-off, h / 2.0, r),
        (w + off, h / 2.0, r),
    ]


def color_bar_patches_mm(
    page_w_mm: float,
    page_h_mm: float,
    *,
    bar_mm: float = 4.0,
    gap_mm: float = 1.0,
) -> list[tuple[float, float, float, float, str]]:
    """CMYK+RGB-Farbkeil unterhalb der Seite (x, y, w, h, hex)."""
    colors = ("#00AEEF", "#E6007E", "#FFED00", "#1A1A1A", "#E30613", "#00A651", "#0057A8")
    n = len(colors)
    bar_h = max(1.0, float(bar_mm))
    g = max(0.2, float(gap_mm))
    usable = max(10.0, float(page_w_mm) * 0.6)
    patch_w = usable / n
    x0 = (float(page_w_mm) - usable) / 2.0
    y0 = float(page_h_mm) + g + 0.5
    return [
        (x0 + i * patch_w, y0, max(0.8, patch_w - 0.2), bar_h, colors[i])
        for i in range(n)
    ]


def stamp_print_marks_pdf(path, marks: "EditorLayoutMarks") -> bool:
    """Crop/Bleed/Register als Content-Stream an jede PDF-Seite (Export/Druck)."""
    from pathlib import Path

    if marks is None or not marks.include_print_on_print:
        return False
    src = Path(path)
    if not src.is_file():
        return False
    try:
        import pikepdf
    except Exception:
        return False
    mm = 72.0 / 25.4
    crop = float(marks.crop_mm) * mm
    gap = float(marks.gap_mm) * mm
    bleed = float(marks.bleed_mm) * mm
    try:
        with pikepdf.open(src, allow_overwriting_input=True) as pdf:
            for page in pdf.pages:
                box = [float(x) for x in page.mediabox]
                x0, y0, x1, y1 = box[0], box[1], box[2], box[3]
                cmds = ["q", "0.35 w", "0 0 0 RG"]
                if marks.show_bleed and bleed > 0:
                    cmds.append("0.89 0.02 0.07 RG")
                    cmds.append(
                        f"{x0 - bleed} {y0 - bleed} { (x1 - x0) + 2 * bleed } "
                        f"{ (y1 - y0) + 2 * bleed } re S"
                    )
                    cmds.append("0 0 0 RG")
                if marks.show_crop:
                    corners = (
                        (x0, y0, -1, -1),
                        (x1, y0, 1, -1),
                        (x0, y1, -1, 1),
                        (x1, y1, 1, 1),
                    )
                    for cx, cy, sx, sy in corners:
                        cmds.append(
                            f"{cx + sx * gap} {cy + sy * gap} m "
                            f"{cx + sx * (gap + crop)} {cy + sy * gap} l S"
                        )
                        cmds.append(
                            f"{cx + sx * gap} {cy + sy * gap} m "
                            f"{cx + sx * gap} {cy + sy * (gap + crop)} l S"
                        )
                if marks.show_register:
                    r = float(marks.register_mm) * mm * 0.35
                    off = gap + float(marks.register_mm) * mm * 0.6
                    centers = (
                        ((x0 + x1) / 2.0, y1 + off),
                        ((x0 + x1) / 2.0, y0 - off),
                        (x0 - off, (y0 + y1) / 2.0),
                        (x1 + off, (y0 + y1) / 2.0),
                    )
                    for cx, cy in centers:
                        cmds.append(f"{cx - r} {cy} m {cx + r} {cy} l S")
                        cmds.append(f"{cx} {cy - r} m {cx} {cy + r} l S")
                cmds.append("Q")
                overlay = pikepdf.Stream(pdf, "\n".join(cmds).encode("ascii"))
                contents = page.get("/Contents")
                if contents is None:
                    page["/Contents"] = overlay
                elif isinstance(contents, pikepdf.Array):
                    contents.append(overlay)
                else:
                    page["/Contents"] = pikepdf.Array([contents, overlay])
            pdf.save(src)
        return True
    except Exception:
        return False


def hit_test_band(
    x: float,
    y: float,
    header: tuple[float, float, float, float],
    footer: tuple[float, float, float, float],
) -> BandHit | None:
    def _inside(rect: tuple[float, float, float, float]) -> bool:
        rx, ry, rw, rh = rect
        return rx <= x <= rx + rw and ry <= y <= ry + rh

    if _inside(header):
        return "header"
    if _inside(footer):
        return "footer"
    return None
