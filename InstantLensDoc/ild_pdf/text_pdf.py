"""Text → einfaches Mehrseiten-PDF via pikepdf (leere Seiten + Helvetica-Text)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

from .pages import PAGE_SIZE_PRESETS


def text_to_pdf(
    text: str,
    path: str | Path,
    *,
    title: str = "InstantLens Doc",
    page_size: Tuple[float, float] | str | None = None,
) -> Path:
    """
    Aktuellen Plaintext als einfaches PDF speichern (pikepdf add_blank_page).
    Zeilenumbruch nach Zeichenzahl — kein Layout-Engine.
    """
    import pikepdf
    from pikepdf import Dictionary, Name, Stream

    dest = Path(path)
    if isinstance(page_size, tuple) and len(page_size) == 2:
        page_w, page_h = float(page_size[0]), float(page_size[1])
    else:
        name = str(page_size or "A4")
        page_w, page_h = PAGE_SIZE_PRESETS.get(name, PAGE_SIZE_PRESETS["A4"])

    margin = 50.0
    font_size = 11.0
    line_h = font_size * 1.35
    usable_w = page_w - 2 * margin
    chars_per_line = max(int(usable_w / (font_size * 0.5)), 40)

    def _lines(raw: str) -> list[str]:
        return (raw or "").replace("\r\n", "\n").split("\n")

    def wrap(paragraph: str) -> list[str]:
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

    all_lines: list[str] = []
    for para in _lines(text):
        all_lines.extend(wrap(para))

    lines_per_page = max(int((page_h - 2 * margin) / line_h), 1)
    pages_lines = [
        all_lines[i : i + lines_per_page]
        for i in range(0, max(len(all_lines), 1), lines_per_page)
    ]
    if not pages_lines:
        pages_lines = [[""]]

    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    pdf = pikepdf.Pdf.new()
    font = Dictionary(
        Type=Name.Font,
        Subtype=Name.Type1,
        BaseFont=Name.Helvetica,
    )
    for plines in pages_lines:
        parts = [
            "BT",
            f"/F1 {font_size:.1f} Tf",
            f"1 0 0 1 {margin:.1f} {page_h - margin:.1f} Tm",
        ]
        first = True
        for line in plines:
            if first:
                parts.append(f"({esc(line)}) Tj")
                first = False
            else:
                parts.append(f"0 {-line_h:.2f} Td ({esc(line)}) Tj")
        parts.append("ET")
        content = "\n".join(parts).encode("latin-1", errors="replace")
        page = pdf.add_blank_page(page_size=(page_w, page_h))
        page[Name.Resources] = Dictionary(Font=Dictionary(F1=font))
        page[Name.Contents] = Stream(pdf, content)

    if title:
        with pdf.open_metadata() as meta:
            meta["dc:title"] = title
    dest.parent.mkdir(parents=True, exist_ok=True)
    pdf.save(dest)
    return dest


def page_count_for_text(
    text: str,
    *,
    page_size: Tuple[float, float] | str | None = None,
) -> int:
    """Geschätzte Seitenzahl für Text (gleiche Logik wie text_to_pdf)."""
    if isinstance(page_size, tuple) and len(page_size) == 2:
        page_w, page_h = float(page_size[0]), float(page_size[1])
    else:
        name = str(page_size or "A4")
        page_w, page_h = PAGE_SIZE_PRESETS.get(name, PAGE_SIZE_PRESETS["A4"])
    margin = 50.0
    font_size = 11.0
    line_h = font_size * 1.35
    usable_w = page_w - 2 * margin
    chars_per_line = max(int(usable_w / (font_size * 0.5)), 40)
    lines_per_page = max(int((page_h - 2 * margin) / line_h), 1)

    def wrap(paragraph: str) -> list[str]:
        if not paragraph:
            return [""]
        words = paragraph.split()
        if not words:
            return [""]
        out: list[str] = []
        cur = words[0]
        for w in words[1:]:
            if len(cur) + 1 + len(w) <= chars_per_line:
                cur = f"{cur} {w}"
            else:
                out.append(cur)
                cur = w
        out.append(cur)
        return out

    n_lines = 0
    for para in (text or "").replace("\r\n", "\n").split("\n"):
        n_lines += len(wrap(para))
    return max(1, (max(n_lines, 1) + lines_per_page - 1) // lines_per_page)
