from __future__ import annotations

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


def import_pptx(path: str | Path, media_dir: str | Path | None = None) -> Presentation:
    from pptx import Presentation as PptxPresentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    package = PptxPresentation(str(path))
    width = max(1, int(package.slide_width / EMU_PER_PIXEL))
    height = max(1, int(package.slide_height / EMU_PER_PIXEL))
    presentation = Presentation(title=Path(path).stem, width=width, height=height)
    presentation.slides = []
    folder = Path(media_dir) if media_dir else Path(path).with_suffix("") 
    folder = Path(str(folder) + "_media")
    folder.mkdir(parents=True, exist_ok=True)
    for index, page in enumerate(package.slides, start=1):
        slide = Slide(id=new_id(), name=f"Folie {index}", background=Background(color="#FFFFFF"))
        try:
            notes = page.notes_slide.notes_text_frame.text
            slide.notes = notes or ""
        except Exception:
            slide.notes = ""
        for shape in page.shapes:
            x = shape.left / package.slide_width
            y = shape.top / package.slide_height
            w = shape.width / package.slide_width
            h = shape.height / package.slide_height
            if shape.has_text_frame and shape.shape_type != MSO_SHAPE_TYPE.PICTURE:
                text = "\n".join(paragraph.text for paragraph in shape.text_frame.paragraphs)
                slide.objects.append(
                    SlideObject(
                        id=new_id(),
                        kind="text",
                        x=x,
                        y=y,
                        w=w,
                        h=h,
                        name=shape.name or "",
                        props={"text": text, "font_size": 18, "color": "#1B1F2A", "font_family": "Calibri"},
                    )
                )
            elif shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                image = shape.image
                file_path = folder / f"{new_id()}.{image.ext}"
                file_path.write_bytes(image.blob)
                slide.objects.append(
                    SlideObject(
                        id=new_id(),
                        kind="image",
                        x=x,
                        y=y,
                        w=w,
                        h=h,
                        name=shape.name or "",
                        props={"path": str(file_path)},
                    )
                )
        presentation.slides.append(slide)
    if not presentation.slides:
        presentation.slides.append(Slide(id=new_id(), name="Folie 1"))
    return presentation
