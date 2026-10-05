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


def test_text_on_path_and_outlines():
    from instantlensdoc.dtp.text_path import (
        ellipse_polyline,
        path_length,
        place_text_on_path,
        polyline_for_kind,
    )

    pts = ellipse_polyline(200, 80)
    assert len(pts) > 16
    assert path_length(pts) > 100
    placed = place_text_on_path("InstantLens", pts, font_size=12)
    assert len(placed) >= 8
    assert placed[0]["char"] == "I"
    assert "angle" in placed[0]
    line = polyline_for_kind("line", 180, 40)
    assert line[0][0] < line[-1][0]
    doc = DtpDocument.sample("A5")
    fr = doc.add_text_frame("Pfad", page=0, x=40, y=40, width=160, height=70)
    doc.apply_text_on_path(fr.id, "ellipse")
    assert fr.path_kind == "ellipse"
    doc.convert_text_to_outlines(fr.id)
    assert fr.as_outlines is True
    dumped = DtpDocument.from_dict(doc.to_dict())
    again = dumped.frame_by_id(fr.id)
    assert again is not None and again.path_kind == "ellipse" and again.as_outlines


def test_clip_mask_and_live_fill():
    doc = DtpDocument()
    content = doc.add_shape("rectangle", x=20, y=20, width=120, height=80, fill="#FF0000")
    mask = doc.add_shape("ellipse", x=40, y=30, width=80, height=60, fill="#00FF00")
    doc.apply_clip_mask(content.id, mask.id)
    assert content.clip_id == mask.id
    doc.apply_live_fill(mask.id, kind="radial", fill="#4A90D9", fill_to="#111111", opacity=0.8)
    assert mask.fill_kind == "radial"
    assert mask.fill_to == "#111111"
    assert abs(mask.opacity - 0.8) < 1e-6
    doc.apply_drop_shadow(mask.id, dx=5, dy=6)
    assert mask.shadow and mask.shadow_dx == 5
    try:
        doc.apply_clip_mask(content.id, content.id)
        assert False, "self-clip should fail"
    except ValueError:
        pass


def test_glyph_insert_on_frame():
    from instantlensdoc.features.glyph_palette import insert_glyph, list_glyphs

    glyphs = list_glyphs(blocks=("latin",), limit=80)
    chars = {g["char"] for g in glyphs}
    assert "A" in chars
    currency = {g["char"] for g in list_glyphs(blocks=("currency",), limit=40)}
    assert "€" in currency
    assert insert_glyph("ab", "€", index=1) == "a€b"
    doc = DtpDocument()
    fr = doc.add_text_frame("Hallo", page=0)
    doc.insert_glyph(fr.id, "—")
    assert fr.text.endswith("—")


def test_export_pdf_path_clip_fill(qapp, tmp_path: Path):
    from instantlensdoc.dtp.export import export_pdf

    doc = DtpDocument.sample("A5")
    dest = tmp_path / "dtp-path-clip.pdf"
    export_pdf(doc, dest)
    assert dest.is_file() and dest.stat().st_size > 200
    import pikepdf

    with pikepdf.open(dest) as pdf:
        assert len(pdf.pages) >= 2
