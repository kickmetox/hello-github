"""PAdES-Signatur- und Validierungsdialog."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
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
    QVBoxLayout,
)

from instantlensdoc.features.pades import QES_NOTE, sign_pades_b, validate_pades


class PadesDialog(QDialog):
    def __init__(self, parent=None, *, pdf_path: str = ""):
        super().__init__(parent)
        self.setObjectName("padesDialog")
        self.setWindowTitle("E-Signatur PAdES / QES")
        self.resize(540, 480)
        layout = QVBoxLayout(self)
        note = QLabel(QES_NOTE)
        note.setWordWrap(True)
        note.setObjectName("padesQesNote")
        layout.addWidget(note)

        form = QFormLayout()
        self.pdf_edit = QLineEdit(pdf_path)
        self.pdf_edit.setObjectName("padesPdfPath")
        row = QHBoxLayout()
        row.addWidget(self.pdf_edit)
        b = QPushButton("PDF…")
        b.clicked.connect(self._pick_pdf)
        row.addWidget(b)
        form.addRow("PDF", row)

        self.p12_edit = QLineEdit()
        self.p12_edit.setObjectName("padesP12Path")
        r2 = QHBoxLayout()
        r2.addWidget(self.p12_edit)
        bp = QPushButton("PKCS#12…")
        bp.clicked.connect(self._pick_p12)
        r2.addWidget(bp)
        form.addRow("Zertifikat", r2)

        self.pw = QLineEdit()
        self.pw.setEchoMode(QLineEdit.Password)
        self.pw.setObjectName("padesPassword")
        form.addRow("Passwort", self.pw)
        self.reason = QLineEdit("PAdES-B")
        form.addRow("Grund", self.reason)
        self.visible = QCheckBox("Sichtbares Signatur-Widget")
        self.visible.setChecked(True)
        form.addRow(self.visible)
        layout.addLayout(form)

        brow = QHBoxLayout()
        sign = QPushButton("PAdES-B signieren")
        sign.setObjectName("padesSignBtn")
        sign.clicked.connect(self._sign)
        brow.addWidget(sign)
        val = QPushButton("Validieren")
        val.setObjectName("padesValidateBtn")
        val.clicked.connect(self._validate)
        brow.addWidget(val)
        layout.addLayout(brow)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setObjectName("padesLog")
        layout.addWidget(self.log, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _pick_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "PDF", "", "PDF (*.pdf)")
        if path:
            self.pdf_edit.setText(path)

    def _pick_p12(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "PKCS#12", "", "PKCS#12 (*.p12 *.pfx)")
        if path:
            self.p12_edit.setText(path)

    def _sign(self) -> None:
        pdf, p12 = self.pdf_edit.text().strip(), self.p12_edit.text().strip()
        if not pdf or not p12:
            QMessageBox.warning(self, "PAdES", "PDF und PKCS#12 angeben.")
            return
        try:
            res = sign_pades_b(
                pdf,
                p12,
                self.pw.text(),
                reason=self.reason.text(),
                box=(50, 50, 250, 120) if self.visible.isChecked() else (0, 0, 1, 1),
            )
            self.log.setPlainText(
                f"OK → {res.get('out')}\nProfil {res.get('profile')}\n{res.get('qes_note')}"
            )
        except Exception as exc:
            self.log.setPlainText(f"Fehler: {exc}")

    def _validate(self) -> None:
        pdf = self.pdf_edit.text().strip()
        if not pdf:
            return
        try:
            res = validate_pades(pdf, p12_path=self.p12_edit.text().strip() or None, password=self.pw.text())
            lines = [
                f"Signaturen: {res.get('count')}",
                res.get("message") or "",
                res.get("qes_note") or "",
            ]
            for s in res.get("signatures") or []:
                lines.append(
                    f"- {s.get('field')}: trusted={s.get('trusted')} bottom_line={s.get('bottom_line')} {s.get('summary')}"
                )
            self.log.setPlainText("\n".join(lines))
        except Exception as exc:
            self.log.setPlainText(f"Fehler: {exc}")
