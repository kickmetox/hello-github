"""Annotation-Suche: klickbare Treffer (Doc+Seite), Case/Regex — 1.4.1."""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
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
    """Nicht-modale Trefferliste; Klick → Dokument/Seite — 1.4.1."""

    hit_activated = Signal(str, int, str)  # path, page_0based, ann_id

    def __init__(self, parent=None, *, paths: list[str] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Annotation-Suche (offene Docs)")
        self.resize(580, 440)
        self.setModal(False)
        self._paths = [str(p) for p in (paths or []) if p]
        self._hits: list[AnnSearchHit] = []

        root = QVBoxLayout(self)
        root.addWidget(
            QLabel(
                "Volltext über Sidecar-Notizen/Highlights/Tags aller offenen Docs — "
                "Treffer klickbar (Doc+Seite) — 1.4.1"
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

        opts = QHBoxLayout()
        self.chk_case = QCheckBox("Aa")
        self.chk_case.setToolTip("Groß-/Kleinschreibung beachten — 1.4.1")
        self.chk_case.toggled.connect(lambda _: self._run_search())
        self.chk_regex = QCheckBox("Regex")
        self.chk_regex.setToolTip("Suchbegriff als regulärer Ausdruck — 1.4.1")
        self.chk_regex.toggled.connect(lambda _: self._run_search())
        opts.addWidget(self.chk_case)
        opts.addWidget(self.chk_regex)
        opts.addStretch()
        root.addLayout(opts)

        self.list = QListWidget()
        self.list.setToolTip(
            "Klick oder Enter: Dokument öffnen und zur Seite springen — 1.4.1"
        )
        # Klickbar: Einfachklick + Activate/Doppelklick — 1.4.1
        self.list.itemClicked.connect(self._activate)
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
        case_sensitive = self.chk_case.isChecked()
        use_regex = self.chk_regex.isChecked()
        if use_regex:
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                re.compile(q, flags)
            except re.error as e:
                self.status.setText(f"Ungültiges Regex: {e}")
                return
        self._hits = search_annotations_in_paths(
            self._paths,
            q,
            case_sensitive=case_sensitive,
            use_regex=use_regex,
        )
        for h in self._hits:
            name = Path(h.path).name
            text = f"{name}  ·  S.{h.page + 1}  [{h.ann_type}]  {h.snippet}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, h)
            item.setToolTip(
                f"{h.path}\nSeite {h.page + 1}\n{h.text or h.tags}\n"
                "Klick → Doc+Seite — 1.4.1"
            )
            self.list.addItem(item)
        flags = []
        if case_sensitive:
            flags.append("Aa")
        if use_regex:
            flags.append("Regex")
        flag_s = f" [{', '.join(flags)}]" if flags else ""
        self.status.setText(
            f"{len(self._hits)} Treffer in {len(self._paths)} Doc(s)"
            f"{flag_s} — Klick öffnet Doc+Seite — 1.4.1"
        )

    def _activate(self, item: QListWidgetItem | None = None) -> None:
        it = item or self.list.currentItem()
        if it is None:
            return
        h = it.data(Qt.UserRole)
        if not isinstance(h, AnnSearchHit):
            return
        self.hit_activated.emit(h.path, int(h.page), h.ann_id)
