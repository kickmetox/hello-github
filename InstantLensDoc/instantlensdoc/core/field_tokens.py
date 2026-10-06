"""Ersatzzeichen / Felder: Builtin- und benutzerdefinierte Tokens.

Sichtbarer Platzhalter bleibt ``{name}`` (kein ¶/Form-Feed). Aufgelöste Werte
kommen bei Druck, Vorschau und Speichern (strftime / QDateTime / Seitenindex).
Benutzerfelder liegen in Dokument-Meta, DOCX-Custom-Properties oder Sidecar.
"""

from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping
from xml.etree import ElementTree as ET


FIELD_FORMATS = ("date", "time", "text", "number")
FIELD_FORMAT_LABELS = {
    "date": "Datum",
    "time": "Uhrzeit",
    "text": "Text",
    "number": "Zahl",
}
INSERT_TARGETS = ("body", "header", "footer")
INSERT_TARGET_LABELS = {
    "body": "Fließtext",
    "header": "Kopfzeile",
    "footer": "Fußzeile",
}

BUILTIN_FIELDS = ("date", "time", "page", "n", "total", "filename", "author")
BUILTIN_FIELD_LABELS = {
    "date": "Datum",
    "time": "Uhrzeit",
    "page": "Seitennummer",
    "n": "Seitennummer (n)",
    "total": "Seitenanzahl",
    "filename": "Dateiname",
    "author": "Autor",
}
BUILTIN_FIELD_FORMATS = {
    "date": "date",
    "time": "time",
    "page": "number",
    "n": "number",
    "total": "number",
    "filename": "text",
    "author": "text",
}
_FIELD_ALIASES = {
    "datum": "date",
    "zeit": "time",
    "uhrzeit": "time",
    "seite": "page",
    "seitennummer": "page",
    "pagenumber": "page",
    "pageno": "page",
    "seiten": "total",
    "seitenanzahl": "total",
    "pagecount": "total",
    "pagetotal": "total",
    "pages": "total",
    "npages": "total",
    "dateiname": "filename",
    "file": "filename",
    "autor": "author",
    "verfasser": "author",
}
BUILTIN_FIELD_TOKENS = frozenset(BUILTIN_FIELDS) | frozenset(_FIELD_ALIASES)

_FIELD_TOKEN_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
_FIELD_TOKEN_DBL_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")
_FIELD_TOKEN_PAD_RE = re.compile(r"\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}")
_FIELD_TOKEN_GUILLEMET_RE = re.compile(r"«\s*([A-Za-z_][A-Za-z0-9_]*)\s*»")
_FIELD_SPAN_ATTR_RE = re.compile(r"data-ild-field\s*=\s*['\"]([^'\"]+)['\"]", re.I)
_CONTROL_RE = re.compile(
    "["
    "\x00-\x08\x0b\x0c\x0e-\x1f\x7f"
    "\u200b-\u200f"
    "\u2028-\u202e"
    "\u2060-\u2064"
    "\u2066-\u2069"
    "\ufeff"
    "\ufff9-\ufffb"
    "\ufffd"
    "]"
)

DATE_STRFTIME = "%d.%m.%Y"
TIME_STRFTIME = "%H:%M:%S"
QDATE_FORMAT = "dd.MM.yyyy"
QTIME_FORMAT = "HH:mm:ss"

SIDECAR_SCHEMA = "ildfields-v1"
CUSTOM_PROP_PREFIX = "ILD.field."
CUSTOM_PROP_BLOB = "ILD.field_tokens"
_CUSTOM_NS = "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"
_VT_NS = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"
_RELS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
_CUSTOM_REL_TYPE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties"
)
_CUSTOM_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.custom-properties+xml"
)
_CUSTOM_FMTID = "{D5CDD505-2E9C-101B-9397-08002B2CF9AE}"


@dataclass
class FieldTokenSpec:
    name: str
    format: str = "text"
    value: str = ""
    builtin: bool = False

    def token(self) -> str:
        ident = canonical_field_name(self.name)
        return f"{{{ident}}}" if ident else ""

    def as_meta(self) -> str | dict[str, str]:
        if self.builtin:
            return self.token()
        return {"value": self.value, "format": canonical_field_format(self.format)}


@dataclass
class FieldResolveContext:
    now: datetime = field(default_factory=datetime.now)
    page: int = 1
    page_count: int = 1
    filename: str = ""
    author: str = ""
    specs: dict[str, FieldTokenSpec] = field(default_factory=dict)

    def with_page(self, page: int, page_count: int | None = None) -> "FieldResolveContext":
        return FieldResolveContext(
            now=self.now,
            page=max(1, int(page)),
            page_count=max(1, int(self.page_count if page_count is None else page_count)),
            filename=self.filename,
            author=self.author,
            specs=dict(self.specs),
        )


def canonical_field_format(fmt: str | None) -> str:
    raw = str(fmt or "text").strip().lower()
    aliases = {
        "datum": "date",
        "uhrzeit": "time",
        "zeit": "time",
        "zahl": "number",
        "nummer": "number",
        "text": "text",
        "date": "date",
        "time": "time",
        "number": "number",
        "int": "number",
        "float": "number",
    }
    return aliases.get(raw, "text" if raw not in FIELD_FORMATS else raw)


def canonical_insert_target(target: str | None) -> str:
    raw = str(target or "body").strip().lower()
    aliases = {
        "body": "body",
        "fliesstext": "body",
        "fließtext": "body",
        "text": "body",
        "header": "header",
        "kopf": "header",
        "kopfzeile": "header",
        "footer": "footer",
        "fuss": "footer",
        "fuß": "footer",
        "fusszeile": "footer",
        "fußzeile": "footer",
    }
    return aliases.get(raw, "body")


def canonical_field_name(name: str) -> str:
    ident = re.sub(r"[^A-Za-z0-9_]", "", str(name or "").strip())
    if not ident:
        return ""
    low = ident.lower()
    if low in _FIELD_ALIASES:
        return _FIELD_ALIASES[low]
    if low in BUILTIN_FIELD_TOKENS:
        return low
    return ident


def canonical_field_token(name: str) -> str:
    ident = canonical_field_name(name)
    return f"{{{ident}}}" if ident else ""


def safe_field_display(name: str, ersatz: str | None = None) -> str:
    """Sichtbares Feld-Token — nie ¶ / Form-Feed / Replacement-Kasten."""
    token = canonical_field_token(name)
    if not token:
        return ""
    if ersatz is None:
        return token
    cleaned = (
        str(ersatz)
        .replace("\x0c", "")
        .replace("\u00b6", "")
        .replace("\ufffd", "")
        .replace("\u2028", "")
        .replace("\u2029", "")
    )
    cleaned = _CONTROL_RE.sub("", cleaned).strip()
    if not cleaned:
        return token
    return cleaned


def normalize_field_tokens(text: str) -> str:
    """``{{date}}`` / ``{ DATE }`` / ``«page»`` → ``{date}`` / ``{page}``; Custom bleibt."""
    if not text:
        return ""

    def _canon(raw: str) -> str:
        return canonical_field_token(raw) or ("{" + raw + "}" if raw else "")

    s = _FIELD_TOKEN_DBL_RE.sub(lambda m: _canon(m.group(1)), str(text))
    s = _FIELD_TOKEN_GUILLEMET_RE.sub(lambda m: _canon(m.group(1)), s)
    s = _FIELD_TOKEN_PAD_RE.sub(lambda m: _canon(m.group(1)), s)
    return s


def extract_field_tokens(text_or_html: str) -> dict[str, str]:
    """Feldnamen aus Fließtext/HTML (data-ild-field + ``{name}``)."""
    blob = text_or_html or ""
    out: dict[str, str] = {}
    for m in _FIELD_SPAN_ATTR_RE.finditer(blob):
        ident = canonical_field_name(m.group(1))
        if ident:
            out[ident] = canonical_field_token(ident)
    for m in _FIELD_TOKEN_RE.finditer(blob):
        ident = canonical_field_name(m.group(1))
        if ident:
            out.setdefault(ident, canonical_field_token(ident))
    return out


def builtin_spec(name: str) -> FieldTokenSpec:
    ident = canonical_field_name(name) or "date"
    if ident not in BUILTIN_FIELDS:
        ident = "date"
    return FieldTokenSpec(
        name=ident,
        format=BUILTIN_FIELD_FORMATS.get(ident, "text"),
        value="",
        builtin=True,
    )


def coerce_field_spec(name: str, raw: Any) -> FieldTokenSpec | None:
    ident = canonical_field_name(name)
    if not ident:
        return None
    builtin = ident in BUILTIN_FIELDS
    if isinstance(raw, FieldTokenSpec):
        spec = raw
        spec.name = ident
        spec.builtin = builtin or spec.builtin
        spec.format = canonical_field_format(spec.format)
        if builtin:
            spec.format = BUILTIN_FIELD_FORMATS.get(ident, spec.format)
        return spec
    if isinstance(raw, Mapping):
        fmt = canonical_field_format(raw.get("format"))
        value = safe_field_display(ident, str(raw.get("value") or raw.get("ersatz") or ""))
        if value == canonical_field_token(ident):
            value = str(raw.get("value") or raw.get("ersatz") or "").strip()
            value = _CONTROL_RE.sub("", value).strip()
        if builtin:
            fmt = BUILTIN_FIELD_FORMATS.get(ident, fmt)
        return FieldTokenSpec(name=ident, format=fmt, value=value, builtin=builtin)
    display = safe_field_display(ident, None if raw is None else str(raw))
    value = ""
    if display and display != canonical_field_token(ident) and not builtin:
        value = display
    fmt = BUILTIN_FIELD_FORMATS.get(ident, "text") if builtin else "text"
    return FieldTokenSpec(name=ident, format=fmt, value=value, builtin=builtin)


def coerce_field_specs(raw: Any) -> dict[str, FieldTokenSpec]:
    out: dict[str, FieldTokenSpec] = {}
    if isinstance(raw, Mapping):
        items: Iterable[tuple[Any, Any]] = raw.items()
    elif isinstance(raw, (list, tuple)):
        items = []
        for item in raw:
            if isinstance(item, FieldTokenSpec):
                items.append((item.name, item))  # type: ignore[arg-type]
            elif isinstance(item, Mapping):
                items.append((item.get("name"), item))  # type: ignore[arg-type]
            else:
                items.append((item, None))  # type: ignore[arg-type]
    else:
        items = []
    for name, val in items:
        spec = coerce_field_spec(str(name or ""), val)
        if spec is not None:
            out[spec.name] = spec
    return out


def serialize_field_specs(specs: Mapping[str, FieldTokenSpec] | Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, spec in coerce_field_specs(specs).items():
        out[name] = spec.as_meta()
    return out


def _now_date_time() -> tuple[str, str]:
    try:
        from PySide6.QtCore import QDateTime

        dt = QDateTime.currentDateTime()
        return dt.toString(QDATE_FORMAT), dt.toString(QTIME_FORMAT)
    except Exception:
        now = datetime.now()
        return now.strftime(DATE_STRFTIME), now.strftime(TIME_STRFTIME)


def _parse_datetime_value(value: str, kind: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        date_s, time_s = _now_date_time()
        return date_s if kind == "date" else time_s
    try:
        from PySide6.QtCore import QDateTime, QDate, QTime

        for fmt in (
            "yyyy-MM-ddTHH:mm:ss",
            "yyyy-MM-dd HH:mm:ss",
            "yyyy-MM-dd",
            "dd.MM.yyyy HH:mm:ss",
            "dd.MM.yyyy",
            "HH:mm:ss",
            "HH:mm",
        ):
            dt = QDateTime.fromString(raw, fmt)
            if dt.isValid():
                return dt.toString(QDATE_FORMAT if kind == "date" else QTIME_FORMAT)
            if kind == "date":
                d = QDate.fromString(raw, fmt)
                if d.isValid():
                    return d.toString(QDATE_FORMAT)
            if kind == "time":
                t = QTime.fromString(raw, fmt)
                if t.isValid():
                    return t.toString(QTIME_FORMAT)
    except Exception:
        pass
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y",
        "%H:%M:%S",
        "%H:%M",
    ):
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.strftime(DATE_STRFTIME if kind == "date" else TIME_STRFTIME)
        except ValueError:
            continue
    return raw


def format_number_value(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "0"
    try:
        n = float(raw.replace(",", "."))
        if n == int(n):
            return str(int(n))
        return f"{n:.2f}".replace(".", ",")
    except (TypeError, ValueError):
        return raw


def resolve_field_value(name: str, ctx: FieldResolveContext, spec: FieldTokenSpec | None = None) -> str:
    ident = canonical_field_name(name) or canonical_field_name(getattr(spec, "name", "") or "")
    if not ident:
        return ""
    spec = spec or ctx.specs.get(ident)
    if spec is None:
        spec = coerce_field_spec(ident, None)
    assert spec is not None
    if ident == "date" or (spec.builtin and ident == "date"):
        return _now_date_time()[0]
    if ident == "time":
        return _now_date_time()[1]
    if ident in {"page", "n"}:
        return str(max(1, int(ctx.page or 1)))
    if ident == "total":
        return str(max(1, int(ctx.page_count or 1)))
    if ident == "filename":
        return str(ctx.filename or "")
    if ident == "author":
        return str(ctx.author or "")
    fmt = canonical_field_format(spec.format)
    value = spec.value
    if fmt == "date":
        return _parse_datetime_value(value, "date")
    if fmt == "time":
        return _parse_datetime_value(value, "time")
    if fmt == "number":
        return format_number_value(value)
    return safe_field_display(ident, value) if value else canonical_field_token(ident)


def resolve_field_tokens_in_text(text: str, ctx: FieldResolveContext) -> str:
    """``{name}`` durch aktuellen Wert ersetzen (Druck/Vorschau/Speichern)."""
    if not text:
        return ""
    blob = normalize_field_tokens(text)

    def _sub(m: re.Match[str]) -> str:
        ident = canonical_field_name(m.group(1))
        if not ident:
            return m.group(0)
        return resolve_field_value(ident, ctx, ctx.specs.get(ident))

    return _FIELD_TOKEN_RE.sub(_sub, blob)


def make_resolve_context(
    *,
    page: int = 1,
    page_count: int = 1,
    filename: str = "",
    author: str = "",
    specs: Any = None,
    now: datetime | None = None,
) -> FieldResolveContext:
    return FieldResolveContext(
        now=now or datetime.now(),
        page=max(1, int(page or 1)),
        page_count=max(1, int(page_count or 1)),
        filename=str(filename or ""),
        author=str(author or ""),
        specs=coerce_field_specs(specs or {}),
    )


def sidecar_path_for(doc_path: str | Path | None) -> Path | None:
    if not doc_path:
        return None
    p = Path(doc_path)
    return p.with_suffix(p.suffix + ".ildfields.json")


def load_field_tokens_sidecar(doc_path: str | Path | None) -> dict[str, FieldTokenSpec]:
    src = sidecar_path_for(doc_path)
    if src is None or not src.is_file():
        return {}
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    if isinstance(data, Mapping) and isinstance(data.get("fields"), Mapping):
        data = data.get("fields")
    return coerce_field_specs(data)


def save_field_tokens_sidecar(
    doc_path: str | Path | None,
    specs: Mapping[str, FieldTokenSpec] | Mapping[str, Any] | None,
) -> Path | None:
    src = sidecar_path_for(doc_path)
    if src is None:
        return None
    payload = {
        "schema": SIDECAR_SCHEMA,
        "version": 1,
        "fields": serialize_field_specs(specs or {}),
    }
    src.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return src


def delete_field_tokens_sidecar(doc_path: str | Path | None) -> bool:
    src = sidecar_path_for(doc_path)
    if src is None or not src.is_file():
        return False
    try:
        src.unlink()
        return True
    except OSError:
        return False


def merge_field_specs(*groups: Mapping[str, Any] | None) -> dict[str, FieldTokenSpec]:
    out: dict[str, FieldTokenSpec] = {}
    for group in groups:
        if not group:
            continue
        for name, spec in coerce_field_specs(group).items():
            prev = out.get(name)
            if prev is None:
                out[name] = spec
                continue
            if spec.value and not prev.value:
                prev.value = spec.value
            if spec.format and spec.format != "text":
                prev.format = spec.format
            prev.builtin = prev.builtin or spec.builtin
            out[name] = prev
    return out


def _read_zip_xml(zf: zipfile.ZipFile, name: str) -> ET.Element | None:
    try:
        raw = zf.read(name)
    except KeyError:
        return None
    try:
        return ET.fromstring(raw)
    except ET.ParseError:
        return None


def read_docx_custom_field_tokens(path: str | Path) -> dict[str, FieldTokenSpec]:
    p = Path(path)
    if not p.is_file():
        return {}
    try:
        with zipfile.ZipFile(p, "r") as zf:
            root = _read_zip_xml(zf, "docProps/custom.xml")
    except (OSError, zipfile.BadZipFile):
        return {}
    if root is None:
        return {}
    blob = ""
    pairs: dict[str, str] = {}
    for prop in root.iter():
        tag = prop.tag.rsplit("}", 1)[-1]
        if tag != "property":
            continue
        name = str(prop.attrib.get("name") or "")
        text = "".join(prop.itertext()).strip()
        if name == CUSTOM_PROP_BLOB:
            blob = text
        elif name.startswith(CUSTOM_PROP_PREFIX):
            pairs[name[len(CUSTOM_PROP_PREFIX) :]] = text
    specs = coerce_field_specs(pairs)
    if blob:
        try:
            parsed = json.loads(blob)
        except ValueError:
            parsed = None
        if isinstance(parsed, Mapping):
            specs = merge_field_specs(specs, parsed)
    return specs


def _ensure_custom_rels(root: ET.Element) -> None:
    found = False
    max_id = 0
    for rel in list(root):
        rid = str(rel.attrib.get("Id") or "")
        if rid.startswith("rId"):
            try:
                max_id = max(max_id, int(rid[3:]))
            except ValueError:
                pass
        if rel.attrib.get("Type") == _CUSTOM_REL_TYPE:
            rel.set("Target", "docProps/custom.xml")
            found = True
    if not found:
        ET.SubElement(
            root,
            f"{{{_RELS_NS}}}Relationship",
            {
                "Id": f"rId{max_id + 1}",
                "Type": _CUSTOM_REL_TYPE,
                "Target": "docProps/custom.xml",
            },
        )


def _ensure_custom_content_type(root: ET.Element) -> None:
    found = False
    for child in list(root):
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "Override" and child.attrib.get("PartName") == "/docProps/custom.xml":
            child.set("ContentType", _CUSTOM_CONTENT_TYPE)
            found = True
    if not found:
        ET.SubElement(
            root,
            f"{{{_CT_NS}}}Override",
            {"PartName": "/docProps/custom.xml", "ContentType": _CUSTOM_CONTENT_TYPE},
        )


def _custom_xml_bytes(specs: Mapping[str, FieldTokenSpec], *, filename: str = "") -> bytes:
    coerced = coerce_field_specs(specs)
    blob = json.dumps(serialize_field_specs(coerced), ensure_ascii=False)
    items: list[tuple[str, str]] = [(CUSTOM_PROP_BLOB, blob)]
    ctx = make_resolve_context(specs=coerced, filename=filename)
    for name, spec in coerced.items():
        if spec.builtin:
            value = resolve_field_value(name, ctx, spec)
        else:
            value = spec.value if spec.value else spec.token()
        if not value:
            continue
        items.append((CUSTOM_PROP_PREFIX + name, value))
    props = []
    pid = 2
    for name, value in items:
        text = (
            str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        name_esc = (
            str(name).replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
        )
        props.append(
            f'<property fmtid="{_CUSTOM_FMTID}" pid="{pid}" name="{name_esc}">'
            f"<vt:lpwstr>{text}</vt:lpwstr></property>"
        )
        pid += 1
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Properties xmlns="{_CUSTOM_NS}" xmlns:vt="{_VT_NS}">'
        f"{''.join(props)}</Properties>"
    )
    return xml.encode("utf-8")


def write_docx_custom_field_tokens(
    path: str | Path,
    specs: Mapping[str, FieldTokenSpec] | Mapping[str, Any] | None,
) -> bool:
    p = Path(path)
    if not p.is_file():
        return False
    coerced = coerce_field_specs(specs or {})
    try:
        with zipfile.ZipFile(p, "r") as zin:
            names = zin.namelist()
            contents = {name: zin.read(name) for name in names}
    except (OSError, zipfile.BadZipFile):
        return False
    rels_name = "_rels/.rels"
    ct_name = "[Content_Types].xml"
    rels_root = ET.fromstring(contents.get(rels_name) or b"<Relationships/>")
    ct_root = ET.fromstring(contents.get(ct_name) or b"<Types/>")
    _ensure_custom_rels(rels_root)
    _ensure_custom_content_type(ct_root)
    contents[rels_name] = ET.tostring(rels_root, encoding="utf-8", xml_declaration=True)
    contents[ct_name] = ET.tostring(ct_root, encoding="utf-8", xml_declaration=True)
    contents["docProps/custom.xml"] = _custom_xml_bytes(coerced, filename=p.name)
    tmp = p.with_suffix(p.suffix + ".ildfields.tmp")
    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for name, data in contents.items():
                zout.writestr(name, data)
        tmp.replace(p)
        return True
    except OSError:
        try:
            if tmp.is_file():
                tmp.unlink()
        except OSError:
            pass
        return False


def persist_document_field_tokens(
    path: str | Path | None,
    specs: Mapping[str, FieldTokenSpec] | Mapping[str, Any] | None,
    *,
    kind: str = "",
) -> None:
    """Custom-Properties (DOCX) und Sidecar neben der Datei schreiben."""
    coerced = coerce_field_specs(specs or {})
    if path:
        suffix = Path(path).suffix.lower()
        if (kind or "").lower() == "docx" or suffix == ".docx":
            write_docx_custom_field_tokens(path, coerced)
        if coerced:
            save_field_tokens_sidecar(path, coerced)
        else:
            delete_field_tokens_sidecar(path)
