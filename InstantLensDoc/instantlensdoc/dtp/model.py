"""DTP-Dokumentmodell: Seiten, Musterseiten, Rahmen, Verkettung, Styles, Ebenen."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from .geometry import column_rects, snap_point, snap_to_guide_mm, snap_baseline
from .presets import BOOK_PRESETS_MM, apply_book_preset, mm_to_pt


def _nid() -> str:
    return uuid4().hex[:10]


@dataclass
class PageGeometry:
    name: str = "A4"
    width_pt: float = 595.28
    height_pt: float = 841.89
    margin_top_pt: float = 56.7
    margin_bottom_pt: float = 70.87
    margin_left_pt: float = 70.87
    margin_right_pt: float = 56.7
    bleed_pt: float = 8.5
    columns: int = 1
    gutter_pt: float = 14.17
    baseline_grid_mm: float = 4.233

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "PageGeometry":
        d = dict(data or {})
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: d[k] for k in d if k in known})


@dataclass
class DtpGuide:
    orientation: str = "vertical"  # vertical | horizontal
    position_pt: float = 0.0
    locked: bool = False
    id: str = field(default_factory=_nid)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DtpLayer:
    id: str = field(default_factory=_nid)
    name: str = "Ebene"
    visible: bool = True
    locked: bool = False
    z: int = 0
    blend_mode: str = "normal"
    opacity: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StyleSheet:
    """Absatz-/Zeichen-/Objektformate."""

    id: str = "body"
    kind: str = "paragraph"  # paragraph | character | object
    font_family: str = "serif"
    font_size: float = 11.0
    weight: int = 400
    stretch: int = 100
    italic: bool = False
    tracking: float = 0.0
    kerning: float = 0.0
    leading: float = 1.2
    color: str = "#111111"
    alignment: str = "left"
    fill: str = ""
    stroke: str = "#333333"
    stroke_width: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StyleSheet":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: data[k] for k in data if k in known})


def default_styles() -> dict[str, StyleSheet]:
    return {
        "body": StyleSheet(id="body", kind="paragraph", font_size=11.0, leading=1.25),
        "h1": StyleSheet(
            id="h1", kind="paragraph", font_size=18.0, weight=700, leading=1.15
        ),
        "h2": StyleSheet(
            id="h2", kind="paragraph", font_size=14.0, weight=600, leading=1.2
        ),
        "caption": StyleSheet(
            id="caption", kind="paragraph", font_size=9.0, italic=True, color="#444444"
        ),
        "emphasis": StyleSheet(
            id="emphasis", kind="character", font_size=11.0, italic=True, weight=600
        ),
        "object": StyleSheet(id="object", kind="object", fill="#D0E8FF", stroke="#1A5276"),
    }


@dataclass
class EnvelopeMesh:
    """4-Punkt-Envelope (TL, TR, BR, BL) in Rahmen-Lokalcoords 0..w / 0..h."""

    corners: list[list[float]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"corners": [list(c) for c in self.corners]}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Optional["EnvelopeMesh"]:
        if not data:
            return None
        corners = data.get("corners") or []
        if len(corners) != 4:
            return None
        return cls(corners=[[float(a), float(b)] for a, b in corners])


@dataclass
class ExtrudeSpec:
    depth: float = 18.0
    angle_deg: float = 32.0
    shading: float = 0.35

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Optional["ExtrudeSpec"]:
        if not data:
            return None
        return cls(
            depth=float(data.get("depth", 18.0)),
            angle_deg=float(data.get("angle_deg", 32.0)),
            shading=float(data.get("shading", 0.35)),
        )


@dataclass
class DtpFrame:
    id: str = field(default_factory=_nid)
    kind: str = "text"  # text | image | render | shape | ink | stamp
    page: int = 0
    x: float = 40.0
    y: float = 40.0
    width: float = 200.0
    height: float = 80.0
    rotation: float = 0.0
    layer_id: str = ""
    z: int = 0
    locked: bool = False
    group_id: str = ""
    next_id: Optional[str] = None
    text: str = ""
    rich_html: str = ""
    image_path: str = ""
    shape: str = "rectangle"  # rectangle|ellipse|line|arrow|triangle
    style_id: str = "body"
    wrap: str = "none"  # none|bounding_box|jump_object|contour
    wrap_padding: float = 8.0
    fill: str = ""
    stroke: str = "#333333"
    stroke_width: float = 1.0
    font_family: str = ""
    font_size: float = 0.0
    font_weight: int = 0
    font_stretch: int = 0
    font_axes: dict[str, float] = field(default_factory=dict)
    envelope: Optional[EnvelopeMesh] = None
    extrude: Optional[ExtrudeSpec] = None
    ink_points: list[list[float]] = field(default_factory=list)  # [x,y,pressure?]
    master: bool = False
    path_kind: str = ""  # "" | ellipse | line
    as_outlines: bool = False
    clip_id: str = ""
    opacity: float = 1.0
    fill_kind: str = "solid"  # solid | linear | radial
    fill_to: str = ""
    fill_angle: float = 90.0
    shadow: bool = False
    shadow_dx: float = 3.0
    shadow_dy: float = 3.0
    shadow_color: str = "#00000066"
    stamp_text_only: bool = False
    stamp_outline: bool = False
    content_id: str = ""
    symbol_id: str = ""
    linked: bool = False
    weld_path: list = field(default_factory=list)
    color_space: str = "rgb"
    spot_name: str = ""
    kerning_pairs: dict[str, float] = field(default_factory=dict)

    def move(self, x: float, y: float) -> None:
        if self.locked:
            raise ValueError(f"Rahmen {self.id} ist gesperrt")
        self.x, self.y = float(x), float(y)

    def resize(self, width: float, height: float) -> None:
        if self.locked:
            raise ValueError(f"Rahmen {self.id} ist gesperrt")
        self.width = max(6.0, float(width))
        self.height = max(6.0, float(height))

    def rect(self) -> tuple[float, float, float, float]:
        return (self.x, self.y, self.width, self.height)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.envelope is not None:
            d["envelope"] = self.envelope.to_dict()
        if self.extrude is not None:
            d["extrude"] = self.extrude.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DtpFrame":
        raw = dict(data)
        env = EnvelopeMesh.from_dict(raw.pop("envelope", None) if isinstance(raw.get("envelope"), dict) else None)
        ext = ExtrudeSpec.from_dict(raw.pop("extrude", None) if isinstance(raw.get("extrude"), dict) else None)
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        fr = cls(**{k: raw[k] for k in raw if k in known and k not in ("envelope", "extrude")})
        fr.envelope = env
        fr.extrude = ext
        return fr


@dataclass
class DtpMaster:
    id: str = field(default_factory=_nid)
    name: str = "Standard"
    header_text: str = "{title}"
    footer_text: str = "{n} / {total}"
    include_page_numbers: bool = True
    odd_even: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def header_for(
        self, page_1based: int, total: int, *, title: str = "", number_system: str = "latin"
    ) -> str:
        return _subst(self.header_text, page_1based, total, title, number_system)

    def footer_for(
        self, page_1based: int, total: int, *, title: str = "", number_system: str = "latin"
    ) -> str:
        txt = self.footer_text
        if self.include_page_numbers and "{n}" not in txt:
            txt = (txt + "  {n} / {total}").strip()
        return _subst(txt, page_1based, total, title, number_system)


def _subst(template: str, n: int, total: int, title: str, number_system: str = "latin") -> str:
    from .type_extras import format_number

    ns = format_number(n, number_system)
    ts = format_number(total, number_system)
    return (
        (template or "")
        .replace("{n}", ns)
        .replace("{page}", ns)
        .replace("{total}", ts)
        .replace("{title}", title or "")
    )


@dataclass
class DtpDocument:
    geometry: PageGeometry = field(default_factory=PageGeometry)
    page_count: int = 1
    frames: list[DtpFrame] = field(default_factory=list)
    guides: list[DtpGuide] = field(default_factory=list)
    layers: list[DtpLayer] = field(default_factory=list)
    styles: dict[str, StyleSheet] = field(default_factory=default_styles)
    masters: list[DtpMaster] = field(default_factory=lambda: [DtpMaster()])
    page_master: list[str] = field(default_factory=list)
    grid_spacing_mm: float = 5.0
    grid_visible: bool = True
    grid_snap: bool = True
    guides_snap: bool = True
    title: str = "Ohne Titel"
    current_page: int = 0
    active_story_id: str = ""
    library: Any = None
    footnotes: list = field(default_factory=list)
    endnotes: list = field(default_factory=list)
    variables: dict[str, str] = field(default_factory=dict)
    cross_refs: list = field(default_factory=list)
    widgets: list = field(default_factory=list)
    number_system: str = "latin"
    ruler_unit: str = "mm"

    def __post_init__(self) -> None:
        if not self.layers:
            self.layers = [
                DtpLayer(id="background", name="Hintergrund", z=0),
                DtpLayer(id="images", name="Bilder", z=1),
                DtpLayer(id="text", name="Text", z=2),
            ]
        if not self.styles:
            self.styles = default_styles()
        if not self.masters:
            self.masters = [DtpMaster()]
        if self.library is None:
            from .assets import AssetLibrary

            self.library = AssetLibrary()
        self._sync_page_master()

    def _sync_page_master(self) -> None:
        mid = self.masters[0].id if self.masters else ""
        while len(self.page_master) < self.page_count:
            self.page_master.append(mid)
        self.page_master = self.page_master[: self.page_count]

    def grid_pt(self) -> float:
        return mm_to_pt(max(1.0, float(self.grid_spacing_mm)))

    def frame_by_id(self, frame_id: str) -> Optional[DtpFrame]:
        for f in self.frames:
            if f.id == frame_id:
                return f
        return None

    def frames_on_page(self, page: int) -> list[DtpFrame]:
        return [f for f in self.frames if int(f.page) == int(page)]

    def sorted_frames(self, page: int | None = None) -> list[DtpFrame]:
        items = self.frames if page is None else self.frames_on_page(page)
        layer_z = {ly.id: ly.z for ly in self.layers}
        vis = {ly.id: ly.visible for ly in self.layers}

        def key(f: DtpFrame) -> tuple[int, int, str]:
            return (layer_z.get(f.layer_id, 0), int(f.z), f.id)

        return [f for f in sorted(items, key=key) if vis.get(f.layer_id, True)]

    def add_page(self) -> int:
        self.page_count += 1
        self._sync_page_master()
        return self.page_count - 1

    def add_guide(self, orientation: str, position_pt: float) -> DtpGuide:
        g = DtpGuide(orientation=orientation, position_pt=float(position_pt))
        self.guides.append(g)
        return g

    def convert_frame(
        self, frame_id: str, kind: str, *, shape: str | None = None
    ) -> DtpFrame:
        """Select-then-tool: Rahmenart auf die Auswahl anwenden; Geometrie bleibt."""
        fr = self.frame_by_id(frame_id)
        if fr is None:
            raise KeyError(frame_id)
        k = (kind or fr.kind or "text").lower()
        if k not in ("text", "image", "render", "shape"):
            raise ValueError(f"unbekannte Rahmenart: {kind}")
        if fr.kind == "text" and k != "text":
            for other in self.frames:
                if other.next_id == fr.id:
                    other.next_id = fr.next_id
                    break
            fr.next_id = None
        fr.kind = k
        if k == "shape":
            sk = (shape or fr.shape or "rectangle").lower()
            if sk not in ("rectangle", "ellipse", "line", "arrow", "triangle"):
                sk = "rectangle"
            fr.shape = sk
            if not (fr.fill or "").strip():
                fr.fill = "#D0E8FF"
            if not fr.layer_id:
                fr.layer_id = "images"
        elif k == "text":
            fr.layer_id = "text"
            if fr.style_id not in self.styles:
                fr.style_id = "body"
        elif k in ("image", "render"):
            if not fr.layer_id:
                fr.layer_id = "images"
        return fr

    def add_text_frame(
        self,
        text: str = "",
        *,
        x: float | None = None,
        y: float | None = None,
        width: float | None = None,
        height: float | None = None,
        page: int = 0,
        style_id: str = "body",
        column: int | None = None,
    ) -> DtpFrame:
        cols = column_rects(
            width_pt=self.geometry.width_pt,
            height_pt=self.geometry.height_pt,
            margin_left_pt=self.geometry.margin_left_pt,
            margin_right_pt=self.geometry.margin_right_pt,
            margin_top_pt=self.geometry.margin_top_pt,
            margin_bottom_pt=self.geometry.margin_bottom_pt,
            columns=self.geometry.columns,
            gutter_pt=self.geometry.gutter_pt,
        )
        col = cols[min(len(cols) - 1, max(0, int(column or 0)))]
        fr = DtpFrame(
            kind="text",
            page=max(0, int(page)),
            x=float(x if x is not None else col["x"]),
            y=float(y if y is not None else col["y"]),
            width=float(width if width is not None else col["width"]),
            height=float(height if height is not None else min(180.0, col["height"])),
            text=text,
            style_id=style_id,
            layer_id="text",
            z=len(self.frames),
        )
        self.frames.append(fr)
        self.page_count = max(self.page_count, fr.page + 1)
        self._sync_page_master()
        return fr

    def add_image_frame(
        self,
        path: str = "",
        *,
        x: float = 80.0,
        y: float = 200.0,
        width: float = 200.0,
        height: float = 140.0,
        page: int = 0,
        wrap: str = "bounding_box",
    ) -> DtpFrame:
        fr = DtpFrame(
            kind="image",
            page=max(0, int(page)),
            x=x,
            y=y,
            width=width,
            height=height,
            image_path=path,
            wrap=wrap,
            layer_id="images",
            z=len(self.frames),
        )
        self.frames.append(fr)
        self.page_count = max(self.page_count, fr.page + 1)
        return fr

    def add_render_frame(
        self,
        path: str = "",
        *,
        x: float = 80.0,
        y: float = 200.0,
        width: float = 200.0,
        height: float = 140.0,
        page: int = 0,
    ) -> DtpFrame:
        fr = DtpFrame(
            kind="render",
            page=max(0, int(page)),
            x=x,
            y=y,
            width=width,
            height=height,
            image_path=path,
            layer_id="images",
            z=len(self.frames),
        )
        self.frames.append(fr)
        self.page_count = max(self.page_count, fr.page + 1)
        return fr

    def add_shape(
        self,
        shape: str = "rectangle",
        *,
        x: float = 80.0,
        y: float = 80.0,
        width: float = 120.0,
        height: float = 80.0,
        page: int = 0,
        fill: str = "#D0E8FF",
        stroke: str = "#1A5276",
    ) -> DtpFrame:
        sk = (shape or "rectangle").lower()
        if sk not in ("rectangle", "ellipse", "line", "arrow", "triangle"):
            sk = "rectangle"
        fr = DtpFrame(
            kind="shape",
            shape=sk,
            page=max(0, int(page)),
            x=x,
            y=y,
            width=width,
            height=height,
            fill=fill,
            stroke=stroke,
            wrap="bounding_box",
            layer_id="images",
            style_id="object",
            z=len(self.frames),
        )
        self.frames.append(fr)
        return fr

    def add_stamp(
        self,
        text: str = "GENEHMIGT",
        *,
        x: float = 80.0,
        y: float = 80.0,
        width: float = 140.0,
        height: float = 44.0,
        page: int = 0,
        color: str = "#1E8449",
    ) -> DtpFrame:
        fr = DtpFrame(
            kind="stamp",
            page=max(0, int(page)),
            x=x,
            y=y,
            width=width,
            height=height,
            text=text or "STEMPEL",
            fill="",
            stroke=color or "#1E8449",
            stroke_width=3.0,
            wrap="none",
            layer_id="text",
            style_id="object",
            z=len(self.frames),
        )
        self.frames.append(fr)
        self.page_count = max(self.page_count, fr.page + 1)
        return fr

    def add_ink_stroke(self, points: list[list[float]], *, page: int = 0) -> DtpFrame:
        xs = [p[0] for p in points] or [0.0]
        ys = [p[1] for p in points] or [0.0]
        x0, y0 = min(xs), min(ys)
        fr = DtpFrame(
            kind="ink",
            page=page,
            x=x0,
            y=y0,
            width=max(4.0, max(xs) - x0),
            height=max(4.0, max(ys) - y0),
            ink_points=[[float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else 0.6] for p in points],
            layer_id="images",
            z=len(self.frames),
        )
        self.frames.append(fr)
        return fr

    def group_frames(self, frame_ids: list[str], group_id: str | None = None) -> tuple[int, str]:
        """Auswahl gruppieren (≥2). Gemeinsame group_id; Rückgabe (Anzahl, id)."""
        ids = self.expand_group_ids([str(i) for i in frame_ids if i])
        seen: set[str] = set()
        targets: list[DtpFrame] = []
        for fid in ids:
            if fid in seen:
                continue
            fr = self.frame_by_id(fid)
            if fr is None:
                continue
            seen.add(fid)
            targets.append(fr)
        if len(targets) < 2:
            return 0, ""
        gid = str(group_id or "").strip() or _nid()
        for fr in targets:
            fr.group_id = gid
        return len(targets), gid

    def ungroup_frames(self, frame_ids: list[str] | None = None) -> int:
        """Gruppierung aufheben. Ohne IDs: alle Rahmen mit group_id."""
        if frame_ids:
            wanted = {str(i) for i in frame_ids if i}
            gids = {
                str(fr.group_id or "").strip()
                for fr in self.frames
                if fr.id in wanted and str(fr.group_id or "").strip()
            }
            targets = [fr for fr in self.frames if str(fr.group_id or "").strip() in gids]
        else:
            targets = [fr for fr in self.frames if str(fr.group_id or "").strip()]
        n = 0
        for fr in targets:
            if fr.group_id:
                fr.group_id = ""
                n += 1
        return n

    def ids_in_group(self, group_id: str) -> list[str]:
        gid = str(group_id or "").strip()
        if not gid:
            return []
        return [fr.id for fr in self.frames if str(fr.group_id or "").strip() == gid]

    def expand_group_ids(self, frame_ids: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for raw in frame_ids or []:
            fid = str(raw or "").strip()
            if not fid or fid in seen:
                continue
            fr = self.frame_by_id(fid)
            gid = str(getattr(fr, "group_id", "") or "").strip() if fr is not None else ""
            if gid:
                for mid in self.ids_in_group(gid):
                    if mid not in seen:
                        seen.add(mid)
                        out.append(mid)
            else:
                seen.add(fid)
                out.append(fid)
        return out

    def link_frames(self, from_id: str, to_id: str) -> None:
        src, dst = self.frame_by_id(from_id), self.frame_by_id(to_id)
        if src is None or dst is None:
            raise KeyError("Rahmen nicht gefunden")
        if from_id == to_id:
            raise ValueError("Selbstverkettung")
        seen = {from_id}
        cur = to_id
        while cur:
            if cur in seen:
                raise ValueError("Verkettung würde Zyklus erzeugen")
            seen.add(cur)
            nxt = self.frame_by_id(cur)
            cur = nxt.next_id if nxt else None
        src.next_id = to_id

    def create_column_chain(self, *, page: int = 0, columns: int | None = None) -> list[DtpFrame]:
        n = max(1, int(columns or self.geometry.columns))
        rects = column_rects(
            width_pt=self.geometry.width_pt,
            height_pt=self.geometry.height_pt,
            margin_left_pt=self.geometry.margin_left_pt,
            margin_right_pt=self.geometry.margin_right_pt,
            margin_top_pt=self.geometry.margin_top_pt,
            margin_bottom_pt=self.geometry.margin_bottom_pt,
            columns=n,
            gutter_pt=self.geometry.gutter_pt,
        )
        frames: list[DtpFrame] = []
        prev: DtpFrame | None = None
        for r in rects:
            fr = self.add_text_frame(
                "",
                x=r["x"],
                y=r["y"],
                width=r["width"],
                height=r["height"],
                page=page,
            )
            if prev is not None:
                prev.next_id = fr.id
            frames.append(fr)
            prev = fr
        return frames

    def bring_to_front(self, frame_id: str) -> None:
        mx = max((f.z for f in self.frames), default=0) + 1
        fr = self.frame_by_id(frame_id)
        if fr:
            fr.z = mx

    def send_to_back(self, frame_id: str) -> None:
        mn = min((f.z for f in self.frames), default=0) - 1
        fr = self.frame_by_id(frame_id)
        if fr:
            fr.z = mn

    def snap_frame(self, fr: DtpFrame) -> None:
        if not (self.grid_snap or self.guides_snap):
            return
        grid = self.grid_pt() if self.grid_snap else 0.0
        guides = self.guides if self.guides_snap else ()
        x, y = snap_point(fr.x, fr.y, grid_pt=grid, guides=guides, threshold=mm_to_pt(1.0))
        if self.geometry.baseline_grid_mm and fr.kind == "text":
            y = snap_baseline(y, mm_to_pt(self.geometry.baseline_grid_mm))
        fr.x, fr.y = x, y

    def _wrap_words(self, text: str, cpl: int) -> str:
        words = (text or "").split()
        lines: list[str] = []
        cur = ""
        for w in words:
            cand = (cur + " " + w).strip()
            if len(cand) <= cpl:
                cur = cand
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return "\n".join(lines)

    def _capacity(self, fr: DtpFrame) -> tuple[int, int]:
        style = self.styles.get(fr.style_id) or self.styles.get("body")
        size = fr.font_size or (style.font_size if style else 11.0)
        leading = style.leading if style else 1.2
        try:
            from PySide6.QtWidgets import QApplication
            from PySide6.QtGui import QFontMetricsF
            from .export import _qfont_for_frame

            if QApplication.instance() is not None:
                font = _qfont_for_frame(self, fr)
                fm = QFontMetricsF(font)
                cpl = max(6, int(fr.width / max(fm.averageCharWidth(), 4.0)))
                lines = max(1, int(fr.height / max(fm.lineSpacing(), 8.0)))
                return cpl, cpl * lines
        except Exception:
            pass
        factor = 0.55
        cpl = max(8, int(fr.width / max(size * factor, 4)))
        line_h = max(size * max(1.0, float(leading)), 8.0)
        lines = max(1, int(fr.height / line_h))
        return cpl, cpl * lines

    def flow_text(self, text: str, start: DtpFrame) -> dict[str, str]:
        remaining = (text or "").strip()
        result: dict[str, str] = {}
        current: DtpFrame | None = start
        visited: set[str] = set()
        obstacles = [
            f
            for f in self.frames_on_page(start.page)
            if f.kind in ("image", "shape") and f.wrap not in ("none", "", None) and f.id != start.id
        ]
        while current is not None and remaining:
            if current.id in visited:
                break
            visited.add(current.id)
            cpl, cap = self._capacity(current)
            if obstacles:
                chunk, remaining = self._flow_around(remaining, current, cpl, obstacles)
            else:
                wrapped = self._wrap_words(remaining, cpl)
                if len(wrapped) <= cap:
                    chunk, remaining = wrapped, ""
                else:
                    words = remaining.split()
                    taken: list[str] = []
                    rest = remaining
                    for i, w in enumerate(words):
                        trial = self._wrap_words(" ".join(taken + [w]), cpl)
                        if len(trial) > cap and taken:
                            rest = " ".join(words[i:])
                            break
                        taken.append(w)
                    else:
                        rest = ""
                    chunk = self._wrap_words(" ".join(taken), cpl)
                    remaining = rest
            current.text = chunk
            result[current.id] = chunk
            if remaining and current.next_id:
                current = self.frame_by_id(current.next_id)
            elif remaining:
                result["__overflow__"] = remaining
                remaining = ""
                break
            else:
                current = self.frame_by_id(current.next_id) if current.next_id else None
        return result

    def _flow_around(
        self, text: str, frame: DtpFrame, cpl: int, obstacles: list[DtpFrame]
    ) -> tuple[str, str]:
        style = self.styles.get(frame.style_id)
        size = frame.font_size or (style.font_size if style else 11.0)
        leading = style.leading if style else 1.2
        line_h = max(size * max(1.0, float(leading)), 8.0)
        max_lines = max(1, int(frame.height / line_h))
        words = text.split()
        lines: list[str] = []
        wi = 0
        for li in range(max_lines):
            if wi >= len(words):
                break
            y = frame.y + li * line_h
            use_cpl = cpl
            skip = False
            for ob in obstacles:
                pad = float(ob.wrap_padding or 0)
                ox, oy, ow, oh = ob.x - pad, ob.y - pad, ob.width + 2 * pad, ob.height + 2 * pad
                if not (frame.x + frame.width <= ox or ox + ow <= frame.x or y + line_h <= oy or oy + oh <= y):
                    if ob.wrap == "jump_object":
                        skip = True
                        break
                    left = max(0.0, ox - frame.x)
                    right = max(0.0, (frame.x + frame.width) - (ox + ow))
                    usable = max(left, right)
                    if usable < frame.width * 0.15:
                        skip = True
                        break
                    use_cpl = max(4, int(cpl * usable / max(frame.width, 1.0)))
            if skip:
                lines.append("")
                continue
            current = ""
            while wi < len(words):
                cand = (current + " " + words[wi]).strip()
                if len(cand) <= use_cpl:
                    current = cand
                    wi += 1
                else:
                    break
            if current:
                lines.append(current)
            else:
                break
        chunk = "\n".join(lines)
        used = chunk.replace("\n", " ").split()
        n = 0
        for a, b in zip(used, words):
            if a == b:
                n += 1
            else:
                break
        rest = " ".join(words[n:])
        return chunk, rest

    def apply_text_on_path(self, frame_id: str, kind: str = "ellipse") -> DtpFrame:
        fr = self.frame_by_id(frame_id)
        if fr is None:
            raise KeyError(frame_id)
        k = (kind or "ellipse").lower()
        if k not in ("ellipse", "line"):
            k = "ellipse"
        fr.path_kind = k
        if fr.kind != "text":
            fr.kind = "text"
        if not (fr.text or "").strip():
            fr.text = "Text auf Pfad"
        return fr

    def convert_text_to_outlines(self, frame_id: str) -> DtpFrame:
        fr = self.frame_by_id(frame_id)
        if fr is None:
            raise KeyError(frame_id)
        fr.as_outlines = True
        if fr.kind != "text":
            fr.kind = "text"
        return fr

    def apply_clip_mask(self, content_id: str, mask_id: str) -> DtpFrame:
        content = self.frame_by_id(content_id)
        mask = self.frame_by_id(mask_id)
        if content is None or mask is None:
            raise KeyError("Inhalt oder Maske nicht gefunden")
        if content_id == mask_id:
            raise ValueError("Rahmen kann sich nicht selbst clippen")
        content.clip_id = mask.id
        return content

    def clear_clip_mask(self, frame_id: str) -> None:
        fr = self.frame_by_id(frame_id)
        if fr is not None:
            fr.clip_id = ""

    def apply_live_fill(
        self,
        frame_id: str,
        *,
        kind: str = "linear",
        fill: str = "#4A90D9",
        fill_to: str = "#0E4D73",
        angle: float = 90.0,
        opacity: float | None = None,
        shadow: bool | None = None,
    ) -> DtpFrame:
        fr = self.frame_by_id(frame_id)
        if fr is None:
            raise KeyError(frame_id)
        k = (kind or "linear").lower()
        if k not in ("solid", "linear", "radial"):
            k = "linear"
        fr.fill_kind = k
        fr.fill = fill
        fr.fill_to = fill_to
        fr.fill_angle = float(angle)
        if opacity is not None:
            fr.opacity = max(0.05, min(1.0, float(opacity)))
        if shadow is not None:
            fr.shadow = bool(shadow)
        return fr

    def apply_drop_shadow(self, frame_id: str, *, dx: float = 3.0, dy: float = 4.0) -> DtpFrame:
        fr = self.frame_by_id(frame_id)
        if fr is None:
            raise KeyError(frame_id)
        fr.shadow = True
        fr.shadow_dx = float(dx)
        fr.shadow_dy = float(dy)
        return fr

    def insert_glyph(self, frame_id: str, glyph: str) -> DtpFrame:
        from instantlensdoc.features.glyph_palette import insert_glyph as _ins

        fr = self.frame_by_id(frame_id)
        if fr is None:
            raise KeyError(frame_id)
        if fr.kind != "text":
            fr.kind = "text"
        fr.text = _ins(fr.text or "", glyph)
        return fr

    def chain_head(self, fr: DtpFrame) -> DtpFrame:
        pred = {f.next_id: f for f in self.frames if f.next_id}
        cur = fr
        seen: set[str] = set()
        while cur.id in pred and cur.id not in seen:
            seen.add(cur.id)
            cur = pred[cur.id]
        return cur

    def chain_members(self, start: DtpFrame) -> list[DtpFrame]:
        out: list[DtpFrame] = []
        cur: Optional[DtpFrame] = start
        seen: set[str] = set()
        while cur is not None and cur.id not in seen:
            seen.add(cur.id)
            out.append(cur)
            cur = self.frame_by_id(cur.next_id) if cur.next_id else None
        return out

    def story_text(self, fr: DtpFrame) -> str:
        parts: list[str] = []
        for m in self.chain_members(self.chain_head(fr)):
            t = (m.text or "").replace("\n", " ").strip()
            if t:
                parts.append(t)
        return " ".join(parts)

    def reflow_chain(self, fr: DtpFrame, *, auto_extend: bool = False) -> dict[str, str]:
        """Gesamten verketteten Text neu umbrechen; Overflow optional auf neue Seite."""
        head = self.chain_head(fr)
        full = self.story_text(head)
        result = self.flow_text(full, head)
        overflow = result.get("__overflow__") or ""
        if overflow and auto_extend:
            members = self.chain_members(head)
            last = members[-1]
            page = last.page + 1
            if page >= self.page_count:
                self.add_page()
            nxt = self.add_text_frame(
                "",
                x=last.x,
                y=self.geometry.margin_top_pt,
                width=last.width,
                height=min(last.height, self.geometry.height_pt - self.geometry.margin_top_pt - self.geometry.margin_bottom_pt),
                page=page,
                style_id=last.style_id,
            )
            self.link_frames(last.id, nxt.id)
            more = self.flow_text(overflow, nxt)
            result.pop("__overflow__", None)
            result.update({k: v for k, v in more.items() if k != "__overflow__"})
            if more.get("__overflow__"):
                result["__overflow__"] = more["__overflow__"]
        return result

    def apply_style(self, frame_id: str, style_id: str) -> DtpFrame:
        fr = self.frame_by_id(frame_id)
        st = self.styles.get(style_id)
        if fr is None or st is None:
            raise KeyError(style_id if fr is not None else frame_id)
        fr.style_id = style_id
        if st.kind in ("paragraph", "character"):
            fr.font_family = st.font_family
            fr.font_size = st.font_size
            fr.font_weight = st.weight
            fr.font_stretch = st.stretch
            if st.italic:
                fr.font_axes = {**(fr.font_axes or {}), "slnt": -12.0}
            fr.rich_html = ""
        if st.kind == "object" and fr.kind in ("shape", "image"):
            if st.fill:
                fr.fill = st.fill
            if st.stroke:
                fr.stroke = st.stroke
            fr.stroke_width = st.stroke_width
        return fr

    def text_frames(self, *, include_master: bool = False) -> list[DtpFrame]:
        return [
            f
            for f in self.frames
            if f.kind == "text" and (include_master or not f.master)
        ]

    def set_active_story(self, fr: Optional[DtpFrame]) -> None:
        if fr is None or fr.kind != "text":
            return
        self.active_story_id = self.chain_head(fr).id

    def story_frames(self, fr: Optional[DtpFrame] = None) -> list[DtpFrame]:
        if fr is not None and fr.kind == "text":
            return self.chain_members(self.chain_head(fr))
        if self.active_story_id:
            head = self.frame_by_id(self.active_story_id)
            if head is not None and head.kind == "text":
                return self.chain_members(self.chain_head(head))
        return self.text_frames()

    def apply_fill_color(
        self,
        frame_id: str,
        color: str,
        *,
        kind: str = "solid",
        fill_to: str = "",
    ) -> DtpFrame:
        fr = self.frame_by_id(frame_id)
        if fr is None:
            raise KeyError(frame_id)
        fr.fill = str(color or "#4A90D9")
        k = (kind or "solid").lower()
        if k not in ("solid", "linear", "radial"):
            k = "solid"
        fr.fill_kind = k
        if fill_to:
            fr.fill_to = fill_to
        elif k == "solid":
            fr.fill_to = ""
        return fr

    def apply_stroke_color(
        self, frame_id: str, color: str, *, width: float | None = None
    ) -> DtpFrame:
        fr = self.frame_by_id(frame_id)
        if fr is None:
            raise KeyError(frame_id)
        fr.stroke = str(color or "#333333")
        if width is not None:
            fr.stroke_width = max(0.0, float(width))
        return fr

    def apply_font_attrs(
        self,
        frame_id: str,
        *,
        family: str | None = None,
        size: float | None = None,
        weight: int | None = None,
        italic: bool | None = None,
        color: str | None = None,
        clear_rich: bool = True,
    ) -> DtpFrame:
        fr = self.frame_by_id(frame_id)
        if fr is None:
            raise KeyError(frame_id)
        if fr.kind != "text":
            raise ValueError("Schrift gilt nur auf Textrahmen (Layout ≠ Inhalt)")
        if family:
            fr.font_family = family
        if size is not None:
            fr.font_size = float(size)
        if weight is not None:
            fr.font_weight = int(weight)
        if italic is not None:
            axes = dict(fr.font_axes or {})
            if italic:
                axes["slnt"] = -12.0
            else:
                axes.pop("slnt", None)
            fr.font_axes = axes
        if color:
            fr.fill = color
        if clear_rich:
            fr.rich_html = ""
        return fr

    def apply_wrap(self, frame_id: str, mode: str) -> DtpFrame:
        fr = self.frame_by_id(frame_id)
        if fr is None:
            raise KeyError(frame_id)
        m = (mode or "none").lower()
        if m not in ("none", "bounding_box", "jump_object", "contour"):
            m = "bounding_box"
        fr.wrap = m
        return fr

    def apply_master(self, master_id: str, pages: list[int] | None = None) -> DtpMaster:
        m = next((x for x in self.masters if x.id == master_id or x.name == master_id), None)
        if m is None:
            raise KeyError(master_id)
        self._sync_page_master()
        targets = list(range(self.page_count)) if pages is None else list(pages)
        for i in targets:
            if 0 <= i < len(self.page_master):
                self.page_master[i] = m.id
        return m

    def add_master(self, name: str, *, header: str = "{title}", footer: str = "{n} / {total}") -> DtpMaster:
        m = DtpMaster(name=name, header_text=header, footer_text=footer)
        self.masters.append(m)
        return m

    def set_image(self, frame_id: str, path: str) -> DtpFrame:
        fr = self.frame_by_id(frame_id)
        if fr is None:
            return self.add_image_frame(path, page=self.current_page)
        if fr.kind not in ("image", "render"):
            raise ValueError("Bild nur in Bild-/Render-Rahmen (Layout ≠ Inhalt)")
        fr.image_path = str(path or "")
        fr.layer_id = fr.layer_id or "images"
        return fr

    def import_into_frame(self, frame_id: str, path: str, *, auto_extend: bool = True) -> DtpFrame:
        from .import_text import read_import_text

        fr = self.frame_by_id(frame_id)
        if fr is None:
            fr = self.add_text_frame("", page=self.current_page)
        if fr.kind != "text":
            raise ValueError("Import nur in Textrahmen")
        fr.kind = "text"
        fr.text = read_import_text(path)
        self.reflow_chain(fr, auto_extend=auto_extend)
        return fr

    def resize_frame(self, frame_id: str, width: float, height: float, *, x: float | None = None, y: float | None = None) -> DtpFrame:
        fr = self.frame_by_id(frame_id)
        if fr is None:
            raise KeyError(frame_id)
        if x is not None:
            fr.x = float(x)
        if y is not None:
            fr.y = float(y)
        fr.resize(width, height)
        if self.grid_snap or self.guides_snap:
            self.snap_frame(fr)
        if fr.kind == "text" and fr.next_id:
            self.reflow_chain(fr)
        return fr

    def set_layer_visible(self, layer_id: str, visible: bool) -> None:
        for ly in self.layers:
            if ly.id == layer_id:
                ly.visible = bool(visible)

    def set_layer_locked(self, layer_id: str, locked: bool) -> None:
        for ly in self.layers:
            if ly.id == layer_id:
                ly.locked = bool(locked)

    def set_layer_blend(self, layer_id: str, blend_mode: str, *, opacity: float | None = None) -> DtpLayer:
        from .color import BLEND_MODES

        mode = (blend_mode or "normal").lower()
        if mode not in BLEND_MODES:
            mode = "normal"
        for ly in self.layers:
            if ly.id == layer_id:
                ly.blend_mode = mode
                if opacity is not None:
                    ly.opacity = max(0.05, min(1.0, float(opacity)))
                return ly
        raise KeyError(layer_id)

    def apply_preset(self, name: str) -> None:
        apply_book_preset(self, name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "ilddtp-v1",
            "title": self.title,
            "page_count": self.page_count,
            "current_page": self.current_page,
            "geometry": self.geometry.to_dict(),
            "frames": [f.to_dict() for f in self.frames],
            "guides": [g.to_dict() for g in self.guides],
            "layers": [ly.to_dict() for ly in self.layers],
            "styles": {k: v.to_dict() for k, v in self.styles.items()},
            "masters": [m.to_dict() for m in self.masters],
            "page_master": list(self.page_master),
            "grid_spacing_mm": self.grid_spacing_mm,
            "grid_visible": self.grid_visible,
            "grid_snap": self.grid_snap,
            "guides_snap": self.guides_snap,
            "number_system": self.number_system,
            "ruler_unit": self.ruler_unit,
            "variables": dict(self.variables),
            "library": self.library.to_dict() if self.library is not None else {},
            "footnotes": [n.to_dict() if hasattr(n, "to_dict") else n for n in self.footnotes],
            "endnotes": [n.to_dict() if hasattr(n, "to_dict") else n for n in self.endnotes],
            "cross_refs": [c.to_dict() if hasattr(c, "to_dict") else c for c in self.cross_refs],
            "widgets": [w.to_dict() if hasattr(w, "to_dict") else w for w in self.widgets],
        }

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DtpDocument":
        doc = cls(
            geometry=PageGeometry.from_dict(data.get("geometry")),
            page_count=int(data.get("page_count") or 1),
            title=str(data.get("title") or "Ohne Titel"),
            current_page=int(data.get("current_page") or 0),
            grid_spacing_mm=float(data.get("grid_spacing_mm") or 5.0),
            grid_visible=bool(data.get("grid_visible", True)),
            grid_snap=bool(data.get("grid_snap", True)),
            guides_snap=bool(data.get("guides_snap", True)),
        )
        doc.frames = [DtpFrame.from_dict(f) for f in (data.get("frames") or [])]
        doc.guides = [DtpGuide(**g) if isinstance(g, dict) else g for g in (data.get("guides") or [])]
        if data.get("layers"):
            doc.layers = [DtpLayer(**ly) for ly in data["layers"] if isinstance(ly, dict)]
        if data.get("styles"):
            doc.styles = {
                k: StyleSheet.from_dict(v) for k, v in data["styles"].items() if isinstance(v, dict)
            }
        if data.get("masters"):
            doc.masters = [DtpMaster(**m) for m in data["masters"] if isinstance(m, dict)]
        doc.page_master = list(data.get("page_master") or [])
        doc.number_system = str(data.get("number_system") or "latin")
        from .geometry import normalize_unit

        doc.ruler_unit = normalize_unit(str(data.get("ruler_unit") or "mm"))
        doc.variables = dict(data.get("variables") or {})
        if data.get("library"):
            from .assets import AssetLibrary

            doc.library = AssetLibrary.from_dict(data["library"])
        from .type_extras import CrossRef, DtpNote
        from .interactive import DtpWidget

        def _notes(raw):
            out = []
            for n in raw or []:
                if isinstance(n, dict):
                    out.append(DtpNote(**{k: n[k] for k in n if k in DtpNote.__dataclass_fields__}))
                else:
                    out.append(n)
            return out

        doc.footnotes = _notes(data.get("footnotes"))
        doc.endnotes = _notes(data.get("endnotes"))
        doc.cross_refs = [
            CrossRef(**{k: c[k] for k in c if k in CrossRef.__dataclass_fields__})
            if isinstance(c, dict)
            else c
            for c in (data.get("cross_refs") or [])
        ]
        doc.widgets = [
            DtpWidget(**{k: w[k] for k in w if k in DtpWidget.__dataclass_fields__})
            if isinstance(w, dict)
            else w
            for w in (data.get("widgets") or [])
        ]
        doc._sync_page_master()
        return doc

    @classmethod
    def load(cls, path: str | Path) -> "DtpDocument":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    @classmethod
    def from_layout_document(cls, layout: Any) -> "DtpDocument":
        """Bestehendes core.layout.LayoutDocument übernehmen."""
        doc = cls()
        doc.geometry.width_pt = float(getattr(layout, "page_width", 595) or 595)
        doc.geometry.height_pt = float(getattr(layout, "page_height", 842) or 842)
        doc.page_count = int(getattr(layout, "page_count", 1) or 1)
        for tf in getattr(layout, "text_frames", []) or []:
            fr = DtpFrame(
                id=getattr(tf, "id", _nid()),
                kind="text",
                page=int(getattr(tf, "page", 0) or 0),
                x=float(tf.x),
                y=float(tf.y),
                width=float(tf.width),
                height=float(tf.height),
                text=str(getattr(tf, "text", "") or ""),
                next_id=getattr(tf, "next_id", None),
                locked=bool(getattr(tf, "locked", False)),
                layer_id="text",
            )
            doc.frames.append(fr)
        for im in getattr(layout, "image_frames", []) or []:
            kind = str(getattr(im, "media_kind", "image") or "image")
            fr = DtpFrame(
                id=getattr(im, "id", _nid()),
                kind="shape" if kind == "shape" else "image",
                shape=str(getattr(im, "shape", "rectangle") or "rectangle"),
                page=int(getattr(im, "page", 0) or 0),
                x=float(im.x),
                y=float(im.y),
                width=float(im.width),
                height=float(im.height),
                image_path=str(getattr(im, "path", "") or ""),
                wrap=str(getattr(im, "text_wrap", "none") or "none"),
                fill=str(getattr(im, "fill_color", "") or ""),
                stroke=str(getattr(im, "stroke_color", "") or "#333"),
                layer_id="images",
            )
            doc.frames.append(fr)
        doc._sync_page_master()
        return doc

    def weld_frames(self, frame_ids: list[str]) -> DtpFrame:
        from .boolean import weld_frames as _weld

        return _weld(self, frame_ids)

    def register_symbol(self, frame_id: str, name: str = "") -> Any:
        from .assets import register_symbol

        fr = self.frame_by_id(frame_id)
        if fr is None:
            raise KeyError(frame_id)
        return register_symbol(self.library, fr, name=name)

    def place_symbol(self, symbol_id: str, *, x: float, y: float, page: int | None = None) -> DtpFrame:
        from .assets import place_symbol

        return place_symbol(self, symbol_id, x=x, y=y, page=self.current_page if page is None else page)

    def add_footnote(self, frame_id: str, body: str, *, marker: str = "") -> Any:
        return self._add_note(frame_id, body, kind="footnote", marker=marker)

    def add_endnote(self, frame_id: str, body: str, *, marker: str = "") -> Any:
        return self._add_note(frame_id, body, kind="endnote", marker=marker)

    def _add_note(self, frame_id: str, body: str, *, kind: str, marker: str = "") -> Any:
        from .type_extras import DtpNote
        from uuid import uuid4

        fr = self.frame_by_id(frame_id)
        bucket = self.footnotes if kind == "footnote" else self.endnotes
        note = DtpNote(
            id=uuid4().hex[:8],
            kind=kind,
            marker=marker or str(len(bucket) + 1),
            body=body,
            frame_id=frame_id,
            page=fr.page if fr else 0,
        )
        bucket.append(note)
        if fr is not None and fr.kind == "text":
            fr.text = (fr.text or "") + f"{{{note.marker}}}"
        return note

    def add_cross_ref(self, target_frame_id: str, fmt: str = "S. {page}") -> Any:
        from .type_extras import CrossRef
        from uuid import uuid4

        cref = CrossRef(id=uuid4().hex[:8], target_frame_id=target_frame_id, fmt=fmt)
        self.cross_refs.append(cref)
        return cref

    def add_widget(
        self,
        frame_id: str,
        kind: str = "text",
        *,
        name: str = "",
        value: str = "",
        options: list[str] | None = None,
    ) -> Any:
        from .interactive import DtpWidget

        fr = self.frame_by_id(frame_id)
        w = DtpWidget(
            kind=kind,
            frame_id=frame_id,
            name=name or kind,
            value=value,
            options=list(options or []),
            page=fr.page if fr else 0,
        )
        self.widgets.append(w)
        return w

    def apply_kerning(self, frame_id: str, pairs: dict[str, float]) -> DtpFrame:
        fr = self.frame_by_id(frame_id)
        if fr is None:
            raise KeyError(frame_id)
        if fr.kind != "text":
            raise ValueError("Kerning gilt nur auf Textrahmen")
        fr.kerning_pairs.update(pairs or {})
        return fr

    def import_graphic(self, path: str, *, page: int | None = None):
        from .import_graphics import import_graphic

        return import_graphic(self, path, page=self.current_page if page is None else page)

    def expand_frame_variables(self, fr: DtpFrame) -> str:
        from .type_extras import expand_variables

        return expand_variables(
            fr.text or "",
            page=fr.page + 1,
            total=self.page_count,
            title=self.title,
            variables=self.variables,
            notes=list(self.footnotes) + list(self.endnotes),
            number_system=self.number_system,
        )

    @classmethod
    def sample(cls, preset: str = "A5") -> "DtpDocument":
        """Beispiel-Buchseite für Tests/Screenshots."""
        doc = cls(title="InstantLens Doc — DTP")
        doc.apply_preset(preset)
        doc.page_count = 2
        doc._sync_page_master()
        cols = doc.create_column_chain(page=0, columns=2)
        body = (
            "Desktop-Publishing in InstantLens Doc: Textrahmen fließen über Spalten, "
            "Hilfslinien rasten am Lineal ein, und der Satzspiegel folgt dem gewählten "
            "Buchformat. Dies ist ein Beispielabsatz für die Verkettung. "
        ) * 8
        doc.flow_text(body, cols[0])
        img = doc.add_image_frame("", x=doc.geometry.margin_left_pt, y=doc.geometry.height_pt * 0.62,
                                  width=160, height=90, page=0, wrap="bounding_box")
        img.fill = "#CFE8F3"
        doc.add_shape("ellipse", x=doc.geometry.margin_left_pt + 170, y=doc.geometry.height_pt * 0.62,
                      width=70, height=70, page=0, fill="#AED6F1", stroke="#1A5276")
        doc.add_shape("triangle", x=doc.geometry.width_pt * 0.55, y=doc.geometry.height_pt * 0.62,
                      width=90, height=70, page=0)
        doc.add_guide("vertical", doc.geometry.margin_left_pt)
        doc.add_guide("horizontal", doc.geometry.margin_top_pt)
        chap = doc.add_master("Kapitel", header="Kapitel · {title}", footer="{n}")
        doc.apply_master(chap.id, pages=[1])
        h1 = doc.add_text_frame("Kapitel 1 — Layout-Modus", page=1, style_id="h1",
                                x=doc.geometry.margin_left_pt, y=doc.geometry.margin_top_pt,
                                width=doc.geometry.width_pt - doc.geometry.margin_left_pt - doc.geometry.margin_right_pt,
                                height=36)
        h1.font_size = 16
        h1.font_weight = 700
        path_fr = doc.add_text_frame(
            "InstantLens Doc",
            page=1,
            x=doc.geometry.margin_left_pt,
            y=doc.geometry.margin_top_pt + 50,
            width=220,
            height=90,
        )
        path_fr.path_kind = "ellipse"
        path_fr.font_size = 11
        mask = doc.add_shape(
            "ellipse",
            x=doc.geometry.width_pt * 0.52,
            y=doc.geometry.margin_top_pt + 48,
            width=130,
            height=90,
            page=1,
            fill="#8E44AD",
            stroke="#4A235A",
        )
        mask.fill_kind = "linear"
        mask.fill_to = "#F4D03F"
        mask.shadow = True
        clipped = doc.add_shape(
            "rectangle",
            x=mask.x - 10,
            y=mask.y - 8,
            width=150,
            height=110,
            page=1,
            fill="#1ABC9C",
            stroke="#0E6655",
        )
        clipped.clip_id = mask.id
        clipped.fill_kind = "radial"
        clipped.fill_to = "#145A32"
        clipped.opacity = 0.92
        return doc


# Buchformate re-exportiert für Tests
BOOK_FORMATS = BOOK_PRESETS_MM
