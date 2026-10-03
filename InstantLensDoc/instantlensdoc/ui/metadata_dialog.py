"""Dialog: PDF-Metadaten bearbeiten (Titel/Autor/Betreff/Keywords) — 1.5.0."""

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
    """Liest/schreibt DocInfo+XMP via pikepdf; Kernfelder Titel/Autor/Betreff/Keywords."""

    def __init__(self, pdf_path: str | Path, parent=None):
        super().__init__(parent)
        self.pdf_path = Path(pdf_path)
        self.setWindowTitle(tr("meta_title"))
        self.resize(480, 320)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"{self.pdf_path.name}"))
        hint = QLabel(tr("meta_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#555;")
        layout.addWidget(hint)

        meta = get_metadata(self.pdf_path)
        form = QFormLayout()
        self.fields: dict[str, QLineEdit] = {}
        # Kernfelder zuerst — 1.5.0
        for key, label_key in [
            ("title", "field_title"),
            ("author", "field_author"),
            ("subject", "field_subject"),
            ("keywords", "field_keywords"),
            ("creator", "field_creator"),
            ("producer", "field_producer"),
        ]:
            edit = QLineEdit(getattr(meta, key) or "")
            edit.setClearButtonEnabled(True)
            self.fields[key] = edit
            form.addRow(tr(label_key), edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        save_btn = buttons.button(QDialogButtonBox.Save)
        if save_btn is not None:
            save_btn.setText(tr("meta_save"))
            save_btn.setDefault(True)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.fields["title"].setFocus()
        self.fields["title"].selectAll()

    def current_metadata(self) -> PdfMetadata:
        return PdfMetadata(**{k: e.text().strip() for k, e in self.fields.items()})

    def _save(self):
        meta = self.current_metadata()
        try:
            set_metadata(self.pdf_path, meta)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, tr("meta_title"), str(e))
