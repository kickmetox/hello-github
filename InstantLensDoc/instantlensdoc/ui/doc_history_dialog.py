"""Panel: Dokument-Historie (ildhist-v1) — letzte 50, Filter, Export JSON — 2.2.1."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
)

from ild_pdf.doc_history import DocHistory, format_history_summary


class DocHistoryDialog(QDialog):
    """Nicht-modales Panel mit Filter Aktionstyp + JSON-Export."""

    PANEL_LIMIT = 50

    def __init__(self, pdf_path: str | Path, parent=None):
        super().__init__(parent)
        self.pdf_path = Path(pdf_path)
        self.hist = DocHistory.for_pdf(self.pdf_path, load=True)
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

        self.txt = QPlainTextEdit()
        self.txt.setReadOnly(True)
        self.txt.setLineWrapMode(QPlainTextEdit.NoWrap)
        layout.addWidget(self.txt, 1)

        btn_row = QHBoxLayout()
        btn_export = QPushButton("Export JSON…")
        btn_export.setToolTip("ildhist-v1 Payload als JSON speichern — 2.2.1")
        btn_export.clicked.connect(self._export_json)
        btn_row.addWidget(btn_export)
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

    def _reload(self) -> None:
        self.hist = DocHistory.for_pdf(self.pdf_path, load=True)
        last = self.hist.last_action_ts() or "—"
        self.lbl_meta.setText(
            f"Datei: {self.hist.path.name}\n"
            f"Schema: ildhist-v1 · Einträge: {len(self.hist.entries)}\n"
            f"Letzte Aktion: {last} · Anzeige max. {self.PANEL_LIMIT}"
        )
        self._fill_actions()
        self._refresh()

    def _selected_action(self) -> str | None:
        data = self.cmb_action.currentData()
        if data in (None, "*", ""):
            return None
        return str(data)

    def _refresh(self) -> None:
        entries = self.hist.filter_entries(
            self._selected_action(), limit=self.PANEL_LIMIT
        )
        self.txt.setPlainText(
            format_history_summary(entries, max_items=self.PANEL_LIMIT)
        )

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
