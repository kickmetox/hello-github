"""Dialog: PDF-Anhänge listen, extrahieren und hinzufügen — 1.9.3."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ild_pdf.attachments import (
    AttachmentInfo,
    add_attachment,
    attachment_name_taken,
    extract_all_attachments,
    extract_attachment,
    list_attachments,
    remove_attachment,
    suggest_attachment_name,
)
from instantlensdoc.core.app_settings import dialog_start_dir, remember_recent_dir


def _format_size(size: int) -> str:
    if not size:
        return "—"
    return f"{size:,} B".replace(",", ".")


def _attachment_type(info: AttachmentInfo) -> str:
    """Typ-Spalte: MIME bevorzugt, sonst Dateiendung — 1.9.1."""
    mime = (info.mime_type or "").strip()
    if mime:
        return mime
    name = info.filename or info.name or ""
    suf = Path(name).suffix.lower().lstrip(".")
    return suf.upper() if suf else "—"


class AttachmentsDialog(QDialog):
    """Zeigt eingebettete PDF-Anhänge; Extraktion, Mehrfach-DnD, Duplikat-Warnung."""

    def __init__(self, pdf_path: str | Path, parent=None):
        super().__init__(parent)
        self.pdf_path = Path(pdf_path)
        self.setWindowTitle("PDF-Anhänge")
        self.resize(720, 440)
        self.setAcceptDrops(True)
        self._changed = False
        # Duplikat-Batch: „Für alle anwenden“ — "rename" | "skip" | None — 1.9.3
        self._dup_apply_all: str | None = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"{self.pdf_path.name} — eingebettete Dateianhänge"))
        hint = QLabel(
            "Doppelklick: extrahieren · Mehrfach-Dateien per Drag&Drop · "
            "Duplikat-Namen: Warnung + Umbenennen · „Für alle anwenden“ — 1.9.3"
        )
        hint.setStyleSheet("color:#555;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Name", "Dateiname", "Größe", "Typ"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAcceptDrops(True)
        self.table.viewport().setAcceptDrops(True)
        self.table.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table)

        row = QHBoxLayout()
        self.btn_add = QPushButton("Hinzufügen…")
        self.btn_add.setToolTip(
            "Eine oder mehrere Dateien als PDF-Anhang hinzufügen; "
            "auch Mehrfach-Drag&Drop; bei Namenskonflikt Warnung + Umbenennen "
            "mit „Für alle anwenden“ — 1.9.3"
        )
        self.btn_add.clicked.connect(self._add)
        self.btn_extract = QPushButton("Auswahl extrahieren…")
        self.btn_extract.setToolTip("Doppelklick auf Zeile extrahiert ebenfalls — 1.9.1")
        self.btn_extract.clicked.connect(self._extract_selected)
        self.btn_all = QPushButton("Alle extrahieren…")
        self.btn_all.clicked.connect(self._extract_all)
        self.btn_remove = QPushButton("Auswahl entfernen")
        self.btn_remove.setToolTip("Ausgewählte Anhänge aus dem PDF entfernen — 1.9.0")
        self.btn_remove.clicked.connect(self._remove_selected)
        row.addWidget(self.btn_add)
        row.addWidget(self.btn_extract)
        row.addWidget(self.btn_all)
        row.addWidget(self.btn_remove)
        row.addStretch(1)
        layout.addLayout(row)

        self._items: list[AttachmentInfo] = []
        self._load()

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    @property
    def changed(self) -> bool:
        return self._changed

    def _load(self):
        try:
            self._items = list_attachments(self.pdf_path)
        except Exception as e:
            QMessageBox.warning(self, "Anhänge", str(e))
            self._items = []
        self.table.setRowCount(0)
        has = bool(self._items)
        self.btn_extract.setEnabled(has)
        self.btn_all.setEnabled(has)
        self.btn_remove.setEnabled(has)
        if not self._items:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("(keine Anhänge)"))
            self.table.setItem(0, 2, QTableWidgetItem("—"))
            self.table.setItem(0, 3, QTableWidgetItem("—"))
            return
        self.table.setRowCount(len(self._items))
        for i, info in enumerate(self._items):
            self.table.setItem(i, 0, QTableWidgetItem(info.name))
            self.table.setItem(i, 1, QTableWidgetItem(info.filename or info.name))
            self.table.setItem(i, 2, QTableWidgetItem(_format_size(info.size)))
            self.table.setItem(i, 3, QTableWidgetItem(_attachment_type(info)))
        self.table.selectRow(0)

    def _selected_names(self) -> list[str]:
        rows = {idx.row() for idx in self.table.selectedIndexes()}
        names: list[str] = []
        for r in sorted(rows):
            if 0 <= r < len(self._items):
                names.append(self._items[r].name)
        return names

    def _pick_dir(self, title: str) -> Path | None:
        start = dialog_start_dir(self.pdf_path.parent)
        path = QFileDialog.getExistingDirectory(self, title, start)
        if not path:
            return None
        remember_recent_dir(path)
        return Path(path)

    def _on_double_click(self, _item) -> None:
        """Doppelklick → Auswahl extrahieren — 1.9.1."""
        if not self._items:
            return
        self._extract_selected()

    def _resolve_attach_name(
        self, preferred: str, *, batch: bool, stats: dict[str, int]
    ) -> str | None:
        """
        Bei Duplikat: Warnung + Umbenennen / Überspringen / Abbrechen;
        optional „Für alle anwenden“ — 1.9.3.
        Rückgabe: gewählter Name, oder None = diese Datei überspringen.
        Wirft ``_AbortBatch`` bei Abbruch der Mehrfach-Operation.
        """
        name = Path(preferred).name.strip() or preferred.strip() or "anhang"
        if not attachment_name_taken(self.pdf_path, name):
            return name

        # „Für alle anwenden“ aus vorherigem Dialog — 1.9.3
        if self._dup_apply_all == "skip":
            stats["skipped"] = stats.get("skipped", 0) + 1
            return None
        if self._dup_apply_all == "rename":
            suggested = suggest_attachment_name(self.pdf_path, name)
            stats["renamed"] = stats.get("renamed", 0) + 1
            return suggested

        suggested = suggest_attachment_name(self.pdf_path, name)
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Doppelter Anhangsname")
        msg.setText(
            f"Ein Anhang „{name}“ existiert bereits.\n\n"
            "Umbenennen, diese Datei überspringen oder Abbruch?"
        )
        msg.setInformativeText(f"Vorschlag: {suggested}")
        apply_cb = QCheckBox("Für alle anwenden")
        apply_cb.setToolTip(
            "Gewählte Aktion (Umbenennen oder Überspringen) für alle "
            "weiteren Namenskonflikte in diesem Durchlauf — 1.9.3"
        )
        if batch:
            msg.setCheckBox(apply_cb)
        btn_rename = msg.addButton("Umbenennen…", QMessageBox.AcceptRole)
        btn_skip = msg.addButton("Überspringen", QMessageBox.DestructiveRole)
        btn_abort = msg.addButton("Abbrechen", QMessageBox.RejectRole)
        msg.setDefaultButton(btn_rename)
        msg.exec()
        clicked = msg.clickedButton()
        apply_all = bool(batch and apply_cb.isChecked())
        if clicked is btn_abort:
            stats["aborted"] = stats.get("aborted", 0) + 1
            raise _AbortBatch()
        if clicked is btn_skip:
            if apply_all:
                self._dup_apply_all = "skip"
            stats["skipped"] = stats.get("skipped", 0) + 1
            return None
        # Umbenennen
        if apply_all:
            # ohne weiteren Dialog: Vorschläge für alle weiteren Konflikte
            self._dup_apply_all = "rename"
            stats["renamed"] = stats.get("renamed", 0) + 1
            return suggested
        new_name, ok = QInputDialog.getText(
            self,
            "Anhang umbenennen",
            "Neuer Name:",
            text=suggested,
        )
        if not ok:
            if batch:
                stats["skipped"] = stats.get("skipped", 0) + 1
                return None
            stats["aborted"] = stats.get("aborted", 0) + 1
            raise _AbortBatch()
        new_name = (new_name or "").strip()
        if not new_name:
            stats["skipped"] = stats.get("skipped", 0) + 1
            return None
        if attachment_name_taken(self.pdf_path, new_name):
            # zweiter Vorschlag erzwingen
            new_name = suggest_attachment_name(self.pdf_path, new_name)
            QMessageBox.information(
                self,
                "Anhänge",
                f"Name weiterhin belegt — verwende „{new_name}“.",
            )
        stats["renamed"] = stats.get("renamed", 0) + 1
        return new_name

    @staticmethod
    def _format_add_status(stats: dict[str, int], *, last_info=None) -> str:
        """Statuszählung am Ende — 1.9.3."""
        added = int(stats.get("added", 0))
        renamed = int(stats.get("renamed", 0))
        skipped = int(stats.get("skipped", 0))
        aborted = int(stats.get("aborted", 0))
        errors = int(stats.get("errors", 0))
        parts: list[str] = []
        if added == 1 and last_info and renamed == 0 and skipped == 0 and not aborted:
            return f"Hinzugefügt: {last_info.name} ({last_info.size} B)"
        if added:
            parts.append(f"{added} hinzugefügt")
        if renamed:
            parts.append(f"{renamed} umbenannt")
        if skipped:
            parts.append(f"{skipped} übersprungen")
        if errors:
            parts.append(f"{errors} Fehler")
        if aborted:
            parts.append("abgebrochen")
        if not parts:
            return "Keine Dateien hinzugefügt."
        return " · ".join(parts)

    def _add_paths(self, paths: list[str | Path]) -> int:
        """Mehrere Dateien hinzufügen; Duplikat-Namen mit Warnung — 1.9.3."""
        files = [Path(p) for p in paths if p and Path(p).is_file()]
        if not files:
            return 0
        self._dup_apply_all = None
        stats: dict[str, int] = {
            "added": 0,
            "renamed": 0,
            "skipped": 0,
            "aborted": 0,
            "errors": 0,
        }
        last_info = None
        batch = len(files) > 1
        try:
            for p in files:
                try:
                    resolved = self._resolve_attach_name(p.name, batch=batch, stats=stats)
                except _AbortBatch:
                    break
                if resolved is None:
                    continue
                try:
                    last_info = add_attachment(self.pdf_path, p, name=resolved)
                    stats["added"] = stats.get("added", 0) + 1
                except Exception as e:
                    stats["errors"] = stats.get("errors", 0) + 1
                    QMessageBox.warning(self, "Anhang hinzufügen", f"{p.name}: {e}")
                    break
        except _AbortBatch:
            stats["aborted"] = max(1, stats.get("aborted", 0))
        finally:
            self._dup_apply_all = None

        added = int(stats.get("added", 0))
        if added:
            self._changed = True
            remember_recent_dir(str(files[0].parent))
            self._load()
        msg = self._format_add_status(stats, last_info=last_info)
        if added or stats.get("skipped") or stats.get("aborted") or stats.get("errors"):
            QMessageBox.information(self, "Anhänge", msg)
        return added

    def _add(self):
        start = dialog_start_dir(self.pdf_path.parent)
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Dateien als Anhang hinzufügen (Mehrfachauswahl)",
            start,
            "Alle Dateien (*.*)",
        )
        if not paths:
            return
        self._add_paths(paths)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls() if event.mimeData() else []
        paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
        files = [p for p in paths if p and Path(p).is_file()]
        if files:
            event.acceptProposedAction()
            self._add_paths(files)
        else:
            super().dropEvent(event)

    def _extract_selected(self):
        names = self._selected_names()
        if not names:
            QMessageBox.information(self, "Anhänge", "Bitte Zeile(n) auswählen.")
            return
        out_dir = self._pick_dir("Zielordner für Anhänge")
        if out_dir is None:
            return
        written: list[Path] = []
        try:
            for name in names:
                written.append(extract_attachment(self.pdf_path, name, out_dir=out_dir))
        except Exception as e:
            QMessageBox.warning(self, "Extrahieren", str(e))
            return
        QMessageBox.information(
            self,
            "Anhänge",
            f"{len(written)} Datei(en) nach:\n{out_dir}",
        )

    def _extract_all(self):
        if not self._items:
            return
        out_dir = self._pick_dir("Zielordner für alle Anhänge")
        if out_dir is None:
            return
        try:
            written = extract_all_attachments(self.pdf_path, out_dir=out_dir)
        except Exception as e:
            QMessageBox.warning(self, "Extrahieren", str(e))
            return
        QMessageBox.information(
            self,
            "Anhänge",
            f"{len(written)} Datei(en) nach:\n{out_dir}",
        )

    def _remove_selected(self):
        names = self._selected_names()
        if not names:
            QMessageBox.information(self, "Anhänge", "Bitte Zeile(n) auswählen.")
            return
        reply = QMessageBox.question(
            self,
            "Anhänge entfernen",
            f"{len(names)} Anhang/Anhänge wirklich aus dem PDF entfernen?",
        )
        if reply != QMessageBox.Yes:
            return
        removed = 0
        try:
            for name in names:
                if remove_attachment(self.pdf_path, name):
                    removed += 1
        except Exception as e:
            QMessageBox.warning(self, "Entfernen", str(e))
            return
        if removed:
            self._changed = True
        self._load()
        QMessageBox.information(self, "Anhänge", f"{removed} Anhang/Anhänge entfernt.")


class _AbortBatch(Exception):
    """Mehrfach-Hinzufügen abbrechen — 1.9.2."""
