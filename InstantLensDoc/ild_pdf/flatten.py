"""Annotationen flatten/bake: Sidecar visuell in alle Seiten einbrennen (Export-PDF)."""

from __future__ import annotations

import io
import math
from pathlib import Path
from typing import List, Sequence

from PIL import Image, ImageDraw, ImageFont

from .annotate import Annotation, AnnotationStore, AnnotationType
from .document import PdfDocument
from .render import render_page


def _parse_color(color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    c = (color or "#FFFF00").strip()
    if not c.startswith("#"):
        c = "#" + c
    c = c.lstrip("#")
    try:
        if len(c) == 3:
            r, g, b = (int(c[i] * 2, 16) for i in range(3))
        elif len(c) >= 6:
            r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        else:
            r, g, b = 255, 255, 0
    except ValueError:
        r, g, b = 255, 255, 0
    return r, g, b, max(0, min(255, int(alpha)))


def _opacity_alpha(ann: Annotation, base: int) -> int:
    try:
        op = float(getattr(ann, "opacity", 1.0) or 1.0)
    except (TypeError, ValueError):
        op = 1.0
    op = max(0.05, min(1.0, op))
    return max(0, min(255, int(round(base * op))))


def _font(size: float):
    size_i = max(8, int(round(size)))
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size_i)
    except OSError:
        try:
            return ImageFont.load_default()
        except Exception:
            return None


def draw_annotations_on_image(
    img: Image.Image,
    annotations: Sequence[Annotation],
    *,
    scale: float = 1.5,
) -> Image.Image:
    """Zeichnet Annotationen auf eine Seiten-Rendition (Koordinaten = Render-Pixel bei scale)."""
    base = img.convert("RGBA") if img.mode != "RGBA" else img.copy()
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    scale = max(float(scale), 0.01)

    for ann in annotations:
        x, y = float(ann.x), float(ann.y)
        w, h = float(ann.width), float(ann.height)
        fill_a = _opacity_alpha(ann, 90 if ann.type == AnnotationType.HIGHLIGHT else 200)
        stroke = _parse_color(ann.color, _opacity_alpha(ann, 255))

        if ann.type == AnnotationType.HIGHLIGHT:
            draw.rectangle([x, y, x + w, y + h], fill=_parse_color(ann.color, fill_a))
        elif ann.type == AnnotationType.REDACTION:
            rw, rh = max(w, 4), max(h, 4)
            draw.rectangle([x, y, x + rw, y + rh], fill=(0, 0, 0, _opacity_alpha(ann, 230)))
            draw.rectangle([x, y, x + rw, y + rh], outline=(220, 50, 50, 255), width=2)
        elif ann.type == AnnotationType.UNDERLINE:
            draw.line([x, y + h, x + w, y + h], fill=stroke, width=2)
        elif ann.type == AnnotationType.STICKY:
            bw, bh = max(w, 80), max(h, 60)
            draw.rectangle([x, y, x + bw, y + bh], fill=(255, 255, 150, _opacity_alpha(ann, 200)))
            draw.rectangle([x, y, x + bw, y + bh], outline=stroke, width=1)
            font = _font(12)
            draw.text((x + 4, y + 4), (ann.text or "Notiz")[:40], fill=(40, 40, 20, 255), font=font)
        elif ann.type in (AnnotationType.TEXT, AnnotationType.TEXT_OVERLAY):
            bw, bh = max(w, 40), max(h, 18)
            if ann.type == AnnotationType.TEXT_OVERLAY:
                draw.rectangle(
                    [x, y, x + bw, y + bh],
                    fill=(255, 255, 255, _opacity_alpha(ann, 160)),
                )
            draw.rectangle([x, y, x + bw, y + bh], outline=stroke, width=1)
            font = _font(max(ann.font_size, 12))
            draw.text((x + 2, y + 2), (ann.text or "")[:80], fill=stroke, font=font)
        elif ann.type in (AnnotationType.STAMP, AnnotationType.SIGNATURE):
            try:
                rot = float(getattr(ann, "rotation", 0.0) or 0.0)
            except (TypeError, ValueError):
                rot = 0.0
            rot = float(int(round(rot / 90.0)) % 4 * 90)
            if (ann.text or "").startswith("img:"):
                img_path = Path(ann.text[4:])
                if img_path.is_file():
                    try:
                        stamp = Image.open(img_path).convert("RGBA")
                        tw, th = max(int(w), 40), max(int(h), 24)
                        stamp = stamp.resize((tw, th), Image.Resampling.LANCZOS)
                        if rot:
                            stamp = stamp.rotate(-rot, expand=True, resample=Image.Resampling.BICUBIC)
                            tw, th = stamp.size
                            cx = int(x + max(w, 40) / 2)
                            cy = int(y + max(h, 24) / 2)
                            overlay.paste(stamp, (cx - tw // 2, cy - th // 2), stamp)
                        else:
                            overlay.paste(stamp, (int(x), int(y)), stamp)
                        continue
                    except Exception:
                        pass
            box_h = max(h, 48 if "\n" in (ann.text or "") else 36)
            bw = max(w, 120)
            if rot:
                cx = int(x + bw / 2)
                cy = int(y + box_h / 2)
                pad = int(max(bw, box_h) * 1.5) + 8
                tile = Image.new("RGBA", (pad * 2, pad * 2), (0, 0, 0, 0))
                td = ImageDraw.Draw(tile)
                ox, oy = pad - int(bw / 2), pad - int(box_h / 2)
                td.rectangle([ox, oy, ox + bw, oy + box_h], outline=stroke, width=3)
                font = _font(14)
                ty = oy + 6
                for line in (ann.text or "STEMPEL").splitlines()[:3]:
                    td.text((ox + 8, ty), line[:28], fill=stroke, font=font)
                    ty += 16
                tile = tile.rotate(-rot, expand=True, resample=Image.Resampling.BICUBIC)
                tw, th = tile.size
                overlay.paste(tile, (cx - tw // 2, cy - th // 2), tile)
                continue
            draw.rectangle([x, y, x + bw, y + box_h], outline=stroke, width=3)
            font = _font(14)
            ty = y + 6
            for line in (ann.text or "STEMPEL").splitlines()[:3]:
                draw.text((x + 8, ty), line[:28], fill=stroke, font=font)
                ty += 16
        elif ann.type == AnnotationType.SIGNATURE_FIELD:
            fh, fw = max(int(h), 48), max(int(w), 160)
            draw.rectangle([x, y, x + fw, y + fh], outline=stroke, width=2)
            draw.line([x + 8, y + fh - 10, x + fw - 8, y + fh - 10], fill=stroke, width=1)
            font = _font(12)
            draw.text((x + 8, y + 6), (ann.text or "Unterschrift")[:40], fill=stroke, font=font)
        elif ann.type == AnnotationType.CALLOUT:
            box_w, box_h = max(w, 100), max(h, 40)
            draw.rectangle(
                [x, y, x + box_w, y + box_h],
                fill=(255, 255, 220, _opacity_alpha(ann, 220)),
                outline=stroke,
                width=1,
            )
            font = _font(12)
            draw.text((x + 4, y + 4), (ann.text or "Callout")[:40], fill=(40, 40, 20, 255), font=font)
            cx = float(ann.callout_x) if ann.callout_x else x - 40
            cy = float(ann.callout_y) if ann.callout_y else y + box_h + 30
            draw.line([x, y + box_h, cx, cy], fill=stroke, width=2)
            draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=stroke)
        elif ann.type == AnnotationType.RECTANGLE:
            draw.rectangle(
                [x, y, x + w, y + h],
                fill=_parse_color(ann.color, _opacity_alpha(ann, 40)),
                outline=stroke,
                width=2,
            )
        elif ann.type in (AnnotationType.LINE, AnnotationType.ARROW, AnnotationType.MEASURE):
            x2, y2 = ann.end_point()
            draw.line([ann.x, ann.y, x2, y2], fill=stroke, width=2)
            if ann.type == AnnotationType.ARROW:
                angle = math.atan2(y2 - ann.y, x2 - ann.x)
                size = 12.0
                p2 = (x2 - size * math.cos(angle - 0.4), y2 - size * math.sin(angle - 0.4))
                p3 = (x2 - size * math.cos(angle + 0.4), y2 - size * math.sin(angle + 0.4))
                draw.polygon([(x2, y2), p2, p3], fill=stroke)
            if ann.type == AnnotationType.MEASURE:
                mid_x = (ann.x + x2) / 2
                mid_y = (ann.y + y2) / 2
                label = ann.text or ann.measure_label(scale)
                font = _font(11)
                draw.text((mid_x + 4, mid_y - 14), label, fill=stroke, font=font)

    return Image.alpha_composite(base, overlay).convert("RGB")


def flatten_annotations_to_pdf(
    pdf_path: str | Path,
    store: AnnotationStore | Sequence[Annotation],
    *,
    scale: float = 2.0,
    out_path: str | Path | None = None,
    password: str | None = None,
    grayscale: bool = False,
    progress=None,
    should_cancel=None,
) -> Path:
    """
    Alle Seiten rendern, Annotationen einzeichnen (flatten/bake) und als neues PDF speichern.
    Original und Sidecar bleiben unverändert. Koordinaten = Render-Pixel bei `scale`.

    progress(msg, current=i, total=n) — optional.
    should_cancel() → True bricht ab (raises InterruptedError).
    """
    import pikepdf

    pdf_path = Path(pdf_path)
    if out_path is None:
        out_path = pdf_path.with_name(f"{pdf_path.stem}_flattened.pdf")
    else:
        out_path = Path(out_path)

    if isinstance(store, AnnotationStore):
        anns = list(store.annotations)
    else:
        anns = list(store)

    by_page: dict[int, list[Annotation]] = {}
    for a in anns:
        by_page.setdefault(int(a.page), []).append(a)

    scale = max(float(scale), 0.5)
    pages_out: List[Image.Image] = []
    with PdfDocument(pdf_path, password=password) as doc:
        n = len(doc)
        sizes = [doc.page_size(i) for i in range(n)]

    def _prog(msg: str, current: int = 0, total: int = 0) -> None:
        if progress:
            try:
                progress(msg, current, total)
            except TypeError:
                progress(msg)

    def _cancelled() -> bool:
        if should_cancel is None:
            return False
        try:
            return bool(should_cancel())
        except Exception:
            return False

    for i in range(n):
        if _cancelled():
            raise InterruptedError("Flatten abgebrochen")
        _prog(f"Seite {i + 1}/{n} rendern…", i, n)
        raw = render_page(
            pdf_path,
            i,
            scale=scale,
            password=password,
            grayscale=grayscale,
            use_cache=False,
        )
        page_anns = by_page.get(i, [])
        if page_anns:
            raw = draw_annotations_on_image(raw, page_anns, scale=scale)
        elif raw.mode != "RGB":
            raw = raw.convert("RGB")
        pages_out.append(raw)

    if _cancelled():
        raise InterruptedError("Flatten abgebrochen")
    _prog("PDF schreiben…", n, n + 1)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with pikepdf.Pdf.new() as dst:
        for img, (pw, ph) in zip(pages_out, sizes):
            if _cancelled():
                raise InterruptedError("Flatten abgebrochen")
            buf = io.BytesIO()
            # Seitengröße in PDF-Punkten beibehalten
            canvas = Image.new("RGB", (max(1, int(pw)), max(1, int(ph))), "white")
            iw, ih = img.size
            fit = min(pw / max(iw, 1), ph / max(ih, 1))
            nw, nh = max(1, int(iw * fit)), max(1, int(ih * fit))
            resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
            ox = int((pw - nw) / 2)
            oy = int((ph - nh) / 2)
            canvas.paste(resized, (ox, oy))
            canvas.save(buf, "PDF", resolution=72.0)
            buf.seek(0)
            with pikepdf.open(buf) as src:
                dst.pages.append(src.pages[0])
        dst.save(out_path)
    _prog("Fertig", n + 1, n + 1)
    return out_path


# Alias klarer Name
bake_annotations = flatten_annotations_to_pdf
