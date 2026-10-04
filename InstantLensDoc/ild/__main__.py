"""python -m ild — Scripting-CLI InstantLens Doc 2.6.9."""

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
        return _fail("unbekanntes Kommando")
    except FileNotFoundError as e:
        return _fail(f"Datei nicht gefunden: {e}", 2)
    except Exception as e:
        return _fail(str(e), 1)


def main(argv: list[str] | None = None) -> int:
    return run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
