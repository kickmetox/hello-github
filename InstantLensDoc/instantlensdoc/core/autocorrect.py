"""Autokorrektur und Textbaustein-Kürzel — 2.6.24.

Tippfehler-Ersetzung beim Tippen (Space/Satzzeichen) und Snippet-Trigger
(z. B. ``mfg`` → Mit freundlichen Grüßen). UI-Sprache steuert Defaults.
"""

from __future__ import annotations

import re
from typing import Any

# Builtin-Tippfehler je Sprache (Trigger → Ersatz, case-insensitive Match)
_DEFAULT_TYPOS: dict[str, dict[str, str]] = {
    "de": {
        "teh": "the",
        "adn": "and",
        "nad": "and",
        "udn": "und",
        "nidht": "nicht",
        "wiessen": "wissen",
        "würklich": "wirklich",
        "dämlich": "dämlich",  # keep as-is (no-op placeholder avoided)
        "recchnung": "rechnung",
        "dokumnet": "dokument",
        "speicehrn": "speichern",
        "öfnen": "öffnen",
        "hife": "hilfe",
        "einstellugen": "einstellungen",
    },
    "en": {
        "teh": "the",
        "adn": "and",
        "nad": "and",
        "taht": "that",
        "recieve": "receive",
        "seperate": "separate",
        "occured": "occurred",
        "definately": "definitely",
        "accomodate": "accommodate",
        "untill": "until",
        "wich": "which",
        "becuase": "because",
        "documnet": "document",
    },
    "fr": {
        "teh": "the",
        "etn": "et",
        "documente": "document",
        "merciii": "merci",
    },
    "es": {
        "teh": "the",
        "qeu": "que",
        "porqe": "porque",
        "documente": "documento",
    },
    "it": {
        "teh": "the",
        "cheh": "che",
        "documente": "documento",
    },
    "pt": {
        "teh": "the",
        "qeu": "que",
        "documente": "documento",
    },
    "ru": {
        "пртвет": "привет",
        "спасиб": "спасибо",
    },
    "zh": {},
    "ar": {},
}

# Entferne No-Ops aus DE
_DEFAULT_TYPOS["de"].pop("dämlich", None)

# Snippet-Kürzel (Bausteine) — Trigger ohne Leerzeichen
_DEFAULT_SNIPPET_TRIGGERS: dict[str, dict[str, str]] = {
    "de": {
        "sgdh": "Sehr geehrte Damen und Herren,\n\n",
        "mfg": "Mit freundlichen Grüßen\n",
        "vg": "Viele Grüße\n",
        "br": "Best regards,\n",
        "adr": "Adresse:\n",
        "dat": "{date}\n",
    },
    "en": {
        "sgdh": "Dear Sir or Madam,\n\n",
        "mfg": "Kind regards,\n",
        "vg": "Best regards,\n",
        "br": "Best regards,\n",
        "adr": "Address:\n",
        "dat": "{date}\n",
    },
    "fr": {
        "mfg": "Cordialement,\n",
        "br": "Bien à vous,\n",
        "sgdh": "Madame, Monsieur,\n\n",
    },
    "es": {
        "mfg": "Atentamente,\n",
        "br": "Saludos cordiales,\n",
        "sgdh": "Estimados señores:\n\n",
    },
    "it": {
        "mfg": "Cordiali saluti,\n",
        "br": "Distinti saluti,\n",
        "sgdh": "Gentili Signore e Signori,\n\n",
    },
    "pt": {
        "mfg": "Com os melhores cumprimentos,\n",
        "br": "Atenciosamente,\n",
        "sgdh": "Exmos. Senhores,\n\n",
    },
    "ru": {
        "mfg": "С уважением,\n",
        "br": "С наилучшими пожеланиями,\n",
    },
    "zh": {
        "mfg": "此致敬礼\n",
        "br": "谢谢\n",
    },
    "ar": {
        "mfg": "مع أطيب التحيات\n",
        "br": "تحياتي\n",
    },
}


def _lang_code(lang: str | None) -> str:
    code = (lang or "de").split("-")[0].lower()
    return code if code in _DEFAULT_TYPOS else "de"


def default_typo_rules(lang: str | None = None) -> dict[str, str]:
    return dict(_DEFAULT_TYPOS.get(_lang_code(lang), {}))


def default_snippet_triggers(lang: str | None = None) -> dict[str, str]:
    return dict(_DEFAULT_SNIPPET_TRIGGERS.get(_lang_code(lang), {}))


def merge_rules(
    base: dict[str, str],
    user: dict[str, str] | None,
) -> dict[str, str]:
    out = {normalize_trigger(k): str(v) for k, v in (base or {}).items() if k and v is not None}
    for k, v in (user or {}).items():
        key = normalize_trigger(k)
        if not key:
            continue
        if v is None or str(v) == "":
            out.pop(key, None)
        else:
            out[key] = str(v)
    return out


def normalize_trigger(trigger: str) -> str:
    return (trigger or "").strip().casefold()


def lookup_replacement(
    token: str,
    rules: dict[str, str],
) -> str | None:
    """Ersatz für Token oder None."""
    key = normalize_trigger(token)
    if not key:
        return None
    rep = rules.get(key)
    if rep is None:
        return None
    # Großschreibung der Vorlage
    if token[:1].isupper() and rep:
        if "\n" in rep:
            first, rest = rep.split("\n", 1)
            return (first[:1].upper() + first[1:]) + ("\n" + rest if rest is not None else "")
        return rep[:1].upper() + rep[1:]
    return rep


_TOKEN_BEFORE_RE = re.compile(
    r"([A-Za-zÀ-ÖØ-öø-ÿĀ-ž0-9_./-]{1,64})$", re.UNICODE
)


def apply_autocorrect_at_cursor(
    text: str,
    cursor_pos: int,
    rules: dict[str, str],
    *,
    expand_snippets: bool = True,
) -> dict[str, Any] | None:
    """
    Token links vom Cursor ersetzen, wenn Regel greift.

    Erwartet, dass der Aufrufer Cursor *nach* dem auslösenden Zeichen
    (Space/Satzzeichen) hat — das Zeichen selbst bleibt.
    Rückgabe: {start, end, old, new} oder None.
    """
    if cursor_pos < 0 or cursor_pos > len(text or ""):
        return None
    before = (text or "")[:cursor_pos]
    # Trailing Space/Punct nicht Teil des Tokens
    m = _TOKEN_BEFORE_RE.search(before.rstrip(" \t"))
    # Wenn vor Cursor noch Space steht: Token vor dem Space
    stripped = before
    trail = ""
    while stripped and stripped[-1] in " \t.,;:!?":
        trail = stripped[-1] + trail
        stripped = stripped[:-1]
    m = _TOKEN_BEFORE_RE.search(stripped)
    if not m:
        return None
    token = m.group(1)
    start = m.start(1)
    end = m.end(1)
    rep = lookup_replacement(token, rules)
    if rep is None:
        return None
    # Snippet-Trigger oft länger Expansion — immer erlaubt wenn in rules
    if not expand_snippets and "\n" in rep:
        return None
    if rep == token:
        return None
    return {"start": start, "end": end, "old": token, "new": rep}


def apply_autocorrect_to_text(
    text: str,
    rules: dict[str, str],
    *,
    whole_words: bool = True,
) -> tuple[str, int]:
    """
    Gesamten Text einmalig korrigieren (Batch). Rückgabe (neuer_text, n_ersetzungen).
    """
    if not text or not rules:
        return text or "", 0
    count = 0

    def _sub(m: re.Match) -> str:
        nonlocal count
        tok = m.group(0)
        rep = lookup_replacement(tok, rules)
        if rep is None or rep == tok:
            return tok
        count += 1
        return rep

    if whole_words:
        pattern = re.compile(
            r"[A-Za-zÀ-ÖØ-öø-ÿĀ-ž][A-Za-zÀ-ÖØ-öø-ÿĀ-ž0-9_./'-]*",
            re.UNICODE,
        )
        new = pattern.sub(_sub, text)
    else:
        new = text
        for trigger, replacement in sorted(rules.items(), key=lambda x: -len(x[0])):
            if not trigger:
                continue
            rx = re.compile(re.escape(trigger), re.IGNORECASE)
            new2, n = rx.subn(replacement, new)
            if n:
                count += n
                new = new2
    return new, count


def list_autocorrect_rules(lang: str | None = None) -> list[dict[str, str]]:
    """Builtin + User-Regeln als Liste [{trigger, replacement, source}]."""
    from instantlensdoc.core.app_settings import get_autocorrect_user_rules

    lang_code = _lang_code(lang)
    builtin = default_typo_rules(lang_code)
    snippets = default_snippet_triggers(lang_code)
    user = get_autocorrect_user_rules()
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for src, mapping in (
        ("builtin_typo", builtin),
        ("builtin_snippet", snippets),
        ("user", user),
    ):
        for k, v in mapping.items():
            key = normalize_trigger(k)
            if not key or key in seen and src != "user":
                continue
            seen.add(key)
            out.append({"trigger": key, "replacement": str(v), "source": src})
    return out


def effective_autocorrect_rules(lang: str | None = None) -> dict[str, str]:
    """Zusammengeführte Regeln für Tippen: Typos + Snippet-Trigger + User."""
    from instantlensdoc.core.app_settings import get_autocorrect_user_rules

    if lang is None:
        try:
            from instantlensdoc.core.i18n import get_lang

            lang = get_lang()
        except Exception:
            lang = "de"
    base = default_typo_rules(lang)
    base.update(default_snippet_triggers(lang))
    return merge_rules(base, get_autocorrect_user_rules())
