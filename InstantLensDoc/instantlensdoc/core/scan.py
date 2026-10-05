"""Scan-/Import-Pipeline mit Tesseract-OCR — 2.6.2 / Layout-Erhalt 2.6.3 / 2.6.41 / 2.6.54.

Seitenbilder (Scanner-Acquire, Datei-Import, Fotos, ScanTuxio-UI) → optional OCR →
PDF-Seiten in die aktuelle Session + ``*.ildocr.txt`` (+ optional hOCR/TSV).

    Acquire (2.6.54): ``scan_transfer.run_scan`` (ScanTuxio-Ablauf; früher
    ``scan_single_page_dispatch`` / WIA-PowerShell). Backend wählbar.
"""

from __future__ import annotations

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


# Letzter Acquire-Fehler (DE) — UI kann anzeigen; nie Exception nach aussen noetig
_LAST_ACQUIRE_ERROR: str = ""
_LAST_ACQUIRE_RESULT = None  # scan_transfer.ScanResult des letzten Aufrufs — 2.6.54


def last_acquire_error() -> str:
    """Letzte Scan-Acquire-Fehlermeldung (leer wenn ok / abgebrochen)."""
    return _LAST_ACQUIRE_ERROR


def last_acquire_result():
    """Vollständiges ``ScanResult`` (Versuche, Befehle, stdout/stderr) — 2.6.54."""
    return _LAST_ACQUIRE_RESULT


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


def build_scan_job(
    device: Optional[DeviceInfo],
    *,
    dpi: int | None = None,
    color_mode: str | None = None,
    source: str | None = None,
    backend: str | None = None,
    out_dir: str | Path | None = None,
    fallback_devices: Sequence[DeviceInfo] = (),
):
    """``ScanJob`` aus DeviceInfo + Einstellungen (Backend/DPI/Farbe/Quelle/Pfade) — 2.6.54."""
    from instantlensdoc.core import scan_transfer as st

    try:
        from instantlensdoc.core.app_settings import get_scan_settings

        cfg = get_scan_settings()
    except Exception:
        cfg = {}
    job = st.ScanJob(
        device_id=(device.device_id if device else "") or "",
        device_name=(device.name if device else "") or "",
        device_backend=(device.backend if device else "") or "",
        backend=str(backend or cfg.get("scan_backend") or st.BACKEND_AUTO),
        dpi=int(dpi or cfg.get("scan_dpi") or 300),
        color_mode=str(color_mode or cfg.get("scan_color_mode") or "Color"),
        source=str(source or cfg.get("scan_source") or "Flatbed"),
        out_dir=Path(out_dir) if out_dir else None,
        external_cmd=str(cfg.get("scan_external_cmd") or ""),
        external_outdir=str(cfg.get("scan_external_outdir") or ""),
        naps2_path=str(cfg.get("scan_naps2_path") or ""),
        fallback_devices=[
            (d.device_id or "", d.name or "", d.backend or "")
            for d in fallback_devices
            if d is not None and d is not device
        ],
    )
    return job


def acquire_from_scanner(
    device: Optional[DeviceInfo] = None,
    *,
    out_dir: str | Path | None = None,
    dpi: int | None = None,
    color_mode: str | None = None,
    source: str | None = None,
    backend: str | None = None,
    fallback_devices: Sequence[DeviceInfo] = (),
) -> List[Path]:
    """
    Scan vom gewählten Gerät — ScanTuxio-Ablauf über ``scan_transfer.run_scan`` — 2.6.54.

    Backend aus Einstellungen (Automatik: WIA direkt → NAPS2 → eSCL → Windows-Dialog;
    oder fest WIA/NAPS2/eSCL/TWAIN/externes Programm). Bei „ausgelastet“ werden
    andere ScanTuxio-Backends (NAPS2/TWAIN/eSCL) versucht.
    Ohne Hardware/Backend: leere Liste (UI zeigt ``last_acquire_error()``).
    Wirft nicht.
    """
    global _LAST_ACQUIRE_ERROR, _LAST_ACQUIRE_RESULT
    _LAST_ACQUIRE_ERROR = ""
    _LAST_ACQUIRE_RESULT = None
    try:
        from instantlensdoc.core import scan_transfer as st

        out = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="ild-scan-"))
        out.mkdir(parents=True, exist_ok=True)
        job = build_scan_job(
            device,
            dpi=dpi,
            color_mode=color_mode,
            source=source,
            backend=backend,
            out_dir=out,
            fallback_devices=fallback_devices,
        )
        result = st.run_scan(job)
        _LAST_ACQUIRE_RESULT = result
        if result.ok:
            _LAST_ACQUIRE_ERROR = ""
            return list(result.paths)
        if result.cancelled:
            _LAST_ACQUIRE_ERROR = ""
            return []
        _LAST_ACQUIRE_ERROR = result.detail_text_de()
        if result.busy and job.backend in (st.BACKEND_AUTO, st.BACKEND_SCANTUXIO):
            alt = _acquire_scantuxio_other_backends(
                out, skip_ids={job.device_id, _scantuxio_device_id(device)}
            )
            if alt:
                _LAST_ACQUIRE_ERROR = ""
                return alt
            from instantlensdoc.core.scantuxio_ui import wia_busy_user_hint_de

            _LAST_ACQUIRE_ERROR = wia_busy_user_hint_de(result.error)
        return []
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
    """NAPS2/TWAIN/eSCL nacheinander, wenn das Gerät ausgelastet ist — 2.6.46/2.6.54."""
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
    """Scan über ScanTuxio-Backends (``scan_single_page_dispatch``-Äquivalent: NAPS2/eSCL/SANE)."""
    global _LAST_ACQUIRE_ERROR
    if not device_id:
        return []
    from instantlensdoc.core import scan_transfer as st

    job = build_scan_job(
        DeviceInfo(kind=DeviceKind.SCANNER, name=device_id, device_id=device_id),
        backend=st.BACKEND_SCANTUXIO,
        out_dir=out_dir,
    )
    result = st.run_scan(job)
    if result.ok:
        _LAST_ACQUIRE_ERROR = ""
        return list(result.paths)
    if not result.cancelled:
        _LAST_ACQUIRE_ERROR = result.error or "ScanTuxio lieferte kein Bild."
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
