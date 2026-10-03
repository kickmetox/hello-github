"""Wasserzeichen und Seitennummer-Stempel in PDF (pikepdf Content-Stream) — 1.6.0."""

from __future__ import annotations

import io
import math
from pathlib import Path
from typing import Iterable, Literal, Optional, Sequence, Union

from PIL import Image, ImageDraw, ImageFont

Placement = Literal["diagonal", "center"]


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


def _ensure_xobject(page, name: str, xobj) -> None:
    from pikepdf import Dictionary, Name

    if Name.Resources not in page:
        page[Name.Resources] = Dictionary()
    res = page[Name.Resources]
    if Name.XObject not in res:
        res[Name.XObject] = Dictionary()
    res[Name.XObject][Name(f"/{name}")] = xobj


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


def _placement_angle(placement: Placement | str, angle_deg: float) -> float:
    mode = (placement or "diagonal").strip().lower()
    if mode in ("center", "centred", "zentriert", "mitte"):
        return 0.0
    return float(angle_deg)


def _make_image_xobject(pdf, img: Image.Image):
    """JPEG Image-XObject in pikepdf anlegen."""
    from pikepdf import Dictionary, Name, Stream

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    data = buf.getvalue()
    w, h = img.size
    cs = Name.DeviceGray if img.mode == "L" else Name.DeviceRGB
    stream = Stream(pdf, data)
    stream.stream_dict = Dictionary(
        Type=Name.XObject,
        Subtype=Name.Image,
        Width=int(w),
        Height=int(h),
        ColorSpace=cs,
        BitsPerComponent=8,
        Filter=Name.DCTDecode,
    )
    return stream, w, h


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
    placement: Placement | str = "diagonal",
) -> Path:
    """
    Schreibt ein Text-Wasserzeichen auf ausgewählte Seiten.
    placement: ``diagonal`` (Winkel) oder ``center`` (horizontal zentriert).
    Koordinaten: Seitenmitte; Bake in ``out_path`` (Default: neues ``*_wm.pdf``).
    """
    import pikepdf

    pdf_path = Path(pdf_path)
    if out_path is None:
        out_path = pdf_path.with_name(f"{pdf_path.stem}_wm{pdf_path.suffix}")
    else:
        out_path = Path(out_path)
    text = (text or "").strip()
    if not text:
        raise ValueError("Wasserzeichen-Text leer")

    angle = _placement_angle(placement, angle_deg)
    with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
        indices = _page_indices(len(pdf.pages), pages)
        rad = math.radians(angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        for i in indices:
            page = pdf.pages[i]
            mediabox = page.mediabox
            page_w = float(mediabox[2] - mediabox[0])
            page_h = float(mediabox[3] - mediabox[1])
            cx, cy = page_w / 2.0, page_h / 2.0
            approx_w = len(text) * font_size * 0.5
            tx = -approx_w / 2.0
            ty = -font_size / 3.0
            _ensure_helvetica(page)
            _ensure_extgstate(page, "ILDwm", opacity)
            g = max(0.0, min(1.0, float(color_gray)))
            parts = [
                "q",
                "/ILDwm gs",
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


def apply_image_watermark(
    pdf_path: str | Path,
    image: Union[str, Path, Image.Image],
    *,
    out_path: str | Path | None = None,
    pages: Optional[Sequence[int]] = None,
    opacity: float = 0.25,
    angle_deg: float = 45.0,
    scale: float = 0.45,
    placement: Placement | str = "diagonal",
) -> Path:
    """
    Bild-Wasserzeichen diagonal oder zentriert auf den Seitenbereich bakken.
    scale: Anteil der kürzeren Seitenkante (0.1–1.0). Default-Out: ``*_wm.pdf``.
    """
    import pikepdf

    pdf_path = Path(pdf_path)
    if out_path is None:
        out_path = pdf_path.with_name(f"{pdf_path.stem}_wm{pdf_path.suffix}")
    else:
        out_path = Path(out_path)

    if isinstance(image, Image.Image):
        src_img = image.convert("RGB")
    else:
        src_img = Image.open(image).convert("RGB")
    src_img.load()

    scale = max(0.1, min(1.0, float(scale)))
    angle = _placement_angle(placement, angle_deg)

    with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
        indices = _page_indices(len(pdf.pages), pages)
        rad = math.radians(angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        for i in indices:
            page = pdf.pages[i]
            mediabox = page.mediabox
            page_w = float(mediabox[2] - mediabox[0])
            page_h = float(mediabox[3] - mediabox[1])
            cx, cy = page_w / 2.0, page_h / 2.0
            target = min(page_w, page_h) * scale
            iw0, ih0 = src_img.size
            ratio = target / float(max(iw0, ih0))
            draw_w = max(8.0, iw0 * ratio)
            draw_h = max(8.0, ih0 * ratio)
            xobj, _, _ = _make_image_xobject(pdf, src_img)
            name = f"ILDwmi{i}"
            _ensure_xobject(page, name, xobj)
            _ensure_extgstate(page, "ILDwm", opacity)
            # cm: rotate around center, then scale image box centered at origin
            parts = [
                "q",
                "/ILDwm gs",
                f"{cos_a:.4f} {sin_a:.4f} {-sin_a:.4f} {cos_a:.4f} {cx:.2f} {cy:.2f} cm",
                f"{draw_w:.2f} 0 0 {draw_h:.2f} {-draw_w/2:.2f} {-draw_h/2:.2f} cm",
                f"/{name} Do",
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


def render_watermark_preview(
    pdf_path: str | Path,
    *,
    page_index: int = 0,
    mode: str = "text",
    text: str = "VERTRAULICH",
    image: Union[str, Path, Image.Image, None] = None,
    opacity: float = 0.25,
    angle_deg: float = 45.0,
    font_size: float = 48.0,
    scale: float = 0.45,
    placement: Placement | str = "diagonal",
    render_scale: float = 1.0,
) -> Image.Image:
    """
    Raster-Vorschau einer Seite mit überlagertem Wasserzeichen (nicht bake).
    """
    from .render import render_page

    base = render_page(pdf_path, int(page_index), scale=render_scale, use_cache=True)
    if base.mode != "RGBA":
        canvas = base.convert("RGBA")
    else:
        canvas = base.copy()
    w, h = canvas.size
    angle = _placement_angle(placement, angle_deg)
    op = max(0.05, min(1.0, float(opacity)))
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    if (mode or "text").strip().lower() == "image" and image is not None:
        if isinstance(image, Image.Image):
            stamp = image.convert("RGBA")
        else:
            stamp = Image.open(image).convert("RGBA")
        target = min(w, h) * max(0.1, min(1.0, float(scale)))
        iw, ih = stamp.size
        ratio = target / float(max(iw, ih))
        nw, nh = max(8, int(iw * ratio)), max(8, int(ih * ratio))
        stamp = stamp.resize((nw, nh), Image.Resampling.LANCZOS)
        if op < 0.999:
            r, g, b, a = stamp.split()
            a = a.point(lambda v: int(v * op))
            stamp = Image.merge("RGBA", (r, g, b, a))
        if abs(angle) > 0.01:
            stamp = stamp.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
        sw, sh = stamp.size
        ox, oy = (w - sw) // 2, (h - sh) // 2
        overlay.paste(stamp, (ox, oy), stamp)
    else:
        draw = ImageDraw.Draw(overlay)
        label = (text or "VERTRAULICH").strip() or "VERTRAULICH"
        # Schriftgröße grob an Render-Scale anpassen
        px = max(10, int(float(font_size) * float(render_scale)))
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", px)
        except Exception:
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None
        # Text auf temporärem Bild drehen
        tw = max(8, int(len(label) * px * 0.6))
        th = max(8, int(px * 1.6))
        tmp = Image.new("RGBA", (tw + 40, th + 40), (0, 0, 0, 0))
        td = ImageDraw.Draw(tmp)
        fill = (90, 90, 90, int(255 * op))
        td.text((20, 20), label, fill=fill, font=font)
        if abs(angle) > 0.01:
            tmp = tmp.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
        sw, sh = tmp.size
        ox, oy = (w - sw) // 2, (h - sh) // 2
        overlay.paste(tmp, (ox, oy), tmp)

    return Image.alpha_composite(canvas, overlay).convert("RGB")
