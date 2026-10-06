"""Word/SoftMaker-Chrome: Ansicht umschalten, Formatvorlagen, Tabelle, Seriendruck."""

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
from menu_smoke_lib import (  # noqa: E402
    create_main_window,
    install_headless_env,
    install_qt_hooks,
    load_state,
    pump,
    build_fixtures,
)

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtGui import QFont, QTextCursor  # noqa: E402
from PySide6.QtWidgets import QDialog  # noqa: E402


_APP = None
_WIN = None
_FIXTURES = None
_TD = None
_RESTORE = None
_HOOKS: list = []


def setup_module() -> None:
    global _APP, _WIN, _FIXTURES, _TD, _RESTORE
    install_headless_env()
    _TD = tempfile.TemporaryDirectory(prefix="ild-word-chrome-2659-")
    _FIXTURES = build_fixtures(Path(_TD.name))
    _RESTORE = install_qt_hooks(_HOOKS)
    _APP, _WIN = create_main_window()


def teardown_module() -> None:
    global _WIN, _TD, _RESTORE
    try:
        if _WIN is not None:
            _WIN.close()
    except Exception:
        pass
    if _RESTORE:
        _RESTORE()
    if _TD is not None:
        _TD.cleanup()


def test_ribbon_has_word_tabs() -> None:
    rb = _WIN.ribbon_bar
    titles = [b.text() for b in rb._cat_buttons]
    for need in (
        "Datei",
        "Start",
        "Einfügen",
        "Layout",
        "Verweise",
        "Sendungen",
        "Überprüfen",
        "Ansicht",
        "Geräte",
        "Tabellentools",
    ):
        assert need in titles, f"Ribbon-Tab fehlt: {need} in {titles}"
    src = Path(ROOT / "instantlensdoc" / "ui" / "ribbon_bar.py").read_text(encoding="utf-8")
    assert "Bearbeiten" in src
    assert "menu_click" in src


def test_chrome_modes_keep_document() -> None:
    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.1)
    marker = "Chrome-Dokument bleibt offen."
    _WIN.editor.setPlainText(marker)
    from instantlensdoc.ui.chrome import (
        CHROME_KLASSISCH,
        CHROME_KOMBINIERT,
        CHROME_RIBBON,
    )

    for mode in (CHROME_KLASSISCH, CHROME_RIBBON, CHROME_KOMBINIERT):
        _WIN._set_chrome_mode(mode)
        pump(_APP, 0.05)
        assert _WIN.editor.toPlainText() == marker
        mb = _WIN.menuBar().isVisible()
        rb = _WIN.ribbon_bar.isVisible()
        if mode == CHROME_KLASSISCH:
            assert mb and not rb
        elif mode == CHROME_RIBBON:
            assert (not mb) and rb
        else:
            assert mb and rb
    _WIN._set_chrome_mode(CHROME_KOMBINIERT)


def test_style_apply_mutates_qtextdocument() -> None:
    from instantlensdoc.ui.editor import TextEditor

    ed = TextEditor()
    ed.setPlainText("Absatz für Formatvorlage.")
    cur = ed.textCursor()
    cur.select(QTextCursor.Document)
    ed.setTextCursor(cur)
    assert ed.apply_style_paragraph("h1")
    probe = ed.textCursor()
    probe.movePosition(QTextCursor.Start)
    fmt = probe.charFormat()
    assert fmt.fontWeight() >= QFont.Bold
    assert fmt.fontPointSize() >= 16.0
    block = ed.document().firstBlock().blockFormat()
    heading = 0
    try:
        heading = int(block.headingLevel())
    except Exception:
        heading = 0
    assert heading == 1 or fmt.fontWeight() >= QFont.Bold
    ed.deleteLater()


def test_insert_2x2_qtext_table() -> None:
    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.1)
    ed = _WIN.editor
    ed.setPlainText("Vor der Tabelle")
    cur = ed.textCursor()
    cur.movePosition(QTextCursor.End)
    ed.setTextCursor(cur)
    assert ed.insert_table(2, 2)
    table = ed.current_qtext_table()
    if table is None:
        # Cursor nach insert hinter der Tabelle — zurück in die Tabelle
        cur = ed.textCursor()
        cur.movePosition(QTextCursor.Start)
        ed.setTextCursor(cur)
        # Suche QTextTable im Dokument
        from PySide6.QtGui import QTextFrame

        def _walk(frame):
            it = frame.begin()
            while not it.atEnd():
                child = it.currentFrame()
                if child is not None and child is not frame:
                    yield child
                    yield from _walk(child)
                it += 1

        found = None
        root = ed.document().rootFrame()
        for fr in _walk(root):
            if fr.__class__.__name__ == "QTextTable" or hasattr(fr, "rows"):
                try:
                    if int(fr.rows()) >= 2 and int(fr.columns()) >= 2:
                        found = fr
                        break
                except Exception:
                    continue
        table = found
    assert table is not None, "2×2 QTextTable fehlt im QTextDocument"
    assert int(table.rows()) >= 2
    assert int(table.columns()) >= 2


def test_mail_merge_dialog_opens_and_closes() -> None:
    from instantlensdoc.ui.mail_merge_dialog import MailMergeDialog

    opened = []

    def _close():
        dlg = None
        for w in _WIN.findChildren(QDialog):
            if w.objectName() == "mailMergeDialog" and w.isVisible():
                dlg = w
                break
        if dlg is not None:
            opened.append(dlg.objectName())
            dlg.reject()

    QTimer.singleShot(80, _close)
    _WIN._run_mail_merge_dialog()
    pump(_APP, 0.25)
    assert "mailMergeDialog" in opened
    dlg = MailMergeDialog(_WIN, template_text="Hallo {{Name}}")
    assert dlg.objectName() == "mailMergeDialog"
    QTimer.singleShot(50, dlg.reject)
    dlg.exec()
    dlg.deleteLater()
