"""Digitale Signatur (eIDAS-Pfad) — 2.6.22."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)


class ESignDialog(QDialog):
    def __init__(self, parent=None, *, pdf_path: str | None = None):
        super().__init__(parent)
        self.setWindowTitle("Digitale Signatur (eIDAS)")
        self.setObjectName("esignDialog")
        self.resize(520, 480)
        self._result: dict | None = None
        layout = QVBoxLayout(self)

        info = QLabel(
            "Zertifikatsbasierte Signatur (AES) bzw. SES-Stempel. "
            "QES erfordert ein QTSP-Zertifikat (PKCS#12 Import). "
            "Baut auf Verschlüsselung 2.6.7 auf — lokal, keine Cloud."
        )
        info.setWordWrap(True)
        info.setObjectName("esignInfo")
        layout.addWidget(info)

        form = QFormLayout()
        self.pdf_edit = QLineEdit(pdf_path or "")
        self.pdf_edit.setObjectName("esignPdfPath")
        row = QHBoxLayout()
        row.addWidget(self.pdf_edit)
        b = QPushButton("PDF…")
        b.clicked.connect(self._pick_pdf)
        row.addWidget(b)
        form.addRow("PDF", row)

        self.level = QComboBox()
        self.level.setObjectName("esignLevel")
        self.level.addItem("SES — einfache eSignatur", "SES")
        self.level.addItem("AES — fortgeschritten (Zertifikat)", "AES")
        self.level.addItem("QES — qualifiziert (QTSP-P12)", "QES")
        self.level.setCurrentIndex(1)
        self.level.currentIndexChanged.connect(self._on_level)
        form.addRow("eIDAS-Stufe", self.level)

        self.p12_edit = QLineEdit()
        self.p12_edit.setObjectName("esignP12Path")
        p12row = QHBoxLayout()
        p12row.addWidget(self.p12_edit)
        bp = QPushButton("PKCS#12…")
        bp.clicked.connect(self._pick_p12)
        p12row.addWidget(bp)
        bg = QPushButton("Self-Signed erzeugen…")
        bg.setObjectName("esignGenCertBtn")
        bg.clicked.connect(self._gen_cert)
        p12row.addWidget(bg)
        form.addRow("Zertifikat", p12row)

        self.p12_pw = QLineEdit()
        self.p12_pw.setEchoMode(QLineEdit.Password)
        self.p12_pw.setObjectName("esignP12Password")
        form.addRow("P12-Passwort", self.p12_pw)

        self.signer = QLineEdit()
        self.signer.setObjectName("esignSigner")
        form.addRow("Unterzeichner", self.signer)
        self.reason = QLineEdit()
        form.addRow("Grund", self.reason)
        self.location = QLineEdit()
        form.addRow("Ort", self.location)
        self.page = QSpinBox()
        self.page.setMinimum(1)
        self.page.setValue(1)
        form.addRow("Seite (1-basiert)", self.page)
        self.visible = QCheckBox("Sichtbarer Stempel")
        self.visible.setChecked(True)
        self.embed = QCheckBox("Signatur als Attachment einbetten")
        self.embed.setChecked(True)
        form.addRow(self.visible)
        form.addRow(self.embed)
        layout.addLayout(form)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(200)
        self.log.setObjectName("esignLog")
        layout.addWidget(self.log)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        self._sign_btn = buttons.addButton("Signieren", QDialogButtonBox.ActionRole)
        self._sign_btn.setObjectName("esignSignBtn")
        self._sign_btn.clicked.connect(self._sign)
        self._verify_btn = buttons.addButton("Prüfen", QDialogButtonBox.ActionRole)
        self._verify_btn.setObjectName("esignVerifyBtn")
        self._verify_btn.clicked.connect(self._verify)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._on_level()

    def _on_level(self):
        need = self.level.currentData() in ("AES", "QES")
        self.p12_edit.setEnabled(need)
        self.p12_pw.setEnabled(need)

    def _pick_pdf(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "PDF signieren", "", "PDF (*.pdf)"
        )
        if path:
            self.pdf_edit.setText(path)

    def _pick_p12(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "PKCS#12 Zertifikat", "", "PKCS#12 (*.p12 *.pfx);;Alle (*.*)"
        )
        if path:
            self.p12_edit.setText(path)

    def _gen_cert(self):
        from ild_pdf.esign import generate_self_signed_cert

        name = self.signer.text().strip() or "ILD Signer"
        dest, _ = QFileDialog.getSaveFileName(
            self,
            "PKCS#12 speichern",
            str(Path.home() / f"{name.replace(' ', '_')}.p12"),
            "PKCS#12 (*.p12)",
        )
        if not dest:
            return
        pw = self.p12_pw.text() or "ild-sign"
        try:
            info = generate_self_signed_cert(name, out_p12=dest, password=pw)
            self.p12_edit.setText(info["path"])
            if not self.p12_pw.text():
                self.p12_pw.setText(pw)
            self.log.appendPlainText(
                f"Zertifikat erzeugt: {info['path']} (bis {info['not_after'][:10]})"
            )
        except Exception as e:
            QMessageBox.warning(self, "Zertifikat", str(e))

    def _sign(self):
        from ild_pdf.esign import sign_pdf

        pdf = self.pdf_edit.text().strip()
        if not pdf or not Path(pdf).is_file():
            QMessageBox.warning(self, "Signatur", "PDF angeben.")
            return
        lvl = self.level.currentData()
        try:
            data = sign_pdf(
                pdf,
                level=lvl,
                p12_path=self.p12_edit.text().strip() or None,
                p12_password=self.p12_pw.text(),
                signer_name=self.signer.text().strip(),
                reason=self.reason.text().strip(),
                location=self.location.text().strip(),
                page=max(0, self.page.value() - 1),
                visible_stamp=self.visible.isChecked(),
                embed_attachment=self.embed.isChecked(),
            )
            self._result = data
            self.log.appendPlainText(
                f"OK: {data.get('out')} · Stufe {lvl} · "
                f"{data.get('count', 0)} Signatur(en)"
            )
            QMessageBox.information(
                self,
                "Signatur",
                f"Signiert ({lvl}):\n{data.get('out')}",
            )
        except Exception as e:
            self.log.appendPlainText(f"FEHLER: {e}")
            QMessageBox.warning(self, "Signatur", str(e))

    def _verify(self):
        from ild_pdf.esign import verify_signature, list_signatures

        pdf = self.pdf_edit.text().strip()
        if not pdf or not Path(pdf).is_file():
            # try signed sibling
            QMessageBox.warning(self, "Prüfen", "PDF angeben.")
            return
        try:
            listed = list_signatures(pdf)
            self.log.appendPlainText(
                f"Sidecar: {listed.get('count', 0)} Signatur(en) · "
                f"Levels {listed.get('levels')}"
            )
            data = verify_signature(
                pdf,
                p12_path=self.p12_edit.text().strip() or None,
                p12_password=self.p12_pw.text(),
            )
            self.log.appendPlainText(
                f"Verify ok={data.get('ok')} · {data.get('results')}"
            )
        except Exception as e:
            self.log.appendPlainText(f"FEHLER: {e}")
            QMessageBox.warning(self, "Prüfen", str(e))

    def result_data(self) -> dict | None:
        return self._result
