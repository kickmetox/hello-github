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
    from PIL import Image, ImageDraw

    from ild_pdf import Annotation, AnnotationStore, AnnotationType, PdfDocument, render_page
    from ild_pdf.pages import rotate_page
    from instantlensdoc.core.documents import open_document, save_document
    from instantlensdoc.core.forms import FieldType, FormDefinition, FormField, export_html
    from instantlensdoc.license import KEY_DAYS, TRIAL_DAYS, generate_key, verify_key

    assert TRIAL_DAYS == 28 and KEY_DAYS == 32
    key = generate_key("ame@sellerbach.de")
    ok, msg, _ = verify_key(key)
    assert ok, msg

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        pdf = td / "t.pdf"
        Image.new("RGB", (200, 200), "white").save(pdf, "PDF")
        with PdfDocument(pdf) as doc:
            assert len(doc) == 1
        render_page(pdf, 0)
        store = AnnotationStore(pdf)
        store.add(Annotation(0, AnnotationType.TEXT, 1, 1, text="x"))
        store.save()
        rotate_page(pdf, 0, 90)
        txt = td / "a.txt"
        txt.write_text("hi", encoding="utf-8")
        doc = open_document(txt)
        doc.text = "ho"
        save_document(doc)
        form = FormDefinition("F")
        form.add_field(FormField("N", type=FieldType.TEXT))
        export_html(form, td / "f.html")

    if os.environ.get("ILD_SMOKE_QT", "1") == "1":
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication

        from instantlensdoc.license import LicenseManager
        from instantlensdoc.ui.main_window import MainWindow

        app = QApplication.instance() or QApplication(["smoke"])
        win = MainWindow(LicenseManager(path=ROOT / ".smoke_license.json"))
        win.new_doc()
        win.close()
        print("Qt: OK")

    print("Smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
