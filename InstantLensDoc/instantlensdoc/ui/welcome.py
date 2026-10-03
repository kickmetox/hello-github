"""Willkommens-/Startseite wenn keine Dokument-Tabs offen sind — 1.0.4."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QKeyEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from instantlensdoc import __version__
from instantlensdoc.config import DISPLAY_NAME
from instantlensdoc.core import recent as recent_mod


class WelcomePage(QWidget):
    """Startseite: Recent-Liste + Live-Filter + Dokument öffnen / Leeres Text / Drag&Drop."""

    open_requested = Signal()
    new_text_requested = Signal()
    recent_activated = Signal(str)
    recent_remove_requested = Signal(str)
    clear_recent_requested = Signal()
    files_dropped = Signal(list)  # list[str] lokale Dateipfade

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._recent_entries: list[tuple[str, bool]] = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(48, 40, 48, 40)
        lay.setSpacing(12)

        title = QLabel(f"<h1>{DISPLAY_NAME}</h1>")
        title.setWordWrap(True)
        lay.addWidget(title)
        sub = QLabel(
            f"<p style='color:#555;'>Version {__version__} — Willkommen.<br>"
            "Kein Dokument geöffnet. Dateien per Drag &amp; Drop hierher ziehen, "
            "eine Aktion wählen oder einen Eintrag aus der Recent-Liste öffnen.</p>"
        )
        sub.setWordWrap(True)
        lay.addWidget(sub)

        btn_row = QHBoxLayout()
        self.btn_open = QPushButton("Dokument öffnen…")
        self.btn_open.setToolTip("Datei öffnen (PDF, Text, …)")
        self.btn_open.clicked.connect(self.open_requested.emit)
        btn_row.addWidget(self.btn_open)
        self.btn_empty = QPushButton("Leeres Text")
        self.btn_empty.setToolTip("Neues leeres Textdokument")
        self.btn_empty.clicked.connect(self.new_text_requested.emit)
        btn_row.addWidget(self.btn_empty)
        self.btn_clear_recent = QPushButton("Recent leeren")
        self.btn_clear_recent.setToolTip("Liste der zuletzt geöffneten Dateien leeren")
        self.btn_clear_recent.clicked.connect(self.clear_recent_requested.emit)
        btn_row.addWidget(self.btn_clear_recent)
        btn_row.addStretch(1)
        lay.addLayout(btn_row)

        lay.addWidget(QLabel("<b>Zuletzt geöffnet</b>"))
        self.recent_filter = QLineEdit()
        self.recent_filter.setPlaceholderText("Recent filtern…")
        self.recent_filter.setClearButtonEnabled(True)
        self.recent_filter.setToolTip(
            "Live-Filter über Dateiname/Pfad der Recent-Liste — 1.0.4"
        )
        self.recent_filter.textChanged.connect(self._apply_recent_filter)
        lay.addWidget(self.recent_filter)
        self.recent_list = QListWidget()
        self.recent_list.setMinimumHeight(180)
        self.recent_list.setToolTip(
            "Enter / Doppelklick öffnet; Entf entfernt den Eintrag; "
            "Rechtsklick: Entfernen / Ordner öffnen; Drag & Drop öffnet Dateien; "
            "Filter oben filtert live"
        )
        self.recent_list.setAcceptDrops(True)
        self.recent_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.recent_list.customContextMenuRequested.connect(self._recent_context_menu)
        # itemActivated: Enter/Return (+ Doppelklick) — 1.0.3
        self.recent_list.itemActivated.connect(self._on_recent_dbl)
        self.recent_list.installEventFilter(self)
        lay.addWidget(self.recent_list, 1)

        self.refresh_recent()

    def eventFilter(self, obj, event):  # noqa: N802
        """Delete entfernt Recent-Eintrag; Enter öffnet (Fallback) — 1.0.3."""
        if obj is self.recent_list and event.type() == QEvent.KeyPress:
            assert isinstance(event, QKeyEvent)
            key = event.key()
            item = self.recent_list.currentItem()
            if item is not None and key in (Qt.Key_Return, Qt.Key_Enter):
                self._on_recent_dbl(item)
                return True
            if item is not None and key in (Qt.Key_Delete, Qt.Key_Backspace):
                path = item.data(Qt.UserRole)
                if path:
                    self.recent_remove_requested.emit(str(path))
                    return True
        return super().eventFilter(obj, event)

    def refresh_recent(self) -> None:
        self._recent_entries = list(recent_mod.load_recent_entries())
        has_entries = bool(self._recent_entries)
        self.btn_clear_recent.setEnabled(has_entries)
        self.recent_filter.setEnabled(has_entries)
        self._apply_recent_filter()

    def _apply_recent_filter(self, _text: str | None = None) -> None:
        """Live-Filter der Recent-Liste nach Teilstring (Dateiname/Pfad) — 1.0.4."""
        self.recent_list.clear()
        entries = self._recent_entries
        if not entries:
            item = QListWidgetItem("(keine zuletzt geöffneten Dateien)")
            item.setFlags(Qt.NoItemFlags)
            self.recent_list.addItem(item)
            return
        needle = (self.recent_filter.text() or "").strip().casefold()
        shown = 0
        for path, exists in entries:
            hay = str(path).casefold()
            if needle and needle not in hay:
                continue
            label = str(path) if exists else f"{path} (fehlt)"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, str(path))
            item.setData(Qt.UserRole + 1, bool(exists))
            if not exists:
                item.setForeground(QColor("#888888"))
            self.recent_list.addItem(item)
            shown += 1
        if shown == 0:
            item = QListWidgetItem("(keine Treffer für Filter)")
            item.setFlags(Qt.NoItemFlags)
            self.recent_list.addItem(item)

    def _on_recent_dbl(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.UserRole)
        if not path:
            return
        if not Path(str(path)).is_file():
            return
        self.recent_activated.emit(str(path))

    def _recent_context_menu(self, pos) -> None:
        item = self.recent_list.itemAt(pos)
        if item is None:
            return
        path = item.data(Qt.UserRole)
        if not path:
            return
        menu = QMenu(self)
        act_remove = menu.addAction("Entfernen")
        act_folder = menu.addAction("Ordner öffnen")
        chosen = menu.exec(self.recent_list.mapToGlobal(pos))
        if chosen is act_remove:
            self.recent_remove_requested.emit(str(path))
        elif chosen is act_folder:
            self._open_containing_folder(str(path))

    def _open_containing_folder(self, path: str) -> None:
        p = Path(path)
        folder = p if p.is_dir() else p.parent
        if not folder.is_dir():
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _local_paths_from_mime(self, mime) -> list[str]:
        paths: list[str] = []
        if mime is None or not mime.hasUrls():
            return paths
        for url in mime.urls():
            if not url.isLocalFile():
                continue
            path = url.toLocalFile()
            if path:
                paths.append(path)
        return paths

    def dragEnterEvent(self, event) -> None:
        if self._local_paths_from_mime(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if self._local_paths_from_mime(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        paths = self._local_paths_from_mime(event.mimeData())
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
            return
        super().dropEvent(event)
