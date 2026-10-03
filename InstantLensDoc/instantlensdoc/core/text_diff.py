"""Einfacher Zeilen-Diff für Editor-Tab-Vergleich (ohne Qt)."""

from __future__ import annotations

import difflib


def _short_side(text: str, max_side: int) -> str:
    ta = str(text or "").strip().replace("\n", " ").replace("\r", " ")
    if len(ta) <= max_side:
        return ta
    return ta[: max_side - 1] + "…"


def _tags_short(tags: object | None, *, max_tags: int = 3) -> str:
    if not tags:
        return ""
    parts = [str(t).strip() for t in list(tags) if str(t).strip()]
    if not parts:
        return ""
    shown = parts[:max_tags]
    s = ",".join(shown)
    if len(parts) > max_tags:
        s += "…"
    return f"[{s}]"


def _color_short(color: str | None) -> str:
    c = str(color or "").strip()
    if not c:
        return ""
    if not c.startswith("#"):
        c = "#" + c
    return c.upper() if len(c) <= 9 else c[:9]


def annotation_text_diff_short(
    left: str,
    right: str,
    *,
    max_side: int = 28,
    left_tags: object | None = None,
    right_tags: object | None = None,
    left_color: str | None = None,
    right_color: str | None = None,
) -> str:
    """
    Kurzer Diff-Hinweis zweier Annotationen für Merge-Vorschau.
    Zeigt Textausschnitte sowie optional Tags und Farbe.
    Beispiel: Diff (40%): „foo…“ [a] #FFE066 ≠ „bar…“ [b] #FF6B6B
    """
    ta = str(left or "").strip().replace("\n", " ").replace("\r", " ")
    tb = str(right or "").strip().replace("\n", " ").replace("\r", " ")
    la = _short_side(ta, max_side)
    lb = _short_side(tb, max_side)
    lt = _tags_short(left_tags)
    rt = _tags_short(right_tags)
    lc = _color_short(left_color)
    rc = _color_short(right_color)

    def _fmt(sample: str, tags_s: str, col_s: str) -> str:
        parts = [f"„{sample or '—'}“"]
        if tags_s:
            parts.append(tags_s)
        if col_s:
            parts.append(col_s)
        return " ".join(parts)

    left_s = _fmt(la, lt, lc)
    right_s = _fmt(lb, rt, rc)
    if ta == tb and (lt or "") == (rt or "") and (lc or "") == (rc or ""):
        return f"Diff: identisch ({left_s})"
    sm = difflib.SequenceMatcher(a=ta, b=tb, autojunk=False)
    pct = int(round(sm.ratio() * 100))
    return f"Diff ({pct}%): {left_s} ≠ {right_s}"


def line_diff_sides(left: str, right: str) -> tuple[list[str], list[str], list[str]]:
    """
    Einfacher Zeilen-Diff: liefert (linke Zeilen, rechte Zeilen, Tags).
    Tags: 'equal' | 'replace' | 'delete' | 'insert' (pro ausgegebener Zeile).
    """
    left_lines = (left or "").replace("\r\n", "\n").split("\n")
    right_lines = (right or "").replace("\r\n", "\n").split("\n")
    sm = difflib.SequenceMatcher(a=left_lines, b=right_lines, autojunk=False)
    out_l: list[str] = []
    out_r: list[str] = []
    tags: list[str] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for a, b in zip(left_lines[i1:i2], right_lines[j1:j2]):
                out_l.append(a)
                out_r.append(b)
                tags.append("equal")
        elif tag == "replace":
            n = max(i2 - i1, j2 - j1)
            for k in range(n):
                out_l.append(left_lines[i1 + k] if i1 + k < i2 else "")
                out_r.append(right_lines[j1 + k] if j1 + k < j2 else "")
                tags.append("replace")
        elif tag == "delete":
            for a in left_lines[i1:i2]:
                out_l.append(a)
                out_r.append("")
                tags.append("delete")
        elif tag == "insert":
            for b in right_lines[j1:j2]:
                out_l.append("")
                out_r.append(b)
                tags.append("insert")
    return out_l, out_r, tags
