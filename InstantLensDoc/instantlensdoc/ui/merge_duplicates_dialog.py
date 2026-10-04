"""Vorschau-Dialog: Annotation-Duplikate vor dem Zusammenführen prüfen."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from instantlensdoc.core.text_diff import annotation_text_diff_short


class MergeDuplicatesPreviewDialog(QDialog):
    """
    Zeigt gefundene Duplikat-Gruppen und fragt vor Apply.
    Pro Gruppe: einzeln mergen oder behalten (beide bleiben).
    accept() → ausgewählte Gruppen zusammenführen; reject() → abbrechen.
    """

    def __init__(self, groups: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Duplikate — Vorschau")
        self.setWindowModality(Qt.WindowModal)
        self.resize(560, 420)

        self._preview_groups = self.sorted_groups_for_preview(groups)
        self._group_checks: list[QCheckBox] = []

        n_groups = len(self._preview_groups)
        n_extra = sum(max(0, len(g) - 1) for g in self._preview_groups)

        layout = QVBoxLayout(self)
        summary = QLabel(
            f"{n_groups} Duplikat-Gruppe(n), {n_extra} überzählige Annotation(en).\n"
            "Pro Paar/Gruppe: ✓ Mergen (älteste behalten, Text/Tags zusammenführen) "
            "oder abwählen = behalten (beide bleiben)."
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)

        row = QHBoxLayout()
        btn_all = QPushButton("Alle mergen")
        btn_all.setToolTip("Alle Gruppen zum Zusammenführen markieren")
        btn_all.clicked.connect(lambda: self._set_all_checked(True))
        btn_none = QPushButton("Alle behalten")
        btn_none.setToolTip("Keine Gruppe mergen — alle Paare behalten")
        btn_none.clicked.connect(lambda: self._set_all_checked(False))
        row.addWidget(btn_all)
        row.addWidget(btn_none)
        row.addStretch(1)
        layout.addLayout(row)

        self.list = QListWidget()
        self.list.setToolTip(
            "Pro Gruppe: Häkchen = mergen; ohne Häkchen = behalten (einzeln je Paar)"
        )
        for gi, group in enumerate(self._preview_groups, start=1):
            # Gruppen-Header mit Checkbox
            header = QWidget()
            hl = QHBoxLayout(header)
            hl.setContentsMargins(4, 2, 4, 2)
            cb = QCheckBox(f"G{gi} mergen ({len(group)} Ann.)")
            cb.setChecked(True)
            cb.setToolTip(
                "An: zusammenführen (älteste behalten). Aus: Gruppe behalten / nicht mergen."
            )
            self._group_checks.append(cb)
            hl.addWidget(cb)
            hl.addStretch(1)
            header_item = QListWidgetItem()
            header_item.setFlags(Qt.ItemIsEnabled)
            header_item.setData(Qt.UserRole, ("group", gi - 1))
            self.list.addItem(header_item)
            self.list.setItemWidget(header_item, header)
            header_item.setSizeHint(header.sizeHint())

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
                role = "behalten" if ai == 0 else "entfernen (bei Merge)"
                line = (
                    f"    · S.{page} · {typ} · [{role}] · "
                    f"„{text or '—'}“ · Tags: {tag_s}"
                )
                item = QListWidgetItem(line)
                item.setData(Qt.UserRole, getattr(ann, "id", None))
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.list.addItem(item)

            # Diff-Kurztext der beiden (älteste vs. nächste) inkl. Tags/Farbe
            if len(group) >= 2:
                keep = group[0]
                other = group[1]
                t_keep = str(getattr(keep, "text", "") or "")
                t_other = str(getattr(other, "text", "") or "")
                try:
                    from instantlensdoc.core.app_settings import get_merge_diff_max_side

                    max_side = get_merge_diff_max_side()
                except Exception:
                    max_side = 28
                diff_s = annotation_text_diff_short(
                    t_keep,
                    t_other,
                    max_side=max_side,
                    left_tags=getattr(keep, "tags", None),
                    right_tags=getattr(other, "tags", None),
                    left_color=getattr(keep, "color", None),
                    right_color=getattr(other, "color", None),
                )
                if len(group) > 2:
                    diff_s = f"{diff_s} (+{len(group) - 2} weitere)"
                diff_item = QListWidgetItem(f"    ↕ {diff_s}")
                diff_item.setData(Qt.UserRole, ("diff", gi - 1))
                diff_item.setFlags(Qt.ItemIsEnabled)
                self.list.addItem(diff_item)
        layout.addWidget(self.list)

        hint = QLabel(
            "Reihenfolge je Gruppe: älteste zuerst (wird bei Merge behalten). "
            "↕ Diff: Kurzvergleich Text + Tags + Farbe. "
            "Übernehmen führt nur markierte Gruppen aus (Ctrl+Z rückgängig)."
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

    def _set_all_checked(self, checked: bool) -> None:
        for cb in self._group_checks:
            cb.setChecked(bool(checked))

    def groups_to_merge(self) -> list:
        """Nur die mit Häkchen markierten Gruppen (oldest-first sortiert)."""
        out = []
        for i, cb in enumerate(self._group_checks):
            if cb.isChecked() and i < len(self._preview_groups):
                out.append(self._preview_groups[i])
        return out

    def groups_to_keep(self) -> list:
        """Abgewählte Gruppen (behalten / nicht mergen)."""
        out = []
        for i, cb in enumerate(self._group_checks):
            if not cb.isChecked() and i < len(self._preview_groups):
                out.append(self._preview_groups[i])
        return out

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
