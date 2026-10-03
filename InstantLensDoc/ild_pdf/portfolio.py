"""PDF-Portfolios (Collection + Attachments) erstellen und öffnen — 2.0.3.

Ein Portfolio ist ein Container-PDF mit eingebetteten Dateien (pikepdf attachments)
und Catalog-/Collection-Eintrag (Adobe PDF Portfolio / PDF Collection).
Extrakt: Fortschritt/Abbruch, Teilergebnis behalten, Namenskollision → Umbenennen — 2.0.3.
"""

from __future__ import annotations

import mimetypes
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Sequence


@dataclass
class PortfolioEntry:
    """Ein Eintrag im Portfolio (Anhang)."""

    name: str
    filename: str = ""
    description: str = ""
    mime_type: str = ""
    size: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PortfolioInfo:
    """Metadaten eines geöffneten/erkannten Portfolios."""

    path: str
    title: str = ""
    is_portfolio: bool = False
    entries: list[PortfolioEntry] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "title": self.title,
            "is_portfolio": self.is_portfolio,
            "entries": [e.to_dict() for e in (self.entries or [])],
            "count": len(self.entries or []),
        }


def _safe_name(name: str) -> str:
    base = "".join(c if c.isalnum() or c in ".-_" else "_" for c in (name or "datei"))
    return (base or "datei")[:80]


def _unique_key(existing: set[str], preferred: str) -> str:
    base = _safe_name(preferred) or "datei"
    if base not in existing:
        return base
    stem = Path(base).stem
    suf = Path(base).suffix
    n = 2
    while True:
        cand = f"{stem}_{n}{suf}"
        if cand not in existing:
            return cand
        n += 1


def is_portfolio(path: str | Path) -> bool:
    """True wenn PDF eine Collection (Portfolio) und/oder Attachments hat."""
    import pikepdf

    path = Path(path)
    if not path.is_file():
        return False
    try:
        with pikepdf.open(path) as pdf:
            root = pdf.Root
            has_coll = "/Collection" in root
            try:
                n_att = len(list(pdf.attachments.keys()))
            except Exception:
                n_att = 0
            return bool(has_coll) or n_att > 0 and has_coll
    except Exception:
        return False


def has_collection(path: str | Path) -> bool:
    """True wenn Catalog /Collection gesetzt ist."""
    import pikepdf

    path = Path(path)
    try:
        with pikepdf.open(path) as pdf:
            return "/Collection" in pdf.Root
    except Exception:
        return False


def list_portfolio_entries(path: str | Path) -> list[PortfolioEntry]:
    """Listet Portfolio-Anhänge (Attachments) als Einträge."""
    from ild_pdf.attachments import list_attachments

    out: list[PortfolioEntry] = []
    for info in list_attachments(path):
        out.append(
            PortfolioEntry(
                name=info.name,
                filename=info.filename or info.name,
                description=info.description or "",
                mime_type=info.mime_type or "",
                size=int(info.size or 0),
            )
        )
    return out


def open_portfolio(path: str | Path) -> PortfolioInfo:
    """
    Portfolio öffnen / inspizieren: Collection + Attachments listen.
    Wirft FileNotFoundError wenn Datei fehlt.
    """
    import pikepdf

    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Portfolio nicht gefunden: {path}")
    title = path.stem
    is_pf = False
    try:
        with pikepdf.open(path) as pdf:
            is_pf = "/Collection" in pdf.Root
            try:
                di = pdf.docinfo
                if di is not None and "/Title" in di:
                    title = str(di["/Title"]) or title
            except Exception:
                pass
    except Exception as exc:
        raise RuntimeError(f"Portfolio konnte nicht geöffnet werden: {exc}") from exc
    entries = list_portfolio_entries(path)
    if not is_pf and entries:
        # Attachments ohne Collection: als „ähnliches“ Portfolio melden
        is_pf = False
    return PortfolioInfo(
        path=str(path.resolve()),
        title=title,
        is_portfolio=is_pf or bool(entries),
        entries=entries,
    )


def create_portfolio(
    out_path: str | Path,
    files: Sequence[str | Path],
    *,
    title: str = "InstantLens Portfolio",
    cover_text: str | None = None,
) -> PortfolioInfo:
    """
    Erstellt ein Container-PDF (Portfolio) mit eingebetteten Dateien
    und Catalog-/Collection (pikepdf attachments + /Collection).
    """
    import pikepdf

    out_path = Path(out_path)
    if out_path.suffix.lower() != ".pdf":
        out_path = out_path.with_suffix(".pdf")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    file_paths: list[Path] = []
    for raw in files:
        p = Path(raw)
        if p.is_file():
            file_paths.append(p)
    if not file_paths:
        raise ValueError("Keine gültigen Dateien für das Portfolio.")

    used_keys: set[str] = set()
    with pikepdf.Pdf.new() as pdf:
        # Cover-Seite (Portfolio braucht mindestens eine Seite)
        pdf.add_blank_page(page_size=(595, 842))  # A4
        try:
            with pdf.open_metadata() as meta:
                meta["dc:title"] = title or "InstantLens Portfolio"
                meta["dc:creator"] = ["InstantLens Doc"]
        except Exception:
            pass
        try:
            pdf.docinfo["/Title"] = title or "InstantLens Portfolio"
            pdf.docinfo["/Creator"] = "InstantLens Doc 2.0"
        except Exception:
            pass

        for fp in file_paths:
            key = _unique_key(used_keys, fp.name)
            used_keys.add(key)
            data = fp.read_bytes()
            pdf.attachments[key] = data
            try:
                spec = pdf.attachments[key]
                try:
                    spec.description = cover_text or f"Portfolio-Datei: {fp.name}"
                except Exception:
                    pass
                mime, _ = mimetypes.guess_type(str(fp))
                if mime:
                    try:
                        af = spec.get_file()
                        if hasattr(af, "mime_type"):
                            af.mime_type = mime
                    except Exception:
                        pass
            except Exception:
                pass

        # PDF Collection / Portfolio Catalog
        coll = pikepdf.Dictionary(
            {
                "/Type": pikepdf.Name("/Collection"),
                "/View": pikepdf.Name("/D"),  # Details
            }
        )
        pdf.Root["/Collection"] = coll
        pdf.Root["/PageMode"] = pikepdf.Name("/UseAttachments")
        pdf.save(out_path)

    return open_portfolio(out_path)


def extract_portfolio(
    path: str | Path,
    out_dir: str | Path | None = None,
    *,
    on_progress: Callable[[int, int, str], bool | None] | None = None,
) -> list[Path]:
    """
    Alle Portfolio-Anhänge extrahieren.
    Namenskollision → Umbenennen (_2, _3, …); optional Fortschritt.
    ``on_progress`` darf ``False`` zurückgeben → Abbruch; Teilergebnis bleibt — 2.0.3.
    """
    from ild_pdf.attachments import extract_attachment, list_attachments

    path = Path(path)
    dest = Path(out_dir) if out_dir else path.parent / f"{path.stem}_portfolio"
    dest.mkdir(parents=True, exist_ok=True)
    infos = list_attachments(path)
    total = len(infos)
    written: list[Path] = []
    for i, info in enumerate(infos, start=1):
        if on_progress is not None:
            try:
                cont = on_progress(i, total, info.filename or info.name)
            except Exception:
                cont = True
            if cont is False:
                break
        written.append(extract_attachment(path, info.name, out_dir=dest))
    return written


def extract_portfolio_entries(
    path: str | Path,
    names: Sequence[str],
    out_dir: str | Path | None = None,
    *,
    on_progress: Callable[[int, int, str], bool | None] | None = None,
) -> list[Path]:
    """
    Ausgewählte Portfolio-Einträge extrahieren (nach Name/Dateiname).
    Namenskollision → Umbenennen; Abbruch behält Teilergebnis — 2.0.3.
    """
    from ild_pdf.attachments import extract_attachment

    path = Path(path)
    dest = Path(out_dir) if out_dir else path.parent / f"{path.stem}_portfolio"
    dest.mkdir(parents=True, exist_ok=True)
    keys = [str(n or "").strip() for n in (names or []) if str(n or "").strip()]
    total = len(keys)
    written: list[Path] = []
    for i, key in enumerate(keys, start=1):
        if on_progress is not None:
            try:
                cont = on_progress(i, total, key)
            except Exception:
                cont = True
            if cont is False:
                break
        written.append(extract_attachment(path, key, out_dir=dest))
    return written


def count_renamed_extracts(written: Sequence[Path]) -> int:
    """
    Zählt Extrakte mit Kollisions-Suffix ``_2``, ``_3``, … — 2.0.2.
    Entspricht der Umbenennung in ``extract_attachment``.
    """
    n = 0
    for p in written or []:
        stem = Path(p).stem
        if "_" not in stem:
            continue
        base, suf = stem.rsplit("_", 1)
        if base and suf.isdigit() and int(suf) >= 2:
            n += 1
    return n


def summarize_extract_status(
    written: Sequence[Path],
    *,
    total: int,
    cancelled: bool = False,
) -> str:
    """
    Statuszählung Portfolio-Extrakt:
    ``extrahiert X, übersprungen Y`` (+ umbenannt/abgebrochen) — 2.0.4.
    """
    n = len(written or [])
    skipped = max(0, int(total) - n)
    renamed = count_renamed_extracts(written)
    # Footer-Kern: „extrahiert X, übersprungen Y“ — 2.0.4
    parts = [f"extrahiert {n}, übersprungen {skipped}"]
    if renamed:
        parts.append(f"umbenannt {renamed}")
    if cancelled:
        parts.append(f"abgebrochen ({n} von {max(int(total), n)})")
    return " · ".join(parts)


def format_extract_footer(
    written: Sequence[Path],
    *,
    total: int,
) -> str:
    """Footer-Kurzform ``extrahiert X, übersprungen Y`` — 2.0.4."""
    n = len(written or [])
    skipped = max(0, int(total) - n)
    return f"extrahiert {n}, übersprungen {skipped}"
