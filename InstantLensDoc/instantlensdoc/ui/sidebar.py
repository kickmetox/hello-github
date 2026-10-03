"""Seitenleiste: Suche, Dokumente, Thumbnails, Lesezeichen, Annotationen, Markierungen."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QStringListModel, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QCompleter,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from instantlensdoc.core.app_settings import pdf_thumbnail_icon_size


def normalize_ann_color(value: object) -> str:
    """Farbe als #RRGGBB normalisieren; leer → ''."""
    raw = str(value or "").strip()
    if not raw:
        return ""
    if not raw.startswith("#"):
        raw = "#" + raw
    c = QColor(raw)
    if not c.isValid():
        return raw.upper()
    return c.name().upper()


# Deutsche Typ-Labels (Filter-Dropdown + Annotation-Suche)
ANN_TYPE_LABELS = {
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


class DocumentList(QListWidget):
    """Dokument-/Session-Tabs; Drag InternalMove → Reihenfolge speichern."""

    documents_reordered = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumHeight(100)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setToolTip("Ziehen zum Neuordnen — Reihenfolge wird in der Session gespeichert")
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
        self.documents_reordered.emit()


class ThumbnailList(QListWidget):
    """Icon-Liste mit InternalMove; meldet neue Seitenreihenfolge nach Drop."""

    pages_reordered = Signal(list)  # list[int] alte Indizes in neuer Reihenfolge

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.IconMode)
        w, h = pdf_thumbnail_icon_size()
        self.setIconSize(QPixmap(w, h).size())
        self.setResizeMode(QListWidget.Adjust)
        self.setMovement(QListWidget.Snap)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSpacing(4)
        self.setMaximumHeight(200)
        self.setMinimumHeight(100)
        self.setToolTip("Ziehen zum Neuordnen der PDF-Seiten")
        self._reorder_enabled = True

    def apply_icon_size(self, width: int | None = None, height: int | None = None):
        if width is None or height is None:
            width, height = pdf_thumbnail_icon_size()
        self.setIconSize(QPixmap(int(width), int(height)).size())

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


class PageFavoriteList(QListWidget):
    """Nummerierte PDF-Favoriten; Drag InternalMove → neue Reihenfolge."""

    favorites_reordered = Signal(list)  # list[int] Seiten 0-basiert in neuer Reihenfolge

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumHeight(100)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setMovement(QListWidget.Snap)
        self.setToolTip(
            "Nummerierte Favoriten — Klick springt; ziehen zum Umsortieren (★ / Ctrl+Shift+F)"
        )
        self._reorder_enabled = True
        self._renumbering = False

    def set_reorder_enabled(self, enabled: bool):
        self._reorder_enabled = bool(enabled)
        mode = QAbstractItemView.InternalMove if enabled else QAbstractItemView.NoDragDrop
        self.setDragDropMode(mode)

    def dropEvent(self, event):
        if not self._reorder_enabled or self._renumbering:
            event.ignore()
            return
        super().dropEvent(event)
        order: list[int] = []
        for i in range(self.count()):
            item = self.item(i)
            if item is None:
                continue
            page = item.data(Qt.UserRole)
            if page is None:
                page = item.data(256)
            if page is not None:
                try:
                    order.append(int(page))
                except (TypeError, ValueError):
                    continue
        if order:
            self._renumber_items()
            self.favorites_reordered.emit(order)

    def _renumber_items(self):
        """Anzeige-Nummern nach Drag anpassen (1. Seite N …)."""
        self._renumbering = True
        try:
            for i in range(self.count()):
                item = self.item(i)
                if item is None:
                    continue
                page = item.data(Qt.UserRole)
                if page is None:
                    continue
                tip_extra = ""
                tip = item.toolTip() or ""
                if "(" in tip and tip.endswith(")"):
                    # Label in Tooltip beibehalten falls vorhanden
                    pass
                label = ""
                text = item.text()
                if "(" in text and text.endswith(")"):
                    label = text[text.rfind("(") + 1 : -1]
                idx = int(page)
                new_text = f"{i + 1}. Seite {idx + 1}"
                if label:
                    new_text = f"{new_text} ({label})"
                item.setText(new_text)
                item.setToolTip(f"Favorit #{i + 1} → Seite {idx + 1}")
        finally:
            self._renumbering = False


class Sidebar(QWidget):
    file_activated = Signal(str)
    recent_activated = Signal(str)
    search_requested = Signal(str)
    search_next_requested = Signal()
    search_prev_requested = Signal()
    mark_activated = Signal(int)  # Index in Markierungsliste
    annotation_activated = Signal(object)  # Annotation oder id
    outline_activated = Signal(int)  # PDF-Seite 0-basiert
    outline_add_requested = Signal()
    outline_delete_requested = Signal()
    annotation_filter_changed = Signal(str)  # Typ-Wert oder "" für alle
    annotation_color_filter_changed = Signal(str)  # #RRGGBB oder "" für alle
    annotation_page_filter_changed = Signal(bool)  # nur aktuelle Seite
    annotation_tag_filter_changed = Signal(object)  # list[str] Tags oder [] für alle
    annotation_tag_rename_requested = Signal(str, str)  # old_tag, new_tag (global)
    annotation_group_edit_requested = Signal(int)  # Seitenindex der Gruppe
    fulltext_hit_activated = Signal(str, object)  # path, page_index|None
    page_thumb_activated = Signal(int)  # PDF-Seite 0-basiert
    page_favorite_activated = Signal(int)  # PDF-Seite 0-basiert (Favoriten-Liste)
    page_favorites_reordered = Signal(list)  # Seiten 0-basiert neue Reihenfolge
    documents_reordered = Signal()  # Dokument-/Session-Tab-Reihenfolge geändert
    line_favorite_activated = Signal(int)  # Editor-Zeile 1-basiert
    line_favorite_label_edit = Signal(int)  # Editor-Zeile 1-basiert → Label bearbeiten
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
        self.search.lineEdit().setPlaceholderText("Im Dokument · Alle Docs · Alle PDFs…")
        self.search.lineEdit().returnPressed.connect(self._emit_search)
        self.search.activated.connect(lambda _i: self._emit_search())
        layout.addWidget(self.search)

        btn_row = QHBoxLayout()
        self.btn_search = QPushButton("Suchen")
        self.btn_search.setToolTip("Suche im aktuellen Dokument")
        self.btn_search.clicked.connect(self._emit_search)
        self.btn_prev = QPushButton("Zurück")
        self.btn_prev.setToolTip(
            "Vorheriger Treffer — über Docs (Alle Docs/PDFs) oder Seite/Editor"
        )
        self.btn_prev.clicked.connect(self.search_prev_requested.emit)
        self.btn_next = QPushButton("Weiter")
        self.btn_next.setToolTip(
            "Nächster Treffer — über Docs (Alle Docs/PDFs) oder Seite/Editor"
        )
        self.btn_next.clicked.connect(self.search_next_requested.emit)
        self.btn_full = QPushButton("Alle Docs")
        self.btn_full.setToolTip("Volltextsuche über alle Dokumente in der Liste")
        self.btn_full.clicked.connect(self._emit_fulltext)
        self.btn_pdfs = QPushButton("Alle PDFs")
        self.btn_pdfs.setToolTip(
            "PDF-Schnellsuche: Volltext nur über geöffnete / gelistete PDFs "
            "(eine PDF-Öffnung pro Datei, Sprung + Highlight)"
        )
        self.btn_pdfs.clicked.connect(self._emit_pdf_fulltext)
        btn_row.addWidget(self.btn_search)
        btn_row.addWidget(self.btn_prev)
        btn_row.addWidget(self.btn_next)
        btn_row.addWidget(self.btn_full)
        btn_row.addWidget(self.btn_pdfs)
        layout.addLayout(btn_row)
        self.search_hits_label = QLabel("")
        self.search_hits_label.setObjectName("searchHitsLabel")
        self.search_hits_label.setStyleSheet(
            "QLabel#searchHitsLabel { color: #555; font-size: 11px; }"
        )
        self.search_hits_label.setToolTip("Trefferanzahl der letzten Schnellsuche")
        layout.addWidget(self.search_hits_label)

        layout.addWidget(QLabel("Schnellsuche-Treffer / Markierungen"))
        self.marks = QListWidget()
        self.marks.setObjectName("searchHitsList")
        self.marks.setMaximumHeight(140)
        self.marks.setToolTip(
            "Schnellsuche-Trefferliste — Klick öffnet Treffer / springt zur Markierung"
        )
        self.marks.itemClicked.connect(self._activate_mark)
        self.marks.itemActivated.connect(self._activate_mark)
        layout.addWidget(self.marks)

        layout.addWidget(QLabel("Zuletzt geöffnet"))
        self.recent = QListWidget()
        self.recent.setMaximumHeight(90)
        self.recent.itemDoubleClicked.connect(self._activate_recent)
        layout.addWidget(self.recent)

        layout.addWidget(QLabel("Dokumente — ziehen zum Ordnen"))
        self.files = DocumentList()
        self.files.itemDoubleClicked.connect(self._activate)
        self.files.documents_reordered.connect(self.documents_reordered.emit)
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
        self.outline.setToolTip("Doppelklick oder Enter → Seite; +/− zum Bearbeiten")
        self.outline.itemDoubleClicked.connect(self._activate_outline)
        self.outline.itemActivated.connect(self._activate_outline)
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

        layout.addWidget(QLabel("PDF-Favoriten — ziehen zum Ordnen"))
        self.page_favorites = PageFavoriteList()
        self.page_favorites.itemClicked.connect(self._activate_page_favorite)
        self.page_favorites.itemDoubleClicked.connect(self._activate_page_favorite)
        self.page_favorites.favorites_reordered.connect(self.page_favorites_reordered.emit)
        layout.addWidget(self.page_favorites)

        layout.addWidget(QLabel("Editor-Zeilenfavoriten"))
        self.line_favorites = QListWidget()
        self.line_favorites.setMaximumHeight(100)
        self.line_favorites.setToolTip(
            "Zeilen-Lesezeichen — Klick springt; Doppelklick / Rechtsklick → Label bearbeiten"
        )
        self.line_favorites.setContextMenuPolicy(Qt.CustomContextMenu)
        self.line_favorites.customContextMenuRequested.connect(self._line_fav_context_menu)
        self.line_favorites.itemClicked.connect(self._activate_line_favorite)
        self.line_favorites.itemDoubleClicked.connect(self._edit_line_favorite_label)
        layout.addWidget(self.line_favorites)

        layout.addWidget(QLabel("Annotationen (gruppiert nach Seite)"))
        self.ann_filter = QComboBox()
        self.ann_filter.setToolTip("Nach Annotationstyp filtern")
        self.ann_filter.addItem("Alle Typen", "")
        self.ann_filter.currentIndexChanged.connect(self._on_ann_filter_changed)
        layout.addWidget(self.ann_filter)
        self.ann_current_page = QCheckBox("Nur aktuelle Seite")
        self.ann_current_page.setToolTip(
            "Annotationsliste auf die aktuelle PDF-Seite beschränken"
        )
        self.ann_current_page.toggled.connect(self._on_ann_current_page_toggled)
        layout.addWidget(self.ann_current_page)
        self.ann_tag_filter = QListWidget()
        self.ann_tag_filter.setToolTip(
            "Tag-Filter Multi-Select: mehrere Tags wählen (ODER); leer = alle Tags"
        )
        self.ann_tag_filter.setSelectionMode(QAbstractItemView.MultiSelection)
        self.ann_tag_filter.setMaximumHeight(72)
        self.ann_tag_filter.itemSelectionChanged.connect(self._on_ann_tag_filter_changed)
        layout.addWidget(self.ann_tag_filter)
        layout.addWidget(QLabel("Tag-Cloud (häufigste)"))
        self.ann_tag_cloud = QWidget()
        self.ann_tag_cloud.setObjectName("annTagCloud")
        self.ann_tag_cloud.setToolTip(
            "Häufigste Tags — Klick setzt Filter (exklusiv); Ctrl+Klick Multi-Select (ODER); "
            "erneut Klick auf allein aktiven Tag löscht Filter; Rechtsklick → Tag umbenennen (global)"
        )
        self.ann_tag_cloud_layout = QHBoxLayout(self.ann_tag_cloud)
        self.ann_tag_cloud_layout.setContentsMargins(0, 2, 0, 2)
        self.ann_tag_cloud_layout.setSpacing(4)
        layout.addWidget(self.ann_tag_cloud)
        self.ann_search = QLineEdit()
        self.ann_search.setPlaceholderText("Annotationen suchen… Tag-Vorschläge")
        self.ann_search.setClearButtonEnabled(True)
        self.ann_search.setToolTip(
            "Filtert die Annotationsliste nach Text/Tags (optional Regex); Tag-Autocomplete"
        )
        self.ann_search.textChanged.connect(self._on_ann_search_changed)
        self._ann_tag_completer_model = QStringListModel(self)
        self._ann_tag_completer = QCompleter(self._ann_tag_completer_model, self)
        self._ann_tag_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._ann_tag_completer.setFilterMode(Qt.MatchContains)
        self._ann_tag_completer.setCompletionMode(QCompleter.PopupCompletion)
        self.ann_search.setCompleter(self._ann_tag_completer)
        search_row = QHBoxLayout()
        search_row.addWidget(self.ann_search, 1)
        self.ann_search_regex = QCheckBox("Regex")
        self.ann_search_regex.setToolTip("Suchbegriff als regulären Ausdruck (case-insensitive)")
        self.ann_search_regex.toggled.connect(self._on_ann_search_regex_toggled)
        search_row.addWidget(self.ann_search_regex)
        layout.addLayout(search_row)
        self.annotations = QListWidget()
        self.annotations.setMaximumHeight(160)
        self.annotations.setToolTip(
            "Gruppiert nach Seite — Klick → Annotation; Rechtsklick auf Gruppe → umbenennen/Farbe"
        )
        self.annotations.itemClicked.connect(self._activate_annotation)
        self.annotations.setContextMenuPolicy(Qt.CustomContextMenu)
        self.annotations.customContextMenuRequested.connect(self._ann_context_menu)
        layout.addWidget(self.annotations)

        layout.addStretch(1)
        self.ann_stats_label = QLabel("Ann.: —")
        self.ann_stats_label.setWordWrap(True)
        self.ann_stats_label.setObjectName("annStatsFooter")
        self.ann_stats_label.setStyleSheet(
            "QLabel#annStatsFooter { color: #666; font-size: 11px; padding-top: 4px; }"
        )
        self.ann_stats_label.setToolTip("Anzahl Annotationen je Typ (unabhängig vom Filter)")
        layout.addWidget(self.ann_stats_label)
        self.ann_color_stats = QWidget()
        self.ann_color_stats.setObjectName("annColorStats")
        self.ann_color_stats.setToolTip(
            "Farben-Statistik — Klick filtert die Annotationsliste nach Farbe"
        )
        self.ann_color_layout = QHBoxLayout(self.ann_color_stats)
        self.ann_color_layout.setContentsMargins(0, 2, 0, 0)
        self.ann_color_layout.setSpacing(4)
        layout.addWidget(self.ann_color_stats)

        self.setMinimumWidth(240)
        self._fulltext_mode = False
        self._pdf_fulltext_mode = False
        self._search_hit_index: int = -1
        self._search_hit_total: int = 0
        self._ann_all_lines: list[str] = []
        self._ann_all_payloads: list = []
        self._ann_filter_updating = False
        self._ann_search_query = ""
        self._ann_search_regex = False
        self._ann_color_filter = ""
        self._ann_tag_filter: list[str] = []
        self._ann_current_page_index: int | None = None
        self._ann_filter_current_page = False
        self._ann_tag_updating = False
        self._ann_page_groups: dict[int, dict] = {}

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
        self._pdf_fulltext_mode = False
        self.search_requested.emit(self.search_text())

    def _emit_fulltext(self):
        self._fulltext_mode = True
        self._pdf_fulltext_mode = False
        self.search_requested.emit(self.search_text())

    def _emit_pdf_fulltext(self):
        self._fulltext_mode = True
        self._pdf_fulltext_mode = True
        self.search_requested.emit(self.search_text())

    @property
    def fulltext_mode(self) -> bool:
        return self._fulltext_mode

    @property
    def pdf_fulltext_mode(self) -> bool:
        return bool(self._pdf_fulltext_mode)

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
        # Trefferindex für Weiter/Zurück mit Klick synchronisieren
        if isinstance(payload, tuple) and len(payload) >= 2 and payload[0] not in (
            None,
            "",
            "__search__",
        ):
            nav = self.navigable_mark_indices()
            if row in nav:
                self._search_hit_index = nav.index(row)
                self._search_hit_total = len(nav)
                self._refresh_search_hits_label()
            path, page = payload[0], payload[1]
            self.fulltext_hit_activated.emit(str(path), page)
            return
        if isinstance(payload, tuple) and len(payload) >= 2:
            path, page = payload[0], payload[1]
            self.fulltext_hit_activated.emit(str(path), page)
            return
        self.mark_activated.emit(row)

    def _activate_annotation(self, item: QListWidgetItem):
        payload = item.data(256)
        if payload is not None:
            self.annotation_activated.emit(payload)

    def _activate_outline(self, item: QTreeWidgetItem, _column: int = 0):
        if item is None or item.isDisabled():
            return
        page = item.data(0, Qt.UserRole)
        if page is None:
            # Kein auflösbares Ziel — Signal mit -1 für Statusmeldung in MainWindow
            self.outline_activated.emit(-1)
            return
        try:
            self.outline_activated.emit(int(page))
        except (TypeError, ValueError):
            self.outline_activated.emit(-1)

    def _activate_page_favorite(self, item: QListWidgetItem):
        if item is None:
            return
        page = item.data(Qt.UserRole)
        if page is None:
            page = item.data(256)
        if page is not None:
            try:
                self.page_favorite_activated.emit(int(page))
            except (TypeError, ValueError):
                pass

    def set_page_favorites(
        self,
        pages: list[int] | None,
        *,
        labels: list[str] | None = None,
        current: int | None = None,
    ):
        """Nummerierte Favoriten-Seiten in der Sidebar (1. Seite N …); Drag zum Umsortieren."""
        self.page_favorites.clear()
        pages = list(pages or [])
        enable_drag = bool(pages)
        if hasattr(self.page_favorites, "set_reorder_enabled"):
            self.page_favorites.set_reorder_enabled(enable_drag)
        for i, p in enumerate(pages):
            try:
                idx = int(p)
            except (TypeError, ValueError):
                continue
            label = ""
            if labels is not None and i < len(labels) and labels[i]:
                label = str(labels[i])
            text = f"{i + 1}. Seite {idx + 1}"
            if label:
                text = f"{text} ({label})"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, idx)
            item.setData(256, idx)
            item.setToolTip(f"Favorit #{i + 1} → Seite {idx + 1} — ziehen zum Umsortieren")
            self.page_favorites.addItem(item)
        if not pages:
            empty = QListWidgetItem("(keine — ★ markieren)")
            empty.setFlags(Qt.NoItemFlags)
            self.page_favorites.addItem(empty)
            return
        if current is not None:
            for row in range(self.page_favorites.count()):
                it = self.page_favorites.item(row)
                if it and it.data(Qt.UserRole) == int(current):
                    self.page_favorites.setCurrentRow(row)
                    break

    def clear_page_favorites(self):
        self.set_page_favorites([])

    def _activate_line_favorite(self, item: QListWidgetItem):
        if item is None:
            return
        line = item.data(Qt.UserRole)
        if line is None:
            line = item.data(256)
        if line is not None:
            try:
                self.line_favorite_activated.emit(int(line))
            except (TypeError, ValueError):
                pass

    def _edit_line_favorite_label(self, item: QListWidgetItem):
        if item is None or not (item.flags() & Qt.ItemIsEnabled):
            return
        line = item.data(Qt.UserRole)
        if line is None:
            line = item.data(256)
        if line is None:
            return
        try:
            self.line_favorite_label_edit.emit(int(line))
        except (TypeError, ValueError):
            pass

    def _line_fav_context_menu(self, pos):
        item = self.line_favorites.itemAt(pos)
        if item is None or not (item.flags() & Qt.ItemIsEnabled):
            return
        menu = QMenu(self)
        act = menu.addAction("Label bearbeiten…")
        chosen = menu.exec(self.line_favorites.mapToGlobal(pos))
        if chosen is act:
            self._edit_line_favorite_label(item)

    def set_line_favorites(
        self,
        lines: list[int] | list[tuple[int, str]] | None,
        *,
        current: int | None = None,
        labels: list[str] | None = None,
    ):
        """
        Alle Editor-Zeilenfavoriten als nummerierte Liste (1-basierte Zeilen).
        lines: [Zeile, …] oder [(Zeile, Label), …]; labels optional parallel.
        """
        self.line_favorites.clear()
        entries: list[tuple[int, str]] = []
        for i, ln in enumerate(list(lines or [])):
            label = ""
            if isinstance(ln, (tuple, list)) and len(ln) >= 1:
                try:
                    line = int(ln[0])
                except (TypeError, ValueError):
                    continue
                if len(ln) >= 2 and ln[1]:
                    label = str(ln[1]).strip()
            else:
                try:
                    line = int(ln)
                except (TypeError, ValueError):
                    continue
            if line < 1:
                continue
            if not label and labels is not None and i < len(labels) and labels[i]:
                label = str(labels[i]).strip()
            entries.append((line, label))
        for i, (line, label) in enumerate(entries):
            text = f"{i + 1}. Zeile {line}"
            if label:
                text = f"{text} — {label}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, line)
            item.setData(256, line)
            tip = f"Zeilenfavorit #{i + 1} → Zeile {line}"
            if label:
                tip = f"{tip} ({label})"
            tip += " — Doppelklick/Rechtsklick: Label"
            item.setToolTip(tip)
            self.line_favorites.addItem(item)
        if not entries:
            empty = QListWidgetItem("(keine — Ctrl+F2)")
            empty.setFlags(Qt.NoItemFlags)
            self.line_favorites.addItem(empty)
            return
        if current is not None:
            for row in range(self.line_favorites.count()):
                it = self.line_favorites.item(row)
                if it and it.data(Qt.UserRole) == int(current):
                    self.line_favorites.setCurrentRow(row)
                    break

    def clear_line_favorites(self):
        self.set_line_favorites([])

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

    def document_paths(self) -> list[str]:
        """Aktuelle Dokument-Reihenfolge (Session-Tabs), absolute Pfade."""
        out: list[str] = []
        for i in range(self.files.count()):
            it = self.files.item(i)
            if it is None:
                continue
            p = it.data(256) or it.data(Qt.UserRole) or it.toolTip() or it.text()
            if p and Path(str(p)).is_file():
                out.append(str(Path(str(p))))
        return out

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

    def remove_document(self, path: str) -> bool:
        """Entfernt Pfad aus der Dokumentliste. True wenn gefunden."""
        target = str(Path(path))
        for i in range(self.files.count()):
            it = self.files.item(i)
            if not it:
                continue
            p = it.data(256) or it.toolTip() or it.text()
            if p and str(Path(str(p))) == target:
                self.files.takeItem(i)
                return True
        return False

    def document_paths(self) -> list[str]:
        out: list[str] = []
        for i in range(self.files.count()):
            it = self.files.item(i)
            if it and it.data(256):
                out.append(str(it.data(256)))
        return out

    def clear_thumbs(self):
        self.thumbs.clear()
        self._thumb_token = getattr(self, "_thumb_token", 0) + 1

    def prepare_lazy_thumbs(self, page_count: int, *, current: int = 0, max_pages: int = 40):
        """Platzhalter-Einträge ohne Render — Icons kommen per update_thumb."""
        self.thumbs.clear()
        self._thumb_token = getattr(self, "_thumb_token", 0) + 1
        w, h = pdf_thumbnail_icon_size()
        self.thumbs.apply_icon_size(w, h)
        n = max(0, min(int(page_count), int(max_pages)))
        for i in range(n):
            item = QListWidgetItem(f"S. {i + 1}")
            item.setData(Qt.UserRole, i)
            item.setToolTip(f"Seite {i + 1} — laden…")
            # hellgraues Platzhalter-Icon
            pm = QPixmap(w, h)
            pm.fill(Qt.lightGray)
            item.setIcon(QIcon(pm))
            self.thumbs.addItem(item)
        self.select_thumb(current)
        return self._thumb_token

    def update_thumb(self, page_index: int, image, *, token: int | None = None) -> bool:
        """Setzt Icon für eine Seite; ignoriert veraltete Lazy-Batches (token)."""
        if token is not None and token != getattr(self, "_thumb_token", None):
            return False
        if page_index < 0 or page_index >= self.thumbs.count():
            return False
        item = self.thumbs.item(page_index)
        if item is None:
            return False
        pm = self._to_pixmap(image)
        if not pm.isNull():
            item.setIcon(QIcon(pm))
        item.setToolTip(f"Seite {page_index + 1} — ziehen zum Neuordnen")
        return True

    def set_page_thumbs(self, images: list, *, current: int = 0):
        """images: Liste von PIL.Image oder QPixmap/QImage."""
        self.thumbs.clear()
        self._thumb_token = getattr(self, "_thumb_token", 0) + 1
        w, h = pdf_thumbnail_icon_size()
        self.thumbs.apply_icon_size(w, h)
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
        w, h = pdf_thumbnail_icon_size()
        if isinstance(img, QPixmap):
            return img.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        if isinstance(img, QImage):
            return QPixmap.fromImage(img).scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        try:
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            data = img.tobytes("raw", "RGBA")
            qimg = QImage(data, img.width, img.height, QImage.Format_RGBA8888)
            return QPixmap.fromImage(qimg.copy()).scaled(
                w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation
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
                if node.page_index is None:
                    twi.setToolTip(0, "Kein Seiten-Ziel (Destination nicht auflösbar)")
                else:
                    twi.setToolTip(0, f"Doppelklick → Seite {node.page_index + 1}")
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

    def annotation_filter_color(self) -> str:
        """Aktueller Farben-Filter (#RRGGBB) oder '' für alle."""
        return getattr(self, "_ann_color_filter", "") or ""

    def annotation_filter_current_page(self) -> bool:
        """True wenn nur Annotationen der aktuellen Seite gezeigt werden."""
        return bool(getattr(self, "_ann_filter_current_page", False))

    def annotation_filter_tags(self) -> list[str]:
        """Aktuelle Tag-Filter (Multi-Select) oder [] für alle."""
        tags = getattr(self, "_ann_tag_filter", None)
        if isinstance(tags, list):
            return [str(t).strip() for t in tags if str(t).strip()]
        if isinstance(tags, str) and tags.strip():
            return [tags.strip()]
        return []

    def annotation_filter_tag(self) -> str:
        """Erster Tag-Filter oder '' für alle (Kompatibilität)."""
        tags = self.annotation_filter_tags()
        return tags[0] if tags else ""

    def set_annotation_tag_filter(self, tag: str | list[str] | None):
        """Tag-Filter setzen; leer / None = alle. str oder list (Multi-Select)."""
        if tag is None:
            want: list[str] = []
        elif isinstance(tag, (list, tuple, set)):
            want = []
            seen: set[str] = set()
            for t in tag:
                s = str(t).strip()
                if not s:
                    continue
                key = s.casefold()
                if key in seen:
                    continue
                seen.add(key)
                want.append(s)
        else:
            s = str(tag).strip()
            want = [s] if s else []
        if want == self.annotation_filter_tags():
            return
        self._ann_tag_filter = list(want)
        if hasattr(self, "ann_tag_filter"):
            self._ann_tag_updating = True
            self.ann_tag_filter.blockSignals(True)
            # Fehlende Tags temporär ergänzen
            existing = {
                (self.ann_tag_filter.item(i).data(Qt.UserRole) or "").casefold()
                for i in range(self.ann_tag_filter.count())
            }
            for t in want:
                if t.casefold() not in existing:
                    item = QListWidgetItem(t)
                    item.setData(Qt.UserRole, t)
                    self.ann_tag_filter.addItem(item)
            want_cf = {t.casefold() for t in want}
            for i in range(self.ann_tag_filter.count()):
                item = self.ann_tag_filter.item(i)
                data = str(item.data(Qt.UserRole) or "")
                item.setSelected(bool(data) and data.casefold() in want_cf)
            self.ann_tag_filter.blockSignals(False)
            self._ann_tag_updating = False
        self._apply_annotation_filter()
        self._update_ann_tag_cloud(getattr(self, "_ann_all_payloads", None))
        self.annotation_tag_filter_changed.emit(self.annotation_filter_tags())

    def _on_ann_tag_filter_changed(self, *_args):
        if getattr(self, "_ann_tag_updating", False):
            return
        selected: list[str] = []
        for item in self.ann_tag_filter.selectedItems():
            data = item.data(Qt.UserRole)
            s = str(data).strip() if data else item.text().strip()
            if s:
                selected.append(s)
        self._ann_tag_filter = selected
        self._apply_annotation_filter()
        self._update_ann_tag_cloud(getattr(self, "_ann_all_payloads", None))
        self.annotation_tag_filter_changed.emit(self.annotation_filter_tags())

    def set_annotation_current_page(self, page_index: int | None):
        """Aktuelle PDF-Seite für den Seitenfilter setzen (0-basiert)."""
        if page_index is None:
            self._ann_current_page_index = None
        else:
            try:
                self._ann_current_page_index = int(page_index)
            except (TypeError, ValueError):
                self._ann_current_page_index = None
        if self.annotation_filter_current_page():
            self._apply_annotation_filter()

    def set_annotation_filter_current_page(self, enabled: bool):
        """Filter ‚nur aktuelle Seite‘ ein-/ausschalten."""
        want = bool(enabled)
        if want == self.annotation_filter_current_page():
            if hasattr(self, "ann_current_page"):
                self.ann_current_page.blockSignals(True)
                self.ann_current_page.setChecked(want)
                self.ann_current_page.blockSignals(False)
            return
        self._ann_filter_current_page = want
        if hasattr(self, "ann_current_page"):
            self.ann_current_page.blockSignals(True)
            self.ann_current_page.setChecked(want)
            self.ann_current_page.blockSignals(False)
        self._apply_annotation_filter()
        self.annotation_page_filter_changed.emit(want)

    def _on_ann_current_page_toggled(self, checked: bool):
        self._ann_filter_current_page = bool(checked)
        self._apply_annotation_filter()
        self.annotation_page_filter_changed.emit(bool(checked))

    def set_annotation_color_filter(self, color: str | None):
        """Farben-Filter setzen; leerer String / None = alle Farben."""
        want = normalize_ann_color(color) if color else ""
        if want == self.annotation_filter_color():
            # erneuter Klick auf aktive Farbe → Filter aufheben
            if want:
                want = ""
            else:
                return
        self._ann_color_filter = want
        self._apply_annotation_filter()
        self.annotation_color_filter_changed.emit(self._ann_color_filter)

    def clear_annotation_color_filter(self):
        if not self.annotation_filter_color():
            return
        self._ann_color_filter = ""
        self._apply_annotation_filter()
        self.annotation_color_filter_changed.emit("")

    def _on_ann_filter_changed(self, _index: int = 0):
        if self._ann_filter_updating:
            return
        self._apply_annotation_filter()
        self.annotation_filter_changed.emit(self.annotation_filter_type())

    def _on_ann_search_changed(self, text: str = ""):
        self._ann_search_query = (text or "").strip()
        if not self.annotation_search_regex():
            self._ann_search_query = self._ann_search_query.lower()
        self._apply_annotation_filter()

    def _on_ann_search_regex_toggled(self, checked: bool = False):
        self._ann_search_regex = bool(checked)
        # Query-Normalisierung anpassen
        raw = self.annotation_search_text()
        self._ann_search_query = raw if self._ann_search_regex else raw.lower()
        self._apply_annotation_filter()

    def annotation_search_regex(self) -> bool:
        if hasattr(self, "ann_search_regex"):
            return bool(self.ann_search_regex.isChecked())
        return bool(getattr(self, "_ann_search_regex", False))

    def set_annotation_search_regex(self, enabled: bool) -> None:
        want = bool(enabled)
        self._ann_search_regex = want
        if hasattr(self, "ann_search_regex"):
            self.ann_search_regex.blockSignals(True)
            self.ann_search_regex.setChecked(want)
            self.ann_search_regex.blockSignals(False)
        raw = self.annotation_search_text()
        self._ann_search_query = raw if want else raw.lower()
        self._apply_annotation_filter()

    def annotation_search_text(self) -> str:
        return getattr(self, "ann_search", None) and self.ann_search.text().strip() or ""

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
        for t in types:
            self.ann_filter.addItem(ANN_TYPE_LABELS.get(t, t), t)
        idx = self.ann_filter.findData(current)
        self.ann_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self.ann_filter.blockSignals(False)
        self._ann_filter_updating = False
        self._sync_ann_tag_filter_options(payloads)

    def _sync_ann_tag_filter_options(self, payloads: list | None):
        """Tag-Liste (Multi-Select) aus vorkommenden Tags (Auswahl behalten)."""
        if not hasattr(self, "ann_tag_filter"):
            return
        current = {t.casefold() for t in self.annotation_filter_tags()}
        tags: list[str] = []
        seen: set[str] = set()
        for p in payloads or []:
            raw = getattr(p, "tags", None) if p is not None else None
            if not raw:
                continue
            for t in raw if isinstance(raw, (list, tuple)) else [raw]:
                s = str(t).strip()
                if not s:
                    continue
                key = s.casefold()
                if key in seen:
                    continue
                seen.add(key)
                tags.append(s)
        tags.sort(key=lambda x: x.casefold())
        if hasattr(self, "_ann_tag_completer_model"):
            self._ann_tag_completer_model.setStringList(tags)
        self._ann_tag_updating = True
        self.ann_tag_filter.blockSignals(True)
        self.ann_tag_filter.clear()
        kept: list[str] = []
        for t in tags:
            item = QListWidgetItem(t)
            item.setData(Qt.UserRole, t)
            self.ann_tag_filter.addItem(item)
            if t.casefold() in current:
                item.setSelected(True)
                kept.append(t)
        self._ann_tag_filter = kept
        self.ann_tag_filter.blockSignals(False)
        self._ann_tag_updating = False
        self._update_ann_tag_cloud(payloads)

    def _clear_tag_cloud_buttons(self) -> None:
        layout = getattr(self, "ann_tag_cloud_layout", None)
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _on_tag_cloud_clicked(self, tag: str):
        """Tag-Cloud-Klick: Filter setzen (exklusiv); Ctrl+Klick = Multi-Select umschalten."""
        from PySide6.QtWidgets import QApplication

        current = list(self.annotation_filter_tags())
        cf = tag.casefold()
        mods = QApplication.keyboardModifiers()
        if mods & Qt.ControlModifier:
            # Multi-Select: Tag umschalten
            if any(t.casefold() == cf for t in current):
                nxt = [t for t in current if t.casefold() != cf]
            else:
                nxt = current + [tag]
        else:
            # Exklusiv: Filter auf diesen Tag setzen; erneuter Klick löscht
            if len(current) == 1 and current[0].casefold() == cf:
                nxt = []
            else:
                nxt = [tag]
        self.set_annotation_tag_filter(nxt)

    def _on_tag_cloud_context_menu(self, tag: str, pos) -> None:
        """Rechtsklick auf Tag-Cloud-Chip: global umbenennen."""
        from PySide6.QtWidgets import QInputDialog

        menu = QMenu(self)
        act = menu.addAction(f"Tag „{tag}“ umbenennen…")
        chosen = menu.exec(pos)
        if chosen is not act:
            return
        text, ok = QInputDialog.getText(
            self,
            "Tag umbenennen",
            f"Neuer Name für Tag „{tag}“ (global in diesem Dokument):",
            text=tag,
        )
        if not ok:
            return
        new_tag = str(text or "").strip()
        if not new_tag or new_tag.casefold() == tag.casefold() and new_tag == tag:
            return
        self.annotation_tag_rename_requested.emit(tag, new_tag)

    def _update_ann_tag_cloud(self, payloads: list | None):
        """Häufigste Tags als klickbare Chips (max. 10)."""
        if not hasattr(self, "ann_tag_cloud_layout"):
            return
        counts: dict[str, int] = {}
        labels: dict[str, str] = {}
        for p in payloads or []:
            raw = getattr(p, "tags", None) if p is not None else None
            if not raw:
                continue
            for t in raw if isinstance(raw, (list, tuple)) else [raw]:
                s = str(t).strip()
                if not s:
                    continue
                key = s.casefold()
                counts[key] = counts.get(key, 0) + 1
                labels.setdefault(key, s)
        self._clear_tag_cloud_buttons()
        if not counts:
            if hasattr(self, "ann_tag_cloud"):
                self.ann_tag_cloud.setVisible(False)
            return
        if hasattr(self, "ann_tag_cloud"):
            self.ann_tag_cloud.setVisible(True)
        active = {t.casefold() for t in self.annotation_filter_tags()}
        ranked = sorted(counts.keys(), key=lambda k: (-counts[k], labels[k].casefold()))[:10]
        for key in ranked:
            tag = labels[key]
            n = counts[key]
            btn = QToolButton()
            btn.setText(f"{tag} · {n}")
            btn.setToolTip(
                f"Tag „{tag}“ filtern ({n}×) — Klick setzt Filter; Ctrl+Klick Multi-Select; "
                f"Rechtsklick → umbenennen (global)"
            )
            btn.setCursor(Qt.PointingHandCursor)
            btn.setAutoRaise(True)
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            is_on = key in active
            border = "2px solid #1a5276" if is_on else "1px solid #999"
            bg = "#d4e6f1" if is_on else "#eee"
            btn.setStyleSheet(
                f"QToolButton {{ background: {bg}; border: {border}; border-radius: 3px; "
                f"padding: 1px 5px; font-size: 10px; }}"
            )
            btn.clicked.connect(lambda checked=False, t=tag: self._on_tag_cloud_clicked(t))
            btn.customContextMenuRequested.connect(
                lambda pos, t=tag, b=btn: self._on_tag_cloud_context_menu(
                    t, b.mapToGlobal(pos)
                )
            )
            self.ann_tag_cloud_layout.addWidget(btn)
        self.ann_tag_cloud_layout.addStretch(1)

    def _apply_annotation_filter(self):
        want = self.annotation_filter_type()
        want_color = self.annotation_filter_color()
        want_tags = {t.casefold() for t in self.annotation_filter_tags()}
        query = self._ann_search_query
        page_only = self.annotation_filter_current_page()
        current_page = getattr(self, "_ann_current_page_index", None)
        self.annotations.clear()
        # Gefilterte Paare sammeln, dann nach Seite gruppieren
        filtered: list[tuple[str, object | None]] = []
        for i, line in enumerate(self._ann_all_lines):
            payload = self._ann_all_payloads[i] if i < len(self._ann_all_payloads) else None
            if page_only and current_page is not None:
                page = -1
                if payload is not None and hasattr(payload, "page"):
                    try:
                        page = int(payload.page)
                    except (TypeError, ValueError):
                        page = -1
                if page != int(current_page):
                    continue
            if want:
                t = getattr(getattr(payload, "type", None), "value", None) or getattr(
                    payload, "type", None
                )
                if str(t) != want:
                    continue
            if want_color:
                c = normalize_ann_color(getattr(payload, "color", None) if payload else None)
                if c != want_color:
                    continue
            if want_tags:
                tags = getattr(payload, "tags", None) if payload is not None else None
                tag_list = []
                if isinstance(tags, (list, tuple)):
                    tag_list = [str(x).strip() for x in tags if str(x).strip()]
                elif tags:
                    tag_list = [str(tags).strip()]
                ann_cf = {t.casefold() for t in tag_list}
                # ODER: Annotation behält mind. einen der gewählten Tags
                if not (want_tags & ann_cf):
                    continue
            if query:
                hay = line.lower()
                extra = ""
                type_label = ""
                tags_hay = ""
                if payload is not None:
                    extra = str(getattr(payload, "text", "") or "").lower()
                    t = getattr(getattr(payload, "type", None), "value", None) or getattr(
                        payload, "type", None
                    )
                    type_label = ANN_TYPE_LABELS.get(str(t), str(t or "")).lower()
                    type_val = str(t or "").lower()
                    color_val = normalize_ann_color(getattr(payload, "color", None)).lower()
                    tags_raw = getattr(payload, "tags", None) or []
                    if isinstance(tags_raw, (list, tuple)):
                        tags_hay = " ".join(str(x) for x in tags_raw).lower()
                    else:
                        tags_hay = str(tags_raw).lower()
                else:
                    type_val = ""
                    color_val = ""
                fields = (hay, extra, type_label, type_val, color_val, tags_hay)
                if self.annotation_search_regex():
                    import re

                    try:
                        rx = re.compile(query, re.IGNORECASE)
                    except re.error:
                        # Ungültiges Regex → kein Treffer (Filter leer)
                        continue
                    if not any(rx.search(f or "") for f in fields):
                        continue
                elif (
                    query not in hay
                    and query not in extra
                    and query not in type_label
                    and query not in type_val
                    and query not in color_val
                    and query not in tags_hay
                ):
                    continue
            filtered.append((line, payload))

        # Nach Seite gruppieren (None/fehlend → Gruppe -1)
        by_page: dict[int, list[tuple[str, object | None]]] = {}
        for line, payload in filtered:
            page = -1
            if payload is not None and hasattr(payload, "page"):
                try:
                    page = int(payload.page)
                except (TypeError, ValueError):
                    page = -1
            by_page.setdefault(page, []).append((line, payload))

        for page in sorted(by_page.keys()):
            items = by_page[page]
            group_meta = {}
            if page >= 0:
                group_meta = (getattr(self, "_ann_page_groups", None) or {}).get(page) or {}
            custom_title = str(group_meta.get("title") or "").strip()
            group_color = normalize_ann_color(group_meta.get("color"))
            if page < 0:
                header_txt = "Ohne Seite"
            elif custom_title:
                header_txt = f"{custom_title} (S. {page + 1}, {len(items)})"
            else:
                header_txt = f"Seite {page + 1} ({len(items)})"
            header = QListWidgetItem(header_txt)
            header.setFlags(Qt.ItemIsEnabled)  # nicht auswählbar
            font = header.font()
            font.setBold(True)
            header.setFont(font)
            header.setData(256, None)
            header.setData(Qt.UserRole + 2, "group")
            header.setData(Qt.UserRole + 3, page)
            if group_color:
                qc = QColor(group_color)
                if qc.isValid():
                    header.setBackground(QBrush(qc))
                    fg = QColor("#000000") if qc.lightness() > 140 else QColor("#FFFFFF")
                    header.setForeground(QBrush(fg))
            self.annotations.addItem(header)
            for line, payload in items:
                item = QListWidgetItem(f"  {line}")
                if payload is not None:
                    item.setData(256, payload)
                self.annotations.addItem(item)
        self._update_ann_stats()

    def _ann_context_menu(self, pos) -> None:
        item = self.annotations.itemAt(pos)
        if item is None:
            return
        if item.data(Qt.UserRole + 2) != "group":
            return
        page = item.data(Qt.UserRole + 3)
        try:
            page_i = int(page)
        except (TypeError, ValueError):
            return
        if page_i < 0:
            return
        menu = QMenu(self)
        act = menu.addAction("Gruppe umbenennen / Farbe…")
        chosen = menu.exec(self.annotations.mapToGlobal(pos))
        if chosen is act:
            self.annotation_group_edit_requested.emit(page_i)

    def _clear_color_stats_buttons(self) -> None:
        layout = getattr(self, "ann_color_layout", None)
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _on_color_chip_clicked(self, color: str):
        self.set_annotation_color_filter(color)

    def _update_ann_stats(self) -> None:
        """Footer: Anzahl je Typ + klickbare Farben-Chips."""
        if not hasattr(self, "ann_stats_label"):
            return
        counts: dict[str, int] = {}
        color_counts: dict[str, int] = {}
        for payload in self._ann_all_payloads:
            if payload is None:
                continue
            t = getattr(getattr(payload, "type", None), "value", None) or getattr(
                payload, "type", None
            )
            key = str(t) if t else "?"
            counts[key] = counts.get(key, 0) + 1
            c = normalize_ann_color(getattr(payload, "color", None))
            if c:
                color_counts[c] = color_counts.get(c, 0) + 1
        total = sum(counts.values())
        active_color = self.annotation_filter_color()
        if total == 0:
            self.ann_stats_label.setText("Ann.: —")
            self._clear_color_stats_buttons()
            if hasattr(self, "ann_color_stats"):
                self.ann_color_stats.setVisible(False)
            return
        parts = [
            f"{ANN_TYPE_LABELS.get(k, k)} {counts[k]}"
            for k in sorted(counts.keys(), key=lambda x: (-counts[x], x))
        ]
        suffix = f" · Farbe {active_color}" if active_color else ""
        self.ann_stats_label.setText(f"Ann. {total}: " + " · ".join(parts) + suffix)

        self._clear_color_stats_buttons()
        if hasattr(self, "ann_color_stats"):
            self.ann_color_stats.setVisible(True)
        # Alle-Farben-Chip wenn Filter aktiv
        if active_color:
            btn_all = QToolButton()
            btn_all.setText("Alle")
            btn_all.setToolTip("Farben-Filter aufheben")
            btn_all.setAutoRaise(True)
            btn_all.clicked.connect(self.clear_annotation_color_filter)
            self.ann_color_layout.addWidget(btn_all)
        for color in sorted(color_counts.keys(), key=lambda x: (-color_counts[x], x)):
            n = color_counts[color]
            btn = QToolButton()
            btn.setText(str(n))
            btn.setToolTip(f"Nach Farbe {color} filtern ({n})")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setAutoRaise(True)
            btn.setMinimumSize(22, 18)
            active = color == active_color
            border = "2px solid #222" if active else "1px solid #888"
            # Kontrastschrift je nach Helligkeit
            qc = QColor(color)
            fg = "#000" if qc.lightness() > 140 else "#fff"
            btn.setStyleSheet(
                f"QToolButton {{ background: {color}; color: {fg}; border: {border}; "
                f"border-radius: 3px; padding: 1px 4px; font-size: 10px; }}"
            )
            btn.clicked.connect(lambda checked=False, c=color: self._on_color_chip_clicked(c))
            self.ann_color_layout.addWidget(btn)
        self.ann_color_layout.addStretch(1)

    def set_annotations(
        self,
        lines: list[str],
        payloads: list | None = None,
        *,
        page_groups: dict | None = None,
    ):
        self._ann_all_lines = list(lines)
        self._ann_all_payloads = list(payloads) if payloads else [None] * len(lines)
        groups: dict[int, dict] = {}
        if isinstance(page_groups, dict):
            for k, v in page_groups.items():
                try:
                    groups[int(k)] = dict(v) if isinstance(v, dict) else {}
                except (TypeError, ValueError):
                    continue
        self._ann_page_groups = groups
        self._sync_ann_filter_options(self._ann_all_payloads)
        self._apply_annotation_filter()

    def clear_annotations(self):
        self._ann_all_lines = []
        self._ann_all_payloads = []
        self._ann_page_groups = {}
        self._ann_search_query = ""
        self._ann_search_regex = False
        self._ann_color_filter = ""
        self._ann_tag_filter = []
        self._ann_filter_current_page = False
        self.annotations.clear()
        if hasattr(self, "ann_search"):
            self.ann_search.blockSignals(True)
            self.ann_search.clear()
            self.ann_search.blockSignals(False)
        if hasattr(self, "ann_search_regex"):
            self.ann_search_regex.blockSignals(True)
            self.ann_search_regex.setChecked(False)
            self.ann_search_regex.blockSignals(False)
        if hasattr(self, "ann_current_page"):
            self.ann_current_page.blockSignals(True)
            self.ann_current_page.setChecked(False)
            self.ann_current_page.blockSignals(False)
        if hasattr(self, "ann_tag_filter"):
            self._ann_tag_updating = True
            self.ann_tag_filter.blockSignals(True)
            self.ann_tag_filter.clear()
            self.ann_tag_filter.blockSignals(False)
            self._ann_tag_updating = False
        self._clear_tag_cloud_buttons()
        if hasattr(self, "ann_tag_cloud"):
            self.ann_tag_cloud.setVisible(False)
        if hasattr(self, "_ann_tag_completer_model"):
            self._ann_tag_completer_model.setStringList([])
        self._ann_filter_updating = True
        self.ann_filter.blockSignals(True)
        self.ann_filter.clear()
        self.ann_filter.addItem("Alle Typen", "")
        self.ann_filter.blockSignals(False)
        self._ann_filter_updating = False
        self._update_ann_stats()

    def set_marks(self, lines: list[str], payloads: list | None = None):
        self.marks.clear()
        for i, line in enumerate(lines):
            item = QListWidgetItem(line)
            if payloads and i < len(payloads):
                item.setData(256, payloads[i])
            self.marks.addItem(item)
        # Navigierbare Doc-Treffer = Einträge mit (path, page[, query])-Payload
        nav = 0
        if payloads:
            for p in payloads:
                if isinstance(p, tuple) and len(p) >= 2 and p[0] not in (None, "", "__search__"):
                    nav += 1
        self._search_hit_index = -1
        if nav > 0:
            self._search_hit_total = nav
        elif lines:
            self._search_hit_total = len(lines)
        else:
            self._search_hit_total = 0
        self._refresh_search_hits_label()

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

    def set_search_hit_status(self, current: int, total: int) -> None:
        """Trefferanzeige setzen (current 1-basiert oder 0; total >= 0)."""
        self._search_hit_total = max(0, int(total))
        if self._search_hit_total <= 0:
            self._search_hit_index = -1
        else:
            cur = int(current)
            if cur <= 0:
                self._search_hit_index = -1
            else:
                self._search_hit_index = max(0, min(cur - 1, self._search_hit_total - 1))
        self._refresh_search_hits_label()

    def clear_search_hit_status(self) -> None:
        self._search_hit_index = -1
        self._search_hit_total = 0
        self._refresh_search_hits_label()

    def _refresh_search_hits_label(self) -> None:
        lbl = getattr(self, "search_hits_label", None)
        if lbl is None:
            return
        total = int(getattr(self, "_search_hit_total", 0) or 0)
        idx = int(getattr(self, "_search_hit_index", -1))
        if total <= 0:
            lbl.setText("")
            return
        if idx < 0:
            lbl.setText(f"{total} Treffer")
        else:
            lbl.setText(f"Treffer {idx + 1}/{total}")

    def navigable_mark_indices(self) -> list[int]:
        """Indizes in der Markierungsliste mit Doc-Pfad-Payload."""
        out: list[int] = []
        for i in range(self.marks.count()):
            item = self.marks.item(i)
            if item is None:
                continue
            p = item.data(256)
            if isinstance(p, tuple) and len(p) >= 2 and p[0] not in (None, "", "__search__"):
                out.append(i)
        return out

    def advance_search_hit(self, *, delta: int = 1) -> tuple[int, object] | None:
        """
        Nächsten/vorherigen Doc-Treffer in der Markierungsliste wählen.
        Rückgabe: (listen_index, payload) oder None.
        """
        indices = self.navigable_mark_indices()
        if not indices:
            return None
        n = len(indices)
        self._search_hit_total = n
        cur = int(getattr(self, "_search_hit_index", -1))
        if cur < 0:
            pos = 0 if delta >= 0 else n - 1
        else:
            pos = (cur + int(delta)) % n
        self._search_hit_index = pos
        list_i = indices[pos]
        item = self.marks.item(list_i)
        if item is None:
            return None
        self.marks.setCurrentRow(list_i)
        self._refresh_search_hits_label()
        return list_i, item.data(256)
