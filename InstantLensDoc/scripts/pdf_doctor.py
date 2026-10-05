#!/usr/bin/env python3
"""pdf_doctor — Warum öffnet diese PDF nicht? (InstantLens Doc 2.6.54)

Prüft eine Datei **nach Inhalt**, nicht nach Endung, und druckt alles, was zur
Diagnose nötig ist:

  * Größe, erste 16/64 Bytes (hex + ASCII), erkannter Typ (PDF / DOCX-ZIP / HTML /
    RTF / Text / leer …), Position des ``%PDF-``-Headers, ``%%EOF``/``startxref``
  * Trailer-Ausschnitt (letzte 512 Bytes als Text), xref-Zähler, Objektzähler
  * ``/Producer`` / ``/Creator`` (wer hat die Datei geschrieben?)
  * pikepdf/qpdf: öffnet? Seitenzahl? Reparatur möglich?  (optional installiert)
  * pypdfium2/PDFium: öffnet? Seitenzahl? Fehlertext?       (optional installiert)
  * Empfehlung in Deutsch; ``--recover`` kopiert eine falsch benannte Datei unter
    der richtigen Endung (Original bleibt unverändert)

Windows (aus dem entpackten Pack bzw. D:\\AI_Temp\\InstantLensDoc-2654):

    python scripts\\pdf_doctor.py "C:\\Users\\Lenovo\\Desktop\\Dunning_Kruger_Effekt_1.pdf"
    python scripts\\pdf_doctor.py "C:\\…\\Datei.pdf" --recover      # Kopie mit richtiger Endung
    python scripts\\pdf_doctor.py "C:\\…\\Datei.pdf" --json         # maschinenlesbar

Exit-Code: 0 = gültiges PDF (beide Parser), 1 = kein PDF / nicht lesbar,
2 = PDF, aber mindestens ein Parser scheitert (Reparatur-Kandidat), 3 = Datei fehlt.
Läuft auch ohne pikepdf/pypdfium2 (dann nur Byte-Analyse).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _hex(b: bytes) -> str:
    return " ".join(f"{x:02x}" for x in b)


def _ascii(b: bytes) -> str:
    return "".join(chr(x) if 32 <= x < 127 else "." for x in b)


def _fmt_size(n: int) -> str:
    return f"{n:,} Byte".replace(",", ".") + (f" ({n / 1024 / 1024:.1f} MB)" if n >= 1024 * 1024 else "")


def _sniff(path: Path) -> dict:
    """Byte-Analyse — nutzt ild_pdf.pdf_sniff wenn vorhanden, sonst eingebaute Kurzfassung."""
    try:
        from ild_pdf.pdf_sniff import describe_non_pdf_de, sniff_file

        r = sniff_file(path)
        return {
            "size": r.size,
            "kind": r.kind,
            "label": r.label_de,
            "detail": r.detail,
            "head16_hex": r.head_hex,
            "head16_ascii": r.head_ascii,
            "pdf_header_offset": r.pdf_header_offset,
            "pdf_version": r.pdf_version,
            "has_eof": r.has_eof,
            "has_startxref": r.has_startxref,
            "is_pdf_like": r.is_pdf_like,
            "suggested_extension": r.suggested_extension,
            "advice": describe_non_pdf_de(r) if not r.is_pdf_like or r.kind != "pdf" else "",
            "zip_names": r.zip_names[:20],
        }
    except Exception:
        pass
    size = path.stat().st_size
    with open(path, "rb") as fh:
        head = fh.read(1100)
        fh.seek(max(0, size - 4096))
        tail = fh.read(4096)
    off = head.find(b"%PDF-")
    kind, label, ext = "unknown", "unbekannt", ""
    if size == 0:
        kind, label = "empty", "leere Datei (0 Byte)"
    elif off >= 0:
        kind, label = ("pdf" if off == 0 else "pdf-junk-prefix"), "PDF"
        if b"%%EOF" not in tail:
            kind, label = "pdf-truncated", "PDF ohne %%EOF"
    elif head.startswith(b"PK\x03\x04"):
        kind, label, ext = "zip", "ZIP-Archiv", ".zip"
        try:
            names = zipfile.ZipFile(path).namelist()
            if "word/document.xml" in names:
                kind, label, ext = "zip-docx", "Word-Dokument (DOCX)", ".docx"
        except Exception:
            pass
    elif head.lstrip().lower().startswith((b"<!doctype", b"<html")):
        kind, label, ext = "html", "HTML", ".html"
    elif head.lstrip().startswith(b"{\\rtf"):
        kind, label, ext = "rtf", "RTF", ".rtf"
    return {
        "size": size,
        "kind": kind,
        "label": label,
        "detail": "",
        "head16_hex": _hex(head[:16]),
        "head16_ascii": _ascii(head[:16]),
        "pdf_header_offset": off,
        "pdf_version": head[off + 5 : off + 8].decode("ascii", "replace") if off >= 0 else "",
        "has_eof": b"%%EOF" in tail,
        "has_startxref": b"startxref" in tail,
        "is_pdf_like": kind.startswith("pdf"),
        "suggested_extension": ext,
        "advice": "" if kind == "pdf" else f"Datei ist {label}, kein gültiges PDF.",
        "zip_names": [],
    }


def _structure(path: Path, size: int) -> dict:
    """Trailer-Text, xref-/obj-Zähler, Producer/Creator per Regex (ohne Parser)."""
    out: dict = {}
    with open(path, "rb") as fh:
        fh.seek(max(0, size - 512))
        tail = fh.read(512)
        fh.seek(0)
        data = fh.read() if size <= 64 * 1024 * 1024 else b""
    out["tail512_text"] = tail.decode("latin-1", "replace").replace("\r", "\\r")
    if data:
        out["xref_count"] = len(re.findall(rb"(?m)^xref\b", data))
        out["startxref_count"] = data.count(b"startxref")
        out["trailer_count"] = data.count(b"trailer")
        out["obj_count"] = len(re.findall(rb"\b\d+ \d+ obj\b", data))
        out["objstm_count"] = data.count(b"/ObjStm")
        out["eof_count"] = data.count(b"%%EOF")
        out["linearized"] = b"/Linearized" in data[:2048]
        out["encrypted_marker"] = b"/Encrypt" in data
        m = re.search(rb"/Producer\s*\((.{0,200}?)\)", data, re.S)
        out["producer_raw"] = m.group(1).decode("latin-1", "replace") if m else ""
        m = re.search(rb"/Creator\s*\((.{0,200}?)\)", data, re.S)
        out["creator_raw"] = m.group(1).decode("latin-1", "replace") if m else ""
        m = re.search(rb"xmp:CreatorTool[^>]*>([^<]{0,200})<", data)
        out["xmp_creator_tool"] = m.group(1).decode("utf-8", "replace") if m else ""
        m = re.search(rb"pdf:Producer[^>]*>([^<]{0,200})<", data)
        out["xmp_producer"] = m.group(1).decode("utf-8", "replace") if m else ""
    return out


def _pikepdf(path: Path) -> dict:
    out: dict = {"available": False}
    try:
        import pikepdf
    except Exception as e:
        out["error"] = f"pikepdf nicht installiert: {e}"
        return out
    out["available"] = True
    out["version"] = pikepdf.__version__
    try:
        with pikepdf.open(str(path)) as pdf:
            out["ok"] = True
            out["pages"] = len(pdf.pages)
            out["pdf_version"] = str(pdf.pdf_version)
            try:
                info = pdf.docinfo
                out["producer"] = str(info.get("/Producer", "")) if info is not None else ""
                out["creator"] = str(info.get("/Creator", "")) if info is not None else ""
                out["title"] = str(info.get("/Title", "")) if info is not None else ""
            except Exception:
                pass
            out["encrypted"] = bool(pdf.is_encrypted)
            try:
                out["repaired"] = bool(getattr(pdf, "_repaired", False))
            except Exception:
                pass
    except Exception as e:
        out["ok"] = False
        out["error"] = f"{type(e).__name__}: {e}"
    return out


def _pdfium(path: Path) -> dict:
    out: dict = {"available": False}
    try:
        import pypdfium2 as pdfium
    except Exception as e:
        out["error"] = f"pypdfium2 nicht installiert: {e}"
        return out
    out["available"] = True
    try:
        out["version"] = str(getattr(pdfium, "PYPDFIUM_INFO", "") or getattr(pdfium, "V_PYPDFIUM2", ""))
        info = getattr(pdfium, "PDFIUM_INFO", None)
        out["pdfium_build"] = str(getattr(info, "build", "") or "")
    except Exception:
        pass
    try:
        try:
            from ild_pdf.pdfium_open import PDFIUM_LOCK
        except Exception:
            import threading

            PDFIUM_LOCK = threading.RLock()  # type: ignore[assignment]
        with PDFIUM_LOCK:
            doc = pdfium.PdfDocument(path.read_bytes())
            try:
                out["ok"] = True
                out["pages"] = len(doc)
                if len(doc):
                    page = doc[0]
                    try:
                        out["page1_size_pt"] = [round(page.get_width(), 1), round(page.get_height(), 1)]
                        txt = page.get_textpage().get_text_range()
                        out["page1_text_chars"] = len(txt)
                        out["page1_text_preview"] = " ".join(txt.split())[:160]
                    finally:
                        page.close()
            finally:
                doc.close()
    except Exception as e:
        out["ok"] = False
        out["error"] = f"{type(e).__name__}: {e}"
    return out


def _verdict(sn: dict, pk: dict, pf: dict) -> tuple[int, str]:
    if not sn["is_pdf_like"]:
        return 1, sn.get("advice") or f"Kein PDF: {sn['label']}"
    pk_ok = pk.get("ok") is True
    pf_ok = pf.get("ok") is True
    if pk.get("available") and pf.get("available"):
        if pk_ok and pf_ok:
            return 0, "Gültiges PDF — pikepdf und PDFium öffnen die Datei."
        if pk_ok and not pf_ok:
            return 2, (
                "PDFium lehnt die Datei ab, pikepdf/qpdf liest sie — InstantLens Doc öffnet sie über den "
                "Reparatur-Schritt (Schritt 3). Dauerhaft: Datei einmal neu speichern (PDF → Speichern unter)."
            )
        if not pk_ok and pf_ok:
            return 2, "pikepdf scheitert, PDFium öffnet — ungewöhnlich; Datei mit PDFium neu rendern/exportieren."
        return 2, (
            "Beide Parser scheitern trotz %PDF-Header — Datei beschädigt/unvollständig "
            f"({sn['label']}: {sn.get('detail') or '–'}). Quelle erneut exportieren."
        )
    if pk.get("available") or pf.get("available"):
        ok = pk_ok or pf_ok
        return (0 if ok else 2), ("Parser öffnet die Datei." if ok else "Parser scheitert — Datei beschädigt?")
    return 0, "Byte-Analyse: sieht nach PDF aus (keine Parser installiert — pip install pikepdf pypdfium2)."


def _recover(path: Path, sn: dict, dest: str | None) -> str:
    ext = sn.get("suggested_extension") or ""
    if not ext:
        return "Keine sichere Ziel-Endung für diesen Typ — nichts kopiert."
    target = Path(dest) if dest else path.with_suffix(ext)
    if target.exists():
        return f"Ziel existiert bereits, nichts überschrieben: {target}"
    import shutil

    shutil.copy2(path, target)
    return f"Kopie mit richtiger Endung angelegt: {target}  (Original unverändert)"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="PDF-Diagnose nach Inhalt (InstantLens Doc)")
    ap.add_argument("file", help="zu prüfende Datei")
    ap.add_argument("--json", action="store_true", help="JSON statt Text")
    ap.add_argument("--recover", action="store_true", help="Nicht-PDF unter richtiger Endung kopieren")
    ap.add_argument("--dest", default=None, help="Zielpfad für --recover")
    ap.add_argument("--no-parsers", action="store_true", help="nur Byte-Analyse (kein pikepdf/PDFium)")
    args = ap.parse_args(argv)

    path = Path(args.file).expanduser()
    if not path.is_file():
        msg = f"Datei nicht gefunden: {path}"
        print(json.dumps({"error": msg}, ensure_ascii=False) if args.json else msg)
        return 3

    sn = _sniff(path)
    st = _structure(path, int(sn["size"])) if sn["is_pdf_like"] else {}
    pk = {} if args.no_parsers or not sn["is_pdf_like"] else _pikepdf(path)
    pf = {} if args.no_parsers or not sn["is_pdf_like"] else _pdfium(path)
    code, verdict = _verdict(sn, pk, pf)
    recover_msg = _recover(path, sn, args.dest) if args.recover and not sn["is_pdf_like"] else ""

    report = {
        "file": str(path),
        "sniff": sn,
        "structure": st,
        "pikepdf": pk,
        "pdfium": pf,
        "exit_code": code,
        "verdict": verdict,
        "recover": recover_msg,
        "python": f"{sys.version_info.major}.{sys.version_info.minor} {sys.platform}",
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        return code

    with open(path, "rb") as fh:
        head64 = fh.read(64)
    print(f"pdf_doctor — {path}")
    print(f"  Größe        : {_fmt_size(int(sn['size']))}")
    print(f"  Typ (Inhalt) : {sn['label']}" + (f" — {sn['detail']}" if sn.get("detail") else ""))
    print(f"  Header 16 B  : {sn['head16_hex']}   {sn['head16_ascii']}")
    print(f"  Header 64 B  : {_ascii(head64)}")
    if sn["is_pdf_like"]:
        print(
            f"  %PDF-Header  : Offset {sn['pdf_header_offset']} · Version {sn.get('pdf_version') or '?'} · "
            f"%%EOF {'ja' if sn['has_eof'] else 'NEIN'} · startxref {'ja' if sn['has_startxref'] else 'NEIN'}"
        )
        if st:
            print(
                f"  Struktur     : xref {st.get('xref_count', '?')} · startxref {st.get('startxref_count', '?')} · "
                f"trailer {st.get('trailer_count', '?')} · obj {st.get('obj_count', '?')} · ObjStm {st.get('objstm_count', '?')} · "
                f"%%EOF {st.get('eof_count', '?')} · linearized {st.get('linearized')} · /Encrypt {st.get('encrypted_marker')}"
            )
            prod = st.get("producer_raw") or st.get("xmp_producer") or ""
            crea = st.get("creator_raw") or st.get("xmp_creator_tool") or ""
            print(f"  Producer     : {prod or '–'}")
            print(f"  Creator      : {crea or '–'}")
            print("  Trailer (Ende, 512 B):")
            for line in (st.get("tail512_text") or "").splitlines()[-8:]:
                print(f"      {line[:140]}")
    else:
        if sn.get("zip_names"):
            print(f"  ZIP-Einträge : {', '.join(sn['zip_names'][:8])}{' …' if len(sn['zip_names']) > 8 else ''}")
    if pk:
        if pk.get("available"):
            if pk.get("ok"):
                print(
                    f"  pikepdf {pk.get('version')}: OK · {pk.get('pages')} Seite(n) · PDF {pk.get('pdf_version')} · "
                    f"Producer {pk.get('producer') or '–'} · Creator {pk.get('creator') or '–'}"
                )
            else:
                print(f"  pikepdf {pk.get('version')}: FEHLER · {pk.get('error')}")
        else:
            print(f"  pikepdf      : {pk.get('error')}")
    if pf:
        if pf.get("available"):
            if pf.get("ok"):
                print(
                    f"  PDFium ({pf.get('version')}/{pf.get('pdfium_build')}): OK · {pf.get('pages')} Seite(n) · "
                    f"Seite 1 {pf.get('page1_size_pt')} pt · Text {pf.get('page1_text_chars')} Zeichen"
                )
                if pf.get("page1_text_preview"):
                    print(f"      „{pf['page1_text_preview']}“")
            else:
                print(f"  PDFium ({pf.get('version')}): FEHLER · {pf.get('error')}")
        else:
            print(f"  PDFium       : {pf.get('error')}")
    print(f"  Ergebnis     : [{code}] {verdict}")
    if recover_msg:
        print(f"  Recover      : {recover_msg}")
    elif not sn["is_pdf_like"] and sn.get("suggested_extension"):
        print(f"  Tipp         : --recover legt eine Kopie als {path.with_suffix(sn['suggested_extension']).name} an")
    return code


if __name__ == "__main__":
    sys.exit(main())
