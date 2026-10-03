"""Annotation-Volltextsuche über Sidecar-Notizen/Highlights geöffneter Docs — 1.4.1."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence


@dataclass(frozen=True)
class AnnSearchHit:
    """Ein Treffer in Sidecar-Annotationen."""

    path: str
    page: int  # 0-based
    ann_type: str
    text: str
    tags: str
    snippet: str
    ann_id: str = ""


def _sidecar_for_pdf(pdf_path: Path) -> Path:
    return pdf_path.with_suffix(pdf_path.suffix + ".ildann.json")


def _match_blob(
    blob: str,
    query: str,
    *,
    case_sensitive: bool,
    use_regex: bool,
) -> bool:
    if use_regex:
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            return re.search(query, blob, flags) is not None
        except re.error:
            return False
    if case_sensitive:
        return query in blob
    return query.casefold() in blob.casefold()


def _make_snippet(
    text: str,
    tags_s: str,
    typ: str,
    query: str,
    *,
    case_sensitive: bool,
    use_regex: bool,
) -> str:
    """Snippet um den Match herum."""
    candidates = [text, tags_s, typ]
    src = text or tags_s or typ
    for cand in candidates:
        if cand and _match_blob(
            cand, query, case_sensitive=case_sensitive, use_regex=use_regex
        ):
            src = cand
            break
    snip = src.replace("\n", " ").strip()
    if len(snip) <= 100:
        return snip or query
    # Fenster um Match
    pos = -1
    if use_regex:
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            m = re.search(query, snip, flags)
            if m:
                pos = m.start()
        except re.error:
            pos = -1
    else:
        hay = snip if case_sensitive else snip.casefold()
        needle = query if case_sensitive else query.casefold()
        pos = hay.find(needle)
    if pos >= 0:
        start = max(0, pos - 30)
        snip = ("…" if start else "") + snip[start : start + 90]
        if start + 90 < len(src):
            snip += "…"
    else:
        snip = snip[:97] + "…"
    return snip


def search_annotations_in_paths(
    paths: Sequence[str],
    query: str,
    *,
    max_hits: int = 300,
    case_sensitive: bool = False,
    use_regex: bool = False,
) -> List[AnnSearchHit]:
    """
    Volltext über *.ildann.json Sidecars (Notizen, Highlights, Tags, Typ)
    quer durch die gelisteten Dokumente (typisch: offene Tabs).
    case_sensitive / use_regex — 1.4.1.
    """
    q = (query or "").strip()
    if not q:
        return []
    if use_regex:
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            re.compile(q, flags)
        except re.error:
            return []  # ungültiges Regex → keine Treffer (UI zeigt Hinweis)
    hits: List[AnnSearchHit] = []
    seen_pdf: set[str] = set()

    for raw in paths:
        p = Path(raw)
        if not p.is_file():
            continue
        # PDF oder direkt Sidecar
        if p.suffix.lower() == ".json" and p.name.endswith(".ildann.json"):
            pdf = Path(str(p)[: -len(".ildann.json")])
            sidecar = p
        elif p.suffix.lower() == ".pdf":
            pdf = p
            sidecar = _sidecar_for_pdf(p)
        else:
            continue
        key = str(pdf.resolve()) if pdf.exists() else str(pdf)
        if key in seen_pdf:
            continue
        seen_pdf.add(key)
        if not sidecar.is_file():
            continue
        try:
            from ild_pdf.annotate import AnnotationStore

            if not pdf.exists():
                continue
            store = AnnotationStore(pdf)
            anns = list(store.annotations or [])
        except Exception:
            continue

        for a in anns:
            text = str(getattr(a, "text", "") or "")
            tags = getattr(a, "tags", None) or []
            tags_s = ", ".join(str(t) for t in tags)
            typ = getattr(getattr(a, "type", None), "value", None) or str(
                getattr(a, "type", "") or ""
            )
            blob = f"{text}\n{tags_s}\n{typ}"
            if not _match_blob(
                blob, q, case_sensitive=case_sensitive, use_regex=use_regex
            ):
                continue
            snip = _make_snippet(
                text,
                tags_s,
                typ,
                q,
                case_sensitive=case_sensitive,
                use_regex=use_regex,
            )
            hits.append(
                AnnSearchHit(
                    path=str(pdf),
                    page=int(getattr(a, "page", 0) or 0),
                    ann_type=str(typ),
                    text=text,
                    tags=tags_s,
                    snippet=snip or q,
                    ann_id=str(getattr(a, "id", "") or ""),
                )
            )
            if len(hits) >= max_hits:
                return hits
    return hits
