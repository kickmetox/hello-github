"""AcroForm-Felder lesen/schreiben/erstellen (soweit pikepdf erlaubt) — 2.6.6."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional, Sequence

FormFieldType = Literal["text", "checkbox", "choice"]


@dataclass
class FormFieldInfo:
    """Beschreibung eines bestehenden AcroForm-Feldes."""

    name: str
    field_type: str  # text | checkbox | radio | choice | pushbutton | signature | unknown
    value: str = ""
    options: list[str] = field(default_factory=list)
    read_only: bool = False
    required: bool = False
    alternate_name: str = ""
    page_index: Optional[int] = None  # 0-basiert; None wenn nicht auflösbar
    rect: Optional[tuple[float, float, float, float]] = None  # PDF-UserSpace llx,lly,urx,ury

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FormFieldCandidate:
    """Erkanntes Formularfeld-Kandidat (Heuristik) — 2.6.6."""

    page_index: int
    suggested_type: FormFieldType
    suggested_name: str
    rect: tuple[float, float, float, float]  # PDF llx,lly,urx,ury
    label: str = ""
    confidence: float = 0.5
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FormCreateResult:
    """Ergebnis einer Feld-Erstellung/Änderung — 2.6.6."""

    out_path: Path
    name: str
    field_type: str
    action: str  # create | update | delete | detect-apply
    page_index: Optional[int] = None
    rect: Optional[tuple[float, float, float, float]] = None


def has_acroform(path: str | Path) -> bool:
    """True, wenn das PDF ein AcroForm mit Feldern hat."""
    import pikepdf

    path = Path(path)
    try:
        with pikepdf.open(path) as pdf:
            return bool(pdf.acroform.exists and list(pdf.acroform.fields))
    except Exception:
        return False


def _field_type_label(field) -> str:
    if getattr(field, "is_text", False):
        return "text"
    if getattr(field, "is_checkbox", False):
        return "checkbox"
    if getattr(field, "is_radio_button", False):
        return "radio"
    if getattr(field, "is_choice", False):
        return "choice"
    if getattr(field, "is_pushbutton", False):
        return "pushbutton"
    ft = str(getattr(field, "field_type", "") or "")
    if "Sig" in ft:
        return "signature"
    return "unknown"


def _value_as_str(wrapped) -> str:
    """Feldwert als String (Checkbox → true/false, sonst Text/Name)."""
    from pikepdf.form import CheckboxField, ChoiceField, RadioButtonGroup, TextField

    if isinstance(wrapped, TextField):
        return wrapped.value or ""
    if isinstance(wrapped, CheckboxField):
        return "true" if wrapped.checked else "false"
    if isinstance(wrapped, ChoiceField):
        try:
            v = wrapped.value
            return "" if v is None else str(v)
        except Exception:
            return ""
    if isinstance(wrapped, RadioButtonGroup):
        try:
            v = wrapped.value
            return "" if v is None else str(v)
        except Exception:
            return ""
    try:
        raw = getattr(wrapped, "value_as_string", None)
        if callable(raw):
            return ""
        if raw:
            return str(raw)
        v = getattr(wrapped, "value", None)
        return "" if v is None else str(v)
    except Exception:
        return ""


def _options_for(wrapped) -> list[str]:
    from pikepdf.form import ChoiceField, RadioButtonGroup

    out: list[str] = []
    try:
        if isinstance(wrapped, ChoiceField):
            for opt in wrapped.options or []:
                try:
                    out.append(str(getattr(opt, "export_value", None) or opt))
                except Exception:
                    out.append(str(opt))
        elif isinstance(wrapped, RadioButtonGroup):
            out = [str(s) for s in (wrapped.states or [])]
    except Exception:
        out = []
    return out


def _page_index_for_obj(pdf, page_obj) -> Optional[int]:
    """Seitenindex über objgen (wie Outline)."""
    if page_obj is None:
        return None
    try:
        target = getattr(page_obj, "objgen", None)
        if target is None:
            return None
        for i, page in enumerate(pdf.pages):
            if getattr(page.obj, "objgen", None) == target:
                return i
    except Exception:
        return None
    return None


def _widget_page_and_rect(pdf, wrapped) -> tuple[Optional[int], Optional[tuple[float, float, float, float]]]:
    """Erste Widget-Annotation: Seitenindex + Rect (PDF-Koordinaten)."""
    obj = getattr(wrapped, "obj", None)
    if obj is None:
        return None, None

    def _rect_of(d) -> Optional[tuple[float, float, float, float]]:
        try:
            if d is None or "/Rect" not in d:
                return None
            r = d["/Rect"]
            return (float(r[0]), float(r[1]), float(r[2]), float(r[3]))
        except Exception:
            return None

    # Direktes Widget
    page_idx = None
    try:
        if "/P" in obj:
            page_idx = _page_index_for_obj(pdf, obj["/P"])
    except Exception:
        page_idx = None
    rect = _rect_of(obj)
    if page_idx is not None or rect is not None:
        return page_idx, rect

    # Parent mit Kids (Radio/Choice)
    try:
        kids = obj.get("/Kids") if hasattr(obj, "get") else None
        if kids:
            for kid in kids:
                try:
                    k = kid.get_object() if hasattr(kid, "get_object") else kid
                    pi = None
                    if "/P" in k:
                        pi = _page_index_for_obj(pdf, k["/P"])
                    rr = _rect_of(k)
                    if pi is not None or rr is not None:
                        return pi, rr
                except Exception:
                    continue
    except Exception:
        pass
    return None, None


def list_form_fields(path: str | Path) -> list[FormFieldInfo]:
    """Liest alle AcroForm-Felder (Name, Typ, Wert, Optionen, Seite/Rect)."""
    import pikepdf
    from pikepdf.form import Form, FormFieldFlag

    path = Path(path)
    result: list[FormFieldInfo] = []
    with pikepdf.open(path) as pdf:
        if not pdf.acroform.exists:
            return result
        form = Form(pdf)
        for name, wrapped in form.items():
            try:
                flags = int(getattr(wrapped, "flags", 0) or 0)
            except Exception:
                flags = 0
            page_idx, rect = _widget_page_and_rect(pdf, wrapped)
            info = FormFieldInfo(
                name=str(name),
                field_type=_field_type_label(wrapped),
                value=_value_as_str(wrapped),
                options=_options_for(wrapped),
                read_only=bool(flags & FormFieldFlag.read_only),
                required=bool(flags & FormFieldFlag.required),
                alternate_name=str(getattr(wrapped, "alternate_name", "") or ""),
                page_index=page_idx,
                rect=rect,
            )
            result.append(info)
    return result


def get_form_values(path: str | Path) -> dict[str, str]:
    """Kurzform: {qualified_name: value_str}."""
    return {f.name: f.value for f in list_form_fields(path)}


FORM_FIELD_CSV_FIELDS = (
    "Name",
    "Typ",
    "Wert",
    "Seite",
    "ReadOnly",
)

# UTF-8 BOM für Excel-Kompatibilität — 1.3.4
_CSV_UTF8_BOM = "\ufeff"


def export_form_fields_csv(
    path: str | Path,
    fields: list[FormFieldInfo] | None = None,
    *,
    out_path: str | Path | None = None,
    utf8_bom: bool = True,
) -> Path:
    """
    AcroForm-Feldliste als CSV exportieren (UTF-8 mit BOM) — 1.3.4.
    Spalten: Name, Typ, Wert, Seite, ReadOnly.
    path: Quell-PDF (für Default-Dateiname) bzw. bereits gelesene fields.
    utf8_bom: Excel-kompatibles BOM (Standard an).
    """
    import csv
    import io

    pdf = Path(path)
    dest = Path(out_path) if out_path else pdf.with_name(f"{pdf.stem}_fields.csv")
    if dest.suffix.lower() != ".csv":
        dest = dest.with_suffix(".csv")
    dest.parent.mkdir(parents=True, exist_ok=True)
    rows = list(fields) if fields is not None else list_form_fields(pdf)
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf, fieldnames=list(FORM_FIELD_CSV_FIELDS), extrasaction="ignore"
    )
    writer.writeheader()
    for f in rows:
        page = getattr(f, "page_index", None)
        writer.writerow(
            {
                "Name": str(getattr(f, "name", "") or ""),
                "Typ": str(getattr(f, "field_type", "") or ""),
                "Wert": str(getattr(f, "value", "") or ""),
                "Seite": "" if page is None else str(int(page) + 1),
                "ReadOnly": "1" if getattr(f, "read_only", False) else "0",
            }
        )
    text = buf.getvalue()
    if utf8_bom:
        text = _CSV_UTF8_BOM + text
    dest.write_text(text, encoding="utf-8")
    return dest


def set_form_values(
    path: str | Path,
    values: dict[str, Any],
    *,
    out_path: str | Path | None = None,
) -> Path:
    """
    Schreibt Werte in bestehende AcroForm-Felder.

    Unterstützt soweit pikepdf: Text, Checkbox (true/false/1/0/yes/no),
    Choice (Auswahltext), Radio (State-Name). Signatur/Pushbutton werden übersprungen.
    Unbekannte Feldnamen werden ignoriert.
    """
    import pikepdf
    from pikepdf import Name
    from pikepdf.form import (
        CheckboxField,
        ChoiceField,
        Form,
        PushbuttonField,
        RadioButtonGroup,
        SignatureField,
        TextField,
    )

    path = Path(path)
    out_path = Path(out_path) if out_path else path
    overwrite = out_path.resolve() == path.resolve()

    truthy = {"1", "true", "yes", "ja", "on", "x", "checked"}
    falsy = {"0", "false", "no", "nein", "off", "", "unchecked"}

    with pikepdf.open(path, allow_overwriting_input=overwrite) as pdf:
        if not pdf.acroform.exists:
            raise ValueError("PDF hat kein AcroForm")
        form = Form(pdf)
        written = 0
        for key, raw in (values or {}).items():
            name = str(key)
            if name not in form:
                continue
            wrapped = form[name]
            if isinstance(wrapped, (PushbuttonField, SignatureField)):
                continue
            if isinstance(wrapped, TextField):
                wrapped.value = "" if raw is None else str(raw)
                written += 1
            elif isinstance(wrapped, CheckboxField):
                if isinstance(raw, bool):
                    wrapped.checked = raw
                else:
                    s = str(raw).strip().lower()
                    if s in truthy:
                        wrapped.checked = True
                    elif s in falsy:
                        wrapped.checked = False
                    else:
                        wrapped.checked = bool(s)
                written += 1
            elif isinstance(wrapped, ChoiceField):
                wrapped.value = "" if raw is None else str(raw)
                written += 1
            elif isinstance(wrapped, RadioButtonGroup):
                if raw is None or str(raw).strip() == "":
                    continue
                s = str(raw).strip()
                try:
                    wrapped.value = Name(s if s.startswith("/") else f"/{s}")
                except Exception:
                    wrapped.value = Name(f"/{s.lstrip('/')}")
                written += 1
            else:
                # Fallback: rohes set_value wenn vorhanden
                try:
                    wrapped.set_value("" if raw is None else str(raw), True)
                    written += 1
                except Exception:
                    pass
        # NeedAppearances für Textfelder ohne Appearance-Generator
        try:
            pdf.acroform.needs_appearances = True
        except Exception:
            pass
        if overwrite:
            pdf.save()
        else:
            pdf.save(out_path)
    return out_path


def _normalize_rect(
    rect: Sequence[float],
) -> tuple[float, float, float, float]:
    """Normiert Rect auf llx,lly,urx,ury mit Mindestgröße."""
    if len(rect) != 4:
        raise ValueError("rect braucht 4 Werte (llx,lly,urx,ury)")
    x0, y0, x1, y1 = (float(rect[0]), float(rect[1]), float(rect[2]), float(rect[3]))
    llx, urx = (x0, x1) if x0 <= x1 else (x1, x0)
    lly, ury = (y0, y1) if y0 <= y1 else (y1, y0)
    if urx - llx < 4.0:
        urx = llx + 4.0
    if ury - lly < 4.0:
        ury = lly + 4.0
    return (llx, lly, urx, ury)


def _sanitize_field_name(name: str, *, fallback: str = "Feld") -> str:
    raw = (name or "").strip()
    if not raw:
        raw = fallback
    # AcroForm: keine Punkte/Leerzeichen in Partial-Names ideal; ersetzen
    cleaned = re.sub(r"[^\w\-]+", "_", raw, flags=re.UNICODE)
    cleaned = cleaned.strip("_") or fallback
    return cleaned[:64]


def _unique_field_name(existing: set[str], base: str) -> str:
    if base not in existing:
        return base
    n = 2
    while f"{base}_{n}" in existing:
        n += 1
    return f"{base}_{n}"


def _ensure_acroform(pdf) -> Any:
    from pikepdf import Array, Dictionary

    root = pdf.Root
    if "/AcroForm" not in root:
        root.AcroForm = Dictionary(Fields=Array(), NeedAppearances=True)
    acro = root.AcroForm
    if "/Fields" not in acro:
        acro.Fields = Array()
    try:
        acro.NeedAppearances = True
    except Exception:
        pass
    return acro


def _checkbox_appearance(pdf, width: float, height: float):
    """Appearance-Streams Off/Yes für Checkbox (pikepdf checked braucht /AP)."""
    from pikepdf import Dictionary, Name, Stream

    w = max(float(width), 4.0)
    h = max(float(height), 4.0)
    # Einfacher Rahmen; Yes mit X
    off_content = (
        f"q\n0.5 w\n0 0 {w:.2f} {h:.2f} re S\nQ\n"
    ).encode("ascii")
    on_content = (
        f"q\n0.5 w\n0 0 {w:.2f} {h:.2f} re S\n"
        f"1.5 w\n1 1 m {w - 1:.2f} {h - 1:.2f} l S\n"
        f"1 {h - 1:.2f} m {w - 1:.2f} 1 l S\nQ\n"
    ).encode("ascii")
    off_stream = Stream(pdf, off_content)
    off_stream.Type = Name.XObject
    off_stream.Subtype = Name.Form
    off_stream.BBox = [0, 0, w, h]
    off_stream.Resources = Dictionary()
    on_stream = Stream(pdf, on_content)
    on_stream.Type = Name.XObject
    on_stream.Subtype = Name.Form
    on_stream.BBox = [0, 0, w, h]
    on_stream.Resources = Dictionary()
    n_dict = Dictionary()
    n_dict[Name.Off] = off_stream
    n_dict[Name.Yes] = on_stream
    ap = Dictionary()
    ap.N = n_dict
    return ap


def _page_height_pt(path: Path, page_index: int, password: str | None = None) -> float:

    kwargs = {}
    if password:
        kwargs["password"] = password
    from .pdfium_open import open_pdfium

    doc = open_pdfium(path, **kwargs)
    try:
        return float(doc[page_index].get_height())
    finally:
        doc.close()


def viewer_rect_to_pdf(
    path: str | Path,
    page_index: int,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    scale: float = 1.0,
    password: str | None = None,
) -> tuple[float, float, float, float]:
    """Viewer-Koordinaten (oben-links, skaliert) → PDF llx,lly,urx,ury — 2.6.6."""
    path = Path(path)
    s = float(scale) if scale else 1.0
    page_h = _page_height_pt(path, page_index, password)
    llx = float(x) / s
    urx = (float(x) + float(width)) / s
    top = float(y) / s
    bottom = (float(y) + float(height)) / s
    ury = page_h - top
    lly = page_h - bottom
    return _normalize_rect((llx, lly, urx, ury))


def pdf_rect_to_viewer(
    path: str | Path,
    page_index: int,
    rect: Sequence[float],
    *,
    scale: float = 1.0,
    password: str | None = None,
) -> tuple[float, float, float, float]:
    """PDF-Rect → Viewer x,y,w,h (oben-links) — 2.6.6."""
    path = Path(path)
    s = float(scale) if scale else 1.0
    llx, lly, urx, ury = _normalize_rect(rect)
    page_h = _page_height_pt(path, page_index, password)
    x = llx * s
    y = (page_h - ury) * s
    w = (urx - llx) * s
    h = (ury - lly) * s
    return (x, y, w, h)


def create_form_field(
    path: str | Path,
    page_index: int,
    rect: Sequence[float],
    name: str,
    field_type: FormFieldType | str = "text",
    *,
    options: Sequence[str] | None = None,
    value: str = "",
    required: bool = False,
    alternate_name: str = "",
    out_path: str | Path | None = None,
    password: str | None = None,
) -> FormCreateResult:
    """
    Neues AcroForm-Feld (text / checkbox / choice=Dropdown) anlegen — 2.6.6.

    ``rect`` in PDF-UserSpace (llx,lly,urx,ury). Existierendes AcroForm wird ergänzt.
    """
    import pikepdf
    from pikepdf import Array, Dictionary, Name, String

    path = Path(path)
    out_path = Path(out_path) if out_path else path
    overwrite = out_path.resolve() == path.resolve()
    ftype = str(field_type or "text").strip().lower()
    if ftype in ("dropdown", "combo", "combobox", "select"):
        ftype = "choice"
    if ftype not in ("text", "checkbox", "choice"):
        raise ValueError("field_type muss text, checkbox oder choice sein")
    llx, lly, urx, ury = _normalize_rect(rect)
    width = urx - llx
    height = ury - lly

    open_kw: dict[str, Any] = {"allow_overwriting_input": overwrite}
    if password:
        open_kw["password"] = password
    with pikepdf.open(path, **open_kw) as pdf:
        if page_index < 0 or page_index >= len(pdf.pages):
            raise IndexError(f"Seitenindex {page_index} ungültig")
        page = pdf.pages[page_index]
        existing_names: set[str] = set()
        try:
            if pdf.acroform.exists:
                from pikepdf.form import Form

                for n in Form(pdf).keys():
                    existing_names.add(str(n))
        except Exception:
            existing_names = set()
        base = _sanitize_field_name(name, fallback=f"Feld_{ftype}")
        fname = _unique_field_name(existing_names, base)
        alt = (alternate_name or name or fname).strip() or fname

        flags = 0
        if required:
            flags |= 2  # Required
        if ftype == "choice":
            flags |= 1 << 17  # Combo

        field = Dictionary(
            FT=Name.Tx if ftype == "text" else (Name.Btn if ftype == "checkbox" else Name.Ch),
            T=String(fname),
            TU=String(alt),
            Rect=Array([llx, lly, urx, ury]),
            Type=Name.Annot,
            Subtype=Name.Widget,
            P=page.obj,
            F=4,  # Print
            Ff=flags,
        )
        if ftype == "text":
            field.V = String("" if value is None else str(value))
            field.DV = String("" if value is None else str(value))
        elif ftype == "checkbox":
            on = str(value).strip().lower() in (
                "1",
                "true",
                "yes",
                "ja",
                "on",
                "x",
                "checked",
            )
            field.AP = _checkbox_appearance(pdf, width, height)
            field.AS = Name.Yes if on else Name.Off
            field.V = Name.Yes if on else Name.Off
        else:  # choice
            opts = [str(o).strip() for o in (options or []) if str(o).strip()]
            if not opts:
                opts = ["Option1", "Option2"]
            field.Opt = Array([String(o) for o in opts])
            chosen = str(value).strip() if value else opts[0]
            if chosen not in opts:
                chosen = opts[0]
            field.V = String(chosen)
            field.DV = String(chosen)

        field_obj = pdf.make_indirect(field)
        annots = page.get("/Annots")
        if annots is None:
            page.Annots = Array([field_obj])
        else:
            annots = list(annots)
            annots.append(field_obj)
            page.Annots = Array(annots)

        acro = _ensure_acroform(pdf)
        fields = list(acro.Fields)
        fields.append(field_obj)
        acro.Fields = Array(fields)

        if overwrite:
            pdf.save()
        else:
            pdf.save(out_path)

    return FormCreateResult(
        out_path=out_path,
        name=fname,
        field_type=ftype,
        action="create",
        page_index=page_index,
        rect=(llx, lly, urx, ury),
    )


def update_form_field(
    path: str | Path,
    name: str,
    *,
    value: str | None = None,
    options: Sequence[str] | None = None,
    required: bool | None = None,
    alternate_name: str | None = None,
    rect: Sequence[float] | None = None,
    out_path: str | Path | None = None,
) -> FormCreateResult:
    """Bestehendes Feld aktualisieren (Wert/Optionen/Rect/Flags) — 2.6.6."""
    import pikepdf
    from pikepdf import Array, Name, String
    from pikepdf.form import Form, FormFieldFlag

    path = Path(path)
    out_path = Path(out_path) if out_path else path
    overwrite = out_path.resolve() == path.resolve()
    target = str(name)

    with pikepdf.open(path, allow_overwriting_input=overwrite) as pdf:
        if not pdf.acroform.exists:
            raise ValueError("PDF hat kein AcroForm")
        form = Form(pdf)
        if target not in form:
            raise KeyError(f"Feld „{target}“ nicht gefunden")
        wrapped = form[target]
        obj = wrapped.obj
        ftype = _field_type_label(wrapped)

        if alternate_name is not None:
            try:
                obj.TU = String(str(alternate_name))
            except Exception:
                pass
        if required is not None:
            try:
                flags = int(getattr(wrapped, "flags", 0) or 0)
                if required:
                    flags |= int(FormFieldFlag.required)
                else:
                    flags &= ~int(FormFieldFlag.required)
                obj.Ff = flags
            except Exception:
                pass
        if rect is not None:
            rr = _normalize_rect(rect)
            obj.Rect = Array(list(rr))
        if options is not None and ftype == "choice":
            opts = [str(o).strip() for o in options if str(o).strip()]
            if opts:
                obj.Opt = Array([String(o) for o in opts])
        if value is not None:
            from pikepdf.form import CheckboxField, ChoiceField, TextField

            if isinstance(wrapped, TextField):
                wrapped.value = str(value)
            elif isinstance(wrapped, CheckboxField):
                s = str(value).strip().lower()
                on = s in (
                    "1",
                    "true",
                    "yes",
                    "ja",
                    "on",
                    "x",
                    "checked",
                )
                try:
                    wrapped.checked = on
                except Exception:
                    obj.AS = Name.Yes if on else Name.Off
                    obj.V = Name.Yes if on else Name.Off
            elif isinstance(wrapped, ChoiceField):
                wrapped.value = str(value)

        try:
            pdf.acroform.needs_appearances = True
        except Exception:
            pass
        if overwrite:
            pdf.save()
        else:
            pdf.save(out_path)

    info = next((f for f in list_form_fields(out_path) if f.name == target), None)
    return FormCreateResult(
        out_path=out_path,
        name=target,
        field_type=ftype,
        action="update",
        page_index=getattr(info, "page_index", None),
        rect=getattr(info, "rect", None),
    )


def delete_form_field(
    path: str | Path,
    name: str,
    *,
    out_path: str | Path | None = None,
) -> FormCreateResult:
    """AcroForm-Feld und Widget-Annotation entfernen — 2.6.6."""
    import pikepdf
    from pikepdf import Array
    from pikepdf.form import Form

    path = Path(path)
    out_path = Path(out_path) if out_path else path
    overwrite = out_path.resolve() == path.resolve()
    target = str(name)

    with pikepdf.open(path, allow_overwriting_input=overwrite) as pdf:
        if not pdf.acroform.exists:
            raise ValueError("PDF hat kein AcroForm")
        form = Form(pdf)
        if target not in form:
            raise KeyError(f"Feld „{target}“ nicht gefunden")
        wrapped = form[target]
        obj = wrapped.obj
        objgen = getattr(obj, "objgen", None)

        # Aus Seiten-Annots entfernen
        for page in pdf.pages:
            annots = page.get("/Annots")
            if not annots:
                continue
            kept = []
            for a in annots:
                try:
                    ao = a.get_object() if hasattr(a, "get_object") else a
                    if getattr(ao, "objgen", None) == objgen:
                        continue
                    # Kids?
                    if "/Parent" in ao:
                        try:
                            parent = ao["/Parent"]
                            if getattr(parent, "objgen", None) == objgen:
                                continue
                        except Exception:
                            pass
                    kept.append(a)
                except Exception:
                    kept.append(a)
            if len(kept) != len(list(annots)):
                if kept:
                    page.Annots = Array(kept)
                elif "/Annots" in page:
                    del page.Annots

        # Aus AcroForm.Fields entfernen
        acro = pdf.Root.AcroForm
        fields = []
        for f in acro.Fields:
            try:
                fo = f.get_object() if hasattr(f, "get_object") else f
                if getattr(fo, "objgen", None) == objgen:
                    continue
            except Exception:
                pass
            fields.append(f)
        acro.Fields = Array(fields)
        if overwrite:
            pdf.save()
        else:
            pdf.save(out_path)

    return FormCreateResult(
        out_path=out_path,
        name=target,
        field_type="unknown",
        action="delete",
    )


def detect_form_candidates(
    path: str | Path,
    page_index: int = 0,
    *,
    password: str | None = None,
    max_candidates: int = 40,
) -> list[FormFieldCandidate]:
    """
    Heuristik: Formularfeld-Kandidaten aus Textlage erkennen — 2.6.6.

    - Labels mit „:“ → Textfeld rechts daneben
    - Unterstrich-Linien („____“) → Textfeld über der Linie
    - ☐/□/Checkbox-Markers → Checkbox
    - „[ ]“ / „( )“ Muster → Checkbox
    Bestehende AcroForm-Rects werden ausgelassen (Overlap).
    """

    path = Path(path)
    kwargs: dict[str, Any] = {}
    if password:
        kwargs["password"] = password
    from .pdfium_open import open_pdfium

    doc = open_pdfium(path, **kwargs)
    try:
        if page_index < 0 or page_index >= len(doc):
            return []
        page = doc[page_index]
        page_h = float(page.get_height())
        page_w = float(page.get_width())
        textpage = page.get_textpage()
        try:
            n = textpage.count_chars()
            chars: list[tuple[str, float, float, float, float]] = []
            for i in range(n):
                try:
                    box = textpage.get_charbox(i)
                    ch = textpage.get_text_range(i, 1)
                    chars.append(
                        (ch, float(box[0]), float(box[1]), float(box[2]), float(box[3]))
                    )
                except Exception:
                    continue
        finally:
            textpage.close()
    finally:
        doc.close()

    existing = []
    try:
        for f in list_form_fields(path):
            if f.page_index == page_index and f.rect:
                existing.append(f.rect)
    except Exception:
        existing = []

    def _overlaps(r1, r2, pad: float = 2.0) -> bool:
        return not (
            r1[2] + pad < r2[0]
            or r2[2] + pad < r1[0]
            or r1[3] + pad < r2[1]
            or r2[3] + pad < r1[1]
        )

    def _occupied(rect) -> bool:
        return any(_overlaps(rect, e) for e in existing)

    # Zeilen aus Zeichen bauen (Steuerzeichen überspringen)
    items: list[tuple[str, float, float, float, float]] = []
    for ch, l, b, r, t in chars:
        if not ch or ch in ("\r", "\n", "\t", "\x00"):
            continue
        items.append((ch, l, b, r, t))
    items.sort(key=lambda c: (-(c[2] + c[4]) / 2.0, c[1]))

    lines: list[list[tuple[str, float, float, float, float]]] = []
    for ch, l, b, r, t in items:
        cy = (t + b) / 2.0
        if not lines:
            lines.append([(ch, l, b, r, t)])
            continue
        prev = lines[-1]
        prev_cy = sum((c[2] + c[4]) / 2.0 for c in prev) / len(prev)
        if abs(cy - prev_cy) <= 4.0:
            lines[-1].append((ch, l, b, r, t))
        else:
            lines.append([(ch, l, b, r, t)])

    candidates: list[FormFieldCandidate] = []
    used_names: set[str] = set()

    def _add(cand: FormFieldCandidate) -> None:
        if len(candidates) >= max_candidates:
            return
        if _occupied(cand.rect):
            return
        if any(_overlaps(cand.rect, c.rect) for c in candidates):
            return
        name = _unique_field_name(
            used_names, _sanitize_field_name(cand.suggested_name, fallback="Feld")
        )
        used_names.add(name)
        cand.suggested_name = name
        candidates.append(cand)
        existing.append(cand.rect)

    for run in lines:
        run = sorted(run, key=lambda c: c[1])
        if not run:
            continue
        text = "".join(c[0] for c in run)
        line_b = min(c[2] for c in run)
        line_t = max(c[4] for c in run)
        line_h = max(line_t - line_b, 10.0)

        # Checkbox-Marker
        for ch, l, b, r, t in run:
            if ch in ("☐", "□", "▢", "◻"):
                side = max(line_h, 12.0)
                rect = _normalize_rect((l - 1, b - 1, l - 1 + side, b - 1 + side))
                _add(
                    FormFieldCandidate(
                        page_index=page_index,
                        suggested_type="checkbox",
                        suggested_name=f"Check_{len(candidates) + 1}",
                        rect=rect,
                        label=ch,
                        confidence=0.85,
                        reason="checkbox-glyph",
                    )
                )

        # [ ] oder ( ) als Checkbox
        for m in re.finditer(r"\[\s*\]|\(\s*\)", text):
            start = m.start()
            if start >= len(run):
                continue
            l = run[start][1]
            b = run[start][2]
            side = max(line_h, 12.0)
            rect = _normalize_rect((l, b - 1, l + side, b - 1 + side))
            _add(
                FormFieldCandidate(
                    page_index=page_index,
                    suggested_type="checkbox",
                    suggested_name=f"Check_{len(candidates) + 1}",
                    rect=rect,
                    label=m.group(0),
                    confidence=0.7,
                    reason="bracket-checkbox",
                )
            )

        # Unterstriche → Textfeld
        for m in re.finditer(r"_{3,}", text):
            start, end = m.start(), m.end()
            if start >= len(run):
                continue
            end_i = min(end - 1, len(run) - 1)
            l = run[start][1]
            r = run[end_i][3]
            b = min(c[2] for c in run[start : end_i + 1])
            h = max(line_h * 1.2, 14.0)
            rect = _normalize_rect((l, b, max(r, l + 40), b + h))
            _add(
                FormFieldCandidate(
                    page_index=page_index,
                    suggested_type="text",
                    suggested_name=f"Text_{len(candidates) + 1}",
                    rect=rect,
                    label=m.group(0)[:12],
                    confidence=0.75,
                    reason="underscore-line",
                )
            )

        # Label mit Doppelpunkt → Textfeld/Dropdown rechts
        if ":" in text:
            idx = text.find(":")
            if 0 <= idx < len(run):
                label = text[: idx + 1].strip()
                if re.match(r"^\d{1,2}:\d{2}", label):
                    continue
                pure = label.rstrip(":").strip()
                if len(pure) < 1:
                    continue
                l = run[idx][3] + 4.0
                if l >= page_w - 20:
                    continue
                r = min(page_w - 20.0, max(l + 120.0, page_w * 0.55))
                b = line_b - 2.0
                t = line_t + 2.0
                if t - b < 12:
                    t = b + 14
                rect = _normalize_rect((l, b, r, t))
                base = _sanitize_field_name(pure, fallback="Feld")
                stype: FormFieldType = "text"
                conf = 0.65
                reason = "label-colon"
                low = pure.lower()
                if any(
                    k in low
                    for k in ("wahl", "auswahl", "typ", "art", "select", "dropdown")
                ):
                    stype = "choice"
                    conf = 0.55
                    reason = "label-colon-choice"
                _add(
                    FormFieldCandidate(
                        page_index=page_index,
                        suggested_type=stype,
                        suggested_name=base,
                        rect=rect,
                        label=label,
                        confidence=conf,
                        reason=reason,
                    )
                )

    candidates.sort(key=lambda c: (-c.confidence, -c.rect[3], c.rect[0]))
    return candidates[:max_candidates]


def apply_form_candidates(
    path: str | Path,
    candidates: Sequence[FormFieldCandidate],
    *,
    out_path: str | Path | None = None,
) -> list[FormCreateResult]:
    """Erkennt Kandidaten als echte AcroForm-Felder anlegen — 2.6.6."""
    path = Path(path)
    out = Path(out_path) if out_path else path
    results: list[FormCreateResult] = []
    current = path
    for i, cand in enumerate(candidates):
        dest = out if i == len(candidates) - 1 else out
        # immer in dest schreiben nach erstem
        if i == 0 and dest.resolve() != path.resolve():
            import shutil

            shutil.copy2(path, dest)
            current = dest
        elif i > 0:
            current = dest
        opts = ["Option1", "Option2"] if cand.suggested_type == "choice" else None
        res = create_form_field(
            current,
            cand.page_index,
            cand.rect,
            cand.suggested_name,
            cand.suggested_type,
            options=opts,
            out_path=dest,
        )
        res.action = "detect-apply"
        results.append(res)
        current = dest
    return results
