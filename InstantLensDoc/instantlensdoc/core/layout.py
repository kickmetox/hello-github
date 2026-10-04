"""Layout: Textrahmen, verkettete Rahmen, Bildrahmen, Move/Resize, Textumfluss, Ebenen, Medien — 2.6.26."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
from uuid import uuid4


FrameKind = Union["TextFrame", "ImageFrame"]

# Textumfluss um Bild-/Formrahmen
TEXT_WRAP_MODES: tuple[str, ...] = ("none", "bounding_box", "jump_object", "contour")

# Dokument-Ebenen 2.6.19
LAYER_NAMES: tuple[str, ...] = ("background", "images", "text")

# Medienarten / Formen — 2.6.26
MEDIA_KINDS: tuple[str, ...] = ("image", "shape", "video")
SHAPE_KINDS: tuple[str, ...] = (
    "rectangle",
    "ellipse",
    "triangle",
    "rounded_rect",
    "line",
    "arrow",
)


def normalize_frame_layer(name: str | None, *, kind: str = "text") -> str:
    """Ebenenname normalisieren; Default text bzw. images für Bildrahmen."""
    key = (name or "").strip().lower()
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
    if key in LAYER_NAMES:
        return key
    return "images" if kind == "image" else "text"


@dataclass
class TextFrame:
    x: float
    y: float
    width: float
    height: float
    text: str = ""
    font_size: int = 12
    # Verkettung: Overflow fließt in next_id
    next_id: Optional[str] = None
    id: str = field(default_factory=lambda: uuid4().hex[:8])
    page: int = 0  # 0-basierter Seitenindex
    locked: bool = False
    column: int = 0  # Spaltenindex innerhalb der Seite (0 = erste)
    # Typografie 2.6.13
    tracking: float = 0.0
    leading: float = 1.15
    hyphenate_lang: str = ""
    # Ebenen 2.6.19
    layer: str = "text"

    @property
    def capacity_chars(self) -> int:
        """Grobe Kapazität: Zeilen × Zeichen/Zeile aus Frame-Maßen."""
        chars_per_line = max(8, int(self.width / max(self.font_size * 0.55, 4)))
        line_h = max(self.font_size * max(1.0, float(self.leading)), 8)
        lines = max(1, int(self.height / line_h))
        return chars_per_line * lines

    @property
    def chars_per_line(self) -> int:
        # Tracking > 0 verringert effektive Zeichen/Zeile leicht
        factor = 0.55 + max(0.0, float(self.tracking)) / 1000.0
        return max(8, int(self.width / max(self.font_size * factor, 4)))

    def move(self, x: float, y: float) -> None:
        if self.locked:
            raise ValueError(f"Rahmen {self.id} ist gesperrt")
        self.x = float(x)
        self.y = float(y)

    def resize(self, width: float, height: float) -> None:
        if self.locked:
            raise ValueError(f"Rahmen {self.id} ist gesperrt")
        self.width = max(8.0, float(width))
        self.height = max(8.0, float(height))

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = "text"
        return d


@dataclass
class ImageFrame:
    x: float
    y: float
    width: float
    height: float
    path: str = ""
    id: str = field(default_factory=lambda: uuid4().hex[:8])
    page: int = 0
    locked: bool = False
    # Textumfluss 2.6.13: none | bounding_box | jump_object | contour
    text_wrap: str = "none"
    wrap_padding: float = 8.0
    # Form-Hinweis für contour / Shape-Rahmen
    shape: str = "rectangle"  # rectangle | ellipse | triangle | rounded_rect | …
    # Ebenen 2.6.19
    layer: str = "images"
    # Medien-Polish 2.6.26: crop (0–1 relativ), scale, Video-Placeholder
    media_kind: str = "image"  # image | shape | video
    crop_left: float = 0.0
    crop_top: float = 0.0
    crop_right: float = 0.0
    crop_bottom: float = 0.0
    scale: float = 1.0
    video_url: str = ""
    video_title: str = ""
    fill_color: str = ""
    stroke_color: str = "#333333"
    stroke_width: float = 1.0

    def move(self, x: float, y: float) -> None:
        if self.locked:
            raise ValueError(f"Rahmen {self.id} ist gesperrt")
        self.x = float(x)
        self.y = float(y)

    def resize(self, width: float, height: float) -> None:
        if self.locked:
            raise ValueError(f"Rahmen {self.id} ist gesperrt")
        self.width = max(8.0, float(width))
        self.height = max(8.0, float(height))

    def scale_by(self, factor: float) -> None:
        """Gleichmäßig skalieren (Rahmenmaße) — 2.6.26."""
        if self.locked:
            raise ValueError(f"Rahmen {self.id} ist gesperrt")
        f = float(factor)
        if f <= 0:
            raise ValueError("Skalierungsfaktor muss > 0 sein")
        self.width = max(8.0, self.width * f)
        self.height = max(8.0, self.height * f)
        self.scale = max(0.01, float(self.scale or 1.0) * f)

    def set_crop(
        self,
        left: float = 0.0,
        top: float = 0.0,
        right: float = 0.0,
        bottom: float = 0.0,
    ) -> None:
        """Zuschneiden relativ 0–1 (Ränder vom Original) — 2.6.26."""
        if self.locked:
            raise ValueError(f"Rahmen {self.id} ist gesperrt")

        def _clamp(v: float) -> float:
            return max(0.0, min(0.49, float(v)))

        self.crop_left = _clamp(left)
        self.crop_top = _clamp(top)
        self.crop_right = _clamp(right)
        self.crop_bottom = _clamp(bottom)
        if self.crop_left + self.crop_right >= 0.99 or self.crop_top + self.crop_bottom >= 0.99:
            raise ValueError("Zuschneiden würde Bild vollständig entfernen")

    def set_text_wrap(self, mode: str, *, padding: float | None = None) -> None:
        m = (mode or "none").strip().lower()
        if m not in TEXT_WRAP_MODES:
            raise ValueError(f"Unbekannter Textumfluss: {mode}")
        self.text_wrap = m
        if padding is not None:
            self.wrap_padding = max(0.0, float(padding))

    def exclusion_rect(self) -> dict[str, float]:
        """Ausschlusszone inkl. Padding (für bounding_box / contour)."""
        pad = float(self.wrap_padding or 0.0)
        return {
            "x": self.x - pad,
            "y": self.y - pad,
            "width": self.width + 2 * pad,
            "height": self.height + 2 * pad,
            "shape": self.shape if self.text_wrap == "contour" else "rectangle",
        }

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = "image"
        return d


@dataclass
class LayoutDocument:
    """Seitenlayout mit beweglichen/skalierbaren, optional verketteten Rahmen."""

    page_width: float = 595.0
    page_height: float = 842.0
    text_frames: List[TextFrame] = field(default_factory=list)
    image_frames: List[ImageFrame] = field(default_factory=list)
    page_count: int = 1

    def frame_by_id(self, frame_id: str) -> Optional[TextFrame]:
        for f in self.text_frames:
            if f.id == frame_id:
                return f
        return None

    def any_frame_by_id(self, frame_id: str) -> Optional[FrameKind]:
        tf = self.frame_by_id(frame_id)
        if tf is not None:
            return tf
        for f in self.image_frames:
            if f.id == frame_id:
                return f
        return None

    def list_frames(self) -> list[dict[str, Any]]:
        rows = [f.to_dict() for f in self.text_frames]
        rows.extend(f.to_dict() for f in self.image_frames)
        return rows

    def set_frame_layer(self, frame_id: str, layer: str) -> FrameKind:
        """Rahmen einer Dokument-Ebene zuordnen — 2.6.19."""
        frame = self.any_frame_by_id(frame_id)
        if frame is None:
            raise KeyError(f"Rahmen nicht gefunden: {frame_id}")
        kind = "image" if isinstance(frame, ImageFrame) else "text"
        frame.layer = normalize_frame_layer(layer, kind=kind)
        return frame

    def frames_by_layer(self) -> dict[str, list[dict[str, Any]]]:
        """Rahmen nach Hintergrund/Bilder/Text gruppieren — 2.6.19."""
        out: dict[str, list[dict[str, Any]]] = {k: [] for k in LAYER_NAMES}
        for fr in self.list_frames():
            kind = str(fr.get("kind") or "text")
            lid = normalize_frame_layer(fr.get("layer"), kind=kind)
            row = dict(fr)
            row["layer"] = lid
            out[lid].append(row)
        return out

    def add_text_frame(
        self,
        text: str = "",
        x: float = 40,
        y: float = 40,
        width: float = 515,
        height: float = 200,
        font_size: int = 12,
        page: int = 0,
        column: int = 0,
    ) -> TextFrame:
        frame = TextFrame(
            x=x,
            y=y,
            width=width,
            height=height,
            text=text,
            font_size=font_size,
            page=max(0, int(page)),
            column=max(0, int(column)),
        )
        self.text_frames.append(frame)
        self.page_count = max(self.page_count, frame.page + 1)
        return frame

    def add_image(
        self,
        path: str,
        x: float = 40,
        y: float = 300,
        width: float = 200,
        height: float = 150,
        page: int = 0,
    ) -> ImageFrame:
        frame = ImageFrame(
            x=x,
            y=y,
            width=width,
            height=height,
            path=path,
            page=max(0, int(page)),
            media_kind="image",
        )
        self.image_frames.append(frame)
        self.page_count = max(self.page_count, frame.page + 1)
        return frame

    def add_shape(
        self,
        shape: str = "rectangle",
        x: float = 40,
        y: float = 300,
        width: float = 120,
        height: float = 80,
        page: int = 0,
        *,
        fill_color: str = "#D0E8FF",
        stroke_color: str = "#1A5276",
        stroke_width: float = 1.5,
        text_wrap: str = "bounding_box",
    ) -> ImageFrame:
        """Formrahmen (ohne Bilddatei) — 2.6.26."""
        sk = (shape or "rectangle").strip().lower()
        if sk not in SHAPE_KINDS:
            raise ValueError(f"Unbekannte Form: {shape} (erlaubt: {', '.join(SHAPE_KINDS)})")
        frame = ImageFrame(
            x=x,
            y=y,
            width=width,
            height=height,
            path="",
            page=max(0, int(page)),
            shape=sk,
            media_kind="shape",
            fill_color=fill_color or "",
            stroke_color=stroke_color or "#333333",
            stroke_width=float(stroke_width),
            text_wrap=text_wrap if text_wrap in TEXT_WRAP_MODES else "bounding_box",
        )
        self.image_frames.append(frame)
        self.page_count = max(self.page_count, frame.page + 1)
        return frame

    def add_video_placeholder(
        self,
        url: str,
        x: float = 40,
        y: float = 300,
        width: float = 320,
        height: float = 180,
        page: int = 0,
        *,
        title: str = "",
        text_wrap: str = "bounding_box",
    ) -> ImageFrame:
        """Online-Video als Platzhalter mit URL (kein Embed-Player) — 2.6.26."""
        from urllib.parse import urlparse

        raw = (url or "").strip()
        if not raw:
            raise ValueError("Video-URL darf nicht leer sein")
        if "://" not in raw and "." in raw:
            raw = "https://" + raw
        parsed = urlparse(raw)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("Video-URL muss http(s) sein")
        frame = ImageFrame(
            x=x,
            y=y,
            width=width,
            height=height,
            path="",
            page=max(0, int(page)),
            media_kind="video",
            video_url=raw,
            video_title=(title or parsed.netloc or "Video").strip(),
            shape="rectangle",
            fill_color="#1C1C1C",
            stroke_color="#E74C3C",
            stroke_width=2.0,
            text_wrap=text_wrap if text_wrap in TEXT_WRAP_MODES else "bounding_box",
        )
        self.image_frames.append(frame)
        self.page_count = max(self.page_count, frame.page + 1)
        return frame

    def scale_image(self, frame_id: str, factor: float) -> ImageFrame:
        """Bild-/Form-/Video-Rahmen skalieren — 2.6.26."""
        fr = self._image_frame(frame_id)
        fr.scale_by(factor)
        return fr

    def crop_image(
        self,
        frame_id: str,
        left: float = 0.0,
        top: float = 0.0,
        right: float = 0.0,
        bottom: float = 0.0,
    ) -> ImageFrame:
        """Bild zuschneiden (relative Ränder) — 2.6.26."""
        fr = self._image_frame(frame_id)
        if fr.media_kind == "video":
            raise ValueError("Video-Platzhalter können nicht zugeschnitten werden")
        fr.set_crop(left=left, top=top, right=right, bottom=bottom)
        return fr

    def _image_frame(self, frame_id: str) -> ImageFrame:
        for f in self.image_frames:
            if f.id == frame_id:
                return f
        raise KeyError(f"Bildrahmen nicht gefunden: {frame_id}")

    def move_frame(self, frame_id: str, x: float, y: float) -> FrameKind:
        frame = self.any_frame_by_id(frame_id)
        if frame is None:
            raise KeyError(f"Rahmen nicht gefunden: {frame_id}")
        frame.move(x, y)
        return frame

    def resize_frame(self, frame_id: str, width: float, height: float) -> FrameKind:
        frame = self.any_frame_by_id(frame_id)
        if frame is None:
            raise KeyError(f"Rahmen nicht gefunden: {frame_id}")
        frame.resize(width, height)
        return frame

    def set_frame_page(self, frame_id: str, page: int) -> FrameKind:
        frame = self.any_frame_by_id(frame_id)
        if frame is None:
            raise KeyError(f"Rahmen nicht gefunden: {frame_id}")
        if getattr(frame, "locked", False):
            raise ValueError(f"Rahmen {frame_id} ist gesperrt")
        frame.page = max(0, int(page))
        self.page_count = max(self.page_count, frame.page + 1)
        return frame

    def link_frames(self, from_id: str, to_id: str) -> None:
        """Verkettet zwei Textrahmen (Overflow von from → to)."""
        src = self.frame_by_id(from_id)
        dst = self.frame_by_id(to_id)
        if src is None or dst is None:
            raise KeyError(f"Rahmen nicht gefunden: {from_id} / {to_id}")
        if from_id == to_id:
            raise ValueError("Rahmen kann nicht auf sich selbst verweisen")
        # Zyklen vermeiden
        seen = {from_id}
        cur = to_id
        while cur:
            if cur in seen:
                raise ValueError("Verkettung würde Zyklus erzeugen")
            seen.add(cur)
            nxt = self.frame_by_id(cur)
            cur = nxt.next_id if nxt else None
        src.next_id = to_id

    def unlink_frame(self, frame_id: str) -> None:
        src = self.frame_by_id(frame_id)
        if src is None:
            raise KeyError(f"Rahmen nicht gefunden: {frame_id}")
        src.next_id = None

    def chain_new_frame(
        self,
        after: TextFrame,
        *,
        x: Optional[float] = None,
        y: Optional[float] = None,
        width: Optional[float] = None,
        height: Optional[float] = None,
        page: Optional[int] = None,
        column: Optional[int] = None,
    ) -> TextFrame:
        """Neuen Rahmen anlegen und an `after` hängen (unterhalb / nächste Spalte/Seite)."""
        nx = x if x is not None else after.x
        ny = y if y is not None else min(after.y + after.height + 16, self.page_height - 80)
        nw = width if width is not None else after.width
        nh = height if height is not None else after.height
        npage = after.page if page is None else max(0, int(page))
        ncol = (after.column + 1) if column is None else max(0, int(column))
        nxt = self.add_text_frame(
            x=nx,
            y=ny,
            width=nw,
            height=nh,
            font_size=after.font_size,
            page=npage,
            column=ncol,
        )
        after.next_id = nxt.id
        return nxt

    def create_column_chain(
        self,
        *,
        columns: int = 2,
        page: int = 0,
        margin_x: float = 40.0,
        margin_y: float = 40.0,
        gutter: float = 16.0,
        height: float = 600.0,
        font_size: int = 12,
    ) -> list[TextFrame]:
        """Erzeugt verkettete Spalten-Rahmen auf einer Seite."""
        cols = max(1, int(columns))
        usable = max(40.0, self.page_width - 2 * margin_x - gutter * (cols - 1))
        col_w = usable / cols
        frames: list[TextFrame] = []
        prev: Optional[TextFrame] = None
        for i in range(cols):
            x = margin_x + i * (col_w + gutter)
            fr = self.add_text_frame(
                x=x,
                y=margin_y,
                width=col_w,
                height=height,
                font_size=font_size,
                page=page,
                column=i,
            )
            if prev is not None:
                prev.next_id = fr.id
            frames.append(fr)
            prev = fr
        return frames

    def create_page_chain(
        self,
        *,
        pages: int = 2,
        x: float = 40.0,
        y: float = 40.0,
        width: float = 515.0,
        height: float = 700.0,
        font_size: int = 12,
        start_page: int = 0,
    ) -> list[TextFrame]:
        """Erzeugt verkettete Textrahmen über mehrere Seiten."""
        n = max(1, int(pages))
        frames: list[TextFrame] = []
        prev: Optional[TextFrame] = None
        for i in range(n):
            fr = self.add_text_frame(
                x=x,
                y=y,
                width=width,
                height=height,
                font_size=font_size,
                page=start_page + i,
                column=0,
            )
            if prev is not None:
                prev.next_id = fr.id
            frames.append(fr)
            prev = fr
        return frames

    def set_text_wrap(
        self,
        frame_id: str,
        mode: str = "bounding_box",
        *,
        padding: float | None = None,
    ) -> ImageFrame:
        """Textumfluss um Bild-/Formrahmen setzen — 2.6.13."""
        fr = None
        for f in self.image_frames:
            if f.id == frame_id:
                fr = f
                break
        if fr is None:
            raise KeyError(f"Bildrahmen nicht gefunden: {frame_id}")
        fr.set_text_wrap(mode, padding=padding)
        return fr

    def wrap_obstacles(self, *, page: int | None = None) -> list[dict[str, Any]]:
        """Aktive Ausschlusszonen (ImageFrames mit text_wrap ≠ none)."""
        out: list[dict[str, Any]] = []
        for im in self.image_frames:
            if im.text_wrap in ("none", "", None):
                continue
            if page is not None and im.page != int(page):
                continue
            rect = im.exclusion_rect()
            rect["id"] = im.id
            rect["mode"] = im.text_wrap
            out.append(rect)
        return out

    def flow_text(
        self,
        text: str,
        frame: Optional[TextFrame] = None,
        chars_per_line: int | None = None,
        *,
        around_wrap: bool = False,
    ) -> str:
        """Einfacher Textumfluss in einem Rahmen (Wortgrenzen); optional um Hindernisse."""
        if around_wrap and frame is not None:
            result = self.flow_text_around(text, frame)
            return result
        cpl = chars_per_line or (frame.chars_per_line if frame else 70)
        result = _wrap_words(text, cpl)
        if frame is not None:
            frame.text = result
        return result

    def flow_text_around(self, text: str, frame: TextFrame) -> str:
        """
        Text fließt um Bild-/Formrahmen auf derselben Seite (bounding_box / contour / jump).
        Zeilenweise: bei Überlappung mit Hindernis schmalere cpl oder Zeile überspringen.
        """
        obstacles = self.wrap_obstacles(page=frame.page)
        if not obstacles:
            wrapped = _wrap_words(text, frame.chars_per_line)
            frame.text = wrapped
            return wrapped
        line_h = max(frame.font_size * max(1.0, float(frame.leading)), 8.0)
        max_lines = max(1, int(frame.height / line_h))
        words = text.split()
        lines: list[str] = []
        wi = 0
        for li in range(max_lines):
            if wi >= len(words):
                break
            y = frame.y + li * line_h
            cpl, skip = _line_capacity_with_obstacles(
                frame, y, line_h, obstacles, base_cpl=frame.chars_per_line
            )
            if skip:
                lines.append("")
                continue
            current = ""
            while wi < len(words):
                candidate = (current + " " + words[wi]).strip()
                if len(candidate) <= cpl:
                    current = candidate
                    wi += 1
                else:
                    break
            if current:
                lines.append(current)
            elif wi < len(words) and cpl < 8:
                lines.append("")
            else:
                break
        result = "\n".join(lines)
        frame.text = result
        return result

    def flow_text_chain(
        self,
        text: str,
        start: TextFrame,
        *,
        around_wrap: bool = False,
    ) -> Dict[str, str]:
        """
        Verketteter Textumfluss: füllt start, Overflow in next_id-Kette
        (Spalte → Spalte / Seite → Seite). Optional Textumfluss um Bildrahmen.
        Rückgabe: {frame_id: text_in_frame}; optional ``__overflow__``.
        """
        remaining = text.strip()
        result: Dict[str, str] = {}
        current: Optional[TextFrame] = start
        visited: set[str] = set()
        while current is not None and remaining:
            if current.id in visited:
                break
            visited.add(current.id)
            if around_wrap and self.wrap_obstacles(page=current.page):
                chunk = self.flow_text_around(remaining, current)
                # Overflow schätzen: Wörter die nicht in chunk landeten
                used = chunk.replace("\n", " ").split()
                rem_words = remaining.split()
                if len(used) < len(rem_words):
                    # Präfix-Match
                    n = 0
                    for a, b in zip(used, rem_words):
                        if a == b:
                            n += 1
                        else:
                            break
                    remaining = " ".join(rem_words[n:])
                else:
                    remaining = ""
                result[current.id] = chunk
            else:
                capacity = current.capacity_chars
                cpl = current.chars_per_line
                chunk, remaining = _take_chars_wrapped(remaining, capacity, cpl)
                current.text = chunk
                result[current.id] = chunk
            if not remaining:
                nxt_id = current.next_id
                while nxt_id and nxt_id not in visited:
                    nf = self.frame_by_id(nxt_id)
                    if not nf:
                        break
                    visited.add(nf.id)
                    nf.text = ""
                    result[nf.id] = ""
                    nxt_id = nf.next_id
                break
            if current.next_id:
                current = self.frame_by_id(current.next_id)
            else:
                current.text = (current.text + "\n[…]").strip()
                result[current.id] = current.text
                result["__overflow__"] = remaining
                remaining = ""
                break
        return result

    def chain_ids(self, start_id: str) -> list[str]:
        """ID-Kette ab start_id (inkl.)."""
        out: list[str] = []
        cur = start_id
        seen: set[str] = set()
        while cur and cur not in seen:
            seen.add(cur)
            out.append(cur)
            fr = self.frame_by_id(cur)
            cur = fr.next_id if fr else None
        return out

    def to_dict(self) -> dict:
        return {
            "page_width": self.page_width,
            "page_height": self.page_height,
            "page_count": self.page_count,
            "text_frames": [asdict(f) for f in self.text_frames],
            "image_frames": [asdict(f) for f in self.image_frames],
        }

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    @classmethod
    def from_dict(cls, data: dict) -> "LayoutDocument":
        doc = cls(
            page_width=float(data.get("page_width", 595)),
            page_height=float(data.get("page_height", 842)),
            page_count=int(data.get("page_count", 1) or 1),
        )
        for tf in data.get("text_frames", []):
            known = {
                k: tf[k]
                for k in (
                    "x",
                    "y",
                    "width",
                    "height",
                    "text",
                    "font_size",
                    "next_id",
                    "id",
                    "page",
                    "locked",
                    "column",
                    "tracking",
                    "leading",
                    "hyphenate_lang",
                    "layer",
                )
                if k in tf
            }
            if "layer" in known:
                known["layer"] = normalize_frame_layer(known["layer"], kind="text")
            doc.text_frames.append(TextFrame(**known))
        for im in data.get("image_frames", []):
            known = {
                k: im[k]
                for k in (
                    "x",
                    "y",
                    "width",
                    "height",
                    "path",
                    "id",
                    "page",
                    "locked",
                    "text_wrap",
                    "wrap_padding",
                    "shape",
                    "layer",
                    "media_kind",
                    "crop_left",
                    "crop_top",
                    "crop_right",
                    "crop_bottom",
                    "scale",
                    "video_url",
                    "video_title",
                    "fill_color",
                    "stroke_color",
                    "stroke_width",
                )
                if k in im
            }
            if "layer" in known:
                known["layer"] = normalize_frame_layer(known["layer"], kind="image")
            if "media_kind" in known:
                mk = str(known["media_kind"] or "image").lower()
                known["media_kind"] = mk if mk in MEDIA_KINDS else "image"
            doc.image_frames.append(ImageFrame(**known))
        if doc.text_frames or doc.image_frames:
            max_page = max(
                [f.page for f in doc.text_frames] + [f.page for f in doc.image_frames] + [0]
            )
            doc.page_count = max(doc.page_count, max_page + 1)
        return doc

    @classmethod
    def load(cls, path: str | Path) -> "LayoutDocument":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)


def _wrap_words(text: str, chars_per_line: int) -> str:
    words = text.split()
    lines: List[str] = []
    current = ""
    for w in words:
        candidate = (current + " " + w).strip()
        if len(candidate) <= chars_per_line:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return "\n".join(lines)


def _take_chars_wrapped(text: str, capacity: int, chars_per_line: int) -> Tuple[str, str]:
    """Nimmt so viele Wörter, dass gewickelter Text ≤ capacity Zeichen hat."""
    words = text.split()
    taken: List[str] = []
    for i, w in enumerate(words):
        trial = _wrap_words(" ".join(taken + [w]), chars_per_line)
        if len(trial) > capacity and taken:
            remaining = " ".join(words[i:])
            return _wrap_words(" ".join(taken), chars_per_line), remaining
        taken.append(w)
    return _wrap_words(" ".join(taken), chars_per_line), ""


def _rects_overlap(ax: float, ay: float, aw: float, ah: float, b: dict[str, float]) -> bool:
    bx, by, bw, bh = float(b["x"]), float(b["y"]), float(b["width"]), float(b["height"])
    return not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)


def _line_capacity_with_obstacles(
    frame: TextFrame,
    line_y: float,
    line_h: float,
    obstacles: Sequence[dict[str, Any]],
    *,
    base_cpl: int,
) -> Tuple[int, bool]:
    """
    Effektive Zeichen/Zeile unter Berücksichtigung von Hindernissen.
    Rückgabe: (chars_per_line, skip_line).
    jump_object → Zeile überspringen wenn Überlappung.
    bounding_box/contour → cpl reduzieren um Hindernisbreite.
    """
    cpl = int(base_cpl)
    for obs in obstacles:
        mode = str(obs.get("mode") or "bounding_box")
        if not _rects_overlap(frame.x, line_y, frame.width, line_h, obs):
            continue
        if mode == "jump_object":
            return 0, True
        # Hindernis schneidet horizontal den Textrahmen
        ox = float(obs["x"])
        ow = float(obs["width"])
        left = max(0.0, ox - frame.x)
        right = max(0.0, (frame.x + frame.width) - (ox + ow))
        usable = max(left, right)
        if usable < frame.width * 0.15:
            return 0, True
        ratio = usable / max(frame.width, 1.0)
        cpl = max(4, int(base_cpl * ratio))
        # contour: etwas großzügiger (Ellipse ≈ 0.85 der Box)
        if mode == "contour" and str(obs.get("shape")) == "ellipse":
            cpl = max(cpl, int(base_cpl * min(1.0, ratio + 0.1)))
    return cpl, False
