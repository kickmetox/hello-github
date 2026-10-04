"""Druckvorbereitung 2.6.18: Farbmanagement, Bleed/Anschnitt, Ebenen, Preflight, PDF/X.

RGB/CMYK-Workflows, Custom-Paletten, Anschnitt-Einstellungen, Dokument-Ebenen
(Hintergrund/Bilder/Text), Preflight (fehlende Schriften, Bildauflösung) und
druckreifer PDF/X- bzw. Print-Ready-Export neben dem bestehenden PDF-Export.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, List, Literal, Optional, Sequence, Tuple, Union

from .pages import mm_to_pt, pt_to_mm

PathLike = Union[str, Path]

ColorMode = Literal["rgb", "cmyk"]
LayerName = Literal["background", "images", "text"]
PdfxProfile = Literal["pdfx1a", "pdfx4", "print_ready"]

LAYER_ORDER: tuple[LayerName, ...] = ("background", "images", "text")
LAYER_LABELS: dict[str, str] = {
    "background": "Hintergrund",
    "images": "Bilder",
    "text": "Text",
}

# Standard-Bleed in mm (Offset-Druck üblich)
DEFAULT_BLEED_MM = 3.0
BLEED_PRESETS_MM: dict[str, float] = {
    "none": 0.0,
    "minimal": 2.0,
    "standard": 3.0,
    "extra": 5.0,
}

# Mindest-DPI für Druck (Preflight)
DEFAULT_MIN_IMAGE_DPI = 150
PRINT_MIN_IMAGE_DPI = 300

# Einfache Prozessfarben / Spot-Hinweise (keine echte Pantone-Lizenz)
SPOT_SWATCHES: dict[str, dict[str, Any]] = {
    "black": {"name": "Prozessschwarz", "cmyk": (0.0, 0.0, 0.0, 1.0), "spot": False},
    "cyan": {"name": "Cyan", "cmyk": (1.0, 0.0, 0.0, 0.0), "spot": False},
    "magenta": {"name": "Magenta", "cmyk": (0.0, 1.0, 0.0, 0.0), "spot": False},
    "yellow": {"name": "Yellow", "cmyk": (0.0, 0.0, 1.0, 0.0), "spot": False},
    "rich_black": {"name": "Tiefschwarz", "cmyk": (0.6, 0.4, 0.4, 1.0), "spot": False},
    "paper": {"name": "Papierweiß", "cmyk": (0.0, 0.0, 0.0, 0.0), "spot": False},
}


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def rgb_to_cmyk(r: float, g: float, b: float) -> Tuple[float, float, float, float]:
    """RGB 0–1 → CMYK 0–1 (einfache Undercolor-Removal-Näherung)."""
    r, g, b = _clamp01(r), _clamp01(g), _clamp01(b)
    k = 1.0 - max(r, g, b)
    if k >= 1.0 - 1e-9:
        return (0.0, 0.0, 0.0, 1.0)
    c = (1.0 - r - k) / (1.0 - k)
    m = (1.0 - g - k) / (1.0 - k)
    y = (1.0 - b - k) / (1.0 - k)
    return (_clamp01(c), _clamp01(m), _clamp01(y), _clamp01(k))


def cmyk_to_rgb(c: float, m: float, y: float, k: float) -> Tuple[float, float, float]:
    """CMYK 0–1 → RGB 0–1."""
    c, m, y, k = _clamp01(c), _clamp01(m), _clamp01(y), _clamp01(k)
    r = (1.0 - c) * (1.0 - k)
    g = (1.0 - m) * (1.0 - k)
    b = (1.0 - y) * (1.0 - k)
    return (_clamp01(r), _clamp01(g), _clamp01(b))


def hex_to_rgb(hex_color: str) -> Tuple[float, float, float]:
    s = (hex_color or "").strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        raise ValueError(f"Ungültige Hex-Farbe: {hex_color!r}")
    return tuple(int(s[i : i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]


def rgb_to_hex(r: float, g: float, b: float) -> str:
    return "#{:02X}{:02X}{:02X}".format(
        int(round(_clamp01(r) * 255)),
        int(round(_clamp01(g) * 255)),
        int(round(_clamp01(b) * 255)),
    )


@dataclass
class ColorSwatch:
    """Farbfeld in RGB und/oder CMYK; optional Spot-Hinweis."""

    id: str
    name: str
    rgb: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    cmyk: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    spot: bool = False
    spot_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "rgb": list(self.rgb),
            "cmyk": list(self.cmyk),
            "hex": rgb_to_hex(*self.rgb),
            "spot": self.spot,
            "spot_name": self.spot_name,
        }

    @classmethod
    def from_rgb(
        cls,
        id: str,
        name: str,
        r: float,
        g: float,
        b: float,
        *,
        spot: bool = False,
        spot_name: str = "",
    ) -> "ColorSwatch":
        return cls(
            id=id,
            name=name,
            rgb=(_clamp01(r), _clamp01(g), _clamp01(b)),
            cmyk=rgb_to_cmyk(r, g, b),
            spot=spot,
            spot_name=spot_name,
        )

    @classmethod
    def from_cmyk(
        cls,
        id: str,
        name: str,
        c: float,
        m: float,
        y: float,
        k: float,
        *,
        spot: bool = False,
        spot_name: str = "",
    ) -> "ColorSwatch":
        return cls(
            id=id,
            name=name,
            rgb=cmyk_to_rgb(c, m, y, k),
            cmyk=(_clamp01(c), _clamp01(m), _clamp01(y), _clamp01(k)),
            spot=spot,
            spot_name=spot_name,
        )

    @classmethod
    def from_hex(
        cls, id: str, name: str, hex_color: str, *, spot: bool = False
    ) -> "ColorSwatch":
        r, g, b = hex_to_rgb(hex_color)
        return cls.from_rgb(id, name, r, g, b, spot=spot)


@dataclass
class ColorPalette:
    """Benutzerdefinierte oder eingebaute Farbpalette."""

    id: str
    name: str
    mode: ColorMode = "rgb"
    swatches: List[ColorSwatch] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "mode": self.mode,
            "swatches": [s.to_dict() for s in self.swatches],
        }

    def add_swatch(self, swatch: ColorSwatch) -> None:
        self.swatches = [s for s in self.swatches if s.id != swatch.id]
        self.swatches.append(swatch)

    def get(self, swatch_id: str) -> Optional[ColorSwatch]:
        for s in self.swatches:
            if s.id == swatch_id:
                return s
        return None


def built_in_palettes() -> list[ColorPalette]:
    """Eingebaute Paletten: RGB Screen, CMYK Process, Spot-Hinweise."""
    rgb = ColorPalette(
        id="rgb_screen",
        name="RGB Bildschirm",
        mode="rgb",
        swatches=[
            ColorSwatch.from_hex("black", "Schwarz", "#000000"),
            ColorSwatch.from_hex("white", "Weiß", "#FFFFFF"),
            ColorSwatch.from_hex("accent", "Akzent Blau", "#1E5AA8"),
            ColorSwatch.from_hex("alert", "Warnung", "#C0392B"),
            ColorSwatch.from_hex("ok", "OK Grün", "#27AE60"),
            ColorSwatch.from_hex("muted", "Grau", "#7F8C8D"),
        ],
    )
    cmyk_sw: list[ColorSwatch] = []
    for sid, meta in SPOT_SWATCHES.items():
        c, m, y, k = meta["cmyk"]
        cmyk_sw.append(
            ColorSwatch.from_cmyk(
                sid, str(meta["name"]), c, m, y, k, spot=bool(meta.get("spot"))
            )
        )
    cmyk = ColorPalette(
        id="cmyk_process",
        name="CMYK Prozess",
        mode="cmyk",
        swatches=cmyk_sw,
    )
    spot = ColorPalette(
        id="spot_hints",
        name="Sonderfarben (Hinweise)",
        mode="cmyk",
        swatches=[
            ColorSwatch.from_cmyk(
                "spot_red",
                "Spot Rot (Hinweis)",
                0.0,
                0.9,
                0.8,
                0.0,
                spot=True,
                spot_name="ILD Spot Red",
            ),
            ColorSwatch.from_cmyk(
                "spot_blue",
                "Spot Blau (Hinweis)",
                0.9,
                0.5,
                0.0,
                0.0,
                spot=True,
                spot_name="ILD Spot Blue",
            ),
            ColorSwatch.from_cmyk(
                "spot_gold",
                "Spot Gold (Hinweis)",
                0.0,
                0.2,
                0.7,
                0.15,
                spot=True,
                spot_name="ILD Spot Gold",
            ),
        ],
    )
    return [rgb, cmyk, spot]


def list_palettes() -> list[dict[str, Any]]:
    return [p.to_dict() for p in built_in_palettes()]


def get_palette(palette_id: str) -> ColorPalette:
    for p in built_in_palettes():
        if p.id == palette_id:
            return p
    raise KeyError(f"Unbekannte Palette: {palette_id}")


def convert_color(
    *,
    rgb: Sequence[float] | None = None,
    cmyk: Sequence[float] | None = None,
    hex_color: str | None = None,
    to: ColorMode = "cmyk",
) -> dict[str, Any]:
    """Farbraum-Konvertierung für Scripting/UI."""
    if hex_color:
        r, g, b = hex_to_rgb(hex_color)
    elif rgb is not None and len(rgb) >= 3:
        r, g, b = float(rgb[0]), float(rgb[1]), float(rgb[2])
        # 0–255 → 0–1 wenn nötig
        if max(r, g, b) > 1.0:
            r, g, b = r / 255.0, g / 255.0, b / 255.0
    elif cmyk is not None and len(cmyk) >= 4:
        r, g, b = cmyk_to_rgb(
            float(cmyk[0]), float(cmyk[1]), float(cmyk[2]), float(cmyk[3])
        )
    else:
        raise ValueError("rgb, cmyk oder hex_color erforderlich")
    c, m, y, k = rgb_to_cmyk(r, g, b)
    out: dict[str, Any] = {
        "rgb": [r, g, b],
        "cmyk": [c, m, y, k],
        "hex": rgb_to_hex(r, g, b),
        "mode": to,
    }
    if to == "cmyk":
        out["value"] = [c, m, y, k]
    else:
        out["value"] = [r, g, b]
    return out


@dataclass
class BleedSettings:
    """Anschnitt/Bleed in mm — einheitlich oder je Seite."""

    top_mm: float = DEFAULT_BLEED_MM
    right_mm: float = DEFAULT_BLEED_MM
    bottom_mm: float = DEFAULT_BLEED_MM
    left_mm: float = DEFAULT_BLEED_MM
    enabled: bool = True
    preset: str = "standard"

    @classmethod
    def from_preset(cls, name: str = "standard") -> "BleedSettings":
        key = (name or "standard").strip().lower()
        if key not in BLEED_PRESETS_MM:
            key = "standard"
        v = float(BLEED_PRESETS_MM[key])
        return cls(
            top_mm=v,
            right_mm=v,
            bottom_mm=v,
            left_mm=v,
            enabled=v > 0,
            preset=key,
        )

    @classmethod
    def uniform(cls, mm: float, *, enabled: bool | None = None) -> "BleedSettings":
        v = max(0.0, float(mm))
        return cls(
            top_mm=v,
            right_mm=v,
            bottom_mm=v,
            left_mm=v,
            enabled=bool(enabled) if enabled is not None else v > 0,
            preset="custom",
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["top_pt"] = mm_to_pt(self.top_mm)
        d["right_pt"] = mm_to_pt(self.right_mm)
        d["bottom_pt"] = mm_to_pt(self.bottom_mm)
        d["left_pt"] = mm_to_pt(self.left_mm)
        return d

    def max_mm(self) -> float:
        return max(self.top_mm, self.right_mm, self.bottom_mm, self.left_mm)


def list_bleed_presets() -> list[dict[str, Any]]:
    return [
        {"id": k, "bleed_mm": v, "bleed_pt": mm_to_pt(v)}
        for k, v in BLEED_PRESETS_MM.items()
    ]


def apply_bleed_boxes(
    path: PathLike,
    bleed: BleedSettings | float | None = None,
    *,
    out: PathLike | None = None,
    all_pages: bool = True,
    page_index: int = 0,
) -> Path:
    """
    Setzt TrimBox = aktuelle MediaBox und erweitert MediaBox/BleedBox um Anschnitt.
    CropBox bleibt am Trim (Beschnittformat).
    """
    import pikepdf

    src = Path(path)
    dest = Path(out) if out else src
    if isinstance(bleed, (int, float)):
        settings = BleedSettings.uniform(float(bleed))
    elif bleed is None:
        settings = BleedSettings.from_preset("standard")
    else:
        settings = bleed
    if not settings.enabled or settings.max_mm() <= 0:
        # Nur TrimBox = MediaBox markieren
        overwrite = dest.resolve() == src.resolve()
        with pikepdf.open(src, allow_overwriting_input=overwrite) as pdf:
            indices = range(len(pdf.pages)) if all_pages else [page_index]
            for i in indices:
                page = pdf.pages[i]
                media = list(page.mediabox)
                page.trimbox = pikepdf.Array(media)
                page.bleedbox = pikepdf.Array(media)
            dest.parent.mkdir(parents=True, exist_ok=True)
            pdf.save(dest)
        return dest

    top = mm_to_pt(settings.top_mm)
    right = mm_to_pt(settings.right_mm)
    bottom = mm_to_pt(settings.bottom_mm)
    left = mm_to_pt(settings.left_mm)
    overwrite = dest.resolve() == src.resolve()
    with pikepdf.open(src, allow_overwriting_input=overwrite) as pdf:
        indices = range(len(pdf.pages)) if all_pages else [page_index]
        for i in indices:
            if i < 0 or i >= len(pdf.pages):
                raise IndexError(f"Seite {i} existiert nicht")
            page = pdf.pages[i]
            mb = page.mediabox
            # Trim = bisherige MediaBox (Beschnittformat)
            trim = [
                float(mb[0]),
                float(mb[1]),
                float(mb[2]),
                float(mb[3]),
            ]
            bleed_box = [
                trim[0] - left,
                trim[1] - bottom,
                trim[2] + right,
                trim[3] + top,
            ]
            page.trimbox = pikepdf.Array(trim)
            page.bleedbox = pikepdf.Array(bleed_box)
            page.mediabox = pikepdf.Array(bleed_box)
            page.cropbox = pikepdf.Array(trim)
        dest.parent.mkdir(parents=True, exist_ok=True)
        pdf.save(dest)
    return dest


def get_bleed_info(path: PathLike, page_index: int = 0) -> dict[str, Any]:
    """Bleed/Trim/Media-Boxen einer Seite lesen."""
    import pikepdf

    src = Path(path)
    with pikepdf.open(src) as pdf:
        if page_index < 0 or page_index >= len(pdf.pages):
            raise IndexError(f"Seite {page_index} existiert nicht")
        page = pdf.pages[page_index]
        media = [float(x) for x in page.mediabox]
        has_trim = page.get("/TrimBox") is not None
        has_bleed = page.get("/BleedBox") is not None
        trim = [float(x) for x in page.trimbox] if has_trim else list(media)
        bleed = [float(x) for x in page.bleedbox] if has_bleed else list(media)
        crop = (
            [float(x) for x in page.cropbox]
            if page.get("/CropBox") is not None
            else list(media)
        )

    def _mm(box: list[float]) -> dict[str, float]:
        return {
            "left_mm": pt_to_mm(max(0.0, trim[0] - box[0])),
            "bottom_mm": pt_to_mm(max(0.0, trim[1] - box[1])),
            "right_mm": pt_to_mm(max(0.0, box[2] - trim[2])),
            "top_mm": pt_to_mm(max(0.0, box[3] - trim[3])),
        }

    return {
        "path": str(src.resolve()),
        "page": page_index + 1,
        "mediabox": media,
        "trimbox": trim,
        "bleedbox": bleed,
        "cropbox": crop,
        "bleed_from_trim_mm": _mm(bleed),
        "has_trimbox": has_trim,
        "has_bleedbox": has_bleed,
    }


@dataclass
class DocumentLayer:
    """Dokument-Ebene für Hintergrund / Bilder / Text."""

    id: LayerName
    name: str
    visible: bool = True
    locked: bool = False
    z_index: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_layers() -> list[DocumentLayer]:
    return [
        DocumentLayer(id="background", name=LAYER_LABELS["background"], z_index=0),
        DocumentLayer(id="images", name=LAYER_LABELS["images"], z_index=1),
        DocumentLayer(id="text", name=LAYER_LABELS["text"], z_index=2),
    ]


def list_layers() -> list[dict[str, Any]]:
    return [layer.to_dict() for layer in default_layers()]


def normalize_layer(name: str | None) -> LayerName:
    key = (name or "text").strip().lower()
    aliases = {
        "bg": "background",
        "hintergrund": "background",
        "image": "images",
        "bilder": "images",
        "img": "images",
        "txt": "text",
        "texte": "text",
    }
    key = aliases.get(key, key)
    if key not in LAYER_ORDER:
        raise ValueError(f"Unbekannte Ebene: {name!r} (erlaubt: {', '.join(LAYER_ORDER)})")
    return key  # type: ignore[return-value]


def organize_by_layer(
    frames: Sequence[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Rahmen nach Ebene gruppieren (fehlend → text bzw. images je kind)."""
    out: dict[str, list[dict[str, Any]]] = {k: [] for k in LAYER_ORDER}
    for fr in frames:
        kind = str(fr.get("kind") or "").lower()
        layer = fr.get("layer")
        if not layer:
            layer = "images" if kind == "image" else "text"
        try:
            lid = normalize_layer(str(layer))
        except ValueError:
            lid = "text"
        row = dict(fr)
        row["layer"] = lid
        out[lid].append(row)
    return out


Severity = Literal["error", "warning", "info"]


@dataclass
class PreflightIssue:
    code: str
    severity: Severity
    message: str
    page: Optional[int] = None
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class PreflightReport:
    path: str
    ok: bool
    issues: List[PreflightIssue] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "ok": self.ok,
            "issues": [i.to_dict() for i in self.issues],
            "summary": self.summary,
            "error_count": sum(1 for i in self.issues if i.severity == "error"),
            "warning_count": sum(1 for i in self.issues if i.severity == "warning"),
        }


def _font_names_from_page(page) -> set[str]:
    names: set[str] = set()
    try:
        resources = page.get("/Resources")
        if resources is None:
            return names
        fonts = resources.get("/Font")
        if fonts is None:
            return names
        for _key, font in fonts.items():
            try:
                base = font.get("/BaseFont")
                if base is not None:
                    names.add(str(base).lstrip("/"))
                # Type0 descendant
                if font.get("/DescendantFonts") is not None:
                    for desc in font["/DescendantFonts"]:
                        b2 = desc.get("/BaseFont")
                        if b2 is not None:
                            names.add(str(b2).lstrip("/"))
            except Exception:
                continue
    except Exception:
        pass
    return names


def _font_is_embedded(font_obj) -> bool:
    try:
        if font_obj.get("/FontDescriptor") is not None:
            fd = font_obj["/FontDescriptor"]
            for key in (
                "/FontFile",
                "/FontFile2",
                "/FontFile3",
            ):
                if fd.get(key) is not None:
                    return True
        if font_obj.get("/DescendantFonts") is not None:
            for desc in font_obj["/DescendantFonts"]:
                if _font_is_embedded(desc):
                    return True
    except Exception:
        return False
    return False


def _collect_font_issues(pdf) -> list[PreflightIssue]:
    issues: list[PreflightIssue] = []
    seen_missing: set[str] = set()
    standard14 = {
        "Helvetica",
        "Helvetica-Bold",
        "Helvetica-Oblique",
        "Helvetica-BoldOblique",
        "Times-Roman",
        "Times-Bold",
        "Times-Italic",
        "Times-BoldItalic",
        "Courier",
        "Courier-Bold",
        "Courier-Oblique",
        "Courier-BoldOblique",
        "Symbol",
        "ZapfDingbats",
    }
    for idx, page in enumerate(pdf.pages):
        try:
            resources = page.get("/Resources")
            if resources is None:
                continue
            fonts = resources.get("/Font")
            if fonts is None:
                continue
            for _key, font in fonts.items():
                try:
                    base = font.get("/BaseFont")
                    name = str(base).lstrip("/") if base is not None else str(_key).lstrip("/")
                    # Subset-Prefix XXXXXX+FontName
                    plain = name.split("+", 1)[-1] if "+" in name else name
                    embedded = _font_is_embedded(font)
                    if not embedded and plain not in standard14 and name not in seen_missing:
                        seen_missing.add(name)
                        issues.append(
                            PreflightIssue(
                                code="missing_font",
                                severity="error",
                                message=f"Schrift nicht eingebettet: {name}",
                                page=idx + 1,
                                detail={"font": name, "base": plain},
                            )
                        )
                except Exception:
                    continue
        except Exception:
            continue
    return issues


def _image_dpi_estimate(img_obj, page_width_pt: float, page_height_pt: float) -> Optional[float]:
    """Grobe DPI aus Pixelgröße und Zeichenrechteck (falls verfügbar)."""
    try:
        w = int(img_obj.get("/Width") or 0)
        h = int(img_obj.get("/Height") or 0)
        if w <= 0 or h <= 0:
            return None
        # Ohne Matrix: annehmen, Bild füllt Seite (konservativ niedrig)
        dpi_x = w / max(page_width_pt / 72.0, 0.01)
        dpi_y = h / max(page_height_pt / 72.0, 0.01)
        return min(dpi_x, dpi_y)
    except Exception:
        return None


def _collect_image_issues(
    pdf, *, min_dpi: float = DEFAULT_MIN_IMAGE_DPI
) -> list[PreflightIssue]:
    issues: list[PreflightIssue] = []
    for idx, page in enumerate(pdf.pages):
        try:
            mb = page.mediabox
            pw = float(mb[2]) - float(mb[0])
            ph = float(mb[3]) - float(mb[1])
            resources = page.get("/Resources")
            if resources is None:
                continue
            xobj = resources.get("/XObject")
            if xobj is None:
                continue
            for key, obj in xobj.items():
                try:
                    if str(obj.get("/Subtype")) != "/Image":
                        continue
                    dpi = _image_dpi_estimate(obj, pw, ph)
                    w = int(obj.get("/Width") or 0)
                    h = int(obj.get("/Height") or 0)
                    if dpi is not None and dpi < float(min_dpi):
                        issues.append(
                            PreflightIssue(
                                code="low_image_resolution",
                                severity="warning",
                                message=(
                                    f"Bildauflösung niedrig (~{dpi:.0f} dpi < {min_dpi:.0f}): "
                                    f"{key}"
                                ),
                                page=idx + 1,
                                detail={
                                    "name": str(key),
                                    "width_px": w,
                                    "height_px": h,
                                    "dpi_est": round(dpi, 1),
                                    "min_dpi": float(min_dpi),
                                },
                            )
                        )
                except Exception:
                    continue
        except Exception:
            continue
    return issues


def _collect_bleed_issues(pdf) -> list[PreflightIssue]:
    issues: list[PreflightIssue] = []
    for idx, page in enumerate(pdf.pages):
        if page.get("/BleedBox") is None and page.get("/TrimBox") is None:
            issues.append(
                PreflightIssue(
                    code="no_bleed",
                    severity="info",
                    message="Keine BleedBox/TrimBox gesetzt (Anschnitt fehlt)",
                    page=idx + 1,
                )
            )
    return issues


def run_preflight(
    path: PathLike,
    *,
    min_image_dpi: float = DEFAULT_MIN_IMAGE_DPI,
    require_bleed: bool = False,
    color_mode: ColorMode | None = None,
) -> PreflightReport:
    """Preflight: fehlende Schriften, niedrige Bildauflösung, Bleed-Hinweise."""
    import pikepdf

    src = Path(path)
    issues: list[PreflightIssue] = []
    page_count = 0
    with pikepdf.open(src) as pdf:
        page_count = len(pdf.pages)
        issues.extend(_collect_font_issues(pdf))
        issues.extend(_collect_image_issues(pdf, min_dpi=min_image_dpi))
        bleed_issues = _collect_bleed_issues(pdf)
        if require_bleed:
            for bi in bleed_issues:
                bi.severity = "warning"
                bi.message = "Anschnitt/Bleed fehlt (für Druck empfohlen)"
            issues.extend(bleed_issues)
        else:
            issues.extend(bleed_issues)
        if color_mode == "cmyk":
            # Hinweis: RGB-Bilder in CMYK-Workflow
            for idx, page in enumerate(pdf.pages):
                try:
                    resources = page.get("/Resources")
                    if resources is None:
                        continue
                    xobj = resources.get("/XObject")
                    if xobj is None:
                        continue
                    for key, obj in xobj.items():
                        try:
                            if str(obj.get("/Subtype")) != "/Image":
                                continue
                            cs = obj.get("/ColorSpace")
                            cs_s = str(cs) if cs is not None else ""
                            if "RGB" in cs_s or cs_s in ("/DeviceRGB",):
                                issues.append(
                                    PreflightIssue(
                                        code="rgb_in_cmyk_workflow",
                                        severity="warning",
                                        message=f"RGB-Bild in CMYK-Workflow: {key}",
                                        page=idx + 1,
                                        detail={"name": str(key), "colorspace": cs_s},
                                    )
                                )
                        except Exception:
                            continue
                except Exception:
                    continue

    errors = sum(1 for i in issues if i.severity == "error")
    warnings = sum(1 for i in issues if i.severity == "warning")
    report = PreflightReport(
        path=str(src.resolve()),
        ok=errors == 0,
        issues=issues,
        summary={
            "pages": page_count,
            "errors": errors,
            "warnings": warnings,
            "infos": sum(1 for i in issues if i.severity == "info"),
            "min_image_dpi": float(min_image_dpi),
            "color_mode": color_mode,
            "require_bleed": require_bleed,
        },
    )
    return report


def preflight_to_text(report: PreflightReport) -> str:
    lines = [
        f"Preflight: {report.path}",
        f"Status: {'OK' if report.ok else 'FEHLER'}",
        (
            f"Seiten={report.summary.get('pages')}  "
            f"Fehler={report.summary.get('errors')}  "
            f"Warnungen={report.summary.get('warnings')}  "
            f"Hinweise={report.summary.get('infos')}"
        ),
        "",
    ]
    if not report.issues:
        lines.append("Keine Probleme gefunden.")
    for i in report.issues:
        page = f" S.{i.page}" if i.page else ""
        lines.append(f"[{i.severity.upper()}] {i.code}{page}: {i.message}")
    return "\n".join(lines) + "\n"


def _set_pdfx_metadata(
    pdf,
    *,
    profile: PdfxProfile,
    title: str | None = None,
    output_condition: str = "FOGRA39",
) -> None:
    """GTS_PDFXVersion + OutputIntent (näherungsweise, druckreif)."""
    import pikepdf
    from pikepdf import Dictionary, Name, Array

    if profile == "pdfx1a":
        gts = "PDF/X-1a:2001"
    elif profile == "pdfx4":
        gts = "PDF/X-4"
    else:
        gts = "PDF/X-ready"

    with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
        if title:
            meta["dc:title"] = title
        try:
            meta["pdfxid:GTS_PDFXVersion"] = gts
        except Exception:
            pass

    # Info-Dict Fallback
    try:
        if pdf.docinfo is None:
            pdf.docinfo = Dictionary()
        pdf.docinfo[Name("/GTS_PDFXVersion")] = gts
        if title:
            pdf.docinfo[Name("/Title")] = title
    except Exception:
        pass

    # Minimaler OutputIntent ohne eingebettetes ICC (Hinweis-Profil)
    try:
        oi = Dictionary(
            {
                "/Type": Name("/OutputIntent"),
                "/S": Name("/GTS_PDFX"),
                "/OutputConditionIdentifier": output_condition,
                "/Info": f"ILD {gts} OutputIntent ({output_condition})",
                "/RegistryName": "http://www.color.org",
            }
        )
        existing = pdf.Root.get("/OutputIntents")
        if existing is None:
            pdf.Root[Name("/OutputIntents")] = Array([oi])
        else:
            arr = Array(list(existing))
            arr.append(oi)
            pdf.Root[Name("/OutputIntents")] = arr
    except Exception:
        pass


def export_pdfx(
    path: PathLike,
    out: PathLike,
    *,
    profile: PdfxProfile = "pdfx4",
    bleed_mm: float | None = DEFAULT_BLEED_MM,
    title: str | None = None,
    run_preflight_first: bool = False,
    min_image_dpi: float = PRINT_MIN_IMAGE_DPI,
) -> dict[str, Any]:
    """
    Druckreifes PDF exportieren: Bleed setzen + PDF/X-Metadaten/OutputIntent.
    Bestehenden PDF-Inhalt kopieren (kein voller Color-Convert-Engine).
    """
    import pikepdf
    import shutil

    src = Path(path)
    dest = Path(out)
    dest.parent.mkdir(parents=True, exist_ok=True)

    preflight_data = None
    if run_preflight_first:
        report = run_preflight(
            src, min_image_dpi=min_image_dpi, require_bleed=False, color_mode="cmyk"
        )
        preflight_data = report.to_dict()

    # Kopie + Bleed + Metadaten
    if dest.resolve() != src.resolve():
        shutil.copy2(src, dest)
    else:
        # in-place: zuerst temp
        pass

    if bleed_mm is not None and float(bleed_mm) > 0:
        apply_bleed_boxes(dest, BleedSettings.uniform(float(bleed_mm)), out=dest)

    with pikepdf.open(dest, allow_overwriting_input=True) as pdf:
        _set_pdfx_metadata(pdf, profile=profile, title=title)
        pdf.save(dest)

    result: dict[str, Any] = {
        "out": str(dest.resolve()),
        "profile": profile,
        "bleed_mm": float(bleed_mm) if bleed_mm is not None else 0.0,
        "source": str(src.resolve()),
        "pdfx": True,
        "print_ready": True,
    }
    if preflight_data is not None:
        result["preflight"] = preflight_data
    return result


def export_print_ready(
    path: PathLike,
    out: PathLike,
    *,
    bleed_mm: float = DEFAULT_BLEED_MM,
    title: str | None = None,
) -> dict[str, Any]:
    """Alias: print-ready PDF (PDF/X-ähnlich) — 2.6.18."""
    return export_pdfx(
        path,
        out,
        profile="print_ready",
        bleed_mm=bleed_mm,
        title=title,
        run_preflight_first=False,
    )


# Sidecar für Dokument-Farb-/Bleed-Einstellungen
PRINT_SETTINGS_SCHEMA = "ildprint-v1"


@dataclass
class PrintSettings:
    """Persistierbare Druck-/Farb-Einstellungen (Sidecar)."""

    color_mode: ColorMode = "rgb"
    bleed: BleedSettings = field(default_factory=lambda: BleedSettings.from_preset("standard"))
    palette_id: str = "rgb_screen"
    custom_swatches: List[ColorSwatch] = field(default_factory=list)
    layers: List[DocumentLayer] = field(default_factory=default_layers)
    min_image_dpi: float = DEFAULT_MIN_IMAGE_DPI
    pdfx_profile: PdfxProfile = "pdfx4"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": PRINT_SETTINGS_SCHEMA,
            "color_mode": self.color_mode,
            "bleed": self.bleed.to_dict(),
            "palette_id": self.palette_id,
            "custom_swatches": [s.to_dict() for s in self.custom_swatches],
            "layers": [layer.to_dict() for layer in self.layers],
            "min_image_dpi": self.min_image_dpi,
            "pdfx_profile": self.pdfx_profile,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PrintSettings":
        bleed_data = data.get("bleed") or {}
        bleed = BleedSettings(
            top_mm=float(bleed_data.get("top_mm", DEFAULT_BLEED_MM)),
            right_mm=float(bleed_data.get("right_mm", DEFAULT_BLEED_MM)),
            bottom_mm=float(bleed_data.get("bottom_mm", DEFAULT_BLEED_MM)),
            left_mm=float(bleed_data.get("left_mm", DEFAULT_BLEED_MM)),
            enabled=bool(bleed_data.get("enabled", True)),
            preset=str(bleed_data.get("preset") or "standard"),
        )
        swatches: list[ColorSwatch] = []
        for s in data.get("custom_swatches") or []:
            rgb = s.get("rgb") or [0, 0, 0]
            cmyk = s.get("cmyk") or rgb_to_cmyk(rgb[0], rgb[1], rgb[2])
            swatches.append(
                ColorSwatch(
                    id=str(s.get("id") or "sw"),
                    name=str(s.get("name") or "Swatch"),
                    rgb=(float(rgb[0]), float(rgb[1]), float(rgb[2])),
                    cmyk=(
                        float(cmyk[0]),
                        float(cmyk[1]),
                        float(cmyk[2]),
                        float(cmyk[3]),
                    ),
                    spot=bool(s.get("spot", False)),
                    spot_name=str(s.get("spot_name") or ""),
                )
            )
        layers_raw = data.get("layers")
        layers = default_layers()
        if layers_raw:
            rebuilt: list[DocumentLayer] = []
            for layer in layers_raw:
                try:
                    lid = normalize_layer(str(layer.get("id")))
                except ValueError:
                    continue
                rebuilt.append(
                    DocumentLayer(
                        id=lid,
                        name=str(layer.get("name") or LAYER_LABELS.get(lid, lid)),
                        visible=bool(layer.get("visible", True)),
                        locked=bool(layer.get("locked", False)),
                        z_index=int(layer.get("z_index") or 0),
                    )
                )
            if rebuilt:
                layers = rebuilt
        mode = str(data.get("color_mode") or "rgb").lower()
        if mode not in ("rgb", "cmyk"):
            mode = "rgb"
        profile = str(data.get("pdfx_profile") or "pdfx4").lower()
        if profile not in ("pdfx1a", "pdfx4", "print_ready"):
            profile = "pdfx4"
        return cls(
            color_mode=mode,  # type: ignore[arg-type]
            bleed=bleed,
            palette_id=str(data.get("palette_id") or "rgb_screen"),
            custom_swatches=swatches,
            layers=layers,
            min_image_dpi=float(data.get("min_image_dpi") or DEFAULT_MIN_IMAGE_DPI),
            pdfx_profile=profile,  # type: ignore[arg-type]
        )


def print_settings_path_for(pdf_path: PathLike) -> Path:
    p = Path(pdf_path)
    return p.with_suffix(p.suffix + ".ildprint.json")


def load_print_settings(pdf_path: PathLike) -> PrintSettings:
    side = print_settings_path_for(pdf_path)
    if not side.is_file():
        return PrintSettings()
    try:
        data = json.loads(side.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return PrintSettings()
        return PrintSettings.from_dict(data)
    except Exception:
        return PrintSettings()


def save_print_settings(pdf_path: PathLike, settings: PrintSettings) -> Path:
    side = print_settings_path_for(pdf_path)
    side.write_text(
        json.dumps(settings.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return side
