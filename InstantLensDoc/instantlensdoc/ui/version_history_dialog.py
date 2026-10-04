"""Dialog: Versionsverlauf speichern/wiederherstellen — 2.6.21."""

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
    QVBoxLayout,
)

from instantlensdoc.core.i18n import tr
from instantlensdoc.core.version_store import VersionStore


class VersionHistoryDialog(QDialog):
    """Lokale Dokument-Versionen speichern und wiederherstellen."""

    def __init__(
        self,
        doc_path: str | Path,
        parent=None,
        *,
        current_text: str | None = None,
        on_restore_text: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(parent)
        self.doc_path = Path(doc_path)
        self.store = VersionStore.for_doc(self.doc_path, load=True)
        self._current_text = current_text
        self._on_restore_text = on_restore_text
        self.setWindowTitle(tr("version_history") or "Versionsverlauf")
        self.setWindowModality(Qt.WindowModal)
        self.resize(560, 460)
        self.setObjectName("ildVersionHistoryDialog")

        layout = QVBoxLayout(self)
        self.lbl_meta = QLabel()
        layout.addWidget(self.lbl_meta)

        self.list = QListWidget()
        self.list.setObjectName("versionHistoryList")
        layout.addWidget(self.list, 1)

        label_row = QHBoxLayout()
        label_row.addWidget(QLabel(tr("version_label") or "Label:"))
        self.ed_label = QLineEdit()
        self.ed_label.setPlaceholderText("Snapshot")
        label_row.addWidget(self.ed_label, 1)
        layout.addLayout(label_row)

        btn_row = QHBoxLayout()
        btn_save = QPushButton(tr("save_version") or "Version speichern")
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_save)
        btn_restore = QPushButton(tr("restore_version") or "Wiederherstellen")
        btn_restore.clicked.connect(self._restore)
        btn_row.addWidget(btn_restore)
        btn_del = QPushButton(tr("delete_version") or "Löschen")
        btn_del.clicked.connect(self._delete)
        btn_row.addWidget(btn_del)
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._refresh()

    def _refresh(self) -> None:
        s = self.store.summary()
        self.lbl_meta.setText(
            f"{self.store.root.name} · {s['total']} Version(en) · "
            f"Limit {s['limit']}"
        )
        self.list.clear()
        for e in reversed(self.store.list_versions(limit=50)):
            ts = e.ts.replace("T", " ").replace("+00:00", " UTC")
            item = QListWidgetItem(
                f"{ts}  {e.label}  ({e.kind}, {e.size} B)  [{e.id}]"
            )
            item.setData(Qt.UserRole, e.id)
            self.list.addItem(item)

    def _selected_id(self) -> str | None:
        item = self.list.currentItem()
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _save(self) -> None:
        label = self.ed_label.text().strip()
        try:
            if self._current_text is not None:
                self.store.save_version(label=label, text=self._current_text)
            elif self.doc_path.is_file():
                self.store.save_version(label=label, source=self.doc_path)
            else:
                QMessageBox.warning(
                    self,
                    tr("version_history") or "Versionsverlauf",
                    tr("version_no_source")
                    or "Kein Dokumentinhalt zum Speichern.",
                )
                return
        except Exception as e:
            QMessageBox.warning(
                self,
                tr("version_history") or "Versionsverlauf",
                str(e),
            )
            return
        self.ed_label.clear()
        self._refresh()

    def _restore(self) -> None:
        vid = self._selected_id()
        if not vid:
            return
        reply = QMessageBox.question(
            self,
            tr("restore_version") or "Wiederherstellen",
            tr("version_restore_confirm")
            or "Aktuellen Stand durch diese Version ersetzen?",
        )
        if reply != QMessageBox.Yes:
            return
        try:
            if self._on_restore_text is not None:
                text = self.store.read_text(vid)
                self._on_restore_text(text)
            else:
                self.store.restore(vid)
        except Exception as e:
            QMessageBox.warning(
                self,
                tr("version_history") or "Versionsverlauf",
                str(e),
            )
            return
        self.accept()

    def _delete(self) -> None:
        vid = self._selected_id()
        if vid and self.store.delete(vid):
            self._refresh()
