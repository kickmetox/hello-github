"""ScanTuxio-Hauptfenster starten und Scan-Dateien nach ILD übernehmen — 2.6.46.

Primärer Scan-Einstieg: externe ScanTuxio-Win-UI (subprocess).
Handshake: Übergabeordner (ILD_SCAN_HANDOFF) + neue Dateien im ScanTuxio-Basisordner.
WIA bleibt sekundärer Fallback (siehe ``scan.py``).
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence

# Kein Import von ocr.py (PIL) — Scan-UI-Bridge muss auch ohne Pillow laden — 2.6.51
try:
    from instantlensdoc.core.ocr import (  # type: ignore
        SCANTUXIO_WIN_ROOTS as _OCR_ROOTS,
        _ild_app_roots as _ocr_ild_roots,
        _join_win_or_posix as _ocr_join,
    )

    SCANTUXIO_WIN_ROOTS = _OCR_ROOTS
    _ild_app_roots = _ocr_ild_roots
    _join_win_or_posix = _ocr_join
except Exception:  # pragma: no cover
    SCANTUXIO_WIN_ROOTS = (
        r"D:\AI_Temp\ScanTuxio Win",
        r"D:\AI_Temp\ScanTuxio-Win",
        r"D:\AI_Temp\ScanTuxioWin",
    )

    def _ild_app_roots() -> List[Path]:
        roots: List[Path] = []
        if getattr(sys, "frozen", False):
            roots.append(Path(sys.executable).parent)
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            roots.append(Path(str(meipass)))
        roots.append(Path(__file__).resolve().parents[2])
        roots.append(Path.cwd())
        out: List[Path] = []
        for r in roots:
            if r not in out:
                out.append(r)
        return out

    def _join_win_or_posix(root: str, *parts: str) -> str:
        p = Path(root)
        for part in parts:
            p = p / part
        return str(p)


try:
    from instantlensdoc.core.scan import IMAGE_SUFFIXES
except Exception:  # pragma: no cover
    IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}


HANDOFF_ENV = "ILD_SCAN_HANDOFF"
HANDOFF_ENV_ALT = "SCANTUXIO_HANDOFF"

SCAN_IMPORT_SUFFIXES = IMAGE_SUFFIXES | {".pdf", ".tif", ".tiff"}

WIA_BUSY_PATTERNS = (
    "ausgelastet",
    "in use",
    "busy",
    "0x80210006",
    "wia_error_busy",
    "device busy",
    "wird verwendet",
    "bereits geöffnet",
    "already in use",
    "cannot communicate",
    "gerät ist beschäftigt",
    "the device is busy",
)

WIA_HOLDER_HINT_DE = (
    "Ein anderes Programm hält das WIA-Gerät. Bitte schließen:\n"
    "  • ScanTuxio\n"
    "  • Windows Fax und Scan\n"
    "  • einen vorherigen InstantLens-Doc-Scan\n"
    "Danach „Erneut versuchen“ oder ScanTuxio als Scan-Oberfläche nutzen."
)

SCANTUXIO_MISSING_HINT_DE = (
    "ScanTuxio wurde nicht gefunden.\n\n"
    "Erwarteter Pfad auf diesem PC:\n"
    "  D:\\AI_Temp\\ScanTuxio Win\n"
    "  (ScanTuxio.exe oder scantuxio\\main.py)\n\n"
    "Weitere Suchorte: neben InstantLens Doc, vendor\\ScanTuxio, PATH.\n"
    "Ohne ScanTuxio: „Bilder importieren…“ nutzen."
)

# Prozessnamen, die WIA oft blockieren
_WIA_HOLDER_NAMES = (
    "ScanTuxio.exe",
    "ScanTuxio",
    "wfs.exe",
    "WFS.exe",
    "wiaacmgr.exe",
    "WiaAcMgr.exe",
    "InstantLensDoc.exe",
)


@dataclass
class ScanTuxioInstall:
    """Gefundene ScanTuxio-Installation."""

    root: str
    exe: str = ""
    main_py: str = ""
    via: str = ""

    def is_usable(self) -> bool:
        return bool(self.exe or self.main_py)


@dataclass
class ScanTuxioLaunch:
    argv: List[str]
    cwd: str
    env: dict
    handshake_dir: str
    install: ScanTuxioInstall
    env_extra: dict = field(default_factory=dict)


def _exists_file(path: str) -> bool:
    try:
        return bool(path) and Path(path).is_file()
    except OSError:
        return False


def _exists_dir(path: str) -> bool:
    try:
        return bool(path) and Path(path).is_dir()
    except OSError:
        return False


def scantuxio_root_candidates() -> List[str]:
    """Lookup-Reihenfolge (Pfade müssen nicht existieren)."""
    cands: List[str] = []

    def _push(p: object) -> None:
        s = str(p or "").strip()
        if s and s not in cands:
            cands.append(s)

    for key in ("SCANTUXIO_HOME", "SCANTUXIO_ROOT", "SCANTUXIO_WIN"):
        _push(os.environ.get(key))
    for win_root in SCANTUXIO_WIN_ROOTS:
        _push(win_root)
    for app in _ild_app_roots():
        _push(_join_win_or_posix(str(app), "ScanTuxio Win"))
        _push(_join_win_or_posix(str(app), "ScanTuxio-Win"))
        _push(_join_win_or_posix(str(app), "ScanTuxio"))
        _push(_join_win_or_posix(str(app), "vendor", "ScanTuxio Win"))
        _push(_join_win_or_posix(str(app), "vendor", "ScanTuxio"))
        _push(_join_win_or_posix(str(app), "..", "ScanTuxio Win"))
        try:
            parent = Path(app).parent
            _push(str(parent / "ScanTuxio Win"))
            _push(str(parent / "ScanTuxio"))
        except Exception:
            pass
    which = shutil.which("ScanTuxio") or shutil.which("ScanTuxio.exe")
    if which:
        try:
            _push(str(Path(which).parent))
        except Exception:
            pass
    return cands


def _probe_root(root: str) -> Optional[ScanTuxioInstall]:
    if not root:
        return None
    exe = ""
    for rel in (
        ("ScanTuxio.exe",),
        ("ScanTuxio",),
        ("dist", "ScanTuxio", "ScanTuxio.exe"),
        ("dist", "ScanTuxio.exe"),
        ("bin", "ScanTuxio.exe"),
    ):
        p = _join_win_or_posix(root, *rel)
        if _exists_file(p):
            exe = p
            break
    main_py = _join_win_or_posix(root, "scantuxio", "main.py")
    if not _exists_file(main_py):
        nested = _join_win_or_posix(root, "ScanTuxio-Win", "scantuxio", "main.py")
        if _exists_file(nested):
            main_py = nested
            root = _join_win_or_posix(root, "ScanTuxio-Win")
        else:
            main_py = ""
    if not exe and not main_py:
        # Nur Quellen ohne main.py (ILD-vendor core) gelten nicht als UI
        ui = _join_win_or_posix(root, "scantuxio", "ui", "main_window.py")
        if not _exists_file(ui):
            return None
        main_py = _join_win_or_posix(root, "scantuxio", "main.py")
        if not _exists_file(main_py):
            return None
    inst = ScanTuxioInstall(root=root, exe=exe, main_py=main_py, via="probe")
    return inst if inst.is_usable() else None


def find_scantuxio_install() -> Optional[ScanTuxioInstall]:
    """Erste nutzbare ScanTuxio-UI-Installation."""
    for root in scantuxio_root_candidates():
        inst = _probe_root(root)
        if inst and inst.is_usable():
            inst.via = root
            return inst
    return None


def missing_scantuxio_hint_de() -> str:
    lines = [SCANTUXIO_MISSING_HINT_DE, "", "Geprüfte Kandidaten:"]
    for c in scantuxio_root_candidates()[:12]:
        lines.append(f"  • {c}")
    return "\n".join(lines)


def prepare_handshake_dir(out_dir: str | Path | None = None) -> Path:
    """Ordner, in den ScanTuxio speichern soll (Handshake)."""
    if out_dir:
        d = Path(out_dir)
        d.mkdir(parents=True, exist_ok=True)
    else:
        d = Path(tempfile.mkdtemp(prefix="ild-st-handoff-"))
    note = d / "ILD-HIER-SPEICHERN.txt"
    if not note.exists():
        note.write_text(
            "InstantLens Doc — Scan-Übergabe\n\n"
            "Bitte das gescannte Dokument (PDF oder Bild) in DIESEM Ordner speichern.\n"
            "InstantLens Doc übernimmt neue Dateien automatisch bzw. per „Scan übernehmen“.\n",
            encoding="utf-8",
        )
    return d


def default_watch_dirs(install: Optional[ScanTuxioInstall], handshake: Path) -> List[Path]:
    dirs: List[Path] = [handshake]
    home_scans = Path.home() / "Scans"
    dirs.append(home_scans)
    if install:
        dirs.append(Path(install.root) / "Scans")
        dirs.append(Path(install.root) / "scans")
    env_base = os.environ.get("SCANTUXIO_BASE_FOLDER")
    if env_base:
        dirs.append(Path(env_base))
    out: List[Path] = []
    seen: set[str] = set()
    for d in dirs:
        try:
            key = str(d)
        except Exception:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(d)
    return out


def snapshot_scan_files(roots: Sequence[Path]) -> dict[str, tuple[int, int]]:
    """Pfad → (mtime_ns, size) für Bilder/PDFs."""
    snap: dict[str, tuple[int, int]] = {}
    for root in roots:
        try:
            if not root.is_dir():
                continue
        except OSError:
            continue
        try:
            entries = list(root.iterdir())
        except OSError:
            continue
        for p in entries:
            try:
                if not p.is_file():
                    continue
                if p.suffix.lower() not in SCAN_IMPORT_SUFFIXES:
                    continue
                st = p.stat()
                snap[str(p)] = (int(st.st_mtime_ns), int(st.st_size))
            except OSError:
                continue
    return snap


def collect_new_scan_files(
    roots: Sequence[Path],
    before: dict[str, tuple[int, int]],
    *,
    min_size: int = 32,
) -> List[Path]:
    """Neue oder gewachsene Scan-Dateien seit ``before``."""
    after = snapshot_scan_files(roots)
    out: List[Path] = []
    for key, meta in after.items():
        mtime_ns, size = meta
        if size < min_size:
            continue
        old = before.get(key)
        if old is None or mtime_ns > old[0] or size > old[1]:
            out.append(Path(key))
    out.sort(key=lambda p: p.stat().st_mtime_ns if p.exists() else 0)
    return out


def python_for_scantuxio() -> str:
    if not getattr(sys, "frozen", False) and sys.executable:
        return sys.executable
    return (
        shutil.which("python")
        or shutil.which("python3")
        or shutil.which("py")
        or "python"
    )


def build_launch(install: ScanTuxioInstall, handshake: Path) -> ScanTuxioLaunch:
    env = os.environ.copy()
    env[HANDOFF_ENV] = str(handshake)
    env[HANDOFF_ENV_ALT] = str(handshake)
    extra = {HANDOFF_ENV: str(handshake), HANDOFF_ENV_ALT: str(handshake)}
    handoff_arg = f"--ild-handoff={handshake}"
    if install.exe:
        argv = [install.exe, handoff_arg]
        cwd = str(Path(install.exe).parent)
    else:
        py = python_for_scantuxio()
        argv = [py, "-m", "scantuxio.main", handoff_arg]
        cwd = install.root
        pp = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = install.root + (os.pathsep + pp if pp else "")
        extra["PYTHONPATH"] = env["PYTHONPATH"]
    return ScanTuxioLaunch(
        argv=argv,
        cwd=cwd,
        env=env,
        handshake_dir=str(handshake),
        install=install,
        env_extra=extra,
    )


def popen_kwargs_show_window() -> dict:
    """GUI-Subprocess: Fenster zeigen (kein CREATE_NO_WINDOW)."""
    kw: dict = {}
    if platform.system() == "Windows":
        flags = 0
        flags |= int(getattr(subprocess, "DETACHED_PROCESS", 0x00000008) or 0)
        flags |= int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200) or 0)
        if flags:
            kw["creationflags"] = flags
    return kw


def launch_scantuxio_process(launch: ScanTuxioLaunch) -> subprocess.Popen:
    return subprocess.Popen(
        launch.argv,
        cwd=launch.cwd or None,
        env=launch.env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **popen_kwargs_show_window(),
    )


def is_wia_busy_message(text: str) -> bool:
    t = (text or "").lower()
    return any(p in t for p in WIA_BUSY_PATTERNS)


def detect_wia_holders() -> List[str]:
    """Laufende Prozesse, die WIA typischerweise belegen."""
    found: List[str] = []
    system = platform.system()
    try:
        if system == "Windows":
            proc = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=8,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
            )
            blob = (proc.stdout or "") + "\n" + (proc.stderr or "")
        else:
            proc = subprocess.run(
                ["ps", "-eo", "comm,args"],
                capture_output=True,
                text=True,
                timeout=8,
            )
            blob = proc.stdout or ""
    except Exception:
        return found
    low = blob.lower()
    labels = {
        "scantuxio": "ScanTuxio",
        "wfs.exe": "Windows Fax und Scan",
        "wiaacmgr": "Windows Bildübernahme (WIA)",
        "instantlensdoc": "InstantLens Doc (vorheriger Scan)",
        "naps2": "NAPS2",
    }
    for needle, label in labels.items():
        if needle in low and label not in found:
            found.append(label)
    return found


def wia_busy_user_hint_de(detail: str = "") -> str:
    holders = detect_wia_holders()
    body = "Das WIA-Gerät ist ausgelastet.\n\n" + WIA_HOLDER_HINT_DE
    if holders:
        body += "\n\nErkannt: " + ", ".join(holders)
    if detail:
        body += f"\n\nDetail: {detail.strip()[:240]}"
    return body


def parse_paths_from_text(text: str) -> List[Path]:
    """Pfadzeilen aus stdout/Übergabedatei."""
    out: List[Path] = []
    for line in (text or "").splitlines():
        s = line.strip().strip('"')
        if not s or s.startswith("#"):
            continue
        p = Path(s)
        try:
            if p.is_file() and p.suffix.lower() in SCAN_IMPORT_SUFFIXES:
                out.append(p)
        except OSError:
            continue
    return out


def read_handoff_manifest(handshake: Path) -> List[Path]:
    for name in ("ild-handoff.txt", "handoff.txt", "last-scan.txt"):
        mf = handshake / name
        if mf.is_file():
            try:
                return parse_paths_from_text(mf.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
    return []
