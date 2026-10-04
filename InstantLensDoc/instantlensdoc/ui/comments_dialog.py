"""Dialog: Dokument-Kommentare — 2.6.21."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from instantlensdoc.core.doc_comments import CommentStore, format_comments_summary
from instantlensdoc.core.i18n import tr


class CommentsDialog(QDialog):
    """Kommentare an Textstellen (ohne Body-Änderung)."""

    def __init__(
        self,
        doc_path: str | Path,
        parent=None,
        *,
        selection_start: int = 0,
        selection_end: int = 0,
        anchor_text: str = "",
        on_goto: Optional[Callable[[int, int], None]] = None,
    ):
        super().__init__(parent)
        self.doc_path = Path(doc_path)
        self.store = CommentStore.for_doc(self.doc_path, load=True)
        self._sel_start = int(selection_start)
        self._sel_end = int(selection_end)
        self._anchor = str(anchor_text or "")
        self._on_goto = on_goto
        self.setWindowTitle(tr("doc_comments") or "Kommentare")
        self.setWindowModality(Qt.WindowModal)
        self.resize(560, 520)
        self.setObjectName("ildCommentsDialog")

        layout = QVBoxLayout(self)
        author_row = QHBoxLayout()
        author_row.addWidget(QLabel(tr("review_author") or "Autor:"))
        self.ed_author = QLineEdit(self.store.author)
        self.ed_author.editingFinished.connect(self._apply_author)
        author_row.addWidget(self.ed_author, 1)
        layout.addLayout(author_row)

        self.lbl_meta = QLabel()
        layout.addWidget(self.lbl_meta)

        self.list = QListWidget()
        self.list.setObjectName("docCommentList")
        self.list.itemDoubleClicked.connect(self._on_dbl)
        layout.addWidget(self.list, 1)

        layout.addWidget(QLabel(tr("new_comment") or "Neuer Kommentar:"))
        self.ed_body = QTextEdit()
        self.ed_body.setMaximumHeight(90)
        self.ed_body.setPlaceholderText(
            tr("comment_body_hint") or "Feedback zur Auswahl…"
        )
        layout.addWidget(self.ed_body)

        add_row = QHBoxLayout()
        btn_add = QPushButton(tr("add_comment") or "Kommentar hinzufügen")
        btn_add.clicked.connect(self._add)
        add_row.addWidget(btn_add)
        btn_resolve = QPushButton(tr("resolve_comment") or "Erledigt")
        btn_resolve.clicked.connect(self._resolve)
        add_row.addWidget(btn_resolve)
        btn_del = QPushButton(tr("delete_comment") or "Löschen")
        btn_del.clicked.connect(self._delete)
        add_row.addWidget(btn_del)
        layout.addLayout(add_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._refresh()

    def _apply_author(self) -> None:
        self.store.set_author(self.ed_author.text())
        self._refresh()

    def _refresh(self) -> None:
        s = self.store.summary()
        self.lbl_meta.setText(
            f"{self.store.path.name} · offen {s['open']} · "
            f"erledigt {s['resolved']} · gesamt {s['total']}"
        )
        self.list.clear()
        for c in self.store.list_comments(limit=200):
            item = QListWidgetItem(format_comments_summary([c], max_items=1))
            item.setData(Qt.UserRole, c.id)
            self.list.addItem(item)

    def _selected_id(self) -> str | None:
        item = self.list.currentItem()
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _add(self) -> None:
        body = self.ed_body.toPlainText().strip()
        if not body:
            QMessageBox.information(
                self,
                tr("doc_comments") or "Kommentare",
                tr("comment_empty") or "Bitte Kommentartext eingeben.",
            )
            return
        self.store.add(
            body,
            start=self._sel_start,
            end=self._sel_end,
            anchor_text=self._anchor,
            author=self.ed_author.text().strip() or None,
        )
        self.ed_body.clear()
        self._refresh()

    def _resolve(self) -> None:
        cid = self._selected_id()
        if cid and self.store.resolve(cid, resolved=True):
            self._refresh()

    def _delete(self) -> None:
        cid = self._selected_id()
        if cid and self.store.delete(cid):
            self._refresh()

    def _on_dbl(self, item: QListWidgetItem) -> None:
        cid = item.data(Qt.UserRole)
        c = self.store.get(cid) if cid else None
        if c and self._on_goto:
            self._on_goto(c.start, c.end)
