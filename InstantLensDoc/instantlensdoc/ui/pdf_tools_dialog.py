"""PDF zusammenführen, teilen und Seitenbereich extrahieren."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QCursor, QDesktopServices, QImage, QPixmap
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
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class SplitPathLogEdit(QPlainTextEdit):
    """Pfad-Log: Doppelklick öffnet Datei/Ordner — 1.2.4."""

    path_activate = Signal()

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        self.path_activate.emit()

from ild_pdf.pages import (
    extract_by_page_spec,
    merge_pdfs,
    parse_page_ranges,
    preview_page_range_count,
    split_pdf,
)


def _pil_to_qpixmap(img) -> QPixmap:
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    data = img.tobytes("raw", img.mode)
    fmt = QImage.Format_RGBA8888 if img.mode == "RGBA" else QImage.Format_RGB888
    qimg = QImage(data, img.width, img.height, fmt).copy()
    return QPixmap.fromImage(qimg)


class MergeListWidget(QListWidget):
    """Liste mit InternalMove + externe PDF-Dateien per Drag&Drop — 1.1.2."""

    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

    def _pdf_paths_from_mime(self, mime) -> list[str]:
        paths: list[str] = []
        if mime is None or not mime.hasUrls():
            return paths
        for url in mime.urls():
            if not url.isLocalFile():
                continue
            path = url.toLocalFile()
            if path and path.lower().endswith(".pdf"):
                paths.append(path)
        return paths

    def dragEnterEvent(self, event):
        if self._pdf_paths_from_mime(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if self._pdf_paths_from_mime(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        paths = self._pdf_paths_from_mime(event.mimeData())
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
            return
        super().dropEvent(event)


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
        self.resize(560, 520)
        self._initial_pdf = initial_pdf or ""
        self._page_count = page_count
        self._current_page = max(0, int(current_page))
        self._preview_path: str | None = None
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
                "(Drag&Drop Dateien / Neuordnen; Doppelklick entfernt):"
            )
        )
        list_row = QHBoxLayout()
        self.merge_list = MergeListWidget()
        self.merge_list.setToolTip(
            "PDFs per Drag&Drop in die Liste ziehen; intern neuordnen; "
            "Doppelklick entfernt; Duplikate werden gewarnt — 1.1.2"
        )
        self.merge_list.itemDoubleClicked.connect(self._merge_double_click)
        self.merge_list.files_dropped.connect(self._merge_add_paths)
        self.merge_list.currentItemChanged.connect(
            lambda _cur, _prev: self._merge_update_preview()
        )
        model = self.merge_list.model()
        if model is not None:
            model.rowsInserted.connect(lambda *_: self._merge_update_pages_sum())
            model.rowsRemoved.connect(lambda *_: self._merge_update_pages_sum())
            model.rowsInserted.connect(lambda *_: self._merge_update_preview())
            model.rowsRemoved.connect(lambda *_: self._merge_update_preview())
        list_row.addWidget(self.merge_list, 1)

        preview_col = QVBoxLayout()
        preview_col.addWidget(QLabel("Vorschau (1. Seite):"))
        self.merge_preview = QLabel()
        self.merge_preview.setAlignment(Qt.AlignCenter)
        self.merge_preview.setMinimumSize(140, 180)
        self.merge_preview.setMaximumWidth(180)
        self.merge_preview.setStyleSheet(
            "QLabel { background: #f0f0f0; border: 1px solid #bbb; }"
        )
        self.merge_preview.setToolTip(
            "Klick öffnet Datei als Readonly-Vorschau (Banner + Bearbeiten) — 1.1.5"
        )
        self.merge_preview.setText("Keine Auswahl")
        self.merge_preview.setWordWrap(True)
        self.merge_preview.setCursor(QCursor(Qt.PointingHandCursor))
        self.merge_preview.mousePressEvent = (  # type: ignore[method-assign]
            self._merge_preview_clicked
        )
        preview_col.addWidget(self.merge_preview)
        preview_col.addStretch(1)
        list_row.addLayout(preview_col)
        lay.addLayout(list_row)

        self.merge_pages_label = QLabel("Seiten gesamt: 0")
        self.merge_pages_label.setToolTip(
            "Summe der Seitenzahlen aller PDFs in der Liste — 1.1.1"
        )
        lay.addWidget(self.merge_pages_label)

        # Readonly-Vorschau schließen — Sync mit Settings — 1.1.7–1.1.9
        from instantlensdoc.core.app_settings import (
            MERGE_CLOSE_PREVIEW_TOOLTIP,
            get_merge_close_preview_on_edit,
            set_merge_close_preview_on_edit,
        )

        self.merge_close_preview = QCheckBox(
            "Readonly-Vorschau bei „Zum Bearbeiten öffnen“ schließen"
        )
        self.merge_close_preview.setChecked(get_merge_close_preview_on_edit())
        self.merge_close_preview.setToolTip(MERGE_CLOSE_PREVIEW_TOOLTIP)
        self.merge_close_preview.toggled.connect(
            lambda checked: set_merge_close_preview_on_edit(bool(checked))
        )
        lay.addWidget(self.merge_close_preview)

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
        btn_rem.setToolTip("Ausgewählte Einträge entfernen")
        btn_rem.clicked.connect(self._merge_remove)
        btn_rem_all = QPushButton("Alle entfernen")
        btn_rem_all.setToolTip("Gesamte Liste leeren — 1.1.1")
        btn_rem_all.clicked.connect(self._merge_remove_all)
        row.addWidget(btn_add)
        row.addWidget(btn_up)
        row.addWidget(btn_down)
        row.addWidget(btn_rem)
        row.addWidget(btn_rem_all)
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
        self.split_ranges.setPlaceholderText(
            "z.B. 1-3,5,8-10 (1-basiert, optional) — 1.2.1"
        )
        self.split_ranges.setToolTip(
            "Kommagetrennte Seiten/Bereiche (1-basiert), z. B. 1-3,5,8-10 — "
            "überschreibt „Alle N Seiten“. Fehlerhafte Bereiche: klare DE-Meldung — 1.2.1"
        )
        self.split_ranges.textChanged.connect(self._split_update_preview)
        self.split_src.textChanged.connect(self._split_update_preview)
        form.addRow("Bereiche", self.split_ranges)
        self.split_preview = QLabel("Vorschau: —")
        self.split_preview.setWordWrap(True)
        self.split_preview.setToolTip(
            "Anzahl Seiten und Bereiche laut aktueller Eingabe — 1.2.1"
        )
        form.addRow("Vorschau", self.split_preview)
        self.split_single = QCheckBox("Jede Seite einzeln")
        form.addRow("", self.split_single)
        from instantlensdoc.core.app_settings import (
            get_split_open_tabs,
            set_split_open_tabs,
        )

        self.split_open_tabs = QCheckBox("Erzeugte Dateien in Tabs öffnen")
        self.split_open_tabs.setChecked(get_split_open_tabs())
        self.split_open_tabs.setToolTip(
            "Nach erfolgreichem Teilen die neuen PDFs optional in Tabs öffnen "
            "(Einstellung wird gespeichert) — 1.2.3"
        )
        self.split_open_tabs.toggled.connect(
            lambda checked: set_split_open_tabs(bool(checked))
        )
        form.addRow("", self.split_open_tabs)
        self.split_log = SplitPathLogEdit()
        self.split_log.setReadOnly(True)
        self.split_log.setMaximumHeight(110)
        self.split_log.setPlaceholderText(
            "Noch kein Log — nach dem Teilen erscheinen Pfade hier. "
            "Doppelklick öffnet Datei/Ordner."
        )
        self.split_log.setToolTip(
            "Liste der nach dem Teilen erzeugten Dateipfade. "
            "Doppelklick auf eine Zeile öffnet Datei bzw. Ordner — 1.2.4"
        )
        self.split_log.path_activate.connect(self._split_open_log_path)
        form.addRow("Pfad-Log", self.split_log)
        log_btns = QHBoxLayout()
        btn_copy_log = QPushButton("Log kopieren")
        btn_copy_log.setToolTip("Pfad-Log in die Zwischenablage kopieren — 1.2.3")
        btn_copy_log.clicked.connect(self._split_copy_log)
        btn_save_log = QPushButton("Log als TXT…")
        btn_save_log.setToolTip("Pfad-Log als Textdatei speichern — 1.2.3")
        btn_save_log.clicked.connect(self._split_save_log_txt)
        log_btns.addWidget(btn_copy_log)
        log_btns.addWidget(btn_save_log)
        log_btns.addStretch()
        form.addRow("", log_btns)
        run = QPushButton("Teilen")
        run.clicked.connect(self._split_run)
        form.addRow(run)
        self._split_update_preview()
        return w

    def _build_extract_tab(self, initial_pdf: str | None) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.addRow(
            QLabel(
                "Seitenbereiche extrahieren (1-basiert), z. B. <b>1-3,5,8-10</b> — 1.2.1"
            )
        )
        self.ex_src = QLineEdit(initial_pdf or "")
        pick = QPushButton("PDF…")
        pick.clicked.connect(self._ex_pick_src)
        src_row = QHBoxLayout()
        src_row.addWidget(self.ex_src)
        src_row.addWidget(pick)
        form.addRow("Quelle", src_row)
        self.ex_spec = QLineEdit()
        n = self._page_count
        if n and n > 0:
            cur = min(self._current_page + 1, n)
            self.ex_spec.setText(f"{cur}-{n}" if cur < n else str(cur))
        else:
            self.ex_spec.setText("1")
        self.ex_spec.setPlaceholderText("z.B. 1-3,5,8-10")
        self.ex_spec.setToolTip(
            "Kommagetrennte Seiten und Bereiche (1-basiert, inklusive). "
            "Leer = Von–Bis-Spinboxen nutzen. Fehlerhafte Bereiche: klare DE-Meldung — 1.2.1"
        )
        self.ex_spec.textChanged.connect(self._ex_update_preview)
        self.ex_src.textChanged.connect(self._ex_update_preview)
        form.addRow("Seitenbereiche", self.ex_spec)
        self.ex_preview = QLabel("Vorschau: —")
        self.ex_preview.setWordWrap(True)
        self.ex_preview.setToolTip(
            "Anzahl Seiten und Bereiche laut aktueller Eingabe — 1.2.1"
        )
        form.addRow("Vorschau", self.ex_preview)
        self.ex_from = QSpinBox()
        self.ex_from.setRange(1, 99999)
        self.ex_to = QSpinBox()
        self.ex_to.setRange(1, 99999)
        if n and n > 0:
            self.ex_from.setMaximum(n)
            self.ex_to.setMaximum(n)
            self.ex_from.setValue(min(self._current_page + 1, n))
            self.ex_to.setValue(n)
        else:
            self.ex_from.setValue(1)
            self.ex_to.setValue(1)
        self.ex_from.valueChanged.connect(self._ex_update_preview)
        self.ex_to.valueChanged.connect(self._ex_update_preview)
        form.addRow("Von Seite (Fallback)", self.ex_from)
        form.addRow("Bis Seite (Fallback)", self.ex_to)
        self.ex_one_per_range = QCheckBox("Eine Datei pro Bereich")
        self.ex_one_per_range.setToolTip(
            "Aktiv: jeder Token (z. B. 1-3 und 5) → eigene PDF-Datei im Ordner — 1.2.0"
        )
        form.addRow("", self.ex_one_per_range)
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
        form.addRow("Ziel-PDF / Ordner", dest_row)
        run = QPushButton("Extrahieren")
        run.clicked.connect(self._ex_run)
        form.addRow(run)
        self._ex_update_preview()
        return w

    def _merge_existing_paths(self) -> set[str]:
        existing: set[str] = set()
        for i in range(self.merge_list.count()):
            item = self.merge_list.item(i)
            if item is None:
                continue
            existing.add(str(Path(item.text()).resolve()) if item.text() else "")
            existing.add(item.text())
        existing.discard("")
        return existing

    def _merge_add_paths(self, paths: list[str], *, warn_duplicates: bool = True) -> int:
        """Pfade hinzufügen; Duplikate warnen und überspringen — 1.1.2."""
        if not paths:
            return 0
        existing = self._merge_existing_paths()
        dups: list[str] = []
        added = 0
        for p in paths:
            p = str(p)
            if not p.lower().endswith(".pdf"):
                continue
            try:
                key = str(Path(p).resolve())
            except Exception:
                key = p
            if p in existing or key in existing:
                dups.append(p)
                continue
            self.merge_list.addItem(p)
            existing.add(p)
            existing.add(key)
            added += 1
        if warn_duplicates and dups:
            shown = "\n".join(Path(d).name for d in dups[:8])
            more = f"\n… (+{len(dups) - 8})" if len(dups) > 8 else ""
            QMessageBox.warning(
                self,
                "Duplikat",
                f"{len(dups)} Duplikat(e) übersprungen (bereits in der Liste):\n"
                f"{shown}{more}",
            )
        self._merge_update_pages_sum()
        if added and self.merge_list.currentRow() < 0 and self.merge_list.count() > 0:
            self.merge_list.setCurrentRow(self.merge_list.count() - 1)
        else:
            self._merge_update_preview()
        return added

    def _merge_add(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "PDFs wählen", "", "PDF (*.pdf)")
        self._merge_add_paths(list(paths))

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
        rows = sorted(
            {i.row() for i in self.merge_list.selectedIndexes()},
            reverse=True,
        )
        if not rows:
            row = self.merge_list.currentRow()
            if row >= 0:
                rows = [row]
        for row in rows:
            self.merge_list.takeItem(row)
        self._merge_update_pages_sum()

    def _merge_double_click(self, item):
        """Doppelklick entfernt den Eintrag — 1.1.1."""
        row = self.merge_list.row(item)
        if row >= 0:
            self.merge_list.takeItem(row)
            self._merge_update_pages_sum()

    def _merge_remove_all(self):
        """Gesamte Merge-Liste leeren — 1.1.1."""
        self.merge_list.clear()
        self._merge_update_pages_sum()

    def _merge_page_count(self, path: str) -> int:
        try:
            import pikepdf

            with pikepdf.open(path) as pdf:
                return len(pdf.pages)
        except Exception:
            return 0

    def _merge_update_pages_sum(self):
        total = 0
        for i in range(self.merge_list.count()):
            item = self.merge_list.item(i)
            if item is None:
                continue
            total += self._merge_page_count(item.text())
        n_files = self.merge_list.count()
        self.merge_pages_label.setText(
            f"Seiten gesamt: {total}"
            + (f" ({n_files} Datei{'en' if n_files != 1 else ''})" if n_files else "")
        )

    def _merge_update_preview(self):
        """Thumbnail der ersten Seite der markierten Datei — 1.1.3/1.1.4."""
        item = self.merge_list.currentItem()
        if item is None or not (item.text() or "").strip():
            self._preview_path = None
            self.merge_preview.setPixmap(QPixmap())
            self.merge_preview.setText("Keine Auswahl")
            self.merge_preview.setToolTip(
                "Klick öffnet Datei als Readonly-Vorschau (Banner + Bearbeiten) — 1.1.5"
            )
            return
        path = item.text().strip()
        if (
            path == self._preview_path
            and self.merge_preview.pixmap() is not None
            and not self.merge_preview.pixmap().isNull()
        ):
            return
        self._preview_path = path
        try:
            from ild_pdf.render import render_page

            img = render_page(path, page_index=0, scale=0.35, use_cache=True)
            pm = _pil_to_qpixmap(img).scaled(
                160, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.merge_preview.setPixmap(pm)
            self.merge_preview.setText("")
            self.merge_preview.setToolTip(
                f"Klick: {Path(path).name} als Readonly-Vorschau öffnen — 1.1.5"
            )
        except Exception as e:
            self.merge_preview.setPixmap(QPixmap())
            self.merge_preview.setText("Vorschau\nnicht möglich")
            self.merge_preview.setToolTip(f"Vorschau fehlgeschlagen: {e}")

    def _merge_preview_clicked(self, event) -> None:
        """Thumbnail-Klick → Datei in neuem Tab (readonly + Banner) — 1.1.5."""
        path = self._preview_path
        if not path or not Path(path).is_file():
            if event is not None:
                event.accept()
            return
        mw = self.parent()
        while mw is not None and not hasattr(mw, "open_path"):
            mw = mw.parent()
        if mw is None:
            if event is not None:
                event.accept()
            return
        preview_path = str(path)

        def _open():
            try:
                mw.open_path(preview_path, readonly=True)
            except TypeError:
                mw.open_path(preview_path)

        self.accept()
        QTimer.singleShot(0, _open)
        if event is not None:
            event.accept()

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

    def _pdf_page_count(self, path: str) -> int | None:
        path = (path or "").strip()
        if not path or not Path(path).is_file():
            return None
        try:
            import pikepdf

            with pikepdf.open(path) as pdf:
                return len(pdf.pages)
        except Exception:
            return None

    def _split_pick_src(self):
        path, _ = QFileDialog.getOpenFileName(self, "PDF", "", "PDF (*.pdf)")
        if path:
            self.split_src.setText(path)
            self._split_update_preview()

    def _split_pick_out(self):
        path = QFileDialog.getExistingDirectory(self, "Ausgabeordner")
        if path:
            self.split_out.setText(path)

    def _parse_ranges(self, text: str, page_count: int) -> list[tuple[int, int]] | None:
        """1-basierte Bereiche → 0-basiert für split_pdf — 1.2.0/1.2.1."""
        text = text.strip()
        if not text:
            return None
        return parse_page_ranges(text, page_count, one_based=True)

    def _split_update_preview(self, *_args) -> None:
        """Live-Vorschau Seitenanzahl / DE-Fehler — 1.2.1."""
        if not hasattr(self, "split_preview"):
            return
        src = self.split_src.text().strip()
        spec = self.split_ranges.text().strip()
        if not spec:
            self.split_preview.setText("Vorschau: — (keine Bereiche; „Alle N“ / einzeln)")
            self.split_preview.setStyleSheet("")
            return
        n = self._pdf_page_count(src)
        if n is None:
            self.split_preview.setText(
                "Vorschau: Quelle wählen, um Seitenanzahl zu prüfen."
            )
            self.split_preview.setStyleSheet("color: #666;")
            return
        pages, n_ranges, err = preview_page_range_count(spec, n, one_based=True)
        if err:
            self.split_preview.setText(f"Fehler: {err}")
            self.split_preview.setStyleSheet("color: #b00020;")
            return
        self.split_preview.setText(
            f"Vorschau: {pages} Seite(n) in {n_ranges} Bereich(en) "
            f"(Dokument: {n} Seiten)"
        )
        self.split_preview.setStyleSheet("color: #0a5;")

    def _split_run(self):
        src = self.split_src.text().strip()
        out = self.split_out.text().strip()
        if not src or not out:
            QMessageBox.warning(self, "Teilen", "Quelle und Ausgabeordner angeben.")
            return
        try:
            n = self._pdf_page_count(src)
            if n is None:
                QMessageBox.warning(
                    self,
                    "Teilen",
                    "PDF konnte nicht gelesen werden. Bitte gültige Quelldatei wählen.",
                )
                return
            ranges = self._parse_ranges(self.split_ranges.text(), n)
            written = split_pdf(
                src,
                out,
                every_n=None
                if ranges or self.split_single.isChecked()
                else self.split_every.value(),
                ranges=ranges,
                single_pages=self.split_single.isChecked(),
            )
            paths = [str(p) for p in written]
            self._split_log_paths(paths)
            QMessageBox.information(
                self,
                "Teilen",
                f"{len(written)} Datei(en) erstellt in\n{out}",
            )
            if self.split_open_tabs.isChecked() and paths:
                self._split_open_written(paths)
        except ValueError as e:
            QMessageBox.warning(self, "Teilen — ungültiger Bereich", str(e))
            self._split_update_preview()
        except Exception as e:
            QMessageBox.critical(self, "Teilen", str(e))

    def _split_log_paths(self, paths: list[str]) -> None:
        """Erzeugte Pfade ins Split-Log schreiben — 1.2.2."""
        if not hasattr(self, "split_log"):
            return
        lines = [f"[{i + 1}] {p}" for i, p in enumerate(paths)]
        header = f"Erzeugt: {len(paths)} Datei(en)"
        self.split_log.setPlainText(header + ("\n" + "\n".join(lines) if lines else ""))

    def _split_log_empty_hint(self) -> None:
        """Hinweis bei leerem Pfad-Log — 1.2.4."""
        QMessageBox.information(
            self,
            "Pfad-Log",
            "Kein Log vorhanden — zuerst teilen.\n"
            "Danach: Doppelklick auf eine Zeile öffnet Datei oder Ordner.",
        )

    def _split_path_from_line(self, line: str) -> str | None:
        """Pfad aus Log-Zeile ``[n] /pfad`` oder blankem Pfad — 1.2.4."""
        import re

        text = (line or "").strip()
        if not text or text.lower().startswith("erzeugt:"):
            return None
        m = re.match(r"^\[\d+\]\s+(.+)$", text)
        if m:
            return m.group(1).strip().strip('"') or None
        # Fallback: ganze Zeile, wenn sie wie ein Pfad aussieht
        if "/" in text or "\\" in text or text.endswith(".pdf"):
            return text.strip('"')
        return None

    def _split_open_log_path(self) -> None:
        """Doppelklick: Datei öffnen, sonst Ordner — 1.2.4."""
        if not hasattr(self, "split_log"):
            return
        text = (self.split_log.toPlainText() or "").strip()
        if not text:
            self._split_log_empty_hint()
            return
        cursor = self.split_log.textCursor()
        block = cursor.block()
        path_s = self._split_path_from_line(block.text() if block.isValid() else "")
        if not path_s:
            QMessageBox.information(
                self,
                "Pfad-Log",
                "Keine Pfadzeile unter dem Cursor.\n"
                "Doppelklick auf eine Zeile mit Dateipfad.",
            )
            return
        target = Path(path_s)
        if target.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
            return
        folder = target if target.is_dir() else target.parent
        if folder.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
            return
        QMessageBox.warning(
            self,
            "Pfad-Log",
            f"Datei/Ordner nicht gefunden:\n{path_s}",
        )

    def _split_copy_log(self) -> None:
        """Pfad-Log in die Zwischenablage — 1.2.3."""
        from PySide6.QtWidgets import QApplication

        if not hasattr(self, "split_log"):
            return
        text = (self.split_log.toPlainText() or "").strip()
        if not text:
            self._split_log_empty_hint()
            return
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Pfad-Log", "Log in die Zwischenablage kopiert.")

    def _split_save_log_txt(self) -> None:
        """Pfad-Log als TXT speichern — 1.2.3."""
        if not hasattr(self, "split_log"):
            return
        text = (self.split_log.toPlainText() or "").strip()
        if not text:
            self._split_log_empty_hint()
            return
        from instantlensdoc.core.app_settings import (
            dialog_start_dir,
            get_last_export_dir,
            set_last_export_dir,
        )

        start = dialog_start_dir(get_last_export_dir())
        default = str(Path(start) / "split-log.txt")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Pfad-Log als TXT speichern",
            default,
            "Text (*.txt);;Alle (*.*)",
        )
        if not path:
            return
        if not path.lower().endswith(".txt"):
            path += ".txt"
        try:
            Path(path).write_text(text + "\n", encoding="utf-8")
            set_last_export_dir(Path(path).parent)
            QMessageBox.information(self, "Pfad-Log", f"Gespeichert:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Pfad-Log", str(e))

    def _split_open_written(self, paths: list[str]) -> None:
        """Erzeugte Split-PDFs optional in Tabs öffnen — 1.2.2."""
        mw = self.parent()
        while mw is not None and not hasattr(mw, "open_path"):
            mw = mw.parent()
        if mw is None:
            return
        # Begrenze Mass-Open; Rest bleibt im Pfad-Log
        to_open = [p for p in paths if p and Path(p).is_file()][:12]

        def _open_all():
            for p in to_open:
                try:
                    mw.open_path(p)
                except Exception:
                    pass

        self.accept()
        QTimer.singleShot(0, _open_all)

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
                self._page_count = n
            except Exception:
                pass
            self._ex_update_preview()

    def _ex_pick_dest(self):
        if self.ex_one_per_range.isChecked():
            path = QFileDialog.getExistingDirectory(
                self, "Ausgabeordner (eine Datei pro Bereich)"
            )
            if path:
                self.ex_dest.setText(path)
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Ziel-PDF", self.ex_dest.text(), "PDF (*.pdf)"
        )
        if path:
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            self.ex_dest.setText(path)

    def _ex_update_preview(self, *_args) -> None:
        """Live-Vorschau Seitenanzahl / DE-Fehler — 1.2.1."""
        if not hasattr(self, "ex_preview"):
            return
        src = self.ex_src.text().strip()
        spec = (self.ex_spec.text() or "").strip()
        if not spec:
            spec = f"{self.ex_from.value()}-{self.ex_to.value()}"
        n = self._pdf_page_count(src)
        if n is None:
            if self._page_count and self._page_count > 0:
                n = int(self._page_count)
            else:
                self.ex_preview.setText(
                    "Vorschau: Quelle wählen, um Seitenanzahl zu prüfen."
                )
                self.ex_preview.setStyleSheet("color: #666;")
                return
        pages, n_ranges, err = preview_page_range_count(spec, n, one_based=True)
        if err:
            self.ex_preview.setText(f"Fehler: {err}")
            self.ex_preview.setStyleSheet("color: #b00020;")
            return
        self.ex_preview.setText(
            f"Vorschau: {pages} Seite(n) in {n_ranges} Bereich(en) "
            f"(Dokument: {n} Seiten)"
        )
        self.ex_preview.setStyleSheet("color: #0a5;")

    def _ex_run(self):
        src = self.ex_src.text().strip()
        dest = self.ex_dest.text().strip()
        if not src or not dest:
            QMessageBox.warning(
                self, "Seitenbereich", "Quelle und Ziel-PDF bzw. Ordner angeben."
            )
            return
        from instantlensdoc.ui.file_dialogs import confirm_overwrite_export

        spec = (self.ex_spec.text() or "").strip()
        one_per = self.ex_one_per_range.isChecked()
        if not spec:
            spec = f"{self.ex_from.value()}-{self.ex_to.value()}"
        try:
            n = self._pdf_page_count(src)
            if n is None:
                QMessageBox.warning(
                    self,
                    "Seitenbereich",
                    "PDF konnte nicht gelesen werden. Bitte gültige Quelldatei wählen.",
                )
                return
            # Vorab validieren → klare DE-Meldung
            parse_page_ranges(spec, n, one_based=True)
            if one_per:
                written = extract_by_page_spec(
                    src, dest, spec, one_based=True, one_file_per_range=True
                )
                QMessageBox.information(
                    self,
                    "Seitenbereich",
                    f"{len(written)} Datei(en) aus „{spec}“:\n{dest}",
                )
            else:
                if not confirm_overwrite_export(dest, self):
                    return
                written = extract_by_page_spec(
                    src, dest, spec, one_based=True, one_file_per_range=False
                )
                out = written[0] if written else dest
                QMessageBox.information(
                    self,
                    "Seitenbereich",
                    f"Extrahiert: {spec}\n{out}",
                )
        except ValueError as e:
            QMessageBox.warning(self, "Seitenbereich — ungültiger Bereich", str(e))
            self._ex_update_preview()
        except Exception as e:
            QMessageBox.critical(self, "Seitenbereich", str(e))