"""Headless InstantLens-Doc-Operationen für Python- und PowerShell-Scripting — 2.6.9."""

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
