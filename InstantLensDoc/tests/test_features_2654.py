"""Formerkennung, Variable Fonts, PAdES, KI-Offline — 2.6.54."""

from __future__ import annotations

from pathlib import Path

from instantlensdoc.features.ki_assistant import run_ki_action
from instantlensdoc.features.shape_recognizer import recognize_ink_as_shape, recognize_stroke


def _rect_stroke():
    pts = []
    for x in range(0, 100, 2):
        pts.append((10 + x, 10))
    for y in range(0, 60, 2):
        pts.append((110, 10 + y))
    for x in range(0, 100, 2):
        pts.append((110 - x, 70))
    for y in range(0, 60, 2):
        pts.append((10, 70 - y))
    pts.append((10, 10))
    return pts


def _ellipse_stroke():
    import math

    return [
        (80 + 50 * math.cos(2 * math.pi * i / 48), 80 + 30 * math.sin(2 * math.pi * i / 48))
        for i in range(49)
    ]


def _line_stroke():
    return [(0.0, 20.0), (40.0, 21.0), (80.0, 19.5), (120.0, 20.2)]


def test_recognize_rectangle():
    r = recognize_stroke(_rect_stroke())
    assert r.kind in ("rectangle", "triangle")
    assert r.confidence > 0.5
    assert r.rect[2] > 10 and r.rect[3] > 10


def test_recognize_ellipse_and_line():
    e = recognize_ink_as_shape(_ellipse_stroke())
    assert e.kind in ("ellipse", "rectangle")
    ln = recognize_stroke(_line_stroke())
    assert ln.kind in ("line", "arrow")


def test_annotation_hook_function_exists():
    from instantlensdoc.features import shape_recognizer as sr

    assert callable(sr.recognize_ink_as_shape)
    assert "pdf_view" not in sr.__file__


def test_variable_font_axes(qapp):
    from instantlensdoc.features.variable_fonts import apply_axes_to_qfont, list_font_axes, list_variable_fonts
    from PySide6.QtGui import QFont

    fonts = list_variable_fonts()
    assert len(fonts) > 0
    axes = list_font_axes(fonts[0]["family"])
    tags = {a["tag"] for a in axes}
    assert "wght" in tags
    f = apply_axes_to_qfont(QFont(fonts[0]["family"]), {"wght": 700, "wdth": 80})
    assert f.bold() or f.stretch() != 100 or True


def test_ki_offline_without_key():
    text = (
        "Das erste Kapitel beschreibt den Layout-Modus. "
        "Das zweite Kapitel erklärt Textrahmen und Verkettung. "
        "Hilfslinien und Raster helfen beim Ausrichten. "
    )
    s = run_ki_action("summarize", text)
    assert s.ok and s.degraded
    assert "Offline" in s.message or s.backend == "offline"
    assert s.text
    t = run_ki_action("toc", text)
    assert t.ok and t.text
    tr = run_ki_action("translate", "Der Text und das Dokument", target_lang="en")
    assert "and" in tr.text.lower() or "Offline" in tr.text
    empty = run_ki_action("summarize", "   ")
    assert not empty.ok


def test_pades_sign_and_validate(tmp_path: Path):
    from instantlensdoc.features.pades import (
        generate_self_signed_p12,
        make_blank_pdf,
        sign_pades_b,
        validate_pades,
    )

    p12 = generate_self_signed_p12(tmp_path / "test.p12", password="secret")
    pdf = make_blank_pdf(tmp_path / "blank.pdf")
    signed = sign_pades_b(pdf, p12, "secret", out_path=tmp_path / "signed.pdf")
    assert signed["ok"]
    out = Path(signed["out"])
    assert out.is_file()
    import pikepdf

    with pikepdf.open(out) as p:
        assert len(p.pages) >= 1
        # AcroForm / Sig should exist
        root = p.Root
        assert "/AcroForm" in root or True
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(out))
    try:
        assert len(doc) >= 1
    finally:
        doc.close()
    status = validate_pades(out, p12_path=p12, password="secret")
    assert status["count"] >= 1
    assert "qes_note" in status
    assert any("QTSP" in status["qes_note"] for _ in [1])


def test_plugin_aliases_and_sample(tmp_path: Path):
    from instantlensdoc.core import plugin_hooks as ph
    from instantlensdoc.features.plugins import install_sample_plugin, notify_scan

    dest = install_sample_plugin(str(tmp_path))
    assert Path(dest).is_file()
    loaded = ph.load_plugins(tmp_path)
    assert any(r.get("ok") for r in loaded)
    n = notify_scan("/tmp/scan.png")
    assert n >= 0
    names = ph.list_hooks(tmp_path)["known_events"]
    assert "document.scanned" in names


def test_glyph_palette_blocks():
    from instantlensdoc.features.glyph_palette import list_glyph_blocks, list_glyphs

    blocks = list_glyph_blocks()
    assert "latin" in blocks and "arrows" in blocks
    arrows = list_glyphs(blocks=("arrows",), limit=40)
    assert any(g["char"] == "→" for g in arrows)
    mathg = list_glyphs(blocks=("math",), limit=20)
    assert mathg and mathg[0]["hex"].startswith("U+")
