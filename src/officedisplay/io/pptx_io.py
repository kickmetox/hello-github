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
            _apply_background_chain(slide, _background_sources(page), media)
        except Exception:
            pass
        try:
            _consume_page(page, slide, slide_w, slide_h, media)
        except Exception:
            pass
        try:
            _prepend_inherited_pictures(page, slide, slide_w, slide_h, media)
        except Exception:
            pass
        try:
            _promote_full_bleed(slide)
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
            slide_dir = _parent_dir(slide_name)
            try:
                _zip_apply_background(archive, names, root, rels, slide_dir, slide, media)
                _fill_tree(root, slide, slide_w, slide_h, rels, archive, names, media, slide_dir)
                _zip_prepend_pictures(archive, names, root, rels, slide_dir, slide, slide_w, slide_h, media)
                slide.notes = _zip_notes(archive, names, rels, slide_dir)
            except Exception:
                pass
            try:
                _promote_full_bleed(slide)
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
        _take_xml_sp(element, slide, slide_w, slide_h, transforms, line=tag == "cxnSp", ctx=ctx)
        return
    if tag == "graphicFrame":
        _take_xml_graphic(element, slide, slide_w, slide_h, transforms)
        return


def _take_xml_sp(element, slide: Slide, slide_w: float, slide_h: float, transforms, line: bool = False, ctx=None) -> None:
    text = "\n".join(_tx_lines(element)).strip()
    box = _xml_box(element, slide_w, slide_h, transforms)
    placeholder = _placeholder(element) is not None
    if box is None and text and placeholder:
        box = _xml_placeholder_box(element)
    if box is None:
        return
    name = _xml_name(element)
    if _blip_embed(element) and ctx is not None:
        _take_xml_picture(element, slide, slide_w, slide_h, transforms, ctx)
        if text:
            slide.objects.append(_xml_text(element, box, text, name))
        return
    if placeholder or _is_textbox(element):
        if text:
            slide.objects.append(_xml_text(element, box, text, name))
        return
    preset = "line" if line else _PRESET_KIND.get(_xml_preset(element) or "rect", "rect")
    if _xml_preset(element) or line:
        stroke, stroke_width = _outline_element(element)
        slide.objects.append(_plain_shape(box, name or preset, preset, _xml_fill(element), stroke, stroke_width))
        if text:
            slide.objects.append(_xml_text(element, box, text, name))
        return
    if text:
        slide.objects.append(_xml_text(element, box, text, name))


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


def _xml_text(element, box, text: str, name: str) -> SlideObject:
    return _plain_text(
        box,
        text,
        name,
        _xml_font_size(element),
        _align_of(element) or "left",
        _valign_of(element),
        _run_color(element) or "#1B1F2A",
    )


def _plain_text(box, text: str, name: str, font_size: int, align: str = "left", valign: str | None = None, color: str = "#1B1F2A") -> SlideObject:
    x, y, w, h = box
    props = {
        "text": text,
        "font_size": font_size,
        "color": color or "#1B1F2A",
        "font_family": "Calibri",
        "align": align or "left",
    }
    if valign:
        props["valign"] = valign
    return SlideObject(id=new_id(), kind="text", x=x, y=y, w=w, h=h, name=name, props=props)


def _plain_shape(box, name: str, preset: str, fill: str, stroke: str = "#00000000", stroke_width: int = 0) -> SlideObject:
    x, y, w, h = box
    return SlideObject(
        id=new_id(),
        kind="shape",
        x=x,
        y=y,
        w=w,
        h=h,
        name=name,
        props={"shape": preset, "fill": fill, "stroke": stroke, "stroke_width": stroke_width},
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
    return _norm_box(x, y, w, h, slide_w, slide_h)


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
    return _explicit_sz(element) or 18


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
    if props is not None and _child(props, "noFill") is not None:
        return "#00000000"
    solid = _child(props, "solidFill") if props is not None else None
    if solid is None:
        return "#0B63E5"
    return _color_of(solid) or "#0B63E5"


_SCHEME = {
    "dk1": "#000000",
    "lt1": "#FFFFFF",
    "dk2": "#1B1F2A",
    "lt2": "#E8EEF8",
    "accent1": "#0B63E5",
    "accent2": "#F28C28",
    "accent3": "#3CB44B",
    "accent4": "#E23B3B",
    "accent5": "#8338EC",
    "accent6": "#F4A261",
    "tx1": "#1B1F2A",
    "bg1": "#FFFFFF",
    "tx2": "#243044",
    "bg2": "#F4F6FB",
}


def _sz_value(raw) -> int | None:
    try:
        return max(8, min(int(round(float(raw) / 100.0)), 96))
    except (TypeError, ValueError):
        return None


def _map_algn(value: str | None) -> str | None:
    return {"l": "left", "ctr": "center", "r": "right", "just": "left", "dist": "left"}.get(value or "")


def _inside(node, stop, name: str) -> bool:
    cursor = node
    while cursor is not None and cursor is not stop:
        if _local(getattr(cursor, "tag", "")) == name:
            return True
        parent = getattr(cursor, "getparent", None)
        cursor = parent() if parent is not None else None
    return False


def _blip_embed(element) -> str | None:
    if element is None:
        return None
    for node in element.iter():
        if _local(node.tag) != "blipFill":
            continue
        if _inside(node, element, "txBody"):
            continue
        for inner in node.iter():
            if _local(inner.tag) != "blip":
                continue
            embed = inner.get(_R_EMBED)
            if embed:
                return embed
    return None


def _alpha_of(node) -> float:
    if node is None:
        return 1.0
    for child in node.iter():
        local = _local(child.tag)
        raw = None
        if local == "alpha":
            raw = child.get("val")
        elif local == "alphaModFix":
            raw = child.get("amt")
        if not raw:
            continue
        try:
            return max(0.0, min(1.0, float(raw) / 100000.0))
        except (TypeError, ValueError):
            continue
    return 1.0


def _color_of(element) -> str | None:
    if element is None:
        return None
    for node in element.iter():
        local = _local(node.tag)
        if local == "srgbClr":
            raw = node.get("val") or ""
            if len(raw) >= 6 and all(ch in "0123456789abcdefABCDEF" for ch in raw[:6]):
                return "#" + raw[:6].upper()
        if local == "schemeClr":
            mapped = _SCHEME.get(node.get("val") or "")
            if mapped:
                return mapped
    return None


def _explicit_sz(element) -> int | None:
    if element is None:
        return None
    body = element if _local(getattr(element, "tag", "")) == "txBody" else _child(element, "txBody")
    if body is None:
        return None
    run_sz = None
    def_sz = None
    for child in body:
        if _local(child.tag) != "p":
            continue
        for node in child.iter():
            local = _local(node.tag)
            if local == "rPr" and node.get("sz") and run_sz is None:
                run_sz = _sz_value(node.get("sz"))
            if local == "defRPr" and node.get("sz") and def_sz is None:
                def_sz = _sz_value(node.get("sz"))
    if run_sz is not None:
        return run_sz
    if def_sz is not None:
        return def_sz
    lst = _child(body, "lstStyle")
    if lst is not None:
        for node in lst.iter():
            if _local(node.tag) == "defRPr" and node.get("sz"):
                return _sz_value(node.get("sz"))
    return None


def _align_of(element) -> str | None:
    if element is None:
        return None
    body = _child(element, "txBody")
    if body is None:
        return None
    for para in body:
        if _local(para.tag) != "p":
            continue
        props = _child(para, "pPr")
        mapped = _map_algn(props.get("algn") if props is not None else None)
        if mapped:
            return mapped
    lst = _child(body, "lstStyle")
    if lst is not None:
        for node in lst.iter():
            mapped = _map_algn(node.get("algn"))
            if mapped:
                return mapped
    return None


def _valign_of(element) -> str | None:
    body = _child(element, "txBody") if element is not None else None
    props = _child(body, "bodyPr") if body is not None else None
    if props is None:
        return None
    return {"t": "top", "ctr": "middle", "b": "bottom"}.get(props.get("anchor") or "")


def _run_color(element) -> str | None:
    body = _child(element, "txBody") if element is not None else None
    if body is None:
        return None
    for para in body:
        if _local(para.tag) != "p":
            continue
        for node in para.iter():
            if _local(node.tag) != "solidFill":
                continue
            found = _color_of(node)
            if found:
                return found
    return None


def _latin_face(element) -> str | None:
    body = _child(element, "txBody") if element is not None else None
    if body is None:
        return None
    for para in body:
        if _local(para.tag) != "p":
            continue
        for node in para.iter():
            if _local(node.tag) != "latin":
                continue
            face = node.get("typeface") or ""
            if face and not face.startswith("+"):
                return face
    return None


def _placeholder_style_name(shape) -> str | None:
    try:
        if not shape.is_placeholder:
            return None
        from pptx.enum.shapes import PP_PLACEHOLDER

        kind = shape.placeholder_format.type
    except Exception:
        return None
    titles = {PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE}
    vertical = getattr(PP_PLACEHOLDER, "VERTICAL_TITLE", None)
    if vertical is not None:
        titles.add(vertical)
    if kind in titles:
        return "titleStyle"
    bodies = {PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.SUBTITLE, PP_PLACEHOLDER.OBJECT}
    vertical_body = getattr(PP_PLACEHOLDER, "VERTICAL_BODY", None)
    if vertical_body is not None:
        bodies.add(vertical_body)
    if kind in bodies:
        return "bodyStyle"
    return "otherStyle"


def _master_style_element(shape):
    name = _placeholder_style_name(shape)
    if not name:
        return None
    master = None
    try:
        master = shape.part.slide_layout.slide_master._element
    except Exception:
        try:
            master = shape.part.slide_master._element
        except Exception:
            return None
    for node in master.iter():
        if _local(node.tag) == name:
            return node
    return None


def _walk_bases(shape):
    base = shape
    seen = set()
    for _ in range(4):
        try:
            nxt = base._base_placeholder
        except Exception:
            nxt = None
        if nxt is None or id(nxt) in seen:
            break
        seen.add(id(nxt))
        yield nxt
        base = nxt


def _api_font_size(shape) -> int | None:
    try:
        frame = shape.text_frame
        for paragraph in frame.paragraphs:
            for run in paragraph.runs:
                if run.font.size is not None:
                    return _sz_value(float(run.font.size.pt) * 100)
            if paragraph.font.size is not None:
                return _sz_value(float(paragraph.font.size.pt) * 100)
    except Exception:
        return None
    return None


def _inherited_font_size(shape) -> int | None:
    try:
        placeholder = bool(shape.is_placeholder)
    except Exception:
        placeholder = False
    if not placeholder:
        return None
    for base in _walk_bases(shape):
        size = _explicit_sz(getattr(base, "_element", None))
        if size is not None:
            return size
    style = _master_style_element(shape)
    if style is None:
        return None
    for node in style.iter():
        if _local(node.tag) == "defRPr" and node.get("sz"):
            return _sz_value(node.get("sz"))
    return None


def _api_align(shape) -> str | None:
    try:
        from pptx.enum.text import PP_ALIGN

        alignment = shape.text_frame.paragraphs[0].alignment
        if alignment == PP_ALIGN.CENTER:
            return "center"
        if alignment == PP_ALIGN.RIGHT:
            return "right"
        if alignment == PP_ALIGN.LEFT:
            return "left"
    except Exception:
        return None
    return None


def _api_valign(shape) -> str | None:
    try:
        from pptx.enum.text import MSO_ANCHOR

        anchor = shape.text_frame.vertical_anchor
        if anchor == MSO_ANCHOR.MIDDLE:
            return "middle"
        if anchor == MSO_ANCHOR.BOTTOM:
            return "bottom"
        if anchor == MSO_ANCHOR.TOP:
            return "top"
    except Exception:
        return None
    return None


def _text_align(shape) -> str:
    found = _align_of(getattr(shape, "_element", None)) or _api_align(shape)
    if found:
        return found
    for base in _walk_bases(shape):
        found = _align_of(getattr(base, "_element", None))
        if found:
            return found
    style = _master_style_element(shape)
    if style is not None:
        for node in style.iter():
            mapped = _map_algn(node.get("algn"))
            if mapped:
                return mapped
    return "left"


def _text_valign(shape) -> str | None:
    found = _valign_of(getattr(shape, "_element", None)) or _api_valign(shape)
    if found:
        return found
    for base in _walk_bases(shape):
        found = _valign_of(getattr(base, "_element", None))
        if found:
            return found
    return None


def _norm_box(x: float, y: float, w: float, h: float, slide_w: float, slide_h: float):
    """EMU durch die Foliengröße in EMU. Eine Pixelbreite verfälscht die Lage."""
    return (x / slide_w, y / slide_h, max(w, 1.0) / slide_w, max(h, 1.0) / slide_h)


def _geometry(shape, slide_w: float, slide_h: float, transforms=()):
    element = getattr(shape, "_element", None)
    if element is not None:
        box = _xml_box(element, slide_w, slide_h, transforms)
        if box is not None:
            return box
    return _box(shape, slide_w, slide_h, transforms)


def _write_image_blob(blob: bytes, ext: str, media: dict) -> str | None:
    suffix = (ext or "png").lower().lstrip(".")
    if suffix == "jpeg":
        suffix = "jpg"
    if suffix not in {"png", "jpg", "gif", "bmp", "tif", "tiff", "webp", "emf", "wmf"}:
        suffix = "png"
    folder = _media_folder(media)
    file_path = folder / f"{new_id()}.{suffix}"
    try:
        file_path.write_bytes(blob)
    except OSError:
        return None
    return str(file_path)


def _image_part_key(part, embed: str) -> str | None:
    try:
        return str(part.related_part(embed).partname)
    except Exception:
        return None


def _part_image_file(part, embed: str, media: dict) -> str | None:
    try:
        image = part.get_image(embed)
        blob = image.blob
        ext = image.ext or "png"
    except Exception:
        return None
    return _write_image_blob(blob, ext, media)


def _shape_image_key(shape) -> str | None:
    part = getattr(shape, "part", None)
    embed = _blip_embed(getattr(shape, "_element", None))
    if part is None or not embed:
        return None
    return _image_part_key(part, embed)


def _mark_image(media: dict, key: str | None) -> None:
    if key:
        media.setdefault("used_images", set()).add(key)


def _bg_fill(element):
    """None heißt: kein eigenes p:bg, also vom Layout oder Master erben."""
    if element is None:
        return None
    c_sld = getattr(element, "cSld", None)
    if c_sld is None:
        c_sld = _child(element, "cSld")
    if c_sld is None and _local(getattr(element, "tag", "")) == "cSld":
        c_sld = element
    if c_sld is None:
        return None
    bg = getattr(c_sld, "bg", None)
    if bg is None:
        bg = _child(c_sld, "bg")
    if bg is None:
        return None
    bg_pr = getattr(bg, "bgPr", None)
    if bg_pr is None:
        bg_pr = _child(bg, "bgPr")
    if bg_pr is None:
        return {"kind": "other"}
    for node in bg_pr.iter():
        if _local(node.tag) != "blip":
            continue
        embed = node.get(_R_EMBED)
        if embed:
            return {"kind": "image", "embed": embed, "opacity": _alpha_of(node)}
    for node in bg_pr:
        if _local(node.tag) != "solidFill":
            continue
        color = _color_of(node)
        if color:
            return {"kind": "solid", "color": color, "opacity": _alpha_of(node)}
    return {"kind": "other"}


def _background_sources(page) -> list:
    sources = []
    element = getattr(page, "_element", None)
    part = getattr(page, "part", None)
    if element is not None:
        sources.append((element, part))
    layout = getattr(page, "slide_layout", None)
    if layout is None:
        return sources
    sources.append((getattr(layout, "_element", None), getattr(layout, "part", None)))
    master = getattr(layout, "slide_master", None)
    if master is not None:
        sources.append((getattr(master, "_element", None), getattr(master, "part", None)))
    return sources


def _apply_background_chain(slide: Slide, sources, media: dict) -> None:
    for element, part in sources:
        spec = _bg_fill(element)
        if spec is None or spec.get("kind") == "other":
            continue
        if spec.get("kind") == "image" and part is not None:
            path = _part_image_file(part, spec["embed"], media)
            if not path:
                continue
            slide.background.mode = "image"
            slide.background.image = path
            slide.background.fit = "cover"
            slide.background.opacity = float(spec.get("opacity", 1.0))
            return
        if spec.get("kind") == "solid":
            slide.background.mode = "solid"
            slide.background.color = spec["color"]
            slide.background.image = None
            slide.background.fit = "cover"
            slide.background.opacity = float(spec.get("opacity", 1.0))
            return


def _show_master_shapes(element) -> bool:
    if element is None:
        return True
    raw = element.get("showMasterSp")
    if raw is None:
        return True
    return str(raw).lower() not in {"0", "false"}


def _copy_pictures(shapes, slide: Slide, slide_w: float, slide_h: float, media: dict, transforms=()) -> None:
    if shapes is None:
        return
    try:
        from pptx.enum.shapes import MSO_SHAPE_TYPE

        members = list(shapes)
    except Exception:
        return
    for shape in members:
        try:
            if getattr(shape, "is_placeholder", False):
                continue
            kind = shape.shape_type
        except Exception:
            continue
        if kind == MSO_SHAPE_TYPE.GROUP:
            frame = _group_frame(shape)
            nested = transforms + (frame,) if frame is not None else transforms
            _copy_pictures(getattr(shape, "shapes", None), slide, slide_w, slide_h, media, nested)
            continue
        embed = _blip_embed(getattr(shape, "_element", None))
        if kind != MSO_SHAPE_TYPE.PICTURE and not embed:
            continue
        box = _geometry(shape, slide_w, slide_h, transforms)
        if box is None:
            continue
        key = _shape_image_key(shape)
        if key and key in media.get("used_images", ()):
            continue
        if kind == MSO_SHAPE_TYPE.PICTURE:
            _take_picture(shape, slide, box, media)
        else:
            _take_embed_picture(getattr(shape, "part", None), embed, slide, box, media, getattr(shape, "name", "") or "")


def _prepend_inherited_pictures(page, slide: Slide, slide_w: float, slide_h: float, media: dict) -> None:
    """Logos vom Layout und Master liegen hinter den Folienobjekten, Platzhaltertext nicht."""
    layout = getattr(page, "slide_layout", None)
    if layout is None:
        return
    master = getattr(layout, "slide_master", None)
    temp = Slide(id="inherited", name="inherited")
    if master is not None and _show_master_shapes(getattr(layout, "_element", None)):
        _copy_pictures(getattr(master, "shapes", None), temp, slide_w, slide_h, media)
    if _show_master_shapes(getattr(page, "_element", None)):
        _copy_pictures(getattr(layout, "shapes", None), temp, slide_w, slide_h, media)
    if temp.objects:
        slide.objects[0:0] = temp.objects


def _promote_full_bleed(slide: Slide) -> None:
    if slide.background.mode == "image" and slide.background.image:
        return
    for obj in slide.objects:
        if obj.kind != "image":
            continue
        if obj.x < 0.05 and obj.y < 0.05 and obj.w > 0.9 and obj.h > 0.9:
            path = obj.props.get("path")
            if not path:
                continue
            slide.background.mode = "image"
            slide.background.image = str(path)
            slide.background.fit = "cover"
            try:
                slide.background.opacity = float(obj.props.get("opacity", 1.0))
            except (TypeError, ValueError):
                slide.background.opacity = 1.0
            return


def _take_embed_picture(part, embed: str | None, slide: Slide, box, media: dict, name: str = "") -> bool:
    if part is None or not embed:
        return False
    path = _part_image_file(part, embed, media)
    if not path:
        return False
    _mark_image(media, _image_part_key(part, embed))
    x, y, w, h = box
    slide.objects.append(
        SlideObject(id=new_id(), kind="image", x=x, y=y, w=w, h=h, name=name or "", props={"path": path})
    )
    return True


def _layout_placeholder_text(shape) -> str:
    try:
        base = shape._base_placeholder
    except Exception:
        return ""
    if base is None:
        return ""
    element = getattr(base, "_element", None)
    if element is None:
        return ""
    return "\n".join(_tx_lines(element)).strip()


def _already_has_text(slide: Slide, text: str) -> bool:
    wanted = " ".join(text.split())
    if not wanted:
        return False
    for obj in slide.objects:
        if obj.kind != "text":
            continue
        have = " ".join(str(obj.props.get("text") or "").split())
        if have == wanted:
            return True
    return False


def _skip_layout_echo(slide: Slide, shape, text: str) -> bool:
    """Layout-Text nicht ein zweites Mal über das Foto legen, wenn die Folie ihn schon hat."""
    layout_text = _layout_placeholder_text(shape)
    if not layout_text or not text:
        return False
    if " ".join(layout_text.split()) != " ".join(text.split()):
        return False
    return _already_has_text(slide, text)


def _rel_by_suffix(rels: dict, suffix: str) -> str | None:
    for typ, target in rels.values():
        if str(typ).rsplit("/", 1)[-1] == suffix:
            return target
    return None


def _zip_apply_background(archive, names, root, rels, slide_dir, slide: Slide, media: dict) -> None:
    chain = [(root, rels, slide_dir)]
    layout_target = _rel_by_suffix(rels, "slideLayout")
    layout_path = _resolve(slide_dir, layout_target) if layout_target else None
    layout_root = _parse_xml(_zip_bytes(archive, names, layout_path)) if layout_path else None
    if layout_root is not None and layout_path is not None:
        layout_dir = _parent_dir(layout_path)
        layout_rels = _rels_map(archive, names, _rels_name(layout_path))
        chain.append((layout_root, layout_rels, layout_dir))
        master_target = _rel_by_suffix(layout_rels, "slideMaster")
        master_path = _resolve(layout_dir, master_target) if master_target else None
        master_root = _parse_xml(_zip_bytes(archive, names, master_path)) if master_path else None
        if master_root is not None and master_path is not None:
            chain.append((master_root, _rels_map(archive, names, _rels_name(master_path)), _parent_dir(master_path)))
    for element, relmap, directory in chain:
        spec = _bg_fill(element)
        if spec is None or spec.get("kind") == "other":
            continue
        if spec.get("kind") == "image":
            relation = relmap.get(spec["embed"])
            target = _resolve(directory, relation[1]) if relation else None
            blob = _zip_bytes(archive, names, target)
            if not blob:
                continue
            ext = target.rsplit(".", 1)[-1] if target and "." in target else "png"
            saved = _write_image_blob(blob, ext, media)
            if not saved:
                continue
            slide.background.mode = "image"
            slide.background.image = saved
            slide.background.fit = "cover"
            slide.background.opacity = float(spec.get("opacity", 1.0))
            return
        if spec.get("kind") == "solid":
            slide.background.mode = "solid"
            slide.background.color = spec["color"]
            slide.background.image = None
            slide.background.opacity = float(spec.get("opacity", 1.0))
            return


def _zip_pic_target(element, rels, directory) -> str | None:
    embed = _blip_embed(element)
    if not embed or embed not in rels:
        return None
    return _resolve(directory, rels[embed][1])


def _zip_collect_pics(element, slide, slide_w, slide_h, transforms, ctx, skip: set[str]) -> None:
    tag = _local(getattr(element, "tag", ""))
    if tag == "grpSp":
        frame = _xml_group_frame(element)
        nested = transforms + (frame,) if frame is not None else transforms
        for child in list(element):
            _zip_collect_pics(child, slide, slide_w, slide_h, nested, ctx, skip)
        return
    if tag != "pic" or _placeholder(element) is not None:
        return
    target = _zip_pic_target(element, ctx.get("rels") or {}, ctx.get("slide_dir") or "")
    if target and target in skip:
        return
    before = len(slide.objects)
    _take_xml_picture(element, slide, slide_w, slide_h, transforms, ctx)
    if target and len(slide.objects) > before:
        skip.add(target)


def _zip_sp_tree(root):
    common = _child(root, "cSld")
    if common is None:
        common = root
    return _child(common, "spTree")


def _zip_prepend_pictures(archive, names, root, rels, slide_dir, slide, slide_w, slide_h, media) -> None:
    skip = set()
    for node in root.iter():
        if _local(node.tag) == "pic":
            target = _zip_pic_target(node, rels, slide_dir)
            if target:
                skip.add(target)
    inherited = Slide(id="inherited", name="inherited")
    layout_target = _rel_by_suffix(rels, "slideLayout")
    layout_path = _resolve(slide_dir, layout_target) if layout_target else None
    if not layout_path or not _show_master_shapes(root):
        return
    layout_root = _parse_xml(_zip_bytes(archive, names, layout_path))
    if layout_root is None:
        return
    layout_dir = _parent_dir(layout_path)
    layout_rels = _rels_map(archive, names, _rels_name(layout_path))
    master_target = _rel_by_suffix(layout_rels, "slideMaster")
    master_path = _resolve(layout_dir, master_target) if master_target else None
    if master_path and _show_master_shapes(layout_root):
        master_root = _parse_xml(_zip_bytes(archive, names, master_path))
        if master_root is not None:
            master_dir = _parent_dir(master_path)
            ctx = {
                "rels": _rels_map(archive, names, _rels_name(master_path)),
                "archive": archive,
                "names": names,
                "media": media,
                "slide_dir": master_dir,
            }
            tree = _zip_sp_tree(master_root)
            if tree is not None:
                for child in list(tree):
                    _zip_collect_pics(child, inherited, slide_w, slide_h, (), ctx, skip)
    ctx = {
        "rels": layout_rels,
        "archive": archive,
        "names": names,
        "media": media,
        "slide_dir": layout_dir,
    }
    tree = _zip_sp_tree(layout_root)
    if tree is not None:
        for child in list(tree):
            _zip_collect_pics(child, inherited, slide_w, slide_h, (), ctx, skip)
    if inherited.objects:
        slide.objects[0:0] = inherited.objects


def _outline_element(element) -> tuple[str, int]:
    props = _child(element, "spPr") if element is not None else None
    line = _child(props, "ln") if props is not None else None
    if line is None:
        return "#00000000", 0
    if _child(line, "noFill") is not None:
        return "#00000000", 0
    color = _color_of(_child(line, "solidFill")) or "#1B1F2A"
    try:
        emu = float(line.get("w") or 0)
    except (TypeError, ValueError):
        emu = 0.0
    width = int(round(emu / EMU_PER_PIXEL)) if emu else 0
    if width <= 0 and _child(line, "solidFill") is not None:
        width = 1
    return color, width


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
    box = _geometry(shape, slide_w, slide_h, transforms)
    element = getattr(shape, "_element", None)
    embed = _blip_embed(element)
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
        if embed and box is not None:
            _take_embed_picture(getattr(shape, "part", None), embed, slide, box, media, getattr(shape, "name", "") or "")
        if text and box is not None:
            slide.objects.append(_text_object(shape, box, text))
        return
    if kind == MSO_SHAPE_TYPE.PLACEHOLDER or getattr(shape, "is_placeholder", False):
        # Eigene Maße, sonst die geerbte Layout-Geometrie. Fehlt beides und
        # der Platzhalter hat eigenen Text, bleibt ein grober Kasten.
        if box is None and text:
            box = _placeholder_fallback(shape)
        if embed and box is not None:
            _take_embed_picture(getattr(shape, "part", None), embed, slide, box, media, getattr(shape, "name", "") or "")
            return
        if _local(getattr(element, "tag", "")) == "pic" and box is not None:
            _take_picture(shape, slide, box, media)
            return
        # Text, der nur im Layout steht, nicht zusätzlich über das Foto legen.
        if text and box is not None and not _skip_layout_echo(slide, shape, text):
            slide.objects.append(_text_object(shape, box, text))
        return
    if kind in {MSO_SHAPE_TYPE.AUTO_SHAPE, MSO_SHAPE_TYPE.FREEFORM, MSO_SHAPE_TYPE.LINE}:
        if box is None:
            return
        preset = "line" if kind == MSO_SHAPE_TYPE.LINE else _auto_kind(shape)
        placed = False
        if embed:
            placed = _take_embed_picture(getattr(shape, "part", None), embed, slide, box, media, getattr(shape, "name", "") or "")
        if not placed:
            slide.objects.append(_shape_object(shape, box, preset))
        if text:
            slide.objects.append(_text_object(shape, box, text))
        return
    if embed and box is not None:
        _take_embed_picture(getattr(shape, "part", None), embed, slide, box, media, getattr(shape, "name", "") or "")
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
    return _norm_box(x, y, w, h, slide_w, slide_h)


def _group_frame(shape):
    """Gruppenkinder stehen im lokalen chOff/chExt-Raum, nicht in Folien-EMUs."""
    element = getattr(shape, "_element", None)
    if element is not None:
        frame = _xml_group_frame(element)
        if frame is not None:
            return frame
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
        lines = [(paragraph.text or "").replace("\v", "\n") for paragraph in shape.text_frame.paragraphs]
        return "\n".join(lines).strip()
    except Exception:
        return ""


def _font_size(shape) -> int:
    size = _explicit_sz(getattr(shape, "_element", None))
    if size is None:
        size = _api_font_size(shape)
    if size is None:
        size = _inherited_font_size(shape)
    return size if size is not None else 18


def _text_object(shape, box, text: str) -> SlideObject:
    x, y, w, h = box
    props = {
        "text": text,
        "font_size": _font_size(shape),
        "color": _run_color(getattr(shape, "_element", None)) or "#1B1F2A",
        "font_family": _latin_face(getattr(shape, "_element", None)) or "Calibri",
        "align": _text_align(shape),
    }
    valign = _text_valign(shape)
    if valign:
        props["valign"] = valign
    return SlideObject(
        id=new_id(),
        kind="text",
        x=x,
        y=y,
        w=w,
        h=h,
        name=getattr(shape, "name", "") or "",
        props=props,
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
    element = getattr(shape, "_element", None)
    props = _child(element, "spPr") if element is not None else None
    if props is not None:
        if _child(props, "noFill") is not None:
            return "#00000000"
        solid = _child(props, "solidFill")
        if solid is not None:
            return _color_of(solid) or "#0B63E5"
        if any(_child(props, name) is not None for name in ("gradFill", "blipFill", "pattFill")):
            return "#00000000"
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
    stroke, stroke_width = _outline_element(getattr(shape, "_element", None))
    return SlideObject(
        id=new_id(),
        kind="shape",
        x=x,
        y=y,
        w=w,
        h=h,
        name=getattr(shape, "name", "") or preset,
        props={"shape": preset, "fill": _fill_hex(shape), "stroke": stroke, "stroke_width": stroke_width},
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
    _mark_image(media, _shape_image_key(shape))
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
