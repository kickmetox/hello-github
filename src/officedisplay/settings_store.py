from __future__ import annotations
from pathlib import Path

def load_secrets() -> dict:
    return {}

def save_secrets(_data: dict) -> None:
    return None

def media_folder(anchor: Path | None) -> Path:
    if anchor is None:
        folder = Path.home() / ".config" / "officedisplay" / "media"
    else:
        folder = Path(str(anchor.with_suffix("")) + "_media")
    folder.mkdir(parents=True, exist_ok=True)
    return folder
