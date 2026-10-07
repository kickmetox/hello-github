"""Seitenmanagement: ordnen, einfügen, drehen, löschen, Seiten aus anderen PDFs — 2.6.5."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from ild_pdf.pages import page_count as pdf_page_count, preview_page_range_count


class PageManageDialog(QDialog):
    """
    Zentrale Seitenverwaltung für das aktuelle PDF.

    Drag-and-Drop / ▲▼ Neuordnen · drehen · leere Seite · löschen · duplizieren ·
    Seiten aus anderem PDF einfügen.
    """

    def __init__(self, pdf_view, parent=None):
        super().__init__(parent)
        self.pdf_view = pdf_view
        self.setWindowTitle("Seitenmanagement")
        self.setWindowModality(Qt.WindowModal)
        self.setObjectName("pageManageDialog")
        self.resize(460, 560)
        self.setAccessibleName("Seitenmanagement")
        self.setAccessibleDescription(
            "Seiten per Drag-and-Drop neu anordnen, einfügen, drehen, löschen "
            "oder aus anderen PDFs zusammenfügen — 2.6.5"
        )

        layout = QVBoxLayout(self)
        self.hint = QLabel(
            "Seiten per Drag-and-Drop oder ▲/▼ neu anordnen. "
            "Auswahl: drehen / einfügen / löschen / aus anderem PDF. — 2.6.5"
        )
        self.hint.setWordWrap(True)
        self.hint.setObjectName("pageManageHint")
        layout.addWidget(self.hint)

        self.list = QListWidget()
        self.list.setObjectName("pageManageList")
        self.list.setDragDropMode(QAbstractItemView.InternalMove)
        self.list.setDefaultDropAction(Qt.MoveAction)
        self.list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list.setAlternatingRowColors(True)
        self.list.setAccessibleName("Seitenliste")
        self.list.setAccessibleDescription(
            "Drag-and-Drop zum Umsortieren; Mehrfachauswahl für Batch-Aktionen"
        )
        layout.addWidget(self.list, 1)

        move_row = QHBoxLayout()
        self.btn_up = QPushButton("▲ Hoch")
        self.btn_up.setObjectName("pageManageUp")
        self.btn_up.setToolTip("Ausgewählte Seite nach oben")
        self.btn_up.clicked.connect(self._move_up)
        self.btn_down = QPushButton("▼ Runter")
        self.btn_down.setObjectName("pageManageDown")
        self.btn_down.setToolTip("Ausgewählte Seite nach unten")
        self.btn_down.clicked.connect(self._move_down)
        self.btn_apply_order = QPushButton("Reihenfolge anwenden")
        self.btn_apply_order.setObjectName("pageManageApplyOrder")
        self.btn_apply_order.setToolTip("Aktuelle Listenreihenfolge speichern (Ctrl+Z rückgängig)")
        self.btn_apply_order.clicked.connect(self._apply_order)
        move_row.addWidget(self.btn_up)
        move_row.addWidget(self.btn_down)
        move_row.addWidget(self.btn_apply_order, 1)
        layout.addLayout(move_row)

        op_row = QHBoxLayout()
        self.btn_rot_ccw = QPushButton("⟲ −90°")
        self.btn_rot_ccw.setObjectName("pageManageRotateCcw")
        self.btn_rot_ccw.setToolTip("Auswahl 90° gegen den Uhrzeigersinn drehen")
        self.btn_rot_ccw.clicked.connect(lambda: self._rotate_selected(-90))
        self.btn_rot_cw = QPushButton("⟳ +90°")
        self.btn_rot_cw.setObjectName("pageManageRotateCw")
        self.btn_rot_cw.setToolTip("Auswahl 90° im Uhrzeigersinn drehen")
        self.btn_rot_cw.clicked.connect(lambda: self._rotate_selected(90))
        self.btn_blank = QPushButton("Leere Seite")
        self.btn_blank.setObjectName("pageManageBlank")
        self.btn_blank.setToolTip("Leere Seite nach Auswahl / aktueller Seite einfügen")
        self.btn_blank.clicked.connect(self._insert_blank)
        self.btn_dup = QPushButton("Duplizieren")
        self.btn_dup.setObjectName("pageManageDup")
        self.btn_dup.setToolTip("Ausgewählte Seite(n) duplizieren")
        self.btn_dup.clicked.connect(self._duplicate_selected)
        self.btn_del = QPushButton("Löschen")
        self.btn_del.setObjectName("pageManageDelete")
        self.btn_del.setToolTip("Ausgewählte Seite(n) löschen (mind. eine bleibt)")
        self.btn_del.clicked.connect(self._delete_selected)
        for b in (
            self.btn_rot_ccw,
            self.btn_rot_cw,
            self.btn_blank,
            self.btn_dup,
            self.btn_del,
        ):
            op_row.addWidget(b)
        layout.addLayout(op_row)

        merge_row = QHBoxLayout()
        self.btn_insert_pdf = QPushButton("Seiten aus PDF einfügen…")
        self.btn_insert_pdf.setObjectName("pageManageInsertPdf")
        self.btn_insert_pdf.setToolTip(
            "Seiten aus einem anderen PDF an gewählter Position einfügen — 2.6.5"
        )
        self.btn_insert_pdf.clicked.connect(self._insert_from_pdf)
        self.btn_goto = QPushButton("Zur Seite")
        self.btn_goto.setObjectName("pageManageGoto")
        self.btn_goto.setToolTip("Viewer zur ausgewählten Seite springen")
        self.btn_goto.clicked.connect(self._goto_selected)
        merge_row.addWidget(self.btn_insert_pdf, 1)
        merge_row.addWidget(self.btn_goto)
        layout.addLayout(merge_row)

        self.status = QLabel("")
        self.status.setObjectName("pageManageStatus")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        close_btn = buttons.button(QDialogButtonBox.Close)
        if close_btn is not None:
            close_btn.setText("Schließen")
        layout.addWidget(buttons)

        self._reload_list()
        if self.list.count():
            cur = int(getattr(pdf_view, "page_index", 0) or 0)
            self.list.setCurrentRow(max(0, min(cur, self.list.count() - 1)))

    def _pdf_path(self) -> Path | None:
        p = getattr(self.pdf_view, "pdf_path", None)
        return Path(p) if p else None

    def _reload_list(self, *, select: int | None = None) -> None:
        self.list.clear()
        n = int(getattr(self.pdf_view, "page_count", 0) or 0)
        for i in range(n):
            label = f"Seite {i + 1}"
            try:
                pl = self.pdf_view.page_label(i) if hasattr(self.pdf_view, "page_label") else ""
                if pl and str(pl) != str(i + 1):
                    label = f"Seite {i + 1} ({pl})"
            except Exception:
                pass
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, i)
            self.list.addItem(item)
        if select is not None and 0 <= select < self.list.count():
            self.list.setCurrentRow(select)
        self.status.setText(f"{n} Seite(n)")

    def current_order(self) -> list[int]:
        order: list[int] = []
        for i in range(self.list.count()):
            order.append(int(self.list.item(i).data(Qt.UserRole)))
        return order

    def _selected_indices(self) -> list[int]:
        rows = sorted({i.row() for i in self.list.selectedIndexes()})
        order = self.current_order()
        out: list[int] = []
        for r in rows:
            if 0 <= r < len(order):
                out.append(order[r])
        return out

    def _move_up(self) -> None:
        row = self.list.currentRow()
        if row <= 0:
            return
        item = self.list.takeItem(row)
        self.list.insertItem(row - 1, item)
        self.list.setCurrentRow(row - 1)

    def _move_down(self) -> None:
        row = self.list.currentRow()
        if row < 0 or row >= self.list.count() - 1:
            return
        item = self.list.takeItem(row)
        self.list.insertItem(row + 1, item)
        self.list.setCurrentRow(row + 1)

    def _apply_order(self) -> None:
        if not self._pdf_path():
            return
        order = self.current_order()
        if not order:
            return
        if order == list(range(len(order))):
            self.status.setText("Reihenfolge unverändert")
            return
        ok = self.pdf_view.apply_page_order(order)
        if ok:
            self._reload_list(select=0)
            self.status.setText("Reihenfolge angewendet (Ctrl+Z rückgängig)")
        else:
            self.status.setText("Reihenfolge nicht geändert")

    def _ensure_order_synced(self) -> bool:
        """Vor strukturellen Ops: ausstehende Listen-Reorder anwenden."""
        order = self.current_order()
        n = int(getattr(self.pdf_view, "page_count", 0) or 0)
        if len(order) != n:
            self._reload_list()
            return True
        if order != list(range(n)):
            if not self.pdf_view.apply_page_order(order):
                return False
            self._reload_list()
        return True

    def _rotate_selected(self, degrees: int) -> None:
        if not self._ensure_order_synced():
            return
        pages = self._selected_indices()
        if not pages:
            cur = int(getattr(self.pdf_view, "page_index", 0) or 0)
            pages = [cur]
        n = 0
        if hasattr(self.pdf_view, "rotate_many"):
            n = int(self.pdf_view.rotate_many(pages, degrees) or 0)
        else:
            for idx in pages:
                if self.pdf_view.rotate_at(idx, degrees):
                    n += 1
        self._reload_list(select=pages[0] if pages else 0)
        self.status.setText(f"{n} Seite(n) gedreht ({degrees:+d}°)")

    def _insert_blank(self) -> None:
        if not self._ensure_order_synced():
            return
        pages = self._selected_indices()
        if pages:
            self.pdf_view.page_index = pages[-1]
        self.pdf_view.insert_blank_after_current()
        new_idx = int(getattr(self.pdf_view, "page_index", 0) or 0)
        self._reload_list(select=new_idx)
        self.status.setText(f"Leere Seite {new_idx + 1} eingefügt")

    def _duplicate_selected(self) -> None:
        if not self._ensure_order_synced():
            return
        pages = self._selected_indices()
        if not pages:
            pages = [int(getattr(self.pdf_view, "page_index", 0) or 0)]
        n = 0
        if hasattr(self.pdf_view, "duplicate_many"):
            n = int(self.pdf_view.duplicate_many(pages) or 0)
        else:
            for idx in sorted(pages, reverse=True):
                if self.pdf_view.duplicate_at(idx):
                    n += 1
        self._reload_list(select=int(getattr(self.pdf_view, "page_index", 0) or 0))
        self.status.setText(f"{n} Seite(n) dupliziert")

    def _delete_selected(self) -> None:
        if not self._ensure_order_synced():
            return
        pages = self._selected_indices()
        if not pages:
            pages = [int(getattr(self.pdf_view, "page_index", 0) or 0)]
        n = 0
        if hasattr(self.pdf_view, "delete_many"):
            n = int(self.pdf_view.delete_many(pages, confirm=True) or 0)
        else:
            for idx in sorted(pages, reverse=True):
                if self.pdf_view.delete_at(idx, confirm=True):
                    n += 1
        self._reload_list(select=int(getattr(self.pdf_view, "page_index", 0) or 0))
        if n:
            self.status.setText(f"{n} Seite(n) gelöscht")

    def _goto_selected(self) -> None:
        pages = self._selected_indices()
        if not pages:
            return
        # Listenreihenfolge kann von PDF abweichen — zur Anzeige-Zeile springen nur wenn synced
        order = self.current_order()
        n = int(getattr(self.pdf_view, "page_count", 0) or 0)
        if order == list(range(n)):
            self.pdf_view.goto_page(pages[0])
            self.status.setText(f"Seite {pages[0] + 1}")
        else:
            self.status.setText("Zuerst „Reihenfolge anwenden“, dann Zur Seite")

    def _insert_from_pdf(self) -> None:
        if not self._pdf_path():
            QMessageBox.information(self, "Seiten einfügen", "Kein PDF geöffnet.")
            return
        if not self._ensure_order_synced():
            return
        start = str(self._pdf_path().parent)
        path, _ = QFileDialog.getOpenFileName(
            self,
            "PDF mit Seiten wählen",
            start,
            "PDF (*.pdf)",
        )
        if not path:
            return
        src = Path(path)
        try:
            src_n = pdf_page_count(src)
        except Exception as e:
            QMessageBox.warning(self, "Seiten einfügen", str(e))
            return
        if src_n < 1:
            QMessageBox.warning(self, "Seiten einfügen", "Quell-PDF hat keine Seiten.")
            return
        default_spec = f"1-{src_n}" if src_n > 1 else "1"
        spec, ok = QInputDialog.getText(
            self,
            "Seiten aus PDF einfügen",
            f"Seitenbereiche aus „{src.name}“ (1…{src_n}), z. B. 1-3,5:",
            text=default_spec,
        )
        if not ok:
            return
        spec = (spec or "").strip()
        if not spec:
            return
        count, _ranges, err = preview_page_range_count(spec, src_n, one_based=True)
        if err:
            QMessageBox.warning(self, "Seiten einfügen", err)
            return
        if count < 1:
            QMessageBox.warning(self, "Seiten einfügen", "Keine Seiten ausgewählt.")
            return
        dest_n = int(getattr(self.pdf_view, "page_count", 0) or 0)
        pages = self._selected_indices()
        default_at = (pages[-1] + 1) if pages else dest_n
        at, ok2 = QInputDialog.getInt(
            self,
            "Einfügeposition",
            f"Einfügen vor Seite (1…{dest_n + 1}; {dest_n + 1} = Ans Ende):",
            max(1, min(default_at + 1, dest_n + 1)),
            1,
            dest_n + 1,
        )
        if not ok2:
            return
        at_index = int(at) - 1  # 0-basiert; dest_n = Ans Ende
        try:
            inserted = self.pdf_view.insert_pages_from_other_pdf(
                src,
                page_spec=spec,
                at_index=at_index,
                one_based=True,
            )
        except Exception as e:
            QMessageBox.warning(self, "Seiten einfügen", str(e))
            return
        sel = inserted[0] if inserted else at_index
        self._reload_list(select=sel)
        self.status.setText(
            f"{len(inserted)} Seite(n) aus „{src.name}“ eingefügt "
            f"(Bereich {spec})"
        )


class InsertPagesFromPdfDialog(QDialog):
    """Optionaler Form-Dialog für spezifizierte Einfüge-Parameter (Tests/API)."""

    def __init__(self, parent=None, *, source_pages: int = 1, dest_pages: int = 1):
        super().__init__(parent)
        self.setWindowTitle("Seiten aus PDF einfügen")
        self.setObjectName("insertPagesFromPdfDialog")
        self.resize(420, 200)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.spec_edit = QLineEdit(f"1-{source_pages}" if source_pages > 1 else "1")
        self.spec_edit.setObjectName("insertPagesSpec")
        self.spec_edit.setPlaceholderText("1-3,5")
        form.addRow("Seitenbereich", self.spec_edit)
        self.at_spin = QSpinBox()
        self.at_spin.setObjectName("insertPagesAt")
        self.at_spin.setRange(1, max(1, dest_pages + 1))
        self.at_spin.setValue(dest_pages + 1)
        form.addRow("Einfügen vor Seite", self.at_spin)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def page_spec(self) -> str:
        return (self.spec_edit.text() or "").strip()

    def at_index_zero_based(self) -> int:
        return int(self.at_spin.value()) - 1
