"""Dialog: Annotation-Vorlagen laden/speichern (ildtmpl-v1) — 2.4.1."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
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
    get_default_template_id,
    import_templates_json,
    load_templates,
    rename_template,
    save_template,
    set_default_template_id,
)
from instantlensdoc.core.app_settings import (
    dialog_start_dir,
    get_last_export_dir,
    remember_recent_dir,
    set_last_export_dir,
)


class AnnTemplatesDialog(QDialog):
    """Gespeicherte Stempel/Highlight-Styles: Umbenennen/Löschen/Vorschau/Standard — 2.4.1."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Annotation-Vorlagen (ildtmpl-v1)")
        self.resize(560, 460)
        self.applied: AnnTemplate | None = None

        layout = QVBoxLayout(self)
        info = QLabel(
            "Gespeicherte Stempel- und Highlight-Styles. "
            f"Schema <b>{TMPL_SCHEMA_ID}</b> — laden setzt Farben/Deckkraft. "
            "★ = Standard-Vorlage — 2.4.1"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        body = QHBoxLayout()
        self.list = QListWidget()
        self.list.setAlternatingRowColors(True)
        self.list.itemDoubleClicked.connect(self._apply_selected)
        self.list.currentRowChanged.connect(self._update_preview)
        body.addWidget(self.list, 2)

        prev_col = QVBoxLayout()
        prev_col.addWidget(QLabel("Vorschau"))
        self.preview = QLabel("—")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(160, 120)
        self.preview.setStyleSheet(
            "background:#f5f5f5;border:1px solid #ccc;color:#666;"
        )
        self.preview.setToolTip("Farb-/Style-Vorschau der ausgewählten Vorlage — 2.4.1")
        prev_col.addWidget(self.preview, 1)
        self.preview_meta = QLabel("")
        self.preview_meta.setWordWrap(True)
        self.preview_meta.setStyleSheet("color:#555;")
        prev_col.addWidget(self.preview_meta)
        body.addLayout(prev_col, 1)
        layout.addLayout(body)

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
        self.btn_rename = QPushButton("Umbenennen…")
        self.btn_rename.setToolTip("Ausgewählte Vorlage umbenennen — 2.4.1")
        self.btn_rename.clicked.connect(self._rename_selected)
        row2.addWidget(self.btn_rename)

        self.btn_delete = QPushButton("Löschen")
        self.btn_delete.setToolTip("Ausgewählte Vorlage löschen — 2.4.1")
        self.btn_delete.clicked.connect(self._delete_selected)
        row2.addWidget(self.btn_delete)

        self.btn_default = QPushButton("Als Standard")
        self.btn_default.setToolTip("Ausgewählte Vorlage als Standard markieren (★) — 2.4.1")
        self.btn_default.clicked.connect(self._mark_default)
        row2.addWidget(self.btn_default)

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
        default_id = get_default_template_id()
        for t in load_templates():
            kind_de = "Stempel" if t.kind == "stamp" else "Highlight"
            star = "★ " if t.id == default_id else ""
            label = f"{star}{t.name}  ·  {kind_de}  ·  {t.color}  ·  α={t.opacity:.2f}"
            if t.stamp_text:
                label += f"  ·  „{t.stamp_text[:24]}“"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, t.id)
            tip = (
                f"id={t.id}\nkind={t.kind}\ncolor={t.color}\n"
                f"opacity={t.opacity}\nstamp_text={t.stamp_text}"
            )
            if t.id == default_id:
                tip += "\n★ Standard-Vorlage — 2.4.1"
            item.setToolTip(tip)
            self.list.addItem(item)
        if self.list.count() > 0 and self.list.currentRow() < 0:
            self.list.setCurrentRow(0)
        self._update_preview()

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

    def _swatch_pixmap(self, color: str, fill: str, opacity: float) -> QPixmap:
        pix = QPixmap(140, 90)
        pix.fill(QColor("#f5f5f5"))
        painter = QPainter(pix)
        try:
            c = QColor(color)
            if not c.isValid():
                c = QColor("#FFE066")
            c.setAlphaF(max(0.15, min(1.0, float(opacity))))
            painter.fillRect(12, 12, 116, 66, c)
            border = QColor(fill if QColor(fill).isValid() else color)
            painter.setPen(border)
            painter.drawRect(12, 12, 116, 66)
        finally:
            painter.end()
        return pix

    def _update_preview(self, *_args) -> None:
        t = self._selected_template()
        if t is None:
            self.preview.setPixmap(QPixmap())
            self.preview.setText("—")
            self.preview_meta.setText("")
            return
        self.preview.setPixmap(self._swatch_pixmap(t.color, t.fill_color, t.opacity))
        self.preview.setText("")
        kind_de = "Stempel" if t.kind == "stamp" else "Highlight"
        star = "★ Standard · " if t.id == get_default_template_id() else ""
        lines = [
            f"{star}{t.name}",
            f"{kind_de} · {t.color} · α={t.opacity:.2f}",
            f"Strich {t.stroke_width:.1f} · Füllung {t.fill_color}",
        ]
        if t.stamp_text:
            lines.append(f"Text: {t.stamp_text[:40]}")
        self.preview_meta.setText("\n".join(lines))

    def _apply_selected(self) -> None:
        t = self._selected_template()
        if t is None:
            QMessageBox.information(self, "Vorlagen", "Bitte eine Vorlage wählen.")
            return
        apply_template(t)
        self.applied = t
        self.accept()

    def _rename_selected(self) -> None:
        t = self._selected_template()
        if t is None:
            QMessageBox.information(self, "Vorlagen", "Bitte eine Vorlage wählen.")
            return
        name, ok = QInputDialog.getText(
            self,
            "Vorlage umbenennen",
            "Neuer Name:",
            text=t.name,
        )
        if not ok:
            return
        name = (name or "").strip()
        if not name:
            QMessageBox.warning(self, "Vorlagen", "Name darf nicht leer sein.")
            return
        try:
            renamed = rename_template(t.id, name)
        except AnnTemplateError as e:
            QMessageBox.warning(self, "Vorlagen", str(e))
            return
        if renamed is None:
            QMessageBox.warning(self, "Vorlagen", "Umbenennen fehlgeschlagen.")
            return
        self._reload()
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.UserRole) == renamed.id:
                self.list.setCurrentRow(i)
                break

    def _mark_default(self) -> None:
        tid = self._selected_id()
        if not tid:
            QMessageBox.information(self, "Vorlagen", "Bitte eine Vorlage wählen.")
            return
        try:
            # Toggle: gleicher Eintrag nochmals → Standard entfernen
            if get_default_template_id() == tid:
                set_default_template_id("")
            else:
                set_default_template_id(tid)
        except AnnTemplateError as e:
            QMessageBox.warning(self, "Vorlagen", str(e))
            return
        self._reload()
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.UserRole) == tid:
                self.list.setCurrentRow(i)
                break

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
