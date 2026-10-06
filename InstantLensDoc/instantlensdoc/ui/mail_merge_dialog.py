"""Seriendruck-Dialog mit Vorschau — 2.6.27 Polish. — 2.6.28."""

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
    QVBoxLayout,
)


class MailMergeDialog(QDialog):
    def __init__(self, parent=None, *, template_text: str | None = None):
        super().__init__(parent)
        self.setWindowTitle("Serienbrief-Assistent")
        self.setObjectName("mailMergeDialog")
        self.resize(620, 560)
        self._result: dict | None = None
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
        br = QPushButton("Empfänger…")
        br.clicked.connect(self._pick_rec)
        rrow.addWidget(br)
        form.addRow("Empfänger", rrow)

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
        layout.addLayout(form)

        if template_text:
            # temp file not needed — keep path empty, use text on run
            self._inline_template = template_text
        else:
            self._inline_template = None

        field_row = QHBoxLayout()
        self.field_combo = QComboBox()
        self.field_combo.setObjectName("mailMergeFieldCombo")
        field_row.addWidget(QLabel("Feld"))
        field_row.addWidget(self.field_combo, 1)
        ins_btn = QPushButton("Feld einfügen")
        ins_btn.setObjectName("mailMergeInsertField")
        ins_btn.clicked.connect(self._insert_field)
        field_row.addWidget(ins_btn)
        prev_rec = QPushButton("◀ Datensatz")
        prev_rec.setObjectName("mailMergePrevRecord")
        prev_rec.clicked.connect(lambda: self._step_record(-1))
        next_rec = QPushButton("Datensatz ▶")
        next_rec.setObjectName("mailMergeNextRecord")
        next_rec.clicked.connect(lambda: self._step_record(1))
        field_row.addWidget(prev_rec)
        field_row.addWidget(next_rec)
        layout.addLayout(field_row)
        self._record_index = 0
        self._recipients: list = []
        self.insert_field_callback = None

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
        run_btn = buttons.addButton("Zusammenführen", QDialogButtonBox.ActionRole)
        run_btn.setObjectName("mailMergeRunBtn")
        run_btn.clicked.connect(self._run)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _pick_tpl(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Vorlage", "", "Text (*.txt *.md *.html);;Alle (*.*)"
        )
        if path:
            self.tpl_edit.setText(path)
            self._inline_template = None

    def _pick_rec(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Empfänger", "", "Tabellen (*.csv *.xlsx);;Alle (*.*)"
        )
        if path:
            self.rec_edit.setText(path)

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

    def _preview(self):
        from instantlensdoc.core.mail_merge import (
            load_recipients,
            preview_merge,
        )

        try:
            tpl = self._load_template()
            rec = self.rec_edit.text().strip()
            if not rec:
                raise ValueError("Empfängerdatei angeben")
            delim = self.delim.currentData() or None
            rows = load_recipients(rec, delimiter=delim or None)
            self._recipients = list(rows)
            self._record_index = 0
            self.field_combo.clear()
            cols = []
            if rows:
                cols = list(rows[0].keys())
            for c in cols:
                self.field_combo.addItem(c, c)
            data = preview_merge(tpl, rows, limit=3)
            lines = [
                f"Empfänger: {data['total_recipients']}",
                f"Platzhalter: {', '.join(data['placeholders']) or '—'}",
                f"Spalten: {', '.join(data['columns']) or '—'}",
            ]
            if data["missing_columns"]:
                lines.append(
                    "FEHLEND: " + ", ".join(data["missing_columns"])
                )
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
                        "Fehlende Spalten: "
                        + ", ".join(analysis["missing_columns"])
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
                msg += (
                    "\nHinweis fehlende Spalten: "
                    + ", ".join(data["missing_columns"])
                )
            self.preview.setPlainText(msg + "\n" + "\n".join(data.get("output", [])))
            QMessageBox.information(self, "Seriendruck", msg)
        except Exception as e:
            QMessageBox.warning(self, "Seriendruck", str(e))

    def _insert_field(self) -> None:
        name = str(self.field_combo.currentData() or self.field_combo.currentText() or "").strip()
        if not name:
            return
        cb = getattr(self, "insert_field_callback", None)
        if callable(cb):
            cb(name)

    def _step_record(self, delta: int) -> None:
        from instantlensdoc.core.mail_merge import merge_one

        rows = list(getattr(self, "_recipients", []) or [])
        if not rows:
            try:
                self._preview()
                rows = list(getattr(self, "_recipients", []) or [])
            except Exception:
                return
        if not rows:
            return
        self._record_index = (int(getattr(self, "_record_index", 0)) + int(delta)) % len(rows)
        try:
            tpl = self._load_template()
        except Exception as e:
            self.preview.setPlainText(str(e))
            return
        letter = merge_one(tpl, rows[self._record_index])
        self.preview.setPlainText(
            f"Datensatz {self._record_index + 1} / {len(rows)}\n---\n{letter}"
        )

    def set_recipients_path(self, path: str) -> None:
        self.rec_edit.setText(path)

    def result_data(self) -> dict | None:
        return self._result
