"""Sichere PIL → Qt Pixmap/QImage Konvertierung — 2.6.48.

Vermeidet QImage(buffer)-Lebensdauerfallen und liefert nur detach'te Pixmaps.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtGui import QImage, QPixmap


def pil_to_qimage(image: Any) -> QImage:
    """PIL.Image → QImage (tiefe Kopie, nie shared Python-Buffer)."""
    if image is None:
        return QImage()
    try:
        if getattr(image, "mode", None) != "RGBA":
            image = image.convert("RGBA")
        w = int(image.width)
        h = int(image.height)
        if w <= 0 or h <= 0:
            return QImage()
        data = image.tobytes("raw", "RGBA")
        bpl = w * 4
        # Explizite bytesPerLine + sofort .copy() → Buffer darf danach GC werden
        qimg = QImage(data, w, h, bpl, QImage.Format_RGBA8888).copy()
        if qimg.isNull():
            return QImage()
        # ARGB32 ist auf Windows/Qt am robustesten für QPixmap
        return qimg.convertToFormat(QImage.Format_ARGB32)
    except Exception:
        return QImage()


def pil_to_qpixmap(image: Any) -> QPixmap:
    """PIL.Image → QPixmap; Null-Pixmap bei Fehler."""
    qimg = pil_to_qimage(image)
    if qimg.isNull():
        return QPixmap()
    pm = QPixmap.fromImage(qimg)
    return pm if pm is not None else QPixmap()


def pil_has_ink(image: Any, *, sample_step: int = 8, ink_threshold: int = 12) -> bool:
    """True wenn PIL-Bild nicht (fast) einfarbig weiß ist — 2.6.48."""
    if image is None:
        return False
    try:
        im = image.convert("RGB")
        w, h = im.size
        if w < 2 or h < 2:
            return False
        step = max(1, int(sample_step))
        ink = 0
        samples = 0
        for y in range(0, h, step):
            for x in range(0, w, step):
                samples += 1
                r, g, b = im.getpixel((x, y))
                if r < 250 or g < 250 or b < 250:
                    ink += 1
                    if ink >= ink_threshold:
                        return True
        return ink >= max(3, min(ink_threshold, samples // 200))
    except Exception:
        return False


def qpixmap_has_ink(pm: QPixmap, *, sample_step: int = 8, ink_threshold: int = 12) -> bool:
    """True wenn das Pixmap nicht (fast) einfarbig weiß/transparent ist — 2.6.48."""
    if pm is None or pm.isNull():
        return False
    w, h = int(pm.width()), int(pm.height())
    if w < 2 or h < 2:
        return False
    img = pm.toImage()
    if img.isNull():
        return False
    step = max(1, int(sample_step))
    ink = 0
    samples = 0
    for y in range(0, h, step):
        for x in range(0, w, step):
            c = img.pixelColor(x, y)
            samples += 1
            a = int(c.alpha())
            if a < 8:
                continue
            # Abweichung von Weiß
            if c.red() < 250 or c.green() < 250 or c.blue() < 250:
                ink += 1
                if ink >= ink_threshold:
                    return True
    # Sehr kleine Seiten: schon wenige dunkle Pixel reichen
    return ink >= max(3, min(ink_threshold, samples // 200))
