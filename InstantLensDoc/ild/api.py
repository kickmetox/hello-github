"""Headless InstantLens-Doc-Operationen für Python- und PowerShell-Scripting — 2.6.15."""

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
    """Dokument speichern/exportieren (docx/xlsx/pdf/txt/rtf/html/jpg) — 2.6.14."""
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
