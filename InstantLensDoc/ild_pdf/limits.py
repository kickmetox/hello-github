"""Grenzen und Diagnose für große / problematische PDFs."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

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
# Hinweis für langsame/hängende Öffnungen
OPEN_TIMEOUT_HINT_SEC = 30
OPEN_TIMEOUT_HINT = (
    f"Hinweis: Bleibt das Öffnen länger als ~{OPEN_TIMEOUT_HINT_SEC}s stehen oder "
    "bricht ab, PDF teilen/verkleinern (PDF → zusammenführen/teilen) oder Passwort prüfen."
)
# Open-Preflight: kurz, immer Worker+Timeout — auch bei kleinen PDFs — 2.6.45
INSPECT_TIMEOUT_SEC = 2.0
# Passwort-Probe (needs_password) — nie UI-Thread blockieren — 2.6.45
PASSWORD_PROBE_TIMEOUT_SEC = 1.5
# PDFium-len() im Open-Preflight standardmäßig AUS (hängt auch bei kurzen PDFs)
PDFIUM_INSPECT_MAX_MB = 0.0
# AcroForm-Vollscan nach Open überspringen (pro Feld Page-Walk) — 2.6.42+
FORM_SCAN_PAGE_THRESHOLD = 80
# Zoom-Render: Pixel-Obergrenze (Breite×Höhe der Bitmap)
MAX_RENDER_PIXELS = 40_000_000


@dataclass
class PdfHealth:
    path: Path
    page_count: int
    size_bytes: int
    warnings: List[str]
    errors: List[str]
    timed_out: bool = False
    probe: str = ""
    skipped_heavy: bool = False

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)

    @property
    def ok_to_open(self) -> bool:
        return not self.errors

    @property
    def needs_confirm(self) -> bool:
        return bool(self.warnings) and self.ok_to_open


def size_only_health(path: str | Path) -> PdfHealth:
    """Nur Dateigröße — synchron, nie PDFium/pikepdf. Für Open-Fast-Path — 2.6.45."""
    path = Path(path)
    warnings: List[str] = []
    errors: List[str] = []
    try:
        size = path.stat().st_size
    except OSError as e:
        return PdfHealth(path, 0, 0, [], [f"Datei nicht lesbar: {e}"], probe="size")
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
    return PdfHealth(
        path,
        0,
        size,
        warnings,
        errors,
        probe="size",
        skipped_heavy=True,
    )


def catalog_page_count(
    path: str | Path, *, password: Optional[str] = None
) -> tuple[Optional[int], Optional[str]]:
    """Seitenanzahl aus /Pages /Count (kein PDFium-Page-Tree). (count, error)."""
    path = Path(path)
    try:
        import pikepdf
        from pikepdf import PasswordError
    except Exception as e:
        return None, f"pikepdf: {e}"
    try:
        kw: dict = {}
        if password:
            kw["password"] = password
        with pikepdf.open(str(path), **kw) as pdf:
            pages_obj = None
            try:
                pages_obj = pdf.Root.get("/Pages")
            except Exception:
                pages_obj = None
            if pages_obj is not None:
                try:
                    count = pages_obj.get("/Count")
                    if count is not None:
                        return int(count), None
                except Exception:
                    pass
            try:
                return int(len(pdf.pages)), None
            except Exception as e:
                return None, str(e)
    except PasswordError as e:
        return None, f"PDF ist passwortgeschützt: {e}"
    except Exception as e:
        return None, str(e)


def _pdfium_page_count(
    path: Path, *, password: Optional[str] = None
) -> tuple[int, Optional[str]]:
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(path), password=password)
    try:
        return int(len(doc)), None
    finally:
        doc.close()


def _apply_page_limits(
    pages: int, warnings: List[str], errors: List[str]
) -> None:
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


def _inspect_structure(
    path: Path,
    *,
    password: Optional[str],
    size: int,
    size_mb: float,
    warnings: List[str],
    errors: List[str],
    allow_pdfium: bool,
) -> PdfHealth:
    probe = "pikepdf"
    skipped_heavy = False
    pages_opt, probe_err = catalog_page_count(path, password=password)
    pages = int(pages_opt or 0)
    if pages_opt is None:
        low = str(probe_err or "").lower()
        if "password" in low or "passwd" in low or "passwort" in low:
            errors.append(str(probe_err))
            return PdfHealth(
                path, 0, size, warnings, errors, probe=probe, skipped_heavy=True
            )
        # PDFium nur explizit — Open-Pfad nutzt es nicht (hängt auch bei kurzen PDFs)
        if not allow_pdfium:
            skipped_heavy = True
            warnings.append(
                "Vollständige PDF-Prüfung übersprungen. Erste Seite wird trotzdem geöffnet."
            )
            probe = "size"
            return PdfHealth(
                path,
                0,
                size,
                warnings,
                errors,
                probe=probe,
                skipped_heavy=True,
            )
        try:
            pages, pdfium_err = _pdfium_page_count(path, password=password)
            probe = "pdfium"
            if pdfium_err:
                errors.append(str(pdfium_err))
                return PdfHealth(path, 0, size, warnings, errors, probe=probe)
        except MemoryError:
            errors.append("Nicht genug Speicher beim Öffnen.\n" + OPEN_TIMEOUT_HINT)
            return PdfHealth(path, 0, size, warnings, errors, probe="pdfium")
        except Exception as e:
            msg = str(e)
            low = msg.lower()
            if "password" in low or "passwd" in low:
                errors.append(f"PDF ist passwortgeschützt: {msg}")
            else:
                errors.append(
                    f"PDF konnte nicht geöffnet werden: {msg}\n{OPEN_TIMEOUT_HINT}"
                )
            return PdfHealth(path, 0, size, warnings, errors, probe="pdfium")

    _apply_page_limits(pages, warnings, errors)
    return PdfHealth(
        path,
        pages,
        size,
        warnings,
        errors,
        probe=probe,
        skipped_heavy=skipped_heavy,
    )


def inspect_pdf(
    path: str | Path,
    *,
    password: Optional[str] = None,
    timeout_sec: float | None = INSPECT_TIMEOUT_SEC,
    cancel_check: Optional[Callable[[], bool]] = None,
    pump: Optional[Callable[[], None]] = None,
    allow_pdfium: Optional[bool] = None,
) -> PdfHealth:
    """Seitenanzahl / Dateigröße — Worker+Timeout, Standard ohne PDFium.

    Open-Pfad: ``allow_pdfium=False`` (Default). Auch kleine PDFs: nie UI blockieren.
    """
    path = Path(path)
    base = size_only_health(path)
    if base.errors and base.probe == "size" and base.size_bytes == 0:
        return base
    if any("sehr groß" in e for e in base.errors):
        return base

    warnings = list(base.warnings)
    errors: List[str] = []
    size = int(base.size_bytes)
    size_mb = size / (1024 * 1024)

    # Open-Default: kein PDFium im Preflight (auch nicht bei kleinen Dateien) — 2.6.45
    use_pdfium = bool(allow_pdfium) if allow_pdfium is not None else False

    def _run() -> PdfHealth:
        return _inspect_structure(
            path,
            password=password,
            size=size,
            size_mb=size_mb,
            warnings=list(warnings),
            errors=list(errors),
            allow_pdfium=use_pdfium,
        )

    if timeout_sec is None or float(timeout_sec) <= 0:
        return _run()

    box: dict = {}

    def _worker() -> None:
        try:
            box["h"] = _run()
        except Exception as e:  # pragma: no cover
            box["e"] = e

    t = threading.Thread(target=_worker, daemon=True, name="ild-pdf-inspect")
    t.start()
    deadline = time.monotonic() + float(timeout_sec)
    while t.is_alive():
        if cancel_check and cancel_check():
            return PdfHealth(
                path,
                0,
                size,
                warnings,
                ["PDF-Prüfung abgebrochen."],
                probe="canceled",
                skipped_heavy=True,
            )
        if time.monotonic() >= deadline:
            warnings.append(
                "PDF-Prüfung zeitüberschritten — Datei wird ohne Vollscan geöffnet "
                "(erste Seite sofort)."
            )
            return PdfHealth(
                path,
                0,
                size,
                warnings,
                errors,
                timed_out=True,
                probe="timeout",
                skipped_heavy=True,
            )
        if pump is not None:
            try:
                pump()
            except Exception:
                pass
        t.join(0.04)
    if "e" in box:
        raise box["e"]
    health = box.get("h")
    if isinstance(health, PdfHealth):
        return health
    return PdfHealth(
        path,
        0,
        size,
        warnings,
        [],
        timed_out=True,
        probe="timeout",
        skipped_heavy=True,
    )


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
