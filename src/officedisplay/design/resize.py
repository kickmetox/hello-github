from __future__ import annotations

RESIZE_PRESETS = {
    "Präsentation 16:9": (1920, 1080),
    "Präsentation 4:3": (1440, 1080),
    "Quadrat": (1080, 1080),
    "Story 9:16": (1080, 1920),
    "Portrait 4:5": (1080, 1350),
    "A4": (794, 1123),
    "LinkedIn": (1200, 627),
    "Banner": (1920, 640),
}


def magic_resize(presentation, width: int, height: int) -> None:
    """Normalisierte Positionen bleiben. Schriften und Hochformat werden nachgeführt."""
    old_w = max(1, presentation.width)
    old_h = max(1, presentation.height)
    scale = min(width / old_w, height / old_h)
    portrait = (height / width) > (old_h / old_w) * 1.15
    for slide in presentation.slides:
        for obj in slide.objects:
            if obj.kind == "text" and "font_size" in obj.props:
                obj.props["font_size"] = max(12, int(int(obj.props["font_size"]) * scale))
            if portrait and obj.w > 0.78:
                obj.w = 0.9
        if portrait:
            _stack(slide.objects)
    presentation.width = int(width)
    presentation.height = int(height)


def _stack(objects) -> None:
    ordered = sorted(objects, key=lambda obj: (obj.y, obj.x))
    cursor = 0.06
    for obj in ordered:
        if obj.y < cursor and obj.kind in {"text", "shape", "image", "chart"}:
            obj.y = min(0.92, cursor)
        cursor = max(cursor, obj.y + obj.h + 0.02)


def align_objects(objects, mode: str) -> None:
    if not objects:
        return
    if mode == "left":
        edge = min(obj.x for obj in objects)
        for obj in objects:
            obj.x = edge
    elif mode == "right":
        edge = max(obj.x + obj.w for obj in objects)
        for obj in objects:
            obj.x = edge - obj.w
    elif mode == "hcenter":
        edge = sum(obj.x + obj.w / 2 for obj in objects) / len(objects)
        for obj in objects:
            obj.x = edge - obj.w / 2
    elif mode == "top":
        edge = min(obj.y for obj in objects)
        for obj in objects:
            obj.y = edge
    elif mode == "bottom":
        edge = max(obj.y + obj.h for obj in objects)
        for obj in objects:
            obj.y = edge - obj.h
    elif mode == "vcenter":
        edge = sum(obj.y + obj.h / 2 for obj in objects) / len(objects)
        for obj in objects:
            obj.y = edge - obj.h / 2
    elif mode == "distribute_h" and len(objects) >= 3:
        ordered = sorted(objects, key=lambda obj: obj.x)
        left = ordered[0].x
        right = ordered[-1].x
        gap = (right - left) / (len(ordered) - 1)
        for index, obj in enumerate(ordered):
            obj.x = left + gap * index
