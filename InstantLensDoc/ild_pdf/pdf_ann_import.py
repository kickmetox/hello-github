"""Native PDF-Markup-Annotationen (pikepdf) grob in Sidecar-Annotationen mappen — 2.1.0."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

from .annotate import Annotation, AnnotationStore, AnnotationType


# Subtypes die wir grob übernehmen (Markup / Zeichnung); Link/Widget bewusst ausgelassen
_SUBTYPE_MAP: dict[str, AnnotationType] = {
    "Highlight": AnnotationType.HIGHLIGHT,
    "Underline": AnnotationType.UNDERLINE,
    "Squiggly": AnnotationType.UNDERLINE,
    "StrikeOut": AnnotationType.UNDERLINE,
    "Text": AnnotationType.STICKY,
    "FreeText": AnnotationType.TEXT,
    "Stamp": AnnotationType.STAMP,
    "Square": AnnotationType.RECTANGLE,
    "Circle": AnnotationType.RECTANGLE,
    "Line": AnnotationType.LINE,
    "Ink": AnnotationType.LINE,
    "Caret": AnnotationType.STICKY,
    "Polygon": AnnotationType.RECTANGLE,
    "PolyLine": AnnotationType.LINE,
}


@dataclass(frozen=True)
class NativeAnnImportResult:
    """Ergebnis des nativen PDF-Kommentar-Imports."""

    annotations: List[Annotation]
    imported: int
    skipped: int
    pages_scanned: int

    @property
    def count(self) -> int:
        return self.imported


def _color_from_annot(obj) -> str:
    """/C Array → #RRGGBB; Fallback Gelb."""
    try:
        c = obj.get("/C")
        if c is not None and len(c) >= 3:
            r = max(0, min(255, int(round(float(c[0]) * 255))))
            g = max(0, min(255, int(round(float(c[1]) * 255))))
            b = max(0, min(255, int(round(float(c[2]) * 255))))
            return f"#{r:02X}{g:02X}{b:02X}"
    except Exception:
        pass
    return "#FFFF00"


def _contents(obj) -> str:
    for key in ("/Contents", "/RC"):
        try:
            val = obj.get(key)
            if val is None:
                continue
            s = str(val).strip()
            if s:
                # grobes RC (rich content) strippen
                if "<" in s and ">" in s:
                    import re

                    s = re.sub(r"<[^>]+>", " ", s)
                    s = " ".join(s.split())
                return s[:2000]
        except Exception:
            continue
    return ""


def _rect_to_xywh(
    rect, page_h: float, scale: float
) -> tuple[float, float, float, float]:
    left = float(rect[0])
    bottom = float(rect[1])
    right = float(rect[2])
    top = float(rect[3])
    x0 = min(left, right) * scale
    x1 = max(left, right) * scale
    y0 = (page_h - max(bottom, top)) * scale
    y1 = (page_h - min(bottom, top)) * scale
    return x0, y0, max(x1 - x0, 1.0), max(y1 - y0, 1.0)


def _line_endpoints(
    obj, page_h: float, scale: float
) -> Optional[tuple[float, float, float, float]]:
    """/L [x1 y1 x2 y2] → (x0,y0,x1,y1) in Render-Pixeln."""
    try:
        line = obj.get("/L")
        if line is None or len(line) < 4:
            return None
        x1 = float(line[0]) * scale
        y1 = (page_h - float(line[1])) * scale
        x2 = float(line[2]) * scale
        y2 = (page_h - float(line[3])) * scale
        return x1, y1, x2, y2
    except Exception:
        return None


def _ink_endpoints(
    obj, page_h: float, scale: float
) -> Optional[tuple[float, float, float, float]]:
    """Erste Ink-Liste: Start/Ende grob als Linie."""
    try:
        ink = obj.get("/InkList")
        if ink is None or len(ink) < 1:
            return None
        pts = ink[0]
        if pts is None or len(pts) < 4:
            return None
        x1 = float(pts[0]) * scale
        y1 = (page_h - float(pts[1])) * scale
        x2 = float(pts[-2]) * scale
        y2 = (page_h - float(pts[-1])) * scale
        return x1, y1, x2, y2
    except Exception:
        return None


def import_native_pdf_annotations(
    pdf_path: str | Path,
    *,
    scale: float = 1.0,
    password: str | None = None,
    page_indices: Sequence[int] | None = None,
) -> NativeAnnImportResult:
    """
    Liest bestehende PDF-Annotationen (Markup) via pikepdf und mappt sie grob
    auf Sidecar-``Annotation``-Objekte (Koordinaten wie UI: Y von oben).

    Nicht übernommen: Link, Widget/AcroForm, Popup-only, unbekannte Subtypes.
    QuadPoints → Bounding-Rect (kein Zeichen-genaues Highlight).
    """
    import pikepdf
    from pikepdf import Name

    path = Path(pdf_path)
    anns: List[Annotation] = []
    skipped = 0
    pages_scanned = 0
    open_kw: dict = {}
    if password:
        open_kw["password"] = password

    with pikepdf.open(path, **open_kw) as doc:
        indices = (
            list(page_indices)
            if page_indices is not None
            else list(range(len(doc.pages)))
        )
        for page_index in indices:
            if page_index < 0 or page_index >= len(doc.pages):
                continue
            pages_scanned += 1
            page = doc.pages[page_index]
            mediabox = page.mediabox
            page_h = float(mediabox[3] - mediabox[1])
            annots = page.get("/Annots")
            if annots is None:
                continue
            for annot in annots:
                try:
                    obj = annot.get_object() if hasattr(annot, "get_object") else annot
                    subtype = obj.get("/Subtype")
                    if subtype is None:
                        skipped += 1
                        continue
                    name = str(subtype).lstrip("/")
                    # Popup / Link / Widget überspringen
                    if name in ("Popup", "Link", "Widget", "FileAttachment", "Sound", "Movie", "Screen", "PrinterMark", "TrapNet", "Watermark", "3D"):
                        skipped += 1
                        continue
                    atype = _SUBTYPE_MAP.get(name)
                    if atype is None:
                        skipped += 1
                        continue
                    rect = obj.get("/Rect")
                    if rect is None or len(rect) < 4:
                        skipped += 1
                        continue
                    x, y, w, h = _rect_to_xywh(rect, page_h, scale)
                    color = _color_from_annot(obj)
                    text = _contents(obj)
                    if not text:
                        text = name
                    try:
                        op = float(obj.get("/CA", 1.0) or 1.0)
                    except Exception:
                        op = 1.0
                    op = max(0.05, min(1.0, op))

                    if atype == AnnotationType.LINE:
                        ends = _line_endpoints(obj, page_h, scale) or _ink_endpoints(
                            obj, page_h, scale
                        )
                        if ends:
                            x1, y1, x2, y2 = ends
                            ann = Annotation(
                                page=page_index,
                                type=atype,
                                x=x1,
                                y=y1,
                                width=abs(x2 - x1),
                                height=abs(y2 - y1),
                                callout_x=x2,
                                callout_y=y2,
                                text=text,
                                color=color,
                                opacity=op,
                                tags=["pdf-import", name.lower()],
                            )
                        else:
                            ann = Annotation(
                                page=page_index,
                                type=atype,
                                x=x,
                                y=y,
                                width=w,
                                height=h,
                                callout_x=x + w,
                                callout_y=y + h,
                                text=text,
                                color=color,
                                opacity=op,
                                tags=["pdf-import", name.lower()],
                            )
                    elif atype in (AnnotationType.HIGHLIGHT, AnnotationType.UNDERLINE):
                        # QuadPoints → erstes Quad als Box (grob)
                        try:
                            qp = obj.get("/QuadPoints")
                            if qp is not None and len(qp) >= 8:
                                xs = [float(qp[i]) for i in range(0, 8, 2)]
                                ys = [float(qp[i]) for i in range(1, 8, 2)]
                                left, right = min(xs), max(xs)
                                bottom, top = min(ys), max(ys)
                                x = left * scale
                                w = max((right - left) * scale, 1.0)
                                y = (page_h - top) * scale
                                h = max((top - bottom) * scale, 1.0)
                        except Exception:
                            pass
                        ann = Annotation(
                            page=page_index,
                            type=atype,
                            x=x,
                            y=y,
                            width=w,
                            height=h,
                            text=text,
                            color=color,
                            opacity=op,
                            tags=["pdf-import", name.lower()],
                        )
                    else:
                        ann = Annotation(
                            page=page_index,
                            type=atype,
                            x=x,
                            y=y,
                            width=max(w, 24.0),
                            height=max(h, 18.0),
                            text=text,
                            color=color,
                            opacity=op,
                            tags=["pdf-import", name.lower()],
                        )
                    anns.append(ann)
                except Exception:
                    skipped += 1
                    continue

    return NativeAnnImportResult(
        annotations=anns,
        imported=len(anns),
        skipped=skipped,
        pages_scanned=pages_scanned,
    )


def import_native_into_store(
    store: AnnotationStore,
    pdf_path: str | Path | None = None,
    *,
    replace: bool = False,
    scale: float = 1.0,
    password: str | None = None,
) -> NativeAnnImportResult:
    """
    Native PDF-Annotationen laden und in ``store`` schreiben (Sidecar dirty).
    ``replace=True`` ersetzt bestehende Sidecar-Einträge.
    """
    path = Path(pdf_path) if pdf_path else store.pdf_path
    if path is None:
        raise ValueError("Kein PDF-Pfad für nativen Kommentar-Import.")
    result = import_native_pdf_annotations(path, scale=scale, password=password)
    store._push_undo()  # noqa: SLF001 — ein Undo-Schritt für den Import
    if replace:
        store.annotations = list(result.annotations)
    else:
        store.annotations.extend(list(result.annotations))
    store.dirty = True
    return result
