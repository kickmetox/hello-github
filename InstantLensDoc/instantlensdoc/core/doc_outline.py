"""Dokumentstruktur / Outline-Pane jenseits reiner TOC — 2.6.26.

Kombiniert:
- Markdown-/Text-Überschriften (H1–H6)
- PDF-Lesezeichen (Outline)
- optionale Zeilen-Favoriten / Bookmarks

Für Sidebar-Navigation (Struktur), nicht nur TOC-Einfügen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence

from instantlensdoc import __version__

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_ATX_SETTEXT = re.compile(r"^(=+|-+)\s*$")


@dataclass
class StructureNode:
    """Ein Knoten der Dokumentstruktur."""

    title: str
    kind: str  # heading | bookmark | favorite
    level: int = 1
    page_index: Optional[int] = None  # 0-basiert PDF
    line: Optional[int] = None  # 1-basiert Text
    anchor: str = ""
    children: List["StructureNode"] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "kind": self.kind,
            "level": int(self.level),
            "page_index": self.page_index,
            "line": self.line,
            "anchor": self.anchor,
            "children": [c.to_dict() for c in self.children],
        }


def _slug(title: str) -> str:
    s = re.sub(r"[^\w\-]+", "-", (title or "").strip().lower(), flags=re.UNICODE)
    return s.strip("-") or "section"


def extract_heading_structure(text: str, *, max_level: int = 6) -> List[StructureNode]:
    """Überschriften-Baum aus Markdown/Text (ATX + Setext)."""
    max_level = max(1, min(6, int(max_level or 6)))
    lines = (text or "").splitlines()
    flat: list[StructureNode] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _HEADING_RE.match(line)
        if m:
            lvl = len(m.group(1))
            title = m.group(2).strip()
            if 1 <= lvl <= max_level and title:
                flat.append(
                    StructureNode(
                        title=title,
                        kind="heading",
                        level=lvl,
                        line=i + 1,
                        anchor=_slug(title),
                    )
                )
            i += 1
            continue
        # Setext: Titel\n===
        if i + 1 < len(lines) and line.strip() and _ATX_SETTEXT.match(lines[i + 1] or ""):
            underline = (lines[i + 1] or "").strip()
            lvl = 1 if underline.startswith("=") else 2
            title = line.strip()
            if lvl <= max_level and title:
                flat.append(
                    StructureNode(
                        title=title,
                        kind="heading",
                        level=lvl,
                        line=i + 1,
                        anchor=_slug(title),
                    )
                )
            i += 2
            continue
        i += 1
    return _nest_by_level(flat)


def _nest_by_level(flat: Sequence[StructureNode]) -> List[StructureNode]:
    root: list[StructureNode] = []
    stack: list[StructureNode] = []
    for node in flat:
        while stack and stack[-1].level >= node.level:
            stack.pop()
        if not stack:
            root.append(node)
        else:
            stack[-1].children.append(node)
        stack.append(node)
    return root


def bookmarks_to_structure(items: Sequence[Any]) -> List[StructureNode]:
    """PDF-OutlineItem-Baum → StructureNode."""
    out: list[StructureNode] = []
    for it in items or []:
        title = str(getattr(it, "title", None) or getattr(it, "get", lambda *_: "")("title") or "")
        if not title and isinstance(it, dict):
            title = str(it.get("title") or "")
        page = getattr(it, "page_index", None)
        if page is None and isinstance(it, dict):
            page = it.get("page_index")
        children_raw = getattr(it, "children", None)
        if children_raw is None and isinstance(it, dict):
            children_raw = it.get("children") or []
        node = StructureNode(
            title=title or "(ohne Titel)",
            kind="bookmark",
            level=1,
            page_index=int(page) if page is not None else None,
            anchor=_slug(title),
            children=bookmarks_to_structure(children_raw or []),
        )
        out.append(node)
    return out


def favorites_to_structure(
    pages: Sequence[tuple[int, str] | int] | None,
) -> List[StructureNode]:
    """Seitenfavoriten → flache StructureNodes."""
    nodes: list[StructureNode] = []
    for entry in pages or []:
        if isinstance(entry, (list, tuple)) and len(entry) >= 1:
            page = int(entry[0])
            title = str(entry[1]).strip() if len(entry) > 1 else ""
        else:
            page = int(entry)
            title = ""
        if page < 0:
            continue
        nodes.append(
            StructureNode(
                title=title or f"Seite {page + 1}",
                kind="favorite",
                level=1,
                page_index=page,
                anchor=f"page-{page + 1}",
            )
        )
    return nodes


def build_document_outline(
    *,
    text: str | None = None,
    pdf_path: str | Path | None = None,
    favorites: Sequence[tuple[int, str] | int] | None = None,
    max_level: int = 6,
    include_headings: bool = True,
    include_bookmarks: bool = True,
    include_favorites: bool = True,
) -> dict[str, Any]:
    """
    Gesamte Dokumentstruktur für das Outline-Pane.

    Rückgabe: ``{sections: [...], counts: {...}, version}``
    """
    sections: list[StructureNode] = []
    counts = {"heading": 0, "bookmark": 0, "favorite": 0}

    if include_headings and text:
        heads = extract_heading_structure(text, max_level=max_level)
        if heads:
            wrap = StructureNode(
                title="Überschriften",
                kind="heading",
                level=0,
                children=heads,
            )
            sections.append(wrap)
            counts["heading"] = _count_kind(heads, "heading")

    if include_bookmarks and pdf_path:
        try:
            from ild_pdf.outline import extract_outline

            bm = extract_outline(pdf_path)
            bm_nodes = bookmarks_to_structure(bm)
            if bm_nodes:
                wrap = StructureNode(
                    title="Lesezeichen",
                    kind="bookmark",
                    level=0,
                    children=bm_nodes,
                )
                sections.append(wrap)
                counts["bookmark"] = _count_kind(bm_nodes, "bookmark")
        except Exception:
            pass

    if include_favorites and favorites:
        fav = favorites_to_structure(favorites)
        if fav:
            wrap = StructureNode(
                title="Favoriten",
                kind="favorite",
                level=0,
                children=fav,
            )
            sections.append(wrap)
            counts["favorite"] = len(fav)

    return {
        "sections": [s.to_dict() for s in sections],
        "counts": counts,
        "total": sum(counts.values()),
        "version": __version__,
    }


def flatten_structure(
    sections: Sequence[dict[str, Any] | StructureNode],
) -> list[dict[str, Any]]:
    """DFS flach für Listen/Filter."""
    out: list[dict[str, Any]] = []

    def walk(nodes: Iterable[Any], depth: int = 0) -> None:
        for n in nodes or []:
            if isinstance(n, StructureNode):
                d = n.to_dict()
                kids = d.pop("children", [])
            elif isinstance(n, dict):
                d = dict(n)
                kids = d.pop("children", []) or []
            else:
                continue
            if int(d.get("level", 1) or 1) == 0 and not d.get("page_index") and not d.get("line"):
                # Gruppenkopf
                walk(kids, depth)
                continue
            d["depth"] = depth
            out.append(d)
            walk(kids, depth + 1)

    walk(sections)
    return out


def _count_kind(nodes: Sequence[StructureNode], kind: str) -> int:
    n = 0
    for node in nodes or []:
        if node.kind == kind:
            n += 1
        n += _count_kind(node.children, kind)
    return n


def filter_structure(
    sections: Sequence[dict[str, Any]],
    query: str,
) -> list[dict[str, Any]]:
    """Einfacher Titel-Filter (casefold Substring)."""
    q = (query or "").strip().casefold()
    flat = flatten_structure(sections)
    if not q:
        return flat
    return [row for row in flat if q in str(row.get("title") or "").casefold()]
