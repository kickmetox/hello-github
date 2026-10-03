"""AcroForm-Felder lesen/schreiben (soweit pikepdf erlaubt)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional


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


def export_form_fields_csv(
    path: str | Path,
    fields: list[FormFieldInfo] | None = None,
    *,
    out_path: str | Path | None = None,
) -> Path:
    """
    AcroForm-Feldliste als CSV exportieren (UTF-8) — 1.3.3.
    Spalten: Name, Typ, Wert, Seite, ReadOnly.
    path: Quell-PDF (für Default-Dateiname) bzw. bereits gelesene fields.
    """
    import csv

    pdf = Path(path)
    dest = Path(out_path) if out_path else pdf.with_name(f"{pdf.stem}_fields.csv")
    if dest.suffix.lower() != ".csv":
        dest = dest.with_suffix(".csv")
    dest.parent.mkdir(parents=True, exist_ok=True)
    rows = list(fields) if fields is not None else list_form_fields(pdf)
    with dest.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=list(FORM_FIELD_CSV_FIELDS), extrasaction="ignore"
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
