"""Befehle für Visual Studio und die Kommandozeile."""

from __future__ import annotations

import argparse
import logging

from app.config import settings
from app.database import SessionLocal
from app.main import init_database
from app.services import rebuild_index, search_documents


def serve() -> None:
    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("docman").info("Startadresse http://%s:%s", settings.host, settings.port)
    uvicorn.run("app.main:app", host=settings.host, port=settings.port)


def search(query: str, top: int) -> None:
    init_database()
    with SessionLocal() as db:
        hits, terms = search_documents(db, query, top)
    if not terms:
        print("Die Anfrage enthält nur Füllwörter.")
        return
    if not hits:
        print("Keine Treffer.")
        return
    for hit in hits:
        doc = hit["document"]
        print(f"{hit['score']:.4f}  {doc['title']}")
        if hit["snippet"]:
            print(f"         {hit['snippet']}")


def reindex() -> None:
    init_database()
    with SessionLocal() as db:
        count = rebuild_index(db)
    print(f"Index neu aufgebaut: {count} Dokumente")


def main() -> None:
    parser = argparse.ArgumentParser(prog="docman", description="Lokales Dokumentenarchiv")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("serve", help="Weboberfläche starten")
    search_parser = sub.add_parser("search", help="TF-IDF-Suche auf der Kommandozeile")
    search_parser.add_argument("query")
    search_parser.add_argument("--top", type=int, default=10)
    sub.add_parser("reindex", help="Suchindex neu aufbauen")
    args = parser.parse_args()
    if args.command == "search":
        search(args.query, args.top)
    elif args.command == "reindex":
        reindex()
    else:
        serve()


if __name__ == "__main__":
    main()
