"""Inline-Textbearbeitung + Schriftart-/Formatabgleich — 2.6.4.

Praktischer Stack mit pypdfium2 (Hit-Test, Font/Größe/Farbe) und pikepdf
(Weißabdeckung + neuer Text-Content mit Standard-14-Font-Mapping).
Zeilenumbruch (Reflow) innerhalb der ursprünglichen Box-Breite.
Native Content-Stream-Umschreibung ist nicht 1:1 möglich — Cover+Rewrite.
"""

from __future__ import annotations

import ctypes
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional, Sequence


# Standard-14 Basisnamen (pikepdf Type1)
_STANDARD_BASES = (
    "Helvetica",
    "Helvetica-Bold",
    "Helvetica-Oblique",
    "Helvetica-BoldOblique",
    "Times-Roman",
    "Times-Bold",
    "Times-Italic",
    "Times-BoldItalic",
    "Courier",
    "Courier-Bold",
    "Courier-Oblique",
    "Courier-BoldOblique",
    "Symbol",
    "ZapfDingbats",
)

_FONT_ALIAS = {
    "arial": "Helvetica",
    "helvetica": "Helvetica",
    "sans": "Helvetica",
    "sans-serif": "Helvetica",
    "chrom sans otf": "Helvetica",
    "liberation sans": "Helvetica",
    "noto sans": "Helvetica",
    "dejavu sans": "Helvetica",
    "calibri": "Helvetica",
    "verdana": "Helvetica",
    "tahoma": "Helvetica",
    "times": "Times-Roman",
    "times new roman": "Times-Roman",
    "times-roman": "Times-Roman",
    "serif": "Times-Roman",
    "liberation serif": "Times-Roman",
    "georgia": "Times-Roman",
    "courier": "Courier",
    "courier new": "Courier",
    "monospace": "Courier",
    "consolas": "Courier",
    "liberation mono": "Courier",
}


@dataclass
class TextStyle:
    """Erkannte bzw. Ziel-Schriftattribute (PDF-Punkte)."""

    font_family: str = "Helvetica"
    font_size: float = 11.0
    color: str = "#000000"
    font_weight: int = 400
    base_font: str = "Helvetica"  # Standard-14 zum Schreiben
    italic: bool = False
    bold: bool = False

    def pdf_resource_name(self) -> str:
        """Kurzer Ressourcenname ohne Sonderzeichen."""
        raw = re.sub(r"[^A-Za-z0-9]", "", self.base_font) or "Helv"
        return raw[:16]


@dataclass
class EditableTextSpan:
    """Editierbarer Textspan einer Seite (PDF-Punkte, Y von oben)."""

    page: int
    x: float
    y: float
    width: float
    height: float
    text: str
    style: TextStyle
    char_start: int = 0
    char_end: int = 0

    def scaled(self, scale: float) -> "EditableTextSpan":
        s = float(scale) if scale else 1.0
        if s == 1.0:
            return self
        st = replace(
            self.style,
            font_size=self.style.font_size * s,
        )
        return EditableTextSpan(
            page=self.page,
            x=self.x * s,
            y=self.y * s,
            width=self.width * s,
            height=self.height * s,
            text=self.text,
            style=st,
            char_start=self.char_start,
            char_end=self.char_end,
        )


@dataclass
class InlineEditResult:
    """Ergebnis von ``apply_inline_text_edit``."""

    out_path: Path
    page: int
    lines_written: int
    font_family: str
    font_size: float
    color: str
    covered: bool


def map_to_standard_font(
    family: str,
    *,
    weight: int = 400,
    bold: bool = False,
    italic: bool = False,
) -> str:
    """Mappt Font-Familie auf Standard-14 BaseFont."""
    name = (family or "Helvetica").strip()
    key = name.lower()
    # Direkt Standard?
    for std in _STANDARD_BASES:
        if key == std.lower():
            base = std.split("-")[0]
            if base == "Times":
                base_key = "Times"
            else:
                base_key = base
            break
    else:
        base_key = None
        for alias, mapped in _FONT_ALIAS.items():
            if alias in key or key == alias:
                base_key = mapped.split("-")[0] if mapped != "Times-Roman" else "Times"
                if mapped.startswith("Times"):
                    base_key = "Times"
                elif mapped.startswith("Courier"):
                    base_key = "Courier"
                else:
                    base_key = "Helvetica"
                break
        if base_key is None:
            if "mono" in key or "courier" in key:
                base_key = "Courier"
            elif "times" in key or "serif" in key:
                base_key = "Times"
            else:
                base_key = "Helvetica"

    is_bold = bool(bold) or int(weight or 0) >= 600
    is_italic = bool(italic)
    if base_key == "Times":
        if is_bold and is_italic:
            return "Times-BoldItalic"
        if is_bold:
            return "Times-Bold"
        if is_italic:
            return "Times-Italic"
        return "Times-Roman"
    if base_key == "Courier":
        if is_bold and is_italic:
            return "Courier-BoldOblique"
        if is_bold:
            return "Courier-Bold"
        if is_italic:
            return "Courier-Oblique"
        return "Courier"
    # Helvetica
    if is_bold and is_italic:
        return "Helvetica-BoldOblique"
    if is_bold:
        return "Helvetica-Bold"
    if is_italic:
        return "Helvetica-Oblique"
    return "Helvetica"


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{max(0, min(255, r)):02X}{max(0, min(255, g)):02X}{max(0, min(255, b)):02X}"


def _hex_to_rgb01(color: str) -> tuple[float, float, float]:
    c = (color or "#000000").strip().lstrip("#")
    if len(c) != 6:
        return 0.0, 0.0, 0.0
    try:
        return int(c[0:2], 16) / 255.0, int(c[2:4], 16) / 255.0, int(c[4:6], 16) / 255.0
    except ValueError:
        return 0.0, 0.0, 0.0


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _char_style_raw(textpage_raw, index: int) -> TextStyle:
    """Font/Größe/Farbe eines Zeichens via PDFium-Raw-API."""
    import pypdfium2.raw as raw

    fs = float(raw.FPDFText_GetFontSize(textpage_raw, index) or 11.0)
    if fs <= 0:
        fs = 11.0
    flags = ctypes.c_int(0)
    buflen = int(raw.FPDFText_GetFontInfo(textpage_raw, index, None, 0, flags) or 0)
    family = "Helvetica"
    if buflen > 0:
        buf = ctypes.create_string_buffer(buflen)
        raw.FPDFText_GetFontInfo(textpage_raw, index, buf, buflen, flags)
        try:
            family = (buf.value or b"Helvetica").decode("utf-8", errors="replace") or "Helvetica"
        except Exception:
            family = "Helvetica"
    weight = int(raw.FPDFText_GetFontWeight(textpage_raw, index) or 0)
    if weight <= 0:
        weight = 400
    r = ctypes.c_uint()
    g = ctypes.c_uint()
    b = ctypes.c_uint()
    a = ctypes.c_uint()
    ok = raw.FPDFText_GetFillColor(textpage_raw, index, r, g, b, a)
    color = _rgb_to_hex(int(r.value), int(g.value), int(b.value)) if ok else "#000000"
    # Flags bit 0 = FixedPitch, 6 = Italic (PDF font flags; PDFium may vary)
    italic = bool(flags.value & (1 << 6)) or "italic" in family.lower() or "oblique" in family.lower()
    bold = weight >= 600 or "bold" in family.lower()
    base = map_to_standard_font(family, weight=weight, bold=bold, italic=italic)
    return TextStyle(
        font_family=family,
        font_size=fs,
        color=color,
        font_weight=weight,
        base_font=base,
        italic=italic,
        bold=bold,
    )


def _page_chars_styled(
    pdf_path: str | Path,
    page_index: int,
    *,
    password: str | None = None,
) -> tuple[list[tuple[float, float, float, float, str, TextStyle, int]], float, float]:
    """Zeichen mit Box + Style (Y oben) + Seitengröße."""
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
                chars: list[tuple[float, float, float, float, str, TextStyle, int]] = []
                n = textpage.count_chars()
                raw_tp = textpage.raw
                for i in range(n):
                    ch = textpage.get_text_range(i, 1)
                    box = textpage.get_charbox(i)
                    if box is None:
                        continue
                    l, btm, r, t = box
                    style = _char_style_raw(raw_tp, i)
                    chars.append(
                        (
                            float(l),
                            float(height - t),
                            float(r - l),
                            float(t - btm),
                            ch or " ",
                            style,
                            i,
                        )
                    )
                return chars, float(width), float(height)
            finally:
                textpage.close()
        finally:
            page.close()
    finally:
        doc.close()


def detect_text_style_at(
    pdf_path: str | Path,
    page_index: int,
    x: float,
    y: float,
    *,
    scale: float = 1.0,
    password: str | None = None,
) -> Optional[TextStyle]:
    """Schriftstil am Klickpunkt (Render-Pixel bei scale) erkennen."""
    span = hit_test_text(
        pdf_path, page_index, x, y, scale=scale, password=password
    )
    return span.style if span else None


def hit_test_text(
    pdf_path: str | Path,
    page_index: int,
    x: float,
    y: float,
    *,
    scale: float = 1.0,
    password: str | None = None,
    pad: float = 2.0,
) -> Optional[EditableTextSpan]:
    """
    Trifft Textzeile am Punkt (Render-Pixel bei scale, Y oben).
    Liefert die Zeile mit Style vom nächsten Zeichen.
    """
    s = float(scale) if scale else 1.0
    if s <= 0:
        s = 1.0
    px, py = float(x) / s, float(y) / s
    try:
        chars, _w, _h = _page_chars_styled(pdf_path, page_index, password=password)
    except Exception:
        return None
    if not chars:
        return None

    # Nächstes Zeichen
    best_i = -1
    best_d = 1e18
    for i, (cx, cy, cw, ch, _t, _st, _idx) in enumerate(chars):
        if cw <= 0 or ch <= 0:
            continue
        # Punkt in Box (+pad)?
        if (cx - pad) <= px <= (cx + cw + pad) and (cy - pad) <= py <= (cy + ch + pad):
            midx = cx + cw * 0.5
            midy = cy + ch * 0.5
            d = (midx - px) ** 2 + (midy - py) ** 2
            if d < best_d:
                best_d = d
                best_i = i
    if best_i < 0:
        # Fallback: nächstes Zentrum
        for i, (cx, cy, cw, ch, _t, _st, _idx) in enumerate(chars):
            midx = cx + max(cw, 1) * 0.5
            midy = cy + max(ch, 1) * 0.5
            d = (midx - px) ** 2 + (midy - py) ** 2
            if d < best_d:
                best_d = d
                best_i = i
    if best_i < 0:
        return None

    # Zeilenband um Mid-Y (Leerzeichen-Boxen können andere Tops haben)
    def _mid_y(c: tuple) -> float:
        return float(c[1]) + max(float(c[3]), 1.0) * 0.5

    ref = chars[best_i]
    ref_mid = _mid_y(ref)
    band_tol = max(ref[3], ref[5].font_size, 8.0) * 0.75
    line = [
        c
        for c in chars
        if abs(_mid_y(c) - ref_mid) <= band_tol and c[4] not in ("\r", "\n")
    ]
    if not line:
        line = [ref]
    line = sorted(line, key=lambda c: c[0])
    text = "".join(c[4] for c in line)
    text_stripped = text.strip()
    if not text_stripped:
        return None
    # Box ohne Zero-Width-Kontrollen
    box_chars = [c for c in line if c[2] > 0.1 or (c[4] and not c[4].isspace())]
    if not box_chars:
        box_chars = line
    x0 = min(c[0] for c in box_chars)
    y0 = min(c[1] for c in box_chars)
    x1 = max(c[0] + max(c[2], 0.0) for c in box_chars)
    y1 = max(c[1] + max(c[3], 0.0) for c in box_chars)
    style = ref[5]
    sizes = sorted(
        c[5].font_size for c in line if c[5].font_size > 0 and not (c[4] or "").isspace()
    )
    if sizes:
        style = replace(style, font_size=sizes[len(sizes) // 2])
    span = EditableTextSpan(
        page=page_index,
        x=x0,
        y=y0,
        width=max(x1 - x0, 20.0),
        height=max(y1 - y0, style.font_size),
        text=text_stripped,
        style=style,
        char_start=line[0][6],
        char_end=line[-1][6] + 1,
    )
    return span.scaled(s) if s != 1.0 else span


def text_span_from_selection(
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
) -> Optional[EditableTextSpan]:
    """Auswahlrechteck → EditableTextSpan inkl. Style vom ersten Zeichen."""
    s = float(scale) if scale else 1.0
    if s <= 0:
        s = 1.0
    rx0, rx1 = sorted((float(x0) / s, float(x1) / s))
    ry0, ry1 = sorted((float(y0) / s, float(y1) / s))
    try:
        chars, _w, _h = _page_chars_styled(pdf_path, page_index, password=password)
    except Exception:
        return None
    if not chars:
        return None
    selected: list[tuple[float, float, float, float, str, TextStyle, int]] = []
    for c in chars:
        cx, cy, cw, ch, text, style, idx = c
        if cw <= 0 or ch <= 0:
            continue
        ox0 = max(cx, rx0)
        oy0 = max(cy, ry0)
        ox1 = min(cx + cw, rx1)
        oy1 = min(cy + ch, ry1)
        if ox1 <= ox0 or oy1 <= oy0:
            midx = cx + cw * 0.5
            midy = cy + ch * 0.5
            if not (rx0 <= midx <= rx1 and ry0 <= midy <= ry1):
                continue
        else:
            overlap = (ox1 - ox0) * (oy1 - oy0)
            area = cw * ch
            if area > 0 and (overlap / area) < min_overlap:
                midx = cx + cw * 0.5
                midy = cy + ch * 0.5
                if not (rx0 <= midx <= rx1 and ry0 <= midy <= ry1):
                    continue
        selected.append(c)
    if not selected:
        return None
    selected = [c for c in selected if c[4] not in ("\r", "\n")]
    if not selected:
        return None

    def _mid_y(c: tuple) -> float:
        return float(c[1]) + max(float(c[3]), 1.0) * 0.5

    selected.sort(key=lambda c: (_mid_y(c), c[0]))
    # Mehrzeilig: Bands nach Mid-Y
    bands: dict[int, list] = {}
    for c in selected:
        key = int(round(_mid_y(c) / 2.0) * 2)
        bands.setdefault(key, []).append(c)
    text_parts: list[str] = []
    all_chars: list = []
    for key in sorted(bands.keys()):
        band = sorted(bands[key], key=lambda c: c[0])
        text_parts.append("".join(c[4] for c in band).rstrip())
        all_chars.extend(band)
    text = "\n".join(p for p in text_parts if p is not None).strip()
    if not text:
        return None
    bx0 = min(c[0] for c in all_chars)
    by0 = min(c[1] for c in all_chars)
    bx1 = max(c[0] + c[2] for c in all_chars)
    by1 = max(c[1] + c[3] for c in all_chars)
    style = all_chars[0][5]
    sizes = sorted(c[5].font_size for c in all_chars if c[5].font_size > 0)
    if sizes:
        style = replace(style, font_size=sizes[len(sizes) // 2])
    # dominante Farbe
    colors = [c[5].color for c in all_chars]
    if colors:
        style = replace(style, color=max(set(colors), key=colors.count))
    span = EditableTextSpan(
        page=page_index,
        x=bx0,
        y=by0,
        width=max(bx1 - bx0, 20.0),
        height=max(by1 - by0, style.font_size),
        text=text,
        style=style,
        char_start=all_chars[0][6],
        char_end=all_chars[-1][6] + 1,
    )
    return span.scaled(s) if s != 1.0 else span


def reflow_lines(
    text: str,
    max_width_pt: float,
    font_size: float,
    *,
    avg_char_factor: float = 0.5,
) -> list[str]:
    """Einfacher Wortumbruch innerhalb max_width (PDF-Punkte)."""
    fs = max(6.0, float(font_size))
    max_w = max(float(max_width_pt), fs * 2)
    chars_per_line = max(int(max_w / (fs * avg_char_factor)), 8)
    out: list[str] = []
    for para in (text or "").replace("\r\n", "\n").split("\n"):
        if not para.strip():
            out.append("")
            continue
        words = para.split()
        if not words:
            out.append("")
            continue
        cur = words[0]
        for w in words[1:]:
            if len(cur) + 1 + len(w) <= chars_per_line:
                cur = f"{cur} {w}"
            else:
                out.append(cur)
                cur = w
        out.append(cur)
    return out if out else [""]


def apply_inline_text_edit(
    pdf_path: str | Path,
    span: EditableTextSpan,
    new_text: str,
    *,
    style: TextStyle | None = None,
    scale: float = 1.0,
    out_path: str | Path | None = None,
    cover: bool = True,
    cover_color: str = "#FFFFFF",
) -> InlineEditResult:
    """
    Ersetzt Text praktisch: optional Weißabdeckung der Alt-Box, dann neuer
    Content-Stream mit gemapptem Standard-Font, Größe und Farbe; Reflow in Box-Breite.

    ``span``-Koordinaten = Render-Pixel bei ``scale`` (wie Annotationen) oder
    PDF-Punkte wenn scale=1.0.
    """
    import pikepdf
    from pikepdf import Dictionary, Name, Stream

    pdf_path = Path(pdf_path)
    out_path = Path(out_path) if out_path else pdf_path
    s = float(scale) if scale else 1.0
    if s <= 0:
        s = 1.0
    st = style or span.style
    fs = max(st.font_size / s, 6.0)
    x = float(span.x) / s
    y_top = float(span.y) / s
    box_w = max(float(span.width) / s, fs * 2)
    box_h = max(float(span.height) / s, fs * 1.2)
    base_font = st.base_font or map_to_standard_font(
        st.font_family, weight=st.font_weight, bold=st.bold, italic=st.italic
    )
    lines = reflow_lines(new_text if new_text is not None else "", box_w, fs)
    # Leerer Text = nur abdecken (löschen)
    write_lines = [ln for ln in lines] if (new_text or "").strip() else []
    r, g, b = _hex_to_rgb01(st.color)
    cr, cg, cb = _hex_to_rgb01(cover_color)
    res_name = re.sub(r"[^A-Za-z0-9]", "", base_font) or "Helv"
    res_name = res_name[:16]
    font_name = Name("/" + res_name)

    with pikepdf.open(
        pdf_path, allow_overwriting_input=(out_path.resolve() == pdf_path.resolve())
    ) as pdf:
        page_index = int(span.page)
        if page_index < 0 or page_index >= len(pdf.pages):
            raise IndexError(f"Seite {page_index} existiert nicht")
        page = pdf.pages[page_index]
        mediabox = page.mediabox
        page_h = float(mediabox[3] - mediabox[1])
        parts: list[str] = ["q"]
        if cover:
            # etwas Padding
            pad = max(fs * 0.15, 1.0)
            # Höhe für Reflow ggf. erweitern
            line_h = fs * 1.2
            need_h = max(box_h, line_h * max(len(write_lines), 1) + pad)
            y_pdf_box = page_h - y_top - need_h
            parts.append(f"{cr:.3f} {cg:.3f} {cb:.3f} rg")
            parts.append(
                f"{x - pad:.2f} {y_pdf_box - pad:.2f} "
                f"{box_w + 2 * pad:.2f} {need_h + 2 * pad:.2f} re f"
            )
        if write_lines:
            parts.append(f"{r:.3f} {g:.3f} {b:.3f} rg")
            for li, line in enumerate(write_lines):
                # Baseline unter Zeilen-Oberkante
                yy = page_h - y_top - fs - li * fs * 1.2
                if not line:
                    continue
                parts.append(
                    f"BT /{res_name} {fs:.2f} Tf 1 0 0 1 {x:.2f} {yy:.2f} Tm "
                    f"({_pdf_escape(line)}) Tj ET"
                )
        parts.append("Q")
        content = "\n".join(parts).encode("latin-1", errors="replace")

        if Name.Resources not in page:
            page[Name.Resources] = Dictionary()
        res = page[Name.Resources]
        if Name.Font not in res:
            res[Name.Font] = Dictionary()
        fonts = res[Name.Font]
        if font_name not in fonts:
            fonts[font_name] = Dictionary(
                Type=Name.Font,
                Subtype=Name.Type1,
                BaseFont=Name("/" + base_font),
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

    return InlineEditResult(
        out_path=Path(out_path),
        page=page_index,
        lines_written=len([ln for ln in write_lines if ln]),
        font_family=base_font,
        font_size=fs,
        color=st.color,
        covered=bool(cover),
    )


def insert_text_at(
    pdf_path: str | Path,
    page_index: int,
    x: float,
    y: float,
    text: str,
    *,
    style: TextStyle | None = None,
    max_width: float = 400.0,
    scale: float = 1.0,
    out_path: str | Path | None = None,
) -> InlineEditResult:
    """Neuen Text an Position einfügen (Style optional vom Kontext)."""
    st = style or TextStyle()
    if style is None:
        nearby = hit_test_text(pdf_path, page_index, x, y, scale=scale)
        if nearby is not None:
            st = nearby.style
    s = float(scale) if scale else 1.0
    span = EditableTextSpan(
        page=page_index,
        x=float(x),
        y=float(y),
        width=max(float(max_width), st.font_size * 4),
        height=max(st.font_size * 1.4, 12.0) * max(s, 1.0),
        text="",
        style=st,
    )
    return apply_inline_text_edit(
        pdf_path,
        span,
        text,
        style=st,
        scale=scale,
        out_path=out_path,
        cover=False,
    )
