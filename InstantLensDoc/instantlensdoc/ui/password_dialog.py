"""Dialog: PDF-Passwort setzen / entfernen / öffnen — 1.6.1."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from ild_pdf.security import password_strength


def ask_pdf_password(parent: QWidget | None, path: str | Path) -> str | None:
    """Fragt nach dem Öffnen-Passwort. None = Abbruch."""
    from PySide6.QtWidgets import QInputDialog

    text, ok = QInputDialog.getText(
        parent,
        "PDF-Passwort",
        f"Passwort für:\n{Path(path).name}",
        QLineEdit.Password,
    )
    if not ok:
        return None
    return text


class SetPasswordDialog(QDialog):
    def __init__(self, parent=None, pdf_name: str = ""):
        super().__init__(parent)
        self.setWindowTitle("PDF verschlüsseln")
        self.resize(420, 280)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                f"Passwortschutz für <b>{pdf_name or 'PDF'}</b><br>"
                "User-Passwort wird zum Öffnen benötigt. Owner optional."
            )
        )
        form = QFormLayout()
        self.user = QLineEdit()
        self.user.setEchoMode(QLineEdit.Password)
        self.owner = QLineEdit()
        self.owner.setEchoMode(QLineEdit.Password)
        self.owner.setPlaceholderText("(optional, sonst = User)")
        form.addRow("User-Passwort:", self.user)
        self.strength_label = QLabel("Stärke: —")
        self.strength_label.setStyleSheet("color:#666;")
        form.addRow("", self.strength_label)
        form.addRow("Owner-Passwort:", self.owner)
        layout.addLayout(form)
        self.user.textChanged.connect(self._update_strength)
        self.allow_print = QCheckBox("Drucken erlauben")
        self.allow_print.setChecked(True)
        self.allow_modify = QCheckBox("Ändern erlauben")
        self.allow_extract = QCheckBox("Kopieren/Extrahieren erlauben")
        layout.addWidget(self.allow_print)
        layout.addWidget(self.allow_modify)
        layout.addWidget(self.allow_extract)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._update_strength()

    def _update_strength(self, *_):
        label, score = password_strength(self.user.text())
        colors = {
            0: "#b71c1c",
            1: "#e65100",
            2: "#f9a825",
            3: "#558b2f",
            4: "#2e7d32",
        }
        color = colors.get(score, "#666")
        self.strength_label.setText(f"Stärke: {label}")
        self.strength_label.setStyleSheet(f"color:{color};")

    def _accept(self):
        # Leeres Passwort ablehnen — 1.6.1
        if not self.user.text().strip():
            QMessageBox.warning(self, "Passwort", "User-Passwort darf nicht leer sein.")
            return
        self.accept()

    def values(self) -> dict:
        owner = self.owner.text() or None
        return {
            "user_password": self.user.text(),
            "owner_password": owner,
            "allow_printing": self.allow_print.isChecked(),
            "allow_modify": self.allow_modify.isChecked(),
            "allow_extract": self.allow_extract.isChecked(),
        }


class RemovePasswordDialog(QDialog):
    """PDF entschlüsseln: User-/Owner-Passwort, speichert ungeschütztes PDF — 1.6.0."""

    def __init__(self, parent=None, pdf_name: str = ""):
        super().__init__(parent)
        self.setWindowTitle("PDF entschlüsseln")
        self.resize(420, 200)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                f"Verschlüsselung entfernen für <b>{pdf_name or 'PDF'}</b><br>"
                "Gültiges User- oder Owner-Passwort erforderlich."
            )
        )
        form = QFormLayout()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        form.addRow("Passwort:", self.password)
        layout.addLayout(form)
        self.inplace = QCheckBox("Original überschreiben")
        self.inplace.setChecked(False)
        self.inplace.setToolTip("Standard: neues PDF (*_unlocked.pdf)")
        layout.addWidget(self.inplace)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self):
        if not self.password.text().strip():
            QMessageBox.warning(self, "Passwort", "Passwort darf nicht leer sein.")
            return
        self.accept()

    def values(self) -> dict:
        return {
            "password": self.password.text(),
            "inplace": self.inplace.isChecked(),
        }


class CompressPdfDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PDF-Bildkompression")
        self.resize(400, 180)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Seiten als JPEG neu einbetten (verlustbehaftet).<br>"
                "Reduziert die Dateigröße von Scan-/Bild-PDFs."
            )
        )
        form = QFormLayout()
        from PySide6.QtWidgets import QSpinBox
        from instantlensdoc.core.app_settings import get_export_image_max_edge, get_export_jpeg_quality

        self.quality = QSpinBox()
        self.quality.setRange(20, 95)
        self.quality.setValue(min(95, max(20, get_export_jpeg_quality())))
        self.max_edge = QSpinBox()
        self.max_edge.setRange(400, 4000)
        self.max_edge.setSingleStep(100)
        self.max_edge.setValue(min(4000, max(400, get_export_image_max_edge())))
        form.addRow("JPEG-Qualität:", self.quality)
        form.addRow("Max. Kante (px):", self.max_edge)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> dict:
        return {
            "jpeg_quality": self.quality.value(),
            "max_edge": self.max_edge.value(),
        }
