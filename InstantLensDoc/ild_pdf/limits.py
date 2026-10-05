"""Grenzen und Diagnose für große / problematische PDFs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# Soft-Warnung (Dialog), Hard-Cap für Seitenanzahl beim Öffnen ohne Override
SOFT_PAGE_WARN = 200
HARD_PAGE_LIMIT = 2500
SOFT_SIZE_MB = 80.0
HARD_SIZE_MB = 512.0
# Thumbnail-Lazy-Load: Default-Schwellwert (Settings: 25/50/100) — 1.3.1
THUMB_LAZY_THRESHOLD = 50
# Ab diesem Schwellwert: nur Viewport±Prefetch rendern (kein Voll-Queue) — 2.6.37
THUMB_VIRTUAL_THRESHOLD = 80
# Platzhalter-Icons in Chunks anlegen (UI bleibt responsiv) — 2.6.37
THUMB_PLACEHOLDER_CHUNK = 40
# Native PageLabels-Scan beim Open überspringen (pro Seite get_page_label) — 2.6.37
PAGE_LABELS_SCAN_THRESHOLD = 120
# Volltext-Extraktion (alle Seiten) erst nach Bestätigung — 2.6.37
TEXT_EXTRACT_ALL_WARN_PAGES = SOFT_PAGE_WARN
# Doc-Stats: Wörter nur auf den ersten N Seiten schätzen (große PDFs) — 2.6.37
STATS_WORD_SAMPLE_PAGES = 8
# Hinweis für langsame/hängende Öffnungen (kein harter Kill — nur UX)
OPEN_TIMEOUT_HINT_SEC = 30
OPEN_TIMEOUT_HINT = (
    f"Hinweis: Bleibt das Öffnen länger als ~{OPEN_TIMEOUT_HINT_SEC}s stehen oder "
    "bricht ab, PDF teilen/verkleinern (PDF → zusammenführen/teilen) oder Passwort prüfen."
)
# Zoom-Render: Pixel-Obergrenze (Breite×Höhe der Bitmap)
MAX_RENDER_PIXELS = 40_000_000


@dataclass
class PdfHealth:
    path: Path
    page_count: int
    size_bytes: int
    warnings: List[str]
    errors: List[str]

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)

    @property
    def ok_to_open(self) -> bool:
        return not self.errors

    @property
    def needs_confirm(self) -> bool:
        return bool(self.warnings) and self.ok_to_open


def inspect_pdf(path: str | Path, *, password: Optional[str] = None) -> PdfHealth:
    """Seitenanzahl / Dateigröße prüfen, ohne volles Rendering."""
    path = Path(path)
    warnings: List[str] = []
    errors: List[str] = []
    size = 0
    pages = 0
    try:
        size = path.stat().st_size
    except OSError as e:
        return PdfHealth(path, 0, 0, [], [f"Datei nicht lesbar: {e}"])

    size_mb = size / (1024 * 1024)
    if size_mb >= HARD_SIZE_MB:
        errors.append(
            f"Datei sehr groß ({size_mb:.0f} MB ≥ {HARD_SIZE_MB:.0f} MB). "
            "Öffnen abgebrochen — Datei teilen oder verkleinern."
        )
    elif size_mb >= SOFT_SIZE_MB:
        warnings.append(
            f"Große Datei ({size_mb:.0f} MB). Laden und Zoomen kann langsam sein.\n"
            + OPEN_TIMEOUT_HINT
        )

    try:
        import pypdfium2 as pdfium

        doc = pdfium.PdfDocument(str(path), password=password)
        try:
            pages = len(doc)
        finally:
            doc.close()
    except MemoryError:
        errors.append(
            "Nicht genug Speicher beim Öffnen.\n" + OPEN_TIMEOUT_HINT
        )
        return PdfHealth(path, 0, size, warnings, errors)
    except Exception as e:
        msg = str(e)
        low = msg.lower()
        if "password" in low or "passwd" in low:
            errors.append(f"PDF ist passwortgeschützt: {msg}")
        else:
            errors.append(
                f"PDF konnte nicht geöffnet werden: {msg}\n{OPEN_TIMEOUT_HINT}"
            )
        return PdfHealth(path, 0, size, warnings, errors)

    if pages <= 0:
        errors.append("PDF enthält keine Seiten.")
    elif pages > HARD_PAGE_LIMIT:
        errors.append(
            f"Zu viele Seiten ({pages} > {HARD_PAGE_LIMIT}). "
            "Bitte PDF vorher teilen (PDF → zusammenführen/teilen)."
        )
    elif pages >= SOFT_PAGE_WARN:
        warnings.append(
            f"Viele Seiten ({pages}). Nur die aktuelle Seite wird gerendert; "
            "Blättern/Zoom kann verzögert reagieren.\n"
            + OPEN_TIMEOUT_HINT
        )

    return PdfHealth(path, pages, size, warnings, errors)


def clamp_render_scale(
    page_width_pt: float,
    page_height_pt: float,
    scale: float,
    *,
    max_pixels: int = MAX_RENDER_PIXELS,
) -> tuple[float, Optional[str]]:
    """
    Begrenzt Render-Scale, damit Bitmap nicht explodiert.
    Rückgabe: (effektiver_scale, warnung_oder_None)
    """
    scale = max(0.1, float(scale))
    w = max(page_width_pt, 1.0) * scale
    h = max(page_height_pt, 1.0) * scale
    pixels = w * h
    if pixels <= max_pixels:
        return scale, None
    factor = (max_pixels / pixels) ** 0.5
    new_scale = max(0.1, scale * factor)
    return new_scale, (
        f"Zoom begrenzt auf {int(round(new_scale * 100))} % "
        f"(max. ~{max_pixels // 1_000_000} MPixel)."
    )
