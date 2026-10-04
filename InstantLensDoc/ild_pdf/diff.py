"""Raster-Diff + Textlayer-Diff zweier PDF-Seiten — 1.4.0–1.4.2 / 2.1.0–2.1.2."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageChops, ImageEnhance, ImageOps

DIFF_FORMAT_UNIFIED = "unified"
DIFF_FORMAT_SIDE_BY_SIDE = "side-by-side"
DIFF_FORMATS = (DIFF_FORMAT_UNIFIED, DIFF_FORMAT_SIDE_BY_SIDE)


@dataclass(frozen=True)
class RasterDiffResult:
    """Ergebnis eines Seiten-Raster-Vergleichs."""

    similarity_percent: float  # 0–100, grob
    different_pixels: int
    total_pixels: int
    overlay: Image.Image  # RGB: Basis + magentafarbene Diff-Maske


@dataclass(frozen=True)
class TextLayerDiffResult:
    """Ergebnis eines Textlayer-Vergleichs zweier PDF-Seiten — 2.1.0–2.1.2."""

    similarity_percent: float  # SequenceMatcher-Ratio 0–100
    left_text: str
    right_text: str
    unified_diff: str
    left_lines: int
    right_lines: int
    changed_hunks: int
    ignore_whitespace: bool = False
    only_differences: bool = False
    side_by_side_diff: str = ""  # Side-by-Side-Text — 2.1.2
    diff_format: str = DIFF_FORMAT_UNIFIED  # unified | side-by-side — 2.1.2


def _as_rgb(img: Image.Image) -> Image.Image:
    if img.mode == "RGB":
        return img
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        return bg
    return img.convert("RGB")


def align_images(
    left: Image.Image, right: Image.Image
) -> Tuple[Image.Image, Image.Image]:
    """Beide Bilder auf gemeinsame Größe (min width/height) bringen."""
    a = _as_rgb(left)
    b = _as_rgb(right)
    w = min(a.width, b.width)
    h = min(a.height, b.height)
    if w < 1 or h < 1:
        return a, b
    if a.size != (w, h):
        a = a.resize((w, h), Image.Resampling.BILINEAR)
    if b.size != (w, h):
        b = b.resize((w, h), Image.Resampling.BILINEAR)
    return a, b


def raster_diff(
    left: Image.Image,
    right: Image.Image,
    *,
    threshold: int = 18,
) -> RasterDiffResult:
    """
    Pixel-Diff zweier gerenderter Seiten.
    similarity_percent ≈ Anteil ähnlicher Pixel (nach Schwellwert), grob.
    overlay: linkes Bild + magentafarbene Markierung der Unterschiede.
    """
    a, b = align_images(left, right)
    w, h = a.size
    total = max(1, w * h)
    # Absolutedifferenz pro Kanal
    diff = ImageChops.difference(a, b)
    # Grau + Schwellwert → Maske
    gray = ImageOps.grayscale(diff)
    # Punktweise: Pixel > threshold gelten als unterschiedlich
    mask = gray.point(lambda p: 255 if p > max(0, min(255, int(threshold))) else 0)
    different = sum(1 for p in mask.getdata() if p)
    similar = max(0, total - different)
    pct = round(100.0 * similar / total, 1)

    # Overlay: Basis abdunkeln + Magenta auf Diff
    base = ImageEnhance.Brightness(a).enhance(0.85)
    overlay = base.copy()
    magenta = Image.new("RGB", (w, h), (220, 40, 180))
    overlay.paste(magenta, mask=mask)

    return RasterDiffResult(
        similarity_percent=pct,
        different_pixels=int(different),
        total_pixels=int(total),
        overlay=overlay,
    )


def _ws_key(line: str) -> str:
    """Whitespace-unabhängiger Vergleichsschlüssel — 2.1.1."""
    return re.sub(r"\s+", "", line or "")


def _filter_unified_only_differences(unified_lines: list[str]) -> list[str]:
    """
    Unified Diff auf Header + geänderte Zeilen (+/-/@@) reduzieren — 2.1.1.
    Context-Zeilen (führendes Leerzeichen) entfallen.
    """
    out: list[str] = []
    for line in unified_lines:
        if (
            line.startswith("---")
            or line.startswith("+++")
            or line.startswith("@@")
            or line.startswith("-")
            or line.startswith("+")
        ):
            # Datei-Header und Hunks/Änderungen behalten; reine Context-Zeilen nicht
            if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
                out.append(line)
            elif line.startswith("-") or line.startswith("+"):
                # +++ / --- schon oben; hier echte Diff-Zeilen
                if not (line.startswith("---") or line.startswith("+++")):
                    out.append(line)
        # Context (leading space) und leere Zeilen auslassen
    return out


def format_side_by_side_diff(
    left_lines: list[str],
    right_lines: list[str],
    *,
    left_label: str = "Links",
    right_label: str = "Rechts",
    ignore_whitespace: bool = False,
    only_differences: bool = False,
    width: int = 48,
) -> str:
    """Side-by-Side Textlayer-Diff als Klartext — 2.1.2."""
    a = list(left_lines)
    b = list(right_lines)
    a_cmp = [_ws_key(x) for x in a] if ignore_whitespace else a
    b_cmp = [_ws_key(x) for x in b] if ignore_whitespace else b
    sm = difflib.SequenceMatcher(a=a_cmp, b=b_cmp, autojunk=False)
    w = max(12, min(120, int(width)))
    rows: list[str] = [
        f"--- {left_label}",
        f"+++ {right_label}",
        f"# Side-by-Side · Spaltenbreite {w}",
        "",
        f"{'L':<{w}} | {'R':<{w}}",
        f"{'-' * w}-+-{'-' * w}",
    ]
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            if only_differences:
                continue
            for la, lb in zip(a[i1:i2], b[j1:j2]):
                rows.append(f"  {la[:w]:<{w}} | {lb[:w]:<{w}}")
        elif tag == "replace":
            n = max(i2 - i1, j2 - j1)
            for k in range(n):
                la = a[i1 + k] if i1 + k < i2 else ""
                lb = b[j1 + k] if j1 + k < j2 else ""
                rows.append(f"~ {la[:w]:<{w}} | {lb[:w]:<{w}}")
        elif tag == "delete":
            for la in a[i1:i2]:
                rows.append(f"- {la[:w]:<{w}} | {'':<{w}}")
        elif tag == "insert":
            for lb in b[j1:j2]:
                rows.append(f"+ {'':<{w}} | {lb[:w]:<{w}}")
    if len(rows) <= 6:
        rows.append("(identischer Textlayer — kein Diff)")
    return "\n".join(rows)


def text_layer_diff(
    left_pdf: str | Path,
    right_pdf: str | Path,
    *,
    left_page: int = 0,
    right_page: int = 0,
    left_password: str | None = None,
    right_password: str | None = None,
    context: int = 2,
    ignore_whitespace: bool = False,
    only_differences: bool = False,
    diff_format: str = DIFF_FORMAT_UNIFIED,
) -> TextLayerDiffResult:
    """
    Textlayer-Diff zweier PDF-Seiten (pypdfium2 Plaintext + difflib).
    Kein Raster — nur extrahierbarer Text. — 2.1.0
    ``ignore_whitespace`` / ``only_differences`` — 2.1.1.
    ``diff_format`` unified|side-by-side — 2.1.2.
    """
    from .overlay import extract_page_plain_text

    left_text = extract_page_plain_text(
        left_pdf, left_page, password=left_password
    ) or ""
    right_text = extract_page_plain_text(
        right_pdf, right_page, password=right_password
    ) or ""
    left_lines = left_text.replace("\r\n", "\n").split("\n")
    right_lines = right_text.replace("\r\n", "\n").split("\n")
    fromfile = f"{Path(left_pdf).name}:p{left_page + 1}"
    tofile = f"{Path(right_pdf).name}:p{right_page + 1}"
    if ignore_whitespace:
        a_cmp = [_ws_key(x) for x in left_lines]
        b_cmp = [_ws_key(x) for x in right_lines]
        # Similarity auf Whitespace-normalisiertem Volltext
        left_cmp = "\n".join(a_cmp)
        right_cmp = "\n".join(b_cmp)
        sm = difflib.SequenceMatcher(a=left_cmp, b=right_cmp, autojunk=False)
        # Unified Diff mit Normalisierung über SequenceMatcher auf Keys,
        # Anzeige aber Originalzeilen
        ud_lines: list[str] = []
        ud_lines.append(f"--- {fromfile}")
        ud_lines.append(f"+++ {tofile}")
        sm_lines = difflib.SequenceMatcher(a=a_cmp, b=b_cmp, autojunk=False)
        n_ctx = max(0, int(context))
        for group in sm_lines.get_grouped_opcodes(n_ctx):
            i1 = group[0][1]
            i2 = group[-1][2]
            j1 = group[0][3]
            j2 = group[-1][4]
            ud_lines.append(f"@@ -{i1 + 1},{i2 - i1} +{j1 + 1},{j2 - j1} @@")
            for tag, a1, a2, b1, b2 in group:
                if tag == "equal":
                    for line in left_lines[a1:a2]:
                        ud_lines.append(f" {line}")
                elif tag == "replace":
                    for line in left_lines[a1:a2]:
                        ud_lines.append(f"-{line}")
                    for line in right_lines[b1:b2]:
                        ud_lines.append(f"+{line}")
                elif tag == "delete":
                    for line in left_lines[a1:a2]:
                        ud_lines.append(f"-{line}")
                elif tag == "insert":
                    for line in right_lines[b1:b2]:
                        ud_lines.append(f"+{line}")
        ud = ud_lines
    else:
        sm = difflib.SequenceMatcher(a=left_text, b=right_text, autojunk=False)
        ud = list(
            difflib.unified_diff(
                left_lines,
                right_lines,
                fromfile=fromfile,
                tofile=tofile,
                lineterm="",
                n=max(0, int(context)),
            )
        )
    pct = round(100.0 * sm.ratio(), 1)
    if only_differences:
        ud = _filter_unified_only_differences(ud)
    # Hunks ≈ Zeilen die mit @@ beginnen
    hunks = sum(1 for line in ud if line.startswith("@@"))
    sbs = format_side_by_side_diff(
        left_lines,
        right_lines,
        left_label=fromfile,
        right_label=tofile,
        ignore_whitespace=bool(ignore_whitespace),
        only_differences=bool(only_differences),
    )
    fmt = (
        DIFF_FORMAT_SIDE_BY_SIDE
        if str(diff_format or "").lower().strip()
        in ("side-by-side", "side_by_side", "sbs", "sidebyside")
        else DIFF_FORMAT_UNIFIED
    )
    return TextLayerDiffResult(
        similarity_percent=pct,
        left_text=left_text,
        right_text=right_text,
        unified_diff="\n".join(ud),
        left_lines=len(left_lines),
        right_lines=len(right_lines),
        changed_hunks=hunks,
        ignore_whitespace=bool(ignore_whitespace),
        only_differences=bool(only_differences),
        side_by_side_diff=sbs,
        diff_format=fmt,
    )


def export_text_layer_diff_txt(
    result: TextLayerDiffResult,
    path: str | Path,
    *,
    title: str | None = None,
    diff_format: str | None = None,
) -> Path:
    """Textlayer-Diff als TXT (unified oder side-by-side) — 2.1.1/2.1.2."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    fmt = (diff_format or result.diff_format or DIFF_FORMAT_UNIFIED).lower().strip()
    side = fmt in ("side-by-side", "side_by_side", "sbs", "sidebyside")
    mode_label = "Side-by-Side" if side else "Unified"
    header = [
        title or f"InstantLens Doc — Textlayer {mode_label} Diff",
        f"# Format: {mode_label}",
        f"# Ähnlichkeit: {result.similarity_percent:.1f} %",
        f"# Zeilen L/R: {result.left_lines}/{result.right_lines}",
        f"# Hunks: {result.changed_hunks}",
        f"# Ignore-Whitespace: {result.ignore_whitespace}",
        f"# Nur-Unterschiede: {result.only_differences}",
        "",
    ]
    if side:
        body = result.side_by_side_diff or "(identischer Textlayer — kein Diff)"
    else:
        body = result.unified_diff or "(identischer Textlayer — kein Diff)"
    dest.write_text("\n".join(header) + body + "\n", encoding="utf-8")
    return dest


def compare_pdf_pages(
    left_pdf: str | Path,
    right_pdf: str | Path,
    *,
    left_page: int = 0,
    right_page: int = 0,
    threshold: int = 18,
    scale: float = 1.0,
    mode: str = "raster",
    ignore_whitespace: bool = False,
    only_differences: bool = False,
    out_png: str | Path | None = None,
    out_txt: str | Path | None = None,
    left_password: str | None = None,
    right_password: str | None = None,
) -> dict:
    """
    PDF-Seiten vergleichen (Raster und/oder Textlayer) — 2.6.19.

    ``mode``: ``raster`` | ``text`` | ``both``.
    Liefert Ähnlichkeit, Diff-Statistik und optional Overlay-PNG / Diff-TXT.
    """
    from .render import render_page

    left_pdf = Path(left_pdf)
    right_pdf = Path(right_pdf)
    lp = max(0, int(left_page))
    rp = max(0, int(right_page))
    thr = max(0, min(255, int(threshold)))
    sc = max(0.25, min(4.0, float(scale or 1.0)))
    m = (mode or "raster").strip().lower()
    if m not in ("raster", "text", "both"):
        m = "raster"

    result: dict = {
        "left": str(left_pdf.resolve()),
        "right": str(right_pdf.resolve()),
        "left_page": lp + 1,
        "right_page": rp + 1,
        "mode": m,
        "threshold": thr,
        "scale": sc,
    }

    if m in ("raster", "both"):
        left_img = render_page(
            left_pdf, lp, scale=sc, password=left_password
        )
        right_img = render_page(
            right_pdf, rp, scale=sc, password=right_password
        )
        rd = raster_diff(left_img, right_img, threshold=thr)
        result["raster"] = {
            "similarity_percent": rd.similarity_percent,
            "different_pixels": rd.different_pixels,
            "total_pixels": rd.total_pixels,
        }
        if out_png is not None:
            dest = Path(out_png)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.suffix.lower() != ".png":
                dest = dest.with_suffix(".png")
            rd.overlay.save(str(dest), "PNG")
            result["out_png"] = str(dest.resolve())

    if m in ("text", "both"):
        td = text_layer_diff(
            left_pdf,
            right_pdf,
            left_page=lp,
            right_page=rp,
            left_password=left_password,
            right_password=right_password,
            ignore_whitespace=bool(ignore_whitespace),
            only_differences=bool(only_differences),
            diff_format=DIFF_FORMAT_UNIFIED,
        )
        result["text"] = {
            "similarity_percent": td.similarity_percent,
            "left_lines": td.left_lines,
            "right_lines": td.right_lines,
            "changed_hunks": td.changed_hunks,
            "ignore_whitespace": td.ignore_whitespace,
            "only_differences": td.only_differences,
        }
        if out_txt is not None:
            dest_t = export_text_layer_diff_txt(td, out_txt)
            result["out_txt"] = str(Path(dest_t).resolve())

    # Kompakte Top-Level-Ähnlichkeit
    if "raster" in result:
        result["similarity_percent"] = result["raster"]["similarity_percent"]
    elif "text" in result:
        result["similarity_percent"] = result["text"]["similarity_percent"]
    else:
        result["similarity_percent"] = 100.0
    return result
