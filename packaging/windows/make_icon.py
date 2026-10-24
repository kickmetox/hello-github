#!/usr/bin/env python3
"""Baut flare.ico aus flare-icon.png. Die Vorlage wird nicht neu gezeichnet."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path


def paeth(left: int, up: int, up_left: int) -> int:
    estimate = left + up - up_left
    dist_left = abs(estimate - left)
    dist_up = abs(estimate - up)
    dist_up_left = abs(estimate - up_left)
    if dist_left <= dist_up and dist_left <= dist_up_left:
        return left
    if dist_up <= dist_up_left:
        return up
    return up_left


def decode_png(data: bytes) -> tuple[int, int, bytes]:
    """8-Bit-RGB oder RGBA, ohne Zeilensprung. Liefert dichtes RGBA."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("keine PNG-Datei")
    pos = 8
    width = height = color_type = None
    idat = bytearray()
    while pos + 12 <= len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        tag = data[pos + 4 : pos + 8]
        chunk = data[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if tag == b"IHDR":
            width, height, depth, color_type, comp, filt, interlace = struct.unpack(">IIBBBBB", chunk)
            if depth != 8 or color_type not in (2, 6) or comp != 0 or filt != 0 or interlace != 0:
                raise ValueError("PNG-Format wird nicht unterstützt")
        elif tag == b"IDAT":
            idat += chunk
        elif tag == b"IEND":
            break
    if width is None or height is None or color_type is None or not idat:
        raise ValueError("PNG unvollständig")
    channels = 4 if color_type == 6 else 3
    stride = width * channels
    raw = zlib.decompress(bytes(idat))
    expected = (stride + 1) * height
    if len(raw) < expected:
        raise ValueError("PNG-Daten zu kurz")
    rows = bytearray()
    cursor = 0
    previous = bytearray(stride)
    for _y in range(height):
        filter_type = raw[cursor]
        cursor += 1
        scan = raw[cursor : cursor + stride]
        cursor += stride
        recon = bytearray(stride)
        for x, value in enumerate(scan):
            left = recon[x - channels] if x >= channels else 0
            up = previous[x]
            up_left = previous[x - channels] if x >= channels else 0
            if filter_type == 0:
                recon[x] = value
            elif filter_type == 1:
                recon[x] = (value + left) & 255
            elif filter_type == 2:
                recon[x] = (value + up) & 255
            elif filter_type == 3:
                recon[x] = (value + ((left + up) // 2)) & 255
            elif filter_type == 4:
                recon[x] = (value + paeth(left, up, up_left)) & 255
            else:
                raise ValueError(f"PNG-Filter {filter_type}")
        if channels == 3:
            rgba = bytearray()
            for x in range(0, stride, 3):
                rgba.extend(recon[x : x + 3])
                rgba.append(255)
            recon = rgba
        rows.extend(recon)
        previous = recon
    return width, height, bytes(rows)


def box_resize(width: int, height: int, rgba: bytes, size: int) -> bytes:
    """Mittelwert je Block. Alpha wird vormultipliziert, das Bild bleibt dasselbe."""
    out = bytearray(size * size * 4)
    dest = 0
    for y in range(size):
        y0 = y * height // size
        y1 = max(y0 + 1, (y + 1) * height // size)
        for x in range(size):
            x0 = x * width // size
            x1 = max(x0 + 1, (x + 1) * width // size)
            red = green = blue = alpha = 0
            count = 0
            for yy in range(y0, y1):
                row = yy * width * 4
                for xx in range(x0, x1):
                    i = row + xx * 4
                    a = rgba[i + 3]
                    red += rgba[i] * a
                    green += rgba[i + 1] * a
                    blue += rgba[i + 2] * a
                    alpha += a
                    count += 1
            if alpha:
                out[dest] = red // alpha
                out[dest + 1] = green // alpha
                out[dest + 2] = blue // alpha
                out[dest + 3] = alpha // count
            dest += 4
    return bytes(out)


def png_rgba(size: int, rgba: bytes) -> bytes:
    raw = bytearray()
    stride = size * 4
    for y in range(size):
        raw.append(0)
        raw.extend(rgba[y * stride : (y + 1) * stride])

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    compressed = zlib.compress(bytes(raw), 9)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")


def ico_from_pngs(images: list[tuple[int, bytes]]) -> bytes:
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = bytearray()
    blob = bytearray()
    for size, image in images:
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(image), offset)
        offset += len(image)
        blob += image
    return bytes(header + entries + blob)


def looks_like_artwork(rgba: bytes) -> bool:
    """Blaues Feld und orangefarbener Flare. Ein graues Platzhalter-Icon fällt hier durch."""
    blue = orange = 0
    for i in range(0, len(rgba), 4):
        red, green, blue_ch, alpha = rgba[i : i + 4]
        if alpha < 128:
            continue
        if blue_ch > 140 and blue_ch > red + 30 and blue_ch > green:
            blue += 1
        if red > 200 and 40 < green < 180 and blue_ch < 80:
            orange += 1
    return blue > 8 and orange > 0


def build(source: Path, dest: Path, sizes: list[int] | None = None) -> None:
    sizes = sizes or [16, 32, 48, 256]
    width, height, rgba = decode_png(source.read_bytes())
    images = []
    for size in sizes:
        scaled = rgba if (width, height) == (size, size) else box_resize(width, height, rgba, size)
        if size == 32 and not looks_like_artwork(scaled):
            raise ValueError("Icon enthält das Flare-Bild nicht")
        images.append((size, png_rgba(size, scaled)))
    dest.write_bytes(ico_from_pngs(images))


def main() -> None:
    folder = Path(__file__).resolve().parent
    source = folder / "flare-icon.png"
    dest = folder / "flare.ico"
    if not source.is_file():
        raise SystemExit(f"Vorlage fehlt: {source}")
    build(source, dest)
    print(f"{dest} ({dest.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
