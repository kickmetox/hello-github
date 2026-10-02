"""Dialog: bestehende PDF-AcroForm-Felder lesen/schreiben."""

from __future__ import annotations

from pathlib import Path

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
        self._load()

        self.table.currentCellChanged.connect(self._on_cell)
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
        self.table.setRowCount(0)
        if not self._fields:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("(keine AcroForm-Felder)"))
            self.value_edit.setEnabled(False)
            return
        self.table.setRowCount(len(self._fields))
        for i, f in enumerate(self._fields):
            self.table.setItem(i, 0, QTableWidgetItem(f.name))
            self.table.setItem(i, 1, QTableWidgetItem(f.field_type))
            self.table.setItem(i, 2, QTableWidgetItem(f.value))
            hint = []
            if f.read_only:
                hint.append("nur lesen")
            if f.required:
                hint.append("pflicht")
            if f.alternate_name and f.alternate_name != f.name:
                hint.append(f.alternate_name)
            if f.options:
                hint.append("Opt: " + ", ".join(f.options[:6]))
            self.table.setItem(i, 3, QTableWidgetItem("; ".join(hint)))
        self.table.selectRow(0)
        self._apply_row(0)

    def _persist_row(self, row: int):
        if 0 <= row < len(self._fields) and self.value_edit.isEnabled():
            self._fields[row].value = self.value_edit.text()
            self.table.setItem(row, 2, QTableWidgetItem(self._fields[row].value))

    def _on_cell(self, row: int, _c, prev_row: int, _pc):
        self._persist_row(prev_row)
        self._apply_row(row)

    def _apply_row(self, row: int):
        if row < 0 or row >= len(self._fields):
            return
        f = self._fields[row]
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
        values = {f.name: f.value for f in self._fields if not f.read_only}
        try:
            set_form_values(self.pdf_path, values)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Formularfelder", str(e))
