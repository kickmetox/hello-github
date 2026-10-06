"""Annotationen flatten/bake: Sidecar visuell in alle Seiten einbrennen (Export-PDF)."""

from __future__ import annotations

import io
import math
from pathlib import Path
from typing import List, Sequence

from copy import deepcopy

from PIL import Image, ImageDraw, ImageFont

from .annotate import Annotation, AnnotationStore, AnnotationType, scale_annotation
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
        try:
            sw = int(round(float(getattr(ann, "stroke_width", 2.0) or 2.0)))
        except (TypeError, ValueError):
            sw = 2
        sw = max(1, min(12, sw))

        if ann.type == AnnotationType.HIGHLIGHT:
            draw.rectangle([x, y, x + w, y + h], fill=_parse_color(ann.color, fill_a))
        elif ann.type == AnnotationType.REDACTION:
            rw, rh = max(w, 4), max(h, 4)
            draw.rectangle([x, y, x + rw, y + rh], fill=(0, 0, 0, _opacity_alpha(ann, 230)))
            draw.rectangle([x, y, x + rw, y + rh], outline=(220, 50, 50, 255), width=sw)
        elif ann.type == AnnotationType.UNDERLINE:
            draw.line([x, y + h, x + w, y + h], fill=stroke, width=sw)
        elif ann.type == AnnotationType.STRIKEOUT:
            my = y + max(h, 2) / 2.0
            draw.line([x, my, x + w, my], fill=stroke, width=max(sw, 2))
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
                        # Deckkraft der Signatur/Stempel anwenden — 1.5.1
                        try:
                            op = float(getattr(ann, "opacity", 1.0) or 1.0)
                        except (TypeError, ValueError):
                            op = 1.0
                        op = max(0.05, min(1.0, op))
                        if op < 0.999:
                            r, g, b, a = stamp.split()
                            a = a.point(lambda v, o=op: max(0, min(255, int(round(v * o)))))
                            stamp = Image.merge("RGBA", (r, g, b, a))
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
            tags = [str(t).casefold() for t in (getattr(ann, "tags", None) or [])]
            text_only = bool(getattr(ann, "stamp_text_only", False)) or "ild-stamp-text-only" in tags
            frame = bool(getattr(ann, "stamp_frame", True)) and not text_only
            if "ild-stamp-no-frame" in tags:
                frame = False
            if float(getattr(ann, "stroke_width", 0) or 0) < 0.5:
                frame = False
            shadow = bool(getattr(ann, "stamp_shadow", False)) or "ild-stamp-shadow" in tags
            outline = (
                bool(getattr(ann, "stamp_outline", False)) or "ild-stamp-outline" in tags
            ) and not text_only
            fill_src = "" if text_only else str(getattr(ann, "fill_color", "") or "").strip()
            try:
                sw_stamp = int(float(getattr(ann, "stroke_width", 3) or 0))
            except (TypeError, ValueError):
                sw_stamp = 3
            if frame or outline:
                sw_stamp = max(1, sw_stamp if sw_stamp >= 1 else (5 if outline else 3))

            def _draw_stamp_box(d, ox, oy, bw_, bh_):
                if shadow:
                    d.rectangle(
                        [ox + 3, oy + 3, ox + bw_ + 3, oy + bh_ + 3],
                        fill=(0, 0, 0, 90),
                    )
                if fill_src:
                    d.rectangle(
                        [ox, oy, ox + bw_, oy + bh_],
                        fill=_parse_color(fill_src, _opacity_alpha(ann, 80)),
                    )
                if frame or outline:
                    d.rectangle(
                        [ox, oy, ox + bw_, oy + bh_],
                        outline=stroke,
                        width=sw_stamp,
                    )
                font = _font(14)
                ty = oy + 6
                for line in (ann.text or "STEMPEL").splitlines()[:3]:
                    d.text((ox + 8, ty), line[:28], fill=stroke, font=font)
                    ty += 16

            if rot:
                cx = int(x + bw / 2)
                cy = int(y + box_h / 2)
                pad = int(max(bw, box_h) * 1.5) + 8
                tile = Image.new("RGBA", (pad * 2, pad * 2), (0, 0, 0, 0))
                td = ImageDraw.Draw(tile)
                ox, oy = pad - int(bw / 2), pad - int(box_h / 2)
                _draw_stamp_box(td, ox, oy, bw, box_h)
                tile = tile.rotate(-rot, expand=True, resample=Image.Resampling.BICUBIC)
                tw, th = tile.size
                overlay.paste(tile, (cx - tw // 2, cy - th // 2), tile)
                continue
            _draw_stamp_box(draw, x, y, bw, box_h)
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
            fill_src = str(getattr(ann, "fill_color", "") or "").strip()
            if fill_src:
                fill = _parse_color(fill_src, _opacity_alpha(ann, 90))
            else:
                fill = _parse_color(ann.color, _opacity_alpha(ann, 40))
            draw.rectangle([x, y, x + w, y + h], fill=fill, outline=stroke, width=sw)
        elif ann.type in (AnnotationType.ELLIPSE, AnnotationType.TRIANGLE, AnnotationType.ROUNDED_RECT):
            fill_src = str(getattr(ann, "fill_color", "") or "").strip()
            fill = _parse_color(fill_src, _opacity_alpha(ann, 110)) if fill_src else None
            box = [x, y, x + max(w, 4), y + max(h, 4)]
            if ann.type == AnnotationType.ELLIPSE:
                if fill:
                    draw.ellipse(box, fill=fill, outline=stroke, width=sw)
                else:
                    draw.ellipse(box, outline=stroke, width=sw)
            elif ann.type == AnnotationType.ROUNDED_RECT:
                rad = max(4, int(min(max(w, 4), max(h, 4)) * 0.18))
                if fill:
                    draw.rounded_rectangle(box, radius=rad, fill=fill, outline=stroke, width=sw)
                else:
                    draw.rounded_rectangle(box, radius=rad, outline=stroke, width=sw)
            else:
                pts = [
                    (x + max(w, 4) / 2.0, y),
                    (x, y + max(h, 4)),
                    (x + max(w, 4), y + max(h, 4)),
                ]
                if fill:
                    draw.polygon(pts, fill=fill, outline=stroke)
                else:
                    draw.polygon(pts, outline=stroke)
        elif ann.type == AnnotationType.MEASURE_AREA:
            draw.rectangle(
                [x, y, x + w, y + h],
                fill=_parse_color(ann.color, _opacity_alpha(ann, 30)),
                outline=stroke,
                width=sw,
            )
            label = ann.text or ann.measure_label(scale, unit="mm")
            font = _font(11)
            draw.text((x + 4, y + 4), label, fill=stroke, font=font)
        elif ann.type == AnnotationType.MEASURE_ANGLE:
            x2, y2 = ann.end_point()
            x3 = float(ann.p3_x) if (ann.p3_x or ann.p3_y) else float(ann.x + ann.width)
            y3 = float(ann.p3_y) if (ann.p3_x or ann.p3_y) else float(ann.y)
            draw.line([ann.x, ann.y, x2, y2], fill=stroke, width=sw)
            draw.line([x2, y2, x3, y3], fill=stroke, width=sw)
            label = ann.text or ann.measure_label(scale)
            font = _font(11)
            draw.text((x2 + 4, y2 - 14), label, fill=stroke, font=font)
        elif ann.type in (AnnotationType.LINE, AnnotationType.ARROW, AnnotationType.MEASURE):
            x2, y2 = ann.end_point()
            draw.line([ann.x, ann.y, x2, y2], fill=stroke, width=sw)
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
        elif ann.type == AnnotationType.INK:
            # Freihand-Polyline — 2.2.0
            pts = []
            for pt in getattr(ann, "points", None) or []:
                if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    try:
                        pts.append((float(pt[0]), float(pt[1])))
                    except (TypeError, ValueError):
                        continue
            if len(pts) >= 2:
                draw.line(pts, fill=stroke, width=sw, joint="curve")
            elif len(pts) == 1:
                px, py = pts[0]
                r = max(1, sw)
                draw.ellipse([px - r, py - r, px + r, py + r], fill=stroke)

    return Image.alpha_composite(base, overlay).convert("RGB")


def flatten_annotations_to_pdf(
    pdf_path: str | Path,
    store: AnnotationStore | Sequence[Annotation],
    *,
    scale: float = 2.0,
    out_path: str | Path | None = None,
    password: str | None = None,
    grayscale: bool = False,
    page_indices: Sequence[int] | None = None,
    progress=None,
    should_cancel=None,
) -> Path:
    """
    Seiten rendern, Annotationen einzeichnen (flatten/bake) und als neues PDF speichern.
    Original und Sidecar bleiben unverändert. Koordinaten = Render-Pixel bei `scale`.
    ``page_indices``: optional 0-basiert — nur diese Seiten (Reihenfolge behalten).

    progress(msg, current=i, total=n) — optional.
    should_cancel() → True bricht ab (raises InterruptedError).
    """
    import pikepdf

    pdf_path = Path(pdf_path)
    if out_path is None:
        out_path = pdf_path.with_name(f"{pdf_path.stem}_flattened.pdf")
    else:
        out_path = Path(out_path)

    space = "render_pixels"
    if isinstance(store, AnnotationStore):
        anns = list(store.annotations)
        space = str((store._meta or {}).get("coord_space") or "render_pixels")
    else:
        anns = list(store)

    by_page: dict[int, list[Annotation]] = {}
    for a in anns:
        by_page.setdefault(int(a.page), []).append(a)
    pts_space = str(space).strip().lower() in ("pdf_points", "pdf-pt", "pt")

    scale = max(float(scale), 0.5)
    pages_out: List[Image.Image] = []
    with PdfDocument(pdf_path, password=password) as doc:
        n = len(doc)
        if page_indices is None:
            indices = list(range(n))
        else:
            indices = []
            seen: set[int] = set()
            for raw_i in page_indices:
                i = int(raw_i)
                if i in seen:
                    continue
                if i < 0 or i >= n:
                    raise IndexError(f"Seite {i + 1} existiert nicht (1..{n})")
                seen.add(i)
                indices.append(i)
            if not indices:
                raise ValueError("Keine Seiten für Flatten ausgewählt")
        sizes = [doc.page_size(i) for i in indices]

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

    total_pages = len(indices)
    for pos, i in enumerate(indices):
        if _cancelled():
            raise InterruptedError("Flatten abgebrochen")
        _prog(f"Seite {i + 1} ({pos + 1}/{total_pages}) rendern…", pos, total_pages)
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
            if pts_space and abs(scale - 1.0) > 1e-9:
                drawn: list[Annotation] = []
                for a in page_anns:
                    d = deepcopy(a)
                    scale_annotation(d, scale)
                    drawn.append(d)
                page_anns = drawn
            raw = draw_annotations_on_image(raw, page_anns, scale=scale)
        elif raw.mode != "RGB":
            raw = raw.convert("RGB")
        pages_out.append(raw)

    if _cancelled():
        raise InterruptedError("Flatten abgebrochen")
    _prog("PDF schreiben…", total_pages, total_pages + 1)
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
    _prog("Fertig", total_pages + 1, total_pages + 1)
    return out_path


# Alias klarer Name
bake_annotations = flatten_annotations_to_pdf
