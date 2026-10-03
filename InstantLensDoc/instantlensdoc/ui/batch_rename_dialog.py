"""Batch-Umbenennen: offene Tabs mit Template {stem}_{n} und Live-Vorschau — 1.4.0."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from instantlensdoc.core.batch_rename import (
    DEFAULT_BATCH_RENAME_TEMPLATE,
    preview_batch_rename,
    rename_files,
)


class BatchRenameDialog(QDialog):
    """Offene Tabs / Dateiliste umbenennen mit Template-Vorschau."""

    def __init__(self, parent=None, *, paths: list[str] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Batch-Umbenennen (offene Tabs)")
        self.resize(640, 480)
        self._paths = [str(p) for p in (paths or []) if p]
        self.renamed: list[tuple[str, str]] = []  # (old, new) erfolgreich

        root = QVBoxLayout(self)
        root.addWidget(
            QLabel(
                "Template-Platzhalter: <code>{stem}</code>, <code>{n}</code>, "
                "<code>{ext}</code>, <code>{name}</code> — 1.4.0"
            )
        )

        form = QFormLayout()
        self.template_edit = QLineEdit(DEFAULT_BATCH_RENAME_TEMPLATE)
        self.template_edit.setPlaceholderText("{stem}_{n}")
        self.template_edit.setToolTip(
            "Dateiname-Template; Standard {stem}_{n} — 1.4.0"
        )
        self.template_edit.textChanged.connect(self._refresh_preview)
        form.addRow("Template", self.template_edit)

        self.start_spin = QSpinBox()
        self.start_spin.setRange(0, 9999)
        self.start_spin.setValue(1)
        self.start_spin.valueChanged.connect(self._refresh_preview)
        form.addRow("Start-Index {n}", self.start_spin)
        root.addLayout(form)

        quick = QHBoxLayout()
        for label, tpl in (
            ("{stem}_{n}", "{stem}_{n}"),
            ("{stem}-{n}", "{stem}-{n}"),
            ("doc_{n}", "doc_{n}"),
        ):
            btn = QPushButton(label)
            btn.clicked.connect(lambda _=False, t=tpl: self.template_edit.setText(t))
            quick.addWidget(btn)
        quick.addStretch()
        root.addLayout(quick)

        self.preview = QListWidget()
        self.preview.setToolTip("Vorschau alt → neu (übersprungene grau) — 1.4.0")
        root.addWidget(self.preview, 1)

        self.status = QLabel("")
        root.addWidget(self.status)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Umbenennen")
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._refresh_preview()

    def _refresh_preview(self) -> None:
        self.preview.clear()
        items = preview_batch_rename(
            self._paths,
            self.template_edit.text(),
            start_index=self.start_spin.value(),
        )
        ok_n = 0
        for it in items:
            text = f"{Path(it.old_path).name}  →  {it.new_name}"
            if it.skipped:
                text += f"  ({it.reason})"
            else:
                ok_n += 1
            row = QListWidgetItem(text)
            if it.skipped:
                row.setForeground(Qt.gray)
            row.setData(Qt.UserRole, it)
            self.preview.addItem(row)
        self.status.setText(
            f"{ok_n} von {len(items)} werden umbenannt — Vorschau live — 1.4.0"
        )

    def _apply(self) -> None:
        items = preview_batch_rename(
            self._paths,
            self.template_edit.text(),
            start_index=self.start_spin.value(),
        )
        todo = [it for it in items if not it.skipped]
        if not todo:
            QMessageBox.information(
                self, "Batch-Umbenennen", "Keine Dateien zum Umbenennen."
            )
            return
        reply = QMessageBox.question(
            self,
            "Batch-Umbenennen",
            f"{len(todo)} Datei(en) wirklich umbenennen?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        results = rename_files(todo, also_sidecars=True)
        errors = [f"{Path(o).name}: {e}" for o, _n, e in results if e]
        self.renamed = [(o, n) for o, n, e in results if e is None]
        if errors:
            QMessageBox.warning(
                self,
                "Batch-Umbenennen",
                f"{len(self.renamed)} ok, {len(errors)} Fehler:\n" + "\n".join(errors[:8]),
            )
        if self.renamed:
            self.accept()
        elif not errors:
            self.reject()
