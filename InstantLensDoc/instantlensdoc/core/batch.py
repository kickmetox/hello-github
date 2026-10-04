"""Batch-Konvertierung und PDF-Stapelverarbeitung — 2.6.24.

Bilder→PDF / OCR (Bestand) plus **viele PDFs** in einem Job:
Konvertieren (→PNG), Wasserzeichen, Komprimieren, Verschlüsseln.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, List, Sequence

from PIL import Image

from instantlensdoc.core import ocr as ocr_mod
from instantlensdoc.core.ocr import OcrOutputMode

_IMAGE_GLOB = ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.tif", "*.tiff")
_PDF_GLOB = ("*.pdf",)

ProgressCb = Callable[..., None]


class BatchMode(str, Enum):
    IMAGES_TO_ONE_PDF = "images_one_pdf"
    IMAGES_TO_PDF_EACH = "images_pdf_each"
    OCR_FOLDER = "ocr_folder"
    PDF_OCR_PAGES = "pdf_ocr_pages"
    # PDF-Stapel — 2.6.24
    PDF_CONVERT_PNG = "pdf_convert_png"
    PDF_WATERMARK = "pdf_watermark"
    PDF_COMPRESS = "pdf_compress"
    PDF_ENCRYPT = "pdf_encrypt"


class PdfBatchOp(str, Enum):
    """Einzelne Operation für ``run_pdf_batch`` — 2.6.24."""

    CONVERT = "convert"  # PDF → PNG-Seiten
    WATERMARK = "watermark"
    COMPRESS = "compress"
    ENCRYPT = "encrypt"


@dataclass
class BatchItemResult:
    source: Path
    output: Path | None
    ok: bool
    message: str = ""


@dataclass
class BatchResult:
    items: List[BatchItemResult]

    @property
    def ok_count(self) -> int:
        return sum(1 for i in self.items if i.ok)

    @property
    def fail_count(self) -> int:
        return sum(1 for i in self.items if not i.ok)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok_count": self.ok_count,
            "fail_count": self.fail_count,
            "items": [
                {
                    "source": str(i.source),
                    "output": str(i.output) if i.output else None,
                    "ok": i.ok,
                    "message": i.message,
                }
                for i in self.items
            ],
        }


@dataclass
class PdfBatchOptions:
    """Optionen für PDF-Stapeljobs — 2.6.24."""

    watermark_text: str = "CONFIDENTIAL"
    watermark_opacity: float = 0.25
    watermark_font_size: float = 48.0
    compress_quality: int = 70
    compress_max_edge: int = 2000
    compress_scale: float = 1.5
    user_password: str = ""
    owner_password: str | None = None
    aes256: bool = True
    convert_dpi: int = 150
    convert_fmt: str = "png"  # png | jpeg
    suffix: str = ""  # optional Output-Suffix vor Extension


def _collect_files(folder: Path, patterns: Sequence[str]) -> List[Path]:
    found: List[Path] = []
    seen: set[str] = set()
    for pat in patterns:
        for p in sorted(folder.glob(pat)):
            key = str(p.resolve())
            if key in seen:
                continue
            seen.add(key)
            if p.is_file():
                found.append(p)
    return found


def collect_pdfs(
    folder: str | Path | None = None,
    paths: Sequence[str | Path] | None = None,
) -> List[Path]:
    """PDFs aus Ordner und/oder expliziter Liste sammeln."""
    out: List[Path] = []
    seen: set[str] = set()
    if paths:
        for raw in paths:
            p = Path(raw)
            if p.is_file() and p.suffix.lower() == ".pdf":
                key = str(p.resolve())
                if key not in seen:
                    seen.add(key)
                    out.append(p)
    if folder:
        for p in _collect_files(Path(folder), _PDF_GLOB):
            key = str(p.resolve())
            if key not in seen:
                seen.add(key)
                out.append(p)
    return out


def _images_to_pdf(sources: Sequence[Path], dest: Path) -> None:
    from ild_pdf.pages import merge_pdfs

    if len(sources) == 1 and sources[0].suffix.lower() == ".pdf":
        dest.write_bytes(sources[0].read_bytes())
        return
    tmp_pdfs: List[Path] = []
    try:
        for src in sources:
            tmp = dest.parent / f"__batch_{src.stem}.pdf"
            img = Image.open(src)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            img.save(tmp, "PDF", resolution=100.0)
            tmp_pdfs.append(tmp)
        merge_pdfs(tmp_pdfs, dest)
    finally:
        for t in tmp_pdfs:
            t.unlink(missing_ok=True)


def _out_name(src: Path, out_dir: Path, *, stem_suffix: str, ext: str) -> Path:
    return out_dir / f"{src.stem}{stem_suffix}.{ext.lstrip('.')}"


def _convert_pdf_to_images(
    pdf: Path,
    out_dir: Path,
    *,
    dpi: int = 150,
    fmt: str = "png",
) -> Path:
    """Jede Seite als Bild; Rückgabe = Ordner mit Seitenbildern."""
    from ild_pdf.render import render_page
    import pypdfium2 as pdfium

    dest_dir = out_dir / f"{pdf.stem}_pages"
    dest_dir.mkdir(parents=True, exist_ok=True)
    scale = max(72, int(dpi or 150)) / 72.0
    doc = pdfium.PdfDocument(str(pdf))
    try:
        n = len(doc)
    finally:
        doc.close()
    fmt_l = (fmt or "png").lower()
    if fmt_l in ("jpg", "jpeg"):
        fmt_l = "jpeg"
        ext = "jpg"
    else:
        fmt_l = "png"
        ext = "png"
    for page in range(n):
        img = render_page(pdf, page, scale=scale, use_cache=False)
        dest = dest_dir / f"{pdf.stem}_p{page + 1:03d}.{ext}"
        if fmt_l == "jpeg":
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            img.save(dest, "JPEG", quality=90)
        else:
            img.save(dest, "PNG")
    return dest_dir


def _apply_one_pdf_op(
    pdf: Path,
    out_dir: Path,
    op: PdfBatchOp,
    opts: PdfBatchOptions,
) -> BatchItemResult:
    try:
        if op == PdfBatchOp.CONVERT:
            dest = _convert_pdf_to_images(
                pdf, out_dir, dpi=opts.convert_dpi, fmt=opts.convert_fmt
            )
            return BatchItemResult(pdf, dest, True, "Seiten als Bilder")

        if op == PdfBatchOp.WATERMARK:
            from ild_pdf.watermark import apply_watermark

            dest = _out_name(pdf, out_dir, stem_suffix=opts.suffix or "_wm", ext="pdf")
            apply_watermark(
                pdf,
                opts.watermark_text,
                out_path=dest,
                opacity=float(opts.watermark_opacity),
                font_size=float(opts.watermark_font_size),
            )
            return BatchItemResult(pdf, dest, True, "Wasserzeichen")

        if op == PdfBatchOp.COMPRESS:
            from ild_pdf.images import compress_pdf_as_images

            dest = _out_name(
                pdf, out_dir, stem_suffix=opts.suffix or "_compressed", ext="pdf"
            )
            compress_pdf_as_images(
                pdf,
                out_path=dest,
                jpeg_quality=int(opts.compress_quality),
                render_scale=float(opts.compress_scale),
                max_edge=int(opts.compress_max_edge),
                downsample=True,
            )
            return BatchItemResult(pdf, dest, True, "Komprimiert")

        if op == PdfBatchOp.ENCRYPT:
            from ild_pdf.security import set_password

            pw = (opts.user_password or "").strip()
            if not pw:
                return BatchItemResult(
                    pdf, None, False, "User-Passwort fehlt für Verschlüsselung"
                )
            dest = _out_name(
                pdf, out_dir, stem_suffix=opts.suffix or "_enc", ext="pdf"
            )
            set_password(
                pdf,
                user_password=pw,
                owner_password=opts.owner_password or pw,
                out_path=dest,
                aes256=bool(opts.aes256),
            )
            return BatchItemResult(pdf, dest, True, "Verschlüsselt AES")

        return BatchItemResult(pdf, None, False, f"Unbekannte Op {op}")
    except InterruptedError:
        raise
    except Exception as e:
        return BatchItemResult(pdf, None, False, str(e))


def run_pdf_batch(
    *,
    folder: str | Path | None = None,
    paths: Sequence[str | Path] | None = None,
    out_dir: str | Path,
    ops: Sequence[PdfBatchOp | str],
    options: PdfBatchOptions | None = None,
    progress: ProgressCb | None = None,
) -> BatchResult:
    """Viele PDFs mit einer oder mehreren Ops in einem Job verarbeiten — 2.6.24.

    Ops werden pro Datei in Reihenfolge ausgeführt (Pipeline). Zwischen-
    ergebnisse landen im Ausgabeordner; die letzte erfolgreiche Datei ist
    ``output`` des Items.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    opts = options or PdfBatchOptions()
    pdfs = collect_pdfs(folder, paths)
    parsed_ops: list[PdfBatchOp] = []
    for raw in ops:
        if isinstance(raw, PdfBatchOp):
            parsed_ops.append(raw)
        else:
            parsed_ops.append(PdfBatchOp(str(raw).lower().strip()))
    if not parsed_ops:
        return BatchResult(
            [BatchItemResult(Path("."), None, False, "Keine Operation angegeben")]
        )

    def log(msg: str, current: int = 0, total: int = 0) -> None:
        if not progress:
            return
        try:
            progress(msg, current, total)
        except TypeError:
            progress(msg)

    items: List[BatchItemResult] = []
    if not pdfs:
        return BatchResult(
            [BatchItemResult(Path(folder or "."), None, False, "Keine PDFs")]
        )

    total = len(pdfs)
    for i, pdf in enumerate(pdfs, start=1):
        log(f"{pdf.name} …", i - 1, total)
        current = pdf
        last_ok: Path | None = None
        messages: list[str] = []
        work_dir = out_dir
        try:
            for op in parsed_ops:
                # Pipeline: Eingabe = vorherige Ausgabe (außer Convert→Ordner)
                r = _apply_one_pdf_op(current, work_dir, op, opts)
                if not r.ok:
                    items.append(r)
                    log(f"Fehler {pdf.name}: {r.message}", i, total)
                    break
                messages.append(r.message or op.value)
                last_ok = r.output
                if r.output is not None and r.output.is_file():
                    current = r.output
                elif r.output is not None and r.output.is_dir():
                    # Convert endet typischerweise die Pipeline
                    last_ok = r.output
            else:
                items.append(
                    BatchItemResult(
                        pdf,
                        last_ok,
                        True,
                        " → ".join(messages),
                    )
                )
                log(f"OK {pdf.name}", i, total)
        except InterruptedError:
            raise
        except Exception as e:
            items.append(BatchItemResult(pdf, None, False, str(e)))
            log(f"Fehler {pdf.name}: {e}", i, total)
    return BatchResult(items)


def run_batch(
    folder: str | Path,
    out_dir: str | Path,
    mode: BatchMode,
    *,
    lang: str = "deu+eng",
    ocr_mode: OcrOutputMode = OcrOutputMode.SEARCHABLE_IMAGE,
    progress: ProgressCb | None = None,
    options: PdfBatchOptions | None = None,
) -> BatchResult:
    """progress(msg, current=i, total=n) — current/total optional (0 = unbekannt)."""
    folder = Path(folder)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    items: List[BatchItemResult] = []
    opts = options or PdfBatchOptions()

    def log(msg: str, current: int = 0, total: int = 0) -> None:
        if not progress:
            return
        try:
            progress(msg, current, total)
        except TypeError:
            progress(msg)
        # InterruptedError aus progress durchlassen (kein TypeError)

    # PDF-Stapel-Modi → run_pdf_batch — 2.6.24
    mode_to_op = {
        BatchMode.PDF_CONVERT_PNG: PdfBatchOp.CONVERT,
        BatchMode.PDF_WATERMARK: PdfBatchOp.WATERMARK,
        BatchMode.PDF_COMPRESS: PdfBatchOp.COMPRESS,
        BatchMode.PDF_ENCRYPT: PdfBatchOp.ENCRYPT,
    }
    if mode in mode_to_op:
        return run_pdf_batch(
            folder=folder,
            out_dir=out_dir,
            ops=[mode_to_op[mode]],
            options=opts,
            progress=progress,
        )

    if mode == BatchMode.IMAGES_TO_ONE_PDF:
        imgs = _collect_files(folder, _IMAGE_GLOB)
        if not imgs:
            return BatchResult([BatchItemResult(folder, None, False, "Keine Bilder im Ordner")])
        dest = out_dir / f"{folder.name}_batch.pdf"
        try:
            log(f"PDF aus {len(imgs)} Bildern…", 0, 1)
            _images_to_pdf(imgs, dest)
            log(f"Fertig: {dest.name}", 1, 1)
            items.append(BatchItemResult(folder, dest, True, f"{len(imgs)} Bilder"))
        except InterruptedError:
            raise
        except Exception as e:
            items.append(BatchItemResult(folder, None, False, str(e)))
        return BatchResult(items)

    if mode == BatchMode.IMAGES_TO_PDF_EACH:
        imgs = _collect_files(folder, _IMAGE_GLOB)
        total = len(imgs)
        for i, src in enumerate(imgs, start=1):
            dest = out_dir / f"{src.stem}.pdf"
            try:
                log(f"PDF {src.name}…", i - 1, total)
                _images_to_pdf([src], dest)
                log(f"OK {src.name}", i, total)
                items.append(BatchItemResult(src, dest, True))
            except InterruptedError:
                raise
            except Exception as e:
                log(f"Fehler {src.name}: {e}", i, total)
                items.append(BatchItemResult(src, None, False, str(e)))
        if not imgs:
            items.append(BatchItemResult(folder, None, False, "Keine Bilder"))
        return BatchResult(items)

    if mode == BatchMode.OCR_FOLDER:
        targets = _collect_files(folder, _IMAGE_GLOB)
        ok_ocr, msg = ocr_mod.tesseract_available()
        if not ok_ocr:
            return BatchResult([BatchItemResult(folder, None, False, msg)])
        total = len(targets)
        for i, src in enumerate(targets, start=1):
            try:
                log(f"OCR {src.name}…", i - 1, total)
                r = ocr_mod.run_ocr(
                    src,
                    lang=lang,
                    mode=ocr_mode,
                    out_dir=out_dir,
                    source_label=src.name,
                )
                out = r.searchable_pdf or out_dir / f"{src.stem}.ocr.txt"
                log(f"OK OCR {src.name}", i, total)
                items.append(BatchItemResult(src, out, True))
            except InterruptedError:
                raise
            except Exception as e:
                log(f"Fehler OCR {src.name}: {e}", i, total)
                items.append(BatchItemResult(src, None, False, str(e)))
        if not targets:
            items.append(BatchItemResult(folder, None, False, "Keine Bilder"))
        return BatchResult(items)

    if mode == BatchMode.PDF_OCR_PAGES:
        pdfs = _collect_files(folder, _PDF_GLOB)
        ok_ocr, msg = ocr_mod.tesseract_available()
        if not ok_ocr:
            return BatchResult([BatchItemResult(folder, None, False, msg)])
        from ild_pdf import render_page

        total = len(pdfs)
        for i, pdf_path in enumerate(pdfs, start=1):
            try:
                log(f"PDF OCR {pdf_path.name}…", i - 1, total)
                import pypdfium2 as pdfium

                doc = pdfium.PdfDocument(str(pdf_path))
                n = len(doc)
                doc.close()
                combined: List[str] = []
                for page in range(n):
                    log(f"OCR {pdf_path.name} Seite {page + 1}/{n}", i - 1, total)
                    img = render_page(pdf_path, page, scale=2.0)
                    r = ocr_mod.run_ocr(
                        img,
                        lang=lang,
                        mode=OcrOutputMode.EDITABLE_TEXT,
                        out_dir=out_dir,
                        source_label=f"{pdf_path.name} p{page + 1}",
                    )
                    combined.append(r.text)
                out_txt = out_dir / f"{pdf_path.stem}.batch-ocr.txt"
                out_txt.write_text("\n\n---\n\n".join(combined), encoding="utf-8")
                log(f"OK PDF OCR {pdf_path.name}", i, total)
                items.append(BatchItemResult(pdf_path, out_txt, True, f"{n} Seiten"))
            except InterruptedError:
                raise
            except Exception as e:
                log(f"Fehler PDF OCR {pdf_path.name}: {e}", i, total)
                items.append(BatchItemResult(pdf_path, None, False, str(e)))
        if not pdfs:
            items.append(BatchItemResult(folder, None, False, "Keine PDFs"))
        return BatchResult(items)

    return BatchResult([BatchItemResult(folder, None, False, f"Unbekannter Modus {mode}")])
