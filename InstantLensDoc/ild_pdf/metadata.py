"""PDF-Dokumentmetadaten lesen/schreiben (pikepdf) — UTF-8 sicher 1.5.1."""

from __future__ import annotations

import unicodedata
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Optional


def utf8_safe(value: object) -> str:
    """
    String UTF-8-sicher normalisieren (NFC, ungültige Surrogates entfernen) — 1.5.1.
    """
    if value is None:
        return ""
    if isinstance(value, bytes):
        try:
            s = value.decode("utf-8")
        except UnicodeDecodeError:
            s = value.decode("utf-8", errors="replace")
    else:
        s = str(value)
    # Surrogate/ungültige Codepoints bereinigen
    s = s.encode("utf-8", errors="surrogatepass").decode("utf-8", errors="replace")
    return unicodedata.normalize("NFC", s)


@dataclass
class PdfMetadata:
    title: str = ""
    author: str = ""
    subject: str = ""
    keywords: str = ""
    creator: str = ""
    producer: str = ""

    def to_dict(self) -> dict[str, str]:
        return {k: utf8_safe(v or "") for k, v in asdict(self).items()}

    @classmethod
    def from_dict(cls, data: dict | None) -> "PdfMetadata":
        if not data:
            return cls()
        known = {f.name for f in fields(cls)}
        return cls(**{k: utf8_safe(data.get(k) or "") for k in known})


def _docinfo_str(docinfo, key: str) -> str:
    try:
        val = docinfo.get(key)
        if val is None:
            return ""
        return utf8_safe(val)
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
                        meta.title = utf8_safe(t)
            except Exception:
                pass
        return meta


def set_metadata(
    path: str | Path,
    meta: PdfMetadata | dict,
    *,
    out_path: str | Path | None = None,
    delete_empty: bool = True,
) -> Path:
    """
    Schreibt Metadaten in DocInfo und XMP-Title/Creator.
    delete_empty=True (Default): leere Felder aus DocInfo/XMP entfernen — 1.5.1.
    delete_empty=False: leere Felder als leere Strings belassen (nicht löschen).
    Werte werden UTF-8-sicher (NFC) geschrieben.
    """
    import pikepdf

    path = Path(path)
    out_path = Path(out_path) if out_path else path
    if isinstance(meta, dict):
        meta = PdfMetadata.from_dict(meta)
    else:
        meta = PdfMetadata(
            title=utf8_safe(meta.title),
            author=utf8_safe(meta.author),
            subject=utf8_safe(meta.subject),
            keywords=utf8_safe(meta.keywords),
            creator=utf8_safe(meta.creator),
            producer=utf8_safe(meta.producer),
        )

    overwrite = out_path.resolve() == path.resolve()
    with pikepdf.open(path, allow_overwriting_input=overwrite) as pdf:
        with pdf.open_metadata(set_pikepdf_as_editor=False) as xmp:
            if meta.title or not delete_empty:
                if meta.title:
                    xmp["dc:title"] = meta.title
                elif not delete_empty:
                    xmp["dc:title"] = ""
            elif "dc:title" in xmp:
                try:
                    del xmp["dc:title"]
                except Exception:
                    pass
            if meta.author:
                xmp["dc:creator"] = [meta.author]
            elif delete_empty and "dc:creator" in xmp:
                try:
                    del xmp["dc:creator"]
                except Exception:
                    pass
            for xkey, val in (
                ("dc:description", meta.subject),
                ("pdf:Keywords", meta.keywords),
                ("xmp:CreatorTool", meta.creator),
            ):
                if val:
                    xmp[xkey] = val
                elif delete_empty and xkey in xmp:
                    try:
                        del xmp[xkey]
                    except Exception:
                        pass
                elif not delete_empty:
                    xmp[xkey] = ""
        # DocInfo parallel (ältere Reader)
        info = pdf.docinfo
        mapping = {
            "/Title": meta.title,
            "/Author": meta.author,
            "/Subject": meta.subject,
            "/Keywords": meta.keywords,
            "/Creator": meta.creator,
            "/Producer": meta.producer or ("InstantLens Doc" if delete_empty else meta.producer),
        }
        for key, val in mapping.items():
            if val:
                info[key] = val
            elif delete_empty:
                if key in info:
                    del info[key]
            else:
                # leere Felder behalten (leerer String) — 1.5.1
                info[key] = ""
        out_path.parent.mkdir(parents=True, exist_ok=True)
        pdf.save(out_path)
    return out_path


def strip_metadata(
    path: str | Path,
    *,
    out_path: str | Path | None = None,
) -> Path:
    """
    Entfernt DocInfo- und XMP-Metadaten (Titel/Autor/Thema/Keywords/…).
    Speichert unter out_path oder überschreibt die Quelldatei.
    """
    import pikepdf

    path = Path(path)
    out_path = Path(out_path) if out_path else path
    overwrite = out_path.resolve() == path.resolve()
    with pikepdf.open(path, allow_overwriting_input=overwrite) as pdf:
        try:
            with pdf.open_metadata(set_pikepdf_as_editor=False) as xmp:
                keys = list(xmp.keys())
                for key in keys:
                    try:
                        del xmp[key]
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            # DocInfo leeren
            info = pdf.docinfo
            for key in list(info.keys()):
                try:
                    del info[key]
                except Exception:
                    pass
        except Exception:
            pass
        # Optional: /Info-Eintrag im Trailer entfernen falls möglich
        try:
            if "/Info" in pdf.trailer:
                del pdf.trailer["/Info"]
        except Exception:
            pass
        out_path.parent.mkdir(parents=True, exist_ok=True)
        pdf.save(out_path)
    return out_path


def sanitize_pdf(
    path: str | Path,
    *,
    strip_meta: bool = True,
    out_path: str | Path | None = None,
) -> Path:
    """
    PDF bereinigen: optional Metadaten strippen, Datei neu speichern
    (pikepdf rewrite — entfernt typischerweise ungültige/verwaiste Objekte).
    """
    import pikepdf

    path = Path(path)
    out_path = Path(out_path) if out_path else path
    if strip_meta:
        return strip_metadata(path, out_path=out_path)
    overwrite = out_path.resolve() == path.resolve()
    with pikepdf.open(path, allow_overwriting_input=overwrite) as pdf:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        pdf.save(out_path)
    return out_path
