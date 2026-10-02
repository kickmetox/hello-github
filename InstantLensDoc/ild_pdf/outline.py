"""PDF-Lesezeichen / Outline (pikepdf) — lesen und editieren."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

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
            with pdf.open_outline() as outline:
                if outline is None:
                    return []
                items: List[OutlineItem] = []
                root = getattr(outline, "root", None)
                if root is None:
                    return []
                for ol in root:
                    items.append(_from_pike_item(pdf, ol))
                return items
        except Exception:
            return []


def _navigate_children(root, path: Sequence[int]):
    """Liefert die Kind-Liste am Pfad (leer = root)."""
    node = root
    for idx in path:
        if idx < 0 or idx >= len(node):
            raise IndexError(f"Outline-Pfad ungültig: {tuple(path)}")
        node = node[idx].children
    return node


def add_outline_item(
    pdf_path: str | Path,
    title: str,
    page_index: int,
    *,
    parent_path: Sequence[int] = (),
) -> Tuple[int, ...]:
    """
    Lesezeichen hinzufügen und speichern.
    parent_path: Indizes vom Root bis zum Elternknoten (leer = Top-Level).
    Rückgabe: Pfad des neuen Eintrags (parent_path + Index).
    """
    pdf_path = Path(pdf_path)
    title = (title or "").strip() or "Lesezeichen"
    page_index = int(page_index)
    parent_path = tuple(int(i) for i in parent_path)
    with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
        n = len(pdf.pages)
        if page_index < 0 or page_index >= n:
            raise IndexError(f"Seite {page_index} existiert nicht (0..{n - 1})")
        with pdf.open_outline() as outline:
            parent = _navigate_children(outline.root, parent_path)
            parent.append(pikepdf.OutlineItem(title, page_index))
            new_index = len(parent) - 1
        pdf.save(pdf_path)
    return parent_path + (new_index,)


def delete_outline_item(pdf_path: str | Path, item_path: Sequence[int]) -> None:
    """
    Lesezeichen löschen (inkl. Kinder) und speichern.
    item_path: Indizes vom Root zum zu löschenden Eintrag (mind. ein Index).
    """
    pdf_path = Path(pdf_path)
    item_path = tuple(int(i) for i in item_path)
    if not item_path:
        raise ValueError("item_path darf nicht leer sein")
    with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
        with pdf.open_outline() as outline:
            parent = _navigate_children(outline.root, item_path[:-1])
            idx = item_path[-1]
            if idx < 0 or idx >= len(parent):
                raise IndexError(f"Outline-Pfad ungültig: {item_path}")
            del parent[idx]
        pdf.save(pdf_path)
