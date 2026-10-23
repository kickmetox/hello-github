"""Kommandozeile. Ohne Unterbefehl startet Flare und bleibt liegen."""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
from pathlib import Path
from typing import Any

from flare import __version__
from flare.autostart import install_autostart, remove_autostart
from flare.client import Client
from flare.paths import config_dir, data_dir
from flare.service import Service, roots_from_args


def load_config(folder: Path | None = None) -> dict[str, Any]:
    path = (folder or config_dir()) / "config.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flare",
        description="Spotlight-ähnliche Suche für Windows 11.",
    )
    parser.add_argument("--version", action="version", version=f"flare {__version__}")
    parser.add_argument("--data-dir", type=Path, help="Katalog statt des Standardordners")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--background", action="store_true", help="ohne Fenster starten, Kürzel öffnet es")
    parser.add_argument("--no-hotkey", action="store_true")
    parser.add_argument("--no-watch", action="store_true")
    parser.add_argument("--roots", nargs="*", help="nur diese Ordner indizieren")
    parser.add_argument("--port", type=int)
    sub = parser.add_subparsers(dest="cmd")

    query = sub.add_parser("query", help="suchen, für Skripte und andere Programme")
    query.add_argument("text")
    query.add_argument("--json", action="store_true")
    query.add_argument("--limit", type=int, default=8)
    query.add_argument("--open", action="store_true", help="besten Treffer öffnen")

    opened = sub.add_parser("open", help="Treffer über die id öffnen")
    opened.add_argument("id", type=int)

    sub.add_parser("status", help="Laufzustand und Kataloggröße")
    sub.add_parser("reindex", help="Katalog neu lesen")
    sub.add_parser("install-autostart", help="mit der Anmeldung starten")
    sub.add_parser("remove-autostart", help="Autostart entfernen")
    return parser


def _client(args: argparse.Namespace) -> Client:
    return Client(args.data_dir)


def _print_hits(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return
    results = payload.get("results") or []
    if not results:
        print("nichts gefunden")
        return
    for hit in results:
        ident = "-" if hit.get("id") is None else str(hit["id"])
        print(f"{ident:>6}  {hit['kind']:<5}  {hit['name']}  {hit.get('path', '')}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if sys.platform != "win32":
        print("Flare ist nur für Windows 11.", file=sys.stderr)
        return 2
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    if args.cmd == "query":
        payload = _client(args).search(args.text, args.limit)
        _print_hits(payload, args.json)
        if args.open and payload.get("results"):
            first = payload["results"][0]
            if first.get("id") is not None:
                ok = _client(args).open_id(int(first["id"]))
                if not ok:
                    print("Treffer nicht geöffnet (Flare läuft nicht)", file=sys.stderr)
                    return 1
        return 0
    if args.cmd == "open":
        return 0 if _client(args).open_id(args.id) else 1
    if args.cmd == "status":
        print(json.dumps(_client(args).status(), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "reindex":
        if _client(args).reindex():
            print("neu indizieren")
            return 0
        print("Flare läuft nicht", file=sys.stderr)
        return 1
    if args.cmd == "install-autostart":
        print(install_autostart())
        return 0
    if args.cmd == "remove-autostart":
        print(remove_autostart())
        return 0

    client = _client(args)
    if client.port() is not None and client.activate():
        print(f"Flare läuft bereits auf {client.port()}")
        return 0
    service = Service(
        data_dir=args.data_dir or data_dir(),
        roots=roots_from_args(args.roots),
        config=load_config(),
        open_immediately=not args.background,
        allow_ui=True,
        hotkey=not args.no_hotkey,
        watch=not args.no_watch,
        port=args.port,
    )

    def stop(_signum: int, _frame: Any) -> None:
        service.stop.set()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    service.run_forever()
    return 0
