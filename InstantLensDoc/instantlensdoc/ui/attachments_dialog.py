"""Dialog: PDF-Anhänge auflisten und extrahieren."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ild_pdf.attachments import (
    AttachmentInfo,
    extract_all_attachments,
    extract_attachment,
    list_attachments,
)
from instantlensdoc.core.app_settings import dialog_start_dir, remember_recent_dir


class AttachmentsDialog(QDialog):
    """Zeigt eingebettete PDF-Anhänge und erlaubt Extraktion."""

    def __init__(self, pdf_path: str | Path, parent=None):
        super().__init__(parent)
        self.pdf_path = Path(pdf_path)
        self.setWindowTitle("PDF-Anhänge")
        self.resize(640, 400)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"{self.pdf_path.name} — eingebettete Dateianhänge"))

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Name", "Dateiname", "Größe", "MIME / Beschreibung"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

        row = QHBoxLayout()
        self.btn_extract = QPushButton("Auswahl extrahieren…")
        self.btn_extract.clicked.connect(self._extract_selected)
        self.btn_all = QPushButton("Alle extrahieren…")
        self.btn_all.clicked.connect(self._extract_all)
        row.addWidget(self.btn_extract)
        row.addWidget(self.btn_all)
        row.addStretch(1)
        layout.addLayout(row)

        self._items: list[AttachmentInfo] = []
        self._load()

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _load(self):
        try:
            self._items = list_attachments(self.pdf_path)
        except Exception as e:
            QMessageBox.warning(self, "Anhänge", str(e))
            self._items = []
        self.table.setRowCount(0)
        if not self._items:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("(keine Anhänge)"))
            self.btn_extract.setEnabled(False)
            self.btn_all.setEnabled(False)
            return
        self.table.setRowCount(len(self._items))
        for i, info in enumerate(self._items):
            self.table.setItem(i, 0, QTableWidgetItem(info.name))
            self.table.setItem(i, 1, QTableWidgetItem(info.filename or info.name))
            size_txt = f"{info.size:,} B".replace(",", ".") if info.size else "—"
            self.table.setItem(i, 2, QTableWidgetItem(size_txt))
            extra = info.mime_type or ""
            if info.description:
                extra = f"{extra}; {info.description}" if extra else info.description
            self.table.setItem(i, 3, QTableWidgetItem(extra))
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
