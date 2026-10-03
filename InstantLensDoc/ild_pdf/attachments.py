"""PDF-Anhänge (Embedded Files / NameTree) listen, extrahieren und hinzufügen — 1.9.2."""

from __future__ import annotations

import mimetypes
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class AttachmentInfo:
    """Metadaten eines eingebetteten PDF-Anhangs."""

    name: str
    filename: str = ""
    description: str = ""
    mime_type: str = ""
    size: int = 0
    relationship: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_name(name: str) -> str:
    base = "".join(c if c.isalnum() or c in ".-_" else "_" for c in (name or "anhang"))
    return (base or "anhang")[:80]


def _unique_attachment_key(pdf, preferred: str) -> str:
    """Eindeutigen Attachments-Key erzeugen (Kollision → _2, _3, …)."""
    base = _safe_name(preferred) or "anhang"
    if base not in pdf.attachments:
        return base
    stem = Path(base).stem
    suf = Path(base).suffix
    n = 2
    while True:
        cand = f"{stem}_{n}{suf}"
        if cand not in pdf.attachments:
            return cand
        n += 1


def attachment_name_taken(path: str | Path, name: str) -> bool:
    """True, wenn Attachments-Key oder Dateiname bereits existiert — 1.9.2."""
    want = (name or "").strip()
    if not want:
        return False
    safe = _safe_name(want)
    try:
        for info in list_attachments(path):
            if info.name == want or info.name == safe:
                return True
            fn = (info.filename or "").strip()
            if fn and (fn == want or fn == Path(want).name):
                return True
    except Exception:
        return False
    return False


def suggest_attachment_name(path: str | Path, preferred: str) -> str:
    """Vorschlag für freien Anhangsnamen bei Kollision — 1.9.2."""
    import pikepdf

    path = Path(path)
    base = _safe_name(preferred) or "anhang"
    try:
        with pikepdf.open(path) as pdf:
            return _unique_attachment_key(pdf, base)
    except Exception:
        if not attachment_name_taken(path, base):
            return base
        stem, suf = Path(base).stem, Path(base).suffix
        n = 2
        while attachment_name_taken(path, f"{stem}_{n}{suf}"):
            n += 1
        return f"{stem}_{n}{suf}"


def has_attachments(path: str | Path) -> bool:
    """True, wenn das PDF mindestens einen Anhang hat."""
    try:
        return len(list_attachments(path)) > 0
    except Exception:
        return False


def list_attachments(path: str | Path) -> list[AttachmentInfo]:
    """Listet eingebettete Dateianhänge (pikepdf Attachments)."""
    import pikepdf

    path = Path(path)
    out: list[AttachmentInfo] = []
    with pikepdf.open(path) as pdf:
        try:
            items = list(pdf.attachments.items())
        except Exception:
            return []
        for key, spec in items:
            name = str(key)
            filename = str(getattr(spec, "filename", None) or name)
            description = str(getattr(spec, "description", None) or "")
            relationship = str(getattr(spec, "relationship", None) or "")
            mime = ""
            size = 0
            try:
                af = spec.get_file()
                mime = str(getattr(af, "mime_type", None) or "") or ""
                try:
                    size = int(getattr(af, "size", 0) or 0)
                except (TypeError, ValueError):
                    size = 0
                if size <= 0:
                    try:
                        size = len(af.read_bytes())
                    except Exception:
                        size = 0
            except Exception:
                pass
            out.append(
                AttachmentInfo(
                    name=name,
                    filename=filename,
                    description=description,
                    mime_type=mime,
                    size=size,
                    relationship=relationship,
                )
            )
    return out


def extract_attachment(
    path: str | Path,
    name: str,
    out_path: str | Path | None = None,
    *,
    out_dir: str | Path | None = None,
) -> Path:
    """
    Extrahiert einen Anhang nach Name (Attachments-Key).
    out_path hat Vorrang; sonst out_dir / filename.
    """
    import pikepdf

    path = Path(path)
    with pikepdf.open(path) as pdf:
        if name not in pdf.attachments:
            # Fallback: Dateiname matchen
            match = None
            for k, spec in pdf.attachments.items():
                fn = str(getattr(spec, "filename", None) or k)
                if str(k) == name or fn == name:
                    match = (str(k), spec)
                    break
            if match is None:
                raise KeyError(f"Anhang nicht gefunden: {name}")
            key, spec = match
        else:
            key, spec = name, pdf.attachments[name]
        filename = str(getattr(spec, "filename", None) or key)
        af = spec.get_file()
        data = af.read_bytes()

    if out_path is not None:
        dest = Path(out_path)
    else:
        base = Path(out_dir) if out_dir else path.parent / f"{path.stem}_attachments"
        base.mkdir(parents=True, exist_ok=True)
        dest = base / _safe_name(filename)
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Kollision vermeiden
    if dest.exists() and out_path is None:
        stem, suf = dest.stem, dest.suffix
        n = 2
        while dest.exists():
            dest = dest.with_name(f"{stem}_{n}{suf}")
            n += 1
    dest.write_bytes(bytes(data))
    return dest


def extract_all_attachments(
    path: str | Path,
    out_dir: str | Path | None = None,
) -> list[Path]:
    """Extrahiert alle Anhänge in out_dir. Rückgabe: geschriebene Pfade."""
    path = Path(path)
    out_dir = Path(out_dir) if out_dir else path.parent / f"{path.stem}_attachments"
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for info in list_attachments(path):
        written.append(extract_attachment(path, info.name, out_dir=out_dir))
    return written


def add_attachment(
    path: str | Path,
    file_path: str | Path,
    *,
    name: str | None = None,
    description: str = "",
    mime_type: str | None = None,
    in_place: bool = True,
    out_path: str | Path | None = None,
) -> AttachmentInfo:
    """
    Fügt eine Datei als eingebetteten PDF-Anhang hinzu (pikepdf Attachments).

    Standard: in_place=True schreibt das Quell-PDF. Sonst out_path (oder
    ``{stem}_with_att.pdf`` neben der Quelle).
    """
    import pikepdf

    path = Path(path)
    file_path = Path(file_path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Datei nicht gefunden: {file_path}")
    data = file_path.read_bytes()
    key_pref = name or file_path.name
    mime = mime_type
    if not mime:
        guess, _ = mimetypes.guess_type(str(file_path))
        mime = guess or "application/octet-stream"

    dest = Path(out_path) if out_path else (path if in_place else path.with_name(f"{path.stem}_with_att.pdf"))
    with pikepdf.open(path, allow_overwriting_input=True) as pdf:
        key = _unique_attachment_key(pdf, key_pref)
        # pikepdf: Zuweisung von bytes oder Pfad erzeugt EmbeddedFile
        pdf.attachments[key] = data
        try:
            spec = pdf.attachments[key]
            if description:
                try:
                    spec.description = description
                except Exception:
                    pass
            try:
                af = spec.get_file()
                if mime and hasattr(af, "mime_type"):
                    af.mime_type = mime
            except Exception:
                pass
        except Exception:
            pass
        pdf.save(dest)

    infos = {i.name: i for i in list_attachments(dest)}
    if key in infos:
        return infos[key]
    return AttachmentInfo(
        name=key,
        filename=file_path.name,
        description=description or "",
        mime_type=mime or "",
        size=len(data),
    )


def remove_attachment(
    path: str | Path,
    name: str,
    *,
    in_place: bool = True,
    out_path: str | Path | None = None,
) -> bool:
    """Entfernt einen Anhang nach Key/Dateiname. True wenn entfernt."""
    import pikepdf

    path = Path(path)
    dest = Path(out_path) if out_path else (path if in_place else path.with_name(f"{path.stem}_no_att.pdf"))
    removed = False
    with pikepdf.open(path, allow_overwriting_input=True) as pdf:
        key = None
        if name in pdf.attachments:
            key = name
        else:
            for k, spec in pdf.attachments.items():
                fn = str(getattr(spec, "filename", None) or k)
                if str(k) == name or fn == name:
                    key = str(k)
                    break
        if key is not None:
            try:
                del pdf.attachments[key]
                removed = True
            except Exception:
                removed = False
        if removed:
            pdf.save(dest)
    return removed
