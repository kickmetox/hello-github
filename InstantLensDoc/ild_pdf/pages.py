"""PDF-Seitenoperationen via pikepdf."""

from __future__ import annotations

from pathlib import Path
from typing import List, Sequence, Tuple

import pikepdf

# Breite × Höhe in PDF-Punkten (1 pt = 1/72 Zoll)
PAGE_SIZE_PRESETS: dict[str, Tuple[float, float]] = {
    "A4": (595.28, 841.89),
    "A5": (419.53, 595.28),
    "Letter": (612.0, 792.0),
    "Legal": (612.0, 1008.0),
    "A3": (841.89, 1190.55),
}

PT_PER_INCH = 72.0
MM_PER_INCH = 25.4


def pt_to_mm(pt: float) -> float:
    return float(pt) / PT_PER_INCH * MM_PER_INCH


def pt_to_inch(pt: float) -> float:
    return float(pt) / PT_PER_INCH


def mm_to_pt(mm: float) -> float:
    return float(mm) / MM_PER_INCH * PT_PER_INCH


def inch_to_pt(inch: float) -> float:
    return float(inch) * PT_PER_INCH


def format_size_pair(
    width_pt: float,
    height_pt: float,
    unit: str = "mm",
    *,
    decimals: int | None = None,
) -> str:
    """Format width×height in mm or inch (from PDF points)."""
    u = (unit or "mm").lower().strip()
    if u in ("in", "inch", "inches", '"'):
        w, h = pt_to_inch(width_pt), pt_to_inch(height_pt)
        d = 2 if decimals is None else decimals
        return f"{w:.{d}f}×{h:.{d}f} in"
    w, h = pt_to_mm(width_pt), pt_to_mm(height_pt)
    d = 1 if decimals is None else decimals
    return f"{w:.{d}f}×{h:.{d}f} mm"


def convert_pt(value_pt: float, unit: str = "mm") -> float:
    """Punktwert in mm oder inch umrechnen."""
    u = (unit or "mm").lower().strip()
    if u in ("in", "inch", "inches", '"'):
        return pt_to_inch(value_pt)
    return pt_to_mm(value_pt)


def to_pt(value: float, unit: str = "mm") -> float:
    """mm oder inch → PDF-Punkte."""
    u = (unit or "mm").lower().strip()
    if u in ("in", "inch", "inches", '"'):
        return inch_to_pt(value)
    return mm_to_pt(value)


def rotate_page(path: str | Path, page_index: int, degrees: int = 90) -> None:
    """Seite um degrees drehen (90/180/270/−90) und speichern."""
    path = Path(path)
    degrees = int(degrees) % 360
    with pikepdf.open(path, allow_overwriting_input=True) as pdf:
        if page_index < 0 or page_index >= len(pdf.pages):
            raise IndexError(f"Seite {page_index} existiert nicht")
        page = pdf.pages[page_index]
        current = int(page.get("/Rotate", 0) or 0)
        page["/Rotate"] = (current + degrees) % 360
        pdf.save(path)


def flip_page(
    path: str | Path,
    page_index: int,
    *,
    horizontal: bool = False,
    vertical: bool = False,
) -> None:
    """
    Seite horizontal (links↔rechts) und/oder vertikal (oben↔unten) spiegeln und speichern.
    Transformation wird um den Content-Stream gelegt (MediaBox).
    """
    if not horizontal and not vertical:
        raise ValueError("horizontal und/oder vertical muss True sein")
    path = Path(path)
    with pikepdf.open(path, allow_overwriting_input=True) as pdf:
        if page_index < 0 or page_index >= len(pdf.pages):
            raise IndexError(f"Seite {page_index} existiert nicht")
        page = pdf.pages[page_index]
        mb = page.mediabox
        llx, lly = float(mb[0]), float(mb[1])
        urx, ury = float(mb[2]), float(mb[3])
        # PDF-Koordinaten: Ursprung unten links
        a, b, c, d, e, f = 1.0, 0.0, 0.0, 1.0, 0.0, 0.0
        if horizontal:
            # x' = -x + (llx+urx)
            a, e = -1.0, llx + urx
        if vertical:
            # y' = -y + (lly+ury)
            d, f = -1.0, lly + ury
        prefix = f"q {a:g} {b:g} {c:g} {d:g} {e:g} {f:g} cm\n".encode("ascii")
        page.contents_add(prefix, prepend=True)
        page.contents_add(b"\nQ\n", prepend=False)
        pdf.save(path)


def insert_blank_page(
    path: str | Path,
    at_index: int | None = None,
    *,
    width: float | None = None,
    height: float | None = None,
) -> int:
    """
    Leere Seite einfügen und speichern.
    at_index: Einfügeposition (0-basiert); None = Ans Ende.
    Größe: width/height oder MediaBox der Nachbarseite bzw. A4.
    Rückgabe: Index der neuen Seite.
    """
    path = Path(path)
    with pikepdf.open(path, allow_overwriting_input=True) as pdf:
        n = len(pdf.pages)
        insert_at = n if at_index is None else int(at_index)
        if insert_at < 0 or insert_at > n:
            raise IndexError(f"Einfügeposition {insert_at} ungültig (0..{n})")
        ref_idx = min(insert_at, n - 1) if n else None
        if width is None or height is None:
            if ref_idx is not None:
                box = pdf.pages[ref_idx].mediabox
                w = float(box[2] - box[0])
                h = float(box[3] - box[1])
            else:
                w, h = PAGE_SIZE_PRESETS["A4"]
            width = float(width) if width is not None else w
            height = float(height) if height is not None else h
        if width <= 1 or height <= 1:
            raise ValueError("Seitengröße muss > 1 pt sein")
        tmp = pikepdf.Pdf.new()
        tmp.add_blank_page(page_size=(float(width), float(height)))
        if insert_at >= n:
            pdf.pages.append(tmp.pages[0])
            insert_at = len(pdf.pages) - 1
        else:
            pdf.pages.insert(insert_at, tmp.pages[0])
        pdf.save(path)
        return insert_at


def duplicate_page(path: str | Path, page_index: int, *, after: bool = True) -> int:
    """
    Seite duplizieren und speichern.
    after=True: Kopie direkt hinter dem Original; sonst davor.
    Rückgabe: Index der neuen Seite.
    """
    path = Path(path)
    with pikepdf.open(path, allow_overwriting_input=True) as pdf:
        n = len(pdf.pages)
        if page_index < 0 or page_index >= n:
            raise IndexError(f"Seite {page_index} existiert nicht")
        tmp = pikepdf.Pdf.new()
        tmp.pages.append(pdf.pages[page_index])
        insert_at = page_index + 1 if after else page_index
        pdf.pages.insert(insert_at, tmp.pages[0])
        pdf.save(path)
        return insert_at


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


def extract_page_range(
    path: str | Path,
    dest: str | Path,
    start: int,
    end: int,
    *,
    one_based: bool = False,
) -> Path:
    """
    Seitenbereich von–bis in ein neues PDF extrahieren (inklusive Endseite).
    start/end: 0-basiert, oder 1-basiert wenn one_based=True.
    Quell-PDF bleibt unverändert.
    """
    path = Path(path)
    dest = Path(dest)
    if one_based:
        start = int(start) - 1
        end = int(end) - 1
    else:
        start = int(start)
        end = int(end)
    with pikepdf.open(path) as pdf:
        n = len(pdf.pages)
        if n == 0:
            raise ValueError("PDF hat keine Seiten")
        if start < 0 or end >= n or start > end:
            raise ValueError(f"Ungültiger Bereich {start + 1}–{end + 1} (1..{n})")
        out = pikepdf.Pdf.new()
        for p in range(start, end + 1):
            out.pages.append(pdf.pages[p])
        dest.parent.mkdir(parents=True, exist_ok=True)
        out.save(dest)
    return dest


def split_into_single_page_pdfs(
    path: str | Path,
    dest_dir: str | Path,
) -> List[Path]:
    """
    Jede Seite als eigene PDF-Datei in dest_dir speichern.
    Dateinamen: ``{stem}_p{N}.pdf`` (1-basiert). Quell-PDF unverändert.
    """
    return split_pdf(path, dest_dir, single_pages=True)


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


def _box_tuple(box) -> Tuple[float, float, float, float]:
    return (float(box[0]), float(box[1]), float(box[2]), float(box[3]))


def get_page_boxes(path: str | Path, page_index: int) -> dict[str, Tuple[float, float, float, float]]:
    """MediaBox / CropBox (l,b,r,t) für eine Seite."""
    path = Path(path)
    with pikepdf.open(path) as pdf:
        if page_index < 0 or page_index >= len(pdf.pages):
            raise IndexError(f"Seite {page_index} existiert nicht")
        page = pdf.pages[page_index]
        media = _box_tuple(page.mediabox)
        crop = _box_tuple(page.cropbox) if page.get("/CropBox") is not None else media
        return {"mediabox": media, "cropbox": crop}


def set_page_size(
    path: str | Path,
    page_index: int,
    width: float,
    height: float,
    *,
    out_path: str | Path | None = None,
    all_pages: bool = False,
) -> Path:
    """
    Setzt MediaBox (und CropBox) auf width×height ab Ursprung (0,0).
    Basis-Zuschneiden der Seitenfläche — Inhalt wird nicht skaliert.
    """
    path = Path(path)
    out_path = Path(out_path) if out_path else path
    if width <= 1 or height <= 1:
        raise ValueError("Seitengröße muss > 1 pt sein")
    overwrite = out_path.resolve() == path.resolve()
    with pikepdf.open(path, allow_overwriting_input=overwrite) as pdf:
        indices = range(len(pdf.pages)) if all_pages else [page_index]
        for i in indices:
            if i < 0 or i >= len(pdf.pages):
                raise IndexError(f"Seite {i} existiert nicht")
            page = pdf.pages[i]
            box = pikepdf.Array([0, 0, float(width), float(height)])
            page.mediabox = box
            page.cropbox = box
        out_path.parent.mkdir(parents=True, exist_ok=True)
        pdf.save(out_path)
    return out_path


def set_crop_box(
    path: str | Path,
    page_index: int,
    left: float,
    bottom: float,
    right: float,
    top: float,
    *,
    out_path: str | Path | None = None,
) -> Path:
    """Setzt CropBox in PDF-Koordinaten (Ursprung unten links)."""
    path = Path(path)
    out_path = Path(out_path) if out_path else path
    if right <= left or top <= bottom:
        raise ValueError("CropBox: right>left und top>bottom erforderlich")
    overwrite = out_path.resolve() == path.resolve()
    with pikepdf.open(path, allow_overwriting_input=overwrite) as pdf:
        if page_index < 0 or page_index >= len(pdf.pages):
            raise IndexError(f"Seite {page_index} existiert nicht")
        page = pdf.pages[page_index]
        page.cropbox = pikepdf.Array([float(left), float(bottom), float(right), float(top)])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        pdf.save(out_path)
    return out_path
