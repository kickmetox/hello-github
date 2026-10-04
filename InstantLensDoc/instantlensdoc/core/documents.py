"""Dokument-I/O: TXT, MD, HTML, DOCX, PDF, Bilder."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

# Editor-Textcodierungen (Öffnen/Speichern); "auto" = BOM/chardet-Erkennung
TEXT_ENCODINGS = ("auto", "utf-8", "latin-1")
ENCODING_LABELS = {
    "auto": "Automatisch (BOM / chardet)",
    "utf-8": "UTF-8",
    "latin-1": "Latin-1 (ISO-8859-1)",
}


def normalize_text_encoding(encoding: str | None) -> str:
    """utf-8 / latin-1 / auto; Default utf-8."""
    enc = (encoding or "utf-8").strip().lower().replace("_", "-")
    if enc in ("auto", "detect", "automatic"):
        return "auto"
    if enc in ("utf8", "utf-8", "utf"):
        return "utf-8"
    if enc in ("latin-1", "latin1", "iso-8859-1", "iso8859-1", "cp1252", "windows-1252"):
        # cp1252-ähnlich bewusst auf latin-1 mappen (Aufgabenumfang)
        return "latin-1"
    return "utf-8"


def detect_file_encoding(path: str | Path, sample_size: int = 65536) -> str:
    """
    Datei-Encoding erkennen: BOM → UTF-8-Probe → optional chardet → latin-1.
    Rückgabe immer normalisiert (utf-8 oder latin-1), nie auto.
    """
    path = Path(path)
    try:
        raw = path.read_bytes()[: max(1024, int(sample_size))]
    except Exception:
        return "utf-8"
    if not raw:
        return "utf-8"
    # BOM
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8"
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        # UTF-16 nicht nativ unterstützt → als latin-1-Fallback vermeiden; utf-8 lesen mit replace
        return "utf-8"
    # Strikte UTF-8-Probe
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass
    # Optional chardet
    try:
        import chardet  # type: ignore

        guess = chardet.detect(raw) or {}
        enc = normalize_text_encoding(guess.get("encoding"))
        if enc == "auto":
            enc = "utf-8"
        # chardet liefert oft windows-1252 → latin-1
        if enc in ("utf-8", "latin-1"):
            return enc
    except Exception:
        pass
    return "latin-1"


def resolve_text_encoding(path: str | Path | None, encoding: str | None) -> str:
    """Encoding auflösen: auto → detect_file_encoding, sonst normalize."""
    enc = normalize_text_encoding(encoding)
    if enc == "auto":
        if path is None:
            return "utf-8"
        return detect_file_encoding(path)
    return enc


# Vorlagen für „Neues leeres Dokument“ (id → Titel, Text)
DOC_TEMPLATES: dict[str, tuple[str, str]] = {
    "empty": ("Unbenannt", ""),
    "brief": (
        "Brief",
        "{name}\n{street}\n{city}\n\n"
        "{date}\n\n"
        "Sehr geehrte Damen und Herren,\n\n"
        "[Text]\n\n"
        "Mit freundlichen Grüßen\n\n"
        "[Unterschrift]\n"
    ),
    "notiz": (
        "Notiz",
        "# Notiz\n\n"
        "Datum: {date}\n"
        "Thema: \n\n"
        "- \n"
        "- \n\n"
        "———\n",
    ),
}


def render_doc_template(template_id: str = "empty") -> tuple[str, str]:
    """
    Dokument-Vorlage rendern.
    Rückgabe: (Titel, Text). Unbekannte ID → leeres Dokument.
    Unterstützt eingebaute IDs und Nutzer-Vorlagen (user:… / UUID).
    """
    from datetime import date

    key = (template_id or "empty").strip()
    key_l = key.lower()
    title: str
    body: str
    if key_l in DOC_TEMPLATES:
        title, body = DOC_TEMPLATES[key_l]
    else:
        # Nutzer-Vorlage aus Einstellungen
        try:
            from instantlensdoc.core.app_settings import get_user_doc_template

            ut = get_user_doc_template(key)
        except Exception:
            ut = None
        if ut:
            title = str(ut.get("title") or "Vorlage")
            body = str(ut.get("body") or "")
        else:
            title, body = DOC_TEMPLATES["empty"]
    today = date.today().strftime("%d.%m.%Y")
    try:
        text = body.format(
            name="[Name]",
            street="[Straße Nr.]",
            city="[PLZ Ort]",
            date=today,
        )
    except (KeyError, ValueError, IndexError):
        # Nutzer-Vorlagen dürfen geschweifte Klammern enthalten
        text = body.replace("{date}", today)
    return title, text


def save_current_as_template(title: str, body: str) -> dict:
    """Aktuellen Editor-Text als Nutzer-Vorlage speichern."""
    from instantlensdoc.core.app_settings import save_user_doc_template

    return save_user_doc_template(title=title, body=body)


class DocKind(str, Enum):
    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"
    DOCX = "docx"
    RTF = "rtf"
    XLSX = "xlsx"
    PDF = "pdf"
    IMAGE = "image"
    UNKNOWN = "unknown"


@dataclass
class Document:
    path: Optional[Path] = None
    kind: DocKind = DocKind.TEXT
    text: str = ""
    dirty: bool = False
    title: str = "Unbenannt"
    meta: dict = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        if self.path:
            return self.path.name
        return self.title

    @property
    def encoding(self) -> str:
        enc = normalize_text_encoding(self.meta.get("encoding"))
        return "utf-8" if enc == "auto" else enc


def detect_kind(path: Path) -> DocKind:
    ext = path.suffix.lower()
    if ext in {".txt", ".log", ".csv"}:
        return DocKind.TEXT
    if ext in {".md", ".markdown"}:
        return DocKind.MARKDOWN
    if ext in {".html", ".htm"}:
        return DocKind.HTML
    if ext == ".docx":
        return DocKind.DOCX
    if ext == ".rtf":
        return DocKind.RTF
    if ext == ".xlsx":
        return DocKind.XLSX
    if ext == ".pdf":
        return DocKind.PDF
    if ext in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}:
        return DocKind.IMAGE
    return DocKind.UNKNOWN


def open_document(path: str | Path, *, encoding: str | None = None) -> Document:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {path}")
    if not path.is_file():
        raise IsADirectoryError(f"Kein Dateipfad: {path}")
    kind = detect_kind(path)
    doc = Document(path=path, kind=kind, title=path.name)

    if encoding is None:
        try:
            from instantlensdoc.core.app_settings import get_editor_text_encoding

            encoding = get_editor_text_encoding()
        except Exception:
            encoding = "utf-8"
    enc = resolve_text_encoding(path, encoding)
    requested = normalize_text_encoding(encoding)
    if requested == "auto":
        doc.meta["encoding_detected"] = True

    if kind in (DocKind.TEXT, DocKind.MARKDOWN, DocKind.HTML):
        doc.text = path.read_text(encoding=enc, errors="replace")
        doc.meta["encoding"] = enc
    elif kind == DocKind.DOCX:
        try:
            from instantlensdoc.core.export import import_document_text

            loaded = import_document_text(path)
            doc.text = loaded.get("text") or ""
            doc.meta.update(loaded.get("meta") or {})
        except Exception:
            try:
                from docx import Document as DocxDocument

                d = DocxDocument(str(path))
                doc.text = "\n".join(p.text for p in d.paragraphs)
            except ImportError:
                doc.text = "[python-docx nicht installiert]"
                doc.meta["error"] = "python-docx fehlt"
    elif kind == DocKind.RTF:
        from instantlensdoc.core.export import import_rtf

        doc.text = import_rtf(path)
        doc.meta["encoding"] = "utf-8"
    elif kind == DocKind.XLSX:
        from ild_pdf.tables import import_xlsx, table_to_markdown

        table = import_xlsx(path)
        doc.text = table_to_markdown(table)
        doc.meta["table"] = table.to_dict()
    elif kind == DocKind.PDF:
        doc.text = ""  # PDF wird über Viewer gerendert
        doc.meta["pdf"] = str(path)
    elif kind == DocKind.IMAGE:
        doc.text = ""
        doc.meta["image"] = str(path)
    else:
        doc.text = path.read_text(encoding=enc, errors="replace")
        doc.kind = DocKind.TEXT
        doc.meta["encoding"] = enc
    return doc


def backup_existing(path: Path) -> Path | None:
    """Kopiert vorhandene Datei nach path.bak (überschreibt älteres .bak)."""
    path = Path(path)
    if not path.is_file():
        return None
    bak = Path(str(path) + ".bak")
    shutil.copy2(path, bak)
    return bak


def backup_ildbak(path: Path, max_backups: int = 3) -> Path | None:
    """
    Autosave-Backup als path.ext.ildbak mit Rotation (max. 1–10) — 0.9.9.

    Neueste Kopie: ``dateiname.ext.ildbak``;
    ältere: ``dateiname.ext.1.ildbak`` … ``dateiname.ext.(n-1).ildbak``.
    """
    path = Path(path)
    if not path.is_file():
        return None
    try:
        n = int(max_backups)
    except (TypeError, ValueError):
        n = 3
    n = max(1, min(10, n))
    base = str(path)
    newest = Path(base + ".ildbak")
    if n == 1:
        shutil.copy2(path, newest)
        return newest
    oldest = Path(f"{base}.{n - 1}.ildbak")
    if oldest.is_file():
        try:
            oldest.unlink()
        except OSError:
            pass
    for i in range(n - 2, 0, -1):
        src = Path(f"{base}.{i}.ildbak")
        dst = Path(f"{base}.{i + 1}.ildbak")
        if src.is_file():
            try:
                src.replace(dst)
            except OSError:
                try:
                    shutil.copy2(src, dst)
                    src.unlink()
                except OSError:
                    pass
    if newest.is_file():
        slot1 = Path(f"{base}.1.ildbak")
        try:
            newest.replace(slot1)
        except OSError:
            try:
                shutil.copy2(newest, slot1)
                newest.unlink()
            except OSError:
                pass
    shutil.copy2(path, newest)
    return newest


def save_document(
    doc: Document,
    path: Optional[Path] = None,
    *,
    encoding: str | None = None,
) -> Path:
    target = Path(path or doc.path or "unbenannt.txt")
    kind = detect_kind(target) if path else doc.kind

    # Optionale Backup-Kopie vor Überschreiben (Einstellungen → Backup .bak)
    try:
        from instantlensdoc.core.app_settings import get_backup_on_save

        if get_backup_on_save() and target.is_file():
            backup_existing(target)
    except Exception:
        pass

    if encoding is None:
        encoding = doc.meta.get("encoding")
    if encoding is None:
        try:
            from instantlensdoc.core.app_settings import get_editor_text_encoding

            encoding = get_editor_text_encoding()
        except Exception:
            encoding = "utf-8"
    # Beim Speichern nie "auto" schreiben — erkanntes/gewähltes Encoding nutzen
    enc = resolve_text_encoding(target if normalize_text_encoding(encoding) == "auto" else None, encoding)
    if normalize_text_encoding(encoding) == "auto" and doc.meta.get("encoding") in ("utf-8", "latin-1"):
        enc = normalize_text_encoding(doc.meta.get("encoding"))

    if kind == DocKind.DOCX:
        from instantlensdoc.core.export import export_docx

        export_docx(doc.text, target, title=doc.title)
    elif kind == DocKind.RTF:
        from instantlensdoc.core.export import export_rtf

        export_rtf(doc.text, target, title=doc.title)
    elif kind == DocKind.XLSX:
        from instantlensdoc.core.export import export_xlsx_from_text

        export_xlsx_from_text(doc.text, target)
    elif kind == DocKind.HTML:
        stripped = (doc.text or "").lstrip().lower()
        if stripped.startswith("<!doctype") or stripped.startswith("<html"):
            target.write_text(doc.text, encoding=enc, errors="replace")
            doc.meta["encoding"] = enc
        else:
            from instantlensdoc.core.export import export_html

            export_html(doc.text, target, title=doc.title or target.stem)
    elif kind == DocKind.PDF:
        # PDF-Inhalt wird über Annotation-Sidecar / pikepdf verwaltet
        if doc.path and doc.path.resolve() != target.resolve():
            shutil.copy2(doc.path, target)
    elif kind == DocKind.IMAGE:
        if doc.path and doc.path.resolve() != target.resolve():
            shutil.copy2(doc.path, target)
    else:
        target.write_text(doc.text, encoding=enc, errors="replace")
        doc.meta["encoding"] = enc
    doc.path = target
    doc.kind = kind
    doc.dirty = False
    doc.title = target.name
    return target
