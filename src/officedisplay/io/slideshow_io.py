"""`.oshow` als Zip, Export nach `.odisp`, Import aus Präsentationen."""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

from officedisplay.ai.doc_transform import read_text_file
from officedisplay.model.presentation import (
    Background,
    Presentation,
    Slide,
    SlideObject,
    iter_objects,
    new_id,
)
from officedisplay.model.slideshow import ShowEntry, Slideshow


IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}
TEXT_EXT = {".txt", ".md", ".markdown", ".pdf"}
MEDIA_KEYS = ("path", "image", "render_path")


def save_oshow(show: Slideshow, path: str | Path) -> None:
    target = Path(path)
    payload = show.to_dict()
    mapping: dict[str, str] = {}

    def visit(node) -> None:
        if isinstance(node, dict):
            for key, value in list(node.items()):
                if key in MEDIA_KEYS and isinstance(value, str) and value:
                    file_path = Path(value)
                    if file_path.is_file():
                        if value not in mapping:
                            mapping[value] = f"media/{len(mapping)}_{file_path.name}"
                        node[key] = mapping[value]
                else:
                    visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(payload)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("slideshow.json", json.dumps(payload, ensure_ascii=False, indent=2))
        for source, arcname in mapping.items():
            archive.write(source, arcname)


def load_oshow(path: str | Path) -> Slideshow:
    source = Path(path)
    media_dir = Path(str(source.with_suffix("")) + "_media")
    if media_dir.exists():
        shutil.rmtree(media_dir)
    media_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source, "r") as archive:
        payload = json.loads(archive.read("slideshow.json").decode("utf-8"))
        for info in archive.infolist():
            if info.filename.startswith("media/") and not info.is_dir():
                archive.extract(info, media_dir)
    _absolutize(payload, media_dir)
    return Slideshow.from_dict(payload)


def _absolutize(node, media_dir: Path) -> None:
    if isinstance(node, dict):
        for key, value in list(node.items()):
            if key in MEDIA_KEYS and isinstance(value, str) and value.startswith("media/"):
                node[key] = str(media_dir / value)
            else:
                _absolutize(value, media_dir)
    elif isinstance(node, list):
        for item in node:
            _absolutize(item, media_dir)


def entries_from_paths(paths: list[str]) -> list[ShowEntry]:
    entries: list[ShowEntry] = []
    for raw in paths:
        file_path = Path(raw)
        suffix = file_path.suffix.lower()
        title = file_path.stem or file_path.name
        if suffix in IMAGE_EXT:
            entries.append(ShowEntry(id=new_id(), kind="image", title=title, path=str(file_path)))
        elif suffix in VIDEO_EXT:
            entries.append(ShowEntry(id=new_id(), kind="video", title=title, path=str(file_path)))
        elif suffix in TEXT_EXT:
            entries.append(ShowEntry(id=new_id(), kind="text", title=title, text=read_text_file(str(file_path))))
    return entries


def _is_image(path: str | None) -> bool:
    return bool(path) and Path(path).suffix.lower() in IMAGE_EXT


def slideshow_to_presentation(show: Slideshow) -> Presentation:
    slides: list[Slide] = []
    for index, entry in enumerate(show.entries):
        slide = Slide(
            id=new_id(),
            name=entry.title or f"Eintrag {index + 1}",
            background=Background(color="#111111" if entry.kind != "text" else "#FFFFFF"),
            notes=entry.title or "",
        )
        if entry.kind == "image":
            slide.objects.append(
                SlideObject(
                    id=new_id(),
                    kind="image",
                    x=0.0,
                    y=0.0,
                    w=1.0,
                    h=1.0,
                    name=entry.title or "bild",
                    props={"path": entry.path or ""},
                )
            )
        elif entry.kind == "video":
            slide.objects.append(
                SlideObject(
                    id=new_id(),
                    kind="video",
                    x=0.08,
                    y=0.08,
                    w=0.84,
                    h=0.84,
                    name=entry.title or "video",
                    props={"path": entry.path or ""},
                )
            )
            if entry.text:
                slide.notes = entry.text
        else:
            slide.objects.append(
                SlideObject(
                    id=new_id(),
                    kind="text",
                    x=0.06,
                    y=0.06,
                    w=0.88,
                    h=0.88 if not _is_image(entry.path) else 0.42,
                    name=entry.title or "text",
                    props={
                        "text": entry.text or entry.title or "",
                        "font_family": "Segoe UI",
                        "font_size": 32,
                        "color": "#1B1F2A",
                        "align": "left",
                    },
                )
            )
            if _is_image(entry.path):
                slide.objects.append(
                    SlideObject(
                        id=new_id(),
                        kind="image",
                        x=0.06,
                        y=0.52,
                        w=0.88,
                        h=0.4,
                        name="bild",
                        props={"path": entry.path},
                    )
                )
        slides.append(slide)
    presentation = Presentation(title=show.title or "Slideshow", slides=slides, author=show.author, email=show.email)
    if not presentation.slides:
        presentation.slides.append(Slide(id=new_id(), name="Leer"))
    return presentation


def export_slideshow_odisp(show: Slideshow, path: str | Path) -> Presentation:
    from officedisplay.io.native_io import save_odisp

    presentation = slideshow_to_presentation(show)
    save_odisp(presentation, path)
    return presentation


def slideshow_from_presentation(presentation: Presentation, preview_dir: Path | None = None) -> Slideshow:
    entries: list[ShowEntry] = []
    for slide in presentation.slides:
        texts: list[str] = []
        image = None
        video = None
        for obj in iter_objects(slide):
            if obj.kind == "text":
                text = str(obj.props.get("text") or "").strip()
                if text:
                    texts.append(text)
            elif obj.kind == "image" and image is None:
                image = obj.props.get("path") or obj.props.get("render_path")
            elif obj.kind == "video" and video is None:
                video = obj.props.get("path")
            elif obj.kind == "shape" and image is None and obj.props.get("image"):
                image = obj.props.get("image")
        if image is None and slide.background.image:
            image = slide.background.image
        title = slide.name or "Folie"
        if video:
            entries.append(ShowEntry(id=new_id(), kind="video", title=title, path=video, text="\n\n".join(texts)))
        elif texts:
            entries.append(ShowEntry(id=new_id(), kind="text", title=title, text="\n\n".join(texts), path=image if _is_image(image) else None))
        elif image:
            entries.append(ShowEntry(id=new_id(), kind="image", title=title, path=image))
        else:
            entries.append(_preview_entry(presentation, slide, title, preview_dir))
    return Slideshow(title=presentation.title, entries=entries, author=presentation.author, email=presentation.email)


def _preview_entry(presentation: Presentation, slide: Slide, title: str, preview_dir: Path | None) -> ShowEntry:
    if preview_dir is not None:
        try:
            from officedisplay.ui.render import render_thumb

            preview_dir.mkdir(parents=True, exist_ok=True)
            image = render_thumb(presentation, slide, 960)
            target = preview_dir / f"{slide.id}.png"
            if image.save(str(target)):
                return ShowEntry(id=new_id(), kind="image", title=title, path=str(target))
        except Exception:
            pass
    note = slide.notes.strip()
    return ShowEntry(id=new_id(), kind="text", title=title, text=note or title)


def slideshow_from_path(path: str | Path) -> Slideshow:
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix == ".oshow":
        return load_oshow(source)
    if suffix == ".pptx":
        from officedisplay.io.pptx_io import import_pptx

        presentation = import_pptx(source)
    elif suffix == ".odp":
        from officedisplay.io.odp_io import import_odp

        presentation = import_odp(source)
    else:
        from officedisplay.io.native_io import load_odisp

        presentation = load_odisp(source)
    preview = source.with_name(source.stem + "_slideshow_preview")
    return slideshow_from_presentation(presentation, preview)
