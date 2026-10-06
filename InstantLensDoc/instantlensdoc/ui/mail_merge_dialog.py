"""Seriendruck-Dialog: Datenquelle, Felder, Datensatz-Vorschau, DOCX/PDF."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)


class MailMergeDialog(QDialog):
    def __init__(
        self,
        parent=None,
        *,
        template_text: str | None = None,
        editor=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Seriendruck")
        self.setObjectName("mailMergeDialog")
        self.setModal(True)
        self.resize(620, 560)
        self._result: dict | None = None
        self._editor = editor
        self._rows: list[dict] = []
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.tpl_edit = QLineEdit()
        self.tpl_edit.setObjectName("mailMergeTemplate")
        trow = QHBoxLayout()
        trow.addWidget(self.tpl_edit)
        bt = QPushButton("Vorlage…")
        bt.clicked.connect(self._pick_tpl)
        trow.addWidget(bt)
        form.addRow("Vorlage", trow)

        self.rec_edit = QLineEdit()
        self.rec_edit.setObjectName("mailMergeRecipients")
        rrow = QHBoxLayout()
        rrow.addWidget(self.rec_edit)
        br = QPushButton("Datenquelle…")
        br.setObjectName("mailMergeDataBtn")
        br.clicked.connect(self._pick_rec)
        rrow.addWidget(br)
        form.addRow("Datenquelle", rrow)

        self.out_edit = QLineEdit()
        orow = QHBoxLayout()
        orow.addWidget(self.out_edit)
        bo = QPushButton("Ausgabe…")
        bo.clicked.connect(self._pick_out)
        orow.addWidget(bo)
        form.addRow("Ausgabeordner", orow)

        self.stem = QLineEdit("letter")
        form.addRow("Dateiname-Stamm", self.stem)
        self.fmt = QComboBox()
        self.fmt.setObjectName("mailMergeFmt")
        self.fmt.addItem("Text (.txt)", "txt")
        self.fmt.addItem("HTML (.html)", "html")
        self.fmt.addItem("Word (.docx)", "docx")
        self.fmt.addItem("PDF (.pdf)", "pdf")
        form.addRow("Format", self.fmt)
        self.delim = QComboBox()
        self.delim.addItem("Auto", "")
        self.delim.addItem("Komma (,)", ",")
        self.delim.addItem("Semikolon (;)", ";")
        self.delim.addItem("Tab", "\t")
        form.addRow("CSV-Delimiter", self.delim)
        self.combined = QCheckBox("Eine kombinierte Datei")
        self.strict = QCheckBox("Abbruch bei fehlenden Spalten")
        form.addRow(self.combined)
        form.addRow(self.strict)

        field_row = QHBoxLayout()
        self.field_combo = QComboBox()
        self.field_combo.setObjectName("mailMergeFieldCombo")
        self.field_combo.setMinimumWidth(160)
        field_row.addWidget(self.field_combo)
        ins = QPushButton("Feld einfügen")
        ins.setObjectName("mailMergeInsertField")
        ins.clicked.connect(self.insert_current_field)
        field_row.addWidget(ins)
        form.addRow("Seriendruckfeld", field_row)

        prev_row = QHBoxLayout()
        self.record_spin = QSpinBox()
        self.record_spin.setObjectName("mailMergeRecordSpin")
        self.record_spin.setMinimum(1)
        self.record_spin.setMaximum(1)
        self.record_spin.valueChanged.connect(lambda _v: self._preview_record())
        prev_row.addWidget(QLabel("Datensatz"))
        prev_row.addWidget(self.record_spin)
        form.addRow(prev_row)
        layout.addLayout(form)

        if template_text:
            self._inline_template = template_text
        else:
            self._inline_template = None

        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setObjectName("mailMergePreview")
        self.preview.setPlaceholderText("Vorschau…")
        layout.addWidget(QLabel("Vorschau / Analyse"))
        layout.addWidget(self.preview)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        prev_btn = buttons.addButton("Vorschau", QDialogButtonBox.ActionRole)
        prev_btn.setObjectName("mailMergePreviewBtn")
        prev_btn.clicked.connect(self._preview)
        run_btn = buttons.addButton("Seriendruck starten", QDialogButtonBox.ActionRole)
        run_btn.setObjectName("mailMergeRunBtn")
        run_btn.clicked.connect(self._run)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _pick_tpl(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Vorlage", "", "Text (*.txt *.md *.html);;Word (*.docx);;Alle (*.*)"
        )
        if path:
            self.tpl_edit.setText(path)
            self._inline_template = None

    def _pick_rec(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Datenquelle",
            "",
            "Tabellen (*.csv *.xlsx *.ods);;CSV (*.csv);;Excel (*.xlsx);;ODS (*.ods);;Alle (*.*)",
        )
        if path:
            self.rec_edit.setText(path)
            self.reload_data_source()

    def _pick_out(self):
        path = QFileDialog.getExistingDirectory(self, "Ausgabeordner")
        if path:
            self.out_edit.setText(path)

    def _load_template(self) -> str:
        if self._inline_template is not None and not self.tpl_edit.text().strip():
            return self._inline_template
        p = self.tpl_edit.text().strip()
        if not p:
            raise ValueError("Vorlage angeben")
        return Path(p).read_text(encoding="utf-8")

    def reload_data_source(self) -> list[dict]:
        from instantlensdoc.core.mail_merge import load_recipients

        rec = self.rec_edit.text().strip()
        self._rows = []
        self.field_combo.clear()
        if not rec:
            return []
        delim = self.delim.currentData() or None
        self._rows = load_recipients(rec, delimiter=delim or None)
        cols: list[str] = []
        for row in self._rows:
            for k in row.keys():
                if k not in cols:
                    cols.append(k)
        for name in cols:
            self.field_combo.addItem(name, name)
        n = max(1, len(self._rows))
        self.record_spin.setMaximum(n)
        self.record_spin.setEnabled(bool(self._rows))
        return self._rows

    def insert_current_field(self) -> str:
        name = str(self.field_combo.currentText() or self.field_combo.currentData() or "").strip()
        if not name:
            self.reload_data_source()
            name = str(self.field_combo.currentText() or "").strip()
        if not name:
            return ""
        token = "{{" + name + "}}"
        ed = self._editor
        if ed is not None and hasattr(ed, "textCursor"):
            cur = ed.textCursor()
            cur.insertText(token)
            ed.setTextCursor(cur)
        return token

    def _preview_record(self) -> None:
        from instantlensdoc.core.mail_merge import merge_one

        if not self._rows:
            try:
                self.reload_data_source()
            except Exception as e:
                self.preview.setPlainText(f"Fehler: {e}")
                return
        if not self._rows:
            return
        try:
            tpl = self._load_template()
        except Exception as e:
            self.preview.setPlainText(f"Fehler: {e}")
            return
        idx = max(0, min(len(self._rows) - 1, int(self.record_spin.value()) - 1))
        letter = merge_one(tpl, self._rows[idx])
        self.preview.setPlainText(
            f"Datensatz {idx + 1} / {len(self._rows)}\n---\n{letter}"
        )

    def _preview(self):
        from instantlensdoc.core.mail_merge import preview_merge

        try:
            tpl = self._load_template()
            rows = self.reload_data_source()
            if not rows:
                raise ValueError("Empfängerdatei angeben")
            data = preview_merge(tpl, rows, limit=3)
            lines = [
                f"Empfänger: {data['total_recipients']}",
                f"Platzhalter: {', '.join(data['placeholders']) or '—'}",
                f"Spalten: {', '.join(data['columns']) or '—'}",
            ]
            if data["missing_columns"]:
                lines.append("FEHLEND: " + ", ".join(data["missing_columns"]))
            if data["rows_with_empty"]:
                lines.append(
                    f"Zeilen mit leeren Feldern: {len(data['rows_with_empty'])}"
                )
            lines.append("--- Vorschau ---")
            for i, letter in enumerate(data["preview"], start=1):
                lines.append(f"[{i}]\n{letter}\n")
            self.preview.setPlainText("\n".join(lines))
        except Exception as e:
            self.preview.setPlainText(f"Fehler: {e}")

    def _run(self):
        from instantlensdoc.core.mail_merge import (
            mail_merge_from_files,
            mail_merge_to_dir,
            load_recipients,
            missing_fields,
        )

        try:
            out = self.out_edit.text().strip()
            if not out:
                raise ValueError("Ausgabeordner angeben")
            rec = self.rec_edit.text().strip()
            if not rec:
                raise ValueError("Empfängerdatei angeben")
            delim = self.delim.currentData() or None
            fmt = self.fmt.currentData()
            stem = self.stem.text().strip() or "letter"
            if self.tpl_edit.text().strip():
                data = mail_merge_from_files(
                    self.tpl_edit.text().strip(),
                    rec,
                    out,
                    stem=stem,
                    fmt=fmt,
                    combined=self.combined.isChecked(),
                    delimiter=delim or None,
                    strict=self.strict.isChecked(),
                )
            else:
                tpl = self._load_template()
                rows = load_recipients(rec, delimiter=delim or None)
                analysis = missing_fields(tpl, rows)
                if self.strict.isChecked() and analysis["missing_columns"]:
                    raise ValueError(
                        "Fehlende Spalten: " + ", ".join(analysis["missing_columns"])
                    )
                paths = mail_merge_to_dir(
                    tpl,
                    rows,
                    out,
                    stem=stem,
                    fmt=fmt,
                    combined=self.combined.isChecked(),
                )
                data = {
                    "count": len(rows),
                    "files": len(paths),
                    "output": [str(p) for p in paths],
                    "out_dir": out,
                    "missing_columns": analysis["missing_columns"],
                }
            self._result = data
            msg = (
                f"Seriendruck: {data.get('count', 0)} Brief(e) → "
                f"{data.get('out_dir')}"
            )
            if data.get("missing_columns"):
                msg += "\nHinweis fehlende Spalten: " + ", ".join(
                    data["missing_columns"]
                )
            self.preview.setPlainText(msg + "\n" + "\n".join(data.get("output", [])))
            QMessageBox.information(self, "Seriendruck", msg)
        except Exception as e:
            QMessageBox.warning(self, "Seriendruck", str(e))

    def result_data(self) -> dict | None:
        return self._result
