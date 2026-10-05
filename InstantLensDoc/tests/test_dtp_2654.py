"""DTP-Modell, Verkettung, Guides, PDF-Export (QPdfWriter) — 2.6.54."""

from __future__ import annotations

from pathlib import Path

import pytest

from instantlensdoc.dtp.geometry import align_frames, distribute_frames, snap_point
from instantlensdoc.dtp.model import DtpDocument, DtpFrame
from instantlensdoc.dtp.presets import BOOK_PRESETS_MM, apply_book_preset


def test_book_presets_cover_user_formats():
    for name in ("Taschenbuch", "DINA5", "Roman", "Sachbuch", "DINA4", "Quadrat", "A4", "Letter"):
        assert name in BOOK_PRESETS_MM


def test_frames_linking_and_flow():
    doc = DtpDocument()
    apply_book_preset(doc, "A5")
    a = doc.add_text_frame("", width=120, height=60, x=40, y=40)
    b = doc.add_text_frame("", width=120, height=60, x=40, y=120)
    doc.link_frames(a.id, b.id)
    text = ("Wort " * 80).strip()
    filled = doc.flow_text(text, a)
    assert a.id in filled
    assert b.id in filled
    assert a.next_id == b.id
    assert len(a.text) > 0
    assert len(b.text) > 0


def test_guides_snap_and_columns():
    doc = DtpDocument()
    apply_book_preset(doc, "Taschenbuch")
    g = doc.add_guide("vertical", 80.0)
    x, y = snap_point(82.0, 10.0, grid_pt=0.0, guides=doc.guides, threshold=6.0)
    assert abs(x - 80.0) < 0.01
    frames = doc.create_column_chain(page=0, columns=2)
    assert len(frames) == 2
    assert frames[0].next_id == frames[1].id
    assert frames[1].x > frames[0].x


def test_align_distribute():
    a = DtpFrame(x=10, y=10, width=20, height=10)
    b = DtpFrame(x=80, y=40, width=20, height=10)
    c = DtpFrame(x=140, y=5, width=20, height=10)
    align_frames([a, b, c], "left")
    assert a.x == b.x == c.x == 10
    a.x, b.x, c.x = 10, 80, 140
    distribute_frames([a, b, c], "h")
    assert a.x < b.x < c.x


def test_sample_document_has_master_and_layers():
    doc = DtpDocument.sample("A5")
    assert doc.page_count >= 1
    assert doc.masters
    assert any(ly.name for ly in doc.layers)
    assert any(f.kind == "text" for f in doc.frames)


def test_export_pdf_valid(qapp, tmp_path: Path):
    from instantlensdoc.dtp.export import export_pdf

    doc = DtpDocument.sample("A5")
    dest = tmp_path / "dtp-sample.pdf"
    export_pdf(doc, dest)
    assert dest.is_file() and dest.stat().st_size > 200
    import pikepdf

    with pikepdf.open(dest) as pdf:
        assert len(pdf.pages) >= 1
        box = pdf.pages[0].mediabox
        assert float(box[2]) > 100
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(dest))
    try:
        assert len(pdf) >= 1
        page = pdf[0]
        bmp = page.render(scale=1.0)
        pil = bmp.to_pil()
        assert pil.size[0] > 50 and pil.size[1] > 50
    finally:
        pdf.close()


def test_export_docx_odt(qapp, tmp_path: Path):
    from instantlensdoc.dtp.export import export_docx, export_odt

    doc = DtpDocument.sample("A4")
    dx = export_docx(doc, tmp_path / "dtp.docx")
    od = export_odt(doc, tmp_path / "dtp.odt")
    assert dx.is_file() and dx.stat().st_size > 100
    assert od.is_file() and od.stat().st_size > 100


def test_envelope_and_extrude_on_frame(qapp):
    from instantlensdoc.dtp.envelope import envelope_corners_default, warp_painter_path
    from instantlensdoc.dtp.extrude import extrude_path, path_for_shape
    from instantlensdoc.dtp.model import EnvelopeMesh, ExtrudeSpec
    from PySide6.QtGui import QPainterPath

    doc = DtpDocument.sample("A5")
    fr = next(f for f in doc.frames if f.kind == "shape")
    fr.envelope = EnvelopeMesh(corners=envelope_corners_default(fr.width, fr.height))
    fr.extrude = ExtrudeSpec(depth=12, angle_deg=30)
    path = path_for_shape(fr.shape, fr.width, fr.height)
    warped = warp_painter_path(path, width=fr.width, height=fr.height, corners=fr.envelope.corners)
    assert warped.elementCount() > 0
    ext = extrude_path(path, depth=12, angle_deg=30)
    assert ext["faces"]


def test_dtp_pane_offscreen(qapp):
    from instantlensdoc.dtp.canvas import DtpPane

    pane = DtpPane(doc=DtpDocument.sample("A5"))
    pane.resize(1100, 800)
    pane.show()
    pane.add_text_frame()
    qapp.processEvents()
    pix = pane.grab()
    assert pix.width() > 100
    pane.close()
