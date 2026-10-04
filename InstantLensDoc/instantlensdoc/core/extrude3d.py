"""Begrenzter 3D-Extrusions-Viewer / Platzhalter — 2.6.27.

Scope (dokumentiert, bewusst begrenzt):
- Isometrische Vorschau einer Rechteck-/Ellipsen-Extrusion (QPainter, kein OpenGL)
- Kein Mesh-Import, keine GLTF/OBJ-Szene, keine Beleuchtung/Physik
- Für DTP-Skizzen / Präsentations-Platzhalter — nicht als CAD-Viewer

Wenn volle 3D-Engine zu schwer wäre: dieser Limited Viewer ersetzt den leeren Stub.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Literal

from instantlensdoc import __version__

ShapeKind = Literal["rectangle", "ellipse", "triangle"]

SCOPE_DE = (
    "Begrenzter 3D-Viewer: isometrische Extrusion einfacher Formen (Rechteck/Ellipse/"
    "Dreieck). Kein Mesh-Import, kein OpenGL, keine Animation. Skizzen/Platzhalter."
)
SCOPE_EN = (
    "Limited 3D viewer: isometric extrusion of simple shapes (rectangle/ellipse/"
    "triangle). No mesh import, no OpenGL, no animation. Sketch/placeholder only."
)


@dataclass
class ExtrudeParams:
    shape: ShapeKind = "rectangle"
    width: float = 120.0
    height: float = 80.0
    depth: float = 40.0
    color: str = "#4A90D9"
    angle_deg: float = 30.0  # isometrischer Kippwinkel

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def clamp_params(p: ExtrudeParams) -> ExtrudeParams:
    p.width = max(8.0, min(400.0, float(p.width)))
    p.height = max(8.0, min(400.0, float(p.height)))
    p.depth = max(4.0, min(200.0, float(p.depth)))
    shape = str(p.shape or "rectangle").lower()
    if shape not in ("rectangle", "ellipse", "triangle"):
        shape = "rectangle"
    p.shape = shape  # type: ignore[assignment]
    p.angle_deg = max(10.0, min(45.0, float(p.angle_deg)))
    return p


def project_isometric(
    x: float, y: float, z: float, *, angle_deg: float = 30.0
) -> tuple[float, float]:
    """Einfache isometrische Projektion → 2D."""
    a = math.radians(angle_deg)
    # Klassisch: x' = (x - z) * cos(a), y' = y + (x + z) * sin(a)
    xp = (x - z) * math.cos(a)
    yp = y + (x + z) * math.sin(a)
    return xp, yp


def extrude_faces(params: ExtrudeParams) -> dict[str, Any]:
    """
    Liefert Polygon-Punkte für Vorder-/Seiten-/Deckflächen (2D-projiziert).

    Koordinaten relativ zum Form-Zentrum (0,0), z=0 vorne, z=depth hinten.
    """
    p = clamp_params(params)
    w, h, d = p.width, p.height, p.depth
    hw, hh = w / 2, h / 2

    def front_poly() -> list[tuple[float, float, float]]:
        if p.shape == "ellipse":
            pts = []
            for i in range(24):
                t = 2 * math.pi * i / 24
                pts.append((hw * math.cos(t), hh * math.sin(t), 0.0))
            return pts
        if p.shape == "triangle":
            return [(0.0, -hh, 0.0), (hw, hh, 0.0), (-hw, hh, 0.0)]
        return [(-hw, -hh, 0.0), (hw, -hh, 0.0), (hw, hh, 0.0), (-hw, hh, 0.0)]

    front = front_poly()
    back = [(x, y, d) for x, y, _ in front]

    def proj(pts):
        return [project_isometric(x, y, z, angle_deg=p.angle_deg) for x, y, z in pts]

    # Seitenflächen: Kanten front→back
    sides = []
    n = len(front)
    for i in range(n):
        j = (i + 1) % n
        quad = [front[i], front[j], back[j], back[i]]
        sides.append(proj(quad))

    return {
        "shape": p.shape,
        "front": proj(front),
        "back": proj(back),
        "sides": sides,
        "params": p.to_dict(),
        "scope": SCOPE_DE,
        "version": __version__,
    }


def extrude3d_info() -> dict[str, Any]:
    return {
        "name": "3D-Extrusion",
        "stub": False,
        "live": True,
        "limited": True,
        "scope_de": SCOPE_DE,
        "scope_en": SCOPE_EN,
        "shapes": ["rectangle", "ellipse", "triangle"],
        "engine": "qpainter-isometric",
        "message": f"3D-Extrusion {__version__} (limited viewer): {SCOPE_DE}",
        "version_marker": __version__,
        "not_production_ready": False,
    }
