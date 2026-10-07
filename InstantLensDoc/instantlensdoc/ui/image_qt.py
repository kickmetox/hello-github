"""Sichere PIL → Qt Pixmap/QImage Konvertierung — 2.6.49.

Vermeidet QImage(buffer)-Lebensdauerfallen und liefert nur detach'te Pixmaps.
Bevorzugt undurchsichtiges RGB32 (kein Alpha-Ghost auf Windows).
"""

from __future__ import annotations

from typing import Any

from PySide6.QtGui import QImage, QPixmap


def pil_to_qimage(image: Any) -> QImage:
    """PIL.Image → QImage (tiefe Kopie, nie shared Python-Buffer)."""
    if image is None:
        return QImage()
    try:
        # Undurchsichtiges RGB — Alpha-Kanal auf Windows oft Ursache für „weiß“
        # trotz gültigem Pixmap (vollständig transparent gegen weißen Scroll-BG).
        if getattr(image, "mode", None) != "RGB":
            image = image.convert("RGB")
        w = int(image.width)
        h = int(image.height)
        if w <= 0 or h <= 0:
            return QImage()
        data = image.tobytes("raw", "RGB")
        bpl = w * 3
        # Explizite bytesPerLine + sofort .copy() → Buffer darf danach GC werden
        qimg = QImage(data, w, h, bpl, QImage.Format_RGB888).copy()
        if qimg.isNull():
            return QImage()
        # RGB32 ist auf Windows/Qt am robustesten für QPixmap (kein Alpha)
        return qimg.convertToFormat(QImage.Format_RGB32)
    except Exception:
        return QImage()


def pil_to_qpixmap(image: Any) -> QPixmap:
    """PIL.Image → QPixmap; Null-Pixmap bei Fehler."""
    qimg = pil_to_qimage(image)
    if qimg.isNull():
        return QPixmap()
    pm = QPixmap.fromImage(qimg)
    if pm is None or pm.isNull():
        return QPixmap()
    # Zusätzliche QPixmap-Kopie: trennt von QImage-Lebensdauer komplett
    return QPixmap(pm)


def pil_has_ink(image: Any, *, sample_step: int = 8, ink_threshold: int = 12) -> bool:
    """True wenn PIL-Bild nicht (fast) einfarbig weiß/grau-Platzhalter ist — 2.6.49."""
    if image is None:
        return False
    try:
        im = image.convert("RGB")
        w, h = im.size
        if w < 2 or h < 2:
            return False
        # Kleine Thumbs: dichter samplen + niedrigere Schwelle (Anti-Alias) — 2.6.49
        step = max(1, int(sample_step))
        need = int(ink_threshold)
        if w * h < 12000:
            step = min(step, 3)
            need = min(need, 4)
        ink = 0
        samples = 0
        # Einheitlicher hellgrauer Placeholder (Qt.lightGray ~211) zählt nicht als Inhalt
        near_placeholder = 0
        for y in range(0, h, step):
            for x in range(0, w, step):
                samples += 1
                r, g, b = im.getpixel((x, y))
                if abs(r - 211) <= 12 and abs(g - 211) <= 12 and abs(b - 211) <= 12:
                    near_placeholder += 1
                    continue
                if r < 250 or g < 250 or b < 250:
                    ink += 1
                    if ink >= need:
                        return True
        if samples > 0 and near_placeholder >= int(samples * 0.92):
            return False
        return ink >= max(2, min(need, max(2, samples // 80)))
    except Exception:
        return False


def qpixmap_has_ink(pm: QPixmap, *, sample_step: int = 8, ink_threshold: int = 12) -> bool:
    """True wenn das Pixmap nicht (fast) einfarbig weiß/grau-Platzhalter ist — 2.6.49."""
    if pm is None or pm.isNull():
        return False
    w, h = int(pm.width()), int(pm.height())
    if w < 2 or h < 2:
        return False
    img = pm.toImage()
    if img.isNull():
        return False
    step = max(1, int(sample_step))
    need = int(ink_threshold)
    if w * h < 12000:
        step = min(step, 3)
        need = min(need, 4)
    ink = 0
    samples = 0
    near_placeholder = 0
    for y in range(0, h, step):
        for x in range(0, w, step):
            c = img.pixelColor(x, y)
            samples += 1
            a = int(c.alpha())
            if a < 8:
                continue
            r, g, b = int(c.red()), int(c.green()), int(c.blue())
            if abs(r - 211) <= 12 and abs(g - 211) <= 12 and abs(b - 211) <= 12:
                near_placeholder += 1
                continue
            if r < 250 or g < 250 or b < 250:
                ink += 1
                if ink >= need:
                    return True
    if samples > 0 and near_placeholder >= int(samples * 0.92):
        return False
    return ink >= max(2, min(need, max(2, samples // 80)))
