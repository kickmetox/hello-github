"""Robustes Öffnen von PDFs mit pypdfium2 — Fallback-Kette + Thread-Serialisierung (2.6.53).

Feldfehler Windows 2.6.52: Hauptansicht zeigt
``PDF-Öffnung fehlgeschlagen: Failed to load document (PDFium: Data format error)``
obwohl Textsuche/pikepdf dieselbe Datei lesen. Mögliche Ursachen, alle hier abgedeckt:

1. **Pfad-Encoding** — ``FPDF_LoadDocument`` erhält UTF-8-Bytes und öffnet unter
   Windows per ``CreateFileA`` (ANSI-Codepage). Umlaute/Sonderzeichen im Pfad →
   Fehlzugriff. Lösung: Datei in Python lesen und als **Bytes** übergeben
   (``FPDF_LoadMemDocument64``) — unabhängig von Pfad, Sharing-Mode und Locks.
2. **Beschädigte / unvollständige Dateien** (Download/Sync nicht fertig, Tool-Export
   ohne Trailer, Müll vor ``%PDF``): PDFium bricht mit ``Data format error`` ab,
   qpdf/pikepdf repariert. Lösung: pikepdf-Re-Save in den Speicher → Bytes an PDFium.
3. **PDFium ist nicht threadsicher.** Der Seitenanzahl-Refresh (2.6.45) und die
   Passwort-Probe liefen in ``threading.Thread`` parallel zum Render im GUI-Thread —
   zwei gleichzeitige PDFium-Aufrufe korrumpieren den Parser (Linux: „double free“,
   Windows: ``Data format error``/weiße Seite). Lösung: globaler RLock um jeden
   Open; Worker-Threads nutzen nur noch pikepdf (siehe ``security.needs_password``,
   ``pdf_view._schedule_page_count_refresh``).

Kette: Header-Sniff (Schritt 0, 2.6.54: DOCX/HTML/Text/0 Byte mit .pdf-Namen → sofort
konkrete Diagnose statt „Data format error“) → Bytes → str-Pfad → pikepdf-Reparatur →
aussagekräftiger Fehler, der jeden Schritt mit exakter Exception sowie
pypdfium2-/PDFium-Version nennt.
"""

from __future__ import annotations

import io
import logging
import sys
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Any, Optional

_log = logging.getLogger("ild_pdf.pdfium_open")

# Dateien über dieser Größe werden nicht komplett in den Speicher gelesen
# (Pfad zuerst, Bytes nur als Fallback ohne Cache).
BYTES_FIRST_MAX_MB = 192.0
# Bytes-Cache: letzte Dateien (Pfad+mtime+size → bytes), Gesamtbudget
BYTES_CACHE_MAX_ENTRIES = 3
BYTES_CACHE_MAX_TOTAL_MB = 320.0

# Globaler Lock: PDFium darf nie aus zwei Threads gleichzeitig laufen.
# RLock → verschachtelte Opens im GUI-Thread (Render innerhalb ``with PdfDocument``) ok.
PDFIUM_LOCK = threading.RLock()

_CACHE_LOCK = threading.Lock()
# key → (bytes, repaired: bool)
_BYTES_CACHE: "OrderedDict[tuple[str, int, int], tuple[bytes, bool]]" = OrderedDict()
# Letzter erfolgreicher Schritt je Datei (für Status/Log/Diagnose)
_LAST_OPEN_STEP: dict[str, str] = {}

STEP_HEADER = "header"
STEP_BYTES = "bytes"
STEP_PATH = "path"
STEP_REPAIR = "pikepdf-repair"


class PdfiumOpenError(RuntimeError):
    """Alle Schritte der Fallback-Kette sind fehlgeschlagen.

    ``steps`` enthält ``(schritt, fehlertext)`` in Reihenfolge der Versuche.
    """

    def __init__(
        self,
        path: Path,
        steps: list[tuple[str, str]],
        *,
        password_error: bool = False,
        sniff: Any = None,
    ):
        self.path = Path(path)
        self.steps = list(steps)
        self.password_error = bool(password_error)
        # ``pdf_sniff.SniffResult`` — gesetzt, wenn die Datei gar kein PDF ist
        self.sniff = sniff
        super().__init__(format_open_failure(self.path, self.steps))

    @property
    def not_a_pdf(self) -> bool:
        """Datei-Inhalt ist kein PDF (DOCX/HTML/Text/leer …) — kein Parser-Fehler."""
        return self.sniff is not None and not getattr(self.sniff, "is_pdf_like", True)


def pdfium_version_info() -> str:
    """``pypdfium2 5.14.0 · PDFium 7xxx (chromium/…) · Python 3.12 win32``."""
    parts: list[str] = []
    try:
        import pypdfium2 as pdfium

        v = getattr(pdfium, "PYPDFIUM_INFO", None) or getattr(pdfium, "V_PYPDFIUM2", None)
        parts.append(f"pypdfium2 {v}" if v else "pypdfium2 ?")
        info = getattr(pdfium, "PDFIUM_INFO", None)
        if info is not None:
            build = getattr(info, "build", None) or getattr(info, "major", None)
            tag = getattr(info, "tag", None)
            txt = f"PDFium {build}" if build else f"PDFium {info}"
            if tag and str(tag) not in txt:
                txt += f" ({tag})"
            parts.append(txt)
    except Exception as e:  # pragma: no cover - defensive
        parts.append(f"pypdfium2 nicht importierbar: {e}")
    try:
        import pikepdf

        parts.append(f"pikepdf {pikepdf.__version__}")
    except Exception:
        parts.append("pikepdf fehlt")
    parts.append(f"Python {sys.version_info.major}.{sys.version_info.minor} {sys.platform}")
    if getattr(sys, "frozen", False):
        parts.append("frozen")
    return " · ".join(parts)


def format_open_failure(path: Path, steps: list[tuple[str, str]]) -> str:
    """Mehrzeiliger Fehlertext: Datei, jeder Schritt mit exakter Exception, Versionen."""
    names = {
        STEP_HEADER: "Schritt 0 (Datei-Header)",
        STEP_BYTES: "Schritt 1 (Bytes → FPDF_LoadMemDocument)",
        STEP_PATH: "Schritt 2 (str-Pfad → FPDF_LoadDocument)",
        STEP_REPAIR: "Schritt 3 (pikepdf-Reparatur → Bytes)",
    }
    lines = [f"PDF-Öffnung fehlgeschlagen: {Path(path).name}"]
    for step, err in steps:
        lines.append(f"• {names.get(step, step)}: {err}")
    lines.append(f"[{pdfium_version_info()}]")
    return "\n".join(lines)


def last_open_step(path: str | Path) -> str:
    """Welcher Schritt die Datei zuletzt erfolgreich geöffnet hat ('' wenn unbekannt)."""
    return _LAST_OPEN_STEP.get(_norm(path), "")


def _norm(path: str | Path) -> str:
    try:
        return str(Path(path).resolve())
    except OSError:
        return str(path)


def _cache_key(path: Path) -> Optional[tuple[str, int, int]]:
    try:
        st = path.stat()
    except OSError:
        return None
    return (_norm(path), int(st.st_mtime_ns), int(st.st_size))


def _cache_get(key: tuple[str, int, int]) -> Optional[tuple[bytes, bool]]:
    with _CACHE_LOCK:
        hit = _BYTES_CACHE.get(key)
        if hit is not None:
            _BYTES_CACHE.move_to_end(key)
        return hit


def _cache_put(key: tuple[str, int, int], data: bytes, repaired: bool) -> None:
    budget = int(BYTES_CACHE_MAX_TOTAL_MB * 1024 * 1024)
    if len(data) > budget:
        return
    with _CACHE_LOCK:
        _BYTES_CACHE[key] = (data, repaired)
        _BYTES_CACHE.move_to_end(key)
        while len(_BYTES_CACHE) > BYTES_CACHE_MAX_ENTRIES:
            _BYTES_CACHE.popitem(last=False)
        total = sum(len(v[0]) for v in _BYTES_CACHE.values())
        while total > budget and len(_BYTES_CACHE) > 1:
            _k, v = _BYTES_CACHE.popitem(last=False)
            total -= len(v[0])


def clear_pdfium_bytes_cache(path: str | Path | None = None) -> None:
    """Bytes-Cache leeren (gesamt oder für einen Pfad) — nach jeder Dateiänderung."""
    with _CACHE_LOCK:
        if path is None:
            _BYTES_CACHE.clear()
            _LAST_OPEN_STEP.clear()
            return
        norm = _norm(path)
        for k in [k for k in _BYTES_CACHE if k[0] == norm or k[0] == str(path)]:
            _BYTES_CACHE.pop(k, None)
        _LAST_OPEN_STEP.pop(norm, None)


def read_pdf_bytes(path: str | Path, *, use_cache: bool = True) -> bytes:
    """Datei einmal lesen (gecacht) — gemeinsame Bytes für Render/Count/Suche."""
    p = Path(path)
    key = _cache_key(p) if use_cache else None
    if key is not None:
        hit = _cache_get(key)
        if hit is not None and not hit[1]:
            return hit[0]
    data = p.read_bytes()
    if key is not None:
        _cache_put(key, data, False)
    return data


def _is_password_error(err: Any) -> bool:
    msg = str(err or "").lower()
    return "password" in msg or "passwd" in msg or "passwort" in msg


def _repaired_bytes(path: Path, password: Optional[str]) -> bytes:
    """pikepdf öffnet tolerant (qpdf-Recovery) und schreibt normalisiert in den Speicher."""
    import pikepdf

    key = _cache_key(path)
    if key is not None:
        hit = _cache_get(key)
        if hit is not None and hit[1]:
            return hit[0]
    kw: dict = {}
    if password:
        kw["password"] = password
    with pikepdf.open(str(path), **kw) as pdf:
        bio = io.BytesIO()
        # Ohne Verschlüsselung/Objektstreams-Umbau: so nah am Original wie möglich
        pdf.save(bio)
        data = bio.getvalue()
    if key is not None:
        _cache_put(key, data, True)
    return data


def open_pdfium(
    path: str | Path,
    password: Optional[str] = None,
    *,
    allow_repair: bool = True,
) -> Any:
    """``pypdfium2.PdfDocument`` über die Fallback-Kette öffnen.

    Rückgabe: geöffnetes ``pypdfium2.PdfDocument`` (Aufrufer schließt).
    Wirft ``FileNotFoundError`` wenn die Datei fehlt, sonst ``PdfiumOpenError``
    mit allen Schritt-Fehlern. Passwortfehler brechen die Kette sofort ab
    (Dialog-Flow in ``pdf_view`` prüft ``is_wrong_password_error``).
    """
    import pypdfium2 as pdfium

    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"PDF nicht gefunden: {p}")
    pw = password if password else None
    steps: list[tuple[str, str]] = []
    try:
        size_mb = p.stat().st_size / (1024 * 1024)
    except OSError:
        size_mb = 0.0
    bytes_first = size_mb <= BYTES_FIRST_MAX_MB
    order = (STEP_BYTES, STEP_PATH) if bytes_first else (STEP_PATH, STEP_BYTES)
    if allow_repair:
        order = order + (STEP_REPAIR,)

    # Schritt 0: Inhalt statt Endung prüfen. Ein DOCX/HTML/Text mit .pdf-Namen oder
    # eine 0-Byte-Datei bekommt eine konkrete Diagnose (Typ, Größe, Header-Hex) statt
    # dreimal „Data format error“ — Feldfall 2.6.53 — 2.6.54
    sniff = None
    try:
        from .pdf_sniff import describe_non_pdf_de, sniff_file

        sniff = sniff_file(p)
        if not sniff.is_pdf_like:
            msg = describe_non_pdf_de(sniff)
            _log.warning("PDF-Öffnung abgebrochen (kein PDF): %s", msg)
            raise PdfiumOpenError(p, [(STEP_HEADER, msg)], sniff=sniff)
        if not sniff.is_clean_pdf:
            steps.append((STEP_HEADER, f"{sniff.label_de}: {sniff.detail} — Reparatur wird versucht"))
    except PdfiumOpenError:
        raise
    except Exception as e:  # pragma: no cover - Sniff darf das Öffnen nie verhindern
        _log.debug("Header-Sniff fehlgeschlagen: %s", e)

    with PDFIUM_LOCK:
        for step in order:
            try:
                if step == STEP_BYTES:
                    data = read_pdf_bytes(p, use_cache=bytes_first)
                    if not data:
                        raise ValueError("Datei ist leer (0 Bytes)")
                    doc = pdfium.PdfDocument(data, password=pw)
                elif step == STEP_PATH:
                    doc = pdfium.PdfDocument(str(p), password=pw)
                else:
                    data = _repaired_bytes(p, pw)
                    # Nach qpdf-Re-Save ist die Datei unverschlüsselt
                    doc = pdfium.PdfDocument(data, password=None)
            except MemoryError:
                raise
            except Exception as e:
                msg = f"{type(e).__name__}: {e}"
                steps.append((step, msg))
                if _is_password_error(e):
                    raise PdfiumOpenError(p, steps, password_error=True) from e
                continue
            norm = _norm(p)
            prev = _LAST_OPEN_STEP.get(norm)
            _LAST_OPEN_STEP[norm] = step
            if step != STEP_BYTES and prev != step:
                _log.warning(
                    "PDF %s über Fallback '%s' geöffnet (vorherige Schritte: %s)",
                    p.name,
                    step,
                    "; ".join(f"{s}: {m}" for s, m in steps) or "-",
                )
            return doc
    raise PdfiumOpenError(p, steps, sniff=sniff)


def open_pdfium_steps_summary(path: str | Path) -> str:
    """Kurztext für Statusleiste: 'geöffnet über Bytes' / 'pikepdf-Reparatur'."""
    step = last_open_step(path)
    if step == STEP_REPAIR:
        return "PDF repariert geladen (pikepdf) — Original unverändert"
    if step == STEP_PATH:
        return "PDF über Pfad geladen (Bytes-Pfad schlug fehl)"
    return ""
