"""Bild in PDF einfügen / aus Seite extrahieren (Hooks über pikepdf + Pillow)."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Callable, List, Optional, Union

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


class CompressCancelled(Exception):
    """Abbruch durch Benutzer während PDF-Kompression / Downsample — 2.3.1."""


def format_byte_size(num: int | float) -> str:
    """Menschenlesbare Dateigröße (B/KB/MB) — 2.3.1."""
    n = max(0.0, float(num or 0))
    if n < 1024:
        return f"{int(n)} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.2f} MB"


# DPI-/Qualitäts-Presets für Kompressionsdialog — 2.3.1
# render_scale ≈ dpi/72; max_edge und jpeg_quality passend zur Zielqualität
COMPRESS_PRESETS: dict[str, dict] = {
    "screen": {
        "label": "Bildschirm (72 DPI, Q50)",
        "jpeg_quality": 50,
        "max_edge": 1000,
        "render_scale": 1.0,
        "downsample": True,
        "dpi": 72,
    },
    "ebook": {
        "label": "E-Book (150 DPI, Q70)",
        "jpeg_quality": 70,
        "max_edge": 1600,
        "render_scale": 150 / 72.0,
        "downsample": True,
        "dpi": 150,
    },
    "print": {
        "label": "Druck (300 DPI, Q85)",
        "jpeg_quality": 85,
        "max_edge": 3000,
        "render_scale": 300 / 72.0,
        "downsample": True,
        "dpi": 300,
    },
    "custom": {
        "label": "Benutzerdefiniert",
        "jpeg_quality": 70,
        "max_edge": 2000,
        "render_scale": 1.5,
        "downsample": True,
        "dpi": None,
    },
}


def compress_pdf_as_images(
    pdf_path: str | Path,
    *,
    out_path: str | Path | None = None,
    jpeg_quality: int = 70,
    render_scale: float = 1.5,
    max_edge: int = 2000,
    downsample: bool = True,
    on_progress: Optional[Callable[[int, int], bool]] = None,
) -> Path:
    """
    Rendert jede Seite (pypdfium2), optional Downsample (max_edge), JPEG-Kompression
    und ersetzt Seiten via pikepdf in einem **neuen** PDF (verlustbehaftet).

    ``downsample=False`` behält die gerasterte Auflösung (nur JPEG-Q).
    ``on_progress``: optional ``(current_1based, total) -> bool``; False = Abbruch
    ohne Zieldatei (``CompressCancelled``) — 2.3.1.
    """
    from .render import render_page
    from .document import PdfDocument

    pdf_path = Path(pdf_path)
    out_path = Path(out_path) if out_path else pdf_path.with_name(f"{pdf_path.stem}_compressed.pdf")
    pages: list[Image.Image] = []
    with PdfDocument(pdf_path) as doc:
        n = len(doc)
        sizes = [doc.page_size(i) for i in range(n)]
    edge = max(64, int(max_edge)) if downsample else 50_000
    for i in range(n):
        if on_progress is not None:
            try:
                cont = on_progress(i + 1, n)
            except Exception:
                cont = True
            if cont is False:
                raise CompressCancelled("Kompression abgebrochen")
        raw = render_page(pdf_path, i, scale=render_scale, use_cache=False)
        pages.append(
            compress_image_for_pdf(raw, max_edge=edge, quality=jpeg_quality, to_jpeg=True)
        )

    # Einzelseiten zusammenführen (pikepdf replace)
    import pikepdf

    with pikepdf.Pdf.new() as dst:
        for idx, (img, (pw, ph)) in enumerate(zip(pages, sizes)):
            if on_progress is not None:
                try:
                    # Schreibphase: Fortschritt bleibt bei total (nach Render)
                    cont = on_progress(n, n)
                except Exception:
                    cont = True
                if cont is False:
                    raise CompressCancelled("Kompression abgebrochen")
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


def downsample_pdf_images(
    pdf_path: str | Path,
    *,
    out_path: str | Path | None = None,
    jpeg_quality: int = 70,
    max_edge: int = 1200,
    render_scale: float = 1.5,
    on_progress: Optional[Callable[[int, int], bool]] = None,
) -> Path:
    """
    Bilder-Downsample (2.3.0/2.3.1): pypdfium2-Raster → JPEG-Downsample → pikepdf-Replace.
    Ausgabe immer als neues File (Default ``*_optimized.pdf``).
    ``on_progress`` / Abbruch wie ``compress_pdf_as_images`` — 2.3.1.
    """
    pdf_path = Path(pdf_path)
    out_path = Path(out_path) if out_path else pdf_path.with_name(f"{pdf_path.stem}_optimized.pdf")
    return compress_pdf_as_images(
        pdf_path,
        out_path=out_path,
        jpeg_quality=jpeg_quality,
        max_edge=max_edge,
        render_scale=render_scale,
        downsample=True,
        on_progress=on_progress,
    )


DEFAULT_PAGE_IMAGE_FILENAME_TEMPLATE = "{stem}_p{page}"


def format_page_image_filename(
    stem: str,
    page: int,
    *,
    template: str | None = None,
    ext: str = ".png",
) -> str:
    """
    Dateiname aus Template bauen — Default ``{stem}_p{page}`` — 1.5.1.
    Platzhalter: ``{stem}``, ``{page}`` (1-basiert).
    """
    tpl = (template or DEFAULT_PAGE_IMAGE_FILENAME_TEMPLATE).strip() or DEFAULT_PAGE_IMAGE_FILENAME_TEMPLATE
    safe_stem = str(stem or "document").strip() or "document"
    # unsichere Pfadzeichen
    safe_stem = "".join(c if c.isalnum() or c in "-_." else "_" for c in safe_stem)[:120]
    name = tpl.replace("{stem}", safe_stem).replace("{page}", str(int(page)))
    name = name.replace("/", "_").replace("\\", "_")
    while "__" in name:
        name = name.replace("__", "_")
    ext = ext if ext.startswith(".") else f".{ext}"
    if not name.lower().endswith((".png", ".jpg", ".jpeg")):
        name = name + ext
    return name


def extract_page_image(
    pdf_path: str | Path,
    page_index: int = 0,
    out_path: str | Path | None = None,
    scale: float = 2.0,
    format: str = "PNG",
    *,
    dpi: int | None = None,
    jpeg_quality: int = 90,
    password: str | None = None,
    grayscale: bool = False,
    filename_template: str | None = None,
) -> Path:
    """
    Rendert eine PDF-Seite und speichert sie als Bild.
    out_path default: <pdf>_p{N}.png (Template ``{stem}_p{page}`` — 1.5.1).
    dpi: wenn gesetzt (z. B. 72/150/300), überschreibt scale (dpi/72).
    """
    from .render import render_page

    pdf_path = Path(pdf_path)
    render_scale = (max(1, int(dpi)) / 72.0) if dpi is not None else float(scale)
    img = render_page(
        pdf_path,
        page_index=page_index,
        scale=render_scale,
        password=password,
        grayscale=grayscale,
    )
    fmt = format.upper()
    if fmt == "JPG":
        fmt = "JPEG"
    ext = ".jpg" if fmt == "JPEG" else ".png"
    if out_path is None:
        name = format_page_image_filename(
            pdf_path.stem, page_index + 1, template=filename_template, ext=ext
        )
        out_path = pdf_path.with_name(name)
    else:
        out_path = Path(out_path)
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
    dpi: int | None = None,
    jpeg_quality: int = 90,
    password: str | None = None,
    grayscale: bool = False,
    filename_template: str | None = None,
    on_progress: Optional[Callable[[int, int], bool]] = None,
) -> List[Path]:
    """
    Exportiert eine oder mehrere PDF-Seiten als PNG/JPEG in out_dir.
    pages=None → alle Seiten. Rückgabe: Liste geschriebener Pfade.
    dpi: wenn gesetzt, überschreibt scale (siehe extract_page_image).
    filename_template: Default ``{stem}_p{page}`` — 1.5.1.
    on_progress: optional ``(current_1based, total) -> bool``; False = Abbruch.
    Abbruch behält bereits geschriebene Dateien (keine Rollback-Löschung) — 1.5.2.
    """
    from .document import PdfDocument

    pdf_path = Path(pdf_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fmt = format.upper()
    if fmt == "JPG":
        fmt = "JPEG"
    ext = ".jpg" if fmt == "JPEG" else ".png"
    tpl = filename_template or DEFAULT_PAGE_IMAGE_FILENAME_TEMPLATE
    with PdfDocument(pdf_path, password=password) as doc:
        n = len(doc)
    indices = list(pages) if pages is not None else list(range(n))
    indices = [i for i in indices if 0 <= i < n]
    written: List[Path] = []
    total = len(indices)
    for idx, i in enumerate(indices):
        if on_progress is not None:
            try:
                cont = on_progress(idx + 1, total)
            except Exception:
                cont = True
            if cont is False:
                # Bereits geschriebene Dateien behalten — 1.5.2
                break
        name = format_page_image_filename(
            pdf_path.stem, i + 1, template=tpl, ext=ext
        )
        out = out_dir / name
        written.append(
            extract_page_image(
                pdf_path,
                i,
                out,
                scale=scale,
                format=fmt,
                dpi=dpi,
                jpeg_quality=jpeg_quality,
                password=password,
                grayscale=grayscale,
                filename_template=tpl,
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
    opacity: float = 1.0,
    flatten: bool = False,
    flatten_path: str | Path | None = None,
    flatten_scale: float = 2.0,
    password: str | None = None,
) -> Path | tuple[Path, Path]:
    """
    Signatur-Platzhalter: Bildstempel als Sidecar-Annotation (img:…).
    Optional Flatten/Bake der betroffenen Seite in ein neues PDF — 1.5.0.
    Größe via width/height; Deckkraft via opacity (0.05–1.0) — 1.5.1.
    Rückgabe: Bildpfad, oder (Bildpfad, Flatten-PDF) wenn flatten=True.
    """
    from .annotate import Annotation, AnnotationStore, AnnotationType

    pdf_path = Path(pdf_path)
    try:
        op = float(opacity)
    except (TypeError, ValueError):
        op = 1.0
    op = max(0.05, min(1.0, op))
    width = max(20.0, float(width))
    height = max(12.0, float(height))
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
            opacity=op,
        )
    )
    store.save(force=True)
    if not flatten:
        return img_path
    from .flatten import flatten_annotations_to_pdf

    out = (
        Path(flatten_path)
        if flatten_path
        else pdf_path.with_name(f"{pdf_path.stem}_sig_p{page_index + 1}_flattened.pdf")
    )
    flat = flatten_annotations_to_pdf(
        pdf_path,
        store,
        scale=max(0.5, float(flatten_scale)),
        out_path=out,
        password=password,
        page_indices=[int(page_index)],
    )
    return img_path, Path(flat)


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
