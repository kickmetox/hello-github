"""Seitenleiste: Dokumentenbaum + Suche."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)


class Sidebar(QWidget):
    file_activated = Signal(str)
    search_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        layout.addWidget(QLabel("Suche / Markieren"))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Im Dokument suchen…")
        self.search.returnPressed.connect(self._emit_search)
        layout.addWidget(self.search)

        layout.addWidget(QLabel("Dokumente"))
        self.files = QListWidget()
        self.files.itemDoubleClicked.connect(self._activate)
        layout.addWidget(self.files)

        layout.addWidget(QLabel("Annotationen / Markierungen"))
        self.marks = QListWidget()
        layout.addWidget(self.marks)

    def _emit_search(self):
        self.search_requested.emit(self.search.text().strip())

    def _activate(self, item: QListWidgetItem):
        path = item.data(256)  # Qt.UserRole
        if path:
            self.file_activated.emit(str(path))

    def add_document(self, path: str | Path, title: str | None = None):
        path = Path(path)
        item = QListWidgetItem(title or path.name)
        item.setData(256, str(path))
        self.files.addItem(item)

    def clear_documents(self):
        self.files.clear()

    def set_marks(self, lines: list[str]):
        self.marks.clear()
        for line in lines:
            self.marks.addItem(line)
