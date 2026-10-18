"""Erzeugt das mitgelieferte SphereDrive-Symbol. Pillow wird nur dafür gebraucht."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw


def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def draw(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pixels = image.load()
    margin = size * 0.08
    radius = size * 0.22
    left, top = margin, margin
    right, bottom = size - margin, size - margin

    def inside_round_rect(x: float, y: float) -> bool:
        if left <= x <= right and top + radius <= y <= bottom - radius:
            return True
        if top <= y <= bottom and left + radius <= x <= right - radius:
            return True
        for cx, cy in (
            (left + radius, top + radius),
            (right - radius, top + radius),
            (left + radius, bottom - radius),
            (right - radius, bottom - radius),
        ):
            if (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2:
                return True
        return False

    cx, cy, sphere = size * 0.50, size * 0.46, size * 0.27
    hx, hy = cx - sphere * 0.38, cy - sphere * 0.42
    for y in range(size):
        for x in range(size):
            if not inside_round_rect(x + 0.5, y + 0.5):
                continue
            pixels[x, y] = (14, 20, 27, 255)
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            dist = math.hypot(dx, dy)
            if dist <= sphere:
                t = dist / sphere
                red = _lerp(186, 29, t)
                green = _lerp(230, 111, t)
                blue = _lerp(253, 168, t)
                highlight = math.hypot(x + 0.5 - hx, y + 0.5 - hy) / sphere
                if highlight < 0.55:
                    mix = (0.55 - highlight) / 0.55
                    red = _lerp(red, 244, mix * 0.85)
                    green = _lerp(green, 252, mix * 0.85)
                    blue = _lerp(blue, 255, mix * 0.85)
                shade = (dy / sphere + 1) / 2
                red = int(red * (0.82 + 0.18 * (1 - shade)))
                green = int(green * (0.82 + 0.18 * (1 - shade)))
                blue = int(blue * (0.82 + 0.18 * (1 - shade)))
                pixels[x, y] = (red, green, blue, 255)

    draw_ring = ImageDraw.Draw(image)
    ring = sphere * 0.92
    width = max(2, size // 28)
    draw_ring.arc(
        (cx - ring, cy - ring * 0.42, cx + ring, cy + ring * 0.42),
        start=18,
        end=162,
        fill=(43, 187, 173, 230),
        width=width,
    )
    return image


def main() -> None:
    root = Path(__file__).resolve().parents[1] / "assets"
    root.mkdir(parents=True, exist_ok=True)
    master = draw(256)
    master.save(root / "SphereDrive.png")
    master.save(
        root / "SphereDrive.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


if __name__ == "__main__":
    main()
