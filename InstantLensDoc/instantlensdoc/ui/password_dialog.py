"""Dialog: PDF-Passwort setzen / entfernen / öffnen — 1.6.3."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
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
            "Unsicher — Standard aus. Passwort nie in Logs. — 1.6.3"
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
    """PDF-Kompression / Bilder-Downsample — Qualitäts-Dialog — 2.3.0/2.3.1.

    2.3.1: Vorher-Größe, DPI/Qualität-Presets (Bildschirm/E-Book/Druck), Abbruch via Fortschritt.
    """

    def __init__(self, parent=None, *, source_path: str | Path | None = None):
        super().__init__(parent)
        self.setWindowTitle("PDF komprimieren / Downsample")
        self.setObjectName("compressPdfDialog")
        self.resize(480, 340)
        self._source_path = Path(source_path) if source_path else None
        self._updating_preset = False
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Seiten via pypdfium2 rastern, optional Downsample, JPEG und "
                "per pikepdf als <b>neues File</b> speichern (verlustbehaftet). "
                "Abbruch im Fortschrittsdialog möglich — 2.3.1."
            )
        )
        form = QFormLayout()
        from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox, QSpinBox
        from ild_pdf.images import COMPRESS_PRESETS, format_byte_size
        from instantlensdoc.core.app_settings import (
            get_export_image_max_edge,
            get_export_jpeg_quality,
        )

        self.size_label = QLabel("—")
        self.size_label.setObjectName("compressSourceSize")
        if self._source_path and self._source_path.is_file():
            try:
                before = self._source_path.stat().st_size
                self.size_label.setText(
                    f"Vorher: {format_byte_size(before)} ({self._source_path.name})"
                )
            except OSError:
                self.size_label.setText("Vorher: (Größe unbekannt)")
        else:
            self.size_label.setText("Vorher: (kein PDF)")
        self.size_label.setToolTip("Quelldatei-Größe vor Kompression — 2.3.1")
        form.addRow("Dateigröße:", self.size_label)

        self.preset = QComboBox()
        self.preset.setObjectName("compressPreset")
        self._presets = COMPRESS_PRESETS
        for key in ("screen", "ebook", "print", "custom"):
            p = self._presets[key]
            self.preset.addItem(p["label"], key)
        self.preset.setToolTip(
            "DPI/Qualität-Presets: Bildschirm 72·Q50, E-Book 150·Q70, Druck 300·Q85 — 2.3.1"
        )
        self.preset.currentIndexChanged.connect(self._apply_preset)
        form.addRow("Preset:", self.preset)

        self.quality = QSpinBox()
        self.quality.setObjectName("compressJpegQuality")
        self.quality.setRange(20, 95)
        self.quality.setValue(min(95, max(20, get_export_jpeg_quality())))
        self.quality.setToolTip("JPEG-Qualität 20–95 (niedriger = kleiner)")
        self.max_edge = QSpinBox()
        self.max_edge.setObjectName("compressMaxEdge")
        self.max_edge.setRange(400, 4000)
        self.max_edge.setSingleStep(100)
        self.max_edge.setValue(min(4000, max(400, get_export_image_max_edge())))
        self.max_edge.setToolTip("Maximale Bildkante in Pixel (Downsample)")
        self.downsample = QCheckBox("Bilder downsample (max. Kante)")
        self.downsample.setObjectName("compressDownsample")
        self.downsample.setChecked(True)
        self.downsample.setToolTip(
            "Längste Kante auf Max. Kante begrenzen (pypdfium2-Raster → pikepdf) — 2.3.0"
        )
        self.downsample.toggled.connect(self.max_edge.setEnabled)
        self.render_scale = QDoubleSpinBox()
        self.render_scale.setObjectName("compressRenderScale")
        self.render_scale.setRange(0.5, 4.5)
        self.render_scale.setSingleStep(0.25)
        self.render_scale.setValue(1.5)
        self.render_scale.setDecimals(2)
        self.render_scale.setToolTip(
            "Raster-Skalierung vor Kompression (≈ DPI/72; höher = schärfer/größer) — 2.3.1"
        )
        self.dpi_hint = QLabel("")
        self.dpi_hint.setObjectName("compressDpiHint")
        self.quality.valueChanged.connect(self._mark_custom)
        self.max_edge.valueChanged.connect(self._mark_custom)
        self.render_scale.valueChanged.connect(self._on_scale_changed)
        self.downsample.toggled.connect(self._mark_custom)

        form.addRow("JPEG-Qualität:", self.quality)
        form.addRow(self.downsample)
        form.addRow("Max. Kante (px):", self.max_edge)
        form.addRow("Render-Scale:", self.render_scale)
        form.addRow("≈ DPI:", self.dpi_hint)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        idx = self.preset.findData("ebook")
        if idx >= 0:
            self.preset.setCurrentIndex(idx)
        self._apply_preset()

    def _on_scale_changed(self, _v=None) -> None:
        self._update_dpi_hint()
        self._mark_custom()

    def _update_dpi_hint(self) -> None:
        try:
            dpi = int(round(float(self.render_scale.value()) * 72.0))
            self.dpi_hint.setText(f"≈ {dpi} DPI")
        except Exception:
            self.dpi_hint.setText("")

    def _mark_custom(self, *_args) -> None:
        if self._updating_preset:
            return
        idx = self.preset.findData("custom")
        if idx >= 0 and self.preset.currentData() != "custom":
            self._updating_preset = True
            self.preset.setCurrentIndex(idx)
            self._updating_preset = False

    def _apply_preset(self, _i: int = 0) -> None:
        if self._updating_preset:
            return
        key = str(self.preset.currentData() or "custom")
        p = self._presets.get(key)
        if not p or key == "custom":
            self._update_dpi_hint()
            return
        self._updating_preset = True
        try:
            self.quality.setValue(int(p["jpeg_quality"]))
            self.max_edge.setValue(int(p["max_edge"]))
            self.render_scale.setValue(float(p["render_scale"]))
            self.downsample.setChecked(bool(p.get("downsample", True)))
        finally:
            self._updating_preset = False
        self._update_dpi_hint()

    def values(self) -> dict:
        key = str(self.preset.currentData() or "custom")
        return {
            "jpeg_quality": self.quality.value(),
            "max_edge": self.max_edge.value(),
            "downsample": bool(self.downsample.isChecked()),
            "render_scale": float(self.render_scale.value()),
            "preset": key,
            "dpi": int(round(float(self.render_scale.value()) * 72.0)),
        }
