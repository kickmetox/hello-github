"""Annotation-Templates (Stempel/Highlight-Styles) — Schema ildtmpl-v1 — 2.4.0."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence
from uuid import uuid4

from instantlensdoc.config import config_dir

TMPL_SCHEMA_ID = "ildtmpl-v1"
TMPL_VERSION = 1
TMPL_KINDS = frozenset({"highlight", "stamp"})
MAX_TEMPLATES = 40


class AnnTemplateError(ValueError):
    """Ungültiges ildtmpl-v1 Template-JSON."""


@dataclass
class AnnTemplate:
    """Gespeicherter Stempel- oder Highlight-Style."""

    id: str
    name: str
    kind: str  # highlight | stamp
    color: str = "#FFE066"
    opacity: float = 0.45
    stroke_width: float = 2.0
    fill_color: str = "#FFE066"
    stamp_text: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "color": self.color,
            "opacity": round(float(self.opacity), 4),
            "stroke_width": round(float(self.stroke_width), 2),
            "fill_color": self.fill_color,
            "stamp_text": self.stamp_text,
            "tags": list(self.tags or []),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AnnTemplate":
        if not isinstance(data, dict):
            raise AnnTemplateError("Template muss ein Objekt sein.")
        kind = str(data.get("kind") or "highlight").strip().lower()
        if kind not in TMPL_KINDS:
            raise AnnTemplateError(
                f"Unbekannter kind „{kind}“ — erlaubt: highlight, stamp."
            )
        name = str(data.get("name") or "").strip() or "Vorlage"
        tid = str(data.get("id") or "").strip() or uuid4().hex[:10]
        color = _norm_hex(data.get("color"), "#FFE066")
        fill = _norm_hex(data.get("fill_color"), color)
        try:
            opacity = float(data.get("opacity", 0.45))
        except (TypeError, ValueError):
            opacity = 0.45
        opacity = max(0.05, min(1.0, opacity))
        try:
            sw = float(data.get("stroke_width", 2.0) or 2.0)
        except (TypeError, ValueError):
            sw = 2.0
        sw = max(1.0, min(12.0, sw))
        stamp_text = str(data.get("stamp_text") or "").strip()
        tags_raw = data.get("tags") or []
        tags: list[str] = []
        if isinstance(tags_raw, (list, tuple)):
            for t in tags_raw:
                s = str(t).strip()
                if s and s not in tags:
                    tags.append(s)
        return cls(
            id=tid,
            name=name,
            kind=kind,
            color=color,
            opacity=opacity,
            stroke_width=sw,
            fill_color=fill,
            stamp_text=stamp_text,
            tags=tags,
        )


def _norm_hex(value: object, fallback: str) -> str:
    c = str(value or "").strip()
    if c.startswith("#") and len(c) >= 4:
        return c.upper() if len(c) == 7 else c
    return fallback


def templates_store_path() -> Path:
    return config_dir() / "ann_templates.json"


def _empty_payload() -> dict[str, Any]:
    return {
        "version": TMPL_VERSION,
        "schema": TMPL_SCHEMA_ID,
        "templates": [],
    }


def load_templates() -> List[AnnTemplate]:
    """Templates aus config/ann_templates.json laden."""
    path = templates_store_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    try:
        return parse_templates_dict(data)
    except AnnTemplateError:
        return []


def parse_templates_dict(data: object) -> List[AnnTemplate]:
    """ildtmpl-v1 Dict → Liste; wirft AnnTemplateError bei Schemafehlern."""
    if not isinstance(data, dict):
        raise AnnTemplateError("Wurzel muss ein JSON-Objekt sein.")
    ver = data.get("version")
    schema = data.get("schema")
    try:
        ver_i = int(ver)
    except (TypeError, ValueError):
        raise AnnTemplateError(
            f"Ungültige Version {ver!r} — erwartet {TMPL_VERSION} ({TMPL_SCHEMA_ID})."
        ) from None
    if ver_i != TMPL_VERSION:
        raise AnnTemplateError(
            f"Inkompatible Version {ver_i} — erwartet {TMPL_VERSION} ({TMPL_SCHEMA_ID})."
        )
    if schema is not None and str(schema) != TMPL_SCHEMA_ID:
        raise AnnTemplateError(
            f"Inkompatibles Schema „{schema}“ — erwartet „{TMPL_SCHEMA_ID}“."
        )
    raw = data.get("templates")
    if raw is None:
        raise AnnTemplateError("Feld „templates“ fehlt.")
    if not isinstance(raw, list):
        raise AnnTemplateError("Feld „templates“ muss eine Liste sein.")
    out: List[AnnTemplate] = []
    seen: set[str] = set()
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise AnnTemplateError(f"templates[{idx}] muss ein Objekt sein.")
        t = AnnTemplate.from_dict(item)
        if t.id in seen:
            t.id = uuid4().hex[:10]
        seen.add(t.id)
        out.append(t)
    return out


def save_templates(templates: Sequence[AnnTemplate]) -> Path:
    """Templates persistieren (max MAX_TEMPLATES)."""
    items = list(templates)[:MAX_TEMPLATES]
    payload = {
        "version": TMPL_VERSION,
        "schema": TMPL_SCHEMA_ID,
        "templates": [t.to_dict() for t in items],
    }
    path = templates_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def export_templates_dict(templates: Sequence[AnnTemplate] | None = None) -> dict[str, Any]:
    """Export-Payload ildtmpl-v1."""
    items = list(templates) if templates is not None else load_templates()
    return {
        "version": TMPL_VERSION,
        "schema": TMPL_SCHEMA_ID,
        "templates": [t.to_dict() for t in items],
    }


def export_templates_json(
    path: str | Path,
    templates: Sequence[AnnTemplate] | None = None,
) -> Path:
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(export_templates_dict(templates), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return dest


def import_templates_dict(
    data: object,
    *,
    merge: bool = True,
) -> List[AnnTemplate]:
    """
    Templates aus ildtmpl-v1 übernehmen.
    merge=True: bestehende behalten, neue/aktualisierte nach id/name mergen.
    merge=False: ersetzen.
    """
    incoming = parse_templates_dict(data)
    if not merge:
        save_templates(incoming)
        return load_templates()
    current = {t.id: t for t in load_templates()}
    by_name = {t.name.casefold(): t.id for t in current.values()}
    for t in incoming:
        # gleiche id ersetzen; sonst gleicher Name → ersetzen; sonst anhängen
        if t.id in current:
            current[t.id] = t
            continue
        name_key = t.name.casefold()
        if name_key in by_name:
            old_id = by_name[name_key]
            t.id = old_id
            current[old_id] = t
        else:
            current[t.id] = t
            by_name[name_key] = t.id
    items = list(current.values())[:MAX_TEMPLATES]
    save_templates(items)
    return load_templates()


def import_templates_json(path: str | Path, *, merge: bool = True) -> List[AnnTemplate]:
    raw = Path(path).read_text(encoding="utf-8")
    data = json.loads(raw)
    return import_templates_dict(data, merge=merge)


def save_template(
    name: str,
    kind: str,
    *,
    color: str = "#FFE066",
    opacity: float = 0.45,
    stroke_width: float = 2.0,
    fill_color: str | None = None,
    stamp_text: str = "",
    tags: Iterable[str] | None = None,
    template_id: str | None = None,
) -> AnnTemplate:
    """Neue Vorlage speichern oder bestehende (id) aktualisieren."""
    kind_n = str(kind or "highlight").strip().lower()
    if kind_n not in TMPL_KINDS:
        raise AnnTemplateError(f"Unbekannter kind „{kind}“.")
    items = load_templates()
    tid = (template_id or "").strip() or uuid4().hex[:10]
    entry = AnnTemplate(
        id=tid,
        name=(name or "").strip() or "Vorlage",
        kind=kind_n,
        color=_norm_hex(color, "#FFE066"),
        opacity=max(0.05, min(1.0, float(opacity))),
        stroke_width=max(1.0, min(12.0, float(stroke_width))),
        fill_color=_norm_hex(fill_color or color, "#FFE066"),
        stamp_text=str(stamp_text or "").strip(),
        tags=[str(t).strip() for t in (tags or []) if str(t).strip()],
    )
    replaced = False
    for i, t in enumerate(items):
        if t.id == entry.id or t.name.casefold() == entry.name.casefold():
            entry.id = t.id
            items[i] = entry
            replaced = True
            break
    if not replaced:
        items.append(entry)
    save_templates(items)
    return entry


def delete_template(template_id: str) -> bool:
    tid = str(template_id or "").strip()
    if not tid:
        return False
    items = load_templates()
    nxt = [t for t in items if t.id != tid]
    if len(nxt) == len(items):
        return False
    save_templates(nxt)
    return True


def get_template(template_id: str) -> Optional[AnnTemplate]:
    tid = str(template_id or "").strip()
    for t in load_templates():
        if t.id == tid:
            return t
    return None


def capture_current_styles(
    kind: str = "highlight",
    *,
    name: str = "",
    stamp_text: str = "",
) -> AnnTemplate:
    """Aktuelle App-Settings als Template-Objekt (noch nicht persistiert)."""
    from instantlensdoc.core.app_settings import (
        get_ann_default_fill_color,
        get_ann_default_opacity,
        get_ann_default_stroke_width,
        get_ann_highlight_color,
        get_ann_pen_color,
    )

    kind_n = str(kind or "highlight").strip().lower()
    if kind_n == "stamp":
        color = get_ann_pen_color()
        opacity = get_ann_default_opacity()
        default_name = name or "Stempel-Style"
    else:
        color = get_ann_highlight_color()
        opacity = min(0.55, get_ann_default_opacity())
        default_name = name or "Highlight-Style"
    return AnnTemplate(
        id=uuid4().hex[:10],
        name=default_name,
        kind=kind_n if kind_n in TMPL_KINDS else "highlight",
        color=color,
        opacity=opacity,
        stroke_width=get_ann_default_stroke_width(),
        fill_color=get_ann_default_fill_color(),
        stamp_text=stamp_text,
        tags=[],
    )


def apply_template(template: AnnTemplate) -> None:
    """Template-Styles in App-Settings übernehmen."""
    from instantlensdoc.core.app_settings import (
        set_ann_default_fill_color,
        set_ann_default_opacity,
        set_ann_default_stroke_width,
        set_ann_highlight_color,
        set_ann_pen_color,
    )

    if template.kind == "stamp":
        set_ann_pen_color(template.color)
        set_ann_default_opacity(template.opacity)
        set_ann_default_stroke_width(template.stroke_width)
        set_ann_default_fill_color(template.fill_color)
    else:
        set_ann_highlight_color(template.color)
        set_ann_default_opacity(template.opacity)
        set_ann_default_fill_color(template.fill_color)
