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


def _page_index_from_page_obj(pdf: pikepdf.Pdf, page_obj) -> Optional[int]:
    """Seitenindex über objgen (nicht ==) — strukturell gleiche Blank-Pages sonst immer 0."""
    if page_obj is None:
        return None
    try:
        target = getattr(page_obj, "objgen", None)
        if target is None:
            return None
        for i, page in enumerate(pdf.pages):
            if getattr(page.obj, "objgen", None) == target:
                return i
    except Exception:
        return None
    return None


def _page_index_from_dest(pdf: pikepdf.Pdf, dest) -> Optional[int]:
    if dest is None:
        return None
    try:
        # Explizites Array [page, /Fit, …] oder Integer-Seitenzahl
        if isinstance(dest, int):
            n = len(pdf.pages)
            return dest if 0 <= dest < n else None
        try:
            # pikepdf.Integer / Number
            if hasattr(dest, "as_int"):
                idx = int(dest.as_int())
                n = len(pdf.pages)
                return idx if 0 <= idx < n else None
        except Exception:
            pass
        if isinstance(dest, pikepdf.Array) and len(dest) > 0:
            return _page_index_from_page_obj(pdf, dest[0])
        # Dictionary mit /D oder /Page
        if isinstance(dest, pikepdf.Dictionary):
            if "/D" in dest:
                return _page_index_from_dest(pdf, dest["/D"])
            if "/Page" in dest:
                return _page_index_from_page_obj(pdf, dest["/Page"])
    except Exception:
        return None
    return None


def _page_index_from_outline_item(pdf: pikepdf.Pdf, ol) -> Optional[int]:
    """
    Zielfseite eines OutlineItems robust auflösen.
    Bevorzugt resolved_destination (Array/int/named), sonst Destination/Action /GoTo.
    """
    # 1) resolved_destination — deckt Array, int und Named Dest ab
    try:
        resolver = getattr(ol, "resolved_destination", None)
        if callable(resolver):
            rd = resolver(pdf)
            if rd is not None:
                page = getattr(rd, "page", None)
                idx = _page_index_from_page_obj(pdf, page)
                if idx is not None:
                    return idx
    except Exception:
        pass

    # 2) Roh-Destination
    dest = getattr(ol, "destination", None)
    idx = _page_index_from_dest(pdf, dest)
    if idx is not None:
        return idx

    # 3) GoTo-Action (/S /GoTo, /D …)
    try:
        action = getattr(ol, "action", None)
        if action is None and hasattr(ol, "obj"):
            action = ol.obj.get("/A") if hasattr(ol.obj, "get") else None
        if action is not None:
            subtype = None
            try:
                subtype = str(action.get("/S", "")) if hasattr(action, "get") else None
            except Exception:
                subtype = None
            if subtype in (None, "/GoTo", "GoTo", "/Goto"):
                d = action.get("/D") if hasattr(action, "get") else None
                idx = _page_index_from_dest(pdf, d)
                if idx is not None:
                    return idx
    except Exception:
        pass
    return None


def _from_pike_item(pdf: pikepdf.Pdf, ol) -> OutlineItem:
    title = str(getattr(ol, "title", "") or "(ohne Titel)")
    page_idx = _page_index_from_outline_item(pdf, ol)
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


def flatten_outline_pages(items: Sequence[OutlineItem]) -> List[Tuple[int, str]]:
    """
    Outline-Baum flach: [(page_index, title), …] in DFS-Reihenfolge.
    Einträge ohne Seiten-Ziel werden übersprungen; doppelte Seiten bleiben.
    """
    out: List[Tuple[int, str]] = []

    def walk(nodes: Sequence[OutlineItem]) -> None:
        for node in nodes or []:
            if not isinstance(node, OutlineItem):
                continue
            if node.page_index is not None and int(node.page_index) >= 0:
                title = (node.title or "").strip() or f"Seite {int(node.page_index) + 1}"
                out.append((int(node.page_index), title))
            if node.children:
                walk(node.children)

    walk(items)
    return out


def outline_from_pages(
    pages: Sequence[Tuple[int, str] | int],
) -> List[OutlineItem]:
    """Flache Outline-Liste aus Seitenfavoriten [(page, title)|page, …]."""
    items: List[OutlineItem] = []
    seen: set[int] = set()
    for entry in pages or []:
        if isinstance(entry, (list, tuple)) and len(entry) >= 1:
            page = int(entry[0])
            title = str(entry[1]).strip() if len(entry) > 1 else ""
        else:
            page = int(entry)
            title = ""
        if page < 0 or page in seen:
            continue
        seen.add(page)
        items.append(
            OutlineItem(
                title=title or f"Seite {page + 1}",
                page_index=page,
            )
        )
    return items


def write_outline(
    pdf_path: str | Path,
    items: Sequence[OutlineItem],
    *,
    out_path: str | Path | None = None,
) -> Path:
    """
    Gesamtes PDF-Outline ersetzen (Import/Export-Ziel).
    Leere Liste → Outline entfernen.
    """
    pdf_path = Path(pdf_path)
    out_path = Path(out_path) if out_path else pdf_path
    overwrite = out_path.resolve() == pdf_path.resolve()

    def _append_nodes(parent_list, nodes: Sequence[OutlineItem], n_pages: int) -> None:
        for node in nodes or []:
            if not isinstance(node, OutlineItem):
                continue
            title = (node.title or "").strip() or "Lesezeichen"
            page = node.page_index
            if page is None or page < 0 or page >= n_pages:
                # Kinder ohne gültige Seite: Titelknoten auf Seite 0 falls Kinder existieren
                if node.children:
                    page = 0
                else:
                    continue
            oi = pikepdf.OutlineItem(title, int(page))
            parent_list.append(oi)
            if node.children:
                _append_nodes(oi.children, node.children, n_pages)

    with pikepdf.open(pdf_path, allow_overwriting_input=overwrite) as pdf:
        n = len(pdf.pages)
        with pdf.open_outline() as outline:
            outline.root.clear()
            _append_nodes(outline.root, items, n)
        if overwrite:
            pdf.save()
        else:
            pdf.save(out_path)
    return out_path
