from __future__ import annotations

import tempfile
from pathlib import Path

from officedisplay.model.presentation import (
    Background,
    Presentation,
    Slide,
    SlideObject,
    flatten,
    new_id,
)


EMU_PER_PIXEL = 9525  # 96 dpi


def _emu(value: float) -> int:
    return int(value * EMU_PER_PIXEL)


def export_pptx(presentation: Presentation, path: str | Path) -> None:
    from pptx import Presentation as PptxPresentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Emu

    package = PptxPresentation()
    package.slide_width = Emu(_emu(presentation.width))
    package.slide_height = Emu(_emu(presentation.height))
    blank = package.slide_layouts[6]
    shapes = {
        "rect": MSO_SHAPE.RECTANGLE,
        "roundrect": MSO_SHAPE.ROUNDED_RECTANGLE,
        "ellipse": MSO_SHAPE.OVAL,
        "triangle": MSO_SHAPE.ISOSCELES_TRIANGLE,
        "diamond": MSO_SHAPE.DIAMOND,
        "arrow": MSO_SHAPE.RIGHT_ARROW,
        "star": MSO_SHAPE.STAR_5_POINT,
        "line": MSO_SHAPE.LINE_INVERSE,
    }
    aligns = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}
    for slide in presentation.slides:
        page = package.slides.add_slide(blank)
        _paint_background(page, slide, presentation)
        for obj, x, y, w, h in flatten(slide):
            left, top, width, height = Emu(_emu(x * presentation.width)), Emu(_emu(y * presentation.height)), Emu(_emu(max(w, 0.01) * presentation.width)), Emu(_emu(max(h, 0.01) * presentation.height))
            if obj.kind == "text":
                box = page.shapes.add_textbox(left, top, width, height)
                frame = box.text_frame
                frame.word_wrap = True
                box.text_frame.paragraphs[0].text = str(obj.props.get("text") or "")
                paragraph = frame.paragraphs[0]
                paragraph.alignment = aligns.get(obj.props.get("align") or "left", PP_ALIGN.LEFT)
                font = paragraph.font
                font.size = _pt(obj.props.get("font_size") or 18)
                font.bold = bool(obj.props.get("bold"))
                font.italic = bool(obj.props.get("italic"))
                font.underline = bool(obj.props.get("underline"))
                font.name = obj.props.get("font_family") or "Calibri"
                font.color.rgb = _rgb(obj.props.get("color") or "#1B1F2A")
                if obj.name:
                    box.name = obj.name
            elif obj.kind == "image" and obj.props.get("path") and Path(obj.props["path"]).is_file():
                picture = page.shapes.add_picture(obj.props["path"], left, top, width, height)
                if obj.name:
                    picture.name = obj.name
            elif obj.kind == "shape":
                kind = shapes.get(obj.props.get("shape") or "rect", MSO_SHAPE.RECTANGLE)
                shape = page.shapes.add_shape(kind, left, top, width, height)
                shape.fill.solid()
                shape.fill.fore_color.rgb = _rgb(obj.props.get("fill") or "#0B63E5")
                if obj.name:
                    shape.name = obj.name
            elif obj.kind == "chart":
                _chart(page, obj, left, top, width, height)
        if slide.notes:
            notes = page.notes_slide
            notes.notes_text_frame.text = slide.notes
    package.save(str(path))


def _pt(size: int):
    from pptx.util import Pt

    return Pt(max(8, min(int(size), 96)))


def _rgb(color: str):
    from pptx.dml.color import RGBColor

    hex_color = (color or "#000000").replace("#", "")
    if len(hex_color) == 8:
        hex_color = hex_color[2:]
    if len(hex_color) != 6:
        hex_color = "000000"
    return RGBColor(int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


def _paint_background(page, slide: Slide, presentation: Presentation) -> None:
    fill = page.background.fill
    fill.solid()
    fill.fore_color.rgb = _rgb(slide.background.color or "#FFFFFF")


def _chart(page, obj, left, top, width, height) -> None:
    from pptx.chart.data import CategoryChartData
    from pptx.enum.chart import XL_CHART_TYPE

    data = CategoryChartData()
    data.categories = obj.props.get("categories") or ["A", "B"]
    for serie in obj.props.get("series") or [{"name": "Werte", "values": [1, 2]}]:
        data.add_series(serie.get("name") or "Werte", serie.get("values") or [0])
    chart_type = XL_CHART_TYPE.COLUMN_CLUSTERED
    if obj.props.get("chart_type") == "pie":
        chart_type = XL_CHART_TYPE.PIE
    elif obj.props.get("chart_type") == "line":
        chart_type = XL_CHART_TYPE.LINE
    page.shapes.add_chart(chart_type, left, top, width, height, data)


class PptxReadError(ValueError):
    """Die Datei ist keine lesbare PowerPoint-Präsentation."""


_ENCRYPTED_MESSAGE = "Die Datei ist verschlüsselt und lässt sich hier nicht öffnen."
_R_ID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
_R_EMBED = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
_PRESET_KIND = {
    "rect": "rect",
    "roundRect": "roundrect",
    "ellipse": "ellipse",
    "triangle": "triangle",
    "diamond": "diamond",
    "rightArrow": "arrow",
    "star5": "star",
    "line": "line",
    "straightConnector1": "line",
}


def import_pptx(path: str | Path, media_dir: str | Path | None = None) -> Presentation:
    source = Path(path)
    try:
        return _import_pptx(source, media_dir)
    except PptxReadError:
        raise
    except Exception as exc:
        raise PptxReadError(_failure_message(source)) from exc


def _import_pptx(source: Path, media_dir: str | Path | None) -> Presentation:
    if not source.is_file():
        raise PptxReadError(f"Die Datei lässt sich nicht laden.\n{source.name}\nkein ZIP")
    if _looks_encrypted(source):
        raise PptxReadError(_ENCRYPTED_MESSAGE)
    media = {"folder": None, "hint": media_dir, "source": source}
    package = _open_package(source)
    if package is not None:
        try:
            presentation = _from_package(package, source, media)
        except Exception:
            presentation = None
        else:
            if presentation.slides:
                return presentation
    presentation = _from_zip(source, media)
    if presentation is not None and presentation.slides:
        return presentation
    raise PptxReadError(_failure_message(source))


def _open_package(source: Path):
    """python-pptx öffnet das Paket. Schlägt das fehl, liest der ZIP-Fallback."""
    try:
        from pptx import Presentation as PptxPresentation

        return PptxPresentation(str(source))
    except Exception:
        return None


def _from_package(package, source: Path, media: dict) -> Presentation:
    try:
        slide_w = float(package.slide_width or 12192000)
        slide_h = float(package.slide_height or 6858000)
    except Exception:
        slide_w, slide_h = 12192000.0, 6858000.0
    presentation = _blank_deck(source, slide_w, slide_h)
    # .slides benennt Teile um und liest jede rId. Eine fehlende Beziehung
    # oder ein sldId ohne r:id wirft hier, bevor die erste Folie ankommt.
    slides = package.slides
    count = len(slides)
    for index in range(count):
        slide = Slide(id=new_id(), name=f"Folie {index + 1}", background=Background(color="#FFFFFF"))
        try:
            page = slides[index]
        except Exception:
            presentation.slides.append(slide)
            continue
        try:
            notes = page.notes_slide.notes_text_frame.text
            slide.notes = notes or ""
        except Exception:
            slide.notes = ""
        try:
            _consume_page(page, slide, slide_w, slide_h, media)
        except Exception:
            pass
        presentation.slides.append(slide)
    if not presentation.slides:
        presentation.slides.append(Slide(id=new_id(), name="Folie 1"))
    return presentation


def _consume_page(page, slide: Slide, slide_w: float, slide_h: float, media: dict) -> None:
    shapes = getattr(page, "shapes", None)
    if shapes is None:
        return
    elements = None
    try:
        elements = list(shapes._iter_member_elms())
    except Exception:
        elements = None
    if elements is not None:
        for index, element in enumerate(elements):
            shape = None
            try:
                shape = shapes._shape_factory(element)
            except Exception:
                shape = None
            if shape is None:
                try:
                    shape = shapes[index]
                except Exception:
                    _take_xml_element(element, slide, slide_w, slide_h, (), None)
                    continue
            try:
                _take_shape(shape, slide, slide_w, slide_h, media)
            except Exception:
                _take_xml_element(element, slide, slide_w, slide_h, (), None)
        try:
            extras = _alternate_shapes(shapes)
        except Exception:
            extras = []
        for shape in extras:
            try:
                _take_shape(shape, slide, slide_w, slide_h, media)
            except Exception:
                continue
        return
    try:
        total = len(shapes)
    except Exception:
        _recover_page_blob(page, slide, slide_w, slide_h, media)
        return
    for index in range(total):
        try:
            shape = shapes[index]
        except Exception:
            continue
        try:
            _take_shape(shape, slide, slide_w, slide_h, media)
        except Exception:
            continue
    try:
        extras = _alternate_shapes(shapes)
    except Exception:
        extras = []
    for shape in extras:
        try:
            _take_shape(shape, slide, slide_w, slide_h, media)
        except Exception:
            continue


def _recover_page_blob(page, slide: Slide, slide_w: float, slide_h: float, media: dict) -> None:
    part = getattr(page, "part", None)
    blob = getattr(part, "blob", None)
    if not isinstance(blob, (bytes, bytearray)):
        return
    root = _parse_xml(bytes(blob))
    if root is None:
        return
    _fill_tree(root, slide, slide_w, slide_h, {}, None, None, media)


def _from_zip(source: Path, media: dict) -> Presentation | None:
    """Liest Folien direkt aus dem ZIP, nur wenn python-pptx das Paket nicht liefert."""
    import zipfile

    if not zipfile.is_zipfile(source):
        return None
    try:
        archive = zipfile.ZipFile(source)
    except Exception:
        return None
    with archive:
        names = _zip_names(archive)
        slide_names = _ordered_slide_names(archive, names)
        if not slide_names:
            return None
        slide_w, slide_h = _zip_slide_size(archive, names)
        presentation = _blank_deck(source, slide_w, slide_h)
        for index, slide_name in enumerate(slide_names, start=1):
            raw = _zip_bytes(archive, names, slide_name)
            root = _parse_xml(raw) if raw else None
            if root is None or _local(root.tag) != "sld":
                continue
            slide = Slide(id=new_id(), name=f"Folie {index}", background=Background(color="#FFFFFF"))
            rels = _rels_map(archive, names, _rels_name(slide_name))
            try:
                _fill_tree(root, slide, slide_w, slide_h, rels, archive, names, media, _parent_dir(slide_name))
                slide.notes = _zip_notes(archive, names, rels, _parent_dir(slide_name))
            except Exception:
                pass
            presentation.slides.append(slide)
        return presentation if presentation.slides else None


def _blank_deck(source: Path, slide_w: float, slide_h: float) -> Presentation:
    width = max(1, int(slide_w / EMU_PER_PIXEL))
    height = max(1, int(slide_h / EMU_PER_PIXEL))
    presentation = Presentation(title=source.stem, width=width, height=height)
    presentation.slides = []
    return presentation


def _failure_message(source: Path) -> str:
    if _looks_encrypted(source):
        return _ENCRYPTED_MESSAGE
    if _password_blocked(source):
        return f"Die Datei lässt sich nicht laden.\n{source.name}\nPasswort/verschlüsselt"
    import zipfile

    if not source.is_file() or not zipfile.is_zipfile(source):
        return f"Die Datei lässt sich nicht laden.\n{source.name}\nkein ZIP"
    return f"Die Datei lässt sich nicht laden.\n{source.name}\nleer"


def _looks_encrypted(source: Path) -> bool:
    import zipfile

    try:
        with source.open("rb") as handle:
            head = handle.read(8)
    except OSError:
        return False
    if head.startswith(b"PK"):
        try:
            with zipfile.ZipFile(source) as archive:
                for name in archive.namelist():
                    base = name.replace("\\", "/").rsplit("/", 1)[-1].lower()
                    if base in {"encryptedpackage", "encryptioninfo"}:
                        return True
        except RuntimeError as exc:
            text = str(exc).lower()
            return "password" in text or "encrypt" in text
        except zipfile.BadZipFile:
            return False
        return False
    try:
        with source.open("rb") as handle:
            blob = handle.read(2_000_000)
    except OSError:
        return False
    return b"EncryptedPackage" in blob or b"EncryptionInfo" in blob


def _password_blocked(source: Path) -> bool:
    import zipfile

    if not zipfile.is_zipfile(source):
        return False
    try:
        with zipfile.ZipFile(source) as archive:
            for info in archive.infolist():
                if info.flag_bits & 0x1:
                    return True
    except RuntimeError as exc:
        text = str(exc).lower()
        return "password" in text or "encrypt" in text
    except zipfile.BadZipFile:
        return False
    return False


def _parse_xml(blob: bytes | None):
    if not blob or not blob.strip():
        return None
    try:
        from lxml import etree

        parser = etree.XMLParser(recover=True, huge_tree=True)
        return etree.fromstring(blob, parser)
    except Exception:
        return None


def _local(tag: str) -> str:
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


def _zip_names(archive) -> dict[str, str]:
    found = {}
    for name in archive.namelist():
        norm = name.replace("\\", "/").lstrip("/")
        found.setdefault(norm, name)
    return found


def _zip_bytes(archive, names: dict[str, str], norm: str | None) -> bytes | None:
    if not norm:
        return None
    original = names.get(norm)
    if original is None:
        return None
    try:
        return archive.read(original)
    except Exception:
        return None


def _parent_dir(norm: str) -> str:
    if "/" not in norm:
        return ""
    return norm.rsplit("/", 1)[0]


def _rels_name(part: str) -> str:
    parent = _parent_dir(part)
    base = part.rsplit("/", 1)[-1]
    folder = f"{parent}/_rels" if parent else "_rels"
    return f"{folder}/{base}.rels"


def _resolve(base_dir: str, target: str) -> str | None:
    target = (target or "").replace("\\", "/").split("?", 1)[0]
    if not target or target.startswith("#"):
        return None
    if target.startswith("/"):
        parts = [bit for bit in target.split("/") if bit and bit != "."]
    else:
        parts = [bit for bit in base_dir.split("/") if bit]
        for bit in target.split("/"):
            if bit in {"", "."}:
                continue
            if bit == "..":
                if not parts:
                    return None
                parts.pop()
                continue
            parts.append(bit)
    if not parts:
        return None
    return "/".join(parts)


def _rels_map(archive, names: dict[str, str], rels_norm: str) -> dict[str, tuple[str, str]]:
    raw = _zip_bytes(archive, names, rels_norm)
    root = _parse_xml(raw) if raw else None
    found: dict[str, tuple[str, str]] = {}
    if root is None:
        return found
    for child in root.iter():
        if _local(child.tag) != "Relationship":
            continue
        rid = child.get("Id")
        target = child.get("Target")
        if not rid or not target or child.get("TargetMode") == "External":
            continue
        found[rid] = (child.get("Type") or "", target)
    return found


def _ordered_slide_names(archive, names: dict[str, str]) -> list[str]:
    rels = _rels_map(archive, names, "ppt/_rels/presentation.xml.rels")
    raw = _zip_bytes(archive, names, "ppt/presentation.xml")
    root = _parse_xml(raw) if raw else None
    slots: list[str | None] = []
    used: set[str] = set()
    if root is not None:
        for element in root.iter():
            if _local(element.tag) != "sldId":
                continue
            rid = element.get(_R_ID)
            if not rid:
                for key, value in element.attrib.items():
                    if isinstance(key, str) and key.endswith("}id") and "relationships" in key:
                        rid = value
                        break
            path = _resolve("ppt", rels[rid][1]) if rid and rid in rels else None
            if path and path in names and path not in used:
                slots.append(path)
                used.add(path)
            else:
                # Fehlende rId oder Ziel: Platz halten, Folie später aus dem ZIP füllen.
                slots.append(None)

    def sort_key(norm: str):
        digits = "".join(ch for ch in norm.rsplit("/", 1)[-1] if ch.isdigit())
        try:
            number = int(digits or "0")
        except ValueError:
            number = 0
        return (number, norm)

    extras = []
    for norm in names:
        if "/_rels/" in norm or norm in used:
            continue
        base = norm.rsplit("/", 1)[-1]
        if norm.startswith("ppt/slides/") and base.startswith("slide") and base.endswith(".xml"):
            extras.append(norm)
    extras.sort(key=sort_key)
    ordered: list[str] = []
    extra_index = 0
    for slot in slots:
        if slot is not None:
            ordered.append(slot)
            continue
        if extra_index < len(extras):
            ordered.append(extras[extra_index])
            extra_index += 1
    ordered.extend(extras[extra_index:])
    return ordered


def _zip_slide_size(archive, names: dict[str, str]) -> tuple[float, float]:
    raw = _zip_bytes(archive, names, "ppt/presentation.xml")
    root = _parse_xml(raw) if raw else None
    if root is None:
        return 12192000.0, 6858000.0
    for element in root.iter():
        if _local(element.tag) != "sldSz":
            continue
        try:
            return float(element.get("cx") or 12192000), float(element.get("cy") or 6858000)
        except (TypeError, ValueError):
            break
    return 12192000.0, 6858000.0


def _zip_notes(archive, names, rels: dict[str, tuple[str, str]], slide_dir: str) -> str:
    for typ, target in rels.values():
        if not (typ.endswith("/notesSlide") or "notesSlide" in target):
            continue
        path = _resolve(slide_dir, target)
        root = _parse_xml(_zip_bytes(archive, names, path))
        if root is None:
            return ""
        lines = []
        for element in root.iter():
            if _local(element.tag) != "sp":
                continue
            ph = _placeholder(element)
            if ph is None or (ph.get("type") or "") != "body":
                continue
            text = "\n".join(_tx_lines(element)).strip()
            if text:
                lines.append(text)
        return "\n".join(lines).strip()
    return ""


def _fill_tree(root, slide, slide_w, slide_h, rels, archive, names, media, slide_dir: str = "ppt/slides") -> None:
    tree = root if _local(root.tag) == "spTree" else None
    if tree is None:
        for element in root.iter():
            if _local(element.tag) == "spTree":
                tree = element
                break
    if tree is None:
        return
    ctx = {
        "rels": rels,
        "archive": archive,
        "names": names,
        "media": media,
        "slide_dir": slide_dir,
    }
    for child in list(tree):
        _take_xml_element(child, slide, slide_w, slide_h, (), ctx)


def _take_xml_element(element, slide: Slide, slide_w: float, slide_h: float, transforms, ctx) -> None:
    tag = _local(getattr(element, "tag", ""))
    if tag in {"nvGrpSpPr", "grpSpPr", "nvSpPr", "spPr", "nvGraphicFramePr", "xfrm", "txBody", "style", "extLst"}:
        return
    if tag == "AlternateContent":
        holder = _child(element, "Fallback") or _child(element, "Choice")
        if holder is None:
            return
        for child in list(holder):
            _take_xml_element(child, slide, slide_w, slide_h, transforms, ctx)
        return
    if tag == "grpSp":
        frame = _xml_group_frame(element)
        nested = transforms + (frame,) if frame is not None else transforms
        for child in list(element):
            _take_xml_element(child, slide, slide_w, slide_h, nested, ctx)
        return
    if tag == "pic":
        _take_xml_picture(element, slide, slide_w, slide_h, transforms, ctx)
        return
    if tag in {"sp", "cxnSp"}:
        _take_xml_sp(element, slide, slide_w, slide_h, transforms, line=tag == "cxnSp")
        return
    if tag == "graphicFrame":
        _take_xml_graphic(element, slide, slide_w, slide_h, transforms)
        return


def _take_xml_sp(element, slide: Slide, slide_w: float, slide_h: float, transforms, line: bool = False) -> None:
    text = "\n".join(_tx_lines(element)).strip()
    box = _xml_box(element, slide_w, slide_h, transforms)
    placeholder = _placeholder(element) is not None
    if box is None and text and placeholder:
        box = _xml_placeholder_box(element)
    if box is None:
        return
    name = _xml_name(element)
    if placeholder or _is_textbox(element):
        if text:
            slide.objects.append(_plain_text(box, text, name, _xml_font_size(element)))
        return
    preset = "line" if line else _PRESET_KIND.get(_xml_preset(element) or "rect", "rect")
    if _xml_preset(element) or line:
        slide.objects.append(_plain_shape(box, name or preset, preset, _xml_fill(element)))
        if text:
            slide.objects.append(_plain_text(box, text, name, _xml_font_size(element)))
        return
    if text:
        slide.objects.append(_plain_text(box, text, name, _xml_font_size(element)))


def _take_xml_graphic(element, slide: Slide, slide_w: float, slide_h: float, transforms) -> None:
    """Tabelle als Text. Diagramm, SmartArt und OLE bleiben aus, ihr Text nicht."""
    text = _table_text(element)
    if not text:
        text = "\n".join(_tx_lines(element)).strip()
    if not text:
        return
    box = _xml_box(element, slide_w, slide_h, transforms)
    if box is None:
        return
    slide.objects.append(_plain_text(box, text, _xml_name(element), _xml_font_size(element)))


def _take_xml_picture(element, slide: Slide, slide_w: float, slide_h: float, transforms, ctx) -> None:
    box = _xml_box(element, slide_w, slide_h, transforms)
    if box is None:
        return
    name = _xml_name(element)
    blip = None
    for node in element.iter():
        if _local(node.tag) == "blip":
            blip = node
            break
    embed = blip.get(_R_EMBED) if blip is not None else None
    rels = (ctx or {}).get("rels") or {}
    archive = (ctx or {}).get("archive")
    names = (ctx or {}).get("names")
    media = (ctx or {}).get("media")
    slide_dir = (ctx or {}).get("slide_dir") or "ppt/slides"
    if not embed or embed not in rels or archive is None or not isinstance(names, dict) or not isinstance(media, dict):
        _append_stand_in(slide, box, name)
        return
    path = _resolve(slide_dir, rels[embed][1])
    blob = _zip_bytes(archive, names, path)
    if not blob:
        _append_stand_in(slide, box, name)
        return
    ext = "png"
    if path and "." in path.rsplit("/", 1)[-1]:
        suffix = path.rsplit(".", 1)[-1].lower()
        if suffix in {"png", "jpg", "jpeg", "gif", "bmp", "tif", "tiff", "webp", "emf", "wmf"}:
            ext = "jpg" if suffix == "jpeg" else suffix
    folder = _media_folder(media)
    file_path = folder / f"{new_id()}.{ext}"
    try:
        file_path.write_bytes(blob)
    except OSError:
        _append_stand_in(slide, box, name)
        return
    x, y, w, h = box
    slide.objects.append(
        SlideObject(id=new_id(), kind="image", x=x, y=y, w=w, h=h, name=name, props={"path": str(file_path)})
    )


def _append_stand_in(slide: Slide, box, name: str) -> None:
    x, y, w, h = box
    slide.objects.append(
        SlideObject(
            id=new_id(),
            kind="shape",
            x=x,
            y=y,
            w=w,
            h=h,
            name=name or "bild",
            props={"shape": "rect", "fill": "#E8EEF8", "stroke": "#0B63E5", "stroke_width": 2},
        )
    )


def _plain_text(box, text: str, name: str, font_size: int) -> SlideObject:
    x, y, w, h = box
    return SlideObject(
        id=new_id(),
        kind="text",
        x=x,
        y=y,
        w=w,
        h=h,
        name=name,
        props={"text": text, "font_size": font_size, "color": "#1B1F2A", "font_family": "Calibri"},
    )


def _plain_shape(box, name: str, preset: str, fill: str) -> SlideObject:
    x, y, w, h = box
    return SlideObject(
        id=new_id(),
        kind="shape",
        x=x,
        y=y,
        w=w,
        h=h,
        name=name,
        props={"shape": preset, "fill": fill, "stroke": "#00000000", "stroke_width": 0},
    )


def _child(element, name: str):
    for child in element:
        if _local(child.tag) == name:
            return child
    return None


def _xml_xfrm(element):
    found = _child(element, "xfrm")
    if found is not None:
        return found
    for props_name in ("spPr", "grpSpPr"):
        props = _child(element, props_name)
        if props is None:
            continue
        found = _child(props, "xfrm")
        if found is not None:
            return found
    return None


def _xml_box(element, slide_w: float, slide_h: float, transforms):
    xfrm = _xml_xfrm(element)
    if xfrm is None or slide_w <= 0 or slide_h <= 0:
        return None
    off = _child(xfrm, "off")
    ext = _child(xfrm, "ext")
    if off is None or ext is None:
        return None
    try:
        x, y = float(off.get("x") or 0), float(off.get("y") or 0)
        w, h = float(ext.get("cx") or 0), float(ext.get("cy") or 0)
    except (TypeError, ValueError):
        return None
    for off_x, off_y, ch_x, ch_y, scale_x, scale_y in reversed(tuple(transforms)):
        x = off_x + (x - ch_x) * scale_x
        y = off_y + (y - ch_y) * scale_y
        w = abs(w * scale_x)
        h = abs(h * scale_y)
    return (x / slide_w, y / slide_h, max(0.01, w / slide_w), max(0.01, h / slide_h))


def _xml_group_frame(element):
    props = _child(element, "grpSpPr")
    xfrm = _child(props, "xfrm") if props is not None else None
    if xfrm is None:
        return None

    def num(node, attr: str) -> float:
        if node is None:
            return 0.0
        try:
            return float(node.get(attr) or 0)
        except (TypeError, ValueError):
            return 0.0

    off, ext = _child(xfrm, "off"), _child(xfrm, "ext")
    ch_off, ch_ext = _child(xfrm, "chOff"), _child(xfrm, "chExt")
    ext_cx, ext_cy = num(ext, "cx"), num(ext, "cy")
    ch_cx, ch_cy = num(ch_ext, "cx"), num(ch_ext, "cy")
    if ext_cx <= 0 or ext_cy <= 0 or ch_cx <= 0 or ch_cy <= 0:
        return None
    return (num(off, "x"), num(off, "y"), num(ch_off, "x"), num(ch_off, "y"), ext_cx / ch_cx, ext_cy / ch_cy)


def _placeholder(element):
    nv = _child(element, "nvSpPr")
    nvpr = _child(nv, "nvPr") if nv is not None else None
    return _child(nvpr, "ph") if nvpr is not None else None


def _xml_placeholder_box(element):
    ph = _placeholder(element)
    if ph is None:
        return None
    ph_type = ph.get("type") or ""
    try:
        index = int(ph.get("idx") or 0)
    except (TypeError, ValueError):
        index = 0
    if ph_type in {"title", "ctrTitle"}:
        return (0.06, 0.12, 0.88, 0.22)
    if ph_type == "subTitle":
        return (0.08, 0.38, 0.84, 0.16)
    return (0.08, min(0.72, 0.36 + max(0, index - 1) * 0.06), 0.84, 0.46)


def _tx_lines(element) -> list[str]:
    body = _child(element, "txBody")
    if body is None:
        return []
    lines = []
    for para in body:
        if _local(para.tag) != "p":
            continue
        bits = []
        for node in para.iter():
            if _local(node.tag) == "t" and node.text:
                bits.append(node.text)
        line = "".join(bits).strip()
        if line:
            lines.append(line)
    return lines


def _table_text(element) -> str:
    rows = []
    for node in element.iter():
        if _local(node.tag) != "tr":
            continue
        cells = []
        for cell in node:
            if _local(cell.tag) != "tc":
                continue
            cells.append(" ".join(_tx_lines(cell)).strip())
        if any(cells):
            rows.append(" | ".join(cells))
    return "\n".join(rows).strip()


def _xml_font_size(element) -> int:
    body = _child(element, "txBody")
    if body is None:
        return 18
    for node in body.iter():
        if _local(node.tag) not in {"rPr", "defRPr", "endParaRPr"}:
            continue
        raw = node.get("sz")
        if not raw:
            continue
        try:
            return max(8, min(int(float(raw) / 100), 96))
        except (TypeError, ValueError):
            continue
    return 18


def _xml_name(element) -> str:
    for parent_name in ("nvSpPr", "nvPicPr", "nvGraphicFramePr", "nvCxnSpPr", "nvGrpSpPr"):
        parent = _child(element, parent_name)
        cnv = _child(parent, "cNvPr") if parent is not None else None
        if cnv is not None and cnv.get("name"):
            return cnv.get("name") or ""
    return ""


def _is_textbox(element) -> bool:
    nv = _child(element, "nvSpPr")
    cnv = _child(nv, "cNvSpPr") if nv is not None else None
    if cnv is None:
        return False
    return str(cnv.get("txBox") or "").lower() in {"1", "true"}


def _xml_preset(element) -> str | None:
    props = _child(element, "spPr")
    geom = _child(props, "prstGeom") if props is not None else None
    if geom is None:
        return None
    return geom.get("prst")


def _xml_fill(element) -> str:
    props = _child(element, "spPr")
    solid = _child(props, "solidFill") if props is not None else None
    if solid is None:
        return "#0B63E5"
    for node in solid.iter():
        if _local(node.tag) == "srgbClr" and node.get("val") and len(node.get("val") or "") == 6:
            return "#" + (node.get("val") or "").upper()
    return "#0B63E5"


def _take_shape(shape, slide: Slide, slide_w: float, slide_h: float, media: dict, transforms=()) -> None:
    """Eine Form übernehmen. Unbekannte oder defekte Formen werden übersprungen."""
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    try:
        kind = shape.shape_type
    except Exception:
        return
    if kind == MSO_SHAPE_TYPE.GROUP:
        try:
            children = list(shape.shapes)
        except Exception:
            children = []
        children.extend(_alternate_shapes(getattr(shape, "shapes", None)))
        frame = _group_frame(shape)
        nested = transforms + (frame,) if frame is not None else transforms
        for child in children:
            _take_shape(child, slide, slide_w, slide_h, media, nested)
        return
    box = _box(shape, slide_w, slide_h, transforms)
    if kind == MSO_SHAPE_TYPE.PICTURE:
        if box is not None:
            _take_picture(shape, slide, box, media)
        return
    if getattr(shape, "has_table", False):
        if box is not None:
            _take_table(shape, slide, box)
        return
    text = _shape_text(shape)
    if kind == MSO_SHAPE_TYPE.TEXT_BOX:
        if text and box is not None:
            slide.objects.append(_text_object(shape, box, text))
        return
    if kind == MSO_SHAPE_TYPE.PLACEHOLDER or getattr(shape, "is_placeholder", False):
        # PowerPoint lässt die Maße oft weg. python-pptx liefert dann None,
        # der Text steht aber im Platzhalter. Ohne Kasten bleibt die Folie leer.
        if box is None and text:
            box = _placeholder_fallback(shape)
        if text and box is not None:
            slide.objects.append(_text_object(shape, box, text))
        elif box is not None:
            _take_picture(shape, slide, box, media)
        return
    if kind in {MSO_SHAPE_TYPE.AUTO_SHAPE, MSO_SHAPE_TYPE.FREEFORM, MSO_SHAPE_TYPE.LINE}:
        if box is None:
            return
        preset = "line" if kind == MSO_SHAPE_TYPE.LINE else _auto_kind(shape)
        slide.objects.append(_shape_object(shape, box, preset))
        if text:
            slide.objects.append(_text_object(shape, box, text))
        return
    if text and box is not None:
        slide.objects.append(_text_object(shape, box, text))


def _box(shape, slide_w: float, slide_h: float, transforms=()):
    try:
        left, top, width, height = shape.left, shape.top, shape.width, shape.height
    except Exception:
        return None
    if left is None or top is None or width is None or height is None:
        return None
    if slide_w <= 0 or slide_h <= 0:
        return None
    x, y, w, h = float(left), float(top), float(width), float(height)
    for off_x, off_y, ch_x, ch_y, scale_x, scale_y in reversed(tuple(transforms)):
        x = off_x + (x - ch_x) * scale_x
        y = off_y + (y - ch_y) * scale_y
        w = abs(w * scale_x)
        h = abs(h * scale_y)
    return (
        x / slide_w,
        y / slide_h,
        max(0.01, w / slide_w),
        max(0.01, h / slide_h),
    )


def _group_frame(shape):
    """Gruppenkinder stehen im lokalen chOff/chExt-Raum, nicht in Folien-EMUs."""
    element = getattr(shape, "_element", None)
    xfrm = getattr(element, "xfrm", None) if element is not None else None
    if xfrm is None:
        props = getattr(element, "grpSpPr", None)
        xfrm = getattr(props, "xfrm", None) if props is not None else None
    if xfrm is None:
        return None

    def num(value) -> float:
        if value is None:
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    off_x, off_y = num(getattr(xfrm, "x", None)), num(getattr(xfrm, "y", None))
    ext_cx, ext_cy = num(getattr(xfrm, "cx", None)), num(getattr(xfrm, "cy", None))
    ch_off, ch_ext = getattr(xfrm, "chOff", None), getattr(xfrm, "chExt", None)
    ch_x = num(getattr(ch_off, "x", None)) if ch_off is not None else 0.0
    ch_y = num(getattr(ch_off, "y", None)) if ch_off is not None else 0.0
    ch_cx = num(getattr(ch_ext, "cx", None)) if ch_ext is not None else 0.0
    ch_cy = num(getattr(ch_ext, "cy", None)) if ch_ext is not None else 0.0
    if ext_cx <= 0 or ext_cy <= 0 or ch_cx <= 0 or ch_cy <= 0:
        return None
    return (off_x, off_y, ch_x, ch_y, ext_cx / ch_cx, ext_cy / ch_cy)


def _placeholder_fallback(shape) -> tuple[float, float, float, float]:
    ph_type = None
    index = 0
    try:
        fmt = shape.placeholder_format
        ph_type = fmt.type
        index = int(getattr(fmt, "idx", 0) or 0)
    except Exception:
        ph_type = None
    try:
        from pptx.enum.shapes import PP_PLACEHOLDER

        if ph_type in {PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE, PP_PLACEHOLDER.VERTICAL_TITLE}:
            return (0.06, 0.12, 0.88, 0.22)
        if ph_type == PP_PLACEHOLDER.SUBTITLE:
            return (0.08, 0.38, 0.84, 0.16)
    except Exception:
        pass
    return (0.08, min(0.72, 0.36 + max(0, index - 1) * 0.06), 0.84, 0.46)


def _alternate_shapes(collection) -> list:
    """python-pptx überspringt AlternateContent. Fallback-Formen trotzdem lesen."""
    if collection is None:
        return []
    try:
        from pptx.oxml.ns import qn

        tree = collection._spTree
        factory = collection._shape_factory
        alternate = qn("ve:AlternateContent")
        fallback = qn("ve:Fallback")
        choice = qn("ve:Choice")
        tags = {qn("p:sp"), qn("p:grpSp"), qn("p:graphicFrame"), qn("p:cxnSp"), qn("p:pic")}
        found = []
        for child in list(tree):
            if child.tag != alternate:
                continue
            holder = None
            for name in (fallback, choice):
                candidate = child.find(name)
                if candidate is not None and any(element.tag in tags for element in candidate):
                    holder = candidate
                    break
            if holder is None:
                continue
            for element in holder:
                if element.tag not in tags:
                    continue
                try:
                    found.append(factory(element))
                except Exception:
                    continue
        return found
    except Exception:
        return []


def _shape_text(shape) -> str:
    try:
        if not shape.has_text_frame:
            return ""
        return "\n".join(paragraph.text for paragraph in shape.text_frame.paragraphs).strip()
    except Exception:
        return ""


def _font_size(shape) -> int:
    try:
        size = shape.text_frame.paragraphs[0].font.size
        if size is not None:
            return max(8, min(int(size.pt), 96))
    except Exception:
        pass
    return 18


def _text_object(shape, box, text: str) -> SlideObject:
    x, y, w, h = box
    return SlideObject(
        id=new_id(),
        kind="text",
        x=x,
        y=y,
        w=w,
        h=h,
        name=getattr(shape, "name", "") or "",
        props={"text": text, "font_size": _font_size(shape), "color": "#1B1F2A", "font_family": "Calibri"},
    )


def _auto_kind(shape) -> str:
    try:
        from pptx.enum.shapes import MSO_SHAPE

        preset = shape.auto_shape_type
    except Exception:
        return "rect"
    pairs = (
        ("RECTANGLE", "rect"),
        ("ROUNDED_RECTANGLE", "roundrect"),
        ("OVAL", "ellipse"),
        ("ISOSCELES_TRIANGLE", "triangle"),
        ("DIAMOND", "diamond"),
        ("RIGHT_ARROW", "arrow"),
        ("STAR_5_POINT", "star"),
        ("LINE_INVERSE", "line"),
        ("STRAIGHT_CONNECTOR_1", "line"),
    )
    for enum_name, kind in pairs:
        member = getattr(MSO_SHAPE, enum_name, None)
        if member is not None and preset == member:
            return kind
    return "rect"


def _fill_hex(shape) -> str:
    try:
        from pptx.enum.dml import MSO_FILL

        fill = shape.fill
        if fill.type != MSO_FILL.SOLID:
            return "#0B63E5"
        rgb = fill.fore_color.rgb
        return "#{:02X}{:02X}{:02X}".format(int(rgb[0]), int(rgb[1]), int(rgb[2]))
    except Exception:
        return "#0B63E5"


def _shape_object(shape, box, preset: str) -> SlideObject:
    x, y, w, h = box
    return SlideObject(
        id=new_id(),
        kind="shape",
        x=x,
        y=y,
        w=w,
        h=h,
        name=getattr(shape, "name", "") or preset,
        props={"shape": preset, "fill": _fill_hex(shape), "stroke": "#00000000", "stroke_width": 0},
    )


def _take_picture(shape, slide: Slide, box, media: dict) -> None:
    try:
        image = shape.image
        blob = image.blob
        ext = image.ext or "png"
    except Exception:
        _picture_stand_in(shape, slide, box)
        return
    folder = _media_folder(media)
    file_path = folder / f"{new_id()}.{ext}"
    try:
        file_path.write_bytes(blob)
    except OSError:
        _picture_stand_in(shape, slide, box)
        return
    x, y, w, h = box
    slide.objects.append(
        SlideObject(
            id=new_id(),
            kind="image",
            x=x,
            y=y,
            w=w,
            h=h,
            name=getattr(shape, "name", "") or "",
            props={"path": str(file_path)},
        )
    )


def _picture_stand_in(shape, slide: Slide, box) -> None:
    """Bild ohne Blob bleibt als Fläche sichtbar, die Folie wird nicht leer."""
    x, y, w, h = box
    slide.objects.append(
        SlideObject(
            id=new_id(),
            kind="shape",
            x=x,
            y=y,
            w=w,
            h=h,
            name=getattr(shape, "name", "") or "bild",
            props={"shape": "rect", "fill": "#E8EEF8", "stroke": "#0B63E5", "stroke_width": 2},
        )
    )


def _take_table(shape, slide: Slide, box) -> None:
    lines = []
    try:
        for row in shape.table.rows:
            cells = []
            for cell in row.cells:
                cells.append((cell.text or "").strip())
            if any(cells):
                lines.append(" | ".join(cells))
    except Exception:
        return
    text = "\n".join(lines).strip()
    if text:
        slide.objects.append(_text_object(shape, box, text))


def _media_folder(media: dict) -> Path:
    if media.get("folder") is not None:
        return media["folder"]
    hint = media.get("hint")
    source = Path(media["source"])
    candidates = []
    if hint:
        candidates.append(Path(hint))
    else:
        candidates.append(Path(str(source.with_suffix("")) + "_media"))
    for folder in candidates:
        try:
            folder.mkdir(parents=True, exist_ok=True)
            probe = folder / ".od-write"
            probe.write_bytes(b"ok")
            probe.unlink()
            media["folder"] = folder
            return folder
        except OSError:
            continue
    folder = Path(tempfile.mkdtemp(prefix="officedisplay-pptx-"))
    media["folder"] = folder
    return folder
