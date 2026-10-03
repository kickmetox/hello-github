"""PDF zusammenführen, teilen und Seitenbereich extrahieren."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ild_pdf.pages import extract_page_range, merge_pdfs, split_pdf


class PdfToolsDialog(QDialog):
    def __init__(
        self,
        parent=None,
        *,
        initial_pdf: str | None = None,
        page_count: int | None = None,
        current_page: int = 0,
    ):
        super().__init__(parent)
        self.setWindowTitle("PDF zusammenführen / teilen / Bereich")
        self.resize(520, 460)
        self._initial_pdf = initial_pdf or ""
        self._page_count = page_count
        self._current_page = max(0, int(current_page))
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._build_merge_tab(), "Zusammenführen")
        tabs.addTab(self._build_split_tab(initial_pdf), "Teilen")
        tabs.addTab(self._build_extract_tab(initial_pdf), "Seitenbereich")
        layout.addWidget(tabs)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_merge_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(
            QLabel(
                "PDFs in Liste-Reihenfolge zu einer Datei "
                "(Mehrfachauswahl; Reihenfolge per Drag oder ▲/▼):"
            )
        )
        self.merge_list = QListWidget()
        self.merge_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.merge_list.setDefaultDropAction(Qt.MoveAction)
        self.merge_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.merge_list.setToolTip(
            "Dateien ziehen zum Neuordnen; Mehrfachauswahl beim Hinzufügen — 1.1.0"
        )
        lay.addWidget(self.merge_list)
        row = QHBoxLayout()
        btn_add = QPushButton("PDFs hinzufügen…")
        btn_add.setToolTip("Mehrere PDFs auswählen (Mehrfachauswahl)")
        btn_add.clicked.connect(self._merge_add)
        btn_up = QPushButton("▲")
        btn_down = QPushButton("▼")
        btn_up.setToolTip("Ausgewählten Eintrag nach oben")
        btn_down.setToolTip("Ausgewählten Eintrag nach unten")
        btn_up.clicked.connect(self._merge_up)
        btn_down.clicked.connect(self._merge_down)
        btn_rem = QPushButton("Entfernen")
        btn_rem.clicked.connect(self._merge_remove)
        row.addWidget(btn_add)
        row.addWidget(btn_up)
        row.addWidget(btn_down)
        row.addWidget(btn_rem)
        lay.addLayout(row)
        self.merge_dest = QLineEdit()
        pick = QPushButton("Ziel-PDF…")
        pick.clicked.connect(self._merge_pick_dest)
        dest_row = QHBoxLayout()
        dest_row.addWidget(self.merge_dest)
        dest_row.addWidget(pick)
        lay.addLayout(dest_row)
        run = QPushButton("Zusammenführen")
        run.clicked.connect(self._merge_run)
        lay.addWidget(run)
        return w

    def _build_split_tab(self, initial_pdf: str | None) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.split_src = QLineEdit(initial_pdf or "")
        pick = QPushButton("PDF…")
        pick.clicked.connect(self._split_pick_src)
        src_row = QHBoxLayout()
        src_row.addWidget(self.split_src)
        src_row.addWidget(pick)
        form.addRow("Quelle", src_row)
        self.split_out = QLineEdit()
        pick_o = QPushButton("Ordner…")
        pick_o.clicked.connect(self._split_pick_out)
        out_row = QHBoxLayout()
        out_row.addWidget(self.split_out)
        out_row.addWidget(pick_o)
        form.addRow("Ausgabeordner", out_row)
        self.split_every = QSpinBox()
        self.split_every.setRange(1, 999)
        self.split_every.setValue(1)
        form.addRow("Alle N Seiten", self.split_every)
        self.split_ranges = QLineEdit()
        self.split_ranges.setPlaceholderText("z.B. 0-2, 3-5 (0-basiert, optional)")
        form.addRow("Bereiche", self.split_ranges)
        self.split_single = QCheckBox("Jede Seite einzeln")
        form.addRow("", self.split_single)
        run = QPushButton("Teilen")
        run.clicked.connect(self._split_run)
        form.addRow(run)
        return w

    def _build_extract_tab(self, initial_pdf: str | None) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.addRow(QLabel("Seiten von–bis in ein neues PDF (1-basiert, inklusive):"))
        self.ex_src = QLineEdit(initial_pdf or "")
        pick = QPushButton("PDF…")
        pick.clicked.connect(self._ex_pick_src)
        src_row = QHBoxLayout()
        src_row.addWidget(self.ex_src)
        src_row.addWidget(pick)
        form.addRow("Quelle", src_row)
        self.ex_from = QSpinBox()
        self.ex_from.setRange(1, 99999)
        self.ex_to = QSpinBox()
        self.ex_to.setRange(1, 99999)
        n = self._page_count
        if n and n > 0:
            self.ex_from.setMaximum(n)
            self.ex_to.setMaximum(n)
            self.ex_from.setValue(min(self._current_page + 1, n))
            self.ex_to.setValue(n)
        else:
            self.ex_from.setValue(1)
            self.ex_to.setValue(1)
        form.addRow("Von Seite", self.ex_from)
        form.addRow("Bis Seite", self.ex_to)
        self.ex_dest = QLineEdit()
        if initial_pdf:
            p = Path(initial_pdf)
            self.ex_dest.setText(
                str(p.with_name(f"{p.stem}_p{self.ex_from.value()}-{self.ex_to.value()}.pdf"))
            )
        pick_d = QPushButton("Ziel…")
        pick_d.clicked.connect(self._ex_pick_dest)
        dest_row = QHBoxLayout()
        dest_row.addWidget(self.ex_dest)
        dest_row.addWidget(pick_d)
        form.addRow("Ziel-PDF", dest_row)
        run = QPushButton("Extrahieren")
        run.clicked.connect(self._ex_run)
        form.addRow(run)
        return w

    def _merge_add(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "PDFs wählen", "", "PDF (*.pdf)")
        for p in paths:
            self.merge_list.addItem(p)

    def _merge_up(self):
        row = self.merge_list.currentRow()
        if row <= 0:
            return
        item = self.merge_list.takeItem(row)
        self.merge_list.insertItem(row - 1, item)
        self.merge_list.setCurrentRow(row - 1)

    def _merge_down(self):
        row = self.merge_list.currentRow()
        if row < 0 or row >= self.merge_list.count() - 1:
            return
        item = self.merge_list.takeItem(row)
        self.merge_list.insertItem(row + 1, item)
        self.merge_list.setCurrentRow(row + 1)

    def _merge_remove(self):
        row = self.merge_list.currentRow()
        if row >= 0:
            self.merge_list.takeItem(row)

    def _merge_pick_dest(self):
        path, _ = QFileDialog.getSaveFileName(self, "Ziel-PDF", "", "PDF (*.pdf)")
        if path:
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            self.merge_dest.setText(path)

    def _merge_run(self):
        sources = [self.merge_list.item(i).text() for i in range(self.merge_list.count())]
        dest = self.merge_dest.text().strip()
        if len(sources) < 1 or not dest:
            QMessageBox.warning(self, "Zusammenführen", "Mindestens eine PDF und Ziel angeben.")
            return
        from instantlensdoc.ui.file_dialogs import confirm_overwrite_export

        if not confirm_overwrite_export(dest, self):
            return
        try:
            merge_pdfs(sources, dest)
            QMessageBox.information(self, "Zusammenführen", f"Gespeichert:\n{dest}")
        except Exception as e:
            QMessageBox.critical(self, "Zusammenführen", str(e))

    def _split_pick_src(self):
        path, _ = QFileDialog.getOpenFileName(self, "PDF", "", "PDF (*.pdf)")
        if path:
            self.split_src.setText(path)

    def _split_pick_out(self):
        path = QFileDialog.getExistingDirectory(self, "Ausgabeordner")
        if path:
            self.split_out.setText(path)

    def _parse_ranges(self, text: str) -> list[tuple[int, int]] | None:
        text = text.strip()
        if not text:
            return None
        out: list[tuple[int, int]] = []
        for part in text.split(","):
            part = part.strip()
            if "-" in part:
                a, b = part.split("-", 1)
                out.append((int(a.strip()), int(b.strip())))
            else:
                i = int(part)
                out.append((i, i))
        return out

    def _split_run(self):
        src = self.split_src.text().strip()
        out = self.split_out.text().strip()
        if not src or not out:
            QMessageBox.warning(self, "Teilen", "Quelle und Ausgabeordner angeben.")
            return
        try:
            ranges = self._parse_ranges(self.split_ranges.text())
            written = split_pdf(
                src,
                out,
                every_n=None if ranges or self.split_single.isChecked() else self.split_every.value(),
                ranges=ranges,
                single_pages=self.split_single.isChecked(),
            )
            QMessageBox.information(
                self,
                "Teilen",
                f"{len(written)} Datei(en) erstellt in\n{out}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Teilen", str(e))

    def _ex_pick_src(self):
        path, _ = QFileDialog.getOpenFileName(self, "PDF", "", "PDF (*.pdf)")
        if path:
            self.ex_src.setText(path)
            try:
                import pikepdf

                with pikepdf.open(path) as pdf:
                    n = len(pdf.pages)
                self.ex_from.setMaximum(max(1, n))
                self.ex_to.setMaximum(max(1, n))
                self.ex_to.setValue(n)
            except Exception:
                pass

    def _ex_pick_dest(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Ziel-PDF", self.ex_dest.text(), "PDF (*.pdf)"
        )
        if path:
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            self.ex_dest.setText(path)

    def _ex_run(self):
        src = self.ex_src.text().strip()
        dest = self.ex_dest.text().strip()
        if not src or not dest:
            QMessageBox.warning(self, "Seitenbereich", "Quelle und Ziel-PDF angeben.")
            return
        from instantlensdoc.ui.file_dialogs import confirm_overwrite_export

        if not confirm_overwrite_export(dest, self):
            return
        try:
            out = extract_page_range(
                src,
                dest,
                self.ex_from.value(),
                self.ex_to.value(),
                one_based=True,
            )
            QMessageBox.information(
                self,
                "Seitenbereich",
                f"Extrahiert: Seiten {self.ex_from.value()}–{self.ex_to.value()}\n{out}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Seitenbereich", str(e))
