"""PDF-Seiten-Thumbnail Disk-Cache — mtime · max MB · Hit/Miss Debug — 2.4.1."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Optional, Union

from PIL import Image

from instantlensdoc.config import config_dir

# Max. Einträge im Disk-Cache (LRU per mtime der Cache-Dateien) — Soft-Cap
_DISK_CACHE_MAX = 2000

# Session Hit/Miss Zähler (optional Debug) — 2.4.1
_hits = 0
_misses = 0


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


def _record_hit() -> None:
    global _hits
    _hits += 1


def _record_miss() -> None:
    global _misses
    _misses += 1


def reset_hit_miss_stats() -> None:
    """Hit/Miss-Zähler zurücksetzen — 2.4.1."""
    global _hits, _misses
    _hits = 0
    _misses = 0


def hit_miss_stats() -> dict:
    """Session Hit/Miss Stats für optionalen Debug-Status — 2.4.1."""
    total = _hits + _misses
    rate = (100.0 * _hits / total) if total else 0.0
    return {
        "hits": int(_hits),
        "misses": int(_misses),
        "total": int(total),
        "hit_rate_pct": round(rate, 1),
    }


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
        _record_miss()
        return None
    key = cache_key(
        p, page_index, scale, grayscale=grayscale, invert=invert
    )
    dest = cache_file_for_key(key)
    if not dest.is_file():
        _record_miss()
        return None
    try:
        img = Image.open(dest)
        img.load()
        _record_hit()
        return img.copy()
    except Exception:
        try:
            dest.unlink(missing_ok=True)
        except OSError:
            pass
        _record_miss()
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
    # Ohne Index-Datei: mtime-Key invalidiert bei nächstem Render.
    _ = Path(pdf_path)
    return 0


def clear_thumb_cache() -> int:
    """Gesamten Thumbnail-Disk-Cache leeren. Rückgabe: gelöschte Dateien."""
    n = invalidate_pdf_thumbnails(None)
    reset_hit_miss_stats()
    return n


def _max_bytes_from_settings() -> int | None:
    """Max. Cache-Größe in Bytes aus Settings (None = nur Entry-Cap)."""
    try:
        from instantlensdoc.core.app_settings import get_thumb_cache_max_mb

        mb = int(get_thumb_cache_max_mb())
    except Exception:
        mb = 100
    if mb <= 0:
        return None
    return max(1, mb) * 1024 * 1024


def _trim_disk_cache(max_entries: int = _DISK_CACHE_MAX) -> None:
    """LRU nach mtime: Entry-Cap + optionale max-MB-Grenze — 2.4.1."""
    root = thumb_cache_dir()
    files = list(root.glob("*.png"))
    if not files:
        return

    def _mtime(f: Path) -> float:
        try:
            return f.stat().st_mtime
        except OSError:
            return 0.0

    files.sort(key=_mtime)

    # 1) Entry-Cap
    if len(files) > max_entries:
        overflow = len(files) - max_entries
        for f in files[:overflow]:
            try:
                f.unlink()
            except OSError:
                pass
        files = files[overflow:]

    # 2) Max-MB Cap
    max_bytes = _max_bytes_from_settings()
    if max_bytes is None:
        return
    sizes: list[tuple[Path, int]] = []
    total = 0
    for f in files:
        try:
            sz = int(f.stat().st_size)
        except OSError:
            continue
        sizes.append((f, sz))
        total += sz
    if total <= max_bytes:
        return
    # älteste zuerst löschen
    for f, sz in sizes:
        if total <= max_bytes:
            break
        try:
            f.unlink()
            total -= sz
        except OSError:
            pass


def thumb_cache_stats() -> dict:
    """Einfache Stats für Smoke/Diagnose inkl. Hit/Miss — 2.4.1."""
    root = thumb_cache_dir()
    files = list(root.glob("*.png"))
    size = 0
    for f in files:
        try:
            size += f.stat().st_size
        except OSError:
            pass
    hm = hit_miss_stats()
    try:
        from instantlensdoc.core.app_settings import get_thumb_cache_max_mb

        max_mb = int(get_thumb_cache_max_mb())
    except Exception:
        max_mb = 100
    return {
        "dir": str(root),
        "count": len(files),
        "bytes": size,
        "max_mb": max_mb,
        "hits": hm["hits"],
        "misses": hm["misses"],
        "hit_rate_pct": hm["hit_rate_pct"],
    }
