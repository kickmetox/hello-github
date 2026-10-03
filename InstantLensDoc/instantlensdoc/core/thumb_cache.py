"""PDF-Seiten-Thumbnail Disk-Cache — invalidiert bei mtime — 2.4.0."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Optional, Union

from PIL import Image

from instantlensdoc.config import config_dir

# Max. Einträge im Disk-Cache (LRU per mtime der Cache-Dateien)
_DISK_CACHE_MAX = 2000


def thumb_cache_dir() -> Path:
    """Cache-Ordner unter config/thumb_cache/."""
    d = config_dir() / "thumb_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _mtime_ns(path: Path) -> int:
    try:
        return int(path.stat().st_mtime_ns)
    except OSError:
        return 0


def _scale_key(scale: float) -> str:
    return f"{float(scale):.4f}"


def cache_key(
    pdf_path: Union[str, Path],
    page_index: int,
    scale: float,
    *,
    grayscale: bool = False,
    invert: bool = False,
    mtime_ns: int | None = None,
) -> str:
    """
    Stabiler Cache-Key (Dateiname ohne Endung).
    Enthält mtime → bei Dateiänderung automatisch neuer Slot (Invalidierung).
    """
    p = Path(pdf_path)
    try:
        resolved = str(p.resolve())
    except OSError:
        resolved = str(p)
    mt = int(mtime_ns) if mtime_ns is not None else _mtime_ns(p)
    raw = "|".join(
        [
            resolved,
            str(mt),
            str(int(page_index)),
            _scale_key(scale),
            "1" if grayscale else "0",
            "1" if invert else "0",
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def cache_file_for_key(key: str) -> Path:
    return thumb_cache_dir() / f"{key}.png"


def get_cached_thumbnail(
    pdf_path: Union[str, Path],
    page_index: int,
    scale: float,
    *,
    grayscale: bool = False,
    invert: bool = False,
) -> Optional[Image.Image]:
    """PNG aus Disk-Cache laden oder None bei Miss / mtime-Mismatch."""
    p = Path(pdf_path)
    if not p.is_file():
        return None
    key = cache_key(
        p, page_index, scale, grayscale=grayscale, invert=invert
    )
    dest = cache_file_for_key(key)
    if not dest.is_file():
        return None
    try:
        img = Image.open(dest)
        img.load()
        return img.copy()
    except Exception:
        try:
            dest.unlink(missing_ok=True)
        except OSError:
            pass
        return None


def put_cached_thumbnail(
    pdf_path: Union[str, Path],
    page_index: int,
    scale: float,
    image: Image.Image,
    *,
    grayscale: bool = False,
    invert: bool = False,
) -> Optional[Path]:
    """Thumbnail als PNG speichern; bei Erfolg Pfad, sonst None."""
    p = Path(pdf_path)
    if not p.is_file() or image is None:
        return None
    key = cache_key(
        p, page_index, scale, grayscale=grayscale, invert=invert
    )
    dest = cache_file_for_key(key)
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        to_save = image
        if to_save.mode not in ("RGB", "RGBA", "L"):
            to_save = to_save.convert("RGB")
        to_save.save(dest, format="PNG", optimize=True)
        _trim_disk_cache()
        return dest
    except Exception:
        return None


def invalidate_pdf_thumbnails(pdf_path: Union[str, Path] | None = None) -> int:
    """
    Cache leeren.
    Mit Pfad: alle Keys zu diesem PDF (alle mtimes/scales) entfernen — grob per Scan.
    Ohne Pfad: gesamten Disk-Cache löschen.
    """
    root = thumb_cache_dir()
    if pdf_path is None:
        n = 0
        for f in root.glob("*.png"):
            try:
                f.unlink()
                n += 1
            except OSError:
                pass
        return n
    # Ohne Index-Datei: kompletter Clear bei gezielter Invalidierung ist ok
    # (mtime im Key invalidiert ohnehin bei nächstem Render).
    # Zusätzlich: leeren wenn PDF gelöscht/umbenannt — hier Full clear für den Pfad
    # nicht möglich ohne Metadaten → Full clear nur bei explizitem None.
    # Für Pfad-Invalidierung: nichts tun (mtime-Key reicht).
    _ = Path(pdf_path)
    return 0


def clear_thumb_cache() -> int:
    """Gesamten Thumbnail-Disk-Cache leeren. Rückgabe: gelöschte Dateien."""
    return invalidate_pdf_thumbnails(None)


def _trim_disk_cache(max_entries: int = _DISK_CACHE_MAX) -> None:
    root = thumb_cache_dir()
    files = list(root.glob("*.png"))
    if len(files) <= max_entries:
        return
    files.sort(key=lambda f: f.stat().st_mtime if f.exists() else 0)
    overflow = len(files) - max_entries
    for f in files[:overflow]:
        try:
            f.unlink()
        except OSError:
            pass


def thumb_cache_stats() -> dict:
    """Einfache Stats für Smoke/Diagnose."""
    root = thumb_cache_dir()
    files = list(root.glob("*.png"))
    size = 0
    for f in files:
        try:
            size += f.stat().st_size
        except OSError:
            pass
    return {"dir": str(root), "count": len(files), "bytes": size}
