#!/usr/bin/env python3
"""Menü-Audit 2.6.54: Inventar + Trigger aller Aktionen (offscreen)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from menu_smoke_lib import (  # noqa: E402
    format_inventory_markdown,
    build_fixtures,
    create_main_window,
    current_state_tag,
    english_in_de_ui,
    install_headless_env,
    install_qt_hooks,
    inventory_window,
    load_state,
    missing_ribbon_handlers,
    pump,
    shortcut_collisions,
    trigger_row,
)

STATES = ("empty", "docx", "pdf20", "pdf500", "none")


def _plain(row: dict) -> dict:
    out = {k: v for k, v in row.items() if k not in ("action", "widget")}
    return out


def main() -> int:
    import faulthandler

    faulthandler.dump_traceback_later(420, exit=True)
    cfg = install_headless_env()
    hook_recs: list[dict] = []
    restore = None
    app = None
    win = None
    report: dict = {"config_home": cfg, "states": {}, "inventory": []}
    with tempfile.TemporaryDirectory(prefix="ild-menu-audit-") as td:
        fixtures = build_fixtures(Path(td), with_pdf500=True)
        hook_recs: list[dict] = []
        restore = install_qt_hooks(hook_recs)
        app, win = create_main_window()
        load_state(win, app, "pdf20", fixtures)
        pump(app, 0.25)
        try:
            win._sync_menu_enablement()
        except Exception:
            pass
        inv = inventory_window(win)
        report["inventory"] = [_plain(r) for r in inv]
        report["counts"] = {
            "inventory": len(inv),
            "menu": sum(1 for r in inv if r["kind"] == "menu"),
            "ribbon": sum(1 for r in inv if r["kind"] == "ribbon"),
            "editor_toolbar": sum(1 for r in inv if r["kind"] == "editor-toolbar"),
            "pdf_toolbar": sum(1 for r in inv if r["kind"] == "pdf-toolbar"),
            "palette": sum(1 for r in inv if r["kind"] == "palette"),
            "shortcut": sum(1 for r in inv if r["kind"] == "shortcut"),
        }
        report["missing_ribbon"] = missing_ribbon_handlers(win)
        report["shortcut_collisions"] = [
            {"shortcut": k, "paths": v} for k, v in shortcut_collisions(inv)
        ]
        report["english_in_de"] = english_in_de_ui(inv)
        report["no_slot"] = [
            r["path"]
            for r in inv
            if r["kind"] == "menu" and int(r.get("receivers") or 0) == 0
        ]
        report["stubs"] = [r["path"] for r in inv if r.get("stub")]
        print("INVENTORY", report["counts"], flush=True)
        print("MISSING_RIBBON", report["missing_ribbon"], flush=True)
        print("COLLISIONS", len(report["shortcut_collisions"]), flush=True)

        trigger_kinds = {"menu", "ribbon", "editor-toolbar", "pdf-toolbar", "palette"}
        for state in STATES:
            load_state(win, app, state, fixtures)
            pump(app, 0.2)
            results = []
            for row in inv:
                if row.get("kind") not in trigger_kinds:
                    continue
                # 500-Seiten-PDF: Palette+Leisten reichen; Menü voll, PDF-Leiste skip heavy export
                if state == "pdf500" and row.get("kind") == "palette":
                    continue
                try:
                    out = trigger_row(app, win, row, state)
                except Exception as e:
                    out = {"exc": f"{type(e).__name__}: {e}"}
                if out.get("skipped"):
                    continue
                interesting = (
                    out.get("exc")
                    or out.get("hang")
                    or out.get("no_slot")
                    or out.get("stub")
                    or out.get("silent")
                )
                if interesting:
                    results.append(
                        {
                            "path": row.get("path"),
                            "kind": row.get("kind"),
                            "area": row.get("area") or "",
                            **{k: v for k, v in out.items() if k != "status_before"},
                        }
                    )
                if current_state_tag(win, fixtures) != state:
                    try:
                        load_state(win, app, state, fixtures)
                    except Exception:
                        pass
            report["states"][state] = {
                "interesting": results,
                "n_interesting": len(results),
            }
            print(f"STATE {state}: {len(results)} interesting", flush=True)

        report["hooks"] = hook_recs[-50:]
        try:
            win.close()
        except Exception:
            pass

    out_path = Path(os.environ.get("ILD_MENU_AUDIT_JSON", "/tmp/ild-menu-audit-2654.json"))
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    md_path = Path(
        os.environ.get(
            "ILD_MENU_INVENTORY_MD",
            "/cursor/stores/bc-b08b150e-66b9-4e56-8bf8-50c583a73b7e/internal/instantlensdoc-2654-menu-inventory.md",
        )
    )
    try:
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(
            format_inventory_markdown(
                report["inventory"],
                state_note=(
                    "Zustand der `enabled`-Spalte: **PDF 20 Seiten geladen** "
                    "(Editor-only-Aktionen daher als PDF-disabled markiert: "
                    "Zeilenabstand, Absatz, Stile, Einrückung, Seitenlayout)."
                ),
            ),
            encoding="utf-8",
        )
        print("WROTE_MD", md_path, flush=True)
    except OSError as e:
        print("INVENTORY_MD_SKIP", e, flush=True)
    print("WROTE", out_path)
    print("INVENTORY", report["counts"])
    print("MISSING_RIBBON", report["missing_ribbon"])
    print("COLLISIONS", len(report["shortcut_collisions"]))
    print("STUBS", report["stubs"])
    print("NO_SLOT", report["no_slot"])
    if restore:
        restore()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
