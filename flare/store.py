"""SQLite-Katalog. Präfix über den B-Tree, Teilstrings über FTS5-Trigramme."""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from flare.paths import sqlite_uri

SCHEMA = """
DROP TABLE IF EXISTS content_fts;
DROP TABLE IF EXISTS items_fts;
DROP TABLE IF EXISTS content;
DROP TABLE IF EXISTS items;
DROP TABLE IF EXISTS dirs;

CREATE TABLE items (
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL,
  name TEXT NOT NULL,
  name_fold TEXT NOT NULL,
  path TEXT NOT NULL UNIQUE,
  dir TEXT NOT NULL,
  ext TEXT NOT NULL DEFAULT '',
  launch TEXT,
  mtime_ns INTEGER NOT NULL DEFAULT 0,
  size INTEGER NOT NULL DEFAULT 0,
  tier INTEGER NOT NULL DEFAULT 2,
  used_at INTEGER NOT NULL DEFAULT 0,
  use_count INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX items_name_fold ON items(name_fold);
CREATE INDEX items_dir ON items(dir);

CREATE VIRTUAL TABLE items_fts USING fts5(
  name, path,
  content='items', content_rowid='id',
  tokenize='trigram case_sensitive 0'
);

CREATE TRIGGER items_ai AFTER INSERT ON items BEGIN
  INSERT INTO items_fts(rowid, name, path) VALUES (new.id, new.name, new.path);
END;
CREATE TRIGGER items_ad AFTER DELETE ON items BEGIN
  INSERT INTO items_fts(items_fts, rowid, name, path)
  VALUES ('delete', old.id, old.name, old.path);
END;
CREATE TRIGGER items_au AFTER UPDATE OF name, path ON items BEGIN
  INSERT INTO items_fts(items_fts, rowid, name, path)
  VALUES ('delete', old.id, old.name, old.path);
  INSERT INTO items_fts(rowid, name, path) VALUES (new.id, new.name, new.path);
END;

CREATE TABLE content (
  item_id INTEGER PRIMARY KEY REFERENCES items(id) ON DELETE CASCADE,
  text TEXT NOT NULL
);
CREATE VIRTUAL TABLE content_fts USING fts5(
  text,
  content='content', content_rowid='item_id',
  tokenize='trigram case_sensitive 0'
);
CREATE TRIGGER content_ai AFTER INSERT ON content BEGIN
  INSERT INTO content_fts(rowid, text) VALUES (new.item_id, new.text);
END;
CREATE TRIGGER content_ad AFTER DELETE ON content BEGIN
  INSERT INTO content_fts(content_fts, rowid, text)
  VALUES ('delete', old.item_id, old.text);
END;
CREATE TRIGGER content_au AFTER UPDATE OF text ON content BEGIN
  INSERT INTO content_fts(content_fts, rowid, text)
  VALUES ('delete', old.item_id, old.text);
  INSERT INTO content_fts(rowid, text) VALUES (new.item_id, new.text);
END;

CREATE TABLE dirs (
  path TEXT PRIMARY KEY,
  parent TEXT NOT NULL,
  mtime_ns INTEGER NOT NULL,
  tier INTEGER NOT NULL,
  dirty INTEGER NOT NULL DEFAULT 0,
  readdir_ns INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX dirs_parent ON dirs(parent);
"""

ITEM_COLS = "id, kind, name, path, dir, ext, launch, tier, used_at, use_count"


def _show_in_empty(name: str) -> bool:
    return sum(char.isalpha() for char in name) >= 2


def like_pattern(prefix: str) -> str:
    out: list[str] = []
    for char in prefix:
        if char in ("%", "_", "!"):
            out.append("!")
        out.append(char)
    out.append("%")
    return "".join(out)


class Index:
    def __init__(self, path: str | Path, readonly: bool = False) -> None:
        self.path = Path(path)
        self.readonly = readonly
        self.lock = threading.RLock()
        if readonly:
            self.con = sqlite3.connect(
                sqlite_uri(self.path, "ro"),
                uri=True,
                check_same_thread=False,
                timeout=3,
            )
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.con = sqlite3.connect(
                self.path,
                check_same_thread=False,
                timeout=5,
            )
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA foreign_keys=ON")
        self.con.execute("PRAGMA busy_timeout=4000")
        self.con.execute("PRAGMA case_sensitive_like=ON")
        if not readonly:
            self.con.execute("PRAGMA journal_mode=WAL")
            self.con.execute("PRAGMA synchronous=NORMAL")
            self.con.execute("PRAGMA temp_store=MEMORY")
            self.con.execute("PRAGMA cache_size=-16000")
            self.con.execute("PRAGMA mmap_size=67108864")
            self.con.execute("PRAGMA case_sensitive_like=ON")
            self._migrate()
            self.con.execute(
                "CREATE TEMP TABLE IF NOT EXISTS flare_seen(path TEXT PRIMARY KEY)"
            )

    def close(self) -> None:
        with self.lock:
            self.con.close()

    def _migrate(self) -> None:
        version = self.con.execute("PRAGMA user_version").fetchone()[0]
        if version == 2:
            return
        self.con.executescript(SCHEMA)
        self.con.execute("PRAGMA user_version=2")
        self.con.commit()

    def _all(self, sql: str, args: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.lock:
            return [dict(row) for row in self.con.execute(sql, args).fetchall()]

    def reconcile_dir(
        self,
        directory: str,
        parent: str,
        mtime_ns: int,
        tier: int,
        items: list[dict[str, Any]],
        child_dirs: list[str],
    ) -> None:
        with self.lock:
            self.con.execute("BEGIN IMMEDIATE")
            try:
                deduped: dict[str, dict[str, Any]] = {}
                for item in items:
                    deduped[item["path"]] = item
                items = list(deduped.values())
                self._upsert_items(items)
                self.con.execute("DELETE FROM flare_seen")
                seen = [(item["path"],) for item in items]
                if seen:
                    self.con.executemany(
                        "INSERT OR IGNORE INTO flare_seen(path) VALUES (?)", seen
                    )
                self.con.execute(
                    "DELETE FROM items WHERE dir=? AND path NOT IN (SELECT path FROM flare_seen)",
                    (directory,),
                )
                old_children = {
                    row[0]
                    for row in self.con.execute(
                        "SELECT path FROM dirs WHERE parent=?", (directory,)
                    )
                }
                for gone in old_children.difference(child_dirs):
                    self._delete_tree(gone)
                for child in child_dirs:
                    self.con.execute(
                        """
                        INSERT INTO dirs(path, parent, mtime_ns, tier, dirty)
                        VALUES (?, ?, 0, ?, 1)
                        ON CONFLICT(path) DO UPDATE SET
                          parent=excluded.parent,
                          tier=MIN(dirs.tier, excluded.tier)
                        """,
                        (child, directory, tier),
                    )
                self.con.execute(
                    """
                    INSERT INTO dirs(path, parent, mtime_ns, tier, dirty, readdir_ns)
                    VALUES (?, ?, ?, ?, 0, ?)
                    ON CONFLICT(path) DO UPDATE SET
                      parent=excluded.parent,
                      mtime_ns=excluded.mtime_ns,
                      tier=MIN(dirs.tier, excluded.tier),
                      dirty=0,
                      readdir_ns=excluded.readdir_ns
                    """,
                    (directory, parent, mtime_ns, tier, time.time_ns()),
                )
                self.con.commit()
            except Exception:
                self.con.rollback()
                raise

    def _upsert_items(self, items: list[dict[str, Any]]) -> None:
        for item in items:
            self.con.execute(
                """
                INSERT INTO items(
                  kind, name, name_fold, path, dir, ext, launch, mtime_ns, size, tier
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                  kind=excluded.kind,
                  name=excluded.name,
                  name_fold=excluded.name_fold,
                  dir=excluded.dir,
                  ext=excluded.ext,
                  launch=excluded.launch,
                  mtime_ns=excluded.mtime_ns,
                  size=excluded.size,
                  tier=MIN(items.tier, excluded.tier)
                WHERE items.mtime_ns != excluded.mtime_ns
                   OR items.size != excluded.size
                   OR items.name != excluded.name
                   OR items.kind != excluded.kind
                   OR IFNULL(items.launch, '') != IFNULL(excluded.launch, '')
                   OR items.tier != excluded.tier
                """,
                (
                    item["kind"],
                    item["name"],
                    item["name"].casefold(),
                    item["path"],
                    item["dir"],
                    item.get("ext") or "",
                    item.get("launch"),
                    int(item.get("mtime_ns") or 0),
                    int(item.get("size") or 0),
                    int(item["tier"]),
                ),
            )

    def _delete_tree(self, path: str) -> None:
        import os

        prefix = like_pattern(path + os.sep)
        self.con.execute(
            "DELETE FROM items WHERE path=? OR dir=? OR dir LIKE ? ESCAPE '!'",
            (path, path, prefix),
        )
        self.con.execute(
            "DELETE FROM dirs WHERE path=? OR path LIKE ? ESCAPE '!'",
            (path, prefix),
        )

    def set_content(self, path: str, text: str) -> None:
        with self.lock:
            row = self.con.execute("SELECT id FROM items WHERE path=?", (path,)).fetchone()
            if row is None:
                return
            self.con.execute(
                """
                INSERT INTO content(item_id, text) VALUES (?, ?)
                ON CONFLICT(item_id) DO UPDATE SET text=excluded.text
                WHERE content.text != excluded.text
                """,
                (row[0], text),
            )
            self.con.commit()

    def dir_info(self, path: str) -> tuple[int | None, bool, int]:
        with self.lock:
            row = self.con.execute(
                "SELECT mtime_ns, dirty, readdir_ns FROM dirs WHERE path=?", (path,)
            ).fetchone()
        if row is None:
            return None, True, 0
        return int(row["mtime_ns"]), bool(row["dirty"]), int(row["readdir_ns"])

    def knows_dir(self, path: str) -> bool:
        with self.lock:
            row = self.con.execute("SELECT 1 FROM dirs WHERE path=?", (path,)).fetchone()
        return row is not None

    def child_dirs(self, path: str) -> list[str]:
        rows = self._all("SELECT path FROM dirs WHERE parent=? ORDER BY path", (path,))
        return [row["path"] for row in rows]

    def mark_dirty(self, path: str) -> None:
        with self.lock:
            self.con.execute("UPDATE dirs SET dirty=1 WHERE path=?", (path,))
            self.con.commit()

    def invalidate_all(self) -> None:
        with self.lock:
            self.con.execute("UPDATE dirs SET mtime_ns=0, dirty=1")
            self.con.commit()

    def prefix(self, folded: str, limit: int) -> list[dict[str, Any]]:
        return self._all(
            f"""
            SELECT {ITEM_COLS} FROM items
            WHERE name_fold LIKE ? ESCAPE '!'
            ORDER BY use_count DESC, length(name_fold) ASC, name_fold ASC
            LIMIT ?
            """,
            (like_pattern(folded), limit),
        )

    def fts(self, match: str, limit: int) -> list[dict[str, Any]]:
        with self.lock:
            try:
                rows = self.con.execute(
                    f"""
                    SELECT {ITEM_COLS} FROM items
                    WHERE id IN (SELECT rowid FROM items_fts WHERE items_fts MATCH ? LIMIT ?)
                    """,
                    (match, limit),
                ).fetchall()
            except sqlite3.OperationalError:
                return []
        return [dict(row) for row in rows]

    def content_hits(self, match: str, limit: int) -> list[tuple[dict[str, Any], str]]:
        with self.lock:
            try:
                rows = self.con.execute(
                    f"""
                    SELECT {", ".join("i." + col for col in ITEM_COLS.split(", "))}, c.text AS snippet
                    FROM content_fts
                    JOIN content c ON c.item_id = content_fts.rowid
                    JOIN items i ON i.id = c.item_id
                    WHERE content_fts MATCH ?
                    LIMIT ?
                    """,
                    (match, limit),
                ).fetchall()
            except sqlite3.OperationalError:
                return []
        out: list[tuple[dict[str, Any], str]] = []
        for row in rows:
            item = dict(row)
            text = str(item.pop("snippet", "") or "")
            out.append((item, text))
        return out

    def get(self, item_id: int) -> dict[str, Any] | None:
        rows = self._all(f"SELECT {ITEM_COLS} FROM items WHERE id=?", (item_id,))
        return rows[0] if rows else None

    def record_use(self, item_id: int, used_at: int) -> None:
        with self.lock:
            self.con.execute(
                "UPDATE items SET use_count=use_count+1, used_at=? WHERE id=?",
                (used_at, item_id),
            )
            self.con.commit()

    def recent(self, limit: int) -> list[dict[str, Any]]:
        rows = self._all(
            f"""
            SELECT {ITEM_COLS} FROM items
            WHERE use_count > 0
            ORDER BY used_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        if rows:
            return rows
        desktop = [
            row
            for row in self._all(
                f"""
                SELECT {ITEM_COLS} FROM items
                WHERE kind='app' AND dir != ':path'
                ORDER BY name_fold ASC
                LIMIT 200
                """
            )
            if _show_in_empty(row["name"])
        ]
        files = self._all(
            f"""
            SELECT {ITEM_COLS} FROM items
            WHERE kind != 'app' AND tier <= 1
            ORDER BY kind='dir' DESC, name_fold ASC
            LIMIT ?
            """,
            (limit,),
        )
        picked = desktop[:limit]
        have = {row["id"] for row in picked}
        for row in files:
            if len(picked) >= limit:
                break
            if row["id"] not in have:
                picked.append(row)
        if picked:
            return picked
        named = [
            row
            for row in self._all(
                f"""
                SELECT {ITEM_COLS} FROM items
                WHERE kind='app' AND dir=':path'
                ORDER BY name_fold ASC
                LIMIT 80
                """
            )
            if _show_in_empty(row["name"])
        ]
        return named[:limit]

    def counts(self) -> dict[str, int]:
        with self.lock:
            items = self.con.execute("SELECT COUNT(*) FROM items").fetchone()[0]
            dirs = self.con.execute("SELECT COUNT(*) FROM dirs").fetchone()[0]
        return {"items": int(items), "dirs": int(dirs)}

    def checkpoint(self) -> None:
        with self.lock:
            self.con.execute("PRAGMA wal_checkpoint(PASSIVE)")
