"""Objektmanipulation — Bilder, Vektorgrafiken und Tabellen — 2.6.5.

Praktischer Stack: pypdfium2 (PageObjects listen/hit-testen/transformieren,
gen_content + speichern) und pikepdf/Pillow (Bild ersetzen).

Koordinaten in der API: wie Annotationen / text_edit — X/Y von oben links
in Render-Pixeln bei ``scale`` (oder PDF-Punkten bei scale=1.0).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional, Sequence, Union

ObjectKind = Literal["image", "vector", "table"]


@dataclass
class DocumentObject:
    """Selektierbares Seitenobjekt (PDF-Punkte + optionale Render-Skalierung)."""

    page: int
    index: int  # Index unter top-level IMAGE/FORM auf der Seite
    kind: ObjectKind
    x: float  # links, Y von oben
    y: float
    width: float
    height: float
    label: str = ""
    # Roh-Bounds in PDF-Koordinaten (Y von unten): left, bottom, right, top
    pdf_left: float = 0.0
    pdf_bottom: float = 0.0
    pdf_right: float = 0.0
    pdf_top: float = 0.0

    def scaled(self, scale: float) -> "DocumentObject":
        s = float(scale) if scale else 1.0
        if s == 1.0:
            return self
        return DocumentObject(
            page=self.page,
            index=self.index,
            kind=self.kind,
            x=self.x * s,
            y=self.y * s,
            width=self.width * s,
            height=self.height * s,
            label=self.label,
            pdf_left=self.pdf_left,
            pdf_bottom=self.pdf_bottom,
            pdf_right=self.pdf_right,
            pdf_top=self.pdf_top,
        )

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width * 0.5, self.y + self.height * 0.5)


@dataclass
class ObjectEditResult:
    """Ergebnis einer Objekt-Transformation."""

    out_path: Path
    page: int
    index: int
    kind: ObjectKind
    action: str
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0


def _page_height_pt(pdf_path: Path, page_index: int, password: str | None) -> float:
    import pypdfium2 as pdfium

    kwargs = {}
    if password:
        kwargs["password"] = password
    doc = pdfium.PdfDocument(str(pdf_path), **kwargs)
    try:
        page = doc[page_index]
        return float(page.get_height())
    finally:
        doc.close()


def _open_doc(pdf_path: Path, password: str | None = None):
    import pypdfium2 as pdfium

    kwargs = {}
    if password:
        kwargs["password"] = password
    return pdfium.PdfDocument(str(pdf_path), **kwargs)


def _classify_form(page, form_obj) -> ObjectKind:
    """Heuristik: Form mit mehreren Pfaden ≈ Tabelle, sonst Vektorgrafik."""
    import pypdfium2 as pdfium

    try:
        nested = list(
            page.get_objects(
                filter=[pdfium.raw.FPDF_PAGEOBJ_PATH],
                max_depth=8,
                form=form_obj,
            )
        )
    except TypeError:
        # ältere Signatur ohne form=
        nested = []
        try:
            for o in page.get_objects(
                filter=[pdfium.raw.FPDF_PAGEOBJ_PATH], max_depth=8
            ):
                if getattr(o, "level", 0) and getattr(o, "level", 0) > 0:
                    nested.append(o)
        except Exception:
            nested = []
    except Exception:
        nested = []
    # Gitter: ≥4 Pfade oder ≥2 horizontale + ≥2 vertikale dünne Bounds
    if len(nested) >= 4:
        thin_h = 0
        thin_v = 0
        for p in nested:
            try:
                l, b, r, t = p.get_bounds()
            except Exception:
                continue
            w, h = abs(r - l), abs(t - b)
            if h <= 2.5 and w >= 8:
                thin_h += 1
            if w <= 2.5 and h >= 8:
                thin_v += 1
        if thin_h >= 2 and thin_v >= 2:
            return "table"
        if len(nested) >= 6:
            return "table"
    return "vector"


def _top_level_objects(page):
    """Top-level IMAGE + FORM (keine verschachtelten Form-Inhalte)."""
    import pypdfium2 as pdfium

    out = []
    for obj in page.get_objects(
        filter=[pdfium.raw.FPDF_PAGEOBJ_IMAGE, pdfium.raw.FPDF_PAGEOBJ_FORM],
        max_depth=1,
    ):
        # level 0 = Seite; Forms liefern ihre Kinder bei höherer depth
        if getattr(obj, "level", 0) not in (0, None):
            continue
        out.append(obj)
    # Fallback: wenn level nicht gesetzt, alle mit max_depth=1 nehmen
    if not out:
        out = list(
            page.get_objects(
                filter=[pdfium.raw.FPDF_PAGEOBJ_IMAGE, pdfium.raw.FPDF_PAGEOBJ_FORM],
                max_depth=1,
            )
        )
    return out


def _obj_to_doc(
    obj,
    *,
    page_index: int,
    index: int,
    page_h: float,
    page,
    scale: float,
) -> DocumentObject:
    import pypdfium2 as pdfium

    l, b, r, t = obj.get_bounds()
    w = max(float(r - l), 1.0)
    h = max(float(t - b), 1.0)
    y_top = float(page_h) - float(t)
    if obj.type == pdfium.raw.FPDF_PAGEOBJ_IMAGE:
        kind: ObjectKind = "image"
        label = f"Bild {index + 1}"
    else:
        kind = _classify_form(page, obj)
        label = f"Tabelle {index + 1}" if kind == "table" else f"Vektor {index + 1}"
    doc = DocumentObject(
        page=page_index,
        index=index,
        kind=kind,
        x=float(l),
        y=y_top,
        width=w,
        height=h,
        label=label,
        pdf_left=float(l),
        pdf_bottom=float(b),
        pdf_right=float(r),
        pdf_top=float(t),
    )
    return doc.scaled(scale)


def list_page_objects(
    pdf_path: str | Path,
    page_index: int = 0,
    *,
    scale: float = 1.0,
    password: str | None = None,
    kinds: Sequence[ObjectKind] | None = None,
) -> list[DocumentObject]:
    """Listet Bilder, Form-XObjects (Vektor) und tabellenartige Forms."""
    pdf_path = Path(pdf_path)
    doc = _open_doc(pdf_path, password)
    try:
        if page_index < 0 or page_index >= len(doc):
            raise IndexError(f"Seite {page_index} existiert nicht")
        page = doc[page_index]
        page_h = float(page.get_height())
        raw_objs = _top_level_objects(page)
        out: list[DocumentObject] = []
        for i, obj in enumerate(raw_objs):
            d = _obj_to_doc(
                obj,
                page_index=page_index,
                index=i,
                page_h=page_h,
                page=page,
                scale=scale,
            )
            if kinds is not None and d.kind not in kinds:
                continue
            out.append(d)
        return out
    finally:
        doc.close()


def hit_test_object(
    pdf_path: str | Path,
    page_index: int,
    x: float,
    y: float,
    *,
    scale: float = 1.0,
    password: str | None = None,
    pad: float = 2.0,
) -> Optional[DocumentObject]:
    """Kleinstes Objekt unter Punkt (Render-Koordinaten bei scale)."""
    objs = list_page_objects(
        pdf_path, page_index, scale=scale, password=password
    )
    if not objs:
        return None
    s = float(scale) if scale else 1.0
    px, py = float(x), float(y)
    pad_s = float(pad) * max(s, 1.0)
    hits = []
    for o in objs:
        if (
            o.x - pad_s <= px <= o.x + o.width + pad_s
            and o.y - pad_s <= py <= o.y + o.height + pad_s
        ):
            hits.append(o)
    if not hits:
        return None
    hits.sort(key=lambda o: o.width * o.height)
    return hits[0]


def _apply_transform(
    pdf_path: Path,
    page_index: int,
    index: int,
    *,
    out_path: Path,
    password: str | None,
    transform_fn,
    action: str,
) -> ObjectEditResult:
    import pypdfium2 as pdfium

    overwrite = out_path.resolve() == pdf_path.resolve()
    # Bei neuem Ziel zuerst kopieren
    if not overwrite:
        import shutil

        shutil.copy2(pdf_path, out_path)
        work = out_path
    else:
        work = pdf_path

    doc = _open_doc(work, password)
    try:
        if page_index < 0 or page_index >= len(doc):
            raise IndexError(f"Seite {page_index} existiert nicht")
        page = doc[page_index]
        objs = _top_level_objects(page)
        if index < 0 or index >= len(objs):
            raise IndexError(f"Objekt-Index {index} ungültig (n={len(objs)})")
        obj = objs[index]
        kind_before = (
            "image"
            if obj.type == pdfium.raw.FPDF_PAGEOBJ_IMAGE
            else _classify_form(page, obj)
        )
        transform_fn(obj, page)
        page.gen_content()
        doc.save(work)
        # Bounds nach Speichern neu lesen
        page2 = doc[page_index]
        objs2 = _top_level_objects(page2)
        page_h = float(page2.get_height())
        if index < len(objs2):
            final = _obj_to_doc(
                objs2[index],
                page_index=page_index,
                index=index,
                page_h=page_h,
                page=page2,
                scale=1.0,
            )
        else:
            final = DocumentObject(
                page=page_index,
                index=index,
                kind=kind_before,
                x=0,
                y=0,
                width=0,
                height=0,
            )
        return ObjectEditResult(
            out_path=Path(work),
            page=page_index,
            index=index,
            kind=final.kind or kind_before,
            action=action,
            x=final.x,
            y=final.y,
            width=final.width,
            height=final.height,
        )
    finally:
        doc.close()


def move_object(
    pdf_path: str | Path,
    page_index: int,
    index: int,
    dx: float,
    dy: float,
    *,
    scale: float = 1.0,
    out_path: str | Path | None = None,
    password: str | None = None,
) -> ObjectEditResult:
    """Verschiebt Objekt um dx/dy (Render-Pixel bei scale; +dy nach unten)."""
    from pypdfium2 import PdfMatrix

    pdf_path = Path(pdf_path)
    out_path = Path(out_path) if out_path else pdf_path
    s = float(scale) if scale else 1.0
    if s <= 0:
        s = 1.0
    dx_pt = float(dx) / s
    dy_pt = -float(dy) / s  # UI Y↓ → PDF Y↑

    def _tf(obj, _page):
        obj.transform(PdfMatrix(1, 0, 0, 1, dx_pt, dy_pt))

    return _apply_transform(
        pdf_path,
        page_index,
        index,
        out_path=out_path,
        password=password,
        transform_fn=_tf,
        action="move",
    )


def resize_object(
    pdf_path: str | Path,
    page_index: int,
    index: int,
    new_width: float,
    new_height: float,
    *,
    scale: float = 1.0,
    anchor: str = "top-left",
    out_path: str | Path | None = None,
    password: str | None = None,
) -> ObjectEditResult:
    """Skaliert Objekt auf neue Breite/Höhe (Render-Pixel bei scale)."""
    from pypdfium2 import PdfMatrix

    pdf_path = Path(pdf_path)
    out_path = Path(out_path) if out_path else pdf_path
    s = float(scale) if scale else 1.0
    if s <= 0:
        s = 1.0
    tw = max(float(new_width) / s, 1.0)
    th = max(float(new_height) / s, 1.0)

    def _tf(obj, _page):
        l, b, r, t = obj.get_bounds()
        ow = max(float(r - l), 0.5)
        oh = max(float(t - b), 0.5)
        sx = tw / ow
        sy = th / oh
        ax = (anchor or "top-left").lower()
        if ax in ("center", "centre", "mitte"):
            cx, cy = (l + r) * 0.5, (b + t) * 0.5
            obj.transform(
                PdfMatrix(sx, 0, 0, sy, cx * (1 - sx), cy * (1 - sy))
            )
        elif ax in ("bottom-left", "bl"):
            obj.transform(PdfMatrix(sx, 0, 0, sy, l * (1 - sx), b * (1 - sy)))
        else:
            # top-left: PDF top = t bleibt
            obj.transform(PdfMatrix(sx, 0, 0, sy, l * (1 - sx), t * (1 - sy)))

    return _apply_transform(
        pdf_path,
        page_index,
        index,
        out_path=out_path,
        password=password,
        transform_fn=_tf,
        action="resize",
    )


def flip_object(
    pdf_path: str | Path,
    page_index: int,
    index: int,
    *,
    horizontal: bool = False,
    vertical: bool = False,
    out_path: str | Path | None = None,
    password: str | None = None,
) -> ObjectEditResult:
    """Spiegelt Objekt horizontal und/oder vertikal um die Objektmitte."""
    from pypdfium2 import PdfMatrix

    pdf_path = Path(pdf_path)
    out_path = Path(out_path) if out_path else pdf_path
    if not horizontal and not vertical:
        raise ValueError("horizontal und/oder vertical muss True sein")

    def _tf(obj, _page):
        l, b, r, t = obj.get_bounds()
        cx = (l + r) * 0.5
        cy = (b + t) * 0.5
        if horizontal:
            obj.transform(PdfMatrix(-1, 0, 0, 1, 2 * cx, 0))
        if vertical:
            obj.transform(PdfMatrix(1, 0, 0, -1, 0, 2 * cy))

    action = "flip"
    if horizontal and vertical:
        action = "flip-hv"
    elif horizontal:
        action = "flip-h"
    else:
        action = "flip-v"
    return _apply_transform(
        pdf_path,
        page_index,
        index,
        out_path=out_path,
        password=password,
        transform_fn=_tf,
        action=action,
    )


def replace_image_object(
    pdf_path: str | Path,
    page_index: int,
    index: int,
    image: Union[str, Path, "Image.Image"],
    *,
    out_path: str | Path | None = None,
    password: str | None = None,
    keep_size: bool = True,
) -> ObjectEditResult:
    """Ersetzt Bild-XObject-Inhalt (Jpeg/Bitmap) am Index; behält Bounds."""
    import io

    import pypdfium2 as pdfium
    from PIL import Image

    pdf_path = Path(pdf_path)
    out_path = Path(out_path) if out_path else pdf_path
    if isinstance(image, Image.Image):
        img = image.convert("RGB") if image.mode not in ("RGB", "L") else image
    else:
        img = Image.open(image)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

    overwrite = out_path.resolve() == pdf_path.resolve()
    if not overwrite:
        import shutil

        shutil.copy2(pdf_path, out_path)
        work = out_path
    else:
        work = pdf_path

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90, optimize=True)
    jpeg = buf.getvalue()

    doc = _open_doc(work, password)
    try:
        page = doc[page_index]
        objs = _top_level_objects(page)
        if index < 0 or index >= len(objs):
            raise IndexError(f"Objekt-Index {index} ungültig")
        obj = objs[index]
        if obj.type != pdfium.raw.FPDF_PAGEOBJ_IMAGE:
            raise TypeError("replace_image_object nur für Bild-Objekte")
        # Bounds vor Ersetzung
        l, b, r, t = obj.get_bounds()
        try:
            obj.load_jpeg(jpeg)
        except Exception:
            # Fallback: Bitmap
            rgba = img.convert("RGBA")
            # set_bitmap expects PdfBitmap
            bitmap = pdfium.PdfBitmap.from_pil(rgba)
            obj.set_bitmap(bitmap)
        if keep_size:
            # Matrix so setzen, dass Bounds erhalten bleiben
            from pypdfium2 import PdfMatrix

            w = max(float(r - l), 1.0)
            h = max(float(t - b), 1.0)
            obj.set_matrix(PdfMatrix(w, 0, 0, h, l, b))
        page.gen_content()
        doc.save(work)
        page_h = float(page.get_height())
        final = _obj_to_doc(
            obj,
            page_index=page_index,
            index=index,
            page_h=page_h,
            page=page,
            scale=1.0,
        )
        return ObjectEditResult(
            out_path=Path(work),
            page=page_index,
            index=index,
            kind="image",
            action="replace",
            x=final.x,
            y=final.y,
            width=final.width,
            height=final.height,
        )
    finally:
        doc.close()


def set_object_rect(
    pdf_path: str | Path,
    page_index: int,
    index: int,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    scale: float = 1.0,
    out_path: str | Path | None = None,
    password: str | None = None,
) -> ObjectEditResult:
    """Setzt Objekt-Rechteck absolut (Render-Koordinaten, Y von oben)."""
    from pypdfium2 import PdfMatrix

    pdf_path = Path(pdf_path)
    out_path = Path(out_path) if out_path else pdf_path
    s = float(scale) if scale else 1.0
    if s <= 0:
        s = 1.0
    x_pt = float(x) / s
    y_top = float(y) / s
    w_pt = max(float(width) / s, 1.0)
    h_pt = max(float(height) / s, 1.0)

    def _tf(obj, page):
        page_h = float(page.get_height())
        pdf_bottom = page_h - y_top - h_pt
        obj.set_matrix(PdfMatrix(w_pt, 0, 0, h_pt, x_pt, pdf_bottom))

    return _apply_transform(
        pdf_path,
        page_index,
        index,
        out_path=out_path,
        password=password,
        transform_fn=_tf,
        action="set-rect",
    )
