from __future__ import annotations

import re
import tempfile
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


# OASIS OpenDocument 1.3 Teil 3: eine Folie ist draw:page in office:presentation.
# svg:x/y/width/height sind Längen (cm, mm, in, pt, pc, px). Die Seite kommt aus
# style:page-layout, fo:page-width und fo:page-height. Beschreibung: docs/FORMATE.md.
_LENGTH = re.compile(r"^\s*(-?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))\s*(cm|mm|in|pt|pc|px)?\s*$")
_TO_CM = {"cm": 1.0, "mm": 0.1, "in": 2.54, "pt": 2.54 / 72.0, "pc": 2.54 / 6.0, "px": 2.54 / 96.0}
_SHAPE_TAGS = {"frame", "custom-shape", "rect", "polygon", "circle", "ellipse", "path", "connector", "line"}


def import_odp(path: str | Path) -> Presentation:
    source = Path(path)
    with zipfile.ZipFile(source) as archive:
        names = {item.replace("\\", "/"): item for item in archive.namelist()}
        content = _xml(archive, names, "content.xml")
        styles_root = _xml(archive, names, "styles.xml")
        presentation = Presentation(title=source.stem)
        presentation.slides = []
        if content is None:
            presentation.slides.append(Slide(id=new_id(), name="Folie 1"))
            return presentation
        bag = _style_bag(content, styles_root)
        body = _first(content, "presentation")
        pages = [child for child in list(body) if _local(child.tag) == "page"] if body is not None else []
        page_w, page_h, physical = _page_size(pages, bag)
        if physical and page_w > 0 and page_h > 0:
            presentation.width = 1920
            presentation.height = max(1, int(round(1920 * page_h / page_w)))
        media = Path(tempfile.mkdtemp(prefix="officedisplay-odp-"))
        for page in pages:
            width, height, page_physical = _page_size([page], bag)
            if not page_physical:
                width, height = page_w, page_h
            slide = Slide(
                id=new_id(),
                name=_qattr(page, "name") or "Folie",
                background=_page_background(page, bag, archive, names, media),
            )
            _walk_page(page, slide, width, height, archive, names, media, bag["styles"])
            _promote_full_bleed(slide)
            presentation.slides.append(slide)
    if not presentation.slides:
        presentation.slides.append(Slide(id=new_id(), name="Folie 1"))
    return presentation


def _xml(archive, names: dict[str, str], norm: str):
    import xml.etree.ElementTree as ET

    original = names.get(norm)
    if original is None:
        lowered = {key.lower(): value for key, value in names.items()}
        original = lowered.get(norm.lower())
    if original is None:
        return None
    try:
        return ET.fromstring(archive.read(original))
    except ET.ParseError:
        return None


def _local(tag: str) -> str:
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


def _qattr(element, name: str) -> str | None:
    if element is None:
        return None
    for key, value in element.attrib.items():
        if key == name or key.endswith("}" + name):
            return value
    return None


def _first(element, name: str):
    if element is None:
        return None
    for node in element.iter():
        if _local(node.tag) == name:
            return node
    return None


def _child(element, name: str):
    if element is None:
        return None
    for child in element:
        if _local(child.tag) == name:
            return child
    return None


def _parse_length(raw: str | None) -> tuple[float, bool] | None:
    if not raw:
        return None
    match = _LENGTH.match(raw)
    if not match:
        return None
    number = float(match.group(1))
    unit = match.group(2)
    if not unit:
        return number, False
    return number * _TO_CM[unit], True


def _style_bag(content, styles_root) -> dict:
    bag = {"layouts": {}, "masters": {}, "images": {}, "styles": {}}
    for root in (styles_root, content):
        if root is None:
            continue
        for element in root.iter():
            name = _local(element.tag)
            style_name = _qattr(element, "name")
            if name == "page-layout" and style_name:
                props = _child(element, "page-layout-properties")
                width = _parse_length(_qattr(props, "page-width"))
                height = _parse_length(_qattr(props, "page-height"))
                if width and height and width[1] and height[1]:
                    bag["layouts"][style_name] = (width[0], height[0])
            elif name == "master-page" and style_name:
                bag["masters"][style_name] = {
                    "layout": _qattr(element, "page-layout-name"),
                    "style": _qattr(element, "style-name"),
                }
            elif name == "fill-image" and style_name:
                href = _qattr(element, "href")
                if href:
                    bag["images"][style_name] = href
            elif name == "style" and style_name:
                bag["styles"][style_name] = element
    return bag


def _page_size(pages, bag) -> tuple[float, float, bool]:
    for page in pages:
        master = bag["masters"].get(_qattr(page, "master-page-name") or "")
        layout_name = master.get("layout") if master else None
        if layout_name and layout_name in bag["layouts"]:
            width, height = bag["layouts"][layout_name]
            return width, height, True
    if bag["layouts"]:
        width, height = next(iter(bag["layouts"].values()))
        return width, height, True
    return 1920.0, 1080.0, False


def _page_background(page, bag, archive, names, media: Path) -> Background:
    """Folienhintergrund: Zeichenformat der Seite, sonst das der Masterseite."""
    names_to_try = []
    if _qattr(page, "style-name"):
        names_to_try.append(_qattr(page, "style-name"))
    master = bag["masters"].get(_qattr(page, "master-page-name") or "")
    if master and master.get("style"):
        names_to_try.append(master["style"])
    for style_name in names_to_try:
        style = bag["styles"].get(style_name or "")
        props = _child(style, "drawing-page-properties")
        if props is None:
            props = _child(style, "graphic-properties")
        if props is None:
            continue
        fill = (_qattr(props, "fill") or "").lower()
        if fill == "bitmap":
            href = bag["images"].get(_qattr(props, "fill-image-name") or "")
            saved = _extract_image(archive, names, href, media)
            if saved:
                return Background(mode="image", image=saved, fit="cover", color="#FFFFFF")
        if fill == "solid":
            color = _hex(_qattr(props, "fill-color"))
            if color:
                return Background(mode="solid", color=color)
    return Background()


def _walk_page(page, slide: Slide, page_w: float, page_h: float, archive, names, media: Path, styles: dict) -> None:
    for child in page:
        name = _local(child.tag)
        if name == "notes":
            slide.notes = _paragraphs(child)
            continue
        if name == "g":
            _walk_page(child, slide, page_w, page_h, archive, names, media, styles)
            continue
        if name not in _SHAPE_TAGS:
            continue
        _take_shape(child, slide, page_w, page_h, archive, names, media, styles)


def _take_shape(element, slide: Slide, page_w: float, page_h: float, archive, names, media: Path, styles: dict) -> None:
    box = _box(element, page_w, page_h)
    images = [node for node in element.iter() if _local(node.tag) == "image"]
    text = _paragraphs(element)
    if box is None:
        return
    x, y, w, h = box
    for image in images:
        saved = _extract_image(archive, names, _qattr(image, "href"), media)
        if not saved:
            continue
        slide.objects.append(
            SlideObject(id=new_id(), kind="image", x=x, y=y, w=w, h=h, name=_qattr(element, "name") or "", props={"path": saved})
        )
    if text:
        slide.objects.append(
            SlideObject(
                id=new_id(),
                kind="text",
                x=x,
                y=y,
                w=w,
                h=h,
                name=_qattr(element, "name") or "",
                props={
                    "text": text,
                    "font_size": _font_size(element, styles),
                    "color": "#1B1F2A",
                    "font_family": "Calibri",
                },
            )
        )


def _box(element, page_w: float, page_h: float):
    raw = [_parse_length(_qattr(element, name)) for name in ("x", "y", "width", "height")]
    if any(item is None for item in raw) or page_w <= 0 or page_h <= 0:
        return None
    x, y, w, h = (item[0] for item in raw)
    if w <= 0 or h <= 0:
        return None
    return (x / page_w, y / page_h, w / page_w, h / page_h)


def _paragraphs(element) -> str:
    lines = []
    for node in element.iter():
        if _local(node.tag) != "p":
            continue
        if _inside_notes(node, element):
            continue
        line = _inline_text(node).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def _inside_notes(node, stop) -> bool:
    parent = node
    while parent is not None and parent is not stop:
        if _local(parent.tag) == "notes":
            return True
        parent = _parent_of(parent)
    return False


def _parent_of(node):
    parent = getattr(node, "getparent", None)
    if parent is None:
        return None
    try:
        return parent()
    except TypeError:
        return None


def _inline_text(node) -> str:
    chunks = [node.text or ""]
    for child in node:
        name = _local(child.tag)
        if name == "line-break":
            chunks.append("\n")
        elif name == "tab":
            chunks.append("\t")
        elif name == "s":
            try:
                count = int(_qattr(child, "c") or "1")
            except ValueError:
                count = 1
            chunks.append(" " * max(1, count))
        else:
            chunks.append(_inline_text(child))
        chunks.append(child.tail or "")
    return "".join(chunks)


def _font_size(element, styles: dict) -> int:
    for node in element.iter():
        if _local(node.tag) != "p":
            continue
        style = styles.get(_qattr(node, "style-name") or "")
        props = _child(style, "text-properties")
        parsed = _parse_length(_qattr(props, "font-size"))
        if parsed and parsed[1] and parsed[0] > 0:
            points = parsed[0] / _TO_CM["pt"]
            return max(8, min(96, int(round(points))))
    return 20


def _extract_image(archive, names: dict[str, str], href: str | None, media: Path) -> str | None:
    from urllib.parse import unquote

    if not href or href.startswith("#"):
        return None
    target = unquote(href.replace("\\", "/").split("?", 1)[0].lstrip("./"))
    original = names.get(target)
    if original is None:
        lowered = {key.lower(): value for key, value in names.items()}
        original = lowered.get(target.lower())
    if original is None:
        return None
    try:
        blob = archive.read(original)
    except KeyError:
        return None
    suffix = Path(target).suffix.lower() or ".png"
    if suffix not in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp"}:
        suffix = ".png"
    path = media / f"{new_id()}{suffix}"
    try:
        path.write_bytes(blob)
    except OSError:
        return None
    return str(path)


def _hex(raw: str | None) -> str | None:
    if not raw:
        return None
    text = raw.strip()
    if text.startswith("#"):
        text = text[1:]
    if len(text) >= 6 and all(ch in "0123456789abcdefABCDEF" for ch in text[:6]):
        return "#" + text[:6].upper()
    return None


def _promote_full_bleed(slide: Slide) -> None:
    """Ein Bild über fast die ganze Seite ist der Folienhintergrund und bleibt Objekt."""
    if slide.background.mode == "image" and slide.background.image:
        return
    for obj in slide.objects:
        if obj.kind != "image":
            continue
        if obj.x < 0.05 and obj.y < 0.05 and obj.w > 0.9 and obj.h > 0.9:
            path = obj.props.get("path")
            if path:
                slide.background.mode = "image"
                slide.background.image = str(path)
                slide.background.fit = "cover"
            return
