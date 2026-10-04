"""Headless InstantLens-Doc-Operationen für Python- und PowerShell-Scripting — 2.6.11."""

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
    """Seitenformate-Presets (US Letter, DIN-A, Buchformate) — 2.6.11."""
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
    """Kopf-/Fußzeile mit Titel/Ersteller bakken — 2.6.11."""
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
    """Absatzausrichtung/Abstände (Marker) bzw. Style-Defaults — 2.6.11."""
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
