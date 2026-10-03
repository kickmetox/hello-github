"""Willkommens-/Startseite wenn keine Dokument-Tabs offen sind — 1.0.1."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
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
    """Startseite: Recent-Liste + Dokument öffnen / Leeres Text."""

    open_requested = Signal()
    new_text_requested = Signal()
    recent_activated = Signal(str)
    recent_remove_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(48, 40, 48, 40)
        lay.setSpacing(12)

        title = QLabel(f"<h1>{DISPLAY_NAME}</h1>")
        title.setWordWrap(True)
        lay.addWidget(title)
        sub = QLabel(
            f"<p style='color:#555;'>Version {__version__} — Willkommen.<br>"
            "Kein Dokument geöffnet. Wählen Sie eine Aktion oder einen Eintrag aus der Recent-Liste.</p>"
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
        btn_row.addStretch(1)
        lay.addLayout(btn_row)

        lay.addWidget(QLabel("<b>Zuletzt geöffnet</b>"))
        self.recent_list = QListWidget()
        self.recent_list.setMinimumHeight(180)
        self.recent_list.setToolTip(
            "Doppelklick öffnet den Eintrag; Rechtsklick: Entfernen / Ordner öffnen"
        )
        self.recent_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.recent_list.customContextMenuRequested.connect(self._recent_context_menu)
        self.recent_list.itemDoubleClicked.connect(self._on_recent_dbl)
        lay.addWidget(self.recent_list, 1)

        self.refresh_recent()

    def refresh_recent(self) -> None:
        self.recent_list.clear()
        entries = recent_mod.load_recent_entries()
        if not entries:
            item = QListWidgetItem("(keine zuletzt geöffneten Dateien)")
            item.setFlags(Qt.NoItemFlags)
            self.recent_list.addItem(item)
            return
        for path, exists in entries:
            label = str(path) if exists else f"{path} (fehlt)"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, str(path))
            item.setData(Qt.UserRole + 1, bool(exists))
            if not exists:
                item.setForeground(QColor("#888888"))
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
