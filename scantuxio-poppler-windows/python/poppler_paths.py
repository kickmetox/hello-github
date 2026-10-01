"""
ScanTuxio — Poppler-Pfadauflösung für Windows (und Fallback Linux/macOS).

Findet pdftoppm/pdfinfo/pdftocairo und setzt PATH sowie Umgebungsvariablen,
damit pdf2image und ähnliche Wrapper ohne manuelle Konfiguration funktionieren.

Nutzung (früh im Start, z. B. in scantuxio_entry.py):

    from poppler_paths import ensure_poppler
    info = ensure_poppler(required=False)
    if not info.ok:
        # UI-Hinweis / FEATURES-Fehlermeldung
        ...
"""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

REQUIRED_TOOLS = ("pdftoppm", "pdfinfo")
OPTIONAL_TOOLS = ("pdftocairo", "pdftotext")


@dataclass(frozen=True)
class PopplerInfo:
    ok: bool
    bin_dir: Optional[Path]
    tools: dict[str, Optional[Path]]
    source: str
    message: str

    @property
    def poppler_path(self) -> Optional[str]:
        """Pfad für pdf2image.convert_from_path(..., poppler_path=...)."""
        return str(self.bin_dir) if self.bin_dir else None


def _exe_name(tool: str) -> str:
    return f"{tool}.exe" if os.name == "nt" else tool


def _app_roots() -> list[Path]:
    """Mögliche Install-/Bundle-Wurzeln (frozen exe, Skript, CWD)."""
    roots: list[Path] = []
    if getattr(sys, "frozen", False):
        roots.append(Path(sys.executable).resolve().parent)
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            roots.append(Path(meipass))
    try:
        roots.append(Path(__file__).resolve().parent.parent)
    except NameError:
        pass
    roots.append(Path.cwd())
    # Dedup unter Beibehaltung der Reihenfolge
    seen: set[Path] = set()
    out: list[Path] = []
    for r in roots:
        try:
            r = r.resolve()
        except OSError:
            continue
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def _candidate_bin_dirs(roots: Sequence[Path]) -> Iterable[Path]:
    """Typische Layouts: vendor/poppler, poppler-windows Release-Zip, conda-ähnlich."""
    rels = (
        Path("vendor") / "poppler" / "Library" / "bin",
        Path("vendor") / "poppler" / "bin",
        Path("poppler") / "Library" / "bin",
        Path("poppler") / "bin",
        Path("Library") / "bin",
        Path("bin"),
    )
    for root in roots:
        for rel in rels:
            yield root / rel
        # Release-26.xx.x-0.zip → Release-*/Library/bin
        vendor = root / "vendor" / "poppler"
        if vendor.is_dir():
            for child in sorted(vendor.glob("Release-*")):
                yield child / "Library" / "bin"
                yield child / "bin"


def _env_bin_dirs() -> Iterable[Path]:
    for key in ("SCANTUXIO_POPPLER", "POPPLER_PATH", "PDF2IMAGE_POPPLER_PATH"):
        raw = os.environ.get(key)
        if not raw:
            continue
        p = Path(raw)
        # Nutzer kann bin-Ordner oder Poppler-Root angeben
        if (p / _exe_name("pdftoppm")).is_file():
            yield p
        elif (p / "bin" / _exe_name("pdftoppm")).is_file():
            yield p / "bin"
        elif (p / "Library" / "bin" / _exe_name("pdftoppm")).is_file():
            yield p / "Library" / "bin"
        else:
            yield p


def _which_tool(tool: str, bin_dir: Optional[Path] = None) -> Optional[Path]:
    name = _exe_name(tool)
    if bin_dir is not None:
        candidate = bin_dir / name
        if candidate.is_file():
            return candidate
        return None
    found = shutil.which(name)
    return Path(found) if found else None


def _probe(bin_dir: Optional[Path], source: str) -> PopplerInfo:
    tools: dict[str, Optional[Path]] = {}
    for t in REQUIRED_TOOLS + OPTIONAL_TOOLS:
        tools[t] = _which_tool(t, bin_dir)
    missing = [t for t in REQUIRED_TOOLS if not tools[t]]
    if missing:
        where = str(bin_dir) if bin_dir else "PATH"
        return PopplerInfo(
            ok=False,
            bin_dir=bin_dir,
            tools=tools,
            source=source,
            message=f"Poppler unvollständig unter {where}: fehlt {', '.join(missing)}",
        )
    return PopplerInfo(
        ok=True,
        bin_dir=bin_dir if bin_dir is not None else tools["pdftoppm"].parent,  # type: ignore[union-attr]
        tools=tools,
        source=source,
        message=f"Poppler OK ({source}): {bin_dir or tools['pdftoppm'].parent}",
    )


def find_poppler() -> PopplerInfo:
    # 1) Explizite Env
    for d in _env_bin_dirs():
        info = _probe(d, "env")
        if info.ok:
            return info

    # 2) Bundle neben App
    for d in _candidate_bin_dirs(_app_roots()):
        if d.is_dir():
            info = _probe(d, "bundle")
            if info.ok:
                return info

    # 3) System-PATH
    info = _probe(None, "path")
    if info.ok:
        return info

    return PopplerInfo(
        ok=False,
        bin_dir=None,
        tools={t: None for t in REQUIRED_TOOLS + OPTIONAL_TOOLS},
        source="none",
        message=(
            "Poppler nicht gefunden. Erwartet: vendor/poppler/Library/bin "
            "(pdftoppm, pdfinfo) neben der App, oder SCANTUXIO_POPPLER / POPPLER_PATH."
        ),
    )


def apply_poppler_env(info: PopplerInfo) -> None:
    """PATH und Convenience-Variablen setzen (für Subprozesse / pdf2image)."""
    if not info.ok or not info.bin_dir:
        return
    bin_s = str(info.bin_dir)
    os.environ["SCANTUXIO_POPPLER"] = bin_s
    os.environ["POPPLER_PATH"] = bin_s
    path = os.environ.get("PATH", "")
    parts = path.split(os.pathsep) if path else []
    if bin_s not in parts:
        os.environ["PATH"] = bin_s + os.pathsep + path


def ensure_poppler(*, required: bool = False) -> PopplerInfo:
    info = find_poppler()
    if info.ok:
        apply_poppler_env(info)
        return info
    if required:
        raise FileNotFoundError(info.message)
    return info


def pdf2image_kwargs() -> dict:
    """Hilfs-kwargs für convert_from_path / convert_from_bytes."""
    info = ensure_poppler(required=False)
    if info.ok and info.poppler_path:
        return {"poppler_path": info.poppler_path}
    return {}
