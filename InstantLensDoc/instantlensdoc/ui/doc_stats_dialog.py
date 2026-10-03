"""Panel/Dialog: Dokument-Statistik (Seiten, Wörter, Ann., Dateigröße) — 1.6.0."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ild_pdf.doc_stats import DocumentStats, collect_document_stats


class DocStatsDialog(QDialog):
    """Nicht-modales Statistik-Panel für das aktuelle PDF."""

    def __init__(
        self,
        parent=None,
        *,
        pdf_path: str | Path | None = None,
        annotation_count: int | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Dokument-Statistik")
        self.setWindowModality(Qt.NonModal)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.resize(380, 260)
        self._pdf_path = Path(pdf_path) if pdf_path else None
        self._ann_count = annotation_count

        layout = QVBoxLayout(self)
        self.hint = QLabel("Seiten · Wörter (Text-PDF) · Annotationen · Dateigröße")
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet("color:#555;")
        layout.addWidget(self.hint)

        form = QFormLayout()
        self.lbl_file = QLabel("—")
        self.lbl_pages = QLabel("—")
        self.lbl_words = QLabel("—")
        self.lbl_ann = QLabel("—")
        self.lbl_size = QLabel("—")
        for lab in (
            self.lbl_file,
            self.lbl_pages,
            self.lbl_words,
            self.lbl_ann,
            self.lbl_size,
        ):
            lab.setTextInteractionFlags(Qt.TextSelectableByMouse)
        form.addRow("Datei", self.lbl_file)
        form.addRow("Seiten", self.lbl_pages)
        form.addRow("Wörter", self.lbl_words)
        form.addRow("Annotationen", self.lbl_ann)
        form.addRow("Dateigröße", self.lbl_size)
        layout.addLayout(form)

        self.btn_refresh = QPushButton("Aktualisieren")
        self.btn_refresh.clicked.connect(self.refresh)
        layout.addWidget(self.btn_refresh)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)

        if self._pdf_path:
            self.refresh()

    def set_document(
        self,
        pdf_path: str | Path | None,
        *,
        annotation_count: int | None = None,
    ) -> None:
        self._pdf_path = Path(pdf_path) if pdf_path else None
        self._ann_count = annotation_count
        self.refresh()

    def refresh(self) -> DocumentStats | None:
        if not self._pdf_path or not self._pdf_path.is_file():
            self.lbl_file.setText("—")
            self.lbl_pages.setText("—")
            self.lbl_words.setText("— (kein PDF)")
            self.lbl_ann.setText("—")
            self.lbl_size.setText("—")
            return None
        try:
            stats = collect_document_stats(
                self._pdf_path,
                annotation_count=self._ann_count,
            )
        except Exception as e:
            self.lbl_file.setText(self._pdf_path.name)
            self.lbl_words.setText(f"Fehler: {e}")
            return None
        self.lbl_file.setText(self._pdf_path.name)
        self.lbl_file.setToolTip(str(self._pdf_path))
        self.lbl_pages.setText(str(stats.pages))
        if stats.has_text:
            self.lbl_words.setText(f"{stats.words}")
        else:
            self.lbl_words.setText(f"{stats.words} (wenig/kein Text)")
        self.lbl_ann.setText(str(stats.annotations))
        self.lbl_size.setText(f"{stats.format_size()} ({stats.file_size} B)")
        return stats
