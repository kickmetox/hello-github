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
