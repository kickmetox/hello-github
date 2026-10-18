"""SQL- und Dokument-Abfragen. SQLite ist immer dabei, andere Treiber optional."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


def sqlite_schema(path: str) -> dict:
    file_path = Path(path)
    if not file_path.is_file():
        return {"ok": False, "error": "Datenbankdatei nicht gefunden."}
    with sqlite3.connect(file_path) as con:
        rows = con.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
        ).fetchall()
    return {
        "ok": True,
        "objects": [{"type": row[0], "name": row[1], "table": row[2], "sql": row[3]} for row in rows],
    }


def _split_sql(sql: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    quote = ""
    i = 0
    text = sql or ""
    while i < len(text):
        char = text[i]
        if quote:
            buf.append(char)
            if char == quote:
                if i + 1 < len(text) and text[i + 1] == quote:
                    buf.append(text[i + 1])
                    i += 2
                    continue
                quote = ""
            i += 1
            continue
        if char in {"'", '"'}:
            quote = char
            buf.append(char)
        elif char == "-" and i + 1 < len(text) and text[i + 1] == "-":
            while i < len(text) and text[i] not in "\n\r":
                buf.append(text[i])
                i += 1
            continue
        elif char == ";":
            piece = "".join(buf).strip()
            if piece:
                parts.append(piece)
            buf = []
        else:
            buf.append(char)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


def sqlite_query(path: str, sql: str, limit: int = 500) -> dict:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    statements = _split_sql(sql)
    if not statements:
        return {"ok": False, "error": "SQL fehlt."}
    try:
        with sqlite3.connect(file_path) as con:
            con.row_factory = sqlite3.Row
            for statement in statements[:-1]:
                con.execute(statement)
            cur = con.execute(statements[-1])
            if cur.description:
                columns = [item[0] for item in cur.description]
                rows = [dict(row) for row in cur.fetchmany(limit)]
                con.commit()
                return {"ok": True, "columns": columns, "rows": rows}
            con.commit()
            return {"ok": True, "columns": [], "rows": [], "rowcount": cur.rowcount}
    except sqlite3.Error as exc:
        return {"ok": False, "error": str(exc)}


def _external(engine: str, dsn: str, sql: str) -> dict:
    try:
        if engine == "postgresql":
            try:
                import psycopg
                con = psycopg.connect(dsn)
            except ImportError:
                import psycopg2
                con = psycopg2.connect(dsn)
        elif engine == "mysql":
            import pymysql

            con = pymysql.connect(**_mysql_kwargs(dsn))
        else:
            return {"ok": False, "error": f"Unbekannte Engine {engine}."}
    except ImportError:
        package = {"postgresql": "psycopg", "mysql": "pymysql"}.get(engine, engine)
        return {"ok": False, "error": f"Treiber fehlt. Installiere das Paket '{package}' über den Paket-Manager."}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    try:
        cur = con.cursor()
        cur.execute(sql)
        if cur.description:
            columns = [item[0] for item in cur.description]
            rows = []
            for row in cur.fetchmany(500):
                rows.append({columns[i]: row[i] for i in range(len(columns))})
            return {"ok": True, "columns": columns, "rows": _jsonable(rows)}
        con.commit()
        return {"ok": True, "columns": [], "rows": [], "rowcount": cur.rowcount}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        con.close()


def mongo_find(uri: str, database: str, collection: str, query: dict, limit: int = 50) -> dict:
    try:
        import pymongo
    except ImportError:
        return {"ok": False, "error": "Treiber fehlt. Installiere das Paket 'pymongo'."}
    try:
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=4000)
        docs = list(client[database][collection].find(query, limit=limit))
        for doc in docs:
            doc["_id"] = str(doc.get("_id"))
        return {"ok": True, "columns": sorted({key for doc in docs for key in doc}), "rows": docs}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _mysql_kwargs(dsn: str) -> dict:
    text = dsn.strip()
    if text.startswith("{"):
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    parts: dict[str, str] = {}
    for token in text.replace(";", " ").split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        parts[{"db": "database", "pass": "password"}.get(key, key)] = value
    return parts


def _jsonable(rows: list[dict]) -> list[dict]:
    cleaned = []
    for row in rows:
        item = {}
        for key, value in row.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                item[key] = value
            else:
                item[key] = str(value)
        cleaned.append(item)
    return cleaned


def query(engine: str, sql: str = "", path: str = "", dsn: str = "", database: str = "", collection: str = "", mongo_query: dict | None = None) -> dict:
    engine = (engine or "sqlite").lower()
    if engine == "sqlite":
        if not path:
            return {"ok": False, "error": "Pfad zur SQLite-Datei fehlt."}
        return sqlite_query(path, sql)
    if engine in {"postgresql", "mysql"}:
        if not dsn:
            return {"ok": False, "error": "Verbindungszeichenkette fehlt."}
        return _external(engine, dsn, sql)
    if engine in {"mongodb", "mongo"}:
        if not dsn or not database or not collection:
            return {"ok": False, "error": "URI, Datenbank und Collection werden gebraucht."}
        return mongo_find(dsn, database, collection, mongo_query or {})
    return {"ok": False, "error": "Engine nicht unterstützt."}
