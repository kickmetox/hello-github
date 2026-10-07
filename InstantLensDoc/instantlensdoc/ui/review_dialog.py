"""Dialog: Review / Track Changes — 2.6.21."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from instantlensdoc.core.i18n import tr
from instantlensdoc.core.review import ReviewStore, format_review_summary


class ReviewDialog(QDialog):
    """Panel für Änderungen nachverfolgen (lokal)."""

    def __init__(
        self,
        doc_path: str | Path,
        parent=None,
        *,
        on_goto: Optional[Callable[[int, int], None]] = None,
    ):
        super().__init__(parent)
        self.doc_path = Path(doc_path)
        self.store = ReviewStore.for_doc(self.doc_path, load=True)
        self._on_goto = on_goto
        self.setWindowTitle(tr("review_mode") or "Review / Änderungen")
        self.setWindowModality(Qt.WindowModal)
        self.resize(560, 480)
        self.setObjectName("ildReviewDialog")

        layout = QVBoxLayout(self)
        self.chk_enabled = QCheckBox(tr("track_changes") or "Änderungen nachverfolgen")
        self.chk_enabled.setChecked(self.store.enabled)
        self.chk_enabled.toggled.connect(self._toggle_enabled)
        layout.addWidget(self.chk_enabled)

        author_row = QHBoxLayout()
        author_row.addWidget(QLabel(tr("review_author") or "Autor:"))
        self.ed_author = QLineEdit(self.store.author)
        self.ed_author.setPlaceholderText("local")
        self.ed_author.editingFinished.connect(self._apply_author)
        author_row.addWidget(self.ed_author, 1)
        layout.addLayout(author_row)

        self.lbl_meta = QLabel()
        layout.addWidget(self.lbl_meta)

        self.list = QListWidget()
        self.list.setObjectName("reviewChangeList")
        self.list.itemDoubleClicked.connect(self._on_dbl)
        layout.addWidget(self.list, 1)

        btn_row = QHBoxLayout()
        btn_accept = QPushButton(tr("accept_change") or "Annehmen")
        btn_accept.clicked.connect(self._accept_selected)
        btn_row.addWidget(btn_accept)
        btn_reject = QPushButton(tr("reject_change") or "Ablehnen")
        btn_reject.clicked.connect(self._reject_selected)
        btn_row.addWidget(btn_reject)
        btn_accept_all = QPushButton(tr("accept_all") or "Alle annehmen")
        btn_accept_all.clicked.connect(self._accept_all)
        btn_row.addWidget(btn_accept_all)
        btn_reject_all = QPushButton(tr("reject_all") or "Alle ablehnen")
        btn_reject_all.clicked.connect(self._reject_all)
        btn_row.addWidget(btn_reject_all)
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
        self._refresh()

    def _toggle_enabled(self, checked: bool) -> None:
        self.store.set_enabled(bool(checked))
        self._refresh()

    def _apply_author(self) -> None:
        self.store.set_author(self.ed_author.text())
        self._refresh()

    def _refresh(self) -> None:
        s = self.store.summary()
        self.lbl_meta.setText(
            f"{self.store.path.name} · pending {s['pending']} "
            f"(+{s['pending_inserts']}/−{s['pending_deletes']}) · "
            f"gesamt {s['total']}"
        )
        self.list.clear()
        for c in self.store.list_changes(limit=200):
            item = QListWidgetItem(format_review_summary([c], max_items=1))
            item.setData(Qt.UserRole, c.id)
            self.list.addItem(item)

    def _selected_id(self) -> str | None:
        item = self.list.currentItem()
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _accept_selected(self) -> None:
        cid = self._selected_id()
        if cid and self.store.accept(cid):
            self._refresh()

    def _reject_selected(self) -> None:
        cid = self._selected_id()
        if cid and self.store.reject(cid):
            self._refresh()

    def _accept_all(self) -> None:
        self.store.accept_all()
        self._refresh()

    def _reject_all(self) -> None:
        self.store.reject_all()
        self._refresh()

    def _on_dbl(self, item: QListWidgetItem) -> None:
        cid = item.data(Qt.UserRole)
        c = self.store.get(cid) if cid else None
        if c and self._on_goto:
            self._on_goto(c.start, c.end)
