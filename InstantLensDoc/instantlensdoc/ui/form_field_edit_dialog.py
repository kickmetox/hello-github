"""Dialog: AcroForm-Feld anlegen/bearbeiten — 2.6.6."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class FormFieldEditDialog(QDialog):
    """Name/Typ/Optionen/Wert für neues oder bestehendes Formularfeld."""

    TYPE_LABELS = (
        ("text", "Textfeld"),
        ("checkbox", "Checkbox"),
        ("choice", "Dropdown"),
    )

    def __init__(
        self,
        parent=None,
        *,
        title: str = "Formularfeld",
        name: str = "",
        field_type: str = "text",
        options: list[str] | None = None,
        value: str = "",
        required: bool = False,
        allow_type_change: bool = True,
        hint: str = "",
    ):
        super().__init__(parent)
        self.setObjectName("formFieldEditDialog")
        self.setWindowTitle(title)
        self.resize(420, 280)
        layout = QVBoxLayout(self)
        if hint:
            lbl = QLabel(hint)
            lbl.setObjectName("formFieldEditHint")
            lbl.setWordWrap(True)
            layout.addWidget(lbl)
        form = QFormLayout()
        self.name_edit = QLineEdit(name or "")
        self.name_edit.setObjectName("formFieldEditName")
        self.name_edit.setPlaceholderText("Feldname…")
        form.addRow("Name:", self.name_edit)

        self.type_combo = QComboBox()
        self.type_combo.setObjectName("formFieldEditType")
        for key, label in self.TYPE_LABELS:
            self.type_combo.addItem(label, key)
        idx = max(0, self.type_combo.findData(field_type if field_type in ("text", "checkbox", "choice") else "text"))
        self.type_combo.setCurrentIndex(idx)
        self.type_combo.setEnabled(bool(allow_type_change))
        self.type_combo.currentIndexChanged.connect(self._sync_type_ui)
        form.addRow("Typ:", self.type_combo)

        self.options_edit = QLineEdit(", ".join(options or []))
        self.options_edit.setObjectName("formFieldEditOptions")
        self.options_edit.setPlaceholderText("Optionen (Komma) für Dropdown")
        form.addRow("Optionen:", self.options_edit)

        self.value_edit = QLineEdit(value or "")
        self.value_edit.setObjectName("formFieldEditValue")
        self.value_edit.setPlaceholderText("Anfangswert…")
        form.addRow("Wert:", self.value_edit)

        self.value_check = QCheckBox("Aktiviert")
        self.value_check.setObjectName("formFieldEditCheckValue")
        on = str(value).strip().lower() in (
            "1",
            "true",
            "yes",
            "ja",
            "on",
            "x",
            "checked",
        )
        self.value_check.setChecked(on)
        form.addRow("Checkbox:", self.value_check)

        self.required = QCheckBox("Pflichtfeld")
        self.required.setObjectName("formFieldEditRequired")
        self.required.setChecked(bool(required))
        form.addRow("", self.required)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._sync_type_ui()
        self.name_edit.setFocus(Qt.FocusReason.OtherFocusReason)

    def _sync_type_ui(self, *_args) -> None:
        ftype = str(self.type_combo.currentData() or "text")
        self.options_edit.setEnabled(ftype == "choice")
        self.value_edit.setVisible(ftype != "checkbox")
        self.value_check.setVisible(ftype == "checkbox")

    def values(self) -> dict:
        ftype = str(self.type_combo.currentData() or "text")
        opts = [
            p.strip()
            for p in (self.options_edit.text() or "").split(",")
            if p.strip()
        ]
        if ftype == "checkbox":
            value = "true" if self.value_check.isChecked() else "false"
        else:
            value = self.value_edit.text()
        return {
            "name": (self.name_edit.text() or "").strip() or "Feld",
            "field_type": ftype,
            "options": opts,
            "value": value,
            "required": bool(self.required.isChecked()),
        }
