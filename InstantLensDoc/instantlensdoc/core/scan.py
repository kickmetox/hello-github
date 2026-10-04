"""Scan-/Import-Pipeline mit Tesseract-OCR — 2.6.2.

Seitenbilder (Scanner-Acquire, Datei-Import, Fotos) → optional OCR →
PDF-Seiten in die aktuelle Session + ``*.ildocr.txt`` Sidecar.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import tempfile
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


def acquire_from_scanner(
    device: Optional[DeviceInfo] = None,
    *,
    out_dir: str | Path | None = None,
) -> List[Path]:
    """
    Versucht einen Scan vom gewählten Gerät.

    Windows: WIA Common Dialog (falls COM verfügbar).
    Linux: ``scanimage`` mit Geräte-ID.
    Ohne Hardware/Backend: leere Liste (UI fällt auf Datei-Import zurück).
    """
    out = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="ild-scan-"))
    out.mkdir(parents=True, exist_ok=True)
    system = platform.system()

    if system == "Windows":
        return _acquire_wia_windows(device, out)
    return _acquire_sane(device, out)


def _acquire_wia_windows(device: Optional[DeviceInfo], out_dir: Path) -> List[Path]:
    """WIA: ShowAcquireImage / Transfer via PowerShell COM."""
    device_id = (device.device_id if device else "") or ""
    out_lit = str(out_dir).replace("'", "''")
    id_lit = device_id.replace("'", "''")
    # Speichert ein JPEG; Common Dialog wenn keine DeviceID
    ps = f"""
$ErrorActionPreference = 'Stop'
$OutDir = '{out_lit}'
$DeviceId = '{id_lit}'
try {{
  $cd = New-Object -ComObject WIA.CommonDialog
  if ($DeviceId) {{
    $dm = New-Object -ComObject WIA.DeviceManager
    $info = $null
    foreach ($d in @($dm.DeviceInfos)) {{
      if ([string]$d.DeviceID -eq $DeviceId) {{ $info = $d; break }}
    }}
    if (-not $info) {{ throw "Scanner nicht gefunden: $DeviceId" }}
    $dev = $info.Connect()
    $item = $dev.Items(1)
    $img = $cd.ShowTransfer($item)
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
        return []
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
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except Exception:
        return []
    paths: List[Path] = []
    for line in (proc.stdout or "").splitlines():
        p = Path(line.strip().strip('"'))
        if p.is_file():
            paths.append(p)
    return paths


def _acquire_sane(device: Optional[DeviceInfo], out_dir: Path) -> List[Path]:
    exe = shutil.which("scanimage")
    if not exe:
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
            return []
        jpg = out_dir / "scan.jpg"
        Image.open(dest).convert("RGB").save(jpg, "JPEG", quality=90)
        dest.unlink(missing_ok=True)
        return [jpg]
    except Exception:
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


def ocr_page_image(
    image: Union[str, Path, Image.Image],
    *,
    lang: str = "deu+eng",
    mode: OcrOutputMode = OcrOutputMode.SEARCHABLE_IMAGE,
    out_dir: str | Path | None = None,
    source_label: str = "",
) -> OcrResult:
    """OCR über bestehende Tesseract-Bridge."""
    ok, msg = ocr_mod.tesseract_available()
    if not ok:
        raise OcrUnavailable(msg)
    return ocr_mod.run_ocr(
        image,
        lang=lang,
        mode=mode,
        out_dir=out_dir,
        source_label=source_label,
    )


def insert_scan_pages_into_pdf(
    pdf_path: str | Path,
    images: Sequence[Union[str, Path, Image.Image]],
    *,
    at_index: Optional[int] = None,
    ocr: bool = True,
    lang: str = "deu+eng",
    ocr_mode: OcrOutputMode = OcrOutputMode.SEARCHABLE_IMAGE,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> ScanSessionResult:
    """
    Fügt Bildseiten in ``pdf_path`` ein; bei OCR zusätzlich Sidecar / Text.

    ``at_index``: Einfügeposition (0-based); ``None`` = ans Ende.
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

            # Sidecar am PDF-Seitennamen zusätzlich ablegen wenn searchable
            if page.ocr and page.ocr.text and page.page_index is not None:
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
