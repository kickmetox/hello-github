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


def _ws_key(line: str) -> str:
    """Vergleichsschlüssel ohne Whitespace — 1.2.3."""
    import re

    return re.sub(r"\s+", "", line or "")


def line_diff_sides(
    left: str,
    right: str,
    *,
    ignore_whitespace: bool = False,
) -> tuple[list[str], list[str], list[str]]:
    """
    Einfacher Zeilen-Diff: liefert (linke Zeilen, rechte Zeilen, Tags).
    Tags: 'equal' | 'replace' | 'delete' | 'insert' (pro ausgegebener Zeile).
    ``ignore_whitespace``: Zeilen nur anhand Inhalt ohne Whitespace vergleichen
    (Anzeige behält Originalzeilen). — 1.2.3
    """
    left_lines = (left or "").replace("\r\n", "\n").split("\n")
    right_lines = (right or "").replace("\r\n", "\n").split("\n")
    if ignore_whitespace:
        a = [_ws_key(x) for x in left_lines]
        b = [_ws_key(x) for x in right_lines]
    else:
        a, b = left_lines, right_lines
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    out_l: list[str] = []
    out_r: list[str] = []
    tags: list[str] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for aa, bb in zip(left_lines[i1:i2], right_lines[j1:j2]):
                out_l.append(aa)
                out_r.append(bb)
                tags.append("equal")
        elif tag == "replace":
            n = max(i2 - i1, j2 - j1)
            for k in range(n):
                out_l.append(left_lines[i1 + k] if i1 + k < i2 else "")
                out_r.append(right_lines[j1 + k] if j1 + k < j2 else "")
                tags.append("replace")
        elif tag == "delete":
            for aa in left_lines[i1:i2]:
                out_l.append(aa)
                out_r.append("")
                tags.append("delete")
        elif tag == "insert":
            for bb in right_lines[j1:j2]:
                out_l.append("")
                out_r.append(bb)
                tags.append("insert")
    return out_l, out_r, tags


def filter_diff_differences(
    left: list[str],
    right: list[str],
    tags: list[str],
) -> tuple[list[str], list[str], list[str]]:
    """Nur abweichende Zeilen behalten (equal entfernen) — 1.2.1."""
    out_l: list[str] = []
    out_r: list[str] = []
    out_t: list[str] = []
    for a, b, t in zip(left, right, tags):
        if t == "equal":
            continue
        out_l.append(a)
        out_r.append(b)
        out_t.append(t)
    return out_l, out_r, out_t


def word_diff_spans(left: str, right: str) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """
    Einfaches Wort-Diff innerhalb einer Zeile.
    Liefert (left_spans, right_spans) mit Tags equal|replace|delete|insert. — 1.2.2
    """
    import re

    def _tokens(s: str) -> list[str]:
        # Wörter und Trennzeichen getrennt halten
        return re.findall(r"\w+|\W+", s or "") or ([""] if not s else [])

    a = _tokens(left)
    b = _tokens(right)
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    left_spans: list[tuple[str, str]] = []
    right_spans: list[tuple[str, str]] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for t in a[i1:i2]:
                left_spans.append(("equal", t))
            for t in b[j1:j2]:
                right_spans.append(("equal", t))
        elif tag == "replace":
            for t in a[i1:i2]:
                left_spans.append(("replace", t))
            for t in b[j1:j2]:
                right_spans.append(("replace", t))
        elif tag == "delete":
            for t in a[i1:i2]:
                left_spans.append(("delete", t))
        elif tag == "insert":
            for t in b[j1:j2]:
                right_spans.append(("insert", t))
    return left_spans, right_spans


def format_unified_diff(
    left_lines: list[str],
    right_lines: list[str],
    tags: list[str],
    *,
    left_label: str = "Links",
    right_label: str = "Rechts",
    line_numbers: bool = True,
    only_differences: bool = False,
) -> str:
    """Unified-Diff-Text (eine Spalte) — 1.2.2."""
    l_lines, r_lines, t_tags = left_lines, right_lines, tags
    if only_differences:
        l_lines, r_lines, t_tags = filter_diff_differences(l_lines, r_lines, t_tags)
    rows: list[str] = [
        f"--- {left_label}",
        f"+++ {right_label}",
        f"# Unified · Zeilen: {len(t_tags)}"
        + (" (nur Unterschiede)" if only_differences else ""),
        "",
    ]
    for i, (a, b, t) in enumerate(zip(l_lines, r_lines, t_tags), start=1):
        num = f"{i:>4} " if line_numbers else ""
        if t == "equal":
            rows.append(f"  {num}{a}")
        elif t == "replace":
            rows.append(f"- {num}{a}")
            rows.append(f"+ {num}{b}")
        elif t == "delete":
            rows.append(f"- {num}{a}")
        elif t == "insert":
            rows.append(f"+ {num}{b}")
        else:
            rows.append(f"? {num}{a} | {b}")
    return "\n".join(rows).rstrip() + "\n"


def format_diff_txt(
    left_lines: list[str],
    right_lines: list[str],
    tags: list[str],
    *,
    left_label: str = "Links",
    right_label: str = "Rechts",
    line_numbers: bool = True,
    only_differences: bool = False,
    unified: bool = False,
) -> str:
    """
    Diff als Klartext (TXT) für Export.
    Marker: `` `` equal, ``~`` replace, ``-`` delete, ``+`` insert. — 1.2.1/1.2.2
    """
    if unified:
        return format_unified_diff(
            left_lines,
            right_lines,
            tags,
            left_label=left_label,
            right_label=right_label,
            line_numbers=line_numbers,
            only_differences=only_differences,
        )
    l_lines, r_lines, t_tags = left_lines, right_lines, tags
    if only_differences:
        l_lines, r_lines, t_tags = filter_diff_differences(l_lines, r_lines, t_tags)
    mark = {"equal": " ", "replace": "~", "delete": "-", "insert": "+"}
    rows: list[str] = [
        f"--- {left_label}",
        f"+++ {right_label}",
        f"# Zeilen: {len(t_tags)}"
        + (" (nur Unterschiede)" if only_differences else ""),
        "",
    ]
    for i, (a, b, t) in enumerate(zip(l_lines, r_lines, t_tags), start=1):
        m = mark.get(t, "?")
        if line_numbers:
            rows.append(f"{m} {i:>4} | {a}")
            rows.append(f"{m} {i:>4} | {b}")
        else:
            rows.append(f"{m} | {a}")
            rows.append(f"{m} | {b}")
        rows.append("")
    return "\n".join(rows).rstrip() + "\n"
