"""Scribus-ähnliches Native-XML (.sla) — genug zum Wiederherstellen von Seiten/Rahmen."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring, fromstring


def export_sla(doc: Any, path: str | Path) -> Path:
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    g = doc.geometry
    root = Element("SCRIBUSUTF8NEW", {"Version": "1.5.8"})
    document = SubElement(
        root,
        "DOCUMENT",
        {
            "ANNAME": doc.title or "InstantLens Doc",
            "PAGEWIDTH": f"{g.width_pt:.4f}",
            "PAGEHEIGHT": f"{g.height_pt:.4f}",
            "BORDERLEFT": f"{g.margin_left_pt:.4f}",
            "BORDERRIGHT": f"{g.margin_right_pt:.4f}",
            "BORDERTOP": f"{g.margin_top_pt:.4f}",
            "BORDERBOTTOM": f"{g.margin_bottom_pt:.4f}",
            "BleedTop": f"{g.bleed_pt:.4f}",
            "BleedLeft": f"{g.bleed_pt:.4f}",
            "BleedRight": f"{g.bleed_pt:.4f}",
            "BleedBottom": f"{g.bleed_pt:.4f}",
            "PAGES": str(doc.page_count),
        },
    )
    for i in range(max(1, doc.page_count)):
        SubElement(
            document,
            "PAGE",
            {"NUM": str(i), "Size": g.name or "Custom"},
        )
    for ly in doc.layers:
        SubElement(
            document,
            "LAYERS",
            {
                "NAME": ly.name,
                "NUMMER": ly.id,
                "SICHTBAR": "1" if ly.visible else "0",
                "LEVEL": str(ly.z),
                "BLEND": str(getattr(ly, "blend_mode", "normal") or "normal"),
                "TRANS": f"{float(getattr(ly, 'opacity', 1.0) or 1.0):.3f}",
            },
        )
    ptype = {"text": "4", "image": "2", "render": "2", "shape": "6"}
    for fr in doc.frames:
        po = SubElement(
            document,
            "PAGEOBJECT",
            {
                "OwnPage": str(fr.page),
                "PTYPE": ptype.get(fr.kind, "6"),
                "XPOS": f"{fr.x:.4f}",
                "YPOS": f"{fr.y:.4f}",
                "WIDTH": f"{fr.width:.4f}",
                "HEIGHT": f"{fr.height:.4f}",
                "ITEMNAME": fr.id,
                "ANNAME": fr.id,
                "PFILE": fr.image_path or "",
                "KIND": fr.kind,
                "LOCALSCX": "1",
                "LOCALSCY": "1",
            },
        )
        if fr.kind == "text" and (fr.text or ""):
            story = SubElement(po, "StoryText")
            it = SubElement(story, "ITEXT", {"CH": fr.text})
            it.text = ""
    xml = b'<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root, encoding="utf-8")
    dest.write_bytes(xml)
    return dest


def import_sla(path: str | Path, doc: Any | None = None) -> Any:
    from instantlensdoc.dtp.model import DtpDocument

    raw = Path(path).read_bytes()
    root = fromstring(raw)
    if root.tag != "SCRIBUSUTF8NEW":
        raise ValueError("Keine Scribus-SLA-Datei (SCRIBUSUTF8NEW fehlt)")
    document = root.find("DOCUMENT")
    if document is None:
        raise ValueError("SLA ohne DOCUMENT")
    d = doc or DtpDocument()
    d.title = document.get("ANNAME") or d.title
    try:
        d.geometry.width_pt = float(document.get("PAGEWIDTH") or d.geometry.width_pt)
        d.geometry.height_pt = float(document.get("PAGEHEIGHT") or d.geometry.height_pt)
        d.geometry.margin_left_pt = float(document.get("BORDERLEFT") or 0) or d.geometry.margin_left_pt
        d.geometry.margin_right_pt = float(document.get("BORDERRIGHT") or 0) or d.geometry.margin_right_pt
        d.geometry.margin_top_pt = float(document.get("BORDERTOP") or 0) or d.geometry.margin_top_pt
        d.geometry.margin_bottom_pt = float(document.get("BORDERBOTTOM") or 0) or d.geometry.margin_bottom_pt
        d.geometry.bleed_pt = float(document.get("BleedTop") or d.geometry.bleed_pt)
        d.page_count = max(1, int(document.get("PAGES") or 1))
    except Exception:
        pass
    d.frames = [f for f in d.frames if f.master]
    for po in document.findall("PAGEOBJECT"):
        ptype = po.get("PTYPE") or "4"
        x = float(po.get("XPOS") or 40)
        y = float(po.get("YPOS") or 40)
        w = float(po.get("WIDTH") or 120)
        h = float(po.get("HEIGHT") or 60)
        page = int(po.get("OwnPage") or 0)
        kind_attr = (po.get("KIND") or "").lower()
        pfile = po.get("PFILE") or ""
        if ptype == "4" or kind_attr == "text":
            ch = ""
            it = po.find("StoryText/ITEXT")
            if it is not None:
                ch = it.get("CH") or (it.text or "")
            d.add_text_frame(ch, x=x, y=y, width=w, height=h, page=page)
        elif kind_attr == "render" or (
            ptype == "2" and Path(pfile).suffix.lower() in (".ai", ".eps", ".pdf")
        ):
            d.add_render_frame(pfile, x=x, y=y, width=w, height=h, page=page)
        elif ptype == "2" or kind_attr == "image":
            d.add_image_frame(pfile, x=x, y=y, width=w, height=h, page=page)
        else:
            d.add_shape("rectangle", x=x, y=y, width=w, height=h, page=page)
    d.page_count = max(d.page_count, 1)
    d._sync_page_master()
    return d
