#!/usr/bin/env python3
"""Offscreen End-to-End 2.6.54 — ungültiges Save-As-PDF, Diagnose, Minimap, Undo.

Feldbefund 2.6.53 (Windows): ``Dunning_Kruger_Effekt_1.pdf`` (25 226 Byte)
``PK 03 04`` = unverändertes Word-DOCX (Application: Microsoft Office Word).
Ursache: ≤ 2.6.42 ``save_document`` kopierte die DOCX-Bytes unter .pdf-Namen.

Dieser Test beweist:

1. Die Nutzerdatei (oder ein synthetisches DOCX-als-PDF) wird als ZIP-DOCX erkannt;
   pikepdf/PDFium scheitern; ``pdf_doctor`` Exit 1; Recover → lesbares .docx.
2. ``save_document``/Export eines geladenen DOCX nach .pdf erzeugt ``%PDF-`` + ``%%EOF``,
   pikepdf- und PDFium-öffenbar, **kein** ZIP-Header.
3. 0-Byte / HTML-mit-.pdf: Diagnosetext mit Größe + Header-Hex (Schritt 0).
4. Minimap Standard aus, Toggle in Ansicht, in DOCX unsichtbar, Textbreite zurück.
5. Tippen → Fett → Undo zweimal → Originaltext; Ribbon/Menü Rückgängig/Wiederholen.

Aufruf: ``QT_QPA_PLATFORM=offscreen python3 scripts/test_ui_audit_2654.py``
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["ILD_SMOKE_QT"] = "1"
os.environ.setdefault("ILD_SKIP_DEPS_CHECK", "1")
os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp(prefix="ild-audit-2654-cfg-")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from test_ui_audit_2652 import _pump  # noqa: E402

USER_PDF = Path(
    "/cursor/stores/bc-b08b150e-66b9-4e56-8bf8-50c583a73b7e/inbox/"
    "Dunning_Kruger_Effekt_1.pdf"
)


def _make_docx(path: Path) -> None:
    from docx import Document

    d = Document()
    d.add_heading("Dunning-Kruger-Effekt", level=1)
    d.add_paragraph("Absatz eins: " + ("Fließtext " * 40))
    p = d.add_paragraph()
    r = p.add_run("Fettkursiv")
    r.bold = True
    r.italic = True
    d.save(str(path))


def _assert_valid_pdf(path: Path, *, must_contain: str | None = None) -> None:
    from ild_pdf.pdf_sniff import validate_pdf_file

    raw = path.read_bytes()
    assert raw[:5] == b"%PDF-", f"{path.name} beginnt nicht mit %PDF- sondern {raw[:16]!r}"
    assert b"%%EOF" in raw[-4096:], f"{path.name} ohne %%EOF"
    assert not raw.startswith(b"PK"), f"{path.name} ist ZIP/DOCX mit .pdf-Endung"
    v = validate_pdf_file(path, use_pdfium=True, min_pages=1)
    assert v.ok, v.message_de()
    if must_contain:
        import pypdfium2 as pdfium

        from ild_pdf.pdfium_open import PDFIUM_LOCK

        with PDFIUM_LOCK:
            doc = pdfium.PdfDocument(raw)
            try:
                txt = " ".join(doc[0].get_textpage().get_text_range().split())
            finally:
                doc.close()
        assert must_contain.lower() in txt.lower(), f"PDF-Text ohne {must_contain!r}: {txt[:200]!r}"


def main() -> int:  # noqa: C901
    from PySide6.QtGui import QTextCursor
    from PySide6.QtWidgets import QApplication

    from ild_pdf.pdfium_open import PdfiumOpenError, open_pdfium
    from ild_pdf.pdf_sniff import (
        KIND_ZIP_DOCX,
        describe_non_pdf_de,
        recover_misnamed_file,
        sniff_file,
        validate_pdf_file,
    )
    from instantlensdoc.core.app_settings import (
        apply_one_time_migrations,
        get_editor_minimap,
        set_editor_minimap,
    )
    from instantlensdoc.core.documents import DocKind, open_document, save_document
    from instantlensdoc.license import LicenseManager
    from instantlensdoc.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    lm = LicenseManager()
    lm.ensure_trial_started()
    win = MainWindow(lm)
    win.resize(1400, 900)
    win.show()
    _pump(app, 0.3)

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)

        # ---- 1) Nutzerdatei / synthetisches DOCX-als-PDF ------------------------
        src_pdf = tdp / "Dunning_Kruger_Effekt_1.pdf"
        if USER_PDF.is_file():
            shutil.copy2(USER_PDF, src_pdf)
        else:
            real = tdp / "_src.docx"
            _make_docx(real)
            shutil.copy2(real, src_pdf)
        sn = sniff_file(src_pdf)
        assert sn.kind == KIND_ZIP_DOCX, f"erwartet zip-docx, got {sn.kind} {sn.detail}"
        assert sn.head[:2] == b"PK", sn.head_hex
        assert not sn.is_pdf_like
        msg = describe_non_pdf_de(sn)
        assert "Word-Dokument" in msg and "25" in msg or "Byte" in msg
        assert "50 4b 03 04" in sn.head_hex
        v = validate_pdf_file(src_pdf, use_pdfium=True)
        assert not v.ok
        try:
            open_pdfium(src_pdf)
            raise AssertionError("DOCX-als-PDF wurde von open_pdfium akzeptiert")
        except PdfiumOpenError as e:
            text = str(e)
            assert e.not_a_pdf and e.steps[0][0] == "header"
            assert "Schritt 0" in text and "Word-Dokument" in text
            assert "50 4b 03 04" in text
        recovered = recover_misnamed_file(src_pdf)
        assert recovered is not None and recovered.suffix == ".docx" and recovered.is_file()
        opened = open_document(src_pdf)
        assert opened.kind == DocKind.DOCX, opened.kind
        assert opened.meta.get("kind_mismatch")
        assert "Dunning" in (opened.text or "") or "Fließtext" in (opened.text or "") or len(opened.text) > 20
        print("OK  1 sniff/recover user-or-synthetic DOCX-as-PDF")

        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "pdf_doctor.py"), str(src_pdf)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 1, proc.stdout + proc.stderr
        assert "Word-Dokument" in proc.stdout or "zip-docx" in proc.stdout.lower()
        print("OK  1b pdf_doctor exit 1 on misnamed DOCX")

        # ---- 2) DOCX → Speichern unter .pdf ergibt echtes PDF -------------------
        docx_path = tdp / "quelle.docx"
        if recovered and recovered.is_file() and USER_PDF.is_file():
            shutil.copy2(recovered, docx_path)
        else:
            _make_docx(docx_path)
        doc = open_document(docx_path)
        assert doc.kind == DocKind.DOCX
        out_core = tdp / "aus_core.pdf"
        save_document(doc, out_core)
        _assert_valid_pdf(out_core, must_contain="Dunning")
        print("OK  2a save_document(DOCX → .pdf) pikepdf+pdfium", out_core.stat().st_size)

        win.open_path(str(docx_path))
        _pump(app, 0.6)
        assert win.editor.rich_mode(), "DOCX nicht im Rich-Modus"
        assert win.doc.kind == DocKind.DOCX
        from instantlensdoc.core.export import export_document

        out_ui = tdp / "aus_ui.pdf"
        html = win.editor.to_rich_html()
        export_document(
            win.editor.toPlainText(),
            out_ui,
            fmt="pdf",
            title="Dunning",
            html=html,
        )
        _assert_valid_pdf(out_ui, must_contain="Dunning")
        print("OK  2b export_document(html) → gültiges PDF")

        # save_as-Zweig: Endung .pdf + Nicht-PDF-Kind darf nie ZIP schreiben
        out_as = tdp / "save_as.pdf"
        from instantlensdoc.core.documents import save_document as sd

        sd(win.doc, out_as)
        _assert_valid_pdf(out_as, must_contain="Dunning")
        print("OK  2c save_document from loaded DOCX via .pdf target")

        # ---- 3) Diagnose 0-Byte / HTML ------------------------------------------
        empty = tdp / "leer.pdf"
        empty.write_bytes(b"")
        try:
            open_pdfium(empty)
            raise AssertionError("0-Byte geöffnet")
        except PdfiumOpenError as e:
            t = str(e)
            assert "0 Byte" in t and "Schritt 0" in t and "leer.pdf" in t
        html_as_pdf = tdp / "seite.pdf"
        html_as_pdf.write_bytes(b"<!DOCTYPE html><html><body>Hallo</body></html>")
        hsn = sniff_file(html_as_pdf)
        assert hsn.kind == "html"
        assert "3c 21 44 4f 43 54 59 50 45" in hsn.head_hex  # <!DOCTYPE
        win.open_path(str(empty))
        _pump(app, 0.6)
        err = str(getattr(win.pdf_view, "_last_refresh_error", "") or "")
        banner = " ".join(
            [
                err,
                str(getattr(win.pdf_view, "_blank_view_fallback_active", False)),
            ]
        )
        # 0-Byte bleibt PDF-Kind → Viewer + Banner (Schritt 0) oder Diagnosetext
        assert "0 Byte" in err or "Schritt 0" in err or bool(
            getattr(win.pdf_view, "_blank_view_fallback_active", False)
        ), f"keine 0-Byte-Diagnose: {err!r} banner={banner!r}"
        print("OK  3 invalid-file diagnostic (0-byte + HTML header hex)")

        # ---- 4) Minimap Standard aus + Toggle + DOCX unsichtbar -----------------
        assert get_editor_minimap() is False
        set_editor_minimap(True)
        notes = apply_one_time_migrations()
        assert get_editor_minimap() is False, f"Migration ließ Minimap an: {notes}"
        txt = tdp / "plain.txt"
        txt.write_text("Zeile eins\n" + "\n".join(f"Zeile {i}" for i in range(40)), encoding="utf-8")
        win.open_path(str(txt))
        _pump(app, 0.4)
        ed = win.editor
        assert ed.minimap_width() == 0 and not ed._minimap_area.isVisible()
        vp_off = ed.viewport().width()
        win._minimap_action.setChecked(True)
        _pump(app, 0.2)
        assert ed.minimap_visible() and ed.minimap_width() == 36 and ed._minimap_area.isVisible()
        vp_on = ed.viewport().width()
        assert vp_on < vp_off, f"Minimap stahl keine Breite: off={vp_off} on={vp_on}"
        win.open_path(str(docx_path))
        _pump(app, 0.5)
        assert ed.rich_mode()
        assert ed.minimap_width() == 0 and not ed._minimap_area.isVisible(), (
            f"Minimap neben DOCX: width={ed.minimap_width()} vis={ed._minimap_area.isVisible()}"
        )
        win._minimap_action.setChecked(False)
        _pump(app, 0.1)
        assert get_editor_minimap() is False
        print("OK  4 minimap default off, toggle, hidden in DOCX")

        # ---- 5) Undo/Redo: tippen → fett → undo ×2 ------------------------------
        win.open_path(str(txt))
        _pump(app, 0.3)
        original = ed.toPlainText()
        ed.setFocus()
        cur = ed.textCursor()
        cur.movePosition(QTextCursor.End)
        ed.setTextCursor(cur)
        cur.insertText(" mehr")
        after_type = ed.toPlainText()
        assert after_type.endswith(" mehr")
        ed.selectAll()
        assert ed.toggle_bold_selection()
        assert ed.selection_font_bold()
        assert win._undo_action.isEnabled()
        assert win.ribbon_bar.is_enabled("undo")
        assert len(win.ribbon_bar.buttons("undo")) >= 2
        win._undo()
        _pump(app, 0.05)
        # Fett weg, Text noch mit " mehr"
        assert ed.toPlainText() == after_type
        assert not ed.selection_font_bold()
        win._undo()
        _pump(app, 0.05)
        assert ed.toPlainText() == original, repr(ed.toPlainText())
        assert win._redo_action.isEnabled() and win.ribbon_bar.is_enabled("redo")
        win._redo()
        assert ed.toPlainText() == after_type
        shortcuts = [k.toString() for k in win._redo_action.shortcuts()]
        assert any("Ctrl+Y" == s or s.endswith("Y") for s in shortcuts) or "Ctrl+Y" in shortcuts
        assert any("Shift+Z" in s for s in shortcuts)
        before = ed.toPlainText()
        ed.insert_table(2, 2)
        assert "|" in ed.toPlainText()
        win._undo()
        assert ed.toPlainText() == before
        print("OK  5 undo/redo type→bold→undo×2 + table one-step + ribbon arrows")

    print("OK test_ui_audit_2654")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
