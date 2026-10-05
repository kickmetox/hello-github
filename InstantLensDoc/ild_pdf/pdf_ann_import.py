"""Native PDF-Markup-Annotationen (pikepdf) grob in Sidecar-Annotationen mappen — 2.1.0–2.1.5."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Sequence

from .annotate import Annotation, AnnotationStore, AnnotationType


# Subtypes die wir grob übernehmen (Markup / Zeichnung); Link/Widget bewusst ausgelassen
_SUBTYPE_MAP: dict[str, AnnotationType] = {
    "Highlight": AnnotationType.HIGHLIGHT,
    "Underline": AnnotationType.UNDERLINE,
    "Squiggly": AnnotationType.UNDERLINE,
    "StrikeOut": AnnotationType.STRIKEOUT,
    "Text": AnnotationType.STICKY,
    "FreeText": AnnotationType.TEXT,
    "Stamp": AnnotationType.STAMP,
    "Square": AnnotationType.RECTANGLE,
    "Circle": AnnotationType.ELLIPSE,
    "Line": AnnotationType.LINE,
    "Ink": AnnotationType.INK,
    "Caret": AnnotationType.STICKY,
    "Polygon": AnnotationType.RECTANGLE,
    "PolyLine": AnnotationType.LINE,
}

# Duplikat-Strategie beim Schreiben in den Sidecar — 2.1.1
DUPLICATE_STRATEGIES = ("keep", "skip", "replace")

ProgressCallback = Callable[[int, int, str], None]
CancelCallback = Callable[[], bool]


@dataclass
class NativeAnnImportResult:
    """Ergebnis des nativen PDF-Kommentar-Imports — 2.1.0–2.1.3."""

    annotations: List[Annotation] = field(default_factory=list)
    imported: int = 0
    skipped: int = 0
    pages_scanned: int = 0
    candidates: int = 0  # Roh-Treffer vor Duplikat-Filter — 2.1.1
    duplicates_found: int = 0
    duplicates_skipped: int = 0
    duplicates_replaced: int = 0
    cancelled: bool = False
    dry_run: bool = False

    @property
    def count(self) -> int:
        return self.imported

    @property
    def skipped_total(self) -> int:
        """Typen-Skip + Duplikat-Skip — 2.1.2."""
        return int(self.skipped) + int(self.duplicates_skipped)

    @property
    def replaced_count(self) -> int:
        """Ersetzte Duplikate — 2.1.3."""
        return int(self.duplicates_replaced)

    @property
    def new_count(self) -> int:
        """Neu hinzugefügte (ohne Ersetzungen) — 2.1.3."""
        return max(0, int(self.imported) - int(self.duplicates_replaced))

    def status_counts_de(self) -> str:
        """Statuszeile „ersetzt X, übersprungen Y, neu Z“ — 2.1.3."""
        return (
            f"ersetzt {self.replaced_count}, "
            f"übersprungen {self.skipped_total}, "
            f"neu {self.new_count}"
        )

    def copyable_status_text(self) -> str:
        """Kopierbarer Detail-Status (ersetzt/übersprungen/neu + Meta) — 2.1.3."""
        lines = [
            self.status_counts_de(),
            f"importiert={int(self.imported)}",
            f"Kandidaten={self.candidates or self.imported}",
            f"Seiten={self.pages_scanned}",
            f"Typen-Skip={int(self.skipped)}",
            f"Duplikate={int(self.duplicates_found)}",
            f"Duplikate-skip={int(self.duplicates_skipped)}",
            f"Duplikate-ersetzt={int(self.duplicates_replaced)}",
        ]
        if self.cancelled:
            lines.append("abgebrochen=ja")
        if self.dry_run:
            lines.append("Dry-Run=ja")
        return "\n".join(lines)

    def summary_de(self) -> str:
        """Kurze DE-Zusammenfassung der Zähler — 2.1.1–2.1.3."""
        parts = [
            self.status_counts_de(),
            f"Kandidaten={self.candidates or self.imported}",
            f"Seiten={self.pages_scanned}",
        ]
        if self.duplicates_found:
            parts.append(f"Duplikate={self.duplicates_found}")
        if self.duplicates_skipped:
            parts.append(f"Duplikate-skip={self.duplicates_skipped}")
        if self.duplicates_replaced:
            parts.append(f"Duplikate-ersetzt={self.duplicates_replaced}")
        if self.cancelled:
            parts.append("abgebrochen")
        if self.dry_run:
            parts.append("Dry-Run")
        return ", ".join(parts)


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


def _ink_points_list(obj, page_h: float, scale: float) -> list[list[float]]:
    """/InkList → [[x,y], ...] in UI-Koordinaten (Y oben)."""
    out: list[list[float]] = []
    try:
        ink = obj.get("/InkList")
        if ink is None or len(ink) < 1:
            return out
        pts = ink[0]
        if pts is None or len(pts) < 4:
            return out
        for i in range(0, len(pts) - 1, 2):
            x = float(pts[i]) * scale
            y = (page_h - float(pts[i + 1])) * scale
            out.append([x, y])
    except Exception:
        return []
    return out


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


def _ann_bbox_close(a: Annotation, b: Annotation, *, tol: float = 2.0) -> bool:
    """Gleiche Seite+Typ+BBox (±tol) — Duplikat-Erkennung — 2.1.1."""
    if int(a.page) != int(b.page):
        return False
    if a.type != b.type:
        return False
    t = max(0.0, float(tol))
    return (
        abs(float(a.x) - float(b.x)) <= t
        and abs(float(a.y) - float(b.y)) <= t
        and abs(float(a.width) - float(b.width)) <= t
        and abs(float(a.height) - float(b.height)) <= t
    )


def find_matching_existing(
    candidate: Annotation,
    existing: Sequence[Annotation],
    *,
    tol: float = 2.0,
) -> Optional[Annotation]:
    """Erste Sidecar-Annotation die als Duplikat von ``candidate`` gilt — 2.1.1."""
    for ann in existing:
        if _ann_bbox_close(candidate, ann, tol=tol):
            return ann
    return None


def import_native_pdf_annotations(
    pdf_path: str | Path,
    *,
    scale: float = 1.0,
    password: str | None = None,
    page_indices: Sequence[int] | None = None,
    on_progress: ProgressCallback | None = None,
    should_cancel: CancelCallback | None = None,
) -> NativeAnnImportResult:
    """
    Liest bestehende PDF-Annotationen (Markup) via pikepdf und mappt sie grob
    auf Sidecar-``Annotation``-Objekte (Koordinaten wie UI: Y von oben).

    Nicht übernommen: Link, Widget/AcroForm, Popup-only, unbekannte Subtypes.
    QuadPoints → Bounding-Rect (kein Zeichen-genaues Highlight).
    Fortschritt/Abbruch optional — 2.1.1.
    """
    import pikepdf

    path = Path(pdf_path)
    anns: List[Annotation] = []
    skipped = 0
    pages_scanned = 0
    cancelled = False
    open_kw: dict = {}
    if password:
        open_kw["password"] = password

    with pikepdf.open(path, **open_kw) as doc:
        indices = (
            list(page_indices)
            if page_indices is not None
            else list(range(len(doc.pages)))
        )
        total_pages = max(1, len(indices))
        for pi, page_index in enumerate(indices):
            if should_cancel is not None and should_cancel():
                cancelled = True
                break
            if on_progress is not None:
                try:
                    on_progress(pi + 1, total_pages, f"Seite {page_index + 1}")
                except Exception:
                    pass
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
                if should_cancel is not None and should_cancel():
                    cancelled = True
                    break
                try:
                    obj = annot.get_object() if hasattr(annot, "get_object") else annot
                    subtype = obj.get("/Subtype")
                    if subtype is None:
                        skipped += 1
                        continue
                    name = str(subtype).lstrip("/")
                    # Popup / Link / Widget überspringen
                    if name in (
                        "Popup",
                        "Link",
                        "Widget",
                        "FileAttachment",
                        "Sound",
                        "Movie",
                        "Screen",
                        "PrinterMark",
                        "TrapNet",
                        "Watermark",
                        "3D",
                    ):
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

                    if atype == AnnotationType.INK:
                        ink_pts = _ink_points_list(obj, page_h, scale)
                        if ink_pts and len(ink_pts) >= 2:
                            ann = Annotation.from_ink_points(
                                page_index,
                                ink_pts,
                                color=color,
                            )
                            ann.text = text
                            ann.opacity = op
                            ann.tags = ["pdf-import", name.lower()]
                        else:
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
                    elif atype == AnnotationType.LINE:
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
                    elif atype in (AnnotationType.HIGHLIGHT, AnnotationType.UNDERLINE, AnnotationType.STRIKEOUT):
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
            if cancelled:
                break

    return NativeAnnImportResult(
        annotations=anns,
        imported=len(anns),
        skipped=skipped,
        pages_scanned=pages_scanned,
        candidates=len(anns),
        cancelled=cancelled,
        dry_run=False,
    )


def apply_duplicate_strategy(
    candidates: Sequence[Annotation],
    existing: Sequence[Annotation],
    *,
    strategy: str = "keep",
    tol: float = 2.0,
) -> tuple[List[Annotation], int, int, int]:
    """
    Duplikat-Strategie auf Import-Kandidaten anwenden — 2.1.1.

    strategy:
      - keep: alle behalten (auch Duplikate)
      - skip: Duplikate zu bestehendem Sidecar auslassen
      - replace: bestehende Duplikate markieren (IDs in replace-Liste via Mutator)

    Rückgabe: (zu_importierende, duplicates_found, duplicates_skipped, replace_ids_count)
    Für ``replace`` werden Matching-IDs als Annotation.id in der 4. Rückgabe
    nicht geliefert — Caller nutzt ``find_matching_existing`` erneut bzw.
    ``plan_duplicate_actions``.
    """
    strat = (strategy or "keep").strip().lower()
    if strat not in DUPLICATE_STRATEGIES:
        strat = "keep"
    found = 0
    skipped = 0
    replace_n = 0
    out: List[Annotation] = []
    # Working copy of existing for sequential skip/replace planning
    live = list(existing)
    for cand in candidates:
        match = find_matching_existing(cand, live, tol=tol)
        if match is None:
            out.append(cand)
            if strat == "replace":
                live.append(cand)
            continue
        found += 1
        if strat == "skip":
            skipped += 1
            continue
        if strat == "replace":
            replace_n += 1
            # Entferne Match aus Live-Liste, füge Kandidat hinzu
            live = [a for a in live if a.id != match.id]
            live.append(cand)
            out.append(cand)
            continue
        # keep
        out.append(cand)
    return out, found, skipped, replace_n


def plan_duplicate_actions(
    candidates: Sequence[Annotation],
    existing: Sequence[Annotation],
    *,
    strategy: str = "keep",
    tol: float = 2.0,
) -> tuple[List[Annotation], List[str], int, int, int]:
    """
    Plant Import: zu schreibende Annotationen + zu entfernende bestehende IDs.
    Rückgabe: (to_add, remove_ids, found, skipped, replaced) — 2.1.1.
    """
    strat = (strategy or "keep").strip().lower()
    if strat not in DUPLICATE_STRATEGIES:
        strat = "keep"
    found = 0
    skipped = 0
    replaced = 0
    to_add: List[Annotation] = []
    remove_ids: List[str] = []
    live = list(existing)
    for cand in candidates:
        match = find_matching_existing(cand, live, tol=tol)
        if match is None:
            to_add.append(cand)
            live.append(cand)
            continue
        found += 1
        if strat == "skip":
            skipped += 1
            continue
        if strat == "replace":
            replaced += 1
            remove_ids.append(match.id)
            live = [a for a in live if a.id != match.id]
            to_add.append(cand)
            live.append(cand)
            continue
        to_add.append(cand)
        live.append(cand)
    return to_add, remove_ids, found, skipped, replaced


def import_native_into_store(
    store: AnnotationStore,
    pdf_path: str | Path | None = None,
    *,
    replace: bool = False,
    scale: float = 1.0,
    password: str | None = None,
    duplicate_strategy: str = "keep",
    dry_run: bool = False,
    tol: float = 2.0,
    on_progress: ProgressCallback | None = None,
    should_cancel: CancelCallback | None = None,
) -> NativeAnnImportResult:
    """
    Native PDF-Annotationen laden und in ``store`` schreiben (Sidecar dirty).
    ``replace=True`` ersetzt bestehende Sidecar-Einträge.
    ``dry_run=True``: nur zählen, Store unverändert — 2.1.1.
    ``duplicate_strategy``: keep|skip|replace (bei replace=False relevant).
    """
    path = Path(pdf_path) if pdf_path else store.pdf_path
    if path is None:
        raise ValueError("Kein PDF-Pfad für nativen Kommentar-Import.")
    result = import_native_pdf_annotations(
        path,
        scale=scale,
        password=password,
        on_progress=on_progress,
        should_cancel=should_cancel,
    )
    if result.cancelled:
        result.dry_run = dry_run
        return result

    existing = [] if replace else list(store.annotations)
    result.candidates = len(result.annotations)
    to_add, remove_ids, dup_found, dup_skip, dup_repl = plan_duplicate_actions(
        result.annotations,
        existing,
        strategy="keep" if replace else duplicate_strategy,
        tol=tol,
    )
    result.duplicates_found = dup_found
    result.duplicates_skipped = dup_skip
    result.duplicates_replaced = dup_repl
    result.imported = len(to_add)
    result.annotations = list(to_add)
    result.dry_run = dry_run

    if dry_run:
        return result

    store._push_undo()  # noqa: SLF001 — ein Undo-Schritt für den Import
    if replace:
        store.annotations = list(to_add)
    else:
        if remove_ids:
            rid = set(remove_ids)
            store.annotations = [a for a in store.annotations if a.id not in rid]
        store.annotations.extend(list(to_add))
    store.dirty = True
    return result
