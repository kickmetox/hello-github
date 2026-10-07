"""Dialog: eigene Stempel-Bilder verwalten und als Sidecar-Stempel setzen — 1.9.1."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
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

from instantlensdoc.core.app_settings import dialog_start_dir, remember_recent_dir
from instantlensdoc.core.stamp_library import (
    STAMP_IMAGE_EXTS,
    StampImageInfo,
    add_stamp_image,
    list_stamp_images,
    place_library_stamp,
    remove_stamp_image,
    rename_stamp_image,
    set_default_stamp_name,
    stamp_library_dir,
)


class StampLibraryDialog(QDialog):
    """Verwaltet Stempel-Bilder: Umbenennen/Löschen, Vorschau, Standard — 1.9.1."""

    def __init__(
        self,
        parent=None,
        *,
        pdf_path: str | Path | None = None,
        page_index: int = 0,
        allow_place: bool = True,
    ):
        super().__init__(parent)
        self.pdf_path = Path(pdf_path) if pdf_path else None
        self.page_index = int(page_index)
        self.setWindowTitle("Stempel-Bibliothek (Bilder)")
        self.resize(560, 460)
        self._placed: Path | None = None
        self._items: list[StampImageInfo] = []

        layout = QVBoxLayout(self)
        self.dir_label = QLabel(f"Ordner: {stamp_library_dir()}")
        self.dir_label.setWordWrap(True)
        self.dir_label.setToolTip("Nutzer-Stempelbilder unter config/stamps/ — 1.9.1")
        layout.addWidget(self.dir_label)

        body = QHBoxLayout()
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list.itemDoubleClicked.connect(self._on_double)
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
        self.preview.setScaledContents(False)
        self.preview.setToolTip("Bildvorschau des ausgewählten Stempels — 1.9.1")
        prev_col.addWidget(self.preview, 1)
        self.default_label = QLabel("")
        self.default_label.setWordWrap(True)
        self.default_label.setStyleSheet("color:#555;")
        prev_col.addWidget(self.default_label)
        body.addLayout(prev_col, 1)
        layout.addLayout(body)

        row = QHBoxLayout()
        self.btn_add = QPushButton("Bild hinzufügen…")
        self.btn_add.clicked.connect(self._add)
        self.btn_rename = QPushButton("Umbenennen…")
        self.btn_rename.setToolTip("Ausgewähltes Stempel-Bild umbenennen — 1.9.1")
        self.btn_rename.clicked.connect(self._rename)
        self.btn_remove = QPushButton("Löschen")
        self.btn_remove.setToolTip("Ausgewählte Bilder aus der Bibliothek löschen — 1.9.1")
        self.btn_remove.clicked.connect(self._remove)
        self.btn_default = QPushButton("Als Standard")
        self.btn_default.setToolTip("Ausgewählten Stempel als Standard markieren (★) — 1.9.1")
        self.btn_default.clicked.connect(self._mark_default)
        self.btn_place = QPushButton("Als Sidecar-Stempel setzen")
        self.btn_place.setToolTip(
            "Ausgewähltes Bild als Stempel-Annotation (img:…) auf aktuelle PDF-Seite — 1.9.0"
        )
        self.btn_place.clicked.connect(self._place)
        self.btn_place.setEnabled(bool(allow_place and self.pdf_path))
        self.btn_place.setVisible(bool(allow_place))
        row.addWidget(self.btn_add)
        row.addWidget(self.btn_rename)
        row.addWidget(self.btn_remove)
        row.addWidget(self.btn_default)
        row.addWidget(self.btn_place)
        row.addStretch(1)
        layout.addLayout(row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        close_btn = buttons.button(QDialogButtonBox.Close)
        if close_btn:
            close_btn.clicked.connect(self.accept)
        layout.addWidget(buttons)

        self._reload()

    @property
    def placed_path(self) -> Path | None:
        return self._placed

    def selected_images(self) -> list[StampImageInfo]:
        rows = sorted({i.row() for i in self.list.selectedIndexes()})
        return [self._items[r] for r in rows if 0 <= r < len(self._items)]

    def _reload(self) -> None:
        self._items = list_stamp_images()
        self.list.clear()
        if not self._items:
            self.list.addItem("(keine Stempel-Bilder — hinzufügen…)")
            self.btn_remove.setEnabled(False)
            self.btn_rename.setEnabled(False)
            self.btn_default.setEnabled(False)
            self.btn_place.setEnabled(False)
            self.preview.setPixmap(QPixmap())
            self.preview.setText("—")
            self.default_label.setText("")
            return
        self.btn_remove.setEnabled(True)
        self.btn_rename.setEnabled(True)
        self.btn_default.setEnabled(True)
        self.btn_place.setEnabled(bool(self.pdf_path))
        for info in self._items:
            size = f"{info.size:,} B".replace(",", ".") if info.size else "—"
            star = "★ " if info.is_default else ""
            item = QListWidgetItem(f"{star}{info.name}  ({size})")
            item.setData(256, str(info.path))
            if info.is_default:
                item.setToolTip("Standard-Stempel — 1.9.1")
            self.list.addItem(item)
        self.list.setCurrentRow(0)
        self._update_preview()

    def _update_preview(self, *_args) -> None:
        sel = self.selected_images()
        if not sel:
            row = self.list.currentRow()
            if 0 <= row < len(self._items):
                sel = [self._items[row]]
        if not sel:
            self.preview.setPixmap(QPixmap())
            self.preview.setText("—")
            self.default_label.setText("")
            return
        info = sel[0]
        pix = QPixmap(str(info.path))
        if pix.isNull():
            self.preview.setPixmap(QPixmap())
            self.preview.setText("(keine Vorschau)")
        else:
            scaled = pix.scaled(
                self.preview.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.preview.setPixmap(scaled)
            self.preview.setText("")
        if info.is_default:
            self.default_label.setText(f"★ Standard: {info.name}")
        else:
            self.default_label.setText(info.name)

    def _add(self) -> None:
        start = dialog_start_dir()
        filt = "Bilder (" + " ".join(f"*{e}" for e in sorted(STAMP_IMAGE_EXTS)) + ")"
        paths, _ = QFileDialog.getOpenFileNames(self, "Stempel-Bild hinzufügen", start, filt)
        if not paths:
            return
        remember_recent_dir(paths[0])
        added = 0
        try:
            for p in paths:
                add_stamp_image(p)
                added += 1
        except Exception as e:
            QMessageBox.warning(self, "Stempel-Bibliothek", str(e))
        self._reload()
        if added:
            QMessageBox.information(self, "Stempel-Bibliothek", f"{added} Bild(er) hinzugefügt.")

    def _rename(self) -> None:
        sel = self.selected_images()
        if not sel:
            QMessageBox.information(self, "Stempel-Bibliothek", "Bitte Eintrag auswählen.")
            return
        info = sel[0]
        new_name, ok = QInputDialog.getText(
            self,
            "Stempel umbenennen",
            "Neuer Dateiname:",
            text=info.name,
        )
        if not ok:
            return
        new_name = (new_name or "").strip()
        if not new_name:
            QMessageBox.warning(self, "Stempel-Bibliothek", "Name darf nicht leer sein.")
            return
        try:
            renamed = rename_stamp_image(info.path, new_name)
        except Exception as e:
            QMessageBox.warning(self, "Stempel umbenennen", str(e))
            return
        self._reload()
        # Auswahl auf umbenanntes Item setzen
        for i, it in enumerate(self._items):
            if it.name == renamed.name:
                self.list.setCurrentRow(i)
                break

    def _remove(self) -> None:
        sel = self.selected_images()
        if not sel:
            QMessageBox.information(self, "Stempel-Bibliothek", "Bitte Eintrag auswählen.")
            return
        reply = QMessageBox.question(
            self,
            "Stempel löschen",
            f"{len(sel)} Bild(er) aus der Bibliothek löschen?",
        )
        if reply != QMessageBox.Yes:
            return
        n = 0
        for info in sel:
            try:
                if remove_stamp_image(info.path):
                    n += 1
            except Exception as e:
                QMessageBox.warning(self, "Stempel-Bibliothek", str(e))
                break
        self._reload()
        if n:
            QMessageBox.information(self, "Stempel-Bibliothek", f"{n} Bild(er) gelöscht.")

    def _mark_default(self) -> None:
        sel = self.selected_images()
        if not sel:
            QMessageBox.information(self, "Stempel-Bibliothek", "Bitte Eintrag auswählen.")
            return
        info = sel[0]
        try:
            set_default_stamp_name(info.name)
        except Exception as e:
            QMessageBox.warning(self, "Standard-Stempel", str(e))
            return
        self._reload()
        for i, it in enumerate(self._items):
            if it.name == info.name:
                self.list.setCurrentRow(i)
                break

    def _on_double(self, _item) -> None:
        if self.pdf_path and self.btn_place.isEnabled():
            self._place()

    def _place(self) -> None:
        if not self.pdf_path:
            QMessageBox.information(self, "Stempel", "Kein PDF geöffnet.")
            return
        sel = self.selected_images()
        if not sel:
            QMessageBox.information(self, "Stempel", "Bitte ein Bild auswählen.")
            return
        info = sel[0]
        try:
            placed = place_library_stamp(
                self.pdf_path,
                info.path,
                page_index=self.page_index,
            )
            from instantlensdoc.core.stamp_library import remember_stamp_usage

            remember_stamp_usage(kind="image", image=info.name)
        except Exception as e:
            QMessageBox.warning(self, "Stempel setzen", str(e))
            return
        self._placed = Path(placed)
        QMessageBox.information(
            self,
            "Stempel",
            f"Sidecar-Stempel gesetzt:\n{info.name}\n(Seite {self.page_index + 1})",
        )
        self.accept()
