from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass


class OnlineAIError(Exception):
    pass


@dataclass
class OnlineAISettings:
    enabled: bool = False
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    image_model: str = "dall-e-3"
    allow_images: bool = False


def validate_endpoint(url: str) -> None:
    low = (url or "").strip().lower()
    if low.startswith("https://"):
        return
    if low.startswith("http://127.0.0.1") or low.startswith("http://localhost"):
        return
    raise OnlineAIError("Nur HTTPS oder http://127.0.0.1 bzw. http://localhost sind erlaubt.")


def chat_completion(settings: OnlineAISettings, messages: list[dict], timeout: float = 60, opener=None) -> str:
    if not settings.enabled:
        raise OnlineAIError("Online-KI ist ausgeschaltet. Einschalten erfolgt in den Einstellungen.")
    if not settings.api_key and "127.0.0.1" not in settings.base_url and "localhost" not in settings.base_url:
        raise OnlineAIError("Kein API-Schlüssel hinterlegt.")
    url = settings.base_url.rstrip("/") + "/chat/completions"
    validate_endpoint(url)
    payload = {"model": settings.model, "temperature": 0.3, "messages": messages}
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {settings.api_key}"},
        method="POST",
    )
    try:
        context = ssl.create_default_context()
        open_fn = opener or (lambda req, timeout=timeout: urllib.request.urlopen(req, timeout=timeout, context=context))
        with open_fn(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except OnlineAIError:
        raise
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise OnlineAIError(f"Online-KI hat HTTP {exc.code} geantwortet. {detail}") from exc
    except Exception as exc:
        raise OnlineAIError("Online-KI nicht erreichbar.") from exc
    try:
        data = json.loads(raw)
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise OnlineAIError("Antwort der Online-KI hat kein Chat-Format.") from exc


def extract_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned[: cleaned.rfind("```")]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end < start:
        raise OnlineAIError("Die Online-KI hat kein JSON geliefert.")
    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise OnlineAIError("JSON der Online-KI ist ungültig.") from exc


DECK_SYSTEM = (
    "Du erzeugst Präsentationsfolien als JSON. Erfinde keine Zahlen, Quellen oder Zitate. "
    'Schema: {"slides":[{"title":"","bullets":[""],"notes":""}]}. Antworte nur mit JSON.'
)


def draft_deck(settings: OnlineAISettings, prompt: str, opener=None) -> dict:
    content = chat_completion(
        settings,
        [{"role": "system", "content": DECK_SYSTEM}, {"role": "user", "content": prompt}],
        opener=opener,
    )
    data = extract_json(content)
    if "slides" not in data or not isinstance(data["slides"], list):
        raise OnlineAIError("JSON enthält keine Folienliste.")
    return data


def rewrite_text(settings: OnlineAISettings, text: str, instruction: str, opener=None) -> str:
    return chat_completion(
        settings,
        [
            {"role": "system", "content": "Forme den Text um. Erfinde keine Fakten. Antworte nur mit dem Text."},
            {"role": "user", "content": f"Anweisung: {instruction}\n\nText:\n{text}"},
        ],
        opener=opener,
    )


def generate_image(settings: OnlineAISettings, prompt: str, timeout: float = 90, opener=None) -> dict:
    if not settings.enabled or not settings.allow_images:
        raise OnlineAIError("Bildgenerierung ist ausgeschaltet.")
    url = settings.base_url.rstrip("/") + "/images/generations"
    validate_endpoint(url)
    payload = {"model": settings.image_model, "prompt": prompt, "size": "1024x1024"}
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {settings.api_key}"},
        method="POST",
    )
    open_fn = opener or (lambda req, timeout=timeout: urllib.request.urlopen(req, timeout=timeout))
    try:
        with open_fn(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        raise OnlineAIError("Bilddienst nicht erreichbar oder Format unbekannt.") from exc
