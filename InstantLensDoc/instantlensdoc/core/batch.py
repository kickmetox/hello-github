"""Batch-Konvertierung: Ordner → PDF / OCR."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, List, Sequence

from PIL import Image

from instantlensdoc.core import ocr as ocr_mod
from instantlensdoc.core.ocr import OcrOutputMode

_IMAGE_GLOB = ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.tif", "*.tiff")
_PDF_GLOB = ("*.pdf",)


class BatchMode(str, Enum):
    IMAGES_TO_ONE_PDF = "images_one_pdf"
    IMAGES_TO_PDF_EACH = "images_pdf_each"
    OCR_FOLDER = "ocr_folder"
    PDF_OCR_PAGES = "pdf_ocr_pages"


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


def run_batch(
    folder: str | Path,
    out_dir: str | Path,
    mode: BatchMode,
    *,
    lang: str = "deu+eng",
    ocr_mode: OcrOutputMode = OcrOutputMode.SEARCHABLE_IMAGE,
    progress: Callable[[str], None] | None = None,
) -> BatchResult:
    folder = Path(folder)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    items: List[BatchItemResult] = []

    def log(msg: str) -> None:
        if progress:
            progress(msg)

    if mode == BatchMode.IMAGES_TO_ONE_PDF:
        imgs = _collect_files(folder, _IMAGE_GLOB)
        if not imgs:
            return BatchResult([BatchItemResult(folder, None, False, "Keine Bilder im Ordner")])
        dest = out_dir / f"{folder.name}_batch.pdf"
        try:
            log(f"PDF aus {len(imgs)} Bildern…")
            _images_to_pdf(imgs, dest)
            items.append(BatchItemResult(folder, dest, True, f"{len(imgs)} Bilder"))
        except Exception as e:
            items.append(BatchItemResult(folder, None, False, str(e)))
        return BatchResult(items)

    if mode == BatchMode.IMAGES_TO_PDF_EACH:
        imgs = _collect_files(folder, _IMAGE_GLOB)
        for src in imgs:
            dest = out_dir / f"{src.stem}.pdf"
            try:
                _images_to_pdf([src], dest)
                items.append(BatchItemResult(src, dest, True))
            except Exception as e:
                items.append(BatchItemResult(src, None, False, str(e)))
        if not imgs:
            items.append(BatchItemResult(folder, None, False, "Keine Bilder"))
        return BatchResult(items)

    if mode == BatchMode.OCR_FOLDER:
        targets = _collect_files(folder, _IMAGE_GLOB)
        ok_ocr, msg = ocr_mod.tesseract_available()
        if not ok_ocr:
            return BatchResult([BatchItemResult(folder, None, False, msg)])
        for src in targets:
            try:
                log(f"OCR {src.name}…")
                r = ocr_mod.run_ocr(
                    src,
                    lang=lang,
                    mode=ocr_mode,
                    out_dir=out_dir,
                    source_label=src.name,
                )
                out = r.searchable_pdf or out_dir / f"{src.stem}.ocr.txt"
                items.append(BatchItemResult(src, out, True))
            except Exception as e:
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

        for pdf_path in pdfs:
            try:
                log(f"PDF OCR {pdf_path.name}…")
                import pypdfium2 as pdfium

                doc = pdfium.PdfDocument(str(pdf_path))
                n = len(doc)
                doc.close()
                combined: List[str] = []
                for page in range(n):
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
                items.append(BatchItemResult(pdf_path, out_txt, True, f"{n} Seiten"))
            except Exception as e:
                items.append(BatchItemResult(pdf_path, None, False, str(e)))
        if not pdfs:
            items.append(BatchItemResult(folder, None, False, "Keine PDFs"))
        return BatchResult(items)

    return BatchResult([BatchItemResult(folder, None, False, f"Unbekannter Modus {mode}")])
