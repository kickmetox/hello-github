"""Kommandozeile. Ohne Unterbefehl startet Flare und bleibt liegen."""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sqlite3
import sys
from pathlib import Path
from typing import Any

from flare import __version__
from flare.autostart import install_autostart, remove_autostart
from flare.client import Client
from flare.paths import config_dir, data_dir
from flare.service import Service, roots_from_args
from flare.store import Index, compare_indexes, copy_index, format_index_compare


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
    query.add_argument("--similar", action="store_true", help="ähnliche Namen mitsuchen")

    opened = sub.add_parser("open", help="Treffer über die id öffnen")
    opened.add_argument("id", type=int)

    sub.add_parser("status", help="Laufzustand und Kataloggröße")
    sub.add_parser("reindex", help="Katalog neu lesen")
    sub.add_parser("install-autostart", help="mit der Anmeldung starten")
    sub.add_parser("remove-autostart", help="Autostart entfernen")
    saved = sub.add_parser("index-save", help="Index zusätzlich in eine Datei schreiben")
    saved.add_argument("dest", metavar="ZIELDATEI")
    copied = sub.add_parser("index-copy", help="eine Indexdatei in eine andere kopieren")
    copied.add_argument("source", metavar="QUELLE")
    copied.add_argument("dest", metavar="ZIEL")
    compared = sub.add_parser("index-compare", help="zwei Indexdateien vergleichen")
    compared.add_argument("left", metavar="A")
    compared.add_argument("right", metavar="B")
    return parser


def _index_save(args: argparse.Namespace) -> int:
    folder = args.data_dir or data_dir()
    source = Path(folder) / "index.db"
    if not source.exists():
        print("Index fehlt", file=sys.stderr)
        return 1
    index = Index(source)
    try:
        saved = index.backup(args.dest)
    except (OSError, ValueError) as exc:
        print(f"Speichern fehlgeschlagen: {exc}", file=sys.stderr)
        return 1
    finally:
        index.close()
    print(saved)
    return 0


def _index_copy(args: argparse.Namespace) -> int:
    try:
        saved = copy_index(args.source, args.dest)
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f"Kopieren fehlgeschlagen: {exc}", file=sys.stderr)
        return 1
    print(saved)
    return 0


def _index_compare(args: argparse.Namespace) -> int:
    try:
        report = compare_indexes(args.left, args.right)
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f"Vergleich fehlgeschlagen: {exc}", file=sys.stderr)
        return 1
    print(format_index_compare(report))
    return 0


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
        extra = ""
        similarity = hit.get("similarity")
        if hit.get("via") == "similar" and isinstance(similarity, (int, float)):
            extra = f"  ähnlich {int(round(float(similarity) * 100)):02d} %"
        print(f"{ident:>6}  {hit['kind']:<5}  {hit['name']}  {hit.get('path', '')}{extra}")


def _ensure_stdio() -> None:
    """Fenster-EXE hat keine Konsole. Fehlende Ströme auf NUL legen.

    PyInstaller startet mit console=False (runw). Dabei sind die
    Standardströme None. Nur os.open / open verwenden, nie einen rohen
    Win32-Zeiger. Sonst stirbt der Prozess, bevor das Fenster aufgeht.
    """
    if sys.stdin is not None and sys.stdout is not None and sys.stderr is not None:
        return
    if sys.platform == "win32":
        _reopen_standard_fds()
    if sys.stdin is None:
        sys.stdin = open(os.devnull, "r", encoding="utf-8", errors="replace")
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8", errors="replace")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8", errors="replace")


def _reopen_standard_fds() -> None:
    """Geschlossene Handles 0/1/2 auf NUL legen. Nur os.fstat, os.open, os.dup2."""
    targets = (
        (0, os.O_RDONLY),
        (1, os.O_WRONLY | os.O_APPEND),
        (2, os.O_WRONLY | os.O_APPEND),
    )
    for fd, flags in targets:
        try:
            os.fstat(fd)
            continue
        except OSError:
            pass
        try:
            opened = os.open(os.devnull, flags)
        except OSError:
            continue
        try:
            if opened != fd:
                os.dup2(opened, fd)
        except OSError:
            pass
        finally:
            if opened != fd:
                os.close(opened)


def main(argv: list[str] | None = None) -> int:
    _ensure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "index-save":
        return _index_save(args)
    if args.cmd == "index-copy":
        return _index_copy(args)
    if args.cmd == "index-compare":
        return _index_compare(args)
    # Nur Windows. Eine eingefrorene Flare.exe meldet win32 und läuft weiter.
    if sys.platform != "win32":
        print("Flare ist nur für Windows 11.", file=sys.stderr)
        return 2
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    if args.cmd == "query":
        payload = _client(args).search(args.text, args.limit, similar=args.similar)
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
