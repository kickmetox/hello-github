"""Benutzerdefinierte PDF-Seitenbeschriftungen (Sidecar + optional PageLabels).

Schema in Sidecar-Meta ``page_labels``: Liste von Strings (Index = Seite 0-basiert)
oder Dict ``{"0": "i", "1": "ii", …}``. Leere Strings = keine Override-Beschriftung.
Optional: Schreiben nativer PDF-``/PageLabels`` via pikepdf (Prefix je Seite).
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence


def normalize_page_labels(
    raw: object,
    *,
    page_count: int,
) -> list[str]:
    """Rohdaten → Liste Länge page_count (fehlende = '')."""
    n = max(0, int(page_count))
    out = [""] * n
    if n <= 0 or raw is None:
        return out
    if isinstance(raw, Mapping):
        for key, val in raw.items():
            try:
                idx = int(key)
            except (TypeError, ValueError):
                continue
            if 0 <= idx < n:
                out[idx] = str(val or "").strip()
        return out
    if isinstance(raw, (list, tuple)):
        for i, val in enumerate(raw):
            if i >= n:
                break
            out[i] = str(val or "").strip()
    return out


def page_labels_to_meta(labels: Sequence[str]) -> list[str]:
    """Persistenzform: Liste; trailing leere Einträge optional kürzen."""
    cleaned = [str(x or "").strip() for x in labels]
    while cleaned and not cleaned[-1]:
        cleaned.pop()
    return cleaned


def merge_labels(
    pdf_labels: Sequence[str],
    custom_labels: Sequence[str],
) -> list[str]:
    """Custom (nicht leer) überschreibt PDF-native Labels."""
    n = max(len(pdf_labels), len(custom_labels))
    out: list[str] = []
    for i in range(n):
        custom = str(custom_labels[i] if i < len(custom_labels) else "").strip()
        native = str(pdf_labels[i] if i < len(pdf_labels) else "").strip()
        out.append(custom or native)
    return out


def remap_page_labels(
    labels: Sequence[str],
    mapping: Mapping[int, int],
    *,
    new_page_count: int,
) -> list[str]:
    """Seiten-Remap (Löschen/Reorder) für Custom-Labels."""
    out = [""] * max(0, int(new_page_count))
    for old_i, lab in enumerate(labels):
        if old_i not in mapping:
            continue
        new_i = int(mapping[old_i])
        if 0 <= new_i < len(out):
            out[new_i] = str(lab or "").strip()
    return out


def read_pdf_page_labels(
    pdf_path: str | Path,
    *,
    password: str | None = None,
) -> list[str]:
    """Native PDF-Seitenlabels (pypdfium2) lesen — Import in den Dialog."""
    from .document import PdfDocument

    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF nicht gefunden: {path}")
    with PdfDocument(path, password=password) as doc:
        return list(doc.page_labels())


def arabic_reset_labels(page_count: int, *, start: int = 1) -> list[str]:
    """Arabische Nummerierung 1… (oder ab ``start``) für alle Seiten."""
    n = max(0, int(page_count))
    s = int(start)
    return [str(s + i) for i in range(n)]


def normalize_page_range(start_page: int, end_page: int) -> tuple[int, int]:
    """0-basierter inklusiver Bereich als (lo, hi)."""
    a = int(start_page)
    b = int(end_page)
    return (min(a, b), max(a, b))


def label_ranges_overlap(
    start_a: int,
    end_a: int,
    start_b: int,
    end_b: int,
) -> bool:
    """True wenn zwei 0-basierte inklusive Bereiche überlappen — 2.2.2."""
    a0, a1 = normalize_page_range(start_a, end_a)
    b0, b1 = normalize_page_range(start_b, end_b)
    return a0 <= b1 and b0 <= a1


def find_overlapping_applied_range(
    applied: Sequence[tuple[int, int]],
    start_page: int,
    end_page: int,
) -> tuple[int, int] | None:
    """
    Ersten überlappenden Bereich aus ``applied`` zurückgeben, sonst None.

    ``applied``-Einträge sind 0-basierte inklusive (start, end).
    """
    for prev in applied or []:
        if not isinstance(prev, (list, tuple)) or len(prev) < 2:
            continue
        if label_ranges_overlap(start_page, end_page, int(prev[0]), int(prev[1])):
            return (int(prev[0]), int(prev[1]))
    return None


def validate_label_range_overlap(
    applied: Sequence[tuple[int, int]],
    start_page: int,
    end_page: int,
) -> str | None:
    """
    DE-Fehlermeldung bei Überlappung mit bereits angewandten Bereichen, sonst None — 2.2.2.
    """
    hit = find_overlapping_applied_range(applied, start_page, end_page)
    if hit is None:
        return None
    lo, hi = normalize_page_range(start_page, end_page)
    plo, phi = hit
    return (
        f"Bereich überlappt mit bereits gesetztem Bereich "
        f"(Seite {plo + 1}–{phi + 1}). "
        f"Neuer Bereich: Seite {lo + 1}–{hi + 1}."
    )


def preview_label_range(
    *,
    start_page: int,
    end_page: int,
    start_value: int = 1,
    max_preview: int = 5,
) -> list[str]:
    """
    Erste Labels eines arabischen Bereichs als Vorschau (ohne Seite zu füllen) — 2.2.2.
    """
    lo, hi = normalize_page_range(start_page, end_page)
    n = max(0, hi - lo + 1)
    k = max(0, min(int(max_preview), n))
    sv = int(start_value)
    return [str(sv + i) for i in range(k)]


def format_label_preview(labels: Sequence[str], *, total: int | None = None) -> str:
    """Kurztext „Vorschau: 1, 2, 3…“ für den Range-Editor."""
    items = [str(x).strip() for x in labels if str(x).strip()]
    if not items:
        return "Vorschau: —"
    body = ", ".join(items)
    n = int(total) if total is not None else len(items)
    if n > len(items):
        body += "…"
    return f"Vorschau: {body}"


def apply_label_range(
    labels: Sequence[str],
    *,
    start_page: int,
    end_page: int,
    start_value: int = 1,
    page_count: int | None = None,
) -> list[str]:
    """
    Bereich (0-basiert inkl.) mit arabischer Folge ab ``start_value`` füllen.

    ``start_page``/``end_page`` werden geklemmt; Reihenfolge egal (min/max).
    """
    n = int(page_count) if page_count is not None else len(labels)
    n = max(0, n)
    out = [str(x or "").strip() for x in labels]
    while len(out) < n:
        out.append("")
    out = out[:n]
    if n <= 0:
        return out
    a = max(0, min(int(start_page), int(end_page)))
    b = min(n - 1, max(int(start_page), int(end_page)))
    sv = int(start_value)
    for i in range(a, b + 1):
        out[i] = str(sv + (i - a))
    return out


def write_pdf_page_labels(
    pdf_path: str | Path,
    labels: Sequence[str],
    *,
    password: str | None = None,
) -> Path:
    """
    Custom-Labels als PDF ``/PageLabels`` schreiben (pikepdf).

    Jede nicht-leere Beschriftung wird als Prefix-Eintrag (``/P``) ohne Nummerierungsstil
    gesetzt — geeignet für beliebige Texte (i, ii, 1, Cover, …).
    Leere Einträge werden übersprungen (PDF fällt auf Standard-Seitenzahl zurück).
    """
    import pikepdf
    from pikepdf import Array, Dictionary, Name

    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF nicht gefunden: {path}")
    cleaned = [str(x or "").strip() for x in labels]
    open_kw: dict = {"allow_overwriting_input": True}
    if password:
        open_kw["password"] = password
    with pikepdf.Pdf.open(path, **open_kw) as pdf:
        n = len(pdf.pages)
        while len(cleaned) < n:
            cleaned.append("")
        cleaned = cleaned[:n]
        nums: list = []
        for i, lab in enumerate(cleaned):
            if not lab:
                continue
            # Prefix-only: Anzeige = genau der Label-Text
            nums.append(i)
            nums.append(Dictionary(P=lab))
        if nums:
            pdf.Root.PageLabels = Dictionary(Nums=Array(nums))
        elif Name.PageLabels in pdf.Root:
            try:
                del pdf.Root.PageLabels
            except Exception:
                pdf.Root.PageLabels = Dictionary(Nums=Array([]))
        pdf.save(path)
    return path
