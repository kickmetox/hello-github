"""Batch-Umbenennen: Dry-Run, Kollision, Undo-TXT, Rückgängig letzte Batch — 1.4.4."""

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

from instantlensdoc.core.app_settings import (
    clear_last_rename_undo_log,
    get_last_rename_undo_log,
    set_last_rename_undo_log,
)
from instantlensdoc.core.batch_rename import (
    DEFAULT_BATCH_RENAME_TEMPLATE,
    RenameUndoEntry,
    RenameUndoLog,
    apply_undo_log,
    count_collisions,
    count_skipped_undo_entries,
    eligible_undo_entries,
    format_dry_run_list,
    invalidate_undo_log,
    is_undo_log_invalidated,
    preview_batch_rename,
    read_undo_log,
    rename_files,
    write_undo_log,
)


class BatchRenameDialog(QDialog):
    """Offene Tabs / Dateiliste umbenennen mit Dry-Run + Undo-TXT."""

    def __init__(self, parent=None, *, paths: list[str] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Batch-Umbenennen (offene Tabs)")
        self.resize(680, 520)
        self._paths = [str(p) for p in (paths or []) if p]
        self.renamed: list[tuple[str, str]] = []  # (old, new) erfolgreich
        self.undo_log_path: str = ""
        self.undone: list[tuple[str, str]] = []  # (new→old) nach Undo

        root = QVBoxLayout(self)
        root.addWidget(
            QLabel(
                "Template-Platzhalter: <code>{stem}</code>, <code>{n}</code>, "
                "<code>{ext}</code>, <code>{name}</code> — Dry-Run / Kollision / "
                "Undo-Log TXT / Rückgängig letzte Batch (nur noch passende Namen) "
                "— 1.4.3"
            )
        )

        form = QFormLayout()
        self.template_edit = QLineEdit(DEFAULT_BATCH_RENAME_TEMPLATE)
        self.template_edit.setPlaceholderText("{stem}_{n}")
        self.template_edit.setToolTip(
            "Dateiname-Template; Standard {stem}_{n} — 1.4.0/1.4.2"
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
        self.btn_undo_last = QPushButton("Rückgängig letzte Batch")
        self.btn_undo_last.setToolTip(
            "Letztes Undo-Log (TXT): Bestätigung mit Anzahl; greift nur Dateien, "
            "die noch dem neuen Namen entsprechen — 1.4.3"
        )
        self.btn_undo_last.clicked.connect(self._undo_last_batch)
        actions.addWidget(self.btn_undo_last)
        actions.addStretch()
        root.addLayout(actions)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Umbenennen")
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._refresh_preview()
        self._refresh_undo_button()

    def _refresh_undo_button(self) -> None:
        last = get_last_rename_undo_log()
        if self.undo_log_path and Path(self.undo_log_path).is_file():
            self.btn_undo_last.setEnabled(True)
            return
        self.btn_undo_last.setEnabled(last is not None and last.is_file())

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
            f"Dry-Run: {ok_n} von {len(items)} würden umbenannt — 1.4.3"
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

    def _resolve_undo_log_path(self) -> Path | None:
        if self.undo_log_path and Path(self.undo_log_path).is_file():
            return Path(self.undo_log_path)
        last = get_last_rename_undo_log()
        if last is not None and last.is_file():
            return last
        return None

    def _invalidate_used_undo_log(self, log_path: Path) -> None:
        """Log nach Undo invalidieren + Settings/Dialog-Pfad leeren — 1.4.4."""
        try:
            invalidate_undo_log(log_path)
        except Exception:
            pass
        try:
            clear_last_rename_undo_log()
        except Exception:
            pass
        if self.undo_log_path and Path(self.undo_log_path) == Path(log_path):
            self.undo_log_path = ""
        self._refresh_undo_button()

    def _undo_last_batch(self) -> None:
        """
        Rückgängig letzte Batch: übersprungene zählen/melden;
        Log danach invalidieren — 1.4.3/1.4.4.
        """
        log_path = self._resolve_undo_log_path()
        if log_path is None:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Undo-Log wählen",
                "",
                "Undo-Log TXT (*.txt);;JSON (*.json);;Alle (*.*)",
            )
            if not path:
                return
            log_path = Path(path)
        if is_undo_log_invalidated(log_path):
            QMessageBox.information(
                self,
                "Rückgängig letzte Batch",
                f"Undo-Log ist bereits ungültig (nach vorherigem Rückgängig):\n"
                f"{log_path}",
            )
            self._invalidate_used_undo_log(log_path)
            return
        try:
            log = read_undo_log(log_path)
        except Exception as e:
            QMessageBox.critical(self, "Rückgängig", f"Undo-Log lesbar?\n{e}")
            return
        if not log.entries:
            QMessageBox.information(
                self, "Rückgängig", "Undo-Log enthält keine Einträge."
            )
            return
        eligible = eligible_undo_entries(log)
        skipped = count_skipped_undo_entries(log)
        if not eligible:
            QMessageBox.information(
                self,
                "Rückgängig letzte Batch",
                f"Keine der {len(log.entries)} Datei(en) entspricht noch dem "
                f"neuen Namen — nichts zurückzunehmen.\n"
                f"Übersprungen: {skipped}\n{log_path}",
            )
            # Auch ohne Undo: Log invalidieren (nicht erneut anbieten) — 1.4.4
            self._invalidate_used_undo_log(log_path)
            return
        msg = (
            f"{len(eligible)} Datei(en) noch unter dem neuen Namen "
            f"wirklich zurücknehmen? (NEW → OLD)\n{log_path}"
        )
        if skipped:
            msg += (
                f"\n\n{skipped} Datei(en) übersprungen "
                "(nicht mehr unter neuem Namen)."
            )
        reply = QMessageBox.question(
            self,
            "Rückgängig letzte Batch",
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        # Nur passende Einträge anwenden
        filtered = RenameUndoLog(
            created=log.created,
            template=log.template,
            entries=list(eligible),
        )
        results = apply_undo_log(
            filtered, also_sidecars=True, only_matching_new_name=True
        )
        errors = [f"{Path(a).name}: {e}" for a, _b, e in results if e]
        self.undone = [(a, b) for a, b, e in results if e is None]
        # Pfade im Dialog aktualisieren (new→old)
        path_map = {a: b for a, b in self.undone}
        self._paths = [path_map.get(p, p) for p in self._paths]
        self._refresh_preview()
        # Log nach Undo invalidieren — 1.4.4
        self._invalidate_used_undo_log(log_path)
        summary = (
            f"{len(self.undone)} Datei(en) zurückbenannt.\n"
            f"Übersprungen: {skipped}"
        )
        if errors:
            QMessageBox.warning(
                self,
                "Rückgängig",
                f"{summary}\n{len(errors)} Fehler:\n" + "\n".join(errors[:8]),
            )
        elif self.undone or skipped:
            QMessageBox.information(
                self,
                "Rückgängig letzte Batch",
                summary + "\nUndo-Log invalidiert.",
            )
        else:
            QMessageBox.information(
                self, "Rückgängig", "Keine Dateien zurückbenannt."
            )

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
            "Undo-Log TXT der alten Namen wird geschrieben — 1.4.2",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        results = rename_files(todo, also_sidecars=True)
        errors = [f"{Path(o).name}: {e}" for o, _n, e in results if e]
        self.renamed = [(o, n) for o, n, e in results if e is None]
        # Undo-Log TXT der alten Namen — 1.4.2
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
                set_last_rename_undo_log(log_path)
                self._refresh_undo_button()
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
                msg += f"\nUndo-Log (TXT):\n{self.undo_log_path}"
            QMessageBox.information(self, "Batch-Umbenennen", msg)
            self.accept()
        elif not errors:
            self.reject()
