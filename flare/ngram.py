"""Umgekehrter Trigramm-Index für die Ähnlichkeitssuche.

Ein Name landet unter jedem seiner Trigramme. Die Anfrage liest nur die
Listen der eigenen Trigramme und bewertet diese Kandidaten, nicht den
ganzen Katalog.
"""

from __future__ import annotations

import os
from typing import Any

from flare.rank import trigrams


class NameIndex:
    def __init__(self) -> None:
        self._post: dict[int, set[int]] = {}
        self._grams: dict[int, set[int]] = {}
        self._rows: dict[int, dict[str, Any]] = {}

    def load(self, rows: list[dict[str, Any]]) -> None:
        self._post.clear()
        self._grams.clear()
        self._rows.clear()
        for row in rows:
            self._set(row)

    def sync_dir(self, directory: str, rows: list[dict[str, Any]]) -> None:
        keep = {int(row["id"]) for row in rows}
        gone = [item_id for item_id, row in self._rows.items() if row.get("dir") == directory and item_id not in keep]
        for item_id in gone:
            self._remove(item_id)
        for row in rows:
            self._set(row)

    def drop_tree(self, path: str) -> None:
        prefix = path + os.sep
        gone = [
            item_id
            for item_id, row in self._rows.items()
            if row["path"] == path
            or row["dir"] == path
            or str(row["dir"]).startswith(prefix)
            or str(row["path"]).startswith(prefix)
        ]
        for item_id in gone:
            self._remove(item_id)

    def candidates(self, query: str, limit: int = 240) -> list[dict[str, Any]]:
        grams = trigrams(query)
        if len(grams) < 2:
            return []
        counts: dict[int, int] = {}
        for gram in grams:
            for item_id in self._post.get(gram, ()):
                counts[item_id] = counts.get(item_id, 0) + 1
        need = max(2, int(len(grams) * 0.34))
        ranked = [item_id for item_id, count in counts.items() if count >= need]
        ranked.sort(key=lambda item_id: counts[item_id], reverse=True)
        out: list[dict[str, Any]] = []
        for item_id in ranked[:limit]:
            row = self._rows.get(item_id)
            if row is not None:
                out.append(row)
        return out

    def _set(self, row: dict[str, Any]) -> None:
        item_id = int(row["id"])
        self._remove(item_id)
        grams = set(trigrams(str(row["name"])))
        self._grams[item_id] = grams
        self._rows[item_id] = row
        for gram in grams:
            self._post.setdefault(gram, set()).add(item_id)

    def _remove(self, item_id: int) -> None:
        grams = self._grams.pop(item_id, None)
        self._rows.pop(item_id, None)
        if not grams:
            return
        for gram in grams:
            bucket = self._post.get(gram)
            if bucket is None:
                continue
            bucket.discard(item_id)
            if not bucket:
                self._post.pop(gram, None)
