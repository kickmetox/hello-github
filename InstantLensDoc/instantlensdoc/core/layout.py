"""Layout: Textrahmen, verkettete Rahmen, Bildrahmen, Move/Resize — 2.6.12."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4


FrameKind = Union["TextFrame", "ImageFrame"]


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

    @property
    def capacity_chars(self) -> int:
        """Grobe Kapazität: Zeilen × Zeichen/Zeile aus Frame-Maßen."""
        chars_per_line = max(8, int(self.width / max(self.font_size * 0.55, 4)))
        lines = max(1, int(self.height / max(self.font_size * 1.35, 8)))
        return chars_per_line * lines

    @property
    def chars_per_line(self) -> int:
        return max(8, int(self.width / max(self.font_size * 0.55, 4)))

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
        )
        self.image_frames.append(frame)
        self.page_count = max(self.page_count, frame.page + 1)
        return frame

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

    def flow_text(
        self,
        text: str,
        frame: Optional[TextFrame] = None,
        chars_per_line: int | None = None,
    ) -> str:
        """Einfacher Textumfluss in einem Rahmen (Wortgrenzen)."""
        cpl = chars_per_line or (frame.chars_per_line if frame else 70)
        result = _wrap_words(text, cpl)
        if frame is not None:
            frame.text = result
        return result

    def flow_text_chain(self, text: str, start: TextFrame) -> Dict[str, str]:
        """
        Verketteter Textumfluss: füllt start, Overflow in next_id-Kette
        (Spalte → Spalte / Seite → Seite).
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
                )
                if k in tf
            }
            doc.text_frames.append(TextFrame(**known))
        for im in data.get("image_frames", []):
            known = {
                k: im[k]
                for k in ("x", "y", "width", "height", "path", "id", "page", "locked")
                if k in im
            }
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
