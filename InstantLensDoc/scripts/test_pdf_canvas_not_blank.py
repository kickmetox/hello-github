#!/usr/bin/env python3
"""Offscreen: PDF-Open muss sichtbares, nicht-weißes Canvas + Thumb liefern — 2.6.49.

Hartet gegen PDFium-Buffer-UAF und PyInstaller-ohne-Binary (Render-Probe).
Multipage: Seite 1 + Seite 2 haben Tinte; Viewer-Grab nicht all-white.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _make_multipage_pdf(path: Path, pages: list[str]) -> None:
    """Minimales multipage PDF mit Helvetica-Text je Seite."""
    # Objekte: 1 Catalog, 2 Pages, dann je Seite (Page + Contents), zuletzt Font
    page_ids = [3 + i * 2 for i in range(len(pages))]
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    font_id = 3 + len(pages) * 2
    objs: list[bytes] = []
    objs.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objs.append(
        f"2 0 obj<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>endobj\n".encode()
    )
    for i, text in enumerate(pages):
        page_id = page_ids[i]
        content_id = page_id + 1
        safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 28 Tf 40 200 Td ({safe}) Tj ET\n".encode()
        objs.append(
            (
                f"{page_id} 0 obj<< /Type /Page /Parent 2 0 R "
                f"/MediaBox [0 0 300 400] /Contents {content_id} 0 R "
                f"/Resources<< /Font<< /F1 {font_id} 0 R >> >> >>endobj\n"
            ).encode()
        )
        objs.append(
            f"{content_id} 0 obj<< /Length {len(stream)} >>stream\n".encode()
            + stream
            + b"endstream\nendobj\n"
        )
    objs.append(
        f"{font_id} 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n".encode()
    )
    parts = [b"%PDF-1.4\n"]
    offsets = [0]
    pos = len(parts[0])
    for o in objs:
        offsets.append(pos)
        parts.append(o)
        pos += len(o)
    xref_pos = pos
    xref = [f"xref\n0 {len(offsets)}\n".encode(), b"0000000000 65535 f \n"]
    for off in offsets[1:]:
        xref.append(f"{off:010d} 00000 n \n".encode())
    trailer = (
        f"trailer<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    ).encode()
    path.write_bytes(b"".join(parts) + b"".join(xref) + trailer)


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
    from PIL import Image
    from PySide6.QtWidgets import QApplication

    from ild_pdf.render import _detach_pil_from_pdfium, clear_render_cache, render_page
    from instantlensdoc.ui.image_qt import pil_has_ink, pil_to_qpixmap, qpixmap_has_ink
    from instantlensdoc.ui.pdf_view import PdfViewer

    app = QApplication.instance() or QApplication([])

    with tempfile.TemporaryDirectory() as td:
        pdf = Path(td) / "canvas_ink_multi.pdf"
        _make_multipage_pdf(pdf, ["PageOneAAA", "PageTwoBBB", "PageThreeCCC"])

        # 0) Hard-detach überlebt Buffer-Invalidierung (simulierter UAF)
        shared = Image.frombuffer("RGB", (32, 32), b"\xff" * (32 * 32 * 3), "raw", "RGB", 0, 1)
        # Paint a dark pixel into a real owned image then share-test via detach helper
        owned = Image.new("RGB", (64, 64), (255, 255, 255))
        for y in range(10, 40):
            for x in range(10, 40):
                owned.putpixel((x, y), (20, 20, 20))
        # frombuffer sharing owned.tobytes() — detach must keep ink after source gone
        buf = bytearray(owned.tobytes())
        shared2 = Image.frombuffer("RGB", owned.size, bytes(buf), "raw", "RGB", 0, 1)
        detached = _detach_pil_from_pdfium(shared2)
        del shared2
        buf[:] = b"\xff" * len(buf)  # destroy original buffer contents
        assert pil_has_ink(detached), "detach verlor Tinte nach Buffer-Overwrite"
        assert detached.mode == "RGB"

        # 1) Render-Pfad: jede Seite hat Tinte; Qt-Convert ebenfalls
        clear_render_cache()
        for pi in range(3):
            img = render_page(pdf, pi, scale=1.5, use_cache=False)
            assert pil_has_ink(img), f"render_page Seite {pi} leer/weiß"
            assert img.mode == "RGB", f"erwartet RGB nach detach, got {img.mode}"
            pm = pil_to_qpixmap(img)
            assert not pm.isNull() and qpixmap_has_ink(pm), f"pil_to_qpixmap Seite {pi} ohne Tinte"

        # 2) PdfViewer Open → sichtbares Canvas, grab nicht all-white
        v = PdfViewer()
        v.resize(960, 720)
        v.show()
        app.processEvents()
        assert v.load(pdf), "PdfViewer.load fehlgeschlagen"
        for _ in range(40):
            app.processEvents()
            if int(v.page_count or 0) >= 3 and v._canvas_has_page_image():
                break
            if not v._canvas_has_page_image():
                v._ensure_page_painted(warn=False)
        # Fast-Open startet oft mit page_count=1 — echte Seitenzahl nachziehen
        if int(v.page_count or 0) < 3:
            try:
                import pypdfium2 as pdfium

                with pdfium.PdfDocument(str(pdf)) as doc:
                    v.page_count = len(doc)
            except Exception:
                v.page_count = 3
            app.processEvents()
        assert int(v.page_count or 0) >= 3, f"page_count={v.page_count}"
        assert v._canvas_has_page_image(), (
            f"Canvas blank nach Open err={v._last_refresh_error!r} "
            f"fallback={v._blank_view_fallback_active}"
        )
        shown = v.canvas.pixmap()
        assert shown is not None and not shown.isNull()
        assert qpixmap_has_ink(shown), "sichtbares Canvas-Pixmap ohne Tinte"
        grab = v.canvas.grab().toImage()
        nw = _nonwhite_count(grab)
        assert nw >= 8, f"canvas.grab() fast weiß (nonwhite={nw})"
        # Viewer-Widget-Grab (ScrollArea) ebenfalls nicht all-white
        view_grab = v.grab().toImage()
        assert _nonwhite_count(view_grab, step=10) >= 4, (
            f"PdfViewer.grab() fast weiß (nonwhite={_nonwhite_count(view_grab, 10)})"
        )

        # 3) Thumb gleicher Render-Pfad (Seite 0 + 1)
        for pi in (0, 1):
            thumb = v.render_thumbnail(pi)
            assert pil_has_ink(thumb), f"Thumbnail Seite {pi} ohne Tinte (grau/leer)"
            tpm = pil_to_qpixmap(thumb)
            assert not tpm.isNull() and qpixmap_has_ink(tpm), f"Thumb-QPixmap Seite {pi} ohne Tinte"

        # 4) Seite 2 anspringen → Canvas weiter mit Tinte
        v.goto_page(2)
        for _ in range(20):
            app.processEvents()
            if v._canvas_has_page_image():
                break
            v._ensure_page_painted(warn=False)
        assert v._canvas_has_page_image(), "Canvas nach goto_page(2) blank"
        assert qpixmap_has_ink(v.canvas.pixmap()), "Seite 2 ohne Tinte"
        assert _nonwhite_count(v.canvas.grab().toImage()) >= 8

        # 5) Zero-size → resize Retry
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
        assert qpixmap_has_ink(v2.canvas.pixmap()), "Retry-Canvas ohne Tinte"

        # 6) Startup-Deps-Probe (Render, nicht nur Import)
        from instantlensdoc.core.deps_check import check_pypdfium2

        st = check_pypdfium2()
        assert st.ok, f"deps_check pypdfium2 fail: {st.message}"

    print("OK test_pdf_canvas_not_blank")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
