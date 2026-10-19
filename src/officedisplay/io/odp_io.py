from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from officedisplay.model.presentation import Background, Presentation, Slide, SlideObject, flatten, new_id


def export_odp(presentation: Presentation, path: str | Path) -> None:
    content = _content_xml(presentation)
    manifest = """<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0">
 <manifest:file-entry manifest:media-type="application/vnd.oasis.opendocument.presentation" manifest:full-path="/"/>
 <manifest:file-entry manifest:media-type="text/xml" manifest:full-path="content.xml"/>
</manifest:manifest>
"""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("mimetype", "application/vnd.oasis.opendocument.presentation", compress_type=zipfile.ZIP_STORED)
        archive.writestr("content.xml", content)
        archive.writestr("META-INF/manifest.xml", manifest)


def _content_xml(presentation: Presentation) -> str:
    pages = []
    for slide in presentation.slides:
        frames = []
        for obj, x, y, w, h in flatten(slide):
            sx, sy = x * presentation.width, y * presentation.height
            sw, sh = max(w, 0.01) * presentation.width, max(h, 0.01) * presentation.height
            if obj.kind == "text":
                lines = "".join(f"<text:p>{escape(line)}</text:p>" for line in str(obj.props.get("text") or "").splitlines()) or "<text:p/>"
                frames.append(
                    f'<draw:frame draw:name="{escape(obj.name or obj.id)}" svg:x="{sx:.0f}" svg:y="{sy:.0f}" svg:width="{sw:.0f}" svg:height="{sh:.0f}"><draw:text-box>{lines}</draw:text-box></draw:frame>'
                )
            elif obj.kind == "shape":
                frames.append(
                    f'<draw:rect svg:x="{sx:.0f}" svg:y="{sy:.0f}" svg:width="{sw:.0f}" svg:height="{sh:.0f}" draw:fill-color="{escape(obj.props.get("fill") or "#0B63E5")}"/>'
                )
        pages.append(
            f'<draw:page draw:name="{escape(slide.name)}">{"".join(frames)}<presentation:notes><draw:text-box><text:p>{escape(slide.notes or "")}</text:p></draw:text-box></presentation:notes></draw:page>'
        )
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" xmlns:presentation="urn:oasis:names:tc:opendocument:xmlns:presentation:1.0">
 <office:body><office:presentation>{"".join(pages)}</office:presentation></office:body>
</office:document-content>
'''


def import_odp(path: str | Path) -> Presentation:
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("content.xml").decode("utf-8", errors="replace")
    presentation = Presentation(title=Path(path).stem)
    presentation.slides = []
    for match in re.finditer(r"<draw:page\b([^>]*)>(.*?)</draw:page>", xml, re.DOTALL):
        body = match.group(2)
        name_match = re.search(r'draw:name="([^"]*)"', match.group(1))
        slide = Slide(id=new_id(), name=name_match.group(1) if name_match else "Folie", background=Background())
        notes = re.search(r"<presentation:notes>.*?<text:p>(.*?)</text:p>", body, re.DOTALL)
        if notes:
            slide.notes = _unescape(re.sub(r"<[^>]+>", "", notes.group(1)))
        for frame in re.finditer(r"<draw:frame\b([^>]*)>(.*?)</draw:frame>", body, re.DOTALL):
            attrs, inner = frame.group(1), frame.group(2)
            texts = [_unescape(re.sub(r"<[^>]+>", "", item)) for item in re.findall(r"<text:p>(.*?)</text:p>", inner, re.DOTALL)]
            slide.objects.append(
                SlideObject(
                    id=new_id(),
                    kind="text",
                    x=_attr(attrs, "svg:x") / presentation.width,
                    y=_attr(attrs, "svg:y") / presentation.height,
                    w=max(0.05, _attr(attrs, "svg:width") / presentation.width),
                    h=max(0.05, _attr(attrs, "svg:height") / presentation.height),
                    props={"text": "\n".join(texts), "font_size": 20, "color": "#1B1F2A", "font_family": "Calibri"},
                )
            )
        presentation.slides.append(slide)
    if not presentation.slides:
        presentation.slides.append(Slide(id=new_id(), name="Folie 1"))
    return presentation


def _attr(attrs: str, name: str) -> float:
    match = re.search(rf'{name}="([0-9.]+)"', attrs)
    return float(match.group(1)) if match else 0.0


def _unescape(text: str) -> str:
    return (
        text.replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&amp;", "&")
    )
