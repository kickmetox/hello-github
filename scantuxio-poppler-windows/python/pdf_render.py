"""
ScanTuxio — lizenzfreundliche PDF-Rasterung über pypdfium2 (PDFium).

PDFium / pypdfium2: Apache-2.0 bzw. BSD-ähnlich (kein Poppler/GPL-Bundle nötig).

API (Drop-in-ähnlich zu pdf2image):

    from pdf_render import convert_from_path, ensure_pdf_backend
    ensure_pdf_backend(required=True)
    images = convert_from_path("doc.pdf", dpi=200)

Fallback: Wenn pypdfium2 fehlt und Poppler im PATH liegt, optional über
pdf2image (GPL-Tools separat — nicht mitliefern). Standardpfad = nur pypdfium2.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence, Union


PathLike = Union[str, Path]


@dataclass(frozen=True)
class PdfBackendInfo:
    ok: bool
    name: str
    message: str
    version: Optional[str] = None


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def probe_pdfium() -> PdfBackendInfo:
    if not _has_module("pypdfium2"):
        return PdfBackendInfo(
            ok=False,
            name="none",
            message=(
                "pypdfium2 nicht installiert. Dev: pip install pypdfium2 pillow. "
                "Frozen: PyInstaller mit --collect-all pypdfium2 neu bauen."
            ),
        )
    import pypdfium2 as pdfium  # noqa: WPS433

    ver = getattr(pdfium, "__version__", None) or getattr(pdfium, "PDFIUM_INFO", None)
    return PdfBackendInfo(
        ok=True,
        name="pypdfium2",
        message=f"PDF-Backend OK: pypdfium2 ({ver})",
        version=str(ver) if ver is not None else None,
    )


def ensure_pdf_backend(*, required: bool = False) -> PdfBackendInfo:
    info = probe_pdfium()
    if info.ok:
        return info
    if required:
        raise ModuleNotFoundError(info.message)
    return info


def convert_from_path(
    pdf_path: PathLike,
    *,
    dpi: float = 200,
    first_page: Optional[int] = None,
    last_page: Optional[int] = None,
    fmt: str = "RGB",
) -> list[Any]:
    """
    Rendert PDF-Seiten zu PIL-Images (wie pdf2image.convert_from_path, ohne Poppler).

    first_page/last_page: 1-basiert, inklusiv (pdf2image-Kompatibilität).
    """
    ensure_pdf_backend(required=True)
    import pypdfium2 as pdfium
    from PIL import Image

    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF nicht gefunden: {path}")

    scale = float(dpi) / 72.0
    doc = pdfium.PdfDocument(str(path))
    try:
        n = len(doc)
        start = 0 if first_page is None else max(0, int(first_page) - 1)
        end = n - 1 if last_page is None else min(n - 1, int(last_page) - 1)
        if start > end:
            return []
        images: list[Any] = []
        for i in range(start, end + 1):
            page = doc[i]
            try:
                bitmap = page.render(scale=scale)
                pil = bitmap.to_pil()
                if fmt and pil.mode != fmt:
                    pil = pil.convert(fmt)
                images.append(pil)
            finally:
                page.close()
        return images
    finally:
        doc.close()


def convert_from_bytes(
    data: bytes,
    *,
    dpi: float = 200,
    first_page: Optional[int] = None,
    last_page: Optional[int] = None,
    fmt: str = "RGB",
) -> list[Any]:
    ensure_pdf_backend(required=True)
    import pypdfium2 as pdfium

    scale = float(dpi) / 72.0
    doc = pdfium.PdfDocument(data)
    try:
        n = len(doc)
        start = 0 if first_page is None else max(0, int(first_page) - 1)
        end = n - 1 if last_page is None else min(n - 1, int(last_page) - 1)
        images = []
        for i in range(start, end + 1):
            page = doc[i]
            try:
                pil = page.render(scale=scale).to_pil()
                if fmt and pil.mode != fmt:
                    pil = pil.convert(fmt)
                images.append(pil)
            finally:
                page.close()
        return images
    finally:
        doc.close()


def page_count(pdf_path: PathLike) -> int:
    ensure_pdf_backend(required=True)
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        return len(doc)
    finally:
        doc.close()


def warn_if_poppler_only_stack() -> Optional[str]:
    """Hinweis, falls nur pdf2image/Poppler vorhanden ist (nicht empfohlen)."""
    if probe_pdfium().ok:
        return None
    if _has_module("pdf2image"):
        return (
            "pdf2image gefunden, pypdfium2 fehlt — würde Poppler (GPL) brauchen. "
            "Bitte auf pypdfium2 umstellen; Poppler nicht mit dem Installer liefern."
        )
    return None


def bootstrap_for_entry() -> PdfBackendInfo:
    """Für scantuxio_entry.py: prüfen und stderr-Hinweis."""
    info = ensure_pdf_backend(required=False)
    msg = info.message
    extra = warn_if_poppler_only_stack()
    if extra:
        msg = f"{msg} | {extra}"
    sys.stderr.write(f"[ScanTuxio] {msg}\n")
    return info
