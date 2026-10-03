"""Annotation-Suche: Volltext Sidecar-Notizen/Highlights über offene Docs — 1.4.0."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from instantlensdoc.core.ann_search import AnnSearchHit, search_annotations_in_paths


class AnnotationSearchDialog(QDialog):
    """Nicht-modale Trefferliste; Doppelklick → Dokument/Seite."""

    hit_activated = Signal(str, int, str)  # path, page_0based, ann_id

    def __init__(self, parent=None, *, paths: list[str] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Annotation-Suche (offene Docs)")
        self.resize(560, 420)
        self.setModal(False)
        self._paths = [str(p) for p in (paths or []) if p]
        self._hits: list[AnnSearchHit] = []

        root = QVBoxLayout(self)
        root.addWidget(
            QLabel(
                "Volltext über Sidecar-Notizen/Highlights/Tags aller offenen Docs — 1.4.0"
            )
        )

        row = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText("Suchbegriff…")
        self.query.returnPressed.connect(self._run_search)
        row.addWidget(self.query, 1)
        btn = QPushButton("Suchen")
        btn.clicked.connect(self._run_search)
        row.addWidget(btn)
        root.addLayout(row)

        self.list = QListWidget()
        self.list.itemActivated.connect(self._activate)
        self.list.itemDoubleClicked.connect(self._activate)
        root.addWidget(self.list, 1)

        self.status = QLabel("Bereit")
        root.addWidget(self.status)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def set_paths(self, paths: list[str]) -> None:
        self._paths = [str(p) for p in paths if p]

    def _run_search(self) -> None:
        q = self.query.text().strip()
        self.list.clear()
        if not q:
            self.status.setText("Leere Suche")
            return
        self._hits = search_annotations_in_paths(self._paths, q)
        for h in self._hits:
            name = Path(h.path).name
            text = f"{name} S.{h.page + 1} [{h.ann_type}] {h.snippet}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, h)
            item.setToolTip(f"{h.path}\n{h.text or h.tags}")
            self.list.addItem(item)
        self.status.setText(
            f"{len(self._hits)} Treffer in {len(self._paths)} Doc(s) — 1.4.0"
        )

    def _activate(self, item: QListWidgetItem | None = None) -> None:
        it = item or self.list.currentItem()
        if it is None:
            return
        h = it.data(Qt.UserRole)
        if not isinstance(h, AnnSearchHit):
            return
        self.hit_activated.emit(h.path, int(h.page), h.ann_id)
