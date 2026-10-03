"""Eigene Stempel-Bilder verwalten (Ordner) und als Sidecar-Stempel setzen — 1.9.0."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Union

from instantlensdoc.config import config_dir

STAMP_IMAGE_EXTS = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"})


@dataclass(frozen=True)
class StampImageInfo:
    """Eintrag in der Stempel-Bildbibliothek."""

    path: Path
    name: str
    size: int = 0

    def to_dict(self) -> dict:
        return {"path": str(self.path), "name": self.name, "size": self.size}


def stamp_library_dir() -> Path:
    """Nutzer-Ordner für Stempel-Bilder: ``config/stamps/``."""
    d = config_dir() / "stamps"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _is_stamp_image(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in STAMP_IMAGE_EXTS


def list_stamp_images(directory: str | Path | None = None) -> List[StampImageInfo]:
    """Listet Stempel-Bilder im Bibliotheksordner (sortiert nach Name)."""
    root = Path(directory) if directory else stamp_library_dir()
    if not root.is_dir():
        return []
    items: List[StampImageInfo] = []
    for p in sorted(root.iterdir(), key=lambda x: x.name.lower()):
        if not _is_stamp_image(p):
            continue
        try:
            size = int(p.stat().st_size)
        except OSError:
            size = 0
        items.append(StampImageInfo(path=p, name=p.name, size=size))
    return items


def _unique_dest(dest_dir: Path, filename: str) -> Path:
    dest = dest_dir / filename
    if not dest.exists():
        return dest
    stem, suf = Path(filename).stem, Path(filename).suffix
    n = 2
    while True:
        cand = dest_dir / f"{stem}_{n}{suf}"
        if not cand.exists():
            return cand
        n += 1


def add_stamp_image(
    source: str | Path,
    *,
    directory: str | Path | None = None,
    name: str | None = None,
) -> StampImageInfo:
    """Kopiert ein Bild in die Stempel-Bibliothek. Rückgabe: neuer Eintrag."""
    src = Path(source)
    if not _is_stamp_image(src):
        raise ValueError(f"Kein unterstütztes Stempel-Bild: {src}")
    root = Path(directory) if directory else stamp_library_dir()
    root.mkdir(parents=True, exist_ok=True)
    filename = name or src.name
    # nur Basename, keine Pfadsegmente
    filename = Path(filename).name
    if Path(filename).suffix.lower() not in STAMP_IMAGE_EXTS:
        filename = f"{Path(filename).stem}{src.suffix.lower()}"
    dest = _unique_dest(root, filename)
    shutil.copy2(src, dest)
    try:
        size = int(dest.stat().st_size)
    except OSError:
        size = 0
    return StampImageInfo(path=dest, name=dest.name, size=size)


def remove_stamp_image(
    target: str | Path,
    *,
    directory: str | Path | None = None,
) -> bool:
    """
    Entfernt ein Bild aus der Bibliothek.
    ``target`` = Pfad oder Dateiname im Bibliotheksordner.
    """
    root = Path(directory) if directory else stamp_library_dir()
    p = Path(target)
    if not p.is_file():
        cand = root / p.name
        if cand.is_file():
            p = cand
        else:
            return False
    # Sicherheit: nur Dateien im Bibliotheksordner löschen
    try:
        p.resolve().relative_to(root.resolve())
    except ValueError:
        raise ValueError(f"Datei liegt nicht in der Stempel-Bibliothek: {p}")
    if not _is_stamp_image(p):
        return False
    p.unlink(missing_ok=True)
    return True


def place_library_stamp(
    pdf_path: str | Path,
    image: Union[str, Path],
    page_index: int = 0,
    *,
    x: float = 72.0,
    y: float = 72.0,
    width: float = 160.0,
    height: float = 80.0,
) -> Path:
    """
    Platziert ein Bibliotheks-Bild als Sidecar-Stempel-Annotation
    (``text=img:…`` via ``insert_image_stamp_overlay``).
    """
    from ild_pdf.images import insert_image_stamp_overlay

    img = Path(image)
    if not img.is_file():
        # Name relativ zur Bibliothek
        cand = stamp_library_dir() / img.name
        if cand.is_file():
            img = cand
        else:
            raise FileNotFoundError(f"Stempel-Bild nicht gefunden: {image}")
    return insert_image_stamp_overlay(
        pdf_path,
        img,
        page_index=page_index,
        x=x,
        y=y,
        width=width,
        height=height,
    )


def stamp_library_labels(
    items: Sequence[StampImageInfo] | None = None,
) -> List[str]:
    """Anzeige-Labels für UI-Listen."""
    src = items if items is not None else list_stamp_images()
    return [i.name for i in src]
