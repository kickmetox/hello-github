"""Dialog: PDF-Anhänge listen, extrahieren und hinzufügen — 1.9.5."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QGuiApplication, QMouseEvent
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


def format_attach_add_status(stats: dict[str, int]) -> str:
    """
    Footer-Statuszählung — 1.9.5.
    Format: ``hinzugefügt X, umbenannt Y, übersprungen Z`` (kopierbar).
    Leerer String wenn alle Zähler 0 (leerer Footer).
    """
    added = int(stats.get("added", 0) or 0)
    renamed = int(stats.get("renamed", 0) or 0)
    skipped = int(stats.get("skipped", 0) or 0)
    errors = int(stats.get("errors", 0) or 0)
    aborted = int(stats.get("aborted", 0) or 0)
    if added == 0 and renamed == 0 and skipped == 0 and errors == 0 and not aborted:
        return ""
    base = f"hinzugefügt {added}, umbenannt {renamed}, übersprungen {skipped}"
    extras: list[str] = []
    if errors:
        extras.append(f"Fehler {errors}")
    if aborted:
        extras.append("abgebrochen")
    if extras:
        return f"{base}, {', '.join(extras)}"
    return base


class _ClickableStatusFooter(QLabel):
    """Klickbarer Footer: Filter umbenannt/übersprungen (Toggle) — 1.9.5."""

    def __init__(self, on_click, parent=None):
        super().__init__(parent)
        self._on_click = on_click

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event is not None and event.button() == Qt.LeftButton:
            if callable(self._on_click):
                self._on_click()
            event.accept()
            return
        super().mousePressEvent(event)


class AttachmentsDialog(QDialog):
    """Zeigt eingebettete PDF-Anhänge; Extraktion, Mehrfach-DnD, Duplikat-Warnung."""

    def __init__(self, pdf_path: str | Path, parent=None):
        super().__init__(parent)
        self.pdf_path = Path(pdf_path)
        self.setWindowTitle("PDF-Anhänge")
        self.resize(720, 460)
        self.setAcceptDrops(True)
        self._changed = False
        # Duplikat-Batch: „Für alle anwenden“ — "rename" | "skip" | None — 1.9.3
        self._dup_apply_all: str | None = None
        # Letzter Add-Lauf für Footer-Filter — 1.9.5
        self._last_renamed_names: list[str] = []
        self._last_skipped_names: list[str] = []
        self._filter_renamed_skipped = False
        self._last_stats: dict[str, int] = {
            "added": 0,
            "renamed": 0,
            "skipped": 0,
            "aborted": 0,
            "errors": 0,
        }
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"{self.pdf_path.name} — eingebettete Dateianhänge"))
        hint = QLabel(
            "Doppelklick: extrahieren · Mehrfach-Dateien per Drag&Drop · "
            "Duplikat-Namen: Warnung + Umbenennen · Footer-Klick filtert "
            "umbenannt/übersprungen (Toggle) — 1.9.5"
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
            "mit „Für alle anwenden“ — Footer-Filter umbenannt/übersprungen — 1.9.5"
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

        # Footer Statuszählung (kopierbar, klickbar Filter) — 1.9.5
        foot = QHBoxLayout()
        self.status_footer = _ClickableStatusFooter(self._toggle_status_filter)
        self.status_footer.setObjectName("attachAddStatusFooter")
        self.status_footer.setTextInteractionFlags(Qt.NoTextInteraction)
        self.status_footer.setCursor(Qt.PointingHandCursor)
        self.status_footer.setToolTip(
            "Klick: Liste auf umbenannt/übersprungen filtern (Toggle). "
            "Leer wenn alle Zähler 0 — 1.9.5"
        )
        self.status_footer.setStyleSheet("color:#333;padding:2px 0;")
        foot.addWidget(self.status_footer, 1)
        self.filter_badge = QLabel("")
        self.filter_badge.setObjectName("attachAddFilterBadge")
        self.filter_badge.setStyleSheet(
            "color:#0d47a1;font-weight:600;padding:2px 6px;"
        )
        self.filter_badge.setVisible(False)
        self.filter_badge.setToolTip("Filter aktiv: umbenannt/übersprungen — 1.9.5")
        foot.addWidget(self.filter_badge)
        self.btn_copy_status = QPushButton("Kopieren")
        self.btn_copy_status.setObjectName("attachAddStatusCopy")
        self.btn_copy_status.setToolTip("Statuszählung in die Zwischenablage kopieren — 1.9.5")
        self.btn_copy_status.clicked.connect(self._copy_status_footer)
        foot.addWidget(self.btn_copy_status)
        layout.addLayout(foot)

        self._items: list[AttachmentInfo] = []
        self._load()
        # Initial leerer Footer (Zähler 0) — 1.9.5
        self._set_status_footer({})

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    @property
    def changed(self) -> bool:
        return self._changed

    def _copy_status_footer(self) -> None:
        text = (self.status_footer.text() or "").strip()
        clip = QGuiApplication.clipboard()
        if clip is not None and text:
            clip.setText(text)

    def _set_status_footer(self, stats: dict[str, int], *, last_info=None) -> str:
        """Footer setzen; leer wenn 0; Rückgabe gleicher Text — 1.9.5."""
        self._last_stats = {
            "added": int(stats.get("added", 0) or 0),
            "renamed": int(stats.get("renamed", 0) or 0),
            "skipped": int(stats.get("skipped", 0) or 0),
            "aborted": int(stats.get("aborted", 0) or 0),
            "errors": int(stats.get("errors", 0) or 0),
        }
        msg = self._format_add_status(self._last_stats, last_info=last_info)
        self.status_footer.setText(msg)
        has = bool(msg.strip())
        self.status_footer.setVisible(has)
        self.btn_copy_status.setVisible(has)
        if not has:
            self._filter_renamed_skipped = False
        self._update_filter_badge()
        return msg

    def _toggle_status_filter(self) -> None:
        """Footer-Klick: Liste auf umbenannt/übersprungen umschalten — 1.9.5."""
        renamed_n = int(self._last_stats.get("renamed", 0) or 0)
        skipped_n = int(self._last_stats.get("skipped", 0) or 0)
        if not self._filter_renamed_skipped and renamed_n == 0 and skipped_n == 0:
            return
        if not self._filter_renamed_skipped and not (
            self._last_renamed_names or self._last_skipped_names
        ):
            return
        self._filter_renamed_skipped = not self._filter_renamed_skipped
        self._apply_table_filter()
        self._update_filter_badge()

    def _update_filter_badge(self) -> None:
        if self._filter_renamed_skipped:
            n = len(self._last_renamed_names) + len(self._last_skipped_names)
            self.filter_badge.setText(f"Filter: umbenannt/übersprungen ({n})")
            self.filter_badge.setVisible(True)
            self.status_footer.setStyleSheet(
                "color:#0d47a1;font-weight:bold;text-decoration:underline;padding:2px 0;"
            )
            self.status_footer.setToolTip(
                "Filter aktiv: nur umbenannt/übersprungen. Klick hebt auf — 1.9.5"
            )
        else:
            self.filter_badge.setText("")
            self.filter_badge.setVisible(False)
            has = bool((self.status_footer.text() or "").strip())
            self.status_footer.setStyleSheet(
                "color:#333;text-decoration:underline;padding:2px 0;"
                if has
                else "color:#333;padding:2px 0;"
            )
            self.status_footer.setToolTip(
                "Klick: Liste auf umbenannt/übersprungen filtern (Toggle). "
                "Leer wenn alle Zähler 0 — 1.9.5"
            )

    def _apply_table_filter(self) -> None:
        """Vollständige Anhänge-Liste oder nur umbenannt/übersprungen — 1.9.5."""
        if not self._filter_renamed_skipped:
            self._populate_table(self._items)
            return
        renamed_set = set(self._last_renamed_names)
        by_name = {info.name: info for info in self._items}
        rows: list[tuple[str, str, str, str]] = []
        for name in self._last_renamed_names:
            info = by_name.get(name)
            if info is not None:
                rows.append(
                    (
                        info.name,
                        info.filename or info.name,
                        _format_size(info.size),
                        _attachment_type(info),
                    )
                )
            else:
                rows.append((name, name, "—", "umbenannt"))
        for name in self._last_skipped_names:
            if name in renamed_set:
                continue
            rows.append((name, name, "—", "übersprungen"))
        self.table.setRowCount(0)
        if not rows:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("(keine umbenannt/übersprungen)"))
            self.table.setItem(0, 2, QTableWidgetItem("—"))
            self.table.setItem(0, 3, QTableWidgetItem("—"))
            return
        self.table.setRowCount(len(rows))
        for i, (n, fn, sz, typ) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(n))
            self.table.setItem(i, 1, QTableWidgetItem(fn))
            self.table.setItem(i, 2, QTableWidgetItem(sz))
            self.table.setItem(i, 3, QTableWidgetItem(typ))
        self.table.selectRow(0)

    def _populate_table(self, items: list[AttachmentInfo]) -> None:
        self.table.setRowCount(0)
        has = bool(items)
        self.btn_extract.setEnabled(has)
        self.btn_all.setEnabled(has)
        self.btn_remove.setEnabled(has)
        if not items:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("(keine Anhänge)"))
            self.table.setItem(0, 2, QTableWidgetItem("—"))
            self.table.setItem(0, 3, QTableWidgetItem("—"))
            return
        self.table.setRowCount(len(items))
        for i, info in enumerate(items):
            self.table.setItem(i, 0, QTableWidgetItem(info.name))
            self.table.setItem(i, 1, QTableWidgetItem(info.filename or info.name))
            self.table.setItem(i, 2, QTableWidgetItem(_format_size(info.size)))
            self.table.setItem(i, 3, QTableWidgetItem(_attachment_type(info)))
        self.table.selectRow(0)

    def _load(self):
        try:
            self._items = list_attachments(self.pdf_path)
        except Exception as e:
            QMessageBox.warning(self, "Anhänge", str(e))
            self._items = []
        if self._filter_renamed_skipped:
            self._apply_table_filter()
        else:
            self._populate_table(self._items)

    def _selected_names(self) -> list[str]:
        rows = {idx.row() for idx in self.table.selectedIndexes()}
        names: list[str] = []
        if self._filter_renamed_skipped:
            # Gefilterte Ansicht: Namen aus Tabellenzellen
            for r in sorted(rows):
                item = self.table.item(r, 0)
                if item is None:
                    continue
                name = (item.text() or "").strip()
                if name and not name.startswith("("):
                    # nur echte Anhänge (nicht „übersprungen“-Zeilen ohne PDF-Eintrag)
                    if any(info.name == name for info in self._items):
                        names.append(name)
            return names
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
        names = self._selected_names()
        if not names:
            return
        self._extract_selected()

    def _resolve_attach_name(
        self,
        preferred: str,
        *,
        batch: bool,
        stats: dict[str, int],
        renamed_names: list[str],
        skipped_names: list[str],
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
            skipped_names.append(name)
            return None
        if self._dup_apply_all == "rename":
            suggested = suggest_attachment_name(self.pdf_path, name)
            stats["renamed"] = stats.get("renamed", 0) + 1
            renamed_names.append(suggested)
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
            skipped_names.append(name)
            return None
        # Umbenennen
        if apply_all:
            # ohne weiteren Dialog: Vorschläge für alle weiteren Konflikte
            self._dup_apply_all = "rename"
            stats["renamed"] = stats.get("renamed", 0) + 1
            renamed_names.append(suggested)
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
                skipped_names.append(name)
                return None
            stats["aborted"] = stats.get("aborted", 0) + 1
            raise _AbortBatch()
        new_name = (new_name or "").strip()
        if not new_name:
            stats["skipped"] = stats.get("skipped", 0) + 1
            skipped_names.append(name)
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
        renamed_names.append(new_name)
        return new_name

    @staticmethod
    def _format_add_status(stats: dict[str, int], *, last_info=None) -> str:
        """Statuszählung Footer — 1.9.5 (leer wenn 0)."""
        # last_info: Kompatibilität 1.9.3-Smoke; Einzel-Hinweis optional
        added = int(stats.get("added", 0) or 0)
        renamed = int(stats.get("renamed", 0) or 0)
        skipped = int(stats.get("skipped", 0) or 0)
        aborted = int(stats.get("aborted", 0) or 0)
        errors = int(stats.get("errors", 0) or 0)
        base = format_attach_add_status(stats)
        if not base:
            return ""
        if (
            added == 1
            and last_info is not None
            and renamed == 0
            and skipped == 0
            and not aborted
            and not errors
        ):
            return f"{base} — {last_info.name} ({last_info.size} B)"
        return base

    def _add_paths(self, paths: list[str | Path]) -> int:
        """Mehrere Dateien hinzufügen; Duplikat-Namen mit Warnung — 1.9.5."""
        files = [Path(p) for p in paths if p and Path(p).is_file()]
        if not files:
            return 0
        self._dup_apply_all = None
        self._filter_renamed_skipped = False
        stats: dict[str, int] = {
            "added": 0,
            "renamed": 0,
            "skipped": 0,
            "aborted": 0,
            "errors": 0,
        }
        renamed_names: list[str] = []
        skipped_names: list[str] = []
        last_info = None
        batch = len(files) > 1
        try:
            for p in files:
                try:
                    resolved = self._resolve_attach_name(
                        p.name,
                        batch=batch,
                        stats=stats,
                        renamed_names=renamed_names,
                        skipped_names=skipped_names,
                    )
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

        self._last_renamed_names = list(renamed_names)
        self._last_skipped_names = list(skipped_names)

        added = int(stats.get("added", 0))
        if added:
            self._changed = True
            remember_recent_dir(str(files[0].parent))
            self._load()
        # Footer statt Modal — 1.9.5 (leer wenn 0)
        self._set_status_footer(stats, last_info=last_info)
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
