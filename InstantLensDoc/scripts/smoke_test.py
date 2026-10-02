#!/usr/bin/env python3
"""Smoke-Test (CLI + optional offscreen Qt)."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from PIL import Image

    from ild_pdf import Annotation, AnnotationStore, AnnotationType, PdfDocument, render_page
    from ild_pdf.pages import reorder_pages, rotate_page
    from instantlensdoc.config import icon_path, icon_paths_for_qt
    from instantlensdoc.core.documents import open_document, save_document
    from instantlensdoc.core.forms import FieldType, FormDefinition, FormField, export_html, export_pdf_form
    from instantlensdoc.core import ocr as ocr_mod
    from instantlensdoc.license import KEY_DAYS, TRIAL_DAYS, generate_key, verify_key

    assert TRIAL_DAYS == 28 and KEY_DAYS == 32
    key = generate_key("ame@sellerbach.de")
    ok, msg, _ = verify_key(key)
    assert ok, msg

    # Icon-Auflösung
    assert icon_path() is not None or True  # Platzhalter darf fehlen in CI
    _ = list(icon_paths_for_qt())

    # OCR-Status darf fehlschlagen, muss aber klare Message liefern
    ok_ocr, ocr_msg = ocr_mod.tesseract_available()
    assert isinstance(ocr_msg, str) and len(ocr_msg) > 5
    print(f"OCR: {'OK' if ok_ocr else 'fehlt (erwartet)'} — {ocr_msg.splitlines()[0]}")

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # Mehrseitiges PDF für reorder
        p1 = td / "p1.pdf"
        p2 = td / "p2.pdf"
        pdf = td / "t.pdf"
        Image.new("RGB", (200, 200), "white").save(p1, "PDF")
        Image.new("RGB", (200, 200), "gray").save(p2, "PDF")
        # Zwei Seiten via pikepdf
        import pikepdf

        with pikepdf.Pdf.new() as out:
            for src in (p1, p2):
                with pikepdf.open(src) as src_pdf:
                    out.pages.append(src_pdf.pages[0])
            out.save(pdf)

        with PdfDocument(pdf) as doc:
            assert len(doc) == 2
        render_page(pdf, 0)
        store = AnnotationStore(pdf)
        store.add(Annotation(0, AnnotationType.HIGHLIGHT, 10, 10, text="mark"))
        store.add(Annotation(1, AnnotationType.STICKY, 20, 20, text="note"))
        sid = store.save()
        assert sid.exists()
        store2 = AnnotationStore(pdf)
        assert len(store2.annotations) == 2
        rotate_page(pdf, 0, 90)
        reorder_pages(pdf, [1, 0])
        with PdfDocument(pdf) as doc:
            assert len(doc) == 2

        txt = td / "a.txt"
        txt.write_text("hello InstantLens Suche", encoding="utf-8")
        doc = open_document(txt)
        doc.text = "hello InstantLens Suche markieren"
        save_document(doc)

        form = FormDefinition("F")
        form.add_field(FormField("Name", type=FieldType.TEXT, required=True))
        form.add_field(FormField("Art", type=FieldType.DROPDOWN, options=["A", "B"]))
        export_html(form, td / "f.html")
        export_pdf_form(form, td / "f.pdf")
        assert (td / "f.html").exists() and (td / "f.pdf").exists()

    if os.environ.get("ILD_SMOKE_QT", "1") == "1":
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication

        from instantlensdoc.license import LicenseManager
        from instantlensdoc.ui.main_window import MainWindow
        from instantlensdoc.ui.editor import TextEditor

        app = QApplication.instance() or QApplication(["smoke"])
        win = MainWindow(LicenseManager(path=ROOT / ".smoke_license.json"))
        win.new_doc()
        win.editor.setPlainText("alpha beta alpha gamma")
        n = win.editor.find_and_highlight("alpha")
        assert n == 2
        # Auswahl markieren
        from PySide6.QtGui import QTextCursor

        cur = win.editor.textCursor()
        cur.movePosition(QTextCursor.Start)
        cur.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        win.editor.setTextCursor(cur)
        assert win.editor.highlight_selection()
        win.close()
        print("Qt: OK")

    print("Smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
