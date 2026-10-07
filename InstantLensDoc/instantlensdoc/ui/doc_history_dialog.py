"""Panel: Dokument-Historie (ildhist-v1) — Filter/Export/Clear — 2.2.1–2.2.5."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ild_pdf.doc_history import DocHistory, format_history_summary


class DocHistoryDialog(QDialog):
    """Panel mit Filter, Export (auch gefiltert), Doppelklick→Seite, Clear optional Filter."""

    PANEL_LIMIT = 50

    def __init__(
        self,
        pdf_path: str | Path,
        parent=None,
        *,
        on_goto_page: Optional[Callable[[int], None]] = None,
        page_count: int | None = None,
    ):
        super().__init__(parent)
        self.pdf_path = Path(pdf_path)
        self.hist = DocHistory.for_pdf(self.pdf_path, load=True)
        self._on_goto_page = on_goto_page
        self._page_count = int(page_count) if page_count is not None else None
        self.setWindowTitle("Dokument-Historie")
        self.setWindowModality(Qt.WindowModal)
        self.resize(560, 480)

        layout = QVBoxLayout(self)
        last = self.hist.last_action_ts() or "—"
        self.lbl_meta = QLabel(
            f"Datei: {self.hist.path.name}\n"
            f"Schema: ildhist-v1 · Einträge: {len(self.hist.entries)}\n"
            f"Letzte Aktion: {last} · Anzeige max. {self.PANEL_LIMIT}"
        )
        layout.addWidget(self.lbl_meta)

        filt_row = QHBoxLayout()
        filt_row.addWidget(QLabel("Aktionstyp:"))
        self.cmb_action = QComboBox()
        self.cmb_action.setMinimumWidth(180)
        self.cmb_action.setToolTip("Filter nach Aktionstyp — 2.2.1")
        self.cmb_action.currentIndexChanged.connect(self._refresh)
        filt_row.addWidget(self.cmb_action, 1)
        btn_refresh = QPushButton("Aktualisieren")
        btn_refresh.clicked.connect(self._reload)
        filt_row.addWidget(btn_refresh)
        layout.addLayout(filt_row)

        self.list = QListWidget()
        self.list.setObjectName("docHistoryList")
        self.list.setToolTip(
            "Doppelklick: zur Seite springen, wenn Eintrag eine Seite enthält — 2.2.3"
        )
        self.list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.list, 1)

        # Abwärtskompatibel: Text-Zusammenfassung (Tests/API) — 2.2.1
        self.txt = None  # type: ignore[assignment]

        btn_row = QHBoxLayout()
        btn_export = QPushButton("Export JSON…")
        btn_export.setToolTip("Gesamte Historie als JSON speichern — 2.2.1")
        btn_export.clicked.connect(self._export_json)
        btn_row.addWidget(btn_export)
        btn_export_filt = QPushButton("Export gefilterte Sicht…")
        btn_export_filt.setObjectName("docHistoryExportFiltered")
        btn_export_filt.setToolTip(
            "Nur die aktuell gefilterte Sicht als JSON exportieren — 2.2.3"
        )
        btn_export_filt.clicked.connect(self._export_filtered)
        btn_row.addWidget(btn_export_filt)
        btn_clear = QPushButton("Leeren…")
        btn_clear.setObjectName("docHistoryClear")
        btn_clear.setToolTip(
            "Historie leeren — optional nur aktuellen Filter; "
            "Zähler „N Einträge entfernt“ · Undo/Redo Clear — 2.2.5"
        )
        btn_clear.clicked.connect(self._clear_with_confirm)
        btn_row.addWidget(btn_clear)
        self.btn_undo_clear = QPushButton("Clear rückgängig")
        self.btn_undo_clear.setObjectName("docHistoryUndoClear")
        self.btn_undo_clear.setEnabled(False)
        self.btn_undo_clear.setToolTip(
            "Letztes Clear in dieser Session rückgängig — 2.2.5"
        )
        self.btn_undo_clear.clicked.connect(self._undo_clear)
        btn_row.addWidget(self.btn_undo_clear)
        self.btn_redo_clear = QPushButton("Clear wiederholen")
        self.btn_redo_clear.setObjectName("docHistoryRedoClear")
        self.btn_redo_clear.setEnabled(False)
        self.btn_redo_clear.setToolTip(
            "Clear nach Undo erneut anwenden (Session) — 2.2.5"
        )
        self.btn_redo_clear.clicked.connect(self._redo_clear)
        btn_row.addWidget(self.btn_redo_clear)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        close_btn = buttons.button(QDialogButtonBox.Close)
        if close_btn is not None:
            close_btn.clicked.connect(self.accept)
        layout.addWidget(buttons)

        self._fill_actions()
        self._refresh()

    def _fill_actions(self) -> None:
        self.cmb_action.blockSignals(True)
        cur = self.cmb_action.currentData()
        self.cmb_action.clear()
        self.cmb_action.addItem("Alle", "*")
        for act in self.hist.action_types():
            self.cmb_action.addItem(act, act)
        if cur:
            idx = self.cmb_action.findData(cur)
            if idx >= 0:
                self.cmb_action.setCurrentIndex(idx)
        self.cmb_action.blockSignals(False)

    def _update_clear_buttons(self) -> None:
        """Undo/Redo-Clear-Buttons an Session-Snapshot anpassen — 2.2.5."""
        self.btn_undo_clear.setEnabled(bool(self.hist.can_undo_clear()))
        self.btn_redo_clear.setEnabled(bool(self.hist.can_redo_clear()))

    def _sync_panel_from_hist(self) -> None:
        """UI aus aktuellem Hist aktualisieren (Session-Snapshots behalten) — 2.2.5."""
        last = self.hist.last_action_ts() or "—"
        self.lbl_meta.setText(
            f"Datei: {self.hist.path.name}\n"
            f"Schema: ildhist-v1 · Einträge: {len(self.hist.entries)}\n"
            f"Letzte Aktion: {last} · Anzeige max. {self.PANEL_LIMIT}"
        )
        self._fill_actions()
        self._refresh()
        self._update_clear_buttons()

    def _reload(self) -> None:
        # Session Undo/Redo Clear über Disk-Reload hinweg behalten — 2.2.5
        undo = getattr(self.hist, "_clear_undo", None)
        redo = getattr(self.hist, "_clear_redo", None)
        self.hist = DocHistory.for_pdf(self.pdf_path, load=True)
        self.hist._clear_undo = undo
        self.hist._clear_redo = redo
        self._sync_panel_from_hist()

    def _selected_action(self) -> str | None:
        data = self.cmb_action.currentData()
        if data in (None, "*", ""):
            return None
        return str(data)

    def _refresh(self) -> None:
        entries = self.hist.filter_entries(
            self._selected_action(), limit=self.PANEL_LIMIT
        )
        self.list.clear()
        if not entries:
            item = QListWidgetItem("(keine Einträge)")
            item.setFlags(Qt.NoItemFlags)
            self.list.addItem(item)
            return
        # Neueste oben
        for e in reversed(entries):
            ts = e.ts.replace("T", " ").replace("+00:00", " UTC")
            pg = e.resolved_page()
            page_bit = f" [S.{pg + 1}]" if pg is not None else ""
            detail = f" — {e.detail}" if e.detail else ""
            text = f"{ts}  {e.action}{page_bit}{detail}"
            item = QListWidgetItem(text)
            if pg is not None:
                item.setData(Qt.UserRole, int(pg))
                item.setToolTip(f"Doppelklick → Seite {pg + 1}")
            else:
                item.setData(Qt.UserRole, None)
                item.setToolTip("Kein Seitenbezug in diesem Eintrag")
            self.list.addItem(item)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        if item is None:
            return
        page = item.data(Qt.UserRole)
        if page is None:
            return
        try:
            idx = int(page)
        except (TypeError, ValueError):
            return
        if idx < 0:
            return
        if self._page_count is not None and idx >= self._page_count:
            QMessageBox.information(
                self,
                "Dokument-Historie",
                f"Seite {idx + 1} liegt außerhalb des Dokuments "
                f"({self._page_count} Seiten).",
            )
            return
        if callable(self._on_goto_page):
            try:
                self._on_goto_page(idx)
            except Exception as e:
                QMessageBox.warning(
                    self, "Dokument-Historie", f"Sprung fehlgeschlagen:\n{e}"
                )
                return
            self.accept()

    def _no_undo_clear_hint(self) -> str:
        """Klarer DE-Hinweis wenn Clear-Undo nicht möglich — 2.2.5."""
        return (
            "Clear-Undo nicht möglich.\n\n"
            "Es liegt kein Session-Snapshot vor. "
            "Bitte zuerst die Historie leeren — danach ist "
            "„Clear rückgängig“ in derselben Session verfügbar."
        )

    def _after_clear(self, n_removed: int) -> None:
        """Zähler „N Einträge entfernt“ + Undo Clear oder klarer Hinweis — 2.2.5."""
        self._sync_panel_from_hist()
        can_undo = bool(self.hist.can_undo_clear())
        if n_removed <= 0:
            return
        count_msg = (
            f"{n_removed} Eintrag entfernt"
            if n_removed == 1
            else f"{n_removed} Einträge entfernt"
        )
        if can_undo:
            reply = QMessageBox.question(
                self,
                "Dokument-Historie",
                f"{count_msg}.\n\nClear rückgängig machen?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self._undo_clear()
        else:
            QMessageBox.information(
                self,
                "Dokument-Historie",
                f"{count_msg}.\n\n{self._no_undo_clear_hint()}",
            )

    def _undo_clear(self) -> None:
        """Letztes Clear aus Session-Snapshot wiederherstellen — 2.2.5."""
        if not self.hist.can_undo_clear():
            QMessageBox.information(
                self,
                "Dokument-Historie",
                self._no_undo_clear_hint(),
            )
            self._update_clear_buttons()
            return
        if self.hist.undo_clear(save=True):
            self._sync_panel_from_hist()
            QMessageBox.information(
                self,
                "Dokument-Historie",
                "Clear rückgängig gemacht.\n"
                "„Clear wiederholen“ stellt das Leeren erneut her.",
            )
        else:
            self._update_clear_buttons()

    def _redo_clear(self) -> None:
        """Clear nach Undo erneut anwenden (Session) — 2.2.5."""
        if not self.hist.can_redo_clear():
            QMessageBox.information(
                self,
                "Dokument-Historie",
                "Clear-Redo nicht möglich.\n\n"
                "Es liegt kein Redo-Snapshot vor. "
                "Zuerst Clear rückgängig machen — danach ist "
                "„Clear wiederholen“ in derselben Session verfügbar.",
            )
            self._update_clear_buttons()
            return
        if self.hist.redo_clear(save=True):
            self._sync_panel_from_hist()
            QMessageBox.information(
                self, "Dokument-Historie", "Clear erneut angewendet."
            )
        else:
            self._update_clear_buttons()

    def _clear_with_confirm(self) -> None:
        """Clear: bei aktivem Filter optional nur Filter; Zähler+Undo — 2.2.4."""
        filt = self._selected_action()
        if filt:
            n_filt = len(self.hist.filter_entries(filt, limit=10_000))
            if n_filt <= 0:
                QMessageBox.information(
                    self, "Dokument-Historie", "Keine Einträge für diesen Filter."
                )
                return
            reply = QMessageBox.question(
                self,
                "Dokument-Historie leeren",
                f"Nur aktuellen Filter „{filt}“ löschen ({n_filt} Einträge)?\n\n"
                f"„Ja“ = nur Filter · „Nein“ = gesamte Historie "
                f"({len(self.hist.entries)} Einträge) · Abbrechen = nichts.",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            if reply == QMessageBox.Cancel:
                return
            if reply == QMessageBox.Yes:
                n_removed = self.hist.clear_filtered(filt, save=True)
            else:
                # Nein = gesamte Historie (wie bisher mit Bestätigung)
                n = len(self.hist.entries)
                reply2 = QMessageBox.question(
                    self,
                    "Dokument-Historie leeren",
                    f"Wirklich alle {n} Einträge löschen?\n"
                    "(Undo/Redo Clear in dieser Session möglich — 2.2.5)",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if reply2 != QMessageBox.Yes:
                    return
                n_removed = self.hist.clear(save=True)
            self._after_clear(n_removed)
            return
        n = len(self.hist.entries)
        if n <= 0:
            QMessageBox.information(self, "Dokument-Historie", "Historie ist bereits leer.")
            return
        reply = QMessageBox.question(
            self,
            "Dokument-Historie leeren",
            f"Wirklich alle {n} Einträge löschen?\n"
            "(Undo/Redo Clear in dieser Session möglich — 2.2.5)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        n_removed = self.hist.clear(save=True)
        self._after_clear(n_removed)

    def summary_text(self) -> str:
        """Textzusammenfassung (Tests/API) — 2.2.1 kompatibel."""
        entries = self.hist.filter_entries(
            self._selected_action(), limit=self.PANEL_LIMIT
        )
        return format_history_summary(entries, max_items=self.PANEL_LIMIT)

    def _export_json(self) -> None:
        default = str(self.hist.path.with_name(self.hist.path.stem + "-export.json"))
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Dokument-Historie exportieren",
            default,
            "JSON (*.json);;Alle Dateien (*)",
        )
        if not path:
            return
        try:
            out = self.hist.export_json(path)
        except Exception as e:
            QMessageBox.warning(self, "Dokument-Historie", f"Export fehlgeschlagen:\n{e}")
            return
        QMessageBox.information(
            self, "Dokument-Historie", f"Exportiert:\n{out}"
        )

    def _export_filtered(self) -> None:
        """Gefilterte Sicht exportieren — 2.2.3."""
        filt = self._selected_action()
        suffix = f"-{filt}" if filt else "-view"
        # Dateiname-sicher
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in (suffix or ""))
        default = str(
            self.hist.path.with_name(self.hist.path.stem + f"{safe}-filtered.json")
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Gefilterte Historie exportieren",
            default,
            "JSON (*.json);;Alle Dateien (*)",
        )
        if not path:
            return
        try:
            out = self.hist.export_filtered_json(
                path, filt, limit=self.PANEL_LIMIT
            )
        except Exception as e:
            QMessageBox.warning(self, "Dokument-Historie", f"Export fehlgeschlagen:\n{e}")
            return
        QMessageBox.information(
            self, "Dokument-Historie", f"Gefilterte Sicht exportiert:\n{out}"
        )
