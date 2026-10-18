"""Ablage für Profile, die nur Daten sind (Undervolt, Ladeschwelle)."""

from __future__ import annotations

import os
from pathlib import Path


def state_path() -> Path:
    override = os.environ.get("CROSSOS_STATE")
    if override:
        return Path(override)
    return Path.home() / ".local" / "share" / "crossos" / "state.json"
