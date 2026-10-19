from __future__ import annotations

from pathlib import Path

from officedisplay.model.presentation import SlideObject, new_id


IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff"}
VIDEOS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".wmv"}
TEXTS = {".txt", ".md", ".markdown", ".pdf"}


def classify(path: str) -> str:
    suffix = Path(path).suffix.lower()
    if suffix in IMAGES:
        return "image"
    if suffix in VIDEOS:
        return "video"
    if suffix == ".pptx":
        return "pptx"
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
        slide.objects.append(
            SlideObject(
                id=new_id(),
                kind="image",
                x=x,
                y=y,
                w=0.36,
                h=0.28,
                name=Path(path).stem,
                props={"path": path},
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
