"""Dialog: Feld-Token / Ersatzzeichen (Datum, Seite, Custom) ohne Steuerzeichen."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)

from instantlensdoc.core.ocr_word_suite import canonical_field_name, safe_field_display

BUILTIN_FIELDS = ("date", "time", "page", "n", "total")


class FieldTokenDialog(QDialog):
    """Ersatzzeichen als ``{name}`` — ¶/Form-Feed werden auf das Token gemappt."""

    def __init__(self, parent=None, *, current_name: str = "date", ersatz: str = ""):
        super().__init__(parent)
        self.setObjectName("fieldTokenDialog")
        self.setWindowTitle("Ersatzzeichen")
        self.setModal(True)
        self.resize(420, 200)

        root = QVBoxLayout(self)
        form = QFormLayout()
        self.field_combo = QComboBox()
        self.field_combo.setObjectName("fieldTokenName")
        self.field_combo.setEditable(True)
        for name in BUILTIN_FIELDS:
            self.field_combo.addItem(f"{{{name}}}", name)
        ident = canonical_field_name(current_name) or "date"
        idx = self.field_combo.findData(ident)
        if idx >= 0:
            self.field_combo.setCurrentIndex(idx)
        else:
            self.field_combo.setEditText(ident)
        self.ersatz_edit = QLineEdit()
        self.ersatz_edit.setObjectName("fieldTokenErsatz")
        self.ersatz_edit.setText(ersatz or "")
        self.ersatz_edit.setPlaceholderText("leer = {name}; Steuerzeichen werden verworfen")
        form.addRow("Feld", self.field_combo)
        form.addRow("Ersatzzeichen", self.ersatz_edit)
        root.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.setObjectName("fieldTokenButtons")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def result_field(self) -> tuple[str, str]:
        data = self.field_combo.currentData()
        raw = str(data or self.field_combo.currentText() or "").strip()
        ident = canonical_field_name(raw) or canonical_field_name(
            raw.strip("{}")
        )
        ident = ident or "date"
        ersatz = safe_field_display(ident, self.ersatz_edit.text())
        return ident, ersatz
