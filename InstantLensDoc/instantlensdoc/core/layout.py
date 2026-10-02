"""Einfaches Layout: Textrahmen, Bild, Basis-Textumfluss."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
from uuid import uuid4


@dataclass
class TextFrame:
    x: float
    y: float
    width: float
    height: float
    text: str = ""
    font_size: int = 12
    id: str = field(default_factory=lambda: uuid4().hex[:8])


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
    """Sehr einfaches Seitenlayout (eine Seite)."""

    page_width: float = 595.0
    page_height: float = 842.0
    text_frames: List[TextFrame] = field(default_factory=list)
    image_frames: List[ImageFrame] = field(default_factory=list)

    def add_text_frame(
        self,
        text: str = "",
        x: float = 40,
        y: float = 40,
        width: float = 515,
        height: float = 200,
    ) -> TextFrame:
        frame = TextFrame(x=x, y=y, width=width, height=height, text=text)
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

    def flow_text(self, text: str, frame: Optional[TextFrame] = None, chars_per_line: int = 70) -> str:
        """
        Sehr einfacher Textumfluss: bricht an Wortgrenzen um.
        (Kein echter Glyph-basierter Umbruch — MVP.)
        """
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
        result = "\n".join(lines)
        if frame is not None:
            frame.text = result
        return result
