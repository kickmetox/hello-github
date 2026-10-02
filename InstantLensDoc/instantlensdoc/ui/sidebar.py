"""Seitenleiste: Dokumentenbaum, Suche, Annotationen/Markierungen."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class Sidebar(QWidget):
    file_activated = Signal(str)
    search_requested = Signal(str)
    search_next_requested = Signal()
    mark_activated = Signal(int)  # Index in Markierungsliste

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        layout.addWidget(QLabel("Suche / Markieren"))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Im Dokument suchen…")
        self.search.returnPressed.connect(self._emit_search)
        layout.addWidget(self.search)

        btn_row = QHBoxLayout()
        self.btn_search = QPushButton("Suchen")
        self.btn_search.clicked.connect(self._emit_search)
        self.btn_next = QPushButton("Weiter")
        self.btn_next.clicked.connect(self.search_next_requested.emit)
        btn_row.addWidget(self.btn_search)
        btn_row.addWidget(self.btn_next)
        layout.addLayout(btn_row)

        layout.addWidget(QLabel("Dokumente"))
        self.files = QListWidget()
        self.files.itemDoubleClicked.connect(self._activate)
        layout.addWidget(self.files)

        layout.addWidget(QLabel("Annotationen / Markierungen"))
        self.marks = QListWidget()
        self.marks.itemDoubleClicked.connect(self._activate_mark)
        layout.addWidget(self.marks)

        self.setMinimumWidth(220)

    def _emit_search(self):
        self.search_requested.emit(self.search.text().strip())

    def _activate(self, item: QListWidgetItem):
        path = item.data(256)  # Qt.UserRole
        if path:
            self.file_activated.emit(str(path))

    def _activate_mark(self, item: QListWidgetItem):
        row = self.marks.row(item)
        self.mark_activated.emit(row)

    def add_document(self, path: str | Path, title: str | None = None):
        path = Path(path)
        # Duplikate vermeiden
        for i in range(self.files.count()):
            it = self.files.item(i)
            if it and it.data(256) == str(path):
                return
        item = QListWidgetItem(title or path.name)
        item.setData(256, str(path))
        self.files.addItem(item)

    def clear_documents(self):
        self.files.clear()

    def set_marks(self, lines: list[str], payloads: list | None = None):
        """Markierungsliste setzen. payloads[i] optional (z.B. Annotation-Objekt)."""
        self.marks.clear()
        for i, line in enumerate(lines):
            item = QListWidgetItem(line)
            if payloads and i < len(payloads):
                item.setData(256, payloads[i])
            self.marks.addItem(item)

    def append_mark(self, line: str, payload=None):
        item = QListWidgetItem(line)
        if payload is not None:
            item.setData(256, payload)
        self.marks.addItem(item)

    def mark_payload(self, index: int):
        item = self.marks.item(index)
        if item is None:
            return None
        return item.data(256)
