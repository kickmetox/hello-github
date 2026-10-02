"""PDF-Seitenoperationen via pikepdf."""

from __future__ import annotations

from pathlib import Path
from typing import List, Sequence

import pikepdf


def rotate_page(path: str | Path, page_index: int, degrees: int = 90) -> None:
    """Seite um degrees drehen (90/180/270) und speichern."""
    path = Path(path)
    degrees = degrees % 360
    with pikepdf.open(path, allow_overwriting_input=True) as pdf:
        if page_index < 0 or page_index >= len(pdf.pages):
            raise IndexError(f"Seite {page_index} existiert nicht")
        page = pdf.pages[page_index]
        current = int(page.get("/Rotate", 0) or 0)
        page["/Rotate"] = (current + degrees) % 360
        pdf.save(path)


def delete_pages(path: str | Path, indices: Sequence[int]) -> None:
    """Seiten löschen (0-basiert) und speichern."""
    path = Path(path)
    to_delete = sorted(set(indices), reverse=True)
    with pikepdf.open(path, allow_overwriting_input=True) as pdf:
        for i in to_delete:
            if 0 <= i < len(pdf.pages):
                del pdf.pages[i]
        if len(pdf.pages) == 0:
            raise ValueError("PDF darf nicht leer werden")
        pdf.save(path)


def reorder_pages(path: str | Path, new_order: List[int]) -> None:
    """Seiten neu anordnen. new_order = Liste alter Indizes in neuer Reihenfolge."""
    path = Path(path)
    with pikepdf.open(path) as pdf:
        if sorted(new_order) != list(range(len(pdf.pages))):
            raise ValueError("new_order muss jede Seite genau einmal enthalten")
        pages = [pdf.pages[i] for i in new_order]
        # Neue Datei schreiben, um Referenzen sauber zu halten
        out = pikepdf.Pdf.new()
        for p in pages:
            out.pages.append(p)
        out.save(path)
