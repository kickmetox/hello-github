"""KI-Assistent: OpenAI-kompatibler Endpoint + lokaler Offline-Fallback.

Aktionen auf ausgewähltem Text: zusammenfassen, umformulieren, übersetzen,
Inhaltsverzeichnis vorschlagen. Ohne API-Schlüssel: degradierter Modus.
"""

from __future__ import annotations

import json
import math
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Iterable

from instantlensdoc.core.app_settings import load_settings, save_settings

ACTIONS = ("summarize", "rewrite", "translate", "toc")

_DE_EN = {
    "und": "and",
    "oder": "or",
    "der": "the",
    "die": "the",
    "das": "the",
    "ein": "a",
    "eine": "a",
    "ist": "is",
    "sind": "are",
    "nicht": "not",
    "mit": "with",
    "für": "for",
    "von": "of",
    "im": "in the",
    "auf": "on",
    "zu": "to",
    "dokument": "document",
    "seite": "page",
    "text": "text",
    "zusammenfassung": "summary",
    "inhaltsverzeichnis": "table of contents",
    "überschrift": "heading",
    "kapitel": "chapter",
    "layout": "layout",
    "rahmen": "frame",
}

_EN_DE = {v: k for k, v in _DE_EN.items() if v not in ("the", "a")}
_EN_DE["the"] = "der"
_EN_DE["a"] = "ein"
_EN_DE["summary"] = "Zusammenfassung"
_EN_DE["heading"] = "Überschrift"

_STOP = {
    "und", "oder", "der", "die", "das", "ein", "eine", "ist", "sind", "nicht",
    "mit", "für", "von", "im", "auf", "zu", "den", "dem", "des", "ein",
    "the", "and", "or", "a", "an", "is", "are", "of", "to", "in", "on", "for",
    "with", "this", "that", "es", "sie", "wir", "ihr", "als", "auch", "bei",
}


def get_ki_settings() -> dict[str, str]:
    s = load_settings()
    return {
        "endpoint": str(s.get("ki_endpoint") or "").strip(),
        "api_key": str(s.get("ki_api_key") or "").strip(),
        "model": str(s.get("ki_model") or "gpt-4o-mini").strip() or "gpt-4o-mini",
    }


def set_ki_settings(*, endpoint: str | None = None, api_key: str | None = None, model: str | None = None) -> dict[str, str]:
    upd: dict[str, Any] = {}
    if endpoint is not None:
        upd["ki_endpoint"] = endpoint.strip()
    if api_key is not None:
        upd["ki_api_key"] = api_key.strip()
    if model is not None:
        upd["ki_model"] = model.strip()
    if upd:
        save_settings(upd)
    return get_ki_settings()


@dataclass
class KiRequest:
    action: str
    text: str
    target_lang: str = "en"
    endpoint: str = ""
    api_key: str = ""
    model: str = "gpt-4o-mini"


@dataclass
class KiResult:
    ok: bool
    action: str
    text: str
    degraded: bool = False
    backend: str = "offline"
    message: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p.strip() for p in parts if p.strip()]


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-zÄÖÜäöüß0-9\-]+", text or "")


def offline_summarize(text: str, *, max_sentences: int = 3) -> str:
    sents = _sentences(text)
    if not sents:
        return ""
    if len(sents) <= max_sentences:
        return " ".join(sents)
    freq: dict[str, int] = {}
    for w in _words(text.lower()):
        if w in _STOP or len(w) < 3:
            continue
        freq[w] = freq.get(w, 0) + 1
    scored = []
    for i, s in enumerate(sents):
        score = sum(freq.get(w.lower(), 0) for w in _words(s))
        scored.append((score, -i, s))
    scored.sort(reverse=True)
    chosen = sorted(scored[:max_sentences], key=lambda t: -t[1])
    return " ".join(t[2] for t in chosen)


def offline_keywords(text: str, *, k: int = 8) -> list[str]:
    freq: dict[str, int] = {}
    for w in _words(text.lower()):
        if w in _STOP or len(w) < 4:
            continue
        freq[w] = freq.get(w, 0) + 1
    return [w for w, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[:k]]


def offline_rewrite(text: str) -> str:
    sents = _sentences(text)
    if not sents:
        return ""
    out = []
    for s in sents:
        s2 = re.sub(r"\s+", " ", s).strip()
        if s2.endswith("."):
            s2 = s2[:-1]
        out.append(f"Präziser: {s2}.")
    return " ".join(out)


def offline_translate(text: str, *, target: str = "en") -> str:
    tgt = (target or "en").lower()
    table = _DE_EN if tgt.startswith("en") else _EN_DE
    words = re.split(r"(\s+|[.,;:!?])", text or "")
    mapped = []
    for w in words:
        key = w.lower()
        if key in table:
            repl = table[key]
            mapped.append(repl.capitalize() if w[:1].isupper() else repl)
        else:
            mapped.append(w)
    note = " [Offline-Übersetzung, Wortliste — kein neuronales Modell]"
    return "".join(mapped) + note


def offline_toc(text: str) -> str:
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    items: list[str] = []
    for ln in lines:
        if ln.startswith("#"):
            items.append(ln.lstrip("# ").strip())
        elif re.match(r"^\d+[\.)]\s+\S+", ln):
            items.append(re.sub(r"^\d+[\.)]\s+", "", ln))
        elif ln.isupper() and 4 <= len(ln) <= 80:
            items.append(ln.title())
        elif re.match(r"^(Kapitel|Chapter|Abschnitt|Teil)\b", ln, re.I):
            items.append(ln)
    if not items:
        # first short lines as heading candidates
        for ln in lines:
            if 8 <= len(ln) <= 60 and not ln.endswith("."):
                items.append(ln)
            if len(items) >= 8:
                break
    if not items:
        kws = offline_keywords(text, k=5)
        items = [f"Abschnitt: {w}" for w in kws] or ["(kein Inhaltsverzeichnis erkennbar)"]
    return "\n".join(f"{i}. {t}" for i, t in enumerate(items[:12], 1))


def _offline(req: KiRequest) -> KiResult:
    act = (req.action or "summarize").lower()
    if act in ("zusammenfassen", "summary"):
        act = "summarize"
    if act in ("umformulieren", "rewrite", "rephrase"):
        act = "rewrite"
    if act in ("übersetzen", "translate"):
        act = "translate"
    if act in ("toc", "inhaltsverzeichnis"):
        act = "toc"
    text = req.text or ""
    if act == "rewrite":
        out = offline_rewrite(text)
    elif act == "translate":
        out = offline_translate(text, target=req.target_lang)
    elif act == "toc":
        out = offline_toc(text)
    else:
        out = offline_summarize(text)
        act = "summarize"
    kws = offline_keywords(text)
    return KiResult(
        ok=True,
        action=act,
        text=out,
        degraded=True,
        backend="offline",
        message="Ohne API-Schlüssel: lokaler Offline-Modus (einfache Algorithmen, kein LLM).",
        extra={"keywords": kws},
    )


def _chat_prompt(req: KiRequest) -> list[dict[str, str]]:
    act = req.action
    lang = req.target_lang or "en"
    if act == "summarize":
        instr = "Fasse den Text knapp auf Deutsch zusammen (3–5 Sätze)."
    elif act == "rewrite":
        instr = "Formuliere den Text klarer und professioneller um, Inhalt behalten."
    elif act == "translate":
        instr = f"Übersetze den Text nach {lang}. Nur die Übersetzung ausgeben."
    else:
        instr = "Erzeuge ein nummeriertes Inhaltsverzeichnis aus den Überschriften/Themen des Texts."
    return [
        {"role": "system", "content": "Du bist der KI-Assistent in InstantLens Doc. Antworte knapp."},
        {"role": "user", "content": instr + "\n\n" + (req.text or "")},
    ]


def _remote(req: KiRequest) -> KiResult:
    endpoint = (req.endpoint or "").rstrip("/")
    if not endpoint.endswith("/chat/completions"):
        endpoint = endpoint + "/chat/completions"
    payload = {
        "model": req.model or "gpt-4o-mini",
        "messages": _chat_prompt(req),
        "temperature": 0.3,
    }
    headers = {"Content-Type": "application/json"}
    if req.api_key:
        headers["Authorization"] = f"Bearer {req.api_key}"
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        text = (
            (((raw.get("choices") or [{}])[0].get("message") or {}).get("content"))
            or ""
        ).strip()
        if not text:
            raise ValueError("leere Antwort")
        return KiResult(
            ok=True,
            action=req.action,
            text=text,
            degraded=False,
            backend="openai-compatible",
            message="",
            extra={"model": req.model},
        )
    except Exception as exc:
        off = _offline(req)
        off.message = f"Remote fehlgeschlagen ({exc}); Offline-Modus."
        return off


def run_ki_action(
    action: str,
    text: str,
    *,
    target_lang: str = "en",
    endpoint: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> KiResult:
    cfg = get_ki_settings()
    req = KiRequest(
        action=action,
        text=text or "",
        target_lang=target_lang,
        endpoint=endpoint if endpoint is not None else cfg["endpoint"],
        api_key=api_key if api_key is not None else cfg["api_key"],
        model=model if model is not None else cfg["model"],
    )
    if not (req.text or "").strip():
        return KiResult(
            ok=False,
            action=req.action,
            text="",
            degraded=True,
            backend="offline",
            message="Kein Text ausgewählt.",
        )
    if req.endpoint and req.api_key:
        return _remote(req)
    return _offline(req)
