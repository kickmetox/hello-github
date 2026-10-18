"""Kommandozeile: serve, translate, diagnose, apps plan, hardware probe."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from crossos import __version__
from crossos.diagnostics import diagnose
from crossos.hardware import probe
from crossos.migrator.apps import plan_apps
from crossos.migrator.semantic import translate_document
from crossos.safety import SafetyError
from crossos.server import serve


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="crossos", description="CrossOS Intelligent Workflow & System Sync")
    parser.add_argument("--version", action="version", version=f"crossos {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    serve_parser = sub.add_parser("serve", help="Lokale Oberfläche starten")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)

    translate_parser = sub.add_parser("translate", help="Konfiguration übersetzen")
    translate_parser.add_argument("--input", required=True)
    translate_parser.add_argument("--from", dest="source_format")
    translate_parser.add_argument("--to", dest="target_format", required=True)
    translate_parser.add_argument("--target-os", default="windows", choices=["linux", "windows", "wsl"])
    translate_parser.add_argument("--user")

    diagnose_parser = sub.add_parser("diagnose", help="Protokoll in Klartext übersetzen")
    diagnose_parser.add_argument("--input", required=True)
    diagnose_parser.add_argument("--shell", choices=["bash", "powershell"])

    apps = sub.add_parser("apps", help="Anwendungskatalog")
    apps_sub = apps.add_subparsers(dest="apps_command", required=True)
    plan = apps_sub.add_parser("plan", help="Zielpakete planen, nichts installieren")
    plan.add_argument("--os", dest="target_os", required=True, choices=["linux", "windows"])
    plan.add_argument("--app", action="append", required=True)
    plan.add_argument("--detect", action="store_true")

    hardware = sub.add_parser("hardware", help="Hardware")
    hardware_sub = hardware.add_subparsers(dest="hardware_command", required=True)
    hardware_sub.add_parser("probe", help="sysfs lesen oder Windows-Befehle planen")

    args = parser.parse_args(argv)
    try:
        return _dispatch(args)
    except SafetyError as exc:
        print(str(exc), file=sys.stderr)
        return 2


def _dispatch(args: argparse.Namespace) -> int:
    if args.command == "serve":
        serve(args.host, args.port)
        return 0
    if args.command == "translate":
        text = Path(args.input).read_text(encoding="utf-8")
        result = translate_document(
            text,
            source_format=args.source_format,
            target_format=args.target_format,
            target_os=args.target_os,
            user=args.user,
        )
        _emit(result)
        return 0
    if args.command == "diagnose":
        text = Path(args.input).read_text(encoding="utf-8")
        _emit(diagnose(text, shell=args.shell))
        return 0
    if args.command == "apps" and args.apps_command == "plan":
        _emit(plan_apps(args.app, target_os=args.target_os, detect=args.detect))
        return 0
    if args.command == "hardware" and args.hardware_command == "probe":
        _emit(probe())
        return 0
    return 2


def _emit(payload: dict) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
