"""Dialog: bestehende PDF-AcroForm-Felder lesen/schreiben."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QAbstractItemView,
    QHeaderView,
)

from ild_pdf.acroform import (
    FormFieldInfo,
    export_form_fields_csv,
    list_form_fields,
    set_form_values,
)
from instantlensdoc.ui.file_dialogs import confirm_overwrite_export


def _display_field_value(f: FormFieldInfo) -> str:
    """Wert inkl. Checkbox/Choice-Anzeige — 1.3.2."""
    ftype = str(getattr(f, "field_type", "") or "")
    value = str(getattr(f, "value", "") or "")
    opts = list(getattr(f, "options", None) or [])
    if ftype == "checkbox":
        on = value.strip().lower() in ("true", "1", "yes", "ja", "on", "x", "checked")
        return "☑ true" if on else "☐ false"
    if ftype in ("choice", "radio") and opts:
        return f"{value}  [{', '.join(opts[:8])}]" if value else f"[{', '.join(opts[:8])}]"
    return value


class FormFieldsDialog(QDialog):
    """Zeigt AcroForm-Felder; Edit nur Textfelder — 1.3.2."""

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
        edit_row.addWidget(QLabel("Wert (nur Text):"))
        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("Textfeld-Wert…")
        self.value_edit.setToolTip(
            "Nur Textfelder editierbar; Checkbox/Choice Werte nur Anzeige — 1.3.2"
        )
        edit_row.addWidget(self.value_edit, 1)
        self.btn_csv = QPushButton("CSV…")
        self.btn_csv.setToolTip("Feldliste als CSV exportieren — 1.3.2")
        self.btn_csv.clicked.connect(self._export_csv)
        edit_row.addWidget(self.btn_csv)
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
            val_disp = _display_field_value(f)
            if f.field_type == "text" and f.value != self._original.get(f.name, f.value):
                val_disp = f"{f.value} *"
            self.table.setItem(row, 2, QTableWidgetItem(val_disp))
            hint = []
            if f.read_only:
                hint.append("nur lesen")
            if f.required:
                hint.append("pflicht")
            if f.field_type in ("checkbox", "choice", "radio"):
                hint.append("Anzeige (edit nur Text)")
            if f.alternate_name and f.alternate_name != f.name:
                hint.append(f.alternate_name)
            if f.options:
                hint.append("Opt: " + ", ".join(f.options[:6]))
            self.table.setItem(row, 3, QTableWidgetItem("; ".join(hint)))
            if f.read_only or f.field_type != "text":
                for col in range(4):
                    it = self.table.item(row, col)
                    if it is not None and (f.read_only or f.field_type != "text"):
                        if f.read_only:
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
        # Nur Textfelder speichern — 1.3.2
        if (
            0 <= fi < len(self._fields)
            and self.value_edit.isEnabled()
            and self._fields[fi].field_type == "text"
            and not self._fields[fi].read_only
        ):
            self._fields[fi].value = self.value_edit.text()
            val = self._fields[fi].value
            disp = (
                f"{val} *"
                if val != self._original.get(self._fields[fi].name, "")
                else val
            )
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
        if f.field_type == "text":
            self.value_edit.setText(f.value)
        else:
            self.value_edit.setText(_display_field_value(f))
        self.value_edit.blockSignals(False)
        editable = (not f.read_only) and f.field_type == "text"
        self.value_edit.setEnabled(editable)
        if not editable and f.field_type in ("checkbox", "choice", "radio"):
            self.value_edit.setToolTip(
                f"{f.field_type}: {_display_field_value(f)} — nur Anzeige, Edit nur Text — 1.3.2"
            )
        else:
            self.value_edit.setToolTip(
                "Nur Textfelder editierbar; Checkbox/Choice Werte nur Anzeige — 1.3.2"
            )

    def _export_csv(self):
        start = str(self.pdf_path.with_name(f"{self.pdf_path.stem}_fields.csv"))
        path, _ = QFileDialog.getSaveFileName(
            self, "Feldliste als CSV", start, "CSV (*.csv)"
        )
        if not path:
            return
        if not confirm_overwrite_export(path, self):
            return
        try:
            dest = export_form_fields_csv(
                self.pdf_path, self._fields, out_path=path
            )
            QMessageBox.information(
                self,
                "Feldliste CSV",
                f"{len(self._fields)} Feld(er) exportiert:\n{dest}",
            )
        except Exception as e:
            QMessageBox.warning(self, "Feldliste CSV", str(e))

    def _save(self):
        self._persist_row(self.table.currentRow())
        if not self._fields:
            self.reject()
            return
        # Nur dirty Textfelder (gegenüber Original), nicht read-only — 1.3.1/1.3.2
        values = {
            f.name: f.value
            for f in self._fields
            if (not f.read_only)
            and f.field_type == "text"
            and f.name
            and f.value != self._original.get(f.name, f.value)
        }
        if not values:
            QMessageBox.information(
                self, "Formularfelder", "Keine geänderten Textfelder zum Speichern."
            )
            return
        try:
            set_form_values(self.pdf_path, values)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Formularfelder", str(e))
