"""Bilder und Video-Endungen. Schwere Pakete werden nicht nachinstalliert."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QImage


RASTER_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif", ".webp"}
HEIC_EXT = {".heic", ".heif"}
RAW_EXT = {".raw", ".cr2", ".nef", ".arw", ".dng"}
VECTOR_EXT = {".svg"}
PAGE_EXT = {".ai", ".eps"}
PDF_EXT = {".pdf"}
IMAGE_EXT = RASTER_EXT | HEIC_EXT | RAW_EXT | VECTOR_EXT | PAGE_EXT | PDF_EXT
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi"}

HEIC_HINT = "HEIC lässt sich hier nicht lesen. Dafür fehlt das Zusatzpaket pillow-heif."
RAW_HINT = "RAW lässt sich hier nicht lesen. Dafür fehlt ein Zusatzpaket wie rawpy."
SVG_HINT = "SVG lässt sich hier nicht lesen."
PAGE_HINT = "Die erste Seite von AI oder EPS lässt sich hier nicht lesen."
PDF_HINT = ""


def prepare_image(path: str) -> tuple[str | None, str | None, bool]:
    """Liefert (nutzbarer Pfad, Hinweis, Textweg).

    Textweg gilt nur für PDF, wenn keine Bildseite erzeugt werden kann.
    """
    source = Path(path)
    suffix = source.suffix.lower()
    if not source.is_file():
        return None, "Die Bilddatei wurde nicht gefunden.", False
    if suffix in RASTER_EXT:
        return str(source), None, False
    if suffix in HEIC_EXT:
        if not _heif_available():
            return None, HEIC_HINT, False
        raster = _pillow_png(source)
        return (str(raster), None, False) if raster else (None, HEIC_HINT, False)
    if suffix in RAW_EXT:
        raster = _raw_png(source)
        return (str(raster), None, False) if raster else (None, RAW_HINT, False)
    if suffix in VECTOR_EXT:
        raster = _svg_png(source)
        if raster is None:
            raster = _pillow_png(source)
        return (str(raster), None, False) if raster else (None, SVG_HINT, False)
    if suffix in PAGE_EXT:
        raster = _pillow_png(source) or _qimage_png(source)
        return (str(raster), None, False) if raster else (None, PAGE_HINT, False)
    if suffix in PDF_EXT:
        raster = _pdf_png(source)
        if raster is not None:
            return str(raster), None, False
        return None, None, True
    return None, "Dieses Bildformat lässt sich hier nicht lesen.", False


def load_qimage(path: str | None) -> tuple[QImage | None, str | None]:
    if not path:
        return None, "Kein Bildpfad."
    usable, hint, use_text = prepare_image(path)
    if use_text or not usable:
        return None, hint
    image = QImage(usable)
    if image.isNull():
        image = _pillow_qimage(Path(usable))
    if image is None or image.isNull():
        return None, hint or "Das Bild lässt sich nicht anzeigen."
    return image, None


def _heif_available() -> bool:
    try:
        import pillow_heif  # type: ignore

        pillow_heif.register_heif_opener()
        return True
    except Exception:
        return False


def _raw_png(source: Path) -> Path | None:
    try:
        import rawpy  # type: ignore
    except Exception:
        return _pillow_png(source)
    try:
        with rawpy.imread(str(source)) as raw:
            rgb = raw.postprocess()
        from PIL import Image

        image = Image.fromarray(rgb)
        return _save_png(image)
    except Exception:
        return None


def _pillow_png(source: Path) -> Path | None:
    try:
        from PIL import Image

        with Image.open(source) as image:
            try:
                image.seek(0)
            except EOFError:
                return None
            frame = image.convert("RGBA")
            return _save_png(frame)
    except Exception:
        return None


def _pillow_qimage(source: Path) -> QImage | None:
    rendered = _pillow_png(source)
    if rendered is None:
        return None
    image = QImage(str(rendered))
    return None if image.isNull() else image


def _qimage_png(source: Path) -> Path | None:
    image = QImage(str(source))
    if image.isNull():
        return None
    return _save_qimage(image)


def _svg_png(source: Path) -> Path | None:
    try:
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainter
        from PySide6.QtSvg import QSvgRenderer
    except Exception:
        return None
    try:
        renderer = QSvgRenderer(str(source))
        if not renderer.isValid():
            return None
        size = renderer.defaultSize()
        if size.width() < 2 or size.height() < 2:
            size = QSize(800, 600)
        image = QImage(size, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(0)
        painter = QPainter(image)
        renderer.render(painter, QRectF(0, 0, size.width(), size.height()))
        painter.end()
        if image.isNull():
            return None
        return _save_qimage(image)
    except Exception:
        return None


def _pdf_png(source: Path) -> Path | None:
    try:
        from PySide6.QtPdf import QPdfDocument
    except Exception:
        return None
    try:
        document = QPdfDocument()
        document.load(str(source))
        if document.pageCount() < 1:
            document.close()
            return None
        point = document.pagePointSize(0)
        width = max(1, int(point.width() * 2))
        height = max(1, int(point.height() * 2))
        image = document.render(0, QSize(width, height))
        document.close()
        if image is None or image.isNull():
            return None
        return _save_qimage(image)
    except Exception:
        return None


def _save_png(image) -> Path:
    folder = Path(tempfile.mkdtemp(prefix="officedisplay-bild-"))
    target = folder / "seite.png"
    image.save(target, format="PNG")
    return target


def _save_qimage(image: QImage) -> Path | None:
    folder = Path(tempfile.mkdtemp(prefix="officedisplay-bild-"))
    target = folder / "seite.png"
    if not image.save(str(target), "PNG"):
        return None
    return target
