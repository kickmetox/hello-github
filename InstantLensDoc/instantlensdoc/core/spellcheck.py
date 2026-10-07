"""Rechtschreibprüfung mit Vorschlägen + leichten Grammatik-Hinweisen — 2.6.26.
Grammatik DE/EN — 2.6.28.

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


def _grammar_issue(
    *,
    type: str,
    start: int,
    end: int,
    message: str,
    suggestion: str | None = None,
    severity: str = "hint",
    lang: str = "",
    **extra: object,
) -> dict:
    d: dict = {
        "type": type,
        "start": start,
        "end": end,
        "message": message,
        "severity": severity,
    }
    if suggestion is not None:
        d["suggestion"] = suggestion
    if lang:
        d["lang"] = lang
    for k, v in extra.items():
        if v is not None:
            d[k] = v
    return d


def _grammar_base_hints(text: str, *, lang: str | None = None) -> list[dict]:
    """Basis-Typografie (rückwärtskompatibel)."""
    hints: list[dict] = []
    raw = text or ""
    if not raw:
        return hints
    code = (lang or "de").split("-")[0].lower()
    for m in re.finditer(r" {2,}", raw):
        hints.append(
            _grammar_issue(
                type="double_space",
                start=m.start(),
                end=m.end(),
                message="Doppeltes Leerzeichen",
                suggestion=" ",
                lang=code,
            )
        )
    for m in re.finditer(
        r"\b([A-Za-zÀ-ÖØ-öø-ÿĀ-ž]{2,})\s+\1\b", raw, flags=re.IGNORECASE
    ):
        hints.append(
            _grammar_issue(
                type="repeated_word",
                start=m.start(),
                end=m.end(),
                message="Wiederholtes Wort",
                suggestion=m.group(1),
                word=m.group(1),
                lang=code,
            )
        )
    for m in re.finditer(r"([.!?])([A-Za-zÀ-ÖØ-öø-ÿ])", raw):
        hints.append(
            _grammar_issue(
                type="missing_space_after_punct",
                start=m.start(),
                end=m.end(),
                message="Leerzeichen nach Satzzeichen fehlt",
                suggestion=f"{m.group(1)} {m.group(2)}",
                lang=code,
            )
        )
    if code not in ("zh",):
        for m in re.finditer(r"(^|[.!?]\s+)([a-zà-öø-ÿ])", raw):
            start = m.start(2)
            hints.append(
                _grammar_issue(
                    type="lowercase_sentence",
                    start=start,
                    end=start + 1,
                    message="Satzanfang kleingeschrieben",
                    suggestion=m.group(2).upper(),
                    lang=code,
                )
            )
    return hints


_DE_ARTICLES = ("der", "die", "das", "ein", "eine", "einem", "einer", "eines", "den", "dem")
_EN_VOWEL_SOUND = re.compile(r"^[aeiouAEIOU]")
_EN_CONSONANT_U = re.compile(r"^(?:uni|eu|use|user|one)\b", re.I)


def _grammar_de(text: str) -> list[dict]:
    """Deutsche Heuristiken: das/dass, seit/seid, tod/tot, Komma, Einheiten, …"""
    hints: list[dict] = []
    raw = text or ""
    if not raw:
        return hints

    # das/dass vor Nebensatz-Verben (sehr grob: "das … [verb]t/en" → oft "dass")
    for m in re.finditer(
        r"\bdas\s+(?=(?:ich|du|er|sie|es|wir|ihr|man)\b)",
        raw,
        flags=re.IGNORECASE,
    ):
        hints.append(
            _grammar_issue(
                type="de_das_dass",
                start=m.start(),
                end=m.start() + 3,
                message='Möglicherweise „dass“ statt „das“ (Nebensatz)',
                suggestion="dass",
                severity="warning",
                lang="de",
            )
        )

    # seit/seid
    for m in re.finditer(r"\bseid\s+(?:dem|wann|Jahren?|Tagen?|Monaten?)\b", raw, re.I):
        hints.append(
            _grammar_issue(
                type="de_seit_seid",
                start=m.start(),
                end=m.start() + 4,
                message='Zeitangabe: „seit“ statt „seid“',
                suggestion="seit",
                severity="warning",
                lang="de",
            )
        )
    for m in re.finditer(r"\bseit\s+(?:ihr|Ihr)\b", raw):
        hints.append(
            _grammar_issue(
                type="de_seit_seid",
                start=m.start(),
                end=m.start() + 4,
                message='Verbform: „seid“ statt „seit“',
                suggestion="seid",
                severity="warning",
                lang="de",
            )
        )

    # tod/tot
    for m in re.finditer(r"\btod\b", raw):
        # Nomen „Tod“ groß; kleines „tod“ oft Fehler für „tot“
        if m.group(0) == "tod":
            hints.append(
                _grammar_issue(
                    type="de_tod_tot",
                    start=m.start(),
                    end=m.end(),
                    message='Adjektiv „tot“ oder Nomen „Tod“? (kleines „tod“ unüblich)',
                    suggestion="tot",
                    severity="hint",
                    lang="de",
                )
            )

    # Artikel + kleingeschriebenes Nomen (heuristisch)
    for m in re.finditer(
        r"\b(" + "|".join(_DE_ARTICLES) + r")\s+([a-zäöüß][a-zäöüß\-]{3,})\b",
        raw,
        flags=re.IGNORECASE,
    ):
        noun = m.group(2)
        if not noun[:1].islower():
            continue
        # Skip häufige Adjektive/Adverbien
        if noun.endswith(("lich", "ig", "isch", "sam", "bar", "end", "ern", "eln", "en", "st", "te")):
            continue
        if noun.casefold() in {
            "auch", "aber", "oder", "noch", "schon", "sehr", "mehr", "nur", "dann",
            "wenn", "weil", "dass", "nicht", "kein", "keine", "einen", "einem",
        }:
            continue
        hints.append(
            _grammar_issue(
                type="de_article_noun_case",
                start=m.start(2),
                end=m.end(2),
                message="Artikel + kleingeschriebenes Wort — Nomen groß?",
                suggestion=noun[:1].upper() + noun[1:],
                severity="hint",
                lang="de",
                word=noun,
            )
        )

    # Komma vor dass/weil/obwohl fehlt
    for m in re.finditer(r"(?<![,\n])\s+\b(dass|weil|obwohl)\b", raw, re.I):
        # Skip Satzanfang
        before = raw[: m.start()].rstrip()
        if not before or before[-1] in ".!?;:":
            continue
        # Wenn direkt nach Artikel/Präposition oft ok ohne Komma — nur bei Verb-Ende davor
        if re.search(r"[a-zäöüß]{3,}e[nt]?$", before, re.I) or re.search(
            r"\b(?:ist|sind|war|waren|hat|haben|wird|kann|muss|soll)\s*$", before, re.I
        ):
            conj = m.group(1)
            # Position des Konjunkts
            cm = re.search(r"\b(dass|weil|obwohl)\b", m.group(0), re.I)
            if not cm:
                continue
            start = m.start() + cm.start()
            hints.append(
                _grammar_issue(
                    type="de_comma_subordinate",
                    start=start - 1 if start > 0 and raw[start - 1] == " " else start,
                    end=start + len(conj),
                    message=f'Komma vor „{conj.lower()}“ prüfen',
                    suggestion=f", {conj.lower()}",
                    severity="hint",
                    lang="de",
                )
            )

    # Doppelte Verneinung (leicht): nicht + kein/nichts/nie
    for m in re.finditer(
        r"\bnicht\s+(kein|keine|keinen|keinem|keiner|nichts|nie|niemand)\b",
        raw,
        re.I,
    ):
        hints.append(
            _grammar_issue(
                type="de_double_negation",
                start=m.start(),
                end=m.end(),
                message="Mögliche doppelte Verneinung",
                suggestion=m.group(1),
                severity="hint",
                lang="de",
            )
        )

    # Leerzeichen vor Einheiten (10km → 10 km)
    for m in re.finditer(
        r"\b(\d+(?:[.,]\d+)?)(km|mm|cm|kg|mg|ml|m|g|l|€|%|°C|°F)\b",
        raw,
    ):
        hints.append(
            _grammar_issue(
                type="de_space_before_unit",
                start=m.start(),
                end=m.end(),
                message="Leerzeichen vor Einheit empfohlen",
                suggestion=f"{m.group(1)} {m.group(2)}",
                severity="hint",
                lang="de",
            )
        )

    # Subject-Verb Abstand: "Ergeht" / fehlendes Leerzeichen nach Pronomen+Verb (sehr leicht)
    for m in re.finditer(
        r"\b(Ich|Du|Er|Sie|Es|Wir|Ihr|Man)([a-zäöüß]{3,})\b",
        raw,
    ):
        hints.append(
            _grammar_issue(
                type="de_subject_verb_space",
                start=m.start(),
                end=m.end(),
                message="Leerzeichen zwischen Subjekt und Verb fehlt?",
                suggestion=f"{m.group(1)} {m.group(2)}",
                severity="hint",
                lang="de",
            )
        )

    return hints


def _grammar_en(text: str) -> list[dict]:
    """English heuristics: its/it's, your/you're, a/an, S-V agreement, …"""
    hints: list[dict] = []
    raw = text or ""
    if not raw:
        return hints

    # its / it's
    for m in re.finditer(r"\bits\s+(?:a|an|the|my|your|his|her|our|their)\b", raw, re.I):
        hints.append(
            _grammar_issue(
                type="en_its_its",
                start=m.start(),
                end=m.start() + 3,
                message='Possibly "it\'s" (it is) instead of "its"',
                suggestion="it's",
                severity="warning",
                lang="en",
            )
        )
    for m in re.finditer(r"\bit's\s+(?:own|color|colour|name|place|way)\b", raw, re.I):
        hints.append(
            _grammar_issue(
                type="en_its_its",
                start=m.start(),
                end=m.start() + 4,
                message='Possessive "its" instead of "it\'s"?',
                suggestion="its",
                severity="hint",
                lang="en",
            )
        )

    # your / you're
    for m in re.finditer(r"\byour\s+(?:welcome|right|wrong|going|here|there)\b", raw, re.I):
        hints.append(
            _grammar_issue(
                type="en_your_youre",
                start=m.start(),
                end=m.start() + 4,
                message='Possibly "you\'re" (you are) instead of "your"',
                suggestion="you're",
                severity="warning",
                lang="en",
            )
        )
    for m in re.finditer(r"\byou're\s+(?:name|house|car|book|idea)\b", raw, re.I):
        hints.append(
            _grammar_issue(
                type="en_your_youre",
                start=m.start(),
                end=m.start() + 6,
                message='Possessive "your" instead of "you\'re"?',
                suggestion="your",
                severity="hint",
                lang="en",
            )
        )

    # their / there / they're
    for m in re.finditer(r"\btheir\s+(?:is|are|was|were|will)\b", raw, re.I):
        hints.append(
            _grammar_issue(
                type="en_their_there",
                start=m.start(),
                end=m.start() + 5,
                message='Possibly "there" instead of "their"',
                suggestion="there",
                severity="warning",
                lang="en",
            )
        )
    for m in re.finditer(r"\bthere\s+(?:book|house|car|idea|name)\b", raw, re.I):
        hints.append(
            _grammar_issue(
                type="en_their_there",
                start=m.start(),
                end=m.start() + 5,
                message='Possibly "their" (possessive) instead of "there"',
                suggestion="their",
                severity="hint",
                lang="en",
            )
        )
    for m in re.finditer(r"\bthey're\s+(?:book|house|car|idea|name)\b", raw, re.I):
        hints.append(
            _grammar_issue(
                type="en_theyre",
                start=m.start(),
                end=m.start() + 7,
                message='Possibly "their" instead of "they\'re"',
                suggestion="their",
                severity="hint",
                lang="en",
            )
        )

    # a / an before vowels
    for m in re.finditer(r"\b(a)\s+([A-Za-z][A-Za-z\-']*)\b", raw, re.I):
        word = m.group(2)
        if _EN_VOWEL_SOUND.match(word) and not _EN_CONSONANT_U.match(word):
            hints.append(
                _grammar_issue(
                    type="en_a_an",
                    start=m.start(1),
                    end=m.end(1),
                    message=f'Use "an" before "{word}"',
                    suggestion="an",
                    severity="warning",
                    lang="en",
                    word=word,
                )
            )
    for m in re.finditer(r"\b(an)\s+([A-Za-z][A-Za-z\-']*)\b", raw, re.I):
        word = m.group(2)
        if (not _EN_VOWEL_SOUND.match(word)) or word.lower().startswith(
            ("uni", "eu", "one", "use", "user")
        ):
            hints.append(
                _grammar_issue(
                    type="en_a_an",
                    start=m.start(1),
                    end=m.end(1),
                    message=f'Use "a" before "{word}"',
                    suggestion="a",
                    severity="warning",
                    lang="en",
                    word=word,
                )
            )

    # Subject-verb: he/she/it + bare verb (go → goes) light
    for m in re.finditer(
        r"\b(he|she|it)\s+(go|do|have|want|need|like|make|take|come|say|get|know|think|see)\b",
        raw,
        re.I,
    ):
        verb = m.group(2).lower()
        sugg = {
            "go": "goes",
            "do": "does",
            "have": "has",
            "want": "wants",
            "need": "needs",
            "like": "likes",
            "make": "makes",
            "take": "takes",
            "come": "comes",
            "say": "says",
            "get": "gets",
            "know": "knows",
            "think": "thinks",
            "see": "sees",
        }.get(verb, verb + "s")
        hints.append(
            _grammar_issue(
                type="en_subject_verb",
                start=m.start(2),
                end=m.end(2),
                message=f'Subject-verb agreement: "{m.group(1)} {sugg}"?',
                suggestion=sugg,
                severity="warning",
                lang="en",
            )
        )

    # Double negatives (allow one intervening word: don't know nothing)
    for m in re.finditer(
        r"\b(don't|doesn't|didn't|won't|can't|cannot|never|not)\s+"
        r"(?:\w+\s+)?"
        r"(no|nobody|nothing|never|nowhere|none)\b",
        raw,
        re.I,
    ):
        hints.append(
            _grammar_issue(
                type="en_double_negative",
                start=m.start(),
                end=m.end(),
                message="Possible double negative",
                severity="hint",
                lang="en",
            )
        )

    # Comma splice light: ", and" missing — clause, clause with capital mid-sentence after comma?skip
    # Pattern: word, Word (two independent-looking clauses) — ", He" after lowercase
    for m in re.finditer(r"([a-z])\s*,\s*([A-Z][a-z]+)\s+(is|are|was|were|has|have|will|can)\b", raw):
        hints.append(
            _grammar_issue(
                type="en_comma_splice",
                start=m.start() + 1,
                end=m.start(2),
                message="Possible comma splice — consider semicolon or conjunction",
                suggestion="; ",
                severity="hint",
                lang="en",
            )
        )

    return hints


def grammar_check(text: str, *, lang: str | None = None) -> list[dict]:
    """
    Reichhaltigere Grammatik-/Stil-Hinweise (heuristisch).

    Kombiniert Basis-Typografie mit sprachspezifischen Regeln (DE/EN).
    Rückgabe: Liste von Issue-Dicts mit type/start/end/message/suggestion/…
    """
    if lang is None:
        try:
            from instantlensdoc.core.i18n import get_lang

            lang = get_lang()
        except Exception:
            lang = "de"
    code = (lang or "de").split("-")[0].lower()
    issues = _grammar_base_hints(text, lang=code)
    if code == "de":
        issues.extend(_grammar_de(text))
    elif code == "en":
        issues.extend(_grammar_en(text))
    # Sort by position for stable UI
    issues.sort(key=lambda d: (int(d.get("start", 0)), int(d.get("end", 0)), str(d.get("type", ""))))
    return issues


def grammar_hints(text: str, *, lang: str | None = None) -> list[dict]:
    """
    Grammatik-/Typografie-Hinweise (heuristisch).

    Rückwärtskompatibel: enthält weiterhin double_space, repeated_word,
    missing_space_after_punct, lowercase_sentence — plus erweiterte DE/EN-Typen
    aus ``grammar_check``.
    """
    return grammar_check(text, lang=lang)


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
    grammar = grammar_check(text, lang=lang) if include_grammar else []
    return {
        "lang": lang,
        "unknown": unknown,
        "grammar": grammar,
        "count": len(unknown),
        "grammar_count": len(grammar),
    }
