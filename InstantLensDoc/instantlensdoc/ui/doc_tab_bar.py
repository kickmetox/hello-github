"""Horizontale Dokument-Tabs für offene Dateien — 2.6.19 (partiell)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QTabBar, QWidget, QHBoxLayout, QLabel


class DocumentTabBar(QWidget):
    """QTabBar über dem Viewer — synchron mit Sidebar-Dokumentliste."""

    tab_activated = Signal(str)  # path
    tab_close_requested = Signal(str)  # path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("documentTabBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            "#documentTabBar {"
            " background: #EEF1F5; border-bottom: 1px solid #C5CCD6;"
            "}"
            "QTabBar::tab {"
            " background: #E2E6EC; color: #243042; padding: 6px 12px;"
            " margin-right: 2px; border: 1px solid #C5CCD6;"
            " border-bottom: none; border-top-left-radius: 4px;"
            " border-top-right-radius: 4px;"
            "}"
            "QTabBar::tab:selected {"
            " background: #FFFFFF; font-weight: 600;"
            "}"
            "QTabBar::tab:hover { background: #F7F9FC; }"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 2, 6, 0)
        lay.setSpacing(6)
        self._hint = QLabel("Tabs")
        self._hint.setStyleSheet("color: #667; font-size: 11px; font-weight: 600;")
        self._hint.setToolTip(
            "Offene Dokumente als Tabs — Klick wechselt, × schließt — 2.6.19"
        )
        lay.addWidget(self._hint)
        self.tabs = QTabBar()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(False)
        self.tabs.setExpanding(False)
        self.tabs.setDrawBase(False)
        self.tabs.setElideMode(Qt.ElideMiddle)
        self.tabs.setUsesScrollButtons(True)
        self.tabs.currentChanged.connect(self._on_current_changed)
        self.tabs.tabCloseRequested.connect(self._on_close)
        lay.addWidget(self.tabs, 1)
        self._paths: list[str] = []
        self._syncing = False

    def set_documents(self, paths: list[str], active: str | None = None) -> None:
        """Tabs aus Pfadliste aufbauen; optional aktiven Tab setzen."""
        self._syncing = True
        try:
            while self.tabs.count():
                self.tabs.removeTab(0)
            self._paths = []
            for raw in paths or []:
                p = str(Path(raw)) if raw else ""
                if not p:
                    continue
                name = Path(p).name or p
                idx = self.tabs.addTab(name)
                self.tabs.setTabToolTip(idx, p)
                self.tabs.setTabData(idx, p)
                self._paths.append(p)
            if active and self._paths:
                key = str(Path(active))
                for i, p in enumerate(self._paths):
                    if str(Path(p)) == key:
                        self.tabs.setCurrentIndex(i)
                        break
            self.setVisible(bool(self._paths))
        finally:
            self._syncing = False

    def set_active_path(self, path: str | None) -> None:
        if not path or self._syncing:
            return
        key = str(Path(path))
        self._syncing = True
        try:
            for i, p in enumerate(self._paths):
                if str(Path(p)) == key:
                    self.tabs.setCurrentIndex(i)
                    break
        finally:
            self._syncing = False

    def _on_current_changed(self, index: int) -> None:
        if self._syncing or index < 0 or index >= len(self._paths):
            return
        self.tab_activated.emit(self._paths[index])

    def _on_close(self, index: int) -> None:
        if index < 0 or index >= len(self._paths):
            return
        self.tab_close_requested.emit(self._paths[index])
