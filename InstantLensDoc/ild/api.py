"""Headless InstantLens-Doc-Operationen für Python- und PowerShell-Scripting — 2.6.24.

Hyperlinks · Grafiken/Medien (Scale/Crop/Shapes/Video) · EPUB · Shared Review · Batch/eIDAS.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional, Sequence, Union

from instantlensdoc import __version__

PathLike = Union[str, Path]


def _p(path: PathLike) -> Path:
    return Path(path)


def _require_file(path: PathLike) -> Path:
    p = _p(path)
    if not p.is_file():
        raise FileNotFoundError(str(p))
    return p


def open_info(path: PathLike, *, password: str | None = None) -> dict[str, Any]:
    """PDF öffnen (Metadaten, Seitenzahl, Verschlüsselung) — kein GUI."""
    pdf = _require_file(path)
    from ild_pdf.document import PdfDocument
    from ild_pdf.security import get_encryption_info, needs_password

    encrypted = bool(needs_password(pdf))
    info: dict[str, Any] = {
        "path": str(pdf.resolve()),
        "exists": True,
        "encrypted": encrypted,
        "version": __version__,
    }
    try:
        enc = get_encryption_info(pdf, password=password)
        info["algorithm"] = enc.algorithm
        info["encrypted"] = bool(enc.encrypted)
    except Exception as e:
        info["encryption_error"] = str(e)
    try:
        with PdfDocument(pdf, password=password) as doc:
            info["pages"] = int(len(doc))
    except Exception as e:
        info["open_error"] = str(e)
        if "pages" not in info:
            info["pages"] = None
    return info


def page_count(path: PathLike, *, password: str | None = None) -> int:
    from ild_pdf.pages import page_count as _pc

    pdf = _require_file(path)
    if password:
        from ild_pdf.document import PdfDocument

        with PdfDocument(pdf, password=password) as doc:
            return int(len(doc))
    return int(_pc(pdf))


def export_page(
    path: PathLike,
    page: int,
    out: PathLike,
    *,
    dpi: int = 150,
    fmt: str | None = None,
    password: str | None = None,
) -> Path:
    """Seite N (1-basiert) als PNG/JPEG exportieren."""
    from ild_pdf.render import render_page

    pdf = _require_file(path)
    dest = _p(out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    n = int(page)
    if n < 1:
        raise ValueError("page muss ≥ 1 sein (1-basiert)")
    scale = max(72, int(dpi or 150)) / 72.0
    img = render_page(pdf, n - 1, scale=scale, password=password, use_cache=False)
    suffix = (fmt or dest.suffix.lstrip(".") or "png").lower()
    if suffix in ("jpg", "jpeg"):
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.save(dest, "JPEG", quality=90)
    else:
        img.save(dest, "PNG")
    return dest


def merge_pdfs(sources: Sequence[PathLike], dest: PathLike) -> Path:
    from ild_pdf.pages import merge_pdfs as _merge

    paths = [_require_file(s) for s in sources]
    out = _p(dest)
    out.parent.mkdir(parents=True, exist_ok=True)
    _merge(paths, out)
    return out


def split_pdf(path: PathLike, dest_dir: PathLike) -> list[Path]:
    from ild_pdf.pages import split_into_single_page_pdfs

    pdf = _require_file(path)
    out_dir = _p(dest_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    return list(split_into_single_page_pdfs(pdf, out_dir))


def rotate_page(path: PathLike, page: int, degrees: int = 90) -> Path:
    from ild_pdf.pages import rotate_page as _rot

    pdf = _require_file(path)
    idx = int(page) - 1
    if idx < 0:
        raise ValueError("page muss ≥ 1 sein")
    _rot(pdf, idx, degrees=int(degrees))
    return pdf


def ocr_image(
    path: PathLike,
    *,
    lang: str = "deu+eng",
    out_dir: PathLike | None = None,
) -> dict[str, Any]:
    from instantlensdoc.core.ocr import ocr_image as _ocr

    img = _require_file(path)
    text = _ocr(img, lang=lang)
    dest = None
    if out_dir is not None:
        d = _p(out_dir)
        d.mkdir(parents=True, exist_ok=True)
        dest = d / f"{img.stem}.ildocr.txt"
        dest.write_text(text or "", encoding="utf-8")
    return {"text": text or "", "lang": lang, "source": str(img), "sidecar": str(dest) if dest else None}


def ocr_pdf_page(
    path: PathLike,
    page: int = 1,
    *,
    lang: str = "deu+eng",
) -> dict[str, Any]:
    from instantlensdoc.core.ocr import ocr_pdf_page as _ocr

    pdf = _require_file(path)
    idx = max(0, int(page) - 1)
    text = _ocr(pdf, page_index=idx, lang=lang)
    return {"text": text or "", "lang": lang, "source": str(pdf), "page": idx + 1}


def add_redaction(
    path: PathLike,
    *,
    page: int,
    x: float,
    y: float,
    width: float,
    height: float,
) -> Path:
    """REDACTION-Rechteck ins Sidecar schreiben (Viewer-Pixel, Seite 1-basiert)."""
    from ild_pdf.annotate import Annotation, AnnotationStore, AnnotationType

    pdf = _require_file(path)
    store = AnnotationStore(pdf)
    store.add(
        Annotation(
            int(page) - 1,
            AnnotationType.REDACTION,
            float(x),
            float(y),
            width=float(width),
            height=float(height),
            text="script-redact",
        )
    )
    store.save()
    return store.sidecar_path


def apply_redactions(
    path: PathLike,
    *,
    out: PathLike | None = None,
    true_redact: bool = True,
    password: str | None = None,
) -> Path:
    from ild_pdf.annotate import AnnotationStore
    from ild_pdf.redact import apply_true_redactions, bake_redactions

    pdf = _require_file(path)
    store = AnnotationStore(pdf)
    dest = _p(out) if out else pdf.with_name(f"{pdf.stem}_redacted.pdf")
    if true_redact:
        result = apply_true_redactions(
            pdf, store, out_path=dest, password=password, strip_meta=True
        )
        return Path(result.out_path)
    return Path(bake_redactions(pdf, store, out_path=dest))


def generate_key(email: str, *, days: int | None = None) -> str:
    from instantlensdoc.license import KEY_DAYS, generate_key as _gk

    return _gk(email, days=days if days is not None else KEY_DAYS)


def verify_key(key: str) -> dict[str, Any]:
    from instantlensdoc.license import verify_key as _vk

    ok, msg, data = _vk(key)
    return {"ok": bool(ok), "message": msg, "payload": data}


def license_status(state_path: PathLike | None = None) -> dict[str, Any]:
    from instantlensdoc.license import LicenseManager

    lm = LicenseManager(path=_p(state_path) if state_path else None)
    lm.ensure_trial_started()
    st = lm.status()
    return {
        "mode": st.mode,
        "allowed": st.allowed,
        "message": st.message,
        "days_remaining": st.days_remaining,
        "email": st.email,
        "expires_at": st.expires_at.isoformat() if st.expires_at else None,
        "version": __version__,
    }


def activate_license(key: str, *, state_path: PathLike | None = None) -> dict[str, Any]:
    from instantlensdoc.license import LicenseManager

    lm = LicenseManager(path=_p(state_path) if state_path else None)
    ok, msg = lm.activate(key)
    st = lm.status()
    return {"ok": bool(ok), "message": msg, "mode": st.mode, "days_remaining": st.days_remaining}


def encrypt_pdf(
    path: PathLike,
    *,
    user_password: str,
    owner_password: str | None = None,
    out: PathLike | None = None,
    aes256: bool = True,
) -> Path:
    from ild_pdf.security import set_password

    pdf = _require_file(path)
    dest = _p(out) if out else pdf
    set_password(
        pdf,
        user_password=user_password,
        owner_password=owner_password or user_password,
        out_path=dest,
        aes256=aes256,
    )
    return dest


def remove_password(
    path: PathLike,
    password: str,
    *,
    out: PathLike | None = None,
) -> Path:
    from ild_pdf.security import remove_password as _rm

    pdf = _require_file(path)
    dest = _p(out) if out else pdf
    _rm(pdf, password, out_path=dest)
    return dest


def get_encryption_info(path: PathLike, *, password: str | None = None) -> dict[str, Any]:
    from ild_pdf.security import get_encryption_info as _gei

    pdf = _require_file(path)
    info = _gei(pdf, password=password)
    perms = None
    if info.permissions is not None:
        perms = {
            "allow_printing": info.permissions.allow_printing,
            "allow_extract": info.permissions.allow_extract,
            "allow_modify": info.permissions.allow_modify,
            "allow_modify_form": info.permissions.allow_modify_form,
            "allow_accessibility": info.permissions.allow_accessibility,
        }
    return {
        "encrypted": bool(info.encrypted),
        "algorithm": info.algorithm,
        "bits": info.bits,
        "permissions": perms,
    }


def dumps_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


def _ann_store(path: PathLike):
    from ild_pdf.annotate import AnnotationStore

    pdf = _require_file(path)
    return AnnotationStore(pdf)


def add_shape(
    path: PathLike,
    *,
    page: int,
    kind: str,
    x: float,
    y: float,
    width: float,
    height: float,
    color: str = "#2980B9",
    fill_color: str = "",
    stroke_width: float = 2.0,
    filled: bool | None = None,
) -> dict[str, Any]:
    """Form-Annotation ins Sidecar (Seite 1-basiert). kind: ellipse|rectangle|triangle|rounded_rect."""
    from ild_pdf.annotate import Annotation, AnnotationType, FILLABLE_SHAPE_TYPES

    aliases = {
        "circle": "ellipse",
        "ellipse": "ellipse",
        "oval": "ellipse",
        "rect": "rectangle",
        "rectangle": "rectangle",
        "triangle": "triangle",
        "rounded": "rounded_rect",
        "rounded_rect": "rounded_rect",
        "rundrect": "rounded_rect",
    }
    raw = aliases.get(str(kind or "").strip().lower(), str(kind or "").strip().lower())
    try:
        at = AnnotationType(raw)
    except ValueError as e:
        raise ValueError(f"Unbekannter Formtyp: {kind!r}") from e
    if at not in FILLABLE_SHAPE_TYPES:
        raise ValueError(f"Kein Formtyp: {kind!r} (ellipse/rectangle/triangle/rounded_rect)")
    fc = str(fill_color or "").strip()
    if filled is True and not fc:
        fc = color
    if filled is False:
        fc = ""
    store = _ann_store(path)
    ann = Annotation(
        int(page) - 1,
        at,
        float(x),
        float(y),
        width=float(width),
        height=float(height),
        color=color or "#2980B9",
        fill_color=fc,
        stroke_width=float(stroke_width or 2.0),
    )
    store.add(ann)
    store.save()
    return {"id": ann.id, "type": at.value, "sidecar": str(store.sidecar_path)}


def add_stamp(
    path: PathLike,
    *,
    page: int,
    text: str,
    x: float = 72.0,
    y: float = 72.0,
    color: str = "#C0392B",
    include_date: bool = False,
    width: float = 140.0,
    height: float = 48.0,
) -> dict[str, Any]:
    from ild_pdf.annotate import Annotation, AnnotationStore, AnnotationType, stamp_text_for_label

    pdf = _require_file(path)
    store = AnnotationStore(pdf)
    label = stamp_text_for_label(text, include_date=include_date)
    ann = Annotation(
        int(page) - 1,
        AnnotationType.STAMP,
        float(x),
        float(y),
        width=float(width),
        height=float(height),
        text=label,
        color=color or "#C0392B",
    )
    store.add(ann)
    store.save()
    return {"id": ann.id, "text": ann.text, "sidecar": str(store.sidecar_path)}


def add_ink(
    path: PathLike,
    *,
    page: int,
    points: Sequence[Sequence[float]],
    color: str = "#2980B9",
    stroke_width: float = 2.0,
) -> dict[str, Any]:
    from ild_pdf.annotate import Annotation, AnnotationStore

    pdf = _require_file(path)
    store = AnnotationStore(pdf)
    ann = Annotation.from_ink_points(
        int(page) - 1, points, color=color, stroke_width=float(stroke_width or 2.0)
    )
    store.add(ann)
    store.save()
    return {"id": ann.id, "type": "ink", "sidecar": str(store.sidecar_path)}


def highlight_paragraphs(
    path: PathLike,
    *,
    page: int,
    x: float,
    y: float,
    width: float,
    height: float,
    color: str = "#FFFF00",
    scale: float = 1.0,
) -> dict[str, Any]:
    """Ganze Absätze unter dem Rechteck als Highlight (Seite 1-basiert)."""
    from ild_pdf.annotate import Annotation, AnnotationStore, AnnotationType
    from ild_pdf.overlay import selection_to_paragraph_highlight_rects

    pdf = _require_file(path)
    store = AnnotationStore(pdf)
    x1 = float(x) + float(width)
    y1 = float(y) + float(height)
    rects, text = selection_to_paragraph_highlight_rects(
        pdf, int(page) - 1, float(x), float(y), x1, y1, scale=float(scale or 1.0)
    )
    ids: list[str] = []
    with store.atomic():
        for r in rects:
            ann = Annotation(
                int(page) - 1,
                AnnotationType.HIGHLIGHT,
                float(r.x),
                float(r.y),
                width=max(float(r.width), 4.0),
                height=max(float(r.height), 6.0),
                color=color or "#FFFF00",
                text=r.text or "",
            )
            store.add(ann)
            ids.append(ann.id)
    store.save()
    return {"count": len(ids), "ids": ids, "text": text, "sidecar": str(store.sidecar_path)}


def list_stamps(*, custom_path: PathLike | None = None) -> list[dict[str, Any]]:
    from ild_pdf.annotate import list_definable_stamps

    return list_definable_stamps(path=_p(custom_path) if custom_path else None)


def add_custom_stamp_def(
    label: str, *, color: str = "#C0392B", custom_path: PathLike | None = None
) -> dict[str, Any]:
    from ild_pdf.annotate import add_custom_stamp as _add

    return _add(label, color=color, path=_p(custom_path) if custom_path else None)


def list_style_presets() -> list[dict[str, Any]]:
    from ild_pdf.auto_format import list_style_presets as _list

    return _list()


def auto_format_text(text: str, *, preset: str = "default") -> dict[str, Any]:
    from ild_pdf.auto_format import auto_format_text as _fmt

    return _fmt(text, preset=preset).to_dict()


def auto_format_pdf(
    path: PathLike,
    *,
    out: PathLike | None = None,
    max_level: int = 3,
    update_toc: bool = True,
    password: str | None = None,
) -> dict[str, Any]:
    from ild_pdf.auto_format import auto_format_pdf as _fmt

    pdf = _require_file(path)
    return _fmt(
        pdf,
        out_path=_p(out) if out else None,
        max_level=int(max_level or 3),
        update_toc=bool(update_toc),
        password=password,
    ).to_dict()


def generate_toc(
    path: PathLike | None = None,
    *,
    text: str | None = None,
    out: PathLike | None = None,
    max_level: int = 3,
    write: bool = True,
    password: str | None = None,
) -> dict[str, Any]:
    """TOC aus Text (Markdown) oder PDF (Outline)."""
    from ild_pdf.auto_format import (
        generate_toc_for_pdf,
        generate_toc_markdown,
        insert_toc_into_text,
    )

    if text is not None:
        toc = generate_toc_markdown(text, max_level=int(max_level or 3))
        merged = insert_toc_into_text(text, max_level=int(max_level or 3))
        return {"toc": toc, "text": merged, "count": toc.count("\n- ")}
    if path is None:
        raise ValueError("path oder text erforderlich")
    pdf = _require_file(path)
    result = generate_toc_for_pdf(
        pdf,
        out_path=_p(out) if out else None,
        max_level=int(max_level or 3),
        write=bool(write),
        password=password,
    )
    return result.to_dict()


def list_system_fonts(*, include_files: bool = False) -> list[str]:
    from ild_pdf.auto_format import list_system_fonts as _fonts

    return _fonts(include_files=include_files)


def find_replace(
    *,
    text: str | None = None,
    path: PathLike | None = None,
    find: str,
    replace: str,
    case_sensitive: bool = False,
    count: int = 0,
    max_replacements: int = 50,
    password: str | None = None,
) -> dict[str, Any]:
    """Suchen/Ersetzen in Text oder PDF."""
    from ild_pdf.auto_format import find_replace_in_pdf_text, find_replace_text

    if text is not None:
        new_text, n = find_replace_text(
            text, find, replace, case_sensitive=case_sensitive, count=count
        )
        return {"count": n, "text": new_text}
    if path is None:
        raise ValueError("path oder text erforderlich")
    pdf = _require_file(path)
    return find_replace_in_pdf_text(
        pdf,
        find,
        replace,
        case_sensitive=case_sensitive,
        max_replacements=int(max_replacements or 50),
        password=password,
    )


def outline_summary(path: PathLike) -> list[dict[str, Any]]:
    from ild_pdf.auto_format import outline_summary as _sum

    return _sum(_require_file(path))


def list_page_formats(*, unit: str = "mm") -> list[dict[str, Any]]:
    """Seitenformate-Presets (US Letter, DIN-A, Buchformate) — 2.6.12."""
    from ild_pdf.page_layout import list_page_format_presets

    return list_page_format_presets(unit=unit)


def resolve_page_format(name: str) -> dict[str, float]:
    from ild_pdf.page_layout import resolve_page_format as _resolve
    from ild_pdf.pages import pt_to_mm

    w, h = _resolve(name)
    return {
        "name": name,
        "width_pt": float(w),
        "height_pt": float(h),
        "width_mm": round(pt_to_mm(w), 1),
        "height_mm": round(pt_to_mm(h), 1),
    }


def set_page_format(
    path: PathLike,
    name: str,
    *,
    page: int = 1,
    all_pages: bool = False,
) -> dict[str, Any]:
    """Seitenformat-Preset auf PDF anwenden (1-basierte Seite)."""
    from ild_pdf.page_layout import resolve_page_format as _resolve
    from ild_pdf.pages import set_page_size

    pdf = _require_file(path)
    w, h = _resolve(name)
    set_page_size(pdf, int(page) - 1, float(w), float(h), all_pages=bool(all_pages))
    return {"path": str(pdf), "format": name, "width_pt": w, "height_pt": h, "all_pages": bool(all_pages)}


def apply_header_footer(
    path: PathLike,
    *,
    out: PathLike | None = None,
    header: str = "{title}",
    footer: str = "{author} — {n} / {total}",
    include_page_numbers: bool = True,
    page_template: str = "{n} / {total}",
    title: str | None = None,
    author: str | None = None,
    creator: str | None = None,
) -> dict[str, Any]:
    """Kopf-/Fußzeile mit Titel/Ersteller bakken — 2.6.12."""
    from ild_pdf.page_layout import apply_header_footer_with_meta

    pdf = _require_file(path)
    dest = apply_header_footer_with_meta(
        pdf,
        out_path=_p(out) if out else None,
        header_text=header,
        footer_text=footer,
        include_page_numbers=include_page_numbers,
        page_number_template=page_template,
        title=title,
        author=author,
        creator=creator,
    )
    return {"path": str(dest), "header": header, "footer": footer, "author": author, "title": title}


def apply_paragraph_format(
    *,
    text: str,
    alignment: str | None = None,
    line_spacing: float | None = None,
    space_before_pt: float | None = None,
    space_after_pt: float | None = None,
    paragraph_index: int | None = None,
    style_id: str | None = None,
) -> dict[str, Any]:
    """Absatzausrichtung/Abstände (Marker) bzw. Style-Defaults — 2.6.12."""
    from ild_pdf.page_layout import (
        apply_paragraph_format as _apply,
        apply_style_paragraph_defaults,
        parse_paragraph_format,
    )

    if style_id:
        new_text = apply_style_paragraph_defaults(text, style_id=style_id)
    else:
        new_text = _apply(
            text,
            alignment=alignment,
            line_spacing=line_spacing,
            space_before_pt=space_before_pt,
            space_after_pt=space_after_pt,
            paragraph_index=paragraph_index,
        )
    fmt = parse_paragraph_format(new_text.split("\n\n")[0] if new_text else "")
    return {"text": new_text, "format": fmt.to_dict()}


def list_paragraph_styles() -> list[dict[str, Any]]:
    from ild_pdf.page_layout import list_paragraph_formats_from_styles

    return list_paragraph_formats_from_styles()


def ruler_ticks(
    length_pt: float, *, unit: str = "mm", major_every: int = 10
) -> list[dict[str, Any]]:
    from ild_pdf.page_layout import ruler_ticks as _ticks

    return _ticks(float(length_pt), unit=unit, major_every=int(major_every))


def grid_lines(
    width_pt: float, height_pt: float, *, spacing_mm: float = 5.0
) -> dict[str, list[float]]:
    from ild_pdf.page_layout import grid_lines as _grid

    return _grid(float(width_pt), float(height_pt), spacing_mm=float(spacing_mm))


# --- Frames / Musterseiten / Satzspiegel — 2.6.12 ---


def satzspiegel(
    format_name: str = "A4",
    *,
    columns: int = 1,
    gutter_mm: float = 5.0,
) -> dict[str, Any]:
    """Satzspiegel (Type Area) für Seitenformat-Preset — 2.6.12."""
    from ild_pdf.page_layout import satzspiegel_for_format

    return satzspiegel_for_format(
        format_name, columns=int(columns), gutter_mm=float(gutter_mm)
    ).to_dict()


def list_satzspiegel(*, columns: int = 1) -> list[dict[str, Any]]:
    from ild_pdf.page_layout import list_satzspiegel_presets

    return list_satzspiegel_presets(columns=int(columns))


def list_master_pages() -> list[dict[str, Any]]:
    """Musterseiten-Presets (Kopf/Fuß + Seitenzahlen + Satzspiegel) — 2.6.12."""
    from ild_pdf.page_layout import list_master_presets

    return list_master_presets()


def apply_master_page(
    path: PathLike,
    master: str = "Standard",
    *,
    out: PathLike | None = None,
    title: str | None = None,
    author: str | None = None,
    creator: str | None = None,
    start_page: int | None = None,
) -> dict[str, Any]:
    """Musterseite auf PDF bakken (HF + Seitenzahlen über Seiten) — 2.6.12."""
    from ild_pdf.page_layout import apply_master_page as _apply
    from ild_pdf.page_layout import master_page_from_preset

    pdf = _require_file(path)
    mp = master_page_from_preset(master)
    if start_page is not None:
        mp.start_page = max(1, int(start_page))
    dest = _apply(
        pdf,
        mp,
        out_path=_p(out) if out else None,
        title=title,
        author=author,
        creator=creator,
    )
    return {
        "path": str(dest),
        "master": mp.name,
        "header": mp.header_text,
        "footer": mp.footer_text,
        "satzspiegel": mp.satzspiegel.to_dict(),
        "title": title,
        "author": author,
    }


def new_layout(
    *,
    page_width: float = 595.0,
    page_height: float = 842.0,
    format_name: str | None = None,
) -> dict[str, Any]:
    """Leeres LayoutDocument (Frames) — 2.6.12."""
    from instantlensdoc.core.layout import LayoutDocument
    from ild_pdf.page_layout import resolve_page_format

    w, h = float(page_width), float(page_height)
    if format_name:
        w, h = resolve_page_format(format_name)
    doc = LayoutDocument(page_width=w, page_height=h)
    return doc.to_dict()


def layout_add_text_frame(
    layout: dict[str, Any] | None = None,
    *,
    text: str = "",
    x: float = 40,
    y: float = 40,
    width: float = 515,
    height: float = 200,
    font_size: int = 12,
    page: int = 0,
    column: int = 0,
    path: PathLike | None = None,
) -> dict[str, Any]:
    """Textrahmen hinzufügen (Layout-Dict oder JSON-Pfad) — 2.6.12."""
    from instantlensdoc.core.layout import LayoutDocument

    doc = _load_layout(layout, path)
    fr = doc.add_text_frame(
        text=text,
        x=float(x),
        y=float(y),
        width=float(width),
        height=float(height),
        font_size=int(font_size),
        page=int(page),
        column=int(column),
    )
    if path:
        doc.save(path)
    return {"layout": doc.to_dict(), "frame": fr.to_dict()}


def layout_add_image_frame(
    layout: dict[str, Any] | None = None,
    *,
    image: str,
    x: float = 40,
    y: float = 300,
    width: float = 200,
    height: float = 150,
    page: int = 0,
    path: PathLike | None = None,
) -> dict[str, Any]:
    from instantlensdoc.core.layout import LayoutDocument

    doc = _load_layout(layout, path)
    fr = doc.add_image(
        image, x=float(x), y=float(y), width=float(width), height=float(height), page=int(page)
    )
    if path:
        doc.save(path)
    return {"layout": doc.to_dict(), "frame": fr.to_dict()}


def layout_move_frame(
    frame_id: str,
    x: float,
    y: float,
    *,
    layout: dict[str, Any] | None = None,
    path: PathLike | None = None,
) -> dict[str, Any]:
    """Rahmen verschieben — 2.6.12."""
    doc = _load_layout(layout, path)
    fr = doc.move_frame(frame_id, float(x), float(y))
    if path:
        doc.save(path)
    return {"layout": doc.to_dict(), "frame": fr.to_dict()}


def layout_resize_frame(
    frame_id: str,
    width: float,
    height: float,
    *,
    layout: dict[str, Any] | None = None,
    path: PathLike | None = None,
) -> dict[str, Any]:
    """Rahmen skalieren — 2.6.12."""
    doc = _load_layout(layout, path)
    fr = doc.resize_frame(frame_id, float(width), float(height))
    if path:
        doc.save(path)
    return {"layout": doc.to_dict(), "frame": fr.to_dict()}


def layout_link_frames(
    from_id: str,
    to_id: str,
    *,
    layout: dict[str, Any] | None = None,
    path: PathLike | None = None,
) -> dict[str, Any]:
    """Textrahmen verketten (Overflow) — 2.6.12."""
    doc = _load_layout(layout, path)
    doc.link_frames(from_id, to_id)
    if path:
        doc.save(path)
    return {"layout": doc.to_dict(), "from": from_id, "to": to_id}


def layout_flow_text(
    text: str,
    start_id: str | None = None,
    *,
    layout: dict[str, Any] | None = None,
    path: PathLike | None = None,
    columns: int | None = None,
    pages: int | None = None,
    around_wrap: bool = False,
) -> dict[str, Any]:
    """
    Text in verkettete Rahmen fließen lassen.
    Optional: Spalten- oder Seitenkette neu anlegen; Textumfluss um Bildrahmen (2.6.13).
    """
    doc = _load_layout(layout, path)
    if columns and int(columns) > 0:
        frames = doc.create_column_chain(columns=int(columns))
        start = frames[0]
    elif pages and int(pages) > 1:
        frames = doc.create_page_chain(pages=int(pages))
        start = frames[0]
    elif start_id:
        start = doc.frame_by_id(start_id)
        if start is None:
            raise KeyError(f"Rahmen nicht gefunden: {start_id}")
    elif doc.text_frames:
        start = doc.text_frames[0]
    else:
        start = doc.add_text_frame()
    filled = doc.flow_text_chain(text, start, around_wrap=bool(around_wrap))
    overflow = filled.pop("__overflow__", "")
    if path:
        doc.save(path)
    return {
        "layout": doc.to_dict(),
        "filled": filled,
        "overflow": overflow,
        "chain": doc.chain_ids(start.id),
        "obstacles": doc.wrap_obstacles() if around_wrap else [],
    }


def layout_list_frames(
    *,
    layout: dict[str, Any] | None = None,
    path: PathLike | None = None,
) -> list[dict[str, Any]]:
    doc = _load_layout(layout, path)
    return doc.list_frames()


# --- Typografie / Textumfluss / Silbentrennung — 2.6.13 ---


def apply_typography(
    *,
    text: str,
    tracking: float | None = None,
    kerning: float | None = None,
    leading: float | None = None,
    drop_cap_lines: int | None = None,
    drop_cap_chars: int | None = None,
    char_style_id: str | None = None,
    alignment: str | None = None,
    line_spacing: float | None = None,
    paragraph_index: int | None = None,
) -> dict[str, Any]:
    """Tracking/Kerning/Leading/Drop-Cap/Zeichenstil auf Absätze — 2.6.13."""
    from ild_pdf.typography import apply_typography as _apply, parse_typography

    new_text = _apply(
        text,
        tracking=tracking,
        kerning=kerning,
        leading=leading,
        drop_cap_lines=drop_cap_lines,
        drop_cap_chars=drop_cap_chars,
        char_style_id=char_style_id,
        alignment=alignment,
        line_spacing=line_spacing,
        paragraph_index=paragraph_index,
    )
    first = new_text.split("\n\n")[0] if new_text else ""
    return {"text": new_text, "typography": parse_typography(first).to_dict()}


def apply_drop_cap(
    text: str,
    *,
    lines: int = 3,
    chars: int = 1,
    paragraph_index: int = 0,
) -> dict[str, Any]:
    """Initial/Drop Cap auf Absatz — 2.6.13."""
    from ild_pdf.typography import apply_drop_cap as _dc, parse_typography

    new_text = _dc(
        text, lines=int(lines), chars=int(chars), paragraph_index=int(paragraph_index)
    )
    first = new_text.split("\n\n")[0] if new_text else ""
    return {"text": new_text, "typography": parse_typography(first).to_dict()}


def list_character_styles() -> list[dict[str, Any]]:
    from ild_pdf.typography import list_character_styles as _list

    return _list()


def list_typography_styles() -> list[dict[str, Any]]:
    """Absatzstile inkl. Typografie-Defaults (Tracking/Leading) — 2.6.13."""
    from ild_pdf.typography import paragraph_styles_with_typography

    return paragraph_styles_with_typography()


def hyphenate(
    text: str,
    *,
    lang: str = "de",
) -> dict[str, Any]:
    """Intelligente Silbentrennung (Soft-Hyphens); DE/EN + Hook — 2.6.13."""
    from ild_pdf.typography import hyphenate_text

    return hyphenate_text(text, lang=lang)


def list_hyphenation_languages() -> list[str]:
    from ild_pdf.typography import list_hyphenation_languages as _list

    return _list()


def layout_set_text_wrap(
    frame_id: str,
    mode: str = "bounding_box",
    *,
    padding: float | None = None,
    layout: dict[str, Any] | None = None,
    path: PathLike | None = None,
) -> dict[str, Any]:
    """Textumfluss um Bild-/Formrahmen — 2.6.13."""
    doc = _load_layout(layout, path)
    fr = doc.set_text_wrap(frame_id, mode, padding=padding)
    if path:
        doc.save(path)
    return {"layout": doc.to_dict(), "frame": fr.to_dict()}


def layout_flow_text_wrap(
    text: str,
    start_id: str | None = None,
    *,
    layout: dict[str, Any] | None = None,
    path: PathLike | None = None,
) -> dict[str, Any]:
    """Text in Rahmen fließen lassen, um Bildrahmen herum — 2.6.13."""
    doc = _load_layout(layout, path)
    if start_id:
        start = doc.frame_by_id(start_id)
        if start is None:
            raise KeyError(f"Rahmen nicht gefunden: {start_id}")
    elif doc.text_frames:
        start = doc.text_frames[0]
    else:
        start = doc.add_text_frame()
    filled = doc.flow_text_chain(text, start, around_wrap=True)
    overflow = filled.pop("__overflow__", "")
    if path:
        doc.save(path)
    return {
        "layout": doc.to_dict(),
        "filled": filled,
        "overflow": overflow,
        "chain": doc.chain_ids(start.id),
        "obstacles": doc.wrap_obstacles(),
    }


# --- Tabellen / Office-I/O — 2.6.14 ---


def create_table(
    rows: int = 3,
    cols: int = 3,
    *,
    header: bool = True,
    data: list[list[Any]] | None = None,
    table_id: str = "t1",
    align: str = "",
    border: bool = True,
    style: str = "default",
    as_markdown: bool = True,
) -> dict[str, Any]:
    """Tabelle erstellen (Markdown + Struktur) — 2.6.14."""
    from ild_pdf.tables import create_table as _ct, table_to_html, table_to_markdown

    t = _ct(
        rows,
        cols,
        header=header,
        data=data,
        table_id=table_id,
        align=align,
        border=border,
        style=style,
    )
    out = t.to_dict()
    out["markdown"] = table_to_markdown(t)
    out["html"] = table_to_html(t)
    if as_markdown:
        out["text"] = out["markdown"]
    return out


def format_table(
    *,
    text: str | None = None,
    table: dict[str, Any] | None = None,
    align: str | None = None,
    border: bool | None = None,
    header: bool | None = None,
    header_bold: bool | None = None,
    style: str | None = None,
) -> dict[str, Any]:
    """Tabelle formatieren — 2.6.14."""
    from ild_pdf.tables import (
        DocumentTable,
        TableFormat,
        format_table as _ft,
        parse_table,
        table_to_html,
        table_to_markdown,
    )

    if text is not None:
        src = parse_table(text)
    elif table is not None:
        fmt = table.get("format") or {}
        src = DocumentTable(
            cells=list(table.get("cells") or []),
            format=TableFormat(
                header=bool(fmt.get("header", True)),
                border=bool(fmt.get("border", True)),
                align=str(fmt.get("align") or ""),
                header_bold=bool(fmt.get("header_bold", True)),
                style=str(fmt.get("style") or "default"),
            ),
            table_id=str(table.get("id") or "t1"),
        )
    else:
        raise ValueError("text oder table erforderlich")
    t = _ft(
        src,
        align=align,
        border=border,
        header=header,
        header_bold=header_bold,
        style=style,
    )
    out = t.to_dict()
    out["markdown"] = table_to_markdown(t)
    out["html"] = table_to_html(t)
    out["text"] = out["markdown"]
    return out


def sort_table(
    *,
    text: str | None = None,
    table: dict[str, Any] | None = None,
    column: int = 0,
    reverse: bool = False,
    numeric: bool = True,
) -> dict[str, Any]:
    """Tabelle nach Spalte sortieren — 2.6.14."""
    from ild_pdf.tables import (
        DocumentTable,
        TableFormat,
        parse_table,
        sort_table as _st,
        table_to_html,
        table_to_markdown,
    )

    if text is not None:
        src = parse_table(text)
    elif table is not None:
        fmt = table.get("format") or {}
        src = DocumentTable(
            cells=list(table.get("cells") or []),
            format=TableFormat(
                header=bool(fmt.get("header", True)),
                border=bool(fmt.get("border", True)),
                align=str(fmt.get("align") or ""),
                style=str(fmt.get("style") or "default"),
            ),
            table_id=str(table.get("id") or "t1"),
        )
    else:
        raise ValueError("text oder table erforderlich")
    t = _st(src, column=int(column), reverse=bool(reverse), numeric=bool(numeric))
    out = t.to_dict()
    out["markdown"] = table_to_markdown(t)
    out["html"] = table_to_html(t)
    out["text"] = out["markdown"]
    return out


def import_table_csv(
    path: PathLike,
    *,
    delimiter: str | None = None,
    encoding: str = "utf-8-sig",
    header: bool = True,
    table_id: str = "csv1",
) -> dict[str, Any]:
    """CSV in Tabelle importieren — 2.6.14."""
    from ild_pdf.tables import import_csv, table_to_html, table_to_markdown

    t = import_csv(path, delimiter=delimiter, encoding=encoding, header=header, table_id=table_id)
    out = t.to_dict()
    out["markdown"] = table_to_markdown(t)
    out["html"] = table_to_html(t)
    out["text"] = out["markdown"]
    return out


def import_table_xlsx(
    path: PathLike,
    *,
    sheet: str | int | None = 0,
    header: bool = True,
    table_id: str = "xlsx1",
) -> dict[str, Any]:
    """Excel/.xlsx in Tabelle importieren — 2.6.14."""
    from ild_pdf.tables import import_xlsx, table_to_html, table_to_markdown

    t = import_xlsx(path, sheet=sheet, header=header, table_id=table_id)
    out = t.to_dict()
    out["markdown"] = table_to_markdown(t)
    out["html"] = table_to_html(t)
    out["text"] = out["markdown"]
    return out


def export_table(
    *,
    text: str | None = None,
    table: dict[str, Any] | None = None,
    out: PathLike,
    fmt: str | None = None,
) -> dict[str, Any]:
    """Tabelle als CSV/XLSX/Markdown/HTML speichern — 2.6.14."""
    from ild_pdf.tables import (
        DocumentTable,
        TableFormat,
        export_table_csv,
        export_table_xlsx,
        parse_table,
        table_to_html,
        table_to_markdown,
    )

    dest = _p(out)
    if text is not None:
        src = parse_table(text)
    elif table is not None:
        fmt_d = table.get("format") or {}
        src = DocumentTable(
            cells=list(table.get("cells") or []),
            format=TableFormat(
                header=bool(fmt_d.get("header", True)),
                border=bool(fmt_d.get("border", True)),
                align=str(fmt_d.get("align") or ""),
                style=str(fmt_d.get("style") or "default"),
            ),
            table_id=str(table.get("id") or "t1"),
        )
    else:
        raise ValueError("text oder table erforderlich")
    f = (fmt or dest.suffix.lstrip(".")).lower()
    if f in ("csv",):
        export_table_csv(src, dest)
    elif f in ("xlsx", "xls"):
        export_table_xlsx(src, dest)
    elif f in ("html", "htm"):
        dest.write_text(table_to_html(src), encoding="utf-8")
    elif f in ("md", "markdown", "txt"):
        dest.write_text(table_to_markdown(src), encoding="utf-8")
    else:
        raise ValueError(f"Unbekanntes Tabellen-Export-Format: {f}")
    return {"path": str(dest), "format": f, "rows": src.rows, "cols": src.cols}


def list_table_styles() -> list[dict[str, Any]]:
    from ild_pdf.tables import list_table_styles as _list

    return _list()


def save_document(
    text: str,
    path: PathLike,
    *,
    fmt: str | None = None,
    title: str = "InstantLens Doc",
) -> dict[str, Any]:
    """Dokument speichern/exportieren (docx/xlsx/pdf/txt/rtf/html/jpg/epub) — 2.6.24."""
    from instantlensdoc.core.export import export_document

    dest = export_document(text, path, fmt=fmt, title=title)
    return {"path": str(dest), "format": (fmt or dest.suffix.lstrip(".")).lower()}


def export_document_fmt(
    text: str,
    path: PathLike,
    *,
    fmt: str | None = None,
    title: str = "InstantLens Doc",
) -> dict[str, Any]:
    """Alias für save_document — 2.6.14."""
    return save_document(text, path, fmt=fmt, title=title)


def import_document(path: PathLike) -> dict[str, Any]:
    """Dokument importieren → Text (+ Meta/Tabelle) — 2.6.14."""
    from instantlensdoc.core.export import import_document_text

    return import_document_text(path)


def list_io_formats() -> dict[str, list[dict[str, str]]]:
    """Unterstützte Import-/Export-Formate — 2.6.14."""
    from instantlensdoc.core.export import list_export_formats, list_import_formats

    return {"export": list_export_formats(), "import": list_import_formats()}


# --- OCR → Word-Suite Handoff — 2.6.15 ---


def ocr_to_word_suite(
    source: PathLike | None = None,
    *,
    text: str | None = None,
    page: int = 1,
    lang: str = "deu+eng",
    auto_format: bool = True,
    title: str | None = None,
    prefer_layout: bool = True,
    out: PathLike | None = None,
) -> dict[str, Any]:
    """OCR/Layout-OCR/ildocr-Sidecar → editierbares Word-Suite-Dokument — 2.6.15."""
    from instantlensdoc.core.ocr_word_suite import handoff_ocr_to_word_suite

    doc = handoff_ocr_to_word_suite(
        source,
        text=text,
        page=page,
        lang=lang,
        auto_format=auto_format,
        title=title,
        prefer_layout=prefer_layout,
        out=out,
    )
    return doc.to_dict()


def import_ildocr(
    path: PathLike,
    *,
    auto_format: bool = True,
    title: str | None = None,
    out: PathLike | None = None,
) -> dict[str, Any]:
    """``*.ildocr.txt`` / hOCR / TSV als Word-Suite-Dokument importieren — 2.6.15."""
    from instantlensdoc.core.ocr_word_suite import import_ildocr_sidecar

    doc = import_ildocr_sidecar(path, auto_format=auto_format, title=title)
    if out is not None:
        dest = _p(out)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(doc.text or "", encoding="utf-8")
        doc.meta["out"] = str(dest)
    return doc.to_dict()


def handoff_ocr_to_word_suite(
    source: PathLike | None = None,
    *,
    text: str | None = None,
    page: int = 1,
    lang: str = "deu+eng",
    auto_format: bool = True,
    title: str | None = None,
    prefer_layout: bool = True,
    out: PathLike | None = None,
) -> dict[str, Any]:
    """Alias für ocr_to_word_suite — 2.6.15."""
    return ocr_to_word_suite(
        source,
        text=text,
        page=page,
        lang=lang,
        auto_format=auto_format,
        title=title,
        prefer_layout=prefer_layout,
        out=out,
    )


def list_ki_wizards() -> list[dict[str, Any]]:
    """Isolierte KI-Dokument-Wizards auflisten — 2.6.16."""
    from instantlensdoc.core.ki_wizards import list_ki_wizards as _list

    return _list()


def generate_ki_document(
    kind: str,
    *,
    fields: dict[str, Any] | None = None,
    company: dict[str, Any] | None = None,
    company_mode: bool | None = None,
    title: str | None = None,
    use_llm: bool = False,
    out: PathLike | None = None,
) -> dict[str, Any]:
    """KI-Wizard: Formular/Anschreiben/Kaufvertrag/Rechnung → editierbares Dokument — 2.6.16.

    Lokal templatebasiert; optionaler LLM-Hook nur bei ``use_llm=True``
    (kein freier Chat).
    """
    from instantlensdoc.core.ki_wizards import generate_ki_document as _gen

    doc = _gen(
        kind,
        fields=fields,
        company=company,
        company_mode=company_mode,
        title=title,
        use_llm=use_llm,
        out=out,
    )
    return doc.to_dict()


def run_ki_wizard(
    kind: str,
    *,
    fields: dict[str, Any] | None = None,
    company: dict[str, Any] | None = None,
    company_mode: bool | None = None,
    title: str | None = None,
    use_llm: bool = False,
    out: PathLike | None = None,
) -> dict[str, Any]:
    """Alias für generate_ki_document — 2.6.16."""
    return generate_ki_document(
        kind,
        fields=fields,
        company=company,
        company_mode=company_mode,
        title=title,
        use_llm=use_llm,
        out=out,
    )


def list_ui_langs() -> list[dict[str, Any]]:
    """Unterstützte UI-Sprachen (DE/EN/FR/RU/ES/ZH/PT/AR/IT) — 2.6.19."""
    from instantlensdoc.core.i18n import (
        SUPPORTED_LANGS,
        is_rtl,
        lang_native_name,
        tr,
    )

    return [
        {
            "code": code,
            "native": lang_native_name(code),
            "label": tr(f"lang_{code}", lang="de"),
            "rtl": is_rtl(code),
        }
        for code in SUPPORTED_LANGS
    ]


def get_ui_lang() -> str:
    """Aktuelle UI-Sprache (Settings) — 2.6.19."""
    from instantlensdoc.core.app_settings import get_ui_lang as _get

    return str(_get())


def set_ui_lang(lang: str) -> str:
    """UI-Sprache setzen und persistieren — 2.6.19."""
    from instantlensdoc.core.app_settings import set_ui_lang as _set
    from instantlensdoc.core.i18n import normalize_lang, set_lang

    code = normalize_lang(lang)
    _set(code)
    set_lang(code)
    return code


def tr(key: str, *, lang: str | None = None) -> str:
    """UI-String übersetzen — 2.6.19."""
    from instantlensdoc.core.i18n import tr as _tr

    return _tr(key, lang=lang)  # type: ignore[arg-type]


def ocr_handwriting(
    path: PathLike,
    *,
    lang: str = "deu+eng",
    psm: int | str = 6,
    out: PathLike | None = None,
) -> dict[str, Any]:
    """Basis-Handschriftenerkennung (Tesseract PSM) — 2.6.19."""
    from instantlensdoc.core.ocr import ocr_image_handwriting, normalize_handwriting_psm

    src = _require_file(path)
    psm_n = normalize_handwriting_psm(psm)
    text = ocr_image_handwriting(src, lang=lang, psm=psm_n)
    result: dict[str, Any] = {
        "path": str(src.resolve()),
        "lang": lang,
        "psm": psm_n,
        "text": text,
        "handwriting": True,
        "version": __version__,
    }
    if out is not None:
        dest = _p(out)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text or "", encoding="utf-8")
        result["out"] = str(dest.resolve())
    return result


def list_color_palettes() -> list[dict[str, Any]]:
    """Eingebaute RGB/CMYK/Spot-Paletten — 2.6.19."""
    from ild_pdf.print_prep import list_palettes

    return list_palettes()


def convert_color_api(
    *,
    rgb: Sequence[float] | None = None,
    cmyk: Sequence[float] | None = None,
    hex_color: str | None = None,
    to: str = "cmyk",
) -> dict[str, Any]:
    """RGB↔CMYK-Konvertierung — 2.6.19."""
    from ild_pdf.print_prep import convert_color

    mode = (to or "cmyk").strip().lower()
    if mode not in ("rgb", "cmyk"):
        mode = "cmyk"
    return convert_color(rgb=rgb, cmyk=cmyk, hex_color=hex_color, to=mode)  # type: ignore[arg-type]


def list_bleed_presets() -> list[dict[str, Any]]:
    """Anschnitt-Presets (mm) — 2.6.19."""
    from ild_pdf.print_prep import list_bleed_presets as _list

    return _list()


def apply_bleed(
    path: PathLike,
    *,
    bleed_mm: float | None = None,
    preset: str | None = None,
    out: PathLike | None = None,
    all_pages: bool = True,
) -> dict[str, Any]:
    """Bleed/Anschnitt auf PDF anwenden — 2.6.19."""
    from ild_pdf.print_prep import BleedSettings, apply_bleed_boxes, get_bleed_info

    src = _require_file(path)
    if preset:
        settings = BleedSettings.from_preset(preset)
    elif bleed_mm is not None:
        settings = BleedSettings.uniform(float(bleed_mm))
    else:
        settings = BleedSettings.from_preset("standard")
    dest = apply_bleed_boxes(src, settings, out=out, all_pages=all_pages)
    info = get_bleed_info(dest, 0)
    return {
        "out": str(Path(dest).resolve()),
        "bleed": settings.to_dict(),
        "page1": info,
        "version": __version__,
    }


def get_bleed(path: PathLike, page: int = 1) -> dict[str, Any]:
    """Bleed/Trim-Info einer Seite — 2.6.19."""
    from ild_pdf.print_prep import get_bleed_info

    src = _require_file(path)
    return get_bleed_info(src, max(0, int(page) - 1))


def list_doc_layers() -> list[dict[str, Any]]:
    """Dokument-Ebenen Hintergrund/Bilder/Text — 2.6.19."""
    from ild_pdf.print_prep import list_layers

    return list_layers()


def layout_set_layer(
    frame_id: str,
    layer: str,
    *,
    layout: dict[str, Any] | None = None,
    path: PathLike | None = None,
    out: PathLike | None = None,
) -> dict[str, Any]:
    """Rahmen einer Ebene zuordnen — 2.6.19."""
    doc = _load_layout(layout, path)
    frame = doc.set_frame_layer(frame_id, layer)
    result: dict[str, Any] = {
        "frame": frame.to_dict(),
        "layers": doc.frames_by_layer(),
        "version": __version__,
    }
    if out is not None:
        dest = doc.save(_p(out))
        result["out"] = str(Path(dest).resolve())
    elif path is not None:
        dest = doc.save(_p(path))
        result["out"] = str(Path(dest).resolve())
    else:
        result["layout"] = doc.to_dict()
    return result


def layout_layers(
    *,
    layout: dict[str, Any] | None = None,
    path: PathLike | None = None,
) -> dict[str, Any]:
    """Rahmen nach Ebenen auflisten — 2.6.19."""
    doc = _load_layout(layout, path)
    return {
        "layers": doc.frames_by_layer(),
        "defs": list_doc_layers(),
        "version": __version__,
    }


def preflight(
    path: PathLike,
    *,
    min_dpi: float = 150.0,
    require_bleed: bool = False,
    color_mode: str | None = None,
    out: PathLike | None = None,
) -> dict[str, Any]:
    """Preflight: Schriften, Bildauflösung, Bleed — 2.6.19."""
    from ild_pdf.print_prep import preflight_to_text, run_preflight

    src = _require_file(path)
    mode = (color_mode or "").strip().lower() or None
    if mode not in (None, "rgb", "cmyk"):
        mode = None
    report = run_preflight(
        src,
        min_image_dpi=float(min_dpi),
        require_bleed=bool(require_bleed),
        color_mode=mode,  # type: ignore[arg-type]
    )
    data = report.to_dict()
    data["version"] = __version__
    data["text"] = preflight_to_text(report)
    if out is not None:
        dest = _p(out)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(data["text"], encoding="utf-8")
        data["out"] = str(dest.resolve())
    return data


def export_pdfx(
    path: PathLike,
    out: PathLike,
    *,
    profile: str = "pdfx4",
    bleed_mm: float | None = 3.0,
    title: str | None = None,
    preflight_first: bool = False,
) -> dict[str, Any]:
    """PDF/X bzw. print-ready Export — 2.6.19."""
    from ild_pdf.print_prep import export_pdfx as _export

    src = _require_file(path)
    prof = (profile or "pdfx4").strip().lower()
    if prof not in ("pdfx1a", "pdfx4", "print_ready"):
        prof = "pdfx4"
    result = _export(
        src,
        _p(out),
        profile=prof,  # type: ignore[arg-type]
        bleed_mm=bleed_mm,
        title=title,
        run_preflight_first=bool(preflight_first),
    )
    result["version"] = __version__
    return result


def compare_pdfs(
    left: PathLike,
    right: PathLike,
    *,
    left_page: int = 1,
    right_page: int = 1,
    threshold: int = 18,
    scale: float = 1.0,
    mode: str = "raster",
    ignore_whitespace: bool = False,
    only_differences: bool = False,
    out_png: PathLike | None = None,
    out_txt: PathLike | None = None,
    left_password: str | None = None,
    right_password: str | None = None,
) -> dict[str, Any]:
    """
    Zwei PDFs seitenweise vergleichen (Raster-Diff / Textlayer) — 2.6.19.

    Seiten 1-basiert. ``mode``: raster | text | both.
    """
    from ild_pdf.diff import compare_pdf_pages

    src_l = _require_file(left)
    src_r = _require_file(right)
    data = compare_pdf_pages(
        src_l,
        src_r,
        left_page=max(0, int(left_page) - 1),
        right_page=max(0, int(right_page) - 1),
        threshold=int(threshold),
        scale=float(scale),
        mode=mode,
        ignore_whitespace=bool(ignore_whitespace),
        only_differences=bool(only_differences),
        out_png=out_png,
        out_txt=out_txt,
        left_password=left_password,
        right_password=right_password,
    )
    data["version"] = __version__
    return data


def spellcheck(
    text: str,
    *,
    dict_path: PathLike | None = None,
    lang: str | None = None,
    include_builtin: bool = True,
    include_grammar: bool = True,
    max_suggestions: int = 5,
) -> dict[str, Any]:
    """
    Rechtschreibung inkl. Vorschläge + leichte Grammatik-Hints — 2.6.21.

    Ohne ``dict_path`` wird die Builtin-Wortliste der UI-Sprache genutzt.
    """
    from instantlensdoc.core.spellcheck import spellcheck_with_suggestions

    data = spellcheck_with_suggestions(
        text or "",
        dict_path,
        lang=lang,
        include_builtin=bool(include_builtin),
        include_grammar=bool(include_grammar),
        max_suggestions=int(max_suggestions),
    )
    data["version"] = __version__
    return data


def suggest_word(
    word: str,
    *,
    dict_path: PathLike | None = None,
    lang: str | None = None,
    max_suggestions: int = 5,
) -> dict[str, Any]:
    """Korrekturvorschläge für ein einzelnes Wort — 2.6.21."""
    from instantlensdoc.core.spellcheck import (
        resolve_wordlist,
        suggest_corrections,
    )

    if lang is None:
        try:
            from instantlensdoc.core.i18n import get_lang

            lang = get_lang()
        except Exception:
            lang = "de"
    words = resolve_wordlist(dict_path, lang=lang, include_builtin=True)
    sugg = suggest_corrections(
        word or "", words, max_suggestions=int(max_suggestions)
    )
    return {
        "word": word,
        "suggestions": sugg,
        "lang": lang,
        "version": __version__,
    }


def autocorrect_text(
    text: str,
    *,
    lang: str | None = None,
) -> dict[str, Any]:
    """Batch-Autokorrektur (Tippfehler + Baustein-Kürzel) — 2.6.21."""
    from instantlensdoc.core.autocorrect import (
        apply_autocorrect_to_text,
        effective_autocorrect_rules,
    )

    rules = effective_autocorrect_rules(lang)
    new, n = apply_autocorrect_to_text(text or "", rules)
    return {
        "text": new,
        "replacements": n,
        "lang": lang,
        "version": __version__,
    }


def list_autocorrect_rules_api(*, lang: str | None = None) -> dict[str, Any]:
    """Autokorrektur-/Snippet-Regeln auflisten — 2.6.21."""
    from instantlensdoc.core.autocorrect import list_autocorrect_rules

    rules = list_autocorrect_rules(lang)
    return {"rules": rules, "count": len(rules), "version": __version__}


def list_snippets() -> dict[str, Any]:
    """Editor-Textbausteine (9 Slots) — 2.6.21."""
    from instantlensdoc.core.app_settings import (
        EDITOR_SNIPPET_COUNT,
        get_editor_snippets,
    )

    snippets = get_editor_snippets()
    return {
        "snippets": snippets,
        "count": EDITOR_SNIPPET_COUNT,
        "version": __version__,
    }


def set_snippet(index: int, text: str) -> dict[str, Any]:
    """Textbaustein-Slot setzen (0..8) — 2.6.20."""
    from instantlensdoc.core.app_settings import set_editor_snippet

    snippets = set_editor_snippet(int(index), text)
    return {"snippets": snippets, "index": int(index), "version": __version__}


def review_enable(
    path: PathLike,
    *,
    enabled: bool = True,
    author: str | None = None,
) -> dict[str, Any]:
    """Review-Modus (Track Changes) ein/aus — 2.6.21."""
    from instantlensdoc.core.review import ReviewStore

    store = ReviewStore.for_doc(path, load=True)
    if author is not None:
        store.set_author(author, save=False)
    store.set_enabled(bool(enabled), save=True)
    data = store.summary()
    data["version"] = __version__
    return data


def review_record_diff(
    path: PathLike,
    before: str,
    after: str,
    *,
    author: str | None = None,
) -> dict[str, Any]:
    """Einfüge-/Lösch-Änderungen aus Text-Diff protokollieren — 2.6.21."""
    from instantlensdoc.core.review import ReviewStore

    store = ReviewStore.for_doc(path, load=True)
    created = store.record_diff(before, after, author=author, save=True)
    data = store.summary()
    data["recorded"] = len(created)
    data["changes"] = [c.to_dict() for c in created]
    data["version"] = __version__
    return data


def review_list(
    path: PathLike,
    *,
    author: str | None = None,
    pending_only: bool = False,
    limit: int = 200,
) -> dict[str, Any]:
    """Änderungen auflisten — 2.6.21."""
    from instantlensdoc.core.review import ReviewStore

    store = ReviewStore.for_doc(path, load=True)
    items = store.list_changes(
        author=author, pending_only=bool(pending_only), limit=int(limit)
    )
    data = store.summary()
    data["changes"] = [c.to_dict() for c in items]
    data["version"] = __version__
    return data


def review_accept(
    path: PathLike,
    change_id: str | None = None,
    *,
    all_pending: bool = False,
) -> dict[str, Any]:
    """Änderung(en) annehmen — 2.6.21."""
    from instantlensdoc.core.review import ReviewStore

    store = ReviewStore.for_doc(path, load=True)
    if all_pending:
        n = store.accept_all()
        ok = n > 0
    else:
        ok = store.accept(str(change_id or ""))
        n = 1 if ok else 0
    data = store.summary()
    data["ok"] = bool(ok)
    data["accepted"] = n
    data["version"] = __version__
    return data


def review_reject(
    path: PathLike,
    change_id: str | None = None,
    *,
    all_pending: bool = False,
) -> dict[str, Any]:
    """Änderung(en) ablehnen — 2.6.21."""
    from instantlensdoc.core.review import ReviewStore

    store = ReviewStore.for_doc(path, load=True)
    if all_pending:
        n = store.reject_all()
        ok = n > 0
    else:
        ok = store.reject(str(change_id or ""))
        n = 1 if ok else 0
    data = store.summary()
    data["ok"] = bool(ok)
    data["rejected"] = n
    data["version"] = __version__
    return data


def comment_add(
    path: PathLike,
    body: str,
    *,
    start: int = 0,
    end: int | None = None,
    anchor_text: str = "",
    author: str | None = None,
) -> dict[str, Any]:
    """Kommentar an Textstelle anhängen (ohne Body-Änderung) — 2.6.21."""
    from instantlensdoc.core.doc_comments import CommentStore

    store = CommentStore.for_doc(path, load=True)
    entry = store.add(
        body,
        start=int(start),
        end=end,
        anchor_text=anchor_text,
        author=author,
        save=True,
    )
    data = store.summary()
    data["comment"] = entry.to_dict()
    data["version"] = __version__
    return data


def comment_list(
    path: PathLike,
    *,
    author: str | None = None,
    unresolved_only: bool = False,
    limit: int = 200,
) -> dict[str, Any]:
    """Kommentare auflisten — 2.6.21."""
    from instantlensdoc.core.doc_comments import CommentStore

    store = CommentStore.for_doc(path, load=True)
    items = store.list_comments(
        author=author,
        unresolved_only=bool(unresolved_only),
        limit=int(limit),
    )
    data = store.summary()
    data["comments"] = [c.to_dict() for c in items]
    data["version"] = __version__
    return data


def comment_resolve(
    path: PathLike,
    comment_id: str,
    *,
    resolved: bool = True,
) -> dict[str, Any]:
    """Kommentar als erledigt markieren — 2.6.21."""
    from instantlensdoc.core.doc_comments import CommentStore

    store = CommentStore.for_doc(path, load=True)
    ok = store.resolve(str(comment_id), resolved=bool(resolved), save=True)
    data = store.summary()
    data["ok"] = bool(ok)
    data["comment_id"] = str(comment_id)
    data["version"] = __version__
    return data


def version_save(
    path: PathLike,
    *,
    label: str = "",
    note: str = "",
    text: str | None = None,
) -> dict[str, Any]:
    """Dokumentstand als Version speichern — 2.6.21."""
    from instantlensdoc.core.version_store import VersionStore

    store = VersionStore.for_doc(path, load=True)
    p = _p(path)
    if text is not None:
        entry = store.save_version(label=label, note=note, text=text)
    elif p.is_file():
        entry = store.save_version(label=label, note=note, source=p)
    else:
        raise FileNotFoundError(str(p))
    data = store.summary()
    data["entry"] = entry.to_dict()
    data["version"] = __version__
    return data


def version_list(path: PathLike, *, limit: int = 50) -> dict[str, Any]:
    """Versionsverlauf auflisten — 2.6.21."""
    from instantlensdoc.core.version_store import VersionStore

    store = VersionStore.for_doc(path, load=True)
    items = store.list_versions(limit=int(limit))
    data = store.summary()
    data["entries"] = [e.to_dict() for e in items]
    data["version"] = __version__
    return data


def version_restore(
    path: PathLike,
    version_id: str,
    *,
    dest: PathLike | None = None,
) -> dict[str, Any]:
    """Version wiederherstellen — 2.6.21."""
    from instantlensdoc.core.version_store import VersionStore

    store = VersionStore.for_doc(path, load=True)
    out = store.restore(str(version_id), dest=dest)
    data = store.summary()
    data["restored"] = str(out)
    data["version_id"] = str(version_id)
    data["version"] = __version__
    return data


def mail_merge_run(
    template: PathLike | str,
    recipients: PathLike,
    out_dir: PathLike,
    *,
    stem: str = "letter",
    template_is_text: bool = False,
    fmt: str = "txt",
    combined: bool = False,
    delimiter: str | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    """Seriendruck: Template + CSV/Excel → Briefe — 2.6.21 / Polish 2.6.23."""
    from instantlensdoc.core.mail_merge import (
        find_placeholders,
        load_recipients,
        mail_merge_from_files,
        mail_merge_to_dir,
        missing_fields,
    )

    if template_is_text:
        recipients_rows = load_recipients(recipients, delimiter=delimiter)
        analysis = missing_fields(str(template), recipients_rows)
        if strict and analysis["missing_columns"]:
            raise ValueError(
                "Fehlende Spalten: " + ", ".join(analysis["missing_columns"])
            )
        paths = mail_merge_to_dir(
            str(template),
            recipients_rows,
            out_dir,
            stem=stem,
            fmt=fmt,
            combined=combined,
        )
        data = {
            "count": len(recipients_rows),
            "files": len(paths),
            "placeholders": find_placeholders(str(template)),
            "missing_columns": analysis["missing_columns"],
            "fmt": fmt,
            "combined": combined,
            "output": [str(p) for p in paths],
            "out_dir": str(_p(out_dir)),
        }
    else:
        data = mail_merge_from_files(
            template,
            recipients,
            out_dir,
            stem=stem,
            fmt=fmt,
            combined=combined,
            delimiter=delimiter,
            strict=strict,
        )
    data["version"] = __version__
    return data


def mail_merge_preview(
    template: PathLike | str,
    recipients: PathLike,
    *,
    limit: int = 3,
    delimiter: str | None = None,
    template_is_text: bool = False,
) -> dict[str, Any]:
    """Seriendruck-Vorschau — 2.6.23."""
    from instantlensdoc.core.mail_merge import load_recipients, preview_merge

    tpl = str(template) if template_is_text else _require_file(template).read_text(
        encoding="utf-8"
    )
    rows = load_recipients(recipients, delimiter=delimiter)
    data = preview_merge(tpl, rows, limit=limit)
    data["version"] = __version__
    return data


def run_batch_job(
    out_dir: PathLike,
    *,
    folder: PathLike | None = None,
    paths: Sequence[PathLike] | None = None,
    ops: Sequence[str] | None = None,
    mode: str | None = None,
    watermark_text: str = "CONFIDENTIAL",
    watermark_opacity: float = 0.25,
    compress_quality: int = 70,
    user_password: str = "",
    owner_password: str | None = None,
    aes256: bool = True,
    convert_dpi: int = 150,
    convert_fmt: str = "png",
) -> dict[str, Any]:
    """PDF-/Ordner-Stapelverarbeitung — 2.6.23.

    ``ops``: convert|watermark|compress|encrypt (Liste, Pipeline).
    Alternativ ``mode`` = BatchMode-Wert (inkl. Bilder/OCR).
    """
    from instantlensdoc.core.batch import (
        BatchMode,
        PdfBatchOp,
        PdfBatchOptions,
        run_batch,
        run_pdf_batch,
    )

    opts = PdfBatchOptions(
        watermark_text=watermark_text,
        watermark_opacity=float(watermark_opacity),
        compress_quality=int(compress_quality),
        user_password=user_password or "",
        owner_password=owner_password,
        aes256=bool(aes256),
        convert_dpi=int(convert_dpi),
        convert_fmt=convert_fmt or "png",
    )
    if ops:
        result = run_pdf_batch(
            folder=folder,
            paths=paths,
            out_dir=out_dir,
            ops=list(ops),
            options=opts,
        )
    elif mode:
        if not folder:
            raise ValueError("folder erforderlich für mode=")
        result = run_batch(
            folder, out_dir, BatchMode(mode), options=opts
        )
    else:
        raise ValueError("ops= oder mode= angeben")
    data = result.to_dict()
    data["version"] = __version__
    data["ops"] = list(ops) if ops else [mode]
    return data


def sign_pdf_api(
    path: PathLike,
    *,
    level: str = "AES",
    p12: PathLike | None = None,
    p12_password: str = "",
    signer_name: str = "",
    reason: str = "",
    location: str = "",
    page: int = 1,
    out: PathLike | None = None,
    visible_stamp: bool = True,
    embed_attachment: bool = True,
) -> dict[str, Any]:
    """PDF digital signieren (eIDAS-Pfad) — 2.6.23."""
    from ild_pdf.esign import sign_pdf

    pdf = _require_file(path)
    data = sign_pdf(
        pdf,
        level=level,
        p12_path=p12,
        p12_password=p12_password,
        signer_name=signer_name,
        reason=reason,
        location=location,
        page=max(0, int(page) - 1),
        out_path=out,
        visible_stamp=visible_stamp,
        embed_attachment=embed_attachment,
    )
    data["version"] = __version__
    return data


def verify_signature_api(
    path: PathLike,
    *,
    p12: PathLike | None = None,
    p12_password: str = "",
    signature_id: str | None = None,
) -> dict[str, Any]:
    """Signatur prüfen — 2.6.23."""
    from ild_pdf.esign import verify_signature

    data = verify_signature(
        _require_file(path),
        p12_path=p12,
        p12_password=p12_password,
        signature_id=signature_id,
    )
    data["version"] = __version__
    return data


def list_signatures_api(path: PathLike) -> dict[str, Any]:
    from ild_pdf.esign import list_signatures

    data = list_signatures(_require_file(path))
    data["version"] = __version__
    return data


def generate_signing_cert(
    common_name: str,
    out_p12: PathLike,
    *,
    password: str,
    email: str = "",
    days: int = 825,
) -> dict[str, Any]:
    """Selbstsigniertes PKCS#12 für AES-Tests erzeugen — 2.6.23."""
    from ild_pdf.esign import generate_self_signed_cert

    data = generate_self_signed_cert(
        common_name,
        out_p12=out_p12,
        password=password,
        email=email,
        days=days,
    )
    data["version"] = __version__
    return data


def eidas_info(level: str = "AES") -> dict[str, Any]:
    from ild_pdf.esign import eidas_level_info, EIDAS_LEVELS

    data = eidas_level_info(level)
    data["levels"] = list(EIDAS_LEVELS)
    data["version"] = __version__
    return data


def shared_review_start(
    path: PathLike,
    share_dir: PathLike,
    *,
    author: str = "local",
    title: str = "",
    endpoint: str | None = None,
) -> dict[str, Any]:
    """Gemeinsames Review starten (Freigabeordner) — 2.6.23."""
    from instantlensdoc.core.shared_review import start_shared_review

    data = start_shared_review(
        path,
        share_dir,
        author=author,
        title=title,
        endpoint=endpoint,
    )
    data["version"] = __version__
    return data


def shared_review_join(
    share: PathLike,
    path: PathLike,
    *,
    author: str = "local",
    apply: bool = True,
) -> dict[str, Any]:
    """Gemeinsamem Review beitreten — 2.6.23."""
    from instantlensdoc.core.shared_review import join_shared_review

    data = join_shared_review(share, path, author=author, apply=bool(apply))
    data["version"] = __version__
    return data


def shared_review_sync(
    share: PathLike,
    path: PathLike,
    *,
    author: str = "local",
) -> dict[str, Any]:
    """Shared Review synchronisieren (publish+pull) — 2.6.23."""
    from instantlensdoc.core.shared_review import sync_shared_review

    data = sync_shared_review(share, path, author=author)
    data["version"] = __version__
    return data


def shared_review_status_api(share: PathLike) -> dict[str, Any]:
    """Session-Status — 2.6.23."""
    from instantlensdoc.core.shared_review import shared_review_status

    data = shared_review_status(share)
    data["version"] = __version__
    return data


def shared_review_info() -> dict[str, Any]:
    """Einschränkungen / Modi der Shared-Review-Kollaboration — 2.6.23."""
    from instantlensdoc.core.shared_review import shared_review_limitations

    data = shared_review_limitations()
    data["version"] = __version__
    return data


# --- Hyperlinks / Medien / EPUB — 2.6.24 ---


def insert_hyperlink(
    text: str,
    link_text: str,
    target: str,
    *,
    start: int | None = None,
    end: int | None = None,
    as_html: bool = False,
) -> dict[str, Any]:
    """Hyperlink in Text einfügen (URL oder #anker / ild://…) — 2.6.24."""
    from instantlensdoc.core.hyperlinks import insert_link_in_text

    return insert_link_in_text(
        text, link_text, target, start=start, end=end, as_html=as_html
    )


def extract_hyperlinks(text: str) -> dict[str, Any]:
    """Markdown-/HTML-Links aus Text lesen — 2.6.24."""
    from instantlensdoc.core.hyperlinks import extract_links_from_text, hyperlink_info

    links = [lk.to_dict() for lk in extract_links_from_text(text)]
    info = hyperlink_info()
    return {"links": links, "count": len(links), "info": info, "version": __version__}


def resolve_hyperlink(
    text: str,
    target: str,
    *,
    bookmarks: Sequence[tuple[int, str]] | None = None,
) -> dict[str, Any]:
    """Internes Hyperlink-Ziel auflösen — 2.6.24."""
    from instantlensdoc.core.hyperlinks import resolve_internal_target

    data = resolve_internal_target(text, target, bookmarks=bookmarks)
    data["version"] = __version__
    return data


def list_doc_anchors(text: str) -> dict[str, Any]:
    """Überschriften-Anker für In-Dokument-Links — 2.6.24."""
    from instantlensdoc.core.hyperlinks import list_heading_anchors

    anchors = list_heading_anchors(text)
    return {"anchors": anchors, "count": len(anchors), "version": __version__}


def save_hyperlinks_sidecar(
    path: PathLike,
    text: str | None = None,
    *,
    links: Sequence[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Links als Sidecar speichern (aus Text extrahiert oder übergeben) — 2.6.24."""
    from instantlensdoc.core.hyperlinks import (
        extract_links_from_text,
        save_links_sidecar,
    )

    p = _p(path)
    if links is None:
        body = text if text is not None else (p.read_text(encoding="utf-8") if p.is_file() else "")
        rows = extract_links_from_text(body)
    else:
        rows = list(links)
    out = save_links_sidecar(p, rows, source=p.name)
    return {"path": str(out), "count": len(rows), "version": __version__}


def layout_add_shape_frame(
    layout: dict[str, Any] | None = None,
    *,
    shape: str = "rectangle",
    x: float = 40,
    y: float = 300,
    width: float = 120,
    height: float = 80,
    page: int = 0,
    fill_color: str = "#D0E8FF",
    stroke_color: str = "#1A5276",
    path: PathLike | None = None,
) -> dict[str, Any]:
    """Formrahmen ins Layout — 2.6.24."""
    doc = _load_layout(layout, path)
    fr = doc.add_shape(
        shape,
        x=float(x),
        y=float(y),
        width=float(width),
        height=float(height),
        page=int(page),
        fill_color=fill_color,
        stroke_color=stroke_color,
    )
    if path:
        doc.save(path)
    return {"layout": doc.to_dict(), "frame": fr.to_dict(), "version": __version__}


def layout_add_video_placeholder(
    layout: dict[str, Any] | None = None,
    *,
    url: str,
    x: float = 40,
    y: float = 300,
    width: float = 320,
    height: float = 180,
    page: int = 0,
    title: str = "",
    path: PathLike | None = None,
) -> dict[str, Any]:
    """Online-Video-Platzhalter mit URL — 2.6.24."""
    doc = _load_layout(layout, path)
    fr = doc.add_video_placeholder(
        url,
        x=float(x),
        y=float(y),
        width=float(width),
        height=float(height),
        page=int(page),
        title=title,
    )
    if path:
        doc.save(path)
    return {"layout": doc.to_dict(), "frame": fr.to_dict(), "version": __version__}


def layout_scale_image(
    frame_id: str,
    factor: float,
    *,
    layout: dict[str, Any] | None = None,
    path: PathLike | None = None,
) -> dict[str, Any]:
    """Bild-/Formrahmen skalieren — 2.6.24."""
    doc = _load_layout(layout, path)
    fr = doc.scale_image(frame_id, float(factor))
    if path:
        doc.save(path)
    return {"layout": doc.to_dict(), "frame": fr.to_dict(), "version": __version__}


def layout_crop_image(
    frame_id: str,
    *,
    left: float = 0.0,
    top: float = 0.0,
    right: float = 0.0,
    bottom: float = 0.0,
    layout: dict[str, Any] | None = None,
    path: PathLike | None = None,
) -> dict[str, Any]:
    """Bild zuschneiden (relative Ränder 0–1) — 2.6.24."""
    doc = _load_layout(layout, path)
    fr = doc.crop_image(
        frame_id, left=float(left), top=float(top), right=float(right), bottom=float(bottom)
    )
    if path:
        doc.save(path)
    return {"layout": doc.to_dict(), "frame": fr.to_dict(), "version": __version__}


def export_epub_api(
    text: str,
    path: PathLike,
    *,
    title: str = "InstantLens Doc",
    author: str = "InstantLens Doc",
) -> dict[str, Any]:
    """Text → EPUB — 2.6.24."""
    from instantlensdoc.core.export import export_epub

    dest = export_epub(text, path, title=title, author=author)
    return {
        "path": str(dest),
        "format": "epub",
        "title": title,
        "version": __version__,
    }


def _load_layout(
    layout: dict[str, Any] | None,
    path: PathLike | None,
):
    from instantlensdoc.core.layout import LayoutDocument

    if path is not None:
        p = _p(path)
        if p.is_file():
            return LayoutDocument.load(p)
        return LayoutDocument()
    if layout is not None:
        return LayoutDocument.from_dict(layout)
    return LayoutDocument()
