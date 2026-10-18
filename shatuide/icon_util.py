"""Programm-Icon.

Liegt im Installationsverzeichnis bereits eine Grafik (icon.png, grafik.png, …),
wird sie verwendet. Nicht quadratische PNGs werden auf die Mitte zugeschnitten,
weil das Programm-Icon dort sitzt.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

from shatuide.paths import ASSETS, ROOT, WINDOWS_HOME

ICON_NAME_PARTS = ("icon", "logo", "grafik", "graphic", "bild", "app", "programm")
EXACT_ICON_NAMES = {"shatuide", "shatu-ide"}
ICON_SUFFIXES = {".png", ".ico", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def encode_png(width: int, height: int, rows: list[bytes]) -> bytes:
    raw = b"".join(b"\x00" + row for row in rows)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(raw, 9)) + _chunk(b"IEND", b"")


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def decode_png(data: bytes) -> tuple[int, int, bytearray] | None:
    """Dekodiert nicht verschachtelte 8-bit-RGB/RGBA-PNGs. Sonst None."""
    signature = b"\x89PNG\r\n\x1a\n"
    if not data.startswith(signature):
        return None
    pos = len(signature)
    width = height = None
    color_type = None
    bit_depth = None
    interlace = None
    idat = bytearray()
    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        tag = data[pos + 4 : pos + 8]
        chunk = data[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if tag == b"IHDR":
            width, height, bit_depth, color_type, _comp, _filter, interlace = struct.unpack(">IIBBBBB", chunk)
        elif tag == b"IDAT":
            idat.extend(chunk)
        elif tag == b"IEND":
            break
    if width is None or interlace or bit_depth != 8 or color_type not in (2, 6):
        return None
    channels = 3 if color_type == 2 else 4
    try:
        raw = zlib.decompress(bytes(idat))
    except zlib.error:
        return None
    stride = width * channels
    expected = (stride + 1) * height
    if len(raw) < expected:
        return None
    rows: list[bytearray] = []
    src = 0
    for _y in range(height):
        filter_type = raw[src]
        src += 1
        row = bytearray(raw[src : src + stride])
        src += stride
        prev = rows[-1] if rows else bytearray(stride)
        if filter_type == 0:
            pass
        elif filter_type == 1:
            for i in range(stride):
                left = row[i - channels] if i >= channels else 0
                row[i] = (row[i] + left) & 255
        elif filter_type == 2:
            for i in range(stride):
                row[i] = (row[i] + prev[i]) & 255
        elif filter_type == 3:
            for i in range(stride):
                left = row[i - channels] if i >= channels else 0
                row[i] = (row[i] + ((left + prev[i]) // 2)) & 255
        elif filter_type == 4:
            for i in range(stride):
                left = row[i - channels] if i >= channels else 0
                up = prev[i]
                ul = prev[i - channels] if i >= channels else 0
                row[i] = (row[i] + _paeth(left, up, ul)) & 255
        else:
            return None
        rows.append(row)
    rgba = bytearray()
    for row in rows:
        if channels == 4:
            rgba.extend(row)
        else:
            for i in range(0, len(row), 3):
                rgba.extend(row[i : i + 3])
                rgba.append(255)
    return width, height, rgba


def crop_center_square(width: int, height: int, rgba: bytearray, out_size: int = 256) -> bytes:
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    rows = []
    for y in range(out_size):
        sy = top + min(side - 1, int(y * side / out_size))
        row = bytearray()
        for x in range(out_size):
            sx = left + min(side - 1, int(x * side / out_size))
            i = (sy * width + sx) * 4
            row.extend(rgba[i : i + 4])
        rows.append(bytes(row))
    return encode_png(out_size, out_size, rows)


def _inside_round(x: int, y: int, size: int, radius: int) -> bool:
    if radius <= x < size - radius and radius <= y < size - radius:
        return True
    if x < radius and y < radius:
        return (x - radius) ** 2 + (y - radius) ** 2 <= radius ** 2
    if x >= size - radius and y < radius:
        return (x - (size - radius - 1)) ** 2 + (y - radius) ** 2 <= radius ** 2
    if x < radius and y >= size - radius:
        return (x - radius) ** 2 + (y - (size - radius - 1)) ** 2 <= radius ** 2
    if x >= size - radius and y >= size - radius:
        return (x - (size - radius - 1)) ** 2 + (y - (size - radius - 1)) ** 2 <= radius ** 2
    return 0 <= x < size and 0 <= y < size


def generated_icon_png(size: int = 64) -> bytes:
    """Ersatz-Icon, falls im Zielordner noch keine Grafik liegt."""
    bg = (28, 27, 25, 255)
    amber = (224, 164, 90, 255)
    ink = (28, 27, 25, 255)
    green = (163, 177, 138, 255)
    pix = [[(0, 0, 0, 0) for _ in range(size)] for _ in range(size)]
    for y in range(size):
        for x in range(size):
            if _inside_round(x, y, size, 12):
                pix[y][x] = bg
    cx = (size - 1) / 2
    cy = (size - 1) / 2
    for y in range(size):
        for x in range(size):
            if (x - cx) ** 2 + (y - cy) ** 2 <= 20 ** 2:
                pix[y][x] = amber
    glyph = [
        "011110",
        "110001",
        "110000",
        "011110",
        "000011",
        "100011",
        "011110",
    ]
    scale = 3
    gw, gh = len(glyph[0]) * scale, len(glyph) * scale
    ox = int(cx - gw / 2) + 1
    oy = int(cy - gh / 2) + 1
    for gy, row in enumerate(glyph):
        for gx, bit in enumerate(row):
            if bit != "1":
                continue
            for dy in range(scale):
                for dx in range(scale):
                    x, y = ox + gx * scale + dx, oy + gy * scale + dy
                    if 0 <= x < size and 0 <= y < size:
                        pix[y][x] = ink
    for y in range(8, 14):
        for x in range(8, 14):
            if (x - 11) ** 2 + (y - 11) ** 2 <= 8:
                pix[y][x] = green
    rows = [bytes(channel for px in row for channel in px) for row in pix]
    return encode_png(size, size, rows)


def write_ico(png_bytes: bytes, size: int) -> bytes:
    width = 0 if size >= 256 else size
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack("<BBBBHHII", width, width, 0, 0, 1, 32, len(png_bytes), 6 + 16)
    return header + entry + png_bytes


def _candidate_dirs() -> list[Path]:
    dirs = [ROOT]
    if WINDOWS_HOME not in dirs:
        dirs.append(WINDOWS_HOME)
    return dirs


def icon_priority(path: Path) -> tuple[int, int, int] | None:
    """Niedrigere Werte gewinnen. shatuide.jpg steht vor icon.png und grafik.png."""
    if path.suffix.lower() not in ICON_SUFFIXES:
        return None
    low = path.stem.lower()
    if low not in EXACT_ICON_NAMES and not any(part in low for part in ICON_NAME_PARTS):
        return None
    exact = 0 if low in EXACT_ICON_NAMES else 1
    named = 0 if "icon" in low else 1
    return (exact, named, len(path.name))


def find_user_icon() -> Path | None:
    found: list[tuple[tuple[int, int, int], Path]] = []
    for directory in _candidate_dirs():
        if not directory.is_dir():
            continue
        try:
            entries = list(directory.iterdir())
        except OSError:
            continue
        for entry in entries:
            if not entry.is_file():
                continue
            rank = icon_priority(entry)
            if rank is not None:
                found.append((rank, entry))
    if not found:
        return None
    found.sort(key=lambda item: item[0])
    return found[0][1]


def load_icon_bytes() -> tuple[bytes, str]:
    """Gibt (bytes, content_type) zurück. PNG wird bei Bedarf auf die Mitte beschnitten."""
    user = find_user_icon()
    if user is not None:
        data = user.read_bytes()
        suffix = user.suffix.lower()
        if suffix == ".png":
            decoded = decode_png(data)
            if decoded is not None:
                width, height, rgba = decoded
                if abs(width - height) > 8 or width > 512:
                    return crop_center_square(width, height, rgba), "image/png"
            return data, "image/png"
        types = {
            ".ico": "image/x-icon",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
        }
        return data, types.get(suffix, "application/octet-stream")
    bundled = ASSETS / "icon.png"
    if bundled.is_file():
        return bundled.read_bytes(), "image/png"
    return generated_icon_png(), "image/png"


def ensure_bundled_icon() -> Path:
    ASSETS.mkdir(parents=True, exist_ok=True)
    path = ASSETS / "icon.png"
    png = generated_icon_png()
    path.write_bytes(png)
    ico = ASSETS / "icon.ico"
    ico.write_bytes(write_ico(png, 64))
    return path
