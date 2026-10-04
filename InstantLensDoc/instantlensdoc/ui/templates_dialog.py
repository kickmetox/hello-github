"""Dialog: Nutzer-Vorlagen per Drag umsortieren und Reihenfolge speichern."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)


class TemplatesOrderDialog(QDialog):
    """
    Liste der Nutzer-Vorlagen mit InternalMove-Drag.
    accept() → neue ID-Reihenfolge via ordered_ids().
    """

    def __init__(self, templates: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vorlagen — Reihenfolge")
        self.setWindowModality(Qt.WindowModal)
        self.resize(420, 360)

        layout = QVBoxLayout(self)
        hint = QLabel(
            "Ziehen zum Neuordnen. Die gespeicherte Reihenfolge gilt für "
            "Datei → Neu → Meine Vorlagen."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.list = QListWidget()
        self.list.setObjectName("templatesOrderList")
        self.list.setDragDropMode(QAbstractItemView.InternalMove)
        self.list.setDefaultDropAction(Qt.MoveAction)
        self.list.setToolTip("Vorlagen ziehen — Reihenfolge wird beim Übernehmen gespeichert")
        for t in templates:
            tid = str(t.get("id") or "")
            title = str(t.get("title") or tid)
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, tid)
            item.setToolTip(f"Vorlage „{title}“ ({tid})")
            self.list.addItem(item)
        layout.addWidget(self.list)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Speichern")
        buttons.button(QDialogButtonBox.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def ordered_ids(self) -> list[str]:
        ids: list[str] = []
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item is None:
                continue
            tid = item.data(Qt.UserRole)
            if tid:
                ids.append(str(tid))
        return ids
