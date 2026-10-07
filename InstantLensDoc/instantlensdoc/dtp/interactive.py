"""Interaktives PDF: Textfelder, Combobox, Präsentationsmodus."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4


def _nid() -> str:
    return uuid4().hex[:8]


@dataclass
class DtpWidget:
    id: str = field(default_factory=_nid)
    kind: str = "text"  # text | combo | button
    frame_id: str = ""
    name: str = "feld"
    value: str = ""
    options: list[str] = field(default_factory=list)
    page: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "frame_id": self.frame_id,
            "name": self.name,
            "value": self.value,
            "options": list(self.options),
            "page": self.page,
        }


def attach_widgets_to_pdf(pdf_path: str | Path, widgets: list[DtpWidget], frames: list[Any]) -> Path:
    """Hängt AcroForm-Felder an ein bestehendes PDF (pikepdf)."""
    dest = Path(pdf_path)
    if not widgets:
        return dest
    import pikepdf
    from pikepdf import Array, Dictionary, Name

    by_id = {getattr(f, "id", ""): f for f in frames}
    with pikepdf.open(dest, allow_overwriting_input=True) as pdf:
        fields = []
        for w in widgets:
            fr = by_id.get(w.frame_id)
            page_i = int(w.page if fr is None else fr.page)
            if page_i < 0 or page_i >= len(pdf.pages):
                continue
            page = pdf.pages[page_i]
            mb = page.mediabox
            ph = float(mb[3])
            x = float(getattr(fr, "x", 36) if fr else 36)
            y = float(getattr(fr, "y", 36) if fr else 36)
            ww = float(getattr(fr, "width", 120) if fr else 120)
            hh = float(getattr(fr, "height", 24) if fr else 24)
            # PDF y von unten
            rect = [x, ph - y - hh, x + ww, ph - y]
            ft = Name.Tx
            if w.kind == "combo":
                ft = Name.Ch
            annot = Dictionary(
                Type=Name.Annot,
                Subtype=Name.Widget,
                FT=ft,
                T=pikepdf.String(w.name or w.id),
                V=pikepdf.String(w.value or ""),
                Rect=rect,
                F=4,
            )
            if w.kind == "combo" and w.options:
                annot[Name.Ff] = 131072  # combo
                annot[Name.Opt] = Array([pikepdf.String(o) for o in w.options])
            annots = page.get("/Annots")
            if annots is None:
                page.Annots = [annot]
            else:
                annots.append(annot)
            fields.append(annot)
        if fields:
            form = pdf.Root.get("/AcroForm")
            if form is None:
                pdf.Root.AcroForm = Dictionary(Fields=Array(fields), NeedAppearances=True)
            else:
                existing = form.get("/Fields") or []
                form.Fields = Array(list(existing) + fields)
                form.NeedAppearances = True
            pdf.Root.PageMode = Name.FullScreen if any(
                w.kind == "button" and w.name == "presentation" for w in widgets
            ) else pdf.Root.get("/PageMode", Name.UseNone)
        pdf.save(dest)
    return dest
