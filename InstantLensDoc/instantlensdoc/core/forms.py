"""Formulargenerator: Felder definieren, speichern/laden, HTML/PDF-Export."""

from __future__ import annotations

import html
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

FORM_SCHEMA_VERSION = 1


class FieldType(str, Enum):
    TEXT = "text"
    TEXTAREA = "textarea"
    CHECKBOX = "checkbox"
    DROPDOWN = "dropdown"
    DATE = "date"
    EMAIL = "email"
    NUMBER = "number"
    RADIO = "radio"
    PASSWORD = "password"
    TEL = "tel"
    SIGNATURE = "signature"  # Unterschriftslinie (Darstellung)
    FILE = "file"


@dataclass
class FormField:
    label: str
    name: str = ""
    type: FieldType = FieldType.TEXT
    required: bool = False
    options: List[str] = field(default_factory=list)
    placeholder: str = ""
    default: str = ""
    id: str = field(default_factory=lambda: uuid4().hex[:8])

    def __post_init__(self):
        if not self.name:
            self.name = f"field_{self.id}"
        if isinstance(self.type, str):
            self.type = FieldType(self.type)


@dataclass
class FormDefinition:
    title: str = "Formular"
    fields: List[FormField] = field(default_factory=list)
    description: str = ""

    def add_field(self, field: FormField) -> FormField:
        self.fields.append(field)
        return field

    def to_dict(self) -> dict:
        return {
            "schema_version": FORM_SCHEMA_VERSION,
            "title": self.title,
            "description": self.description,
            "fields": [
                {
                    **asdict(f),
                    "type": f.type.value,
                }
                for f in self.fields
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FormDefinition":
        form = cls(
            title=data.get("title") or "Formular",
            description=data.get("description") or "",
        )
        for raw in data.get("fields", []):
            raw = dict(raw)
            raw.pop("id", None)  # frische IDs ok; behalten wenn vorhanden
            fid = raw.get("id")
            raw.setdefault("placeholder", "")
            raw.setdefault("default", "")
            field = FormField(**{k: v for k, v in raw.items() if k in FormField.__dataclass_fields__})
            if fid:
                field.id = fid
            form.fields.append(field)
        return form

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: str | Path) -> "FormDefinition":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)


def export_html(form: FormDefinition, path: str | Path) -> Path:
    path = Path(path)
    parts = [
        "<!DOCTYPE html>",
        "<html lang='de'><head><meta charset='utf-8'>",
        f"<title>{html.escape(form.title)}</title>",
        "<style>body{font-family:sans-serif;max-width:640px;margin:2rem auto}"
        "label{display:block;margin:.75rem 0 .25rem}input,select,textarea{width:100%;padding:.4rem}"
        ".req{color:#a00}.sig{border-bottom:2px solid #333;height:48px;margin:8px 0}"
        ".radio label{display:inline;margin-right:1rem}</style></head><body>",
        f"<h1>{html.escape(form.title)}</h1>",
    ]
    if form.description:
        parts.append(f"<p>{html.escape(form.description)}</p>")
    parts.append("<form method='post' action='#'>")
    for f in form.fields:
        req = " <span class='req'>*</span>" if f.required else ""
        req_attr = " required" if f.required else ""
        ph = f" placeholder='{html.escape(f.placeholder)}'" if f.placeholder else ""
        val = f" value='{html.escape(f.default)}'" if f.default else ""
        parts.append(f"<label for='{f.name}'>{html.escape(f.label)}{req}</label>")
        if f.type == FieldType.TEXTAREA:
            parts.append(
                f"<textarea id='{f.name}' name='{f.name}' rows='4'{ph}{req_attr}>"
                f"{html.escape(f.default)}</textarea>"
            )
        elif f.type == FieldType.CHECKBOX:
            parts.append(f"<input type='checkbox' id='{f.name}' name='{f.name}'{req_attr}>")
        elif f.type == FieldType.DROPDOWN:
            opts = "".join(f"<option>{html.escape(o)}</option>" for o in f.options)
            parts.append(f"<select id='{f.name}' name='{f.name}'{req_attr}>{opts}</select>")
        elif f.type == FieldType.RADIO:
            parts.append("<div class='radio'>")
            for i, o in enumerate(f.options or ["Option"]):
                oid = f"{f.name}_{i}"
                parts.append(
                    f"<label><input type='radio' id='{oid}' name='{f.name}' "
                    f"value='{html.escape(o)}'{req_attr}> {html.escape(o)}</label>"
                )
            parts.append("</div>")
        elif f.type == FieldType.DATE:
            parts.append(f"<input type='date' id='{f.name}' name='{f.name}'{val}{req_attr}>")
        elif f.type == FieldType.EMAIL:
            parts.append(f"<input type='email' id='{f.name}' name='{f.name}'{ph}{val}{req_attr}>")
        elif f.type == FieldType.NUMBER:
            parts.append(f"<input type='number' id='{f.name}' name='{f.name}'{ph}{val}{req_attr}>")
        elif f.type == FieldType.PASSWORD:
            parts.append(f"<input type='password' id='{f.name}' name='{f.name}'{ph}{req_attr}>")
        elif f.type == FieldType.TEL:
            parts.append(f"<input type='tel' id='{f.name}' name='{f.name}'{ph}{val}{req_attr}>")
        elif f.type == FieldType.FILE:
            parts.append(f"<input type='file' id='{f.name}' name='{f.name}'{req_attr}>")
        elif f.type == FieldType.SIGNATURE:
            parts.append(f"<div class='sig' id='{f.name}' title='Unterschrift'></div>")
            parts.append(f"<input type='hidden' name='{f.name}' value=''>")
        else:
            parts.append(f"<input type='text' id='{f.name}' name='{f.name}'{ph}{val}{req_attr}>")
    parts.append("<p><button type='submit'>Absenden</button></p>")
    parts.append("</form></body></html>")
    path.write_text("\n".join(parts), encoding="utf-8")
    return path


def export_pdf_form(form: FormDefinition, path: str | Path) -> Path:
    """Einfaches PDF-Formular (Text-Darstellung + Hinweis auf HTML für interaktiv)."""
    path = Path(path)
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as e:
        raise RuntimeError(f"PDF-Export benötigt Pillow: {e}") from e

    w, h = 595, 842
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 16)
        font_sm = ImageFont.truetype("DejaVuSans.ttf", 12)
    except Exception:
        font = ImageFont.load_default()
        font_sm = font

    y = 40
    draw.text((40, y), form.title, fill="black", font=font)
    y += 28
    if form.description:
        draw.text((40, y), form.description[:80], fill="#444", font=font_sm)
        y += 22
    for f in form.fields:
        label = f"{f.label}" + (" *" if f.required else "")
        draw.text((40, y), f"[{f.type.value}] {label}", fill="black", font=font_sm)
        y += 18
        if f.type == FieldType.SIGNATURE:
            draw.line([40, y + 28, w - 40, y + 28], fill="black", width=1)
            y += 40
        elif f.type == FieldType.CHECKBOX:
            draw.rectangle([40, y, 54, y + 14], outline="black")
            y += 28
        elif f.type == FieldType.RADIO and f.options:
            for o in f.options[:5]:
                draw.ellipse([40, y, 52, y + 12], outline="black")
                draw.text((58, y), o, fill="#333", font=font_sm)
                y += 18
            y += 8
        else:
            draw.rectangle([40, y, w - 40, y + 22], outline="black")
            hint = ""
            if f.type == FieldType.DROPDOWN and f.options:
                hint = " / ".join(f.options[:4])
            elif f.placeholder:
                hint = f.placeholder
            if hint:
                draw.text((44, y + 4), hint, fill="#666", font=font_sm)
            y += 36
        if y > h - 60:
            draw.text((40, y), "… weitere Felder im HTML-Export", fill="#888", font=font_sm)
            break
    draw.text((40, h - 40), "InstantLens Doc — Formular-Export", fill="#888", font=font_sm)

    img.save(path, "PDF", resolution=72.0)
    return path
