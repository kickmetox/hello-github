"""Panel/Dialog: Dokument-Statistik (Seiten, Wörter, Ann., Dateigröße) — 1.6.4."""

from __future__ import annotations

import html as _html
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ild_pdf.doc_stats import (
    DEFAULT_STATS_FILENAME_TEMPLATE,
    DocumentStats,
    collect_document_stats,
    export_document_stats_json,
    find_invalid_stats_placeholders,
    format_document_stats_text,
    format_stats_filename,
    highlight_stats_template_html,
    preview_stats_filename,
)
from instantlensdoc.core.app_settings import (
    dialog_start_dir,
    get_last_stats_export_dir,
    get_stats_filename_template,
    set_last_stats_export_dir,
    set_stats_filename_template,
)


class StatsFilenameTemplateEdit(QLineEdit):
    """Stats-Dateiname-Template: Cursor merken + lokales Undo — 1.6.4."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_cursor = 0
        self._saved_sel_start = -1
        self._saved_sel_len = 0

    def focusOutEvent(self, event):
        self._saved_cursor = self.cursorPosition()
        self._saved_sel_start = self.selectionStart()
        self._saved_sel_len = self.selectionLength()
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Undo):
            if self.isUndoAvailable():
                self.undo()
            event.accept()
            return
        if event.matches(QKeySequence.Redo):
            if self.isRedoAvailable():
                self.redo()
            event.accept()
            return
        super().keyPressEvent(event)

    def restore_insert_position(self) -> None:
        if self.hasFocus():
            return
        if self._saved_sel_start >= 0 and self._saved_sel_len > 0:
            self.setSelection(self._saved_sel_start, self._saved_sel_len)
        else:
            pos = max(0, min(self._saved_cursor, len(self.text())))
            self.setCursorPosition(pos)


class DocStatsDialog(QDialog):
    """Nicht-modales Statistik-Panel für das aktuelle PDF."""

    def __init__(
        self,
        parent=None,
        *,
        pdf_path: str | Path | None = None,
        annotation_count: int | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Dokument-Statistik")
        self.setWindowModality(Qt.NonModal)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.resize(440, 360)
        self._pdf_path = Path(pdf_path) if pdf_path else None
        self._ann_count = annotation_count
        self._last_stats: DocumentStats | None = None

        layout = QVBoxLayout(self)
        self.hint = QLabel(
            "Seiten · Wörter (Text-PDF) · Annotationen · Dateigröße — "
            "Copy/JSON ildstats-v1 · Dateiname-Template Live-Vorschau — 1.6.4"
        )
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet("color:#555;")
        layout.addWidget(self.hint)

        form = QFormLayout()
        self.lbl_file = QLabel("—")
        self.lbl_pages = QLabel("—")
        self.lbl_words = QLabel("—")
        self.lbl_ann = QLabel("—")
        self.lbl_size = QLabel("—")
        for lab in (
            self.lbl_file,
            self.lbl_pages,
            self.lbl_words,
            self.lbl_ann,
            self.lbl_size,
        ):
            lab.setTextInteractionFlags(Qt.TextSelectableByMouse)
        form.addRow("Datei", self.lbl_file)
        form.addRow("Seiten", self.lbl_pages)
        form.addRow("Wörter", self.lbl_words)
        form.addRow("Annotationen", self.lbl_ann)
        form.addRow("Dateigröße", self.lbl_size)

        # Dateiname-Template {stem}_stats.json Live-Vorschau — 1.6.4
        self.stats_tpl = StatsFilenameTemplateEdit(get_stats_filename_template())
        self.stats_tpl.setPlaceholderText(DEFAULT_STATS_FILENAME_TEMPLATE)
        self.stats_tpl.setToolTip(
            "Dateiname-Template für Stats-JSON. "
            "Platzhalter: {stem}, {date}. Quick-Insert — 1.6.4"
        )
        self.stats_tpl.textChanged.connect(self._update_stats_tpl_preview)
        tpl_row = QHBoxLayout()
        tpl_row.addWidget(self.stats_tpl, 1)
        for token in ("{stem}", "{date}"):
            btn = QPushButton(token)
            btn.setAutoDefault(False)
            btn.setDefault(False)
            btn.setFocusPolicy(Qt.TabFocus)
            btn.setToolTip(
                f"Platzhalter {token} an Cursor einfügen — 1.6.4"
            )
            btn.clicked.connect(
                lambda _checked=False, t=token: self._insert_stats_placeholder(t)
            )
            tpl_row.addWidget(btn)
        form.addRow("JSON-Dateiname", tpl_row)
        self.stats_tpl_preview = QLabel("")
        self.stats_tpl_preview.setWordWrap(True)
        self.stats_tpl_preview.setTextFormat(Qt.RichText)
        self.stats_tpl_preview.setToolTip(
            "Live-Vorschau Dateiname; ungültige Platzhalter rot — 1.6.4"
        )
        form.addRow("Vorschau Dateiname", self.stats_tpl_preview)
        layout.addLayout(form)
        self._update_stats_tpl_preview()

        btn_row = QHBoxLayout()
        self.btn_refresh = QPushButton("Aktualisieren")
        self.btn_refresh.clicked.connect(self.refresh)
        btn_row.addWidget(self.btn_refresh)
        self.btn_copy = QPushButton("Als Text kopieren")
        self.btn_copy.setToolTip("Statistik in die Zwischenablage (Copy-as-Text) — 1.6.2")
        self.btn_copy.clicked.connect(self.copy_as_text)
        btn_row.addWidget(self.btn_copy)
        self.btn_export = QPushButton("JSON exportieren…")
        self.btn_export.setToolTip(
            "Export als ildstats-v1 JSON; Dateiname aus Template — 1.6.4"
        )
        self.btn_export.clicked.connect(self.export_json)
        btn_row.addWidget(self.btn_export)
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)

        if self._pdf_path:
            self.refresh()

    def _insert_stats_placeholder(self, token: str) -> None:
        """Quick-Insert {stem}/{date} — 1.6.4."""
        edit = self.stats_tpl
        if isinstance(edit, StatsFilenameTemplateEdit):
            edit.restore_insert_position()
        edit.insert(str(token or ""))
        edit.setFocus()
        if isinstance(edit, StatsFilenameTemplateEdit):
            edit._saved_cursor = edit.cursorPosition()
            edit._saved_sel_start = -1
            edit._saved_sel_len = 0
        self._update_stats_tpl_preview()

    def _update_stats_tpl_preview(self, *_args) -> None:
        """Live-Vorschau Stats-JSON-Dateiname — 1.6.4."""
        if not hasattr(self, "stats_tpl_preview"):
            return
        tpl = self.stats_tpl.text().strip() or DEFAULT_STATS_FILENAME_TEMPLATE
        sample_stem = "dokument"
        if self._pdf_path:
            sample_stem = self._pdf_path.stem or "dokument"
        name = preview_stats_filename(tpl, sample_stem=sample_stem)
        html_tpl = highlight_stats_template_html(tpl)
        invalid = find_invalid_stats_placeholders(tpl)
        parts = [html_tpl, f"→ {_html.escape(name)}"]
        if invalid:
            listed = ", ".join(_html.escape("{" + n + "}") for n in invalid)
            parts.append(
                f'<span style="color:#c62828">Ungültige Platzhalter: {listed}</span>'
            )
        self.stats_tpl_preview.setText("<br>".join(parts))

    def set_document(
        self,
        pdf_path: str | Path | None,
        *,
        annotation_count: int | None = None,
    ) -> None:
        self._pdf_path = Path(pdf_path) if pdf_path else None
        self._ann_count = annotation_count
        self.refresh()
        self._update_stats_tpl_preview()

    def refresh(self) -> DocumentStats | None:
        if not self._pdf_path or not self._pdf_path.is_file():
            self.lbl_file.setText("—")
            self.lbl_pages.setText("—")
            self.lbl_words.setText("— (kein PDF)")
            self.lbl_ann.setText("—")
            self.lbl_size.setText("—")
            self._last_stats = None
            self._update_stats_tpl_preview()
            return None
        try:
            stats = collect_document_stats(
                self._pdf_path,
                annotation_count=self._ann_count,
            )
        except Exception as e:
            self.lbl_file.setText(self._pdf_path.name)
            self.lbl_words.setText(f"Fehler: {e}")
            self._last_stats = None
            return None
        self.lbl_file.setText(self._pdf_path.name)
        self.lbl_file.setToolTip(str(self._pdf_path))
        self.lbl_pages.setText(str(stats.pages))
        # Wörter nur bei vorhandener Textschicht, sonst „—“ — 1.6.1
        if stats.has_text:
            self.lbl_words.setText(f"{stats.words}")
        else:
            self.lbl_words.setText("—")
        self.lbl_ann.setText(str(stats.annotations))
        self.lbl_size.setText(f"{stats.format_size()} ({stats.file_size} B)")
        self._last_stats = stats
        self._update_stats_tpl_preview()
        return stats

    def copy_as_text(self) -> bool:
        """Statistik als Text in die Zwischenablage — 1.6.2."""
        stats = self._last_stats or self.refresh()
        if stats is None:
            QMessageBox.information(self, "Dokument-Statistik", "Keine Statistik verfügbar.")
            return False
        text = format_document_stats_text(stats)
        QGuiApplication.clipboard().setText(text)
        return True

    def export_json(self) -> Path | None:
        """Statistik als ildstats-v1 JSON speichern; Template + Zielordner — 1.6.4."""
        stats = self._last_stats or self.refresh()
        if stats is None:
            QMessageBox.information(self, "Dokument-Statistik", "Keine Statistik verfügbar.")
            return None
        stem = Path(stats.path).stem or "document"
        tpl = set_stats_filename_template(self.stats_tpl.text().strip())
        fname = format_stats_filename(stem, tpl)
        start = dialog_start_dir(
            get_last_stats_export_dir(),
            Path(stats.path).parent,
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Statistik exportieren (ildstats-v1)",
            str(Path(start) / fname),
            "JSON (*.json);;Alle (*.*)",
        )
        if not path:
            return None
        try:
            out = export_document_stats_json(stats, path)
            set_last_stats_export_dir(Path(out).parent)
            QMessageBox.information(
                self,
                "Dokument-Statistik",
                f"Exportiert (ildstats-v1, UTF-8):\n{out}",
            )
            return out
        except Exception as e:
            QMessageBox.critical(self, "Dokument-Statistik", str(e))
            return None
