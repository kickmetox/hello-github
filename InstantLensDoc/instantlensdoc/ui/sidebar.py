"""Seitenleiste: Suche, Dokumente, Thumbnails, Lesezeichen, Markierungen."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ThumbnailList(QListWidget):
    """Icon-Liste mit InternalMove; meldet neue Seitenreihenfolge nach Drop."""

    pages_reordered = Signal(list)  # list[int] alte Indizes in neuer Reihenfolge

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.IconMode)
        self.setIconSize(QPixmap(72, 96).size())
        self.setResizeMode(QListWidget.Adjust)
        self.setMovement(QListWidget.Snap)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSpacing(4)
        self.setMaximumHeight(200)
        self.setMinimumHeight(100)
        self.setToolTip("Ziehen zum Neuordnen der PDF-Seiten")
        self._reorder_enabled = True

    def set_reorder_enabled(self, enabled: bool):
        self._reorder_enabled = bool(enabled)
        mode = QAbstractItemView.InternalMove if enabled else QAbstractItemView.NoDragDrop
        self.setDragDropMode(mode)

    def dropEvent(self, event):
        if not self._reorder_enabled:
            event.ignore()
            return
        super().dropEvent(event)
        order: list[int] = []
        for i in range(self.count()):
            item = self.item(i)
            if item is None:
                continue
            page = item.data(Qt.UserRole)
            if page is not None:
                order.append(int(page))
        if order:
            self.pages_reordered.emit(order)


class Sidebar(QWidget):
    file_activated = Signal(str)
    recent_activated = Signal(str)
    search_requested = Signal(str)
    search_next_requested = Signal()
    mark_activated = Signal(int)  # Index in Markierungsliste
    outline_activated = Signal(int)  # PDF-Seite 0-basiert
    fulltext_hit_activated = Signal(str, object)  # path, page_index|None
    page_thumb_activated = Signal(int)  # PDF-Seite 0-basiert
    pages_reordered = Signal(list)  # alte Indizes in neuer Reihenfolge

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        layout.addWidget(QLabel("Suche / Volltext"))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Im Dokument oder allen geöffneten…")
        self.search.returnPressed.connect(self._emit_search)
        layout.addWidget(self.search)

        btn_row = QHBoxLayout()
        self.btn_search = QPushButton("Suchen")
        self.btn_search.clicked.connect(self._emit_search)
        self.btn_next = QPushButton("Weiter")
        self.btn_next.clicked.connect(self.search_next_requested.emit)
        self.btn_full = QPushButton("Alle Docs")
        self.btn_full.setToolTip("Volltextsuche über alle Dokumente in der Liste")
        self.btn_full.clicked.connect(self._emit_fulltext)
        btn_row.addWidget(self.btn_search)
        btn_row.addWidget(self.btn_next)
        btn_row.addWidget(self.btn_full)
        layout.addLayout(btn_row)

        layout.addWidget(QLabel("Zuletzt geöffnet"))
        self.recent = QListWidget()
        self.recent.setMaximumHeight(90)
        self.recent.itemDoubleClicked.connect(self._activate_recent)
        layout.addWidget(self.recent)

        layout.addWidget(QLabel("Dokumente"))
        self.files = QListWidget()
        self.files.setMaximumHeight(100)
        self.files.itemDoubleClicked.connect(self._activate)
        layout.addWidget(self.files)

        layout.addWidget(QLabel("Seiten (Vorschaubilder) — ziehen zum Ordnen"))
        self.thumbs = ThumbnailList()
        self.thumbs.itemClicked.connect(self._activate_thumb)
        self.thumbs.pages_reordered.connect(self.pages_reordered.emit)
        layout.addWidget(self.thumbs)

        layout.addWidget(QLabel("Lesezeichen / Outline"))
        self.outline = QTreeWidget()
        self.outline.setHeaderHidden(True)
        self.outline.setMaximumHeight(120)
        self.outline.itemDoubleClicked.connect(self._activate_outline)
        layout.addWidget(self.outline)

        layout.addWidget(QLabel("Treffer / Markierungen"))
        self.marks = QListWidget()
        self.marks.itemDoubleClicked.connect(self._activate_mark)
        layout.addWidget(self.marks)

        self.setMinimumWidth(240)
        self._fulltext_mode = False

    def _emit_search(self):
        self._fulltext_mode = False
        self.search_requested.emit(self.search.text().strip())

    def _emit_fulltext(self):
        self._fulltext_mode = True
        self.search_requested.emit(self.search.text().strip())

    @property
    def fulltext_mode(self) -> bool:
        return self._fulltext_mode

    def _activate(self, item: QListWidgetItem):
        path = item.data(256)
        if path:
            self.file_activated.emit(str(path))

    def _activate_recent(self, item: QListWidgetItem):
        path = item.data(256)
        if path:
            self.recent_activated.emit(str(path))

    def _activate_mark(self, item: QListWidgetItem):
        row = self.marks.row(item)
        payload = item.data(256)
        if isinstance(payload, tuple) and len(payload) == 2:
            path, page = payload
            self.fulltext_hit_activated.emit(str(path), page)
            return
        self.mark_activated.emit(row)

    def _activate_outline(self, item: QTreeWidgetItem, _column: int):
        page = item.data(0, Qt.UserRole)
        if page is not None:
            self.outline_activated.emit(int(page))

    def _activate_thumb(self, item: QListWidgetItem):
        page = item.data(Qt.UserRole)
        if page is not None:
            self.page_thumb_activated.emit(int(page))

    def set_recent(self, paths: list[str]):
        self.recent.clear()
        for p in paths:
            path = Path(p)
            item = QListWidgetItem(path.name)
            item.setToolTip(str(path))
            item.setData(256, str(path))
            self.recent.addItem(item)

    def add_document(self, path: str | Path, title: str | None = None):
        path = Path(path)
        for i in range(self.files.count()):
            it = self.files.item(i)
            if it and it.data(256) == str(path):
                return
        item = QListWidgetItem(title or path.name)
        item.setData(256, str(path))
        self.files.addItem(item)

    def clear_documents(self):
        self.files.clear()

    def document_paths(self) -> list[str]:
        out: list[str] = []
        for i in range(self.files.count()):
            it = self.files.item(i)
            if it and it.data(256):
                out.append(str(it.data(256)))
        return out

    def clear_thumbs(self):
        self.thumbs.clear()

    def set_page_thumbs(self, images: list, *, current: int = 0):
        """images: Liste von PIL.Image oder QPixmap/QImage."""
        self.thumbs.clear()
        for i, img in enumerate(images):
            pm = self._to_pixmap(img)
            item = QListWidgetItem(f"S. {i + 1}")
            if not pm.isNull():
                item.setIcon(QIcon(pm))
            item.setData(Qt.UserRole, i)
            item.setToolTip(f"Seite {i + 1} — ziehen zum Neuordnen")
            self.thumbs.addItem(item)
        self.select_thumb(current)

    def select_thumb(self, page_index: int):
        if 0 <= page_index < self.thumbs.count():
            self.thumbs.setCurrentRow(page_index)

    @staticmethod
    def _to_pixmap(img) -> QPixmap:
        if isinstance(img, QPixmap):
            return img
        if isinstance(img, QImage):
            return QPixmap.fromImage(img)
        try:
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            data = img.tobytes("raw", "RGBA")
            qimg = QImage(data, img.width, img.height, QImage.Format_RGBA8888)
            return QPixmap.fromImage(qimg.copy()).scaled(
                72, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        except Exception:
            return QPixmap()

    def set_outline(self, items, *, _add=None):
        """items: Liste von OutlineItem (ild_pdf) oder leer."""
        self.outline.clear()
        if not items:
            empty = QTreeWidgetItem("(kein Outline)")
            empty.setDisabled(True)
            self.outline.addTopLevelItem(empty)
            return

        def add_nodes(parent_item: QTreeWidgetItem | None, nodes):
            from ild_pdf.outline import OutlineItem

            for node in nodes:
                if not isinstance(node, OutlineItem):
                    continue
                label = node.title
                if node.page_index is not None:
                    label += f"  (S. {node.page_index + 1})"
                twi = QTreeWidgetItem([label])
                twi.setData(0, Qt.UserRole, node.page_index)
                if parent_item is None:
                    self.outline.addTopLevelItem(twi)
                else:
                    parent_item.addChild(twi)
                if node.children:
                    add_nodes(twi, node.children)

        add_nodes(None, items)
        self.outline.expandToDepth(1)

    def set_marks(self, lines: list[str], payloads: list | None = None):
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
