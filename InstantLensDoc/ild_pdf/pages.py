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


def merge_pdfs(sources: Sequence[str | Path], dest: str | Path) -> None:
    """Mehrere PDFs zu einer Datei zusammenführen (Reihenfolge wie sources)."""
    dest = Path(dest)
    if not sources:
        raise ValueError("Keine Quelldateien")
    out = pikepdf.Pdf.new()
    for src in sources:
        src = Path(src)
        with pikepdf.open(src) as pdf:
            for page in pdf.pages:
                out.pages.append(page)
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest)


def split_pdf(
    path: str | Path,
    dest_dir: str | Path,
    *,
    every_n: int | None = None,
    ranges: Sequence[tuple[int, int]] | None = None,
    single_pages: bool = False,
) -> List[Path]:
    """
    PDF teilen. Seiten 0-basiert, ranges inklusive Endseite.
    single_pages: eine PDF pro Seite.
    """
    path = Path(path)
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []
    stem = path.stem
    with pikepdf.open(path) as pdf:
        n = len(pdf.pages)
        chunks: List[tuple[int, int]] = []
        if single_pages:
            chunks = [(i, i) for i in range(n)]
        elif ranges:
            for start, end in ranges:
                if start < 0 or end >= n or start > end:
                    raise ValueError(f"Ungültiger Bereich {start}-{end} (0..{n - 1})")
                chunks.append((start, end))
        elif every_n and every_n > 0:
            i = 0
            while i < n:
                chunks.append((i, min(i + every_n - 1, n - 1)))
                i += every_n
        else:
            raise ValueError("split_pdf: every_n, ranges oder single_pages angeben")
        for idx, (start, end) in enumerate(chunks):
            out = pikepdf.Pdf.new()
            for p in range(start, end + 1):
                out.pages.append(pdf.pages[p])
            label = f"{stem}_p{start + 1}-{end + 1}" if start != end else f"{stem}_p{start + 1}"
            if len(chunks) > 1 and single_pages:
                label = f"{stem}_p{start + 1}"
            out_path = dest_dir / f"{label}.pdf"
            out.save(out_path)
            written.append(out_path)
    return written


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
