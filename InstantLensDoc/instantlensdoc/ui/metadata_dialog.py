"""Dialog: PDF-Metadaten bearbeiten."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from ild_pdf.metadata import PdfMetadata, get_metadata, set_metadata
from instantlensdoc.core.i18n import tr


class MetadataDialog(QDialog):
    def __init__(self, pdf_path: str | Path, parent=None):
        super().__init__(parent)
        self.pdf_path = Path(pdf_path)
        self.setWindowTitle(tr("meta_title"))
        self.resize(460, 300)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"{self.pdf_path.name}"))

        meta = get_metadata(self.pdf_path)
        form = QFormLayout()
        self.fields: dict[str, QLineEdit] = {}
        for key, label_key in [
            ("title", "field_title"),
            ("author", "field_author"),
            ("subject", "field_subject"),
            ("keywords", "field_keywords"),
            ("creator", "field_creator"),
            ("producer", "field_producer"),
        ]:
            edit = QLineEdit(getattr(meta, key) or "")
            self.fields[key] = edit
            form.addRow(tr(label_key), edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        meta = PdfMetadata(**{k: e.text().strip() for k, e in self.fields.items()})
        try:
            set_metadata(self.pdf_path, meta)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, tr("meta_title"), str(e))
