"""PDF-Lesezeichen / Outline (pikepdf)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import pikepdf


@dataclass
class OutlineItem:
    title: str
    page_index: Optional[int] = None
    children: List["OutlineItem"] = field(default_factory=list)


def _page_index_from_dest(pdf: pikepdf.Pdf, dest) -> Optional[int]:
    if dest is None:
        return None
    try:
        page_obj = None
        if isinstance(dest, pikepdf.Array) and len(dest) > 0:
            page_obj = dest[0]
        if page_obj is None:
            return None
        for i, page in enumerate(pdf.pages):
            if page.obj == page_obj:
                return i
    except Exception:
        return None
    return None


def _from_pike_item(pdf: pikepdf.Pdf, ol) -> OutlineItem:
    title = str(getattr(ol, "title", "") or "(ohne Titel)")
    page_idx: Optional[int] = None
    dest = getattr(ol, "destination", None)
    if dest is not None:
        page_idx = _page_index_from_dest(pdf, dest)
    children: List[OutlineItem] = []
    for child in getattr(ol, "children", []) or []:
        children.append(_from_pike_item(pdf, child))
    return OutlineItem(title=title, page_index=page_idx, children=children)


def extract_outline(pdf_path: str | Path) -> List[OutlineItem]:
    """Lesezeichen-Baum; leere Liste wenn kein Outline."""
    pdf_path = Path(pdf_path)
    with pikepdf.open(pdf_path) as pdf:
        try:
            outline = pdf.open_outline()
        except Exception:
            return []
        if outline is None:
            return []
        items: List[OutlineItem] = []
        try:
            for ol in outline:
                items.append(_from_pike_item(pdf, ol))
        except Exception:
            return []
        return items
