"""Scan-Übertragung: Gerät → Bilddatei(en) → InstantLens Doc — 2.6.54.

Portiert den ScanTuxio-Win-Ablauf (``scantuxio/ui/main_window.py::_do_scan`` →
``scanner.scan_single_page_dispatch``): **ein** Scan ist **ein** Subprozess
(``NAPS2.Console.exe -o <datei> --driver … --device …`` bzw. ``scanimage``) oder ein
eSCL-HTTP-Job mit **explizitem Ausgabepfad**; danach wird auf das Prozessende
**und** auf die Datei gewartet, das Ergebnis im Ausgabeordner gesucht (auch
NAPS2-Nummerierung ``name1.png``), geprüft (PIL) und zurückgegeben.

Warum die alte Übertragung scheiterte (2.6.46–2.6.53):

* WIA-Pfad: ``$dev.Items(1)`` ist in PowerShell kein gültiger Aufruf (``Items`` ist
  eine einfache Eigenschaft) → COM-Fehler nach ``Connect()`` (Lampe geht an, kein
  Bild); Ergebnis nur über ``Write-Output`` + UTF-8-Decode → Pfade mit Umlauten
  (``C:\\Users\\Müller\\…``) wurden nicht wiedergefunden; keine ``-STA``-Apartment,
  kein Log, kein Datei-Fallback.
* ScanTuxio-UI-Übergabe: ScanTuxio speichert nach ``~/Scans/{Jahr}/{Monat}/{Tag}/…``,
  die Überwachung las nur die oberste Ebene.
* NAPS2-Pfad: kein Log, kein Retry bei älterer NAPS2-Kommandozeile, keine
  Wartezeit auf die Datei, stdout/stderr verworfen.

Alle Backends schreiben nach ``%LOCALAPPDATA%\\InstantLensDoc\\scan.log``
(POSIX: Konfig-Ordner ``logs/scan.log``).
"""

from __future__ import annotations

import datetime as _dt
import os
import platform
import re
import shlex
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
RESULT_SUFFIXES = IMAGE_SUFFIXES | {".pdf"}

# Backend-Schlüssel (persistiert in app_settings.scan_backend)
BACKEND_AUTO = "auto"
BACKEND_SCANTUXIO = "scantuxio"
BACKEND_WIA = "wia"
BACKEND_NAPS2 = "naps2"
BACKEND_ESCL = "escl"
BACKEND_TWAIN = "twain"
BACKEND_EXTERNAL = "external"

BACKEND_ORDER: Tuple[str, ...] = (
    BACKEND_AUTO,
    BACKEND_SCANTUXIO,
    BACKEND_WIA,
    BACKEND_NAPS2,
    BACKEND_ESCL,
    BACKEND_TWAIN,
    BACKEND_EXTERNAL,
)

BACKEND_LABELS_DE: Dict[str, str] = {
    BACKEND_AUTO: "Automatisch (ScanTuxio-Ablauf)",
    BACKEND_SCANTUXIO: "ScanTuxio Win (Oberfläche)",
    BACKEND_WIA: "WIA (direkt, Windows)",
    BACKEND_NAPS2: "NAPS2 (Konsole)",
    BACKEND_ESCL: "eSCL / AirScan (Netzwerk)",
    BACKEND_TWAIN: "TWAIN (über NAPS2, falls verfügbar)",
    BACKEND_EXTERNAL: "Externes Programm (Befehlszeile)",
}

COLOR_MODES: Tuple[str, ...] = ("Color", "Gray", "Lineart")
COLOR_LABELS_DE: Dict[str, str] = {
    "Color": "Farbe",
    "Gray": "Graustufen",
    "Lineart": "Schwarzweiß",
}
SOURCES: Tuple[str, ...] = ("Flatbed", "ADF", "ADF Duplex")
SOURCE_LABELS_DE: Dict[str, str] = {
    "Flatbed": "Flachbett",
    "ADF": "Einzug (ADF)",
    "ADF Duplex": "Einzug beidseitig (Duplex)",
}
DPI_CHOICES: Tuple[int, ...] = (100, 150, 200, 300, 400, 600)

EXTERNAL_PLACEHOLDERS: Tuple[str, ...] = (
    "{output}",
    "{outdir}",
    "{dpi}",
    "{device}",
    "{color}",
    "{source}",
)

WIA_DIALOG_DEVICE_ID = "wia:dialog"
WIA_DIALOG_LABEL_DE = "Windows-Scannerauswahl (WIA-Dialog)"

DEFAULT_TIMEOUT_S = 240.0
FILE_WAIT_S = 6.0
EXTERNAL_FILE_WAIT_S = 12.0
LOG_MAX_BYTES = 2 * 1024 * 1024

try:
    from instantlensdoc.core.device_io import WIA_HANG_TIMEOUT_S
except Exception:  # pragma: no cover
    WIA_HANG_TIMEOUT_S = 12.0

_WIA_FORMAT_BMP = "{B96B3CAB-0728-11D3-9D7B-0000F81EF32E}"

_BUSY_PATTERNS = (
    "ausgelastet",
    "in use",
    "busy",
    "0x80210006",
    "wia_error_busy",
    "device busy",
    "wird verwendet",
    "bereits geöffnet",
    "already in use",
    "gerät ist beschäftigt",
    "the device is busy",
)


def is_windows() -> bool:
    return platform.system() == "Windows"


# --------------------------------------------------------------------------- Log


def scan_log_path() -> Path:
    """``%LOCALAPPDATA%\\InstantLensDoc\\scan.log`` bzw. ``<config>/logs/scan.log``."""
    try:
        if os.name == "nt":
            base = os.environ.get("LOCALAPPDATA") or str(
                Path.home() / "AppData" / "Local"
            )
            d = Path(base) / "InstantLensDoc"
        else:
            from instantlensdoc.config import config_dir

            d = config_dir() / "logs"
        d.mkdir(parents=True, exist_ok=True)
        return d / "scan.log"
    except Exception:
        return Path(tempfile.gettempdir()) / "InstantLensDoc-scan.log"


def scan_log(message: str) -> None:
    """Zeile(n) mit Zeitstempel anhängen; Rotation bei > 2 MB. Wirft nie."""
    try:
        path = scan_log_path()
        try:
            if path.is_file() and path.stat().st_size > LOG_MAX_BYTES:
                bak = path.with_suffix(".log.1")
                if bak.exists():
                    bak.unlink()
                path.rename(bak)
        except OSError:
            pass
        stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = str(message or "").rstrip()
        lines = text.splitlines() or [""]
        with open(path, "a", encoding="utf-8", errors="replace") as fh:
            fh.write(f"[{stamp}] {lines[0]}\n")
            for extra in lines[1:]:
                fh.write(f"    {extra}\n")
    except Exception:
        pass


def _tail(text: str, limit: int = 1200) -> str:
    t = (text or "").strip()
    if len(t) <= limit:
        return t
    return "…" + t[-limit:]


# ------------------------------------------------------------------ Datenmodell


@dataclass
class ScanJob:
    """Ein Scanauftrag (eine Seite bzw. ein ADF-Stapel)."""

    device_id: str = ""
    device_name: str = ""
    device_backend: str = ""  # Backend-Name aus devices.DeviceInfo (WIA, ScanTuxio/NAPS2/WIA, …)
    backend: str = BACKEND_AUTO  # gewünschtes Backend (Einstellungen)
    dpi: int = 300
    color_mode: str = "Color"
    source: str = "Flatbed"
    out_dir: Optional[Path] = None
    timeout: float = DEFAULT_TIMEOUT_S
    fallback_devices: List[Tuple[str, str, str]] = field(default_factory=list)
    external_cmd: str = ""
    external_outdir: str = ""
    naps2_path: str = ""

    @property
    def is_adf(self) -> bool:
        return str(self.source or "").startswith("ADF")

    def describe_de(self) -> str:
        parts = [self.device_name or self.device_id or "Standardgerät"]
        parts.append(f"{int(self.dpi)} dpi")
        parts.append(COLOR_LABELS_DE.get(self.color_mode, self.color_mode))
        parts.append(SOURCE_LABELS_DE.get(self.source, self.source))
        parts.append(BACKEND_LABELS_DE.get(self.backend, self.backend))
        return " · ".join(parts)


@dataclass
class ScanAttempt:
    backend: str
    command: str = ""
    returncode: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    error: str = ""
    duration_s: float = 0.0
    paths: List[Path] = field(default_factory=list)
    cancelled: bool = False
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return bool(self.paths)

    @property
    def busy(self) -> bool:
        blob = f"{self.error}\n{self.stderr}\n{self.stdout}".lower()
        return any(p in blob for p in _BUSY_PATTERNS)


@dataclass
class ScanResult:
    paths: List[Path] = field(default_factory=list)
    backend: str = ""
    error: str = ""
    cancelled: bool = False
    attempts: List[ScanAttempt] = field(default_factory=list)
    out_dir: Optional[Path] = None

    @property
    def ok(self) -> bool:
        return bool(self.paths)

    @property
    def busy(self) -> bool:
        return any(a.busy for a in self.attempts)

    def detail_text_de(self) -> str:
        """Mehrzeiliger DE-Fehlertext mit Befehl, Exit-Code, stdout/stderr, Log."""
        if self.ok:
            names = ", ".join(p.name for p in self.paths[:5])
            more = f" … (+{len(self.paths) - 5})" if len(self.paths) > 5 else ""
            return f"{len(self.paths)} Seite(n) über {self.backend}: {names}{more}"
        if self.cancelled:
            return "Scan abgebrochen."
        lines: List[str] = [self.error or "Kein Bild vom Scanner erhalten."]
        for a in self.attempts:
            lines.append("")
            lines.append(f"Versuch {BACKEND_LABELS_DE.get(a.backend, a.backend)}:")
            if a.command:
                lines.append(f"  Befehl: {a.command}")
            if a.returncode is not None:
                lines.append(f"  Exit-Code: {a.returncode}")
            if a.timed_out:
                lines.append("  Zeitüberschreitung")
            if a.error:
                lines.append(f"  Fehler: {_tail(a.error, 400)}")
            if a.stderr.strip():
                lines.append(f"  stderr: {_tail(a.stderr, 600)}")
            if a.stdout.strip():
                lines.append(f"  stdout: {_tail(a.stdout, 600)}")
        lines.append("")
        lines.append(f"Log: {scan_log_path()}")
        return "\n".join(lines)


@dataclass
class BackendStatus:
    key: str
    label: str
    available: bool
    detail: str = ""
    path: str = ""

    def status_text_de(self) -> str:
        mark = "✓" if self.available else "✗"
        return f"{mark} {self.detail}" if self.detail else mark


# ------------------------------------------------------------------ Hilfsfunktionen


def decode_output(raw: Any) -> str:
    """Bytes aus Subprozessen robust dekodieren (UTF-8 → cp1252 → latin-1)."""
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw.lstrip("\ufeff")
    data = bytes(raw)
    for enc in ("utf-8", "cp1252"):
        try:
            return data.decode(enc).lstrip("\ufeff")
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace").lstrip("\ufeff")


def _hidden_kwargs() -> dict:
    if is_windows():
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)}
    return {}


def format_command(cmd: Sequence[str]) -> str:
    """Befehl als eine Zeile mit korrekt gequoteten Argumenten (für Log/Fehlertext)."""
    if is_windows():
        return subprocess.list2cmdline([str(c) for c in cmd])
    return " ".join(shlex.quote(str(c)) for c in cmd)


def run_process(
    cmd: Sequence[str],
    *,
    timeout: float,
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
    hide_window: bool = True,
) -> Tuple[Optional[int], str, str, bool]:
    """Prozess starten, auf Ende warten; (returncode, stdout, stderr, timed_out)."""
    kwargs: dict = {}
    if hide_window:
        kwargs.update(_hidden_kwargs())
    proc = subprocess.Popen(
        [str(c) for c in cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        cwd=cwd or None,
        env=env,
        **kwargs,
    )
    timed_out = False
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            proc.kill()
        except Exception:
            pass
        try:
            out, err = proc.communicate(timeout=5)
        except Exception:
            out, err = b"", b""
    return proc.returncode, decode_output(out), decode_output(err), timed_out


def snapshot_dir(
    root: Path, *, recursive: bool = False, max_depth: int = 4
) -> Dict[str, Tuple[int, int]]:
    """Pfad → (mtime_ns, size) für Bild-/PDF-Dateien unter ``root``."""
    snap: Dict[str, Tuple[int, int]] = {}
    try:
        root = Path(root)
        if not root.is_dir():
            return snap
    except OSError:
        return snap
    base_depth = len(root.parts)
    stack = [root]
    while stack:
        d = stack.pop()
        try:
            entries = list(d.iterdir())
        except OSError:
            continue
        for p in entries:
            try:
                if p.is_dir():
                    if recursive and len(p.parts) - base_depth < max_depth:
                        stack.append(p)
                    continue
                if p.suffix.lower() not in RESULT_SUFFIXES:
                    continue
                st = p.stat()
                snap[str(p)] = (int(st.st_mtime_ns), int(st.st_size))
            except OSError:
                continue
    return snap


def new_files_since(
    root: Path,
    before: Dict[str, Tuple[int, int]],
    *,
    recursive: bool = False,
    min_size: int = 32,
) -> List[Path]:
    after = snapshot_dir(root, recursive=recursive)
    out: List[Path] = []
    for key, (mtime_ns, size) in after.items():
        if size < min_size:
            continue
        old = before.get(key)
        if old is None or mtime_ns > old[0] or size != old[1]:
            out.append(Path(key))
    out.sort(key=lambda p: (_safe_mtime(p), p.name))
    return out


def _safe_mtime(p: Path) -> int:
    try:
        return p.stat().st_mtime_ns
    except OSError:
        return 0


def _candidate_files(
    out_dir: Path,
    before: Dict[str, Tuple[int, int]],
    *,
    expected: Sequence[Path],
    stem: str,
    extra_dirs: Sequence[Path] = (),
    min_size: int = 32,
) -> List[Path]:
    found: List[Path] = []
    for p in expected:
        try:
            if p.is_file() and p.stat().st_size >= min_size:
                found.append(p)
        except OSError:
            continue
    if stem:
        try:
            for p in sorted(out_dir.glob(f"{stem}*")):
                if p.is_file() and p.suffix.lower() in RESULT_SUFFIXES and p.stat().st_size >= min_size:
                    found.append(p)
        except OSError:
            pass
    found.extend(new_files_since(out_dir, before, min_size=min_size))
    for d in extra_dirs:
        found.extend(new_files_since(d, before, recursive=True, min_size=min_size))
    seen: set = set()
    uniq: List[Path] = []
    for p in found:
        try:
            key = str(p.resolve())
        except OSError:
            key = str(p)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(p)
    return uniq


def wait_for_output(
    out_dir: Path,
    before: Dict[str, Tuple[int, int]],
    *,
    expected: Sequence[Path] = (),
    stem: str = "",
    extra_dirs: Sequence[Path] = (),
    timeout: float = FILE_WAIT_S,
    poll: float = 0.2,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> List[Path]:
    """Auf Ergebnisdateien warten: Datei vorhanden **und** Größe stabil."""
    deadline = clock() + max(0.0, float(timeout))
    last_sizes: Dict[str, int] = {}
    while True:
        cands = _candidate_files(
            out_dir, before, expected=expected, stem=stem, extra_dirs=extra_dirs
        )
        if cands:
            sizes = {}
            for p in cands:
                try:
                    sizes[str(p)] = p.stat().st_size
                except OSError:
                    sizes[str(p)] = -1
            if sizes == last_sizes:
                return cands
            last_sizes = sizes
        if clock() >= deadline:
            return cands
        sleep(poll)


def validate_and_normalize(paths: Iterable[Path], *, out_dir: Optional[Path] = None) -> List[Path]:
    """Bilder mit PIL prüfen; BMP → PNG; PDFs unverändert; defekte Dateien überspringen."""
    out: List[Path] = []
    for p in paths:
        p = Path(p)
        suf = p.suffix.lower()
        if suf == ".pdf":
            out.append(p)
            continue
        if suf not in IMAGE_SUFFIXES:
            continue
        try:
            from PIL import Image

            with Image.open(p) as im:
                im.load()
                if suf == ".bmp":
                    target_dir = Path(out_dir) if out_dir else p.parent
                    png = target_dir / (p.stem + ".png")
                    n = 1
                    while png.exists():
                        n += 1
                        png = target_dir / f"{p.stem}_{n}.png"
                    im.convert("RGB").save(png, "PNG")
                    try:
                        p.unlink()
                    except OSError:
                        pass
                    out.append(png)
                    continue
        except Exception as e:
            scan_log(f"Ergebnisdatei nicht lesbar, übersprungen: {p} ({e})")
            continue
        out.append(p)
    return out


def is_busy_text(text: str) -> bool:
    t = (text or "").lower()
    return any(p in t for p in _BUSY_PATTERNS)


# ------------------------------------------------------------------ Tool-Suche


def _settings_scan() -> dict:
    try:
        from instantlensdoc.core.app_settings import get_scan_settings

        return get_scan_settings()
    except Exception:
        return {}


def naps2_console_path(configured: str = "") -> Optional[str]:
    """NAPS2.Console.exe: Einstellungen → ScanTuxio-Suche → typische Ordner."""
    cfg = (configured or "").strip() or str(_settings_scan().get("scan_naps2_path") or "").strip()
    if cfg:
        p = Path(cfg)
        try:
            if p.is_file():
                return str(p)
            if p.is_dir():
                for name in ("NAPS2.Console.exe", "NAPS2.Console", "naps2.console"):
                    cand = p / name
                    if cand.is_file():
                        return str(cand)
        except OSError:
            pass
    try:
        from instantlensdoc.core.scantuxio import scanner_naps2 as st_naps2

        found = st_naps2._naps2_console_path()
        if found:
            return found
    except Exception:
        pass
    names = ["NAPS2.Console.exe", "NAPS2.Console", "naps2.console", "naps2-console"]
    for n in names:
        w = shutil.which(n)
        if w:
            return w
    extra: List[Path] = []
    for env_key in ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
        base = os.environ.get(env_key)
        if not base:
            continue
        extra.append(Path(base) / "NAPS2")
        extra.append(Path(base) / "Programs" / "NAPS2")
    for d in extra:
        try:
            if d.is_dir():
                for n in names[:2]:
                    cand = d / n
                    if cand.is_file():
                        return str(cand)
        except OSError:
            continue
    return None


def powershell_exe() -> Optional[str]:
    """Windows PowerShell (5.1, STA, volle COM-Unterstützung) bevorzugt, sonst pwsh."""
    if not is_windows():
        return None
    for name in ("powershell.exe", "powershell", "pwsh.exe", "pwsh"):
        w = shutil.which(name)
        if w:
            return w
    sysroot = os.environ.get("SystemRoot") or r"C:\Windows"
    cand = Path(sysroot) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    try:
        if cand.is_file():
            return str(cand)
    except OSError:
        pass
    return None


def backend_availability(settings: Optional[dict] = None) -> List[BackendStatus]:
    """Verfügbarkeit jedes Backends (gefunden/nicht gefunden + Pfad/Hinweis)."""
    cfg = settings if settings is not None else _settings_scan()
    out: List[BackendStatus] = []
    naps2 = naps2_console_path(str(cfg.get("scan_naps2_path") or ""))
    ps = powershell_exe()

    out.append(
        BackendStatus(
            BACKEND_AUTO,
            BACKEND_LABELS_DE[BACKEND_AUTO],
            True,
            "Lokal: WIA → NAPS2 → Dialog. Netzwerk: eSCL/AirScan zuerst (kein WIA-Connect im Sleep).",
        )
    )
    st_path = ""
    st_detail = "nicht gefunden"
    try:
        from instantlensdoc.core.scantuxio_ui import find_scantuxio_install

        inst = find_scantuxio_install()
        if inst is not None:
            st_path = inst.exe or inst.main_py
            st_detail = f"gefunden: {st_path}"
    except Exception as e:
        st_detail = f"nicht prüfbar: {e}"
    out.append(
        BackendStatus(
            BACKEND_SCANTUXIO,
            BACKEND_LABELS_DE[BACKEND_SCANTUXIO],
            bool(st_path),
            st_detail,
            st_path,
        )
    )
    if is_windows():
        out.append(
            BackendStatus(
                BACKEND_WIA,
                BACKEND_LABELS_DE[BACKEND_WIA],
                bool(ps),
                f"gefunden: {ps} (WIA-COM)" if ps else "PowerShell nicht gefunden",
                ps or "",
            )
        )
    else:
        out.append(
            BackendStatus(
                BACKEND_WIA, BACKEND_LABELS_DE[BACKEND_WIA], False, "nur unter Windows"
            )
        )
    out.append(
        BackendStatus(
            BACKEND_NAPS2,
            BACKEND_LABELS_DE[BACKEND_NAPS2],
            bool(naps2),
            f"gefunden: {naps2}" if naps2 else "NAPS2.Console.exe nicht gefunden (Pfad wählen…)",
            naps2 or "",
        )
    )
    out.append(
        BackendStatus(
            BACKEND_ESCL,
            BACKEND_LABELS_DE[BACKEND_ESCL],
            True,
            "integriert (HTTP/eSCL, Netzwerk-Scanner per mDNS oder manuelle Adresse)",
        )
    )
    out.append(
        BackendStatus(
            BACKEND_TWAIN,
            BACKEND_LABELS_DE[BACKEND_TWAIN],
            bool(naps2) and is_windows(),
            f"über NAPS2 --driver twain ({naps2})" if (naps2 and is_windows()) else "nicht verfügbar (NAPS2 fehlt)",
            naps2 or "",
        )
    )
    cmd = str(cfg.get("scan_external_cmd") or "").strip()
    out.append(
        BackendStatus(
            BACKEND_EXTERNAL,
            BACKEND_LABELS_DE[BACKEND_EXTERNAL],
            bool(cmd),
            f"Befehl: {cmd[:80]}" if cmd else "Befehlszeile nicht konfiguriert",
        )
    )
    return out


# ------------------------------------------------------------------ Geräte-IDs


def classify_device_id(device_id: str, device_backend: str = "") -> str:
    """Grobe Klasse einer DeviceInfo-ID: naps2 | escl | wia | twain | pnp | sane | dialog | none."""
    did = (device_id or "").strip()
    low = did.lower()
    be = (device_backend or "").lower()
    if not did:
        return "none"
    if low == WIA_DIALOG_DEVICE_ID:
        return "dialog"
    if low.startswith("naps2:"):
        return "naps2"
    if low.startswith(("native-escl:", "escl:", "mdns:", "airscan:")):
        return "escl"
    if low.startswith(("twain:", "twain-ds:")):
        return "twain"
    if low.startswith("{") and "}" in low:
        return "wia"
    if "wia" in be:
        return "wia"
    if "twain" in be:
        return "twain"
    if "pnp" in be or "cim" in be or low.startswith(("usb\\", "swd\\", "root\\", "cim:")):
        return "pnp"
    if "escl" in be or "mdns" in be:
        return "escl"
    if "sane" in be or ":" in did or "/" in did:
        return "sane"
    return "unknown"


def parse_naps2_id(device_id: str) -> Tuple[str, str]:
    rest = (device_id or "")[len("naps2:"):]
    driver, _, name = rest.partition(":")
    return (driver or "wia").lower(), name


def escl_device_id(device_id: str) -> str:
    """``mdns:host:port`` → ``native-escl:http://host:port``; andere unverändert."""
    did = (device_id or "").strip()
    if did.lower().startswith("mdns:"):
        rest = did[5:]
        host, _, port = rest.rpartition(":")
        if host and port:
            return f"native-escl:http://{host}:{port}"
    if did.lower().startswith("escl:") and is_windows():
        # SANE-Schreibweise unter Windows → nativer Client
        return "native-" + did
    return did


def clean_device_name(name: str) -> str:
    """Anzeigename ohne Backend-Suffixe ``(WIA)``/``(TWAIN)``/``(Netzwerk, eSCL)``."""
    n = re.sub(r"\s*\((WIA|TWAIN|Netzwerk, eSCL|lokal|Netzwerk)\)\s*$", "", name or "", flags=re.I)
    return n.strip()


# ------------------------------------------------------------------ Backends


def build_naps2_command(
    exe: str,
    out_path: Path,
    *,
    driver: str,
    device: str,
    dpi: int,
    color_mode: str,
    source: str,
    adhoc: bool = True,
    verbose: bool = True,
) -> List[str]:
    """NAPS2.Console-Aufruf wie ScanTuxio (``-o … --driver … --device …``) + Optionen."""
    cmd: List[str] = [exe, "-o", str(out_path)]
    if verbose:
        cmd.append("--verbose")
    if adhoc:
        cmd += ["--driver", (driver or "wia").lower()]
        if device:
            cmd += ["--device", device]
        cmd += ["--dpi", str(int(dpi))]
        cmd += ["--source", {"Flatbed": "glass", "ADF": "feeder", "ADF Duplex": "duplex"}.get(source, "glass")]
        cmd += ["--bitdepth", {"Color": "color", "Gray": "gray", "Lineart": "bw"}.get(color_mode, "color")]
    return cmd


_CLI_OPTION_ERROR = re.compile(
    r"(?i)(unknown option|unrecognized|is not a valid option|option '[^']*' is unknown|"
    r"ERROR\(S\)|Required option|--help|Verb .* is not recognized|not recognized)"
)


def looks_like_cli_option_error(text: str) -> bool:
    return bool(_CLI_OPTION_ERROR.search(text or ""))


def naps2_error_hint_de(text: str) -> str:
    low = (text or "").lower()
    if is_busy_text(low):
        return "Scanner ausgelastet — ScanTuxio / Windows-Fax und -Scan / NAPS2-Fenster schließen."
    if re.search(r"no (scanning )?device|device not found|could not find|kein ger", low):
        return "NAPS2 findet das Gerät nicht — Gerätename prüfen (NAPS2.Console --listdevices --driver wia)."
    if "no profile" in low or "profile" in low and "not found" in low:
        return "Kein NAPS2-Profil — Gerät direkt wählen (Treiber + Name) oder in NAPS2 ein Profil anlegen."
    if re.search(r"feeder (is )?empty|no pages|keine seiten|out of paper", low):
        return "Einzug leer — Papier einlegen oder Quelle „Flachbett“ wählen."
    return ""


def _run_naps2(
    job: ScanJob,
    out_dir: Path,
    *,
    driver: str,
    device_name: str,
    exe: Optional[str] = None,
) -> ScanAttempt:
    attempt = ScanAttempt(backend=BACKEND_NAPS2 if driver != "twain" else BACKEND_TWAIN)
    exe = exe or naps2_console_path(job.naps2_path)
    if not exe:
        attempt.error = (
            "NAPS2.Console.exe nicht gefunden — NAPS2 installieren oder Pfad unter "
            "Einstellungen → Scannen → „Pfad wählen…“ setzen."
        )
        scan_log(f"NAPS2: {attempt.error}")
        return attempt
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = f"scan_naps2_{stamp}"
    out_path = out_dir / f"{stem}.png"
    before = snapshot_dir(out_dir)

    def _one(adhoc: bool) -> Tuple[List[str], Optional[int], str, str, bool]:
        cmd = build_naps2_command(
            exe,
            out_path,
            driver=driver,
            device=device_name,
            dpi=job.dpi,
            color_mode=job.color_mode,
            source=job.source,
            adhoc=adhoc,
        )
        scan_log(f"NAPS2 start: {format_command(cmd)}")
        rc, out, err, to = run_process(cmd, timeout=job.timeout, cwd=str(out_dir))
        scan_log(
            f"NAPS2 ende: exit={rc} timeout={to}\n"
            f"stdout: {_tail(out, 2000)}\nstderr: {_tail(err, 2000)}"
        )
        return cmd, rc, out, err, to

    t0 = time.monotonic()
    cmd, rc, out, err, to = _one(True)
    attempt.command = format_command(cmd)
    attempt.returncode, attempt.stdout, attempt.stderr, attempt.timed_out = rc, out, err, to
    paths = wait_for_output(out_dir, before, expected=[out_path], stem=stem)
    if not paths and not to and rc not in (0, None) and looks_like_cli_option_error(out + "\n" + err):
        scan_log("NAPS2: Kommandozeilen-Option unbekannt → zweiter Versuch mit Standardprofil")
        cmd2, rc2, out2, err2, to2 = _one(False)
        attempt.command += "\n  → Retry: " + format_command(cmd2)
        attempt.returncode = rc2
        attempt.stdout = (out + "\n--- Retry ---\n" + out2).strip()
        attempt.stderr = (err + "\n--- Retry ---\n" + err2).strip()
        attempt.timed_out = to2
        paths = wait_for_output(out_dir, before, expected=[out_path], stem=stem)
    attempt.duration_s = time.monotonic() - t0
    attempt.paths = validate_and_normalize(paths, out_dir=out_dir)
    if not attempt.paths:
        if attempt.timed_out:
            attempt.error = f"Zeitüberschreitung ({int(job.timeout)} s) beim NAPS2-Scan."
        else:
            hint = naps2_error_hint_de(attempt.stderr + "\n" + attempt.stdout)
            attempt.error = (
                "NAPS2 hat keine Bilddatei geschrieben"
                + (f" (Exit-Code {attempt.returncode})" if attempt.returncode not in (0, None) else "")
                + "."
                + (f" {hint}" if hint else "")
            )
    scan_log(f"NAPS2 Ergebnis: {[str(p) for p in attempt.paths]} fehler={attempt.error!r}")
    return attempt


WIA_SCRIPT = r"""
param(
  [string]$OutDir,
  [string]$DeviceId = '',
  [string]$DeviceName = '',
  [int]$Dpi = 300,
  [string]$ColorMode = 'Color',
  [string]$Source = 'Flatbed',
  [string]$ResultFile = '',
  [switch]$UseDialog
)
$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$utf8 = New-Object System.Text.UTF8Encoding($false)
function Write-Result([string]$p) {
  if ($ResultFile) { [System.IO.File]::AppendAllText($ResultFile, $p + "`r`n", $utf8) }
  Write-Output $p
}
function Write-Err([string]$m) { [Console]::Error.WriteLine($m) }
function Save-Image($img, [string]$path) {
  if ($null -eq $img) { return $false }
  try { $img.SaveFile($path); return $true } catch { }
  try { $img.ImageFile.SaveFile($path); return $true } catch { }
  try { [System.IO.File]::WriteAllBytes($path, [byte[]]$img.BinaryData); return $true } catch { }
  return $false
}
function Image-Ext($img) {
  $ext = '.bmp'
  try {
    $fid = [string]$img.FormatID
    if ($fid -eq '{B96B3CAE-0728-11D3-9D7B-0000F81EF32E}') { $ext = '.jpg' }
    elseif ($fid -eq '{B96B3CAF-0728-11D3-9D7B-0000F81EF32E}') { $ext = '.png' }
    elseif ($fid -eq '{B96B3CB1-0728-11D3-9D7B-0000F81EF32E}') { $ext = '.tif' }
  } catch { }
  return $ext
}
function Next-Path([string]$base, [string]$ext) {
  $p = $base + $ext
  $n = 1
  while (Test-Path -LiteralPath $p) { $n++; $p = $base + '_' + $n + $ext }
  return $p
}
$fmtBmp = '{B96B3CAB-0728-11D3-9D7B-0000F81EF32E}'
$saved = 0
try {
  if (-not (Test-Path -LiteralPath $OutDir)) { New-Item -ItemType Directory -Path $OutDir -Force | Out-Null }
  $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
  $base = Join-Path $OutDir ('scan_wia_' + $stamp)
  $cd = New-Object -ComObject WIA.CommonDialog
  $item = $null
  if (-not $UseDialog -and ($DeviceId -or $DeviceName)) {
    $dm = New-Object -ComObject WIA.DeviceManager
    $info = $null
    foreach ($d in $dm.DeviceInfos) {
      $did = ''
      $dname = ''
      try { $did = [string]$d.DeviceID } catch { }
      try { $dname = [string]$d.Properties.Item('Name').Value } catch { }
      if ($DeviceId -and $did -eq $DeviceId) { $info = $d; break }
      if ($DeviceName -and $dname -and ($dname -eq $DeviceName -or $dname -like ('*' + $DeviceName + '*') -or $DeviceName -like ('*' + $dname + '*'))) { $info = $d; break }
    }
    if ($null -eq $info) {
      Write-Err ("WIA: Gerät nicht gefunden (" + $DeviceId + " / " + $DeviceName + ") - Windows-Scannerdialog wird verwendet.")
    } else {
      $dev = $info.Connect()
      try {
        if ($Source -ne 'Flatbed') {
          $sel = 1
          if ($Source -like '*Duplex*') { $sel = $sel -bor 4 }
          foreach ($p in $dev.Properties) { if ([int]$p.PropertyID -eq 3088) { $p.Value = $sel; break } }
        }
      } catch { Write-Err ('WIA: Papierquelle nicht setzbar: ' + $_.Exception.Message) }
      try { $item = $dev.Items.Item(1) } catch { foreach ($i in $dev.Items) { $item = $i; break } }
      if ($null -eq $item) { throw 'WIA: Scanner-Item nicht gefunden (Gerät ohne Items).' }
      try {
        $intent = 1
        if ($ColorMode -eq 'Gray') { $intent = 2 } elseif ($ColorMode -eq 'Lineart') { $intent = 4 }
        foreach ($p in $item.Properties) {
          $propId = [int]$p.PropertyID
          try {
            if ($propId -eq 6146) { $p.Value = $intent }
            elseif ($propId -eq 6147 -or $propId -eq 6148) { $p.Value = $Dpi }
          } catch { Write-Err ('WIA: Eigenschaft ' + $propId + ' nicht setzbar: ' + $_.Exception.Message) }
        }
      } catch { Write-Err ('WIA: DPI/Farbmodus nicht setzbar: ' + $_.Exception.Message) }
      $maxPages = 1
      if ($Source -ne 'Flatbed') { $maxPages = 200 }
      for ($k = 0; $k -lt $maxPages; $k++) {
        $img = $null
        try {
          $img = $item.Transfer($fmtBmp)
        } catch {
          $m = $_.Exception.Message
          $hr = 0
          try { $hr = $_.Exception.HResult } catch { }
          if ($k -gt 0 -and ($hr -eq -2145320957 -or $m -match 'empty|leer|paper|Papier')) { break }
          throw
        }
        if ($null -eq $img) { break }
        $path = Next-Path $base (Image-Ext $img)
        if (-not (Save-Image $img $path)) { throw 'WIA: Bild konnte nicht gespeichert werden (unerwarteter Rückgabetyp).' }
        Write-Result $path
        $saved++
      }
    }
  }
  if ($saved -eq 0) {
    $img = $cd.ShowAcquireImage()
    if ($null -eq $img) { Write-Output 'CANCELLED'; exit 3 }
    $path = Next-Path $base (Image-Ext $img)
    if (-not (Save-Image $img $path)) { throw 'WIA: Bild konnte nicht gespeichert werden (Dialog).' }
    Write-Result $path
    $saved++
  }
  exit 0
} catch {
  $msg = $_.Exception.Message
  try { $msg = $msg + (' [0x{0:X8}]' -f $_.Exception.HResult) } catch { }
  Write-Err ('WIA-Fehler: ' + $msg)
  if ($saved -gt 0) { exit 0 }
  exit 1
}
"""


def write_wia_script(out_dir: Path) -> Path:
    """PowerShell-Skript als UTF-8 mit BOM ablegen (Windows PowerShell 5.1 liest sonst ANSI)."""
    path = Path(out_dir) / "ild_wia_scan.ps1"
    path.write_text(WIA_SCRIPT.lstrip("\n"), encoding="utf-8-sig")
    return path


def build_wia_command(
    ps: str,
    script: Path,
    *,
    out_dir: Path,
    result_file: Path,
    device_id: str,
    device_name: str,
    dpi: int,
    color_mode: str,
    source: str,
    use_dialog: bool,
) -> List[str]:
    cmd = [
        ps,
        "-NoProfile",
        "-NoLogo",
        "-STA",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-OutDir",
        str(out_dir),
        "-DeviceId",
        device_id or "",
        "-DeviceName",
        device_name or "",
        "-Dpi",
        str(int(dpi)),
        "-ColorMode",
        color_mode or "Color",
        "-Source",
        source or "Flatbed",
        "-ResultFile",
        str(result_file),
    ]
    if use_dialog:
        cmd.append("-UseDialog")
    return cmd


def read_result_file(result_file: Path) -> List[Path]:
    out: List[Path] = []
    try:
        if not result_file.is_file():
            return out
        for line in result_file.read_text(encoding="utf-8", errors="replace").splitlines():
            s = line.strip().strip('"').lstrip("\ufeff")
            if not s or s == "CANCELLED":
                continue
            p = Path(s)
            try:
                if p.is_file():
                    out.append(p)
            except OSError:
                continue
    except OSError:
        pass
    return out


def _run_wia(
    job: ScanJob,
    out_dir: Path,
    *,
    device_id: str,
    device_name: str,
    use_dialog: bool,
) -> ScanAttempt:
    attempt = ScanAttempt(backend=BACKEND_WIA)
    ps = powershell_exe()
    if not ps:
        attempt.error = "PowerShell nicht gefunden — WIA-Scan nur unter Windows möglich."
        scan_log(f"WIA: {attempt.error}")
        return attempt
    script = write_wia_script(out_dir)
    result_file = out_dir / "wia_result.txt"
    try:
        result_file.unlink()
    except OSError:
        pass
    before = snapshot_dir(out_dir)
    cmd = build_wia_command(
        ps,
        script,
        out_dir=out_dir,
        result_file=result_file,
        device_id=device_id if not use_dialog else "",
        device_name=device_name if not use_dialog else "",
        dpi=job.dpi,
        color_mode=job.color_mode,
        source=job.source,
        use_dialog=use_dialog,
    )
    attempt.command = format_command(cmd)
    scan_log(f"WIA start: {attempt.command}")
    t0 = time.monotonic()
    wia_timeout = min(float(job.timeout or DEFAULT_TIMEOUT_S), float(WIA_HANG_TIMEOUT_S))
    if use_dialog:
        wia_timeout = float(job.timeout or DEFAULT_TIMEOUT_S)
    rc, out, err, to = run_process(cmd, timeout=wia_timeout, cwd=str(out_dir))
    attempt.returncode, attempt.stdout, attempt.stderr, attempt.timed_out = rc, out, err, to
    attempt.duration_s = time.monotonic() - t0
    scan_log(
        f"WIA ende: exit={rc} timeout={to} dauer={attempt.duration_s:.1f}s\n"
        f"stdout: {_tail(out, 2000)}\nstderr: {_tail(err, 2000)}"
    )
    paths: List[Path] = read_result_file(result_file)
    if not paths:
        for line in (out or "").splitlines():
            s = line.strip().strip('"')
            if s and s != "CANCELLED":
                p = Path(s)
                try:
                    if p.is_file():
                        paths.append(p)
                except OSError:
                    pass
    if not paths:
        paths = wait_for_output(out_dir, before, stem="scan_wia_", timeout=2.0)
    attempt.paths = validate_and_normalize(paths, out_dir=out_dir)
    if not attempt.paths:
        if rc == 3 or "CANCELLED" in (out or ""):
            attempt.cancelled = True
            attempt.error = "Scan abgebrochen (Windows-Scannerdialog)."
        elif to:
            attempt.error = (
                f"Zeitüberschreitung ({int(wia_timeout)} s) beim WIA-Scan. "
                "Gerät im Energiesparmodus oder nicht erreichbar — anderes Gerät wählen."
            )
        else:
            msg = _tail(err, 400) or f"Exit-Code {rc}"
            if is_busy_text(err):
                attempt.error = (
                    "WIA-Gerät ausgelastet — ScanTuxio / Windows-Fax und -Scan / vorherigen Scan schließen. "
                    + msg
                )
            else:
                attempt.error = "WIA hat kein Bild geliefert. " + msg
    scan_log(f"WIA Ergebnis: {[str(p) for p in attempt.paths]} fehler={attempt.error!r}")
    return attempt


def _run_escl(job: ScanJob, out_dir: Path, *, device_id: str) -> ScanAttempt:
    attempt = ScanAttempt(backend=BACKEND_ESCL)
    did = escl_device_id(device_id)
    if not did.lower().startswith("native-escl:"):
        attempt.error = f"Kein eSCL-Gerät: {device_id or '(leer)'}"
        return attempt
    try:
        from instantlensdoc.core.scantuxio import scanner_escl as st_escl
    except Exception as e:
        attempt.error = f"eSCL-Client nicht ladbar: {e}"
        return attempt
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = f"scan_escl_{stamp}"
    before = snapshot_dir(out_dir)
    attempt.command = f"eSCL {did} dpi={job.dpi} mode={job.color_mode} source={job.source}"
    scan_log(f"eSCL start: {attempt.command}")
    t0 = time.monotonic()
    try:
        if job.is_adf:
            batch_dir = out_dir / stem
            batch_dir.mkdir(parents=True, exist_ok=True)
            produced = st_escl.scan_batch_adf(
                did, str(batch_dir), job.color_mode, str(job.dpi), job.source, None, timeout=int(job.timeout)
            )
            paths = [Path(p) for p in (produced or [])]
        else:
            dest = out_dir / f"{stem}.jpg"
            st_escl.scan_single_page(
                did, str(dest), job.color_mode, str(job.dpi), job.source, None, timeout=int(job.timeout)
            )
            paths = wait_for_output(out_dir, before, expected=[dest], stem=stem, timeout=2.0)
    except Exception as e:
        attempt.error = f"eSCL: {e}"
        paths = wait_for_output(out_dir, before, stem=stem, timeout=0.5)
    attempt.duration_s = time.monotonic() - t0
    attempt.paths = validate_and_normalize(paths, out_dir=out_dir)
    if not attempt.paths and not attempt.error:
        attempt.error = "eSCL-Scanner hat kein Bild geliefert."
    scan_log(f"eSCL Ergebnis: {[str(p) for p in attempt.paths]} fehler={attempt.error!r}")
    return attempt


def _run_sane(job: ScanJob, out_dir: Path, *, device_id: str) -> ScanAttempt:
    attempt = ScanAttempt(backend="sane")
    exe = shutil.which("scanimage")
    if not exe:
        attempt.error = "scanimage (SANE) nicht im PATH."
        return attempt
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = f"scan_sane_{stamp}"
    before = snapshot_dir(out_dir)
    mode = {"Color": "Color", "Gray": "Gray", "Lineart": "Lineart"}.get(job.color_mode, "Color")
    if job.is_adf:
        pattern = str(out_dir / f"{stem}-%03d.png")
        cmd = [exe, "--format=png", f"--batch={pattern}", "--batch-count=-1"]
    else:
        cmd = [exe, "--format=png"]
    if device_id:
        cmd += ["-d", device_id]
    cmd += ["--mode", mode, "--resolution", str(int(job.dpi))]
    if job.is_adf:
        cmd += ["--source", "ADF Duplex" if "Duplex" in job.source else "ADF"]
    dest = out_dir / f"{stem}.png"
    if not job.is_adf:
        cmd += ["-o", str(dest)]
    attempt.command = format_command(cmd)
    scan_log(f"SANE start: {attempt.command}")
    t0 = time.monotonic()
    rc, out, err, to = run_process(cmd, timeout=job.timeout, cwd=str(out_dir), hide_window=False)
    attempt.returncode, attempt.stdout, attempt.stderr, attempt.timed_out = rc, out, err, to
    attempt.duration_s = time.monotonic() - t0
    paths = wait_for_output(out_dir, before, expected=[dest], stem=stem, timeout=2.0)
    attempt.paths = validate_and_normalize(paths, out_dir=out_dir)
    if not attempt.paths:
        attempt.error = (
            f"Zeitüberschreitung ({int(job.timeout)} s) beim SANE-Scan."
            if to
            else (_tail(err, 400) or f"scanimage lieferte kein Bild (Exit-Code {rc}).")
        )
    scan_log(f"SANE Ergebnis: {[str(p) for p in attempt.paths]} fehler={attempt.error!r}")
    return attempt


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:  # unbekannte Platzhalter unverändert lassen
        return "{" + key + "}"


def split_command_template(template: str) -> List[str]:
    """Befehlsvorlage in Argumente zerlegen (Windows: Backslashes bleiben erhalten)."""
    t = (template or "").strip()
    if not t:
        return []
    if is_windows():
        tokens = shlex.split(t, posix=False)
        out: List[str] = []
        for tok in tokens:
            if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in "\"'":
                tok = tok[1:-1]
            out.append(tok)
        return out
    return shlex.split(t, posix=True)


def build_external_command(
    template: str,
    *,
    output: Path,
    outdir: Path,
    dpi: int,
    device: str,
    color: str,
    source: str,
) -> List[str]:
    """Platzhalter ``{output} {outdir} {dpi} {device} {color} {source}`` tokenweise ersetzen."""
    values = _SafeDict(
        output=str(output),
        outdir=str(outdir),
        dpi=str(int(dpi)),
        device=device or "",
        color=color or "Color",
        source=source or "Flatbed",
    )
    return [tok.format_map(values) for tok in split_command_template(template)]


def _run_external(job: ScanJob, out_dir: Path) -> ScanAttempt:
    attempt = ScanAttempt(backend=BACKEND_EXTERNAL)
    template = (job.external_cmd or "").strip()
    if not template:
        attempt.error = (
            "Externes Scanprogramm: keine Befehlszeile konfiguriert "
            "(Einstellungen → Scannen → Externes Programm)."
        )
        return attempt
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = f"scan_ext_{stamp}"
    output = out_dir / f"{stem}.png"
    ext_dir: Optional[Path] = None
    if (job.external_outdir or "").strip():
        ext_dir = Path(job.external_outdir).expanduser()
        try:
            ext_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
    before = snapshot_dir(out_dir)
    if ext_dir is not None:
        before.update(snapshot_dir(ext_dir, recursive=True))
    try:
        cmd = build_external_command(
            template,
            output=output,
            outdir=ext_dir or out_dir,
            dpi=job.dpi,
            device=job.device_name or job.device_id,
            color=job.color_mode,
            source=job.source,
        )
    except Exception as e:
        attempt.error = f"Befehlsvorlage ungültig: {e}"
        return attempt
    if not cmd:
        attempt.error = "Befehlsvorlage leer."
        return attempt
    attempt.command = format_command(cmd)
    scan_log(f"Extern start: {attempt.command}")
    t0 = time.monotonic()
    try:
        rc, out, err, to = run_process(cmd, timeout=max(job.timeout, 600.0), cwd=str(ext_dir or out_dir), hide_window=False)
    except FileNotFoundError as e:
        attempt.error = f"Programm nicht gefunden: {e}"
        scan_log(f"Extern: {attempt.error}")
        return attempt
    except OSError as e:
        attempt.error = f"Programm konnte nicht gestartet werden: {e}"
        scan_log(f"Extern: {attempt.error}")
        return attempt
    attempt.returncode, attempt.stdout, attempt.stderr, attempt.timed_out = rc, out, err, to
    attempt.duration_s = time.monotonic() - t0
    paths = wait_for_output(
        out_dir,
        before,
        expected=[output],
        stem=stem,
        extra_dirs=[ext_dir] if ext_dir is not None else (),
        timeout=EXTERNAL_FILE_WAIT_S if rc in (0, None) else 1.0,
    )
    attempt.paths = validate_and_normalize(paths, out_dir=out_dir)
    if not attempt.paths:
        where = str(ext_dir) if ext_dir is not None else str(out_dir)
        attempt.error = (
            f"Externes Programm hat keine neue Bild-/PDF-Datei erzeugt (geprüft: {where}"
            + (f", {output.name}" if "{output}" in template else "")
            + f"; Exit-Code {rc})."
        )
    scan_log(f"Extern Ergebnis: {[str(p) for p in attempt.paths]} fehler={attempt.error!r}")
    return attempt


# ------------------------------------------------------------------ Planung


@dataclass
class _Step:
    kind: str  # naps2 | wia | wia-dialog | escl | sane | external
    device_id: str = ""
    device_name: str = ""
    driver: str = "wia"

    def key(self) -> Tuple[str, str, str]:
        return (self.kind, self.driver, (self.device_id or self.device_name).lower())


def _job_looks_network(job: ScanJob) -> bool:
    blob = f"{job.device_id} {job.device_name} {job.device_backend}".lower()
    if any(
        x in blob
        for x in (
            "native-escl:",
            "escl:",
            "mdns:",
            "airscan:",
            "netzwerk",
            "network",
            "http://",
            "https://",
        )
    ):
        return True
    if classify_device_id(job.device_id, job.device_backend) == "escl":
        return True
    for did, _dn, dbe in job.fallback_devices or []:
        if classify_device_id(did, dbe) == "escl":
            return True
    return False


def _steps_for_device(device_id: str, device_name: str, device_backend: str, *, naps2_ok: bool, core_only: bool, skip_wia: bool = False) -> List[_Step]:
    """Reihenfolge je Gerät (Automatik). ``core_only``: nur ScanTuxio-Backends (kein PowerShell-WIA)."""
    cls = classify_device_id(device_id, device_backend)
    name = clean_device_name(device_name)
    win = is_windows()
    steps: List[_Step] = []
    if cls == "dialog":
        return [_Step("wia-dialog")]
    if cls == "naps2":
        drv, nm = parse_naps2_id(device_id)
        steps.append(_Step("naps2", device_id, nm or name, drv))
        if win and not core_only and drv == "wia" and not skip_wia:
            steps.append(_Step("wia", "", nm or name))
        return steps
    if cls == "escl":
        return [_Step("escl", device_id, name)]
    if cls == "wia":
        if win and not core_only and not skip_wia:
            steps.append(_Step("wia", device_id, name))
        if naps2_ok and name:
            steps.append(_Step("naps2", "", name, "wia"))
        return steps
    if cls == "twain":
        if naps2_ok and name:
            steps.append(_Step("naps2", "", name, "twain"))
        if win and not core_only and name and not skip_wia:
            steps.append(_Step("wia", "", name))
        return steps
    if cls == "pnp":
        if win and not core_only and name and not skip_wia:
            steps.append(_Step("wia", "", name))
        if naps2_ok and name:
            steps.append(_Step("naps2", "", name, "wia"))
        return steps
    if cls == "sane" or (cls == "unknown" and not win):
        return [_Step("sane", device_id, name)]
    if cls == "none":
        return [_Step("wia-dialog")] if win and not skip_wia else ([_Step("sane", "", "")] if not win else [])
    # unknown unter Windows: Name probieren
    if win and not core_only and name and not skip_wia:
        steps.append(_Step("wia", "", name))
    if naps2_ok and name:
        steps.append(_Step("naps2", "", name, "wia"))
    return steps


def plan_steps(job: ScanJob) -> List[_Step]:
    """Versuchsreihenfolge gemäß Backend-Einstellung (dedupliziert)."""
    backend = (job.backend or BACKEND_AUTO).lower()
    naps2_ok = bool(naps2_console_path(job.naps2_path))
    win = is_windows()
    devices = [(job.device_id, job.device_name, job.device_backend)] + list(job.fallback_devices or [])
    name = clean_device_name(job.device_name)
    steps: List[_Step] = []

    if backend == BACKEND_EXTERNAL:
        steps = [_Step("external", job.device_id, name)]
    elif backend == BACKEND_WIA:
        cls = classify_device_id(job.device_id, job.device_backend)
        if cls == "dialog" or (not job.device_id and not name):
            steps = [_Step("wia-dialog")]
        elif cls == "wia":
            steps = [_Step("wia", job.device_id, name), _Step("wia-dialog")]
        else:
            steps = [_Step("wia", "", name), _Step("wia-dialog")]
    elif backend == BACKEND_NAPS2:
        cls = classify_device_id(job.device_id, job.device_backend)
        if cls == "naps2":
            drv, nm = parse_naps2_id(job.device_id)
            steps = [_Step("naps2", job.device_id, nm or name, drv)]
        else:
            steps = [_Step("naps2", "", name, "twain" if cls == "twain" else "wia")]
    elif backend == BACKEND_TWAIN:
        nm = name
        if classify_device_id(job.device_id, job.device_backend) == "naps2":
            _drv, nm2 = parse_naps2_id(job.device_id)
            nm = nm2 or name
        steps = [_Step("naps2", "", nm, "twain")]
    elif backend == BACKEND_ESCL:
        for did, dn, dbe in devices:
            if classify_device_id(did, dbe) == "escl":
                steps.append(_Step("escl", did, clean_device_name(dn)))
        if not steps:
            steps = [_Step("escl", job.device_id, name)]
    else:
        core_only = backend == BACKEND_SCANTUXIO
        skip_wia = _job_looks_network(job)
        for did, dn, dbe in devices:
            steps.extend(
                _steps_for_device(
                    did, dn, dbe, naps2_ok=naps2_ok, core_only=core_only, skip_wia=skip_wia
                )
            )
        if win and not core_only and not skip_wia:
            steps.append(_Step("wia-dialog"))
        if skip_wia:
            escl_steps = [s for s in steps if s.kind == "escl"]
            rest = [s for s in steps if s.kind != "escl" and s.kind != "wia"]
            steps = escl_steps + rest
    seen: set = set()
    uniq: List[_Step] = []
    for s in steps:
        k = s.key()
        if k in seen:
            continue
        seen.add(k)
        uniq.append(s)
    return uniq


def _run_step(job: ScanJob, out_dir: Path, step: _Step) -> ScanAttempt:
    if step.kind == "naps2":
        return _run_naps2(job, out_dir, driver=step.driver, device_name=step.device_name)
    if step.kind == "wia":
        return _run_wia(job, out_dir, device_id=step.device_id, device_name=step.device_name, use_dialog=False)
    if step.kind == "wia-dialog":
        return _run_wia(job, out_dir, device_id="", device_name="", use_dialog=True)
    if step.kind == "escl":
        return _run_escl(job, out_dir, device_id=step.device_id)
    if step.kind == "sane":
        return _run_sane(job, out_dir, device_id=step.device_id)
    if step.kind == "external":
        return _run_external(job, out_dir)
    a = ScanAttempt(backend=step.kind)
    a.error = f"Unbekannter Schritt: {step.kind}"
    return a


def run_scan(job: ScanJob) -> ScanResult:
    """Scan ausführen; wirft nie. Ergebnisdateien liegen in ``result.out_dir``."""
    out_dir = Path(job.out_dir) if job.out_dir else Path(tempfile.mkdtemp(prefix="ild-scan-"))
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return ScanResult(error=f"Ausgabeordner nicht anlegbar: {e}", out_dir=out_dir)
    result = ScanResult(out_dir=out_dir)
    scan_log(
        f"=== Scan: {job.describe_de()} | id={job.device_id!r} backend-info={job.device_backend!r} "
        f"out={out_dir} ==="
    )
    try:
        steps = plan_steps(job)
    except Exception as e:
        result.error = f"Scan-Planung fehlgeschlagen: {e}"
        scan_log(result.error)
        return result
    if not steps:
        result.error = (
            "Kein passendes Scan-Backend für dieses Gerät "
            f"({job.device_name or job.device_id or 'kein Gerät'}) — Backend in Einstellungen → Scannen prüfen."
        )
        scan_log(result.error)
        return result
    scan_log("Plan: " + " → ".join(f"{s.kind}:{s.driver}:{s.device_id or s.device_name}" for s in steps))
    for step in steps:
        try:
            attempt = _run_step(job, out_dir, step)
        except Exception as e:  # defensiv — Backend-Fehler nie nach oben
            attempt = ScanAttempt(backend=step.kind, error=f"{type(e).__name__}: {e}")
            scan_log(f"Schritt {step.kind} Ausnahme: {e}")
        result.attempts.append(attempt)
        if attempt.ok:
            result.paths = list(attempt.paths)
            result.backend = BACKEND_LABELS_DE.get(attempt.backend, attempt.backend)
            scan_log(f"OK über {attempt.backend}: {[str(p) for p in result.paths]}")
            return result
        if attempt.cancelled:
            result.cancelled = True
            result.error = attempt.error or "Scan abgebrochen."
            scan_log("Abgebrochen.")
            return result
    first = result.attempts[0] if result.attempts else None
    dev = job.device_name or job.device_id or "Standardgerät"
    if result.busy:
        result.error = (
            f"Scanner „{dev}“ ist ausgelastet. Bitte ScanTuxio, Windows-Fax und -Scan, NAPS2 "
            "oder einen vorherigen Scan schließen und erneut versuchen."
        )
    else:
        result.error = (
            f"Kein Bild von „{dev}“ erhalten"
            + (f" ({first.error})" if first and first.error else "")
            + "."
        )
    scan_log(f"FEHLER: {result.error}")
    return result


__all__ = [
    "BACKEND_AUTO",
    "BACKEND_ESCL",
    "BACKEND_EXTERNAL",
    "BACKEND_LABELS_DE",
    "BACKEND_NAPS2",
    "BACKEND_ORDER",
    "BACKEND_SCANTUXIO",
    "BACKEND_TWAIN",
    "BACKEND_WIA",
    "BackendStatus",
    "COLOR_LABELS_DE",
    "COLOR_MODES",
    "DPI_CHOICES",
    "EXTERNAL_PLACEHOLDERS",
    "ScanAttempt",
    "ScanJob",
    "ScanResult",
    "SOURCES",
    "SOURCE_LABELS_DE",
    "WIA_DIALOG_DEVICE_ID",
    "WIA_DIALOG_LABEL_DE",
    "backend_availability",
    "build_external_command",
    "build_naps2_command",
    "build_wia_command",
    "classify_device_id",
    "clean_device_name",
    "decode_output",
    "escl_device_id",
    "format_command",
    "looks_like_cli_option_error",
    "naps2_console_path",
    "plan_steps",
    "powershell_exe",
    "read_result_file",
    "run_process",
    "run_scan",
    "scan_log",
    "scan_log_path",
    "snapshot_dir",
    "validate_and_normalize",
    "wait_for_output",
    "write_wia_script",
]
