"""Lizenzdialog."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from instantlensdoc.config import CONTACT_EMAIL
from instantlensdoc.license import LicenseManager


class LicenseDialog(QDialog):
    def __init__(self, manager: LicenseManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("Lizenz — InstantLens Doc")
        self.resize(480, 220)

        layout = QVBoxLayout(self)
        st = manager.status()
        self.info = QLabel(
            f"Status: {st.mode}\n{st.message}\n\n"
            f"Ohne Key: 4 Wochen Test. Keys gelten 30+2 Tage.\n"
            f"Neuen Key anfordern: {CONTACT_EMAIL}"
        )
        self.info.setWordWrap(True)
        layout.addWidget(self.info)

        form = QFormLayout()
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("ILD1....")
        form.addRow("Lizenzschlüssel:", self.key_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._activate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _activate(self):
        key = self.key_edit.text().strip()
        if not key:
            self.accept()
            return
        ok, msg = self.manager.activate(key)
        if ok:
            QMessageBox.information(self, "Lizenz", msg)
            self.accept()
        else:
            QMessageBox.warning(self, "Lizenz", msg)
