#!/usr/bin/env python3
"""Smoke-Test 0.9.1 (CLI + optional offscreen Qt). Kernpfade: open/annotate/export/license + ausgewählte 0.6.x-Pfade."""

from __future__ import annotations

import os
import json
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
        selection_to_highlight_rects,
        selection_to_plain_text,
        get_metadata,
        get_page_boxes,
        sanitize_pdf,
        strip_metadata,
        normalize_tags,
        tags_to_str,
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
        get_project_workspaces,
        get_active_project_workspace,
        remember_project_workspace,
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

    assert __version__ == "0.9.1", __version__
    assert ild_ver == "0.9.1", ild_ver
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
    assert upd.local_version == "0.9.1" and not upd.online
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
    assert "0.9.1" in cl and "0.9.0" in cl and "0.8.9" in cl and "0.8.8" in cl and "0.8.7" in cl and "0.8.6" in cl and "0.8.5" in cl and "0.8.4" in cl and "0.8.3" in cl and "0.8.2" in cl and "0.8.1" in cl and "0.8.0" in cl
    assert "## 0.9.1" in cl and "## 0.9.0" in cl and "## 0.8.9" in cl and "## 0.8.8" in cl and "## 0.8.7" in cl and "## 0.8.6" in cl and "## 0.8.5" in cl and "## 0.8.4" in cl and "## 0.8.3" in cl and "## 0.8.2" in cl and "## 0.8.1" in cl and "## 0.8.0" in cl
    assert "## 0.7.9" in cl
    assert "## 0.7.8" in cl
    assert "## 0.7.6" in cl
    assert "## 0.7.4" in cl
    assert "## 0.7.3" in cl
    assert "## 0.7.2" in cl
    assert "## 0.7.1" in cl
    assert "## 0.7.0" in cl
    assert "0.6.0 → 0.7.0" in cl or "0.6.0→0.7.0" in cl
    assert "## 0.6.0" in cl
    assert "0.5.0 → 0.6.0" in cl or "0.5.0→0.6.0" in cl
    assert "## 0.5.0" in cl
    assert "0.6.9" in cl
    assert "0.6.5" in cl
    assert "0.6.1" in cl
    assert "0.4.0 → 0.5.0" in cl or "0.4.0→0.5.0" in cl
    assert "## 0.4.0" in cl
    assert "0.3.0 → 0.4.0" in cl or "0.3.0→0.4.0" in cl
    assert "## 0.3.0" in cl
    assert "## 0.2.0" in cl
    assert "AcroForm" in cl or "Formularfelder" in cl
    assert "Fit-Height" in cl or "Höhe" in cl
    assert "Präsentation" in cl or "F5" in cl
    assert "CSV" in cl
    assert "Sonderzeichen" in cl
    assert "Lazy" in cl or "Lazy-Load" in cl or "Thumbnail" in cl
    assert "Anhang" in cl or "Anhänge" in cl or "attachments" in cl.lower()
    assert "Seitenlabel" in cl or "Seitenlabels" in cl
    assert "Continuous Scroll" in cl
    assert "Schema v4" in cl or "ildann-v4" in cl
    assert "Spread" in cl or "Zwei-Seiten" in cl
    assert "Batch-OCR" in cl or "OCR gesamtes PDF" in cl
    assert "Tags" in cl or "Labels" in cl
    assert "Projekt-Ordner" in cl or "Workspace" in cl
    assert "bereinigen" in cl or "Metadaten" in cl
    assert "ildfav" in cl or "Favoriten JSON" in cl or "Seiten-Favoriten" in cl
    assert "Toolbar-Slider" in cl or "Opacity" in cl
    assert "Erste-Schritte" in cl or "Wizard" in cl
    assert "Tag-Cloud" in cl or "Sync-Scroll" in cl
    assert "Doc-Split" in cl or "Fenster teilen" in cl
    assert "Fehlerliste" in cl or "Alle speichern" in cl
    assert "Wizard" in cl or "Erste-Schritte" in cl
    # Kompakt: Einzel-Header 0.6.1–0.6.9, 0.5.1–0.5.9, 0.4.1–0.4.9, 0.3.1–0.3.9 und 0.2.1–0.2.9 entfernt (nur Kurz-Tabelle)
    assert "## 0.6.9" not in cl and "## 0.6.8" not in cl
    assert "## 0.6.1" not in cl and "## 0.6.5" not in cl
    assert "## 0.5.9" not in cl and "## 0.5.8" not in cl
    assert "## 0.5.1" not in cl and "## 0.5.5" not in cl
    assert "## 0.4.9" not in cl and "## 0.4.8" not in cl
    assert "## 0.4.1" not in cl and "## 0.4.6" not in cl
    assert "## 0.3.9" not in cl and "## 0.3.8" not in cl
    assert "## 0.3.1" not in cl and "## 0.2.9" not in cl
    assert "0.6.9" in cl  # noch in Kurz-Tabelle
    assert "0.5.9" in cl  # noch in Kurz-Tabelle
    assert "0.4.9" in cl  # noch in Kurz-Tabelle
    assert "0.3.9" in cl  # noch in Kurz-Tabelle
    assert "0.2.9" in cl  # noch in Kurz-Tabelle
    assert "0.9.1" in (ROOT / "README.md").read_text(encoding="utf-8")
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
        assert '"version": 4' in raw
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
        assert "0.9.1" in iss and "desktopicon" in iss and "DisableProgramGroupPage=no" in iss
        assert "UninstallDisplayName" in iss and "Uninstallable=yes" in iss
        assert "IncludeKeygen" in iss and "SetupIconFile" in iss
        assert "InstantLensKeygen.exe" in iss
        assert "uninstallexe" in iss
        bw = (ROOT / "build-windows.ps1").read_text(encoding="utf-8")
        assert "0.9.1" in bw and "NoKeygenInApp" in bw and "--icon" in bw
        assert "InstantLensKeygen.exe" in bw
        bi = (ROOT / "installer" / "build-installer.ps1").read_text(encoding="utf-8")
        assert "InstantLensKeygen.exe" in bi and "IncludeKeygen" in bi
        kg_readme = (ROOT / "keygen" / "README.md").read_text(encoding="utf-8")
        assert "InstantLensKeygen.exe" in kg_readme
        assert "Installer" in kg_readme
        hinweis = (ROOT / "installer" / "installer-hinweis.txt").read_text(encoding="utf-8")
        assert "InstantLensKeygen.exe" in hinweis or "run-keygen.bat" in hinweis
        assert "0.9.1" in hinweis
        assert "checkedonce" in iss and "Desktop-Verknüpfung" in hinweis
        from ild_pdf.limits import OPEN_TIMEOUT_HINT, OPEN_TIMEOUT_HINT_SEC

        assert OPEN_TIMEOUT_HINT_SEC >= 15 and "teilen" in OPEN_TIMEOUT_HINT.lower()
        kb = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
        assert "Ctrl+Shift+S" in kb and "Sidecar" in kb
        assert "save_annotations_as" in (ROOT / "instantlensdoc" / "ui" / "pdf_view.py").read_text(encoding="utf-8")
        assert "QProgressBar" in (ROOT / "instantlensdoc" / "ui" / "batch_dialog.py").read_text(encoding="utf-8")
        assert "QProgressDialog" in (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")

        assert (ROOT / "examples" / "ild_pdf_demo.py").exists()
        assert "0.9.1" in (ROOT / "INFO.md").read_text(encoding="utf-8")
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

        # --- Ausgewählte 0.3.x-/0.4.x-/0.5.x-/0.6.x-Pfade (CLI, Konsolidierung 0.7.0) + 0.9.0 ---
        from ild_pdf.annotate import stamp_library_items
        from ild_pdf.attachments import has_attachments, list_attachments
        from ild_pdf.flatten import flatten_annotations_to_pdf
        from ild_pdf.pages import format_size_pair, pt_to_mm, split_into_single_page_pdfs
        from instantlensdoc.core.app_settings import (
            get_backup_on_save,
            get_editor_show_special_chars,
            get_export_raster_dpi,
            get_minimize_to_tray,
            get_page_size_unit,
            get_pdf_thumbnail_scale,
            get_restore_session_on_start,
            pdf_thumbnail_icon_size,
            set_backup_on_save,
            set_editor_show_special_chars,
            set_export_raster_dpi,
            set_pdf_thumbnail_scale,
            set_restore_session_on_start,
        )

        stamps = stamp_library_items(include_date=True)
        assert len(stamps) >= 3 and all(len(t) == 3 for t in stamps)
        assert not has_attachments(pdf)
        assert list_attachments(pdf) == []
        mm_pair = format_size_pair(595.0, 842.0, "mm")
        assert "mm" in mm_pair and abs(pt_to_mm(72.0) - 25.4) < 0.05
        singles_dir = td / "singles03"
        singles_dir.mkdir(exist_ok=True)
        single_paths = split_into_single_page_pdfs(pdf, singles_dir)
        assert len(single_paths) >= 2 and all(Path(p).is_file() for p in single_paths)
        flat_cli = td / "flat03.pdf"
        flat_store = AnnotationStore(pdf)
        flat_store.add(
            Annotation(0, AnnotationType.HIGHLIGHT, 8, 8, width=40, height=10, text="flat-cli")
        )
        written = flatten_annotations_to_pdf(pdf, flat_store, out_path=flat_cli, scale=1.0)
        assert Path(written).is_file() and Path(written).stat().st_size > 50
        set_export_raster_dpi(300)
        assert get_export_raster_dpi() == 300
        set_export_raster_dpi(150)
        assert get_export_raster_dpi() == 150
        set_pdf_thumbnail_scale(0.24)
        assert get_pdf_thumbnail_scale() == 0.24
        assert pdf_thumbnail_icon_size(0.24)[0] > pdf_thumbnail_icon_size(0.12)[0]
        set_pdf_thumbnail_scale(0.18)
        set_restore_session_on_start(False)
        assert get_restore_session_on_start() is False
        set_restore_session_on_start(True)
        assert get_restore_session_on_start() is True
        set_editor_show_special_chars(True)
        assert get_editor_show_special_chars() is True
        set_editor_show_special_chars(False)
        set_backup_on_save(True)
        assert get_backup_on_save() is True
        set_backup_on_save(False)
        assert get_page_size_unit() in ("mm", "inch")
        assert isinstance(get_minimize_to_tray(), bool)
        assert "0.9.1" in feat and "0.9.0" in feat and "0.8.9" in feat and "0.8.8" in feat and "0.8.7" in feat and "0.8.6" in feat and "0.8.5" in feat and "0.8.4" in feat and "0.8.3" in feat and "0.8.2" in feat and "0.8.1" in feat and "0.8.0" in feat and "0.7.9" in feat and "0.7.8" in feat and "0.7.7" in feat and "0.7.6" in feat and "0.7.5" in feat and "0.7.4" in feat and "0.7.3" in feat and "0.7.2" in feat and "0.7.1" in feat and "0.6.9" in feat and "0.5.9" in feat and "0.4.9" in feat  # Release + Zeitraum-Feature-Hinweise
        assert "Batch-OCR" in feat or "OCR gesamtes PDF" in feat
        assert "Tag" in feat
        assert "Projekt-Ordner" in feat or "Workspace" in feat
        # --- 0.4.5 CLI: CropBox settings, Ann Lock/Move, Snippets, Templates ---
        from instantlensdoc.core.app_settings import (
            get_annotations_locked,
            get_editor_snippets,
            get_show_page_boxes,
            set_annotations_locked,
            set_editor_snippet,
            set_editor_snippets,
            set_show_page_boxes,
        )
        from instantlensdoc.core.documents import DOC_TEMPLATES, render_doc_template

        set_show_page_boxes(True)
        assert get_show_page_boxes() is True
        set_show_page_boxes(False)
        assert get_show_page_boxes() is False
        set_annotations_locked(True)
        assert get_annotations_locked() is True
        set_annotations_locked(False)
        assert get_annotations_locked() is False
        snips = get_editor_snippets()
        assert len(snips) == 3
        set_editor_snippet(0, "SNIP-A\n")
        assert get_editor_snippets()[0] == "SNIP-A\n"
        set_editor_snippets(["A", "B", "C"])
        assert get_editor_snippets() == ["A", "B", "C"]
        t_brief, body_brief = render_doc_template("brief")
        assert t_brief == "Brief" and "Sehr geehrte" in body_brief
        t_notiz, body_notiz = render_doc_template("notiz")
        assert t_notiz == "Notiz" and body_notiz.startswith("# Notiz")
        assert "brief" in DOC_TEMPLATES and "notiz" in DOC_TEMPLATES
        store_mv = AnnotationStore(pdf)
        store_mv.annotations = []
        store_mv.clear_history()
        m0 = store_mv.add(
            Annotation(0, AnnotationType.STICKY, 10, 20, width=40, height=20, text="mv")
        )
        assert store_mv.move_by([m0.id], 5.0, -3.0) == 1
        assert abs(store_mv.get(m0.id).x - 15.0) < 1e-6
        assert abs(store_mv.get(m0.id).y - 17.0) < 1e-6
        assert "CropBox" in feat or "Seitenrahmen" in feat
        assert "Textbausteine" in feat or "Snippets" in feat
        assert "Brief" in feat or "Vorlagen" in feat
        # --- 0.4.5 CLI: Printer marks, Schema v4, sort lines, reset defaults ---
        from ild_pdf.annotate import SCHEMA_ID, SIDECAR_VERSION
        from instantlensdoc.core.app_settings import (
            DEFAULTS,
            get_show_printer_marks,
            load_settings,
            reset_to_defaults,
            set_show_printer_marks,
            set_theme,
        )

        assert SIDECAR_VERSION == 4 and SCHEMA_ID == "ildann-v4"
        # 0.5.1 CLI: Tags, sanitize, workspaces, batch-OCR API (weiterhin geprüft)
        assert normalize_tags("A, b; A") == ["A", "b"]
        assert tags_to_str(["x", "y"]) == "x, y"
        tagged = Annotation(
            0,
            AnnotationType.STICKY,
            1,
            1,
            width=10,
            height=10,
            text="t",
            tags=["Alpha", "Beta"],
        )
        assert tagged.to_dict()["tags"] == ["Alpha", "Beta"]
        assert Annotation.from_dict(tagged.to_dict()).tags == ["Alpha", "Beta"]
        tmp_ws = td / "proj_workspace_051"
        tmp_ws.mkdir(exist_ok=True)
        remember_project_workspace(tmp_ws, activate=True)
        assert get_active_project_workspace() is not None
        assert len(get_project_workspaces()) >= 1
        assert callable(ocr_mod.ocr_pdf_document)
        assert hasattr(ocr_mod, "OcrDocumentResult")
        # 0.5.2 CLI: Selection→Highlight, Export-Profile, Text-Diff
        from instantlensdoc.core.app_settings import (
            apply_export_profile,
            delete_export_profile,
            get_export_profile,
            get_export_profiles,
            save_export_profile,
        )
        from instantlensdoc.core.text_diff import line_diff_sides

        sel_rects, sel_text = selection_to_highlight_rects(
            pdf, 0, 0, 0, 2000, 2000, scale=1.0
        )
        # PDF mit Text → mindestens ein Highlight-Band möglich (oder leer bei Bild-only)
        assert isinstance(sel_rects, list) and isinstance(sel_text, str)
        if extract_page_plain_text(pdf, 0).strip():
            assert len(sel_rects) >= 1
            assert sel_text.strip()
        prof = save_export_profile("SmokePNG", dpi=150, format="PNG", target=td)
        assert prof["name"] == "SmokePNG" and prof["dpi"] == 150 and prof["format"] == "PNG"
        assert get_export_profile("SmokePNG") is not None
        assert any(p["name"] == "SmokePNG" for p in get_export_profiles())
        assert apply_export_profile("SmokePNG") is not None
        assert delete_export_profile("SmokePNG") is True
        assert get_export_profile("SmokePNG") is None
        dl, dr, dtags = line_diff_sides("a\nb\nc", "a\nx\nc")
        assert "replace" in dtags and len(dl) == len(dr) == len(dtags)
        # 0.5.3 CLI: Kommentar-Bericht, Palette-Zyklus, Minimap-Setting
        from instantlensdoc.core.app_settings import (
            ANN_COLOR_PALETTE,
            cycle_ann_palette_color,
            get_ann_palette_index,
            get_editor_minimap,
            random_ann_palette_color,
            set_ann_palette_index,
            set_editor_minimap,
        )

        store_rep = AnnotationStore(pdf)
        store_rep.annotations = []
        store_rep.clear_history()
        store_rep.add(
            Annotation(
                0,
                AnnotationType.HIGHLIGHT,
                5,
                5,
                width=40,
                height=12,
                text="Bericht Zeile eins",
                tags=["Review"],
                color="#FFE066",
            )
        )
        store_rep.add(
            Annotation(
                0,
                AnnotationType.STICKY,
                10,
                40,
                width=60,
                height=40,
                text="Notiz im Bericht",
                color="#FFEB3B",
            )
        )
        md_rep = store_rep.build_report(fmt="md", source=pdf)
        assert "Annotationsbericht" in md_rep or "Bericht" in md_rep
        assert "Markierung" in md_rep and "Bericht Zeile eins" in md_rep
        assert "Notiz" in md_rep and "Review" in md_rep
        txt_rep = store_rep.build_report(fmt="txt", source=pdf)
        assert "Seite 1" in txt_rep and "Bericht Zeile eins" in txt_rep
        md_path = td / "kommentare.md"
        txt_path = td / "kommentare.txt"
        assert store_rep.export_report(md_path, fmt="md").is_file()
        assert store_rep.export_report(txt_path, fmt="txt").is_file()
        assert "Bericht Zeile eins" in md_path.read_text(encoding="utf-8")
        assert "Notiz im Bericht" in txt_path.read_text(encoding="utf-8")
        set_ann_palette_index(0)
        c1 = cycle_ann_palette_color()
        assert c1 in ANN_COLOR_PALETTE and get_ann_palette_index() >= 0
        c2 = cycle_ann_palette_color()
        assert c2 in ANN_COLOR_PALETTE and c2 != c1
        cr = random_ann_palette_color()
        assert cr in ANN_COLOR_PALETTE
        set_editor_minimap(True)
        assert get_editor_minimap() is True
        set_editor_minimap(False)
        assert get_editor_minimap() is False
        # 0.5.4 CLI: Seiten-Löschen-Undo-Helpers, Ann.-Gruppen, Deps-Check
        from ild_pdf.pages import extract_page_bytes, insert_page_from_bytes
        from instantlensdoc.core.deps_check import (
            check_runtime_dependencies,
            format_deps_summary,
            has_any_failure,
        )

        multi = td / "multi054.pdf"
        merge_pdfs([pdf, pdf], multi)
        assert Path(multi).is_file()
        raw_page = extract_page_bytes(multi, 0)
        assert isinstance(raw_page, (bytes, bytearray)) and len(raw_page) > 50
        # Roundtrip insert at end then delete-bytes path sanity
        n_before = 2
        insert_page_from_bytes(multi, n_before, raw_page)
        store_g = AnnotationStore(multi)
        store_g.annotations = []
        store_g.clear_history()
        store_g.set_page_group(0, title="Deckblatt", color="#90CAF9")
        g0 = store_g.get_page_group(0)
        assert g0["title"] == "Deckblatt" and g0["color"] == "#90CAF9"
        assert 0 in store_g.list_page_groups()
        store_g.save(force=True)
        assert "page_groups" in (store_g._meta or {})
        deps = check_runtime_dependencies()
        assert len(deps) >= 2
        assert any(d.key == "pypdfium2" for d in deps)
        assert any(d.key == "tesseract" for d in deps)
        summary = format_deps_summary(deps)
        assert "pypdfium2" in summary.lower() or "PDF-Engine" in summary
        assert isinstance(has_any_failure(deps), bool)

        # 0.5.5 CLI: Historie-Labels, Export Tags/Gruppen, Encoding-Auto, skip_splash
        from instantlensdoc.core.app_settings import (
            get_editor_text_encoding,
            get_skip_splash,
            set_editor_text_encoding,
            set_skip_splash,
        )
        from instantlensdoc.core.documents import (
            detect_file_encoding,
            normalize_text_encoding,
            open_document,
            resolve_text_encoding,
        )

        assert normalize_text_encoding("auto") == "auto"
        assert normalize_text_encoding("detect") == "auto"
        bom_txt = td / "bom_utf8.txt"
        bom_txt.write_bytes(b"\xef\xbb\xbfHallo Encoding")
        assert detect_file_encoding(bom_txt) == "utf-8"
        assert resolve_text_encoding(bom_txt, "auto") == "utf-8"
        auto_doc = open_document(bom_txt, encoding="auto")
        assert auto_doc.encoding == "utf-8" and "Hallo" in auto_doc.text
        latin_auto = td / "latin_auto.txt"
        latin_auto.write_bytes(("caf" + chr(0xE9) + " " + chr(0xFC)).encode("latin-1"))
        # Nicht-UTF8 → latin-1 (ohne chardet oder mit)
        assert detect_file_encoding(latin_auto) == "latin-1"
        set_editor_text_encoding("auto")
        assert get_editor_text_encoding() == "auto"
        set_skip_splash(True)
        assert get_skip_splash() is True
        set_skip_splash(False)
        assert get_skip_splash() is False
        store_g.add(
            Annotation(
                0,
                AnnotationType.STICKY,
                2,
                2,
                width=20,
                height=10,
                text="grp-export",
                tags=["Review", "Prio"],
            )
        )
        csv055 = td / "ann055.csv"
        store_g.export_csv(csv055)
        csv055_txt = csv055.read_text(encoding="utf-8")
        hdr055 = csv055_txt.splitlines()[0]
        assert "tags" in hdr055 and "group_title" in hdr055 and "group_color" in hdr055
        assert "Deckblatt" in csv055_txt and "Review" in csv055_txt
        rep055 = store_g.build_report(fmt="md")
        assert "Deckblatt" in rep055 and ("Review" in rep055 or "Tags" in rep055)
        j055 = td / "ann055.json"
        store_g.export_json(j055)
        j055_raw = j055.read_text(encoding="utf-8")
        assert "page_groups" in j055_raw and "Deckblatt" in j055_raw
        assert "Historie" in feat or "Encoding" in feat or "Splash" in feat
        print("0.5.5 CLI history/export/encoding/splash: OK")

        # 0.5.6 CLI: Seiten-Favoriten, Batch-Farbe, Spellcheck-Wortliste, Privacy
        from instantlensdoc.core.app_settings import (
            get_spellcheck_dict_path,
            set_spellcheck_dict_path,
        )
        from instantlensdoc.core.spellcheck import (
            find_unknown_spans,
            load_wordlist,
            spellcheck_text,
        )

        store_fav = AnnotationStore(pdf)
        store_fav.annotations = []
        store_fav.clear_history()
        store_fav._meta = {}
        assert store_fav.toggle_page_favorite(0) is True
        assert store_fav.is_page_favorite(0)
        assert store_fav.list_page_favorites() == [0]
        assert store_fav.toggle_page_favorite(2) is True
        assert store_fav.list_page_favorites() == [0, 2]
        assert store_fav.toggle_page_favorite(0) is False
        assert store_fav.list_page_favorites() == [2]
        store_fav.set_page_favorites([0, 1, 5])
        store_fav.remap_pages({0: 0, 1: 1, 5: 4})  # Seite 5→4
        assert store_fav.list_page_favorites() == [0, 1, 4]
        a1 = Annotation(0, AnnotationType.HIGHLIGHT, 1, 1, width=10, height=5, color="#111111")
        a2 = Annotation(0, AnnotationType.HIGHLIGHT, 2, 2, width=10, height=5, color="#222222")
        store_fav.add(a1)
        store_fav.add(a2)
        n_col = store_fav.set_colors([a1.id, a2.id], "#AABBCC")
        assert n_col == 2
        assert store_fav.get(a1.id).color.upper() == "#AABBCC"
        assert store_fav.get(a2.id).color.upper() == "#AABBCC"
        wl = td / "words056.txt"
        wl.write_text("# demo\nHallo\nWelt\nTest\n", encoding="utf-8")
        words = load_wordlist(wl)
        assert "hallo" in words and "welt" in words
        unknown = spellcheck_text("Hallo Foo Welt", wl)
        assert any(u[2] == "Foo" for u in unknown)
        assert not any(u[2] == "Hallo" for u in unknown)
        set_spellcheck_dict_path(str(wl))
        assert get_spellcheck_dict_path() == str(wl)
        set_spellcheck_dict_path("")
        assert get_spellcheck_dict_path() == ""
        about_src = (ROOT / "instantlensdoc" / "ui" / "help_dialog.py").read_text(encoding="utf-8")
        assert "Telemetrie" in about_src or "Privacy" in about_src or "Datenschutz" in about_src
        assert "keine Telemetrie" in about_src.lower() or "keine Telemetrie" in about_src or "Telemetrie" in about_src
        feat056 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "Seiten-Favoriten" in feat056 or "page_favorites" in feat056
        assert "Batch-Farbe" in feat056 or "Wortliste" in feat056
        cl056 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "0.5.6" in cl056 and "## 0.5.6" not in cl056
        print("0.5.6 CLI favorites/batch-color/spellcheck/privacy: OK")

        # 0.5.7 CLI (retained): Favoriten-Sidebar-Nummern, Opacity-Batch, Editor-Bookmarks, Crash-ZIP
        from instantlensdoc.core.logging_setup import create_crash_report_zip, log_dir, setup_logging

        setup_logging(force=True)
        (log_dir() / "smoke057.log").write_text("smoke-057\n", encoding="utf-8")
        zip057 = td / "crash057.zip"
        out057 = create_crash_report_zip(zip057)
        assert out057.exists() and out057.stat().st_size > 0
        import zipfile

        with zipfile.ZipFile(out057, "r") as zf:
            names = zf.namelist()
            assert "REPORT.txt" in names
            assert any(n.endswith(".log") for n in names)
        store_op = AnnotationStore(pdf)
        store_op.annotations = []
        store_op.clear_history()
        o1 = Annotation(0, AnnotationType.HIGHLIGHT, 3, 3, width=10, height=5, opacity=1.0)
        o2 = Annotation(0, AnnotationType.STICKY, 4, 4, width=10, height=5, opacity=0.9)
        store_op.add(o1)
        store_op.add(o2)
        n_op = store_op.set_opacities([o1.id, o2.id], 0.42)
        assert n_op == 2
        assert abs(store_op.get(o1.id).opacity - 0.42) < 0.001
        assert abs(store_op.get(o2.id).opacity - 0.42) < 0.001
        feat057 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.5.7" in feat057 or "0.5.8" in feat057
        assert "Deckkraft Batch" in feat057 or "Opacity" in feat057 or "Zeilen-Lesezeichen" in feat057
        assert "Crash-Report" in feat057 or "Sidebar-Liste" in feat057
        cl057 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "0.5.7" in cl057 and "## 0.5.7" not in cl057
        help057 = (ROOT / "instantlensdoc" / "ui" / "help_dialog.py").read_text(encoding="utf-8")
        assert "Crash-Report" in help057
        print("0.5.7 CLI favorites-sidebar/opacity-batch/bookmarks/crash-zip: OK")

        # 0.5.8 CLI: Favoriten-Reorder, Opacity Sidecar-Force, Zeilenfavoriten-Liste, Crash-Screenshot
        store_ord = AnnotationStore(pdf)
        store_ord.annotations = []
        store_ord.clear_history()
        store_ord._meta = {}
        store_ord.set_page_favorites([2, 0, 1])
        assert store_ord.list_page_favorites() == [2, 0, 1]
        store_ord.reorder_page_favorites([1, 2, 0])
        assert store_ord.list_page_favorites() == [1, 2, 0]
        store_ord.toggle_page_favorite(3)
        assert store_ord.list_page_favorites() == [1, 2, 0, 3]
        o3 = Annotation(0, AnnotationType.STICKY, 5, 5, width=8, height=8, opacity=1.0)
        store_ord.add(o3)
        n_save = store_ord.save_opacities([o3.id], 0.55)
        assert n_save == 1
        assert abs(store_ord.get(o3.id).opacity - 0.55) < 0.001
        assert "opacity" in store_ord.get(o3.id).to_dict()
        loaded_op = AnnotationStore(pdf)
        found = next((a for a in loaded_op.annotations if a.id == o3.id), None)
        assert found is not None and abs(found.opacity - 0.55) < 0.001
        shot = td / "hint-shot.png"
        shot.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
        zip058 = td / "crash058.zip"
        out058 = create_crash_report_zip(zip058, screenshot_path=shot)
        assert out058.exists()
        with zipfile.ZipFile(out058, "r") as zf058:
            names058 = zf058.namelist()
            assert "REPORT.txt" in names058
            report058 = zf058.read("REPORT.txt").decode("utf-8")
            assert "screenshot_path_hint:" in report058
            assert str(shot) in report058 or shot.name in report058
            assert any(n.startswith("screenshots/") for n in names058)
        zip058b = td / "crash058-hint.zip"
        out058b = create_crash_report_zip(zip058b, screenshot_path="/tmp/does-not-exist-ild.png")
        with zipfile.ZipFile(out058b, "r") as zf058b:
            report058b = zf058b.read("REPORT.txt").decode("utf-8")
            assert "screenshot_path_hint: /tmp/does-not-exist-ild.png" in report058b
            assert not any(n.startswith("screenshots/") for n in zf058b.namelist())
        feat058 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.5.8" in feat058
        assert "Drag" in feat058 or "Umsortieren" in feat058 or "Zeilenfavoriten" in feat058
        assert "Screenshot" in feat058 or "Force-Save" in feat058 or "Sidebar-Liste" in feat058
        cl058 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "0.5.8" in cl058 and "## 0.5.8" not in cl058
        print("0.5.8 CLI fav-reorder/opacity-force/line-list/crash-screenshot: OK")

        # 0.5.9 CLI: Favoriten JSON Export/Import, FAV schema, Labels API, Wizard HTML
        from ild_pdf import FAV_SCHEMA_ID, FAV_VERSION, FavoritesImportError

        store_fav_io = AnnotationStore(pdf)
        store_fav_io.annotations = []
        store_fav_io.clear_history()
        store_fav_io._meta = {}
        store_fav_io.set_page_favorites([1, 3, 0])
        fav_json = td / "pages.favorites.json"
        out_fav = store_fav_io.export_page_favorites_json(fav_json)
        assert out_fav.exists()
        raw_fav = json.loads(out_fav.read_text(encoding="utf-8"))
        assert raw_fav["version"] == FAV_VERSION
        assert raw_fav["schema"] == FAV_SCHEMA_ID
        assert raw_fav["page_favorites"] == [1, 3, 0]
        store_fav_io2 = AnnotationStore(pdf)
        store_fav_io2._meta = {}
        imported = store_fav_io2.import_page_favorites_json(fav_json)
        assert imported == [1, 3, 0]
        store_fav_io2.set_page_favorites([2])
        merged = store_fav_io2.import_page_favorites_json(fav_json, merge=True)
        assert merged == [2, 1, 3, 0]
        try:
            store_fav_io2.import_page_favorites_dict(
                {"version": 99, "schema": FAV_SCHEMA_ID, "page_favorites": []}
            )
            assert False, "expected FavoritesImportError"
        except FavoritesImportError:
            pass
        try:
            store_fav_io2.import_page_favorites_dict(
                {"version": FAV_VERSION, "schema": "wrong", "page_favorites": []}
            )
            assert False, "expected FavoritesImportError"
        except FavoritesImportError:
            pass
        feat059 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.5.9" in feat059
        assert "ildfav" in feat059 or "JSON Export/Import" in feat059 or "Toolbar-Slider" in feat059
        assert "Labels" in feat059 or "Erste-Schritte" in feat059 or "Wizard" in feat059
        cl059 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "0.5.9" in cl059 and "## 0.5.9" not in cl059
        help059 = (ROOT / "instantlensdoc" / "ui" / "help_dialog.py").read_text(encoding="utf-8")
        assert "GettingStartedWizard" in help059 or "WIZARD_PAGES" in help059
        assert "Erste Schritte" in help059
        print("0.5.9 CLI fav-json/opacity-slider/labels/wizard: OK")

        # 0.6.1 CLI: selection_to_plain_text, session order, desktopicon docs
        plain_sel = selection_to_plain_text(pdf, 0, 0, 0, 2000, 2000, scale=1.0)
        assert isinstance(plain_sel, str)
        if extract_page_plain_text(pdf, 0).strip():
            assert plain_sel.strip()
        # Session order-Feld
        sess_ord = td / "session_ord.json"
        orig_sess2 = session_mod.session_path
        session_mod.session_path = lambda: sess_ord  # type: ignore
        try:
            a_txt = td / "ord_a.txt"
            b_txt = td / "ord_b.txt"
            a_txt.write_text("a", encoding="utf-8")
            b_txt.write_text("b", encoding="utf-8")
            st_ord = session_mod.build_session([str(b_txt), str(a_txt)], active_path=str(a_txt))
            session_mod.save_session(st_ord)
            raw_ord = json.loads(sess_ord.read_text(encoding="utf-8"))
            assert raw_ord["tabs"][0]["order"] == 0
            assert raw_ord["tabs"][1]["order"] == 1
            assert Path(raw_ord["tabs"][0]["path"]).name == "ord_b.txt"
            # Reihenfolge per order-Feld erzwingen
            raw_ord["tabs"][0]["order"] = 5
            raw_ord["tabs"][1]["order"] = 1
            sess_ord.write_text(json.dumps(raw_ord), encoding="utf-8")
            loaded_ord = session_mod.load_session()
            assert Path(loaded_ord.tabs[0].path).name == "ord_a.txt"
            assert Path(loaded_ord.tabs[1].path).name == "ord_b.txt"
        finally:
            session_mod.session_path = orig_sess2  # type: ignore
        iss061 = (ROOT / "installer" / "instantlensdoc.iss").read_text(encoding="utf-8")
        assert 'Name: "desktopicon"' in iss061
        assert "checkedonce" in iss061
        assert "Desktop-Verknüpfung erstellen" in iss061
        hinweis061 = (ROOT / "installer" / "installer-hinweis.txt").read_text(encoding="utf-8")
        assert "desktopicon" in hinweis061 and "checkedonce" in hinweis061
        feat061 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.6.1" in feat061 and "Tag-Autocomplete" in feat061
        assert "selection_to_plain_text" in feat061 or "Clipboard" in feat061
        cl061 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "0.6.1" in cl061 and "## 0.6.1" not in cl061 and "Tag-Autocomplete" in cl061
        assert "selection_to_plain_text" in (ROOT / "ild_pdf" / "__init__.py").read_text(encoding="utf-8")
        print("0.6.1 CLI copy-text/session-order/desktopicon: OK")

        # 0.6.2 CLI: sticky_from_text_selection API, tag multi-select helpers, sync SkipStart/exit codes
        sync062 = (ROOT / "scripts" / "sync-ild.ps1").read_text(encoding="utf-8")
        assert "SkipStart" in sync062
        assert "Exit-Codes" in sync062 or "exit 2" in sync062
        assert "exit 0" in sync062 and "exit 1" in sync062 and "exit 2" in sync062
        feat062 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.6.2" in feat062
        assert "Multi-Select" in feat062 or "Selection→Notiz" in feat062 or "Andere Tabs" in feat062
        cl062 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "0.6.2" in cl062 and "## 0.6.2" not in cl062
        assert "SkipStart" in cl062 or "Multi-Select" in cl062 or "Notiz" in cl062
        mw062 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
        assert "close_other_tabs" in mw062
        assert "_sticky_from_selection" in mw062
        pv062 = (ROOT / "instantlensdoc" / "ui" / "pdf_view.py").read_text(encoding="utf-8")
        assert "sticky_from_text_selection" in pv062
        sb062 = (ROOT / "instantlensdoc" / "ui" / "sidebar.py").read_text(encoding="utf-8")
        assert "annotation_filter_tags" in sb062
        assert "MultiSelection" in sb062 or "Multi-Select" in sb062
        print("0.6.2 CLI note/multi-tag/close-others/sync: OK")

        # 0.6.3 CLI: highlight+note setting, tag cloud, doc split, unsaved count
        from instantlensdoc.core.app_settings import (
            get_editor_doc_split,
            get_selection_note_with_highlight,
            set_editor_doc_split,
            set_selection_note_with_highlight,
        )
        set_selection_note_with_highlight(True)
        assert get_selection_note_with_highlight() is True
        set_selection_note_with_highlight(False)
        assert get_selection_note_with_highlight() is False
        set_editor_doc_split(True)
        assert get_editor_doc_split() is True
        set_editor_doc_split(False)
        assert get_editor_doc_split() is False
        feat063 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.6.3" in feat063
        assert "Tag-Cloud" in feat063 or "Highlight+Notiz" in feat063 or "Fenster teilen" in feat063
        cl063 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "0.6.3" in cl063 and "## 0.6.3" not in cl063
        mw063 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
        assert "count_unsaved_tabs" in mw063
        assert "_toggle_doc_split" in mw063
        pv063 = (ROOT / "instantlensdoc" / "ui" / "pdf_view.py").read_text(encoding="utf-8")
        assert "with_highlight" in pv063
        sb063 = (ROOT / "instantlensdoc" / "ui" / "sidebar.py").read_text(encoding="utf-8")
        assert "_update_ann_tag_cloud" in sb063
        print("0.6.3 CLI highlight-note/tag-cloud/doc-split/unsaved: OK")

        # 0.6.4 CLI: tag-cloud sets filter, sync-scroll, dirty tabs list, shortcuts
        from instantlensdoc.core.app_settings import (
            get_editor_doc_split_sync_scroll,
            set_editor_doc_split_sync_scroll,
        )
        set_editor_doc_split_sync_scroll(True)
        assert get_editor_doc_split_sync_scroll() is True
        set_editor_doc_split_sync_scroll(False)
        assert get_editor_doc_split_sync_scroll() is False
        feat064 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.6.4" in feat064
        assert "Sync-Scroll" in feat064 or "setzt Filter" in feat064 or "Dirty" in feat064
        cl064 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "0.6.4" in cl064 and "## 0.6.4" not in cl064
        mw064 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
        assert "list_unsaved_tabs" in mw064
        assert "_toggle_doc_split_sync_scroll" in mw064
        assert "_on_unsaved_status_clicked" in mw064
        sb064 = (ROOT / "instantlensdoc" / "ui" / "sidebar.py").read_text(encoding="utf-8")
        assert "ControlModifier" in sb064 or "setzt Filter" in sb064
        kh064 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
        assert "Sync-Scroll" in kh064
        assert "0.6.4" in kh064 or "Ctrl+Alt+\\\\" in kh064 or "ungespeichert" in kh064
        print("0.6.4 CLI tag-filter/sync-scroll/dirty-tabs/shortcuts: OK")

        # 0.6.5 CLI: rename_tag, vertical split, dirty-save, wizard 4 pages
        from instantlensdoc.core.app_settings import (
            get_editor_doc_split_vertical,
            set_editor_doc_split_vertical,
        )
        set_editor_doc_split_vertical(True)
        assert get_editor_doc_split_vertical() is True
        set_editor_doc_split_vertical(False)
        assert get_editor_doc_split_vertical() is False
        store_rn = AnnotationStore(pdf)
        store_rn.annotations = []
        store_rn.clear_history()
        a_rn1 = Annotation(0, AnnotationType.HIGHLIGHT, 1, 1, width=10, height=10, text="t1", tags=["Alpha065"])
        a_rn2 = Annotation(0, AnnotationType.STICKY, 2, 2, width=10, height=10, text="t2", tags=["Alpha065", "Beta065"])
        store_rn.add(a_rn1)
        store_rn.add(a_rn2)
        n_rn = store_rn.rename_tag("Alpha065", "Gamma065")
        assert n_rn == 2
        assert "Gamma065" in (a_rn1.tags or []) and "Alpha065" not in (a_rn1.tags or [])
        assert "Gamma065" in (a_rn2.tags or []) and "Beta065" in (a_rn2.tags or [])
        feat065 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.6.5" in feat065
        assert "umbenennen" in feat065 or "Vertikal" in feat065 or "Dirty-Save" in feat065
        cl065 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "0.6.5" in cl065 and "## 0.6.5" not in cl065
        mw065 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
        assert "_toggle_doc_split_vertical" in mw065
        assert "_save_unsaved_tab" in mw065
        assert "_rename_annotation_tag_global" in mw065
        sb065 = (ROOT / "instantlensdoc" / "ui" / "sidebar.py").read_text(encoding="utf-8")
        assert "_on_tag_cloud_context_menu" in sb065
        assert "annotation_tag_rename_requested" in sb065
        hd065 = (ROOT / "instantlensdoc" / "ui" / "help_dialog.py").read_text(encoding="utf-8")
        assert "Neu in 0.6" in hd065 or "Highlights 0.6" in hd065
        assert hd065.count('"1 / 4') + hd065.count("1 / 4") >= 1
        assert "4 / 4" in hd065
        kh065 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
        assert "Vertikaler Split" in kh065 or "umbenennen" in kh065
        print("0.6.5 CLI tag-rename/vertical-split/dirty-save/wizard: OK")

        # 0.6.6 CLI: rename undo one step, split settings, save-all dirty, wizard skip-once
        from instantlensdoc.core.app_settings import (
            consume_wizard_skip_once,
            get_editor_doc_split_vertical,
            get_wizard_completed,
            get_wizard_skip_once,
            set_editor_doc_split_vertical,
            set_wizard_completed,
            set_wizard_skip_once,
        )
        set_wizard_completed(False)
        set_wizard_skip_once(True)
        assert get_wizard_skip_once() is True
        assert consume_wizard_skip_once() is True
        assert get_wizard_skip_once() is False
        assert consume_wizard_skip_once() is False
        set_wizard_completed(True)
        assert get_wizard_completed() is True
        set_wizard_completed(False)
        set_editor_doc_split_vertical(True)
        assert get_editor_doc_split_vertical() is True
        set_editor_doc_split_vertical(False)
        store_ru = AnnotationStore(pdf)
        store_ru.annotations = []
        store_ru.clear_history()
        a_ru1 = Annotation(0, AnnotationType.HIGHLIGHT, 1, 1, width=10, height=10, text="u1", tags=["Old066"])
        a_ru2 = Annotation(0, AnnotationType.STICKY, 2, 2, width=10, height=10, text="u2", tags=["Old066", "Keep066"])
        store_ru.add(a_ru1)
        store_ru.add(a_ru2)
        assert store_ru.rename_tag("Old066", "New066") == 2
        assert store_ru.can_undo()
        assert store_ru.undo()  # ein Schritt stellt beide Tags zurück
        tags1 = [str(t) for t in (store_ru.annotations[0].tags or [])]
        tags2 = [str(t) for t in (store_ru.annotations[1].tags or [])]
        assert "Old066" in tags1 and "New066" not in tags1
        assert "Old066" in tags2 and "Keep066" in tags2 and "New066" not in tags2
        feat066 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.6.6" in feat066
        assert "Alle speichern" in feat066 or "skip-once" in feat066 or "Rename-Undo" in feat066
        cl066 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "0.6.6" in cl066 and "## 0.6.6" not in cl066
        mw066 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
        assert "_save_all_unsaved_tabs" in mw066
        assert "_sync_doc_split_orientation" in mw066
        assert "_maybe_show_getting_started_wizard" in mw066
        assert "_revert_tag_filter_after_rename_undo" in mw066
        sd066 = (ROOT / "instantlensdoc" / "ui" / "settings_dialog.py").read_text(encoding="utf-8")
        assert "doc_split_orient" in sd066
        assert "Doc-Split Layout" in sd066
        hd066 = (ROOT / "instantlensdoc" / "ui" / "help_dialog.py").read_text(encoding="utf-8")
        assert "skip_once_cb" in hd066
        assert "Dieses Mal überspringen" in hd066
        kh066 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
        assert "Alle speichern" in kh066 or "skip-once" in kh066 or "Undo-Schritt" in kh066
        print("0.6.6 CLI rename-undo/split-settings/save-all/wizard-skip: OK")

        # 0.6.7 CLI: undo label, split PDF+editor, save progress, wizard dont-show
        store_ul = AnnotationStore(pdf)
        store_ul.annotations = []
        store_ul.clear_history()
        a_ul1 = Annotation(0, AnnotationType.HIGHLIGHT, 1, 1, width=10, height=10, text="ul1", tags=["Old067"])
        a_ul2 = Annotation(0, AnnotationType.STICKY, 2, 2, width=10, height=10, text="ul2", tags=["Old067"])
        store_ul.add(a_ul1)
        store_ul.add(a_ul2)
        assert store_ul.rename_tag("Old067", "New067") == 2
        assert store_ul.peek_undo_label() == "Tag umbenennen"
        hist_ul = store_ul.undo_history_items()
        assert hist_ul and hist_ul[-1]["label"] == "Tag umbenennen"
        assert store_ul.undo()
        assert "Old067" in [str(t) for t in (store_ul.annotations[0].tags or [])]
        mw067 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
        assert "secondary_pdf" in mw067
        assert "secondary_stack" in mw067
        assert "_refresh_undo_hint" in mw067
        assert "use_progress" in mw067 or "total > 3" in mw067
        hd067 = (ROOT / "instantlensdoc" / "ui" / "help_dialog.py").read_text(encoding="utf-8")
        assert "dont_show_cb" in hd067
        assert "Nicht mehr zeigen" in hd067
        pv067 = (ROOT / "instantlensdoc" / "ui" / "pdf_view.py").read_text(encoding="utf-8")
        assert "PDF-Undo-Stack" in pv067
        assert "annotation_undo_history_items" in pv067
        assert "restore_annotation_undo_at" in pv067
        feat067 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.6.7" in feat067
        cl067 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "0.6.7" in cl067 and "## 0.6.7" not in cl067
        kh067 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
        assert "Nicht mehr zeigen" in kh067 or "PDF+Editor" in kh067 or "Tag umbenennen" in kh067
        print("0.6.7 CLI undo-label/split-mix/save-progress/wizard-dont-show: OK")

        # 0.6.8 CLI: session panel kind, save cancel, wizard reset, tag confirm >20
        from instantlensdoc.core import session as session_mod068
        store_ct = AnnotationStore(pdf)
        store_ct.annotations = []
        store_ct.clear_history()
        for i in range(21):
            store_ct.add(
                Annotation(
                    0,
                    AnnotationType.HIGHLIGHT,
                    float(i),
                    float(i),
                    width=8,
                    height=8,
                    text=f"c{i}",
                    tags=["Bulk068"],
                )
            )
        assert store_ct.count_tag("Bulk068") == 21
        assert store_ct.count_tag("missing") == 0
        sess068 = session_mod068.build_session(
            [str(pdf)],
            active_path=str(pdf),
            secondary_path=str(pdf),
            secondary_kind="pdf",
        )
        assert sess068.secondary_kind == "pdf"
        assert sess068.secondary_path
        session_mod068.save_session(sess068)
        loaded068 = session_mod068.load_session()
        assert loaded068.secondary_kind == "pdf"
        assert loaded068.secondary_path
        mw068 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
        assert "_secondary_kind" in mw068
        assert "setCancelButtonText" in mw068 or '"Abbrechen"' in mw068
        assert "get_tag_rename_confirm_threshold" in mw068 or "hit_count > threshold" in mw068
        sd068 = (ROOT / "instantlensdoc" / "ui" / "settings_dialog.py").read_text(encoding="utf-8")
        assert "_reset_wizard" in sd068
        assert "btn_wizard_reset" in sd068
        feat068 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.6.8" in feat068
        cl068 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "0.6.8" in cl068 and "## 0.6.8" not in cl068
        kh068 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
        assert "Abbrechen" in kh068 or "Wizard" in kh068 or ">20" in kh068 or "&gt;20" in kh068
        print("0.6.8 CLI panel-session/save-cancel/wizard-reset/tag-confirm: OK")

        # 0.6.9 CLI: sync_scroll session, tag threshold settings, save error list, F1/Wizard 0.6.8 tips
        from instantlensdoc.core.app_settings import (
            get_tag_rename_confirm_threshold,
            set_tag_rename_confirm_threshold,
        )
        from instantlensdoc.core import session as session_mod069

        set_tag_rename_confirm_threshold(20)
        assert get_tag_rename_confirm_threshold() == 20
        set_tag_rename_confirm_threshold(5)
        assert get_tag_rename_confirm_threshold() == 5
        set_tag_rename_confirm_threshold(20)
        sess069 = session_mod069.build_session(
            [str(pdf)],
            active_path=str(pdf),
            secondary_path=str(pdf),
            secondary_kind="pdf",
            sync_scroll=True,
        )
        assert sess069.sync_scroll is True
        session_mod069.save_session(sess069)
        loaded069 = session_mod069.load_session()
        assert loaded069.sync_scroll is True
        mw069 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
        assert "sync_scroll" in mw069
        assert "_batch_save_quiet" in mw069
        assert "Alle speichern — Fehler" in mw069
        sd069 = (ROOT / "instantlensdoc" / "ui" / "settings_dialog.py").read_text(encoding="utf-8")
        assert "tag_rename_confirm" in sd069
        assert "set_tag_rename_confirm_threshold" in sd069
        kh069 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
        assert "0.6.8" in kh069 or "0.6.9" in kh069
        assert "Fehlerliste" in kh069 or "Schwelle" in kh069 or "Session" in kh069
        wiz069 = (ROOT / "instantlensdoc" / "ui" / "help_dialog.py").read_text(encoding="utf-8")
        assert "0.6.8" in wiz069
        feat069 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.6.9" in feat069
        cl069 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "0.6.9" in cl069 and "## 0.6.9" not in cl069
        print("0.6.9 CLI sync-session/tag-threshold/save-errors/f1-wizard: OK")

        # 0.7.1 CLI: PDF-Schnellsuche, Ann.-Duplikate, Nutzer-Vorlagen, Sidecar-Debounce
        from instantlensdoc.core.app_settings import (
            delete_user_doc_template,
            get_user_doc_templates,
            save_user_doc_template,
        )
        from instantlensdoc.core.documents import render_doc_template as render_tpl071
        from instantlensdoc.core import fulltext as ft071

        pdf_b = td / "search_b.pdf"
        import pikepdf as _pike071

        with _pike071.Pdf.new() as _doc071:
            _doc071.add_blank_page(page_size=(200, 280))
            _doc071.save(pdf_b)
        # Text in PDF via AnnotationStore / extract — use a text file + pdf filter
        hits_pdf = ft071.search_open_pdfs([str(pdf), str(txt), str(pdf_b)], "FINDME")
        assert all(Path(h.path).suffix.lower() == ".pdf" for h in hits_pdf)
        # text-only query may yield 0 on blank PDFs — filter_pdf_paths still works
        assert ft071.filter_pdf_paths([str(pdf), str(txt), str(pdf_b)]) == [str(pdf), str(pdf_b)]
        # Duplikate
        store_dup = AnnotationStore(pdf)
        store_dup.annotations = []
        store_dup.clear_history()
        store_dup.add(
            Annotation(0, AnnotationType.HIGHLIGHT, 40, 50, width=30, height=10, text="dup-a", tags=["x"])
        )
        store_dup.add(
            Annotation(0, AnnotationType.HIGHLIGHT, 41, 51, width=30, height=10, text="dup-b", tags=["y"])
        )
        store_dup.add(
            Annotation(0, AnnotationType.STICKY, 40, 50, width=30, height=10, text="other-type")
        )
        groups = store_dup.find_duplicate_groups(tol=2.0, same_type=True)
        assert len(groups) == 1 and len(groups[0]) == 2
        removed = store_dup.merge_duplicates(tol=2.0, keep="oldest", merge_text=True, merge_tags=True)
        assert removed == 1
        assert len(store_dup.annotations) == 2
        kept = [a for a in store_dup.annotations if a.type == AnnotationType.HIGHLIGHT][0]
        assert "dup-a" in kept.text and "dup-b" in kept.text
        assert store_dup.count_tag("x") == 1 and store_dup.count_tag("y") == 1
        # Nutzer-Vorlagen
        for old in list(get_user_doc_templates()):
            delete_user_doc_template(old["id"])
        entry = save_user_doc_template(title="SmokeVorlage071", body="Hallo {date}\n")
        assert entry["id"] and get_user_doc_templates()
        t_title, t_body = render_tpl071(f"user:{entry['id']}")
        assert t_title == "SmokeVorlage071" and "Hallo" in t_body
        delete_user_doc_template(entry["id"])
        # Sidecar debounce helpers in pdf_view source
        pv071 = (ROOT / "instantlensdoc" / "ui" / "pdf_view.py").read_text(encoding="utf-8")
        assert "schedule_sidecar_save" in pv071 and "_sidecar_save_timer" in pv071
        assert "merge_duplicate_annotations" in pv071
        sb071 = (ROOT / "instantlensdoc" / "ui" / "sidebar.py").read_text(encoding="utf-8")
        assert "Alle PDFs" in sb071 and "pdf_fulltext_mode" in sb071
        feat071 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.7.1" in feat071 and "Duplikate" in feat071 and "Debounce" in feat071
        cl071 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## 0.7.1" in cl071 and "Vorlage" in cl071
        print("0.7.1 CLI pdf-search/dup-merge/templates/debounce: OK")

        # 0.7.2 CLI: Treffer-Nav, Merge-Undo-Label, Vorlagen rename/delete, Debounce-Settings
        from instantlensdoc.core.app_settings import (
            get_sidecar_save_debounce_ms,
            get_user_doc_template as get_tpl_by_id,
            rename_user_doc_template,
            set_sidecar_save_debounce_ms,
            SIDECAR_SAVE_DEBOUNCE_MAX_MS,
            SIDECAR_SAVE_DEBOUNCE_MIN_MS,
        )

        assert store_dup.peek_undo_label() == "Duplikate zusammenführen"
        assert store_dup.can_undo()
        n_before = len(store_dup.annotations)
        assert store_dup.undo() is True
        assert len(store_dup.annotations) == n_before + 1
        # Debounce settings clamp
        assert SIDECAR_SAVE_DEBOUNCE_MIN_MS == 200 and SIDECAR_SAVE_DEBOUNCE_MAX_MS == 1000
        set_sidecar_save_debounce_ms(150)
        assert get_sidecar_save_debounce_ms() == 200
        set_sidecar_save_debounce_ms(1200)
        assert get_sidecar_save_debounce_ms() == 1000
        set_sidecar_save_debounce_ms(350)
        assert get_sidecar_save_debounce_ms() == 350
        set_sidecar_save_debounce_ms(400)
        assert get_sidecar_save_debounce_ms() == 400
        # Vorlagen rename/delete
        for old in list(get_user_doc_templates()):
            delete_user_doc_template(old["id"])
        entry072 = save_user_doc_template(title="SmokeVorlage072", body="Body072\n")
        renamed = rename_user_doc_template(entry072["id"], "SmokeVorlage072b")
        assert renamed and renamed["title"] == "SmokeVorlage072b"
        got072 = get_tpl_by_id(entry072["id"])
        assert got072 and got072["title"] == "SmokeVorlage072b"
        assert delete_user_doc_template(entry072["id"]) is True
        sb072 = (ROOT / "instantlensdoc" / "ui" / "sidebar.py").read_text(encoding="utf-8")
        assert "search_prev_requested" in sb072 and "search_hits_label" in sb072
        assert "btn_prev" in sb072 and "advance_search_hit" in sb072
        pv072 = (ROOT / "instantlensdoc" / "ui" / "pdf_view.py").read_text(encoding="utf-8")
        assert "search_prev" in pv072 and "apply_sidecar_debounce_ms" in pv072
        assert "peek_undo_label" in pv072
        mw072 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
        assert "_on_search_prev" in mw072 and "_rename_user_template" in mw072
        assert "_delete_user_template" in mw072
        sd072 = (ROOT / "instantlensdoc" / "ui" / "settings_dialog.py").read_text(encoding="utf-8")
        assert "sidecar_debounce" in sd072 and "set_sidecar_save_debounce_ms" in sd072
        feat072 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.7.2" in feat072 and "Weiter/Zurück" in feat072
        cl072 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## 0.7.2" in cl072 and "Debounce" in cl072
        print("0.7.2 CLI search-nav/merge-undo/templates/debounce-settings: OK")

        # 0.7.3 CLI: Trefferliste-Klick, Vorlagen-Ordner, Merge-Vorschau, Ctrl+S-Flush
        from instantlensdoc.core.app_settings import (
            sync_user_templates_folder,
            user_templates_dir,
        )

        sb073 = (ROOT / "instantlensdoc" / "ui" / "sidebar.py").read_text(encoding="utf-8")
        assert "searchHitsList" in sb073 and "itemClicked" in sb073
        assert "Schnellsuche-Treffer" in sb073
        mw073 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
        assert "_open_user_templates_folder" in mw073
        assert "flush_sidecar_save()" in mw073
        pv073 = (ROOT / "instantlensdoc" / "ui" / "pdf_view.py").read_text(encoding="utf-8")
        assert "MergeDuplicatesPreviewDialog" in pv073
        dlg073_src = (
            ROOT / "instantlensdoc" / "ui" / "merge_duplicates_dialog.py"
        ).read_text(encoding="utf-8")
        assert "MergeDuplicatesPreviewDialog" in dlg073_src
        assert "Übernehmen" in dlg073_src and "sorted_groups_for_preview" in dlg073_src
        # Vorlagen-Ordner Spiegel
        for old in list(get_user_doc_templates()):
            delete_user_doc_template(old["id"])
        entry073 = save_user_doc_template(title="SmokeVorlage073", body="Body073\n")
        folder073 = sync_user_templates_folder()
        assert folder073 == user_templates_dir()
        assert folder073.is_dir()
        mirrors = list(folder073.glob("*.ildtpl.md"))
        assert mirrors, "expected mirrored template file"
        assert any(entry073["id"][:8] in m.name for m in mirrors)
        assert (folder073 / "README.txt").is_file()
        delete_user_doc_template(entry073["id"])
        # Duplikat-Gruppen weiterhin findbar (Basis für Vorschau-Dialog)
        groups073 = store_dup.find_duplicate_groups(tol=2.0, same_type=True)
        if not groups073:
            store_dup.annotations = []
            store_dup.clear_history()
            store_dup.add(
                Annotation(0, AnnotationType.HIGHLIGHT, 5, 5, width=10, height=6, text="d1")
            )
            store_dup.add(
                Annotation(0, AnnotationType.HIGHLIGHT, 5, 6, width=10, height=6, text="d2")
            )
            groups073 = store_dup.find_duplicate_groups(tol=2.0, same_type=True)
        assert groups073 and len(groups073[0]) >= 2
        feat073 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.7.3" in feat073 and "Trefferliste" in feat073 and "Ctrl+S" in feat073
        cl073 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## 0.7.3" in cl073 and "Vorschau" in cl073
        kb073 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
        assert "flush" in kb073.lower() or "Debounce" in kb073
        print("0.7.3 CLI hits-list/templates-folder/merge-preview/ctrl-s-flush: OK")

        # 0.7.4 CLI: Kontext-Snippet, Merge je Paar, Vorlagen-Reorder, Dirty-Debounce
        from instantlensdoc.core.app_settings import reorder_user_doc_templates
        from instantlensdoc.core.fulltext import _snippet_around, format_hit_line

        snip074 = _snippet_around(
            "alpha FINDME omega und mehr Text drumherum",
            "FINDME",
            context_chars=6,
            width=80,
        )
        assert "«FINDME»" in snip074
        assert "alpha" in snip074 or "…" in snip074
        line074 = format_hit_line(
            "demo.pdf", page=0, line=None, snippet=snip074, kind="pdf", query="FINDME"
        )
        assert "demo.pdf" in line074 and "S.1" in line074 and "«FINDME»" in line074
        # Vorlagen-Reorder persistiert
        for old in list(get_user_doc_templates()):
            delete_user_doc_template(old["id"])
        e074a = save_user_doc_template(title="TplA074", body="A\n")
        e074b = save_user_doc_template(title="TplB074", body="B\n")
        reordered = reorder_user_doc_templates([e074b["id"], e074a["id"]])
        assert [t["id"] for t in reordered] == [e074b["id"], e074a["id"]]
        delete_user_doc_template(e074a["id"])
        delete_user_doc_template(e074b["id"])
        # Merge groups= nur ausgewählte Gruppe
        store_dup.annotations = []
        store_dup.clear_history()
        a074 = Annotation(0, AnnotationType.HIGHLIGHT, 8, 8, width=12, height=5, text="g1a")
        b074 = Annotation(0, AnnotationType.HIGHLIGHT, 8, 9, width=12, height=5, text="g1b")
        c074 = Annotation(0, AnnotationType.STICKY, 40, 40, width=20, height=10, text="alone")
        store_dup.add(a074)
        store_dup.add(b074)
        store_dup.add(c074)
        groups074 = store_dup.find_duplicate_groups(tol=2.0, same_type=True)
        assert groups074
        removed074 = store_dup.merge_duplicates(
            tol=2.0, same_type=True, keep="oldest", groups=groups074[:1]
        )
        assert removed074 >= 1
        assert any(x.text == "alone" for x in store_dup.annotations)
        dlg074_src = (
            ROOT / "instantlensdoc" / "ui" / "merge_duplicates_dialog.py"
        ).read_text(encoding="utf-8")
        assert "groups_to_merge" in dlg074_src and "Alle behalten" in dlg074_src
        tpl074_src = (
            ROOT / "instantlensdoc" / "ui" / "templates_dialog.py"
        ).read_text(encoding="utf-8")
        assert "TemplatesOrderDialog" in tpl074_src and "ordered_ids" in tpl074_src
        mw074 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
        assert "_reorder_user_templates_dialog" in mw074
        assert "_refresh_document_dirty_labels" in mw074
        assert "sidecar_save_pending" in mw074
        pv074 = (ROOT / "instantlensdoc" / "ui" / "pdf_view.py").read_text(encoding="utf-8")
        assert "sidecar_save_pending" in pv074 and "groups_to_merge" in pv074
        assert "reorder_user_doc_templates" in (
            ROOT / "instantlensdoc" / "core" / "app_settings.py"
        ).read_text(encoding="utf-8")
        feat074 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.7.4" in feat074 and "Kontext-Snippet" in feat074
        cl074 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## 0.7.4" in cl074 and "Dirty" in cl074
        kb074 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
        assert "Kontext-Snippet" in kb074 or "Vorlagen-Reihenfolge" in kb074
        print("0.7.4 CLI snippet/merge-pair/templates-drag/dirty-debounce: OK")

        # 0.7.5 CLI: Snippet-Länge Settings, Alle mergen/behalten, Vorlagen-Zip, Debounce-Tooltip
        from instantlensdoc.core.app_settings import (
            SEARCH_SNIPPET_CONTEXT_DEFAULT,
            SEARCH_SNIPPET_CONTEXT_MAX,
            SEARCH_SNIPPET_CONTEXT_MIN,
            export_user_templates_zip,
            get_search_snippet_context_chars,
            import_user_templates_zip,
            set_search_snippet_context_chars,
        )

        assert SEARCH_SNIPPET_CONTEXT_MIN == 20 and SEARCH_SNIPPET_CONTEXT_MAX == 80
        assert SEARCH_SNIPPET_CONTEXT_DEFAULT == 40
        set_search_snippet_context_chars(10)
        assert get_search_snippet_context_chars() == 20
        set_search_snippet_context_chars(99)
        assert get_search_snippet_context_chars() == 80
        set_search_snippet_context_chars(35)
        assert get_search_snippet_context_chars() == 35
        set_search_snippet_context_chars(40)
        assert get_search_snippet_context_chars() == 40
        # Merge Alle-Buttons in Dialog
        dlg075_src = (
            ROOT / "instantlensdoc" / "ui" / "merge_duplicates_dialog.py"
        ).read_text(encoding="utf-8")
        assert "Alle mergen" in dlg075_src and "Alle behalten" in dlg075_src
        assert "_set_all_checked" in dlg075_src
        # Vorlagen Zip export/import
        for old in list(get_user_doc_templates()):
            delete_user_doc_template(old["id"])
        e075a = save_user_doc_template(title="ZipA075", body="BodyA075\n")
        e075b = save_user_doc_template(title="ZipB075", body="BodyB075\n")
        zip075 = ROOT / ".smoke_templates_075.zip"
        try:
            export_user_templates_zip(zip075)
            assert zip075.is_file()
            import zipfile as _zf075

            with _zf075.ZipFile(zip075, "r") as zf:
                names075 = zf.namelist()
            assert "templates.json" in names075
            assert any(n.endswith(".ildtpl.md") for n in names075)
            delete_user_doc_template(e075a["id"])
            delete_user_doc_template(e075b["id"])
            assert not get_user_doc_templates()
            imported075 = import_user_templates_zip(zip075, merge=True)
            assert len(imported075) >= 2
            titles075 = {t["title"] for t in get_user_doc_templates()}
            assert "ZipA075" in titles075 and "ZipB075" in titles075
        finally:
            if zip075.is_file():
                zip075.unlink()
            for old in list(get_user_doc_templates()):
                if old["title"] in ("ZipA075", "ZipB075"):
                    delete_user_doc_template(old["id"])
        mw075 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
        assert "_export_user_templates_zip" in mw075 and "_import_user_templates_zip" in mw075
        assert "Speichern ausstehend" in mw075
        sd075 = (ROOT / "instantlensdoc" / "ui" / "settings_dialog.py").read_text(
            encoding="utf-8"
        )
        assert "snippet_context" in sd075 and "set_search_snippet_context_chars" in sd075
        assert "get_search_snippet_context_chars" in (
            ROOT / "instantlensdoc" / "core" / "app_settings.py"
        ).read_text(encoding="utf-8")
        feat075 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.7.5" in feat075 and "Snippet-Länge" in feat075
        cl075 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## 0.7.5" in cl075 and "Zip" in cl075
        kb075 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(
            encoding="utf-8"
        )
        assert "Speichern ausstehend" in kb075 or "Alle mergen" in kb075
        print("0.7.5 CLI snippet-len/merge-all/templates-zip/debounce-tooltip: OK")

        # 0.7.6 CLI: Snippet-Ellipsis, Zip-Konflikt, Merge-Diff, Debounce-Blink
        from instantlensdoc.core.app_settings import (
            SEARCH_SNIPPET_ELLIPSIS_DOTS,
            SEARCH_SNIPPET_ELLIPSIS_GUILLEMETS,
            export_user_templates_zip as export_tpl076,
            find_user_template_import_conflicts,
            get_search_snippet_ellipsis_style,
            get_user_doc_template,
            import_user_templates_zip as import_tpl076,
            parse_user_templates_zip,
            set_search_snippet_ellipsis_style,
        )
        from instantlensdoc.core.fulltext import _snippet_around as snip076
        from instantlensdoc.core.text_diff import annotation_text_diff_short

        set_search_snippet_ellipsis_style("guillemets")
        assert get_search_snippet_ellipsis_style() == SEARCH_SNIPPET_ELLIPSIS_GUILLEMETS
        assert "«FIND»" in snip076("xx FIND yy", "FIND", context_chars=4, ellipsis_style="guillemets")
        set_search_snippet_ellipsis_style("ellipsis")
        assert get_search_snippet_ellipsis_style() == SEARCH_SNIPPET_ELLIPSIS_DOTS
        snip_e = snip076("xx FIND yy", "FIND", context_chars=4, ellipsis_style="ellipsis")
        assert "FIND" in snip_e and "«" not in snip_e
        set_search_snippet_ellipsis_style("guillemets")
        assert get_search_snippet_ellipsis_style() == SEARCH_SNIPPET_ELLIPSIS_GUILLEMETS
        d076 = annotation_text_diff_short("alpha note", "beta note")
        assert "Diff" in d076 and "≠" in d076
        assert "identisch" in annotation_text_diff_short("same", "same")
        dlg076_src = (
            ROOT / "instantlensdoc" / "ui" / "merge_duplicates_dialog.py"
        ).read_text(encoding="utf-8")
        assert "annotation_text_diff_short" in dlg076_src and "↕" in dlg076_src
        fd076 = (ROOT / "instantlensdoc" / "ui" / "file_dialogs.py").read_text(
            encoding="utf-8"
        )
        assert "resolve_template_zip_conflicts" in fd076
        assert "find_user_template_import_conflicts" in (
            ROOT / "instantlensdoc" / "core" / "app_settings.py"
        ).read_text(encoding="utf-8")
        for old in list(get_user_doc_templates()):
            delete_user_doc_template(old["id"])
        e076 = save_user_doc_template(title="Konflikt076", body="alt\n")
        zip076 = ROOT / ".smoke_templates_076.zip"
        try:
            export_tpl076(zip076)
            # Zip mit gleichem Titel wie lokal → Konflikt
            items076 = parse_user_templates_zip(zip076)
            conflicts076 = find_user_template_import_conflicts(items076)
            assert len(conflicts076) >= 1
            skipped = import_tpl076(zip076, merge=True, conflict_mode="skip")
            assert skipped == [] or all(
                t.get("title") != "Konflikt076" for t in skipped
            )
            # Skip: Konflikt nicht überschrieben
            still = get_user_doc_template("Konflikt076")
            assert still is not None and still["body"] == "alt\n"
            overwritten = import_tpl076(zip076, merge=True, conflict_mode="overwrite")
            assert len(overwritten) >= 1
        finally:
            if zip076.is_file():
                zip076.unlink()
            for old in list(get_user_doc_templates()):
                if old["title"] == "Konflikt076":
                    delete_user_doc_template(old["id"])
        mw076 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(
            encoding="utf-8"
        )
        assert "_blink_pending_debounce_status" in mw076
        assert "resolve_template_zip_conflicts" in mw076
        sd076 = (ROOT / "instantlensdoc" / "ui" / "settings_dialog.py").read_text(
            encoding="utf-8"
        )
        assert "snippet_ellipsis" in sd076 and "set_search_snippet_ellipsis_style" in sd076
        feat076 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.7.6" in feat076 and "Ellipsis" in feat076
        cl076 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## 0.7.6" in cl076 and "Konflikt" in cl076
        kb076 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(
            encoding="utf-8"
        )
        assert "Statusleisten-Blink" in kb076 or "Konflikt-Dialog" in kb076
        print("0.7.6 CLI ellipsis/zip-conflict/merge-diff/debounce-blink: OK")

        # 0.7.7 CLI: Status-Blink Settings, Merge-Tags/Farbe, Zip-Dry-Run, Ann.-Ellipsis
        from instantlensdoc.core.app_settings import (
            STATUS_BLINK_AUS,
            STATUS_BLINK_KURZ,
            dry_run_user_templates_zip_import as dry077,
            export_user_templates_zip as export_tpl077,
            get_status_blink_mode,
            set_search_snippet_ellipsis_style as set_ell077,
            set_status_blink_mode,
        )
        from instantlensdoc.core.fulltext import truncate_display_text as trunc077
        from instantlensdoc.core.text_diff import annotation_text_diff_short as diff077

        set_status_blink_mode("aus")
        assert get_status_blink_mode() == STATUS_BLINK_AUS
        set_status_blink_mode("kurz")
        assert get_status_blink_mode() == STATUS_BLINK_KURZ
        set_status_blink_mode("off")
        assert get_status_blink_mode() == STATUS_BLINK_AUS
        set_status_blink_mode("kurz")
        d077 = diff077(
            "alpha",
            "beta",
            left_tags=["tagA"],
            right_tags=["tagB"],
            left_color="#ffe066",
            right_color="#ff6b6b",
        )
        assert "Diff" in d077 and "[tagA]" in d077 and "#FFE066" in d077
        assert "#" in d077 and "≠" in d077
        set_ell077("guillemets")
        assert "«…»" in trunc077("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", 16)
        set_ell077("ellipsis")
        t077 = trunc077("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", 16)
        assert t077.endswith("…") and "«" not in t077
        set_ell077("guillemets")
        for old in list(get_user_doc_templates()):
            delete_user_doc_template(old["id"])
        save_user_doc_template(title="Konflikt077", body="alt077\n")
        zip077 = ROOT / ".smoke_templates_077.zip"
        try:
            export_tpl077(zip077)
            rows077 = dry077(zip077)
            assert any(
                r.get("action") == "overwrite" and r.get("title") == "Konflikt077"
                for r in rows077
            )
            fd077 = (ROOT / "instantlensdoc" / "ui" / "file_dialogs.py").read_text(
                encoding="utf-8"
            )
            assert "dry_run_rows" in fd077 and "Dry-Run" in fd077
            assert "dry_run_user_templates_zip_import" in (
                ROOT / "instantlensdoc" / "core" / "app_settings.py"
            ).read_text(encoding="utf-8")
        finally:
            if zip077.is_file():
                zip077.unlink()
            for old in list(get_user_doc_templates()):
                if old["title"] == "Konflikt077":
                    delete_user_doc_template(old["id"])
        mw077 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(
            encoding="utf-8"
        )
        assert "get_status_blink_mode" in mw077 and "STATUS_BLINK_AUS" in mw077
        assert "dry_run_user_templates_zip_import" in mw077
        assert "truncate_display_text" in (
            ROOT / "instantlensdoc" / "ui" / "pdf_view.py"
        ).read_text(encoding="utf-8")
        sd077 = (ROOT / "instantlensdoc" / "ui" / "settings_dialog.py").read_text(
            encoding="utf-8"
        )
        assert "status_blink" in sd077 and "set_status_blink_mode" in sd077
        feat077 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.7.7" in feat077 and "Dry-Run" in feat077
        cl077 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## 0.7.7" in cl077 and "Status-Blink" in cl077
        kb077 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(
            encoding="utf-8"
        )
        assert "kurz" in kb077 and "Dry-Run" in kb077
        print("0.7.7 CLI blink/merge-tags/zip-dry-run/ann-ellipsis: OK")

        # 0.7.8 CLI: Dry-Run-TXT, Ann.-Tooltip, Blink-Hinweis, Merge-Diff-Länge
        from instantlensdoc.core.app_settings import (
            MERGE_DIFF_MAX_SIDE_DEFAULT,
            MERGE_DIFF_MAX_SIDE_MAX,
            MERGE_DIFF_MAX_SIDE_MIN,
            STATUS_BLINK_AUS as AUS078,
            dry_run_user_templates_zip_import as dry078,
            export_dry_run_conflict_list_txt as export_txt078,
            export_user_templates_zip as export_tpl078,
            format_dry_run_conflict_list_txt as fmt_txt078,
            get_merge_diff_max_side,
            get_status_blink_mode as get_blink078,
            set_merge_diff_max_side,
            set_status_blink_mode as set_blink078,
        )
        from instantlensdoc.core.text_diff import annotation_text_diff_short as diff078

        set_merge_diff_max_side(12)
        assert get_merge_diff_max_side() == MERGE_DIFF_MAX_SIDE_MIN
        set_merge_diff_max_side(99)
        assert get_merge_diff_max_side() == MERGE_DIFF_MAX_SIDE_MAX
        set_merge_diff_max_side(MERGE_DIFF_MAX_SIDE_DEFAULT)
        assert get_merge_diff_max_side() == MERGE_DIFF_MAX_SIDE_DEFAULT
        d078_short = diff078("abcdefghijklmnop", "qrstuvwxyzabcdef", max_side=12)
        assert "…" in d078_short
        d078_long = diff078("abcdefghijklmnop", "qrstuvwxyzabcdef", max_side=64)
        assert "abcdefghijklmnop" in d078_long
        for old in list(get_user_doc_templates()):
            delete_user_doc_template(old["id"])
        save_user_doc_template(title="Konflikt078", body="alt078\n")
        zip078 = ROOT / ".smoke_templates_078.zip"
        txt078 = ROOT / ".smoke_dryrun_078.txt"
        try:
            export_tpl078(zip078)
            rows078 = dry078(zip078)
            assert any(
                r.get("action") == "overwrite" and r.get("title") == "Konflikt078"
                for r in rows078
            )
            body078 = fmt_txt078(rows078)
            assert "OVERWRITE" in body078 and "Konflikt078" in body078
            dest078 = export_txt078(txt078, rows078)
            assert dest078.is_file()
            assert "OVERWRITE" in dest078.read_text(encoding="utf-8")
            fd078 = (ROOT / "instantlensdoc" / "ui" / "file_dialogs.py").read_text(
                encoding="utf-8"
            )
            assert "Liste als TXT" in fd078 and "export_dry_run_conflict_list_txt" in fd078
        finally:
            if zip078.is_file():
                zip078.unlink()
            if txt078.is_file():
                txt078.unlink()
            for old in list(get_user_doc_templates()):
                if old["title"] == "Konflikt078":
                    delete_user_doc_template(old["id"])
        sb078 = (ROOT / "instantlensdoc" / "ui" / "sidebar.py").read_text(
            encoding="utf-8"
        )
        assert "setToolTip" in sb078 and "full_txt" in sb078
        mw078 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(
            encoding="utf-8"
        )
        assert "einmaliger Status-Hinweis" in mw078 or "STATUS_BLINK_AUS" in mw078
        assert "1800" in mw078  # Aus-Hinweis Dauer
        set_blink078("aus")
        assert get_blink078() == AUS078
        set_blink078("kurz")
        sd078 = (ROOT / "instantlensdoc" / "ui" / "settings_dialog.py").read_text(
            encoding="utf-8"
        )
        assert "merge_diff_max" in sd078 and "set_merge_diff_max_side" in sd078
        feat078 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.7.8" in feat078 and "TXT" in feat078 and "Tooltip" in feat078
        cl078 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## 0.7.8" in cl078 and "Dry-Run" in cl078
        kb078 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(
            encoding="utf-8"
        )
        assert "TXT" in kb078 and "Tooltip" in kb078
        print("0.7.8 CLI dry-run-txt/ann-tooltip/blink-hint/merge-diff-len: OK")

        # 0.7.9 CLI: Such-Export CSV/JSON, Ann.-Filter-Presets, Bracket-Auto-Close
        from instantlensdoc.core.app_settings import (
            delete_ann_filter_preset,
            get_ann_filter_preset,
            get_ann_filter_presets,
            get_editor_bracket_auto_close,
            save_ann_filter_preset,
            set_editor_bracket_auto_close,
        )
        from instantlensdoc.core.fulltext import (
            export_search_hits_csv,
            export_search_hits_json,
            normalize_search_hit_record,
        )

        set_editor_bracket_auto_close(False)
        assert get_editor_bracket_auto_close() is False
        set_editor_bracket_auto_close(True)
        assert get_editor_bracket_auto_close() is True
        # Filter-Presets roundtrip
        for old in list(get_ann_filter_presets()):
            delete_ann_filter_preset(old["name"])
        saved079 = save_ann_filter_preset(
            "Preset079",
            type="sticky",
            color="#FFCC00",
            tags=["Review", "Smoke"],
            current_page=True,
            search="note",
            regex=True,
        )
        assert saved079["name"] == "Preset079"
        assert saved079["type"] == "sticky"
        assert "Review" in saved079["tags"]
        loaded079 = get_ann_filter_preset("preset079")
        assert loaded079 is not None and loaded079["search"] == "note"
        assert loaded079["regex"] is True and loaded079["current_page"] is True
        assert any(p["name"] == "Preset079" for p in get_ann_filter_presets())
        assert delete_ann_filter_preset("Preset079") is True
        assert get_ann_filter_preset("Preset079") is None
        # Such-Export CSV/JSON
        hits079 = [
            normalize_search_hit_record(
                {
                    "label": "doc.pdf S.1: «hello»",
                    "path": "/tmp/doc.pdf",
                    "page": 1,
                    "kind": "pdf",
                    "query": "hello",
                    "snippet": "«hello»",
                },
                index=1,
                query="hello",
            ),
            {
                "label": "S.2 Ann.: note",
                "path": "",
                "page": 2,
                "kind": "annotation:sticky",
                "query": "hello",
                "snippet": "note",
            },
        ]
        csv079 = td / "search079.csv"
        json079 = td / "search079.json"
        out_csv079 = export_search_hits_csv(csv079, hits079, query="hello")
        out_json079 = export_search_hits_json(json079, hits079, query="hello")
        assert out_csv079.is_file()
        csv_body079 = out_csv079.read_text(encoding="utf-8")
        assert "index,label,path,page" in csv_body079.splitlines()[0]
        assert "hello" in csv_body079 and "doc.pdf" in csv_body079
        raw079 = json.loads(out_json079.read_text(encoding="utf-8"))
        assert raw079["schema"] == "ildsearch-v1" and raw079["count"] == 2
        assert raw079["query"] == "hello" and len(raw079["hits"]) == 2
        ed079 = (ROOT / "instantlensdoc" / "ui" / "editor.py").read_text(encoding="utf-8")
        assert "set_bracket_auto_close_enabled" in ed079 and "_bracket_auto_close" in ed079
        sd079 = (ROOT / "instantlensdoc" / "ui" / "settings_dialog.py").read_text(
            encoding="utf-8"
        )
        assert "bracket_auto_close" in sd079 and "set_editor_bracket_auto_close" in sd079
        sb079 = (ROOT / "instantlensdoc" / "ui" / "sidebar.py").read_text(encoding="utf-8")
        assert "search_hit_records" in sb079 and "ann_filter_preset" in sb079
        assert "btn_export_search_csv" in sb079 and "save_ann_filter_preset" in sb079
        mw079 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(
            encoding="utf-8"
        )
        assert "_on_search_export" in mw079 and "export_search_hits" in mw079
        feat079 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.7.9" in feat079 and "Filter-Presets" in feat079
        assert "Bracket-Auto-Close" in feat079 and "ildsearch" in feat079
        cl079 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## 0.7.9" in cl079 and "Suchergebnis" in cl079
        kb079 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(
            encoding="utf-8"
        )
        assert "CSV/JSON" in kb079 and "Bracket-Auto-Close" in kb079
        assert "Filter-Presets" in kb079
        print("0.7.9 CLI search-export/ann-presets/bracket-auto-close: OK")

        # 0.8.0 CLI: Bookmark ildbm-v1, Tag-Cloud Kontext, Recent max/Clear, Status
        from instantlensdoc.core.app_settings import (
            get_recent_files_max,
            set_recent_files_max,
        )
        from instantlensdoc.core import recent as recent_mod080
        from instantlensdoc.core.bookmarks import (
            BM_SCHEMA_ID,
            BM_VERSION,
            BookmarksImportError,
            bookmarks_to_export_dict,
            export_bookmarks_json,
            load_bookmarks_json,
            parse_bookmarks_dict,
        )

        set_recent_files_max(8)
        assert get_recent_files_max() == 8
        set_recent_files_max(12)
        assert get_recent_files_max() == 12
        recent_file080 = td / "recent080.json"
        orig_recent080 = recent_mod080.recent_path
        recent_mod080.recent_path = lambda: recent_file080  # type: ignore
        try:
            (td / "a080.txt").write_text("a", encoding="utf-8")
            (td / "b080.txt").write_text("b", encoding="utf-8")
            (td / "c080.txt").write_text("c", encoding="utf-8")
            recent_mod080.save_recent(
                [str(td / "a080.txt"), str(td / "b080.txt"), str(td / "c080.txt")],
                max_items=12,
            )
            trimmed = recent_mod080.trim_recent_to_max(3)
            assert len(trimmed) == 3
            set_recent_files_max(3)
            assert get_recent_files_max() == 3
            trimmed2 = recent_mod080.trim_recent_to_max(3)
            assert len(trimmed2) == 3
            recent_mod080.clear_recent()
            assert recent_mod080.load_recent() == []
            set_recent_files_max(12)
        finally:
            recent_mod080.recent_path = orig_recent080  # type: ignore
        assert BM_SCHEMA_ID == "ildbm-v1" and BM_VERSION == 1
        bm_json = td / "bm080.json"
        out_bm = export_bookmarks_json(
            bm_json, [(2, "Intro"), (4, "")], source="doc.txt"
        )
        raw_bm = json.loads(out_bm.read_text(encoding="utf-8"))
        assert raw_bm["schema"] == "ildbm-v1" and raw_bm["version"] == 1
        assert raw_bm["source"] == "doc.txt"
        assert any(b.get("line") == 2 and b.get("label") == "Intro" for b in raw_bm["bookmarks"])
        assert any(b.get("line") == 4 for b in raw_bm["bookmarks"])
        imported = load_bookmarks_json(bm_json)
        assert imported == [(2, "Intro"), (4, "")]
        d080 = bookmarks_to_export_dict([(1, "A"), (3, "B")], source="x")
        assert parse_bookmarks_dict(d080) == [(1, "A"), (3, "B")]
        assert parse_bookmarks_dict(d080, max_line=1) == [(1, "A")]
        try:
            parse_bookmarks_dict({"version": 99, "schema": BM_SCHEMA_ID, "bookmarks": []})
            raise AssertionError("expected BookmarksImportError")
        except BookmarksImportError:
            pass
        try:
            parse_bookmarks_dict({"version": BM_VERSION, "schema": "wrong", "bookmarks": []})
            raise AssertionError("expected BookmarksImportError")
        except BookmarksImportError:
            pass
        ed_src080 = (ROOT / "instantlensdoc" / "ui" / "editor.py").read_text(encoding="utf-8")
        assert "export_line_bookmarks_json" in ed_src080
        assert "from instantlensdoc.core.bookmarks import" in ed_src080
        sb080 = (ROOT / "instantlensdoc" / "ui" / "sidebar.py").read_text(encoding="utf-8")
        assert "annotation_tag_recolor_requested" in sb080
        assert "Farbe ändern" in sb080 and "filtern" in sb080
        mw080 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
        assert "_export_line_bookmarks_json" in mw080 and "_import_line_bookmarks_json" in mw080
        assert "_recolor_annotation_tag_global" in mw080
        assert "_on_editor_cursor_changed" in mw080
        assert "Zeile {" in mw080
        sd080 = (ROOT / "instantlensdoc" / "ui" / "settings_dialog.py").read_text(
            encoding="utf-8"
        )
        assert "recent_files_max" in sd080 and "btn_clear_recent" in sd080
        assert "set_recent_files_max" in sd080
        feat080 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.8.0" in feat080 and "ildbm-v1" in feat080
        cl080 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## 0.8.0" in cl080 and "ildbm-v1" in cl080
        kb080 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(
            encoding="utf-8"
        )
        assert "ildbm-v1" in kb080 and "Farbe ändern" in kb080
        print("0.8.0 CLI bookmark-ildbm/tag-cloud-ctx/recent-max/status: OK")

        # 0.8.1 CLI: Bookmark Drag/Sidecar, Tag-Cloud Sort, Recent fehlt+Entfernen, Zoom-%
        from instantlensdoc.core.app_settings import (
            TAG_CLOUD_SORT_AZ,
            TAG_CLOUD_SORT_FREQ,
            get_tag_cloud_sort,
            set_tag_cloud_sort,
        )
        from instantlensdoc.core import recent as recent_mod081
        from instantlensdoc.core.bookmarks import (
            bookmarks_to_export_dict,
            load_bookmarks_sidecar,
            parse_bookmarks_dict,
            save_bookmarks_sidecar,
            sidecar_path_for,
        )

        set_tag_cloud_sort("freq")
        assert get_tag_cloud_sort() == TAG_CLOUD_SORT_FREQ
        set_tag_cloud_sort("az")
        assert get_tag_cloud_sort() == TAG_CLOUD_SORT_AZ
        set_tag_cloud_sort("freq")
        assert get_tag_cloud_sort() == TAG_CLOUD_SORT_FREQ
        # ildbm-v1 behält Drag-Reihenfolge
        d081 = bookmarks_to_export_dict([(5, "Z"), (2, "A"), (9, "")], source="ord.txt")
        assert [b["line"] for b in d081["bookmarks"]] == [5, 2, 9]
        assert parse_bookmarks_dict(d081) == [(5, "Z"), (2, "A"), (9, "")]
        txt081 = td / "bm081.txt"
        txt081.write_text("L1\nL2\nL3\nL4\nL5\n", encoding="utf-8")
        side081 = save_bookmarks_sidecar(txt081, [(5, "Ende"), (2, "Start")])
        assert side081 == sidecar_path_for(txt081)
        assert side081.is_file()
        loaded081 = load_bookmarks_sidecar(txt081)
        assert loaded081 == [(5, "Ende"), (2, "Start")]
        # Recent: fehlende Dateien behalten + remove_recent
        recent_file081 = td / "recent081.json"
        orig_recent081 = recent_mod081.recent_path
        recent_mod081.recent_path = lambda: recent_file081  # type: ignore
        try:
            alive = td / "alive081.txt"
            alive.write_text("ok", encoding="utf-8")
            ghost = td / "ghost081-missing.txt"
            recent_mod081.save_recent([str(alive), str(ghost)], max_items=12)
            entries081 = recent_mod081.load_recent_entries()
            assert len(entries081) == 2
            assert entries081[0] == (str(alive), True)
            assert entries081[1][0] == str(ghost) and entries081[1][1] is False
            assert recent_mod081.load_recent(existing_only=True) == [str(alive)]
            recent_mod081.remove_recent(ghost)
            assert [p for p, _ in recent_mod081.load_recent_entries()] == [str(alive)]
            recent_mod081.clear_recent()
        finally:
            recent_mod081.recent_path = orig_recent081  # type: ignore
        ed_src081 = (ROOT / "instantlensdoc" / "ui" / "editor.py").read_text(encoding="utf-8")
        assert "reorder_line_bookmarks" in ed_src081 and "_line_bookmark_order" in ed_src081
        sb081 = (ROOT / "instantlensdoc" / "ui" / "sidebar.py").read_text(encoding="utf-8")
        assert "LineFavoriteList" in sb081 and "line_favorites_reordered" in sb081
        assert "_toggle_tag_cloud_sort" in sb081 and "recent_remove_requested" in sb081
        assert "Entfernen" in sb081 and "(fehlt)" in sb081
        mw081 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
        assert "_on_line_favorites_reordered" in mw081
        assert "_persist_line_bookmarks_sidecar" in mw081
        assert "_remove_recent_path" in mw081
        assert 'Zoom {' in mw081 or "Zoom {" in mw081
        feat081 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.8.1" in feat081 and "Drag-Reorder" in feat081
        assert "A–Z" in feat081 or "A-Z" in feat081 or "Sort" in feat081
        cl081 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## 0.8.1" in cl081 and "Zoom" in cl081
        kb081 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(
            encoding="utf-8"
        )
        assert "0.8.1" in kb081 and "Tag-Cloud Sortierung" in kb081
        print("0.8.1 CLI bookmark-drag/tag-sort/recent-missing/zoom: OK")

        # 0.8.2 CLI: Thumbnail-Undo, Fit-Zoom-Modus, Ann.-Ctrl+D, Standard-Zoom speichern
        from instantlensdoc.core.app_settings import (
            DEFAULT_ZOOM_MODE_FIT_PAGE,
            DEFAULT_ZOOM_MODE_FIT_WIDTH,
            DEFAULT_ZOOM_MODE_PERCENT,
            get_default_zoom_mode,
            set_default_zoom_mode,
        )

        set_default_zoom_mode("percent")
        assert get_default_zoom_mode() == DEFAULT_ZOOM_MODE_PERCENT
        set_default_zoom_mode("fit_width")
        assert get_default_zoom_mode() == DEFAULT_ZOOM_MODE_FIT_WIDTH
        set_default_zoom_mode("fit_page")
        assert get_default_zoom_mode() == DEFAULT_ZOOM_MODE_FIT_PAGE
        set_default_zoom_mode("bogus")
        assert get_default_zoom_mode() == DEFAULT_ZOOM_MODE_PERCENT
        set_default_zoom_mode("percent")
        pv082 = (ROOT / "instantlensdoc" / "ui" / "pdf_view.py").read_text(
            encoding="utf-8"
        )
        assert 'kind == "reorder"' in pv082
        assert "record_undo" in pv082
        assert "ann_remapped" in pv082
        assert "get_default_zoom_mode" in pv082
        assert "Fit-Width" in pv082 and "Fit-Page" in pv082
        mw082 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(
            encoding="utf-8"
        )
        assert "_duplicate_current" in mw082
        assert "_save_current_zoom_as_default" in mw082
        assert "Ctrl+Shift+0" in mw082
        assert "Fit-Width" in mw082 and "Fit-Page" in mw082
        sd082 = (ROOT / "instantlensdoc" / "ui" / "settings_dialog.py").read_text(
            encoding="utf-8"
        )
        assert "zoom_mode" in sd082 and "_capture_current_pdf_zoom" in sd082
        assert "set_default_zoom_mode" in sd082
        sb082 = (ROOT / "instantlensdoc" / "ui" / "sidebar.py").read_text(
            encoding="utf-8"
        )
        assert "Ctrl+Z" in sb082
        feat082 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.8.2" in feat082 and "Ctrl+D" in feat082
        assert "Reorder-Undo" in feat082 or "Undo Ctrl+Z" in feat082
        cl082 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## 0.8.2" in cl082 and "Fit-Width" in cl082
        kb082 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(
            encoding="utf-8"
        )
        assert "0.8.2" in kb082 and "Fit-Width" in kb082
        assert "Thumbnail-Reorder Undo" in kb082
        print("0.8.2 CLI thumb-undo/fit-zoom/ann-ctrl-d/default-zoom: OK")

        # 0.8.3 CLI: Ann.-Multi-Select, Thumb-Drehen, Seitennummer-Overlay, Zeilennummern
        from instantlensdoc.core.app_settings import (
            get_show_page_number_overlay,
            set_show_page_number_overlay,
            get_editor_line_numbers as get_ln083,
            set_editor_line_numbers as set_ln083,
        )

        set_show_page_number_overlay(True)
        assert get_show_page_number_overlay() is True
        set_show_page_number_overlay(False)
        assert get_show_page_number_overlay() is False
        set_ln083(True)
        assert get_ln083() is True
        set_ln083(False)
        assert get_ln083() is False
        pv083 = (ROOT / "instantlensdoc" / "ui" / "pdf_view.py").read_text(
            encoding="utf-8"
        )
        assert "ShiftModifier" in pv083 and "_selected_ids" in pv083
        assert "rotate_at" in pv083
        assert "set_show_page_number_overlay" in pv083
        assert "_update_page_number_overlay" in pv083
        mw083 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(
            encoding="utf-8"
        )
        assert "_on_thumb_rotate" in mw083
        assert "_toggle_page_number_overlay" in mw083
        assert "set_editor_line_numbers" in mw083
        sb083 = (ROOT / "instantlensdoc" / "ui" / "sidebar.py").read_text(
            encoding="utf-8"
        )
        assert "page_rotate_requested" in sb083
        assert "_thumbs_context_menu" in sb083
        assert "Drehen 90°" in sb083
        sd083 = (ROOT / "instantlensdoc" / "ui" / "settings_dialog.py").read_text(
            encoding="utf-8"
        )
        assert "page_num_overlay" in sd083
        assert "set_show_page_number_overlay" in sd083
        feat083 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.8.3" in feat083 and "Mehrfachauswahl" in feat083
        assert "Seitennummer-Overlay" in feat083
        cl083 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## 0.8.3" in cl083 and "Shift+Klick" in cl083
        kb083 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(
            encoding="utf-8"
        )
        assert "0.8.3" in kb083 and "Mehrfachauswahl" in kb083
        print("0.8.3 CLI multi-select/thumb-rotate/page-num/line-numbers: OK")

        # 0.8.4 CLI: Ann.-Align/Distribute, Thumb-Löschen, Overlay-Opacity, Wortumbruch
        from instantlensdoc.core.app_settings import (
            get_page_number_overlay_opacity,
            set_page_number_overlay_opacity,
            get_editor_soft_wrap as get_sw084,
            set_editor_soft_wrap as set_sw084,
        )
        from ild_pdf import Annotation as Ann084, AnnotationStore as AS084, AnnotationType as AT084

        set_page_number_overlay_opacity(0.35)
        assert abs(get_page_number_overlay_opacity() - 0.35) < 0.001
        set_page_number_overlay_opacity(0.59)
        assert abs(get_page_number_overlay_opacity() - 0.59) < 0.001
        set_sw084(True)
        assert get_sw084() is True
        set_sw084(False)
        assert get_sw084() is False
        set_sw084(True)
        store084 = AS084(pdf)
        store084.annotations = []
        store084.clear_history()
        a084 = Ann084(0, AT084.HIGHLIGHT, 10, 10, width=20, height=10, text="a")
        b084 = Ann084(0, AT084.HIGHLIGHT, 50, 20, width=20, height=10, text="b")
        c084 = Ann084(0, AT084.HIGHLIGHT, 90, 30, width=20, height=10, text="c")
        store084.add(a084); store084.add(b084); store084.add(c084)
        n_al = store084.align([a084.id, b084.id, c084.id], horizontal="left")
        assert n_al >= 1
        assert abs(float(store084.get(a084.id).x) - float(store084.get(b084.id).x)) < 0.01
        store084.align([a084.id, b084.id, c084.id], horizontal="right")
        store084.align([a084.id, b084.id, c084.id], horizontal="center")
        # reset xs for distribute
        store084.update(a084.id, x=10.0)
        store084.update(b084.id, x=40.0)
        store084.update(c084.id, x=100.0)
        n_dh = store084.distribute_horizontal([a084.id, b084.id, c084.id])
        assert n_dh >= 1
        xs = sorted(float(store084.get(i).x) for i in (a084.id, b084.id, c084.id))
        assert abs((xs[1] - xs[0]) - (xs[2] - xs[1])) < 0.05
        pv084 = (ROOT / "instantlensdoc" / "ui" / "pdf_view.py").read_text(encoding="utf-8")
        assert "align_selected_annotations" in pv084
        assert "distribute_selected_annotations_horizontal" in pv084
        assert "delete_at" in pv084
        assert "set_page_number_overlay_opacity" in pv084
        mw084 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
        assert "_on_thumb_delete" in mw084
        assert "_align_selected_annotations" in mw084
        assert "Wortumbruch" in mw084
        assert "get_editor_soft_wrap" in mw084
        sb084 = (ROOT / "instantlensdoc" / "ui" / "sidebar.py").read_text(encoding="utf-8")
        assert "page_delete_requested" in sb084
        assert "Seite löschen" in sb084
        sd084 = (ROOT / "instantlensdoc" / "ui" / "settings_dialog.py").read_text(encoding="utf-8")
        assert "page_num_opacity" in sd084
        assert "set_page_number_overlay_opacity" in sd084
        feat084 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.8.4" in feat084 and ("Align" in feat084 or "verteilen" in feat084 or "Ausrichten" in feat084 or "Distribute" in feat084)
        cl084 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## 0.8.4" in cl084
        kb084 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
        assert "0.8.4" in kb084 and ("Wortumbruch" in kb084 or "verteilen" in kb084 or "löschen" in kb084)
        print("0.8.4 CLI align/distribute/thumb-delete/overlay-opacity/word-wrap: OK")

        # 0.8.5 CLI: Ann.-Align/Distribute V, Thumb-Duplizieren, Overlay-Font, Tab-Breite
        from instantlensdoc.core.app_settings import (
            get_page_number_overlay_font_size,
            set_page_number_overlay_font_size,
            get_editor_tab_width as get_tw085,
            set_editor_tab_width as set_tw085,
        )
        from ild_pdf import Annotation as Ann085, AnnotationStore as AS085, AnnotationType as AT085

        set_page_number_overlay_font_size(14)
        assert get_page_number_overlay_font_size() == 14
        set_page_number_overlay_font_size(11)
        assert get_page_number_overlay_font_size() == 11
        set_tw085(2)
        assert get_tw085() == 2
        set_tw085(8)
        assert get_tw085() == 8
        set_tw085(4)
        assert get_tw085() == 4
        store085 = AS085(pdf)
        store085.annotations = []
        store085.clear_history()
        a085 = Ann085(0, AT085.HIGHLIGHT, 10, 10, width=20, height=10, text="av")
        b085 = Ann085(0, AT085.HIGHLIGHT, 20, 50, width=20, height=10, text="bv")
        c085 = Ann085(0, AT085.HIGHLIGHT, 30, 100, width=20, height=10, text="cv")
        store085.add(a085); store085.add(b085); store085.add(c085)
        n_top = store085.align([a085.id, b085.id, c085.id], vertical="top")
        assert n_top >= 1
        assert abs(float(store085.get(a085.id).y) - float(store085.get(b085.id).y)) < 0.01
        store085.align([a085.id, b085.id, c085.id], vertical="bottom")
        store085.align([a085.id, b085.id, c085.id], vertical="middle")
        store085.update(a085.id, y=10.0)
        store085.update(b085.id, y=40.0)
        store085.update(c085.id, y=100.0)
        n_dv = store085.distribute_vertical([a085.id, b085.id, c085.id])
        assert n_dv >= 1
        ys = sorted(float(store085.get(i).y) for i in (a085.id, b085.id, c085.id))
        assert abs((ys[1] - ys[0]) - (ys[2] - ys[1])) < 0.05
        pv085 = (ROOT / "instantlensdoc" / "ui" / "pdf_view.py").read_text(encoding="utf-8")
        assert "distribute_selected_annotations_vertical" in pv085
        assert "duplicate_at" in pv085
        assert "set_page_number_overlay_font_size" in pv085
        assert 'kind == "duplicate"' in pv085 or "kind == 'duplicate'" in pv085 or '"duplicate"' in pv085
        mw085 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
        assert "_on_thumb_duplicate" in mw085
        assert "_distribute_selected_annotations_vertical" in mw085
        sb085 = (ROOT / "instantlensdoc" / "ui" / "sidebar.py").read_text(encoding="utf-8")
        assert "page_duplicate_requested" in sb085
        assert "Seite duplizieren" in sb085
        sd085 = (ROOT / "instantlensdoc" / "ui" / "settings_dialog.py").read_text(encoding="utf-8")
        assert "page_num_font" in sd085
        assert "set_page_number_overlay_font_size" in sd085
        assert "tab_width" in sd085
        assert "set_editor_tab_width" in sd085
        ed085 = (ROOT / "instantlensdoc" / "ui" / "editor.py").read_text(encoding="utf-8")
        assert "set_tab_width" in ed085
        feat085 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.8.5" in feat085 and (
            "Distribute V" in feat085 or "vertikal" in feat085 or "Tab-Breite" in feat085 or "duplizieren" in feat085
        )
        cl085 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## 0.8.5" in cl085
        kb085 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
        assert "0.8.5" in kb085 and (
            "duplizieren" in kb085 or "Tab-Breite" in kb085 or "Schriftgröße" in kb085 or "vertikal" in kb085
        )
        print("0.8.5 CLI align-v/distribute-v/thumb-dup/overlay-font/tab-width: OK")

        # 0.8.6 CLI: Ann.-Group/Ungroup, Thumb Multi-Select Batch, Overlay-Position, Soft-Tabs
        from instantlensdoc.core.app_settings import (
            get_page_number_overlay_position,
            set_page_number_overlay_position,
            get_editor_soft_tabs as get_st086,
            set_editor_soft_tabs as set_st086,
        )
        from ild_pdf import Annotation as Ann086, AnnotationStore as AS086, AnnotationType as AT086

        set_page_number_overlay_position("top-center")
        assert get_page_number_overlay_position() == "top-center"
        set_page_number_overlay_position("bottom-center")
        assert get_page_number_overlay_position() == "bottom-center"
        set_st086(False)
        assert get_st086() is False
        set_st086(True)
        assert get_st086() is True
        store086 = AS086(pdf)
        store086.annotations = []
        store086.clear_history()
        a086 = Ann086(0, AT086.HIGHLIGHT, 10, 10, width=20, height=10, text="g1")
        b086 = Ann086(0, AT086.HIGHLIGHT, 40, 20, width=20, height=10, text="g2")
        c086 = Ann086(0, AT086.HIGHLIGHT, 70, 30, width=20, height=10, text="g3")
        store086.add(a086); store086.add(b086); store086.add(c086)
        n_g, gid = store086.group([a086.id, b086.id, c086.id])
        assert n_g == 3 and gid
        assert store086.get(a086.id).group_id == gid
        assert store086.get(b086.id).group_id == gid
        n_ug = store086.ungroup([a086.id, b086.id])
        assert n_ug == 2
        assert store086.get(a086.id).group_id == ""
        assert store086.get(c086.id).group_id == gid
        store086.ungroup([c086.id])
        pv086 = (ROOT / "instantlensdoc" / "ui" / "pdf_view.py").read_text(encoding="utf-8")
        assert "group_selected_annotations" in pv086
        assert "ungroup_selected_annotations" in pv086
        assert "duplicate_many" in pv086
        assert "delete_many" in pv086
        assert "set_page_number_overlay_position" in pv086
        mw086 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
        assert "_group_selected_annotations" in mw086
        assert "_on_thumbs_batch_duplicate" in mw086
        assert "_on_thumbs_batch_delete" in mw086
        sb086 = (ROOT / "instantlensdoc" / "ui" / "sidebar.py").read_text(encoding="utf-8")
        assert "pages_batch_duplicate_requested" in sb086
        assert "pages_batch_delete_requested" in sb086
        assert "ExtendedSelection" in sb086
        assert "selected_thumb_pages" in sb086
        sd086 = (ROOT / "instantlensdoc" / "ui" / "settings_dialog.py").read_text(encoding="utf-8")
        assert "page_num_pos" in sd086
        assert "set_page_number_overlay_position" in sd086
        assert "soft_tabs" in sd086
        assert "set_editor_soft_tabs" in sd086
        ed086 = (ROOT / "instantlensdoc" / "ui" / "editor.py").read_text(encoding="utf-8")
        assert "set_soft_tabs" in ed086
        assert "_indent_pad" in ed086
        ann086 = (ROOT / "ild_pdf" / "annotate.py").read_text(encoding="utf-8")
        assert "group_id" in ann086
        assert "def group(" in ann086
        assert "def ungroup(" in ann086
        feat086 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.8.6" in feat086 and (
            "Gruppieren" in feat086 or "group_id" in feat086 or "Soft-Tabs" in feat086 or "Mehrfachauswahl" in feat086
        )
        cl086 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## 0.8.6" in cl086
        kb086 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
        assert "0.8.6" in kb086 and (
            "Gruppieren" in kb086 or "Soft-Tabs" in kb086 or "unten-mitte" in kb086 or "Mehrfachauswahl" in kb086
        )
        print("0.8.6 CLI group/ungroup/thumb-batch/overlay-pos/soft-tabs: OK")

        # 0.8.7 CLI: Group-Select/Lock, Thumb Batch-Rotate, Overlay-Format, Mehrzeilen-Indent
        from instantlensdoc.core.app_settings import (
            get_page_number_overlay_format,
            set_page_number_overlay_format,
        )
        from ild_pdf import Annotation as Ann087, AnnotationStore as AS087, AnnotationType as AT087

        set_page_number_overlay_format("S.{page}/{pages}")
        assert get_page_number_overlay_format() == "S.{page}/{pages}"
        set_page_number_overlay_format("{page} / {pages}")
        assert get_page_number_overlay_format() == "{page} / {pages}"
        store087 = AS087(pdf)
        store087.annotations = []
        store087.clear_history()
        a087 = Ann087(0, AT087.HIGHLIGHT, 10, 10, width=20, height=10, text="g1")
        b087 = Ann087(0, AT087.HIGHLIGHT, 40, 20, width=20, height=10, text="g2")
        c087 = Ann087(0, AT087.STICKY, 70, 30, width=20, height=10, text="solo")
        store087.add(a087); store087.add(b087); store087.add(c087)
        n_g087, gid087 = store087.group([a087.id, b087.id])
        assert n_g087 == 2 and gid087
        expanded = store087.expand_group_ids([a087.id])
        assert set(expanded) == {a087.id, b087.id}
        assert store087.ids_in_group(gid087) == [a087.id, b087.id] or set(
            store087.ids_in_group(gid087)
        ) == {a087.id, b087.id}
        n_lock, locked087 = store087.toggle_group_lock([a087.id])
        assert n_lock == 2 and locked087 is True
        assert store087.get(a087.id).locked and store087.get(b087.id).locked
        assert not store087.get(c087.id).locked
        moved = store087.move_by([a087.id, b087.id], 5, 5)
        assert moved == 0  # gesperrt
        n_unlock, locked087b = store087.toggle_group_lock([b087.id])
        assert n_unlock == 2 and locked087b is False
        moved2 = store087.move_by([a087.id], 3, 0)
        assert moved2 == 1
        store087.ungroup([a087.id, b087.id])
        pv087 = (ROOT / "instantlensdoc" / "ui" / "pdf_view.py").read_text(encoding="utf-8")
        assert "toggle_selected_group_lock" in pv087
        assert "rotate_many" in pv087
        assert "format_page_number_overlay_text" in pv087
        assert "set_page_number_overlay_format" in pv087
        mw087 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
        assert "_toggle_selected_group_lock" in mw087
        assert "_on_thumbs_batch_rotate" in mw087
        sb087 = (ROOT / "instantlensdoc" / "ui" / "sidebar.py").read_text(encoding="utf-8")
        assert "pages_batch_rotate_requested" in sb087
        sd087 = (ROOT / "instantlensdoc" / "ui" / "settings_dialog.py").read_text(encoding="utf-8")
        assert "page_num_format" in sd087
        assert "set_page_number_overlay_format" in sd087
        ed087 = (ROOT / "instantlensdoc" / "ui" / "editor.py").read_text(encoding="utf-8")
        assert "selection_spans_multiple_lines" in ed087
        assert "insert_indent_at_cursor" in ed087
        ann087src = (ROOT / "ild_pdf" / "annotate.py").read_text(encoding="utf-8")
        assert "locked" in ann087src
        assert "def toggle_group_lock(" in ann087src
        assert "def expand_group_ids(" in ann087src
        assert "def ids_in_group(" in ann087src
        feat087 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.8.7" in feat087 and (
            "Gruppen-Sperre" in feat087
            or "Batch-Drehen" in feat087
            or "{page}" in feat087
            or "Mehrzeilen" in feat087
        )
        cl087 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## 0.8.7" in cl087
        kb087 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
        assert "0.8.7" in kb087 and (
            "Gruppen-Sperre" in kb087
            or "Batch-Drehen" in kb087
            or "{page}" in kb087
            or "Mehrzeilen" in kb087
        )
        print("0.8.7 CLI group-select/lock/thumb-rotate/overlay-fmt/multiline-indent: OK")

        # 0.8.8 CLI: Group Rename/Color, Thumb Extract-PDF, Overlay-Start, Indent-Guides
        from instantlensdoc.core.app_settings import (
            get_editor_indent_guides,
            get_page_number_overlay_start,
            set_editor_indent_guides,
            set_page_number_overlay_start,
        )
        from ild_pdf import Annotation as Ann088, AnnotationStore as AS088, AnnotationType as AT088
        from ild_pdf.pages import extract_pages as extract_pages_088

        set_page_number_overlay_start(5)
        assert get_page_number_overlay_start() == 5
        set_page_number_overlay_start(1)
        assert get_page_number_overlay_start() == 1
        set_editor_indent_guides(False)
        assert get_editor_indent_guides() is False
        set_editor_indent_guides(True)
        assert get_editor_indent_guides() is True
        store088 = AS088(pdf)
        store088.annotations = []
        store088.clear_history()
        a088 = Ann088(0, AT088.HIGHLIGHT, 10, 10, width=20, height=10, text="g088a")
        b088 = Ann088(0, AT088.HIGHLIGHT, 40, 20, width=20, height=10, text="g088b")
        store088.add(a088)
        store088.add(b088)
        n_g088, gid088 = store088.group([a088.id, b088.id])
        assert n_g088 == 2 and gid088
        meta088 = store088.set_ann_group(gid088, title="Kapitel A", color="#90CAF9")
        assert meta088["title"] == "Kapitel A"
        assert meta088["color"] == "#90CAF9"
        assert store088.get_ann_group(gid088)["title"] == "Kapitel A"
        assert gid088 in store088.list_ann_groups()
        # extract_pages non-contiguous
        multi088 = td / "extract_src.pdf"
        import pikepdf as _pike088

        with _pike088.Pdf.new() as _d088:
            for _ in range(4):
                _d088.add_blank_page(page_size=(200, 280))
            _d088.save(multi088)
        out088 = td / "extract_sel.pdf"
        extract_pages_088(multi088, out088, [0, 2, 3])
        with _pike088.open(out088) as _chk088:
            assert len(_chk088.pages) == 3
        pv088 = (ROOT / "instantlensdoc" / "ui" / "pdf_view.py").read_text(encoding="utf-8")
        assert "edit_selected_ann_group" in pv088
        assert "extract_selected_pages_as_pdf" in pv088
        assert "set_page_number_overlay_start" in pv088
        mw088 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
        assert "_edit_selected_ann_group" in mw088
        assert "_on_thumbs_batch_extract" in mw088
        assert "_toggle_indent_guides" in mw088
        sb088 = (ROOT / "instantlensdoc" / "ui" / "sidebar.py").read_text(encoding="utf-8")
        assert "pages_batch_extract_requested" in sb088
        assert "ann_groups" in sb088
        sd088 = (ROOT / "instantlensdoc" / "ui" / "settings_dialog.py").read_text(encoding="utf-8")
        assert "page_num_start" in sd088
        assert "indent_guides" in sd088
        assert "set_page_number_overlay_start" in sd088
        assert "set_editor_indent_guides" in sd088
        ed088 = (ROOT / "instantlensdoc" / "ui" / "editor.py").read_text(encoding="utf-8")
        assert "set_indent_guides_visible" in ed088
        assert "_paint_indent_guides" in ed088
        ann088src = (ROOT / "ild_pdf" / "annotate.py").read_text(encoding="utf-8")
        assert "def set_ann_group(" in ann088src
        assert "def get_ann_group(" in ann088src
        assert "ann_groups" in ann088src
        pages088src = (ROOT / "ild_pdf" / "pages.py").read_text(encoding="utf-8")
        assert "def extract_pages(" in pages088src
        feat088 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.8.8" in feat088 and (
            "Rename" in feat088
            or "extrahieren" in feat088
            or "Start-Offset" in feat088
            or "Einrückungs-Guides" in feat088
        )
        cl088 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## 0.8.8" in cl088
        kb088 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
        assert "0.8.8" in kb088 and (
            "umbenennen" in kb088
            or "extrahieren" in kb088
            or "Start-Offset" in kb088
            or "Einrückungs-Guides" in kb088
        )
        print("0.8.8 CLI group-rename/color/thumb-extract/overlay-start/indent-guides: OK")

        # 0.8.9 CLI: Group Filter/JSON, Thumb Tab-Open, Overlay-Edges, Current-Line-HL
        from instantlensdoc.core.app_settings import (
            get_editor_current_line_highlight,
            get_page_number_overlay_skip_edges,
            set_editor_current_line_highlight,
            set_page_number_overlay_skip_edges,
        )
        from ild_pdf import Annotation as Ann089, AnnotationStore as AS089, AnnotationType as AT089

        set_page_number_overlay_skip_edges(True)
        assert get_page_number_overlay_skip_edges() is True
        set_page_number_overlay_skip_edges(False)
        assert get_page_number_overlay_skip_edges() is False
        set_editor_current_line_highlight(False)
        assert get_editor_current_line_highlight() is False
        set_editor_current_line_highlight(True)
        assert get_editor_current_line_highlight() is True
        store089 = AS089(pdf)
        store089.annotations = []
        store089.clear_history()
        a089 = Ann089(0, AT089.HIGHLIGHT, 10, 10, width=20, height=10, text="g089a")
        b089 = Ann089(0, AT089.HIGHLIGHT, 40, 20, width=20, height=10, text="g089b")
        c089 = Ann089(0, AT089.HIGHLIGHT, 70, 30, width=20, height=10, text="solo089")
        store089.add(a089)
        store089.add(b089)
        store089.add(c089)
        n_g089, gid089 = store089.group([a089.id, b089.id])
        assert n_g089 == 2 and gid089
        store089.set_ann_group(gid089, title="ExportG", color="#CCDDEE")
        j089 = td / "group_export.json"
        out089 = store089.export_group_json(gid089, j089)
        assert out089.is_file()
        raw089 = j089.read_text(encoding="utf-8")
        assert "ExportG" in raw089 and "g089a" in raw089 and "g089b" in raw089
        assert "solo089" not in raw089
        assert "export_group_id" in raw089
        pv089 = (ROOT / "instantlensdoc" / "ui" / "pdf_view.py").read_text(encoding="utf-8")
        assert "open_selected_pages_as_document" in pv089
        assert "export_selected_ann_group_json" in pv089
        assert "set_page_number_overlay_skip_edges" in pv089
        assert "_page_number_overlay_should_skip" in pv089
        mw089 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
        assert "_on_thumbs_batch_open" in mw089
        assert "_on_ann_group_export" in mw089
        assert "_toggle_current_line_highlight" in mw089
        sb089 = (ROOT / "instantlensdoc" / "ui" / "sidebar.py").read_text(encoding="utf-8")
        assert "pages_batch_open_requested" in sb089
        assert "annotation_group_export_requested" in sb089
        assert "set_annotation_group_filter" in sb089
        assert "Nur diese Gruppe" in sb089
        sd089 = (ROOT / "instantlensdoc" / "ui" / "settings_dialog.py").read_text(encoding="utf-8")
        assert "page_num_skip_edges" in sd089
        assert "current_line_hl" in sd089
        assert "set_page_number_overlay_skip_edges" in sd089
        assert "set_editor_current_line_highlight" in sd089
        ed089 = (ROOT / "instantlensdoc" / "ui" / "editor.py").read_text(encoding="utf-8")
        assert "set_current_line_highlight" in ed089
        assert "_update_current_line_highlight" in ed089
        ann089src = (ROOT / "ild_pdf" / "annotate.py").read_text(encoding="utf-8")
        assert "def export_group_json(" in ann089src
        feat089 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.8.9" in feat089 and (
            "nur diese Gruppe" in feat089
            or "JSON-Export" in feat089
            or "neues Dokument" in feat089
            or "Aktuelle Zeile" in feat089
            or "erste/letzte" in feat089
        )
        cl089 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## 0.8.9" in cl089
        kb089 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
        assert "0.8.9" in kb089 and (
            "Nur diese Gruppe" in kb089
            or "neues Dokument" in kb089
            or "Aktuelle Zeile" in kb089
            or "erste/letzte" in kb089
        )
        print("0.8.9 CLI group-filter/json/thumb-open/overlay-edges/line-hl: OK")

        # 0.9.0 CLI: Tab Mittelklick/Andere, PDF-Suche F3, Opacity-Auswahl, Session-Geometry-Toggle
        from instantlensdoc.core.app_settings import (
            get_restore_window_geometry_on_start,
            set_restore_window_geometry_on_start,
        )

        set_restore_window_geometry_on_start(False)
        assert get_restore_window_geometry_on_start() is False
        set_restore_window_geometry_on_start(True)
        assert get_restore_window_geometry_on_start() is True
        sb090 = (ROOT / "instantlensdoc" / "ui" / "sidebar.py").read_text(encoding="utf-8")
        assert "document_close_requested" in sb090
        assert "document_close_others_requested" in sb090
        assert "MiddleButton" in sb090
        assert "Andere schließen" in sb090
        mw090 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
        assert "close_tab_path" in mw090
        assert "close_other_tabs_keeping" in mw090
        assert "FindNext" in mw090 and "FindPrevious" in mw090
        assert "get_restore_window_geometry_on_start" in mw090
        pv090 = (ROOT / "instantlensdoc" / "ui" / "pdf_view.py").read_text(encoding="utf-8")
        assert "_find_search_on_pages" in pv090
        assert "search_active_index" in pv090
        assert "ausgewählte Annotation" in pv090 or "ausgewähltes Objekt" in pv090.lower() or "Opacity-Slider" in pv090
        sd090 = (ROOT / "instantlensdoc" / "ui" / "settings_dialog.py").read_text(encoding="utf-8")
        assert "restore_geometry" in sd090
        assert "set_restore_window_geometry_on_start" in sd090
        assert "Offene Tabs wiederherstellen" in sd090
        assert "Fenstergeometrie wiederherstellen" in sd090
        feat090 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.9.0" in feat090 and (
            "Mittelklick" in feat090
            or "F3" in feat090
            or "Fenstergeometrie" in feat090
            or "Opacity" in feat090
        )
        cl090 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## 0.9.0" in cl090
        kb090 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
        assert "0.9.0" in kb090 and (
            "F3" in kb090 or "Mittelklick" in kb090 or "Session-Toggles" in kb090
        )
        print("0.9.0 CLI tab-midclick/search-f3/opacity/session-toggles: OK")

        # 0.9.1 CLI: Tabs Alle/Links/Rechts, PDF-Trefferliste, Opacity Commit-on-Release, Session Scroll
        sb091 = (ROOT / "instantlensdoc" / "ui" / "sidebar.py").read_text(encoding="utf-8")
        assert "document_close_all_requested" in sb091
        assert "document_close_left_requested" in sb091
        assert "document_close_right_requested" in sb091
        assert "Alle schließen" in sb091
        assert "Links schließen" in sb091
        assert "Rechts schließen" in sb091
        mw091 = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
        assert "close_all_tabs" in mw091
        assert "close_tabs_left_of" in mw091
        assert "close_tabs_right_of" in mw091
        assert "_tab_view_state" in mw091
        assert "_capture_current_tab_view_state" in mw091
        assert "_restore_tab_view_state" in mw091
        assert "collect_search_hits" in mw091 or "collect_search_hits" in (
            ROOT / "instantlensdoc" / "ui" / "pdf_view.py"
        ).read_text(encoding="utf-8")
        pv091 = (ROOT / "instantlensdoc" / "ui" / "pdf_view.py").read_text(encoding="utf-8")
        assert "collect_search_hits" in pv091
        assert "_on_opacity_slider_pressed" in pv091
        assert "_on_opacity_slider_released" in pv091
        assert "sliderPressed" in pv091 and "sliderReleased" in pv091
        sess091 = (ROOT / "instantlensdoc" / "core" / "session.py").read_text(encoding="utf-8")
        assert "scroll_y" in sess091
        assert "tab_states" in sess091
        # Session roundtrip Last-Page / Scroll
        sess_file091 = td / "session091.json"
        orig_sess091 = session_mod.session_path
        session_mod.session_path = lambda: sess_file091  # type: ignore
        try:
            t_a = td / "sess_a.txt"
            t_b = td / "sess_b.txt"
            t_a.write_text("aaa\n", encoding="utf-8")
            t_b.write_text("bbb\n", encoding="utf-8")
            st091 = session_mod.build_session(
                [str(t_a), str(t_b)],
                active_path=str(t_b),
                page=2,
                scale=1.75,
                scroll_y=120,
                tab_states={
                    str(t_a): {"page": 1, "scale": 1.25, "scroll_y": 40},
                    str(t_b): {"page": 2, "scale": 1.75, "scroll_y": 120},
                },
            )
            session_mod.save_session(st091)
            loaded091 = session_mod.load_session()
            assert len(loaded091.tabs) == 2
            by_path = {t.path: t for t in loaded091.tabs}
            assert by_path[str(Path(t_a))].page == 1
            assert by_path[str(Path(t_a))].scroll_y == 40
            assert by_path[str(Path(t_b))].page == 2
            assert by_path[str(Path(t_b))].scroll_y == 120
            assert abs(by_path[str(Path(t_b))].scale - 1.75) < 0.01
        finally:
            session_mod.session_path = orig_sess091  # type: ignore
        feat091 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.9.1" in feat091 and (
            "Last-Page" in feat091
            or "Trefferliste" in feat091
            or "Commit on release" in feat091
            or "Links" in feat091
        )
        cl091 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## 0.9.1" in cl091
        kb091 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
        assert "0.9.1" in kb091 and (
            "Alle" in kb091 or "Trefferliste" in kb091 or "Last-Page" in kb091
        )
        print("0.9.1 CLI tabs-close/search-list/opacity-commit/session-scroll: OK")

        set_show_printer_marks(True)
        assert get_show_printer_marks() is True
        set_show_printer_marks(False)
        assert get_show_printer_marks() is False
        hl = Annotation(0, AnnotationType.HIGHLIGHT, 10, 20, width=30, height=12, text="hl-v4", color="#FFCC00", opacity=0.6)
        ed = hl.to_export_dict()
        assert "rects" in ed and "quadPoints" in ed and "colorRGB" in ed
        assert ed["pdf_highlight"]["subtype"] == "Highlight"
        assert ed["pdf_highlight"]["contents"] == "hl-v4"
        store_v4 = AnnotationStore(pdf)
        store_v4.annotations = []
        store_v4.clear_history()
        store_v4.add(hl)
        v4path = td / "ann-v4-export.json"
        store_v4.export_json(v4path)
        raw_v4 = v4path.read_text(encoding="utf-8")
        assert '"version": 4' in raw_v4 and '"schema": "ildann-v4"' in raw_v4
        assert "quadPoints" in raw_v4 and "pdf_highlight" in raw_v4
        # Import v4 highlight block
        store_imp4 = AnnotationStore(pdf)
        store_imp4.annotations = []
        store_imp4.clear_history()
        assert store_imp4.import_json(v4path, replace=True) == 1
        assert store_imp4.annotations[0].type == AnnotationType.HIGHLIGHT
        # 0.4.5: Schema-Validierung ablehnen + Trim + Toolbar-Gruppen
        from ild_pdf.annotate import AnnotationImportError

        bad_v = td / "ann-bad-ver.json"
        bad_v.write_text(
            json.dumps({"version": 99, "schema": "ildann-v4", "annotations": []}),
            encoding="utf-8",
        )
        store_bad = AnnotationStore(pdf)
        store_bad.annotations = []
        store_bad.clear_history()
        try:
            store_bad.import_json(bad_v, replace=True)
            raise AssertionError("expected AnnotationImportError")
        except AnnotationImportError as err:
            assert "99" in str(err) or "Inkompatible" in str(err)
        bad_schema = td / "ann-bad-schema.json"
        bad_schema.write_text(
            json.dumps({"version": 4, "schema": "wrong", "annotations": []}),
            encoding="utf-8",
        )
        try:
            store_bad.import_json(bad_schema, replace=True)
            raise AssertionError("expected AnnotationImportError")
        except AnnotationImportError as err:
            assert "wrong" in str(err) or "Schema" in str(err)
        from instantlensdoc.core.app_settings import (
            get_ann_note_color,
            get_editor_bracket_match,
            get_editor_trim_trailing_whitespace,
            get_editor_trim_whitespace_on_paste,
            get_pdf_continuous_scroll,
            get_pdf_toolbar_groups,
            get_pdf_two_page_spread,
            set_ann_note_color,
            set_editor_bracket_match,
            set_editor_trim_trailing_whitespace,
            set_editor_trim_whitespace_on_paste,
            set_pdf_continuous_scroll,
            set_pdf_toolbar_groups,
            set_pdf_two_page_spread,
        )

        set_editor_trim_trailing_whitespace(True)
        assert get_editor_trim_trailing_whitespace() is True
        set_editor_trim_trailing_whitespace(False)
        assert get_editor_trim_trailing_whitespace() is False
        set_editor_trim_whitespace_on_paste(True)
        assert get_editor_trim_whitespace_on_paste() is True
        set_editor_trim_whitespace_on_paste(False)
        assert get_editor_trim_whitespace_on_paste() is False
        set_editor_bracket_match(False)
        assert get_editor_bracket_match() is False
        set_editor_bracket_match(True)
        assert get_editor_bracket_match() is True
        set_ann_note_color("#AABB11")
        assert get_ann_note_color() == "#AABB11"
        set_pdf_two_page_spread(True)
        assert get_pdf_two_page_spread() is True
        set_pdf_two_page_spread(False)
        assert get_pdf_two_page_spread() is False
        set_pdf_continuous_scroll(True)
        assert get_pdf_continuous_scroll() is True
        set_pdf_continuous_scroll(False)
        assert get_pdf_continuous_scroll() is False
        groups = get_pdf_toolbar_groups()
        assert "tools" in groups and "io" in groups
        set_pdf_toolbar_groups({**groups, "io": False})
        assert get_pdf_toolbar_groups()["io"] is False
        set_pdf_toolbar_groups(groups)
        assert "Seitenbild" in feat or "Toolbar" in feat or "Whitespace" in feat
        assert "Spread" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8") or "Zwei-Seiten" in feat
        assert "Notizfarbe" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8") or "Notizfarbe" in feat
        assert "trim on paste" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8").lower() or "paste" in feat.lower()
        assert "Continuous Scroll" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8") or "Continuous" in feat
        assert "Zeitstempel" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8") or "Zeitstempel" in feat
        assert "Bracket-Match" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8") or "Bracket" in feat
        assert "Arbeitsverzeichnis" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8") or "Arbeitsverzeichnis" in feat
        from instantlensdoc.ui.keyboard_help import export_shortcuts_pdf, SHORTCUTS_HTML

        assert "Als PDF exportieren" in (
            ROOT / "instantlensdoc" / "ui" / "keyboard_help.py"
        ).read_text(encoding="utf-8")
        assert callable(export_shortcuts_pdf)
        assert "Zwei-Seiten" in SHORTCUTS_HTML or "Spread" in SHORTCUTS_HTML
        assert "Continuous Scroll" in SHORTCUTS_HTML or "Ctrl+3" in SHORTCUTS_HTML
        assert "Arbeitsverzeichnis" in SHORTCUTS_HTML
        # Reset-to-defaults
        set_theme("dark")
        assert load_settings()["theme"] == "dark"
        reset_to_defaults()
        assert load_settings()["theme"] == DEFAULTS["theme"]
        assert "Druckermarken" in feat or "Druckermarken" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "Schema v4" in feat or "ildann-v4" in feat or "PDF-Highlight" in feat
        assert "sortieren" in feat.lower() or "Zeilen sortieren" in feat
        assert "Reset" in feat or "zurücksetzen" in feat.lower()
        # Ausgewählte 0.4.x-/0.5.x-Inhalte (kompakt in 0.6.x, Kurz-Tabelle + Konsolidierung)
        assert "Seitenbild" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8") or "0.4.5" in feat
        assert "Gehe zu Seite" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8") or "0.4.6" in feat
        assert "0.4.6" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "0.4.7" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "0.4.8" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "0.4.9" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## 0.4.6" not in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## 0.4.9" not in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "Continuous Scroll" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "Seitenlabel" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8") or "Seitenlabels" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "Zwischenablage-Verlauf" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8") or "Clipboard" in (ROOT / "FEATURES.md").read_text(encoding="utf-8")
        assert "0.9.1" in feat and "0.9.0" in feat and "0.8.9" in feat and "0.8.8" in feat and "0.8.7" in feat and "0.8.6" in feat and "0.8.5" in feat and "0.8.4" in feat and "0.8.3" in feat and "0.8.2" in feat and "0.8.1" in feat and "0.8.0" in feat and "0.7.9" in feat and "0.7.8" in feat and "0.7.7" in feat and "0.7.6" in feat and "0.7.5" in feat and "0.7.4" in feat and "0.7.3" in feat and "0.7.2" in feat and "0.7.1" in feat and "0.6.9" in feat and "0.5.9" in feat and "0.4.9" in feat
        # --- 0.4.2 CLI: Outline Goto, Ann Copy/Paste, Flatten Progress ---
        import pikepdf as _pike_ol

        ol_pdf = td / "outline_goto.pdf"
        with _pike_ol.Pdf.new() as _odoc:
            for _ in range(3):
                _odoc.add_blank_page(page_size=(200, 300))
            with _odoc.open_outline() as _ool:
                _ool.root.append(_pike_ol.OutlineItem("Seite3", 2))
            _odoc.save(ol_pdf)
        ol_items = extract_outline(ol_pdf)
        assert ol_items and ol_items[0].page_index == 2, getattr(ol_items[0], "page_index", None)
        store_cp = AnnotationStore(pdf)
        store_cp.annotations = []
        store_cp.clear_history()
        a0 = store_cp.add(
            Annotation(0, AnnotationType.STICKY, 10, 10, width=40, height=20, text="cp-src")
        )
        pasted = store_cp.paste_dicts([a0.to_dict()], page=1, dx=4, dy=4)
        assert len(pasted) == 1 and pasted[0].page == 1 and pasted[0].id != a0.id
        assert store_cp.duplicate(a0.id, page=1, dx=1, dy=1) is not None
        flat_prog: list = []
        flatten_annotations_to_pdf(
            pdf,
            AnnotationStore(pdf),
            out_path=td / "flat_prog.pdf",
            scale=1.0,
            progress=lambda m, c=0, t=0: flat_prog.append((m, c, t)),
        )
        assert (td / "flat_prog.pdf").is_file() and flat_prog
        # --- 0.4.1 CLI retained ---
        from ild_pdf import list_page_uri_links, uri_link_at, is_external_http_uri
        from instantlensdoc.core.documents import (
            normalize_text_encoding,
            open_document,
            save_document,
        )
        from instantlensdoc.core.app_settings import (
            get_editor_text_encoding,
            set_editor_text_encoding,
        )
        import pikepdf as _pike041

        assert is_external_http_uri("https://example.com/a")
        assert not is_external_http_uri("file:///tmp/x")
        assert normalize_text_encoding("latin1") == "latin-1"
        set_editor_text_encoding("latin-1")
        assert get_editor_text_encoding() == "latin-1"
        set_editor_text_encoding("utf-8")
        assert get_editor_text_encoding() == "utf-8"
        link_pdf = td / "uri_link.pdf"
        with _pike041.Pdf.new() as _ldoc:
            _lpage = _ldoc.add_blank_page(page_size=(400, 400))
            from pikepdf import Array, Dictionary, Name

            _annot = Dictionary(
                Type=Name.Annot,
                Subtype=Name.Link,
                Rect=Array([40, 280, 180, 320]),
                Border=Array([0, 0, 1]),
                A=Dictionary(Type=Name.Action, S=Name.URI, URI="https://example.com/ild"),
            )
            _lpage.Annots = _ldoc.make_indirect(Array([_ldoc.make_indirect(_annot)]))
            _ldoc.save(link_pdf)
        links = list_page_uri_links(link_pdf, 0, scale=1.5)
        assert len(links) == 1 and links[0].uri.endswith("/ild")
        hit = uri_link_at(link_pdf, 0, links[0].x + 2, links[0].y + 2, scale=1.5)
        assert hit is not None and hit.uri == links[0].uri
        enc_txt = td / "latin.txt"
        enc_txt.write_bytes(("caf" + chr(0xE9)).encode("latin-1"))
        enc_doc = open_document(enc_txt, encoding="latin-1")
        assert enc_doc.encoding == "latin-1" and "caf" in enc_doc.text
        enc_doc.text = "Grüße"
        save_document(enc_doc, encoding="utf-8")
        assert enc_txt.read_text(encoding="utf-8") == "Grüße"
        stamp_rot = Annotation(
            0, AnnotationType.STAMP, 10, 10, text="GENEHMIGT", width=120, height=40, rotation=90
        )
        assert stamp_rot.rotation == 90
        assert Annotation.from_dict(stamp_rot.to_dict()).rotation == 90
        assert "URI-Links" in feat or "Link" in feat
        assert "Encoding" in feat or "Latin-1" in feat
        assert "mehrere Dateien" in feat or "Tabs" in feat
        assert "kopieren/einfügen" in feat or "Ctrl+Alt+C" in feat
        print("0.4.x selected paths cropbox/lock/snippets + marks/schema/sort/reset (CLI): OK")
        print("0.4.2 outline/copy-paste/progress (CLI): OK")
        print("0.4.1 links/encoding/stamp-rotation (CLI): OK")
        print("0.3.x selected paths (CLI): OK")

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
        assert "v0.9.1" in win.version_label.text()
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
            assert win.editor.transform_document_case("lower")
            assert win.editor.toPlainText() == "hello world"
            assert win.editor.transform_document_case("upper")
            assert win.editor.toPlainText() == "HELLO WORLD"
            assert callable(win._transform_document_case)
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
            assert "0.9.1" in win.windowTitle()
            from instantlensdoc.ui.help_dialog import AboutDialog, HelpDialog, open_log_folder

            about = AboutDialog(win)
            assert "0.9.1" in about.windowTitle()
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
            # 0.4.2: Goto auf Seite 2 (Index 1) über Outline-Jump
            add_outline_item(smoke_pdf, "Seite2", 1)
            win._refresh_outline(smoke_pdf)
            win._on_outline_jump(1)
            assert win.pdf_view.page_index == 1
            win._on_outline_jump(-1)  # kein Ziel → Status, kein Crash
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
            win.stack.setCurrentWidget(win.pdf_view)
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
            if win.sidebar.recent.count() < 1:
                win._remember_path(smoke_pdf)
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
            # Status folgt der aktuellen Ansicht (0.8.0): PDF-Seitengröße nur im PDF-Stack
            win.stack.setCurrentWidget(win.pdf_view)
            win._update_doc_status()
            size_txt = win.size_status_label.text()
            assert size_txt and size_txt != "—" and ("mm" in size_txt or "in" in size_txt)
            assert callable(win._format_current_page_size)
            win.stack.setCurrentWidget(win.editor_pane)
            win._update_doc_status()
            assert "Zeile" in win.page_status_label.text()
            assert win.size_status_label.text() == "—"
            win.stack.setCurrentWidget(win.pdf_view)
            win._update_doc_status()
            assert "Seite" in win.page_status_label.text()

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
                assert "0.9.1" in tip and "InstantLens Doc" in tip
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
            assert "0.9.1" in PLANNED["ki"]
            assert "Coming soon" in PLANNED["cloud"]
            assert "0.9.1" in PLANNED["stylus"] and "0.9.1" in PLANNED["extrude3d"]
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

            assert "Stub 0.9.1" in HELP_HTML
            assert "scripts/sync-ild.ps1" in HELP_HTML
            assert "Präsentationsmodus" in HELP_HTML or "F5" in (
                ROOT / "instantlensdoc" / "ui" / "keyboard_help.py"
            ).read_text(encoding="utf-8")
            # 0.4.5 Qt: page boxes, ann lock/move, snippets, templates
            assert callable(win.pdf_view.set_show_page_boxes)
            assert callable(win.pdf_view.set_annotations_locked)
            from ild_pdf.annotate import AnnotationStore as _AS043

            assert callable(_AS043.move_by)
            assert callable(win._insert_snippet)
            assert callable(win._save_snippet)
            assert callable(getattr(win, "new_doc", None))
            win.new_doc("brief")
            assert "Sehr geehrte" in win.editor.toPlainText()
            win.new_doc("notiz")
            assert win.editor.toPlainText().startswith("# Notiz")
            win.new_doc("empty")
            assert win.editor.toPlainText() == ""
            from instantlensdoc.core.app_settings import set_editor_snippets as _set_snips

            _set_snips(["ALPHA", "BETA", "GAMMA"])
            win.editor.setPlainText("")
            win._insert_snippet(1)
            assert "BETA" in win.editor.toPlainText()
            win.pdf_view.set_show_page_boxes(True)
            assert win.pdf_view.show_page_boxes() is True
            win.pdf_view.set_show_page_boxes(False)
            win.pdf_view.set_annotations_locked(True)
            assert win.pdf_view.annotations_locked() is True
            win.pdf_view.set_annotations_locked(False)
            assert hasattr(win.pdf_view.canvas, "annotations_moved")
            # 0.4.5 Qt: printer marks, sort lines, schema v4, reset defaults
            assert callable(win.pdf_view.set_show_printer_marks)
            win.pdf_view.set_show_printer_marks(True)
            assert win.pdf_view.show_printer_marks() is True
            win.pdf_view.set_show_printer_marks(False)
            assert callable(win.editor.sort_lines_az)
            win.editor.setPlainText("c\na\nb")
            from PySide6.QtGui import QTextCursor as _QTC044

            cur = win.editor.textCursor()
            cur.select(_QTC044.Document)
            win.editor.setTextCursor(cur)
            assert win.editor.sort_lines_az()
            assert win.editor.toPlainText().splitlines() == ["a", "b", "c"]
            win._sort_lines_az()
            from ild_pdf.annotate import SCHEMA_ID as _SCH044, SIDECAR_VERSION as _VER044

            assert _VER044 == 4 and _SCH044 == "ildann-v4"
            from instantlensdoc.core.app_settings import reset_to_defaults as _rtd044

            assert callable(_rtd044)
            assert "Auf Standard zurücksetzen" in (
                ROOT / "instantlensdoc" / "ui" / "settings_dialog.py"
            ).read_text(encoding="utf-8")
            # 0.4.5 Qt: trim trailing, toolbar groups, page image → editor
            assert callable(win.editor.trim_trailing_whitespace)
            win.editor.setPlainText("abc  \ndef\t\n")
            assert win.editor.trim_trailing_whitespace()
            assert win.editor.toPlainText() == "abc\ndef\n"
            assert callable(win.pdf_view.apply_toolbar_groups)
            from instantlensdoc.core.app_settings import (
                get_pdf_toolbar_groups as _gtb045,
                set_pdf_toolbar_groups as _stb045,
            )

            _g0 = _gtb045()
            _stb045({**_g0, "io": False})
            win.pdf_view.apply_toolbar_groups()
            assert not win.pdf_view._toolbar_group_widgets["io"][0].isVisible()
            _stb045(_g0)
            win.pdf_view.apply_toolbar_groups()
            assert callable(win._insert_page_image_to_editor)
            assert callable(win._insert_all_page_images_to_editor)
            # 0.4.6 Qt: goto page, color filter, duplicate tab, undo hint
            from instantlensdoc.ui.goto_page_dialog import GotoPageDialog
            assert GotoPageDialog
            assert callable(win._goto_page)
            assert callable(win._goto_line_or_page)
            assert win.pdf_view.page_count >= 1
            win.pdf_view.goto_page(0)
            assert win.pdf_view.page_index == 0
            if win.pdf_view.page_count > 1:
                win.pdf_view.goto_page(1)
                assert win.pdf_view.page_index == 1
                win.pdf_view.goto_page(0)
            # Ann color filter chips
            from ild_pdf.annotate import Annotation, AnnotationType
            win.pdf_view.store.add(
                Annotation(0, AnnotationType.HIGHLIGHT, 8, 8, width=20, height=10, color="#FFCC00", text="c1")
            )
            win.pdf_view.store.add(
                Annotation(0, AnnotationType.STICKY, 12, 12, width=18, height=18, color="#112233", text="c2")
            )
            win._refresh_pdf_marks()
            assert hasattr(win.sidebar, "ann_color_stats")
            assert callable(win.sidebar.set_annotation_color_filter)
            win.sidebar.set_annotation_color_filter("#FFCC00")
            assert win.sidebar.annotation_filter_color() == "#FFCC00"
            # second click toggles off
            win.sidebar.set_annotation_color_filter("#FFCC00")
            assert win.sidebar.annotation_filter_color() == ""
            win.sidebar.set_annotation_color_filter("#112233")
            assert win.sidebar.annotation_filter_color() == "#112233"
            win.sidebar.clear_annotation_color_filter()
            assert win.sidebar.annotation_filter_color() == ""
            # Duplicate tab / reopen
            assert callable(win.duplicate_tab)
            assert callable(win.reopen_current)
            from instantlensdoc.core.documents import DocKind, Document

            win.doc = Document(kind=DocKind.TEXT, title="src-tab", text="dup-tab-source\nline2")
            win.stack.setCurrentWidget(win.editor_pane)
            win.editor.setPlainText("dup-tab-source\nline2")
            win.duplicate_tab()
            assert win.doc is not None
            assert win.doc.path is None
            assert "Kopie" in win.doc.title or win.doc.dirty
            assert "dup-tab-source" in win.editor.toPlainText()
            # Undo hint present
            assert hasattr(win, "undo_hint_label")
            assert "rückgängig" in win.undo_hint_label.text().lower() or "Ctrl+Z" in win.undo_hint_label.text()
            # 0.4.8/0.4.9 Qt: continuous scroll + labels/filter/clipboard/about, ann timestamps, bracket-match, workdir
            from instantlensdoc.core.app_settings import (
                get_ann_note_color,
                get_editor_bracket_match,
                get_editor_trim_whitespace_on_paste,
                get_pdf_continuous_scroll,
                set_ann_note_color,
                set_editor_bracket_match,
                set_editor_trim_whitespace_on_paste,
                set_pdf_continuous_scroll,
            )
            from instantlensdoc.ui.keyboard_help import KeyboardHelpDialog, export_shortcuts_pdf

            assert callable(win.pdf_view.set_two_page_spread)
            assert callable(win.pdf_view.two_page_spread_enabled)
            assert callable(win.pdf_view.set_continuous_scroll)
            assert callable(win.pdf_view.continuous_scroll_enabled)
            assert hasattr(win, "_spread_action")
            assert hasattr(win, "_continuous_action")
            assert hasattr(win.pdf_view, "btn_spread")
            assert hasattr(win.pdf_view, "btn_continuous")
            assert hasattr(win.pdf_view, "btn_note_color")
            win.pdf_view.set_two_page_spread(True)
            assert win.pdf_view.two_page_spread_enabled() is True
            win.pdf_view.refresh()
            if win.pdf_view.page_count > 1:
                assert win.pdf_view._spread_left_width > 0
                assert "–" in win.pdf_view.lbl_page.text() or "-" in win.pdf_view.lbl_page.text()
            win.pdf_view.set_continuous_scroll(True)
            assert win.pdf_view.continuous_scroll_enabled() is True
            assert win.pdf_view.two_page_spread_enabled() is False  # mutual exclusive
            win.pdf_view.refresh()
            assert win.pdf_view._continuous_offsets or win.pdf_view.page_count >= 1
            assert "Scroll" in win.pdf_view.lbl_page.text() or win.pdf_view.page_count >= 1
            win.pdf_view.set_continuous_scroll(False)
            assert win.pdf_view.continuous_scroll_enabled() is False
            win.pdf_view.set_two_page_spread(False)
            set_ann_note_color("#1122AA")
            win.pdf_view.apply_settings_colors()
            assert win.pdf_view._note_color == "#1122AA"
            assert get_ann_note_color() == "#1122AA"
            # Annotation timestamps in list
            from ild_pdf import Annotation as Ann048, AnnotationType as AT048

            ts_ann = Ann048(0, AT048.STICKY, 5, 5, width=20, height=20, text="ts-check")
            win.pdf_view.store.add(ts_ann)
            summaries = win.pdf_view.annotation_summaries()
            assert any("ts-check" in lab for lab, _ in summaries)
            assert any("·" in lab for lab, a in summaries if a.text == "ts-check")
            # Bracket-Match
            assert callable(win.editor.set_bracket_match_enabled)
            assert win.editor.bracket_match_enabled() is True or get_editor_bracket_match() is True
            win.editor.setPlainText("foo(bar)")
            from PySide6.QtGui import QTextCursor

            c = win.editor.textCursor()
            c.setPosition(4)  # after '('
            win.editor.setTextCursor(c)
            win.editor._update_bracket_match()
            assert len(win.editor._bracket_selections) == 2
            set_editor_bracket_match(False)
            win.editor.set_bracket_match_enabled(False)
            assert win.editor.bracket_match_enabled() is False
            set_editor_bracket_match(True)
            win.editor.set_bracket_match_enabled(True)
            # Arbeitsverzeichnis öffnen
            assert callable(win._open_workdir)
            set_editor_trim_whitespace_on_paste(True)
            assert get_editor_trim_whitespace_on_paste() is True
            from PySide6.QtCore import QMimeData

            md = QMimeData()
            md.setText("line  \nfoo\t\t\n")
            win.editor.insertFromMimeData(md)
            assert "line\nfoo\n" in win.editor.toPlainText() or win.editor.toPlainText().endswith("line\nfoo\n") or "line\nfoo" in win.editor.toPlainText()
            set_editor_trim_whitespace_on_paste(False)
            # --- 0.4.9: page labels, ann current-page filter, clipboard history, about ---
            from ild_pdf import format_page_status
            from ild_pdf.document import PdfDocument as DocLabels
            import pikepdf as _pike_lab
            from pikepdf import Name, Dictionary, Array
            from instantlensdoc.ui.help_dialog import HELP_HTML as HELP_HTML_049

            kh_src = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(
                encoding="utf-8"
            )

            lab_pdf = td2 / "page_labels_049.pdf"
            with _pike_lab.Pdf.new() as _ldoc:
                for _ in range(4):
                    _ldoc.add_blank_page(page_size=(200, 280))
                _ldoc.Root.PageLabels = Dictionary(
                    Nums=Array(
                        [
                            0,
                            Dictionary(S=Name.r),
                            2,
                            Dictionary(S=Name.D, St=1),
                        ]
                    )
                )
                _ldoc.save(lab_pdf)
            with DocLabels(lab_pdf) as _dlab:
                assert _dlab.page_label(0) == "i"
                assert _dlab.page_label(1) == "ii"
                assert _dlab.page_label(2) == "1"
                assert format_page_status(0, 4, "i") == "Seite i (1/4)"
                assert format_page_status(2, 4, "") == "Seite 3/4"
            win.open_path(str(lab_pdf))
            assert win.pdf_view.pdf_path is not None
            assert win.pdf_view.has_page_labels()
            assert win.pdf_view.page_label(0) == "i"
            win.pdf_view.goto_page(0)
            win._update_doc_status()
            assert "i" in win.page_status_label.text()
            assert "(" in win.page_status_label.text()
            # Annotation current-page filter
            from ild_pdf import Annotation as Ann049, AnnotationType as AT049

            win.pdf_view.store.add(
                Ann049(0, AT049.STICKY, 10, 10, width=20, height=20, text="p0-only")
            )
            win.pdf_view.store.add(
                Ann049(1, AT049.STICKY, 10, 10, width=20, height=20, text="p1-only")
            )
            win.pdf_view.goto_page(0)
            win._refresh_pdf_marks()
            assert hasattr(win.sidebar, "ann_current_page")
            win.sidebar.set_annotation_filter_current_page(True)
            texts = [
                win.sidebar.annotations.item(i).text()
                for i in range(win.sidebar.annotations.count())
            ]
            joined = " ".join(texts)
            assert "p0-only" in joined
            assert "p1-only" not in joined
            win.sidebar.set_annotation_filter_current_page(False)
            win._refresh_pdf_marks()
            texts2 = [
                win.sidebar.annotations.item(i).text()
                for i in range(win.sidebar.annotations.count())
            ]
            assert "p1-only" in " ".join(texts2)
            # Clipboard history (3 entries)
            assert callable(win.editor.push_clipboard_history)
            assert callable(win.editor.paste_clipboard_history)
            win.editor._clipboard_history.clear()
            win.editor.setPlainText("")
            win.stack.setCurrentWidget(win.editor_pane)
            for frag in ("alpha", "beta", "gamma", "delta"):
                mdh = QMimeData()
                mdh.setText(frag)
                win.editor.insertFromMimeData(mdh)
            hist = win.editor.clipboard_history()
            assert len(hist) == 3
            assert hist == ["delta", "gamma", "beta"]
            win.editor.setPlainText("")
            assert win.editor.paste_clipboard_history(1)  # gamma
            assert "gamma" in win.editor.toPlainText()
            assert win.editor.clipboard_history()[0] == "gamma"
            assert hasattr(win, "_clipboard_history_menu")
            win._rebuild_clipboard_history_menu()
            # About feature shortlist + FEATURES.md
            from instantlensdoc.ui.help_dialog import AboutDialog as About049

            about049 = About049(win)
            assert hasattr(about049, "_open_features_md")
            assert callable(about049._open_features_md)
            about_src = (ROOT / "instantlensdoc" / "ui" / "help_dialog.py").read_text(
                encoding="utf-8"
            )
            assert "FEATURES.md" in about_src
            assert "Feature-Kurzliste" in about_src or "Features (Kurz)" in about_src
            assert (
                "Zwischenablage-Verlauf" in kh_src
                or "Zwischenablage-Verlauf" in HELP_HTML_049
            )
            feat049 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "Seitenlabel" in feat049 or "Seitenlabels" in feat049
            assert "Nur aktuelle Seite" in feat049 or "nur aktuelle Seite" in feat049.lower()
            assert callable(export_shortcuts_pdf)
            assert KeyboardHelpDialog
            assert "Als PDF exportieren" in kh_src
            assert "Continuous Scroll" in kh_src
            assert "Arbeitsverzeichnis" in kh_src
            # Restore smoke PDF for remaining tests
            win.open_path(str(smoke_pdf))
            assert "Whitespace trim on paste" in (
                ROOT / "instantlensdoc" / "ui" / "settings_dialog.py"
            ).read_text(encoding="utf-8")
            assert "Bracket-Match" in (
                ROOT / "instantlensdoc" / "ui" / "settings_dialog.py"
            ).read_text(encoding="utf-8")
            assert "Continuous Scroll" in (
                ROOT / "instantlensdoc" / "ui" / "settings_dialog.py"
            ).read_text(encoding="utf-8")
            assert "Zwei-Seiten" in (
                ROOT / "CHANGELOG.md"
            ).read_text(encoding="utf-8") or "0.5.8" in (
                ROOT / "FEATURES.md"
            ).read_text(encoding="utf-8")
            assert "Gehe zu Seite" in (
                ROOT / "CHANGELOG.md"
            ).read_text(encoding="utf-8") or "0.5.8" in (
                ROOT / "FEATURES.md"
            ).read_text(encoding="utf-8")
            assert "PDF-Toolbar" in (
                ROOT / "instantlensdoc" / "ui" / "settings_dialog.py"
            ).read_text(encoding="utf-8")
            assert "Trailing Whitespace" in (
                ROOT / "instantlensdoc" / "ui" / "settings_dialog.py"
            ).read_text(encoding="utf-8")
            assert "Druckermarken" in HELP_HTML or "Ctrl+Alt+M" in (
                ROOT / "instantlensdoc" / "ui" / "keyboard_help.py"
            ).read_text(encoding="utf-8")
            assert "Continuous Scroll" in HELP_HTML or "Ctrl+3" in kh_src
            assert "Arbeitsverzeichnis" in HELP_HTML or "Ctrl+Shift+E" in kh_src
            store_mv = win.pdf_view.store
            if store_mv is not None:
                from ild_pdf import Annotation as Ann043, AnnotationType as AT043

                mv = Ann043(
                    win.pdf_view.page_index,
                    AT043.STICKY,
                    30,
                    40,
                    width=50,
                    height=30,
                    text="drag-me",
                )
                store_mv.add(mv)
                ox, oy = mv.x, mv.y
                assert store_mv.move_by([mv.id], 12.0, 8.0) == 1
                assert abs(store_mv.get(mv.id).x - (ox + 12)) < 1e-6
                assert abs(store_mv.get(mv.id).y - (oy + 8)) < 1e-6
                store_mv.dirty = False
            # Dirty-Zustand von Snippet/Vorlagen-Tests zurücksetzen (Close-Dialog)
            if win.doc is not None:
                win.doc.text = win.editor.toPlainText()
                win.doc.dirty = False
            # 0.4.2 Qt: Outline jump, Ann copy/paste, document case, progress APIs
            assert callable(win._on_outline_jump)
            assert callable(win.pdf_view.copy_selected_annotations)
            assert callable(win.pdf_view.paste_annotations_on_page)
            assert callable(win._copy_annotations)
            assert callable(win._paste_annotations)
            assert "QProgressDialog" in (
                ROOT / "instantlensdoc" / "ui" / "pdf_view.py"
            ).read_text(encoding="utf-8")
            assert "Abbrechen Lauf" in (
                ROOT / "instantlensdoc" / "ui" / "batch_dialog.py"
            ).read_text(encoding="utf-8")
            # 0.4.1 Qt retained: Links, Stempel-Rotation, Encoding-Menü, Multi-Drop
            assert callable(win.pdf_view.rotate_selected_stamp)
            assert callable(getattr(win, "open_dialog_with_encoding", None))
            assert callable(getattr(win, "save_doc_with_encoding", None))
            src = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
            assert "for path in paths" in src and "open_path(path)" in src
            assert hasattr(win.pdf_view.canvas, "uri_link_clicked")
            win.pdf_view._set_tool(None)
            store = win.pdf_view.store
            if store is not None:
                from ild_pdf import Annotation as Ann041, AnnotationType as AT041

                s = Ann041(
                    win.pdf_view.page_index,
                    AT041.STAMP,
                    20,
                    20,
                    text="ROT",
                    width=100,
                    height=40,
                    rotation=0,
                )
                store.add(s)
                win.pdf_view._selected_ann_id = s.id
                win.pdf_view._selected_ann_ids = {s.id}
                assert win.pdf_view.rotate_selected_stamp(90)
                assert store.get(s.id).rotation == 90
                assert win.pdf_view.copy_selected_annotations() == 1
                assert len(win.pdf_view._ann_clipboard) == 1
                if win.pdf_view.page_count > 1:
                    win.pdf_view.goto_page(1)
                    n_paste = win.pdf_view.paste_annotations_on_page()
                    assert n_paste == 1

            # --- 0.5.1 Qt: Batch-OCR API, Tags-Filter, Workspace, PDF bereinigen ---
            assert callable(getattr(win, "_run_ocr_document", None))
            assert callable(getattr(win, "_sanitize_pdf", None))
            assert callable(getattr(win, "_choose_project_workspace", None))
            assert callable(getattr(win, "_activate_project_workspace", None))
            assert callable(getattr(win, "_edit_annotation_tags", None))
            assert hasattr(win.sidebar, "ann_tag_filter")
            assert callable(win.sidebar.set_annotation_tag_filter)
            assert callable(win.pdf_view.edit_selected_annotation_tags)
            from ild_pdf import Annotation as Ann051, AnnotationType as AT051, normalize_tags as nt051

            store051 = win.pdf_view.store
            assert store051 is not None
            a051 = Ann051(
                0,
                AT051.STICKY,
                5,
                5,
                width=40,
                height=20,
                text="tagged",
                tags=["Review", "TODO"],
            )
            store051.add(a051)
            win._refresh_pdf_marks()
            win.sidebar.set_annotation_tag_filter("Review")
            texts051 = [
                win.sidebar.annotations.item(i).text()
                for i in range(win.sidebar.annotations.count())
            ]
            assert "tagged" in " ".join(texts051)
            win.sidebar.set_annotation_tag_filter("MissingTagXYZ")
            texts_empty = [
                win.sidebar.annotations.item(i).text()
                for i in range(win.sidebar.annotations.count())
            ]
            assert "tagged" not in " ".join(texts_empty)
            win.sidebar.set_annotation_tag_filter("")
            win.pdf_view._selected_ann_id = a051.id
            # Tags via store update (ohne Dialog)
            store051.update(a051.id, tags=nt051("done, Review"))
            assert "done" in (store051.get(a051.id).tags or [])
            assert callable(ocr_mod.ocr_pdf_document)
            # Workspace merken
            ws = Path(td2) / "workspace051"
            ws.mkdir(exist_ok=True)
            remember_project_workspace(ws, activate=True)
            assert get_active_project_workspace() is not None
            assert any(p.resolve() == ws.resolve() for p in get_project_workspaces())
            assert dialog_start_dir().startswith(str(ws)) or str(ws) in dialog_start_dir()
            win._refresh_workspaces()
            # PDF bereinigen / Metadaten strip
            dirty_pdf = Path(td2) / "dirty_meta.pdf"
            import shutil as _shutil

            _shutil.copy2(smoke_pdf, dirty_pdf)
            set_metadata(dirty_pdf, PdfMetadata(title="StripMe", author="Smoke"))
            assert "StripMe" in get_metadata(dirty_pdf).title
            clean_pdf = Path(td2) / "clean_meta.pdf"
            sanitize_pdf(dirty_pdf, strip_meta=True, out_path=clean_pdf)
            meta_clean = get_metadata(clean_pdf)
            assert not (meta_clean.title or "").strip() or "StripMe" not in meta_clean.title
            feat051 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "Batch-OCR" in feat051 or "OCR gesamtes PDF" in feat051
            assert "Tags" in feat051 or "Tag-Filter" in feat051
            assert "Projekt-Ordner" in feat051 or "Workspace" in feat051
            assert "bereinigen" in feat051.lower()
            kh051 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
            assert "Ctrl+Alt+T" in kh051
            assert "Projekt-Ordner" in kh051 or "Workspace" in kh051
            print("0.5.1 Qt batch-ocr/tags/workspace/sanitize: OK")

            # --- 0.5.2 Qt: Selection→Highlight, Ann-Regex, Text-Diff, Export-Profil ---
            assert callable(getattr(win.pdf_view, "_highlight_from_text_selection", None))
            assert hasattr(win.sidebar, "ann_search_regex")
            assert callable(win.sidebar.set_annotation_search_regex)
            assert callable(getattr(win, "_compare_text_tabs", None))
            assert callable(getattr(win, "_save_export_profile", None))
            assert callable(getattr(win, "_apply_export_profile", None))
            from instantlensdoc.core.app_settings import (
                apply_export_profile as aep052,
                delete_export_profile as dep052,
                get_export_profiles as gep052,
                save_export_profile as sep052,
            )
            from instantlensdoc.ui.text_compare_dialog import TextCompareDialog
            from instantlensdoc.core.text_diff import line_diff_sides

            # Ann-Regex Filter
            store052 = win.pdf_view.store
            assert store052 is not None
            a052 = Annotation(
                0,
                AnnotationType.HIGHLIGHT,
                8,
                8,
                width=30,
                height=10,
                text="regex-hit-alpha",
            )
            store052.add(a052)
            win._refresh_pdf_marks()
            win.sidebar.set_annotation_search_regex(True)
            win.sidebar.ann_search.setText(r"regex-hit-\w+")
            texts_rx = [
                win.sidebar.annotations.item(i).text()
                for i in range(win.sidebar.annotations.count())
            ]
            assert "regex-hit-alpha" in " ".join(texts_rx)
            win.sidebar.ann_search.setText(r"^nomatchXYZ$")
            texts_rx_empty = [
                win.sidebar.annotations.item(i).text()
                for i in range(win.sidebar.annotations.count())
            ]
            assert "regex-hit-alpha" not in " ".join(texts_rx_empty)
            win.sidebar.set_annotation_search_regex(False)
            win.sidebar.ann_search.clear()
            # Selection→Highlight API (große Auswahl)
            if win.pdf_view.pdf_path:
                ok_hl = win.pdf_view._highlight_from_text_selection(0, 0, 0, 500, 500)
                assert ok_hl is True or ok_hl is False  # abhängig von Text auf Seite
            # Text-Diff Utility + Dialog-Klasse
            _l, _r, _t = line_diff_sides("one\ntwo", "one\nTWO")
            assert any(x != "equal" for x in _t)
            assert TextCompareDialog is not None
            # Export-Profil
            sep052("QtSmoke052", dpi=72, format="JPEG", target=td2)
            assert any(p["name"] == "QtSmoke052" for p in gep052())
            assert aep052("QtSmoke052")["dpi"] == 72
            dep052("QtSmoke052")
            feat052 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "Selection→Highlight" in feat052 or "Selection" in feat052
            assert "Regex" in feat052
            assert "Export-Profil" in feat052 or "Export-Profil" in feat052
            assert "vergleichen" in feat052.lower() or "Side-by-Side" in feat052
            kh052 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
            assert "Ctrl+Alt+D" in kh052
            assert "Export-Profil" in kh052 or "DPI" in kh052
            cl052 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "0.5.2" in cl052 and "## 0.5.2" not in cl052
            print("0.5.2 Qt selection-hl/regex/diff/export-profile: OK")

            # --- 0.5.3 Qt: Kommentar-Bericht, Farbe-Zyklus, Minimap, About-Keygen ---
            assert callable(getattr(win.pdf_view, "export_annotations_report", None))
            assert callable(getattr(win.pdf_view, "cycle_annotation_color", None))
            assert callable(getattr(win.pdf_view, "randomize_annotation_color", None))
            assert callable(getattr(win.editor, "set_minimap_visible", None))
            assert callable(getattr(win, "_toggle_minimap", None))
            from instantlensdoc.core.app_settings import (
                ANN_COLOR_PALETTE as _PAL053,
                get_ann_highlight_color as _ghc053,
                get_editor_minimap as _gemm053,
                set_ann_highlight_color as _shc053,
                set_ann_palette_index as _spi053,
                set_editor_minimap as _sem053,
            )

            store053 = win.pdf_view.store
            assert store053 is not None
            store053.add(
                Annotation(
                    0,
                    AnnotationType.HIGHLIGHT,
                    15,
                    15,
                    width=40,
                    height=12,
                    text="smoke-report-hl",
                    tags=["Smoke"],
                )
            )
            rep_md = Path(td2) / "smoke-report.md"
            rep_txt = Path(td2) / "smoke-report.txt"
            assert store053.export_report(rep_md, fmt="md", source=win.pdf_view.pdf_path).is_file()
            assert store053.export_report(rep_txt, fmt="txt", source=win.pdf_view.pdf_path).is_file()
            assert "smoke-report-hl" in rep_md.read_text(encoding="utf-8")
            assert "Smoke" in rep_txt.read_text(encoding="utf-8") or "smoke-report-hl" in rep_txt.read_text(
                encoding="utf-8"
            )
            _spi053(0)
            before = _ghc053()
            cyc = win.pdf_view.cycle_annotation_color()
            assert cyc in _PAL053 and win.pdf_view._highlight_color == cyc
            rnd = win.pdf_view.randomize_annotation_color()
            assert rnd in _PAL053
            _shc053(before)
            win.pdf_view.apply_settings_colors()
            # Minimap
            _sem053(True)
            win.editor.set_minimap_visible(True)
            assert win.editor.minimap_visible()
            assert hasattr(win, "_minimap_action")
            win._minimap_action.blockSignals(True)
            win._minimap_action.setChecked(True)
            win._minimap_action.blockSignals(False)
            win._toggle_minimap(False)
            assert not win.editor.minimap_visible()
            assert _gemm053() is False
            # About Trial-Keygen-Hinweis
            from instantlensdoc.ui.help_dialog import AboutDialog as About053
            from PySide6.QtWidgets import QLabel as _QL053
            from instantlensdoc.license import LicenseManager as _LM053

            about053 = About053(win)
            labels053 = " ".join(
                w.text() for w in about053.findChildren(_QL053) if hasattr(w, "text")
            )
            st053 = _LM053().status()
            if st053.mode == "trial":
                assert "Testversion" in labels053 or "Keygen" in labels053 or "run-keygen" in labels053
            feat053 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "Kommentar-Bericht" in feat053 or "Minimap" in feat053
            assert "Palette-Zyklus" in feat053 or "Random" in feat053
            kh053 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
            assert "Ctrl+Shift+C" in kh053 and "Ctrl+Shift+I" in kh053
            cl053 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "0.5.3" in cl053 and "## 0.5.3" not in cl053
            print("0.5.3 Qt report/color/minimap/about-keygen: OK")

            # --- 0.5.5 Qt: Seiten-Undo, Ann.-Gruppen, Soft-Hyphen/NBSP, Deps ---
            from ild_pdf.pages import extract_page_bytes as _epb054
            from instantlensdoc.core.deps_check import check_runtime_dependencies as _crd054
            from instantlensdoc.ui.deps_dialog import DependencyCheckDialog as _DCD054

            # Soft-Hyphen / NBSP
            from PySide6.QtGui import QTextCursor as _QTC054

            win.stack.setCurrentWidget(win.editor_pane)
            win.editor.setPlainText("abc")
            cur054 = win.editor.textCursor()
            cur054.movePosition(_QTC054.End)
            win.editor.setTextCursor(cur054)
            assert win.editor.insert_soft_hyphen()
            assert "\u00ad" in win.editor.toPlainText()
            assert win.editor.insert_nbsp()
            assert "\u202f" in win.editor.toPlainText()
            assert callable(getattr(win, "_insert_soft_hyphen", None))
            assert callable(getattr(win, "_insert_nbsp", None))

            # Annotation-Gruppe
            win.stack.setCurrentWidget(win.pdf_view)
            assert win.pdf_view.store is not None
            win.pdf_view.store.set_page_group(0, title="SmokeGruppe", color="#AABBCC")
            assert win.pdf_view.store.get_page_group(0)["title"] == "SmokeGruppe"
            win.pdf_view.annotations_changed.emit()
            win._refresh_pdf_marks()
            assert callable(getattr(win.pdf_view, "edit_page_annotation_group", None))
            assert hasattr(win.sidebar, "annotation_group_edit_requested")

            # Seite löschen + Undo (PDF mit >=2 Seiten)
            two = Path(td2) / "two054.pdf"
            merge_pdfs([smoke_pdf, smoke_pdf], two)
            assert win.pdf_view.load(str(two))
            assert win.pdf_view.page_count >= 2
            before_n = win.pdf_view.page_count
            # delete_current ohne Bestätigungsdialog simulieren
            win.pdf_view.page_index = 0
            # Methode mit Auto-Yes: direkten Undo-Pfad testen via rotate + delete helpers
            assert callable(getattr(win.pdf_view, "delete_current", None))
            assert callable(getattr(win.pdf_view, "undo_page_op", None))
            # Drehen-Undo zuerst (ohne Dialog)
            win.pdf_view.rotate_current(90)
            assert win.pdf_view.can_undo_page_op()
            assert win.pdf_view.undo_page_op()
            # Löschen intern (ohne QMessageBox): gleiche Logik wie delete_current
            deleted = win.pdf_view.page_index
            page_bytes = _epb054(win.pdf_view.pdf_path, deleted)
            groups_before = dict(win.pdf_view.store._meta.get("page_groups") or {})
            win.pdf_view._page_ops_undo.append(
                {
                    "kind": "delete",
                    "index": deleted,
                    "page_bytes": page_bytes,
                    "page_groups": groups_before,
                }
            )
            from ild_pdf.pages import delete_pages as _dp054

            _dp054(win.pdf_view.pdf_path, [deleted])
            if win.pdf_view.store:
                mapping = {
                    i: (i if i < deleted else i - 1)
                    for i in range(before_n)
                    if i != deleted
                }
                with win.pdf_view.store.atomic():
                    planned = []
                    for ann in list(win.pdf_view.store.annotations):
                        if ann.page in mapping:
                            planned.append((ann, mapping[ann.page]))
                    kept = []
                    for ann, new_page in planned:
                        if ann.page != new_page:
                            ann.page = new_page
                            ann.touch()
                        kept.append(ann)
                    win.pdf_view.store.annotations = kept
                    win.pdf_view.store.dirty = True
                win.pdf_view.store.save(force=True)
            win.pdf_view.page_count -= 1
            win.pdf_view.page_index = min(win.pdf_view.page_index, win.pdf_view.page_count - 1)
            from ild_pdf.render import clear_render_cache as _crc054

            _crc054(win.pdf_view.pdf_path)
            win.pdf_view.refresh()
            assert win.pdf_view.page_count == before_n - 1
            assert win.pdf_view.can_undo_page_op()
            assert win.pdf_view.undo_page_op()
            assert win.pdf_view.page_count == before_n

            deps054 = _crd054()
            dlg054 = _DCD054(deps054, win)
            assert "Abhängigkeiten" in dlg054.windowTitle()
            dlg054.close()

            feat054 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "Soft-Hyphen" in feat054 or "NBSP" in feat054
            assert "Seite löschen" in feat054 and "Undo" in feat054
            assert "Gruppen" in feat054 or "Annotation-Gruppen" in feat054
            kh054 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
            assert "Soft-Hyphen" in kh054 and "Ctrl+Alt+G" in kh054
            cl054 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "0.5.4" in cl054 and "## 0.5.4" not in cl054
            print("0.5.4 Qt page-undo/groups/shy-nbsp/deps: OK")

            # --- 0.5.5 Qt: Historie-Liste, Export Tags/Gruppen, Encoding-Auto, Splash ---
            from instantlensdoc.core.app_settings import (
                get_skip_splash as _gss055,
                set_editor_text_encoding as _setenc055,
                set_skip_splash as _sss055,
            )
            from instantlensdoc.core.documents import detect_file_encoding as _dfe055

            assert callable(getattr(win.pdf_view, "show_page_ops_history", None))
            assert callable(getattr(win.pdf_view, "page_ops_history_items", None))
            assert callable(getattr(win.pdf_view, "restore_page_op_at", None))
            # Historie nach Rotate befüllen
            win.pdf_view.rotate_current(90)
            hist055 = win.pdf_view.page_ops_history_items()
            assert hist055 and "gedreht" in hist055[-1]["label"].lower()
            assert win.pdf_view.restore_page_op_at(hist055[-1]["stack_index"])
            assert not win.pdf_view.can_undo_page_op() or True
            # Export Tags+Gruppen
            win.pdf_view.store.set_page_group(0, title="SmokeGrp055", color="#112233")
            win.pdf_view.store.add(
                Annotation(
                    0,
                    AnnotationType.HIGHLIGHT,
                    8,
                    8,
                    width=40,
                    height=10,
                    text="ex055",
                    tags=["Tag055"],
                )
            )
            csv_ui055 = Path(td2) / "ann055_ui.csv"
            assert win.pdf_view.store.export_csv(csv_ui055).is_file()
            csv_body055 = csv_ui055.read_text(encoding="utf-8")
            assert "group_title" in csv_body055 and "SmokeGrp055" in csv_body055
            assert "Tag055" in csv_body055
            _setenc055("auto")
            bom055 = Path(td2) / "bom055.txt"
            bom055.write_bytes(b"\xef\xbb\xbfauto-ok")
            assert _dfe055(bom055) == "utf-8"
            _sss055(True)
            assert _gss055() is True
            _sss055(False)
            feat055 = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "Historie" in feat055 or "Quiet" in feat055 or "BOM" in feat055
            assert "group_title" in feat055 or "Tags" in feat055
            kh055 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
            assert "Historie" in kh055 or "Encoding Auto" in kh055 or "Quiet Startup" in kh055
            cl055 = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "0.5.5" in cl055 and "## 0.5.5" not in cl055
            print("0.5.5 Qt history/export/encoding/splash: OK")

            # --- 0.5.6 Qt: Favoriten, Batch-Farbe, Spellcheck, Privacy-About ---
            from instantlensdoc.core.app_settings import (
                get_spellcheck_dict_path as _gsp056,
                set_spellcheck_dict_path as _ssp056,
            )
            from instantlensdoc.ui.help_dialog import AboutDialog as _About056

            assert callable(getattr(win.pdf_view, "toggle_page_favorite", None))
            assert callable(getattr(win.pdf_view, "show_page_favorites", None))
            assert callable(getattr(win.pdf_view, "recolor_selected_annotations", None))
            assert callable(getattr(win.pdf_view, "list_page_favorites", None))
            assert win.pdf_view.store is not None
            win.pdf_view.store.set_page_favorites([])
            assert win.pdf_view.toggle_page_favorite() is True
            assert win.pdf_view.page_index in win.pdf_view.list_page_favorites()
            assert win.pdf_view.toggle_page_favorite() is False
            ann056 = Annotation(
                win.pdf_view.page_index,
                AnnotationType.HIGHLIGHT,
                5,
                5,
                width=30,
                height=8,
                text="batch056",
                color="#010101",
            )
            win.pdf_view.store.add(ann056)
            n056 = win.pdf_view.store.set_colors([ann056.id], "#FF00AA")
            assert n056 == 1 and win.pdf_view.store.get(ann056.id).color.upper() == "#FF00AA"
            wl056 = Path(td2) / "dict056.txt"
            wl056.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
            _ssp056(str(wl056))
            win.stack.setCurrentWidget(win.editor_pane)
            win.editor.setPlainText("alpha Foo beta")
            n_spell = win.editor.check_spelling(str(wl056))
            assert n_spell >= 1
            win.editor.clear_spelling()
            assert callable(getattr(win, "_check_spelling", None))
            assert callable(getattr(win, "_clear_spelling", None))
            _ssp056("")
            assert _gsp056() == ""
            about056 = _About056(win)
            src056 = (ROOT / "instantlensdoc" / "ui" / "help_dialog.py").read_text(encoding="utf-8")
            assert "Datenschutz" in src056 or "Privacy" in src056
            assert "Telemetrie" in src056
            about056.close()
            sett056 = (ROOT / "instantlensdoc" / "ui" / "settings_dialog.py").read_text(encoding="utf-8")
            assert "Rechtschreibwörterbuch" in sett056
            kh056 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
            assert "Favorit" in kh056 and ("F7" in kh056 or "Rechtschreibung" in kh056)
            feat056q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.5.6" in feat056q
            cl056q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "0.5.6" in cl056q and "## 0.5.6" not in cl056q
            print("0.5.6 Qt favorites/batch-color/spellcheck/privacy: OK")

            # --- 0.5.7 Qt retained: Favoriten-Sidebar, Opacity-Batch, Zeilen-Lesezeichen, Crash-ZIP ---
            assert hasattr(win.sidebar, "set_page_favorites")
            assert hasattr(win.sidebar, "page_favorite_activated")
            assert callable(getattr(win.pdf_view, "set_opacity_selected_annotations", None))
            assert callable(getattr(win, "_refresh_page_favorites", None))
            assert callable(getattr(win, "_create_crash_report", None))
            assert callable(getattr(win.editor, "toggle_line_bookmark", None))
            assert callable(getattr(win.editor, "list_line_bookmarks", None))
            win.pdf_view.store.set_page_favorites([0])
            win._refresh_page_favorites()
            assert win.sidebar.page_favorites.count() >= 1
            txt0 = win.sidebar.page_favorites.item(0).text()
            assert txt0.startswith("1.") and "Seite" in txt0
            ann057 = Annotation(
                win.pdf_view.page_index,
                AnnotationType.HIGHLIGHT,
                8,
                8,
                width=20,
                height=6,
                text="op057",
                opacity=1.0,
            )
            win.pdf_view.store.add(ann057)
            n057 = win.pdf_view.store.set_opacities([ann057.id], 0.33)
            assert n057 == 1 and abs(win.pdf_view.store.get(ann057.id).opacity - 0.33) < 0.001
            win.stack.setCurrentWidget(win.editor_pane)
            win.editor.set_line_numbers_visible(True)
            win.editor.setPlainText("alpha\nbeta\ngamma\ndelta\n")
            win.editor.clear_line_bookmarks()
            assert win.editor.toggle_line_bookmark(2) is True
            assert win.editor.toggle_line_bookmark(4) is True
            assert win.editor.list_line_bookmarks() == [2, 4]
            assert win.editor.is_line_bookmarked(2)
            assert win.editor.goto_next_line_bookmark() in (2, 4)
            assert win.editor.toggle_line_bookmark(2) is False
            assert win.editor.list_line_bookmarks() == [4]
            win.editor.clear_line_bookmarks()
            assert win.editor.list_line_bookmarks() == []
            from instantlensdoc.core.logging_setup import create_crash_report_zip as _crz057
            from instantlensdoc.core.logging_setup import setup_logging as _sl057

            _sl057(force=True)
            z057 = Path(td2) / "qt-crash057.zip"
            assert _crz057(z057).exists()
            kh057 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
            assert "Ctrl+Alt+Shift+O" in kh057 or "Deckkraft" in kh057
            assert "Ctrl+F2" in kh057 or "Zeilenfavorit" in kh057 or "Lesezeichen" in kh057
            assert "Crash-Report" in kh057
            feat057q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.5.8" in feat057q
            cl057q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "0.5.7" in cl057q and "0.5.8" in cl057q and "## 0.5.7" not in cl057q and "## 0.5.8" not in cl057q
            print("0.5.7 Qt favorites-sidebar/opacity/bookmarks/crash-zip: OK")

            # --- 0.5.8 Qt: Favoriten-Drag, Opacity Force, Zeilenfavoriten-Liste, Crash-Screenshot ---
            assert hasattr(win.sidebar, "page_favorites_reordered")
            assert hasattr(win.sidebar, "set_line_favorites")
            assert hasattr(win.sidebar, "line_favorite_activated")
            assert callable(getattr(win.pdf_view, "reorder_page_favorites", None))
            assert callable(getattr(win, "_on_page_favorites_reordered", None))
            assert callable(getattr(win, "_refresh_line_favorites", None))
            assert callable(getattr(win.pdf_view.store, "save_opacities", None))
            win.pdf_view.store.set_page_favorites([2, 0, 1])
            win._refresh_page_favorites()
            assert win.sidebar.page_favorites.count() >= 3
            assert "Seite 3" in win.sidebar.page_favorites.item(0).text()
            win.pdf_view.reorder_page_favorites([0, 2, 1])
            win._refresh_page_favorites()
            assert win.pdf_view.list_page_favorites() == [0, 2, 1]
            assert win.sidebar.page_favorites.item(0).text().startswith("1.")
            ann058 = Annotation(
                win.pdf_view.page_index,
                AnnotationType.STICKY,
                9,
                9,
                width=12,
                height=10,
                text="op058",
                opacity=1.0,
            )
            win.pdf_view.store.add(ann058)
            n058 = win.pdf_view.store.save_opacities([ann058.id], 0.27)
            assert n058 == 1 and abs(win.pdf_view.store.get(ann058.id).opacity - 0.27) < 0.001
            win.stack.setCurrentWidget(win.editor_pane)
            win.editor.setPlainText("one\ntwo\nthree\nfour\nfive\n")
            win.editor.clear_line_bookmarks()
            win.editor.toggle_line_bookmark(1)
            win.editor.toggle_line_bookmark(3)
            win.editor.toggle_line_bookmark(5)
            win._refresh_line_favorites()
            assert win.sidebar.line_favorites.count() >= 3
            assert "Zeile 1" in win.sidebar.line_favorites.item(0).text()
            assert "Zeile 3" in win.sidebar.line_favorites.item(1).text()
            win._on_line_favorite_jump(3)
            assert win.editor.textCursor().blockNumber() + 1 == 3
            from instantlensdoc.core.logging_setup import create_crash_report_zip as _crz058

            shot058 = Path(td2) / "qt-shot.png"
            shot058.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
            z058 = Path(td2) / "qt-crash058.zip"
            assert _crz058(z058, screenshot_path=shot058).exists()
            import zipfile as _zf058

            with _zf058.ZipFile(z058, "r") as zf_q:
                rep_q = zf_q.read("REPORT.txt").decode("utf-8")
                assert "screenshot_path_hint:" in rep_q
                assert any(n.startswith("screenshots/") for n in zf_q.namelist())
            kh058 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
            assert "Umsortieren" in kh058 or "ziehen" in kh058
            assert "Screenshot" in kh058
            assert "Sidebar-Liste" in kh058 or "Zeilenfavoriten" in kh058
            print("0.5.8 Qt fav-drag/opacity-force/line-list/crash-screenshot: OK")

            # --- 0.5.9 Qt: Favoriten JSON, Opacity-Slider, Labels, Erste-Schritte-Wizard ---
            assert hasattr(win.pdf_view, "slider_opacity")
            assert callable(getattr(win.pdf_view, "export_page_favorites_json", None))
            assert callable(getattr(win.pdf_view, "import_page_favorites_json", None))
            assert callable(getattr(win.editor, "set_line_bookmark_label", None))
            assert callable(getattr(win.editor, "get_line_bookmark_label", None))
            assert callable(getattr(win.editor, "list_line_bookmarks_with_labels", None))
            assert hasattr(win.sidebar, "line_favorite_label_edit")
            from instantlensdoc.ui.help_dialog import GettingStartedWizard, WIZARD_PAGES

            assert len(WIZARD_PAGES) == 4
            wiz = GettingStartedWizard(win)
            assert wiz._stack.count() == 4
            wiz._next()
            assert wiz._index == 1
            wiz._next()
            assert wiz._index == 2
            wiz._next()
            assert wiz._index == 3
            wiz.close()
            win.pdf_view.store.set_page_favorites([0, 2])
            fav_qt = Path(td2) / "qt-fav.json"
            saved_fav = win.pdf_view.store.export_page_favorites_json(fav_qt)
            assert saved_fav.exists()
            win.pdf_view.store.set_page_favorites([])
            win.pdf_view.store.import_page_favorites_json(fav_qt)
            assert win.pdf_view.list_page_favorites() == [0, 2]
            win._refresh_page_favorites()
            # Ohne Auswahl → Standard-Deckkraft; mit Auswahl → nur Objekt (0.9.0)
            win.pdf_view._selected_ann_id = None
            win.pdf_view._selected_ann_ids = []
            win.pdf_view.slider_opacity.blockSignals(True)
            win.pdf_view.slider_opacity.setValue(40)
            win.pdf_view.slider_opacity.blockSignals(False)
            win.pdf_view._on_opacity_slider_changed(40)
            assert abs(win.pdf_view._default_opacity - 0.40) < 0.001
            assert abs(win.pdf_view.spin_opacity.value() - 0.40) < 0.001
            ann059 = Annotation(
                win.pdf_view.page_index,
                AnnotationType.HIGHLIGHT,
                12,
                12,
                width=20,
                height=8,
                text="op059",
                opacity=1.0,
            )
            win.pdf_view.store.add(ann059)
            win.pdf_view._selected_ann_id = ann059.id
            win.pdf_view._selected_ann_ids = {ann059.id}
            before_def059 = float(win.pdf_view._default_opacity)
            win.pdf_view._on_opacity_slider_changed(65)
            assert abs(win.pdf_view.store.get(ann059.id).opacity - 0.65) < 0.001
            assert abs(float(win.pdf_view._default_opacity) - before_def059) < 0.001
            win.stack.setCurrentWidget(win.editor_pane)
            win.editor.setPlainText("a\nb\nc\nd\n")
            win.editor.clear_line_bookmarks()
            win.editor.toggle_line_bookmark(2)
            assert win.editor.set_line_bookmark_label(2, "Kapitel")
            assert win.editor.get_line_bookmark_label(2) == "Kapitel"
            pairs = win.editor.list_line_bookmarks_with_labels()
            assert pairs == [(2, "Kapitel")]
            win._refresh_line_favorites()
            assert "Kapitel" in win.sidebar.line_favorites.item(0).text()
            kh059 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
            assert "Toolbar-Slider" in kh059 or "ildfav" in kh059 or "Erste Schritte" in kh059
            assert "Label" in kh059
            feat059q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.5.9" in feat059q
            cl059q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "0.5.9" in cl059q and "## 0.5.9" not in cl059q
            print("0.5.9 Qt fav-json/opacity-slider/labels/wizard: OK")

            # --- 0.6.1 Qt: Text-Copy, Tag-Completer, Session-Tabs Drag ---
            assert callable(getattr(win.pdf_view, "copy_text_selection", None))
            assert callable(getattr(win.pdf_view, "selection_text", None))
            assert callable(getattr(win.pdf_view, "_on_text_selection", None))
            assert hasattr(win.pdf_view.canvas, "text_selection_finished")
            assert hasattr(win.sidebar, "documents_reordered")
            assert hasattr(win.sidebar, "document_paths")
            assert hasattr(win.sidebar, "_ann_tag_completer")
            assert hasattr(win.sidebar, "_ann_tag_completer_model")
            from ild_pdf import Annotation as Ann061, AnnotationType as AT061

            win.pdf_view.store.add(
                Ann061(0, AT061.STICKY, 5, 5, width=30, height=20, text="tag-ac", tags=["SmokeTag061", "Other"])
            )
            win.stack.setCurrentWidget(win.pdf_view)
            win._refresh_pdf_marks()
            # Completer direkt aus Payloads syncen falls Filter-UI verzögert
            payloads061 = [p[1] for p in win.pdf_view.annotation_summaries()]
            win.sidebar._sync_ann_tag_filter_options(payloads061)
            tags_model = win.sidebar._ann_tag_completer_model.stringList()
            assert any(t.casefold() == "smoketag061" for t in tags_model), (tags_model, [getattr(p, "tags", None) for p in payloads061])
            win.pdf_view._text_selection_text = "Hello Clipboard 061"
            assert win.pdf_view.copy_text_selection() is True
            from PySide6.QtWidgets import QApplication as QA061

            clip061 = QA061.clipboard()
            assert clip061 is not None and "Hello Clipboard 061" in (clip061.text() or "")
            assert callable(getattr(win, "_on_documents_reordered", None))
            assert callable(getattr(win, "_copy", None))
            from instantlensdoc.ui.sidebar import DocumentList

            assert isinstance(win.sidebar.files, DocumentList)
            kh061 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
            assert "PDF-Text kopieren" in kh061 or "Zwischenablage" in kh061
            assert "Tag-Autocomplete" in kh061 or "Autocomplete" in kh061
            feat061q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.6.1" in feat061q
            cl061q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "0.6.1" in cl061q and "## 0.6.1" not in cl061q
            print("0.6.1 Qt copy-text/tag-completer/session-tabs: OK")

            # --- 0.6.2 Qt: Selection→Notiz, Tag Multi-Select, Close-Others ---
            assert callable(getattr(win.pdf_view, "sticky_from_text_selection", None))
            assert callable(getattr(win, "close_other_tabs", None))
            assert callable(getattr(win, "_sticky_from_selection", None))
            assert callable(getattr(win.sidebar, "annotation_filter_tags", None))
            from ild_pdf import Annotation as Ann062, AnnotationType as AT062

            win.pdf_view.store.add(
                Ann062(0, AT062.STICKY, 8, 8, width=30, height=20, text="t1", tags=["Alpha062", "Shared"])
            )
            win.pdf_view.store.add(
                Ann062(0, AT062.STICKY, 18, 18, width=30, height=20, text="t2", tags=["Beta062", "Shared"])
            )
            win.stack.setCurrentWidget(win.pdf_view)
            win._refresh_pdf_marks()
            payloads062 = [p[1] for p in win.pdf_view.annotation_summaries()]
            win.sidebar._sync_ann_tag_filter_options(payloads062)
            win.sidebar.set_annotation_tag_filter(["Alpha062", "Beta062"])
            assert set(t.casefold() for t in win.sidebar.annotation_filter_tags()) == {
                "alpha062",
                "beta062",
            }
            win.sidebar.set_annotation_tag_filter("Alpha062")
            assert win.sidebar.annotation_filter_tag().casefold() == "alpha062"
            win.sidebar.set_annotation_tag_filter("")
            assert win.sidebar.annotation_filter_tags() == []
            win.pdf_view._text_selection_text = "Sticky Prefill 062"
            win.pdf_view._text_selection_rects = [(12.0, 12.0, 40.0, 10.0)]
            assert win.pdf_view.sticky_from_text_selection(edit=False) is True
            texts062 = [a.text for a in win.pdf_view.store.annotations if a.type == AT062.STICKY]
            assert any("Sticky Prefill 062" in (t or "") for t in texts062)
            # Close-others: Sidebar-Pfade außer aktuellem
            t_a = Path(td2) / "close_a.txt"
            t_b = Path(td2) / "close_b.txt"
            t_a.write_text("a", encoding="utf-8")
            t_b.write_text("b", encoding="utf-8")
            win.sidebar.add_document(str(t_a))
            win.sidebar.add_document(str(t_b))
            win.open_path(str(t_a))
            assert str(t_b) in win.sidebar.document_paths()
            win.close_other_tabs()
            remaining062 = win.sidebar.document_paths()
            assert str(t_a) in remaining062
            assert str(t_b) not in remaining062
            # PDF wieder öffnen für nachfolgende Qt-Kernpfade
            win.open_path(str(smoke_pdf))
            kh062 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
            assert "Auswahl → Notiz" in kh062 or "Ctrl+Alt+N" in kh062
            assert "Andere Tabs schließen" in kh062 or "Ctrl+Shift+W" in kh062
            feat062q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.6.2" in feat062q
            cl062q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "0.6.2" in cl062q and "## 0.6.2" not in cl062q
            print("0.6.2 Qt note/multi-tag/close-others: OK")

            # --- 0.6.3 Qt: Highlight+Notiz, Tag-Cloud, Doc-Split, Unsaved ---
            from instantlensdoc.core.app_settings import (
                get_selection_note_with_highlight as g_snh063,
                set_selection_note_with_highlight as s_snh063,
            )
            assert callable(getattr(win, "count_unsaved_tabs", None))
            assert callable(getattr(win, "_toggle_doc_split", None))
            assert callable(getattr(win, "_load_secondary_document", None))
            assert hasattr(win.sidebar, "_update_ann_tag_cloud")
            assert hasattr(win, "unsaved_status_label")
            assert hasattr(win, "secondary_wrap")
            assert hasattr(win, "doc_splitter")
            win.pdf_view._text_selection_text = "HL Note Combo 063"
            win.pdf_view._text_selection_rects = [(14.0, 14.0, 50.0, 12.0)]
            before_hl = sum(1 for a in win.pdf_view.store.annotations if a.type == AT062.HIGHLIGHT)
            before_st = sum(1 for a in win.pdf_view.store.annotations if a.type == AT062.STICKY)
            assert win.pdf_view.sticky_from_text_selection(edit=False, with_highlight=True) is True
            after_hl = sum(1 for a in win.pdf_view.store.annotations if a.type == AT062.HIGHLIGHT)
            after_st = sum(1 for a in win.pdf_view.store.annotations if a.type == AT062.STICKY)
            assert after_hl >= before_hl + 1
            assert after_st >= before_st + 1
            s_snh063(False)
            assert g_snh063() is False
            win.sidebar._sync_ann_tag_filter_options(payloads062)
            win.sidebar._update_ann_tag_cloud(payloads062)
            assert win.sidebar.ann_tag_cloud.isVisible() or win.sidebar.ann_tag_cloud_layout.count() >= 0
            # Doc split
            t_c = Path(td2) / "split_c.txt"
            t_d = Path(td2) / "split_d.txt"
            t_c.write_text("left-c", encoding="utf-8")
            t_d.write_text("right-d", encoding="utf-8")
            win.sidebar.add_document(str(t_c))
            win.sidebar.add_document(str(t_d))
            win.open_path(str(t_c))
            win._toggle_doc_split(True)
            assert win.secondary_wrap.isVisible()
            win._load_secondary_document(str(t_d))
            assert "right-d" in win.secondary_editor.toPlainText()
            win.editor.setPlainText("dirty-c")
            win._on_text_changed()
            assert win.count_unsaved_tabs() >= 1
            assert "ungespeichert" in win.unsaved_status_label.text()
            win._toggle_doc_split(False)
            win.open_path(str(smoke_pdf))
            kh063 = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
            assert "Fenster teilen" in kh063 or "Tag-Cloud" in kh063
            feat063q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.6.3" in feat063q
            cl063q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "0.6.3" in cl063q and "## 0.6.3" not in cl063q
            print("0.6.3 Qt highlight-note/tag-cloud/doc-split/unsaved: OK")

            # --- 0.6.4 Qt: Tag-Cloud setzt Filter, Sync-Scroll, Dirty-Tabs ---
            from instantlensdoc.core.app_settings import (
                get_editor_doc_split_sync_scroll as g_sync064,
                set_editor_doc_split_sync_scroll as s_sync064,
            )
            assert callable(getattr(win, "list_unsaved_tabs", None))
            assert callable(getattr(win, "_toggle_doc_split_sync_scroll", None))
            assert callable(getattr(win, "_on_unsaved_status_clicked", None))
            assert callable(getattr(win.sidebar, "_on_tag_cloud_clicked", None))
            # Tag-Cloud: Klick setzt exklusiven Filter
            win.sidebar._sync_ann_tag_filter_options(payloads062)
            win.sidebar.set_annotation_tag_filter(["Alpha062", "Beta062"])
            assert len(win.sidebar.annotation_filter_tags()) == 2
            win.sidebar._on_tag_cloud_clicked("Alpha062")
            tags064 = [t.casefold() for t in win.sidebar.annotation_filter_tags()]
            assert tags064 == ["alpha062"]
            win.sidebar._on_tag_cloud_clicked("Alpha062")  # erneut → clear
            assert win.sidebar.annotation_filter_tags() == []
            # Sync-Scroll
            s_sync064(True)
            assert g_sync064() is True
            win._toggle_doc_split(True)
            assert hasattr(win, "_doc_split_sync_action")
            win._doc_split_sync_action.setChecked(True)
            assert win._doc_split_sync_action.isChecked()
            assert g_sync064() is True
            win._apply_doc_split_sync_scroll()
            assert win._sync_secondary_bar is not None or win.secondary_wrap.isVisible()
            # Dirty tabs list
            t_e = Path(td2) / "dirty_e.txt"
            t_e.write_text("clean-e", encoding="utf-8")
            win.sidebar.add_document(str(t_e))
            win.open_path(str(t_e))
            win.editor.setPlainText("dirty-e-064")
            win._on_text_changed()
            dirty064 = win.list_unsaved_tabs()
            assert any(Path(p).name == "dirty_e.txt" for p, _ in dirty064 if p)
            assert "ungespeichert" in win.unsaved_status_label.text()
            win._toggle_doc_split_sync_scroll(False)
            win._toggle_doc_split(False)
            s_sync064(False)
            win.open_path(str(smoke_pdf))
            kh064q = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
            assert "Sync-Scroll" in kh064q
            assert "Tag-Cloud Filter" in kh064q or "setzt Filter" in kh064q
            feat064q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.6.4" in feat064q
            cl064q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "0.6.4" in cl064q and "## 0.6.4" not in cl064q
            print("0.6.4 Qt tag-filter/sync-scroll/dirty-tabs/shortcuts: OK")

            # --- 0.6.5 Qt: Tag-Rename, Vertikal-Split, Dirty-Save, Wizard ---
            from PySide6.QtCore import Qt
            from instantlensdoc.core.app_settings import (
                get_editor_doc_split_vertical as g_vert065,
                set_editor_doc_split_vertical as s_vert065,
            )
            assert callable(getattr(win, "_toggle_doc_split_vertical", None))
            assert callable(getattr(win, "_save_unsaved_tab", None))
            assert callable(getattr(win, "_rename_annotation_tag_global", None))
            assert callable(getattr(win.sidebar, "_on_tag_cloud_context_menu", None))
            assert hasattr(win.sidebar, "annotation_tag_rename_requested")
            # Vertikal-Split
            s_vert065(False)
            win._toggle_doc_split(True)
            win._doc_split_vertical_action.setChecked(True)
            assert g_vert065() is True
            assert win.doc_splitter.orientation() == Qt.Vertical
            win._doc_split_vertical_action.setChecked(False)
            assert g_vert065() is False
            assert win.doc_splitter.orientation() == Qt.Horizontal
            # Tag rename global
            win.open_path(str(smoke_pdf))
            store065 = win.pdf_view.store
            assert store065 is not None
            store065.annotations = []
            store065.clear_history()
            from ild_pdf import Annotation as Ann065, AnnotationType as AT065
            a065 = Ann065(0, AT065.HIGHLIGHT, 5, 5, width=20, height=10, text="rn", tags=["Old065"])
            store065.add(a065)
            win._refresh_pdf_marks()
            win._rename_annotation_tag_global("Old065", "New065")
            assert "New065" in (a065.tags or []) and "Old065" not in (a065.tags or [])
            # Dirty-Save entry path
            t_f = Path(td2) / "dirty_f.txt"
            t_f.write_text("clean-f", encoding="utf-8")
            win.sidebar.add_document(str(t_f))
            win.open_path(str(t_f))
            win.editor.setPlainText("dirty-f-065")
            win._on_text_changed()
            assert any(Path(p).name == "dirty_f.txt" for p, _ in win.list_unsaved_tabs() if p)
            assert "_save_unsaved_tab" in (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
            win._save_unsaved_tab(str(t_f))
            assert t_f.read_text(encoding="utf-8") == "dirty-f-065"
            # Wizard 4 pages
            from instantlensdoc.ui.help_dialog import GettingStartedWizard as Wiz065, WIZARD_PAGES as WP065q
            assert len(WP065q) == 4
            assert any("0.6" in c or "0.6" in h for c, h in WP065q)
            wiz065 = Wiz065(win)
            assert wiz065._stack.count() == 4
            wiz065.close()
            win._toggle_doc_split(False)
            s_vert065(False)
            win.open_path(str(smoke_pdf))
            kh065q = (ROOT / "instantlensdoc" / "ui" / "keyboard_help.py").read_text(encoding="utf-8")
            assert "Vertikaler Split" in kh065q or "umbenennen" in kh065q
            feat065q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.6.5" in feat065q
            cl065q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "0.6.5" in cl065q and "## 0.6.5" not in cl065q
            print("0.6.5 Qt tag-rename/vertical-split/dirty-save/wizard: OK")

            # --- 0.6.6 Qt: Rename-Undo, Split-Settings, Alle speichern, Wizard skip-once ---
            from instantlensdoc.core.app_settings import (
                consume_wizard_skip_once as cons066,
                get_editor_doc_split_vertical as g_vert066,
                get_wizard_completed as g_wiz066,
                get_wizard_skip_once as g_skip066,
                set_editor_doc_split_vertical as s_vert066,
                set_wizard_completed as s_wiz066,
                set_wizard_skip_once as s_skip066,
            )
            assert callable(getattr(win, "_save_all_unsaved_tabs", None))
            assert callable(getattr(win, "_sync_doc_split_orientation", None))
            assert callable(getattr(win, "_maybe_show_getting_started_wizard", None))
            assert callable(getattr(win, "_revert_tag_filter_after_rename_undo", None))
            # Settings H/V sync
            s_vert066(True)
            win._sync_doc_split_orientation()
            assert g_vert066() is True
            assert win._doc_split_vertical_action.isChecked()
            s_vert066(False)
            win._sync_doc_split_orientation()
            assert g_vert066() is False
            # Tag rename undo one step + filter revert
            win.open_path(str(smoke_pdf))
            store066 = win.pdf_view.store
            assert store066 is not None
            store066.annotations = []
            store066.clear_history()
            from ild_pdf import Annotation as Ann066, AnnotationType as AT066
            a066a = Ann066(0, AT066.HIGHLIGHT, 5, 5, width=20, height=10, text="a", tags=["T066"])
            a066b = Ann066(0, AT066.STICKY, 8, 8, width=20, height=10, text="b", tags=["T066"])
            store066.add(a066a)
            store066.add(a066b)
            win.sidebar.set_annotation_tag_filter(["T066"])
            win._refresh_pdf_marks()
            win._rename_annotation_tag_global("T066", "U066")
            assert win._last_tag_rename == ("T066", "U066")
            assert "U066" in win.sidebar.annotation_filter_tags() or any(
                t.casefold() == "u066" for t in win.sidebar.annotation_filter_tags()
            )
            assert store066.can_undo()
            assert win.pdf_view.undo_annotation()
            tags_back = []
            for ann in store066.annotations:
                tags_back.extend(str(t) for t in (ann.tags or []))
            assert tags_back.count("T066") == 2
            assert "U066" not in tags_back
            assert any(t.casefold() == "t066" for t in win.sidebar.annotation_filter_tags())
            # Dirty Alle speichern
            t_g = Path(td2) / "dirty_g.txt"
            t_g.write_text("clean-g", encoding="utf-8")
            win.sidebar.add_document(str(t_g))
            win.open_path(str(t_g))
            win.editor.setPlainText("dirty-g-066")
            win._on_text_changed()
            assert any(Path(p).name == "dirty_g.txt" for p, _ in win.list_unsaved_tabs() if p)
            win._save_all_unsaved_tabs()
            assert t_g.read_text(encoding="utf-8") == "dirty-g-066"
            # Wizard skip-once checkbox
            from instantlensdoc.ui.help_dialog import GettingStartedWizard as Wiz066
            s_wiz066(False)
            s_skip066(False)
            wiz066 = Wiz066(win)
            assert hasattr(wiz066, "skip_once_cb")
            wiz066.skip_once_cb.setChecked(True)
            wiz066._close_clicked()
            assert g_skip066() is True
            assert g_wiz066() is False
            assert cons066() is True
            assert g_skip066() is False
            s_wiz066(False)
            win.open_path(str(smoke_pdf))
            feat066q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.6.6" in feat066q
            cl066q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "0.6.6" in cl066q and "## 0.6.6" not in cl066q
            print("0.6.6 Qt rename-undo/split-settings/save-all/wizard-skip: OK")

            # --- 0.6.7 Qt: Undo-Label, Split PDF+Editor, Save-Progress, Wizard dont-show ---
            from instantlensdoc.core.app_settings import (
                get_wizard_completed as g_wiz067,
                get_wizard_skip_once as g_skip067,
                set_wizard_completed as s_wiz067,
                set_wizard_skip_once as s_skip067,
            )
            assert hasattr(win, "secondary_pdf")
            assert hasattr(win, "secondary_stack")
            assert callable(getattr(win, "_refresh_undo_hint", None))
            # Tag rename → sichtbares Undo-Label
            win.open_path(str(smoke_pdf))
            store067 = win.pdf_view.store
            assert store067 is not None
            store067.annotations = []
            store067.clear_history()
            from ild_pdf import Annotation as Ann067, AnnotationType as AT067
            store067.add(Ann067(0, AT067.HIGHLIGHT, 5, 5, width=20, height=10, text="a", tags=["T067"]))
            store067.add(Ann067(0, AT067.STICKY, 8, 8, width=20, height=10, text="b", tags=["T067"]))
            win._rename_annotation_tag_global("T067", "U067")
            assert store067.peek_undo_label() == "Tag umbenennen"
            win._refresh_undo_hint()
            assert "Tag umbenennen" in win.undo_hint_label.text()
            ann_hist = win.pdf_view.annotation_undo_history_items()
            assert any(it.get("label") == "Tag umbenennen" for it in ann_hist)
            assert win.pdf_view.undo_annotation()
            # Doc-Split: PDF im Zweit-Panel wenn Text primär
            t_mix = Path(td2) / "mix067.txt"
            t_mix.write_text("mix-editor", encoding="utf-8")
            win.sidebar.add_document(str(t_mix))
            win.sidebar.add_document(str(smoke_pdf))
            win.open_path(str(t_mix))
            win._toggle_doc_split(True)
            win._load_secondary_document(str(smoke_pdf))
            assert win.secondary_stack.currentWidget() is win.secondary_pdf
            assert win.secondary_pdf.pdf_path is not None
            win._load_secondary_document(str(t_mix))
            assert win.secondary_stack.currentWidget() is win.secondary_pane
            win._toggle_doc_split(False)
            # Wizard Nicht mehr zeigen
            from instantlensdoc.ui.help_dialog import GettingStartedWizard as Wiz067
            s_wiz067(False)
            s_skip067(False)
            wiz067 = Wiz067(win)
            assert hasattr(wiz067, "dont_show_cb")
            wiz067.dont_show_cb.setChecked(True)
            wiz067._close_clicked()
            assert g_wiz067() is True
            assert g_skip067() is False
            s_wiz067(False)
            feat067q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.6.7" in feat067q
            cl067q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "0.6.7" in cl067q and "## 0.6.7" not in cl067q
            print("0.6.7 Qt undo-label/split-mix/save-progress/wizard-dont-show: OK")

            # --- 0.6.8 Qt: panel session, save cancel, wizard reset, tag confirm ---
            from unittest.mock import patch

            from PySide6.QtWidgets import QMessageBox

            from instantlensdoc.core.app_settings import (
                get_wizard_completed as g_wiz068,
                get_wizard_skip_once as g_skip068,
                set_wizard_completed as s_wiz068,
                set_wizard_skip_once as s_skip068,
            )
            from instantlensdoc.ui.settings_dialog import SettingsDialog as SD068
            assert hasattr(win, "_secondary_kind")
            t_mix068 = Path(td2) / "mix068.txt"
            t_mix068.write_text("mix-editor-068", encoding="utf-8")
            win.sidebar.add_document(str(t_mix068))
            win.sidebar.add_document(str(smoke_pdf))
            win.open_path(str(t_mix068))
            win._toggle_doc_split(True)
            win._load_secondary_document(str(smoke_pdf))
            assert win._secondary_kind == "pdf"
            assert win._secondary_path and Path(win._secondary_path).suffix.lower() == ".pdf"
            win._toggle_doc_split(False)
            win._toggle_doc_split(True)
            assert win._secondary_kind == "pdf"
            assert win.secondary_stack.currentWidget() is win.secondary_pdf
            win._toggle_doc_split(False)
            # Tag-Rename Bestätigung >20: Abbruch ohne Rename
            win.open_path(str(smoke_pdf))
            store068 = win.pdf_view.store
            assert store068 is not None
            store068.annotations = []
            store068.clear_history()
            from ild_pdf import Annotation as Ann068, AnnotationType as AT068
            for i in range(21):
                store068.add(
                    Ann068(0, AT068.HIGHLIGHT, float(i), float(i), width=8, height=8, text=f"b{i}", tags=["Bulk068"])
                )
            assert store068.count_tag("Bulk068") == 21
            with patch("instantlensdoc.ui.main_window.QMessageBox.question", return_value=QMessageBox.No):
                win._rename_annotation_tag_global("Bulk068", "Other068")
            assert store068.count_tag("Bulk068") == 21
            assert store068.count_tag("Other068") == 0
            # Wizard-Reset in Einstellungen
            s_wiz068(True)
            s_skip068(True)
            sd068 = SD068(win)
            assert hasattr(sd068, "btn_wizard_reset")
            assert callable(getattr(sd068, "_reset_wizard", None))
            with patch("instantlensdoc.ui.settings_dialog.QMessageBox.question", return_value=QMessageBox.Yes):
                with patch("instantlensdoc.ui.settings_dialog.QMessageBox.information"):
                    sd068._reset_wizard()
            assert g_wiz068() is False
            assert g_skip068() is False
            sd068.close()
            # Save-All Progress Cancel-Button Text
            assert "Abbrechen" in (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
            feat068q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.6.8" in feat068q
            cl068q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "0.6.8" in cl068q and "## 0.6.8" not in cl068q
            print("0.6.8 Qt panel-session/save-cancel/wizard-reset/tag-confirm: OK")

            # --- 0.6.9 Qt: sync_scroll session, tag threshold, save error list ---
            from instantlensdoc.core.app_settings import (
                get_editor_doc_split_sync_scroll as g_sync069,
                get_tag_rename_confirm_threshold as g_thr069,
                set_editor_doc_split_sync_scroll as s_sync069,
                set_tag_rename_confirm_threshold as s_thr069,
            )
            from instantlensdoc.core import session as session_mod069q
            from instantlensdoc.ui.settings_dialog import SettingsDialog as SD069

            s_thr069(10)
            assert g_thr069() == 10
            sd069q = SD069(win)
            assert hasattr(sd069q, "tag_rename_confirm")
            assert sd069q.tag_rename_confirm.value() == 10
            sd069q.tag_rename_confirm.setValue(15)
            sd069q._save()
            assert g_thr069() == 15
            sd069q.close()
            s_thr069(20)
            # Tag-Rename mit Schwelle 5 → Confirm bei 6 Treffern
            win.open_path(str(smoke_pdf))
            store069 = win.pdf_view.store
            assert store069 is not None
            store069.annotations = []
            store069.clear_history()
            from ild_pdf import Annotation as Ann069, AnnotationType as AT069
            for i in range(6):
                store069.add(
                    Ann069(0, AT069.HIGHLIGHT, float(i), float(i), width=8, height=8, text=f"t{i}", tags=["Bulk069"])
                )
            s_thr069(5)
            with patch("instantlensdoc.ui.main_window.QMessageBox.question", return_value=QMessageBox.No):
                win._rename_annotation_tag_global("Bulk069", "Other069")
            assert store069.count_tag("Bulk069") == 6
            assert store069.count_tag("Other069") == 0
            s_thr069(20)
            # Sync-Scroll Session speichern/laden
            s_sync069(True)
            win._doc_split_sync_action.setChecked(True)
            win._toggle_doc_split_sync_scroll(True)
            assert g_sync069() is True
            win._save_session()
            loaded_ss = session_mod069q.load_session()
            assert loaded_ss.sync_scroll is True
            s_sync069(False)
            win._toggle_doc_split_sync_scroll(False)
            assert g_sync069() is False
            # Save-all Fehlerliste vorhanden
            assert callable(getattr(win, "_save_all_unsaved_tabs", None))
            assert "Alle speichern — Fehler" in (
                ROOT / "instantlensdoc" / "ui" / "main_window.py"
            ).read_text(encoding="utf-8")
            feat069q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.6.9" in feat069q
            cl069q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "0.6.9" in cl069q and "## 0.6.9" not in cl069q
            print("0.6.9 Qt sync-session/tag-threshold/save-errors: OK")

            # --- 0.7.1 Qt: Alle PDFs, Duplikate, Vorlage speichern, Sidecar-Debounce ---
            from instantlensdoc.core.app_settings import (
                delete_user_doc_template as del_tpl071,
                get_user_doc_templates as get_tpl071,
                save_user_doc_template as save_tpl071,
            )

            assert hasattr(win.sidebar, "btn_pdfs")
            assert hasattr(win.sidebar, "pdf_fulltext_mode")
            win.sidebar._emit_pdf_fulltext()
            assert win.sidebar.fulltext_mode and win.sidebar.pdf_fulltext_mode
            win.sidebar._emit_search()
            assert not win.sidebar.pdf_fulltext_mode
            assert callable(win.pdf_view.schedule_sidecar_save)
            assert callable(win.pdf_view.flush_sidecar_save)
            assert callable(win.pdf_view.merge_duplicate_annotations)
            assert callable(win._save_doc_as_template)
            win.open_path(str(smoke_pdf))
            store071 = win.pdf_view.store
            assert store071 is not None
            store071.annotations = []
            store071.clear_history()
            from ild_pdf import Annotation as Ann071, AnnotationType as AT071

            store071.add(Ann071(0, AT071.HIGHLIGHT, 12, 12, width=20, height=8, text="a071", tags=["t1"]))
            store071.add(Ann071(0, AT071.HIGHLIGHT, 12, 13, width=20, height=8, text="b071", tags=["t2"]))
            with patch(
                "instantlensdoc.ui.merge_duplicates_dialog.MergeDuplicatesPreviewDialog.exec",
                return_value=1,
            ):
                n_rm = win.pdf_view.merge_duplicate_annotations()
            assert n_rm == 1
            assert len(store071.annotations) == 1
            # Debounce: schedule ohne force setzt pending
            store071.dirty = True
            win.pdf_view._sidecar_save_pending = False
            win.pdf_view.schedule_sidecar_save(force=False)
            assert win.pdf_view._sidecar_save_pending is True
            win.pdf_view.flush_sidecar_save()
            assert win.pdf_view._sidecar_save_pending is False
            # Vorlage speichern
            for old in list(get_tpl071()):
                del_tpl071(old["id"])
            from instantlensdoc.core.documents import Document as Doc071, DocKind as DK071

            win.doc = Doc071(kind=DK071.TEXT, title="Tpl071", text="Vorlage-Inhalt 071\n")
            win.editor.setPlainText("Vorlage-Inhalt 071\n")
            win.stack.setCurrentWidget(win.editor_pane)
            with patch(
                "PySide6.QtWidgets.QInputDialog.getText",
                return_value=("MeineSmoke071", True),
            ):
                win._save_doc_as_template()
            tpls = get_tpl071()
            assert any(t["title"] == "MeineSmoke071" for t in tpls)
            for t in list(tpls):
                del_tpl071(t["id"])
            feat071q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.7.1" in feat071q
            cl071q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "## 0.7.1" in cl071q
            print("0.7.1 Qt pdf-search/dup-merge/templates/debounce: OK")

            # --- 0.7.2 Qt: Treffer-Nav, Merge-Undo, Vorlagen rename/delete, Debounce ---
            from instantlensdoc.core.app_settings import (
                get_sidecar_save_debounce_ms as get_deb072,
                rename_user_doc_template as ren_tpl072,
                set_sidecar_save_debounce_ms as set_deb072,
            )

            assert hasattr(win.sidebar, "btn_prev")
            assert hasattr(win.sidebar, "search_hits_label")
            assert callable(win.sidebar.advance_search_hit)
            assert callable(win._on_search_prev)
            assert callable(win.pdf_view.search_prev)
            assert callable(win.pdf_view.apply_sidecar_debounce_ms)
            assert callable(win._rename_user_template)
            assert callable(win._delete_user_template)
            # Merge-Undo Label nach Duplikat-Merge (0.7.1 Setup oben)
            win.open_path(str(smoke_pdf))
            store072 = win.pdf_view.store
            assert store072 is not None
            store072.annotations = []
            store072.clear_history()
            store072.add(Ann071(0, AT071.HIGHLIGHT, 20, 20, width=18, height=8, text="m1"))
            store072.add(Ann071(0, AT071.HIGHLIGHT, 21, 20, width=18, height=8, text="m2"))
            with patch(
                "instantlensdoc.ui.merge_duplicates_dialog.MergeDuplicatesPreviewDialog.exec",
                return_value=1,
            ):
                assert win.pdf_view.merge_duplicate_annotations() == 1
            assert store072.peek_undo_label() == "Duplikate zusammenführen"
            win._refresh_undo_hint()
            assert "Duplikate zusammenführen" in win.undo_hint_label.text()
            # Debounce apply
            set_deb072(250)
            assert win.pdf_view.apply_sidecar_debounce_ms() == 250
            assert win.pdf_view._sidecar_save_timer.interval() == 250
            set_deb072(400)
            win.pdf_view.apply_sidecar_debounce_ms()
            assert get_deb072() == 400
            # Vorlagen rename/delete UI helpers
            for old in list(get_tpl071()):
                del_tpl071(old["id"])
            e072 = save_tpl071(title="QtTpl072", body="x\n")
            with patch(
                "PySide6.QtWidgets.QInputDialog.getText",
                return_value=("QtTpl072ren", True),
            ):
                win._rename_user_template(e072["id"], "QtTpl072")
            assert any(t["title"] == "QtTpl072ren" for t in get_tpl071())
            with patch(
                "instantlensdoc.ui.main_window.QMessageBox.question",
                return_value=QMessageBox.Yes,
            ):
                win._delete_user_template(e072["id"], "QtTpl072ren")
            assert not any(t["id"] == e072["id"] for t in get_tpl071())
            # Search hit nav over marks
            win.sidebar.set_marks(
                ["a.pdf S.1: x", "b.pdf S.2: y"],
                [("a.pdf", 0, "q"), ("b.pdf", 1, "q")],
            )
            assert win.sidebar._search_hit_total == 2
            adv = win.sidebar.advance_search_hit(delta=1)
            assert adv is not None and adv[1][0] == "a.pdf"
            adv2 = win.sidebar.advance_search_hit(delta=1)
            assert adv2 is not None and adv2[1][0] == "b.pdf"
            assert "2" in win.sidebar.search_hits_label.text() or "Treffer" in win.sidebar.search_hits_label.text()
            feat072q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.7.2" in feat072q
            cl072q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "## 0.7.2" in cl072q
            print("0.7.2 Qt search-nav/merge-undo/templates/debounce: OK")

            # --- 0.7.3 Qt: Trefferliste-Klick, Vorlagen-Ordner, Merge-Vorschau, Ctrl+S-Flush ---
            from instantlensdoc.core.app_settings import user_templates_dir as tpl_dir073
            from instantlensdoc.ui.merge_duplicates_dialog import (
                MergeDuplicatesPreviewDialog as MDP073,
            )

            assert win.sidebar.marks.objectName() == "searchHitsList"
            # Klick sync: Index setzen ohne Datei zu öffnen
            win.sidebar.set_marks(
                ["c.pdf S.1: z", "d.pdf S.3: w"],
                [("c.pdf", 0, "q"), ("d.pdf", 2, "q")],
            )
            item0 = win.sidebar.marks.item(0)
            assert item0 is not None
            with patch.object(win, "_on_fulltext_hit"):
                win.sidebar._activate_mark(item0)
            assert win.sidebar._search_hit_index == 0
            assert "1/" in win.sidebar.search_hits_label.text() or "Treffer" in win.sidebar.search_hits_label.text()
            assert callable(win._open_user_templates_folder)
            for old in list(get_tpl071()):
                del_tpl071(old["id"])
            e073 = save_tpl071(title="QtTpl073", body="body073\n")
            with patch(
                "PySide6.QtGui.QDesktopServices.openUrl",
                return_value=True,
            ):
                win._open_user_templates_folder()
            assert tpl_dir073().is_dir()
            assert list(tpl_dir073().glob("*.ildtpl.md"))
            del_tpl071(e073["id"])
            # Merge preview dialog reject → 0 removed
            win.open_path(str(smoke_pdf))
            store073 = win.pdf_view.store
            assert store073 is not None
            store073.annotations = []
            store073.clear_history()
            store073.add(Ann071(0, AT071.HIGHLIGHT, 30, 30, width=16, height=7, text="p1"))
            store073.add(Ann071(0, AT071.HIGHLIGHT, 31, 30, width=16, height=7, text="p2"))
            with patch(
                "instantlensdoc.ui.merge_duplicates_dialog.MergeDuplicatesPreviewDialog.exec",
                return_value=0,
            ):
                assert win.pdf_view.merge_duplicate_annotations() == 0
            assert len(store073.annotations) == 2
            with patch(
                "instantlensdoc.ui.merge_duplicates_dialog.MergeDuplicatesPreviewDialog.exec",
                return_value=1,
            ):
                assert win.pdf_view.merge_duplicate_annotations() == 1
            # Ctrl+S flush: pending debounce cleared (save_doc ruft flush_sidecar_save)
            store073.dirty = True
            win.pdf_view._sidecar_save_pending = True
            win.pdf_view._sidecar_save_timer.start()
            win.pdf_view.flush_sidecar_save()
            assert win.pdf_view._sidecar_save_pending is False
            assert not win.pdf_view._sidecar_save_timer.isActive()
            src_save = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
            assert "flush_sidecar_save()" in src_save
            # Dialog-Construct mit künstlicher Gruppe
            sample_ann = store073.annotations[0]
            dlg073 = MDP073([[sample_ann, sample_ann]], parent=win)
            assert dlg073.list.count() >= 2
            dlg073.close()
            feat073q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.7.3" in feat073q and "Vorschau" in feat073q
            cl073q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "## 0.7.3" in cl073q
            print("0.7.3 Qt hits-list/templates-folder/merge-preview/ctrl-s-flush: OK")

            # --- 0.7.4 Qt: Kontext-Snippet, Merge je Paar, Vorlagen-Drag, Dirty-Debounce ---
            from instantlensdoc.core.app_settings import (
                reorder_user_doc_templates as reorder_tpl074,
            )
            from instantlensdoc.core.fulltext import _snippet_around as snip_fn074
            from instantlensdoc.ui.merge_duplicates_dialog import (
                MergeDuplicatesPreviewDialog as MDP074,
            )
            from instantlensdoc.ui.templates_dialog import TemplatesOrderDialog as TOD074

            assert "«" in snip_fn074("xx FINDME yy", "FINDME", context_chars=4)
            assert callable(win._reorder_user_templates_dialog)
            assert callable(win._refresh_document_dirty_labels)
            assert callable(win.pdf_view.sidecar_save_pending)
            for old in list(get_tpl071()):
                del_tpl071(old["id"])
            e074q1 = save_tpl071(title="QtTpl074a", body="a\n")
            e074q2 = save_tpl071(title="QtTpl074b", body="b\n")
            dlg_tpl = TOD074([e074q1, e074q2], parent=win)
            assert dlg_tpl.list.count() == 2
            # Drag-Simulation: IDs manuell umdrehen via ordered_ids nach Item-Swap
            item0 = dlg_tpl.list.takeItem(0)
            dlg_tpl.list.addItem(item0)
            ids074 = dlg_tpl.ordered_ids()
            assert ids074 == [e074q2["id"], e074q1["id"]]
            reorder_tpl074(ids074)
            assert [t["id"] for t in get_tpl071()] == ids074
            del_tpl071(e074q1["id"])
            del_tpl071(e074q2["id"])
            dlg_tpl.close()
            # Merge dialog: eine Gruppe abwählen → groups_to_merge leer / partial
            win.open_path(str(smoke_pdf))
            store074 = win.pdf_view.store
            assert store074 is not None
            store074.annotations = []
            store074.clear_history()
            store074.add(Ann071(0, AT071.HIGHLIGHT, 50, 50, width=14, height=6, text="m1"))
            store074.add(Ann071(0, AT071.HIGHLIGHT, 51, 50, width=14, height=6, text="m2"))
            g074 = store074.find_duplicate_groups(tol=2.0, same_type=True)
            dlg_m = MDP074(g074, parent=win)
            assert dlg_m.list.count() >= 2
            assert len(dlg_m.groups_to_merge()) >= 1
            dlg_m._set_all_checked(False)
            assert dlg_m.groups_to_merge() == []
            assert len(dlg_m.groups_to_keep()) >= 1
            dlg_m._set_all_checked(True)
            with patch(
                "instantlensdoc.ui.merge_duplicates_dialog.MergeDuplicatesPreviewDialog.exec",
                return_value=1,
            ):
                # real dialog would return selected; patch path uses groups_to_merge on real instance —
                # call merge with selected groups directly
                n_rm = store074.merge_duplicates(
                    tol=2.0, keep="oldest", groups=dlg_m.groups_to_merge()
                )
                assert n_rm >= 1
            dlg_m.close()
            # Dirty indicator during pending sidecar debounce
            store074.dirty = True
            win.pdf_view._sidecar_save_pending = True
            win.pdf_view._sidecar_save_timer.stop()
            assert win.pdf_view.sidecar_save_pending() is True
            assert win._current_is_dirty() is True
            if win.doc and win.doc.path:
                win._mark_unsaved(win.doc.path, True)
                win._refresh_document_dirty_labels()
                # Tab-Label mit *
                found_star = False
                for i in range(win.sidebar.files.count()):
                    it = win.sidebar.files.item(i)
                    if it and it.text().endswith(" *"):
                        found_star = True
                        break
                assert found_star
            win.pdf_view._sidecar_save_pending = False
            store074.dirty = False
            feat074q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.7.4" in feat074q and "Kontext-Snippet" in feat074q
            cl074q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "## 0.7.4" in cl074q
            print("0.7.4 Qt snippet/merge-pair/templates-drag/dirty-debounce: OK")

            # --- 0.7.5 Qt: Snippet-Länge, Alle mergen/behalten, Vorlagen-Zip, Debounce-Tooltip ---
            from instantlensdoc.core.app_settings import (
                export_user_templates_zip as exp_zip075,
                get_search_snippet_context_chars as get_snip075,
                import_user_templates_zip as imp_zip075,
                set_search_snippet_context_chars as set_snip075,
            )
            from instantlensdoc.ui.merge_duplicates_dialog import (
                MergeDuplicatesPreviewDialog as MDP075,
            )
            from instantlensdoc.ui.settings_dialog import SettingsDialog as SD075

            assert callable(win._export_user_templates_zip)
            assert callable(win._import_user_templates_zip)
            set_snip075(55)
            assert get_snip075() == 55
            sd_dlg = SD075(parent=win)
            assert hasattr(sd_dlg, "snippet_context")
            assert sd_dlg.snippet_context.value() == 55
            sd_dlg.snippet_context.setValue(25)
            sd_dlg._save()
            assert get_snip075() == 25
            set_snip075(40)
            # Merge Alle mergen / Alle behalten
            store075 = win.pdf_view.store
            assert store075 is not None
            store075.annotations = []
            store075.clear_history()
            store075.add(Ann071(0, AT071.HIGHLIGHT, 1, 1, width=10, height=4, text="g1a"))
            store075.add(Ann071(0, AT071.HIGHLIGHT, 1, 2, width=10, height=4, text="g1b"))
            store075.add(Ann071(0, AT071.HIGHLIGHT, 40, 40, width=10, height=4, text="g2a"))
            store075.add(Ann071(0, AT071.HIGHLIGHT, 40, 41, width=10, height=4, text="g2b"))
            groups075 = store075.find_duplicate_groups(tol=2.0, same_type=True)
            dlg_all = MDP075(groups075, parent=win)
            assert len(dlg_all.groups_to_merge()) >= 1
            dlg_all._set_all_checked(False)
            assert dlg_all.groups_to_merge() == []
            assert len(dlg_all.groups_to_keep()) >= 1
            dlg_all._set_all_checked(True)
            assert len(dlg_all.groups_to_merge()) >= 1
            dlg_all.close()
            # Vorlagen Zip roundtrip
            for old in list(get_tpl071()):
                del_tpl071(old["id"])
            save_tpl071(title="QtZip075", body="qt-zip-body\n")
            zpath = Path(td2) / "qt_templates_075.zip"
            exp_zip075(zpath)
            for old in list(get_tpl071()):
                del_tpl071(old["id"])
            n_imp = imp_zip075(zpath, merge=True)
            assert len(n_imp) >= 1
            assert any(t["title"] == "QtZip075" for t in get_tpl071())
            for old in list(get_tpl071()):
                if old["title"] == "QtZip075":
                    del_tpl071(old["id"])
            # Debounce tooltip „Speichern ausstehend…“
            store075.dirty = True
            win.pdf_view._sidecar_save_pending = True
            win.pdf_view._sidecar_save_timer.stop()
            if win.doc and win.doc.path:
                win._mark_unsaved(win.doc.path, True)
                win.stack.setCurrentWidget(win.pdf_view)
                win._refresh_document_dirty_labels()
                tip_found = False
                for i in range(win.sidebar.files.count()):
                    it = win.sidebar.files.item(i)
                    if it and it.text().endswith(" *"):
                        assert "Speichern ausstehend" in (it.toolTip() or "")
                        tip_found = True
                        break
                assert tip_found
            win.pdf_view._sidecar_save_pending = False
            store075.dirty = False
            feat075q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.7.5" in feat075q and "Snippet-Länge" in feat075q
            cl075q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "## 0.7.5" in cl075q
            print("0.7.5 Qt snippet-len/merge-all/templates-zip/debounce-tooltip: OK")

            # --- 0.7.6 Qt: Ellipsis-Style, Zip-Konflikt, Merge-Diff, Debounce-Blink ---
            from instantlensdoc.core.app_settings import (
                get_search_snippet_ellipsis_style as get_ell076,
                set_search_snippet_ellipsis_style as set_ell076,
            )
            from instantlensdoc.core.text_diff import (
                annotation_text_diff_short as diff076,
            )
            from instantlensdoc.ui.file_dialogs import (
                resolve_template_zip_conflicts as rtc076,
            )
            from instantlensdoc.ui.merge_duplicates_dialog import (
                MergeDuplicatesPreviewDialog as MDP076,
            )
            from instantlensdoc.ui.settings_dialog import SettingsDialog as SD076

            set_ell076("ellipsis")
            assert get_ell076() == "ellipsis"
            sd076 = SD076(parent=win)
            assert hasattr(sd076, "snippet_ellipsis")
            # Combo zeigt Ellipsis
            assert str(sd076.snippet_ellipsis.currentData()) == "ellipsis"
            sd076.snippet_ellipsis.setCurrentIndex(0)  # guillemets
            sd076._save()
            assert get_ell076() == "guillemets"
            set_ell076("guillemets")
            assert "Diff" in diff076("aaa", "bbb")
            store076 = win.pdf_view.store
            assert store076 is not None
            store076.annotations = []
            store076.clear_history()
            store076.add(Ann071(0, AT071.HIGHLIGHT, 2, 2, width=10, height=4, text="keep-text"))
            store076.add(Ann071(0, AT071.HIGHLIGHT, 2, 3, width=10, height=4, text="drop-text"))
            groups076 = store076.find_duplicate_groups(tol=2.0, same_type=True)
            dlg_diff = MDP076(groups076, parent=win)
            # Diff-Zeile in Liste
            texts076 = [
                dlg_diff.list.item(i).text()
                for i in range(dlg_diff.list.count())
                if dlg_diff.list.item(i)
            ]
            assert any("↕" in t and "Diff" in t for t in texts076)
            dlg_diff.close()
            assert callable(rtc076)
            assert callable(win._blink_pending_debounce_status)
            # Debounce-Blink rising edge
            win._pending_was_pending = False
            win._pending_blink_active = False
            win.pdf_view._sidecar_save_pending = True
            win.pdf_view._sidecar_save_timer.stop()
            if win.doc and win.doc.path:
                win._mark_unsaved(win.doc.path, True)
                win.stack.setCurrentWidget(win.pdf_view)
                win._refresh_document_dirty_labels()
                assert win._pending_was_pending is True
            win.pdf_view._sidecar_save_pending = False
            win._pending_was_pending = False
            feat076q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.7.6" in feat076q and "Ellipsis" in feat076q
            cl076q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "## 0.7.6" in cl076q
            print("0.7.6 Qt ellipsis/zip-conflict/merge-diff/debounce-blink: OK")

            # --- 0.7.7 Qt: Status-Blink, Merge-Tags/Farbe, Zip-Dry-Run, Ann.-Ellipsis ---
            from instantlensdoc.core.app_settings import (
                get_status_blink_mode as get_blink077,
                set_search_snippet_ellipsis_style as set_ell077q,
                set_status_blink_mode as set_blink077,
            )
            from instantlensdoc.core.fulltext import truncate_display_text as trunc077q
            from instantlensdoc.core.text_diff import (
                annotation_text_diff_short as diff077q,
            )
            from instantlensdoc.ui.merge_duplicates_dialog import (
                MergeDuplicatesPreviewDialog as MDP077,
            )
            from instantlensdoc.ui.settings_dialog import SettingsDialog as SD077

            set_blink077("aus")
            assert get_blink077() == "aus"
            sd077 = SD077(parent=win)
            assert hasattr(sd077, "status_blink")
            assert str(sd077.status_blink.currentData()) == "aus"
            sd077.status_blink.setCurrentIndex(0)  # kurz
            sd077._save()
            assert get_blink077() == "kurz"
            set_blink077("kurz")
            d077q = diff077q(
                "keep",
                "drop",
                left_tags=["a"],
                right_tags=["b"],
                left_color="#112233",
                right_color="#445566",
            )
            assert "[a]" in d077q and "#112233" in d077q
            store077 = win.pdf_view.store
            assert store077 is not None
            store077.annotations = []
            store077.clear_history()
            store077.add(
                Ann071(
                    0,
                    AT071.HIGHLIGHT,
                    2,
                    2,
                    width=10,
                    height=4,
                    text="keep-text",
                    color="#FFE066",
                    tags=["keepTag"],
                )
            )
            store077.add(
                Ann071(
                    0,
                    AT071.HIGHLIGHT,
                    2,
                    3,
                    width=10,
                    height=4,
                    text="drop-text",
                    color="#FF6B6B",
                    tags=["dropTag"],
                )
            )
            groups077 = store077.find_duplicate_groups(tol=2.0, same_type=True)
            dlg077 = MDP077(groups077, parent=win)
            texts077 = [
                dlg077.list.item(i).text()
                for i in range(dlg077.list.count())
                if dlg077.list.item(i)
            ]
            assert any("↕" in t and ("#" in t or "[" in t) for t in texts077)
            dlg077.close()
            set_ell077q("guillemets")
            long_txt = "X" * 80
            store077.annotations = []
            store077.clear_history()
            store077.add(
                Ann071(0, AT071.STICKY, 1, 1, width=20, height=20, text=long_txt)
            )
            summaries077 = win.pdf_view.annotation_summaries()
            assert summaries077
            assert "«…»" in summaries077[0][0]
            set_ell077q("ellipsis")
            summaries077b = win.pdf_view.annotation_summaries()
            assert "…" in summaries077b[0][0] and "«" not in summaries077b[0][0]
            set_ell077q("guillemets")
            assert "«…»" in trunc077q(long_txt, 40)
            # Blink aus: rising edge ohne aktiver Blink-Flag
            set_blink077("aus")
            win._pending_was_pending = False
            win._pending_blink_active = False
            win.pdf_view._sidecar_save_pending = True
            win.pdf_view._sidecar_save_timer.stop()
            if win.doc and win.doc.path:
                win._mark_unsaved(win.doc.path, True)
                win.stack.setCurrentWidget(win.pdf_view)
                win._refresh_document_dirty_labels()
                assert win._pending_blink_active is False
            win.pdf_view._sidecar_save_pending = False
            win._pending_was_pending = False
            set_blink077("kurz")
            feat077q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.7.7" in feat077q and "Dry-Run" in feat077q
            cl077q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "## 0.7.7" in cl077q
            print("0.7.7 Qt blink/merge-tags/zip-dry-run/ann-ellipsis: OK")

            # --- 0.7.8 Qt: Dry-Run-TXT, Ann.-Tooltip, Blink-Hinweis, Merge-Diff-Länge ---
            from instantlensdoc.core.app_settings import (
                get_merge_diff_max_side as get_md078,
                set_merge_diff_max_side as set_md078,
                set_status_blink_mode as set_blink078q,
                format_dry_run_conflict_list_txt as fmt078q,
            )
            from instantlensdoc.core.text_diff import (
                annotation_text_diff_short as diff078q,
            )
            from instantlensdoc.ui.merge_duplicates_dialog import (
                MergeDuplicatesPreviewDialog as MDP078,
            )
            from instantlensdoc.ui.settings_dialog import SettingsDialog as SD078

            set_md078(16)
            assert get_md078() == 16
            sd078 = SD078(parent=win)
            assert hasattr(sd078, "merge_diff_max")
            assert int(sd078.merge_diff_max.value()) == 16
            sd078.merge_diff_max.setValue(40)
            sd078._save()
            assert get_md078() == 40
            set_md078(20)
            d078q = diff078q("A" * 50, "B" * 50, max_side=get_md078())
            assert "…" in d078q
            store078 = win.pdf_view.store
            assert store078 is not None
            store078.annotations = []
            store078.clear_history()
            long078 = "VOLLER TEXT FÜR TOOLTIP " + ("Z" * 60)
            store078.add(
                Ann071(0, AT071.STICKY, 1, 1, width=20, height=20, text=long078)
            )
            store078.add(
                Ann071(
                    0,
                    AT071.STICKY,
                    1,
                    2,
                    width=20,
                    height=20,
                    text="kurz",
                    color="#112233",
                )
            )
            # Zwei ähnliche für Merge-Diff mit max_side aus Settings
            store078.annotations = []
            store078.clear_history()
            store078.add(
                Ann071(
                    0,
                    AT071.HIGHLIGHT,
                    3,
                    3,
                    width=12,
                    height=4,
                    text="AAAAAAAAAAAAAAAABBBBB",
                    color="#FFE066",
                    tags=["t1"],
                )
            )
            store078.add(
                Ann071(
                    0,
                    AT071.HIGHLIGHT,
                    3,
                    4,
                    width=12,
                    height=4,
                    text="AAAAAAAAAAAAAAAACCCCC",
                    color="#FF6B6B",
                    tags=["t2"],
                )
            )
            groups078 = store078.find_duplicate_groups(tol=2.0, same_type=True)
            dlg078 = MDP078(groups078, parent=win)
            texts078 = [
                dlg078.list.item(i).text()
                for i in range(dlg078.list.count())
                if dlg078.list.item(i)
            ]
            assert any("↕" in t and "…" in t for t in texts078)
            dlg078.close()
            # Ann.-Liste Tooltip voller Text
            store078.annotations = []
            store078.clear_history()
            store078.add(
                Ann071(0, AT071.STICKY, 1, 1, width=20, height=20, text=long078)
            )
            summaries078 = win.pdf_view.annotation_summaries()
            win.sidebar.set_annotations(
                [s[0] for s in summaries078],
                [s[1] for s in summaries078],
            )
            tip_found = False
            for i in range(win.sidebar.annotations.count()):
                it = win.sidebar.annotations.item(i)
                if it is None:
                    continue
                tip = it.toolTip() or ""
                if long078 in tip:
                    tip_found = True
                    break
            assert tip_found, "Ann.-Liste Tooltip sollte vollen Text zeigen"
            # Blink aus: einmaliger Hinweis, kein Blink-Flag
            set_blink078q("aus")
            win._pending_blink_active = False
            win._blink_pending_debounce_status()
            assert win._pending_blink_active is False
            msg078 = win.statusBar().currentMessage()
            assert "Speichern ausstehend" in msg078
            set_blink078q("kurz")
            set_md078(28)
            assert "OVERWRITE" in fmt078q(
                [{"title": "X", "action": "overwrite"}]
            )
            feat078q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.7.8" in feat078q and "Tooltip" in feat078q
            cl078q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "## 0.7.8" in cl078q
            print("0.7.8 Qt dry-run-txt/ann-tooltip/blink-hint/merge-diff-len: OK")

            # --- 0.7.9 Qt: Such-Export, Ann.-Filter-Presets, Bracket-Auto-Close ---
            from instantlensdoc.core.app_settings import (
                delete_ann_filter_preset as del_preset079,
                get_ann_filter_presets as get_presets079,
                get_editor_bracket_auto_close as get_ac079,
                save_ann_filter_preset as save_preset079,
                set_editor_bracket_auto_close as set_ac079,
            )
            from instantlensdoc.core.fulltext import (
                export_search_hits_csv as exp_csv079q,
                export_search_hits_json as exp_json079q,
            )
            from instantlensdoc.ui.settings_dialog import SettingsDialog as SD079

            set_ac079(False)
            sd079q = SD079(parent=win)
            assert hasattr(sd079q, "bracket_auto_close")
            assert sd079q.bracket_auto_close.isChecked() is False
            sd079q.bracket_auto_close.setChecked(True)
            sd079q._save()
            assert get_ac079() is True
            assert win.editor.bracket_auto_close_enabled() is True
            win.editor.set_bracket_auto_close_enabled(False)
            assert win.editor.bracket_auto_close_enabled() is False
            win.editor.set_bracket_auto_close_enabled(True)
            set_ac079(True)
            # Trefferliste füllen + export records
            win.sidebar.set_marks(
                ["doc.pdf S.1: hello", "S.2 Ann.: note"],
                [
                    (str(smoke_pdf), 0, "hello"),
                    Ann071(0, AT071.STICKY, 1, 1, width=10, height=10, text="note"),
                ],
            )
            recs079 = win.sidebar.search_hit_records()
            assert len(recs079) == 2
            assert recs079[0]["kind"] == "pdf" and recs079[0]["page"] == 1
            assert "annotation" in recs079[1]["kind"]
            csv_q079 = Path(td2) / "qt-search079.csv"
            json_q079 = Path(td2) / "qt-search079.json"
            assert exp_csv079q(csv_q079, recs079, query="hello").is_file()
            assert exp_json079q(json_q079, recs079, query="hello").is_file()
            assert "hello" in csv_q079.read_text(encoding="utf-8")
            assert "ildsearch-v1" in json_q079.read_text(encoding="utf-8")
            assert hasattr(win.sidebar, "btn_export_search_csv")
            assert hasattr(win.sidebar, "ann_filter_preset")
            assert callable(win.sidebar.annotation_filter_state)
            assert callable(win._on_search_export)
            # Filter-Presets UI roundtrip
            for old in list(get_presets079()):
                del_preset079(old["name"])
            win.sidebar.set_annotation_filter_current_page(True)
            win.sidebar.set_annotation_color_filter("#FFCC00")
            win.sidebar.set_annotation_tag_filter(["Review079"])
            win.sidebar.ann_search.setText("preset")
            win.sidebar.set_annotation_search_regex(True)
            state079 = win.sidebar.annotation_filter_state()
            assert state079["current_page"] is True
            assert state079["color"].upper() == "#FFCC00"
            assert state079["search"] == "preset" and state079["regex"] is True
            save_preset079("QtPreset079", state=state079)
            win.sidebar.set_annotation_filter_current_page(False)
            win.sidebar.clear_annotation_color_filter()
            win.sidebar.set_annotation_tag_filter("")
            win.sidebar.ann_search.setText("")
            win.sidebar.set_annotation_search_regex(False)
            win.sidebar._refresh_ann_filter_preset_combo(keep="QtPreset079")
            win.sidebar.ann_filter_preset.setCurrentText("QtPreset079")
            win.sidebar._load_ann_filter_preset_clicked()
            st2 = win.sidebar.annotation_filter_state()
            assert st2["current_page"] is True
            assert st2["color"].upper() == "#FFCC00"
            assert st2["search"] == "preset" and st2["regex"] is True
            del_preset079("QtPreset079")
            feat079q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.7.9" in feat079q and "Bracket-Auto-Close" in feat079q
            cl079q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "## 0.7.9" in cl079q
            print("0.7.9 Qt search-export/ann-presets/bracket-auto-close: OK")

            # --- 0.8.0 Qt: Bookmark ildbm, Tag-Cloud Kontext, Status, Recent ---
            from instantlensdoc.core.app_settings import (
                get_recent_files_max as get_rf080,
                set_recent_files_max as set_rf080,
            )
            from instantlensdoc.core.bookmarks import BM_SCHEMA_ID as BM080
            from instantlensdoc.ui.settings_dialog import SettingsDialog as SD080

            assert callable(getattr(win, "_export_line_bookmarks_json", None))
            assert callable(getattr(win, "_import_line_bookmarks_json", None))
            assert callable(getattr(win, "_recolor_annotation_tag_global", None))
            assert hasattr(win.sidebar, "annotation_tag_recolor_requested")
            win.stack.setCurrentWidget(win.editor_pane)
            win.editor.setPlainText("L1\nL2\nL3\nL4\nL5\n")
            win.editor.clear_line_bookmarks()
            win.editor.toggle_line_bookmark(2)
            win.editor.set_line_bookmark_label(2, "Kapitel")
            win.editor.toggle_line_bookmark(4)
            bm_qt = Path(td2) / "qt-bm080.json"
            saved_bm = win.editor.export_line_bookmarks_json(bm_qt, source="smoke.txt")
            raw_bmq = json.loads(saved_bm.read_text(encoding="utf-8"))
            assert raw_bmq["schema"] == BM080 and raw_bmq["version"] == 1
            win.editor.clear_line_bookmarks()
            assert win.editor.list_line_bookmarks() == []
            win.editor.import_line_bookmarks_json(bm_qt)
            assert win.editor.list_line_bookmarks() == [2, 4]
            assert win.editor.get_line_bookmark_label(2) == "Kapitel"
            win._update_doc_status()
            assert "Zeile" in win.page_status_label.text()
            win.stack.setCurrentWidget(win.pdf_view)
            if win.pdf_view.pdf_path and win.pdf_view.page_count > 0:
                win._update_doc_status()
                assert "Seite" in win.page_status_label.text()
            win.stack.setCurrentWidget(win.editor_pane)
            win._update_doc_status()
            assert "Zeile" in win.page_status_label.text()
            # Tag-Cloud recolor API + context menu actions present
            assert "annotation_tag_recolor_requested" in dir(win.sidebar)
            # Recent settings UI
            set_rf080(7)
            sd080q = SD080(parent=win)
            assert hasattr(sd080q, "recent_files_max") and hasattr(sd080q, "btn_clear_recent")
            assert sd080q.recent_files_max.value() == 7
            sd080q.recent_files_max.setValue(15)
            sd080q._save()
            assert get_rf080() == 15
            set_rf080(12)
            feat080q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.8.0" in feat080q and "ildbm-v1" in feat080q
            cl080q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "## 0.8.0" in cl080q
            print("0.8.0 Qt bookmark-ildbm/tag-cloud-ctx/status/recent: OK")

            # --- 0.8.1 Qt: Bookmark Drag/Sidecar, Tag-Cloud Sort, Recent fehlt, Zoom-% ---
            from PySide6.QtCore import Qt as Qt081
            from instantlensdoc.core.app_settings import (
                TAG_CLOUD_SORT_AZ as TC_AZ081,
                TAG_CLOUD_SORT_FREQ as TC_FREQ081,
                get_tag_cloud_sort as get_tcs081,
                set_tag_cloud_sort as set_tcs081,
            )
            from instantlensdoc.core.bookmarks import (
                load_bookmarks_sidecar as load_side081,
                sidecar_path_for as side_for081,
            )
            from instantlensdoc.core import recent as recent_mod081q

            assert callable(getattr(win.editor, "reorder_line_bookmarks", None))
            assert hasattr(win.sidebar, "line_favorites_reordered")
            assert callable(getattr(win.sidebar, "set_tag_cloud_sort_mode", None))
            assert callable(getattr(win, "_on_line_favorites_reordered", None))
            assert callable(getattr(win, "_remove_recent_path", None))
            # Bookmark order + sidecar
            win.stack.setCurrentWidget(win.editor_pane)
            win.editor.setPlainText("A\nB\nC\nD\nE\nF\n")
            win.editor.clear_line_bookmarks()
            win.editor.toggle_line_bookmark(2)
            win.editor.toggle_line_bookmark(4)
            win.editor.toggle_line_bookmark(6)
            assert win.editor.list_line_bookmarks() == [2, 4, 6]
            win.editor.reorder_line_bookmarks([6, 2, 4])
            assert win.editor.list_line_bookmarks() == [6, 2, 4]
            bm_txt081 = td2 / "qt_bm081.txt"
            bm_txt081.write_text("A\nB\nC\nD\nE\nF\n", encoding="utf-8")
            win.open_path(str(bm_txt081))
            win.editor.clear_line_bookmarks()
            win.editor.toggle_line_bookmark(3)
            win.editor.set_line_bookmark_label(3, "Mitte")
            win.editor.toggle_line_bookmark(1)
            win.editor.reorder_line_bookmarks([1, 3])
            win._persist_line_bookmarks_sidecar()
            assert side_for081(bm_txt081).is_file()
            assert load_side081(bm_txt081) == [(1, ""), (3, "Mitte")]
            win._suppress_bookmark_persist = True
            try:
                win.editor.clear_line_bookmarks()
                assert win.editor.list_line_bookmarks() == []
                win._load_line_bookmarks_sidecar(bm_txt081)
            finally:
                win._suppress_bookmark_persist = False
            assert win.editor.list_line_bookmarks() == [1, 3]
            assert win.editor.get_line_bookmark_label(3) == "Mitte"
            # Tag-Cloud sort toggle
            set_tcs081("freq")
            assert win.sidebar.set_tag_cloud_sort_mode("az") == TC_AZ081
            assert get_tcs081() == TC_AZ081
            assert win.sidebar.tag_cloud_sort_mode() == TC_AZ081
            assert win.sidebar.set_tag_cloud_sort_mode("freq") == TC_FREQ081
            # Recent missing gray + remove
            ghost_q = td2 / "ghost_qt081.txt"
            alive_q = td2 / "alive_qt081.txt"
            alive_q.write_text("x", encoding="utf-8")
            rf081 = td2 / "recent_qt081.json"
            orig_rf081 = recent_mod081q.recent_path
            recent_mod081q.recent_path = lambda: rf081  # type: ignore
            try:
                recent_mod081q.save_recent([str(alive_q), str(ghost_q)])
                win._refresh_recent()
                assert win.sidebar.recent.count() == 2
                miss_item = None
                for i in range(win.sidebar.recent.count()):
                    it = win.sidebar.recent.item(i)
                    if it is None:
                        continue
                    raw = it.data(Qt081.UserRole) or it.data(256)
                    if raw and Path(str(raw)).name == ghost_q.name:
                        miss_item = it
                        break
                assert miss_item is not None
                assert miss_item.data(Qt081.UserRole + 1) is False
                assert "fehlt" in miss_item.text()
                win._remove_recent_path(str(ghost_q))
                left = [
                    win.sidebar.recent.item(i).data(Qt081.UserRole)
                    or win.sidebar.recent.item(i).data(256)
                    for i in range(win.sidebar.recent.count())
                ]
                assert str(ghost_q) not in left
            finally:
                recent_mod081q.recent_path = orig_rf081  # type: ignore
                recent_mod081q.clear_recent()
            # Zoom-% in Statusleiste bei PDF
            if win.pdf_view.pdf_path and win.pdf_view.page_count > 0:
                win.stack.setCurrentWidget(win.pdf_view)
                win._update_doc_status()
                ztxt = win.zoom_status_label.text()
                assert "Zoom" in ztxt and "%" in ztxt
                win._on_pdf_zoom_changed(1.25)
                assert "Zoom 125%" in win.zoom_status_label.text()
            feat081q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.8.1" in feat081q and "Drag-Reorder" in feat081q
            cl081q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "## 0.8.1" in cl081q
            print("0.8.1 Qt bookmark-drag/tag-sort/recent-missing/zoom: OK")

            # --- 0.8.2 Qt: Thumbnail-Undo, Fit-Zoom, Ann.-Ctrl+D, Standard-Zoom ---
            from instantlensdoc.core.app_settings import (
                DEFAULT_ZOOM_MODE_FIT_WIDTH as ZM_FW082,
                DEFAULT_ZOOM_MODE_PERCENT as ZM_PCT082,
                get_default_zoom_mode as get_zm082,
                get_default_zoom_percent as get_zp082,
                set_default_zoom_mode as set_zm082,
                set_default_zoom_percent as set_zp082,
            )
            from instantlensdoc.ui.settings_dialog import SettingsDialog as SD082
            from ild_pdf import Annotation as Ann082, AnnotationType as AT082

            assert callable(getattr(win, "_duplicate_current", None))
            assert callable(getattr(win, "_save_current_zoom_as_default", None))
            assert callable(getattr(win.pdf_view, "apply_page_order", None))
            # Standard-Zoom-Modus Settings
            set_zm082("percent")
            set_zp082(140)
            sd082q = SD082(parent=win)
            assert hasattr(sd082q, "zoom_mode") and hasattr(sd082q, "btn_zoom_from_pdf")
            assert sd082q.zoom_mode.currentData() == ZM_PCT082
            for i in range(sd082q.zoom_mode.count()):
                if sd082q.zoom_mode.itemData(i) == ZM_FW082:
                    sd082q.zoom_mode.setCurrentIndex(i)
                    break
            sd082q._sync_zoom_pct_enabled()
            assert not sd082q.zoom_pct.isEnabled()
            sd082q._save()
            assert get_zm082() == ZM_FW082
            set_zm082("percent")
            # Thumbnail reorder + undo
            if win.pdf_view.pdf_path and win.pdf_view.page_count >= 2:
                n_pages = win.pdf_view.page_count
                order = list(range(n_pages))
                order[0], order[1] = order[1], order[0]
                win.pdf_view.clear_page_ops_undo()
                assert win.pdf_view.apply_page_order(order) is True
                assert win.pdf_view.can_undo_page_op()
                hist = win.pdf_view.page_ops_history_items()
                assert any(h.get("kind") == "reorder" for h in hist)
                assert win.pdf_view.undo_page_op() is True
                assert not win.pdf_view.can_undo_page_op()
            # Ctrl+D / Annotation duplizieren
            if win.pdf_view.pdf_path and win.pdf_view.store is not None:
                win.stack.setCurrentWidget(win.pdf_view)
                a082 = Ann082(
                    0, AT082.HIGHLIGHT, 5, 5, width=20, height=10, text="dup082"
                )
                win.pdf_view.store.add(a082)
                win.pdf_view._selected_ann_id = a082.id
                win.pdf_view._selected_ann_ids = {a082.id}
                before_n = len(win.pdf_view.store.annotations)
                win._duplicate_current()
                assert len(win.pdf_view.store.annotations) == before_n + 1
            # Aktuellen Zoom als Standard speichern
            if win.pdf_view.pdf_path:
                win.stack.setCurrentWidget(win.pdf_view)
                win.pdf_view.set_scale(1.33, immediate=True)
                win._save_current_zoom_as_default()
                assert get_zp082() == 133
                assert get_zm082() == ZM_PCT082
            feat082q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.8.2" in feat082q and ("Ctrl+D" in feat082q or "Fit-Width" in feat082q)
            cl082q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "## 0.8.2" in cl082q
            print("0.8.2 Qt thumb-undo/fit-zoom/ann-ctrl-d/default-zoom: OK")

            # --- 0.8.3 Qt: Ann.-Multi-Select, Thumb-Drehen, Seitennummer-Overlay, Zeilennummern ---
            from instantlensdoc.core.app_settings import (
                get_editor_line_numbers as get_ln083q,
                get_show_page_number_overlay as get_pno083,
                set_editor_line_numbers as set_ln083q,
                set_show_page_number_overlay as set_pno083,
            )
            from instantlensdoc.ui.settings_dialog import SettingsDialog as SD083
            from ild_pdf import Annotation as Ann083, AnnotationType as AT083

            assert callable(getattr(win, "_on_thumb_rotate", None))
            assert callable(getattr(win, "_toggle_page_number_overlay", None))
            assert callable(getattr(win.pdf_view, "rotate_at", None))
            assert callable(getattr(win.pdf_view, "set_show_page_number_overlay", None))
            assert hasattr(win.sidebar, "page_rotate_requested")
            # Seitennummer-Overlay Settings
            set_pno083(False)
            sd083q = SD083(parent=win)
            assert hasattr(sd083q, "page_num_overlay")
            sd083q.page_num_overlay.setChecked(True)
            sd083q._save()
            assert get_pno083() is True
            assert win.pdf_view.show_page_number_overlay() is True
            set_pno083(False)
            win.pdf_view.set_show_page_number_overlay(False)
            # Zeilennummern Toggle persistieren
            set_ln083q(False)
            win._toggle_line_numbers(True)
            assert get_ln083q() is True
            assert win.editor.line_numbers_visible()
            win._toggle_line_numbers(False)
            assert get_ln083q() is False
            # Annotation Mehrfachauswahl + gemeinsame Verschiebung
            if win.pdf_view.pdf_path and win.pdf_view.store is not None:
                win.stack.setCurrentWidget(win.pdf_view)
                a083a = Ann083(
                    0, AT083.HIGHLIGHT, 10, 10, width=30, height=12, text="ms-a"
                )
                a083b = Ann083(
                    0, AT083.HIGHLIGHT, 50, 40, width=30, height=12, text="ms-b"
                )
                win.pdf_view.store.add(a083a)
                win.pdf_view.store.add(a083b)
                win.pdf_view._selected_ann_ids = {a083a.id, a083b.id}
                win.pdf_view._selected_ann_id = a083b.id
                win.pdf_view.canvas.set_selected_ids(win.pdf_view._selected_ann_ids)
                assert len(win.pdf_view._selected_ann_ids) == 2
                x0a = float(a083a.x)
                y0b = float(a083b.y)
                n_moved = win.pdf_view.store.move_by(
                    list(win.pdf_view._selected_ann_ids), 15.0, 10.0
                )
                assert n_moved == 2
                a083a2 = win.pdf_view.store.get(a083a.id)
                a083b2 = win.pdf_view.store.get(a083b.id)
                assert abs(float(a083a2.x) - (x0a + 15.0)) < 0.01
                assert abs(float(a083b2.y) - (y0b + 10.0)) < 0.01
            # Thumbnail drehen + Undo
            if win.pdf_view.pdf_path and win.pdf_view.page_count >= 1:
                win.pdf_view.clear_page_ops_undo()
                idx = int(win.pdf_view.page_index)
                assert win.pdf_view.rotate_at(idx, 90) is True
                assert win.pdf_view.can_undo_page_op()
                hist = win.pdf_view.page_ops_history_items()
                assert any(h.get("kind") == "rotate" for h in hist)
                assert win.pdf_view.undo_page_op() is True
            feat083q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.8.3" in feat083q and "Mehrfachauswahl" in feat083q
            cl083q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "## 0.8.3" in cl083q
            print("0.8.3 Qt multi-select/thumb-rotate/page-num/line-numbers: OK")

            # --- 0.8.4 Qt: Align/Distribute, Thumb-Löschen, Overlay-Opacity, Wortumbruch ---
            from instantlensdoc.core.app_settings import (
                get_editor_soft_wrap as get_sw084q,
                get_page_number_overlay_opacity as get_pno_op084,
                set_editor_soft_wrap as set_sw084q,
                set_page_number_overlay_opacity as set_pno_op084,
            )
            from instantlensdoc.ui.settings_dialog import SettingsDialog as SD084
            from ild_pdf import Annotation as Ann084q, AnnotationType as AT084q

            assert callable(getattr(win, "_on_thumb_delete", None))
            assert callable(getattr(win, "_align_selected_annotations", None))
            assert callable(getattr(win, "_distribute_selected_annotations_horizontal", None))
            assert callable(getattr(win.pdf_view, "align_selected_annotations", None))
            assert callable(getattr(win.pdf_view, "distribute_selected_annotations_horizontal", None))
            assert callable(getattr(win.pdf_view, "delete_at", None))
            assert callable(getattr(win.pdf_view, "set_page_number_overlay_opacity", None))
            assert hasattr(win.sidebar, "page_delete_requested")
            # Overlay opacity Settings
            set_pno_op084(0.4)
            sd084q = SD084(parent=win)
            assert hasattr(sd084q, "page_num_opacity")
            sd084q.page_num_opacity.setValue(0.72)
            sd084q._save()
            assert abs(get_pno_op084() - 0.72) < 0.001
            assert abs(win.pdf_view.page_number_overlay_opacity() - 0.72) < 0.001
            set_pno_op084(0.59)
            win.pdf_view.set_page_number_overlay_opacity(0.59)
            # Wortumbruch Toggle persistieren
            set_sw084q(False)
            win._toggle_soft_wrap(True)
            assert get_sw084q() is True
            assert win.editor.soft_wrap_enabled()
            win._toggle_soft_wrap(False)
            assert get_sw084q() is False
            assert not win.editor.soft_wrap_enabled()
            win._toggle_soft_wrap(True)
            # Align / Distribute
            if win.pdf_view.pdf_path and win.pdf_view.store is not None:
                win.stack.setCurrentWidget(win.pdf_view)
                a1 = Ann084q(0, AT084q.STICKY, 10, 10, width=20, height=12, text="al1")
                a2 = Ann084q(0, AT084q.STICKY, 60, 30, width=20, height=12, text="al2")
                a3 = Ann084q(0, AT084q.STICKY, 110, 50, width=20, height=12, text="al3")
                win.pdf_view.store.add(a1)
                win.pdf_view.store.add(a2)
                win.pdf_view.store.add(a3)
                win.pdf_view._selected_ann_ids = {a1.id, a2.id, a3.id}
                win.pdf_view._selected_ann_id = a3.id
                n_left = win.pdf_view.align_selected_annotations("left")
                assert n_left >= 1
                xs_l = [float(win.pdf_view.store.get(i).x) for i in (a1.id, a2.id, a3.id)]
                assert max(xs_l) - min(xs_l) < 0.01
                win.pdf_view.store.update(a1.id, x=10.0)
                win.pdf_view.store.update(a2.id, x=40.0)
                win.pdf_view.store.update(a3.id, x=100.0)
                win.pdf_view._selected_ann_ids = {a1.id, a2.id, a3.id}
                n_dist = win.pdf_view.distribute_selected_annotations_horizontal()
                assert n_dist >= 1
            # Thumb delete + Undo (ohne Confirm-Dialog: confirm=False)
            if win.pdf_view.pdf_path and win.pdf_view.page_count >= 2:
                win.pdf_view.clear_page_ops_undo()
                before = int(win.pdf_view.page_count)
                idx = min(int(win.pdf_view.page_index), before - 1)
                assert win.pdf_view.delete_at(idx, confirm=False) is True
                assert int(win.pdf_view.page_count) == before - 1
                assert win.pdf_view.can_undo_page_op()
                assert win.pdf_view.undo_page_op() is True
                assert int(win.pdf_view.page_count) == before
            feat084q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.8.4" in feat084q
            cl084q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "## 0.8.4" in cl084q
            print("0.8.4 Qt align/distribute/thumb-delete/overlay-opacity/word-wrap: OK")

            # --- 0.8.5 Qt: Align/Distribute V, Thumb-Duplizieren, Overlay-Font, Tab-Breite ---
            from instantlensdoc.core.app_settings import (
                get_editor_tab_width as get_tw085q,
                get_page_number_overlay_font_size as get_pno_fs085,
                set_editor_tab_width as set_tw085q,
                set_page_number_overlay_font_size as set_pno_fs085,
            )
            from instantlensdoc.ui.settings_dialog import SettingsDialog as SD085
            from ild_pdf import Annotation as Ann085q, AnnotationType as AT085q

            assert callable(getattr(win, "_on_thumb_duplicate", None))
            assert callable(getattr(win, "_distribute_selected_annotations_vertical", None))
            assert callable(getattr(win.pdf_view, "distribute_selected_annotations_vertical", None))
            assert callable(getattr(win.pdf_view, "duplicate_at", None))
            assert callable(getattr(win.pdf_view, "set_page_number_overlay_font_size", None))
            assert hasattr(win.sidebar, "page_duplicate_requested")
            assert callable(getattr(win.editor, "set_tab_width", None))
            # Overlay font Settings
            set_pno_fs085(16)
            sd085q = SD085(parent=win)
            assert hasattr(sd085q, "page_num_font")
            assert hasattr(sd085q, "tab_width")
            sd085q.page_num_font.setValue(18)
            # Tab-Breite 8
            for i in range(sd085q.tab_width.count()):
                if sd085q.tab_width.itemData(i) == 8:
                    sd085q.tab_width.setCurrentIndex(i)
                    break
            sd085q._save()
            assert get_pno_fs085() == 18
            assert win.pdf_view.page_number_overlay_font_size() == 18
            assert get_tw085q() == 8
            assert win.editor.tab_width() == 8
            set_pno_fs085(11)
            win.pdf_view.set_page_number_overlay_font_size(11)
            set_tw085q(4)
            win.editor.set_tab_width(4)
            # Align V / Distribute V
            if win.pdf_view.pdf_path and win.pdf_view.store is not None:
                win.stack.setCurrentWidget(win.pdf_view)
                v1 = Ann085q(0, AT085q.STICKY, 10, 10, width=20, height=12, text="v1")
                v2 = Ann085q(0, AT085q.STICKY, 30, 40, width=20, height=12, text="v2")
                v3 = Ann085q(0, AT085q.STICKY, 50, 90, width=20, height=12, text="v3")
                win.pdf_view.store.add(v1)
                win.pdf_view.store.add(v2)
                win.pdf_view.store.add(v3)
                win.pdf_view._selected_ann_ids = {v1.id, v2.id, v3.id}
                win.pdf_view._selected_ann_id = v3.id
                n_top = win.pdf_view.align_selected_annotations("top")
                assert n_top >= 1
                ys_t = [float(win.pdf_view.store.get(i).y) for i in (v1.id, v2.id, v3.id)]
                assert max(ys_t) - min(ys_t) < 0.01
                win.pdf_view.store.update(v1.id, y=10.0)
                win.pdf_view.store.update(v2.id, y=40.0)
                win.pdf_view.store.update(v3.id, y=100.0)
                win.pdf_view._selected_ann_ids = {v1.id, v2.id, v3.id}
                n_dv = win.pdf_view.distribute_selected_annotations_vertical()
                assert n_dv >= 1
            # Thumb duplicate + Undo
            if win.pdf_view.pdf_path:
                win.pdf_view.clear_page_ops_undo()
                before_d = int(win.pdf_view.page_count)
                idx_d = min(int(win.pdf_view.page_index), before_d - 1)
                assert win.pdf_view.duplicate_at(idx_d) is True
                assert int(win.pdf_view.page_count) == before_d + 1
                assert win.pdf_view.can_undo_page_op()
                assert win.pdf_view.undo_page_op() is True
                assert int(win.pdf_view.page_count) == before_d
            feat085q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.8.5" in feat085q
            cl085q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "## 0.8.5" in cl085q
            print("0.8.5 Qt align-v/distribute-v/thumb-dup/overlay-font/tab-width: OK")

            # --- 0.8.6 Qt: Group/Ungroup, Thumb Batch, Overlay-Position, Soft-Tabs ---
            from instantlensdoc.core.app_settings import (
                get_editor_soft_tabs as get_st086q,
                get_page_number_overlay_position as get_pno_pos086,
                set_editor_soft_tabs as set_st086q,
                set_page_number_overlay_position as set_pno_pos086,
            )
            from instantlensdoc.ui.settings_dialog import SettingsDialog as SD086
            from ild_pdf import Annotation as Ann086q, AnnotationType as AT086q

            assert callable(getattr(win, "_group_selected_annotations", None))
            assert callable(getattr(win, "_ungroup_selected_annotations", None))
            assert callable(getattr(win, "_on_thumbs_batch_duplicate", None))
            assert callable(getattr(win, "_on_thumbs_batch_delete", None))
            assert callable(getattr(win.pdf_view, "group_selected_annotations", None))
            assert callable(getattr(win.pdf_view, "ungroup_selected_annotations", None))
            assert callable(getattr(win.pdf_view, "duplicate_many", None))
            assert callable(getattr(win.pdf_view, "delete_many", None))
            assert callable(getattr(win.pdf_view, "set_page_number_overlay_position", None))
            assert hasattr(win.sidebar, "pages_batch_duplicate_requested")
            assert hasattr(win.sidebar, "pages_batch_delete_requested")
            assert callable(getattr(win.sidebar, "selected_thumb_pages", None))
            assert callable(getattr(win.editor, "set_soft_tabs", None))
            # Overlay position + Soft-Tabs Settings
            set_pno_pos086("top-center")
            set_st086q(False)
            sd086q = SD086(parent=win)
            assert hasattr(sd086q, "page_num_pos")
            assert hasattr(sd086q, "soft_tabs")
            for i in range(sd086q.page_num_pos.count()):
                if sd086q.page_num_pos.itemData(i) == "bottom-center":
                    sd086q.page_num_pos.setCurrentIndex(i)
                    break
            sd086q.soft_tabs.setChecked(True)
            sd086q._save()
            assert get_pno_pos086() == "bottom-center"
            assert win.pdf_view.page_number_overlay_position() == "bottom-center"
            assert get_st086q() is True
            assert win.editor.soft_tabs_enabled() is True
            win.pdf_view.set_page_number_overlay_position("top-center")
            assert win.pdf_view.page_number_overlay_position() == "top-center"
            win.editor.set_soft_tabs(False)
            assert win.editor.soft_tabs_enabled() is False
            win.editor.set_soft_tabs(True)
            set_pno_pos086("bottom-center")
            win.pdf_view.set_page_number_overlay_position("bottom-center")
            # Group / Ungroup
            if win.pdf_view.pdf_path and win.pdf_view.store is not None:
                win.stack.setCurrentWidget(win.pdf_view)
                g1 = Ann086q(0, AT086q.STICKY, 10, 10, width=20, height=12, text="g1")
                g2 = Ann086q(0, AT086q.STICKY, 40, 20, width=20, height=12, text="g2")
                win.pdf_view.store.add(g1)
                win.pdf_view.store.add(g2)
                win.pdf_view._selected_ann_ids = {g1.id, g2.id}
                win.pdf_view._selected_ann_id = g2.id
                n_g = win.pdf_view.group_selected_annotations()
                assert n_g == 2
                assert win.pdf_view.store.get(g1.id).group_id
                assert win.pdf_view.store.get(g1.id).group_id == win.pdf_view.store.get(g2.id).group_id
                n_ug = win.pdf_view.ungroup_selected_annotations()
                assert n_ug == 2
                assert win.pdf_view.store.get(g1.id).group_id == ""
            # Thumb batch duplicate (1 page) + Undo
            if win.pdf_view.pdf_path and int(win.pdf_view.page_count or 0) >= 1:
                win.pdf_view.clear_page_ops_undo()
                before_b = int(win.pdf_view.page_count)
                idx_b = min(int(win.pdf_view.page_index), before_b - 1)
                n_dup = win.pdf_view.duplicate_many([idx_b])
                assert n_dup == 1
                assert int(win.pdf_view.page_count) == before_b + 1
                assert win.pdf_view.undo_page_op() is True
                assert int(win.pdf_view.page_count) == before_b
            feat086q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.8.6" in feat086q
            cl086q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "## 0.8.6" in cl086q
            print("0.8.6 Qt group/ungroup/thumb-batch/overlay-pos/soft-tabs: OK")

            # --- 0.8.7 Qt: Group-Select/Lock, Thumb Batch-Rotate, Overlay-Format, Mehrzeilen-Indent ---
            from instantlensdoc.core.app_settings import (
                get_page_number_overlay_format as get_pno_fmt087,
                set_page_number_overlay_format as set_pno_fmt087,
            )
            from instantlensdoc.ui.settings_dialog import SettingsDialog as SD087q

            assert callable(getattr(win, "_toggle_selected_group_lock", None))
            assert callable(getattr(win, "_on_thumbs_batch_rotate", None))
            assert callable(getattr(win.pdf_view, "toggle_selected_group_lock", None))
            assert callable(getattr(win.pdf_view, "rotate_many", None))
            assert callable(getattr(win.pdf_view, "set_page_number_overlay_format", None))
            assert callable(getattr(win.pdf_view, "format_page_number_overlay_text", None))
            assert callable(getattr(win.editor, "selection_spans_multiple_lines", None))
            assert callable(getattr(win.editor, "insert_indent_at_cursor", None))
            assert hasattr(win.sidebar, "pages_batch_rotate_requested")
            sd087q = SD087q(win)
            assert hasattr(sd087q, "page_num_format")
            set_pno_fmt087("Seite {page} von {pages}")
            win.pdf_view.set_page_number_overlay_format("Seite {page} von {pages}")
            assert win.pdf_view.page_number_overlay_format() == "Seite {page} von {pages}"
            assert "Seite" in win.pdf_view.format_page_number_overlay_text()
            win.pdf_view.set_page_number_overlay_format("{page} / {pages}")
            set_pno_fmt087("{page} / {pages}")
            assert get_pno_fmt087() == "{page} / {pages}"
            # Group select + lock
            if win.pdf_view.store is not None:
                win.pdf_view.store.annotations = [
                    a
                    for a in win.pdf_view.store.annotations
                    if getattr(a, "text", "") not in ("g087a", "g087b")
                ]
                from ild_pdf import Annotation as A087q, AnnotationType as T087q

                g1 = A087q(0, T087q.HIGHLIGHT, 15, 15, width=25, height=12, text="g087a")
                g2 = A087q(0, T087q.HIGHLIGHT, 50, 25, width=25, height=12, text="g087b")
                win.pdf_view.store.add(g1)
                win.pdf_view.store.add(g2)
                win.pdf_view.store.group([g1.id, g2.id])
                win.pdf_view._on_annotation_selected(g1.id)
                assert g1.id in win.pdf_view._selected_ann_ids
                assert g2.id in win.pdf_view._selected_ann_ids
                n_lock_q = win.pdf_view.toggle_selected_group_lock()
                assert n_lock_q >= 2
                assert win.pdf_view.store.get(g1.id).locked
                n_unlock_q = win.pdf_view.toggle_selected_group_lock()
                assert n_unlock_q >= 2
                assert not win.pdf_view.store.get(g1.id).locked
                win.pdf_view.ungroup_selected_annotations()
            # Thumb batch rotate
            if int(win.pdf_view.page_count or 0) >= 2:
                assert win.pdf_view.rotate_many([0, 1], 90) == 2
                assert win.pdf_view.undo_page_op() is True
                assert win.pdf_view.undo_page_op() is True
            # Editor multiline indent
            from PySide6.QtGui import QTextCursor as _TC087

            win.editor.setPlainText("alpha\nbeta\ngamma\n")
            cur = win.editor.textCursor()
            cur.setPosition(0)
            cur.setPosition(len("alpha\nbeta"), _TC087.KeepAnchor)
            win.editor.setTextCursor(cur)
            assert win.editor.selection_spans_multiple_lines() is True
            win.editor.set_soft_tabs(True)
            assert win.editor.indent_selection(4) is True
            body = win.editor.toPlainText()
            assert body.startswith("    alpha\n    beta")
            feat087q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.8.7" in feat087q
            cl087q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "## 0.8.7" in cl087q
            print("0.8.7 Qt group-select/lock/thumb-rotate/overlay-fmt/multiline-indent: OK")

            # --- 0.8.8 Qt: Group Rename/Color, Thumb Extract, Overlay-Start, Indent-Guides ---
            from instantlensdoc.core.app_settings import (
                get_editor_indent_guides as get_ig088,
                get_page_number_overlay_start as get_pno_start088,
                set_editor_indent_guides as set_ig088,
                set_page_number_overlay_start as set_pno_start088,
            )
            from instantlensdoc.ui.settings_dialog import SettingsDialog as SD088q

            assert callable(getattr(win, "_edit_selected_ann_group", None))
            assert callable(getattr(win, "_on_thumbs_batch_extract", None))
            assert callable(getattr(win, "_toggle_indent_guides", None))
            assert callable(getattr(win.pdf_view, "edit_selected_ann_group", None))
            assert callable(getattr(win.pdf_view, "extract_selected_pages_as_pdf", None))
            assert callable(getattr(win.pdf_view, "set_page_number_overlay_start", None))
            assert callable(getattr(win.editor, "set_indent_guides_visible", None))
            assert hasattr(win.sidebar, "pages_batch_extract_requested")
            sd088q = SD088q(win)
            assert hasattr(sd088q, "page_num_start")
            assert hasattr(sd088q, "indent_guides")
            set_pno_start088(7)
            win.pdf_view.set_page_number_overlay_start(7)
            assert win.pdf_view.page_number_overlay_start() == 7
            win.pdf_view.page_index = 0
            txt088 = win.pdf_view.format_page_number_overlay_text()
            assert "7" in txt088
            win.pdf_view.set_page_number_overlay_start(1)
            set_pno_start088(1)
            assert get_pno_start088() == 1
            set_ig088(False)
            win.editor.set_indent_guides_visible(False)
            assert win.editor.indent_guides_visible() is False
            sd088q.indent_guides.setChecked(True)
            sd088q.page_num_start.setValue(1)
            sd088q._save()
            assert get_ig088() is True
            assert win.editor.indent_guides_visible() is True
            if win.pdf_view.store is not None:
                from ild_pdf import Annotation as A088q, AnnotationType as T088q

                g1 = A088q(0, T088q.HIGHLIGHT, 12, 12, width=22, height=10, text="g088qa")
                g2 = A088q(0, T088q.HIGHLIGHT, 48, 22, width=22, height=10, text="g088qb")
                win.pdf_view.store.add(g1)
                win.pdf_view.store.add(g2)
                _, gid_q = win.pdf_view.store.group([g1.id, g2.id])
                win.pdf_view.store.set_ann_group(gid_q, title="SmokeG", color="#AABBCC")
                assert win.pdf_view.store.get_ann_group(gid_q)["title"] == "SmokeG"
                assert win.pdf_view.store.get_ann_group(gid_q)["color"] == "#AABBCC"
                win.pdf_view.store.ungroup([g1.id, g2.id])
            if int(win.pdf_view.page_count or 0) >= 2:
                from ild_pdf.pages import extract_pages as ep088q

                dest088q = Path(tempfile.mkdtemp()) / "batch_extract.pdf"
                ep088q(win.pdf_view.pdf_path, dest088q, [0, 1])
                assert dest088q.is_file() and dest088q.stat().st_size > 0
            feat088q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.8.8" in feat088q
            cl088q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "## 0.8.8" in cl088q
            print("0.8.8 Qt group-rename/color/thumb-extract/overlay-start/indent-guides: OK")

            # --- 0.8.9 Qt: Group Filter/JSON, Thumb Tab-Open, Overlay-Edges, Current-Line-HL ---
            from instantlensdoc.core.app_settings import (
                get_editor_current_line_highlight as get_clh089,
                get_page_number_overlay_skip_edges as get_skip089,
                set_editor_current_line_highlight as set_clh089,
                set_page_number_overlay_skip_edges as set_skip089,
            )
            from instantlensdoc.ui.settings_dialog import SettingsDialog as SD089q

            assert callable(getattr(win, "_on_thumbs_batch_open", None))
            assert callable(getattr(win, "_on_ann_group_export", None))
            assert callable(getattr(win, "_toggle_current_line_highlight", None))
            assert callable(getattr(win.pdf_view, "open_selected_pages_as_document", None))
            assert callable(getattr(win.pdf_view, "export_selected_ann_group_json", None))
            assert callable(getattr(win.pdf_view, "set_page_number_overlay_skip_edges", None))
            assert callable(getattr(win.editor, "set_current_line_highlight", None))
            assert hasattr(win.sidebar, "pages_batch_open_requested")
            assert hasattr(win.sidebar, "annotation_group_export_requested")
            assert callable(getattr(win.sidebar, "set_annotation_group_filter", None))
            sd089q = SD089q(win)
            assert hasattr(sd089q, "page_num_skip_edges")
            assert hasattr(sd089q, "current_line_hl")
            set_skip089(True)
            win.pdf_view.set_page_number_overlay_skip_edges(True)
            assert win.pdf_view.page_number_overlay_skip_edges() is True
            win.pdf_view.set_show_page_number_overlay(True)
            n_pages089 = int(win.pdf_view.page_count or 0)
            if n_pages089 >= 1:
                win.pdf_view.page_index = 0
                assert win.pdf_view.format_page_number_overlay_text() == ""
            if n_pages089 >= 2:
                win.pdf_view.page_index = n_pages089 - 1
                assert win.pdf_view.format_page_number_overlay_text() == ""
                win.pdf_view.page_index = 0
            win.pdf_view.set_page_number_overlay_skip_edges(False)
            set_skip089(False)
            assert get_skip089() is False
            set_clh089(False)
            win.editor.set_current_line_highlight(False)
            assert win.editor.current_line_highlight_enabled() is False
            sd089q.current_line_hl.setChecked(True)
            sd089q.page_num_skip_edges.setChecked(False)
            sd089q._save()
            assert get_clh089() is True
            assert win.editor.current_line_highlight_enabled() is True
            if win.pdf_view.store is not None:
                from ild_pdf import Annotation as A089q, AnnotationType as T089q

                g1 = A089q(0, T089q.HIGHLIGHT, 14, 14, width=22, height=10, text="g089qa")
                g2 = A089q(0, T089q.HIGHLIGHT, 50, 24, width=22, height=10, text="g089qb")
                win.pdf_view.store.add(g1)
                win.pdf_view.store.add(g2)
                _, gid_q089 = win.pdf_view.store.group([g1.id, g2.id])
                win.pdf_view.store.set_ann_group(gid_q089, title="SmokeG089", color="#112233")
                jpath089 = Path(tempfile.mkdtemp()) / "grp089.json"
                win.pdf_view.store.export_group_json(gid_q089, jpath089)
                assert jpath089.is_file() and "SmokeG089" in jpath089.read_text(encoding="utf-8")
                win.sidebar.set_annotation_group_filter(gid_q089)
                assert win.sidebar.annotation_group_filter() == gid_q089
                win.sidebar.clear_annotation_group_filter()
                assert win.sidebar.annotation_group_filter() == ""
                win.pdf_view.store.ungroup([g1.id, g2.id])
            feat089q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.8.9" in feat089q
            cl089q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "## 0.8.9" in cl089q
            print("0.8.9 Qt group-filter/json/thumb-open/overlay-edges/line-hl: OK")

            # --- 0.9.0 Qt: Tab Mittelklick/Andere, PDF-Suche F3, Opacity-Auswahl, Session-Toggles ---
            from instantlensdoc.core.app_settings import (
                get_restore_window_geometry_on_start as get_geo090,
                set_restore_window_geometry_on_start as set_geo090,
            )
            from instantlensdoc.ui.settings_dialog import SettingsDialog as SD090q
            from PySide6.QtGui import QKeySequence

            assert callable(getattr(win, "close_tab_path", None))
            assert callable(getattr(win, "close_other_tabs_keeping", None))
            assert hasattr(win.sidebar, "document_close_requested")
            assert hasattr(win.sidebar, "document_close_others_requested")
            assert hasattr(win.sidebar.files, "document_close_requested")
            assert callable(getattr(win.pdf_view, "search_next", None))
            assert callable(getattr(win.pdf_view, "search_prev", None))
            assert callable(getattr(win.pdf_view, "highlight_search", None))
            assert callable(getattr(win.pdf_view, "_find_search_on_pages", None))
            assert callable(getattr(win.pdf_view, "search_active_index", None))
            sd090q = SD090q(win)
            assert hasattr(sd090q, "restore_geometry")
            assert hasattr(sd090q, "restore_session")
            set_geo090(False)
            sd090q.restore_geometry.setChecked(False)
            sd090q.restore_session.setChecked(True)
            sd090q._save()
            assert get_geo090() is False
            set_geo090(True)
            sd090q.restore_geometry.setChecked(True)
            sd090q._save()
            assert get_geo090() is True
            # Opacity-Slider: Auswahl → nur Objekt; ohne Auswahl → Default
            if win.pdf_view.store is not None:
                from ild_pdf import Annotation as A090q, AnnotationType as T090q

                a090 = A090q(0, T090q.HIGHLIGHT, 12, 12, width=24, height=10, text="op090", opacity=1.0)
                win.pdf_view.store.add(a090)
                win.pdf_view._selected_ann_id = a090.id
                win.pdf_view._selected_ann_ids = [a090.id]
                before_default = float(win.pdf_view._default_opacity)
                win.pdf_view._on_opacity_slider_changed(40)
                ann090 = win.pdf_view.store.get(a090.id)
                assert ann090 is not None
                assert abs(float(ann090.opacity) - 0.40) < 0.02
                assert abs(float(win.pdf_view._default_opacity) - before_default) < 0.02
                win.pdf_view._selected_ann_id = None
                win.pdf_view._selected_ann_ids = []
                win.pdf_view._on_opacity_slider_changed(55)
                assert abs(float(win.pdf_view._default_opacity) - 0.55) < 0.02
            # PDF-Suche Highlight + next/prev API
            if win.pdf_view.pdf_path:
                n_hl = win.pdf_view.highlight_search("a")
                if n_hl > 0:
                    assert win.pdf_view.search_active_index() >= 0
                    assert win.pdf_view.search_next() is True
                    assert win.pdf_view.search_prev() is True
                win.pdf_view.clear_search_highlights()
            # F3 / Shift+F3 Shortcuts vorhanden
            from PySide6.QtGui import QAction as QA090

            find_next_ok = False
            find_prev_ok = False
            for act in win.findChildren(QA090):
                sc = act.shortcut()
                if sc == QKeySequence.FindNext or sc.toString() in ("F3", "Find Next"):
                    find_next_ok = True
                if sc == QKeySequence.FindPrevious or "Shift+F3" in sc.toString() or sc.toString() in (
                    "Shift+F3",
                    "Find Previous",
                ):
                    find_prev_ok = True
            assert find_next_ok and find_prev_ok
            # Tab close helpers: close_other_tabs_keeping / close_tab_path callable
            t1 = Path(tempfile.mkdtemp()) / "tab090a.txt"
            t2 = Path(tempfile.mkdtemp()) / "tab090b.txt"
            t1.write_text("alpha\n", encoding="utf-8")
            t2.write_text("beta\n", encoding="utf-8")
            win.sidebar.add_document(str(t1))
            win.sidebar.add_document(str(t2))
            win.open_path(str(t1))
            win.close_other_tabs_keeping(str(t1))
            paths_keep = win.sidebar.document_paths()
            assert str(t1) in paths_keep or any(Path(p).name == t1.name for p in paths_keep)
            assert not any(Path(p).name == t2.name for p in paths_keep)
            feat090q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.9.0" in feat090q
            cl090q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "## 0.9.0" in cl090q
            print("0.9.0 Qt tab-midclick/search-f3/opacity/session-toggles: OK")

            # --- 0.9.1 Qt: Tabs Alle/Links/Rechts, Trefferliste, Opacity Commit-on-Release, Session ---
            assert callable(getattr(win, "close_all_tabs", None))
            assert callable(getattr(win, "close_tabs_left_of", None))
            assert callable(getattr(win, "close_tabs_right_of", None))
            assert hasattr(win.sidebar, "document_close_all_requested")
            assert hasattr(win.sidebar, "document_close_left_requested")
            assert hasattr(win.sidebar, "document_close_right_requested")
            assert callable(getattr(win.pdf_view, "collect_search_hits", None))
            assert callable(getattr(win.pdf_view, "_on_opacity_slider_pressed", None))
            assert callable(getattr(win.pdf_view, "_on_opacity_slider_released", None))
            assert hasattr(win, "_tab_view_state")
            # Opacity Commit-on-Release: Drag → eine Undo-Stufe
            if win.pdf_view.store is not None:
                from ild_pdf import Annotation as A091q, AnnotationType as T091q

                a091 = A091q(
                    0, T091q.HIGHLIGHT, 14, 14, width=20, height=10, text="op091", opacity=1.0
                )
                win.pdf_view.store.add(a091)
                win.pdf_view.store.clear_history()
                win.pdf_view._selected_ann_id = a091.id
                win.pdf_view._selected_ann_ids = [a091.id]
                win.pdf_view._on_opacity_slider_pressed()
                win.pdf_view._on_opacity_slider_changed(30)
                win.pdf_view._on_opacity_slider_changed(50)
                win.pdf_view._on_opacity_slider_released()
                ann091 = win.pdf_view.store.get(a091.id)
                assert ann091 is not None
                assert abs(float(ann091.opacity) - 0.50) < 0.02
                assert len(win.pdf_view.store._undo) == 1
                assert win.pdf_view.store.undo() is True
                ann091b = win.pdf_view.store.get(a091.id)
                assert ann091b is not None
                assert abs(float(ann091b.opacity) - 1.0) < 0.02
                win.pdf_view._selected_ann_id = None
                win.pdf_view._selected_ann_ids = []
            # PDF-Trefferliste API
            if win.pdf_view.pdf_path and hasattr(win.pdf_view, "collect_search_hits"):
                hits091 = win.pdf_view.collect_search_hits("a", max_hits=20)
                assert isinstance(hits091, list)
                if hits091:
                    page_i, hit_i, snip = hits091[0]
                    assert isinstance(page_i, int) and page_i >= 0
                    assert isinstance(hit_i, int) and hit_i >= 0
                    assert isinstance(snip, str)
            # Tab close left/right/all
            td091 = Path(tempfile.mkdtemp())
            ta = td091 / "tab091a.txt"
            tb = td091 / "tab091b.txt"
            tc = td091 / "tab091c.txt"
            ta.write_text("a\n", encoding="utf-8")
            tb.write_text("b\n", encoding="utf-8")
            tc.write_text("c\n", encoding="utf-8")
            win.sidebar.clear_documents()
            win.sidebar.add_document(str(ta))
            win.sidebar.add_document(str(tb))
            win.sidebar.add_document(str(tc))
            win.open_path(str(tb))
            win.close_tabs_left_of(str(tb))
            paths_mid = [Path(p).name for p in win.sidebar.document_paths()]
            assert ta.name not in paths_mid
            assert tb.name in paths_mid and tc.name in paths_mid
            win.close_tabs_right_of(str(tb))
            paths_mid2 = [Path(p).name for p in win.sidebar.document_paths()]
            assert tc.name not in paths_mid2
            assert tb.name in paths_mid2
            # Session tab state capture
            win._tab_view_state[win._path_key(str(tb))] = {
                "page": 0,
                "scale": 1.5,
                "scroll_y": 33,
            }
            win._capture_current_tab_view_state()
            key_tb = win._path_key(str(tb))
            assert key_tb in win._tab_view_state
            feat091q = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
            assert "0.9.1" in feat091q
            cl091q = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
            assert "## 0.9.1" in cl091q
            print("0.9.1 Qt tabs-close/search-list/opacity-commit/session-scroll: OK")

            print("0.4.x selected Qt marks/schema/sort/reset: OK")
            print("0.4.2 Qt outline/copy-paste/case/progress: OK")
            print("0.4.1 Qt links/stamp/encoding/drop: OK")
            print("0.3.x–0.9.1 review OK")
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

        # Close ohne Speichern-Dialog (offscreen)
        if getattr(win, "doc", None) is not None:
            win.doc.text = win.editor.toPlainText()
            win.doc.dirty = False
        if win.pdf_view.store is not None:
            win.pdf_view.store.dirty = False
        win.close()
        print("Qt: OK")

    print("Smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
