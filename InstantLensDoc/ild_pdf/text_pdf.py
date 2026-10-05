"""Text → einfaches Mehrseiten-PDF via pikepdf (leere Seiten + Helvetica-Text)."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

from .pages import PAGE_SIZE_PRESETS

# Producer/CreatorTool in jeder Text→PDF-Ausgabe: macht eigene Dateien im Feld
# (pdf_doctor, Edge/Adobe-Eigenschaften) eindeutig zuordenbar — 2.6.54
PRODUCER = "InstantLens Doc (ild_pdf.text_pdf / pikepdf)"


def _resolve_page_size(
    page_size: Tuple[float, float] | str | None,
) -> tuple[float, float]:
    if isinstance(page_size, tuple) and len(page_size) == 2:
        return float(page_size[0]), float(page_size[1])
    name = str(page_size or "A4")
    return PAGE_SIZE_PRESETS.get(name, PAGE_SIZE_PRESETS["A4"])


def _layout_metrics(
    *,
    page_size: Tuple[float, float] | str | None = None,
    font_size: float = 11.0,
    margin: float = 50.0,
) -> tuple[float, float, float, float, float, int, int]:
    page_w, page_h = _resolve_page_size(page_size)
    fs = max(6.0, min(36.0, float(font_size)))
    mg = max(10.0, min(120.0, float(margin)))
    line_h = fs * 1.35
    usable_w = page_w - 2 * mg
    chars_per_line = max(int(usable_w / (fs * 0.5)), 20)
    lines_per_page = max(int((page_h - 2 * mg) / line_h), 1)
    return page_w, page_h, fs, mg, line_h, chars_per_line, lines_per_page


def _wrap_paragraph(paragraph: str, chars_per_line: int) -> list[str]:
    if not paragraph:
        return [""]
    words = paragraph.split()
    if not words:
        return [""]
    lines: list[str] = []
    cur = words[0]
    for w in words[1:]:
        if len(cur) + 1 + len(w) <= chars_per_line:
            cur = f"{cur} {w}"
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def _all_lines(text: str, chars_per_line: int) -> list[str]:
    out: list[str] = []
    for para in (text or "").replace("\r\n", "\n").split("\n"):
        out.extend(_wrap_paragraph(para, chars_per_line))
    return out


def text_to_pdf(
    text: str,
    path: str | Path,
    *,
    title: str = "InstantLens Doc",
    page_size: Tuple[float, float] | str | None = None,
    font_size: float = 11.0,
    margin: float = 50.0,
) -> Path:
    """
    Aktuellen Plaintext als einfaches PDF speichern (pikepdf add_blank_page).
    Zeilenumbruch nach Zeichenzahl — kein Layout-Engine.
    Schriftgröße/Rand seit 1.7.1 parametrisch.
    """
    import os

    import pikepdf
    from pikepdf import Dictionary, Name, Stream

    dest = Path(path)
    page_w, page_h, fs, mg, line_h, chars_per_line, lines_per_page = _layout_metrics(
        page_size=page_size, font_size=font_size, margin=margin
    )

    all_lines = _all_lines(text, chars_per_line)
    pages_lines = [
        all_lines[i : i + lines_per_page]
        for i in range(0, max(len(all_lines), 1), lines_per_page)
    ]
    if not pages_lines:
        pages_lines = [[""]]

    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    pdf = pikepdf.Pdf.new()
    # WinAnsiEncoding: Umlaute/ß/€ aus dem cp1252-Bereich landen auf den richtigen
    # Glyphen (StandardEncoding zeigte z. B. „ä“ als Fremdzeichen) — 2.6.54
    font = Dictionary(
        Type=Name.Font,
        Subtype=Name.Type1,
        BaseFont=Name.Helvetica,
        Encoding=Name.WinAnsiEncoding,
    )
    for plines in pages_lines:
        parts = [
            "BT",
            f"/F1 {fs:.1f} Tf",
            f"1 0 0 1 {mg:.1f} {page_h - mg:.1f} Tm",
        ]
        first = True
        for line in plines:
            if first:
                parts.append(f"({esc(line)}) Tj")
                first = False
            else:
                parts.append(f"0 {-line_h:.2f} Td ({esc(line)}) Tj")
        parts.append("ET")
        content = "\n".join(parts).encode("cp1252", errors="replace")
        page = pdf.add_blank_page(page_size=(page_w, page_h))
        page[Name.Resources] = Dictionary(Font=Dictionary(F1=font))
        page[Name.Contents] = Stream(pdf, content)

    with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
        if title:
            meta["dc:title"] = title
        meta["pdf:Producer"] = PRODUCER
        meta["xmp:CreatorTool"] = PRODUCER
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Erst in eine Temp-Datei im Zielordner, dann atomar ersetzen: ein Absturz oder
    # Fehler mitten im Schreiben hinterlässt nie eine halbe .pdf — 2.6.54
    tmp = dest.with_name(f".{dest.name}.ild-tmp{os.getpid()}")
    try:
        pdf.save(tmp)
        from .pdf_sniff import assert_valid_pdf

        assert_valid_pdf(tmp, remove_invalid=True)
        os.replace(tmp, dest)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
    return dest


def page_count_for_text(
    text: str,
    *,
    page_size: Tuple[float, float] | str | None = None,
    font_size: float = 11.0,
    margin: float = 50.0,
) -> int:
    """Geschätzte Seitenzahl für Text (gleiche Logik wie text_to_pdf)."""
    *_, chars_per_line, lines_per_page = _layout_metrics(
        page_size=page_size, font_size=font_size, margin=margin
    )
    n_lines = len(_all_lines(text, chars_per_line))
    return max(1, (max(n_lines, 1) + lines_per_page - 1) // lines_per_page)
