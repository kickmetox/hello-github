"""Zentrale Multi-Dokument-Suche: Volltext über alle offenen PDFs — 2.0.0."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
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
    QWidget,
)

from instantlensdoc.core import fulltext as fulltext_mod


class MultiDocSearchDialog(QDialog):
    """
    Zentrale Trefferliste: Volltext (Textlayer) über alle offenen/gelisteten PDFs.
    Doppelklick / Enter → Treffer aktivieren (Signal hit_activated).
    """

    hit_activated = Signal(str, object, str)  # path, page_index|None, query

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        paths: list[str] | None = None,
        initial_query: str = "",
    ):
        super().__init__(parent)
        self.setObjectName("multiDocSearchDialog")
        self.setWindowTitle("Multi-Dokument-Suche — InstantLens Doc 2.0")
        self.setModal(False)
        self.resize(640, 480)
        self._paths = list(paths or [])
        self._hits: list[fulltext_mod.SearchHit] = []
        self._query = ""

        layout = QVBoxLayout(self)
        intro = QLabel(
            "Volltextsuche über alle offenen PDFs (Textlayer). "
            "Treffer zentral; Doppelklick springt zum Dokument."
        )
        intro.setWordWrap(True)
        intro.setObjectName("multiDocSearchIntro")
        layout.addWidget(intro)

        row = QHBoxLayout()
        self.query_edit = QLineEdit()
        self.query_edit.setObjectName("multiDocSearchQuery")
        self.query_edit.setPlaceholderText("Suchbegriff…")
        self.query_edit.setClearButtonEnabled(True)
        if initial_query:
            self.query_edit.setText(initial_query)
        self.query_edit.returnPressed.connect(self.run_search)
        self.btn_search = QPushButton("Suchen")
        self.btn_search.setObjectName("multiDocSearchBtn")
        self.btn_search.setDefault(True)
        self.btn_search.clicked.connect(self.run_search)
        row.addWidget(self.query_edit, 1)
        row.addWidget(self.btn_search)
        layout.addLayout(row)

        self.status = QLabel("")
        self.status.setObjectName("multiDocSearchStatus")
        self.status.setAccessibleName("Multi-Dokument-Suche Status")
        layout.addWidget(self.status)

        self.hits_list = QListWidget()
        self.hits_list.setObjectName("multiDocSearchHits")
        self.hits_list.setAccessibleName("Zentrale Trefferliste")
        self.hits_list.itemActivated.connect(self._activate_item)
        self.hits_list.itemDoubleClicked.connect(self._activate_item)
        layout.addWidget(self.hits_list, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        close_btn = buttons.button(QDialogButtonBox.Close)
        if close_btn is not None:
            close_btn.setText("Schließen")
        layout.addWidget(buttons)

        esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        esc.setContext(Qt.WindowShortcut)
        esc.activated.connect(self.reject)

        if initial_query.strip():
            self.run_search()

    def set_paths(self, paths: list[str]) -> None:
        self._paths = list(paths or [])

    def run_search(self) -> None:
        query = (self.query_edit.text() or "").strip()
        self._query = query
        self.hits_list.clear()
        self._hits = []
        if not query:
            self.status.setText("Leere Suche")
            return
        pdfs = fulltext_mod.filter_pdf_paths(self._paths)
        if not pdfs:
            self.status.setText("Keine offenen PDFs für Multi-Dokument-Suche")
            return
        hits = fulltext_mod.search_open_pdfs(pdfs, query, max_hits=200)
        self._hits = hits
        if not hits:
            self.status.setText(f"0 Treffer in {len(pdfs)} PDF(s)")
            return
        for h in hits:
            label = fulltext_mod.format_hit_line(
                Path(h.path).name,
                page=h.page,
                line=h.line,
                snippet=h.snippet or query,
                kind=h.kind,
                query=query,
            )
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, (h.path, h.page, query))
            item.setToolTip(f"{h.path}\n{h.snippet or ''}")
            self.hits_list.addItem(item)
        files = {Path(h.path).name for h in hits}
        self.status.setText(
            f"{len(hits)} Treffer in {len(pdfs)} PDF(s) · {len(files)} Datei(en) — zentral"
        )

    def _activate_item(self, item: QListWidgetItem | None = None) -> None:
        it = item or self.hits_list.currentItem()
        if it is None:
            return
        payload = it.data(Qt.UserRole)
        if not (isinstance(payload, tuple) and len(payload) >= 2):
            return
        path = str(payload[0])
        page = payload[1]
        query = str(payload[2]) if len(payload) >= 3 else self._query
        self.hit_activated.emit(path, page, query)
