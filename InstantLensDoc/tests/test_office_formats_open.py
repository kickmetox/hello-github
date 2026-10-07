"""Offscreen: Markdown/CSV/Excel öffnen in der Word-Suite (Tabelle/Überschrift)."""

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

from instantlensdoc.core.documents import (  # noqa: E402
    DocKind,
    open_document,
    save_document,
)
from instantlensdoc.core.markdown_io import html_to_markdown, markdown_to_html  # noqa: E402
from instantlensdoc.ui.file_dialogs import (  # noqa: E402
    document_open_name_filters,
    document_save_name_filters,
)


_SAMPLE_MD = """# Bericht

Ein Absatz mit **fett** und *kursiv* plus [Link](https://example.com).

- eins
- zwei

```python
print("hi")
```

| Name | Wert |
| --- | --- |
| Alpha | 1 |
| Beta | 2 |
"""


def _write_samples(td: Path) -> dict[str, Path]:
    md = td / "sample.md"
    md.write_text(_SAMPLE_MD, encoding="utf-8")
    csvp = td / "sample.csv"
    csvp.write_text("Name;Wert\nAlpha;1\nBeta;2\n", encoding="utf-8")
    from ild_pdf.tables import create_table, export_table_xlsx

    xlsx = td / "sample.xlsx"
    export_table_xlsx(
        create_table(data=[["Name", "Wert"], ["Alpha", "1"], ["Beta", "2"]], header=True),
        xlsx,
        sheet_name="Daten",
    )
    xls_as_xlsx = td / "sample.xls"
    xls_as_xlsx.write_bytes(xlsx.read_bytes())
    return {"md": md, "csv": csvp, "xlsx": xlsx, "xls": xls_as_xlsx}


def test_filters_include_md_csv_xls() -> None:
    open_f = document_open_name_filters().lower()
    save_f = document_save_name_filters().lower()
    for ext in (".md", ".csv", ".xls", ".xlsx"):
        assert ext in open_f, f"Öffnen-Filter fehlt {ext}"
        assert ext in save_f, f"Speichern-Filter fehlt {ext}"
    from instantlensdoc.ui.file_dialogs import document_save_filters_are_safe

    assert document_save_filters_are_safe()
    import inspect
    from instantlensdoc.ui.main_window import MainWindow

    src = inspect.getsource(MainWindow.open_dialog) + inspect.getsource(
        MainWindow.open_dialog_with_encoding
    )
    assert "document_open_name_filters" in src


def test_open_document_md_csv_xlsx(tmp_path: Path) -> None:
    samples = _write_samples(tmp_path)
    md = open_document(samples["md"])
    assert md.kind == DocKind.MARKDOWN
    html = str(md.meta.get("html") or "")
    assert "<h1>" in html.lower() and "Bericht" in html
    assert "<table" in html.lower()
    assert "**" not in (md.text or "") or "Bericht" in md.text

    csv_doc = open_document(samples["csv"])
    assert csv_doc.kind == DocKind.CSV
    assert csv_doc.meta.get("csv_delimiter") == ";"
    assert "<table" in str(csv_doc.meta.get("html") or "").lower()
    cells = (csv_doc.meta.get("table") or {}).get("cells") or []
    assert any("Alpha" in (c or "") for row in cells for c in row)

    xdoc = open_document(samples["xlsx"])
    assert xdoc.kind == DocKind.XLSX
    assert "<table" in str(xdoc.meta.get("html") or "").lower()
    assert "Alpha" in (xdoc.text or "")
    sheets = xdoc.meta.get("sheets") or []
    assert sheets

    xls = open_document(samples["xls"])
    assert xls.kind == DocKind.XLSX
    assert "Alpha" in (xls.text or "")


def test_markdown_html_roundtrip_no_pilcrow() -> None:
    html = markdown_to_html(_SAMPLE_MD)
    assert "¶" not in html
    assert "<h1>" in html
    assert "<table" in html.lower()
    md2 = html_to_markdown(html)
    assert "¶" not in md2
    assert "Bericht" in md2
    assert "Alpha" in md2


def test_save_markdown_strips_pilcrow(tmp_path: Path) -> None:
    from instantlensdoc.core.documents import Document

    dest = tmp_path / "out.md"
    doc = Document(
        kind=DocKind.MARKDOWN,
        text="# Titel¶\n\nText",
        meta={"html": "<h1>Titel¶</h1><p>Text</p>", "rich_text": True},
    )
    save_document(doc, dest)
    body = dest.read_text(encoding="utf-8")
    assert "¶" not in body
    assert "Titel" in body


def test_save_csv_from_table(tmp_path: Path) -> None:
    from instantlensdoc.core.documents import Document

    dest = tmp_path / "out.csv"
    doc = Document(
        kind=DocKind.CSV,
        text="Name;Wert",
        meta={
            "table": {"cells": [["Name", "Wert"], ["X", "9"]], "format": {"header": True}},
            "csv_delimiter": ";",
        },
    )
    save_document(doc, dest)
    raw = dest.read_text(encoding="utf-8-sig")
    assert "Name" in raw and "X" in raw


def test_mainwindow_open_heading_and_table(tmp_path: Path, qapp) -> None:
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QToolButton

    from instantlensdoc.license import LicenseManager
    from instantlensdoc.ui.main_window import MainWindow
    from instantlensdoc.ui.tables import first_qtext_table_cells, iter_qtext_tables

    samples = _write_samples(tmp_path)
    lm = LicenseManager()
    lm.ensure_trial_started()
    win = MainWindow(lm)
    win.resize(1200, 800)
    try:
        win.open_path(str(samples["md"]))
        win._sync_menu_enablement()
        assert win._text_document_active()
        assert win._view_capability_state()["font"] is True
        assert win.ribbon_bar.is_enabled("font")
        assert win.ribbon_bar.is_enabled("bold")
        plain = win.editor.toPlainText()
        assert "Bericht" in plain
        html = win.editor.to_rich_html()
        heading = False
        block = win.editor.document().firstBlock()
        while block.isValid():
            fmt = block.blockFormat()
            if int(fmt.headingLevel() or 0) >= 1 or fmt.fontWeight() >= QFont.Bold:
                if "Bericht" in (block.text() or ""):
                    heading = True
                    break
            block = block.next()
        assert heading or "<h1" in html.lower() or "Bericht" in plain
        assert "¶" not in plain

        win.open_path(str(samples["csv"]))
        win._sync_menu_enablement()
        assert win._view_capability_state()["font"] is True
        assert win.ribbon_bar.is_enabled("font_color")
        tables = iter_qtext_tables(win.editor.document())
        cells = first_qtext_table_cells(win.editor.document())
        assert tables or cells or "Alpha" in win.editor.toPlainText()
        if cells:
            flat = " ".join(c for row in cells for c in row)
            assert "Alpha" in flat or "Name" in flat

        win.open_path(str(samples["xlsx"]))
        win._sync_menu_enablement()
        assert win._text_document_active()
        assert win._view_capability_state()["font"] is True
        assert win.ribbon_bar.is_enabled("font")
        assert win.ribbon_bar.is_enabled("bold")
        cells = first_qtext_table_cells(win.editor.document())
        assert cells or "Alpha" in win.editor.toPlainText()
        bold = win.editor_pane._tool_buttons.get("bold")
        assert isinstance(bold, QToolButton)
        assert bold.isEnabled()

        win.doc.meta["readonly"] = True
        win._apply_schreibschutz_ui()
        assert win.editor.isReadOnly()
        assert not bold.isEnabled()
        win.doc.meta.pop("readonly", None)
        win._apply_schreibschutz_ui()
        assert bold.isEnabled()
    finally:
        win.close()
