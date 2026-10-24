"""Treffer zusammenstellen: Präfix, Trigramm, Inhalt, Tippfehler, Rechnung."""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from flare.calc import try_calc
from flare.rank import Ranker
from flare.store import Index, has_whole_word, open_index

_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
_FUZZY_MIN = 0.5
_SIMILAR_ALL = 3000
# FTS-LIMIT 80 verliert nahe Namen, sobald häufige Trigramme die Liste füllen.
_SIMILAR_CANDIDATES = 400
# Das Fenster soll eine Anfrage mit vielen Worttreffern zeigen, nicht nur eine Handvoll.
# 734 Namen wie IFATSEA müssen scrollbar sein, nicht bei 19 oder 200 enden.
PLAIN_UI_LIMIT = 1000
SIMILAR_UI_LIMIT = 1000
# Kurzes Token: ganzes Wort weit über einem Infix in einem langen Hash.
_SHORT_TOKEN = 4
_LONG_TOKEN = 12


def phrase_query(text: str) -> str | None:
    """FTS5-Phrase. Unter vier Zeichen leer: Trigramme scheitern darunter und bei genau drei."""
    folded = text.casefold().strip()
    if len(folded) < 4:
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


# Bänder liegen weiter auseinander als Art, Tier und Nutzung zusammen
# (höchstens 40 + 36 + 180). Ein Infix kann einen exakten Namen nicht überholen.
_EXACT = 5000.0
_PREFIX = 4000.0
_TOKEN_BAND = 3000.0
_SUBSTRING = 2000.0
# Weit unter dem Wortband, auch mit Art, Tier und Nutzung (höchstens etwa 256).
_BURIED = 80.0
_PATH = 900.0
_CONTENT = 500.0


def short_token(text: str) -> str | None:
    """Ein einzelnes Token aus 1 bis 4 Buchstaben oder Ziffern."""
    folded = text.casefold().strip()
    if not folded or len(folded) > _SHORT_TOKEN or not folded.isalnum():
        return None
    return folded


def buried_in_long_token(query: str, name: str) -> bool:
    """Die Anfrage steckt in einem langen Buchstaben-Ziffern-Token, nicht als eigenes Wort."""
    needle = query.casefold().strip()
    folded = name.casefold()
    if not needle or has_whole_word(needle, folded):
        return False
    start = 0
    while True:
        at = folded.find(needle, start)
        if at < 0:
            return False
        left = at
        while left > 0 and folded[left - 1].isalnum():
            left -= 1
        right = at + len(needle)
        while right < len(folded) and folded[right].isalnum():
            right += 1
        if right - left >= _LONG_TOKEN:
            return True
        start = at + 1
    return False


def drop_buried_hash_hits(query: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Gibt es ein ganzes Wort, bleiben Hash-Infixe draußen."""
    token = short_token(query)
    if token is None:
        return rows
    if not any(has_whole_word(token, str(hit.get("name") or "")) for hit in rows):
        return rows
    kept: list[dict[str, Any]] = []
    for hit in rows:
        if hit.get("kind") == "calc":
            kept.append(hit)
            continue
        name = str(hit.get("name") or "")
        if has_whole_word(token, name) or name.casefold().startswith(token):
            kept.append(hit)
            continue
        if buried_in_long_token(token, name):
            continue
        kept.append(hit)
    return kept


def has_exact_or_prefix(query: str, names: list[str]) -> bool:
    """True, wenn ein Name die Anfrage ist oder mit ihr beginnt."""
    q = query.casefold().strip()
    if not q:
        return False
    for name in names:
        folded = name.casefold()
        if folded == q or folded.startswith(q):
            return True
    return False


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
        base = _EXACT
    elif folded.startswith(q):
        base = _PREFIX - min(len(folded) - len(q), 80)
    elif any(token == q for token in _TOKEN.findall(folded)) or (
        len(q) > _SHORT_TOKEN and any(token.startswith(q) for token in _TOKEN.findall(folded))
    ):
        base = _TOKEN_BAND
    elif q in folded:
        if len(q) <= _SHORT_TOKEN and buried_in_long_token(q, folded):
            base = _BURIED
        else:
            base = _SUBSTRING - min(folded.index(q), 80)
    elif q in path_folded:
        base = _PATH
    elif via == "content":
        base = _CONTENT
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


def ui_result_limit(similar: bool) -> int:
    """Zeilen im Suchfenster. Mit und ohne Ähnlichkeit bis 1000."""
    return SIMILAR_UI_LIMIT if similar else PLAIN_UI_LIMIT


def _similar_pool(index: Index, text: str) -> list[dict[str, Any]]:
    """Kandidaten für „Ähnliche Namen“.

    Kleine Kataloge werden ganz bewertet. Große Kataloge nehmen den
    Trigramm-Index, nicht die ersten FTS-Zeilen: die verdrängen Johnston,
    sobald „son“ und „ohn“ das LIMIT füllen.
    """
    if index.counts()["items"] <= _SIMILAR_ALL:
        return index.all_items(_SIMILAR_ALL)
    ranked = index.similar_candidates(text, _SIMILAR_CANDIDATES)
    if ranked:
        return ranked
    fuzzy = fuzzy_query(text)
    if not fuzzy:
        return []
    return index.fts(fuzzy, _SIMILAR_CANDIDATES)


def merge_similar(lexical: list[dict[str, Any]], near: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    """Lexikalische Treffer und nahe Namen teilen sich das Limit.

    Solange beide zusammen in das Limit passen, bleibt jeder nahe Name eine
    eigene Zeile. Die Hälfte ist nur die Balance, wenn beide Seiten überlaufen,
    nicht eine kleinere Deckelung für die Ähnlichkeit.
    """
    limit = max(1, min(int(limit), SIMILAR_UI_LIMIT))
    if not near:
        return list(lexical[:limit])
    seen: set[Any] = set()
    merged: list[dict[str, Any]] = []

    def add(hit: dict[str, Any]) -> bool:
        if len(merged) >= limit:
            return False
        ident = hit.get("id")
        if ident is not None and ident in seen:
            return True
        if ident is not None:
            seen.add(ident)
        merged.append(hit)
        return True

    if len(lexical) + len(near) <= limit:
        for hit in lexical:
            add(hit)
        for hit in near:
            add(hit)
        return merged
    lex_keep = min(len(lexical), max(1, limit // 2))
    for hit in lexical[:lex_keep]:
        add(hit)
    for hit in near:
        if not add(hit):
            return merged
    for hit in lexical[lex_keep:]:
        if not add(hit):
            return merged
    return merged


def _detail(item: dict[str, Any]) -> str:
    if item["kind"] == "app":
        return "Programm"
    if item["kind"] == "dir":
        return "Ordner"
    return item.get("dir") or item["path"]


def _hit(
    item: dict[str, Any],
    via: str,
    score: float,
    snippet: str = "",
    similarity: float | None = None,
) -> dict[str, Any]:
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
    if similarity is not None:
        hit["similarity"] = round(similarity, 2)
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


def search_index_file(
    path: str | Path,
    query: str,
    limit: int = 8,
    similar: bool = False,
) -> dict[str, Any]:
    """Einen eigenen Index lesen, ohne den laufenden Katalog zu öffnen."""
    index = open_index(path, readonly=True)
    ranker = Ranker()
    try:
        return search(index, ranker, query, limit, similar)
    finally:
        ranker.close()
        index.close()


def search(
    index: Index,
    ranker: Ranker,
    query: str,
    limit: int = 8,
    similar: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    limit = max(1, min(int(limit), SIMILAR_UI_LIMIT))
    text = query.strip()
    hits: dict[int, dict[str, Any]] = {}

    def consider(
        item: dict[str, Any],
        via: str,
        score: float,
        snippet: str = "",
        similarity: float | None = None,
    ) -> None:
        if score <= 0:
            return
        current = hits.get(item["id"])
        if current is None or score > current["score"]:
            hits[item["id"]] = _hit(item, via, score, snippet, similarity)

    if not text:
        for item in index.recent(limit):
            consider(item, "recent", 100.0 + min(item["use_count"], 30))
    else:
        folded_query = text.casefold()
        # LIKE auf dem Namen, nicht eine FTS5-Trigramm-Phrase. Kurze und
        # längere Wörter holen das Fensterlimit, sonst bleibt es bei einer
        # Handvoll Präfixen (19, 40, 64), obwohl hunderte Ordner den Namen tragen.
        fetch = max(limit, PLAIN_UI_LIMIT)
        # Exakte Namen zuerst und ohne ein kleineres Präfix-Limit, sonst verdrängen
        # häufig genutzte längere Namen den Ordner aus der Kandidatenliste.
        for item in index.exact(folded_query, fetch):
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
        for item in index.prefix(folded_query, fetch):
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
        # Teilstring irgendwo im Namen, nicht nur am Anfang. LIKE, nicht die
        # Trigramm-Phrase: die liefert bei drei Zeichen oft nichts.
        if len(folded_query) >= 3:
            for item in index.contains(folded_query, fetch):
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
        phrase = phrase_query(text)
        if phrase:
            for item in index.fts(phrase, fetch):
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
        short = short_token(text)
        word_hit = bool(short) and any(has_whole_word(short, str(hit["name"])) for hit in hits.values())
        if word_hit and short:
            for item_id, hit in list(hits.items()):
                name = str(hit["name"])
                if has_whole_word(short, name) or name.casefold().startswith(short):
                    continue
                if buried_in_long_token(short, name):
                    del hits[item_id]
        strong = [hit for hit in hits.values() if hit["score"] >= 240]
        # Exakter Name, Präfix oder ganzes Wort: keine unscharfen Verwandten nachziehen.
        # „Ähnliche Namen“ bleibt ein eigener Modus und läuft darüber.
        named = has_exact_or_prefix(text, [hit["name"] for hit in hits.values()]) or word_hit
        if similar:
            pending = [item for item in _similar_pool(index, text) if item["id"] not in hits]
            if pending:
                scores = ranker.similarity_scores(text, [_fuzzy_surface(item["name"]) for item in pending])
                for item, cosine in zip(pending, scores):
                    if cosine < _FUZZY_MIN:
                        continue
                    if word_hit and short and buried_in_long_token(short, str(item["name"])):
                        continue
                    base = 120.0 + cosine * 420.0
                    if item["kind"] == "app":
                        base += 20.0
                    consider(item, "similar", base, similarity=cosine)
        elif not named and len(strong) < limit:
            fuzzy = fuzzy_query(text)
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
                        base = 120.0 + cosine * 420.0 + max(bonus, 0.0) * 0.05
                        if item["kind"] == "app":
                            base += 20.0
                        consider(item, "fuzzy", base)

    ordered = sorted(hits.values(), key=lambda hit: (-hit["score"], hit["name"].casefold()))
    ordered = drop_buried_hash_hits(text, ordered)
    if similar and text:
        lexical = [hit for hit in ordered if hit["via"] != "similar"]
        near = [hit for hit in ordered if hit["via"] == "similar"]
        if near:
            ordered = merge_similar(lexical, near, limit)
        ordered = drop_buried_hash_hits(text, ordered)
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
        "similar": bool(similar and text),
        "results": ordered[:limit],
    }
