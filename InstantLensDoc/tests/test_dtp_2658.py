"""DTP User-Spec: getrennte Rahmen, Weld, Symbole, Farbe, Preflight, SLA — 2.6.54."""

from __future__ import annotations

import zipfile
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

import pytest

from instantlensdoc.dtp.model import DtpDocument
from instantlensdoc.features.dtp_spec import (
    align_frames,
    convert,
    distribute_frames,
    export_pdf_versions,
    export_pdfx3,
    export_sla,
    format_number,
    from_cmyk,
    from_lab,
    from_rgb,
    from_spot,
    import_graphic,
    import_sla,
    run_dtp_preflight,
    snap_mm,
    snap_to_guide_mm,
    weld_frames,
)


PNG_1x1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_text_image_render_kinds_stay_separate(tmp_path: Path):
    doc = DtpDocument()
    t = doc.add_text_frame("Text")
    im = doc.add_image_frame("")
    rnd = doc.add_render_frame("")
    assert t.kind == "text" and im.kind == "image" and rnd.kind == "render"
    png = tmp_path / "x.png"
    png.write_bytes(PNG_1x1)
    doc.set_image(im.id, str(png))
    assert im.kind == "image"
    with pytest.raises(ValueError):
        doc.set_image(t.id, str(png))
    with pytest.raises(ValueError):
        doc.apply_font_attrs(im.id, family="serif")
    with pytest.raises(ValueError):
        doc.import_into_frame(im.id, str(png))
    sample = DtpDocument.sample("A5")
    kinds = {f.kind for f in sample.frames}
    assert "image" in kinds and "text" in kinds and "shape" in kinds


def test_weld_is_boolean_not_group():
    doc = DtpDocument()
    a = doc.add_shape("rectangle", x=10, y=10, width=40, height=20)
    b = doc.add_shape("rectangle", x=30, y=15, width=40, height=20)
    n = len(doc.frames)
    keeper = weld_frames(doc, [a.id, b.id])
    assert keeper.kind == "shape"
    assert keeper.path_kind == "weld"
    assert keeper.weld_path
    assert len(doc.frames) == n - 1
    t = doc.add_text_frame("x")
    with pytest.raises(ValueError):
        weld_frames(doc, [keeper.id, t.id])


def test_symbol_linked_clone_and_library():
    doc = DtpDocument()
    proto = doc.add_shape("rectangle", x=20, y=20, width=50, height=30, fill="#112233")
    sym = doc.register_symbol(proto.id, name="Marke")
    clone = doc.place_symbol(sym.id, x=80, y=90)
    assert clone.linked and clone.symbol_id == sym.id
    assert clone.x == 80 and clone.fill == "#112233"
    proto.fill = "#AABBCC"
    sym.proto = {k: v for k, v in proto.to_dict().items() if k not in ("id", "x", "y")}
    from instantlensdoc.dtp.assets import sync_linked_clones

    n = sync_linked_clones(doc, sym.id)
    assert n >= 1
    assert clone.fill == "#AABBCC"
    item = doc.library.add_file("/tmp/marke.svg", kind="svg")
    assert item.kind == "svg"
    assert any(s.id == sym.id for s in doc.library.symbols)


def test_align_distribute_snap_mm():
    doc = DtpDocument()
    g = doc.add_guide("vertical", snap_mm(80.0, 5.0, 1.0))
    x, y = snap_to_guide_mm(82.0, 10.0, [g], threshold_mm=1.5)
    assert abs(x - g.position_pt) < 0.01
    a = doc.add_shape("rectangle", x=10, y=10, width=20, height=10)
    b = doc.add_shape("rectangle", x=80, y=40, width=20, height=10)
    c = doc.add_shape("rectangle", x=140, y=5, width=20, height=10)
    align_frames([a, b, c], "left")
    assert a.x == b.x == c.x
    a.x, b.x, c.x = 10, 80, 140
    distribute_frames([a, b, c], "h")
    assert a.x < b.x < c.x
    doc.set_layer_blend("images", "multiply", opacity=0.5)
    ly = next(l for l in doc.layers if l.id == "images")
    assert ly.blend_mode == "multiply" and ly.opacity == 0.5


def test_numbering_kerning_notes_variables():
    assert format_number(12, "bengali") == "১২"
    assert format_number(12, "devanagari") == "१२"
    assert format_number(5, "thai") == "๕"
    assert format_number(7, "cjk") == "七"
    doc = DtpDocument(title="Buch", number_system="bengali")
    fr = doc.add_text_frame("Hallo {title}")
    note = doc.add_footnote(fr.id, "Eine Fußnote")
    assert note.kind == "footnote" and note.marker
    end = doc.add_endnote(fr.id, "Endnote")
    assert end.kind == "endnote"
    expanded = doc.expand_frame_variables(fr)
    assert "Buch" in expanded
    doc.apply_kerning(fr.id, {"Ha": -40})
    assert "Ha" in fr.kerning_pairs
    m = doc.masters[0]
    assert "১" in m.footer_for(1, 2, title="Buch", number_system="bengali")
    xref = doc.add_cross_ref(fr.id, "siehe S. {page}")
    from instantlensdoc.dtp.type_extras import resolve_cross_ref

    assert "S. 1" in resolve_cross_ref(xref, doc.frames)


def test_color_spaces_and_convert():
    rgb = from_rgb(1.0, 0.0, 0.0)
    assert rgb.space == "rgb" and rgb.hex.startswith("#")
    cmyk = convert(rgb, "cmyk")
    assert cmyk.space == "cmyk" and (cmyk.cmyk[1] > 0 or cmyk.cmyk[2] > 0)
    lab = from_lab(50.0, 20.0, -10.0)
    assert lab.space == "lab"
    spot = from_spot("red")
    assert spot.space == "spot" and spot.spot_name
    c2 = from_cmyk(0.0, 1.0, 1.0, 0.0)
    assert c2.space == "cmyk"


def test_preflight_missing_font_and_lowres(tmp_path: Path):
    png = tmp_path / "tiny.png"
    png.write_bytes(PNG_1x1)
    doc = DtpDocument()
    t = doc.add_text_frame("x")
    t.font_family = "DefinitelyMissingFontXYZ_2658"
    doc.add_image_frame(str(png), width=400, height=300)
    report = run_dtp_preflight(doc, min_dpi=150)
    kinds = {i.kind for i in report.issues}
    assert "font" in kinds
    assert "image" in kinds
    assert not report.ok


def test_sla_roundtrip(tmp_path: Path):
    doc = DtpDocument(title="SLA-Test")
    doc.add_text_frame("Wiederherstellen", x=40, y=50, width=200, height=40)
    doc.add_image_frame("/tmp/foto.tif", x=40, y=120, width=80, height=60)
    dest = tmp_path / "page.sla"
    export_sla(doc, dest)
    raw = dest.read_text(encoding="utf-8")
    assert "SCRIBUSUTF8NEW" in raw
    assert "NUM=" in raw
    loaded = import_sla(dest)
    texts = [f.text for f in loaded.frames if f.kind == "text"]
    assert any("Wiederherstellen" in (t or "") for t in texts)
    assert any(f.kind == "image" for f in loaded.frames)


def test_import_svg_tiff_idml_kra_ai(tmp_path: Path, qapp):
    svg = tmp_path / "a.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><text>Hallo SVG</text></svg>',
        encoding="utf-8",
    )
    tif = tmp_path / "a.tif"
    from PIL import Image

    Image.new("RGB", (8, 8), (20, 40, 60)).save(tif)

    idml = tmp_path / "a.idml"
    story = Element("Story")
    content = SubElement(story, "Content")
    content.text = "Hallo IDML Story"
    xml = b'<?xml version="1.0"?>\n' + tostring(story, encoding="utf-8")
    with zipfile.ZipFile(idml, "w") as zf:
        zf.writestr("Stories/story_u1.xml", xml)

    kra = tmp_path / "a.kra"
    with zipfile.ZipFile(kra, "w") as zf:
        zf.writestr("mergedimage.png", PNG_1x1)

    ai = tmp_path / "a.ai"
    ai.write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n")

    doc = DtpDocument()
    r_svg = import_graphic(doc, svg)
    assert r_svg["kind"] in ("svg", "image")
    assert any("Hallo SVG" in (f.text or "") for f in doc.frames if f.kind == "text")
    r_tif = import_graphic(doc, tif)
    assert r_tif["kind"] == "image"
    import_graphic(doc, idml)
    assert "IDML" in " ".join(f.text or "" for f in doc.frames if f.kind == "text")
    r_kra = import_graphic(doc, kra)
    assert r_kra["kind"] == "image"
    r_ai = import_graphic(doc, ai)
    assert r_ai["kind"] == "render"
    fr = doc.frame_by_id(r_ai["frames"][0])
    assert fr.kind == "render"


def test_pdfx3_and_versions(qapp, tmp_path: Path):
    doc = DtpDocument.sample("A5")
    dest = tmp_path / "x3.pdf"
    export_pdfx3(doc, dest)
    raw = dest.read_bytes()
    assert raw.startswith(b"%PDF")
    import pikepdf

    with pikepdf.open(dest) as pdf:
        assert "PDF/X-3" in str(pdf.docinfo.get("/GTS_PDFXVersion", ""))
        assert pdf.Root.get("/OutputIntents") is not None
    vers = export_pdf_versions(doc, tmp_path / "multi.pdf", versions=("1.4", "1.7"))
    assert vers["1.4"].is_file() and vers["1.7"].is_file()
    assert vers["1.4"].read_bytes()[:4] == b"%PDF"


def test_interactive_widgets_and_select_then_weld(qapp):
    from instantlensdoc.dtp.canvas import DtpPane

    doc = DtpDocument()
    field = doc.add_shape("rectangle", x=40, y=40, width=120, height=24)
    w = doc.add_widget(field.id, "combo", name="wahl", options=["A", "B"])
    assert w.kind == "combo" and w.options == ["A", "B"]
    a = doc.add_shape("rectangle", x=10, y=80, width=30, height=20)
    b = doc.add_shape("rectangle", x=25, y=90, width=30, height=20)
    pane = DtpPane(doc=doc)
    pane.show()
    pane.scene._items[a.id].setSelected(True)
    pane.scene._items[b.id].setSelected(True)
    welded = pane.weld_selected()
    assert welded is not None and welded.path_kind == "weld"
    pane.close()
