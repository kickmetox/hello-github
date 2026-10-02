"""PDF-Dokumentmetadaten lesen/schreiben (pikepdf)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Optional


@dataclass
class PdfMetadata:
    title: str = ""
    author: str = ""
    subject: str = ""
    keywords: str = ""
    creator: str = ""
    producer: str = ""

    def to_dict(self) -> dict[str, str]:
        return {k: (v or "") for k, v in asdict(self).items()}

    @classmethod
    def from_dict(cls, data: dict | None) -> "PdfMetadata":
        if not data:
            return cls()
        known = {f.name for f in fields(cls)}
        return cls(**{k: str(data.get(k) or "") for k in known})


def _docinfo_str(docinfo, key: str) -> str:
    try:
        val = docinfo.get(key)
        if val is None:
            return ""
        return str(val)
    except Exception:
        return ""


def get_metadata(path: str | Path) -> PdfMetadata:
    """Liest Info-Dictionary (+ ggf. XMP-Titel) aus dem PDF."""
    import pikepdf

    path = Path(path)
    with pikepdf.open(path) as pdf:
        info = pdf.docinfo
        meta = PdfMetadata(
            title=_docinfo_str(info, "/Title"),
            author=_docinfo_str(info, "/Author"),
            subject=_docinfo_str(info, "/Subject"),
            keywords=_docinfo_str(info, "/Keywords"),
            creator=_docinfo_str(info, "/Creator"),
            producer=_docinfo_str(info, "/Producer"),
        )
        if not meta.title:
            try:
                with pdf.open_metadata() as xmp:
                    t = xmp.get("dc:title")
                    if t:
                        meta.title = str(t)
            except Exception:
                pass
        return meta


def set_metadata(
    path: str | Path,
    meta: PdfMetadata | dict,
    *,
    out_path: str | Path | None = None,
) -> Path:
    """Schreibt Metadaten in DocInfo und XMP-Title/Creator."""
    import pikepdf

    path = Path(path)
    out_path = Path(out_path) if out_path else path
    if isinstance(meta, dict):
        meta = PdfMetadata.from_dict(meta)

    overwrite = out_path.resolve() == path.resolve()
    with pikepdf.open(path, allow_overwriting_input=overwrite) as pdf:
        with pdf.open_metadata(set_pikepdf_as_editor=False) as xmp:
            if meta.title:
                xmp["dc:title"] = meta.title
            if meta.author:
                xmp["dc:creator"] = [meta.author]
            if meta.subject:
                xmp["dc:description"] = meta.subject
            if meta.keywords:
                xmp["pdf:Keywords"] = meta.keywords
            if meta.creator:
                xmp["xmp:CreatorTool"] = meta.creator
        # DocInfo parallel (ältere Reader)
        info = pdf.docinfo
        mapping = {
            "/Title": meta.title,
            "/Author": meta.author,
            "/Subject": meta.subject,
            "/Keywords": meta.keywords,
            "/Creator": meta.creator,
            "/Producer": meta.producer or "InstantLens Doc",
        }
        for key, val in mapping.items():
            if val:
                info[key] = val
            elif key in info:
                del info[key]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        pdf.save(out_path)
    return out_path
