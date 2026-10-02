"""Layout: Textrahmen, verkettete Rahmen, Bildrahmen, einfacher Textumfluss."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4


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

    @property
    def capacity_chars(self) -> int:
        """Grobe Kapazität: Zeilen × Zeichen/Zeile aus Frame-Maßen."""
        chars_per_line = max(8, int(self.width / max(self.font_size * 0.55, 4)))
        lines = max(1, int(self.height / max(self.font_size * 1.35, 8)))
        return chars_per_line * lines

    @property
    def chars_per_line(self) -> int:
        return max(8, int(self.width / max(self.font_size * 0.55, 4)))


@dataclass
class ImageFrame:
    x: float
    y: float
    width: float
    height: float
    path: str = ""
    id: str = field(default_factory=lambda: uuid4().hex[:8])


@dataclass
class LayoutDocument:
    """Einfaches Seitenlayout mit optional verketteten Textrahmen."""

    page_width: float = 595.0
    page_height: float = 842.0
    text_frames: List[TextFrame] = field(default_factory=list)
    image_frames: List[ImageFrame] = field(default_factory=list)

    def frame_by_id(self, frame_id: str) -> Optional[TextFrame]:
        for f in self.text_frames:
            if f.id == frame_id:
                return f
        return None

    def add_text_frame(
        self,
        text: str = "",
        x: float = 40,
        y: float = 40,
        width: float = 515,
        height: float = 200,
        font_size: int = 12,
    ) -> TextFrame:
        frame = TextFrame(
            x=x, y=y, width=width, height=height, text=text, font_size=font_size
        )
        self.text_frames.append(frame)
        return frame

    def add_image(
        self,
        path: str,
        x: float = 40,
        y: float = 300,
        width: float = 200,
        height: float = 150,
    ) -> ImageFrame:
        frame = ImageFrame(x=x, y=y, width=width, height=height, path=path)
        self.image_frames.append(frame)
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

    def chain_new_frame(
        self,
        after: TextFrame,
        *,
        x: Optional[float] = None,
        y: Optional[float] = None,
        width: Optional[float] = None,
        height: Optional[float] = None,
    ) -> TextFrame:
        """Neuen Rahmen anlegen und an `after` hängen (unterhalb oder daneben)."""
        nx = x if x is not None else after.x
        ny = y if y is not None else min(after.y + after.height + 16, self.page_height - 80)
        nw = width if width is not None else after.width
        nh = height if height is not None else after.height
        nxt = self.add_text_frame(x=nx, y=ny, width=nw, height=nh, font_size=after.font_size)
        after.next_id = nxt.id
        return nxt

    def flow_text(
        self,
        text: str,
        frame: Optional[TextFrame] = None,
        chars_per_line: int | None = None,
    ) -> str:
        """
        Einfacher Textumfluss in einem Rahmen (Wortgrenzen).
        """
        cpl = chars_per_line or (frame.chars_per_line if frame else 70)
        result = _wrap_words(text, cpl)
        if frame is not None:
            frame.text = result
        return result

    def flow_text_chain(self, text: str, start: TextFrame) -> Dict[str, str]:
        """
        Verketteter Textumfluss: füllt start, Overflow in next_id-Kette.
        Rückgabe: {frame_id: text_in_frame}
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
            # Zeilen bis Kapazität
            chunk, remaining = _take_chars_wrapped(remaining, capacity, cpl)
            current.text = chunk
            result[current.id] = chunk
            if not remaining:
                # Restkette leeren
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
                # Overflow ohne Folgeahmen: Rest an aktuellen Rahmen anhängen (markiert)
                current.text = (current.text + "\n[…]").strip()
                result[current.id] = current.text
                result["__overflow__"] = remaining
                remaining = ""
                break
        return result

    def to_dict(self) -> dict:
        return {
            "page_width": self.page_width,
            "page_height": self.page_height,
            "text_frames": [asdict(f) for f in self.text_frames],
            "image_frames": [asdict(f) for f in self.image_frames],
        }

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: str | Path) -> "LayoutDocument":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        doc = cls(
            page_width=float(data.get("page_width", 595)),
            page_height=float(data.get("page_height", 842)),
        )
        for tf in data.get("text_frames", []):
            doc.text_frames.append(TextFrame(**tf))
        for im in data.get("image_frames", []):
            doc.image_frames.append(ImageFrame(**im))
        return doc


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


def _take_chars_wrapped(text: str, capacity: int, chars_per_line: int) -> tuple[str, str]:
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
