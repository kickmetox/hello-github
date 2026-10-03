"""Dialog: PDF-Metadaten bearbeiten (Titel/Autor/Betreff/Keywords) — 1.5.1."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ild_pdf.metadata import PdfMetadata, get_metadata, set_metadata, utf8_safe
from instantlensdoc.core.i18n import tr


class MetadataDialog(QDialog):
    """Liest/schreibt DocInfo+XMP via pikepdf; Dirty-Markierung, Reset, leere Felder löschen — 1.5.1."""

    def __init__(self, pdf_path: str | Path, parent=None):
        super().__init__(parent)
        self.pdf_path = Path(pdf_path)
        self.setWindowTitle(tr("meta_title"))
        self.setWindowModified(False)
        self.resize(520, 380)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"{self.pdf_path.name}"))
        hint = QLabel(tr("meta_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#555;")
        layout.addWidget(hint)

        meta = get_metadata(self.pdf_path)
        self._original = {
            "title": utf8_safe(meta.title or ""),
            "author": utf8_safe(meta.author or ""),
            "subject": utf8_safe(meta.subject or ""),
            "keywords": utf8_safe(meta.keywords or ""),
            "creator": utf8_safe(meta.creator or ""),
            "producer": utf8_safe(meta.producer or ""),
        }
        form = QFormLayout()
        self.fields: dict[str, QLineEdit] = {}
        self._labels: dict[str, QLabel] = {}
        for key, label_key in [
            ("title", "field_title"),
            ("author", "field_author"),
            ("subject", "field_subject"),
            ("keywords", "field_keywords"),
            ("creator", "field_creator"),
            ("producer", "field_producer"),
        ]:
            edit = QLineEdit(self._original[key])
            edit.setClearButtonEnabled(True)
            # UTF-8 / Unicode sicher anzeigen und eingeben — 1.5.1
            edit.setText(utf8_safe(edit.text()))
            edit.textChanged.connect(self._on_field_changed)
            self.fields[key] = edit
            lab = QLabel(tr(label_key))
            self._labels[key] = lab
            form.addRow(lab, edit)
        layout.addLayout(form)

        self.chk_delete_empty = QCheckBox(tr("meta_delete_empty"))
        self.chk_delete_empty.setChecked(True)
        self.chk_delete_empty.setToolTip(tr("meta_delete_empty_tip"))
        layout.addWidget(self.chk_delete_empty)

        self.dirty_label = QLabel("")
        self.dirty_label.setStyleSheet("color:#A65C00; font-weight:600;")
        layout.addWidget(self.dirty_label)

        row = QHBoxLayout()
        self.btn_reset = QPushButton(tr("meta_reset"))
        self.btn_reset.setToolTip(tr("meta_reset_tip"))
        self.btn_reset.setEnabled(False)
        self.btn_reset.clicked.connect(self._reset_fields)
        row.addWidget(self.btn_reset)
        row.addStretch(1)
        layout.addLayout(row)

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
        self._refresh_dirty()

    def current_metadata(self) -> PdfMetadata:
        return PdfMetadata(
            **{k: utf8_safe(e.text().strip()) for k, e in self.fields.items()}
        )

    def is_dirty(self) -> bool:
        cur = {k: utf8_safe(e.text()) for k, e in self.fields.items()}
        return cur != self._original

    def _on_field_changed(self, *_args) -> None:
        self._refresh_dirty()

    def _refresh_dirty(self) -> None:
        dirty = self.is_dirty()
        self.setWindowModified(dirty)
        base = tr("meta_title")
        self.setWindowTitle(f"{base}[*]" if dirty else base)
        self.btn_reset.setEnabled(dirty)
        self.dirty_label.setText(tr("meta_dirty") if dirty else "")
        key_map = {
            "title": "field_title",
            "author": "field_author",
            "subject": "field_subject",
            "keywords": "field_keywords",
            "creator": "field_creator",
            "producer": "field_producer",
        }
        for key, edit in self.fields.items():
            changed = utf8_safe(edit.text()) != self._original.get(key, "")
            lab = self._labels.get(key)
            if lab is not None:
                lab.setText(("* " if changed else "") + tr(key_map[key]))
            if changed:
                edit.setStyleSheet("QLineEdit { border: 1px solid #C47A00; }")
            else:
                edit.setStyleSheet("")

    def _reset_fields(self) -> None:
        """Felder auf geladene Originalwerte zurücksetzen — 1.5.1."""
        for key, edit in self.fields.items():
            edit.blockSignals(True)
            edit.setText(self._original.get(key, ""))
            edit.blockSignals(False)
        self._refresh_dirty()

    def _save(self):
        meta = self.current_metadata()
        try:
            set_metadata(
                self.pdf_path,
                meta,
                delete_empty=bool(self.chk_delete_empty.isChecked()),
            )
            self._original = {
                k: utf8_safe(e.text()) for k, e in self.fields.items()
            }
            self._refresh_dirty()
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, tr("meta_title"), str(e))
