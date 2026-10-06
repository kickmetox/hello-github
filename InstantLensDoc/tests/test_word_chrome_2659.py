"""Word-Chrome: Klassisch/Ribbon/Kombiniert, Tabelle, Überschrift 1, Serienbrief."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["ILD_SMOKE_QT"] = "1"
os.environ.setdefault("ILD_SKIP_DEPS_CHECK", "1")
os.environ.setdefault("ILD_NO_SESSION", "1")
os.environ.setdefault("ILD_NO_SPLASH", "1")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

sys.path.insert(0, str(ROOT / "tests"))
from menu_smoke_lib import create_main_window, install_headless_env, pump  # noqa: E402

from PySide6.QtGui import QTextCursor, QFont  # noqa: E402


_APP = None
_WIN = None
_RESTORE_HOME = None


def setup_module() -> None:
    global _APP, _WIN, _RESTORE_HOME
    _RESTORE_HOME = install_headless_env()
    _APP, _WIN = create_main_window()


def teardown_module() -> None:
    global _WIN
    _WIN = None


def test_chrome_modes_keep_document() -> None:
    win = _WIN
    app = _APP
    win.new_doc("empty")
    pump(app, 0.1)
    marker = "Chrome-Test-Dokument-2659"
    win.editor.setPlainText(marker)
    pump(app, 0.05)
    win.apply_chrome_mode("classic")
    pump(app, 0.05)
    assert win.menuBar().isVisible()
    assert not win.ribbon_bar.isVisible()
    assert win.editor.toPlainText() == marker
    win.apply_chrome_mode("ribbon")
    pump(app, 0.05)
    assert not win.menuBar().isVisible()
    assert win.ribbon_bar.isVisible()
    assert win.editor.toPlainText() == marker
    win.apply_chrome_mode("combined")
    pump(app, 0.05)
    assert win.menuBar().isVisible()
    assert win.ribbon_bar.isVisible()
    assert win.editor.toPlainText() == marker
    titles = [b.text() for b in win.ribbon_bar._cat_buttons]
    for need in (
        "Datei",
        "Start",
        "Einfügen",
        "Seitenlayout",
        "Referenzen",
        "Sendungen",
        "Überprüfen",
        "Ansicht",
    ):
        assert need in titles, f"Ribbon-Tab fehlt: {need}"
    assert win.ribbon_bar.category_count() >= 8


def test_insert_table_and_heading1() -> None:
    win = _WIN
    app = _APP
    win.new_doc("empty")
    pump(app, 0.1)
    ed = win.editor
    ed.setPlainText("Ueberschrift eins\nZweiter Absatz")
    pump(app, 0.05)
    cur = ed.textCursor()
    cur.setPosition(0)
    cur.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
    ed.setTextCursor(cur)
    assert ed.apply_style_paragraph("h1")
    probe = ed._selection_probe_format(ed.textCursor())
    assert probe.fontPointSize() >= 16
    assert probe.fontWeight() >= QFont.Bold
    ed._ensure_rich_mode()
    cur = ed.textCursor()
    cur.movePosition(QTextCursor.End)
    ed.setTextCursor(cur)
    assert ed.insert_table(2, 3, rich=True)
    table = ed.current_qtext_table()
    assert table is not None
    assert table.rows() >= 2
    assert table.columns() == 3
    assert ed.add_table_row()
    assert table.rows() >= 3
    assert ed.set_table_header_row(True)
    assert ed.set_table_borders(width=1.0)
    assert ed.set_table_cell_align("center")


def test_mail_merge_two_row_csv(tmp_path: Path) -> None:
    from instantlensdoc.core.mail_merge import mail_merge_from_files, load_recipients

    tpl = tmp_path / "brief.txt"
    tpl.write_text("Hallo {{Name}}, Ort {{Ort}}.", encoding="utf-8")
    csv = tmp_path / "empf.csv"
    csv.write_text("Name,Ort\nAnna,Berlin\nBen,Hamburg\n", encoding="utf-8")
    rows = load_recipients(csv)
    assert len(rows) == 2
    out = tmp_path / "out"
    data = mail_merge_from_files(tpl, csv, out, fmt="docx", combined=False)
    assert data["count"] == 2
    files = list(Path(data["out_dir"]).glob("*"))
    assert len(files) >= 2
    texts = [p.read_bytes() for p in files if p.suffix.lower() == ".docx"]
    assert texts, "keine DOCX erzeugt"
    # PDF-Zweig
    data_pdf = mail_merge_from_files(tpl, csv, tmp_path / "pdfs", fmt="pdf", combined=True)
    assert data_pdf["files"] >= 1


def test_start_ribbon_still_has_twins() -> None:
    rb = _WIN.ribbon_bar
    for aid in ("undo", "redo", "bold", "italic", "underline", "strike", "highlight", "highlight_color"):
        assert aid in rb._actions
    src = Path(ROOT / "instantlensdoc" / "ui" / "ribbon_bar.py").read_text(encoding="utf-8")
    assert "Bearbeiten" in src
    assert "Review" in src
