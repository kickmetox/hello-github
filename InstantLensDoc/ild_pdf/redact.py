"""Schwärzung (Redaction): Sidecar-Annotation, Overlay-Bake und echtes Schwärzen (2.6.0).

``bake_redactions`` — Legacy: schwarze Flächen über den Content-Stream legen
(Text darunter kann noch selektierbar sein).

``apply_true_redactions`` — Irreversibel: betroffene Seiten werden gerastert,
Schwärzungszonen schwarz gefüllt und als Bildseite ohne Textschicht ersetzt;
optional Metadaten-Bereinigung (DocInfo/XMP).
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from .annotate import Annotation, AnnotationStore, AnnotationType


@dataclass
class TrueRedactionResult:
    """Ergebnis von ``apply_true_redactions`` — 2.6.0."""

    out_path: Path
    pages_redacted: int
    rect_count: int
    metadata_stripped: bool


def _collect_redactions(
    store: AnnotationStore | Sequence[Annotation],
) -> dict[int, list[Annotation]]:
    if isinstance(store, AnnotationStore):
        anns = list(store.annotations)
    else:
        anns = list(store)
    by_page: dict[int, list[Annotation]] = {}
    for a in anns:
        if a.type == AnnotationType.REDACTION:
            by_page.setdefault(int(a.page), []).append(a)
    return by_page


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

    Hinweis: Overlay-Modus — Text unter der Fläche kann in der Textschicht
    noch selektierbar sein. Für unwiderrufliches Schwärzen
    ``apply_true_redactions`` nutzen — 2.6.0.
    """
    import pikepdf
    from pikepdf import Name, Stream

    pdf_path = Path(pdf_path)
    out_path = Path(out_path) if out_path else pdf_path
    by_page = _collect_redactions(store)

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


def _page_image_to_pdf_bytes(img, page_w: float, page_h: float) -> bytes:
    """PIL-Bild → Einzelseiten-PDF-Bytes in Ziel-MediaBox-Größe (pt)."""
    from PIL import Image

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    pw = max(1, int(round(page_w)))
    ph = max(1, int(round(page_h)))
    canvas = Image.new("RGB", (pw, ph), "white")
    iw, ih = img.size
    sc = min(pw / max(iw, 1), ph / max(ih, 1))
    nw, nh = max(1, int(iw * sc)), max(1, int(ih * sc))
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
    ox = int((pw - nw) / 2)
    oy = int((ph - nh) / 2)
    canvas.paste(resized, (ox, oy))
    buf = io.BytesIO()
    canvas.save(buf, "PDF", resolution=72.0)
    return buf.getvalue()


def apply_true_redactions(
    pdf_path: str | Path,
    store: AnnotationStore | Sequence[Annotation],
    *,
    scale: float = 1.5,
    out_path: str | Path | None = None,
    remove_from_store: bool = False,
    strip_meta: bool = True,
    render_dpi: int = 150,
    password: str | None = None,
    fill_rgb: tuple[int, int, int] = (0, 0, 0),
) -> TrueRedactionResult:
    """
    Echtes / unwiderrufliches Schwärzen — 2.6.0.

    Für jede Seite mit REDACTION-Annotationen:
    1. Seite rendern (pypdfium2)
    2. Schwärzungszonen schwarz füllen
    3. Seite durch Bildseite ersetzen → Content-Stream/Textschicht der Seite weg

    Seiten ohne Schwärzung bleiben vektorial erhalten.
    Optional: DocInfo/XMP via ``strip_metadata`` bereinigen.
    """
    import pikepdf
    from PIL import ImageDraw

    from .metadata import strip_metadata
    from .render import render_page

    pdf_path = Path(pdf_path)
    if out_path is None:
        out_path = pdf_path.with_name(f"{pdf_path.stem}_redacted.pdf")
    else:
        out_path = Path(out_path)

    by_page = _collect_redactions(store)
    if not by_page:
        raise ValueError("Keine Schwärzungs-Annotationen (REDACTION) vorhanden.")

    ann_scale = max(float(scale), 0.01)
    dpi = max(72, min(600, int(render_dpi or 150)))
    render_scale = dpi / 72.0
    fill = tuple(max(0, min(255, int(c))) for c in fill_rgb)
    if len(fill) != 3:
        fill = (0, 0, 0)

    pages_redacted = 0
    rect_count = sum(len(v) for v in by_page.values())

    with pikepdf.open(pdf_path, password=password or "") as src:
        n_pages = len(src.pages)
        with pikepdf.Pdf.new() as dst:
            for i in range(n_pages):
                page = src.pages[i]
                items = by_page.get(i) or []
                if not items:
                    dst.pages.append(page)
                    continue
                mediabox = page.mediabox
                page_w = float(mediabox[2] - mediabox[0])
                page_h = float(mediabox[3] - mediabox[1])
                img = render_page(
                    pdf_path,
                    i,
                    scale=render_scale,
                    password=password,
                    use_cache=False,
                )
                if img.mode != "RGB":
                    img = img.convert("RGB")
                draw = ImageDraw.Draw(img)
                for a in items:
                    x = float(a.x) / ann_scale * render_scale
                    y = float(a.y) / ann_scale * render_scale
                    w = max(float(a.width), 1.0) / ann_scale * render_scale
                    h = max(float(a.height), 1.0) / ann_scale * render_scale
                    x0, y0 = min(x, x + w), min(y, y + h)
                    x1, y1 = max(x, x + w), max(y, y + h)
                    draw.rectangle([x0, y0, x1, y1], fill=fill)
                one_bytes = _page_image_to_pdf_bytes(img, page_w, page_h)
                with pikepdf.open(io.BytesIO(one_bytes)) as one:
                    dst.pages.append(one.pages[0])
                pages_redacted += 1
            out_path.parent.mkdir(parents=True, exist_ok=True)
            dst.save(out_path)

    meta_stripped = False
    if strip_meta:
        strip_metadata(out_path, out_path=out_path)
        meta_stripped = True

    if remove_from_store and isinstance(store, AnnotationStore) and by_page:
        keep = [a for a in store.annotations if a.type != AnnotationType.REDACTION]
        if len(keep) != len(store.annotations):
            with store.atomic():
                store.annotations = keep
                store.dirty = True
            store.save(force=True)

    return TrueRedactionResult(
        out_path=out_path,
        pages_redacted=pages_redacted,
        rect_count=rect_count,
        metadata_stripped=meta_stripped,
    )


def redaction_rects_cover_text(
    pdf_path: str | Path,
    page_index: int,
    secret: str,
    *,
    password: str | None = None,
) -> bool:
    """Hilfstest: ob ``secret`` noch im Seiten-Volltext vorkommt (False = entfernt)."""
    from .overlay import extract_page_plain_text

    blob = extract_page_plain_text(pdf_path, page_index, password=password) or ""
    return (secret or "") not in blob
