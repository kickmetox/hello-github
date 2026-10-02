"""Dokument-I/O: TXT, MD, HTML, DOCX, PDF, Bilder."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

# Editor-Textcodierungen (Öffnen/Speichern)
TEXT_ENCODINGS = ("utf-8", "latin-1")
ENCODING_LABELS = {
    "utf-8": "UTF-8",
    "latin-1": "Latin-1 (ISO-8859-1)",
}


def normalize_text_encoding(encoding: str | None) -> str:
    """Nur utf-8 / latin-1; Default utf-8."""
    enc = (encoding or "utf-8").strip().lower().replace("_", "-")
    if enc in ("utf8", "utf-8", "utf"):
        return "utf-8"
    if enc in ("latin-1", "latin1", "iso-8859-1", "iso8859-1", "cp1252"):
        # cp1252-ähnlich bewusst auf latin-1 mappen (Aufgabenumfang)
        return "latin-1"
    return "utf-8"


class DocKind(str, Enum):
    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"
    DOCX = "docx"
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
        return normalize_text_encoding(self.meta.get("encoding"))


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
    enc = normalize_text_encoding(encoding)

    if kind in (DocKind.TEXT, DocKind.MARKDOWN, DocKind.HTML):
        doc.text = path.read_text(encoding=enc, errors="replace")
        doc.meta["encoding"] = enc
    elif kind == DocKind.DOCX:
        try:
            from docx import Document as DocxDocument

            d = DocxDocument(str(path))
            doc.text = "\n".join(p.text for p in d.paragraphs)
        except ImportError:
            doc.text = "[python-docx nicht installiert]"
            doc.meta["error"] = "python-docx fehlt"
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
    enc = normalize_text_encoding(encoding)

    if kind == DocKind.DOCX:
        from instantlensdoc.core.export import export_docx

        export_docx(doc.text, target, title=doc.title)
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
