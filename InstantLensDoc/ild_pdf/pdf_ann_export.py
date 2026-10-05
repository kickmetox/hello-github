"""Sidecar-Annotationen als native PDF-/Annots schreiben (pikepdf) — 2.6.54.

Koordinaten im Store: PDF-Punkte, Y von oben (``coord_space=pdf_points``).
Alte Sidecars (``render_pixels``) werden mit ``render_scale`` umgerechnet.
Jede ILD-Annotation trägt ``/NM = ild:<id>``; beim Speichern werden nur diese
ersetzt, fremde Annots bleiben.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Optional, Sequence

from .annotate import Annotation, AnnotationStore, AnnotationType, scale_annotation

ILD_ANN_NM_PREFIX = "ild:"


def _hex_rgb(color: str) -> list[float]:
    c = (color or "#FFFF00").strip().lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    try:
        r = int(c[0:2], 16) / 255.0
        g = int(c[2:4], 16) / 255.0
        b = int(c[4:6], 16) / 255.0
        return [round(r, 4), round(g, 4), round(b, 4)]
    except Exception:
        return [1.0, 1.0, 0.0]


def _page_height(page) -> float:
    box = page.mediabox
    return float(box[3] - box[1])


def _to_pdf_xy(x: float, y: float, page_h: float) -> tuple[float, float]:
    """UI (Y unten wächst nach unten) → PDF-User-Space (Y nach oben)."""
    return float(x), float(page_h) - float(y)


def _pdf_rect(ann: Annotation, page_h: float) -> list[float]:
    x0, y0 = float(ann.x), float(ann.y)
    x1 = x0 + max(float(ann.width), 1.0)
    y1 = y0 + max(float(ann.height), 1.0)
    px0, py_top = _to_pdf_xy(min(x0, x1), min(y0, y1), page_h)
    px1, py_bot = _to_pdf_xy(max(x0, x1), max(y0, y1), page_h)
    # Rect: llx, lly, urx, ury
    return [
        min(px0, px1),
        min(py_top, py_bot),
        max(px0, px1),
        max(py_top, py_bot),
    ]


def _quad_points(ann: Annotation, page_h: float) -> list[float]:
    """Highlight/Underline/StrikeOut QuadPoints: UL, UR, LL, LR (PDF-Y)."""
    x0, y0 = float(ann.x), float(ann.y)
    x1 = x0 + max(float(ann.width), 1.0)
    y1 = y0 + max(float(ann.height), 1.0)
    ulx, uly = _to_pdf_xy(x0, y0, page_h)
    urx, ury = _to_pdf_xy(x1, y0, page_h)
    llx, lly = _to_pdf_xy(x0, y1, page_h)
    lrx, lry = _to_pdf_xy(x1, y1, page_h)
    return [ulx, uly, urx, ury, llx, lly, lrx, lry]


def _ann_to_points(ann: Annotation, store: AnnotationStore | None) -> Annotation:
    """Kopie in PDF-Punkten (Y oben)."""
    out = deepcopy(ann)
    space = "pdf_points"
    scale = 1.0
    if store is not None:
        meta = getattr(store, "_meta", {}) or {}
        space = str(meta.get("coord_space") or "render_pixels")
        try:
            scale = float(meta.get("render_scale") or 1.5)
        except (TypeError, ValueError):
            scale = 1.5
    if space != "pdf_points":
        scale_annotation(out, 1.0 / max(scale, 0.01))
    return out


def _subtype_for(ann: Annotation) -> str:
    t = ann.type
    if t == AnnotationType.HIGHLIGHT:
        return "Highlight"
    if t == AnnotationType.UNDERLINE:
        return "Underline"
    if t == AnnotationType.STRIKEOUT:
        return "StrikeOut"
    if t == AnnotationType.STICKY:
        return "Text"
    if t in (AnnotationType.TEXT, AnnotationType.TEXT_OVERLAY, AnnotationType.CALLOUT):
        return "FreeText"
    if t == AnnotationType.STAMP:
        return "Stamp"
    if t == AnnotationType.RECTANGLE:
        return "Square"
    if t == AnnotationType.ELLIPSE:
        return "Circle"
    if t == AnnotationType.ARROW:
        return "Line"
    if t == AnnotationType.LINE:
        return "Line"
    if t == AnnotationType.INK:
        return "Ink"
    if t == AnnotationType.LINK:
        return "Link"
    if t == AnnotationType.REDACTION:
        return "Square"
    return "Square"


def _build_annot_dict(pdf, ann: Annotation, page_h: float):
    import pikepdf

    subtype = _subtype_for(ann)
    rgb = _hex_rgb(ann.color)
    try:
        ca = float(getattr(ann, "opacity", 1.0) or 1.0)
    except (TypeError, ValueError):
        ca = 1.0
    ca = max(0.05, min(1.0, ca))
    rect = _pdf_rect(ann, page_h)
    d = pdf.make_indirect(
        pikepdf.Dictionary(
            {
                "/Type": pikepdf.Name("/Annot"),
                "/Subtype": pikepdf.Name(f"/{subtype}"),
                "/Rect": pikepdf.Array(rect),
                "/C": pikepdf.Array(rgb),
                "/CA": ca,
                "/F": 4,  # Print
                "/NM": pikepdf.String(f"{ILD_ANN_NM_PREFIX}{ann.id}"),
                "/Contents": pikepdf.String(str(ann.text or "")),
            }
        )
    )
    obj = d.get_object() if hasattr(d, "get_object") else d
    if subtype in ("Highlight", "Underline", "StrikeOut"):
        obj["/QuadPoints"] = pikepdf.Array(_quad_points(ann, page_h))
    if subtype == "FreeText":
        fs = max(8.0, float(getattr(ann, "font_size", 12.0) or 12.0))
        r, g, b = rgb
        obj["/DA"] = pikepdf.String(f"/Helv {fs:.1f} Tf {r:.3f} {g:.3f} {b:.3f} rg")
        rot = float(getattr(ann, "rotation", 0.0) or 0.0)
        if rot:
            obj["/Rotate"] = int(round(rot)) % 360
    if subtype == "Stamp":
        rot = float(getattr(ann, "rotation", 0.0) or 0.0)
        if rot:
            obj["/Rotate"] = int(round(rot / 90.0)) % 4 * 90
    if subtype == "Line":
        x2, y2 = ann.end_point()
        x1p, y1p = _to_pdf_xy(ann.x, ann.y, page_h)
        x2p, y2p = _to_pdf_xy(x2, y2, page_h)
        obj["/L"] = pikepdf.Array([x1p, y1p, x2p, y2p])
        if ann.type == AnnotationType.ARROW:
            obj["/LE"] = pikepdf.Array([pikepdf.Name("/None"), pikepdf.Name("/ClosedArrow")])
    if subtype == "Ink":
        pts = ann.ink_points()
        flat: list[float] = []
        for px, py in pts:
            qx, qy = _to_pdf_xy(px, py, page_h)
            flat.extend([qx, qy])
        if len(flat) >= 4:
            obj["/InkList"] = pikepdf.Array([pikepdf.Array(flat)])
    if subtype == "Link":
        uri = str(ann.text or "").strip()
        if uri:
            obj["/A"] = pikepdf.Dictionary(
                {
                    "/S": pikepdf.Name("/URI"),
                    "/URI": pikepdf.String(uri),
                }
            )
    if subtype in ("Square", "Circle"):
        try:
            sw = float(getattr(ann, "stroke_width", 2.0) or 2.0)
        except (TypeError, ValueError):
            sw = 2.0
        obj["/Border"] = pikepdf.Array([0, 0, max(1.0, sw)])
        fill = str(getattr(ann, "fill_color", "") or "").strip()
        if fill:
            obj["/IC"] = pikepdf.Array(_hex_rgb(fill))
    return d


def strip_ild_annots(page) -> None:
    """Entfernt nur ILD-eigene Annots (``/NM`` beginnt mit ``ild:``)."""
    import pikepdf

    annots = page.get("/Annots")
    if annots is None:
        return
    kept = pikepdf.Array()
    for annot in annots:
        try:
            obj = annot.get_object() if hasattr(annot, "get_object") else annot
            nm = str(obj.get("/NM", "") or "")
            if nm.startswith(ILD_ANN_NM_PREFIX):
                continue
            kept.append(annot)
        except Exception:
            kept.append(annot)
    if len(kept) == 0:
        try:
            del page["/Annots"]
        except Exception:
            page["/Annots"] = pikepdf.Array()
    else:
        page["/Annots"] = kept


def write_annotations_to_pdf(
    pdf_path: str | Path,
    store: AnnotationStore | Sequence[Annotation],
    *,
    password: Optional[str] = None,
    scale: float | None = None,
) -> Path:
    """Schreibt Store-Annotationen als native PDF-Annots. Rückgabe: Pfad."""
    import pikepdf

    path = Path(pdf_path)
    anns: list[Annotation]
    meta_store: AnnotationStore | None
    if isinstance(store, AnnotationStore):
        anns = list(store.annotations)
        meta_store = store
        if scale is None:
            try:
                scale = float((store._meta or {}).get("render_scale") or 0.0) or None
            except (TypeError, ValueError):
                scale = None
    else:
        anns = list(store)
        meta_store = None

    open_kw: dict = {"allow_overwriting_input": True}
    if password:
        open_kw["password"] = password
    with pikepdf.open(path, **open_kw) as pdf:
        by_page: dict[int, list[Annotation]] = {}
        for raw in anns:
            pt = _ann_to_points(raw, meta_store)
            by_page.setdefault(int(pt.page), []).append(pt)
        for i, page in enumerate(pdf.pages):
            strip_ild_annots(page)
            page_h = _page_height(page)
            page_anns = by_page.get(i, [])
            if not page_anns:
                continue
            annots = page.get("/Annots")
            if annots is None:
                annots = pikepdf.Array()
                page["/Annots"] = annots
            for ann in page_anns:
                try:
                    annots.append(_build_annot_dict(pdf, ann, page_h))
                except Exception:
                    continue
        pdf.save(path)
    return path


def read_ild_annots(
    pdf_path: str | Path,
    *,
    password: Optional[str] = None,
    page_index: int = 0,
) -> list[dict]:
    """Liest ILD-Annots einer Seite (für Tests): Subtype, Rect, Contents, NM."""
    import pikepdf

    path = Path(pdf_path)
    open_kw: dict = {}
    if password:
        open_kw["password"] = password
    out: list[dict] = []
    with pikepdf.open(path, **open_kw) as pdf:
        if page_index < 0 or page_index >= len(pdf.pages):
            return out
        page = pdf.pages[page_index]
        annots = page.get("/Annots")
        if annots is None:
            return out
        for annot in annots:
            try:
                obj = annot.get_object() if hasattr(annot, "get_object") else annot
                nm = str(obj.get("/NM", "") or "")
                if not nm.startswith(ILD_ANN_NM_PREFIX):
                    continue
                subtype = str(obj.get("/Subtype") or "").lstrip("/")
                rect = obj.get("/Rect")
                rect_l = [float(rect[i]) for i in range(4)] if rect is not None else []
                contents = str(obj.get("/Contents") or "")
                out.append(
                    {
                        "nm": nm,
                        "subtype": subtype,
                        "rect": rect_l,
                        "contents": contents,
                        "quad": (
                            [float(x) for x in obj.get("/QuadPoints")]
                            if obj.get("/QuadPoints") is not None
                            else None
                        ),
                        "ink": obj.get("/InkList") is not None,
                    }
                )
            except Exception:
                continue
    return out
