"""Dialog: PDF-Passwort setzen / entfernen / öffnen / Rechte — 1.6.3 / 2.6.7."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ild_pdf.security import (
    WRONG_PASSWORD_MSG_DE,
    EncryptionInfo,
    PdfPermissionFlags,
    get_encryption_info,
    password_strength,
)
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


def _make_permission_checks(
    parent: QWidget,
    *,
    flags: PdfPermissionFlags | None = None,
) -> dict[str, QCheckBox]:
    """Gemeinsame Rechte-Checkboxen — 2.6.7."""
    f = flags or PdfPermissionFlags()
    checks: dict[str, QCheckBox] = {}
    specs = (
        ("allow_printing", "Drucken erlauben (niedrige Auflösung)", f.allow_printing),
        ("allow_print_highres", "Drucken in hoher Auflösung", f.allow_print_highres),
        ("allow_extract", "Kopieren / Extrahieren erlauben", f.allow_extract),
        ("allow_modify", "Inhalt ändern erlauben", f.allow_modify),
        ("allow_modify_annotation", "Annotationen ändern erlauben", f.allow_modify_annotation),
        ("allow_modify_form", "Formulare ausfüllen erlauben", f.allow_modify_form),
        ("allow_modify_assembly", "Seiten zusammenstellen erlauben", f.allow_modify_assembly),
        ("allow_accessibility", "Barrierefreiheit / Screenreader", f.allow_accessibility),
    )
    for key, label, checked in specs:
        cb = QCheckBox(label, parent)
        cb.setObjectName(f"securityPerm_{key}")
        cb.setChecked(bool(checked))
        checks[key] = cb
    return checks


def _flags_from_checks(checks: dict[str, QCheckBox]) -> PdfPermissionFlags:
    return PdfPermissionFlags(
        **{k: bool(cb.isChecked()) for k, cb in checks.items()}
    )


class SetPasswordDialog(QDialog):
    def __init__(
        self,
        parent=None,
        pdf_name: str = "",
        *,
        initial_flags: PdfPermissionFlags | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("PDF verschlüsseln")
        self.setObjectName("setPasswordDialog")
        self.resize(460, 480)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                f"Passwortschutz für <b>{pdf_name or 'PDF'}</b><br>"
                "User-Passwort wird zum Öffnen benötigt. Owner optional.<br>"
                "<b>AES-256</b> (R=6) bevorzugt; Fallback AES-128 — 2.6.7"
            )
        )
        self.algo_label = QLabel("Verschlüsselung: AES-256 (bevorzugt)")
        self.algo_label.setObjectName("setPasswordAlgoLabel")
        self.algo_label.setStyleSheet("color:#2e7d32; font-weight:600;")
        layout.addWidget(self.algo_label)
        form = QFormLayout()
        self.user = QLineEdit()
        self.user.setObjectName("setPasswordUser")
        self.user.setEchoMode(QLineEdit.Password)
        self.owner = QLineEdit()
        self.owner.setObjectName("setPasswordOwner")
        self.owner.setEchoMode(QLineEdit.Password)
        self.owner.setPlaceholderText("(optional, sonst = User)")
        form.addRow("User-Passwort:", self.user)
        self.strength_label = QLabel("Stärke: —")
        self.strength_label.setStyleSheet("color:#666;")
        form.addRow("", self.strength_label)
        form.addRow("Owner-Passwort:", self.owner)
        layout.addLayout(form)
        self.user.textChanged.connect(self._update_strength)
        self.aes256 = QCheckBox("AES-256 bevorzugen (sonst AES-128)")
        self.aes256.setObjectName("setPasswordAes256")
        self.aes256.setChecked(True)
        self.aes256.setToolTip("pikepdf/qpdf: R=6 / AESV3 wenn möglich — 2.6.7")
        layout.addWidget(self.aes256)
        box = QGroupBox("Rechte (Owner-Permissions)")
        box.setObjectName("setPasswordPermBox")
        box_l = QVBoxLayout(box)
        self._perm_checks = _make_permission_checks(self, flags=initial_flags)
        # Legacy-Aliase für Smoke/1.6.x
        self.allow_print = self._perm_checks["allow_printing"]
        self.allow_modify = self._perm_checks["allow_modify"]
        self.allow_extract = self._perm_checks["allow_extract"]
        for cb in self._perm_checks.values():
            box_l.addWidget(cb)
        layout.addWidget(box)
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
        flags = _flags_from_checks(self._perm_checks)
        return {
            "user_password": self.user.text(),
            "owner_password": owner,
            "allow_printing": flags.allow_printing,
            "allow_modify": flags.allow_modify,
            "allow_extract": flags.allow_extract,
            "permissions": flags,
            "aes256": bool(self.aes256.isChecked()),
            "prefill_reload": self.prefill_reload.isChecked(),
        }


class RemovePasswordDialog(QDialog):
    """PDF entschlüsseln: User-/Owner-Passwort, speichert ungeschütztes PDF — 1.6.0/1.6.2."""

    def __init__(self, parent=None, pdf_name: str = ""):
        super().__init__(parent)
        self.setWindowTitle("PDF entschlüsseln")
        self.setObjectName("removePasswordDialog")
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
        self.password.setObjectName("removePasswordField")
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


class PdfSecurityDialog(QDialog):
    """Verschlüsselung & Rechte — Status, setzen, entfernen, Permissions — 2.6.7."""

    ACTION_NONE = "none"
    ACTION_SET = "set"
    ACTION_REMOVE = "remove"
    ACTION_UPDATE_PERMS = "update_perms"

    def __init__(
        self,
        parent=None,
        *,
        pdf_path: str | Path | None = None,
        password: str | None = None,
        pdf_name: str = "",
    ):
        super().__init__(parent)
        self.setWindowTitle("Verschlüsselung & Rechte")
        self.setObjectName("pdfSecurityDialog")
        self.resize(520, 560)
        self._pdf_path = Path(pdf_path) if pdf_path else None
        self._password = password
        self._action = self.ACTION_NONE
        self._info: EncryptionInfo | None = None

        layout = QVBoxLayout(self)
        name = pdf_name or (self._pdf_path.name if self._pdf_path else "PDF")
        layout.addWidget(
            QLabel(
                f"<b>{name}</b> — Passwortschutz und Rechte (AES-256 bevorzugt)"
            )
        )
        self.status_label = QLabel("Status: …")
        self.status_label.setObjectName("pdfSecurityStatus")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("pdfSecurityTabs")

        # --- Schützen ---
        tab_set = QWidget()
        set_l = QVBoxLayout(tab_set)
        form = QFormLayout()
        self.user = QLineEdit()
        self.user.setObjectName("pdfSecurityUser")
        self.user.setEchoMode(QLineEdit.Password)
        self.owner = QLineEdit()
        self.owner.setObjectName("pdfSecurityOwner")
        self.owner.setEchoMode(QLineEdit.Password)
        self.owner.setPlaceholderText("(optional, sonst = User)")
        form.addRow("User-Passwort:", self.user)
        self.strength_label = QLabel("Stärke: —")
        form.addRow("", self.strength_label)
        form.addRow("Owner-Passwort:", self.owner)
        set_l.addLayout(form)
        self.user.textChanged.connect(self._update_strength)
        self.aes256 = QCheckBox("AES-256 bevorzugen")
        self.aes256.setObjectName("pdfSecurityAes256")
        self.aes256.setChecked(True)
        set_l.addWidget(self.aes256)
        self.inplace_set = QCheckBox("Original überschreiben")
        self.inplace_set.setObjectName("pdfSecurityInplaceSet")
        self.inplace_set.setChecked(False)
        self.inplace_set.setToolTip("Standard: neues PDF (*_locked.pdf)")
        set_l.addWidget(self.inplace_set)
        box = QGroupBox("Rechte beim Verschlüsseln")
        box.setObjectName("pdfSecurityPermBox")
        box_l = QVBoxLayout(box)
        self._perm_checks = _make_permission_checks(self)
        for cb in self._perm_checks.values():
            box_l.addWidget(cb)
        set_l.addWidget(box)
        self.prefill_reload = QCheckBox(
            "Passwort beim Neu-Laden vorausfüllen (unsicher)"
        )
        self.prefill_reload.setChecked(bool(get_crypto_reload_prefill_password()))
        set_l.addWidget(self.prefill_reload)
        btn_set = QPushButton("Verschlüsseln…")
        btn_set.setObjectName("pdfSecuritySetBtn")
        btn_set.clicked.connect(self._accept_set)
        set_l.addWidget(btn_set)
        set_l.addStretch(1)
        self.tabs.addTab(tab_set, "Schützen")

        # --- Entfernen ---
        tab_rm = QWidget()
        rm_l = QVBoxLayout(tab_rm)
        rm_l.addWidget(
            QLabel("Verschlüsselung entfernen — gültiges Passwort erforderlich.")
        )
        form_rm = QFormLayout()
        self.rm_password = QLineEdit()
        self.rm_password.setObjectName("pdfSecurityRemovePassword")
        self.rm_password.setEchoMode(QLineEdit.Password)
        if password:
            self.rm_password.setText(password)
        form_rm.addRow("Passwort:", self.rm_password)
        rm_l.addLayout(form_rm)
        self.inplace_rm = QCheckBox("Original überschreiben")
        self.inplace_rm.setObjectName("pdfSecurityInplaceRemove")
        self.inplace_rm.setChecked(False)
        rm_l.addWidget(self.inplace_rm)
        btn_rm = QPushButton("Entschlüsseln…")
        btn_rm.setObjectName("pdfSecurityRemoveBtn")
        btn_rm.clicked.connect(self._accept_remove)
        rm_l.addWidget(btn_rm)
        rm_l.addStretch(1)
        self.tabs.addTab(tab_rm, "Entfernen")

        # --- Rechte aktualisieren ---
        tab_perm = QWidget()
        perm_l = QVBoxLayout(tab_perm)
        perm_l.addWidget(
            QLabel(
                "Rechte eines geschützten PDFs ändern (Owner-Passwort; "
                "User-Passwort für erneutes Verschlüsseln)."
            )
        )
        form_p = QFormLayout()
        self.upd_user = QLineEdit()
        self.upd_user.setObjectName("pdfSecurityUpdateUser")
        self.upd_user.setEchoMode(QLineEdit.Password)
        self.upd_owner = QLineEdit()
        self.upd_owner.setObjectName("pdfSecurityUpdateOwner")
        self.upd_owner.setEchoMode(QLineEdit.Password)
        if password:
            self.upd_user.setText(password)
            self.upd_owner.setText(password)
        form_p.addRow("User-Passwort:", self.upd_user)
        form_p.addRow("Owner-Passwort:", self.upd_owner)
        perm_l.addLayout(form_p)
        box2 = QGroupBox("Neue Rechte")
        box2_l = QVBoxLayout(box2)
        self._upd_perm_checks = _make_permission_checks(self)
        for cb in self._upd_perm_checks.values():
            # objectName uniqueness
            cb.setObjectName(cb.objectName() + "_upd")
            box2_l.addWidget(cb)
        perm_l.addWidget(box2)
        self.inplace_upd = QCheckBox("Original überschreiben")
        self.inplace_upd.setChecked(True)
        perm_l.addWidget(self.inplace_upd)
        btn_upd = QPushButton("Rechte speichern…")
        btn_upd.setObjectName("pdfSecurityUpdatePermsBtn")
        btn_upd.clicked.connect(self._accept_update_perms)
        perm_l.addWidget(btn_upd)
        perm_l.addStretch(1)
        self.tabs.addTab(tab_perm, "Rechte")

        layout.addWidget(self.tabs)
        close_box = QDialogButtonBox(QDialogButtonBox.Close)
        close_box.rejected.connect(self.reject)
        close_box.accepted.connect(self.reject)
        layout.addWidget(close_box)

        self.refresh_status()
        self._update_strength()

    def refresh_status(self) -> None:
        if not self._pdf_path or not self._pdf_path.is_file():
            self.status_label.setText("Status: keine PDF-Datei")
            return
        try:
            info = get_encryption_info(self._pdf_path, password=self._password)
        except Exception as e:
            self.status_label.setText(f"Status: Fehler — {e}")
            return
        self._info = info
        self.status_label.setText(f"Status: {info.label_de()}")
        if info.permissions is not None:
            for key, cb in self._perm_checks.items():
                cb.setChecked(bool(getattr(info.permissions, key)))
            for key, cb in self._upd_perm_checks.items():
                cb.setChecked(bool(getattr(info.permissions, key)))
        # Tab-Hinweis
        if info.encrypted:
            self.tabs.setTabEnabled(1, True)
            self.tabs.setTabEnabled(2, True)
        else:
            self.tabs.setCurrentIndex(0)

    def _update_strength(self, *_):
        label, score = password_strength(self.user.text())
        colors = {
            0: "#b71c1c",
            1: "#e65100",
            2: "#f9a825",
            3: "#558b2f",
            4: "#2e7d32",
        }
        self.strength_label.setText(f"Stärke: {label}")
        self.strength_label.setStyleSheet(f"color:{colors.get(score, '#666')};")

    def _accept_set(self):
        if not self.user.text().strip():
            QMessageBox.warning(self, "Passwort", "User-Passwort darf nicht leer sein.")
            return
        set_crypto_reload_prefill_password(self.prefill_reload.isChecked())
        self._action = self.ACTION_SET
        self.accept()

    def _accept_remove(self):
        if not self.rm_password.text().strip():
            QMessageBox.warning(self, "Passwort", "Passwort darf nicht leer sein.")
            return
        self._action = self.ACTION_REMOVE
        self.accept()

    def _accept_update_perms(self):
        if not self.upd_user.text().strip() or not self.upd_owner.text().strip():
            QMessageBox.warning(
                self, "Passwort", "User- und Owner-Passwort erforderlich."
            )
            return
        self._action = self.ACTION_UPDATE_PERMS
        self.accept()

    def action(self) -> str:
        return self._action

    def values(self) -> dict:
        act = self._action
        if act == self.ACTION_SET:
            flags = _flags_from_checks(self._perm_checks)
            return {
                "action": act,
                "user_password": self.user.text(),
                "owner_password": self.owner.text() or None,
                "permissions": flags,
                "aes256": bool(self.aes256.isChecked()),
                "inplace": bool(self.inplace_set.isChecked()),
                "prefill_reload": bool(self.prefill_reload.isChecked()),
                "allow_printing": flags.allow_printing,
                "allow_modify": flags.allow_modify,
                "allow_extract": flags.allow_extract,
            }
        if act == self.ACTION_REMOVE:
            return {
                "action": act,
                "password": self.rm_password.text(),
                "inplace": bool(self.inplace_rm.isChecked()),
                "prefill_reload": bool(self.prefill_reload.isChecked()),
            }
        if act == self.ACTION_UPDATE_PERMS:
            flags = _flags_from_checks(self._upd_perm_checks)
            return {
                "action": act,
                "user_password": self.upd_user.text(),
                "owner_password": self.upd_owner.text(),
                "permissions": flags,
                "aes256": True,
                "inplace": bool(self.inplace_upd.isChecked()),
                "prefill_reload": bool(self.prefill_reload.isChecked()),
            }
        return {"action": self.ACTION_NONE}


class CompressPdfDialog(QDialog):
    """PDF-Kompression / Bilder-Downsample — Qualitäts-Dialog — 2.3.0–2.3.2.

    2.3.1: Vorher-Größe, DPI/Qualität-Presets, Abbruch.
    2.3.2: optional neues File öffnen; Größenersparnis-% im Status.
    """

    def __init__(self, parent=None, *, source_path: str | Path | None = None):
        super().__init__(parent)
        self.setWindowTitle("PDF komprimieren / Downsample")
        self.setObjectName("compressPdfDialog")
        self.resize(480, 380)
        self._source_path = Path(source_path) if source_path else None
        self._updating_preset = False
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Seiten via pypdfium2 rastern, optional Downsample, JPEG und "
                "per pikepdf als <b>neues File</b> speichern (verlustbehaftet). "
                "Abbruch im Fortschrittsdialog möglich. "
                "„Öffnen“-Toggle wird in Einstellungen gemerkt — 2.3.3."
            )
        )
        form = QFormLayout()
        from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox, QSpinBox
        from ild_pdf.images import COMPRESS_PRESETS, format_byte_size
        from instantlensdoc.core.app_settings import (
            get_compress_open_after,
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

        self.open_after = QCheckBox("Ergebnis nach Kompression öffnen")
        self.open_after.setObjectName("compressOpenAfter")
        self.open_after.setAccessibleName("Ergebnis nach Kompression öffnen")
        self.open_after.setAccessibleDescription(
            "Öffnet das komprimierte Ergebnis-PDF nach erfolgreicher Speicherung. "
            "Toggle wird in den Einstellungen gemerkt. "
            "Ersparnis-% in der Statuszeile wird für Screenreader announced — 2.3.5"
        )
        self.open_after.setChecked(bool(get_compress_open_after()))
        self.open_after.setToolTip(
            "Ergebnis nach Kompression öffnen — Toggle in Einstellungen gemerkt. "
            "Ersparnis-% Status wird announced — 2.3.5"
        )
        form.addRow(self.open_after)

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
            "open_after": bool(self.open_after.isChecked()),
        }
