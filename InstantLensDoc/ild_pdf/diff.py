"""Raster-Diff + Textlayer-Diff zweier PDF-Seiten — 1.4.0–1.4.2 / 2.1.0 / 2.1.1."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageChops, ImageEnhance, ImageOps


@dataclass(frozen=True)
class RasterDiffResult:
    """Ergebnis eines Seiten-Raster-Vergleichs."""

    similarity_percent: float  # 0–100, grob
    different_pixels: int
    total_pixels: int
    overlay: Image.Image  # RGB: Basis + magentafarbene Diff-Maske


@dataclass(frozen=True)
class TextLayerDiffResult:
    """Ergebnis eines Textlayer-Vergleichs zweier PDF-Seiten — 2.1.0/2.1.1."""

    similarity_percent: float  # SequenceMatcher-Ratio 0–100
    left_text: str
    right_text: str
    unified_diff: str
    left_lines: int
    right_lines: int
    changed_hunks: int
    ignore_whitespace: bool = False
    only_differences: bool = False


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
) -> TextLayerDiffResult:
    """
    Textlayer-Diff zweier PDF-Seiten (pypdfium2 Plaintext + difflib).
    Kein Raster — nur extrahierbarer Text. — 2.1.0
    ``ignore_whitespace`` / ``only_differences`` — 2.1.1.
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
        fromfile = f"{Path(left_pdf).name}:p{left_page + 1}"
        tofile = f"{Path(right_pdf).name}:p{right_page + 1}"
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
                fromfile=f"{Path(left_pdf).name}:p{left_page + 1}",
                tofile=f"{Path(right_pdf).name}:p{right_page + 1}",
                lineterm="",
                n=max(0, int(context)),
            )
        )
    pct = round(100.0 * sm.ratio(), 1)
    if only_differences:
        ud = _filter_unified_only_differences(ud)
    # Hunks ≈ Zeilen die mit @@ beginnen
    hunks = sum(1 for line in ud if line.startswith("@@"))
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
    )


def export_text_layer_diff_txt(
    result: TextLayerDiffResult,
    path: str | Path,
    *,
    title: str | None = None,
) -> Path:
    """Unified Textlayer-Diff als TXT speichern — 2.1.1."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    header = [
        title or "InstantLens Doc — Textlayer Unified Diff",
        f"# Ähnlichkeit: {result.similarity_percent:.1f} %",
        f"# Zeilen L/R: {result.left_lines}/{result.right_lines}",
        f"# Hunks: {result.changed_hunks}",
        f"# Ignore-Whitespace: {result.ignore_whitespace}",
        f"# Nur-Unterschiede: {result.only_differences}",
        "",
    ]
    body = result.unified_diff or "(identischer Textlayer — kein Diff)"
    dest.write_text("\n".join(header) + body + "\n", encoding="utf-8")
    return dest
