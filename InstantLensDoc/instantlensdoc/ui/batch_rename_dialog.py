"""Batch-Umbenennen: Dry-Run, Kollisionswarnung, Undo-Log — 1.4.1."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
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
    RenameUndoEntry,
    count_collisions,
    format_dry_run_list,
    preview_batch_rename,
    rename_files,
    write_undo_log,
)


class BatchRenameDialog(QDialog):
    """Offene Tabs / Dateiliste umbenennen mit Dry-Run + Undo-Log."""

    def __init__(self, parent=None, *, paths: list[str] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Batch-Umbenennen (offene Tabs)")
        self.resize(680, 520)
        self._paths = [str(p) for p in (paths or []) if p]
        self.renamed: list[tuple[str, str]] = []  # (old, new) erfolgreich
        self.undo_log_path: str = ""

        root = QVBoxLayout(self)
        root.addWidget(
            QLabel(
                "Template-Platzhalter: <code>{stem}</code>, <code>{n}</code>, "
                "<code>{ext}</code>, <code>{name}</code> — Dry-Run / Kollision / "
                "Undo-Log — 1.4.1"
            )
        )

        form = QFormLayout()
        self.template_edit = QLineEdit(DEFAULT_BATCH_RENAME_TEMPLATE)
        self.template_edit.setPlaceholderText("{stem}_{n}")
        self.template_edit.setToolTip(
            "Dateiname-Template; Standard {stem}_{n} — 1.4.0/1.4.1"
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
        self.preview.setToolTip(
            "Dry-Run-Liste alt → neu; Kollisionen rot hervorgehoben — 1.4.1"
        )
        root.addWidget(self.preview, 1)

        self.status = QLabel("")
        self.lbl_collision = QLabel("")
        self.lbl_collision.setStyleSheet("color: #b33;")
        root.addWidget(self.status)
        root.addWidget(self.lbl_collision)

        actions = QHBoxLayout()
        self.btn_dry_run = QPushButton("Dry-Run speichern…")
        self.btn_dry_run.setToolTip(
            "Dry-Run-Liste als Textdatei speichern (ohne Umbenennen) — 1.4.1"
        )
        self.btn_dry_run.clicked.connect(self._save_dry_run)
        actions.addWidget(self.btn_dry_run)
        actions.addStretch()
        root.addLayout(actions)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Umbenennen")
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._refresh_preview()

    def _current_items(self):
        return preview_batch_rename(
            self._paths,
            self.template_edit.text(),
            start_index=self.start_spin.value(),
        )

    def _refresh_preview(self) -> None:
        self.preview.clear()
        items = self._current_items()
        ok_n = 0
        col_n = 0
        for it in items:
            text = f"{Path(it.old_path).name}  →  {it.new_name}"
            if it.skipped:
                text += f"  ({it.reason})"
            else:
                ok_n += 1
            row = QListWidgetItem(text)
            if it.collision:
                row.setForeground(QColor("#c0392b"))
                col_n += 1
            elif it.skipped:
                row.setForeground(Qt.gray)
            row.setData(Qt.UserRole, it)
            self.preview.addItem(row)
        self.status.setText(
            f"Dry-Run: {ok_n} von {len(items)} würden umbenannt — 1.4.1"
        )
        if col_n:
            self.lbl_collision.setText(
                f"⚠ Kollisionswarnung: {col_n} Zielkonflikt(e) "
                f"(Liste/existierende Datei) — werden übersprungen — 1.4.1"
            )
        else:
            self.lbl_collision.setText("")

    def _save_dry_run(self) -> None:
        items = self._current_items()
        text = format_dry_run_list(items)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Dry-Run-Liste speichern",
            "ild-rename-dry-run.txt",
            "Text (*.txt)",
        )
        if not path:
            return
        try:
            Path(path).write_text(text, encoding="utf-8")
            QMessageBox.information(
                self, "Dry-Run", f"Dry-Run-Liste gespeichert:\n{path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Dry-Run", str(e))

    def _apply(self) -> None:
        items = self._current_items()
        todo = [it for it in items if not it.skipped]
        col_n = count_collisions(items)
        if col_n:
            reply = QMessageBox.warning(
                self,
                "Kollisionswarnung",
                f"{col_n} Kollision(en) erkannt — diese werden übersprungen.\n"
                f"{len(todo)} Datei(en) trotzdem umbenennen?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        if not todo:
            QMessageBox.information(
                self, "Batch-Umbenennen", "Keine Dateien zum Umbenennen."
            )
            return
        reply = QMessageBox.question(
            self,
            "Batch-Umbenennen",
            f"{len(todo)} Datei(en) wirklich umbenennen?\n"
            "Undo-Log der alten Namen wird geschrieben — 1.4.1",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        results = rename_files(todo, also_sidecars=True)
        errors = [f"{Path(o).name}: {e}" for o, _n, e in results if e]
        self.renamed = [(o, n) for o, n, e in results if e is None]
        # Undo-Log der alten Namen — 1.4.1
        if self.renamed:
            entries = [
                RenameUndoEntry(
                    old_path=o,
                    new_path=n,
                    old_name=Path(o).name,
                    new_name=Path(n).name,
                )
                for o, n in self.renamed
            ]
            try:
                log_path = write_undo_log(
                    entries, template=self.template_edit.text().strip()
                )
                self.undo_log_path = str(log_path)
            except Exception as e:
                self.undo_log_path = ""
                QMessageBox.warning(
                    self,
                    "Undo-Log",
                    f"Umbenennung ok, aber Undo-Log fehlgeschlagen:\n{e}",
                )
        if errors:
            QMessageBox.warning(
                self,
                "Batch-Umbenennen",
                f"{len(self.renamed)} ok, {len(errors)} Fehler:\n"
                + "\n".join(errors[:8]),
            )
        if self.renamed:
            msg = f"{len(self.renamed)} Datei(en) umbenannt."
            if self.undo_log_path:
                msg += f"\nUndo-Log:\n{self.undo_log_path}"
            QMessageBox.information(self, "Batch-Umbenennen", msg)
            self.accept()
        elif not errors:
            self.reject()
