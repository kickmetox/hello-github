"""Dialog: benutzerdefinierte PDF-Seitenbeschriftungen — 2.2.0 / Polish 2.2.1–2.2.3."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class PageLabelsDialog(QDialog):
    """Labels pro Seite bearbeiten; Sidecar + optional PDF PageLabels."""

    def __init__(self, pdf_view, parent=None):
        super().__init__(parent)
        self.pdf_view = pdf_view
        self.setWindowTitle("Seitenbeschriftungen…")
        self.setWindowModality(Qt.WindowModal)
        self.resize(500, 640)
        # Bereits angewandte Ranges in dieser Dialog-Session (0-basiert inkl.) — 2.2.3
        self._applied_ranges: list[tuple[int, int]] = []
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Benutzerdefinierte Labels (z. B. i, ii, 1…). "
                "Leer = PDF-Standard / native PageLabels. — 2.2.3"
            )
        )
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        form = QVBoxLayout(body)
        n = max(0, int(getattr(pdf_view, "page_count", 0) or 0))
        custom = []
        if getattr(pdf_view, "store", None) is not None:
            custom = pdf_view.store.list_custom_page_labels(page_count=n)
        while len(custom) < n:
            custom.append("")
        self._edits: list[QLineEdit] = []
        for i in range(n):
            row = QHBoxLayout()
            native = ""
            try:
                native = str(pdf_view.page_label(i) or "")
            except Exception:
                native = ""
            hint = f"Seite {i + 1}"
            if native and (i >= len(custom) or not custom[i]):
                hint += f" ({native})"
            row.addWidget(QLabel(hint))
            ed = QLineEdit(custom[i] if i < len(custom) else "")
            ed.setPlaceholderText(native or str(i + 1))
            ed.setMaxLength(64)
            ed.setClearButtonEnabled(True)
            row.addWidget(ed, 1)
            form.addLayout(row)
            self._edits.append(ed)
        form.addStretch(1)
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)

        # Range-Editor — 2.2.1 + Überlappung/Vorschau — 2.2.3 + Scroll-Liste 20 — 2.2.3
        range_box = QGroupBox("Bereich setzen (Range-Editor)")
        range_form = QFormLayout(range_box)
        self.spin_from = QSpinBox()
        self.spin_from.setRange(1, max(1, n))
        self.spin_from.setValue(1)
        self.spin_to = QSpinBox()
        self.spin_to.setRange(1, max(1, n))
        self.spin_to.setValue(max(1, n))
        self.spin_start = QSpinBox()
        self.spin_start.setRange(0, 9999)
        self.spin_start.setValue(1)
        self.spin_start.setToolTip("Arabischer Startwert für den Bereich")
        range_form.addRow("Von Seite", self.spin_from)
        range_form.addRow("Bis Seite", self.spin_to)
        range_form.addRow("Startwert", self.spin_start)
        self.lbl_range_preview = QLabel("Vorschau: —")
        self.lbl_range_preview.setObjectName("pageLabelRangePreview")
        self.lbl_range_preview.setToolTip(
            "Kurzvorschau erste Labels — 2.2.3; Scroll-Liste darunter (max. 20) — 2.2.3"
        )
        range_form.addRow(self.lbl_range_preview)
        self.list_preview = QListWidget()
        self.list_preview.setObjectName("pageLabelPreviewList")
        self.list_preview.setMaximumHeight(140)
        self.list_preview.setToolTip(
            "Scroll-Liste: erste 20 Labels des Bereichs — 2.2.3"
        )
        range_form.addRow(self.list_preview)
        self.lbl_range_error = QLabel("")
        self.lbl_range_error.setObjectName("pageLabelRangeError")
        self.lbl_range_error.setStyleSheet("color: #B00020;")
        self.lbl_range_error.setWordWrap(True)
        range_form.addRow(self.lbl_range_error)
        btn_range = QPushButton("Bereich arabisch anwenden")
        btn_range.setToolTip(
            "Füllt den Bereich mit 1, 2, 3… ab Startwert; "
            "überlappende Bereiche werden abgelehnt (DE) — 2.2.3"
        )
        btn_range.clicked.connect(self._apply_range)
        range_form.addRow(btn_range)
        layout.addWidget(range_box)

        self.spin_from.valueChanged.connect(self._update_range_preview)
        self.spin_to.valueChanged.connect(self._update_range_preview)
        self.spin_start.valueChanged.connect(self._update_range_preview)

        presets = QHBoxLayout()
        btn_roman = QPushButton("Vorspann i, ii…")
        btn_roman.setToolTip("Erste Seiten römisch klein, Rest arabisch ab 1")
        btn_roman.clicked.connect(self._preset_frontmatter)
        presets.addWidget(btn_roman)
        btn_import = QPushButton("Aus PDF importieren")
        btn_import.setToolTip("Native PDF-PageLabels in die Felder übernehmen — 2.2.1")
        btn_import.clicked.connect(self._import_from_pdf)
        presets.addWidget(btn_import)
        btn_arabic = QPushButton("Reset arabisch 1…")
        btn_arabic.setToolTip("Alle Seiten auf arabisch 1, 2, 3… zurücksetzen — 2.2.1")
        btn_arabic.clicked.connect(self._reset_arabic)
        presets.addWidget(btn_arabic)
        btn_export_txt = QPushButton("Labels als TXT…")
        btn_export_txt.setObjectName("pageLabelExportTxt")
        btn_export_txt.setToolTip("Aktuelle Labels als TXT exportieren — 2.2.3")
        btn_export_txt.clicked.connect(self._export_labels_txt)
        presets.addWidget(btn_export_txt)
        btn_clear = QPushButton("Alle leeren")
        btn_clear.clicked.connect(self._clear_all)
        presets.addWidget(btn_clear)
        presets.addStretch(1)
        layout.addLayout(presets)

        self.chk_write_pdf = QCheckBox("Auch in PDF schreiben (PageLabels via pikepdf)")
        self.chk_write_pdf.setChecked(False)
        self.chk_write_pdf.setToolTip(
            "Schreibt /PageLabels in die PDF-Datei (Prefix je Label). "
            "Sidecar wird immer gespeichert."
        )
        layout.addWidget(self.chk_write_pdf)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._update_range_preview()

    def _clear_all(self) -> None:
        for ed in self._edits:
            ed.clear()
        self._applied_ranges.clear()
        self._update_range_preview()

    def _preset_frontmatter(self) -> None:
        """Einfaches Schema: Seite 1→i, 2→ii, ab 3 arabisch 1…"""
        n = len(self._edits)
        if n <= 0:
            return
        romans = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"]
        front = min(2, n)  # erste 2 römisch wenn möglich
        for i, ed in enumerate(self._edits):
            if i < front:
                ed.setText(romans[i] if i < len(romans) else str(i + 1))
            else:
                ed.setText(str(i - front + 1))
        self._applied_ranges.clear()
        if n > 0:
            self._applied_ranges.append((0, n - 1))
        self._update_range_preview()

    def _range_bounds(self) -> tuple[int, int]:
        """0-basierte inklusive Grenzen aus den SpinBoxes."""
        a = self.spin_from.value() - 1
        b = self.spin_to.value() - 1
        return (min(a, b), max(a, b))

    def _update_range_preview(self) -> None:
        from ild_pdf.page_labels import (
            LABEL_PREVIEW_SCROLL_LIMIT,
            format_label_preview,
            format_label_preview_lines,
            normalize_page_range,
            preview_label_range,
            validate_label_range_overlap,
        )

        lo, hi = self._range_bounds()
        total = max(0, hi - lo + 1)
        # Kurztext: erste 5
        first_short = preview_label_range(
            start_page=lo,
            end_page=hi,
            start_value=self.spin_start.value(),
            max_preview=5,
        )
        self.lbl_range_preview.setText(format_label_preview(first_short, total=total))
        # Scroll-Liste: erste 20
        first_scroll = preview_label_range(
            start_page=lo,
            end_page=hi,
            start_value=self.spin_start.value(),
            max_preview=LABEL_PREVIEW_SCROLL_LIMIT,
        )
        lines = format_label_preview_lines(
            first_scroll,
            start_page=lo,
            total=total,
            max_lines=LABEL_PREVIEW_SCROLL_LIMIT,
        )
        self.list_preview.clear()
        if not lines:
            item = QListWidgetItem("(keine Vorschau)")
            item.setFlags(Qt.NoItemFlags)
            self.list_preview.addItem(item)
        else:
            for line in lines:
                self.list_preview.addItem(QListWidgetItem(line))
        err = validate_label_range_overlap(self._applied_ranges, lo, hi)
        if err:
            self.lbl_range_error.setText(err)
        else:
            # Hinweis wenn von > bis (wird trotzdem normalisiert)
            a = self.spin_from.value()
            b = self.spin_to.value()
            if a > b:
                nlo, nhi = normalize_page_range(a - 1, b - 1)
                self.lbl_range_error.setText(
                    f"Hinweis: Von/Bis vertauscht — effektiv Seite {nlo + 1}–{nhi + 1}."
                )
            else:
                self.lbl_range_error.setText("")

    def _apply_range(self) -> None:
        from ild_pdf.page_labels import apply_label_range, validate_label_range_overlap

        n = len(self._edits)
        if n <= 0:
            return
        lo, hi = self._range_bounds()
        err = validate_label_range_overlap(self._applied_ranges, lo, hi)
        if err:
            self.lbl_range_error.setText(err)
            QMessageBox.warning(self, "Seitenbeschriftungen", err)
            return
        current = self.labels()
        filled = apply_label_range(
            current,
            start_page=lo,
            end_page=hi,
            start_value=self.spin_start.value(),
            page_count=n,
        )
        for i, ed in enumerate(self._edits):
            ed.setText(filled[i] if i < len(filled) else "")
        self._applied_ranges.append((lo, hi))
        self._update_range_preview()

    def _import_from_pdf(self) -> None:
        pv = self.pdf_view
        if not getattr(pv, "pdf_path", None):
            QMessageBox.warning(self, "Seitenbeschriftungen", "Kein PDF geöffnet.")
            return
        try:
            from ild_pdf.page_labels import read_pdf_page_labels

            native = read_pdf_page_labels(pv.pdf_path, password=getattr(pv, "password", None))
        except Exception as e:
            QMessageBox.warning(self, "Seitenbeschriftungen", f"Import fehlgeschlagen:\n{e}")
            return
        for i, ed in enumerate(self._edits):
            ed.setText(native[i] if i < len(native) else "")
        self._applied_ranges.clear()
        self._update_range_preview()

    def _reset_arabic(self) -> None:
        from ild_pdf.page_labels import arabic_reset_labels

        filled = arabic_reset_labels(len(self._edits), start=1)
        for i, ed in enumerate(self._edits):
            ed.setText(filled[i] if i < len(filled) else "")
        self._applied_ranges.clear()
        n = len(self._edits)
        if n > 0:
            self._applied_ranges.append((0, n - 1))
        self._update_range_preview()

    def _export_labels_txt(self) -> None:
        """Aktuelle Dialog-Labels als TXT speichern — 2.2.3."""
        from ild_pdf.page_labels import export_page_labels_txt

        labels = self.labels()
        if not labels:
            QMessageBox.information(
                self, "Seitenbeschriftungen", "Keine Labels zum Exportieren."
            )
            return
        stem = "page-labels"
        try:
            p = getattr(self.pdf_view, "pdf_path", None)
            if p:
                from pathlib import Path

                stem = Path(p).stem + "-labels"
        except Exception:
            pass
        default = f"{stem}.txt"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Labels als TXT exportieren",
            default,
            "Text (*.txt);;Alle Dateien (*)",
        )
        if not path:
            return
        try:
            out = export_page_labels_txt(path, labels)
        except Exception as e:
            QMessageBox.warning(
                self, "Seitenbeschriftungen", f"Export fehlgeschlagen:\n{e}"
            )
            return
        QMessageBox.information(
            self, "Seitenbeschriftungen", f"Exportiert:\n{out}"
        )

    def labels(self) -> list[str]:
        return [ed.text().strip() for ed in self._edits]

    def write_pdf(self) -> bool:
        return bool(self.chk_write_pdf.isChecked())

    def _save(self) -> None:
        pv = self.pdf_view
        if getattr(pv, "store", None) is None:
            QMessageBox.warning(self, "Seitenbeschriftungen", "Kein PDF / Sidecar geöffnet.")
            return
        labels = self.labels()
        try:
            pv.apply_custom_page_labels(labels, write_pdf=self.write_pdf())
        except Exception as e:
            QMessageBox.warning(self, "Seitenbeschriftungen", f"Speichern fehlgeschlagen:\n{e}")
            return
        self.accept()
