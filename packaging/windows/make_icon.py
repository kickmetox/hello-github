#!/usr/bin/env python3
"""Lupen-Icon als ICO. Reicht für Windows 11, ohne Pillow."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path


def pixel(size: int, x: int, y: int) -> tuple[int, int, int, int]:
    cx = cy = (size - 1) / 2
    nx = (x - cx) / size
    ny = (y - cy) / size
    lx = nx + 0.05
    ly = ny + 0.07
    dist = (lx * lx + ly * ly) ** 0.5
    on_ring = abs(dist - 0.20) < 0.045
    along = ((nx - 0.10) + (ny - 0.10)) / 2
    cross = ((nx - 0.10) - (ny - 0.10)) / 2
    on_handle = 0.06 < along < 0.34 and abs(cross) < 0.032
    if on_ring or on_handle:
        return (245, 245, 247, 255)
    if max(abs(nx), abs(ny)) < 0.46:
        return (32, 32, 36, 255)
    return (0, 0, 0, 0)


def png(size: int) -> bytes:
    raw = bytearray()
    for y in range(size):
        raw.append(0)
        for x in range(size):
            raw.extend(pixel(size, x, y))

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    compressed = zlib.compress(bytes(raw), 9)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")


def ico(sizes: list[int]) -> bytes:
    images = [png(size) for size in sizes]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = bytearray()
    blob = bytearray()
    for size, image in zip(sizes, images):
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(image), offset)
        offset += len(image)
        blob += image
    return bytes(header + entries + blob)


def main() -> None:
    dest = Path(__file__).with_name("flare.ico")
    dest.write_bytes(ico([16, 32, 48, 256]))
    print(f"{dest} ({dest.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
