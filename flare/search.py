"""Treffer zusammenstellen: Präfix, Trigramm, Inhalt, Tippfehler, Rechnung."""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from flare.calc import try_calc
from flare.rank import Ranker
from flare.store import Index

_TOKEN = re.compile(r"\w+", re.UNICODE)
_FUZZY_MIN = 0.5


def phrase_query(text: str) -> str | None:
    folded = text.casefold().strip()
    if len(folded) < 3:
        return None
    return '"' + folded.replace('"', '""') + '"'


def fuzzy_query(text: str) -> str | None:
    parts = _TOKEN.findall(text.casefold())
    token = max(parts, key=len) if parts else text.casefold().strip()
    if len(token) < 4 or len(token) > 32:
        return None
    grams: list[str] = []
    seen: set[str] = set()
    for index in range(len(token) - 2):
        gram = token[index : index + 3]
        if gram not in seen:
            seen.add(gram)
            grams.append(gram)
    if len(grams) < 2:
        return None
    grams = grams[:12]
    return " OR ".join('"' + gram.replace('"', '""') + '"' for gram in grams)


def lexical_score(
    query: str,
    name: str,
    path: str,
    *,
    kind: str,
    tier: int,
    use_count: int,
    via: str,
) -> float:
    q = query.casefold().strip()
    folded = name.casefold()
    path_folded = path.casefold()
    if not q:
        base = 100.0
    elif folded == q:
        base = 1000.0
    elif folded.startswith(q):
        base = 860.0 - min(len(folded) - len(q), 80)
    elif any(token.startswith(q) for token in _TOKEN.findall(folded)):
        base = 740.0
    elif q in folded:
        base = 580.0 - min(folded.index(q), 80)
    elif q in path_folded:
        base = 320.0
    elif via == "content":
        base = 260.0
    else:
        return 0.0
    if kind == "app":
        base += 40.0
    elif kind == "dir":
        base += 10.0
    base += max(0, 3 - tier) * 12.0
    base += min(use_count, 30) * 6.0
    return base


def _fuzzy_surface(name: str) -> str:
    stem = Path(name).stem
    return stem if len(stem) >= 3 else name


def _detail(item: dict[str, Any]) -> str:
    if item["kind"] == "app":
        return "Programm"
    if item["kind"] == "dir":
        return "Ordner"
    return item.get("dir") or item["path"]


def _hit(item: dict[str, Any], via: str, score: float, snippet: str = "") -> dict[str, Any]:
    hit = {
        "id": item["id"],
        "kind": item["kind"],
        "name": item["name"],
        "path": item["path"],
        "detail": _detail(item),
        "via": via,
        "score": round(score, 1),
    }
    if snippet:
        hit["snippet"] = snippet
    return hit


def _snippet(text: str, query: str) -> str:
    folded = text.casefold()
    needle = query.casefold().strip()
    at = folded.find(needle) if needle else 0
    if at < 0:
        at = 0
    start = max(0, at - 28)
    clip = text[start : at + len(needle) + 48].replace("\n", " ").strip()
    if start > 0:
        clip = "…" + clip
    return clip


def search(index: Index, ranker: Ranker, query: str, limit: int = 8) -> dict[str, Any]:
    started = time.perf_counter()
    limit = max(1, min(int(limit), 50))
    text = query.strip()
    hits: dict[int, dict[str, Any]] = {}

    def consider(item: dict[str, Any], via: str, score: float, snippet: str = "") -> None:
        if score <= 0:
            return
        current = hits.get(item["id"])
        if current is None or score > current["score"]:
            hits[item["id"]] = _hit(item, via, score, snippet)

    if not text:
        for item in index.recent(limit):
            consider(item, "recent", 100.0 + min(item["use_count"], 30))
    else:
        for item in index.prefix(text.casefold(), 40):
            consider(
                item,
                "prefix",
                lexical_score(
                    text,
                    item["name"],
                    item["path"],
                    kind=item["kind"],
                    tier=item["tier"],
                    use_count=item["use_count"],
                    via="prefix",
                ),
            )
        phrase = phrase_query(text)
        if phrase:
            for item in index.fts(phrase, 40):
                consider(
                    item,
                    "trigram",
                    lexical_score(
                        text,
                        item["name"],
                        item["path"],
                        kind=item["kind"],
                        tier=item["tier"],
                        use_count=item["use_count"],
                        via="trigram",
                    ),
                )
            for item, body in index.content_hits(phrase, 20):
                consider(
                    item,
                    "content",
                    lexical_score(
                        text,
                        item["name"],
                        item["path"],
                        kind=item["kind"],
                        tier=item["tier"],
                        use_count=item["use_count"],
                        via="content",
                    ),
                    _snippet(body, text),
                )
        strong = [hit for hit in hits.values() if hit["score"] >= 240]
        fuzzy = fuzzy_query(text) if len(strong) < limit else None
        if fuzzy:
            candidates = index.fts(fuzzy, 80)
            pending = [item for item in candidates if item["id"] not in hits]
            if pending:
                scores = ranker.fuzzy_scores(text, [_fuzzy_surface(item["name"]) for item in pending])
                for item, cosine in zip(pending, scores):
                    if cosine < _FUZZY_MIN:
                        continue
                    bonus = lexical_score(
                        text,
                        item["name"],
                        item["path"],
                        kind=item["kind"],
                        tier=item["tier"],
                        use_count=item["use_count"],
                        via="fuzzy",
                    )
                    # lexical_score ist 0, wenn die Zeichenfolge nicht vorkommt.
                    base = 120.0 + cosine * 420.0 + max(bonus, 0.0) * 0.05
                    if item["kind"] == "app":
                        base += 20.0
                    consider(item, "fuzzy", base)

    ordered = sorted(hits.values(), key=lambda hit: (-hit["score"], hit["name"].casefold()))
    calc = try_calc(text) if text else None
    if calc is not None:
        ordered.insert(
            0,
            {
                "id": None,
                "kind": "calc",
                "name": calc,
                "path": "",
                "detail": "Berechnung",
                "via": "calc",
                "score": 2000,
                "value": calc,
            },
        )
    took_ms = (time.perf_counter() - started) * 1000.0
    return {
        "query": text,
        "backend": ranker.mode,
        "took_ms": round(took_ms, 2),
        "results": ordered[:limit],
    }
