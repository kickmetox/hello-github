#!/usr/bin/env python3
"""Nightly/CI Smoke: CLI + Import-Checks für InstantLens Doc — 2.1.0–2.1.2.

Leichtgewichtig. Exit-Codes:
  0  OK
  1  Fehler (Assertion/Import/Version)
  2  Nutzung / unbekannte Option (--help → 0)

Aufruf:
  python scripts/smoke_ild.py
  python scripts/smoke_ild.py --qt          # optionale Qt-Source-Checks
  python scripts/smoke_ild.py --skip-qt     # Qt-Checks überspringen (Default)
  python scripts/smoke_ild.py --json        # Summary als JSON (stdout)
  python scripts/smoke_ild.py -h
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Headless/CI: Qt ohne Display
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

EXPECTED_VERSION = "2.1.2"

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2


_JSON_MODE = False


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(EXIT_FAIL)


def _ok(msg: str) -> None:
    if not _JSON_MODE:
        print(f"OK: {msg}")


def check_version() -> None:
    from ild_pdf import __version__ as ild_ver
    from instantlensdoc import __version__ as app_ver

    if app_ver != EXPECTED_VERSION:
        _fail(f"instantlensdoc.__version__={app_ver!r} erwartet {EXPECTED_VERSION}")
    if ild_ver != EXPECTED_VERSION:
        _fail(f"ild_pdf.__version__={ild_ver!r} erwartet {EXPECTED_VERSION}")
    ver_txt = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
    docs_ver = (ROOT / "docs" / "VERSION").read_text(encoding="utf-8").strip()
    if not ver_txt.startswith(EXPECTED_VERSION):
        _fail(f"VERSION.txt={ver_txt!r}")
    if not docs_ver.startswith(EXPECTED_VERSION):
        _fail(f"docs/VERSION={docs_ver!r}")
    _ok(f"version {EXPECTED_VERSION}")


def check_imports(*, with_qt: bool) -> None:
    modules = [
        "ild_pdf",
        "ild_pdf.annotate",
        "ild_pdf.diff",
        "ild_pdf.pdf_ann_import",
        "ild_pdf.overlay",
        "ild_pdf.render",
        "instantlensdoc",
        "instantlensdoc.core.app_settings",
        "instantlensdoc.core.text_diff",
    ]
    for name in modules:
        try:
            importlib.import_module(name)
        except Exception as e:
            _fail(f"import {name}: {e}")
    # UI-Module: Quelltext-Checks (Qt/EGL auf CI oft ohne Display-Libs)
    ui_checks = {
        ROOT / "instantlensdoc" / "ui" / "compare_dialog.py": (
            "chk_text_diff",
            "text_layer_diff",
            "chk_ignore_ws",
            "chk_only_diff",
            "chk_side_by_side",
            "txt_template_edit",
            "_export_text_diff_txt",
        ),
        ROOT / "instantlensdoc" / "ui" / "pdf_view.py": (
            "import_native_pdf_comments",
            "MEASURE_AREA",
            "MEASURE_ANGLE",
            "_toggle_measure_unit",
            "_toggle_measure_snap",
            "export_measures_csv",
            "dry_run",
            "Nach Import Sidecar speichern",
            "status_counts_de",
            "get_measure_csv_utf8_bom",
            "get_last_measure_csv_dir",
        ),
    }
    if with_qt:
        for path, needles in ui_checks.items():
            if not path.is_file():
                _fail(f"fehlt: {path}")
            src = path.read_text(encoding="utf-8")
            for n in needles:
                if n not in src:
                    _fail(f"{path.name} fehlt {n!r}")
        _ok(f"imports ({len(modules)}) + ui-source (--qt)")
    else:
        _ok(f"imports ({len(modules)}) · Qt-Source übersprungen (--skip-qt)")


def check_cli_version() -> None:
    import subprocess

    r = subprocess.run(
        [sys.executable, "-m", "instantlensdoc", "--version"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0:
        _fail(f"--version exit {r.returncode}: {out[:200]}")
    if EXPECTED_VERSION not in out:
        _fail(f"--version Ausgabe ohne {EXPECTED_VERSION}: {out[:200]}")
    _ok("cli --version")


def check_measure_and_diff() -> None:
    from ild_pdf import (
        Annotation,
        AnnotationType,
        DIFF_FORMAT_SIDE_BY_SIDE,
        export_text_layer_diff_txt,
        format_side_by_side_diff,
        text_layer_diff,
        text_to_pdf,
    )
    from ild_pdf.pdf_ann_import import (
        import_native_into_store,
        import_native_pdf_annotations,
    )
    from ild_pdf.annotate import AnnotationStore
    from instantlensdoc.core.app_settings import (
        get_measure_csv_utf8_bom,
        get_measure_labels_persistent,
        get_measure_snap_to_annotation,
        get_measure_unit,
        get_native_ann_import_save_sidecar,
        get_textlayer_diff_side_by_side,
        get_textlayer_diff_txt_template,
        set_measure_csv_utf8_bom,
        set_measure_labels_persistent,
        set_measure_snap_to_annotation,
        set_measure_unit,
        set_native_ann_import_save_sidecar,
        set_textlayer_diff_side_by_side,
        toggle_measure_unit,
    )

    # Maß-Einheit Toggle
    set_measure_unit("mm")
    assert get_measure_unit() == "mm"
    assert toggle_measure_unit() == "px"
    assert get_measure_unit() == "px"
    set_measure_unit("mm")

    # Snap / Labels Settings — 2.1.1
    set_measure_snap_to_annotation(True)
    assert get_measure_snap_to_annotation() is True
    set_measure_snap_to_annotation(False)
    assert get_measure_snap_to_annotation() is False
    set_measure_labels_persistent(True)
    assert get_measure_labels_persistent() is True

    # BOM / Sidecar-Toggle / Side-by-Side Settings — 2.1.2
    set_measure_csv_utf8_bom(True)
    assert get_measure_csv_utf8_bom() is True
    set_measure_csv_utf8_bom(False)
    assert get_measure_csv_utf8_bom() is False
    set_measure_csv_utf8_bom(True)
    set_native_ann_import_save_sidecar(True)
    assert get_native_ann_import_save_sidecar() is True
    set_textlayer_diff_side_by_side(True)
    assert get_textlayer_diff_side_by_side() is True
    set_textlayer_diff_side_by_side(False)
    assert get_textlayer_diff_side_by_side() is False
    assert "{stemA}" in get_textlayer_diff_txt_template()

    # Flächen-/Winkel-Labels
    area = Annotation(
        0, AnnotationType.MEASURE_AREA, 0, 0, width=72, height=72, color="#E67E22"
    )
    assert "mm²" in area.measure_label(1.0, unit="mm") or "pt²" in area.measure_label(
        1.0, unit="pt"
    )
    assert "px²" in area.measure_label(1.0, unit="px")
    ang = Annotation(
        0,
        AnnotationType.MEASURE_ANGLE,
        0,
        0,
        callout_x=50,
        callout_y=0,
        p3_x=50,
        p3_y=50,
        color="#E67E22",
    )
    deg = ang.angle_degrees()
    assert 80.0 <= deg <= 100.0, deg
    assert "°" in ang.measure_label(1.0)

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        a = td_path / "a.pdf"
        b = td_path / "b.pdf"
        text_to_pdf("alpha\nbeta\ngamma", a)
        text_to_pdf("alpha\nBETA\ngamma", b)
        result = text_layer_diff(a, b, left_page=0, right_page=0)
        assert 0.0 <= result.similarity_percent <= 100.0
        assert result.unified_diff or result.left_text
        # Ignore-WS / Nur-Unterschiede — 2.1.1
        ws = text_layer_diff(
            a, b, ignore_whitespace=True, only_differences=True
        )
        assert ws.ignore_whitespace and ws.only_differences
        # Side-by-Side — 2.1.2
        sbs = text_layer_diff(
            a, b, diff_format=DIFF_FORMAT_SIDE_BY_SIDE, only_differences=True
        )
        assert sbs.side_by_side_diff
        assert "|" in sbs.side_by_side_diff
        assert format_side_by_side_diff(
            ["a", "b"], ["a", "c"], only_differences=True
        )
        txt_out = td_path / "diff.txt"
        export_text_layer_diff_txt(ws, txt_out)
        assert txt_out.is_file() and txt_out.stat().st_size > 0
        txt_sbs = td_path / "diff_sbs.txt"
        export_text_layer_diff_txt(
            sbs, txt_sbs, diff_format=DIFF_FORMAT_SIDE_BY_SIDE
        )
        assert "Side-by-Side" in txt_sbs.read_text(encoding="utf-8")
        # Native Import auf Text-PDF (meist 0 Annots, API muss laufen)
        native = import_native_pdf_annotations(a)
        assert native.imported >= 0
        assert native.pages_scanned >= 1
        # Dry-Run into store
        store = AnnotationStore(a)
        store.annotations = []
        dry = import_native_into_store(store, a, dry_run=True)
        assert dry.dry_run is True
        assert len(store.annotations) == 0
        assert "importiert" in dry.status_counts_de()
        # Messwerte CSV Spalten Typ,Seite,Wert,Einheit + BOM — 2.1.2
        store.add(area)
        store.add(ang)
        csv_path = td_path / "messwerte.csv"
        store.export_measures_csv(csv_path, scale=1.0, unit="mm", utf8_bom=True)
        assert csv_path.is_file()
        body = csv_path.read_text(encoding="utf-8-sig")
        assert body.startswith("Typ,Seite,Wert,Einheit") or body.splitlines()[
            0
        ].startswith("Typ")
        assert "measure_area" in body or "measure_angle" in body
        csv_nobom = td_path / "messwerte_nobom.csv"
        store.export_measures_csv(
            csv_nobom, scale=1.0, unit="mm", utf8_bom=False
        )
        raw = csv_nobom.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf")

    _ok(
        "measure + textlayer-diff + native-import + measures-csv "
        "Typ/Seite/Wert/Einheit + side-by-side API"
    )


def check_changelog() -> None:
    cl = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if "## 2.1.2" not in cl:
        _fail("CHANGELOG fehlt ## 2.1.2")
    if "## 2.1.1" not in cl:
        _fail("CHANGELOG fehlt ## 2.1.1")
    if "## 2.1.0" not in cl:
        _fail("CHANGELOG fehlt ## 2.1.0")
    feat = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
    if "2.1.2" not in feat:
        _fail("FEATURES.md fehlt 2.1.2")
    info = (ROOT / "INFO.md").read_text(encoding="utf-8")
    if "smoke_ild" not in info or "--json" not in info:
        _fail("INFO.md fehlt smoke_ild/--json Hinweis")
    _ok("changelog + features + info(smoke_ild --json)")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="smoke_ild.py",
        description=(
            "InstantLens Doc Nightly-Smoke (CLI/Imports/Messung/Diff).\n"
            "Exit: 0=OK, 1=Fehler, 2=ungültige Option."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )
    p.add_argument(
        "-h",
        "--help",
        action="store_true",
        help="kurze DE-Hilfe anzeigen und mit Exit 0 beenden",
    )
    p.add_argument(
        "--qt",
        action="store_true",
        help="UI-Quelltext-Checks ausführen (optional)",
    )
    p.add_argument(
        "--skip-qt",
        action="store_true",
        help="UI-Quelltext-Checks überspringen (Standard)",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Summary als JSON auf stdout (inkl. duration_ms) — 2.1.2",
    )
    return p


def _print_help_de() -> None:
    print(
        """smoke_ild.py — InstantLens Doc Nightly-Smoke

Aufruf:
  python scripts/smoke_ild.py
  python scripts/smoke_ild.py --qt
  python scripts/smoke_ild.py --skip-qt
  python scripts/smoke_ild.py --json
  python scripts/smoke_ild.py -h

Optionen:
  -h, --help     kurze DE-Hilfe (Exit 0)
  --qt           UI-Quelltext-Checks (compare_dialog/pdf_view) ausführen
  --skip-qt      UI-Checks überspringen (Default ohne --qt)
  --json         Summary als JSON (ok/version/duration_ms/checks) — 2.1.2

Exit-Codes:
  0  OK
  1  Fehler (Version/Import/Assertion)
  2  unbekannte Option

Laufzeit: am Ende als „Laufzeit: N ms“ (oder duration_ms im JSON).
""".rstrip()
    )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    try:
        args, unknown = parser.parse_known_args(argv)
    except SystemExit:
        return EXIT_USAGE
    if unknown:
        print(f"Unbekannte Option: {' '.join(unknown)}", file=sys.stderr)
        _print_help_de()
        return EXIT_USAGE
    if args.help:
        _print_help_de()
        return EXIT_OK

    with_qt = bool(args.qt) and not bool(args.skip_qt)
    # Explizites --skip-qt gewinnt; ohne Flags: skip (leichter CI-Default)
    if args.skip_qt:
        with_qt = False

    as_json = bool(args.json)
    global _JSON_MODE
    _JSON_MODE = as_json
    t0 = time.perf_counter()
    checks: list[str] = []
    if not as_json:
        print(f"smoke_ild.py — InstantLens Doc {EXPECTED_VERSION}")
    try:
        check_version()
        checks.append("version")
        check_imports(with_qt=with_qt)
        checks.append("imports")
        check_cli_version()
        checks.append("cli")
        check_measure_and_diff()
        checks.append("measure_diff_import")
        check_changelog()
        checks.append("changelog")
    except SystemExit as e:
        code = int(e.code) if e.code is not None else EXIT_FAIL
        duration_ms = int(round((time.perf_counter() - t0) * 1000))
        if as_json:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "version": EXPECTED_VERSION,
                        "duration_ms": duration_ms,
                        "with_qt": with_qt,
                        "checks": checks,
                        "exit": code,
                    },
                    ensure_ascii=False,
                )
            )
        else:
            print(f"Laufzeit: {duration_ms} ms")
        return code if code != 0 else EXIT_FAIL

    duration_ms = int(round((time.perf_counter() - t0) * 1000))
    if as_json:
        print(
            json.dumps(
                {
                    "ok": True,
                    "version": EXPECTED_VERSION,
                    "duration_ms": duration_ms,
                    "with_qt": with_qt,
                    "checks": checks,
                    "exit": EXIT_OK,
                },
                ensure_ascii=False,
            )
        )
    else:
        print(f"Laufzeit: {duration_ms} ms")
        print("smoke_ild: OK")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
