"""Schwärzung (Redaction): Sidecar-Annotation + optionales Einbrennen."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

from .annotate import Annotation, AnnotationStore, AnnotationType


def bake_redactions(
    pdf_path: str | Path,
    store: AnnotationStore | Sequence[Annotation],
    *,
    scale: float = 1.5,
    out_path: str | Path | None = None,
    remove_from_store: bool = False,
) -> Path:
    """
    Brennt REDACTION-Rechtecke als undurchsichtige schwarze Flächen in das PDF ein.
    Store-Koordinaten = Render-Pixel bei `scale` (Y von oben).
    """
    import pikepdf
    from pikepdf import Name, Stream

    pdf_path = Path(pdf_path)
    out_path = Path(out_path) if out_path else pdf_path
    if isinstance(store, AnnotationStore):
        anns = list(store.annotations)
    else:
        anns = list(store)

    by_page: dict[int, list[Annotation]] = {}
    for a in anns:
        if a.type == AnnotationType.REDACTION:
            by_page.setdefault(a.page, []).append(a)

    with pikepdf.open(pdf_path, allow_overwriting_input=(out_path.resolve() == pdf_path.resolve())) as pdf:
        for page_index, items in by_page.items():
            if page_index < 0 or page_index >= len(pdf.pages):
                continue
            page = pdf.pages[page_index]
            mediabox = page.mediabox
            page_h = float(mediabox[3] - mediabox[1])
            parts: list[str] = ["q", "0 0 0 rg"]
            for a in items:
                x = a.x / max(scale, 0.01)
                y_top = a.y / max(scale, 0.01)
                w = max(a.width, 1.0) / max(scale, 0.01)
                h = max(a.height, 1.0) / max(scale, 0.01)
                y_pdf = page_h - y_top - h
                parts.append(f"{x:.2f} {y_pdf:.2f} {w:.2f} {h:.2f} re f")
            parts.append("Q")
            content = "\n".join(parts).encode("latin-1", errors="replace")
            new_stream = Stream(pdf, content)
            if Name.Contents in page:
                existing = page[Name.Contents]
                if isinstance(existing, pikepdf.Array):
                    existing.append(new_stream)
                else:
                    page[Name.Contents] = pikepdf.Array([existing, new_stream])
            else:
                page[Name.Contents] = new_stream
        pdf.save(out_path)

    if remove_from_store and isinstance(store, AnnotationStore) and by_page:
        keep = [a for a in store.annotations if a.type != AnnotationType.REDACTION]
        if len(keep) != len(store.annotations):
            with store.atomic():
                store.annotations = keep
                store.dirty = True
            store.save(force=True)
    return out_path
