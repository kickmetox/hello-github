"""Permanentes Boolean (Schweißen) — kein Gruppe-Container."""

from __future__ import annotations

from typing import Any, Sequence


def weld_frames(doc: Any, frame_ids: Sequence[str]) -> Any:
    """Vereinigt ausgewählte Form-/Bildrahmen zu einem Pfad-Objekt."""
    frames = [doc.frame_by_id(i) for i in frame_ids]
    frames = [f for f in frames if f is not None]
    if len(frames) < 2:
        raise ValueError("Schweißen braucht mindestens zwei Rahmen")
    kinds = {f.kind for f in frames}
    if "text" in kinds:
        raise ValueError("Textrahmen bleiben getrennt (Layout ≠ Inhalt)")
    xs = [f.x for f in frames]
    ys = [f.y for f in frames]
    r = [f.x + f.width for f in frames]
    b = [f.y + f.height for f in frames]
    x, y = min(xs), min(ys)
    w, h = max(r) - x, max(b) - y
    path = _united_path(frames, origin=(x, y))
    keeper = frames[0]
    keeper.kind = "shape"
    keeper.shape = "path"
    keeper.x, keeper.y, keeper.width, keeper.height = x, y, w, h
    keeper.path_kind = "weld"
    keeper.weld_path = path
    drop = [f.id for f in frames[1:]]
    doc.frames = [f for f in doc.frames if f.id not in drop]
    return keeper


def _united_path(frames: Sequence[Any], *, origin: tuple[float, float]) -> list[list[float]]:
    """Rechteck-Union als Polygon-Ring (Qt-Pfad wenn verfügbar)."""
    ox, oy = origin
    try:
        from PySide6.QtGui import QPainterPath
        from PySide6.QtCore import QRectF

        path = QPainterPath()
        first = True
        for fr in frames:
            p = QPainterPath()
            p.addRect(QRectF(fr.x - ox, fr.y - oy, fr.width, fr.height))
            path = p if first else path.united(p)
            first = False
        polys = []
        for poly in path.toSubpathPolygons():
            polys.append([[pt.x(), pt.y()] for pt in poly])
        if polys:
            return polys[0]
    except Exception:
        pass
    return [[0.0, 0.0], [max(f.width for f in frames), 0.0],
            [max(f.width for f in frames), max(f.height for f in frames)],
            [0.0, max(f.height for f in frames)]]
