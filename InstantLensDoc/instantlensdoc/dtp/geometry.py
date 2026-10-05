"""Snap, Align, Distribute, Spalten, Bleed — DTP-Geometrie."""

from __future__ import annotations

from typing import Any, Iterable, Sequence


def snap_value(value: float, spacing: float, threshold: float = 6.0) -> float:
    """Nächsten Rasterpunkt wählen, wenn näher als threshold."""
    sp = float(spacing) if spacing else 0.0
    if sp <= 0.0:
        return float(value)
    n = round(float(value) / sp) * sp
    return n if abs(float(value) - n) <= float(threshold) else float(value)


def snap_point(
    x: float,
    y: float,
    *,
    grid_pt: float = 0.0,
    guides: Sequence[Any] = (),
    threshold: float = 6.0,
) -> tuple[float, float]:
    """Snap gegen Raster und Hilfslinien (Guides mit orientation/position_pt)."""
    sx, sy = float(x), float(y)
    if grid_pt and grid_pt > 0:
        sx = snap_value(sx, grid_pt, threshold)
        sy = snap_value(sy, grid_pt, threshold)
    for g in guides:
        ori = getattr(g, "orientation", None) or (g.get("orientation") if isinstance(g, dict) else "")
        pos = getattr(g, "position_pt", None)
        if pos is None and isinstance(g, dict):
            pos = g.get("position_pt", 0.0)
        pos = float(pos or 0.0)
        ori = str(ori or "").lower()
        if ori in ("v", "vertical") and abs(sx - pos) <= threshold:
            sx = pos
        if ori in ("h", "horizontal") and abs(sy - pos) <= threshold:
            sy = pos
    return sx, sy


def _frames(frames: Iterable[Any]) -> list[Any]:
    return [f for f in frames if f is not None]


def align_frames(frames: Sequence[Any], mode: str) -> list[Any]:
    """left|right|center|top|middle|bottom — ändert x/y der Rahmen."""
    items = _frames(frames)
    if len(items) < 2:
        return items
    mode = (mode or "left").lower()
    xs = [float(f.x) for f in items]
    ys = [float(f.y) for f in items]
    rights = [float(f.x) + float(f.width) for f in items]
    bottoms = [float(f.y) + float(f.height) for f in items]
    if mode == "left":
        v = min(xs)
        for f in items:
            f.x = v
    elif mode == "right":
        v = max(rights)
        for f in items:
            f.x = v - float(f.width)
    elif mode in ("center", "hcenter"):
        mid = (min(xs) + max(rights)) / 2.0
        for f in items:
            f.x = mid - float(f.width) / 2.0
    elif mode == "top":
        v = min(ys)
        for f in items:
            f.y = v
    elif mode == "bottom":
        v = max(bottoms)
        for f in items:
            f.y = v - float(f.height)
    elif mode in ("middle", "vcenter"):
        mid = (min(ys) + max(bottoms)) / 2.0
        for f in items:
            f.y = mid - float(f.height) / 2.0
    return items


def distribute_frames(frames: Sequence[Any], axis: str = "h") -> list[Any]:
    """Gleiche Abstände horizontal (h) oder vertikal (v)."""
    items = _frames(frames)
    if len(items) < 3:
        return items
    axis = (axis or "h").lower()
    if axis in ("h", "horizontal", "x"):
        items = sorted(items, key=lambda f: float(f.x))
        left = float(items[0].x)
        right = float(items[-1].x) + float(items[-1].width)
        total_w = sum(float(f.width) for f in items)
        gap = (right - left - total_w) / (len(items) - 1)
        x = left
        for f in items:
            f.x = x
            x += float(f.width) + gap
    else:
        items = sorted(items, key=lambda f: float(f.y))
        top = float(items[0].y)
        bottom = float(items[-1].y) + float(items[-1].height)
        total_h = sum(float(f.height) for f in items)
        gap = (bottom - top - total_h) / (len(items) - 1)
        y = top
        for f in items:
            f.y = y
            y += float(f.height) + gap
    return items


def column_rects(
    *,
    width_pt: float,
    height_pt: float,
    margin_left_pt: float,
    margin_right_pt: float,
    margin_top_pt: float,
    margin_bottom_pt: float,
    columns: int = 1,
    gutter_pt: float = 12.0,
) -> list[dict[str, float]]:
    """Spaltenrechtecke im Satzspiegel."""
    cols = max(1, int(columns))
    usable = max(8.0, float(width_pt) - float(margin_left_pt) - float(margin_right_pt))
    gut = float(gutter_pt) if cols > 1 else 0.0
    col_w = (usable - gut * (cols - 1)) / cols
    h = max(8.0, float(height_pt) - float(margin_top_pt) - float(margin_bottom_pt))
    out = []
    for i in range(cols):
        out.append(
            {
                "x": float(margin_left_pt) + i * (col_w + gut),
                "y": float(margin_top_pt),
                "width": col_w,
                "height": h,
                "column": float(i),
            }
        )
    return out


def bleed_rect(width_pt: float, height_pt: float, bleed_pt: float) -> dict[str, float]:
    b = max(0.0, float(bleed_pt))
    return {
        "x": -b,
        "y": -b,
        "width": float(width_pt) + 2 * b,
        "height": float(height_pt) + 2 * b,
    }


def margin_rect(
    width_pt: float,
    height_pt: float,
    *,
    top: float,
    right: float,
    bottom: float,
    left: float,
) -> dict[str, float]:
    return {
        "x": float(left),
        "y": float(top),
        "width": max(1.0, float(width_pt) - float(left) - float(right)),
        "height": max(1.0, float(height_pt) - float(top) - float(bottom)),
    }
