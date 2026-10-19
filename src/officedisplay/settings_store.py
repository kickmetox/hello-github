from __future__ import annotations

import json
from pathlib import Path

from officedisplay.paths import secrets_path


def load_secrets() -> dict:
    path = secrets_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def save_secrets(data: dict) -> None:
    path = secrets_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    path.chmod(0o600)


def media_folder(anchor: Path | None) -> Path:
    if anchor is None:
        folder = Path.home() / ".config" / "officedisplay" / "media"
    else:
        folder = Path(str(anchor.with_suffix("")) + "_media")
    folder.mkdir(parents=True, exist_ok=True)
    return folder
