"""Select-then-tool: Rahmen, aktive Story oder Caret/Absatz."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional


TEXT_TOOLS = frozenset(
    {
        "font",
        "style",
        "text",
        "bold",
        "italic",
        "underline",
        "fill_text",
        "typography",
        "dropcap",
        "hyphenate",
        "leading",
    }
)
OBJECT_TOOLS = frozenset({"fill", "stroke", "wrap", "object", "envelope", "extrude", "clip"})


@dataclass
class ToolHit:
    """Ergebnis der Zielauflösung für ein Layout-Werkzeug."""

    scope: str  # caret_selection | caret_paragraph | frames | story | all_text | all_objects
    frames: list = field(default_factory=list)
    item: Any = None
    has_text_selection: bool = False
    role: str = ""

    @property
    def ids(self) -> list[str]:
        return [getattr(f, "id", "") for f in self.frames]

    @property
    def is_caret(self) -> bool:
        return self.scope in ("caret_selection", "caret_paragraph")


def is_text_tool(role: str) -> bool:
    return (role or "").lower() in TEXT_TOOLS


def is_object_tool(role: str) -> bool:
    r = (role or "").lower()
    return r in OBJECT_TOOLS or r == "fill"


def story_or_all_text(doc, selected: Iterable[Any] | None = None) -> list:
    """Aktive Story (Kettenkopf) oder alle Textrahmen im Layout."""
    texts = [f for f in (selected or ()) if getattr(f, "kind", "") == "text"]
    if texts:
        head = doc.chain_head(texts[0])
        return doc.chain_members(head)
    sid = getattr(doc, "active_story_id", "") or ""
    if sid:
        head = doc.frame_by_id(sid)
        if head is not None and head.kind == "text":
            return doc.chain_members(doc.chain_head(head))
    return [f for f in doc.frames if f.kind == "text" and not getattr(f, "master", False)]
