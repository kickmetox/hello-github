from __future__ import annotations

from pathlib import Path

from officedisplay.io.media import IMAGE_EXT, VIDEO_EXT, prepare_image
from officedisplay.io.open_file import DECK_EXT
from officedisplay.model.presentation import SlideObject, new_id


IMAGES = set(IMAGE_EXT)
VIDEOS = set(VIDEO_EXT)
TEXTS = {".txt", ".md", ".markdown", ".pdf", ".rtx"}


def classify(path: str) -> str:
    suffix = Path(path).suffix.lower()
    if suffix in {".pdf"}:
        return "image"
    if suffix in IMAGES:
        return "image"
    if suffix in VIDEOS:
        return "video"
    if suffix == ".pptx":
        return "pptx"
    if suffix in DECK_EXT and suffix not in {".odp", ".odisp", ".pptx"}:
        return "deck"
    if suffix == ".odp":
        return "odp"
    if suffix == ".odisp":
        return "odisp"
    if suffix in {".xlsx", ".xls", ".csv"}:
        return "table"
    if suffix in TEXTS:
        return "text"
    if suffix == ".obj":
        return "obj"
    return "file"


def place_on_slide(slide, path: str, x: float, y: float) -> str:
    kind = classify(path)
    if kind == "image":
        usable, hint, use_text = prepare_image(path)
        if use_text:
            return "textfile"
        if not usable:
            return "hint:" + (hint or "Das Bild lässt sich nicht lesen.")
        slide.objects.append(
            SlideObject(
                id=new_id(),
                kind="image",
                x=x,
                y=y,
                w=0.36,
                h=0.28,
                name=Path(path).stem,
                props={"path": usable, "source": path},
            )
        )
    elif kind == "video":
        slide.objects.append(
            SlideObject(
                id=new_id(),
                kind="video",
                x=x,
                y=y,
                w=0.42,
                h=0.28,
                name=Path(path).stem,
                props={"path": path},
            )
        )
    elif kind == "text":
        text = Path(path).read_text(encoding="utf-8", errors="replace") if not path.lower().endswith(".pdf") else ""
        slide.objects.append(
            SlideObject(
                id=new_id(),
                kind="text",
                x=x,
                y=y,
                w=0.4,
                h=0.3,
                name="import",
                props={"text": text[:2000] or Path(path).name, "font_size": 18, "color": "#1B1F2A", "font_family": "Segoe UI"},
            )
        )
    return kind
