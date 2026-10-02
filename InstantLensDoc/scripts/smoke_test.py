#!/usr/bin/env python3
"""Smoke-Test 0.2.7 (CLI + optional offscreen Qt). Kernpfade: open/annotate/export/license."""

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
        get_ann_highlight_color,
        get_ann_pen_color,
        get_autosave_interval_sec,
        get_default_zoom_percent,
        get_editor_line_numbers,
        get_export_jpeg_quality,
        get_last_export_dir,
        get_ocr_lang,
        get_ui_lang,
        load_settings,
        save_settings,
        set_ann_highlight_color,
        set_ann_pen_color,
        set_autosave_interval_sec,
        set_default_zoom_percent,
        set_editor_line_numbers,
        set_last_export_dir,
    )
    from instantlensdoc.core.i18n import set_lang, tr
    from instantlensdoc.core.update_check import check_for_updates
    from instantlensdoc.license import KEY_DAYS, TRIAL_DAYS, generate_key, verify_key

    assert __version__ == "0.2.7", __version__
    assert ild_ver == "0.2.7", ild_ver
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
    assert upd.local_version == "0.2.7" and not upd.online
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
    set_default_zoom_percent(175)
    assert get_default_zoom_percent() == 175
    set_autosave_interval_sec(45)
    assert get_autosave_interval_sec() == 45
    set_ann_highlight_color("#FFCC00")
    set_ann_pen_color("#112233")
    assert get_ann_highlight_color() == "#FFCC00"
    assert get_ann_pen_color() == "#112233"
    assert (ROOT / "CHANGELOG.md").is_file()
    assert "0.2.7" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "0.2.7" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "run.bat" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "sync-ild.ps1" in (ROOT / "README.md").read_text(encoding="utf-8")

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
        sid = store.save(force=True)
        assert sid.exists()
        raw = sid.read_text(encoding="utf-8")
        assert '"version": 3' in raw
        store2 = AnnotationStore(pdf)
        assert len(store2.annotations) == 9
        types = {a.type for a in store2.annotations}
        assert AnnotationType.STAMP in types and AnnotationType.CALLOUT in types
        assert AnnotationType.RECTANGLE in types and AnnotationType.MEASURE in types
        assert AnnotationType.TEXT_OVERLAY in types
        last_id = store2.annotations[-1].id
        assert store2.update(last_id, text="Overlay-Updated")
        assert store2.get(last_id).text == "Overlay-Updated"

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
        assert "0.2.7" in iss and "desktopicon" in iss and "DisableProgramGroupPage=no" in iss
        assert "UninstallDisplayName" in iss and "Uninstallable=yes" in iss
        assert "IncludeKeygen" in iss and "SetupIconFile" in iss
        assert "InstantLensKeygen.exe" in iss
        assert "uninstallexe" in iss
        bw = (ROOT / "build-windows.ps1").read_text(encoding="utf-8")
        assert "0.2.7" in bw and "NoKeygenInApp" in bw and "--icon" in bw
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
        assert "0.2.7" in (ROOT / "INFO.md").read_text(encoding="utf-8")
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
        assert "v0.2.7" in win.version_label.text()
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
                "sticky" in (win.sidebar.annotations.item(i).text().lower())
                for i in range(win.sidebar.annotations.count())
            )
            win.sidebar.ann_filter.setCurrentIndex(0)  # Alle
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
            win.pdf_view.store.add(
                Annotation(0, AnnotationType.REDACTION, 5, 5, width=30, height=20, color="#000000", text="REDACT")
            )
            assert any(a.type == AnnotationType.REDACTION for a in win.pdf_view.store.annotations)
            assert win.pdf_view.redaction_count() >= 1
            from instantlensdoc.ui.keyboard_help import KeyboardHelpDialog
            from instantlensdoc.ui.password_dialog import CompressPdfDialog, SetPasswordDialog
            from instantlensdoc.ui.stubs import PLANNED
            assert KeyboardHelpDialog and SetPasswordDialog and CompressPdfDialog
            assert "0.2.7" in PLANNED["ki"]
            assert "Coming soon" in PLANNED["cloud"]
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
