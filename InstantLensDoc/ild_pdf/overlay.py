"""PDF-Textblöcke lesen + Overlay-Sidecar in PDF einbrennen (pikepdf).

Native PDF-Textbearbeitung ist mit pypdfium2/pikepdf nicht zuverlässig möglich.
Deshalb: Overlay-Editor (Sidecar) + optionaler Bake-Schritt.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

from .annotate import Annotation, AnnotationStore, AnnotationType


@dataclass
class TextBlock:
    """Grob erkannter Textblock einer PDF-Seite (Pixel bei scale=1.0 ≈ PDF-Punkte)."""

    page: int
    x: float
    y: float
    width: float
    height: float
    text: str
    font_size: float = 12.0

    def to_overlay(self, scale: float = 1.0) -> Annotation:
        """Als editierbares TEXT_OVERLAY in Render-Pixelkoordinaten."""
        return Annotation(
            page=self.page,
            type=AnnotationType.TEXT_OVERLAY,
            x=self.x * scale,
            y=self.y * scale,
            width=max(self.width * scale, 40.0),
            height=max(self.height * scale, self.font_size * scale * 1.4),
            text=self.text,
            color="#1A5276",
            font_size=self.font_size * scale,
        )


def extract_text_blocks(
    pdf_path: str | Path,
    page_index: int = 0,
    *,
    merge_lines: bool = True,
) -> List[TextBlock]:
    """
    Liest sichtbaren Text einer Seite via pypdfium2 (PDF-Punkte, Y von oben).
    Liefert grobe Zeilen-/Blöcke — keine 1:1-Layout-Rekonstruktion.
    """
    import pypdfium2 as pdfium

    pdf_path = Path(pdf_path)
    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        if page_index < 0 or page_index >= len(doc):
            raise IndexError(f"Seite {page_index} existiert nicht")
        page = doc[page_index]
        try:
            width, height = page.get_size()
            textpage = page.get_textpage()
            try:
                # chars → einfache Zeilengruppierung nach Y
                chars: list[tuple[float, float, float, float, str]] = []
                n = textpage.count_chars()
                for i in range(n):
                    ch = textpage.get_text_range(i, 1)
                    if not ch or ch.isspace():
                        # Leerzeichen trotzdem für Wortgrenzen behalten wenn Box da
                        box = textpage.get_charbox(i)
                        if box is None:
                            continue
                        l, b, r, t = box
                        chars.append((l, height - t, r - l, t - b, ch or " "))
                        continue
                    box = textpage.get_charbox(i)
                    if box is None:
                        continue
                    l, b, r, t = box
                    # PDF Y von unten → Y von oben
                    chars.append((float(l), float(height - t), float(r - l), float(t - b), ch))
            finally:
                textpage.close()
        finally:
            page.close()
    finally:
        doc.close()

    if not chars:
        return []

    if not merge_lines:
        return [
            TextBlock(
                page=page_index,
                x=x,
                y=y,
                width=max(w, 4),
                height=max(h, 8),
                text=ch,
                font_size=max(h, 8),
            )
            for x, y, w, h, ch in chars
            if ch.strip()
        ]

    # Nach Y-Band gruppieren (Zeilen)
    chars_sorted = sorted(chars, key=lambda c: (round(c[1] / 4) * 4, c[0]))
    lines: list[list[tuple[float, float, float, float, str]]] = []
    for c in chars_sorted:
        if not lines:
            lines.append([c])
            continue
        prev = lines[-1][0]
        if abs(c[1] - prev[1]) <= max(prev[3], c[3], 8) * 0.6:
            lines[-1].append(c)
        else:
            lines.append([c])

    blocks: List[TextBlock] = []
    for line in lines:
        line = sorted(line, key=lambda c: c[0])
        text = "".join(c[4] for c in line).strip()
        if not text:
            continue
        x0 = min(c[0] for c in line)
        y0 = min(c[1] for c in line)
        x1 = max(c[0] + c[2] for c in line)
        y1 = max(c[1] + c[3] for c in line)
        fs = max(sum(c[3] for c in line) / len(line), 8.0)
        blocks.append(
            TextBlock(
                page=page_index,
                x=x0,
                y=y0,
                width=max(x1 - x0, 20),
                height=max(y1 - y0, fs),
                text=text,
                font_size=fs,
            )
        )
    return blocks


def extract_page_plain_text(
    pdf_path: str | Path,
    page_index: int = 0,
    *,
    password: str | None = None,
) -> str:
    """Sichtbaren Text einer Seite als Plaintext (pypdfium2 get_text_bounded)."""
    import pypdfium2 as pdfium

    pdf_path = Path(pdf_path)
    kwargs = {}
    if password:
        kwargs["password"] = password
    doc = pdfium.PdfDocument(str(pdf_path), **kwargs)
    try:
        if page_index < 0 or page_index >= len(doc):
            raise IndexError(f"Seite {page_index} existiert nicht")
        page = doc[page_index]
        try:
            tp = page.get_textpage()
            try:
                return tp.get_text_bounded() or ""
            finally:
                tp.close()
        finally:
            page.close()
    finally:
        doc.close()


def extract_all_plain_text(
    pdf_path: str | Path,
    *,
    password: str | None = None,
    page_headers: bool = True,
) -> str:
    """
    Text aller Seiten als Plaintext.
    Mit page_headers: Abschnitte „--- Seite N ---“ zwischen den Seiten.
    """
    import pypdfium2 as pdfium

    pdf_path = Path(pdf_path)
    kwargs = {}
    if password:
        kwargs["password"] = password
    doc = pdfium.PdfDocument(str(pdf_path), **kwargs)
    try:
        parts: list[str] = []
        for i in range(len(doc)):
            page = doc[i]
            try:
                tp = page.get_textpage()
                try:
                    blob = tp.get_text_bounded() or ""
                finally:
                    tp.close()
            finally:
                page.close()
            if page_headers:
                parts.append(f"--- Seite {i + 1} ---\n{blob}".rstrip())
            else:
                parts.append(blob.rstrip())
        return "\n\n".join(parts).strip() + ("\n" if parts else "")
    finally:
        doc.close()


@dataclass
class TextMatchRect:
    """Treffer-Rechteck einer Textsuche (PDF-Punkte, Y von oben; optional skaliert)."""

    page: int
    x: float
    y: float
    width: float
    height: float
    text: str = ""

    def scaled(self, scale: float) -> "TextMatchRect":
        s = float(scale)
        return TextMatchRect(
            page=self.page,
            x=self.x * s,
            y=self.y * s,
            width=self.width * s,
            height=self.height * s,
            text=self.text,
        )


def _page_chars(
    pdf_path: str | Path,
    page_index: int,
    *,
    password: str | None = None,
) -> tuple[list[tuple[float, float, float, float, str]], float, float]:
    """Zeichen mit Boxen (Y oben) + Seitengröße."""
    import pypdfium2 as pdfium

    pdf_path = Path(pdf_path)
    kwargs = {}
    if password:
        kwargs["password"] = password
    doc = pdfium.PdfDocument(str(pdf_path), **kwargs)
    try:
        if page_index < 0 or page_index >= len(doc):
            raise IndexError(f"Seite {page_index} existiert nicht")
        page = doc[page_index]
        try:
            width, height = page.get_size()
            textpage = page.get_textpage()
            try:
                chars: list[tuple[float, float, float, float, str]] = []
                n = textpage.count_chars()
                for i in range(n):
                    ch = textpage.get_text_range(i, 1)
                    box = textpage.get_charbox(i)
                    if box is None:
                        continue
                    l, b, r, t = box
                    chars.append((float(l), float(height - t), float(r - l), float(t - b), ch or " "))
                return chars, float(width), float(height)
            finally:
                textpage.close()
        finally:
            page.close()
    finally:
        doc.close()


def find_text_rects(
    pdf_path: str | Path,
    page_index: int,
    query: str,
    *,
    scale: float = 1.0,
    password: str | None = None,
    max_hits: int = 200,
) -> List[TextMatchRect]:
    """
    Findet Query-Treffer auf einer PDF-Seite und liefert Highlight-Rechtecke
    (Render-Pixel bei scale, Y von oben). Case-insensitive.
    """
    q = (query or "").strip()
    if not q:
        return []
    try:
        chars, _w, _h = _page_chars(pdf_path, page_index, password=password)
    except Exception:
        return []
    if not chars:
        return []

    # Volltext + Index-Mapping (inkl. Whitespace für Wortgrenzen)
    text_chars = [(c[4] or " ") for c in chars]
    hay = "".join(text_chars)
    hay_l = hay.lower()
    needle = q.lower()
    if not needle or needle not in hay_l:
        return []

    hits: List[TextMatchRect] = []
    start = 0
    while len(hits) < max_hits:
        pos = hay_l.find(needle, start)
        if pos < 0:
            break
        end = pos + len(needle)
        slice_chars = chars[pos:end]
        if not slice_chars:
            start = pos + 1
            continue
        # Mehrzeilige Treffer → pro Y-Band ein Rechteck
        bands: dict[int, list[tuple[float, float, float, float, str]]] = {}
        for c in slice_chars:
            key = int(round(c[1] / 2.0) * 2)
            bands.setdefault(key, []).append(c)
        for band in bands.values():
            x0 = min(c[0] for c in band)
            y0 = min(c[1] for c in band)
            x1 = max(c[0] + c[2] for c in band)
            y1 = max(c[1] + c[3] for c in band)
            snippet = "".join(c[4] for c in band)
            rect = TextMatchRect(
                page=page_index,
                x=x0,
                y=y0,
                width=max(x1 - x0, 4.0),
                height=max(y1 - y0, 6.0),
                text=snippet,
            )
            hits.append(rect.scaled(scale) if scale != 1.0 else rect)
            if len(hits) >= max_hits:
                break
        start = pos + max(len(needle), 1)
    return hits


def selection_to_highlight_rects(
    pdf_path: str | Path,
    page_index: int,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    *,
    scale: float = 1.0,
    password: str | None = None,
    min_overlap: float = 0.35,
) -> tuple[List[TextMatchRect], str]:
    """
    Selection→Highlight: Zeichen im Auswahlrechteck (Render-Pixel bei scale)
    zu Zeilen-Highlight-Rechtecken + ausgewähltem Text zusammenfassen.
    """
    s = float(scale) if scale else 1.0
    if s <= 0:
        s = 1.0
    # Render-Pixel → PDF-Punkte
    rx0, rx1 = sorted((float(x0) / s, float(x1) / s))
    ry0, ry1 = sorted((float(y0) / s, float(y1) / s))
    if rx1 - rx0 < 1.0 and ry1 - ry0 < 1.0:
        return [], ""
    try:
        chars, _w, _h = _page_chars(pdf_path, page_index, password=password)
    except Exception:
        return [], ""
    if not chars:
        return [], ""

    selected: list[tuple[float, float, float, float, str]] = []
    for cx, cy, cw, ch, text in chars:
        if cw <= 0 or ch <= 0:
            continue
        # Überlappung Zeichenvs. Auswahl
        ox0 = max(cx, rx0)
        oy0 = max(cy, ry0)
        ox1 = min(cx + cw, rx1)
        oy1 = min(cy + ch, ry1)
        if ox1 <= ox0 or oy1 <= oy0:
            continue
        overlap = (ox1 - ox0) * (oy1 - oy0)
        area = cw * ch
        if area <= 0 or (overlap / area) < min_overlap:
            # Zentrum im Rechteck zählt trotzdem
            midx = cx + cw * 0.5
            midy = cy + ch * 0.5
            if not (rx0 <= midx <= rx1 and ry0 <= midy <= ry1):
                continue
        selected.append((cx, cy, cw, ch, text or " "))

    if not selected:
        return [], ""

    # Lesereihenfolge: Y-Band, dann X
    selected.sort(key=lambda c: (round(c[1] / 2.0) * 2, c[0]))
    bands: dict[int, list[tuple[float, float, float, float, str]]] = {}
    for c in selected:
        key = int(round(c[1] / 2.0) * 2)
        bands.setdefault(key, []).append(c)

    rects: List[TextMatchRect] = []
    text_parts: list[str] = []
    for key in sorted(bands.keys()):
        band = sorted(bands[key], key=lambda c: c[0])
        bx0 = min(c[0] for c in band)
        by0 = min(c[1] for c in band)
        bx1 = max(c[0] + c[2] for c in band)
        by1 = max(c[1] + c[3] for c in band)
        snippet = "".join(c[4] for c in band)
        text_parts.append(snippet)
        rect = TextMatchRect(
            page=page_index,
            x=bx0,
            y=by0,
            width=max(bx1 - bx0, 4.0),
            height=max(by1 - by0, 6.0),
            text=snippet.strip(),
        )
        rects.append(rect.scaled(s) if s != 1.0 else rect)

    combined = "\n".join(p.rstrip() for p in text_parts).strip()
    return rects, combined


def import_page_text_as_overlays(
    store: AnnotationStore,
    pdf_path: str | Path,
    page_index: int,
    scale: float = 1.5,
    *,
    replace_page_overlays: bool = False,
) -> List[Annotation]:
    """Extrahiert Textblöcke und legt sie als TEXT_OVERLAY in den Store."""
    blocks = extract_text_blocks(pdf_path, page_index)
    created: List[Annotation] = []
    with store.atomic():
        if replace_page_overlays:
            keep = [
                a
                for a in store.annotations
                if not (a.page == page_index and a.type == AnnotationType.TEXT_OVERLAY)
            ]
            if len(keep) != len(store.annotations):
                store.annotations = keep
                store.dirty = True
        for b in blocks:
            ann = b.to_overlay(scale=scale)
            store.add(ann)
            created.append(ann)
    return created


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def bake_text_overlays(
    pdf_path: str | Path,
    store: AnnotationStore | Sequence[Annotation],
    *,
    scale: float = 1.5,
    out_path: str | Path | None = None,
    types: Optional[Sequence[AnnotationType]] = None,
) -> Path:
    """
    Schreibt TEXT_OVERLAY/TEXT als PDF-Content (Helvetica).
    Koordinaten im Store = Render-Pixel bei `scale` → Division durch scale → PDF-Punkte.
    Native Textobjekte werden nicht verändert — Overlays landen als zusätzliche Content-Streams.
    """
    import pikepdf
    from pikepdf import Name, Dictionary, Stream

    pdf_path = Path(pdf_path)
    out_path = Path(out_path) if out_path else pdf_path
    anns: Sequence[Annotation]
    if isinstance(store, AnnotationStore):
        anns = store.annotations
    else:
        anns = store
    want = set(types or (AnnotationType.TEXT_OVERLAY, AnnotationType.TEXT))

    with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
        by_page: dict[int, list[Annotation]] = {}
        for a in anns:
            if a.type in want and (a.text or "").strip():
                by_page.setdefault(a.page, []).append(a)

        for page_index, items in by_page.items():
            if page_index < 0 or page_index >= len(pdf.pages):
                continue
            page = pdf.pages[page_index]
            mediabox = page.mediabox
            page_h = float(mediabox[3] - mediabox[1])
            parts: list[str] = ["q"]
            for a in items:
                # Pixel (Y oben) → PDF-Punkte (Y unten)
                x = a.x / scale
                y_top = a.y / scale
                fs = max(a.font_size / scale, 6.0)
                # Baseline etwas unter der Box-Oberkante
                y_pdf = page_h - y_top - fs
                # Mehrzeilig: \\n splitten
                lines = (a.text or "").replace("\r\n", "\n").split("\n")
                for li, line in enumerate(lines):
                    if not line:
                        continue
                    yy = y_pdf - li * fs * 1.2
                    parts.append(f"BT /Helv {fs:.2f} Tf 1 0 0 1 {x:.2f} {yy:.2f} Tm ({_pdf_escape(line)}) Tj ET")
            parts.append("Q")
            content = "\n".join(parts).encode("latin-1", errors="replace")

            # Font-Ressource sicherstellen
            if Name.Resources not in page:
                page[Name.Resources] = Dictionary()
            res = page[Name.Resources]
            if Name.Font not in res:
                res[Name.Font] = Dictionary()
            fonts = res[Name.Font]
            if Name.Helv not in fonts:
                fonts[Name.Helv] = Dictionary(
                    Type=Name.Font,
                    Subtype=Name.Type1,
                    BaseFont=Name.Helvetica,
                )

            new_stream = Stream(pdf, content)
            if Name.Contents in page:
                existing = page[Name.Contents]
                if isinstance(existing, pikepdf.Array):
                    existing.append(new_stream)
                else:
                    page[Name.Contents] = pikepdf.Array([existing, new_stream])
            else:
                page[Name.Contents] = new_stream

        pdf.save(out_path)
    return out_path
