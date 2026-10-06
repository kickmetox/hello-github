#!/usr/bin/env python3
"""Menü-Audit 2655: open / effect / fail — kein Trigger-ohne-Exception-Pass."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["ILD_SMOKE_QT"] = "1"
os.environ.setdefault("ILD_SKIP_DEPS_CHECK", "1")
os.environ.setdefault("ILD_NO_SESSION", "1")
os.environ.setdefault("ILD_NO_SPLASH", "1")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from menu_effect_lib import (  # noqa: E402
    DialogRecorder,
    build_effect_fixtures,
    create_main_window,
    install_headless_env,
    load_effect_state,
    pump,
    walk_state,
)

STORE = Path("/cursor/stores/bc-b08b150e-66b9-4e56-8bf8-50c583a73b7e")
STATES = ("docx", "ocr", "pdf")


def _summarize(rows: list[dict]) -> dict:
    c = Counter(r.get("verdict") for r in rows)
    fails = [r for r in rows if r.get("verdict") == "fail"]
    return {
        "n": len(rows),
        "open": c.get("open", 0),
        "effect": c.get("effect", 0),
        "fail": c.get("fail", 0),
        "disabled": c.get("disabled", 0),
        "skip": c.get("skip", 0),
        "fails": fails,
    }


def _md_table(rows: list[dict], *, limit: int | None = None) -> str:
    lines = [
        "| Pfad | Urteil | Detail |",
        "|---|---|---|",
    ]
    use = rows if limit is None else rows[:limit]
    for r in use:
        path = str(r.get("path") or "").replace("|", "/")
        verd = str(r.get("verdict") or "")
        det = str(r.get("detail") or "").replace("|", "/")[:120]
        lines.append(f"| {path} | {verd} | {det} |")
    if limit is not None and len(rows) > limit:
        lines.append(f"| … | {len(rows) - limit} weitere | |")
    return "\n".join(lines)


def main() -> int:
    shot = STORE / "media" / "menu-2655" / "offscreen"
    shot.mkdir(parents=True, exist_ok=True)
    cfg = install_headless_env()
    rec = DialogRecorder(shot_dir=shot)
    rec.install()
    report: dict = {"config_home": cfg, "bar": "open-or-effect", "states": {}}
    with tempfile.TemporaryDirectory(prefix="ild-menu-2655-") as td:
        fixtures = build_effect_fixtures(Path(td))
        app, win = create_main_window()
        for state in STATES:
            print(f"WALK {state}", flush=True)
            load_effect_state(win, app, state, fixtures)
            pump(app, 0.25)
            rows = walk_state(app, win, state, rec, fixtures)
            report["states"][state] = {
                "summary": _summarize(rows),
                "rows": rows,
            }
            sm = report["states"][state]["summary"]
            print(
                f"  n={sm['n']} open={sm['open']} effect={sm['effect']} "
                f"fail={sm['fail']} disabled={sm['disabled']}",
                flush=True,
            )
            json_path = STORE / "internal" / "instantlensdoc-2655-menu-inventory.json"
            json_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(
                json.dumps(report, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
            print("JSON", json_path, flush=True)
        try:
            win.close()
        except Exception:
            pass

    rec.restore()

    xvfb_dir = STORE / "media" / "menu-2655" / "xvfb"
    xvfb_dir.mkdir(parents=True, exist_ok=True)
    n_off = len(list(shot.glob("*.png")))
    report["screenshots_offscreen"] = n_off
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen" and n_off:
        try:
            subprocess.run(
                ["bash", "-lc", f"cp -a {shot}/*.png {xvfb_dir}/"],
                check=False,
            )
        except Exception:
            pass
    print("SHOTS", n_off, flush=True)
    return 0 if all(
        report["states"][s]["summary"]["fail"] == 0 for s in STATES
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
