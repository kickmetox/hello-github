"""Annotation-Suche: klickbare Treffer, Regex-Fehlerstatus, CSV-Export — 1.4.5."""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from instantlensdoc.core.ann_search import (
    AnnSearchHit,
    export_ann_search_hits_csv,
    search_annotations_in_paths,
)
from instantlensdoc.core.app_settings import (
    dialog_start_dir,
    get_last_export_dir,
    set_last_export_dir,
)

# Fortschrittsdialog ab so vielen Docs beim CSV-Neu-Scan — 1.4.5
CSV_RESCAN_PROGRESS_THRESHOLD = 3


class AnnotationSearchDialog(QDialog):
    """Nicht-modale Trefferliste; Klick → Dokument/Seite — 1.4.5."""

    hit_activated = Signal(str, int, str)  # path, page_0based, ann_id

    def __init__(self, parent=None, *, paths: list[str] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Annotation-Suche (offene Docs)")
        self.resize(580, 460)
        self.setModal(False)
        self._paths = [str(p) for p in (paths or []) if p]
        self._hits: list[AnnSearchHit] = []
        self._regex_error: str = ""

        root = QVBoxLayout(self)
        root.addWidget(
            QLabel(
                "Volltext über Sidecar-Notizen/Highlights/Tags aller offenen Docs — "
                "Treffer klickbar (Doc+Seite); CSV: aktuelle Liste oder Neu-Scan "
                "(Fortschritt/Abbruch bei vielen Docs) — 1.4.5"
            )
        )

        row = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText("Suchbegriff…")
        self.query.returnPressed.connect(self._run_search)
        row.addWidget(self.query, 1)
        btn = QPushButton("Suchen")
        btn.clicked.connect(self._run_search)
        row.addWidget(btn)
        root.addLayout(row)

        opts = QHBoxLayout()
        self.chk_case = QCheckBox("Aa")
        self.chk_case.setToolTip("Groß-/Kleinschreibung beachten — 1.4.1")
        self.chk_case.toggled.connect(lambda _: self._run_search())
        self.chk_regex = QCheckBox("Regex")
        self.chk_regex.setToolTip("Suchbegriff als regulären Ausdruck — 1.4.1/1.4.2")
        self.chk_regex.toggled.connect(lambda _: self._run_search())
        opts.addWidget(self.chk_case)
        opts.addWidget(self.chk_regex)
        opts.addStretch()
        self.btn_export_csv = QPushButton("Treffer CSV…")
        self.btn_export_csv.setToolTip(
            "CSV-Export: aktuelle Trefferliste oder alle Docs neu scannen "
            "(Fortschritt + Abbrechen bei vielen Docs) — 1.4.5"
        )
        self.btn_export_csv.clicked.connect(self._export_csv)
        opts.addWidget(self.btn_export_csv)
        root.addLayout(opts)

        # CSV-Scope: nur aktuelle Trefferliste vs. alle Docs neu scannen — 1.4.4/1.4.5
        csv_row = QHBoxLayout()
        csv_row.addWidget(QLabel("CSV-Quelle:"))
        self.radio_csv_current = QRadioButton("nur aktuelle Trefferliste")
        self.radio_csv_current.setToolTip(
            "Exportiert die derzeit angezeigte Trefferliste ohne erneuten Scan — 1.4.4"
        )
        self.radio_csv_rescan = QRadioButton("alle Docs neu scannen")
        self.radio_csv_rescan.setToolTip(
            "Vor dem Export Suche über alle gelisteten Docs erneut ausführen; "
            "bei vielen Docs Fortschrittsdialog mit Abbrechen — 1.4.5"
        )
        self.radio_csv_current.setChecked(True)
        self._csv_scope_group = QButtonGroup(self)
        self._csv_scope_group.addButton(self.radio_csv_current)
        self._csv_scope_group.addButton(self.radio_csv_rescan)
        csv_row.addWidget(self.radio_csv_current)
        csv_row.addWidget(self.radio_csv_rescan)
        csv_row.addStretch()
        root.addLayout(csv_row)

        self.list = QListWidget()
        self.list.setToolTip(
            "Klick oder Enter: Dokument öffnen und zur Seite springen — 1.4.1"
        )
        # Klickbar: Einfachklick + Activate/Doppelklick — 1.4.1
        self.list.itemClicked.connect(self._activate)
        self.list.itemActivated.connect(self._activate)
        self.list.itemDoubleClicked.connect(self._activate)
        root.addWidget(self.list, 1)

        self.status = QLabel("Bereit")
        self.status.setObjectName("annSearchStatus")
        root.addWidget(self.status)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def set_paths(self, paths: list[str]) -> None:
        self._paths = [str(p) for p in paths if p]

    def csv_export_scope(self) -> str:
        """``current`` = Trefferliste; ``rescan`` = alle Docs neu scannen — 1.4.4."""
        if self.radio_csv_rescan.isChecked():
            return "rescan"
        return "current"

    def _set_status_ok(self, text: str) -> None:
        self.status.setStyleSheet("")
        self.status.setText(text)

    def _set_status_error(self, text: str) -> None:
        """Fehlerstatus wie PDF-Suche (Regex-Fehler) — 1.4.2."""
        self.status.setStyleSheet(
            "QLabel#annSearchStatus { color: #b33; font-weight: 600; }"
        )
        self.status.setText(text)

    def _populate_hits(self, hits: list[AnnSearchHit]) -> None:
        self._hits = list(hits)
        self.list.clear()
        for h in self._hits:
            name = Path(h.path).name
            text = f"{name}  ·  S.{h.page + 1}  [{h.ann_type}]  {h.snippet}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, h)
            item.setToolTip(
                f"{h.path}\nSeite {h.page + 1}\n{h.text or h.tags}\n"
                "Klick → Doc+Seite — 1.4.1"
            )
            self.list.addItem(item)

    def _run_search(self) -> None:
        q = self.query.text().strip()
        self.list.clear()
        self._hits = []
        self._regex_error = ""
        if not q:
            self._set_status_ok("Leere Suche")
            return
        case_sensitive = self.chk_case.isChecked()
        use_regex = self.chk_regex.isChecked()
        if use_regex:
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                re.compile(q, flags)
            except re.error as e:
                # Wie PDF-Suche: Status „Regex-Fehler: …“ — 1.4.2
                self._regex_error = str(e)
                self._set_status_error(f"Regex-Fehler: {e}")
                self.list.addItem(QListWidgetItem(f"Regex-Fehler: {e}"))
                return
        hits = search_annotations_in_paths(
            self._paths,
            q,
            case_sensitive=case_sensitive,
            use_regex=use_regex,
        )
        self._populate_hits(hits)
        flags = []
        if case_sensitive:
            flags.append("Aa")
        if use_regex:
            flags.append("Regex")
        flag_s = f" [{', '.join(flags)}]" if flags else ""
        self._set_status_ok(
            f"{len(self._hits)} Treffer in {len(self._paths)} Doc(s)"
            f"{flag_s} — Klick öffnet Doc+Seite — 1.4.5"
        )

    def _rescan_hits_with_progress(
        self,
        q: str,
        *,
        case_sensitive: bool,
        use_regex: bool,
    ) -> list[AnnSearchHit] | None:
        """
        Neu-Scan über alle Docs; bei vielen Docs Fortschrittsdialog + Abbrechen — 1.4.5.
        Rückgabe None = abgebrochen; sonst Trefferliste.
        """
        paths = list(self._paths)
        n_docs = len(paths)
        use_progress = n_docs > CSV_RESCAN_PROGRESS_THRESHOLD
        cancelled = {"flag": False}
        prog: QProgressDialog | None = None
        if use_progress:
            prog = QProgressDialog(
                "Annotation-Suche Neu-Scan…", "Abbrechen", 0, n_docs, self
            )
            prog.setWindowTitle("CSV Neu-Scan")
            prog.setWindowModality(Qt.WindowModal)
            prog.setMinimumDuration(0)
            prog.setCancelButtonText("Abbrechen")
            prog.setValue(0)
            prog.setLabelText(f"0 / {n_docs} Docs…")
            QApplication.processEvents()

        def on_progress(i: int, total: int, name: str) -> bool:
            if prog is None:
                return True
            if prog.wasCanceled():
                cancelled["flag"] = True
                return False
            prog.setLabelText(f"Scan {i + 1}/{total}: {name}")
            prog.setValue(i)
            QApplication.processEvents()
            if prog.wasCanceled():
                cancelled["flag"] = True
                return False
            return True

        try:
            hits = search_annotations_in_paths(
                paths,
                q,
                case_sensitive=case_sensitive,
                use_regex=use_regex,
                on_progress=on_progress if use_progress else None,
            )
        finally:
            if prog is not None:
                if not cancelled["flag"]:
                    prog.setValue(n_docs)
                prog.close()

        if cancelled["flag"]:
            self._set_status_ok(
                f"CSV Neu-Scan abgebrochen ({len(hits)} Treffer bisher) — 1.4.5"
            )
            return None
        return list(hits)

    def _hits_for_csv_export(self) -> list[AnnSearchHit] | None:
        """
        Treffer je CSV-Scope.
        ``current``: aktuelle Liste; ``rescan``: alle Docs neu scannen — 1.4.4/1.4.5.
        Bei Regex-Fehler oder Abbruch: None.
        """
        if self._regex_error:
            return None
        scope = self.csv_export_scope()
        if scope == "current":
            return list(self._hits)
        # Neu scannen (Liste aktualisieren) — Fortschritt bei vielen Docs — 1.4.5
        q = self.query.text().strip()
        if not q:
            return []
        case_sensitive = self.chk_case.isChecked()
        use_regex = self.chk_regex.isChecked()
        if use_regex:
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                re.compile(q, flags)
            except re.error as e:
                self._regex_error = str(e)
                self._set_status_error(f"Regex-Fehler: {e}")
                return None
        hits = self._rescan_hits_with_progress(
            q, case_sensitive=case_sensitive, use_regex=use_regex
        )
        if hits is None:
            return None  # abgebrochen
        self._populate_hits(hits)
        return list(self._hits)

    def _export_csv(self) -> None:
        """Treffer-Export CSV — aktuelle Liste oder Neu-Scan — 1.4.5."""
        if self._regex_error and self.csv_export_scope() == "current":
            QMessageBox.warning(
                self,
                "Treffer CSV",
                f"Kein Export bei Regex-Fehler:\n{self._regex_error}",
            )
            return
        hits = self._hits_for_csv_export()
        if hits is None:
            if self.csv_export_scope() == "rescan" and not self._regex_error:
                # Abbruch Neu-Scan — kein Fehlerdialog
                return
            QMessageBox.warning(
                self,
                "Treffer CSV",
                f"Kein Export bei Regex-Fehler:\n{self._regex_error or '?'}",
            )
            return
        if not hits:
            QMessageBox.information(
                self,
                "Treffer CSV",
                "Keine Treffer zum Export — zuerst suchen "
                "bzw. gültigen Suchbegriff für Neu-Scan.",
            )
            return
        q = self.query.text().strip()
        safe_q = "".join(
            c if c.isalnum() or c in "-_" else "_" for c in (q or "hits")
        )[:40] or "hits"
        start = dialog_start_dir(get_last_export_dir())
        default = str(Path(start) / f"ann_search_{safe_q}.csv")
        path, _ = QFileDialog.getSaveFileName(
            self, "Annotation-Treffer als CSV", default, "CSV (*.csv)"
        )
        if not path:
            return
        try:
            dest = export_ann_search_hits_csv(path, hits, query=q)
            set_last_export_dir(dest.parent)
            scope = self.csv_export_scope()
            scope_lbl = (
                "Neu-Scan" if scope == "rescan" else "aktuelle Trefferliste"
            )
            self._set_status_ok(
                f"{len(hits)} Treffer als CSV ({scope_lbl}): {dest.name} — 1.4.5"
            )
            QMessageBox.information(
                self,
                "Treffer CSV",
                f"{len(hits)} Treffer exportiert ({scope_lbl}):\n{dest}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Treffer CSV", str(e))

    def _activate(self, item: QListWidgetItem | None = None) -> None:
        it = item or self.list.currentItem()
        if it is None:
            return
        h = it.data(Qt.UserRole)
        if not isinstance(h, AnnSearchHit):
            return
        self.hit_activated.emit(h.path, int(h.page), h.ann_id)
