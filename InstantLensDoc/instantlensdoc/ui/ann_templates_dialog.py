"""Dialog: Annotation-Vorlagen laden/speichern (ildtmpl-v1) — 2.4.0."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from instantlensdoc.core.ann_templates import (
    TMPL_SCHEMA_ID,
    AnnTemplate,
    AnnTemplateError,
    apply_template,
    capture_current_styles,
    delete_template,
    export_templates_json,
    import_templates_json,
    load_templates,
    save_template,
)
from instantlensdoc.core.app_settings import (
    dialog_start_dir,
    get_last_export_dir,
    remember_recent_dir,
    set_last_export_dir,
)


class AnnTemplatesDialog(QDialog):
    """Gespeicherte Stempel/Highlight-Styles verwalten."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Annotation-Vorlagen (ildtmpl-v1)")
        self.resize(480, 420)
        self.applied: AnnTemplate | None = None

        layout = QVBoxLayout(self)
        info = QLabel(
            "Gespeicherte Stempel- und Highlight-Styles. "
            f"Schema <b>{TMPL_SCHEMA_ID}</b> — laden setzt Farben/Deckkraft."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.list = QListWidget()
        self.list.setAlternatingRowColors(True)
        self.list.itemDoubleClicked.connect(self._apply_selected)
        layout.addWidget(self.list, 1)

        row = QHBoxLayout()
        self.btn_apply = QPushButton("Anwenden")
        self.btn_apply.setToolTip("Ausgewählte Vorlage auf aktuelle Styles anwenden")
        self.btn_apply.clicked.connect(self._apply_selected)
        row.addWidget(self.btn_apply)

        self.btn_save_hl = QPushButton("Highlight speichern…")
        self.btn_save_hl.setToolTip("Aktuellen Highlight-Style als Vorlage speichern")
        self.btn_save_hl.clicked.connect(lambda: self._save_current("highlight"))
        row.addWidget(self.btn_save_hl)

        self.btn_save_stamp = QPushButton("Stempel speichern…")
        self.btn_save_stamp.setToolTip("Aktuellen Stempel-Style als Vorlage speichern")
        self.btn_save_stamp.clicked.connect(lambda: self._save_current("stamp"))
        row.addWidget(self.btn_save_stamp)
        layout.addLayout(row)

        row2 = QHBoxLayout()
        self.btn_delete = QPushButton("Löschen")
        self.btn_delete.clicked.connect(self._delete_selected)
        row2.addWidget(self.btn_delete)

        self.btn_export = QPushButton("Export JSON…")
        self.btn_export.setToolTip(f"Alle Vorlagen als {TMPL_SCHEMA_ID} exportieren")
        self.btn_export.clicked.connect(self._export_json)
        row2.addWidget(self.btn_export)

        self.btn_import = QPushButton("Import JSON…")
        self.btn_import.setToolTip(f"Vorlagen aus {TMPL_SCHEMA_ID} mergen")
        self.btn_import.clicked.connect(self._import_json)
        row2.addWidget(self.btn_import)
        layout.addLayout(row2)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self._reload()

    def _reload(self) -> None:
        self.list.clear()
        for t in load_templates():
            kind_de = "Stempel" if t.kind == "stamp" else "Highlight"
            label = f"{t.name}  ·  {kind_de}  ·  {t.color}  ·  α={t.opacity:.2f}"
            if t.stamp_text:
                label += f"  ·  „{t.stamp_text[:24]}“"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, t.id)
            item.setToolTip(
                f"id={t.id}\nkind={t.kind}\ncolor={t.color}\n"
                f"opacity={t.opacity}\nstamp_text={t.stamp_text}"
            )
            self.list.addItem(item)

    def _selected_id(self) -> str | None:
        item = self.list.currentItem()
        if not item:
            return None
        return str(item.data(Qt.UserRole) or "") or None

    def _selected_template(self) -> AnnTemplate | None:
        tid = self._selected_id()
        if not tid:
            return None
        for t in load_templates():
            if t.id == tid:
                return t
        return None

    def _apply_selected(self) -> None:
        t = self._selected_template()
        if t is None:
            QMessageBox.information(self, "Vorlagen", "Bitte eine Vorlage wählen.")
            return
        apply_template(t)
        self.applied = t
        self.accept()

    def _save_current(self, kind: str) -> None:
        default = "Highlight-Style" if kind == "highlight" else "Stempel-Style"
        name, ok = QInputDialog.getText(
            self,
            "Vorlage speichern",
            "Name der Vorlage:",
            text=default,
        )
        if not ok:
            return
        name = (name or "").strip() or default
        stamp_text = ""
        if kind == "stamp":
            stamp_text, ok2 = QInputDialog.getText(
                self,
                "Stempel-Text",
                "Optionaler Stempel-Text (z. B. GENEHMIGT):",
                text="GENEHMIGT",
            )
            if not ok2:
                return
            stamp_text = (stamp_text or "").strip()
        draft = capture_current_styles(kind, name=name, stamp_text=stamp_text)
        entry = save_template(
            draft.name,
            draft.kind,
            color=draft.color,
            opacity=draft.opacity,
            stroke_width=draft.stroke_width,
            fill_color=draft.fill_color,
            stamp_text=draft.stamp_text,
            tags=draft.tags,
        )
        self._reload()
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.UserRole) == entry.id:
                self.list.setCurrentRow(i)
                break

    def _delete_selected(self) -> None:
        tid = self._selected_id()
        if not tid:
            return
        t = self._selected_template()
        label = t.name if t else tid
        reply = QMessageBox.question(
            self,
            "Vorlage löschen",
            f"Vorlage „{label}“ wirklich löschen?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        delete_template(tid)
        self._reload()

    def _export_json(self) -> None:
        start = get_last_export_dir() or dialog_start_dir()
        path, _ = QFileDialog.getSaveFileName(
            self,
            f"Vorlagen exportieren ({TMPL_SCHEMA_ID})",
            str(Path(start) / "ann-templates.json"),
            "JSON (*.json)",
        )
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        try:
            out = export_templates_json(path)
            remember_recent_dir(out)
            set_last_export_dir(out.parent)
            QMessageBox.information(
                self, "Vorlagen", f"Exportiert ({TMPL_SCHEMA_ID}):\n{out}"
            )
        except Exception as e:
            QMessageBox.warning(self, "Vorlagen", str(e))

    def _import_json(self) -> None:
        start = get_last_export_dir() or dialog_start_dir()
        path, _ = QFileDialog.getOpenFileName(
            self,
            f"Vorlagen importieren ({TMPL_SCHEMA_ID})",
            str(start),
            "JSON (*.json)",
        )
        if not path:
            return
        try:
            items = import_templates_json(path, merge=True)
            remember_recent_dir(Path(path))
            self._reload()
            QMessageBox.information(
                self,
                "Vorlagen",
                f"Importiert/gemerged ({TMPL_SCHEMA_ID}): {len(items)} Vorlage(n).",
            )
        except AnnTemplateError as e:
            QMessageBox.warning(self, "Vorlagen", f"Ungültiges Schema:\n{e}")
        except Exception as e:
            QMessageBox.warning(self, "Vorlagen", str(e))
