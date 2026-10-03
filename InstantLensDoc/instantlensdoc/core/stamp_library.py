"""Eigene Stempel-Bilder verwalten (Ordner) und als Sidecar-Stempel setzen — 1.9.2."""

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
    is_default: bool = False

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "name": self.name,
            "size": self.size,
            "is_default": self.is_default,
        }


def stamp_library_dir() -> Path:
    """Nutzer-Ordner für Stempel-Bilder: ``config/stamps/``."""
    d = config_dir() / "stamps"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _is_stamp_image(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in STAMP_IMAGE_EXTS


def get_default_stamp_name() -> str:
    """Dateiname des Standard-Stempels (leer = keiner) — 1.9.1."""
    from instantlensdoc.core.app_settings import get_default_stamp_image

    return get_default_stamp_image()


def set_default_stamp_name(name: str | None) -> str:
    """Standard-Stempel setzen (Dateiname im Bibliotheksordner) — 1.9.1."""
    from instantlensdoc.core.app_settings import set_default_stamp_image

    return set_default_stamp_image(name)


def list_stamp_images(directory: str | Path | None = None) -> List[StampImageInfo]:
    """Listet Stempel-Bilder im Bibliotheksordner (sortiert nach Name)."""
    root = Path(directory) if directory else stamp_library_dir()
    if not root.is_dir():
        return []
    default_name = ""
    try:
        default_name = get_default_stamp_name()
    except Exception:
        default_name = ""
    items: List[StampImageInfo] = []
    for p in sorted(root.iterdir(), key=lambda x: x.name.lower()):
        if not _is_stamp_image(p):
            continue
        try:
            size = int(p.stat().st_size)
        except OSError:
            size = 0
        items.append(
            StampImageInfo(
                path=p,
                name=p.name,
                size=size,
                is_default=(p.name == default_name),
            )
        )
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
    Entfernt ein Bild aus der Bibliothek (Löschen).
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
    name = p.name
    p.unlink(missing_ok=True)
    try:
        if get_default_stamp_name() == name:
            set_default_stamp_name("")
    except Exception:
        pass
    return True


def rename_stamp_image(
    target: str | Path,
    new_name: str,
    *,
    directory: str | Path | None = None,
) -> StampImageInfo:
    """
    Benennt ein Stempel-Bild in der Bibliothek um — 1.9.1.
    ``new_name`` = neuer Dateiname (mit oder ohne Extension).
    """
    root = Path(directory) if directory else stamp_library_dir()
    p = Path(target)
    if not p.is_file():
        cand = root / p.name
        if cand.is_file():
            p = cand
        else:
            raise FileNotFoundError(f"Stempel-Bild nicht gefunden: {target}")
    try:
        p.resolve().relative_to(root.resolve())
    except ValueError:
        raise ValueError(f"Datei liegt nicht in der Stempel-Bibliothek: {p}")
    if not _is_stamp_image(p):
        raise ValueError(f"Kein unterstütztes Stempel-Bild: {p}")

    nn = Path(new_name).name.strip()
    if not nn:
        raise ValueError("Neuer Name darf nicht leer sein.")
    if Path(nn).suffix.lower() not in STAMP_IMAGE_EXTS:
        nn = f"{Path(nn).stem}{p.suffix.lower()}"
    if Path(nn).suffix.lower() not in STAMP_IMAGE_EXTS:
        raise ValueError(f"Ungültige Dateiendung: {nn}")
    dest = root / nn
    if dest.resolve() == p.resolve():
        try:
            size = int(p.stat().st_size)
        except OSError:
            size = 0
        return StampImageInfo(
            path=p,
            name=p.name,
            size=size,
            is_default=(p.name == get_default_stamp_name()),
        )
    if dest.exists():
        raise FileExistsError(f"Ziel existiert bereits: {nn}")
    old_name = p.name
    p.rename(dest)
    try:
        if get_default_stamp_name() == old_name:
            set_default_stamp_name(dest.name)
    except Exception:
        pass
    try:
        size = int(dest.stat().st_size)
    except OSError:
        size = 0
    return StampImageInfo(
        path=dest,
        name=dest.name,
        size=size,
        is_default=(dest.name == get_default_stamp_name()),
    )


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


def resolve_quick_stamp() -> dict | None:
    """
    Payload für Quick-Stempel-Button — 1.9.2.

    Priorität: zuletzt verwendet → Standard-Bild ★ → erster Text-Preset (GENEHMIGT).
    Rückgabe: ``{"kind": "text"|"image", "text", "color", "image"}`` oder None.
    """
    from instantlensdoc.core.app_settings import get_last_used_stamp

    last = get_last_used_stamp()
    kind = last.get("kind") or ""
    if kind == "image" and last.get("image"):
        cand = stamp_library_dir() / Path(last["image"]).name
        if cand.is_file():
            return {
                "kind": "image",
                "text": "",
                "color": "#CCCCCC",
                "image": cand.name,
                "path": cand,
            }
    if kind == "text" and (last.get("text") or "").strip():
        return {
            "kind": "text",
            "text": str(last["text"]),
            "color": str(last.get("color") or "#C0392B"),
            "image": "",
            "path": None,
        }
    # Standard-Bild ★
    default_name = get_default_stamp_name()
    if default_name:
        cand = stamp_library_dir() / Path(default_name).name
        if cand.is_file():
            return {
                "kind": "image",
                "text": "",
                "color": "#CCCCCC",
                "image": cand.name,
                "path": cand,
            }
    # Fallback Text-Preset
    from ild_pdf.annotate import stamp_with_date

    return {
        "kind": "text",
        "text": stamp_with_date("GENEHMIGT", include_date=True),
        "color": "#1E8449",
        "image": "",
        "path": None,
    }


def remember_stamp_usage(
    *,
    kind: str,
    text: str = "",
    color: str = "#C0392B",
    image: str = "",
) -> None:
    """Persistiert zuletzt verwendeten Stempel — 1.9.2."""
    from instantlensdoc.core.app_settings import set_last_used_stamp

    set_last_used_stamp(kind=kind, text=text, color=color, image=image)
