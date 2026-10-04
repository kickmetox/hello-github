"""Batch-Konvertierung Ordner → PDF / OCR + PDF-Stapel — 2.6.22."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from instantlensdoc.core.app_settings import get_batch_output_dir, get_ocr_lang
from instantlensdoc.core.batch import BatchMode, PdfBatchOptions, run_batch, run_pdf_batch
from instantlensdoc.core.batch import PdfBatchOp
from instantlensdoc.core.ocr import OcrOutputMode


class BatchConvertDialog(QDialog):
    """Bilder/OCR-Batch und PDF-Stapel (Convert/WM/Compress/Encrypt)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Stapelverarbeitung")
        self.setObjectName("batchConvertDialog")
        self.resize(560, 560)
        self._running = False
        self._cancel_requested = False
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.src_edit = QLineEdit()
        self.src_edit.setObjectName("batchSrcEdit")
        src_row = QVBoxLayout()
        pick_src = QPushButton("Quellordner…")
        pick_src.clicked.connect(self._pick_src)
        src_row.addWidget(self.src_edit)
        src_row.addWidget(pick_src)
        form.addRow("Ordner", src_row)

        self.out_edit = QLineEdit()
        self.out_edit.setObjectName("batchOutEdit")
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
        self.mode_combo.setObjectName("batchModeCombo")
        for label, mode in [
            ("Bilder → eine PDF", BatchMode.IMAGES_TO_ONE_PDF),
            ("Bilder → je eine PDF", BatchMode.IMAGES_TO_PDF_EACH),
            ("OCR aller Bilder (durchsuchbares PDF)", BatchMode.OCR_FOLDER),
            ("OCR aller PDFs (Text pro Datei)", BatchMode.PDF_OCR_PAGES),
            ("PDFs → PNG-Seiten (Konvertieren)", BatchMode.PDF_CONVERT_PNG),
            ("PDFs Wasserzeichen", BatchMode.PDF_WATERMARK),
            ("PDFs komprimieren", BatchMode.PDF_COMPRESS),
            ("PDFs verschlüsseln (AES)", BatchMode.PDF_ENCRYPT),
            ("PDF-Pipeline: WM → Komprimieren → Verschlüsseln", "pipeline_wm_comp_enc"),
        ]:
            self.mode_combo.addItem(label, mode)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        form.addRow("Modus", self.mode_combo)
        layout.addLayout(form)

        # PDF-Optionen — 2.6.22
        self.pdf_opts = QWidget()
        self.pdf_opts.setObjectName("batchPdfOpts")
        po = QFormLayout(self.pdf_opts)
        self.wm_text = QLineEdit("CONFIDENTIAL")
        self.wm_text.setObjectName("batchWmText")
        po.addRow("Wasserzeichen", self.wm_text)
        self.wm_opacity = QDoubleSpinBox()
        self.wm_opacity.setRange(0.05, 1.0)
        self.wm_opacity.setSingleStep(0.05)
        self.wm_opacity.setValue(0.25)
        po.addRow("WM-Deckkraft", self.wm_opacity)
        self.comp_q = QSpinBox()
        self.comp_q.setRange(10, 95)
        self.comp_q.setValue(70)
        po.addRow("JPEG-Qualität", self.comp_q)
        self.user_pw = QLineEdit()
        self.user_pw.setObjectName("batchUserPassword")
        self.user_pw.setEchoMode(QLineEdit.Password)
        self.user_pw.setPlaceholderText("Passwort für Verschlüsselung")
        po.addRow("User-Passwort", self.user_pw)
        self.aes256 = QCheckBox("AES-256 bevorzugen")
        self.aes256.setChecked(True)
        self.aes256.setObjectName("batchAes256")
        po.addRow(self.aes256)
        layout.addWidget(self.pdf_opts)

        layout.addWidget(QLabel(f"OCR-Sprache (Einstellungen): {get_ocr_lang()}"))

        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setFormat("%p % — %v/%m")
        self.progress.setTextVisible(True)
        layout.addWidget(self.progress)
        self.progress_label = QLabel("Bereit")
        self.progress_label.setWordWrap(True)
        layout.addWidget(self.progress_label)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        self.log.setObjectName("batchLog")
        layout.addWidget(self.log)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._run_btn = buttons.addButton("Start", QDialogButtonBox.ActionRole)
        self._run_btn.setObjectName("batchStartBtn")
        self._run_btn.clicked.connect(self._run)
        self._cancel_btn = buttons.addButton("Abbrechen Lauf", QDialogButtonBox.ActionRole)
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._request_cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._on_mode_changed()

    def _pdf_options(self) -> PdfBatchOptions:
        return PdfBatchOptions(
            watermark_text=self.wm_text.text().strip() or "CONFIDENTIAL",
            watermark_opacity=float(self.wm_opacity.value()),
            compress_quality=int(self.comp_q.value()),
            user_password=self.user_pw.text(),
            aes256=bool(self.aes256.isChecked()),
        )

    def _on_mode_changed(self):
        mode = self.mode_combo.currentData()
        pdfish = mode in (
            BatchMode.PDF_CONVERT_PNG,
            BatchMode.PDF_WATERMARK,
            BatchMode.PDF_COMPRESS,
            BatchMode.PDF_ENCRYPT,
            "pipeline_wm_comp_enc",
        ) or (
            isinstance(mode, BatchMode)
            and mode.value.startswith("pdf_")
        )
        self.pdf_opts.setVisible(bool(pdfish))

    def _pick_src(self):
        if self._running:
            return
        path = QFileDialog.getExistingDirectory(self, "Quellordner")
        if path:
            self.src_edit.setText(path)
            if not self.out_edit.text().strip():
                self.out_edit.setText(str(Path(path) / "batch-out"))

    def _pick_out(self):
        if self._running:
            return
        path = QFileDialog.getExistingDirectory(self, "Ausgabeordner")
        if path:
            self.out_edit.setText(path)

    def _request_cancel(self):
        if self._running:
            self._cancel_requested = True
            self.progress_label.setText("Abbruch angefordert…")
            self.log.appendPlainText("Abbruch angefordert…")

    def _on_progress(self, msg: str, current: int = 0, total: int = 0) -> None:
        self.log.appendPlainText(msg)
        self.progress_label.setText(msg)
        if total > 0:
            self.progress.setMaximum(total)
            self.progress.setValue(min(max(0, current), total))
            self.progress.setFormat(f"%v/%m — {msg[:48]}")
        else:
            self.progress.setMaximum(0)  # busy
            self.progress.setFormat(msg[:64] or "…")
        QApplication.processEvents()
        if self._cancel_requested:
            raise InterruptedError("Batch abgebrochen")

    def _set_running(self, running: bool) -> None:
        self._running = running
        self._run_btn.setEnabled(not running)
        self._cancel_btn.setEnabled(running)
        self.src_edit.setEnabled(not running)
        self.out_edit.setEnabled(not running)
        self.mode_combo.setEnabled(not running)
        self.pdf_opts.setEnabled(not running)

    def _run(self):
        if self._running:
            return
        src = self.src_edit.text().strip()
        out = self.out_edit.text().strip()
        if not src or not out:
            self.log.appendPlainText("Quell- und Ausgabeordner angeben.")
            return
        if not Path(src).is_dir():
            self.log.appendPlainText(f"Quellordner fehlt: {src}")
            QMessageBox.warning(self, "Batch", f"Quellordner nicht gefunden:\n{src}")
            return
        mode = self.mode_combo.currentData()
        opts = self._pdf_options()
        if mode in (BatchMode.PDF_ENCRYPT, "pipeline_wm_comp_enc") and not opts.user_password.strip():
            QMessageBox.warning(self, "Batch", "User-Passwort für Verschlüsselung angeben.")
            return
        self._cancel_requested = False
        self.progress.setValue(0)
        self.progress.setMaximum(100)
        self.progress_label.setText("Start…")
        label = mode if isinstance(mode, str) else mode.value
        self.log.appendPlainText(f"Start: {label} …")
        ocr_mode = OcrOutputMode.SEARCHABLE_IMAGE
        if mode == BatchMode.PDF_OCR_PAGES:
            ocr_mode = OcrOutputMode.EDITABLE_TEXT
        self._set_running(True)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        result = None
        try:
            if mode == "pipeline_wm_comp_enc":
                result = run_pdf_batch(
                    folder=src,
                    out_dir=out,
                    ops=[
                        PdfBatchOp.WATERMARK,
                        PdfBatchOp.COMPRESS,
                        PdfBatchOp.ENCRYPT,
                    ],
                    options=opts,
                    progress=self._on_progress,
                )
            else:
                result = run_batch(
                    src,
                    out,
                    mode,
                    lang=get_ocr_lang(),
                    ocr_mode=ocr_mode,
                    progress=self._on_progress,
                    options=opts,
                )
        except InterruptedError:
            self.progress_label.setText("Abgebrochen")
            self.progress.setFormat("abgebrochen")
            self.log.appendPlainText("Batch abgebrochen.")
            return
        except Exception as e:
            self.progress.setMaximum(1)
            self.progress.setValue(0)
            self.progress.setFormat("Fehler")
            self.progress_label.setText(f"Fehler: {e}")
            self.log.appendPlainText(f"FEHLER: {e}")
            QMessageBox.warning(self, "Batch", str(e))
            return
        finally:
            QApplication.restoreOverrideCursor()
            self._set_running(False)
            self._cancel_requested = False

        if result is None:
            return
        done = result.ok_count + result.fail_count
        self.progress.setMaximum(max(1, done))
        self.progress.setValue(done)
        self.progress.setFormat("%v/%m fertig")
        self.progress_label.setText(
            f"Fertig: {result.ok_count} OK, {result.fail_count} Fehler"
        )
        self.log.appendPlainText(f"Fertig: {result.ok_count} OK, {result.fail_count} Fehler")
        for item in result.items:
            status = "OK" if item.ok else "FEHLER"
            dest = item.output.name if item.output else item.message
            self.log.appendPlainText(f"  [{status}] {item.source.name} → {dest}")


# Alias für Klarheit in Menüs — 2.6.22
BatchPdfDialog = BatchConvertDialog
