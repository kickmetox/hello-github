"""Dialog: eigene Stempel-Bilder verwalten und als Sidecar-Stempel setzen — 1.9.0."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
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
    stamp_library_dir,
)


class StampLibraryDialog(QDialog):
    """Verwaltet Stempel-Bilder im Bibliotheksordner; optional Platzieren."""

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
        self.resize(480, 400)
        self._placed: Path | None = None
        self._items: list[StampImageInfo] = []

        layout = QVBoxLayout(self)
        self.dir_label = QLabel(f"Ordner: {stamp_library_dir()}")
        self.dir_label.setWordWrap(True)
        self.dir_label.setToolTip("Nutzer-Stempelbilder unter config/stamps/ — 1.9.0")
        layout.addWidget(self.dir_label)

        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list.itemDoubleClicked.connect(self._on_double)
        layout.addWidget(self.list)

        row = QHBoxLayout()
        self.btn_add = QPushButton("Bild hinzufügen…")
        self.btn_add.clicked.connect(self._add)
        self.btn_remove = QPushButton("Entfernen")
        self.btn_remove.clicked.connect(self._remove)
        self.btn_place = QPushButton("Als Sidecar-Stempel setzen")
        self.btn_place.setToolTip(
            "Ausgewähltes Bild als Stempel-Annotation (img:…) auf aktuelle PDF-Seite — 1.9.0"
        )
        self.btn_place.clicked.connect(self._place)
        self.btn_place.setEnabled(bool(allow_place and self.pdf_path))
        self.btn_place.setVisible(bool(allow_place))
        row.addWidget(self.btn_add)
        row.addWidget(self.btn_remove)
        row.addWidget(self.btn_place)
        row.addStretch(1)
        layout.addLayout(row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        # Close = Reject role typically
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
            self.btn_place.setEnabled(False)
            return
        self.btn_remove.setEnabled(True)
        self.btn_place.setEnabled(bool(self.pdf_path))
        for info in self._items:
            size = f"{info.size:,} B".replace(",", ".") if info.size else "—"
            item = QListWidgetItem(f"{info.name}  ({size})")
            item.setData(256, str(info.path))
            self.list.addItem(item)
        self.list.setCurrentRow(0)

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

    def _remove(self) -> None:
        sel = self.selected_images()
        if not sel:
            QMessageBox.information(self, "Stempel-Bibliothek", "Bitte Eintrag auswählen.")
            return
        reply = QMessageBox.question(
            self,
            "Stempel entfernen",
            f"{len(sel)} Bild(er) aus der Bibliothek entfernen?",
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
            QMessageBox.information(self, "Stempel-Bibliothek", f"{n} Bild(er) entfernt.")

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
