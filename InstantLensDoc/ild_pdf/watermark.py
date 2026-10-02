"""Wasserzeichen und Seitennummer-Stempel in PDF (pikepdf Content-Stream)."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional, Sequence


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _ensure_helvetica(page) -> None:
    from pikepdf import Dictionary, Name

    if Name.Resources not in page:
        page[Name.Resources] = Dictionary()
    res = page[Name.Resources]
    if Name.Font not in res:
        res[Name.Font] = Dictionary()
    fonts = res[Name.Font]
    if Name.Helv not in fonts:
        fonts[Name.Helv] = Dictionary(
            Type=Name.Font,
            Subtype=Name.Type1,
            BaseFont=Name.Helvetica,
        )


def _ensure_extgstate(page, name: str, opacity: float) -> None:
    from pikepdf import Dictionary, Name

    if Name.Resources not in page:
        page[Name.Resources] = Dictionary()
    res = page[Name.Resources]
    if Name.ExtGState not in res:
        res[Name.ExtGState] = Dictionary()
    gs = res[Name.ExtGState]
    key = Name(f"/{name}")
    ca = max(0.05, min(1.0, float(opacity)))
    gs[key] = Dictionary(Type=Name.ExtGState, ca=ca, CA=ca)


def _append_content(page, pdf, content: bytes) -> None:
    from pikepdf import Array, Name, Stream

    new_stream = Stream(pdf, content)
    if Name.Contents in page:
        existing = page[Name.Contents]
        if isinstance(existing, Array):
            existing.append(new_stream)
        else:
            page[Name.Contents] = Array([existing, new_stream])
    else:
        page[Name.Contents] = new_stream


def _page_indices(n: int, pages: Optional[Sequence[int]]) -> list[int]:
    if pages is None:
        return list(range(n))
    out: list[int] = []
    for i in pages:
        if 0 <= int(i) < n:
            out.append(int(i))
    return out


def apply_watermark(
    pdf_path: str | Path,
    text: str,
    *,
    out_path: str | Path | None = None,
    pages: Optional[Sequence[int]] = None,
    opacity: float = 0.25,
    angle_deg: float = 45.0,
    font_size: float = 48.0,
    color_gray: float = 0.55,
) -> Path:
    """
    Schreibt ein diagonales Text-Wasserzeichen auf ausgewählte Seiten.
    Koordinaten: Seitenmitte, Rotation um die Mitte.
    """
    import math

    import pikepdf

    pdf_path = Path(pdf_path)
    out_path = Path(out_path) if out_path else pdf_path
    text = (text or "").strip()
    if not text:
        raise ValueError("Wasserzeichen-Text leer")

    with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
        indices = _page_indices(len(pdf.pages), pages)
        rad = math.radians(angle_deg)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        for i in indices:
            page = pdf.pages[i]
            mediabox = page.mediabox
            page_w = float(mediabox[2] - mediabox[0])
            page_h = float(mediabox[3] - mediabox[1])
            cx, cy = page_w / 2.0, page_h / 2.0
            # Textbreite grob schätzen → zentrieren
            approx_w = len(text) * font_size * 0.5
            tx = -approx_w / 2.0
            ty = -font_size / 3.0
            _ensure_helvetica(page)
            _ensure_extgstate(page, "ILDwm", opacity)
            g = max(0.0, min(1.0, float(color_gray)))
            parts = [
                "q",
                f"/ILDwm gs",
                f"{g:.3f} g",
                f"{cos_a:.4f} {sin_a:.4f} {-sin_a:.4f} {cos_a:.4f} {cx:.2f} {cy:.2f} cm",
                "BT",
                f"/Helv {font_size:.2f} Tf",
                f"1 0 0 1 {tx:.2f} {ty:.2f} Tm",
                f"({_pdf_escape(text)}) Tj",
                "ET",
                "Q",
            ]
            _append_content(page, pdf, "\n".join(parts).encode("latin-1", errors="replace"))
        pdf.save(out_path)
    return out_path


Position = str  # "bottom-center" | "bottom-right" | "bottom-left" | "top-center"


def apply_page_numbers(
    pdf_path: str | Path,
    *,
    out_path: str | Path | None = None,
    pages: Optional[Sequence[int]] = None,
    template: str = "{n} / {total}",
    position: Position = "bottom-center",
    font_size: float = 10.0,
    margin: float = 28.0,
    start_at: int = 1,
) -> Path:
    """
    Stempel: Seitennummer auf jede Seite.
    Platzhalter: {n} = sichtbare Nummer, {total} = Gesamtseitenzahl, {i} = 0-basierter Index.
    """
    import pikepdf

    pdf_path = Path(pdf_path)
    out_path = Path(out_path) if out_path else pdf_path

    with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
        total = len(pdf.pages)
        indices = _page_indices(total, pages)
        for i in indices:
            page = pdf.pages[i]
            mediabox = page.mediabox
            page_w = float(mediabox[2] - mediabox[0])
            page_h = float(mediabox[3] - mediabox[1])
            n = start_at + i
            label = template.format(n=n, total=total, i=i)
            approx_w = len(label) * font_size * 0.5
            if position == "bottom-right":
                x = page_w - margin - approx_w
                y = margin
            elif position == "bottom-left":
                x = margin
                y = margin
            elif position == "top-center":
                x = (page_w - approx_w) / 2.0
                y = page_h - margin - font_size
            else:  # bottom-center
                x = (page_w - approx_w) / 2.0
                y = margin
            _ensure_helvetica(page)
            parts = [
                "q",
                "0 g",
                "BT",
                f"/Helv {font_size:.2f} Tf",
                f"1 0 0 1 {x:.2f} {y:.2f} Tm",
                f"({_pdf_escape(label)}) Tj",
                "ET",
                "Q",
            ]
            _append_content(page, pdf, "\n".join(parts).encode("latin-1", errors="replace"))
        pdf.save(out_path)
    return out_path


def watermark_pages(
    pdf_path: str | Path,
    text: str,
    page_indices: Iterable[int],
    **kwargs,
) -> Path:
    """Alias: Wasserzeichen nur auf page_indices."""
    return apply_watermark(pdf_path, text, pages=list(page_indices), **kwargs)
