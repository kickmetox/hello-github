"""TF-IDF-Index mit Kosinusähnlichkeit.

Grundlage ist das Suchprinzip aus einem Mini-Search-Engine:
Dokumente werden vor der Abfrage in Termgewichte zerlegt
(Termhäufigkeit mal inverse Dokumenthäufigkeit) und die Anfrage
wird über das Skalarprodukt der normalisierten Vektoren gerankt.
"""

from __future__ import annotations

import math
import re
import threading
from collections import Counter


TOKEN = re.compile(r"[0-9A-Za-zÄÖÜäöüß]{2,}")

STOPWORDS = {
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einer", "einem", "einen",
    "und", "oder", "aber", "nicht", "nur", "auch", "wie", "als", "von", "vom", "für",
    "mit", "auf", "aus", "bei", "nach", "über", "unter", "vor", "zum", "zur", "im",
    "in", "an", "am", "zu", "ist", "sind", "war", "sein", "hat", "haben", "wird",
    "werden", "kann", "dass", "daß", "dies", "diese", "dieser", "dieses", "sich",
    "es", "er", "sie", "ich", "wir", "ihr", "man", "so", "noch", "schon", "wenn",
    "dann", "durch", "ohne", "bis", "mehr", "the", "and", "or", "of", "to", "in",
    "is", "for", "on", "with", "as", "by", "at", "from", "that", "this", "it", "be",
    "are", "was", "an", "a",
}


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN.finditer(text or "") if match.group(0).lower() not in STOPWORDS]


class TfidfIndex:
    def __init__(self) -> None:
        self._vectors: dict[int, dict[str, float]] = {}
        self._norms: dict[int, float] = {}
        self._idf: dict[str, float] = {}

    def rebuild(self, documents: list[tuple[int, str]]) -> None:
        tokenized: dict[int, list[str]] = {}
        document_frequency: Counter[str] = Counter()
        for doc_id, text in documents:
            tokens = tokenize(text)
            tokenized[doc_id] = tokens
            document_frequency.update(set(tokens))
        count = len(tokenized)
        self._idf = {
            term: math.log((1 + count) / (1 + freq)) + 1.0
            for term, freq in document_frequency.items()
        }
        self._vectors = {}
        self._norms = {}
        for doc_id, tokens in tokenized.items():
            if not tokens:
                self._vectors[doc_id] = {}
                self._norms[doc_id] = 0.0
                continue
            counts = Counter(tokens)
            length = float(len(tokens))
            vector = {
                term: (freq / length) * self._idf[term]
                for term, freq in counts.items()
            }
            self._vectors[doc_id] = vector
            self._norms[doc_id] = math.sqrt(sum(value * value for value in vector.values()))

    def search(self, query: str, top_k: int = 20) -> list[tuple[int, float]]:
        tokens = tokenize(query)
        if not tokens or not self._vectors:
            return []
        counts = Counter(tokens)
        length = float(len(tokens))
        query_vector = {
            term: (freq / length) * self._idf[term]
            for term, freq in counts.items()
            if term in self._idf
        }
        query_norm = math.sqrt(sum(value * value for value in query_vector.values()))
        if query_norm == 0.0:
            return []
        ranked: list[tuple[int, float]] = []
        for doc_id, vector in self._vectors.items():
            doc_norm = self._norms[doc_id]
            if doc_norm == 0.0:
                continue
            dot = sum(query_vector[term] * vector[term] for term in query_vector if term in vector)
            if dot <= 0.0:
                continue
            ranked.append((doc_id, dot / (query_norm * doc_norm)))
        ranked.sort(key=lambda item: (-item[1], item[0]))
        return ranked[:top_k]


INDEX = TfidfIndex()
INDEX_LOCK = threading.Lock()


def snippet(text: str, query: str, radius: int = 110) -> str:
    source = (text or "").strip()
    if not source:
        return ""
    lowered = source.lower()
    position = -1
    for term in tokenize(query):
        found = lowered.find(term)
        if found >= 0:
            position = found
            break
    if position < 0:
        cut = source[: radius * 2].strip()
        return cut + ("…" if len(source) > radius * 2 else "")
    start = max(0, position - radius)
    end = min(len(source), position + radius)
    chunk = source[start:end].strip()
    if start > 0:
        chunk = "…" + chunk
    if end < len(source):
        chunk = chunk + "…"
    return chunk
