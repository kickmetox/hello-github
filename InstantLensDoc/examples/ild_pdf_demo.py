#!/usr/bin/env python3
"""
Beispiel: ild_pdf aus einem anderen Programm nutzen.

Aufruf (aus InstantLensDoc-Root):
  python examples/ild_pdf_demo.py
  python examples/ild_pdf_demo.py /pfad/zu/datei.pdf
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main(argv: list[str]) -> int:
    from PIL import Image

    from ild_pdf import (
        Annotation,
        AnnotationStore,
        AnnotationType,
        PdfDocument,
        __version__,
        bake_text_overlays,
        extract_page_image,
        extract_text_blocks,
        import_page_text_as_overlays,
        render_page,
        rotate_page,
    )

    print(f"ild_pdf {__version__}")

    if len(argv) > 1:
        pdf = Path(argv[1])
        if not pdf.exists():
            print(f"Datei fehlt: {pdf}", file=sys.stderr)
            return 1
        work = pdf
        cleanup = None
    else:
        cleanup = tempfile.TemporaryDirectory()
        td = Path(cleanup.name)
        # Mini-PDF erzeugen
        img = Image.new("RGB", (400, 300), "white")
        work = td / "demo.pdf"
        img.save(work, "PDF")
        # Text-Layer via pikepdf
        import pikepdf
        from pikepdf import Dictionary, Name, Stream

        with pikepdf.open(work, allow_overwriting_input=True) as doc:
            page = doc.pages[0]
            font = Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica)
            page[Name.Resources] = Dictionary(Font=Dictionary(F1=font))
            page[Name.Contents] = Stream(
                doc, b"BT /F1 16 Tf 40 220 Td (Demo fuer andere Programme) Tj ET"
            )
            doc.save(work)

    with PdfDocument(work) as doc:
        print(f"Seiten: {len(doc)}  Größe S1: {doc.page_size(0)}")

    img = render_page(work, 0, scale=1.5)
    out_png = work.with_name(work.stem + "_preview.png")
    img.save(out_png)
    print(f"Preview: {out_png}")

    blocks = extract_text_blocks(work, 0)
    print(f"Textblöcke: {len(blocks)}")
    for b in blocks[:5]:
        print(f"  · ({b.x:.0f},{b.y:.0f}) {b.text[:60]!r}")

    store = AnnotationStore(work)
    store.add(
        Annotation(
            0,
            AnnotationType.HIGHLIGHT,
            30,
            40,
            width=120,
            height=20,
            text="mark",
            color="#FFE066",
        )
    )
    store.add(
        Annotation(
            0,
            AnnotationType.ARROW,
            50,
            100,
            callout_x=180,
            callout_y=60,
            color="#8E44AD",
        )
    )
    store.add(
        Annotation(
            0,
            AnnotationType.MEASURE,
            20,
            200,
            callout_x=200,
            callout_y=200,
            color="#E67E22",
            text="Messung",
        )
    )
    imported = import_page_text_as_overlays(store, work, 0, scale=1.5)
    print(f"Overlays aus Text: {len(imported)}")
    sidecar = store.save(force=True)
    print(f"Sidecar: {sidecar.name} (v3, {len(store.annotations)} Annot.)")

    baked = work.with_name(work.stem + "_baked.pdf")
    bake_text_overlays(work, store, scale=1.5, out_path=baked)
    print(f"Eingebrannt: {baked.name}")

    extract_page_image(work, 0, work.with_name(work.stem + "_p1.png"), scale=1.0)
    # rotate nur auf Kopie, wenn Demo-Temp
    if cleanup is not None:
        rotate_page(work, 0, 90)
        print("Seite 0 um 90° gedreht (Temp-Demo)")

    print("OK — siehe ild_pdf/README.md für die API-Tabelle.")
    if cleanup is not None:
        cleanup.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
