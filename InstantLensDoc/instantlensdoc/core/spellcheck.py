"""Rechtschreibprüfung mit Vorschlägen + leichten Grammatik-Hinweisen — 2.6.22.

Lokale Wortlisten (ohne externe Spell-Lib). UI-Sprache steuert eingebaute
Minimal-Wörterbücher und Autokorrektur-Defaults wo möglich.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Iterable

# Wort-Token: Buchstaben inkl. Umlaute; Bindestrich innerhalb erlaubt
_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿĀ-ž]+(?:'[A-Za-zÀ-ÖØ-öø-ÿĀ-ž]+)?", re.UNICODE)

# Eingebaute Minimal-Wortlisten je UI-Sprache (Erweiterung über Settings-Pfad)
_BUILTIN: dict[str, frozenset[str]] = {
    "de": frozenset(
        {
            "hallo", "welt", "und", "oder", "der", "die", "das", "ein", "eine",
            "mit", "freundlichen", "grüßen", "sehr", "geehrte", "damen", "herren",
            "bitte", "danke", "dokument", "seite", "text", "prüfung", "rechtschreibung",
            "automatisch", "korrektur", "baustein", "vorschau", "speichern", "öffnen",
            "rückgängig", "wiederholen", "suche", "ersetzen", "format", "absatz",
            "überschrift", "liste", "tabelle", "bild", "export", "import", "hilfe",
            "einstellungen", "sprache", "deutsch", "englisch", "heute", "morgen",
            "gestern", "uhr", "datum", "name", "adresse", "firma", "rechnung",
            "vertrag", "anschreiben", "formular", "anfrage", "antwort", "betreff",
        }
    ),
    "en": frozenset(
        {
            "hello", "world", "and", "or", "the", "a", "an", "with", "kind",
            "regards", "dear", "sir", "madam", "please", "thank", "thanks",
            "document", "page", "text", "spell", "check", "spelling", "grammar",
            "suggestion", "autocorrect", "snippet", "preview", "save", "open",
            "undo", "redo", "search", "replace", "format", "paragraph",
            "heading", "list", "table", "image", "export", "import", "help",
            "settings", "language", "english", "german", "today", "tomorrow",
            "yesterday", "date", "name", "address", "company", "invoice",
            "contract", "letter", "form", "request", "reply", "subject",
        }
    ),
    "fr": frozenset(
        {
            "bonjour", "monde", "et", "ou", "le", "la", "les", "un", "une",
            "avec", "merci", "document", "page", "texte", "orthographe",
            "correction", "enregistrement", "ouvrir", "annuler", "rétablir",
            "recherche", "remplacer", "format", "paragraphe", "liste", "tableau",
            "image", "aide", "paramètres", "langue", "français", "aujourd",
        }
    ),
    "es": frozenset(
        {
            "hola", "mundo", "y", "o", "el", "la", "los", "las", "un", "una",
            "con", "gracias", "documento", "página", "texto", "ortografía",
            "corrección", "guardar", "abrir", "deshacer", "rehacer", "buscar",
            "reemplazar", "formato", "párrafo", "lista", "tabla", "imagen",
            "ayuda", "ajustes", "idioma", "español", "hoy",
        }
    ),
    "it": frozenset(
        {
            "ciao", "mondo", "e", "o", "il", "la", "lo", "gli", "un", "una",
            "con", "grazie", "documento", "pagina", "testo", "ortografia",
            "correzione", "salva", "apri", "annulla", "ripeti", "cerca",
            "sostituisci", "formato", "paragrafo", "elenco", "tabella", "immagine",
            "aiuto", "impostazioni", "lingua", "italiano", "oggi",
        }
    ),
    "pt": frozenset(
        {
            "olá", "mundo", "e", "ou", "o", "a", "os", "as", "um", "uma",
            "com", "obrigado", "documento", "página", "texto", "ortografia",
            "correção", "guardar", "abrir", "desfazer", "refazer", "pesquisar",
            "substituir", "formato", "parágrafo", "lista", "tabela", "imagem",
            "ajuda", "definições", "idioma", "português", "hoje",
        }
    ),
    "ru": frozenset(
        {
            "привет", "мир", "и", "или", "документ", "страница", "текст",
            "проверка", "орфография", "исправление", "сохранить", "открыть",
            "отменить", "повторить", "поиск", "замена", "формат", "абзац",
            "список", "таблица", "изображение", "помощь", "настройки", "язык",
            "сегодня", "спасибо",
        }
    ),
    "zh": frozenset(),  # CJK: Wortlisten-Prüfung wenig sinnvoll ohne Segmentierer
    "ar": frozenset(
        {
            "مرحبا", "العالم", "و", "أو", "مستند", "صفحة", "نص", "تدقيق",
            "إملائي", "حفظ", "فتح", "تراجع", "إعادة", "بحث", "استبدال",
            "تنسيق", "فقرة", "قائمة", "جدول", "صورة", "مساعدة", "إعدادات",
            "لغة", "اليوم", "شكرا",
        }
    ),
}


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


def builtin_wordlist(lang: str | None = None) -> set[str]:
    """Eingebaute Minimal-Wortliste für UI-Sprache (Fallback: de)."""
    code = (lang or "de").split("-")[0].lower()
    if code not in _BUILTIN:
        code = "de"
    return set(_BUILTIN.get(code, frozenset()))


def resolve_wordlist(
    dict_path: str | Path | None = None,
    *,
    lang: str | None = None,
    include_builtin: bool = True,
) -> set[str]:
    """Benutzer-Wortliste ∪ eingebautes Wörterbuch der UI-Sprache."""
    words = get_wordlist(dict_path) if dict_path else set()
    if include_builtin:
        words |= builtin_wordlist(lang)
    return words


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


def _edit_distance(a: str, b: str, *, max_dist: int = 2) -> int:
    """Levenshtein mit Early-Exit bei > max_dist."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if abs(la - lb) > max_dist:
        return max_dist + 1
    if la > lb:
        a, b = b, a
        la, lb = lb, la
    prev = list(range(la + 1))
    for j, cb in enumerate(b, 1):
        cur = [j]
        row_min = j
        for i, ca in enumerate(a, 1):
            cost = 0 if ca == cb else 1
            v = min(prev[i] + 1, cur[i - 1] + 1, prev[i - 1] + cost)
            cur.append(v)
            if v < row_min:
                row_min = v
        if row_min > max_dist:
            return max_dist + 1
        prev = cur
    return prev[-1]


def suggest_corrections(
    word: str,
    wordlist: set[str] | frozenset[str],
    *,
    max_suggestions: int = 5,
    max_dist: int = 2,
) -> list[str]:
    """Korrekturvorschläge per Edit-Distanz (+ einfache Transposition)."""
    key = normalize_word(word)
    if not key or not wordlist:
        return []
    if key in wordlist:
        return []
    scored: list[tuple[int, str]] = []
    # Prefix-/Suffix-Kandidaten beschleunigen
    prefix = key[:2] if len(key) >= 2 else key[:1]
    candidates = [w for w in wordlist if abs(len(w) - len(key)) <= max_dist]
    if len(candidates) > 4000:
        candidates = [w for w in candidates if w.startswith(prefix) or w[:1] == key[:1]]
    for cand in candidates:
        d = _edit_distance(key, cand, max_dist=max_dist)
        if d <= max_dist:
            scored.append((d, cand))
    scored.sort(key=lambda t: (t[0], t[1]))
    out: list[str] = []
    seen: set[str] = set()
    for _d, cand in scored:
        if cand in seen:
            continue
        seen.add(cand)
        # Großschreibung der Vorlage übernehmen
        if word[:1].isupper() and cand:
            shaped = cand[:1].upper() + cand[1:]
        else:
            shaped = cand
        out.append(shaped)
        if len(out) >= max_suggestions:
            break
    return out


def grammar_hints(text: str, *, lang: str | None = None) -> list[dict]:
    """
    Leichte Grammatik-/Typografie-Hinweise (heuristisch, keine volle Grammar-Engine).

    Typen: double_space, repeated_word, missing_space_after_punct, lowercase_sentence
    """
    hints: list[dict] = []
    raw = text or ""
    if not raw:
        return hints
    # Doppelte Leerzeichen
    for m in re.finditer(r" {2,}", raw):
        hints.append(
            {
                "type": "double_space",
                "start": m.start(),
                "end": m.end(),
                "message": "Doppeltes Leerzeichen",
                "suggestion": " ",
            }
        )
    # Wiederholte Wörter
    for m in re.finditer(
        r"\b([A-Za-zÀ-ÖØ-öø-ÿĀ-ž]{2,})\s+\1\b", raw, flags=re.IGNORECASE
    ):
        hints.append(
            {
                "type": "repeated_word",
                "start": m.start(),
                "end": m.end(),
                "message": "Wiederholtes Wort",
                "suggestion": m.group(1),
                "word": m.group(1),
            }
        )
    # Fehlendes Leerzeichen nach .!? (außer Abkürzungen/Zahlen)
    for m in re.finditer(r"([.!?])([A-Za-zÀ-ÖØ-öø-ÿ])", raw):
        hints.append(
            {
                "type": "missing_space_after_punct",
                "start": m.start(),
                "end": m.end(),
                "message": "Leerzeichen nach Satzzeichen fehlt",
                "suggestion": f"{m.group(1)} {m.group(2)}",
            }
        )
    # Satzanfang kleingeschrieben (nach .!? + Leerzeichen)
    for m in re.finditer(r"(^|[.!?]\s+)([a-zà-öø-ÿ])", raw):
        # Skip wenn UI-Sprache CJK
        code = (lang or "de").split("-")[0].lower()
        if code in ("zh",):
            continue
        start = m.start(2)
        hints.append(
            {
                "type": "lowercase_sentence",
                "start": start,
                "end": start + 1,
                "message": "Satzanfang kleingeschrieben",
                "suggestion": m.group(2).upper(),
            }
        )
    return hints


def spellcheck_text(
    text: str,
    dict_path: str | Path | None,
    *,
    min_len: int = 2,
    lang: str | None = None,
    include_builtin: bool = True,
) -> list[tuple[int, int, str]]:
    """Convenience: Wortliste laden + unbekannte Spans (inkl. Builtin der UI-Sprache)."""
    if lang is None:
        try:
            from instantlensdoc.core.i18n import get_lang

            lang = get_lang()
        except Exception:
            lang = "de"
    words = resolve_wordlist(dict_path, lang=lang, include_builtin=include_builtin)
    # Ohne User-Dict und ohne Builtin → nichts prüfen
    if not words:
        return []
    return find_unknown_spans(text, words, min_len=min_len)


def spellcheck_with_suggestions(
    text: str,
    dict_path: str | Path | None = None,
    *,
    lang: str | None = None,
    include_builtin: bool = True,
    max_suggestions: int = 5,
    include_grammar: bool = True,
) -> dict:
    """
    Vollständige Prüfung: unbekannte Wörter + Vorschläge + optionale Grammar-Hints.

    Rückgabe::
        {
          "lang": "de",
          "unknown": [{"start", "end", "word", "suggestions"}, ...],
          "grammar": [...],
          "count": N,
        }
    """
    if lang is None:
        try:
            from instantlensdoc.core.i18n import get_lang

            lang = get_lang()
        except Exception:
            lang = "de"
    words = resolve_wordlist(dict_path, lang=lang, include_builtin=include_builtin)
    unknown_spans = find_unknown_spans(text, words) if words else []
    unknown = []
    for start, end, word in unknown_spans:
        unknown.append(
            {
                "start": start,
                "end": end,
                "word": word,
                "suggestions": suggest_corrections(
                    word, words, max_suggestions=max_suggestions
                ),
            }
        )
    grammar = grammar_hints(text, lang=lang) if include_grammar else []
    return {
        "lang": lang,
        "unknown": unknown,
        "grammar": grammar,
        "count": len(unknown),
        "grammar_count": len(grammar),
    }
