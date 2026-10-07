"""Dialog: PDF-AcroForm-Felder lesen/schreiben/anlegen — 2.6.6."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
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
    QWidget,
)

from ild_pdf.acroform import (
    FormFieldInfo,
    apply_form_candidates,
    create_form_field,
    delete_form_field,
    detect_form_candidates,
    export_form_fields_csv,
    list_form_fields,
    set_form_values,
)
from instantlensdoc.ui.form_field_edit_dialog import FormFieldEditDialog
from instantlensdoc.core.app_settings import (
    dialog_start_dir,
    get_forms_csv_visible_only,
    get_last_export_dir,
    set_forms_csv_visible_only,
    set_last_export_dir,
)
from instantlensdoc.ui.file_dialogs import confirm_overwrite_export


def ask_forms_csv_export_options(
    parent: QWidget | None,
    *,
    n_all: int,
    n_vis: int,
    prefer_visible: bool,
    checkbox_enabled: bool = True,
) -> bool | None:
    """CSV-Optionen: Esc schließt ohne Export; Enter auf OK startet Export — 1.3.6.

    Returns:
        True = nur sichtbare, False = alle, None = abgebrochen.
    """
    dlg = QDialog(parent)
    dlg.setWindowTitle("Feldliste als CSV")
    lay = QVBoxLayout(dlg)
    lay.addWidget(
        QLabel(
            f"{n_all} Feld(er) als CSV exportieren (UTF-8 BOM)?\n"
            "Zielordner wird gemerkt."
        )
    )
    lbl_count = QLabel()
    lay.addWidget(lbl_count)
    cb = QCheckBox("Nur sichtbare/gefilterte Zeilen")
    cb.setToolTip(
        "Nur die aktuell sichtbaren/gefilterten Felder; Default wird persistiert — 1.3.6"
    )
    cb.setChecked(bool(prefer_visible and n_vis > 0))
    cb.setEnabled(bool(checkbox_enabled))
    lay.addWidget(cb)

    def _sync_csv_count(_checked: bool = False) -> None:
        n_export = n_vis if cb.isChecked() else n_all
        lbl_count.setText(f"{n_export} von {n_all} Zeilen")

    cb.toggled.connect(_sync_csv_count)
    _sync_csv_count(cb.isChecked())

    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    ok_btn = buttons.button(QDialogButtonBox.Ok)
    cancel_btn = buttons.button(QDialogButtonBox.Cancel)
    ok_btn.setText("OK")
    ok_btn.setDefault(True)
    ok_btn.setAutoDefault(True)
    cancel_btn.setAutoDefault(False)
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)
    ok_btn.setFocus(Qt.FocusReason.OtherFocusReason)

    class _CsvKeyFilter(QObject):
        """Esc → Abbruch; Enter nur bei Fokus auf OK → Export — 1.3.6."""

        def eventFilter(self, obj, event):  # noqa: N802
            if event.type() == QEvent.Type.KeyPress:
                key = event.key()
                if key == Qt.Key_Escape:
                    dlg.reject()
                    return True
                if key in (Qt.Key_Return, Qt.Key_Enter):
                    fw = dlg.focusWidget()
                    if fw is ok_btn:
                        dlg.accept()
                        return True
                    # Kein Export ohne OK-Fokus (Enter nicht an Default-Button)
                    return True
            return False

    key_filter = _CsvKeyFilter(dlg)
    dlg.installEventFilter(key_filter)
    ok_btn.installEventFilter(key_filter)
    cancel_btn.installEventFilter(key_filter)
    cb.installEventFilter(key_filter)

    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    return bool(cb.isChecked())


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
    """AcroForm-Felder anzeigen, ausfüllen, anlegen/löschen — 2.6.6."""

    def __init__(self, pdf_path: str | Path, parent=None, *, page_index: int = 0):
        super().__init__(parent)
        self.pdf_path = Path(pdf_path)
        self.page_index = int(page_index or 0)
        self.setObjectName("formFieldsDialog")
        self.setWindowTitle("PDF-Formularfelder")
        self.resize(720, 480)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                f"{self.pdf_path.name} — AcroForm-Felder ausfüllen & erstellen — 2.6.6"
            )
        )

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter nach Name…")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.setToolTip("Formularfelder nach Name filtern — 1.3.1")
        self.filter_edit.textChanged.connect(self._rebuild_table)
        layout.addWidget(self.filter_edit)

        self.table = QTableWidget(0, 4)
        self.table.setObjectName("formFieldsTable")
        self.table.setHorizontalHeaderLabels(["Name", "Typ", "Wert", "Hinweis"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

        edit_row = QHBoxLayout()
        edit_row.addWidget(QLabel("Wert:"))
        self.value_edit = QLineEdit()
        self.value_edit.setObjectName("formFieldsValueEdit")
        self.value_edit.setPlaceholderText("Textfeld-Wert…")
        self.value_edit.setToolTip(
            "Text / Dropdown-Wert; Checkbox über Schalter — 2.6.6"
        )
        edit_row.addWidget(self.value_edit, 1)
        self.value_check = QCheckBox("☑")
        self.value_check.setObjectName("formFieldsValueCheck")
        self.value_check.setToolTip("Checkbox-Wert — 2.6.6")
        self.value_check.toggled.connect(self._mark_dirty_from_check)
        edit_row.addWidget(self.value_check)
        self.value_choice = QComboBox()
        self.value_choice.setObjectName("formFieldsValueChoice")
        self.value_choice.setMinimumWidth(120)
        self.value_choice.setToolTip("Dropdown-Auswahl — 2.6.6")
        self.value_choice.currentTextChanged.connect(self._mark_dirty_from_choice)
        edit_row.addWidget(self.value_choice)
        self.btn_csv = QPushButton("CSV…")
        self.btn_csv.setToolTip(
            "Feldliste als CSV; Zähler N von M Zeilen; Default persistiert — 1.3.5"
        )
        self.btn_csv.clicked.connect(self._export_csv)
        edit_row.addWidget(self.btn_csv)
        layout.addLayout(edit_row)

        action_row = QHBoxLayout()
        self.btn_add = QPushButton("Feld hinzu…")
        self.btn_add.setObjectName("formFieldsAddBtn")
        self.btn_add.setToolTip("Neues Text-/Checkbox-/Dropdown-Feld — 2.6.6")
        self.btn_add.clicked.connect(self._add_field)
        self.btn_del = QPushButton("Feld löschen")
        self.btn_del.setObjectName("formFieldsDeleteBtn")
        self.btn_del.clicked.connect(self._delete_field)
        self.btn_detect = QPushButton("Felder erkennen…")
        self.btn_detect.setObjectName("formFieldsDetectBtn")
        self.btn_detect.setToolTip(
            "Heuristik: Labels „:“, Unterstriche, [ ] → Felder anlegen — 2.6.6"
        )
        self.btn_detect.clicked.connect(self._detect_fields)
        action_row.addWidget(self.btn_add)
        action_row.addWidget(self.btn_del)
        action_row.addWidget(self.btn_detect)
        action_row.addStretch(1)
        layout.addLayout(action_row)

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
            if f.value != self._original.get(f.name, f.value):
                val_disp = f"{val_disp} *"
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
            if f.page_index is not None:
                hint.append(f"S.{int(f.page_index) + 1}")
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
        if fi is None or not (0 <= fi < len(self._fields)):
            return
        f = self._fields[fi]
        if f.read_only:
            return
        if f.field_type == "text" and self.value_edit.isEnabled():
            f.value = self.value_edit.text()
        elif f.field_type == "checkbox" and self.value_check.isEnabled():
            f.value = "true" if self.value_check.isChecked() else "false"
        elif f.field_type == "choice" and self.value_choice.isEnabled():
            f.value = self.value_choice.currentText()
        else:
            return
        val_disp = _display_field_value(f)
        if f.value != self._original.get(f.name, ""):
            val_disp = f"{val_disp} *"
        self.table.setItem(row, 2, QTableWidgetItem(val_disp))

    def _mark_dirty_from_edit(self, _text: str = ""):
        row = self.table.currentRow()
        self._persist_row(row)

    def _mark_dirty_from_check(self, _checked: bool = False):
        row = self.table.currentRow()
        self._persist_row(row)

    def _mark_dirty_from_choice(self, _text: str = ""):
        row = self.table.currentRow()
        self._persist_row(row)

    def _on_cell(self, row: int, _c, prev_row: int, _pc):
        self._persist_row(prev_row)
        self._apply_row(row)

    def _apply_row(self, row: int):
        fi = self._field_index_for_row(row)
        if fi is None or fi < 0 or fi >= len(self._fields):
            self.value_edit.setEnabled(False)
            self.value_check.setEnabled(False)
            self.value_choice.setEnabled(False)
            return
        f = self._fields[fi]
        editable = not f.read_only and f.field_type in ("text", "checkbox", "choice")
        self.value_edit.blockSignals(True)
        self.value_check.blockSignals(True)
        self.value_choice.blockSignals(True)
        try:
            if f.field_type == "checkbox":
                on = f.value.strip().lower() in (
                    "true",
                    "1",
                    "yes",
                    "ja",
                    "on",
                    "x",
                    "checked",
                )
                self.value_check.setChecked(on)
                self.value_edit.setText(_display_field_value(f))
                self.value_edit.setEnabled(False)
                self.value_check.setEnabled(editable)
                self.value_choice.setEnabled(False)
                self.value_choice.clear()
            elif f.field_type == "choice":
                self.value_choice.clear()
                opts = list(f.options or [])
                if f.value and f.value not in opts:
                    opts = [f.value] + opts
                self.value_choice.addItems(opts or [f.value or ""])
                if f.value:
                    i = self.value_choice.findText(f.value)
                    if i >= 0:
                        self.value_choice.setCurrentIndex(i)
                self.value_edit.setText(f.value)
                self.value_edit.setEnabled(False)
                self.value_check.setEnabled(False)
                self.value_choice.setEnabled(editable)
            else:
                self.value_edit.setText(f.value)
                self.value_edit.setEnabled(editable and f.field_type == "text")
                self.value_check.setEnabled(False)
                self.value_choice.setEnabled(False)
                self.value_choice.clear()
        finally:
            self.value_edit.blockSignals(False)
            self.value_check.blockSignals(False)
            self.value_choice.blockSignals(False)
        self.value_edit.setToolTip(
            "Text-/Checkbox-/Dropdown-Werte speichern — 2.6.6"
            if editable
            else "Feld nicht editierbar"
        )

    def _visible_fields(self) -> list[FormFieldInfo]:
        """Felder der aktuell sichtbaren Tabellenzeilen — 1.3.4."""
        out: list[FormFieldInfo] = []
        for fi in self._row_map:
            if 0 <= fi < len(self._fields):
                out.append(self._fields[fi])
        return out

    def _export_csv(self):
        """CSV: Esc ohne Export; Enter auf OK; Zähler N von M; Default persistiert — 1.3.6."""
        all_fields = list(self._fields)
        visible = self._visible_fields()
        n_vis = len(visible)
        n_all = len(all_fields)

        choice = ask_forms_csv_export_options(
            self,
            n_all=n_all,
            n_vis=n_vis,
            prefer_visible=bool(get_forms_csv_visible_only()),
            checkbox_enabled=bool(self._fields),
        )
        if choice is None:
            return
        set_forms_csv_visible_only(choice)
        rows = visible if choice else all_fields
        if not rows:
            QMessageBox.information(
                self, "Feldliste CSV", "Keine Felder zum Export."
            )
            return
        start_dir = dialog_start_dir(get_last_export_dir() or self.pdf_path.parent)
        start = str(Path(start_dir) / f"{self.pdf_path.stem}_fields.csv")
        path, _ = QFileDialog.getSaveFileName(
            self, "Feldliste als CSV", start, "CSV (*.csv)"
        )
        if not path:
            return
        if not confirm_overwrite_export(path, self):
            return
        try:
            dest = export_form_fields_csv(
                self.pdf_path, rows, out_path=path, utf8_bom=True
            )
            set_last_export_dir(Path(dest).parent)
            QMessageBox.information(
                self,
                "Feldliste CSV",
                f"{len(rows)} Feld(er) exportiert:\n{dest}",
            )
        except Exception as e:
            QMessageBox.warning(self, "Feldliste CSV", str(e))

    def _add_field(self) -> None:
        dlg = FormFieldEditDialog(
            self,
            title="Formularfeld hinzufügen",
            name=f"Feld_{len(self._fields) + 1}",
            field_type="text",
            hint="Neues ausfüllbares Feld auf der aktuellen Seite (Standard-Rect) — 2.6.6",
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        vals = dlg.values()
        # Standard-Position gestaffelt
        y0 = 700 - (len(self._fields) % 12) * 36
        if vals["field_type"] == "checkbox":
            rect = (72, y0, 88, y0 + 16)
        else:
            rect = (72, y0, 280, y0 + 22)
        try:
            create_form_field(
                self.pdf_path,
                self.page_index,
                rect,
                vals["name"],
                vals["field_type"],
                options=vals["options"],
                value=vals["value"],
                required=vals["required"],
            )
            self._load()
        except Exception as e:
            QMessageBox.warning(self, "Feld hinzu", str(e))

    def _delete_field(self) -> None:
        fi = self._field_index_for_row(self.table.currentRow())
        if fi is None or not (0 <= fi < len(self._fields)):
            QMessageBox.information(self, "Feld löschen", "Bitte Feld auswählen.")
            return
        name = self._fields[fi].name
        if (
            QMessageBox.question(
                self,
                "Feld löschen",
                f"Feld „{name}“ wirklich entfernen?",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        try:
            delete_form_field(self.pdf_path, name)
            self._load()
        except Exception as e:
            QMessageBox.warning(self, "Feld löschen", str(e))

    def _detect_fields(self) -> None:
        try:
            cands = detect_form_candidates(self.pdf_path, self.page_index)
        except Exception as e:
            QMessageBox.warning(self, "Felder erkennen", str(e))
            return
        if not cands:
            QMessageBox.information(
                self,
                "Felder erkennen",
                "Keine Kandidaten auf dieser Seite (Labels „:“, ____, [ ]).",
            )
            return
        summary = "\n".join(
            f"· {c.suggested_type}: {c.suggested_name} ({c.reason})" for c in cands[:12]
        )
        more = "" if len(cands) <= 12 else f"\n… +{len(cands) - 12} weitere"
        if (
            QMessageBox.question(
                self,
                "Felder erkennen",
                f"{len(cands)} Kandidat(en) anlegen?\n\n{summary}{more}",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        try:
            apply_form_candidates(self.pdf_path, cands)
            self._load()
            QMessageBox.information(
                self, "Felder erkennen", f"{len(cands)} Feld(er) angelegt."
            )
        except Exception as e:
            QMessageBox.warning(self, "Felder erkennen", str(e))

    def _save(self):
        self._persist_row(self.table.currentRow())
        if not self._fields:
            self.reject()
            return
        # Dirty Text/Checkbox/Choice — 2.6.6
        values = {
            f.name: f.value
            for f in self._fields
            if (not f.read_only)
            and f.field_type in ("text", "checkbox", "choice")
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
