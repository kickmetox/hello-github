"""GitHub-Anmeldung und Editor-Profile für VS Code und Visual Studio.

Schlüssel bleiben in der Nutzerkonfiguration. Die Workspace-Datei
`.vscode/shatuide.ai.json` enthält nur Anbieter, Modell und Erweiterungspfade.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

_MARKET = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,120}$")
_HOSTS = {"github.com", "www.github.com"}

PROVIDERS: list[dict] = [
    {
        "id": "ollama",
        "name": "Ollama (lokal)",
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "llama3.1",
        "key_hint": "Bei Ollama leer lassen",
        "docs": "https://github.com/ollama/ollama/blob/main/docs/openai.md",
        "note": "Lokales OpenAI-kompatibles Modell. Basis-URL ohne /chat/completions.",
    },
    {
        "id": "kimi",
        "name": "Kimi (Moonshot)",
        "base_url": "https://api.moonshot.ai/v1",
        "model": "kimi-k3",
        "key_hint": "Moonshot-API-Schlüssel",
        "docs": "https://platform.kimi.ai/docs/api/quickstart",
        "note": "OpenAI-kompatible Kimi-API. Dieselbe Schlüsselart kann Kimi Code in VS Code verwenden.",
    },
    {
        "id": "gemini",
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-flash-latest",
        "key_hint": "Gemini-API-Schlüssel aus Google AI Studio",
        "docs": "https://ai.google.dev/gemini-api/docs/openai",
        "note": "OpenAI-kompatible Gemini-API. Gemini Code Assist in VS Code meldet sich zusätzlich mit dem Google-Konto an.",
    },
    {
        "id": "openai",
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "key_hint": "OpenAI-API-Schlüssel",
        "docs": "https://platform.openai.com/docs/api-reference",
        "note": "Auch der Endpunkt, den Code GPT nutzt, wenn dort OpenAI als Anbieter gewählt ist.",
    },
    {
        "id": "custom",
        "name": "OpenAI-kompatibel (eigener Endpunkt)",
        "base_url": "",
        "model": "",
        "key_hint": "API-Schlüssel des Anbieters",
        "docs": "https://docs.codegpt.co/docs/tutorial-ai-providers/custom",
        "note": "Für Code-GPT-Custom, Azure, Groq und andere Dienste. Die Basis-URL endet vor /chat/completions.",
    },
]

EXTENSIONS: list[dict] = [
    {
        "id": "kimi",
        "name": "Kimi Code",
        "style": "Agent",
        "vscode": ["moonshot-ai.kimi-code"],
        "note": "Chat, Projektkontext mit @, Diff-Übernahme und MCP in VS Code.",
    },
    {
        "id": "copilot",
        "name": "GitHub Copilot",
        "style": "Inline",
        "vscode": ["GitHub.copilot", "GitHub.copilot-chat"],
        "note": "Anmeldung in VS Code oder Visual Studio mit dem GitHub-Konto. ShatuIDE nutzt das Token nur für Git über HTTPS.",
    },
    {
        "id": "tabnine",
        "name": "Tabnine",
        "style": "Autocomplete",
        "vscode": ["TabNine.tabnine-vscode"],
        "note": "Vorschläge und Datenschutzoptionen werden in der Erweiterung selbst eingestellt.",
    },
    {
        "id": "bito",
        "name": "Bito AI",
        "style": "Review",
        "vscode": ["Bito.Bito"],
        "note": "Erklärungen, Reviews und Generierung laufen in der Bito-Erweiterung.",
    },
    {
        "id": "mintlify",
        "name": "Mintlify Doc Writer",
        "style": "Dokumentation",
        "vscode": ["mintlify.document"],
        "note": "Dokumentation aus markiertem Code, direkt in VS Code.",
    },
    {
        "id": "codegpt",
        "name": "Code GPT",
        "style": "Chat",
        "vscode": ["DanielSanMedium.dscodegpt"],
        "note": "In VS Code denselben OpenAI-kompatiblen Endpunkt eintragen wie hier unter Anbieter.",
    },
    {
        "id": "windsurf",
        "name": "Windsurf (Codeium)",
        "style": "Begleiter",
        "vscode": ["Codeium.codeium"],
        "visual_studio": ["Codeium.CodeiumVS"],
        "note": "Die VS-Code-Erweiterung heißt Windsurf Plugin. Für Visual Studio gibt es Codeium.CodeiumVS.",
    },
    {
        "id": "qodo",
        "name": "Qodo Gen",
        "style": "Review",
        "vscode": ["Codium.codium"],
        "note": "Die Marketplace-Seite nennt den 30. Oktober 2026 als Ende dieser IDE-Erweiterung.",
    },
    {
        "id": "gemini-assist",
        "name": "Google Gemini Code Assist",
        "style": "Pair-Programming",
        "vscode": ["Google.geminicodeassist"],
        "note": "Editor-Anmeldung über das Google-Konto. Die Gemini-API oben ist davon getrennt konfigurierbar.",
    },
]


def provider_by_id(provider_id: str) -> dict | None:
    for item in PROVIDERS:
        if item["id"] == provider_id:
            return item
    return None


def extension_by_id(extension_id: str) -> dict | None:
    for item in EXTENSIONS:
        if item["id"] == extension_id:
            return item
    return None


def marketplace_ids(extension_ids: list[str], field: str = "vscode") -> list[str]:
    found: list[str] = []
    for extension_id in extension_ids:
        item = extension_by_id(extension_id)
        if not item:
            continue
        for market_id in item.get(field, []):
            if _MARKET.match(market_id) and market_id not in found:
                found.append(market_id)
    return found


def github_host(url: str) -> bool:
    text = (url or "").strip()
    if text.startswith("git@github.com:"):
        return True
    if "://" not in text:
        return False
    host = (urlparse(text).hostname or "").lower()
    return host in _HOSTS


def with_github_auth(env: dict, token: str, urls: list[str]) -> dict:
    """Setzt den Authorization-Header nur für github.com und nur für diesen Prozess."""
    cleaned = (token or "").strip()
    if not cleaned or any(char.isspace() for char in cleaned) or len(cleaned) > 400:
        return env
    if not any(github_host(url) for url in urls):
        return env
    updated = dict(env)
    updated["GIT_CONFIG_COUNT"] = "1"
    updated["GIT_CONFIG_KEY_0"] = "http.https://github.com/.extraheader"
    updated["GIT_CONFIG_VALUE_0"] = "AUTHORIZATION: bearer " + cleaned
    return updated


def github_user(token: str, timeout: int = 20) -> dict:
    cleaned = (token or "").strip()
    if not cleaned or any(char.isspace() for char in cleaned) or len(cleaned) > 400:
        return {"ok": False, "error": "GitHub-Token fehlt oder enthält ungültige Zeichen."}
    request = urllib.request.Request(
        "https://api.github.com/user",
        headers={
            "Authorization": "Bearer " + cleaned,
            "Accept": "application/vnd.github+json",
            "User-Agent": "ShatuIDE",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read(500).decode("utf-8", errors="replace")
        return {"ok": False, "error": f"GitHub HTTP {exc.code}: {detail[:300]}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    if not isinstance(data, dict):
        return {"ok": False, "error": "Unerwartete GitHub-Antwort."}
    return {"ok": True, "login": str(data.get("login") or ""), "name": str(data.get("name") or "")}


def _configured_path(value: str) -> str:
    text = str(value or "").strip()
    if not text or any(char in text for char in "\r\n\x00"):
        return ""
    if Path(text).is_absolute() or re.match(r"^[A-Za-z]:[\\/]", text):
        return text
    return ""


def editor_binary(kind: str, configured: str = "") -> str:
    override = _configured_path(configured)
    if override and Path(override).is_file():
        return override
    names = {
        "vscode": ("code", "code-insiders"),
        "visualstudio": ("devenv",),
        "windsurf": ("windsurf",),
    }
    for name in names.get(kind, ()):
        found = shutil.which(name)
        if found:
            return found
    return override


def editor_status(cfg: dict) -> dict:
    status = {}
    for kind, key in (
        ("vscode", "editor_vscode"),
        ("visualstudio", "editor_visualstudio"),
        ("windsurf", "editor_windsurf"),
    ):
        configured = str(cfg.get(key) or "")
        binary = editor_binary(kind, configured)
        status[kind] = {
            "configured": configured,
            "path": binary,
            "found": bool(binary and Path(binary).is_file()),
        }
    return status


def safe_editor_path(value: str) -> str:
    return _configured_path(value)


def known_extension_ids(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    chosen: list[str] = []
    for item in values:
        extension_id = str(item or "")
        if extension_by_id(extension_id) and extension_id not in chosen:
            chosen.append(extension_id)
    return chosen


def write_editor_config(workspace: Path, extension_ids: list[str], profile: dict) -> dict:
    folder = workspace / ".vscode"
    folder.mkdir(parents=True, exist_ok=True)
    ext_path = folder / "extensions.json"
    current: dict = {}
    if ext_path.is_file():
        try:
            loaded = json.loads(ext_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                current = loaded
        except (OSError, json.JSONDecodeError):
            current = {}
    recommendations = [str(item) for item in current.get("recommendations") or [] if isinstance(item, str)]
    for market_id in marketplace_ids(extension_ids):
        if market_id not in recommendations:
            recommendations.append(market_id)
    current["recommendations"] = recommendations
    ext_path.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    exported = {
        "provider": str(profile.get("provider") or ""),
        "base_url": str(profile.get("base_url") or ""),
        "model": str(profile.get("model") or ""),
        "system_prompt": str(profile.get("system_prompt") or ""),
        "extensions": known_extension_ids(extension_ids),
        "marketplace": marketplace_ids(extension_ids, "vscode"),
        "visual_studio": marketplace_ids(extension_ids, "visual_studio"),
        "github_configured": bool(profile.get("has_github_token")),
    }
    profile_path = folder / "shatuide.ai.json"
    profile_path.write_text(json.dumps(exported, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "extensions": str(ext_path),
        "profile": str(profile_path),
        "recommendations": recommendations,
    }


def open_editor(kind: str, workspace: Path, configured: str = "") -> dict:
    binary = editor_binary(kind, configured)
    if not binary or not Path(binary).is_file():
        names = {"vscode": "Visual Studio Code", "visualstudio": "Visual Studio", "windsurf": "Windsurf"}
        return {"ok": False, "error": f"{names.get(kind, 'Editor')} wurde nicht gefunden. Pfad in der Konfiguration eintragen."}
    subprocess.Popen([binary, str(workspace)], start_new_session=True)
    return {"ok": True, "path": binary}


def install_extensions(code_binary: str, extension_ids: list[str]) -> dict:
    if not code_binary or not Path(code_binary).is_file():
        return {"ok": False, "error": "Visual Studio Code (Befehl code) wurde nicht gefunden."}
    vscode_only = marketplace_ids(extension_ids, "vscode")
    if not vscode_only:
        return {"ok": False, "error": "Keine VS-Code-Erweiterung ausgewählt."}
    lines: list[str] = []
    failed = False
    for market_id in vscode_only:
        if not _MARKET.match(market_id):
            continue
        try:
            proc = subprocess.run(
                [code_binary, "--install-extension", market_id],
                capture_output=True,
                text=True,
                timeout=90,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            failed = True
            lines.append(f"{market_id}: {exc}")
            continue
        text = ((proc.stdout or "") + (proc.stderr or "")).strip()
        lines.append(f"{market_id}: {text[:500] or proc.returncode}")
        if proc.returncode != 0:
            failed = True
    log = "\n".join(lines) or "Keine Ausgabe."
    if failed:
        log += "\nMindestens eine Installation ist fehlgeschlagen."
    return {"ok": True, "log": log, "failed": failed}
