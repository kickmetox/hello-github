"""Zentrale Multi-Dokument-Suche: Volltext über alle offenen PDFs — 2.0.4."""

from __future__ import annotations

import html as _html
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
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
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from instantlensdoc.core.app_settings import (
    DEFAULT_MULTI_DOC_CSV_FILENAME_TEMPLATE,
    dialog_start_dir,
    find_invalid_multi_doc_csv_placeholders,
    format_multi_doc_csv_filename,
    get_last_multi_doc_csv_dir,
    get_multi_doc_csv_filename_template,
    highlight_multi_doc_csv_template_html,
    set_last_multi_doc_csv_dir,
    set_multi_doc_csv_filename_template,
)
from instantlensdoc.core import fulltext as fulltext_mod
from instantlensdoc.core.fulltext import SearchPatternError


class MultiDocSearchDialog(QDialog):
    """
    Zentrale Trefferliste: Volltext (Textlayer) über alle offenen/gelisteten PDFs.
    Case / Regex / Whole-word · CSV Doc,Seite,Snippet,Match · BOM · Fortschritt —
    CSV Zielordner merken · Live-Template Quick-Insert ``{date}``/``{query}`` ·
    ungültige Platzhalter rot · Reset Default — 2.0.4.
    Doppelklick / Enter → Treffer aktivieren (Signal hit_activated).
    """

    hit_activated = Signal(str, object, str)  # path, page_index|None, query

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        paths: list[str] | None = None,
        initial_query: str = "",
    ):
        super().__init__(parent)
        self.setObjectName("multiDocSearchDialog")
        self.setWindowTitle("Multi-Dokument-Suche — InstantLens Doc 2.0")
        self.setModal(False)
        self.resize(680, 520)
        self._paths = list(paths or [])
        self._hits: list[fulltext_mod.SearchHit] = []
        self._query = ""

        layout = QVBoxLayout(self)
        intro = QLabel(
            "Volltextsuche über alle offenen PDFs (Textlayer). "
            "Optionen Aa / Wort / Regex; CSV Doc,Seite,Snippet,Match; BOM; "
            "Zielordner merken; Template Quick-Insert {date}/{query}; "
            "ungültige Platzhalter rot; Reset Default; Regex-Fehler im Status."
        )
        intro.setWordWrap(True)
        intro.setObjectName("multiDocSearchIntro")
        layout.addWidget(intro)

        row = QHBoxLayout()
        self.query_edit = QLineEdit()
        self.query_edit.setObjectName("multiDocSearchQuery")
        self.query_edit.setPlaceholderText("Suchbegriff…")
        self.query_edit.setClearButtonEnabled(True)
        if initial_query:
            self.query_edit.setText(initial_query)
        self.query_edit.returnPressed.connect(self.run_search)
        self.query_edit.textChanged.connect(self._update_csv_filename_preview)
        self.btn_search = QPushButton("Suchen")
        self.btn_search.setObjectName("multiDocSearchBtn")
        self.btn_search.setDefault(True)
        self.btn_search.clicked.connect(self.run_search)
        row.addWidget(self.query_edit, 1)
        row.addWidget(self.btn_search)
        layout.addLayout(row)

        opt_row = QHBoxLayout()
        self.chk_case = QCheckBox("Aa")
        self.chk_case.setObjectName("multiDocSearchCase")
        self.chk_case.setToolTip("Groß-/Kleinschreibung beachten — 2.0.1")
        self.chk_case.setChecked(False)
        self.chk_whole = QCheckBox("Wort")
        self.chk_whole.setObjectName("multiDocSearchWhole")
        self.chk_whole.setToolTip("Nur ganze Wörter — 2.0.1")
        self.chk_whole.setChecked(False)
        self.chk_regex = QCheckBox(".*")
        self.chk_regex.setObjectName("multiDocSearchRegex")
        self.chk_regex.setToolTip(
            "Suchbegriff als regulärer Ausdruck — Fehler im Status — 2.0.2"
        )
        self.chk_regex.setChecked(False)
        self.chk_bom = QCheckBox("UTF-8 BOM")
        self.chk_bom.setObjectName("multiDocSearchBom")
        self.chk_bom.setToolTip("CSV mit UTF-8 BOM schreiben (Excel) — 2.0.2")
        self.chk_bom.setChecked(True)
        opt_row.addWidget(self.chk_case)
        opt_row.addWidget(self.chk_whole)
        opt_row.addWidget(self.chk_regex)
        opt_row.addWidget(self.chk_bom)
        opt_row.addStretch(1)
        self.btn_export_csv = QPushButton("Treffer CSV…")
        self.btn_export_csv.setObjectName("multiDocSearchExportCsv")
        self.btn_export_csv.setToolTip(
            "Trefferliste CSV: Doc,Seite,Snippet,Match · Zielordner merken · "
            "Template Quick-Insert {date}/{query} · Reset Default — 2.0.4"
        )
        self.btn_export_csv.clicked.connect(self._export_csv)
        self.btn_export_csv.setEnabled(False)
        opt_row.addWidget(self.btn_export_csv)
        layout.addLayout(opt_row)

        tpl_row = QHBoxLayout()
        tpl_row.addWidget(QLabel("CSV-Dateiname:"))
        self.csv_tpl_edit = QLineEdit()
        self.csv_tpl_edit.setObjectName("multiDocSearchCsvTemplate")
        self.csv_tpl_edit.setPlaceholderText(DEFAULT_MULTI_DOC_CSV_FILENAME_TEMPLATE)
        self.csv_tpl_edit.setText(get_multi_doc_csv_filename_template())
        self.csv_tpl_edit.setToolTip(
            "Live-Dateiname-Template; Platzhalter {date} (YYYY-MM-DD), "
            "{query} (Suchbegriff); Quick-Insert an Cursor; "
            "Reset Default ({date}_multisearch.csv); "
            "ungültige Platzhalter rot — 2.0.4"
        )
        self.csv_tpl_edit.textChanged.connect(self._update_csv_filename_preview)
        tpl_row.addWidget(self.csv_tpl_edit, 1)
        for token in ("{date}", "{query}"):
            btn = QPushButton(token)
            btn.setObjectName(
                "multiDocSearchInsertDate"
                if token == "{date}"
                else "multiDocSearchInsertQuery"
            )
            btn.setAutoDefault(False)
            btn.setDefault(False)
            btn.setFocusPolicy(Qt.TabFocus)
            btn.setToolTip(
                f"Platzhalter {token} an Cursor-Position einfügen — 2.0.4"
            )
            btn.clicked.connect(
                lambda _checked=False, t=token: self._insert_csv_placeholder(t)
            )
            tpl_row.addWidget(btn)
        self.btn_reset_csv_tpl = QPushButton("Reset Default")
        self.btn_reset_csv_tpl.setObjectName("multiDocSearchCsvReset")
        self.btn_reset_csv_tpl.setAutoDefault(False)
        self.btn_reset_csv_tpl.setDefault(False)
        self.btn_reset_csv_tpl.setFocusPolicy(Qt.TabFocus)
        self.btn_reset_csv_tpl.setToolTip(
            f"Template auf Default zurücksetzen "
            f"({DEFAULT_MULTI_DOC_CSV_FILENAME_TEMPLATE}); "
            "Bestätigung nur bei Abweichung — 2.0.4"
        )
        self.btn_reset_csv_tpl.clicked.connect(self._reset_csv_template)
        tpl_row.addWidget(self.btn_reset_csv_tpl)
        layout.addLayout(tpl_row)

        self.csv_filename_preview = QLabel("")
        self.csv_filename_preview.setObjectName("multiDocSearchCsvPreview")
        self.csv_filename_preview.setWordWrap(True)
        self.csv_filename_preview.setTextFormat(Qt.RichText)
        self.csv_filename_preview.setToolTip(
            "Live-Vorschau des CSV-Dateinamens; ungültige Platzhalter rot — 2.0.4"
        )
        layout.addWidget(self.csv_filename_preview)
        self._update_csv_filename_preview()

        self.progress = QProgressBar()
        self.progress.setObjectName("multiDocSearchProgress")
        self.progress.setAccessibleName("Multi-Dokument-Suche Fortschritt")
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setFormat("%v / %m Docs")
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.status = QLabel("")
        self.status.setObjectName("multiDocSearchStatus")
        self.status.setAccessibleName("Multi-Dokument-Suche Status")
        layout.addWidget(self.status)

        self.hits_list = QListWidget()
        self.hits_list.setObjectName("multiDocSearchHits")
        self.hits_list.setAccessibleName("Zentrale Trefferliste")
        self.hits_list.itemActivated.connect(self._activate_item)
        self.hits_list.itemDoubleClicked.connect(self._activate_item)
        layout.addWidget(self.hits_list, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        close_btn = buttons.button(QDialogButtonBox.Close)
        if close_btn is not None:
            close_btn.setText("Schließen")
        layout.addWidget(buttons)

        esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        esc.setContext(Qt.WindowShortcut)
        esc.activated.connect(self.reject)

        if initial_query.strip():
            self.run_search()

    def set_paths(self, paths: list[str]) -> None:
        self._paths = list(paths or [])

    def _current_query_for_filename(self) -> str:
        return (self._query or self.query_edit.text() or "").strip()

    def _insert_csv_placeholder(self, token: str) -> None:
        """Quick-Insert {date}/{query} an Cursor — 2.0.4."""
        edit = self.csv_tpl_edit
        edit.insert(str(token or ""))
        edit.setFocus()
        self._update_csv_filename_preview()

    def _focus_csv_tpl_select_all(self) -> None:
        """Fokus + Selektion ganzer Default-Text — 2.0.4."""
        edit = self.csv_tpl_edit
        edit.setFocus()
        edit.selectAll()

    def _reset_csv_template(self) -> None:
        """
        Template auf Default; Bestätigung nur bei Abweichung;
        danach Live-Vorschau + Fokus mit Selektion — 2.0.4.
        """
        edit = self.csv_tpl_edit
        default = DEFAULT_MULTI_DOC_CSV_FILENAME_TEMPLATE
        current = edit.text() or ""
        if current == default:
            self._update_csv_filename_preview()
            QTimer.singleShot(0, self._focus_csv_tpl_select_all)
            return
        reply = QMessageBox.question(
            self,
            "Reset Default",
            f"CSV-Dateiname-Template auf Default zurücksetzen?\n\n"
            f"Aktuell: {current}\n"
            f"Default: {default}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            QTimer.singleShot(0, self._focus_csv_tpl_select_all)
            return
        edit.selectAll()
        edit.insert(default)
        self._update_csv_filename_preview()
        QTimer.singleShot(0, self._focus_csv_tpl_select_all)

    def _update_csv_filename_preview(self, *_args) -> None:
        """Live-Vorschau; ungültige Platzhalter rot — 2.0.4."""
        tpl = (
            (self.csv_tpl_edit.text() or "").strip()
            or DEFAULT_MULTI_DOC_CSV_FILENAME_TEMPLATE
        )
        q = self._current_query_for_filename()
        name = format_multi_doc_csv_filename(template=tpl, query=q)
        html_tpl = highlight_multi_doc_csv_template_html(tpl)
        invalid = find_invalid_multi_doc_csv_placeholders(tpl)
        parts = [html_tpl, f"→ {_html.escape(name)}"]
        if invalid:
            listed = ", ".join(_html.escape("{" + n + "}") for n in invalid)
            parts.append(
                f'<span style="color:#c62828">Ungültige Platzhalter: {listed}</span>'
            )
        self.csv_filename_preview.setText("<br>".join(parts))
        self.csv_filename_preview.setAccessibleName(f"CSV-Dateiname Vorschau {name}")

    def _csv_start_path(self) -> str:
        """Startpfad Save-Dialog: gemerkter Ordner + Live-Template — 2.0.4."""
        tpl = (
            (self.csv_tpl_edit.text() or "").strip()
            or DEFAULT_MULTI_DOC_CSV_FILENAME_TEMPLATE
        )
        name = format_multi_doc_csv_filename(
            template=tpl, query=self._current_query_for_filename()
        )
        remembered = get_last_multi_doc_csv_dir()
        start_dir = dialog_start_dir(remembered)
        return str(Path(start_dir) / name)

    def _set_regex_error(self, message: str) -> None:
        """Regex-Fehlerstatus sichtbar setzen — 2.0.2."""
        self.status.setProperty("ildError", True)
        self.status.setStyleSheet("color: #c0392b; font-weight: bold;")
        self.status.setText(f"Regex-Fehler: {message}")
        self.status.setToolTip(f"Ungültiger regulärer Ausdruck: {message}")

    def _clear_status_error(self) -> None:
        self.status.setProperty("ildError", False)
        self.status.setStyleSheet("")
        self.status.setToolTip("")

    def _on_progress(self, current: int, total: int, path: str) -> None:
        self.progress.setMaximum(max(1, total))
        self.progress.setValue(current)
        name = Path(path).name if path else ""
        self.status.setText(f"Suche… {current}/{total} · {name}")
        QApplication.processEvents()

    def run_search(self) -> None:
        query = (self.query_edit.text() or "").strip()
        self._query = query
        self.hits_list.clear()
        self._hits = []
        self.btn_export_csv.setEnabled(False)
        self._clear_status_error()
        self._update_csv_filename_preview()
        if not query:
            self.status.setText("Leere Suche")
            self.progress.setVisible(False)
            return
        pdfs = fulltext_mod.filter_pdf_paths(self._paths)
        if not pdfs:
            self.status.setText("Keine offenen PDFs für Multi-Dokument-Suche")
            self.progress.setVisible(False)
            return
        show_prog = len(pdfs) >= 3
        self.progress.setVisible(show_prog)
        if show_prog:
            self.progress.setMaximum(len(pdfs))
            self.progress.setValue(0)
        case_sensitive = bool(self.chk_case.isChecked())
        whole_word = bool(self.chk_whole.isChecked())
        use_regex = bool(self.chk_regex.isChecked())
        try:
            hits = fulltext_mod.search_open_pdfs(
                pdfs,
                query,
                max_hits=200,
                case_sensitive=case_sensitive,
                whole_word=whole_word,
                regex=use_regex,
                on_progress=self._on_progress if show_prog else None,
            )
        except SearchPatternError as exc:
            self.progress.setVisible(False)
            self._set_regex_error(str(exc))
            return
        self._hits = hits
        self.progress.setVisible(False)
        if not hits:
            self.status.setText(f"0 Treffer in {len(pdfs)} PDF(s)")
            return
        for h in hits:
            label = fulltext_mod.format_hit_line(
                Path(h.path).name,
                page=h.page,
                line=h.line,
                snippet=h.snippet or query,
                kind=h.kind,
                query=query,
            )
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, (h.path, h.page, query))
            item.setToolTip(f"{h.path}\n{h.snippet or ''}")
            self.hits_list.addItem(item)
        files = {Path(h.path).name for h in hits}
        opts = []
        if case_sensitive:
            opts.append("Aa")
        if whole_word:
            opts.append("Wort")
        if use_regex:
            opts.append("Regex")
        opt_s = f" · {', '.join(opts)}" if opts else ""
        self.status.setText(
            f"{len(hits)} Treffer in {len(pdfs)} PDF(s) · {len(files)} Datei(en)"
            f"{opt_s} — zentral"
        )
        self.btn_export_csv.setEnabled(True)

    def _export_csv(self) -> None:
        if not self._hits:
            QMessageBox.information(self, "Multi-Dokument-Suche", "Keine Treffer zum Export.")
            return
        tpl = (
            (self.csv_tpl_edit.text() or "").strip()
            or DEFAULT_MULTI_DOC_CSV_FILENAME_TEMPLATE
        )
        invalid = find_invalid_multi_doc_csv_placeholders(tpl)
        if invalid:
            listed = ", ".join("{" + n + "}" for n in invalid)
            QMessageBox.warning(
                self,
                "Multi-Dokument-Suche",
                f"Ungültige Platzhalter im Template:\n{listed}\n\n"
                f"Erlaubt: {{date}}, {{query}}.",
            )
            return
        set_multi_doc_csv_filename_template(tpl)
        start = self._csv_start_path()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Treffer als CSV speichern",
            start,
            "CSV (*.csv)",
        )
        if not path:
            return
        try:
            dest = fulltext_mod.export_multi_doc_hits_csv(
                path,
                self._hits,
                query=self._query,
                utf8_bom=bool(self.chk_bom.isChecked()),
            )
            set_last_multi_doc_csv_dir(dest.parent)
            bom_s = "BOM" if self.chk_bom.isChecked() else "ohne BOM"
            self.status.setText(
                f"CSV exportiert: {dest.name} · {len(self._hits)} Zeile(n) · "
                f"Doc,Seite,Snippet,Match · {bom_s} · Ordner gemerkt"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Multi-Dokument-Suche", f"CSV-Export fehlgeschlagen:\n{exc}")

    def _activate_item(self, item: QListWidgetItem | None = None) -> None:
        it = item or self.hits_list.currentItem()
        if it is None:
            return
        payload = it.data(Qt.UserRole)
        if not (isinstance(payload, tuple) and len(payload) >= 2):
            return
        path = str(payload[0])
        page = payload[1]
        query = str(payload[2]) if len(payload) >= 3 else self._query
        self.hit_activated.emit(path, page, query)
