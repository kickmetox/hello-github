"""Kommandozeile für Sicherung, Wiederherstellung und Diagnose."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cpcm.backup import create_snapshot, list_snapshots, restore_snapshot
from cpcm.diagnose import analyze
from cpcm.hardware import probe
from cpcm.paths import host_identity
from cpcm.selection import add_path, load_selection, save_selection
from cpcm.settings import counterpart_identity, install_root, load_settings, vault_dir
from cpcm.translate import identities_from_request, translate_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cpcm", description="Cross Platform Config Manager")
    parser.add_argument("--root", type=Path, default=None)
    sub = parser.add_subparsers(dest="command", required=True)
    serve_parser = sub.add_parser("serve")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=None)
    serve_parser.add_argument("--no-browser", action="store_true")
    add_parser = sub.add_parser("add")
    add_parser.add_argument("path", type=Path)
    sub.add_parser("list")
    sub.add_parser("backup")
    restore_parser = sub.add_parser("restore")
    restore_parser.add_argument("id")
    restore_parser.add_argument("--overwrite", action="store_true")
    restore_parser.add_argument("--translate-paths", action="store_true")
    restore_parser.add_argument("--destination", type=Path, default=None)
    translate_parser = sub.add_parser("translate")
    translate_parser.add_argument("file", type=Path)
    translate_parser.add_argument("--source", default=None)
    translate_parser.add_argument("--target", default=None)
    diagnose_parser = sub.add_parser("diagnose")
    diagnose_parser.add_argument("file", type=Path)
    sub.add_parser("probe")
    args = parser.parse_args(argv)
    root = (args.root or install_root()).resolve()
    if args.command == "serve":
        from cpcm.server import serve
        settings = load_settings(root)
        serve(args.host, args.port or int(settings.get("port") or 8765), root, open_browser=not args.no_browser)
        return 0
    vault = vault_dir(load_settings(root), root)
    host = host_identity()
    if args.command == "add":
        selection = load_selection(vault)
        item = add_path(selection, args.path, host, counterpart_identity(load_settings(root), host))
        save_selection(vault, selection)
        print(json.dumps(item.to_json(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "list":
        print(json.dumps({"selection": load_selection(vault).to_json(), "snapshots": list_snapshots(vault)}, indent=2, ensure_ascii=False))
        return 0
    if args.command == "backup":
        print(create_snapshot(vault, load_selection(vault), host).id)
        return 0
    if args.command == "restore":
        print(json.dumps(restore_snapshot(vault, args.id, host, source=host, overwrite=args.overwrite, translate_paths=args.translate_paths, destination=args.destination).to_json(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "translate":
        text = args.file.read_text(encoding="utf-8")
        payload = {"text": text, "homes": load_settings(root)["homes"]}
        if args.source:
            payload["source"] = args.source
        if args.target:
            payload["target"] = args.target
        source, target = identities_from_request(payload, host)
        print(translate_config(text, source, target)["text"])
        return 0
    if args.command == "diagnose":
        print(json.dumps(analyze(args.file.read_text(encoding="utf-8")), indent=2, ensure_ascii=False))
        return 0
    if args.command == "probe":
        print(json.dumps(probe(), indent=2, ensure_ascii=False))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
