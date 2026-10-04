"""python -m ild — Scripting-CLI InstantLens Doc 2.6.10."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from instantlensdoc import __version__


def _print(obj, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            print(f"{k}: {v}")
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            print(item)
    else:
        print(obj)


def _fail(msg: str, code: int = 1) -> int:
    print(f"FEHLER: {msg}", file=sys.stderr)
    return code


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ild",
        description=(
            "InstantLens Doc Scripting (headless). "
            "Python: import ild · PowerShell: scripts\\ild.ps1"
        ),
        epilog=(
            "Beispiele:\n"
            "  python -m ild version\n"
            "  python -m ild info dokument.pdf\n"
            "  python -m ild pages dokument.pdf\n"
            "  python -m ild export dokument.pdf --page 1 --out seite.png\n"
            "  python -m ild ocr scan.png --lang deu+eng\n"
            "  python -m ild license generate kunde@example.com\n"
            "  python -m ild license verify ILD1....\n"
            "\nExit: 0 OK · 1 Fehler · 2 Datei fehlt"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--json", action="store_true", help="JSON-Ausgabe")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("version", help="Version ausgeben")

    s = sub.add_parser("info", help="PDF öffnen / Infos")
    s.add_argument("pdf")
    s.add_argument("--password", default=None)

    s = sub.add_parser("pages", help="Seitenzahl")
    s.add_argument("pdf")
    s.add_argument("--password", default=None)

    s = sub.add_parser("export", help="Seite als Bild exportieren")
    s.add_argument("pdf")
    s.add_argument("--page", type=int, default=1)
    s.add_argument("--out", required=True)
    s.add_argument("--dpi", type=int, default=150)
    s.add_argument("--format", dest="fmt", default=None)

    s = sub.add_parser("merge", help="PDFs zusammenführen")
    s.add_argument("pdfs", nargs="+")
    s.add_argument("--out", required=True)

    s = sub.add_parser("split", help="PDF in Einzelseiten teilen")
    s.add_argument("pdf")
    s.add_argument("--out-dir", required=True)

    s = sub.add_parser("rotate", help="Seite drehen (1-basiert)")
    s.add_argument("pdf")
    s.add_argument("--page", type=int, required=True)
    s.add_argument("--degrees", type=int, default=90)

    s = sub.add_parser("ocr", help="OCR Bild oder PDF-Seite")
    s.add_argument("source")
    s.add_argument("--page", type=int, default=None, help="PDF-Seite (1-basiert)")
    s.add_argument("--lang", default="deu+eng")
    s.add_argument("--out-dir", default=None)

    s = sub.add_parser("redact-add", help="Schwärzungsrechteck ins Sidecar")
    s.add_argument("pdf")
    s.add_argument("--page", type=int, required=True)
    s.add_argument("--x", type=float, required=True)
    s.add_argument("--y", type=float, required=True)
    s.add_argument("--width", type=float, required=True)
    s.add_argument("--height", type=float, required=True)

    s = sub.add_parser("redact-apply", help="Schwärzungen anwenden")
    s.add_argument("pdf")
    s.add_argument("--out", default=None)
    s.add_argument("--overlay", action="store_true", help="nur Overlay statt echtem Schwärzen")
    s.add_argument("--password", default=None)

    lic = sub.add_parser("license", help="Lizenz / Keygen")
    lic_sub = lic.add_subparsers(dest="lic_cmd", required=True)
    lic_sub.add_parser("status")
    g = lic_sub.add_parser("generate")
    g.add_argument("email")
    g.add_argument("--days", type=int, default=None)
    v = lic_sub.add_parser("verify")
    v.add_argument("key")
    a = lic_sub.add_parser("activate")
    a.add_argument("key")
    a.add_argument("--state", default=None)

    s = sub.add_parser("encrypt", help="PDF-Passwort setzen (AES-256)")
    s.add_argument("pdf")
    s.add_argument("--user", required=True)
    s.add_argument("--owner", default=None)
    s.add_argument("--out", default=None)

    s = sub.add_parser("decrypt", help="PDF-Passwort entfernen")
    s.add_argument("pdf")
    s.add_argument("--password", required=True)
    s.add_argument("--out", default=None)

    s = sub.add_parser("ann-shape", help="Form-Annotation (ellipse/rectangle/triangle/rounded_rect)")
    s.add_argument("pdf")
    s.add_argument("--page", type=int, required=True)
    s.add_argument("--type", dest="kind", required=True)
    s.add_argument("--x", type=float, required=True)
    s.add_argument("--y", type=float, required=True)
    s.add_argument("--width", type=float, required=True)
    s.add_argument("--height", type=float, required=True)
    s.add_argument("--color", default="#2980B9")
    s.add_argument("--fill", default="", dest="fill_color")
    s.add_argument("--stroke", type=float, default=2.0)
    s.add_argument("--filled", action="store_true")

    s = sub.add_parser("ann-stamp", help="Text-Stempel (Paid/Bezahlt/Rechnung/Datum/custom)")
    s.add_argument("pdf")
    s.add_argument("--page", type=int, default=1)
    s.add_argument("--text", required=True)
    s.add_argument("--x", type=float, default=72)
    s.add_argument("--y", type=float, default=72)
    s.add_argument("--color", default="#C0392B")
    s.add_argument("--date", action="store_true")

    s = sub.add_parser("ann-highlight-para", help="Absatz-Highlight unter Rechteck")
    s.add_argument("pdf")
    s.add_argument("--page", type=int, required=True)
    s.add_argument("--x", type=float, required=True)
    s.add_argument("--y", type=float, required=True)
    s.add_argument("--width", type=float, required=True)
    s.add_argument("--height", type=float, required=True)
    s.add_argument("--color", default="#FFFF00")
    s.add_argument("--scale", type=float, default=1.0)

    s = sub.add_parser("stamp-list", help="Definierbare Stempel (Builtin + custom)")
    s = sub.add_parser("stamp-add", help="Benutzer-Stempel anlegen")
    s.add_argument("label")
    s.add_argument("--color", default="#C0392B")

    s = sub.add_parser("auto-format", help="Automatische Formatierung (Text oder PDF+TOC)")
    s.add_argument("source", nargs="?", default=None, help="PDF-Pfad oder weglassen mit --text")
    s.add_argument("--text", default=None, help="Plaintext/Markdown statt PDF")
    s.add_argument("--out", default=None)
    s.add_argument("--max-level", type=int, default=3)
    s.add_argument("--no-toc", action="store_true")

    s = sub.add_parser("toc", help="Inhaltsverzeichnis erzeugen (PDF-Outline oder Markdown)")
    s.add_argument("pdf", nargs="?", default=None)
    s.add_argument("--text", default=None)
    s.add_argument("--out", default=None)
    s.add_argument("--max-level", type=int, default=3)
    s.add_argument("--dry-run", action="store_true", help="Outline nicht schreiben")

    s = sub.add_parser("fonts", help="Systemschriften auflisten (Windows Fonts / Qt)")
    s.add_argument("--files", action="store_true", help="auch Dateinamen")

    s = sub.add_parser("styles", help="Style-Presets (H1/H2/H3/Body/Quote)")

    s = sub.add_parser("find-replace", help="Suchen/Ersetzen in Text oder PDF")
    s.add_argument("source", nargs="?", default=None, help="PDF-Pfad")
    s.add_argument("--text", default=None)
    s.add_argument("--find", required=True)
    s.add_argument("--replace", required=True)
    s.add_argument("--case", action="store_true", help="Groß-/Kleinschreibung beachten")
    s.add_argument("--count", type=int, default=0, help="max. Ersetzungen (Text; 0=alle)")
    s.add_argument("--max", type=int, default=50, dest="max_replacements")

    s = sub.add_parser("page-formats", help="Seitenformate-Presets (US/DIN/Buch) — 2.6.14")
    s.add_argument("--unit", default="mm", choices=("mm", "inch"))

    s = sub.add_parser("set-page-format", help="Seitenformat-Preset auf PDF anwenden")
    s.add_argument("pdf")
    s.add_argument("--format", required=True, dest="page_format")
    s.add_argument("--page", type=int, default=1)
    s.add_argument("--all", action="store_true", dest="all_pages")

    s = sub.add_parser(
        "header-footer",
        help="Kopf-/Fußzeile bakken (Titel/Autor/Seitenzahl) — 2.6.14",
    )
    s.add_argument("pdf")
    s.add_argument("--out", default=None)
    s.add_argument("--header", default="{title}")
    s.add_argument("--footer", default="{author} — {n} / {total}")
    s.add_argument("--title", default=None)
    s.add_argument("--author", default=None)
    s.add_argument("--creator", default=None)
    s.add_argument("--no-page-numbers", action="store_true")
    s.add_argument("--page-template", default="{n} / {total}")

    s = sub.add_parser("paragraph-format", help="Absatzausrichtung/Abstände (Text)")
    s.add_argument("--text", required=True)
    s.add_argument("--align", default=None, choices=("left", "center", "right", "justify"))
    s.add_argument("--line-spacing", type=float, default=None)
    s.add_argument("--space-before", type=float, default=None)
    s.add_argument("--space-after", type=float, default=None)
    s.add_argument("--index", type=int, default=None, help="Absatzindex 0-basiert")
    s.add_argument("--style", default=None, help="Style-Preset-ID (body/heading1/…)")

    s = sub.add_parser("paragraph-styles", help="Style-Presets inkl. Absatzattribute")

    s = sub.add_parser("satzspiegel", help="Satzspiegel für Seitenformat — 2.6.14")
    s.add_argument("--format", default="A4", dest="page_format")
    s.add_argument("--columns", type=int, default=1)
    s.add_argument("--gutter", type=float, default=5.0, help="Spaltenabstand mm")

    s = sub.add_parser("satzspiegel-list", help="Alle Satzspiegel-Presets")
    s.add_argument("--columns", type=int, default=1)

    s = sub.add_parser("master-pages", help="Musterseiten-Presets auflisten — 2.6.14")

    s = sub.add_parser(
        "apply-master",
        help="Musterseite auf PDF bakken (HF/Seitenzahlen) — 2.6.14",
    )
    s.add_argument("pdf")
    s.add_argument("--master", default="Standard", help="Preset: Standard/Buch/Sachbuch/Minimal")
    s.add_argument("--out", default=None)
    s.add_argument("--title", default=None)
    s.add_argument("--author", default=None)
    s.add_argument("--creator", default=None)
    s.add_argument("--start-page", type=int, default=None)

    s = sub.add_parser("layout-new", help="Leeres Layout (Frames) — 2.6.14")
    s.add_argument("--format", default=None, dest="page_format")
    s.add_argument("--out", default=None, help="JSON-Pfad speichern")

    s = sub.add_parser("layout-flow", help="Text in verkettete Rahmen fließen")
    s.add_argument("--text", required=True)
    s.add_argument("--layout", default=None, help="Layout-JSON Pfad")
    s.add_argument("--columns", type=int, default=None)
    s.add_argument("--pages", type=int, default=None)
    s.add_argument("--start", default=None, dest="start_id")
    s.add_argument("--out", default=None, help="Layout-JSON speichern")
    s.add_argument(
        "--around-wrap",
        action="store_true",
        help="Textumfluss um Bildrahmen (2.6.14)",
    )

    s = sub.add_parser("layout-move", help="Rahmen verschieben")
    s.add_argument("--layout", required=True, help="Layout-JSON")
    s.add_argument("--id", required=True, dest="frame_id")
    s.add_argument("--x", type=float, required=True)
    s.add_argument("--y", type=float, required=True)

    s = sub.add_parser("layout-resize", help="Rahmen skalieren")
    s.add_argument("--layout", required=True, help="Layout-JSON")
    s.add_argument("--id", required=True, dest="frame_id")
    s.add_argument("--width", type=float, required=True)
    s.add_argument("--height", type=float, required=True)

    s = sub.add_parser("layout-frames", help="Rahmen eines Layouts auflisten")
    s.add_argument("--layout", required=True)

    s = sub.add_parser(
        "typography",
        help="Tracking/Kerning/Leading/Drop-Cap/Zeichenstil — 2.6.14",
    )
    s.add_argument("--text", required=True)
    s.add_argument("--tracking", type=float, default=None)
    s.add_argument("--kerning", type=float, default=None)
    s.add_argument("--leading", type=float, default=None)
    s.add_argument("--drop-cap-lines", type=int, default=None)
    s.add_argument("--drop-cap-chars", type=int, default=None)
    s.add_argument("--char-style", default=None)
    s.add_argument("--align", default=None, choices=("left", "center", "right", "justify"))
    s.add_argument("--index", type=int, default=None)

    s = sub.add_parser("drop-cap", help="Drop Cap / Initial auf Absatz — 2.6.14")
    s.add_argument("--text", required=True)
    s.add_argument("--lines", type=int, default=3)
    s.add_argument("--chars", type=int, default=1)
    s.add_argument("--index", type=int, default=0)

    s = sub.add_parser("character-styles", help="Zeichenstile auflisten — 2.6.14")

    s = sub.add_parser("typography-styles", help="Absatzstile inkl. Typo-Defaults — 2.6.14")

    s = sub.add_parser("hyphenate", help="Silbentrennung (Soft-Hyphens) — 2.6.14")
    s.add_argument("--text", required=True)
    s.add_argument("--lang", default="de", help="de|en (+ registrierte Sprachen)")

    s = sub.add_parser("hyphenation-langs", help="Verfügbare Silbentrennungs-Sprachen")

    s = sub.add_parser(
        "layout-text-wrap",
        help="Textumfluss um Bildrahmen setzen — 2.6.14",
    )
    s.add_argument("--layout", required=True)
    s.add_argument("--id", required=True, dest="frame_id")
    s.add_argument(
        "--mode",
        default="bounding_box",
        choices=("none", "bounding_box", "jump_object", "contour"),
    )
    s.add_argument("--padding", type=float, default=None)

    s = sub.add_parser(
        "layout-flow-wrap",
        help="Text um Bildrahmen fließen lassen — 2.6.14",
    )
    s.add_argument("--text", required=True)
    s.add_argument("--layout", default=None)
    s.add_argument("--start", default=None, dest="start_id")
    s.add_argument("--out", default=None)

    s = sub.add_parser("table-create", help="Tabelle erstellen — 2.6.14")
    s.add_argument("--rows", type=int, default=3)
    s.add_argument("--cols", type=int, default=3)
    s.add_argument("--id", default="t1", dest="table_id")
    s.add_argument("--align", default="")
    s.add_argument("--style", default="default")
    s.add_argument("--no-header", action="store_true")
    s.add_argument("--data-json", default=None, help="JSON-Array von Zeilen")

    s = sub.add_parser("table-format", help="Tabelle formatieren — 2.6.14")
    s.add_argument("--text", required=True)
    s.add_argument("--align", default=None)
    s.add_argument("--style", default=None)
    s.add_argument("--border", default=None, choices=("0", "1"))
    s.add_argument("--header", default=None, choices=("0", "1"))

    s = sub.add_parser("table-sort", help="Tabelle sortieren — 2.6.14")
    s.add_argument("--text", required=True)
    s.add_argument("--column", type=int, default=0)
    s.add_argument("--reverse", action="store_true")
    s.add_argument("--alpha", action="store_true", help="alphabetisch statt numerisch")

    s = sub.add_parser("table-import-csv", help="CSV in Tabelle importieren — 2.6.14")
    s.add_argument("path")
    s.add_argument("--delimiter", default=None)
    s.add_argument("--id", default="csv1", dest="table_id")

    s = sub.add_parser("table-import-xlsx", help="Excel/.xlsx in Tabelle — 2.6.14")
    s.add_argument("path")
    s.add_argument("--sheet", default="0")
    s.add_argument("--id", default="xlsx1", dest="table_id")

    s = sub.add_parser("table-export", help="Tabelle als CSV/XLSX/MD/HTML — 2.6.14")
    s.add_argument("--text", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--fmt", default=None)

    s = sub.add_parser("table-styles", help="Tabellenstile auflisten — 2.6.14")

    s = sub.add_parser(
        "save",
        help="Dokument speichern/exportieren (docx/xlsx/pdf/txt/rtf/html/jpg) — 2.6.14",
    )
    s.add_argument("--text", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--fmt", default=None)
    s.add_argument("--title", default="InstantLens Doc")

    s = sub.add_parser(
        "export-doc",
        help="Dokument exportieren (Alias save) — 2.6.14",
    )
    s.add_argument("--text", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--fmt", default=None)
    s.add_argument("--title", default="InstantLens Doc")

    s = sub.add_parser("import-doc", help="Dokument importieren → Text — 2.6.14")
    s.add_argument("path")

    s = sub.add_parser("io-formats", help="Import-/Export-Formate auflisten — 2.6.14")

    s = sub.add_parser(
        "ocr-word-suite",
        help="OCR/Layout/ildocr → Word-Suite-Dokument — 2.6.15",
    )
    s.add_argument("source", nargs="?", default=None, help="Bild, PDF oder *.ildocr.*")
    s.add_argument("--text", default=None, help="Rohtext statt Datei")
    s.add_argument("--page", type=int, default=1, help="PDF-Seite (1-basiert)")
    s.add_argument("--lang", default="deu+eng")
    s.add_argument("--title", default=None)
    s.add_argument("--out", default=None, help="Optional: Text speichern")
    s.add_argument(
        "--no-auto-format",
        action="store_true",
        help="Kein Auto-Format (2.6.10)",
    )
    s.add_argument(
        "--no-layout",
        action="store_true",
        help="Kein Layout-OCR (nur plain editable)",
    )

    s = sub.add_parser(
        "import-ildocr",
        help="*.ildocr.txt / hOCR / TSV → Word-Suite — 2.6.15",
    )
    s.add_argument("path")
    s.add_argument("--title", default=None)
    s.add_argument("--out", default=None)
    s.add_argument("--no-auto-format", action="store_true")

    s = sub.add_parser(
        "ki-wizards",
        help="Isolierte KI-Dokument-Wizards auflisten — 2.6.16",
    )

    s = sub.add_parser(
        "ki-wizard",
        help="KI-Wizard: Formular/Anschreiben/Kaufvertrag/Rechnung — 2.6.16",
    )
    s.add_argument(
        "kind",
        help="formular | anschreiben | kaufvertrag | rechnung",
    )
    s.add_argument(
        "--field",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Feld setzen (mehrfach); z.B. --field betreff=Anfrage",
    )
    s.add_argument(
        "--company",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Unternehmensfeld (firma/adresse/ust_id/…)",
    )
    s.add_argument("--title", default=None)
    s.add_argument("--out", default=None, help="Optional: Text speichern")
    s.add_argument(
        "--use-llm",
        action="store_true",
        help="Optionalen LLM-Hook nutzen (nur wenn registriert)",
    )
    s.add_argument(
        "--company-mode",
        action="store_true",
        help="Unternehmensmodus erzwingen",
    )

    return p


def run(argv: list[str] | None = None) -> int:
    from ild import api

    p = build_parser()
    args = p.parse_args(argv)
    js = bool(args.json)
    try:
        if args.cmd == "version":
            _print({"version": __version__, "product": "InstantLens Doc"}, as_json=js)
            return 0
        if args.cmd == "info":
            _print(api.open_info(args.pdf, password=args.password), as_json=js)
            return 0
        if args.cmd == "pages":
            n = api.page_count(args.pdf, password=args.password)
            _print({"pages": n, "path": str(Path(args.pdf))} if js else n, as_json=js)
            return 0
        if args.cmd == "export":
            dest = api.export_page(
                args.pdf, args.page, args.out, dpi=args.dpi, fmt=args.fmt
            )
            _print({"out": str(dest)}, as_json=js)
            return 0
        if args.cmd == "merge":
            dest = api.merge_pdfs(args.pdfs, args.out)
            _print({"out": str(dest)}, as_json=js)
            return 0
        if args.cmd == "split":
            files = api.split_pdf(args.pdf, args.out_dir)
            _print({"files": [str(f) for f in files]}, as_json=js)
            return 0
        if args.cmd == "rotate":
            api.rotate_page(args.pdf, args.page, args.degrees)
            _print({"ok": True, "path": args.pdf}, as_json=js)
            return 0
        if args.cmd == "ocr":
            src = Path(args.source)
            if src.suffix.lower() == ".pdf" or args.page is not None:
                data = api.ocr_pdf_page(src, page=args.page or 1, lang=args.lang)
            else:
                data = api.ocr_image(src, lang=args.lang, out_dir=args.out_dir)
            _print(data, as_json=js)
            return 0
        if args.cmd == "redact-add":
            sidecar = api.add_redaction(
                args.pdf,
                page=args.page,
                x=args.x,
                y=args.y,
                width=args.width,
                height=args.height,
            )
            _print({"sidecar": str(sidecar)}, as_json=js)
            return 0
        if args.cmd == "redact-apply":
            dest = api.apply_redactions(
                args.pdf,
                out=args.out,
                true_redact=not args.overlay,
                password=args.password,
            )
            _print({"out": str(dest)}, as_json=js)
            return 0
        if args.cmd == "license":
            if args.lic_cmd == "status":
                _print(api.license_status(), as_json=js)
                return 0
            if args.lic_cmd == "generate":
                key = api.generate_key(args.email, days=args.days)
                _print({"key": key, "email": args.email} if js else key, as_json=js)
                return 0
            if args.lic_cmd == "verify":
                data = api.verify_key(args.key)
                _print(data, as_json=js)
                return 0 if data.get("ok") else 1
            if args.lic_cmd == "activate":
                data = api.activate_license(args.key, state_path=args.state)
                _print(data, as_json=js)
                return 0 if data.get("ok") else 1
        if args.cmd == "encrypt":
            dest = api.encrypt_pdf(
                args.pdf,
                user_password=args.user,
                owner_password=args.owner,
                out=args.out,
            )
            _print({"out": str(dest)}, as_json=js)
            return 0
        if args.cmd == "decrypt":
            dest = api.remove_password(args.pdf, args.password, out=args.out)
            _print({"out": str(dest)}, as_json=js)
            return 0
        if args.cmd == "ann-shape":
            data = api.add_shape(
                args.pdf,
                page=args.page,
                kind=args.kind,
                x=args.x,
                y=args.y,
                width=args.width,
                height=args.height,
                color=args.color,
                fill_color=args.fill_color,
                stroke_width=args.stroke,
                filled=True if args.filled else None,
            )
            _print(data, as_json=js)
            return 0
        if args.cmd == "ann-stamp":
            data = api.add_stamp(
                args.pdf,
                page=args.page,
                text=args.text,
                x=args.x,
                y=args.y,
                color=args.color,
                include_date=args.date,
            )
            _print(data, as_json=js)
            return 0
        if args.cmd == "ann-highlight-para":
            data = api.highlight_paragraphs(
                args.pdf,
                page=args.page,
                x=args.x,
                y=args.y,
                width=args.width,
                height=args.height,
                color=args.color,
                scale=args.scale,
            )
            _print(data, as_json=js)
            return 0
        if args.cmd == "stamp-list":
            items = api.list_stamps()
            if js:
                _print(items, as_json=True)
            else:
                for rec in items:
                    kind = "custom" if rec.get("custom") else "builtin"
                    print(f"{rec.get('label')}\t{rec.get('color')}\t{kind}")
            return 0
        if args.cmd == "stamp-add":
            data = api.add_custom_stamp_def(args.label, color=args.color)
            _print(data, as_json=js)
            return 0
        if args.cmd == "auto-format":
            if args.text is not None:
                data = api.auto_format_text(args.text)
            elif args.source:
                data = api.auto_format_pdf(
                    args.source,
                    out=args.out,
                    max_level=args.max_level,
                    update_toc=not args.no_toc,
                )
            else:
                return _fail("source (PDF) oder --text erforderlich")
            _print(data, as_json=js)
            return 0
        if args.cmd == "toc":
            data = api.generate_toc(
                path=args.pdf,
                text=args.text,
                out=args.out,
                max_level=args.max_level,
                write=not args.dry_run,
            )
            _print(data, as_json=js)
            return 0
        if args.cmd == "fonts":
            fonts = api.list_system_fonts(include_files=args.files)
            if js:
                _print(fonts, as_json=True)
            else:
                for name in fonts:
                    print(name)
            return 0
        if args.cmd == "styles":
            presets = api.list_style_presets()
            _print(presets, as_json=js or True)
            return 0
        if args.cmd == "find-replace":
            data = api.find_replace(
                text=args.text,
                path=args.source,
                find=args.find,
                replace=args.replace,
                case_sensitive=args.case,
                count=args.count,
                max_replacements=args.max_replacements,
            )
            _print(data, as_json=js)
            return 0
        if args.cmd == "page-formats":
            data = api.list_page_formats(unit=args.unit)
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "set-page-format":
            data = api.set_page_format(
                args.pdf,
                args.page_format,
                page=args.page,
                all_pages=args.all_pages,
            )
            _print(data, as_json=js)
            return 0
        if args.cmd == "header-footer":
            data = api.apply_header_footer(
                args.pdf,
                out=args.out,
                header=args.header,
                footer=args.footer,
                include_page_numbers=not args.no_page_numbers,
                page_template=args.page_template,
                title=args.title,
                author=args.author,
                creator=args.creator,
            )
            _print(data, as_json=js)
            return 0
        if args.cmd == "paragraph-format":
            data = api.apply_paragraph_format(
                text=args.text,
                alignment=args.align,
                line_spacing=args.line_spacing,
                space_before_pt=args.space_before,
                space_after_pt=args.space_after,
                paragraph_index=args.index,
                style_id=args.style,
            )
            _print(data, as_json=js)
            return 0
        if args.cmd == "paragraph-styles":
            data = api.list_paragraph_styles()
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "satzspiegel":
            data = api.satzspiegel(
                args.page_format, columns=args.columns, gutter_mm=args.gutter
            )
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "satzspiegel-list":
            data = api.list_satzspiegel(columns=args.columns)
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "master-pages":
            data = api.list_master_pages()
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "apply-master":
            data = api.apply_master_page(
                args.pdf,
                args.master,
                out=args.out,
                title=args.title,
                author=args.author,
                creator=args.creator,
                start_page=args.start_page,
            )
            _print(data, as_json=js)
            return 0
        if args.cmd == "layout-new":
            data = api.new_layout(format_name=args.page_format)
            if args.out:
                from instantlensdoc.core.layout import LayoutDocument

                LayoutDocument.from_dict(data).save(args.out)
                data = {"path": str(Path(args.out)), "layout": data}
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "layout-flow":
            from instantlensdoc.core.layout import LayoutDocument

            layout_path = args.layout
            data = api.layout_flow_text(
                args.text,
                start_id=args.start_id,
                path=layout_path,
                columns=args.columns,
                pages=args.pages,
                around_wrap=bool(getattr(args, "around_wrap", False)),
            )
            save_to = args.out or layout_path
            if save_to:
                LayoutDocument.from_dict(data["layout"]).save(save_to)
                data["path"] = str(Path(save_to))
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "layout-move":
            data = api.layout_move_frame(
                args.frame_id, args.x, args.y, path=args.layout
            )
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "layout-resize":
            data = api.layout_resize_frame(
                args.frame_id, args.width, args.height, path=args.layout
            )
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "layout-frames":
            data = api.layout_list_frames(path=args.layout)
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "typography":
            data = api.apply_typography(
                text=args.text,
                tracking=args.tracking,
                kerning=args.kerning,
                leading=args.leading,
                drop_cap_lines=args.drop_cap_lines,
                drop_cap_chars=args.drop_cap_chars,
                char_style_id=args.char_style,
                alignment=args.align,
                paragraph_index=args.index,
            )
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "drop-cap":
            data = api.apply_drop_cap(
                args.text,
                lines=args.lines,
                chars=args.chars,
                paragraph_index=args.index,
            )
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "character-styles":
            data = api.list_character_styles()
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "typography-styles":
            data = api.list_typography_styles()
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "hyphenate":
            data = api.hyphenate(args.text, lang=args.lang)
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "hyphenation-langs":
            data = api.list_hyphenation_languages()
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "layout-text-wrap":
            data = api.layout_set_text_wrap(
                args.frame_id,
                args.mode,
                padding=args.padding,
                path=args.layout,
            )
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "layout-flow-wrap":
            from instantlensdoc.core.layout import LayoutDocument

            data = api.layout_flow_text_wrap(
                args.text, start_id=args.start_id, path=args.layout
            )
            save_to = args.out or args.layout
            if save_to:
                LayoutDocument.from_dict(data["layout"]).save(save_to)
                data["path"] = str(Path(save_to))
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "table-create":
            data_rows = None
            if args.data_json:
                data_rows = json.loads(args.data_json)
            data = api.create_table(
                args.rows,
                args.cols,
                header=not args.no_header,
                data=data_rows,
                table_id=args.table_id,
                align=args.align,
                style=args.style,
            )
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "table-format":
            data = api.format_table(
                text=args.text,
                align=args.align,
                style=args.style,
                border=None if args.border is None else args.border == "1",
                header=None if args.header is None else args.header == "1",
            )
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "table-sort":
            data = api.sort_table(
                text=args.text,
                column=args.column,
                reverse=bool(args.reverse),
                numeric=not bool(args.alpha),
            )
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "table-import-csv":
            data = api.import_table_csv(
                args.path, delimiter=args.delimiter, table_id=args.table_id
            )
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "table-import-xlsx":
            sheet: str | int = args.sheet
            if isinstance(sheet, str) and sheet.isdigit():
                sheet = int(sheet)
            data = api.import_table_xlsx(args.path, sheet=sheet, table_id=args.table_id)
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "table-export":
            data = api.export_table(text=args.text, out=args.out, fmt=args.fmt)
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "table-styles":
            data = api.list_table_styles()
            _print(data, as_json=js or True)
            return 0
        if args.cmd in ("save", "export-doc"):
            data = api.save_document(
                args.text, args.out, fmt=args.fmt, title=args.title
            )
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "import-doc":
            data = api.import_document(args.path)
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "io-formats":
            data = api.list_io_formats()
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "ocr-word-suite":
            data = api.ocr_to_word_suite(
                args.source,
                text=args.text,
                page=args.page,
                lang=args.lang,
                auto_format=not args.no_auto_format,
                title=args.title,
                prefer_layout=not args.no_layout,
                out=args.out,
            )
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "import-ildocr":
            data = api.import_ildocr(
                args.path,
                auto_format=not args.no_auto_format,
                title=args.title,
                out=args.out,
            )
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "ki-wizards":
            data = api.list_ki_wizards()
            _print(data, as_json=js or True)
            return 0
        if args.cmd == "ki-wizard":

            def _kv_list(items):
                out = {}
                for item in items or []:
                    if "=" not in item:
                        raise ValueError(f"Erwarte KEY=VALUE, got {item!r}")
                    k, v = item.split("=", 1)
                    out[k.strip()] = v.strip()
                return out

            fields = _kv_list(args.field)
            company = _kv_list(args.company)
            data = api.generate_ki_document(
                args.kind,
                fields=fields or None,
                company=company or None,
                company_mode=True if args.company_mode or company else None,
                title=args.title,
                use_llm=bool(args.use_llm),
                out=args.out,
            )
            _print(data, as_json=js or True)
            return 0
        return _fail("unbekanntes Kommando")
    except FileNotFoundError as e:
        return _fail(f"Datei nicht gefunden: {e}", 2)
    except Exception as e:
        return _fail(str(e), 1)


def main(argv: list[str] | None = None) -> int:
    return run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
