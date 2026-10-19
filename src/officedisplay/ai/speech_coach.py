from __future__ import annotations

import re
import statistics


FILLER_DE = ("äh", "aeh", "ähm", "aehm", "halt", "quasi", "sozusagen", "eigentlich", "irgendwie", "praktisch")
FILLER_EN = ("um", "uh", "like", "actually", "basically", "literally")


def analyze_speech(notes: str, duration_sec: float | None = None) -> dict:
    """Sprechtempo, Füllwörter und Satzlängen – nur aus dem Notiztext, offline."""
    raw = notes or ""
    tokens = re.findall(r"[A-Za-zÄÖÜäöüß']+", raw)
    words = [token for token in tokens if token]
    lowered = [token.lower() for token in words]
    filler_hits = [token for token in lowered if token in FILLER_DE or token in FILLER_EN]
    plain = raw.lower()
    for phrase in ("you know", "sort of", "kind of", "sozusagen"):
        filler_hits.extend([phrase] * plain.count(phrase))
    sentences = [part.strip() for part in re.split(r"[.!?]+", raw) if part.strip()]
    lengths = [len(re.findall(r"[A-Za-zÄÖÜäöüß']+", sentence)) for sentence in sentences] or [0]
    wpm_target = 130
    if duration_sec and duration_sec > 0 and words:
        wpm = round(len(words) / (duration_sec / 60.0), 1)
        minutes = round(duration_sec / 60.0, 2)
    else:
        wpm = wpm_target if words else 0
        minutes = round((len(words) / wpm_target) if words else 0.0, 2)
    variation = statistics.pstdev(lengths) if len(lengths) > 1 else 0.0
    tips = []
    if not words:
        tips.append("Keine Sprechernotiz vorhanden.")
    if len(filler_hits) >= 3:
        tips.append("Mehrere Füllwörter. Betroffene Stellen kürzen oder streichen.")
    if words and wpm > 160:
        tips.append("Text ist dicht. Für etwa 130 Wörter pro Minute kürzen.")
    if variation < 3 and len(sentences) >= 3:
        tips.append("Sätze sind ähnlich lang. Wechsel aus kurzen und langen Sätzen erhöht die Spannung.")
    if words and minutes < 0.25:
        tips.append("Notiz ist sehr kurz. Kernsatz und ein Beispiel ergänzen, falls die Folie mehr tragen soll.")
    if not tips:
        tips.append("Notiz liegt in einem ruhigen Sprechbereich.")
    return {
        "words": len(words),
        "minutes": minutes,
        "wpm": wpm,
        "target_wpm": wpm_target,
        "fillers": filler_hits,
        "filler_count": len(filler_hits),
        "sentence_lengths": lengths,
        "length_variation": round(variation, 2),
        "tips": tips,
    }
