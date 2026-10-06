"""Textersteller / Autor wie Word Datei ▸ Informationen (core.xml dc:creator, PDF /Author)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

META_SIDECAR_SUFFIX = ".ildmeta.json"


def os_user_name() -> str:
    try:
        import getpass

        name = str(getpass.getuser() or "").strip()
        if name:
            return name
    except Exception:
        pass
    try:
        import os

        for key in ("USER", "USERNAME", "LOGNAME"):
            name = str(os.environ.get(key) or "").strip()
            if name:
                return name
    except Exception:
        pass
    return ""


def default_author() -> str:
    return os_user_name() or "local"


def normalize_author(value: Any) -> str:
    return str(value or "").strip()


def ensure_author(meta: dict | None, fallback: str | None = None) -> str:
    data = meta if isinstance(meta, dict) else {}
    author = normalize_author(data.get("author") or data.get("creator"))
    if author:
        return author
    return normalize_author(fallback) or default_author()


def meta_sidecar_path(path: str | Path | None) -> Path | None:
    if not path:
        return None
    return Path(str(Path(path)) + META_SIDECAR_SUFFIX)


def load_author_sidecar(path: str | Path | None) -> str:
    src = meta_sidecar_path(path)
    if src is None or not src.is_file():
        return ""
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return ""
    if not isinstance(data, dict):
        return ""
    return normalize_author(data.get("author") or data.get("creator"))


def save_author_sidecar(path: str | Path | None, author: str) -> Path | None:
    src = meta_sidecar_path(path)
    if src is None:
        return None
    payload = {"schema": "ild-doc-meta", "version": 1, "author": normalize_author(author)}
    src.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return src


def load_docx_author(path: str | Path) -> str:
    try:
        from instantlensdoc.core.richtext_docx import docx_header_footer_author

        _h, _f, author = docx_header_footer_author(path)
        return normalize_author(author)
    except Exception:
        return ""


def save_docx_author(path: str | Path, author: str) -> None:
    name = normalize_author(author)
    if not name:
        return
    try:
        from docx import Document as DocxDocument
    except ImportError:
        return
    try:
        d = DocxDocument(str(path))
        d.core_properties.author = name
        d.save(str(path))
    except Exception:
        pass


def load_pdf_author(path: str | Path) -> str:
    try:
        from ild_pdf.metadata import get_metadata

        meta = get_metadata(path)
        return normalize_author(meta.author or meta.creator)
    except Exception:
        return ""


def save_pdf_author(path: str | Path, author: str) -> None:
    name = normalize_author(author)
    try:
        from ild_pdf.metadata import get_metadata, set_metadata

        current = get_metadata(path)
        current.author = name
        if not current.creator:
            current.creator = name
        set_metadata(path, current)
    except Exception:
        pass


def load_author(path: str | Path | None, *, kind: str = "", meta: dict | None = None) -> str:
    data = meta if isinstance(meta, dict) else {}
    author = normalize_author(data.get("author") or data.get("creator"))
    if author:
        return author
    if path:
        suffix = Path(path).suffix.lower()
        kind_u = str(kind or "").upper()
        if suffix == ".docx" or kind_u == "DOCX":
            author = load_docx_author(path)
        elif suffix == ".pdf" or kind_u == "PDF":
            author = load_pdf_author(path)
        if not author:
            author = load_author_sidecar(path)
    return author


def persist_author(path: str | Path | None, author: str, *, kind: str = "") -> None:
    if not path:
        return
    p = Path(path)
    name = normalize_author(author) or default_author()
    suffix = p.suffix.lower()
    kind_u = str(kind or "").upper()
    if suffix == ".docx" or kind_u == "DOCX":
        save_docx_author(p, name)
        return
    if suffix == ".pdf" or kind_u == "PDF":
        save_pdf_author(p, name)
        return
    save_author_sidecar(p, name)
