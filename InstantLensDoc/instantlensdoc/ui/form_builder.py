"""Formulargenerator-Dialog mit Vorschau und Export."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from instantlensdoc.core.forms import FieldType, FormDefinition, FormField, export_html, export_pdf_form


class FormBuilderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Formulargenerator")
        self.resize(640, 520)
        self.form = FormDefinition(title="Neues Formular")

        layout = QVBoxLayout(self)
        self.title_edit = QLineEdit(self.form.title)
        self.title_edit.textChanged.connect(self._update_preview)
        layout.addWidget(QLabel("Titel"))
        layout.addWidget(self.title_edit)

        row = QHBoxLayout()
        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("Feldbezeichnung")
        self.type_combo = QComboBox()
        for t in FieldType:
            self.type_combo.addItem(t.value, t)
        self.req = QCheckBox("Pflicht")
        self.options_edit = QLineEdit()
        self.options_edit.setPlaceholderText("Optionen (Komma) für Dropdown")
        add_btn = QPushButton("Feld hinzu")
        add_btn.clicked.connect(self._add_field)
        row.addWidget(self.label_edit)
        row.addWidget(self.type_combo)
        row.addWidget(self.req)
        layout.addLayout(row)
        layout.addWidget(self.options_edit)
        layout.addWidget(add_btn)

        mid = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(QLabel("Felder"))
        self.list = QListWidget()
        left.addWidget(self.list)
        btn_rm = QPushButton("Feld entfernen")
        btn_rm.clicked.connect(self._remove_field)
        left.addWidget(btn_rm)
        mid.addLayout(left)

        right = QVBoxLayout()
        right.addWidget(QLabel("Vorschau"))
        self.preview = QTextBrowser()
        right.addWidget(self.preview)
        mid.addLayout(right)
        layout.addLayout(mid)

        export_row = QHBoxLayout()
        btn_html = QPushButton("Als HTML exportieren")
        btn_pdf = QPushButton("Als PDF exportieren")
        btn_html.clicked.connect(self._export_html)
        btn_pdf.clicked.connect(self._export_pdf)
        export_row.addWidget(btn_html)
        export_row.addWidget(btn_pdf)
        layout.addLayout(export_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.clicked.connect(self.accept)
        layout.addWidget(buttons)
        self._update_preview()

    def _sync_title(self):
        self.form.title = self.title_edit.text().strip() or "Formular"

    def _add_field(self):
        label = self.label_edit.text().strip()
        if not label:
            return
        ftype = self.type_combo.currentData()
        opts = [o.strip() for o in self.options_edit.text().split(",") if o.strip()]
        field = FormField(label=label, type=ftype, required=self.req.isChecked(), options=opts)
        self.form.add_field(field)
        self.list.addItem(f"{field.type.value}: {field.label}")
        self.label_edit.clear()
        self._update_preview()

    def _remove_field(self):
        row = self.list.currentRow()
        if row < 0 or row >= len(self.form.fields):
            return
        del self.form.fields[row]
        self.list.takeItem(row)
        self._update_preview()

    def _update_preview(self):
        self._sync_title()
        # HTML-Vorschau ohne Datei
        from instantlensdoc.core.forms import export_html
        import tempfile
        from pathlib import Path as P

        with tempfile.TemporaryDirectory() as td:
            p = P(td) / "preview.html"
            export_html(self.form, p)
            self.preview.setHtml(p.read_text(encoding="utf-8"))

    def _export_html(self):
        self._sync_title()
        if not self.form.fields:
            QMessageBox.information(self, "Export", "Bitte zuerst Felder hinzufügen.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "HTML speichern", "formular.html", "HTML (*.html)")
        if not path:
            return
        export_html(self.form, path)
        QMessageBox.information(self, "Export", f"HTML gespeichert:\n{path}")

    def _export_pdf(self):
        self._sync_title()
        if not self.form.fields:
            QMessageBox.information(self, "Export", "Bitte zuerst Felder hinzufügen.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "PDF speichern", "formular.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            export_pdf_form(self.form, path)
            QMessageBox.information(self, "Export", f"PDF gespeichert:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "Export", str(e))
