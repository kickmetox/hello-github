"""Datei-Inhalt prüfen: Ist das wirklich ein PDF? — und Ausgabe-PDFs validieren (2.6.54).

Feldfall 2.6.53 (Windows): ``Dunning_Kruger_Effekt_1.pdf`` → PDFium „Data format
error“, pikepdf „unable to find trailer dictionary“, Edge „ungültiges Dateiformat“.
Die Datei begann mit ``50 4b 03 04`` (ZIP) und enthielt ``word/document.xml`` — ein
unverändertes Word-DOCX, das von einer älteren Version (≤ 2.6.42) über „Speichern
unter … .pdf“ **byte-identisch kopiert** statt exportiert wurde.

Dieses Modul liefert

* :func:`sniff_file` — Größe, erste 16 Bytes (hex), erkannter Typ (``pdf``,
  ``zip-docx``, ``html``, ``rtf``, ``text``, ``empty`` …), Position des
  ``%PDF-``-Headers, Vorhandensein von ``%%EOF``/``startxref``;
* :func:`describe_non_pdf_de` — deutscher Diagnosetext mit konkretem Hinweis;
* :func:`validate_pdf_file` / :func:`assert_valid_pdf` — Nachkontrolle **jeder**
  PDF-Ausgabe (Header, EOF, pikepdf-Öffnung, Seitenanzahl, optional PDFium).

Kein Qt, kein PDFium-Import auf Modulebene — überall importierbar.
"""

from __future__ import annotations

import logging
import os
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_log = logging.getLogger("ild_pdf.pdf_sniff")

PDF_MAGIC = b"%PDF-"
# Spezifikation: Header in den ersten 1024 Bytes erlaubt (Müll davor ist tolerierbar)
HEADER_SEARCH_WINDOW = 1024
# ``%%EOF`` wird in den letzten Bytes gesucht (Spezifikation: letzte 1024 Bytes; wir
# sind großzügiger, weil inkrementelle Updates/Anhängsel vorkommen)
EOF_SEARCH_WINDOW = 4096

KIND_PDF = "pdf"
KIND_PDF_JUNK_PREFIX = "pdf-junk-prefix"
KIND_PDF_TRUNCATED = "pdf-truncated"
KIND_EMPTY = "empty"
KIND_ZIP_DOCX = "zip-docx"
KIND_ZIP_XLSX = "zip-xlsx"
KIND_ZIP_PPTX = "zip-pptx"
KIND_ZIP_ODT = "zip-odt"
KIND_ZIP = "zip"
KIND_HTML = "html"
KIND_RTF = "rtf"
KIND_PNG = "png"
KIND_JPEG = "jpeg"
KIND_TEXT = "text"
KIND_UNKNOWN = "unknown"
KIND_UNREADABLE = "unreadable"

# Typen, bei denen sich ein PDFium-/pikepdf-Versuch überhaupt lohnt
PDF_LIKE_KINDS = frozenset({KIND_PDF, KIND_PDF_JUNK_PREFIX, KIND_PDF_TRUNCATED})

_KIND_LABEL_DE = {
    KIND_PDF: "PDF",
    KIND_PDF_JUNK_PREFIX: "PDF mit Fremdbytes vor dem Header",
    KIND_PDF_TRUNCATED: "PDF ohne %%EOF (abgeschnitten/unvollständig)",
    KIND_EMPTY: "leere Datei (0 Byte)",
    KIND_ZIP_DOCX: "Word-Dokument (DOCX, ZIP-Container)",
    KIND_ZIP_XLSX: "Excel-Arbeitsmappe (XLSX, ZIP-Container)",
    KIND_ZIP_PPTX: "PowerPoint-Präsentation (PPTX, ZIP-Container)",
    KIND_ZIP_ODT: "OpenDocument (ODT/ODS, ZIP-Container)",
    KIND_ZIP: "ZIP-Archiv",
    KIND_HTML: "HTML-Text",
    KIND_RTF: "RTF-Text",
    KIND_PNG: "PNG-Bild",
    KIND_JPEG: "JPEG-Bild",
    KIND_TEXT: "Klartext",
    KIND_UNKNOWN: "unbekanntes Binärformat",
    KIND_UNREADABLE: "nicht lesbar",
}

_KIND_EXT = {
    KIND_ZIP_DOCX: ".docx",
    KIND_ZIP_XLSX: ".xlsx",
    KIND_ZIP_PPTX: ".pptx",
    KIND_ZIP_ODT: ".odt",
    KIND_HTML: ".html",
    KIND_RTF: ".rtf",
    KIND_PNG: ".png",
    KIND_JPEG: ".jpg",
    KIND_TEXT: ".txt",
}


@dataclass
class SniffResult:
    path: Path
    size: int = 0
    head: bytes = b""
    kind: str = KIND_UNKNOWN
    pdf_header_offset: int = -1
    pdf_version: str = ""
    has_eof: bool = False
    has_startxref: bool = False
    detail: str = ""
    error: str = ""
    zip_names: list[str] = field(default_factory=list)

    @property
    def is_pdf_like(self) -> bool:
        return self.kind in PDF_LIKE_KINDS

    @property
    def is_clean_pdf(self) -> bool:
        return self.kind == KIND_PDF

    @property
    def head_hex(self) -> str:
        return " ".join(f"{b:02x}" for b in self.head[:16])

    @property
    def head_ascii(self) -> str:
        return "".join(chr(b) if 32 <= b < 127 else "." for b in self.head[:16])

    @property
    def label_de(self) -> str:
        return _KIND_LABEL_DE.get(self.kind, self.kind)

    @property
    def suggested_extension(self) -> str:
        return _KIND_EXT.get(self.kind, "")

    def summary_de(self) -> str:
        """Einzeiler: Typ · Größe · Header."""
        return (
            f"{self.label_de} · {_fmt_size(self.size)} · Header: {self.head_hex or '–'}"
            + (f" ({self.head_ascii})" if self.head else "")
        )


def _fmt_size(n: int) -> str:
    try:
        return f"{int(n):,} Byte".replace(",", ".")
    except Exception:
        return f"{n} Byte"


def _looks_like_text(head: bytes) -> bool:
    if not head:
        return False
    sample = head[:512]
    if sample.startswith((b"\xef\xbb\xbf", b"\xff\xfe", b"\xfe\xff")):
        return True
    bad = sum(1 for b in sample if b < 9 or (13 < b < 32 and b != 27))
    return bad <= max(1, len(sample) // 50)


def _classify_zip(path: Path) -> tuple[str, list[str], str]:
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
    except Exception as e:
        return KIND_ZIP, [], f"ZIP nicht lesbar: {e}"
    nset = set(names)
    if "word/document.xml" in nset:
        detail = "enthält word/document.xml"
        app = _zip_app_name(path)
        if app:
            detail += f"; Anwendung: {app}"
        return KIND_ZIP_DOCX, names, detail
    if "xl/workbook.xml" in nset:
        return KIND_ZIP_XLSX, names, "enthält xl/workbook.xml"
    if "ppt/presentation.xml" in nset:
        return KIND_ZIP_PPTX, names, "enthält ppt/presentation.xml"
    if "mimetype" in nset:
        try:
            with zipfile.ZipFile(path) as z:
                mt = z.read("mimetype")[:80].decode("ascii", "replace")
            if "opendocument" in mt:
                return KIND_ZIP_ODT, names, f"mimetype {mt}"
        except Exception:
            pass
    return KIND_ZIP, names, f"{len(names)} Einträge"


def _zip_app_name(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as z:
            if "docProps/app.xml" not in z.namelist():
                return ""
            xml = z.read("docProps/app.xml").decode("utf-8", "replace")
    except Exception:
        return ""
    start = xml.find("<Application>")
    if start < 0:
        return ""
    end = xml.find("</Application>", start)
    return xml[start + len("<Application>") : end].strip() if end > start else ""


def sniff_bytes(head: bytes, tail: bytes, size: int, path: Path | None = None) -> SniffResult:
    """Klassifikation aus Kopf-/Endbytes (für Tests ohne Datei nutzbar)."""
    res = SniffResult(path=Path(path) if path is not None else Path(""), size=int(size), head=bytes(head[:16]))
    if size <= 0 or not head:
        res.kind = KIND_EMPTY
        res.detail = "0 Byte"
        return res
    off = head.find(PDF_MAGIC)
    if 0 <= off < HEADER_SEARCH_WINDOW:
        res.pdf_header_offset = off
        ver = head[off + len(PDF_MAGIC) : off + len(PDF_MAGIC) + 3]
        res.pdf_version = ver.decode("ascii", "replace").strip()
        res.has_eof = b"%%EOF" in tail
        res.has_startxref = b"startxref" in tail
        if off > 0:
            res.kind = KIND_PDF_JUNK_PREFIX
            res.detail = f"{off} Fremdbyte(s) vor %PDF-"
        elif not res.has_eof:
            res.kind = KIND_PDF_TRUNCATED
            res.detail = "kein %%EOF am Dateiende" + ("" if res.has_startxref else ", kein startxref")
        else:
            res.kind = KIND_PDF
            res.detail = f"PDF-{res.pdf_version}"
        return res
    if head.startswith(b"PK\x03\x04") or head.startswith(b"PK\x05\x06"):
        if path is not None and Path(path).is_file():
            res.kind, res.zip_names, res.detail = _classify_zip(Path(path))
        else:
            res.kind, res.detail = KIND_ZIP, "ZIP-Signatur"
        return res
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        res.kind, res.detail = KIND_PNG, "PNG-Signatur"
        return res
    if head.startswith(b"\xff\xd8\xff"):
        res.kind, res.detail = KIND_JPEG, "JPEG-Signatur"
        return res
    if head.lstrip().startswith(b"{\\rtf"):
        res.kind, res.detail = KIND_RTF, "{\\rtf"
        return res
    low = head[:512].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if low.startswith((b"<!doctype html", b"<html", b"<?xml")) or b"<html" in low or b"<body" in low:
        res.kind, res.detail = KIND_HTML, "HTML/XML-Markup"
        return res
    if _looks_like_text(head):
        res.kind, res.detail = KIND_TEXT, "druckbare Zeichen, kein %PDF-"
        return res
    res.kind, res.detail = KIND_UNKNOWN, "keine bekannte Signatur"
    return res


def sniff_file(path: str | Path) -> SniffResult:
    """Datei-Typ aus den Bytes bestimmen — nie nach Dateiendung."""
    p = Path(path)
    try:
        size = p.stat().st_size
    except OSError as e:
        return SniffResult(path=p, kind=KIND_UNREADABLE, error=str(e), detail=str(e))
    head = b""
    tail = b""
    try:
        with open(p, "rb") as fh:
            head = fh.read(HEADER_SEARCH_WINDOW + len(PDF_MAGIC) + 8)
            if size > len(head):
                fh.seek(max(0, size - EOF_SEARCH_WINDOW))
                tail = fh.read(EOF_SEARCH_WINDOW)
            else:
                tail = head
    except OSError as e:
        return SniffResult(path=p, size=size, kind=KIND_UNREADABLE, error=str(e), detail=str(e))
    return sniff_bytes(head, tail, size, p)


def describe_non_pdf_de(res: SniffResult) -> str:
    """Deutscher Diagnosetext für Nicht-PDF-Dateien (Banner/Dialog)."""
    name = res.path.name if res.path and str(res.path) else "Datei"
    if res.kind == KIND_EMPTY:
        return (
            f"{name} ist leer (0 Byte) — kein PDF. Quelle prüfen: Download/Sync (OneDrive, "
            "Files-On-Demand) unvollständig, Datei noch in Bearbeitung oder vom Virenscanner gesperrt."
        )
    if res.kind == KIND_UNREADABLE:
        return f"{name} ist nicht lesbar: {res.error or res.detail}"
    base = (
        f"{name} ist kein gültiges PDF, sondern: {res.label_de}"
        + (f" ({res.detail})" if res.detail else "")
        + f". Größe {_fmt_size(res.size)}, Header {res.head_hex} ({res.head_ascii})."
    )
    hint = ""
    if res.kind == KIND_ZIP_DOCX:
        hint = (
            " Die Datei ist ein unverändertes Word-Dokument mit .pdf-Endung — vermutlich mit einer "
            "älteren InstantLens-Doc-Version über „Speichern unter … .pdf“ kopiert statt exportiert. "
            "Abhilfe: Datei in .docx umbenennen (Inhalt vollständig erhalten) oder direkt öffnen — "
            "InstantLens Doc erkennt den Inhalt und lädt sie als DOCX; danach Datei → Export → PDF."
        )
    elif res.kind in (KIND_ZIP_XLSX, KIND_ZIP_PPTX, KIND_ZIP_ODT, KIND_ZIP):
        hint = f" Abhilfe: Datei in {res.suggested_extension or '.zip'} umbenennen und mit dem passenden Programm öffnen."
    elif res.kind == KIND_HTML:
        hint = " Abhilfe: Datei in .html umbenennen oder im Editor öffnen; PDF über Datei → Export → PDF erzeugen."
    elif res.kind == KIND_RTF:
        hint = " Abhilfe: Datei in .rtf umbenennen; PDF über Datei → Export → PDF erzeugen."
    elif res.kind == KIND_TEXT:
        hint = " Abhilfe: Datei in .txt umbenennen und im Editor öffnen; PDF über Datei → Export → PDF erzeugen."
    elif res.kind in (KIND_PNG, KIND_JPEG):
        hint = f" Abhilfe: Datei in {res.suggested_extension} umbenennen oder über Scan/Bild → PDF importieren."
    elif res.kind == KIND_PDF_TRUNCATED:
        hint = (
            " Die Datei wurde nicht zu Ende geschrieben (Download/Sync/Export abgebrochen). "
            "pikepdf versucht eine Reparatur; sonst Quelle erneut speichern."
        )
    elif res.kind == KIND_PDF_JUNK_PREFIX:
        hint = " pikepdf überspringt die Fremdbytes normalerweise (Reparatur-Schritt)."
    else:
        hint = " Quelle prüfen (unvollständiger Download, falsche Endung, beschädigte Datei)."
    return base + hint


class InvalidPdfOutput(RuntimeError):
    """Eine PDF-Ausgabe hat die Nachkontrolle nicht bestanden."""


@dataclass
class PdfValidation:
    path: Path
    ok: bool
    sniff: SniffResult
    page_count: int = 0
    pikepdf_error: str = ""
    pdfium_error: str = ""
    producer: str = ""
    problems: list[str] = field(default_factory=list)

    def message_de(self) -> str:
        if self.ok:
            return (
                f"PDF ok: {self.path.name} · {self.page_count} Seite(n) · {_fmt_size(self.sniff.size)}"
                + (f" · Producer {self.producer}" if self.producer else "")
            )
        return f"PDF ungültig: {self.path.name} — " + "; ".join(self.problems or ["unbekannter Fehler"])


def validate_pdf_file(
    path: str | Path,
    *,
    use_pikepdf: bool = True,
    use_pdfium: bool = False,
    min_pages: int = 1,
) -> PdfValidation:
    """Header + %%EOF + pikepdf-Öffnung (+ optional PDFium) einer PDF-Datei prüfen."""
    p = Path(path)
    sn = sniff_file(p)
    problems: list[str] = []
    if sn.kind != KIND_PDF:
        problems.append(describe_non_pdf_de(sn) if not sn.is_pdf_like else f"{sn.label_de}: {sn.detail}")
    val = PdfValidation(path=p, ok=False, sniff=sn)
    if use_pikepdf and sn.is_pdf_like:
        try:
            import pikepdf

            with pikepdf.open(str(p)) as pdf:
                val.page_count = len(pdf.pages)
                try:
                    info = pdf.docinfo
                    prod = info.get("/Producer") if info is not None else None
                    if prod is not None:
                        val.producer = str(prod)
                except Exception:
                    pass
            if val.page_count < int(min_pages):
                problems.append(f"nur {val.page_count} Seite(n) (< {min_pages})")
        except Exception as e:
            val.pikepdf_error = f"{type(e).__name__}: {e}"
            problems.append(f"pikepdf: {val.pikepdf_error}")
    if use_pdfium and sn.is_pdf_like:
        try:
            from .pdfium_open import PDFIUM_LOCK

            import pypdfium2 as pdfium

            with PDFIUM_LOCK:
                doc = pdfium.PdfDocument(p.read_bytes())
                try:
                    n = len(doc)
                finally:
                    doc.close()
            if n < int(min_pages):
                problems.append(f"PDFium: nur {n} Seite(n)")
            elif val.page_count == 0:
                val.page_count = n
        except Exception as e:
            val.pdfium_error = f"{type(e).__name__}: {e}"
            problems.append(f"PDFium: {val.pdfium_error}")
    val.problems = problems
    val.ok = not problems
    return val


def assert_valid_pdf(path: str | Path, *, use_pdfium: bool = False, remove_invalid: bool = False) -> PdfValidation:
    """Nach jedem PDF-Schreiben aufrufen: wirft :class:`InvalidPdfOutput` statt still eine
    unlesbare Datei zu hinterlassen. ``remove_invalid`` löscht die defekte Ausgabe."""
    val = validate_pdf_file(path, use_pdfium=use_pdfium)
    if not val.ok:
        _log.error("PDF-Ausgabe ungültig: %s", val.message_de())
        if remove_invalid:
            try:
                os.remove(str(path))
            except OSError:
                pass
        raise InvalidPdfOutput(val.message_de())
    return val


def recover_misnamed_file(path: str | Path, dest: str | Path | None = None) -> Optional[Path]:
    """Nicht-PDF mit .pdf-Endung unter der richtigen Endung **kopieren** (Original bleibt).

    Rückgabe: Zielpfad oder ``None`` wenn der Typ keine sichere Endung hat
    (echtes PDF, unbekanntes Binärformat).
    """
    import shutil

    p = Path(path)
    sn = sniff_file(p)
    ext = sn.suggested_extension
    if not ext:
        return None
    target = Path(dest) if dest is not None else p.with_suffix(ext)
    if target.exists() and target.resolve() == p.resolve():
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, target)
    return target
