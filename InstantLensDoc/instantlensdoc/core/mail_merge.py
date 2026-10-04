"""Seriendruck-Basis: Empfänger aus CSV/Excel → Briefe — 2.6.21.

Platzhalter ``{{Feld}}`` / ``«Feld»`` im Template; lokal, ohne Cloud.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any, Sequence

_PLACEHOLDER_RE = re.compile(
    r"\{\{\s*([A-Za-z_][\w]*)\s*\}\}|«\s*([A-Za-z_][\w]*)\s*»"
)


def load_recipients_csv(path: str | Path) -> list[dict[str, str]]:
    """CSV mit Kopfzeile laden → Liste von Empfänger-Dicts."""
    p = Path(path)
    text = p.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(text.splitlines())
    rows: list[dict[str, str]] = []
    for row in reader:
        if not isinstance(row, dict):
            continue
        cleaned = {
            str(k).strip(): ("" if v is None else str(v))
            for k, v in row.items()
            if k is not None and str(k).strip()
        }
        if any(v.strip() for v in cleaned.values()):
            rows.append(cleaned)
    return rows


def load_recipients_xlsx(path: str | Path) -> list[dict[str, str]]:
    """Erste Sheet als Empfängerliste (openpyxl falls vorhanden)."""
    p = Path(path)
    try:
        from openpyxl import load_workbook
    except ImportError as e:
        raise RuntimeError(
            "openpyxl fehlt — CSV nutzen oder openpyxl installieren"
        ) from e
    wb = load_workbook(p, read_only=True, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    try:
        header = next(rows_iter)
    except StopIteration:
        return []
    keys = [
        str(h).strip() if h is not None else f"col{i}"
        for i, h in enumerate(header)
    ]
    out: list[dict[str, str]] = []
    for raw in rows_iter:
        row = {
            keys[i]: ("" if (raw[i] is None) else str(raw[i]))
            for i in range(min(len(keys), len(raw or ())))
            if keys[i]
        }
        if any(v.strip() for v in row.values()):
            out.append(row)
    return out


def load_recipients(path: str | Path) -> list[dict[str, str]]:
    p = Path(path)
    suf = p.suffix.lower()
    if suf in (".xlsx", ".xlsm"):
        return load_recipients_xlsx(p)
    return load_recipients_csv(p)


def find_placeholders(template: str) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for m in _PLACEHOLDER_RE.finditer(template or ""):
        name = m.group(1) or m.group(2) or ""
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    return names


def merge_one(template: str, fields: dict[str, Any]) -> str:
    mapping = {str(k): ("" if v is None else str(v)) for k, v in (fields or {}).items()}

    def _repl(m: re.Match[str]) -> str:
        name = m.group(1) or m.group(2) or ""
        return mapping.get(name, m.group(0))

    return _PLACEHOLDER_RE.sub(_repl, template or "")


def mail_merge(
    template: str,
    recipients: Sequence[dict[str, Any]],
) -> list[str]:
    """Jeden Empfänger zu einem Brieftext mergen."""
    return [merge_one(template, r) for r in recipients]


def mail_merge_to_dir(
    template: str,
    recipients: Sequence[dict[str, Any]],
    out_dir: str | Path,
    *,
    stem: str = "letter",
) -> list[Path]:
    """Briefe als ``letter_001.txt`` … schreiben."""
    dest = Path(out_dir)
    dest.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for i, letter in enumerate(mail_merge(template, recipients), start=1):
        path = dest / f"{stem}_{i:03d}.txt"
        path.write_text(letter, encoding="utf-8")
        written.append(path)
    return written


def mail_merge_from_files(
    template_path: str | Path,
    recipients_path: str | Path,
    out_dir: str | Path,
    *,
    stem: str = "letter",
) -> dict[str, Any]:
    tpl_path = Path(template_path)
    template = tpl_path.read_text(encoding="utf-8")
    recipients = load_recipients(recipients_path)
    paths = mail_merge_to_dir(template, recipients, out_dir, stem=stem)
    return {
        "template": str(tpl_path),
        "recipients": str(Path(recipients_path)),
        "count": len(paths),
        "placeholders": find_placeholders(template),
        "output": [str(p) for p in paths],
        "out_dir": str(Path(out_dir)),
    }
