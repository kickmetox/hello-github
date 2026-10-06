"""Layout-Ribbon (Word-Seite einrichten) und Schriftfarbe in allen Bereichen."""

from __future__ import annotations

import inspect
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

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QColor, QTextCursor  # noqa: E402
from PySide6.QtWidgets import QLabel  # noqa: E402

from menu_smoke_lib import (  # noqa: E402
    build_fixtures,
    create_main_window,
    install_headless_env,
    load_state,
    pump,
)


_APP = None
_WIN = None
_TD = None
_FIXTURES = None


def setup_module() -> None:
    global _APP, _WIN, _FIXTURES, _TD
    install_headless_env()
    _TD = tempfile.TemporaryDirectory(prefix="ild-layout-color-2663-")
    _FIXTURES = build_fixtures(Path(_TD.name))
    _APP, _WIN = create_main_window()


def teardown_module() -> None:
    global _WIN, _TD
    try:
        if _WIN is not None:
            _WIN.hide()
    except Exception:
        pass
    _WIN = None
    if _TD is not None:
        try:
            _TD.cleanup()
        except Exception:
            pass
        _TD = None


def test_margin_presets_normal_schmal_breit() -> None:
    from instantlensdoc.core.editor_page_layout import EditorPageLayout, MARGIN_PRESETS

    lay = EditorPageLayout()
    lay.apply_margin_preset("schmal")
    assert abs(lay.margin_left_mm - MARGIN_PRESETS["schmal"][2]) < 0.15
    lay.apply_margin_preset("breit")
    assert abs(lay.margin_left_mm - 50.8) < 0.2
    lay.apply_margin_preset("normal")
    assert abs(lay.margin_top_mm - 25.0) < 0.2
    lay.set_margins(11.0, 12.0, 13.0, 14.0)
    assert abs(lay.margin_left_mm - 13.0) < 0.05


def test_layout_ribbon_word_page_setup_groups() -> None:
    rb = _WIN.ribbon_bar
    rb.select_tab("Layout")
    pump(_APP, 0.05)
    wrap = rb._stack.currentWidget()
    titles = [
        lab.text()
        for lab in wrap.findChildren(QLabel)
        if lab.objectName() == "ribbonGroupTitle"
    ]
    assert "Seite einrichten" in titles, titles
    assert "Absatz" in titles, titles
    assert "Anordnen" in titles, titles
    for aid in (
        "page_margins",
        "page_orientation",
        "page_size",
        "page_columns",
        "page_breaks",
        "line_numbers",
        "hyphenate",
        "paragraph",
        "indent",
        "outdent",
        "bring_forward",
        "send_backward",
        "group_frames",
        "ungroup_frames",
        "page_layout",
        "font_color",
    ):
        assert aid in rb._actions, f"Ribbon-Aktion fehlt: {aid}"
    src = Path(ROOT / "instantlensdoc" / "ui" / "ribbon_bar.py").read_text(encoding="utf-8")
    assert "Benutzerdefiniert" in src
    assert "Silbentrennung" in src
    assert "Zeilennummern" in src


def test_custom_margins_dialog_is_mm() -> None:
    from instantlensdoc.core.editor_page_layout import EditorPageLayout
    from instantlensdoc.ui.page_margins_dialog import PageMarginsDialog

    lay = EditorPageLayout()
    dlg = PageMarginsDialog(lay, _WIN)
    assert dlg.objectName() == "pageMarginsDialog"
    assert "mm" in dlg.m_left.suffix().lower()
    dlg._apply_preset("schmal")
    top, bottom, left, right = dlg.result_margins_mm()
    assert abs(left - 12.7) < 0.15
    dlg.close()
    from PySide6.QtWidgets import QPushButton
    from instantlensdoc.ui.page_layout_dialog import PageLayoutDialog

    pld = PageLayoutDialog(lay, _WIN, rich_document=True)
    preset_btns = [b.objectName() for b in pld.findChildren(QPushButton)]
    assert "pageLayoutMarginPreset_normal" in preset_btns
    pld._apply_margin_preset("breit")
    collected = pld.result_layout()
    assert collected.margin_left_mm > 40.0
    pld.close()


def test_editor_margin_preset_applies() -> None:
    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.1)
    assert _WIN._editor_document_active()
    _WIN._apply_margin_preset("schmal")
    lay = _WIN.editor.page_layout()
    assert lay is not None
    assert abs(lay.margin_top_mm - 12.7) < 0.3
    _WIN._apply_margin_preset("breit")
    lay = _WIN.editor.page_layout()
    assert abs(lay.margin_left_mm - 50.8) < 0.4


def _foreground_hex(ed) -> str:
    cur = ed.textCursor()
    if not cur.hasSelection():
        cur.select(QTextCursor.Document)
        ed.setTextCursor(cur)
    fmt = ed._selection_probe_format(ed.textCursor())
    return fmt.foreground().color().name().lower()


def test_schriftfarbe_glyph_not_highlight_klartext_and_docx() -> None:
    from instantlensdoc.ui.editor import TextEditor

    ed = TextEditor()
    ed.setPlainText("Klartext Glyphenfarbe")
    assert ed.apply_font_color("#cc0000")
    cur = ed.textCursor()
    cur.select(QTextCursor.Document)
    ed.setTextCursor(cur)
    fmt = ed._selection_probe_format(ed.textCursor())
    assert fmt.foreground().color().name().lower() == "#cc0000"
    bg = fmt.background()
    assert bg.style() == Qt.NoBrush or bg.color().alpha() == 0 or not bg.color().isValid()
    ed.deleteLater()

    load_state(_WIN, _APP, "docx", _FIXTURES)
    pump(_APP, 0.15)
    ed = _WIN.editor
    ed.setPlainText("DOCX Farbe")
    cur = ed.textCursor()
    cur.select(QTextCursor.Document)
    ed.setTextCursor(cur)
    _WIN._apply_font_color(QColor("#336699"))
    assert _foreground_hex(ed) == "#336699"
    src = inspect.getsource(_WIN._choose_font_color)
    assert "_guard_editor_action" not in src
    apply_src = inspect.getsource(_WIN._apply_font_color)
    assert "apply_font_color" in apply_src
    assert "apply_font" in apply_src


def test_schriftfarbe_ocr_rich_text() -> None:
    _WIN._show_scan_ocr_text(
        "OCR Rich-Text mit genug Inhalt für Glyphenfarbe.",
        title="OCR — Farbe",
    )
    pump(_APP, 0.15)
    assert _WIN._editor_document_active()
    ed = _WIN.editor
    cur = ed.textCursor()
    cur.select(QTextCursor.Document)
    ed.setTextCursor(cur)
    assert ed.apply_font_color("#aa2200")
    assert _foreground_hex(ed) == "#aa2200"


def test_pdf_apply_font_color_uses_ann_color_not_fill() -> None:
    src = inspect.getsource(_WIN.pdf_view.apply_font_color)
    assert "set_colors" in src
    assert "set_fill_colors" not in src
    from ild_pdf.annotate import Annotation, AnnotationStore, AnnotationType

    store = AnnotationStore()
    ann = Annotation(type=AnnotationType.TEXT, page=0, x=10, y=10, width=80, height=20, text="Hi")
    store.add(ann)
    n = store.set_colors([ann.id], "#FF00AA")
    assert n == 1
    got = store.get(ann.id)
    assert str(got.color).upper() == "#FF00AA"
    assert not str(getattr(got, "fill_color", "") or "").strip()


def test_dtp_font_color_sets_glyph_foreground() -> None:
    from instantlensdoc.dtp.canvas import DtpPane
    from instantlensdoc.dtp.model import DtpDocument

    doc = DtpDocument()
    fr = doc.add_text_frame("DTP Rahmen Text", x=20, y=20, width=180, height=50)
    pane = DtpPane(doc=doc)
    pane.show()
    _APP.processEvents()
    pane.scene.clearSelection()
    pane.scene._items[fr.id].setSelected(True)
    pane.apply_font(color="#cc3300", dialog=False)
    item = pane.scene._items[fr.id]
    html = (fr.rich_html or "") + item.text_item.toHtml()
    assert "#cc3300" in html.lower() or "rgb(204, 51, 0)" in html.lower()
    fmt = item.text_item.textCursor().charFormat()
    cur = QTextCursor(item.text_item.document())
    cur.select(QTextCursor.Document)
    fg = cur.charFormat().foreground().color()
    assert fg.name().lower() == "#cc3300" or "#cc3300" in html.lower()
    pane.close()
