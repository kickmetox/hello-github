from __future__ import annotations

import ctypes
from pathlib import Path

from officedisplay.paths import native_candidates


_LIB = None
_TRIED = False


def load_library():
    global _LIB, _TRIED
    if _TRIED:
        return _LIB
    _TRIED = True
    for candidate in native_candidates():
        if candidate.is_file():
            _LIB = ctypes.CDLL(str(candidate))
            _LIB.od_adjust_rgb.argtypes = [
                ctypes.POINTER(ctypes.c_uint8),
                ctypes.c_int,
                ctypes.c_float,
                ctypes.c_float,
                ctypes.c_int,
            ]
            _LIB.od_smooth_stroke.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.c_int, ctypes.c_int]
            break
    return _LIB


def using_native() -> bool:
    return load_library() is not None


def adjust_rgb(data: bytearray, pixels: int, brightness: float, contrast: float, grayscale: bool) -> None:
    lib = load_library()
    if lib is not None:
        buffer = (ctypes.c_uint8 * len(data)).from_buffer(data)
        lib.od_adjust_rgb(buffer, pixels, float(brightness), float(contrast), 1 if grayscale else 0)
        return
    _adjust_python(data, pixels, brightness, contrast, grayscale)


def _adjust_python(data: bytearray, pixels: int, brightness: float, contrast: float, grayscale: bool) -> None:
    for index in range(pixels):
        base = index * 3
        for channel in range(3):
            value = data[base + channel] / 255.0
            value = (value - 0.5) * contrast + 0.5 + brightness
            value = 0.0 if value < 0 else 1.0 if value > 1 else value
            data[base + channel] = int(value * 255 + 0.5)
        if grayscale:
            luma = int(0.299 * data[base] + 0.587 * data[base + 1] + 0.114 * data[base + 2] + 0.5)
            data[base] = data[base + 1] = data[base + 2] = luma


def smooth_stroke_inplace(coords: list[float], passes: int) -> list[float]:
    """coords ist eine flache Liste x,y,x,y. Die C++-Variante glättet, Python ist Ersatz."""
    lib = load_library()
    array = (ctypes.c_float * len(coords))(*coords)
    count = len(coords) // 2
    if lib is not None and count:
        lib.od_smooth_stroke(array, count, int(passes))
        return list(array)
    points = [(coords[i], coords[i + 1]) for i in range(0, len(coords), 2)]
    for _ in range(max(0, passes)):
        if len(points) < 3:
            break
        nxt = [points[0]]
        for index in range(1, len(points) - 1):
            nxt.append(
                (
                    (points[index - 1][0] + points[index][0] + points[index + 1][0]) / 3,
                    (points[index - 1][1] + points[index][1] + points[index + 1][1]) / 3,
                )
            )
        nxt.append(points[-1])
        points = nxt
    flat = []
    for x, y in points:
        flat.extend((x, y))
    return flat


def library_path() -> Path | None:
    for candidate in native_candidates():
        if candidate.is_file():
            return candidate
    return None
