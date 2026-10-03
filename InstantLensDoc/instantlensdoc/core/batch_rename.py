"""Batch-Umbenennen offener Tabs: Template {stem}_{n} + Undo-TXT — 1.4.4."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Sequence


DEFAULT_BATCH_RENAME_TEMPLATE = "{stem}_{n}"

_PLACEHOLDER_RE = re.compile(r"\{(stem|n|ext|name)\}")
_UNDO_ARROW_RE = re.compile(r"^(.+?)\s+→\s+(.+)$")


@dataclass(frozen=True)
class RenamePreviewItem:
    """Eine Zeile der Umbenenn-Vorschau."""

    old_path: str
    new_name: str
    new_path: str
    skipped: bool = False
    reason: str = ""
    collision: bool = False  # Kollision in Liste oder Zieldatei — 1.4.1


@dataclass
class RenameUndoEntry:
    """Ein Eintrag im Undo-Log (alter → neuer Name)."""

    old_path: str
    new_path: str
    old_name: str = ""
    new_name: str = ""


@dataclass
class RenameUndoLog:
    """Undo-Log nach erfolgreichem Batch-Rename — 1.4.1/1.4.2 TXT."""

    created: str
    template: str
    entries: List[RenameUndoEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "schema": "ildrename-undo-v1",
            "version": 1,
            "created": self.created,
            "template": self.template,
            "entries": [asdict(e) for e in self.entries],
        }


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
    """Vorschau / Dry-Run-Liste für offene Tabs; Index ab start_index — 1.4.1."""
    items: List[RenamePreviewItem] = []
    seen_targets: set[str] = set()
    n = max(0, int(start_index))
    for raw in paths:
        p = Path(raw)
        if not raw:
            continue
        if not p.is_file() and not p.exists():
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
        collision = False
        key = new_path.casefold()
        if new_name == p.name:
            skipped = True
            reason = "unverändert"
        elif key in seen_targets:
            skipped = True
            reason = "Kollision in Liste"
            collision = True
        elif Path(new_path).exists() and Path(new_path).resolve() != (
            p.resolve() if p.exists() else Path(new_path)
        ):
            skipped = True
            reason = "Zieldatei existiert"
            collision = True
        else:
            seen_targets.add(key)
        items.append(
            RenamePreviewItem(
                old_path=str(p),
                new_name=new_name,
                new_path=new_path,
                skipped=skipped,
                reason=reason,
                collision=collision,
            )
        )
    return items


def count_collisions(items: Sequence[RenamePreviewItem]) -> int:
    """Anzahl Kollisionswarnungen in der Vorschau — 1.4.1."""
    return sum(1 for it in items if it.collision)


def format_dry_run_list(items: Sequence[RenamePreviewItem]) -> str:
    """Dry-Run-Liste als Klartext (alt → neu) — 1.4.1."""
    lines = ["# InstantLens Doc Batch-Rename Dry-Run", ""]
    for it in items:
        name = Path(it.old_path).name
        flag = f"  [{it.reason}]" if it.skipped else ""
        lines.append(f"{name}  →  {it.new_name}{flag}")
    ok_n = sum(1 for it in items if not it.skipped)
    col_n = count_collisions(items)
    lines.append("")
    lines.append(f"# {ok_n}/{len(items)} würden umbenannt; Kollisionen: {col_n}")
    return "\n".join(lines) + "\n"


def format_undo_log_txt(log: RenameUndoLog) -> str:
    """
    Undo-Log als TXT (schema ildrename-undo-v1).
    Zeilen: NEW → OLD (Rückgängig = neue Datei zurück zum alten Namen) — 1.4.2.
    """
    lines = [
        "# InstantLens Doc Batch-Rename Undo-Log",
        "# schema: ildrename-undo-v1",
        f"# created: {log.created}",
        f"# template: {log.template}",
        "# Format: NEW → OLD (Rückgängig letzte Batch)",
        "",
    ]
    for e in log.entries:
        lines.append(f"{e.new_path}  →  {e.old_path}")
    lines.append("")
    lines.append(f"# {len(log.entries)} Eintrag/Einträge")
    return "\n".join(lines) + "\n"


def write_undo_log(
    entries: Sequence[RenameUndoEntry],
    *,
    template: str,
    path: str | Path | None = None,
) -> Path:
    """
    Schreibt Undo-Log der alten Namen als TXT (ildrename-undo-v1) — 1.4.2.
    Default-Pfad: neben erster neuer Datei bzw. CWD, Endung .txt.
    """
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log = RenameUndoLog(created=created, template=template, entries=list(entries))
    if path is None:
        if entries:
            base = Path(entries[0].new_path).parent
        else:
            base = Path.cwd()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = base / f"ild-rename-undo-{stamp}.txt"
    out = Path(path)
    if out.suffix.lower() != ".txt":
        out = out.with_suffix(".txt")
    out.write_text(format_undo_log_txt(log), encoding="utf-8")
    return out


def read_undo_log(path: str | Path) -> RenameUndoLog:
    """
    Liest Undo-Log aus TXT (1.4.2) oder JSON (1.4.1 Kompatibilität).
    """
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    stripped = raw.lstrip()
    if stripped.startswith("{"):
        data = json.loads(raw)
        entries = [
            RenameUndoEntry(
                old_path=str(e.get("old_path") or ""),
                new_path=str(e.get("new_path") or ""),
                old_name=str(e.get("old_name") or ""),
                new_name=str(e.get("new_name") or ""),
            )
            for e in (data.get("entries") or [])
            if isinstance(e, dict)
        ]
        return RenameUndoLog(
            created=str(data.get("created") or ""),
            template=str(data.get("template") or ""),
            entries=entries,
        )
    created = ""
    template = ""
    entries: List[RenameUndoEntry] = []
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            low = s.lower()
            if low.startswith("# created:"):
                created = s.split(":", 1)[1].strip()
            elif low.startswith("# template:"):
                template = s.split(":", 1)[1].strip()
            continue
        m = _UNDO_ARROW_RE.match(s)
        if not m:
            continue
        new_path = m.group(1).strip()
        old_path = m.group(2).strip()
        entries.append(
            RenameUndoEntry(
                old_path=old_path,
                new_path=new_path,
                old_name=Path(old_path).name,
                new_name=Path(new_path).name,
            )
        )
    return RenameUndoLog(created=created, template=template, entries=entries)


def entry_still_has_new_name(entry: RenameUndoEntry) -> bool:
    """
    True wenn die Datei noch unter dem geloggten neuen Namen liegt — 1.4.3.
    """
    src = Path(entry.new_path)
    if not src.is_file():
        return False
    expected = (entry.new_name or src.name).strip() or src.name
    return src.name == expected


def eligible_undo_entries(log: RenameUndoLog) -> List[RenameUndoEntry]:
    """Einträge deren NEW-Datei noch dem neuen Namen entspricht — 1.4.3."""
    return [e for e in (log.entries or []) if entry_still_has_new_name(e)]


def count_skipped_undo_entries(log: RenameUndoLog) -> int:
    """Anzahl übersprungener Undo-Einträge (nicht mehr unter neuem Namen) — 1.4.4."""
    total = len(log.entries or [])
    return max(0, total - len(eligible_undo_entries(log)))


def is_undo_log_invalidated(path: str | Path) -> bool:
    """True wenn Undo-Log nach Rückgängig als ungültig markiert — 1.4.4."""
    p = Path(path)
    if not p.is_file():
        return True
    try:
        head = p.read_text(encoding="utf-8")[:4000]
    except Exception:
        return False
    for line in head.splitlines():
        s = line.strip().lower()
        if s.startswith("# invalidated"):
            return True
    return False


def invalidate_undo_log(path: str | Path) -> Path:
    """
    Markiert Undo-Log als ungültig (nach Rückgängig), damit es nicht erneut
    angewendet wird. Schreibt ``# INVALIDATED: …`` an den Anfang — 1.4.4.
    """
    p = Path(path)
    if not p.is_file():
        return p
    if is_undo_log_invalidated(p):
        return p
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        raw = p.read_text(encoding="utf-8")
    except Exception:
        raw = ""
    marker = (
        f"# INVALIDATED: {stamp}\n"
        "# Dieses Undo-Log wurde nach „Rückgängig letzte Batch“ ungültig.\n"
    )
    p.write_text(marker + raw, encoding="utf-8")
    return p


def apply_undo_log(
    log: RenameUndoLog,
    *,
    also_sidecars: bool = True,
    only_matching_new_name: bool = True,
) -> List[tuple[str, str, str | None]]:
    """
    Macht einen Batch-Rename rückgängig: NEW → OLD.
    Mit only_matching_new_name (Default): greift nur Dateien, die noch dem
    neuen Namen entsprechen — 1.4.2/1.4.3.
    Returns: Liste (from_new, to_old, error|None).
    """
    results: List[tuple[str, str, str | None]] = []
    sidecar_suffixes = (
        ".ildann.json",
        ".ildocr.txt",
        ".ildfav.json",
        ".ildbm.json",
    )
    entries = (
        eligible_undo_entries(log)
        if only_matching_new_name
        else list(log.entries or [])
    )
    # Umgekehrt der Umbenenn-Reihenfolge (weniger Kollisionen)
    for e in reversed(entries):
        src = Path(e.new_path)
        dst = Path(e.old_path)
        try:
            if only_matching_new_name and not entry_still_has_new_name(e):
                results.append(
                    (e.new_path, e.old_path, "nicht mehr unter neuem Namen")
                )
                continue
            if not src.exists():
                results.append((e.new_path, e.old_path, "Quelle (neu) fehlt"))
                continue
            if dst.exists() and dst.resolve() != src.resolve():
                results.append((e.new_path, e.old_path, "Ziel (alt) existiert"))
                continue
            src.rename(dst)
            if also_sidecars:
                for suf in sidecar_suffixes:
                    c = Path(str(src) + suf)
                    if c.is_file():
                        target = Path(str(dst) + suf)
                        if not target.exists():
                            c.rename(target)
            results.append((e.new_path, e.old_path, None))
        except Exception as ex:
            results.append((e.new_path, e.old_path, str(ex)))
    return results


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
