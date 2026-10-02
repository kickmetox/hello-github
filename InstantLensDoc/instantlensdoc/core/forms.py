"""Formulargenerator: Felder definieren, HTML/PDF-Export."""

from __future__ import annotations

import html
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import List
from uuid import uuid4


class FieldType(str, Enum):
    TEXT = "text"
    TEXTAREA = "textarea"
    CHECKBOX = "checkbox"
    DROPDOWN = "dropdown"
    DATE = "date"


@dataclass
class FormField:
    label: str
    name: str = ""
    type: FieldType = FieldType.TEXT
    required: bool = False
    options: List[str] = field(default_factory=list)
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

    def add_field(self, field: FormField) -> FormField:
        self.fields.append(field)
        return field

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "fields": [
                {**asdict(f), "type": f.type.value}
                for f in self.fields
            ],
        }


def export_html(form: FormDefinition, path: str | Path) -> Path:
    path = Path(path)
    parts = [
        "<!DOCTYPE html>",
        "<html lang='de'><head><meta charset='utf-8'>",
        f"<title>{html.escape(form.title)}</title>",
        "<style>body{font-family:sans-serif;max-width:640px;margin:2rem auto}"
        "label{display:block;margin:.75rem 0 .25rem}input,select,textarea{width:100%;padding:.4rem}"
        ".req{color:#a00}</style></head><body>",
        f"<h1>{html.escape(form.title)}</h1>",
        "<form method='post' action='#'>",
    ]
    for f in form.fields:
        req = " <span class='req'>*</span>" if f.required else ""
        parts.append(f"<label for='{f.name}'>{html.escape(f.label)}{req}</label>")
        if f.type == FieldType.TEXTAREA:
            parts.append(f"<textarea id='{f.name}' name='{f.name}' rows='4'></textarea>")
        elif f.type == FieldType.CHECKBOX:
            parts.append(f"<input type='checkbox' id='{f.name}' name='{f.name}'>")
        elif f.type == FieldType.DROPDOWN:
            opts = "".join(f"<option>{html.escape(o)}</option>" for o in f.options)
            parts.append(f"<select id='{f.name}' name='{f.name}'>{opts}</select>")
        elif f.type == FieldType.DATE:
            parts.append(f"<input type='date' id='{f.name}' name='{f.name}'>")
        else:
            parts.append(f"<input type='text' id='{f.name}' name='{f.name}'>")
    parts.append("<p><button type='submit'>Absenden</button></p>")
    parts.append("</form></body></html>")
    path.write_text("\n".join(parts), encoding="utf-8")
    return path


def export_pdf_form(form: FormDefinition, path: str | Path) -> Path:
    """Einfaches PDF-Formular (Text-Darstellung + Hinweis auf HTML für interaktiv)."""
    path = Path(path)
    try:
        from PIL import Image, ImageDraw, ImageFont
        import pypdfium2 as pdfium
    except ImportError as e:
        raise RuntimeError(f"PDF-Export benötigt Pillow/pypdfium2: {e}") from e

    # Seite als Bild zeichnen und als Einzelseiten-PDF speichern
    w, h = 595, 842  # A4 @ 72dpi-ish
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
    y += 36
    for f in form.fields:
        label = f"{f.label}" + (" *" if f.required else "")
        draw.text((40, y), label, fill="black", font=font_sm)
        y += 20
        draw.rectangle([40, y, w - 40, y + 22], outline="black")
        if f.type == FieldType.DROPDOWN and f.options:
            draw.text((44, y + 4), " / ".join(f.options[:4]), fill="#666", font=font_sm)
        y += 36
        if y > h - 60:
            break
    draw.text((40, h - 40), "InstantLens Doc — Formular-Export", fill="#888", font=font_sm)

    # Über pypdfium2 / pikepdf: PNG → PDF via Pillow
    img.save(path, "PDF", resolution=72.0)
    return path
