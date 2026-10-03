"""Dialog: PDF-Passwort setzen / entfernen / öffnen — 1.6.2."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from ild_pdf.security import WRONG_PASSWORD_MSG_DE, password_strength
from instantlensdoc.core.app_settings import (
    get_crypto_reload_prefill_password,
    set_crypto_reload_prefill_password,
)


def ask_pdf_password(
    parent: QWidget | None,
    path: str | Path,
    *,
    prefill: str = "",
    wrong_password: bool = False,
) -> str | None:
    """
    Fragt nach dem Öffnen-Passwort. None = Abbruch.
    prefill: vorausgefülltes Passwort (nur wenn Settings-Toggle an) — 1.6.2.
    wrong_password: klarer DE-Hinweis bei erneutem Versuch — 1.6.2.
    """
    from PySide6.QtWidgets import QInputDialog

    hint = ""
    if wrong_password:
        hint = f"{WRONG_PASSWORD_MSG_DE}\n\n"
    text, ok = QInputDialog.getText(
        parent,
        "PDF-Passwort",
        f"{hint}Passwort für:\n{Path(path).name}",
        QLineEdit.Password,
        prefill or "",
    )
    if not ok:
        return None
    return text


class SetPasswordDialog(QDialog):
    def __init__(self, parent=None, pdf_name: str = ""):
        super().__init__(parent)
        self.setWindowTitle("PDF verschlüsseln")
        self.resize(420, 320)
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
        # Reload-Prefill Toggle (unsicher, default aus) — 1.6.2
        self.prefill_reload = QCheckBox(
            "Passwort beim Neu-Laden vorausfüllen (unsicher)"
        )
        self.prefill_reload.setChecked(bool(get_crypto_reload_prefill_password()))
        self.prefill_reload.setToolTip(
            "Speichert das Passwort kurz für den Reload-Dialog. "
            "Unsicher — Standard aus. — 1.6.2"
        )
        layout.addWidget(self.prefill_reload)
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
        set_crypto_reload_prefill_password(self.prefill_reload.isChecked())
        self.accept()

    def values(self) -> dict:
        owner = self.owner.text() or None
        return {
            "user_password": self.user.text(),
            "owner_password": owner,
            "allow_printing": self.allow_print.isChecked(),
            "allow_modify": self.allow_modify.isChecked(),
            "allow_extract": self.allow_extract.isChecked(),
            "prefill_reload": self.prefill_reload.isChecked(),
        }


class RemovePasswordDialog(QDialog):
    """PDF entschlüsseln: User-/Owner-Passwort, speichert ungeschütztes PDF — 1.6.0/1.6.2."""

    def __init__(self, parent=None, pdf_name: str = ""):
        super().__init__(parent)
        self.setWindowTitle("PDF entschlüsseln")
        self.resize(420, 240)
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
        self.prefill_reload = QCheckBox(
            "Passwort beim Neu-Laden vorausfüllen (unsicher)"
        )
        self.prefill_reload.setChecked(bool(get_crypto_reload_prefill_password()))
        self.prefill_reload.setToolTip(
            "Nur relevant wenn die Zieldatei noch geschützt ist. Unsicher — Standard aus. — 1.6.2"
        )
        layout.addWidget(self.prefill_reload)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self):
        if not self.password.text().strip():
            QMessageBox.warning(self, "Passwort", "Passwort darf nicht leer sein.")
            return
        set_crypto_reload_prefill_password(self.prefill_reload.isChecked())
        self.accept()

    def values(self) -> dict:
        return {
            "password": self.password.text(),
            "inplace": self.inplace.isChecked(),
            "prefill_reload": self.prefill_reload.isChecked(),
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
