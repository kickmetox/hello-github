"""Vorschau-Dialog: Annotation-Duplikate vor dem Zusammenführen prüfen."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)


class MergeDuplicatesPreviewDialog(QDialog):
    """
    Zeigt gefundene Duplikat-Gruppen und fragt vor Apply.
    accept() → zusammenführen; reject() → abbrechen.
    """

    def __init__(self, groups: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Duplikate — Vorschau")
        self.setWindowModality(Qt.WindowModal)
        self.resize(520, 360)

        n_groups = len(groups)
        n_extra = sum(max(0, len(g) - 1) for g in groups)

        layout = QVBoxLayout(self)
        summary = QLabel(
            f"{n_groups} Duplikat-Gruppe(n), {n_extra} überzählige Annotation(en).\n"
            "Beim Übernehmen bleibt die älteste je Gruppe; Text und Tags werden gemerged."
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)

        preview_groups = self.sorted_groups_for_preview(groups)
        self.list = QListWidget()
        self.list.setToolTip("Vorschau der Duplikat-Gruppen (noch nicht angewendet)")
        for gi, group in enumerate(preview_groups, start=1):
            for ai, ann in enumerate(group):
                typ = getattr(getattr(ann, "type", None), "value", None) or str(
                    getattr(ann, "type", "?")
                )
                page = int(getattr(ann, "page", 0) or 0) + 1
                text = str(getattr(ann, "text", "") or "").strip().replace("\n", " ")
                if len(text) > 48:
                    text = text[:45] + "…"
                tags = getattr(ann, "tags", None) or []
                tag_s = ", ".join(str(t) for t in tags[:4]) if tags else "—"
                role = "behalten" if ai == 0 else "entfernen"
                # Anzeige grob nach oldest sortiert — Dialog sortiert für Klarheit
                line = (
                    f"G{gi} · S.{page} · {typ} · [{role}] · "
                    f"„{text or '—'}“ · Tags: {tag_s}"
                )
                item = QListWidgetItem(line)
                item.setData(Qt.UserRole, getattr(ann, "id", None))
                self.list.addItem(item)
        layout.addWidget(self.list)

        hint = QLabel(
            "Reihenfolge in der Liste: älteste zuerst (wird behalten). "
            "Übernehmen führt die Zusammenführung aus (Ctrl+Z rückgängig)."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #555; font-size: 11px;")
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.button(QDialogButtonBox.Ok).setText("Übernehmen")
        buttons.button(QDialogButtonBox.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def sorted_groups_for_preview(groups: list) -> list:
        """Gruppen mit oldest-first für Vorschau (keep=oldest)."""
        out = []
        for group in groups:
            ordered = sorted(
                list(group),
                key=lambda a: (str(getattr(a, "created", "") or ""), getattr(a, "id", "")),
            )
            out.append(ordered)
        return out
