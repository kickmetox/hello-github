"""PDF-Anhänge (Embedded Files / NameTree) auflisten und extrahieren."""

from __future__ import annotations

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
