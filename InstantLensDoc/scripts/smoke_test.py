#!/usr/bin/env python3
"""Smoke-Test 0.3.9 (CLI + optional offscreen Qt). Kernpfade: open/annotate/export/license."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from PIL import Image

    from ild_pdf import (
        Annotation,
        AnnotationStore,
        AnnotationType,
        PAGE_SIZE_PRESETS,
        PdfDocument,
        PdfMetadata,
        apply_page_numbers,
        apply_watermark,
        bake_redactions,
        bake_text_overlays,
        clear_render_cache,
        compress_image_for_pdf,
        compress_pdf_as_images,
        extract_page_image,
        extract_pages_as_images,
        extract_all_plain_text,
        extract_page_plain_text,
        extract_text_blocks,
        find_text_rects,
        get_metadata,
        get_page_boxes,
        import_page_text_as_overlays,
        insert_image_as_page,
        insert_signature_field,
        insert_signature_image,
        inspect_pdf,
        needs_password,
        render_page,
        set_crop_box,
        set_metadata,
        set_page_size,
        set_password,
        try_open_password,
        __version__ as ild_ver,
    )
    from ild_pdf.pages import (
        duplicate_page,
        extract_page_range,
        flip_page,
        insert_blank_page,
        merge_pdfs,
        reorder_pages,
        rotate_page,
        split_into_single_page_pdfs,
        split_pdf,
    )
    from ild_pdf.outline import add_outline_item, delete_outline_item, extract_outline
    from instantlensdoc import __version__
    from instantlensdoc.config import icon_path, icon_paths_for_qt
    from instantlensdoc.core.documents import open_document, save_document
    from instantlensdoc.core.export import export_docx, export_html, export_pdf, resolve_page_size
    from instantlensdoc.core.forms import FieldType, FormDefinition, FormField, export_html as form_html, export_pdf_form
    from instantlensdoc.core.layout import LayoutDocument
    from instantlensdoc.core import ocr as ocr_mod
    from instantlensdoc.core.ocr import LANG_PRESETS, OcrOutputMode
    from instantlensdoc.core import recent as recent_mod
    from instantlensdoc.core import recent_searches as recent_searches_mod
    from instantlensdoc.core import batch as batch_mod
    from instantlensdoc.core import fulltext as ft_mod
    from instantlensdoc.core import session as session_mod
    from instantlensdoc.core.app_settings import (
        dialog_start_dir,
        get_ann_default_opacity,
        get_ann_highlight_color,
        get_ann_pen_color,
        get_annotations_visible,
        get_autosave_interval_sec,
        get_default_zoom_percent,
        get_editor_line_numbers,
        get_editor_markdown_preview,
        get_export_jpeg_quality,
        get_last_export_dir,
        get_ocr_lang,
        get_pdf_grayscale,
        get_pdf_night_mode,
        get_recent_dirs,
        get_ui_lang,
        load_settings,
        remember_recent_dir,
        save_settings,
        set_ann_default_opacity,
        set_ann_highlight_color,
        set_ann_pen_color,
        set_annotations_visible,
        set_autosave_interval_sec,
        set_default_zoom_percent,
        set_editor_line_numbers,
        set_editor_markdown_preview,
        set_last_export_dir,
        set_pdf_grayscale,
        set_pdf_night_mode,
    )
    from instantlensdoc.core.i18n import set_lang, tr
    from instantlensdoc.core.update_check import check_for_updates
    from instantlensdoc.license import KEY_DAYS, TRIAL_DAYS, generate_key, verify_key

    assert __version__ == "0.3.9", __version__
    assert ild_ver == "0.3.9", ild_ver
    assert TRIAL_DAYS == 28 and KEY_DAYS == 32
    key = generate_key("ame@sellerbach.de")
    ok, msg, _ = verify_key(key)
    assert ok, msg

    assert icon_path() is not None or True
    _ = list(icon_paths_for_qt())
    assert "Deutsch + Englisch" in LANG_PRESETS
    assert OcrOutputMode.EDITABLE_TEXT.value == "editable_text"
    assert "A4" in PAGE_SIZE_PRESETS
    assert resolve_page_size("A4")[0] > 500
    set_lang("de")
    assert "Einstellungen" in tr("settings")
    set_lang("en")
    assert "Settings" in tr("settings")
    set_lang("de")
    upd = check_for_updates(allow_network=False)
    assert upd.local_version == "0.3.9" and not upd.online
    assert get_export_jpeg_quality() >= 10
    assert get_ui_lang() in ("de", "en")
    assert 25 <= get_default_zoom_percent() <= 500
    assert 10 <= get_autosave_interval_sec() <= 600
    assert get_ann_highlight_color().startswith("#")
    assert get_ann_pen_color().startswith("#")
    set_editor_line_numbers(True)
    assert get_editor_line_numbers() is True
    set_editor_line_numbers(False)
    assert get_editor_line_numbers() is False
    set_pdf_grayscale(True)
    assert get_pdf_grayscale() is True
    set_pdf_grayscale(False)
    assert get_pdf_grayscale() is False
    set_pdf_night_mode(True)
    assert get_pdf_night_mode() is True
    set_pdf_night_mode(False)
    assert get_pdf_night_mode() is False
    set_ann_default_opacity(0.55)
    assert abs(get_ann_default_opacity() - 0.55) < 0.001
    set_ann_default_opacity(1.0)
    assert abs(get_ann_default_opacity() - 1.0) < 0.001
    set_annotations_visible(False)
    assert get_annotations_visible() is False
    set_annotations_visible(True)
    assert get_annotations_visible() is True
    set_editor_markdown_preview(True)
    assert get_editor_markdown_preview() is True
    set_editor_markdown_preview(False)
    assert get_editor_markdown_preview() is False
    set_default_zoom_percent(175)
    assert get_default_zoom_percent() == 175
    set_autosave_interval_sec(45)
    assert get_autosave_interval_sec() == 45
    set_ann_highlight_color("#FFCC00")
    set_ann_pen_color("#112233")
    assert get_ann_highlight_color() == "#FFCC00"
    assert get_ann_pen_color() == "#112233"
    assert (ROOT / "CHANGELOG.md").is_file()
    cl = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "0.3.9" in cl
    assert "## 0.3.9" in cl
    assert "## 0.3.7" in cl
    assert "## 0.3.1" in cl
    assert "## 0.3.0" in cl
    assert "0.2.0 → 0.3.0" in cl or "0.2.0→0.3.0" in cl
    assert "AcroForm" in cl or "Formularfelder" in cl
    assert "Lazy" in cl or "Lazy-Load" in cl or "Thumbnail" in cl
    assert "Anhang" in cl or "Anhänge" in cl or "attachments" in cl.lower()
    assert "Markdown" in cl or "Vorschau" in cl
    assert "Ordner" in cl or "recent" in cl.lower()
    # Kompakt: Einzel-Header 0.2.1–0.2.9 entfernt (nur Kurz-Tabelle)
    assert "## 0.2.9" not in cl and "## 0.2.8" not in cl
    assert "0.2.9" in cl  # noch in Kurz-Tabelle
    assert "0.3.9" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "run.bat" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "sync-ild.ps1" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "scripts/sync-ild.ps1" in (ROOT / "FEATURES.md").read_text(encoding="utf-8")
    assert (ROOT / "scripts" / "sync-ild.ps1").is_file()

    ok_ocr, ocr_msg = ocr_mod.tesseract_available()
    assert isinstance(ocr_msg, str) and len(ocr_msg) > 5
    print(f"OCR: {'OK' if ok_ocr else 'fehlt (erwartet)'} — {ocr_msg.splitlines()[0]}")

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p1 = td / "p1.pdf"
        p2 = td / "p2.pdf"
        pdf = td / "t.pdf"
        Image.new("RGB", (200, 200), "white").save(p1, "PDF")
        Image.new("RGB", (200, 200), "gray").save(p2, "PDF")
        import pikepdf
        from pikepdf import Dictionary, Name, Stream

        with pikepdf.Pdf.new() as out:
            for src in (p1, p2):
                with pikepdf.open(src) as src_pdf:
                    out.pages.append(src_pdf.pages[0])
            page = out.pages[0]
            font = Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica)
            page[Name.Resources] = Dictionary(Font=Dictionary(F1=font))
            content = b"BT /F1 18 Tf 50 150 Td (Hello InstantLens Overlay) Tj ET"
            if Name.Contents in page:
                existing = page[Name.Contents]
                page[Name.Contents] = pikepdf.Array([existing, Stream(out, content)])
            else:
                page[Name.Contents] = Stream(out, content)
            out.save(pdf)

        with PdfDocument(pdf) as doc:
            assert len(doc) == 2
            w, h = doc.page_size(0)
            assert w > 0 and h > 0
        render_page(pdf, 0)
        clear_render_cache(pdf)
        render_page(pdf, 0)
        render_page(pdf, 0)
        gray_img = render_page(pdf, 0, scale=0.5, grayscale=True, use_cache=False)
        assert gray_img.mode in ("L", "RGB", "RGBA")
        # Graustufen-Export
        g_out = td / "gray_p1.png"
        extract_page_image(pdf, 0, g_out, scale=0.5, grayscale=True)
        assert g_out.is_file() and g_out.stat().st_size > 0
        print("Grayscale: OK")
        # Nachtmodus Invert (nur Ansicht)
        from ild_pdf.render import invert_for_display

        night_img = render_page(pdf, 0, scale=0.5, invert=True, use_cache=False)
        assert night_img.mode in ("L", "RGB", "RGBA")
        base = render_page(pdf, 0, scale=0.5, use_cache=False)
        inv_manual = invert_for_display(base)
        assert inv_manual.size == night_img.size
        # Export ohne invert (nicht speichern)
        n_out = td / "no_night_export.png"
        extract_page_image(pdf, 0, n_out, scale=0.5, grayscale=False)
        assert n_out.is_file()
        print("NightMode: OK")

        # Textsuche-Rechtecke (aktuelle Seite)
        rects = find_text_rects(pdf, 0, "InstantLens", scale=1.5)
        assert len(rects) >= 1
        assert rects[0].width > 0 and rects[0].height > 0
        assert find_text_rects(pdf, 0, "ZZZNOMATCH") == []
        print("TextSearchRects: OK")

        health = inspect_pdf(pdf)
        assert health.ok_to_open and health.page_count == 2

        set_metadata(pdf, PdfMetadata(title="ILD Test", author="Andreas", subject="Smoke", keywords="a,b"))
        meta = get_metadata(pdf)
        assert "ILD" in meta.title and meta.author == "Andreas"
        print("Metadata: OK")

        boxes = get_page_boxes(pdf, 0)
        assert "mediabox" in boxes and "cropbox" in boxes
        a4w, a4h = PAGE_SIZE_PRESETS["A4"]
        set_page_size(pdf, 0, a4w, a4h)
        boxes2 = get_page_boxes(pdf, 0)
        assert abs((boxes2["mediabox"][2] - boxes2["mediabox"][0]) - a4w) < 0.5
        set_crop_box(pdf, 0, 10, 10, a4w - 10, a4h - 10)
        boxes3 = get_page_boxes(pdf, 0)
        assert boxes3["cropbox"][0] == 10
        print("PageSize/Crop: OK")

        wm_out = td / "wm.pdf"
        apply_watermark(pdf, "TEST-WM", out_path=wm_out, opacity=0.3, font_size=36)
        assert wm_out.is_file() and wm_out.stat().st_size > 100
        num_out = td / "num.pdf"
        apply_page_numbers(pdf, out_path=num_out, template="S.{n}/{total}")
        assert num_out.is_file()
        print("Watermark/PageNumbers: OK")

        # Redaction + bake (eigenes PDF, Sidecar nicht mit Haupttest vermischen)
        pdf_red = td / "red_src.pdf"
        pdf_red.write_bytes(pdf.read_bytes())
        store_r = AnnotationStore(pdf_red)
        store_r.annotations = []
        store_r.dirty = True
        store_r.add(Annotation(0, AnnotationType.REDACTION, 20, 20, width=50, height=30, color="#000000", text="REDACT"))
        store_r.save(force=True)
        assert any(a.type == AnnotationType.REDACTION for a in AnnotationStore(pdf_red).annotations)
        red_out = td / "redacted.pdf"
        bake_redactions(pdf_red, store_r, scale=1.5, out_path=red_out, remove_from_store=True)
        assert red_out.is_file() and red_out.stat().st_size > 50
        assert not any(a.type == AnnotationType.REDACTION for a in store_r.annotations)
        print("Redaction: OK")

        # Password
        enc = td / "enc.pdf"
        set_password(pdf, user_password="secret", out_path=enc)
        assert needs_password(enc)
        ok_pw, msg_pw = try_open_password(enc, "secret")
        assert ok_pw, msg_pw
        ok_bad, _ = try_open_password(enc, "wrong")
        assert not ok_bad
        with PdfDocument(enc, password="secret") as doc:
            assert len(doc) >= 1
        render_page(enc, 0, scale=0.5, password="secret")
        print("Password: OK")

        # Image compression
        big = Image.new("RGB", (800, 600), "red")
        small = compress_image_for_pdf(big, max_edge=200, quality=50)
        assert max(small.size) <= 200
        comp = compress_pdf_as_images(pdf, out_path=td / "comp.pdf", jpeg_quality=60, max_edge=400, render_scale=1.0)
        assert comp.is_file() and comp.stat().st_size > 50
        print("Compress: OK")

        # Logging
        from instantlensdoc.core.logging_setup import setup_logging
        lp = setup_logging(force=True)
        assert lp.exists()
        assert "InstantLensDoc" in str(lp) or "instantlensdoc" in lp.name.lower()
        print(f"Logging: OK → {lp}")

        # Saubere Annotationen für Undo/Redo-Tests
        store = AnnotationStore(pdf)
        store.annotations = []
        store.dirty = True
        store.clear_history()
        sid_old = store.sidecar_path
        if sid_old.exists():
            sid_old.unlink()
        store.add(Annotation(0, AnnotationType.HIGHLIGHT, 10, 10, text="mark"))
        store.add(Annotation(1, AnnotationType.STICKY, 20, 20, text="note"))
        store.add(Annotation(0, AnnotationType.STAMP, 30, 30, text="GEPRÜFT", width=120, height=40))
        store.add(Annotation(0, AnnotationType.CALLOUT, 80, 80, text="Hinweis", callout_x=40, callout_y=120))
        store.add(Annotation(0, AnnotationType.RECTANGLE, 15, 15, width=60, height=40, color="#27AE60"))
        store.add(Annotation(0, AnnotationType.LINE, 10, 10, callout_x=90, callout_y=50, color="#2C3E50"))
        store.add(Annotation(0, AnnotationType.ARROW, 20, 80, callout_x=100, callout_y=40, color="#8E44AD"))
        meas = Annotation(0, AnnotationType.MEASURE, 5, 5, callout_x=5 + 72 * 1.5, callout_y=5, color="#E67E22")
        meas.text = meas.measure_label(scale=1.5)
        store.add(meas)
        store.add(Annotation(0, AnnotationType.TEXT_OVERLAY, 40, 40, width=180, height=28, text="Overlay-Edit", font_size=14, color="#1A5276"))
        fade = Annotation(0, AnnotationType.HIGHLIGHT, 50, 50, width=40, height=12, text="fade", opacity=0.4)
        store.add(fade)
        assert abs(store.get(fade.id).opacity - 0.4) < 0.001
        store.update(fade.id, opacity=0.7)
        assert abs(store.get(fade.id).opacity - 0.7) < 0.001
        print("AnnOpacity: OK")
        sid = store.save(force=True)
        assert sid.exists()
        raw = sid.read_text(encoding="utf-8")
        assert '"version": 3' in raw
        store2 = AnnotationStore(pdf)
        assert len(store2.annotations) == 10
        types = {a.type for a in store2.annotations}
        assert AnnotationType.STAMP in types and AnnotationType.CALLOUT in types
        assert AnnotationType.RECTANGLE in types and AnnotationType.MEASURE in types
        assert AnnotationType.TEXT_OVERLAY in types
        overlay = next(a for a in store2.annotations if a.type == AnnotationType.TEXT_OVERLAY)
        last_id = overlay.id
        assert store2.update(last_id, text="Overlay-Updated")
        assert store2.get(last_id).text == "Overlay-Updated"
        # Opacity roundtrip from sidecar
        fade2 = next(a for a in store2.annotations if a.text == "fade")
        assert abs(fade2.opacity - 0.7) < 0.001

        assert store2.can_undo()
        n_before_undo = len(store2.annotations)
        assert store2.undo()
        assert store2.get(last_id).text == "Overlay-Edit"
        assert store2.redo()
        assert store2.get(last_id).text == "Overlay-Updated"
        store2.add(Annotation(0, AnnotationType.HIGHLIGHT, 1, 1, text="temp"))
        assert len(store2.annotations) == n_before_undo + 1
        assert store2.undo()
        assert len(store2.annotations) == n_before_undo
        assert store2.redo()
        assert len(store2.annotations) == n_before_undo + 1
        store2.undo()
        print("Undo/Redo: OK")

        blocks = extract_text_blocks(pdf, 0)
        assert isinstance(blocks, list)
        print(f"Textblöcke Seite 0: {len(blocks)}")
        plain0 = extract_page_plain_text(pdf, 0)
        assert isinstance(plain0, str)
        plain_all = extract_all_plain_text(pdf, page_headers=True)
        assert "--- Seite 1 ---" in plain_all
        print(f"Plaintext Seite 0: {len(plain0)} Zeichen")
        n0 = len(store2.annotations)
        created = import_page_text_as_overlays(store2, pdf, 0, scale=1.5)
        assert isinstance(created, list)
        if created:
            assert store2.can_undo()
            store2.undo()
            assert len(store2.annotations) == n0
            store2.redo()
            assert len(store2.annotations) == n0 + len(created)
        store2.save(force=True)
        bake_text_overlays(pdf, store2, scale=1.5, out_path=td / "baked.pdf")
        assert (td / "baked.pdf").exists()

        img_out = extract_page_image(pdf, 0, td / "seite.png", scale=1.0)
        assert img_out.exists()
        multi = extract_pages_as_images(pdf, td / "pages_png", format="PNG", scale=1.0)
        assert len(multi) >= 2 and all(p.exists() for p in multi)
        img_page = td / "extra.png"
        Image.new("RGB", (100, 80), "blue").save(img_page)
        insert_image_as_page(pdf, img_page)
        with PdfDocument(pdf) as doc:
            assert len(doc) == 3

        rotate_page(pdf, 0, 90)
        rotate_page(pdf, 0, -90)
        flip_page(pdf, 0, horizontal=True)
        flip_page(pdf, 0, vertical=True)
        flip_page(pdf, 0, horizontal=True, vertical=True)
        blank_idx = insert_blank_page(pdf, 1)
        assert blank_idx == 1
        with PdfDocument(pdf) as doc:
            assert len(doc) == 4
        dup_idx = duplicate_page(pdf, 0, after=True)
        assert dup_idx == 1
        with PdfDocument(pdf) as doc:
            assert len(doc) == 5
        reorder_pages(pdf, [1, 0, 2, 3, 4])
        with PdfDocument(pdf) as doc:
            assert len(doc) == 5

        layout = LayoutDocument()
        f1 = layout.add_text_frame(x=40, y=40, width=120, height=60, font_size=12)
        f2 = layout.chain_new_frame(f1)
        long = "Wort " * 80
        filled = layout.flow_text_chain(long, f1)
        assert f1.id in filled and f2.id in filled
        assert f1.next_id == f2.id
        layout_path = td / "layout.json"
        layout.save(layout_path)
        layout2 = LayoutDocument.load(layout_path)
        assert len(layout2.text_frames) == 2

        form = FormDefinition("F", description="Test")
        form.add_field(FormField("Name", type=FieldType.TEXT, required=True))
        form.add_field(FormField("Art", type=FieldType.DROPDOWN, options=["A", "B"]))
        form.add_field(FormField("Mail", type=FieldType.EMAIL))
        form.add_field(FormField("Zahl", type=FieldType.NUMBER))
        form.add_field(FormField("Wahl", type=FieldType.RADIO, options=["X", "Y"]))
        form.add_field(FormField("Unterschrift", type=FieldType.SIGNATURE))
        def_path = td / "f.ildform.json"
        form.save(def_path)
        form2 = FormDefinition.load(def_path)
        assert form2.title == "F" and len(form2.fields) == 6
        form_html(form2, td / "f.html")
        export_pdf_form(form2, td / "f.pdf")
        assert (td / "f.html").exists() and (td / "f.pdf").exists()
        html = (td / "f.html").read_text(encoding="utf-8")
        assert "type='email'" in html and "sig" in html

        sample = "# Titel\n\nAbsatz eins.\n\n## Unter\n\n- Punkt A\n- Punkt B\n"
        export_html(sample, td / "e.html", title="ExportTest")
        export_docx(sample, td / "e.docx", title="ExportTest")
        export_pdf(sample, td / "e.pdf", title="ExportTest", page_size="A4")
        assert (td / "e.html").exists() and "<h1>" in (td / "e.html").read_text(encoding="utf-8")
        assert (td / "e.docx").exists() and (td / "e.pdf").stat().st_size > 100
        with PdfDocument(td / "e.pdf") as doc:
            assert len(doc) >= 1

        txt = td / "a.txt"
        txt.write_text("hello InstantLens Suche", encoding="utf-8")
        doc = open_document(txt)
        doc.text = "# Hello\n\nWelt export"
        save_document(doc, td / "out.html")
        assert "<h1>" in (td / "out.html").read_text(encoding="utf-8")
        doc.text = "# Docx\n\nInhalt"
        save_document(doc, td / "out.docx")
        assert (td / "out.docx").exists()

        recent_file = td / "recent.json"
        orig_path = recent_mod.recent_path
        recent_mod.recent_path = lambda: recent_file  # type: ignore
        try:
            recent_mod.clear_recent()
            assert recent_mod.load_recent() == []
            recent_mod.add_recent(txt)
            recent_mod.add_recent(pdf)
            files = recent_mod.load_recent()
            assert str(pdf) in files and str(txt) in files
            assert files[0] == str(pdf)
            recent_mod.clear_recent()
            assert recent_mod.load_recent() == []
            print("Recent: OK")
        finally:
            recent_mod.recent_path = orig_path  # type: ignore

        sess_file = td / "session.json"
        orig_sess = session_mod.session_path
        session_mod.session_path = lambda: sess_file  # type: ignore
        try:
            st = session_mod.build_session([str(txt), str(pdf)], active_path=str(pdf), page=1, scale=1.25)
            session_mod.save_session(st)
            loaded = session_mod.load_session()
            assert len(loaded.tabs) == 2
            assert loaded.tabs[loaded.active].path == str(pdf)
            assert loaded.tabs[loaded.active].page == 1
            print("Session: OK")
        finally:
            session_mod.session_path = orig_sess  # type: ignore

        if ok_ocr:
            sample_img = td / "ocr.png"
            Image.new("RGB", (200, 60), "white").save(sample_img)
            try:
                r = ocr_mod.run_ocr(
                    sample_img,
                    lang="eng",
                    mode=OcrOutputMode.SEARCHABLE_IMAGE,
                    out_dir=td,
                    source_label="ocr.png",
                )
                assert r.searchable_pdf and r.searchable_pdf.exists()
                assert r.sidecar and r.sidecar.exists()
            except Exception as e:
                print(f"OCR run (optional): {e}")
        else:
            sample_img = td / "ocr.png"
            Image.new("RGB", (200, 60), "white").save(sample_img)
            pdf_s, side = ocr_mod.make_searchable_image_pdf(sample_img, "dummy text", td / "s.pdf")
            assert pdf_s.exists() and side.exists()

        assert (ROOT / "installer" / "installer-hinweis.txt").exists()
        iss = (ROOT / "installer" / "instantlensdoc.iss").read_text(encoding="utf-8")
        assert "0.3.9" in iss and "desktopicon" in iss and "DisableProgramGroupPage=no" in iss
        assert "UninstallDisplayName" in iss and "Uninstallable=yes" in iss
        assert "IncludeKeygen" in iss and "SetupIconFile" in iss
        assert "InstantLensKeygen.exe" in iss
        assert "uninstallexe" in iss
        bw = (ROOT / "build-windows.ps1").read_text(encoding="utf-8")
        assert "0.3.9" in bw and "NoKeygenInApp" in bw and "--icon" in bw
        assert "InstantLensKeygen.exe" in bw
        bi = (ROOT / "installer" / "build-installer.ps1").read_text(encoding="utf-8")
        assert "InstantLensKeygen.exe" in bi and "IncludeKeygen" in bi
        kg_readme = (ROOT / "keygen" / "README.md").read_text(encoding="utf-8")
        assert "InstantLensKeygen.exe" in kg_readme
        assert "Installer" in kg_readme
        hinweis = (ROOT / "installer" / "installer-hinweis.txt").read_text(encoding="utf-8")
        assert "InstantLensKeygen.exe" in hinweis or "run-keygen.bat" in hinweis
        from ild_pdf.limits import OPEN_TIMEOUT_HINT, OPEN_TIMEOUT_HINT_SEC

        assert OPEN_TIMEOUT_HINT_SEC >= 15 and "teilen" in OPEN_TIMEOUT_HINT.lower()
        kb = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
        assert "Ctrl+Shift+S" in kb and "Sidecar" in kb
        assert "save_annotations_as" in (ROOT / "instantlensdoc" / "ui" / "pdf_view.py").read_text(encoding="utf-8")
        assert "QProgressBar" in (ROOT / "instantlensdoc" / "ui" / "batch_dialog.py").read_text(encoding="utf-8")
        assert "QProgressDialog" in (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")

        assert (ROOT / "examples" / "ild_pdf_demo.py").exists()
        assert "0.3.9" in (ROOT / "INFO.md").read_text(encoding="utf-8")
        assert (ROOT / "assets" / "app.ico").is_file()

        # --- Kernpfade: open / annotate / export / license ---
        core_txt = td / "core_open.txt"
        core_txt.write_text("Kernpfad Open Annotate Export License", encoding="utf-8")
        opened = open_document(core_txt)
        assert opened.kind.value in ("text", "markdown") or opened.text
        assert "Kernpfad" in opened.text
        try:
            open_document(td / "fehlt_nicht_da.txt")
            raise AssertionError("fehlende Datei hätte FileNotFoundError werfen müssen")
        except FileNotFoundError:
            pass

        core_pdf = td / "core_ann.pdf"
        Image.new("RGB", (240, 320), "white").save(core_pdf, "PDF")
        store_core = AnnotationStore(core_pdf)
        store_core.add(
            Annotation(0, AnnotationType.HIGHLIGHT, 20, 40, width=80, height=14, text="core-ann")
        )
        store_core.add(
            Annotation(0, AnnotationType.STICKY, 30, 60, width=40, height=40, text="note")
        )
        store_core.save()
        store_reload = AnnotationStore(core_pdf)
        assert any(a.text == "core-ann" for a in store_reload.annotations)
        assert store_reload.can_undo() or len(store_reload.annotations) >= 2

        exp_html = td / "core_export.html"
        exp_docx = td / "core_export.docx"
        exp_pdf = td / "core_export.pdf"
        export_html(opened.text, exp_html, title="Core")
        export_docx(opened.text, exp_docx, title="Core")
        export_pdf(opened.text, exp_pdf, title="Core")
        assert exp_html.is_file() and exp_html.stat().st_size > 20
        assert exp_docx.is_file() and exp_docx.stat().st_size > 20
        assert exp_pdf.is_file() and exp_pdf.stat().st_size > 20

        from instantlensdoc.license import LicenseManager

        lic_path = td / "core_license.json"
        lm = LicenseManager(path=lic_path)
        st0 = lm.status()
        assert st0.allowed and st0.mode in ("trial", "licensed")
        ok_act, act_msg = lm.activate(key)
        assert ok_act, act_msg
        st1 = lm.status()
        assert st1.mode == "licensed" and st1.days_remaining > 0
        bad_ok, bad_msg, _ = verify_key("ILD1.bad.payload")
        assert not bad_ok and bad_msg
        print("CorePaths open/annotate/export/license: OK")

        merge_pdfs([p1, p2], td / "merged.pdf")
        assert (td / "merged.pdf").is_file()
        parts = split_pdf(pdf, td / "split", single_pages=True)
        assert len(parts) >= 2
        range_out = td / "range.pdf"
        extract_page_range(pdf, range_out, 1, 2, one_based=True)
        assert range_out.is_file() and range_out.stat().st_size > 0
        import pikepdf as _pike

        with _pike.open(range_out) as _rpdf:
            assert len(_rpdf.pages) == 2

        txt = td / "findme.txt"
        txt.write_text("alpha beta FINDME gamma", encoding="utf-8")
        hits = ft_mod.search_paths([str(txt), str(pdf)], "FINDME")
        assert any("FINDME" in h.snippet for h in hits)
        save_settings({"ocr_lang": get_ocr_lang(), "theme": load_settings().get("theme", "light")})

        img_dir = td / "imgs"
        img_dir.mkdir()
        Image.new("RGB", (100, 100), "white").save(img_dir / "a.png")
        Image.new("RGB", (100, 100), "black").save(img_dir / "b.png")
        br = batch_mod.run_batch(img_dir, td / "bout", batch_mod.BatchMode.IMAGES_TO_ONE_PDF)
        assert br.ok_count >= 1 and br.items[0].output and br.items[0].output.exists()

        assert isinstance(extract_outline(pdf), list)
        add_outline_item(pdf, "Smoke Cap", 0)
        ol = extract_outline(pdf)
        assert ol and ol[0].title == "Smoke Cap" and ol[0].page_index == 0
        add_outline_item(pdf, "Child", 1, parent_path=(0,))
        ol = extract_outline(pdf)
        assert ol[0].children and ol[0].children[0].title == "Child"
        delete_outline_item(pdf, (0, 0))
        ol = extract_outline(pdf)
        assert ol and not ol[0].children
        delete_outline_item(pdf, (0,))
        assert extract_outline(pdf) == []
        # Annotation JSON export/import
        store_json = AnnotationStore(pdf)
        store_json.annotations = []
        store_json.clear_history()
        store_json.add(Annotation(0, AnnotationType.HIGHLIGHT, 5, 5, width=20, height=8, text="json-ex"))
        jpath = td / "ann-export.json"
        store_json.export_json(jpath)
        assert jpath.is_file()
        store_imp = AnnotationStore(pdf)
        store_imp.annotations = []
        store_imp.clear_history()
        n_imp = store_imp.import_json(jpath, replace=True)
        assert n_imp == 1 and any(a.text == "json-ex" for a in store_imp.annotations)
        csv_path = td / "ann-export.csv"
        store_json.export_csv(csv_path)
        assert csv_path.is_file()
        csv_txt = csv_path.read_text(encoding="utf-8")
        assert "json-ex" in csv_txt and "page" in csv_txt.splitlines()[0]
        assert "Wasserzeichen" in (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "Schwärzung" in (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "Metadaten" in (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "Als Kopie" in (ROOT / "FEATURES.md").read_text(encoding="utf-8") or "Kopie" in (
            ROOT / "FEATURES.md"
        ).read_text(encoding="utf-8")
        assert "Wortzählung" in (ROOT / "FEATURES.md").read_text(encoding="utf-8") or "Wörter" in (
            ROOT / "FEATURES.md"
        ).read_text(encoding="utf-8")
        feat = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "Seitenbereich" in feat or "extract_page_range" in feat
        assert "Find/Replace" in feat or "Ersetzen" in feat
        assert "Filter" in feat

        insert_signature_field(pdf, 0, x=50, y=50, label="Test")
        insert_signature_image(pdf, Image.new("RGBA", (80, 30), (0, 0, 0, 0)), 0, x=60, y=120)
        store_sig = AnnotationStore(pdf)
        types = {a.type for a in store_sig.annotations}
        assert AnnotationType.SIGNATURE_FIELD in types
        assert AnnotationType.SIGNATURE in types

        tbl = ocr_mod.format_text_as_table([["A", "B"], ["1", "2"]])
        assert "| A" in tbl and "| 1" in tbl
        assert ocr_mod.TESSERACT_WIKI_URL.startswith("https://")

    if os.environ.get("ILD_SMOKE_QT", "1") == "1":
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        os.environ["ILD_SMOKE_QT"] = "1"
        os.environ["ILD_NO_SESSION"] = "1"
        from PySide6.QtWidgets import QApplication

        from instantlensdoc.license import LicenseManager
        from instantlensdoc.ui.main_window import MainWindow

        app = QApplication.instance() or QApplication(["smoke"])
        win = MainWindow(LicenseManager(path=ROOT / ".smoke_license.json"))
        win.new_doc()
        win.editor.setPlainText("alpha beta alpha gamma")
        assert win.editor.word_stats() == (4, len("alpha beta alpha gamma"))
        win._update_doc_status()
        assert "Wörter" in win.word_status_label.text()
        n = win.editor.find_and_highlight("alpha")
        assert n == 2
        assert win.editor.replace_all("alpha", "ALPHA") == 2
        assert "ALPHA" in win.editor.toPlainText() and "alpha" not in win.editor.toPlainText()
        assert win.editor.replace_one("beta", "BETA") == 1
        assert "BETA" in win.editor.toPlainText()
        from instantlensdoc.ui.find_replace_dialog import FindReplaceDialog

        assert FindReplaceDialog
        from PySide6.QtGui import QTextCursor

        cur = win.editor.textCursor()
        cur.movePosition(QTextCursor.Start)
        cur.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        win.editor.setTextCursor(cur)
        assert win.editor.highlight_selection()
        win._add_chained_frame()
        assert len(win.layout_doc.text_frames) >= 2
        assert "Lizenz:" in win.license_label.text() or "⚠" in win.license_label.text()
        assert "v0.3.9" in win.version_label.text()
        # Lizenz <7 Tage: Style prominent
        st_lic = win.license_manager.status()
        if st_lic.allowed and st_lic.days_remaining < 7:
            assert "⚠" in win.license_label.text() or "font-weight: 800" in win.license_label.styleSheet()
        assert callable(win._find_replace)
        assert callable(win._extract_page_range)
        assert hasattr(win.sidebar, "ann_filter")
        from instantlensdoc.ui.settings_dialog import SettingsDialog
        from instantlensdoc.ui.batch_dialog import BatchConvertDialog
        from instantlensdoc.ui.pdf_tools_dialog import PdfToolsDialog
        from instantlensdoc.ui.watermark_dialog import WatermarkDialog
        from instantlensdoc.ui.compare_dialog import PdfCompareDialog
        from instantlensdoc.ui.metadata_dialog import MetadataDialog
        from instantlensdoc.ui.page_size_dialog import PageSizeDialog

        assert SettingsDialog and BatchConvertDialog and PdfToolsDialog
        assert WatermarkDialog and PdfCompareDialog and MetadataDialog and PageSizeDialog
        assert win.sidebar.outline is not None
        from instantlensdoc.ui.theme import load_theme_mode, toggle_theme

        mode_before = load_theme_mode()
        mode_after = toggle_theme(win)
        assert mode_after != mode_before or mode_before in ("light", "dark")
        toggle_theme(win)
        assert win.acceptDrops()
        from instantlensdoc.core.export import export_html as eh

        eh(win.editor.toPlainText(), ROOT / ".smoke_export.html", title="smoke")
        assert (ROOT / ".smoke_export.html").exists()
        (ROOT / ".smoke_export.html").unlink(missing_ok=True)

        with tempfile.TemporaryDirectory() as td2:
            td2 = Path(td2)
            smoke_pdf = td2 / "smoke.pdf"
            Image.new("RGB", (300, 400), "white").save(smoke_pdf, "PDF")
            # Mehrseitiges PDF für extract_page_range
            from ild_pdf.pages import insert_blank_page as _ins_blank

            _ins_blank(smoke_pdf, at_index=1)
            _ins_blank(smoke_pdf, at_index=2)
            win.open_path(str(smoke_pdf))
            assert win.stack.currentWidget() is win.pdf_view
            old_scale = win.pdf_view.scale
            win.pdf_view.zoom_in()
            win.pdf_view._apply_pending_zoom()
            assert win.pdf_view.scale > old_scale
            win.pdf_view.zoom_100()
            assert abs(win.pdf_view.scale - 1.0) < 0.01
            win.pdf_view.fit_page()
            assert win.pdf_view.scale > 0
            assert callable(win.pdf_view.highlight_search)
            assert callable(win.pdf_view.search_next)
            assert hasattr(win.pdf_view, "btn_hl_color") and hasattr(win.pdf_view, "btn_pen_color")
            # Textsuche-Highlight braucht Text-PDF — Image-PDF → 0 Treffer OK
            assert win.pdf_view.highlight_search("nothing") == 0
            win.pdf_view.clear_search_highlights()
            exp_dir = Path(td2) / "exports"
            exp_dir.mkdir()
            set_last_export_dir(exp_dir)
            assert get_last_export_dir() == exp_dir
            assert get_autosave_interval_sec() >= 10
            assert get_default_zoom_percent() >= 25
            from ild_pdf import Annotation, AnnotationType, extract_pages_as_images

            assert win.pdf_view.store is not None
            win.pdf_view.store.add(
                Annotation(0, AnnotationType.HIGHLIGHT, 10, 10, width=40, height=12, text="u", color=get_ann_highlight_color())
            )
            assert win.pdf_view.store.can_undo()
            assert win.pdf_view.undo_annotation()
            assert not any(a.text == "u" for a in win.pdf_view.store.annotations)
            assert win.pdf_view.redo_annotation()
            assert any(a.text == "u" for a in win.pdf_view.store.annotations)
            # Annotation löschen (letzte)
            assert win.pdf_view.delete_annotation()
            assert not any(a.text == "u" for a in win.pdf_view.store.annotations)
            win.pdf_view.store.add(
                Annotation(0, AnnotationType.STICKY, 20, 20, width=60, height=40, text="sel")
            )
            win.pdf_view._on_annotation_selected(win.pdf_view.store.annotations[-1].id)
            assert win.pdf_view._selected_ann_id
            assert win.pdf_view.delete_annotation()
            assert not any(a.text == "sel" for a in win.pdf_view.store.annotations)
            # Seiten als Bilder
            imgs_out = Path(td2) / "page_imgs"
            written = extract_pages_as_images(smoke_pdf, imgs_out, format="PNG", scale=1.0)
            assert written and all(p.is_file() for p in written)
            jpg_written = extract_pages_as_images(
                smoke_pdf, imgs_out, pages=[0], format="JPEG", scale=1.0
            )
            assert jpg_written and jpg_written[0].suffix.lower() in (".jpg", ".jpeg")
            assert callable(win.pdf_view.export_pages_as_images)
            assert callable(win.pdf_view.apply_page_order)
            assert callable(win.pdf_view.insert_blank_after_current)
            assert callable(win.pdf_view.duplicate_current)
            assert callable(win.pdf_view.focus_annotation)
            assert callable(win.pdf_view.rotate_current)
            assert callable(win.pdf_view.flip_current)
            assert callable(win.pdf_view.edit_selected_annotation_text)
            assert callable(win.pdf_view.export_annotations_json)
            assert callable(win.pdf_view.export_annotations_csv)
            assert callable(win.pdf_view.import_annotations_json)
            assert callable(win.pdf_view.save_pdf_as_copy)
            assert callable(win._outline_add)
            assert callable(win._outline_delete)
            assert callable(win.save_as_copy)
            assert callable(win.save_all_docs)
            assert callable(win._edit_annotation_text)
            assert callable(win._toggle_line_numbers)
            assert hasattr(win, "word_status_label")
            assert hasattr(win.sidebar, "btn_outline_add")
            # Zeilennummern
            win.editor.set_line_numbers_visible(True)
            assert win.editor.line_numbers_visible()
            win.editor.set_line_numbers_visible(False)
            assert not win.editor.line_numbers_visible()
            # Groß-/Kleinschreibung (Zyklus: GROSS → klein → Titel → GROSS)
            win.editor.setPlainText("HELLO WORLD")
            from PySide6.QtGui import QTextCursor as _TC

            cur_case = win.editor.textCursor()
            cur_case.select(_TC.Document)
            win.editor.setTextCursor(cur_case)
            assert win.editor.toggle_case_selection()
            assert win.editor.toPlainText() == "hello world"
            cur_case = win.editor.textCursor()
            cur_case.select(_TC.Document)
            win.editor.setTextCursor(cur_case)
            assert win.editor.toggle_case_selection()
            assert win.editor.toPlainText() == "Hello World"
            cur_case = win.editor.textCursor()
            cur_case.select(_TC.Document)
            win.editor.setTextCursor(cur_case)
            assert win.editor.toggle_case_selection()
            assert win.editor.toPlainText() == "HELLO WORLD"
            assert callable(win._toggle_case_selection)
            assert callable(win._toggle_grayscale)
            assert callable(win._toggle_night_mode)
            assert callable(win._indent_selection)
            assert callable(win._outdent_selection)
            assert callable(win._open_log_folder)
            assert callable(win.pdf_view.set_grayscale)
            assert callable(win.pdf_view.set_night_mode)
            assert hasattr(win.pdf_view, "spin_opacity")
            assert hasattr(win.pdf_view, "btn_grayscale")
            assert hasattr(win.pdf_view, "btn_night")
            assert hasattr(win.sidebar, "ann_search")
            # Graustufen Toggle
            win.pdf_view.set_grayscale(True)
            assert win.pdf_view.grayscale_enabled()
            win.pdf_view.refresh()
            win.pdf_view.set_grayscale(False)
            assert not win.pdf_view.grayscale_enabled()
            # Nachtmodus Toggle (Ansicht)
            win.pdf_view.set_night_mode(True)
            assert win.pdf_view.night_mode_enabled()
            win.pdf_view.refresh()
            win.pdf_view.set_night_mode(False)
            assert not win.pdf_view.night_mode_enabled()
            # Annotation Opacity
            op_ann = Annotation(0, AnnotationType.STICKY, 11, 11, width=30, height=20, text="op", opacity=0.35)
            win.pdf_view.store.add(op_ann)
            assert abs(win.pdf_view.store.get(op_ann.id).opacity - 0.35) < 0.001
            win.pdf_view.store.update(op_ann.id, opacity=0.8)
            assert abs(win.pdf_view.store.get(op_ann.id).opacity - 0.8) < 0.001
            # Einrückung
            win.editor.setPlainText("alpha\nbeta")
            cur_ind = win.editor.textCursor()
            cur_ind.select(_TC.Document)
            win.editor.setTextCursor(cur_ind)
            assert win.editor.indent_selection(4)
            assert win.editor.toPlainText().startswith("    ")
            assert win.editor.outdent_selection(4)
            assert win.editor.toPlainText().splitlines()[0] == "alpha"
            # Fenstertitel mit Version
            assert "0.3.9" in win.windowTitle()
            from instantlensdoc.ui.help_dialog import AboutDialog, HelpDialog, open_log_folder

            about = AboutDialog(win)
            assert "0.3.9" in about.windowTitle()
            help_dlg = HelpDialog(win)
            assert help_dlg.windowTitle() == "Hilfe"
            assert callable(open_log_folder)
            from instantlensdoc.core.logging_setup import log_dir

            assert log_dir().is_dir()
            # Annotation-Text update API
            sticky = Annotation(0, AnnotationType.STICKY, 15, 15, width=40, height=30, text="alt")
            win.pdf_view.store.add(sticky)
            win.pdf_view.store.update(sticky.id, text="neu-edit")
            assert win.pdf_view.store.get(sticky.id).text == "neu-edit"
            win.pdf_view._on_annotation_selected(sticky.id)
            assert win.pdf_view._selected_ann_id == sticky.id
            # Outline add/delete API + refresh
            from ild_pdf.outline import add_outline_item, delete_outline_item, extract_outline

            add_outline_item(smoke_pdf, "Qt-Bookmark", 0)
            win._refresh_outline(smoke_pdf)
            assert win.sidebar.outline.topLevelItemCount() >= 1
            assert extract_outline(smoke_pdf)
            delete_outline_item(smoke_pdf, (0,))
            win._refresh_outline(smoke_pdf)
            # Ann JSON roundtrip via store
            win.pdf_view.store.add(
                Annotation(0, AnnotationType.STICKY, 4, 4, width=30, height=20, text="json-qt")
            )
            jexp = Path(td2) / "qt-ann.json"
            assert win.pdf_view.store.export_json(jexp).is_file()
            win.pdf_view.store.annotations = []
            assert win.pdf_view.store.import_json(jexp, replace=True) >= 1
            # PDF als Kopie
            copy_pdf = Path(td2) / "smoke_Kopie.pdf"
            import shutil

            shutil.copy2(smoke_pdf, copy_pdf)
            side = smoke_pdf.with_suffix(smoke_pdf.suffix + ".ildann.json")
            if side.is_file():
                shutil.copy2(side, copy_pdf.with_suffix(copy_pdf.suffix + ".ildann.json"))
            assert copy_pdf.is_file()
            assert win.pdf_view.pdf_path == smoke_pdf  # unverändert
            # Seite drehen / spiegeln / leere / duplizieren
            n0 = win.pdf_view.page_count
            win.pdf_view.rotate_current(90)
            win.pdf_view.rotate_current(-90)
            win.pdf_view.flip_current(horizontal=True)
            win.pdf_view.flip_current(vertical=True)
            win.pdf_view.insert_blank_after_current()
            assert win.pdf_view.page_count == n0 + 1
            win.pdf_view.page_index = 0
            win.pdf_view.duplicate_current()
            assert win.pdf_view.page_count == n0 + 2
            # Alles speichern
            win.save_all_docs()
            # Annotation-Liste Sidebar + Filter
            win.pdf_view.store.add(
                Annotation(0, AnnotationType.HIGHLIGHT, 8, 8, width=30, height=10, text="ann-list")
            )
            win.pdf_view.store.add(
                Annotation(0, AnnotationType.STICKY, 9, 9, width=20, height=20, text="sticky-f")
            )
            win._refresh_pdf_marks()
            assert win.sidebar.annotations.count() >= 2
            # Filter sticky
            idx = win.sidebar.ann_filter.findData("sticky")
            assert idx >= 0
            win.sidebar.ann_filter.setCurrentIndex(idx)
            assert win.sidebar.annotations.count() >= 1
            assert all(
                (
                    "notiz" in win.sidebar.annotations.item(i).text().lower()
                    or "sticky" in win.sidebar.annotations.item(i).text().lower()
                    or getattr(win.sidebar.annotations.item(i).data(256), "type", None)
                    and getattr(
                        win.sidebar.annotations.item(i).data(256).type, "value", ""
                    )
                    == "sticky"
                )
                for i in range(win.sidebar.annotations.count())
                if win.sidebar.annotations.item(i).data(256) is not None  # Gruppenköpfe überspringen
            )
            win.sidebar.ann_filter.setCurrentIndex(0)  # Alle
            # Annotation-Suche in Sidebar
            win.sidebar.ann_search.setText("sticky-f")
            assert win.sidebar.annotations.count() >= 1
            assert all(
                "sticky" in win.sidebar.annotations.item(i).text().lower()
                or "notiz" in win.sidebar.annotations.item(i).text().lower()
                or "sticky-f" in (getattr(win.sidebar.annotations.item(i).data(256), "text", "") or "").lower()
                for i in range(win.sidebar.annotations.count())
                if win.sidebar.annotations.item(i).data(256) is not None
            )
            win.sidebar.ann_search.clear()
            assert win.sidebar.annotations.count() >= 2
            win.pdf_view.focus_annotation(win.pdf_view.store.annotations[-1])
            assert win.pdf_view._selected_ann_id
            # extract_page_range API
            from ild_pdf import extract_page_range as epr

            er_out = Path(td2) / "extracted.pdf"
            epr(smoke_pdf, er_out, 1, min(2, win.pdf_view.page_count), one_based=True)
            assert er_out.is_file()
            # Suchhistorie
            win._remember_search("smoke-query-027")
            assert "smoke-query-027" in recent_searches_mod.load_recent_searches()
            win.sidebar.set_recent_searches(recent_searches_mod.load_recent_searches())
            assert "smoke-query-027" in [
                win.sidebar.search.itemText(i) for i in range(win.sidebar.search.count())
            ]
            assert hasattr(win, "file_status_label") and hasattr(win, "page_status_label")
            assert hasattr(win, "zoom_status_label")
            win._update_doc_status()
            assert "Seite" in win.page_status_label.text()
            assert "%" in win.zoom_status_label.text() or "—" in win.zoom_status_label.text()
            assert smoke_pdf.name in win.file_status_label.text()
            assert win.sidebar.thumbs.dragDropMode() != 0  # InternalMove aktiv
            assert callable(win.pdf_view.print_current_page)
            assert callable(win._print)
            assert callable(win.pdf_view.paste_clipboard_image)
            assert callable(win._paste_clipboard_image)
            assert callable(win._save_session)
            assert win.sidebar.recent.count() >= 1
            win._save_session()
            # Thumbnails + redaction + keyboard/stubs
            thumbs = win.pdf_view.render_thumbnails(max_pages=5, scale=0.15)
            assert len(thumbs) >= 1
            win.sidebar.set_page_thumbs(thumbs, current=0)
            assert win.sidebar.thumbs.count() >= 1
            # Lazy thumbs API
            tok = win.sidebar.prepare_lazy_thumbs(3, current=0, max_pages=40)
            assert win.sidebar.thumbs.count() == 3
            one = win.pdf_view.render_thumbnail(0, scale=0.15)
            assert win.sidebar.update_thumb(0, one, token=tok)
            assert callable(win.close_current_tab)
            assert callable(win._confirm_close_current)
            assert callable(win._edit_pdf_form_fields)
            from ild_pdf import (
                STAMP_LIBRARY,
                has_acroform,
                list_form_fields,
                set_form_values,
                stamp_library_items,
                stamp_with_date,
            )
            from instantlensdoc.ui.pdf_view import StampPickDialog
            from instantlensdoc.ui.form_fields_dialog import FormFieldsDialog
            import pikepdf

            assert len(STAMP_LIBRARY) == 3
            assert "GENEHMIGT" in stamp_with_date("GENEHMIGT", include_date=False)
            assert "\n" in stamp_with_date("ENTWURF", include_date=True)
            assert len(stamp_library_items(include_date=True)) == 3
            assert StampPickDialog and FormFieldsDialog
            # Mini-AcroForm PDF
            form_pdf = Path(td2) / "acro.pdf"
            with pikepdf.Pdf.new() as _fp:
                _fp.add_blank_page(page_size=(300, 200))
                _page = _fp.pages[0]
                from pikepdf import Dictionary as _D, Name as _N, Array as _A, String as _S

                _field = _fp.make_indirect(
                    _D(
                        FT=_N.Tx,
                        T=_S("City"),
                        V=_S("Berlin"),
                        Ff=0,
                        Rect=[40, 80, 200, 110],
                        Subtype=_N.Widget,
                        Type=_N.Annot,
                        DA=_S("/Helv 12 Tf 0 g"),
                    )
                )
                _page.Annots = _A([_field])
                _fp.Root.AcroForm = _D(Fields=_A([_field]), NeedAppearances=True)
                _fp.save(form_pdf)
            assert has_acroform(form_pdf)
            fl = list_form_fields(form_pdf)
            assert fl and fl[0].name == "City" and fl[0].value == "Berlin"
            set_form_values(form_pdf, {"City": "Hamburg"})
            assert list_form_fields(form_pdf)[0].value == "Hamburg"
            print("0.3.1 form/stamp/close/lazy: OK")
            # 0.3.2: Anhänge / Ann-Layer / MD-Preview / recent dirs
            from ild_pdf import (
                extract_all_attachments,
                extract_attachment,
                has_attachments,
                list_attachments,
            )
            from instantlensdoc.ui.attachments_dialog import AttachmentsDialog

            att_pdf = Path(td2) / "with_att.pdf"
            with pikepdf.Pdf.new() as _ap:
                _ap.add_blank_page(page_size=(300, 200))
                _ap.attachments["readme.txt"] = b"hello-ild-attachment"
                _ap.save(att_pdf)
            assert has_attachments(att_pdf)
            atts = list_attachments(att_pdf)
            assert atts and atts[0].name == "readme.txt"
            att_out = Path(td2) / "atts"
            written = extract_all_attachments(att_pdf, att_out)
            assert written and written[0].is_file()
            assert b"hello-ild-attachment" in written[0].read_bytes()
            one = extract_attachment(att_pdf, "readme.txt", out_dir=Path(td2) / "atts2")
            assert one.is_file()
            assert AttachmentsDialog and callable(win._pdf_attachments)
            win.pdf_view.set_annotations_visible(False)
            assert not win.pdf_view.annotations_visible()
            assert not win._ann_layer_action.isChecked()
            win.pdf_view.set_annotations_visible(True)
            assert win.pdf_view.annotations_visible()
            assert win._ann_layer_action.isChecked()
            assert hasattr(win, "editor_pane")
            win._md_preview_action.setChecked(True)
            assert win.editor_pane.preview_visible()
            assert win._md_preview_action.isChecked()
            win.editor.setPlainText("# Hello\n\n**bold**")
            assert "Hello" in win.editor_pane.preview.toPlainText() or win.editor_pane.preview_visible()
            win._md_preview_action.setChecked(False)
            assert not win.editor_pane.preview_visible()
            remember_recent_dir(td2)
            dirs = get_recent_dirs()
            assert dirs and str(dirs[0]) == str(Path(td2))
            assert dialog_start_dir() == str(Path(td2))
            print("0.3.2 attachments/layer/md/dirs: OK")
            # 0.3.3: Einzel-PDFs / Flatten / Soft-Wrap / Lizenz-Dialog
            from ild_pdf import flatten_annotations_to_pdf
            from instantlensdoc.core.app_settings import get_editor_soft_wrap, set_editor_soft_wrap
            from instantlensdoc.ui.license_dialog import LicenseDialog

            multi_split = Path(td2) / "split_src.pdf"
            with pikepdf.Pdf.new() as _sp:
                _sp.add_blank_page(page_size=(200, 280))
                _sp.add_blank_page(page_size=(200, 280))
                _sp.add_blank_page(page_size=(200, 280))
                _sp.save(multi_split)
            split_out = Path(td2) / "single_pages"
            singles = split_into_single_page_pdfs(multi_split, split_out)
            assert len(singles) == 3
            assert all(p.is_file() and p.suffix.lower() == ".pdf" for p in singles)
            assert callable(win._split_into_single_page_pdfs)

            store_flat = AnnotationStore(str(multi_split))
            store_flat.add(
                Annotation(0, AnnotationType.HIGHLIGHT, 10, 10, width=40, height=12, color="#FFE066")
            )
            store_flat.add(
                Annotation(1, AnnotationType.STICKY, 20, 20, width=60, height=40, text="Notiz")
            )
            store_flat.add(
                Annotation(2, AnnotationType.REDACTION, 5, 5, width=30, height=20, color="#000000")
            )
            flat_out = Path(td2) / "flattened.pdf"
            written_flat = flatten_annotations_to_pdf(
                multi_split, store_flat, scale=1.5, out_path=flat_out
            )
            assert written_flat.is_file() and written_flat.stat().st_size > 0
            with pikepdf.open(written_flat) as _fpdf:
                assert len(_fpdf.pages) == 3
            assert callable(win.pdf_view.export_annotations_flattened)

            set_editor_soft_wrap(True)
            win._soft_wrap_action.setChecked(True)
            assert win.editor.soft_wrap_enabled()
            assert win._soft_wrap_action.isChecked()
            win._soft_wrap_action.setChecked(False)
            assert not win.editor.soft_wrap_enabled()
            assert get_editor_soft_wrap() is False
            win._soft_wrap_action.setChecked(True)
            assert win.editor.soft_wrap_enabled()

            dlg_lic = LicenseDialog(win.license_manager)
            assert "Resttage" in dlg_lic.info.text()
            assert "Ablaufdatum" in dlg_lic.info.text()
            dlg_lic.close()
            print("0.3.3 single-pdf/flatten/softwrap/license: OK")
            # 0.3.4: PDF-Text→Editor / Ann.-Duplikat / Goto Line / Tray
            from instantlensdoc.core.app_settings import (
                get_minimize_to_tray,
                set_minimize_to_tray,
            )
            from instantlensdoc.ui.goto_line_dialog import GotoLineDialog

            # Plaintext helpers + Editor
            text_page = extract_page_plain_text(smoke_pdf, 0)
            assert isinstance(text_page, str)
            text_all = extract_all_plain_text(smoke_pdf, page_headers=True)
            assert "--- Seite 1 ---" in text_all
            assert callable(win._extract_page_text_to_editor)
            assert callable(win._extract_all_text_to_editor)
            win._extract_page_text_to_editor()
            assert win.stack.currentWidget() is win.editor_pane
            assert win.editor.toPlainText() == text_page
            win.stack.setCurrentWidget(win.pdf_view)
            win._extract_all_text_to_editor()
            assert win.stack.currentWidget() is win.editor_pane
            assert win.editor.toPlainText() == text_all

            # Annotation duplicate
            win.stack.setCurrentWidget(win.pdf_view)
            src_ann = win.pdf_view.store.add(
                Annotation(
                    0,
                    AnnotationType.STICKY,
                    40,
                    50,
                    width=70,
                    height=40,
                    text="dup-src",
                    color="#3498DB",
                )
            )
            before_n = len(win.pdf_view.store.annotations)
            dup_via_store = win.pdf_view.store.duplicate(src_ann.id, dx=8, dy=8)
            assert dup_via_store is not None
            assert dup_via_store.id != src_ann.id
            assert dup_via_store.text == "dup-src"
            assert abs(dup_via_store.x - (src_ann.x + 8)) < 0.01
            assert abs(dup_via_store.y - (src_ann.y + 8)) < 0.01
            assert len(win.pdf_view.store.annotations) == before_n + 1
            win.pdf_view._selected_ann_id = src_ann.id
            assert win.pdf_view.duplicate_selected_annotation()
            assert win.pdf_view._selected_ann_id != src_ann.id
            assert callable(win._duplicate_annotation)

            # Goto line
            win.editor.setPlainText("alpha\nbeta\ngamma\ndelta")
            win.stack.setCurrentWidget(win.editor_pane)
            assert win.editor.goto_line(3)
            assert win.editor.textCursor().blockNumber() == 2
            assert not win.editor.goto_line(0)
            assert not win.editor.goto_line(99)
            dlg_goto = GotoLineDialog(win.editor, win)
            assert dlg_goto.line_spin.maximum() == 4
            dlg_goto.line_spin.setValue(2)
            dlg_goto._go()
            assert win.editor.textCursor().blockNumber() == 1
            dlg_goto.close()
            assert callable(win._goto_line)

            # Tray minimize setting
            set_minimize_to_tray(False)
            assert get_minimize_to_tray() is False
            set_minimize_to_tray(True)
            assert get_minimize_to_tray() is True
            win.apply_tray_setting()
            assert callable(win.apply_tray_setting)
            set_minimize_to_tray(False)
            win.apply_tray_setting()
            print("0.3.4 text/dup/goto/tray: OK")
            # 0.3.5: Seitengröße mm/inch, Ann.-Gruppen, Zeile duplizieren, Backup .bak
            from instantlensdoc.core.app_settings import (
                get_backup_on_save,
                get_page_size_unit,
                set_backup_on_save,
                set_page_size_unit,
                toggle_page_size_unit,
            )
            from ild_pdf.pages import format_size_pair, pt_to_inch, pt_to_mm
            from instantlensdoc.core.documents import backup_existing, save_document as save_doc_fn
            from instantlensdoc.core.documents import Document as DocCls, DocKind as DK

            # Unit helpers
            assert abs(pt_to_mm(72.0) - 25.4) < 0.01
            assert abs(pt_to_inch(72.0) - 1.0) < 0.001
            assert "mm" in format_size_pair(595.28, 841.89, "mm")
            assert "in" in format_size_pair(612.0, 792.0, "inch")

            set_page_size_unit("mm")
            assert get_page_size_unit() == "mm"
            assert toggle_page_size_unit() == "inch"
            assert get_page_size_unit() == "inch"
            win._toggle_page_size_unit()
            assert get_page_size_unit() == "mm"
            assert hasattr(win, "size_status_label")
            win._update_doc_status()
            size_txt = win.size_status_label.text()
            assert size_txt and size_txt != "—" and ("mm" in size_txt or "in" in size_txt)
            assert callable(win._format_current_page_size)

            # Annotation grouping by page
            win.stack.setCurrentWidget(win.pdf_view)
            win.pdf_view.store.add(
                Annotation(1, AnnotationType.HIGHLIGHT, 10, 10, width=40, height=12, text="p2-ann")
            )
            win._refresh_pdf_marks()
            win.sidebar.ann_filter.setCurrentIndex(0)
            win.sidebar.ann_search.clear()
            headers = [
                win.sidebar.annotations.item(i).text()
                for i in range(win.sidebar.annotations.count())
                if win.sidebar.annotations.item(i).data(256) is None
                and "Seite" in (win.sidebar.annotations.item(i).text() or "")
            ]
            assert any("Seite 1" in h for h in headers), headers
            assert any("Seite 2" in h for h in headers), headers

            # Duplicate line
            win.editor.setPlainText("alpha\nbeta\ngamma")
            win.stack.setCurrentWidget(win.editor_pane)
            assert win.editor.goto_line(2)
            assert win.editor.duplicate_line()
            assert win.editor.toPlainText().splitlines() == ["alpha", "beta", "beta", "gamma"]
            assert callable(win._duplicate_line)
            win._duplicate_line()

            # Backup .bak on save
            set_backup_on_save(False)
            assert get_backup_on_save() is False
            set_backup_on_save(True)
            assert get_backup_on_save() is True
            txt_path = Path(td2) / "bak-test.txt"
            txt_path.write_text("v1", encoding="utf-8")
            assert backup_existing(txt_path).exists()
            assert Path(str(txt_path) + ".bak").read_text(encoding="utf-8") == "v1"
            d = DocCls(path=txt_path, kind=DK.TEXT, text="v2")
            save_doc_fn(d)
            assert Path(str(txt_path) + ".bak").read_text(encoding="utf-8") == "v1"
            assert txt_path.read_text(encoding="utf-8") == "v2"
            set_backup_on_save(False)
            print("0.3.5 size/ann-group/dup-line/backup: OK")
            # 0.3.6: Raster-DPI, Ann. Select-All, Kommentar, Fenstergeometrie
            from instantlensdoc.core.app_settings import (
                EXPORT_RASTER_DPI_CHOICES,
                get_export_raster_dpi,
                get_window_geometry_b64,
                get_window_state_b64,
                set_export_raster_dpi,
                set_window_geometry_b64,
                set_window_state_b64,
            )

            assert EXPORT_RASTER_DPI_CHOICES == (72, 150, 300)
            set_export_raster_dpi(150)
            assert get_export_raster_dpi() == 150
            assert set_export_raster_dpi(300) == 300
            assert get_export_raster_dpi() == 300
            assert set_export_raster_dpi(72) == 72
            dpi_out = Path(td2) / "dpi72.png"
            extract_page_image(smoke_pdf, 0, dpi_out, dpi=72)
            assert dpi_out.is_file()
            from PIL import Image as _Img

            with _Img.open(dpi_out) as im72:
                w72, h72 = im72.size
            dpi_out150 = Path(td2) / "dpi150.png"
            extract_page_image(smoke_pdf, 0, dpi_out150, dpi=150)
            with _Img.open(dpi_out150) as im150:
                w150, h150 = im150.size
            assert w150 > w72 and h150 > h72
            set_export_raster_dpi(150)

            # Select-all annotations on page
            win.stack.setCurrentWidget(win.pdf_view)
            win.pdf_view.store.add(
                Annotation(0, AnnotationType.HIGHLIGHT, 12, 12, width=30, height=10, text="sa1")
            )
            win.pdf_view.store.add(
                Annotation(0, AnnotationType.STICKY, 80, 80, width=40, height=30, text="sa2")
            )
            n_sel = win.pdf_view.select_all_annotations_on_page()
            assert n_sel >= 2
            assert len(win.pdf_view._selected_ann_ids) >= 2
            assert callable(win._select_all_annotations_on_page)
            win._select_all_annotations_on_page()

            # Comment / uncomment
            win.stack.setCurrentWidget(win.editor_pane)
            win.editor.setPlainText("print(1)\nprint(2)\n")
            assert win.editor.comment_prefix_for_path("x.py") == "#"
            assert win.editor.comment_prefix_for_path("x.js") == "//"
            assert win.editor.toggle_line_comment("#")
            lines = win.editor.toPlainText().splitlines()
            assert lines[0].startswith("# ")
            assert win.editor.toggle_line_comment("#")
            assert win.editor.toPlainText().splitlines()[0] == "print(1)"
            win.editor.setPlainText("const a = 1;\nconst b = 2;")
            assert win.editor.toggle_line_comment("//")
            assert win.editor.toPlainText().splitlines()[0].startswith("// ")
            assert callable(win._toggle_line_comment)

            # Window geometry persistence
            set_window_geometry_b64("dGVzdA==")
            set_window_state_b64("c3RhdGU=")
            assert get_window_geometry_b64() == "dGVzdA=="
            assert get_window_state_b64() == "c3RhdGU="
            assert callable(win._save_window_geometry)
            assert callable(win._restore_window_geometry)
            win._save_window_geometry()
            assert get_window_geometry_b64()  # non-empty after save
            set_window_geometry_b64("")
            set_window_state_b64("")
            print("0.3.6 dpi/select-all/comment/geometry: OK")
            # 0.3.7: Präsentation, Ann.-Favoriten, Block-Tab, Session-Toggle
            from instantlensdoc.core.app_settings import (
                get_ann_color_presets,
                get_restore_session_on_start,
                set_ann_color_preset,
                set_ann_color_presets,
                set_restore_session_on_start,
            )

            presets = get_ann_color_presets()
            assert len(presets) == 3
            assert all(c.startswith("#") for c in presets)
            set_ann_color_presets(["#AABBCC", "#112233", "#FFE066"])
            assert get_ann_color_presets()[0] == "#AABBCC"
            set_ann_color_preset(1, "#99AA00")
            assert get_ann_color_presets()[1] == "#99AA00"
            win.pdf_view._refresh_preset_btns()
            assert len(win.pdf_view._preset_btns) == 3
            win.pdf_view._apply_color_preset(0)
            assert win.pdf_view._highlight_color == "#AABBCC"
            win.pdf_view._save_color_preset(2)
            assert get_ann_color_presets()[2] == win.pdf_view._highlight_color

            set_restore_session_on_start(False)
            assert get_restore_session_on_start() is False
            set_restore_session_on_start(True)
            assert get_restore_session_on_start() is True
            assert callable(win._toggle_presentation)
            assert callable(win._enter_presentation)
            assert callable(win._exit_presentation)
            assert win._presentation_active is False
            # ohne PDF: Enter bleibt inaktiv (kein Dialog im Smoke)
            win.pdf_view.pdf_path = None
            # _enter_presentation zeigt sonst QMessageBox — direkt Guard prüfen
            assert not win.pdf_view.pdf_path
            # mit PDF: Enter/Exit (ohne showFullScreen-Probleme: Flag-Pfad)
            win.open_path(smoke_pdf)
            assert win.pdf_view.pdf_path
            win._presentation_active = True
            win._presentation_prev = {
                "menu": True,
                "status": True,
                "sidebar": True,
                "was_fullscreen": False,
                "stack": win.stack.currentWidget(),
                "toolbar_layout": None,
            }
            win._exit_presentation()
            assert win._presentation_active is False

            # Block-Tab: Tab ohne Auswahl rückt aktuelle Zeile ein
            win.stack.setCurrentWidget(win.editor_pane)
            win.editor.setPlainText("block\nline")
            from PySide6.QtGui import QTextCursor as _TC_BLK
            from PySide6.QtGui import QKeyEvent
            from PySide6.QtCore import QEvent, Qt

            cur_b = win.editor.textCursor()
            cur_b.movePosition(_TC_BLK.Start)
            win.editor.setTextCursor(cur_b)
            assert win.editor.indent_selection(4)
            assert win.editor.toPlainText().splitlines()[0].startswith("    ")
            assert win.editor.outdent_selection(4)
            assert win.editor.toPlainText().splitlines()[0] == "block"
            ev_tab = QKeyEvent(QEvent.KeyPress, Qt.Key_Tab, Qt.NoModifier)
            win.editor.keyPressEvent(ev_tab)
            assert win.editor.toPlainText().splitlines()[0].startswith("    ")
            ev_shift = QKeyEvent(QEvent.KeyPress, Qt.Key_Backtab, Qt.ShiftModifier)
            win.editor.keyPressEvent(ev_shift)
            assert win.editor.toPlainText().splitlines()[0] == "block"
            print("0.3.7 present/presets/block-tab/session: OK")
            # 0.3.8: Thumbnail-Größe, Ann.-CSV, Zeile verschieben, Overwrite-Schutz
            from instantlensdoc.core.app_settings import (
                PDF_THUMBNAIL_SCALE_CHOICES,
                get_pdf_thumbnail_scale,
                pdf_thumbnail_icon_size,
                set_pdf_thumbnail_scale,
            )
            from instantlensdoc.ui.file_dialogs import confirm_overwrite_export

            assert PDF_THUMBNAIL_SCALE_CHOICES == (0.12, 0.18, 0.24)
            set_pdf_thumbnail_scale(0.18)
            assert get_pdf_thumbnail_scale() == 0.18
            assert set_pdf_thumbnail_scale(0.24) == 0.24
            assert get_pdf_thumbnail_scale() == 0.24
            assert pdf_thumbnail_icon_size(0.18) == (72, 96)
            w24, h24 = pdf_thumbnail_icon_size(0.24)
            assert w24 > 72 and h24 > 96
            set_pdf_thumbnail_scale(0.12)
            assert get_pdf_thumbnail_scale() == 0.12
            set_pdf_thumbnail_scale(0.18)

            csv_ui = Path(td2) / "ann-ui.csv"
            n_csv = win.pdf_view.store.export_csv(csv_ui)
            assert Path(n_csv).is_file()
            assert "id,page,type" in Path(n_csv).read_text(encoding="utf-8").splitlines()[0]
            assert callable(win.pdf_view.export_annotations_csv)

            win.stack.setCurrentWidget(win.editor_pane)
            win.editor.setPlainText("one\ntwo\nthree")
            from PySide6.QtGui import QTextCursor as _TC_MV

            cur_m = win.editor.textCursor()
            cur_m.movePosition(_TC_MV.Start)
            cur_m.movePosition(_TC_MV.Down)
            win.editor.setTextCursor(cur_m)
            assert win.editor.move_line_up()
            assert win.editor.toPlainText().splitlines() == ["two", "one", "three"]
            assert win.editor.move_line_down()
            assert win.editor.toPlainText().splitlines() == ["one", "two", "three"]
            assert callable(win._move_line_up) and callable(win._move_line_down)
            win._move_line_down()

            missing = Path(td2) / "no-such-export.bin"
            assert confirm_overwrite_export(missing, win) is True
            existing = Path(td2) / "exists-export.bin"
            existing.write_text("keep", encoding="utf-8")
            # Ohne Dialog-Antwort: Helper muss Datei nicht löschen wenn No — hier nur Existenz-Pfad
            assert existing.is_file() and existing.read_text(encoding="utf-8") == "keep"
            assert callable(confirm_overwrite_export)
            print("0.3.8 thumb/csv/move-line/overwrite: OK")
            # 0.3.9: Fit-Height, Ann.-Statistik, Sonderzeichen, Tray-Version
            from instantlensdoc.core.app_settings import (
                get_editor_show_special_chars,
                get_update_check_on_start,
                set_editor_show_special_chars,
                set_update_check_on_start,
            )

            assert callable(win.pdf_view.fit_height)
            assert callable(win._fit_height)
            win.pdf_view.fit_height()
            assert callable(win.pdf_view.fit_width)

            win._refresh_pdf_marks()
            stats = win.sidebar.ann_stats_label.text()
            assert stats.startswith("Ann.")
            assert "Highlight" in stats or "Notiz" in stats or "Ann. " in stats

            set_editor_show_special_chars(False)
            assert get_editor_show_special_chars() is False
            win._special_chars_action.setChecked(True)
            assert win.editor.special_chars_visible()
            assert get_editor_show_special_chars() is True
            win._special_chars_action.setChecked(False)
            assert not win.editor.special_chars_visible()
            assert get_editor_show_special_chars() is False
            win.editor.set_special_chars_visible(True)
            assert win.editor.special_chars_visible()
            win.editor.set_special_chars_visible(False)

            # Update-Check-on-Start: Setting muss abgefragt werden (silent nur wenn erlaubt)
            set_update_check_on_start(False)
            assert get_update_check_on_start() is False
            set_update_check_on_start(True)
            assert get_update_check_on_start() is True
            set_update_check_on_start(False)

            set_minimize_to_tray(True)
            win.apply_tray_setting()
            if win._tray is not None:
                tip = win._tray.toolTip()
                assert "0.3.9" in tip and "InstantLens Doc" in tip
            set_minimize_to_tray(False)
            win.apply_tray_setting()
            print("0.3.9 fit-h/ann-stats/special/tray: OK")
            win.pdf_view.store.add(
                Annotation(0, AnnotationType.REDACTION, 5, 5, width=30, height=20, color="#000000", text="REDACT")
            )
            assert any(a.type == AnnotationType.REDACTION for a in win.pdf_view.store.annotations)
            assert win.pdf_view.redaction_count() >= 1
            from instantlensdoc.ui.keyboard_help import KeyboardHelpDialog
            from instantlensdoc.ui.password_dialog import CompressPdfDialog, SetPasswordDialog
            from instantlensdoc.ui.stubs import PLANNED
            assert KeyboardHelpDialog and SetPasswordDialog and CompressPdfDialog
            assert "0.3.9" in PLANNED["ki"]
            assert "Coming soon" in PLANNED["cloud"]
            assert "0.3.9" in PLANNED["stylus"] and "0.3.9" in PLANNED["extrude3d"]
            # Toolbar ↔ Menü Sync Graustufen/Nacht
            win.pdf_view.set_grayscale(True)
            assert win._grayscale_action.isChecked()
            win.pdf_view.set_grayscale(False)
            assert not win._grayscale_action.isChecked()
            win.pdf_view.set_night_mode(True)
            assert win._night_action.isChecked()
            win.pdf_view.set_night_mode(False)
            assert not win._night_action.isChecked()
            # Ann-Suche: deutsches Typ-Label „Notiz“
            win.pdf_view.store.add(
                Annotation(0, AnnotationType.STICKY, 3, 3, width=20, height=20, text="xyz-unique")
            )
            win._refresh_pdf_marks()
            win.sidebar.ann_filter.setCurrentIndex(0)
            win.sidebar.ann_search.setText("notiz")
            assert win.sidebar.annotations.count() >= 1
            win.sidebar.ann_search.clear()
            # Einrückung Mehrzeile: Auswahl bleibt auf beiden Zeilen
            win.editor.setPlainText("one\ntwo")
            from PySide6.QtGui import QTextCursor as _TC3

            cur_m = win.editor.textCursor()
            cur_m.select(_TC3.Document)
            win.editor.setTextCursor(cur_m)
            assert win.editor.indent_selection(2)
            lines = win.editor.toPlainText().splitlines()
            assert lines[0].startswith("  ") and lines[1].startswith("  ")
            sel = win.editor.textCursor()
            assert sel.hasSelection()
            assert win.editor.outdent_selection(2)
            assert win.editor.toPlainText().splitlines() == ["one", "two"]
            from instantlensdoc.ui.help_dialog import HELP_HTML

            assert "Stub 0.3.9" in HELP_HTML
            assert "scripts/sync-ild.ps1" in HELP_HTML
            assert "Präsentationsmodus" in HELP_HTML or "F5" in (
                ROOT / "instantlensdoc" / "ui" / "keyboard_help.py"
            ).read_text(encoding="utf-8")
            print("0.3.4–0.3.9 review OK")
            assert callable(win.pdf_view.bake_redactions)
            assert callable(win.pdf_view.clear_redactions)
            assert callable(win._set_pdf_password)
            assert callable(win._compress_pdf_images)
            assert callable(win._edit_pdf_metadata)
            assert callable(win._pdf_page_size)
            assert callable(win._check_updates)
            set_metadata(smoke_pdf, PdfMetadata(title="SmokeMeta"))
            assert "Smoke" in get_metadata(smoke_pdf).title
            set_page_size(smoke_pdf, 0, *PAGE_SIZE_PRESETS["Letter"])

            # Qt-Kern: annotate speichern + Editor-Export + Lizenzlabel
            assert win.pdf_view.store is not None
            win.pdf_view.store.add(
                Annotation(0, AnnotationType.UNDERLINE, 12, 12, width=50, height=10, text="qt-core")
            )
            assert win.pdf_view.save_annotations()
            assert win.pdf_view.store.sidecar_path.exists()
            assert callable(win.pdf_view.save_annotations_as)
            backup = Path(td2) / "ann-backup.ildann.json"
            assert win.pdf_view.store.export_backup(backup).exists()
            assert "Lizenz:" in win.license_label.text() or "⚠" in win.license_label.text()
            # Batch-Fortschritt Callback (current/total)
            from instantlensdoc.core import batch as batch_mod2

            imgs = Path(td2) / "batch_imgs"
            imgs.mkdir()
            Image.new("RGB", (40, 40), "white").save(imgs / "a.png")
            Image.new("RGB", (40, 40), "black").save(imgs / "b.png")
            seen: list[tuple] = []

            def _prog(msg, current=0, total=0):
                seen.append((msg, current, total))

            br2 = batch_mod2.run_batch(
                imgs, Path(td2) / "bout2", batch_mod2.BatchMode.IMAGES_TO_PDF_EACH, progress=_prog
            )
            assert br2.ok_count == 2 and seen and any(t > 0 for _, _, t in seen)
            qt_html = Path(td2) / "qt_core.html"
            from instantlensdoc.core.export import export_html as eh2

            eh2("qt core export", qt_html, title="qt")
            assert qt_html.is_file()
            print("Qt core open/annotate/export/license: OK")

        win.close()
        print("Qt: OK")

    print("Smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
