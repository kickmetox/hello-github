"""Chat, Inline-Edit und Agent über eine OpenAI-kompatible Schnittstelle (auch Ollama)."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

AGENT_SYSTEM = """Du bist der Coding-Agent von ShatuIDE und arbeitest nur im geöffneten Projekt.
Antworte ausschließlich mit einem JSON-Objekt, ohne Markdown.

Während der Arbeit:
{"done": false, "message": "kurzer Status auf Deutsch", "tool": "read_file", "args": {"path": "relativer/pfad.py"}}

Wenn das Ziel erreicht ist:
{"done": true, "message": "Zusammenfassung auf Deutsch"}

Werkzeuge, genau ein Aufruf pro Antwort:
- list_dir: args {path}
- read_file: args {path}
- write_file: args {path, content}
- search: args {query}
- pip_install: args {package}
- run_python: args {path}
- run_tests: args {}

Installiere fehlende Bibliotheken mit pip_install, führe Skripte mit run_python aus und korrigiere Fehler aus der Rückgabe.
Erfinde keine Dateiinhalte, die du nicht gelesen oder gerade geschrieben hast.
"""

CHAT_SYSTEM = """Du bist der Programmierassistent in ShatuIDE von Andreas Meyer.
Antworte auf Deutsch, präzise und mit lauffähigem Python, wenn Code gefragt ist.
Ändere nur, was die Aufgabe braucht.
"""


def extract_code(text: str) -> str:
    match = re.search(r"```(?:python|py)?\s*\n(.*?)```", text, re.S | re.I)
    if match:
        return match.group(1).strip("\n") + "\n"
    return text.strip("\n") + ("\n" if text.strip() else "")


def parse_agent_message(text: str) -> dict:
    raw = text.strip()
    fenced = re.search(r"```(?:json)?\s*\n(.*?)```", raw, re.S | re.I)
    if fenced:
        raw = fenced.group(1).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        raw = raw[start : end + 1]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"Keine JSON-Antwort: {exc}", "raw": text[:2000]}
    if not isinstance(data, dict):
        return {"ok": False, "error": "Antwort ist kein Objekt.", "raw": text[:2000]}
    data["ok"] = True
    return data


def chat_completion(base_url: str, api_key: str, model: str, messages: list[dict], timeout: int = 120) -> dict:
    if not base_url:
        return {
            "ok": False,
            "error": "Kein Sprachmodell konfiguriert. Unter KI → Einstellungen eine OpenAI-kompatible URL eintragen, zum Beispiel http://127.0.0.1:11434/v1 für Ollama.",
        }
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {"model": model or "gpt-4o", "messages": messages, "temperature": 0.2}
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read(4000).decode("utf-8", errors="replace")
        return {"ok": False, "error": f"HTTP {exc.code}: {detail[:800]}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return {"ok": False, "error": "Unerwartete Modellantwort.", "raw": json.dumps(data)[:800]}
    return {"ok": True, "content": content or ""}


def build_messages(system: str, history: list[dict], extra: str = "") -> list[dict]:
    content = system if not extra else system + "\n\nKontext:\n" + extra
    messages = [{"role": "system", "content": content}]
    for item in history[-20:]:
        role = item.get("role")
        if role in {"user", "assistant"} and item.get("content"):
            messages.append({"role": role, "content": str(item["content"])[:20000]})
    return messages
