"""Dialog: PDF-Passwort setzen / öffnen."""

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
        self.setWindowTitle("PDF-Passwort setzen")
        self.resize(420, 220)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                f"Passwortschutz für <b>{pdf_name or 'PDF'}</b><br>"
                "User-Passwort wird zum Öffnen benötigt."
            )
        )
        form = QFormLayout()
        self.user = QLineEdit()
        self.user.setEchoMode(QLineEdit.Password)
        self.owner = QLineEdit()
        self.owner.setEchoMode(QLineEdit.Password)
        self.owner.setPlaceholderText("(optional, sonst = User)")
        form.addRow("User-Passwort:", self.user)
        form.addRow("Owner-Passwort:", self.owner)
        layout.addLayout(form)
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

    def _accept(self):
        if not self.user.text():
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

        self.quality = QSpinBox()
        self.quality.setRange(20, 95)
        self.quality.setValue(70)
        self.max_edge = QSpinBox()
        self.max_edge.setRange(400, 4000)
        self.max_edge.setSingleStep(100)
        self.max_edge.setValue(2000)
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
