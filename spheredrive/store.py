"""JSON-Konfiguration der von SphereDrive verwalteten Zuordnungen."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULTS: dict[str, Any] = {
    "version": 1,
    "subst": [],
    "net": [],
    "shares": [],
    "links": [],
    "psdrives": [],
    "mounts": [],
    "settings": {
        "autostart": True,
        "elevated_task": False,
        "linked_connections": False,
    },
}


class Store:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.data = deepcopy(DEFAULTS)
        if self.path.is_file():
            self.load()

    def load(self) -> None:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        data = deepcopy(DEFAULTS)
        if isinstance(raw, dict):
            for key in ("version", "subst", "net", "shares", "links", "psdrives", "mounts"):
                if key in raw:
                    data[key] = raw[key]
            if isinstance(raw.get("settings"), dict):
                data["settings"] = {**DEFAULTS["settings"], **raw["settings"]}
        self.data = data

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.data, indent=2, ensure_ascii=False) + "\n"
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(self.path)
