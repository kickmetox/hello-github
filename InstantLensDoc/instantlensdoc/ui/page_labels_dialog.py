"""Dialog: benutzerdefinierte PDF-Seitenbeschriftungen speichern/anzeigen — 2.2.0."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
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
        self.resize(420, 480)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Benutzerdefinierte Labels (z. B. i, ii, 1…). "
                "Leer = PDF-Standard / native PageLabels. — 2.2.0"
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
            # Anzeige: Index + aktuelles Label (ohne Custom-Override in Preview)
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

        presets = QHBoxLayout()
        btn_roman = QPushButton("Vorspann i, ii…")
        btn_roman.setToolTip("Erste Seiten römisch klein, Rest arabisch ab 1")
        btn_roman.clicked.connect(self._preset_frontmatter)
        presets.addWidget(btn_roman)
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

    def _clear_all(self) -> None:
        for ed in self._edits:
            ed.clear()

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
