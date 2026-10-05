#!/usr/bin/env python3
"""Offscreen End-to-End-Audit 2.6.53 — PDFium-Ladefehler + DOCX-Layout.

Feldbefunde 2.6.52 (Windows), die hier reproduziert und als behoben bewiesen werden:

1. Banner „PDF-Öffnung fehlgeschlagen: Failed to load document (PDFium: Data
   format error)“ obwohl pikepdf/Textsuche die Datei lesen:
   a) Windows-Pfadproblem (``FPDF_LoadDocument`` → ``CreateFileA`` mit UTF-8-Bytes):
      simuliert per Monkeypatch — Pfad-Open schlägt fehl, Bytes-Open funktioniert.
      Datei mit Umlauten/Leerzeichen im Pfad öffnet über ``MainWindow.open_path``.
   b) Beschädigte/unvollständige PDF (abgeschnittener Trailer): PDFium lehnt ab,
      pikepdf repariert → Seite sichtbar, Statushinweis.
   c) Totalausfall (0-Byte-Datei): Banner nennt jeden Schritt, die exakte Exception
      und die pypdfium2-/PDFium-Version.
   d) PDFium wird **nie** aus einem Worker-Thread aufgerufen (Passwort-Probe,
      Seitenanzahl-Refresh) — parallel zum Render korrumpierte das den Parser.
2. DOCX überbreit / „Formatierung verloren“: Rich-Dokumente brechen am
   Spaltenrand um (auch bei Wortumbruch=aus), horizontaler Scroll = 0,
   proportionale Standardschrift statt Editor-Monospace; TXT danach wieder
   Monospace + Einstellung.
3. Seitenlayout: Menü/Ribbon/Palette-Aktion, Dialog mit DTP-Presets, ändert
   ``QTextDocument.pageSize`` und die Spaltenbreite (Viewport) des Editors.

Aufruf: ``QT_QPA_PLATFORM=offscreen python3 scripts/test_ui_audit_2653.py``
"""

from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["ILD_SMOKE_QT"] = "1"
os.environ.setdefault("ILD_SKIP_DEPS_CHECK", "1")
# Isolierte Settings: Test darf Nutzer-Einstellungen (Wortumbruch/Seitenlayout) nicht verändern
os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp(prefix="ild-audit-2653-cfg-")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from test_pdf_canvas_not_blank import _make_multipage_pdf, _nonwhite_count  # noqa: E402
from test_ui_audit_2652 import _pump  # noqa: E402


def _make_wide_docx(path: Path, *, font: str | None = None) -> None:
    from docx import Document

    d = Document()
    d.add_heading("Gesamtbuch — Kapitel 1", level=1)
    for i in range(4):
        p = d.add_paragraph()
        r = p.add_run(f"Absatz {i + 1}: " + "Dies ist ein sehr langer Fließtextabsatz ohne Zeilenumbruch. " * 25)
        if font and i == 1:
            r.font.name = font
    d.save(str(path))


def _record_pdfium_threads(monkey_box: dict):
    """pypdfium2.PdfDocument so patchen, dass der aufrufende Thread protokolliert wird."""
    import pypdfium2 as pdfium

    real = monkey_box.setdefault("real", pdfium.PdfDocument)
    calls: list[str] = monkey_box.setdefault("threads", [])

    class _Recording(real):  # type: ignore[misc,valid-type]
        def __init__(self, input, password=None, autoclose=False):
            calls.append(threading.current_thread().name)
            super().__init__(input, password=password, autoclose=autoclose)

    pdfium.PdfDocument = _Recording
    return calls


def _patch_pdfium_path_fails(monkey_box: dict):
    """Windows-Simulation: str/Path-Input → „Data format error“, Bytes funktionieren."""
    import pypdfium2 as pdfium
    from pypdfium2 import PdfiumError

    real = monkey_box.setdefault("real", pdfium.PdfDocument)

    class _WinLike(real):  # type: ignore[misc,valid-type]
        def __init__(self, input, password=None, autoclose=False):
            if isinstance(input, (str, Path)):
                raise PdfiumError("Failed to load document (PDFium: Data format error).")
            super().__init__(input, password=password, autoclose=autoclose)

    pdfium.PdfDocument = _WinLike


def _restore_pdfium(monkey_box: dict) -> None:
    import pypdfium2 as pdfium

    real = monkey_box.get("real")
    if real is not None:
        pdfium.PdfDocument = real


def main() -> int:  # noqa: C901 - ein Skript, bewusst linear
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QDialog, QPlainTextEdit

    from ild_pdf.pdfium_open import (
        PdfiumOpenError,
        clear_pdfium_bytes_cache,
        last_open_step,
        open_pdfium,
        pdfium_version_info,
    )
    from ild_pdf.security import needs_password
    from instantlensdoc.license import LicenseManager
    from instantlensdoc.ui.main_window import MainWindow
    from instantlensdoc.ui.ribbon_bar import RibbonBar

    app = QApplication.instance() or QApplication([])
    lm = LicenseManager()
    lm.ensure_trial_started()
    win = MainWindow(lm)
    win.resize(1600, 900)
    win.show()
    _pump(app, 0.2)
    pv = win.pdf_view
    box: dict = {}

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        # Pfad mit Umlauten, ß, Leerzeichen, Klammern — wie D:\Dokumente\Übung …
        udir = tdp / "Übungs Ordner ß" / "Dünning-Krüger (1)"
        udir.mkdir(parents=True)
        upath = udir / "Dünning_Krüger_Effekt (1).pdf"
        pages = ["SeiteEinsAAA", "SeiteZweiBBB", "SeiteDreiCCC"]
        _make_multipage_pdf(upath, pages)

        # ---- 1a) Windows-Simulation: Pfad-Open scheitert, Bytes retten ---------
        _patch_pdfium_path_fails(box)
        try:
            clear_pdfium_bytes_cache()
            doc = open_pdfium(upath)
            assert len(doc) == len(pages), f"Bytes-Open liefert {len(doc)} Seiten"
            doc.close()
            assert last_open_step(upath) == "bytes", f"Schritt {last_open_step(upath)!r} statt bytes"
            win.open_path(str(upath))
            _pump(app, 2.0, until=lambda: int(pv.page_count or 0) >= len(pages))
            assert win.stack.currentWidget() is pv, "Stack zeigt nach PDF-Open nicht den PdfViewer"
            assert pv._canvas_has_page_image(), (
                f"Canvas ohne Seitenbild bei simuliertem Windows-Pfadfehler: err={pv._last_refresh_error!r}"
            )
            assert not bool(getattr(pv, "_blank_view_fallback_active", False)), "Fallback-Banner statt Seite"
            assert int(pv.page_count) == len(pages), f"page_count={pv.page_count} statt {len(pages)}"
            pv.next_page()
            _pump(app, 0.3)
            assert pv.page_index == 1 and pv._canvas_has_page_image(), "Seite 2 ohne Bild (Windows-Simulation)"
            thumbs = win.sidebar.thumbs
            _pump(app, 2.0, until=lambda: thumbs.count() >= len(pages))
            assert thumbs.count() == len(pages), f"Thumbs: {thumbs.count()} statt {len(pages)}"
            print("OK  1a umlaut path via bytes (Windows-Simulation):", upath.name)
        finally:
            _restore_pdfium(box)

        # ---- 1b) Beschädigte PDF → pikepdf-Reparatur -----------------------------
        good = tdp / "intakt.pdf"
        _make_multipage_pdf(good, ["Repariert", "Zwei"])
        raw = good.read_bytes()
        broken = tdp / "abgeschnitten (Download unvollständig).pdf"
        broken.write_bytes(raw[: int(len(raw) * 0.8)])
        try:
            import pypdfium2 as pdfium

            pdfium.PdfDocument(broken)
            raise AssertionError("Testdatei wird von PDFium akzeptiert — Reparaturpfad nicht geprüft")
        except Exception as e:
            assert "Data format error" in str(e), f"Unerwarteter PDFium-Fehler: {e}"
        doc = open_pdfium(broken)
        assert len(doc) >= 1, "Reparatur ohne Seiten"
        doc.close()
        assert last_open_step(broken) == "pikepdf-repair", last_open_step(broken)
        status_seen: list[str] = []
        pv.status.connect(status_seen.append)
        win.open_path(str(broken))
        _pump(app, 1.0)
        assert pv._canvas_has_page_image(), f"Reparierte PDF ohne Seitenbild: {pv._last_refresh_error!r}"
        assert any("repariert" in s.lower() for s in status_seen), (
            f"Kein Reparatur-Hinweis in der Statusleiste: {status_seen[-5:]}"
        )
        pv.status.disconnect(status_seen.append)
        print("OK  1b damaged pdf repaired via pikepdf")

        # ---- 1c) Totalausfall → Banner mit Schritten, Exception, Versionen -------
        # Kaputtes PDF mit echtem Header: alle drei Parser-Schritte scheitern.
        # (0-Byte-Dateien stoppen seit 2.6.54 schon in Schritt 0 — siehe test_ui_audit_2654.)
        empty = tdp / "leer.pdf"
        empty.write_bytes(b"%PDF-1.4\n" + b"\x00garbage" * 64 + b"\n%%EOF\n")
        try:
            open_pdfium(empty)
            raise AssertionError("Schrott-PDF wurde geöffnet")
        except PdfiumOpenError as e:
            msg = str(e)
            for need in ("Schritt 1", "Schritt 2", "Schritt 3", "pypdfium2", "Data format error", "leer.pdf"):
                assert need in msg, f"Fehlertext ohne {need!r}:\n{msg}"
            assert [s for s, _ in e.steps] == ["bytes", "path", "pikepdf-repair"], e.steps
        assert "pypdfium2" in pdfium_version_info() and "PDFium" in pdfium_version_info()
        win.open_path(str(empty))
        _pump(app, 0.8)
        err = str(getattr(pv, "_last_refresh_error", "") or "")
        assert "pypdfium2" in err and "Schritt 1" in err and "Data format error" in err, (
            f"Banner/Fehlertext ohne Diagnose: {err!r}"
        )
        assert bool(getattr(pv, "_blank_view_fallback_active", False)), "Kein sichtbares Banner bei Totalausfall"
        grab = pv.canvas.grab().toImage()
        assert _nonwhite_count(grab, 10) >= 50, "Banner-Canvas fast weiß"
        print("OK  1c total failure → diagnostic banner")

        # ---- 1d) Kein PDFium aus Worker-Threads ----------------------------------
        calls = _record_pdfium_threads(box)
        try:
            clear_pdfium_bytes_cache()
            assert needs_password(good) is False
            win.open_path(str(good))
            _pump(app, 1.5, until=lambda: int(pv.page_count or 0) >= 2)
            assert int(pv.page_count) == 2, f"page_count={pv.page_count}"
            _pump(app, 0.5)
            offenders = sorted({t for t in calls if t != threading.main_thread().name})
            assert calls, "PDFium wurde gar nicht aufgerufen (Patch greift nicht)"
            assert not offenders, f"PDFium aus Worker-Threads aufgerufen: {offenders}"
        finally:
            _restore_pdfium(box)
        print(f"OK  1d pdfium only on GUI thread ({len(calls)} Aufrufe)")

        # ---- 2) DOCX: Umbruch + proportionale Schrift ----------------------------
        from instantlensdoc.core.app_settings import set_editor_soft_wrap

        ed = win.editor
        set_editor_soft_wrap(False)
        ed.set_soft_wrap(False)  # Nutzer hat Wortumbruch aus (Feld: horizontaler Scroll)
        docx_path = tdp / "Full_Read_Gesamtbuch.docx"
        _make_wide_docx(docx_path, font="Arial")
        win.open_path(str(docx_path))
        _pump(app, 0.4)
        assert win.stack.currentWidget() is win.editor_pane
        assert ed.lineWrapMode() == QPlainTextEdit.WidgetWidth, "DOCX ohne Zeilenumbruch (NoWrap)"
        assert ed.horizontalScrollBar().maximum() == 0, (
            f"DOCX horizontal scrollbar max={ed.horizontalScrollBar().maximum()} — Absätze überbreit"
        )
        assert ed.document().lineCount() > ed.blockCount() + 4, "Absätze werden nicht umbrochen"
        fam = ed.document().defaultFont().family()
        assert fam.lower() not in {"consolas", "monospace", "courier new"}, f"DOCX in Editor-Monospace {fam!r}"
        assert ed.document().defaultFont().styleHint() != ed.font().styleHint() or fam != ed.font().family()
        ps = ed.document().pageSize()
        assert ps.width() > 0 and abs(ps.width() - 595.28 * 96 / 72) < 2.0, f"pageSize A4 erwartet, ist {ps}"
        lay = ed.page_layout()
        assert lay is not None and ed.page_layout_active(), "Seitenlayout für DOCX nicht aktiv"
        col = ed.page_column_width_px()
        exp = lay.text_width_px(96.0)
        assert abs(col - exp) <= 24, f"Spaltenbreite {col}px ≠ Textbreite {exp:.0f}px (A4 minus Ränder)"
        # Run-Schriftart aus DOCX kommt an (Arial) — Formatierung „verloren“ war Font-Fallback
        html = ed.to_rich_html()
        assert "Arial" in html, "Run-Schriftart (Arial) nicht im Editor-HTML"
        assert "<pre" not in html.lower(), "Editor-HTML mit <pre> (Umbruch-Killer)"
        grab = ed.grab().toImage()
        assert _nonwhite_count(grab, 6) > 50, "Editor grab() leer"
        # Roundtrip DOCX → Schriftart bleibt
        out = tdp / "roundtrip.docx"
        win.doc.path = out
        assert win.save_doc(), "DOCX speichern fehlgeschlagen"
        from docx import Document as DocxDocument

        dd = DocxDocument(str(out))
        fonts = {r.font.name for p in dd.paragraphs for r in p.runs if r.font.name}
        assert "Arial" in fonts, f"Schriftart nach Roundtrip verloren: {fonts}"
        print(f"OK  2 docx wraps at page column ({col}px), font {fam!r}, pageSize {ps.width():.0f}px")

        # TXT danach: Einstellung (Wortumbruch aus) + Monospace zurück, kein Seitenlayout (scope rich)
        txt = tdp / "plain.txt"
        txt.write_text("x " * 400 + "\n", encoding="utf-8")
        win.open_path(str(txt))
        _pump(app, 0.3)
        assert ed.lineWrapMode() == QPlainTextEdit.NoWrap, "TXT ignoriert Wortumbruch=aus"
        assert ed.document().defaultFont().family() == ed.font().family(), "TXT nicht in Editor-Schrift"
        assert ed.document().pageSize().width() < 0, "Seitenlayout bleibt an TXT kleben (scope rich)"
        assert not ed.page_layout_active()
        set_editor_soft_wrap(True)
        ed.set_soft_wrap(True)
        print("OK  2b txt restores monospace + wrap setting")

        # ---- 3) Seitenlayout-Dialog + Aktionen ----------------------------------
        from instantlensdoc.ui.page_layout_dialog import PageLayoutDialog

        act = win.findChild(type(win._page_layout_action), "actPageLayout")
        assert act is not None, "Menüaktion Seitenlayout fehlt"
        rb = win.findChild(RibbonBar)
        assert rb is not None and "page_layout" in rb._actions, "Ribbon ohne Seitenlayout-Button"
        from instantlensdoc.ui.command_palette import PaletteCommand  # noqa: F401

        dlg = PageLayoutDialog(ed.page_layout(), win, rich_document=False)
        idx = dlg.preset.findData("US Letter")
        assert idx >= 0, [dlg.preset.itemData(i) for i in range(dlg.preset.count())]
        dlg.preset.setCurrentIndex(idx)
        dlg.rb_landscape.setChecked(True)
        dlg.scope.setCurrentIndex(dlg.scope.findData("all"))
        dlg.m_left.setValue(20.0)
        dlg.m_right.setValue(20.0)
        lay2 = dlg.result_layout()
        assert lay2.preset == "US Letter" and lay2.orientation == "landscape" and lay2.scope == "all", lay2.describe()
        w_pt, h_pt = lay2.page_size_pt()
        assert abs(w_pt - 792.0) < 0.1 and abs(h_pt - 612.0) < 0.1, (w_pt, h_pt)
        before = ed.document().pageSize()
        lay2.save()
        ed.set_page_layout(lay2)
        _pump(app, 0.2)
        after = ed.document().pageSize()
        assert abs(after.width() - 792.0 * 96 / 72) < 2.0 and abs(after.height() - 612.0 * 96 / 72) < 2.0, (
            f"pageSize nicht geändert: {before} → {after}"
        )
        assert ed.page_layout_active(), "scope=all gilt nicht für TXT"
        col2 = ed.page_column_width_px()
        exp2 = lay2.text_width_px(96.0)
        assert abs(col2 - exp2) <= 24, f"Spalte {col2}px ≠ {exp2:.0f}px (Letter quer minus 20/20 mm)"
        assert ed.horizontalScrollBar().maximum() == 0
        # Satzspiegel-Vorschlag (DTP) füllt Ränder
        dlg2 = PageLayoutDialog(lay2, win, rich_document=True)
        dlg2.preset.setCurrentIndex(dlg2.preset.findData("A4"))
        dlg2._apply_satzspiegel()
        lay3 = dlg2.result_layout()
        assert lay3.preset == "A4" and lay3.margin_left_mm > 0 and lay3.margin_top_mm > 0, lay3.describe()
        # Dialog über Ribbon-Aktion öffnen und automatisch schließen
        opened: list[str] = []

        def _close_modal() -> None:
            w = QApplication.activeModalWidget()
            if isinstance(w, QDialog):
                opened.append(w.objectName())
                w.reject()

        QTimer.singleShot(300, _close_modal)
        win._on_ribbon_action("page_layout")
        _pump(app, 0.2)
        assert opened == ["pageLayoutDialog"], f"Ribbon-Aktion öffnete {opened}"
        # Aus → Umbruch am Fensterrand, pageSize ungültig
        lay_off = dlg.result_layout()
        lay_off.scope = "off"
        lay_off.enabled = False
        ed.set_page_layout(lay_off)
        _pump(app, 0.1)
        assert not ed.page_layout_active() and ed.document().pageSize().width() < 0
        assert ed.page_column_width_px() > col2, "Spalte wächst nach Layout=aus nicht auf Fensterbreite"
        print(f"OK  3 page layout dialog: Letter quer → pageSize {after.width():.0f}×{after.height():.0f}px, Spalte {col2}px")

    assert not win._current_is_dirty(), "Dokument vor close() unerwartet dirty"
    win.close()
    print("OK test_ui_audit_2653")
    return 0


if __name__ == "__main__":
    import faulthandler

    faulthandler.dump_traceback_later(240, exit=True)
    raise SystemExit(main())
