"""Scan-/Import-Pipeline mit Tesseract-OCR — 2.6.2 / Layout-Erhalt 2.6.3 / 2.6.41 / 2.6.46.

Seitenbilder (Scanner-Acquire, Datei-Import, Fotos, ScanTuxio-UI) → optional OCR →
PDF-Seiten in die aktuelle Session + ``*.ildocr.txt`` (+ optional hOCR/TSV).

Acquire: primär ScanTuxio-Hauptfenster (``scantuxio_ui``); sekundär
``scan_single_page_dispatch`` (NAPS2 / native-eSCL / SANE) und WIA.
Bei WIA busy/in-use: andere ScanTuxio-Backends (NAPS2/TWAIN/eSCL) versuchen.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Union

from PIL import Image

from instantlensdoc.core import ocr as ocr_mod
from instantlensdoc.core.devices import DeviceInfo, DeviceKind
from instantlensdoc.core.ocr import OcrOutputMode, OcrResult, OcrUnavailable


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}


@dataclass
class ScanPageResult:
    source_label: str
    image_path: Optional[Path] = None
    page_index: Optional[int] = None  # 0-based im Ziel-PDF nach Einfügen
    ocr: Optional[OcrResult] = None
    sidecar: Optional[Path] = None
    error: str = ""


@dataclass
class ScanSessionResult:
    pages: List[ScanPageResult] = field(default_factory=list)
    pdf_path: Optional[Path] = None
    ocr_enabled: bool = False
    warnings: List[str] = field(default_factory=list)

    @property
    def ok_count(self) -> int:
        return sum(1 for p in self.pages if not p.error)

    @property
    def combined_text(self) -> str:
        parts: List[str] = []
        for i, p in enumerate(self.pages, 1):
            if p.ocr and p.ocr.text.strip():
                parts.append(f"--- Seite {i}: {p.source_label} ---\n{p.ocr.text.strip()}")
        return "\n\n".join(parts)


def _load_rgb(path: Union[str, Path, Image.Image]) -> Image.Image:
    if isinstance(path, Image.Image):
        img = path
    else:
        img = Image.open(path)
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        return bg
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


# Letzter Acquire-Fehler (DE) — UI kann anzeigen; nie Exception nach aussen noetig
_LAST_ACQUIRE_ERROR: str = ""


def last_acquire_error() -> str:
    """Letzte Scan-Acquire-Fehlermeldung (leer wenn ok / abgebrochen)."""
    return _LAST_ACQUIRE_ERROR


def _scantuxio_device_id(device: Optional[DeviceInfo]) -> str:
    """Mappt ILD-DeviceInfo auf ScanTuxio device_id (naps2:/native-escl:/…)."""
    if not device:
        return ""
    did = (device.device_id or "").strip()
    if did.startswith(("naps2:", "native-escl:", "escl:", "airscan:", "net:")):
        return did
    # Legacy ILD-IDs
    if did.startswith("NAPS2:"):
        rest = did[len("NAPS2:") :]
        if rest.lower().startswith(("wia:", "twain:")):
            return "naps2:" + rest
        return f"naps2:wia:{rest}" if rest else ""
    if did.startswith("TWAIN"):
        name = (device.name or did.replace("TWAIN:", "").replace("TWAIN-DS:", "")).strip()
        return f"naps2:twain:{name}" if name else ""
    backend = (device.backend or "").upper()
    if "NAPS2" in backend:
        drv = "wia"
        if "TWAIN" in backend:
            drv = "twain"
        return f"naps2:{drv}:{(device.name or did).strip()}"
    if "ESCL" in backend or "MDNS" in backend:
        return did
    return did


def acquire_from_scanner(
    device: Optional[DeviceInfo] = None,
    *,
    out_dir: str | Path | None = None,
) -> List[Path]:
    """
    Versucht einen Scan vom gewählten Gerät.

    Sekundär (nach ScanTuxio-UI): ``scan_single_page_dispatch`` (NAPS2/eSCL/SANE).
    Windows: WIA nur als Fallback; bei busy andere ScanTuxio-Backends.
    Ohne Hardware/Backend: leere Liste (UI fällt auf Datei-Import zurück).
    Wirft nicht — Fehler in ``last_acquire_error()``.
    """
    global _LAST_ACQUIRE_ERROR
    _LAST_ACQUIRE_ERROR = ""
    try:
        out = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="ild-scan-"))
        out.mkdir(parents=True, exist_ok=True)
        system = platform.system()
        st_id = _scantuxio_device_id(device)
        if st_id:
            paths = _acquire_scantuxio(st_id, out)
            if paths:
                return paths
            if _wia_busy_acquire_error():
                alt = _acquire_scantuxio_other_backends(out, skip_ids={st_id})
                if alt:
                    return alt
        if device and (device.device_id or "").startswith("TWAIN"):
            _LAST_ACQUIRE_ERROR = (
                "TWAIN-Quelle: ScanTuxio/NAPS2 ohne Bild — Fallback WIA. "
                "Falls leer: Bilder importieren oder NAPS2/WIA-Treiber prüfen."
            )
        if system == "Windows":
            paths = _acquire_wia_windows(device, out)
            if paths:
                return paths
            wia_err = _LAST_ACQUIRE_ERROR
            if _wia_busy_acquire_error():
                alt = _acquire_scantuxio_other_backends(out, skip_ids={st_id} if st_id else set())
                if alt:
                    return alt
                from instantlensdoc.core.scantuxio_ui import wia_busy_user_hint_de

                _LAST_ACQUIRE_ERROR = wia_busy_user_hint_de(wia_err)
                return []
            # Letzter Versuch: ScanTuxio NAPS2 ohne feste ID (erstes WIA-Gerät)
            if not st_id:
                try:
                    from instantlensdoc.core.scantuxio import scanner_naps2 as st_naps2

                    for d in st_naps2.list_devices(timeout=15) or []:
                        paths = _acquire_scantuxio(d.device_id, out)
                        if paths:
                            return paths
                        break
                except Exception:
                    pass
            return []
        if st_id:
            return []
        return _acquire_sane(device, out)
    except Exception as e:
        _LAST_ACQUIRE_ERROR = f"Scan fehlgeschlagen: {e}"
        return []


def _wia_busy_acquire_error() -> bool:
    from instantlensdoc.core.scantuxio_ui import is_wia_busy_message

    return is_wia_busy_message(_LAST_ACQUIRE_ERROR)


def _acquire_scantuxio_other_backends(
    out_dir: Path,
    *,
    skip_ids: Optional[set[str]] = None,
) -> List[Path]:
    """NAPS2/TWAIN/eSCL nacheinander, wenn WIA busy ist — 2.6.46."""
    skip = {s for s in (skip_ids or set()) if s}
    try:
        from instantlensdoc.core.scantuxio import scanner as st_scanner
    except Exception:
        return []
    try:
        devices = list(st_scanner.list_devices_all(timeout=20) or [])
    except Exception:
        return []

    def _prio(did: str) -> int:
        d = (did or "").lower()
        if d.startswith("naps2:twain:"):
            return 0
        if d.startswith("native-escl:") or d.startswith("escl:"):
            return 1
        if d.startswith("naps2:"):
            return 2
        return 9

    ordered = sorted(
        devices,
        key=lambda d: _prio(str(getattr(d, "device_id", "") or "")),
    )
    for d in ordered:
        did = str(getattr(d, "device_id", "") or "").strip()
        if not did or did in skip:
            continue
        paths = _acquire_scantuxio(did, out_dir)
        if paths:
            return paths
        skip.add(did)
    return []


def _acquire_scantuxio(device_id: str, out_dir: Path) -> List[Path]:
    """Scan über ScanTuxio ``scan_single_page_dispatch``."""
    global _LAST_ACQUIRE_ERROR
    if not device_id:
        return []
    try:
        from instantlensdoc.core.scantuxio import scanner as st_scanner
    except Exception as e:
        _LAST_ACQUIRE_ERROR = f"ScanTuxio nicht ladbar: {e}"
        return []
    token = uuid.uuid4().hex[:8]
    dest = out_dir / f"scan_st_{token}.png"
    try:
        st_scanner.scan_single_page_dispatch(
            device_id,
            str(dest),
            mode="Color",
            resolution="300",
            source=None,
            timeout=180,
        )
    except Exception as e:
        _LAST_ACQUIRE_ERROR = str(e)[:240]
        return []
    if dest.is_file() and dest.stat().st_size > 32:
        _LAST_ACQUIRE_ERROR = ""
        return [dest]
    alts = [
        p
        for p in out_dir.glob(f"scan_st_{token}*")
        if p.is_file() and p.stat().st_size > 32
    ]
    if alts:
        _LAST_ACQUIRE_ERROR = ""
        return alts[:1]
    if not _LAST_ACQUIRE_ERROR:
        _LAST_ACQUIRE_ERROR = "ScanTuxio lieferte kein Bild."
    return []


def _acquire_wia_windows(device: Optional[DeviceInfo], out_dir: Path) -> List[Path]:
    """WIA: ShowAcquireImage / Transfer via PowerShell COM."""
    global _LAST_ACQUIRE_ERROR
    device_id = (device.device_id if device else "") or ""
    # TWAIN-IDs sind keine WIA DeviceIDs — Common Dialog nutzen
    if device_id.startswith("TWAIN"):
        device_id = ""
    out_lit = str(out_dir).replace("'", "''")
    id_lit = device_id.replace("'", "''")
    ps = f"""
$ErrorActionPreference = 'Stop'
$OutDir = '{out_lit}'
$DeviceId = '{id_lit}'
try {{
  $cd = New-Object -ComObject WIA.CommonDialog
  if ($DeviceId -and -not $DeviceId.StartsWith('TWAIN')) {{
    $dm = New-Object -ComObject WIA.DeviceManager
    $info = $null
    foreach ($d in @($dm.DeviceInfos)) {{
      if ([string]$d.DeviceID -eq $DeviceId) {{ $info = $d; break }}
    }}
    if (-not $info) {{
      # Fallback: Common Dialog statt hartem Fehler
      $img = $cd.ShowAcquireImage()
    }} else {{
      $dev = $info.Connect()
      $item = $dev.Items(1)
      $img = $cd.ShowTransfer($item)
    }}
  }} else {{
    $img = $cd.ShowAcquireImage()
  }}
  if (-not $img) {{ exit 0 }}
  $path = Join-Path $OutDir ('scan_' + [guid]::NewGuid().ToString('N').Substring(0,8) + '.jpg')
  $img.SaveFile($path)
  Write-Output $path
}} catch {{
  [Console]::Error.WriteLine($_.Exception.Message)
  exit 1
}}
"""
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if not powershell:
        _LAST_ACQUIRE_ERROR = "PowerShell nicht gefunden — Scan nicht moeglich."
        return []
    run_kwargs: dict = {
        "capture_output": True,
        "text": True,
        "timeout": 180,
        "check": False,
    }
    if platform.system() == "Windows":
        run_kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        run_kwargs["encoding"] = "utf-8"
        run_kwargs["errors"] = "replace"
    try:
        proc = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                ps,
            ],
            **run_kwargs,
        )
    except subprocess.TimeoutExpired:
        _LAST_ACQUIRE_ERROR = "Scan-Timeout (WIA). Bitte erneut versuchen oder Bilder importieren."
        return []
    except Exception as e:
        _LAST_ACQUIRE_ERROR = f"WIA-Scan: {e}"
        return []
    paths: List[Path] = []
    for line in (proc.stdout or "").splitlines():
        p = Path(line.strip().strip('"'))
        if p.is_file():
            paths.append(p)
    if not paths:
        err = (proc.stderr or "").strip()
        if err:
            _LAST_ACQUIRE_ERROR = err
        elif proc.returncode not in (0, None):
            _LAST_ACQUIRE_ERROR = (
                "Kein Bild vom Scanner (WIA). Treiber pruefen oder Bilder importieren."
            )
    return paths


def _acquire_sane(device: Optional[DeviceInfo], out_dir: Path) -> List[Path]:
    global _LAST_ACQUIRE_ERROR
    exe = shutil.which("scanimage")
    if not exe:
        _LAST_ACQUIRE_ERROR = "scanimage (SANE) nicht im PATH."
        return []
    dest = out_dir / "scan.pnm"
    cmd = [exe, "--format=pnm"]
    if device and device.device_id:
        cmd.extend(["-d", device.device_id])
    try:
        with open(dest, "wb") as fh:
            proc = subprocess.run(cmd, stdout=fh, stderr=subprocess.PIPE, timeout=180, check=False)
        if proc.returncode != 0 or not dest.is_file() or dest.stat().st_size < 32:
            if dest.exists():
                dest.unlink(missing_ok=True)
            err = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
            _LAST_ACQUIRE_ERROR = err or "scanimage lieferte kein Bild."
            return []
        jpg = out_dir / "scan.jpg"
        Image.open(dest).convert("RGB").save(jpg, "JPEG", quality=90)
        dest.unlink(missing_ok=True)
        return [jpg]
    except Exception as e:
        _LAST_ACQUIRE_ERROR = f"SANE-Scan: {e}"
        return []


def import_image_paths(paths: Sequence[Union[str, Path]]) -> List[Path]:
    """Filtert und normalisiert importierte Bildpfade."""
    out: List[Path] = []
    for raw in paths:
        p = Path(raw)
        if not p.is_file():
            continue
        if p.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        out.append(p.resolve())
    return out


def expand_scan_import_paths(
    paths: Sequence[Union[str, Path]],
    *,
    out_dir: str | Path | None = None,
) -> List[Path]:
    """Bilder durchreichen; PDF-Seiten als PNG rasterisieren — 2.6.46."""
    dest = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="ild-scan-imp-"))
    dest.mkdir(parents=True, exist_ok=True)
    out: List[Path] = []
    for raw in paths:
        p = Path(raw)
        try:
            if not p.is_file():
                continue
        except OSError:
            continue
        suf = p.suffix.lower()
        if suf in IMAGE_SUFFIXES:
            out.append(p.resolve())
            continue
        if suf != ".pdf":
            continue
        try:
            from ild_pdf.pages import page_count
            from ild_pdf.render import render_page

            n = int(page_count(p))
            for i in range(max(0, n)):
                img = render_page(p, i, scale=2.0, use_cache=False)
                png = dest / f"{p.stem}_p{i + 1}.png"
                img.convert("RGB").save(png, "PNG")
                if png.is_file() and png.stat().st_size > 32:
                    out.append(png)
        except Exception:
            continue
    return out


def ocr_page_image(
    image: Union[str, Path, Image.Image],
    *,
    lang: str = "deu+eng",
    mode: OcrOutputMode = OcrOutputMode.LAYOUT_PRESERVE,
    out_dir: str | Path | None = None,
    source_label: str = "",
    write_hocr: bool = True,
    write_tsv: bool = True,
) -> OcrResult:
    """OCR über Tesseract-Bridge (Default: Layout-Erhalt) — 2.6.3."""
    ok, msg = ocr_mod.tesseract_available()
    if not ok:
        raise OcrUnavailable(msg)
    return ocr_mod.run_ocr(
        image,
        lang=lang,
        mode=mode,
        out_dir=out_dir,
        source_label=source_label,
        write_hocr=write_hocr,
        write_tsv=write_tsv,
        preserve_layout=mode
        in (OcrOutputMode.LAYOUT_PRESERVE, OcrOutputMode.SEARCHABLE_IMAGE),
    )


def insert_scan_pages_into_pdf(
    pdf_path: str | Path,
    images: Sequence[Union[str, Path, Image.Image]],
    *,
    at_index: Optional[int] = None,
    ocr: bool = True,
    lang: str = "deu+eng",
    ocr_mode: OcrOutputMode = OcrOutputMode.LAYOUT_PRESERVE,
    write_hocr: bool = True,
    write_tsv: bool = True,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> ScanSessionResult:
    """
    Fügt Bildseiten in ``pdf_path`` ein; bei OCR Layout-Text + Sidecars.

    ``at_index``: Einfügeposition (0-based); ``None`` = ans Ende.
    Default-OCR: Layout-Erhalt (Blöcke / Lesereihenfolge / hOCR+TSV) — 2.6.3.
    """
    from ild_pdf.images import insert_image_as_page
    from ild_pdf.pages import page_count

    pdf_path = Path(pdf_path)
    result = ScanSessionResult(pdf_path=pdf_path, ocr_enabled=bool(ocr))
    if ocr:
        ok, msg = ocr_mod.tesseract_available()
        if not ok:
            result.warnings.append(msg)
            result.ocr_enabled = False

    total = len(images)
    insert_at = at_index
    if insert_at is None and pdf_path.exists():
        try:
            insert_at = page_count(pdf_path)
        except Exception:
            insert_at = None

    for i, src in enumerate(images):
        label = (
            str(src)
            if isinstance(src, (str, Path))
            else f"scan-{i + 1}"
        )
        if on_progress:
            on_progress(i, total, label)
        page = ScanPageResult(source_label=label)
        try:
            img = _load_rgb(src)
            if isinstance(src, (str, Path)):
                page.image_path = Path(src)
            # OCR zuerst (Sidecar neben PDF)
            if result.ocr_enabled:
                try:
                    ocr_res = ocr_page_image(
                        img,
                        lang=lang,
                        mode=ocr_mode,
                        out_dir=pdf_path.parent,
                        source_label=Path(label).name,
                        write_hocr=write_hocr,
                        write_tsv=write_tsv,
                    )
                    page.ocr = ocr_res
                    page.sidecar = ocr_res.sidecar
                except OcrUnavailable as e:
                    result.warnings.append(str(e))
                    result.ocr_enabled = False
                except Exception as e:
                    result.warnings.append(f"OCR {label}: {e}")

            before = 0
            if pdf_path.exists():
                try:
                    before = page_count(pdf_path)
                except Exception:
                    before = 0
            pos = insert_at if insert_at is not None else None
            insert_image_as_page(pdf_path, img, at_index=pos)
            after = page_count(pdf_path)
            # Index der eingefügten Seite
            if pos is not None:
                page.page_index = pos
                insert_at = pos + 1
            else:
                page.page_index = max(0, after - 1)

            # Sidecar am PDF-Seitennamen zusätzlich ablegen (Layout + optional hOCR/TSV)
            if page.ocr and page.ocr.text and page.page_index is not None:
                stem = f"{pdf_path.stem}.p{page.page_index + 1}"
                if page.ocr.layout is not None:
                    txt_p, hocr_p, tsv_p = ocr_mod.write_layout_sidecars(
                        pdf_path.parent,
                        stem,
                        page.ocr.layout,
                        lang=lang,
                        write_hocr=write_hocr,
                        write_tsv=write_tsv,
                    )
                    # Header-Seite ergänzen
                    body = txt_p.read_text(encoding="utf-8")
                    page_header = (
                        f"# page={page.page_index + 1}\n"
                        f"# source={Path(label).name}\n"
                    )
                    if "# page=" not in body:
                        # nach erstem Header-Block einfügen
                        lines = body.splitlines()
                        insert_at_line = 0
                        for li, ln in enumerate(lines):
                            if ln.startswith("#"):
                                insert_at_line = li + 1
                            else:
                                break
                        lines.insert(insert_at_line, page_header.rstrip())
                        txt_p.write_text("\n".join(lines) + "\n", encoding="utf-8")
                    page.sidecar = txt_p
                    if hocr_p:
                        page.ocr.hocr_path = hocr_p
                    if tsv_p:
                        page.ocr.tsv_path = tsv_p
                else:
                    side = pdf_path.with_suffix(
                        pdf_path.suffix + f".p{page.page_index + 1}.ildocr.txt"
                    )
                    header = (
                        f"# InstantLens Doc Scan OCR\n"
                        f"# lang={lang}\n"
                        f"# page={page.page_index + 1}\n"
                        f"# source={Path(label).name}\n\n"
                    )
                    side.write_text(header + page.ocr.text, encoding="utf-8")
                    page.sidecar = side
            _ = before  # quiet linters
        except Exception as e:
            page.error = str(e)
        result.pages.append(page)

    if on_progress and total:
        on_progress(total, total, "fertig")
    return result


def ensure_pdf_for_session(
    pdf_path: Optional[Union[str, Path]],
    *,
    fallback_dir: str | Path,
    stem: str = "scan-session",
) -> Path:
    """Liefert Ziel-PDF: bestehendes oder neues leeres Ein-Seiten-PDF-Ziel."""
    if pdf_path:
        return Path(pdf_path)
    out = Path(fallback_dir) / f"{stem}.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


def device_is_scanner(device: Optional[DeviceInfo]) -> bool:
    return bool(device and device.kind == DeviceKind.SCANNER)
