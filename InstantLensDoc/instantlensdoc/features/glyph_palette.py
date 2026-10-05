"""Glyphen-Palette: Unicode-Blöcke einer Schrift, Einfügen in Textrahmen."""

from __future__ import annotations

import unicodedata
from typing import Iterable, Sequence

# BMP-Blöcke, die in DTP-Satzspiegeln häufig gebraucht werden
_BLOCKS: dict[str, Sequence[int]] = {
    "latin": list(range(0x20, 0x7F)),
    "latin1": list(range(0xA0, 0x100)),
    "latin_ext": list(range(0x100, 0x180)),
    "punctuation": list(range(0x2000, 0x2070)) + list(range(0x2E00, 0x2E30)),
    "currency": list(range(0x20A0, 0x20C0)),
    "arrows": list(range(0x2190, 0x21FF)),
    "math": list(range(0x2200, 0x22FF)),
    "box": list(range(0x2500, 0x2580)),
    "geometric": list(range(0x25A0, 0x2600)),
    "dingbats": list(range(0x2700, 0x27C0)),
}

DEFAULT_BLOCKS = ("latin", "latin1", "currency", "punctuation", "arrows", "math")


def list_glyph_blocks() -> list[str]:
    return list(_BLOCKS.keys())


def _safe_name(cp: int) -> str:
    try:
        return unicodedata.name(chr(cp))
    except ValueError:
        return f"U+{cp:04X}"


def list_glyphs(
    family: str = "",
    *,
    blocks: Iterable[str] | None = None,
    limit: int = 800,
) -> list[dict]:
    """Glyphen als {char, codepoint, name, block, category}. family nur Metadaten."""
    names = list(blocks) if blocks is not None else list(DEFAULT_BLOCKS)
    out: list[dict] = []
    seen: set[int] = set()
    cap = max(16, int(limit))
    for block in names:
        cps = _BLOCKS.get(block) or ()
        for cp in cps:
            if cp in seen:
                continue
            ch = chr(cp)
            cat = unicodedata.category(ch)
            if cat in ("Cc", "Cs", "Co"):
                continue
            seen.add(cp)
            out.append(
                {
                    "char": ch,
                    "codepoint": cp,
                    "hex": f"U+{cp:04X}",
                    "name": _safe_name(cp),
                    "block": block,
                    "category": cat,
                    "family": family or "",
                }
            )
            if len(out) >= cap:
                return out
    return out


def insert_glyph(text: str, glyph: str, *, index: int | None = None) -> str:
    src = text or ""
    g = glyph or ""
    if not g:
        return src
    if index is None or index < 0 or index > len(src):
        return src + g
    return src[:index] + g + src[index:]
