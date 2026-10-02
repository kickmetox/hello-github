"""Einfache Rechtschreibprüfung über lokale Wortliste (ohne externe Spell-Lib)."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Iterable

# Wort-Token: Buchstaben inkl. Umlaute; Bindestrich innerhalb erlaubt
_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿĀ-ž]+(?:'[A-Za-zÀ-ÖØ-öø-ÿĀ-ž]+)?", re.UNICODE)


def normalize_word(word: str) -> str:
    """Vergleichsschlüssel: lower, Soft-Hyphen entfernen."""
    return (word or "").replace("\u00ad", "").casefold().strip()


def load_wordlist(path: str | Path) -> set[str]:
    """
    Wortliste laden: eine Zeile = ein Wort; # und ; Kommentare; leer ignorieren.
    Rückgabe: normalisierte Wörter (casefold).
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Wörterbuch nicht gefunden: {p}")
    words: set[str] = set()
    text = p.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or raw.startswith(";"):
            continue
        # optional: mehrere Wörter pro Zeile (Whitespace)
        for part in re.split(r"[\s,]+", raw):
            key = normalize_word(part)
            if key and len(key) >= 1:
                words.add(key)
    return words


@lru_cache(maxsize=8)
def _cached_wordlist(path_str: str, mtime_ns: int) -> frozenset[str]:
    return frozenset(load_wordlist(path_str))


def get_wordlist(path: str | Path | None) -> set[str]:
    """Wortliste für Pfad (Cache anhand mtime); leerer Pfad → leeres Set."""
    if not path:
        return set()
    p = Path(path)
    if not p.is_file():
        return set()
    try:
        mtime = p.stat().st_mtime_ns
    except OSError:
        return set()
    return set(_cached_wordlist(str(p.resolve()), mtime))


def clear_wordlist_cache() -> None:
    _cached_wordlist.cache_clear()


def iter_word_spans(text: str) -> Iterable[tuple[int, int, str]]:
    """(start, end, word) für jedes Wort-Token im Text."""
    for m in _WORD_RE.finditer(text or ""):
        yield m.start(), m.end(), m.group(0)


def find_unknown_spans(
    text: str,
    wordlist: set[str] | frozenset[str],
    *,
    min_len: int = 2,
) -> list[tuple[int, int, str]]:
    """
    Unbekannte Wörter als (start, end, word).
    Ohne Wortliste → leere Liste (keine Prüfung).
    Zahlen/einzelne Buchstaben unter min_len werden übersprungen.
    """
    if not wordlist:
        return []
    unknown: list[tuple[int, int, str]] = []
    for start, end, word in iter_word_spans(text):
        if len(word) < min_len:
            continue
        if word.isdigit():
            continue
        key = normalize_word(word)
        if not key:
            continue
        if key not in wordlist:
            unknown.append((start, end, word))
    return unknown


def spellcheck_text(
    text: str,
    dict_path: str | Path | None,
    *,
    min_len: int = 2,
) -> list[tuple[int, int, str]]:
    """Convenience: Wortliste laden + unbekannte Spans."""
    return find_unknown_spans(text, get_wordlist(dict_path), min_len=min_len)
