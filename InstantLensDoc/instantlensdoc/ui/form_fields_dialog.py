"""Dialog: bestehende PDF-AcroForm-Felder lesen/schreiben."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QAbstractItemView,
    QHeaderView,
)

from ild_pdf.acroform import FormFieldInfo, list_form_fields, set_form_values


class FormFieldsDialog(QDialog):
    """Zeigt AcroForm-Felder und erlaubt Werte zu ändern."""

    def __init__(self, pdf_path: str | Path, parent=None):
        super().__init__(parent)
        self.pdf_path = Path(pdf_path)
        self.setWindowTitle("PDF-Formularfelder")
        self.resize(640, 420)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"{self.pdf_path.name} — bestehende AcroForm-Felder"))

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter nach Name…")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.setToolTip("Formularfelder nach Name filtern — 1.3.1")
        self.filter_edit.textChanged.connect(self._rebuild_table)
        layout.addWidget(self.filter_edit)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Name", "Typ", "Wert", "Hinweis"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

        edit_row = QHBoxLayout()
        edit_row.addWidget(QLabel("Wert:"))
        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("Feldwert…")
        edit_row.addWidget(self.value_edit, 1)
        self.choice = QComboBox()
        self.choice.setVisible(False)
        self.choice.currentTextChanged.connect(self._choice_to_edit)
        edit_row.addWidget(self.choice)
        layout.addLayout(edit_row)

        self._fields: list[FormFieldInfo] = []
        self._original: dict[str, str] = {}
        self._row_map: list[int] = []  # table row → field index
        self._load()

        self.table.currentCellChanged.connect(self._on_cell)
        self.value_edit.textChanged.connect(self._mark_dirty_from_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load(self):
        try:
            self._fields = list_form_fields(self.pdf_path)
        except Exception as e:
            QMessageBox.warning(self, "Formularfelder", str(e))
            self._fields = []
        self._original = {f.name: f.value for f in self._fields}
        self._rebuild_table()

    def _rebuild_table(self, _text: str = ""):
        self.table.setRowCount(0)
        self._row_map = []
        needle = (self.filter_edit.text() or "").strip().lower()
        if not self._fields:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("(keine AcroForm-Felder)"))
            self.value_edit.setEnabled(False)
            return
        rows = []
        for i, f in enumerate(self._fields):
            if needle and needle not in f.name.lower() and needle not in (
                f.alternate_name or ""
            ).lower():
                continue
            rows.append(i)
        if not rows:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("(keine Treffer)"))
            self.value_edit.setEnabled(False)
            return
        self.table.setRowCount(len(rows))
        gray = QBrush(QColor("#888888"))
        for row, fi in enumerate(rows):
            f = self._fields[fi]
            name_disp = f"{f.name} [RO]" if f.read_only else f.name
            self.table.setItem(row, 0, QTableWidgetItem(name_disp))
            self.table.setItem(row, 1, QTableWidgetItem(f.field_type))
            val_disp = f.value
            if f.name in self._original and f.value != self._original.get(f.name, f.value):
                # value already on field object — mark if dirty vs original
                pass
            if f.value != self._original.get(f.name, f.value):
                val_disp = f"{f.value} *"
            self.table.setItem(row, 2, QTableWidgetItem(val_disp))
            hint = []
            if f.read_only:
                hint.append("nur lesen")
            if f.required:
                hint.append("pflicht")
            if f.alternate_name and f.alternate_name != f.name:
                hint.append(f.alternate_name)
            if f.options:
                hint.append("Opt: " + ", ".join(f.options[:6]))
            self.table.setItem(row, 3, QTableWidgetItem("; ".join(hint)))
            if f.read_only:
                for col in range(4):
                    it = self.table.item(row, col)
                    if it is not None:
                        it.setForeground(gray)
            self._row_map.append(fi)
        self.table.selectRow(0)
        self._apply_row(0)

    def _field_index_for_row(self, row: int) -> int | None:
        if 0 <= row < len(self._row_map):
            return self._row_map[row]
        return None

    def _persist_row(self, row: int):
        fi = self._field_index_for_row(row)
        if fi is None:
            return
        if 0 <= fi < len(self._fields) and self.value_edit.isEnabled():
            self._fields[fi].value = self.value_edit.text()
            val = self._fields[fi].value
            disp = f"{val} *" if val != self._original.get(self._fields[fi].name, "") else val
            self.table.setItem(row, 2, QTableWidgetItem(disp))

    def _mark_dirty_from_edit(self, _text: str = ""):
        row = self.table.currentRow()
        self._persist_row(row)

    def _on_cell(self, row: int, _c, prev_row: int, _pc):
        self._persist_row(prev_row)
        self._apply_row(row)

    def _apply_row(self, row: int):
        fi = self._field_index_for_row(row)
        if fi is None or fi < 0 or fi >= len(self._fields):
            return
        f = self._fields[fi]
        self.value_edit.blockSignals(True)
        self.value_edit.setText(f.value)
        self.value_edit.blockSignals(False)
        ro = f.read_only or f.field_type in ("signature", "pushbutton")
        self.value_edit.setEnabled(not ro)
        if f.options and f.field_type in ("choice", "radio", "checkbox"):
            self.choice.blockSignals(True)
            self.choice.clear()
            opts = list(f.options)
            if f.field_type == "checkbox" and not opts:
                opts = ["true", "false"]
            if f.value and f.value not in opts:
                opts = [f.value] + opts
            self.choice.addItems(opts)
            idx = self.choice.findText(f.value)
            if idx >= 0:
                self.choice.setCurrentIndex(idx)
            self.choice.setVisible(True)
            self.choice.setEnabled(not ro)
            self.choice.blockSignals(False)
        else:
            self.choice.setVisible(False)

    def _choice_to_edit(self, text: str):
        if self.choice.isVisible():
            self.value_edit.setText(text)

    def _save(self):
        self._persist_row(self.table.currentRow())
        if not self._fields:
            self.reject()
            return
        # Nur dirty (gegenüber Original) und nicht read-only — 1.3.1
        values = {
            f.name: f.value
            for f in self._fields
            if (not f.read_only)
            and f.name
            and f.value != self._original.get(f.name, f.value)
        }
        if not values:
            QMessageBox.information(
                self, "Formularfelder", "Keine geänderten Felder zum Speichern."
            )
            return
        try:
            set_form_values(self.pdf_path, values)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Formularfelder", str(e))
