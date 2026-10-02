"""Batch-Konvertierung Ordner → PDF / OCR."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
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
        self.resize(520, 460)
        self._running = False
        self._cancel_requested = False
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
        layout.addWidget(self.log)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._run_btn = buttons.addButton("Start", QDialogButtonBox.ActionRole)
        self._run_btn.clicked.connect(self._run)
        self._cancel_btn = buttons.addButton("Abbrechen Lauf", QDialogButtonBox.ActionRole)
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._request_cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

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
        self._cancel_requested = False
        self.progress.setValue(0)
        self.progress.setMaximum(100)
        self.progress_label.setText("Start…")
        self.log.appendPlainText(f"Start: {mode.value} …")
        ocr_mode = OcrOutputMode.SEARCHABLE_IMAGE
        if mode == BatchMode.PDF_OCR_PAGES:
            ocr_mode = OcrOutputMode.EDITABLE_TEXT
        self._set_running(True)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        result = None
        try:
            result = run_batch(
                src,
                out,
                mode,
                lang=get_ocr_lang(),
                ocr_mode=ocr_mode,
                progress=self._on_progress,
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
