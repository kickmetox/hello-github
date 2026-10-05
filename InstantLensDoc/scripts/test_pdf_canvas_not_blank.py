#!/usr/bin/env python3
"""Offscreen: PDF-Open muss sichtbares, nicht-weißes Canvas + Thumb liefern — 2.6.48."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


MINI_PDF = b"""%PDF-1.4
1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj
2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj
3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 400] /Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj
4 0 obj<< /Length 55 >>stream
BT /F1 36 Tf 50 200 Td (HelloPDF) Tj ET
endstream
endobj
5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000276 00000 n 
0000000382 00000 n 
trailer<< /Size 6 /Root 1 0 R >>
startxref
454
%%EOF
"""


def _nonwhite_count(qimg, step: int = 6) -> int:
    n = 0
    for y in range(0, qimg.height(), step):
        for x in range(0, qimg.width(), step):
            c = qimg.pixelColor(x, y)
            if c.alpha() < 8:
                continue
            if c.red() < 250 or c.green() < 250 or c.blue() < 250:
                n += 1
    return n


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from ild_pdf.render import clear_render_cache, render_page
    from instantlensdoc.ui.image_qt import pil_has_ink, pil_to_qpixmap, qpixmap_has_ink
    from instantlensdoc.ui.pdf_view import PdfViewer

    app = QApplication.instance() or QApplication([])

    with tempfile.TemporaryDirectory() as td:
        pdf = Path(td) / "canvas_ink.pdf"
        pdf.write_bytes(MINI_PDF)

        # 1) Render-Pfad: PIL hat Tinte auch nach BGRA-forced / close
        clear_render_cache()
        img = render_page(pdf, 0, scale=1.5, use_cache=False)
        assert pil_has_ink(img), "render_page lieferte leeres/weißes PIL"
        pm = pil_to_qpixmap(img)
        assert not pm.isNull() and qpixmap_has_ink(pm), "pil_to_qpixmap ohne Tinte"

        # 2) PdfViewer Open → sichtbares Canvas, grab nicht all-white
        v = PdfViewer()
        v.resize(960, 720)
        v.show()
        app.processEvents()
        assert v.load(pdf), "PdfViewer.load fehlgeschlagen"
        for _ in range(20):
            app.processEvents()
            if v._canvas_has_page_image():
                break
            v._ensure_page_painted(warn=False)
        assert v._canvas_has_page_image(), (
            f"Canvas blank nach Open err={v._last_refresh_error!r} "
            f"fallback={v._blank_view_fallback_active}"
        )
        shown = v.canvas.pixmap()
        assert shown is not None and not shown.isNull()
        assert qpixmap_has_ink(shown), "sichtbares Canvas-Pixmap ohne Tinte"
        grab = v.canvas.grab().toImage()
        assert _nonwhite_count(grab) >= 8, (
            f"canvas.grab() fast weiß (nonwhite={_nonwhite_count(grab)})"
        )

        # 3) Thumb gleicher Render-Pfad
        thumb = v.render_thumbnail(0)
        assert pil_has_ink(thumb), "Thumbnail ohne Tinte (grau/leer)"
        tpm = pil_to_qpixmap(thumb)
        assert not tpm.isNull() and qpixmap_has_ink(tpm), "Thumb-QPixmap ohne Tinte"

        # 4) Zero-size → resize Retry
        v2 = PdfViewer()
        v2.resize(1, 1)
        v2.show()
        app.processEvents()
        assert v2.load(pdf)
        v2.resize(1000, 800)
        app.processEvents()
        v2._schedule_paint_retry(delays_ms=(0, 10, 30))
        for _ in range(30):
            app.processEvents()
            if v2._canvas_has_page_image():
                break
        assert v2._canvas_has_page_image(), "Canvas nach resize/show-retry blank"

    print("OK test_pdf_canvas_not_blank")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
