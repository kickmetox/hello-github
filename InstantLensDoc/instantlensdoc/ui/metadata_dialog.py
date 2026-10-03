"""Dialog: PDF-Metadaten bearbeiten (Titel/Autor/Betreff/Keywords) — 1.5.2."""

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
    """Liest/schreibt DocInfo+XMP; Dirty/Reset; Backup .ildbak; Erfolgs-Toast — 1.5.2."""

    def __init__(self, pdf_path: str | Path, parent=None):
        super().__init__(parent)
        self.pdf_path = Path(pdf_path)
        self.setWindowTitle(tr("meta_title"))
        self.setWindowModified(False)
        self.resize(520, 400)
        self.last_toast = ""
        self.backup_path: Path | None = None
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

        from instantlensdoc.core.app_settings import get_meta_backup_on_save

        self.chk_backup = QCheckBox(tr("meta_backup"))
        self.chk_backup.setChecked(bool(get_meta_backup_on_save()))
        self.chk_backup.setToolTip(tr("meta_backup_tip"))
        layout.addWidget(self.chk_backup)

        self.dirty_label = QLabel("")
        self.dirty_label.setStyleSheet("color:#A65C00; font-weight:600;")
        layout.addWidget(self.dirty_label)

        self.toast_label = QLabel("")
        self.toast_label.setWordWrap(True)
        self.toast_label.setStyleSheet("color:#1B6B2A; font-weight:600;")
        layout.addWidget(self.toast_label)

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

    def _field_short_info(self, meta: PdfMetadata) -> str:
        """Kurzinfo gefüllter Felder für Erfolgs-Toast — 1.5.2."""
        parts: list[str] = []
        mapping = [
            ("title", tr("field_title")),
            ("author", tr("field_author")),
            ("subject", tr("field_subject")),
            ("keywords", tr("field_keywords")),
        ]
        for attr, label in mapping:
            val = utf8_safe(getattr(meta, attr, "") or "").strip()
            if not val:
                continue
            if len(val) > 28:
                val = val[:25] + "…"
            parts.append(f"{label}: {val}")
        if not parts:
            return tr("meta_toast_empty")
        return " · ".join(parts)

    def _save(self):
        from instantlensdoc.core.app_settings import (
            get_autosave_backup_max,
            set_meta_backup_on_save,
        )
        from instantlensdoc.core.documents import backup_ildbak

        meta = self.current_metadata()
        do_backup = bool(self.chk_backup.isChecked())
        set_meta_backup_on_save(do_backup)
        try:
            self.backup_path = None
            if do_backup and self.pdf_path.is_file():
                self.backup_path = backup_ildbak(
                    self.pdf_path, max_backups=get_autosave_backup_max()
                )
            set_metadata(
                self.pdf_path,
                meta,
                delete_empty=bool(self.chk_delete_empty.isChecked()),
            )
            self._original = {
                k: utf8_safe(e.text()) for k, e in self.fields.items()
            }
            self._refresh_dirty()
            short = self._field_short_info(meta)
            bak_note = ""
            if self.backup_path is not None:
                bak_note = f" · Backup {self.backup_path.name}"
            self.last_toast = f"{tr('meta_toast_ok')}: {short}{bak_note}"
            self.toast_label.setText(self.last_toast)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, tr("meta_title"), str(e))
