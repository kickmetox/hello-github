"""Lokale Einstellungen. Der API-Schlüssel liegt nur in der Nutzerdatei."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def config_dir() -> Path:
    path = Path.home() / ".shatuide"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return config_dir() / "config.json"


def load() -> dict[str, Any]:
    path = config_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save(data: dict[str, Any]) -> None:
    path = config_path()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def public_view(data: dict[str, Any]) -> dict[str, Any]:
    view = dict(data)
    key = str(view.get("api_key") or "")
    view["has_api_key"] = bool(key)
    view["api_key"] = "••••••••" if key else ""
    return view
