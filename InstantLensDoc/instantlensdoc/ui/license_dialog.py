"""Lizenzdialog."""

from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import Qt
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
from instantlensdoc.license import LicenseManager, format_resttage, resttage_phrase


def _format_expiry(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is not None:
        local = dt.astimezone()
    else:
        local = dt.replace(tzinfo=timezone.utc).astimezone()
    return local.strftime("%d.%m.%Y %H:%M")


class LicenseDialog(QDialog):
    def __init__(self, manager: LicenseManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("Lizenz — InstantLens Doc")
        self.resize(520, 280)

        layout = QVBoxLayout(self)
        st = manager.status()
        mode_de = {
            "trial": "Testversion",
            "licensed": "Aktiviert (Key)",
            "expired": "Abgelaufen",
        }.get(st.mode, st.mode)
        days = int(st.days_remaining)
        expiry = _format_expiry(st.expires_at)
        # Gleiche Formulierung wie Statusleiste / About — 1.0.2
        if st.mode == "expired":
            rest_line = f"Resttage: {format_resttage(0)} ({resttage_phrase(0)})"
        else:
            rest_line = f"Resttage: {format_resttage(days)} ({resttage_phrase(days)})"

        lines = [
            f"Status: {mode_de}",
            rest_line,
            f"Ablaufdatum: {expiry}",
            "",
            st.message,
            "",
            "Ohne Key: 4 Wochen Test. Keys gelten 30+2 Tage.",
            f"Neuen Key anfordern: {CONTACT_EMAIL}",
        ]
        if st.email:
            lines.insert(3, f"E-Mail: {st.email}")
        self.info = QLabel("\n".join(lines))
        self.info.setWordWrap(True)
        self.info.setTextInteractionFlags(Qt.TextSelectableByMouse)
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
