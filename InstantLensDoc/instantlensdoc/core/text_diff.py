"""Einfacher Zeilen-Diff für Editor-Tab-Vergleich (ohne Qt)."""

from __future__ import annotations

import difflib


def annotation_text_diff_short(
    left: str,
    right: str,
    *,
    max_side: int = 28,
) -> str:
    """
    Kurzer Diff-Hinweis zweier Annotationstexte für Merge-Vorschau.
    Beispiel: Diff (40%): „foo…“ ≠ „bar…“
    """
    ta = str(left or "").strip().replace("\n", " ").replace("\r", " ")
    tb = str(right or "").strip().replace("\n", " ").replace("\r", " ")
    if ta == tb:
        sample = ta if len(ta) <= max_side else ta[: max_side - 1] + "…"
        return f"Diff: identisch („{sample or '—'}“)"
    sm = difflib.SequenceMatcher(a=ta, b=tb, autojunk=False)
    pct = int(round(sm.ratio() * 100))
    la = ta if len(ta) <= max_side else ta[: max_side - 1] + "…"
    lb = tb if len(tb) <= max_side else tb[: max_side - 1] + "…"
    return f"Diff ({pct}%): „{la or '—'}“ ≠ „{lb or '—'}“"


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
