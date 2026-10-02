"""Seitenleiste: Suche, Dokumente, Thumbnails, Lesezeichen, Annotationen, Markierungen."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
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
    annotation_activated = Signal(object)  # Annotation oder id
    outline_activated = Signal(int)  # PDF-Seite 0-basiert
    outline_add_requested = Signal()
    outline_delete_requested = Signal()
    annotation_filter_changed = Signal(str)  # Typ-Wert oder "" für alle
    fulltext_hit_activated = Signal(str, object)  # path, page_index|None
    page_thumb_activated = Signal(int)  # PDF-Seite 0-basiert
    pages_reordered = Signal(list)  # alte Indizes in neuer Reihenfolge

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        layout.addWidget(QLabel("Suche / Volltext"))
        self.search = QComboBox()
        self.search.setEditable(True)
        self.search.setInsertPolicy(QComboBox.NoInsert)
        self.search.setMaxCount(20)
        self.search.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.search.lineEdit().setPlaceholderText("Im Dokument oder allen geöffneten…")
        self.search.lineEdit().returnPressed.connect(self._emit_search)
        self.search.activated.connect(lambda _i: self._emit_search())
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
        self.outline.setToolTip("Doppelklick → Seite; +/− zum Bearbeiten")
        self.outline.itemDoubleClicked.connect(self._activate_outline)
        layout.addWidget(self.outline)
        ol_btns = QHBoxLayout()
        self.btn_outline_add = QPushButton("+")
        self.btn_outline_add.setFixedWidth(28)
        self.btn_outline_add.setToolTip("Lesezeichen für aktuelle Seite hinzufügen")
        self.btn_outline_add.clicked.connect(self.outline_add_requested.emit)
        self.btn_outline_del = QPushButton("−")
        self.btn_outline_del.setFixedWidth(28)
        self.btn_outline_del.setToolTip("Ausgewähltes Lesezeichen löschen")
        self.btn_outline_del.clicked.connect(self.outline_delete_requested.emit)
        ol_btns.addWidget(self.btn_outline_add)
        ol_btns.addWidget(self.btn_outline_del)
        ol_btns.addStretch(1)
        layout.addLayout(ol_btns)

        layout.addWidget(QLabel("Annotationen"))
        self.ann_filter = QComboBox()
        self.ann_filter.setToolTip("Nach Annotationstyp filtern")
        self.ann_filter.addItem("Alle Typen", "")
        self.ann_filter.currentIndexChanged.connect(self._on_ann_filter_changed)
        layout.addWidget(self.ann_filter)
        self.annotations = QListWidget()
        self.annotations.setMaximumHeight(140)
        self.annotations.setToolTip("Klick → zur Annotation springen")
        self.annotations.itemClicked.connect(self._activate_annotation)
        layout.addWidget(self.annotations)

        layout.addWidget(QLabel("Treffer / Markierungen"))
        self.marks = QListWidget()
        self.marks.itemDoubleClicked.connect(self._activate_mark)
        layout.addWidget(self.marks)

        self.setMinimumWidth(240)
        self._fulltext_mode = False
        self._ann_all_lines: list[str] = []
        self._ann_all_payloads: list = []
        self._ann_filter_updating = False

    def search_text(self) -> str:
        return self.search.currentText().strip()

    def set_search_text(self, text: str):
        self.search.setEditText(text or "")

    def set_recent_searches(self, queries: list[str]):
        """Füllt Dropdown mit letzten Suchbegriffen; aktueller Text bleibt."""
        current = self.search.currentText()
        self.search.blockSignals(True)
        self.search.clear()
        for q in queries:
            if q:
                self.search.addItem(str(q))
        self.search.setEditText(current)
        self.search.blockSignals(False)

    def _emit_search(self):
        self._fulltext_mode = False
        self.search_requested.emit(self.search_text())

    def _emit_fulltext(self):
        self._fulltext_mode = True
        self.search_requested.emit(self.search_text())

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

    def _activate_annotation(self, item: QListWidgetItem):
        payload = item.data(256)
        if payload is not None:
            self.annotation_activated.emit(payload)

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

        def add_nodes(parent_item: QTreeWidgetItem | None, nodes, path: tuple[int, ...] = ()):
            from ild_pdf.outline import OutlineItem

            for i, node in enumerate(nodes):
                if not isinstance(node, OutlineItem):
                    continue
                item_path = path + (i,)
                label = node.title
                if node.page_index is not None:
                    label += f"  (S. {node.page_index + 1})"
                twi = QTreeWidgetItem([label])
                twi.setData(0, Qt.UserRole, node.page_index)
                twi.setData(0, Qt.UserRole + 1, item_path)
                if parent_item is None:
                    self.outline.addTopLevelItem(twi)
                else:
                    parent_item.addChild(twi)
                if node.children:
                    add_nodes(twi, node.children, item_path)

        add_nodes(None, items)
        self.outline.expandToDepth(1)

    def selected_outline_path(self) -> tuple[int, ...] | None:
        """Pfad (Indizes) des ausgewählten Lesezeichens, sonst None."""
        item = self.outline.currentItem()
        if item is None or item.isDisabled():
            return None
        path = item.data(0, Qt.UserRole + 1)
        if path is None:
            return None
        return tuple(int(i) for i in path)

    def annotation_filter_type(self) -> str:
        """Aktueller Filter: AnnotationType.value oder '' für alle."""
        data = self.ann_filter.currentData()
        return str(data) if data else ""

    def _on_ann_filter_changed(self, _index: int = 0):
        if self._ann_filter_updating:
            return
        self._apply_annotation_filter()
        self.annotation_filter_changed.emit(self.annotation_filter_type())

    def _sync_ann_filter_options(self, payloads: list | None):
        """Filter-Dropdown mit vorkommenden Typen aktualisieren (Auswahl behalten)."""
        current = self.annotation_filter_type()
        types: list[str] = []
        seen: set[str] = set()
        for p in payloads or []:
            t = getattr(getattr(p, "type", None), "value", None) or getattr(p, "type", None)
            if t and str(t) not in seen:
                seen.add(str(t))
                types.append(str(t))
        types.sort()
        self._ann_filter_updating = True
        self.ann_filter.blockSignals(True)
        self.ann_filter.clear()
        self.ann_filter.addItem("Alle Typen", "")
        labels = {
            "highlight": "Highlight",
            "underline": "Unterstreichen",
            "sticky": "Notiz",
            "text": "Text",
            "stamp": "Stempel",
            "callout": "Callout",
            "rectangle": "Rechteck",
            "line": "Linie",
            "arrow": "Pfeil",
            "measure": "Messung",
            "text_overlay": "Text-Overlay",
            "signature_field": "Signaturfeld",
            "signature": "Signatur",
            "redaction": "Schwärzung",
        }
        for t in types:
            self.ann_filter.addItem(labels.get(t, t), t)
        idx = self.ann_filter.findData(current)
        self.ann_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self.ann_filter.blockSignals(False)
        self._ann_filter_updating = False

    def _apply_annotation_filter(self):
        want = self.annotation_filter_type()
        self.annotations.clear()
        for i, line in enumerate(self._ann_all_lines):
            payload = self._ann_all_payloads[i] if i < len(self._ann_all_payloads) else None
            if want:
                t = getattr(getattr(payload, "type", None), "value", None) or getattr(
                    payload, "type", None
                )
                if str(t) != want:
                    continue
            item = QListWidgetItem(line)
            if payload is not None:
                item.setData(256, payload)
            self.annotations.addItem(item)

    def set_annotations(self, lines: list[str], payloads: list | None = None):
        self._ann_all_lines = list(lines)
        self._ann_all_payloads = list(payloads) if payloads else [None] * len(lines)
        self._sync_ann_filter_options(self._ann_all_payloads)
        self._apply_annotation_filter()

    def clear_annotations(self):
        self._ann_all_lines = []
        self._ann_all_payloads = []
        self.annotations.clear()
        self._ann_filter_updating = True
        self.ann_filter.blockSignals(True)
        self.ann_filter.clear()
        self.ann_filter.addItem("Alle Typen", "")
        self.ann_filter.blockSignals(False)
        self._ann_filter_updating = False

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
