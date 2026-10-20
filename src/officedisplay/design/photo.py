from __future__ import annotations

from io import BytesIO


def _load(path: str):
    from PIL import Image

    return Image.open(path).convert("RGBA")


def adjust(path: str, brightness: float = 0.0, contrast: float = 1.0, grayscale: bool = False) -> bytes:
    """Helligkeit/Kontrast über die C++-Bibliothek, sonst dieselbe Formel in Python."""
    image = _load(path)
    raw = bytearray(image.convert("RGB").tobytes())
    pixels = len(raw) // 3
    from officedisplay.native.cpp_bridge import adjust_rgb

    adjust_rgb(raw, pixels, brightness, contrast, grayscale)
    from PIL import Image

    out = Image.frombytes("RGB", image.size, bytes(raw)).convert("RGBA")
    out.putalpha(image.getchannel("A"))
    return _png(out)


def color_filter(path: str, mode: str) -> bytes:
    from PIL import ImageEnhance, ImageFilter, ImageOps

    image = _load(path)
    if mode == "gray":
        image = ImageOps.grayscale(image).convert("RGBA")
    elif mode == "blur":
        image = image.filter(ImageFilter.GaussianBlur(radius=2))
    elif mode == "sharpen":
        image = image.filter(ImageFilter.SHARPEN)
    elif mode == "flip":
        image = image.transpose(image.Transpose.FLIP_LEFT_RIGHT)
    elif mode == "warm":
        image = ImageEnhance.Color(image).enhance(1.35)
    return _png(image)


def knockout_corners(path: str, tolerance: int = 36) -> bytes:
    """Einfaches Freistellen nach der Eckfarbe. Kein Cloud-Modell."""
    image = _load(path)
    pixels = image.load()
    width, height = image.size
    corners = [pixels[0, 0], pixels[width - 1, 0], pixels[0, height - 1], pixels[width - 1, height - 1]]
    base = tuple(sum(c[i] for c in corners) // 4 for i in range(3))
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if abs(r - base[0]) <= tolerance and abs(g - base[1]) <= tolerance and abs(b - base[2]) <= tolerance:
                pixels[x, y] = (r, g, b, 0)
    return _png(image)


def _png(image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
