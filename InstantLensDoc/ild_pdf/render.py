"""PDF-Seiten als Bilder rendern (pypdfium2) mit Zoom-Cache."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, Union

from PIL import Image
import pypdfium2 as pdfium

from .document import PdfDocument
from .limits import clamp_render_scale

# LRU: (path_str, mtime_ns, page, scale_key, grayscale, invert) → PIL Image
_CACHE: "OrderedDict[Tuple[str, int, int, float, bool, bool], Image.Image]" = OrderedDict()
_CACHE_MAX = 24


def clear_render_cache(path: str | Path | None = None) -> None:
    """Gesamten Cache oder Einträge zu einem Pfad leeren."""
    if path is None:
        _CACHE.clear()
        return
    key_prefix = str(Path(path).resolve()) if Path(path).exists() else str(path)
    dead = [k for k in _CACHE if k[0] == key_prefix or k[0] == str(path)]
    for k in dead:
        _CACHE.pop(k, None)


def _mtime_ns(path: Path) -> int:
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return 0


def _cache_get(key: Tuple[str, int, int, float, bool, bool]) -> Optional[Image.Image]:
    img = _CACHE.get(key)
    if img is None:
        return None
    _CACHE.move_to_end(key)
    return img.copy()


def _cache_put(key: Tuple[str, int, int, float, bool, bool], img: Image.Image) -> None:
    _CACHE[key] = img.copy()
    _CACHE.move_to_end(key)
    while len(_CACHE) > _CACHE_MAX:
        _CACHE.popitem(last=False)


def _to_grayscale(img: Image.Image) -> Image.Image:
    """Farbe → Graustufen (RGBA beibehalten wenn vorhanden)."""
    if img.mode == "RGBA":
        rgb = img.convert("RGB").convert("L").convert("RGB")
        r, g, b, a = img.split()
        gray = rgb.convert("L")
        return Image.merge("RGBA", (gray, gray, gray, a))
    if img.mode == "L":
        return img
    return img.convert("L").convert("RGB")


def invert_for_display(img: Image.Image) -> Image.Image:
    """
    Dunkle Invert-Ansicht (Nachtmodus) — nur Darstellung, nicht zum Speichern/Export.
    Alpha-Kanal bleibt erhalten.
    """
    from PIL import ImageOps

    if img.mode == "RGBA":
        r, g, b, a = img.split()
        rgb = Image.merge("RGB", (r, g, b))
        inv = ImageOps.invert(rgb)
        ir, ig, ib = inv.split()
        return Image.merge("RGBA", (ir, ig, ib, a))
    if img.mode == "L":
        return ImageOps.invert(img)
    return ImageOps.invert(img.convert("RGB"))


def render_page(
    source: Union[str, Path, PdfDocument, pdfium.PdfDocument],
    page_index: int = 0,
    scale: float = 2.0,
    *,
    use_cache: bool = True,
    password: Optional[str] = None,
    grayscale: bool = False,
    invert: bool = False,
) -> Image.Image:
    """
    Eine Seite als PIL-Image rendern (optional LRU-Cache, Graustufen, Invert).

    ``invert`` ist für die Nachtmodus-Ansicht gedacht und sollte bei
    Speichern/Export nicht gesetzt werden.
    """
    own = False
    path_for_cache: Optional[Path] = None
    if isinstance(source, (str, Path)):
        path_for_cache = Path(source)
        pw = password
        doc = pdfium.PdfDocument(str(source), password=pw)
        own = True
    elif isinstance(source, PdfDocument):
        doc = source.raw
        path_for_cache = source.path
    else:
        doc = source

    try:
        page = doc[page_index]
        try:
            pw, ph = page.get_size()
            eff_scale, _ = clamp_render_scale(float(pw), float(ph), scale)
            scale_key = round(eff_scale, 3)
            gray = bool(grayscale)
            inv = bool(invert)
            cache_key: Optional[Tuple[str, int, int, float, bool, bool]] = None
            if use_cache and path_for_cache is not None:
                try:
                    resolved = str(path_for_cache.resolve())
                except OSError:
                    resolved = str(path_for_cache)
                cache_key = (
                    resolved,
                    _mtime_ns(path_for_cache),
                    page_index,
                    scale_key,
                    gray,
                    inv,
                )
                hit = _cache_get(cache_key)
                if hit is not None:
                    return hit
            bitmap = page.render(scale=eff_scale)
            img = bitmap.to_pil()
            if gray:
                img = _to_grayscale(img)
            if inv:
                img = invert_for_display(img)
            if cache_key is not None:
                _cache_put(cache_key, img)
            return img
        finally:
            page.close()
    finally:
        if own:
            doc.close()


def render_pages(
    source: Union[str, Path, PdfDocument],
    indices: Iterable[int] | None = None,
    scale: float = 2.0,
    *,
    password: Optional[str] = None,
    grayscale: bool = False,
    invert: bool = False,
) -> List[Image.Image]:
    """Mehrere Seiten rendern. Ohne indices: alle Seiten."""
    own = False
    if isinstance(source, (str, Path)):
        doc = PdfDocument(source, password=password)
        own = True
    elif isinstance(source, PdfDocument):
        doc = source
    else:
        raise TypeError("source muss Pfad oder PdfDocument sein")

    try:
        pages = list(indices) if indices is not None else list(range(len(doc)))
        return [
            render_page(doc, i, scale=scale, grayscale=grayscale, invert=invert)
            for i in pages
        ]
    finally:
        if own:
            doc.close()


def convert_from_path(
    path: str | Path,
    dpi: int = 150,
    *,
    password: Optional[str] = None,
    grayscale: bool = False,
    invert: bool = False,
) -> List[Image.Image]:
    """pdf2image-ähnliche API für Drop-in-Ersatz."""
    scale = dpi / 72.0
    return render_pages(
        path, scale=scale, password=password, grayscale=grayscale, invert=invert
    )
