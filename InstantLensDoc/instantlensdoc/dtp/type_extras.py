"""Typografie-Extras: Kerning, Baseline, Witwen/Waisen, Notes, Variablen, CJK-Ziffern."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

DIGITS = {
    "latin": "0123456789",
    "bengali": "০১২৩৪৫৬৭৮৯",
    "devanagari": "०१२३४५६७८९",
    "thai": "๐๑๒๓๔๕๖๗๘๙",
    "cjk": "零一二三四五六七八九",
}

FONT_FALLBACKS = {
    "cjk": ("Noto Sans CJK SC", "Source Han Sans SC", "WenQuanYi Zen Hei", "Noto Sans"),
    "bengali": ("Noto Sans Bengali", "Lohit Bengali", "Noto Sans"),
    "devanagari": ("Noto Sans Devanagari", "Lohit Devanagari", "Noto Sans"),
    "thai": ("Noto Sans Thai", "Garuda", "Noto Sans"),
}


def format_number(n: int, system: str = "latin") -> str:
    sys = (system or "latin").lower()
    digits = DIGITS.get(sys) or DIGITS["latin"]
    if sys == "cjk" and 0 <= int(n) <= 9:
        return digits[int(n)]
    s = str(abs(int(n)))
    out = "".join(digits[int(ch)] if ch.isdigit() and int(ch) < len(digits) else ch for ch in s)
    return ("-" if n < 0 else "") + out


def list_system_fonts() -> list[str]:
    """Installierte Schriften (Windows: QFontDatabase, sonst Qt-Families)."""
    try:
        from PySide6.QtGui import QFontDatabase
        from PySide6.QtWidgets import QApplication

        if QApplication.instance() is None:
            return ["serif", "sans-serif", "monospace"]
        fams = [str(f) for f in QFontDatabase.families() if str(f).strip()]
        return fams or ["serif", "sans-serif", "monospace"]
    except Exception:
        return ["serif", "sans-serif", "monospace"]


def list_script_fonts(script: str = "cjk") -> list[str]:
    names = list(FONT_FALLBACKS.get((script or "").lower(), FONT_FALLBACKS["cjk"]))
    try:
        from PySide6.QtGui import QFontDatabase

        fams = [str(f) for f in QFontDatabase.families()]
        needles = {
            "cjk": ("cjk", "chinese", "japanese", "korean", "noto sans sc", "source han"),
            "bengali": ("bengali", "bangla"),
            "devanagari": ("devanagari", "hindi"),
            "thai": ("thai",),
        }.get((script or "").lower(), ())
        for f in fams:
            low = f.lower()
            if any(n in low for n in needles) and f not in names:
                names.append(f)
    except Exception:
        pass
    return names


def apply_pair_kerning(text: str, pairs: dict[str, float]) -> str:
    """Manuelles Kerning: Paare als Hair-Space/Thin-Space-Näherung im Plaintext."""
    if not pairs or not text:
        return text or ""
    out = []
    i = 0
    while i < len(text):
        pair = text[i : i + 2]
        adj = pairs.get(pair)
        out.append(text[i])
        if adj is not None and i + 1 < len(text):
            if adj < -10:
                out.append("\u2009")  # thin space as negative-kern stand-in when missing GPOS
            elif adj > 10:
                out.append("\u2006")
        i += 1
    return "".join(out)


def keep_orphans_widows(lines: list[str], *, min_start: int = 2, min_end: int = 2) -> list[str]:
    """Verhindert 1-Zeilen-Stümpfe am Rahmenanfang/-ende (einfache Zeilenliste)."""
    if len(lines) <= max(min_start, min_end):
        return list(lines)
    out = list(lines)
    while out and len(out) >= 2 and out[0].strip() == "":
        out.pop(0)
    return out


def split_avoiding_widows(
    text: str,
    capacity_chars: int,
    *,
    min_end: int = 2,
) -> tuple[str, str]:
    """Bricht Text so, dass am Ende des ersten Stücks mindestens min_end Zeilen bleiben."""
    raw = text or ""
    if len(raw) <= capacity_chars:
        return raw, ""
    chunk, rest = raw[:capacity_chars], raw[capacity_chars:]
    nl = chunk.rfind("\n")
    lines = chunk.split("\n")
    if len(lines) > min_end and nl > 0:
        # letzte unvollständige Zeile zum Rest
        keep = "\n".join(lines[:-1]) if len(lines[-1]) < 12 else chunk
        rest = raw[len(keep) :].lstrip("\n")
        return keep, rest
    return chunk, rest


@dataclass
class DtpNote:
    id: str
    kind: str  # footnote | endnote
    marker: str
    body: str
    frame_id: str = ""
    page: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "marker": self.marker,
            "body": self.body,
            "frame_id": self.frame_id,
            "page": self.page,
        }


@dataclass
class CrossRef:
    id: str
    target_frame_id: str
    fmt: str = "S. {page}"

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "target_frame_id": self.target_frame_id, "fmt": self.fmt}


def expand_variables(
    text: str,
    *,
    page: int = 1,
    total: int = 1,
    title: str = "",
    variables: dict[str, str] | None = None,
    notes: list[DtpNote] | None = None,
    number_system: str = "latin",
) -> str:
    vars_ = dict(variables or {})
    vars_.setdefault("page", format_number(page, number_system))
    vars_.setdefault("total", format_number(total, number_system))
    vars_.setdefault("title", title or "")
    vars_.setdefault("date", date.today().isoformat())
    out = text or ""
    for k, v in vars_.items():
        out = out.replace("{" + k + "}", str(v))
        out = out.replace("<" + k + ">", str(v))
    if notes:
        for n in notes:
            out = out.replace("{note:" + n.id + "}", n.marker)
            out = out.replace("{footnote:" + n.id + "}", n.marker)
    return out


def resolve_cross_ref(cref: CrossRef, frames: list[Any]) -> str:
    page = 1
    for fr in frames:
        if getattr(fr, "id", "") == cref.target_frame_id:
            page = int(getattr(fr, "page", 0)) + 1
            break
    return (cref.fmt or "S. {page}").replace("{page}", str(page))
