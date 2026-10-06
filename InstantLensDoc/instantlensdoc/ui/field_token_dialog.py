"""Dialog: Ersatzzeichen / Felder — Builtin plus frei definierbare name=value."""

from __future__ import annotations

from typing import Any, Mapping

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from instantlensdoc.core.field_tokens import (
    BUILTIN_FIELD_FORMATS,
    BUILTIN_FIELD_LABELS,
    BUILTIN_FIELDS,
    FIELD_FORMAT_LABELS,
    FIELD_FORMATS,
    INSERT_TARGET_LABELS,
    INSERT_TARGETS,
    FieldTokenSpec,
    canonical_field_format,
    canonical_field_name,
    canonical_insert_target,
    coerce_field_specs,
    safe_field_display,
)


class FieldTokenDialog(QDialog):
    """Ersatzzeichen als ``{name}`` — ¶/Form-Feed werden auf das Token gemappt."""

    insert_requested = Signal()

    def __init__(
        self,
        parent=None,
        *,
        current_name: str = "date",
        ersatz: str = "",
        specs: Mapping[str, Any] | None = None,
        header: str = "",
        footer: str = "",
        target: str = "body",
    ):
        super().__init__(parent)
        self.setObjectName("fieldTokenDialog")
        self.setWindowTitle("Ersatzzeichen / Felder")
        self.setModal(True)
        self.resize(640, 460)
        self._inserted = False
        self._specs: dict[str, FieldTokenSpec] = {}

        root = QVBoxLayout(self)
        root.addWidget(QLabel("Felder einfügen, eigene Werte anlegen und Format wählen."))

        self.table = QTableWidget(0, 3)
        self.table.setObjectName("fieldTokenTable")
        self.table.setHorizontalHeaderLabels(["Name", "Format", "Wert"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        self.table.itemChanged.connect(self._on_item_changed)
        root.addWidget(self.table)

        row_btns = QHBoxLayout()
        self.add_btn = QPushButton("Hinzufügen")
        self.add_btn.setObjectName("fieldTokenAdd")
        self.add_btn.clicked.connect(self._add_custom)
        self.rename_btn = QPushButton("Umbenennen")
        self.rename_btn.setObjectName("fieldTokenRename")
        self.rename_btn.clicked.connect(self._rename_custom)
        self.delete_btn = QPushButton("Löschen")
        self.delete_btn.setObjectName("fieldTokenDelete")
        self.delete_btn.clicked.connect(self._delete_custom)
        row_btns.addWidget(self.add_btn)
        row_btns.addWidget(self.rename_btn)
        row_btns.addWidget(self.delete_btn)
        row_btns.addStretch(1)
        root.addLayout(row_btns)

        form = QFormLayout()
        self.field_combo = QComboBox()
        self.field_combo.setObjectName("fieldTokenName")
        self.field_combo.setEditable(True)
        self.field_combo.currentTextChanged.connect(self._on_combo_changed)
        self.format_combo = QComboBox()
        self.format_combo.setObjectName("fieldTokenFormat")
        for fmt in FIELD_FORMATS:
            self.format_combo.addItem(FIELD_FORMAT_LABELS[fmt], fmt)
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        self.ersatz_edit = QLineEdit()
        self.ersatz_edit.setObjectName("fieldTokenErsatz")
        self.ersatz_edit.setText(ersatz or "")
        self.ersatz_edit.setPlaceholderText("Wert (leer = {name}; Steuerzeichen werden verworfen)")
        self.ersatz_edit.textChanged.connect(self._on_value_changed)
        self.target_combo = QComboBox()
        self.target_combo.setObjectName("fieldTokenTarget")
        for tgt in INSERT_TARGETS:
            self.target_combo.addItem(INSERT_TARGET_LABELS[tgt], tgt)
        idx_t = self.target_combo.findData(canonical_insert_target(target))
        if idx_t >= 0:
            self.target_combo.setCurrentIndex(idx_t)
        self.header_edit = QLineEdit()
        self.header_edit.setObjectName("fieldTokenHeaderEdit")
        self.header_edit.setText(header or "")
        self.header_edit.setPlaceholderText("Caret in der Kopfzeile")
        self.footer_edit = QLineEdit()
        self.footer_edit.setObjectName("fieldTokenFooterEdit")
        self.footer_edit.setText(footer or "")
        self.footer_edit.setPlaceholderText("Caret in der Fußzeile")
        form.addRow("Feld", self.field_combo)
        form.addRow("Format", self.format_combo)
        form.addRow("Wert", self.ersatz_edit)
        form.addRow("Einfügen in", self.target_combo)
        form.addRow("Kopfzeile", self.header_edit)
        form.addRow("Fußzeile", self.footer_edit)
        root.addLayout(form)

        insert_row = QHBoxLayout()
        self.insert_btn = QPushButton("Einfügen")
        self.insert_btn.setObjectName("fieldTokenInsert")
        self.insert_btn.setDefault(True)
        self.insert_btn.clicked.connect(self._emit_insert)
        insert_row.addWidget(self.insert_btn)
        insert_row.addStretch(1)
        root.addLayout(insert_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.setObjectName("fieldTokenButtons")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._load_specs(specs, current_name=current_name, ersatz=ersatz)

    def _load_specs(
        self,
        specs: Mapping[str, Any] | None,
        *,
        current_name: str,
        ersatz: str,
    ) -> None:
        coerced = coerce_field_specs(specs or {})
        for name in BUILTIN_FIELDS:
            if name not in coerced:
                coerced[name] = FieldTokenSpec(
                    name=name,
                    format=BUILTIN_FIELD_FORMATS.get(name, "text"),
                    builtin=True,
                )
            else:
                coerced[name].builtin = True
                coerced[name].format = BUILTIN_FIELD_FORMATS.get(name, coerced[name].format)
        ident = canonical_field_name(current_name) or "date"
        if ident not in coerced:
            coerced[ident] = FieldTokenSpec(name=ident, format="text", value=ersatz or "")
        elif ersatz:
            coerced[ident].value = safe_field_display(ident, ersatz)
            if coerced[ident].value == f"{{{ident}}}":
                coerced[ident].value = ""
        self._specs = coerced
        self._rebuild_table(select=ident)

    def _rebuild_table(self, select: str | None = None) -> None:
        self.table.blockSignals(True)
        self.field_combo.blockSignals(True)
        self.table.setRowCount(0)
        self.field_combo.clear()
        names = list(BUILTIN_FIELDS) + [
            n for n in sorted(self._specs) if n not in BUILTIN_FIELDS
        ]
        for name in names:
            spec = self._specs.get(name)
            if spec is None:
                continue
            row = self.table.rowCount()
            self.table.insertRow(row)
            label = BUILTIN_FIELD_LABELS.get(name, name)
            name_item = QTableWidgetItem(f"{label}  {{{name}}}" if name in BUILTIN_FIELDS else name)
            name_item.setData(256, name)
            if spec.builtin:
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            fmt_item = QTableWidgetItem(FIELD_FORMAT_LABELS.get(spec.format, spec.format))
            fmt_item.setData(256, spec.format)
            val_item = QTableWidgetItem(spec.value)
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, fmt_item)
            self.table.setItem(row, 2, val_item)
            self.field_combo.addItem(
                f"{label} ({{{name}}})" if name in BUILTIN_FIELDS else f"{{{name}}}",
                name,
            )
        self.table.blockSignals(False)
        self.field_combo.blockSignals(False)
        ident = canonical_field_name(select or "") or "date"
        self._select_name(ident)

    def _select_name(self, ident: str) -> None:
        ident = canonical_field_name(ident) or "date"
        idx = self.field_combo.findData(ident)
        if idx >= 0:
            self.field_combo.setCurrentIndex(idx)
        else:
            self.field_combo.setEditText(ident)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and str(item.data(256) or "") == ident:
                self.table.selectRow(row)
                break
        self._sync_editors_from_spec(ident)

    def _current_ident(self) -> str:
        data = self.field_combo.currentData()
        raw = str(data or self.field_combo.currentText() or "").strip()
        ident = canonical_field_name(raw) or canonical_field_name(raw.strip("{}"))
        return ident or "date"

    def _spec_for(self, ident: str) -> FieldTokenSpec:
        spec = self._specs.get(ident)
        if spec is None:
            spec = FieldTokenSpec(
                name=ident,
                format=BUILTIN_FIELD_FORMATS.get(ident, "text"),
                builtin=ident in BUILTIN_FIELDS,
            )
            self._specs[ident] = spec
        return spec

    def _sync_editors_from_spec(self, ident: str) -> None:
        spec = self._spec_for(ident)
        self.format_combo.blockSignals(True)
        self.ersatz_edit.blockSignals(True)
        fidx = self.format_combo.findData(canonical_field_format(spec.format))
        self.format_combo.setCurrentIndex(fidx if fidx >= 0 else 0)
        self.format_combo.setEnabled(not spec.builtin)
        self.ersatz_edit.setText(spec.value)
        self.ersatz_edit.setEnabled(not spec.builtin)
        self.rename_btn.setEnabled(not spec.builtin)
        self.delete_btn.setEnabled(not spec.builtin)
        self.format_combo.blockSignals(False)
        self.ersatz_edit.blockSignals(False)

    def _on_row_selected(self) -> None:
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not rows:
            return
        item = self.table.item(rows[0].row(), 0)
        ident = canonical_field_name(str(item.data(256) if item is not None else "")) or "date"
        if self.field_combo.currentData() != ident:
            idx = self.field_combo.findData(ident)
            if idx >= 0:
                self.field_combo.blockSignals(True)
                self.field_combo.setCurrentIndex(idx)
                self.field_combo.blockSignals(False)
        self._sync_editors_from_spec(ident)

    def _on_combo_changed(self, _text: str) -> None:
        ident = self._current_ident()
        if ident not in self._specs and ident:
            self._specs[ident] = FieldTokenSpec(name=ident, format="text")
            self._rebuild_table(select=ident)
            return
        self._select_name(ident)

    def _on_format_changed(self, _idx: int) -> None:
        ident = self._current_ident()
        spec = self._spec_for(ident)
        if spec.builtin:
            return
        spec.format = canonical_field_format(self.format_combo.currentData())
        self._refresh_row(ident)

    def _on_value_changed(self, text: str) -> None:
        ident = self._current_ident()
        spec = self._spec_for(ident)
        if spec.builtin:
            return
        cleaned = safe_field_display(ident, text)
        spec.value = "" if cleaned == f"{{{ident}}}" else cleaned
        self._refresh_row(ident)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() != 2:
            return
        name_item = self.table.item(item.row(), 0)
        ident = canonical_field_name(str(name_item.data(256) if name_item is not None else ""))
        if not ident:
            return
        spec = self._spec_for(ident)
        if spec.builtin:
            return
        cleaned = safe_field_display(ident, item.text())
        spec.value = "" if cleaned == f"{{{ident}}}" else cleaned
        if ident == self._current_ident():
            self.ersatz_edit.blockSignals(True)
            self.ersatz_edit.setText(spec.value)
            self.ersatz_edit.blockSignals(False)

    def _refresh_row(self, ident: str) -> None:
        spec = self._spec_for(ident)
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is None or str(item.data(256) or "") != ident:
                continue
            fmt_item = self.table.item(row, 1)
            val_item = self.table.item(row, 2)
            if fmt_item is not None:
                fmt_item.setText(FIELD_FORMAT_LABELS.get(spec.format, spec.format))
                fmt_item.setData(256, spec.format)
            if val_item is not None:
                val_item.setText(spec.value)
            break
        self.table.blockSignals(False)

    def _add_custom(self) -> None:
        name, ok = QInputDialog.getText(self, "Feld hinzufügen", "Name des Ersatzzeichens:")
        if not ok:
            return
        ident = canonical_field_name(name)
        if not ident:
            QMessageBox.information(self, "Ersatzzeichen", "Bitte einen gültigen Feldnamen eingeben.")
            return
        if ident in self._specs:
            self._select_name(ident)
            return
        self._specs[ident] = FieldTokenSpec(name=ident, format="text")
        self._rebuild_table(select=ident)

    def _rename_custom(self) -> None:
        ident = self._current_ident()
        spec = self._spec_for(ident)
        if spec.builtin:
            return
        name, ok = QInputDialog.getText(
            self, "Feld umbenennen", "Neuer Name:", text=ident
        )
        if not ok:
            return
        new_ident = canonical_field_name(name)
        if not new_ident or new_ident == ident:
            return
        if new_ident in BUILTIN_FIELDS:
            QMessageBox.information(
                self, "Ersatzzeichen", "Der Name ist für ein festes Feld reserviert."
            )
            return
        self._specs.pop(ident, None)
        spec.name = new_ident
        self._specs[new_ident] = spec
        self._rebuild_table(select=new_ident)

    def _delete_custom(self) -> None:
        ident = self._current_ident()
        spec = self._spec_for(ident)
        if spec.builtin:
            return
        self._specs.pop(ident, None)
        self._rebuild_table(select="date")

    def _emit_insert(self) -> None:
        self._inserted = True
        self.insert_requested.emit()

    def did_insert(self) -> bool:
        return bool(self._inserted)

    def mark_inserted(self) -> None:
        self._inserted = True

    def result_field(self) -> tuple[str, str]:
        ident = self._current_ident()
        spec = self._spec_for(ident)
        display = safe_field_display(ident, spec.value or None)
        return ident, display

    def result_target(self) -> str:
        return canonical_insert_target(str(self.target_combo.currentData() or "body"))

    def result_header_footer(self) -> tuple[str, str]:
        return (self.header_edit.text() or ""), (self.footer_edit.text() or "")

    def result_specs(self) -> dict[str, FieldTokenSpec]:
        ident = self._current_ident()
        if ident and ident not in self._specs:
            self._spec_for(ident)
        return dict(self._specs)

    def insert_token_at_target(self, ident: str, display: str) -> str:
        """Caret in Kopf-/Fuß-Zeile; sonst ans Ende. Nie stiller No-Op."""
        token = display or f"{{{ident}}}"
        target = self.result_target()
        if target == "header":
            self._insert_into_line(self.header_edit, token)
        elif target == "footer":
            self._insert_into_line(self.footer_edit, token)
        return target

    @staticmethod
    def _insert_into_line(edit: QLineEdit, text: str) -> None:
        pos = edit.cursorPosition()
        cur = edit.text() or ""
        if pos < 0 or pos > len(cur):
            pos = len(cur)
        edit.setText(cur[:pos] + text + cur[pos:])
        edit.setCursorPosition(pos + len(text))
