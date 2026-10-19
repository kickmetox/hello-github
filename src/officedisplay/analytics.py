from __future__ import annotations

import json
import time
from pathlib import Path


class DwellLog:
    def __init__(self) -> None:
        self.events: list[dict] = []
        self._index: int | None = None
        self._started = 0.0

    def enter(self, index: int) -> None:
        self.leave()
        self._index = index
        self._started = time.time()

    def leave(self) -> None:
        if self._index is None:
            return
        self.events.append({"slide": self._index, "seconds": round(time.time() - self._started, 2)})
        self._index = None

    def save(self, path: str | Path) -> None:
        self.leave()
        target = Path(path)
        target.write_text(json.dumps({"events": self.events}, indent=2), encoding="utf-8")
