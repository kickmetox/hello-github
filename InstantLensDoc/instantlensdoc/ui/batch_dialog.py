"""Batch-Konvertierung Ordner → PDF / OCR."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from instantlensdoc.core.app_settings import get_batch_output_dir, get_ocr_lang
from instantlensdoc.core.batch import BatchMode, run_batch
from instantlensdoc.core.ocr import OcrOutputMode


class BatchConvertDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch-Konvertierung")
        self.resize(520, 420)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.src_edit = QLineEdit()
        src_row = QVBoxLayout()
        pick_src = QPushButton("Quellordner…")
        pick_src.clicked.connect(self._pick_src)
        src_row.addWidget(self.src_edit)
        src_row.addWidget(pick_src)
        form.addRow("Ordner", src_row)

        self.out_edit = QLineEdit()
        out_default = get_batch_output_dir()
        if out_default:
            self.out_edit.setText(str(out_default))
        pick_out = QPushButton("Ausgabeordner…")
        pick_out.clicked.connect(self._pick_out)
        out_row = QVBoxLayout()
        out_row.addWidget(self.out_edit)
        out_row.addWidget(pick_out)
        form.addRow("Ausgabe", out_row)

        self.mode_combo = QComboBox()
        for label, mode in [
            ("Bilder → eine PDF", BatchMode.IMAGES_TO_ONE_PDF),
            ("Bilder → je eine PDF", BatchMode.IMAGES_TO_PDF_EACH),
            ("OCR aller Bilder (durchsuchbares PDF)", BatchMode.OCR_FOLDER),
            ("OCR aller PDFs (Text pro Datei)", BatchMode.PDF_OCR_PAGES),
        ]:
            self.mode_combo.addItem(label, mode)
        form.addRow("Modus", self.mode_combo)
        layout.addLayout(form)

        layout.addWidget(QLabel(f"OCR-Sprache (Einstellungen): {get_ocr_lang()}"))
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        layout.addWidget(self.log)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        run_btn = buttons.addButton("Start", QDialogButtonBox.ActionRole)
        run_btn.clicked.connect(self._run)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _pick_src(self):
        path = QFileDialog.getExistingDirectory(self, "Quellordner")
        if path:
            self.src_edit.setText(path)
            if not self.out_edit.text().strip():
                self.out_edit.setText(str(Path(path) / "batch-out"))

    def _pick_out(self):
        path = QFileDialog.getExistingDirectory(self, "Ausgabeordner")
        if path:
            self.out_edit.setText(path)

    def _run(self):
        src = self.src_edit.text().strip()
        out = self.out_edit.text().strip()
        if not src or not out:
            self.log.appendPlainText("Quell- und Ausgabeordner angeben.")
            return
        mode = self.mode_combo.currentData()
        self.log.appendPlainText(f"Start: {mode.value} …")
        ocr_mode = OcrOutputMode.SEARCHABLE_IMAGE
        if mode == BatchMode.PDF_OCR_PAGES:
            ocr_mode = OcrOutputMode.EDITABLE_TEXT
        result = run_batch(
            src,
            out,
            mode,
            lang=get_ocr_lang(),
            ocr_mode=ocr_mode,
            progress=lambda m: self.log.appendPlainText(m),
        )
        self.log.appendPlainText(f"Fertig: {result.ok_count} OK, {result.fail_count} Fehler")
        for item in result.items:
            status = "OK" if item.ok else "FEHLER"
            dest = item.output.name if item.output else item.message
            self.log.appendPlainText(f"  [{status}] {item.source.name} → {dest}")
