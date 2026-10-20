from __future__ import annotations

import math
from io import BytesIO


def cube_mesh() -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]:
    vertices = [
        (-1, -1, -1),
        (1, -1, -1),
        (1, 1, -1),
        (-1, 1, -1),
        (-1, -1, 1),
        (1, -1, 1),
        (1, 1, 1),
        (-1, 1, 1),
    ]
    faces = [
        (0, 1, 2),
        (0, 2, 3),
        (4, 6, 5),
        (4, 7, 6),
        (0, 4, 5),
        (0, 5, 1),
        (2, 6, 7),
        (2, 7, 3),
        (1, 5, 6),
        (1, 6, 2),
        (0, 3, 7),
        (0, 7, 4),
    ]
    return vertices, faces


def pyramid_mesh() -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]:
    vertices = [(0, -1.2, 0), (-1, 1, -1), (1, 1, -1), (1, 1, 1), (-1, 1, 1)]
    faces = [(0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 1), (1, 4, 3), (1, 3, 2)]
    return vertices, faces


def load_obj(text: str) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]:
    vertices = []
    faces = []
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "v" and len(parts) >= 4:
            vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
        elif parts[0] == "f" and len(parts) >= 4:
            idx = []
            for item in parts[1:4]:
                idx.append(int(item.split("/")[0]) - 1)
            faces.append((idx[0], idx[1], idx[2]))
    if not vertices or not faces:
        raise ValueError("OBJ ohne Dreiecke")
    return vertices, faces


def _rotate(point, yaw: float, pitch: float):
    x, y, z = point
    cy, sy = math.cos(yaw), math.sin(yaw)
    x, z = x * cy - z * sy, x * sy + z * cy
    cp, sp = math.cos(pitch), math.sin(pitch)
    y, z = y * cp - z * sp, y * sp + z * cp
    return x, y, z


def render_rgba(vertices, faces, yaw: float, pitch: float, size: int = 360) -> bytes:
    """Flaches Schattieren, Maleralgorithmus, ohne GPU."""
    projected = []
    for vertex in vertices:
        x, y, z = _rotate(vertex, yaw, pitch)
        depth = z + 4.0
        factor = 2.4 / depth
        projected.append((x * factor, y * factor, z))
    ordered = []
    for face in faces:
        zavg = sum(projected[i][2] for i in face) / 3
        ordered.append((zavg, face))
    ordered.sort()
    pixels = bytearray([245, 247, 252, 255] * (size * size))

    def put(px, py, color):
        if 0 <= px < size and 0 <= py < size:
            pos = (py * size + px) * 4
            pixels[pos : pos + 4] = bytes(color)

    def edge(ax, ay, bx, by, y):
        if ay == by:
            return ax
        return ax + (bx - ax) * ((y - ay) / (by - ay))

    for _z, face in ordered:
        pts = []
        for index in face:
            x, y, _z = projected[index]
            pts.append((int(size / 2 + x * size * 0.22), int(size / 2 + y * size * 0.22)))
        shade = 80 + int((_z + 2) * 40) % 140
        color = (11, 80 + shade // 3, 180 + shade // 5, 255)
        ys = [p[1] for p in pts]
        y0, y1 = max(0, min(ys)), min(size - 1, max(ys))
        for y in range(y0, y1 + 1):
            xs = []
            for a, b in ((pts[0], pts[1]), (pts[1], pts[2]), (pts[2], pts[0])):
                if (a[1] <= y <= b[1]) or (b[1] <= y <= a[1]):
                    xs.append(edge(a[0], a[1], b[0], b[1], y))
            if len(xs) >= 2:
                left, right = int(min(xs)), int(max(xs))
                for x in range(max(0, left), min(size - 1, right) + 1):
                    put(x, y, color)
    return bytes(pixels)


def render_png(kind: str = "cube", yaw: float = 0.6, pitch: float = 0.4, obj_text: str | None = None) -> bytes:
    from PIL import Image

    if obj_text:
        vertices, faces = load_obj(obj_text)
    elif kind == "pyramid":
        vertices, faces = pyramid_mesh()
    else:
        vertices, faces = cube_mesh()
    raw = render_rgba(vertices, faces, yaw, pitch)
    image = Image.frombytes("RGBA", (360, 360), raw)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
