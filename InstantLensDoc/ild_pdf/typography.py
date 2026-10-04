"""Erweiterte Typografie 2.6.13: Tracking, Kerning, Leading, Zeichenstile, Silbentrennung, Drop Caps.

Baut auf Style-Presets (2.6.10) und Absatzformat (2.6.11) auf.
Kein CMYK/Bleed/Preflight/PDF/X, kein volles i18n, keine KI-Wizards.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .page_layout import (
    PARAGRAPH_ALIGNMENTS,
    ParagraphFormat,
    _split_paragraphs,
    _strip_para_markers,
    apply_paragraph_format,
    parse_paragraph_format,
)

# Tracking in 1/1000 em; Leading als Multiplikator oder absolute pt
TRACKING_PRESETS: tuple[float, ...] = (-50.0, -25.0, 0.0, 25.0, 50.0, 100.0)
LEADING_MULTIPLIERS: tuple[float, ...] = (1.0, 1.15, 1.2, 1.5, 2.0)

_TYPO_MARKER_RE = re.compile(
    r"^<!--\s*ild-typo:tr=([-0-9.]+);kn=([-0-9.]+);ld=([-0-9.]+)\s*-->\s*$",
    re.IGNORECASE,
)
_DROPCAP_MARKER_RE = re.compile(
    r"^<!--\s*ild-dropcap:lines=(\d+);chars=(\d+)\s*-->\s*$",
    re.IGNORECASE,
)
_CHARSTYLE_MARKER_RE = re.compile(
    r"^<!--\s*ild-charstyle:([a-z0-9_-]+)\s*-->\s*$",
    re.IGNORECASE,
)

SOFT_HYPHEN = "\u00ad"

# --- Zeichenstile (dokumentweit, auf 2.6.10 Presets aufbauend) ---

CHARACTER_STYLE_PRESETS: dict[str, dict[str, Any]] = {
    "emphasis": {
        "name": "Betonung",
        "font_family": "Helvetica",
        "font_size": 11.0,
        "bold": False,
        "italic": True,
        "tracking": 0.0,
        "kerning": 0.0,
    },
    "strong": {
        "name": "Fett",
        "font_family": "Helvetica",
        "font_size": 11.0,
        "bold": True,
        "italic": False,
        "tracking": 0.0,
        "kerning": 0.0,
    },
    "smallcaps": {
        "name": "Kapitälchen",
        "font_family": "Helvetica",
        "font_size": 10.0,
        "bold": False,
        "italic": False,
        "tracking": 40.0,
        "kerning": 0.0,
        "small_caps": True,
    },
    "code": {
        "name": "Code",
        "font_family": "Courier",
        "font_size": 10.0,
        "bold": False,
        "italic": False,
        "tracking": 0.0,
        "kerning": 0.0,
    },
}


@dataclass
class CharacterStyle:
    """Zeichenstil — Tracking/Kerning in 1/1000 em."""

    id: str = "emphasis"
    name: str = "Betonung"
    font_family: str = "Helvetica"
    font_size: float = 11.0
    bold: bool = False
    italic: bool = False
    tracking: float = 0.0
    kerning: float = 0.0
    small_caps: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_preset(cls, style_id: str) -> "CharacterStyle":
        key = (style_id or "emphasis").strip().lower()
        preset = CHARACTER_STYLE_PRESETS.get(key) or CHARACTER_STYLE_PRESETS["emphasis"]
        return cls(
            id=key if key in CHARACTER_STYLE_PRESETS else "emphasis",
            name=str(preset.get("name") or key),
            font_family=str(preset.get("font_family") or "Helvetica"),
            font_size=float(preset.get("font_size") or 11.0),
            bold=bool(preset.get("bold", False)),
            italic=bool(preset.get("italic", False)),
            tracking=float(preset.get("tracking") or 0.0),
            kerning=float(preset.get("kerning") or 0.0),
            small_caps=bool(preset.get("small_caps", False)),
        )


@dataclass
class TypographyFormat:
    """Erweiterte Typografie-Attribute (Absatz + Zeichen)."""

    tracking: float = 0.0  # 1/1000 em
    kerning: float = 0.0  # globale Paar-Anpassung 1/1000 em
    leading: float = 1.15  # Multiplikator (Leading ≈ font_size * leading)
    drop_cap_lines: int = 0
    drop_cap_chars: int = 0
    char_style_id: str = ""
    paragraph: ParagraphFormat = field(default_factory=ParagraphFormat)

    def to_dict(self) -> dict[str, Any]:
        d = {
            "tracking": self.tracking,
            "kerning": self.kerning,
            "leading": self.leading,
            "drop_cap_lines": self.drop_cap_lines,
            "drop_cap_chars": self.drop_cap_chars,
            "char_style_id": self.char_style_id,
            "paragraph": self.paragraph.to_dict(),
        }
        return d


def list_character_styles() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for sid in CHARACTER_STYLE_PRESETS:
        out.append(CharacterStyle.from_preset(sid).to_dict())
    return out


def get_character_style(style_id: str) -> dict[str, Any]:
    return CharacterStyle.from_preset(style_id).to_dict()


def typography_marker(
    *,
    tracking: float = 0.0,
    kerning: float = 0.0,
    leading: float = 1.15,
) -> str:
    return (
        f"<!-- ild-typo:tr={float(tracking):g};kn={float(kerning):g};"
        f"ld={float(leading):g} -->"
    )


def dropcap_marker(*, lines: int = 3, chars: int = 1) -> str:
    return f"<!-- ild-dropcap:lines={max(0, int(lines))};chars={max(0, int(chars))} -->"


def charstyle_marker(style_id: str) -> str:
    sid = re.sub(r"[^a-z0-9_-]", "", (style_id or "emphasis").lower()) or "emphasis"
    return f"<!-- ild-charstyle:{sid} -->"


def apply_typography(
    text: str,
    *,
    tracking: float | None = None,
    kerning: float | None = None,
    leading: float | None = None,
    drop_cap_lines: int | None = None,
    drop_cap_chars: int | None = None,
    char_style_id: str | None = None,
    alignment: str | None = None,
    line_spacing: float | None = None,
    paragraph_index: int | None = None,
) -> str:
    """Setzt Typo-Marker (Tracking/Kerning/Leading/DropCap/CharStyle) vor Absätze."""
    # Leading und line_spacing sind verwandt — Leading steuert ild-typo, line_spacing ild-spacing
    if alignment is not None or line_spacing is not None:
        text = apply_paragraph_format(
            text,
            alignment=alignment,
            line_spacing=line_spacing if line_spacing is not None else leading,
            paragraph_index=paragraph_index,
        )
    paras = _split_paragraphs(text)
    if not paras:
        return text or ""
    indices = range(len(paras)) if paragraph_index is None else [int(paragraph_index)]
    for idx in indices:
        if idx < 0 or idx >= len(paras):
            continue
        cur = parse_typography(paras[idx])
        body = _strip_typo_markers(paras[idx])
        prefix: list[str] = []
        # bestehende Align/Spacing-Marker behalten
        for line in paras[idx].splitlines():
            s = line.strip()
            if s.startswith("<!-- ild-align:") or s.startswith("<!-- ild-spacing:"):
                prefix.append(line if line.strip() == s else s)
        tr = float(tracking) if tracking is not None else cur.tracking
        kn = float(kerning) if kerning is not None else cur.kerning
        ld = float(leading) if leading is not None else cur.leading
        if tracking is not None or kerning is not None or leading is not None:
            prefix.append(typography_marker(tracking=tr, kerning=kn, leading=ld))
        dc_lines = (
            int(drop_cap_lines)
            if drop_cap_lines is not None
            else cur.drop_cap_lines
        )
        dc_chars = (
            int(drop_cap_chars)
            if drop_cap_chars is not None
            else cur.drop_cap_chars
        )
        if drop_cap_lines is not None or drop_cap_chars is not None:
            if dc_lines > 0 and dc_chars > 0:
                prefix.append(dropcap_marker(lines=dc_lines, chars=dc_chars))
        if char_style_id is not None:
            prefix.append(charstyle_marker(char_style_id))
        paras[idx] = "\n".join(prefix + body) if prefix else "\n".join(body)
    return "\n\n".join(paras)


def apply_drop_cap(
    text: str,
    *,
    lines: int = 3,
    chars: int = 1,
    paragraph_index: int = 0,
) -> str:
    """Drop Cap auf einen Absatz anwenden (Marker + erster Buchstabe markiert)."""
    return apply_typography(
        text,
        drop_cap_lines=max(1, int(lines)),
        drop_cap_chars=max(1, int(chars)),
        paragraph_index=int(paragraph_index),
    )


def parse_typography(paragraph: str) -> TypographyFormat:
    pf = parse_paragraph_format(paragraph)
    tr, kn, ld = 0.0, 0.0, pf.line_spacing
    dc_lines, dc_chars = 0, 0
    char_id = ""
    for line in (paragraph or "").splitlines():
        s = line.strip()
        m = _TYPO_MARKER_RE.match(s)
        if m:
            tr = float(m.group(1))
            kn = float(m.group(2))
            ld = float(m.group(3))
            continue
        m2 = _DROPCAP_MARKER_RE.match(s)
        if m2:
            dc_lines = int(m2.group(1))
            dc_chars = int(m2.group(2))
            continue
        m3 = _CHARSTYLE_MARKER_RE.match(s)
        if m3:
            char_id = m3.group(1)
    return TypographyFormat(
        tracking=tr,
        kerning=kn,
        leading=ld,
        drop_cap_lines=dc_lines,
        drop_cap_chars=dc_chars,
        char_style_id=char_id,
        paragraph=pf,
    )


def _strip_typo_markers(paragraph: str) -> list[str]:
    lines: list[str] = []
    for line in (paragraph or "").splitlines():
        s = line.strip()
        if (
            _TYPO_MARKER_RE.match(s)
            or _DROPCAP_MARKER_RE.match(s)
            or _CHARSTYLE_MARKER_RE.match(s)
            or s.startswith("<!-- ild-align:")
            or s.startswith("<!-- ild-spacing:")
        ):
            continue
        lines.append(line)
    return lines if lines else [""]


def leading_pt(font_size: float, leading: float = 1.15) -> float:
    """Leading in Punkten aus Schriftgröße × Multiplikator."""
    return max(1.0, float(font_size) * float(leading))


def apply_tracking_visual(text: str, tracking: float) -> str:
    """Einfache Visualisierung: Tracking > 0 → schmale Spaces zwischen Zeichen."""
    if abs(float(tracking)) < 1e-6 or not text:
        return text
    # Nur Buchstaben/Ziffern aufweiten; Whitespace unverändert
    if float(tracking) <= 0:
        return text
    gap = "\u200a" if float(tracking) < 50 else "\u2009"
    out: list[str] = []
    for ch in text:
        out.append(ch)
        if ch.isalnum():
            out.append(gap)
    # trailing gap entfernen
    result = "".join(out)
    return result.rstrip("\u200a\u2009")


# --- Silbentrennung (alle 9 UI-Sprachen) ---

HyphenPatternFn = Callable[[str], List[int]]

# Kanonische UI-Sprach-IDs (identisch zu i18n.SUPPORTED_LANGS)
HYPHENATION_UI_LANGS: tuple[str, ...] = (
    "de",
    "en",
    "fr",
    "ru",
    "es",
    "zh",
    "pt",
    "ar",
    "it",
)

# Einfache Muster: Positionen NACH dem Index (0-basiert), an denen getrennt werden darf.
# Heuristisch (kein TeX-Liang); praktische VC-Regeln pro Sprache.
_DE_VOWELS = set("aeiouäöüAEIOUÄÖÜyY")
_EN_VOWELS = set("aeiouyAEIOUY")
_FR_VOWELS = set("aeiouyàâäéèêëïîôöùûüœæAEIOUYÀÂÄÉÈÊËÏÎÔÖÙÛÜŒÆ")
_ES_VOWELS = set("aeiouáéíóúüAEIOUÁÉÍÓÚÜyY")
_PT_VOWELS = set("aeiouáàâãéêíóôõúüAEIOUÁÀÂÃÉÊÍÓÔÕÚÜyY")
_IT_VOWELS = set("aeiouàèéìíîòóùúAEIOUÀÈÉÌÍÎÒÓÙÚyY")
# Kyrillische Vokale (RU) + lateinische Fallback
_RU_VOWELS = set(
    "аеёиоуыэюяАЕЁИОУЫЭЮЯ"
    "aeiouyAEIOUY"
)

# Ausnahmewörter (feste Trennpunkte)
_DE_EXCEPTIONS: dict[str, tuple[int, ...]] = {
    "instantlens": (8,),
    "dokument": (3,),
    "silbentrennung": (5, 10),
    "typografie": (4,),
    "veröffentlichung": (3, 10),
}
_EN_EXCEPTIONS: dict[str, tuple[int, ...]] = {
    "hyphenation": (2, 6),
    "typography": (4,),
    "publishing": (3,),
    "document": (3,),
    "instantlens": (8,),
}
_FR_EXCEPTIONS: dict[str, tuple[int, ...]] = {
    "typographie": (4,),
    "document": (3,),
    "publication": (3, 7),
    "instantlens": (8,),
}
_ES_EXCEPTIONS: dict[str, tuple[int, ...]] = {
    "tipografia": (4,),
    "documento": (3,),
    "publicacion": (4,),
    "instantlens": (8,),
}
_PT_EXCEPTIONS: dict[str, tuple[int, ...]] = {
    "tipografia": (4,),
    "documento": (3,),
    "publicacao": (4,),
    "instantlens": (8,),
}
_IT_EXCEPTIONS: dict[str, tuple[int, ...]] = {
    "tipografia": (4,),
    "documento": (3,),
    "pubblicazione": (3, 7),
    "instantlens": (8,),
}
_RU_EXCEPTIONS: dict[str, tuple[int, ...]] = {
    "типографика": (4,),
    "документ": (3,),
    "публикация": (4,),
}


def _vowel_consonant_breaks(word: str, vowels: set[str]) -> list[int]:
    """Heuristik: Trennung zwischen Vokal und Konsonant-Vokal (min. 2 Zeichen je Seite)."""
    w = word
    n = len(w)
    breaks: list[int] = []
    if n < 5:
        return breaks
    for i in range(2, n - 2):
        left, right = w[i - 1], w[i]
        if left in vowels and right not in vowels:
            # ck/ch/sch nicht mitten trennen (lateinische Digraphen)
            digraph = w[i : i + 2].lower()
            if digraph in ("ck", "ch", "sch"[:2], "ll", "rr", "qu"):
                continue
            if w[i + 1 : i + 2] and (w[i + 1] in vowels or w[i + 1].isalpha()):
                breaks.append(i)
    return breaks


def _hyphenate_de(word: str) -> list[int]:
    key = word.lower()
    if key in _DE_EXCEPTIONS:
        return list(_DE_EXCEPTIONS[key])
    return _vowel_consonant_breaks(word, _DE_VOWELS)


def _hyphenate_en(word: str) -> list[int]:
    key = word.lower()
    if key in _EN_EXCEPTIONS:
        return list(_EN_EXCEPTIONS[key])
    return _vowel_consonant_breaks(word, _EN_VOWELS)


def _hyphenate_fr(word: str) -> list[int]:
    """FR: VC-Heuristik; vermeidet Trennung nach stummem e am Wortende."""
    key = word.lower()
    if key in _FR_EXCEPTIONS:
        return list(_FR_EXCEPTIONS[key])
    breaks = _vowel_consonant_breaks(word, _FR_VOWELS)
    # Keine Trennung direkt vor End-e / End-es (sehr grob)
    n = len(word)
    if n >= 3 and word[-1].lower() == "e":
        breaks = [b for b in breaks if b < n - 2]
    return breaks


def _hyphenate_es(word: str) -> list[int]:
    key = word.lower()
    if key in _ES_EXCEPTIONS:
        return list(_ES_EXCEPTIONS[key])
    return _vowel_consonant_breaks(word, _ES_VOWELS)


def _hyphenate_pt(word: str) -> list[int]:
    key = word.lower()
    if key in _PT_EXCEPTIONS:
        return list(_PT_EXCEPTIONS[key])
    return _vowel_consonant_breaks(word, _PT_VOWELS)


def _hyphenate_it(word: str) -> list[int]:
    key = word.lower()
    if key in _IT_EXCEPTIONS:
        return list(_IT_EXCEPTIONS[key])
    return _vowel_consonant_breaks(word, _IT_VOWELS)


def _hyphenate_ru(word: str) -> list[int]:
    """RU: kyrillisch-bewusste Vokal-Konsonant-Trennung."""
    key = word.lower()
    if key in _RU_EXCEPTIONS:
        return list(_RU_EXCEPTIONS[key])
    return _vowel_consonant_breaks(word, _RU_VOWELS)


def _hyphenate_ar(word: str) -> list[int]:
    """AR: leicht / No-Op — Arabisch wird typografisch nicht per Soft-Hyphen gebrochen."""
    return []


def _hyphenate_zh(word: str) -> list[int]:
    """ZH: Identity / No-Break — CJK braucht keine Silbentrennung."""
    return []


_HYPHENATORS: dict[str, HyphenPatternFn] = {}

# Alias-Gruppen → kanonische Funktion
_HYPHEN_ALIAS_GROUPS: tuple[tuple[tuple[str, ...], HyphenPatternFn], ...] = (
    (("de", "deu", "ger", "german"), _hyphenate_de),
    (("en", "eng", "english"), _hyphenate_en),
    (("fr", "fra", "fre", "french"), _hyphenate_fr),
    (("es", "spa", "spanish"), _hyphenate_es),
    (("pt", "por", "portuguese"), _hyphenate_pt),
    (("it", "ita", "italian"), _hyphenate_it),
    (("ru", "rus", "russian"), _hyphenate_ru),
    (("ar", "ara", "arabic"), _hyphenate_ar),
    (("zh", "zho", "chi", "cn", "chinese"), _hyphenate_zh),
)


def _register_builtin_hyphenators() -> None:
    """Auto-Register aller 9 UI-Sprachen (+ Aliase) beim Import."""
    for aliases, fn in _HYPHEN_ALIAS_GROUPS:
        for key in aliases:
            _HYPHENATORS[key] = fn


_register_builtin_hyphenators()


def register_hyphenation_language(lang: str, fn: HyphenPatternFn) -> None:
    """Hook: weitere Sprachen registrieren. ``fn(word) -> break_indices``."""
    key = (lang or "").strip().lower()
    if not key:
        raise ValueError("lang darf nicht leer sein")
    if not callable(fn):
        raise TypeError("fn muss aufrufbar sein")
    _HYPHENATORS[key] = fn


def list_hyphenation_languages() -> list[str]:
    """Kanonische UI-Sprach-IDs (9) zuerst, danach manuell registrierte Extras."""
    canon = list(HYPHENATION_UI_LANGS)
    alias_skip = {
        "deu",
        "ger",
        "german",
        "eng",
        "english",
        "fra",
        "fre",
        "french",
        "spa",
        "spanish",
        "por",
        "portuguese",
        "ita",
        "italian",
        "rus",
        "russian",
        "ara",
        "arabic",
        "zho",
        "chi",
        "cn",
        "chinese",
    }
    extras = sorted(
        k for k in _HYPHENATORS if k not in canon and k not in alias_skip
    )
    return canon + extras


def hyphenate_word(word: str, *, lang: str = "de") -> str:
    """Wort mit Soft-Hyphens an Trennstellen zurückgeben."""
    raw = word or ""
    if len(raw) < 5:
        return raw
    # isalpha() deckt Kyrillisch/Latein ab; Arabisch/CJK bewusst kein Soft-Hyphen
    if not raw.isalpha():
        return raw
    key = (lang or "de").strip().lower()
    fn = _HYPHENATORS.get(key)
    if fn is None:
        # Fallback: de
        fn = _HYPHENATORS["de"]
    breaks = sorted(set(fn(raw)))
    if not breaks:
        return raw
    parts: list[str] = []
    prev = 0
    for b in breaks:
        if b <= prev or b >= len(raw):
            continue
        parts.append(raw[prev:b])
        parts.append(SOFT_HYPHEN)
        prev = b
    parts.append(raw[prev:])
    return "".join(parts)


# Latein (inkl. Akzente) + Kyrillisch; Arabisch/CJK bewusst nicht (No-Op-Hyphenatoren)
_WORD_RE = re.compile(
    r"[A-Za-zÄÖÜäöüßÀ-ÖØ-öø-ÿĀ-ſ"
    r"А-Яа-яЁёІіЇїЄєҐґ]+"
)


def hyphenate_text(text: str, *, lang: str = "de") -> dict[str, Any]:
    """Text silbentrennen (Soft-Hyphens). Rückgabe: text, count, lang.

    Unterstützt alle 9 UI-Sprachen out of the box (``lang='fr'`` etc.).
    ``zh``/``ar``: keine Soft-Hyphens (Identity / No-Op).
    """
    count = 0

    def _repl(m: re.Match[str]) -> str:
        nonlocal count
        w = m.group(0)
        hy = hyphenate_word(w, lang=lang)
        if SOFT_HYPHEN in hy:
            count += hy.count(SOFT_HYPHEN)
        return hy

    new_text = _WORD_RE.sub(_repl, text or "")
    return {"text": new_text, "count": count, "lang": (lang or "de").lower()}


def paragraph_styles_with_typography() -> list[dict[str, Any]]:
    """Absatzstile (2.6.10/11) inkl. Typografie-Defaults Tracking/Leading."""
    from .page_layout import list_paragraph_formats_from_styles

    rows = list_paragraph_formats_from_styles()
    defaults = {
        "heading1": {"tracking": -10.0, "kerning": 0.0, "leading": 1.15, "drop_cap_lines": 0},
        "heading2": {"tracking": -5.0, "kerning": 0.0, "leading": 1.15, "drop_cap_lines": 0},
        "heading3": {"tracking": 0.0, "kerning": 0.0, "leading": 1.15, "drop_cap_lines": 0},
        "body": {"tracking": 0.0, "kerning": 0.0, "leading": 1.15, "drop_cap_lines": 0},
        "quote": {"tracking": 10.0, "kerning": 0.0, "leading": 1.5, "drop_cap_lines": 0},
    }
    for row in rows:
        sid = str(row.get("id") or "body")
        d = defaults.get(sid, defaults["body"])
        row["typography"] = dict(d)
        row.setdefault("character_styles", list_character_styles())
    return rows


def enrich_style_presets_typography() -> None:
    """Idempotent: Tracking/Leading-Defaults in STYLE_PRESETS setzen."""
    from .auto_format import STYLE_PRESETS

    defaults = {
        "heading1": {"tracking": -10.0, "kerning": 0.0, "leading": 1.15},
        "heading2": {"tracking": -5.0, "kerning": 0.0, "leading": 1.15},
        "heading3": {"tracking": 0.0, "kerning": 0.0, "leading": 1.15},
        "body": {"tracking": 0.0, "kerning": 0.0, "leading": 1.15},
        "quote": {"tracking": 10.0, "kerning": 0.0, "leading": 1.5},
    }
    for sid, preset in STYLE_PRESETS.items():
        d = defaults.get(sid, defaults["body"])
        for k, v in d.items():
            preset.setdefault(k, v)


enrich_style_presets_typography()
