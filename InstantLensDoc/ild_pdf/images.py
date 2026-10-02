"""Bild in PDF einfügen / aus Seite extrahieren (Hooks über pikepdf + Pillow)."""

from __future__ import annotations

import io
from pathlib import Path
from typing import List, Optional, Union

from PIL import Image


def compress_image_for_pdf(
    image: Union[str, Path, Image.Image],
    *,
    max_edge: int = 2000,
    quality: int = 75,
    to_jpeg: bool = True,
) -> Image.Image:
    """
    Verkleinert/komprimiert ein Bild vor dem Einfügen als PDF-Seite.
    max_edge: längste Kante in Pixel. quality: JPEG 1–95.
    """
    if isinstance(image, (str, Path)):
        img = Image.open(image)
    else:
        img = image.copy() if hasattr(image, "copy") else image
    img.load()
    max_edge = max(64, int(max_edge))
    quality = max(1, min(95, int(quality)))
    w, h = img.size
    longest = max(w, h)
    if longest > max_edge:
        scale = max_edge / float(longest)
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    if to_jpeg:
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        buf.seek(0)
        img = Image.open(buf)
        img.load()
        return img.convert("RGB")
    if img.mode not in ("RGB", "L", "RGBA"):
        img = img.convert("RGB")
    return img


def compress_pdf_as_images(
    pdf_path: str | Path,
    *,
    out_path: str | Path | None = None,
    jpeg_quality: int = 70,
    render_scale: float = 1.5,
    max_edge: int = 2000,
) -> Path:
    """
    Rendert jede Seite, komprimiert als JPEG und baut ein neues PDF
    (verlustbehaftet — gut für Scan-PDFs / Dateigröße).
    """
    from .render import render_page
    from .document import PdfDocument

    pdf_path = Path(pdf_path)
    out_path = Path(out_path) if out_path else pdf_path.with_name(f"{pdf_path.stem}_compressed.pdf")
    pages: list[Image.Image] = []
    with PdfDocument(pdf_path) as doc:
        n = len(doc)
        sizes = [doc.page_size(i) for i in range(n)]
    for i in range(n):
        raw = render_page(pdf_path, i, scale=render_scale, use_cache=False)
        pages.append(
            compress_image_for_pdf(raw, max_edge=max_edge, quality=jpeg_quality, to_jpeg=True)
        )

    # Einzelseiten zusammenführen
    import pikepdf

    with pikepdf.Pdf.new() as dst:
        for img, (pw, ph) in zip(pages, sizes):
            img_pdf = io.BytesIO()
            canvas = Image.new("RGB", (max(1, int(pw)), max(1, int(ph))), "white")
            iw, ih = img.size
            scale = min(pw / iw, ph / ih)
            nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
            resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
            ox = int((pw - nw) / 2)
            oy = int((ph - nh) / 2)
            canvas.paste(resized, (ox, oy))
            canvas.save(img_pdf, "PDF", resolution=72.0)
            img_pdf.seek(0)
            with pikepdf.open(img_pdf) as src:
                dst.pages.append(src.pages[0])
        dst.save(out_path)
    return out_path


def extract_page_image(
    pdf_path: str | Path,
    page_index: int = 0,
    out_path: str | Path | None = None,
    scale: float = 2.0,
    format: str = "PNG",
    *,
    jpeg_quality: int = 90,
    password: str | None = None,
) -> Path:
    """
    Rendert eine PDF-Seite und speichert sie als Bild.
    out_path default: <pdf>_p{N}.png
    """
    from .render import render_page

    pdf_path = Path(pdf_path)
    img = render_page(pdf_path, page_index=page_index, scale=scale, password=password)
    if out_path is None:
        ext = ".jpg" if format.upper() in ("JPEG", "JPG") else ".png"
        out_path = pdf_path.with_name(f"{pdf_path.stem}_p{page_index + 1}{ext}")
    else:
        out_path = Path(out_path)
    fmt = format.upper()
    if fmt == "JPG":
        fmt = "JPEG"
    if fmt == "JPEG" and img.mode == "RGBA":
        img = img.convert("RGB")
    save_kw: dict = {}
    if fmt == "JPEG":
        save_kw["quality"] = max(1, min(95, int(jpeg_quality)))
        save_kw["optimize"] = True
    img.save(out_path, fmt, **save_kw)
    return out_path


def extract_pages_as_images(
    pdf_path: str | Path,
    out_dir: str | Path,
    *,
    pages: list[int] | None = None,
    scale: float = 2.0,
    format: str = "PNG",
    jpeg_quality: int = 90,
    password: str | None = None,
) -> List[Path]:
    """
    Exportiert eine oder mehrere PDF-Seiten als PNG/JPEG in out_dir.
    pages=None → alle Seiten. Rückgabe: Liste geschriebener Pfade.
    """
    from .document import PdfDocument

    pdf_path = Path(pdf_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fmt = format.upper()
    if fmt == "JPG":
        fmt = "JPEG"
    ext = ".jpg" if fmt == "JPEG" else ".png"
    with PdfDocument(pdf_path, password=password) as doc:
        n = len(doc)
    indices = list(pages) if pages is not None else list(range(n))
    written: List[Path] = []
    for i in indices:
        if i < 0 or i >= n:
            continue
        out = out_dir / f"{pdf_path.stem}_p{i + 1}{ext}"
        written.append(
            extract_page_image(
                pdf_path,
                i,
                out,
                scale=scale,
                format=fmt,
                jpeg_quality=jpeg_quality,
                password=password,
            )
        )
    return written


def extract_embedded_images(
    pdf_path: str | Path,
    out_dir: str | Path | None = None,
    page_index: Optional[int] = None,
) -> List[Path]:
    """
    Extrahiert eingebettete XObject-Bilder via pikepdf (soweit möglich).
    page_index=None → alle Seiten. Liefert Liste geschriebener Dateipfade.
    """
    import pikepdf

    pdf_path = Path(pdf_path)
    out_dir = Path(out_dir) if out_dir else pdf_path.parent / f"{pdf_path.stem}_images"
    out_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []

    with pikepdf.open(pdf_path) as pdf:
        pages = list(enumerate(pdf.pages))
        if page_index is not None:
            pages = [(page_index, pdf.pages[page_index])]
        for pi, page in pages:
            try:
                images = list(page.images.keys()) if hasattr(page, "images") else []
            except Exception:
                images = []
            for n, name in enumerate(images):
                try:
                    raw = page.images[name]
                    pdfimg = pikepdf.PdfImage(raw)
                    out = out_dir / f"p{pi + 1}_{n + 1}_{_safe(str(name))}.png"
                    pdfimg.extract_to(fileprefix=str(out.with_suffix("")))
                    # extract_to schreibt ggf. .ppm/.jpg — normalisieren auf gefundenes File
                    candidates = list(out_dir.glob(f"p{pi + 1}_{n + 1}_{_safe(str(name))}*"))
                    if candidates:
                        written.append(candidates[0])
                except Exception:
                    continue
    return written


def insert_image_as_page(
    pdf_path: str | Path,
    image: Union[str, Path, Image.Image],
    *,
    at_index: Optional[int] = None,
    page_size: tuple[float, float] = (595.0, 842.0),
    compress: bool = True,
    max_edge: int = 2000,
    jpeg_quality: int = 75,
) -> Path:
    """
    Hängt ein Bild als neue PDF-Seite an (oder fügt an at_index ein).
    Erzeugt bei Bedarf das PDF neu. Standard: Bild vorher komprimieren.
    """
    import pikepdf

    pdf_path = Path(pdf_path)
    if compress:
        img = compress_image_for_pdf(
            image, max_edge=max_edge, quality=jpeg_quality, to_jpeg=True
        )
    else:
        if isinstance(image, (str, Path)):
            img = Image.open(image)
        else:
            img = image
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

    # Zwischen-PDF mit einer Bildseite
    img_pdf = io.BytesIO()
    # A4-Bereich: Bild skalieren in Seite
    canvas = Image.new("RGB", (int(page_size[0]), int(page_size[1])), "white")
    iw, ih = img.size
    scale = min(page_size[0] / iw, page_size[1] / ih, 1.0)
    nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
    ox = int((page_size[0] - nw) / 2)
    oy = int((page_size[1] - nh) / 2)
    canvas.paste(resized, (ox, oy))
    canvas.save(img_pdf, "PDF", resolution=72.0)
    img_pdf.seek(0)

    if not pdf_path.exists():
        # Neues Einzelseiten-PDF
        pdf_path.write_bytes(img_pdf.getvalue())
        return pdf_path

    with pikepdf.open(pdf_path, allow_overwriting_input=True) as dst:
        with pikepdf.open(img_pdf) as src:
            if at_index is None:
                dst.pages.append(src.pages[0])
            else:
                dst.pages.insert(at_index, src.pages[0])
        dst.save(pdf_path)
    return pdf_path


def insert_signature_field(
    pdf_path: str | Path,
    page_index: int = 0,
    *,
    x: float = 40.0,
    y: float = 520.0,
    width: float = 220.0,
    height: float = 56.0,
    label: str = "Unterschrift",
) -> None:
    """Signaturfeld-Platzhalter als Sidecar-Annotation."""
    from .annotate import Annotation, AnnotationStore, AnnotationType

    store = AnnotationStore(Path(pdf_path))
    store.add(
        Annotation(
            page=page_index,
            type=AnnotationType.SIGNATURE_FIELD,
            x=x,
            y=y,
            width=width,
            height=height,
            text=label,
            color="#7F8C8D",
        )
    )
    store.save(force=True)


def insert_signature_image(
    pdf_path: str | Path,
    image: Union[str, Path, Image.Image],
    page_index: int = 0,
    *,
    x: float = 40.0,
    y: float = 520.0,
    width: float = 180.0,
    height: float = 64.0,
) -> Path:
    """Einfache Signatur: Bild als Annotation (Sidecar, img:…)."""
    from .annotate import Annotation, AnnotationStore, AnnotationType

    pdf_path = Path(pdf_path)
    if isinstance(image, Image.Image):
        assets = pdf_path.parent / f"{pdf_path.stem}_signatures"
        assets.mkdir(parents=True, exist_ok=True)
        dest = assets / f"sig_{page_index}_{int(x)}_{int(y)}.png"
        image.convert("RGBA").save(dest)
        img_path = dest
    else:
        img_path = Path(image)

    store = AnnotationStore(pdf_path)
    store.add(
        Annotation(
            page=page_index,
            type=AnnotationType.SIGNATURE,
            x=x,
            y=y,
            width=width,
            height=height,
            text=f"img:{img_path}",
            color="#2C3E50",
        )
    )
    store.save(force=True)
    return img_path


def insert_image_stamp_overlay(
    pdf_path: str | Path,
    image: Union[str, Path, Image.Image],
    page_index: int = 0,
    *,
    x: float = 40.0,
    y: float = 40.0,
    width: float = 120.0,
    height: float = 80.0,
) -> Path:
    """
    Einfacher Hook: speichert Bildstempel-Metadaten in Sidecar und optional
    als Annotation vom Typ STAMP (Pfad im text-Feld als file://…).
    Kein vollständiges PDF-Embed (bewusst leichtgewichtig) — Persistenz über AnnotationStore.
    """
    from .annotate import Annotation, AnnotationStore, AnnotationType

    pdf_path = Path(pdf_path)
    if isinstance(image, Image.Image):
        assets = pdf_path.parent / f"{pdf_path.stem}_stamps"
        assets.mkdir(parents=True, exist_ok=True)
        dest = assets / f"stamp_{page_index}_{int(x)}_{int(y)}.png"
        image.convert("RGBA").save(dest)
        img_path = dest
    else:
        img_path = Path(image)

    store = AnnotationStore(pdf_path)
    store.add(
        Annotation(
            page=page_index,
            type=AnnotationType.STAMP,
            x=x,
            y=y,
            width=width,
            height=height,
            text=f"img:{img_path}",
            color="#CCCCCC",
        )
    )
    store.save(force=True)
    return img_path


def _safe(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:40]
