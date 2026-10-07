"""Word-Tabellen in QTextDocument: einfügen, Zeilen/Spalten, verbinden, Rahmen."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFrameFormat,
    QTextLength,
    QTextTable,
    QTextTableFormat,
)
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

MAX_PICKER_ROWS = 8
MAX_PICKER_COLS = 10


def current_table(cursor: QTextCursor | None) -> QTextTable | None:
    if cursor is None:
        return None
    try:
        table = cursor.currentTable()
    except Exception:
        table = None
    return table


def insert_qtext_table(
    document: QTextDocument,
    cursor: QTextCursor,
    rows: int = 2,
    cols: int = 2,
    *,
    header: bool = True,
) -> QTextTable | None:
    """QTextTable an der Cursorposition — DOCX/OCR-Rich-Text."""
    if document is None or cursor is None:
        return None
    rows = max(1, min(200, int(rows)))
    cols = max(1, min(50, int(cols)))
    work = QTextCursor(cursor)
    fmt = QTextTableFormat()
    fmt.setBorder(1.0)
    fmt.setBorderBrush(QBrush(QColor("#4B5563")))
    fmt.setBorderStyle(QTextFrameFormat.BorderStyle_Solid)
    fmt.setCellPadding(4.0)
    fmt.setCellSpacing(0.0)
    try:
        fmt.setWidth(QTextLength(QTextLength.PercentageLength, 100))
    except Exception:
        pass
    work.beginEditBlock()
    try:
        table = work.insertTable(rows, cols, fmt)
    except Exception:
        work.endEditBlock()
        return None
    if table is None:
        work.endEditBlock()
        return None
    if header and table.rows() > 0:
        _format_header_row(table, enabled=True)
    work.endEditBlock()
    return table


def _cell_cursor(table: QTextTable, row: int, col: int) -> QTextCursor:
    cell = table.cellAt(int(row), int(col))
    return cell.firstCursorPosition()


def _format_header_row(table: QTextTable, *, enabled: bool) -> None:
    cols = table.columns()
    if table.rows() < 1 or cols < 1:
        return
    bg = QBrush(QColor("#E8EEF5")) if enabled else QBrush()
    char = QTextCharFormat()
    char.setFontWeight(QFont.Bold if enabled else QFont.Normal)
    char.setBackground(bg)
    for c in range(cols):
        cell = table.cellAt(0, c)
        cur = cell.firstCursorPosition()
        last = cell.lastCursorPosition()
        cur.setPosition(last.position(), QTextCursor.KeepAnchor)
        cur.mergeCharFormat(char)
        cf = cell.format()
        cf.setBackground(bg)
        cell.setFormat(cf)


def add_row(table: QTextTable, *, after: bool = True) -> bool:
    if table is None:
        return False
    idx = table.rows() if after else 0
    table.insertRows(idx, 1)
    return True


def add_column(table: QTextTable, *, after: bool = True) -> bool:
    if table is None:
        return False
    idx = table.columns() if after else 0
    table.insertColumns(idx, 1)
    return True


def delete_row(table: QTextTable, cursor: QTextCursor) -> bool:
    if table is None or cursor is None:
        return False
    cell = table.cellAt(cursor)
    if cell.row() < 0:
        return False
    if table.rows() <= 1:
        table.removeRows(0, table.rows())
        return True
    table.removeRows(cell.row(), 1)
    return True


def delete_column(table: QTextTable, cursor: QTextCursor) -> bool:
    if table is None or cursor is None:
        return False
    cell = table.cellAt(cursor)
    if cell.column() < 0:
        return False
    if table.columns() <= 1:
        table.removeColumns(0, table.columns())
        return True
    table.removeColumns(cell.column(), 1)
    return True


def merge_selected_cells(table: QTextTable, cursor: QTextCursor) -> bool:
    if table is None or cursor is None:
        return False
    try:
        table.mergeCells(cursor)
        return True
    except Exception:
        pass
    start = table.cellAt(cursor.selectionStart())
    end = table.cellAt(cursor.selectionEnd())
    if start.row() < 0 or end.row() < 0:
        return False
    r0, r1 = sorted((start.row(), end.row()))
    c0, c1 = sorted((start.column(), end.column()))
    try:
        table.mergeCells(r0, c0, r1 - r0 + 1, c1 - c0 + 1)
        return True
    except Exception:
        return False


def split_current_cell(table: QTextTable, cursor: QTextCursor) -> bool:
    if table is None or cursor is None:
        return False
    cell = table.cellAt(cursor)
    if cell.row() < 0:
        return False
    try:
        table.splitCell(cell.row(), cell.column(), 1, 2)
        return True
    except Exception:
        try:
            table.splitCell(cell.row(), cell.column(), 2, 1)
            return True
        except Exception:
            return False


def set_borders(table: QTextTable, *, width: float = 1.0, enabled: bool = True) -> bool:
    if table is None:
        return False
    fmt = table.format()
    fmt.setBorder(float(width) if enabled else 0.0)
    fmt.setBorderStyle(
        QTextFrameFormat.BorderStyle_Solid if enabled else QTextFrameFormat.BorderStyle_None
    )
    table.setFormat(fmt)
    return True


def set_header_row(table: QTextTable, *, enabled: bool = True) -> bool:
    if table is None:
        return False
    _format_header_row(table, enabled=enabled)
    return True


def set_cell_alignment(table: QTextTable, cursor: QTextCursor, alignment: str) -> bool:
    if table is None or cursor is None:
        return False
    mapping = {
        "left": Qt.AlignLeft | Qt.AlignAbsolute,
        "center": Qt.AlignHCenter,
        "right": Qt.AlignRight | Qt.AlignAbsolute,
        "justify": Qt.AlignJustify,
    }
    align = mapping.get((alignment or "left").lower())
    if align is None:
        return False
    cell = table.cellAt(cursor)
    if cell.row() < 0:
        return False
    cur = cell.firstCursorPosition()
    last = cell.lastCursorPosition()
    cur.setPosition(last.position(), QTextCursor.KeepAnchor)
    block = cur.blockFormat()
    block.setAlignment(align)
    cur.mergeBlockFormat(block)
    return True


class TableSizePicker(QFrame):
    """Raster zum Wählen von Zeilen×Spalten (Word-ähnlich)."""

    picked = Signal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setObjectName("ildTableSizePicker")
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setStyleSheet(
            "#ildTableSizePicker { background: #FFFFFF; border: 1px solid #8FA3C0; }"
            "QToolButton#ildTableCell { background: #F8FAFC; border: 1px solid #C5CCD6; }"
            "QToolButton#ildTableCell:checked { background: #D9E6F8; border-color: #3B6DB5; }"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        self._label = QLabel("Tabelle einfügen")
        self._label.setObjectName("ildTablePickerLabel")
        root.addWidget(self._label)
        grid = QGridLayout()
        grid.setSpacing(2)
        self._cells: list[list[QToolButton]] = []
        for r in range(MAX_PICKER_ROWS):
            row_btns: list[QToolButton] = []
            for c in range(MAX_PICKER_COLS):
                b = QToolButton()
                b.setObjectName("ildTableCell")
                b.setFixedSize(16, 16)
                b.setCheckable(True)
                b.setAutoRaise(False)
                b.enterEvent = lambda e, rr=r, cc=c: self._hover(rr, cc)  # type: ignore[method-assign]
                b.clicked.connect(lambda _=False, rr=r, cc=c: self._choose(rr + 1, cc + 1))
                grid.addWidget(b, r, c)
                row_btns.append(b)
            self._cells.append(row_btns)
        root.addLayout(grid)
        self._hover(1, 1)

    def _hover(self, rows: int, cols: int) -> None:
        self._label.setText(f"{rows + 1} × {cols + 1} Tabelle")
        for r, row in enumerate(self._cells):
            for c, b in enumerate(row):
                b.setChecked(r <= rows and c <= cols)

    def _choose(self, rows: int, cols: int) -> None:
        self.picked.emit(int(rows), int(cols))
        self.close()


def show_table_picker(
    parent: QWidget | None = None,
    *,
    pos: QPoint | None = None,
    on_pick: Callable[[int, int], None] | None = None,
) -> TableSizePicker:
    picker = TableSizePicker(parent)
    if on_pick is not None:
        picker.picked.connect(on_pick)
    if pos is not None:
        picker.move(pos)
    picker.show()
    picker.raise_()
    return picker


def qtext_table_cells(table: QTextTable | None) -> list[list[str]]:
    """Zelleninhalt einer QTextTable."""
    if table is None:
        return []
    try:
        rows, cols = int(table.rows()), int(table.columns())
    except Exception:
        return []
    out: list[list[str]] = []
    for r in range(rows):
        row: list[str] = []
        for c in range(cols):
            try:
                cell = table.cellAt(r, c)
                cur = cell.firstCursorPosition()
                cur.setPosition(cell.lastCursorPosition().position(), QTextCursor.KeepAnchor)
                row.append((cur.selectedText() or "").replace("\u2029", " ").strip())
            except Exception:
                row.append("")
        out.append(row)
    return out


def iter_qtext_tables(document: QTextDocument | None) -> list[QTextTable]:
    """Alle QTextTable im Dokument (Word-Suite / CSV / Excel)."""
    if document is None:
        return []
    found: list[QTextTable] = []

    def _walk(frame) -> None:
        try:
            it = frame.begin()
        except Exception:
            return
        while not it.atEnd():
            child = it.currentFrame()
            if child is not None and child is not frame:
                if isinstance(child, QTextTable) or (
                    hasattr(child, "rows") and hasattr(child, "columns")
                ):
                    found.append(child)
                _walk(child)
            it += 1

    try:
        _walk(document.rootFrame())
    except Exception:
        pass
    return found


def first_qtext_table_cells(document: QTextDocument | None) -> list[list[str]]:
    tables = iter_qtext_tables(document)
    if not tables:
        return []
    return qtext_table_cells(tables[0])
