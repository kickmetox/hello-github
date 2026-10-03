"""Batch-Umbenennen offener Tabs: Template {stem}_{n} + Vorschau — 1.4.0."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence


DEFAULT_BATCH_RENAME_TEMPLATE = "{stem}_{n}"

_PLACEHOLDER_RE = re.compile(r"\{(stem|n|ext|name)\}")


@dataclass(frozen=True)
class RenamePreviewItem:
    """Eine Zeile der Umbenenn-Vorschau."""

    old_path: str
    new_name: str
    new_path: str
    skipped: bool = False
    reason: str = ""


def apply_rename_template(
    template: str,
    *,
    stem: str,
    n: int,
    ext: str,
    name: str = "",
) -> str:
    """
    Template → Dateiname (ohne Pfad).
    Platzhalter: {stem} {n} {ext} {name}
    {ext} ohne führenden Punkt wenn Template ihn setzt; sonst Suffix mit Punkt.
    """
    tpl = (template or DEFAULT_BATCH_RENAME_TEMPLATE).strip() or DEFAULT_BATCH_RENAME_TEMPLATE
    ext_clean = ext.lstrip(".") if ext else ""
    mapping = {
        "stem": stem or "doc",
        "n": str(int(n)),
        "ext": ext_clean,
        "name": name or (f"{stem}.{ext_clean}" if ext_clean else stem),
    }

    def _sub(m: re.Match) -> str:
        return mapping.get(m.group(1), m.group(0))

    out = _PLACEHOLDER_RE.sub(_sub, tpl)
    # Wenn Template keine Extension enthält, Suffix anhängen
    if ext_clean and not out.lower().endswith("." + ext_clean.lower()):
        if "{ext}" not in tpl.casefold():
            out = f"{out}.{ext_clean}"
    return out


def preview_batch_rename(
    paths: Sequence[str],
    template: str = DEFAULT_BATCH_RENAME_TEMPLATE,
    *,
    start_index: int = 1,
) -> List[RenamePreviewItem]:
    """Vorschau für offene Tabs / Dateiliste; Index ab start_index."""
    items: List[RenamePreviewItem] = []
    seen_targets: set[str] = set()
    n = max(0, int(start_index))
    for raw in paths:
        p = Path(raw)
        if not raw:
            continue
        if not p.is_file() and not p.exists():
            # Auch nicht-existente offene Tabs listen (z. B. neu)
            stem, ext = p.stem, p.suffix
        else:
            stem, ext = p.stem, p.suffix
        new_name = apply_rename_template(
            template, stem=stem, n=n, ext=ext, name=p.name
        )
        n += 1
        new_path = str(p.with_name(new_name))
        skipped = False
        reason = ""
        key = new_path.casefold()
        if new_name == p.name:
            skipped = True
            reason = "unverändert"
        elif key in seen_targets:
            skipped = True
            reason = "Kollision in Liste"
        elif Path(new_path).exists() and Path(new_path).resolve() != (
            p.resolve() if p.exists() else Path(new_path)
        ):
            skipped = True
            reason = "Zieldatei existiert"
        else:
            seen_targets.add(key)
        items.append(
            RenamePreviewItem(
                old_path=str(p),
                new_name=new_name,
                new_path=new_path,
                skipped=skipped,
                reason=reason,
            )
        )
    return items


def rename_files(
    items: Iterable[RenamePreviewItem],
    *,
    also_sidecars: bool = True,
) -> List[tuple[str, str, str | None]]:
    """
    Führt Umbenennungen aus.
    Returns: Liste (old, new, error|None).
    Sidecars: *.ildann.json, *.ildocr.txt, page_favorites etc. neben PDF.
    """
    results: List[tuple[str, str, str | None]] = []
    sidecar_suffixes = (
        ".ildann.json",
        ".ildocr.txt",
        ".ildfav.json",
        ".ildbm.json",
    )
    for it in items:
        if it.skipped:
            results.append((it.old_path, it.new_path, it.reason or "übersprungen"))
            continue
        src = Path(it.old_path)
        dst = Path(it.new_path)
        try:
            if not src.exists():
                results.append((it.old_path, it.new_path, "Quelle fehlt"))
                continue
            if dst.exists() and dst.resolve() != src.resolve():
                results.append((it.old_path, it.new_path, "Ziel existiert"))
                continue
            src.rename(dst)
            if also_sidecars:
                for suf in sidecar_suffixes:
                    # Sidecar: datei.pdf.ildann.json (= str(pdf) + ".ildann.json")
                    c = Path(str(src) + suf)
                    if c.is_file():
                        target = Path(str(dst) + suf)
                        if not target.exists():
                            c.rename(target)
            results.append((it.old_path, it.new_path, None))
        except Exception as e:
            results.append((it.old_path, it.new_path, str(e)))
    return results
