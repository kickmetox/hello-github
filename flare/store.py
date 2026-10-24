"""SQLite-Katalog. Präfix über den B-Tree, Teilstrings über FTS5-Trigramme."""

from __future__ import annotations

import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from flare.ngram import NameIndex
from flare.paths import child_prefix, norm, sqlite_uri

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


def has_whole_word(query: str, name: str) -> bool:
    """Die Anfrage ist ein ganzes Wort: Ränder sind Anfang, Ende oder kein Buchstabe und keine Ziffer."""
    needle = query.casefold().strip()
    folded = name.casefold()
    if not needle or needle not in folded:
        return False
    start = 0
    while True:
        at = folded.find(needle, start)
        if at < 0:
            return False
        before = at == 0 or not folded[at - 1].isalnum()
        after_at = at + len(needle)
        after = after_at >= len(folded) or not folded[after_at].isalnum()
        if before and after:
            return True
        start = at + 1


class Index:
    def __init__(self, path: str | Path, readonly: bool = False) -> None:
        self.path = Path(path)
        self.readonly = readonly
        self.lock = threading.RLock()
        self._open_connection()
        self.names = NameIndex()
        self._load_names()

    def _open_connection(self) -> None:
        if self.readonly:
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
        self.con.create_function(
            "flare_word",
            2,
            lambda name, query: 1 if has_whole_word(str(query or ""), str(name or "")) else 0,
        )
        if not self.readonly:
            self.con.execute("PRAGMA journal_mode=WAL")
            self.con.execute("PRAGMA synchronous=NORMAL")
            self.con.execute("PRAGMA temp_store=MEMORY")
            self.con.execute("PRAGMA cache_size=-65536")
            self.con.execute("PRAGMA mmap_size=268435456")
            self._migrate()
            self.con.execute(
                "CREATE TEMP TABLE IF NOT EXISTS flare_seen(path TEXT PRIMARY KEY)"
            )

    def close(self) -> None:
        with self.lock:
            if not self.readonly:
                try:
                    self.con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                except sqlite3.Error:
                    pass
            self.con.close()

    def _migrate(self) -> None:
        version = self.con.execute("PRAGMA user_version").fetchone()[0]
        if version == 2:
            return
        self.con.executescript(SCHEMA)
        self.con.execute("PRAGMA user_version=2")
        self.con.commit()

    def _load_names(self) -> None:
        rows = [dict(row) for row in self.con.execute(f"SELECT {ITEM_COLS} FROM items")]
        self.names.load(rows)

    def similar_candidates(self, query: str, limit: int = 240) -> list[dict[str, Any]]:
        with self.lock:
            return self.names.candidates(query, limit)

    def all_items(self, limit: int) -> list[dict[str, Any]]:
        return self._all(
            f"""
            SELECT {ITEM_COLS} FROM items
            ORDER BY use_count DESC, name_fold ASC
            LIMIT ?
            """,
            (max(0, int(limit)),),
        )

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
            gone_paths: list[str] = []
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
                gone_paths = list(old_children.difference(child_dirs))
                for gone in gone_paths:
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
            for gone in gone_paths:
                self.names.drop_tree(gone)
            current = [
                dict(row)
                for row in self.con.execute(
                    f"SELECT {ITEM_COLS} FROM items WHERE dir=?",
                    (directory,),
                )
            ]
            self.names.sync_dir(directory, current)

    def _upsert_items(self, items: list[dict[str, Any]]) -> None:
        if not items:
            return
        self.con.executemany(
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
            [
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
                )
                for item in items
            ],
        )

    def drop_tree(self, path: str) -> None:
        """Baum aus dem Katalog nehmen. Der Dateisystemstamm bleibt unangetastet."""
        path = norm(path)
        if not path or path == norm(os.sep):
            return
        with self.lock:
            self.con.execute("BEGIN IMMEDIATE")
            try:
                self._delete_tree(path)
                self.con.commit()
            except Exception:
                self.con.rollback()
                raise
            self.names.drop_tree(path)

    def _delete_tree(self, path: str) -> None:
        prefix = like_pattern(child_prefix(path))
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

    def exact(self, folded: str, limit: int) -> list[dict[str, Any]]:
        """Namen, die der Anfrage genau entsprechen. Unabhängig vom Präfix-Limit."""
        if not folded:
            return []
        return self._all(
            f"""
            SELECT {ITEM_COLS} FROM items
            WHERE name_fold = ?
            ORDER BY use_count DESC, length(path) ASC
            LIMIT ?
            """,
            (folded, max(0, int(limit))),
        )

    def prefix(self, folded: str, limit: int) -> list[dict[str, Any]]:
        return self._all(
            f"""
            SELECT {ITEM_COLS} FROM items
            WHERE name_fold LIKE ? ESCAPE '!'
            ORDER BY length(name_fold) ASC, use_count DESC, name_fold ASC
            LIMIT ?
            """,
            (like_pattern(folded), limit),
        )

    def contains(self, folded: str, limit: int) -> list[dict[str, Any]]:
        """Datei- und Ordnernamen, die die Anfrage irgendwo enthalten.

        `name_fold` ist bereits klein geschrieben, `case_sensitive_like` bleibt an.
        Das führende `%` sucht mitten im Namen, nicht nur am Anfang. Ein ganzes
        Wort steht vor einem Infix, damit Hash-Dateien kurze Treffer nicht verdrängen.
        Unabhängig von FTS5: Trigramm-Phrasen mit drei Zeichen sind unzuverlässig.
        """
        if len(folded) < 3:
            return []
        return self._all(
            f"""
            SELECT {ITEM_COLS} FROM items
            WHERE name_fold LIKE ? ESCAPE '!'
            ORDER BY flare_word(name_fold, ?) DESC,
                     use_count DESC,
                     length(name_fold) ASC,
                     name_fold ASC
            LIMIT ?
            """,
            ("%" + like_pattern(folded), folded, max(0, int(limit))),
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

    def backup(self, dest: str | Path) -> Path:
        """Konsistente Kopie über sqlite3.Connection.backup.

        Die laufende Datenbank bleibt an ihrem Ort. Es wird kein WAL roh kopiert.
        """
        target = Path(dest)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.resolve() == self.path.resolve():
            raise ValueError("Ziel ist der laufende Index")
        with self.lock:
            dest_con = sqlite3.connect(target)
            try:
                self.con.backup(dest_con)
                dest_con.commit()
            finally:
                dest_con.close()
        return target

    def replace_from(self, source: str | Path) -> Path:
        """Laufende Datei durch einen Snapshot ersetzen.

        Die Quelle bleibt liegen. Ein WAL wird nicht roh kopiert. Eine Datei
        ohne Flare-Index lässt diese Datenbank unverändert. Der Namensindex
        wird danach neu aus der Tabelle items geladen.
        """
        if self.readonly:
            raise ValueError("Laufender Index ist nur lesbar")
        src = Path(source)
        _require_index_file(src)
        if src.resolve() == self.path.resolve():
            raise ValueError("Quelle ist der laufende Index")
        with self.lock:
            self._install_snapshot(src)
        return self.path

    def _install_snapshot(self, src: Path) -> None:
        row = self.con.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if row is not None and int(row[0]) != 0:
            raise sqlite3.OperationalError("Checkpoint beschäftigt")
        self.con.close()
        try:
            _remove_sidecars(self.path)
            _backup_file_into(src, self.path)
            _remove_sidecars(self.path)
        except Exception:
            self._open_connection()
            self._load_names()
            raise
        self._open_connection()
        self._load_names()


def replace_live_index(index: Index, source: str | Path) -> Path:
    """Offenen Katalog durch eine Snapshot-Datei ersetzen. Die Quelle bleibt."""
    return index.replace_from(source)


def load_index_at(live: str | Path, source: str | Path) -> Path:
    """Indexdatei durch einen Snapshot ersetzen.

    Die Quelle wird geprüft, bevor die laufende Datei geöffnet oder angelegt
    wird. Dieselbe Ersetzung nutzt das Menü über replace_live_index.
    """
    src = Path(source)
    dest = Path(live)
    _require_index_file(src)
    if dest.exists() and dest.resolve() == src.resolve():
        raise ValueError("Quelle ist der laufende Index")
    index = Index(dest)
    try:
        replace_live_index(index, src)
    finally:
        index.close()
    return dest


def _require_index_file(path: Path) -> None:
    if not path.is_file():
        raise ValueError(f"Index fehlt: {path}")
    try:
        con = sqlite3.connect(sqlite_uri(path, "ro"), uri=True, timeout=3)
    except sqlite3.Error as exc:
        raise ValueError(f"Index lässt sich nicht öffnen: {path}") from exc
    try:
        try:
            row = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='items'"
            ).fetchone()
        except sqlite3.Error as exc:
            raise ValueError(f"Index lässt sich nicht öffnen: {path}") from exc
    finally:
        con.close()
    if row is None:
        raise ValueError(f"Index ohne Tabelle items: {path}")


def _remove_sidecars(path: Path) -> None:
    for suffix in ("-wal", "-shm"):
        sidecar = path.with_name(path.name + suffix)
        if sidecar.is_file():
            sidecar.unlink()


def _backup_file_into(source: Path, dest: Path) -> None:
    """Inhalt von source nach dest über sqlite3.Connection.backup schreiben.

    Es wird keine WAL-Datei roh kopiert. Das Ziel läuft dafür im
    Rollback-Journal, damit ein altes WAL beim Schließen nicht zurückgespielt
    wird.
    """
    src_con = sqlite3.connect(sqlite_uri(source, "ro"), uri=True, timeout=5)
    try:
        dest_con = sqlite3.connect(dest, timeout=5)
        try:
            dest_con.execute("PRAGMA journal_mode=DELETE").fetchone()
            src_con.backup(dest_con)
            dest_con.commit()
            dest_con.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        finally:
            dest_con.close()
    finally:
        src_con.close()


_COMPARE_SAMPLE = 20


def copy_index(source: str | Path, dest: str | Path) -> Path:
    """Konsistente Kopie einer Indexdatei über sqlite3.Connection.backup.

    Die Quelle wird nur gelesen und bleibt an ihrem Ort. Es wird kein WAL roh
    kopiert und nichts verschoben oder gelöscht.
    """
    src = Path(source)
    target = Path(dest)
    if not src.is_file():
        raise ValueError(f"Index fehlt: {src}")
    if target.resolve() == src.resolve():
        raise ValueError("Ziel ist die Quelle")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        src_con = sqlite3.connect(sqlite_uri(src, "ro"), uri=True, timeout=3)
    except sqlite3.Error as exc:
        raise ValueError(f"Index lässt sich nicht öffnen: {src}") from exc
    try:
        dest_con = sqlite3.connect(target)
        try:
            src_con.backup(dest_con)
            dest_con.commit()
        finally:
            dest_con.close()
    finally:
        src_con.close()
    return target


def compare_indexes(
    path_a: str | Path,
    path_b: str | Path,
    *,
    sample: int = _COMPARE_SAMPLE,
) -> dict[str, Any]:
    """Zwei Indexdateien nach Pfad vergleichen.

    Zählungen laufen in SQL. Zurück kommen die Anzahlen und höchstens 20
    Beispielpfade je Gruppe, nicht der ganze Katalog.
    """
    left = Path(path_a)
    right = Path(path_b)
    limit = max(0, min(_COMPARE_SAMPLE, int(sample)))
    con = _open_index_pair(left, right)
    try:
        count_a = _item_count(con, "main")
        count_b = _item_count(con, "idxb")
        only_a = _count_missing(con, "main", "idxb")
        only_b = _count_missing(con, "idxb", "main")
        changed = _count_changed(con)
        return {
            "count_a": count_a,
            "count_b": count_b,
            "only_a": only_a,
            "only_b": only_b,
            "changed": changed,
            "only_a_paths": _sample_missing(con, "main", "idxb", limit),
            "only_b_paths": _sample_missing(con, "idxb", "main", limit),
            "changed_paths": _sample_changed(con, limit),
        }
    finally:
        con.close()


def format_index_compare(report: dict[str, Any]) -> str:
    """Kurzer deutscher Bericht für Kommandozeile und Hilfefenster."""
    lines = [
        f"Einträge in A: {report['count_a']}",
        f"Einträge in B: {report['count_b']}",
        f"Nur in A: {report['only_a']}",
    ]
    lines.extend(f"  {path}" for path in report["only_a_paths"])
    lines.append(f"Nur in B: {report['only_b']}")
    lines.extend(f"  {path}" for path in report["only_b_paths"])
    lines.append(f"Geändert: {report['changed']}")
    lines.extend(f"  {path}" for path in report["changed_paths"])
    return "\n".join(lines)


def _open_index_pair(left: Path, right: Path) -> sqlite3.Connection:
    if not left.is_file():
        raise ValueError(f"Index fehlt: {left}")
    if not right.is_file():
        raise ValueError(f"Index fehlt: {right}")
    try:
        con = sqlite3.connect(sqlite_uri(left, "ro"), uri=True, timeout=3)
    except sqlite3.Error as exc:
        raise ValueError(f"Index lässt sich nicht öffnen: {left}") from exc
    try:
        con.execute("ATTACH DATABASE ? AS idxb", (sqlite_uri(right, "ro"),))
    except sqlite3.Error as exc:
        con.close()
        raise ValueError(f"Index lässt sich nicht öffnen: {right}") from exc
    try:
        _require_items(con, "main", left)
        _require_items(con, "idxb", right)
    except ValueError:
        con.close()
        raise
    return con


def _require_items(con: sqlite3.Connection, schema: str, path: Path) -> None:
    row = con.execute(
        f"SELECT 1 FROM {schema}.sqlite_master WHERE type='table' AND name='items'"
    ).fetchone()
    if row is None:
        raise ValueError(f"Index ohne Tabelle items: {path}")


def _item_count(con: sqlite3.Connection, schema: str) -> int:
    row = con.execute(f"SELECT COUNT(*) FROM {schema}.items").fetchone()
    return int(row[0])


def _count_missing(con: sqlite3.Connection, have: str, other: str) -> int:
    row = con.execute(
        f"""
        SELECT COUNT(*) FROM {have}.items AS have
        WHERE NOT EXISTS (
          SELECT 1 FROM {other}.items AS other WHERE other.path = have.path
        )
        """
    ).fetchone()
    return int(row[0])


def _sample_missing(con: sqlite3.Connection, have: str, other: str, limit: int) -> list[str]:
    if limit <= 0:
        return []
    rows = con.execute(
        f"""
        SELECT have.path FROM {have}.items AS have
        WHERE NOT EXISTS (
          SELECT 1 FROM {other}.items AS other WHERE other.path = have.path
        )
        ORDER BY have.path
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [str(row[0]) for row in rows]


def _count_changed(con: sqlite3.Connection) -> int:
    row = con.execute(
        """
        SELECT COUNT(*) FROM main.items AS a
        JOIN idxb.items AS b ON b.path = a.path
        WHERE a.size != b.size OR a.mtime_ns != b.mtime_ns
        """
    ).fetchone()
    return int(row[0])


def _sample_changed(con: sqlite3.Connection, limit: int) -> list[str]:
    if limit <= 0:
        return []
    rows = con.execute(
        """
        SELECT a.path FROM main.items AS a
        JOIN idxb.items AS b ON b.path = a.path
        WHERE a.size != b.size OR a.mtime_ns != b.mtime_ns
        ORDER BY a.path
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [str(row[0]) for row in rows]


def create_index(dest: str | Path) -> Path:
    """Leere Indexdatei mit demselben Schema wie der laufende Katalog.

    Eine andere Datei, auch der persönliche Index, wird nicht angefasst.
    """
    target = Path(dest)
    if target.exists() and not target.is_file():
        raise ValueError(f"Ziel ist kein Dateipfad: {target}")
    index = open_index(target, readonly=False)
    index.close()
    return target


def add_names(
    dest: str | Path,
    items: list[dict[str, Any]],
    *,
    prune_root: str | None = None,
) -> dict[str, int]:
    """Namen einfügen oder aktualisieren. Pfade außerhalb bleiben, außer beim Prunen.

    Es wird kein Dateiinhalt geschrieben. prune_root entfernt nur nicht gesehene
    Pfade unter diesem Ordner.
    """
    index = open_index(Path(dest), readonly=False)
    try:
        unique: dict[str, dict[str, Any]] = {}
        for item in items:
            unique[str(item["path"])] = item
        rows = list(unique.values())
        with index.lock:
            index.con.execute("BEGIN IMMEDIATE")
            try:
                index._upsert_items(rows)
                pruned = 0
                if prune_root:
                    pruned = _prune_unseen(index, prune_root, list(unique))
                index.con.commit()
            except Exception:
                index.con.rollback()
                raise
        return {"names": len(rows), "pruned": pruned}
    finally:
        index.close()


def open_index(path: str | Path, *, readonly: bool) -> Index:
    """Index öffnen. Eine Datei ohne items-Tabelle ist kein Flare-Index."""
    path = Path(path)
    if readonly and not path.is_file():
        raise ValueError(f"Index fehlt: {path}")
    try:
        index = Index(path, readonly=readonly)
    except sqlite3.Error as exc:
        raise ValueError(f"Index lässt sich nicht öffnen: {path}") from exc
    try:
        row = index.con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='items'"
        ).fetchone()
    except sqlite3.Error as exc:
        index.close()
        raise ValueError(f"Index lässt sich nicht öffnen: {path}") from exc
    if row is None:
        index.close()
        raise ValueError(f"Index ohne Tabelle items: {path}")
    return index


def _prune_unseen(index: Index, root: str, seen: list[str]) -> int:
    folder = norm(root)
    prefix = like_pattern(child_prefix(folder))
    index.con.execute("DELETE FROM flare_seen")
    if seen:
        index.con.executemany(
            "INSERT OR IGNORE INTO flare_seen(path) VALUES (?)",
            [(path,) for path in seen],
        )
    cursor = index.con.execute(
        """
        DELETE FROM items
        WHERE (path=? OR path LIKE ? ESCAPE '!')
          AND path NOT IN (SELECT path FROM flare_seen)
        """,
        (folder, prefix),
    )
    index.con.execute(
        """
        DELETE FROM dirs
        WHERE (path=? OR path LIKE ? ESCAPE '!')
          AND path NOT IN (SELECT path FROM flare_seen)
        """,
        (folder, prefix),
    )
    return int(cursor.rowcount if cursor.rowcount is not None else 0)
