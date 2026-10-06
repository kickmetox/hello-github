"""Formatvorlagen anlegen, ändern, löschen — Word-ähnlich."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from instantlensdoc.core.doc_styles import (
    StyleSpec,
    all_styles,
    delete_custom_style,
    get_style,
    upsert_custom_style,
)


class StyleManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Formatvorlagen")
        self.setObjectName("ildStyleManagerDialog")
        self.resize(480, 360)
        self._changed = False
        root = QHBoxLayout(self)
        self.list = QListWidget()
        self.list.setObjectName("ildStyleList")
        root.addWidget(self.list, 1)
        form_host = QVBoxLayout()
        form = QFormLayout()
        self.name = QLineEdit()
        self.name.setObjectName("ildStyleName")
        form.addRow("Name", self.name)
        self.size = QDoubleSpinBox()
        self.size.setRange(6.0, 72.0)
        self.size.setValue(11.0)
        form.addRow("Größe (pt)", self.size)
        self.bold = QCheckBox("Fett")
        self.italic = QCheckBox("Kursiv")
        form.addRow(self.bold)
        form.addRow(self.italic)
        self.align = QComboBox()
        self.align.addItem("Links", "left")
        self.align.addItem("Zentriert", "center")
        self.align.addItem("Rechts", "right")
        self.align.addItem("Blocksatz", "justify")
        form.addRow("Ausrichtung", self.align)
        form_host.addLayout(form)
        row = QHBoxLayout()
        btn_new = QPushButton("Neu")
        btn_new.setObjectName("ildStyleNew")
        btn_new.clicked.connect(self._new)
        btn_save = QPushButton("Ändern")
        btn_save.setObjectName("ildStyleSave")
        btn_save.clicked.connect(self._save)
        btn_del = QPushButton("Löschen")
        btn_del.setObjectName("ildStyleDelete")
        btn_del.clicked.connect(self._delete)
        row.addWidget(btn_new)
        row.addWidget(btn_save)
        row.addWidget(btn_del)
        form_host.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        form_host.addWidget(buttons)
        root.addLayout(form_host, 2)
        self.list.currentItemChanged.connect(self._load_item)
        self._reload()

    def styles_changed(self) -> bool:
        return bool(self._changed)

    def _reload(self) -> None:
        self.list.clear()
        for spec in all_styles():
            item = QListWidgetItem(spec.label)
            item.setData(32, spec.id)
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)

    def _current_id(self) -> str:
        it = self.list.currentItem()
        if it is None:
            return ""
        return str(it.data(32) or "")

    def _load_item(self, *_args) -> None:
        sid = self._current_id()
        if not sid:
            return
        spec = get_style(sid)
        self.name.setText(spec.label)
        self.size.setValue(float(spec.size))
        self.bold.setChecked(bool(spec.bold))
        self.italic.setChecked(bool(spec.italic))
        idx = max(0, self.align.findData(spec.align))
        self.align.setCurrentIndex(idx)
        builtin = bool(spec.builtin)
        self.name.setReadOnly(builtin)

    def _new(self) -> None:
        label = (self.name.text() or "Neue Vorlage").strip()
        sid = "".join(ch.lower() if ch.isalnum() else "_" for ch in label).strip("_") or "custom"
        spec = StyleSpec(
            id=sid,
            label=label,
            word_name=label,
            size=float(self.size.value()),
            bold=self.bold.isChecked(),
            italic=self.italic.isChecked(),
            align=str(self.align.currentData() or "left"),
            builtin=False,
        )
        upsert_custom_style(spec)
        self._changed = True
        self._reload()

    def _save(self) -> None:
        sid = self._current_id()
        if not sid:
            return
        spec = get_style(sid)
        if spec.builtin:
            QMessageBox.information(
                self, "Formatvorlagen", "Eingebaute Vorlagen können nicht überschrieben werden."
            )
            return
        spec.label = self.name.text().strip() or spec.label
        spec.word_name = spec.label
        spec.size = float(self.size.value())
        spec.bold = self.bold.isChecked()
        spec.italic = self.italic.isChecked()
        spec.align = str(self.align.currentData() or "left")
        upsert_custom_style(spec)
        self._changed = True
        self._reload()

    def _delete(self) -> None:
        sid = self._current_id()
        if not sid:
            return
        if not delete_custom_style(sid):
            QMessageBox.information(
                self, "Formatvorlagen", "Eingebaute Vorlagen können nicht gelöscht werden."
            )
            return
        self._changed = True
        self._reload()
